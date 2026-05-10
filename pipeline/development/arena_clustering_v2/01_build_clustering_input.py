#!/usr/bin/env python3
"""Phase 1: materialise the v2 clustering input.

Joins three sources into one JSONL with one row per record:
- corpora/arena/output/per_doc/doc_*.json — narratives + evidence
- corpora/arena/output/record_type_tags/opus-4-6-v3-temp0/tags.json — 6-axis tags
- runs/arena/fullcorpus_dedup/<project_slug>/{doc_id}.assignments.json — event_id

Applies the looser clustering filter (no spec gate):
  valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes')

Output:
- output/filter_input.jsonl — one record per line with all fields needed downstream
- output/filter_summary.json — diagnostic counts
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)

TAGS_PATH = ROOT / 'corpora/arena/output/record_type_tags/opus-4-6-v3-temp0/tags.json'
PER_DOC = ROOT / 'corpora/arena/output/per_doc'
DEDUP_DIR = ROOT / 'runs/arena/fullcorpus_dedup'

OUT_JSONL = OUT_DIR / 'filter_input.jsonl'
OUT_SUMMARY = OUT_DIR / 'filter_summary.json'


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60]


def matches_filter(tag):
    return (tag.get('valence') == 'negative'
            and (tag.get('is_occurrence') == 'yes' or tag.get('is_mechanism') == 'yes'))


def main():
    print(f"Loading tags...", flush=True)
    tags = json.load(open(TAGS_PATH))['tags']
    print(f"  {len(tags):,} records tagged", flush=True)

    print(f"Loading per-doc records + project lookup...", flush=True)
    records = {}
    rec_to_proj = {}
    for f in sorted(PER_DOC.glob('doc_*.json')):
        d = json.load(open(f))
        for r in d.get('records', []):
            records[r['id']] = r
            rec_to_proj[r['id']] = r.get('kb_associated_project', '')
    print(f"  {len(records):,} records loaded", flush=True)

    print(f"Loading dedup event assignments...", flush=True)
    rec_to_event = {}        # record_id -> canonical_event_id
    rec_to_doc = {}          # record_id -> doc_id (sanity)
    n_assignments_files = 0
    for asn in DEDUP_DIR.rglob('*.assignments.json'):
        n_assignments_files += 1
        d = json.load(open(asn))
        # Each assignment has record_id (or 'id') and event_id
        for a in d.get('assignments', []):
            rid = a.get('record_id') or a.get('id')
            eid = a.get('event_id') or a.get('canonical_id')
            if rid and eid:
                rec_to_event[rid] = eid
                rec_to_doc[rid] = a.get('doc_id') or d.get('doc')
    print(f"  {n_assignments_files} assignment files, {len(rec_to_event):,} records assigned to events", flush=True)
    print(f"  {len(set(rec_to_event.values())):,} unique events", flush=True)

    # Apply filter and build output rows
    print(f"\nApplying clustering filter (negative + (occurrence OR mechanism), NO spec gate)...", flush=True)
    n_pass = n_no_event = 0
    n_total = len(tags)
    by_axis_combo = defaultdict(int)
    by_project = defaultdict(int)
    by_event_size = defaultdict(int)
    event_to_records = defaultdict(list)

    rows = []
    for rid, tag in tags.items():
        if not matches_filter(tag):
            continue
        rec = records.get(rid, {})
        event_id = rec_to_event.get(rid)
        # Records without an event mapping (e.g. no-project synthesis docs that
        # were skipped by dedup) get a singleton event_id = record_id
        if not event_id:
            n_no_event += 1
            event_id = rid  # singleton
        project = rec_to_proj.get(rid, '')
        # Build axis combo string for diagnostics
        axes = tuple((ax, tag.get(ax)) for ax in
                     ['is_occurrence','is_mechanism','is_specification','is_lesson','is_recommendation'])
        combo = '|'.join(f"{ax}:{v}" for ax, v in axes)
        by_axis_combo[combo] += 1
        by_project[project] += 1
        event_to_records[event_id].append(rid)

        rows.append({
            'record_id': rid,
            'event_id': event_id,
            'project': project,
            'doc_id': rec.get('doc_id', ''),
            'narrative': rec.get('narrative', '') or '',
            'evidence': rec.get('evidence', '') or '',
            'is_occurrence': tag.get('is_occurrence'),
            'is_mechanism': tag.get('is_mechanism'),
            'is_specification': tag.get('is_specification'),
            'is_lesson': tag.get('is_lesson'),
            'is_recommendation': tag.get('is_recommendation'),
            'valence': tag.get('valence'),
        })
        n_pass += 1

    # Event size histogram
    for eid, recs in event_to_records.items():
        by_event_size[len(recs)] += 1

    print(f"  {n_pass:,} records passed the looser filter ({100*n_pass/n_total:.1f}% of corpus)", flush=True)
    print(f"  {n_no_event:,} records had no event assignment (treated as singletons)", flush=True)
    print(f"  {len(event_to_records):,} unique events represented in clustering input", flush=True)

    # Write JSONL
    with open(OUT_JSONL, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"\nWrote {OUT_JSONL}  ({OUT_JSONL.stat().st_size:,} bytes)", flush=True)

    # Summary diagnostics
    summary = {
        'n_records_tagged': n_total,
        'n_records_passing_loose_filter': n_pass,
        'n_records_with_event_assignment': n_pass - n_no_event,
        'n_singletons_no_event': n_no_event,
        'n_unique_events': len(event_to_records),
        'top_axis_combos': sorted(by_axis_combo.items(), key=lambda x: -x[1])[:15],
        'top_projects_by_filter_count': sorted(by_project.items(), key=lambda x: -x[1])[:10],
        'event_size_histogram': sorted(by_event_size.items()),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT_SUMMARY}", flush=True)

    print(f"\n=== TOP 10 AXIS COMBINATIONS ===", flush=True)
    for combo, n in summary['top_axis_combos']:
        print(f"  {n:>5}  {combo}", flush=True)

    print(f"\n=== TOP 10 PROJECTS BY FILTER COUNT ===", flush=True)
    for p, n in summary['top_projects_by_filter_count']:
        print(f"  {n:>5}  {p[:70]}", flush=True)

    print(f"\n=== EVENT-SIZE DISTRIBUTION (records-per-event in filter input) ===", flush=True)
    for size, n in summary['event_size_histogram'][:15]:
        print(f"  {size:>3}-record events: {n:,}", flush=True)
    if len(summary['event_size_histogram']) > 15:
        print(f"  ... and tail to max event size {max(by_event_size.keys())}", flush=True)


if __name__ == "__main__":
    main()
