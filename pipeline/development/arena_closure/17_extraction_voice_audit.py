#!/usr/bin/env python3
"""Corpus-wide audit of vocabulary that appears in extracted record narratives
but is absent from the raw markdown source corpus.

The hypothesis (from p19/p29 etc. in 16_framework_bridge_typology.py): the
extraction model has its own vocabulary preferences, systematically
introducing or suppressing terms relative to the source. This script
generalises that question to the *whole* corpus rather than per-parent
patterns.

Approach: count 1-/2-/3-grams in (a) all record narratives, (b) all
markdown files. For each n-gram with frequency above a threshold in
records, check its frequency in markdown. Surface the high-frequency
record-only n-grams — these are the model's "voice."

No API calls; entirely local text processing.
"""
from __future__ import annotations
import json, re, time, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILTER_INPUT = ROOT / 'output/filter_input.jsonl'
MARKDOWN_DIR = Path('/home/jeffzda/broadlearnings/corpora/arena/markdown')
OUT = ROOT / 'closure/output/extraction_voice_audit.json'

# Standard stopword set — common English words that aren't diagnostic of voice.
STOP = set("""
a about above after again against all am an and any are aren as at be because
been before being below between both but by can cannot could couldn did didn
do does doesn doing don down during each few for from further had hadn has
hasn have haven having he her here hers herself him himself his how however i
if in into is isn it its itself just let me more most must my myself nor not
now of off on once only or other our ours ourselves out over own same shall
she should shouldn so some such than that the their theirs them themselves
then there these they this those through to too under until up upon very was
wasn we were weren what when where which while who whom why will with won
would wouldn you your yours yourself yourselves get may might us also into
within without due via per across upon either neither among various certain
many much several though although since whether thus hence therefore however
moreover furthermore additionally indeed instead rather quite often always
never sometimes usually generally typically specifically particularly
following including including excluding given despite besides toward towards
near throughout regardless beside above below behind within between
""".split())

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]+")  # word characters + internal hyphens

# Frequency thresholds — high enough to surface 'voice' patterns, not noise.
MIN_REC_FREQ_1 = 200   # words appearing 200+ times in records
MIN_REC_FREQ_2 = 50    # bigrams 50+ times
MIN_REC_FREQ_3 = 20    # trigrams 20+ times

# Top N to display per n-gram size
TOP_N = 60


def tokenise(text: str) -> list[str]:
    """Lowercased word tokens, hyphens preserved."""
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def is_content(tokens: tuple[str, ...]) -> bool:
    """Filter trivial n-grams: all-stopword, all-tiny, or all-numeric."""
    if all(t in STOP for t in tokens):
        return False
    if all(len(t) < 3 for t in tokens):
        return False
    return True


def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def main():
    t0 = time.time()
    print("Loading record narratives...", flush=True)
    rec_text_parts = []
    n_records = 0
    for line in open(FILTER_INPUT):
        r = json.loads(line)
        n_records += 1
        rec_text_parts.append(' '.join([
            r.get('narrative', '') or '',
            r.get('lesson', '') or '',
            r.get('evidence', '') or '',
        ]))
    rec_text = '\n'.join(rec_text_parts)
    print(f"  {n_records:,} records, {len(rec_text)/1e6:.1f}M chars  ({time.time()-t0:.0f}s)", flush=True)

    print("Loading markdown corpus...", flush=True)
    md_files = sorted(MARKDOWN_DIR.glob('*.md'))
    md_parts = []
    for f in md_files:
        try:
            md_parts.append(f.read_text(errors='ignore'))
        except Exception:
            pass
    md_text = '\n'.join(md_parts)
    print(f"  {len(md_files):,} files, {len(md_text)/1e6:.1f}M chars  ({time.time()-t0:.0f}s)", flush=True)

    print("Tokenising...", flush=True)
    rec_tok = tokenise(rec_text)
    md_tok = tokenise(md_text)
    print(f"  records: {len(rec_tok):,} tokens  ({time.time()-t0:.0f}s)", flush=True)
    print(f"  markdown: {len(md_tok):,} tokens  ({time.time()-t0:.0f}s)", flush=True)

    # Per-million-token normalisation factor
    rec_M = len(rec_tok) / 1e6
    md_M = len(md_tok) / 1e6

    voice = {}  # 'unigrams', 'bigrams', 'trigrams'

    for n, label, threshold in [
        (1, 'unigrams', MIN_REC_FREQ_1),
        (2, 'bigrams',  MIN_REC_FREQ_2),
        (3, 'trigrams', MIN_REC_FREQ_3),
    ]:
        print(f"\nCounting {label}...", flush=True)
        rec_counter = Counter(g for g in ngrams(rec_tok, n) if is_content(g))
        print(f"  records {label} unique: {len(rec_counter):,}  ({time.time()-t0:.0f}s)", flush=True)

        # Only count markdown n-grams for keys we care about (those above record threshold)
        candidates = {g for g, c in rec_counter.items() if c >= threshold}
        print(f"  candidates (rec freq ≥ {threshold}): {len(candidates):,}", flush=True)

        # Stream markdown tokens once, count only candidate n-grams
        md_counter = Counter()
        for g in ngrams(md_tok, n):
            if g in candidates:
                md_counter[g] += 1
        print(f"  markdown frequency tabulated  ({time.time()-t0:.0f}s)", flush=True)

        # Compute ratios
        rows = []
        for g in candidates:
            rec_n = rec_counter[g]
            md_n = md_counter.get(g, 0)
            rec_per_M = rec_n / rec_M
            md_per_M = md_n / md_M
            ratio = (rec_per_M / md_per_M) if md_per_M else float('inf') if rec_per_M else 0
            rows.append({
                'ngram': ' '.join(g),
                'rec_count': rec_n,
                'md_count': md_n,
                'rec_per_Mtok': round(rec_per_M, 2),
                'md_per_Mtok': round(md_per_M, 3),
                'ratio': float('inf') if ratio == float('inf') else round(ratio, 2),
            })

        # Sort: most "voice-like" = highest ratio, with high absolute rec freq
        rows_sorted = sorted(rows, key=lambda r: (
            -(float('inf') if r['ratio'] == float('inf') else r['ratio']),
            -r['rec_count'],
        ))
        # Headline filter: ratio >= 5 and md_count <= 50% of rec_count (gives "model voice" cases)
        amplified = [r for r in rows_sorted if r['ratio'] == float('inf') or r['ratio'] >= 5]
        zero_in_md = [r for r in rows_sorted if r['md_count'] == 0]

        print(f"\n  ---- {label.upper()} ----")
        print(f"  candidates above record-freq threshold: {len(rows):,}")
        print(f"  amplified (ratio ≥ 5×):                 {len(amplified):,}")
        print(f"  absent from markdown (md_count = 0):    {len(zero_in_md):,}")
        print()
        print(f"  TOP {TOP_N} (sorted by ratio rec/md, then by rec freq):")
        print(f"  {'ngram':40} {'rec':>6} {'md':>6} {'rec/Mt':>8} {'md/Mt':>8} {'ratio':>7}")
        print("  " + "-" * 80)
        for r in rows_sorted[:TOP_N]:
            ratio_s = '∞' if r['ratio'] == float('inf') else f"{r['ratio']:.1f}"
            print(f"  {r['ngram'][:40]:40} {r['rec_count']:>6,} {r['md_count']:>6,} "
                  f"{r['rec_per_Mtok']:>8.1f} {r['md_per_Mtok']:>8.2f} {ratio_s:>7}")

        voice[label] = {
            'threshold_rec_freq': threshold,
            'n_candidates': len(rows),
            'n_amplified_ratio_ge_5': len(amplified),
            'n_absent_in_markdown': len(zero_in_md),
            'top_by_ratio': [
                {**r, 'ratio': ('inf' if r['ratio'] == float('inf') else r['ratio'])}
                for r in rows_sorted[:200]
            ],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'corpus_tokens': {'records': len(rec_tok), 'markdown': len(md_tok)},
        'n_records': n_records,
        'n_markdown_files': len(md_files),
        'thresholds': {'unigrams': MIN_REC_FREQ_1, 'bigrams': MIN_REC_FREQ_2, 'trigrams': MIN_REC_FREQ_3},
        'voice': voice,
    }, indent=2))
    print(f"\nWrote {OUT}", flush=True)
    print(f"Total wall: {time.time()-t0:.0f}s", flush=True)


if __name__ == '__main__':
    main()
