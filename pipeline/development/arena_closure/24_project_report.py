#!/usr/bin/env python3
"""Project-level synthesis report (analog of 07_cluster_report.py).

Given a project name (substring match against kb_associated_project), pulls
every record for that project, joins each to its cluster assignment, and asks
Opus 4.7 to synthesise a portfolio-grade report on the project's failure-mode
footprint — what mechanism families show up, how they interact, what the
project's lessons-learned imply for similar future projects.

Output:
  closure/output/project_reports/<slug>_report.md
  closure/output/project_reports/<slug>_report.html
  closure/output/project_reports/<slug>_meta.json

Cost: ~$0.30-1.00 depending on project size. Western Downs BESS (~136 records)
estimated ~$0.30.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import anthropic

MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
ASSIGN_LAYERS = [
    V2_OUT / 'sweep' / 'corpus_assignments.jsonl',
    V2_OUT / 'sweep' / 'reclassify' / 'reclassified_assignments.jsonl',
    V2_OUT / 'sweep' / 'third_pass' / 'third_pass_assignments.jsonl',
    V2_OUT / 'sweep' / 'residual' / 'residual_assignments.jsonl',
    V2_OUT / 'sweep' / 'convergence' / 'convergence_assignments.jsonl',
]
INPUT = V2_OUT / 'filter_input.jsonl'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/portfolio.csv')
PER_DOC_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')
PARENTS = CLOSURE_OUT / 'parents_v1.json'
ASSIGN_PARENTS = CLOSURE_OUT / 'cluster_to_parent_assignments.jsonl'
THEMES = CLOSURE_OUT / 'themes_and_parent_audit_v1.json'

REPORT_DIR = CLOSURE_OUT / 'project_reports'
REPORT_DIR.mkdir(exist_ok=True)


PROMPT_TEMPLATE = """You are writing a portfolio-review synthesis report for ARENA on a single project. Your audience is a senior portfolio manager who already understands ARENA's mandate. The report draws on the project's records as classified across the v2 mechanism-cluster taxonomy — the report's value is the cross-mechanism story of what bit this project, not a chronological account of milestones.

# PROJECT UNDER REVIEW

Project name: {project_name}

Project metadata (from ARENA's portfolio catalogue):
{project_meta_block}

Footprint in the v2 substrate:
- Records extracted: {n_records}
- Distinct mechanism clusters touched: {n_clusters}
- Parent-archetype families involved: {n_parents}
- Themes spanned: {n_themes}
- Source documents: {n_docs}
- Project-year range: {project_year_range}
- Publish-year range: {publish_year_range}
- Peer-tech reference class loaded: {n_peer_tech_records} records across {n_peer_tech_clusters} clusters (sibling projects sharing ≥1 of: {project_categories})

# EVIDENCE BASE

Below is the full evidence base. Four layers:

1. **Cluster-by-cluster footprint**: every cluster this project touches, ordered by record count, with the cluster's canonical name, mechanism signature, and parent-archetype it sits under. This shows you which mechanism families bit this project and how many distinct ways each manifested.

2. **Project records grouped by cluster**: each record under its assigned cluster, with project year, publish date, document type, source title, source URL, PDF URL. Records inside each cluster are oldest project-year first.

3. **Peer-tech records in the same clusters**: where other projects sharing this project's ARENA tech category have records in the same clusters, those peer records are listed below the project's own records (capped per cluster). These are the within-tech reference class — same mechanism family, same tech, different project. Use them to compare whether the project's manifestation is typical or atypical for the tech, and to surface lessons from sibling projects that the present project hit too.

4. **Project context**: the portfolio metadata (lead organisation, funding, location, status, summary) appears once at the top.

{evidence_block}

# TIME-VARIANT FACTORS — IMPORTANT

Mechanisms in this corpus are typically time-variant: their salience depends on the state of market, regulation, technology cost, deployment penetration, or counterparty maturity at the time the project was operating. Two date fields per record matter:
- **project year** = when the project was actually operating (dates the mechanism's *cause*)
- **publish date** = when ARENA released the document (dates the *interpretation*; often 1-5 years later)

Where claims are time-bound, name the period. Where the corpus only has older records, name that limitation.

# TASK

Write a synthesis report. Required elements:

1. **Opening framing**: one or two paragraphs on what this project is and why it sits where it does in the ARENA portfolio (scale, novelty, location, role). Include the temporal range of evidence and what stage of the project the records cover.

2. **The mechanism-family map**: for each parent-archetype represented by ≥2 clusters or ≥3 records in this project's footprint, articulate the mechanism in plain language and how it specifically manifested *for this project*. Use the clusters under each parent to give concrete substance — don't just name the parent; name the sub-mechanisms.

3. **Within-tech reference class**: for each major cluster, compare the project's manifestation to the peer-tech records (other projects in the same ARENA category that landed in the same cluster). Where the manifestation is *typical* for the tech, name that. Where the project diverged from the peer pattern (earlier, later, more severe, or in a tech-specific variant), name that too. This is a key value-add of the v2 substrate: the same cluster pulls together every project where the mechanism showed up, regardless of project, so the within-tech reference class is empirical rather than asserted.

4. **Cross-cutting observations**: where two or more parent-families interact. E.g. regulatory novelty + commissioning surprises often compound; harmonic distortion + grid-forming inverter ambiguity tend to surface together. The point of having structured clusters is to make these intersections visible.

5. **Time trajectory**: how do the records evolve across project years? Are early-stage findings refined or modified by later records? Did the project surface mechanisms that *resolved* (fixes worked) vs ones that *persisted* (still flagged in later docs)?

6. **What this project's evidence implies for analogous future projects**: be specific. The project is a worked instance of a class — what would a portfolio manager do differently knowing how *this* project unfolded? Where the project's lessons depend on time-bound conditions (e.g. NER state at the time, AEMO commissioning workflow, regulatory interpretation), name those dependencies.

7. **Open questions / evidence gaps**: what does the corpus *not* tell you about this project? What would sharpen the picture?

Style:
- Report-style prose. Bullets only when they help.
- Do NOT quote source text — synthesise.
- For every specific claim, cite using **HTML superscript tags**: `<sup>1</sup>`, `<sup>2,7</sup>`, etc. Numbering rules: number references by order of first appearance in the body; reuse the same number for repeat citations of the same record.
- Length: 1500-3000 words for the body, plus references.

# CITATION FORMAT

Same format as cluster reports. Body uses `<sup>N</sup>`. Cluster IDs appear inline as `[c###]` for context (not citations). Project-stage labels and document titles in body are unadorned.

End with `## References` listing every cited record in numeric order, one per line:

```
1. **ARENA-DLV-NNNN-NN** — *Document Title* (DocumentType, project year YYYY, published DD/MM/YYYY, p. N). [Source page](URL) · [PDF](URL)
```

Skip any field missing in metadata; do not invent values. Every cited record (anything with a `<sup>` in body) MUST appear in references.

Return only the report Markdown — no preamble.
"""


DOC_META_FIELDS = (
    'kb_publish_date', 'kb_year', 'kb_document_type',
    'source_title', 'source_url', 'pages', 'pdf_url', 'doc_id',
)


def _load_doc_metadata():
    doc_meta = {}
    for f in sorted(PER_DOC_DIR.glob('doc_*.json')):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for rec in d.get('records', []):
            rid = rec.get('id')
            if not rid: continue
            doc_meta[rid] = {k: rec.get(k) for k in DOC_META_FIELDS}
            doc_meta[rid]['kb_associated_project'] = rec.get('kb_associated_project','') or ''
            doc_meta[rid]['kb_category'] = rec.get('kb_category','') or ''
    return doc_meta


def load_data():
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_meta = {r['Project']: r for r in csv_rows}
    rid_to_cluster = {}
    for f in ASSIGN_LAYERS:
        if not f.exists(): continue
        for line in open(f):
            a = json.loads(line)
            rid_to_cluster[a['record_id']] = a.get('cluster_id')
    parents = {p['parent_id']: p for p in json.load(open(PARENTS))['parents']}
    cluster_to_parent = {}
    for line in open(ASSIGN_PARENTS):
        a = json.loads(line)
        cluster_to_parent[a['cluster_id']] = a['parent_id']
    themes_data = json.load(open(THEMES)) if THEMES.exists() else {}
    parent_to_theme = {}
    for t in themes_data.get('themes', []):
        for pid in t.get('parent_ids', []):
            parent_to_theme[pid] = {'theme_id': t.get('theme_id'), 'name': t.get('name')}
    doc_meta = _load_doc_metadata()
    return {
        'catalogue': cid_to_meta,
        'records': rid_to,
        'projects': proj_meta,
        'rid_to_cluster': rid_to_cluster,
        'parents': parents,
        'cluster_to_parent': cluster_to_parent,
        'parent_to_theme': parent_to_theme,
        'doc_meta': doc_meta,
    }


def _publish_year(date_str):
    if not date_str: return None
    parts = str(date_str).strip().split('/')
    if len(parts) == 3:
        try: return int(parts[2])
        except ValueError: return None
    return None


def _format_doc_metadata(meta):
    if not meta: return ""
    parts = []
    py = meta.get('kb_year')
    pd = meta.get('kb_publish_date')
    if py: parts.append(f"project year {py}")
    if pd: parts.append(f"published {pd}")
    dt = meta.get('kb_document_type')
    if dt: parts.append(dt)
    pages = meta.get('pages')
    if pages and isinstance(pages, list) and pages:
        parts.append(f"p. {','.join(str(p) for p in pages[:3])}")
    return " · ".join(parts)


def find_project(query, data):
    """Resolve a project query (substring, case-insensitive) to a canonical name."""
    q = query.lower()
    matches = [p for p in data['projects'] if q in p.lower()]
    # Also check kb_associated_project from records (sometimes differs from portfolio CSV)
    record_projs = {(m.get('kb_associated_project') or '').strip()
                    for m in data['doc_meta'].values()}
    record_projs.discard('')
    matches += [p for p in record_projs if q in p.lower() and p not in matches]
    matches = list(dict.fromkeys(matches))  # dedup, preserve order
    if not matches:
        raise SystemExit(f"No project matches '{query}'")
    if len(matches) > 1:
        # Pick the one with the most records
        record_counts = defaultdict(int)
        for m in data['doc_meta'].values():
            p = (m.get('kb_associated_project') or '').strip()
            if p: record_counts[p] += 1
        matches.sort(key=lambda p: -record_counts.get(p, 0))
        print(f"  Multiple matches ({len(matches)}); picking '{matches[0]}' "
              f"({record_counts.get(matches[0],0)} records)", flush=True)
    return matches[0]


def _base_categories(cat_str):
    """Split kb_category 'Battery storage, System security and reliability' into base set."""
    if not cat_str: return set()
    return {c.strip() for c in cat_str.split(',') if c.strip()}


def build_evidence_block(project_name, data, peer_tech=True, max_peer_per_cluster=8):
    # Find every record for this project
    proj_records = []
    for rid, m in data['doc_meta'].items():
        if (m.get('kb_associated_project') or '').strip() == project_name:
            proj_records.append(rid)

    if not proj_records:
        raise SystemExit(f"No records found for project '{project_name}'")

    # Group by cluster (None / unclustered handled separately)
    by_cluster = defaultdict(list)
    for rid in proj_records:
        cid = data['rid_to_cluster'].get(rid)
        by_cluster[cid].append(rid)

    # === Peer-tech reference class ===
    # Project's own ARENA categories (record-level): the union of base categories
    # across the project's records. A peer-tech record is one in the same cluster
    # with ≥1 base-category overlap with the project, and from a different project.
    proj_cats = set()
    for rid in proj_records:
        proj_cats |= _base_categories(data['doc_meta'].get(rid, {}).get('kb_category', ''))

    # Build cluster→peer-records map
    peer_records_by_cluster = defaultdict(list)
    if peer_tech and proj_cats:
        proj_record_set = set(proj_records)
        for rid, dm in data['doc_meta'].items():
            if rid in proj_record_set:
                continue
            cid = data['rid_to_cluster'].get(rid)
            if cid not in by_cluster:  # only clusters this project touches
                continue
            other_proj = (dm.get('kb_associated_project') or '').strip()
            if other_proj == project_name:
                continue
            other_cats = _base_categories(dm.get('kb_category', ''))
            if proj_cats & other_cats:
                peer_records_by_cluster[cid].append(rid)
        # Sort each cluster's peer set: oldest project-year first, then cap
        for cid in list(peer_records_by_cluster):
            peer_records_by_cluster[cid].sort(key=lambda rid: (
                int(data['doc_meta'].get(rid, {}).get('kb_year') or 0)
                if str(data['doc_meta'].get(rid, {}).get('kb_year') or '').isdigit()
                else 9999
            ))
            peer_records_by_cluster[cid] = peer_records_by_cluster[cid][:max_peer_per_cluster]
    n_peer_total = sum(len(v) for v in peer_records_by_cluster.values())

    # Compute parent + theme footprint
    clusters_touched = [c for c in by_cluster if c]
    parents_touched = set(data['cluster_to_parent'].get(c) for c in clusters_touched
                          if data['cluster_to_parent'].get(c))
    themes_touched = set()
    for pid in parents_touched:
        t = data['parent_to_theme'].get(pid)
        if t: themes_touched.add(t['theme_id'])

    # Project metadata
    pmeta = data['projects'].get(project_name, {})

    # Temporal range
    pys, pbys = [], []
    for rid in proj_records:
        m = data['doc_meta'].get(rid, {})
        py = m.get('kb_year')
        pby = _publish_year(m.get('kb_publish_date'))
        try:
            if py: pys.append(int(py))
        except (ValueError, TypeError): pass
        if pby: pbys.append(pby)

    docs = {data['doc_meta'].get(rid,{}).get('doc_id') for rid in proj_records}
    docs.discard(None)

    py_range = f"{min(pys)}–{max(pys)}" if pys else "(no project years tagged)"
    pby_range = f"{min(pbys)}–{max(pbys)}" if pbys else "(no publish dates tagged)"

    project_meta_block_lines = []
    if pmeta:
        for k in ['Category','Lead organisation','Arena program','Status',
                  'Start date','Location','Arena funding provided','Total project value']:
            v = (pmeta.get(k) or '').strip()
            if v: project_meta_block_lines.append(f"  {k}: {v}")
        summary = (pmeta.get('Summary/Information') or '').strip()
        if summary:
            project_meta_block_lines.append(f"  Summary: {summary[:1500]}")
    if not project_meta_block_lines:
        project_meta_block_lines.append("  (No portfolio-CSV metadata found for this project name)")
    project_meta_block = '\n'.join(project_meta_block_lines)

    lines = []
    # === CLUSTER FOOTPRINT SUMMARY ===
    lines.append("\n## Cluster footprint of this project (largest first)\n")
    cluster_order = sorted(clusters_touched, key=lambda c: -len(by_cluster[c]))
    for cid in cluster_order:
        cmeta = data['catalogue'].get(cid, {})
        nm = cmeta.get('canonical_name','(no name)')
        sig = (cmeta.get('mechanism_signature','') or '')[:300]
        pid = data['cluster_to_parent'].get(cid, '?')
        pname = data['parents'].get(pid, {}).get('name','?')
        n = len(by_cluster[cid])
        lines.append(f"- **[{cid}]** ({n} records) — {nm}")
        lines.append(f"  parent: [{pid}] {pname}")
        lines.append(f"  mechanism: {sig}")

    if None in by_cluster:
        n_unclust = len(by_cluster[None])
        lines.append(f"\n- **(unclustered)** ({n_unclust} records) — singletons / final-pass residuals")

    # === RECORDS BY CLUSTER ===
    lines.append("\n## Records grouped by cluster (oldest project-year first within each cluster)\n")
    for cid in cluster_order + ([None] if None in by_cluster else []):
        cmeta = data['catalogue'].get(cid, {}) if cid else {}
        nm = cmeta.get('canonical_name','(unclustered)') if cid else '(unclustered residuals)'
        pid = data['cluster_to_parent'].get(cid, '?') if cid else '—'
        cluster_label = f"[{cid}] {nm}" if cid else nm
        lines.append(f"\n### Cluster {cluster_label} (parent: {pid})")
        recs_sorted = sorted(by_cluster[cid], key=lambda rid: (
            int(data['doc_meta'].get(rid, {}).get('kb_year') or 0)
            if str(data['doc_meta'].get(rid, {}).get('kb_year') or '').isdigit()
            else 9999
        ))
        lines.append(f"\n#### This project's records ({len(recs_sorted)}):")
        for rid in recs_sorted:
            r = data['records'].get(rid)
            if not r:
                continue
            narr = (r.get('narrative') or '').strip()
            evi = (r.get('evidence') or '').strip()
            evi_short = evi[:250] if evi and evi != narr else ''
            doc_meta_r = data['doc_meta'].get(rid, {})
            timing_line = _format_doc_metadata(doc_meta_r)
            source_title = (doc_meta_r.get('source_title') or '').strip()
            source_url = (doc_meta_r.get('source_url') or '').strip()
            pdf_url = (doc_meta_r.get('pdf_url') or '').strip()
            lines.append(f"\n- [{rid}]" + (f"  ({timing_line})" if timing_line else ""))
            if source_title:
                lines.append(f"  source_title: {source_title[:160]}")
            if source_url:
                lines.append(f"  source_url:   {source_url}")
            if pdf_url:
                lines.append(f"  pdf_url:      {pdf_url}")
            lines.append(f"  narrative: {narr[:600]}")
            if evi_short:
                lines.append(f"  evidence: {evi_short}")

        # Peer-tech records in this cluster
        peer_rids = peer_records_by_cluster.get(cid, []) if cid else []
        if peer_rids:
            lines.append(f"\n#### Peer-tech records in [{cid}] ({len(peer_rids)} from sibling projects sharing ≥1 base ARENA category):")
            for rid in peer_rids:
                r = data['records'].get(rid)
                if not r:
                    continue
                dm = data['doc_meta'].get(rid, {})
                narr = (r.get('narrative') or '').strip()
                proj_p = (dm.get('kb_associated_project') or '').strip() or '(no project tag)'
                cat_p = (dm.get('kb_category') or '').strip()
                timing_line = _format_doc_metadata(dm)
                source_title = (dm.get('source_title') or '').strip()
                lines.append(f"\n- [{rid}]  project: {proj_p}"
                             + (f"  ({timing_line})" if timing_line else ""))
                if cat_p:
                    lines.append(f"  category: {cat_p}")
                if source_title:
                    lines.append(f"  source_title: {source_title[:160]}")
                lines.append(f"  narrative: {narr[:500]}")

    return '\n'.join(lines), {
        'n_records': len(proj_records),
        'n_clusters': len(clusters_touched),
        'n_parents': len(parents_touched),
        'n_themes': len(themes_touched),
        'n_docs': len(docs),
        'n_peer_tech_records': n_peer_total,
        'n_peer_tech_clusters': sum(1 for v in peer_records_by_cluster.values() if v),
        'project_categories': sorted(proj_cats),
        'project_year_range': py_range,
        'publish_year_range': pby_range,
        'project_meta_block': project_meta_block,
    }


def slugify(s):
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()
    return s[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True, help='project name (substring, case-insensitive)')
    ap.add_argument('--model', default='claude-sonnet-4-6')
    ap.add_argument('--max-tokens', type=int, default=128000)
    ap.add_argument('--no-peer-tech', action='store_true',
                    help='disable peer-tech reference-class block (default on)')
    ap.add_argument('--max-peer-per-cluster', type=int, default=8,
                    help='cap peer-tech records included per cluster (default 8)')
    args = ap.parse_args()

    print("Loading data...", flush=True)
    data = load_data()
    project_name = find_project(args.project, data)
    print(f"  resolved project: {project_name}", flush=True)

    print("\nBuilding evidence block...", flush=True)
    evidence_block, stats = build_evidence_block(
        project_name, data,
        peer_tech=not args.no_peer_tech,
        max_peer_per_cluster=args.max_peer_per_cluster,
    )
    print(f"  records: {stats['n_records']}, clusters: {stats['n_clusters']}, "
          f"parents: {stats['n_parents']}, themes: {stats['n_themes']}, "
          f"docs: {stats['n_docs']}", flush=True)
    print(f"  project categories: {stats['project_categories']}", flush=True)
    print(f"  peer-tech: {stats['n_peer_tech_records']} records across "
          f"{stats['n_peer_tech_clusters']} clusters", flush=True)
    print(f"  project years: {stats['project_year_range']}, publish: {stats['publish_year_range']}", flush=True)
    print(f"  evidence block: {len(evidence_block):,} chars", flush=True)

    prompt = PROMPT_TEMPLATE.format(
        project_name=project_name,
        project_meta_block=stats['project_meta_block'],
        n_records=stats['n_records'],
        n_clusters=stats['n_clusters'],
        n_parents=stats['n_parents'],
        n_themes=stats['n_themes'],
        n_docs=stats['n_docs'],
        n_peer_tech_records=stats['n_peer_tech_records'],
        n_peer_tech_clusters=stats['n_peer_tech_clusters'],
        project_categories=', '.join(stats['project_categories']) or '(none)',
        project_year_range=stats['project_year_range'],
        publish_year_range=stats['publish_year_range'],
        evidence_block=evidence_block,
    )
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model}...", flush=True)
    started = time.time()
    parts = []
    last_print = 0; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=args.model, max_tokens=args.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                      flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    text = ''.join(parts)
    wall = time.time() - started
    in_p = 5 if 'opus' in args.model else 3
    out_p = 25 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  cost ${cost:.3f}", flush=True)

    slug = slugify(project_name)
    out = REPORT_DIR / f'{slug}_report.md'
    out.write_text(text)

    html_out = REPORT_DIR / f'{slug}_report.html'
    title = f"ARENA — {project_name}"
    eyebrow = f"Broad Learnings · ARENA project synthesis"
    try:
        proc = subprocess.run(
            [sys.executable, str(MD2HTML), title, eyebrow],
            input=text, capture_output=True, text=True, check=True,
        )
        html_out.write_text(proc.stdout)
        print(f"  wrote {html_out}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"  md2html failed (non-fatal): {e.stderr.strip()}", flush=True)

    meta_out = REPORT_DIR / f'{slug}_meta.json'
    meta_out.write_text(json.dumps({
        'project': project_name,
        'records': stats['n_records'],
        'clusters': stats['n_clusters'],
        'parents': stats['n_parents'],
        'themes': stats['n_themes'],
        'docs': stats['n_docs'],
        'project_categories': stats['project_categories'],
        'peer_tech_records': stats['n_peer_tech_records'],
        'peer_tech_clusters': stats['n_peer_tech_clusters'],
        'peer_tech_enabled': not args.no_peer_tech,
        'max_peer_per_cluster': args.max_peer_per_cluster,
        'project_year_range': stats['project_year_range'],
        'publish_year_range': stats['publish_year_range'],
        'evidence_chars': len(evidence_block),
        'prompt_chars': len(prompt),
        'output_chars': len(text),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'model': args.model,
    }, indent=2))
    print(f"\n  wrote {out}", flush=True)


if __name__ == "__main__":
    main()
