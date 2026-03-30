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
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "insights" / "per_doc"
DEFAULT_OUTPUT = ROOT / "dashboard" / "insights.html"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
AGGREGATED_DIR = ROOT / "tables" / "aggregated"

FAILURE_MODE_COLOURS = {
    "no major failure stated":        "#22c55e",
    "design assumption failure":      "#f97316",
    "regulatory misfit":              "#a855f7",
    "data quality/measurement failure": "#eab308",
    "integration failure":            "#ef4444",
    "technical underperformance":     "#f43f5e",
    "commercial/demand failure":      "#14b8a6",
    "governance/coordination failure":"#ec4899",
    "schedule slippage":              "#fb923c",
    "cost overrun":                   "#dc2626",
    "resource/capability shortfall":  "#6366f1",
}

OUTCOME_COLOURS = {
    "successful demonstration":        "#16a34a",
    "follow-on scale-up enabled":      "#15803d",
    "knowledge generated despite setback": "#3b82f6",
    "policy/market influence only":    "#8b5cf6",
    "partial success":                 "#ca8a04",
    "delayed but recoverable":         "#ea580c",
    "re-scoped/adapted":               "#0891b2",
    "discontinued/not progressed":     "#dc2626",
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
    records = []
    for path in sorted(glob.glob(str(input_dir / "doc_*.yaml"))):
        with open(path, encoding="utf-8") as f:
            recs = yaml.safe_load(f)
            if recs:
                records.extend(recs)
    return records


def load_deduped_records(registry_path: Path) -> list[dict]:
    with open(registry_path, encoding="utf-8") as f:
        records = yaml.safe_load(f)
    return records if records else []


def load_qa_results() -> dict:
    """Load QA verdicts from per_doc_qa/, keyed by record_id."""
    qa = {}
    if not QA_DIR.exists():
        return qa
    for path in sorted(glob.glob(str(QA_DIR / "doc_*_qa.yaml"))):
        with open(path, encoding="utf-8") as f:
            results = yaml.safe_load(f)
            if results:
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
            r["qa_verdict"]      = qa_results[rid].get("verdict") or ""
            r["qa_source_text"]  = qa_results[rid].get("source_text") or ""
            r["qa_source_page"]  = qa_results[rid].get("source_page") or ""
            r["qa_note"]         = qa_results[rid].get("note") or ""
        else:
            r["qa_verdict"] = r["qa_source_text"] = r["qa_source_page"] = r["qa_note"] = ""

    records = [clean_record(r) for r in records]
    data_json = json.dumps(records, ensure_ascii=False)
    fm_colours = json.dumps(FAILURE_MODE_COLOURS)
    oc_colours = json.dumps(OUTCOME_COLOURS)
    is_colours = json.dumps(ISSUE_SEVERITY_COLOURS)
    qa_colours = json.dumps(QA_VERDICT_COLOURS)
    benchmarks_json = json.dumps(benchmarks or {}, ensure_ascii=False)
    arena_root = str(ROOT).replace("\\", "/")

    failure_modes = distinct_sorted(records, "failure_mode")
    project_types = distinct_sorted(records, "project_type")
    proponent_types = distinct_sorted(records, "proponent_type")
    outcome_classes = distinct_sorted(records, "outcome_class")
    lifecycle_phases = distinct_sorted(records, "lifecycle_phase")
    tech_domains = distinct_sorted(records, "technology_domain")
    scale_bands = distinct_sorted(records, "project_scale_band")
    severity_levels = distinct_sorted(records, "issue_severity")
    transferability_vals = distinct_sorted(records, "transferability")
    qa_verdicts = distinct_sorted(records, "qa_verdict")

    def options(values):
        return "\n".join(f'<option value="{v}">{v}</option>' for v in values)

    n = len(records)
    n_projects_covered = len({r["kb_associated_project"] for r in records if r.get("in_arena_portfolio")})
    portfolio_pct = f"{n_projects_covered/portfolio_size*100:.0f}%" if portfolio_size else "—"
    n_failures = len([r for r in records if r.get("failure_mode") and r["failure_mode"] != "no major failure stated"])
    kb_projects = distinct_sorted(records, "kb_associated_project")

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
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; }}

  /* Header */
  header {{ background: #0f172a; color: white; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 20px; font-weight: 600; letter-spacing: -0.3px; }}
  header span {{ font-size: 13px; color: #94a3b8; }}

  /* Tab navigation */
  .tabs {{ background: white; border-bottom: 2px solid #e2e8f0; padding: 0 32px; display: flex; }}
  .tab {{ padding: 14px 22px; font-size: 13px; font-weight: 600; color: #64748b; cursor: pointer;
          border-bottom: 3px solid transparent; margin-bottom: -2px; transition: color 0.15s; }}
  .tab:hover {{ color: #1e293b; }}
  .tab.active {{ color: #6366f1; border-bottom-color: #6366f1; }}
  .tab-content {{ display: none; flex-direction: column; }}
  .tab-content.active {{ display: flex; }}

  /* Stats bar */
  .stats {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 32px; display: flex; gap: 32px; }}
  .stat {{ display: flex; flex-direction: column; }}
  .stat-value {{ font-size: 24px; font-weight: 700; color: #0f172a; }}
  .stat-label {{ font-size: 12px; color: #64748b; margin-top: 2px; }}

  /* Layout */
  .layout {{ display: flex; height: calc(100vh - 163px); }}

  /* Sidebar */
  aside {{ width: 260px; min-width: 260px; background: white; border-right: 1px solid #e2e8f0; overflow-y: auto; padding: 20px 16px; display: flex; flex-direction: column; gap: 16px; }}
  aside h2 {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 6px; }}
  .filter-group label {{ font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }}
  .filter-group select {{ font-size: 13px; padding: 6px 8px; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; color: #1e293b; width: 100%; }}
  .filter-group select:focus {{ outline: none; border-color: #6366f1; }}
  .search-box {{ font-size: 13px; padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 6px; width: 100%; background: #f8fafc; }}
  .search-box:focus {{ outline: none; border-color: #6366f1; }}
  .clear-btn {{ font-size: 12px; padding: 7px 12px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; color: #475569; width: 100%; }}
  .clear-btn:hover {{ background: #e2e8f0; }}

  /* Main content */
  main {{ flex: 1; overflow-y: auto; padding: 20px 24px; }}
  .results-header {{ font-size: 13px; color: #64748b; margin-bottom: 14px; }}
  .results-header strong {{ color: #1e293b; }}

  /* Cards */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px; }}
  .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; display: flex; flex-direction: column; gap: 10px; }}
  .card:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-color: #c7d2fe; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .card-id {{ font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; white-space: nowrap; }}
  .card-year {{ font-size: 10px; color: #94a3b8; white-space: nowrap; }}
  .card-project {{ font-size: 13px; font-weight: 600; color: #1e293b; line-height: 1.4; }}
  .card-chips {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }}
  .chip {{ font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }}
  .chip-scale {{ background: #e0f2fe; color: #0369a1; }}
  .chip-tech  {{ background: #ede9fe; color: #6d28d9; }}
  .card-what {{ font-size: 12px; color: #475569; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
  .card-footer {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 10px; padding-top: 8px; border-top: 1px solid #f1f5f9; }}
  .card-meta-item {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; overflow: hidden; }}
  .card-meta-label {{ font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }}
  .badge {{ font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 20px; color: white;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block; }}

  /* Modal */
  .overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; align-items: center; justify-content: center; padding: 24px; }}
  .overlay.active {{ display: flex; }}
  .modal {{ background: white; border-radius: 14px; width: 100%; max-width: 760px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }}
  .modal-header {{ padding: 20px 24px 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; position: sticky; top: 0; background: white; z-index: 1; }}
  .modal-title {{ font-size: 16px; font-weight: 700; color: #0f172a; line-height: 1.4; }}
  .modal-sub {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
  .close-btn {{ font-size: 20px; color: #94a3b8; cursor: pointer; line-height: 1; flex-shrink: 0; padding: 4px; }}
  .close-btn:hover {{ color: #1e293b; }}
  .modal-body {{ padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; }}
  .modal-section {{ display: flex; flex-direction: column; gap: 6px; }}
  .modal-section-label {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; }}
  .modal-section-value {{ font-size: 14px; color: #1e293b; line-height: 1.6; }}
  .modal-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .excerpt {{ background: #f8fafc; border-left: 3px solid #6366f1; padding: 12px 14px; border-radius: 0 8px 8px 0; font-size: 13px; color: #374151; line-height: 1.7; font-style: italic; }}
  .modal-links {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .link-btn {{ font-size: 12px; font-weight: 600; padding: 8px 14px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
  .link-btn-primary {{ background: #6366f1; color: white; }}
  .link-btn-primary:hover {{ background: #4f46e5; }}
  .link-btn-secondary {{ background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
  .link-btn-secondary:hover {{ background: #e2e8f0; }}
  .confidence-note {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 12px; font-size: 12px; color: #92400e; line-height: 1.6; }}
  .modal-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .hidden {{ display: none !important; }}

  /* ── Synthesis ── */
  .synth-btn {{ font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 6px;
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
  .synth-title {{ font-size: 15px; font-weight: 700; color: #0f172a; }}
  .synth-meta {{ font-size: 11px; color: #94a3b8; margin-top: 3px; }}
  .synth-body {{ padding: 20px 24px; overflow-y: auto; flex: 1; }}
  .synth-text {{ font-size: 13px; color: #1e293b; line-height: 1.8; }}
  .synth-text h1 {{ font-size: 17px; font-weight: 700; margin: 18px 0 8px; color: #0f172a; }}
  .synth-text h2 {{ font-size: 15px; font-weight: 700; margin: 16px 0 6px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
  .synth-text h3 {{ font-size: 13px; font-weight: 700; margin: 12px 0 4px; color: #1e293b; }}
  .synth-text p {{ margin: 6px 0; }}
  .synth-text ul, .synth-text ol {{ margin: 6px 0 6px 20px; }}
  .synth-text li {{ margin: 3px 0; }}
  .synth-text strong {{ font-weight: 700; color: #0f172a; }}
  .synth-text hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }}
  .synth-text code {{ font-family: monospace; font-size: 12px; background: #f1f5f9; padding: 1px 4px; border-radius: 3px; }}
  .synth-cursor {{ display: inline-block; width: 2px; height: 14px; background: #6366f1;
                  animation: blink 0.8s step-end infinite; vertical-align: middle; margin-left: 2px; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  .synth-key-form {{ display: flex; flex-direction: column; gap: 10px; padding: 20px 0; }}
  .synth-key-input {{ font-size: 13px; padding: 9px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
                     width: 100%; font-family: monospace; }}
  .synth-key-input:focus {{ outline: none; border-color: #6366f1; }}
  .synth-key-btn {{ font-size: 13px; font-weight: 600; padding: 9px 18px; background: #6366f1; color: white;
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
  #record-tooltip .rt-id {{ font-size: 10px; color: #6366f1; font-weight: 700; letter-spacing: .5px; }}
  #record-tooltip .rt-close {{ font-size: 14px; color: #94a3b8; cursor: pointer; line-height: 1; padding: 2px 4px; }}
  #record-tooltip .rt-close:hover {{ color: #475569; }}
  #record-tooltip .rt-body {{ padding: 10px 14px 14px; font-size: 12px; line-height: 1.6; display: flex; flex-direction: column; gap: 6px; }}
  #record-tooltip .rt-project {{ font-weight: 700; color: #1e293b; font-size: 13px; }}
  #record-tooltip .rt-chips {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  #record-tooltip .rt-what {{ color: #334155; }}
  #record-tooltip .rt-lesson {{ color: #475569; font-style: italic; }}
  #record-tooltip .rt-excerpt {{ font-size: 11px; color: #64748b; background: #f8fafc;
                                border-left: 3px solid #e2e8f0; padding: 6px 8px; border-radius: 0 4px 4px 0; }}
  #record-tooltip .rt-footer {{ display: flex; flex-wrap: wrap; gap: 6px; padding-top: 4px; border-top: 1px solid #f1f5f9; }}
  #record-tooltip .rt-meta {{ font-size: 10px; color: #64748b; }}
  #record-tooltip .rt-src {{ font-size: 11px; color: #6366f1; text-decoration: none; }}
  #record-tooltip .rt-src:hover {{ text-decoration: underline; }}

  /* Reports tab */
  .rep-list {{ display: flex; flex-direction: column; gap: 12px; padding: 24px; max-width: 900px; }}
  .rep-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px;
              padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; }}
  .rep-card-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }}
  .rep-card-title {{ font-size: 14px; font-weight: 700; color: #1e293b; cursor: pointer; }}
  .rep-card-title:hover {{ color: #6366f1; }}
  .rep-card-meta {{ font-size: 11px; color: #94a3b8; }}
  .rep-card-summary {{ font-size: 12px; color: #475569; line-height: 1.5; }}
  .rep-card-actions {{ display: flex; gap: 8px; flex-shrink: 0; }}
  .rep-action-btn {{ font-size: 11px; padding: 4px 10px; border-radius: 5px; border: 1px solid #e2e8f0;
                    background: #f8fafc; color: #475569; cursor: pointer; white-space: nowrap; }}
  .rep-action-btn:hover {{ background: #f1f5f9; }}
  .rep-empty {{ padding: 48px 24px; color: #94a3b8; font-size: 14px; text-align: center; }}

  /* New v1.3 card elements */
  .card-lesson {{
    font-size: 11px; color: #166534; background: #f0fdf4;
    border-left: 3px solid #22c55e; padding: 6px 8px; border-radius: 4px;
    line-height: 1.5;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .card-top-right {{ display: flex; align-items: center; gap: 6px; }}
  .card-src-btn {{
    font-size: 10px; color: #6366f1; text-decoration: none;
    padding: 2px 5px; border: 1px solid #c7d2fe; border-radius: 4px; line-height: 1.4;
  }}
  .card-src-btn:hover {{ background: #eef2ff; }}
  .lesson-value {{ color: #166534; background: #f0fdf4; padding: 8px 10px; border-radius: 6px;
                  border-left: 3px solid #22c55e; line-height: 1.6; }}
  .qa-excerpt {{ background: #fefce8; border-left: 3px solid #ca8a04; padding: 10px 14px;
                border-radius: 0 8px 8px 0; font-size: 13px; color: #374151; line-height: 1.7;
                font-style: italic; }}
  .src-link {{
    display: inline-block; font-size: 11px; font-weight: 600; padding: 5px 10px;
    border-radius: 6px; text-decoration: none; margin-right: 6px; margin-top: 4px;
    background: #6366f1; color: white;
  }}
  .src-link:hover {{ opacity: 0.85; }}
  .src-link-md   {{ background: #0891b2; }}
  .src-link-kb   {{ background: #64748b; }}
  .src-link-proj {{ background: #7c3aed; }}
  .corroboration-badge {{
    font-size: 10px; font-weight: 700; color: #0891b2;
    background: #e0f2fe; border: 1px solid #bae6fd;
    padding: 2px 6px; border-radius: 12px; white-space: nowrap;
  }}

  /* ── Project summary panel ── */
  .proj-summary {{ background: white; border-bottom: 2px solid #e2e8f0; padding: 16px 32px 18px; display: none; }}
  .proj-summary.visible {{ display: block; }}
  .proj-summary-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 14px; }}
  .proj-summary-title {{ font-size: 15px; font-weight: 700; color: #0f172a; }}
  .proj-meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 5px; }}
  .proj-meta-tag {{ font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #f1f5f9; color: #475569; font-weight: 500; }}
  .coverage-strip {{ display: flex; gap: 20px; font-size: 12px; color: #64748b; flex-shrink: 0; padding-top: 2px; }}
  .coverage-strip strong {{ color: #0f172a; }}
  .phase-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; }}
  .phase-col {{ display: flex; flex-direction: column; gap: 4px; }}
  .phase-col-label {{ font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: #94a3b8; line-height: 1.3; min-height: 26px; display: flex; align-items: flex-end; }}
  .phase-dots {{ display: flex; flex-wrap: wrap; gap: 3px; min-height: 18px; padding: 5px 0 2px; border-top: 2px solid #f1f5f9; }}
  .phase-dots.has-dots {{ border-top-color: #cbd5e1; }}
  .phase-dot {{ width: 10px; height: 10px; border-radius: 50%; cursor: pointer; flex-shrink: 0; transition: transform 0.1s; }}
  .phase-dot:hover {{ transform: scale(1.4); }}
  .phase-empty-msg {{ font-size: 10px; color: #e2e8f0; padding-top: 3px; }}

  /* ── Pagination ── */
  .pagination {{ display: flex; align-items: center; gap: 10px; padding: 12px 0 4px; }}
  .page-btn {{ font-size: 12px; font-weight: 600; padding: 5px 12px; border: 1px solid #e2e8f0;
              border-radius: 6px; background: #f8fafc; cursor: pointer; color: #475569; }}
  .page-btn:hover {{ background: #eef2ff; border-color: #c7d2fe; color: #6366f1; }}
  .page-btn:disabled {{ opacity: 0.35; cursor: default; pointer-events: none; }}
  .page-info {{ font-size: 12px; color: #64748b; }}

  /* ── Analysis tab ── */
  .an-page {{ display: flex; flex-direction: column; height: calc(100vh - 108px); overflow: hidden; }}
  .an-stats {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 32px; display: flex; gap: 32px; flex-shrink: 0; }}
  .an-grid {{ padding: 20px 24px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; overflow-y: auto; flex: 1; }}
  .an-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }}
  .an-card.an-wide {{ grid-column: span 2; }}
  .an-card-title {{ font-size: 12px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.4px; }}
  .an-card-sub {{ font-size: 11px; color: #94a3b8; }}
  .an-card canvas {{ max-height: 280px; }}
  .an-card.an-wide canvas {{ max-height: 340px; }}

  /* ── Benchmarks tab ── */
  .bench-layout {{ display: flex; height: calc(100vh - 120px); }}
  .bench-nav {{ width: 220px; min-width: 220px; background: white; border-right: 1px solid #e2e8f0;
               padding: 16px 12px; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; }}
  .bench-nav-btn {{ font-size: 12px; font-weight: 600; padding: 10px 12px; border-radius: 8px;
                   border: 1px solid #e2e8f0; background: #f8fafc; cursor: pointer; text-align: left;
                   color: #374151; display: flex; justify-content: space-between; align-items: center; }}
  .bench-nav-btn:hover {{ background: #eef2ff; border-color: #c7d2fe; }}
  .bench-nav-btn.active {{ background: #6366f1; color: white; border-color: #6366f1; }}
  .bench-main {{ flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }}
  .bench-header {{ display: flex; flex-direction: column; gap: 3px; }}
  .bench-title {{ font-size: 16px; font-weight: 700; color: #0f172a; }}
  .bench-desc {{ font-size: 12px; color: #64748b; }}
  .bench-chart-wrap {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px;
                       position: relative; }}
  .bench-chart-wrap canvas {{ max-height: 300px; }}
  .bench-controls {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .bench-search {{ font-size: 13px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
                  width: 260px; background: #f8fafc; }}
  .bench-search:focus {{ outline: none; border-color: #6366f1; }}
  .bench-filter {{ font-size: 13px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; color: #1e293b; }}
  .bench-count {{ font-size: 12px; color: #64748b; margin-left: auto; }}
  .bench-table-wrap {{ overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 10px; }}
  .bench-table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
  .bench-table th {{ background: #f8fafc; padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 700;
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
    <div class="stat"><span class="stat-value">{n_projects_covered} <span style="font-size:14px;color:#64748b">of {portfolio_size} ({portfolio_pct})</span></span><span class="stat-label">ARENA portfolio covered</span></div>
    <div class="stat"><span class="stat-value">{n_failures}</span><span class="stat-label">With failure mode</span></div>
    <div class="stat"><span class="stat-value">{len(records) - n_failures}</span><span class="stat-label">No major failure</span></div>
  </div>
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
  <div class="layout">
    <aside>
      <div class="filter-group">
        <label>ARENA project</label>
        <input class="search-box" id="f-project" list="project-datalist" placeholder="Type to search projects…" autocomplete="off">
        <datalist id="project-datalist">{options(kb_projects)}</datalist>
      </div>
      <div><h2>Filters</h2></div>
      <input class="search-box" id="search" placeholder="Search projects, findings…" type="text">
      <div class="filter-group">
        <label>Failure mode</label>
        <select id="f-failure"><option value="">All</option>{options(failure_modes)}</select>
      </div>
      <div class="filter-group">
        <label>Outcome</label>
        <select id="f-outcome"><option value="">All</option>{options(outcome_classes)}</select>
      </div>
      <div class="filter-group">
        <label>Project type</label>
        <select id="f-type"><option value="">All</option>{options(project_types)}</select>
      </div>
      <div class="filter-group">
        <label>Scale</label>
        <select id="f-scale"><option value="">All</option>{options(scale_bands)}</select>
      </div>
      <div class="filter-group">
        <label>Proponent type</label>
        <select id="f-proponent"><option value="">All</option>{options(proponent_types)}</select>
      </div>
      <div class="filter-group">
        <label>Lifecycle phase</label>
        <select id="f-phase"><option value="">All</option>{options(lifecycle_phases)}</select>
      </div>
      <div class="filter-group">
        <label>Technology domain</label>
        <select id="f-tech"><option value="">All</option>{options(tech_domains)}</select>
      </div>
      <div class="filter-group">
        <label>Severity</label>
        <select id="f-severity"><option value="">All</option>{options(severity_levels)}</select>
      </div>
      <div class="filter-group">
        <label>Transferability</label>
        <select id="f-transferability"><option value="">All</option>{options(transferability_vals)}</select>
      </div>
      <div class="filter-group">
        <label>QA verdict</label>
        <select id="f-qa"><option value="">All</option>{options(qa_verdicts)}</select>
      </div>
      <button class="clear-btn" onclick="clearFilters()">Clear all filters</button>
    </aside>
    <main>
      <div class="results-header" style="display:flex;align-items:center">
        <span><strong id="count-label">{n} records</strong> · click any card to view detail</span>
        <select id="synth-mode" style="font-size:12px;padding:5px 8px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;color:#475569;margin-left:12px;cursor:pointer">
          <option value="brief">Brief summary</option>
          <option value="short">Short report</option>
          <option value="detailed" selected>Detailed report</option>
        </select>
        <button class="synth-btn" id="synth-btn" onclick="openSynth()">Synthesise</button>
      </div>
      <div style="padding:8px 0 4px 0">
        <textarea id="synth-context" rows="2"
          placeholder="Optional: add focus or context for the synthesis — e.g. 'focus on grid connection risks' or 'I need evidence to assess a hydrogen proposal at approvals stage'"
          style="width:100%;font-size:12px;padding:7px 10px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;color:#1e293b;resize:vertical;font-family:inherit;box-sizing:border-box"></textarea>
      </div>
      <div class="pagination">
        <button class="page-btn" id="btn-prev" onclick="changePage(-1)">&#8592; Prev</button>
        <span class="page-info" id="page-info"></span>
        <button class="page-btn" id="btn-next" onclick="changePage(1)">Next &#8594;</button>
      </div>
      <div class="cards" id="cards"></div>
    </main>
  </div>
</div>

<!-- ── Analysis tab ── -->
<div class="tab-content" id="tc-analysis">
  <div class="an-page">
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
        <div class="an-card-title">Failure rate by project type</div>
        <div class="an-card-sub">% of records with any failure mode, by delivery archetype</div>
        <canvas id="an-type-fail"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Failure modes by technology domain</div>
        <div class="an-card-sub">Top 8 technology domains — stacked by failure type</div>
        <canvas id="an-tech-fm"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Outcome class distribution</div>
        <div class="an-card-sub">How projects resolved delivery events</div>
        <canvas id="an-outcomes"></canvas>
      </div>
      <div class="an-card">
        <div class="an-card-title">Issue severity distribution</div>
        <div class="an-card-sub">Magnitude of delivery issues across all records</div>
        <canvas id="an-severity"></canvas>
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
    </div>
  </div>
</div>

<!-- ── Benchmarks tab ── -->
<div class="tab-content" id="tc-benchmarks">
  <div class="bench-layout">
    <div class="bench-nav" id="bench-nav"></div>
    <div class="bench-main" id="bench-main">
      <div style="color:#94a3b8;padding:40px;font-size:14px;text-align:center">
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
          <div class="modal-section-label">Outcome</div>
          <div id="m-outcome"></div>
        </div>
        <div class="modal-section">
          <div class="modal-section-label">Lifecycle phase</div>
          <div class="modal-section-value" id="m-phase"></div>
        </div>
        <div class="modal-section">
          <div class="modal-section-label">Delay category</div>
          <div class="modal-section-value" id="m-delay"></div>
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
        <div style="font-size:12px;color:#64748b;margin-top:6px" id="m-qa-note"></div>
      </div>
      <div id="m-corr-wrap" class="modal-section">
        <div class="modal-section-label">Corroboration</div>
        <div class="modal-section-value" id="m-corr"></div>
        <div style="font-size:12px;color:#64748b;margin-top:4px" id="m-corr-titles"></div>
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
const OC_COLOURS = {oc_colours};
const IS_COLOURS = {is_colours};
const QA_COLOURS = {qa_colours};
const ARENA_ROOT = '{arena_root}';
const BENCHMARKS = {benchmarks_json};

// ── Tab switching ──────────────────────────────────────────────
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('tc-' + name).classList.add('active');
  if (name === 'analysis') initAnalysis();
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
    const oc = r.outcome_class || '—';
    const fmCol = FM_COLOURS[fm] || '#64748b';
    const ocCol = OC_COLOURS[oc] || '#64748b';
    const isCol = IS_COLOURS[r.issue_severity] || '#94a3b8';
    const srcUrl = buildSrcUrl(r);
    let chips = '';
    if (r.project_scale_band) chips += `<span class="chip chip-scale">${{r.project_scale_band}}</span>`;
    if (r.technology_domain)  chips += `<span class="chip chip-tech">${{r.technology_domain}}</span>`;
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
          ${{oc !== '—' ? `<span class="badge" style="background:${{ocCol}}">${{oc}}</span>` : ''}}
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

function renderReports() {{
  const list = loadReports();
  const tab = document.getElementById('tab-reports');
  if (tab) tab.textContent = list.length ? `Reports (${{list.length}})` : 'Reports';
  const el = document.getElementById('rep-list');
  if (!list.length) {{
    el.innerHTML = '<div class="rep-empty">No reports saved yet. Run a synthesis and it will appear here automatically.</div>';
    return;
  }}
  el.innerHTML = list.map(rep => {{
    const modeLabel = rep.mode === 'brief' ? 'Brief' : rep.mode === 'short' ? 'Short' : 'Detailed';
    const dateStr = new Date(rep.date).toLocaleDateString('en-AU', {{day:'numeric',month:'short',year:'numeric'}});
    return `<div class="rep-card">
      <div class="rep-card-header">
        <div>
          <div class="rep-card-title" onclick="openReport('${{rep.id}}')">${{modeLabel}} · ${{rep.filterDesc}}</div>
          <div class="rep-card-meta">${{dateStr}} · ${{rep.recordCount}} records</div>
        </div>
        <div class="rep-card-actions">
          <button class="rep-action-btn" onclick="openReport('${{rep.id}}')">Open</button>
          <button class="rep-action-btn" data-permalink="${{rep.id}}" onclick="createPermalink('${{rep.id}}')">Permalink</button>
          <button class="rep-action-btn" onclick="navigator.clipboard.writeText('${{reportUrl(rep.id)}}').then(()=>this.textContent='Copied!').catch(()=>{{}});setTimeout(()=>this.textContent='Copy link',1500)">Copy link</button>
          <button class="rep-action-btn" style="color:#dc2626" onclick="if(confirm('Delete this report?'))deleteReport('${{rep.id}}')">Delete</button>
        </div>
      </div>
      ${{rep.summary ? `<div class="rep-card-summary">${{rep.summary}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

// ── Delivery Records ──────────────────────────────────────────
function fmColour(v) {{ return FM_COLOURS[v] || '#64748b'; }}
function ocColour(v) {{ return OC_COLOURS[v] || '#64748b'; }}
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
    container.innerHTML = '<div style="color:#94a3b8;font-size:14px;padding:20px">No records match the current filters.</div>';
    return;
  }}
  pageRecs.forEach(r => {{
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openModal(r);
    const year = r.publish_date ? r.publish_date.slice(0,4) : (r.kb_year || '');
    const fm = r.failure_mode || '—';
    const oc = r.outcome_class || '—';
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
    // Project-level chips (scale + tech) — shown under project name
    let chips = '';
    if (r.project_scale_band) chips += `<span class="chip chip-scale">${{r.project_scale_band}}</span>`;
    if (r.technology_domain)  chips += `<span class="chip chip-tech">${{r.technology_domain}}</span>`;
    // Record-level footer items — labelled
    const footerItems = [];
    if (r.lifecycle_phase)  footerItems.push(['Stage',    `<span class="badge" style="background:#64748b">${{r.lifecycle_phase}}</span>`]);
    if (r.failure_mode)     footerItems.push(['Type',     `<span class="badge" style="background:${{fmColour(fm)}}">${{fm}}</span>`]);
    if (r.issue_severity)   footerItems.push(['Severity', `<span class="badge" style="background:${{isColour(r.issue_severity)}}">${{r.issue_severity}}</span>`]);
    if (r.outcome_class)    footerItems.push(['Outcome',  `<span class="badge" style="background:${{ocColour(oc)}}">${{oc}}</span>`]);
    const footerHtml = footerItems.map(([label, badge]) =>
      `<div class="card-meta-item"><span class="card-meta-label">${{label}}</span>${{badge}}</div>`
    ).join('');
    card.innerHTML = `
      <div class="card-top">
        <span class="card-id">${{r.record_id}}</span>
        <div class="card-top-right">${{corrBadge}}<span class="card-year">${{year}}</span>${{srcBtn}}</div>
      </div>
      <div class="card-project">${{r.project_name || r.source_title}}</div>
      ${{chips ? `<div class="card-chips">${{chips}}</div>` : ''}}
      <div class="card-what">${{r.what_happened}}</div>
      ${{lessonEl}}
      <div class="card-footer">${{footerHtml}}</div>`;
    container.appendChild(card);
  }});
}}

const ALL_FILTER_IDS = ['search','f-failure','f-outcome','f-type','f-scale','f-proponent','f-phase','f-tech','f-project','f-severity','f-transferability','f-qa'];
const PROJECT_SET = new Set(RECORDS.map(r => r.kb_associated_project).filter(Boolean));
const PAGE_SIZE = 50;
let _curPage = 0, _lastFiltered = [];

// ── Project summary panel ───────────────────────────────────────
const PHASES = [
  'concept/feasibility','development/design','approvals/contracting','procurement',
  'construction/installation','commissioning/integration','operations','variation/re-scope'
];
const PHASE_LABELS = {{
  'concept/feasibility':       'Concept / Feasibility',
  'development/design':        'Development / Design',
  'approvals/contracting':     'Approvals / Contracting',
  'procurement':               'Procurement',
  'construction/installation': 'Construction / Installation',
  'commissioning/integration': 'Commissioning / Integration',
  'operations':                'Operations',
  'variation/re-scope':        'Variation / Re-scope',
}};

function setLayoutHeight() {{
  const ps = document.getElementById('proj-summary');
  const layout = document.querySelector('.layout');
  if (!layout) return;
  const psHeight = ps.classList.contains('visible') ? ps.offsetHeight : 0;
  layout.style.height = 'calc(100vh - 163px - ' + psHeight + 'px)';
}}

function renderProjectSummary(filtered) {{
  const proj = document.getElementById('f-project').value.trim();
  const panel = document.getElementById('proj-summary');
  if (!proj || !PROJECT_SET.has(proj)) {{
    panel.classList.remove('visible');
    setLayoutHeight();
    return;
  }}
  const projRecords = filtered.filter(r => r.kb_associated_project === proj);
  if (projRecords.length === 0) {{
    panel.classList.remove('visible');
    setLayoutHeight();
    return;
  }}

  panel.classList.add('visible');

  // Title
  document.getElementById('ps-title').textContent = proj;

  // Meta tags
  const r0 = projRecords[0];
  const metaTags = [r0.project_type, r0.project_scale_band, r0.proponent_type,
                    r0.technology_domain, r0.location].filter(Boolean);
  document.getElementById('ps-meta').innerHTML =
    metaTags.map(t => `<span class="proj-meta-tag">${{t}}</span>`).join('');

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

  setLayoutHeight();
}}

function getFilters() {{
  return {{
    search:         document.getElementById('search').value.toLowerCase(),
    failure:        document.getElementById('f-failure').value,
    outcome:        document.getElementById('f-outcome').value,
    type:           document.getElementById('f-type').value,
    scale:          document.getElementById('f-scale').value,
    proponent:      document.getElementById('f-proponent').value,
    phase:          document.getElementById('f-phase').value,
    tech:           document.getElementById('f-tech').value,
    project:        document.getElementById('f-project').value,
    severity:       document.getElementById('f-severity').value,
    transferability:document.getElementById('f-transferability').value,
    qa:             document.getElementById('f-qa').value,
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
    if (f.project) {{
      const kap = r.kb_associated_project || '';
      if (PROJECT_SET.has(f.project)) {{
        if (kap !== f.project) return false;
      }} else {{
        if (!kap.toLowerCase().includes(f.project.toLowerCase())) return false;
      }}
    }}
    if (f.severity && r.issue_severity !== f.severity) return false;
    if (f.transferability && r.transferability !== f.transferability) return false;
    if (f.qa && r.qa_verdict !== f.qa) return false;
    if (f.search) {{
      const blob = [r.project_name, r.what_happened, r.lesson_learnt, r.evidence_excerpt,
                    r.source_title, r.kb_associated_project, r.intervention_note].join(' ').toLowerCase();
      if (!blob.includes(f.search)) return false;
    }}
    return true;
  }});
  renderCards(filtered);
  renderProjectSummary(filtered);
}}

function changePage(delta) {{
  _curPage += delta;
  renderPage();
  document.querySelector('main').scrollTop = 0;
}}

function clearFilters() {{
  ALL_FILTER_IDS.forEach(id => {{ document.getElementById(id).value = ''; }});
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
  const oc = r.outcome_class || '—';
  const isBadge = r.issue_severity
    ? ` <span class="badge" style="background:${{isColour(r.issue_severity)}}">${{r.issue_severity}}</span>`
    : '';
  document.getElementById('m-failure').innerHTML =
    `<span class="badge" style="background:${{fmColour(fm)}}">${{fm}}</span>${{isBadge}}`;
  document.getElementById('m-outcome').innerHTML =
    `<span class="badge" style="background:${{ocColour(oc)}}">${{oc}}</span>`;
  document.getElementById('m-phase').textContent = r.lifecycle_phase || '—';
  document.getElementById('m-delay').textContent = r.delay_category || '—';

  // intervention_note
  const iw = document.getElementById('m-intervention-wrap');
  const mi = document.getElementById('m-intervention');
  if (r.intervention_note) {{ mi.textContent = r.intervention_note; iw.classList.remove('hidden'); }}
  else iw.classList.add('hidden');

  // classification tags
  const tags = [];
  if (r.project_type) tags.push(['Project type', r.project_type, '#1e40af']);
  if (r.project_scale_band) tags.push(['Scale', r.project_scale_band, '#0891b2']);
  if (r.proponent_type) tags.push(['Proponent', r.proponent_type, '#7c3aed']);
  if (r.technology_domain) tags.push(['Technology', r.technology_domain, '#059669']);
  if (r.transferability) tags.push(['Transferability', r.transferability, '#0f766e']);
  if (r.kb_associated_project) tags.push(['ARENA project', r.kb_associated_project, '#0f766e']);
  if (r.kb_category) tags.push(['KB category', r.kb_category, '#64748b']);
  document.getElementById('m-tags').innerHTML = tags.map(([label, val, colour]) =>
    `<span class="tag" style="background:${{colour}}" title="${{label}}">${{val}}</span>`).join('');

  // QA verdict
  const qw = document.getElementById('m-qa-wrap');
  if (r.qa_verdict) {{
    document.getElementById('m-qa-verdict').innerHTML =
      `<span class="badge" style="background:${{qaColour(r.qa_verdict)}}">${{r.qa_verdict}}</span>`;
    document.getElementById('m-qa-text').textContent = r.qa_source_text || '';
    document.getElementById('m-qa-text').style.display = r.qa_source_text ? '' : 'none';
    document.getElementById('m-qa-note').textContent = r.qa_note || '';
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
    (linkBlocks + projLink) || '<span style="color:#94a3b8;font-size:13px">No source links available</span>';

  document.getElementById('overlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}}

function closeModal(e) {{ if (e.target === document.getElementById('overlay')) closeModalDirect(); }}
function closeModalDirect() {{ document.getElementById('overlay').classList.remove('active'); document.body.style.overflow = ''; }}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModalDirect(); }});

// ── Analysis tab ───────────────────────────────────────────────
let _analysisInit = false;

function initAnalysis() {{
  if (_analysisInit) return;
  _analysisInit = true;

  const total = RECORDS.length;
  const nProjects = PROJECT_SET.size;
  const withFailure = RECORDS.filter(r => r.failure_mode && r.failure_mode !== 'no major failure stated').length;
  const failPct = (withFailure / total * 100).toFixed(0);
  const avgPerProj = (total / nProjects).toFixed(1);
  document.getElementById('an-stats').innerHTML = `
    <div class="stat"><span class="stat-value">${{total.toLocaleString()}}</span><span class="stat-label">Total records</span></div>
    <div class="stat"><span class="stat-value">${{nProjects.toLocaleString()}}</span><span class="stat-label">Projects covered</span></div>
    <div class="stat"><span class="stat-value">${{withFailure.toLocaleString()}} <span style="font-size:14px;color:#64748b">(${{failPct}}%)</span></span><span class="stat-label">Records with any failure</span></div>
    <div class="stat"><span class="stat-value">${{avgPerProj}}</span><span class="stat-label">Avg insights per project</span></div>`;

  anPhaseFM();
  anFMFreq();
  anTypeFailRate();
  anTechFM();
  anOutcomes();
  anSeverity();
  anPhaseSev();
  anCooccurrence();
}}

const AN_PHASES = ['concept/feasibility','development/design','approvals/contracting','procurement',
  'construction/installation','commissioning/integration','operations','variation/re-scope','close-out/post-project review'];
const AN_PHASE_SHORT = ['Concept','Design','Approvals','Procurement','Construction','Commissioning','Operations','Variation','Close-out'];
const FM_LIST = Object.keys(FM_COLOURS);

function anPhaseFM() {{
  const matrix = {{}};
  AN_PHASES.forEach(p => {{ matrix[p] = {{}}; FM_LIST.forEach(fm => {{ matrix[p][fm] = 0; }}); }});
  RECORDS.forEach(r => {{
    if (r.lifecycle_phase && matrix[r.lifecycle_phase] && r.failure_mode && matrix[r.lifecycle_phase][r.failure_mode] !== undefined)
      matrix[r.lifecycle_phase][r.failure_mode]++;
  }});
  const datasets = FM_LIST.map(fm => ({{
    label: fm,
    data: AN_PHASES.map(p => matrix[p][fm] || 0),
    backgroundColor: FM_COLOURS[fm] + 'cc',
    borderColor: FM_COLOURS[fm],
    borderWidth: 1,
  }}));
  new Chart(document.getElementById('an-phase-fm'), {{
    type: 'bar',
    data: {{ labels: AN_PHASE_SHORT, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }} }},
      scales: {{
        x: {{ stacked: true, ticks: {{ font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, title: {{ display: true, text: 'Record count', font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }});
}}

function anFMFreq() {{
  const counts = {{}};
  RECORDS.forEach(r => {{ if (r.failure_mode) counts[r.failure_mode] = (counts[r.failure_mode] || 0) + 1; }});
  const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]);
  new Chart(document.getElementById('an-fm-freq'), {{
    type: 'bar',
    data: {{
      labels: sorted.map(([k]) => k),
      datasets: [{{ data: sorted.map(([,v]) => v),
        backgroundColor: sorted.map(([k]) => FM_COLOURS[k] || '#94a3b8'), borderWidth: 0, borderRadius: 3 }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
        label: ctx => `${{ctx.parsed.x.toLocaleString()}} records (${{(ctx.parsed.x/RECORDS.length*100).toFixed(1)}}%)`
      }} }} }},
      scales: {{
        x: {{ grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 10 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anTypeFailRate() {{
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const totals = {{}};
  const matrix = {{}};
  RECORDS.forEach(r => {{
    if (!r.project_type) return;
    totals[r.project_type] = (totals[r.project_type] || 0) + 1;
    if (!matrix[r.project_type]) matrix[r.project_type] = {{}};
    const sev = r.issue_severity || 'none';
    matrix[r.project_type][sev] = (matrix[r.project_type][sev] || 0) + 1;
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
    data: types.map(t => matrix[t]?.[sev] || 0),
    backgroundColor: IS_COLOURS[sev] + 'cc',
    borderColor: IS_COLOURS[sev],
    borderWidth: 1,
  }}));
  new Chart(document.getElementById('an-type-fail'), {{
    type: 'bar',
    data: {{ labels: types.map(t => `${{t}} (n=${{totals[t]}})`), datasets }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'top', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x}} records`
        }} }}
      }},
      scales: {{
        x: {{ stacked: true, title: {{ display: true, text: 'Record count by severity', font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, ticks: {{ font: {{ size: 10 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anTechFM() {{
  const techCounts = {{}};
  RECORDS.forEach(r => {{ if (r.technology_domain) techCounts[r.technology_domain] = (techCounts[r.technology_domain]||0)+1; }});
  const topTechs = Object.entries(techCounts).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([k])=>k);
  const matrix = {{}};
  topTechs.forEach(t => {{ matrix[t] = {{}}; FM_LIST.forEach(fm => {{ matrix[t][fm] = 0; }}); }});
  RECORDS.forEach(r => {{
    if (r.technology_domain && matrix[r.technology_domain] && r.failure_mode && matrix[r.technology_domain][r.failure_mode] !== undefined)
      matrix[r.technology_domain][r.failure_mode]++;
  }});
  const datasets = FM_LIST.map(fm => ({{
    label: fm,
    data: topTechs.map(t => matrix[t][fm]||0),
    backgroundColor: FM_COLOURS[fm]+'cc', borderColor: FM_COLOURS[fm], borderWidth: 1,
  }}));
  new Chart(document.getElementById('an-tech-fm'), {{
    type: 'bar',
    data: {{ labels: topTechs, datasets }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ stacked: true, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, ticks: {{ font: {{ size: 10 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});
}}

function anOutcomes() {{
  const counts = {{}};
  RECORDS.forEach(r => {{ if (r.outcome_class) counts[r.outcome_class] = (counts[r.outcome_class]||0)+1; }});
  const sorted = Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  new Chart(document.getElementById('an-outcomes'), {{
    type: 'doughnut',
    data: {{
      labels: sorted.map(([k])=>k),
      datasets: [{{ data: sorted.map(([,v])=>v),
        backgroundColor: sorted.map(([k])=>OC_COLOURS[k]||'#94a3b8'), borderWidth: 2 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.label}}: ${{ctx.parsed.toLocaleString()}} (${{(ctx.parsed/RECORDS.length*100).toFixed(1)}}%)` }} }} }}
    }}
  }});
}}

function anSeverity() {{
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const counts = {{}};
  RECORDS.forEach(r => {{ if (r.issue_severity) counts[r.issue_severity] = (counts[r.issue_severity]||0)+1; }});
  const labels = SEV_ORDER.filter(s => counts[s]);
  new Chart(document.getElementById('an-severity'), {{
    type: 'doughnut',
    data: {{
      labels,
      datasets: [{{ data: labels.map(s=>counts[s]),
        backgroundColor: labels.map(s=>IS_COLOURS[s]||'#94a3b8'), borderWidth: 2 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.label}}: ${{ctx.parsed.toLocaleString()}} (${{(ctx.parsed/RECORDS.length*100).toFixed(1)}}%)` }} }} }}
    }}
  }});
}}

function anPhaseSev() {{
  const SEV_ORDER = ['critical','major','moderate','minor','none'];
  const matrix = {{}};
  AN_PHASES.forEach(p => {{ matrix[p] = {{}}; SEV_ORDER.forEach(s => {{ matrix[p][s] = 0; }}); }});
  RECORDS.forEach(r => {{
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
  new Chart(document.getElementById('an-phase-sev'), {{
    type: 'bar',
    data: {{ labels: AN_PHASE_SHORT, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: true,
      plugins: {{
        legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y}} records`
        }} }}
      }},
      scales: {{
        x: {{ stacked: true, ticks: {{ font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ stacked: true, title: {{ display: true, text: 'Record count', font: {{ size: 10 }} }}, grid: {{ color: '#f1f5f9' }} }}
      }}
    }}
  }});
}}

function anCooccurrence() {{
  const FM_NO_FAILURE = 'no major failure stated';
  const FMS = FM_LIST.filter(fm => fm !== FM_NO_FAILURE);
  const SHORT = {{
    'design assumption failure':      'Design assumption',
    'regulatory misfit':              'Regulatory misfit',
    'integration failure':            'Integration',
    'technical underperformance':     'Tech underperf.',
    'schedule slippage':              'Schedule slippage',
    'cost overrun':                   'Cost overrun',
    'resource/capability shortfall':  'Resource shortfall',
    'commercial/demand failure':      'Commercial/demand',
    'governance/coordination failure':'Governance',
    'data quality/measurement failure':'Data quality',
  }};

  // matrix[primary][secondary] = count
  const matrix = {{}};
  FMS.forEach(p => {{ matrix[p] = {{}}; FMS.forEach(s => {{ matrix[p][s] = 0; }}); }});
  let maxVal = 0;
  RECORDS.forEach(r => {{
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

  const th = `style="padding:3px 5px;background:#f8fafc;border:1px solid #e2e8f0;font-size:9px;font-weight:700;color:#475569"`;
  const rotTh = `style="padding:3px;background:#f8fafc;border:1px solid #e2e8f0;font-size:9px;font-weight:600;color:#475569;writing-mode:vertical-lr;transform:rotate(180deg);height:90px;text-align:left;vertical-align:bottom"`;

  let html = `<table style="border-collapse:collapse;font-size:10px;width:100%">`;
  // Header: columns = secondary
  html += `<tr><td ${{th}} style="color:#94a3b8;font-size:8px">Primary ↓ / Secondary →</td>`;
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
    btn.innerHTML = `<span>${{ds.title}}</span><span style="font-size:10px;opacity:0.65">${{ds.rows.length}}</span>`;
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
        x: {{ title: {{ display: true, text: xLabel, font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 11 }} }}, grid: {{ display: false }} }}
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
      plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }} }},
      scales: {{
        x: {{ type: 'linear', title: {{ display: true, text: 'Scenario Year', font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ title: {{ display: true, text: 'AUD$/kW (midpoint)', font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }}
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
        legend: {{ display: true, labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x?.toFixed(0) ?? ctx.raw?.toFixed(0)}}` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'AUD$/tCO₂e (midpoint)', font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 10 }} }}, grid: {{ display: false }} }}
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
        legend: {{ position: 'right', labels: {{ font: {{ size: 10 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{
          label: ctx => ctx.dataset.type === 'line' ? ctx.dataset.label
            : `${{ctx.dataset.label}}: designed ${{ctx.parsed.x}}% → actual ${{ctx.parsed.y}}%`
        }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Designed CF (%)', font: {{ size: 11 }} }}, min: 0, grid: {{ color: '#f1f5f9' }} }},
        y: {{ title: {{ display: true, text: 'Actual CF (%)', font: {{ size: 11 }} }}, min: 0, grid: {{ color: '#f1f5f9' }} }}
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
        legend: {{ position: 'top', labels: {{ font: {{ size: 11 }}, boxWidth: 12 }} }},
        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.x?.toFixed(1)}}%` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Round-Trip Efficiency (%)', font: {{ size: 11 }} }}, min: 0, max: 100, grid: {{ color: '#f1f5f9' }} }},
        y: {{ ticks: {{ font: {{ size: 11 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }};
}}

// ── Synthesis ──────────────────────────────────────────────────
const SYNTH_MAX = 500;

function getActiveFilterDesc() {{
  const f = getFilters();
  const parts = [];
  if (f.project)  parts.push(`project: ${{f.project}}`);
  if (f.type)     parts.push(`project type: ${{f.type}}`);
  if (f.tech)     parts.push(`technology: ${{f.tech}}`);
  if (f.phase)    parts.push(`lifecycle phase: ${{f.phase}}`);
  if (f.failure)  parts.push(`failure mode: ${{f.failure}}`);
  if (f.outcome)  parts.push(`outcome: ${{f.outcome}}`);
  if (f.proponent)parts.push(`proponent: ${{f.proponent}}`);
  if (f.scale)    parts.push(`scale: ${{f.scale}}`);
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
    outcome: r.outcome_class,
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
      <div style="font-size:13px;color:#475569">Enter your Anthropic API key to enable synthesis. It will be saved locally and reused.</div>
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
        body.innerHTML = '<div style="color:#dc2626;font-size:13px;padding:8px 0">Invalid API key — removed. Click Synthesise again to re-enter.</div>';
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
    body.innerHTML += `<div style="color:#dc2626;font-size:13px;padding:8px 0">Error: ${{e.message}}</div>`;
  }} finally {{
    document.getElementById('synth-btn').disabled = false;
  }}
}}

// ── Init ───────────────────────────────────────────────────────
_lastFiltered = RECORDS;
renderPage();

// Update Reports tab count on load
(function() {{
  const list = loadReports();
  const tab = document.getElementById('tab-reports');
  if (tab && list.length) tab.textContent = `Reports (${{list.length}})`;
}})();

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
  // Extract cited record IDs from report text
  const cited = [];
  const idRe = /\\b(ARENA-DLV-\\d{{4,}})\\b/g;
  let m;
  while ((m = idRe.exec(rep.text)) !== null) {{
    const r = RECORD_MAP.get(m[1]);
    if (r && !cited.find(x => x.record_id === r.record_id)) cited.push(r);
  }}
  const modeLabel = rep.mode === 'brief' ? 'Brief Summary' : rep.mode === 'short' ? 'Short Report' : 'Detailed Report';
  const dateStr = new Date(rep.date).toLocaleDateString('en-AU', {{day:'numeric',month:'long',year:'numeric'}});
  const FM_COLOURS_JSON = JSON.stringify({fm_colours});
  const OC_COLOURS_JSON = JSON.stringify({oc_colours});
  const IS_COLOURS_JSON = JSON.stringify({is_colours});
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${{modeLabel}} — ${{rep.filterDesc}}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"><\/script>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;margin:0;padding:0}}
.rp-page{{max-width:820px;margin:0 auto;padding:40px 24px 80px}}
.rp-header{{margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid #e2e8f0}}
.rp-mode{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:8px}}
.rp-title{{font-size:22px;font-weight:800;color:#0f172a;margin-bottom:6px;line-height:1.3}}
.rp-meta{{font-size:12px;color:#94a3b8}}
.rp-context{{margin-top:10px;font-size:13px;color:#475569;background:#f1f5f9;padding:10px 14px;border-radius:8px;border-left:3px solid #6366f1}}
.rp-body{{font-size:14px;color:#1e293b;line-height:1.8}}
.rp-body h1{{font-size:20px;font-weight:800;margin:28px 0 10px;color:#0f172a}}
.rp-body h2{{font-size:17px;font-weight:700;margin:24px 0 8px;color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:4px}}
.rp-body h3{{font-size:15px;font-weight:700;margin:18px 0 6px;color:#1e293b}}
.rp-body p{{margin:8px 0}}
.rp-body ul,.rp-body ol{{margin:8px 0 8px 24px}}
.rp-body li{{margin:4px 0}}
.rp-body strong{{font-weight:700;color:#0f172a}}
.rp-body hr{{border:none;border-top:1px solid #e2e8f0;margin:20px 0}}
.rp-body code{{font-family:monospace;font-size:12px;background:#f1f5f9;padding:1px 5px;border-radius:3px}}
.record-link{{color:#6366f1!important;text-decoration:underline;text-decoration-style:dotted;cursor:pointer;font-weight:500}}
.record-link:hover{{color:#4f46e5!important}}
.badge{{font-size:10px;font-weight:700;padding:3px 9px;border-radius:20px;color:white;white-space:nowrap}}
.chip{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}}
.chip-scale{{background:#e0f2fe;color:#0369a1}}
.chip-tech{{background:#ede9fe;color:#6d28d9}}
#record-tooltip{{position:fixed;z-index:9999;width:380px;background:white;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.16);max-height:480px;overflow-y:auto;display:none}}
#record-tooltip .rt-header{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px 8px;border-bottom:1px solid #f1f5f9;position:sticky;top:0;background:white;z-index:1}}
#record-tooltip .rt-id{{font-size:10px;color:#6366f1;font-weight:700;letter-spacing:.5px}}
#record-tooltip .rt-close{{font-size:14px;color:#94a3b8;cursor:pointer;padding:2px 4px}}
#record-tooltip .rt-close:hover{{color:#475569}}
#record-tooltip .rt-body{{padding:10px 14px 14px;font-size:12px;line-height:1.6;display:flex;flex-direction:column;gap:6px}}
#record-tooltip .rt-project{{font-weight:700;color:#1e293b;font-size:13px}}
#record-tooltip .rt-chips{{display:flex;flex-wrap:wrap;gap:4px}}
#record-tooltip .rt-what{{color:#334155}}
#record-tooltip .rt-lesson{{color:#475569;font-style:italic}}
#record-tooltip .rt-excerpt{{font-size:11px;color:#64748b;background:#f8fafc;border-left:3px solid #e2e8f0;padding:6px 8px;border-radius:0 4px 4px 0}}
#record-tooltip .rt-footer{{display:flex;flex-wrap:wrap;gap:6px;padding-top:4px;border-top:1px solid #f1f5f9}}
#record-tooltip .rt-src{{font-size:11px;color:#6366f1;text-decoration:none}}
#record-tooltip .rt-src:hover{{text-decoration:underline}}
.rp-footer{{margin-top:48px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8}}
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
const OC_COLOURS = ${{OC_COLOURS_JSON}};
const IS_COLOURS = ${{IS_COLOURS_JSON}};

function buildSrcUrl(r) {{
  if (r.source_url) return r.source_url;
  if (r.pdf_url) return r.pdf_url;
  return null;
}}

// Linkify record IDs with sequential citation numbers
const body = document.getElementById('rp-body');
let rpHtml = body.innerHTML;
// Expand partial citations: "ARENA-DLV-N, -M" and ranges "ARENA-DLV-N through -M"
rpHtml = rpHtml.replace(
  /\\\\bARENA-DLV-(\\\\d+)((?:\\\\s+through\\\\s+-\\\\d+|(?:\\\\s*,\\\\s*-\\\\d+(?:\\\\s+through\\\\s+-\\\\d+)?))+)/g,
  function(match, firstNum, tail) {{
    var ids = ['ARENA-DLV-' + firstNum];
    var immRange = /^\\\\s+through\\\\s+-(\\\\d+)/.exec(tail);
    var rest = immRange ? tail.slice(immRange[0].length) : tail;
    if (immRange) {{
      var s = parseInt(firstNum), e = parseInt(immRange[1]);
      for (var i = s + 1; i <= Math.min(e, s + 50); i++) ids.push('ARENA-DLV-' + i);
    }}
    var itemRe = /,\\\\s*-(\\\\d+)(?:\\\\s+through\\\\s+-(\\\\d+))?/g;
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
    const oc = r.outcome_class || '—';
    let chips = '';
    if (r.project_scale_band) chips += \`<span class="chip chip-scale">\${{r.project_scale_band}}</span>\`;
    if (r.technology_domain)  chips += \`<span class="chip chip-tech">\${{r.technology_domain}}</span>\`;
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
          \${{oc !== '—' ? \`<span class="badge" style="background:\${{OC_COLOURS[oc]||'#64748b'}}">\${{oc}}</span>\` : ''}}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:4px">
          \${{year ? \`<span style="font-size:10px;color:#94a3b8">\${{year}}</span>\` : '<span></span>'}}
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
<\/script>
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
      body: JSON.stringify({{ id: rep.id, html }}),
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

    portfolio_size = load_portfolio_size()
    benchmarks = load_benchmarks()
    qa_results = load_qa_results()
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
