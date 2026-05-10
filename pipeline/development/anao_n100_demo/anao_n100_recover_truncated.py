#!/usr/bin/env python3
"""Recover records from truncated batch outputs.

Many docs hit max_tokens=16000 ceiling and were truncated mid-record.
The text up to the last complete record is still valid; we just need
to close the JSON envelope.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import Counter

ROOT = Path('/home/jeffzda/broadlearnings')
RAW = ROOT/'corpora/anao/n100_demo/output/anao_n100_results_raw.jsonl'
MANIFEST = ROOT/'corpora/anao/n100_demo/output/anao_n100_manifest.json'
OUT = ROOT/'corpora/anao/n100_demo/output/anao_n100_records_recovered.jsonl'


def lenient_parse(text: str) -> list[dict]:
    """Extract as many complete record objects as possible, even from truncated text."""
    # Strip code fences
    t = text.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1] if '\n' in t else t
        if t.endswith('```'): t = t.rsplit('```', 1)[0]
    # Try strict parse first
    s, e = t.find('{'), t.rfind('}')
    if s >= 0 and e > s:
        try:
            d = json.loads(t[s:e+1])
            if 'records' in d:
                return d['records']
        except json.JSONDecodeError:
            pass
    # Lenient: walk the text, find each `{ ... }` record-shaped object inside the records array
    # Find the start of the records array
    m = re.search(r'"records"\s*:\s*\[', t)
    if not m: return []
    start = m.end()
    out = []
    i = start
    while i < len(t):
        # Skip whitespace and commas
        while i < len(t) and t[i] in ' \n\r\t,': i += 1
        if i >= len(t) or t[i] != '{': break
        # Find matching close brace, respecting strings
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
                        # Try to parse this record
                        try:
                            rec = json.loads(t[i:j+1])
                            out.append(rec)
                        except json.JSONDecodeError:
                            pass
                        break
            j += 1
        if depth != 0:
            # Truncated mid-record; stop
            break
        i = j + 1
    return out


def main():
    manifest = json.load(MANIFEST.open())
    docs_by_id = {d['slug'][:60]: d for d in manifest['docs']}
    raw = [json.loads(l) for l in RAW.open()]
    print(f'raw responses: {len(raw)}')

    all_records = []
    per_doc = Counter()
    parse_recovered = 0
    parse_full = 0
    parse_zero = 0
    for r in raw:
        cid = r['custom_id']
        recs = lenient_parse(r['text'])
        meta = docs_by_id.get(cid, {})
        for rec in recs:
            rec['_doc_slug'] = meta.get('slug')
            rec['_year_tabled'] = meta.get('year_tabled')
            rec['_portfolio'] = meta.get('portfolio')
            rec['_entity'] = meta.get('entity')
            rec['_sector'] = meta.get('sector')
            rec['_era'] = meta.get('era')
        all_records.extend(recs)
        per_doc[cid] = len(recs)
        # Diagnose: did strict parse work?
        try:
            t = r['text'].strip()
            if t.startswith('```'): t = t.split('\n',1)[1].rsplit('```',1)[0]
            s, e = t.find('{'), t.rfind('}')
            json.loads(t[s:e+1])
            parse_full += 1
        except Exception:
            if recs:
                parse_recovered += 1
            else:
                parse_zero += 1

    with OUT.open('w') as f:
        for rec in all_records:
            f.write(json.dumps(rec) + '\n')

    print(f'\nrecovered records: {len(all_records)}')
    print(f'docs full strict-parse: {parse_full}')
    print(f'docs lenient-recovered: {parse_recovered}')
    print(f'docs no records: {parse_zero}')
    print(f'\nrecords/doc — min {min(v for v in per_doc.values() if v>0):>2}  max {max(per_doc.values()):>2}  median {sorted([v for v in per_doc.values() if v>0])[len([v for v in per_doc.values() if v>0])//2]}  mean {sum(per_doc.values())/sum(1 for v in per_doc.values() if v>0):.1f}')

    by_era = Counter(r.get('_era') for r in all_records)
    by_sig = Counter(r.get('significance') for r in all_records)
    print(f'\nby era: {dict(by_era)}')
    print(f'by significance: {dict(by_sig)}')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
