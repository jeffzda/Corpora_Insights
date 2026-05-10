#!/usr/bin/env python3
"""Clean and harmonise the consolidated registry.

Config-driven version of scripts/05_clean_registry.py.
Uses domain config for enum values, keyword rules, and remap rules.

Usage:
    python -m pipeline.clean --domain arena
    python -m pipeline.clean --domain arena --input path/to/input.yaml --output path/to/output.yaml
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

try:
    from rapidfuzz import fuzz
except ImportError:
    raise SystemExit("rapidfuzz not installed")

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAJORITY_THRESHOLD = 0.70
PROJECT_LEVEL_FIELDS = ["project_type", "project_scale_band", "proponent_type"]


def get_defaults(cfg):
    """Get default input/output paths for this domain."""
    runs_dir = ROOT / "runs" / cfg.domain.name.lower()
    # Fall back to insights/ for ARENA backward compat
    input_path = runs_dir / "registry_deduped.yaml"
    if not input_path.exists():
        input_path = ROOT / "insights" / "registry_deduped.yaml"
    output_path = runs_dir / "registry_deduped_clean.yaml"
    if not output_path.parent.exists():
        output_path = ROOT / "insights" / "registry_deduped_clean.yaml"
    return input_path, output_path


def normalise_name(s):
    """Normalise project name for fuzzy comparison."""
    s = s.lower()
    s = re.sub(r"[\(\)\[\]\-–—/]", " ", s)
    for w in ["project", "the", "a", "and", "&", "demonstration", "demo",
              "programme", "program", "phase", "1", "2", "3", "i", "ii",
              "iii", "pilot", "trial", "study", "australia", "australian",
              "arena", "energy", "power", "renewable", "renewables"]:
        s = re.sub(r"\b" + w + r"\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def remap_tech_domain(raw, valid_tech, keyword_rules):
    """Map raw technology domain value to canonical taxonomy value."""
    if not raw:
        return None, None
    if raw in valid_tech:
        return raw, None
    lower = raw.lower()
    if keyword_rules:
        for rule in keyword_rules:
            keywords = rule["keywords"]
            canonical = rule["canonical"]
            if any(kw in lower for kw in keywords):
                matched = next(kw for kw in keywords if kw in lower)
                return canonical, f"keyword match on '{matched}'"
    return "other", "no keyword match — fallback to other"


def fix_project_type(raw, valid_types, remap_rules):
    """Remap technology names used as project types to delivery archetypes."""
    if not raw or raw in valid_types:
        return raw, None
    project_type_map = {}
    if remap_rules and "project_type" in remap_rules:
        project_type_map = remap_rules["project_type"]
    mapped = project_type_map.get(raw.lower())
    if mapped:
        return mapped, f"technology name '{raw}' remapped to delivery archetype"
    return raw, None


def fix_scale_band(raw):
    """Nullify lifecycle phase values that leaked into scale_band."""
    if raw == "concept/feasibility":
        return None, "lifecycle_phase value leaked into scale_band — nulled"
    return raw, None


def fix_failure_mode(raw, valid_modes, remap_rules):
    """Remap off-taxonomy failure mode values."""
    if not raw or raw in valid_modes:
        return raw, None
    failure_mode_map = {}
    if remap_rules and "failure_mode" in remap_rules:
        failure_mode_map = remap_rules["failure_mode"]
    mapped = failure_mode_map.get(raw.lower())
    if mapped:
        return mapped, f"off-taxonomy value '{raw}' remapped"
    return raw, None


def main():
    parser = argparse.ArgumentParser(description="Clean and harmonise registry")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    default_input, default_output = get_defaults(cfg)

    in_path = Path(args.input) if args.input else default_input
    out_clean = Path(args.output) if args.output else default_output
    out_audit = Path(str(out_clean).replace("_clean.yaml", "_audit.yaml"))
    out_clean.parent.mkdir(parents=True, exist_ok=True)

    # Load config
    valid_tech = set(cfg.enums.technology_domain)
    valid_types = set(cfg.enums.project_type)
    valid_scale = set(cfg.enums.project_scale_band)
    valid_modes = set(cfg.enums.failure_mode)
    keyword_rules = cfg.keyword_rules or []
    remap_rules = cfg.remap_rules or {}
    do_not_merge_raw = cfg.do_not_merge or []
    do_not_merge = {frozenset(pair) for pair in do_not_merge_raw}

    print(f"Loading: {in_path.name}")
    with open(in_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    if isinstance(records, dict):
        records = records.get("records", [])
    print(f"  {len(records)} records")

    audit = []

    def log(record_id, field_name, old, new, reason, tier):
        audit.append({"record_id": record_id, "field": field_name,
                      "old_value": old, "new_value": new,
                      "reason": reason, "tier": tier})

    # Build project name canonicalisation map
    raw_names = sorted({(r.get("project_name") or "").strip() for r in records if r.get("project_name")})
    parent = {n: n for n in raw_names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb if len(rb) >= len(ra) else ra] = ra if len(rb) >= len(ra) else rb

    for i, n1 in enumerate(raw_names):
        n1n = normalise_name(n1)
        for n2 in raw_names[i + 1:]:
            if frozenset([n1, n2]) in do_not_merge:
                continue
            if fuzz.token_sort_ratio(n1n, normalise_name(n2)) >= 82:
                union(n1, n2)

    clusters = defaultdict(list)
    for n in raw_names:
        clusters[find(n)].append(n)
    name_to_canon = {v: min(variants, key=lambda x: (len(x), x))
                     for variants in clusters.values() for v in variants}

    # Tier 1: deterministic fixes
    for r in records:
        rid = r.get("record_id", "?")

        raw_name = (r.get("project_name") or "").strip()
        canon = name_to_canon.get(raw_name, raw_name)
        if canon != raw_name:
            log(rid, "project_name", raw_name, canon, "fuzzy name canonicalisation", "1-name")
            r["project_name"] = canon

        # Technology domain
        old = r.get("technology_domain")
        new, reason = remap_tech_domain(old, valid_tech, keyword_rules)
        if new != old:
            log(rid, "technology_domain", old, new, reason, "1")
            r["technology_domain"] = new

        # Project type
        old = r.get("project_type")
        new, reason = fix_project_type(old, valid_types, remap_rules)
        if new != old:
            log(rid, "project_type", old, new, reason, "1")
            r["project_type"] = new

        # Scale band
        old = r.get("project_scale_band")
        new, reason = fix_scale_band(old)
        if new != old:
            log(rid, "project_scale_band", old, new, reason, "1")
            r["project_scale_band"] = new

        # Failure mode
        old = r.get("failure_mode")
        new, reason = fix_failure_mode(old, valid_modes, remap_rules)
        if new != old:
            log(rid, "failure_mode", old, new, reason, "1")
            r["failure_mode"] = new

    # Tier 2: majority-vote harmonisation
    grouping_field = cfg.domain.project_grouping_field
    proj_record_counts = Counter()
    proj_crosscutting_signals = Counter()
    for r in records:
        proj = r.get("project_name") or ""
        proj_record_counts[proj] += 1
        if not r.get(grouping_field) or r.get("project_scale_band") == "programmatic/portfolio-level":
            proj_crosscutting_signals[proj] += 1
    crosscutting_projects = {
        proj for proj, signals in proj_crosscutting_signals.items()
        if signals / proj_record_counts[proj] >= 0.5
    }
    print(f"  Cross-cutting project groups (skipping majority vote): {len(crosscutting_projects)}")

    proj_votes = defaultdict(lambda: defaultdict(Counter))
    for r in records:
        proj = r.get("project_name") or ""
        if proj in crosscutting_projects:
            continue
        for f in PROJECT_LEVEL_FIELDS:
            v = r.get(f)
            if v:
                proj_votes[proj][f][v] += 1

    proj_majority = {}
    contested_projects = set()

    for proj, fields in proj_votes.items():
        proj_majority[proj] = {}
        for f, ctr in fields.items():
            total = sum(ctr.values())
            top_val, top_count = ctr.most_common(1)[0]
            pct = top_count / total
            contested = len(ctr) > 1 and pct < MAJORITY_THRESHOLD
            proj_majority[proj][f] = (top_val, pct, contested)
            if contested:
                contested_projects.add((proj, f))

    for r in records:
        proj = r.get("project_name") or ""
        rid = r.get("record_id", "?")
        existing_note = r.get("confidence_note") or ""

        for f in PROJECT_LEVEL_FIELDS:
            if proj not in proj_majority or f not in proj_majority[proj]:
                continue
            majority_val, pct, contested = proj_majority[proj][f]
            current = r.get(f)

            if contested:
                if "contested" not in existing_note:
                    note = f"harmonisation-contested: {f} split ({dict(proj_votes[proj][f])})"
                    r["confidence_note"] = (existing_note + "; " + note).lstrip("; ")
                    log(rid, "confidence_note", existing_note or None, r["confidence_note"],
                        f"{f} has no clear majority ({pct:.0%})", "2-contested")
            elif current != majority_val and current is not None:
                log(rid, f, current, majority_val,
                    f"majority-vote harmonisation ({pct:.0%} of project records)", "2-majority")
                r[f] = majority_val
            elif current is None and majority_val:
                log(rid, f, None, majority_val,
                    f"null filled from project majority ({pct:.0%})", "2-fill")
                r[f] = majority_val

    # Write outputs
    with open(out_clean, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    with open(out_audit, "w", encoding="utf-8") as f:
        yaml.dump(audit, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    tier_counts = Counter(a["tier"] for a in audit)
    field_counts = Counter(a["field"] for a in audit)

    print(f"\nTotal changes: {len(audit)}")
    print("By tier:")
    for tier in sorted(tier_counts):
        print(f"  {tier}: {tier_counts[tier]}")
    print("By field:")
    for field, count in field_counts.most_common():
        print(f"  {field}: {count}")
    print(f"\nContested (flagged for Tier 3): {len(contested_projects)}")
    if contested_projects:
        print("  Run pipeline.reconcile to resolve these via LLM.")
    print(f"\nSaved: {out_clean}")
    print(f"Saved: {out_audit}")


if __name__ == "__main__":
    main()
