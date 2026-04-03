#!/usr/bin/env python3
"""Analyze failure narratives from ARENA delivery records — for taxonomy redesign research."""

import glob
import random
import yaml
from collections import Counter, defaultdict

# ── Load all per_doc YAML files ──────────────────────────────────────────────
print("Loading per_doc YAML files...")
per_doc_files = sorted(glob.glob("/home/jeffzda/ARENA/insights/per_doc/doc_*.yaml"))
print(f"  Found {len(per_doc_files)} per_doc files")

all_records = []
for fpath in per_doc_files:
    with open(fpath) as f:
        docs = yaml.safe_load(f)
    if docs:
        for rec in docs:
            all_records.append(rec)

print(f"  Loaded {len(all_records)} total records")

# ── Filter to records WITH a failure mode ────────────────────────────────────
failure_records = [
    r for r in all_records
    if r.get("failure_mode") and r["failure_mode"] != "no major failure stated"
]
print(f"  Records with a failure mode: {len(failure_records)} ({100*len(failure_records)/len(all_records):.1f}%)\n")

# ── Load QA data ─────────────────────────────────────────────────────────────
print("Loading QA data...")
qa_files = sorted(glob.glob("/home/jeffzda/ARENA/insights/per_doc_qa/doc_*_qa.yaml"))
qa_by_id = {}
for fpath in qa_files:
    with open(fpath) as f:
        docs = yaml.safe_load(f)
    if docs:
        for rec in docs:
            rid = rec.get("record_id")
            if rid:
                qa_by_id[rid] = rec
print(f"  Loaded QA verdicts for {len(qa_by_id)} records\n")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Stratified sample of what_happened narratives
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 100)
print("SECTION 3: STRATIFIED SAMPLE OF FAILURE NARRATIVES (15 per failure_mode)")
print("=" * 100)

by_fm = defaultdict(list)
for r in failure_records:
    by_fm[r["failure_mode"]].append(r)

rng = random.Random(42)

for fm in sorted(by_fm.keys()):
    pool = by_fm[fm]
    sample = rng.sample(pool, min(15, len(pool)))
    print(f"\n{'─' * 100}")
    print(f"  FAILURE MODE: {fm}  ({len(pool)} records total)")
    print(f"{'─' * 100}")
    for i, r in enumerate(sample, 1):
        rid = r.get("record_id", "?")
        sev = r.get("issue_severity", "?")
        sfm = r.get("secondary_failure_mode", "—")
        wh = r.get("what_happened", "")
        ll = r.get("lesson_learnt", "")
        print(f"\n  [{i}] {rid}  severity={sev}  secondary={sfm}")
        print(f"      WHAT: {wh}")
        print(f"      LESSON: {ll}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4a: Co-occurrence of (failure_mode, secondary_failure_mode) — top 20
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 100)
print("SECTION 4a: TOP 20 CO-OCCURRING (failure_mode, secondary_failure_mode) PAIRS")
print("=" * 100)

pair_counter = Counter()
for r in failure_records:
    sfm = r.get("secondary_failure_mode")
    if sfm and sfm != "no major failure stated":
        pair_counter[(r["failure_mode"], sfm)] += 1

for (fm, sfm), count in pair_counter.most_common(20):
    print(f"  {count:5d}  {fm}  +  {sfm}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4b: For each failure_mode, % with secondary + most common secondary
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 100)
print("SECTION 4b: SECONDARY FAILURE MODE PREVALENCE BY PRIMARY FAILURE MODE")
print("=" * 100)

for fm in sorted(by_fm.keys()):
    pool = by_fm[fm]
    has_secondary = [
        r for r in pool
        if r.get("secondary_failure_mode") and r["secondary_failure_mode"] != "no major failure stated"
    ]
    pct = 100 * len(has_secondary) / len(pool) if pool else 0

    sec_counter = Counter()
    for r in has_secondary:
        sec_counter[r["secondary_failure_mode"]] += 1

    top_sec = sec_counter.most_common(3)
    top_str = "; ".join(f"{s} ({c})" for s, c in top_sec) if top_sec else "—"

    print(f"\n  {fm}")
    print(f"    Total: {len(pool)}   With secondary: {len(has_secondary)} ({pct:.1f}%)")
    print(f"    Top secondaries: {top_str}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4c: Overall distribution of secondary_failure_mode values
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 100)
print("SECTION 4c: OVERALL DISTRIBUTION OF secondary_failure_mode")
print("=" * 100)

sfm_counter = Counter()
no_secondary = 0
for r in failure_records:
    sfm = r.get("secondary_failure_mode")
    if sfm and sfm != "no major failure stated":
        sfm_counter[sfm] += 1
    else:
        no_secondary += 1

print(f"\n  Records with NO secondary failure mode: {no_secondary} ({100*no_secondary/len(failure_records):.1f}%)")
print(f"  Records WITH secondary failure mode:    {sum(sfm_counter.values())} ({100*sum(sfm_counter.values())/len(failure_records):.1f}%)\n")

for sfm, count in sfm_counter.most_common():
    print(f"  {count:5d}  ({100*count/len(failure_records):5.1f}%)  {sfm}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: QA "questionable" records where classification_note mentions failure_mode
# ══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 100)
print("SECTION 5: QA 'QUESTIONABLE' CLASSIFICATION RECORDS MENTIONING FAILURE_MODE (30 random)")
print("=" * 100)

# Build lookup of what_happened by record_id
wh_by_id = {r["record_id"]: r for r in all_records}

questionable = []
for rid, qa in qa_by_id.items():
    verdict = qa.get("classification_verdict", "")
    note = qa.get("classification_note") or ""
    if verdict == "questionable" and "failure" in note.lower():
        rec = wh_by_id.get(rid, {})
        questionable.append({
            "record_id": rid,
            "failure_mode": rec.get("failure_mode", "?"),
            "secondary_failure_mode": rec.get("secondary_failure_mode", "—"),
            "classification_note": note,
            "what_happened": rec.get("what_happened", "?"),
        })

print(f"\n  Found {len(questionable)} questionable records mentioning 'failure' in classification_note\n")

sample_q = rng.sample(questionable, min(30, len(questionable)))
for i, q in enumerate(sample_q, 1):
    print(f"  [{i}] {q['record_id']}  failure_mode={q['failure_mode']}  secondary={q['secondary_failure_mode']}")
    print(f"      QA NOTE: {q['classification_note']}")
    print(f"      WHAT: {q['what_happened']}")
    print()

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)
