#!/usr/bin/env python3
"""Retrieve and parse ANAO N=100 MARKER batch results.

Uses the same lenient parser as the flat-markdown run. Saves outputs
namespaced with `_marker_` for clean comparison.
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path
import anthropic

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT/'corpora/anao/n100_demo/output'
BATCH_ID_FILE = OUT_DIR/'anao_n100_marker_batch_id.txt'
MANIFEST_FILE = OUT_DIR/'anao_n100_marker_manifest.json'
RESULTS_RAW = OUT_DIR/'anao_n100_marker_results_raw.jsonl'
RECORDS_OUT = OUT_DIR/'anao_n100_marker_records.jsonl'
META_OUT = OUT_DIR/'anao_n100_marker_extraction_meta.json'


def lenient_parse(text):
    t = text.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1] if '\n' in t else t
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    s, e = t.find('{'), t.rfind('}')
    if s >= 0 and e > s:
        try:
            d = json.loads(t[s:e+1])
            if 'records' in d: return d['records']
        except json.JSONDecodeError:
            pass
    m = re.search(r'"records"\s*:\s*\[', t)
    if not m: return []
    out, i = [], m.end()
    while i < len(t):
        while i < len(t) and t[i] in ' \n\r\t,': i += 1
        if i >= len(t) or t[i] != '{': break
        depth, j, in_str, esc = 0, i, False, False
        while j < len(t):
            c = t[j]
            if in_str:
                if esc: esc = False
                elif c == '\\': esc = True
                elif c == '"': in_str = False
            else:
                if c == '"': in_str = True
                elif c == '{': depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        try: out.append(json.loads(t[i:j+1]))
                        except json.JSONDecodeError: pass
                        break
            j += 1
        if depth != 0: break
        i = j + 1
    return out


def main():
    if not BATCH_ID_FILE.exists():
        sys.exit(f'no batch_id at {BATCH_ID_FILE}')
    batch_id = BATCH_ID_FILE.read_text().strip()
    manifest = json.load(MANIFEST_FILE.open())
    docs_by_id = {d['slug'][:60]: d for d in manifest['docs']}
    print(f'batch: {batch_id}', flush=True)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    print(f'status: {batch.processing_status}  counts: {batch.request_counts.model_dump()}', flush=True)
    if batch.processing_status != 'ended':
        print('not ready', flush=True); return

    records_total = []
    raw_lines = []
    in_tok = out_tok = 0
    parse_full = parse_recovered = parse_zero = errored = 0

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        if result.result.type != 'succeeded':
            print(f'  ! {custom_id}: {result.result.type}', flush=True)
            errored += 1
            continue
        msg = result.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        text = ''.join(b.text for b in msg.content if hasattr(b, 'text'))
        raw_lines.append(json.dumps({'custom_id': custom_id, 'text': text}))
        # diagnose strict vs lenient
        try:
            t2 = text.strip()
            if t2.startswith('```'): t2 = t2.split('\n',1)[1].rsplit('```',1)[0]
            s, e = t2.find('{'), t2.rfind('}')
            json.loads(t2[s:e+1]); strict_ok = True
        except Exception:
            strict_ok = False
        recs = lenient_parse(text)
        if strict_ok and recs:
            parse_full += 1
        elif recs:
            parse_recovered += 1
            print(f'  ~ {custom_id}: lenient-recovered ({len(recs)} records)', flush=True)
        else:
            parse_zero += 1
            print(f'  ! {custom_id}: zero records', flush=True)
        meta = docs_by_id.get(custom_id, {})
        for r in recs:
            r['_doc_slug'] = meta.get('slug')
            r['_year_tabled'] = meta.get('year_tabled')
            r['_portfolio'] = meta.get('portfolio')
            r['_entity'] = meta.get('entity')
            r['_sector'] = meta.get('sector')
            r['_era'] = meta.get('era')
        records_total.extend(recs)

    RESULTS_RAW.write_text('\n'.join(raw_lines))
    with RECORDS_OUT.open('w') as f:
        for r in records_total: f.write(json.dumps(r) + '\n')

    cost = in_tok/1e6*5*0.5 + out_tok/1e6*25*0.5
    print(f'\nrecords: {len(records_total)}', flush=True)
    print(f'tokens: {in_tok:,} in / {out_tok:,} out', flush=True)
    print(f'parse — full: {parse_full}  lenient: {parse_recovered}  zero: {parse_zero}  errored: {errored}', flush=True)
    print(f'batch cost: ${cost:.2f}', flush=True)

    by_era = Counter(r.get('_era') for r in records_total)
    by_sig = Counter(r.get('significance') for r in records_total)
    per_doc = Counter(r.get('_doc_slug') for r in records_total if r.get('_doc_slug'))
    print(f'\nby era: {dict(by_era)}', flush=True)
    print(f'by significance: {dict(by_sig)}', flush=True)
    if per_doc:
        vals = sorted(per_doc.values())
        print(f'records/doc — n_docs={len(per_doc)} min={vals[0]} median={vals[len(vals)//2]} max={vals[-1]} mean={sum(vals)/len(vals):.1f}', flush=True)

    META_OUT.write_text(json.dumps({
        'batch_id': batch_id, 'source': 'marker_output rendered.md',
        'max_tokens': manifest['max_tokens'],
        'n_docs_input': manifest['n_docs'],
        'n_records': len(records_total),
        'records_per_doc_avg': round(len(records_total)/max(len(per_doc),1), 1),
        'parse_full': parse_full, 'parse_recovered': parse_recovered,
        'parse_zero': parse_zero, 'errored': errored,
        'input_tokens': in_tok, 'output_tokens': out_tok, 'cost_usd': round(cost, 4),
        'era_distribution': dict(by_era),
        'significance_distribution': dict(by_sig),
    }, indent=2))
    print(f'\nwrote {RECORDS_OUT}\nwrote {META_OUT}', flush=True)


if __name__ == '__main__':
    main()
