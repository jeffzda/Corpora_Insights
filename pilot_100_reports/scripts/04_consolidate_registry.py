#!/usr/bin/env python3
"""
Step 4: Consolidate all group YAML files into a single master registry.

Reads insights/raw_batches/group_*.yaml
Outputs:
  insights/ARENA_delivery_registry_v1.yaml       — raw consolidated (all records)
  insights/ARENA_delivery_registry_v1_clean.yaml — deduplicated
  insights/ARENA_delivery_registry_v1_removed_dupes.yaml — audit trail

Requires: pip install pyyaml
"""

import re
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

PILOT_ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = PILOT_ROOT / "insights" / "raw_batches"
OUT_DIR = PILOT_ROOT / "insights"


def load_batches() -> list[dict]:
    records = []
    for batch_file in sorted(BATCH_DIR.glob("group_*.yaml")):
        with open(batch_file, encoding="utf-8") as f:
            content = yaml.safe_load(f)
        if isinstance(content, list):
            batch_records = content
        elif isinstance(content, dict) and "records" in content:
            batch_records = content["records"]
        else:
            print(f"WARNING: unexpected format in {batch_file}")
            continue
        records.extend(batch_records)
        print(f"  {batch_file.name}: {len(batch_records)} records")
    return records


def find_duplicates(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Flag likely duplicates: same project_name + same (failure_mode, lifecycle_phase).
    Returns (clean_records, removed_records).
    """
    # Group by project_name
    by_project: dict[str, list] = defaultdict(list)
    for r in records:
        key = (r.get("project_name") or "").strip().lower()
        by_project[key].append(r)

    keep = []
    removed = []

    for project, group in by_project.items():
        if len(group) == 1:
            keep.extend(group)
            continue

        # Within group, flag records with identical structural fingerprint
        seen: dict[tuple, dict] = {}
        for r in group:
            fp = (
                str(r.get("failure_mode", "")),
                str(r.get("lifecycle_phase", "")),
            )
            if fp in seen:
                # Compare what_happened similarity — keep the one with more text
                existing = seen[fp]
                existing_len = len(str(existing.get("what_happened", "")))
                this_len = len(str(r.get("what_happened", "")))
                if this_len > existing_len:
                    # Replace: demote existing to removed
                    r["_DUPLICATE_REASON"] = (
                        f"Superseded by {existing.get('record_id')} "
                        f"(same project, same failure_mode+phase, shorter text)"
                    )
                    removed.append(existing)
                    seen[fp] = r
                else:
                    r["_DUPLICATE_REASON"] = (
                        f"Duplicate of {existing.get('record_id')} "
                        f"(same project, same failure_mode+phase)"
                    )
                    removed.append(r)
            else:
                seen[fp] = r

        keep.extend(seen.values())

    return keep, removed


def main():
    print("Loading batch files...")
    records = load_batches()
    print(f"\nTotal raw records: {len(records)}")

    # Save raw consolidated
    raw_path = OUT_DIR / "ARENA_delivery_registry_v1.yaml"
    with open(raw_path, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Saved raw registry: {raw_path} ({len(records)} records)")

    # Deduplicate
    clean, removed = find_duplicates(records)
    print(f"Duplicates removed: {len(removed)}")
    print(f"Clean records: {len(clean)}")

    clean_path = OUT_DIR / "ARENA_delivery_registry_v1_clean.yaml"
    with open(clean_path, "w", encoding="utf-8") as f:
        yaml.dump(clean, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Saved clean registry: {clean_path}")

    dupes_path = OUT_DIR / "ARENA_delivery_registry_v1_removed_dupes.yaml"
    with open(dupes_path, "w", encoding="utf-8") as f:
        yaml.dump(removed, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Saved removed dupes audit: {dupes_path}")


if __name__ == "__main__":
    main()
