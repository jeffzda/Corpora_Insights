#!/usr/bin/env python3
"""Phase 3: cluster records at multiple cosine thresholds.

Performance path:
1. Compute pairwise cosine distance matrix on GPU (single matmul, seconds)
2. Convert to scipy condensed form
3. scipy.cluster.hierarchy.linkage with average linkage (uses internal C code,
   parallelisable, much faster than sklearn AgglomerativeClustering for this size)
4. fcluster at multiple thresholds — reuses the linkage result, no recompute

Total runtime for 25k × 2560 dims: ~2-5 min for all 4 thresholds.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
EMB_PATH = OUT_DIR / 'embeddings.npy'
IDS_PATH = OUT_DIR / 'embedding_record_ids.json'
INPUT_JSONL = OUT_DIR / 'filter_input.jsonl'

DEFAULT_THRESHOLDS = [0.50, 0.55, 0.60, 0.65]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--thresholds', type=str,
                     default=','.join(str(t) for t in DEFAULT_THRESHOLDS))
    args = ap.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(',')]

    print(f"Loading embeddings...", flush=True)
    emb = np.load(EMB_PATH)
    rec_ids = json.load(open(IDS_PATH))
    rows = [json.loads(line) for line in open(INPUT_JSONL)]
    rid_to_row = {r['record_id']: r for r in rows}
    print(f"  {emb.shape[0]:,} embeddings × {emb.shape[1]} dims", flush=True)
    assert len(rec_ids) == emb.shape[0]

    # Step 1: GPU pairwise cosine distance
    import torch
    print(f"\nComputing pairwise cosine distance on GPU...", flush=True)
    t0 = time.time()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"  device: {device}", flush=True)
    # Embeddings should already be unit-normalised (we verified mean norm ~1.0)
    et = torch.from_numpy(emb).to(device)
    # cosine similarity = X @ X^T for unit-normalised X
    # cosine distance = 1 - similarity
    print(f"  matmul on {tuple(et.shape)}...", flush=True)
    sim = (et @ et.T).cpu().numpy()
    # Free GPU memory immediately
    del et
    torch.cuda.empty_cache() if device == 'cuda' else None
    print(f"  similarity matrix shape: {sim.shape}, dtype: {sim.dtype}", flush=True)
    np.fill_diagonal(sim, 1.0)
    dist = 1.0 - sim
    # Numerical safety: clip negatives caused by fp roundoff
    np.clip(dist, 0.0, 2.0, out=dist)
    print(f"  pairwise distance computed in {time.time()-t0:.1f}s", flush=True)

    # Step 2: convert to condensed form for scipy
    print(f"\nConverting to scipy condensed distance vector...", flush=True)
    from scipy.spatial.distance import squareform
    t0 = time.time()
    # squareform requires symmetric matrix with zero diagonal
    np.fill_diagonal(dist, 0.0)
    cond = squareform(dist, checks=False)
    del dist  # free
    print(f"  condensed: {cond.shape[0]:,} pairwise distances, "
          f"{cond.nbytes/1e9:.2f} GB ({time.time()-t0:.1f}s)", flush=True)

    # Step 3: scipy linkage (uses internal C, parallelisable)
    print(f"\nRunning scipy linkage (average) ...", flush=True)
    from scipy.cluster.hierarchy import linkage, fcluster
    t0 = time.time()
    Z = linkage(cond, method='average')
    print(f"  linkage built in {time.time()-t0:.1f}s", flush=True)
    del cond  # free

    # Step 4: extract clusters at each threshold (cheap, reuses Z)
    for thresh in thresholds:
        cosine_distance_threshold = 1 - thresh  # we cluster at distance ≤ this
        print(f"\nExtracting clusters at cosine ≥{thresh} (distance ≤{cosine_distance_threshold:.2f})...",
              flush=True)
        t0 = time.time()
        labels = fcluster(Z, t=cosine_distance_threshold, criterion='distance') - 1
        n_clusters = len(set(labels))
        elapsed = time.time() - t0
        sizes = Counter(labels)
        size_dist = Counter(sizes.values())
        print(f"  {n_clusters:,} clusters in {elapsed:.0f}s", flush=True)
        size_sorted = sorted(size_dist.items())
        print(f"  Cluster size distribution (top 10):", flush=True)
        for sz, n in size_sorted[:10]:
            print(f"    {sz}-record clusters: {n:,}", flush=True)
        if len(size_sorted) > 10:
            largest = max(sizes.values())
            print(f"    ... up to {largest}-record largest cluster", flush=True)

        # Save with axis-feature consistency annotations
        out_path = OUT_DIR / f'clusters_thr_{int(thresh*100):02d}.json'
        clusters_dict = {}
        for rid, lbl in zip(rec_ids, labels):
            cid = int(lbl)
            clusters_dict.setdefault(cid, []).append(rid)
        cluster_records = []
        for cid, members in clusters_dict.items():
            row_metas = [rid_to_row[r] for r in members]
            n_neg = sum(1 for m in row_metas if m['valence']=='negative')
            n_occ = sum(1 for m in row_metas if m['is_occurrence']=='yes')
            n_mech = sum(1 for m in row_metas if m['is_mechanism']=='yes')
            n_spec = sum(1 for m in row_metas if m['is_specification']=='yes')
            n_les = sum(1 for m in row_metas if m['is_lesson']=='yes')
            n_rec = sum(1 for m in row_metas if m['is_recommendation']=='yes')
            uniq_events = len({m['event_id'] for m in row_metas})
            uniq_projs  = len({m['project'] for m in row_metas if m['project']})
            cluster_records.append({
                'cluster_id': cid,
                'size': len(members),
                'member_record_ids': members,
                'n_unique_events': uniq_events,
                'n_unique_projects': uniq_projs,
                'mechanism_share': round(n_mech/len(members), 3),
                'occurrence_share': round(n_occ/len(members), 3),
                'specification_share': round(n_spec/len(members), 3),
                'lesson_share': round(n_les/len(members), 3),
                'recommendation_share': round(n_rec/len(members), 3),
                'negative_share': round(n_neg/len(members), 3),
            })
        cluster_records.sort(key=lambda c: -c['size'])
        out_path.write_text(json.dumps(cluster_records, indent=2, ensure_ascii=False))
        print(f"  Wrote {out_path}  ({out_path.stat().st_size:,} bytes)", flush=True)


if __name__ == "__main__":
    main()
