#!/usr/bin/env python3
"""Stage 1 of entity extraction: regex sweep across all ARENA markdown.

Captures three pattern types from raw rendered.md text:
1. Acronyms       — \\b[A-Z]{2,8}\\b  with stoplist
2. Initialisms    — multiple letter+period (A.B.C., U.S.A.)
3. Title-case NPs — multi-word capitalised phrases (Hydro Tasmania, etc.)

Outputs:
- candidates_raw.csv: one row per (surface_form, doc_id, char_offset)
- candidate_frequencies.csv: surface_form → n_total_mentions, n_unique_docs
- pattern_stats.csv: per-pattern stats

This is the cheapest stage; ~2 min runtime, no model loading.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/jeffzda/broadlearnings')
MD_DIR = ROOT / 'corpora/arena/marker_output'
OUT_DIR = Path(__file__).resolve().parent.parent / 'output'

# Pattern definitions
ACRONYM_RE = re.compile(r'\b([A-Z]{2,8})\b')
INITIALISM_RE = re.compile(r'\b((?:[A-Z]\.){2,5}[A-Z]?)\b')
# Title-case: 2-7 consecutive capitalised words, allow lowercase connectors (of, and, the, in, for, &)
TITLECASE_RE = re.compile(
    r'\b('
    r'[A-Z][a-zA-Z]+'
    r'(?:\s+(?:of|and|the|in|for|to|on|at|&|de|von|van)\s+[A-Z][a-zA-Z]+'
    r'|\s+[A-Z][a-zA-Z]+'
    r'){1,7}'
    r')\b'
)

# Stoplist — common English caps/acronyms that aren't entities of interest
ACRONYM_STOP = {
    # Roman numerals up to ~30
    'II','III','IV','VI','VII','VIII','IX','XI','XII','XIII','XIV','XV','XVI',
    'XVII','XVIII','XIX','XX','XXI','XXII','XXIII','XXIV','XXV',
    # Common
    'I','A','THE','AND','OR','BUT','NOT','OK','OK',
    'PDF','DOCX','PPT','URL','HTTP','HTTPS','HTML','CSS',
    'PNG','JPG','GIF','PDF','TXT','DOC','XLS','XLSX',
    # Page-marker and structural artefacts
    'TOC','REF','ID','APP','EOF','BOF','TBC','TBD','N','Y',
    # Cardinals / temporal
    'AM','PM','AD','BC','CE','BCE','GMT','UTC','EST','PST',
    'MON','TUE','WED','THU','FRI','SAT','SUN',
    'JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC',
}

# Title-case stoplist — common phrases that aren't entities
TITLECASE_STOP_PREFIXES = [
    'Page ', 'Figure ', 'Table ', 'Section ', 'Chapter ',
    'Appendix ', 'Note ', 'Reference ',
]


def passes_titlecase_filter(s):
    """Reject obvious non-entity title-case noise."""
    if any(s.startswith(p) for p in TITLECASE_STOP_PREFIXES):
        return False
    if len(s) > 120:  # too long, probably a sentence not an entity
        return False
    return True


def sweep_doc(text, doc_id):
    """Run all 3 pattern sweeps over text. Yield (pattern, surface, offset)."""
    for m in INITIALISM_RE.finditer(text):
        s = m.group(1)
        yield ('initialism', s, m.start())
    for m in ACRONYM_RE.finditer(text):
        s = m.group(1)
        if s in ACRONYM_STOP: continue
        yield ('acronym', s, m.start())
    for m in TITLECASE_RE.finditer(text):
        s = m.group(1).strip()
        if not passes_titlecase_filter(s): continue
        yield ('titlecase', s, m.start())


def main():
    md_files = sorted(MD_DIR.glob('*/*.rendered.md'))
    print(f"Sweeping {len(md_files):,} markdown files...", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates_path = OUT_DIR / 'candidates_raw.csv'
    freq_path = OUT_DIR / 'candidate_frequencies.csv'
    stats_path = OUT_DIR / 'pattern_stats.csv'

    pattern_counts = Counter()
    surface_doc_counts = defaultdict(set)  # surface → set of doc_ids
    surface_total_counts = Counter()
    surface_pattern = {}  # surface → primary pattern that captured it (first hit)

    n_candidates_total = 0
    with open(candidates_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['doc_id', 'pattern', 'surface', 'char_offset'])
        for i, md in enumerate(md_files):
            if i % 200 == 0:
                print(f"  [{i:>4}/{len(md_files)}]  {n_candidates_total:>10,} candidates so far",
                      flush=True)
            doc_id = md.parent.name
            try:
                text = md.read_text(errors='ignore')
            except Exception as e:
                print(f"  skip {md}: {e}")
                continue
            for pattern, surface, offset in sweep_doc(text, doc_id):
                w.writerow([doc_id, pattern, surface, offset])
                pattern_counts[pattern] += 1
                surface_total_counts[surface] += 1
                surface_doc_counts[surface].add(doc_id)
                if surface not in surface_pattern:
                    surface_pattern[surface] = pattern
                n_candidates_total += 1

    print(f"\nTotal candidates: {n_candidates_total:,}", flush=True)
    print(f"Pattern breakdown:")
    for p, n in pattern_counts.most_common():
        print(f"  {p:<14}  {n:>9,}")

    # Frequency table — one row per unique surface
    print(f"\nUnique surfaces: {len(surface_total_counts):,}")
    with open(freq_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['surface', 'pattern', 'n_total_mentions', 'n_unique_docs'])
        for surface, n in surface_total_counts.most_common():
            w.writerow([surface, surface_pattern[surface], n, len(surface_doc_counts[surface])])

    # Pattern stats
    with open(stats_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pattern', 'n_mentions', 'n_unique_surfaces'])
        unique_per_pattern = Counter()
        for s, p in surface_pattern.items():
            unique_per_pattern[p] += 1
        for p, n in pattern_counts.most_common():
            w.writerow([p, n, unique_per_pattern[p]])

    # Quick top sample per pattern
    print(f"\nTop 20 acronyms:")
    for s, n in [(s, n) for s, n in surface_total_counts.most_common(200)
                 if surface_pattern[s] == 'acronym'][:20]:
        print(f"  {n:>5}×  {s}")
    print(f"\nTop 20 title-case phrases:")
    for s, n in [(s, n) for s, n in surface_total_counts.most_common(200)
                 if surface_pattern[s] == 'titlecase'][:20]:
        print(f"  {n:>5}×  {s}")
    print(f"\nTop 10 initialisms:")
    for s, n in [(s, n) for s, n in surface_total_counts.most_common(200)
                 if surface_pattern[s] == 'initialism'][:10]:
        print(f"  {n:>5}×  {s}")

    print(f"\nWrote:")
    print(f"  {candidates_path}  ({candidates_path.stat().st_size:,} bytes)")
    print(f"  {freq_path}        ({freq_path.stat().st_size:,} bytes)")
    print(f"  {stats_path}       ({stats_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
