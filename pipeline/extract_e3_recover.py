#!/usr/bin/env python3
"""Recovery extraction for the 23 docs that failed in the canonical run.

Two failure modes:
  - 3 docs truncated at Sonnet's 64k cap → re-extract with Opus 4.7 at 128k.
  - 20 docs with unescaped double-quotes inside JSON string values →
    re-extract with Sonnet 4.6 + an explicit JSON-escape instruction.

Submits one mixed-model batch (Anthropic batches API supports per-request
model). Reuses extract_e3.py's catalogue join, metadata stamping, output
schema.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import anthropic

from pipeline.extract_e3 import (
    ROOT, BATCH_PRICE_INPUT_PER_M, BATCH_PRICE_OUTPUT_PER_M,
    load_domain_yaml, load_manifest, build_marker_index, derive_md_path,
    build_metadata_for_record, parse_json_output, render_prompt,
    wait_for_batch,
)

# Sonnet 4.6 pricing (batch)
SONNET_IN = 1.50
SONNET_OUT = 7.50
# Opus 4.7 pricing (batch — 50% off sync $15/$75)
OPUS_IN = 7.50
OPUS_OUT = 37.50

# The escape-failure addendum, appended to the prompt for Sonnet retries
JSON_ESCAPE_ADDENDUM = """

# Critical JSON escaping requirement

The output must be valid JSON. Within every string value (narrative,
lesson, evidence, intervention, etc.), escape every literal double-quote
character as \\". Never emit a literal unescaped " inside a string value.
For example, write \\"free\\" cooling rather than "free" cooling. This
applies to all double-quotes that appear within source-text quotations,
named entities in scare-quotes, technical terms in quotes, and any other
embedded quotation."""


def doc_seq_for(doc_id: str) -> int:
    """doc_NNNN -> NNNN (int)."""
    return int(doc_id.replace("doc_", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="arena")
    ap.add_argument("--truncated", nargs="+", default=["doc_0326", "doc_0562", "doc_1388"],
                    help="Docs that hit max_tokens — re-extract with Opus 4.7 @ 128k")
    ap.add_argument("--escape-failures", nargs="+",
                    default=[
                        "doc_0102", "doc_0262", "doc_0319", "doc_0332", "doc_0500",
                        "doc_0503", "doc_0504", "doc_0505", "doc_0541", "doc_0550",
                        "doc_0565", "doc_0599", "doc_0627", "doc_0678", "doc_0705",
                        "doc_0720", "doc_0749", "doc_0805", "doc_0838", "doc_1387",
                    ],
                    help="Docs that produced unescaped quotes — re-extract with Sonnet @ 64k + escape addendum")
    ap.add_argument("--retrieve", default=None,
                    help="Skip submission, retrieve+process existing batch_id")
    ap.add_argument("--poll-interval", type=int, default=30)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    dyaml = load_domain_yaml(args.domain)
    rows, cat_cfg = load_manifest(args.domain, dyaml)
    rows.sort(key=lambda r: (r.get("local_path") or "").strip())

    marker_idx = build_marker_index(ROOT / "corpora" / args.domain / "marker_output")

    out_dir = Path(args.output_dir) if args.output_dir else (
        ROOT / "corpora" / args.domain / "output" / "per_doc"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_template = (ROOT / "domains" / args.domain / "prompts" / "extract.md").read_text()
    prefix_root = dyaml.get("record_id_prefix", "REC")

    # Build target list — for each requested doc_id, find its row and md_path
    doc_targets = {}
    for spec, model, max_tokens, prompt_suffix in [
        (args.truncated, "claude-opus-4-7", 128000, ""),
        (args.escape_failures, "claude-sonnet-4-6", 64000, JSON_ESCAPE_ADDENDUM),
    ]:
        for doc_id in spec:
            seq = doc_seq_for(doc_id)
            if seq < 1 or seq > len(rows):
                print(f"  WARN: doc_id {doc_id} out of range", file=sys.stderr)
                continue
            row = rows[seq - 1]
            md_path = derive_md_path(row, marker_idx, cat_cfg)
            if not md_path:
                print(f"  WARN: no marker md for {doc_id}", file=sys.stderr)
                continue
            doc_targets[doc_id] = {
                "row": row, "md_path": md_path, "seq": seq,
                "model": model, "max_tokens": max_tokens,
                "prompt_suffix": prompt_suffix,
            }

    print(f"recovery targets: {len(doc_targets)}")
    for doc_id, t in sorted(doc_targets.items()):
        print(f"  {doc_id} -> {t['model']} max={t['max_tokens']}")

    # Build batch requests
    from anthropic.types.messages.batch_create_params import Request

    requests = []
    for doc_id, t in sorted(doc_targets.items()):
        seq = t["seq"]
        title = t["row"].get(cat_cfg.get("title_field", "Title"), "").strip()
        text = Path(t["md_path"]).read_text()
        prefix = f"{prefix_root}-{seq:04d}"
        prompt = render_prompt(prompt_template, prefix, title, text) + t["prompt_suffix"]
        params = {
            "model": t["model"],
            "max_tokens": t["max_tokens"],
            "messages": [{"role": "user", "content": prompt}],
        }
        # Opus 4.7 deprecates the temperature param; only set it for Sonnet
        if not t["model"].startswith("claude-opus"):
            params["temperature"] = 0
        requests.append(Request(custom_id=doc_id, params=params))

    client = anthropic.Anthropic()

    if args.retrieve:
        batch_id = args.retrieve
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status != "ended":
            wait_for_batch(client, batch_id, poll_interval=args.poll_interval)
    else:
        if not requests:
            print("no recovery targets; exiting")
            return
        print(f"\nsubmitting recovery batch with {len(requests)} requests...")
        batch = client.messages.batches.create(requests=requests)
        print(f"batch_id: {batch.id}")
        (out_dir.parent / "batch_id_recover.txt").write_text(batch.id)
        wait_for_batch(client, batch.id, poll_interval=args.poll_interval)
        batch_id = batch.id

    # Process results
    n_ok = n_fail = 0
    total_in = total_out = total_recs = 0
    cost_total = 0.0
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        target = doc_targets.get(custom_id)
        if target is None:
            print(f"  WARN: result for unknown {custom_id}", file=sys.stderr)
            continue
        if result.result.type == "errored":
            print(f"  [{custom_id}] ERROR: {result.result.error}")
            n_fail += 1
            continue
        msg = result.result.message
        raw = "".join(b.text for b in msg.content if b.type == "text")
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        finish_reason = getattr(msg, "stop_reason", None)
        truncated = (finish_reason in ("max_tokens", "length")
                     or out_t >= target["max_tokens"] - 1000)

        records, parse_method = parse_json_output(raw)
        if parse_method == "failed":
            (out_dir / f"{custom_id}.raw.txt").write_text(raw)
            (out_dir / f"{custom_id}.meta.json").write_text(json.dumps({
                "stop_reason": finish_reason, "input_tokens": in_t,
                "output_tokens": out_t, "truncated": truncated,
                "model": target["model"], "recovery_attempt": True,
            }))
            print(f"  [{custom_id}] PARSE STILL FAILED  stop={finish_reason} out={out_t}")
            n_fail += 1
            continue

        # Success — stamp metadata and write
        prefix = f"{prefix_root}-{target['seq']:04d}"
        meta = build_metadata_for_record(target["row"], cat_cfg, dyaml)
        for j, r in enumerate(records):
            if "id" not in r or not r["id"]:
                r["id"] = f"{prefix}-{j+1:04d}"
            for k, v in meta.items():
                r.setdefault(k, v)
            r["doc_id"] = custom_id
            r["markdown_path"] = str(Path(target["md_path"]).relative_to(ROOT))

        out_path = out_dir / f"{custom_id}.json"
        out_path.write_text(json.dumps({
            "records": records,
            "_meta": {
                "stop_reason": finish_reason,
                "input_tokens": in_t, "output_tokens": out_t,
                "truncated": truncated, "model": target["model"],
                "recovery_attempt": True,
            },
        }, indent=2, ensure_ascii=False))

        # Clean up raw / meta files from the original failure
        old_raw = out_dir / f"{custom_id}.raw.txt"
        old_meta_json = out_dir / f"{custom_id}.meta.json"
        if old_raw.exists(): old_raw.unlink()
        if old_meta_json.exists(): old_meta_json.unlink()

        # Pricing
        if target["model"].startswith("claude-opus"):
            pin, pout = OPUS_IN, OPUS_OUT
        else:
            pin, pout = SONNET_IN, SONNET_OUT
        cost = in_t * pin / 1e6 + out_t * pout / 1e6
        cost_total += cost
        total_in += in_t; total_out += out_t; total_recs += len(records)
        n_ok += 1
        trunc_flag = "  TRUNCATED" if truncated else ""
        print(f"  [{custom_id}] ok ({target['model']})  {len(records):3d} recs  "
              f"in={in_t} out={out_t}  ${cost:.3f}{trunc_flag}")

    print(f"\n=== recovery summary ===")
    print(f"docs: {n_ok} ok, {n_fail} fail")
    print(f"records added: {total_recs}")
    print(f"tokens: in={total_in:,} out={total_out:,}  cost ${cost_total:.2f} (batch pricing)")


if __name__ == "__main__":
    main()
