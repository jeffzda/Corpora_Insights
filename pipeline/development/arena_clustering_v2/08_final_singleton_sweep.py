#!/usr/bin/env python3
"""Phase 4d — final per-record cached classification of pending singletons.

Inputs:
  - cluster_catalogue.json: the matured catalogue from the iterative sweep (~797 clusters)
  - pending_singletons.json: ~6,034 records that didn't form ≥3 clusters during the sweep
  - seed_response_raw.txt: ~600 seed-pass singletons held out for this final sweep
  - filter_input.jsonl: full record metadata

Method (cascade Stage 2):
  - Each record gets a dedicated Sonnet call against the maximal frozen catalogue
  - Catalogue is at the prompt prefix with prompt-caching enabled (ephemeral, 5min TTL)
  - Concurrency ~30 so cache stays warm across calls
  - Output schema: a single cluster_id from the catalogue, OR "orphan"
  - Save-as-we-go (one line per record into final_assignments.jsonl)

Why per-record instead of batched-200:
  - Catalogue is frozen → cache stays valid for the entire pass
  - No combinatorial reasoning required (pure classification)
  - Each record gets dedicated model attention (no 200-record dilution)
  - This pass is the one cited in the methodology paper for completeness/accuracy

Cost estimate at 6,634 records and ~10k cached catalogue tokens:
  ~$0.0038/call → ~$25 sync, ~25min wall at concurrency 30.

Resumable: existing entries in final_assignments.jsonl are skipped on restart.
"""
import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
SEED_RAW = OUT_DIR / 'seed_response_raw.txt'
SEED_CATALOGUE = OUT_DIR / 'cluster_catalogue.json'  # original seed catalogue (45)
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'  # final matured (797)
PENDING = SWEEP_DIR / 'pending_singletons.json'
ASSIGNMENTS_OUT = SWEEP_DIR / 'final_assignments.jsonl'
META_OUT = SWEEP_DIR / 'final_assignments_meta.json'

PROMPT_HEADER = """You are classifying ARENA renewable-energy project records against a frozen catalogue of failure-mode clusters.

Decide whether the record's causal failure mechanism matches one cluster from the catalogue. If it does, return that cluster_id. If no cluster's mechanism captures this record, return "orphan".

CRITICAL: Match on MECHANISM (the causal pathway), not on:
- Project name, equipment vocabulary, technology label
- Surface text similarity
- Topic similarity (e.g. both are about voltage doesn't mean same mechanism)

A record matches a cluster only if it describes the SAME causal pathway.

Do NOT force-fit. If no cluster captures this record's mechanism, return "orphan" — it is better to be honest than to assign incorrectly.

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

PROMPT_FOOTER_TEMPLATE = """\

# RECORD TO CLASSIFY

## {rid}  [axes: {axes}; v: {valence}]
narrative: {narrative}
{evidence_line}

# OUTPUT FORMAT — STRICT

Return JSON only. The first character must be `{{` and the last must be `}}`. No prose.

Schema:
{{"cluster_id": "c042"}}     ← any cluster_id from the catalogue
or
{{"cluster_id": "orphan"}}   ← if no catalogue cluster captures this record's mechanism"""


def build_catalogue_block(catalogue):
    lines = []
    for c in catalogue:
        lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        lines.append(f"  mechanism: {c['mechanism_signature']}")
    return PROMPT_HEADER + ''.join(lines)


def build_record_text(r):
    rid = r['record_id']
    narr = (r.get('narrative') or '').strip()
    evi = (r.get('evidence') or '').strip()
    axes = []
    for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
        if r.get(ax) == 'yes':
            axes.append(ax[3:])
    evidence_line = f"evidence: {evi[:600]}" if (evi and evi != narr) else ""
    return PROMPT_FOOTER_TEMPLATE.format(
        rid=rid, axes=','.join(axes), valence=r.get('valence',''),
        narrative=narr, evidence_line=evidence_line,
    )


def parse_response(text):
    text = text.strip()
    # Strip code fence if present
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        # Try to find {"cluster_id": "..."} substring
        m = re.search(r'\{"?cluster_id"?\s*:\s*"([^"]+)"\}', body)
        if m: return {'cluster_id': m.group(1)}
        return None


async def classify_one(client, sem, catalogue_block, record, valid_cluster_ids):
    rid = record['record_id']
    record_text = build_record_text(record)
    async with sem:
        try:
            t0 = time.time()
            resp = await client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=64,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": catalogue_block,
                         "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": record_text},
                    ]
                }],
            )
            text = resp.content[0].text if resp.content else ''
            parsed = parse_response(text)
            cid = (parsed or {}).get('cluster_id', None)
            if cid != 'orphan' and cid not in valid_cluster_ids:
                cid = 'orphan'  # defensive: model invented an id
            return {
                'record_id': rid,
                'cluster_id': cid or 'orphan',
                'input_tokens': resp.usage.input_tokens,
                'output_tokens': resp.usage.output_tokens,
                'cache_creation_input_tokens': getattr(resp.usage, 'cache_creation_input_tokens', 0),
                'cache_read_input_tokens': getattr(resp.usage, 'cache_read_input_tokens', 0),
                'wall_seconds': round(time.time()-t0, 2),
                'raw': text,
            }
        except Exception as e:
            return {'record_id': rid, 'cluster_id': None, 'error': str(e)}


async def main_async(records, catalogue_block, valid_cluster_ids, concurrency,
                      out_path, progress_every=50):
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(concurrency)
    started = time.time()
    n_done = 0
    total_in = total_out = total_cache_w = total_cache_r = 0
    errors = 0
    classified = 0
    orphan = 0

    out_f = open(out_path, 'a')
    tasks = [asyncio.create_task(classify_one(client, sem, catalogue_block, r, valid_cluster_ids))
             for r in records]
    for fut in asyncio.as_completed(tasks):
        result = await fut
        n_done += 1
        if 'error' in result:
            errors += 1
        else:
            total_in += result['input_tokens']
            total_out += result['output_tokens']
            total_cache_w += result['cache_creation_input_tokens']
            total_cache_r += result['cache_read_input_tokens']
            if result['cluster_id'] == 'orphan': orphan += 1
            elif result['cluster_id']: classified += 1
        out_f.write(json.dumps(result, ensure_ascii=False) + '\n')
        out_f.flush()
        if n_done % progress_every == 0 or n_done == len(records):
            elapsed = time.time() - started
            rate = n_done / max(elapsed, 1)
            eta = (len(records) - n_done) / max(rate, 1e-9)
            cost_estimate = (total_in/1e6)*3 + (total_out/1e6)*15 \
                            + (total_cache_w/1e6)*3.75 + (total_cache_r/1e6)*0.30
            # input_tokens already excludes cache reads in Anthropic billing; the cost above
            # estimates: in $3/M for fresh input, $15/M for output, $3.75/M for cache writes,
            # $0.30/M for cache reads. (This may double-count slightly depending on usage.)
            print(f"  [{int(elapsed)}s] {n_done}/{len(records)}  "
                  f"({rate:.1f}/s, eta {int(eta)}s)  "
                  f"classified {classified}, orphan {orphan}, errors {errors}  "
                  f"~${cost_estimate:.2f}", flush=True)
    out_f.close()
    return {
        'n_records': len(records), 'n_done': n_done,
        'classified': classified, 'orphan': orphan, 'errors': errors,
        'total_input_tokens': total_in, 'total_output_tokens': total_out,
        'cache_creation_tokens': total_cache_w, 'cache_read_tokens': total_cache_r,
        'wall_seconds': round(time.time()-started, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--concurrency', type=int, default=30)
    ap.add_argument('--limit', type=int, default=None,
                    help='Limit number of records (for testing)')
    args = ap.parse_args()

    print("Loading catalogue and records...", flush=True)
    catalogue = json.load(open(WORKING_CATALOGUE))['clusters']
    valid_cluster_ids = {c['cluster_id'] for c in catalogue}
    print(f"  catalogue: {len(catalogue)} clusters", flush=True)

    pending_ids = set(json.load(open(PENDING)))
    print(f"  pending singletons (from sweep): {len(pending_ids):,}", flush=True)

    # Seed singletons (held out from the original seed pass)
    seed_singleton_ids = set()
    if SEED_RAW.exists():
        raw = open(SEED_RAW).read()
        sm = re.search(r'```json\s*(.*?)```', raw, re.DOTALL)
        sbody = sm.group(1) if sm else raw
        try:
            sparsed = json.loads(sbody)
            seed_singleton_ids = set(sparsed.get('singletons', []))
        except: pass
    # Drop any that are now in the catalogue (they were anchor records or got picked up)
    in_cat = set()
    for c in catalogue:
        in_cat.update(c.get('supporting_record_ids') or [])
    seed_singleton_ids -= in_cat
    print(f"  seed singletons (after dedup vs catalogue): {len(seed_singleton_ids):,}", flush=True)

    target_ids = pending_ids | seed_singleton_ids
    print(f"  combined target: {len(target_ids):,}", flush=True)

    # Resume support: skip records already in final_assignments.jsonl
    already_done = set()
    if ASSIGNMENTS_OUT.exists():
        for line in open(ASSIGNMENTS_OUT):
            try:
                rec = json.loads(line)
                if rec.get('cluster_id') is not None:
                    already_done.add(rec['record_id'])
            except: pass
        print(f"  resume: skipping {len(already_done):,} already-classified records", flush=True)

    target_ids -= already_done
    print(f"  remaining to classify: {len(target_ids):,}", flush=True)

    if args.limit:
        target_ids = set(list(target_ids)[:args.limit])
        print(f"  --limit {args.limit}: trimmed to {len(target_ids)}", flush=True)

    if not target_ids:
        print("Nothing to do.")
        return

    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    records = [rid_to_record[rid] for rid in target_ids if rid in rid_to_record]
    print(f"  records resolved: {len(records):,}", flush=True)

    catalogue_block = build_catalogue_block(catalogue)
    print(f"  cached prefix: {len(catalogue_block):,} chars (~{len(catalogue_block)//4:,} tok)", flush=True)
    print(f"  concurrency: {args.concurrency}", flush=True)
    print(f"\nStarting per-record cached classification...\n", flush=True)

    summary = asyncio.run(main_async(
        records, catalogue_block, valid_cluster_ids,
        args.concurrency, ASSIGNMENTS_OUT,
    ))

    print(f"\n=== DONE ===", flush=True)
    for k, v in summary.items():
        print(f"  {k}: {v}", flush=True)
    META_OUT.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
