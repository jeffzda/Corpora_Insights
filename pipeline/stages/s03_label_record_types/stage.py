"""Stage 03 — 6-axis record-type labelling (label_record_types_v3).

Engine version of the labelling pass. Mirrors the canonical ARENA
implementation:
    corpora/arena/canonical/narrative/runs/2026-05-02-record-type-pilot/
    code/{submit_corpus_opus,poll_corpus_opus}.py

with hard-coded paths replaced by domain config lookups. Submits as
Anthropic Batches API for the 50% discount + prompt caching.

Two subcommands:
    --submit   build batch + submit (default)
    --poll     poll status; with --download fetch + parse + write tags

Domain config (domain.yaml stages.label_record_types):
    model: claude-opus-4-6
    temperature: 0.0
    max_tokens: 128000
    records_per_call: 30
    input_records: <jsonl path with {id, narrative, evidence} per record>
    output_dir: <where to write batch_info, raw responses, tags.json>
    prompt: <override path for prompt; defaults to stage prompt.md>

Prompt resolution: cfg.prompt('label_record_types_v3', stage='s03_label_record_types').
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import anthropic

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[3]


def load_records(path: Path):
    """Load records from jsonl with {id, narrative, evidence}.

    Trims to (id, narrative, evidence) only — drops other fields including
    intervention to avoid contamination per the v3 design rationale.
    """
    records = []
    for line in path.open():
        r = json.loads(line)
        out = {'id': r.get('id') or r.get('record_id')}
        if r.get('narrative'): out['narrative'] = r['narrative']
        if r.get('evidence'):  out['evidence']  = r['evidence']
        records.append(out)
    return records


def submit(cfg: DomainConfig, args):
    stage_cfg = cfg.stage('label_record_types')
    model = stage_cfg.get('model', 'claude-opus-4-6')
    temperature = stage_cfg.get('temperature', 0.0)
    max_tokens = stage_cfg.get('max_tokens', 128_000)
    records_per_call = stage_cfg.get('records_per_call', 30)

    input_path = Path(stage_cfg.get('input_records') or args.input)
    output_dir = Path(stage_cfg.get('output_dir') or args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    records = load_records(input_path)
    print(f'records: {len(records):,}', flush=True)

    template = cfg.prompt('label_record_types_v3', stage='s03_label_record_types')
    placeholder = '[Records appended by the orchestrating script]'
    if placeholder not in template:
        raise SystemExit(f'Prompt template missing placeholder: {placeholder!r}')
    prefix, suffix = template.split(placeholder, 1)
    print(f'cached prefix: {len(prefix)} chars; suffix: {len(suffix)} chars', flush=True)

    requests = []
    n_calls = (len(records) + records_per_call - 1) // records_per_call
    for bi in range(0, len(records), records_per_call):
        batch = records[bi:bi + records_per_call]
        records_block = json.dumps(batch, indent=2, ensure_ascii=False)
        cached_text = prefix
        fresh_text = f'```json\n{records_block}\n```{suffix}'
        cid = f'{model}__rep1__batch{bi // records_per_call:05d}'
        params = {
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature,
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

    print(f'generated {len(requests):,} batch requests', flush=True)
    if args.dry_run:
        print('dry-run; not submitted'); return

    client = anthropic.Anthropic()
    started = time.time()
    batch = client.messages.batches.create(requests=requests)
    info = {
        'batch_id': batch.id,
        'n_requests': len(requests),
        'model': model,
        'n_records': len(records),
        'records_per_call': records_per_call,
        'records_path': str(input_path),
        'submitted_at': time.time(),
    }
    info_path = output_dir / 'batch_info.json'
    info_path.write_text(json.dumps(info, indent=2))
    records_path = output_dir / 'records_input.json'
    records_path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    print(f'batch.id = {batch.id}', flush=True)
    print(f'wrote {info_path}', flush=True)


def parse_one(text: str) -> dict:
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        s, e = body.find('{'), body.rfind('}')
        if s >= 0:
            try: return json.loads(body[s:e + 1])
            except: pass
    return {}


def poll(cfg: DomainConfig, args):
    stage_cfg = cfg.stage('label_record_types')
    output_dir = Path(stage_cfg.get('output_dir') or args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    info_path = output_dir / 'batch_info.json'
    if not info_path.exists():
        raise SystemExit(f'no batch info — run --submit first')
    info = json.load(info_path.open())
    print(f'batch: {info["batch_id"]}', flush=True)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(info['batch_id'])
    print(f'status: {batch.processing_status}  counts: {batch.request_counts}',
          flush=True)
    if not args.download:
        return
    if batch.processing_status != 'ended':
        raise SystemExit(f'batch not ended (status={batch.processing_status})')

    print('streaming results...', flush=True)
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
            print(f'  ERROR {cid}: {result.result.type}', flush=True)
            continue
        msg = result.result.message
        text = msg.content[0].text if msg.content and msg.content[0].type == 'text' else ''
        batches_data.append({
            'batch_idx': bi, 'text': text,
            'input_tokens': msg.usage.input_tokens,
            'output_tokens': msg.usage.output_tokens,
        })
        n_ok += 1
    print(f'succeeded: {n_ok}, errored: {n_err}', flush=True)
    batches_data.sort(key=lambda b: b['batch_idx'])

    raw_path = output_dir / 'raw_responses.json'
    raw_path.write_text(json.dumps(batches_data, indent=2, ensure_ascii=False))

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
        tot_in += b['input_tokens']
        tot_out += b['output_tokens']

    records_input = json.load((output_dir / 'records_input.json').open())
    expected_ids = {r['id'] for r in records_input}
    missing = sorted(expected_ids - set(all_tags.keys()))

    cost = tot_in / 1e6 * 2.50 + tot_out / 1e6 * 12.50  # batch-discounted Opus 4.6
    payload = {
        'model': info.get('model', 'claude-opus-4-6'),
        'n_records_tagged': len(all_tags),
        'n_records_expected': len(expected_ids),
        'n_records_missing': len(missing),
        'n_batches': len(batches_data),
        'n_parse_errors': len(parse_errors),
        'input_tokens': tot_in,
        'output_tokens': tot_out,
        'cost_usd_batch': round(cost, 4),
        'tags': all_tags,
    }
    tags_path = output_dir / 'tags.json'
    tags_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    missing_path = output_dir / 'missing_records.json'
    missing_path.write_text(json.dumps(missing, indent=2))

    print(f'\ntagged {len(all_tags):,} / {len(expected_ids):,}', flush=True)
    print(f'missing: {len(missing)} ({len(missing)/max(len(expected_ids),1)*100:.2f}%)', flush=True)
    print(f'parse errors: {len(parse_errors)} batches', flush=True)
    print(f'tokens: {tot_in:,} in / {tot_out:,} out', flush=True)
    print(f'cost (batch): ${cost:.2f}', flush=True)

    # Axis distributions
    for axis in ('is_occurrence', 'is_mechanism', 'is_specification',
                 'is_lesson', 'is_recommendation', 'valence'):
        dist = Counter(t.get(axis) for t in all_tags.values())
        print(f'  {axis}: {dict(dist)}', flush=True)

    print(f'\nwrote {tags_path}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True, help='domain name, e.g. arena, anao')
    ap.add_argument('--submit', action='store_true', help='build + submit batch (default action)')
    ap.add_argument('--poll', action='store_true', help='poll status only')
    ap.add_argument('--download', action='store_true', help='with --poll: fetch + parse + write tags.json')
    ap.add_argument('--input', help='records jsonl path (overrides cfg)')
    ap.add_argument('--output-dir', help='output directory (overrides cfg)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    if args.poll or args.download:
        poll(cfg, args)
    else:
        submit(cfg, args)


if __name__ == '__main__':
    main()
