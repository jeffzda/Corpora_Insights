#!/usr/bin/env python3
"""Classify event_type and consequence_level for all delivery insight records.

Config-driven version of scripts/batch_event_type.py.
Uses domain config for model selection and prompt rendering.

Usage:
    python -m pipeline.event_type --domain arena --batch submit
    python -m pipeline.event_type --domain arena --batch status
    python -m pipeline.event_type --domain arena --batch collect
    python -m pipeline.event_type --domain arena --dry-run
    python -m pipeline.event_type --domain arena --stats
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

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
BATCH_SIZE = 10_000
MAX_TOKENS = 200


def get_dirs(cfg):
    """Get input/output directories for this domain."""
    input_dir = ROOT / "runs" / cfg.domain.name.lower() / "per_doc"
    # Fall back to insights/per_doc for ARENA backward compat
    if not input_dir.exists():
        input_dir = ROOT / "insights" / "per_doc"
    output_dir = ROOT / "runs" / cfg.domain.name.lower() / "per_doc_event_type"
    # Fall back to insights/per_doc_event_type for ARENA backward compat
    if not output_dir.exists() and (ROOT / "insights" / "per_doc_event_type").exists():
        output_dir = ROOT / "insights" / "per_doc_event_type"
    return input_dir, output_dir


def load_all_records(input_dir):
    records = []
    for path in sorted(glob.glob(str(input_dir / "doc_*.yaml"))):
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
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"event_type": "parse_error", "consequence_level": None,
                "confidence": 0, "_raw": text[:200]}


def submit_batch(records, cfg, output_dir, batch_num=0):
    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_state = output_dir / "batch_state.json"

    system_prompt = cfg.prompt("event_type")
    model = cfg.domain.classification_model

    requests = []
    for r in records:
        rid = r.get("record_id", "unknown")
        requests.append({
            "custom_id": rid,
            "params": {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "messages": [{"role": "user", "content": build_user_prompt(r)}],
            },
        })

    jsonl_path = output_dir / f"batch_{batch_num}.jsonl"
    with open(jsonl_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    print(f"Wrote {len(requests)} requests to {jsonl_path}")

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")

    if batch_state.exists():
        with open(batch_state) as f:
            all_state = json.load(f)
        if not isinstance(all_state, list):
            all_state = [all_state]
    else:
        all_state = []
    all_state.append({"batch_id": batch.id, "batch_num": batch_num, "n_requests": len(requests)})
    with open(batch_state, "w") as f:
        json.dump(all_state, f, indent=2)
    print(f"State saved to {batch_state}")


def _load_batch_states(output_dir):
    batch_state = output_dir / "batch_state.json"
    if not batch_state.exists():
        raise SystemExit("No batch state found. Run --batch submit first.")
    with open(batch_state) as f:
        state = json.load(f)
    if isinstance(state, dict):
        return [state]
    return state


def check_status(output_dir):
    states = _load_batch_states(output_dir)
    client = anthropic.Anthropic()
    for state in states:
        batch = client.messages.batches.retrieve(state["batch_id"])
        print(f"Batch {state.get('batch_num', '?')}: {state['batch_id']}")
        print(f"  Status: {batch.processing_status}")
        print(f"  Requests: {state['n_requests']}")
        counts = batch.request_counts
        print(f"  Processing: {counts.processing}")
        print(f"  Succeeded: {counts.succeeded}")
        print(f"  Errored: {counts.errored}")
        print()


def collect_results(cfg, input_dir, output_dir):
    states = _load_batch_states(output_dir)
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
            rid = result.custom_id
            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                parsed = parse_response(text, rid)
                results[rid] = parsed
            else:
                errors += 1
                results[rid] = {"event_type": "api_error", "consequence_level": None,
                                "confidence": 0}

    print(f"Collected {len(results)} results from {len(states)} batches ({errors} errors)")

    records = load_all_records(input_dir)
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
            out_path = output_dir / f"{stem}_event_type.yaml"
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(out_records, f, default_flow_style=False, allow_unicode=True,
                          sort_keys=False)
            files_written += 1

    print(f"Wrote {files_written} files to {output_dir}")
    print_stats(cfg, output_dir, results)


def print_stats(cfg, output_dir, results=None):
    event_types = cfg.enums.event_type
    consequence_levels = cfg.enums.consequence_level

    if results is None:
        results = {}
        for path in sorted(glob.glob(str(output_dir / "doc_*_event_type.yaml"))):
            with open(path) as f:
                data = yaml.safe_load(f)
            if data:
                for r in data:
                    results[r["record_id"]] = r

    et_counts = Counter()
    cl_counts = Counter()

    for rid, r in results.items():
        et = r.get("event_type", "unknown")
        cl = r.get("consequence_level")
        et_counts[et] += 1
        if et == "realised_delivery_event" and cl:
            cl_counts[cl] += 1

    total = sum(et_counts.values())
    print(f"\n{'='*60}")
    print(f"EVENT TYPE DISTRIBUTION ({total} records)")
    print(f"{'='*60}")
    for et in event_types + ["parse_error", "api_error"]:
        n = et_counts.get(et, 0)
        if n > 0:
            print(f"  {et:<35s} {n:>6d}  ({n/total*100:.1f}%)")

    if cl_counts:
        n_rde = et_counts.get("realised_delivery_event", 0)
        print(f"\n{'='*60}")
        print(f"CONSEQUENCE LEVEL (of {n_rde} realised delivery events)")
        print(f"{'='*60}")
        for cl in consequence_levels:
            n = cl_counts.get(cl, 0)
            if n > 0:
                print(f"  {cl:<35s} {n:>6d}  ({n/n_rde*100:.1f}%)")

        mat_plus = sum(cl_counts.get(c, 0) for c in ["material_impact", "project_threatening", "project_terminated"])
        threat_plus = sum(cl_counts.get(c, 0) for c in ["project_threatening", "project_terminated"])
        terminated = cl_counts.get("project_terminated", 0)
        print(f"\n  --- Escalation tiers ---")
        print(f"  Material impact+:      {mat_plus:>6d}  ({mat_plus/n_rde*100:.1f}% of realised events)")
        print(f"  Project threatening+:  {threat_plus:>6d}  ({threat_plus/n_rde*100:.1f}% of realised events)")
        print(f"  Project terminated:    {terminated:>6d}  ({terminated/n_rde*100:.1f}% of realised events)")


def main():
    parser = argparse.ArgumentParser(description="Classify event type and consequence level")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    input_dir, output_dir = get_dirs(cfg)

    if args.stats:
        print_stats(cfg, output_dir)
        return

    if args.batch == "status":
        check_status(output_dir)
        return

    if args.batch == "collect":
        collect_results(cfg, input_dir, output_dir)
        return

    records = load_all_records(input_dir)
    print(f"Loaded {len(records)} records")

    if args.dry_run:
        system_prompt = cfg.prompt("event_type")
        for r in records[:5]:
            print(f"\n{'='*80}")
            print(f"Record: {r.get('record_id')}")
            print(f"System prompt: {len(system_prompt)} chars")
            prompt = build_user_prompt(r)
            print(f"User prompt ({len(prompt)} chars):")
            print(prompt)
        est_input = len(records) * 500 / 1e6
        est_output = len(records) * 50 / 1e6
        cost = est_input * 0.80 + est_output * 4.0
        print(f"\nEstimated cost: ~${cost:.2f} ({len(records)} records)")
        return

    if args.batch == "submit":
        for i in range(0, len(records), BATCH_SIZE):
            batch_recs = records[i:i + BATCH_SIZE]
            submit_batch(batch_recs, cfg, output_dir, batch_num=i // BATCH_SIZE)


if __name__ == "__main__":
    main()
