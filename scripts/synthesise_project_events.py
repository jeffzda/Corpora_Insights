#!/usr/bin/env python3
"""
Synthesise project-level events from per-document delivery insight records.

For each project, clusters records that describe the same underlying event into
a single synthesised event record with corroboration counts and provenance links.

Usage:
    python scripts/synthesise_project_events.py --project "Yuri"     # test on one project
    python scripts/synthesise_project_events.py --dry-run             # print prompt for first project
    python scripts/synthesise_project_events.py --batch submit        # batch all projects
    python scripts/synthesise_project_events.py --batch status
    python scripts/synthesise_project_events.py --batch collect
"""

import argparse
import glob
import json
import re
from collections import defaultdict
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
FM_V3_DIR = ROOT / "insights" / "per_doc_fm_v3"
EVENT_TYPE_DIR = ROOT / "insights" / "per_doc_event_type"
OUTPUT_DIR = ROOT / "insights" / "per_project_events"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

SYSTEM_PROMPT = """You are synthesising delivery insight records from a single ARENA project into distinct events.

You will receive a set of insight records — extracted from one or more documents about the same project. Many records describe the SAME underlying event from different documents or perspectives. Your job is to identify the distinct events and synthesise each one.

## What is an "event"?

An event is a distinct thing that happened (or was observed/found) during the project. Examples:
- "EPA approval took 24 months instead of 12" — one event, even if mentioned in 3 different reports
- "Electrolyser vendor couldn't meet Australian standards" — one event
- "Budget increased from $87M to $123M" — one event (the overall cost overrun)
- "Community engagement was relationship-based" — one observation

Two records describe the SAME event if they refer to the same underlying occurrence, finding, or observation — even if they use different words, emphasise different aspects, or come from different time periods. A lessons-learned report and a progress report describing the same delay are the same event.

Two records describe DIFFERENT events if they are about genuinely separate occurrences — e.g., "harmonic filter procurement delay" and "EPA approval delay" are different events even though both caused schedule slippage.

## How to synthesise

For each distinct event, produce a synthesised record that:
1. Combines the most specific and quantified information from all constituent records
2. Captures the full narrative arc (cause → impact → resolution) where available
3. Uses the HIGHEST severity from any constituent record
4. Preserves the event_type from the majority of constituent records
5. Lists all source record IDs with their role (primary = most detailed account, corroborating = adds detail or confirms)

## Output format

Respond with a JSON array of synthesised events. Each event:

```json
{
  "event_id": "EVT-001",
  "event_title": "Short descriptive title (5-10 words)",
  "event_type": "realised_delivery_event|design_technical_finding|identified_future_risk|contextual_observation",
  "what_happened": "Synthesised narrative combining the best detail from all sources. Include specific numbers, durations, dollar amounts where available. 2-4 sentences.",
  "consequence": "What was the impact? Be specific — cost, delay duration, performance shortfall. Null if no consequence.",
  "resolution": "How was it resolved or adapted? Null if unresolved or not applicable.",
  "severity": "none|minor|moderate|major|critical",
  "failure_mode": "The most appropriate failure mode from: technical underperformance|unvalidated integration|execution & logistics|regulatory & approvals|commercial & market|coordination & stakeholders|data & measurement|no major failure stated",
  "date_range": "Earliest to latest date mentioned, e.g. '2021-2022' or '2023-07'. Null if no dates mentioned.",
  "source_records": [
    {"record_id": "ARENA-DLV-XXXX", "role": "primary"},
    {"record_id": "ARENA-DLV-YYYY", "role": "corroborating"}
  ],
  "corroboration_count": 3
}
```

## Rules

- Every input record MUST appear in exactly one event's source_records list
- Do NOT merge events that are genuinely distinct just because they have the same failure mode
- DO merge records that describe the same event from different documents/timeframes
- Records with event_type "contextual_observation" or "design_technical_finding" that describe the same topic should be merged
- If a record adds no new information beyond another record, it is "corroborating"
- The "primary" record is the one with the most specific/quantified detail
- corroboration_count = total number of source records for that event
- Sort events by severity (critical > major > moderate > minor > none), then by corroboration_count descending

Respond ONLY with the JSON array. No markdown fencing, no explanation."""


def load_project_records(project_name_pattern):
    """Load all records for projects matching a name pattern, with fm_v3 and event_type merged."""
    # Load all per_doc records
    all_records = []
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                stem = Path(path).stem
                for r in recs:
                    r["_doc_stem"] = stem
                all_records.extend(recs)

    # Load fm_v3
    fm_v3_map = {}
    for path in sorted(glob.glob(str(FM_V3_DIR / "doc_*_fm_v3.yaml"))):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data:
                for r in data:
                    fm_v3_map[r["record_id"]] = r.get("failure_mode_v3") or r.get("failure_mode")

    # Load event_type
    et_map = {}
    for path in sorted(glob.glob(str(EVENT_TYPE_DIR / "doc_*_event_type.yaml"))):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data:
                for r in data:
                    et_map[r["record_id"]] = r.get("event_type")

    # Filter by project name and merge
    pattern = project_name_pattern.lower()
    project_records = []
    for r in all_records:
        pname = (r.get("kb_associated_project") or r.get("project_name") or "")
        # Match if pattern appears as a whole word in the project name
        if re.search(r'\b' + re.escape(pattern) + r'\b', pname.lower()):
            rid = r.get("record_id")
            rec = {
                "record_id": rid,
                "source_title": r.get("source_title"),
                "publish_date": r.get("publish_date"),
                "what_happened": r.get("what_happened"),
                "lesson_learnt": r.get("lesson_learnt"),
                "evidence_excerpt": r.get("evidence_excerpt"),
                "issue_severity": r.get("issue_severity"),
                "failure_mode_v3": fm_v3_map.get(rid, r.get("failure_mode")),
                "event_type": et_map.get(rid, "unknown"),
                "outcome_class": r.get("outcome_class"),
            }
            project_records.append(rec)

    return project_records


def build_user_prompt(records, project_name):
    """Build the user prompt with all records for a project."""
    lines = [f"Project: {project_name}", f"Total records: {len(records)}", ""]
    for r in records:
        lines.append(f"--- Record {r['record_id']} ---")
        lines.append(f"Source: {r.get('source_title', 'unknown')}")
        lines.append(f"Date: {r.get('publish_date', 'unknown')}")
        lines.append(f"Event type: {r.get('event_type', 'unknown')}")
        lines.append(f"Severity: {r.get('issue_severity', 'unknown')}")
        lines.append(f"Failure mode: {r.get('failure_mode_v3', 'unknown')}")
        lines.append(f"Outcome: {r.get('outcome_class', 'unknown')}")
        lines.append(f"What happened: {r.get('what_happened', '')}")
        lines.append(f"Lesson: {r.get('lesson_learnt', '')}")
        lines.append("")
    return "\n".join(lines)


def get_all_projects():
    """Get all projects with their record counts from per_doc files."""
    project_records = defaultdict(list)
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                for r in recs:
                    pname = r.get("kb_associated_project") or r.get("project_name") or "Unknown"
                    project_records[pname].append(r.get("record_id"))
    return {k: v for k, v in project_records.items() if len(v) >= 2}


def run_single(project_name, records):
    """Run synthesis for a single project via direct API call."""
    client = anthropic.Anthropic()
    prompt = build_user_prompt(records, project_name)

    print(f"Sending {len(records)} records for '{project_name}' ({len(prompt)} chars)...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    try:
        events = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            events = json.loads(m.group())
        else:
            print(f"Parse error: {text[:500]}")
            return None

    return events


def print_events(events):
    """Pretty-print synthesised events."""
    print(f"\n{'=' * 70}")
    print(f"SYNTHESISED EVENTS: {len(events)} distinct events")
    print(f"{'=' * 70}")
    for e in events:
        n = e.get("corroboration_count", len(e.get("source_records", [])))
        sources = ", ".join(s["record_id"] for s in e.get("source_records", []))
        print(f"\n{e['event_id']}: {e['event_title']}")
        print(f"  Type: {e['event_type']} | Severity: {e['severity']} | FM: {e['failure_mode']}")
        if e.get("date_range"):
            print(f"  Date range: {e['date_range']}")
        print(f"  Corroboration: {n} records ({sources})")
        print(f"  What happened: {e['what_happened']}")
        if e.get("consequence"):
            print(f"  Consequence: {e['consequence']}")
        if e.get("resolution"):
            print(f"  Resolution: {e['resolution']}")


def main():
    parser = argparse.ArgumentParser(description="Synthesise project-level events")
    parser.add_argument("--project", type=str, help="Project name pattern to test")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    args = parser.parse_args()

    if args.project:
        records = load_project_records(args.project)
        if not records:
            print(f"No records found matching '{args.project}'")
            return

        # Deduce project name from records
        project_name = args.project
        for r in records:
            if r.get("source_title"):
                project_name = args.project
                break

        if args.dry_run:
            prompt = build_user_prompt(records, project_name)
            print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
            print(f"User prompt: {len(prompt)} chars")
            print(f"Records: {len(records)}")
            print(f"\n{prompt[:3000]}...")
            return

        events = run_single(project_name, records)
        if events:
            print_events(events)

            # Verify all records accounted for
            input_ids = {r["record_id"] for r in records}
            output_ids = set()
            for e in events:
                for s in e.get("source_records", []):
                    output_ids.add(s["record_id"])
            missing = input_ids - output_ids
            extra = output_ids - input_ids
            if missing:
                print(f"\nWARNING: {len(missing)} input records not in any event: {missing}")
            if extra:
                print(f"\nWARNING: {len(extra)} output records not in input: {extra}")
            print(f"\nCoverage: {len(output_ids)}/{len(input_ids)} records accounted for")


if __name__ == "__main__":
    main()
