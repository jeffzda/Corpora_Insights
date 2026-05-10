"""Stage 09 — Parent-category derivation from cluster catalogue.

Generalises:
    corpora/arena/clustering_v2/closure/code/12_opus_derive_parents.py
    corpora/anao/n100_demo/code/anao_n100_derive_parents.py

Single Opus call ingests cluster catalogue + per-cluster record counts
and proposes parent categories grouping clusters by mechanism class.

Domain config (domain.yaml stages.parent_derive):
    model: claude-opus-4-7
    max_tokens: 32000
    catalogue_path: final cluster catalogue (after s08)
    assignments_paths: list of paths to compute n_records per cluster
    output_json, output_md, output_raw
"""
from __future__ import annotations
import argparse
import json
import time
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
    s = cfg.stage('parent_derive')

    model = s.get('model', 'claude-opus-4-7')
    max_tokens = s.get('max_tokens', 32_000)

    catalogue_path = Path(s.get('catalogue_path') or '')
    if not catalogue_path.is_absolute() and catalogue_path.parts:
        catalogue_path = ROOT / catalogue_path
    assignments_paths = [Path(p) for p in (s.get('assignments_paths') or [])]
    assignments_paths = [p if p.is_absolute() else ROOT / p for p in assignments_paths]

    output_json = Path(s.get('output_json') or '')
    if not output_json.is_absolute() and output_json.parts:
        output_json = ROOT / output_json
    output_md = Path(s.get('output_md') or '')
    if not output_md.is_absolute() and output_md.parts:
        output_md = ROOT / output_md
    output_raw = Path(s.get('output_raw') or '')
    if not output_raw.is_absolute() and output_raw.parts:
        output_raw = ROOT / output_raw

    catalogue = json.load(catalogue_path.open())['clusters']
    print(f'catalogue: {len(catalogue)} clusters', flush=True)

    # n_records per cluster
    counts = Counter()
    for path in assignments_paths:
        if not path.exists(): continue
        for line in path.open():
            a = json.loads(line)
            cid = a.get('cluster_id')
            if cid and cid != 'orphan':
                counts[cid] += 1

    cluster_lines = []
    for c in catalogue:
        cid = c['cluster_id']
        n = counts.get(cid, len(c.get('seed_members', [])))
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        cluster_lines.append(f'{cid} | {name} | {sig} | {n}')
    cluster_block = '\n'.join(cluster_lines)

    template = cfg.prompt('prompt', stage='s09_parent_derive')
    prompt = template.format(
        n_clusters=len(catalogue),
        cluster_block=cluster_block,
    )
    print(f'prompt: {len(prompt):,} chars', flush=True)

    client = anthropic.Anthropic()
    text, msg, cost, wall = stream_call(
        client, prompt, model=model, max_tokens=max_tokens,
        raw_path=output_raw if output_raw.parts else None, label='parent_derive',
    )
    parsed = parse_json_tolerant(text)
    if not parsed or 'parents' not in parsed:
        raise SystemExit(f'parse failed; raw at {output_raw}')

    parents = parsed.get('parents', [])
    unassigned = parsed.get('unassigned', [])
    print(f'parents: {len(parents)}  unassigned: {len(unassigned)}', flush=True)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    json.dump({
        'model': model, 'cost': round(cost, 4), 'wall_seconds': round(wall, 1),
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'n_clusters': len(catalogue), 'n_parents': len(parents),
        'n_unassigned': len(unassigned),
        'derivation': parsed,
    }, output_json.open('w'), indent=2)

    if output_md.parts:
        md = ['# Parent set derived from {} clusters'.format(len(catalogue)), '',
              f'Single {model} call. {len(catalogue)} clusters → {len(parents)} parents. '
              f'${cost:.2f}, {wall:.0f}s.', '',
              f'**Unassigned:** {len(unassigned)}', '',
              '## Parents', '',
              '| parent_id | name | est. population | mechanism criterion |',
              '|---|---|---|---|']
        for p in parents:
            crit = (p.get('mechanism_criterion') or '—')[:120]
            md.append(f"| {p.get('parent_id','?')} | {p.get('name','?')} | "
                      f"{p.get('estimated_population','?')} | {crit} |")
        md.append('')
        md.append('## Full parent definitions')
        md.append('')
        for p in parents:
            md += [f"### {p.get('parent_id','?')} — {p.get('name','?')}", '',
                   p.get('description', ''), '',
                   f"**Mechanism criterion:** {p.get('mechanism_criterion','?')}", '']
            ex = p.get('exemplar_cluster_ids', [])
            if ex:
                md.append(f"**Exemplar clusters:** {', '.join(ex)}")
            md.append(f"**Estimated population:** {p.get('estimated_population','?')}")
            md.append('')
        if unassigned:
            md += ['## Unassigned', '', '| cluster_id | reason |', '|---|---|']
            for u in unassigned:
                md.append(f"| {u.get('cluster_id','?')} | {u.get('reason','')[:200]} |")
        notes = parsed.get('notes')
        if notes:
            md += ['', '## Notes', '', notes]
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text('\n'.join(md))
        print(f'wrote {output_md}', flush=True)

    print(f'wrote {output_json}', flush=True)


if __name__ == '__main__':
    main()
