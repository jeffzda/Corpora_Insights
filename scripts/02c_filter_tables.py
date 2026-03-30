#!/usr/bin/env python3
"""
Filter noise from the extracted table CSV corpus.

Noise criteria (any one triggers rejection):
  1. Fewer than 2 non-empty rows
  2. Fewer than 2 columns
  3. More than 80% of cells are empty
  4. Single-value table — all non-empty cells contain the same string
     (common artefact: repeated header cell from merged-cell detection)

Outputs
-------
  tables/             — clean CSVs remain here (noisy ones moved to tables/noise/)
  insights/tables_index.json — full index of all tables with quality flags,
                               row/col counts, and matched project metadata

The tables_index.json is keyed for use by downstream scripts (e.g. a Haiku
classification pass) to quickly filter to clean tables only.

Usage
-----
    python scripts/02c_filter_tables.py
    python scripts/02c_filter_tables.py --dry-run   # report only, no moves
"""

import argparse
import csv
import json
import re
import shutil
from pathlib import Path

ROOT          = Path(__file__).resolve().parents[1]
TABLE_DIR     = ROOT / "tables"
NOISE_DIR     = TABLE_DIR / "noise"
MANIFEST_CSV  = ROOT / "manifest.csv"
INDEX_OUT     = ROOT / "insights" / "tables_index.json"

# ---------------------------------------------------------------------------
# Noise detection
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def assess_table(rows: list[list[str]]) -> tuple[bool, str]:
    """
    Return (is_clean, reason_if_noisy).
    """
    if not rows:
        return False, "empty file"

    # Normalise: strip whitespace, treat None-like strings as empty
    cleaned = [[c.strip() for c in row] for row in rows]

    # Non-empty rows: at least one non-empty cell
    nonempty_rows = [r for r in cleaned if any(c for c in r)]

    if len(nonempty_rows) < 2:
        return False, f"only {len(nonempty_rows)} non-empty row(s)"

    # Column count: use max cols across non-empty rows
    max_cols = max(len(r) for r in nonempty_rows)
    if max_cols < 2:
        return False, "single column"

    # Empty cell ratio
    total_cells = sum(len(r) for r in nonempty_rows)
    empty_cells = sum(1 for r in nonempty_rows for c in r if not c)
    if total_cells > 0 and empty_cells / total_cells > 0.80:
        return False, f"{empty_cells/total_cells:.0%} empty cells"

    # Single-value table
    all_values = {c for r in nonempty_rows for c in r if c}
    if len(all_values) == 1:
        return False, f"single repeated value: '{next(iter(all_values))[:30]}'"

    return True, ""


# ---------------------------------------------------------------------------
# Slug → manifest metadata
# ---------------------------------------------------------------------------

def load_manifest_by_slug() -> dict[str, dict]:
    """Return manifest rows keyed by the PDF stem (slug)."""
    by_slug = {}
    with open(MANIFEST_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            local_path = row.get("local_path", "")
            if local_path.endswith(".pdf"):
                slug = Path(local_path).stem
                by_slug[slug] = row
    return by_slug


def slug_from_filename(csv_name: str) -> str:
    """
    Extract document slug from table filename.
    Format: {slug}_p{page:03d}_t{idx:02d}.csv
    The trailing _pNNN_tNN is always exactly 9 chars before .csv.
    """
    stem = csv_name.replace(".csv", "")
    # Strip _pNNN_tNN (always ends with _p + 3 digits + _t + 2 digits)
    return re.sub(r"_p\d{3}_t\d{2}$", "", stem)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Filter noise tables from CSV corpus")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report stats and write index but do not move files")
    args = parser.parse_args()

    manifest = load_manifest_by_slug()

    csv_files = sorted(TABLE_DIR.glob("*.csv"))
    print(f"Total CSV files: {len(csv_files):,}")

    if not args.dry_run:
        NOISE_DIR.mkdir(exist_ok=True)
        INDEX_OUT.parent.mkdir(exist_ok=True)

    index = []
    stats = {"clean": 0, "noise": 0, "reasons": {}}

    for csv_path in csv_files:
        slug = slug_from_filename(csv_path.name)
        meta = manifest.get(slug, {})

        rows = load_csv(csv_path)
        is_clean, reason = assess_table(rows)

        nonempty = [r for r in rows if any(c.strip() for c in r)]
        max_cols = max((len(r) for r in nonempty), default=0)

        entry = {
            "filename": csv_path.name,
            "slug": slug,
            "clean": is_clean,
            "rows": len(nonempty),
            "cols": max_cols,
            "title": meta.get("Title", ""),
            "doc_type": meta.get("Type", ""),
            "project": meta.get("Associated project name", ""),
            "year": meta.get("Year", ""),
            "category": meta.get("Category", ""),
        }
        if not is_clean:
            entry["noise_reason"] = reason

        index.append(entry)

        if is_clean:
            stats["clean"] += 1
        else:
            stats["noise"] += 1
            stats["reasons"][reason.split(":")[0].split("(")[0].strip()] = \
                stats["reasons"].get(reason.split(":")[0].split("(")[0].strip(), 0) + 1
            if not args.dry_run:
                shutil.move(str(csv_path), str(NOISE_DIR / csv_path.name))

    # Write index
    if not args.dry_run:
        INDEX_OUT.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Index written: {INDEX_OUT} ({len(index):,} entries)")

    print(f"\nResults:")
    print(f"  Clean:  {stats['clean']:,} ({stats['clean']/len(csv_files)*100:.1f}%)")
    print(f"  Noise:  {stats['noise']:,} ({stats['noise']/len(csv_files)*100:.1f}%)")
    print(f"\nNoise breakdown:")
    for reason, count in sorted(stats["reasons"].items(), key=lambda x: -x[1]):
        print(f"  {reason:<35} {count:>5}")
    if not args.dry_run:
        print(f"\nNoisy files moved to: {NOISE_DIR}")
        print(f"Clean files remain in: {TABLE_DIR}")


if __name__ == "__main__":
    main()
