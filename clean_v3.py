#!/usr/bin/env python3
"""
Tier 3: LLM-assisted reconciliation for contested project-level fields.

For each project flagged as contested in v2, send its records to Claude
and ask it to make a single authoritative classification for each contested field.

Inputs:
  insights/ARENA_delivery_registry_full_v2_clean.yaml
  insights/ARENA_delivery_registry_full_v2_audit.yaml

Outputs:
  insights/ARENA_delivery_registry_full_v3_clean.yaml
  insights/ARENA_delivery_registry_full_v3_audit.yaml  (Tier 3 changes only)
"""

import yaml
import json
import re
import time
from collections import defaultdict
import anthropic

# ─────────────────────────────────────────────
# 0. Load
# ─────────────────────────────────────────────
with open("insights/ARENA_delivery_registry_full_v2_clean.yaml") as f:
    records = yaml.safe_load(f)

with open("insights/ARENA_delivery_registry_full_v2_audit.yaml") as f:
    v2_audit = yaml.safe_load(f)

# Build index: project_name → list of records
proj_records = defaultdict(list)
for r in records:
    proj_records[r.get("project_name", "") or ""].append(r)

# ─────────────────────────────────────────────
# 1. Identify contested (project, field) pairs from v2 audit
# ─────────────────────────────────────────────
VALID_VALUES = {
    "project_type": [
        "generation", "storage", "network/grid", "DER/customer-side",
        "transport electrification", "industrial decarbonisation",
        "manufacturing/supply chain", "software/data/digital",
        "enabling infrastructure", "multi-technology/hybrid"
    ],
    "project_scale_band": [
        "lab/bench", "pilot", "demonstration", "first commercial/FOAK",
        "commercial expansion", "utility/large-scale", "programmatic/portfolio-level"
    ],
    "proponent_type": [
        "project developer", "utility/energy retailer", "network business",
        "industrial operator", "fleet/logistics operator", "manufacturer/OEM",
        "technology vendor", "research organisation/university",
        "consortium/multi-party venture", "government/public-sector body",
        "community/local body"
    ],
}

# Parse contested info from confidence_note added in Tier 2
contested_by_project = defaultdict(dict)  # proj → {field → vote_dict}

for r in records:
    note = r.get("confidence_note") or ""
    if "harmonisation-contested" not in note:
        continue
    proj = r.get("project_name", "")
    # Extract all "harmonisation-contested: FIELD split (...)" patterns
    for m in re.finditer(r"harmonisation-contested: (\S+) split \((\{[^}]+\})\)", note):
        field = m.group(1)
        try:
            votes = json.loads(m.group(2).replace("'", '"'))
        except Exception:
            continue
        if field in VALID_VALUES:
            # Use the vote dict with the most information
            existing = contested_by_project[proj].get(field, {})
            if sum(votes.values()) >= sum(existing.values()):
                contested_by_project[proj][field] = votes

print(f"Contested projects to resolve: {len(contested_by_project)}")
total_decisions = sum(len(fields) for fields in contested_by_project.values())
print(f"Total field decisions needed: {total_decisions}\n")

# ─────────────────────────────────────────────
# 2. Build prompts and call Claude
# ─────────────────────────────────────────────
client = anthropic.Anthropic()

SYSTEM = """You are a classification assistant for the ARENA Delivery Insight Registry — a dataset of Australian clean energy project delivery records.

Your task: given a project name, a sample of delivery events from that project, and the current vote split for one or more classification fields, choose the single best value for each field.

Rules:
- Choose strictly from the allowed values listed
- Base your decision on the project's actual nature, not on which option got more votes
- For project_type: classify by the dominant DELIVERY object, not every technology
- For project_scale_band: use the scale that best describes the project's primary activity
- For proponent_type: identify the lead delivery actor
- Respond ONLY with a valid JSON object mapping field names to chosen values"""


def build_prompt(proj_name, recs, contested_fields):
    # Sample up to 6 what_happened, prioritising diverse lifecycle phases
    seen_phases = set()
    samples = []
    for r in recs:
        phase = r.get("lifecycle_phase", "")
        wh = r.get("what_happened", "")
        if wh and phase not in seen_phases:
            samples.append(f"  - [{phase}] {wh[:200]}")
            seen_phases.add(phase)
        if len(samples) >= 6:
            break
    # Fill up to 6 if we ran out of unique phases
    for r in recs:
        if len(samples) >= 6:
            break
        wh = r.get("what_happened", "")
        line = f"  - [{r.get('lifecycle_phase','')}] {wh[:200]}"
        if line not in samples and wh:
            samples.append(line)

    lines = [
        f"Project: {proj_name}",
        f"Total records: {len(recs)}",
        "",
        "Sample delivery events:",
        *samples,
        "",
        "Classify the following fields:",
    ]
    for field, votes in contested_fields.items():
        allowed = " | ".join(VALID_VALUES[field])
        lines.append(f"\nField: {field}")
        lines.append(f"Current vote split: {votes}")
        lines.append(f"Allowed values: {allowed}")

    lines.append('\nRespond with JSON only, e.g. {"project_type": "storage"}')
    return "\n".join(lines)


tier3_audit = []
resolved = {}  # proj → {field → chosen_value}
errors = []

projects_list = sorted(contested_by_project.items())
total = len(projects_list)

for i, (proj, contested_fields) in enumerate(projects_list):
    recs = proj_records.get(proj, [])
    if not recs:
        print(f"  [{i+1}/{total}] SKIP (no records): {proj[:60]}")
        continue

    prompt = build_prompt(proj, recs, contested_fields)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Extract JSON even if wrapped in markdown
        json_match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON found in response: {raw}")
        decisions = json.loads(json_match.group())

        # Validate all values are in allowed set
        for field, val in decisions.items():
            if field not in VALID_VALUES:
                raise ValueError(f"Unknown field: {field}")
            if val not in VALID_VALUES[field]:
                raise ValueError(f"Invalid value for {field}: {val}")

        resolved[proj] = decisions
        fields_str = ", ".join(f"{k}={v}" for k, v in decisions.items())
        print(f"  [{i+1}/{total}] {proj[:55]} → {fields_str}")

    except Exception as e:
        errors.append({"project": proj, "error": str(e)})
        print(f"  [{i+1}/{total}] ERROR {proj[:50]}: {e}")

    # Polite rate limiting
    time.sleep(0.15)

print(f"\nResolved: {len(resolved)} / {total}")
print(f"Errors:   {len(errors)}")

# ─────────────────────────────────────────────
# 3. Apply decisions to records
# ─────────────────────────────────────────────
changes = 0
for r in records:
    proj = r.get("project_name", "")
    if proj not in resolved:
        continue
    rid = r.get("record_id", "?")
    for field, chosen in resolved[proj].items():
        old = r.get(field)
        if old != chosen:
            tier3_audit.append({
                "record_id": rid,
                "field": field,
                "old_value": old,
                "new_value": chosen,
                "reason": f"Tier 3 LLM reconciliation (votes: {contested_by_project[proj].get(field,{})})",
                "tier": "3",
            })
            r[field] = chosen
            changes += 1

    # Clean up the contested flag from confidence_note
    note = r.get("confidence_note") or ""
    if "harmonisation-contested" in note:
        # Remove only the resolved fields' flags
        new_note = note
        for field in resolved[proj]:
            new_note = re.sub(
                r";?\s*harmonisation-contested: " + re.escape(field) + r" split \([^)]+\)",
                "", new_note
            ).strip().lstrip(";").strip()
        if new_note != note:
            r["confidence_note"] = new_note if new_note else None

print(f"\nRecord field changes applied: {changes}")

# ─────────────────────────────────────────────
# 4. Write outputs
# ─────────────────────────────────────────────
out_clean = "insights/ARENA_delivery_registry_full_v3_clean.yaml"
out_audit  = "insights/ARENA_delivery_registry_full_v3_audit.yaml"

with open(out_clean, "w") as f:
    yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

with open(out_audit, "w") as f:
    yaml.dump({
        "tier3_changes": tier3_audit,
        "errors": errors,
        "summary": {
            "projects_resolved": len(resolved),
            "projects_errored": len(errors),
            "record_fields_changed": changes,
        }
    }, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

print(f"\nWritten: {out_clean}")
print(f"Written: {out_audit}")
