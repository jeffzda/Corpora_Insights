"""Stage g11 — Inverse signatures: project vocab + term top-projects.

Generalises:
    pipeline/development/arena_glossary/11_project_vocabularies.py
    pipeline/development/arena_glossary/12_term_top_projects.py

Two views from the same per-term × per-project distinctiveness matrix:
    --view project_vocab       — per project, terms most characteristic
    --view term_top_projects   — per term, projects where it is most concentrated
    --view both                — emit both (default)

Domain config (domain.yaml glossary.inverses):
    distinctiveness_floor      default 3.0
    min_term_mentions          default 2
    min_project_total_mentions default 10
    top_n                      default 25
    output_dir
"""
from __future__ import annotations
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve, load_doc_metadata_from_catalogue

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')


def _build_proj_term_matrix(cand_dir: Path, target_terms: set[str], doc_proj: dict[str, str]):
    proj_term: dict[str, Counter] = defaultdict(Counter)
    proj_doc_set: dict[str, set] = defaultdict(set)
    for fn in ('candidates_raw.csv', 'ner_candidates.csv', 'ner_trf_candidates.csv'):
        path = cand_dir / fn
        if not path.exists():
            continue
        with open(path) as f:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                if i % 200000 == 0 and i > 0:
                    print(f"  {path.name}: {i:,}", flush=True)
                surf = row.get('surface', '').strip()
                if surf not in target_terms:
                    continue
                proj = doc_proj.get(row.get('doc_id'))
                if not proj:
                    continue
                proj_term[proj][surf] += 1
                proj_doc_set[proj].add(row.get('doc_id'))
    return proj_term, proj_doc_set


def _project_vocab_view(proj_term, proj_doc_set, target_terms, entry_by_term,
                        cfg_inverses, out_dir, corpus_label):
    min_term = int(cfg_inverses.get('min_term_mentions', 2))
    min_dist = float(cfg_inverses.get('distinctiveness_floor', 3.0))
    min_total = int(cfg_inverses.get('min_project_total_mentions', 10))
    top_n = int(cfg_inverses.get('top_n', 25))

    proj_total = {p: sum(c.values()) for p, c in proj_term.items()}
    term_corpus: Counter = Counter()
    for p, tc in proj_term.items():
        for t, n in tc.items():
            term_corpus[t] += n
    total_corpus = sum(term_corpus.values()) or 1

    proj_chars = {}
    for proj, term_c in proj_term.items():
        total_p = proj_total[proj]
        if total_p < min_total:
            continue
        chars = []
        for term, n_in_proj in term_c.items():
            if n_in_proj < min_term:
                continue
            obs_share = n_in_proj / total_p
            base_share = term_corpus[term] / total_corpus
            if base_share <= 0:
                continue
            ratio = obs_share / base_share
            if ratio < min_dist:
                continue
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
        if chars:
            proj_chars[proj] = {
                'project': proj,
                'n_docs': len(proj_doc_set[proj]),
                'n_total_mentions': total_p,
                'characteristic_terms': chars[:top_n],
            }

    sorted_proj = sorted(proj_chars.values(), key=lambda p: -p['n_total_mentions'])
    out_json = out_dir / 'project_vocabularies.json'
    out_md = out_dir / 'project_vocabularies.md'
    out_html = out_dir / 'project_vocabularies.html'
    title = f"{corpus_label} Project Vocabulary Signatures"

    json.dump({
        'config': {'min_term_mentions': min_term, 'min_distinctiveness': min_dist,
                   'min_total_project_mentions': min_total, 'top_n_per_project': top_n},
        'n_projects': len(proj_chars),
        'projects': sorted_proj,
    }, open(out_json, 'w'), indent=2)

    md = [f"# {title}", '',
          f"For each project, glossary terms that appear at disproportionately high rates vs the corpus base. The project's vocabulary signature.",
          '',
          f'**Method.** For each project, find glossary terms with ≥{min_term} mentions where the project-share is ≥{min_dist}× the corpus base rate. Top {top_n} per project.',
          '',
          f'**Coverage.** {len(proj_chars)} projects.',
          '',
          '## Projects (by total glossary mentions)', '']

    for p in sorted_proj:
        md += [f"### {p['project']}", '',
               f"{p['n_docs']} docs · {p['n_total_mentions']:,} term mentions · "
               f"{len(p['characteristic_terms'])} characteristic terms", '',
               '| term | expansion | category | n | distinctiveness |',
               '|---|---|---|---:|---:|']
        for c in p['characteristic_terms']:
            exp = c.get('expansion') or ''
            cat = c.get('category') or ''
            sub = c.get('subcategory')
            cat_label = f"{cat}/{sub}" if sub and sub != 'other' else cat
            md.append(f"| **{c['term']}** | {exp} | {cat_label} | {c['n_in_project']} "
                      f"| {c['distinctiveness']}× |")
        md.append('')

    out_md.write_text('\n'.join(md))
    if MD2HTML.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(MD2HTML), title, 'Inverse glossary view'],
                input='\n'.join(md), capture_output=True, text=True, check=True)
            out_html.write_text(proc.stdout)
        except Exception:
            pass

    print(f"wrote {out_json}\nwrote {out_md}", flush=True)
    if out_html.exists():
        print(f"wrote {out_html}", flush=True)


def _term_top_projects_view(proj_term, proj_doc_set, target_terms, entry_by_term,
                            cfg_inverses, out_dir, corpus_label):
    min_term = int(cfg_inverses.get('min_term_mentions', 2))
    min_dist = float(cfg_inverses.get('distinctiveness_floor', 3.0))
    min_total = int(cfg_inverses.get('min_project_total_mentions', 10))
    top_n = int(cfg_inverses.get('top_n', 25))
    min_corpus_for_term = int(cfg_inverses.get('min_corpus_mentions_for_term', 5))

    proj_total = {p: sum(c.values()) for p, c in proj_term.items()}
    term_corpus: Counter = Counter()
    for p, tc in proj_term.items():
        for t, n in tc.items():
            term_corpus[t] += n
    total_corpus = sum(term_corpus.values()) or 1

    term_top = {}
    for term in target_terms:
        if term not in term_corpus:
            continue
        term_total = term_corpus[term]
        if term_total < min_corpus_for_term:
            continue
        base_share = term_total / total_corpus
        chars = []
        for proj, term_c in proj_term.items():
            n_in_proj = term_c.get(term, 0)
            if n_in_proj < min_term:
                continue
            total_p = proj_total[proj]
            if total_p < min_total:
                continue
            obs_share = n_in_proj / total_p
            if base_share <= 0:
                continue
            ratio = obs_share / base_share
            if ratio < min_dist:
                continue
            chars.append({
                'project': proj, 'n_in_project': n_in_proj,
                'project_share': round(obs_share, 4),
                'distinctiveness': round(ratio, 1),
            })
        chars.sort(key=lambda c: -c['distinctiveness'])
        if chars:
            term_top[term] = {
                'term': term,
                'expansion': entry_by_term[term].get('expansion'),
                'category': entry_by_term[term].get('category'),
                'subcategory': entry_by_term[term].get('subcategory'),
                'corpus_total_mentions': term_total,
                'top_projects': chars[:top_n],
            }

    sorted_terms = sorted(term_top.values(), key=lambda t: -t['corpus_total_mentions'])
    out_json = out_dir / 'term_top_projects.json'
    out_md = out_dir / 'term_top_projects.md'
    out_html = out_dir / 'term_top_projects.html'
    title = f"{corpus_label} Glossary — Top Projects per Term"

    json.dump({
        'config': {'min_term_mentions': min_term, 'min_distinctiveness': min_dist,
                   'min_project_total_mentions': min_total,
                   'top_n_projects_per_term': top_n,
                   'min_corpus_mentions_for_term': min_corpus_for_term},
        'n_terms': len(term_top),
        'terms': sorted_terms,
    }, open(out_json, 'w'), indent=2)

    md = [f"# {title}", '',
          'For each glossary term, the projects where it is most characteristic '
          '(project-share vs corpus base rate). Inverse of the per-project signatures.',
          '',
          f'**Method.** For each term with ≥{min_corpus_for_term} corpus mentions, find '
          f'projects with ≥{min_term} mentions where the project-share is ≥{min_dist}× '
          f'the corpus base. Top {top_n} per term.',
          '',
          f'**Coverage.** {len(term_top)} terms.',
          '']

    by_cat = defaultdict(list)
    for t in sorted(term_top.values(), key=lambda x: (x.get('term') or '').lower()):
        by_cat[t.get('category', '?')].append(t)

    md += ['## Categories', '', '| category | n terms |', '|---|---:|']
    for c in sorted(by_cat, key=lambda k: -len(by_cat[k])):
        md.append(f'| {c} | {len(by_cat[c])} |')
    md.append('')

    for cat in sorted(by_cat, key=lambda k: -len(by_cat[k])):
        md += [f'## {cat}', '']
        for t in sorted(by_cat[cat], key=lambda x: (x['term'] or '').lower()):
            term = t['term']; exp = t.get('expansion') or ''
            sub = t.get('subcategory')
            sub_label = f" · {sub}" if sub and sub != 'other' else ''
            md += [f"### {term}" + (f" — *{exp}*" if exp else ''), '']
            md += [f"**{cat}**{sub_label} · {t['corpus_total_mentions']:,} mentions corpus-wide", '',
                   '| rank | project | n | distinctiveness |',
                   '|---:|---|---:|---:|']
            for i, p in enumerate(t['top_projects'], 1):
                md.append(f"| {i} | {p['project']} | {p['n_in_project']} "
                          f"| {p['distinctiveness']}× |")
            md.append('')

    out_md.write_text('\n'.join(md))
    if MD2HTML.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(MD2HTML), title, 'Term-to-project inverse view'],
                input='\n'.join(md), capture_output=True, text=True, check=True)
            out_html.write_text(proc.stdout)
        except Exception:
            pass

    print(f"wrote {out_json}\nwrote {out_md}", flush=True)
    if out_html.exists():
        print(f"wrote {out_html}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    ap.add_argument('--view', choices=['project_vocab', 'term_top_projects', 'both'],
                    default='both')
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    inv = (cfg.glossary.get('inverses') or {})
    c = (cfg.glossary.get('candidate') or {})
    fp = (cfg.glossary.get('fingerprint') or {})
    fin = (cfg.glossary.get('finalise') or {})

    cand_dir = resolve(c.get('output_dir') or '')
    glossary_path = resolve(fin.get('output_json') or '')
    out_dir = resolve(inv.get('output_dir') or cand_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not glossary_path.exists():
        raise SystemExit(f'final glossary missing: {glossary_path}')

    project_field = fp.get('project_field') or ''
    if not project_field:
        raise SystemExit('glossary.fingerprint.project_field is required')

    cat_path = resolve(fp['catalogue_path']) if fp.get('catalogue_path') else None
    if not cat_path:
        raise SystemExit('glossary.fingerprint.catalogue_path is required '
                         '(catalogue is the canonical metadata source)')
    slug_col = fp.get('catalogue_slug_column') or ''
    slug_pattern = fp.get('catalogue_slug_pattern')
    if not slug_col:
        raise SystemExit('glossary.fingerprint.catalogue_slug_column is required')

    print(f"Loading slug→project from catalogue {cat_path.name} ...", flush=True)
    rows = load_doc_metadata_from_catalogue(
        cat_path, slug_col, slug_pattern,
        {'project': fp.get('catalogue_project_column') or project_field})
    doc_proj = {s: v['project'] for s, v in rows.items() if v.get('project')}
    print(f"  {len(doc_proj):,} slug→project mappings", flush=True)

    print(f"Loading glossary {glossary_path.name} ...", flush=True)
    g = json.load(open(glossary_path))
    entry_by_term = {e['term']: e for e in g['entries']}
    target_terms = set(entry_by_term)
    print(f"  {len(target_terms):,} target terms", flush=True)

    print("Building proj × term matrix ...", flush=True)
    proj_term, proj_doc_set = _build_proj_term_matrix(cand_dir, target_terms, doc_proj)
    print(f"  projects: {len(proj_term):,}", flush=True)

    corpus_label = cfg.prompt_tokens.get('corpus_full_name', cfg.domain.full_name)
    if args.view in ('project_vocab', 'both'):
        _project_vocab_view(proj_term, proj_doc_set, target_terms, entry_by_term,
                            inv, out_dir, corpus_label)
    if args.view in ('term_top_projects', 'both'):
        _term_top_projects_view(proj_term, proj_doc_set, target_terms, entry_by_term,
                                inv, out_dir, corpus_label)


if __name__ == '__main__':
    main()
