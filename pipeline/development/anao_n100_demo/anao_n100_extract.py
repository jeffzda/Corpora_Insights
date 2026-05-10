#!/usr/bin/env python3
"""ANAO N=100 extraction for cross-corpus generalisability demo.

Stratified sample of 100 ANAO performance audit reports across 5 era
bands (1996–2001, 2002–2007, 2008–2013, 2014–2019, 2020–2025), 20 per
band. Submits as a single Anthropic Batches API job for 50% discount.

Run: python3 corpora/anao/n100_demo/output/anao_n100_extract.py
Output: batch_id saved to corpora/anao/n100_demo/output/anao_n100_batch_id.txt
        sample manifest at corpora/anao/n100_demo/output/anao_n100_manifest.json

Then poll with: python3 corpora/anao/n100_demo/output/anao_n100_retrieve.py
"""
from __future__ import annotations
import csv, json, random
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
ANAO_MD = ROOT / 'corpora/anao/markdown'
META_CSV = ROOT / 'corpora/anao/reports_metadata.csv'
PROMPT_FILE = ROOT / 'domains/arena/prompts/extract.md'
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
BATCH_ID_FILE = OUT_DIR / 'anao_n100_batch_id.txt'
MANIFEST_FILE = OUT_DIR / 'anao_n100_manifest.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 16000  # records output; rare to need more
SEED = 42


def era(year_str: str) -> str | None:
    """Map '2003–04' style year to era band."""
    if not year_str: return None
    try:
        y = int(year_str[:4])
    except ValueError:
        return None
    if y <= 2001: return '1996-2001'
    if y <= 2007: return '2002-2007'
    if y <= 2013: return '2008-2013'
    if y <= 2019: return '2014-2019'
    return '2020-2025'


def main():
    random.seed(SEED)
    avail = set(p.name for p in ANAO_MD.glob('*.md'))
    print(f'available markdown files: {len(avail)}')

    by_era: dict[str, list[dict]] = {e: [] for e in ['1996-2001','2002-2007','2008-2013','2014-2019','2020-2025']}
    with open(META_CSV) as f:
        for row in csv.DictReader(f):
            md_name = (row.get('title') or '').strip() + '.md'
            if md_name not in avail: continue
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

    for e, lst in by_era.items():
        print(f'  {e}: {len(lst)} candidates')

    # Stratified sample: 20 per era
    sample = []
    for e, lst in by_era.items():
        n_take = min(20, len(lst))
        chosen = random.sample(lst, n_take)
        for c in chosen: c['era'] = e
        sample.extend(chosen)
    print(f'\nsampled {len(sample)} docs total ({len(set(s["era"] for s in sample))} eras)')

    # Build batch requests
    template = PROMPT_FILE.read_text()
    requests = []
    skipped = 0
    total_in_chars = 0
    for s in sample:
        text = (ANAO_MD / s['md_name']).read_text(errors='ignore')
        # Truncate ultra-large docs to 600k chars (~150k tokens) to keep batch cost predictable
        if len(text) > 600_000:
            text = text[:600_000]
            s['truncated'] = True
        prefix = f'ANAO-{s["slug"][:40]}'
        prompt = (template
                  .replace('{{prefix}}', prefix)
                  .replace('{{title}}', s['title'])
                  .replace('{{text}}', text))
        s['prefix'] = prefix
        s['prompt_chars'] = len(prompt)
        total_in_chars += len(prompt)
        requests.append({
            'custom_id': s['slug'][:60],
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'messages': [{'role': 'user', 'content': prompt}],
            },
        })

    print(f'total prompt chars across batch: {total_in_chars:,} (~{total_in_chars//4:,} input tokens)')
    est_in = total_in_chars / 4 / 1e6 * 5 * 0.5  # 50% batch discount
    est_out = len(requests) * 4000 / 1e6 * 25 * 0.5  # ~4k tokens per doc avg
    print(f'estimated batch cost: ${est_in + est_out:.2f}')

    # Save manifest before submission
    MANIFEST_FILE.write_text(json.dumps({
        'model': MODEL, 'max_tokens': MAX_TOKENS, 'seed': SEED,
        'n_docs': len(sample),
        'docs': sample,
        'estimated_cost_usd': round(est_in + est_out, 2),
    }, indent=2))

    print(f'\nsubmitting batch...')
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    print(f'  batch_id: {batch.id}')
    print(f'  status: {batch.processing_status}')
    print(f'\nsaved manifest to {MANIFEST_FILE}')
    print(f'saved batch id to {BATCH_ID_FILE}')
    print(f'\nretrieve later with:')
    print(f'  python3 {OUT_DIR}/anao_n100_retrieve.py')


if __name__ == '__main__':
    main()
