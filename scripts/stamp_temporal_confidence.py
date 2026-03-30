#!/usr/bin/env python3
"""
Deterministically stamp temporal relevance notes onto existing records
where the finding is time-sensitive and the source is older than 5 years.

Rules (all require publish year < 2021):
  1. failure_mode = 'commercial/demand failure'
        → market conditions, demand forecasts, and commercial viability
          have shifted substantially since ~2015-2020
  2. failure_mode = 'technical underperformance' AND technology_domain
     in the fast-evolving set (battery storage, solar PV, hydrogen, EV)
        → cost curves and capability benchmarks have moved dramatically
  3. outcome_class = 'discontinued/not progressed'
        → projects abandoned as unviable may have since restarted under
          changed market conditions

Stable findings NOT flagged regardless of age:
  - governance/coordination failure
  - design assumption failure
  - schedule slippage
  - cost overrun
  - integration failure
  - regulatory misfit
  - resource/capability shortfall
  - data quality/measurement failure
  (These describe specific events — the lesson holds regardless of when it happened)

Runs in-place on insights/per_doc/*.yaml.
Does not overwrite existing confidence_note content — appends to it.

Usage:
    python3 scripts/stamp_temporal_confidence.py             # all per_doc files
    python3 scripts/stamp_temporal_confidence.py --dry-run   # print changes, no writes
    python3 scripts/stamp_temporal_confidence.py --stats     # summary only
"""

import argparse
import glob
import re
from pathlib import Path

import yaml

ROOT    = Path(__file__).resolve().parents[1]
PER_DOC = ROOT / "insights" / "per_doc"

CUTOFF_YEAR = 2021   # documents published before this year are flagged

# technology domains where cost/capability claims from before CUTOFF_YEAR
# are particularly likely to be superseded
FAST_EVOLVING_DOMAINS = {
    "battery storage",
    "solar PV",
    "hydrogen",
    "EV",
}

# failure modes where old findings on commercial/market viability are unreliable
COMMERCIAL_MODES = {"commercial/demand failure"}

# failure modes where old findings on technical capability may be superseded
# (only for fast-evolving domains — see FAST_EVOLVING_DOMAINS)
TECHNICAL_MODES = {"technical underperformance"}

# outcome classes where the situation may have changed
STALE_OUTCOMES = {"discontinued/not progressed"}


def parse_year(record: dict) -> int | None:
    """Extract publication year from record metadata."""
    # Try publish_date first ("YYYY-MM" or "YYYY")
    pd = record.get("publish_date") or ""
    m = re.match(r"(\d{4})", str(pd))
    if m:
        return int(m.group(1))
    # Fall back to kb_year
    ky = record.get("kb_year") or ""
    m = re.match(r"(\d{4})", str(ky))
    if m:
        return int(m.group(1))
    # Fall back to kb_publish_date ("DD/MM/YYYY")
    kpd = record.get("kb_publish_date") or ""
    m = re.search(r"(\d{4})", str(kpd))
    if m:
        return int(m.group(1))
    return None


def build_note(year: int, reason: str) -> str:
    return f"Published {year} — {reason} may be superseded by subsequent developments in this rapidly evolving field."


def should_flag(record: dict) -> str | None:
    """
    Return a confidence note string if this record warrants a temporal flag,
    else None.
    """
    year = parse_year(record)
    if year is None or year >= CUTOFF_YEAR:
        return None

    fm  = (record.get("failure_mode") or "").strip().lower()
    oc  = (record.get("outcome_class") or "").strip().lower()
    td  = (record.get("technology_domain") or "").strip().lower()

    if fm in COMMERCIAL_MODES:
        return build_note(year, "commercial viability and demand conditions")

    if fm in TECHNICAL_MODES and td in FAST_EVOLVING_DOMAINS:
        return build_note(year, f"technical performance benchmarks for {td}")

    if oc in STALE_OUTCOMES:
        return build_note(year, "commercial and technical conditions that led to discontinuation")

    return None


def process_file(path: Path, dry_run: bool) -> tuple[int, int]:
    """
    Returns (records_checked, records_flagged).
    """
    with open(path, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    if not isinstance(records, list):
        return 0, 0

    changed = 0
    for record in records:
        note = should_flag(record)
        if note is None:
            continue

        existing = record.get("confidence_note") or ""
        # Don't double-stamp
        if "superseded" in existing or "rapidly evolving" in existing:
            continue

        new_note = f"{existing}; {note}" if existing else note
        if dry_run:
            rid = record.get("record_id", "?")
            year = parse_year(record)
            fm = record.get("failure_mode", "")
            oc = record.get("outcome_class", "")
            td = record.get("technology_domain", "")
            print(f"  {rid} [{year}] fm={fm!r} oc={oc!r} td={td!r}")
            print(f"    → {note}")
        else:
            record["confidence_note"] = new_note
        changed += 1

    if not dry_run and changed:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)

    return len(records), changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print flagged records without writing")
    parser.add_argument("--stats", action="store_true",
                        help="Print summary counts only")
    args = parser.parse_args()

    paths = sorted(PER_DOC.glob("doc_*.yaml"))
    total_records = total_flagged = total_files_changed = 0

    for path in paths:
        checked, flagged = process_file(path, dry_run=args.dry_run or args.stats)
        total_records += checked
        total_flagged += flagged
        if flagged:
            total_files_changed += 1
            if args.stats:
                print(f"  {path.name}: {flagged}/{checked} flagged")

    print(f"\nRecords checked: {total_records:,}")
    print(f"Records flagged: {total_flagged:,} ({100*total_flagged/total_records:.1f}%)")
    print(f"Files updated:   {total_files_changed}")
    if args.dry_run:
        print("(dry run — no files written)")


if __name__ == "__main__":
    main()
