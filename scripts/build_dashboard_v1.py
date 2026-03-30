#!/usr/bin/env python3
"""
Build enhanced single-file HTML dashboard from v3_clean registry.
Includes analysis charts tab + filterable record browser.

Usage:
    python3 scripts/build_dashboard_v1.py
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed.")

ROOT = Path(__file__).resolve().parents[1]
REGISTRY   = ROOT / "insights" / "ARENA_delivery_registry_full_v3_clean.yaml"
MAPPING    = ROOT / "insights" / "registry_to_document_mapping.csv"
PROJECTS   = ROOT / "arena-projects-export_1772932404.csv"
OUTPUT     = ROOT / "dashboard" / "insights_v1.html"

FAILURE_COLOURS = {
    "no major failure stated":          "#22c55e",
    "design assumption failure":        "#f97316",
    "regulatory misfit":                "#a855f7",
    "data quality/measurement failure": "#eab308",
    "integration failure":              "#ef4444",
    "technical underperformance":       "#f43f5e",
    "commercial/demand failure":        "#14b8a6",
    "governance/coordination failure":  "#ec4899",
    "schedule slippage":                "#fb923c",
    "cost overrun":                     "#dc2626",
    "resource/capability shortfall":    "#6366f1",
}
OUTCOME_COLOURS = {
    "successful demonstration":          "#16a34a",
    "follow-on scale-up enabled":        "#15803d",
    "knowledge generated despite setback":"#3b82f6",
    "policy/market influence only":      "#8b5cf6",
    "partial success":                   "#ca8a04",
    "delayed but recoverable":           "#ea580c",
    "re-scoped/adapted":                 "#0891b2",
    "discontinued/not progressed":       "#dc2626",
}
ADVERSE_OUTCOMES = {
    "delayed but recoverable", "re-scoped/adapted",
    "knowledge generated despite setback", "discontinued/not progressed",
    "partial success", "policy/market influence only",
}

def load_data():
    with open(REGISTRY, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    # Build record_id → KB URL map
    url_map = {}
    if MAPPING.exists():
        with open(MAPPING, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url_map[row["record_id"]] = row.get("kb_document_page", "")

    # Portfolio size
    portfolio_size = 0
    portfolio_names = set()
    if PROJECTS.exists():
        with open(PROJECTS, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                portfolio_names.add(row["Project"].strip())
                portfolio_size += 1

    # Enrich records
    cleaned = []
    for r in records:
        rec = {k: (v if v is not None else "") for k, v in r.items()}
        rec["source_url"] = url_map.get(rec["record_id"], "")
        cleaned.append(rec)

    # Projects covered
    projects_covered = {r.get("csv_project_name","").strip() or r.get("project_name","").strip()
                        for r in cleaned if r.get("project_name")}
    n_covered = len(projects_covered & portfolio_names) if portfolio_names else len(projects_covered)

    return cleaned, portfolio_size, n_covered


def pct(n, total):
    return round(n / total * 100, 1) if total else 0


def analyse(records):
    n = len(records)
    adverse = [r for r in records if r.get("outcome_class") in ADVERSE_OUTCOMES]
    n_adverse = len(adverse)

    # Failure mode distribution
    fm_counts = Counter(r["failure_mode"] for r in records if r.get("failure_mode"))

    # Outcome class distribution
    oc_counts = Counter(r["outcome_class"] for r in records if r.get("outcome_class"))

    # Project type → failure mode breakdown (adverse rate)
    pt_data = defaultdict(lambda: {"total": 0, "adverse": 0, "failure_modes": Counter()})
    for r in records:
        pt = r.get("project_type", "")
        if not pt: continue
        pt_data[pt]["total"] += 1
        if r.get("outcome_class") in ADVERSE_OUTCOMES:
            pt_data[pt]["adverse"] += 1
        if r.get("failure_mode"):
            pt_data[pt]["failure_modes"][r["failure_mode"]] += 1

    # Proponent type → adverse rate
    prop_data = defaultdict(lambda: {"total": 0, "adverse": 0})
    for r in records:
        p = r.get("proponent_type", "")
        if not p: continue
        prop_data[p]["total"] += 1
        if r.get("outcome_class") in ADVERSE_OUTCOMES:
            prop_data[p]["adverse"] += 1

    # Lifecycle phase distribution
    phase_counts = Counter(r["lifecycle_phase"] for r in records if r.get("lifecycle_phase"))

    # Scale band
    scale_counts = Counter(r["project_scale_band"] for r in records if r.get("project_scale_band"))

    # Technology domain
    tech_counts = Counter(r["technology_domain"] for r in records if r.get("technology_domain"))

    # Top failure mode per project type
    pt_top_failure = {
        pt: d["failure_modes"].most_common(1)[0][0] if d["failure_modes"] else "—"
        for pt, d in pt_data.items()
    }

    return {
        "n": n, "n_adverse": n_adverse,
        "fm_counts": dict(fm_counts.most_common()),
        "oc_counts": dict(oc_counts.most_common()),
        "pt_data": {k: dict(v, failure_modes=dict(v["failure_modes"])) for k, v in pt_data.items()},
        "prop_data": dict(prop_data),
        "phase_counts": dict(phase_counts.most_common()),
        "scale_counts": dict(scale_counts.most_common()),
        "tech_counts": dict(tech_counts.most_common()),
        "pt_top_failure": pt_top_failure,
    }


def bar_chart(counts, colour_map=None, default_colour="#6366f1", max_label_len=45):
    """Generate a pure CSS horizontal bar chart from a counts dict."""
    if not counts:
        return ""
    total = sum(counts.values())
    max_val = max(counts.values())
    rows = []
    for label, count in sorted(counts.items(), key=lambda x: -x[1]):
        colour = (colour_map or {}).get(label, default_colour)
        width_pct = count / max_val * 100
        display_label = label[:max_label_len] if len(label) > max_label_len else label
        rows.append(f"""
        <div class="bar-row">
          <div class="bar-label" title="{label}">{display_label}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{width_pct:.1f}%;background:{colour}"></div>
          </div>
          <div class="bar-count">{count} <span class="bar-pct">({pct(count,total)}%)</span></div>
        </div>""")
    return "\n".join(rows)


def adverse_rate_chart(data, sort_by="rate"):
    """Adverse rate chart for proponent or project type."""
    items = [(k, v["total"], v["adverse"]) for k, v in data.items() if v["total"] >= 5]
    items.sort(key=lambda x: -x[2]/x[1])
    rows = []
    for label, total, adverse in items:
        rate = adverse / total * 100
        display = label[:42] if len(label) > 42 else label
        rows.append(f"""
        <div class="bar-row">
          <div class="bar-label" title="{label}">{display}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{rate:.1f}%;background:#ef4444"></div>
          </div>
          <div class="bar-count">{rate:.0f}% <span class="bar-pct">({adverse}/{total})</span></div>
        </div>""")
    return "\n".join(rows)


def build_html(records, portfolio_size, n_covered, stats):
    n = stats["n"]
    n_adverse = stats["n_adverse"]
    adverse_rate = pct(n_adverse, n)
    portfolio_pct = pct(n_covered, portfolio_size)
    data_json = json.dumps(records, ensure_ascii=False)
    fm_colours_json = json.dumps(FAILURE_COLOURS)
    oc_colours_json = json.dumps(OUTCOME_COLOURS)

    # Pre-build chart HTML
    fm_chart    = bar_chart(stats["fm_counts"], FAILURE_COLOURS)
    oc_chart    = bar_chart(stats["oc_counts"], OUTCOME_COLOURS)
    phase_chart = bar_chart(stats["phase_counts"], default_colour="#0891b2")
    scale_chart = bar_chart(stats["scale_counts"], default_colour="#7c3aed")
    tech_chart  = bar_chart(stats["tech_counts"],  default_colour="#059669")
    prop_chart  = adverse_rate_chart(stats["prop_data"])
    pt_chart    = adverse_rate_chart(stats["pt_data"])

    # Project type summary table
    pt_rows = ""
    for pt, d in sorted(stats["pt_data"].items(), key=lambda x: -x[1]["total"]):
        ar = pct(d["adverse"], d["total"])
        top_fm = stats["pt_top_failure"].get(pt, "—")
        colour = FAILURE_COLOURS.get(top_fm, "#64748b")
        pt_rows += f"""<tr>
          <td>{pt}</td>
          <td style="text-align:center">{d['total']}</td>
          <td style="text-align:center">{ar}%</td>
          <td><span class="badge" style="background:{colour}">{top_fm}</span></td>
        </tr>"""

    # Filter options
    def opts(field):
        vals = sorted({r[field] for r in records if r.get(field)})
        return "\n".join(f'<option value="{v}">{v}</option>' for v in vals)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARENA Delivery Insights</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f1f5f9; color:#1e293b; }}

header {{ background:#0f172a; color:white; padding:18px 32px; display:flex; align-items:center; justify-content:space-between; }}
header h1 {{ font-size:20px; font-weight:700; letter-spacing:-0.3px; }}
header span {{ font-size:12px; color:#94a3b8; }}

.stats {{ background:white; border-bottom:1px solid #e2e8f0; padding:14px 32px; display:flex; gap:40px; flex-wrap:wrap; }}
.stat {{ display:flex; flex-direction:column; }}
.stat-value {{ font-size:22px; font-weight:700; color:#0f172a; }}
.stat-sub {{ font-size:11px; color:#94a3b8; }}
.stat-label {{ font-size:11px; color:#64748b; margin-top:2px; }}

/* Tabs */
.tabs {{ background:white; border-bottom:2px solid #e2e8f0; padding:0 32px; display:flex; gap:0; }}
.tab {{ padding:14px 22px; font-size:13px; font-weight:600; color:#64748b; cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-2px; transition:color 0.15s; }}
.tab:hover {{ color:#1e293b; }}
.tab.active {{ color:#6366f1; border-bottom-color:#6366f1; }}
.tab-content {{ display:none; }}
.tab-content.active {{ display:block; }}

/* Analysis tab */
.analysis {{ padding:28px 32px; display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
.chart-card {{ background:white; border:1px solid #e2e8f0; border-radius:12px; padding:20px 22px; }}
.chart-card.full {{ grid-column:1/-1; }}
.chart-title {{ font-size:13px; font-weight:700; color:#0f172a; margin-bottom:4px; }}
.chart-subtitle {{ font-size:11px; color:#94a3b8; margin-bottom:16px; }}
.bar-row {{ display:flex; align-items:center; gap:10px; margin-bottom:7px; }}
.bar-label {{ font-size:11px; color:#475569; width:190px; min-width:190px; text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.bar-track {{ flex:1; background:#f1f5f9; border-radius:4px; height:18px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:4px; transition:width 0.3s; }}
.bar-count {{ font-size:11px; color:#64748b; width:90px; min-width:90px; white-space:nowrap; }}
.bar-pct {{ color:#94a3b8; }}

/* Summary table */
.summary-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
.summary-table th {{ text-align:left; padding:8px 10px; font-size:10px; text-transform:uppercase; letter-spacing:0.6px; color:#94a3b8; border-bottom:2px solid #e2e8f0; }}
.summary-table td {{ padding:8px 10px; border-bottom:1px solid #f1f5f9; color:#374151; }}
.summary-table tr:hover td {{ background:#f8fafc; }}

/* Records tab */
.records-layout {{ display:flex; height:calc(100vh - 180px); }}
aside {{ width:240px; min-width:240px; background:white; border-right:1px solid #e2e8f0; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }}
aside h2 {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; color:#64748b; }}
.filter-group label {{ font-size:10px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:0.4px; display:block; margin-bottom:3px; }}
.filter-group select, .search-box {{ font-size:12px; padding:5px 8px; border:1px solid #e2e8f0; border-radius:6px; background:#f8fafc; width:100%; color:#1e293b; }}
.filter-group select:focus, .search-box:focus {{ outline:none; border-color:#6366f1; }}
.clear-btn {{ font-size:11px; padding:6px; background:#f1f5f9; border:1px solid #e2e8f0; border-radius:6px; cursor:pointer; color:#475569; width:100%; }}
.clear-btn:hover {{ background:#e2e8f0; }}
main {{ flex:1; overflow-y:auto; padding:16px 20px; }}
.results-bar {{ font-size:12px; color:#64748b; margin-bottom:12px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:12px; }}
.card {{ background:white; border:1px solid #e2e8f0; border-radius:10px; padding:14px; cursor:pointer; transition:box-shadow 0.15s,border-color 0.15s; display:flex; flex-direction:column; gap:8px; }}
.card:hover {{ box-shadow:0 4px 16px rgba(0,0,0,0.08); border-color:#c7d2fe; }}
.card-top {{ display:flex; justify-content:space-between; }}
.card-id {{ font-size:10px; font-weight:700; color:#94a3b8; }}
.card-year {{ font-size:10px; color:#94a3b8; }}
.card-project {{ font-size:12px; font-weight:600; color:#1e293b; line-height:1.4; }}
.card-what {{ font-size:11px; color:#475569; line-height:1.6; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
.card-tags {{ display:flex; flex-wrap:wrap; gap:4px; }}
.tag {{ font-size:9px; font-weight:600; padding:2px 7px; border-radius:20px; color:white; }}
.tag-phase {{ background:#64748b; }}
.tag-scale {{ background:#0891b2; }}
.tag-tech {{ background:#7c3aed; }}
.card-footer {{ display:flex; justify-content:space-between; padding-top:6px; border-top:1px solid #f1f5f9; }}
.badge {{ font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px; color:white; }}

/* Modal */
.overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,0.4); z-index:100; align-items:center; justify-content:center; padding:24px; }}
.overlay.active {{ display:flex; }}
.modal {{ background:white; border-radius:14px; width:100%; max-width:740px; max-height:90vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.2); }}
.modal-header {{ padding:18px 22px 14px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:flex-start; position:sticky; top:0; background:white; z-index:1; }}
.modal-title {{ font-size:15px; font-weight:700; line-height:1.4; }}
.modal-sub {{ font-size:11px; color:#64748b; margin-top:3px; }}
.close-btn {{ font-size:18px; color:#94a3b8; cursor:pointer; flex-shrink:0; }}
.close-btn:hover {{ color:#1e293b; }}
.modal-body {{ padding:18px 22px; display:flex; flex-direction:column; gap:16px; }}
.ms-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.7px; color:#94a3b8; margin-bottom:4px; }}
.ms-value {{ font-size:13px; color:#1e293b; line-height:1.6; }}
.modal-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.excerpt {{ background:#f8fafc; border-left:3px solid #6366f1; padding:10px 12px; border-radius:0 8px 8px 0; font-size:12px; color:#374151; line-height:1.7; font-style:italic; }}
.modal-links {{ display:flex; gap:8px; flex-wrap:wrap; }}
.link-btn {{ font-size:11px; font-weight:600; padding:7px 12px; border-radius:7px; text-decoration:none; }}
.link-btn-primary {{ background:#6366f1; color:white; }}
.link-btn-primary:hover {{ background:#4f46e5; }}
.link-btn-secondary {{ background:#f1f5f9; color:#475569; border:1px solid #e2e8f0; }}
.link-btn-secondary:hover {{ background:#e2e8f0; }}
.modal-tags {{ display:flex; flex-wrap:wrap; gap:5px; }}
.conf-note {{ background:#fffbeb; border:1px solid #fde68a; border-radius:7px; padding:9px 11px; font-size:11px; color:#92400e; line-height:1.6; }}
.hidden {{ display:none !important; }}
</style>
</head>
<body>

<header>
  <h1>ARENA Delivery Insights</h1>
  <span>v3_clean registry · {n:,} records · {n_covered} of {portfolio_size} ARENA projects</span>
</header>

<div class="stats">
  <div class="stat">
    <span class="stat-value">{n:,}</span>
    <span class="stat-label">Delivery insight records</span>
  </div>
  <div class="stat">
    <span class="stat-value">{n_covered} <span style="font-size:14px;color:#94a3b8">of {portfolio_size}</span></span>
    <span class="stat-label">ARENA projects covered ({portfolio_pct}%)</span>
  </div>
  <div class="stat">
    <span class="stat-value" style="color:#ef4444">{adverse_rate}%</span>
    <span class="stat-label">Adverse outcome rate</span>
  </div>
  <div class="stat">
    <span class="stat-value">{stats['fm_counts'].get('design assumption failure',0)}</span>
    <span class="stat-label">Design assumption failures (#1 mode)</span>
  </div>
  <div class="stat">
    <span class="stat-value">{stats['fm_counts'].get('regulatory misfit',0)}</span>
    <span class="stat-label">Regulatory misfits (#2 mode)</span>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('analysis')">Analysis</div>
  <div class="tab" onclick="switchTab('records')">Record browser</div>
</div>

<!-- ANALYSIS TAB -->
<div class="tab-content active" id="tab-analysis">
<div class="analysis">

  <div class="chart-card">
    <div class="chart-title">Failure mode distribution</div>
    <div class="chart-subtitle">All {n:,} records · % of total</div>
    {fm_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Outcome class distribution</div>
    <div class="chart-subtitle">All {n:,} records · % of total</div>
    {oc_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Adverse outcome rate by proponent type</div>
    <div class="chart-subtitle">% of records with adverse outcome · min 5 records · sorted by rate</div>
    {prop_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Adverse outcome rate by project type</div>
    <div class="chart-subtitle">% of records with adverse outcome · min 5 records · sorted by rate</div>
    {pt_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Records by lifecycle phase</div>
    <div class="chart-subtitle">Where in the delivery journey insights are concentrated</div>
    {phase_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Records by project scale</div>
    <div class="chart-subtitle">Scale band distribution across all records</div>
    {scale_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Records by technology domain</div>
    <div class="chart-subtitle">Top technology domains by record count</div>
    {tech_chart}
  </div>

  <div class="chart-card">
    <div class="chart-title">Project type summary</div>
    <div class="chart-subtitle">Record count, adverse rate, and dominant failure mode per project type</div>
    <table class="summary-table">
      <thead><tr><th>Project type</th><th>Records</th><th>Adverse rate</th><th>Top failure mode</th></tr></thead>
      <tbody>{pt_rows}</tbody>
    </table>
  </div>

</div>
</div>

<!-- RECORDS TAB -->
<div class="tab-content" id="tab-records">
<div class="records-layout">
  <aside>
    <h2>Filters</h2>
    <input class="search-box" id="search" placeholder="Search…" type="text">
    <div class="filter-group"><label>Failure mode</label><select id="f-failure"><option value="">All</option>{opts("failure_mode")}</select></div>
    <div class="filter-group"><label>Outcome</label><select id="f-outcome"><option value="">All</option>{opts("outcome_class")}</select></div>
    <div class="filter-group"><label>Project type</label><select id="f-type"><option value="">All</option>{opts("project_type")}</select></div>
    <div class="filter-group"><label>Scale</label><select id="f-scale"><option value="">All</option>{opts("project_scale_band")}</select></div>
    <div class="filter-group"><label>Proponent</label><select id="f-proponent"><option value="">All</option>{opts("proponent_type")}</select></div>
    <div class="filter-group"><label>Lifecycle phase</label><select id="f-phase"><option value="">All</option>{opts("lifecycle_phase")}</select></div>
    <div class="filter-group"><label>Technology</label><select id="f-tech"><option value="">All</option>{opts("technology_domain")}</select></div>
    <button class="clear-btn" onclick="clearFilters()">Clear filters</button>
  </aside>
  <main>
    <div class="results-bar"><strong id="count-label">{n:,} records</strong> · click any card to view detail</div>
    <div class="cards" id="cards"></div>
  </main>
</div>
</div>

<!-- Modal -->
<div class="overlay" id="overlay" onclick="closeModal(event)">
  <div class="modal">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="m-title"></div>
        <div class="modal-sub" id="m-sub"></div>
      </div>
      <span class="close-btn" onclick="closeModalDirect()">✕</span>
    </div>
    <div class="modal-body">
      <div><div class="ms-label">What happened</div><div class="ms-value" id="m-what"></div></div>
      <div id="m-excerpt-wrap"><div class="ms-label">Evidence</div><div class="excerpt" id="m-excerpt"></div></div>
      <div class="modal-grid">
        <div><div class="ms-label">Failure mode</div><div id="m-failure"></div></div>
        <div><div class="ms-label">Outcome</div><div id="m-outcome"></div></div>
        <div><div class="ms-label">Lifecycle phase</div><div class="ms-value" id="m-phase"></div></div>
        <div><div class="ms-label">Delay category</div><div class="ms-value" id="m-delay"></div></div>
      </div>
      <div><div class="ms-label">Classification</div><div class="modal-tags" id="m-tags"></div></div>
      <div id="m-note-wrap"><div class="ms-label">Confidence note</div><div class="conf-note" id="m-note"></div></div>
      <div><div class="ms-label">Source</div><div class="modal-links" id="m-links"></div></div>
    </div>
  </div>
</div>

<script>
const RECORDS = {data_json};
const FM_COL = {fm_colours_json};
const OC_COL = {oc_colours_json};

function fmc(v) {{ return FM_COL[v] || '#64748b'; }}
function occ(v) {{ return OC_COL[v] || '#64748b'; }}

// Tab switching
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
  if (name === 'records') applyFilters();
}}

// Records
function renderCards(recs) {{
  const c = document.getElementById('cards');
  c.innerHTML = '';
  document.getElementById('count-label').textContent = recs.length.toLocaleString() + ' record' + (recs.length !== 1 ? 's' : '');
  if (!recs.length) {{
    c.innerHTML = '<div style="color:#94a3b8;font-size:13px;padding:20px">No records match.</div>';
    return;
  }}
  recs.forEach(r => {{
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openModal(r);
    const year = r.publish_date ? r.publish_date.toString().slice(0,4) : '';
    let tags = '';
    if (r.lifecycle_phase) tags += `<span class="tag tag-phase">${{r.lifecycle_phase}}</span>`;
    if (r.project_scale_band) tags += `<span class="tag tag-scale">${{r.project_scale_band}}</span>`;
    if (r.technology_domain) tags += `<span class="tag tag-tech">${{r.technology_domain}}</span>`;
    card.innerHTML = `
      <div class="card-top"><span class="card-id">${{r.record_id}}</span><span class="card-year">${{year}}</span></div>
      <div class="card-project">${{r.project_name || r.source_title}}</div>
      <div class="card-what">${{r.what_happened}}</div>
      <div class="card-tags">${{tags}}</div>
      <div class="card-footer">
        <span class="badge" style="background:${{fmc(r.failure_mode)}}">${{r.failure_mode || '—'}}</span>
        <span class="badge" style="background:${{occ(r.outcome_class)}}">${{r.outcome_class || '—'}}</span>
      </div>`;
    c.appendChild(card);
  }});
}}

function getFilters() {{
  return {{
    q: document.getElementById('search').value.toLowerCase(),
    failure: document.getElementById('f-failure').value,
    outcome: document.getElementById('f-outcome').value,
    type: document.getElementById('f-type').value,
    scale: document.getElementById('f-scale').value,
    proponent: document.getElementById('f-proponent').value,
    phase: document.getElementById('f-phase').value,
    tech: document.getElementById('f-tech').value,
  }};
}}

function applyFilters() {{
  const f = getFilters();
  const filtered = RECORDS.filter(r => {{
    if (f.failure && r.failure_mode !== f.failure) return false;
    if (f.outcome && r.outcome_class !== f.outcome) return false;
    if (f.type && r.project_type !== f.type) return false;
    if (f.scale && r.project_scale_band !== f.scale) return false;
    if (f.proponent && r.proponent_type !== f.proponent) return false;
    if (f.phase && r.lifecycle_phase !== f.phase) return false;
    if (f.tech && r.technology_domain !== f.tech) return false;
    if (f.q) {{
      const blob = [r.project_name,r.what_happened,r.evidence_excerpt,r.source_title].join(' ').toLowerCase();
      if (!blob.includes(f.q)) return false;
    }}
    return true;
  }});
  renderCards(filtered);
}}

function clearFilters() {{
  ['search','f-failure','f-outcome','f-type','f-scale','f-proponent','f-phase','f-tech'].forEach(id => {{
    document.getElementById(id).value = '';
  }});
  applyFilters();
}}

['search','f-failure','f-outcome','f-type','f-scale','f-proponent','f-phase','f-tech'].forEach(id => {{
  const el = document.getElementById(id);
  el.addEventListener('input', applyFilters);
  el.addEventListener('change', applyFilters);
}});

function openModal(r) {{
  document.getElementById('m-title').textContent = r.project_name || r.source_title;
  document.getElementById('m-sub').textContent = [r.record_id, r.source_title, r.publish_date].filter(Boolean).join(' · ');
  document.getElementById('m-what').textContent = r.what_happened;
  if (r.evidence_excerpt) {{
    document.getElementById('m-excerpt').textContent = r.evidence_excerpt;
    document.getElementById('m-excerpt-wrap').classList.remove('hidden');
  }} else document.getElementById('m-excerpt-wrap').classList.add('hidden');
  document.getElementById('m-failure').innerHTML = `<span class="badge" style="background:${{fmc(r.failure_mode)}}">${{r.failure_mode||'—'}}</span>`;
  document.getElementById('m-outcome').innerHTML = `<span class="badge" style="background:${{occ(r.outcome_class)}}">${{r.outcome_class||'—'}}</span>`;
  document.getElementById('m-phase').textContent = r.lifecycle_phase || '—';
  document.getElementById('m-delay').textContent = r.delay_category || '—';
  const tags = [];
  if (r.project_type) tags.push(['#1e40af', r.project_type]);
  if (r.project_scale_band) tags.push(['#0891b2', r.project_scale_band]);
  if (r.proponent_type) tags.push(['#7c3aed', r.proponent_type]);
  if (r.technology_domain) tags.push(['#059669', r.technology_domain]);
  document.getElementById('m-tags').innerHTML = tags.map(([c,v]) => `<span class="badge" style="background:${{c}}">${{v}}</span>`).join('');
  if (r.confidence_note) {{
    document.getElementById('m-note').textContent = r.confidence_note;
    document.getElementById('m-note-wrap').classList.remove('hidden');
  }} else document.getElementById('m-note-wrap').classList.add('hidden');
  const links = [];
  if (r.source_url) links.push(`<a class="link-btn link-btn-primary" href="${{r.source_url}}" target="_blank">📄 Source document</a>`);
  document.getElementById('m-links').innerHTML = links.join('') || '<span style="color:#94a3b8;font-size:12px">No source link available</span>';
  document.getElementById('overlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}}
function closeModal(e) {{ if (e.target === document.getElementById('overlay')) closeModalDirect(); }}
function closeModalDirect() {{ document.getElementById('overlay').classList.remove('active'); document.body.style.overflow=''; }}
document.addEventListener('keydown', e => {{ if (e.key==='Escape') closeModalDirect(); }});

renderCards(RECORDS);
</script>
</body>
</html>"""


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records, portfolio_size, n_covered = load_data()
    stats = analyse(records)
    print(f"Loaded {len(records):,} records")
    html = build_html(records, portfolio_size, n_covered, stats)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard written → {OUTPUT}")
    print(f"File size: {OUTPUT.stat().st_size/1024:.0f} KB")

if __name__ == "__main__":
    main()
