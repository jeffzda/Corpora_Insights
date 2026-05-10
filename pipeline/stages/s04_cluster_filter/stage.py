"""Stage 04 — Cluster filter: build clustering input from tagged records.

Generalises:
    corpora/arena/clustering_v2/code/01_build_clustering_input.py
    corpora/anao/n100_demo/code/anao_n100_filter_input.py

Joins tagged records (from s03) + source records (from s01) + per-doc
event assignments (from s02) and applies the clustering filter:

    valence == <predicate_valence> AND
    any(<axis> == 'yes' for axis in <predicate_axes_any_of>)

Default filter (per ARENA notes.md, retained for ANAO): negative valence
AND (is_occurrence OR is_mechanism). NO specification gate.

Domain config (domain.yaml stages.cluster_filter):
    tags_path:           path to s03 tags.json
    records_path:        path to s01 records jsonl
    events_path:         path to s02 event_assignments jsonl
    output_path:         where to write filter_input.jsonl
    output_summary:      where to write filter_summary.json (optional)
    predicate_valence:   default 'negative'
    predicate_axes_any_of: default ['is_occurrence', 'is_mechanism']
    record_meta_fields:  list of metadata fields to copy from records
                         (e.g. ['portfolio', 'era', 'entity'] for ANAO,
                         ['kb_category', 'kb_associated_project'] for ARENA)
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args = ap.parse_args()

    cfg = DomainConfig.load(args.domain)
    s = cfg.stage('cluster_filter')

    tags_path = Path(s.get('tags_path') or '')
    if not tags_path.is_absolute() and tags_path.parts:
        tags_path = ROOT / tags_path
    records_path = Path(s.get('records_path') or '')
    if not records_path.is_absolute() and records_path.parts:
        records_path = ROOT / records_path
    events_path = Path(s.get('events_path') or '')
    if not events_path.is_absolute() and events_path.parts:
        events_path = ROOT / events_path
    output_path = Path(s.get('output_path') or '')
    if not output_path.is_absolute() and output_path.parts:
        output_path = ROOT / output_path
    summary_path = Path(s.get('output_summary') or '')
    if not summary_path.is_absolute() and summary_path.parts:
        summary_path = ROOT / summary_path

    pred_valence = s.get('predicate_valence', 'negative')
    pred_axes = s.get('predicate_axes_any_of', ['is_occurrence', 'is_mechanism'])
    meta_fields = s.get('record_meta_fields', [])

    if not tags_path.exists():
        raise SystemExit(f'tags_path missing: {tags_path}')
    if not records_path.exists():
        raise SystemExit(f'records_path missing: {records_path}')

    # Load tags
    print(f'loading tags from {tags_path}', flush=True)
    tags_payload = json.load(tags_path.open())
    tags = tags_payload.get('tags') if isinstance(tags_payload, dict) and 'tags' in tags_payload else tags_payload
    print(f'  {len(tags):,} records tagged', flush=True)

    # Load records
    print(f'loading source records from {records_path}', flush=True)
    records = {}
    if records_path.is_dir():
        for f in sorted(records_path.glob('*.json')):
            d = json.load(f.open())
            for r in d.get('records', []):
                records[r.get('id') or r.get('record_id')] = r
    else:
        for line in records_path.open():
            r = json.loads(line)
            records[r.get('id') or r.get('record_id')] = r
    print(f'  {len(records):,} records loaded', flush=True)

    # Load event assignments (optional)
    rec_to_event = {}
    rec_to_doc = {}
    if events_path.exists():
        print(f'loading event assignments from {events_path}', flush=True)
        if events_path.is_file() and events_path.suffix == '.jsonl':
            for line in events_path.open():
                a = json.loads(line)
                rid = a.get('record_id') or a.get('id')
                eid = a.get('event_id') or (a.get('event_ids') or [None])[0]
                if rid and eid:
                    rec_to_event[rid] = eid
                    rec_to_doc[rid] = a.get('_doc_slug') or a.get('doc_id')
        elif events_path.is_dir():
            for asn in events_path.rglob('*.assignments.json'):
                d = json.load(asn.open())
                for a in d.get('assignments', []):
                    rid = a.get('record_id') or a.get('id')
                    eid = a.get('event_id') or a.get('canonical_id')
                    if rid and eid:
                        rec_to_event[rid] = eid
                        rec_to_doc[rid] = a.get('doc_id') or d.get('doc')
        print(f'  {len(rec_to_event):,} records assigned to events', flush=True)

    print(f'\napplying filter: valence == {pred_valence!r} AND any({pred_axes})', flush=True)
    n_pass = n_no_event = 0
    by_axis_combo = defaultdict(int)
    by_meta = {f: defaultdict(int) for f in meta_fields}

    rows = []
    for rid, tag in tags.items():
        if tag.get('valence') != pred_valence:
            continue
        if not any(tag.get(ax) == 'yes' for ax in pred_axes):
            continue
        rec = records.get(rid)
        if not rec:
            continue
        eid = rec_to_event.get(rid)
        if events_path.exists() and not eid:
            n_no_event += 1
            continue
        n_pass += 1
        # diagnostics
        is_occ = tag.get('is_occurrence') == 'yes'
        is_mech = tag.get('is_mechanism') == 'yes'
        if is_occ and is_mech: combo = 'occ_mech'
        elif is_mech: combo = 'mech_only'
        elif is_occ: combo = 'occ_only'
        else: combo = 'other'
        by_axis_combo[combo] += 1
        for f in meta_fields:
            v = (rec.get(f) or rec.get(f'_{f}') or '').strip() if isinstance(rec.get(f) or rec.get(f'_{f}'), str) else ''
            by_meta[f][v] += 1

        row = {
            'record_id': rid,
            'narrative': rec.get('narrative'),
            'evidence': rec.get('evidence'),
            'lesson': rec.get('lesson'),
            'is_occurrence': tag.get('is_occurrence'),
            'is_mechanism': tag.get('is_mechanism'),
            'is_specification': tag.get('is_specification'),
            'is_lesson': tag.get('is_lesson'),
            'is_recommendation': tag.get('is_recommendation'),
            'valence': tag.get('valence'),
        }
        if eid:
            row['event_id'] = eid
            row['doc_slug'] = rec_to_doc.get(rid) or rec.get('_doc_slug') or rec.get('doc_id')
        for f in meta_fields:
            v = rec.get(f) or rec.get(f'_{f}') or ''
            row[f] = v
        rows.append(row)

    rows.sort(key=lambda r: r['record_id'])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    summary = {
        'n_total_tagged': len(tags),
        'n_pass_filter': n_pass,
        'n_no_event_link': n_no_event,
        'pass_rate': round(n_pass / max(len(tags), 1) * 100, 2),
        'predicate_valence': pred_valence,
        'predicate_axes_any_of': pred_axes,
        'by_axis_combo': dict(by_axis_combo),
        'by_meta_top10': {f: dict(sorted(d.items(), key=lambda x: -x[1])[:10]) for f, d in by_meta.items()},
    }
    if summary_path.parts:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2))

    print(f'\nfilter pass: {n_pass:,} / {len(tags):,} ({summary["pass_rate"]}%)', flush=True)
    print(f'  axis combos: {dict(by_axis_combo)}', flush=True)
    print(f'wrote {output_path}', flush=True)
    if summary_path.parts:
        print(f'wrote {summary_path}', flush=True)


if __name__ == '__main__':
    main()
