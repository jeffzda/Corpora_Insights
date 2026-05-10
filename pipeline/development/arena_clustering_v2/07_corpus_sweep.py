#!/usr/bin/env python3
"""Phase 4c — corpus sweep driver.

Processes the filter_input.jsonl pool in successive batches. Each batch:
  1. Pass 1 (classify) against the current catalogue
  2. Pass 2 (cluster orphans) on this-batch orphans only
  3. Reconciled new clusters are appended to the catalogue (in memory + on disk)
  4. Reconciled singletons are accumulated into a pending pile (not re-passed)

Key design decisions:
  - Singletons from earlier iterations are NOT injected into later Pass 2 calls.
    They accumulate into pending_singletons.json. End-of-corpus phase will run
    a final classification + Pass 2 on the merged pending + seed singleton pile
    against the matured catalogue. Rationale: Pass 2 loses coherence above
    ~250 records; we'd rather give lonely records one fair shot against a rich
    catalogue than several shots against thin ones (which produces spurious
    clusters).
  - Catalogue is checkpointed after every batch, so a kill is safe.
  - Use --max-iterations to bound test runs (e.g. 10) and watch the orphan
    rate decline as the catalogue matures.

Outputs (in clustering_v2/output/sweep/):
  - cluster_catalogue.json (overwrites the seed catalogue path; backup kept)
  - corpus_assignments.jsonl (one line per record processed, append-only)
  - pending_singletons.json (running pile of unclustered records)
  - sweep_state.json (iteration history, processed_record_ids set)
  - iteration_<NN>_pass1_raw.txt / pass2_raw.txt (debug)
  - iteration_<NN>_summary.json (per-iteration stats)
"""
import argparse
import json
import random
import re
import shutil
import time
from pathlib import Path

import anthropic

# Reuse prompts + helpers from script 06
import importlib.util
_06_path = Path(__file__).resolve().parent / '06_classify_and_cluster_orphans.py'
_spec = importlib.util.spec_from_file_location('p06', _06_path)
p06 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p06)

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT = OUT_DIR / 'filter_input.jsonl'
SEED_CATALOGUE = OUT_DIR / 'cluster_catalogue.json'

SWEEP_DIR = OUT_DIR / 'sweep'
SWEEP_DIR.mkdir(exist_ok=True)
WORKING_CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
ASSIGNMENTS = SWEEP_DIR / 'corpus_assignments.jsonl'
PENDING_SINGLETONS = SWEEP_DIR / 'pending_singletons.json'
STATE = SWEEP_DIR / 'sweep_state.json'


def load_state():
    if STATE.exists():
        return json.load(open(STATE))
    return {
        'iterations': [],
        'processed_record_ids': [],
        'next_orphan_cluster_id': 500,
        'cumulative_cost_sync': 0.0,
        'cumulative_cost_batch': 0.0,
    }


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_catalogue():
    if WORKING_CATALOGUE.exists():
        return json.load(open(WORKING_CATALOGUE))['clusters']
    # Bootstrap from seed catalogue (and copy it across)
    shutil.copy2(SEED_CATALOGUE, WORKING_CATALOGUE)
    return json.load(open(WORKING_CATALOGUE))['clusters']


def save_catalogue(catalogue):
    WORKING_CATALOGUE.write_text(json.dumps({'clusters': catalogue}, indent=2, ensure_ascii=False))


def append_assignments(rows):
    with open(ASSIGNMENTS, 'a') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def load_pending_singletons():
    if PENDING_SINGLETONS.exists():
        return json.load(open(PENDING_SINGLETONS))
    return []


def save_pending_singletons(ids):
    PENDING_SINGLETONS.write_text(json.dumps(sorted(set(ids)), indent=2))


def run_iteration(iter_num, batch, catalogue, client, next_orphan_id):
    """Run one classify+orphan-cluster iteration. Returns dict with:
       new_clusters, classified_assignments, batch_singletons, costs, raw paths.
    """
    p1_raw = SWEEP_DIR / f'iteration_{iter_num:03d}_pass1_raw.txt'
    p2_raw = SWEEP_DIR / f'iteration_{iter_num:03d}_pass2_raw.txt'

    # --- Pass 1: classification
    print(f"\n  [Pass 1] classify {len(batch)} records against {len(catalogue)} clusters", flush=True)
    p1_prompt = p06.build_classify_prompt(catalogue, batch)
    p1_text, p1_msg = p06.stream_call(client, p1_prompt, raw_path=str(p1_raw),
                                        label=f'i{iter_num:03d}-p1')
    p1_parsed = p06.parse_json_tolerant(p1_text)
    assignments = p1_parsed.get('assignments') or p1_parsed.get('_recovered') or []

    rid_to_cluster = {a['record_id']: a['cluster_id'] for a in assignments
                      if isinstance(a, dict) and 'record_id' in a}
    # Cover any records the model dropped from output → mark orphan defensively
    for r in batch:
        if r['record_id'] not in rid_to_cluster:
            rid_to_cluster[r['record_id']] = 'orphan'

    n_classified = sum(1 for v in rid_to_cluster.values() if v != 'orphan')
    n_orphan = sum(1 for v in rid_to_cluster.values() if v == 'orphan')
    p1_cost = p1_msg.usage.input_tokens/1e6*3 + p1_msg.usage.output_tokens/1e6*15
    print(f"  [Pass 1] {n_classified} classified, {n_orphan} orphan  "
          f"({p1_msg.usage.input_tokens:,}in/{p1_msg.usage.output_tokens:,}out, ${p1_cost:.3f})",
          flush=True)

    batch_orphans = [r for r in batch if rid_to_cluster[r['record_id']] == 'orphan']

    # --- Pass 2: orphan clustering (only this batch's orphans)
    new_clusters = []
    p2_msg = None
    p2_cost = 0.0
    if batch_orphans:
        print(f"  [Pass 2] cluster {len(batch_orphans)} orphans", flush=True)
        p2_prompt = p06.build_orphan_prompt(batch_orphans)
        p2_text, p2_msg = p06.stream_call(client, p2_prompt, raw_path=str(p2_raw),
                                            label=f'i{iter_num:03d}-p2')
        p2_parsed = p06.parse_json_tolerant(p2_text)
        proposed = p2_parsed.get('clusters') or p2_parsed.get('_recovered') or []

        # Reconcile: prune to orphan-pool members, dedup, ≥3 threshold,
        # rewrite cluster_id to canonical sequential range to avoid model collisions.
        orphan_pool_ids = {r['record_id'] for r in batch_orphans}
        seen = set()
        clean = []
        for c in proposed:
            if not isinstance(c, dict): continue
            sup = [r for r in (c.get('supporting_record_ids') or [])
                   if r in orphan_pool_ids and r not in seen]
            if len(sup) < 3: continue
            cid = f"c{next_orphan_id:03d}"
            next_orphan_id += 1
            clean.append({
                'cluster_id': cid,
                'canonical_name': c.get('canonical_name', ''),
                'mechanism_signature': c.get('mechanism_signature', ''),
                'supporting_record_ids': sup,
            })
            seen.update(sup)
        new_clusters = clean
        in_cluster = {r for c in new_clusters for r in c['supporting_record_ids']}
        batch_singletons = sorted(orphan_pool_ids - in_cluster)
        p2_cost = p2_msg.usage.input_tokens/1e6*3 + p2_msg.usage.output_tokens/1e6*15
        print(f"  [Pass 2] {len(new_clusters)} new clusters covering "
              f"{len(in_cluster)} records; {len(batch_singletons)} → pending pile  "
              f"({p2_msg.usage.input_tokens:,}in/{p2_msg.usage.output_tokens:,}out, ${p2_cost:.3f})",
              flush=True)
    else:
        batch_singletons = []
        print(f"  [Pass 2] skipped (no orphans)", flush=True)

    # Build per-record assignments to log
    cluster_member_lookup = {r: c['cluster_id']
                             for c in new_clusters for r in c['supporting_record_ids']}
    assigned_rows = []
    for r in batch:
        rid = r['record_id']
        if rid in cluster_member_lookup:
            cid = cluster_member_lookup[rid]; status = 'new_cluster'
        elif rid_to_cluster[rid] != 'orphan':
            cid = rid_to_cluster[rid]; status = 'classified'
        else:
            cid = None; status = 'pending_singleton'
        assigned_rows.append({
            'record_id': rid, 'iteration': iter_num,
            'cluster_id': cid, 'status': status,
        })

    return {
        'new_clusters': new_clusters,
        'next_orphan_id': next_orphan_id,
        'assigned_rows': assigned_rows,
        'batch_singletons': batch_singletons,
        'n_classified': n_classified,
        'n_orphan': n_orphan,
        'p1_cost': p1_cost,
        'p2_cost': p2_cost,
        'p1_in': p1_msg.usage.input_tokens, 'p1_out': p1_msg.usage.output_tokens,
        'p2_in': p2_msg.usage.input_tokens if p2_msg else 0,
        'p2_out': p2_msg.usage.output_tokens if p2_msg else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-iterations', type=int, default=10,
                    help='How many batches to process this run (test cap).')
    ap.add_argument('--batch-size', type=int, default=200)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--ramp', action='store_true',
                    help='Grow batch size as orphan-rate drops below thresholds.')
    args = ap.parse_args()

    state = load_state()
    catalogue = load_catalogue()
    pending_singletons = set(load_pending_singletons())
    processed_ids = set(state['processed_record_ids'])
    next_orphan_id = state['next_orphan_cluster_id']

    print(f"Loading filter_input pool...", flush=True)
    rows = [json.loads(l) for l in open(INPUT)]
    pool = [r for r in rows if r['record_id'] not in processed_ids]
    print(f"  filter_input: {len(rows):,} records", flush=True)
    print(f"  already processed (resume): {len(processed_ids):,}", flush=True)
    print(f"  pool remaining: {len(pool):,}", flush=True)
    print(f"  catalogue: {len(catalogue)} clusters", flush=True)
    print(f"  pending singletons: {len(pending_singletons)}", flush=True)
    print(f"  next orphan cluster id: c{next_orphan_id:03d}", flush=True)

    if not pool:
        print("Nothing left to process. Exiting.", flush=True)
        return

    rng = random.Random(args.seed + len(processed_ids))
    rng.shuffle(pool)

    client = anthropic.Anthropic()

    starting_iter_count = len(state['iterations'])
    iter_num = starting_iter_count + 1
    cap = starting_iter_count + args.max_iterations
    cursor = 0

    while iter_num <= cap and cursor < len(pool):
        batch_size = args.batch_size
        if args.ramp and len(state['iterations']) >= 3:
            recent = state['iterations'][-3:]
            recent_orphan_rate = sum(it['n_orphan'] for it in recent) / sum(it['n_classified']+it['n_orphan'] for it in recent)
            if recent_orphan_rate < 0.5: batch_size = 300
            if recent_orphan_rate < 0.3: batch_size = 500
            if recent_orphan_rate < 0.15: batch_size = 800
        batch = pool[cursor:cursor+batch_size]
        if not batch: break
        cursor += len(batch)

        t0 = time.time()
        print(f"\n=== Iteration {iter_num} ({len(batch)} records, "
              f"catalogue: {len(catalogue)} clusters) ===", flush=True)
        result = run_iteration(iter_num, batch, catalogue, client, next_orphan_id)
        elapsed = time.time() - t0

        # Update catalogue, pending pile, state
        catalogue = catalogue + result['new_clusters']
        save_catalogue(catalogue)
        next_orphan_id = result['next_orphan_id']

        pending_singletons.update(result['batch_singletons'])
        save_pending_singletons(pending_singletons)

        append_assignments(result['assigned_rows'])

        processed_ids.update(r['record_id'] for r in batch)
        iter_summary = {
            'iteration': iter_num,
            'batch_size': len(batch),
            'catalogue_size_before': len(catalogue) - len(result['new_clusters']),
            'catalogue_size_after': len(catalogue),
            'n_new_clusters': len(result['new_clusters']),
            'n_classified': result['n_classified'],
            'n_orphan': result['n_orphan'],
            'orphan_rate': result['n_orphan'] / len(batch),
            'classification_rate': result['n_classified'] / len(batch),
            'n_into_new_clusters': sum(len(c['supporting_record_ids']) for c in result['new_clusters']),
            'n_to_pending_singletons': len(result['batch_singletons']),
            'p1_in': result['p1_in'], 'p1_out': result['p1_out'],
            'p2_in': result['p2_in'], 'p2_out': result['p2_out'],
            'p1_cost': result['p1_cost'], 'p2_cost': result['p2_cost'],
            'iter_cost_sync': result['p1_cost'] + result['p2_cost'],
            'iter_cost_batch': (result['p1_cost'] + result['p2_cost']) / 2,
            'wall_seconds': round(elapsed, 1),
        }
        (SWEEP_DIR / f'iteration_{iter_num:03d}_summary.json').write_text(
            json.dumps(iter_summary, indent=2, ensure_ascii=False))
        state['iterations'].append(iter_summary)
        state['processed_record_ids'] = sorted(processed_ids)
        state['next_orphan_cluster_id'] = next_orphan_id
        state['cumulative_cost_sync'] += iter_summary['iter_cost_sync']
        state['cumulative_cost_batch'] += iter_summary['iter_cost_batch']
        save_state(state)

        print(f"  iteration done in {elapsed:.0f}s; "
              f"cumulative ${state['cumulative_cost_sync']:.2f} sync / "
              f"${state['cumulative_cost_batch']:.2f} batch", flush=True)

        iter_num += 1

    print(f"\n=== SWEEP RUN COMPLETE ({len(state['iterations'])} total iterations) ===", flush=True)
    print(f"  Catalogue: {len(catalogue)} clusters", flush=True)
    print(f"  Records processed: {len(processed_ids):,}", flush=True)
    print(f"  Pending singletons (set aside for end-of-corpus sweep): {len(pending_singletons):,}", flush=True)
    print(f"  Cumulative cost: ${state['cumulative_cost_sync']:.2f} sync / ${state['cumulative_cost_batch']:.2f} batch", flush=True)
    if state['iterations']:
        print(f"\n  Orphan-rate trajectory:", flush=True)
        for it in state['iterations']:
            bar = '#' * int(it['orphan_rate'] * 40)
            print(f"    iter {it['iteration']:>3}  bs={it['batch_size']:>3}  "
                  f"orphan {it['orphan_rate']*100:5.1f}%  classify {it['classification_rate']*100:5.1f}%  "
                  f"+{it['n_new_clusters']} clusters  cat→{it['catalogue_size_after']}  "
                  f"|{bar}", flush=True)


if __name__ == "__main__":
    main()
