#!/usr/bin/env python3
"""ANAO N=100 extraction — MARKER-rendered version.

Same stratified sample (same SEED) as anao_n100_extract.py but operating
on the higher-fidelity marker_output/<slug>/<slug>.rendered.md files
instead of the flat markdown/ files. Also fixes the previous
max_tokens=16000 cap (now 64000) to avoid mid-record truncation.

Output files namespaced with `_marker_` for clean comparison.
"""
from __future__ import annotations
import csv, json, random
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
ANAO_MARKER = ROOT/'corpora/anao/marker_output'
ANAO_MD = ROOT/'corpora/anao/markdown'  # used only for parity check on slug coverage
META_CSV = ROOT/'corpora/anao/reports_metadata.csv'
PROMPT_FILE = ROOT/'domains/arena/prompts/extract.md'
OUT_DIR = ROOT/'corpora/anao/n100_demo/output'
BATCH_ID_FILE = OUT_DIR/'anao_n100_marker_batch_id.txt'
MANIFEST_FILE = OUT_DIR/'anao_n100_marker_manifest.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 64000
SEED = 42  # same seed as flat-markdown run for sample parity


def era(year_str):
    if not year_str: return None
    try: y = int(year_str[:4])
    except ValueError: return None
    if y <= 2001: return '1996-2001'
    if y <= 2007: return '2002-2007'
    if y <= 2013: return '2008-2013'
    if y <= 2019: return '2014-2019'
    return '2020-2025'


def main():
    random.seed(SEED)
    # We sample using the same logic as flat-markdown run, then resolve to rendered.md.
    avail_md = set(p.name for p in ANAO_MD.glob('*.md'))
    print(f'flat markdown available: {len(avail_md)}', flush=True)

    by_era = {e: [] for e in ['1996-2001','2002-2007','2008-2013','2014-2019','2020-2025']}
    with open(META_CSV) as f:
        for row in csv.DictReader(f):
            md_name = (row.get('title') or '').strip() + '.md'
            if md_name not in avail_md: continue
            e = era(row.get('year_tabled'))
            if e is None: continue
            by_era[e].append({
                'slug': (row.get('title') or '').strip(),
                'md_name': md_name,
                'title': (row.get('title') or '').strip(),
                'year_tabled': (row.get('year_tabled') or '').strip(),
                'portfolio': (row.get('portfolio') or '').strip(),
                'entity': (row.get('entity') or '').strip(),
                'sector': (row.get('sector') or '').strip(),
                'report_number': (row.get('report_number') or '').strip(),
            })
    sample = []
    for e, lst in by_era.items():
        chosen = random.sample(lst, min(20, len(lst)))
        for c in chosen: c['era'] = e
        sample.extend(chosen)
    print(f'sampled {len(sample)} docs (same seed as flat-markdown run)', flush=True)

    # Resolve each to rendered.md
    template = PROMPT_FILE.read_text()
    requests = []
    missing_marker = []
    total_in_chars = 0
    for s in sample:
        rendered = ANAO_MARKER / s['slug'] / f"{s['slug']}.rendered.md"
        if not rendered.exists():
            missing_marker.append(s['slug'])
            continue
        text = rendered.read_text(errors='ignore')
        if len(text) > 600_000:
            text = text[:600_000]
            s['truncated'] = True
        prefix = f'ANAOM-{s["slug"][:40]}'  # M = marker variant, distinct prefix
        prompt = (template
                  .replace('{{prefix}}', prefix)
                  .replace('{{title}}', s['title'])
                  .replace('{{text}}', text))
        s['prefix'] = prefix
        s['prompt_chars'] = len(prompt)
        s['rendered_chars'] = len(text)
        total_in_chars += len(prompt)
        requests.append({
            'custom_id': s['slug'][:60],
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'messages': [{'role': 'user', 'content': prompt}],
            },
        })

    if missing_marker:
        print(f'! {len(missing_marker)} sample docs have no rendered.md: {missing_marker[:5]}...', flush=True)
    print(f'requests built: {len(requests)}', flush=True)
    print(f'total prompt chars: {total_in_chars:,} (~{total_in_chars//4:,} input tokens)', flush=True)
    est_in = total_in_chars/4/1e6 * 5 * 0.5
    est_out = len(requests) * 12000/1e6 * 25 * 0.5  # ~12k tok output per doc with 64k cap
    print(f'estimated batch cost: ${est_in + est_out:.2f}', flush=True)

    MANIFEST_FILE.write_text(json.dumps({
        'model': MODEL, 'max_tokens': MAX_TOKENS, 'seed': SEED,
        'source': 'marker_output/<slug>/<slug>.rendered.md',
        'n_docs': len(requests),
        'n_missing_marker': len(missing_marker),
        'missing_marker': missing_marker,
        'docs': sample,
        'estimated_cost_usd': round(est_in + est_out, 2),
    }, indent=2))

    print('\nsubmitting batch...', flush=True)
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    print(f'  batch_id: {batch.id}', flush=True)
    print(f'  status: {batch.processing_status}', flush=True)
    print(f'\nsaved manifest to {MANIFEST_FILE}', flush=True)
    print(f'saved batch id to {BATCH_ID_FILE}', flush=True)


if __name__ == '__main__':
    main()
