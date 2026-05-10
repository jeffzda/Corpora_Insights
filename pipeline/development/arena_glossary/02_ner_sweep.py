#!/usr/bin/env python3
"""Stage 2: SpaCy NER pass — parallelised across N workers.

Each worker loads en_core_web_sm once and processes a queue of docs.
Captures ORG / PRODUCT / EVENT / FAC / WORK_OF_ART entities.
"""
import argparse
import csv
import multiprocessing as mp
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
MD_DIR = ROOT / 'corpora/arena/marker_output'
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'

LABELS_OF_INTEREST = {'ORG', 'PRODUCT', 'EVENT', 'FAC', 'WORK_OF_ART'}
TABLE_RE = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL)
HTML_TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


def clean_for_ner(text):
    text = TABLE_RE.sub(' ', text)
    text = HTML_TAG_RE.sub(' ', text)
    return text


# Each worker loads its own SpaCy model (initializer pattern)
_NLP = None
def _init_worker(model_name):
    global _NLP
    import spacy
    _NLP = spacy.load(model_name, disable=['parser','attribute_ruler','lemmatizer','tagger'])


def process_doc(md_path_str):
    """Process one doc; return list of entity tuples."""
    md_path = Path(md_path_str)
    doc_id = md_path.parent.name
    try:
        text = md_path.read_text(errors='ignore')
    except Exception as e:
        return doc_id, [], str(e)
    cleaned = clean_for_ner(text)
    out = []
    CHUNK = 500_000
    err = None
    for start in range(0, len(cleaned), CHUNK):
        chunk_text = cleaned[start:start + CHUNK]
        try:
            doc = _NLP(chunk_text)
        except Exception as e:
            err = f"err@{start}: {e}"
            continue
        for ent in doc.ents:
            if ent.label_ not in LABELS_OF_INTEREST: continue
            surf = WS_RE.sub(' ', ent.text).strip()
            if len(surf) < 2 or len(surf) > 100: continue
            if not any(c.isupper() for c in surf): continue
            abs_offset = start + ent.start_char
            out.append((doc_id, ent.label_, surf, abs_offset))
    return doc_id, out, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=32)
    ap.add_argument('--model', default='en_core_web_sm')
    args = ap.parse_args()

    md_files = sorted(str(p) for p in MD_DIR.glob('*/*.rendered.md'))
    print(f"NER sweep: {len(md_files):,} files × {args.workers} workers (model={args.model})", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / 'ner_candidates.csv'
    freq_path = OUT_DIR / 'ner_candidate_frequencies.csv'

    surface_counts = Counter()
    surface_doc_counts = defaultdict(set)
    label_counts = Counter()
    n_total = 0
    n_done = 0

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'label', 'surface', 'char_offset'])

        with mp.Pool(args.workers, initializer=_init_worker, initargs=(args.model,)) as pool:
            import time
            started = time.time()
            for doc_id, ents, err in pool.imap_unordered(process_doc, md_files, chunksize=4):
                if err: print(f"  WARN {doc_id}: {err}", flush=True)
                for tup in ents:
                    w.writerow(tup)
                    surface_counts[tup[2]] += 1
                    surface_doc_counts[tup[2]].add(tup[0])
                    label_counts[tup[1]] += 1
                    n_total += 1
                n_done += 1
                if n_done % 50 == 0 or n_done == len(md_files):
                    el = time.time() - started
                    rate = n_done / el if el > 0 else 0
                    eta = (len(md_files) - n_done) / rate if rate > 0 else 0
                    print(f"  [{n_done:>4}/{len(md_files)}]  {n_total:>10,} ents  "
                          f"{rate:.1f} docs/s  ETA={eta:.0f}s", flush=True)

    print(f"\nTotal NER entities: {n_total:,}")
    print(f"Unique surfaces:    {len(surface_counts):,}")
    print(f"Label breakdown:")
    for l, n in label_counts.most_common():
        print(f"  {l:<12}  {n:>9,}")

    print(f"\nTop 20 NER surfaces:")
    for s, n in surface_counts.most_common(20):
        print(f"  {n:>5}× ({len(surface_doc_counts[s]):>3} docs)  {s}")

    with open(freq_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['surface', 'n_total_mentions', 'n_unique_docs'])
        for s, n in surface_counts.most_common():
            w.writerow([s, n, len(surface_doc_counts[s])])

    print(f"\nWrote:")
    print(f"  {out_path}  ({out_path.stat().st_size:,} bytes)")
    print(f"  {freq_path}  ({freq_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
