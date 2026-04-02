"""
ARENA Taxonomy v2 — Category mapping module.

Maps raw KB metadata categories to 14 normalised arena_category values.
Provides consortium reclassification helpers and website filter reverse-lookup.
"""

import csv
import os
import yaml
from collections import Counter

# ---------------------------------------------------------------------------
# 1. Raw KB category → arena_category (14 active values, 3 excluded)
# ---------------------------------------------------------------------------

ARENA_CATEGORY_MAP = {
    # 9 current website filter categories
    "Battery storage":                          "Battery storage",
    "Bioenergy / Energy from waste":            "Bioenergy",
    "Concentrated solar thermal":               "Solar thermal",
    "Demand response":                          "Demand response",
    "Distributed energy resources":             "Distributed energy resources",
    "Electric vehicles":                        "Electric vehicles",
    "Geothermal energy":                        None,   # excluded — too few records
    "Hybrid technologies":                      "Hybrid technologies",
    "Hydrogen energy":                          "Hydrogen",
    # Legacy / unlisted categories
    "Solar energy":                             "Solar PV",
    "Solar PV R&D":                             "Solar PV",
    "Large-scale solar":                        "Solar PV",
    "Renewables for industry":                  "Industrial renewables",
    "System security and reliability":          "Grid stability",
    "Wind energy":                              "Wind",
    "Hydropower / Pumped Hydro Energy Storage": "Pumped hydro",
    "Renewables in buildings":                  "Distributed energy resources",
    "Off grid":                                 "Off grid",
    "Ocean energy":                             None,   # excluded — too few records
    "General":                                  None,
}

# Categories excluded from reference class matrices (but records preserved)
EXCLUDED_RAW_CATEGORIES = {"Geothermal energy", "Ocean energy", "General"}

# The 14 active arena_category values
ARENA_CATEGORIES = sorted({v for v in ARENA_CATEGORY_MAP.values() if v is not None})

# ---------------------------------------------------------------------------
# 2. Website filter reverse-lookup (9 ARENA KB website filters → leaf values)
# ---------------------------------------------------------------------------

WEBSITE_FILTER_REVERSE = {
    "Battery storage":                ["Battery storage"],
    "Bioenergy / Energy from waste":  ["Bioenergy"],
    "Concentrated solar thermal":     ["Solar thermal"],
    "Demand response":                ["Demand response"],
    "Distributed energy resources":   ["Distributed energy resources"],
    "Electric vehicles":              ["Electric vehicles"],
    "Geothermal energy":              [],          # excluded from matrices
    "Hybrid technologies":            ["Hybrid technologies"],
    "Hydrogen energy":                ["Hydrogen"],
}

# ---------------------------------------------------------------------------
# 3. Helpers: map a record's kb_category string → list of arena_category values
# ---------------------------------------------------------------------------

def map_kb_categories(kb_category_str):
    """
    Map a comma-separated kb_category string to a list of arena_category values.
    Returns (mapped_list, excluded_list) where excluded_list contains raw values
    that mapped to None.
    """
    if not kb_category_str:
        return [], []
    raw_cats = [c.strip() for c in kb_category_str.split(",") if c.strip()]
    mapped = []
    excluded = []
    for raw in raw_cats:
        val = ARENA_CATEGORY_MAP.get(raw)
        if val is not None:
            if val not in mapped:
                mapped.append(val)
        else:
            excluded.append(raw)
    return mapped, excluded


# ---------------------------------------------------------------------------
# 4. Consortium reclassification helpers
# ---------------------------------------------------------------------------

# Known lead-org keywords → proponent_type mapping
# Used for consortium projects where all docs were classified as consortium
LEAD_ORG_PROPONENT_MAP = [
    # Utilities / energy retailers
    (["agl", "origin energy", "energyaustralia", "engie", "synergy",
      "ergon", "alinta", "momentum energy", "simply energy", "lumo",
      "red energy", "powershop", "actewagl", "aurora energy"],
     "utility/energy retailer"),
    # Network businesses
    (["ausgrid", "endeavour energy", "essential energy", "ausnet",
      "powercor", "citipower", "united energy", "jemena",
      "sa power networks", "sapn", "energex", "western power",
      "electricity networks corporation", "transgrid", "electranet",
      "powerlink", "tasnetworks", "evoenergy", "horizon power"],
     "network business"),
    # Government / public-sector
    (["aemo", "arena", "cefc", "csiro", "department of",
      "government", "council", "shire", "city of", "state of"],
     "government/public-sector body"),
    # Research / university
    (["university", "anu", "unsw", "monash", "curtin", "uq ",
      "rmit", "uts ", "deakin", "flinders", "murdoch", "swinburne",
      "national university", "institute", "acap", "desert knowledge"],
     "research organisation/university"),
    # Industrial operators
    (["rio tinto", "bhp", "fortescue", "fmg", "alcoa", "yara",
      "orica", "incitec", "boral", "bluescope", "cement australia",
      "nyrstar", "tomago", "sun metals"],
     "industrial operator"),
    # Fleet / logistics
    (["zenobe", "bus", "fleet", "transit", "transport for",
      "keolis", "transdev"],
     "fleet/logistics operator"),
    # Manufacturers / OEM
    (["vestas", "goldwind", "tesla", "lg ", "samsung", "byd",
      "sungrow", "trina", "longi", "jinko"],
     "manufacturer/OEM"),
    # Technology vendors
    (["dnv", "worley", "ghd", "jacobs", "aurecon",
      "imc", "luceo", "redback", "reposit", "evergen",
      "brighte", "sonnen", "enphase", "solaredge"],
     "technology vendor"),
    # Project developers
    (["neoen", "tilt renewables", "goldwind", "edify", "photon",
      "maoneng", "canadian solar", "risen", "vena energy",
      "genex", "squadron", "cwe ", "acen", "amp energy"],
     "project developer"),
    # Community / local
    (["community", "aboriginal", "indigenous", "cooperative",
      "co-operative", "hepburn"],
     "community/local body"),
]


def classify_lead_org(lead_org_str):
    """
    Attempt to classify a lead organisation string into a proponent_type.
    Returns the proponent_type string or None if unresolvable.
    """
    if not lead_org_str:
        return None
    lower = lead_org_str.lower()
    for keywords, ptype in LEAD_ORG_PROPONENT_MAP:
        for kw in keywords:
            if kw in lower:
                return ptype
    return None


def _classify_from_project_name(pname):
    """
    Fallback: infer proponent_type from clues in the project name itself.
    """
    lower = pname.lower()
    # Portfolio-level / ARENA program records → government
    if any(k in lower for k in ["portfolio", "arena ", "fpdi", "general",
                                 "industry –", "industry —", "insights forum",
                                 "customer insights series", "analogue lesson"]):
        return "government/public-sector body"
    # University clues in name
    if any(k in lower for k in ["university", "(anu)", "(unsw)", "monash",
                                 "(uq)", "curtin"]):
        return "research organisation/university"
    # Named companies in project name
    for kw, pt in [
        ("agl", "utility/energy retailer"),
        ("jemena", "network business"),
        ("fortescue", "industrial operator"),
        ("yara", "industrial operator"),
        ("reposit", "technology vendor"),
        ("brighte", "technology vendor"),
        ("east kimberley", "community/local body"),
        ("aboriginal", "community/local body"),
    ]:
        if kw in lower:
            return pt
    return None


def build_consortium_reclassification(per_doc_dir, projects_csv_path):
    """
    Build a mapping: project_name → reclassified proponent_type for consortium projects.

    Strategy:
    1. Sibling-doc vote: if other docs for the same project have a non-consortium
       proponent_type, use majority vote.
    2. Lead-org keyword match from projects CSV.
    3. Project-name keyword match.
    4. Default remaining to government/public-sector body (most are ARENA
       portfolio-level assessments).

    Returns:
        (reclassified: dict[str, str], unresolved: list[str], stats: dict)
    """
    # Collect all proponent_types per project
    project_pts = {}  # project_name → Counter of proponent_types
    consortium_projects = set()

    for fn in sorted(os.listdir(per_doc_dir)):
        if not fn.endswith(".yaml"):
            continue
        with open(os.path.join(per_doc_dir, fn)) as f:
            records = yaml.safe_load(f)
        if not records or not isinstance(records, list):
            continue
        for rec in records:
            pname = rec.get("kb_associated_project") or rec.get("project_name") or ""
            pt = rec.get("proponent_type") or ""
            if not pname or not pt:
                continue
            if pname not in project_pts:
                project_pts[pname] = Counter()
            project_pts[pname][pt] += 1
            if "consortium" in pt.lower():
                consortium_projects.add(pname)

    # Strategy 1: sibling-doc vote
    reclassified = {}
    still_unresolved = []
    sibling_resolved = 0

    for pname in consortium_projects:
        pts = project_pts[pname]
        non_consortium = {k: v for k, v in pts.items()
                         if "consortium" not in k.lower()}
        if non_consortium:
            best = max(non_consortium, key=non_consortium.get)
            reclassified[pname] = best
            sibling_resolved += 1
        else:
            still_unresolved.append(pname)

    # Strategy 2: lead-org keyword match from projects CSV
    projects_csv = {}
    if os.path.exists(projects_csv_path):
        with open(projects_csv_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = (row.get("Project") or "").strip()
                lead = (row.get("Lead organisation") or "").strip()
                if name:
                    projects_csv[name] = lead

    leadorg_resolved = 0
    name_resolved = 0
    defaulted = 0
    final_unresolved = []

    for pname in still_unresolved:
        lead = projects_csv.get(pname, "")
        pt = classify_lead_org(lead)
        if pt:
            reclassified[pname] = pt
            leadorg_resolved += 1
            continue

        # Strategy 3: project-name keyword match
        pt = _classify_from_project_name(pname)
        if pt:
            reclassified[pname] = pt
            name_resolved += 1
            continue

        # Strategy 4: default remaining to government (mostly ARENA portfolio records)
        reclassified[pname] = "government/public-sector body"
        defaulted += 1

    stats = {
        "total_consortium_projects": len(consortium_projects),
        "sibling_resolved": sibling_resolved,
        "leadorg_resolved": leadorg_resolved,
        "name_resolved": name_resolved,
        "defaulted": defaulted,
        "unresolved": len(final_unresolved),
    }
    return reclassified, final_unresolved, stats


# ---------------------------------------------------------------------------
# 5. CLI: test the mappings
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("ARENA Category Map — 14 active values:")
    for cat in ARENA_CATEGORIES:
        sources = [k for k, v in ARENA_CATEGORY_MAP.items() if v == cat]
        print(f"  {cat:30s} ← {', '.join(sources)}")

    print(f"\nExcluded from matrices: {EXCLUDED_RAW_CATEGORIES}")

    print("\nWebsite filter reverse-lookup:")
    for filt, vals in WEBSITE_FILTER_REVERSE.items():
        print(f"  {filt:35s} → {vals}")

    # Test consortium reclassification if data available
    per_doc = os.path.join(os.path.dirname(__file__), "..", "insights", "per_doc")
    csv_path = os.path.join(os.path.dirname(__file__), "..", "arena-projects-export_1772932404.csv")
    if os.path.isdir(per_doc):
        print("\nBuilding consortium reclassification...")
        reclass, unresolved, stats = build_consortium_reclassification(per_doc, csv_path)
        print(f"  Consortium projects: {stats['total_consortium_projects']}")
        print(f"  Sibling-doc resolved: {stats['sibling_resolved']}")
        print(f"  Lead-org resolved: {stats['leadorg_resolved']}")
        print(f"  Name-resolved: {stats['name_resolved']}")
        print(f"  Defaulted to govt: {stats['defaulted']}")
        print(f"  Unresolved: {stats['unresolved']}")
