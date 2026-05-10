#!/usr/bin/env python3
"""Term → top-25 projects by distinctiveness.

Inverse of project_vocabularies — for each glossary term, the projects where
it is *most characteristic* (highest project-share vs corpus base rate),
not merely the projects with the most absolute mentions.

Different from the existing per-term fingerprint (which lists top projects
by raw mention count). A project with 10 mentions of a rare term may rank
above a deeply-documented project with 100 mentions of a common term — that
distinction is the value.

Output: term_top_projects.{json,md,html}
"""
from __future__ import annotations
import csv
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings/corpora/arena')
ENT_ROOT = ROOT / 'entity_extraction'
RAW = ENT_ROOT / 'output/candidates_raw.csv'
NER = ENT_ROOT / 'output/ner_candidates.csv'
NER_TRF = ENT_ROOT / 'output/ner_trf_candidates.csv'
GLOSSARY = ENT_ROOT / 'output/glossary_v3.json'
PER_DOC = ROOT / 'output/per_doc'
OUT_JSON = ENT_ROOT / 'output/term_top_projects.json'
OUT_MD = ENT_ROOT / 'output/term_top_projects.md'
OUT_HTML = ENT_ROOT / 'output/term_top_projects.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MIN_TERM_MENTIONS_IN_PROJECT = 2
MIN_DISTINCTIVENESS = 3.0
MIN_PROJECT_TOTAL_MENTIONS = 10
TOP_N_PROJECTS_PER_TERM = 25


def load_doc_to_project():
    slug_to_proj = defaultdict(Counter)
    for fn in sorted(os.listdir(PER_DOC)):
        if not fn.startswith('doc_'): continue
        try: d = json.load(open(PER_DOC / fn))
        except Exception: continue
        for rec in d.get('records', []):
            mp = (rec.get('markdown_path') or '').strip()
            if not mp: continue
            parts = mp.split('/')
            slug = parts[-2] if len(parts) >= 2 else ''
            if not slug: continue
            proj = (rec.get('kb_associated_project') or '').strip()
            if proj: slug_to_proj[slug][proj] += 1
    return {s: c.most_common(1)[0][0] for s, c in slug_to_proj.items() if c}


def main():
    print("Loading slug→project map...", flush=True)
    doc_proj = load_doc_to_project()
    print(f"  {len(doc_proj)} slug→project mappings", flush=True)

    print("Loading glossary v3...", flush=True)
    g = json.load(open(GLOSSARY))
    entry_by_term = {e['term']: e for e in g['entries']}
    target_terms = set(entry_by_term)
    print(f"  {len(target_terms)} target terms", flush=True)

    print("Scanning candidate sources...", flush=True)
    # term × project mention matrix
    proj_term = defaultdict(Counter)  # proj → {term: n}
    for path in (RAW, NER, NER_TRF):
        if not path.exists(): continue
        with open(path) as f:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                if i % 200000 == 0 and i > 0:
                    print(f"  {path.name}: {i:,}", flush=True)
                surf = row.get('surface','').strip()
                if surf not in target_terms: continue
                proj = doc_proj.get(row.get('doc_id'))
                if proj: proj_term[proj][surf] += 1

    # Aggregate corpus base rates
    proj_total = {p: sum(c.values()) for p, c in proj_term.items()}
    term_corpus = Counter()
    for p, tc in proj_term.items():
        for t, n in tc.items():
            term_corpus[t] += n
    total_corpus = sum(term_corpus.values())
    print(f"  corpus total mentions: {total_corpus:,}", flush=True)
    print(f"  projects: {len(proj_total)}", flush=True)
    print(f"  terms with mentions: {len(term_corpus)}", flush=True)

    # Invert: for each term, list projects by distinctiveness
    print("Computing term → top-projects (by distinctiveness)...", flush=True)
    term_top = {}
    for term in target_terms:
        if term not in term_corpus: continue
        term_total = term_corpus[term]
        if term_total < 5: continue   # term must have ≥5 corpus mentions to be meaningful
        base_share = term_total / total_corpus
        chars = []
        for proj, term_c in proj_term.items():
            n_in_proj = term_c.get(term, 0)
            if n_in_proj < MIN_TERM_MENTIONS_IN_PROJECT: continue
            total_p = proj_total[proj]
            if total_p < MIN_PROJECT_TOTAL_MENTIONS: continue
            obs_share = n_in_proj / total_p
            if base_share <= 0: continue
            ratio = obs_share / base_share
            if ratio < MIN_DISTINCTIVENESS: continue
            chars.append({
                'project': proj,
                'n_in_project': n_in_proj,
                'project_share': round(obs_share, 4),
                'distinctiveness': round(ratio, 1),
            })
        chars.sort(key=lambda c: -c['distinctiveness'])
        chars = chars[:TOP_N_PROJECTS_PER_TERM]
        if chars:
            term_top[term] = {
                'term': term,
                'expansion': entry_by_term[term].get('expansion'),
                'category': entry_by_term[term].get('category'),
                'subcategory': entry_by_term[term].get('subcategory'),
                'corpus_total_mentions': term_total,
                'top_projects': chars,
            }

    print(f"  terms with ≥1 distinctive project: {len(term_top)}", flush=True)

    # Sort terms by corpus mentions (matches glossary ordering convention)
    sorted_terms = sorted(term_top.values(), key=lambda t: -t['corpus_total_mentions'])

    json.dump({
        'config': {'min_term_mentions': MIN_TERM_MENTIONS_IN_PROJECT,
                   'min_distinctiveness': MIN_DISTINCTIVENESS,
                   'min_project_total_mentions': MIN_PROJECT_TOTAL_MENTIONS,
                   'top_n_projects_per_term': TOP_N_PROJECTS_PER_TERM,
                   'min_corpus_mentions_for_term': 5},
        'n_terms': len(term_top),
        'terms': sorted_terms,
    }, open(OUT_JSON, 'w'), indent=2)

    # MD
    md = ['# ARENA Glossary — Top Projects per Term',
          '',
          'For each glossary term, the ARENA projects where the term is *most characteristic* — sorted by distinctiveness (project-share vs corpus base rate), not raw mention count. Inverse of the per-project vocabulary signatures.',
          '',
          f'**Method.** For each term with ≥5 corpus mentions, find projects with ≥{MIN_TERM_MENTIONS_IN_PROJECT} mentions of the term where the project-share is ≥{MIN_DISTINCTIVENESS}× the corpus base rate. Top {TOP_N_PROJECTS_PER_TERM} projects shown per term, sorted by distinctiveness.',
          '',
          f'**Coverage.** {len(term_top)} terms with at least one distinctive project.',
          '',
          f'**Reading guide.** "16.4× / 12m" means the term appears 12 times in this project, 16.4× more concentrated than its corpus-wide base rate. Higher distinctiveness = the project is more thoroughly *about* this term.',
          '',
          '## Terms (alphabetic)',
          '',
          ]

    sorted_terms_alpha = sorted(term_top.values(), key=lambda t: (t['term'] or '').lower())
    # Group by category for navigation
    by_cat = defaultdict(list)
    for t in sorted_terms_alpha:
        by_cat[t.get('category','?')].append(t)

    md.append('## Categories')
    md.append('')
    md.append('| category | n terms |')
    md.append('|---|---:|')
    for c in sorted(by_cat, key=lambda k: -len(by_cat[k])):
        md.append(f'| {c} | {len(by_cat[c])} |')
    md.append('')

    for cat in sorted(by_cat, key=lambda k: -len(by_cat[k])):
        md.append(f'## {cat}')
        md.append('')
        for t in sorted(by_cat[cat], key=lambda x: (x['term'] or '').lower()):
            term = t['term']; exp = t.get('expansion') or ''
            sub = t.get('subcategory')
            sub_label = f" · {sub}" if sub and sub != 'other' else ''
            md.append(f"### {term}" + (f" — *{exp}*" if exp else ''))
            md.append('')
            md.append(f"**{cat}**{sub_label} · {t['corpus_total_mentions']:,} mentions corpus-wide")
            md.append('')
            md.append('| rank | project | n | distinctiveness |')
            md.append('|---:|---|---:|---:|')
            for i, p in enumerate(t['top_projects'], 1):
                md.append(f"| {i} | {p['project']} | {p['n_in_project']} | {p['distinctiveness']}× |")
            md.append('')

    OUT_MD.write_text('\n'.join(md))

    # HTML
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'ARENA Glossary — Top Projects per Term',
         'Broad Learnings · Term-to-project inverse view'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD} ({len(open(OUT_MD).read()):,} chars)")
    print(f"wrote {OUT_HTML} ({len(open(OUT_HTML).read()):,} chars)")

    # Sample
    print("\n=== sample ===")
    for term in ['DERMS','GFM','HVDC','VPP','TRL','LCOE','ARENA','BESS']:
        if term not in term_top: continue
        t = term_top[term]
        print(f"\n[{term}] ({t['corpus_total_mentions']:,} corpus mentions)")
        for p in t['top_projects'][:5]:
            print(f"  {p['distinctiveness']:>5.1f}× {p['n_in_project']:>3}m  {p['project'][:70]}")


if __name__ == '__main__':
    main()
