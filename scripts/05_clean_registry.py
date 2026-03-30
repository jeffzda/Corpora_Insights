#!/usr/bin/env python3
"""
Step 5: Clean and harmonise the consolidated registry.

Two tiers of cleaning:

  Tier 1 — Deterministic rule-based fixes:
    - technology_domain: remap freetext to canonical taxonomy values
    - project_type: technology names used instead of delivery archetypes → remap
    - project_scale_band: lifecycle values leaked in (e.g. "concept/feasibility") → null
    - failure_mode: off-taxonomy values → nearest canonical value
    - project_name: fuzzy canonicalisation across variant spellings

  Tier 2 — Majority-vote harmonisation:
    - project_type, project_scale_band, proponent_type
    - Applied where ≥70% of non-null values for a project agree
    - Contested projects (no clear majority) are flagged in confidence_note
      for Tier 3 resolution (see 05b_reconcile_contested.py)

Reads:   insights/ARENA_delivery_registry_full_v1_clean.yaml  (or --input)
Outputs:
  insights/ARENA_delivery_registry_full_v2_clean.yaml   (or --output)
  insights/ARENA_delivery_registry_full_v2_audit.yaml

Usage:
    python scripts/05_clean_registry.py
    python scripts/05_clean_registry.py \\
        --input  insights/ARENA_delivery_registry_full_v1_clean.yaml \\
        --output insights/ARENA_delivery_registry_full_v2_clean.yaml

Requires: pip install pyyaml rapidfuzz
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

try:
    from rapidfuzz import fuzz
except ImportError:
    raise SystemExit("rapidfuzz not installed. Run: pip install rapidfuzz")

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Taxonomy constants
# ---------------------------------------------------------------------------

VALID_TECH = {
    "battery storage", "hydrogen", "solar PV", "solar thermal", "wind", "DER",
    "demand response", "EV", "bioenergy", "industrial renewables",
    "grid/system stability", "hybrid systems", "pumped hydro", "other",
}

VALID_PROJECT_TYPES = {
    "generation", "storage", "network/grid", "DER/customer-side",
    "transport electrification", "industrial decarbonisation",
    "manufacturing/supply chain", "software/data/digital",
    "enabling infrastructure", "multi-technology/hybrid",
}

VALID_SCALE_BANDS = {
    "lab/bench", "pilot", "demonstration", "first commercial/FOAK",
    "commercial expansion", "utility/large-scale", "programmatic/portfolio-level",
}

VALID_FAILURE_MODES = {
    "no major failure stated", "technical underperformance", "integration failure",
    "schedule slippage", "cost overrun", "resource/capability shortfall",
    "commercial/demand failure", "regulatory misfit", "data quality/measurement failure",
    "design assumption failure", "governance/coordination failure",
}

# Ordered keyword rules for technology_domain remapping.
# Earlier rules take priority. Keywords matched against lowercased raw value.
TECH_DOMAIN_RULES = [
    (["pumped hydro", "pumped storage hydro", "phes", "pumped storage"], "pumped hydro"),
    (["geothermal", "wave energy", "tidal", "ocean energy", "wave swell"], "other"),
    (["solar thermal", "concentrating solar", "csp", "cst", "heliostat",
      "linear fresnel", "solar air turbine", "solar dish", "solar tower",
      "solar fuels", "solar gasification", "thermoelectric", "solar cooling",
      "solar steam", "solar redox"], "solar thermal"),
    (["hydrogen", "electrolysis", "electrolyser", "pem electrolysis",
      "alkaline electrolysis", "green hydrogen", "h2xport", "hazer",
      "power-to-gas", "ammonia synthesis", "electrochemical hydrogen",
      "water splitting", "hydrogen blending", "hydrogen distribution",
      "hydrogen pipeline", "hydrogen appliance", "hydrogen storage",
      "liquefied hydrogen", "hydrogen calcination"], "hydrogen"),
    (["solar pv", "solar cell", "silicon pv", "silicon solar", "perovskite",
      "photovoltaic", "pv module", "pv manufacturing", "pv thermal",
      "solar irradiance", "solar forecasting", "solar resource",
      "monocrystalline", "polysilicon", "topcon", "perc", "hjt", "ibc",
      "bifacial", "thin-film", "sliver cell", "laser crystallisation",
      "silicon ingot", "solar construction", "module manufacturing"], "solar PV"),
    (["wind", "wind forecasting", "wind farm", "wind turbine", "lidar",
      "wind power forecasting", "wind fcas"], "wind"),
    (["electric vehicle", "ev charging", "ev smart charging", "vehicle-to-grid",
      "v2g", "fleet charging", "ev fleet", "ev fast charging", "dc fast charging",
      "battery electric", "bev", "phev", "evse", "ocpp", "tesla fleet",
      "fleet electrification", "charging network", "charging infrastructure",
      "kerbside ev", "pole-mounted charger"], "EV"),
    (["demand response", "rert", "load control", "load curtailment",
      "behavioural demand", "behavioural dr", "smart hot water", "controlled load",
      "ripple control", "hvac control", "direct load control",
      "demand aggregation", "demand flexibility", "demand management"], "demand response"),
    (["der", "vpp", "virtual power plant", "operating envelope",
      "dynamic operating envelope", "der orchestration", "der coordination",
      "der aggregation", "der integration", "cer data", "consumer energy resources",
      "distribution system operator", "rooftop pv inverter", "behind-the-meter"], "DER"),
    (["bess", "battery storage", "battery energy storage", "grid-scale bess",
      "grid-forming bess", "grid forming bess", "lithium-ion battery",
      "lithium ion battery", "vanadium flow", "flow battery", "nas battery",
      "residential battery", "community battery", "battery test centre",
      "synthetic inertia", "virtual machine mode", "vmm", "fast frequency response",
      "grid-forming inverter", "grid forming inverter", "fcas bess",
      "hornsdale", "wallgrove", "lake bonney", "liddell bess",
      "battery electric trucks", "bess energy arbitrage"], "battery storage"),
    (["bioenergy", "biomass", "biogas", "biomethane", "biofuel", "bio-oil",
      "biochar", "anaerobic digestion", "gasification", "pyrolysis",
      "waste-to-energy", "energy from waste", "hefa", "saf", "sustainable aviation",
      "renewable diesel", "fischer-tropsch", "biorefinery", "fogo"], "bioenergy"),
    (["industrial", "process heat", "heat pump", "alumina", "steel",
      "ironmaking", "dri", "iron ore", "ammonia", "fertiliser",
      "calcination", "electrification of industry", "industrial decarbonisation",
      "industrial demand response", "industrial heat", "mechanical vapour", "mvr",
      "electric arc furnace", "high temperature", "thermal energy storage",
      "aquatic centre", "building electrification", "hvac", "refrigeration",
      "waste heat recovery"], "industrial renewables"),
    (["grid", "network", "system strength", "frequency control", "inertia",
      "fcas", "harmonic", "power quality", "grid connection", "emt modelling",
      "pscad", "protection relay", "islanding", "grid-forming",
      "inverter-based resources", "grid stability", "causer pays",
      "primary frequency", "system restart", "ancillary services",
      "low voltage feeder", "lvft", "dynamic model validation",
      "voltage management", "network tariff", "distribution network",
      "transmission"], "grid/system stability"),
    (["hybrid", "microgrid", "off-grid", "remote community", "solar-diesel",
      "wind-solar hybrid", "battery-solar", "solar pv bess",
      "containerised hybrid", "hybrid renewable", "hybrid power"], "hybrid systems"),
]

PROJECT_TYPE_MAP = {
    "solar thermal": "generation",
    "solar pv": "generation",
    "hydrogen": "industrial decarbonisation",
    "bioenergy": "generation",
    "programmatic/portfolio-level": "enabling infrastructure",
}

FAILURE_MODE_MAP = {
    "procurement/supply chain": "resource/capability shortfall",
}

# Projects that look similar but are genuinely distinct — do not merge names
DO_NOT_MERGE = {
    frozenset(["Lake Bonney Battery Energy Storage System", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Broken Hill Battery Energy Storage System (BHBESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Liddell Battery Energy Storage System (AGL)"]),
    frozenset(["ENGIE Future Fuels Public Fast Charging", "Evie Networks Future Fuels Public Fast Charging"]),
    frozenset(["NRMA National EV Charging Infrastructure Program", "Evie Networks National Ultrafast EV Charging Infrastructure Network"]),
    frozenset(["RayGen Solar Power Plant 1 (SPP1)", "RayGen Solar Power Plant 2 (SPP2) Phase 1"]),
    frozenset(["RayGen Solar Power Plant One (SPP1)", "RayGen Solar Power Plant 2 (SPP2) Phase 1"]),
    frozenset(["Australian Hydrogen Centre – 10% Hydrogen Distribution Networks SA",
               "Australian Hydrogen Centre – 100% Hydrogen Distribution Networks Victoria Feasibility Study"]),
    frozenset(["UNSW High Efficiency Silicon Solar Cell Technology – Phase 1 (ARENA 1-A060)",
               "UNSW High Efficiency Silicon Solar Cell Technology – Phase 2 (ARENA Solar R&D Round 3)"]),
    frozenset(["AGL Nyngan Solar Plant", "AGL Energy Solar Project – Broken Hill Solar Plant"]),
    frozenset(["United Energy Demand Response Project", "United Energy Dynamic Voltage Management System (DVMS) Rollout"]),
}

MAJORITY_THRESHOLD = 0.70
PROJECT_LEVEL_FIELDS = ["project_type", "project_scale_band", "proponent_type"]


# ---------------------------------------------------------------------------
# Tier 1 helpers
# ---------------------------------------------------------------------------

def normalise_name(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[\(\)\[\]\-–—/]", " ", s)
    for w in ["project", "the", "a", "and", "&", "demonstration", "demo",
              "programme", "program", "phase", "1", "2", "3", "i", "ii",
              "iii", "pilot", "trial", "study", "australia", "australian",
              "arena", "energy", "power", "renewable", "renewables"]:
        s = re.sub(r"\b" + w + r"\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def remap_tech_domain(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    if raw in VALID_TECH:
        return raw, None
    lower = raw.lower()
    for keywords, canonical in TECH_DOMAIN_RULES:
        if any(kw in lower for kw in keywords):
            matched = next(kw for kw in keywords if kw in lower)
            return canonical, f"keyword match on '{matched}'"
    return "other", "no keyword match — fallback to other"


def fix_project_type(raw: str | None) -> tuple[str | None, str | None]:
    if not raw or raw in VALID_PROJECT_TYPES:
        return raw, None
    mapped = PROJECT_TYPE_MAP.get(raw.lower())
    if mapped:
        return mapped, f"technology name '{raw}' remapped to delivery archetype"
    return raw, None


def fix_scale_band(raw: str | None) -> tuple[str | None, str | None]:
    if raw == "concept/feasibility":
        return None, "lifecycle_phase value leaked into scale_band — nulled"
    return raw, None


def fix_failure_mode(raw: str | None) -> tuple[str | None, str | None]:
    if not raw or raw in VALID_FAILURE_MODES:
        return raw, None
    mapped = FAILURE_MODE_MAP.get(raw.lower())
    if mapped:
        return mapped, f"off-taxonomy value '{raw}' remapped"
    return raw, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",
                        default=str(ROOT / "insights" / "registry_deduped.yaml"))
    parser.add_argument("--output",
                        default=str(ROOT / "insights" / "registry_deduped_clean.yaml"))
    args = parser.parse_args()

    in_path = Path(args.input)
    out_clean = Path(args.output)
    out_audit = Path(str(out_clean).replace("_clean.yaml", "_audit.yaml"))
    out_clean.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {in_path.name}")
    with open(in_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    if isinstance(records, dict):
        records = records.get("records", [])
    print(f"  {len(records)} records")

    audit = []

    def log(record_id, field, old, new, reason, tier):
        audit.append({"record_id": record_id, "field": field,
                      "old_value": old, "new_value": new,
                      "reason": reason, "tier": tier})

    # ------------------------------------------------------------------
    # Build project name canonicalisation map
    # ------------------------------------------------------------------
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
            if frozenset([n1, n2]) in DO_NOT_MERGE:
                continue
            if fuzz.token_sort_ratio(n1n, normalise_name(n2)) >= 82:
                union(n1, n2)

    clusters: dict[str, list] = defaultdict(list)
    for n in raw_names:
        clusters[find(n)].append(n)
    name_to_canon = {v: min(variants, key=lambda x: (len(x), x))
                     for variants in clusters.values() for v in variants}

    # ------------------------------------------------------------------
    # Tier 1: deterministic fixes
    # ------------------------------------------------------------------
    for r in records:
        rid = r.get("record_id", "?")

        raw_name = (r.get("project_name") or "").strip()
        canon = name_to_canon.get(raw_name, raw_name)
        if canon != raw_name:
            log(rid, "project_name", raw_name, canon, "fuzzy name canonicalisation", "1-name")
            r["project_name"] = canon

        for fixer, field in [
            (remap_tech_domain, "technology_domain"),
            (fix_project_type, "project_type"),
            (fix_scale_band, "project_scale_band"),
            (fix_failure_mode, "failure_mode"),
        ]:
            old = r.get(field)
            new, reason = fixer(old)
            if new != old:
                log(rid, field, old, new, reason, "1")
                r[field] = new

    # ------------------------------------------------------------------
    # Tier 2: majority-vote harmonisation
    # ------------------------------------------------------------------
    # Identify cross-cutting project groups — skip majority vote for these.
    # A project group is cross-cutting if the majority of its records have
    # no kb_associated_project (KB couldn't link to a single project) or
    # if the majority have project_scale_band = programmatic/portfolio-level.
    proj_record_counts: dict[str, int] = Counter()
    proj_crosscutting_signals: dict[str, int] = Counter()
    for r in records:
        proj = r.get("project_name") or ""
        proj_record_counts[proj] += 1
        if not r.get("kb_associated_project") or r.get("project_scale_band") == "programmatic/portfolio-level":
            proj_crosscutting_signals[proj] += 1
    crosscutting_projects = {
        proj for proj, signals in proj_crosscutting_signals.items()
        if signals / proj_record_counts[proj] >= 0.5
    }
    print(f"  Cross-cutting project groups (skipping majority vote): {len(crosscutting_projects)}")

    proj_votes: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for r in records:
        proj = r.get("project_name") or ""
        if proj in crosscutting_projects:
            continue
        for f in PROJECT_LEVEL_FIELDS:
            v = r.get(f)
            if v:
                proj_votes[proj][f][v] += 1

    proj_majority: dict[str, dict] = {}
    contested_projects: set = set()

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

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
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
        print("  Run 05b_reconcile_contested.py to resolve these via LLM.")
    print(f"\nSaved: {out_clean}")
    print(f"Saved: {out_audit}")


if __name__ == "__main__":
    main()
