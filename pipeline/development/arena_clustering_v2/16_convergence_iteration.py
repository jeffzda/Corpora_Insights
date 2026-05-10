#!/usr/bin/env python3
"""Phase 4g — convergence iteration on remaining singletons.

After script 15 (Pass 1 only on residual singletons against the matured
1,048-cluster catalogue), there is still a residual pile of records that
didn't classify into any cluster. Some of those records may share a
mechanism with each other but were never in the same Pass 2 pool during
script 14's chunked sequential run.

This script runs Pass 2 (cluster formation) on each chunk, and a TIGHT
Pass 1 against ONLY clusters formed in earlier chunks of this run (not
the 1,048-cluster catalogue from before — that Pass 1 has already been
done by script 15 and would be redundant). The earlier-chunk-only Pass 1
serves as cross-chunk cluster-propagation, preventing two chunks from
independently forming duplicate clusters from records sharing a novel
mechanism.

Chunk 1: Pass 1 catalogue is empty → skip Pass 1, just Pass 2.
Chunk N≥2: Pass 1 catalogue = clusters formed in chunks 1..N-1.
Pass 2 every chunk: forms new clusters from this chunk's residual.

Demonstrates convergence: if this iteration discovers significant new
clusters, more iteration is warranted; if it produces near-nothing,
we've hit the fixed point and can stop.

Inputs:
  output/sweep/third_pass/final_singletons.json (post-script-15 singletons)
  output/sweep/residual/catalogue_after_residual.json (1,048-cluster matured
    catalogue — used only for cluster_id continuation; not for Pass 1 here)

Outputs (in output/sweep/convergence/):
  convergence_assignments.jsonl
  convergence_new_clusters.json
  catalogue_after_convergence.json
  meta.json
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
SOURCE_CATALOGUE = SWEEP_DIR / 'residual' / 'catalogue_after_residual.json'
SINGLETONS_IN = SWEEP_DIR / 'third_pass' / 'final_singletons.json'

CONV_DIR = SWEEP_DIR / 'convergence'
CONV_DIR.mkdir(exist_ok=True)
WORKING_CAT = CONV_DIR / 'catalogue_after_convergence.json'
ASSIGN_OUT = CONV_DIR / 'convergence_assignments.jsonl'
NEW_CLUSTERS_OUT = CONV_DIR / 'convergence_new_clusters.json'
META_OUT = CONV_DIR / 'meta.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunk-size', type=int, default=180)
    ap.add_argument('--seed', type=int, default=2026)
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    full_catalogue = json.load(open(SOURCE_CATALOGUE))['clusters']
    print(f"  source catalogue: {len(full_catalogue)} clusters (used for cluster_id continuation only)", flush=True)
    singletons = json.load(open(SINGLETONS_IN))
    print(f"  remaining singletons: {len(singletons):,}", flush=True)
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}

    max_id = max(int(c['cluster_id'][1:]) for c in full_catalogue if c['cluster_id'][1:].isdigit())
    next_orphan_id = max_id + 1
    print(f"  next orphan cluster id: c{next_orphan_id}", flush=True)
    # Pass 1 catalogue starts empty; populated by clusters this run forms
    convergence_clusters = []

    # Resume support
    processed = set()
    if ASSIGN_OUT.exists():
        for line in open(ASSIGN_OUT):
            try: processed.add(json.loads(line)['record_id'])
            except: pass
        print(f"  resume: skipping {len(processed):,} already-processed", flush=True)

    todo_ids = [rid for rid in singletons if rid not in processed and rid in rid_to_record]
    rng = random.Random(args.seed)
    rng.shuffle(todo_ids)
    print(f"  to process: {len(todo_ids):,}", flush=True)
    if not todo_ids:
        print("Nothing to do.")
        return

    n_chunks = (len(todo_ids) + args.chunk_size - 1) // args.chunk_size
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
        print(f"\n=== Convergence chunk {chunk_i+1}/{n_chunks} "
              f"({len(records)} records, propagation catalogue {len(convergence_clusters)}) ===",
              flush=True)

        # Pass 1 — only against clusters formed in earlier chunks of this run
        # (skips redundant Pass 1 against the 1,048 catalogue, which script 15 already did)
        valid = {c['cluster_id'] for c in convergence_clusters}
        rid_to_cid = {}
        n_clf = 0; p1_cost = 0.0
        if convergence_clusters:
            p1_prompt = p12.build_neutral_batched_prompt(convergence_clusters, records)
            print(f"  Pass 1 prompt: {len(p1_prompt):,} chars (against {len(convergence_clusters)} earlier-chunk clusters)", flush=True)
            p1_text, p1_msg = p06.stream_call(client, p1_prompt, raw_path=None,
                                                label=f'c{chunk_i+1}-p1')
            p1_parsed = p06.parse_json_tolerant(p1_text)
            raw_assigns = p1_parsed.get('assignments') or p1_parsed.get('_recovered') or []
            rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assigns
                          if isinstance(a, dict) and 'record_id' in a}
            n_clf = sum(1 for r in records if rid_to_cid.get(r['record_id']) in valid)
            p1_cost = p1_msg.usage.input_tokens/1e6*3 + p1_msg.usage.output_tokens/1e6*15
            print(f"  Pass 1: {n_clf} classified, {len(records)-n_clf} orphan; ${p1_cost:.3f}", flush=True)
        else:
            print(f"  Pass 1: skipped (no earlier-chunk clusters yet)", flush=True)

        chunk_orphans = [r for r in records
                         if rid_to_cid.get(r['record_id'], 'orphan') not in valid]

        new_clusters = []
        p2_cost = 0.0
        if chunk_orphans:
            p2_prompt = p06.build_orphan_prompt(chunk_orphans)
            print(f"  Pass 2: clustering {len(chunk_orphans)} orphans", flush=True)
            p2_text, p2_msg = p06.stream_call(client, p2_prompt, raw_path=None,
                                                label=f'c{chunk_i+1}-p2')
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

        convergence_clusters = convergence_clusters + new_clusters
        all_new_clusters.extend(new_clusters)

        cluster_member = {r: c['cluster_id']
                          for c in new_clusters for r in c['supporting_record_ids']}
        for r in records:
            rid = r['record_id']
            if rid in cluster_member:
                cid = cluster_member[rid]; status = 'convergence_new_cluster'
                total_into_new += 1
            elif rid_to_cid.get(rid) in valid:
                cid = rid_to_cid[rid]; status = 'convergence_classified_to_existing'
                total_classified += 1
            else:
                cid = None; status = 'final_singleton'
                total_singleton += 1
            assign_f.write(json.dumps({
                'record_id': rid, 'chunk': chunk_i+1,
                'cluster_id': cid, 'status': status,
            }) + '\n')
        assign_f.flush()

        cum_cost += p1_cost + p2_cost
        elapsed = time.time() - started
        print(f"  chunk wall {time.time()-t0:.0f}s; cumulative ${cum_cost:.2f}, {elapsed/60:.1f} min", flush=True)

        # Working catalogue snapshot: full source + all convergence clusters formed so far
        WORKING_CAT.write_text(json.dumps(
            {'clusters': full_catalogue + convergence_clusters},
            indent=2, ensure_ascii=False))
        NEW_CLUSTERS_OUT.write_text(json.dumps(all_new_clusters, indent=2, ensure_ascii=False))

    assign_f.close()
    META_OUT.write_text(json.dumps({
        'records_processed': total_classified + total_into_new + total_singleton,
        'classified_to_existing': total_classified,
        'into_new_convergence_cluster': total_into_new,
        'final_singleton': total_singleton,
        'new_clusters_formed': len(all_new_clusters),
        'final_catalogue_size': len(full_catalogue) + len(convergence_clusters),
        'convergence_clusters_only': len(convergence_clusters),
        'cost_sync': round(cum_cost, 3),
        'wall_seconds': round(time.time()-started, 1),
    }, indent=2))

    print(f"\n=== CONVERGENCE ITERATION DONE ===")
    print(f"  Records processed: {total_classified + total_into_new + total_singleton}")
    print(f"  Classified into earlier-chunk convergence clusters: {total_classified}")
    print(f"  Placed in new convergence clusters: {total_into_new}")
    print(f"  Final singletons: {total_singleton}")
    print(f"  New convergence clusters formed: {len(all_new_clusters)}")
    print(f"  Final catalogue (full source + convergence): {len(full_catalogue) + len(convergence_clusters)}")
    print(f"  Cost: ${cum_cost:.2f}, wall {(time.time()-started)/60:.1f} min")
    print(f"\nIf new_clusters_formed << previous iteration AND classified << previous iteration,")
    print(f"the pipeline has converged.")


if __name__ == "__main__":
    main()
