#!/usr/bin/env python3
"""Index extracted insight records into ChromaDB for semantic search.

Embeds the `narrative` field of every record using Qwen3-Embedding-4B
(same model used for the markdown corpus). Stores per-record metadata
for filtering: doc_id, record_id, kb_associated_project, kb_category,
significance, lesson, evidence, source_url, etc.

Usage:
    python -m pipeline.index_records --domain arena
    python -m pipeline.index_records --domain arena --collection arena_records_e3
    python -m pipeline.index_records --domain arena --resume

Resumable: skips records whose record_id is already in the collection.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from pipeline.rag import get_model, MAX_EMBED_CHARS, CHROMA_DIR

import chromadb

ROOT = Path(__file__).resolve().parents[1]


def get_records_collection(chroma_dir: Path, name: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"},
    )


def load_records(out_dir: Path):
    """Iterate (doc_id, record) pairs from per-doc JSONs."""
    files = sorted(p for p in out_dir.glob("doc_*.json") if not p.name.endswith(".meta.json"))
    print(f"  Found {len(files)} per-doc files")
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"  WARN: failed to load {f.name}: {e}", file=sys.stderr)
            continue
        for r in data.get("records", []):
            r["_doc_file"] = f.name
            yield r


def build_metadata(rec: dict) -> dict:
    """ChromaDB metadata supports str/int/float/bool only — flatten lists/None."""
    keys_str = (
        "doc_id", "id", "title", "source_title", "project_name",
        "kb_associated_project", "kb_category", "kb_document_type",
        "kb_publish_date", "kb_year", "kb_project_status",
        "lesson", "intervention", "evidence",
        "source_url", "project_page_url", "pdf_url", "markdown_path",
    )
    md = {}
    for k in keys_str:
        v = rec.get(k)
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            md[k] = v.strip()
        elif isinstance(v, (int, float, bool)):
            md[k] = v
    sig = rec.get("significance")
    if isinstance(sig, int):
        md["significance"] = sig
    pages = rec.get("pages") or rec.get("source_pages")
    if isinstance(pages, list) and pages:
        md["pages"] = ",".join(str(p) for p in pages if isinstance(p, int))
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="arena")
    ap.add_argument("--records-dir", default=None,
                    help="Default: corpora/<domain>/output/per_doc")
    ap.add_argument("--chroma-dir", default=None,
                    help="Default: corpora/.chromadb")
    ap.add_argument("--collection", default=None,
                    help="Default: <domain>_records_e3")
    ap.add_argument("--batch-size", type=int, default=8,
                    help="Embedding batch size; cap at 8 to bound peak VRAM")
    ap.add_argument("--upsert-batch", type=int, default=512,
                    help="ChromaDB upsert batch size")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true",
                    help="Skip record_ids already in the collection")
    args = ap.parse_args()

    records_dir = Path(args.records_dir) if args.records_dir else (
        ROOT / "corpora" / args.domain / "output" / "per_doc"
    )
    chroma_dir = Path(args.chroma_dir) if args.chroma_dir else CHROMA_DIR
    collection_name = args.collection or f"{args.domain}_records_e3"

    print(f"records: {records_dir}")
    print(f"chroma:  {chroma_dir}/{collection_name}")
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Load records
    print("Loading records...")
    records = list(load_records(records_dir))
    print(f"  Loaded {len(records)} records")
    if args.limit:
        records = records[: args.limit]
        print(f"  Limited to {len(records)}")

    # Set up collection + resume
    collection = get_records_collection(chroma_dir, collection_name)
    existing_ids = set()
    if args.resume:
        # Stream existing ids in pages of 5000
        offset = 0
        while True:
            page = collection.get(limit=5000, offset=offset, include=[])
            ids = page.get("ids", [])
            if not ids: break
            existing_ids.update(ids)
            offset += len(ids)
        print(f"  Already indexed: {len(existing_ids)}")

    # Filter to records that need embedding
    to_index = []
    skipped = 0
    no_id = 0
    for r in records:
        rec_id = r.get("id")
        if not rec_id:
            no_id += 1
            continue
        if rec_id in existing_ids:
            skipped += 1
            continue
        narrative = (r.get("narrative") or "").strip()
        if not narrative:
            continue
        to_index.append({
            "id": rec_id,
            "narrative": narrative,
            "metadata": build_metadata(r),
        })
    print(f"  To index: {len(to_index)} ({skipped} skip via resume, {no_id} no id)")

    if not to_index:
        print("Nothing to index. Done.")
        return

    # Load model
    model = get_model()

    import torch
    t_start = time.time()
    upsert_buf_ids = []
    upsert_buf_emb = []
    upsert_buf_doc = []
    upsert_buf_meta = []
    embedded = 0

    BATCH = args.batch_size
    UPSERT_BATCH = args.upsert_batch

    for i in range(0, len(to_index), BATCH):
        batch = to_index[i:i + BATCH]
        texts = [r["narrative"][:MAX_EMBED_CHARS] for r in batch]
        embeddings = model.encode(
            texts, show_progress_bar=False,
            batch_size=len(texts), convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()
        for r, emb in zip(batch, embeddings):
            upsert_buf_ids.append(r["id"])
            upsert_buf_emb.append(emb)
            upsert_buf_doc.append(r["narrative"])
            upsert_buf_meta.append(r["metadata"])
        embedded += len(batch)

        if len(upsert_buf_ids) >= UPSERT_BATCH:
            collection.upsert(
                ids=upsert_buf_ids, embeddings=upsert_buf_emb,
                documents=upsert_buf_doc, metadatas=upsert_buf_meta,
            )
            upsert_buf_ids.clear(); upsert_buf_emb.clear()
            upsert_buf_doc.clear(); upsert_buf_meta.clear()

        if embedded % 1024 == 0 or embedded >= len(to_index):
            elapsed = time.time() - t_start
            rate = embedded / max(elapsed, 0.001)
            remaining = (len(to_index) - embedded) / max(rate, 0.001)
            torch.cuda.empty_cache()
            print(f"  {embedded:,}/{len(to_index):,}  "
                  f"{rate:.0f} rec/s  ETA {remaining/60:.1f}m", flush=True)

    # Flush remainder
    if upsert_buf_ids:
        collection.upsert(
            ids=upsert_buf_ids, embeddings=upsert_buf_emb,
            documents=upsert_buf_doc, metadatas=upsert_buf_meta,
        )

    elapsed = time.time() - t_start
    print(f"\nDone. {embedded:,} records embedded in {elapsed/60:.1f} min "
          f"({embedded/elapsed:.0f} rec/s)")
    print(f"Collection: {collection_name}, total docs: {collection.count()}")


if __name__ == "__main__":
    main()
