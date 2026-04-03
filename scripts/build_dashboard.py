#!/usr/bin/env python3
"""
Generate a single-file HTML dashboard from per_doc YAML extraction outputs.

Usage:
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --input insights/per_doc --output dashboard/insights.html
"""

import argparse
import csv
import glob
import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")


# ── Parallel YAML loading ───────────────────────────────────────────────────

def _load_yaml_file(path: str) -> list[dict]:
    """Load a single YAML file — used as a worker function for ProcessPoolExecutor."""
    with open(path, encoding="utf-8") as f:
        recs = yaml.safe_load(f)
    return recs if recs else []


def _parallel_load_yaml(paths: list[str], workers: int = None) -> list[list[dict]]:
    """Load many YAML files in parallel using ProcessPoolExecutor."""
    if not paths:
        return []
    w = workers or min(cpu_count() or 4, len(paths))
    with ProcessPoolExecutor(max_workers=w) as pool:
        return list(pool.map(_load_yaml_file, paths))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "insights" / "per_doc"
DEFAULT_OUTPUT = ROOT / "dashboard" / "insights.html"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
AGGREGATED_DIR = ROOT / "tables" / "aggregated"
PER_PROJECT_DIR = ROOT / "insights" / "per_project"

FAILURE_MODE_COLOURS = {
    "no major failure stated":          "#22c55e",
    "poor scoping":                     "#f97316",
    "unvalidated technical assumptions":"#ef4444",
    "unvalidated integration":          "#f43f5e",
    "regulatory & approvals":           "#a855f7",
    "commercial & market":              "#14b8a6",
    "coordination & stakeholders":      "#ec4899",
    "data & measurement":               "#eab308",
    "execution & logistics":            "#6366f1",
}


ISSUE_SEVERITY_COLOURS = {
    "none":     "#22c55e",
    "minor":    "#eab308",
    "moderate": "#f97316",
    "major":    "#ef4444",
    "critical": "#7f1d1d",
}

QA_VERDICT_COLOURS = {
    "confirmed":    "#16a34a",
    "plausible":    "#ca8a04",
    "unsupported":  "#ef4444",
    "fabricated":   "#7f1d1d",
}

QA_DIR = ROOT / "insights" / "per_doc_qa"

# ── Reference class matrix constants ────────────────────────────────────────

_NO_FAIL = "no major failure stated"

_AC_ORDER = [
    "Solar PV", "Battery storage", "Distributed energy resources", "Hydrogen",
    "Demand response", "Electric vehicles", "Industrial renewables",
    "Grid stability", "Hybrid technologies", "Solar thermal",
    "Bioenergy", "Wind", "Pumped hydro", "Off grid",
]
_AT_ORDER = [
    "Study / feasibility", "Pilot / demonstration", "Deployment",
]
_PH_ORDER = [
    "concept/feasibility", "development/design", "approvals/contracting",
    "procurement", "construction/installation", "commissioning/integration",
    "operations", "close-out/post-project review",
]


_SEV_HIGH = {"major", "critical"}
_SEV_SEVERE = {"major", "critical"}
_SEV_MILD = {"minor", "moderate"}


def _adv_rate(recs):
    return sum(1 for r in recs if (r.get("issue_severity") or "") in _SEV_HIGH) / len(recs) if recs else 0.0



def _top_fms(recs, n=2):
    c = Counter(r.get("failure_mode") or "" for r in recs if (r.get("failure_mode") or "") != _NO_FAIL)
    return [fm for fm, _ in c.most_common(n)]


def _pct(x):
    return f"{round(100 * x)}%"


_INFERNO = [
    (0.000, (0,    0,   4)),
    (0.125, (31,  12,  72)),
    (0.250, (85,  15, 109)),
    (0.375, (139,  34,  82)),
    (0.500, (188,  55,  84)),
    (0.625, (229, 105,  56)),
    (0.750, (249, 163,   7)),
    (0.875, (252, 213,  82)),
    (1.000, (252, 255, 164)),
]


def _viridis_cell(rate, vmin, vmax):
    """Return (bg_hex, fg_hex) using inferno, normalised to [vmin, vmax]."""
    t = (rate - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    t = max(0.0, min(1.0, t))
    for i in range(len(_INFERNO) - 1):
        t0, c0 = _INFERNO[i]
        t1, c1 = _INFERNO[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            r = int(c0[0] + f * (c1[0] - c0[0]))
            g = int(c0[1] + f * (c1[1] - c0[1]))
            b = int(c0[2] + f * (c1[2] - c0[2]))
            bg = f"#{r:02x}{g:02x}{b:02x}"
            return bg, "#000000"
    bg = f"#{_INFERNO[-1][1][0]:02x}{_INFERNO[-1][1][1]:02x}{_INFERNO[-1][1][2]:02x}"
    return bg, "#000000"


def load_project_profiles() -> list[dict]:
    """
    Build one profile per project from per_project/*.yaml files.
    Each profile captures boolean flags and phase-level breakdown needed
    for project-level matrix rates.
    """
    _SEV_HIGH_SET = {"major", "critical"}
    paths = sorted(str(p) for p in PER_PROJECT_DIR.glob("*.yaml"))
    all_file_records = _parallel_load_yaml(paths)
    profiles = []
    for records in all_file_records:
        if not records:
            continue

        def majority(field):
            c = Counter(r.get(field) for r in records if r.get(field))
            return c.most_common(1)[0][0] if c else None

        # Aggregate per lifecycle phase
        phase_recs: dict = defaultdict(list)
        for r in records:
            ph = r.get("lifecycle_phase")
            if ph:
                phase_recs[ph].append(r)

        # Phase-level failure presence: phase → top failure mode among major+ records
        phase_failures: dict = {}
        for ph, recs in phase_recs.items():
            bad = [r for r in recs if (r.get("issue_severity") or "") in _SEV_HIGH_SET]
            if bad:
                c = Counter(
                    r.get("failure_mode") for r in bad
                    if r.get("failure_mode") and r["failure_mode"] != _NO_FAIL
                )
                phase_failures[ph] = c.most_common(1)[0][0] if c else None

        # arena_category: flatten list field, take most common
        ac_counter = Counter()
        for r in records:
            for cat in (r.get("arena_category") or []):
                ac_counter[cat] += 1
        arena_cat = ac_counter.most_common(1)[0][0] if ac_counter else None

        # Severity counts for escalation ratio
        sev_severe = sum(1 for r in records if (r.get("issue_severity") or "") in _SEV_SEVERE)
        sev_mild = sum(1 for r in records if (r.get("issue_severity") or "") in _SEV_MILD)

        # Per-failure-mode severity counts
        fm_sev: dict = defaultdict(lambda: [0, 0])  # fm → [severe, mild]
        for r in records:
            fm = r.get("failure_mode") or ""
            sev = r.get("issue_severity") or ""
            if fm and fm != _NO_FAIL:
                if sev in _SEV_SEVERE:
                    fm_sev[fm][0] += 1
                elif sev in _SEV_MILD:
                    fm_sev[fm][1] += 1

        profiles.append({
            "arena_category":    arena_cat,
            "activity_type":     majority("activity_type"),
            "proponent_type":    majority("proponent_type"),
            "is_consortium":     any(r.get("is_consortium") for r in records),
            "had_moderate_plus": any(
                (r.get("issue_severity") or "") in _SEV_HIGH_SET for r in records
            ),
            "failure_modes": {
                r.get("failure_mode") for r in records
                if r.get("failure_mode") and r["failure_mode"] != _NO_FAIL
            },
            "phases_covered":  set(phase_recs.keys()),
            "phase_failures":  phase_failures,   # phase → top fm at that phase (major+ only)
            "n_records":       len(records),
            "sev_severe":      sev_severe,
            "sev_mild":        sev_mild,
            "fm_severity":     dict(fm_sev),      # fm → [severe, mild]
        })
    return profiles


def _sev_ratio(profs):
    """Severity percentage: major+critical as % of all adverse (major+critical+minor+moderate)."""
    severe = sum(p["sev_severe"] for p in profs)
    mild = sum(p["sev_mild"] for p in profs)
    total = severe + mild
    return (severe / total * 100) if total > 0 else None


def _sev_ratio_fmt(profs):
    """Format severity percentage as string, or '—' if no adverse records."""
    r = _sev_ratio(profs)
    return f"{r:.0f}%" if r is not None else "—"


def _sev_ratio_from_counts(severe, mild):
    """Severity percentage from raw counts."""
    total = severe + mild
    return (severe / total * 100) if total > 0 else None


def _sev_ratio_cell(ratio, vmin=0.0, vmax=60.0):
    """Return inline style for a severity ratio cell. Higher = more red."""
    if ratio is None:
        return 'background:#f8fafc;color:#94a3b8'
    t = (ratio - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    t = max(0.0, min(1.0, t))
    # Green (low) → Yellow (mid) → Red (high)
    if t < 0.5:
        f = t / 0.5
        r = int(34 + f * (202 - 34))
        g = int(197 + f * (138 - 197))
        b = int(94 + f * (4 - 94))
    else:
        f = (t - 0.5) / 0.5
        r = int(202 + f * (220 - 202))
        g = int(138 + f * (38 - 138))
        b = int(4 + f * (38 - 4))
    return f'background:#{r:02x}{g:02x}{b:02x};color:#000;font-weight:600'


def build_reference_class_html(profiles: list[dict], min_n: int = 5) -> str:
    """
    Generate HTML for the reference-class matrices.
    Unit of analysis is the PROJECT (one profile per project), not the record.
    Adv% = % of projects with at least one major/critical record.
    Sev% = major+critical as % of all adverse records in the group.
    """

    # ── Group profiles ────────────────────────────────────────────────────────
    # Matrix 1: arena_category × activity_type
    ac_at: dict = defaultdict(list)
    for p in profiles:
        ac = p.get("arena_category") or ""
        at = p.get("activity_type") or ""
        if ac and at and at != "R&D":  # Exclude R&D from matrices
            ac_at[(ac, at)].append(p)

    ptype_profiles: dict = defaultdict(list)
    for p in profiles:
        ptype_profiles[p["proponent_type"] or "null"].append(p)

    # Consortium flag grouping
    cons_yes = [p for p in profiles if p.get("is_consortium")]
    cons_no = [p for p in profiles if not p.get("is_consortium")]

    n_projects = len(profiles)
    corpus_adv = sum(1 for p in profiles if p["had_moderate_plus"]) / n_projects if n_projects else 0.0
    def proj_adv(profs):
        return sum(1 for p in profs if p["had_moderate_plus"]) / len(profs) if profs else 0.0

    def proj_top_fms(profs, n=2):
        c = Counter(fm for p in profs for fm in p["failure_modes"])
        return [fm for fm, _ in c.most_common(n)]

    # ── Pre-pass: collect all cell rates for vmin/vmax ────────────────────────
    all_rates = []
    for ac in _AC_ORDER:
        for at in _AT_ORDER:
            profs = ac_at.get((ac, at), [])
            if len(profs) >= min_n:
                all_rates.append(proj_adv(profs))
    for profs in ptype_profiles.values():
        if len(profs) >= min_n:
            all_rates.append(proj_adv(profs))

    # Matrix 2: arena_category × lifecycle_phase
    ac_ph_cells: dict = {}
    min_n_b = 5
    for ac in _AC_ORDER:
        ac_profs = [p for p in profiles if p.get("arena_category") == ac]
        for ph in _PH_ORDER:
            covered = [p for p in ac_profs if ph in p["phases_covered"]]
            if len(covered) < min_n_b:
                continue
            adv = sum(1 for p in covered if ph in p["phase_failures"]) / len(covered)
            fm_c = Counter(
                p["phase_failures"][ph] for p in covered
                if ph in p["phase_failures"] and p["phase_failures"][ph]
            )
            fm1 = fm_c.most_common(1)[0][0] if fm_c else "—"
            ac_ph_cells[(ac, ph)] = (len(covered), adv, fm1)
            all_rates.append(adv)

    vmin = 0.0
    vmax = 0.70

    def adv_cell(rate):
        bg, fg = _viridis_cell(rate, vmin, vmax)
        return f'background:{bg};color:{fg}'

    # ── Matrix 1: arena_category × activity_type (2D heatmap) ──────────────
    corpus_sev_ratio = _sev_ratio(profiles)
    corpus_sr_fmt = f"{corpus_sev_ratio:.0f}%" if corpus_sev_ratio is not None else "—"

    # Collect all sev% values for colour normalisation
    ma_sev_vals = []
    ma_cells: dict = {}  # (ac, at) → (n, adv, sr, fm1)
    for ac in _AC_ORDER:
        for at in _AT_ORDER:
            profs = ac_at.get((ac, at), [])
            if len(profs) < min_n:
                continue
            adv = proj_adv(profs)
            sr = _sev_ratio(profs)
            fms = proj_top_fms(profs, 1)
            fm1 = fms[0] if fms else "—"
            ma_cells[(ac, at)] = (len(profs), adv, sr, fm1)
            if sr is not None:
                ma_sev_vals.append(sr)

    # Build header row
    at_short = {"Study / feasibility": "Study", "Pilot / demonstration": "Pilot", "Deployment": "Deploy"}
    ma_hdr = '<tr><th class="hm-row-hdr">ARENA category</th>'
    for at in _AT_ORDER:
        ma_hdr += f'<th>{at_short.get(at, at)}</th>'
    ma_hdr += '</tr>'

    # Build data rows
    ma_rows = []
    for ac in _AC_ORDER:
        has_data = any((ac, at) in ma_cells for at in _AT_ORDER)
        if not has_data:
            continue
        row = f'<tr><td class="hm-row-hdr">{ac}</td>'
        for at in _AT_ORDER:
            if (ac, at) in ma_cells:
                n, adv, sr, fm1 = ma_cells[(ac, at)]
                sr_fmt = f"{sr:.0f}%" if sr is not None else "—"
                tip = f"n={n} projects · Adv%={_pct(adv)} · Top: {fm1}"
                row += f'<td style="{_sev_ratio_cell(sr)}" title="{tip}">{sr_fmt}</td>'
            else:
                row += '<td class="hm-empty">—</td>'
        row += '</tr>'
        ma_rows.append(row)

    ma_html = (
        f'<div class="an-card an-wide">'
        f'<div class="an-card-title">ARENA Category × Activity Type</div>'
        f'<div class="an-card-sub">'
        f'Sev% = major+critical as % of adverse records. '
        f'Corpus baseline: <strong>{corpus_sr_fmt}</strong>. '
        f'Hover for detail. '
        f'Cells with &lt; {min_n} projects omitted. R&amp;D excluded.</div>'
        f'<div class="rcm-scroll"><table class="hm-table">'
        f'<thead>{ma_hdr}</thead>'
        f'<tbody>{"".join(ma_rows)}</tbody>'
        f'</table></div></div>'
    )

    # ── Matrix 2: arena_category × lifecycle_phase (2D heatmap) ─────────────
    ph_short = {
        "concept/feasibility": "Concept", "development/design": "Design",
        "approvals/contracting": "Approvals", "procurement": "Procure",
        "construction/installation": "Build", "commissioning/integration": "Commiss.",
        "operations": "Ops", "close-out/post-project review": "Close-out",
    }

    mb_hdr = '<tr><th class="hm-row-hdr">ARENA category</th>'
    for ph in _PH_ORDER:
        mb_hdr += f'<th>{ph_short.get(ph, ph)}</th>'
    mb_hdr += '</tr>'

    mb_rows = []
    for ac in _AC_ORDER:
        has_data = any((ac, ph) in ac_ph_cells for ph in _PH_ORDER)
        if not has_data:
            continue
        row = f'<tr><td class="hm-row-hdr">{ac}</td>'
        for ph in _PH_ORDER:
            if (ac, ph) in ac_ph_cells:
                n_cov, adv, fm1 = ac_ph_cells[(ac, ph)]
                tip = f"n={n_cov} projects · Watch for: {fm1}"
                row += f'<td style="{adv_cell(adv)}" title="{tip}">{_pct(adv)}</td>'
            else:
                row += '<td class="hm-empty">—</td>'
        row += '</tr>'
        mb_rows.append(row)

    mb_html = (
        f'<div class="an-card an-wide">'
        f'<div class="an-card-title">ARENA Category × Lifecycle Phase</div>'
        f'<div class="an-card-sub">'
        f'Adv% = % of projects with a major+ issue at that phase. '
        f'Hover for detail. '
        f'Cells with &lt; {min_n_b} projects omitted.</div>'
        f'<div class="rcm-scroll"><table class="hm-table">'
        f'<thead>{mb_hdr}</thead>'
        f'<tbody>{"".join(mb_rows)}</tbody>'
        f'</table></div></div>'
    )

    # ── Matrix 3: proponent_type + consortium adjustment ─────────────────────
    mc_data = sorted(
        [(pt, profs) for pt, profs in ptype_profiles.items() if len(profs) >= min_n],
        key=lambda x: proj_adv(x[1]),
    )
    mc_rows = []
    for pt, profs in mc_data:
        adv = proj_adv(profs)
        sr = _sev_ratio(profs)
        delta = adv - corpus_adv
        sign = "+" if delta >= 0 else ""
        delta_col = "#dc2626" if delta >= 0.05 else ("#16a34a" if delta <= -0.05 else "#64748b")
        fms = proj_top_fms(profs, 1)
        sr_fmt = f"{sr:.0f}%" if sr is not None else "—"
        mc_rows.append(
            f'<tr><td>{pt}</td>'
            f'<td class="rcm-num">{len(profs)}</td>'
            f'<td class="rcm-num rcm-rate" style="{adv_cell(adv)}">{_pct(adv)}</td>'
            f'<td class="rcm-num" style="color:{delta_col};font-weight:600">{sign}{round(100 * delta, 1):+.1f}pp</td>'
            f'<td class="rcm-num" style="{_sev_ratio_cell(sr)}">{sr_fmt}</td>'
            f'<td class="rcm-fm">{fms[0] if fms else "—"}</td>'
            f'</tr>'
        )

    # Consortium governance adjustment row
    cons_adj_html = ""
    if len(cons_yes) >= min_n and len(cons_no) >= min_n:
        adv_yes = proj_adv(cons_yes)
        adv_no = proj_adv(cons_no)
        uplift = adv_yes - adv_no
        up_sign = "+" if uplift >= 0 else ""
        up_col = "#dc2626" if uplift >= 0.03 else ("#16a34a" if uplift <= -0.03 else "#64748b")
        sr_yes = _sev_ratio(cons_yes)
        sr_no = _sev_ratio(cons_no)
        sr_yes_fmt = f"{sr_yes:.0f}%" if sr_yes is not None else "—"
        sr_no_fmt = f"{sr_no:.0f}%" if sr_no is not None else "—"
        cons_adj_html = (
            f'<tr style="border-top:2px solid #cbd5e1;background:#f8fafc">'
            f'<td><em>Consortium governance adjustment</em></td>'
            f'<td class="rcm-num">{len(cons_yes)} vs {len(cons_no)}</td>'
            f'<td class="rcm-num">{_pct(adv_yes)} vs {_pct(adv_no)}</td>'
            f'<td class="rcm-num" style="color:{up_col};font-weight:600">{up_sign}{round(100 * uplift, 1):+.1f}pp</td>'
            f'<td class="rcm-num">{sr_yes_fmt} vs {sr_no_fmt}</td>'
            f'<td class="rcm-fm">coordination &amp; stakeholders</td>'
            f'</tr>'
        )

    mc_empty = '<tr><td colspan="6" class="rcm-empty">Insufficient data</td></tr>'
    mc_html = (
        f'<div class="an-card an-wide">'
        f'<div class="an-card-title">Matrix 3 — Proponent Type Adjustment Factor</div>'
        f'<div class="an-card-sub">Corpus baseline: <strong>{_pct(corpus_adv)}</strong> adversity, '
        f'severity <strong>{corpus_sr_fmt}</strong>.'
        f' Red adjustment = above baseline, green = below.</div>'
        f'<div class="rcm-scroll"><table class="rcm-table">'
        f'<thead><tr><th>Proponent type</th><th>Projects</th><th>Adv%</th>'
        f'<th>Adjustment</th><th>Sev%</th><th>Primary risk</th></tr></thead>'
        f'<tbody>{"".join(mc_rows) if mc_rows else mc_empty}{cons_adj_html}</tbody>'
        f'</table></div></div>'
    )

    # ── Matrix 5: Severity Escalation by Failure Mode ──────────────────────
    fm_agg: dict = defaultdict(lambda: [0, 0])  # fm → [total_severe, total_mild]
    for p in profiles:
        for fm, (sev, mild) in p.get("fm_severity", {}).items():
            fm_agg[fm][0] += sev
            fm_agg[fm][1] += mild

    se_data = []
    for fm, (sev, mild) in fm_agg.items():
        total = sev + mild
        if total < 10:
            continue
        ratio = (sev / total * 100) if total > 0 else None
        se_data.append((ratio if ratio is not None else 999, fm, sev, mild, total, ratio))
    se_data.sort(reverse=True)

    se_rows = []
    for _, fm, sev, mild, total, ratio in se_data:
        r_fmt = f"{ratio:.0f}%" if ratio is not None else "—"
        se_rows.append(
            f'<tr><td>{fm}</td>'
            f'<td class="rcm-num">{total:,}</td>'
            f'<td class="rcm-num">{sev:,}</td>'
            f'<td class="rcm-num">{mild:,}</td>'
            f'<td class="rcm-num" style="{_sev_ratio_cell(ratio)}">{r_fmt}</td>'
            f'</tr>'
        )

    se_empty = '<tr><td colspan="5" class="rcm-empty">Insufficient data</td></tr>'
    se_html = (
        f'<div class="an-card an-wide">'
        f'<div class="an-card-title">Matrix 5 — Severity Escalation by Failure Mode</div>'
        f'<div class="an-card-sub">Which failure types tend to be severe when they occur? '
        f'Sev% = major+critical as % of all adverse records. '
        f'Corpus baseline: <strong>{corpus_sr_fmt}</strong>. '
        f'Higher = problems tend to be severe; lower = problems stay manageable.</div>'
        f'<div class="rcm-scroll"><table class="rcm-table">'
        f'<thead><tr><th>Failure mode</th><th>Adverse records</th>'
        f'<th>Major/critical</th><th>Minor/moderate</th><th>Sev%</th></tr></thead>'
        f'<tbody>{"".join(se_rows) if se_rows else se_empty}</tbody>'
        f'</table></div></div>'
    )

    # ── Matrix 6: Severity Escalation by ARENA Category ──────────────────
    ac_sev_data = []
    for ac in _AC_ORDER:
        ac_profs = [p for p in profiles if p.get("arena_category") == ac]
        if len(ac_profs) < min_n:
            continue
        sr = _sev_ratio(ac_profs)
        sev_total = sum(p["sev_severe"] for p in ac_profs)
        mild_total = sum(p["sev_mild"] for p in ac_profs)
        adv = proj_adv(ac_profs)
        ac_sev_data.append((ac, len(ac_profs), sev_total, mild_total, sr, adv))

    sc_rows = []
    for ac, n_p, sev, mild, sr, adv in sorted(ac_sev_data, key=lambda x: (x[4] if x[4] is not None else -1), reverse=True):
        sr_fmt = f"{sr:.0f}%" if sr is not None else "—"
        sc_rows.append(
            f'<tr><td>{ac}</td>'
            f'<td class="rcm-num">{n_p}</td>'
            f'<td class="rcm-num rcm-rate" style="{adv_cell(adv)}">{_pct(adv)}</td>'
            f'<td class="rcm-num">{sev:,}</td>'
            f'<td class="rcm-num">{mild:,}</td>'
            f'<td class="rcm-num" style="{_sev_ratio_cell(sr)}">{sr_fmt}</td>'
            f'</tr>'
        )

    sc_empty = '<tr><td colspan="6" class="rcm-empty">Insufficient data</td></tr>'
    sc_html = (
        f'<div class="an-card an-wide">'
        f'<div class="an-card-title">Matrix 6 — Severity Escalation by ARENA Category</div>'
        f'<div class="an-card-sub">How severe are problems when they occur, by technology? '
        f'Sorted by severity %. Corpus baseline: <strong>{corpus_sr_fmt}</strong>.</div>'
        f'<div class="rcm-scroll"><table class="rcm-table">'
        f'<thead><tr><th>ARENA category</th><th>Projects</th><th>Adv%</th>'
        f'<th>Major/critical</th><th>Minor/moderate</th><th>Sev%</th></tr></thead>'
        f'<tbody>{"".join(sc_rows) if sc_rows else sc_empty}</tbody>'
        f'</table></div></div>'
    )

    return ma_html + mb_html + mc_html + se_html + sc_html


def load_portfolio_size() -> int:
    if not PROJECTS_FILE.exists():
        return 0
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def load_benchmarks() -> dict:
    datasets = {
        'lcoe':            ('lcoe_unified.csv',              'LCOE (AUD$/MWh)',              'Levelised cost of energy by technology and scenario year'),
        'capex':           ('capex_per_kw_unified.csv',      'Capex (AUD$/kW or kWh)',       'Capital costs by technology and configuration'),
        'lcoh':            ('hydrogen_lcoh_unified.csv',     'LCOH (AUD$/kg H\u2082)',       'Levelised cost of hydrogen by production pathway'),
        'capacity_factor': ('capacity_factor_unified.csv',   'Capacity Factor (%)',          'Actual and modelled capacity factors by technology and project'),
        'abatement':       ('abatement_cost_unified.csv',    'Abatement Cost (AUD$/tCO\u2082e)', 'Cost of abatement by technology and measure'),
        'storage':         ('storage_performance_unified.csv','Storage Performance (RTE %)', 'Round-trip efficiency and performance metrics by storage technology'),
    }
    result = {}
    for key, (filename, title, desc) in datasets.items():
        path = AGGREGATED_DIR / filename
        if not path.exists():
            continue
        rows = list(csv.DictReader(open(path, encoding='utf-8')))
        result[key] = {
            'title': title,
            'description': desc,
            'columns': list(rows[0].keys()) if rows else [],
            'rows': rows,
        }
    return result


def load_records(input_dir: Path) -> list[dict]:
    paths = sorted(glob.glob(str(input_dir / "doc_*.yaml")))
    batches = _parallel_load_yaml(paths)
    records = []
    for recs in batches:
        records.extend(recs)
    return records


def load_deduped_records(registry_path: Path) -> list[dict]:
    with open(registry_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    return records if records else []


def load_qa_results() -> dict:
    """Load QA verdicts from per_doc_qa/, keyed by record_id."""
    if not QA_DIR.exists():
        return {}
    paths = sorted(glob.glob(str(QA_DIR / "doc_*_qa.yaml")))
    batches = _parallel_load_yaml(paths)
    qa = {}
    for results in batches:
        for r in results:
            if r.get("record_id"):
                qa[r["record_id"]] = r
    return qa


def clean_record(r: dict) -> dict:
    return {k: (v if v is not None else "") for k, v in r.items()}


def distinct_sorted(records, field):
    vals = sorted({r[field] for r in records if r.get(field)})
    return vals


def build_html(records: list[dict], portfolio_size: int = 0, benchmarks: dict = None,
               qa_results: dict = None) -> str:
    qa_results = qa_results or {}
    # Merge QA verdicts onto records
    for r in records:
        rid = r.get("record_id")
        if rid and rid in qa_results:
            r["qa_verdict"]              = qa_results[rid].get("grounding_verdict") or qa_results[rid].get("verdict") or ""
            r["qa_classification"]       = qa_results[rid].get("classification_verdict") or ""
            r["qa_classification_note"]  = qa_results[rid].get("classification_note") or ""
            r["qa_source_text"]          = qa_results[rid].get("source_text") or ""
            r["qa_source_page"]          = qa_results[rid].get("source_page") or ""
            r["qa_note"]                 = qa_results[rid].get("grounding_note") or qa_results[rid].get("note") or ""
        else:
            r["qa_verdict"] = r["qa_classification"] = r["qa_classification_note"] = ""
            r["qa_source_text"] = r["qa_source_page"] = r["qa_note"] = ""

    records = [clean_record(r) for r in records]
    data_json = json.dumps(records, ensure_ascii=False)
    fm_colours = json.dumps(FAILURE_MODE_COLOURS)
    is_colours = json.dumps(ISSUE_SEVERITY_COLOURS)
    qa_colours = json.dumps(QA_VERDICT_COLOURS)
    benchmarks_json = json.dumps(benchmarks or {}, ensure_ascii=False)
    arena_root = str(ROOT).replace("\\", "/")

    failure_modes = distinct_sorted(records, "failure_mode")
    proponent_types = distinct_sorted(records, "proponent_type")
    lifecycle_phases = distinct_sorted(records, "lifecycle_phase")
    severity_levels = distinct_sorted(records, "issue_severity")
    transferability_vals = distinct_sorted(records, "transferability")
    qa_verdicts = distinct_sorted(records, "qa_verdict")
    qa_classifications = distinct_sorted(records, "qa_classification")
    arena_categories = sorted({c for r in records for c in (r.get("arena_category") or []) if c})
    activity_types = sorted({r.get("activity_type") for r in records if r.get("activity_type")})

    def options(values):
        return "\n".join(f'<option value="{v}">{v}</option>' for v in values)

    n = len(records)
    n_projects_covered = len({r["kb_associated_project"] for r in records if r.get("in_arena_portfolio")})
    portfolio_pct = f"{n_projects_covered/portfolio_size*100:.0f}%" if portfolio_size else "—"
    n_failures = len([r for r in records if r.get("failure_mode") and r["failure_mode"] != "no major failure stated"])
    kb_projects = distinct_sorted(records, "kb_associated_project")
    project_profiles = load_project_profiles() if PER_PROJECT_DIR.exists() else []
    matrix_html = build_reference_class_html(project_profiles) if project_profiles else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARENA Delivery Insights</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ height: 100%; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; height: 100%; display: flex; flex-direction: column; overflow: hidden; }}

  /* Header */
  header {{ background: #0f172a; color: white; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size:24px; font-weight: 600; letter-spacing: -0.3px; }}
  header span {{ font-size:17px; color: #94a3b8; }}

  /* Tab navigation */
  .tabs {{ background: white; border-bottom: 2px solid #e2e8f0; padding: 0 32px; display: flex; }}
  .tab {{ padding: 14px 22px; font-size:17px; font-weight: 600; color: #64748b; cursor: pointer;
          border-bottom: 3px solid transparent; margin-bottom: -2px; transition: color 0.15s; }}
  .tab:hover {{ color: #1e293b; }}
  .tab.active {{ color: #6366f1; border-bottom-color: #6366f1; }}
  .tab-content {{ display: none; flex-direction: column; }}
  .tab-content.active {{ display: flex; flex: 1; min-height: 0; }}

  /* Stats bar */
  .stats {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 32px; display: flex; gap: 32px; }}
  .stat {{ display: flex; flex-direction: column; }}
  .stat-value {{ font-size:28px; font-weight: 700; color: #0f172a; }}
  .stat-label {{ font-size:16px; color: #64748b; margin-top: 2px; }}

  /* Filter bar */
  .filter-bar {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 8px 20px; display: flex; align-items: flex-end; gap: 10px; overflow-x: auto; flex-shrink: 0; white-space: nowrap; }}
  .fi {{ display: inline-flex; flex-direction: column; gap: 2px; }}
  .fi label {{ font-size:13px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
  .fi select, .fi input {{ font-size:16px; padding: 4px 7px; border: 1px solid #e2e8f0; border-radius: 5px; background: #f8fafc; color: #1e293b; height: 28px; }}
  .fi select:focus, .fi input:focus {{ outline: none; border-color: #6366f1; }}
  .fi-search input {{ width: 180px; }}
  .fi select {{ min-width: 110px; }}
  .filter-clear-btn {{ font-size:15px; padding: 0 12px; height: 28px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 5px; cursor: pointer; color: #475569; flex-shrink: 0; align-self: flex-end; }}
  .filter-clear-btn:hover {{ background: #e2e8f0; }}

  /* Two-panel layout */
  .layout {{ display: flex; flex: 1; min-height: 0; overflow: hidden; }}

  .project-panel {{ width: 320px; min-width: 320px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; overflow: hidden; }}
  .proj-panel-top {{ padding: 10px 12px 8px; border-bottom: 1px solid #f1f5f9; display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }}
  .proj-panel-top .search-box {{ font-size:17px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px; width: 100%; background: #f8fafc; }}
  .proj-panel-top .search-box:focus {{ outline: none; border-color: #6366f1; }}
  .proj-panel-count {{ font-size:15px; color: #94a3b8; padding: 0 2px; display: flex; justify-content: space-between; align-items: center; }}
  .proj-sel-clear {{ font-size:15px; color: #6366f1; cursor: pointer; text-decoration: underline; flex-shrink: 0; }}
  .proj-sel-clear:hover {{ color: #4f46e5; }}

  .proj-list {{ flex: 1; overflow-y: auto; }}
  .proj-item {{ border-bottom: 1px solid #f1f5f9; border-left: 3px solid transparent; transition: border-color 0.1s; }}
  .proj-item.selected {{ background: #eef2ff; border-left-color: #6366f1; }}
  .proj-item-header {{ padding: 10px 14px 10px 13px; cursor: pointer; transition: background 0.1s; }}
  .proj-item-header:hover {{ background: #f8fafc; }}
  .proj-item.selected .proj-item-header:hover {{ background: #e0e7ff; }}
  .proj-item-name-row {{ display: flex; align-items: flex-start; gap: 4px; }}
  .proj-arrow {{ display: inline-block; font-size:12px; color: #94a3b8; margin-top: 3px; flex-shrink: 0; transition: transform 0.15s; line-height: 1; }}
  .proj-item.expanded .proj-arrow {{ transform: rotate(90deg); }}
  .proj-item-name {{ font-size:16px; font-weight: 600; color: #1e293b; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 3px; }}
  .proj-item-meta {{ font-size:14px; color: #64748b; line-height: 1.6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .proj-item-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 4px; gap: 6px; }}
  .proj-item-loc {{ font-size:14px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }}
  .proj-item-count {{ font-size:15px; font-weight: 700; color: #6366f1; background: #eef2ff; padding: 2px 7px; border-radius: 12px; flex-shrink: 0; white-space: nowrap; }}
  .proj-docs {{ display: none; border-top: 1px solid #e2e8f0; }}
  .proj-item.expanded .proj-docs {{ display: block; }}
  .proj-doc-item {{ display: flex; align-items: center; gap: 8px; padding: 6px 12px 6px 26px; cursor: pointer; border-bottom: 1px solid #f1f5f9; background: #fafbff; transition: background 0.1s; }}
  .proj-doc-item:last-child {{ border-bottom: none; }}
  .proj-doc-item:hover {{ background: #eef2ff; }}
  .proj-doc-item.selected {{ background: #e0e7ff; }}
  .proj-doc-title {{ font-size:14px; color: #475569; line-height: 1.4; flex: 1; min-width: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
  .proj-doc-count {{ font-size:14px; font-weight: 700; color: #818cf8; background: #eef2ff; padding: 1px 5px; border-radius: 10px; flex-shrink: 0; white-space: nowrap; }}

  .records-panel {{ flex: 1; overflow-y: auto; display: flex; flex-direction: column; padding: 16px 20px; gap: 0; min-width: 0; }}

  /* Compat: search-box used in proj-panel-top */
  .search-box {{ font-size:17px; padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 6px; width: 100%; background: #f8fafc; }}
  .search-box:focus {{ outline: none; border-color: #6366f1; }}

  .results-header {{ font-size:17px; color: #64748b; margin-bottom: 14px; }}
  .results-header strong {{ color: #1e293b; }}

  /* Cards */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px; }}
  .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; display: flex; flex-direction: column; gap: 10px; }}
  .card:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-color: #c7d2fe; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .card-id {{ font-size:14px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; white-space: nowrap; }}
  .card-year {{ font-size:14px; color: #94a3b8; white-space: nowrap; }}
  .card-project {{ font-size:17px; font-weight: 600; color: #1e293b; line-height: 1.4; }}
  .card-source {{ font-size:14px; color: #94a3b8; line-height: 1.4; margin-top: 2px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
  .card-chips {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }}
  .chip {{ font-size:14px; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; color: white; }}
  .chip-scale {{ background: #0891b2; }}
  .chip-tech  {{ background: #7c3aed; }}
  .card-what {{ font-size:16px; color: #475569; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
  .card-footer {{ display: flex; flex-wrap: wrap; gap: 6px; padding-top: 8px; border-top: 1px solid #f1f5f9; }}
  .card-meta-item {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
  .card-meta-label {{ font-size:13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }}
  .badge {{ font-size:14px; font-weight: 600; padding: 2px 8px; border-radius: 20px; color: white;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; display: inline-block; }}

  /* Modal */
  .overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; align-items: center; justify-content: center; padding: 24px; }}
  .overlay.active {{ display: flex; }}
  .modal {{ background: white; border-radius: 14px; width: 100%; max-width: 760px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }}
  .modal-header {{ padding: 20px 24px 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; position: sticky; top: 0; background: white; z-index: 1; }}
  .modal-title {{ font-size:20px; font-weight: 700; color: #0f172a; line-height: 1.4; }}
  .modal-sub {{ font-size:16px; color: #64748b; margin-top: 4px; }}
  .close-btn {{ font-size:24px; color: #94a3b8; cursor: pointer; line-height: 1; flex-shrink: 0; padding: 4px; }}
  .close-btn:hover {{ color: #1e293b; }}
  .modal-body {{ padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; }}
  .modal-section {{ display: flex; flex-direction: column; gap: 6px; }}
  .modal-section-label {{ font-size:14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; }}
  .modal-section-value {{ font-size:18px; color: #1e293b; line-height: 1.6; }}
  .modal-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .excerpt {{ background: #f8fafc; border-left: 3px solid #6366f1; padding: 12px 14px; border-radius: 0 8px 8px 0; font-size:17px; color: #374151; line-height: 1.7; font-style: italic; }}
  .modal-links {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .link-btn {{ font-size:16px; font-weight: 600; padding: 8px 14px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
  .link-btn-primary {{ background: #6366f1; color: white; }}
  .link-btn-primary:hover {{ background: #4f46e5; }}
  .link-btn-secondary {{ background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
  .link-btn-secondary:hover {{ background: #e2e8f0; }}
  .confidence-note {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 12px; font-size:16px; color: #92400e; line-height: 1.6; }}
  .modal-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{ font-size:14px; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; color: white; display: inline-block; }}
  .hidden {{ display: none !important; }}

  /* ── Synthesis ── */
  .synth-btn {{ font-size:16px; font-weight: 600; padding: 6px 14px; border-radius: 6px;
               background: #6366f1; color: white; border: none; cursor: pointer; margin-left: 12px; }}
  .synth-btn:hover {{ background: #4f46e5; }}
  .synth-btn:disabled {{ background: #a5b4fc; cursor: default; }}
  .synth-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 200;
                   align-items: center; justify-content: center; padding: 24px; }}
  .synth-overlay.active {{ display: flex; }}
  .synth-modal {{ background: white; border-radius: 14px; width: 100%; max-width: 820px;
                 max-height: 88vh; display: flex; flex-direction: column;
                 box-shadow: 0 20px 60px rgba(0,0,0,0.25); }}
  .synth-header {{ padding: 18px 22px 14px; border-bottom: 1px solid #e2e8f0; display: flex;
                  justify-content: space-between; align-items: center; flex-shrink: 0; }}
  .synth-title {{ font-size:19px; font-weight: 700; color: #0f172a; }}
  .synth-meta {{ font-size:15px; color: #94a3b8; margin-top: 3px; }}
  .synth-body {{ padding: 20px 24px; overflow-y: auto; flex: 1; }}
  .synth-text {{ font-size:17px; color: #1e293b; line-height: 1.8; }}
  .synth-text h1 {{ font-size:21px; font-weight: 700; margin: 18px 0 8px; color: #0f172a; }}
  .synth-text h2 {{ font-size:19px; font-weight: 700; margin: 16px 0 6px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
  .synth-text h3 {{ font-size:17px; font-weight: 700; margin: 12px 0 4px; color: #1e293b; }}
  .synth-text p {{ margin: 6px 0; }}
  .synth-text ul, .synth-text ol {{ margin: 6px 0 6px 20px; }}
  .synth-text li {{ margin: 3px 0; }}
  .synth-text strong {{ font-weight: 700; color: #0f172a; }}
  .synth-text hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }}
  .synth-text code {{ font-family: monospace; font-size:16px; background: #f1f5f9; padding: 1px 4px; border-radius: 3px; }}
  .synth-cursor {{ display: inline-block; width: 2px; height: 14px; background: #6366f1;
                  animation: blink 0.8s step-end infinite; vertical-align: middle; margin-left: 2px; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  .synth-key-form {{ display: flex; flex-direction: column; gap: 10px; padding: 20px 0; }}
  .synth-key-input {{ font-size:17px; padding: 9px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
                     width: 100%; font-family: monospace; }}
  .synth-key-input:focus {{ outline: none; border-color: #6366f1; }}
  .synth-key-btn {{ font-size:17px; font-weight: 600; padding: 9px 18px; background: #6366f1; color: white;
                   border: none; border-radius: 8px; cursor: pointer; align-self: flex-start; }}
  .synth-key-btn:hover {{ background: #4f46e5; }}

  /* Record ID links & popup */
  .record-link {{ color: #6366f1 !important; text-decoration: underline; text-decoration-style: dotted;
                 cursor: pointer; font-weight: 500; }}
  .record-link:hover {{ color: #4f46e5 !important; }}
  #record-tooltip {{ position: fixed; z-index: 9999; width: 380px; background: white;
                    border: 1px solid #e2e8f0; border-radius: 12px;
                    box-shadow: 0 12px 32px rgba(0,0,0,0.16);
                    max-height: 480px; overflow-y: auto; display: none; }}
  #record-tooltip .rt-header {{ display: flex; align-items: center; justify-content: space-between;
                               padding: 12px 14px 8px; border-bottom: 1px solid #f1f5f9; position: sticky; top: 0; background: white; z-index: 1; }}
  #record-tooltip .rt-id {{ font-size:14px; color: #6366f1; font-weight: 700; letter-spacing: .5px; }}
  #record-tooltip .rt-close {{ font-size:18px; color: #94a3b8; cursor: pointer; line-height: 1; padding: 2px 4px; }}
  #record-tooltip .rt-close:hover {{ color: #475569; }}
  #record-tooltip .rt-body {{ padding: 10px 14px 14px; font-size:16px; line-height: 1.6; display: flex; flex-direction: column; gap: 6px; }}
  #record-tooltip .rt-project {{ font-weight: 700; color: #1e293b; font-size:17px; }}
  #record-tooltip .rt-chips {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  #record-tooltip .rt-what {{ color: #334155; }}
  #record-tooltip .rt-lesson {{ color: #475569; font-style: italic; }}
  #record-tooltip .rt-excerpt {{ font-size:15px; color: #64748b; background: #f8fafc;
                                border-left: 3px solid #e2e8f0; padding: 6px 8px; border-radius: 0 4px 4px 0; }}
  #record-tooltip .rt-footer {{ display: flex; flex-wrap: wrap; gap: 6px; padding-top: 4px; border-top: 1px solid #f1f5f9; }}
  #record-tooltip .rt-meta {{ font-size:14px; color: #64748b; }}
  #record-tooltip .rt-src {{ font-size:15px; color: #6366f1; text-decoration: none; }}
  #record-tooltip .rt-src:hover {{ text-decoration: underline; }}

  /* Reports tab */
  .rep-list {{ display: flex; flex-direction: column; gap: 12px; padding: 24px; max-width: 900px; }}
  .rep-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px;
              padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; }}
  .rep-card-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }}
  .rep-card-title {{ font-size:18px; font-weight: 700; color: #1e293b; cursor: pointer; }}
  .rep-card-title:hover {{ color: #6366f1; }}
  .rep-card-meta {{ font-size:15px; color: #94a3b8; }}
  .rep-card-summary {{ font-size:16px; color: #475569; line-height: 1.5; }}
  .rep-card-actions {{ display: flex; gap: 8px; flex-shrink: 0; }}
  .rep-action-btn {{ font-size:15px; padding: 4px 10px; border-radius: 5px; border: 1px solid #e2e8f0;
                    background: #f8fafc; color: #475569; cursor: pointer; white-space: nowrap; }}
  .rep-action-btn:hover {{ background: #f1f5f9; }}
  .rep-empty {{ padding: 48px 24px; color: #94a3b8; font-size:18px; text-align: center; }}

  /* New v1.3 card elements */
  .card-lesson {{
    font-size:15px; color: #166534; background: #f0fdf4;
    border-left: 3px solid #22c55e; padding: 6px 8px; border-radius: 4px;
    line-height: 1.5;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .card-top-right {{ display: flex; align-items: center; gap: 6px; }}
  .card-src-btn {{
    font-size:14px; color: #6366f1; text-decoration: none;
    padding: 2px 5px; border: 1px solid #c7d2fe; border-radius: 4px; line-height: 1.4;
  }}
  .card-src-btn:hover {{ background: #eef2ff; }}
  .lesson-value {{ color: #166534; background: #f0fdf4; padding: 8px 10px; border-radius: 6px;
                  border-left: 3px solid #22c55e; line-height: 1.6; }}
  .qa-excerpt {{ background: #fefce8; border-left: 3px solid #ca8a04; padding: 10px 14px;
                border-radius: 0 8px 8px 0; font-size:17px; color: #374151; line-height: 1.7;
                font-style: italic; }}
  .src-link {{
    display: inline-block; font-size:15px; font-weight: 600; padding: 5px 10px;
    border-radius: 6px; text-decoration: none; margin-right: 6px; margin-top: 4px;
    background: #6366f1; color: white;
  }}
  .src-link:hover {{ opacity: 0.85; }}
  .src-link-md   {{ background: #0891b2; }}
  .src-link-kb   {{ background: #64748b; }}
  .src-link-proj {{ background: #7c3aed; }}
  .corroboration-badge {{
    font-size:14px; font-weight: 700; color: #0891b2;
    background: #e0f2fe; border: 1px solid #bae6fd;
    padding: 2px 6px; border-radius: 12px; white-space: nowrap;
  }}

  /* ── Project summary panel ── */
  .proj-summary {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; display: none; }}
  .proj-summary.visible {{ display: block; }}
  .proj-summary-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 14px; }}
  .proj-summary-title {{ font-size:19px; font-weight: 700; color: #0f172a; }}
  .proj-meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 5px; }}
  .proj-meta-tag {{ font-size:15px; padding: 2px 8px; border-radius: 12px; background: #f1f5f9; color: #475569; font-weight: 500; }}
  .coverage-strip {{ display: flex; gap: 20px; font-size:16px; color: #64748b; flex-shrink: 0; padding-top: 2px; }}
  .coverage-strip strong {{ color: #0f172a; }}
  .phase-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; }}
  .phase-col {{ display: flex; flex-direction: column; gap: 4px; }}
  .phase-col-label {{ font-size:13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: #94a3b8; line-height: 1.3; min-height: 26px; display: flex; align-items: flex-end; }}
  .phase-dots {{ display: flex; flex-wrap: wrap; gap: 3px; min-height: 18px; padding: 5px 0 2px; border-top: 2px solid #f1f5f9; }}
  .phase-dots.has-dots {{ border-top-color: #cbd5e1; }}
  .phase-dot {{ width: 10px; height: 10px; border-radius: 50%; cursor: pointer; flex-shrink: 0; transition: transform 0.1s; }}
  .phase-dot:hover {{ transform: scale(1.4); }}
  .phase-empty-msg {{ font-size:14px; color: #e2e8f0; padding-top: 3px; }}

  /* ── Pagination ── */
  .pagination {{ display: flex; align-items: center; gap: 10px; padding: 12px 0 4px; }}
  .page-btn {{ font-size:16px; font-weight: 600; padding: 5px 12px; border: 1px solid #e2e8f0;
              border-radius: 6px; background: #f8fafc; cursor: pointer; color: #475569; }}
  .page-btn:hover {{ background: #eef2ff; border-color: #c7d2fe; color: #6366f1; }}
  .page-btn:disabled {{ opacity: 0.35; cursor: default; pointer-events: none; }}
  .page-info {{ font-size:16px; color: #64748b; }}

  /* ── Analysis tab ── */
  .an-page {{ display: flex; flex-direction: column; height: calc(100vh - 108px); overflow: hidden; }}
  .an-stats {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 32px; display: flex; gap: 32px; flex-shrink: 0; }}
  .an-grid {{ padding: 20px 24px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; overflow-y: auto; flex: 1; }}
  .an-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }}
  .an-card.an-wide {{ grid-column: span 2; }}
  .an-card-title {{ font-size:16px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.4px; }}
  .an-card-sub {{ font-size:15px; color: #94a3b8; }}
  .an-card canvas {{ max-height: 280px; }}
  .an-card.an-wide canvas {{ max-height: 340px; }}
  .rcm-scroll {{ overflow-x: auto; margin-top: 8px; }}
  .rcm-table {{ border-collapse: collapse; width: 100%; font-size:16px; }}
  .rcm-table th {{ background: #f8fafc; padding: 8px 10px; text-align: left; font-size:14px;
                  font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.4px;
                  border-bottom: 2px solid #e2e8f0; white-space: nowrap; }}
  .rcm-table td {{ padding: 7px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; font-size:16px; }}
  .rcm-table tr:last-child td {{ border-bottom: none; }}
  .rcm-table tr:hover td {{ background: #fafbff; }}
  .rcm-num {{ text-align: center; white-space: nowrap; }}
  .rcm-rate {{ font-weight: 700; }}
  .rcm-fm {{ color: #475569; font-size:15px; }}
  .rcm-empty {{ color: #94a3b8; text-align: center; padding: 16px; }}
  .hm-table {{ border-collapse: collapse; font-size: 14px; }}
  .hm-table th {{ background: #f8fafc; padding: 6px 8px; font-size: 13px; font-weight: 700;
                  color: #475569; text-transform: uppercase; letter-spacing: 0.3px;
                  border: 1px solid #e2e8f0; white-space: nowrap; text-align: center; }}
  .hm-table th.hm-row-hdr {{ text-align: left; min-width: 140px; }}
  .hm-table td {{ padding: 6px 8px; border: 1px solid #e2e8f0; text-align: center;
                  font-weight: 700; font-size: 14px; min-width: 70px; cursor: default; }}
  .hm-table td.hm-row-hdr {{ text-align: left; font-weight: 600; color: #1e293b; background: #f8fafc; white-space: nowrap; }}
  .hm-table td.hm-empty {{ background: #f8fafc; color: #cbd5e1; font-weight: 400; font-size: 12px; }}

  /* ── Benchmarks tab ── */
  .bench-layout {{ display: flex; height: calc(100vh - 120px); }}
  .bench-nav {{ width: 220px; min-width: 220px; background: white; border-right: 1px solid #e2e8f0;
               padding: 16px 12px; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; }}
  .bench-nav-btn {{ font-size:16px; font-weight: 600; padding: 10px 12px; border-radius: 8px;
                   border: 1px solid #e2e8f0; background: #f8fafc; cursor: pointer; text-align: left;
                   color: #374151; display: flex; justify-content: space-between; align-items: center; }}
  .bench-nav-btn:hover {{ background: #eef2ff; border-color: #c7d2fe; }}
  .bench-nav-btn.active {{ background: #6366f1; color: white; border-color: #6366f1; }}
  .bench-main {{ flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }}
  .bench-header {{ display: flex; flex-direction: column; gap: 3px; }}
  .bench-title {{ font-size:20px; font-weight: 700; color: #0f172a; }}
  .bench-desc {{ font-size:16px; color: #64748b; }}
  .bench-chart-wrap {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px;
                       position: relative; }}
  .bench-chart-wrap canvas {{ max-height: 300px; }}
  .bench-controls {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .bench-search {{ font-size:17px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
                  width: 260px; background: #f8fafc; }}
  .bench-search:focus {{ outline: none; border-color: #6366f1; }}
  .bench-filter {{ font-size:17px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; color: #1e293b; }}
  .bench-count {{ font-size:16px; color: #64748b; margin-left: auto; }}
  .bench-table-wrap {{ overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 10px; }}
  .bench-table {{ border-collapse: collapse; width: 100%; font-size:16px; }}
  .bench-table th {{ background: #f8fafc; padding: 10px 12px; text-align: left; font-size:15px; font-weight: 700;
                    color: #475569; text-transform: uppercase; letter-spacing: 0.5px;
                    border-bottom: 1px solid #e2e8f0; white-space: nowrap; cursor: pointer; user-select: none; }}
  .bench-table th:hover {{ background: #eef2ff; color: #6366f1; }}
  .bench-table td {{ padding: 9px 12px; border-bottom: 1px solid #f1f5f9; color: #1e293b; vertical-align: top; }}
  .bench-table tr:last-child td {{ border-bottom: none; }}
  .bench-table tr:hover td {{ background: #fafbff; }}
  .col-notes {{ max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #64748b; cursor: help; }}
  .col-value {{ font-weight: 600; color: #0f172a; }}
  .col-actual {{ font-weight: 600; color: #16a34a; }}
  .col-empty {{ color: #cbd5e1; }}
</style>
</head>
<body>

<header>
  <h1>ARENA Delivery Insights</h1>
  <span>Prototype · {n} records · {n_projects_covered} of {portfolio_size} ARENA projects</span>
</header>

<div class="filter-bar">
    <div class="fi fi-search"><label>Search records</label><input id="search" type="text" placeholder="Keywords…"></div>
    <div class="fi"><label>ARENA category</label><select id="f-category"><option value="">All categories</option>{options(arena_categories)}</select></div>
    <div class="fi"><label>Activity type</label><select id="f-activity"><option value="">All activities</option>{options(activity_types)}</select></div>
    <div class="fi"><label>Failure mode</label><select id="f-failure"><option value="">All failures</option>{options(failure_modes)}</select></div>
    <div class="fi"><label>Proponent</label><select id="f-proponent"><option value="">All proponents</option>{options(proponent_types)}</select></div>
    <div class="fi"><label>Lifecycle phase</label><select id="f-phase"><option value="">All phases</option>{options(lifecycle_phases)}</select></div>
    <div class="fi"><label>Severity</label><select id="f-severity"><option value="">All severities</option>{options(severity_levels)}</select></div>
    <div class="fi"><label>Consortium</label><select id="f-consortium"><option value="">All</option><option value="true">Consortium only</option><option value="false">Non-consortium</option></select></div>
    <div class="fi"><label>Transferability</label><select id="f-transferability"><option value="">All</option>{options(transferability_vals)}</select></div>
    <div class="fi"><label>QA grounding</label><select id="f-qa"><option value="">All</option>{options(qa_verdicts)}</select></div>
    <div class="fi"><label>QA classification</label><select id="f-qa-class"><option value="">All</option>{options(qa_classifications)}</select></div>
    <button class="filter-clear-btn" onclick="clearFilters()">Clear</button>
  </div>
<div class="tabs">
  <div class="tab active" id="tab-records" onclick="switchTab('records')">Delivery Records</div>
  <div class="tab" id="tab-analysis" onclick="switchTab('analysis')">Analysis</div>
  <div class="tab" id="tab-benchmarks" onclick="switchTab('benchmarks')">Benchmarks</div>
  <div class="tab" id="tab-reports" onclick="switchTab('reports')">Reports</div>
</div>

<div id="record-tooltip" style="display:none"></div>

<!-- ── Delivery Records tab ── -->
<div class="tab-content active" id="tc-records" style="flex-direction:column">
  <div class="stats">
    <div class="stat"><span class="stat-value" id="stat-shown">{n}</span><span class="stat-label">Records shown</span></div>
    <div class="stat"><span class="stat-value">{n_projects_covered} <span style="font-size:18px;color:#64748b">of {portfolio_size} ({portfolio_pct})</span></span><span class="stat-label">ARENA portfolio covered</span></div>
    <div class="stat"><span class="stat-value">{n_failures}</span><span class="stat-label">With failure mode</span></div>
    <div class="stat"><span class="stat-value">{len(records) - n_failures}</span><span class="stat-label">No major failure</span></div>
  </div>
  <div class="layout">
    <div class="project-panel">
      <div class="proj-panel-top">
        <input class="search-box" id="proj-search" type="text" placeholder="Search {n_projects_covered} projects…" oninput="renderProjectList()">
        <div class="proj-panel-count" id="proj-count-badge"></div>
      </div>
      <div class="proj-list" id="proj-list"></div>
    </div>

    <div class="records-panel">
      <div id="proj-summary" class="proj-summary">
        <div class="proj-summary-header">
          <div>
            <div class="proj-summary-title" id="ps-title"></div>
            <div class="proj-meta" id="ps-meta"></div>
          </div>
          <div class="coverage-strip" id="ps-coverage"></div>
        </div>
        <div class="phase-grid" id="ps-phases"></div>
      </div>
      <div class="results-header" style="display:flex;align-items:center;padding-bottom:8px">
        <span><strong id="count-label">{n} records</strong> · click any card to view detail</span>
        <select id="synth-mode" style="font-size:16px;padding:5px 8px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;color:#475569;margin-left:12px;cursor:pointer">
          <option value="brief">Brief summary</option>
          <option value="short">Short report</option>
          <option value="detailed" selected>Detailed report</option>
        </select>
        <button class="synth-btn" id="synth-btn" onclick="openSynth()">Synthesise</button>
      </div>
      <div style="padding-bottom:8px">
        <textarea id="synth-context" rows="2"
          placeholder="Optional: add focus or context for the synthesis — e.g. 'focus on grid connection risks' or 'I need evidence to assess a hydrogen proposal at approvals stage'"
          style="width:100%;font-size:16px;padding:7px 10px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;color:#1e293b;resize:vertical;font-family:inherit;box-sizing:border-box"></textarea>
      </div>
      <div class="pagination">
        <button class="page-btn" id="btn-prev" onclick="changePage(-1)">&#8592; Prev</button>
        <span class="page-info" id="page-info"></span>
        <button class="page-btn" id="btn-next" onclick="changePage(1)">Next &#8594;</button>
      </div>
      <div class="cards" id="cards"></div>
    </div>
  </div>
</div>

<!-- ── Analysis tab ── -->
<div class="tab-content" id="tc-analysis">
  <div class="an-page">
    <div id="an-warn" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:8px 14px;margin-bottom:10px;font-size:16px;color:#92400e"></div>
    <div class="an-stats" id="an-stats"></div>
    <div class="an-grid">
      <div class="an-card an-wide">
        <div class="an-card-title">Failure mode by lifecycle phase</div>
        <div class="an-card-sub">Where in delivery do different failure types cluster?</div>
        <canvas id="an-phase-fm"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Failure mode frequency</div>
        <div class="an-card-sub">Most common failure types across all records</div>
        <canvas id="an-fm-freq"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Failure rate by ARENA category</div>
        <div class="an-card-sub">% of records with any failure mode, by delivery archetype</div>
        <canvas id="an-type-fail"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Failure modes by ARENA category</div>
        <div class="an-card-sub">Top 10 categories — stacked by failure type</div>
        <canvas id="an-tech-fm"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Issue severity distribution</div>
        <div class="an-card-sub">Magnitude of delivery issues across all records</div>
        <canvas id="an-severity"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Severity % by failure mode</div>
        <div class="an-card-sub">Major+critical as % of adverse records · Dashed line = corpus baseline</div>
        <canvas id="an-sev-ratio"></canvas>
      </div>
      <div class="an-card an-wide">
        <div class="an-card-title">Issue severity by lifecycle phase</div>
        <div class="an-card-sub">Does severity increase as projects progress through delivery?</div>
        <canvas id="an-phase-sev"></canvas>
      </div>
      <div class="an-card an-wide">
        <div class="an-card-title">Failure mode co-occurrence</div>
        <div class="an-card-sub">Rows = primary failure mode · Columns = secondary failure mode · Cell = record count</div>
        <div id="an-cooccur" style="overflow-x:auto;margin-top:4px"></div>
      </div>
      {matrix_html}
    </div>
  </div>
</div>

<!-- ── Benchmarks tab ── -->
<div class="tab-content" id="tc-benchmarks">
  <div class="bench-layout">
    <div class="bench-nav" id="bench-nav"></div>
    <div class="bench-main" id="bench-main">
      <div style="color:#94a3b8;padding:40px;font-size:18px;text-align:center">
        Select a dataset from the left panel.
      </div>
    </div>
  </div>
</div>

<!-- Modal -->
<div class="overlay" id="overlay" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="m-title"></div>
        <div class="modal-sub" id="m-sub"></div>
      </div>
      <span class="close-btn" onclick="closeModalDirect()">✕</span>
    </div>
    <div class="modal-body">
      <div class="modal-section">
        <div class="modal-section-label">What happened</div>
        <div class="modal-section-value" id="m-what"></div>
      </div>
      <div id="m-lesson-wrap" class="modal-section">
        <div class="modal-section-label">Lesson learnt</div>
        <div class="modal-section-value lesson-value" id="m-lesson"></div>
      </div>
      <div id="m-excerpt-wrap" class="modal-section">
        <div class="modal-section-label">Evidence excerpt</div>
        <div class="excerpt" id="m-excerpt"></div>
      </div>
      <div class="modal-grid">
        <div class="modal-section">
          <div class="modal-section-label">Failure mode &amp; severity</div>
          <div id="m-failure"></div>
        </div>
        <div class="modal-section">
          <div class="modal-section-label">Lifecycle phase</div>
          <div class="modal-section-value" id="m-phase"></div>
        </div>
      </div>
      <div id="m-intervention-wrap" class="modal-section">
        <div class="modal-section-label">Intervention / resolution</div>
        <div class="modal-section-value" id="m-intervention"></div>
      </div>
      <div class="modal-section">
        <div class="modal-section-label">Classification</div>
        <div class="modal-tags" id="m-tags"></div>
      </div>
      <div id="m-qa-wrap" class="modal-section">
        <div class="modal-section-label">QA verification</div>
        <div id="m-qa-verdict"></div>
        <div class="qa-excerpt" id="m-qa-text" style="margin-top:8px"></div>
        <div style="font-size:16px;color:#64748b;margin-top:6px" id="m-qa-note"></div>
      </div>
      <div id="m-corr-wrap" class="modal-section">
        <div class="modal-section-label">Corroboration</div>
        <div class="modal-section-value" id="m-corr"></div>
        <div style="font-size:16px;color:#64748b;margin-top:4px" id="m-corr-titles"></div>
      </div>
      <div id="m-note-wrap" class="modal-section">
        <div class="modal-section-label">Confidence note</div>
        <div class="confidence-note" id="m-note"></div>
      </div>
      <div class="modal-section">
        <div class="modal-section-label">Source</div>
        <div class="modal-links" id="m-links"></div>
      </div>
    </div>
  </div>
</div>

<!-- Synthesis modal -->
<div class="synth-overlay" id="synth-overlay" onclick="if(event.target===this)closeSynth()">
  <div class="synth-modal">
    <div class="synth-header">
      <div>
        <div class="synth-title" id="synth-title">Synthesising insights…</div>
        <div class="synth-meta" id="synth-meta"></div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
        <button class="synth-btn" id="synth-copy-btn" onclick="synthCopy()" style="display:none;background:#475569">Copy</button>
        <button class="synth-btn" id="synth-save-btn" onclick="synthSave()" style="display:none;background:#059669">Save</button>
        <span class="close-btn" onclick="closeSynth()">✕</span>
      </div>
    </div>
    <div class="synth-body" id="synth-body"></div>
  </div>
</div>

<!-- ── Reports tab ── -->
<div class="tab-content" id="tc-reports" style="flex-direction:column">
  <div class="rep-list" id="rep-list"></div>
</div>

<script>
const RECORDS = {data_json};
const FM_COLOURS = {fm_colours};
const IS_COLOURS = {is_colours};
const QA_COLOURS = {qa_colours};
Chart.defaults.font.size = 14;
Chart.defaults.plugins.legend.labels.font = {{ size: 14 }};
Chart.defaults.plugins.tooltip.bodyFont = {{ size: 14 }};
Chart.defaults.plugins.tooltip.titleFont = {{ size: 14 }};
const ARENA_ROOT = '{arena_root}';
const BENCHMARKS = {benchmarks_json};

// ── Tab switching ──────────────────────────────────────────────
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('tc-' + name).classList.add('active');
  if (name === 'analysis') {{
    const f = getFilters();
    const filtered = RECORDS.filter(r => matchesDimFilters(r, f));
    renderAnalysis(filtered);
  }}
  if (name === 'reports') renderReports();
}}

// ── Record ID tooltip ──────────────────────────────────────────
const RECORD_MAP = new Map(RECORDS.map(r => [r.record_id, r]));

function linkifyRecordIds(container) {{
  let html = container.innerHTML;
  // Expand partial citations: "ARENA-DLV-N, -M" and ranges "ARENA-DLV-N through -M"
  html = html.replace(
    /\\bARENA-DLV-(\\d+)((?:\\s+through\\s+-\\d+|(?:\\s*,\\s*-\\d+(?:\\s+through\\s+-\\d+)?))+)/g,
    function(match, firstNum, tail) {{
      var ids = ['ARENA-DLV-' + firstNum];
      var immRange = /^\\s+through\\s+-(\\d+)/.exec(tail);
      var rest = immRange ? tail.slice(immRange[0].length) : tail;
      if (immRange) {{
        var s = parseInt(firstNum), e = parseInt(immRange[1]);
        for (var i = s + 1; i <= Math.min(e, s + 50); i++) ids.push('ARENA-DLV-' + i);
      }}
      var itemRe = /,\\s*-(\\d+)(?:\\s+through\\s+-(\\d+))?/g;
      var mx;
      while ((mx = itemRe.exec(rest)) !== null) {{
        if (mx[2]) {{
          var sa = parseInt(mx[1]), ea = parseInt(mx[2]);
          for (var j = sa; j <= Math.min(ea, sa + 50); j++) ids.push('ARENA-DLV-' + j);
        }} else {{
          ids.push('ARENA-DLV-' + mx[1]);
        }}
      }}
      return ids.join(', ');
    }}
  );
  container.innerHTML = html.replace(
    /\\b(ARENA-DLV-\\d{{4,}})\\b/g,
    (match, id) => `<span class="record-link" data-id="${{id}}">${{id}}</span>`
  );
}}

const _tooltip = document.getElementById('record-tooltip');
let _tooltipAnchor = null;

function closeTooltip() {{
  _tooltip.style.display = 'none';
  _tooltipAnchor = null;
}}

function positionTooltip(anchor) {{
  const rect = anchor.getBoundingClientRect();
  const vp = {{ w: window.innerWidth, h: window.innerHeight }};
  const popH = 480, popW = 380;
  const left = Math.min(rect.left, vp.w - popW - 8);
  const below = rect.bottom + 8 + popH <= vp.h;
  const top = below ? rect.bottom + 8 : Math.max(8, rect.top - popH - 8);
  _tooltip.style.left = Math.max(8, left) + 'px';
  _tooltip.style.top = top + 'px';
}}

document.addEventListener('click', e => {{
  const link = e.target.closest('.record-link');
  if (link) {{
    e.stopPropagation();
    if (_tooltipAnchor === link) {{ closeTooltip(); return; }}
    _tooltipAnchor = link;
    const r = RECORD_MAP.get(link.dataset.id);
    if (!r) return;
    const fm = r.failure_mode || '—';
    const fmCol = FM_COLOURS[fm] || '#64748b';
    const isCol = IS_COLOURS[r.issue_severity] || '#94a3b8';
    const srcUrl = buildSrcUrl(r);
    let chips = '';
    if (r.arena_category && r.arena_category.length) r.arena_category.forEach(c => {{ chips += `<span class="chip chip-tech">${{c}}</span>`; }});
    if (r.activity_type) chips += `<span class="chip chip-scale">${{r.activity_type}}</span>`;
    const year = r.publish_date ? r.publish_date.slice(0,4) : (r.kb_year || '');
    _tooltip.innerHTML = `
      <div class="rt-header">
        <span class="rt-id">${{r.record_id}}</span>
        <span class="rt-close" onclick="closeTooltip()">✕</span>
      </div>
      <div class="rt-body">
        <div class="rt-project">${{r.project_name || r.kb_associated_project || ''}}</div>
        ${{chips ? `<div class="rt-chips">${{chips}}</div>` : ''}}
        <div class="rt-what">${{r.what_happened || ''}}</div>
        ${{r.lesson_learnt ? `<div class="rt-lesson">${{r.lesson_learnt}}</div>` : ''}}
        ${{r.evidence_excerpt ? `<div class="rt-excerpt">"${{r.evidence_excerpt}}"</div>` : ''}}
        <div class="rt-footer">
          ${{r.lifecycle_phase ? `<span class="badge" style="background:#64748b">${{r.lifecycle_phase}}</span>` : ''}}
          ${{fm !== '—' ? `<span class="badge" style="background:${{fmCol}}">${{fm}}</span>` : ''}}
          ${{r.issue_severity ? `<span class="badge" style="background:${{isCol}}">${{r.issue_severity}}</span>` : ''}}
          ${{r.proponent_type ? `<span class="badge" style="background:#0891b2">${{r.proponent_type}}</span>` : ''}}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:4px">
          ${{year ? `<span class="rt-meta">${{year}}</span>` : '<span></span>'}}
          ${{srcUrl ? `<a class="rt-src" href="${{srcUrl}}" target="_blank" onclick="event.stopPropagation()">Open source ↗</a>` : ''}}
        </div>
      </div>`;
    _tooltip.style.display = 'block';
    positionTooltip(link);
    return;
  }}
  if (!e.target.closest('#record-tooltip')) closeTooltip();
}});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeTooltip(); }});

// ── Reports storage ────────────────────────────────────────────
function loadReports() {{
  try {{ return JSON.parse(localStorage.getItem('arena_reports') || '[]'); }}
  catch(e) {{ return []; }}
}}
function saveReports(list) {{
  localStorage.setItem('arena_reports', JSON.stringify(list));
}}
function saveReport(report) {{
  const list = loadReports();
  list.unshift(report);
  saveReports(list);
  // update Reports tab badge count
  const tab = document.getElementById('tab-reports');
  if (tab) tab.textContent = `Reports (${{list.length}})`;
}}
function deleteReport(id) {{
  const list = loadReports().filter(r => r.id !== id);
  saveReports(list);
  renderReports();
  const tab = document.getElementById('tab-reports');
  if (tab) tab.textContent = list.length ? `Reports (${{list.length}})` : 'Reports';
}}

function reportUrl(id) {{
  return window.location.origin + window.location.pathname + '#report-' + id;
}}

function openReport(id) {{
  const list = loadReports();
  const rep = list.find(r => r.id === id);
  if (!rep) return;
  const modeLabel = rep.mode === 'brief' ? 'Brief Summary' : rep.mode === 'short' ? 'Short Report' : 'Detailed Report';
  document.getElementById('synth-title').textContent = modeLabel;
  document.getElementById('synth-meta').textContent =
    `${{rep.recordCount}} records · ${{rep.filterDesc}} · ${{new Date(rep.date).toLocaleDateString()}}`;
  const body = document.getElementById('synth-body');
  body.innerHTML = '<div class="synth-text" id="synth-stream"></div>';
  const streamEl = document.getElementById('synth-stream');
  streamEl.innerHTML = marked.parse(rep.text);
  linkifyRecordIds(streamEl);
  _synthText = rep.text;
  document.getElementById('synth-copy-btn').style.display = '';
  document.getElementById('synth-save-btn').style.display = '';
  const overlay = document.getElementById('synth-overlay');
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
  history.replaceState(null, '', '#report-' + id);
}}

async function renderReports() {{
  const el = document.getElementById('rep-list');
  el.innerHTML = '<div class="rep-empty">Loading…</div>';

  // Fetch server reports
  let serverReports = [];
  try {{
    const res = await fetch('/list-reports');
    serverReports = await res.json();
  }} catch(e) {{
    // Server unreachable — fall through and show localStorage only
  }}
  const serverIds = new Set(serverReports.map(r => r.id));

  // Merge: server reports + any localStorage reports not yet on server
  const localReports = loadReports();
  const localOnly = localReports.filter(r => !serverIds.has(r.id));

  // Combined list: server reports first (already have URLs), then local-only
  const allReports = [...serverReports, ...localOnly];

  const tab = document.getElementById('tab-reports');
  if (tab) tab.textContent = allReports.length ? `Reports (${{allReports.length}})` : 'Reports';
  if (!allReports.length) {{
    el.innerHTML = '<div class="rep-empty">No reports yet. Generate a synthesis to create one.</div>';
    return;
  }}

  el.innerHTML = allReports.map(rep => {{
    const isLocal = !serverIds.has(rep.id);
    const modeLabel = rep.mode === 'brief' ? 'Brief' : rep.mode === 'short' ? 'Short' : 'Detailed';
    const rawDate = rep.date;
    const dateStr = rawDate ? new Date(typeof rawDate === 'number' ? rawDate : rawDate).toLocaleDateString('en-AU', {{day:'numeric',month:'short',year:'numeric'}}) : '';
    const countStr = rep.recordCount ? `${{rep.recordCount}} records` : '';
    const localLabel = isLocal ? 'Local only' : '';
    const meta = [modeLabel, countStr, dateStr, localLabel].filter(Boolean).join(' · ');
    const safeUrl = (rep.url || '').replace(/"/g, '&quot;');
    const safeId = rep.id.replace(/"/g, '');
    const actions = isLocal
      ? `<button class="rep-action-btn" style="color:#6366f1;font-weight:700" data-permalink="${{safeId}}" onclick="createPermalinkFromList('${{safeId}}',this)">Save permalink</button>`
      : `<button class="rep-action-btn" onclick="window.open('${{safeUrl}}','_blank')">Open</button>
         <button class="rep-action-btn" onclick="navigator.clipboard.writeText('${{safeUrl}}').then(()=>{{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy link',2000)}}).catch(()=>{{}})">Copy link</button>
         <button class="rep-action-btn" style="color:#dc2626" onclick="deleteServerReport('${{safeId}}',this)">Delete</button>`;
    return `<div class="rep-card">
      <div class="rep-card-header">
        <div>
          <div class="rep-card-title">${{rep.filterDesc || '(no description)'}}</div>
          <div class="rep-card-meta">${{meta}}</div>
        </div>
        <div class="rep-card-actions">${{actions}}</div>
      </div>
      ${{rep.summary ? `<div class="rep-card-summary">${{rep.summary}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function createPermalinkFromList(repId, btn) {{
  const list = loadReports();
  const rep = list.find(r => r.id === repId);
  if (!rep) return;
  btn.textContent = 'Saving…';
  btn.disabled = true;
  try {{
    const html = generateReportHtml(rep);
    const res = await fetch('/save-report', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        id: rep.id,
        html,
        meta: {{
          filterDesc:  rep.filterDesc,
          mode:        rep.mode,
          date:        rep.date,
          recordCount: rep.recordCount,
          summary:     rep.summary || '',
        }},
      }}),
    }});
    const data = await res.json();
    await navigator.clipboard.writeText(data.url);
    btn.textContent = 'Link copied!';
    setTimeout(() => renderReports(), 1500);
  }} catch(e) {{
    btn.textContent = 'Error';
    btn.disabled = false;
    console.error(e);
  }}
}}

async function deleteServerReport(id, btn) {{
  if (!confirm('Delete this report from the server? This cannot be undone.')) return;
  btn.disabled = true;
  try {{
    await fetch('/delete-report/' + id, {{ method: 'DELETE' }});
    renderReports();
  }} catch(e) {{
    btn.disabled = false;
    alert('Could not delete report.');
  }}
}}

// ── Delivery Records ──────────────────────────────────────────
function fmColour(v) {{ return FM_COLOURS[v] || '#64748b'; }}
function isColour(v) {{ return IS_COLOURS[v] || '#94a3b8'; }}
function qaColour(v) {{ return QA_COLOURS[v] || '#94a3b8'; }}

function firstPage(source_pages) {{
  if (!source_pages) return null;
  if (Array.isArray(source_pages) && source_pages.length > 0) return source_pages[0];
  if (typeof source_pages === 'number') return source_pages;
  return null;
}}

function buildSrcUrl(r) {{
  if (r.pdf_url) {{
    const pg = firstPage(r.source_pages);
    return pg ? r.pdf_url + '#page=' + pg : r.pdf_url;
  }}
  return r.source_url || '';
}}

function buildMdUrl(r) {{
  if (!r.markdown_filename) return '';
  const base = 'file://' + ARENA_ROOT + '/markdown/all/' + r.markdown_filename;
  if (r.evidence_excerpt) {{
    const frag = encodeURIComponent(r.evidence_excerpt.substring(0, 100));
    return base + '#:~:text=' + frag;
  }}
  return base;
}}

function renderCards(records) {{
  _lastFiltered = records;
  _curPage = 0;
  renderPage();
}}

function renderPage() {{
  const records = _lastFiltered;
  const total = records.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  _curPage = Math.max(0, Math.min(_curPage, totalPages - 1));
  const start = _curPage * PAGE_SIZE;
  const pageRecs = records.slice(start, start + PAGE_SIZE);

  document.getElementById('stat-shown').textContent = total;
  document.getElementById('count-label').textContent = total + ' record' + (total !== 1 ? 's' : '');
  document.getElementById('page-info').textContent =
    total > PAGE_SIZE ? `Page ${{_curPage + 1}} of ${{totalPages}} · showing ${{start + 1}}–${{Math.min(start + PAGE_SIZE, total)}}` : '';
  document.getElementById('btn-prev').disabled = _curPage === 0;
  document.getElementById('btn-next').disabled = _curPage >= totalPages - 1;

  const container = document.getElementById('cards');
  container.innerHTML = '';
  if (total === 0) {{
    container.innerHTML = '<div style="color:#94a3b8;font-size:18px;padding:20px">No records match the current filters.</div>';
    return;
  }}
  pageRecs.forEach(r => {{
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openModal(r);
    const year = r.publish_date ? r.publish_date.slice(0,4) : (r.kb_year || '');
    const fm = r.failure_mode || '—';
    const srcUrl = buildSrcUrl(r);
    const srcBtn = srcUrl
      ? `<a class="card-src-btn" href="${{srcUrl}}" target="_blank" title="Open source" onclick="event.stopPropagation()">↗</a>`
      : '';
    const lessonEl = r.lesson_learnt
      ? `<div class="card-lesson">${{r.lesson_learnt}}</div>`
      : '';
    const corrBadge = (r.corroboration_count > 1)
      ? `<span class="corroboration-badge" title="Corroborated across ${{r.corroboration_count}} source records">×${{r.corroboration_count}}</span>`
      : '';
    // Project-level chips — arena_category + activity_type + consortium flag
    let chips = '';
    if (r.arena_category && r.arena_category.length) r.arena_category.forEach(c => {{ chips += `<span class="chip chip-tech">${{c}}</span>`; }});
    if (r.activity_type) chips += `<span class="chip chip-scale">${{r.activity_type}}</span>`;
    if (r.is_consortium) chips += `<span class="chip" style="background:#fef3c7;color:#92400e;border-color:#fcd34d">Consortium</span>`;
    // Record-level footer items — labelled
    const footerItems = [];
    if (r.lifecycle_phase)  footerItems.push(['Stage',    `<span class="badge" style="background:#64748b;color:white">${{r.lifecycle_phase}}</span>`]);
    if (r.failure_mode)     footerItems.push(['Type',     `<span class="badge" style="background:${{fmColour(fm)}};color:white">${{fm}}</span>`]);
    if (r.issue_severity)   footerItems.push(['Severity', `<span class="badge" style="background:${{isColour(r.issue_severity)}};color:white">${{r.issue_severity}}</span>`]);
    const footerHtml = footerItems.map(([label, badge]) =>
      `<div class="card-meta-item"><span class="card-meta-label">${{label}}</span>${{badge}}</div>`
    ).join('');
    card.innerHTML = `
      <div class="card-top">
        <span class="card-id">${{r.record_id}}</span>
        <div class="card-top-right">${{corrBadge}}<span class="card-year">${{year}}</span>${{srcBtn}}</div>
      </div>
      <div class="card-project">${{r.project_name || r.source_title}}</div>
      ${{r.source_title ? `<div class="card-source">${{r.source_title}}</div>` : ''}}
      ${{chips ? `<div class="card-chips">${{chips}}</div>` : ''}}
      <div class="card-what">${{r.what_happened}}</div>
      ${{lessonEl}}
      <div class="card-footer">${{footerHtml}}</div>`;
    container.appendChild(card);
  }});
}}

const ALL_FILTER_IDS = ['search','f-category','f-activity','f-failure','f-proponent','f-phase','f-severity','f-consortium','f-transferability','f-qa','f-qa-class'];
const PROJECT_SET = new Set(RECORDS.map(r => r.kb_associated_project).filter(Boolean));
const PAGE_SIZE = 50;
let _curPage = 0, _lastFiltered = [];

// ── Project grouping ───────────────────────────────────────────
const PROJECT_GROUPS = new Map();
RECORDS.forEach(r => {{
  const proj = r.kb_associated_project || '(No project)';
  if (!PROJECT_GROUPS.has(proj)) PROJECT_GROUPS.set(proj, []);
  PROJECT_GROUPS.get(proj).push(r);
}});

let _selectedProjects = new Set();
let _expandedProjects = new Set();
let _selectedDoc = null; // {{ proj, title }} | null

function getMostCommon(recs, field) {{
  const counts = {{}};
  recs.forEach(r => {{ if (r[field]) counts[r[field]] = (counts[r[field]] || 0) + 1; }});
  const top = Object.entries(counts).sort((a,b) => b[1]-a[1])[0];
  return top ? top[0] : null;
}}

function renderProjectList() {{
  const search = (document.getElementById('proj-search').value || '').toLowerCase();
  const f = getFilters();

  // Build proj → docs → records map
  const projDocs = new Map();
  RECORDS.forEach(r => {{
    if (!matchesDimFilters(r, f)) return;
    const proj = r.kb_associated_project || '(No project)';
    if (!projDocs.has(proj)) projDocs.set(proj, new Map());
    const title = r.source_title || '(Unknown document)';
    if (!projDocs.get(proj).has(title)) projDocs.get(proj).set(title, []);
    projDocs.get(proj).get(title).push(r);
  }});

  let projects = [...projDocs.entries()].map(([name, docsMap]) => [name, docsMap, [...docsMap.values()].flat()]);
  if (search) projects = projects.filter(([name]) => name.toLowerCase().includes(search));
  projects.sort((a, b) => b[2].length - a[2].length);

  const badge = document.getElementById('proj-count-badge');
  if (badge) {{
    const projCount = projects.length + ' project' + (projects.length !== 1 ? 's' : '');
    if (_selectedDoc) {{
      badge.innerHTML = `<span>${{projCount}}</span><span class="proj-sel-clear" onclick="clearProjectSelection()">1 report selected · clear</span>`;
    }} else if (_selectedProjects.size > 0) {{
      badge.innerHTML = `<span>${{projCount}}</span><span class="proj-sel-clear" onclick="clearProjectSelection()">${{_selectedProjects.size}} selected · clear</span>`;
    }} else {{
      badge.textContent = projCount;
    }}
  }}

  const list = document.getElementById('proj-list');
  list.innerHTML = projects.map(([name, docsMap, recs]) => {{
    const isSelected = _selectedProjects.has(name);
    const isExpanded = _expandedProjects.has(name);
    const isDocSel   = _selectedDoc && _selectedDoc.proj === name;
    const cats = [...new Set(recs.flatMap(r => r.arena_category || []))].join(', ');
    const actType   = getMostCommon(recs, 'activity_type') || '';
    const proponent = getMostCommon(recs, 'proponent_type') || '';
    const isCons    = recs.some(r => r.is_consortium);
    const location  = (recs.find(r => r.location) || {{}}).location || '';
    const safeAttr  = name.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    const meta1 = [cats, actType].filter(Boolean).join(' · ');
    const meta2 = [proponent, isCons ? '(consortium)' : ''].filter(Boolean).join(' · ');

    const docs = [...docsMap.entries()].sort((a, b) => b[1].length - a[1].length);
    const docsHtml = docs.map(([title, drecs]) => {{
      const isSel = isDocSel && _selectedDoc.title === title;
      const safeTitle = title.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      return `<div class="proj-doc-item ${{isSel ? 'selected' : ''}}" data-proj="${{safeAttr}}" data-title="${{safeTitle}}" onclick="event.stopPropagation(); selectDoc(this.dataset.proj, this.dataset.title)">
        <span class="proj-doc-title">${{title}}</span>
        <span class="proj-doc-count">${{drecs.length}}</span>
      </div>`;
    }}).join('');

    const classes = [(isSelected || isDocSel) ? 'selected' : '', isExpanded ? 'expanded' : ''].filter(Boolean).join(' ');
    return `<div class="proj-item ${{classes}}">
      <div class="proj-item-header" data-proj="${{safeAttr}}" onclick="selectProject(this.dataset.proj)">
        <div class="proj-item-name-row">
          <span class="proj-arrow">&#9654;</span>
          <div class="proj-item-name">${{name}}</div>
        </div>
        ${{meta1 ? `<div class="proj-item-meta">${{meta1}}</div>` : ''}}
        ${{meta2 ? `<div class="proj-item-meta">${{meta2}}</div>` : ''}}
        <div class="proj-item-footer">
          <span class="proj-item-loc">${{location}}</span>
          <span class="proj-item-count">${{recs.length}}</span>
        </div>
      </div>
      <div class="proj-docs">${{docsHtml}}</div>
    </div>`;
  }}).join('');
}}

function selectProject(name) {{
  if (_selectedProjects.has(name) && !_selectedDoc) {{
    // already selected at project level — deselect and collapse
    _selectedProjects.delete(name);
    _expandedProjects.delete(name);
  }} else {{
    // select and expand (also upgrades from doc-level selection)
    _selectedProjects.add(name);
    _expandedProjects.add(name);
  }}
  _selectedDoc = null;
  renderProjectList();
  applyFilters();
  const rp = document.querySelector('.records-panel');
  if (rp) rp.scrollTop = 0;
}}

function selectDoc(proj, title) {{
  if (_selectedDoc && _selectedDoc.proj === proj && _selectedDoc.title === title) {{
    // clicking the same doc again → upgrade to project-level selection
    _selectedDoc = null;
    _selectedProjects.add(proj);
  }} else {{
    _selectedDoc = {{ proj, title }};
    _selectedProjects.clear();
    _selectedProjects.add(proj); // keep parent project highlighted
    _expandedProjects.add(proj);
  }}
  renderProjectList();
  applyFilters();
  const rp = document.querySelector('.records-panel');
  if (rp) rp.scrollTop = 0;
}}

function clearProjectSelection() {{
  _selectedProjects.clear();
  _expandedProjects.clear();
  _selectedDoc = null;
  renderProjectList();
  applyFilters();
}}

// ── Project summary panel ───────────────────────────────────────
const PHASES = [
  'concept/feasibility','development/design','approvals/contracting','procurement',
  'construction/installation','commissioning/integration','operations','close-out/post-project review'
];
const PHASE_LABELS = {{
  'concept/feasibility':       'Concept / Feasibility',
  'development/design':        'Development / Design',
  'approvals/contracting':     'Approvals / Contracting',
  'procurement':               'Procurement',
  'construction/installation': 'Construction / Installation',
  'commissioning/integration': 'Commissioning / Integration',
  'operations':                'Operations',
  'close-out/post-project review': 'Close-out / Review',
}};

function renderProjectSummary(filtered) {{
  const panel = document.getElementById('proj-summary');
  const selSize = _selectedProjects.size;
  if (selSize === 0) {{
    panel.classList.remove('visible');
    return;
  }}

  const projRecords = filtered.filter(r => _selectedProjects.has(r.kb_associated_project));
  if (projRecords.length === 0) {{
    panel.classList.remove('visible');
    return;
  }}

  panel.classList.add('visible');

  // Title
  const proj = selSize === 1 ? [..._selectedProjects][0] : null;
  document.getElementById('ps-title').textContent = proj || `${{selSize}} projects selected`;

  // Meta tags — for single project show detail; for multi show aggregated project types
  if (selSize === 1) {{
    const r0 = projRecords[0];
    const cats = [...new Set(projRecords.flatMap(r => r.arena_category || []))];
    const metaTags = [...cats, r0.activity_type, r0.proponent_type,
                      r0.is_consortium ? 'Consortium' : '', r0.location].filter(Boolean);
    document.getElementById('ps-meta').innerHTML =
      metaTags.map(t => `<span class="proj-meta-tag">${{t}}</span>`).join('');
  }} else {{
    const cats = [...new Set(projRecords.flatMap(r => r.arena_category || []))];
    document.getElementById('ps-meta').innerHTML =
      cats.map(t => `<span class="proj-meta-tag">${{t}}</span>`).join('');
  }}

  // Coverage strip
  const nInsights = projRecords.length;
  const nDocs = new Set(projRecords.map(r => r.source_title).filter(Boolean)).size;
  const nCorr = projRecords.filter(r => r.corroboration_count > 1).length;
  let cov = `<span><strong>${{nInsights}}</strong> insight${{nInsights !== 1 ? 's' : ''}}</span>`;
  cov += `<span><strong>${{nDocs}}</strong> source doc${{nDocs !== 1 ? 's' : ''}}</span>`;
  if (nCorr > 0) cov += `<span><strong>${{nCorr}}</strong> corroborated</span>`;
  document.getElementById('ps-coverage').innerHTML = cov;

  // Phase grid
  const phaseMap = {{}};
  PHASES.forEach(p => {{ phaseMap[p] = []; }});
  projRecords.forEach(r => {{
    if (r.lifecycle_phase && phaseMap[r.lifecycle_phase] !== undefined)
      phaseMap[r.lifecycle_phase].push(r);
  }});

  const grid = document.getElementById('ps-phases');
  grid.innerHTML = '';
  PHASES.forEach(phase => {{
    const col = document.createElement('div');
    col.className = 'phase-col';
    const label = document.createElement('div');
    label.className = 'phase-col-label';
    label.textContent = PHASE_LABELS[phase];
    const dotsDiv = document.createElement('div');
    dotsDiv.className = 'phase-dots';
    const recs = phaseMap[phase];
    if (recs.length > 0) {{
      dotsDiv.classList.add('has-dots');
      recs.forEach(r => {{
        const dot = document.createElement('div');
        dot.className = 'phase-dot';
        dot.style.background = FM_COLOURS[r.failure_mode] || '#94a3b8';
        const tip = [r.failure_mode, r.issue_severity,
                     (r.what_happened || '').substring(0, 80)].filter(Boolean).join(' · ');
        dot.title = tip;
        dot.onclick = () => openModal(r);
        dotsDiv.appendChild(dot);
      }});
    }} else {{
      const empty = document.createElement('div');
      empty.className = 'phase-empty-msg';
      empty.textContent = '—';
      dotsDiv.appendChild(empty);
    }}
    col.appendChild(label);
    col.appendChild(dotsDiv);
    grid.appendChild(col);
  }});
}}

function getFilters() {{
  return {{
    search:         document.getElementById('search').value.toLowerCase(),
    category:       document.getElementById('f-category').value,
    activity:       document.getElementById('f-activity').value,
    failure:        document.getElementById('f-failure').value,
    proponent:      document.getElementById('f-proponent').value,
    phase:          document.getElementById('f-phase').value,
    severity:       document.getElementById('f-severity').value,
    consortium:     document.getElementById('f-consortium').value,
    transferability:document.getElementById('f-transferability').value,
    qa:             document.getElementById('f-qa').value,
    qaClass:        document.getElementById('f-qa-class').value,
  }};
}}

function matchesDimFilters(r, f) {{
  if (f.category && !(r.arena_category || []).includes(f.category)) return false;
  if (f.activity && r.activity_type !== f.activity) return false;
  if (f.failure && r.failure_mode !== f.failure) return false;
  if (f.proponent && r.proponent_type !== f.proponent) return false;
  if (f.phase && r.lifecycle_phase !== f.phase) return false;
  if (f.severity && r.issue_severity !== f.severity) return false;
  if (f.consortium === 'true' && !r.is_consortium) return false;
  if (f.consortium === 'false' && r.is_consortium) return false;
  if (f.transferability && r.transferability !== f.transferability) return false;
  if (f.qa && r.qa_verdict !== f.qa) return false;
  if (f.qaClass && r.qa_classification !== f.qaClass) return false;
  if (f.search) {{
    const blob = [r.project_name, r.what_happened, r.lesson_learnt, r.evidence_excerpt,
                  r.source_title, r.kb_associated_project, r.intervention_note].join(' ').toLowerCase();
    if (!blob.includes(f.search)) return false;
  }}
  return true;
}}

function applyFilters() {{
  const f = getFilters();
  const filtered = RECORDS.filter(r => {{
    const proj = r.kb_associated_project || '(No project)';
    if (_selectedDoc) {{
      if (proj !== _selectedDoc.proj || r.source_title !== _selectedDoc.title) return false;
    }} else if (_selectedProjects.size > 0 && !_selectedProjects.has(proj)) return false;
    return matchesDimFilters(r, f);
  }});
  renderCards(filtered);
  renderProjectSummary(filtered);
  renderProjectList();
  if (document.getElementById('tc-analysis').classList.contains('active')) {{
    const dimFiltered = RECORDS.filter(r => matchesDimFilters(r, f));
    renderAnalysis(dimFiltered);
  }}
}}

function changePage(delta) {{
  _curPage += delta;
  renderPage();
  document.querySelector('.records-panel').scrollTop = 0;
}}

function clearFilters() {{
  ALL_FILTER_IDS.forEach(id => {{ const el = document.getElementById(id); if (el) el.value = ''; }});
  _selectedProjects.clear();
  _expandedProjects.clear();
  _selectedDoc = null;
  applyFilters();
}}

ALL_FILTER_IDS.forEach(id => {{
  document.getElementById(id).addEventListener('input', applyFilters);
  document.getElementById(id).addEventListener('change', applyFilters);
}});

function openModal(r) {{
  document.getElementById('m-title').textContent = r.project_name || r.source_title;
  document.getElementById('m-sub').textContent = [r.record_id, r.source_title, r.publish_date].filter(Boolean).join(' · ');
  document.getElementById('m-what').textContent = r.what_happened;

  // lesson_learnt
  const lw = document.getElementById('m-lesson-wrap');
  const ml = document.getElementById('m-lesson');
  if (r.lesson_learnt) {{ ml.textContent = r.lesson_learnt; lw.classList.remove('hidden'); }}
  else lw.classList.add('hidden');

  // evidence excerpt
  if (r.evidence_excerpt) {{
    document.getElementById('m-excerpt').textContent = r.evidence_excerpt;
    document.getElementById('m-excerpt-wrap').classList.remove('hidden');
  }} else {{
    document.getElementById('m-excerpt-wrap').classList.add('hidden');
  }}

  // failure + severity
  const fm = r.failure_mode || '—';
  const isBadge = r.issue_severity
    ? ` <span class="badge" style="background:${{isColour(r.issue_severity)}};color:white">${{r.issue_severity}}</span>`
    : '';
  document.getElementById('m-failure').innerHTML =
    `<span class="badge" style="background:${{fmColour(fm)}};color:white">${{fm}}</span>${{isBadge}}`;
  document.getElementById('m-phase').textContent = r.lifecycle_phase || '—';

  // intervention_note
  const iw = document.getElementById('m-intervention-wrap');
  const mi = document.getElementById('m-intervention');
  if (r.intervention_note) {{ mi.textContent = r.intervention_note; iw.classList.remove('hidden'); }}
  else iw.classList.add('hidden');

  // classification tags
  const tags = [];
  if (r.arena_category && r.arena_category.length) r.arena_category.forEach(c => tags.push(['ARENA category', c, '#1e40af']));
  if (r.activity_type) tags.push(['Activity type', r.activity_type, '#0891b2']);
  if (r.proponent_type) tags.push(['Proponent', r.proponent_type, '#7c3aed']);
  if (r.is_consortium) tags.push(['Governance', 'Consortium', '#92400e']);
  if (r.transferability) tags.push(['Transferability', r.transferability, '#0f766e']);
  if (r.kb_associated_project) tags.push(['ARENA project', r.kb_associated_project, '#0f766e']);
  document.getElementById('m-tags').innerHTML = tags.map(([label, val, colour]) =>
    `<span class="tag" style="background:${{colour}}" title="${{label}}">${{val}}</span>`).join('');

  // QA verdict
  const qw = document.getElementById('m-qa-wrap');
  if (r.qa_verdict) {{
    const classColour = {{ok:'#16a34a', questionable:'#ca8a04', wrong:'#dc2626'}};
    let verdictHtml = `<span class="badge" style="background:${{qaColour(r.qa_verdict)}};color:white">grounding: ${{r.qa_verdict}}</span>`;
    if (r.qa_classification) {{
      verdictHtml += ` <span class="badge" style="background:${{classColour[r.qa_classification]||'#64748b'}};color:white">taxonomy: ${{r.qa_classification}}</span>`;
    }}
    document.getElementById('m-qa-verdict').innerHTML = verdictHtml;
    document.getElementById('m-qa-text').textContent = r.qa_source_text || '';
    document.getElementById('m-qa-text').style.display = r.qa_source_text ? '' : 'none';
    const noteText = [r.qa_note, r.qa_classification_note].filter(Boolean).join(' | ');
    document.getElementById('m-qa-note').textContent = noteText;
    qw.classList.remove('hidden');
  }} else qw.classList.add('hidden');

  // corroboration
  const cw = document.getElementById('m-corr-wrap');
  if (r.corroboration_count > 1) {{
    document.getElementById('m-corr').innerHTML =
      `<span class="corroboration-badge">×${{r.corroboration_count}} source records</span>` +
      ` from ${{r.source_doc_count}} document(s)`;
    const titles = Array.isArray(r.contributing_source_titles)
      ? r.contributing_source_titles.join(' · ') : '';
    document.getElementById('m-corr-titles').textContent = titles;
    cw.classList.remove('hidden');
  }} else cw.classList.add('hidden');

  // confidence note
  if (r.confidence_note) {{
    document.getElementById('m-note').textContent = r.confidence_note;
    document.getElementById('m-note-wrap').classList.remove('hidden');
  }} else {{
    document.getElementById('m-note-wrap').classList.add('hidden');
  }}

  // source links — one set per contributing source document
  const sources = Array.isArray(r.contributing_sources) && r.contributing_sources.length
    ? r.contributing_sources
    : [{{ pdf_url: r.pdf_url, source_pages: r.source_pages, source_url: r.source_url,
          markdown_filename: r.markdown_filename, source_title: r.source_title }}];
  const linkBlocks = sources.map((s, i) => {{
    const pg = firstPage(s.source_pages);
    const pdfHref = s.pdf_url ? (pg ? s.pdf_url + '#page=' + pg : s.pdf_url) : '';
    const mdHref = s.markdown_filename
      ? 'file://' + ARENA_ROOT + '/markdown/all/' + s.markdown_filename +
        (r.evidence_excerpt ? '#:~:text=' + encodeURIComponent(r.evidence_excerpt.substring(0,100)) : '')
      : '';
    const label = sources.length > 1 ? ` (doc ${{i+1}})` : '';
    const pgLabel = pg ? ` p.${{pg}}` : '';
    return [
      pdfHref ? `<a href="${{pdfHref}}" target="_blank" class="src-link">PDF${{pgLabel}}${{label}}</a>` : '',
      mdHref  ? `<a href="${{mdHref}}"  target="_blank" class="src-link src-link-md">Markdown${{label}}</a>` : '',
      (i === 0 && s.source_url) ? `<a href="${{s.source_url}}" target="_blank" class="src-link src-link-kb">ARENA KB</a>` : '',
    ].filter(Boolean).join('');
  }}).join('');
  const projLink = r.project_page_url
    ? `<a href="${{r.project_page_url}}" target="_blank" class="src-link src-link-proj">Project page</a>` : '';
  document.getElementById('m-links').innerHTML =
    (linkBlocks + projLink) || '<span style="color:#94a3b8;font-size:17px">No source links available</span>';

  document.getElementById('overlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}}

function closeModal(e) {{ if (e.target === document.getElementById('overlay')) closeModalDirect(); }}
function closeModalDirect() {{ document.getElementById('overlay').classList.remove('active'); document.body.style.overflow = ''; }}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModalDirect(); }});

// ── Analysis tab ───────────────────────────────────────────────
const _anCharts = {{}};

function renderAnalysis(recs) {{
  const total = recs.length;
  const projects = new Set(recs.map(r => r.kb_associated_project).filter(Boolean));
  const nProjects = projects.size;
  const withFailure = recs.filter(r => r.failure_mode && r.failure_mode !== 'no major failure stated').length;
  const failPct = total > 0 ? (withFailure / total * 100).toFixed(0) : '0';
  const sevMajCrit = recs.filter(r => r.issue_severity === 'major' || r.issue_severity === 'critical').length;
  const sevMinMod = recs.filter(r => r.issue_severity === 'minor' || r.issue_severity === 'moderate').length;
  const sevTotal = sevMajCrit + sevMinMod;
  const sevPct = sevTotal > 0 ? Math.round(sevMajCrit / sevTotal * 100) + '%' : '—';
  const isFiltered = total < RECORDS.length;
  const totalLabel = isFiltered ? `${{total.toLocaleString()}} <span style="font-size:18px;color:#64748b">of ${{RECORDS.length.toLocaleString()}}</span>` : total.toLocaleString();
  document.getElementById('an-stats').innerHTML = `
    <div class="stat"><span class="stat-value">${{totalLabel}}</span><span class="stat-label">${{isFiltered ? 'Filtered records' : 'Total records'}}</span></div>
    <div class="stat"><span class="stat-value">${{nProjects.toLocaleString()}}</span><span class="stat-label">Projects covered</span></div>
    <div class="stat"><span class="stat-value">${{withFailure.toLocaleString()}} <span style="font-size:18px;color:#64748b">(${{failPct}}%)</span></span><span class="stat-label">Records with any failure</span></div>
    <div class="stat"><span class="stat-value">${{sevPct}}</span><span class="stat-label">Severity % (major+critical of adverse)</span></div>`;

  const warnEl = document.getElementById('an-warn');
  if (total > 0 && total < 30) {{
    warnEl.style.display = 'block';
    warnEl.textContent = 'Only ' + total + ' records match filters — ratios may not be reliable.';
  }} else {{
    warnEl.style.display = 'none';
  }}

  anPhaseFM(recs);
  anFMFreq(recs);
  anTypeFailRate(recs);
  anTechFM(recs);
  anSeverity(recs);
  anPhaseSev(recs);
  anSevRatio(recs);
  anCooccurrence(recs);
}}

const AN_PHASES = ['concept/feasibility','development/design','approvals/contracting','procurement',
  'construction/installation','commissioning/integration','operations','close-out/post-project review'];
const AN_PHASE_SHORT = ['Concept','Design','Approvals','Procurement','Construction','Commissioning','Operations','Close-out'];
const FM_LIST = Object.keys(FM_COLOURS);
const FM_NO = 'no major failure stated';
const FM_ADV = FM_LIST.filter(fm => fm !== FM_NO);

function anPhaseFM(recs) {{
  if (_anCharts.phaseFM) _anCharts.phaseFM.destroy();
  const matrix = {{}};
  const totals = {{}};
  AN_PHASES.forEach(p => {{ matrix[p] = {{}}; totals[p] = 0; FM_ADV.forEach(fm => {{ matrix[p][fm] = 0; }}); }});
  recs.forEach(r => {{
    if (r.lifecycle_phase && matrix[r.lifecycle_phase] && r.failure_mode && r.failure_mode !== FM_NO && matrix[r.lifecycle_phase][r.failure_mode] !== undefined) {{
      matrix[r.lifecycle_phase][r.failure_mode]++;
      totals[r.lifecycle_phase]++;
    }}
  }});
  const labels = AN_PHASES.map((p, i) => `${{AN_PHASE_SHORT[i]}} (n=${{totals[p]}})`);
  const datasets = FM_ADV.map(fm => ({{
    label: fm,
    data: AN_PHASES.map(p => totals[p] > 0 ? +((matrix[p][fm] || 0) / totals[p] * 100).toFixed(1) : 0),
    backgroundColor: FM_COLOURS[fm] + 'cc',
    borderColor: FM_COLOURS[fm],
    borderWidth: 1,
  }}));
  _anCharts.phaseFM = new Chart(document.getElementById('an-phase-fm'), {{
    type: 'bar',
    data: {{ labels, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1)}}%` }} }}
      }},
      scales: {{
        x: {{ stacked: true, ticks: {{ font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, max: 100, title: {{ display: true, text: '% of records at phase', font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }});
}}

function anFMFreq(recs) {{
  if (_anCharts.fmFreq) _anCharts.fmFreq.destroy();
  const counts = {{}};
  recs.forEach(r => {{ if (r.failure_mode) counts[r.failure_mode] = (counts[r.failure_mode] || 0) + 1; }});
  const total = recs.length || 1;
  const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]);
  _anCharts.fmFreq = new Chart(document.getElementById('an-fm-freq'), {{
    type: 'bar',
    data: {{
      labels: sorted.map(([k,v]) => `${{k}} (n=${{v}})`),
      datasets: [{{ data: sorted.map(([,v]) => +(v/total*100).toFixed(1)),
        backgroundColor: sorted.map(([k]) => FM_COLOURS[k] || '#94a3b8'), borderWidth: 0, borderRadius: 3 }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
        label: ctx => `${{ctx.parsed.x.toFixed(1)}}%`
      }} }} }},
      scales: {{
        x: {{ max: 100, title: {{ display: true, text: '% of records', font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 14 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anTypeFailRate(recs) {{
  if (_anCharts.typeFailRate) _anCharts.typeFailRate.destroy();
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const totals = {{}};
  const matrix = {{}};
  recs.forEach(r => {{
    (r.arena_category || []).forEach(cat => {{
      totals[cat] = (totals[cat] || 0) + 1;
      if (!matrix[cat]) matrix[cat] = {{}};
      const sev = r.issue_severity || 'none';
      matrix[cat][sev] = (matrix[cat][sev] || 0) + 1;
    }});
  }});
  const MIN_N = 10;
  const types = Object.keys(totals)
    .filter(t => totals[t] >= MIN_N)
    .sort((a,b) => {{
      const failA = SEV_ORDER.slice(0,4).reduce((s,sv) => s + (matrix[a][sv]||0), 0);
      const failB = SEV_ORDER.slice(0,4).reduce((s,sv) => s + (matrix[b][sv]||0), 0);
      return failB/totals[b] - failA/totals[a];
    }});
  const datasets = SEV_ORDER.map(sev => ({{
    label: sev,
    data: types.map(t => +((matrix[t]?.[sev] || 0) / totals[t] * 100).toFixed(1)),
    backgroundColor: IS_COLOURS[sev] + 'cc',
    borderColor: IS_COLOURS[sev],
    borderWidth: 1,
  }}));
  _anCharts.typeFailRate = new Chart(document.getElementById('an-type-fail'), {{
    type: 'bar',
    data: {{ labels: types.map(t => `${{t}} (n=${{totals[t]}})`), datasets }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'top', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x.toFixed(1)}}%`
        }} }}
      }},
      scales: {{
        x: {{ stacked: true, max: 100, title: {{ display: true, text: '% of records by severity', font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, ticks: {{ font: {{ size: 14 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anTechFM(recs) {{
  if (_anCharts.techFM) _anCharts.techFM.destroy();
  const techCounts = {{}};
  recs.forEach(r => {{ (r.arena_category || []).forEach(cat => {{ techCounts[cat] = (techCounts[cat]||0)+1; }}); }});
  const topTechs = Object.entries(techCounts).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([k])=>k);
  const matrix = {{}};
  topTechs.forEach(t => {{ matrix[t] = {{}}; FM_ADV.forEach(fm => {{ matrix[t][fm] = 0; }}); }});
  recs.forEach(r => {{
    (r.arena_category || []).forEach(cat => {{
      if (matrix[cat] && r.failure_mode && r.failure_mode !== FM_NO && matrix[cat][r.failure_mode] !== undefined)
        matrix[cat][r.failure_mode]++;
    }});
  }});
  const datasets = FM_ADV.map(fm => ({{
    label: fm,
    data: topTechs.map(t => matrix[t][fm]||0),
    backgroundColor: FM_COLOURS[fm]+'cc', borderColor: FM_COLOURS[fm], borderWidth: 1,
  }}));
  _anCharts.techFM = new Chart(document.getElementById('an-tech-fm'), {{
    type: 'bar',
    data: {{ labels: topTechs, datasets }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ stacked: true, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, ticks: {{ font: {{ size: 14 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}


function anSeverity(recs) {{
  if (_anCharts.severity) _anCharts.severity.destroy();
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const counts = {{}};
  recs.forEach(r => {{ if (r.issue_severity) counts[r.issue_severity] = (counts[r.issue_severity]||0)+1; }});
  const labels = SEV_ORDER.filter(s => counts[s]);
  _anCharts.severity = new Chart(document.getElementById('an-severity'), {{
    type: 'doughnut',
    data: {{
      labels,
      datasets: [{{ data: labels.map(s=>counts[s]),
        backgroundColor: labels.map(s=>IS_COLOURS[s]||'#94a3b8'), borderWidth: 2 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.label}}: ${{ctx.parsed.toLocaleString()}} (${{(ctx.parsed/RECORDS.length*100).toFixed(1)}}%)` }} }} }}
    }}
  }});
}}

function anPhaseSev(recs) {{
  if (_anCharts.phaseSev) _anCharts.phaseSev.destroy();
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const matrix = {{}};
  AN_PHASES.forEach(p => {{ matrix[p] = {{}}; SEV_ORDER.forEach(s => {{ matrix[p][s] = 0; }}); }});
  recs.forEach(r => {{
    if (r.lifecycle_phase && matrix[r.lifecycle_phase] && r.issue_severity)
      matrix[r.lifecycle_phase][r.issue_severity] = (matrix[r.lifecycle_phase][r.issue_severity] || 0) + 1;
  }});
  const datasets = SEV_ORDER.map(sev => ({{
    label: sev,
    data: AN_PHASES.map(p => matrix[p][sev] || 0),
    backgroundColor: IS_COLOURS[sev] + 'cc',
    borderColor: IS_COLOURS[sev],
    borderWidth: 1,
  }}));
  _anCharts.phaseSev = new Chart(document.getElementById('an-phase-sev'), {{
    type: 'bar',
    data: {{ labels: AN_PHASE_SHORT, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y}} records`
        }} }}
      }},
      scales: {{
        x: {{ stacked: true, ticks: {{ font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, title: {{ display: true, text: 'Record count', font: {{ size: 14 }} }}, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }});
}}

function anSevRatio(recs) {{
  if (_anCharts.sevRatio) _anCharts.sevRatio.destroy();
  const FM_NO_FAILURE = 'no major failure stated';
  const fms = FM_LIST.filter(fm => fm !== FM_NO_FAILURE);
  const sevCounts = {{}};
  fms.forEach(fm => {{ sevCounts[fm] = {{major:0,critical:0,minor:0,moderate:0}}; }});
  let allMajCrit = 0, allMinMod = 0;
  recs.forEach(r => {{
    const fm = r.failure_mode;
    if (!fm || fm === FM_NO_FAILURE || !sevCounts[fm]) return;
    const s = r.issue_severity;
    if (s === 'major' || s === 'critical') {{ sevCounts[fm][s]++; allMajCrit++; }}
    if (s === 'minor' || s === 'moderate') {{ sevCounts[fm][s]++; allMinMod++; }}
  }});
  const allTotal = allMajCrit + allMinMod;
  const baseline = allTotal > 0 ? allMajCrit / allTotal * 100 : 0;
  const pcts = fms.map(fm => {{
    const mc = sevCounts[fm].major + sevCounts[fm].critical;
    const mm = sevCounts[fm].minor + sevCounts[fm].moderate;
    const tot = mc + mm;
    return tot > 0 ? mc / tot * 100 : 0;
  }});
  // Sort by severity % descending
  const indexed = fms.map((fm, i) => ({{fm, pct: pcts[i]}})).sort((a,b) => b.pct - a.pct);
  _anCharts.sevRatio = new Chart(document.getElementById('an-sev-ratio'), {{
    type: 'bar',
    data: {{
      labels: indexed.map(d => d.fm),
      datasets: [
        {{
          data: indexed.map(d => +d.pct.toFixed(1)),
          backgroundColor: indexed.map(d => FM_COLOURS[d.fm] + 'cc'),
          borderColor: indexed.map(d => FM_COLOURS[d.fm]),
          borderWidth: 1, borderRadius: 3
        }},
        {{
          type: 'line',
          label: `Corpus baseline (${{Math.round(baseline)}}%)`,
          data: indexed.map(() => +baseline.toFixed(1)),
          borderColor: '#64748b', borderWidth: 2, borderDash: [6,3],
          pointRadius: 0, fill: false
        }}
      ]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{
        legend: {{ display: true, labels: {{ filter: item => item.text && item.text.includes('Corpus'), font: {{ size: 9 }} }} }},
        tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.type === 'line' ? `Baseline: ${{Math.round(ctx.parsed.x)}}%` : `${{Math.round(ctx.parsed.x)}}%` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Severity %', font: {{ size: 14 }} }}, max: 100, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 14 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anCooccurrence(recs) {{
  const FM_NO_FAILURE = 'no major failure stated';
  const FMS = FM_LIST.filter(fm => fm !== FM_NO_FAILURE);
  const SHORT = {{
    'poor scoping':                     'Poor scoping',
    'unvalidated technical assumptions':'Tech assumptions',
    'unvalidated integration':          'Integration',
    'regulatory & approvals':           'Regulatory',
    'commercial & market':              'Commercial',
    'coordination & stakeholders':      'Coordination',
    'data & measurement':               'Data & measurement',
    'execution & logistics':            'Execution',
  }};

  // matrix[primary][secondary] = count
  const matrix = {{}};
  FMS.forEach(p => {{ matrix[p] = {{}}; FMS.forEach(s => {{ matrix[p][s] = 0; }}); }});
  let maxVal = 0;
  recs.forEach(r => {{
    const p = r.failure_mode, s = r.secondary_failure_mode;
    if (p && s && p !== FM_NO_FAILURE && matrix[p] && matrix[p][s] !== undefined) {{
      matrix[p][s]++;
      if (matrix[p][s] > maxVal) maxVal = matrix[p][s];
    }}
  }});

  // Row totals — skip rows with nothing
  const rowHasData = p => FMS.some(s => matrix[p][s] > 0);

  function cellBg(v) {{
    if (v === 0 || maxVal === 0) return '#f8fafc';
    const t = v / maxVal;
    return `rgb(${{Math.round(255+(99-255)*t)}},${{Math.round(255+(102-255)*t)}},${{Math.round(255+(241-255)*t)}})`;
  }}
  function cellFg(v) {{ return v / maxVal > 0.45 ? 'white' : '#1e293b'; }}

  const th = `style="padding:3px 5px;background:#f8fafc;border:1px solid #e2e8f0;font-size:13px;font-weight:700;color:#475569"`;
  const rotTh = `style="padding:3px;background:#f8fafc;border:1px solid #e2e8f0;font-size:13px;font-weight:600;color:#475569;writing-mode:vertical-lr;transform:rotate(180deg);height:90px;text-align:left;vertical-align:bottom"`;

  let html = `<table style="border-collapse:collapse;font-size:14px;width:100%">`;
  // Header: columns = secondary
  html += `<tr><td ${{th}} style="color:#94a3b8;font-size:12px">Primary ↓ / Secondary →</td>`;
  FMS.forEach(s => {{ html += `<th ${{rotTh}}>${{SHORT[s]||s}}</th>`; }});
  html += `</tr>`;

  FMS.forEach(p => {{
    if (!rowHasData(p)) return;
    const rowTotal = FMS.reduce((sum,s) => sum+(matrix[p][s]||0), 0);
    html += `<tr><th ${{th}} style="text-align:left;white-space:nowrap">${{SHORT[p]||p}} <span style="color:#94a3b8;font-weight:400">(n=${{rowTotal}})</span></th>`;
    FMS.forEach(s => {{
      if (p === s) {{
        html += `<td style="padding:4px;text-align:center;background:#f1f5f9;border:1px solid #e2e8f0;color:#cbd5e1">—</td>`;
      }} else {{
        const v = matrix[p][s] || 0;
        const bg = cellBg(v), fg = cellFg(v);
        html += `<td style="padding:4px;text-align:center;background:${{bg}};border:1px solid #e2e8f0;color:${{fg}};cursor:default" title="${{p}} + ${{s}}: ${{v}}">${{v||''}}</td>`;
      }}
    }});
    html += `</tr>`;
  }});
  html += `</table>`;
  document.getElementById('an-cooccur').innerHTML = html;
}}

// ── Benchmarks ─────────────────────────────────────────────────
const PALETTE = ['#6366f1','#0891b2','#059669','#f97316','#a855f7','#ec4899','#ca8a04','#14b8a6','#dc2626','#3b82f6'];

// Build nav buttons
(function() {{
  const nav = document.getElementById('bench-nav');
  Object.entries(BENCHMARKS).forEach(([key, ds]) => {{
    const btn = document.createElement('button');
    btn.className = 'bench-nav-btn';
    btn.dataset.key = key;
    btn.innerHTML = `<span>${{ds.title}}</span><span style="font-size:14px;opacity:0.65">${{ds.rows.length}}</span>`;
    btn.onclick = () => loadBenchmark(key);
    nav.appendChild(btn);
  }});
}})();

let _bSortCol = null, _bSortDir = 1, _bKey = null, _chartInst = null;

function loadBenchmark(key) {{
  _bKey = key; _bSortCol = null;
  document.querySelectorAll('.bench-nav-btn').forEach(b => b.classList.toggle('active', b.dataset.key === key));
  renderBenchmark(key, '', '');
}}

function renderBenchmark(key, search, cat) {{
  const ds = BENCHMARKS[key];
  const catField = ds.columns.find(c => /technology_category/i.test(c) || c === 'Category');
  const cats = catField ? [...new Set(ds.rows.map(r => r[catField]).filter(Boolean))].sort() : [];

  let rows = ds.rows.filter(r => {{
    if (cat && catField && r[catField] !== cat) return false;
    if (search) {{
      const blob = Object.values(r).join(' ').toLowerCase();
      if (!blob.includes(search.toLowerCase())) return false;
    }}
    return true;
  }});

  if (_bSortCol) {{
    rows = [...rows].sort((a, b) => {{
      const av = a[_bSortCol] || '', bv = b[_bSortCol] || '';
      const an = parseFloat(av), bn = parseFloat(bv);
      return (!isNaN(an) && !isNaN(bn)) ? (an - bn) * _bSortDir : av.localeCompare(bv) * _bSortDir;
    }});
  }}

  const catOpts = cats.map(c => `<option value="${{c}}"${{c === cat ? ' selected' : ''}}>${{c}}</option>`).join('');
  const catSel = catField
    ? `<select class="bench-filter" id="bench-cat"
         onchange="renderBenchmark('${{key}}', document.getElementById('bench-search').value, this.value)">
         <option value="">All categories</option>${{catOpts}}
       </select>`
    : '';

  const ths = ds.columns.map(col => {{
    const arrow = col === _bSortCol ? (_bSortDir === 1 ? ' ↑' : ' ↓') : '';
    return `<th onclick="sortBench('${{key}}','${{col}}')">${{col.replace(/_/g, ' ')}}${{arrow}}</th>`;
  }}).join('');

  const trs = rows.map(row => {{
    const tds = ds.columns.map(col => {{
      const v = row[col] || '';
      if (!v) return `<td class="col-empty">—</td>`;
      if (/notes/i.test(col)) return `<td class="col-notes" title="${{v.replace(/"/g, '&quot;')}}">${{v}}</td>`;
      if (/actual/i.test(col) && !isNaN(parseFloat(v))) return `<td class="col-actual">${{v}}</td>`;
      if (/(low|high|rte_|lcoe|capex|lcoh|^cf_|cost_low|cost_high)/i.test(col) && !isNaN(parseFloat(v))) return `<td class="col-value">${{v}}</td>`;
      return `<td>${{v}}</td>`;
    }}).join('');
    return `<tr>${{tds}}</tr>`;
  }}).join('');

  const main = document.getElementById('bench-main');
  main.innerHTML = `
    <div class="bench-header">
      <div class="bench-title">${{ds.title}}</div>
      <div class="bench-desc">${{ds.description}}</div>
    </div>
    <div class="bench-chart-wrap"><canvas id="bench-canvas"></canvas></div>
    <div class="bench-controls">
      <input class="bench-search" id="bench-search" placeholder="Search all columns…" value="${{search}}"
        oninput="renderBenchmark('${{key}}', this.value, document.getElementById('bench-cat')?.value || '')">
      ${{catSel}}
      <span class="bench-count">${{rows.length}} of ${{ds.rows.length}} rows</span>
    </div>
    <div class="bench-table-wrap">
      <table class="bench-table"><thead><tr>${{ths}}</tr></thead><tbody>${{trs}}</tbody></table>
    </div>`;

  // Render chart after DOM update
  renderChart(key, rows);
}}

function sortBench(key, col) {{
  _bSortDir = (_bSortCol === col) ? _bSortDir * -1 : 1;
  _bSortCol = col;
  renderBenchmark(key, document.getElementById('bench-search')?.value || '', document.getElementById('bench-cat')?.value || '');
}}

// ── Chart rendering ────────────────────────────────────────────
function renderChart(key, rows) {{
  const canvas = document.getElementById('bench-canvas');
  if (!canvas) return;
  if (_chartInst) {{ _chartInst.destroy(); _chartInst = null; }}
  const cfg = buildChartConfig(key, rows);
  if (cfg) _chartInst = new Chart(canvas, cfg);
  else canvas.closest('.bench-chart-wrap').style.display = 'none';
}}

function median(arr) {{
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2;
}}

function buildChartConfig(key, rows) {{
  if (key === 'lcoe')           return buildRangeBar(rows, 'Technology_Category', 'LCOE_Low_AUD_per_MWh', 'LCOE_High_AUD_per_MWh', 'AUD$/MWh');
  if (key === 'lcoh')           return buildRangeBar(rows, 'Technology/Project',  'LCOH_Low_AUD_per_kg',  'LCOH_High_AUD_per_kg',  'AUD$/kg H₂');
  if (key === 'capex')          return buildCapexLine(rows);
  if (key === 'abatement')      return buildMACcurve(rows);
  if (key === 'capacity_factor')return buildCFScatter(rows);
  if (key === 'storage')        return buildRTEbar(rows);
  return null;
}}

// Horizontal floating range bars grouped by label field
function buildRangeBar(rows, labelField, lowField, highField, xLabel) {{
  // Group by label, collect low/high values
  const groups = {{}};
  rows.forEach(r => {{
    const lbl = r[labelField] || 'Unknown';
    const lo = parseFloat(r[lowField]), hi = parseFloat(r[highField]);
    if (!groups[lbl]) groups[lbl] = {{ lows: [], highs: [] }};
    if (!isNaN(lo)) groups[lbl].lows.push(lo);
    if (!isNaN(hi)) groups[lbl].highs.push(hi);
  }});

  // Build sorted list by midpoint
  const entries = Object.entries(groups)
    .map(([lbl, g]) => {{
      const lo = g.lows.length ? Math.min(...g.lows) : null;
      const hi = g.highs.length ? Math.max(...g.highs) : null;
      const mid = (lo !== null && hi !== null) ? (lo + hi) / 2 : (lo ?? hi ?? 0);
      return {{ lbl, lo: lo ?? mid, hi: hi ?? mid, mid }};
    }})
    .filter(e => e.lo !== null || e.hi !== null)
    .sort((a, b) => a.mid - b.mid);

  if (!entries.length) return null;

  return {{
    type: 'bar',
    data: {{
      labels: entries.map(e => e.lbl),
      datasets: [{{
        label: xLabel,
        data: entries.map(e => [e.lo, e.hi]),
        backgroundColor: entries.map((_, i) => PALETTE[i % PALETTE.length] + 'cc'),
        borderColor: entries.map((_, i) => PALETTE[i % PALETTE.length]),
        borderWidth: 1,
        borderRadius: 3,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{ legend: {{ display: false }}, tooltip: {{
        callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.raw[0]?.toFixed(0)}} – ${{ctx.raw[1]?.toFixed(0)}}` }}
      }} }},
      scales: {{
        x: {{ title: {{ display: true, text: xLabel, font: {{ size: 15 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 15 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }};
}}

// Line chart: capex midpoint over scenario year, one line per tech category
function buildCapexLine(rows) {{
  const groups = {{}};
  rows.forEach(r => {{
    const cat = r['Technology_Category'] || 'Other';
    const yr = parseInt(r['Scenario_Year']);
    const lo = parseFloat(r['Capex_Low']), hi = parseFloat(r['Capex_High']);
    if (isNaN(yr)) return;
    const mid = (!isNaN(lo) && !isNaN(hi)) ? (lo + hi) / 2 : (!isNaN(lo) ? lo : hi);
    if (isNaN(mid)) return;
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push({{ yr, mid, lo: isNaN(lo) ? mid : lo, hi: isNaN(hi) ? mid : hi }});
  }});

  const cats = Object.keys(groups).filter(c => groups[c].length >= 2).sort();
  if (!cats.length) return null;

  const datasets = cats.flatMap((cat, i) => {{
    const pts = groups[cat].sort((a, b) => a.yr - b.yr);
    const colour = PALETTE[i % PALETTE.length];
    return [{{
      label: cat,
      data: pts.map(p => ({{ x: p.yr, y: p.mid }})),
      borderColor: colour,
      backgroundColor: colour + '22',
      fill: false,
      tension: 0.3,
      pointRadius: 4,
    }}];
  }});

  return {{
    type: 'line',
    data: {{ datasets }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }} }},
      scales: {{
        x: {{ type: 'linear', title: {{ display: true, text: 'Scenario Year', font: {{ size: 15 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ title: {{ display: true, text: 'AUD$/kW (midpoint)', font: {{ size: 15 }} }}, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }};
}}

// Marginal abatement cost curve: sorted horizontal bars coloured by value
function buildMACcurve(rows) {{
  const entries = rows
    .map(r => {{
      const lo = parseFloat(r['Cost_Low_AUD_per_tCO2e']), hi = parseFloat(r['Cost_High_AUD_per_tCO2e']);
      const mid = (!isNaN(lo) && !isNaN(hi)) ? (lo + hi) / 2 : (!isNaN(lo) ? lo : hi);
      return {{ lbl: (r['Technology/Measure'] || r['Technology_Category'] || '').substring(0, 50), mid }};
    }})
    .filter(e => !isNaN(e.mid))
    .sort((a, b) => a.mid - b.mid);

  if (!entries.length) return null;

  const colours = entries.map(e =>
    e.mid < 0 ? '#16a34a' : e.mid <= 80 ? '#f97316' : '#dc2626');

  return {{
    type: 'bar',
    data: {{
      labels: entries.map(e => e.lbl),
      datasets: [{{
        label: 'AUD$/tCO₂e',
        data: entries.map(e => e.mid),
        backgroundColor: colours,
        borderColor: colours,
        borderWidth: 1,
        borderRadius: 3,
      }}, {{
        label: 'ACCU price ~$80',
        data: entries.map(() => 80),
        type: 'line',
        borderColor: '#64748b',
        borderDash: [4, 4],
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{
        legend: {{ display: true, labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x?.toFixed(0) ?? ctx.raw?.toFixed(0)}}` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'AUD$/tCO₂e (midpoint)', font: {{ size: 15 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 14 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }};
}}

// Scatter: CF designed vs actual, y=x reference line
function buildCFScatter(rows) {{
  const catField = 'Technology_Category';
  const groups = {{}};
  rows.forEach(r => {{
    const x = parseFloat(r['CF_Designed_pct']), y = parseFloat(r['CF_Actual_pct']);
    if (isNaN(x) || isNaN(y)) return;
    const cat = r[catField] || 'Other';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push({{ x, y, label: r['Technology/Configuration'] || r['Location/Project'] || '' }});
  }});

  const cats = Object.keys(groups).sort();
  if (!cats.length) return null;

  const maxVal = Math.max(...Object.values(groups).flat().map(p => Math.max(p.x, p.y)), 100);

  const datasets = cats.map((cat, i) => ({{
    label: cat,
    data: groups[cat],
    backgroundColor: PALETTE[i % PALETTE.length] + 'cc',
    borderColor: PALETTE[i % PALETTE.length],
    pointRadius: 6,
    type: 'scatter',
  }}));

  // y=x reference line
  datasets.push({{
    label: 'Designed = Actual',
    data: [{{ x: 0, y: 0 }}, {{ x: maxVal, y: maxVal }}],
    type: 'line',
    borderColor: '#94a3b8',
    borderDash: [5, 5],
    borderWidth: 1.5,
    pointRadius: 0,
    fill: false,
  }});

  return {{
    type: 'scatter',
    data: {{ datasets }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 14 }}, boxWidth: 14 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => ctx.dataset.type === 'line' ? ctx.dataset.label
            : `${{ctx.dataset.label}}: designed ${{ctx.parsed.x}}% → actual ${{ctx.parsed.y}}%`
        }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Designed CF (%)', font: {{ size: 15 }} }}, min: 0, grid: {{ color: '#f1f5f9' }} }},
        y: {{ title: {{ display: true, text: 'Actual CF (%)', font: {{ size: 15 }} }}, min: 0, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }};
}}

// Grouped horizontal bar: designed vs actual RTE by tech category
function buildRTEbar(rows) {{
  const groups = {{}};
  rows.forEach(r => {{
    const cat = r['Technology_Category'] || 'Other';
    if (!groups[cat]) groups[cat] = {{ designed: [], actual: [] }};
    const d = parseFloat(r['RTE_Designed_pct']), a = parseFloat(r['RTE_Actual_pct']);
    if (!isNaN(d)) groups[cat].designed.push(d);
    if (!isNaN(a)) groups[cat].actual.push(a);
  }});

  const cats = Object.keys(groups)
    .filter(c => groups[c].designed.length || groups[c].actual.length)
    .sort();
  if (!cats.length) return null;

  const avg = arr => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : null;

  return {{
    type: 'bar',
    data: {{
      labels: cats,
      datasets: [
        {{
          label: 'Designed RTE %',
          data: cats.map(c => avg(groups[c].designed)),
          backgroundColor: '#6366f133',
          borderColor: '#6366f1',
          borderWidth: 1.5,
          borderRadius: 3,
        }},
        {{
          label: 'Actual RTE %',
          data: cats.map(c => avg(groups[c].actual)),
          backgroundColor: '#16a34acc',
          borderColor: '#16a34a',
          borderWidth: 1,
          borderRadius: 3,
        }}
      ]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'top', labels: {{ font: {{ size: 15 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x?.toFixed(1)}}%` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Round-Trip Efficiency (%)', font: {{ size: 15 }} }}, min: 0, max: 100, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 15 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }};
}}

// ── Synthesis ──────────────────────────────────────────────────
const SYNTH_MAX = 500;

function getActiveFilterDesc() {{
  const f = getFilters();
  const parts = [];
  if (_selectedDoc) parts.push(`report: ${{_selectedDoc.title}} (${{_selectedDoc.proj}})`);
  else if (_selectedProjects.size === 1) parts.push(`project: ${{[..._selectedProjects][0]}}`);
  else if (_selectedProjects.size > 1) parts.push(`${{_selectedProjects.size}} projects selected`);
  if (f.category) parts.push(`ARENA category: ${{f.category}}`);
  if (f.activity) parts.push(`activity type: ${{f.activity}}`);
  if (f.phase)    parts.push(`lifecycle phase: ${{f.phase}}`);
  if (f.failure)  parts.push(`failure mode: ${{f.failure}}`);
  if (f.proponent)parts.push(`proponent: ${{f.proponent}}`);
  if (f.severity) parts.push(`severity: ${{f.severity}}`);
  if (f.search)   parts.push(`search: "${{f.search}}"`);
  return parts.length ? parts.join(', ') : 'all records';
}}

function buildSynthPrompt(records, mode) {{
  const filterDesc = getActiveFilterDesc();
  const extraContext = (document.getElementById('synth-context').value || '').trim();
  const compact = records.slice(0, SYNTH_MAX).map(r => ({{
    id: r.record_id,
    project: r.project_name || r.kb_associated_project,
    what: r.what_happened,
    lesson: r.lesson_learnt,
    failure_mode: r.failure_mode,
    phase: r.lifecycle_phase,
    severity: r.issue_severity,
    intervention: r.intervention_note,
  }}));
  const header = `You are a senior energy infrastructure analyst synthesising delivery insights from ARENA-funded projects.\n\nThe records below have been filtered to: ${{filterDesc}} (${{records.length}} records${{records.length > SYNTH_MAX ? `, showing first ${{SYNTH_MAX}}` : ''}}).`;
  const contextBlock = extraContext ? `\n\nAdditional context from the analyst: ${{extraContext}}\n\nLet this context shape your framing and emphasis — surface evidence most relevant to it, but do not ignore significant patterns that fall outside it.` : '';
  const footer = `\n\nRecords:\n${{JSON.stringify(compact, null, 0)}}`;

  if (mode === 'brief') {{
    return `${{header}}${{contextBlock}}

Write a brief summary of 2–3 paragraphs. Cover: the dominant failure modes, the lifecycle phases where issues concentrate, and the single most important lesson for a project manager. Be specific — cite 2–3 project names or record IDs as anchors. No headings, no lists. Plain prose only. Stop after 3 paragraphs.${{footer}}`;
  }} else if (mode === 'short') {{
    return `${{header}}${{contextBlock}}

Write a structured short report. Use the following headings:

**Key failure modes** — the top 2–3 patterns with brief examples.

**Where issues concentrate** — which lifecycle phases matter most.

**What works** — the most effective interventions.

**Top risk to watch** — the single highest-priority risk for a project manager.

Be specific. Cite project names or record IDs for the strongest evidence. Keep each section to 2–4 sentences. Total response should be 2000–4000 tokens — substantive but not exhaustive.${{footer}}`;
  }} else {{
    return `${{header}}${{contextBlock}}

Synthesise the key patterns across these records. Structure your response as follows:

**Most common failure modes** — what goes wrong most often in this context, with specific examples from the records.

**Where in delivery** — which lifecycle phases concentrate the most issues.

**What works** — interventions and approaches that resolved or mitigated issues.

**Watch out for** — the 2–3 highest-priority risks a project manager should anticipate at this stage.

**Gaps in the evidence** — what failure modes or phases are suspiciously absent, suggesting blind spots in the knowledge base.

Be specific. Cite project names or record IDs where the evidence is strong. Do not pad with generic advice.

You have a budget of approximately 8000 tokens. Use it fully — pace yourself across all five sections and do not truncate or trail off before completing the final section.${{footer}}`;
  }}
}}

let _synthText = '';

function synthCopy() {{
  navigator.clipboard.writeText(_synthText).then(() => {{
    const btn = document.getElementById('synth-copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = 'Copy'; }}, 1500);
  }});
}}

function synthSave() {{
  const meta = document.getElementById('synth-meta').textContent;
  const filename = 'synthesis-' + meta.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 60) + '.md';
  const blob = new Blob([_synthText], {{ type: 'text/markdown' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}}

function openSynth() {{
  const apiKey = localStorage.getItem('arena_api_key');
  const overlay = document.getElementById('synth-overlay');
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
  if (!apiKey) {{
    showKeyForm();
  }} else {{
    runSynthesis(apiKey);
  }}
}}

function closeSynth() {{
  document.getElementById('synth-overlay').classList.remove('active');
  document.body.style.overflow = '';
}}

function showKeyForm() {{
  document.getElementById('synth-title').textContent = 'Anthropic API key required';
  document.getElementById('synth-meta').textContent = 'Stored in browser localStorage — never sent anywhere except api.anthropic.com';
  document.getElementById('synth-body').innerHTML = `
    <div class="synth-key-form">
      <div style="font-size:17px;color:#475569">Enter your Anthropic API key to enable synthesis. It will be saved locally and reused.</div>
      <input class="synth-key-input" id="synth-key-input" type="password" placeholder="sk-ant-…" autocomplete="off">
      <button class="synth-key-btn" onclick="saveKeyAndRun()">Save and synthesise</button>
    </div>`;
  document.getElementById('synth-key-input').focus();
}}

function saveKeyAndRun() {{
  const key = document.getElementById('synth-key-input').value.trim();
  if (!key.startsWith('sk-ant-')) {{
    alert('API key should start with sk-ant-');
    return;
  }}
  localStorage.setItem('arena_api_key', key);
  runSynthesis(key);
}}

async function runSynthesis(apiKey) {{
  const records = _lastFiltered;
  const filterDesc = getActiveFilterDesc();
  const mode = document.getElementById('synth-mode').value;
  const modeLabel = mode === 'brief' ? 'Brief Summary' : mode === 'short' ? 'Short Report' : 'Detailed Report';
  const maxTokens = 16000;

  document.getElementById('synth-title').textContent = modeLabel;
  document.getElementById('synth-meta').textContent =
    `${{records.length}} records · ${{filterDesc}}${{records.length > SYNTH_MAX ? ` · capped at ${{SYNTH_MAX}}` : ''}}`;

  const body = document.getElementById('synth-body');
  body.innerHTML = '<div class="synth-text" id="synth-stream"></div><span class="synth-cursor" id="synth-cursor"></span>';
  const streamEl = document.getElementById('synth-stream');
  const cursor = document.getElementById('synth-cursor');

  _synthText = '';
  document.getElementById('synth-btn').disabled = true;
  document.getElementById('synth-copy-btn').style.display = 'none';
  document.getElementById('synth-save-btn').style.display = 'none';

  try {{
    const response = await fetch('https://api.anthropic.com/v1/messages', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      }},
      body: JSON.stringify({{
        model: 'claude-sonnet-4-6',
        max_tokens: maxTokens,
        stream: true,
        messages: [{{ role: 'user', content: buildSynthPrompt(records, mode) }}],
      }}),
    }});

    if (!response.ok) {{
      const err = await response.json().catch(() => ({{}}));
      if (response.status === 401) {{
        localStorage.removeItem('arena_api_key');
        body.innerHTML = '<div style="color:#dc2626;font-size:17px;padding:8px 0">Invalid API key — removed. Click Synthesise again to re-enter.</div>';
        return;
      }}
      throw new Error(err.error?.message || `HTTP ${{response.status}}`);
    }}

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let text = '';

    while (true) {{
      const {{ done, value }} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, {{ stream: true }});
      for (const line of chunk.split('\\n')) {{
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') continue;
        try {{
          const evt = JSON.parse(data);
          if (evt.type === 'content_block_delta' && evt.delta?.type === 'text_delta') {{
            text += evt.delta.text;
            _synthText = text;
            streamEl.innerHTML = marked.parse(text);
            body.scrollTop = body.scrollHeight;
          }}
        }} catch(e) {{}}
      }}
    }}
    document.getElementById('synth-cursor')?.remove();
    if (_synthText) {{
      linkifyRecordIds(streamEl);
      document.getElementById('synth-copy-btn').style.display = '';
      document.getElementById('synth-save-btn').style.display = '';
      const filterDesc = getActiveFilterDesc();
      const extraContext = (document.getElementById('synth-context').value || '').trim();
      const summary = (filterDesc + (extraContext ? ' · ' + extraContext : '')).substring(0, 100);
      const rep = {{
        id: 'rep_' + Date.now(),
        date: new Date().toISOString(),
        mode: mode,
        filterDesc: filterDesc,
        context: extraContext,
        recordCount: records.length,
        summary: summary,
        text: _synthText,
      }};
      saveReport(rep);
      history.replaceState(null, '', '#report-' + rep.id);
    }}
  }} catch(e) {{
    document.getElementById('synth-cursor')?.remove();
    streamEl.textContent = '';
    body.innerHTML += `<div style="color:#dc2626;font-size:17px;padding:8px 0">Error: ${{e.message}}</div>`;
  }} finally {{
    document.getElementById('synth-btn').disabled = false;
  }}
}}

// ── Init ───────────────────────────────────────────────────────
_lastFiltered = RECORDS;
renderPage();
renderProjectList();

// Update Reports tab count from server on load
fetch('/list-reports').then(r => r.json()).then(list => {{
  const tab = document.getElementById('tab-reports');
  if (tab && list.length) tab.textContent = `Reports (${{list.length}})`;
}}).catch(() => {{}});

// Hash navigation — open report if URL contains #report-{id}
function handleHash() {{
  const hash = window.location.hash;
  if (hash.startsWith('#report-')) {{
    const id = hash.slice(8);
    switchTab('reports');
    openReport(id);
  }}
}}
window.addEventListener('hashchange', handleHash);
handleHash();

// ── Permalink generation ───────────────────────────────────────
function generateReportHtml(rep) {{
  const renderedBody = marked.parse(rep.text);
  // Extract cited record IDs from report text (full IDs + partial citation continuations)
  const cited = [];
  const seenIds = new Set();
  function addIdToCited(id) {{
    if (!seenIds.has(id)) {{
      const r = RECORD_MAP.get(id);
      if (r) {{ cited.push(r); seenIds.add(id); }}
    }}
  }}
  // Match ARENA-DLV-N optionally followed by ranges/comma-lists like ", -M", " through -M", ", and -M"
  const expandRe = /\\bARENA-DLV-(\\d+)((?:(?:\\s+through\\s+-\\d+)|(?:\\s*,\\s*(?:and\\s+)?-\\d+(?:\\s+through\\s+-\\d+)?))*)/g;
  let em;
  while ((em = expandRe.exec(rep.text)) !== null) {{
    const first = parseInt(em[1]);
    addIdToCited('ARENA-DLV-' + first);
    const tail = em[2] || '';
    const immRange = /^\\s+through\\s+-(\\d+)/.exec(tail);
    const rest = immRange ? tail.slice(immRange[0].length) : tail;
    if (immRange) {{
      const s = first, e = parseInt(immRange[1]);
      for (let ci = s + 1; ci <= Math.min(e, s + 50); ci++) addIdToCited('ARENA-DLV-' + ci);
    }}
    const itemRe = /,\\s*(?:and\\s+)?-(\\d+)(?:\\s+through\\s+-(\\d+))?/g;
    let mx;
    while ((mx = itemRe.exec(rest)) !== null) {{
      if (mx[2]) {{
        const sa = parseInt(mx[1]), ea = parseInt(mx[2]);
        for (let cj = sa; cj <= Math.min(ea, sa + 50); cj++) addIdToCited('ARENA-DLV-' + cj);
      }} else {{
        addIdToCited('ARENA-DLV-' + mx[1]);
      }}
    }}
  }}
  const modeLabel = rep.mode === 'brief' ? 'Brief Summary' : rep.mode === 'short' ? 'Short Report' : 'Detailed Report';
  const dateStr = new Date(rep.date).toLocaleDateString('en-AU', {{day:'numeric',month:'long',year:'numeric'}});
  const FM_COLOURS_JSON = JSON.stringify({fm_colours});
  const IS_COLOURS_JSON = JSON.stringify({is_colours});
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${{modeLabel}} — ${{rep.filterDesc}}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"><\\/script>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:0}}
.rp-page{{max-width:820px;margin:0 auto;padding:40px 24px 80px}}
.rp-header{{margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid #e2e8f0}}
.rp-mode{{font-size:15px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:8px}}
.rp-title{{font-size:26px;font-weight:800;color:#0f172a;margin-bottom:6px;line-height:1.3}}
.rp-meta{{font-size:16px;color:#94a3b8}}
.rp-context{{margin-top:10px;font-size:17px;color:#475569;background:#f1f5f9;padding:10px 14px;border-radius:8px;border-left:3px solid #6366f1}}
.rp-body{{font-size:18px;color:#1e293b;line-height:1.8}}
.rp-body h1{{font-size:24px;font-weight:800;margin:28px 0 10px;color:#0f172a}}
.rp-body h2{{font-size:21px;font-weight:700;margin:24px 0 8px;color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:4px}}
.rp-body h3{{font-size:19px;font-weight:700;margin:18px 0 6px;color:#1e293b}}
.rp-body p{{margin:8px 0}}
.rp-body ul,.rp-body ol{{margin:8px 0 8px 24px}}
.rp-body li{{margin:4px 0}}
.rp-body strong{{font-weight:700;color:#0f172a}}
.rp-body hr{{border:none;border-top:1px solid #e2e8f0;margin:20px 0}}
.rp-body code{{font-family:monospace;font-size:16px;background:#f1f5f9;padding:1px 5px;border-radius:3px}}
.record-link{{color:#6366f1!important;text-decoration:underline;text-decoration-style:dotted;cursor:pointer;font-weight:500}}
.record-link:hover{{color:#4f46e5!important}}
.badge{{font-size:14px;font-weight:700;padding:3px 9px;border-radius:20px;color:white;white-space:nowrap}}
.chip{{font-size:14px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}}
.chip-scale{{background:#e0f2fe;color:#0369a1}}
.chip-tech{{background:#ede9fe;color:#6d28d9}}
#record-tooltip{{position:fixed;z-index:9999;width:380px;background:white;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.16);max-height:480px;overflow-y:auto;display:none}}
#record-tooltip .rt-header{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px 8px;border-bottom:1px solid #f1f5f9;position:sticky;top:0;background:white;z-index:1}}
#record-tooltip .rt-id{{font-size:14px;color:#6366f1;font-weight:700;letter-spacing:.5px}}
#record-tooltip .rt-close{{font-size:18px;color:#94a3b8;cursor:pointer;padding:2px 4px}}
#record-tooltip .rt-close:hover{{color:#475569}}
#record-tooltip .rt-body{{padding:10px 14px 14px;font-size:16px;line-height:1.6;display:flex;flex-direction:column;gap:6px}}
#record-tooltip .rt-project{{font-weight:700;color:#1e293b;font-size:17px}}
#record-tooltip .rt-chips{{display:flex;flex-wrap:wrap;gap:4px}}
#record-tooltip .rt-what{{color:#334155}}
#record-tooltip .rt-lesson{{color:#475569;font-style:italic}}
#record-tooltip .rt-excerpt{{font-size:15px;color:#64748b;background:#f8fafc;border-left:3px solid #e2e8f0;padding:6px 8px;border-radius:0 4px 4px 0}}
#record-tooltip .rt-footer{{display:flex;flex-wrap:wrap;gap:6px;padding-top:4px;border-top:1px solid #f1f5f9}}
#record-tooltip .rt-src{{font-size:15px;color:#6366f1;text-decoration:none}}
#record-tooltip .rt-src:hover{{text-decoration:underline}}
.rp-footer{{margin-top:48px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:15px;color:#94a3b8}}
</style>
</head>
<body>
<div class="rp-page">
  <div class="rp-header">
    <div class="rp-mode">${{modeLabel}}</div>
    <div class="rp-title">${{rep.filterDesc}}</div>
    <div class="rp-meta">${{dateStr}} · ${{rep.recordCount}} records reviewed</div>
    ${{rep.context ? `<div class="rp-context"><strong>Context:</strong> ${{rep.context}}</div>` : ''}}
  </div>
  <div class="rp-body" id="rp-body">${{renderedBody}}</div>
  <div class="rp-footer">Generated from the ARENA Delivery Insights registry · ${{dateStr}}</div>
</div>
<div id="record-tooltip"></div>
<script>
const CITED = ${{JSON.stringify(cited)}};
const RECORD_MAP = new Map(CITED.map(r => [r.record_id, r]));
const INDEX_MAP = new Map(CITED.map((r, i) => [r.record_id, i + 1]));
const FM_COLOURS = ${{FM_COLOURS_JSON}};
const IS_COLOURS = ${{IS_COLOURS_JSON}};

function buildSrcUrl(r) {{
  if (r.source_url) return r.source_url;
  if (r.pdf_url) return r.pdf_url;
  return null;
}}

// Linkify record IDs with sequential citation numbers
const body = document.getElementById('rp-body');
let rpHtml = body.innerHTML;
// Expand partial citations: "ARENA-DLV-N, -M", "through -M", ", and -M"
rpHtml = rpHtml.replace(
  /\\\\bARENA-DLV-(\\\\d+)((?:(?:\\\\s+through\\\\s+-\\\\d+)|(?:\\\\s*,\\\\s*(?:and\\\\s+)?-\\\\d+(?:\\\\s+through\\\\s+-\\\\d+)?))+)/g,
  function(match, firstNum, tail) {{
    var ids = ['ARENA-DLV-' + firstNum];
    var immRange = /^\\\\s+through\\\\s+-(\\\\d+)/.exec(tail);
    var rest = immRange ? tail.slice(immRange[0].length) : tail;
    if (immRange) {{
      var s = parseInt(firstNum), e = parseInt(immRange[1]);
      for (var i = s + 1; i <= Math.min(e, s + 50); i++) ids.push('ARENA-DLV-' + i);
    }}
    var itemRe = /,\\\\s*(?:and\\\\s+)?-(\\\\d+)(?:\\\\s+through\\\\s+-(\\\\d+))?/g;
    var mx;
    while ((mx = itemRe.exec(rest)) !== null) {{
      if (mx[2]) {{
        var sa = parseInt(mx[1]), ea = parseInt(mx[2]);
        for (var j = sa; j <= Math.min(ea, sa + 50); j++) ids.push('ARENA-DLV-' + j);
      }} else {{
        ids.push('ARENA-DLV-' + mx[1]);
      }}
    }}
    return ids.join(', ');
  }}
);
rpHtml = rpHtml.replace(
  /\\\\b(ARENA-DLV-\\\\d{{4,}})\\\\b/g,
  (match, id) => {{
    const n = INDEX_MAP.get(id);
    return n ? \`<span class="record-link" data-id="\${{id}}">[\${{n}}]</span>\` : match;
  }}
);
body.innerHTML = rpHtml;

const _tooltip = document.getElementById('record-tooltip');
let _anchor = null;
function closeTooltip() {{ _tooltip.style.display = 'none'; _anchor = null; }}
function positionTooltip(el) {{
  const rect = el.getBoundingClientRect();
  const vp = {{ w: window.innerWidth, h: window.innerHeight }};
  const left = Math.min(rect.left, vp.w - 388);
  const below = rect.bottom + 8 + 480 <= vp.h;
  _tooltip.style.left = Math.max(8, left) + 'px';
  _tooltip.style.top = (below ? rect.bottom + 8 : Math.max(8, rect.top - 488)) + 'px';
}}
document.addEventListener('click', e => {{
  const link = e.target.closest('.record-link');
  if (link) {{
    e.stopPropagation();
    if (_anchor === link) {{ closeTooltip(); return; }}
    _anchor = link;
    const r = RECORD_MAP.get(link.dataset.id);
    if (!r) {{ closeTooltip(); return; }}
    const fm = r.failure_mode || '—';
    let chips = '';
    if (r.arena_category && r.arena_category.length) r.arena_category.forEach(c => {{ chips += \`<span class="chip chip-tech">\${{c}}</span>\`; }});
    if (r.activity_type) chips += \`<span class="chip chip-scale">\${{r.activity_type}}</span>\`;
    const srcUrl = buildSrcUrl(r);
    const year = r.publish_date ? r.publish_date.slice(0,4) : (r.kb_year || '');
    _tooltip.innerHTML = \`
      <div class="rt-header"><span class="rt-id">\${{r.record_id}}</span><span class="rt-close" onclick="closeTooltip()">✕</span></div>
      <div class="rt-body">
        <div class="rt-project">\${{r.project_name || r.kb_associated_project || ''}}</div>
        \${{chips ? \`<div class="rt-chips">\${{chips}}</div>\` : ''}}
        <div class="rt-what">\${{r.what_happened || ''}}</div>
        \${{r.lesson_learnt ? \`<div class="rt-lesson">\${{r.lesson_learnt}}</div>\` : ''}}
        \${{r.evidence_excerpt ? \`<div class="rt-excerpt">"\${{r.evidence_excerpt}}"</div>\` : ''}}
        <div class="rt-footer">
          \${{r.lifecycle_phase ? \`<span class="badge" style="background:#64748b">\${{r.lifecycle_phase}}</span>\` : ''}}
          \${{fm !== '—' ? \`<span class="badge" style="background:\${{FM_COLOURS[fm]||'#64748b'}}">\${{fm}}</span>\` : ''}}
          \${{r.issue_severity ? \`<span class="badge" style="background:\${{IS_COLOURS[r.issue_severity]||'#94a3b8'}}">\${{r.issue_severity}}</span>\` : ''}}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:4px">
          \${{year ? \`<span style="font-size:14px;color:#94a3b8">\${{year}}</span>\` : '<span></span>'}}
          \${{srcUrl ? \`<a class="rt-src" href="\${{srcUrl}}" target="_blank">\${{srcUrl.includes('assets') ? 'Open PDF ↗' : 'Open source ↗'}}</a>\` : ''}}
        </div>
      </div>\`;
    _tooltip.style.display = 'block';
    positionTooltip(link);
    return;
  }}
  if (!e.target.closest('#record-tooltip')) closeTooltip();
}});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeTooltip(); }});
<\\/script>
</body>
</html>`;
}}

async function createPermalink(repId) {{
  const btn = document.querySelector(`[data-permalink="${{repId}}"]`);
  const list = loadReports();
  const rep = list.find(r => r.id === repId);
  if (!rep) return;
  if (btn) {{ btn.textContent = 'Generating…'; btn.disabled = true; }}
  try {{
    const html = generateReportHtml(rep);
    const res = await fetch('/save-report', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        id: rep.id,
        html,
        meta: {{
          filterDesc:  rep.filterDesc,
          mode:        rep.mode,
          date:        rep.date,
          recordCount: rep.recordCount,
          summary:     rep.summary || '',
        }},
      }}),
    }});
    const data = await res.json();
    await navigator.clipboard.writeText(data.url);
    if (btn) {{ btn.textContent = 'Copied!'; setTimeout(() => {{ btn.textContent = 'Permalink'; btn.disabled = false; }}, 2000); }}
  }} catch(e) {{
    if (btn) {{ btn.textContent = 'Error'; btn.disabled = false; }}
    console.error(e);
  }}
}}
</script>
</body>
</html>"""


DEDUPED_REGISTRY = ROOT / "insights" / "registry_deduped.yaml"


def main():
    parser = argparse.ArgumentParser(description="Build ARENA insights HTML dashboard")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--deduped", action="store_true",
                        help="Load from insights/registry_deduped.yaml instead of per_doc/")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.deduped:
        if not DEDUPED_REGISTRY.exists():
            raise SystemExit(f"Deduped registry not found: {DEDUPED_REGISTRY}\n"
                             f"Run: python scripts/04c_dedup_within_project.py first")
        records = load_deduped_records(DEDUPED_REGISTRY)
        print(f"Loaded {len(records)} deduped records from {DEDUPED_REGISTRY.name}")
    else:
        input_dir = Path(args.input)
        records = load_records(input_dir)
        if not records:
            raise SystemExit(f"No records found in {input_dir}")

    from concurrent.futures import ThreadPoolExecutor as _ThreadPool
    with _ThreadPool(max_workers=3) as tp:
        f_portfolio = tp.submit(load_portfolio_size)
        f_bench = tp.submit(load_benchmarks)
        f_qa = tp.submit(load_qa_results)
    portfolio_size = f_portfolio.result()
    benchmarks = f_bench.result()
    qa_results = f_qa.result()
    total_bench_rows = sum(len(v['rows']) for v in benchmarks.values())
    if not args.deduped:
        print(f"Loaded {len(records)} records from {Path(args.input)}")
    print(f"Loaded {total_bench_rows} benchmark rows across {len(benchmarks)} datasets")
    print(f"Loaded {len(qa_results)} QA verdicts from {QA_DIR}")

    html = build_html(records, portfolio_size, benchmarks, qa_results)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {output_path}")


if __name__ == "__main__":
    main()
