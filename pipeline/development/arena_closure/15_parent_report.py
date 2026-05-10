#!/usr/bin/env python3
"""Closure phase: parent-archetype synthesis report.

One Opus 4.7 call that synthesises across every cluster assigned to a
given parent archetype. Mirrors 07_cluster_report.py but operates one
rung up: cluster-as-instance rather than record-as-instance.

For each constituent cluster of the parent, the evidence block carries:
- Cluster name + mechanism signature
- Every supporting record (narrative + source title + URLs + dates +
  document type), grouped by project and sorted oldest-first
- Project metadata
- Event siblings *outside* the parent (records sharing an event with
  the parent's records but assigned to a different parent — useful
  context for cross-mechanism interactions)

Output:
  closure/output/parent_reports/<parent_id>_report.md
  closure/output/parent_reports/<parent_id>_report.html (via tools/md2html)
  closure/output/parent_reports/<parent_id>_meta.json

Cost: ~$2-3 for a typical 15-30 cluster parent. Larger parents (>40
clusters) may run $4-6.
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

ROOT = Path(__file__).resolve().parents[2]  # corpora/arena/clustering_v2
V2_OUT = ROOT / 'output'
CLOSURE_OUT = ROOT / 'closure/output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
# Assignment layers in chronological order — later passes override earlier ones
# for a given record_id. Mirrors tools/q's ASSIGN_LAYERS. Earlier code only
# loaded the first layer, leaving ~35% of records out of parent reports.
ASSIGN_LAYERS = [
    V2_OUT / 'sweep' / 'corpus_assignments.jsonl',
    V2_OUT / 'sweep' / 'reclassify' / 'reclassified_assignments.jsonl',
    V2_OUT / 'sweep' / 'third_pass' / 'third_pass_assignments.jsonl',
    V2_OUT / 'sweep' / 'residual' / 'residual_assignments.jsonl',
    V2_OUT / 'sweep' / 'convergence' / 'convergence_assignments.jsonl',
]
INPUT = V2_OUT / 'filter_input.jsonl'
PARENTS_FILE = CLOSURE_OUT / 'parents_v1.json'
PARENT_ASSIGNS = CLOSURE_OUT / 'cluster_to_parent_assignments.jsonl'
THEMES_FILE = CLOSURE_OUT / 'themes_and_parent_audit_v1.json'
PROMPT_FILE = ROOT / 'closure/prompts/15_parent_report.md'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/portfolio.csv')
PER_DOC_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/output/per_doc')
MD2HTML = Path('/home/jeffzda/broadlearnings/tools/md2html')

REPORT_DIR = CLOSURE_OUT / 'parent_reports'
REPORT_DIR.mkdir(exist_ok=True)


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
            if not rid:
                continue
            doc_meta[rid] = {k: rec.get(k) for k in DOC_META_FIELDS}
    return doc_meta


def load_data():
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_meta = {r['Project']: r for r in csv_rows}
    # Load all assignment layers; later layers override earlier ones for a given record_id.
    rid_to_cluster = {}
    for f in ASSIGN_LAYERS:
        if not f.exists():
            continue
        for line in open(f):
            a = json.loads(line)
            rid_to_cluster[a['record_id']] = a.get('cluster_id')
    cluster_members = defaultdict(list)
    for rid, cid in rid_to_cluster.items():
        if cid:
            cluster_members[cid].append(rid)
    event_records = defaultdict(list)
    for r in rows:
        eid = r.get('event_id')
        proj = r.get('project') or ''
        if eid:
            event_records[(proj, eid)].append(r['record_id'])
    doc_meta = _load_doc_metadata()
    parents = {p['parent_id']: p for p in json.load(open(PARENTS_FILE))['parents']}
    parent_to_clusters = defaultdict(list)
    for line in open(PARENT_ASSIGNS):
        a = json.loads(line)
        pid = a.get('parent_id')
        if pid and pid != 'none':
            parent_to_clusters[pid].append(a['cluster_id'])
    themes_data = json.load(open(THEMES_FILE))
    parent_to_theme = {pid: t for t in themes_data['themes'] for pid in t.get('parent_ids', [])}
    cluster_to_parent = {a.get('cluster_id'): a.get('parent_id')
                          for a in (json.loads(l) for l in open(PARENT_ASSIGNS))}
    return {
        'catalogue': cid_to_meta,
        'records': rid_to,
        'projects': proj_meta,
        'rid_to_cluster': rid_to_cluster,
        'cluster_members': dict(cluster_members),
        'event_records': dict(event_records),
        'doc_meta': doc_meta,
        'parents': parents,
        'parent_to_clusters': dict(parent_to_clusters),
        'parent_to_theme': parent_to_theme,
        'cluster_to_parent': cluster_to_parent,
    }


def _publish_year(date_str):
    if not date_str:
        return None
    parts = str(date_str).strip().split('/')
    if len(parts) == 3:
        try:
            return int(parts[2])
        except ValueError:
            return None
    return None


def _format_doc_metadata(meta):
    if not meta:
        return ""
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


def build_evidence_block(parent_id, data, max_event_siblings_per_record=2):
    """Synthesis-grade evidence block for a parent: every cluster, every record, project metadata, event siblings outside the parent."""
    cluster_ids = data['parent_to_clusters'].get(parent_id, [])
    if not cluster_ids:
        raise ValueError(f"Parent {parent_id} has no clusters assigned")

    parent_cluster_set = set(cluster_ids)

    # Aggregate stats
    all_record_ids = []
    project_set = set()
    project_years_all = []
    publish_years_all = []
    for cid in cluster_ids:
        cluster_record_ids = data['cluster_members'].get(cid, [])
        all_record_ids.extend(cluster_record_ids)
        for rid in cluster_record_ids:
            r = data['records'].get(rid)
            if not r: continue
            proj = r.get('project') or ''
            if proj: project_set.add(proj)
            m = data['doc_meta'].get(rid, {})
            py = m.get('kb_year')
            pby = _publish_year(m.get('kb_publish_date'))
            try:
                if py: project_years_all.append(int(py))
            except (ValueError, TypeError):
                pass
            if pby: publish_years_all.append(pby)

    cat_set = set()
    for proj in project_set:
        c = data['projects'].get(proj, {}).get('Category', '')
        if c: cat_set.add(c)

    lines = []

    # === Top-level temporal range ===
    lines.append("\n## Temporal range across all records in this parent\n")
    if project_years_all:
        lines.append(f"Project years span {min(project_years_all)}–{max(project_years_all)} "
                     f"(n={len(project_years_all)} records have a project year tag)")
    if publish_years_all:
        lines.append(f"Publish years span {min(publish_years_all)}–{max(publish_years_all)} "
                     f"(n={len(publish_years_all)} records have a publish date)")
    lines.append("\nProject year = when the project was operating (market conditions, regulatory state, costs at that time). "
                 "Publish year = when ARENA released the document (often 1–5 years later, reflecting more current understanding). "
                 "Both matter; weight evidence accordingly when making claims about current vs historical state.")

    # === Constituent clusters, larger first for prominence ===
    lines.append(f"\n## Constituent clusters of parent {parent_id}\n")
    cluster_order = sorted(cluster_ids,
                            key=lambda c: -len(data['cluster_members'].get(c, [])))
    for cid in cluster_order:
        cluster = data['catalogue'].get(cid)
        if not cluster:
            continue
        cluster_record_ids = data['cluster_members'].get(cid, [])
        cluster_records = [data['records'][r] for r in cluster_record_ids
                           if r in data['records']]
        if not cluster_records: continue

        lines.append(f"\n### [{cid}] {cluster.get('canonical_name', '')}")
        lines.append(f"Mechanism signature: {cluster.get('mechanism_signature', '')}")
        lines.append(f"Records in cluster: {len(cluster_records)}")

        # Group cluster's records by project
        by_project = defaultdict(list)
        for r in cluster_records:
            by_project[r.get('project') or '(no project)'].append(r)

        for proj in sorted(by_project, key=lambda p: -len(by_project[p])):
            recs = by_project[proj]
            meta = data['projects'].get(proj, {})
            lines.append(f"\n#### Project: {proj}")
            if meta:
                mlines = []
                for k in ['Category','Lead organisation','Arena program','Status',
                          'Start date','Location','Arena funding provided','Total project value']:
                    v = (meta.get(k) or '').strip()
                    if v: mlines.append(f"{k}: {v}")
                if mlines:
                    lines.append("  " + " | ".join(mlines))
                summary = (meta.get('Summary/Information') or '').strip()
                if summary:
                    lines.append(f"  Summary: {summary[:800]}")
            recs_sorted = sorted(recs, key=lambda r: (
                int(data['doc_meta'].get(r['record_id'], {}).get('kb_year') or 0)
                if str(data['doc_meta'].get(r['record_id'], {}).get('kb_year') or '').isdigit()
                else 9999
            ))
            for r in recs_sorted:
                rid = r['record_id']
                narr = (r.get('narrative') or '').strip()
                evi = (r.get('evidence') or '').strip()
                evi_short = evi[:220] if evi and evi != narr else ''
                m = data['doc_meta'].get(rid, {})
                timing_line = _format_doc_metadata(m)
                source_title = (m.get('source_title') or '').strip()
                source_url = (m.get('source_url') or '').strip()
                pdf_url = (m.get('pdf_url') or '').strip()
                lines.append(f"\n  - [{rid}]" + (f"  ({timing_line})" if timing_line else ""))
                if source_title:
                    lines.append(f"    source_title: {source_title[:160]}")
                if source_url:
                    lines.append(f"    source_url:   {source_url}")
                if pdf_url:
                    lines.append(f"    pdf_url:      {pdf_url}")
                lines.append(f"    narrative: {narr[:600]}")
                if evi_short:
                    lines.append(f"    evidence: {evi_short}")

    # === Event siblings OUTSIDE this parent ===
    sibling_section = [f"\n## Event siblings outside parent {parent_id} (records sharing an event with parent records but assigned to other parents)\n"]
    sibling_count = 0
    seen_siblings = set()
    parent_record_set = set(all_record_ids)
    for rid in all_record_ids:
        r = data['records'].get(rid)
        if not r: continue
        eid = r.get('event_id')
        proj = r.get('project') or ''
        if not eid: continue
        key = (proj, eid)
        sibling_rids = [s for s in data['event_records'].get(key, [])
                        if s != rid and s not in parent_record_set
                        and s not in seen_siblings]
        if not sibling_rids: continue
        sibling_section.append(f"\n### Event {eid} in project '{proj}' (seed record from parent: {rid})")
        for srid in sibling_rids[:max_event_siblings_per_record]:
            s = data['records'].get(srid)
            if not s: continue
            seen_siblings.add(srid)
            other_cluster = data['rid_to_cluster'].get(srid, 'unassigned')
            other_parent = data['cluster_to_parent'].get(other_cluster, 'unassigned')
            other_cluster_name = (data['catalogue'].get(other_cluster, {}) or {}).get('canonical_name', '')
            other_parent_name = ''
            if other_parent in data['parents']:
                other_parent_name = data['parents'][other_parent].get('name', '')
            sib_meta = data['doc_meta'].get(srid, {})
            sib_timing = _format_doc_metadata(sib_meta)
            sib_title = (sib_meta.get('source_title') or '').strip()
            sib_url = (sib_meta.get('source_url') or '').strip()
            sib_pdf = (sib_meta.get('pdf_url') or '').strip()
            sibling_section.append(
                f"\n  - [{srid}] (cluster: {other_cluster}"
                + (f" — {other_cluster_name}" if other_cluster_name else "")
                + (f"; parent: {other_parent}"
                   + (f" — {other_parent_name}" if other_parent_name else ""))
                + (f"; {sib_timing}" if sib_timing else "")
                + ")"
            )
            if sib_title:
                sibling_section.append(f"    source_title: {sib_title[:160]}")
            if sib_url:
                sibling_section.append(f"    source_url:   {sib_url}")
            if sib_pdf:
                sibling_section.append(f"    pdf_url:      {sib_pdf}")
            sibling_section.append(f"    narrative: {(s.get('narrative') or '').strip()[:400]}")
            sibling_count += 1

    if sibling_count > 0:
        lines.extend(sibling_section)
        lines.append(f"\n(Total event siblings outside parent: {sibling_count})")

    return '\n'.join(lines), {
        'n_clusters': len(cluster_ids),
        'n_records': len(all_record_ids),
        'n_projects': len(project_set),
        'n_categories': len(cat_set),
        'n_event_siblings': sibling_count,
        'project_year_range': (min(project_years_all), max(project_years_all)) if project_years_all else None,
        'publish_year_range': (min(publish_years_all), max(publish_years_all)) if publish_years_all else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parent', required=True, help='parent_id (e.g. p18)')
    ap.add_argument('--model', default='claude-sonnet-4-6')
    ap.add_argument('--max-tokens', type=int, default=128000)
    args = ap.parse_args()

    print("Loading data...", flush=True)
    data = load_data()
    if args.parent not in data['parents']:
        raise SystemExit(f"Parent {args.parent} not in parents_v1.json")
    parent = data['parents'][args.parent]
    theme = data['parent_to_theme'].get(args.parent, {})
    print(f"  parent: [{args.parent}] {parent['name']}", flush=True)
    print(f"  theme: [{theme.get('theme_id', '?')}] {theme.get('name', '?')}", flush=True)

    print("\nBuilding evidence block...", flush=True)
    evidence_block, stats = build_evidence_block(args.parent, data)
    print(f"  clusters: {stats['n_clusters']}  records: {stats['n_records']}  "
          f"projects: {stats['n_projects']}  categories: {stats['n_categories']}", flush=True)
    print(f"  event siblings: {stats['n_event_siblings']}", flush=True)
    if stats['project_year_range']:
        print(f"  project year range: {stats['project_year_range'][0]}–{stats['project_year_range'][1]}", flush=True)
    if stats['publish_year_range']:
        print(f"  publish year range: {stats['publish_year_range'][0]}–{stats['publish_year_range'][1]}", flush=True)
    print(f"  evidence block: {len(evidence_block):,} chars", flush=True)

    prompt_template = PROMPT_FILE.read_text()
    prompt = (prompt_template
              .replace('{parent_id}', args.parent)
              .replace('{parent_name}', parent['name'])
              .replace('{parent_criterion}', parent.get('mechanism_criterion', ''))
              .replace('{parent_description}', parent.get('description', ''))
              .replace('{theme_name}', theme.get('name', '?'))
              .replace('{n_clusters}', str(stats['n_clusters']))
              .replace('{n_records}', str(stats['n_records']))
              .replace('{n_projects}', str(stats['n_projects']))
              .replace('{n_categories}', str(stats['n_categories']))
              .replace('{evidence_block}', evidence_block))
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model} (max_tokens={args.max_tokens:,})...", flush=True)
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
    # Opus 4.7 (1M context, claude-opus-4-7): $5/M input, $25/M output.
    # Sonnet 4.6: $3/M input, $15/M output.
    in_p = 5 if 'opus' in args.model else 3
    out_p = 25 if 'opus' in args.model else 15
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out  "
          f"stop={msg.stop_reason}  cost ${cost:.3f}", flush=True)
    if msg.stop_reason != 'end_turn':
        print(f"  ! Stop reason was {msg.stop_reason!r} — output may be truncated", flush=True)

    out = REPORT_DIR / f'{args.parent}_report.md'
    out.write_text(text)
    print(f"\n  wrote {out}", flush=True)

    # Render styled HTML sibling
    html_out = REPORT_DIR / f'{args.parent}_report.html'
    title = f"ARENA {args.parent} — {parent['name']}"
    eyebrow = f"Broad Learnings · ARENA parent archetype synthesis · {args.parent}"
    try:
        proc = subprocess.run(
            [sys.executable, str(MD2HTML), title, eyebrow],
            input=text, capture_output=True, text=True, check=True,
        )
        html_out.write_text(proc.stdout)
        print(f"  wrote {html_out}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"  md2html failed (non-fatal): {e.stderr.strip()}", flush=True)

    meta = REPORT_DIR / f'{args.parent}_meta.json'
    meta.write_text(json.dumps({
        'parent_id': args.parent,
        'parent_name': parent['name'],
        'theme': theme.get('name', '?'),
        'n_clusters': stats['n_clusters'],
        'n_records': stats['n_records'],
        'n_projects': stats['n_projects'],
        'n_categories': stats['n_categories'],
        'n_event_siblings': stats['n_event_siblings'],
        'project_year_range': stats['project_year_range'],
        'publish_year_range': stats['publish_year_range'],
        'evidence_chars': len(evidence_block),
        'prompt_chars': len(prompt),
        'output_chars': len(text),
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'model': args.model,
    }, indent=2))
    print(f"  wrote {meta}", flush=True)


if __name__ == "__main__":
    main()
