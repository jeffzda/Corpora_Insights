#!/usr/bin/env python3
"""
Step 6: Reference class analysis of the clean delivery registry.

Reads:   insights/ARENA_delivery_registry_full_v1_clean.yaml  — or --registry
Outputs: insights/reports/ARENA_reference_class_matrix.md     — or --out

Produces three matrices:
  A — project_type × scale_band  (base rate reference class lookup)
  B — technology_domain × lifecycle_phase  (phase risk watch-list)
  C — proponent_type  (adjustment factor)

Plus: discontinuation risk summary table.

Usage:
    python scripts/06_run_analysis.py
    python scripts/06_run_analysis.py --registry insights/ARENA_delivery_registry_full_v3_clean.yaml
    python scripts/06_run_analysis.py --min-n 20       # minimum cell size for Matrix A
    python scripts/06_run_analysis.py --out insights/reports/my_analysis.md

Requires: pip install pyyaml
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]

NO_FAIL = "no major failure stated"
DISC = "discontinued/not progressed"

PT_ORDER = [
    "DER/customer-side", "software/data/digital", "industrial decarbonisation",
    "storage", "generation", "transport electrification", "manufacturing/supply chain",
    "network/grid", "multi-technology/hybrid", "enabling infrastructure",
]
SB_ORDER = [
    "lab/bench", "pilot", "demonstration", "first commercial/FOAK",
    "commercial expansion", "utility/large-scale", "programmatic/portfolio-level",
]
TD_ORDER = [
    "solar PV", "battery storage", "DER", "hydrogen", "EV", "demand response",
    "bioenergy", "solar thermal", "grid/system stability", "wind", "pumped hydro",
    "industrial renewables", "hybrid systems", "other",
]
PH_ORDER = [
    "concept/feasibility", "development/design", "approvals/contracting",
    "procurement", "construction/installation", "commissioning/integration",
    "operations", "variation/re-scope", "close-out/post-project review",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def adv_rate(recs: list[dict]) -> float:
    return sum(1 for r in recs if (r.get("failure_mode") or "") != NO_FAIL) / len(recs) if recs else 0.0


def disc_rate(recs: list[dict]) -> float:
    return sum(1 for r in recs if (r.get("outcome_class") or "") == DISC) / len(recs) if recs else 0.0


def top_fms(recs: list[dict], n: int = 2) -> list[str]:
    c = Counter(r.get("failure_mode") or "" for r in recs if (r.get("failure_mode") or "") != NO_FAIL)
    return [fm for fm, _ in c.most_common(n)]


def peak_phase(recs: list[dict]) -> str:
    c = Counter(r.get("lifecycle_phase") or "unknown" for r in recs)
    return c.most_common(1)[0][0] if c else "—"


def outcome_profile(recs: list[dict], top: int = 4) -> str:
    ABBREV = {
        "knowledge generated despite setback": "knowledge",
        "delayed but recoverable": "delayed",
        "re-scoped/adapted": "rescoped",
        "partial success": "partial",
        "successful demonstration": "success",
        "policy/market influence only": "policy-only",
        "follow-on scale-up enabled": "scale-up",
        "discontinued/not progressed": "DISC",
    }
    c = Counter(r.get("outcome_class") or "unknown" for r in recs)
    total = len(recs)
    return ", ".join(
        f"{ABBREV.get(k, k)}={round(100 * v / total)}%"
        for k, v in c.most_common(top)
    )


def pct(x: float) -> str:
    return f"{round(100 * x)}%"


# ---------------------------------------------------------------------------
# Matrix A
# ---------------------------------------------------------------------------

def matrix_a(records: list[dict], min_n: int) -> str:
    pt_sb: dict[tuple, list] = defaultdict(list)
    for r in records:
        pt_sb[(r.get("project_type") or "null", r.get("project_scale_band") or "null")].append(r)

    corpus_adv = adv_rate(records)
    lines = [
        "## Matrix A — Delivery Archetype Reference Classes",
        "",
        f"Corpus mean adversity: **{pct(corpus_adv)}**  "
        f"(n = {len(records)} records). Cells with n < {min_n} omitted.",
        "",
        "| Project type | Scale | n | Adv% | Disc% | FM1 | FM2 | Peak phase | Outcome profile |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for pt in PT_ORDER:
        for sb in SB_ORDER:
            recs = pt_sb.get((pt, sb), [])
            if len(recs) < min_n:
                continue
            fms = top_fms(recs, 2)
            fm1 = fms[0] if len(fms) > 0 else "—"
            fm2 = fms[1] if len(fms) > 1 else "—"
            lines.append(
                f"| {pt} | {sb} | {len(recs)} | {pct(adv_rate(recs))} "
                f"| {pct(disc_rate(recs))} | {fm1} | {fm2} "
                f"| {peak_phase(recs)} | {outcome_profile(recs)} |"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matrix B
# ---------------------------------------------------------------------------

def matrix_b(records: list[dict], min_n: int = 8) -> str:
    td_ph: dict[tuple, list] = defaultdict(list)
    for r in records:
        td_ph[(r.get("technology_domain") or "null", r.get("lifecycle_phase") or "null")].append(r)

    lines = [
        "## Matrix B — Phase Risk Watch-list",
        "",
        f"Cells with n < {min_n} omitted. **Bold** = 100% adverse.",
        "",
        "| Technology domain | Phase | n | Adv% | Watch for |",
        "|---|---|---|---|---|",
    ]

    for td in TD_ORDER:
        for ph in PH_ORDER:
            recs = td_ph.get((td, ph), [])
            if len(recs) < min_n:
                continue
            adv = adv_rate(recs)
            fm1 = top_fms(recs, 1)
            fm_str = fm1[0] if fm1 else "—"
            adv_str = f"**{pct(adv)}**" if adv >= 1.0 else pct(adv)
            lines.append(f"| {td} | {ph} | {len(recs)} | {adv_str} | {fm_str} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matrix C
# ---------------------------------------------------------------------------

def matrix_c(records: list[dict]) -> str:
    pt_recs: dict[str, list] = defaultdict(list)
    for r in records:
        pt_recs[r.get("proponent_type") or "null"].append(r)

    corpus_adv = adv_rate(records)
    lines = [
        "## Matrix C — Proponent Type Adjustment Factor",
        "",
        f"Corpus baseline: **{pct(corpus_adv)}**",
        "",
        "| Proponent type | n | Adv% | Adjustment | Disc% | Primary risk |",
        "|---|---|---|---|---|---|",
    ]

    rows = [
        (pt, recs) for pt, recs in pt_recs.items() if len(recs) >= 10
    ]
    rows.sort(key=lambda x: adv_rate(x[1]))

    for pt, recs in rows:
        adv = adv_rate(recs)
        delta = adv - corpus_adv
        sign = "+" if delta >= 0 else ""
        fm1 = top_fms(recs, 1)
        lines.append(
            f"| {pt} | {len(recs)} | {pct(adv)} "
            f"| {sign}{round(100 * delta, 1):+.1f}pp "
            f"| {pct(disc_rate(recs))} "
            f"| {fm1[0] if fm1 else '—'} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discontinuation risk table
# ---------------------------------------------------------------------------

def disc_table(records: list[dict], min_disc_pct: float = 3.0) -> str:
    pt_sb: dict[tuple, list] = defaultdict(list)
    for r in records:
        pt_sb[(r.get("project_type") or "null", r.get("project_scale_band") or "null")].append(r)

    rows = []
    for (pt, sb), recs in pt_sb.items():
        if len(recs) < 15:
            continue
        dr = disc_rate(recs)
        if 100 * dr >= min_disc_pct:
            fms = top_fms(recs, 1)
            rows.append((dr, pt, sb, len(recs), fms[0] if fms else "—"))

    rows.sort(reverse=True)

    lines = [
        "## Discontinuation Risk Summary",
        "",
        f"Reference class cells with discontinuation rate ≥ {min_disc_pct:.0f}% (n ≥ 15).",
        "",
        "| Reference class | n | Disc% | Primary driver |",
        "|---|---|---|---|",
    ]
    for dr, pt, sb, n, fm1 in rows:
        lines.append(f"| {pt} × {sb} | {n} | {pct(dr)} | {fm1} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry",
                        default=str(ROOT / "insights" / "ARENA_delivery_registry_full_v1_clean.yaml"))
    parser.add_argument("--out",
                        default=str(ROOT / "insights" / "reports" / "ARENA_reference_class_matrix.md"))
    parser.add_argument("--min-n", type=int, default=15,
                        help="Minimum cell size for Matrix A (default 15)")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {registry_path.name}")
    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    records = data if isinstance(data, list) else data.get("records", [])
    print(f"  {len(records)} records")

    sections = [
        f"# ARENA Reference Class Matrix",
        f"*Source: {registry_path.name}, {len(records)} records*",
        "",
        "## How to use",
        "",
        "| Matrix | Question answered | When to use |",
        "|---|---|---|",
        "| **A** — `project_type` × `scale_band` | What base rate should I use? | Project approval |",
        "| **B** — `technology_domain` × `lifecycle_phase` | What should I monitor right now? | Phase gate |",
        "| **C** — `proponent_type` | How does my delivery actor shift the rate? | RCF adjustment |",
        "",
        "---",
        "",
        matrix_a(records, args.min_n),
        "",
        "---",
        "",
        matrix_b(records),
        "",
        "---",
        "",
        matrix_c(records),
        "",
        "---",
        "",
        disc_table(records),
    ]

    output = "\n".join(sections)
    out_path.write_text(output, encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
