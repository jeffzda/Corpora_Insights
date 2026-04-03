#!/usr/bin/env python3
"""
Analyze correlation between technical challenge tags (keyword-based) and failure modes
in the ARENA delivery insight registry. Proof-of-concept for challenge classification.
"""

import glob
import re
import yaml
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# 1. Define challenges and their keyword patterns
# ---------------------------------------------------------------------------

CHALLENGES = {
    "Connecting to the grid": [
        r"\bgrid\b", r"\bnetwork connect", r"\bMLF\b", r"\bmarginal loss",
        r"\bcurtail", r"\bdispatch\b", r"\bFCAS\b", r"\bsystem strength\b",
        r"\bharmonic", r"\binverter compliance\b",
        r"\bconnection agreement\b", r"\bconnection process\b",
        r"\bconnection point\b", r"\bconnection approval\b",
        r"\bNER\b", r"\bGPS\b", r"\bgenerator performance standard",
        r"\bFIA\b", r"\bpower quality\b", r"\bvoltage\b", r"\bfrequency\b",
        r"\bislanding\b", r"\bAEMO\b", r"\bDNSP\b", r"\bTNSP\b",
        r"\bpoint of connection\b", r"\bexport limit",
    ],
    "Scaling from lab/pilot to field": [
        r"\bscale\b", r"\bTRL\b", r"\bpilot to\b", r"\blab to field\b",
        r"\bfirst deployment\b", r"\bfirst.of.kind\b", r"\bFOAK\b",
        r"\bprototype\b", r"\bdemonstration to commercial\b",
        r"\bscale.up\b", r"\bcommerialis", r"\bfield trial\b",
        r"\breal.world conditions\b", r"\boperational environment\b",
    ],
    "Building/integrating software/control systems": [
        r"\bsoftware\b", r"\bfirmware\b", r"\bplatform\b", r"\balgorithm\b",
        r"\bSCADA\b", r"\bcontrol system\b", r"\bcontroller\b", r"\bAPI\b",
        r"\binteroperab", r"\bdata format\b", r"\bdata model\b",
        r"\bdata standard\b", r"\bdata exchange\b", r"\bcyber\b",
        r"\bdigital twin\b", r"\boptimisation algorithm\b",
        r"\bdispatch engine\b", r"\bforecast", r"\bmachine learning\b",
    ],
    "Sourcing/assembling physical components": [
        r"\bsupply chain\b", r"\bprocurement\b", r"\blead time\b",
        r"\bshipping\b", r"\bsupplier\b", r"\bmanufacturer\b", r"\bOEM\b",
        r"\bcomponent shortage\b", r"\bimport\b", r"\bequipment\b",
        r"\bEPC\b", r"\bcontractor\b", r"\bfabricat", r"\bcustom.built\b",
        r"\bsole source\b",
    ],
    "Operating in uncertain regulatory environment": [
        r"\bregulat", r"\bcompliance\b", r"\bstandard\b", r"\brule change\b",
        r"\bNER\b", r"\bAEMC\b", r"\bframework\b", r"\bpolicy barrier\b",
        r"\bpolicy gap\b", r"\blegislat", r"\bpermit\b",
        r"\bapproval process\b", r"\bcode\b", r"\bexemption\b",
        r"\bderogation\b", r"\bguideline\b", r"\bno precedent\b",
        r"\bnew market\b", r"\bmarket rule\b", r"\bmarket design\b",
    ],
    "Deploying in difficult/unfamiliar site context": [
        r"\bsite specific\b", r"\bsite.specific\b", r"\bsite condition",
        r"\bsite access\b", r"\bweather\b", r"\btemperature\b", r"\bheat\b",
        r"\bflood\b", r"\bcyclone\b", r"\bgeotechnical\b", r"\bterrain\b",
        r"\bwildlife\b", r"\benvironmental condition",
        r"\bremote\b", r"\blogistics\b", r"\btransport route\b",
        r"\bcommunity\b", r"\bsocial licence\b", r"\bland access\b",
        r"\blandholder\b", r"\btraditional owner\b", r"\bcouncil\b",
        r"\bresident\b", r"\bnoise\b", r"\bdust\b", r"\bvisual amenity\b",
        r"\bheritage\b",
    ],
}

# Pre-compile patterns per challenge
COMPILED = {}
for name, patterns in CHALLENGES.items():
    COMPILED[name] = [re.compile(p, re.IGNORECASE) for p in patterns]

CHALLENGE_NAMES = list(CHALLENGES.keys())
SHORT_NAMES = [
    "Grid connect",
    "Scale-up",
    "Software/ctrl",
    "Supply chain",
    "Regulatory",
    "Site/environ",
]

# All known failure modes (excluding "no major failure stated")
FAILURE_MODES = [
    "technical underperformance",
    "integration failure",
    "schedule slippage",
    "cost overrun",
    "resource/capability shortfall",
    "commercial/demand failure",
    "regulatory misfit",
    "data quality/measurement failure",
    "design assumption failure",
    "governance/coordination failure",
]

FM_SHORT = [
    "Tech underp",
    "Integration",
    "Sched slip",
    "Cost overrun",
    "Resource gap",
    "Commercial",
    "Reg misfit",
    "Data/measure",
    "Design assum",
    "Governance",
]

# ---------------------------------------------------------------------------
# 2. Load records
# ---------------------------------------------------------------------------

def load_all_records():
    records = []
    paths = sorted(glob.glob("/home/jeffzda/ARENA/insights/per_doc/doc_*.yaml"))
    for p in paths:
        with open(p) as f:
            docs = yaml.safe_load(f)
        if isinstance(docs, list):
            records.extend(docs)
        elif isinstance(docs, dict):
            records.append(docs)
    return records


def get_text(rec):
    parts = []
    for field in ("what_happened", "lesson_learnt", "evidence_excerpt"):
        v = rec.get(field)
        if v:
            parts.append(str(v))
    return " ".join(parts)


def match_challenges(text):
    matched = []
    for name in CHALLENGE_NAMES:
        for pat in COMPILED[name]:
            if pat.search(text):
                matched.append(name)
                break
    return matched


# ---------------------------------------------------------------------------
# 3. Main analysis
# ---------------------------------------------------------------------------

def main():
    print("Loading records...")
    records = load_all_records()
    print(f"Loaded {len(records):,} records\n")

    # Tag each record
    for rec in records:
        text = get_text(rec)
        rec["_challenges"] = match_challenges(text)
        fm = rec.get("failure_mode") or "no major failure stated"
        rec["_fm"] = fm
        rec["_has_failure"] = fm != "no major failure stated"
        sev = rec.get("issue_severity") or "none"
        rec["_sev"] = sev

    # -----------------------------------------------------------------------
    # 3a. Challenge prevalence
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("3a. CHALLENGE PREVALENCE")
    print("=" * 90)
    print(f"{'Challenge':<45} {'Total':>7} {'w/ failure':>10} {'no failure':>10} {'% of corpus':>12}")
    print("-" * 90)
    for i, name in enumerate(CHALLENGE_NAMES):
        matched = [r for r in records if name in r["_challenges"]]
        w_fail = sum(1 for r in matched if r["_has_failure"])
        no_fail = sum(1 for r in matched if not r["_has_failure"])
        pct = 100 * len(matched) / len(records)
        print(f"{SHORT_NAMES[i]:<45} {len(matched):>7,} {w_fail:>10,} {no_fail:>10,} {pct:>11.1f}%")
    total_adverse = sum(1 for r in records if r["_has_failure"])
    total_success = sum(1 for r in records if not r["_has_failure"])
    print("-" * 90)
    print(f"{'CORPUS TOTAL':<45} {len(records):>7,} {total_adverse:>10,} {total_success:>10,} {'100.0%':>12}")
    print()

    # -----------------------------------------------------------------------
    # 3b. Challenge x Failure Mode distribution (THE KEY TABLE)
    # -----------------------------------------------------------------------
    print("=" * 120)
    print("3b. CHALLENGE x FAILURE MODE DISTRIBUTION (% of adverse records matching each challenge)")
    print("=" * 120)

    # Header
    hdr = f"{'Challenge':<18}"
    for fm_s in FM_SHORT:
        hdr += f" {fm_s:>12}"
    hdr += f" {'N (adverse)':>12}"
    print(hdr)
    print("-" * 120)

    # Baseline row
    baseline_counts = Counter(r["_fm"] for r in records if r["_has_failure"])
    baseline_total = sum(baseline_counts.values())
    row = f"{'BASELINE':<18}"
    for fm in FAILURE_MODES:
        pct = 100 * baseline_counts.get(fm, 0) / baseline_total if baseline_total else 0
        row += f" {pct:>11.1f}%"
    row += f" {baseline_total:>12,}"
    print(row)
    print("-" * 120)

    # Per challenge
    for i, name in enumerate(CHALLENGE_NAMES):
        adverse = [r for r in records if name in r["_challenges"] and r["_has_failure"]]
        fm_counts = Counter(r["_fm"] for r in adverse)
        n = len(adverse)
        row = f"{SHORT_NAMES[i]:<18}"
        for fm in FAILURE_MODES:
            pct = 100 * fm_counts.get(fm, 0) / n if n else 0
            row += f" {pct:>11.1f}%"
        row += f" {n:>12,}"
        print(row)
    print()

    # Also show delta from baseline
    print("DELTA FROM BASELINE (percentage points):")
    print("-" * 120)
    hdr2 = f"{'Challenge':<18}"
    for fm_s in FM_SHORT:
        hdr2 += f" {fm_s:>12}"
    print(hdr2)
    print("-" * 120)
    for i, name in enumerate(CHALLENGE_NAMES):
        adverse = [r for r in records if name in r["_challenges"] and r["_has_failure"]]
        fm_counts = Counter(r["_fm"] for r in adverse)
        n = len(adverse)
        row = f"{SHORT_NAMES[i]:<18}"
        for fm in FAILURE_MODES:
            pct = 100 * fm_counts.get(fm, 0) / n if n else 0
            base_pct = 100 * baseline_counts.get(fm, 0) / baseline_total if baseline_total else 0
            delta = pct - base_pct
            sign = "+" if delta >= 0 else ""
            row += f" {sign}{delta:>10.1f}%"
        print(row)
    print()

    # -----------------------------------------------------------------------
    # 3c. Severity escalation ratio by challenge
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("3c. SEVERITY ESCALATION RATIO BY CHALLENGE  (major+critical)/(minor+moderate)")
    print("=" * 90)

    def sev_ratio(recs):
        hi = sum(1 for r in recs if r["_sev"] in ("major", "critical"))
        lo = sum(1 for r in recs if r["_sev"] in ("minor", "moderate"))
        return (hi / lo if lo > 0 else float("inf")), hi, lo

    corpus_ratio, corpus_hi, corpus_lo = sev_ratio(records)
    print(f"{'Challenge':<45} {'Ratio':>8} {'Maj+Crit':>10} {'Min+Mod':>10}")
    print("-" * 90)
    print(f"{'CORPUS BASELINE':<45} {corpus_ratio:>8.2f} {corpus_hi:>10,} {corpus_lo:>10,}")
    print("-" * 90)
    for i, name in enumerate(CHALLENGE_NAMES):
        matched = [r for r in records if name in r["_challenges"]]
        ratio, hi, lo = sev_ratio(matched)
        ratio_str = f"{ratio:.2f}" if ratio != float("inf") else "inf"
        print(f"{SHORT_NAMES[i]:<45} {ratio_str:>8} {hi:>10,} {lo:>10,}")
    print()

    # -----------------------------------------------------------------------
    # 3d. Challenge x Failure Mode severity ratio (top combos)
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("3d. CHALLENGE x FAILURE MODE SEVERITY RATIO (top 10 combos by count)")
    print("=" * 90)

    combo_records = defaultdict(list)
    for r in records:
        if r["_has_failure"]:
            for ch in r["_challenges"]:
                combo_records[(ch, r["_fm"])].append(r)

    # Sort by count, take top 10
    top_combos = sorted(combo_records.items(), key=lambda x: -len(x[1]))[:10]

    print(f"{'Challenge':<25} {'Failure Mode':<30} {'N':>6} {'Sev Ratio':>10} {'Maj+Crit':>10} {'Min+Mod':>10}")
    print("-" * 95)
    for (ch, fm), recs in top_combos:
        ch_short = SHORT_NAMES[CHALLENGE_NAMES.index(ch)]
        ratio, hi, lo = sev_ratio(recs)
        ratio_str = f"{ratio:.2f}" if ratio != float("inf") else "inf"
        print(f"{ch_short:<25} {fm:<30} {len(recs):>6,} {ratio_str:>10} {hi:>10,} {lo:>10,}")

    # Also show baseline severity ratio per failure mode for comparison
    print()
    print("BASELINE severity ratio per failure mode (for comparison):")
    print(f"{'Failure Mode':<35} {'N':>6} {'Sev Ratio':>10} {'Maj+Crit':>10} {'Min+Mod':>10}")
    print("-" * 75)
    for fm in FAILURE_MODES:
        fm_recs = [r for r in records if r["_fm"] == fm]
        ratio, hi, lo = sev_ratio(fm_recs)
        ratio_str = f"{ratio:.2f}" if ratio != float("inf") else "inf"
        print(f"{fm:<35} {len(fm_recs):>6,} {ratio_str:>10} {hi:>10,} {lo:>10,}")
    print()

    # -----------------------------------------------------------------------
    # 3e. Multi-challenge overlap
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("3e. MULTI-CHALLENGE OVERLAP")
    print("=" * 90)
    n_challenges = Counter(len(r["_challenges"]) for r in records)
    print(f"{'# challenges matched':<25} {'Records':>10} {'%':>10}")
    print("-" * 50)
    for k in sorted(n_challenges.keys()):
        label = f"{k}" if k < 4 else f"{k}+"
        if k >= 4:
            # Merge 4+ into 3+
            continue
        pct = 100 * n_challenges[k] / len(records)
        print(f"{k:<25} {n_challenges[k]:>10,} {pct:>9.1f}%")
    # 3+ bucket
    three_plus = sum(v for k, v in n_challenges.items() if k >= 3)
    pct_3p = 100 * three_plus / len(records)
    print(f"{'3+':<25} {three_plus:>10,} {pct_3p:>9.1f}%")
    print()

    # Pairwise co-occurrence
    print("Pairwise co-occurrence (records matching BOTH challenges):")
    print(f"{'':>18}", end="")
    for s in SHORT_NAMES:
        print(f" {s[:11]:>11}", end="")
    print()
    print("-" * (18 + 12 * len(SHORT_NAMES)))
    for i, name_i in enumerate(CHALLENGE_NAMES):
        row = f"{SHORT_NAMES[i]:<18}"
        for j, name_j in enumerate(CHALLENGE_NAMES):
            if j <= i:
                overlap = sum(1 for r in records if name_i in r["_challenges"] and name_j in r["_challenges"])
                row += f" {overlap:>11,}"
            else:
                row += f" {'':>11}"
        print(row)
    print()

    # -----------------------------------------------------------------------
    # 3f. Success rate by challenge
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("3f. SUCCESS RATE BY CHALLENGE (% with 'no major failure stated')")
    print("=" * 90)
    corpus_success_rate = 100 * total_success / len(records)
    print(f"{'Challenge':<45} {'Total':>8} {'Success':>8} {'Success %':>10} {'vs baseline':>12}")
    print("-" * 90)
    print(f"{'CORPUS BASELINE':<45} {len(records):>8,} {total_success:>8,} {corpus_success_rate:>9.1f}% {'':>12}")
    print("-" * 90)
    for i, name in enumerate(CHALLENGE_NAMES):
        matched = [r for r in records if name in r["_challenges"]]
        n_success = sum(1 for r in matched if not r["_has_failure"])
        if len(matched) > 0:
            rate = 100 * n_success / len(matched)
            delta = rate - corpus_success_rate
            sign = "+" if delta >= 0 else ""
            print(f"{SHORT_NAMES[i]:<45} {len(matched):>8,} {n_success:>8,} {rate:>9.1f}% {sign}{delta:>10.1f}pp")
        else:
            print(f"{SHORT_NAMES[i]:<45} {len(matched):>8,} {n_success:>8,} {'N/A':>10} {'':>12}")
    print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    tagged_any = sum(1 for r in records if len(r["_challenges"]) > 0)
    pct_tagged = 100 * tagged_any / len(records)
    print(f"Records matching at least 1 challenge: {tagged_any:,} ({pct_tagged:.1f}%)")
    print(f"Records matching 0 challenges:          {len(records) - tagged_any:,} ({100 - pct_tagged:.1f}%)")
    print()


if __name__ == "__main__":
    main()
