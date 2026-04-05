#!/usr/bin/env python3
"""
Identify records where the model's project_name differs from the document's
kb_associated_project, and determine whether they refer to the same project
(name variant) or a genuinely different project (cross-reference).

Uses Haiku batch API to semantically match each unique (kb, pn) pair.

Usage:
    python scripts/reassign_cross_refs.py --scan            # show pairs to check
    python scripts/reassign_cross_refs.py --batch submit     # submit Haiku batch
    python scripts/reassign_cross_refs.py --batch status
    python scripts/reassign_cross_refs.py --batch collect    # collect + apply
"""

import argparse
import csv
import glob
import json
import re
from collections import Counter
from difflib import SequenceMatcher
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
OUTPUT_DIR = ROOT / "insights" / "cross_ref_matches"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
PROJECTS_CSV = ROOT / "arena-projects-export_1772932404.csv"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

SYSTEM_PROMPT = """You are matching project names from ARENA (Australian Renewable Energy Agency) records.

You will receive:
1. kb_name: The canonical project name from ARENA's Knowledge Bank metadata (document-level attribution)
2. model_name: The project name inferred by an LLM from the record's content
3. A list of all canonical ARENA project names

Your job: determine whether kb_name and model_name refer to the SAME project or DIFFERENT projects.

SAME PROJECT means the model just used a different name, abbreviation, or phrasing for the same project.
Examples of SAME:
- "Lake Bonney Battery Energy Storage System" = "Lake Bonney BESS"
- "Consumer Energy Systems Providing Cost-Effective Grid Support" = "CONSORT Bruny Island Battery Trial"
- "Simply Energy Virtual Power Plant (VPP)" = "Simply Energy VPPx"

DIFFERENT PROJECT means the record is actually about a different ARENA project or activity.
Examples of DIFFERENT:
- A record from "Lake Bonney Stages 2/3" about "Vestas Wind Forecasting for the NEM" — different project
- A record from "AGL Solar Project" about "Moree Solar Farm" — different project

If DIFFERENT, identify which canonical project the model_name best matches (if any).

Respond ONLY with JSON (no markdown):
{"verdict": "same", "confidence": 0.95}
or
{"verdict": "different", "canonical_match": "Exact Canonical Project Name", "confidence": 0.9}
or if no canonical match exists:
{"verdict": "different", "canonical_match": null, "confidence": 0.85}"""


def load_canonical_projects():
    """Load all canonical project names."""
    projects = set()
    with open(PROJECTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            projects.add(row["Project"].strip())
    # Also add kb_associated_project values
    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                for r in recs:
                    kb = r.get("kb_associated_project")
                    if kb:
                        projects.add(kb)
    return sorted(projects)


def find_divergent_pairs():
    """Find all (kb, pn) pairs where the names are genuinely different."""
    pairs = {}  # (kb, pn) -> list of record_ids

    for path in sorted(glob.glob(str(PER_DOC_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
        if not recs:
            continue
        for r in recs:
            kb = r.get("kb_associated_project") or ""
            pn = r.get("project_name") or ""
            if not kb or not pn:
                continue
            # Skip obvious same-name variants
            if pn.lower() in kb.lower() or kb.lower() in pn.lower():
                continue
            sim = SequenceMatcher(None, kb.lower(), pn.lower()).ratio()
            if sim > 0.6:
                continue
            key = (kb, pn)
            pairs.setdefault(key, []).append(r.get("record_id"))

    return pairs


def submit_batch(pairs, canonical_projects):
    """Submit Haiku batch to classify pairs."""
    client = anthropic.Anthropic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build compact project list
    project_list = "\n".join(f"- {p}" for p in canonical_projects)

    requests = []
    for i, ((kb, pn), rids) in enumerate(sorted(pairs.items())):
        custom_id = f"pair_{i:04d}"
        user_prompt = f"""kb_name: {kb}
model_name: {pn}
records_affected: {len(rids)}

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

    # Save pair index for later
    pair_index = []
    for i, ((kb, pn), rids) in enumerate(sorted(pairs.items())):
        pair_index.append({
            "pair_id": f"pair_{i:04d}",
            "kb": kb,
            "pn": pn,
            "record_ids": rids,
        })
    with open(OUTPUT_DIR / "pair_index.json", "w") as f:
        json.dump(pair_index, f, indent=2)

    # Write JSONL
    jsonl_path = OUTPUT_DIR / "batch_0.jsonl"
    with open(jsonl_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    print(f"Wrote {len(requests)} requests to {jsonl_path}")

    # Submit
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")

    with open(BATCH_STATE, "w") as f:
        json.dump({"batch_id": batch.id, "n_requests": len(requests)}, f, indent=2)
    print(f"State saved to {BATCH_STATE}")


def check_status():
    """Check batch status."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        state = json.load(f)
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch: {state['batch_id']}")
    print(f"Status: {batch.processing_status}")
    counts = batch.request_counts
    print(f"Processing: {counts.processing}")
    print(f"Succeeded: {counts.succeeded}")
    print(f"Errored: {counts.errored}")


def collect_results():
    """Collect results and report."""
    if not BATCH_STATE.exists():
        raise SystemExit("No batch state found.")
    with open(BATCH_STATE) as f:
        state = json.load(f)
    with open(OUTPUT_DIR / "pair_index.json") as f:
        pair_index = json.load(f)

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        print(f"Batch not done: {batch.processing_status}")
        return

    # Collect
    results = {}
    for result in client.messages.batches.results(state["batch_id"]):
        pid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r'\{.*\}', text, re.DOTALL)
                parsed = json.loads(m.group()) if m else {"verdict": "parse_error"}
            results[pid] = parsed
        else:
            results[pid] = {"verdict": "api_error"}

    # Merge with pair index
    same_count = 0
    same_records = 0
    diff_count = 0
    diff_records = 0
    diff_matched = 0
    diff_unmatched = 0
    errors = 0

    reassignments = []

    for entry in pair_index:
        pid = entry["pair_id"]
        r = results.get(pid, {"verdict": "missing"})
        verdict = r.get("verdict", "unknown")
        n_recs = len(entry["record_ids"])

        if verdict == "same":
            same_count += 1
            same_records += n_recs
        elif verdict == "different":
            diff_count += 1
            diff_records += n_recs
            canonical = r.get("canonical_match")
            if canonical:
                diff_matched += 1
                reassignments.append({
                    "kb": entry["kb"],
                    "pn": entry["pn"],
                    "canonical_match": canonical,
                    "record_ids": entry["record_ids"],
                    "confidence": r.get("confidence", 0),
                })
            else:
                diff_unmatched += 1
        else:
            errors += 1

    # Save results
    out = {
        "summary": {
            "total_pairs": len(pair_index),
            "same_project": same_count,
            "same_project_records": same_records,
            "different_project": diff_count,
            "different_project_records": diff_records,
            "different_matched": diff_matched,
            "different_unmatched": diff_unmatched,
            "errors": errors,
        },
        "reassignments": reassignments,
    }
    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n{'='*60}")
    print(f"CROSS-REFERENCE ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"Total pairs checked:        {len(pair_index)}")
    print(f"Same project (name variant): {same_count} pairs ({same_records} records)")
    print(f"Different project:           {diff_count} pairs ({diff_records} records)")
    print(f"  → matched to canonical:    {diff_matched}")
    print(f"  → no canonical match:      {diff_unmatched}")
    print(f"Errors:                      {errors}")

    if reassignments:
        print(f"\nReassignments to apply ({len(reassignments)} pairs, "
              f"{sum(len(r['record_ids']) for r in reassignments)} records):")
        for r in reassignments[:20]:
            print(f"  {len(r['record_ids']):3d} recs  "
                  f"FROM {r['kb'][:40]:40s} → {r['canonical_match'][:40]}")

    print(f"\nResults saved to {OUTPUT_DIR / 'results.json'}")


def main():
    parser = argparse.ArgumentParser(description="Cross-reference reassignment")
    parser.add_argument("--scan", action="store_true", help="Show pairs to check")
    parser.add_argument("--batch", choices=["submit", "status", "collect"])
    args = parser.parse_args()

    if args.scan:
        pairs = find_divergent_pairs()
        print(f"Divergent (kb, pn) pairs: {len(pairs)}")
        print(f"Total records affected: {sum(len(v) for v in pairs.values())}")
        print(f"\nTop 20 pairs:")
        for (kb, pn), rids in sorted(pairs.items(), key=lambda x: -len(x[1]))[:20]:
            print(f"  {len(rids):3d}  kb={kb[:45]:45s}  pn={pn[:40]}")
        return

    if args.batch == "submit":
        pairs = find_divergent_pairs()
        canonical = load_canonical_projects()
        print(f"Pairs to check: {len(pairs)}")
        print(f"Canonical projects: {len(canonical)}")
        submit_batch(pairs, canonical)
        return

    if args.batch == "status":
        check_status()
        return

    if args.batch == "collect":
        collect_results()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
