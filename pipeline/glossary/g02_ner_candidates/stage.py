"""Stage g02 — SpaCy NER candidate sweep.

Generalises:
    pipeline/development/arena_glossary/02_ner_sweep.py
    pipeline/development/arena_glossary/02b_ner_sweep_trf.py

Outputs:
    output_dir/ner_candidates.csv             (sm)  or
    output_dir/ner_trf_candidates.csv         (trf)
    output_dir/ner_candidate_frequencies.csv  (or trf variant)

Domain config (domain.yaml glossary.candidate / glossary.ner):
    glossary.candidate.markdown_dir, markdown_glob, doc_id_strategy
    glossary.ner.spacy_model        e.g. en_core_web_sm
    glossary.ner.transformer_model  e.g. en_core_web_trf
    glossary.ner.workers            int, default 4
    glossary.ner.labels             list[str], default ORG/PRODUCT/EVENT/FAC/WORK_OF_ART
    glossary.ner.output_dir
"""
from __future__ import annotations
import argparse
import csv
import multiprocessing as mp
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve, derive_doc_id, iter_markdown


TABLE_RE = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL)
HTML_TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')

DEFAULT_LABELS = {'ORG', 'PRODUCT', 'EVENT', 'FAC', 'WORK_OF_ART'}

_NLP = None
_LABELS: set[str] = set()
_STRATEGY = 'parent_name'


def _init_worker(model_name: str, labels: list[str], strategy: str):
    global _NLP, _LABELS, _STRATEGY
    import spacy
    _NLP = spacy.load(model_name, disable=['parser', 'attribute_ruler', 'lemmatizer', 'tagger'])
    _LABELS = set(labels)
    _STRATEGY = strategy


def _clean(text: str) -> str:
    text = TABLE_RE.sub(' ', text)
    text = HTML_TAG_RE.sub(' ', text)
    return text


def _process_doc(md_path_str: str):
    md = Path(md_path_str)
    doc_id = derive_doc_id(md, _STRATEGY)
    try:
        text = md.read_text(errors='ignore')
    except Exception as e:
        return doc_id, [], str(e)
    cleaned = _clean(text)
    out = []
    CHUNK = 500_000
    err = None
    for start in range(0, len(cleaned), CHUNK):
        chunk = cleaned[start:start + CHUNK]
        try:
            doc = _NLP(chunk)
        except Exception as e:
            err = f"err@{start}: {e}"
            continue
        for ent in doc.ents:
            if ent.label_ not in _LABELS:
                continue
            surf = WS_RE.sub(' ', ent.text).strip()
            if len(surf) < 2 or len(surf) > 100:
                continue
            if not any(c.isupper() for c in surf):
                continue
            abs_offset = start + ent.start_char
            out.append((doc_id, ent.label_, surf, abs_offset))
    return doc_id, out, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    ap.add_argument('--variant', choices=['sm', 'trf'], default='sm',
                    help='sm = en_core_web_sm; trf = en_core_web_trf (slower, better)')
    ap.add_argument('--workers', type=int, default=None)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    c = (cfg.glossary.get('candidate') or {})
    n = (cfg.glossary.get('ner') or {})

    md_dir = resolve(c.get('markdown_dir') or '')
    md_glob = c.get('markdown_glob', '*/*.rendered.md')
    strategy = c.get('doc_id_strategy', 'parent_name')

    if args.variant == 'sm':
        model = n.get('spacy_model', 'en_core_web_sm')
        out_csv = 'ner_candidates.csv'
        freq_csv = 'ner_candidate_frequencies.csv'
    else:
        model = n.get('transformer_model', 'en_core_web_trf')
        out_csv = 'ner_trf_candidates.csv'
        freq_csv = 'ner_trf_candidate_frequencies.csv'
    workers = args.workers if args.workers is not None else int(n.get('workers', 4))
    labels = list(n.get('labels', DEFAULT_LABELS))
    out_dir = resolve(n.get('output_dir') or c.get('output_dir') or '')
    out_dir.mkdir(parents=True, exist_ok=True)

    md_files = [str(p) for p in iter_markdown(md_dir, md_glob)]
    print(f"NER sweep ({args.variant}): {len(md_files):,} files × {workers} workers (model={model})",
          flush=True)
    print(f"  labels: {sorted(labels)}", flush=True)

    out_path = out_dir / out_csv
    freq_path = out_dir / freq_csv

    surface_counts: Counter = Counter()
    surface_doc_counts: dict[str, set] = defaultdict(set)
    label_counts: Counter = Counter()
    n_total = 0
    n_done = 0

    started = time.time()
    with out_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'label', 'surface', 'char_offset'])

        with mp.Pool(workers, initializer=_init_worker,
                     initargs=(model, labels, strategy)) as pool:
            for doc_id, ents, err in pool.imap_unordered(_process_doc, md_files, chunksize=4):
                if err:
                    print(f"  WARN {doc_id}: {err}", flush=True)
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
                    print(f"  [{n_done:>4}/{len(md_files)}] {n_total:>10,} ents  "
                          f"{rate:.1f} d/s  ETA={eta:.0f}s", flush=True)

    print(f"\nTotal NER entities: {n_total:,}")
    print(f"Unique surfaces:    {len(surface_counts):,}")
    for l, n in label_counts.most_common():
        print(f"  {l:<12}  {n:>10,}")

    with freq_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['surface', 'n_total_mentions', 'n_unique_docs'])
        for s, n in surface_counts.most_common():
            w.writerow([s, n, len(surface_doc_counts[s])])

    print(f"\nWrote:\n  {out_path}\n  {freq_path}", flush=True)


if __name__ == "__main__":
    main()
