#!/usr/bin/env python3
"""Glossary v3 merge — combine v2 entries + subcategory assignments + metadata
fingerprints into a single navigable artefact organised by subcategory.

Inputs:
  output/glossary.json (v2: 760 entries + noise)
  output/glossary_subcategories.json (subcategory assignment per entry)
  output/glossary_metadata_fingerprint.json (corpus-mention fingerprint per term)

Outputs:
  output/glossary_v3.json
  output/glossary_v3.md  (organised by category > subcategory)
  output/glossary_v3.html
"""
from __future__ import annotations
import json
import subprocess
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / 'output/glossary.json'
SUBS = ROOT / 'output/glossary_subcategories.json'
FP = ROOT / 'output/glossary_metadata_fingerprint.json'
OUT_JSON = ROOT / 'output/glossary_v3.json'
OUT_MD = ROOT / 'output/glossary_v3.md'
OUT_HTML = ROOT / 'output/glossary_v3.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'


def fmt_fingerprint_block(fp):
    """Render a per-term metadata fingerprint as a short markdown block."""
    if not fp: return ''
    lines = []
    n_m = fp.get('total_mentions', 0)
    n_d = fp.get('n_docs', 0)
    traj = fp.get('year_trajectory','')
    yd = fp.get('year_distribution', {})
    if yd:
        # year keys may be strings (after JSON round-trip)
        years = sorted(int(y) for y in yd.keys())
        yr_range = f"{years[0]}–{years[-1]}"
    else:
        yr_range = '?'

    parts = []
    if traj and traj not in ('no_year_data','short_window'):
        parts.append(f"trajectory: **{traj}** {yr_range}")
    elif yr_range != '?':
        parts.append(f"years: {yr_range}")

    cats = fp.get('top_categories', [])
    if cats:
        # Pick the most distinctive (highest distinctiveness) where obs_share ≥ 0.10
        sig = [c for c in cats if c.get('distinctiveness') and c.get('obs_share',0) >= 0.10]
        sig.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig:
            top3 = sig[:3]
            parts.append("category concentration: " + ", ".join(
                f"{c['name']} ({int(c['obs_share']*100)}% / {c['distinctiveness']:.1f}×)" for c in top3
            ))
    leads = fp.get('top_lead_orgs', [])
    if leads:
        sig_leads = [l for l in leads if l.get('distinctiveness') and l.get('obs_share',0) >= 0.10]
        sig_leads.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig_leads:
            top3 = sig_leads[:3]
            parts.append("lead orgs: " + ", ".join(
                f"{c['name']} ({int(c['obs_share']*100)}% / {c['distinctiveness']:.1f}×)" for c in top3
            ))

    progs = fp.get('top_programs', [])
    if progs and progs[0].get('distinctiveness',0) >= 1.5 and progs[0].get('obs_share',0) >= 0.20:
        sig_progs = [p for p in progs if p.get('obs_share',0) >= 0.10]
        sig_progs.sort(key=lambda c: -(c.get('distinctiveness') or 0))
        if sig_progs:
            top2 = sig_progs[:2]
            parts.append("ARENA programmes: " + ", ".join(
                f"{p['name']} ({int(p['obs_share']*100)}%)" for p in top2
            ))

    projs = fp.get('top_projects', [])
    if projs:
        top3 = projs[:3]
        parts.append("top projects: " + ", ".join(
            f"{p[0]} ({p[1]})" for p in top3
        ))

    if not parts:
        return ''

    lines.append(f"*Fingerprint* ({n_m:,} mentions / {n_d} docs):")
    for p in parts:
        lines.append(f"  - {p}")
    return '\n'.join(lines)


def main():
    g = json.load(open(GLOSSARY))
    subs_data = json.load(open(SUBS)) if SUBS.exists() else {'assignments': []}
    fp_data = json.load(open(FP)) if FP.exists() else {'fingerprints': {}}

    sub_map = {a['t']: a['s'] for a in subs_data.get('assignments', [])}
    fp_map = fp_data.get('fingerprints', {})

    entries = list(g['entries'])
    noise = list(g.get('noise', []))

    # Augment
    for e in entries:
        e['subcategory'] = sub_map.get(e.get('term'))
        e['metadata_fingerprint'] = fp_map.get(e.get('term'))

    # Group by category > subcategory
    by_cat_sub = defaultdict(lambda: defaultdict(list))
    cat_only = defaultdict(list)
    for e in entries:
        c = e.get('category','?')
        s = e.get('subcategory')
        if s:
            by_cat_sub[c][s].append(e)
        else:
            cat_only[c].append(e)

    # === MD rendering ===
    md = ['# ARENA Corpus Glossary v3',
          '',
          'Study-guide companion to ARENA project reports. Empirical scope set by the corpus (which terms appear, ranked by document coverage); definitions written by Sonnet 4.6 across four passes; subcategories assigned by Sonnet via a Sonnet-proposed taxonomy; per-term *fingerprints* compute observed metadata concentrations vs corpus base rates.',
          '',
          f'**Coverage.** {len(entries)} glossary entries across the corpus of 1,440 ARENA Knowledge Bank documents.',
          '',
          f'**How to read fingerprint distinctiveness.** A category at "(65% / 7.9×)" means: 65% of this term\'s mentions fall in that category, which is 7.9× the rate the same category appears in the broader corpus. Values >2× indicate the term is a marker for that cohort. Values near 1.0× indicate the term is general-vocabulary.',
          '']

    # Top-level navigation
    md += ['## Categories', '', '| category | n |', '|---|---:|']
    cat_counts = {c: sum(len(es) for es in subs.values()) + len(cat_only[c])
                  for c, subs in by_cat_sub.items()}
    for c in cat_only:
        if c not in cat_counts:
            cat_counts[c] = len(cat_only[c])
    for c, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        md.append(f'| {c} | {n} |')
    md.append('')

    # Body — by category, then subcategory
    for cat in ['technology','organisation','concept','market','regulation',
                'programme','standard','location','unit','event','person']:
        if cat not in by_cat_sub and cat not in cat_only: continue
        md.append(f'## {cat}')
        md.append('')
        # subcategory order: by size descending
        subs = by_cat_sub.get(cat, {})
        sub_order = sorted(subs.keys(), key=lambda s: -len(subs[s]))
        for sub in sub_order:
            sub_entries = subs[sub]
            md.append(f'### {sub}  ({len(sub_entries)})')
            md.append('')
            sub_entries.sort(key=lambda e: (e.get('term') or '').lower())
            for e in sub_entries:
                _render_entry(md, e)
        # entries with no subcategory in this top category
        if cat_only.get(cat):
            md.append(f'### (uncategorised)  ({len(cat_only[cat])})')
            md.append('')
            for e in sorted(cat_only[cat], key=lambda e: (e.get('term') or '').lower()):
                _render_entry(md, e)

    # Noise list at end
    if noise:
        md += ['## Filtered as noise', '',
               'Surfaces caught by the entity-extraction pipeline but not glossary-worthy:',
               '',
               ', '.join(f'`{n.get("term","")}`' for n in sorted(noise, key=lambda n: (n.get('term','') or '').lower())),
               '']

    OUT_MD.write_text('\n'.join(md))

    # JSON
    json.dump({
        'n_entries': len(entries),
        'n_noise': len(noise),
        'category_counts': cat_counts,
        'subcategory_counts': {f'{c}/{s}': len(es) for c, ss in by_cat_sub.items() for s, es in ss.items()},
        'entries': entries,
        'noise': noise,
    }, open(OUT_JSON, 'w'), indent=2, default=str)

    # HTML
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'ARENA Corpus Glossary v3',
         'Broad Learnings · Sub-categorised + corpus-fingerprinted'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON} ({len(entries)} entries)")
    print(f"wrote {OUT_MD} ({len(open(OUT_MD).read()):,} chars)")
    print(f"wrote {OUT_HTML} ({len(open(OUT_HTML).read()):,} chars)")
    # Quick distribution
    print(f"\nsubcategory distribution:")
    for c, ss in by_cat_sub.items():
        print(f"  {c}:")
        for s in sorted(ss, key=lambda k: -len(ss[k])):
            print(f"    {len(ss[s]):>3}  {s}")


def _render_entry(md, e):
    term = e.get('term','?')
    expansion = e.get('expansion') or ''
    cat = e.get('category','?')
    defn = e.get('definition','') or ''
    ctx = e.get('arena_context','') or ''
    notes = e.get('notes')
    u = ' ⚠' if e.get('uncertainty') else ''
    n_m = e.get('n_total_mentions')
    n_d = e.get('n_unique_docs')
    head = f"#### {term}"
    if expansion: head += f" — *{expansion}*"
    head += u
    md.append(head); md.append('')
    if n_m and n_d:
        md.append(f"**{cat}** · {n_m:,} mentions / {n_d:,} docs")
    else:
        md.append(f"**{cat}**")
    md.append('')
    if defn: md.append(defn); md.append('')
    if ctx: md.append(f"*ARENA context (model):* {ctx}"); md.append('')
    fp = e.get('metadata_fingerprint')
    if fp:
        block = fmt_fingerprint_block(fp)
        if block:
            md.append(block); md.append('')
    if notes: md.append(f"*Notes:* {notes}"); md.append('')


if __name__ == '__main__':
    main()
