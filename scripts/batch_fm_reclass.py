#!/usr/bin/env python3
"""
Batch failure mode reclassification: repass records currently tagged
'unvalidated technical assumptions' or 'poor scoping' through Haiku
with only the 6 specific failure modes as options (plus 'none of these').
Also asks for a suggested alternative failure mode on every record.

Usage:
    python scripts/batch_fm_reclass.py --batch submit
    python scripts/batch_fm_reclass.py --batch status
    python scripts/batch_fm_reclass.py --batch collect
    python scripts/batch_fm_reclass.py --analyze
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_fm_reclass"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

BROAD_FMS = {"unvalidated technical assumptions", "poor scoping"}

SPECIFIC_FMS = [
    "commercial & market",
    "coordination & stakeholders",
    "data & measurement",
    "execution & logistics",
    "regulatory & approvals",
    "unvalidated integration",
]

SYSTEM_PROMPT = """You are reclassifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

Each record was previously classified with a broad failure mode. Your job is to determine whether a MORE SPECIFIC failure mode better describes what went wrong.

The 6 specific failure modes are:

1. commercial & market: The issue relates to revenue, demand, pricing, offtake, business case viability, market conditions, or commercial arrangements failing to materialise as expected.

2. coordination & stakeholders: The issue relates to misalignment between parties, communication breakdowns, stakeholder management failures, governance gaps, or organisational coordination problems.

3. data & measurement: The issue relates to inadequate data, measurement errors, monitoring gaps, data quality problems, validation failures, or inability to verify performance claims.

4. execution & logistics: The issue relates to physical delivery problems — construction delays, supply chain disruption, transport/logistics failures, installation errors, manufacturing defects, or workforce availability.

5. regulatory & approvals: The issue relates to regulatory requirements, approval processes, compliance obligations, grid codes, planning permits, standards, or policy changes that created barriers.

6. unvalidated integration: The issue relates to components or systems failing to work together — interface problems, interoperability failures, system integration challenges, or commissioning failures when combining subsystems.

For each record, decide:
- Does ONE of the 6 specific failure modes above clearly describe what went wrong? If so, select it.
- If none of the 6 is a clear fit, select "none".

ALSO: regardless of your choice above, suggest what failure mode label you WOULD use if you could name it freely. This should be a short phrase (2-4 words) that precisely captures the mechanism of failure in this record.

Respond ONLY with a JSON object (no markdown, no explanation):
{"reclassified": "regulatory & approvals", "confidence": 0.85, "suggested_label": "grid code non-compliance"}

If none of the 6 fit:
{"reclassified": "none", "confidence": 0.0, "suggested_label": "technology immaturity"}"""


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
        return {"reclassified": "none", "confidence": 0.0, "suggested_label": "", "_parse_error": text[:200]}


# ── Submit ──���───────────────────────────────────────────────────────────────

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
        # Encode original FM in custom_id for collection
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


# ── Status ──────────��────────────────────────────────────���──────────────────

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


# ── Collect ──────���───────────────────────────────���──────────────────────────

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
            original_fm = "unvalidated technical assumptions" if original_fm_code == "UTA" else "poor scoping"

            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                parsed = parse_response(text, record_id)
                n_succeeded += 1
                if parsed.get("_parse_error"):
                    n_parse_errors += 1
            else:
                error_msg = str(result.result)[:200]
                parsed = {"reclassified": "none", "confidence": 0.0,
                          "suggested_label": "", "_api_error": error_msg}
                n_errors += 1

            entry = {
                "record_id": record_id,
                "original_fm": original_fm,
                "reclassified": parsed.get("reclassified", "none"),
                "confidence": parsed.get("confidence", 0.0),
                "suggested_label": parsed.get("suggested_label", ""),
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


# ─�� Analyze ─────────────────────────────────────────────────────────────────

def run_analyze():
    if not OUTPUT_DIR.exists():
        raise SystemExit(f"No output dir: {OUTPUT_DIR}")

    reclass_counts = Counter()
    reclass_by_original = defaultdict(Counter)
    suggested_labels = Counter()
    suggested_by_original = defaultdict(Counter)
    total = 0
    n_none = 0

    for path in sorted(OUTPUT_DIR.glob("doc_*_fm_reclass.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
        if not results:
            continue
        for r in results:
            total += 1
            original = r.get("original_fm", "?")
            reclass = r.get("reclassified", "none")
            suggested = r.get("suggested_label", "").strip().lower()

            if reclass == "none" or not reclass:
                n_none += 1
                reclass_counts["none"] += 1
            else:
                reclass_counts[reclass] += 1
            reclass_by_original[original][reclass if reclass else "none"] += 1

            if suggested:
                suggested_labels[suggested] += 1
                suggested_by_original[original][suggested] += 1

    print(f"Total records: {total}")
    print(f"Reclassified to 'none' (kept broad): {n_none} ({n_none/total*100:.1f}%)")
    print(f"Reclassified to specific FM: {total - n_none} ({(total-n_none)/total*100:.1f}%)")

    print(f"\nReclassification targets:")
    for fm, count in reclass_counts.most_common():
        print(f"  {fm:40s} {count:6d}  ({count/total*100:.1f}%)")

    for orig in sorted(reclass_by_original.keys()):
        print(f"\nFrom '{orig}':")
        orig_total = sum(reclass_by_original[orig].values())
        for fm, count in reclass_by_original[orig].most_common():
            print(f"  → {fm:40s} {count:6d}  ({count/orig_total*100:.1f}%)")

    print(f"\nTop 30 suggested labels (free-text):")
    for label, count in suggested_labels.most_common(30):
        print(f"  {label:50s} {count:5d}")

    for orig in sorted(suggested_by_original.keys()):
        print(f"\nTop 15 suggested labels from '{orig}':")
        for label, count in suggested_by_original[orig].most_common(15):
            print(f"  {label:50s} {count:5d}")


# ── Main ─────��─────────────────────────────────────���────────────────────────

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
