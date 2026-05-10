"""Stage g01 — Regex candidate sweep across corpus markdown.

Generalises:
    pipeline/development/arena_glossary/01_regex_sweep.py

Sweeps three pattern families:
    1. acronyms       \\b[A-Z]{2,8}\\b   (with stoplist)
    2. initialisms    multiple letter+period (A.B.C., U.S.A.)
    3. title-case NPs multi-word capitalised phrases

Outputs:
    output_dir/candidates_raw.csv           (doc_id, pattern, surface, char_offset)
    output_dir/candidate_frequencies.csv    (surface, pattern, n_total_mentions, n_unique_docs)
    output_dir/pattern_stats.csv

Corpus-specific assumptions are all in domain.yaml:
    glossary.candidate.markdown_dir        path containing markdown files
    glossary.candidate.markdown_glob       default '*/*.rendered.md' (marker layout)
    glossary.candidate.doc_id_strategy     'parent_name' | 'stem'
    glossary.candidate.stoplist_path       per-corpus acronym false-positives
    glossary.candidate.title_case_min_words  default 2
    glossary.candidate.title_case_max_words  default 8
    glossary.candidate.output_dir          where to write CSVs
"""
from __future__ import annotations
import argparse
import csv
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.config import DomainConfig
from pipeline.glossary.shared.io import resolve, derive_doc_id, iter_markdown, load_stoplist


# Generic English/document-artefact stoplist baked into the engine.
# Per-corpus extras live in glossary.candidate.stoplist_path.
GENERIC_ACRONYM_STOP = {
    # Roman numerals
    'II','III','IV','VI','VII','VIII','IX','XI','XII','XIII','XIV','XV','XVI',
    'XVII','XVIII','XIX','XX','XXI','XXII','XXIII','XXIV','XXV',
    # Common English caps that aren't entities
    'I','A','THE','AND','OR','BUT','NOT','OK',
    # Document-format artefacts
    'PDF','DOCX','PPT','URL','HTTP','HTTPS','HTML','CSS',
    'PNG','JPG','GIF','TXT','DOC','XLS','XLSX',
    # Structural artefacts
    'TOC','REF','ID','APP','EOF','BOF','TBC','TBD','N','Y',
    # Cardinals / temporal
    'AM','PM','AD','BC','CE','BCE','GMT','UTC','EST','PST',
    'MON','TUE','WED','THU','FRI','SAT','SUN',
    'JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC',
}

GENERIC_TITLECASE_STOP_PREFIXES = (
    'Page ', 'Figure ', 'Table ', 'Section ', 'Chapter ',
    'Appendix ', 'Note ', 'Reference ',
)


def build_titlecase_re(min_words: int, max_words: int) -> re.Pattern:
    """A {min_words}-{max_words} run of capitalised words, with lowercase connectors."""
    rep_min = max(min_words - 1, 1)
    rep_max = max_words - 1
    return re.compile(
        r'\b('
        r'[A-Z][a-zA-Z]+'
        r'(?:\s+(?:of|and|the|in|for|to|on|at|&|de|von|van)\s+[A-Z][a-zA-Z]+'
        r'|\s+[A-Z][a-zA-Z]+'
        r'){' + str(rep_min) + ',' + str(rep_max) + r'}'
        r')\b'
    )


ACRONYM_RE = re.compile(r'\b([A-Z]{2,8})\b')
INITIALISM_RE = re.compile(r'\b((?:[A-Z]\.){2,5}[A-Z]?)\b')


def passes_titlecase_filter(s: str) -> bool:
    if any(s.startswith(p) for p in GENERIC_TITLECASE_STOP_PREFIXES):
        return False
    if len(s) > 120:
        return False
    return True


def sweep_doc(text: str, stoplist: set[str], titlecase_re: re.Pattern):
    for m in INITIALISM_RE.finditer(text):
        yield ('initialism', m.group(1), m.start())
    for m in ACRONYM_RE.finditer(text):
        s = m.group(1)
        if s in stoplist:
            continue
        yield ('acronym', s, m.start())
    for m in titlecase_re.finditer(text):
        s = m.group(1).strip()
        if not passes_titlecase_filter(s):
            continue
        yield ('titlecase', s, m.start())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', required=True)
    args, _ = ap.parse_known_args()

    cfg = DomainConfig.load(args.domain)
    c = (cfg.glossary.get('candidate') or {})

    md_dir = resolve(c.get('markdown_dir') or '')
    if not md_dir.exists():
        raise SystemExit(f"markdown_dir does not exist: {md_dir}")
    md_glob = c.get('markdown_glob', '*/*.rendered.md')
    doc_id_strategy = c.get('doc_id_strategy', 'parent_name')
    out_dir = resolve(c.get('output_dir') or '')
    out_dir.mkdir(parents=True, exist_ok=True)

    stop_user = load_stoplist(resolve(c['stoplist_path']) if c.get('stoplist_path') else None)
    stoplist = GENERIC_ACRONYM_STOP | stop_user

    titlecase_re = build_titlecase_re(
        c.get('title_case_min_words', 2),
        c.get('title_case_max_words', 8),
    )

    md_files = list(iter_markdown(md_dir, md_glob))
    print(f"Sweeping {len(md_files):,} markdown files (glob={md_glob!r}) ...", flush=True)
    print(f"  stoplist: {len(stoplist)} entries ({len(GENERIC_ACRONYM_STOP)} engine + "
          f"{len(stop_user)} corpus)", flush=True)

    candidates_path = out_dir / 'candidates_raw.csv'
    freq_path = out_dir / 'candidate_frequencies.csv'
    stats_path = out_dir / 'pattern_stats.csv'

    pattern_counts = Counter()
    surface_doc_counts: dict[str, set] = defaultdict(set)
    surface_total_counts: Counter = Counter()
    surface_pattern: dict[str, str] = {}

    n_total = 0
    started = time.time()
    with candidates_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'pattern', 'surface', 'char_offset'])
        for i, md in enumerate(md_files):
            if i % 200 == 0:
                el = time.time() - started
                rate = i / el if el > 0 else 0
                eta = (len(md_files) - i) / rate if rate > 0 else 0
                print(f"  [{i:>4}/{len(md_files)}] {n_total:>10,} cands  {rate:.1f} d/s  ETA={eta:.0f}s",
                      flush=True)
            doc_id = derive_doc_id(md, doc_id_strategy)
            try:
                text = md.read_text(errors='ignore')
            except Exception as e:
                print(f"  skip {md}: {e}", flush=True)
                continue
            for pattern, surface, offset in sweep_doc(text, stoplist, titlecase_re):
                w.writerow([doc_id, pattern, surface, offset])
                pattern_counts[pattern] += 1
                surface_total_counts[surface] += 1
                surface_doc_counts[surface].add(doc_id)
                if surface not in surface_pattern:
                    surface_pattern[surface] = pattern
                n_total += 1

    print(f"\nTotal candidates: {n_total:,}")
    for p, n in pattern_counts.most_common():
        print(f"  {p:<12}  {n:>10,}")

    with freq_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['surface', 'pattern', 'n_total_mentions', 'n_unique_docs'])
        for surface, n in surface_total_counts.most_common():
            w.writerow([surface, surface_pattern[surface], n, len(surface_doc_counts[surface])])

    with stats_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pattern', 'n_mentions', 'n_unique_surfaces'])
        unique_per_pattern = Counter()
        for s, p in surface_pattern.items():
            unique_per_pattern[p] += 1
        for p, n in pattern_counts.most_common():
            w.writerow([p, n, unique_per_pattern[p]])

    print(f"\nUnique surfaces: {len(surface_total_counts):,}")
    print(f"Wrote:\n  {candidates_path}\n  {freq_path}\n  {stats_path}", flush=True)


if __name__ == "__main__":
    main()
