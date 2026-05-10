#!/usr/bin/env python3
"""Closure phase 5: cluster co-occurrence analysis via shared events.

For every real event (scoped by (project, event_id) — same fix as script 07),
finds all clusters whose records are present in that event. Pairs of clusters
that share an event "co-occur." Counts pair frequency across the corpus.

This reveals which failure mechanisms tend to manifest together within the
same project event sequence — siblings, causal precursors/consequents, or
mechanism pairs that share a triggering condition.

Output:
  cluster_cooccurrence.json — full pair-count matrix (sparse list)
  cluster_cooccurrence_top.md — ranked top-N pairs with cluster names
                                and example shared events
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
ASSIGNMENTS = V2_OUT / 'sweep' / 'corpus_assignments.jsonl'
INPUT = V2_OUT / 'filter_input.jsonl'
PROJECTS_CSV = Path('/home/jeffzda/broadlearnings/corpora/arena/arena-projects-export_1772932404.csv')

OUT_JSON = CLOSURE_OUT / 'cluster_cooccurrence.json'
OUT_MD = CLOSURE_OUT / 'cluster_cooccurrence_top.md'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=80,
                    help='Number of top co-occurring pairs to show in MD report')
    ap.add_argument('--min-event-size', type=int, default=2,
                    help='Skip events smaller than this (default: 2 — singletons contribute no pairs)')
    ap.add_argument('--max-event-size', type=int, default=30,
                    help='Skip events larger than this (likely upstream bucket artefacts)')
    args = ap.parse_args()

    print("Loading data...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    rows = [json.loads(l) for l in open(INPUT)]
    rid_to_record = {r['record_id']: r for r in rows}
    csv_rows = list(csv.DictReader(open(PROJECTS_CSV)))
    proj_to_cat = {r['Project']: r.get('Category','') for r in csv_rows}
    assigns = [json.loads(l) for l in open(ASSIGNMENTS)]
    rid_to_cluster = {a['record_id']: a['cluster_id'] for a in assigns
                      if a.get('cluster_id') in cid_to_meta}
    print(f"  catalogue: {len(catalogue)}", flush=True)
    print(f"  clustered records: {len(rid_to_cluster)}", flush=True)

    # Build (project, event_id) → list of cluster_ids
    event_to_clusters = defaultdict(list)  # key: (project, event_id), val: list of cluster_ids (one per record)
    event_to_records = defaultdict(list)
    for r in rows:
        eid = r.get('event_id')
        proj = r.get('project') or ''
        if not eid: continue
        cid = rid_to_cluster.get(r['record_id'])
        key = (proj, eid)
        event_to_records[key].append(r['record_id'])
        if cid:
            event_to_clusters[key].append(cid)

    # Filter by event size
    event_sizes = {k: len(v) for k, v in event_to_records.items()}
    valid_events = {k for k, sz in event_sizes.items()
                    if args.min_event_size <= sz <= args.max_event_size}
    print(f"  total (project, event_id) pairs: {len(event_to_records):,}", flush=True)
    print(f"  events with size {args.min_event_size}-{args.max_event_size}: {len(valid_events):,}", flush=True)

    # Co-occurrence counts (unordered pairs)
    pair_counts = Counter()
    pair_to_events = defaultdict(list)  # for citing example events
    self_counts = Counter()  # cluster appearing >1× in same event
    n_multi_cluster_events = 0
    for key in valid_events:
        cids = event_to_clusters.get(key, [])
        if len(cids) < 2: continue
        unique_cids = sorted(set(cids))
        # Self counts: a cluster appearing 2+ times in same event
        cnt = Counter(cids)
        for c, n in cnt.items():
            if n >= 2:
                self_counts[c] += 1
        # Pair counts (only different clusters)
        if len(unique_cids) >= 2:
            n_multi_cluster_events += 1
            for i in range(len(unique_cids)):
                for j in range(i+1, len(unique_cids)):
                    pair = (unique_cids[i], unique_cids[j])
                    pair_counts[pair] += 1
                    if len(pair_to_events[pair]) < 5:
                        pair_to_events[pair].append(key)
    print(f"  multi-cluster events: {n_multi_cluster_events:,}", flush=True)
    print(f"  unique cluster pairs co-occurring: {len(pair_counts):,}", flush=True)

    # Save full pair counts
    pair_data = [
        {
            'cluster_a': a, 'cluster_b': b,
            'name_a': cid_to_meta[a]['canonical_name'],
            'name_b': cid_to_meta[b]['canonical_name'],
            'cooccurrences': n,
            'example_events': [{'project': p, 'event_id': e}
                                for p, e in pair_to_events[(a,b)][:3]],
        }
        for (a, b), n in pair_counts.most_common()
    ]
    OUT_JSON.write_text(json.dumps(pair_data, indent=2, ensure_ascii=False))
    print(f"\n  wrote {OUT_JSON} ({len(pair_data)} pairs)", flush=True)

    # Markdown top-N report
    lines = [
        f"# Cluster co-occurrence via shared events",
        "",
        f"For every real event (project, event_id with size {args.min_event_size}-{args.max_event_size}), recorded which clusters had records in that event. Pairs of distinct clusters that share an event co-occur. Counts measure how often the two failure mechanisms manifest together within the same project event sequence.",
        "",
        f"- Multi-cluster events: {n_multi_cluster_events:,}",
        f"- Unique cluster pairs that co-occur: {len(pair_counts):,}",
        f"- Showing top {args.top} pairs by co-occurrence count",
        "",
        "## Top co-occurring cluster pairs",
        "",
    ]
    for i, ((a, b), n) in enumerate(pair_counts.most_common(args.top), 1):
        meta_a = cid_to_meta[a]
        meta_b = cid_to_meta[b]
        size_a = sum(1 for c in rid_to_cluster.values() if c == a)
        size_b = sum(1 for c in rid_to_cluster.values() if c == b)
        lines.append(f"\n### {i}. [{a}] × [{b}] — co-occur in {n} events")
        lines.append(f"- **[{a}] {meta_a['canonical_name']}** (cluster size {size_a})")
        lines.append(f"  > {meta_a.get('mechanism_signature','')[:280]}")
        lines.append(f"- **[{b}] {meta_b['canonical_name']}** (cluster size {size_b})")
        lines.append(f"  > {meta_b.get('mechanism_signature','')[:280]}")
        # Show 2 example events
        events = pair_to_events[(a, b)][:3]
        if events:
            lines.append(f"- Example events:")
            for proj, eid in events:
                lines.append(f"  - {eid} in *{proj}*")

    # Top self-co-occurrences (same cluster manifesting multiple times in one event)
    if self_counts:
        lines.append(f"\n## Top self-co-occurring clusters")
        lines.append("(Same mechanism manifesting multiple times within one project event sequence)\n")
        for cid, n in self_counts.most_common(20):
            meta = cid_to_meta[cid]
            lines.append(f"- [{cid}] {meta['canonical_name']} — {n} events")

    OUT_MD.write_text('\n'.join(lines))
    print(f"  wrote {OUT_MD}", flush=True)

    # Summary print
    print(f"\n=== TOP 15 CO-OCCURRING PAIRS ===")
    for (a, b), n in pair_counts.most_common(15):
        print(f"  {n:>4}  [{a}] × [{b}]")
        print(f"        {cid_to_meta[a]['canonical_name'][:70]}")
        print(f"        {cid_to_meta[b]['canonical_name'][:70]}")


if __name__ == "__main__":
    main()
