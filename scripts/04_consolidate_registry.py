#!/usr/bin/env python3
"""
Step 4: Consolidate group YAML files into a single deduplicated registry.

Reads:   insights/full_run/group_*.yaml
Outputs:
  insights/ARENA_delivery_registry_full_v1.yaml            — raw consolidated
  insights/ARENA_delivery_registry_full_v1_clean.yaml      — deduplicated
  insights/ARENA_delivery_registry_full_v1_removed_dupes.yaml — audit trail

Deduplication logic: within each project_name, records with identical
(failure_mode, lifecycle_phase) are flagged as duplicates. The longer
what_happened text is kept; the shorter is moved to the audit trail.

Usage:
    python scripts/04_consolidate_registry.py
    python scripts/04_consolidate_registry.py --batch-dir insights/full_run
    python scripts/04_consolidate_registry.py --out-prefix insights/ARENA_delivery_registry_full_v1

Requires: pip install pyyaml
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]


def fix_unquoted_colons(text: str) -> str:
    """Fix the most common YAML formatting issue from LLM output."""
    return re.sub(
        r'^(\s*\w[\w_]*:\s+)([^"\n]*:[^"\n]*)$',
        lambda m: m.group(1) + '"' + m.group(2).replace('"', '\\"') + '"',
        text,
        flags=re.MULTILINE,
    )


def load_batches(batch_dir: Path) -> list[dict]:
    records = []
    files = sorted(batch_dir.glob("group_*.yaml"))
    if not files:
        raise SystemExit(f"No group_*.yaml files found in {batch_dir}")
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            content = yaml.safe_load(text)
        except yaml.YAMLError:
            text = fix_unquoted_colons(text)
            try:
                content = yaml.safe_load(text)
            except yaml.YAMLError as e:
                print(f"  SKIP {f.name}: YAML error after fix attempt: {e}")
                continue
        if isinstance(content, list):
            batch = content
        elif isinstance(content, dict) and "records" in content:
            batch = content["records"]
        else:
            print(f"  SKIP {f.name}: unexpected structure")
            continue
        records.extend(batch)
        print(f"  {f.name}: {len(batch)} records")
    return records


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    by_project: dict[str, list] = defaultdict(list)
    for r in records:
        key = (r.get("project_name") or "").strip().lower()
        by_project[key].append(r)

    keep, removed = [], []
    for _, group in by_project.items():
        if len(group) == 1:
            keep.extend(group)
            continue
        seen: dict[tuple, dict] = {}
        for r in group:
            fp = (str(r.get("failure_mode", "")), str(r.get("lifecycle_phase", "")))
            if fp in seen:
                existing = seen[fp]
                if len(str(r.get("what_happened", ""))) > len(str(existing.get("what_happened", ""))):
                    existing["_DUPLICATE_REASON"] = (
                        f"Superseded by {r.get('record_id')} (same fingerprint, shorter text)"
                    )
                    removed.append(existing)
                    seen[fp] = r
                else:
                    r["_DUPLICATE_REASON"] = (
                        f"Duplicate of {existing.get('record_id')} (same fingerprint)"
                    )
                    removed.append(r)
            else:
                seen[fp] = r
        keep.extend(seen.values())

    return keep, removed


def save_yaml(records: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", default=str(ROOT / "insights" / "full_run"))
    parser.add_argument("--out-prefix", default=str(ROOT / "insights" / "ARENA_delivery_registry_full_v1"))
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    out_prefix = Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading from {batch_dir} ...")
    records = load_batches(batch_dir)
    print(f"\nTotal raw records: {len(records)}")

    raw_path = Path(str(out_prefix) + ".yaml")
    save_yaml(records, raw_path)
    print(f"Saved raw: {raw_path}")

    clean, removed = deduplicate(records)
    print(f"Removed {len(removed)} duplicates → {len(clean)} clean records")

    clean_path = Path(str(out_prefix) + "_clean.yaml")
    save_yaml(clean, clean_path)
    print(f"Saved clean: {clean_path}")

    dupes_path = Path(str(out_prefix) + "_removed_dupes.yaml")
    save_yaml(removed, dupes_path)
    print(f"Saved audit: {dupes_path}")


if __name__ == "__main__":
    main()
