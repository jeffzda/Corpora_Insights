#!/usr/bin/env python3
"""
Validate proposed v3 failure mode taxonomy against a 20% stratified sample
of adverse records.

Classifies ~2,300 records against the 8 proposed v3 failure modes, then
cross-tabulates results against severity, proponent type, arena category,
activity type, and lifecycle phase to assess whether each category produces
distinct analytical signals.

Usage:
    python scripts/validate_failure_modes_v3.py --batch submit
    python scripts/validate_failure_modes_v3.py --batch collect
    python scripts/validate_failure_modes_v3.py --batch status
    python scripts/validate_failure_modes_v3.py --analyse

Output:
    insights/failure_mode_validation/validation_sample.yaml
    insights/failure_mode_validation/validation_results.yaml
    insights/failure_mode_validation/validation_analysis.md
"""

import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
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
INPUT_DIR = ROOT / "insights" / "per_doc"
OUTPUT_DIR = ROOT / "insights" / "failure_mode_validation"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
SAMPLE_FILE = OUTPUT_DIR / "validation_sample.yaml"
RESULTS_FILE = OUTPUT_DIR / "validation_results.yaml"
ANALYSIS_FILE = OUTPUT_DIR / "validation_analysis.md"
DEFINITIONS_FILE = ROOT / "pilot_100_reports" / "taxonomy" / "FAILURE_MODE_DEFINITIONS_V3.md"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 200
BATCH_SIZE = 10_000
SAMPLE_SEED = 2026
SAMPLE_FRACTION = 0.20
SAMPLE_FLOOR = 100

V3_CATEGORIES = [
    "poor scoping",
    "technical assumptions",
    "regulatory & approvals",
    "commercial & market",
    "capability shortfall",
    "coordination & stakeholders",
    "data & measurement",
    "execution & logistics",
]

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects against a failure mode taxonomy.

For each record, you must:
1. Classify the record into EXACTLY ONE of the 8 failure mode categories defined below.
2. Provide a confidence score (0.0 to 1.0) for your classification.
3. Provide a free-form root-cause tag (5-10 words) describing what specifically went wrong, in concrete language (not taxonomy labels).

## WHAT IS A FAILURE MODE?

A failure mode names the specific mechanism by which a project's capacity to deliver its intended outcome was degraded. It names what broke or was absent — not what happened as a result (consequence) and not why it was broken in some deeper organisational sense (root cause).

- Consequence (NOT a failure mode): cost overrun, schedule slippage, underperformance against spec. Test: "Could two projects exhibit this same outcome through completely different mechanisms?" If yes, it's a consequence.
- Symptom (NOT a failure mode): contractor disputes, repeated design changes, missed milestones. These signal something is wrong but don't identify the mechanism.
- Root cause (too deep): "Minister wanted announcement before design was ready." The failure mode is "premature commitment to scope before technical feasibility was established."

## CODING RULE

Classify based on WHAT WAS BROKEN, not WHY it was broken. If technical assumptions were wrong because the team lacked expertise to recognise the flaw, that's still "technical assumptions" — the broken mechanism is the unvalidated assumption. "Capability shortfall" is reserved for cases where the team knew what to do but couldn't do it.

## THE 8 FAILURE MODE CATEGORIES

### 1. Poor scoping

The project committed to a definition of what it would deliver — objectives, boundaries, scale, requirements, constraints, success criteria — that was inadequate, premature, or internally inconsistent. Critical scope items were not identified before design was locked.

What belongs here:
- Scope items omitted from estimates or designs (civil works, balance-of-plant, decommissioning)
- Site conditions not assessed before design (subsurface, structural, environmental)
- Operating parameters left undefined during feasibility
- Project scale chosen without evidence

What does NOT belong here:
- A scope item was identified but the assumption about its value was wrong → Technical assumptions
- The scope was correct but the regulatory pathway wasn't understood → Regulatory & approvals
- The scope was correct but measurement systems to verify it were absent → Data & measurement

Boundary with Technical assumptions: Scoping is about WHAT the project decided to attempt. Technical assumptions is about WHAT THE PROJECT BELIEVED WOULD BE TRUE about performance within that scope. If the item was never on anyone's radar, it's poor scoping. If the item was identified but the team adopted an untested value, it's technical assumptions.

### 2. Technical assumptions

A critical technical design choice, parameter value, or performance expectation was adopted without adequate empirical validation for the specific project conditions — including cases where the technology itself was insufficiently mature for the deployment context.

What belongs here:
- Equipment sized using literature values instead of site-specific data
- Performance assumptions based on international studies not validated locally
- Hardware specifications incompatible with actual operating conditions
- Technology treated as mature when specific variants/applications remained unproven
- Technology deployed before cost curves, supply chains, or standards were ready
- Lab or pilot performance extrapolated to field scale without validation

What does NOT belong here:
- The parameter was never identified as something to validate → Poor scoping
- The business case assumption (demand, price, offtake) was wrong → Commercial & market
- The measurement system to verify performance was inadequate → Data & measurement

Boundary with Data & measurement: If the flawed belief was about the technology's performance characteristics, it's technical assumptions. If the flaw was in the project's ability to observe, measure, or demonstrate outcomes (instrumentation, baselines, methodology), it's data & measurement.

### 3. Regulatory & approvals

The project entered execution without a viable, well-understood pathway through the relevant regulatory, permitting, standards, or compliance landscape. The complexity, duration, novelty, or sequencing of statutory processes was not adequately accounted for.

What belongs here:
- Multiple overlapping regulatory frameworks not coordinated
- Grid connection standards inadequate for novel technology
- Regulatory processes initiated too late
- Land tenure complexity not mapped upfront
- Standards or certification pathways not yet established
- Policy or rule changes mid-project

What does NOT belong here:
- A commercial counterparty or community group blocked progress → Coordination & stakeholders (unless the blocking party is a statutory authority)
- The regulatory environment was understood but the technology couldn't comply → Technical assumptions

Boundary with Coordination & stakeholders: Classify by the blocking entity. Statutory authority = regulatory & approvals. Private party, community, or commercial counterparty = coordination & stakeholders.

### 4. Commercial & market

The project's business case rested on commercial or market conditions — demand, price, offtake, cost trajectory, revenue model, competitor landscape — that proved wrong, were never adequately validated, or changed materially during delivery.

What belongs here:
- Business case assumptions invalidated by market reality
- Customer demand insufficient or behaviour different from assumptions
- Competing technologies made economics unviable
- Offtake agreements or commercial arrangements not secured
- Input cost changes undermining viability

What does NOT belong here:
- A technology didn't perform to spec the business case assumed → Technical assumptions (the commercial failure is the consequence)
- A regulatory change made the business model unviable → Regulatory & approvals

Boundary with Technical assumptions: If the business case failed because a technology parameter was wrong, classify by what was broken. If the parameter was an unvalidated technical assumption, it's technical assumptions. If the technology performed as expected but market conditions changed, it's commercial & market.

### 5. Capability shortfall

The project required skills, experience, organisational capacity, or specialist resources that the delivery team or supply chain did not possess. The team knew what needed to be done but couldn't do it, or didn't have the right people.

What belongs here:
- Team lacked specialist technical knowledge
- Organisation had no experience with this type/scale of project
- Key personnel departed and couldn't be replaced
- Supply chain partner lacked expertise
- Talent scarcity in the relevant domain

What does NOT belong here:
- The team had the skills but made wrong technical assumptions → Technical assumptions
- The team had the skills but couldn't coordinate → Coordination & stakeholders
- The team had the skills but the delivery plan was inadequate → Execution & logistics

### 6. Coordination & stakeholders

Parties who needed to work together — within the project (internal governance), between project organisations (inter-party coordination), or with external communities and counterparties (stakeholder engagement) — were not adequately aligned, engaged, or coordinated.

What belongs here:
- Internal governance: unclear decision rights, inadequate oversight, accountability gaps
- Inter-organisational: data sharing failures, scope change coordination, technology handoffs
- External stakeholders: community engagement too late, landholder negotiations delayed, customer recruitment insufficient
- Consortium-specific: partner incentive misalignment, IP disputes

What does NOT belong here:
- A statutory authority or regulator blocked progress → Regulatory & approvals
- The team lacked skills to coordinate → Capability shortfall
- The coordination failure was about inadequate technical interface specification → Technical assumptions or Poor scoping

### 7. Data & measurement

The project could not generate, access, or rely on data of sufficient quality, resolution, coverage, or timeliness to support design decisions, performance verification, or operational control.

What belongs here:
- Monitoring infrastructure deployed too late or at insufficient granularity
- Baseline data inadequate for design or verification
- Data governance absent
- Measurement systems producing corrupted or unreliable data
- Training data contaminated by unfiltered exogenous variables
- Single points of failure in data architecture

What does NOT belong here:
- The project had good data but made wrong technical assumptions from it → Technical assumptions
- The project never identified what data was needed → Poor scoping

Boundary with Poor scoping: If the project never identified that certain data would be needed, that's poor scoping. If the project identified the data need but the measurement system was inadequate, that's data & measurement.

### 8. Execution & logistics

The project had a sound design and understood its requirements, but the plan for physically delivering the work — construction management, supply chain procurement, workforce deployment, site logistics, quality assurance — was inadequate for the realities of implementation.

What belongs here:
- Construction or assembly quality defects
- Supply chain delays, supplier insolvency, single-supplier dependency
- Workforce capacity insufficient for delivery schedule
- Site logistics failures (road access, camp capacity, equipment transport)
- Long-lead procurement not initiated early enough
- Quality assurance gaps during physical delivery

What does NOT belong here:
- The design itself was wrong → Technical assumptions or Poor scoping
- The team lacked skills to manage delivery → Capability shortfall
- A regulatory process delayed physical works → Regulatory & approvals
- A stakeholder blocked site access → Coordination & stakeholders

Boundary with Capability shortfall: Capability shortfall = the team didn't have the skills. Execution & logistics = the delivery plan was inadequate even if the team was competent.

## OUTPUT FORMAT

Respond ONLY with a JSON object (no markdown, no explanation):
{"failure_mode_v3": "<category name>", "confidence": 0.85, "root_cause_tag": "<5-10 words>"}

The failure_mode_v3 value MUST be one of: "poor scoping", "technical assumptions", "regulatory & approvals", "commercial & market", "capability shortfall", "coordination & stakeholders", "data & measurement", "execution & logistics"."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_all_records():
    """Load all records from per_doc YAMLs."""
    records = []
    for path in sorted(INPUT_DIR.glob("doc_*.yaml")):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                for r in recs:
                    r["_doc_stem"] = path.stem
                records.extend(recs)
    return records


def build_sample(records):
    """Stratified sample: 20% per v2 failure mode, floor of 100."""
    adverse = [r for r in records
               if r.get("failure_mode")
               and r["failure_mode"] != "no major failure stated"]

    by_mode = defaultdict(list)
    for r in adverse:
        by_mode[r["failure_mode"]].append(r)

    rng = random.Random(SAMPLE_SEED)
    sample = []
    for mode, recs in sorted(by_mode.items()):
        n = max(SAMPLE_FLOOR, int(len(recs) * SAMPLE_FRACTION))
        n = min(n, len(recs))
        chosen = rng.sample(recs, n)
        for r in chosen:
            r["_sample_stratum"] = mode
        sample.extend(chosen)
        print(f"  {mode:40s}  {len(recs):5d} total → {n:4d} sampled")

    print(f"\n  Total sampled: {len(sample)}")
    return sample


def build_user_prompt(record):
    wh = record.get("what_happened") or ""
    ll = record.get("lesson_learnt") or ""
    ee = record.get("evidence_excerpt") or ""
    fm = record.get("failure_mode") or ""
    rid = record.get("record_id", "unknown")
    return f"""Record ID: {rid}
Original failure mode (v2): {fm}

WHAT HAPPENED:
{wh}

LESSON LEARNT:
{ll}

EVIDENCE EXCERPT:
{ee}"""


def parse_response(text, record_id):
    """Parse JSON response from Haiku."""
    text = text.strip()
    result = {"record_id": record_id, "failure_mode_v3": None,
              "confidence": None, "root_cause_tag": None}
    try:
        parsed = json.loads(text)
        result["failure_mode_v3"] = parsed.get("failure_mode_v3")
        result["confidence"] = parsed.get("confidence")
        result["root_cause_tag"] = parsed.get("root_cause_tag")
        return result
    except json.JSONDecodeError:
        pass
    # Fallback: find JSON in text
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group())
            result["failure_mode_v3"] = parsed.get("failure_mode_v3")
            result["confidence"] = parsed.get("confidence")
            result["root_cause_tag"] = parsed.get("root_cause_tag")
            return result
        except json.JSONDecodeError:
            pass
    result["failure_mode_v3"] = f"parse_error"
    result["root_cause_tag"] = f"parse_error: {text[:100]}"
    return result


# ── Batch submit ─────────────────────────────────────────────────────────────

def run_batch_submit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    print("Loading records...")
    records = load_all_records()
    print(f"  {len(records)} records loaded\n")

    print("Building stratified sample...")
    sample = build_sample(records)

    # Save sample for reproducibility (slim version)
    sample_slim = []
    for r in sample:
        sample_slim.append({
            "record_id": r.get("record_id"),
            "failure_mode": r.get("failure_mode"),
            "what_happened": r.get("what_happened"),
            "lesson_learnt": r.get("lesson_learnt"),
            "evidence_excerpt": r.get("evidence_excerpt"),
            "issue_severity": r.get("issue_severity"),
            "arena_category": r.get("arena_category"),
            "activity_type": r.get("activity_type"),
            "proponent_type": r.get("proponent_type"),
            "lifecycle_phase": r.get("lifecycle_phase"),
            "_doc_stem": r.get("_doc_stem"),
            "_sample_stratum": r.get("_sample_stratum"),
        })
    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        yaml.dump(sample_slim, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False)
    print(f"\n  Sample saved to {SAMPLE_FILE}")

    print("\nBuilding batch requests...")
    requests = []
    for r in sample:
        record_id = r.get("record_id", "unknown")
        doc_stem = r.get("_doc_stem", "unknown")
        custom_id = f"{doc_stem}__{record_id}"
        if len(custom_id) > 64:
            custom_id = custom_id[:64]

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": build_user_prompt(r)}],
            },
        })

    # Submit (single batch, well under 10k)
    batch = client.messages.batches.create(requests=requests)
    print(f"  Submitted batch: {batch.id}  ({len(requests)} requests)")

    state = {"batch_id": batch.id, "total_requests": len(requests)}
    with open(BATCH_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"  State saved to {BATCH_STATE}")
    print("  Run with --batch collect when processing is complete.")


# ── Batch status ─────────────────────────────────────────────────────────────

def run_batch_status():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state at {BATCH_STATE}")
    client = anthropic.Anthropic()
    with open(BATCH_STATE) as f:
        state = json.load(f)
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch {state['batch_id']}: {batch.processing_status}")
    print(f"  Total requests: {state['total_requests']}")
    if hasattr(batch, 'request_counts'):
        rc = batch.request_counts
        print(f"  Succeeded: {rc.succeeded}  Errored: {rc.errored}  "
              f"Expired: {rc.expired}  Canceled: {rc.canceled}")


# ── Batch collect ────────────────────────────────────────────────────────────

def run_batch_collect():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state at {BATCH_STATE}. Run --batch submit first.")
    if not SAMPLE_FILE.exists():
        raise SystemExit(f"No sample at {SAMPLE_FILE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE) as f:
        state = json.load(f)

    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch {state['batch_id']}: {batch.processing_status}")
    if batch.processing_status != "ended":
        print("  Not ready yet — try again later.")
        return

    # Load sample for joining metadata
    with open(SAMPLE_FILE, encoding="utf-8") as f:
        sample = yaml.safe_load(f) or []
    sample_by_id = {r["record_id"]: r for r in sample}

    results = []
    errors = 0
    v3_counts = Counter()

    for result in client.messages.batches.results(state["batch_id"]):
        custom_id = result.custom_id
        # Extract record_id from custom_id
        if "__" in custom_id:
            _, record_id_raw = custom_id.split("__", 1)
        else:
            record_id_raw = custom_id
        # No need to transform — custom_id preserves original chars since we
        # didn't replace dashes in this script

        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            tag = parse_response(text, record_id_raw)
        else:
            tag = {"record_id": record_id_raw, "failure_mode_v3": "api_error",
                   "confidence": 0, "root_cause_tag": str(result.result)[:200]}
            errors += 1

        # Find original record — try exact match first, then fuzzy
        orig = sample_by_id.get(record_id_raw, {})
        if not orig:
            # Try matching without dashes
            for sid, sr in sample_by_id.items():
                if sid.replace("-", "") == record_id_raw.replace("-", ""):
                    orig = sr
                    break

        v3 = tag.get("failure_mode_v3", "unknown")
        v3_counts[v3] += 1

        results.append({
            "record_id": record_id_raw,
            "failure_mode_v2": orig.get("failure_mode"),
            "failure_mode_v3": v3,
            "confidence": tag.get("confidence"),
            "root_cause_tag": tag.get("root_cause_tag"),
            "issue_severity": orig.get("issue_severity"),
            "arena_category": orig.get("arena_category"),
            "activity_type": orig.get("activity_type"),
            "proponent_type": orig.get("proponent_type"),
            "lifecycle_phase": orig.get("lifecycle_phase"),
        })

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(results, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False)

    print(f"\n{len(results)} records collected  ({errors} errors)")
    print(f"\nv3 category distribution:")
    for cat in V3_CATEGORIES:
        print(f"  {cat:30s}  {v3_counts.get(cat, 0):4d}")
    other = sum(c for k, c in v3_counts.items() if k not in V3_CATEGORIES)
    if other:
        print(f"  {'(other/errors)':30s}  {other:4d}")
    print(f"\nResults written to {RESULTS_FILE}")
    print("Run with --analyse to generate cross-tabulations.")


# ── Analysis ─────────────────────────────────────────────────────────────────

def run_analyse():
    if not RESULTS_FILE.exists():
        raise SystemExit(f"No results at {RESULTS_FILE}. Run --batch collect first.")

    with open(RESULTS_FILE, encoding="utf-8") as f:
        results = yaml.safe_load(f) or []

    # Filter to valid v3 classifications
    valid = [r for r in results if r.get("failure_mode_v3") in V3_CATEGORIES]
    total = len(valid)
    print(f"Analysing {total} validly classified records "
          f"({len(results) - total} parse errors/other excluded)\n")

    lines = []
    lines.append("# Failure Mode v3 Validation Analysis\n")
    lines.append(f"Based on {total} records from a stratified 20% sample of "
                 f"{len(results)} adverse records.\n")
    lines.append("---\n")

    # ── 3a. Prevalence ────────────────────────────────────────────────────
    lines.append("## 1. Prevalence Summary\n")
    lines.append("| # | Category | Count | % | Avg Confidence | Low Conf (<0.70) |")
    lines.append("|---|---|---|---|---|---|")

    for i, cat in enumerate(V3_CATEGORIES, 1):
        recs = [r for r in valid if r["failure_mode_v3"] == cat]
        n = len(recs)
        pct = 100 * n / total if total else 0
        confs = [r["confidence"] for r in recs if r.get("confidence") is not None]
        avg_conf = sum(confs) / len(confs) if confs else 0
        low_conf = sum(1 for c in confs if c < 0.70)
        flag = " **⚠ <5%**" if pct < 5 else ""
        lines.append(f"| {i} | {cat} | {n} | {pct:.1f}%{flag} | "
                     f"{avg_conf:.2f} | {low_conf} |")

    lines.append("")

    # ── 3b. Severity ratio ───────────────────────────────────────────────
    lines.append("## 2. Severity Ratio by v3 Category\n")
    lines.append("Severity escalation ratio = (major + critical) / (minor + moderate). "
                 "Corpus baseline: 0.27.\n")
    lines.append("| Category | None | Minor | Moderate | Major | Critical | "
                 "Ratio | vs Baseline |")
    lines.append("|---|---|---|---|---|---|---|---|")

    severity_ratios = {}
    for cat in V3_CATEGORIES:
        recs = [r for r in valid if r["failure_mode_v3"] == cat]
        sev = Counter(r.get("issue_severity", "unknown") for r in recs)
        num = sev.get("major", 0) + sev.get("critical", 0)
        den = sev.get("minor", 0) + sev.get("moderate", 0)
        ratio = num / den if den > 0 else float('inf')
        severity_ratios[cat] = ratio
        delta = ratio - 0.27
        sign = "+" if delta >= 0 else ""
        lines.append(f"| {cat} | {sev.get('none',0)} | {sev.get('minor',0)} | "
                     f"{sev.get('moderate',0)} | {sev.get('major',0)} | "
                     f"{sev.get('critical',0)} | {ratio:.2f} | {sign}{delta:.2f} |")

    lines.append("")

    # Check for merge candidates (within 0.05)
    cats = list(severity_ratios.keys())
    merge_flags = []
    for i in range(len(cats)):
        for j in range(i + 1, len(cats)):
            diff = abs(severity_ratios[cats[i]] - severity_ratios[cats[j]])
            if diff < 0.05:
                merge_flags.append((cats[i], cats[j], diff))
    if merge_flags:
        lines.append("**Merge candidates (severity ratio within 0.05):**\n")
        for a, b, d in merge_flags:
            lines.append(f"- {a} ({severity_ratios[a]:.2f}) ≈ {b} "
                         f"({severity_ratios[b]:.2f}), diff={d:.3f}")
        lines.append("")

    # ── 3c. Cross-tab profiles ───────────────────────────────────────────
    lines.append("## 3. Cross-Tab Profiles\n")

    dimensions = [
        ("activity_type", "Activity Type"),
        ("proponent_type", "Proponent Type (top 5)"),
        ("lifecycle_phase", "Lifecycle Phase"),
    ]

    # Arena category is a list field — handle separately
    lines.append("### Arena Category (top 5 per v3 category)\n")
    lines.append("| v3 Category | #1 | #2 | #3 | #4 | #5 |")
    lines.append("|---|---|---|---|---|---|")

    for cat in V3_CATEGORIES:
        recs = [r for r in valid if r["failure_mode_v3"] == cat]
        ac_counts = Counter()
        for r in recs:
            ac = r.get("arena_category")
            if isinstance(ac, list):
                for a in ac:
                    ac_counts[a] += 1
            elif ac:
                ac_counts[ac] += 1
        top5 = ac_counts.most_common(5)
        cells = [f"{name} ({cnt})" for name, cnt in top5]
        while len(cells) < 5:
            cells.append("—")
        lines.append(f"| {cat} | {' | '.join(cells)} |")

    lines.append("")

    for dim_key, dim_name in dimensions:
        lines.append(f"### {dim_name}\n")
        # Collect all values
        all_vals = sorted(set(r.get(dim_key, "unknown") for r in valid
                              if r.get(dim_key)))

        # Build table
        header = "| v3 Category | " + " | ".join(all_vals[:10]) + " |"
        sep = "|---" * (min(len(all_vals), 10) + 1) + "|"
        lines.append(header)
        lines.append(sep)

        for cat in V3_CATEGORIES:
            recs = [r for r in valid if r["failure_mode_v3"] == cat]
            n = len(recs) or 1
            counts = Counter(r.get(dim_key, "unknown") for r in recs)
            cells = [f"{counts.get(v, 0)} ({100*counts.get(v,0)/n:.0f}%)"
                     for v in all_vals[:10]]
            lines.append(f"| {cat} | {' | '.join(cells)} |")

        lines.append("")

    # ── JSD computation ──────────────────────────────────────────────────
    lines.append("### Jensen-Shannon Divergence (category pairs)\n")
    lines.append("Pairs with JSD < 0.05 across ALL dimensions are merge candidates.\n")

    def jsd(p, q):
        """Jensen-Shannon divergence between two distributions."""
        # Ensure same support
        all_keys = set(p.keys()) | set(q.keys())
        eps = 1e-10
        p_vals = [p.get(k, 0) + eps for k in all_keys]
        q_vals = [q.get(k, 0) + eps for k in all_keys]
        p_sum = sum(p_vals)
        q_sum = sum(q_vals)
        p_norm = [x / p_sum for x in p_vals]
        q_norm = [x / q_sum for x in q_vals]
        m = [(a + b) / 2 for a, b in zip(p_norm, q_norm)]
        def kl(a, b):
            return sum(ai * math.log(ai / bi) for ai, bi in zip(a, b))
        return (kl(p_norm, m) + kl(q_norm, m)) / 2

    # Compute distributions per category per dimension
    jsd_dims = ["activity_type", "proponent_type", "lifecycle_phase"]
    cat_dists = {}
    for cat in V3_CATEGORIES:
        recs = [r for r in valid if r["failure_mode_v3"] == cat]
        cat_dists[cat] = {}
        for dim in jsd_dims:
            cat_dists[cat][dim] = Counter(r.get(dim, "unknown") for r in recs)

    jsd_flags = []
    lines.append("| Cat A | Cat B | JSD activity | JSD proponent | JSD lifecycle | All <0.05? |")
    lines.append("|---|---|---|---|---|---|")
    for i in range(len(V3_CATEGORIES)):
        for j in range(i + 1, len(V3_CATEGORIES)):
            a, b = V3_CATEGORIES[i], V3_CATEGORIES[j]
            jsds = {}
            for dim in jsd_dims:
                jsds[dim] = jsd(cat_dists[a][dim], cat_dists[b][dim])
            all_low = all(v < 0.05 for v in jsds.values())
            flag = "**YES**" if all_low else "no"
            lines.append(f"| {a} | {b} | {jsds['activity_type']:.3f} | "
                         f"{jsds['proponent_type']:.3f} | {jsds['lifecycle_phase']:.3f} | "
                         f"{flag} |")
            if all_low:
                jsd_flags.append((a, b))

    lines.append("")
    if jsd_flags:
        lines.append("**⚠ Merge candidates (all JSDs < 0.05):**\n")
        for a, b in jsd_flags:
            lines.append(f"- {a} + {b}")
        lines.append("")

    # ── 3d. Confusion matrix ─────────────────────────────────────────────
    lines.append("## 4. Confusion Matrix (v2 → v3)\n")

    v2_modes = sorted(set(r.get("failure_mode_v2", "unknown") for r in valid))
    header = "| v2 \\ v3 | " + " | ".join(V3_CATEGORIES) + " | Total |"
    sep = "|---" * (len(V3_CATEGORIES) + 2) + "|"
    lines.append(header)
    lines.append(sep)

    for v2 in v2_modes:
        recs = [r for r in valid if r.get("failure_mode_v2") == v2]
        n = len(recs) or 1
        counts = Counter(r["failure_mode_v3"] for r in recs)
        cells = []
        for v3 in V3_CATEGORIES:
            cnt = counts.get(v3, 0)
            pct = 100 * cnt / n
            # Bold the dominant mapping
            if pct >= 40:
                cells.append(f"**{cnt} ({pct:.0f}%)**")
            else:
                cells.append(f"{cnt} ({pct:.0f}%)" if cnt else "—")
        lines.append(f"| {v2} | {' | '.join(cells)} | {len(recs)} |")

    lines.append("")

    # ── 3e. Boundary cases ───────────────────────────────────────────────
    lines.append("## 5. Boundary Cases (confidence < 0.70)\n")

    low_conf = [r for r in valid
                if r.get("confidence") is not None and r["confidence"] < 0.70]
    low_conf.sort(key=lambda r: r.get("confidence", 0))

    lines.append(f"{len(low_conf)} records with confidence < 0.70 "
                 f"({100*len(low_conf)/total:.1f}% of sample)\n")

    if low_conf:
        lines.append("| Record ID | v2 | v3 | Conf | Root Cause Tag | What Happened (100 chars) |")
        lines.append("|---|---|---|---|---|---|")
        for r in low_conf[:50]:  # Cap at 50
            wh = (r.get("what_happened") or "")[:100].replace("|", "/")
            rc = (r.get("root_cause_tag") or "")[:60].replace("|", "/")
            v2 = (r.get("failure_mode_v2") or "?")[:25]
            v3 = (r.get("failure_mode_v3") or "?")[:25]
            lines.append(f"| {r['record_id']} | {v2} | {v3} | "
                         f"{r.get('confidence', 0):.2f} | {rc} | {wh} |")
        if len(low_conf) > 50:
            lines.append(f"\n*({len(low_conf) - 50} more records not shown)*\n")

    lines.append("")

    # Boundary pair analysis
    lines.append("### Boundary pair frequency (low-confidence records)\n")
    pair_counts = Counter()
    for r in low_conf:
        pair = (r.get("failure_mode_v2", "?"), r.get("failure_mode_v3", "?"))
        pair_counts[pair] += 1
    if pair_counts:
        lines.append("| v2 → v3 | Count |")
        lines.append("|---|---|")
        for (v2, v3), cnt in pair_counts.most_common(15):
            lines.append(f"| {v2} → {v3} | {cnt} |")
    lines.append("")

    # ── 3f. Root-cause tag analysis ──────────────────────────────────────
    lines.append("## 6. Root-Cause Tag Analysis\n")

    for cat in V3_CATEGORIES:
        recs = [r for r in valid if r["failure_mode_v3"] == cat]
        tags = [r.get("root_cause_tag", "").lower().strip().rstrip(".")
                for r in recs if r.get("root_cause_tag")]
        tag_counts = Counter(tags)
        lines.append(f"### {cat} (n={len(recs)})\n")
        lines.append("Top 10 root-cause tags:\n")
        for tag, cnt in tag_counts.most_common(10):
            lines.append(f"- {tag} ({cnt})")
        lines.append("")

    # Cross-category tags
    lines.append("### Root-cause tags appearing in 3+ categories\n")
    tag_to_cats = defaultdict(set)
    for r in valid:
        tag = (r.get("root_cause_tag") or "").lower().strip().rstrip(".")
        if tag and "parse_error" not in tag:
            tag_to_cats[tag].add(r["failure_mode_v3"])
    cross_tags = [(tag, cats) for tag, cats in tag_to_cats.items()
                  if len(cats) >= 3]
    cross_tags.sort(key=lambda x: -len(x[1]))
    if cross_tags:
        lines.append("| Root Cause Tag | Categories |")
        lines.append("|---|---|")
        for tag, cats in cross_tags[:20]:
            lines.append(f"| {tag} | {', '.join(sorted(cats))} |")
    else:
        lines.append("*No root-cause tags appear across 3+ categories.*")
    lines.append("")

    # ── Write output ─────────────────────────────────────────────────────
    output = "\n".join(lines)
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(output)
    print(f"\n\nAnalysis written to {ANALYSIS_FILE}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate v3 failure mode taxonomy against stratified sample")
    parser.add_argument("--batch", choices=["submit", "collect", "status"],
                        help="Batch API: submit, collect, or status")
    parser.add_argument("--analyse", action="store_true",
                        help="Run cross-tabulation analysis on collected results")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch == "submit":
        run_batch_submit()
    elif args.batch == "collect":
        run_batch_collect()
    elif args.batch == "status":
        run_batch_status()
    elif args.analyse:
        run_analyse()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
