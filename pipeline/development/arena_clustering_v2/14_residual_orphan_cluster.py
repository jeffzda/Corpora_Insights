#!/usr/bin/env python3
"""Phase 4e — residual orphan clustering on the post-reclassify pile.

Input: 3,412 records that stayed orphan even after the Arm-D reclassify pass.
These are genuine residuals — no good match in the 797-cluster catalogue.

The job: form any genuinely novel mechanism clusters that survive across this
residual pool, leaving the rest as true singletons.

Design (sequential chunked, mirrors the iterative sweep):
- Chunk residuals into ~180-record batches
- Per chunk:
  - Pass 1 (NEUTRAL prompt — Arm D winner): classify each chunk against the
    current catalogue (matured 797 + any clusters formed in earlier chunks
    of this run)
  - Pass 2 (defensive Pass 2 prompt — cluster formation, ≥3 threshold):
    propose new ≥3-member clusters from this chunk's residual orphans
  - New clusters are appended to the working catalogue, available to
    subsequent chunks (procurement-probity preserved: signatures stay
    immutable once published)
- Output: residual_assignments.jsonl, residual_new_clusters.json,
  catalogue_after_residual.json

Why sequential not parallel: cross-chunk records that share a novel mechanism
need to land in the same new cluster. Sequential processing (chunk N sees
clusters formed in chunks 1..N-1) ensures that. Parallel would produce
duplicate cluster-formation that requires post-hoc consolidation, which is
worse than just running sequentially.

Why ~180 record chunks: Pass 2 combinatorial reasoning loses coherence above
~250 records (we saw 600-record pool fail catastrophically earlier). 180 is
safely within the working range.

Estimate: ~19 chunks × ~$0.30 per Pass 1 + ~$0.10 per Pass 2 ≈ $8 sync,
~30 min wall.
"""
import argparse
import json
import random
import time
from collections import Counter
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
SOURCE_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
RESIDUAL_IDS = SWEEP_DIR / 'reclassify' / 'residual_orphans.json'

RES_DIR = SWEEP_DIR / 'residual'
RES_DIR.mkdir(exist_ok=True)
WORKING_CAT = RES_DIR / 'catalogue_after_residual.json'
ASSIGN_OUT = RES_DIR / 'residual_assignments.jsonl'
NEW_CLUSTERS_OUT = RES_DIR / 'residual_new_clusters.json'
STATE_OUT = RES_DIR / 'residual_state.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunk-size', type=int, default=180)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--limit-chunks', type=int, default=None,
                    help='Cap chunk count for testing')
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    catalogue = json.load(open(SOURCE_CATALOGUE))['clusters']
    print(f"  source catalogue: {len(catalogue)} clusters", flush=True)
    residual_ids = json.load(open(RESIDUAL_IDS))
    print(f"  residual orphans: {len(residual_ids):,}", flush=True)
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}

    # Determine starting next_orphan_id (continue numbering from where the sweep left off)
    max_id = 499
    for c in catalogue:
        try:
            n = int(c['cluster_id'][1:])
            if n > max_id: max_id = n
        except: pass
    next_orphan_id = max_id + 1
    print(f"  next orphan cluster id: c{next_orphan_id:03d}", flush=True)

    # Resume support
    processed = set()
    if ASSIGN_OUT.exists():
        for line in open(ASSIGN_OUT):
            try: processed.add(json.loads(line)['record_id'])
            except: pass
        print(f"  resume: skipping {len(processed):,} already-processed", flush=True)

    todo_ids = [rid for rid in residual_ids if rid not in processed and rid in rid_to_record]
    rng = random.Random(args.seed)
    rng.shuffle(todo_ids)
    print(f"  to process: {len(todo_ids):,}", flush=True)

    if not todo_ids:
        print("Nothing to do.")
        return

    n_chunks = (len(todo_ids) + args.chunk_size - 1) // args.chunk_size
    if args.limit_chunks:
        n_chunks = min(n_chunks, args.limit_chunks)
        todo_ids = todo_ids[:n_chunks * args.chunk_size]
    print(f"  chunks: {n_chunks} × ~{args.chunk_size}", flush=True)

    client = anthropic.Anthropic()
    assign_f = open(ASSIGN_OUT, 'a')
    started = time.time()
    cum_cost = 0.0
    all_new_clusters = []
    total_classified = 0
    total_into_new = 0
    total_singleton = 0

    for chunk_i in range(n_chunks):
        ids = todo_ids[chunk_i*args.chunk_size:(chunk_i+1)*args.chunk_size]
        records = [rid_to_record[rid] for rid in ids]
        t0 = time.time()
        print(f"\n=== Chunk {chunk_i+1}/{n_chunks} ({len(records)} records, "
              f"catalogue {len(catalogue)}) ===", flush=True)

        # --- Pass 1: classify against current catalogue (NEUTRAL prompt — Arm D)
        p1_prompt = p12.build_neutral_batched_prompt(catalogue, records)
        print(f"  Pass 1 prompt: {len(p1_prompt):,} chars", flush=True)
        p1_text, p1_msg = p06.stream_call(client, p1_prompt, raw_path=None,
                                            label=f'r{chunk_i+1}-p1')
        p1_parsed = p06.parse_json_tolerant(p1_text)
        raw_assigns = p1_parsed.get('assignments') or p1_parsed.get('_recovered') or []
        valid = {c['cluster_id'] for c in catalogue}
        rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assigns
                      if isinstance(a, dict) and 'record_id' in a}
        n_clf = sum(1 for r in records
                    if rid_to_cid.get(r['record_id']) in valid)
        n_orph = len(records) - n_clf
        p1_cost = p1_msg.usage.input_tokens/1e6*3 + p1_msg.usage.output_tokens/1e6*15
        print(f"  Pass 1: {n_clf} classified into existing, {n_orph} orphan; ${p1_cost:.3f}", flush=True)

        chunk_orphans = [r for r in records
                         if rid_to_cid.get(r['record_id'], 'orphan') not in valid]

        new_clusters = []
        p2_cost = 0.0
        if chunk_orphans:
            # --- Pass 2: cluster this chunk's orphans
            p2_prompt = p06.build_orphan_prompt(chunk_orphans)
            print(f"  Pass 2: clustering {len(chunk_orphans)} orphans", flush=True)
            p2_text, p2_msg = p06.stream_call(client, p2_prompt, raw_path=None,
                                                label=f'r{chunk_i+1}-p2')
            p2_parsed = p06.parse_json_tolerant(p2_text)
            proposed = p2_parsed.get('clusters') or p2_parsed.get('_recovered') or []
            orphan_pool_ids = {r['record_id'] for r in chunk_orphans}
            seen = set()
            for c in proposed:
                if not isinstance(c, dict): continue
                sup = [r for r in (c.get('supporting_record_ids') or [])
                       if r in orphan_pool_ids and r not in seen]
                if len(sup) < 3: continue
                cid = f"c{next_orphan_id:03d}"
                next_orphan_id += 1
                new_clusters.append({
                    'cluster_id': cid,
                    'canonical_name': c.get('canonical_name', ''),
                    'mechanism_signature': c.get('mechanism_signature', ''),
                    'supporting_record_ids': sup,
                })
                seen.update(sup)
            p2_cost = p2_msg.usage.input_tokens/1e6*3 + p2_msg.usage.output_tokens/1e6*15
            print(f"  Pass 2: {len(new_clusters)} new clusters covering {len(seen)} records; "
                  f"{len(chunk_orphans)-len(seen)} → singleton; ${p2_cost:.3f}", flush=True)

        # Append new clusters to working catalogue (available to subsequent chunks)
        catalogue = catalogue + new_clusters
        all_new_clusters.extend(new_clusters)

        # Build per-record assignments
        cluster_member = {r: c['cluster_id']
                          for c in new_clusters for r in c['supporting_record_ids']}
        for r in records:
            rid = r['record_id']
            if rid in cluster_member:
                cid = cluster_member[rid]; status = 'residual_new_cluster'
                total_into_new += 1
            elif rid_to_cid.get(rid) in valid:
                cid = rid_to_cid[rid]; status = 'residual_classified_to_existing'
                total_classified += 1
            else:
                cid = None; status = 'true_singleton'
                total_singleton += 1
            assign_f.write(json.dumps({
                'record_id': rid, 'chunk': chunk_i+1,
                'cluster_id': cid, 'status': status,
            }) + '\n')
        assign_f.flush()

        cum_cost += p1_cost + p2_cost
        elapsed = time.time() - started
        print(f"  chunk wall {time.time()-t0:.0f}s; cumulative ${cum_cost:.2f}, {elapsed/60:.1f} min", flush=True)

        # Snapshot working state
        WORKING_CAT.write_text(json.dumps({'clusters': catalogue}, indent=2, ensure_ascii=False))
        NEW_CLUSTERS_OUT.write_text(json.dumps(all_new_clusters, indent=2, ensure_ascii=False))
        STATE_OUT.write_text(json.dumps({
            'chunks_done': chunk_i+1, 'n_chunks_total': n_chunks,
            'records_processed': sum(min(args.chunk_size, len(todo_ids)-i*args.chunk_size) for i in range(chunk_i+1)),
            'classified_to_existing': total_classified,
            'into_new_residual_cluster': total_into_new,
            'true_singleton': total_singleton,
            'new_residual_clusters': len(all_new_clusters),
            'catalogue_size': len(catalogue),
            'cumulative_cost_sync': round(cum_cost, 3),
        }, indent=2))

    assign_f.close()

    print(f"\n=== RESIDUAL CLUSTERING DONE ===")
    print(f"  Records processed: {sum([total_classified, total_into_new, total_singleton])}")
    print(f"  Classified into existing catalogue (Pass 1 hits): {total_classified}")
    print(f"  Placed in NEW residual clusters: {total_into_new}")
    print(f"  True singletons: {total_singleton}")
    print(f"  New clusters formed: {len(all_new_clusters)}")
    print(f"  Final catalogue size: {len(catalogue)}")
    print(f"  Cost: ${cum_cost:.2f} sync")
    print(f"  Wall: {(time.time()-started)/60:.1f} min")


if __name__ == "__main__":
    main()
