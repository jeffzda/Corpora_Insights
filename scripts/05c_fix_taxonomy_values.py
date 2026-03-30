#!/usr/bin/env python3
"""
Fix cross-field taxonomy contamination and encoding issues in registry_deduped.yaml.
Also patches per_doc YAML files so source data is consistent.

Fixes applied:
  project_type:
    - 'pumped hydro'                   → 'storage'           (unambiguous)
    - 'solar'                          → 'generation'        (unambiguous)
    - 'hydrogen','bioenergy','research organisation/university',
      'programmatic/portfolio-level','demonstration'         → null (wrong field)

  project_scale_band:
    - 'concept/feasibility'            → null (lifecycle_phase value)

  lifecycle_phase:
    - 'commercialisation/operations'   → 'operations'
    - 'approvals/regulatory'           → 'approvals/contracting'
    - 'financing/commercial close'     → null (delay_category value)

  technology_domain:
    - 'software/data/digital'          → null (project_type value)

  delay_category:
    - 'approvals/contracting'          → 'approvals/regulatory'
    - 'commercial/demand failure'      → null (failure_mode value)

  delay_magnitude:
    - en-dash variants → hyphen variants  (encoding fix)
"""

import glob
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

ROOT = Path(__file__).resolve().parents[1]

# ── Fix rules ──────────────────────────────────────────────────────────────
FIXES = {
    "project_type": {
        "pumped hydro":                     "storage",
        "solar":                            "generation",
        "hydrogen":                         None,
        "bioenergy":                        None,
        "research organisation/university": None,
        "programmatic/portfolio-level":     None,
        "demonstration":                    None,
    },
    "project_scale_band": {
        "concept/feasibility":              None,
    },
    "lifecycle_phase": {
        "commercialisation/operations":     "operations",
        "approvals/regulatory":             "approvals/contracting",
        "financing/commercial close":       None,
    },
    "technology_domain": {
        "software/data/digital":            None,
    },
    "delay_category": {
        "approvals/contracting":            "approvals/regulatory",
        "commercial/demand failure":        None,
    },
    "delay_magnitude": {
        "3\u201312 months":  "3-12 months",   # en-dash → hyphen
        "1\u20133 months":   "1-3 months",
        "1\u20133 years":    "1-3 years",
    },
}


def fix_record(r: dict) -> dict:
    changed = False
    for field, mapping in FIXES.items():
        val = r.get(field)
        if val and val in mapping:
            r[field] = mapping[val]
            changed = True
    return r, changed


def process_yaml(path: Path) -> tuple[int, int]:
    with open(path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    if not records:
        return 0, 0

    total = len(records)
    fixed = 0
    new_records = []
    for r in records:
        r, changed = fix_record(r)
        if changed:
            fixed += 1
        new_records.append(r)

    if fixed:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(new_records, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False, width=120)

    return total, fixed


def main():
    total_records = 0
    total_fixed = 0

    # Fix registry_deduped.yaml
    registry = ROOT / "insights" / "registry_deduped.yaml"
    if registry.exists():
        n, f = process_yaml(registry)
        total_records += n
        total_fixed += f
        print(f"registry_deduped.yaml: {f}/{n} records fixed")

    # Fix per_doc YAMLs
    per_doc_dir = ROOT / "insights" / "per_doc"
    per_doc_files = sorted(per_doc_dir.glob("doc_*.yaml"))
    pd_total, pd_fixed = 0, 0
    for path in per_doc_files:
        n, f = process_yaml(path)
        pd_total += n
        pd_fixed += f
    print(f"per_doc/ ({len(per_doc_files)} files): {pd_fixed}/{pd_total} records fixed")

    # Fix per_project YAMLs
    per_proj_dir = ROOT / "insights" / "per_project"
    if per_proj_dir.exists():
        pp_files = sorted(per_proj_dir.glob("*.yaml"))
        pp_total, pp_fixed = 0, 0
        for path in pp_files:
            n, f = process_yaml(path)
            pp_total += n
            pp_fixed += f
        print(f"per_project/ ({len(pp_files)} files): {pp_fixed}/{pp_total} records fixed")

    print(f"\nTotal records fixed: {total_fixed + pd_fixed}")


if __name__ == "__main__":
    main()
