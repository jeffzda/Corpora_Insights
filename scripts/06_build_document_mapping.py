#!/usr/bin/env python3
"""
Step 5: Map every registry record to its ARENA Knowledge Bank page URL and local markdown file.

Reads:
  insights/ARENA_delivery_registry_full_v1_clean.yaml   — or --registry
  arena-kb-export_1772889492.csv                        — or --kb-csv
  markdown/all/                                         — or --markdown-root

Outputs:
  insights/registry_to_document_mapping.csv   — full 14-column mapping
  insights/insight_to_source.csv              — simplified record_id → kb_document_page

Matching strategies (KB catalogue, in priority order):
  1. Exact normalised title
  2. Substring containment (≥70% length ratio)
  3. Fuzzy sequence match (≥0.60)
  4. Associated project name cross-reference (≥0.85 project match + ≥30% word overlap)
  5. Significant-word overlap (≥65%)
  6. Fuzzy fallback (≥0.50, title ≥4 words)

Matching strategies (markdown file):
  Fuzzy match on filename stem (≥0.45 confidence)

Usage:
    python scripts/05_build_document_mapping.py
    python scripts/05_build_document_mapping.py --registry insights/ARENA_delivery_registry_full_v3_clean.yaml
    python scripts/05_build_document_mapping.py --verbose

Requires: pip install pyyaml
"""

import argparse
import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]

FIELDNAMES = [
    "record_id", "registry_project", "csv_project_name", "technology_domain",
    "failure_mode", "source_title_registry", "kb_title", "kb_match_confidence",
    "kb_type", "kb_year", "kb_associated_project", "kb_document_page",
    "markdown_filename", "md_match_confidence",
]


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def sig_words(s: str) -> set[str]:
    stop = {"a", "an", "the", "and", "or", "in", "of", "for", "to", "from",
            "with", "on", "at", "by", "that", "through", "its", "is", "are"}
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
            if w not in stop and len(w) > 2}


def seq(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def word_overlap(a: str, b: str) -> float:
    wa, wb = sig_words(a), sig_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


# ---------------------------------------------------------------------------
# KB matching
# ---------------------------------------------------------------------------

def build_kb_index(kb_rows: list[dict]) -> dict[str, dict]:
    return {norm(r["Title"]): r for r in kb_rows}


def best_kb_match(source_title: str, cpn: str,
                  kb_rows: list[dict], kb_index: dict[str, dict]) -> tuple[dict | None, float, str]:
    """Return (kb_row, confidence, strategy) or (None, 0, '')."""
    sn = norm(source_title)

    # 1. Exact normalised title
    if sn in kb_index:
        return kb_index[sn], 1.0, "exact"

    # 2. Substring containment
    for r in kb_rows:
        kt = norm(r["Title"])
        if sn and kt and len(sn) > 10 and (sn in kt or kt in sn):
            score = min(len(sn), len(kt)) / max(len(sn), len(kt))
            if score >= 0.70:
                return r, score, "substring"

    # 3. Fuzzy sequence ≥0.60
    best_score, best_row = 0.0, None
    for r in kb_rows:
        s = seq(source_title, r["Title"])
        if s > best_score:
            best_score, best_row = s, r
    if best_score >= 0.60:
        return best_row, best_score, "fuzzy"

    # 4. Associated project name cross-reference
    if cpn and cpn.lower() not in ("none", ""):
        for r in kb_rows:
            ap = r.get("Associated project name", "")
            if ap and seq(cpn, ap) >= 0.85 and word_overlap(source_title, r["Title"]) >= 0.30:
                return r, 0.75, "project_name"

    # 5. Significant-word overlap ≥65%
    best_wo, best_wr = 0.0, None
    for r in kb_rows:
        wo = word_overlap(source_title, r["Title"])
        if wo > best_wo:
            best_wo, best_wr = wo, r
    if best_wo >= 0.65:
        return best_wr, best_wo, "word_overlap"

    # 6. Fuzzy fallback ≥0.50 (min 4-word title)
    if best_score >= 0.50 and len(source_title.split()) >= 4:
        return best_row, best_score, "fuzzy_fallback"

    return None, 0.0, ""


# ---------------------------------------------------------------------------
# Markdown matching
# ---------------------------------------------------------------------------

def build_md_index(md_root: Path) -> list[Path]:
    return list(md_root.rglob("*.md"))


def best_md_match(source_title: str, md_files: list[Path],
                  threshold: float = 0.45) -> tuple[str, float]:
    best_score, best_name = 0.0, ""
    for p in md_files:
        stem = p.stem.replace("_", " ")
        s = seq(source_title, stem)
        if s > best_score:
            best_score, best_name = s, p.name
    if best_score >= threshold:
        return best_name, best_score
    return "", 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=str(ROOT / "insights" / "ARENA_delivery_registry_full_v1_clean.yaml"))
    parser.add_argument("--kb-csv", default=str(ROOT / "arena-kb-export_1772889492.csv"))
    parser.add_argument("--markdown-root", default=str(ROOT / "markdown" / "all"))
    parser.add_argument("--out-dir", default=str(ROOT / "insights"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    kb_csv_path = Path(args.kb_csv)
    md_root = Path(args.markdown_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load registry
    print(f"Loading registry: {registry_path.name}")
    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    records = data if isinstance(data, list) else data.get("records", [])
    print(f"  {len(records)} records")

    # Load KB catalogue
    print(f"Loading KB catalogue: {kb_csv_path.name}")
    with open(kb_csv_path, encoding="utf-8") as f:
        kb_rows = list(csv.DictReader(f))
    print(f"  {len(kb_rows)} KB entries")
    kb_index = build_kb_index(kb_rows)

    # Load markdown files
    print(f"Indexing markdown files: {md_root}")
    md_files = build_md_index(md_root)
    print(f"  {len(md_files)} files")

    # Build mapping
    mapping_rows = []
    kb_matched = 0
    md_matched = 0
    strategy_counts: dict[str, int] = defaultdict(int)

    for r in records:
        rid = r.get("record_id", "")
        source_title = r.get("source_title", "")
        cpn = r.get("csv_project_name", "")

        # KB match
        kb_row, kb_conf, strategy = best_kb_match(source_title, cpn, kb_rows, kb_index)
        if kb_row:
            kb_matched += 1
            strategy_counts[strategy] += 1
        if args.verbose and not kb_row:
            print(f"  NO KB MATCH: {rid} '{source_title[:60]}'")

        # Markdown match
        md_name, md_conf = best_md_match(source_title, md_files)
        if md_name:
            md_matched += 1

        mapping_rows.append({
            "record_id": rid,
            "registry_project": r.get("project_name", ""),
            "csv_project_name": cpn,
            "technology_domain": r.get("technology_domain", ""),
            "failure_mode": r.get("failure_mode", ""),
            "source_title_registry": source_title,
            "kb_title": kb_row["Title"] if kb_row else "",
            "kb_match_confidence": f"{kb_conf:.2f}" if kb_row else "",
            "kb_type": kb_row.get("Type", "") if kb_row else "",
            "kb_year": kb_row.get("Year", "") if kb_row else "",
            "kb_associated_project": kb_row.get("Associated project name", "") if kb_row else "",
            "kb_document_page": kb_row.get("Link to item", "") if kb_row else "",
            "markdown_filename": md_name,
            "md_match_confidence": f"{md_conf:.2f}" if md_name else "",
        })

    total = len(mapping_rows)
    print(f"\nKB matched:       {kb_matched}/{total} ({100*kb_matched/total:.1f}%)")
    print(f"Markdown matched: {md_matched}/{total} ({100*md_matched/total:.1f}%)")
    print("\nKB matching strategies:")
    for s, n in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print(f"  {s:20s} {n:5d} ({100*n/total:.1f}%)")

    # Write full mapping
    full_path = out_dir / "registry_to_document_mapping.csv"
    with open(full_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(mapping_rows)
    print(f"\nSaved: {full_path}")

    # Write simplified mapping
    simple_path = out_dir / "insight_to_source.csv"
    with open(simple_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "kb_document_page"])
        writer.writeheader()
        for row in mapping_rows:
            writer.writerow({"record_id": row["record_id"],
                             "kb_document_page": row["kb_document_page"]})
    print(f"Saved: {simple_path}")


if __name__ == "__main__":
    main()
