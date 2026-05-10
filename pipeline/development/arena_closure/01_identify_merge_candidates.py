#!/usr/bin/env python3
"""Closure phase 1: identify near-duplicate cluster pairs via embedding similarity.

Embeds all 1,141 clusters' canonical_name + mechanism_signature using
Qwen3-Embedding-4B (same model as the rest of the pipeline). Computes pairwise
cosine similarity on GPU and surfaces pairs above a threshold for LLM
adjudication in step 02.

Output: merge_candidates.json — list of pairs above threshold with both clusters'
metadata and the cosine score, ready for review or LLM adjudication.

Cost: just GPU compute, no API calls. ~30 seconds wall.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

CLUSTERING_V2 = Path(__file__).resolve().parents[2]
SOURCE_CATALOGUE = CLUSTERING_V2 / 'output' / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
OUT_DIR.mkdir(exist_ok=True)
EMB_OUT = OUT_DIR / 'cluster_embeddings.npy'
IDS_OUT = OUT_DIR / 'cluster_ids.json'
CAND_OUT = OUT_DIR / 'merge_candidates.json'

MODEL = 'Qwen/Qwen3-Embedding-4B'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threshold', type=float, default=0.80,
                    help='Cosine similarity threshold for pair shortlisting (default 0.80)')
    ap.add_argument('--top-k', type=int, default=400,
                    help='Cap on number of pairs returned (default 400)')
    args = ap.parse_args()

    print(f"Loading catalogue from {SOURCE_CATALOGUE}", flush=True)
    catalogue = json.load(open(SOURCE_CATALOGUE))['clusters']
    print(f"  {len(catalogue)} clusters loaded", flush=True)

    # Build embedding text per cluster
    cluster_ids = [c['cluster_id'] for c in catalogue]
    texts = [f"{c['canonical_name']}\n{c.get('mechanism_signature','')}".strip()
             for c in catalogue]

    # Embed
    print(f"Loading {MODEL} on GPU bfloat16...", flush=True)
    from sentence_transformers import SentenceTransformer
    import torch
    model = SentenceTransformer(MODEL, device='cuda',
                                model_kwargs={'torch_dtype': 'bfloat16'})
    t0 = time.time()
    embs = model.encode(texts, batch_size=16, show_progress_bar=True,
                         normalize_embeddings=True, convert_to_numpy=True)
    print(f"\nEmbedded {len(texts)} clusters in {time.time()-t0:.0f}s; shape {embs.shape}", flush=True)

    # Save embeddings (useful for downstream work)
    np.save(EMB_OUT, embs.astype(np.float32))
    IDS_OUT.write_text(json.dumps(cluster_ids))
    print(f"  saved {EMB_OUT}", flush=True)

    # Pairwise similarity on GPU
    print(f"Computing pairwise cosine similarity...", flush=True)
    et = torch.from_numpy(embs).to('cuda')
    sim = (et @ et.T).cpu().numpy()
    del et
    torch.cuda.empty_cache()
    np.fill_diagonal(sim, -1.0)  # exclude self-similarity
    print(f"  similarity matrix {sim.shape}", flush=True)

    # Find pairs above threshold (upper triangle to avoid duplicates)
    n = len(cluster_ids)
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            s = float(sim[i, j])
            if s >= args.threshold:
                pairs.append((s, i, j))
    pairs.sort(reverse=True)
    print(f"  {len(pairs)} pairs above threshold {args.threshold}", flush=True)
    if len(pairs) > args.top_k:
        print(f"  capping at top-{args.top_k}", flush=True)
        pairs = pairs[:args.top_k]

    # Build candidate records with both clusters' metadata
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    candidates = []
    for s, i, j in pairs:
        a = cid_to_meta[cluster_ids[i]]
        b = cid_to_meta[cluster_ids[j]]
        candidates.append({
            'cosine_similarity': round(s, 4),
            'cluster_a': {
                'cluster_id': a['cluster_id'],
                'canonical_name': a['canonical_name'],
                'mechanism_signature': a.get('mechanism_signature', ''),
                'n_members': len(a.get('supporting_record_ids') or []),
            },
            'cluster_b': {
                'cluster_id': b['cluster_id'],
                'canonical_name': b['canonical_name'],
                'mechanism_signature': b.get('mechanism_signature', ''),
                'n_members': len(b.get('supporting_record_ids') or []),
            },
        })

    CAND_OUT.write_text(json.dumps(candidates, indent=2, ensure_ascii=False))
    print(f"\n  wrote {CAND_OUT} ({len(candidates)} candidates)", flush=True)

    # Quick distribution summary
    if candidates:
        print(f"\nSimilarity distribution among shortlisted pairs:")
        bands = [(0.95, 1.01), (0.90, 0.95), (0.85, 0.90), (0.80, 0.85)]
        for lo, hi in bands:
            n_band = sum(1 for c in candidates if lo <= c['cosine_similarity'] < hi)
            print(f"  cos {lo:.2f}-{hi:.2f}: {n_band}", flush=True)

        print(f"\nTop 10 highest-similarity candidate pairs:")
        for c in candidates[:10]:
            print(f"\n  cos={c['cosine_similarity']:.4f}")
            print(f"    [{c['cluster_a']['cluster_id']}] {c['cluster_a']['canonical_name']}")
            print(f"      ({c['cluster_a']['n_members']} members)")
            print(f"    [{c['cluster_b']['cluster_id']}] {c['cluster_b']['canonical_name']}")
            print(f"      ({c['cluster_b']['n_members']} members)")


if __name__ == "__main__":
    main()
