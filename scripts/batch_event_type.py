#!/usr/bin/env python3
"""
Classify event_type and consequence_level for all delivery insight records.

event_type (all records):
  - realised_delivery_event: the project experienced a concrete adverse outcome
  - design_technical_finding: analysis/testing revealed a limitation or constraint
  - identified_future_risk: a study flagged something that has NOT materialised
  - contextual_observation: describes market/policy/industry context, not a project event

consequence_level (only for realised_delivery_event):
  - adaptation_required: project adjusted but no quantifiable damage
  - material_impact: quantifiable cost, schedule, or performance impact
  - project_threatening: project viability was in question
  - project_terminated: project discontinued or abandoned

Uses Haiku batch API for cost efficiency.

Usage:
    python scripts/batch_event_type.py --batch submit
    python scripts/batch_event_type.py --batch status
    python scripts/batch_event_type.py --batch collect
    python scripts/batch_event_type.py --dry-run          # print prompt for first 5 records
    python scripts/batch_event_type.py --stats             # show distribution from collected results
"""

import argparse
import glob
import json
import re
from collections import Counter
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_event_type"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 200

EVENT_TYPES = [
    "realised_delivery_event",
    "design_technical_finding",
    "identified_future_risk",
    "contextual_observation",
]
CONSEQUENCE_LEVELS = [
    "adaptation_required",
    "material_impact",
    "project_threatening",
    "project_terminated",
]

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

Each record describes something that happened (or was observed) during an energy project. Your job is to classify TWO things:

## 1. EVENT TYPE — what kind of record is this?

Choose exactly one:

**realised_delivery_event**: The project experienced a concrete adverse outcome — a delay, cost increase, performance shortfall, equipment failure, scope change, or cancellation. The cause can be internal OR external (weather, pandemic, regulatory change, market shift) — what matters is that the project SUFFERED A MEASURABLE CONSEQUENCE. If a risk was identified AND it materialised during the project, this is a realised delivery event, not an identified future risk.

**design_technical_finding**: Analysis, testing, simulation, or modelling revealed a technical limitation, constraint, or unexpected behaviour. Nothing went wrong operationally — the finding IS the output of the work, not a failure of the work. Examples: lab experiments showing material degradation, modelling revealing a design constraint, testing showing equipment behaviour differs from assumptions.

**identified_future_risk**: A study or assessment flagged something that COULD happen but HAS NOT MATERIALISED. Risk register entries, "there is a risk that...", scenario modelling of potential outcomes. CRITICAL: if the risk actually materialised during the project (the project experienced the consequence), classify as realised_delivery_event instead.

**contextual_observation**: The project is COMMENTING ON market conditions, policy gaps, industry structure, cost curves, or other external context — not suffering from them. The record describes the environment, not a project event. Examples: "no market mechanism exists for X", "grid emissions intensity in state Y is Z", "the cost of technology X has declined".

## 2. CONSEQUENCE LEVEL — how bad was it? (only for realised_delivery_event)

If event_type is realised_delivery_event, also classify the consequence:

**adaptation_required**: The project adjusted scope, design, timeline, or approach, but there is no evidence of quantifiable damage. The team adapted and moved on.

**material_impact**: There is evidence of quantifiable cost, schedule, or performance impact — dollar amounts, specific delay durations, measurable performance shortfalls, liquidated damages, budget overruns.

**project_threatening**: The project's viability was in question — references to potential cancellation, fundamental commercial unviability, existential technical challenges, inability to secure financing or offtake.

**project_terminated**: The project was discontinued, abandoned, or not progressed. The record explicitly states the project did not proceed.

If event_type is NOT realised_delivery_event, set consequence_level to null.

## KEY DECISION RULES

- If the project experienced a CONSEQUENCE (cost, delay, performance loss, scope change), it is realised_delivery_event regardless of whether the cause was external.
- "The project found that X is not commercially viable" from a feasibility study that was DESIGNED to answer that question = design_technical_finding (the finding is the deliverable).
- "The project was discontinued because X was not commercially viable" = realised_delivery_event with consequence project_terminated.
- "There is a risk that X could happen" where X did NOT happen = identified_future_risk.
- "X happened, causing Y delay/cost" = realised_delivery_event.
- Generic industry commentary with no project-specific consequence = contextual_observation.

Respond ONLY with a JSON object (no markdown, no explanation):
{"event_type": "realised_delivery_event", "consequence_level": "material_impact", "confidence": 0.9}

For non-delivery events:
{"event_type": "contextual_observation", "consequence_level": null, "confidence": 0.85}"""


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
    wh = record.get("what_happened") or ""
    ll = record.get("lesson_learnt") or ""
    ee = record.get("evidence_excerpt") or ""
    oc = record.get("outcome_class") or ""
    sev = record.get("issue_severity") or ""
    at = record.get("activity_type") or ""
    fm = record.get("failure_mode") or ""
    return f"""Record ID: {record.get('record_id', 'unknown')}
Activity type: {at}
Failure mode: {fm}
Issue severity: {sev}
Outcome class: {oc}

WHAT HAPPENED:
{wh}

LESSON LEARNT:
{ll}

EVIDENCE EXCERPT:
{ee}"""


def parse_response(text, record_id):
    text = text.strip()
    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"event_type": "parse_error", "consequence_level": None,
                "confidence": 0, "_raw": text[:200]}


def submit_batch(records, batch_num=0):
    """Submit a batch of records to the Anthropic batch API."""
    client = anthropic.Anthropic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    requests = []
    for r in records:
        rid = r.get("record_id", "unknown")
        requests.append({
            "custom_id": rid,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": build_user_prompt(r)}],
            },
        })

    # Write JSONL
    jsonl_path = OUTPUT_DIR / f"batch_{batch_num}.jsonl"
    with open(jsonl_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    print(f"Wrote {len(requests)} requests to {jsonl_path}")

    # Submit
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")

    # Save state
    state = {"batch_id": batch.id, "batch_num": batch_num, "n_requests": len(requests)}
    with open(BATCH_STATE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"State saved to {BATCH_STATE}")


def check_status():
    """Check batch status."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found. Run --batch submit first.")
    with open(BATCH_STATE) as f:
        state = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch: {state['batch_id']}")
    print(f"Status: {batch.processing_status}")
    print(f"Requests: {state['n_requests']}")
    counts = batch.request_counts
    print(f"  Processing: {counts.processing}")
    print(f"  Succeeded: {counts.succeeded}")
    print(f"  Errored: {counts.errored}")
    print(f"  Canceled: {counts.canceled}")
    print(f"  Expired: {counts.expired}")


def collect_results():
    """Collect batch results and save per-doc YAML files."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        state = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])

    if batch.processing_status != "ended":
        print(f"Batch not done yet: {batch.processing_status}")
        return

    # Collect results
    results = {}
    errors = 0
    for result in client.messages.batches.results(state["batch_id"]):
        rid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            parsed = parse_response(text, rid)
            results[rid] = parsed
        else:
            errors += 1
            results[rid] = {"event_type": "api_error", "consequence_level": None,
                            "confidence": 0}

    print(f"Collected {len(results)} results ({errors} errors)")

    # Group by doc stem and save
    records = load_all_records()
    doc_groups = {}
    for r in records:
        stem = r["_doc_stem"]
        doc_groups.setdefault(stem, []).append(r)

    files_written = 0
    for stem, recs in sorted(doc_groups.items()):
        out_records = []
        for r in recs:
            rid = r.get("record_id")
            if rid in results:
                entry = {"record_id": rid}
                entry.update(results[rid])
                out_records.append(entry)
        if out_records:
            out_path = OUTPUT_DIR / f"{stem}_event_type.yaml"
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(out_records, f, default_flow_style=False, allow_unicode=True,
                          sort_keys=False)
            files_written += 1

    print(f"Wrote {files_written} files to {OUTPUT_DIR}")

    # Print distribution
    print_stats(results)


def print_stats(results=None):
    """Print distribution of event types and consequence levels."""
    if results is None:
        # Load from saved files
        results = {}
        for path in sorted(glob.glob(str(OUTPUT_DIR / "doc_*_event_type.yaml"))):
            with open(path) as f:
                data = yaml.safe_load(f)
            if data:
                for r in data:
                    results[r["record_id"]] = r

    et_counts = Counter()
    cl_counts = Counter()
    et_cl = Counter()

    for rid, r in results.items():
        et = r.get("event_type", "unknown")
        cl = r.get("consequence_level")
        et_counts[et] += 1
        if et == "realised_delivery_event" and cl:
            cl_counts[cl] += 1
            et_cl[cl] += 1

    total = sum(et_counts.values())
    print(f"\n{'='*60}")
    print(f"EVENT TYPE DISTRIBUTION ({total} records)")
    print(f"{'='*60}")
    for et in EVENT_TYPES + ["parse_error", "api_error"]:
        n = et_counts.get(et, 0)
        if n > 0:
            print(f"  {et:<35s} {n:>6d}  ({n/total*100:.1f}%)")

    if cl_counts:
        n_rde = et_counts.get("realised_delivery_event", 0)
        print(f"\n{'='*60}")
        print(f"CONSEQUENCE LEVEL (of {n_rde} realised delivery events)")
        print(f"{'='*60}")
        for cl in CONSEQUENCE_LEVELS:
            n = cl_counts.get(cl, 0)
            if n > 0:
                print(f"  {cl:<35s} {n:>6d}  ({n/n_rde*100:.1f}%)")

        # The three tiers
        mat_plus = sum(cl_counts.get(c, 0) for c in ["material_impact", "project_threatening", "project_terminated"])
        threat_plus = sum(cl_counts.get(c, 0) for c in ["project_threatening", "project_terminated"])
        terminated = cl_counts.get("project_terminated", 0)
        print(f"\n  --- Escalation tiers ---")
        print(f"  Material impact+:      {mat_plus:>6d}  ({mat_plus/n_rde*100:.1f}% of realised events)")
        print(f"  Project threatening+:  {threat_plus:>6d}  ({threat_plus/n_rde*100:.1f}% of realised events)")
        print(f"  Project terminated:    {terminated:>6d}  ({terminated/n_rde*100:.1f}% of realised events)")


def main():
    parser = argparse.ArgumentParser(description="Classify event type and consequence level")
    parser.add_argument("--batch", choices=["submit", "status", "collect"],
                        help="Batch API operation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts for first 5 records")
    parser.add_argument("--stats", action="store_true",
                        help="Show distribution from collected results")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    records = load_all_records()
    print(f"Loaded {len(records)} records")

    if args.dry_run:
        for r in records[:5]:
            print(f"\n{'='*80}")
            print(f"Record: {r.get('record_id')}")
            print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
            prompt = build_user_prompt(r)
            print(f"User prompt ({len(prompt)} chars):")
            print(prompt)
        # Cost estimate
        # ~1500 chars system + ~500 chars user = ~500 tokens input per record
        # ~50 tokens output per record
        est_input = len(records) * 500 / 1e6
        est_output = len(records) * 50 / 1e6
        cost = est_input * 0.80 + est_output * 4.0  # Haiku pricing
        print(f"\nEstimated cost: ~${cost:.2f} ({len(records)} records)")
        return

    if args.batch == "submit":
        # Split into batches if needed
        for i in range(0, len(records), BATCH_SIZE):
            batch_recs = records[i:i + BATCH_SIZE]
            submit_batch(batch_recs, batch_num=i // BATCH_SIZE)
    elif args.batch == "status":
        check_status()
    elif args.batch == "collect":
        collect_results()


if __name__ == "__main__":
    main()
