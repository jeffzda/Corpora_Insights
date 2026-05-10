#!/usr/bin/env python3
"""Synthesise project-level events from per-document delivery insight records.

Config-driven version of scripts/synthesise_project_events.py.
Uses domain config for model selection and prompt rendering.

Usage:
    python -m pipeline.synthesise --domain arena --project "Yuri"
    python -m pipeline.synthesise --domain arena --dry-run
    python -m pipeline.synthesise --domain arena --batch submit
    python -m pipeline.synthesise --domain arena --batch status
    python -m pipeline.synthesise --domain arena --batch collect
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

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAX_TOKENS = 128000
BATCH_SIZE = 10_000

STOPWORDS = frozenset(
    "the a an to of in for and or is was were are be been being have has had "
    "that this with from by on at as it its not but which their they them "
    "than into also can could would should may will about more other all some "
    "any each no so if when very most such only own same both during after "
    "before between through over under further then once did does do these "
    "those here there where how what who whom project record".split()
)


def get_dirs(cfg):
    """Get input/output directories for this domain."""
    domain_lower = cfg.domain.name.lower()
    per_doc = ROOT / "runs" / domain_lower / "per_doc"
    if not per_doc.exists():
        per_doc = ROOT / "insights" / "per_doc"
    event_type_dir = ROOT / "runs" / domain_lower / "per_doc_event_type"
    if not event_type_dir.exists() and (ROOT / "insights" / "per_doc_event_type").exists():
        event_type_dir = ROOT / "insights" / "per_doc_event_type"
    output_dir = ROOT / "runs" / domain_lower / "per_project_events"
    if not output_dir.exists() and (ROOT / "insights" / "per_project_events").exists():
        output_dir = ROOT / "insights" / "per_project_events"
    return per_doc, event_type_dir, output_dir


def _tokenise(text):
    words = re.findall(r'[a-z]{3,}', (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


def compute_similarity_hints(records, threshold=0.15, max_hints=50):
    """Compute TF-IDF cosine similarity between records and return hint lines."""
    docs = [
        _tokenise((r.get("what_happened") or "") + " " + (r.get("lesson_learnt") or ""))
        for r in records
    ]

    df = Counter()
    for doc in docs:
        for w in set(doc):
            df[w] += 1
    n_docs = len(docs)
    if n_docs < 2:
        return ""

    def tfidf(doc):
        tf = Counter(doc)
        vec = {}
        for w, count in tf.items():
            if df[w] < n_docs * 0.7:
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


EVENT_TYPE_ORDER = {
    "realised_delivery_event": 0,
    "design_technical_finding": 1,
    "identified_future_risk": 2,
    "contextual_observation": 3,
    "unknown": 4,
}


def sort_records(records):
    severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3, "none": 4}
    return sorted(
        records,
        key=lambda r: (
            EVENT_TYPE_ORDER.get(r.get("event_type", "unknown"), 4),
            r.get("failure_mode") or "zzz",
            severity_order.get(r.get("issue_severity", "none"), 4),
        ),
    )


def load_all_data(per_doc_dir, event_type_dir, grouping_field):
    """Load all per_doc records with event_type merged. Returns dict of project -> records."""
    # Load event_type
    et_map = {}
    if event_type_dir.exists():
        for path in sorted(glob.glob(str(event_type_dir / "doc_*_event_type.yaml"))):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    for r in data:
                        et_map[r["record_id"]] = r.get("event_type")

    # Load per_doc and group by project
    projects = defaultdict(list)
    for path in sorted(glob.glob(str(per_doc_dir / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
        if not recs:
            continue
        for r in recs:
            pname = r.get(grouping_field)
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
                "failure_mode": r.get("failure_mode"),
                "event_type": et_map.get(rid, "unknown"),
                "outcome_class": r.get("outcome_class"),
            }
            projects[pname].append(rec)

    return {k: v for k, v in projects.items() if len(v) >= 2}


def build_user_prompt(records, project_name):
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
        lines.append(f"Failure mode: {r.get('failure_mode', 'unknown')}")
        lines.append(f"Outcome: {r.get('outcome_class', 'unknown')}")
        lines.append(f"What happened: {r.get('what_happened', '')}")
        lines.append(f"Lesson: {r.get('lesson_learnt', '')}")
        lines.append("")
    return "\n".join(lines)


def run_single(project_name, records, model, system_prompt):
    client = anthropic.Anthropic()
    prompt = build_user_prompt(records, project_name)

    print(f"Sending {len(records)} records for '{project_name}' ({len(prompt)} chars)...")
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
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


def submit_batch(projects, model, system_prompt, output_dir):
    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_state = output_dir / "batch_state.json"

    requests = []
    project_index = []
    for pname in sorted(projects):
        recs = projects[pname]
        prompt = build_user_prompt(recs, pname)

        requests.append({
            "custom_id": f"proj_{len(requests):04d}",
            "params": {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
        project_index.append({
            "id": f"proj_{len(project_index):04d}",
            "project_name": pname,
            "n_records": len(recs),
            "record_ids": [r["record_id"] for r in recs],
        })

    with open(output_dir / "project_index.json", "w") as f:
        json.dump(project_index, f, indent=2)

    all_states = []
    for batch_num, start in enumerate(range(0, len(requests), BATCH_SIZE)):
        batch_reqs = requests[start:start + BATCH_SIZE]

        jsonl_path = output_dir / f"batch_{batch_num}.jsonl"
        with open(jsonl_path, "w") as f:
            for req in batch_reqs:
                f.write(json.dumps(req) + "\n")
        print(f"Wrote {len(batch_reqs)} requests to {jsonl_path}")

        batch = client.messages.batches.create(requests=batch_reqs)
        print(f"Batch {batch_num} submitted: {batch.id}")

        all_states.append({
            "batch_id": batch.id,
            "batch_num": batch_num,
            "n_requests": len(batch_reqs),
        })

    with open(batch_state, "w") as f:
        json.dump(all_states, f, indent=2)
    print(f"\nState saved to {batch_state}")


def check_status(output_dir):
    batch_state = output_dir / "batch_state.json"
    if not batch_state.exists():
        raise SystemExit("No batch state found. Run --batch submit first.")
    with open(batch_state) as f:
        states = json.load(f)
    if isinstance(states, dict):
        states = [states]

    client = anthropic.Anthropic()
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        counts = batch.request_counts
        print(f"Batch {state.get('batch_num', '?')}: {state['batch_id']}")
        print(f"  Status: {batch.processing_status}")
        print(f"  Processing: {counts.processing}, Succeeded: {counts.succeeded}, "
              f"Errored: {counts.errored}")


def collect_results(output_dir):
    batch_state = output_dir / "batch_state.json"
    if not batch_state.exists():
        raise SystemExit("No batch state found.")
    with open(batch_state) as f:
        states = json.load(f)
    if isinstance(states, dict):
        states = [states]
    with open(output_dir / "project_index.json") as f:
        project_index = json.load(f)

    client = anthropic.Anthropic()

    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        if batch.processing_status != "ended":
            print(f"Batch {state.get('batch_num', '?')} not done: {batch.processing_status}")
            return

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

        for e in events:
            e["project_name"] = pname

        safe_name = re.sub(r'[^\w\-]', '_', pname)[:80]
        out_path = output_dir / f"{safe_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"EVENT SYNTHESIS RESULTS")
    print(f"{'='*60}")
    print(f"Projects processed:  {len(project_index)}")
    print(f"Total events:        {total_events}")
    if total_records_expected > 0:
        print(f"Record coverage:     {total_records_covered}/{total_records_expected} "
              f"({total_records_covered/total_records_expected*100:.1f}%)")
    print(f"Errors:              {errors}")

    if coverage_issues:
        print(f"\nCoverage issues ({len(coverage_issues)} projects):")
        for pname, missing_count, total_count in sorted(coverage_issues, key=lambda x: -x[1])[:20]:
            print(f"  {missing_count:3d}/{total_count:3d} missing  {pname[:60]}")

    if total_events > 0 and total_records_expected > 0:
        print(f"\nCompression: {total_records_expected} records → {total_events} events "
              f"({total_events/total_records_expected*100:.0f}%)")

    print(f"\nResults saved to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Synthesise project-level events")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--project", type=str, help="Project name pattern to test")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    per_doc_dir, event_type_dir, output_dir = get_dirs(cfg)
    grouping_field = cfg.domain.project_grouping_field
    model = cfg.domain.synthesis_model
    system_prompt = cfg.prompt("event_synthesis")

    if args.batch == "status":
        check_status(output_dir)
        return

    if args.batch == "collect":
        collect_results(output_dir)
        return

    if args.project:
        projects = load_all_data(per_doc_dir, event_type_dir, grouping_field)
        pattern = args.project.lower()
        pname, records = None, []
        for p, recs in projects.items():
            if re.search(r'\b' + re.escape(pattern) + r'\b', p.lower()):
                pname, records = p, recs
                break
        if not records:
            print(f"No records found matching '{args.project}'")
            return

        if args.dry_run:
            prompt = build_user_prompt(records, pname)
            print(f"Project: {pname}")
            print(f"System prompt: {len(system_prompt)} chars")
            print(f"User prompt: {len(prompt)} chars")
            print(f"Records: {len(records)}")
            return

        events = run_single(pname, records, model, system_prompt)
        if events:
            print_events(events)
            input_ids = {r["record_id"] for r in records}
            output_ids = set()
            for e in events:
                for s in e.get("source_records", []):
                    output_ids.add(s["record_id"])
            missing = input_ids - output_ids
            if missing:
                print(f"\nWARNING: {len(missing)} input records not in any event: {missing}")
            print(f"\nCoverage: {len(output_ids)}/{len(input_ids)} records accounted for")
        return

    if args.batch == "submit":
        projects = load_all_data(per_doc_dir, event_type_dir, grouping_field)
        print(f"Loaded {len(projects)} projects with 2+ records "
              f"({sum(len(v) for v in projects.values())} total records)")
        submit_batch(projects, model, system_prompt, output_dir)
        return

    if args.dry_run:
        projects = load_all_data(per_doc_dir, event_type_dir, grouping_field)
        print(f"Loaded {len(projects)} projects with 2+ records")
        print(f"System prompt: {len(system_prompt)} chars")
        print(f"Model: {model}")


if __name__ == "__main__":
    main()
