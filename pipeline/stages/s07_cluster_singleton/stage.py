"""Stage 07 — Pending singleton reclassify (Pass 1 only against matured catalogue).

Generalises:
    corpora/arena/clustering_v2/code/13_pending_reclassify.py
    corpora/arena/clustering_v2/code/12_batched_neutral_test.py
    corpora/anao/n100_demo/code/anao_n100_singleton_sweep.py

Re-runs Pass 1 only on pending singletons against the matured catalogue
from s06, using the Arm-D winning configuration: batched (200/call) +
neutral prompt (no defensive force-fit warning).

Records that classify successfully get appended to a fresh assignments
file; the rest go to residual_orphans.json.

Domain config (domain.yaml stages.cluster_singleton):
    model, batch_size, seed, input_path (filter_input.jsonl),
    catalogue_path (sweep cluster_catalogue.json),
    pending_path (sweep pending_singletons.json),
    output_dir (singleton/ subdirectory)
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


def build_neutral_prompt(template, catalogue, records):
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
    return template.format(
        catalogue_block=''.join(cat_lines),
        records_block=''.join(rec_lines),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('cluster_singleton')

    model = s.get('model', 'claude-sonnet-4-6')
    batch_size = s.get('batch_size', 200)
    max_tokens = s.get('max_tokens', 128_000)
    seed = s.get('seed', 42)

    input_path = Path(s.get('input_path') or '')
    if not input_path.is_absolute() and input_path.parts:
        input_path = ROOT / input_path
    catalogue_path = Path(s.get('catalogue_path') or '')
    if not catalogue_path.is_absolute() and catalogue_path.parts:
        catalogue_path = ROOT / catalogue_path
    pending_path = Path(s.get('pending_path') or '')
    if not pending_path.is_absolute() and pending_path.parts:
        pending_path = ROOT / pending_path
    output_dir = Path(s.get('output_dir') or '')
    if not output_dir.is_absolute() and output_dir.parts:
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    assigns_out = output_dir / 'reclassified_assignments.jsonl'
    residual_out = output_dir / 'residual_orphans.json'
    meta_out = output_dir / 'meta.json'

    template = cfg.prompt('classify_neutral_prompt', stage='s07_cluster_singleton')

    catalogue = json.load(catalogue_path.open())['clusters']
    valid_ids = {c['cluster_id'] for c in catalogue}
    pending_ids = list(json.load(pending_path.open()))
    rows = [json.loads(l) for l in input_path.open()]
    rid_to_record = {r['record_id']: r for r in rows}
    print(f'catalogue: {len(catalogue)} clusters', flush=True)
    print(f'pending: {len(pending_ids):,}', flush=True)

    todo = [rid for rid in pending_ids if rid in rid_to_record]
    print(f'to process: {len(todo):,}', flush=True)
    rng = random.Random(seed)
    rng.shuffle(todo)

    client = anthropic.Anthropic()
    started = time.time()
    cum_in = cum_out = cum_cost = 0.0
    n_classified = n_orphan = n_invalid = 0
    out_f = assigns_out.open('w')

    n_batches = (len(todo) + batch_size - 1) // batch_size
    for batch_i in range(n_batches):
        ids = todo[batch_i*batch_size:(batch_i+1)*batch_size]
        records = [rid_to_record[rid] for rid in ids]
        prompt = build_neutral_prompt(template, catalogue, records)
        text, msg, cost, wall = stream_call(
            client, prompt, model=model, max_tokens=max_tokens,
            label=f'b{batch_i+1}/{n_batches}', temperature=0.0,
        )
        parsed = parse_json_tolerant(text)
        raw_assigns = parsed.get('assignments', []) or parsed.get('_recovered', [])
        rid_to_cid = {a['record_id']: a['cluster_id'] for a in raw_assigns
                      if isinstance(a, dict) and 'record_id' in a}

        b_classified = b_orphan = b_invalid = 0
        for r in records:
            cid = rid_to_cid.get(r['record_id'], 'orphan')
            invalid = (cid != 'orphan' and cid not in valid_ids)
            if invalid:
                cid = 'orphan'; b_invalid += 1
            if cid == 'orphan': b_orphan += 1
            else: b_classified += 1
            row = {'record_id': r['record_id'], 'cluster_id': cid,
                   'batch': batch_i+1, 'method': 'singleton_reclassify_neutral'}
            out_f.write(json.dumps(row, ensure_ascii=False) + '\n')
        out_f.flush()

        cum_in += msg.usage.input_tokens
        cum_out += msg.usage.output_tokens
        cum_cost += cost
        n_classified += b_classified
        n_orphan += b_orphan
        n_invalid += b_invalid
        print(f'  batch {batch_i+1}/{n_batches}: {b_classified} classified, '
              f'{b_orphan} orphan ({b_invalid} invalid→orphan)  cumulative ${cum_cost:.2f}',
              flush=True)

    out_f.close()

    residuals = []
    for line in assigns_out.open():
        rec = json.loads(line)
        if rec.get('cluster_id') == 'orphan':
            residuals.append(rec['record_id'])
    residual_out.write_text(json.dumps(sorted(set(residuals)), indent=2))

    meta_out.write_text(json.dumps({
        'n_records_processed': len(todo),
        'n_classified': n_classified,
        'n_orphan': n_orphan,
        'n_invalid_assignments_coerced_to_orphan': n_invalid,
        'classification_rate': round(n_classified/max(len(todo),1), 3),
        'orphan_rate': round(n_orphan/max(len(todo),1), 3),
        'total_input_tokens': cum_in,
        'total_output_tokens': cum_out,
        'total_cost_sync': round(cum_cost, 3),
        'wall_seconds': round(time.time()-started, 1),
        'method': 'singleton_reclassify_neutral',
        'batch_size': batch_size,
        'catalogue_size': len(catalogue),
    }, indent=2))

    print(f'\n=== DONE ===')
    print(f'  Processed: {len(todo):,}')
    print(f'  Classified: {n_classified:,} ({100*n_classified/max(len(todo),1):.1f}%)')
    print(f'  Orphan: {n_orphan:,} ({100*n_orphan/max(len(todo),1):.1f}%)')
    print(f'  Cost: ${cum_cost:.2f}')


if __name__ == '__main__':
    main()
