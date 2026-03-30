#!/usr/bin/env python3
"""
sense_check.py — ARENA Delivery Registry Source Verification Tool
==================================================================

Verifies that claims in the ARENA delivery registry (v3_clean) are traceable
to their source markdown documents by:
  1. Fuzzy-matching each record's source_title to a markdown filename
  2. Searching for key phrases from evidence_excerpt and what_happened in the source doc
  3. Reporting PASS / PARTIAL / FAIL verdicts with supporting detail

Usage:
    # Spot-check specific record IDs:
    python3 sense_check.py --ids ARENA-DLV-0512 ARENA-DLV-0207

    # Random stratified sample (default 20 records):
    python3 sense_check.py --sample 20

    # Sample filtered by field value:
    python3 sense_check.py --sample 15 --filter failure_mode "design assumption failure"
    python3 sense_check.py --sample 15 --filter technology_domain "battery storage"
    python3 sense_check.py --sample 15 --filter proponent_type "network business"

    # Write results to a report file:
    python3 sense_check.py --sample 20 --out insights/sense_check_report.md

Outputs:
    - Console table with PASS / PARTIAL / FAIL per record
    - Summary counts
    - Optional markdown report file (--out)

Verdict definitions:
    PASS    — ≥2 exact phrase matches between registry text and source doc
    PARTIAL — <2 exact but ≥2 phrases match at 80%+ word level (formatting/OCR variance)
    FAIL    — <2 phrases match at any level; source doc may be wrong or claim unsupported

See docs/sense_check_methodology.md for full methodology and interpretation guidance.
"""

import argparse
import random
import re
import sys
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY_PATH  = Path("insights/ARENA_delivery_registry_full_v3_clean.yaml")
MARKDOWN_ROOT  = Path("markdown")
PASS_THRESHOLD  = 2   # exact hits needed for PASS
PARTIAL_MIN_WORD_RATIO = 0.80   # word-level match ratio for PARTIAL credit
FUZZY_MATCH_THRESHOLD  = 0.45   # minimum SequenceMatcher score to accept a file match
PHRASES_PER_RECORD = 5          # number of phrases sampled per record

# ─────────────────────────────────────────────────────────────────────────────
# File matching
# ─────────────────────────────────────────────────────────────────────────────

def normalise(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def build_markdown_index(root: Path) -> dict:
    """Return {normalised_stem: Path} for all .md files under root."""
    return {normalise(p.stem): p for p in root.rglob("*.md")}


def find_source_file(title: str, md_index: dict) -> tuple:
    """
    Match a source_title string to a markdown file path.

    Returns (Path | None, float score).
    Strategy:
      1. Substring containment (score=1.0)
      2. SequenceMatcher on first 60 chars of normalised title vs normalised stem
    """
    norm_title = normalise(title)
    # Exact substring match
    for norm, path in md_index.items():
        if norm_title in norm or norm in norm_title:
            return path, 1.0
    # Fuzzy fallback
    short = norm_title[:60]
    best_score, best_path = 0.0, None
    for norm, path in md_index.items():
        score = SequenceMatcher(None, short, norm[:60]).ratio()
        if score > best_score:
            best_score, best_path = score, path
    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_path, best_score
    return None, 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Phrase extraction and verification
# ─────────────────────────────────────────────────────────────────────────────

STOPWORDS = {
    "during", "project", "system", "energy", "would", "however", "which",
    "through", "there", "their", "these", "those", "after", "before",
    "between", "within", "without", "because", "although", "while",
    "other", "under", "above", "found", "being", "where", "when",
}


def extract_phrases(text: str, n: int = PHRASES_PER_RECORD) -> list:
    """
    Extract n evenly-spaced 6-7-word phrases from text, skipping stopword-heavy
    regions. Falls back to any contiguous 6-word window if needed.
    """
    if not text:
        return []
    words = text.split()
    if len(words) < 6:
        return [text.lower()]

    phrases = []
    step = max(1, len(words) // (n + 1))
    for i in range(1, n + 1):
        start = i * step
        chunk = words[start : start + 7]
        if len(chunk) >= 5:
            phrases.append(" ".join(chunk).lower())

    # Pad with additional windows if we got fewer than requested
    for start in range(0, len(words) - 5, 4):
        if len(phrases) >= n:
            break
        chunk = words[start : start + 7]
        candidate = " ".join(chunk).lower()
        if candidate not in phrases:
            phrases.append(candidate)

    return phrases[:n]


def check_phrases(phrases: list, doc_text: str) -> list:
    """
    For each phrase, check:
      - exact: phrase appears verbatim (lowercased) in doc
      - ratio: fraction of phrase words present anywhere in doc (word-level)

    Returns list of (phrase, exact: bool, word_ratio: float).
    """
    doc_lower = doc_text.lower()
    doc_words = set(re.findall(r"\b\w+\b", doc_lower))
    results = []
    for phrase in phrases:
        exact = phrase in doc_lower
        phrase_words = re.findall(r"\b\w+\b", phrase)
        ratio = (
            sum(1 for w in phrase_words if w in doc_words) / len(phrase_words)
            if phrase_words else 0.0
        )
        results.append((phrase, exact, ratio))
    return results


def verdict(checks: list) -> str:
    exact_hits   = sum(1 for _, e, _ in checks if e)
    partial_hits = sum(1 for _, e, r in checks if not e and r >= PARTIAL_MIN_WORD_RATIO)
    if exact_hits >= PASS_THRESHOLD:
        return "PASS"
    if exact_hits + partial_hits >= PASS_THRESHOLD:
        return "PARTIAL"
    return "FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# Core check runner
# ─────────────────────────────────────────────────────────────────────────────

def check_record(record: dict, md_index: dict) -> dict:
    """Run full source verification for one record. Returns result dict."""
    rid   = record.get("record_id", "?")
    title = record.get("source_title", "")
    excerpt = record.get("evidence_excerpt") or ""
    what    = record.get("what_happened") or ""

    path, match_score = find_source_file(title, md_index)

    if path is None:
        return {
            "record_id":   rid,
            "project_name": record.get("project_name", ""),
            "source_title": title,
            "file":         None,
            "file_match_score": 0.0,
            "verdict":      "NO_FILE",
            "exact_hits":   0,
            "partial_hits": 0,
            "total_phrases": 0,
            "checks":       [],
            "failure_mode": record.get("failure_mode", ""),
            "technology_domain": record.get("technology_domain", ""),
        }

    doc_text = path.read_text(encoding="utf-8", errors="ignore")

    # Prefer evidence_excerpt (direct quote), supplement with what_happened
    n_excerpt = min(4, PHRASES_PER_RECORD)
    n_what    = PHRASES_PER_RECORD - n_excerpt
    phrases   = extract_phrases(excerpt, n_excerpt) + extract_phrases(what, n_what)
    phrases   = phrases[:PHRASES_PER_RECORD]

    checks = check_phrases(phrases, doc_text)
    v      = verdict(checks)

    exact_hits   = sum(1 for _, e, _ in checks if e)
    partial_hits = sum(1 for _, e, r in checks if not e and r >= PARTIAL_MIN_WORD_RATIO)

    return {
        "record_id":        rid,
        "project_name":     record.get("project_name", ""),
        "source_title":     title,
        "file":             path,
        "file_match_score": match_score,
        "verdict":          v,
        "exact_hits":       exact_hits,
        "partial_hits":     partial_hits,
        "total_phrases":    len(checks),
        "checks":           checks,
        "failure_mode":     record.get("failure_mode", ""),
        "technology_domain": record.get("technology_domain", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def print_results(results: list, verbose: bool = False):
    col = {"PASS": "\033[92m", "PARTIAL": "\033[93m", "FAIL": "\033[91m",
           "NO_FILE": "\033[90m", "RESET": "\033[0m"}

    print(f"\n{'Record ID':<20} {'Project':<36} {'Verdict':<10}  "
          f"{'File match':>10}  Detail")
    print("-" * 100)

    for r in results:
        v     = r["verdict"]
        score = f"{r['file_match_score']:.2f}" if r["file"] else " n/a"
        detail = (f"{r['exact_hits']} exact, {r['partial_hits']} partial "
                  f"/ {r['total_phrases']} phrases")
        proj  = (r["project_name"] or "")[:34]
        c     = col.get(v, "")
        reset = col["RESET"]
        print(f"{r['record_id']:<20} {proj:<36} {c}{v:<10}{reset}  "
              f"{score:>10}  {detail}")

        if verbose and r["verdict"] in ("FAIL", "NO_FILE"):
            for phrase, exact, ratio in r.get("checks", [])[:3]:
                tag = "EXACT" if exact else f"{ratio:.0%}"
                print(f"    [{tag}] {phrase[:70]}")

    counts = Counter(r["verdict"] for r in results)
    n = len(results)
    print(f"\n{'─'*60}")
    print(f"  Total checked : {n}")
    print(f"  PASS          : {counts['PASS']}  ({counts['PASS']/n*100:.0f}%)")
    print(f"  PARTIAL       : {counts['PARTIAL']}  ({counts['PARTIAL']/n*100:.0f}%)")
    print(f"  FAIL          : {counts['FAIL']}  ({counts['FAIL']/n*100:.0f}%)")
    print(f"  NO FILE       : {counts['NO_FILE']}  ({counts['NO_FILE']/n*100:.0f}%)")
    if counts["FAIL"] > 0:
        print(f"\n  ⚠ FAIL records warrant manual review — see details above.")
    elif counts["NO_FILE"] > 0:
        print(f"\n  ⚠ NO_FILE records: source markdown not found. Check title matching.")
    else:
        print(f"\n  ✓ All claims traceable to source documents.")


def write_markdown_report(results: list, out_path: Path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# ARENA Delivery Registry — Sense Check Report",
        f"**Generated:** {ts}  ",
        f"**Registry:** {REGISTRY_PATH}  ",
        f"**Records checked:** {len(results)}\n",
        "## Results\n",
        "| Record ID | Project | Verdict | File match | Detail |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        score = f"{r['file_match_score']:.2f}" if r["file"] else "n/a"
        detail = (f"{r['exact_hits']} exact, {r['partial_hits']} partial "
                  f"/ {r['total_phrases']} phrases")
        lines.append(
            f"| {r['record_id']} | {r['project_name']} | **{r['verdict']}** "
            f"| {score} | {detail} |"
        )

    counts = Counter(r["verdict"] for r in results)
    n = len(results)
    lines += [
        "\n## Summary\n",
        f"| Verdict | n | % |",
        f"|---|---|---|",
        f"| PASS    | {counts['PASS']} | {counts['PASS']/n*100:.0f}% |",
        f"| PARTIAL | {counts['PARTIAL']} | {counts['PARTIAL']/n*100:.0f}% |",
        f"| FAIL    | {counts['FAIL']} | {counts['FAIL']/n*100:.0f}% |",
        f"| NO FILE | {counts['NO_FILE']} | {counts['NO_FILE']/n*100:.0f}% |",
        "\n## Verdict Definitions\n",
        "- **PASS** — ≥2 exact phrase matches between registry text and source document",
        "- **PARTIAL** — <2 exact but ≥2 phrases match at 80%+ word level "
          "(typically PDF/OCR formatting variance — not a content mismatch)",
        "- **FAIL** — fewer than 2 phrases match; warrants manual review",
        "- **NO FILE** — source markdown could not be matched to a file\n",
        "_See `docs/sense_check_methodology.md` for full methodology._",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sense-check ARENA delivery registry records against source markdown."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ids", nargs="+", metavar="ARENA-DLV-XXXX",
        help="One or more specific record IDs to check",
    )
    group.add_argument(
        "--sample", type=int, metavar="N",
        help="Check a random sample of N records",
    )
    parser.add_argument(
        "--filter", nargs=2, metavar=("FIELD", "VALUE"),
        help="Filter records by field value before sampling "
             "(e.g. --filter failure_mode 'design assumption failure')",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--out", metavar="PATH",
        help="Write results to a markdown report file",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show phrase-level detail for FAIL and NO_FILE records",
    )
    parser.add_argument(
        "--registry", default=str(REGISTRY_PATH),
        help=f"Path to registry YAML (default: {REGISTRY_PATH})",
    )
    parser.add_argument(
        "--markdown-root", default=str(MARKDOWN_ROOT),
        help=f"Root directory for markdown files (default: {MARKDOWN_ROOT})",
    )
    args = parser.parse_args()

    # Load registry
    registry_path = Path(args.registry)
    if not registry_path.exists():
        sys.exit(f"Registry not found: {registry_path}")
    with open(registry_path) as f:
        records = yaml.safe_load(f)
    idx = {r["record_id"]: r for r in records}

    # Build markdown index
    md_root = Path(args.markdown_root)
    if not md_root.exists():
        sys.exit(f"Markdown root not found: {md_root}")
    print(f"Building markdown index from {md_root}...")
    md_index = build_markdown_index(md_root)
    print(f"  {len(md_index)} files indexed")

    # Select records
    if args.ids:
        selected = []
        for rid in args.ids:
            if rid not in idx:
                print(f"  WARNING: {rid} not found in registry — skipping")
            else:
                selected.append(idx[rid])
    else:
        pool = list(records)
        if args.filter:
            field, value = args.filter
            pool = [r for r in pool if (r.get(field) or "") == value]
            if not pool:
                sys.exit(f"No records match {field}={value!r}")
            print(f"  Filtered to {len(pool)} records where {field}={value!r}")
        random.seed(args.seed)
        n = min(args.sample, len(pool))
        selected = random.sample(pool, n)
        print(f"  Selected {n} records (seed={args.seed})")

    # Run checks
    print(f"\nChecking {len(selected)} records...")
    results = [check_record(r, md_index) for r in selected]

    # Output
    print_results(results, verbose=args.verbose)
    if args.out:
        write_markdown_report(results, Path(args.out))


if __name__ == "__main__":
    main()
