#!/usr/bin/env python3
"""
Step 3: Group markdown files into balanced batches for parallel agent processing.

Reads data/reports_sample_100.json (with md_path populated by step 2).
Groups files by total text size using round-robin assignment.

Output: data/agent_groups.json — list of groups, each a list of record dicts

Usage:
    python 03_build_agent_groups.py [--groups 10] [--max-kb 400]
"""

import json
import argparse
from pathlib import Path

PILOT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PILOT_ROOT / "data" / "reports_sample_100.json"
OUTPUT_FILE = PILOT_ROOT / "data" / "agent_groups.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=int, default=10)
    parser.add_argument("--max-kb", type=int, default=400)
    args = parser.parse_args()

    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    # Only include records with md_path
    valid = [r for r in records if r.get("md_path") and Path(r["md_path"]).exists()]
    print(f"Records with markdown: {len(valid)}")

    # Get file sizes
    for r in valid:
        r["_text_size"] = Path(r["md_path"]).stat().st_size

    # Sort largest first, then round-robin assign to groups
    valid.sort(key=lambda r: -r["_text_size"])
    groups: list[list] = [[] for _ in range(args.groups)]
    group_sizes = [0] * args.groups

    for r in valid:
        # Assign to the smallest group
        idx = min(range(args.groups), key=lambda i: group_sizes[i])
        groups[idx].append(r)
        group_sizes[idx] += r["_text_size"]

    # Report
    for i, (grp, sz) in enumerate(zip(groups, group_sizes), 1):
        print(f"Group {i:2d}: {len(grp):3d} docs, {sz // 1024:5d} KB total")

    # Strip internal size field before saving
    for grp in groups:
        for r in grp:
            r.pop("_text_size", None)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2)
    print(f"\nSaved {args.groups} groups to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
