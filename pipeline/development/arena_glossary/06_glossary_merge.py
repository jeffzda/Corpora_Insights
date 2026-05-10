#!/usr/bin/env python3
"""Glossary merge — combine v1 confident entries with v2 tail/titlecase/reground.

Inputs:
  output/glossary_recovered.json (v1 — 505 entries; keeps non-noise non-uncertain)
  output/glossary_v2_tail.json (95 missing tail acronyms)
  output/glossary_v2_titlecase.json (~300 orgs/programmes/standards)
  output/glossary_v2_reground.json (100 re-grounded uncertain entries)

Output:
  output/glossary.json (canonical merged glossary)
  output/glossary.md (human-readable, alphabetic, by category)
  output/glossary.html (rendered)
  output/glossary_meta.json (provenance — which pass each entry came from)
"""
from __future__ import annotations
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'output/entity_index.csv'
V1 = ROOT / 'output/glossary_recovered.json'
TAIL = ROOT / 'output/glossary_v2_tail.json'
TITLECASE = ROOT / 'output/glossary_v2_titlecase.json'
REGROUND = ROOT / 'output/glossary_v2_reground.json'

OUT_JSON = ROOT / 'output/glossary.json'
OUT_MD = ROOT / 'output/glossary.md'
OUT_HTML = ROOT / 'output/glossary.html'
OUT_META = ROOT / 'output/glossary_meta.json'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'


def normalise_v2_entry(e):
    """v2 uses compact keys (t/e/c/d/x/n/u); normalise to verbose for merging."""
    return {
        'term': e.get('t') or e.get('term'),
        'expansion': e.get('e') if 'e' in e else e.get('expansion'),
        'category': e.get('c') or e.get('category'),
        'definition': e.get('d') if 'd' in e else e.get('definition'),
        'arena_context': e.get('x') if 'x' in e else e.get('arena_context'),
        'notes': e.get('n') if 'n' in e else e.get('notes'),
        'uncertainty': bool(e.get('u') if 'u' in e else e.get('uncertainty')),
    }


def main():
    by_surf_index = {r['canonical_surface']: r for r in csv.DictReader(open(INDEX))}

    sources = {}  # term → pass_label

    # v1 — keep all non-noise entries (we'll override uncertain ones with reground)
    v1_entries = json.load(open(V1))['entries']
    confident_v1 = {}
    for e in v1_entries:
        if e.get('category') == 'noise': continue
        confident_v1[e['term']] = e
        sources[e['term']] = 'v1'

    # reground — replaces v1 uncertain entries
    reg = []
    if REGROUND.exists():
        reg_data = json.load(open(REGROUND))
        for e in reg_data.get('entries', []):
            ne = normalise_v2_entry(e)
            if not ne.get('term'): continue
            confident_v1[ne['term']] = ne   # override v1
            sources[ne['term']] = 'v2-reground'
            reg.append(ne)

    # tail — add new acronyms
    tail = []
    if TAIL.exists():
        td = json.load(open(TAIL))
        for e in td.get('entries', []):
            ne = normalise_v2_entry(e)
            if not ne.get('term'): continue
            if ne['category'] == 'noise':
                # still keep in noise list
                confident_v1[ne['term']] = ne
                sources[ne['term']] = 'v2-tail'
                tail.append(ne); continue
            confident_v1[ne['term']] = ne
            sources[ne['term']] = 'v2-tail'
            tail.append(ne)

    # titlecase — add new entries
    tc = []
    if TITLECASE.exists():
        tcd = json.load(open(TITLECASE))
        for e in tcd.get('entries', []):
            ne = normalise_v2_entry(e)
            if not ne.get('term'): continue
            confident_v1[ne['term']] = ne
            sources[ne['term']] = 'v2-titlecase'
            tc.append(ne)

    # Augment all entries with corpus-frequency stats
    for term, e in confident_v1.items():
        m = by_surf_index.get(term)
        if m:
            e['n_total_mentions'] = int(m['n_total_mentions'])
            e['n_unique_docs'] = int(m['n_unique_docs'])
            e['sources'] = m['sources']
            e['pattern'] = m['pattern']

    all_entries = list(confident_v1.values())
    glossary = [e for e in all_entries if e.get('category') != 'noise']
    noise = [e for e in all_entries if e.get('category') == 'noise']

    print(f"v1 entries: {len(v1_entries)}")
    print(f"v2 tail: {len(tail)} | titlecase: {len(tc)} | reground: {len(reg)}")
    print(f"total merged: {len(all_entries)} ({len(glossary)} glossary + {len(noise)} noise)")

    # === Markdown ===
    by_cat = {}
    for e in glossary:
        by_cat.setdefault(e.get('category','?'), []).append(e)
    cat_counts = {c: len(v) for c, v in by_cat.items()}
    n_unc = sum(1 for e in glossary if e.get('uncertainty'))

    md = ['# ARENA Corpus Glossary', '',
          'Auto-generated study-guide companion to ARENA project reports. Empirical scope is set by the corpus (which terms appear, ranked by document coverage); definitions are model-written with uncertainty flags surfacing entries that warrant further corpus-grounding.',
          '',
          f'**Source.** Entity index built from 1,440 ARENA Knowledge Bank documents via regex + spaCy NER + transformer NER, filtered to high-frequency surfaces. Definitions written by Claude Sonnet 4.6 across four passes (initial top-600 acronyms; tail recovery for max-tokens-truncated entries; titlecase pass for organisations / programmes / standards; corpus-grounded re-grounding for uncertain entries).',
          '',
          f'**Coverage.** {len(glossary)} glossary entries (plus {len(noise)} surfaces filtered as noise: sentence fragments, generic English mis-caught, project codenames not glossary-worthy).',
          '',
          f'**Quality flag.** {n_unc} entries flagged uncertain — model wasn\'t confident in the expansion or definition even after corpus context. Treat those as starting points, not authoritative.',
          '',
          '## Categories', '',
          '| category | n |', '|---|---:|']
    for c, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        md.append(f'| {c} | {n} |')

    # Provenance summary
    pass_counts = Counter(sources.values())
    md += ['', '## Provenance (by pass)', '',
           '| pass | n |', '|---|---:|']
    for p, n in pass_counts.most_common():
        md.append(f'| {p} | {n} |')

    md += ['', '## Entries (alphabetic)', '']
    glossary.sort(key=lambda e: (e.get('term') or '').lower())
    for e in glossary:
        term = e.get('term','?')
        expansion = e.get('expansion') or ''
        cat = e.get('category','?')
        defn = e.get('definition','') or ''
        ctx = e.get('arena_context','') or ''
        notes = e.get('notes')
        u = ' ⚠' if e.get('uncertainty') else ''
        n_m = e.get('n_total_mentions')
        n_d = e.get('n_unique_docs')
        head = f"### {term}"
        if expansion: head += f" — *{expansion}*"
        head += u
        md.append(head); md.append('')
        if n_m and n_d: md.append(f"**{cat}** · {n_m:,} mentions / {n_d:,} docs")
        else: md.append(f"**{cat}**")
        md.append('')
        if defn: md.append(defn); md.append('')
        if ctx: md.append(f"*ARENA context:* {ctx}"); md.append('')
        if notes: md.append(f"*Notes:* {notes}"); md.append('')

    if noise:
        md += ['## Filtered as noise', '',
               'Surfaces caught by the entity-extraction pipeline but not glossary-worthy:',
               '',
               ', '.join(f'`{e.get("term","")}`' for e in sorted(noise, key=lambda x: (x.get("term") or "").lower())),
               '']

    OUT_MD.write_text('\n'.join(md))

    # JSON
    json.dump({
        'n_glossary': len(glossary),
        'n_noise': len(noise),
        'n_uncertain': n_unc,
        'category_counts': cat_counts,
        'pass_counts': dict(pass_counts),
        'entries': glossary,
        'noise': noise,
        'sources': sources,
    }, open(OUT_JSON, 'w'), indent=2)

    # HTML
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'ARENA Corpus Glossary',
         'Broad Learnings · Study-guide companion'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    json.dump({
        'n_glossary': len(glossary), 'n_noise': len(noise),
        'n_uncertain': n_unc,
        'category_counts': cat_counts,
        'pass_counts': dict(pass_counts),
    }, open(OUT_META, 'w'), indent=2)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_HTML}")


if __name__ == '__main__':
    main()
