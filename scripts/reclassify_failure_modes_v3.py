#!/usr/bin/env python3
"""
Reclassify failure modes from v2 (10 categories) to v3 (8 categories) using
the Anthropic Batch API.

Sends the full insight record to Haiku for context. Haiku returns ONLY the
v3 failure mode classification (primary + secondary) and confidence. The script
stamps these minimal fields back onto the per_doc YAML files — no other fields
are touched.

Usage:
    python scripts/reclassify_failure_modes_v3.py --batch submit
    python scripts/reclassify_failure_modes_v3.py --batch status
    python scripts/reclassify_failure_modes_v3.py --batch collect
    python scripts/reclassify_failure_modes_v3.py --batch collect --dry-run
"""

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "insights" / "per_doc"
OUTPUT_DIR = ROOT / "insights" / "failure_mode_reclassification"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
RECLASS_LOG = OUTPUT_DIR / "reclassification_log.yaml"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300
BATCH_SIZE = 10_000

V3_CATEGORIES = [
    "poor scoping",
    "unvalidated technical assumptions",
    "unvalidated integration",
    "regulatory & approvals",
    "commercial & market",
    "coordination & stakeholders",
    "data & measurement",
    "execution & logistics",
]

# Lookup set for validation (lowercase)
_V3_SET = {c.lower() for c in V3_CATEGORIES}

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA renewable energy projects.

Classify each record into EXACTLY ONE of the 8 failure mode categories below. Classify based
on what was broken (the mechanism), not the consequence (cost overrun, schedule slippage,
underperformance are consequences, not failure modes).

Classify the PRIMARY failure mechanism. If a second DISTINCT mechanism is also present in the
record, classify that as the secondary. The secondary must name a different broken mechanism,
not a consequence of the primary. If only one mechanism is present, set secondary to null.

Respond ONLY with JSON:
{"failure_mode_v3": "<category>", "secondary_failure_mode_v3": "<category or null>", "confidence": 0.85}

---

## 1. Poor scoping

The project committed to objectives, boundaries, scale, requirements, or success criteria
that were inadequate, premature, or internally inconsistent. Critical scope items were not
identified before design was locked.

What belongs: scope items omitted from estimates/designs; site conditions not assessed before
design; operating parameters left undefined during feasibility; success criteria not defined;
project scale chosen without evidence.

What does NOT belong: scope item identified but assumption about its value was wrong →
unvalidated technical assumptions. Regulatory pathway not understood → regulatory & approvals.
Measurement systems absent → data & measurement. Delivery plan inadequate → execution &
logistics.

Boundary with unvalidated technical assumptions: scoping = what the project decided to
attempt. Technical assumptions = what the project believed would be true within that scope.
If the item was never on anyone's radar → poor scoping. If identified but untested value
adopted → unvalidated technical assumptions.

## 2. Unvalidated technical assumptions

The team adopted technical assumptions about technology performance, component behaviour,
design parameters, or empirical inputs that were not validated for the actual deployment
context. Covers both "the technology didn't work here" (performance) and "the numbers were
wrong" (parameters) — same mechanism: reliance on unverified technical beliefs.

What belongs: lab/pilot performance extrapolated without validation; hardware specs
incompatible with operating conditions; technology treated as mature when unproven for this
application; algorithm/control system performance assumed without field testing; component
degradation not validated for local conditions; equipment sized using literature values not
site-specific data; cost parameters from international benchmarks without local validation;
soiling rates, temperature coefficients, degradation curves from different climates;
manufacturer data not validated against site conditions.

What does NOT belong: two systems failed at their interface → unvalidated integration.
Assumption never identified → poor scoping. Business case about commercial viability →
commercial & market. Measurement system inadequate → data & measurement. Work attempted and
done badly → execution & logistics.

Boundary with poor scoping: if item never on anyone's radar → poor scoping. If identified
but untested value adopted → unvalidated technical assumptions.

Boundary with unvalidated integration: single component/technology with wrong assumptions →
technical assumptions. Two separately-functioning components failed at their interface →
integration.

Boundary with data & measurement: team used wrong values from wrong context (method error) →
technical assumptions. Data did not exist because infrastructure absent (availability error) →
data & measurement.

Boundary with execution & logistics: wrong beliefs about what would work → technical
assumptions. Work attempted and done badly → execution & logistics. Test: "Was the problem in
what they believed, or in how they carried it out?"

## 3. Unvalidated integration

Two or more separately-functioning components, systems, standards, or processes were assumed
to work in combination, but the interface, interaction, or compatibility was never validated.

What belongs: hardware from different vendors with incompatible characteristics; proprietary
architectures preventing third-party control; communication protocols/API standards immature
or conflicting; control system interactions not validated before commissioning; SCADA/BMS/
inverter combinations untested; protection settings not coordinated across fleet.

What does NOT belong: single component failed its own spec → unvalidated technical
assumptions. Interface never identified as scope item → poor scoping. Organisational
coordination gaps between parties → coordination & stakeholders.

Boundary with technical assumptions: one system's assumptions wrong → technical assumptions.
Interface between two+ systems not validated → integration.

Boundary with coordination & stakeholders: technical interface spec wrong/absent → integration.
Organisations failed to coordinate → coordination & stakeholders. Classify by whether primary
gap was technical or organisational.

## 4. Regulatory & approvals

The project entered execution without a viable pathway through regulatory, permitting,
standards, or compliance requirements. Complexity, duration, novelty, or sequencing of
statutory processes was not adequately accounted for.

What belongs: overlapping regulatory frameworks not coordinated; grid connection standards
inadequate for novel tech; regulatory processes initiated too late; land tenure complexity
not mapped; compliance underestimated; standards/certification not yet established; policy
changes mid-project invalidating assumptions.

What does NOT belong: commercial counterparty or community blocked progress → coordination &
stakeholders (unless blocking party is statutory authority). Technology couldn't comply →
unvalidated technical assumptions. Team couldn't execute against mapped pathway → execution &
logistics.

Boundary with coordination & stakeholders: classify by blocking entity. Government/regulator/
network operator with statutory powers → regulatory & approvals. Private party/community/
commercial counterparty → coordination & stakeholders.

## 5. Commercial & market

The business case rested on commercial or market conditions — demand, price, offtake, cost
trajectory, revenue model, competitor landscape — that proved wrong, were never validated,
or changed materially during delivery.

What belongs: business case assumptions invalidated by market reality; revenue model dependent
on conditions that didn't materialise; customer demand insufficient; competing technologies
made economics unviable; offtake agreements not secured; input cost changes undermining
viability.

What does NOT belong: technology didn't perform or design parameters wrong → unvalidated
technical assumptions (commercial failure is consequence of technical gap). Regulatory change
made business model unviable → regulatory & approvals. Commercial counterparty couldn't be
engaged → coordination & stakeholders.

Boundary with technical assumptions: if business case failed because technology/parameters
wrong → technical assumptions. If technology performed correctly but market changed →
commercial & market.

## 6. Coordination & stakeholders

Parties who needed to work together — internal governance, inter-party coordination, or
external stakeholder engagement — were not adequately aligned, engaged, or coordinated.

What belongs: internal governance gaps (unclear decision rights, inadequate oversight);
inter-organisational failures (data sharing, access disputes, scope change coordination);
external stakeholders (community engagement too late, landholder negotiations delayed,
customer recruitment insufficient); consortium issues (misaligned incentives, IP disputes).

What does NOT belong: statutory authority blocked progress → regulatory & approvals.
Technical interface specification inadequate → unvalidated integration or poor scoping.

Boundary with regulatory & approvals: statutory authority = regulatory. Private party/
community/commercial counterparty = coordination & stakeholders.

## 7. Data & measurement

The project could not generate, access, or rely on data of sufficient quality, resolution,
coverage, or timeliness. Data infrastructure, collection protocols, or governance frameworks
were inadequate.

What belongs: monitoring infrastructure deployed too late or insufficient granularity;
baseline data inadequate; data governance absent; measurement systems producing corrupted
data; training data contaminated; cost categorisation inconsistent across parties; single
points of failure in data architecture.

What does NOT belong: had good data but used wrong values from wrong context → unvalidated
technical assumptions. Never identified what data was needed → poor scoping. Data problem was
commercial insight → commercial & market.

Boundary with technical assumptions: wrong values from wrong context (method error) →
technical assumptions. Data infrastructure absent (availability error) → data & measurement.

Boundary with poor scoping: never identified data need → poor scoping. Identified need but
measurement system inadequate → data & measurement.

## 8. Execution & logistics

The project had a sound design and understood its requirements, but the plan for physically
delivering the work was inadequate — construction management, supply chain, workforce, site
logistics, quality assurance.

What belongs: construction/assembly quality defects; supply chain delays or single-supplier
dependency; workforce capacity insufficient; site logistics failures; long-lead procurement
not initiated; QA gaps during delivery; team/supply chain lacked capacity to execute.

What does NOT belong: design itself was wrong → unvalidated technical assumptions or poor
scoping. Regulatory process delayed works → regulatory & approvals. Stakeholder blocked
access → coordination & stakeholders.

TIEBREAKER with unvalidated technical assumptions: if work was attempted and done badly →
execution & logistics. If work was designed based on wrong beliefs about what would work →
unvalidated technical assumptions."""


def load_all_records():
    records = []
    for path in sorted(glob.glob(str(INPUT_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                for r in recs:
                    r["_doc_stem"] = Path(path).stem
                records.extend(recs)
    return records


def build_user_prompt(record):
    lines = [f"Record ID: {record.get('record_id', 'unknown')}"]
    lines.append(f"Current failure mode (v2): {record.get('failure_mode', '')}")
    for key, label in [
        ("what_happened", "WHAT HAPPENED"),
        ("lesson_learnt", "LESSON LEARNT"),
        ("evidence_excerpt", "EVIDENCE EXCERPT"),
        ("issue_severity", "SEVERITY"),
        ("project_type", "PROJECT TYPE"),
        ("project_scale_band", "SCALE"),
        ("lifecycle_phase", "LIFECYCLE PHASE"),
        ("proponent_type", "PROPONENT TYPE"),
        ("technology_domain", "TECHNOLOGY"),
        ("outcome_class", "OUTCOME"),
        ("secondary_failure_mode", "SECONDARY FAILURE MODE (v2)"),
        ("delay_category", "DELAY CATEGORY"),
        ("intervention_note", "INTERVENTION"),
        ("confidence_note", "CONFIDENCE NOTE"),
    ]:
        val = record.get(key)
        if val:
            lines.append(f"\n{label}: {val}")
    return "\n".join(lines)


def parse_response(text, record_id):
    """Parse the JSON response from Haiku."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"failure_mode_v3": None, "secondary_failure_mode_v3": None,
                "confidence": None, "_parse_error": text[:200]}


def validate_category(category):
    """Validate and normalise a v3 category name. Returns normalised name or None."""
    if not category or category == "null":
        return None
    normalised = category.strip().lower()
    if normalised in _V3_SET:
        # Return the canonical casing
        for c in V3_CATEGORIES:
            if c.lower() == normalised:
                return c
    return None


# ── Submit ──────────────────────────────────────────────────────────────────

def run_batch_submit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    print("Loading records...")
    records = load_all_records()
    print(f"  {len(records)} records loaded")

    # Filter to adverse records only
    adverse = [r for r in records
               if r.get("failure_mode") and r["failure_mode"] != "no major failure stated"]
    print(f"  {len(adverse)} adverse records (failure_mode != 'no major failure stated')")

    print("Building batch requests...")
    requests = []
    for r in adverse:
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

    print(f"  {len(requests)} requests built")

    # Submit in chunks
    batch_ids = []
    for i in range(0, len(requests), BATCH_SIZE):
        chunk = requests[i: i + BATCH_SIZE]
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Submitted batch {len(batch_ids)}: {batch.id}  ({len(chunk)} requests)")

    state = {"batch_ids": batch_ids, "total_requests": len(requests)}
    with open(BATCH_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"\nBatch IDs saved to {BATCH_STATE}")
    print("Run with --batch status to check progress, --batch collect when done.")


# ── Status ──────────────────────────────────────────────────────────────────

def run_batch_status():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    for batch_id in state["batch_ids"]:
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Batch {batch_id}:")
        print(f"  Status: {batch.processing_status}")
        counts = batch.request_counts
        print(f"  Processing: {counts.processing}  Succeeded: {counts.succeeded}  "
              f"Errored: {counts.errored}  Canceled: {counts.canceled}  Expired: {counts.expired}")


# ── Collect ─────────────────────────────────────────────────────────────────

def run_batch_collect(dry_run=False):
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    # Collect all results grouped by doc_stem
    doc_updates = defaultdict(dict)  # doc_stem -> {record_id -> update_dict}
    n_succeeded = 0
    n_errors = 0
    n_parse_errors = 0
    n_invalid_category = 0
    v3_primary = Counter()
    v3_secondary = Counter()
    v2_to_v3 = Counter()

    for batch_id in state["batch_ids"]:
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Batch {batch_id}: {batch.processing_status}")
        if batch.processing_status != "ended":
            print("  Not ready yet — try again later.")
            continue

        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            parts = custom_id.split("__", 1)
            doc_stem = parts[0] if len(parts) == 2 else "unknown"
            record_id = parts[1] if len(parts) == 2 else custom_id

            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                parsed = parse_response(text, record_id)
                n_succeeded += 1

                if parsed.get("_parse_error"):
                    n_parse_errors += 1
                    continue

                # Validate primary
                primary = validate_category(parsed.get("failure_mode_v3"))
                if primary is None:
                    n_invalid_category += 1
                    continue

                # Validate secondary (null is valid)
                raw_secondary = parsed.get("secondary_failure_mode_v3")
                secondary = None
                if raw_secondary and raw_secondary != "null":
                    secondary = validate_category(raw_secondary)
                    if secondary is None:
                        # Invalid secondary — still stamp primary, just skip secondary
                        pass

                confidence = parsed.get("confidence")
                if isinstance(confidence, (int, float)):
                    confidence = round(float(confidence), 2)
                else:
                    confidence = None

                doc_updates[doc_stem][record_id] = {
                    "failure_mode_v3": primary,
                    "secondary_failure_mode_v3": secondary,
                    "confidence": confidence,
                }
                v3_primary[primary] += 1
                if secondary:
                    v3_secondary[secondary] += 1
            else:
                n_errors += 1

    # Summary before stamping
    total_valid = sum(v3_primary.values())
    print(f"\n{'='*60}")
    print(f"RESULTS: {n_succeeded} succeeded, {n_errors} API errors, "
          f"{n_parse_errors} parse errors, {n_invalid_category} invalid categories")
    print(f"Valid classifications: {total_valid}")
    print(f"\nPrimary failure mode distribution:")
    for cat in V3_CATEGORIES:
        n = v3_primary.get(cat, 0)
        pct = 100 * n / total_valid if total_valid > 0 else 0
        print(f"  {cat:40s} {n:5d}  ({pct:5.1f}%)")
    print(f"\nSecondary failure mode distribution:")
    n_with_secondary = sum(v3_secondary.values())
    print(f"  Records with secondary: {n_with_secondary} ({100*n_with_secondary/total_valid:.1f}%)")
    for cat in V3_CATEGORIES:
        n = v3_secondary.get(cat, 0)
        if n > 0:
            print(f"  {cat:40s} {n:5d}")

    if dry_run:
        print(f"\n--dry-run: no files written.")
        return

    # Stamp onto per_doc YAMLs
    print(f"\nStamping results onto per_doc YAMLs...")
    n_stamped = 0
    n_skipped = 0
    n_files = 0

    for doc_stem, updates in sorted(doc_updates.items()):
        path = INPUT_DIR / f"{doc_stem}.yaml"
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping {len(updates)} records")
            continue

        with open(path, encoding="utf-8") as f:
            records = yaml.safe_load(f)
        if not records:
            continue

        changed = False
        for r in records:
            rid = r.get("record_id")
            if rid not in updates:
                continue

            # Idempotency: skip if already reclassified
            if r.get("failure_mode_v2"):
                n_skipped += 1
                continue

            u = updates[rid]

            # Preserve v2 values
            r["failure_mode_v2"] = r.get("failure_mode")
            r["failure_mode"] = u["failure_mode_v3"]

            # Secondary: preserve original if it existed
            old_secondary = r.get("secondary_failure_mode")
            if old_secondary:
                r["secondary_failure_mode_v2"] = old_secondary
            r["secondary_failure_mode"] = u["secondary_failure_mode_v3"]

            r["failure_mode_confidence"] = u["confidence"]

            # Track migration
            v2_to_v3[f"{r['failure_mode_v2']} -> {u['failure_mode_v3']}"] += 1

            changed = True
            n_stamped += 1

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
            n_files += 1

    print(f"  Stamped {n_stamped} records across {n_files} files")
    if n_skipped:
        print(f"  Skipped {n_skipped} already-reclassified records")

    # Save log
    log = {
        "total_succeeded": n_succeeded,
        "api_errors": n_errors,
        "parse_errors": n_parse_errors,
        "invalid_categories": n_invalid_category,
        "records_stamped": n_stamped,
        "records_skipped": n_skipped,
        "files_updated": n_files,
        "primary_distribution": {cat: v3_primary.get(cat, 0) for cat in V3_CATEGORIES},
        "secondary_count": n_with_secondary,
        "secondary_distribution": {cat: v3_secondary.get(cat, 0) for cat in V3_CATEGORIES
                                   if v3_secondary.get(cat, 0) > 0},
        "v2_to_v3_migration": dict(v2_to_v3.most_common()),
    }
    with open(RECLASS_LOG, "w", encoding="utf-8") as f:
        yaml.dump(log, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"  Log saved to {RECLASS_LOG}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Reclassify failure modes from v2 to v3 taxonomy"
    )
    parser.add_argument("--batch", choices=["submit", "collect", "status"], required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="Collect phase: parse and report but don't write YAMLs")
    args = parser.parse_args()

    if args.batch == "submit":
        run_batch_submit()
    elif args.batch == "collect":
        run_batch_collect(dry_run=args.dry_run)
    elif args.batch == "status":
        run_batch_status()


if __name__ == "__main__":
    main()
