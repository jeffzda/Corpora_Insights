#!/usr/bin/env python3
"""Phase 4: print sample clusters from each threshold for human inspection.

For each threshold's output, show:
- Top 10 largest clusters with axis profiles + sample narratives
- 10 random clusters of size 3-15 with full member previews
- Singleton percentage (clusters of size 1 = unclustered)

Output to stdout for visual scan + writes a markdown summary.
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT_JSONL = OUT_DIR / 'filter_input.jsonl'


def load_records():
    return {r['record_id']: r for r in (json.loads(l) for l in open(INPUT_JSONL))}


def axis_signature(c):
    parts = []
    for ax_short, ax_full in [('o','occurrence_share'),('m','mechanism_share'),
                                 ('s','specification_share'),('l','lesson_share'),
                                 ('r','recommendation_share'),('-','negative_share')]:
        v = c.get(ax_full, 0)
        if v >= 0.5:
            parts.append(f"{ax_short}{int(v*100):>2}%")
    return ' '.join(parts) if parts else '(no >50%)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--thresholds', default='50,55,60,65')
    args = ap.parse_args()
    thresholds = [int(t) for t in args.thresholds.split(',')]

    records = load_records()
    print(f"Loaded {len(records):,} input records\n")

    summary_md = ['# Clustering v2 — first inspection\n']

    for thr in thresholds:
        path = OUT_DIR / f'clusters_thr_{thr:02d}.json'
        if not path.exists():
            print(f"  Missing: {path}, skipping")
            continue
        clusters = json.load(open(path))
        n_total = len(clusters)
        sizes = [c['size'] for c in clusters]
        n_singleton = sum(1 for s in sizes if s == 1)
        n_small = sum(1 for s in sizes if 2 <= s <= 5)
        n_med = sum(1 for s in sizes if 6 <= s <= 20)
        n_big = sum(1 for s in sizes if s > 20)

        print(f"\n{'='*70}")
        print(f"  THRESHOLD {thr/100:.2f}  —  {n_total:,} clusters")
        print(f"{'='*70}")
        print(f"  Singleton (size=1):  {n_singleton:,}  ({100*n_singleton/n_total:.0f}%)")
        print(f"  Small  (2-5):         {n_small:,}  ({100*n_small/n_total:.0f}%)")
        print(f"  Medium (6-20):        {n_med:,}  ({100*n_med/n_total:.0f}%)")
        print(f"  Large  (>20):          {n_big:,}  ({100*n_big/n_total:.0f}%)")
        print(f"  Largest cluster:      {max(sizes)}")

        summary_md.append(f"\n## Threshold {thr/100:.2f}\n")
        summary_md.append(f"- {n_total:,} clusters; {n_singleton:,} singletons ({100*n_singleton/n_total:.0f}%)")
        summary_md.append(f"- {n_small:,} small (2-5); {n_med:,} medium (6-20); {n_big:,} large (>20)")
        summary_md.append(f"- Largest cluster: {max(sizes)} records\n")

        print(f"\n  --- TOP 8 LARGEST CLUSTERS ---")
        summary_md.append("\n### Top 8 largest clusters\n")
        for c in clusters[:8]:
            members = c['member_record_ids']
            sig = axis_signature(c)
            sample = members[0]
            sample_narr = (records[sample]['narrative'] or '')[:120]
            print(f"\n  Cluster {c['cluster_id']}: {c['size']} records, "
                  f"{c['n_unique_events']} events, {c['n_unique_projects']} projects  [{sig}]")
            print(f"    Sample: {sample_narr}")
            summary_md.append(f"- **Cluster {c['cluster_id']}** ({c['size']} records, "
                              f"{c['n_unique_events']} events, {c['n_unique_projects']} projects, axes: {sig})")
            summary_md.append(f"  - Sample: \"{sample_narr}...\"")

        print(f"\n  --- 6 RANDOM MEDIUM CLUSTERS (size 4-12) ---")
        summary_md.append(f"\n### Random sample of medium clusters\n")
        rng = random.Random(thr)  # deterministic per-threshold
        med = [c for c in clusters if 4 <= c['size'] <= 12]
        sample_med = rng.sample(med, min(6, len(med)))
        for c in sample_med:
            members = c['member_record_ids']
            sig = axis_signature(c)
            print(f"\n  Cluster {c['cluster_id']}: {c['size']} records  [{sig}]")
            for rid in members[:5]:
                narr = (records[rid]['narrative'] or '')[:130]
                print(f"    {rid}: {narr}")
            summary_md.append(f"\n- **Cluster {c['cluster_id']}** ({c['size']} records, axes: {sig}):")
            for rid in members[:5]:
                narr = (records[rid]['narrative'] or '')[:130]
                summary_md.append(f"  - `{rid}`: {narr}")

    summary_path = OUT_DIR / 'inspection_notes.md'
    summary_path.write_text('\n'.join(summary_md))
    print(f"\n\nWrote {summary_path}")


if __name__ == "__main__":
    main()
