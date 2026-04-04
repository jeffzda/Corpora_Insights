#!/usr/bin/env python3
"""
Full corpus failure mode reclassification v4: retag all 16,931 records with
both primary AND secondary failure modes using the revised 7 failure modes
(+ no major failure stated). Also asks for an ideal two-word label per record
for post-hoc gap analysis.

Saves current v3 primary FMs as a baseline before overwriting.

Usage:
    python scripts/batch_fm_reclass_v4.py --batch submit
    python scripts/batch_fm_reclass_v4.py --batch status
    python scripts/batch_fm_reclass_v4.py --batch collect
    python scripts/batch_fm_reclass_v4.py --analyze
    python scripts/batch_fm_reclass_v4.py --validate
"""

import argparse
import glob
import json
import re
import shutil
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_fm_v3"
BASELINE_DIR = ROOT / "insights" / "per_doc_fm_v3_baseline"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

Each record describes something that happened during an energy project. Your job is to classify the FAILURE MODE — the type of failure observed. If no failure occurred, classify as "no major failure stated".

The 8 failure modes are:

1. no major failure stated: The record describes a success, a neutral observation, or a lesson learnt without an associated failure or adverse event.

2. commercial & market: The failure relates to revenue, demand, pricing, offtake, business case viability, market conditions, or commercial arrangements not materialising as expected.

3. coordination & stakeholders: The failure relates to misalignment between parties, communication breakdowns, stakeholder management failures, governance gaps, or organisational coordination problems.

4. data & measurement: The failure relates to inadequate data, measurement errors, monitoring gaps, data quality problems, validation failures, or inability to verify performance claims.

5. execution & logistics: The failure relates to physical delivery problems — construction delays, supply chain disruption, transport/logistics failures, installation errors, manufacturing defects, or workforce availability.

6. regulatory & approvals: The failure relates to regulatory requirements, approval processes, compliance obligations, grid codes, planning permits, standards, or policy changes that created barriers.

7. technical underperformance: The failure relates to technology, equipment, or systems not achieving expected performance — degradation, efficiency shortfalls, reliability problems, technology immaturity, or performance below design specifications.

8. unvalidated integration: The failure relates to components or systems failing to work together — interface problems, interoperability failures, system integration challenges, or commissioning failures when combining subsystems.

For each record:
- Select the ONE failure mode that best describes the primary failure observed.
- If a clearly distinct secondary failure mode is also present, select it too. The secondary MUST name a different category from the primary. If there is no secondary failure, set it to null.
- Provide the ideal two-word label that you think most precisely captures the primary failure in this specific record, as if you had free rein to name the category (even if it matches one of the 8 above).

Respond ONLY with a JSON object (no markdown, no explanation):
{"failure_mode": "technical underperformance", "secondary_failure_mode": "execution & logistics", "confidence": 0.85, "ideal_label": "efficiency shortfall"}

When no secondary: {"failure_mode": "technical underperformance", "secondary_failure_mode": null, "confidence": 0.85, "ideal_label": "efficiency shortfall"}

If no failure: {"failure_mode": "no major failure stated", "secondary_failure_mode": null, "confidence": 0.95, "ideal_label": "no failure"}"""


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
        return {"failure_mode": "none", "secondary_failure_mode": None,
                "confidence": 0.0, "ideal_label": "",
                "_parse_error": text[:200]}


# ── Baseline ─────────────────────────────────────────────────────────────

def save_baseline():
    """Copy current v3 FM files to baseline directory for comparison."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(OUTPUT_DIR.glob("doc_*_fm_v3.yaml"))
    for src in existing:
        shutil.copy2(src, BASELINE_DIR / src.name)
    print(f"  Saved {len(existing)} baseline files to {BASELINE_DIR}")


# ── Submit ────────────────────────────────────────────────────────────────

def run_batch_submit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Saving baseline...")
    save_baseline()

    client = anthropic.Anthropic()

    print("Loading all records...")
    records = load_all_records()
    print(f"  {len(records)} records loaded")

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
                parsed = {"failure_mode": "none", "secondary_failure_mode": None,
                          "confidence": 0.0, "ideal_label": "",
                          "_api_error": error_msg}
                n_errors += 1

            entry = {
                "record_id": record_id,
                "failure_mode": parsed.get("failure_mode", "none"),
                "secondary_failure_mode": parsed.get("secondary_failure_mode"),
                "confidence": parsed.get("confidence", 0.0),
                "ideal_label": parsed.get("ideal_label", ""),
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
        out_path = OUTPUT_DIR / f"{doc_stem}_fm_v3.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\nResults written to {OUTPUT_DIR}/")
    print(f"  Succeeded: {n_succeeded}  Errors: {n_errors}  Parse errors: {n_parse_errors}")
    print(f"  Files written: {len(doc_results)}")


# ── Analyze ───────────────────────────────────────────────────────────────

def run_analyze():
    if not OUTPUT_DIR.exists():
        raise SystemExit(f"No output dir: {OUTPUT_DIR}")

    fm_counts = Counter()
    sfm_counts = Counter()
    ideal_labels = Counter()
    total = 0
    n_with_secondary = 0

    for path in sorted(OUTPUT_DIR.glob("doc_*_fm_v3.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
        if not results:
            continue
        for r in results:
            total += 1
            fm = r.get("failure_mode", "none")
            fm_counts[fm] += 1

            sfm = r.get("secondary_failure_mode")
            if sfm:
                sfm_counts[sfm] += 1
                n_with_secondary += 1

            il = r.get("ideal_label", "").strip().lower()
            if il:
                ideal_labels[il] += 1

    print(f"Total records: {total}")
    print(f"Records with secondary FM: {n_with_secondary} ({n_with_secondary/total*100:.1f}%)")

    print(f"\nPrimary failure mode distribution:")
    for fm, count in fm_counts.most_common():
        print(f"  {fm:40s} {count:6d}  ({count/total*100:.1f}%)")

    print(f"\nSecondary failure mode distribution:")
    for fm, count in sfm_counts.most_common():
        print(f"  {fm:40s} {count:6d}  ({count/n_with_secondary*100:.1f}% of secondaries)")

    print(f"\nTop 50 ideal labels:")
    for label, count in ideal_labels.most_common(50):
        print(f"  {label:50s} {count:5d}")


# ── Validate ──────────────────────────────────────────────────────────────

def run_validate():
    """Compare new primary FMs against baseline to measure agreement."""
    if not BASELINE_DIR.exists():
        raise SystemExit(f"No baseline dir: {BASELINE_DIR}")

    agree = 0
    disagree = 0
    changes = Counter()

    for path in sorted(OUTPUT_DIR.glob("doc_*_fm_v3.yaml")):
        baseline_path = BASELINE_DIR / path.name
        if not baseline_path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            new_recs = yaml.safe_load(f) or []
        with open(baseline_path, encoding="utf-8") as f:
            old_recs = yaml.safe_load(f) or []

        new_data = {r["record_id"]: r for r in new_recs if isinstance(r, dict)}
        old_data = {r["record_id"]: r for r in old_recs if isinstance(r, dict)}

        for rid, new_r in new_data.items():
            old_r = old_data.get(rid)
            if not old_r:
                continue
            new_fm = new_r.get("failure_mode", "none")
            old_fm = old_r.get("failure_mode", "none")
            if new_fm == old_fm:
                agree += 1
            else:
                disagree += 1
                changes[f"{old_fm} -> {new_fm}"] += 1

    total = agree + disagree
    if total == 0:
        print("No comparable records found.")
        return
    print(f"Agreement: {agree}/{total} ({agree/total*100:.1f}%)")
    print(f"Changed:   {disagree}/{total} ({disagree/total*100:.1f}%)")
    print(f"\nTop 30 changes:")
    for change, count in changes.most_common(30):
        print(f"  {change}: {count}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["submit", "collect", "status"])
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.batch == "submit":
        run_batch_submit()
    elif args.batch == "collect":
        run_batch_collect()
    elif args.batch == "status":
        run_batch_status()
    elif args.analyze:
        run_analyze()
    elif args.validate:
        run_validate()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
