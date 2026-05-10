#!/usr/bin/env python3
"""Stage 2 (transformer variant): NER with en_core_web_trf on GPU.

Single process + nlp.pipe with batched GPU inference. Higher accuracy
than en_core_web_sm at moderate runtime.
"""
import csv
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import spacy

ROOT = Path('/home/jeffzda/broadlearnings')
MD_DIR = ROOT / 'corpora/arena/marker_output'
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'

LABELS_OF_INTEREST = {'ORG', 'PRODUCT', 'EVENT', 'FAC', 'WORK_OF_ART'}
TABLE_RE = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL)
HTML_TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')

CHUNK_CHARS = 50_000     # split each doc into pieces this size before NER
BATCH_SIZE = 32          # nlp.pipe internal batch (transformers fed in batches)


def clean_for_ner(text):
    text = TABLE_RE.sub(' ', text)
    text = HTML_TAG_RE.sub(' ', text)
    return text


def chunk_doc(text, doc_id):
    """Yield (doc_id, chunk_offset, chunk_text) tuples."""
    cleaned = clean_for_ner(text)
    for start in range(0, len(cleaned), CHUNK_CHARS):
        yield (doc_id, start, cleaned[start:start + CHUNK_CHARS])


def main():
    print(f"Loading en_core_web_trf with GPU...", flush=True)
    spacy.prefer_gpu()
    nlp = spacy.load('en_core_web_trf', disable=['parser','attribute_ruler','lemmatizer','tagger'])
    print(f"Pipes: {nlp.pipe_names}", flush=True)

    md_files = sorted(MD_DIR.glob('*/*.rendered.md'))
    print(f"NER trf sweep: {len(md_files):,} files", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / 'ner_trf_candidates.csv'
    freq_path = OUT_DIR / 'ner_trf_candidate_frequencies.csv'

    surface_counts = Counter()
    surface_doc_counts = defaultdict(set)
    label_counts = Counter()
    n_total = 0

    # Build the chunk stream
    def chunk_iter():
        for md in md_files:
            doc_id = md.parent.name
            try:
                text = md.read_text(errors='ignore')
            except Exception as e:
                print(f"  skip {doc_id}: {e}", flush=True)
                continue
            for tup in chunk_doc(text, doc_id):
                yield tup

    # Build context tuples for nlp.pipe with as_tuples=True
    def context_iter():
        for doc_id, offset, chunk_text in chunk_iter():
            yield (chunk_text, (doc_id, offset))

    started = time.time()
    n_chunks_done = 0
    n_docs_seen = set()
    last_print = 0

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'label', 'surface', 'char_offset'])
        for doc, (doc_id, offset) in nlp.pipe(context_iter(), batch_size=BATCH_SIZE, as_tuples=True):
            n_chunks_done += 1
            n_docs_seen.add(doc_id)
            for ent in doc.ents:
                if ent.label_ not in LABELS_OF_INTEREST: continue
                surf = WS_RE.sub(' ', ent.text).strip()
                if len(surf) < 2 or len(surf) > 100: continue
                if not any(c.isupper() for c in surf): continue
                abs_offset = offset + ent.start_char
                w.writerow([doc_id, ent.label_, surf, abs_offset])
                surface_counts[surf] += 1
                surface_doc_counts[surf].add(doc_id)
                label_counts[ent.label_] += 1
                n_total += 1
            elapsed = time.time() - started
            if elapsed - last_print >= 10:
                rate = len(n_docs_seen) / elapsed if elapsed > 0 else 0
                eta = (len(md_files) - len(n_docs_seen)) / rate if rate > 0 else 0
                print(f"  [{len(n_docs_seen):>4}/{len(md_files)} docs, {n_chunks_done:>5} chunks]  "
                      f"{n_total:>10,} ents  {rate:.1f} docs/s  ETA={eta:.0f}s", flush=True)
                last_print = elapsed

    elapsed = time.time() - started
    print(f"\n=== DONE in {elapsed:.0f}s ===", flush=True)
    print(f"Total NER entities: {n_total:,}")
    print(f"Unique surfaces:    {len(surface_counts):,}")
    print(f"Label breakdown:")
    for l, n in label_counts.most_common():
        print(f"  {l:<12}  {n:>9,}")

    print(f"\nTop 20 surfaces:")
    for s, n in surface_counts.most_common(20):
        print(f"  {n:>5}× ({len(surface_doc_counts[s]):>3} docs)  {s}")

    with open(freq_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['surface', 'n_total_mentions', 'n_unique_docs'])
        for s, n in surface_counts.most_common():
            w.writerow([s, n, len(surface_doc_counts[s])])

    print(f"\nWrote {out_path}  ({out_path.stat().st_size:,} bytes)")
    print(f"Wrote {freq_path}  ({freq_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
