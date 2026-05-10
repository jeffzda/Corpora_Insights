#!/usr/bin/env python3
"""ANAO N=100 — Phase 4a: seed cluster catalogue.

Mirrors corpora/arena/clustering_v2/code/05_seed_clusters.py with
ANAO-appropriate stratification (portfolio replaces kb_category).

Stratification: 8 top portfolios × 3 axis-combos × 15 = 360 target.
"""
import argparse
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
INPUT = OUT_DIR / 'anao_n100_filter_input.jsonl'
SAMPLE_OUT = OUT_DIR / 'anao_n100_seed_sample.jsonl'
CATALOGUE_OUT = OUT_DIR / 'anao_n100_cluster_catalogue.json'
RAW_OUT = OUT_DIR / 'anao_n100_seed_response_raw.txt'

TOP_PORTFOLIOS = [
    'Defence',
    'Across Entities',
    'Treasury',
    'Prime Minister and Cabinet',
    'Health and Ageing',
    'Environment, Water, Heritage & the Arts',
    'Finance',
    'Agriculture, Fisheries and Forestry',
]

AXIS_COMBOS = [
    ('occ_mech', lambda r: r.get('is_occurrence')=='yes' and r.get('is_mechanism')=='yes'),
    ('mech_only', lambda r: r.get('is_mechanism')=='yes' and r.get('is_occurrence')=='no'),
    ('occ_only', lambda r: r.get('is_occurrence')=='yes' and r.get('is_mechanism')=='no'),
]

PER_CELL = 15
MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 32000


SEED_PROMPT = """You are building an initial catalogue of FAILURE-MODE CLUSTERS for the ANAO performance audit corpus.

Each input record is a piece of extracted insight from an audit report. The records below have all been pre-tagged as failure-mode-relevant (negative valence + occurrence-or-mechanism). Read all records and infer the set of failure-mode clusters that exist in this sample.

CRITICAL: Cluster by MECHANISM (the 'how' or 'why' something fails), NOT by:
- Agency name or portfolio
- Programme name or specific entity
- Domain (defence/health/treasury/etc) — the same mechanism can occur across portfolios

Two records share a cluster if they describe the SAME causal pathway, even if the agencies, programmes, and surface vocabulary differ.

YOUR JOB: produce a CATALOGUE of failure-mode cluster LABELS. Each cluster must be supported by at least 3 records sharing the same causal mechanism. Records that don't have at least 2 other records sharing their mechanism should be returned as singletons — listed by record_id but NOT promoted to a cluster definition.

You are NOT assigning records to clusters in this step beyond identifying which records justified each cluster (no full member lists), and you are NOT writing descriptions yet (those come later, after all assignment is done across the full corpus).

For each cluster you identify, output:
- cluster_id: c001, c002, ... (zero-padded 3 digits)
- canonical_name: 4-12 word descriptive name (locks forever; do not change later)
- mechanism_signature: 1 sentence of the abstracted causal logic. Either form is fine:
  - "X causes Y because Z" (when there is a clear triggering condition)
  - "Y because Z" (when the cause is the property/condition itself, with no separate trigger)
- supporting_record_ids: list of 3+ record_ids from the input that share this mechanism (just the ids, no descriptions). Used to verify the ≥3 threshold and to seed downstream classification.

Then list every record that did NOT get grouped into a cluster as a singleton, by record_id.

CRITICAL THRESHOLD RULE:
- Do NOT propose a cluster supported by fewer than 3 records. A pattern observed in 1 or 2 records is a hypothesis, not a cluster — leave those records as singletons.
- Singletons may later become clusters when subsequent batches contribute matching records.

Rules:
- Aim for clusters that are tightly mechanism-bound, not breadth-bound.
- Prefer specificity over breadth. "Procurement controls weak" is too broad. "Procurement records dispersed across non-integrated systems prevent compliance verification" is the right resolution.
- DO NOT cluster by agency, programme, or sector — the test is mechanism, not topic.
- Avoid agency-specific vocabulary in the canonical_name and signature. The label should generalise.
- It is fine — preferred, even — to leave many records as singletons. The catalogue is only for patterns with ≥3 evidence.

Output valid JSON, schema:
{
  "clusters": [
    {
      "cluster_id": "c001",
      "canonical_name": "...",
      "mechanism_signature": "...",
      "supporting_record_ids": ["ANAOM-...", "ANAOM-...", "ANAOM-..."]
    }
  ],
  "singletons": ["ANAOM-...", "ANAOM-..."]
}

# Records to cluster"""


def stratified_sample(rows, seed=42):
    rng = random.Random(seed)
    by_cell = defaultdict(list)
    for r in rows:
        portfolio = (r.get('portfolio') or '').strip()
        if portfolio not in TOP_PORTFOLIOS:
            continue
        for combo_name, pred in AXIS_COMBOS:
            if pred(r):
                by_cell[(portfolio, combo_name)].append(r)
                break

    sample = []
    for (portfolio, combo), pool in by_cell.items():
        rng.shuffle(pool)
        take = min(PER_CELL, len(pool))
        for r in pool[:take]:
            r['_seed_cat'] = portfolio
            r['_seed_combo'] = combo
            sample.append(r)
    rng.shuffle(sample)
    return sample


def build_record_block(records):
    lines = []
    for r in records:
        rid = r['record_id']
        cat = r.get('_seed_cat', '')
        combo = r.get('_seed_combo', '')
        narr = (r.get('narrative') or '').strip()
        evi = (r.get('evidence') or '').strip()
        axes = []
        for ax in ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation']:
            if r.get(ax) == 'yes':
                axes.append(ax[3:])
        v = r.get('valence', '')
        lines.append(f'\n## {rid}  [portfolio: {cat[:30]}]  [axes: {",".join(axes)}; v: {v}]')
        lines.append(f'narrative: {narr}')
        if evi and evi != narr:
            lines.append(f'evidence: {evi[:600]}')
    return '\n'.join(lines)


def parse_clusters(raw):
    t = raw.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1]
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    s, e = t.find('{'), t.rfind('}')
    if s >= 0 and e > s:
        try: return json.loads(t[s:e+1])
        except json.JSONDecodeError as ex: print(f'parse error: {ex}')
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    rows = [json.loads(l) for l in INPUT.open()]
    print(f'pool: {len(rows):,}', flush=True)

    sample = stratified_sample(rows)
    print(f'sample: {len(sample)} records ({len(set((r["_seed_cat"], r["_seed_combo"]) for r in sample))} cells)', flush=True)

    with SAMPLE_OUT.open('w') as f:
        for r in sample:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    record_block = build_record_block(sample)
    prompt = SEED_PROMPT + '\n' + record_block
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} input tokens)', flush=True)

    if args.dry_run:
        print('dry-run; not calling API'); return

    print(f'\ncalling {MODEL}...', flush=True)
    client = anthropic.Anthropic()
    started = time.time()
    parts = []
    last_print = started; last_chars = 0; text_chars = 0
    with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS,
                                 messages=[{'role':'user','content':prompt}]) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars)/max(now-last_print,1)
                print(f'  [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    RAW_OUT.write_text(raw)
    wall = time.time()-started
    cost = msg.usage.input_tokens/1e6*3 + msg.usage.output_tokens/1e6*15  # Sonnet 4.6 pricing
    print(f'done: {wall:.0f}s {msg.usage.input_tokens:,}in/{msg.usage.output_tokens:,}out ${cost:.3f}', flush=True)

    parsed = parse_clusters(raw)
    if not parsed:
        raise SystemExit(f'parse failed; raw at {RAW_OUT}')

    clusters = parsed.get('clusters', [])
    singletons = parsed.get('singletons', [])
    print(f'\nclusters proposed: {len(clusters)}', flush=True)
    print(f'singletons: {len(singletons)}', flush=True)

    catalogue = {
        'model': MODEL, 'cost_usd': round(cost,4), 'wall_seconds': round(wall,1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'sample_size': len(sample),
        'clusters': clusters,
        'singletons': singletons,
    }
    CATALOGUE_OUT.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False))
    print(f'\nwrote {CATALOGUE_OUT}', flush=True)
    print(f'  e.g. first 3 clusters:')
    for c in clusters[:3]:
        print(f"    [{c.get('cluster_id')}] {c.get('canonical_name')}")
        print(f"       sig: {(c.get('mechanism_signature') or '')[:120]}")


if __name__ == '__main__':
    main()
