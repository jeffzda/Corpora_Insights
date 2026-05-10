#!/usr/bin/env python3
"""Per-doc event derivation for ANAO N=97 filtered marker records.

Runs the canonical `group_events.md` prompt once per document with empty
prior_events_block (chain length 1, no carry-forward — each ANAO audit
is standalone after the multi-doc filter).

Submits as Anthropic Batches API for ~50% discount.

Inputs:
  - corpora/anao/n100_demo/output/anao_n100_marker_records_filtered.jsonl (4,617 records, 97 docs)
  - corpora/arena/canonical/prompts/group_events.md

Outputs:
  - anao_n100_event_batch_id.txt
  - anao_n100_event_manifest.json
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
RECORDS = ROOT/'corpora/anao/n100_demo/output/anao_n100_marker_records_filtered.jsonl'
PROMPT_FILE = ROOT/'corpora/arena/canonical/prompts/group_events.md'
OUT_DIR = ROOT/'corpora/anao/n100_demo/output'
BATCH_ID_FILE = OUT_DIR/'anao_n100_event_batch_id.txt'
MANIFEST_FILE = OUT_DIR/'anao_n100_event_manifest.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 32000


def main():
    template = PROMPT_FILE.read_text()

    by_doc = defaultdict(list)
    for line in RECORDS.open():
        r = json.loads(line)
        slug = r.get('_doc_slug')
        if slug: by_doc[slug].append(r)
    print(f'docs: {len(by_doc)}', flush=True)
    print(f'records: {sum(len(v) for v in by_doc.values())}', flush=True)

    requests = []
    total_in = 0
    for slug, recs in by_doc.items():
        # Strip internal _-prefixed metadata before passing to model
        slim = []
        for r in recs:
            slim.append({k: v for k, v in r.items() if not k.startswith('_')})
        records_block = json.dumps(slim, indent=1, ensure_ascii=False)
        prompt = (template
                  .replace('{{prior_events_block}}', '(no prior events — first document of this audit)')
                  .replace('{{records_block}}', records_block))
        total_in += len(prompt)
        requests.append({
            'custom_id': slug[:60],
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'messages': [{'role': 'user', 'content': prompt}],
            },
        })
    print(f'requests: {len(requests)}', flush=True)
    print(f'total prompt chars: {total_in:,} (~{total_in//4:,} input tokens)', flush=True)
    est_in = total_in/4/1e6 * 5 * 0.5
    est_out = len(requests) * 6000/1e6 * 25 * 0.5  # ~6k tok output per doc
    print(f'estimated batch cost: ${est_in + est_out:.2f}', flush=True)

    MANIFEST_FILE.write_text(json.dumps({
        'model': MODEL, 'max_tokens': MAX_TOKENS,
        'n_docs': len(requests),
        'n_records': sum(len(v) for v in by_doc.values()),
        'records_per_doc': {slug: len(recs) for slug, recs in by_doc.items()},
    }, indent=2))

    print('\nsubmitting batch...', flush=True)
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    print(f'  batch_id: {batch.id}', flush=True)
    print(f'  status: {batch.processing_status}', flush=True)


if __name__ == '__main__':
    main()
