#!/usr/bin/env python3
"""Phase 4d — pending-pile reclassify (batched + neutral prompt).

Re-classifies the 6,034 records currently in pending_singletons.json against
the matured 797-cluster catalogue using the Arm D winning combination:
  - batched 200-record Pass 1
  - neutral matter-of-fact prompt (no defensive force-fit warning)
  - Sonnet 4.6, temperature 0

Records that classify successfully are appended to a fresh assignments file
without modifying the existing corpus_assignments.jsonl. Records that don't
classify are written to residual_orphans.json for one final combinatorial
Pass 2 (handled by a follow-up script).

Inputs:
  output/sweep/cluster_catalogue.json  (final 797 clusters, frozen)
  output/sweep/pending_singletons.json (6,034 record_ids)
  output/filter_input.jsonl            (record metadata)

Outputs (in output/sweep/reclassify/):
  reclassified_assignments.jsonl  — one row per processed record
  residual_orphans.json           — records that stayed orphan
  meta.json                       — cost, batch stats

Cost estimate: 31 batches × ~$0.20 = ~$6 sync. Wall ~30 min.
"""
import argparse
import json
import random
import time
from pathlib import Path

import anthropic

import importlib.util
_06_path = Path(__file__).resolve().parent / '06_classify_and_cluster_orphans.py'
_spec = importlib.util.spec_from_file_location('p06', _06_path)
p06 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p06)
_12_path = Path(__file__).resolve().parent / '12_batched_neutral_test.py'
_spec = importlib.util.spec_from_file_location('p12', _12_path)
p12 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p12)

OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
SWEEP_DIR = OUT_DIR / 'sweep'
INPUT = OUT_DIR / 'filter_input.jsonl'
CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
PENDING = SWEEP_DIR / 'pending_singletons.json'

RECLASS_DIR = SWEEP_DIR / 'reclassify'
RECLASS_DIR.mkdir(exist_ok=True)
ASSIGN_OUT = RECLASS_DIR / 'reclassified_assignments.jsonl'
RESIDUAL_OUT = RECLASS_DIR / 'residual_orphans.json'
META_OUT = RECLASS_DIR / 'meta.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-size', type=int, default=200)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--limit', type=int, default=None,
                    help='Cap total records (for testing)')
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    valid_ids = {c['cluster_id'] for c in catalogue}
    pending_ids = list(json.load(open(PENDING)))
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    print(f"  catalogue: {len(catalogue)} clusters", flush=True)
    print(f"  pending: {len(pending_ids):,} records", flush=True)

    # Resume support
    already = set()
    if ASSIGN_OUT.exists():
        for line in open(ASSIGN_OUT):
            try:
                rec = json.loads(line)
                if rec.get('cluster_id') is not None:
                    already.add(rec['record_id'])
            except: pass
        print(f"  resume: skipping {len(already):,} already-classified", flush=True)

    todo = [rid for rid in pending_ids if rid not in already and rid in rid_to_record]
    print(f"  to process: {len(todo):,}", flush=True)
    if args.limit:
        todo = todo[:args.limit]
        print(f"  --limit {args.limit}: trimmed to {len(todo)}", flush=True)
    if not todo:
        print("Nothing to do.")
        return

    # Shuffle for batch-mix uniformity
    rng = random.Random(args.seed)
    rng.shuffle(todo)

    client = anthropic.Anthropic()
    started = time.time()
    cum_in = cum_out = cum_cost = 0.0
    n_classified = n_orphan = n_invalid = 0
    out_f = open(ASSIGN_OUT, 'a')

    n_batches = (len(todo) + args.batch_size - 1) // args.batch_size
    for batch_i in range(n_batches):
        ids = todo[batch_i*args.batch_size:(batch_i+1)*args.batch_size]
        records = [rid_to_record[rid] for rid in ids]

        prompt = p12.build_neutral_batched_prompt(catalogue, records)
        prompt_size = len(prompt)
        t0 = time.time()
        text, msg = p06.stream_call(client, prompt, raw_path=None,
                                       label=f'batch{batch_i+1}/{n_batches}')
        wall = time.time() - t0
        parsed = p06.parse_json_tolerant(text)
        raw_assigns = parsed.get('assignments') or parsed.get('_recovered') or []
        rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assigns
                      if isinstance(a, dict) and 'record_id' in a}

        b_classified = b_orphan = b_invalid = 0
        for r in records:
            cid = rid_to_cid.get(r['record_id'], 'orphan')
            invalid = (cid != 'orphan' and cid not in valid_ids)
            if invalid:
                cid = 'orphan'; b_invalid += 1
            if cid == 'orphan':
                b_orphan += 1
            else:
                b_classified += 1
            row = {'record_id': r['record_id'], 'cluster_id': cid,
                   'batch': batch_i+1, 'method': 'batched_neutral'}
            out_f.write(json.dumps(row, ensure_ascii=False) + '\n')
        out_f.flush()

        in_tok = msg.usage.input_tokens
        out_tok = msg.usage.output_tokens
        cost = in_tok/1e6*3 + out_tok/1e6*15
        cum_in += in_tok; cum_out += out_tok; cum_cost += cost
        n_classified += b_classified; n_orphan += b_orphan; n_invalid += b_invalid

        elapsed = time.time() - started
        rate = (batch_i+1)*args.batch_size / elapsed
        print(f"  batch {batch_i+1}/{n_batches}: {b_classified} classified, "
              f"{b_orphan} orphan ({b_invalid} invalid→orphan)  "
              f"{in_tok:,}in/{out_tok:,}out  ${cost:.3f}  {wall:.0f}s  "
              f"cumulative ${cum_cost:.2f}", flush=True)

    out_f.close()

    # Emit residual list (records that classified as orphan)
    residuals = []
    for line in open(ASSIGN_OUT):
        rec = json.loads(line)
        if rec.get('cluster_id') == 'orphan':
            residuals.append(rec['record_id'])
    RESIDUAL_OUT.write_text(json.dumps(sorted(set(residuals)), indent=2))

    META_OUT.write_text(json.dumps({
        'n_records_processed': len(todo),
        'n_classified': n_classified,
        'n_orphan': n_orphan,
        'n_invalid_assignments_coerced_to_orphan': n_invalid,
        'classification_rate': round(n_classified/max(len(todo),1), 3),
        'orphan_rate': round(n_orphan/max(len(todo),1), 3),
        'total_input_tokens': cum_in,
        'total_output_tokens': cum_out,
        'total_cost_sync': round(cum_cost, 3),
        'wall_seconds': round(time.time()-started, 1),
        'method': 'batched_neutral',
        'batch_size': args.batch_size,
        'catalogue_size': len(catalogue),
    }, indent=2))

    print(f"\n=== DONE ===")
    print(f"  Processed: {len(todo):,}")
    print(f"  Classified: {n_classified:,} ({100*n_classified/max(len(todo),1):.1f}%)")
    print(f"  Orphan: {n_orphan:,} ({100*n_orphan/max(len(todo),1):.1f}%)")
    print(f"  Cost: ${cum_cost:.2f} sync")
    print(f"  Wall: {(time.time()-started)/60:.1f} min")
    print(f"  Residuals written to {RESIDUAL_OUT}")


if __name__ == "__main__":
    main()
