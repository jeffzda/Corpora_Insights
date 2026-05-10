#!/usr/bin/env python3
"""Poll / download / parse the corpus-wide Opus 4.6 tagging batch.

Usage:
  python3 poll_corpus_opus.py             # status only
  python3 poll_corpus_opus.py --download  # fetch + parse + write tags.json

Outputs:
  outputs/opus-4-6-v3prompt-corpus/rep1/raw_responses.json   (audit trail)
  outputs/opus-4-6-v3prompt-corpus/rep1/tags.json            (90k tags)
  outputs/opus-4-6-v3prompt-corpus/rep1/missing_records.json (records dropped by model — for re-tagging)

Plus a canonical copy at:
  output/record_type_tags/opus-4-6-v3-temp0/tags.json
"""
import argparse
import json
import re
import time
from pathlib import Path
from collections import defaultdict

import anthropic

PILOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[7]
BATCH_INFO_PATH = PILOT / "code" / "batch_corpus_opus_info.json"
RECORDS_PATH = PILOT / "code" / "corpus_records.json"
RUN_OUT = PILOT / "outputs" / "opus-4-6-v3prompt-corpus" / "rep1"
CANONICAL_OUT = ROOT / "corpora/arena/output/record_type_tags/opus-4-6-v3-temp0"


def parse_one(text):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        first, last = body.find("{"), body.rfind("}")
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: return {}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()

    if not BATCH_INFO_PATH.exists():
        raise SystemExit(f"No batch info — submit first.")
    info = json.load(open(BATCH_INFO_PATH))
    print(f"Batch: {info['batch_id']}")
    print(f"Submitted: {time.ctime(info['submitted_at'])}")

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(info["batch_id"])
    print(f"\nstatus: {batch.processing_status}")
    print(f"counts: {batch.request_counts}")
    if batch.ended_at: print(f"ended:  {batch.ended_at}")

    if not args.download:
        if batch.processing_status == "ended":
            print("\n→ batch ended. Re-run with --download to fetch.")
        return
    if batch.processing_status != "ended":
        raise SystemExit(f"Batch not ended (status={batch.processing_status})")

    print("\nStreaming results...")
    batches_data = []
    n_ok = n_err = 0
    for result in client.messages.batches.results(info["batch_id"]):
        cid = result.custom_id
        try:
            _, _, batch_part = cid.split("__")
            bi = int(batch_part.replace("batch", ""))
        except Exception:
            continue
        if result.result.type != "succeeded":
            n_err += 1
            print(f"  ERROR {cid}: {result.result.type}")
            continue
        msg = result.result.message
        text = msg.content[0].text if msg.content and msg.content[0].type == "text" else ""
        batches_data.append({
            "batch_idx": bi, "text": text,
            "input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
        })
        n_ok += 1
    print(f"  succeeded: {n_ok}, errored: {n_err}")
    batches_data.sort(key=lambda b: b["batch_idx"])

    RUN_OUT.mkdir(parents=True, exist_ok=True)
    (RUN_OUT/"raw_responses.json").write_text(json.dumps(batches_data, indent=2, ensure_ascii=False))

    # Parse to tags
    all_tags = {}
    parse_errors = []
    tot_in = tot_out = 0
    for b in batches_data:
        parsed = parse_one(b["text"])
        for asn in parsed.get("assignments", []):
            if "id" in asn:
                all_tags[asn["id"]] = asn
        if not parsed.get("assignments"):
            parse_errors.append(b["batch_idx"])
        tot_in += b["input_tokens"]; tot_out += b["output_tokens"]

    # Detect missing records (the model sometimes drops a few from a batch)
    expected_records = json.load(open(RECORDS_PATH))
    expected_ids = {r["id"] for r in expected_records}
    missing = sorted(expected_ids - set(all_tags.keys()))

    cost_batch = tot_in/1e6*2.50 + tot_out/1e6*12.50
    payload = {
        "model": info.get("model", "claude-opus-4-6"),
        "n_records_tagged": len(all_tags),
        "n_records_expected": len(expected_ids),
        "n_records_missing": len(missing),
        "n_batches": len(batches_data),
        "n_parse_errors": len(parse_errors),
        "input_tokens": tot_in,
        "output_tokens": tot_out,
        "cost_usd_batch": round(cost_batch, 4),
        "tags": all_tags,
    }
    (RUN_OUT/"tags.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (RUN_OUT/"missing_records.json").write_text(json.dumps(missing, indent=2))

    print(f"\nTagged {len(all_tags):,} / {len(expected_ids):,} records")
    print(f"  missing: {len(missing)} ({len(missing)/len(expected_ids)*100:.2f}%)")
    print(f"  parse errors: {len(parse_errors)} batches")
    print(f"  tokens: {tot_in:,} in / {tot_out:,} out")
    print(f"  cost (batch): ${cost_batch:.2f}")
    print(f"\nWrote:")
    print(f"  {RUN_OUT/'tags.json'}")
    print(f"  {RUN_OUT/'raw_responses.json'}")
    print(f"  {RUN_OUT/'missing_records.json'}")

    # Canonical copy (just tags + minimal metadata, no raw responses)
    CANONICAL_OUT.mkdir(parents=True, exist_ok=True)
    canonical = {
        "model": payload["model"],
        "prompt": "label_record_types_v3.md",
        "temperature": 0.0,
        "n_records_tagged": payload["n_records_tagged"],
        "n_records_missing": payload["n_records_missing"],
        "tags": all_tags,
    }
    (CANONICAL_OUT/"tags.json").write_text(json.dumps(canonical, indent=2, ensure_ascii=False))
    print(f"  {CANONICAL_OUT/'tags.json'}  (canonical copy for downstream consumers)")

    if missing:
        print(f"\nNOTE: {len(missing)} records were dropped by the model. "
              f"To re-tag them, see missing_records.json and re-run on the subset.")


if __name__ == "__main__":
    main()
