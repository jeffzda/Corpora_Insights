#!/usr/bin/env python3
"""
Batch challenge tagging: submit all 16,931 records to Anthropic Batch API for
technical challenge classification.

Usage:
    python scripts/batch_challenge_tagging.py --batch submit          # submit all
    python scripts/batch_challenge_tagging.py --batch submit --skip-done  # skip already-tagged
    python scripts/batch_challenge_tagging.py --batch collect         # retrieve results
    python scripts/batch_challenge_tagging.py --batch status          # check batch status
    python scripts/batch_challenge_tagging.py --analyze               # analyze collected results
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
OUTPUT_DIR = ROOT / "insights" / "per_doc_challenges"
BATCH_STATE = OUTPUT_DIR / "batch_state.json"
BATCH_SIZE = 10_000  # Anthropic batch API limit per request
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

For each record, determine which TECHNICAL CHALLENGES the record addresses, and for each challenge present, whether the record describes a FAILURE, SUCCESS, or NEUTRAL observation with respect to that challenge.

The 6 technical challenges are framed as questions about what the project was attempting:

1. GRID_CONNECTION: Was the project connecting to, or interacting with, the electricity network? (grid connection process, system strength, curtailment, MLF risk, dispatch, FCAS, power quality, voltage/frequency management, network interoperability)

2. SCALING_TO_FIELD: Was the project taking something that worked at a smaller scale and deploying it at a larger one? (lab to pilot, pilot to commercial, first-of-kind deployment, TRL progression, scaling manufacturing, field validation of lab results)

3. SOFTWARE_CONTROLS: Did the project depend on software, control systems, or digital platforms that were unproven or immature? (SCADA, control algorithms, forecasting systems, energy management platforms, data platforms, APIs, digital twins, optimisation engines)

4. SUPPLY_CHAIN: Did the project depend on specialised equipment, long lead-time items, or thin supplier markets? (procurement of custom equipment, sole-source components, EPC contractor capability, import dependencies, manufacturing/fabrication)

5. REGULATORY_ENVIRONMENT: Was the project operating in a regulatory, standards, or market design environment that wasn't ready for what it was doing? (missing frameworks, unclear compliance pathways, rule changes mid-project, no precedent, market design gaps)

6. SITE_CONTEXT: Was the project deploying in a physically, environmentally, or socially challenging context? (extreme climate, remote location, wildlife/heritage constraints, community opposition, land access, noise, logistics access, unfamiliar operating environment)

IMPORTANT DISTINCTIONS:
- A challenge is present when the record DESCRIBES the project confronting that challenge — not merely mentioning it in passing.
- FAILURE means the challenge caused or contributed to a problem, delay, cost, or underperformance.
- SUCCESS means the challenge was present but the project navigated it well — the record describes overcoming or managing the difficulty.
- NEUTRAL means the challenge is present in the record but the record is neither describing a failure nor a clear success — it's an observation, finding, or design choice related to the challenge.
- If a challenge is NOT relevant to this record, do not include it.

Respond ONLY with a JSON object in this exact format (no markdown, no explanation):
{"challenges": [{"id": "GRID_CONNECTION", "confidence": 0.85, "outcome": "failure"}, {"id": "SCALING_TO_FIELD", "confidence": 0.70, "outcome": "success"}]}

If no challenges are present, respond with: {"challenges": []}
Confidence should be 0.0 to 1.0 indicating how confident you are that this challenge is genuinely being addressed in the record (not just mentioned)."""


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
    """Parse the JSON response from Haiku."""
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
        return {"challenges": [], "_parse_error": text[:200]}


def load_done_ids():
    """Load record IDs that already have challenge tags."""
    done = set()
    if not OUTPUT_DIR.exists():
        return done
    for path in sorted(OUTPUT_DIR.glob("doc_*_challenges.yaml")):
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
        # Truncate custom_id to 64 chars (API limit)
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

    # Submit in chunks
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
    print(f"Run with --batch collect when processing is complete (usually <1 hour).")


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
                parsed = {"challenges": [], "_api_error": error_msg}
                n_errors += 1

            entry = {
                "record_id": record_id,
                "challenges": parsed.get("challenges", []),
            }
            if parsed.get("_parse_error"):
                entry["_parse_error"] = parsed["_parse_error"]
            if parsed.get("_api_error"):
                entry["_api_error"] = parsed["_api_error"]

            doc_results[doc_stem].append(entry)

    # Write per-doc challenge files
    for doc_stem, results in sorted(doc_results.items()):
        out_path = OUTPUT_DIR / f"{doc_stem}_challenges.yaml"
        results.sort(key=lambda r: r.get("record_id", ""))
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(results, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\nCollected: {n_succeeded} succeeded, {n_errors} API errors, {n_parse_errors} parse errors")
    print(f"Written to {OUTPUT_DIR}/  ({len(doc_results)} doc files)")


# ── Analyze ─────────────────────────────────────────────────────────────────

def run_analyze():
    """Load challenge tags and original records, run correlation analysis."""
    print("Loading challenge tags...")
    challenge_data = {}  # record_id -> list of challenge dicts
    for path in sorted(OUTPUT_DIR.glob("doc_*_challenges.yaml")):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
            if results:
                for r in results:
                    challenge_data[r["record_id"]] = r.get("challenges", [])

    print(f"  {len(challenge_data)} records with challenge tags")

    print("Loading original records...")
    records = load_all_records()
    print(f"  {len(records)} records loaded")

    # Merge
    merged = []
    for r in records:
        rid = r.get("record_id")
        if rid and rid in challenge_data:
            r["_challenges"] = challenge_data[rid]
            merged.append(r)

    print(f"  {len(merged)} merged records")

    CHALLENGE_IDS = [
        "GRID_CONNECTION", "SCALING_TO_FIELD", "SOFTWARE_CONTROLS",
        "SUPPLY_CHAIN", "REGULATORY_ENVIRONMENT", "SITE_CONTEXT",
    ]
    CHALLENGE_SHORT = {
        "GRID_CONNECTION": "Grid",
        "SCALING_TO_FIELD": "Scale-up",
        "SOFTWARE_CONTROLS": "Software",
        "SUPPLY_CHAIN": "Supply chain",
        "REGULATORY_ENVIRONMENT": "Regulatory",
        "SITE_CONTEXT": "Site/env",
    }
    _NO_FAIL = "no major failure stated"
    _SEV_SEVERE = {"major", "critical"}
    _SEV_MILD = {"minor", "moderate"}
    CONF_THRESHOLD = 0.80

    # Index: challenge_id -> list of record dicts with outcome/confidence
    challenge_records = defaultdict(list)
    for r in merged:
        for ch in r["_challenges"]:
            if ch.get("confidence", 0) >= CONF_THRESHOLD:
                challenge_records[ch["id"]].append({
                    "record_id": r["record_id"],
                    "outcome": ch.get("outcome", ""),
                    "confidence": ch.get("confidence", 0),
                    "failure_mode": r.get("failure_mode"),
                    "severity": r.get("issue_severity"),
                })

    # Count records with no challenge above threshold
    n_no_ch = sum(1 for r in merged if not any(
        ch.get("confidence", 0) >= CONF_THRESHOLD for ch in r["_challenges"]
    ))

    print(f"\n{'='*80}")
    print(f"CHALLENGE TAGGING ANALYSIS — {len(merged)} records (conf >= {CONF_THRESHOLD})")
    print(f"{'='*80}\n")

    # 1. Prevalence
    print("1. CHALLENGE PREVALENCE & OUTCOME DISTRIBUTION")
    print("-" * 90)
    print(f"{'Challenge':<15} {'Total':>6} {'Failure':>10} {'Success':>10} {'Neutral':>10} {'Avg conf':>9}")
    print("-" * 90)

    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        n = len(recs)
        if n == 0:
            continue
        n_f = sum(1 for r in recs if r["outcome"] == "failure")
        n_s = sum(1 for r in recs if r["outcome"] == "success")
        n_n = sum(1 for r in recs if r["outcome"] == "neutral")
        avg_c = sum(r["confidence"] for r in recs) / n
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {n:>6} {n_f:>6} ({n_f/n*100:4.0f}%) "
              f"{n_s:>6} ({n_s/n*100:4.0f}%) {n_n:>6} ({n_n/n*100:4.0f}%) {avg_c:>8.2f}")

    print(f"\n{'No challenge':<15} {n_no_ch:>6} ({n_no_ch/len(merged)*100:.1f}%)")

    # Overlap
    ch_counts = Counter()
    for r in merged:
        n_above = sum(1 for ch in r["_challenges"] if ch.get("confidence", 0) >= CONF_THRESHOLD)
        ch_counts[n_above] += 1
    print(f"\n0 challenges: {ch_counts.get(0,0)} ({ch_counts.get(0,0)/len(merged)*100:.1f}%)")
    print(f"1 challenge:  {ch_counts.get(1,0)} ({ch_counts.get(1,0)/len(merged)*100:.1f}%)")
    print(f"2 challenges: {ch_counts.get(2,0)} ({ch_counts.get(2,0)/len(merged)*100:.1f}%)")
    print(f"3+ challenges: {sum(v for k,v in ch_counts.items() if k>=3)} "
          f"({sum(v for k,v in ch_counts.items() if k>=3)/len(merged)*100:.1f}%)")

    # 2. Challenge × Failure Mode
    print(f"\n\n2. CHALLENGE × FAILURE MODE (failure-outcome records, conf >= {CONF_THRESHOLD})")
    print("-" * 120)

    fm_list = sorted({r.get("failure_mode") for r in merged
                      if r.get("failure_mode") and r["failure_mode"] != _NO_FAIL})
    all_adverse = [r for r in merged if r.get("failure_mode") and r["failure_mode"] != _NO_FAIL]
    baseline_fm = Counter(r["failure_mode"] for r in all_adverse)
    baseline_total = len(all_adverse)

    fm_short = {
        "design assumption failure": "design",
        "technical underperformance": "tech",
        "commercial/demand failure": "commercial",
        "governance/coordination failure": "governance",
        "regulatory misfit": "reg misfit",
        "schedule slippage": "schedule",
        "resource/capability shortfall": "resource",
        "data quality/measurement failure": "data",
        "integration failure": "integr",
        "cost overrun": "cost",
    }

    header = f"{'Challenge':<15} {'n':>5}"
    for fm in fm_list:
        header += f" {fm_short.get(fm, fm[:8]):>9}"
    print(header)
    print("-" * len(header))

    row = f"{'BASELINE':<15} {baseline_total:>5}"
    for fm in fm_list:
        pct = baseline_fm[fm] / baseline_total * 100 if baseline_total else 0
        row += f" {pct:>8.1f}%"
    print(row)
    print()

    for cid in CHALLENGE_IDS:
        recs = [r for r in challenge_records.get(cid, []) if r["outcome"] == "failure"]
        fm_counts = Counter(r["failure_mode"] for r in recs
                           if r["failure_mode"] and r["failure_mode"] != _NO_FAIL)
        fm_total = sum(fm_counts.values())
        if fm_total < 5:
            continue
        row = f"{CHALLENGE_SHORT.get(cid, cid):<15} {fm_total:>5}"
        for fm in fm_list:
            pct = fm_counts[fm] / fm_total * 100 if fm_total else 0
            row += f" {pct:>8.1f}%"
        print(row)

    # 3. Severity ratio
    print(f"\n\n3. SEVERITY ESCALATION RATIO BY CHALLENGE")
    print("-" * 80)
    print(f"{'Challenge':<15} {'Severe':>7} {'Mild':>7} {'Ratio':>7}  {'vs baseline'}")
    print("-" * 80)

    all_sev = sum(1 for r in merged if r.get("issue_severity") in _SEV_SEVERE)
    all_mild = sum(1 for r in merged if r.get("issue_severity") in _SEV_MILD)
    baseline_ratio = all_sev / all_mild if all_mild else 0
    print(f"{'BASELINE':<15} {all_sev:>7} {all_mild:>7} {baseline_ratio:>7.2f}")

    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        sev = sum(1 for r in recs if r["severity"] in _SEV_SEVERE)
        mild = sum(1 for r in recs if r["severity"] in _SEV_MILD)
        ratio = sev / mild if mild else 0
        delta = ratio - baseline_ratio
        sign = "+" if delta >= 0 else ""
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {sev:>7} {mild:>7} {ratio:>7.2f}  {sign}{delta:.2f}")

    # 4. Severity by outcome
    print(f"\n\n4. SEVERITY RATIO BY CHALLENGE × OUTCOME")
    print("-" * 80)
    print(f"{'Challenge':<15} {'Fail ratio':>11} {'Success ratio':>14} {'Neutral ratio':>14}")
    print("-" * 80)
    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        ratios = {}
        for outcome in ["failure", "success", "neutral"]:
            subset = [r for r in recs if r["outcome"] == outcome]
            sev = sum(1 for r in subset if r["severity"] in _SEV_SEVERE)
            mild = sum(1 for r in subset if r["severity"] in _SEV_MILD)
            ratios[outcome] = f"{sev/mild:.2f}" if mild > 0 else "—"
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {ratios['failure']:>11} {ratios['success']:>14} {ratios['neutral']:>14}")

    # 5. Success rate
    print(f"\n\n5. SUCCESS RATE BY CHALLENGE (records navigating challenge without failure)")
    print("-" * 60)
    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        n = len(recs)
        if n == 0:
            continue
        n_s = sum(1 for r in recs if r["outcome"] == "success")
        print(f"  {CHALLENGE_SHORT.get(cid, cid):<15} {n_s:>5}/{n:>5} ({n_s/n*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["submit", "collect", "status"], default=None)
    parser.add_argument("--skip-done", action="store_true",
                        help="Skip records that already have challenge tags")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        run_analyze()
    elif args.batch == "submit":
        run_batch_submit(skip_done=args.skip_done)
    elif args.batch == "collect":
        run_batch_collect()
    elif args.batch == "status":
        run_batch_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
