#!/usr/bin/env python3
"""
Step 5b: LLM-assisted reconciliation for contested project-level fields.

Reads projects flagged as 'harmonisation-contested' by 05_clean_registry.py
and asks Claude to make a single authoritative classification for each.

Uses claude-haiku (fast, cheap) — each call handles one project (~6 delivery
event samples). Typical run: ~200 contested projects, ~$0.50 USD total.

Reads:
  insights/ARENA_delivery_registry_full_v2_clean.yaml   (or --input)
  insights/ARENA_delivery_registry_full_v2_audit.yaml

Outputs:
  insights/ARENA_delivery_registry_full_v3_clean.yaml   (or --output)
  insights/ARENA_delivery_registry_full_v3_audit.yaml

Usage:
    python scripts/05b_reconcile_contested.py
    python scripts/05b_reconcile_contested.py \\
        --input  insights/ARENA_delivery_registry_full_v2_clean.yaml \\
        --output insights/ARENA_delivery_registry_full_v3_clean.yaml

Requires:
    pip install anthropic pyyaml
    export ANTHROPIC_API_KEY=sk-ant-...
"""

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed. Run: pip install anthropic")

ROOT = Path(__file__).resolve().parents[1]

MODEL = "claude-haiku-4-5-20251001"

VALID_VALUES = {
    "project_type": [
        "generation", "storage", "network/grid", "DER/customer-side",
        "transport electrification", "industrial decarbonisation",
        "manufacturing/supply chain", "software/data/digital",
        "enabling infrastructure", "multi-technology/hybrid",
    ],
    "project_scale_band": [
        "lab/bench", "pilot", "demonstration", "first commercial/FOAK",
        "commercial expansion", "utility/large-scale", "programmatic/portfolio-level",
    ],
    "proponent_type": [
        "project developer", "utility/energy retailer", "network business",
        "industrial operator", "fleet/logistics operator", "manufacturer/OEM",
        "technology vendor", "research organisation/university",
        "consortium/multi-party venture", "government/public-sector body",
        "community/local body",
    ],
}

SYSTEM = """\
You are a classification assistant for the ARENA Delivery Insight Registry —
a dataset of Australian clean energy project delivery records.

Your task: given a project name, sample delivery events, and a vote split for
one or more classification fields, choose the single best value for each field.

Rules:
- Choose strictly from the allowed values listed.
- Base your decision on the project's actual nature, not on vote counts.
- project_type: classify by the dominant DELIVERY object, not every technology.
- project_scale_band: use the scale that best describes the primary activity.
- proponent_type: identify the lead delivery actor.
- Respond ONLY with a valid JSON object, e.g. {"project_type": "storage"}
"""


def build_prompt(proj_name: str, recs: list[dict], contested_fields: dict) -> str:
    seen_phases: set = set()
    samples: list[str] = []
    for r in recs:
        phase = r.get("lifecycle_phase", "")
        wh = (r.get("what_happened") or "").strip()
        if wh and phase not in seen_phases:
            samples.append(f"  - [{phase}] {wh[:200]}")
            seen_phases.add(phase)
        if len(samples) >= 6:
            break
    for r in recs:
        if len(samples) >= 6:
            break
        wh = (r.get("what_happened") or "").strip()
        line = f"  - [{r.get('lifecycle_phase', '')}] {wh[:200]}"
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
        lines += [
            f"\nField: {field}",
            f"Current vote split: {votes}",
            f"Allowed values: {allowed}",
        ]
    lines.append('\nRespond with JSON only.')
    return "\n".join(lines)


def parse_response(raw: str) -> dict:
    match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in: {raw!r}")
    decisions = json.loads(match.group())
    for field, val in decisions.items():
        if field not in VALID_VALUES:
            raise ValueError(f"Unknown field: {field}")
        if val not in VALID_VALUES[field]:
            raise ValueError(f"Invalid value for {field}: {val!r}")
    return decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",
                        default=str(ROOT / "insights" / "registry_deduped_clean.yaml"))
    parser.add_argument("--output",
                        default=str(ROOT / "insights" / "registry_deduped_reconciled.yaml"))
    args = parser.parse_args()

    in_path = Path(args.input)
    out_clean = Path(args.output)
    out_audit = Path(str(out_clean).replace("_clean.yaml", "_audit.yaml"))
    out_clean.parent.mkdir(parents=True, exist_ok=True)

    # Derive audit path for the v2 input
    in_audit = Path(str(in_path).replace("_clean.yaml", "_audit.yaml"))

    print(f"Loading: {in_path.name}")
    with open(in_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    if isinstance(records, dict):
        records = records.get("records", [])
    print(f"  {len(records)} records")

    # Build project → records index
    proj_records: dict[str, list] = defaultdict(list)
    for r in records:
        proj_records[r.get("project_name") or ""].append(r)

    # Find contested (project, field) pairs from confidence_note flags
    contested_by_project: dict[str, dict] = defaultdict(dict)
    for r in records:
        note = r.get("confidence_note") or ""
        if "harmonisation-contested" not in note:
            continue
        proj = r.get("project_name") or ""
        for m in re.finditer(r"harmonisation-contested: (\S+) split \((\{[^}]+\})\)", note):
            field, votes_str = m.group(1), m.group(2)
            if field not in VALID_VALUES:
                continue
            try:
                votes = json.loads(votes_str.replace("'", '"'))
            except Exception:
                continue
            existing = contested_by_project[proj].get(field, {})
            if sum(votes.values()) >= sum(existing.values()):
                contested_by_project[proj][field] = votes

    total = len(contested_by_project)
    print(f"Contested projects to resolve: {total}")
    print(f"Field decisions needed: {sum(len(v) for v in contested_by_project.values())}\n")

    if total == 0:
        print("Nothing to resolve — copying input to output unchanged.")
        with open(out_clean, "w", encoding="utf-8") as f:
            yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return

    client = anthropic.Anthropic()
    resolved: dict[str, dict] = {}
    errors: list[dict] = []

    for i, (proj, contested_fields) in enumerate(sorted(contested_by_project.items()), 1):
        recs = proj_records.get(proj, [])
        if not recs:
            print(f"  [{i}/{total}] SKIP (no records): {proj[:60]}")
            continue

        prompt = build_prompt(proj, recs, contested_fields)
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            decisions = parse_response(response.content[0].text.strip())
            resolved[proj] = decisions
            fields_str = ", ".join(f"{k}={v}" for k, v in decisions.items())
            print(f"  [{i}/{total}] {proj[:55]:55s} → {fields_str}")
        except Exception as e:
            errors.append({"project": proj, "error": str(e)})
            print(f"  [{i}/{total}] ERROR {proj[:50]}: {e}")

        time.sleep(0.15)  # polite rate limiting

    print(f"\nResolved: {len(resolved)}/{total}  Errors: {len(errors)}")

    # Apply decisions
    tier3_audit = []
    changes = 0
    for r in records:
        proj = r.get("project_name") or ""
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
                    "reason": f"Tier 3 LLM reconciliation (votes: {contested_by_project[proj].get(field, {})})",
                    "tier": "3",
                })
                r[field] = chosen
                changes += 1
        # Clean up the contested flag from confidence_note
        note = r.get("confidence_note") or ""
        if "harmonisation-contested" in note:
            new_note = note
            for field in resolved[proj]:
                new_note = re.sub(
                    r";?\s*harmonisation-contested: " + re.escape(field) + r" split \([^)]+\)",
                    "", new_note,
                ).strip().lstrip(";").strip()
            r["confidence_note"] = new_note if new_note else None

    print(f"Record field changes applied: {changes}")

    with open(out_clean, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    with open(out_audit, "w", encoding="utf-8") as f:
        yaml.dump({
            "tier3_changes": tier3_audit,
            "errors": errors,
            "summary": {
                "projects_resolved": len(resolved),
                "projects_errored": len(errors),
                "record_fields_changed": changes,
            },
        }, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"\nSaved: {out_clean}")
    print(f"Saved: {out_audit}")


if __name__ == "__main__":
    main()
