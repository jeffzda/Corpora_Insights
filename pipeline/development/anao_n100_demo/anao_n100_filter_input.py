#!/usr/bin/env python3
"""ANAO N=100 — Phase 1: build clustering input.

Mirrors corpora/arena/clustering_v2/code/01_build_clustering_input.py
with the same filter:
  valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes')

Joins:
  - 6-axis tags from anao_n100_label_tags.json
  - source records (narrative + evidence + portfolio + era) from anao_n100_marker_records_filtered.jsonl
  - per-doc event_ids from anao_n100_event_assignments.jsonl

Output:
  output/anao_n100_filter_input.jsonl — one record per line, all fields downstream needs
  output/anao_n100_filter_summary.json — diagnostic counts
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = ROOT / 'corpora/anao/n100_demo/output'
TAGS_PATH = OUT_DIR / 'anao_n100_label_tags.json'
RECORDS_PATH = OUT_DIR / 'anao_n100_marker_records_filtered.jsonl'
EVENTS_PATH = OUT_DIR / 'anao_n100_event_assignments.jsonl'

OUT_JSONL = OUT_DIR / 'anao_n100_filter_input.jsonl'
OUT_SUMMARY = OUT_DIR / 'anao_n100_filter_summary.json'


def matches_filter(tag):
    return (tag.get('valence') == 'negative'
            and (tag.get('is_occurrence') == 'yes' or tag.get('is_mechanism') == 'yes'))


def main():
    print(f'Loading tags...', flush=True)
    tags = json.load(TAGS_PATH.open())['tags']
    print(f'  {len(tags):,} records tagged', flush=True)

    print(f'Loading source records...', flush=True)
    records = {}
    for line in RECORDS_PATH.open():
        r = json.loads(line)
        records[r['id']] = r
    print(f'  {len(records):,} records loaded', flush=True)

    print(f'Loading event assignments...', flush=True)
    rec_to_event = {}
    rec_to_doc = {}
    for line in EVENTS_PATH.open():
        a = json.loads(line)
        rid = a.get('record_id')
        eid = a.get('event_id') or (a.get('event_ids') or [None])[0]
        if rid and eid:
            rec_to_event[rid] = eid
            rec_to_doc[rid] = a.get('_doc_slug')
    print(f'  {len(rec_to_event):,} records assigned to events', flush=True)
    print(f'  {len(set(rec_to_event.values())):,} unique events', flush=True)

    print(f'\nApplying clustering filter (negative + (occurrence OR mechanism), NO spec gate)...', flush=True)
    n_pass = n_no_event = 0
    n_total = len(tags)
    by_axis_combo = defaultdict(int)
    by_portfolio = defaultdict(int)
    by_era = defaultdict(int)

    rows = []
    for rid, tag in tags.items():
        if not matches_filter(tag):
            continue
        rec = records.get(rid)
        if not rec:
            continue
        eid = rec_to_event.get(rid)
        if not eid:
            n_no_event += 1
            continue
        n_pass += 1
        # Axis combo for diagnostics
        is_occ = tag.get('is_occurrence') == 'yes'
        is_mech = tag.get('is_mechanism') == 'yes'
        if is_occ and is_mech: combo = 'occ_mech'
        elif is_mech: combo = 'mech_only'
        elif is_occ: combo = 'occ_only'
        else: combo = 'other'
        by_axis_combo[combo] += 1
        portfolio = (rec.get('_portfolio') or '').strip()
        era = (rec.get('_era') or '').strip()
        by_portfolio[portfolio] += 1
        by_era[era] += 1

        rows.append({
            'record_id': rid,
            'event_id': eid,
            'doc_slug': rec_to_doc.get(rid) or rec.get('_doc_slug'),
            'narrative': rec.get('narrative'),
            'evidence': rec.get('evidence'),
            'lesson': rec.get('lesson'),
            'is_occurrence': tag.get('is_occurrence'),
            'is_mechanism': tag.get('is_mechanism'),
            'is_specification': tag.get('is_specification'),
            'is_lesson': tag.get('is_lesson'),
            'is_recommendation': tag.get('is_recommendation'),
            'valence': tag.get('valence'),
            'portfolio': portfolio,
            'era': era,
            'entity': (rec.get('_entity') or '').strip(),
            'sector': (rec.get('_sector') or '').strip(),
            'year_tabled': (rec.get('_year_tabled') or '').strip(),
        })

    rows.sort(key=lambda r: r['record_id'])
    with OUT_JSONL.open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    summary = {
        'n_total_tagged': n_total,
        'n_pass_filter': n_pass,
        'n_no_event_link': n_no_event,
        'pass_rate': round(n_pass / n_total * 100, 1) if n_total else 0,
        'by_axis_combo': dict(by_axis_combo),
        'by_portfolio_top10': dict(sorted(by_portfolio.items(), key=lambda x: -x[1])[:10]),
        'by_era': dict(by_era),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2))

    print(f'\nFilter pass: {n_pass:,} / {n_total:,} ({summary["pass_rate"]}%)')
    print(f'  axis combos: {dict(by_axis_combo)}')
    print(f'  by era: {dict(by_era)}')
    print(f'  top 10 portfolios:')
    for p, n in sorted(by_portfolio.items(), key=lambda x: -x[1])[:10]:
        print(f'    {n:>4}  {p[:60]}')
    print(f'\nWrote {OUT_JSONL}')
    print(f'Wrote {OUT_SUMMARY}')


if __name__ == '__main__':
    main()
