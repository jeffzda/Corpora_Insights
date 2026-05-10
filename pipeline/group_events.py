#!/usr/bin/env python3
"""Group already-extracted records into events as a separate downstream pass.

Tests the orthogonality hypothesis: extraction yield should be invariant to
event-grouping policy. Inputs are records already extracted (e.g. by v1's
extract_e3 driver or v2's extract_v2 driver). For each project doc processed
in seed-order, this script reads the doc's records + the project's running
event registry, sends batches to Sonnet, and writes per-record event
assignments alongside the input records.

Usage:
    python -m pipeline.group_events \\
        --in corpora/arena/output/per_doc/doc_0844.json \\
        --out runs/arena/grouping_test/doc_0844.assignments.json

    # Subsequent docs use the prior doc's events.json as input
    python -m pipeline.group_events \\
        --in corpora/arena/output/per_doc/doc_1347.json \\
        --out runs/arena/grouping_test/doc_1347.assignments.json \\
        --prior-events runs/arena/grouping_test/doc_0844.events.json
"""
import argparse
import json
import re
import time
from pathlib import Path

import anthropic
try:
    import httpx
except ImportError:
    httpx = None

ROOT = Path(__file__).resolve().parents[1]
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10
PRICE_INPUT_SONNET = 3.0
PRICE_OUTPUT_SONNET = 15.0
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = 20  # records per LLM call
PROMPT_PATH = ROOT / "pipeline" / "prompts" / "group_events.md"


def load_prompt():
    return PROMPT_PATH.read_text()


def trim_record_for_grouping(rec, exclude=None):
    """Trim a record to the fields the grouping LLM needs.

    Keeps id + the substantive narrative/evidence/lesson/intervention/title.
    Strips catalogue-stamping, page numbers, etc.

    `exclude` is a set of canonical field names to remove from the output
    after schema normalisation. Use to ablate priors — e.g. exclude={"lesson"}
    drops the LLM-inferred transferable-implication field, which carries
    model priors and may bias grouping toward template similarity rather
    than source-content overlap.
    """
    exclude = set(exclude or [])
    keep = ["id", "record_id", "title", "source_title", "narrative",
            "what_happened", "lesson", "lesson_learnt", "evidence",
            "evidence_excerpt", "intervention", "intervention_note",
            "significance", "issue_severity"]
    out = {k: rec[k] for k in keep if rec.get(k) is not None}
    # Normalise to v1 schema field names where possible (LLM sees consistent shape)
    if "record_id" in out and "id" not in out:
        out["id"] = out.pop("record_id")
    if "what_happened" in out and "narrative" not in out:
        out["narrative"] = out.pop("what_happened")
    if "lesson_learnt" in out and "lesson" not in out:
        out["lesson"] = out.pop("lesson_learnt")
    if "evidence_excerpt" in out and "evidence" not in out:
        out["evidence"] = out.pop("evidence_excerpt")
    if "intervention_note" in out and "intervention" not in out:
        out["intervention"] = out.pop("intervention_note")
    if "issue_severity" in out and "significance" not in out:
        sev_map = {"none": 1, "minor": 2, "moderate": 3, "major": 4, "critical": 5}
        out["significance"] = sev_map.get(out.pop("issue_severity"), 3)
    # Apply ablation drops after normalisation
    for f in exclude:
        out.pop(f, None)
    return out


def build_prior_events_block(prior_events):
    if not prior_events:
        return ("none — this is the first batch. Number new events starting at EVT-0001.")
    next_n = 1
    for ev in prior_events:
        m = re.search(r"EVT-(\d+)", ev.get("event_id", ""))
        if m:
            next_n = max(next_n, int(m.group(1)) + 1)
    lines = [
        f"{len(prior_events)} events already established. Number any new "
        f"declarations starting at EVT-{next_n:04d}.\n",
    ]
    for ev in prior_events:
        eid = ev.get("event_id", "EVT-XXXX")
        name = ev.get("event_name", "")
        desc = ev.get("description", "") or ""
        ex = ev.get("exemplar_mechanism_phrase", "") or ""
        block = f"- `{eid}` — **{name}**"
        if desc:
            block += f"\n    Description: {desc}"
        if ex:
            block += f"\n    Exemplar mechanism phrase: \"{ex}\""
        lines.append(block)
    return "\n".join(lines)


def build_prompt(template, prior_events, records_batch, exclude_fields=None):
    prompt = template
    prompt = prompt.replace("{{prior_events_block}}",
                             build_prior_events_block(prior_events))
    trimmed = [trim_record_for_grouping(r, exclude=exclude_fields)
                for r in records_batch]
    prompt = prompt.replace("{{records_block}}",
                             json.dumps(trimmed, indent=2, ensure_ascii=False))
    return prompt


def call_api(client, prompt, model, max_tokens, label, temperature=0.0):
    """Anthropic SDK requires streaming whenever max_tokens > ~8192 for
    Sonnet, since the call may exceed the 10-minute non-streaming timeout.
    Use streaming above 8192."""
    use_streaming = max_tokens > 8192
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_streaming:
                with client.messages.stream(
                    model=model, max_tokens=max_tokens, temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    msg = stream.get_final_message()
                    return (msg.content[0].text,
                            msg.usage.input_tokens, msg.usage.output_tokens)
            msg = client.messages.create(
                model=model, max_tokens=max_tokens, temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return (msg.content[0].text,
                    msg.usage.input_tokens, msg.usage.output_tokens)
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  Rate limit ({label}, attempt {attempt}/{MAX_RETRIES}), waiting {delay}s",
                  flush=True)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"  Server error {e.status_code} ({label}, attempt {attempt}/{MAX_RETRIES})",
                      flush=True)
                time.sleep(delay)
            else:
                raise
        except (anthropic.APIConnectionError,) + (
                (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError)
                if httpx else ()) as e:
            delay = RETRY_BASE_DELAY * attempt
            print(f"  Network error ({type(e).__name__}: {e}) ({label}, "
                  f"attempt {attempt}/{MAX_RETRIES}), waiting {delay}s",
                  flush=True)
            time.sleep(delay)
    raise RuntimeError(f"{label}: API failed after {MAX_RETRIES} attempts")


def parse_response(response, label):
    """Parse JSON {assignments: [...], events: [...]} from the model response."""
    text = response.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        first = text.find("{"); last = text.rfind("}")
        if first >= 0 and last > first:
            try:
                parsed = json.loads(text[first:last+1])
            except json.JSONDecodeError as e:
                print(f"  WARNING ({label}): JSON parse failed: {e}", flush=True)
                return [], []
        else:
            return [], []
    if not isinstance(parsed, dict):
        return [], []
    return parsed.get("assignments", []) or [], parsed.get("events", []) or []


def merge_event_registries(running, new_events):
    by_id = {ev["event_id"]: ev for ev in running}
    for ev in new_events:
        eid = ev.get("event_id")
        if eid and eid not in by_id:
            by_id[eid] = ev
    return list(by_id.values())


def group_one_doc(records, prior_events, prompt_template, client, model,
                   max_tokens, batch_size, label_prefix, exclude_fields=None):
    """Group all records in one doc, batching them. Returns (all_assignments,
    final_events_registry, total_in_tokens, total_out_tokens)."""
    all_assignments = []
    running_events = list(prior_events)
    total_in = total_out = 0
    n_batches = (len(records) + batch_size - 1) // batch_size

    for bi in range(n_batches):
        batch = records[bi * batch_size:(bi + 1) * batch_size]
        label = f"{label_prefix} batch {bi+1}/{n_batches}"
        prompt = build_prompt(prompt_template, running_events, batch,
                                exclude_fields=exclude_fields)
        response, in_tok, out_tok = call_api(client, prompt, model, max_tokens, label)
        total_in += in_tok
        total_out += out_tok
        cost = (in_tok / 1_000_000 * PRICE_INPUT_SONNET) + \
               (out_tok / 1_000_000 * PRICE_OUTPUT_SONNET)
        assignments, new_events = parse_response(response, label)
        running_events = merge_event_registries(running_events, new_events)
        all_assignments.extend(assignments)
        print(f"    {label}: {len(batch)} records → {len(assignments)} "
              f"assignments  (registry: {len(running_events)} events)  "
              f"({in_tok:,} in / {out_tok:,} out, ${cost:.3f})", flush=True)

    return all_assignments, running_events, total_in, total_out


def main():
    parser = argparse.ArgumentParser(
        description="Group already-extracted records into events")
    parser.add_argument("--in", dest="in_path", required=True,
                         help="Input record JSON (e.g. v1 doc_NNNN.json)")
    parser.add_argument("--out", required=True,
                         help="Output assignments JSON path")
    parser.add_argument("--prior-events", default=None,
                         help="Prior doc's events.json (cross-doc walks)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--exclude-fields", default="",
                         help="Comma-separated list of record fields to drop "
                              "before sending to the grouping LLM. Use to "
                              "ablate priors — e.g. --exclude-fields lesson")
    args = parser.parse_args()
    exclude_fields = {f.strip() for f in args.exclude_fields.split(",") if f.strip()}

    in_path = Path(args.in_path)
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load input records
    data = json.load(open(in_path))
    if isinstance(data, dict) and "records" in data:
        records = data["records"]
    elif isinstance(data, list):
        records = data
    else:
        raise SystemExit(f"Unexpected input shape: {in_path}")

    # Load prior events if any
    prior_events = []
    if args.prior_events:
        pp = Path(args.prior_events)
        if not pp.is_absolute():
            pp = ROOT / pp
        if pp.exists():
            pd = json.load(open(pp))
            prior_events = pd.get("events", []) if isinstance(pd, dict) else (pd or [])
            print(f"Loaded {len(prior_events)} prior events from {pp.name}",
                  flush=True)

    print(f"Grouping {len(records)} records from {in_path.name} "
          f"(batch size {args.batch_size}, model {args.model})", flush=True)

    client = anthropic.Anthropic()
    prompt_template = load_prompt()
    max_tokens = 32_000

    if exclude_fields:
        print(f"Excluding fields from grouping LLM input: {sorted(exclude_fields)}",
              flush=True)

    assignments, final_events, total_in, total_out = group_one_doc(
        records, prior_events, prompt_template, client, args.model,
        max_tokens, args.batch_size, in_path.stem,
        exclude_fields=exclude_fields)

    # Write outputs
    out_path.write_text(json.dumps({
        "doc": in_path.stem,
        "n_records": len(records),
        "n_assignments": len(assignments),
        "assignments": assignments,
    }, indent=2, ensure_ascii=False))

    events_out = out_path.parent / (in_path.stem + ".events.json")
    events_out.write_text(json.dumps({
        "doc": in_path.stem,
        "n_events": len(final_events),
        "events": final_events,
    }, indent=2, ensure_ascii=False))

    cost = (total_in / 1_000_000 * PRICE_INPUT_SONNET) + \
           (total_out / 1_000_000 * PRICE_OUTPUT_SONNET)
    print(f"\nDone: {len(assignments)} assignments → {out_path.name}; "
          f"{len(final_events)} events → {events_out.name}", flush=True)
    print(f"Tokens: {total_in:,} in / {total_out:,} out  (${cost:.2f})", flush=True)


if __name__ == "__main__":
    main()
