#!/usr/bin/env python3
"""ANAO N=100 — Phase 4d: pending singleton reclassify.

Mirrors corpora/arena/clustering_v2/code/13_pending_reclassify.py with
the Arm-D winning configuration: batched (200/call) + neutral prompt
(no defensive force-fit warning).

Re-runs Pass 1 only on the 493 pending singletons against the matured
189-cluster catalogue. Records that classify successfully get appended
to a fresh assignments file. Records that stay orphan are written to
residual_orphans.json.
"""
import argparse
import json
import random
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
INPUT = OUT_DIR / 'anao_n100_filter_input.jsonl'
SWEEP_DIR = OUT_DIR / 'sweep'
CATALOGUE = SWEEP_DIR / 'cluster_catalogue.json'
PENDING = SWEEP_DIR / 'pending_singletons.json'

RECLASS_DIR = SWEEP_DIR / 'reclassify'
RECLASS_DIR.mkdir(parents=True, exist_ok=True)
ASSIGN_OUT = RECLASS_DIR / 'reclassified_assignments.jsonl'
RESIDUAL_OUT = RECLASS_DIR / 'residual_orphans.json'
META_OUT = RECLASS_DIR / 'meta.json'

MODEL = 'claude-sonnet-4-6'
BATCH_SIZE = 200
MAX_TOKENS = 128_000


# Neutral batched prompt (Arm D, ARENA's winning combination)
NEUTRAL_BATCHED_HEADER = """You are classifying ANAO performance-audit records against a catalogue of failure-mode clusters.

For each record, your goal is to assign it to one of the listed clusters if one of them reasonably describes the causal failure mechanism the record discusses. If no existing cluster fits, return cluster_id="orphan".

# CATALOGUE OF FAILURE-MODE CLUSTERS"""

NEUTRAL_BATCHED_FOOTER = """# OUTPUT FORMAT

Return JSON only:
{
  "assignments": [
    {"record_id": "ANAOM-...", "cluster_id": "c042"},
    {"record_id": "ANAOM-...", "cluster_id": "orphan"}
  ]
}

One assignment per input record, in input order. cluster_id must be either an existing catalogue id (e.g. "c042") or the literal string "orphan"."""


def build_neutral_prompt(catalogue, records):
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
    return NEUTRAL_BATCHED_HEADER + ''.join(cat_lines) + '\n\n# RECORDS TO CLASSIFY' + \
           ''.join(rec_lines) + '\n\n' + NEUTRAL_BATCHED_FOOTER


def stream_call(client, prompt, label='call'):
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS, temperature=0.0,
        messages=[{'role':'user','content':prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars-last_chars)/max(now-last_print,1)
                print(f'  [{label}] [{int(now-started)}s] {text_chars:,} chars +{rate:.0f} c/s', flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    return ''.join(parts), msg


def parse_json_tolerant(text):
    import re
    m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try: return json.loads(body)
    except json.JSONDecodeError:
        first = body.find('{'); last = body.rfind('}')
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: pass
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    catalogue = json.load(CATALOGUE.open())['clusters']
    valid_ids = {c['cluster_id'] for c in catalogue}
    pending_ids = list(json.load(PENDING.open()))
    rows = [json.loads(l) for l in INPUT.open()]
    rid_to_record = {r['record_id']: r for r in rows}
    print(f'catalogue: {len(catalogue)} clusters', flush=True)
    print(f'pending: {len(pending_ids):,} records', flush=True)

    todo = [rid for rid in pending_ids if rid in rid_to_record]
    print(f'to process: {len(todo):,}', flush=True)
    rng = random.Random(args.seed)
    rng.shuffle(todo)

    client = anthropic.Anthropic()
    started = time.time()
    cum_in = cum_out = cum_cost = 0.0
    n_classified = n_orphan = n_invalid = 0
    out_f = ASSIGN_OUT.open('w')

    n_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_i in range(n_batches):
        ids = todo[batch_i*BATCH_SIZE:(batch_i+1)*BATCH_SIZE]
        records = [rid_to_record[rid] for rid in ids]
        prompt = build_neutral_prompt(catalogue, records)
        t0 = time.time()
        text, msg = stream_call(client, prompt, label=f'b{batch_i+1}/{n_batches}')
        wall = time.time() - t0
        parsed = parse_json_tolerant(text)
        raw_assigns = parsed.get('assignments', [])
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

        in_tok = msg.usage.input_tokens
        out_tok = msg.usage.output_tokens
        cost = in_tok/1e6*3 + out_tok/1e6*15
        cum_in += in_tok; cum_out += out_tok; cum_cost += cost
        n_classified += b_classified; n_orphan += b_orphan; n_invalid += b_invalid

        print(f'  batch {batch_i+1}/{n_batches}: {b_classified} classified, '
              f'{b_orphan} orphan ({b_invalid} invalid→orphan)  '
              f'{in_tok:,}in/{out_tok:,}out  ${cost:.3f}  {wall:.0f}s  '
              f'cumulative ${cum_cost:.2f}', flush=True)

    out_f.close()

    residuals = []
    for line in ASSIGN_OUT.open():
        rec = json.loads(line)
        if rec.get('cluster_id') == 'orphan':
            residuals.append(rec['record_id'])
    RESIDUAL_OUT.write_text(json.dumps(sorted(set(residuals)), indent=2))

    META_OUT.write_text(json.dumps({
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
        'batch_size': BATCH_SIZE,
        'catalogue_size': len(catalogue),
    }, indent=2))

    print(f'\n=== DONE ===')
    print(f'  Processed: {len(todo):,}')
    print(f'  Classified: {n_classified:,} ({100*n_classified/max(len(todo),1):.1f}%)')
    print(f'  Orphan: {n_orphan:,} ({100*n_orphan/max(len(todo),1):.1f}%)')
    print(f'  Cost: ${cum_cost:.2f}')
    print(f'  Wall: {(time.time()-started)/60:.1f} min')


if __name__ == '__main__':
    main()
