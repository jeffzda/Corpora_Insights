#!/usr/bin/env python3
"""Grouping rep-stability test on Lake Bonney + Musselroe.

Re-runs the production grouping pass (`pipeline/group_events.py`) on two
projects whose events are central to the causal-chain analysis. Compares
new event_ids (rep2) to the v1 production event_ids (rep1) by computing
pair-Jaccard within each project.

This addresses the open §16.1 gap from `methodology_lessons.md`: full-corpus
rep-noise is unmeasured. Doing it on a small but causal-chain-load-bearing
sample.

Output: grouping_rep_stability.{json,md,html}
"""
from __future__ import annotations
import csv, json, os, subprocess, sys, time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT_REPO = Path('/home/jeffzda/broadlearnings')
PER_DOC = ROOT_REPO / 'corpora/arena/output/per_doc'
RUNS_DIR = ROOT_REPO / 'runs/arena/grouping_rep_stability'
RUNS_DIR.mkdir(parents=True, exist_ok=True)
FILTER_INPUT = ROOT_REPO / 'corpora/arena/clustering_v2/output/filter_input.jsonl'
OUT_DIR = ROOT_REPO / 'corpora/arena/clustering_v2/closure/output/use_case_demos'
OUT_JSON = OUT_DIR / 'grouping_rep_stability.json'
OUT_MD = OUT_DIR / 'grouping_rep_stability.md'
OUT_HTML = OUT_DIR / 'grouping_rep_stability.html'
MD2HTML = '/home/jeffzda/broadlearnings/tools/md2html'

# Seed-doc-first chronological order. Lake Bonney's Project Summary covers the
# whole project arc; Musselroe's Lessons Learnt 2019 is the earliest substantive
# write-up (subsequent reports build on it).
TARGET_PROJECTS = {
    'Lake Bonney Battery Energy Storage System': [
        'doc_0651',  # Project Summary (seed — full project arc)
        'doc_0648',  # Operational Report #1 (16/09/2020)
        'doc_0649',  # Operational Report 2 (9/04/2021)
        'doc_0650',  # Operational Report 3 and 4 (20/07/2022)
        'doc_0647',  # Final KS Report (30/08/2023)
    ],
    'Musselroe Wind Farm FCAS Trial': [
        'doc_1292',  # Lessons Learnt 2019 (seed)
        'doc_0721',  # Provision of FCAS (30/09/2021)
        'doc_0720',  # Public Report (30/01/2022)
    ],
}


def run_grouping(doc_id, prior_events_path, out_path):
    """Invoke pipeline.group_events on one doc."""
    in_path = PER_DOC / f'{doc_id}.json'
    cmd = [sys.executable, '-u', '-m', 'pipeline.group_events',
           '--in', str(in_path),
           '--out', str(out_path),
           '--batch-size', '200']
    if prior_events_path and prior_events_path.exists():
        cmd += ['--prior-events', str(prior_events_path)]
    print(f"    cmd: {' '.join(cmd)}", flush=True)
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT_REPO), capture_output=True, text=True)
    wall = time.time() - started
    if proc.returncode != 0:
        print(f"    FAILED rc={proc.returncode}\n{proc.stderr[-2000:]}", flush=True)
        raise SystemExit
    # Parse cost from stdout (group_events prints a final line with cost)
    cost = 0.0
    for ln in proc.stdout.splitlines():
        if '$' in ln and ('total' in ln.lower() or 'cost' in ln.lower()):
            import re
            m = re.search(r'\$([\d.]+)', ln)
            if m: cost = float(m.group(1))
    print(f"    done: {wall:.0f}s, ${cost:.3f}", flush=True)
    return wall, cost


def collect_rep2_assignments(project_name, docs):
    """Run grouping for each doc in order, return record_id → event_id."""
    proj_dir = RUNS_DIR / project_name.replace(' ','_').replace('/','_')[:60]
    proj_dir.mkdir(parents=True, exist_ok=True)
    prior_events_path = None
    rid_to_event = {}
    total_wall = 0; total_cost = 0
    for i, doc_id in enumerate(docs):
        out_path = proj_dir / f'{doc_id}.assignments.json'
        events_path = proj_dir / f'{doc_id}.events.json'
        # Run
        if not out_path.exists():
            wall, cost = run_grouping(doc_id, prior_events_path, out_path)
            total_wall += wall; total_cost += cost
        else:
            print(f"    cached {out_path.name}", flush=True)
        # Load assignments + events
        d = json.load(open(out_path))
        for a in d.get('assignments', []):
            rid_to_event[a['record_id']] = a.get('event_id')
        if events_path.exists():
            prior_events_path = events_path
    return rid_to_event, total_wall, total_cost


def pair_jaccard(rid_to_event_1, rid_to_event_2, common_rids):
    """Compute pair-decision Jaccard between two event-assignment maps over the same record set.
    Returns (jaccard, n_pairs_total, n_same_in_both, n_same_in_either)."""
    same1 = set()
    same2 = set()
    rids = sorted(common_rids)
    for a, b in combinations(rids, 2):
        if rid_to_event_1.get(a) and rid_to_event_1.get(a) == rid_to_event_1.get(b):
            same1.add((a,b))
        if rid_to_event_2.get(a) and rid_to_event_2.get(a) == rid_to_event_2.get(b):
            same2.add((a,b))
    inter = same1 & same2
    union = same1 | same2
    j = len(inter)/len(union) if union else 1.0
    return j, len(rids)*(len(rids)-1)//2, len(inter), len(union)


def main():
    # Load v1 (rep1) event assignments from filter_input
    print("Loading v1 event assignments...", flush=True)
    rid_to_event_v1 = {}
    rid_to_proj = {}
    for line in open(FILTER_INPUT):
        r = json.loads(line)
        rid = r['record_id']; eid = r.get('event_id'); proj = r.get('project') or ''
        if eid and proj:
            rid_to_event_v1[rid] = f"{proj}::{eid}"  # globally unique
            rid_to_proj[rid] = proj
    print(f"  {len(rid_to_event_v1)} v1 record→event mappings", flush=True)

    # For each project, run rep2
    project_results = {}
    grand_wall = 0; grand_cost = 0
    for project_name, docs in TARGET_PROJECTS.items():
        print(f"\n=== {project_name} ({len(docs)} docs) ===", flush=True)
        rid_to_event_v2, wall, cost = collect_rep2_assignments(project_name, docs)
        grand_wall += wall; grand_cost += cost

        # Determine common record set
        # v2 event ids are doc-local; namespace them with project too
        rid_to_event_v2_ns = {rid: f"{project_name}::{eid}" for rid, eid in rid_to_event_v2.items()}

        common = set(rid_to_event_v1) & set(rid_to_event_v2_ns)
        only_v1 = set(rid_to_event_v1) & {rid for rid in rid_to_proj if rid_to_proj[rid] == project_name} - common
        only_v2 = set(rid_to_event_v2_ns) - common
        print(f"  records v1∩v2: {len(common)}, only-v1: {len(only_v1)}, only-v2: {len(only_v2)}")
        if not common:
            print(f"  WARNING: no common records; skip"); continue

        j, n_pairs, n_same_both, n_same_either = pair_jaccard(rid_to_event_v1, rid_to_event_v2_ns, common)
        # Also event-count comparison
        v1_events_in_proj = len({rid_to_event_v1[rid] for rid in common})
        v2_events_in_proj = len({rid_to_event_v2_ns[rid] for rid in common})
        print(f"  pair-Jaccard: {j:.3f}")
        print(f"  events in v1: {v1_events_in_proj}, v2: {v2_events_in_proj}")
        print(f"  records covered: {len(common)}")
        print(f"  same-event pairs: v1={n_same_either}, both={n_same_both}")

        project_results[project_name] = {
            'n_docs': len(docs),
            'n_records_common': len(common),
            'n_records_only_v1': len(only_v1),
            'n_records_only_v2': len(only_v2),
            'n_events_v1': v1_events_in_proj,
            'n_events_v2': v2_events_in_proj,
            'pair_jaccard': round(j, 4),
            'n_same_event_pairs_v1': sum(1 for a,b in combinations(sorted(common),2) if rid_to_event_v1.get(a) and rid_to_event_v1.get(a)==rid_to_event_v1.get(b)),
            'n_same_event_pairs_v2': sum(1 for a,b in combinations(sorted(common),2) if rid_to_event_v2_ns.get(a) and rid_to_event_v2_ns.get(a)==rid_to_event_v2_ns.get(b)),
            'n_same_event_pairs_both': n_same_both,
            'n_same_event_pairs_either': n_same_either,
            'wall_seconds': round(wall,1),
            'cost_sync': round(cost,3),
        }

    print(f"\nGrand total: ${grand_cost:.2f}, {grand_wall:.0f}s")

    json.dump({
        'projects': project_results,
        'grand_cost': round(grand_cost,3),
        'grand_wall': round(grand_wall,1),
        'targets': {p: docs for p, docs in TARGET_PROJECTS.items()},
    }, open(OUT_JSON,'w'), indent=2)

    # MD report
    md = ['# Grouping rep-stability test',
          '',
          'Re-runs the production event-grouping pass (`pipeline/group_events.py`) on two projects whose events are central to the causal-chain analysis (Lake Bonney BESS, Musselroe Wind FCAS). Compares the new event_ids (rep2) to the v1 production event_ids (rep1) using pair-decision Jaccard within each project.',
          '',
          'Addresses the open §16.1 gap from `methodology_lessons.md`: full-corpus rep-noise is unmeasured. This sample answers the question on a small but causal-chain-load-bearing scope.',
          '',
          'Reference points from prior work:',
          '- 3-doc REVS replication campaign (2026-05-02): pair-decision instability ~32% at temp=0',
          '- 12-doc full REVS production: pair-Jaccard ~0.50',
          '- FC-pool-only subset on 3-doc REVS: Jaccard 1.000 (deterministic)',
          '',
          f'**Total cost:** ${project_results and sum(p["cost_sync"] for p in project_results.values()) or 0:.2f}',
          '',
          '## Per-project results',
          '',
          '| project | n_docs | records | events v1 | events v2 | pair-Jaccard |',
          '|---|---:|---:|---:|---:|---:|']
    for p, r in project_results.items():
        md.append(f"| {p[:55]} | {r['n_docs']} | {r['n_records_common']} | {r['n_events_v1']} | {r['n_events_v2']} | {r['pair_jaccard']:.3f} |")
    md += ['', '## Interpretation', '',
           'Pair-Jaccard interpretation:',
           '- 1.000 = perfect agreement (every pair of records that v1 placed in the same event is also placed in the same event by v2, and vice versa)',
           '- 0.500 = the rep-2 grouping makes ~50% different pair decisions vs rep-1',
           '- 0.000 = no shared pair decisions',
           '',
           'Compare to documented benchmarks (REVS 3-doc 0.68; full-REVS 12-doc 0.50). Higher Jaccard on this sample = production grouping is more stable than the REVS replication campaign suggested; lower = stability concern is real and the 88% causal-chain finding inherits noise.',
           '']

    OUT_MD.write_text('\n'.join(md))
    proc = subprocess.run(
        [sys.executable, MD2HTML, 'Grouping rep-stability test',
         'Broad Learnings · production-handoff §16.1'],
        input='\n'.join(md), capture_output=True, text=True, check=True)
    OUT_HTML.write_text(proc.stdout)

    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == '__main__':
    main()
