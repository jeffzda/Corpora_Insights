#!/usr/bin/env python3
"""
Step 1: Select 100 high-quality report documents from the full manifest.

Reads manifest.csv from the ARENA root, filters to report-type subdirectories,
scores each document on quality indicators, and selects proportionally
by technology domain.

Output: ../data/reports_sample_100.json
"""

import csv
import json
import html
import re
from pathlib import Path
from collections import defaultdict

# --- Config ---
ARENA_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_FILE = ARENA_ROOT / "manifest.csv"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "reports_sample_100.json"
TARGET_COUNT = 100
RANDOM_SEED = 42

# Subdirs that indicate a report document (not lessons learnt or milestone)
REPORT_SUBDIRS = {
    "Reports",
    "Reports_Lessons",       # lessons learnt style reports
    "Reports_Milestones",    # milestone reports
    "Reports_Insights",
    "Reports_Guides",
}

# Quality scoring bonuses by subdir
GOOD_SUBDIRS = {
    "Reports_Lessons": 3,
    "Reports_Milestones": 2,
    "Reports_Insights": 1,
    "Reports": 0,
    "Reports_Guides": 0,
}

TITLE_POSITIVE = re.compile(
    r"final report|technical report|feasibility|lessons learnt|knowledge sharing|deployment report",
    re.IGNORECASE,
)
TITLE_NEGATIVE = re.compile(
    r"newsletter|brochure|fact sheet|media release|infographic|webinar|presentation",
    re.IGNORECASE,
)

DOMAIN_MAP = [
    ("Solar energy, Solar PV R&D", "solar_pv"),
    ("Concentrated solar thermal", "solar_thermal"),
    ("Distributed energy resources", "der"),
    ("Demand response", "demand_response"),
    ("Electric vehicles", "ev"),
    ("Battery storage", "battery_storage"),
    ("Hydrogen energy", "hydrogen"),
    ("Bioenergy", "bioenergy"),
    ("Industrial energy efficiency", "industrial_decarbonisation"),
    ("Renewables for industry", "industrial_decarbonisation"),
    ("Advanced manufacturing", "manufacturing"),
    ("Grid stability", "grid_stability"),
    ("Pumped hydro", "pumped_hydro"),
    ("Wind energy", "wind"),
    ("Enabling infrastructure", "enabling_infrastructure"),
    ("Ocean energy", "ocean"),
]


def map_domain(cat: str) -> str:
    cat = cat.strip()
    for prefix, domain in DOMAIN_MAP:
        if prefix.lower() in cat.lower():
            return domain
    return "other"


def quality_score(r: dict) -> int:
    score = 0
    path = Path(r["local_path"])
    if not path.exists():
        return -99

    size = path.stat().st_size
    if 300_000 <= size <= 5_000_000:
        score += 3
    elif 100_000 <= size < 300_000:
        score += 1
    elif size > 5_000_000:
        score -= 1

    try:
        year = int(r.get("Year", 0))
        if 2020 <= year <= 2025:
            score += 3
        elif 2017 <= year < 2020:
            score += 2
        elif 2015 <= year < 2017:
            score += 1
    except (ValueError, TypeError):
        pass

    if r.get("Project Status", "") == "Past":
        score += 1

    score += GOOD_SUBDIRS.get(path.parent.name, 0)

    title = r.get("Title", "")
    if TITLE_POSITIVE.search(title):
        score += 2
    if TITLE_NEGATIVE.search(title):
        score -= 5

    return score


def main():
    with open(MANIFEST_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Decode HTML entities in Category field
    for r in rows:
        r["Category"] = html.unescape(r.get("Category", ""))

    # Filter to report subdirs with downloaded PDFs
    report_rows = [
        r for r in rows
        if r.get("status") == "downloaded"
        and r.get("local_path")
        and Path(r["local_path"]).parent.name in REPORT_SUBDIRS
    ]
    print(f"Report-type PDFs available: {len(report_rows)}")

    # Score and domain-classify
    for r in report_rows:
        r["domain"] = map_domain(r["Category"])
        r["quality_score"] = quality_score(r)

    # Pool by domain, sorted by quality score descending
    pools: dict[str, list] = defaultdict(list)
    for r in sorted(report_rows, key=lambda x: -x["quality_score"]):
        pools[r["domain"]].append(r)

    # Proportional allocation: allocate TARGET_COUNT across domains
    total = len(report_rows)
    allocations: dict[str, int] = {}
    assigned = 0
    domains = sorted(pools.keys(), key=lambda d: -len(pools[d]))
    for d in domains:
        alloc = round(TARGET_COUNT * len(pools[d]) / total)
        alloc = min(alloc, len(pools[d]))
        allocations[d] = alloc
        assigned += alloc

    # Adjust to hit TARGET_COUNT exactly
    diff = TARGET_COUNT - assigned
    if diff > 0:
        for d in domains:
            if diff == 0:
                break
            if allocations[d] < len(pools[d]):
                allocations[d] += 1
                diff -= 1
    elif diff < 0:
        for d in reversed(domains):
            if diff == 0:
                break
            if allocations[d] > 0:
                allocations[d] -= 1
                diff += 1

    # Select top-scored docs from each domain pool
    selected = []
    for d, count in allocations.items():
        selected.extend(pools[d][:count])

    print(f"Selected: {len(selected)} documents across {len(allocations)} domains")
    for d, count in sorted(allocations.items(), key=lambda x: -x[1]):
        print(f"  {d}: {count}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
