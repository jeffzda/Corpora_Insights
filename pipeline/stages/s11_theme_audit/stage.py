"""Stage 11 — Pass 3: theme audit + parent grouping.

Generalises:
    corpora/arena/clustering_v2/closure/code/14_opus_themes_audit.py

Single Opus call: (a) audits each parent (verdict, mechanism_coherence,
distinctness, population_fit), (b) groups parents into themes derived
from mechanism similarity.

Domain config (domain.yaml stages.theme_audit):
    model, max_tokens
    catalogue_path, parents_path, assignments_path
    output_path, output_meta
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
    s = cfg.stage('theme_audit')

    model = s.get('model', 'claude-opus-4-7')
    max_tokens = s.get('max_tokens', 128_000)

    catalogue_path = Path(s.get('catalogue_path') or '')
    if not catalogue_path.is_absolute() and catalogue_path.parts:
        catalogue_path = ROOT / catalogue_path
    parents_path = Path(s.get('parents_path') or '')
    if not parents_path.is_absolute() and parents_path.parts:
        parents_path = ROOT / parents_path
    assignments_path = Path(s.get('assignments_path') or '')
    if not assignments_path.is_absolute() and assignments_path.parts:
        assignments_path = ROOT / assignments_path
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
    assigns = [json.loads(l) for l in assignments_path.open()]
    print(f'{len(clusters)} clusters, {len(parents)} parents, {len(assigns)} assignments',
          flush=True)

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
        cluster_lines.append(f"  {cid} | {name} | {sig} | {n}")
    cluster_block = '\n'.join(cluster_lines)

    assignment_lines = []
    for a in assigns:
        cid = a.get('cluster_id', '?')
        pid = a.get('parent_id', '?')
        conf = a.get('confidence', '?')
        assignment_lines.append(f"  {cid} -> {pid} ({conf})")
    assignment_block = '\n'.join(assignment_lines)

    template = cfg.prompt('prompt', stage='s11_theme_audit')
    prompt = template.format(
        parent_block=parent_block,
        cluster_block=cluster_block,
        assignment_block=assignment_block,
    )
    print(f'prompt: {len(prompt):,} chars', flush=True)

    client = anthropic.Anthropic()
    text, msg, cost, wall = stream_call(
        client, prompt, model=model, max_tokens=max_tokens, label='theme_audit',
    )
    parsed = parse_json_tolerant(text)
    if not parsed:
        raise SystemExit('parse failed')

    audit = parsed.get('audit', {})
    themes = parsed.get('themes', [])
    unthemed = parsed.get('unthemed_parents', [])
    per = audit.get('per_parent', [])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parsed, indent=2))

    verdicts = Counter(p.get('verdict', '?') for p in per)
    coherence = Counter(p.get('mechanism_coherence', '?') for p in per)
    pop_fit = Counter(p.get('population_fit', '?') for p in per)

    if output_meta.parts:
        valid_pids = {p.get('parent_id') for p in parents}
        in_themes = [pid for t in themes for pid in t.get('parent_ids', [])]
        in_themes_set = set(in_themes)
        in_unthemed_set = {u.get('parent_id') for u in unthemed}
        missing_pids = valid_pids - in_themes_set - in_unthemed_set
        duplicated = [pid for pid, n in Counter(in_themes).items() if n > 1]

        output_meta.parent.mkdir(parents=True, exist_ok=True)
        output_meta.write_text(json.dumps({
            'model': model, 'max_tokens': max_tokens,
            'input_tokens': msg.usage.input_tokens,
            'output_tokens': msg.usage.output_tokens,
            'cost_usd': round(cost, 4),
            'wall_seconds': round(wall, 1),
            'n_parents_input': len(parents),
            'n_themes_output': len(themes),
            'n_unthemed_output': len(unthemed),
            'verdict_distribution': dict(verdicts),
            'coherence_distribution': dict(coherence),
            'population_fit_distribution': dict(pop_fit),
            'parents_uncovered': sorted(missing_pids),
            'parents_duplicated_in_themes': duplicated,
        }, indent=2))

    print(f'\n=== AUDIT ===')
    print(f'verdicts: {dict(verdicts)}', flush=True)
    print(f'coherence: {dict(coherence)}', flush=True)
    print(f'pop fit: {dict(pop_fit)}', flush=True)
    print(f'\n=== THEMES ({len(themes)}) ===')
    for t in themes:
        print(f"  [{t.get('theme_id', '?')}] {t.get('name', '?')}  ({len(t.get('parent_ids', []))} parents)",
              flush=True)
    if unthemed:
        print(f'\nUnthemed: {len(unthemed)}')
    print(f'\nwrote {output_path}', flush=True)


if __name__ == '__main__':
    main()
