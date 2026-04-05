#!/usr/bin/env python3
"""
Match orphan records (no kb_associated_project) to canonical ARENA projects.

These are records from documents not associated with any ARENA project in the
KB export, but the model inferred a project_name that might match a canonical
project. Uses Haiku to semantically match.

Usage:
    python scripts/match_orphan_projects.py --scan
    python scripts/match_orphan_projects.py --batch submit
    python scripts/match_orphan_projects.py --batch status
    python scripts/match_orphan_projects.py --batch collect
"""

import argparse
import csv
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
PER_DOC_DIR = ROOT / "insights" / "per_doc"
OUTPUT_DIR = ROOT / "insights" / "orphan_matches"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
PROJECTS_CSV = ROOT / "arena-projects-export_1772932404.csv"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

# Keywords that indicate portfolio/program-level, not a specific project
PORTFOLIO_KEYWORDS = [
    "portfolio", "program", "round", "sector", "cross-project", "multiple",
    "cross-cutting", "cross-trial", "industry", "(general)", "various",
    "funding round", "all projects", "prior rounds",
]

SYSTEM_PROMPT = """You are matching project names to canonical ARENA (Australian Renewable Energy Agency) project names.

You will receive a model-inferred project name from an insight record, plus the full list of canonical ARENA project names.

Determine whether this name matches any canonical ARENA project. The name may be:
1. An abbreviation or alternate name for a canonical project (e.g., "Project Edith" = "Ausgrid Power2U Project")
2. A sub-component of a canonical project
3. An ARENA-commissioned study or program that isn't tracked as a "project"
4. An international project referenced for comparison (not in ARENA portfolio)

Respond ONLY with JSON (no markdown):

If it matches a canonical project:
{"match": "Exact Canonical Project Name", "confidence": 0.9, "match_type": "same_project"}

If it's a sub-project or component of a canonical project:
{"match": "Exact Canonical Project Name", "confidence": 0.8, "match_type": "sub_project"}

If it's an ARENA study/program not in the project list:
{"match": null, "confidence": 0.9, "match_type": "arena_study"}

If it's an external/international reference:
{"match": null, "confidence": 0.9, "match_type": "external"}

If unsure:
{"match": null, "confidence": 0.5, "match_type": "unknown"}"""


def load_canonical_projects():
    projects = set()
    with open(PROJECTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            projects.add(row["Project"].strip())
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                for r in recs:
                    kb = r.get("kb_associated_project")
                    if kb:
                        projects.add(kb)
    return sorted(projects)


def find_orphan_names():
    """Find model-inferred project names from records with no kb_associated_project."""
    orphans = {}  # name -> list of record_ids
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
        if not recs:
            continue
        for r in recs:
            if not r.get("kb_associated_project"):
                pn = r.get("project_name") or ""
                if pn:
                    orphans.setdefault(pn, []).append(r.get("record_id"))

    # Filter to 2+ records and non-portfolio names
    filtered = {}
    for name, rids in orphans.items():
        if len(rids) >= 2:
            if not any(kw in name.lower() for kw in PORTFOLIO_KEYWORDS):
                filtered[name] = rids
    return filtered


def submit_batch(orphans, canonical_projects):
    client = anthropic.Anthropic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    project_list = "\n".join(f"- {p}" for p in canonical_projects)

    requests = []
    name_index = []
    for i, (name, rids) in enumerate(sorted(orphans.items())):
        custom_id = f"orphan_{i:04d}"
        user_prompt = f"""Model-inferred project name: {name}
Number of records with this name: {len(rids)}

Canonical ARENA project names:
{project_list}"""

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        })
        name_index.append({
            "id": custom_id,
            "name": name,
            "record_ids": rids,
        })

    with open(OUTPUT_DIR / "name_index.json", "w") as f:
        json.dump(name_index, f, indent=2)

    jsonl_path = OUTPUT_DIR / "batch_0.jsonl"
    with open(jsonl_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    print(f"Wrote {len(requests)} requests to {jsonl_path}")

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")

    with open(BATCH_STATE, "w") as f:
        json.dump({"batch_id": batch.id, "n_requests": len(requests)}, f, indent=2)


def check_status():
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        state = json.load(f)
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch: {state['batch_id']}")
    print(f"Status: {batch.processing_status}")
    counts = batch.request_counts
    print(f"Processing: {counts.processing}, Succeeded: {counts.succeeded}, Errored: {counts.errored}")


def collect_results():
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        state = json.load(f)
    with open(OUTPUT_DIR / "name_index.json") as f:
        name_index = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        print(f"Batch not done: {batch.processing_status}")
        return

    results = {}
    for result in client.messages.batches.results(state["batch_id"]):
        oid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r'\{.*\}', text, re.DOTALL)
                parsed = json.loads(m.group()) if m else {"match": None, "match_type": "parse_error"}
            results[oid] = parsed
        else:
            results[oid] = {"match": None, "match_type": "api_error"}

    # Analyse
    matched = []
    arena_studies = []
    external = []
    unknown = []

    for entry in name_index:
        r = results.get(entry["id"], {"match": None, "match_type": "missing"})
        entry["result"] = r
        mt = r.get("match_type", "unknown")
        if r.get("match"):
            matched.append(entry)
        elif mt == "arena_study":
            arena_studies.append(entry)
        elif mt == "external":
            external.append(entry)
        else:
            unknown.append(entry)

    # Save
    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(name_index, f, indent=2)

    print(f"\n{'='*60}")
    print(f"ORPHAN PROJECT MATCHING RESULTS")
    print(f"{'='*60}")
    print(f"Total names checked:    {len(name_index)}")
    print(f"Matched to canonical:   {len(matched)} ({sum(len(e['record_ids']) for e in matched)} records)")
    print(f"ARENA study (no match): {len(arena_studies)} ({sum(len(e['record_ids']) for e in arena_studies)} records)")
    print(f"External reference:     {len(external)} ({sum(len(e['record_ids']) for e in external)} records)")
    print(f"Unknown:                {len(unknown)} ({sum(len(e['record_ids']) for e in unknown)} records)")

    if matched:
        print(f"\nMatched projects:")
        for e in sorted(matched, key=lambda x: -len(x["record_ids"])):
            print(f"  {len(e['record_ids']):3d} recs  {e['name'][:45]:45s} → {e['result']['match'][:40]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    args = parser.parse_args()

    if args.scan:
        orphans = find_orphan_names()
        print(f"Orphan names to match: {len(orphans)} ({sum(len(v) for v in orphans.values())} records)")
    elif args.batch == "submit":
        orphans = find_orphan_names()
        canonical = load_canonical_projects()
        print(f"Names to check: {len(orphans)}, Canonical projects: {len(canonical)}")
        submit_batch(orphans, canonical)
    elif args.batch == "status":
        check_status()
    elif args.batch == "collect":
        collect_results()
    else:
        parser.print_help()
