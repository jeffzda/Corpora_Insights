#!/usr/bin/env python3
"""Cross-corpus RAG search over ingested markdown documents.

Chunks markdown by sections, embeds with sentence-transformers on GPU,
stores in ChromaDB, and provides semantic search with source citations.

Usage:
    # Index corpora
    python -m pipeline.rag index --corpus arena anao pc

    # Search
    python -m pipeline.rag search "renewable energy procurement"
    python -m pipeline.rag search "audit findings on NDIS" --corpus anao
    python -m pipeline.rag search "carbon capture" --top-k 10
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

from pipeline.chunk import chunk_markdown as _chunk_structured

ROOT = Path(__file__).resolve().parents[1]
CORPORA_DIR = ROOT / "corpora"
CHROMA_DIR = CORPORA_DIR / ".chromadb"
COLLECTION_NAME = "broadlearnings"

# Embedding model: top MTEB retrieval scorer, 32k context, 1024-dim default
# Requires: transformers>=4.51.0, sentence-transformers>=2.7.0
MODEL_NAME = "Qwen/Qwen3-Embedding-4B"

# Cap chunk length at embed time to bound attention memory (O(N²)).
# Qwen3-Embedding-4B in bf16 on a 16GB card: 8000 chars (~2k tokens)
# blows peak VRAM once per-chunk activation memory stacks with the
# 8GB static model. 4000 chars (~1k tokens) leaves enough headroom.
MAX_EMBED_CHARS = 4000

# Legacy chunking parameters (kept for reference; no longer used)
# CHUNK_SIZE = 1500
# CHUNK_OVERLAP = 200
# MIN_CHUNK_SIZE = 100


def get_model() -> SentenceTransformer:
    """Load embedding model onto GPU.

    Load weights in bfloat16 — Qwen3-Embedding-4B at fp32 is ~16GB of
    parameters alone, which doesn't fit on a 16GB card alongside any
    activation memory. bf16 is the native training dtype.
    """
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(
        MODEL_NAME, device="cuda",
        model_kwargs={"torch_dtype": "bfloat16"},
    )
    dim = model.get_embedding_dimension()
    print(f"  Dimension: {dim}, Max seq: {model.max_seq_length}")
    return model


def get_collection(chroma_dir: Path | None = None,
                   collection_name: str | None = None) -> chromadb.Collection:
    """Get or create the ChromaDB collection."""
    client = chromadb.PersistentClient(path=str(chroma_dir or CHROMA_DIR))
    return client.get_or_create_collection(
        name=collection_name or COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_markdown(text: str, source_file: str) -> list[dict]:
    """Split markdown into paragraph-level chunks using the universal chunker.

    Uses pipeline.chunk for structure-aware paragraph-level chunking with
    synthetic IDs, then adapts the output to the RAG metadata format.

    Each chunk carries:
      - text: the chunk content (with hierarchical context prefix)
      - section: nearest heading above this chunk
      - page: nearest page marker above this chunk
      - paragraph_id: synthetic paragraph identifier (e.g. "3.1.2")
      - source: the source filename
    """
    structured_chunks = _chunk_structured(text, source_file)

    rag_chunks = []
    for c in structured_chunks:
        # Build section from the chunk's hierarchical context
        section_parts = []
        if c["chapter_title"]:
            section_parts.append(c["chapter_title"])
        if c["section_title"]:
            section_parts.append(c["section_title"])
        section = " > ".join(section_parts)

        rag_chunks.append({
            "text": c["text"],
            "section": section,
            "page": c["page_number"],
            "paragraph_id": c["paragraph_id"],
            "source": source_file,
            "role": c.get("role", ""),
        })

    return rag_chunks


def extract_doc_title(text: str, filename: str) -> str:
    """Extract document title from markdown content."""
    # Look for first substantial heading
    for line in text.split("\n")[:30]:
        m = re.match(r"^#\s+(.+)", line)
        if m:
            title = m.group(1).strip()
            if len(title) > 5 and title.lower() != "source pdf":
                return title
    return filename.replace(".md", "").replace("-", " ").replace("_", " ").title()


def _chunk_one_file(filepath: str) -> list[dict]:
    """Chunk a single markdown file (runs in worker process).

    Returns list of dicts with keys: text, section, page, paragraph_id,
    source, role, doc_title.
    """
    path = Path(filepath)
    text = path.read_text(encoding="utf-8", errors="replace")
    doc_title = extract_doc_title(text, path.name)
    chunks = chunk_markdown(text, path.name)
    for c in chunks:
        c["doc_title"] = doc_title
    return chunks


def index_corpus(corpus_name: str, model: SentenceTransformer,
                 collection: chromadb.Collection, force: bool = False,
                 workers: int = 1, source_glob: str | None = None):
    """Index all markdown files from a corpus into ChromaDB.

    source_glob: optional path (absolute or relative to repo root) with glob
    syntax, e.g. "corpora/arena/marker_output/*/*.rendered.md". When omitted,
    falls back to the flat layout corpora/<name>/markdown/*.md.
    """
    if source_glob:
        import glob as _glob
        base = source_glob if os.path.isabs(source_glob) else str(ROOT / source_glob)
        md_files = sorted(Path(p) for p in _glob.glob(base, recursive=True))
        if not md_files:
            print(f"  No files matching {source_glob} — skipping")
            return
    else:
        md_dir = CORPORA_DIR / corpus_name / "markdown"
        if not md_dir.exists():
            print(f"  No markdown directory at {md_dir} — skipping")
            return

        md_files = sorted(md_dir.glob("*.md"))
        if not md_files:
            print(f"  No markdown files in {md_dir} — skipping")
            return

    # Check what's already indexed for this corpus
    if not force:
        existing_sources = set()
        offset = 0
        page = 10000
        while True:
            existing = collection.get(
                where={"corpus": corpus_name},
                include=["metadatas"],
                limit=page,
                offset=offset,
            )
            metas = existing["metadatas"] if existing else None
            if not metas:
                break
            for meta in metas:
                existing_sources.add(meta.get("source", ""))
            if len(metas) < page:
                break
            offset += page
        indexed_files = {f.name for f in md_files} & existing_sources
        md_files = [f for f in md_files if f.name not in existing_sources]
        if indexed_files:
            print(f"  Skipping {len(indexed_files)} already-indexed files")

    if not md_files:
        print(f"  All files already indexed for {corpus_name}")
        return

    print(f"  Chunking {len(md_files)} markdown files from {corpus_name} "
          f"({workers} workers)...")

    # Phase 1: Parallel chunking (CPU-bound)
    t0 = time.time()
    all_chunks = []  # list of (filename, chunks)

    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            file_paths = [str(f) for f in md_files]
            for i, chunks in enumerate(pool.map(_chunk_one_file, file_paths,
                                                chunksize=32)):
                filename = md_files[i].name
                all_chunks.append((filename, chunks))
                if (i + 1) % 500 == 0:
                    n_chunks = sum(len(c) for _, c in all_chunks)
                    print(f"    chunked {i+1}/{len(md_files)} "
                          f"({n_chunks:,} chunks)")
    else:
        for i, md_file in enumerate(md_files):
            chunks = _chunk_one_file(str(md_file))
            all_chunks.append((md_file.name, chunks))
            if (i + 1) % 500 == 0:
                n_chunks = sum(len(c) for _, c in all_chunks)
                print(f"    chunked {i+1}/{len(md_files)} "
                      f"({n_chunks:,} chunks)")

    total_chunks = sum(len(c) for _, c in all_chunks)
    chunk_time = time.time() - t0
    print(f"  Chunked: {total_chunks:,} chunks from {len(md_files)} docs "
          f"in {chunk_time:.1f}s")

    # Phase 2: Batch embedding on GPU + ChromaDB upsert
    print(f"  Embedding {total_chunks:,} chunks...")
    t1 = time.time()

    batch_ids = []
    batch_texts = []
    batch_metas = []
    batch_size = 256
    embedded_count = 0

    for filename, chunks in all_chunks:
        for j, chunk in enumerate(chunks):
            # Namespaced, human-readable id so per-corpus DBs can be merged
            # later without collisions.
            chunk_id = f"{corpus_name}:{filename}:{j}"

            batch_ids.append(chunk_id)
            batch_texts.append(chunk["text"])
            batch_metas.append({
                "corpus": corpus_name,
                "source": filename,
                "doc_title": chunk.get("doc_title", ""),
                "section": chunk["section"],
                "page": chunk["page"],
                "paragraph_id": chunk.get("paragraph_id", ""),
                "chunk_index": j,
                "role": chunk.get("role", ""),
            })

            if len(batch_texts) >= batch_size:
                embed_inputs = [t[:MAX_EMBED_CHARS] for t in batch_texts]
                embeddings = model.encode(
                    embed_inputs, show_progress_bar=False,
                    batch_size=4,
                    normalize_embeddings=True).tolist()
                collection.upsert(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_texts,
                    metadatas=batch_metas,
                )
                embedded_count += len(batch_texts)
                batch_ids, batch_texts, batch_metas = [], [], []

                # Return unused VRAM each outer batch — long chunks can
                # spike activation memory and the allocator otherwise
                # fragments over a multi-hour run.
                import torch
                torch.cuda.empty_cache()

                if embedded_count % 2048 == 0:
                    elapsed = time.time() - t1
                    rate = embedded_count / elapsed
                    remaining = (total_chunks - embedded_count) / rate
                    print(f"    embedded {embedded_count:,}/{total_chunks:,} "
                          f"({rate:.0f} chunks/s, ~{remaining:.0f}s remaining)")

    # Flush remaining
    if batch_texts:
        embed_inputs = [t[:MAX_EMBED_CHARS] for t in batch_texts]
        embeddings = model.encode(
            embed_inputs, show_progress_bar=False,
            batch_size=8,
            normalize_embeddings=True).tolist()
        collection.upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metas,
        )
        embedded_count += len(batch_texts)

    embed_time = time.time() - t1
    total_time = time.time() - t0
    print(f"  {corpus_name}: {total_chunks:,} chunks from {len(md_files)} docs")
    print(f"    Chunk: {chunk_time:.1f}s, Embed: {embed_time:.1f}s, "
          f"Total: {total_time:.1f}s")


def generalise_query(query: str) -> list[str]:
    """Expand a user query into corpus-aware search angles via LLM.

    Returns the original query plus reformulations that target the vocabulary
    of each corpus type: technical project reports (ARENA), performance audits
    (ANAO), and economic policy analysis (PC). This ensures the generalised
    angles bridge into the distinct terminology each corpus uses.
    """
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""You are helping a search system retrieve relevant passages from three Australian government document corpora:

1. ARENA (Australian Renewable Energy Agency) — technical project reports, knowledge sharing, commercialisation studies, industry surveys. Uses vocabulary like: project outcomes, technology readiness, cost reduction, deployment barriers, knowledge gaps.

2. ANAO (Australian National Audit Office) — performance audits of government programs. Uses vocabulary like: program administration, compliance, performance measurement, value for money, audit findings, entity governance, risk management.

3. PC (Productivity Commission) — economic policy analysis, public inquiries, research reports. Uses vocabulary like: cost-effectiveness, market design, regulatory frameworks, economic welfare, abatement costs, productivity impacts, policy instruments.

Given this search query:
"{query}"

Generate exactly 5 alternative search queries. Each must target a DIFFERENT corpus vocabulary:
1. Rephrase using ARENA technical/project language
2. Rephrase using ANAO audit/compliance/administration language
3. Rephrase using PC economic analysis/policy instrument language
4. Broaden to the general class of issue using cross-cutting government language
5. Narrow to a specific concrete aspect the user likely cares about

Return ONLY a JSON array of 5 strings. No explanation, no markdown fencing."""}],
    )
    text = resp.content[0].text.strip()
    # Strip markdown fencing if present despite instruction
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        alternatives = json.loads(text)
        if isinstance(alternatives, list):
            return [query] + [str(q) for q in alternatives]
    except json.JSONDecodeError:
        pass
    return [query]


def _discover_corpora(collection: chromadb.Collection) -> list[str]:
    """Return the list of distinct corpus names in the collection."""
    # Sample metadata to find corpus values — peek returns up to limit items
    sample = collection.peek(limit=1)
    if not sample["metadatas"]:
        return []
    # Get all distinct corpora by querying each known corpus dir
    corpora = []
    for d in sorted(CORPORA_DIR.iterdir()):
        if d.is_dir() and (d / "markdown").exists():
            try:
                result = collection.get(
                    where={"corpus": d.name}, include=[], limit=1)
                if result["ids"]:
                    corpora.append(d.name)
            except Exception:
                pass
    return corpora


def _query_embeddings(query_embeddings: list[list[float]],
                      collection: chromadb.Collection,
                      n_results: int,
                      where: dict | None = None) -> dict[str, dict]:
    """Run multiple query embeddings against the collection, merge by best score."""
    seen: dict[str, dict] = {}
    for q_emb in query_embeddings:
        results = collection.query(
            query_embeddings=[q_emb],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            score = 1 - results["distances"][0][i]
            if chunk_id not in seen or score > seen[chunk_id]["score"]:
                meta = results["metadatas"][0][i]
                seen[chunk_id] = {
                    "text": results["documents"][0][i],
                    "corpus": meta["corpus"],
                    "source": meta["source"],
                    "doc_title": meta["doc_title"],
                    "section": meta["section"],
                    "page": meta["page"],
                    "paragraph_id": meta.get("paragraph_id", ""),
                    "role": meta.get("role", ""),
                    "score": score,
                }
    return seen


def _build_where(corpus_filter: str | None = None,
                 role_filter: str | None = None) -> dict | None:
    """Build a ChromaDB where clause from optional filters."""
    clauses = []
    if corpus_filter:
        clauses.append({"corpus": corpus_filter})
    if role_filter:
        clauses.append({"role": role_filter})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search(query: str, collection: chromadb.Collection,
           model: SentenceTransformer, top_k: int = 5,
           corpus_filter: str | None = None,
           role_filter: str | None = None,
           generalise: bool = False) -> list[dict]:
    """Search across corpora and return cited results.

    If generalise=True, expands the query into multiple angles via LLM,
    runs each against the index, and merges results by best score.

    role_filter limits results to chunks with a specific role
    (e.g. "recommendation", "overview", "key_finding").

    When no corpus_filter is set, retrieves top_k per corpus independently
    to guarantee balanced cross-corpus coverage regardless of corpus size
    or vocabulary density.
    """
    if generalise:
        queries = generalise_query(query)
        print(f"  Query generalisation ({len(queries)} angles):")
        for i, q in enumerate(queries):
            label = "original" if i == 0 else f"angle {i}"
            print(f"    [{label}] {q}")
    else:
        queries = [query]

    # Embed all queries at once
    query_embeddings = model.encode(queries, normalize_embeddings=True).tolist()

    per_query_k = top_k * 3 if generalise else top_k

    if corpus_filter or role_filter:
        where = _build_where(corpus_filter, role_filter)
        seen = _query_embeddings(
            query_embeddings, collection, per_query_k,
            where=where)
        hits = sorted(seen.values(), key=lambda h: h["score"], reverse=True)
        return hits[:top_k]

    # Cross-corpus: retrieve top_k per corpus, then merge and rank globally.
    corpora = _discover_corpora(collection)
    if not corpora:
        return []

    all_seen: dict[str, dict] = {}
    for corpus_name in corpora:
        where = _build_where(corpus_name, role_filter)
        corpus_seen = _query_embeddings(
            query_embeddings, collection, per_query_k,
            where=where)
        # Take top_k from this corpus
        corpus_hits = sorted(
            corpus_seen.items(), key=lambda kv: kv[1]["score"], reverse=True
        )[:top_k]
        for chunk_id, hit in corpus_hits:
            if chunk_id not in all_seen or hit["score"] > all_seen[chunk_id]["score"]:
                all_seen[chunk_id] = hit

    hits = sorted(all_seen.values(), key=lambda h: h["score"], reverse=True)
    return hits[:top_k]


def fetch_document_context(
    hits: list[dict],
    collection: chromadb.Collection,
) -> dict[tuple[str, str], list[dict]]:
    """Fetch role-tagged chunks from documents that contributed search results.

    For each unique (corpus, source) in the hits, retrieves chunks with
    non-empty role (overview, recommendation, key_finding, etc.) from
    that document. Returns a dict keyed by (corpus, source) with lists
    of context chunks sorted by chunk_index.
    """
    context: dict[tuple[str, str], list[dict]] = {}
    seen_docs: set[tuple[str, str]] = set()

    for hit in hits:
        doc_key = (hit["corpus"], hit["source"])
        if doc_key in seen_docs:
            continue
        seen_docs.add(doc_key)

        try:
            results = collection.get(
                where={"$and": [
                    {"corpus": hit["corpus"]},
                    {"source": hit["source"]},
                    {"role": {"$ne": ""}},
                ]},
                include=["documents", "metadatas"],
            )
        except Exception:
            continue

        if not results["ids"]:
            continue

        doc_chunks = []
        for i in range(len(results["ids"])):
            meta = results["metadatas"][i]
            doc_chunks.append({
                "text": results["documents"][i],
                "role": meta.get("role", ""),
                "section": meta.get("section", ""),
                "paragraph_id": meta.get("paragraph_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
            })

        doc_chunks.sort(key=lambda c: c["chunk_index"])
        context[doc_key] = doc_chunks

    return context


def format_results(hits: list[dict], query: str,
                    doc_context: dict[tuple[str, str], list[dict]] | None = None,
                    ) -> str:
    """Format search results for display.

    If doc_context is provided, appends document-level context (overview,
    recommendations, key findings) for each hit's source document.
    """
    if not hits:
        return "No results found."

    lines = [f'Search: "{query}"', f"Results: {len(hits)}", ""]

    # Track which documents we've already shown context for
    shown_context: set[tuple[str, str]] = set()

    for i, hit in enumerate(hits, 1):
        lines.append(f"{'='*70}")
        lines.append(f"[{i}] {hit['doc_title']}")
        pid = hit.get('paragraph_id', '')
        pid_str = f"  |  §{pid}" if pid else ""
        role = hit.get('role', '')
        role_str = f"  |  Role: {role}" if role else ""
        lines.append(f"    Corpus: {hit['corpus'].upper()}  |  "
                      f"Source: {hit['source']}  |  "
                      f"Page: {hit['page'] or '?'}{pid_str}{role_str}  |  "
                      f"Score: {hit['score']:.3f}")
        if hit["section"]:
            lines.append(f"    Section: {hit['section']}")
        lines.append("")
        # Show text preview (first 500 chars)
        preview = hit["text"][:500]
        if len(hit["text"]) > 500:
            preview += "..."
        for line in preview.split("\n"):
            lines.append(f"    {line}")
        lines.append("")

        # Show document context if available and not already shown
        if doc_context:
            doc_key = (hit["corpus"], hit["source"])
            if doc_key in doc_context and doc_key not in shown_context:
                shown_context.add(doc_key)
                ctx_chunks = doc_context[doc_key]
                # Group by role
                by_role: dict[str, list[dict]] = {}
                for c in ctx_chunks:
                    r = c["role"]
                    by_role.setdefault(r, []).append(c)
                lines.append(f"    --- Document context ---")
                for ctx_role, ctx_list in by_role.items():
                    label = ctx_role.replace("_", " ").title()
                    lines.append(f"    [{label}]")
                    for c in ctx_list[:3]:  # cap at 3 chunks per role
                        preview = c["text"][:300]
                        if len(c["text"]) > 300:
                            preview += "..."
                        for ln in preview.split("\n"):
                            lines.append(f"      {ln}")
                    if len(ctx_list) > 3:
                        lines.append(f"      ... +{len(ctx_list)-3} more")
                lines.append("")

    return "\n".join(lines)


def cmd_index(args):
    """Index command."""
    model = get_model()
    chroma_dir = Path(args.chroma_dir) if args.chroma_dir else None
    collection = get_collection(chroma_dir=chroma_dir,
                                collection_name=args.collection)

    corpora = args.corpus
    if not corpora:
        # Auto-discover corpora with markdown dirs
        corpora = [d.name for d in sorted(CORPORA_DIR.iterdir())
                   if d.is_dir() and (d / "markdown").exists()]
        print(f"Auto-discovered corpora: {', '.join(corpora)}")

    workers = getattr(args, 'workers', 1)
    source_glob = getattr(args, 'source_glob', None)
    for corpus in corpora:
        print(f"\n--- {corpus.upper()} ---")
        index_corpus(corpus, model, collection, force=args.force,
                     workers=workers, source_glob=source_glob)

    # Summary
    total = collection.count()
    print(f"\nTotal chunks in index: {total:,}")


def cmd_search(args):
    """Search command."""
    model = get_model()
    chroma_dir = Path(args.chroma_dir) if getattr(args, "chroma_dir", None) else None
    collection = get_collection(chroma_dir=chroma_dir,
                                collection_name=getattr(args, "collection", None))

    total = collection.count()
    if total == 0:
        print("Index is empty. Run: python -m pipeline.rag index")
        return

    hits = search(args.query, collection, model,
                  top_k=args.top_k, corpus_filter=args.corpus,
                  role_filter=args.role,
                  generalise=args.generalise)

    doc_context = None
    if args.context:
        doc_context = fetch_document_context(hits, collection)

    print(format_results(hits, args.query, doc_context=doc_context))


def cmd_interactive(args):
    """Interactive search REPL."""
    model = get_model()
    collection = get_collection()

    total = collection.count()
    if total == 0:
        print("Index is empty. Run: python -m pipeline.rag index")
        return

    print(f"\nBroad Learnings — Cross-Corpus Search")
    print(f"Index: {total:,} chunks")
    print(f"Prefixes: @corpus to filter corpus, %role to filter role")
    print(f"Type a query, or 'quit' to exit.\n")

    while True:
        try:
            query = input("search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query or query.lower() in ("quit", "exit", "q"):
            break

        # Parse @corpus and %role prefixes
        corpus_filter = None
        role_filter = args.role
        tokens = query.split()
        remaining = []
        for token in tokens:
            if token.startswith("@"):
                corpus_filter = token[1:]
            elif token.startswith("%"):
                role_filter = token[1:]
            else:
                remaining.append(token)
        query = " ".join(remaining)
        if not query:
            print("Usage: [@corpus] [%role] your query")
            continue

        hits = search(query, collection, model,
                      top_k=args.top_k, corpus_filter=corpus_filter,
                      role_filter=role_filter,
                      generalise=args.generalise)

        doc_context = None
        if args.context:
            doc_context = fetch_document_context(hits, collection)

        print(format_results(hits, query, doc_context=doc_context))


def cmd_stats(args):
    """Show index statistics."""
    collection = get_collection()
    total = collection.count()
    print(f"Total chunks: {total:,}")

    if total > 0:
        # Get corpus breakdown
        for corpus_name in sorted(set(
            d.name for d in CORPORA_DIR.iterdir()
            if d.is_dir() and (d / "markdown").exists()
        )):
            result = collection.get(
                where={"corpus": corpus_name},
                include=[],
            )
            count = len(result["ids"]) if result["ids"] else 0
            if count > 0:
                print(f"  {corpus_name:>10}: {count:>8,} chunks")


def main():
    parser = argparse.ArgumentParser(
        description="Cross-corpus RAG search over government documents")
    sub = parser.add_subparsers(dest="command")

    # Index
    idx = sub.add_parser("index", help="Index markdown corpora")
    idx.add_argument("--corpus", nargs="*",
                     help="Corpus names to index (default: all with markdown)")
    idx.add_argument("--force", action="store_true",
                     help="Re-index even if already indexed")
    idx.add_argument("--workers", type=int, default=1,
                     help="Parallel workers for chunking (default: 1)")
    idx.add_argument("--source-glob", default=None,
                     help="Override source file location with a glob pattern "
                     "(e.g. corpora/arena/marker_output/*/*.rendered.md). "
                     "Defaults to corpora/<corpus>/markdown/*.md.")
    idx.add_argument("--chroma-dir", default=None,
                     help="ChromaDB directory to index into "
                     "(default: corpora/.chromadb)")
    idx.add_argument("--collection", default=None,
                     help=f"Collection name (default: {COLLECTION_NAME})")
    idx.set_defaults(func=cmd_index)

    # Search
    srch = sub.add_parser("search", help="Search across corpora")
    srch.add_argument("query", help="Search query")
    srch.add_argument("--corpus", help="Filter to single corpus")
    srch.add_argument("--role", help="Filter to chunks with specific role "
                      "(e.g. recommendation, overview, key_finding, conclusion)")
    srch.add_argument("--context", action="store_true",
                      help="Show document-level context (overview, recommendations) "
                      "alongside each hit")
    srch.add_argument("--top-k", type=int, default=5,
                      help="Number of results (default: 5)")
    srch.add_argument("--generalise", action="store_true",
                      help="Expand query into multiple angles via LLM before retrieval")
    srch.add_argument("--collection", default=None,
                      help="Override collection name (defaults to COLLECTION_NAME)")
    srch.set_defaults(func=cmd_search)

    # Interactive
    inter = sub.add_parser("interactive", help="Interactive search REPL")
    inter.add_argument("--role", help="Default role filter (override per-query with %%role)")
    inter.add_argument("--context", action="store_true",
                       help="Show document-level context alongside hits")
    inter.add_argument("--top-k", type=int, default=5,
                       help="Number of results per query (default: 5)")
    inter.add_argument("--generalise", action="store_true",
                       help="Expand queries into multiple angles via LLM before retrieval")
    inter.set_defaults(func=cmd_interactive)

    # Stats
    st = sub.add_parser("stats", help="Show index statistics")
    st.set_defaults(func=cmd_stats)

    # Allow query-side commands to point at an alternate chroma dir
    # (e.g. a snapshot taken during an ongoing index run).
    for p in (srch, inter, st):
        p.add_argument("--chroma-dir", default=None,
                       help="Path to an alternate ChromaDB directory "
                       "(e.g. a snapshot). Defaults to the live index.")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if getattr(args, "chroma_dir", None):
        global CHROMA_DIR
        CHROMA_DIR = Path(args.chroma_dir)

    args.func(args)


if __name__ == "__main__":
    main()
