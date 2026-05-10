#!/usr/bin/env python3
"""Phase 2: embed clustering input records using Qwen3-Embedding-4B.

For each record, embed the concatenation of narrative + evidence (which is
what we used elsewhere). Save embeddings as a numpy array aligned with the
record_ids in filter_input.jsonl.
"""
import json
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path('/home/jeffzda/broadlearnings')
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'
INPUT = OUT_DIR / 'filter_input.jsonl'
OUT_NPY = OUT_DIR / 'embeddings.npy'
OUT_IDS = OUT_DIR / 'embedding_record_ids.json'

MODEL = 'Qwen/Qwen3-Embedding-4B'  # 4B params, 2560-dim; matches RAG pipeline embedding
BATCH_SIZE = 16  # bf16 + 4000-char cap fits comfortably on 16GB VRAM
MAX_EMBED_CHARS = 4000  # matches pipeline/rag.py — bounds attention memory O(N²)


def main():
    print(f"Loading {INPUT}...", flush=True)
    rows = [json.loads(line) for line in open(INPUT)]
    record_ids = [r['record_id'] for r in rows]
    texts = []
    for r in rows:
        n = (r['narrative'] or '').strip()
        e = (r['evidence'] or '').strip()
        # Combine — both convey signal
        texts.append(f"{n}\n\n{e}" if e and e != n else n)
    print(f"  {len(rows):,} records to embed", flush=True)

    print(f"Loading {MODEL} on GPU in bfloat16 (matches pipeline/rag.py)...", flush=True)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(
        MODEL, device='cuda',
        model_kwargs={'torch_dtype': 'bfloat16'},
    )
    # Cap text length to 4000 chars (~1000 tokens) per pipeline/rag.py rationale
    texts = [t[:MAX_EMBED_CHARS] for t in texts]

    started = time.time()
    embs = model.encode(
        texts, batch_size=BATCH_SIZE, show_progress_bar=True,
        normalize_embeddings=True, convert_to_numpy=True
    )
    elapsed = time.time() - started
    print(f"\nEmbedded {len(rows):,} records in {elapsed:.0f}s ({len(rows)/elapsed:.1f} rec/s)", flush=True)
    print(f"Embeddings shape: {embs.shape}, dtype: {embs.dtype}", flush=True)

    # Save
    embs = embs.astype(np.float32)
    np.save(OUT_NPY, embs)
    OUT_IDS.write_text(json.dumps(record_ids))
    print(f"\nWrote {OUT_NPY}  ({OUT_NPY.stat().st_size:,} bytes)", flush=True)
    print(f"Wrote {OUT_IDS}  ({OUT_IDS.stat().st_size:,} bytes)", flush=True)


if __name__ == "__main__":
    main()
