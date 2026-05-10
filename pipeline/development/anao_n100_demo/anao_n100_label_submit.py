#!/usr/bin/env python3
"""Submit ANAO N=100 6-axis record-type tagging via Anthropic Batches API.

Mirrors the canonical ARENA labelling submitter:
  corpora/arena/canonical/narrative/runs/2026-05-02-record-type-pilot/code/submit_corpus_opus.py

Modified only to point at the ANAO N=100 filtered records and write outputs
under corpora/anao/n100_demo/output/.

Configuration (per ARENA validation):
- Model:    claude-opus-4-6  (NOT 4.7 — supports temperature, deterministic)
- Temp:     0.0
- Prompt:   label_record_types_v3.md  (corpus-agnostic per inspection)
- Trim:     id + narrative + evidence only
- Records-per-call: 30
- Caching:  prompt prefix cached
- max_tokens: 128_000

Usage:
  python3 anao_n100_label_submit.py --dry-run
  python3 anao_n100_label_submit.py
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
RECORDS_IN = ROOT / 'corpora/anao/n100_demo/output/anao_n100_marker_records_filtered.jsonl'
PROMPT_PATH = ROOT / 'corpora/arena/canonical/prompts/label_record_types_v3.md'
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
BATCH_INFO_PATH = OUT_DIR / 'anao_n100_label_batch_info.json'
RECORD_LIST_PATH = OUT_DIR / 'anao_n100_label_records.json'

RECORDS_PER_CALL = 30
MAX_TOKENS = 128_000
MODEL = 'claude-opus-4-6'
TEMPERATURE = 0.0


def trim(rec):
    out = {'id': rec['id']}
    if rec.get('narrative'): out['narrative'] = rec['narrative']
    if rec.get('evidence'):  out['evidence']  = rec['evidence']
    return out


def load_records():
    if RECORD_LIST_PATH.exists():
        return json.load(open(RECORD_LIST_PATH))
    records = []
    for line in RECORDS_IN.open():
        rec = json.loads(line)
        records.append(trim(rec))
    records.sort(key=lambda r: r['id'])
    RECORD_LIST_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    print(f'Built record list: {len(records):,} records → {RECORD_LIST_PATH}')
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    records = load_records()
    print(f'Total records to tag: {len(records):,}')

    template = PROMPT_PATH.read_text()
    placeholder = '[Records appended by the orchestrating script]'
    if placeholder not in template:
        raise SystemExit(f'Prompt template missing placeholder: {placeholder!r}')
    prefix, suffix = template.split(placeholder, 1)
    print(f'Prompt: {PROMPT_PATH.name}  (cached prefix: {len(prefix)} chars; suffix: {len(suffix)} chars)')

    requests = []
    n_calls = (len(records) + RECORDS_PER_CALL - 1) // RECORDS_PER_CALL
    for bi in range(0, len(records), RECORDS_PER_CALL):
        batch = records[bi:bi + RECORDS_PER_CALL]
        records_block = json.dumps(batch, indent=2, ensure_ascii=False)
        cached_text = prefix
        fresh_text = f'```json\n{records_block}\n```{suffix}'
        cid = f'{MODEL}__rep1__batch{bi // RECORDS_PER_CALL:05d}'
        params = {
            'model': MODEL,
            'max_tokens': MAX_TOKENS,
            'temperature': TEMPERATURE,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': cached_text,
                     'cache_control': {'type': 'ephemeral'}},
                    {'type': 'text', 'text': fresh_text},
                ],
            }],
        }
        requests.append({'custom_id': cid, 'params': params})

    print(f'\nGenerated {len(requests):,} batch requests ({n_calls} expected)')

    OBS_IN_PER = 273
    OBS_OUT_PER = 98
    in_total = len(records) * OBS_IN_PER
    out_total = len(records) * OBS_OUT_PER
    sync = in_total/1e6*5.0 + out_total/1e6*25.0
    batch_no_cache = in_total/1e6*2.50 + out_total/1e6*12.50
    TEMPLATE_TOK = 1518
    fresh_in_total = max(0, in_total - n_calls * TEMPLATE_TOK)
    cached_writes = TEMPLATE_TOK
    cached_reads = (n_calls - 1) * TEMPLATE_TOK
    batch_cached = (fresh_in_total/1e6*2.50
                     + cached_writes/1e6*3.125
                     + cached_reads/1e6*0.25
                     + out_total/1e6*12.50)
    print(f'\nCost projection ({len(records):,} records):')
    print(f'  Sync:                          ${sync:>7.2f}')
    print(f'  Batch API (no cache):          ${batch_no_cache:>7.2f}')
    print(f'  Batch API + cache (this run):  ${batch_cached:>7.2f}')

    print(f'\nFirst request preview:')
    r0 = requests[0]
    print(f"  custom_id: {r0['custom_id']}")
    print(f"  model:     {r0['params']['model']}")
    print(f"  max_tok:   {r0['params']['max_tokens']}")
    print(f"  temp:      {r0['params'].get('temperature')}")
    print(f"  content blocks: {len(r0['params']['messages'][0]['content'])}")
    for i, b in enumerate(r0['params']['messages'][0]['content']):
        cc = b.get('cache_control')
        print(f"    block {i}: {len(b['text'])} chars  cache_control={cc}")

    if args.dry_run:
        print(f'\nDry-run; NOT submitted.')
        return

    print(f'\nSubmitting {len(requests):,} requests to Anthropic Batches API...')
    client = anthropic.Anthropic()
    started = time.time()
    batch = client.messages.batches.create(requests=requests)
    print(f'\nBatch submitted in {time.time()-started:.1f}s')
    print(f'  batch.id   = {batch.id}')
    print(f'  status     = {batch.processing_status}')
    print(f'  counts     = {batch.request_counts}')
    print(f'  expires_at = {batch.expires_at}')

    info = {
        'batch_id': batch.id,
        'n_requests': len(requests),
        'model': MODEL,
        'n_records': len(records),
        'records_per_call': RECORDS_PER_CALL,
        'prompt_path': str(PROMPT_PATH),
        'submitted_at': time.time(),
    }
    BATCH_INFO_PATH.write_text(json.dumps(info, indent=2))
    print(f'\nSaved batch info → {BATCH_INFO_PATH}')


if __name__ == '__main__':
    main()
