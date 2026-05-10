#!/usr/bin/env python3
"""One-shot variant of group_events.py — sends ALL records to a single
Sonnet call instead of batching across docs.

Tests whether the model produces tighter or looser event grouping when it
sees the full record set at once vs sequentially in batches with a running
event registry.

Usage:
    python -m pipeline.group_events_oneshot \\
        --in corpora/arena/output/per_doc/doc_0844.json \\
        --in corpora/arena/output/per_doc/doc_1347.json \\
        --in corpora/arena/output/per_doc/doc_1348.json \\
        --out runs/arena/grouping_oneshot/assignments.json
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
PROMPT_PATH = ROOT / "pipeline" / "prompts" / "group_events.md"

# Reuse the trim + parse + retry logic from group_events.py
from pipeline.group_events import (
    trim_record_for_grouping, build_prior_events_block,
    parse_response, merge_event_registries,
)


def call_api(client, prompt, model, max_tokens, label):
    """Call Claude API with retry. One-shot version uses streaming because
    the call may take a while given the large input."""
    use_streaming = max_tokens > 8192
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_streaming:
                with client.messages.stream(
                    model=model, max_tokens=max_tokens, temperature=0.0,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    msg = stream.get_final_message()
                    return (msg.content[0].text,
                            msg.usage.input_tokens, msg.usage.output_tokens)
            else:
                msg = client.messages.create(
                    model=model, max_tokens=max_tokens, temperature=0.0,
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


def main():
    parser = argparse.ArgumentParser(
        description="Group records in one Sonnet call (no batching)")
    parser.add_argument("--in", dest="in_paths", action="append", required=True,
                         help="Input record JSON files (repeatable, processed in given order)")
    parser.add_argument("--out", required=True,
                         help="Output assignments JSON path")
    parser.add_argument("--prior-events", default=None,
                         help="Prior events.json (cross-project chain)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=64_000)
    args = parser.parse_args()

    # Resolve and load all input record files
    all_records = []
    doc_origins = []  # parallel list of source doc-id per record
    for in_path_str in args.in_paths:
        p = Path(in_path_str)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            raise SystemExit(f"Input not found: {p}")
        d = json.load(open(p))
        recs = d["records"] if isinstance(d, dict) and "records" in d else d
        if not isinstance(recs, list):
            raise SystemExit(f"Unexpected shape: {p}")
        for r in recs:
            all_records.append(r)
            doc_origins.append(p.stem)
        print(f"  Loaded {len(recs)} records from {p.stem}", flush=True)

    print(f"Total: {len(all_records)} records across {len(args.in_paths)} docs",
          flush=True)

    # Load prior events if any
    prior_events = []
    if args.prior_events:
        pp = Path(args.prior_events)
        if not pp.is_absolute():
            pp = ROOT / pp
        if pp.exists():
            pd = json.load(open(pp))
            prior_events = pd.get("events", []) if isinstance(pd, dict) else (pd or [])
            print(f"Loaded {len(prior_events)} prior events", flush=True)

    # Build the one-shot prompt
    template = PROMPT_PATH.read_text()
    trimmed = [trim_record_for_grouping(r) for r in all_records]
    prompt = template
    prompt = prompt.replace("{{prior_events_block}}",
                             build_prior_events_block(prior_events))
    prompt = prompt.replace("{{records_block}}",
                             json.dumps(trimmed, indent=2, ensure_ascii=False))

    print(f"Prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)",
          flush=True)

    client = anthropic.Anthropic()
    print(f"Calling {args.model} (max_tokens={args.max_tokens:,})...", flush=True)
    t0 = time.time()
    response, in_tok, out_tok = call_api(client, prompt, args.model,
                                           args.max_tokens, "oneshot")
    elapsed = time.time() - t0
    cost = (in_tok / 1_000_000 * PRICE_INPUT_SONNET) + \
           (out_tok / 1_000_000 * PRICE_OUTPUT_SONNET)
    print(f"  {in_tok:,} in / {out_tok:,} out  ({elapsed:.0f}s, ${cost:.2f})",
          flush=True)

    assignments, new_events = parse_response(response, "oneshot")
    final_events = merge_event_registries(prior_events, new_events)
    print(f"  → {len(assignments)} assignments, {len(final_events)} events",
          flush=True)

    # Build doc-id lookup so output can be sliced per doc downstream if useful
    rid_to_doc = {}
    for r, doc_stem in zip(all_records, doc_origins):
        rid_to_doc[r.get("id", r.get("record_id"))] = doc_stem

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Annotate assignments with origin doc
    for asn in assignments:
        rid = asn.get("record_id")
        asn["_doc"] = rid_to_doc.get(rid, "unknown")

    out_path.write_text(json.dumps({
        "in_paths": [str(Path(p).name) for p in args.in_paths],
        "n_records": len(all_records),
        "n_assignments": len(assignments),
        "n_events": len(final_events),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "wall_seconds": int(elapsed),
        "cost_usd": round(cost, 4),
        "assignments": assignments,
    }, indent=2, ensure_ascii=False))

    events_out = out_path.parent / (out_path.stem + ".events.json")
    events_out.write_text(json.dumps({
        "n_events": len(final_events),
        "events": final_events,
    }, indent=2, ensure_ascii=False))

    # Save raw response for debugging
    raw_out = out_path.parent / (out_path.stem + ".raw.txt")
    raw_out.write_text(response, encoding="utf-8")

    print(f"\nDone: {out_path.name}, {events_out.name}, {raw_out.name}", flush=True)


if __name__ == "__main__":
    main()
