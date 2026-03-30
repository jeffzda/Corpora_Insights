#!/usr/bin/env python3
"""
Produce ARENA_delivery_registry_full_v2_clean.yaml with three tiers of cleaning:

Tier 1 — Deterministic rule-based fixes:
  - technology_domain: remap freetext to canonical taxonomy values
  - project_scale_band: "concept/feasibility" is a lifecycle value, null it
  - project_type: technology names used instead of delivery archetypes → remap
  - failure_mode: "procurement/supply chain" → "resource/capability shortfall"

Tier 2 — Majority-vote harmonisation for project-level fields:
  - project_type, project_scale_band, proponent_type
  - Apply only where majority ≥ 70% of non-null values for that project
  - Flag contested projects (majority < 70%) in confidence_note

Outputs:
  insights/ARENA_delivery_registry_full_v2_clean.yaml
  insights/ARENA_delivery_registry_full_v2_audit.yaml
"""

import yaml
import re
from collections import defaultdict, Counter

from rapidfuzz import fuzz

# ─────────────────────────────────────────────
# 0. Load
# ─────────────────────────────────────────────
with open("insights/ARENA_delivery_registry_full_v1_clean.yaml") as f:
    records = yaml.safe_load(f)

audit = []  # list of {record_id, field, old_value, new_value, reason, tier}


def log(record_id, field, old, new, reason, tier):
    audit.append({
        "record_id": record_id,
        "field": field,
        "old_value": old,
        "new_value": new,
        "reason": reason,
        "tier": tier,
    })


# ─────────────────────────────────────────────
# 1. Project name canonicalisation
# ─────────────────────────────────────────────
raw_names = sorted(set(r.get("project_name", "") or "" for r in records))
raw_names = [n for n in raw_names if n]


def normalise(s):
    s = s.lower()
    s = re.sub(r'[\(\)\[\]\-–—/]', ' ', s)
    for word in ['project', 'the', 'a', 'and', '&', 'demonstration', 'demo',
                 'programme', 'program', 'phase', '1', '2', '3', 'i', 'ii',
                 'iii', 'pilot', 'trial', 'study', 'australia', 'australian',
                 'arena', 'energy', 'power', 'renewable', 'renewables']:
        s = re.sub(r'\b' + word + r'\b', '', s)
    return re.sub(r'\s+', ' ', s).strip()


DO_NOT_MERGE = {
    frozenset(["Lake Bonney Battery Energy Storage System", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Broken Hill Battery Energy Storage System (BHBESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Liddell Battery Energy Storage System (AGL)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Liddell Battery Energy Storage System (BESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System", "Liddell Battery Energy Storage System (LIDBESS) — AGL"]),
    frozenset(["Lake Bonney Battery Energy Storage System (BESS)", "Liddell Battery Energy Storage System (AGL)"]),
    frozenset(["Lake Bonney Battery Energy Storage System (BESS)", "Liddell Battery Energy Storage System (BESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System (BESS)", "Broken Hill Battery Energy Storage System (BHBESS)"]),
    frozenset(["Lake Bonney Battery Energy Storage System (BESS)", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["Liddell Battery Energy Storage System (AGL)", "Broken Hill Battery Energy Storage System (BHBESS)"]),
    frozenset(["Liddell Battery Energy Storage System (AGL)", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["Liddell Battery Energy Storage System (BESS)", "Broken Hill Battery Energy Storage System (BHBESS)"]),
    frozenset(["Liddell Battery Energy Storage System (BESS)", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["Broken Hill Battery Energy Storage System (BHBESS)", "Blyth Battery Energy Storage System (BBESS)"]),
    frozenset(["ENGIE Future Fuels Public Fast Charging", "Evie Networks Future Fuels Public Fast Charging"]),
    frozenset(["ENGIE Future Fuels Public Fast Charging Network", "Evie Networks Future Fuels Public Fast Charging"]),
    frozenset(["ENGIE Future Fuels Public Fast Charging Program", "Evie Networks Future Fuels Public Fast Charging Program"]),
    frozenset(["NRMA National EV Charging Infrastructure Program", "Evie Networks National Ultrafast EV Charging Infrastructure Network"]),
    frozenset(["NRMA National EV Charging Infrastructure Program", "National Ultrafast EV Charging Infrastructure Network (Evie Networks)"]),
    frozenset(["RayGen Solar Power Plant 1 (SPP1)", "RayGen Solar Power Plant 2 (SPP2) Phase 1"]),
    frozenset(["RayGen Solar Power Plant One (SPP1)", "RayGen Solar Power Plant 2 (SPP2) Phase 1"]),
    frozenset(["RayGen Solar Power Plant One (SPP1) Demonstration Project", "RayGen Solar Power Plant 2 (SPP2) Phase 1"]),
    frozenset(["Australian Hydrogen Centre – 10% Hydrogen Distribution Networks SA",
               "Australian Hydrogen Centre – 100% Hydrogen Distribution Networks Victoria Feasibility Study"]),
    frozenset(["UNSW High Efficiency Silicon Solar Cell Technology – Phase 1 (ARENA 1-A060)",
               "UNSW High Efficiency Silicon Solar Cell Technology – Phase 2 (ARENA Solar R&D Round 3)"]),
    frozenset(["AGL Nyngan Solar Plant", "AGL Energy Solar Project – Broken Hill Solar Plant"]),
    frozenset(["AGL Energy Nyngan Solar Plant", "AGL Energy Solar Project – Broken Hill Solar Plant"]),
    frozenset(["United Energy Demand Response Project", "United Energy Dynamic Voltage Management System (DVMS) Rollout"]),
    frozenset(["United Energy Demand Response Project (DVMS)", "United Energy Dynamic Voltage Management System (DVMS) Rollout"]),
    frozenset(["United Energy Dynamic Voltage Management System (DVMS) Rollout",
               "United Energy Demand Response Project - Dynamic Voltage Management System (DVMS)"]),
}

parent = {n: n for n in raw_names}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        if len(ra) <= len(rb):
            parent[rb] = ra
        else:
            parent[ra] = rb


for i, n1 in enumerate(raw_names):
    n1n = normalise(n1)
    for n2 in raw_names[i + 1:]:
        if frozenset([n1, n2]) in DO_NOT_MERGE:
            continue
        if fuzz.token_sort_ratio(n1n, normalise(n2)) >= 82:
            union(n1, n2)

clusters = defaultdict(list)
for n in raw_names:
    clusters[find(n)].append(n)

name_to_canon = {}
for canon, variants in clusters.items():
    chosen = min(variants, key=lambda x: (len(x), x))
    for v in variants:
        name_to_canon[v] = chosen

# ─────────────────────────────────────────────
# TIER 1a: technology_domain remapping
# ─────────────────────────────────────────────
VALID_TECH = {
    "battery storage", "hydrogen", "solar PV", "solar thermal", "wind", "DER",
    "demand response", "EV", "bioenergy", "industrial renewables",
    "grid/system stability", "hybrid systems", "pumped hydro", "other"
}

# Ordered rules: (keywords_any, canonical_value)
# Earlier rules take priority. Keywords matched against lowercased domain string.
TECH_DOMAIN_RULES = [
    # Pumped hydro — must come before "hydro" catches hydrogen
    (["pumped hydro", "pumped storage hydro", "phes", "pumped storage"], "pumped hydro"),
    # Geothermal / wave / tidal → other
    (["geothermal", "wave energy", "tidal", "ocean energy", "wave swell"], "other"),
    # Solar thermal — before solar PV so "concentrating solar" doesn't hit PV
    (["solar thermal", "concentrating solar", "csp", "cst", "heliostat",
      "linear fresnel", "solar air turbine", "solar dish", "solar tower",
      "solar fuels", "solar gasification", "thermoelectric", "solar cooling",
      "solar steam", "solar redox"], "solar thermal"),
    # Hydrogen — before generic "solar PV" to catch "solar-driven hydrogen"
    (["hydrogen", "electrolysis", "electrolyser", "pem electrolysis",
      "alkaline electrolysis", "green hydrogen", "h2xport", "hazer",
      "power-to-gas", "ammonia synthesis", "electrochemical hydrogen",
      "water splitting", "hydrogen blending", "hydrogen distribution",
      "hydrogen pipeline", "hydrogen appliance", "hydrogen storage",
      "liquefied hydrogen", "hydrogen calcination"], "hydrogen"),
    # Solar PV — silicon cell research, perovskite, manufacturing
    (["solar pv", "solar cell", "silicon pv", "silicon solar", "perovskite",
      "photovoltaic", "pv module", "pv manufacturing", "pv thermal",
      "solar irradiance", "solar forecasting", "solar resource",
      "monocrystalline", "polysilicon", "topcon", "perc", "hjt", "ibc",
      "bifacial", "thin-film", "sliver cell", "laser crystallisation",
      "silicon ingot", "solar construction", "module manufacturing"], "solar PV"),
    # Wind
    (["wind", "wind forecasting", "wind farm", "wind turbine", "lidar",
      "wind power forecasting", "wind fcas"], "wind"),
    # EV — before DER to prevent VPP+EV being classified as DER
    (["electric vehicle", "ev charging", "ev smart charging", "vehicle-to-grid",
      "v2g", "fleet charging", "ev fleet", "ev fast charging", "dc fast charging",
      "battery electric", "bev", "phev", "evse", "ocpp", "tesla fleet",
      "fleet electrification", "charging network", "charging infrastructure",
      "kerbside ev", "pole-mounted charger"], "EV"),
    # Demand response — before DER
    (["demand response", "rert", "load control", "load curtailment",
      "behavioural demand", "behavioural dr", "smart hot water", "controlled load",
      "ripple control", "hvac control", "direct load control",
      "demand aggregation", "demand flexibility", "demand management"], "demand response"),
    # DER / VPP
    (["der", "vpp", "virtual power plant", "operating envelope",
      "dynamic operating envelope", "der orchestration", "der coordination",
      "der aggregation", "der integration", "cer data", "consumer energy resources",
      "distribution system operator", "rooftop pv inverter", "behind-the-meter"], "DER"),
    # Battery storage — BESS, grid-scale, grid-forming
    (["bess", "battery storage", "battery energy storage", "grid-scale bess",
      "grid-forming bess", "grid forming bess", "lithium-ion battery",
      "lithium ion battery", "vanadium flow", "flow battery", "nas battery",
      "residential battery", "community battery", "battery test centre",
      "synthetic inertia", "virtual machine mode", "vmm", "fast frequency response",
      "grid-forming inverter", "grid forming inverter", "fcas bess",
      "hornsdale", "wallgrove", "lake bonney", "liddell bess",
      "battery electric trucks", "bess energy arbitrage"], "battery storage"),
    # Bioenergy
    (["bioenergy", "biomass", "biogas", "biomethane", "biofuel", "bio-oil",
      "biochar", "anaerobic digestion", "gasification", "pyrolysis",
      "waste-to-energy", "energy from waste", "hefa", "saf", "sustainable aviation",
      "renewable diesel", "fischer-tropsch", "biorefinery", "fogo"], "bioenergy"),
    # Industrial renewables
    (["industrial", "process heat", "heat pump", "alumina", "steel",
      "ironmaking", "dri", "iron ore", "ammonia", "fertiliser",
      "calcination", "decarbonisation", "electrification of industry",
      "industrial decarbonisation", "industrial demand response",
      "industrial heat", "mechanical vapour", "mvr",
      "electric arc furnace", "high temperature", "thermal energy storage",
      "aquatic centre", "building electrification", "hvac", "refrigeration",
      "waste heat recovery"], "industrial renewables"),
    # Grid / system stability
    (["grid", "network", "system strength", "frequency control", "inertia",
      "fcas", "harmonic", "power quality", "grid connection",
      "emt modelling", "pscad", "protection relay", "islanding",
      "grid-forming", "inverter-based resources", "grid stability",
      "causer pays", "primary frequency", "system restart",
      "ancillary services", "low voltage feeder", "lvft",
      "dynamic model validation", "voltage management", "network tariff",
      "distribution network", "transmission"], "grid/system stability"),
    # Hybrid / off-grid
    (["hybrid", "microgrid", "off-grid", "remote community", "solar-diesel",
      "wind-solar hybrid", "battery-solar", "solar pv bess",
      "containerised hybrid", "hybrid renewable", "hybrid power"], "hybrid systems"),
]


def remap_tech_domain(raw):
    if not raw:
        return None, None
    if raw in VALID_TECH:
        return raw, None
    lower = raw.lower()
    for keywords, canonical in TECH_DOMAIN_RULES:
        if any(kw in lower for kw in keywords):
            return canonical, f"keyword match on '{next(kw for kw in keywords if kw in lower)}'"
    return "other", "no keyword match — fallback to other"


# ─────────────────────────────────────────────
# TIER 1b: project_type remapping
# ─────────────────────────────────────────────
VALID_PROJECT_TYPES = {
    "generation", "storage", "network/grid", "DER/customer-side",
    "transport electrification", "industrial decarbonisation",
    "manufacturing/supply chain", "software/data/digital",
    "enabling infrastructure", "multi-technology/hybrid"
}

PROJECT_TYPE_MAP = {
    "solar thermal": "generation",
    "solar pv": "generation",
    "hydrogen": "industrial decarbonisation",
    "bioenergy": "generation",
    "programmatic/portfolio-level": "enabling infrastructure",
}


def fix_project_type(raw):
    if not raw or raw in VALID_PROJECT_TYPES:
        return raw, None
    mapped = PROJECT_TYPE_MAP.get(raw.lower())
    if mapped:
        return mapped, f"technology name '{raw}' remapped to delivery archetype"
    return raw, None


# ─────────────────────────────────────────────
# TIER 1c: project_scale_band fix
# ─────────────────────────────────────────────
VALID_SCALE_BANDS = {
    "lab/bench", "pilot", "demonstration", "first commercial/FOAK",
    "commercial expansion", "utility/large-scale", "programmatic/portfolio-level",
    "concept/feasibility"  # we will null these
}


def fix_scale_band(raw):
    if raw == "concept/feasibility":
        return None, "lifecycle_phase value leaked into scale_band — nulled"
    return raw, None


# ─────────────────────────────────────────────
# TIER 1d: failure_mode fix
# ─────────────────────────────────────────────
VALID_FAILURE_MODES = {
    "no major failure stated", "technical underperformance", "integration failure",
    "schedule slippage", "cost overrun", "resource/capability shortfall",
    "commercial/demand failure", "regulatory misfit", "data quality/measurement failure",
    "design assumption failure", "governance/coordination failure"
}

FAILURE_MODE_MAP = {
    "procurement/supply chain": "resource/capability shortfall",
}


def fix_failure_mode(raw):
    if not raw or raw in VALID_FAILURE_MODES:
        return raw, None
    mapped = FAILURE_MODE_MAP.get(raw.lower())
    if mapped:
        return mapped, f"off-taxonomy value '{raw}' remapped"
    return raw, None


# ─────────────────────────────────────────────
# Apply Tier 1 to all records
# ─────────────────────────────────────────────
for r in records:
    rid = r.get("record_id", "?")

    # project_name canonicalisation
    raw_name = r.get("project_name", "") or ""
    canon_name = name_to_canon.get(raw_name, raw_name)
    if canon_name != raw_name:
        log(rid, "project_name", raw_name, canon_name, "fuzzy name canonicalisation", "1-name")
        r["project_name"] = canon_name

    # technology_domain
    td = r.get("technology_domain")
    new_td, reason = remap_tech_domain(td)
    if new_td != td:
        log(rid, "technology_domain", td, new_td, reason, "1a")
        r["technology_domain"] = new_td

    # project_type
    pt = r.get("project_type")
    new_pt, reason = fix_project_type(pt)
    if new_pt != pt:
        log(rid, "project_type", pt, new_pt, reason, "1b")
        r["project_type"] = new_pt

    # project_scale_band
    sb = r.get("project_scale_band")
    new_sb, reason = fix_scale_band(sb)
    if new_sb != sb:
        log(rid, "project_scale_band", sb, new_sb, reason, "1c")
        r["project_scale_band"] = new_sb

    # failure_mode
    fm = r.get("failure_mode")
    new_fm, reason = fix_failure_mode(fm)
    if new_fm != fm:
        log(rid, "failure_mode", fm, new_fm, reason, "1d")
        r["failure_mode"] = new_fm


# ─────────────────────────────────────────────
# TIER 2: Majority-vote harmonisation
# ─────────────────────────────────────────────
PROJECT_LEVEL_FIELDS = ["project_type", "project_scale_band", "proponent_type"]
MAJORITY_THRESHOLD = 0.70

# Build vote tallies per canonical project
proj_votes = defaultdict(lambda: defaultdict(Counter))
for r in records:
    proj = r.get("project_name", "") or ""
    for f in PROJECT_LEVEL_FIELDS:
        v = r.get(f)
        if v:
            proj_votes[proj][f][v] += 1

# For each project, determine majority value (if any clears threshold)
proj_majority = {}  # proj → {field → (majority_val, pct, contested)}
contested_projects = set()

for proj, fields in proj_votes.items():
    proj_majority[proj] = {}
    for f, ctr in fields.items():
        total = sum(ctr.values())
        top_val, top_count = ctr.most_common(1)[0]
        pct = top_count / total
        if len(ctr) == 1:
            # Already unanimous — record for completeness but no change needed
            proj_majority[proj][f] = (top_val, 1.0, False)
        elif pct >= MAJORITY_THRESHOLD:
            proj_majority[proj][f] = (top_val, pct, False)
        else:
            # Contested — flag but don't overwrite
            proj_majority[proj][f] = (top_val, pct, True)
            contested_projects.add((proj, f))

# Apply majority vote
for r in records:
    proj = r.get("project_name", "") or ""
    rid = r.get("record_id", "?")
    existing_note = r.get("confidence_note") or ""

    for f in PROJECT_LEVEL_FIELDS:
        current = r.get(f)
        if proj not in proj_majority or f not in proj_majority[proj]:
            continue
        majority_val, pct, contested = proj_majority[proj][f]

        if contested:
            # Don't overwrite — just flag if not already flagged
            if "contested" not in existing_note:
                note = f"harmonisation-contested: {f} split ({dict(proj_votes[proj][f])})"
                r["confidence_note"] = (existing_note + "; " + note).lstrip("; ")
                log(rid, "confidence_note", existing_note or None,
                    r["confidence_note"],
                    f"field {f} has no clear majority ({pct:.0%})", "2-contested")
        elif current != majority_val and current is not None:
            # Minority value — overwrite with majority
            log(rid, f, current, majority_val,
                f"majority-vote harmonisation ({pct:.0%} of project records)", "2-majority")
            r[f] = majority_val
        elif current is None and majority_val:
            # Null — fill from majority
            log(rid, f, None, majority_val,
                f"null filled from project majority ({pct:.0%})", "2-fill")
            r[f] = majority_val


# ─────────────────────────────────────────────
# Write outputs
# ─────────────────────────────────────────────
out_clean = "insights/ARENA_delivery_registry_full_v2_clean.yaml"
out_audit = "insights/ARENA_delivery_registry_full_v2_audit.yaml"

with open(out_clean, "w") as f:
    yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

with open(out_audit, "w") as f:
    yaml.dump(audit, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
from collections import Counter as C
tier_counts = C(a["tier"] for a in audit)
field_counts = C(a["field"] for a in audit)

print(f"Records processed:  {len(records)}")
print(f"Total changes made: {len(audit)}")
print()
print("Changes by tier:")
for tier in sorted(tier_counts):
    print(f"  {tier}: {tier_counts[tier]}")
print()
print("Changes by field:")
for field, count in field_counts.most_common():
    print(f"  {field}: {count}")
print()
print(f"Contested projects (no clear majority, flagged only): {len(contested_projects)}")
for proj, f in sorted(contested_projects):
    votes = dict(proj_votes[proj][f])
    print(f"  {proj[:55]} | {f}: {votes}")
print()
print(f"Written: {out_clean}")
print(f"Written: {out_audit}")
