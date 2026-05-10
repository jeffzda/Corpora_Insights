#!/usr/bin/env python3
"""Closure phase 6: rebuild filter_input.jsonl with globally-unique event_ids.

The upstream dedup pipeline produced per-project local event_ids
(EVT-0001, EVT-0002, ...) that COLLIDE when joined globally — EVT-0001
appears in 179 of the 493 projects in the corpus. This makes any
downstream event-based analysis treat unrelated records as siblings.

Fix: re-emit filter_input with a new event_id field of the form
    EVT-{project_num:03d}-{event_num:04d}
where:
    project_num    — 3-digit project number, assigned in alphabetical
                     order of project name (stable across runs)
    event_num      — 4-digit local event number within that project
                     (preserves the original EVT-NNNN value if present;
                     for records whose event_id was their own record_id,
                     i.e. singleton-events from dedup, assigns a
                     synthetic number starting at 9000)

Records without a project (project == '' or null) get project_num 000.

Outputs:
    output/filter_input_globalkey.jsonl — same records, new event_id
    output/project_id_map.json — project name → project_num mapping
    output/event_key_map.jsonl — for each record, the old vs new event_id
                                 (for diagnostic / re-join purposes)
"""
import json
import re
from collections import defaultdict
from pathlib import Path

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
INPUT = V2_OUT / 'filter_input.jsonl'
OUT = V2_OUT / 'filter_input_globalkey.jsonl'
PROJ_MAP_OUT = V2_OUT / 'project_id_map.json'
EVENT_MAP_OUT = V2_OUT / 'event_key_map.jsonl'


def main():
    print(f"Loading {INPUT}...", flush=True)
    rows = [json.loads(l) for l in open(INPUT)]
    print(f"  {len(rows):,} records", flush=True)

    # Stable project numbering: alphabetical order of non-empty project names
    projects = sorted({r.get('project','') for r in rows} - {'', None})
    proj_to_num = {'': 0}  # 0 = no project
    for i, p in enumerate(projects, start=1):
        proj_to_num[p] = i
    print(f"  {len(projects)} unique projects (project_num 1..{len(projects)})", flush=True)

    # Within each project, identify the local event_num.
    # Original event_id values fall into two camps:
    #   1. EVT-NNNN — local event number; extract NNNN.
    #   2. Anything else (typically the record's own record_id) — singleton
    #      "event" with no real grouping. Assign a synthetic local number
    #      starting at 9000 for that project, incrementing once per record.
    evt_pattern = re.compile(r'^EVT-(\d+)$')
    project_singleton_counter = defaultdict(lambda: 9000)

    new_rows = []
    map_rows = []
    n_real = 0
    n_synth = 0
    n_no_proj = 0

    for r in rows:
        proj = r.get('project','') or ''
        proj_num = proj_to_num[proj]
        if proj_num == 0:
            n_no_proj += 1
        old_eid = r.get('event_id','') or ''
        m = evt_pattern.match(old_eid)
        if m:
            event_num = int(m.group(1))
            n_real += 1
        else:
            event_num = project_singleton_counter[proj]
            project_singleton_counter[proj] += 1
            n_synth += 1
        new_eid = f"EVT-{proj_num:03d}-{event_num:04d}"
        nr = dict(r)
        nr['event_id_old'] = old_eid
        nr['event_id'] = new_eid
        nr['project_num'] = proj_num
        new_rows.append(nr)
        map_rows.append({
            'record_id': r['record_id'],
            'project': proj,
            'project_num': proj_num,
            'event_id_old': old_eid,
            'event_id_new': new_eid,
        })

    print(f"  records with original EVT-NNNN: {n_real:,}", flush=True)
    print(f"  records with synthetic singleton event_id: {n_synth:,}", flush=True)
    print(f"  records with no project: {n_no_proj:,}", flush=True)

    with open(OUT, 'w') as f:
        for r in new_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"\n  wrote {OUT}", flush=True)

    PROJ_MAP_OUT.write_text(json.dumps(proj_to_num, indent=2, ensure_ascii=False))
    print(f"  wrote {PROJ_MAP_OUT}", flush=True)

    with open(EVENT_MAP_OUT, 'w') as f:
        for r in map_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"  wrote {EVENT_MAP_OUT}", flush=True)

    # Sanity check: globally-unique event_ids no longer collide on project
    from collections import Counter
    event_counts = Counter(r['event_id'] for r in new_rows)
    largest_events = event_counts.most_common(10)
    print(f"\n  total distinct globally-unique event_ids: {len(event_counts):,}", flush=True)
    print(f"  largest events under new keys (now correctly per-project):", flush=True)
    for eid, n in largest_events:
        # Look up project for clarity
        sample = next(r for r in new_rows if r['event_id'] == eid)
        proj = sample.get('project','(no project)')[:50]
        print(f"    {eid}: {n} records  in  {proj}", flush=True)

    # Verify every project's events are now properly local
    project_event_overlaps = Counter()
    for r in new_rows:
        # Each (project, new_event_id) pair should be self-consistent
        assert r['event_id'].startswith(f"EVT-{r['project_num']:03d}-"), \
            f"Inconsistent: {r['record_id']} has project_num {r['project_num']} but event_id {r['event_id']}"
    print(f"\n  ✓ all {len(new_rows):,} new event_ids consistent with project_num prefix", flush=True)


if __name__ == "__main__":
    main()
