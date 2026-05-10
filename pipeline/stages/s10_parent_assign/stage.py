"""Stage 10 — Pass 2: cluster-to-parent assignment.

Generalises:
    corpora/arena/clustering_v2/closure/code/13_opus_assign_clusters.py

One-shot assignment of every cluster in the catalogue to one of the
parents from s09 (or 'none' if no parent fits).

Domain config (domain.yaml stages.parent_assign):
    model: claude-opus-4-7
    max_tokens: 128000
    catalogue_path, parents_path, output_path, output_meta
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.stages.shared import stream_call, parse_json_tolerant

ROOT = Path(__file__).resolve().parents[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('parent_assign')

    model = s.get('model', 'claude-opus-4-7')
    max_tokens = s.get('max_tokens', 128_000)

    catalogue_path = Path(s.get('catalogue_path') or '')
    if not catalogue_path.is_absolute() and catalogue_path.parts:
        catalogue_path = ROOT / catalogue_path
    parents_path = Path(s.get('parents_path') or '')
    if not parents_path.is_absolute() and parents_path.parts:
        parents_path = ROOT / parents_path
    output_path = Path(s.get('output_path') or '')
    if not output_path.is_absolute() and output_path.parts:
        output_path = ROOT / output_path
    output_meta = Path(s.get('output_meta') or '')
    if not output_meta.is_absolute() and output_meta.parts:
        output_meta = ROOT / output_meta

    catalogue = json.load(catalogue_path.open())
    clusters = catalogue.get('clusters') if isinstance(catalogue, dict) and 'clusters' in catalogue else catalogue
    parents_data = json.load(parents_path.open())
    if 'derivation' in parents_data:
        parents = parents_data['derivation']['parents']
    elif 'parents' in parents_data:
        parents = parents_data['parents']
    else:
        parents = parents_data
    valid_pids = {p.get('parent_id') for p in parents}
    print(f'{len(clusters)} clusters, {len(parents)} parents', flush=True)

    parent_lines = []
    for p in parents:
        parent_lines.append(f"### {p.get('parent_id', '?')}: {p.get('name', '?')}")
        parent_lines.append(f"Description: {p.get('description', '')}")
        parent_lines.append(f"Mechanism criterion: {p.get('mechanism_criterion', '')}")
        parent_lines.append('')
    parent_block = '\n'.join(parent_lines)

    cluster_lines = []
    for c in clusters:
        cid = c['cluster_id']
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        n = len(c.get('supporting_record_ids', c.get('seed_members', [])))
        cluster_lines.append(f'  {cid} | {name} | {sig} | {n}')
    cluster_block = '\n'.join(cluster_lines)

    template = cfg.prompt('prompt', stage='s10_parent_assign')
    prompt = template.format(parent_block=parent_block, cluster_block=cluster_block)
    print(f'prompt: {len(prompt):,} chars', flush=True)

    client = anthropic.Anthropic()
    text, msg, cost, wall = stream_call(
        client, prompt, model=model, max_tokens=max_tokens, label='parent_assign',
    )
    parsed = parse_json_tolerant(text)
    if not parsed or 'assignments' not in parsed:
        raise SystemExit(f'parse failed')

    assigns = parsed['assignments']
    print(f'returned {len(assigns)} assignments (input {len(clusters)})', flush=True)

    bad = [a for a in assigns if a.get('parent_id') not in valid_pids and a.get('parent_id') != 'none']
    seen = {a.get('cluster_id') for a in assigns}
    input_ids = {c['cluster_id'] for c in clusters}
    missing = input_ids - seen

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w') as f:
        for a in assigns:
            f.write(json.dumps(a) + '\n')

    parent_counter = Counter(a.get('parent_id') for a in assigns)
    confidence_counter = Counter(a.get('confidence') for a in assigns)

    if output_meta.parts:
        output_meta.parent.mkdir(parents=True, exist_ok=True)
        output_meta.write_text(json.dumps({
            'model': model, 'max_tokens': max_tokens,
            'input_tokens': msg.usage.input_tokens,
            'output_tokens': msg.usage.output_tokens,
            'cost_usd': round(cost, 4),
            'wall_seconds': round(wall, 1),
            'n_clusters_input': len(clusters),
            'n_assignments_output': len(assigns),
            'n_missing_clusters': len(missing),
            'n_invalid_parent_ids': len(bad),
            'confidence_distribution': dict(confidence_counter),
            'parent_assignment_distribution': dict(parent_counter),
        }, indent=2))

    print(f'\nconfidence: {dict(confidence_counter)}', flush=True)
    print(f'missing: {len(missing)}, invalid parent_ids: {len(bad)}', flush=True)
    print(f'wrote {output_path}', flush=True)


if __name__ == '__main__':
    main()
