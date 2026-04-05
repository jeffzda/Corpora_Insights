#!/usr/bin/env python3
"""
Synthesise project-level events from per-document delivery insight records.

For each project, clusters records that describe the same underlying event into
a single synthesised event record with corroboration counts and provenance links.

Pre-computes TF-IDF similarity hints and sorts records by failure_mode/event_type
to help the model identify related records in large projects.

Usage:
    python scripts/synthesise_project_events.py --project "Yuri"     # test on one project
    python scripts/synthesise_project_events.py --dry-run             # print prompt for first project
    python scripts/synthesise_project_events.py --batch submit        # batch all projects
    python scripts/synthesise_project_events.py --batch status
    python scripts/synthesise_project_events.py --batch collect
    python scripts/synthesise_project_events.py --stats               # summary from collected results
"""

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from math import log, sqrt
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
MAX_TOKENS = 16384
BATCH_SIZE = 10_000  # Anthropic batch API limit

SYSTEM_PROMPT = """You are synthesising delivery insight records from a single ARENA project into distinct events.

You will receive a set of insight records — extracted from one or more documents about the same project. Many records describe the SAME underlying event from different documents or perspectives. Your job is to identify the distinct events and synthesise each one.

Records are sorted by failure mode and event type to group related records together. You will also receive SIMILARITY HINTS showing pairs of records that share significant vocabulary — these are candidates for merging, but use your judgement.

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

# ---------------------------------------------------------------------------
# TF-IDF similarity
# ---------------------------------------------------------------------------

STOPWORDS = frozenset(
    "the a an to of in for and or is was were are be been being have has had "
    "that this with from by on at as it its not but which their they them "
    "than into also can could would should may will about more other all some "
    "any each no so if when very most such only own same both during after "
    "before between through over under further then once did does do these "
    "those here there where how what who whom project arena dlv record".split()
)


def _tokenise(text):
    words = re.findall(r'[a-z]{3,}', (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


def compute_similarity_hints(records, threshold=0.15, max_hints=50):
    """Compute TF-IDF cosine similarity between records and return hint lines."""
    docs = [
        _tokenise((r.get("what_happened", "") + " " + r.get("lesson_learnt", "")))
        for r in records
    ]

    # Document frequency
    df = Counter()
    for doc in docs:
        for w in set(doc):
            df[w] += 1
    n_docs = len(docs)
    if n_docs < 2:
        return ""

    # TF-IDF vectors
    def tfidf(doc):
        tf = Counter(doc)
        vec = {}
        for w, count in tf.items():
            if df[w] < n_docs * 0.7:  # skip very common terms
                vec[w] = count * log(n_docs / df[w])
        return vec

    def cosine(v1, v2):
        common = set(v1) & set(v2)
        if not common:
            return 0.0
        dot = sum(v1[w] * v2[w] for w in common)
        mag1 = sqrt(sum(v ** 2 for v in v1.values()))
        mag2 = sqrt(sum(v ** 2 for v in v2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    vecs = [tfidf(d) for d in docs]

    # Find similar pairs
    pairs = []
    for i in range(n_docs):
        for j in range(i + 1, n_docs):
            sim = cosine(vecs[i], vecs[j])
            if sim >= threshold:
                shared = sorted(
                    set(vecs[i]) & set(vecs[j]),
                    key=lambda w: -(vecs[i].get(w, 0) + vecs[j].get(w, 0)),
                )[:5]
                pairs.append((sim, records[i]["record_id"], records[j]["record_id"], shared))

    if not pairs:
        return ""

    pairs.sort(reverse=True)
    pairs = pairs[:max_hints]

    lines = ["SIMILARITY HINTS (records sharing significant vocabulary):"]
    for sim, r1, r2, shared in pairs:
        lines.append(f"  {sim:.2f}  {r1} ↔ {r2}  [{' '.join(shared)}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Record sorting
# ---------------------------------------------------------------------------

EVENT_TYPE_ORDER = {
    "realised_delivery_event": 0,
    "design_technical_finding": 1,
    "identified_future_risk": 2,
    "contextual_observation": 3,
    "unknown": 4,
}


def sort_records(records):
    """Sort records by event_type, then failure_mode, then severity descending."""
    severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3, "none": 4}
    return sorted(
        records,
        key=lambda r: (
            EVENT_TYPE_ORDER.get(r.get("event_type", "unknown"), 4),
            r.get("failure_mode_v3") or "zzz",
            severity_order.get(r.get("issue_severity", "none"), 4),
        ),
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_data():
    """Load all per_doc records with fm_v3 and event_type merged. Returns dict of project -> records."""
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

    # Load per_doc and group by kb_associated_project
    projects = defaultdict(list)
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
        if not recs:
            continue
        for r in recs:
            pname = r.get("kb_associated_project")
            if not pname:
                continue
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
            projects[pname].append(rec)

    # Filter to 2+ records
    return {k: v for k, v in projects.items() if len(v) >= 2}


def load_project_records(project_name_pattern):
    """Load records for a single project by name pattern."""
    all_projects = load_all_data()
    pattern = project_name_pattern.lower()
    for pname, recs in all_projects.items():
        if re.search(r'\b' + re.escape(pattern) + r'\b', pname.lower()):
            return pname, recs
    return None, []


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_user_prompt(records, project_name):
    """Build the user prompt with sorted records and similarity hints."""
    records = sort_records(records)
    hints = compute_similarity_hints(records)

    lines = [f"Project: {project_name}", f"Total records: {len(records)}", ""]
    if hints:
        lines.append(hints)
        lines.append("")

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


# ---------------------------------------------------------------------------
# Single project run
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def submit_batch():
    """Submit all projects to the Anthropic batch API."""
    client = anthropic.Anthropic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    projects = load_all_data()
    print(f"Loaded {len(projects)} projects with 2+ records "
          f"({sum(len(v) for v in projects.values())} total records)")

    # Build requests
    requests = []
    project_index = []
    for pname in sorted(projects):
        recs = projects[pname]
        prompt = build_user_prompt(recs, pname)

        # Scale max_tokens with project size
        est_events = max(1, int(len(recs) * 0.6))
        max_tok = min(MAX_TOKENS, max(4096, est_events * 500))

        requests.append({
            "custom_id": f"proj_{len(requests):04d}",
            "params": {
                "model": MODEL,
                "max_tokens": max_tok,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
        project_index.append({
            "id": f"proj_{len(project_index):04d}",
            "project_name": pname,
            "n_records": len(recs),
            "record_ids": [r["record_id"] for r in recs],
        })

    # Save project index
    with open(OUTPUT_DIR / "project_index.json", "w") as f:
        json.dump(project_index, f, indent=2)

    # Submit in batches of BATCH_SIZE
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
    print(f"\nState saved to {BATCH_STATE}")


def check_status():
    """Check batch status."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found. Run --batch submit first.")
    with open(BATCH_STATE) as f:
        states = json.load(f)
    if isinstance(states, dict):
        states = [states]

    client = anthropic.Anthropic()
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        counts = batch.request_counts
        print(f"Batch {state.get('batch_num', '?')}: {state['batch_id']}")
        print(f"  Status: {batch.processing_status}")
        print(f"  Requests: {state['n_requests']}")
        print(f"  Processing: {counts.processing}, Succeeded: {counts.succeeded}, "
              f"Errored: {counts.errored}")
        print()


def collect_results():
    """Collect batch results and save per-project event files."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        states = json.load(f)
    if isinstance(states, dict):
        states = [states]
    with open(OUTPUT_DIR / "project_index.json") as f:
        project_index = json.load(f)

    client = anthropic.Anthropic()

    # Check all done
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        if batch.processing_status != "ended":
            print(f"Batch {state.get('batch_num', '?')} not done: {batch.processing_status}")
            return

    # Collect all results
    results = {}
    errors = 0
    for state in states:
        for result in client.messages.batches.results(state["batch_id"]):
            pid = result.custom_id
            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    m = re.search(r'\[.*\]', text, re.DOTALL)
                    try:
                        parsed = json.loads(m.group()) if m else None
                    except (json.JSONDecodeError, AttributeError):
                        parsed = None
                if parsed is None:
                    errors += 1
                    parsed = {"_error": "parse_error", "_raw": text[:500]}
                results[pid] = parsed
            else:
                errors += 1
                results[pid] = {"_error": "api_error"}

    print(f"Collected {len(results)} results ({errors} errors)")

    # Save per-project YAML files
    total_events = 0
    total_records_covered = 0
    total_records_expected = 0
    coverage_issues = []

    for entry in project_index:
        pid = entry["id"]
        pname = entry["project_name"]
        r = results.get(pid)
        if not r or isinstance(r, dict) and "_error" in r:
            continue

        events = r if isinstance(r, list) else []
        total_events += len(events)

        # Check coverage
        expected = set(entry["record_ids"])
        covered = set()
        for e in events:
            for s in e.get("source_records", []):
                covered.add(s["record_id"])
        total_records_expected += len(expected)
        total_records_covered += len(covered & expected)
        missing = expected - covered
        if missing:
            coverage_issues.append((pname, len(missing), len(expected)))

        # Stamp project name onto each event
        for e in events:
            e["project_name"] = pname

        # Save
        safe_name = re.sub(r'[^\w\-]', '_', pname)[:80]
        out_path = OUTPUT_DIR / f"{safe_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"EVENT SYNTHESIS RESULTS")
    print(f"{'='*60}")
    print(f"Projects processed:  {len(project_index)}")
    print(f"Total events:        {total_events}")
    print(f"Record coverage:     {total_records_covered}/{total_records_expected} "
          f"({total_records_covered/total_records_expected*100:.1f}%)")
    print(f"Errors:              {errors}")

    if coverage_issues:
        print(f"\nCoverage issues ({len(coverage_issues)} projects):")
        for pname, missing, total in sorted(coverage_issues, key=lambda x: -x[1])[:20]:
            print(f"  {missing:3d}/{total:3d} missing  {pname[:60]}")

    # Compression ratio
    if total_events > 0:
        print(f"\nCompression: {total_records_expected} records → {total_events} events "
              f"({total_events/total_records_expected*100:.0f}%)")

    print(f"\nResults saved to {OUTPUT_DIR}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Synthesise project-level events")
    parser.add_argument("--project", type=str, help="Project name pattern to test")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    parser.add_argument("--stats", action="store_true", help="Show stats from collected results")
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

    if args.project:
        pname, records = load_project_records(args.project)
        if not records:
            print(f"No records found matching '{args.project}'")
            return

        if args.dry_run:
            prompt = build_user_prompt(records, pname)
            print(f"Project: {pname}")
            print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
            print(f"User prompt: {len(prompt)} chars")
            print(f"Records: {len(records)}")
            hints = compute_similarity_hints(records)
            if hints:
                print(f"\n{hints}")
            return

        events = run_single(pname, records)
        if events:
            print_events(events)

            # Verify coverage
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
