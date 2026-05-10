"""Stage 05 — Seed cluster catalogue.

Generalises:
    corpora/arena/clustering_v2/code/05_seed_clusters.py
    corpora/anao/n100_demo/code/anao_n100_seed.py

Stratified sample from filter_input.jsonl → single LLM call → initial
mechanism-cluster catalogue.

Stratification: top-N values of <stratification_field> × axis_combos × per_cell.

Domain config (domain.yaml stages.cluster_seed):
    model: claude-sonnet-4-6
    max_tokens: 32000
    seed: 42
    input_path: filter_input.jsonl
    output_catalogue: cluster_catalogue.json (seed)
    output_sample: seed_sample.jsonl
    output_raw: seed_response_raw.txt
    stratification_field: kb_category | portfolio
    top_n_categories: 8
    top_categories: optional explicit list (overrides top_n auto-detection)
    axis_combos: [occ_mech, mech_only, occ_only]
    per_cell: 15

Prompt template: pipeline/stages/s05_cluster_seed/prompt.md
Tokens used: {corpus_short_description}, {audience_persona},
             {topic_axis_examples}, {primary_grouping_field},
             {record_id_prefix}, {cluster_id_prefix}
"""
from __future__ import annotations
import argparse
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.stages.shared import stream_call, parse_json_tolerant

ROOT = Path(__file__).resolve().parents[3]


AXIS_COMBO_PREDICATES = {
    'occ_mech':  lambda r: r.get('is_occurrence') == 'yes' and r.get('is_mechanism') == 'yes',
    'mech_only': lambda r: r.get('is_mechanism') == 'yes' and r.get('is_occurrence') == 'no',
    'occ_only':  lambda r: r.get('is_occurrence') == 'yes' and r.get('is_mechanism') == 'no',
    'lesson_or_rec': lambda r: ((r.get('is_lesson') == 'yes' or r.get('is_recommendation') == 'yes')
                                 and (r.get('is_mechanism') == 'yes' or r.get('is_occurrence') == 'yes')),
}


def stratified_sample(rows, strat_field, top_categories, axis_combos, per_cell, seed=42):
    rng = random.Random(seed)
    by_cell = defaultdict(list)
    for r in rows:
        cat = (r.get(strat_field) or r.get(f'_{strat_field}') or '').strip() if isinstance(
            r.get(strat_field) or r.get(f'_{strat_field}'), str) else ''
        if top_categories and cat not in top_categories:
            continue
        for combo_name in axis_combos:
            pred = AXIS_COMBO_PREDICATES[combo_name]
            if pred(r):
                by_cell[(cat, combo_name)].append(r)
                break

    sample = []
    for (cat, combo), pool in by_cell.items():
        rng.shuffle(pool)
        for r in pool[:per_cell]:
            r = dict(r)
            r['_seed_cat'] = cat
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
            if r.get(ax) == 'yes': axes.append(ax[3:])
        v = r.get('valence', '')
        lines.append(f'\n## {rid}  [{cat[:30]}]  [axes: {",".join(axes)}; v: {v}]')
        lines.append(f'narrative: {narr}')
        if evi and evi != narr:
            lines.append(f'evidence: {evi[:600]}')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('cluster_seed')

    model = s.get('model', 'claude-sonnet-4-6')
    max_tokens = s.get('max_tokens', 32000)
    seed = s.get('seed', 42)
    strat_field = s.get('stratification_field', 'kb_category')
    top_n = s.get('top_n_categories', 8)
    explicit_top = s.get('top_categories')
    axis_combos = s.get('axis_combos', ['occ_mech', 'mech_only', 'occ_only'])
    per_cell = s.get('per_cell', 15)

    input_path = Path(s.get('input_path') or '')
    if not input_path.is_absolute() and input_path.parts:
        input_path = ROOT / input_path
    out_catalogue = Path(s.get('output_catalogue') or '')
    if not out_catalogue.is_absolute() and out_catalogue.parts:
        out_catalogue = ROOT / out_catalogue
    out_sample = Path(s.get('output_sample') or '')
    if not out_sample.is_absolute() and out_sample.parts:
        out_sample = ROOT / out_sample
    out_raw = Path(s.get('output_raw') or '')
    if not out_raw.is_absolute() and out_raw.parts:
        out_raw = ROOT / out_raw

    rows = [json.loads(l) for l in input_path.open()]
    print(f'pool: {len(rows):,} records', flush=True)

    # Determine top categories
    if explicit_top:
        top_categories = explicit_top
    else:
        cat_counts = Counter()
        for r in rows:
            cat = (r.get(strat_field) or r.get(f'_{strat_field}') or '').strip() if isinstance(
                r.get(strat_field) or r.get(f'_{strat_field}'), str) else ''
            if cat: cat_counts[cat] += 1
        top_categories = [c for c, _ in cat_counts.most_common(top_n)]
    print(f'stratification: field={strat_field}  top categories={len(top_categories)}', flush=True)

    sample = stratified_sample(rows, strat_field, top_categories, axis_combos, per_cell, seed=seed)
    print(f'sample: {len(sample)} records', flush=True)

    if out_sample.parts:
        out_sample.parent.mkdir(parents=True, exist_ok=True)
        with out_sample.open('w') as f:
            for r in sample:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')

    record_block = build_record_block(sample)
    template = cfg.prompt('prompt', stage='s05_cluster_seed')
    prompt = template + '\n' + record_block
    print(f'prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tok)', flush=True)

    if args.dry_run:
        print('dry-run; not calling API'); return

    client = anthropic.Anthropic()
    text, msg, cost, wall = stream_call(
        client, prompt, model=model, max_tokens=max_tokens,
        raw_path=out_raw if out_raw.parts else None, label='seed',
    )
    parsed = parse_json_tolerant(text)
    if not parsed or 'clusters' not in parsed:
        raise SystemExit(f'parse failed; raw at {out_raw}')

    clusters = parsed.get('clusters', [])
    singletons = parsed.get('singletons', [])
    print(f'\nclusters: {len(clusters)}  singletons: {len(singletons)}', flush=True)

    catalogue = {
        'model': model, 'cost_usd': round(cost, 4), 'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'sample_size': len(sample),
        'clusters': clusters,
        'singletons': singletons,
    }
    out_catalogue.parent.mkdir(parents=True, exist_ok=True)
    out_catalogue.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False))
    print(f'wrote {out_catalogue}', flush=True)


if __name__ == '__main__':
    main()
