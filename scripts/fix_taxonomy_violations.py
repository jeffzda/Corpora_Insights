#!/usr/bin/env python3
"""
Fix known taxonomy violations in per_doc YAML files.

Problems:
  1. delay_magnitude: hyphen instead of en-dash
       '3-12 months' → '3–12 months'
       '1-3 months'  → '1–3 months'
       '1-3 years'   → '1–3 years'

  2. project_scale_band: lifecycle_phase values cross-contaminated
       'concept/feasibility' → null  (lifecycle_phase value, not a scale)
       'operations'          → null  (lifecycle_phase value, not a scale)

  3. project_type: values from other fields cross-contaminated
       'research organisation/university' → null  (proponent_type value)
       'solar PV'                         → null  (technology_domain value)
       'pumped hydro'                     → null  (technology_domain value)
       'programmatic/portfolio-level'     → null  (project_scale_band value)

  4. lifecycle_phase: delay_category value cross-contaminated
       'financing/commercial close'       → null  (delay_category value)

Runs in-place on insights/per_doc/*.yaml.
"""

import glob
from pathlib import Path

import yaml

ROOT    = Path(__file__).resolve().parents[1]
PER_DOC = ROOT / "insights" / "per_doc"

DELAY_MAGNITUDE_MAP = {
    '3-12 months': '3–12 months',
    '1-3 months':  '1–3 months',
    '1-3 years':   '1–3 years',
}

PROJECT_SCALE_NULLS = {'concept/feasibility', 'operations'}

PROJECT_TYPE_NULLS = {
    'research organisation/university',
    'solar PV',
    'pumped hydro',
    'programmatic/portfolio-level',
}

LIFECYCLE_PHASE_NULLS = {'financing/commercial close'}


def fix_record(record: dict) -> int:
    """Apply all fixes to a single record. Returns number of fields changed."""
    changes = 0

    # 1. delay_magnitude en-dash
    dm = record.get('delay_magnitude')
    if dm in DELAY_MAGNITUDE_MAP:
        record['delay_magnitude'] = DELAY_MAGNITUDE_MAP[dm]
        changes += 1

    # 2. project_scale_band cross-contamination
    psb = record.get('project_scale_band')
    if psb in PROJECT_SCALE_NULLS:
        record['project_scale_band'] = None
        changes += 1

    # 3. project_type cross-contamination
    pt = record.get('project_type')
    if pt in PROJECT_TYPE_NULLS:
        record['project_type'] = None
        changes += 1

    # 4. lifecycle_phase cross-contamination
    lp = record.get('lifecycle_phase')
    if lp in LIFECYCLE_PHASE_NULLS:
        record['lifecycle_phase'] = None
        changes += 1

    return changes


def main():
    paths = sorted(PER_DOC.glob('doc_*.yaml'))
    total_records = total_changes = files_changed = 0

    for path in paths:
        with open(path, encoding='utf-8') as f:
            records = yaml.safe_load(f)
        if not isinstance(records, list):
            continue

        file_changes = 0
        for record in records:
            file_changes += fix_record(record)
            total_records += 1

        if file_changes:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
            files_changed += 1
            total_changes += file_changes

    print(f'Records processed: {total_records:,}')
    print(f'Fields fixed:      {total_changes:,}')
    print(f'Files updated:     {files_changed}')


if __name__ == '__main__':
    main()
