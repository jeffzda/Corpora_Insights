"""
ARENA Taxonomy v2 — Activity type classifier.

Deterministically classifies each ARENA project into one of:
  - Study / feasibility
  - Pilot / demonstration
  - Deployment
  - R&D (excluded from reference class matrices)

Classification uses project title, summary, program name, and investment size.
No LLM calls required.
"""

import csv
import os
import re
import sys
import yaml

# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

# Programs that indicate pure R&D — excluded from reference class matrices
RD_PROGRAMS = {
    "Post Fellowship Doctorate",
    "Australian Solar Institute",
    "Ultra Low Cost Solar PV Research and Development Round",
    "Hydrogen Research and Development Funding Round",
    "Iron and Steel Research and Development Funding Round",
    "Addressing Solar PV End-of-Life Issues and Lowering Solar PV Cost",
    "International Engagement Program",
    "Solar Sunshot",
    "Commercialisation of R&D Funding Initiative Pilot",
}

# Program substrings that indicate R&D
RD_PROGRAM_SUBSTRINGS = [
    "post fellowship",
    "fellowship",
    "international engagement",
]

# Keywords for each activity type (applied to title + summary, case-insensitive)
STUDY_KEYWORDS = [
    r"\bfeasibility\b", r"\bpre-feed\b", r"\bfeed\b(?!\s*stock)",
    r"\bassessment\b", r"\broadmap\b",
    r"\binvestigation\b", r"\bscoping\b", r"\bfront.end engineering\b",
    r"\bdesktop study\b", r"\btechno.economic\b", r"\bmarket analysis\b",
    r"\bfinal investment decision\b", r"\bfid\b",
]

# "study" and "review" need more context to avoid false positives
STUDY_KEYWORDS_CONTEXTUAL = [
    (r"\bstudy\b", [r"case study", r"study tour"]),  # exclude these contexts
    (r"\breview\b", [r"peer review", r"review panel", r"literature review"]),
]

RD_KEYWORDS = [
    r"\bresearch\b", r"\br&d\b", r"\blaboratory\b", r"\blab.scale\b",
    r"\bbench.scale\b", r"\bphd\b", r"\bdoctoral\b", r"\bacademic\b",
    r"\bfundamental\b", r"\bnovel material\b",
]

PILOT_KEYWORDS = [
    r"\bpilot\b", r"\btrial\b", r"\bdemonstrat", r"\bproof of concept\b",
    r"\btesting\b", r"\bvalidat", r"\bprototyp",
]

DEPLOYMENT_KEYWORDS = [
    r"\bconstruct", r"\bdeploy", r"\binstall", r"\bcommission",
    r"\bsolar farm\b", r"\bwind farm\b", r"\bbess\b",
    r"\belectrif", r"\bupgrad", r"\bretrofit", r"\brolling out\b",
    r"\broll.out\b", r"\bfull.scale\b", r"\bcommercial.scale\b",
    r"\butility.scale\b", r"\blarge.scale\b",
]

# MW/MWh/GW capacity mentions (strong deployment signal)
CAPACITY_PATTERN = re.compile(
    r"\b\d+\s*(?:MW|MWh|GW|GWh|kW(?:h)?)\b", re.IGNORECASE
)

# Investment-size fallback thresholds (total project value)
STUDY_MAX = 3_000_000
PILOT_MAX = 15_000_000


def _parse_money(s):
    """Parse '$5m', '$21.54m', '$94.72m', '$500,000' etc. to float."""
    if not s:
        return None
    s = s.strip().replace(",", "").replace("$", "")
    m = re.match(r"([\d.]+)\s*(m|b|k)?", s, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    suffix = (m.group(2) or "").lower()
    if suffix == "m":
        val *= 1_000_000
    elif suffix == "b":
        val *= 1_000_000_000
    elif suffix == "k":
        val *= 1_000
    return val


def _has_keyword(text, patterns):
    """Check if any regex pattern matches in text."""
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _has_contextual_keyword(text, contextual_list):
    """Check contextual keywords — match if keyword present but exclusion contexts absent."""
    for pat, exclusions in contextual_list:
        if re.search(pat, text, re.IGNORECASE):
            excluded = False
            for exc in exclusions:
                if re.search(exc, text, re.IGNORECASE):
                    excluded = True
                    break
            if not excluded:
                return True
    return False


def classify_project(title, summary, program, total_value_str):
    """
    Classify a single project into activity_type.

    Returns: (activity_type, rule_fired)
      activity_type: 'Study / feasibility' | 'Pilot / demonstration' | 'Deployment' | 'R&D' | None
      rule_fired: string describing which rule matched
    """
    text = f"{title} {summary}".strip()
    program_clean = (program or "").strip()

    # Rule 1: R&D programs
    if program_clean in RD_PROGRAMS:
        return "R&D", f"program:{program_clean}"
    for sub in RD_PROGRAM_SUBSTRINGS:
        if sub in program_clean.lower():
            return "R&D", f"program_substring:{sub}"

    # Rule 2: Study/feasibility keywords
    if _has_keyword(text, STUDY_KEYWORDS) or _has_contextual_keyword(text, STUDY_KEYWORDS_CONTEXTUAL):
        return "Study / feasibility", "keyword:study"

    # Rule 3: R&D keywords (after study, since FEED studies > R&D)
    if _has_keyword(text, RD_KEYWORDS):
        return "R&D", "keyword:rd"

    # Rule 4: Pilot/demonstration keywords
    if _has_keyword(text, PILOT_KEYWORDS):
        return "Pilot / demonstration", "keyword:pilot"

    # Rule 5: Deployment keywords or capacity mention
    if _has_keyword(text, DEPLOYMENT_KEYWORDS):
        return "Deployment", "keyword:deployment"
    if CAPACITY_PATTERN.search(text):
        return "Deployment", "keyword:capacity_MW"

    # Rule 6: Investment-size fallback
    total = _parse_money(total_value_str)
    if total is not None:
        if total <= STUDY_MAX:
            return "Study / feasibility", f"investment:{total/1e6:.1f}m<=3m"
        elif total <= PILOT_MAX:
            return "Pilot / demonstration", f"investment:{total/1e6:.1f}m<=15m"
        else:
            return "Deployment", f"investment:{total/1e6:.1f}m>15m"

    return None, "unclassified"


def classify_all_projects(csv_path):
    """
    Classify all projects from the CSV. Returns dict[project_name, dict].
    """
    results = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Project") or "").strip()
            if not name:
                continue
            title = name
            summary = (row.get("Summary/Information") or "").strip()
            program = (row.get("Arena program") or "").strip()
            total_val = (row.get("Total project value") or "").strip()
            arena_funding = (row.get("Arena funding provided") or "").strip()

            activity, rule = classify_project(title, summary, program, total_val)
            results[name] = {
                "activity_type": activity,
                "rule_fired": rule,
                "program": program,
                "total_value": total_val,
                "arena_funding": arena_funding,
            }
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), "..",
                            "arena-projects-export_1772932404.csv")
    results = classify_all_projects(csv_path)

    # Stats
    from collections import Counter
    type_counts = Counter(r["activity_type"] for r in results.values())
    rule_counts = Counter(r["rule_fired"].split(":")[0] for r in results.values())

    print(f"Total projects: {len(results)}")
    print(f"\nActivity type distribution:")
    for t, c in type_counts.most_common():
        print(f"  {c:4d}  {t}")
    print(f"\nRule distribution:")
    for r, c in rule_counts.most_common():
        print(f"  {c:4d}  {r}")

    # Show unclassified
    unclassified = [n for n, r in results.items() if r["activity_type"] is None]
    if unclassified:
        print(f"\nUnclassified ({len(unclassified)}):")
        for n in unclassified:
            print(f"  - {n}")

    # Show investment fallbacks
    fallbacks = [(n, r) for n, r in results.items() if r["rule_fired"].startswith("investment")]
    if fallbacks:
        print(f"\nInvestment fallbacks ({len(fallbacks)}):")
        for n, r in fallbacks[:15]:
            print(f"  {r['activity_type']:25s} {r['rule_fired']:25s} {n[:50]}")

    # Optional: write mapping YAML
    if "--write" in sys.argv:
        out_path = os.path.join(os.path.dirname(__file__), "..",
                                "insights", "activity_type_map.yaml")
        mapping = {name: info["activity_type"] for name, info in results.items()}
        with open(out_path, "w") as f:
            yaml.dump(mapping, f, default_flow_style=False, allow_unicode=True)
        print(f"\nWritten to {out_path}")
