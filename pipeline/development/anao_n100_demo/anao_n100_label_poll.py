#!/usr/bin/env python3
"""Poll/download/parse the ANAO N=100 6-axis tagging batch.

Mirrors the canonical ARENA poller:
  corpora/arena/canonical/narrative/runs/2026-05-02-record-type-pilot/code/poll_corpus_opus.py

Usage:
  python3 anao_n100_label_poll.py             # status only
  python3 anao_n100_label_poll.py --download  # fetch + parse + write tags.json
"""
import argparse
import json
import re
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
BATCH_INFO_PATH = OUT_DIR / 'anao_n100_label_batch_info.json'
RECORDS_PATH = OUT_DIR / 'anao_n100_label_records.json'
RAW_OUT = OUT_DIR / 'anao_n100_label_raw_responses.json'
TAGS_OUT = OUT_DIR / 'anao_n100_label_tags.json'
MISSING_OUT = OUT_DIR / 'anao_n100_label_missing.json'


def parse_one(text):
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        first, last = body.find('{'), body.rfind('}')
        if first >= 0:
            try: return json.loads(body[first:last+1])
            except: return {}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--download', action='store_true')
    args = ap.parse_args()

    if not BATCH_INFO_PATH.exists():
        raise SystemExit(f'No batch info — submit first.')
    info = json.load(open(BATCH_INFO_PATH))
    print(f"Batch: {info['batch_id']}")
    print(f"Submitted: {time.ctime(info['submitted_at'])}")

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(info['batch_id'])
    print(f'\nstatus: {batch.processing_status}')
    print(f'counts: {batch.request_counts}')
    if batch.ended_at: print(f'ended:  {batch.ended_at}')

    if not args.download:
        if batch.processing_status == 'ended':
            print('\n→ batch ended. Re-run with --download to fetch.')
        return
    if batch.processing_status != 'ended':
        raise SystemExit(f'Batch not ended (status={batch.processing_status})')

    print('\nStreaming results...')
    batches_data = []
    n_ok = n_err = 0
    for result in client.messages.batches.results(info['batch_id']):
        cid = result.custom_id
        try:
            _, _, batch_part = cid.split('__')
            bi = int(batch_part.replace('batch', ''))
        except Exception:
            continue
        if result.result.type != 'succeeded':
            n_err += 1
            print(f'  ERROR {cid}: {result.result.type}')
            continue
        msg = result.result.message
        text = msg.content[0].text if msg.content and msg.content[0].type == 'text' else ''
        batches_data.append({
            'batch_idx': bi, 'text': text,
            'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        })
        n_ok += 1
    print(f'  succeeded: {n_ok}, errored: {n_err}')
    batches_data.sort(key=lambda b: b['batch_idx'])

    RAW_OUT.write_text(json.dumps(batches_data, indent=2, ensure_ascii=False))

    all_tags = {}
    parse_errors = []
    tot_in = tot_out = 0
    for b in batches_data:
        parsed = parse_one(b['text'])
        for asn in parsed.get('assignments', []):
            if 'id' in asn:
                all_tags[asn['id']] = asn
        if not parsed.get('assignments'):
            parse_errors.append(b['batch_idx'])
        tot_in += b['input_tokens']; tot_out += b['output_tokens']

    expected_records = json.load(open(RECORDS_PATH))
    expected_ids = {r['id'] for r in expected_records}
    missing = sorted(expected_ids - set(all_tags.keys()))

    cost_batch = tot_in/1e6*2.50 + tot_out/1e6*12.50
    payload = {
        'model': info.get('model', 'claude-opus-4-6'),
        'n_records_tagged': len(all_tags),
        'n_records_expected': len(expected_ids),
        'n_records_missing': len(missing),
        'n_batches': len(batches_data),
        'n_parse_errors': len(parse_errors),
        'input_tokens': tot_in,
        'output_tokens': tot_out,
        'cost_usd_batch': round(cost_batch, 4),
        'tags': all_tags,
    }
    TAGS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    MISSING_OUT.write_text(json.dumps(missing, indent=2))

    print(f'\nTagged {len(all_tags):,} / {len(expected_ids):,} records')
    print(f'  missing: {len(missing)} ({len(missing)/len(expected_ids)*100:.2f}%)')
    print(f'  parse errors: {len(parse_errors)} batches')
    print(f'  tokens: {tot_in:,} in / {tot_out:,} out')
    print(f'  cost (batch): ${cost_batch:.2f}')
    print(f'\nWrote:')
    print(f'  {TAGS_OUT}')
    print(f'  {RAW_OUT}')
    print(f'  {MISSING_OUT}')

    # axis distributions
    from collections import Counter
    for axis in ('is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation','valence'):
        dist = Counter(t.get(axis) for t in all_tags.values())
        print(f'  {axis}: {dict(dist)}')

    if missing:
        print(f'\nNOTE: {len(missing)} records were dropped by the model. '
              f'See {MISSING_OUT} to re-tag the subset.')


if __name__ == '__main__':
    main()
