"""Stage 06 — Corpus sweep (Pass 1 + Pass 2 per batch).

Generalises:
    corpora/arena/clustering_v2/code/07_corpus_sweep.py
    corpora/arena/clustering_v2/code/06_classify_and_cluster_orphans.py
    corpora/anao/n100_demo/code/anao_n100_sweep.py

Iterative bootstrap-merge: take BATCH_SIZE unprocessed records → Pass 1
(classify against current catalogue) → Pass 2 (cluster batch's orphans
into new ≥3-record clusters) → append to catalogue → checkpoint.

Records that even Pass 2 can't cluster accumulate as pending singletons.

Domain config (domain.yaml stages.cluster_sweep):
    model: claude-sonnet-4-6
    max_tokens: 128000
    batch_size: 200
    seed: 42
    input_path: filter_input.jsonl
    seed_catalogue_path: cluster_catalogue.json (from s05)
    output_dir: sweep/ directory
    max_iterations: int (optional, default infinite)
"""
from __future__ import annotations
import argparse
import json
import random
import time
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig
from pipeline.stages.shared import stream_call, parse_json_tolerant

ROOT = Path(__file__).resolve().parents[3]


def build_classify_prompt(template, catalogue, records):
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
    # Template has {catalogue_block} and {records_block} placeholders
    return template.format(
        catalogue_block=''.join(cat_lines),
        records_block=''.join(rec_lines),
    )


def build_orphan_prompt(template, orphan_records):
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
    return template.format(orphan_records_block=''.join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    ap.add_argument('--max-iterations', type=int, default=999)
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('cluster_sweep')

    model = s.get('model', 'claude-sonnet-4-6')
    max_tokens = s.get('max_tokens', 128_000)
    batch_size = s.get('batch_size', 200)
    seed = s.get('seed', 42)

    input_path = Path(s.get('input_path') or '')
    if not input_path.is_absolute() and input_path.parts:
        input_path = ROOT / input_path
    seed_catalogue_path = Path(s.get('seed_catalogue_path') or '')
    if not seed_catalogue_path.is_absolute() and seed_catalogue_path.parts:
        seed_catalogue_path = ROOT / seed_catalogue_path
    output_dir = Path(s.get('output_dir') or '')
    if not output_dir.is_absolute() and output_dir.parts:
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    catalogue_path = output_dir / 'cluster_catalogue.json'
    assignments_path = output_dir / 'corpus_assignments.jsonl'
    pending_path = output_dir / 'pending_singletons.json'
    state_path = output_dir / 'sweep_state.json'

    # Load prompts
    classify_template = cfg.prompt('classify_prompt', stage='s06_cluster_sweep')
    orphan_template = cfg.prompt('orphan_prompt', stage='s06_cluster_sweep')

    # Load inputs
    rows = [json.loads(l) for l in input_path.open()]
    by_id = {r['record_id']: r for r in rows}
    print(f'pool: {len(rows):,}', flush=True)

    # Initial catalogue from seed (or resume from checkpoint)
    if catalogue_path.exists():
        catalogue = json.load(catalogue_path.open())
    else:
        seed_data = json.load(seed_catalogue_path.open())
        catalogue = {
            'clusters': seed_data.get('clusters', []),
            'next_cluster_id': max(
                [int(c['cluster_id'][1:]) for c in seed_data.get('clusters', []) if c['cluster_id'][0].isalpha()] + [0]
            ) + 1,
        }
    if state_path.exists():
        state = json.load(state_path.open())
    else:
        state = {'iteration': 0, 'processed_record_ids': [], 'pending_singleton_ids': []}
    print(f'catalogue: {len(catalogue["clusters"])} clusters', flush=True)
    print(f'state: iter {state["iteration"]}, processed {len(state["processed_record_ids"])}',
          flush=True)

    processed = set(state['processed_record_ids'])
    remaining = [r for r in rows if r['record_id'] not in processed]
    rng = random.Random(seed)
    rng.shuffle(remaining)

    client = anthropic.Anthropic()

    iter_idx = state['iteration']
    while remaining and iter_idx - state['iteration'] < args.max_iterations:
        iter_idx += 1
        batch = remaining[:batch_size]
        remaining = remaining[batch_size:]
        print(f"\n=== iter {iter_idx} | batch {len(batch)} | catalogue {len(catalogue['clusters'])} | remaining {len(remaining):,} ===",
              flush=True)

        # Pass 1
        p1_prompt = build_classify_prompt(classify_template, catalogue['clusters'], batch)
        p1_raw = output_dir / f'iteration_{iter_idx:03d}_pass1_raw.txt'
        p1_text, p1_msg, p1_cost, _ = stream_call(
            client, p1_prompt, model=model, max_tokens=max_tokens,
            raw_path=p1_raw, label=f'p1-i{iter_idx}', temperature=0.0,
        )
        p1_parsed = parse_json_tolerant(p1_text)
        assigns = p1_parsed.get('assignments', []) or p1_parsed.get('_recovered', [])

        classified = [a for a in assigns if a.get('cluster_id') and a.get('cluster_id') != 'orphan']
        orphans = [a for a in assigns if a.get('cluster_id') == 'orphan']
        seen = {a.get('record_id') for a in assigns}
        missing = [r for r in batch if r['record_id'] not in seen]
        print(f'  P1: {len(classified)} classified, {len(orphans)} orphan, {len(missing)} missing',
              flush=True)

        # Pass 2
        orphan_records = [by_id[a['record_id']] for a in orphans if a.get('record_id') in by_id]
        orphan_records.extend(r for r in missing)

        p2_clusters = []
        p2_cost = 0.0
        if orphan_records:
            p2_prompt = build_orphan_prompt(orphan_template, orphan_records)
            p2_raw = output_dir / f'iteration_{iter_idx:03d}_pass2_raw.txt'
            p2_text, p2_msg, p2_cost, _ = stream_call(
                client, p2_prompt, model=model, max_tokens=max_tokens,
                raw_path=p2_raw, label=f'p2-i{iter_idx}', temperature=0.0,
            )
            p2_parsed = parse_json_tolerant(p2_text)
            p2_clusters = p2_parsed.get('clusters', []) or p2_parsed.get('_recovered', [])
            print(f'  P2: {len(p2_clusters)} new clusters', flush=True)

        # Reconcile
        new_assignments = []
        nci = catalogue.get('next_cluster_id', max(
            [int(c['cluster_id'][1:]) for c in catalogue['clusters']] + [0]) + 1)
        accepted_clusters = []
        for nc in p2_clusters:
            members = nc.get('supporting_record_ids', [])
            if len(members) < 3: continue
            new_id = f'c{nci:03d}'
            cat_entry = {
                'cluster_id': new_id,
                'canonical_name': nc.get('canonical_name', '?'),
                'mechanism_signature': nc.get('mechanism_signature', ''),
                'created_iter': iter_idx,
                'seed_members': members,
            }
            catalogue['clusters'].append(cat_entry)
            accepted_clusters.append(cat_entry)
            for rid in members:
                new_assignments.append({'record_id': rid, 'cluster_id': new_id, 'iter': iter_idx, 'via': 'pass2'})
            nci += 1
        catalogue['next_cluster_id'] = nci

        # Persist assignments
        with assignments_path.open('a') as f:
            for a in classified:
                f.write(json.dumps({**a, 'iter': iter_idx, 'via': 'pass1'}) + '\n')
            for a in new_assignments:
                f.write(json.dumps(a) + '\n')

        # Pending update
        placed_in_p2 = {rid for c in accepted_clusters for rid in c['seed_members']}
        new_pending = [r['record_id'] for r in orphan_records
                        if r['record_id'] not in placed_in_p2]
        state['pending_singleton_ids'].extend(new_pending)

        for r in batch:
            state['processed_record_ids'].append(r['record_id'])
        state['iteration'] = iter_idx

        catalogue_path.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False))
        state_path.write_text(json.dumps(state, indent=2))

        orphan_rate = len(orphans) / max(len(batch), 1) * 100
        print(f'  end of iter {iter_idx}: catalogue={len(catalogue["clusters"])}  '
              f'orphan_rate={orphan_rate:.1f}%  pending={len(state["pending_singleton_ids"])}',
              flush=True)

    pending_path.write_text(json.dumps(state['pending_singleton_ids'], indent=2))
    print(f'\nsweep complete: catalogue={len(catalogue["clusters"])} clusters, '
          f'pending={len(state["pending_singleton_ids"])}', flush=True)


if __name__ == '__main__':
    main()
