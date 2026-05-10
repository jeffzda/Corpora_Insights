#!/usr/bin/env python3
"""Phase 4f — third-pass classification of true singletons against the final catalogue.

Why this pass exists:
  Script 14 ran sequential chunks. A record placed as singleton in chunk 5 was
  classified against catalogue = 797 (sweep) + clusters formed in chunks 1..4.
  But chunks 5..19 went on to create ~150-200 more clusters. A singleton from
  chunk 5 might match a cluster created in chunk 14 — same catalogue-immaturity
  effect we addressed for the original sweep with the reclassify pass (script 13).

This script runs the symmetric operation: Pass 1 only (batched + neutral, the
2x2 winner) on the 2,240 true singletons against the matured 1,048-cluster
catalogue.

No Pass 2: if a record didn't anchor a cluster during the residual run's Pass 2,
it's not going to in a single re-run pass. (Could be done in a future iteration
that re-runs Pass 2 on a combined residual pool, but the marginal yield would
be small.)

Cost estimate: ~11 batches × ~$0.32 = ~$3.50 sync, ~13 min wall.
Expected yield: 10-20% recovery (~225-450 records) — combination of
batch-composition sensitivity (~8%) plus catalogue-immaturity-within-residual.
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
RESIDUAL_DIR = SWEEP_DIR / 'residual'
RES_ASSIGNMENTS = RESIDUAL_DIR / 'residual_assignments.jsonl'
WORKING_CATALOGUE = RESIDUAL_DIR / 'catalogue_after_residual.json'

THIRD_DIR = SWEEP_DIR / 'third_pass'
THIRD_DIR.mkdir(exist_ok=True)
ASSIGN_OUT = THIRD_DIR / 'third_pass_assignments.jsonl'
RESIDUAL_SINGLETONS_OUT = THIRD_DIR / 'final_singletons.json'
META_OUT = THIRD_DIR / 'meta.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-size', type=int, default=200)
    ap.add_argument('--seed', type=int, default=2026)
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    catalogue = json.load(open(WORKING_CATALOGUE))['clusters']
    valid_ids = {c['cluster_id'] for c in catalogue}
    print(f"  matured catalogue: {len(catalogue)} clusters", flush=True)

    # Pull singleton record_ids from residual_assignments
    singletons = []
    for line in open(RES_ASSIGNMENTS):
        rec = json.loads(line)
        if rec.get('status') == 'true_singleton':
            singletons.append(rec['record_id'])
    print(f"  singletons from residual run: {len(singletons):,}", flush=True)

    # Resume support
    already = set()
    if ASSIGN_OUT.exists():
        for line in open(ASSIGN_OUT):
            try:
                rec = json.loads(line)
                if rec.get('cluster_id') is not None:
                    already.add(rec['record_id'])
            except: pass
        print(f"  resume: skipping {len(already):,} already-processed", flush=True)

    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    todo = [rid for rid in singletons if rid not in already and rid in rid_to_record]
    if not todo:
        print("Nothing to do.")
        return
    rng = random.Random(args.seed)
    rng.shuffle(todo)
    print(f"  to process: {len(todo):,}", flush=True)

    client = anthropic.Anthropic()
    out_f = open(ASSIGN_OUT, 'a')
    started = time.time()
    cum_in = cum_out = cum_cost = 0.0
    n_classified = n_singleton = 0

    n_batches = (len(todo) + args.batch_size - 1) // args.batch_size
    for batch_i in range(n_batches):
        ids = todo[batch_i*args.batch_size:(batch_i+1)*args.batch_size]
        records = [rid_to_record[rid] for rid in ids]
        prompt = p12.build_neutral_batched_prompt(catalogue, records)
        t0 = time.time()
        text, msg = p06.stream_call(client, prompt, raw_path=None,
                                       label=f'batch{batch_i+1}/{n_batches}')
        wall = time.time() - t0
        parsed = p06.parse_json_tolerant(text)
        raw_assigns = parsed.get('assignments') or parsed.get('_recovered') or []
        rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assigns
                      if isinstance(a, dict) and 'record_id' in a}

        b_clf = b_sing = 0
        for r in records:
            cid = rid_to_cid.get(r['record_id'], 'orphan')
            if cid != 'orphan' and cid not in valid_ids:
                cid = 'orphan'
            if cid == 'orphan':
                b_sing += 1
            else:
                b_clf += 1
            out_f.write(json.dumps({
                'record_id': r['record_id'], 'cluster_id': cid,
                'batch': batch_i+1,
            }, ensure_ascii=False) + '\n')
        out_f.flush()

        in_t = msg.usage.input_tokens; out_t = msg.usage.output_tokens
        cost = in_t/1e6*3 + out_t/1e6*15
        cum_in += in_t; cum_out += out_t; cum_cost += cost
        n_classified += b_clf; n_singleton += b_sing
        print(f"  batch {batch_i+1}/{n_batches}: {b_clf} classified, {b_sing} singleton  "
              f"{in_t:,}in/{out_t:,}out  ${cost:.3f}  {wall:.0f}s  "
              f"cumulative ${cum_cost:.2f}", flush=True)

    out_f.close()

    # Final singletons list
    final_sing = []
    for line in open(ASSIGN_OUT):
        rec = json.loads(line)
        if rec.get('cluster_id') == 'orphan':
            final_sing.append(rec['record_id'])
    RESIDUAL_SINGLETONS_OUT.write_text(json.dumps(sorted(set(final_sing)), indent=2))

    META_OUT.write_text(json.dumps({
        'n_processed': len(todo),
        'n_classified': n_classified,
        'n_singleton': n_singleton,
        'classification_rate': round(n_classified/max(len(todo),1), 3),
        'total_input_tokens': cum_in,
        'total_output_tokens': cum_out,
        'cost_sync': round(cum_cost, 3),
        'wall_seconds': round(time.time()-started, 1),
        'catalogue_size': len(catalogue),
    }, indent=2))

    print(f"\n=== THIRD-PASS DONE ===")
    print(f"  Singletons processed: {len(todo):,}")
    print(f"  Classified to existing cluster: {n_classified:,} "
          f"({100*n_classified/max(len(todo),1):.1f}%)")
    print(f"  Final true singletons: {n_singleton:,} "
          f"({100*n_singleton/max(len(todo),1):.1f}%)")
    print(f"  Cost: ${cum_cost:.2f} sync")
    print(f"  Wall: {(time.time()-started)/60:.1f} min")


if __name__ == "__main__":
    main()
