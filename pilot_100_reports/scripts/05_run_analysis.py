#!/usr/bin/env python3
"""
Step 5: Cross-cutting reference class analysis of the clean delivery registry.

Reads insights/ARENA_delivery_registry_v1_clean.yaml
Produces a structured analysis report to stdout (or a file).

Covers 14 analytical cuts:
  1.  Failure mode distribution
  2.  Project type × failure mode
  3.  Delay category × lifecycle phase
  4.  Outcome class × scale band
  5.  Proponent type × failure mode
  6.  Delay category × technology domain
  7.  Commissioning/integration deep-dive
  8.  Design assumption failure deep-dive
  9.  Regulatory misfit analysis
  10. Success conditions (no major failure stated)
  11. Governance failure analysis
  12. FOAK vs demonstration comparison
  13. Grid connection outcomes
  14. Commercial/demand failure analysis

Output: analysis/reference_class_analysis.md (or stdout if no --output flag)

Requires: pip install pyyaml
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

PILOT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = PILOT_ROOT / "insights" / "ARENA_delivery_registry_v1_clean.yaml"


def load_records() -> list[dict]:
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round(100 * n / total)}%"


def top_n(counter: Counter, n: int = 5) -> list[tuple]:
    return counter.most_common(n)


def crosstab(records: list[dict], row_field: str, col_field: str) -> dict[str, Counter]:
    result: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        row = r.get(row_field) or "unknown"
        col = r.get(col_field) or "unknown"
        result[row][col] += 1
    return dict(result)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def analyze(records: list[dict]) -> str:
    out = []
    N = len(records)

    out.append(f"# ARENA Delivery Registry — Reference Class Analysis")
    out.append(f"**Records analysed: {N} (deduplicated clean registry)**\n")

    # --- Cut 1: Failure mode distribution ---
    out.append("## 1. Failure mode distribution\n")
    fm_counts = Counter(r.get("failure_mode") or "null" for r in records)
    rows = [[fm, n, pct(n, N)] for fm, n in fm_counts.most_common()]
    out.append(md_table(["Failure mode", "n", "%"], rows))
    out.append("")

    # --- Cut 2: Project type × failure mode ---
    out.append("## 2. Project type × failure mode\n")
    ct = crosstab(records, "project_type", "failure_mode")
    for pt, fm_counter in sorted(ct.items(), key=lambda x: -sum(x[1].values())):
        total = sum(fm_counter.values())
        top = fm_counter.most_common(3)
        top_str = ", ".join(f"{fm} ({n})" for fm, n in top)
        out.append(f"**{pt}** (n={total}): {top_str}")
    out.append("")

    # --- Cut 3: Delay category × lifecycle phase ---
    out.append("## 3. Delay category × lifecycle phase\n")
    ct = crosstab(records, "lifecycle_phase", "delay_category")
    rows = []
    for phase, dc_counter in sorted(ct.items(), key=lambda x: -sum(x[1].values())):
        total_delays = sum(v for k, v in dc_counter.items() if k != "no material delay stated")
        top = dc_counter.most_common(2)
        top_str = " / ".join(f"{dc} ({n})" for dc, n in top)
        rows.append([phase, sum(dc_counter.values()), top_str])
    out.append(md_table(["Lifecycle phase", "Total records", "Top delay categories"], rows))
    out.append("")

    # --- Cut 4: Outcome class × scale band ---
    out.append("## 4. Outcome class × scale band\n")
    ct = crosstab(records, "project_scale_band", "outcome_class")
    scale_order = [
        "lab / bench", "pilot", "demonstration", "first commercial / FOAK",
        "commercial expansion", "utility / large-scale", "programmatic / portfolio-level"
    ]
    for band in scale_order:
        if band not in ct:
            continue
        oc_counter = ct[band]
        total = sum(oc_counter.values())
        adverse = sum(v for k, v in oc_counter.items()
                      if k in ("delayed but recoverable", "re-scoped / adapted",
                               "knowledge generated despite setback", "discontinued / not progressed"))
        success = sum(v for k, v in oc_counter.items()
                      if k in ("successful demonstration", "follow-on scale-up enabled"))
        out.append(f"**{band}** (n={total}): {pct(adverse, total)} adverse, {pct(success, total)} successful")
    out.append("")

    # --- Cut 5: Proponent type × failure mode ---
    out.append("## 5. Proponent type × failure mode\n")
    ct = crosstab(records, "proponent_type", "failure_mode")
    rows = []
    for pt, fm_counter in sorted(ct.items(), key=lambda x: -sum(x[1].values())):
        total = sum(fm_counter.values())
        any_fail = total - fm_counter.get("no major failure stated", 0)
        top = fm_counter.most_common(1)[0]
        rows.append([pt, total, pct(any_fail, total), f"{top[0]} ({top[1]})"])
    out.append(md_table(["Proponent type", "n", "Any failure", "Top failure mode"], rows))
    out.append("")

    # --- Cut 6: Delay category × technology domain ---
    out.append("## 6. Delay category × technology domain\n")
    ct = crosstab(records, "technology_domain", "delay_category")
    for td, dc_counter in sorted(ct.items(), key=lambda x: -sum(x[1].values())):
        total = sum(dc_counter.values())
        top = dc_counter.most_common(2)
        top_str = " / ".join(f"{dc} ({pct(n, total)})" for dc, n in top)
        out.append(f"**{td}** (n={total}): {top_str}")
    out.append("")

    # --- Cut 7: Commissioning/integration deep-dive ---
    out.append("## 7. Commissioning/integration phase deep-dive\n")
    comm = [r for r in records if r.get("lifecycle_phase") == "commissioning / integration"]
    out.append(f"Records in commissioning/integration phase: {len(comm)}")
    fm = Counter(r.get("failure_mode") for r in comm)
    out.append("Failure modes: " + ", ".join(f"{k} ({v})" for k, v in fm.most_common(5)))
    pt = Counter(r.get("project_type") for r in comm)
    out.append("Project types: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("")

    # --- Cut 8: Design assumption failure deep-dive ---
    out.append("## 8. Design assumption failure deep-dive\n")
    daf = [r for r in records if r.get("failure_mode") == "design assumption failure"]
    out.append(f"Total design assumption failure records: {len(daf)}")
    phase = Counter(r.get("lifecycle_phase") for r in daf)
    pt = Counter(r.get("project_type") for r in daf)
    prop = Counter(r.get("proponent_type") for r in daf)
    out.append("By lifecycle phase: " + ", ".join(f"{k} ({v})" for k, v in phase.most_common(5)))
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By proponent type: " + ", ".join(f"{k} ({v})" for k, v in prop.most_common(5)))
    out.append("")

    # --- Cut 9: Regulatory misfit ---
    out.append("## 9. Regulatory misfit analysis\n")
    reg = [r for r in records if r.get("failure_mode") == "regulatory misfit"]
    out.append(f"Total regulatory misfit records: {len(reg)}")
    pt = Counter(r.get("project_type") for r in reg)
    td = Counter(r.get("technology_domain") for r in reg)
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By technology domain: " + ", ".join(f"{k} ({v})" for k, v in td.most_common(5)))
    out.append("")

    # --- Cut 10: Success conditions ---
    out.append("## 10. Success conditions (no major failure stated)\n")
    success = [r for r in records if r.get("failure_mode") == "no major failure stated"]
    out.append(f"Records with no major failure: {len(success)} ({pct(len(success), N)})")
    pt = Counter(r.get("project_type") for r in success)
    prop = Counter(r.get("proponent_type") for r in success)
    scale = Counter(r.get("project_scale_band") for r in success)
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By proponent type: " + ", ".join(f"{k} ({v})" for k, v in prop.most_common(5)))
    out.append("By scale band: " + ", ".join(f"{k} ({v})" for k, v in scale.most_common(5)))
    out.append("")

    # --- Cut 11: Governance failure ---
    out.append("## 11. Governance / coordination failure analysis\n")
    gov = [r for r in records if r.get("failure_mode") == "governance / coordination failure"]
    out.append(f"Total governance failure records: {len(gov)}")
    pt = Counter(r.get("proponent_type") for r in gov)
    ptype = Counter(r.get("project_type") for r in gov)
    out.append("By proponent type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in ptype.most_common(5)))
    out.append("")

    # --- Cut 12: FOAK vs demonstration ---
    out.append("## 12. FOAK vs demonstration comparison\n")
    foak = [r for r in records if r.get("project_scale_band") == "first commercial / FOAK"]
    demo = [r for r in records if r.get("project_scale_band") == "demonstration"]
    for label, group in [("FOAK", foak), ("Demonstration", demo)]:
        n = len(group)
        fm = Counter(r.get("failure_mode") for r in group)
        out.append(f"**{label}** (n={n})")
        out.append("  Top failure modes: " + ", ".join(f"{k} ({v})" for k, v in fm.most_common(3)))
    out.append("")

    # --- Cut 13: Grid connection outcomes ---
    out.append("## 13. Grid connection delay analysis\n")
    grid = [r for r in records if r.get("delay_category") == "grid connection / system studies"]
    out.append(f"Records with grid connection delay: {len(grid)}")
    pt = Counter(r.get("project_type") for r in grid)
    td = Counter(r.get("technology_domain") for r in grid)
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By technology domain: " + ", ".join(f"{k} ({v})" for k, v in td.most_common(5)))
    out.append("")

    # --- Cut 14: Commercial/demand failure ---
    out.append("## 14. Commercial / demand failure analysis\n")
    comm_fail = [r for r in records if r.get("failure_mode") == "commercial / demand failure"]
    out.append(f"Total commercial/demand failure records: {len(comm_fail)}")
    pt = Counter(r.get("project_type") for r in comm_fail)
    td = Counter(r.get("technology_domain") for r in comm_fail)
    scale = Counter(r.get("project_scale_band") for r in comm_fail)
    out.append("By project type: " + ", ".join(f"{k} ({v})" for k, v in pt.most_common(5)))
    out.append("By technology: " + ", ".join(f"{k} ({v})" for k, v in td.most_common(5)))
    out.append("By scale: " + ", ".join(f"{k} ({v})" for k, v in scale.most_common(5)))
    out.append("")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Run reference class analysis on clean registry")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write output to this file (default: stdout)")
    args = parser.parse_args()

    records = load_records()
    print(f"Loaded {len(records)} records from {REGISTRY_FILE}", file=sys.stderr)

    report = analyze(records)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
