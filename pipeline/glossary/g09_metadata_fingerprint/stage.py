"""Stage g09 — Per-term metadata fingerprint vs corpus base rate (deterministic).

Generalises:
    pipeline/development/arena_glossary/09_metadata_fingerprint.py

For each glossary term, aggregates corpus mentions by metadata dimension
(project, category, programme, lead_org, year) and computes a distinctiveness
ratio (observed share vs corpus base share). No LLM.

Reads slug → metadata directly from the corpus catalogue. The glossary
sub-pipeline is independent of the failure-mode pipeline; it never relies
on extracted insight records (per_doc/<doc>.json). The catalogue carries
the metadata fields fingerprinting needs (project/entity, category/portfolio,
year, etc.).

Inputs:
    glossary.candidate.output_dir/candidates_raw.csv
    glossary.candidate.output_dir/ner_candidates.csv     (optional)
    glossary.candidate.output_dir/ner_trf_candidates.csv (optional)
    glossary.merge.output_path                merged glossary.json
    glossary.fingerprint.catalogue_path       corpus catalogue CSV
    glossary.fingerprint.portfolio_path       optional separate portfolio CSV

Domain config (domain.yaml glossary.fingerprint):
    project_field             logical name for project/entity field
    category_field            logical name for category field
    programme_field           logical name for programme (optional)
    lead_org_field            logical name for lead-org (catalogue or portfolio)
    year_field                logical name for year field
    catalogue_path            corpus catalogue CSV
    catalogue_slug_column     column whose value identifies a doc
    catalogue_slug_extract    'url_last_segment' | 'filename_stem' | 'raw'
    catalogue_project_column  optional override; defaults to project_field
    catalogue_category_column optional override; defaults to category_field
    catalogue_year_column     optional override; defaults to year_field
    portfolio_path            optional CSV with per-project metadata
    portfolio_join_key        column in portfolio CSV matching project value
    portfolio_field_map       dict{csv_col: record_field} for enrichment
    output_path               where to write fingerprints JSON
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve, load_doc_metadata_from_catalogue


def _split_multi(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]


def _coerce_year(value):
    if value is None or value == '':
        return None
    try:
        return int(str(value)[:4])
    except (ValueError, TypeError):
        return None


def _load_portfolio(portfolio_path: Path | None, join_key: str | None,
                    field_map: dict | None):
    if not portfolio_path or not portfolio_path.exists() or not join_key or not field_map:
        return {}
    out: dict[str, dict] = {}
    for r in csv.DictReader(open(portfolio_path)):
        key = (r.get(join_key) or '').strip()
        if not key:
            continue
        rec = {}
        for csv_col, dest_field in field_map.items():
            v = r.get(csv_col)
            rec[dest_field] = (v or '').strip() if v is not None else ''
        out[key] = rec
    return out


def _distinctiveness(obs_counter: Counter, base_counter: Counter,
                     obs_total: int, top_k: int = 8):
    if obs_total == 0:
        return []
    base_total_active = sum(base_counter.values()) or 1
    out = []
    for k, n in obs_counter.most_common(top_k):
        obs_share = n / obs_total
        base_share = base_counter.get(k, 0) / base_total_active
        ratio = (obs_share / base_share) if base_share > 0 else None
        out.append({
            'name': k, 'n': n,
            'obs_share': round(obs_share, 3),
            'base_share': round(base_share, 4),
            'distinctiveness': round(ratio, 2) if ratio is not None else None,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    fp = (cfg.glossary.get('fingerprint') or {})
    c = (cfg.glossary.get('candidate') or {})
    m = (cfg.glossary.get('merge') or {})

    output_path = resolve(fp.get('output_path') or '')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cand_dir = resolve(c.get('output_dir') or '')
    glossary_path = resolve(m.get('output_path') or '')
    portfolio_path = resolve(fp['portfolio_path']) if fp.get('portfolio_path') else None

    project_field = fp.get('project_field') or ''
    category_field = fp.get('category_field') or ''
    programme_field = fp.get('programme_field') or ''
    lead_org_field = fp.get('lead_org_field') or ''
    year_field = fp.get('year_field') or ''

    if not glossary_path.exists():
        raise SystemExit(f'merged glossary missing: {glossary_path}')

    cat_path = resolve(fp['catalogue_path']) if fp.get('catalogue_path') else None
    if not cat_path:
        raise SystemExit('glossary.fingerprint.catalogue_path is required '
                         '(catalogue is the canonical metadata source)')
    slug_col = fp.get('catalogue_slug_column') or ''
    slug_pattern = fp.get('catalogue_slug_pattern')
    if not slug_col:
        raise SystemExit('glossary.fingerprint.catalogue_slug_column is required')

    print(f"Loading slug→metadata from catalogue {cat_path.name} "
          f"(slug from {slug_col!r}{', regex='+repr(slug_pattern) if slug_pattern else ''}) ...",
          flush=True)
    col_map = {}
    if project_field:
        col_map['project'] = fp.get('catalogue_project_column') or project_field
    if category_field:
        col_map['category'] = fp.get('catalogue_category_column') or category_field
    if year_field:
        col_map['year'] = fp.get('catalogue_year_column') or year_field
    rows = load_doc_metadata_from_catalogue(cat_path, slug_col, slug_pattern, col_map)
    doc_proj = {s: v['project'] for s, v in rows.items() if v.get('project')}
    doc_cat = {s: v['category'] for s, v in rows.items() if v.get('category')}

    def _yr(raw):
        import re as _re
        m_ = _re.search(r'\b(19|20)\d{2}\b', str(raw))
        return int(m_.group()) if m_ else None
    doc_year = {s: _yr(v['year']) for s, v in rows.items() if v.get('year')}
    doc_year = {s: y for s, y in doc_year.items() if y}

    print(f"  {len(doc_proj):,} slug→project mappings", flush=True)

    portfolio = _load_portfolio(portfolio_path, fp.get('portfolio_join_key'),
                                fp.get('portfolio_field_map'))
    print(f"  {len(portfolio):,} projects in portfolio (optional)", flush=True)

    print("Loading glossary terms ...", flush=True)
    glossary = json.load(open(glossary_path))
    target_terms = {e['term'] for e in glossary.get('entries', [])}
    target_terms.update(e['term'] for e in glossary.get('noise', []) if 'term' in e)
    print(f"  {len(target_terms):,} target terms", flush=True)

    raw_cands = cand_dir / 'candidates_raw.csv'
    ner_cands = cand_dir / 'ner_candidates.csv'
    ner_trf_cands = cand_dir / 'ner_trf_candidates.csv'

    print("Scanning candidate sources for term→doc mention counts ...", flush=True)
    term_doc_count: dict[str, Counter] = defaultdict(Counter)
    for path in [p for p in (raw_cands, ner_cands, ner_trf_cands) if p.exists()]:
        with open(path) as f:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                if i % 100000 == 0 and i > 0:
                    print(f"  {path.name}: {i:,}", flush=True)
                surf = row.get('surface', '').strip()
                if surf in target_terms:
                    term_doc_count[surf][row['doc_id']] += 1
    print(f"  total terms with mentions: {len(term_doc_count):,}", flush=True)

    print("Computing corpus base rates ...", flush=True)
    base_proj: Counter = Counter()
    base_cat: Counter = Counter()
    base_year: Counter = Counter()
    base_lead: Counter = Counter()
    base_program: Counter = Counter()
    total_docs = 0
    for slug, proj in doc_proj.items():
        cat = doc_cat.get(slug, '')
        year = doc_year.get(slug)
        pmeta = portfolio.get(proj, {})
        base_proj[proj] += 1
        for c_v in _split_multi(cat):
            base_cat[c_v] += 1
        if year:
            base_year[year] += 1
        lead = pmeta.get(lead_org_field) or pmeta.get('lead_org') or ''
        if lead:
            base_lead[lead] += 1
        prog = pmeta.get(programme_field) or pmeta.get('arena_program') or ''
        if prog:
            base_program[prog] += 1
        total_docs += 1
    corpus_year_list = []
    for y, n in base_year.items():
        corpus_year_list.extend([y] * n)
    corpus_year_list.sort()
    corpus_median_year = (corpus_year_list[len(corpus_year_list) // 2]
                          if corpus_year_list else None)
    print(f"  corpus base: {total_docs} mapped docs; "
          f"median year: {corpus_median_year}", flush=True)

    print("Computing per-term fingerprints ...", flush=True)
    fingerprints = {}
    for term, doc_counts in term_doc_count.items():
        n_total_mentions = sum(doc_counts.values())
        if n_total_mentions == 0:
            continue

        proj_c: Counter = Counter()
        cat_c: Counter = Counter()
        year_c: Counter = Counter()
        lead_c: Counter = Counter()
        prog_c: Counter = Counter()
        n_mapped_docs = 0
        for slug, cnt in doc_counts.items():
            proj = doc_proj.get(slug)
            if not proj:
                continue
            n_mapped_docs += 1
            cat = doc_cat.get(slug, '')
            year = doc_year.get(slug)
            pmeta = portfolio.get(proj, {})
            proj_c[proj] += cnt
            for c_v in _split_multi(cat):
                cat_c[c_v] += cnt
            if year:
                year_c[year] += cnt
            lead = pmeta.get(lead_org_field) or pmeta.get('lead_org') or ''
            if lead:
                lead_c[lead] += cnt
            prog = pmeta.get(programme_field) or pmeta.get('arena_program') or ''
            if prog:
                prog_c[prog] += cnt

        if year_c:
            mention_years = []
            for y, n in year_c.items():
                mention_years.extend([y] * n)
            mention_years.sort()
            term_median = mention_years[len(mention_years) // 2]
            delta = (term_median - corpus_median_year) if corpus_median_year else 0
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
            'n_docs': len(doc_counts),
            'n_mapped_docs': n_mapped_docs,
            'top_projects': proj_c.most_common(5),
            'top_categories': _distinctiveness(cat_c, base_cat, sum(cat_c.values())),
            'top_lead_orgs': _distinctiveness(lead_c, base_lead, sum(lead_c.values())),
            'top_programs': _distinctiveness(prog_c, base_program, sum(prog_c.values())),
            'year_distribution': dict(sorted(year_c.items())),
            'year_trajectory': trajectory,
        }

    json.dump({
        'fingerprints': fingerprints,
        'corpus_base_total_docs': total_docs,
        'corpus_median_year': corpus_median_year,
        'coverage': {
            'n_target': len(target_terms),
            'n_with_mentions': len(term_doc_count),
            'n_with_fingerprint': len(fingerprints),
        },
    }, open(output_path, 'w'), indent=2, default=str)
    print(f"\nwrote {output_path}  ({len(fingerprints):,} fingerprints)", flush=True)


if __name__ == '__main__':
    main()
