#!/usr/bin/env python3
"""
Verify and correct synthesised project events.

The initial synthesis pass (synthesise_project_events.py) clustered records and
wrote narratives in a single Sonnet call per project. The clustering is good but
the narratives may reference information from other events (context contamination)
and severity was inherited from source records rather than derived from actual impact.

This script sends each event individually to Haiku with only its own source records,
asking the model to:
1. Verify narratives (remove contamination, add missing details)
2. Reassess severity from actual impact described
3. Reassess failure mode from verified narrative
4. Validate event_type (especially RDE claims)
5. Flag misattributed source records

Usage:
    python scripts/verify_event_synthesis.py --dry-run              # print prompts + cost estimate
    python scripts/verify_event_synthesis.py --batch submit
    python scripts/verify_event_synthesis.py --batch status
    python scripts/verify_event_synthesis.py --batch collect
    python scripts/verify_event_synthesis.py --stats                # compare v1 vs v2
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
PER_DOC_DIR = ROOT / "insights" / "per_doc"
INPUT_DIR = ROOT / "insights" / "per_project_events"
OUTPUT_DIR = ROOT / "insights" / "per_project_events_v2"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
EVENT_INDEX = OUTPUT_DIR / "event_index.json"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 3200
BATCH_SIZE = 10_000


SYSTEM_PROMPT = """You are verifying synthesised delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

You will receive a synthesised event and the original source records it was built from. The synthesis was produced by an earlier model pass that had access to ALL records for the project simultaneously, so the narrative may reference information that belongs to other events — not to this event's source records.

Your job is to verify and correct five things:

## 1. NARRATIVE VERIFICATION

Check that what_happened, consequence, and resolution are fully supportable from the provided source records ALONE. For each field:
- REMOVE any claim, detail, or reference not inferrable from the source records provided. This includes names of mechanisms, organisations, dollar figures, or technical details that appear nowhere in the sources.
- ADD any important detail present in the source records but missing from the synthesis.
- PRESERVE specific quantified details (dates, durations, dollar amounts, percentages) that ARE supported by sources.
- Keep the narrative concise: 2-4 sentences for what_happened, 1-2 for consequence and resolution.
- If the existing narrative is already a faithful synthesis with no contamination and no missing details, keep it as-is.

## 2. SEVERITY REASSESSMENT

Derive severity from what the verified narrative actually describes — the concrete impact, not how dramatically the source records frame it. Knowledge Bank reports often use advocacy language ("critical barrier", "major challenge") for issues that were actually navigated without significant damage.

Definitions:
- **none**: No adverse impact. An observation, finding, or successful outcome with no negative consequence.
- **minor**: Minor inconvenience or small adjustment. No measurable cost, delay (>1 month), or performance impact stated.
- **moderate**: Measurable but contained impact — a specific delay, cost increase, or performance shortfall that was managed without threatening the project.
- **major**: Significant quantified impact — multi-month delays, substantial budget overruns, major scope reductions, or measurable performance shortfalls that materially affected project outcomes.
- **critical**: Project viability threatened or project terminated/discontinued.

Key: "threatened to" or "could have" is NOT the same as "did". A barrier that was overcome through pricing incentives is moderate (adaptation), not major. A risk that was identified but didn't materialise is none or minor.

## 3. FAILURE MODE REASSESSMENT

Derive the failure mode from the verified narrative. Choose exactly one:
- **technical underperformance**: Equipment, materials, or technology did not perform as expected
- **unvalidated integration**: Components or systems failed when combined, or interfaces were not adequately tested
- **execution & logistics**: Construction, procurement, installation, or operational execution problems
- **regulatory & approvals**: Permitting, regulatory compliance, grid connection approvals, or policy barriers
- **commercial & market**: Offtake, financing, market conditions, commercial viability issues
- **coordination & stakeholders**: Communication, stakeholder management, community engagement, partnership issues
- **data & measurement**: Monitoring, data quality, measurement methodology, or baseline data problems
- **no major failure stated**: The event does not describe a failure or adverse outcome

## 4. EVENT TYPE VALIDATION

If the event is tagged as realised_delivery_event, verify that what_happened describes a concrete project consequence (delay, cost, performance loss, scope change, cancellation). If it instead describes a finding, observation, or unrealised risk, provide the correct event_type:
- **realised_delivery_event**: concrete adverse outcome experienced by the project
- **design_technical_finding**: analysis/testing revealed a limitation (the finding IS the output)
- **identified_future_risk**: risk flagged but not materialised
- **contextual_observation**: market/policy/industry commentary, not a project event

## 5. MISATTRIBUTED RECORD DETECTION

If any source record does not appear to describe the same event as the others, flag it. A record is misattributed if its what_happened and lesson_learnt describe a clearly different occurrence — not merely a different perspective on the same event. Different perspectives, timeframes, or emphasis on the same underlying event are FINE and should NOT be flagged.

For singleton events (only 1 source record), do not flag — there is nothing to compare against.

## OUTPUT FORMAT

Respond ONLY with a JSON object (no markdown fencing, no explanation):

{"event_title": "...", "what_happened": "...", "consequence": "... or null", "resolution": "... or null", "severity": "none|minor|moderate|major|critical", "failure_mode": "...", "event_type": "...", "narrative_changed": true/false, "severity_changed": true/false, "failure_mode_changed": true/false, "flagged_records": [{"record_id": "ARENA-DLV-XXXX", "reason": "..."}] or null}"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_source_records():
    """Load all per-doc records into a flat dict keyed by record_id."""
    records = {}
    for f in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if not data:
            continue
        for r in data:
            records[r["record_id"]] = {
                "what_happened": r.get("what_happened") or "",
                "lesson_learnt": r.get("lesson_learnt") or "",
                "evidence_excerpt": r.get("evidence_excerpt") or "",
                "issue_severity": r.get("issue_severity") or "unknown",
            }
    return records


def load_all_events():
    """Load all synthesised events, returning (source_file, event_index, event_dict) tuples."""
    events = []
    for f in sorted(glob.glob(str(INPUT_DIR / "*.json"))):
        fname = Path(f).name
        # Skip metadata files
        if fname in ("batch_state.json", "batch_state_redo.json",
                      "project_index.json", "event_index.json"):
            continue
        with open(f) as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            continue
        for i, e in enumerate(data):
            if not e.get("source_records"):
                continue
            events.append((f, i, e))
    return events


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_user_prompt(event, source_map):
    """Build the user prompt for a single event verification."""
    lines = []
    lines.append("CURRENT SYNTHESISED EVENT:")
    lines.append(f"Event title: {event.get('event_title', '')}")
    lines.append(f"Event type: {event.get('event_type', '')}")
    lines.append(f"Severity: {event.get('severity', '')}")
    lines.append(f"Failure mode: {event.get('failure_mode', '')}")
    lines.append("")
    lines.append(f"What happened: {event.get('what_happened', '')}")
    lines.append(f"Consequence: {event.get('consequence') or 'null'}")
    lines.append(f"Resolution: {event.get('resolution') or 'null'}")

    sources = event.get("source_records", [])
    lines.append(f"\nSOURCE RECORDS ({len(sources)} records):")

    for s in sources:
        rid = s["record_id"]
        role = s.get("role", "unknown")
        rec = source_map.get(rid)
        lines.append(f"\n--- Record {rid} (role: {role}) ---")
        if rec:
            lines.append(f"What happened: {rec['what_happened']}")
            lines.append(f"Lesson learnt: {rec['lesson_learnt']}")
            lines.append(f"Severity: {rec['issue_severity']}")
            # Include evidence excerpt if short enough
            excerpt = rec["evidence_excerpt"]
            if excerpt and len(excerpt) <= 200:
                lines.append(f"Evidence: {excerpt}")
        else:
            lines.append("[source record not found in registry]")

    return "\n".join(lines)


def parse_response(text):
    """Parse JSON response with regex fallback."""
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
        return None


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def submit_batch():
    """Submit all events to the Anthropic batch API."""
    client = anthropic.Anthropic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_map = load_source_records()
    print(f"Loaded {len(source_map)} source records")

    all_events = load_all_events()
    print(f"Loaded {len(all_events)} events")

    # Build requests and event index
    requests = []
    event_index = []
    total_input_chars = 0

    for source_file, event_idx, event in all_events:
        custom_id = f"evt_{len(requests):05d}"
        prompt = build_user_prompt(event, source_map)
        total_input_chars += len(prompt) + len(SYSTEM_PROMPT)

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
        event_index.append({
            "custom_id": custom_id,
            "source_file": source_file,
            "event_index": event_idx,
            "event_id": event.get("event_id", "?"),
            "project_name": event.get("project_name", Path(source_file).stem),
            "original_severity": event.get("severity", "?"),
            "original_failure_mode": event.get("failure_mode", "?"),
        })

    # Save event index
    with open(EVENT_INDEX, "w") as f:
        json.dump(event_index, f, indent=2)
    print(f"Saved event index ({len(event_index)} entries) to {EVENT_INDEX}")

    # Cost estimate
    est_input_tokens = total_input_chars / 4
    est_output_tokens = len(requests) * 500
    est_cost = (est_input_tokens / 1e6 * 0.40 + est_output_tokens / 1e6 * 2.00)
    print(f"Estimated cost: ~${est_cost:.2f} (batch 50% discount)")

    # Submit in batches
    all_states = []
    for batch_num, start in enumerate(range(0, len(requests), BATCH_SIZE)):
        batch_reqs = requests[start:start + BATCH_SIZE]

        jsonl_path = OUTPUT_DIR / f"batch_{batch_num}.jsonl"
        with open(jsonl_path, "w") as f:
            for req in batch_reqs:
                f.write(json.dumps(req) + "\n")
        print(f"Wrote {len(batch_reqs)} requests to {jsonl_path}")

        batch = client.messages.batches.create(requests=batch_reqs)
        print(f"Batch {batch_num} submitted: {batch.id}")
        print(f"Status: {batch.processing_status}")

        all_states.append({
            "batch_id": batch.id,
            "batch_num": batch_num,
            "n_requests": len(batch_reqs),
        })

    with open(BATCH_STATE, "w") as f:
        json.dump(all_states, f, indent=2)
    print(f"State saved to {BATCH_STATE}")


def _load_batch_states():
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found. Run --batch submit first.")
    with open(BATCH_STATE) as f:
        state = json.load(f)
    if isinstance(state, dict):
        return [state]
    return state


def check_status():
    states = _load_batch_states()
    client = anthropic.Anthropic()
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        print(f"Batch {state.get('batch_num', '?')}: {state['batch_id']}")
        print(f"  Status: {batch.processing_status}")
        counts = batch.request_counts
        print(f"  Processing: {counts.processing}, "
              f"Succeeded: {counts.succeeded}, Errored: {counts.errored}")


def collect_results():
    """Collect batch results and write corrected events to per_project_events_v2/."""
    states = _load_batch_states()
    client = anthropic.Anthropic()

    # Check all batches are done
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        if batch.processing_status != "ended":
            print(f"Batch {state.get('batch_num', '?')} not done: "
                  f"{batch.processing_status}")
            return

    # Load event index
    with open(EVENT_INDEX) as f:
        event_index = json.load(f)
    index_map = {e["custom_id"]: e for e in event_index}

    # Collect all results
    results = {}
    errors = 0
    for state in states:
        for result in client.messages.batches.results(state["batch_id"]):
            cid = result.custom_id
            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                parsed = parse_response(text)
                if parsed is None:
                    errors += 1
                    results[cid] = {"_error": "parse_error", "_raw": text[:500]}
                else:
                    results[cid] = parsed
            else:
                errors += 1
                results[cid] = {"_error": "api_error"}

    print(f"Collected {len(results)} results ({errors} errors)")

    # Group by source file
    file_events = defaultdict(list)
    for entry in event_index:
        file_events[entry["source_file"]].append(entry)

    # Merge and save
    OVERWRITE_KEYS = {"event_title", "what_happened", "consequence", "resolution",
                      "severity", "failure_mode", "event_type"}
    TRACKING_KEYS = {"narrative_changed", "severity_changed", "failure_mode_changed",
                     "flagged_records"}

    total_events = 0
    narrative_changed = 0
    severity_changed = 0
    fm_changed = 0
    flagged_count = 0
    sev_migration = Counter()  # (old, new) -> count

    for source_file, entries in file_events.items():
        with open(source_file) as f:
            original_events = json.load(f)
        if not isinstance(original_events, list):
            continue

        for entry in entries:
            cid = entry["custom_id"]
            idx = entry["event_index"]
            model_out = results.get(cid)
            if not model_out or "_error" in model_out:
                continue

            event = original_events[idx]
            total_events += 1

            # Store originals for tracking
            event["original_severity"] = entry["original_severity"]
            event["original_failure_mode"] = entry["original_failure_mode"]

            # Track changes
            if model_out.get("narrative_changed"):
                narrative_changed += 1
            if model_out.get("severity_changed"):
                severity_changed += 1
                sev_migration[(entry["original_severity"],
                               model_out.get("severity", "?"))] += 1
            if model_out.get("failure_mode_changed"):
                fm_changed += 1
            flags = model_out.get("flagged_records")
            if flags:
                flagged_count += len(flags)

            # Merge
            for key in OVERWRITE_KEYS:
                if key in model_out:
                    event[key] = model_out[key]
            for key in TRACKING_KEYS:
                event[key] = model_out.get(key)

        # Write to v2
        out_path = OUTPUT_DIR / Path(source_file).name
        with open(out_path, "w") as f:
            json.dump(original_events, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"VERIFICATION SUMMARY ({total_events} events)")
    print(f"{'='*60}")
    print(f"Narrative changed:     {narrative_changed:5d}  "
          f"({100*narrative_changed/total_events:.1f}%)")
    print(f"Severity changed:      {severity_changed:5d}  "
          f"({100*severity_changed/total_events:.1f}%)")
    print(f"Failure mode changed:  {fm_changed:5d}  "
          f"({100*fm_changed/total_events:.1f}%)")
    print(f"Records flagged:       {flagged_count:5d}")

    if sev_migration:
        print(f"\nSeverity migrations (top 10):")
        for (old, new), count in sev_migration.most_common(10):
            print(f"  {old} -> {new}: {count}")

    print(f"\nResults saved to {OUTPUT_DIR}/")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats():
    """Show detailed change statistics from v2 results."""
    sev_order = ["none", "minor", "moderate", "major", "critical"]
    fm_values = ["technical underperformance", "unvalidated integration",
                 "execution & logistics", "regulatory & approvals",
                 "commercial & market", "coordination & stakeholders",
                 "data & measurement", "no major failure stated"]

    total = 0
    nar_changed = 0
    sev_changed = 0
    fm_changed = 0
    flagged_total = 0
    sev_matrix = Counter()
    fm_matrix = Counter()
    flagged_details = []

    for f in sorted(glob.glob(str(OUTPUT_DIR / "*.json"))):
        fname = Path(f).name
        if fname in ("batch_state.json", "event_index.json") or fname.startswith("batch_"):
            continue
        with open(f) as fh:
            events = json.load(fh)
        if not isinstance(events, list):
            continue
        for e in events:
            if "original_severity" not in e:
                continue
            total += 1
            if e.get("narrative_changed"):
                nar_changed += 1
            if e.get("severity_changed"):
                sev_changed += 1
            if e.get("failure_mode_changed"):
                fm_changed += 1
            sev_matrix[(e.get("original_severity", "?"),
                        e.get("severity", "?"))] += 1
            fm_matrix[(e.get("original_failure_mode", "?"),
                       e.get("failure_mode", "?"))] += 1
            flags = e.get("flagged_records")
            if flags:
                flagged_total += len(flags)
                for fl in flags:
                    flagged_details.append((
                        e.get("project_name", "?"),
                        e.get("event_id", "?"),
                        fl.get("record_id", "?"),
                        fl.get("reason", "?"),
                    ))

    if total == 0:
        print("No v2 results found.")
        return

    print(f"\n{'='*60}")
    print(f"VERIFICATION STATISTICS ({total} events)")
    print(f"{'='*60}")
    print(f"Narrative changed:     {nar_changed:5d}  ({100*nar_changed/total:.1f}%)")
    print(f"Severity changed:      {sev_changed:5d}  ({100*sev_changed/total:.1f}%)")
    print(f"Failure mode changed:  {fm_changed:5d}  ({100*fm_changed/total:.1f}%)")
    print(f"Records flagged:       {flagged_total:5d}")

    # Severity migration matrix
    print(f"\nSEVERITY MIGRATION MATRIX")
    print(f"{'':>15}", end="")
    for s in sev_order:
        print(f"  {s:>8}", end="")
    print()
    for old in sev_order:
        print(f"{old:>15}", end="")
        for new in sev_order:
            c = sev_matrix.get((old, new), 0)
            print(f"  {c:>8}", end="")
        print()

    # Failure mode changes
    fm_changes = {k: v for k, v in fm_matrix.items() if k[0] != k[1]}
    if fm_changes:
        print(f"\nFAILURE MODE CHANGES (top 15):")
        for (old, new), count in Counter(fm_changes).most_common(15):
            print(f"  {old} -> {new}: {count}")

    # Flagged records
    if flagged_details:
        print(f"\nFLAGGED RECORDS ({flagged_total} total):")
        for proj, eid, rid, reason in flagged_details[:30]:
            print(f"  {proj} / {eid}: {rid}")
            print(f"    {reason}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Verify event synthesis")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts for first 5 events + cost estimate")
    parser.add_argument("--stats", action="store_true",
                        help="Show change statistics from v2 results")
    args = parser.parse_args()

    if args.batch == "status":
        check_status()
        return

    if args.batch == "collect":
        collect_results()
        return

    if args.batch == "submit":
        submit_batch()
        return

    if args.stats:
        print_stats()
        return

    if args.dry_run:
        source_map = load_source_records()
        all_events = load_all_events()
        print(f"Source records: {len(source_map)}")
        print(f"Events to verify: {len(all_events)}")

        total_chars = 0
        for _, _, event in all_events:
            prompt = build_user_prompt(event, source_map)
            total_chars += len(prompt) + len(SYSTEM_PROMPT)

        est_input_tokens = total_chars / 4
        est_output_tokens = len(all_events) * 500
        est_cost = (est_input_tokens / 1e6 * 0.40 + est_output_tokens / 1e6 * 2.00)
        print(f"Estimated input tokens: {est_input_tokens:,.0f}")
        print(f"Estimated output tokens: {est_output_tokens:,.0f}")
        print(f"Estimated cost: ~${est_cost:.2f} (batch 50% discount)")

        print(f"\n--- Sample prompts (first 3) ---")
        for _, _, event in all_events[:3]:
            prompt = build_user_prompt(event, source_map)
            print(f"\n{'='*60}")
            print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
            print(f"User prompt: {len(prompt)} chars")
            print(prompt[:1500])
            print("..." if len(prompt) > 1500 else "")

        return

    parser.print_help()


if __name__ == "__main__":
    main()
