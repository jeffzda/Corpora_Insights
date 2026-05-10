#!/usr/bin/env python3
"""LLM-assisted reconciliation for contested project-level fields.

Config-driven version of scripts/05b_reconcile_contested.py.
Uses domain config for model selection, valid values, and prompt rendering.

Usage:
    python -m pipeline.reconcile --domain arena
    python -m pipeline.reconcile --domain arena --input path/to/clean.yaml --output path/to/reconciled.yaml
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
    raise SystemExit("pyyaml not installed")

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
RECONCILE_FIELDS = ["project_type", "project_scale_band", "proponent_type"]


def get_defaults(cfg):
    """Get default input/output paths for this domain."""
    runs_dir = ROOT / "runs" / cfg.domain.name.lower()
    input_path = runs_dir / "registry_deduped_clean.yaml"
    if not input_path.exists():
        input_path = ROOT / "insights" / "registry_deduped_clean.yaml"
    output_path = runs_dir / "registry_deduped_reconciled.yaml"
    if not output_path.parent.exists():
        output_path = ROOT / "insights" / "registry_deduped_reconciled.yaml"
    return input_path, output_path


def build_field_guidance(cfg):
    """Build field-specific guidance lines for the reconciliation prompt."""
    lines = []
    lines.append("- project_type: classify by the dominant DELIVERY object, not every technology.")
    lines.append("- project_scale_band: use the scale that best describes the primary activity.")
    lines.append("- proponent_type: identify the lead delivery actor.")
    return "\n".join(lines)


def build_prompt(proj_name, recs, contested_fields, valid_values):
    """Build user prompt for reconciliation."""
    seen_phases = set()
    samples = []
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
        allowed = " | ".join(valid_values[field])
        lines += [
            f"\nField: {field}",
            f"Current vote split: {votes}",
            f"Allowed values: {allowed}",
        ]
    lines.append('\nRespond with JSON only.')
    return "\n".join(lines)


def parse_response(raw, valid_values):
    """Parse and validate reconciliation response."""
    match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in: {raw!r}")
    decisions = json.loads(match.group())
    for field, val in decisions.items():
        if field not in valid_values:
            raise ValueError(f"Unknown field: {field}")
        if val not in valid_values[field]:
            raise ValueError(f"Invalid value for {field}: {val!r}")
    return decisions


def main():
    parser = argparse.ArgumentParser(description="LLM reconciliation of contested fields")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    default_input, default_output = get_defaults(cfg)

    in_path = Path(args.input) if args.input else default_input
    out_clean = Path(args.output) if args.output else default_output
    out_audit = Path(str(out_clean).replace("_reconciled.yaml", "_reconciled_audit.yaml"))
    out_clean.parent.mkdir(parents=True, exist_ok=True)

    model = cfg.domain.reconciliation_model
    system_prompt = cfg.prompt("reconciliation", field_guidance=build_field_guidance(cfg))

    # Build valid values dict from enums
    valid_values = {}
    for field in RECONCILE_FIELDS:
        valid_values[field] = cfg.enums.get(field, [])

    print(f"Loading: {in_path.name}")
    with open(in_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    if isinstance(records, dict):
        records = records.get("records", [])
    print(f"  {len(records)} records")

    # Build project → records index
    proj_records = defaultdict(list)
    for r in records:
        proj_records[r.get("project_name") or ""].append(r)

    # Find contested (project, field) pairs
    contested_by_project = defaultdict(dict)
    for r in records:
        note = r.get("confidence_note") or ""
        if "harmonisation-contested" not in note:
            continue
        proj = r.get("project_name") or ""
        for m in re.finditer(r"harmonisation-contested: (\S+) split \((\{[^}]+\})\)", note):
            field, votes_str = m.group(1), m.group(2)
            if field not in valid_values:
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
    resolved = {}
    errors = []

    for i, (proj, contested_fields) in enumerate(sorted(contested_by_project.items()), 1):
        recs = proj_records.get(proj, [])
        if not recs:
            print(f"  [{i}/{total}] SKIP (no records): {proj[:60]}")
            continue

        prompt = build_prompt(proj, recs, contested_fields, valid_values)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=256,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            decisions = parse_response(response.content[0].text.strip(), valid_values)
            resolved[proj] = decisions
            fields_str = ", ".join(f"{k}={v}" for k, v in decisions.items())
            print(f"  [{i}/{total}] {proj[:55]:55s} → {fields_str}")
        except Exception as e:
            errors.append({"project": proj, "error": str(e)})
            print(f"  [{i}/{total}] ERROR {proj[:50]}: {e}")

        time.sleep(0.15)

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
                    "record_id": rid, "field": field,
                    "old_value": old, "new_value": chosen,
                    "reason": f"Tier 3 LLM reconciliation (votes: {contested_by_project[proj].get(field, {})})",
                    "tier": "3",
                })
                r[field] = chosen
                changes += 1
        # Clean up contested flag
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
