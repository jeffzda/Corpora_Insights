#!/usr/bin/env python3
"""
Batch failure mode reclassification v2: repass records originally tagged
'unvalidated technical assumptions' or 'poor scoping' through Haiku with
7 specific failure modes (including technical underperformance) plus 'none'.
Also asks for suggested additional categories.

Usage:
    python scripts/batch_fm_reclass_v2.py --batch submit
    python scripts/batch_fm_reclass_v2.py --batch status
    python scripts/batch_fm_reclass_v2.py --batch collect
    python scripts/batch_fm_reclass_v2.py --analyze
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_fm_reclass_v2"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400

BROAD_FMS = {"unvalidated technical assumptions", "poor scoping"}

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

Each record describes something that went wrong (or a lesson learnt) during an energy project. Your job is to classify the FAILURE MODE — the type of failure observed.

The 7 failure modes are:

1. commercial & market: The failure relates to revenue, demand, pricing, offtake, business case viability, market conditions, or commercial arrangements not materialising as expected.

2. coordination & stakeholders: The failure relates to misalignment between parties, communication breakdowns, stakeholder management failures, governance gaps, or organisational coordination problems.

3. data & measurement: The failure relates to inadequate data, measurement errors, monitoring gaps, data quality problems, validation failures, or inability to verify performance claims.

4. execution & logistics: The failure relates to physical delivery problems — construction delays, supply chain disruption, transport/logistics failures, installation errors, manufacturing defects, or workforce availability.

5. regulatory & approvals: The failure relates to regulatory requirements, approval processes, compliance obligations, grid codes, planning permits, standards, or policy changes that created barriers.

6. technical underperformance: The failure relates to technology, equipment, or systems not achieving expected performance — degradation, efficiency shortfalls, reliability problems, technology immaturity, or performance below design specifications.

7. unvalidated integration: The failure relates to components or systems failing to work together — interface problems, interoperability failures, system integration challenges, or commissioning failures when combining subsystems.

For each record:
- Select the ONE failure mode that best describes the type of failure observed.
- If none of the 7 is a clear fit, select "none".
- Also tell us: are there any failure mode categories NOT in the list above that would have helped you classify this record more effectively? If so, suggest them as short phrases (2-4 words each).

Respond ONLY with a JSON object (no markdown, no explanation):
{"failure_mode": "technical underperformance", "confidence": 0.85, "missing_categories": ["technology maturity gap"]}

If none of the 7 fit:
{"failure_mode": "none", "confidence": 0.0, "missing_categories": ["suggested category"]}

If the 7 categories were sufficient:
{"failure_mode": "regulatory & approvals", "confidence": 0.90, "missing_categories": []}"""


def load_target_records():
    """Load records with broad failure modes (excl R&D)."""
    records = []
    for path in sorted(glob.glob(str(INPUT_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
        if not recs:
            continue
        for r in recs:
            if r.get("activity_type") == "R&D":
                continue
            fm = r.get("failure_mode", "")
            if fm in BROAD_FMS:
                r["_doc_stem"] = Path(path).stem
                records.append(r)
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
        return {"failure_mode": "none", "confidence": 0.0,
                "missing_categories": [], "_parse_error": text[:200]}


# ── Submit ────────────────────────────────────────────────────────────────

def run_batch_submit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    print("Loading target records (broad failure modes, excl R&D)...")
    records = load_target_records()
    print(f"  {len(records)} records to reclassify")

    print("Building batch requests...")
    requests = []
    for r in records:
        record_id = r.get("record_id", "unknown")
        doc_stem = r.get("_doc_stem", "unknown")
        original_fm = r.get("failure_mode", "unknown")
        fm_code = "UTA" if original_fm == "unvalidated technical assumptions" else "PS"
        custom_id = f"{doc_stem}__{record_id}__{fm_code}"
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


# ── Status ────────────────────────────────────────────────────────────────

def run_batch_status():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}")

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


# ── Collect ───────────────────────────────────────────────────────────────

def run_batch_collect():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}")

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
            parts = custom_id.split("__")
            doc_stem = parts[0] if len(parts) >= 2 else "unknown"
            record_id = parts[1] if len(parts) >= 2 else custom_id
            original_fm_code = parts[2] if len(parts) >= 3 else "?"
            original_fm = ("unvalidated technical assumptions"
                           if original_fm_code == "UTA" else "poor scoping")

            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                parsed = parse_response(text, record_id)
                n_succeeded += 1
                if parsed.get("_parse_error"):
                    n_parse_errors += 1
            else:
                error_msg = str(result.result)[:200]
                parsed = {"failure_mode": "none", "confidence": 0.0,
                          "missing_categories": [], "_api_error": error_msg}
                n_errors += 1

            entry = {
                "record_id": record_id,
                "original_fm": original_fm,
                "failure_mode": parsed.get("failure_mode", "none"),
                "confidence": parsed.get("confidence", 0.0),
                "missing_categories": parsed.get("missing_categories", []),
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
        out_path = OUTPUT_DIR / f"{doc_stem}_fm_reclass.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\nResults written to {OUTPUT_DIR}/")
    print(f"  Succeeded: {n_succeeded}  Errors: {n_errors}  Parse errors: {n_parse_errors}")
    print(f"  Files written: {len(doc_results)}")


# ── Analyze ───────────────────────────────────────────────────────────────

def run_analyze():
    if not OUTPUT_DIR.exists():
        raise SystemExit(f"No output dir: {OUTPUT_DIR}")

    reclass_counts = Counter()
    reclass_by_original = defaultdict(Counter)
    missing_cats = Counter()
    missing_by_original = defaultdict(Counter)
    total = 0
    n_none = 0
    n_no_missing = 0

    for path in sorted(OUTPUT_DIR.glob("doc_*_fm_reclass.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
        if not results:
            continue
        for r in results:
            total += 1
            original = r.get("original_fm", "?")
            fm = r.get("failure_mode", "none")

            if fm == "none" or not fm:
                n_none += 1
                reclass_counts["none"] += 1
            else:
                reclass_counts[fm] += 1
            reclass_by_original[original][fm if fm else "none"] += 1

            cats = r.get("missing_categories", [])
            if not cats:
                n_no_missing += 1
            for c in cats:
                c = c.strip().lower()
                if c:
                    missing_cats[c] += 1
                    missing_by_original[original][c] += 1

    print(f"Total records: {total}")
    print(f"Reclassified to 'none': {n_none} ({n_none/total*100:.1f}%)")
    print(f"Reclassified to specific FM: {total - n_none} ({(total-n_none)/total*100:.1f}%)")
    print(f"Records with no missing categories suggested: {n_no_missing} ({n_no_missing/total*100:.1f}%)")

    print(f"\nReclassification targets:")
    for fm, count in reclass_counts.most_common():
        print(f"  {fm:40s} {count:6d}  ({count/total*100:.1f}%)")

    for orig in sorted(reclass_by_original.keys()):
        print(f"\nFrom '{orig}':")
        orig_total = sum(reclass_by_original[orig].values())
        for fm, count in reclass_by_original[orig].most_common():
            print(f"  -> {fm:40s} {count:6d}  ({count/orig_total*100:.1f}%)")

    print(f"\nTop 40 missing categories (free-text):")
    for label, count in missing_cats.most_common(40):
        print(f"  {label:50s} {count:5d}")

    for orig in sorted(missing_by_original.keys()):
        print(f"\nTop 20 missing categories from '{orig}':")
        for label, count in missing_by_original[orig].most_common(20):
            print(f"  {label:50s} {count:5d}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["submit", "collect", "status"])
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.batch == "submit":
        run_batch_submit()
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
