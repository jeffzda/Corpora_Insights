#!/usr/bin/env python3
"""Productionised 6-axis record-type tagging via Anthropic Batches API.

Canonical labelling pass for the ARENA pipeline (and generalisable to other
domains). Reads extracted records from corpora/<domain>/output/per_doc/, sends
them through Opus 4.6 with the v3 prompt at
`corpora/<domain>/canonical/prompts/label_record_types_v3.md`, and writes
tags.json under corpora/<domain>/output/record_type_tags/<model>-<temp>/.

Six axes per record (per the v3 prompt):
    is_occurrence, is_mechanism, is_specification, is_lesson, is_recommendation,
    valence (positive/neutral/negative).

Replaces the earlier `pipeline/label_axes.py` (9-axis bundled) and
`pipeline/event_type.py` (4-class realised/design/risk/contextual). Both
superseded; preserved under corpora/arena/legacy/code/pipeline/ for cold-start
reference.

Usage:
    # Submit a batch
    python -m pipeline.label_record_types --domain arena --batch submit
    # (--dry-run to inspect cost projection without submitting)

    # Check status
    python -m pipeline.label_record_types --domain arena --batch status

    # Collect results when batch completes
    python -m pipeline.label_record_types --domain arena --batch collect
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_TEMPERATURE = 0.0
RECORDS_PER_CALL = 30
MAX_TOKENS = 128_000  # standing rule: never cap below model ceiling


def model_slug(model: str, temperature: float) -> str:
    """Derive a stable folder slug from model + temperature."""
    base = model.replace("claude-", "").replace("-", "-")  # "opus-4-6"
    return f"{base}-v3-temp{int(temperature)}" if temperature == 0.0 else f"{base}-v3-temp{temperature}"


def domain_paths(domain: str, model: str, temperature: float):
    """Return paths used by the labelling pass for a given domain."""
    base = ROOT / "corpora" / domain
    slug = model_slug(model, temperature)
    return {
        "per_doc": base / "output" / "per_doc",
        "prompt": base / "canonical" / "prompts" / "label_record_types_v3.md",
        "out_dir": base / "output" / "record_type_tags" / slug,
        "batch_info": base / "output" / "record_type_tags" / slug / "batch_info.json",
        "tags": base / "output" / "record_type_tags" / slug / "tags.json",
        "raw_responses": base / "output" / "record_type_tags" / slug / "raw_responses.jsonl",
    }


def trim(rec: dict) -> dict:
    """Trim a record to the fields the v3 prompt expects."""
    out = {"id": rec["id"]}
    if rec.get("narrative"):
        out["narrative"] = rec["narrative"]
    if rec.get("evidence"):
        out["evidence"] = rec["evidence"]
    return out


def load_corpus(per_doc_dir: Path) -> list[dict]:
    """Load every record from per_doc/*.json, sorted deterministically by id."""
    if not per_doc_dir.exists():
        raise SystemExit(f"per_doc/ not found: {per_doc_dir}")
    records = []
    for f in sorted(per_doc_dir.glob("doc_*.json")):
        d = json.load(open(f))
        for rec in d.get("records", []):
            records.append(trim(rec))
    records.sort(key=lambda r: r["id"])
    return records


def load_prompt(prompt_path: Path) -> tuple[str, str]:
    """Load the v3 prompt and split it on the records placeholder."""
    if not prompt_path.exists():
        raise SystemExit(f"Prompt not found: {prompt_path}")
    template = prompt_path.read_text()
    placeholder = "[Records appended by the orchestrating script]"
    if placeholder not in template:
        raise SystemExit(f"Prompt template missing placeholder: {placeholder!r}")
    prefix, suffix = template.split(placeholder, 1)
    return prefix, suffix


def build_requests(records: list[dict], prefix: str, suffix: str,
                   model: str, temperature: float) -> list[dict]:
    """Build Batches API request list with prompt-prefix caching."""
    requests = []
    n_calls = (len(records) + RECORDS_PER_CALL - 1) // RECORDS_PER_CALL
    for bi in range(0, len(records), RECORDS_PER_CALL):
        batch = records[bi:bi + RECORDS_PER_CALL]
        records_block = json.dumps(batch, indent=2, ensure_ascii=False)
        fresh_text = f"```json\n{records_block}\n```{suffix}"
        cid = f"{model}__rep1__batch{bi // RECORDS_PER_CALL:05d}"
        params = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "temperature": temperature,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prefix,
                     "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": fresh_text},
                ],
            }],
        }
        requests.append({"custom_id": cid, "params": params})
    return requests


def cost_projection(n_records: int, n_calls: int, prefix_len_tokens: int) -> dict:
    """Project cost using observed 2k Opus per-record token rates (273 in / 98 out)."""
    OBS_IN_PER = 273
    OBS_OUT_PER = 98
    in_total = n_records * OBS_IN_PER
    out_total = n_records * OBS_OUT_PER
    sync = in_total / 1e6 * 5.0 + out_total / 1e6 * 25.0
    batch_no_cache = in_total / 1e6 * 2.50 + out_total / 1e6 * 12.50
    fresh_in = max(0, in_total - n_calls * prefix_len_tokens)
    cached_writes = prefix_len_tokens
    cached_reads = (n_calls - 1) * prefix_len_tokens
    batch_cached = (
        fresh_in / 1e6 * 2.50
        + cached_writes / 1e6 * 3.125
        + cached_reads / 1e6 * 0.25
        + out_total / 1e6 * 12.50
    )
    return {"sync": sync, "batch_no_cache": batch_no_cache, "batch_cached": batch_cached}


def cmd_submit(args):
    paths = domain_paths(args.domain, args.model, args.temperature)
    paths["out_dir"].mkdir(parents=True, exist_ok=True)

    records = load_corpus(paths["per_doc"])
    print(f"Records to tag: {len(records):,}", flush=True)

    prefix, suffix = load_prompt(paths["prompt"])
    print(f"Prompt: {paths['prompt'].relative_to(ROOT)}  "
          f"(prefix {len(prefix)} chars / suffix {len(suffix)} chars)", flush=True)

    requests = build_requests(records, prefix, suffix, args.model, args.temperature)
    n_calls = len(requests)
    print(f"Batch requests: {n_calls:,}", flush=True)

    # Rough prefix token estimate: 4 chars/token
    cost = cost_projection(len(records), n_calls, len(prefix) // 4)
    print(f"\nCost projection ({len(records):,} records):")
    print(f"  Sync:                          ${cost['sync']:>7.2f}")
    print(f"  Batch (no cache):              ${cost['batch_no_cache']:>7.2f}")
    print(f"  Batch + prefix cache:          ${cost['batch_cached']:>7.2f}")

    if args.dry_run:
        print(f"\nDry run; not submitted.", flush=True)
        return 0

    print(f"\nSubmitting {n_calls:,} requests...", flush=True)
    client = anthropic.Anthropic()
    started = time.time()
    batch = client.messages.batches.create(requests=requests)
    print(f"Submitted in {time.time() - started:.1f}s", flush=True)
    print(f"  batch.id   = {batch.id}")
    print(f"  status     = {batch.processing_status}")
    print(f"  expires_at = {batch.expires_at}")

    info = {
        "batch_id": batch.id,
        "n_requests": n_calls,
        "model": args.model,
        "temperature": args.temperature,
        "n_records": len(records),
        "records_per_call": RECORDS_PER_CALL,
        "prompt_path": str(paths["prompt"]),
        "submitted_at": time.time(),
    }
    paths["batch_info"].write_text(json.dumps(info, indent=2))
    print(f"\nSaved → {paths['batch_info'].relative_to(ROOT)}")
    return 0


def cmd_status(args):
    paths = domain_paths(args.domain, args.model, args.temperature)
    if not paths["batch_info"].exists():
        raise SystemExit(f"No batch info at {paths['batch_info']}. Submit first.")
    info = json.load(open(paths["batch_info"]))
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(info["batch_id"])
    print(f"batch_id:   {batch.id}")
    print(f"status:     {batch.processing_status}")
    print(f"counts:     {batch.request_counts}")
    return 0


def cmd_collect(args):
    paths = domain_paths(args.domain, args.model, args.temperature)
    if not paths["batch_info"].exists():
        raise SystemExit(f"No batch info at {paths['batch_info']}.")
    info = json.load(open(paths["batch_info"]))
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(info["batch_id"])
    if batch.processing_status != "ended":
        raise SystemExit(f"Batch not finished: {batch.processing_status}")

    print(f"Downloading results...", flush=True)
    raw_lines = []
    parsed_tags = {}
    n_responses = 0
    for entry in client.messages.batches.results(info["batch_id"]):
        n_responses += 1
        raw_lines.append(json.dumps(entry, default=str))
        if entry.result.type != "succeeded":
            print(f"  FAILED: {entry.custom_id} — {entry.result.type}", flush=True)
            continue
        text = entry.result.message.content[0].text
        # Strip optional JSON code fences
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  PARSE FAIL: {entry.custom_id} — {e}", flush=True)
            continue
        for assignment in parsed.get("assignments", []):
            rid = assignment.get("id")
            if rid:
                parsed_tags[rid] = assignment

    paths["raw_responses"].write_text("\n".join(raw_lines))
    print(f"Saved {n_responses} raw responses → {paths['raw_responses'].relative_to(ROOT)}")

    payload = {
        "model": info["model"],
        "prompt": Path(info["prompt_path"]).name,
        "temperature": info["temperature"],
        "n_records_tagged": len(parsed_tags),
        "n_records_missing": info["n_records"] - len(parsed_tags),
        "tags": parsed_tags,
    }
    paths["tags"].write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {len(parsed_tags):,} tags → {paths['tags'].relative_to(ROOT)}")
    if payload["n_records_missing"]:
        print(f"  WARNING: {payload['n_records_missing']:,} records missing")
    return 0


def main():
    ap = argparse.ArgumentParser(description="6-axis record-type tagging via Batches API")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--batch", choices=["submit", "status", "collect"], required=True)
    ap.add_argument("--dry-run", action="store_true",
                     help="(submit only) Inspect cost projection without submitting")
    args = ap.parse_args()

    if args.batch == "submit":
        return cmd_submit(args)
    elif args.batch == "status":
        return cmd_status(args)
    elif args.batch == "collect":
        return cmd_collect(args)


if __name__ == "__main__":
    sys.exit(main())
