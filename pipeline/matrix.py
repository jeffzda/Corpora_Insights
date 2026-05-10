#!/usr/bin/env python3
"""Generate archetype × category cross-reference matrix PDF.

Config-driven version of scripts/generate_archetype_cross_matrix_pdf.py.
Uses domain config for independence thresholds and category labels.

Usage:
    python -m pipeline.matrix --domain arena
    python -m pipeline.matrix --domain arena --output dashboard/cross_matrix.pdf
"""

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]


def get_dirs(cfg):
    """Get input directories for this domain."""
    domain_lower = cfg.domain.name.lower()
    taxonomy_dir = ROOT / "runs" / domain_lower / "failure_archetypes"
    if not taxonomy_dir.exists() and (ROOT / "insights" / "failure_archetypes" / "v2").exists():
        taxonomy_dir = ROOT / "insights" / "failure_archetypes" / "v2"
    events_dir = ROOT / "runs" / domain_lower / "per_project_events"
    if not events_dir.exists() and (ROOT / "insights" / "per_project_events_v2").exists():
        events_dir = ROOT / "insights" / "per_project_events_v2"
    return taxonomy_dir, events_dir


def load_event_project_map(events_dir):
    """Build event_title → project_name from events."""
    event_project = {}
    for fp in sorted(glob.glob(str(events_dir / "*.json"))):
        fname = Path(fp).name
        if fname in ("batch_state.json", "event_index.json", "project_index.json",
                      "discovery_summary.json", "canonical_taxonomy.json",
                      "reconciled_classifications.json"):
            continue
        with open(fp) as f:
            data = json.load(f)
        evts = data if isinstance(data, list) else data.get("events", [])
        proj_name = None
        for e in evts:
            if not proj_name:
                proj_name = e.get("project_name", Path(fp).stem.replace("_", " "))
            et = e.get("event_title", "")
            if et:
                event_project[et] = proj_name
    return event_project


def load_data(taxonomy_dir):
    """Load canonical taxonomy and reconciled classifications."""
    canon_path = taxonomy_dir / "canonical_taxonomy.json"
    recon_path = taxonomy_dir / "reconciled_classifications.json"
    with open(canon_path) as f:
        canon = json.load(f)
    with open(recon_path) as f:
        recon = json.load(f)
    return canon, recon


def build_cross_matrix(canon, recon, events_dir):
    """Build archetype → set of categories, plus event counts."""
    event_project = load_event_project_map(events_dir)

    arch_cats = defaultdict(lambda: defaultdict(int))
    arch_total = defaultdict(int)
    arch_projects = defaultdict(set)

    for event_title, r in recon.items():
        pri = r.get("primary") or ""
        if not pri or pri.startswith("Other "):
            continue
        src = r.get("source_category", "")
        if src:
            arch_cats[pri][src] += 1
            arch_total[pri] += 1
            if event_title in event_project:
                arch_projects[pri].add(event_project[event_title])

    arch_parent = {}
    for c in canon.get("canonical_archetypes", []):
        arch_parent[c["name"]] = c["parent_category"]
    for event_title, r in recon.items():
        pri = r.get("primary") or ""
        pcat = r.get("primary_category") or ""
        if pri and pcat and pri not in arch_parent:
            arch_parent[pri] = pcat

    return arch_cats, arch_total, arch_projects, arch_parent


# Default parent category colours (can be overridden by domain config)
DEFAULT_PARENT_COLOURS = {
    "Technology Performance": "#ef4444",
    "Data, Platforms, and Monitoring": "#06b6d4",
    "Grid Connection, Approvals, and Land": "#f97316",
    "Commercial and Contractual Structure": "#14b8a6",
    "Market Design and DER Integration": "#a855f7",
    "Control Systems and Commissioning": "#3b82f6",
    "Program and Project Delivery": "#ec4899",
    "Construction and Procurement": "#8b5cf6",
    "Customer and Stakeholder Engagement": "#eab308",
    "Operations and Maintenance": "#64748b",
    "Electric Vehicle Infrastructure": "#10b981",
    "Standards, Safety, and Certification": "#f43f5e",
}


def generate_pdf(arch_cats, arch_total, arch_projects, arch_parent, cfg, output_path,
                 cat_short_labels=None, parent_colours=None):
    """Generate the cross-reference matrix PDF."""
    min_events = cfg.domain.archetype_independence_threshold.get("min_events", 3)
    min_projects = cfg.domain.archetype_independence_threshold.get("min_projects", 3)

    if parent_colours is None:
        parent_colours = DEFAULT_PARENT_COLOURS

    page_w, page_h = landscape(A3)
    margin = 10 * mm

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A3),
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"],
        fontSize=14, leading=17, textColor=HexColor("#1e293b"), spaceAfter=2)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=HexColor("#64748b"), spaceAfter=6)
    group_style = ParagraphStyle("Group", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=white, fontName="Helvetica-Bold", alignment=TA_LEFT)
    header_style = ParagraphStyle("ColHeader", parent=styles["Normal"],
        fontSize=6, leading=7.5, textColor=HexColor("#1e293b"),
        alignment=TA_CENTER, fontName="Helvetica-Bold")
    arch_style = ParagraphStyle("Arch", parent=styles["Normal"],
        fontSize=5.5, leading=7, textColor=HexColor("#1e293b"), alignment=TA_LEFT)
    count_style = ParagraphStyle("Count", parent=styles["Normal"],
        fontSize=5.5, leading=7, textColor=HexColor("#64748b"), alignment=TA_RIGHT)
    x_style = ParagraphStyle("XMark", parent=styles["Normal"],
        fontSize=7, leading=8, textColor=HexColor("#1e293b"),
        alignment=TA_CENTER, fontName="Helvetica-Bold")
    x_strong_style = ParagraphStyle("XStrong", parent=styles["Normal"],
        fontSize=7, leading=8, textColor=HexColor("#dc2626"),
        alignment=TA_CENTER, fontName="Helvetica-Bold")

    # Determine categories present
    all_arena = set()
    for cats in arch_cats.values():
        all_arena.update(cats.keys())
    arena_totals = defaultdict(int)
    for cats in arch_cats.values():
        for ac, cnt in cats.items():
            arena_totals[ac] += cnt
    arena_order = sorted(all_arena, key=lambda c: -arena_totals[c])

    # Apply independence filter
    qualifying = {a for a, total in arch_total.items()
                  if total >= min_events and len(arch_projects.get(a, set())) >= min_projects}

    # Group by parent category
    by_parent = defaultdict(list)
    for arch in qualifying:
        parent = arch_parent.get(arch, "Unknown")
        by_parent[parent].append(arch)

    parent_order = sorted(by_parent.keys(),
                          key=lambda p: -sum(arch_total[a] for a in by_parent[p]))
    for p in parent_order:
        by_parent[p].sort(key=lambda a: -arch_total[a])

    # Column widths
    avail_w = page_w - 2 * margin
    name_col = 90 * mm
    count_col = 11 * mm
    proj_col = 11 * mm
    n_cats_col = 8 * mm
    remaining = avail_w - name_col - count_col - proj_col - n_cats_col
    cat_col = remaining / max(len(arena_order), 1)

    col_widths = [name_col, count_col, proj_col, n_cats_col] + [cat_col] * len(arena_order)
    n_cols = len(col_widths)

    # Header row
    header_row = [
        Paragraph("Archetype", header_style),
        Paragraph("Events", header_style),
        Paragraph("Proj", header_style),
        Paragraph("#", header_style),
    ]
    for ac in arena_order:
        short = (cat_short_labels or {}).get(ac, ac[:8])
        header_row.append(Paragraph(short, header_style))

    table_data = [header_row]
    row_colours = []
    total_archetypes = 0

    for parent in parent_order:
        archetypes = by_parent[parent]
        total_archetypes += len(archetypes)

        parent_hex = parent_colours.get(parent, "#475569")
        group_row = [Paragraph(f"{parent} ({len(archetypes)})", group_style)] + \
                    [Paragraph("", group_style)] * (n_cols - 1)
        table_data.append(group_row)
        row_colours.append((len(table_data) - 1, parent_hex))

        for arch in archetypes:
            n_arena = len(arch_cats[arch])
            n_proj = len(arch_projects.get(arch, set()))
            row = [
                Paragraph(arch, arch_style),
                Paragraph(str(arch_total[arch]), count_style),
                Paragraph(str(n_proj), count_style),
                Paragraph(str(n_arena), count_style),
            ]
            for ac in arena_order:
                cnt = arch_cats[arch].get(ac, 0)
                if cnt == 0:
                    row.append(Paragraph("", x_style))
                elif cnt >= 5:
                    row.append(Paragraph(f"<b>{cnt}</b>", x_strong_style))
                else:
                    row.append(Paragraph(str(cnt), x_style))
            table_data.append(row)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
        ("LINEBELOW", (0, 0), (-1, 0), 1, HexColor("#475569")),
    ]

    for row_idx, hex_col in row_colours:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), HexColor(hex_col)))
        style_cmds.append(("SPAN", (0, row_idx), (-1, row_idx)))

    group_rows = {r for r, _ in row_colours}
    data_row_idx = 0
    for i in range(1, len(table_data)):
        if i in group_rows:
            data_row_idx = 0
            continue
        data_row_idx += 1
        if data_row_idx % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor("#f8fafc")))

    table.setStyle(TableStyle(style_cmds))

    domain_name = cfg.domain.name
    elements = [
        Paragraph(f"{domain_name} Failure Archetype Cross-Reference Matrix", title_style),
        Paragraph(
            f"{total_archetypes} archetypes ({min_events}+ events, {min_projects}+ independent projects) "
            f"× {len(arena_order)} categories · "
            f"Grouped by parent failure category · "
            f"Numbers show event count per category · "
            f"<font color='#dc2626'><b>Red bold</b></font> = 5+ events",
            subtitle_style,
        ),
        table,
    ]

    doc.build(elements)
    print(f"PDF written to {output_path}")
    print(f"  {total_archetypes} archetypes × {len(arena_order)} categories")
    print(f"  {len(parent_order)} parent category groups")


def main():
    parser = argparse.ArgumentParser(description="Generate archetype cross-reference matrix PDF")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--output", default=None, help="Output PDF path")
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    taxonomy_dir, events_dir = get_dirs(cfg)

    output_path = Path(args.output) if args.output else ROOT / "dashboard" / "archetype_cross_matrix.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load category short labels from parent_categories config if available
    cat_short_labels = None
    if cfg.parent_categories and "short_labels" in cfg.parent_categories:
        cat_short_labels = cfg.parent_categories["short_labels"]

    canon, recon = load_data(taxonomy_dir)
    arch_cats, arch_total, arch_projects, arch_parent = build_cross_matrix(canon, recon, events_dir)
    print(f"Loaded {len(arch_cats)} archetypes with category data")

    # Load parent colours from config if available
    parent_colours = None
    if cfg.parent_categories and "colours" in cfg.parent_categories:
        parent_colours = cfg.parent_categories["colours"]

    generate_pdf(arch_cats, arch_total, arch_projects, arch_parent, cfg, output_path,
                 cat_short_labels, parent_colours)


if __name__ == "__main__":
    main()
