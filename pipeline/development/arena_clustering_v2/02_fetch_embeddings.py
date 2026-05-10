#!/usr/bin/env python3
"""Phase 2 (revised): pull existing Qwen3-Embedding-4B vectors from ChromaDB.

The arena_records_e3 collection already has all 90,192 records embedded
with the same model used in the RAG pipeline. We just need to fetch the
subset corresponding to the 25,479 records that pass our clustering filter.
"""
import json
import time
from pathlib import Path

import numpy as np
import chromadb

ROOT = Path('/home/jeffzda/broadlearnings')
CHROMA = ROOT / 'corpora/.chromadb'
COLLECTION = 'arena_records_e3'
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT = OUT_DIR / 'filter_input.jsonl'
OUT_NPY = OUT_DIR / 'embeddings.npy'
OUT_IDS = OUT_DIR / 'embedding_record_ids.json'

BATCH = 500  # chroma's get() can take many ids at once but bound to be safe


def main():
    print(f"Loading filter input...", flush=True)
    rows = [json.loads(line) for line in open(INPUT)]
    record_ids = [r['record_id'] for r in rows]
    print(f"  {len(record_ids):,} record ids to fetch", flush=True)

    print(f"Connecting to ChromaDB collection '{COLLECTION}'...", flush=True)
    client = chromadb.PersistentClient(path=str(CHROMA))
    coll = client.get_collection(COLLECTION)
    print(f"  Collection has {coll.count():,} entries total", flush=True)

    started = time.time()
    embs = np.empty((len(record_ids), 2560), dtype=np.float32)
    found = 0
    missing = []
    for i in range(0, len(record_ids), BATCH):
        batch_ids = record_ids[i:i+BATCH]
        result = coll.get(ids=batch_ids, include=['embeddings'])
        # Result preserves the order of returned ids in result['ids'];
        # build a lookup so we map back to the requested order
        emb_map = {rid: emb for rid, emb in zip(result['ids'], result['embeddings'])}
        for j, rid in enumerate(batch_ids):
            v = emb_map.get(rid)
            if v is None:
                missing.append(rid)
                # leave as zeros; downstream filter handles
                continue
            embs[i+j] = np.asarray(v, dtype=np.float32)
            found += 1
        if i % 5000 == 0:
            print(f"  fetched {i+len(batch_ids):,}/{len(record_ids):,}  "
                  f"({(i+len(batch_ids))/(time.time()-started):.0f} rec/s)", flush=True)

    elapsed = time.time() - started
    print(f"\nFetched {found:,} embeddings in {elapsed:.1f}s", flush=True)
    if missing:
        print(f"  {len(missing)} records had no embedding in ChromaDB", flush=True)
        print(f"  first few missing: {missing[:5]}", flush=True)
        # Drop missing from output to keep alignment perfect
        keep_mask = np.array([1 if rid not in set(missing) else 0
                                for rid in record_ids], dtype=bool)
        embs = embs[keep_mask]
        record_ids = [rid for rid, k in zip(record_ids, keep_mask) if k]
        print(f"  Dropped {(~keep_mask).sum()} from output to maintain alignment", flush=True)
    print(f"Final embedding matrix: {embs.shape} ({embs.dtype})", flush=True)

    # Sanity: are they normalised? cosine clustering expects unit vectors
    norms = np.linalg.norm(embs, axis=1)
    print(f"  L2 norm distribution: mean={norms.mean():.4f}, "
          f"min={norms.min():.4f}, max={norms.max():.4f}", flush=True)
    if abs(norms.mean() - 1.0) > 0.01:
        print(f"  Re-normalising for cosine clustering...", flush=True)
        embs = embs / norms[:, np.newaxis]

    np.save(OUT_NPY, embs)
    OUT_IDS.write_text(json.dumps(record_ids))
    print(f"\nWrote {OUT_NPY}  ({OUT_NPY.stat().st_size:,} bytes)", flush=True)
    print(f"Wrote {OUT_IDS}", flush=True)


if __name__ == "__main__":
    main()
