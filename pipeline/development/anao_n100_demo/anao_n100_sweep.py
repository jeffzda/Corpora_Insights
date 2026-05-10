#!/usr/bin/env python3
"""ANAO N=100 — Phase 4b: corpus sweep (Pass 1 + Pass 2 per batch).

Mirrors the original integrated design from
corpora/arena/clustering_v2/code/07_corpus_sweep.py (Pass 1 + Pass 2 same iteration)
with prompts adapted from 06_classify_and_cluster_orphans.py.

Iteration: take BATCH_SIZE unprocessed records → Pass 1 (classify against
current catalogue) → Pass 2 (cluster the orphans from this batch only) →
append new clusters to catalogue → checkpoint.

Records that even Pass 2 can't cluster accumulate as pending singletons.
"""
import argparse
import json
import random
import re
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
INPUT = OUT_DIR / 'anao_n100_filter_input.jsonl'
SEED_CATALOGUE = OUT_DIR / 'anao_n100_cluster_catalogue.json'

# Sweep state and outputs
SWEEP_DIR = OUT_DIR / 'sweep'
SWEEP_DIR.mkdir(parents=True, exist_ok=True)
CATALOGUE_PATH = SWEEP_DIR / 'cluster_catalogue.json'
ASSIGNMENTS_PATH = SWEEP_DIR / 'corpus_assignments.jsonl'
PENDING_PATH = SWEEP_DIR / 'pending_singletons.json'
STATE_PATH = SWEEP_DIR / 'sweep_state.json'

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 128_000
BATCH_SIZE = 200
SEED = 42


CLASSIFY_PROMPT_HEADER = """You are classifying ANAO performance-audit records against an existing catalogue of failure-mode clusters.

For each record, decide: does its causal failure mechanism match one of the catalogue entries? If yes, return that cluster_id. If no clear match exists in the catalogue, return cluster_id="orphan".

CRITICAL: Do NOT force-fit. It is better to mark a record as 'orphan' than to assign it to a cluster that doesn't actually capture its mechanism. Orphans will be processed by a separate clustering pass that may create new clusters for them. Force-fitting damages the catalogue.

Match on MECHANISM, not on:
- Agency name, programme name, sector
- Surface text similarity
- Topic similarity (just because both are about "procurement" doesn't mean same mechanism)

Two records share a cluster only if they describe the SAME causal pathway.

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

CLASSIFY_PROMPT_FOOTER = """\
# OUTPUT FORMAT

Return JSON only:
{
  "assignments": [
    {"record_id": "ANAOM-...", "cluster_id": "c042"},
    {"record_id": "ANAOM-...", "cluster_id": "orphan"}
  ]
}

One assignment per input record, in input order. cluster_id must be either an existing catalogue id (e.g. "c042") or the literal string "orphan"."""

ORPHAN_CLUSTER_PROMPT = """You are extending the catalogue of FAILURE-MODE CLUSTERS for the ANAO performance audit corpus.

The records below were rejected as 'orphans' by the classifier — they did not match any existing catalogue cluster's mechanism. Your job is to identify any NEW failure-mode clusters these orphans collectively support.

CRITICAL: Cluster by MECHANISM, not by agency / programme / topic / sector vocabulary. Two records share a cluster only if they describe the SAME causal pathway, even with different surface vocabulary.

THRESHOLD RULE: A cluster must be supported by at least 3 records. Do NOT propose a cluster justified by 1 or 2 records — simply leave those records out of your output. Records you don't list will be treated as singletons by post-processing; you do not need to enumerate them.

For each new cluster you identify, output:
- cluster_id: must NOT collide with existing catalogue ids; use a high range starting from c500
- canonical_name: 4-12 word descriptive name (locks forever)
- mechanism_signature: 1 sentence ("X causes Y because Z" OR "Y because Z")
- supporting_record_ids: list of 3+ record_ids from the orphan set that share this mechanism

DO NOT emit a singletons list. Records you do not place in any cluster are automatically treated as singletons by post-processing.

Rules:
- It IS expected that many orphans will remain unclustered — that is the correct behaviour for genuinely unique mechanisms or patterns with only 1-2 examples in this batch.
- Avoid agency-specific vocabulary in the canonical_name and signature.
- The catalogue is only for patterns with ≥3 evidence.

# OUTPUT FORMAT — STRICT

Return a single JSON object and NOTHING ELSE. No prose, markdown fences, working notes, or per-record commentary. The very first character must be `{` and the last character must be `}`.

Schema:
{
  "clusters": [
    {
      "cluster_id": "c501",
      "canonical_name": "4-12 word descriptive name",
      "mechanism_signature": "1 sentence",
      "supporting_record_ids": ["ANAOM-...", "ANAOM-...", "ANAOM-..."]
    }
  ]
}

No record_id may appear in more than one cluster. Cluster supporting_record_ids must contain at least 3 ids drawn from the input orphan set.

# ORPHAN RECORDS"""


def stream_call(client, prompt, raw_path=None, label='call'):
    raw_f = open(raw_path, 'w', encoding='utf-8') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
    try:
        with client.messages.stream(
            model=MODEL, max_tokens=MAX_TOKENS, temperature=0.0,
            messages=[{'role':'user','content':prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev); text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars-last_chars)/max(now-last_print,1)
                    print(f'  [{label}] [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    return ''.join(parts), msg


def parse_json_tolerant(text):
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try: return json.loads(body)
    except json.JSONDecodeError:
        first = body.find('{'); last = body.rfind('}')
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: pass
    return {}


def build_classify_prompt(catalogue, records):
    cat_lines = []
    for c in catalogue:
        cat_lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        cat_lines.append(f"  mechanism: {c['mechanism_signature']}")
    rec_lines = []
    for r in records:
        rid = r['record_id']
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes': axes.append(ax[3:])
        rec_lines.append(f"\n## {rid}  [axes: {','.join(axes)}; v: {r.get('valence','')}]")
        rec_lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            rec_lines.append(f"evidence: {evi[:600]}")
    return CLASSIFY_PROMPT_HEADER + ''.join(cat_lines) + '\n\n# RECORDS TO CLASSIFY' + \
           ''.join(rec_lines) + '\n\n' + CLASSIFY_PROMPT_FOOTER


def build_orphan_prompt(orphan_records):
    lines = []
    for r in orphan_records:
        rid = r['record_id']
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes': axes.append(ax[3:])
        lines.append(f"\n## {rid}  [axes: {','.join(axes)}; v: {r.get('valence','')}]")
        lines.append(f"narrative: {narr}")
        if evi and evi != narr:
            lines.append(f"evidence: {evi[:600]}")
    return ORPHAN_CLUSTER_PROMPT + ''.join(lines)


def load_seed_catalogue():
    """Load seed catalogue if it exists, else from script 05's output."""
    if CATALOGUE_PATH.exists():
        return json.load(CATALOGUE_PATH.open())
    seed = json.load(SEED_CATALOGUE.open())
    return {
        'clusters': seed.get('clusters', []),
        'next_cluster_id': max([int(c['cluster_id'][1:]) for c in seed.get('clusters', [])] + [0]) + 1,
    }


def save_catalogue(cat):
    CATALOGUE_PATH.write_text(json.dumps(cat, indent=2, ensure_ascii=False))


def load_state():
    if STATE_PATH.exists():
        return json.load(STATE_PATH.open())
    return {'iteration': 0, 'processed_record_ids': [], 'pending_singleton_ids': []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-iterations', type=int, default=999)
    ap.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    args = ap.parse_args()

    rng = random.Random(SEED)
    rows = [json.loads(l) for l in INPUT.open()]
    by_id = {r['record_id']: r for r in rows}
    print(f'pool: {len(rows):,}')

    catalogue = load_seed_catalogue()
    state = load_state()
    print(f'catalogue size: {len(catalogue["clusters"])}')
    print(f'state: iter {state["iteration"]}, processed {len(state["processed_record_ids"])}, pending {len(state["pending_singleton_ids"])}')

    # Records yet to be processed
    processed = set(state['processed_record_ids'])
    remaining = [r for r in rows if r['record_id'] not in processed]
    print(f'remaining: {len(remaining):,}')
    rng.shuffle(remaining)

    client = anthropic.Anthropic()

    iter_idx = state['iteration']
    while remaining and iter_idx - state['iteration'] < args.max_iterations:
        iter_idx += 1
        batch = remaining[:args.batch_size]
        remaining = remaining[args.batch_size:]
        print(f"\n=== iter {iter_idx} | batch {len(batch)} | catalogue {len(catalogue['clusters'])} | remaining {len(remaining):,} ===")

        # Pass 1: classify
        p1_prompt = build_classify_prompt(catalogue['clusters'], batch)
        p1_raw = SWEEP_DIR / f'iteration_{iter_idx:03d}_pass1_raw.txt'
        p1_text, p1_msg = stream_call(client, p1_prompt, raw_path=p1_raw, label=f'p1-i{iter_idx}')
        p1_cost = p1_msg.usage.input_tokens/1e6*3 + p1_msg.usage.output_tokens/1e6*15
        p1_parsed = parse_json_tolerant(p1_text)
        assigns = p1_parsed.get('assignments', [])
        print(f'  P1: {len(assigns)} assignments, ${p1_cost:.3f}')

        # Bucket: classified vs orphan
        classified = [a for a in assigns if a.get('cluster_id') and a.get('cluster_id') != 'orphan']
        orphans = [a for a in assigns if a.get('cluster_id') == 'orphan']
        # Records missing from output
        seen = {a.get('record_id') for a in assigns}
        missing = [r for r in batch if r['record_id'] not in seen]
        print(f'  P1: {len(classified)} classified, {len(orphans)} orphan, {len(missing)} missing-from-output')

        # Pass 2: cluster orphans (and any missing — treat them as orphans for safety)
        orphan_records = [by_id[a['record_id']] for a in orphans if a.get('record_id') in by_id]
        orphan_records.extend(r for r in missing)

        p2_clusters = []
        if orphan_records:
            p2_prompt = build_orphan_prompt(orphan_records)
            p2_raw = SWEEP_DIR / f'iteration_{iter_idx:03d}_pass2_raw.txt'
            p2_text, p2_msg = stream_call(client, p2_prompt, raw_path=p2_raw, label=f'p2-i{iter_idx}')
            p2_cost = p2_msg.usage.input_tokens/1e6*3 + p2_msg.usage.output_tokens/1e6*15
            p2_parsed = parse_json_tolerant(p2_text)
            p2_clusters = p2_parsed.get('clusters', [])
            print(f'  P2: {len(p2_clusters)} new clusters, ${p2_cost:.3f}')
        else:
            p2_cost = 0.0
            print(f'  P2: skipped (no orphans)')

        # Reconcile new clusters into catalogue with reassigned ids
        new_assignments = []  # extra assignments for records that joined new clusters
        nci = catalogue.get('next_cluster_id', max(
            [int(c['cluster_id'][1:]) for c in catalogue['clusters']] + [0]) + 1)
        cluster_id_map = {}
        for nc in p2_clusters:
            members = nc.get('supporting_record_ids', [])
            if len(members) < 3: continue
            new_id = f'c{nci:03d}'
            cluster_id_map[nc.get('cluster_id', new_id)] = new_id
            cat_entry = {
                'cluster_id': new_id,
                'canonical_name': nc.get('canonical_name', '?'),
                'mechanism_signature': nc.get('mechanism_signature', ''),
                'created_iter': iter_idx,
                'seed_members': members,
            }
            catalogue['clusters'].append(cat_entry)
            for rid in members:
                new_assignments.append({'record_id': rid, 'cluster_id': new_id, 'iter': iter_idx, 'via': 'pass2'})
            nci += 1
        catalogue['next_cluster_id'] = nci

        # Persist assignments — Pass 1 classified + Pass 2 new
        with ASSIGNMENTS_PATH.open('a') as f:
            for a in classified:
                f.write(json.dumps({**a, 'iter': iter_idx, 'via': 'pass1'}) + '\n')
            for a in new_assignments:
                f.write(json.dumps(a) + '\n')

        # Update pending pile: orphans not placed in a Pass 2 cluster
        placed_in_p2 = {rid for nc in p2_clusters
                        for rid in nc.get('supporting_record_ids', [])
                        if len(nc.get('supporting_record_ids', [])) >= 3}
        new_pending = [r['record_id'] for r in orphan_records
                        if r['record_id'] not in placed_in_p2]
        state['pending_singleton_ids'].extend(new_pending)

        # Update processed-set (every record in this batch is now accounted for)
        for r in batch: state['processed_record_ids'].append(r['record_id'])
        state['iteration'] = iter_idx

        # Save catalogue + state + per-iter summary
        save_catalogue(catalogue)
        save_state(state)
        summary = {
            'iter': iter_idx, 'batch_size': len(batch),
            'p1_classified': len(classified), 'p1_orphan': len(orphans), 'p1_missing': len(missing),
            'p2_new_clusters': len([c for c in p2_clusters if len(c.get('supporting_record_ids',[])) >= 3]),
            'p2_placed_records': len(placed_in_p2),
            'newly_pending': len(new_pending),
            'catalogue_size': len(catalogue['clusters']),
            'cumulative_pending': len(state['pending_singleton_ids']),
            'p1_cost': round(p1_cost,4), 'p2_cost': round(p2_cost,4),
            'p1_in_tok': p1_msg.usage.input_tokens, 'p1_out_tok': p1_msg.usage.output_tokens,
        }
        (SWEEP_DIR / f'iteration_{iter_idx:03d}_summary.json').write_text(
            json.dumps(summary, indent=2))

        orphan_rate = len(orphans) / max(len(batch), 1) * 100
        print(f'  end of iter {iter_idx}: catalogue={len(catalogue["clusters"])}  '
              f'orphan_rate={orphan_rate:.1f}%  pending={len(state["pending_singleton_ids"])}')

    PENDING_PATH.write_text(json.dumps(state['pending_singleton_ids'], indent=2))

    print(f'\n=== sweep complete ===')
    print(f'iterations: {iter_idx}')
    print(f'catalogue size: {len(catalogue["clusters"])}')
    print(f'pending singletons: {len(state["pending_singleton_ids"])}')
    print(f'remaining unprocessed: {len(remaining)}')


if __name__ == '__main__':
    main()
