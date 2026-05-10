#!/usr/bin/env python3
"""Closure phase 6 (revised): rebuild events with globally-unique IDs across the FULL corpus.

The previous fix (script 10) operated on filter_input.jsonl — only the 25,479
records that pass the clustering filter. This was wrong scope: the underlying
event_id collision exists in the full ~90,000-record tagged corpus, and any
fix should address the full source-of-truth (the dedup output) rather than
just the clustering subset.

This script reads:
  1. corpora/arena/output/per_doc/doc_*.json — all records (90k+) with their
     kb_associated_project (canonical project name)
  2. runs/arena/fullcorpus_dedup/<slug>/*.assignments.json — per-project local
     event assignments (record_id → EVT-NNNN + event_name)

It then:
  - Assigns each project a stable 3-digit project_num (alphabetical order of
    canonical kb_associated_project name; project_num 0 for null/missing)
  - For each record, composes a globally-unique event_id:
        EVT-{project_num:03d}-{event_num:04d}
  - Records with no dedup assignment (singletons) get synthetic event_nums
    starting at 9000 within their project

Outputs:
  output/full_corpus_events.jsonl    — one row per record (90k) with new
                                        event_id, plus project, project_num,
                                        old event_id, event_name where present
  output/full_project_id_map.json    — canonical project name → project_num
  output/full_event_key_map.jsonl    — old → new event_id per record
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
PER_DOC = ROOT / 'corpora/arena/output/per_doc'
DEDUP_DIR = ROOT / 'runs/arena/fullcorpus_dedup'
OUT_DIR = Path(__file__).resolve().parents[2] / 'output'

OUT_FULL = OUT_DIR / 'full_corpus_events.jsonl'
OUT_PROJ = OUT_DIR / 'full_project_id_map.json'
OUT_MAP = OUT_DIR / 'full_event_key_map.jsonl'


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60]


def main():
    print("Loading per-doc records (full corpus)...", flush=True)
    records = {}  # record_id -> {project, doc_id, etc.}
    for f in sorted(PER_DOC.glob('doc_*.json')):
        d = json.load(open(f))
        for r in d.get('records', []):
            rid = r.get('id')
            if rid:
                records[rid] = {
                    'record_id': rid,
                    'project': r.get('kb_associated_project') or '',
                    'doc_id': r.get('doc_id') or '',
                }
    print(f"  {len(records):,} records loaded from per_doc", flush=True)

    print("Loading dedup assignments...", flush=True)
    rec_to_event = {}    # record_id -> (event_id, event_name, project_slug)
    n_files = 0
    for asn in DEDUP_DIR.rglob('*.assignments.json'):
        n_files += 1
        slug = asn.parent.name
        try:
            d = json.load(open(asn))
        except json.JSONDecodeError:
            continue
        for a in d.get('assignments', []):
            rid = a.get('record_id') or a.get('id')
            eid = a.get('event_id')
            if rid and eid:
                rec_to_event[rid] = {
                    'event_id_old': eid,
                    'event_name': a.get('event_name', ''),
                    'project_slug': slug,
                }
    print(f"  {n_files} assignment files; {len(rec_to_event):,} record→event assignments", flush=True)

    # Stable project numbering: alphabetical order of canonical project names
    project_names = sorted({r['project'] for r in records.values()} - {''})
    proj_to_num = {'': 0}
    for i, p in enumerate(project_names, start=1):
        proj_to_num[p] = i
    print(f"  {len(project_names)} unique canonical projects (project_num 1..{len(project_names)})", flush=True)

    # Slug → canonical name map (best-effort)
    slug_to_canonical = {slugify(p): p for p in project_names}

    # For each record, build the new global event_id
    project_singleton_counter = defaultdict(lambda: 9000)
    new_records = []
    map_rows = []
    n_assigned = 0
    n_singleton = 0
    for rid, rec in records.items():
        # Canonical project comes from per_doc kb_associated_project; if that's
        # missing, try to recover from the dedup slug (if record was in a
        # project's dedup output).
        proj_name = rec['project']
        ev = rec_to_event.get(rid)
        if not proj_name and ev:
            proj_name = slug_to_canonical.get(ev['project_slug'], '')
            if proj_name and proj_name not in proj_to_num:
                proj_to_num[proj_name] = max(proj_to_num.values()) + 1
        proj_num = proj_to_num.get(proj_name, 0)

        if ev:
            m = re.match(r'^EVT-(\d+)$', ev['event_id_old'])
            if m:
                event_num = int(m.group(1))
            else:
                event_num = project_singleton_counter[proj_name]
                project_singleton_counter[proj_name] += 1
            event_id_old = ev['event_id_old']
            event_name = ev['event_name']
            n_assigned += 1
        else:
            event_num = project_singleton_counter[proj_name]
            project_singleton_counter[proj_name] += 1
            event_id_old = ''  # never had one
            event_name = ''
            n_singleton += 1

        new_eid = f"EVT-{proj_num:03d}-{event_num:04d}"
        nr = {
            'record_id': rid,
            'doc_id': rec['doc_id'],
            'project': proj_name,
            'project_num': proj_num,
            'event_id_old': event_id_old,
            'event_id': new_eid,
            'event_name': event_name,
        }
        new_records.append(nr)
        map_rows.append({
            'record_id': rid,
            'project': proj_name,
            'project_num': proj_num,
            'event_id_old': event_id_old,
            'event_id_new': new_eid,
        })

    print(f"  records with dedup assignment: {n_assigned:,}", flush=True)
    print(f"  records as synthetic singletons: {n_singleton:,}", flush=True)

    print(f"\nWriting outputs...", flush=True)
    with open(OUT_FULL, 'w') as f:
        for r in new_records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"  {OUT_FULL}  ({len(new_records):,} rows)", flush=True)

    OUT_PROJ.write_text(json.dumps(proj_to_num, indent=2, ensure_ascii=False))
    print(f"  {OUT_PROJ}  ({len(proj_to_num)} entries)", flush=True)

    with open(OUT_MAP, 'w') as f:
        for r in map_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"  {OUT_MAP}", flush=True)

    # Sanity check: largest events under new keys
    from collections import Counter
    event_counts = Counter(r['event_id'] for r in new_records)
    print(f"\n  total distinct globally-unique event_ids: {len(event_counts):,}", flush=True)
    print(f"  largest events under new keys (now correctly per-project):", flush=True)
    for eid, n in event_counts.most_common(10):
        sample = next(r for r in new_records if r['event_id'] == eid)
        proj = sample.get('project','(no project)')[:50]
        nm = sample.get('event_name','')[:60]
        print(f"    {eid}: {n} records  in  {proj}", flush=True)
        if nm: print(f"      ↳ {nm}", flush=True)


if __name__ == "__main__":
    main()
