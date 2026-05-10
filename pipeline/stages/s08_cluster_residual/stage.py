"""Stage 08 — Residual orphan cohort clustering (Pass 2 only).

Generalises:
    corpora/arena/clustering_v2/code/14_residual_orphan_cluster.py
    corpora/anao/n100_demo/code/anao_n100_residual_cluster.py

The residual orphans from s07 (rejected by both the matured catalogue
and Pass 2 across iterations) are tested AS A COHORT for the first
time. Any ≥3-record clusters they share with each other are recovered.

Domain config (domain.yaml stages.cluster_residual):
    model, max_tokens
    input_path: filter_input.jsonl
    catalogue_path: matured catalogue (after singleton sweep)
    residual_path: residual_orphans.json (from s07)
    output_dir: residual/ subdirectory
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.stages.shared import stream_call, parse_json_tolerant

ROOT = Path(__file__).resolve().parents[3]


def build_orphan_block(records):
    lines = []
    for r in records:
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
    return ''.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('cluster_residual')

    model = s.get('model', 'claude-sonnet-4-6')
    max_tokens = s.get('max_tokens', 64_000)

    input_path = Path(s.get('input_path') or '')
    if not input_path.is_absolute() and input_path.parts:
        input_path = ROOT / input_path
    catalogue_path = Path(s.get('catalogue_path') or '')
    if not catalogue_path.is_absolute() and catalogue_path.parts:
        catalogue_path = ROOT / catalogue_path
    residual_path = Path(s.get('residual_path') or '')
    if not residual_path.is_absolute() and residual_path.parts:
        residual_path = ROOT / residual_path
    output_dir = Path(s.get('output_dir') or '')
    if not output_dir.is_absolute() and output_dir.parts:
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    new_catalogue_out = output_dir / 'catalogue_after_residual.json'
    assignments_out = output_dir / 'residual_assignments.jsonl'
    new_clusters_out = output_dir / 'residual_new_clusters.json'
    true_singletons_out = output_dir / 'true_singletons.json'
    raw_out = output_dir / 'residual_raw.txt'
    meta_out = output_dir / 'meta.json'

    template = cfg.prompt('orphan_prompt', stage='s08_cluster_residual')

    catalogue = json.load(catalogue_path.open())
    residual_ids = json.load(residual_path.open())
    rows = [json.loads(l) for l in input_path.open()]
    rid_to_record = {r['record_id']: r for r in rows}
    residual_records = [rid_to_record[r] for r in residual_ids if r in rid_to_record]
    print(f'catalogue: {len(catalogue["clusters"])} clusters', flush=True)
    print(f'residual orphans: {len(residual_records):,}', flush=True)

    orphan_block = build_orphan_block(residual_records)
    prompt = template.format(orphan_records_block=orphan_block)
    print(f'prompt: {len(prompt):,} chars', flush=True)

    client = anthropic.Anthropic()
    text, msg, cost, wall = stream_call(
        client, prompt, model=model, max_tokens=max_tokens,
        raw_path=raw_out, label='residual', temperature=0.0,
    )
    parsed = parse_json_tolerant(text)
    new_clusters = parsed.get('clusters', []) or parsed.get('_recovered', [])
    print(f'new clusters proposed: {len(new_clusters)}', flush=True)

    nci = catalogue.get('next_cluster_id',
                         max([int(c['cluster_id'][1:]) for c in catalogue['clusters']] + [0]) + 1)
    placed_ids = set()
    new_assigns = []
    accepted = []
    for nc in new_clusters:
        members = nc.get('supporting_record_ids', [])
        if len(members) < 3: continue
        new_id = f'c{nci:03d}'
        cat_entry = {
            'cluster_id': new_id,
            'canonical_name': nc.get('canonical_name', '?'),
            'mechanism_signature': nc.get('mechanism_signature', ''),
            'created_iter': 'residual',
            'seed_members': members,
        }
        catalogue['clusters'].append(cat_entry)
        accepted.append(cat_entry)
        for rid in members:
            new_assigns.append({'record_id': rid, 'cluster_id': new_id, 'method': 'residual_pass2'})
            placed_ids.add(rid)
        nci += 1
    catalogue['next_cluster_id'] = nci

    new_catalogue_out.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False))
    with assignments_out.open('w') as f:
        for a in new_assigns: f.write(json.dumps(a) + '\n')
    new_clusters_out.write_text(json.dumps(accepted, indent=2, ensure_ascii=False))

    true_singletons = sorted(rid for rid in residual_ids if rid not in placed_ids)
    true_singletons_out.write_text(json.dumps(true_singletons, indent=2))

    meta_out.write_text(json.dumps({
        'n_residual_input': len(residual_records),
        'n_new_clusters': len(accepted),
        'n_records_placed': len(new_assigns),
        'n_true_singletons': len(true_singletons),
        'placement_rate': round(len(new_assigns)/max(len(residual_records),1), 3),
        'final_catalogue_size': len(catalogue['clusters']),
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
    }, indent=2))

    print(f'\n=== residual clustering done ===')
    print(f'  new clusters: {len(accepted)}')
    print(f'  records placed: {len(new_assigns)}')
    print(f'  true singletons: {len(true_singletons)}')
    print(f'  final catalogue: {len(catalogue["clusters"])}')
    print(f'  cost: ${cost:.2f}')


if __name__ == '__main__':
    main()
