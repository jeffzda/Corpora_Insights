"""Stage g06 — Merge initial glossary + followup passes (deterministic).

Generalises:
    pipeline/development/arena_glossary/06_glossary_merge.py

Combines:
    define output (glossary_recovered.json or glossary.json) — non-noise entries
    define_followups outputs:
        glossary_v2_tail.json
        glossary_v2_titlecase.json
        glossary_v2_reground.json   (overrides v1 entries with same term)

Outputs:
    merge.output_path                glossary.json (canonical merged)
    sibling glossary.md              human-readable
    sibling glossary.html            rendered (if md2html available)

Domain config (domain.yaml glossary.merge + glossary.normalise):
    merge.inputs                     list of input files (override default order)
    merge.output_path                where to write merged glossary.json
    merge.entity_index_path          for per-term frequency stats (default normalise.output_path)
    merge.title                      MD title (default '<corpus_full_name> Glossary')
    merge.subtitle                   MD subtitle
"""
from __future__ import annotations
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')


def _normalise_compact(e: dict) -> dict:
    """v2 compact (t/e/c/d/x/n/u) → verbose. Accept either schema; coerce
    legacy `arena_context` to `context`."""
    return {
        'term': e.get('t') or e.get('term'),
        'expansion': e.get('e') if 'e' in e else e.get('expansion'),
        'category': e.get('c') or e.get('category'),
        'definition': e.get('d') if 'd' in e else e.get('definition'),
        'context': (e.get('x') if 'x' in e
                    else e.get('context') if 'context' in e
                    else e.get('arena_context')),
        'notes': e.get('n') if 'n' in e else e.get('notes'),
        'uncertainty': bool(e.get('u') if 'u' in e else e.get('uncertainty')),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    m = (cfg.glossary.get('merge') or {})
    nrm = (cfg.glossary.get('normalise') or {})

    inputs = m.get('inputs') or []
    if not inputs:
        raise SystemExit('glossary.merge.inputs is required')
    output_path = resolve(m.get('output_path') or '')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = output_path.with_suffix('.md')
    html_path = output_path.with_suffix('.html')
    meta_path = output_path.parent / 'glossary_merge_meta.json'

    entity_index = resolve(m.get('entity_index_path') or nrm.get('output_path') or '')
    by_surf_index = {}
    if entity_index.exists():
        by_surf_index = {r['canonical_surface']: r for r in csv.DictReader(open(entity_index))}

    sources: dict[str, str] = {}
    merged: dict[str, dict] = {}
    for inp in inputs:
        path = resolve(inp)
        if not path.exists():
            print(f"  skip (missing): {path}", flush=True)
            continue
        d = json.load(open(path))
        entries = d.get('entries', d) if isinstance(d, dict) else d
        label = path.stem
        for e in entries:
            ne = _normalise_compact(e) if isinstance(e, dict) else None
            if not ne or not ne.get('term'):
                continue
            merged[ne['term']] = ne
            sources[ne['term']] = label

    for term, e in merged.items():
        ix = by_surf_index.get(term)
        if ix:
            e['n_total_mentions'] = int(ix['n_total_mentions'])
            e['n_unique_docs'] = int(ix['n_unique_docs'])
            e['sources'] = ix['sources']
            e['pattern'] = ix['pattern']

    glossary = [e for e in merged.values() if e.get('category') != 'noise']
    noise = [e for e in merged.values() if e.get('category') == 'noise']
    cat_counts = {c: sum(1 for e in glossary if e.get('category') == c)
                  for c in {e.get('category') for e in glossary}}
    n_unc = sum(1 for e in glossary if e.get('uncertainty'))

    print(f"merged {len(merged)} entries: {len(glossary)} glossary + {len(noise)} noise")
    print(f"  uncertain: {n_unc}", flush=True)

    json.dump({
        'n_glossary': len(glossary),
        'n_noise': len(noise),
        'n_uncertain': n_unc,
        'category_counts': cat_counts,
        'pass_counts': dict(Counter(sources.values())),
        'entries': glossary,
        'noise': noise,
        'sources': sources,
    }, open(output_path, 'w'), indent=2)

    title = m.get('title') or f"{cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name)} Glossary"
    subtitle = m.get('subtitle') or 'Auto-generated study-guide companion'

    md = [f"# {title}", '', subtitle, '',
          f'**Coverage.** {len(glossary)} glossary entries (plus {len(noise)} surfaces filtered as noise).',
          '',
          f'**Quality flag.** {n_unc} entries flagged uncertain.',
          '',
          '## Categories', '', '| category | n |', '|---|---:|']
    for c, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        md.append(f'| {c} | {n} |')

    pass_counts = Counter(sources.values())
    md += ['', '## Provenance (by pass)', '', '| pass | n |', '|---|---:|']
    for p, n in pass_counts.most_common():
        md.append(f'| {p} | {n} |')

    md += ['', '## Entries (alphabetic)', '']
    glossary.sort(key=lambda e: (e.get('term') or '').lower())
    for e in glossary:
        term = e.get('term', '?')
        expansion = e.get('expansion') or ''
        cat = e.get('category', '?')
        defn = e.get('definition') or ''
        ctx = e.get('context') or ''
        notes = e.get('notes')
        u = ' ⚠' if e.get('uncertainty') else ''
        n_m = e.get('n_total_mentions')
        n_d = e.get('n_unique_docs')
        head = f"### {term}"
        if expansion:
            head += f" — *{expansion}*"
        head += u
        md += [head, '']
        if n_m and n_d:
            md.append(f"**{cat}** · {n_m:,} mentions / {n_d:,} docs")
        else:
            md.append(f"**{cat}**")
        md.append('')
        if defn:
            md += [defn, '']
        if ctx:
            md += [f"*Context:* {ctx}", '']
        if notes:
            md += [f"*Notes:* {notes}", '']

    if noise:
        md += ['## Filtered as noise', '',
               'Surfaces caught by the entity-extraction pipeline but not glossary-worthy:',
               '',
               ', '.join(f'`{e.get("term", "")}`' for e in
                         sorted(noise, key=lambda x: (x.get('term') or '').lower())),
               '']

    md_path.write_text('\n'.join(md))

    if MD2HTML.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(MD2HTML), title, subtitle],
                input='\n'.join(md), capture_output=True, text=True, check=True)
            html_path.write_text(proc.stdout)
        except Exception as e:
            print(f"  md2html failed: {e}", flush=True)

    json.dump({
        'n_glossary': len(glossary), 'n_noise': len(noise),
        'n_uncertain': n_unc,
        'category_counts': cat_counts,
        'pass_counts': dict(pass_counts),
    }, open(meta_path, 'w'), indent=2)

    print(f"\nWrote:\n  {output_path}\n  {md_path}", flush=True)
    if html_path.exists():
        print(f"  {html_path}", flush=True)


if __name__ == '__main__':
    main()
