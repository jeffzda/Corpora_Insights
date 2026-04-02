"""
ARENA Taxonomy v2 — Stamp new fields onto per_doc YAML files.

For each record:
  - arena_category: list of mapped categories from kb_category
  - activity_type: from projects CSV keyword classifier
  - is_consortium: boolean (true if original proponent_type was consortium)
  - proponent_type: reclassified if was consortium; original preserved as proponent_type_original
  - lifecycle_phase: variation/re-scope merged into close-out/post-project review

No API calls. All changes are deterministic.
"""

import os
import sys
import yaml
from collections import Counter

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from arena_category_map import (
    map_kb_categories, build_consortium_reclassification,
    ARENA_CATEGORY_MAP, ARENA_CATEGORIES,
)
from classify_activity_type import classify_all_projects

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PER_DOC_DIR = os.path.join(BASE_DIR, "insights", "per_doc")
PROJECTS_CSV = os.path.join(BASE_DIR, "arena-projects-export_1772932404.csv")

# Lifecycle phase remap
LIFECYCLE_REMAP = {
    "variation / re-scope": "close-out/post-project review",
    "variation/re-scope": "close-out/post-project review",
}


def main():
    dry_run = "--dry-run" in sys.argv

    # 1. Build activity_type mapping from projects CSV
    print("Building activity type classifications...")
    activity_results = classify_all_projects(PROJECTS_CSV)
    activity_map = {name: info["activity_type"] for name, info in activity_results.items()}
    print(f"  {len(activity_map)} projects classified")

    # 2. Build consortium reclassification mapping
    print("Building consortium reclassification...")
    consortium_reclass, unresolved, stats = build_consortium_reclassification(
        PER_DOC_DIR, PROJECTS_CSV
    )
    print(f"  {stats['total_consortium_projects']} consortium projects")
    print(f"  Sibling: {stats['sibling_resolved']}, Lead-org: {stats['leadorg_resolved']}, "
          f"Name: {stats['name_resolved']}, Default: {stats['defaulted']}")

    # 3. Process each per_doc YAML
    print(f"\nStamping per_doc YAMLs {'(DRY RUN)' if dry_run else ''}...")

    totals = Counter()
    cat_counts = Counter()
    activity_counts = Counter()
    consortium_count = 0
    lifecycle_remapped = 0
    files_modified = 0

    yaml_files = sorted(f for f in os.listdir(PER_DOC_DIR) if f.endswith(".yaml"))
    for fn in yaml_files:
        path = os.path.join(PER_DOC_DIR, fn)
        with open(path) as f:
            records = yaml.safe_load(f)
        if not records or not isinstance(records, list):
            continue

        modified = False
        for rec in records:
            totals["records"] += 1

            # --- arena_category ---
            kb_cat = rec.get("kb_category", "")
            mapped, excluded = map_kb_categories(kb_cat)
            if mapped != rec.get("arena_category"):
                rec["arena_category"] = mapped
                modified = True
            for c in mapped:
                cat_counts[c] += 1
            if not mapped:
                totals["no_arena_category"] += 1

            # --- activity_type ---
            pname = rec.get("kb_associated_project") or rec.get("project_name") or ""
            at = activity_map.get(pname)
            if at != rec.get("activity_type"):
                rec["activity_type"] = at
                modified = True
            activity_counts[at] += 1
            if at is None:
                totals["no_activity_type"] += 1

            # --- is_consortium + proponent_type reclassification ---
            orig_pt = rec.get("proponent_type") or ""
            is_cons = "consortium" in orig_pt.lower()

            if is_cons:
                consortium_count += 1
                rec["is_consortium"] = True
                rec["proponent_type_original"] = orig_pt
                new_pt = consortium_reclass.get(pname, orig_pt)
                rec["proponent_type"] = new_pt
                modified = True
            else:
                if rec.get("is_consortium") is not True:
                    rec["is_consortium"] = False
                    modified = True

            # --- lifecycle_phase remap ---
            lp = rec.get("lifecycle_phase", "")
            if lp in LIFECYCLE_REMAP:
                rec["lifecycle_phase_original"] = lp
                rec["lifecycle_phase"] = LIFECYCLE_REMAP[lp]
                lifecycle_remapped += 1
                modified = True

        if modified:
            files_modified += 1
            if not dry_run:
                with open(path, "w") as f:
                    yaml.dump(records, f, default_flow_style=False,
                              allow_unicode=True, sort_keys=False, width=200)

    # 4. Report
    print(f"\n{'=' * 60}")
    print(f"Stamping complete {'(DRY RUN)' if dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"Files processed: {len(yaml_files)}")
    print(f"Files modified:  {files_modified}")
    print(f"Records:         {totals['records']}")
    print(f"\narena_category coverage:")
    print(f"  Populated: {totals['records'] - totals['no_arena_category']} "
          f"({(totals['records'] - totals['no_arena_category'])/totals['records']*100:.1f}%)")
    print(f"  Missing:   {totals['no_arena_category']}")
    print(f"  Distribution:")
    for cat, count in cat_counts.most_common():
        print(f"    {count:6d}  {cat}")

    print(f"\nactivity_type coverage:")
    print(f"  Populated: {totals['records'] - totals['no_activity_type']} "
          f"({(totals['records'] - totals['no_activity_type'])/totals['records']*100:.1f}%)")
    print(f"  Distribution:")
    for at, count in activity_counts.most_common():
        print(f"    {count:6d}  {at}")

    print(f"\nConsortium reclassification: {consortium_count} records")
    print(f"Lifecycle phase remapped: {lifecycle_remapped} records")


if __name__ == "__main__":
    main()
