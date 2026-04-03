#!/usr/bin/env python3
"""
Test LLM pass: tag technical challenges on a stratified sample of insight records.
For each record, identifies which challenges are present and whether the record
describes a failure, success, or neutral observation with respect to each challenge.

Usage:
    python scripts/test_challenge_tagging.py                # run full sample
    python scripts/test_challenge_tagging.py --dry-run      # show sample, no API calls
    python scripts/test_challenge_tagging.py --analyze      # analyze saved results only
"""

import argparse
import glob
import json
import random
import sys
import time
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
OUTPUT_FILE = ROOT / "insights" / "challenge_tagging_test.json"

SAMPLE_SIZE = 500
RANDOM_SEED = 42

SYSTEM_PROMPT = """You are classifying delivery insight records from ARENA (Australian Renewable Energy Agency) projects.

For each record, you must determine which TECHNICAL CHALLENGES the record addresses, and for each challenge present, whether the record describes a FAILURE, SUCCESS, or NEUTRAL observation with respect to that challenge.

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
{
  "challenges": [
    {"id": "GRID_CONNECTION", "confidence": 0.85, "outcome": "failure"},
    {"id": "SCALING_TO_FIELD", "confidence": 0.70, "outcome": "success"}
  ]
}

If no challenges are present, respond with: {"challenges": []}
Confidence should be 0.0 to 1.0 indicating how confident you are that this challenge is genuinely being addressed in the record (not just mentioned).
"""


def load_all_records():
    records = []
    for path in sorted(glob.glob(str(INPUT_DIR / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                records.extend(recs)
    return records


def build_stratified_sample(records, n=SAMPLE_SIZE, seed=RANDOM_SEED):
    """Stratified sample: proportional by failure_mode, ensuring all modes represented."""
    random.seed(seed)
    by_fm = defaultdict(list)
    for r in records:
        fm = r.get("failure_mode") or "no major failure stated"
        by_fm[fm].append(r)

    sample = []
    total = len(records)
    for fm, recs in by_fm.items():
        k = max(5, round(len(recs) / total * n))
        k = min(k, len(recs))
        sample.extend(random.sample(recs, k))

    # Trim or pad to target
    random.shuffle(sample)
    if len(sample) > n:
        sample = sample[:n]
    return sample


def build_user_prompt(record):
    wh = record.get("what_happened") or ""
    ll = record.get("lesson_learnt") or ""
    ee = record.get("evidence_excerpt") or ""
    sev = record.get("issue_severity") or "unknown"
    fm = record.get("failure_mode") or "unknown"

    return f"""Record ID: {record.get('record_id', 'unknown')}

WHAT HAPPENED:
{wh}

LESSON LEARNT:
{ll}

EVIDENCE EXCERPT:
{ee}

(For context only — do NOT use these to determine challenges, only the narrative above:
issue_severity: {sev}, failure_mode: {fm})"""


def call_api(client, record, retries=3):
    user_prompt = build_user_prompt(record)
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text.strip()
            # Parse JSON
            result = json.loads(text)
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return {"challenges": [], "parse_error": text[:200]}
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            print(f"  API error: {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return {"challenges": [], "api_error": str(e)[:200]}
    return {"challenges": [], "error": "max retries"}


def run_tagging(sample, dry_run=False):
    if dry_run:
        print(f"Sample size: {len(sample)}")
        fm_dist = Counter(r.get("failure_mode", "?") for r in sample)
        for fm, n in fm_dist.most_common():
            print(f"  {fm}: {n}")
        print("\nExample prompt:")
        print(build_user_prompt(sample[0]))
        return []

    client = anthropic.Anthropic()
    results = []

    # Load existing results for resume
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        done_ids = {r["record_id"] for r in existing}
        results = existing
        print(f"Resuming: {len(done_ids)} already done")
    else:
        done_ids = set()

    pending = [r for r in sample if r.get("record_id") not in done_ids]
    print(f"Processing {len(pending)} records ({len(done_ids)} already done)...")

    for i, record in enumerate(pending):
        rid = record.get("record_id", "?")
        result = call_api(client, record)
        results.append({
            "record_id": rid,
            "failure_mode": record.get("failure_mode"),
            "issue_severity": record.get("issue_severity"),
            "what_happened": record.get("what_happened"),
            "challenges": result.get("challenges", []),
            "parse_error": result.get("parse_error"),
        })

        n_challenges = len(result.get("challenges", []))
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1}/{len(pending)}] {rid}: {n_challenges} challenges")

        # Save periodically
        if (i + 1) % 50 == 0:
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

    # Final save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} results to {OUTPUT_FILE}")
    return results


def analyze_results(results=None):
    if results is None:
        if not OUTPUT_FILE.exists():
            print("No results file found. Run tagging first.")
            return
        with open(OUTPUT_FILE) as f:
            results = json.load(f)

    print(f"\n{'='*80}")
    print(f"CHALLENGE TAGGING ANALYSIS — {len(results)} records")
    print(f"{'='*80}\n")

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
    _SEV_SEVERE = {"major", "critical"}
    _SEV_MILD = {"minor", "moderate"}
    _NO_FAIL = "no major failure stated"

    # Build lookup: record_id -> challenges
    tagged = {}
    for r in results:
        challenges = r.get("challenges") or []
        tagged[r["record_id"]] = {
            "failure_mode": r.get("failure_mode"),
            "severity": r.get("issue_severity"),
            "challenges": challenges,
        }

    # ── 1. Challenge prevalence and outcome distribution ──
    print("1. CHALLENGE PREVALENCE & OUTCOME DISTRIBUTION")
    print("-" * 80)
    print(f"{'Challenge':<15} {'Total':>6} {'Failure':>8} {'Success':>8} {'Neutral':>8} {'Avg conf':>9}")
    print("-" * 80)

    challenge_records = defaultdict(list)  # challenge_id -> list of (record_id, outcome, confidence)

    for rid, data in tagged.items():
        for ch in data["challenges"]:
            cid = ch.get("id", "")
            outcome = ch.get("outcome", "")
            conf = ch.get("confidence", 0)
            challenge_records[cid].append({
                "record_id": rid,
                "outcome": outcome,
                "confidence": conf,
                "failure_mode": data["failure_mode"],
                "severity": data["severity"],
            })

    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        n = len(recs)
        n_fail = sum(1 for r in recs if r["outcome"] == "failure")
        n_succ = sum(1 for r in recs if r["outcome"] == "success")
        n_neut = sum(1 for r in recs if r["outcome"] == "neutral")
        avg_conf = sum(r["confidence"] for r in recs) / n if n else 0
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {n:>6} {n_fail:>7} ({n_fail/n*100:4.0f}%) "
              f"{n_succ:>4} ({n_succ/n*100:4.0f}%) {n_neut:>4} ({n_neut/n*100:4.0f}%) {avg_conf:>8.2f}")

    # No challenges
    no_ch = sum(1 for data in tagged.values() if not data["challenges"])
    print(f"\n{'No challenge':<15} {no_ch:>6} ({no_ch/len(tagged)*100:.1f}% of all records)")

    # Multi-challenge overlap
    ch_counts = Counter(len(data["challenges"]) for data in tagged.values())
    print(f"\nRecords matching 0 challenges: {ch_counts.get(0,0)} ({ch_counts.get(0,0)/len(tagged)*100:.1f}%)")
    print(f"Records matching 1 challenge:  {ch_counts.get(1,0)} ({ch_counts.get(1,0)/len(tagged)*100:.1f}%)")
    print(f"Records matching 2 challenges: {ch_counts.get(2,0)} ({ch_counts.get(2,0)/len(tagged)*100:.1f}%)")
    print(f"Records matching 3+ challenges: {sum(v for k,v in ch_counts.items() if k>=3)} "
          f"({sum(v for k,v in ch_counts.items() if k>=3)/len(tagged)*100:.1f}%)")

    # ── 2. Challenge × Failure Mode distribution ──
    print(f"\n\n2. CHALLENGE × FAILURE MODE (among challenge-failure records)")
    print("-" * 80)

    fm_list = sorted({data["failure_mode"] for data in tagged.values() if data["failure_mode"] and data["failure_mode"] != _NO_FAIL})

    # Baseline
    all_adverse = [data for data in tagged.values() if data["failure_mode"] and data["failure_mode"] != _NO_FAIL]
    baseline_fm = Counter(d["failure_mode"] for d in all_adverse)
    baseline_total = len(all_adverse)

    # Header
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

    # Baseline row
    row = f"{'BASELINE':<15} {baseline_total:>5}"
    for fm in fm_list:
        pct = baseline_fm[fm] / baseline_total * 100 if baseline_total else 0
        row += f" {pct:>8.1f}%"
    print(row)
    print()

    # Per challenge (failure outcomes only)
    for cid in CHALLENGE_IDS:
        recs = [r for r in challenge_records.get(cid, []) if r["outcome"] == "failure"]
        n = len(recs)
        if n < 5:
            continue
        fm_counts = Counter(r["failure_mode"] for r in recs if r["failure_mode"] and r["failure_mode"] != _NO_FAIL)
        fm_total = sum(fm_counts.values())
        row = f"{CHALLENGE_SHORT.get(cid, cid):<15} {fm_total:>5}"
        for fm in fm_list:
            pct = fm_counts[fm] / fm_total * 100 if fm_total else 0
            row += f" {pct:>8.1f}%"
        print(row)

    # ── 3. Severity ratio by challenge ──
    print(f"\n\n3. SEVERITY ESCALATION RATIO BY CHALLENGE")
    print("-" * 80)
    print(f"{'Challenge':<15} {'Severe':>7} {'Mild':>7} {'Ratio':>7}  {'vs baseline 0.26'}")
    print("-" * 80)

    # Baseline
    all_severe = sum(1 for d in tagged.values() if d["severity"] in _SEV_SEVERE)
    all_mild = sum(1 for d in tagged.values() if d["severity"] in _SEV_MILD)
    baseline_ratio = all_severe / all_mild if all_mild else 0
    print(f"{'BASELINE':<15} {all_severe:>7} {all_mild:>7} {baseline_ratio:>7.2f}")

    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        severe = sum(1 for r in recs if r["severity"] in _SEV_SEVERE)
        mild = sum(1 for r in recs if r["severity"] in _SEV_MILD)
        ratio = severe / mild if mild else 0
        delta = ratio - baseline_ratio
        sign = "+" if delta >= 0 else ""
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {severe:>7} {mild:>7} {ratio:>7.2f}  {sign}{delta:.2f}")

    # By outcome
    print(f"\n\n4. SEVERITY RATIO BY CHALLENGE × OUTCOME")
    print("-" * 80)
    print(f"{'Challenge':<15} {'Failure ratio':>14} {'Success ratio':>14} {'Neutral ratio':>14}")
    print("-" * 80)
    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        ratios = {}
        for outcome in ["failure", "success", "neutral"]:
            subset = [r for r in recs if r["outcome"] == outcome]
            sev = sum(1 for r in subset if r["severity"] in _SEV_SEVERE)
            mild = sum(1 for r in subset if r["severity"] in _SEV_MILD)
            ratios[outcome] = f"{sev/mild:.2f}" if mild > 0 else "—"
        print(f"{CHALLENGE_SHORT.get(cid, cid):<15} {ratios['failure']:>14} {ratios['success']:>14} {ratios['neutral']:>14}")

    # ── 5. High-confidence challenge-outcome examples ──
    print(f"\n\n5. HIGH-CONFIDENCE EXAMPLES (confidence >= 0.85)")
    print("-" * 80)
    for cid in CHALLENGE_IDS:
        recs = challenge_records.get(cid, [])
        high_conf = [r for r in recs if r["confidence"] >= 0.85]
        for outcome in ["success", "failure"]:
            examples = [r for r in high_conf if r["outcome"] == outcome][:2]
            for ex in examples:
                # Find the what_happened
                orig = next((rr for rr in results if rr["record_id"] == ex["record_id"]), None)
                wh = (orig.get("what_happened", "") if orig else "")[:150]
                print(f"  {CHALLENGE_SHORT.get(cid, cid):<12} {outcome:<8} conf={ex['confidence']:.2f}  "
                      f"sev={ex['severity']:<9} fm={ex['failure_mode']}")
                print(f"    {wh}...")
                print()

    # ── 6. Confidence distribution ──
    print(f"\n6. CONFIDENCE DISTRIBUTION")
    print("-" * 80)
    all_confs = [ch["confidence"] for data in tagged.values() for ch in data["challenges"]]
    if all_confs:
        buckets = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]
        for lo, hi in buckets:
            n = sum(1 for c in all_confs if lo <= c < hi)
            print(f"  {lo:.1f}-{hi:.1f}: {n:>5} ({n/len(all_confs)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args()

    if args.analyze:
        analyze_results()
        return

    print("Loading records...")
    records = load_all_records()
    print(f"Loaded {len(records)} records")

    sample = build_stratified_sample(records, n=args.sample_size)
    print(f"Stratified sample: {len(sample)} records")

    if args.dry_run:
        run_tagging(sample, dry_run=True)
        return

    results = run_tagging(sample)
    if results:
        analyze_results(results)


if __name__ == "__main__":
    main()
