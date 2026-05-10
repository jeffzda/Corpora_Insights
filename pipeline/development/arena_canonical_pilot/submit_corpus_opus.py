#!/usr/bin/env python3
"""Submit corpus-wide record-type tagging via Anthropic Batches API.

Configuration (all validated through the pilot + 2k run + cross-version check):
- Model:    claude-opus-4-6  (1 rep — production tagging)
- Temp:     0.0 (deterministic; 4.6 supports temperature, 4.7 does not)
- Prompt:   label_record_types_v3.md  (v3, with intervention-trim)
- Format:   full JSON output  (per format-compression study)
- Trim:     id + narrative + evidence only  (drop intervention contamination)
- Records-per-call: 30  (matches 2k validation)
- Caching:  prompt prefix cached (saves ~$10 vs no-cache)
- Records:  ALL v1 per_doc records (90,192 expected)

Why Opus 4.6 + temp=0 (vs Opus 4.7 default):
- Same accuracy on the 44-record hand-adjudicated mechanism set (28/44 = 64%)
- Higher within-rep stability (0.98-0.99 vs 0.95-0.99 across axes)
- Deterministic — re-runs reproduce; methodology-paper rigour
- Same pricing ($5/$25 per M tokens)

Usage:
  python3 submit_corpus_opus.py --dry-run
  python3 submit_corpus_opus.py
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[7]
V1 = ROOT / "corpora/arena/output/per_doc"
PILOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PILOT / "code" / "label_record_types_v3.md"
BATCH_INFO_PATH = PILOT / "code" / "batch_corpus_opus_info.json"
RECORD_LIST_PATH = PILOT / "code" / "corpus_records.json"
RECORDS_PER_CALL = 30
MAX_TOKENS = 128_000  # standing rule: never cap max_tokens below model ceiling
MODEL = "claude-opus-4-6"
TEMPERATURE = 0.0


def trim(rec):
    out = {"id": rec["id"]}
    if rec.get("narrative"): out["narrative"] = rec["narrative"]
    if rec.get("evidence"):  out["evidence"]  = rec["evidence"]
    return out


def load_corpus():
    """Load all v1 records sorted deterministically by id."""
    if RECORD_LIST_PATH.exists():
        return json.load(open(RECORD_LIST_PATH))
    records = []
    for f in sorted(V1.glob("*.json")):
        d = json.load(open(f))
        for rec in d.get("records", []):
            records.append(trim(rec))
    records.sort(key=lambda r: r["id"])
    RECORD_LIST_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    print(f"Built corpus record list: {len(records):,} records → {RECORD_LIST_PATH}")
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="Generate requests + report cost without submitting")
    args = ap.parse_args()

    records = load_corpus()
    print(f"Total records to tag: {len(records):,}")

    template = PROMPT_PATH.read_text()
    placeholder = "[Records appended by the orchestrating script]"
    if placeholder not in template:
        raise SystemExit(f"Prompt template missing placeholder: {placeholder!r}")
    prefix, suffix = template.split(placeholder, 1)
    print(f"Prompt: {PROMPT_PATH.name}  (cached prefix: {len(prefix)} chars; suffix: {len(suffix)} chars)")

    requests = []
    n_calls = (len(records) + RECORDS_PER_CALL - 1) // RECORDS_PER_CALL
    for bi in range(0, len(records), RECORDS_PER_CALL):
        batch = records[bi:bi + RECORDS_PER_CALL]
        records_block = json.dumps(batch, indent=2, ensure_ascii=False)
        # Build content as two blocks: cached prefix, then fresh records suffix
        # The fresh block also includes the prompt-template suffix (typically empty/whitespace)
        cached_text = prefix
        fresh_text = f"```json\n{records_block}\n```{suffix}"
        cid = f"{MODEL}__rep1__batch{bi // RECORDS_PER_CALL:05d}"
        params = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": cached_text,
                     "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": fresh_text},
                ],
            }],
        }
        requests.append({"custom_id": cid, "params": params})

    print(f"\nGenerated {len(requests):,} batch requests ({n_calls} expected)")

    # Cost projection from observed 2k Opus per-record (273 in / 98 out)
    OBS_IN_PER = 273
    OBS_OUT_PER = 98
    in_total = len(records) * OBS_IN_PER
    out_total = len(records) * OBS_OUT_PER
    sync = in_total/1e6*5.0 + out_total/1e6*25.0
    batch_no_cache = in_total/1e6*2.50 + out_total/1e6*12.50
    # With caching (template ~1518 tok cached once + ~3000 reads)
    TEMPLATE_TOK = 1518
    fresh_in_total = max(0, in_total - n_calls * TEMPLATE_TOK)
    cached_writes = TEMPLATE_TOK
    cached_reads = (n_calls - 1) * TEMPLATE_TOK
    batch_cached = (fresh_in_total/1e6*2.50
                     + cached_writes/1e6*3.125
                     + cached_reads/1e6*0.25
                     + out_total/1e6*12.50)
    print(f"\nCost projection (90,192 records):")
    print(f"  Sync:                          ${sync:>7.2f}")
    print(f"  Batch API (no cache):          ${batch_no_cache:>7.2f}")
    print(f"  Batch API + cache (this run):  ${batch_cached:>7.2f}")

    # Show first request structure for verification
    print(f"\nFirst request preview:")
    r0 = requests[0]
    print(f"  custom_id: {r0['custom_id']}")
    print(f"  model:     {r0['params']['model']}")
    print(f"  max_tok:   {r0['params']['max_tokens']}")
    print(f"  has temp:  {'temperature' in r0['params']}")
    print(f"  content blocks: {len(r0['params']['messages'][0]['content'])}")
    for i, b in enumerate(r0['params']['messages'][0]['content']):
        cc = b.get('cache_control')
        print(f"    block {i}: {len(b['text'])} chars  cache_control={cc}")

    if args.dry_run:
        print(f"\nDry-run; NOT submitted.")
        return

    print(f"\nSubmitting {len(requests):,} requests to Anthropic Batches API...")
    client = anthropic.Anthropic()
    started = time.time()
    batch = client.messages.batches.create(requests=requests)
    print(f"\nBatch submitted in {time.time()-started:.1f}s")
    print(f"  batch.id   = {batch.id}")
    print(f"  status     = {batch.processing_status}")
    print(f"  counts     = {batch.request_counts}")
    print(f"  expires_at = {batch.expires_at}")

    info = {
        "batch_id": batch.id,
        "n_requests": len(requests),
        "model": MODEL,
        "n_records": len(records),
        "records_per_call": RECORDS_PER_CALL,
        "prompt_path": str(PROMPT_PATH),
        "submitted_at": time.time(),
    }
    BATCH_INFO_PATH.write_text(json.dumps(info, indent=2))
    print(f"\nSaved batch info → {BATCH_INFO_PATH}")
    print(f"Use poll_corpus_opus.py to check status / download results.")


if __name__ == "__main__":
    main()
