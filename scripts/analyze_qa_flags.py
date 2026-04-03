#!/usr/bin/env python3
"""Analyze QA classification verdicts to understand patterns in questionable/wrong flags."""

import glob
import re
import yaml
from collections import Counter, defaultdict
from pathlib import Path

QA_DIR = Path("/home/jeffzda/ARENA/insights/per_doc_qa")
PER_DOC_DIR = Path("/home/jeffzda/ARENA/insights/per_doc")

# ── 1. Load all QA verdicts ──────────────────────────────────────────────────

print("=" * 80)
print("LOADING QA VERDICTS")
print("=" * 80)

qa_records = {}  # record_id -> qa dict
parse_errors = 0
total_records = 0

for path in sorted(QA_DIR.glob("doc_*_qa.yaml")):
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        for rec in data:
            rid = rec.get("record_id")
            if rid:
                qa_records[rid] = rec
                total_records += 1
    except Exception as e:
        parse_errors += 1

print(f"Total QA records loaded: {total_records}")
print(f"Parse errors (files): {parse_errors}")

# ── 2. Load per_doc records for cross-referencing ────────────────────────────

print("\nLoading per_doc records for cross-referencing...")
doc_records = {}  # record_id -> record dict

for path in sorted(PER_DOC_DIR.glob("doc_*.yaml")):
    if "_qa" in path.name:
        continue
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        for rec in data:
            rid = rec.get("record_id")
            if rid:
                doc_records[rid] = rec
    except:
        pass

print(f"Per-doc records loaded: {len(doc_records)}")

# ── 3. Filter to questionable and wrong ──────────────────────────────────────

questionable = []
wrong = []

for rid, rec in qa_records.items():
    verdict = rec.get("classification_verdict")
    if verdict == "questionable":
        questionable.append(rec)
    elif verdict == "wrong":
        wrong.append(rec)

# Count all verdicts
verdict_counts = Counter()
for rec in qa_records.values():
    v = rec.get("classification_verdict")
    verdict_counts[v] += 1

print("\n" + "=" * 80)
print("VERDICT DISTRIBUTION")
print("=" * 80)
for v, c in verdict_counts.most_common():
    pct = 100 * c / total_records
    print(f"  {str(v):20s}  {c:6d}  ({pct:.1f}%)")

print(f"\n  Questionable: {len(questionable)}")
print(f"  Wrong:        {len(wrong)}")
print(f"  Total flagged: {len(questionable) + len(wrong)}")

# ── 4. ALL "wrong" classification notes ──────────────────────────────────────

print("\n" + "=" * 80)
print(f"ALL 'WRONG' CLASSIFICATION NOTES ({len(wrong)} records)")
print("=" * 80)

for i, rec in enumerate(wrong, 1):
    rid = rec.get("record_id", "?")
    note = rec.get("classification_note", "(no note)")
    doc_rec = doc_records.get(rid, {})
    project = doc_rec.get("project_name", "?")
    fm = doc_rec.get("failure_mode", "?")
    oc = doc_rec.get("outcome_class", "?")
    sev = doc_rec.get("issue_severity", "?")
    lp = doc_rec.get("lifecycle_phase", "?")
    pt = doc_rec.get("proponent_type", "?")
    arena_cat = doc_rec.get("arena_category", "?")
    print(f"\n--- Wrong #{i}: {rid} ---")
    print(f"  Project:        {project}")
    print(f"  Failure mode:   {fm}")
    print(f"  Outcome class:  {oc}")
    print(f"  Severity:       {sev}")
    print(f"  Lifecycle:      {lp}")
    print(f"  Proponent:      {pt}")
    print(f"  ARENA category: {arena_cat}")
    print(f"  NOTE: {note}")

# ── 5. Thematic analysis of classification notes ─────────────────────────────

print("\n" + "=" * 80)
print("THEMATIC ANALYSIS OF CLASSIFICATION NOTES")
print("=" * 80)

# Define theme patterns (regex, label)
theme_patterns = [
    # Field-specific disagreements
    (r"(?i)\bseverity\b.*\b(too high|too low|overstat|understat|should be|disproportionate|inflated|excessive|mild|minor.*not.*moderate|moderate.*not.*major|major.*not)", "severity_disputed"),
    (r"(?i)\bseverity\b", "severity_mentioned"),
    (r"(?i)\bfailure.?mode\b", "failure_mode_mentioned"),
    (r"(?i)\bdelay.?category\b", "delay_category_mentioned"),
    (r"(?i)\boutcome.?class\b", "outcome_class_mentioned"),
    (r"(?i)\blifecycle.?phase\b", "lifecycle_phase_mentioned"),
    (r"(?i)\bproponent.?type\b", "proponent_type_mentioned"),
    (r"(?i)\bproject.?type\b", "project_type_mentioned"),
    (r"(?i)\bproject.?scale\b", "project_scale_mentioned"),
    (r"(?i)\btransferability\b", "transferability_mentioned"),
    (r"(?i)\btechnology.?domain\b", "technology_domain_mentioned"),
    # Nature of issue
    (r"(?i)\b(not well supported|not supported|no evidence|insufficient evidence|no clear|unclear|not clear|lacks support)\b", "insufficient_evidence"),
    (r"(?i)\b(overstat|inflat|exaggerat|too high|too severe|disproportionate)\b", "overstated"),
    (r"(?i)\b(understat|too low|too mild|downplay|minimis)\b", "understated"),
    (r"(?i)\b(ambiguous|borderline|could be|arguab|debatable|subjective)\b", "ambiguous_borderline"),
    (r"(?i)\b(should be|more appropriate|better classified|more accurately|would be better)\b", "suggests_reclassification"),
    (r"(?i)\b(multiple|several|both|overlap|co-present)\b.*\b(failure|issue|categor|classif)", "multiple_issues_overlap"),
    (r"(?i)\b(mismatch|inconsisten|contradict)\b", "internal_inconsistency"),
    (r"(?i)\bno (material |major )?failure\b.*\bstated\b", "no_failure_but_classified"),
    (r"(?i)\bcommercial\b", "commercial_related"),
    (r"(?i)\bregulat\b", "regulatory_related"),
    (r"(?i)\bgrid\b", "grid_related"),
    (r"(?i)\bdesign assumption\b", "design_assumption_related"),
]

# Count themes across all flagged records
all_flagged = questionable + wrong
theme_counts = Counter()
theme_examples = defaultdict(list)

for rec in all_flagged:
    note = rec.get("classification_note") or ""
    rid = rec.get("record_id", "?")
    verdict = rec.get("classification_verdict", "?")
    matched_themes = set()
    for pattern, label in theme_patterns:
        if re.search(pattern, note):
            matched_themes.add(label)
    for theme in matched_themes:
        theme_counts[theme] += 1
        if len(theme_examples[theme]) < 3:
            theme_examples[theme].append((rid, verdict, note[:200]))

print(f"\nTheme frequency across {len(all_flagged)} flagged records (questionable + wrong):\n")
for theme, count in theme_counts.most_common():
    pct = 100 * count / len(all_flagged)
    print(f"  {theme:35s}  {count:5d}  ({pct:.1f}%)")
    for rid, verdict, note in theme_examples[theme]:
        print(f"    [{verdict}] {rid}: {note}")
    print()

# ── 6. Which FIELDS are most often disputed? ─────────────────────────────────

print("\n" + "=" * 80)
print("WHICH FIELDS ARE MOST DISPUTED?")
print("=" * 80)

field_keywords = {
    "failure_mode": [r"failure.?mode"],
    "delay_category": [r"delay.?category", r"delay classification"],
    "outcome_class": [r"outcome.?class", r"outcome classification"],
    "issue_severity": [r"severity", r"issue.?severity"],
    "lifecycle_phase": [r"lifecycle.?phase", r"lifecycle stage"],
    "proponent_type": [r"proponent.?type"],
    "project_type": [r"project.?type"],
    "project_scale_band": [r"project.?scale", r"scale.?band"],
    "transferability": [r"transferability"],
    "technology_domain": [r"technology.?domain"],
}

field_dispute_counts = Counter()
field_dispute_examples = defaultdict(list)

for rec in all_flagged:
    note = rec.get("classification_note") or ""
    rid = rec.get("record_id", "?")
    for field, patterns in field_keywords.items():
        for p in patterns:
            if re.search(p, note, re.IGNORECASE):
                field_dispute_counts[field] += 1
                if len(field_dispute_examples[field]) < 2:
                    field_dispute_examples[field].append((rid, note[:200]))
                break

print(f"\nField mention frequency in flagged classification notes:\n")
for field, count in field_dispute_counts.most_common():
    pct = 100 * count / len(all_flagged)
    print(f"  {field:25s}  {count:5d}  ({pct:.1f}%)")
    for rid, note in field_dispute_examples[field]:
        print(f"    {rid}: {note}")
    print()

# ── 7. Cross-reference with record fields ────────────────────────────────────

print("\n" + "=" * 80)
print("FLAGGED RECORDS BY ARENA CATEGORY")
print("=" * 80)

cat_counts_flagged = Counter()
cat_counts_total = Counter()

# Total by arena_category
for rid, rec in doc_records.items():
    cats = rec.get("arena_category") or []
    if isinstance(cats, str):
        cats = [cats]
    for c in cats:
        cat_counts_total[c] += 1

for rec in all_flagged:
    rid = rec.get("record_id")
    doc_rec = doc_records.get(rid, {})
    cats = doc_rec.get("arena_category") or []
    if isinstance(cats, str):
        cats = [cats]
    for c in cats:
        cat_counts_flagged[c] += 1

print(f"\n{'ARENA Category':45s}  {'Flagged':>8s}  {'Total':>8s}  {'Rate':>6s}")
print("-" * 75)
for cat in sorted(cat_counts_total.keys(), key=lambda x: cat_counts_flagged.get(x, 0), reverse=True):
    fl = cat_counts_flagged.get(cat, 0)
    tot = cat_counts_total.get(cat, 0)
    rate = 100 * fl / tot if tot else 0
    print(f"  {cat:43s}  {fl:8d}  {tot:8d}  {rate:5.1f}%")

# ── By failure_mode ──────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("FLAGGED RECORDS BY FAILURE MODE")
print("=" * 80)

fm_flagged = Counter()
fm_total = Counter()

for rid, rec in doc_records.items():
    fm = rec.get("failure_mode", "unknown")
    fm_total[fm] += 1

for rec in all_flagged:
    rid = rec.get("record_id")
    doc_rec = doc_records.get(rid, {})
    fm = doc_rec.get("failure_mode", "unknown")
    fm_flagged[fm] += 1

print(f"\n{'Failure Mode':45s}  {'Flagged':>8s}  {'Total':>8s}  {'Rate':>6s}")
print("-" * 75)
for fm in sorted(fm_total.keys(), key=lambda x: fm_flagged.get(x, 0), reverse=True):
    fl = fm_flagged.get(fm, 0)
    tot = fm_total.get(fm, 0)
    rate = 100 * fl / tot if tot else 0
    print(f"  {fm:43s}  {fl:8d}  {tot:8d}  {rate:5.1f}%")

# ── By proponent_type ────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("FLAGGED RECORDS BY PROPONENT TYPE")
print("=" * 80)

pt_flagged = Counter()
pt_total = Counter()

for rid, rec in doc_records.items():
    pt = rec.get("proponent_type", "unknown")
    pt_total[pt] += 1

for rec in all_flagged:
    rid = rec.get("record_id")
    doc_rec = doc_records.get(rid, {})
    pt = doc_rec.get("proponent_type", "unknown")
    pt_flagged[pt] += 1

print(f"\n{'Proponent Type':45s}  {'Flagged':>8s}  {'Total':>8s}  {'Rate':>6s}")
print("-" * 75)
for pt in sorted(pt_total.keys(), key=lambda x: pt_flagged.get(x, 0), reverse=True):
    fl = pt_flagged.get(pt, 0)
    tot = pt_total.get(pt, 0)
    rate = 100 * fl / tot if tot else 0
    print(f"  {pt:43s}  {fl:8d}  {tot:8d}  {rate:5.1f}%")

# ── By outcome_class ─────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("FLAGGED RECORDS BY OUTCOME CLASS")
print("=" * 80)

oc_flagged = Counter()
oc_total = Counter()

for rid, rec in doc_records.items():
    oc = rec.get("outcome_class", "unknown")
    oc_total[oc] += 1

for rec in all_flagged:
    rid = rec.get("record_id")
    doc_rec = doc_records.get(rid, {})
    oc = doc_rec.get("outcome_class", "unknown")
    oc_flagged[oc] += 1

print(f"\n{'Outcome Class':45s}  {'Flagged':>8s}  {'Total':>8s}  {'Rate':>6s}")
print("-" * 75)
for oc in sorted(oc_total.keys(), key=lambda x: oc_flagged.get(x, 0), reverse=True):
    fl = oc_flagged.get(oc, 0)
    tot = oc_total.get(oc, 0)
    rate = 100 * fl / tot if tot else 0
    print(f"  {oc:43s}  {fl:8d}  {tot:8d}  {rate:5.1f}%")

# ── 8. Top patterns in questionable notes (clustered) ────────────────────────

print("\n" + "=" * 80)
print("TOP PATTERNS IN 'QUESTIONABLE' NOTES (manual clustering)")
print("=" * 80)

# Extract the core complaint from each note — normalize and cluster
def extract_complaint_key(note):
    """Simplify note to a cluster key."""
    if not note:
        return "no_note"
    note_lower = note.lower().strip()
    # Try to identify the main field + direction
    # Common pattern: "X is/seems/may be Y" or "X should be Y"
    # Simplify to main complaint type

    # Severity complaints
    if re.search(r"severity.*\b(too high|overstat|inflat|excessive|disproportionate)", note_lower):
        return "severity too high"
    if re.search(r"severity.*\b(too low|understat|minor.*moderate|should be higher)", note_lower):
        return "severity too low"
    if re.search(r"severity", note_lower) and re.search(r"(not well supported|questionable|unclear|debat)", note_lower):
        return "severity questionable"

    # failure_mode complaints
    if re.search(r"failure.?mode.*(not well supported|not supported|no evidence|questionable)", note_lower):
        return "failure_mode not well supported"
    if re.search(r"failure.?mode.*(should be|more accurate|better classified|mislabel)", note_lower):
        return "failure_mode should be different"
    if re.search(r"failure.?mode", note_lower):
        return "failure_mode disputed"

    # delay_category
    if re.search(r"delay.?category.*(not well supported|not supported|no evidence)", note_lower):
        return "delay_category not well supported"
    if re.search(r"delay.?category", note_lower):
        return "delay_category disputed"

    # outcome_class
    if re.search(r"outcome.?class", note_lower):
        return "outcome_class disputed"

    # lifecycle_phase
    if re.search(r"lifecycle.?phase", note_lower):
        return "lifecycle_phase disputed"

    # proponent
    if re.search(r"proponent", note_lower):
        return "proponent_type disputed"

    # project_type
    if re.search(r"project.?type", note_lower):
        return "project_type disputed"

    # General
    if re.search(r"(not well supported|insufficient evidence|no clear evidence)", note_lower):
        return "general: classification not well supported"
    if re.search(r"(overstat|inflat|exaggerat)", note_lower):
        return "general: overstated"
    if re.search(r"(understat|too low|too mild)", note_lower):
        return "general: understated"
    if re.search(r"(ambiguous|borderline|arguab)", note_lower):
        return "general: ambiguous/borderline"

    return "other"

cluster_counts = Counter()
cluster_examples = defaultdict(list)

for rec in questionable:
    note = rec.get("classification_note") or ""
    rid = rec.get("record_id", "?")
    key = extract_complaint_key(note)
    cluster_counts[key] += 1
    if len(cluster_examples[key]) < 3:
        cluster_examples[key].append((rid, note[:250]))

print(f"\nTop complaint clusters across {len(questionable)} 'questionable' records:\n")
for cluster, count in cluster_counts.most_common(15):
    pct = 100 * count / len(questionable)
    print(f"  {cluster:45s}  {count:5d}  ({pct:.1f}%)")
    for rid, note in cluster_examples[cluster]:
        print(f"    {rid}: {note}")
    print()

# ── 9. "wrong" records by complaint cluster ──────────────────────────────────

print("\n" + "=" * 80)
print("'WRONG' RECORDS BY COMPLAINT CLUSTER")
print("=" * 80)

wrong_clusters = Counter()
for rec in wrong:
    note = rec.get("classification_note") or ""
    key = extract_complaint_key(note)
    wrong_clusters[key] += 1

for cluster, count in wrong_clusters.most_common():
    print(f"  {cluster:45s}  {count:5d}")

# ── 10. Severity distribution of flagged vs all ──────────────────────────────

print("\n" + "=" * 80)
print("SEVERITY DISTRIBUTION: FLAGGED vs ALL RECORDS")
print("=" * 80)

sev_flagged = Counter()
sev_total = Counter()

for rid, rec in doc_records.items():
    sev = rec.get("issue_severity", "unknown")
    sev_total[sev] += 1

for rec in all_flagged:
    rid = rec.get("record_id")
    doc_rec = doc_records.get(rid, {})
    sev = doc_rec.get("issue_severity", "unknown")
    sev_flagged[sev] += 1

print(f"\n{'Severity':20s}  {'Flagged':>8s}  {'Flagged%':>9s}  {'Total':>8s}  {'Total%':>8s}  {'Flag Rate':>10s}")
print("-" * 75)
for sev in ["none", "minor", "moderate", "major", "critical", "unknown"]:
    fl = sev_flagged.get(sev, 0)
    tot = sev_total.get(sev, 0)
    fl_pct = 100 * fl / len(all_flagged) if all_flagged else 0
    tot_pct = 100 * tot / len(doc_records) if doc_records else 0
    rate = 100 * fl / tot if tot else 0
    print(f"  {sev:18s}  {fl:8d}  {fl_pct:8.1f}%  {tot:8d}  {tot_pct:7.1f}%  {rate:9.1f}%")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
