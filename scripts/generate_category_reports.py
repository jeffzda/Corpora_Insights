#!/usr/bin/env python3
"""
Generate delivery risk narrative reports per ARENA category.

For each category with sufficient data, assembles a prompt package containing:
  - Pre-computed dimension × failure mode matrix (percentages + counts)
  - Severity escalation by failure mode
  - Coverage timeline (record count by year band, temporal flags)
  - Individual records (what_happened, lesson_learnt, failure_mode, severity,
    evidence_excerpt, publish_date, confidence_note)

Sends to Claude Sonnet for narrative synthesis. Output: one markdown file per
category in insights/reports/category_profiles/.

Usage:
    python scripts/generate_category_reports.py                    # all categories
    python scripts/generate_category_reports.py --category "Battery storage"
    python scripts/generate_category_reports.py --dry-run          # print prompt, no API
    python scripts/generate_category_reports.py --list             # list eligible categories
"""

import argparse
import json
import glob
import os
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    from ruamel.yaml import YAML
    _ry = YAML()
    class yaml:
        @staticmethod
        def safe_load(f): return _ry.load(f)

ROOT = Path(__file__).resolve().parent.parent
PER_DOC_DIR = ROOT / "insights" / "per_doc"
FM_V3_DIR = ROOT / "insights" / "per_doc_fm_v3"
DIMENSIONS_DIR = ROOT / "insights" / "per_doc_dimensions"
OUTPUT_DIR = ROOT / "insights" / "reports" / "category_profiles"

DIMENSION_ORDER = [
    "DESIGN", "PROCUREMENT", "CONSTRUCTION", "SOFTWARE_CONTROLS",
    "GRID_CONNECTION", "INTEGRATION_COMMISSIONING", "SITING",
    "COMMUNITY_ENGAGEMENT", "FINANCING", "OPERATIONS",
]
DIMENSION_SHORT = {
    "DESIGN": "Design",
    "PROCUREMENT": "Procurement",
    "CONSTRUCTION": "Construction",
    "SOFTWARE_CONTROLS": "Software & controls",
    "GRID_CONNECTION": "Grid connection",
    "INTEGRATION_COMMISSIONING": "Integration & commissioning",
    "SITING": "Siting",
    "COMMUNITY_ENGAGEMENT": "Community engagement",
    "FINANCING": "Financing",
    "OPERATIONS": "Operations",
}
FM_ORDER = [
    "commercial & market",
    "coordination & stakeholders",
    "data & measurement",
    "execution & logistics",
    "regulatory & approvals",
    "technical underperformance",
    "unvalidated integration",
]
NO_FAIL = "no major failure stated"
SEV_SEVERE = {"major", "critical"}
SEV_MILD = {"minor", "moderate"}
MIN_RECORDS = 50  # minimum records for a category report


def load_all_records():
    """Load all per_doc records with dimensions and v3 FM tags merged."""
    # Load per_doc records
    records = []
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            records.extend(data)

    # Load dimension tags
    dim_tags = {}
    if DIMENSIONS_DIR.exists():
        for path in sorted(glob.glob(str(DIMENSIONS_DIR / "doc_*_dimensions.yaml"))):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                for r in data:
                    rid = r.get("record_id")
                    if rid:
                        dim_tags[rid] = [d["id"] if isinstance(d, dict) else d
                                         for d in r.get("dimensions", [])]

    # Load v3 FM tags
    fm_tags = {}
    if FM_V3_DIR.exists():
        for path in sorted(glob.glob(str(FM_V3_DIR / "doc_*_fm_v3.yaml"))):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                for r in data:
                    rid = r.get("record_id")
                    if rid:
                        fm = r.get("failure_mode", "")
                        if fm and fm != "none":
                            entry = {"failure_mode": fm}
                            sfm = r.get("secondary_failure_mode")
                            if sfm:
                                entry["secondary_failure_mode"] = sfm
                            fm_tags[rid] = entry

    # Merge
    for r in records:
        rid = r.get("record_id")
        if rid:
            r["dimensions"] = dim_tags.get(rid, [])
            if rid in fm_tags:
                r["failure_mode"] = fm_tags[rid]["failure_mode"]
                r["secondary_failure_mode"] = fm_tags[rid].get("secondary_failure_mode")
            else:
                r["secondary_failure_mode"] = None

    print(f"Loaded {len(records)} records, {len(dim_tags)} dimension tags, {len(fm_tags)} FM tags")
    return records


def filter_by_category(records, category):
    """Filter records where arena_category list contains the given category."""
    return [r for r in records if category in (r.get("arena_category") or [])]


def build_dim_fm_matrix(recs):
    """Build dimension × failure mode matrix: percentages and counts."""
    # Count per dimension × FM
    dim_fm = defaultdict(Counter)  # dim → {fm: count}
    dim_totals = Counter()

    for r in recs:
        fm = r.get("failure_mode", "")
        if not fm or fm == NO_FAIL:
            continue
        for d in r.get("dimensions", []):
            if d in DIMENSION_ORDER:
                dim_fm[d][fm] += 1
                dim_totals[d] += 1

    # Build matrix
    rows = []
    for d in DIMENSION_ORDER:
        if dim_totals[d] == 0:
            continue
        row = {"dimension": DIMENSION_SHORT.get(d, d), "total_adverse": dim_totals[d]}
        for fm in FM_ORDER:
            cnt = dim_fm[d].get(fm, 0)
            pct = cnt / dim_totals[d] * 100 if dim_totals[d] > 0 else 0
            row[fm] = {"count": cnt, "pct": round(pct, 1)}
        rows.append(row)
    return rows


def build_fm_severity(recs):
    """Severity escalation by failure mode."""
    fm_severe = Counter()
    fm_mild = Counter()
    fm_total = Counter()

    for r in recs:
        fm = r.get("failure_mode", "")
        sev = r.get("issue_severity", "")
        if not fm or fm == NO_FAIL:
            continue
        fm_total[fm] += 1
        if sev in SEV_SEVERE:
            fm_severe[fm] += 1
        elif sev in SEV_MILD:
            fm_mild[fm] += 1

    result = []
    for fm in FM_ORDER:
        sv = fm_severe.get(fm, 0)
        ml = fm_mild.get(fm, 0)
        total = fm_total.get(fm, 0)
        if total == 0:
            continue
        esc = round(sv / (sv + ml) * 100, 1) if (sv + ml) > 0 else None
        result.append({
            "failure_mode": fm,
            "count": total,
            "severe": sv,
            "mild": ml,
            "escalation_pct": esc,
            "pct_of_adverse": round(total / sum(fm_total.values()) * 100, 1) if fm_total else 0,
        })
    return sorted(result, key=lambda x: x["count"], reverse=True)


def build_coverage_timeline(recs):
    """Record and project counts by year band, plus temporal flag stats."""
    year_counts = Counter()
    year_projects = defaultdict(set)
    flagged = 0
    flagged_years = Counter()

    for r in recs:
        # Extract year from kb_publish_date (DD/MM/YYYY) or publish_date (YYYY or YYYY-MM)
        year = None
        pd = r.get("kb_publish_date", "")
        if pd and "/" in pd:
            parts = pd.split("/")
            if len(parts) == 3:
                try:
                    year = int(parts[2])
                except ValueError:
                    pass
        if not year:
            pd2 = r.get("publish_date", "")
            if pd2:
                try:
                    year = int(str(pd2)[:4])
                except ValueError:
                    pass

        if year:
            year_counts[year] += 1
            proj = r.get("kb_associated_project") or r.get("project_name", "")
            if proj:
                year_projects[year].add(proj)

        # Check temporal flag
        cn = r.get("confidence_note", "") or ""
        if "superseded" in cn or "rapidly evolving" in cn:
            flagged += 1
            if year:
                flagged_years[year] += 1

    # Build year bands
    bands = [
        ("2012-2015", range(2012, 2016)),
        ("2016-2018", range(2016, 2019)),
        ("2019-2021", range(2019, 2022)),
        ("2022-2024", range(2022, 2025)),
        ("2025+", range(2025, 2030)),
    ]
    timeline = []
    for label, yrs in bands:
        n_recs = sum(year_counts.get(y, 0) for y in yrs)
        n_projs = len(set().union(*(year_projects.get(y, set()) for y in yrs)))
        n_flagged = sum(flagged_years.get(y, 0) for y in yrs)
        if n_recs > 0:
            timeline.append({
                "period": label,
                "records": n_recs,
                "projects": n_projs,
                "temporal_flags": n_flagged,
            })

    return {
        "timeline": timeline,
        "total_records": len(recs),
        "total_projects": len({r.get("kb_associated_project") or r.get("project_name", "")
                               for r in recs} - {""}),
        "total_flagged": flagged,
        "flagged_pct": round(flagged / len(recs) * 100, 1) if recs else 0,
    }


def build_record_summaries(recs, max_records=200):
    """Extract the fields Sonnet needs for narrative colour, capped for token budget."""
    # Prioritise: recent records first, then severe, then unflagged
    def sort_key(r):
        year = 0
        pd = r.get("publish_date", "")
        if pd:
            try:
                year = int(str(pd)[:4])
            except ValueError:
                pass
        sev_rank = {"critical": 4, "major": 3, "moderate": 2, "minor": 1}.get(
            r.get("issue_severity", ""), 0)
        cn = r.get("confidence_note", "") or ""
        flagged = 1 if ("superseded" in cn or "rapidly evolving" in cn) else 0
        return (-year, -sev_rank, flagged)

    sorted_recs = sorted(recs, key=sort_key)[:max_records]

    summaries = []
    for r in sorted_recs:
        cn = r.get("confidence_note", "") or ""
        temporal_flag = "superseded" in cn or "rapidly evolving" in cn
        s = {
            "what_happened": r.get("what_happened", ""),
            "lesson_learnt": r.get("lesson_learnt", ""),
            "failure_mode": r.get("failure_mode", ""),
            "secondary_fm": r.get("secondary_failure_mode"),
            "severity": r.get("issue_severity", ""),
            "publish_date": r.get("publish_date", ""),
            "dimensions": r.get("dimensions", []),
            "project_name": r.get("project_name", ""),
            "technology_domain": r.get("technology_domain", ""),
        }
        if temporal_flag:
            s["temporal_warning"] = True
        excerpt = r.get("evidence_excerpt", "")
        if excerpt:
            s["evidence_excerpt"] = excerpt[:300]
        summaries.append(s)
    return summaries


def build_prompt(category, matrix, fm_severity, coverage, record_summaries):
    """Build the full prompt for Sonnet."""

    # Format matrix as markdown table
    matrix_md = "| Dimension | " + " | ".join(fm.split(" & ")[0].title() if "&" in fm else fm.title() for fm in FM_ORDER) + " | Total |\n"
    matrix_md += "|---|" + "---|" * len(FM_ORDER) + "---|\n"
    for row in matrix:
        cells = []
        for fm in FM_ORDER:
            d = row.get(fm, {"pct": 0, "count": 0})
            if d["count"] > 0:
                cells.append(f"{d['pct']:.0f}% ({d['count']})")
            else:
                cells.append("—")
        matrix_md += f"| {row['dimension']} | " + " | ".join(cells) + f" | {row['total_adverse']} |\n"

    # Format FM severity table
    sev_md = "| Failure mode | Occurrence | Severity escalation | Severe | Mild |\n"
    sev_md += "|---|---|---|---|---|\n"
    for fm in fm_severity:
        esc = f"{fm['escalation_pct']:.0f}%" if fm['escalation_pct'] is not None else "—"
        sev_md += f"| {fm['failure_mode']} | {fm['pct_of_adverse']:.0f}% ({fm['count']}) | {esc} | {fm['severe']} | {fm['mild']} |\n"

    # Format coverage timeline
    cov_md = "| Period | Records | Projects | Temporal flags |\n"
    cov_md += "|---|---|---|---|\n"
    for t in coverage["timeline"]:
        cov_md += f"| {t['period']} | {t['records']} | {t['projects']} | {t['temporal_flags']} |\n"

    system_prompt = f"""You are writing a delivery risk profile for ARENA (Australian Renewable Energy Agency) projects in the "{category}" category. This will be used by portfolio managers reviewing new funding applications or monitoring existing projects.

Your audience is an experienced energy sector professional who wants specific, actionable insight — not generic risk management advice. Write with authority but acknowledge uncertainty where the data is thin.

CRITICAL TEMPORAL GUIDANCE:
- Records span 2012–2024. Newer records (2022+) are more representative of current risks.
- Some records carry a temporal_warning flag indicating the insight relates to fast-moving technology and the source is pre-2021. These records may describe conditions (costs, capability, market) that have since changed substantially.
- DO NOT present old findings on cost curves, technology capability, or market conditions as current. Instead, frame them historically: "Early ARENA projects experienced X, though [technology/market] has since matured."
- Findings about governance, coordination, stakeholder management, and design process failures are generally time-stable — these patterns persist regardless of technology generation.
- When the evidence for a claim comes primarily from pre-2018 records, say so explicitly.
- Lead with recent patterns. Use older records for historical context and trend identification.

STRUCTURE:
1. **Executive summary** (3-4 sentences): What a PM should know before their first meeting about a {category} project.
2. **Coverage and data quality**: How much data underlies this profile, its temporal distribution, and any caveats.
3. **Risk landscape by delivery dimension**: For each dimension where there is meaningful data, describe what tends to go wrong and how severe it is. Thread the failure mode data through naturally — don't just list percentages. Identify which dimensions are highest-risk and why.
4. **Failure mode deep-dive**: For the top 3-4 failure modes, provide narrative detail drawing on the individual records. What does this failure mode actually look like in {category} projects? Include specific examples from records where they illustrate a pattern.
5. **Temporal trends**: How has the risk profile shifted over time? Are certain failure modes becoming more or less common? Are newer projects experiencing different patterns than older ones?
6. **Key watchpoints for due diligence**: 5-7 specific things a PM should probe when reviewing a {category} project, grounded in the data.

LENGTH: 1500-2500 words. Be specific and evidence-based. Avoid generic statements that could apply to any technology category.

FORMAT: Markdown with headers. Include a metadata block at the top with category, date generated, record count, project count."""

    user_prompt = f"""# {category} — Delivery Risk Profile Data Package

## Dimension × Failure Mode Matrix
(Each cell shows % of adverse records in that dimension attributed to that failure mode, with count in brackets)

{matrix_md}

## Failure Mode Severity
(Occurrence = % of all adverse records. Severity escalation = major+critical as % of all adverse records with that FM)

{sev_md}

## Data Coverage
- Total records: {coverage['total_records']}
- Total projects: {coverage['total_projects']}
- Temporally flagged records: {coverage['total_flagged']} ({coverage['flagged_pct']}%)

### Timeline
{cov_md}

## Individual Records (most recent first, capped at {len(record_summaries)})

{json.dumps(record_summaries, indent=None, ensure_ascii=False)}

---

Write the delivery risk profile for {category} based on the data above."""

    return system_prompt, user_prompt


def generate_report(category, records, dry_run=False):
    """Generate a report for one ARENA category."""
    cat_recs = filter_by_category(records, category)
    if len(cat_recs) < MIN_RECORDS:
        print(f"  Skipping {category}: only {len(cat_recs)} records (min {MIN_RECORDS})")
        return None

    matrix = build_dim_fm_matrix(cat_recs)
    fm_severity = build_fm_severity(cat_recs)
    coverage = build_coverage_timeline(cat_recs)
    record_summaries = build_record_summaries(cat_recs)

    system_prompt, user_prompt = build_prompt(
        category, matrix, fm_severity, coverage, record_summaries)

    if dry_run:
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"Records: {len(cat_recs)}, Projects: {coverage['total_projects']}")
        print(f"System prompt: {len(system_prompt)} chars")
        print(f"User prompt: {len(user_prompt)} chars")
        print(f"Record summaries: {len(record_summaries)}")
        print(f"\n--- SYSTEM PROMPT (first 500 chars) ---")
        print(system_prompt[:500])
        print(f"\n--- USER PROMPT (first 1000 chars) ---")
        print(user_prompt[:1000])
        return None

    import anthropic
    client = anthropic.Anthropic()

    print(f"  Generating report for {category} ({len(cat_recs)} records, "
          f"{coverage['total_projects']} projects)...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    report_text = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    print(f"  Done: {tokens_out} output tokens ({tokens_in} input)")

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = category.lower().replace(" ", "_").replace("/", "_")
    out_path = OUTPUT_DIR / f"{slug}.md"
    out_path.write_text(report_text, encoding="utf-8")
    print(f"  Written to {out_path}")

    return {
        "category": category,
        "records": len(cat_recs),
        "projects": coverage["total_projects"],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "output_file": str(out_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate delivery risk profiles per ARENA category")
    parser.add_argument("--category", help="Generate for a specific category only")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt, don't call API")
    parser.add_argument("--list", action="store_true", help="List eligible categories and exit")
    parser.add_argument("--min-records", type=int, default=MIN_RECORDS,
                        help=f"Minimum records for a category (default {MIN_RECORDS})")
    args = parser.parse_args()

    records = load_all_records()

    # Find all categories with enough data
    cat_counts = Counter()
    for r in records:
        for c in (r.get("arena_category") or []):
            cat_counts[c] += 1

    eligible = [(cat, n) for cat, n in cat_counts.most_common() if n >= args.min_records]

    if args.list:
        print(f"\nEligible categories (>= {args.min_records} records):\n")
        for cat, n in eligible:
            print(f"  {cat}: {n} records")
        print(f"\n{len(eligible)} categories eligible, "
              f"{len(cat_counts) - len(eligible)} below threshold")
        return

    if args.category:
        if args.category not in cat_counts:
            raise SystemExit(f"Category '{args.category}' not found. "
                             f"Available: {', '.join(sorted(cat_counts.keys()))}")
        eligible = [(args.category, cat_counts[args.category])]

    print(f"\nGenerating reports for {len(eligible)} categories...")
    results = []
    total_cost = 0
    for cat, n in eligible:
        result = generate_report(cat, records, dry_run=args.dry_run)
        if result:
            results.append(result)
            # Rough cost estimate: Sonnet input $3/MTok, output $15/MTok
            cost = result["tokens_in"] / 1e6 * 3 + result["tokens_out"] / 1e6 * 15
            total_cost += cost
            print(f"  Est. cost: ${cost:.3f}")

    if results:
        print(f"\n{'='*60}")
        print(f"Generated {len(results)} reports")
        print(f"Total estimated cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
