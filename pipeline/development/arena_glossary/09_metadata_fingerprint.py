#!/usr/bin/env python3
"""Compute a metadata fingerprint per glossary term:
  - Top projects, ARENA categories, lead organisations, ARENA programmes
  - Year distribution
  - Distinctiveness (observed share vs corpus base rate)

Pure data analysis — no LLM. Reads candidates_raw.csv (825k mentions),
joins to per_doc/* and portfolio.csv, aggregates per term.

Output: glossary_metadata_fingerprint.json
"""
from __future__ import annotations
import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings/corpora/arena')
ENT_ROOT = ROOT / 'entity_extraction'
RAW_CANDS = ENT_ROOT / 'output/candidates_raw.csv'
NER_CANDS = ENT_ROOT / 'output/ner_candidates.csv'
NER_TRF_CANDS = ENT_ROOT / 'output/ner_trf_candidates.csv'
GLOSSARY = ENT_ROOT / 'output/glossary.json'
PORTFOLIO = ROOT / 'portfolio.csv'
PER_DOC = ROOT / 'output/per_doc'
OUT = ENT_ROOT / 'output/glossary_metadata_fingerprint.json'

# Variants: doc_ids in the entity-extraction pipeline use the slug-style
# directory names from marker_output/<slug>/ — different from per_doc/doc_NNNN.json.
MARKER_OUT = ROOT / 'marker_output'


def load_doc_id_to_project():
    """Build slug → kb_associated_project (modal across records in that doc).
    The entity pipeline records doc_id as the marker_output subdir slug
    (e.g. 'neoen_western_downs_bess_deployment_development_report_milestone_2'),
    not the doc_NNNN form. We need to map slug → project.

    Strategy: per_doc has 'source' field on records that matches the slug.
    """
    slug_to_proj = defaultdict(Counter)  # slug → Counter of projects
    slug_to_cat = defaultdict(Counter)
    slug_to_year = defaultdict(Counter)
    slug_to_doc = {}  # slug → doc_NNNN

    for fn in sorted(os.listdir(PER_DOC)):
        if not fn.startswith('doc_'): continue
        try:
            d = json.load(open(PER_DOC / fn))
        except Exception:
            continue
        doc_id_num = fn.replace('.json','')
        for rec in d.get('records', []):
            mp = (rec.get('markdown_path') or '').strip()
            if not mp: continue
            # markdown_path: 'corpora/arena/marker_output/<slug>/<slug>.rendered.md'
            parts = mp.split('/')
            slug = parts[-2] if len(parts) >= 2 else ''
            if not slug: continue
            slug_to_doc[slug] = doc_id_num
            proj = (rec.get('kb_associated_project') or '').strip()
            cat = (rec.get('kb_category') or '').strip()
            year = rec.get('kb_year')
            if proj: slug_to_proj[slug][proj] += 1
            if cat: slug_to_cat[slug][cat] += 1
            if year:
                try: slug_to_year[slug][int(year)] += 1
                except (ValueError, TypeError): pass

    # Take modal value per slug
    doc_proj = {s: c.most_common(1)[0][0] for s, c in slug_to_proj.items() if c}
    doc_cat = {s: c.most_common(1)[0][0] for s, c in slug_to_cat.items() if c}
    doc_year = {s: c.most_common(1)[0][0] for s, c in slug_to_year.items() if c}
    return doc_proj, doc_cat, doc_year, slug_to_doc


def load_portfolio_meta():
    """project name → {Lead organisation, Arena program, ...}"""
    def s(v):
        return (v or '').strip() if v is not None else ''
    out = {}
    for r in csv.DictReader(open(PORTFOLIO)):
        p = s(r.get('Project'))
        if not p: continue
        out[p] = {
            'lead_org': s(r.get('Lead organisation')),
            'arena_program': s(r.get('Arena program')),
            'category': s(r.get('Category')),
            'status': s(r.get('Status')),
            'location': s(r.get('Location')),
            'arena_funding': s(r.get('Arena funding provided')),
            'total_value': s(r.get('Total project value')),
            'start_date': s(r.get('Start date')),
        }
    return out


def base_categories(cat_str):
    if not cat_str: return set()
    return {c.strip() for c in cat_str.split(',') if c.strip()}


def main():
    print("Loading per_doc → project/category/year maps...", flush=True)
    doc_proj, doc_cat, doc_year, slug_to_doc = load_doc_id_to_project()
    print(f"  {len(doc_proj)} slug→project mappings", flush=True)

    print("Loading portfolio metadata...", flush=True)
    portfolio = load_portfolio_meta()
    print(f"  {len(portfolio)} projects in portfolio.csv", flush=True)

    print("Loading glossary terms...", flush=True)
    glossary = json.load(open(GLOSSARY))
    target_terms = {e['term'] for e in glossary['entries']}
    # Also include noise — useful even for boundary terms
    target_terms.update(e['term'] for e in glossary.get('noise',[]) if 'term' in e)
    print(f"  {len(target_terms)} target terms", flush=True)

    # Build the term → list of doc_ids map. We need to find every mention.
    # candidates_raw.csv has columns: doc_id, surface, char_offset, pattern, ...
    # ner_candidates.csv has: doc_id, label, surface, char_offset
    # We want: for each target term, count mentions per doc, group by metadata.

    print("Scanning candidate sources for term→doc mention counts...", flush=True)
    term_doc_count = defaultdict(Counter)  # term → Counter(doc_slug → mention_count)

    # First scan: candidates_raw.csv
    with open(RAW_CANDS) as f:
        rdr = csv.DictReader(f)
        for i, row in enumerate(rdr):
            if i % 100000 == 0 and i > 0:
                print(f"  raw_cands: {i:,}", flush=True)
            surf = row.get('surface','').strip()
            if surf in target_terms:
                term_doc_count[surf][row['doc_id']] += 1
    print(f"  raw_cands done; matched on {len(term_doc_count):,} terms so far", flush=True)

    # NER + NER-TRF (also have surface column)
    for path in (NER_CANDS, NER_TRF_CANDS):
        if not path.exists(): continue
        with open(path) as f:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                if i % 100000 == 0 and i > 0:
                    print(f"  {path.name}: {i:,}", flush=True)
                surf = row.get('surface','').strip()
                if surf in target_terms:
                    term_doc_count[surf][row['doc_id']] += 1
    print(f"  total terms with mentions: {len(term_doc_count):,}", flush=True)

    # Compute corpus base rates for distinctiveness calc
    print("Computing corpus base rates...", flush=True)
    base_proj = Counter(); base_cat_base = Counter(); base_year = Counter()
    base_lead = Counter(); base_program = Counter()
    total_docs = 0
    for slug, proj in doc_proj.items():
        cat = doc_cat.get(slug, '')
        year = doc_year.get(slug)
        portfolio_meta = portfolio.get(proj, {})
        base_proj[proj] += 1
        for c in base_categories(cat):
            base_cat_base[c] += 1
        if year: base_year[year] += 1
        if portfolio_meta.get('lead_org'): base_lead[portfolio_meta['lead_org']] += 1
        if portfolio_meta.get('arena_program'): base_program[portfolio_meta['arena_program']] += 1
        total_docs += 1
    base_total = total_docs
    # Corpus-median year (weighted by docs)
    corpus_year_list = []
    for y, n in base_year.items():
        corpus_year_list.extend([y]*n)
    corpus_year_list.sort()
    corpus_median_year = corpus_year_list[len(corpus_year_list)//2] if corpus_year_list else None
    print(f"  corpus base: {total_docs} mapped docs; median year: {corpus_median_year}", flush=True)

    print("Computing per-term fingerprints...", flush=True)
    fingerprints = {}
    for term, doc_counts in term_doc_count.items():
        n_docs_with_term = len(doc_counts)
        n_total_mentions = sum(doc_counts.values())
        if n_docs_with_term == 0: continue

        # Aggregate per-metadata across mentions
        proj_c = Counter(); cat_c = Counter(); year_c = Counter()
        lead_c = Counter(); prog_c = Counter()
        n_mapped_docs = 0
        for slug, cnt in doc_counts.items():
            proj = doc_proj.get(slug)
            if not proj: continue
            n_mapped_docs += 1
            cat = doc_cat.get(slug, '')
            year = doc_year.get(slug)
            pm = portfolio.get(proj, {})
            proj_c[proj] += cnt
            for c in base_categories(cat):
                cat_c[c] += cnt
            if year: year_c[year] += cnt
            if pm.get('lead_org'): lead_c[pm['lead_org']] += cnt
            if pm.get('arena_program'): prog_c[pm['arena_program']] += cnt

        # Distinctiveness: for the top category, programme, lead — observed
        # share within term mentions vs base rate share.
        def distinctiveness(obs_counter, base_counter, obs_total, base_total):
            """Return list of (key, obs_count, obs_share, base_share, ratio) for top-5."""
            if obs_total == 0 or base_total == 0: return []
            base_total_active = sum(base_counter.values()) or 1
            out = []
            for k, n in obs_counter.most_common(8):
                obs_share = n / obs_total
                base_share = base_counter.get(k, 0) / base_total_active
                ratio = (obs_share / base_share) if base_share > 0 else float('inf')
                out.append({'name': k, 'n': n, 'obs_share': round(obs_share, 3),
                            'base_share': round(base_share, 4),
                            'distinctiveness': round(ratio, 2) if ratio != float('inf') else None})
            return out

        # Year trajectory — median-year vs corpus-median, with mention weighting
        # The earlier first-third / last-third heuristic was biased because
        # ARENA project years span 2009-2025 but most documents publish in a
        # tight band (2019-2023). The median-of-mentions vs corpus-median is
        # more robust to the heavy-middle distribution.
        if year_c:
            mention_years = []
            for y, n in year_c.items():
                mention_years.extend([y]*n)
            mention_years.sort()
            term_median = mention_years[len(mention_years)//2]
            # corpus_median_year is computed in main() and passed via closure / module
            delta = term_median - corpus_median_year
            if delta >= 1.5:
                trajectory = f"rising (median {term_median} vs corpus {corpus_median_year})"
            elif delta <= -1.5:
                trajectory = f"falling (median {term_median} vs corpus {corpus_median_year})"
            else:
                trajectory = f"steady (median {term_median})"
        else:
            trajectory = 'no_year_data'

        fingerprints[term] = {
            'term': term,
            'total_mentions': n_total_mentions,
            'n_docs': n_docs_with_term,
            'n_mapped_docs': n_mapped_docs,
            'top_projects': proj_c.most_common(5),
            'top_categories': distinctiveness(cat_c, base_cat_base, sum(cat_c.values()), base_total),
            'top_lead_orgs': distinctiveness(lead_c, base_lead, sum(lead_c.values()), base_total),
            'top_programs': distinctiveness(prog_c, base_program, sum(prog_c.values()), base_total),
            'year_distribution': dict(sorted(year_c.items())),
            'year_trajectory': trajectory,
        }

    # Coverage diagnostics
    n_target = len(target_terms)
    n_with_mentions = len(term_doc_count)
    n_with_fp = len(fingerprints)
    n_no_doc_mapping = sum(1 for term, dc in term_doc_count.items()
                            if not any(slug in doc_proj for slug in dc))
    print(f"\nFingerprint coverage:", flush=True)
    print(f"  target glossary terms: {n_target}", flush=True)
    print(f"  terms with corpus mentions: {n_with_mentions}", flush=True)
    print(f"  terms with valid project mapping: {n_with_fp}", flush=True)
    print(f"  terms whose mentions don't map to any portfolio project: {n_no_doc_mapping}", flush=True)

    print(f"  fingerprints computed: {len(fingerprints)}", flush=True)
    json.dump({'fingerprints': fingerprints,
               'corpus_base_total_docs': base_total,
               'corpus_median_year': corpus_median_year,
               'coverage': {
                   'n_target': n_target,
                   'n_with_mentions': n_with_mentions,
                   'n_with_fingerprint': n_with_fp,
                   'n_no_project_mapping': n_no_doc_mapping,
               }},
              open(OUT,'w'), indent=2, default=str)
    print(f"  wrote {OUT}", flush=True)

    # Quick sample
    print("\n=== sample fingerprints ===")
    for t in ['DERMS','BESS','HVDC','ARENA','LCOE','VPP','GFM','TRL']:
        if t not in fingerprints: continue
        f = fingerprints[t]
        print(f"\n[{t}] {f['total_mentions']:,} mentions / {f['n_docs']} docs")
        if f['top_projects']:
            ps = ', '.join(f"{p}({n})" for p, n in f['top_projects'][:3])
            print(f"  top projects: {ps}")
        if f['top_categories']:
            cs = ', '.join(f"{c['name']}({c['obs_share']:.0%}, {c['distinctiveness']}x)" for c in f['top_categories'][:3])
            print(f"  top categories: {cs}")
        if f['top_lead_orgs']:
            ls = ', '.join(f"{c['name']}({c['obs_share']:.0%}, {c['distinctiveness']}x)" for c in f['top_lead_orgs'][:3])
            print(f"  top lead orgs: {ls}")
        ymin = min(f['year_distribution']) if f['year_distribution'] else '?'
        ymax = max(f['year_distribution']) if f['year_distribution'] else '?'
        print(f"  year trajectory: {f['year_trajectory']}, range: {ymin}-{ymax}")


if __name__ == '__main__':
    main()
