"""Stage g10 — Final glossary merge: entries + subcategories + fingerprints.

Generalises:
    pipeline/development/arena_glossary/10_glossary_v3_merge.py

Combines merged glossary + subcategory assignments + per-term fingerprints into
a single navigable v3 artefact (JSON/MD/HTML), organised by category > subcategory.

Domain config (domain.yaml glossary.finalise):
    output_json
    output_md
    output_html
    title              default '<corpus_full_name> Glossary v3'
    subtitle           default 'Sub-categorised + corpus-fingerprinted'
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')


def _fmt_fingerprint(fp: dict) -> str:
    if not fp:
        return ''
    n_m = fp.get('total_mentions', 0)
    n_d = fp.get('n_docs', 0)
    traj = fp.get('year_trajectory', '')
    yd = fp.get('year_distribution', {})
    if yd:
        years = sorted(int(y) for y in yd.keys())
        yr_range = f"{years[0]}–{years[-1]}"
    else:
        yr_range = '?'

    parts = []
    if traj and traj not in ('no_year_data', 'short_window'):
        parts.append(f"trajectory: **{traj}** {yr_range}")
    elif yr_range != '?':
        parts.append(f"years: {yr_range}")

    cats = fp.get('top_categories', [])
    if cats:
        sig = [c for c in cats if c.get('distinctiveness') and c.get('obs_share', 0) >= 0.10]
        sig.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig:
            top3 = sig[:3]
            parts.append("category concentration: " + ", ".join(
                f"{c['name']} ({int(c['obs_share']*100)}% / {c['distinctiveness']:.1f}×)"
                for c in top3))

    leads = fp.get('top_lead_orgs', [])
    if leads:
        sig_leads = [l for l in leads if l.get('distinctiveness') and l.get('obs_share', 0) >= 0.10]
        sig_leads.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig_leads:
            top3 = sig_leads[:3]
            parts.append("lead orgs: " + ", ".join(
                f"{c['name']} ({int(c['obs_share']*100)}% / {c['distinctiveness']:.1f}×)"
                for c in top3))

    progs = fp.get('top_programs', [])
    if progs and progs[0].get('distinctiveness') and progs[0].get('distinctiveness', 0) >= 1.5 \
            and progs[0].get('obs_share', 0) >= 0.20:
        sig_progs = [p for p in progs if p.get('obs_share', 0) >= 0.10]
        sig_progs.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig_progs:
            top2 = sig_progs[:2]
            parts.append("programmes: " + ", ".join(
                f"{p['name']} ({int(p['obs_share']*100)}%)" for p in top2))

    projs = fp.get('top_projects', [])
    if projs:
        top3 = projs[:3]
        parts.append("top projects: " + ", ".join(
            f"{p[0]} ({p[1]})" for p in top3))

    if not parts:
        return ''

    lines = [f"*Fingerprint* ({n_m:,} mentions / {n_d} docs):"]
    for p in parts:
        lines.append(f"  - {p}")
    return '\n'.join(lines)


def _render_entry(md, e):
    term = e.get('term', '?')
    expansion = e.get('expansion') or ''
    cat = e.get('category', '?')
    defn = e.get('definition', '') or ''
    ctx = e.get('context') or e.get('arena_context') or ''
    notes = e.get('notes')
    u = ' ⚠' if e.get('uncertainty') else ''
    n_m = e.get('n_total_mentions')
    n_d = e.get('n_unique_docs')
    head = f"#### {term}"
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
        md += [f"*Context (model):* {ctx}", '']
    fp = e.get('metadata_fingerprint')
    if fp:
        block = _fmt_fingerprint(fp)
        if block:
            md += [block, '']
    if notes:
        md += [f"*Notes:* {notes}", '']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    fin = (cfg.glossary.get('finalise') or {})
    m = (cfg.glossary.get('merge') or {})
    s = (cfg.glossary.get('subcategory') or {})
    fp = (cfg.glossary.get('fingerprint') or {})

    glossary_path = resolve(m.get('output_path') or '')
    sub_path_dir = resolve(s.get('output_dir') or glossary_path.parent)
    sub_path = sub_path_dir / 'glossary_subcategories.json'
    fp_path = resolve(fp.get('output_path') or '')

    out_json = resolve(fin.get('output_json') or '')
    out_md = resolve(fin.get('output_md') or out_json.with_suffix('.md'))
    out_html = resolve(fin.get('output_html') or out_json.with_suffix('.html'))
    out_json.parent.mkdir(parents=True, exist_ok=True)

    title = fin.get('title') or f"{cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name)} Glossary v3"
    subtitle = fin.get('subtitle') or 'Sub-categorised + corpus-fingerprinted'

    if not glossary_path.exists():
        raise SystemExit(f'merged glossary missing: {glossary_path}')

    g = json.load(open(glossary_path))
    subs_data = json.load(open(sub_path)) if sub_path.exists() else {'assignments': []}
    fp_data = json.load(open(fp_path)) if fp_path.exists() else {'fingerprints': {}}

    sub_map = {a['t']: a['s'] for a in subs_data.get('assignments', [])}
    fp_map = fp_data.get('fingerprints', {})

    entries = list(g['entries'])
    noise = list(g.get('noise', []))

    for e in entries:
        e['subcategory'] = sub_map.get(e.get('term'))
        e['metadata_fingerprint'] = fp_map.get(e.get('term'))

    by_cat_sub: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    cat_only: dict[str, list] = defaultdict(list)
    for e in entries:
        c = e.get('category', '?')
        sub = e.get('subcategory')
        if sub:
            by_cat_sub[c][sub].append(e)
        else:
            cat_only[c].append(e)

    md = [f"# {title}", '', subtitle, '',
          f'**Coverage.** {len(entries)} glossary entries.',
          '',
          '**How to read fingerprint distinctiveness.** A category at "(65% / 7.9×)" means: '
          '65% of this term\'s mentions fall in that category, which is 7.9× the rate the '
          'same category appears in the broader corpus. Values >2× indicate the term is a '
          'marker for that cohort. Values near 1.0× indicate general-vocabulary.',
          '']

    cat_counts = {c: sum(len(es) for es in subs.values()) + len(cat_only[c])
                  for c, subs in by_cat_sub.items()}
    for c in cat_only:
        if c not in cat_counts:
            cat_counts[c] = len(cat_only[c])

    md += ['## Categories', '', '| category | n |', '|---|---:|']
    for c, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        md.append(f'| {c} | {n} |')
    md.append('')

    render_order = sorted(set(by_cat_sub) | set(cat_only),
                          key=lambda c: -cat_counts.get(c, 0))
    for cat in render_order:
        if cat not in by_cat_sub and cat not in cat_only:
            continue
        md += [f'## {cat}', '']
        subs = by_cat_sub.get(cat, {})
        sub_order = sorted(subs.keys(), key=lambda s: -len(subs[s]))
        for sub in sub_order:
            sub_entries = subs[sub]
            md += [f'### {sub}  ({len(sub_entries)})', '']
            sub_entries.sort(key=lambda e: (e.get('term') or '').lower())
            for e in sub_entries:
                _render_entry(md, e)
        if cat_only.get(cat):
            md += [f'### (uncategorised)  ({len(cat_only[cat])})', '']
            for e in sorted(cat_only[cat], key=lambda e: (e.get('term') or '').lower()):
                _render_entry(md, e)

    if noise:
        md += ['## Filtered as noise', '',
               'Surfaces caught by the entity-extraction pipeline but not glossary-worthy:',
               '',
               ', '.join(f'`{n.get("term", "")}`' for n in
                         sorted(noise, key=lambda n: (n.get('term', '') or '').lower())),
               '']

    out_md.write_text('\n'.join(md))

    json.dump({
        'n_entries': len(entries),
        'n_noise': len(noise),
        'category_counts': cat_counts,
        'subcategory_counts': {f'{c}/{s}': len(es)
                               for c, ss in by_cat_sub.items() for s, es in ss.items()},
        'entries': entries,
        'noise': noise,
    }, open(out_json, 'w'), indent=2, default=str)

    if MD2HTML.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(MD2HTML), title, subtitle],
                input='\n'.join(md), capture_output=True, text=True, check=True)
            out_html.write_text(proc.stdout)
        except Exception as e:
            print(f"  md2html failed: {e}", flush=True)

    print(f"wrote {out_json} ({len(entries)} entries)")
    print(f"wrote {out_md}")
    if out_html.exists():
        print(f"wrote {out_html}")


if __name__ == '__main__':
    main()
