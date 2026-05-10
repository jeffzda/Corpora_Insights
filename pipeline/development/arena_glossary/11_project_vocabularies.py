#!/usr/bin/env python3
"""Project vocabulary signatures — inverse of the glossary fingerprint.

For each ARENA project, list the glossary terms that appear there at
disproportionately high rates vs the corpus base — i.e. the project's
characteristic vocabulary.

Outputs:
  output/project_vocabularies.json
  output/project_vocabularies.md
  output/project_vocabularies.html
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
PORTFOLIO = ROOT / 'portfolio.csv'
PER_DOC = ROOT / 'output/per_doc'
OUT_JSON = ENT_ROOT / 'output/project_vocabularies.json'
OUT_MD = ENT_ROOT / 'output/project_vocabularies.md'
OUT_HTML = ENT_ROOT / 'output/project_vocabularies.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

MIN_TERM_MENTIONS_IN_PROJECT = 2
MIN_DISTINCTIVENESS = 3.0
MIN_DOCS_FOR_PROJECT = 1
MIN_TOTAL_PROJECT_MENTIONS = 10
TOP_N_TERMS_PER_PROJECT = 25


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

    print("Loading glossary v3...", flush=True)
    g = json.load(open(GLOSSARY))
    # term → entry (for definitions / categories)
    entry_by_term = {e['term']: e for e in g['entries']}
    target_terms = set(entry_by_term)

    print("Scanning all candidate sources for term×doc mentions...", flush=True)
    term_doc_count = defaultdict(Counter)  # term → {doc_slug: n}
    for path in (RAW, NER, NER_TRF):
        if not path.exists(): continue
        with open(path) as f:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                if i % 200000 == 0 and i > 0:
                    print(f"  {path.name}: {i:,}", flush=True)
                surf = row.get('surface','').strip()
                if surf in target_terms:
                    term_doc_count[surf][row['doc_id']] += 1
    print(f"  terms with mentions: {len(term_doc_count):,}", flush=True)

    # Aggregate per project
    print("Aggregating per project...", flush=True)
    proj_term_count = defaultdict(Counter)  # project → {term: n}
    proj_doc_count = Counter()  # project → n_docs
    proj_doc_set = defaultdict(set)
    term_corpus_count = Counter()
    for term, doc_counts in term_doc_count.items():
        for slug, n in doc_counts.items():
            proj = doc_proj.get(slug)
            if not proj: continue
            proj_term_count[proj][term] += n
            term_corpus_count[term] += n
            proj_doc_set[proj].add(slug)
    proj_doc_count = {p: len(s) for p, s in proj_doc_set.items()}

    # Corpus base rate per term
    total_corpus_mentions = sum(term_corpus_count.values())
    total_proj_mentions = {p: sum(c.values()) for p, c in proj_term_count.items()}

    # For each project, compute distinctive terms
    proj_chars = {}
    for proj, term_c in proj_term_count.items():
        if proj_doc_count[proj] < MIN_DOCS_FOR_PROJECT:
            continue
        total_p = total_proj_mentions[proj]
        if total_p < MIN_TOTAL_PROJECT_MENTIONS:
            continue
        chars = []
        for term, n_in_proj in term_c.items():
            if n_in_proj < MIN_TERM_MENTIONS_IN_PROJECT: continue
            obs_share = n_in_proj / total_p
            base_share = term_corpus_count[term] / total_corpus_mentions
            if base_share <= 0: continue
            ratio = obs_share / base_share
            if ratio < MIN_DISTINCTIVENESS: continue
            entry = entry_by_term.get(term, {})
            chars.append({
                'term': term,
                'expansion': entry.get('expansion'),
                'category': entry.get('category'),
                'subcategory': entry.get('subcategory'),
                'n_in_project': n_in_proj,
                'distinctiveness': round(ratio, 1),
                'project_share': round(obs_share, 3),
            })
        chars.sort(key=lambda c: -c['distinctiveness'])
        chars = chars[:TOP_N_TERMS_PER_PROJECT]
        if chars:
            proj_chars[proj] = {
                'project': proj,
                'n_docs': proj_doc_count[proj],
                'n_total_mentions': total_p,
                'characteristic_terms': chars,
            }

    print(f"  projects with characteristic vocabulary: {len(proj_chars)}", flush=True)

    # Sort projects by total mentions desc for stable output
    sorted_proj = sorted(proj_chars.values(), key=lambda p: -p['n_total_mentions'])

    json.dump({
        'config': {'min_term_mentions': MIN_TERM_MENTIONS_IN_PROJECT,
                   'min_distinctiveness': MIN_DISTINCTIVENESS,
                   'min_docs_for_project': MIN_DOCS_FOR_PROJECT,
                   'min_total_project_mentions': MIN_TOTAL_PROJECT_MENTIONS,
                   'top_n_per_project': TOP_N_TERMS_PER_PROJECT},
        'n_projects': len(proj_chars),
        'projects': sorted_proj,
    }, open(OUT_JSON, 'w'), indent=2)

    # MD
    md = ['# ARENA Project Vocabulary Signatures',
          '',
          'For each project in the ARENA portfolio, the glossary terms that appear at disproportionately high rates vs the corpus base. A project\'s "vocabulary signature" — terms that are characteristic of *this* project rather than the corpus generally.',
          '',
          f'**Method.** For each project, find glossary terms with ≥{MIN_TERM_MENTIONS_IN_PROJECT} mentions in the project where the project-share is ≥{MIN_DISTINCTIVENESS}× the corpus base rate. Top {TOP_N_TERMS_PER_PROJECT} terms shown per project.',
          '',
          f'**Coverage.** {len(proj_chars)} projects with ≥{MIN_DOCS_FOR_PROJECT} doc and ≥{MIN_TOTAL_PROJECT_MENTIONS} total term mentions.',
          '',
          f'**Reading guide.** "5.2× / 14m" means: the term appears 14 times in this project, 5.2× more concentrated than its corpus-wide base rate. Higher distinctiveness = more characteristic.',
          '',
          '## Projects (by total glossary mentions)',
          '',
          ]

    for p in sorted_proj:
        md.append(f"### {p['project']}")
        md.append('')
        md.append(f"{p['n_docs']} docs · {p['n_total_mentions']:,} term mentions · {len(p['characteristic_terms'])} characteristic terms")
        md.append('')
        md.append('| term | expansion | category | n | distinctiveness |')
        md.append('|---|---|---|---:|---:|')
        for c in p['characteristic_terms']:
            exp = c.get('expansion') or ''
            cat = c.get('category') or ''
            sub = c.get('subcategory')
            cat_label = f"{cat}/{sub}" if sub and sub != 'other' else cat
            md.append(f"| **{c['term']}** | {exp} | {cat_label} | {c['n_in_project']} | {c['distinctiveness']}× |")
        md.append('')

    OUT_MD.write_text('\n'.join(md))

    # HTML
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'ARENA Project Vocabulary Signatures',
         'Broad Learnings · Inverse glossary view'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD} ({len(open(OUT_MD).read()):,} chars)")
    print(f"wrote {OUT_HTML} ({len(open(OUT_HTML).read()):,} chars)")

    # Sample
    print("\n=== sample vocab signatures ===")
    for p in sorted_proj[:5]:
        terms = ', '.join(c['term'] for c in p['characteristic_terms'][:8])
        print(f"\n[{p['project'][:60]}] ({p['n_docs']} docs, {p['n_total_mentions']:,} mentions)")
        print(f"  top terms: {terms}")


if __name__ == '__main__':
    main()
