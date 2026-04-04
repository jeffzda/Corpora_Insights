#!/usr/bin/env python3
"""
Batch delivery dimension tagging: submit records to Anthropic Batch API for
delivery dimension classification.

Delivery dimensions are the physical/organisational things a proponent must
provide or organise as part of the project. Failure modes cut across them.

Usage:
    python scripts/batch_delivery_dimensions.py --batch submit
    python scripts/batch_delivery_dimensions.py --batch submit --skip-done
    python scripts/batch_delivery_dimensions.py --batch collect
    python scripts/batch_delivery_dimensions.py --batch status
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_dimensions"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

For each record, determine which DELIVERY DIMENSIONS the record relates to. A delivery dimension is a physical or organisational aspect of the project that the proponent must provide or organise. Failure modes (what goes wrong) cut across delivery dimensions — your job is to identify which dimension(s) the insight is about.

The 10 delivery dimensions are:

1. DESIGN: Engineering design, modelling, specifications, technical due diligence, feasibility assessment. The record describes design decisions, design errors, design validation, or design methodology.

2. PROCUREMENT: Sourcing equipment, materials, contractors, or services. The record describes purchasing, supplier selection, lead times, equipment specification, vendor management, import logistics, or EPC contractor engagement.

3. CONSTRUCTION: Physical building, installation, civil works, manufacturing, assembly. The record describes on-site construction activities, installation challenges, fabrication, or physical build quality.

4. SOFTWARE_CONTROLS: Software systems, control algorithms, SCADA, firmware, energy management platforms, data platforms, monitoring systems, digital twins, optimisation engines, APIs, cybersecurity. The record describes software development, integration, performance, or digital system operation.

5. GRID_CONNECTION: Connecting to or interacting with the electricity network. The record describes the grid connection process, network approvals, system strength, power quality, inverter compliance, frequency/voltage management, curtailment, MLF, dispatch, or FCAS.

6. INTEGRATION_COMMISSIONING: Getting separate systems to work together and bringing the asset into operation. The record describes system integration, commissioning testing, performance verification, interoperability between components, or handover to operations.

7. SITING: Site selection, site conditions, land access, environmental constraints, weather/climate, geotechnical conditions, logistics access to site, noise, visual amenity. The record describes site-specific physical or environmental factors.

8. COMMUNITY_ENGAGEMENT: Stakeholder engagement, community consultation, social licence, First Nations engagement, landowner negotiations, public communication. The record describes the social interface of the project.

9. FINANCING: Securing project finance, debt/equity, PPAs, offtake agreements, insurance, grant acquittal, commercial close, business case development, revenue model validation. The record describes the financial/commercial structuring of the project.

10. OPERATIONS: Running the asset post-commissioning. Performance monitoring, maintenance, degradation management, operational optimisation, asset management, workforce for ongoing operations. The record describes operational experience.

IMPORTANT:
- Tag the delivery dimension(s) that the record is ABOUT — the aspect of the project being described.
- A record can relate to multiple dimensions (e.g., a procurement delay affecting construction).
- Only include dimensions that the record substantively addresses, not ones mentioned in passing.
- If a record is purely about policy, market analysis, or knowledge sharing methodology with no delivery dimension, return an empty list.

Respond ONLY with a JSON object (no markdown, no explanation):
{"dimensions": [{"id": "CONSTRUCTION", "confidence": 0.85}, {"id": "PROCUREMENT", "confidence": 0.70}]}

If no delivery dimensions are present: {"dimensions": []}
Confidence: 0.0-1.0 indicating how clearly this record relates to that dimension."""


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
    return f"""Record ID: {record.get('record_id', 'unknown')}

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
        return {"dimensions": [], "_parse_error": text[:200]}


def load_done_ids():
    done = set()
    if not OUTPUT_DIR.exists():
        return done
    for path in sorted(OUTPUT_DIR.glob("doc_*_dimensions.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
            if results:
                for r in results:
                    if r.get("record_id"):
                        done.add(r["record_id"])
    return done


# ── Submit ──────────────────────────────────────────────────────────────────

def run_batch_submit(skip_done=False):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    print("Loading records...")
    records = load_all_records()
    print(f"  {len(records)} records loaded")

    if skip_done:
        done_ids = load_done_ids()
        records = [r for r in records if r.get("record_id") not in done_ids]
        print(f"  {len(done_ids)} already tagged, {len(records)} remaining")

    print("Building batch requests...")
    requests = []
    for r in records:
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
    print(f"Run with --batch collect when processing is complete.")


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

def run_batch_collect():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    doc_results: dict = defaultdict(list)
    n_succeeded = 0
    n_errors = 0
    n_parse_errors = 0

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
            else:
                error_msg = str(result.result)[:200]
                parsed = {"dimensions": [], "_api_error": error_msg}
                n_errors += 1

            entry = {
                "record_id": record_id,
                "dimensions": parsed.get("dimensions", []),
            }
            if parsed.get("_parse_error"):
                entry["_parse_error"] = parsed["_parse_error"]
            if parsed.get("_api_error"):
                entry["_api_error"] = parsed["_api_error"]

            doc_results[doc_stem].append(entry)

    # Write per-doc YAML files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for doc_stem, entries in sorted(doc_results.items()):
        entries.sort(key=lambda e: e.get("record_id", ""))
        out_path = OUTPUT_DIR / f"{doc_stem}_dimensions.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\nResults written to {OUTPUT_DIR}/")
    print(f"  Succeeded: {n_succeeded}  Errors: {n_errors}  Parse errors: {n_parse_errors}")
    print(f"  Files written: {len(doc_results)}")


# ── Analyze ─────────────────────────────────────────────────────────────────

def run_analyze():
    if not OUTPUT_DIR.exists():
        raise SystemExit(f"No output dir: {OUTPUT_DIR}")

    dim_counts = Counter()
    n_dims_per_record = Counter()
    total = 0
    n_empty = 0

    for path in sorted(OUTPUT_DIR.glob("doc_*_dimensions.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
        if not results:
            continue
        for r in results:
            total += 1
            dims = r.get("dimensions", [])
            n_dims_per_record[len(dims)] += 1
            if not dims:
                n_empty += 1
            for d in dims:
                dim_counts[d["id"]] += 1

    print(f"Total records: {total}")
    print(f"Records with no dimension: {n_empty} ({n_empty/total*100:.1f}%)")
    print(f"\nDimension frequency:")
    for dim, count in dim_counts.most_common():
        print(f"  {dim:30s} {count:6d}  ({count/total*100:.1f}%)")
    print(f"\nDimensions per record:")
    for n, count in sorted(n_dims_per_record.items()):
        print(f"  {n} dimensions: {count:6d}  ({count/total*100:.1f}%)")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["submit", "collect", "status"])
    parser.add_argument("--skip-done", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.batch == "submit":
        run_batch_submit(skip_done=args.skip_done)
    elif args.batch == "collect":
        run_batch_collect()
    elif args.batch == "status":
        run_batch_status()
    elif args.analyze:
        run_analyze()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
