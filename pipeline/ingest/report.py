"""Post-scrape diagnostic report.

Produces a human-readable markdown report organised by decision type:
documents without PDFs, download failures, metadata gaps, format anomalies,
and overall coverage. Written to corpora/<domain>/scrape_report.md after
every scrape run.

Usage:
    from pipeline.ingest.report import generate_report
    generate_report("anao")

Or via CLI:
    python -m pipeline.ingest --domain anao --phase report
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = ROOT / "domains"
CORPORA_DIR = ROOT / "corpora"


def _load_domain_config(domain: str) -> dict:
    """Load domain.yaml as raw dict."""
    import yaml
    domain_yaml = DOMAINS_DIR / domain / "domain.yaml"
    if not domain_yaml.exists():
        return {}
    with open(domain_yaml) as f:
        return yaml.safe_load(f) or {}


def _load_metadata_csv(domain: str, config: dict) -> list[dict]:
    """Load the scraper's output metadata CSV.

    Checks, in order:
    1. The catalogue file specified in domain.yaml
    2. reports_metadata.csv (BaseScraper default)
    """
    catalogue_file = config.get("catalogue", {}).get("file", "")
    candidates = []
    if catalogue_file:
        candidates.append(CORPORA_DIR / domain / catalogue_file)
    candidates.append(CORPORA_DIR / domain / "reports_metadata.csv")

    for csv_path in candidates:
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                return list(csv.DictReader(f))
    return []


def _load_scrape_state(domain: str) -> dict:
    """Load .scrape_state.json if it exists."""
    state_path = CORPORA_DIR / domain / ".scrape_state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text())


def _check_pdf_exists(domain: str, row: dict) -> Path | None:
    """Check whether a PDF file exists on disk for a metadata row."""
    pdf_dir = CORPORA_DIR / domain / "pdfs"
    # Try doc_url-derived filename
    doc_url = row.get("doc_url", "")
    if doc_url:
        filename = doc_url.rstrip("/").split("/")[-1]
        path = pdf_dir / filename
        if path.exists() and path.stat().st_size > 0:
            return path
    # Try doc_urls (semicolon-separated)
    doc_urls = row.get("doc_urls", "")
    if doc_urls:
        for url in doc_urls.split("; "):
            url = url.strip()
            if url:
                filename = url.rstrip("/").split("/")[-1]
                path = pdf_dir / filename
                if path.exists() and path.stat().st_size > 0:
                    return path
    return None



def _find_url_column(rows: list[dict]) -> str | None:
    """Detect which column contains document/page URLs.

    Checks common names produced by BaseScraper and domain-specific scrapers.
    """
    candidates = ["doc_url", "doc_urls", "pdf_url", "page_url",
                   "Link to item", "source_url"]
    if not rows:
        return None
    sample = rows[0]
    for col in candidates:
        if col in sample:
            return col
    return None


def _find_title_column(rows: list[dict], config: dict) -> str:
    """Detect which column contains document titles."""
    # Prefer catalogue config
    title_field = config.get("catalogue", {}).get("title_field", "")
    if title_field and rows and title_field in rows[0]:
        return title_field
    # Fall back to common names
    for col in ["title", "Title"]:
        if rows and col in rows[0]:
            return col
    return "title"


def _row_has_doc_url(row: dict, url_col: str | None) -> bool:
    """Check whether a row has a non-empty document URL."""
    if url_col and row.get(url_col, "").strip():
        return True
    # Also check BaseScraper's standard columns
    if row.get("doc_url", "").strip() or row.get("doc_urls", "").strip():
        return True
    return False


def generate_report(domain: str) -> str:
    """Generate a diagnostic report and write it to corpora/<domain>/scrape_report.md.

    Returns the report text.
    """
    config = _load_domain_config(domain)
    rows = _load_metadata_csv(domain, config)
    state = _load_scrape_state(domain)
    expected_count = config.get("source", {}).get("estimated_count")
    domain_name = config.get("name", domain.upper())

    pdf_dir = CORPORA_DIR / domain / "pdfs"

    url_col = _find_url_column(rows)
    title_col = _find_title_column(rows, config)

    sections = []
    decisions_needed = []

    # --- Header ---
    sections.append(f"# Scrape Report: {domain_name}")
    sections.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    sections.append("")

    # --- Coverage summary ---
    sections.append("## Coverage Summary")
    sections.append("")
    discovered = len(rows)
    sections.append(f"- **Discovered:** {discovered} documents")
    if expected_count:
        pct = discovered / expected_count * 100
        sections.append(f"- **Expected:** ~{expected_count} ({pct:.1f}% coverage)")
        if pct < 95:
            gap = expected_count - discovered
            decisions_needed.append(
                f"Coverage gap: {gap} documents not discovered ({100-pct:.1f}% missing)"
            )

    # Count documents with/without document URLs
    has_doc_url = sum(1 for r in rows if _row_has_doc_url(r, url_col))
    no_doc_url = discovered - has_doc_url
    sections.append(f"- **Have document URL:** {has_doc_url}")
    sections.append(f"- **No document URL:** {no_doc_url}")

    # Count PDFs on disk
    pdfs_on_disk = 0
    zero_byte = []
    if pdf_dir.exists():
        for f in pdf_dir.iterdir():
            if f.suffix.lower() in (".pdf", ".docx"):
                if f.stat().st_size > 0:
                    pdfs_on_disk += 1
                else:
                    zero_byte.append(f.name)
    sections.append(f"- **PDFs on disk:** {pdfs_on_disk}")
    if zero_byte:
        sections.append(f"- **Zero-byte files:** {len(zero_byte)}")

    sections.append("")

    # Failed downloads from state
    failed = state.get("failed", [])
    if failed:
        sections.append(f"- **Failed downloads (from state):** {len(failed)}")
        sections.append("")

    # --- Documents without PDFs ---
    no_pdf_rows = [r for r in rows if not _row_has_doc_url(r, url_col)]
    if no_pdf_rows:
        sections.append("## Documents Without PDF URLs")
        sections.append("")
        sections.append("These documents were discovered but no downloadable PDF was found on their page.")
        sections.append("**Decision needed:** investigate individually, accept the gap, or try alternative download sources.")
        sections.append("")
        sections.append("| # | Title | Page URL | Metadata |")
        sections.append("|---|-------|----------|----------|")
        # Show at most 30 rows in the table, with a note about the rest
        display_rows = no_pdf_rows[:30]
        for i, r in enumerate(display_rows, 1):
            title = r.get(title_col, r.get("title", "—"))[:60]
            url = r.get("page_url", r.get("Link to item", "—"))
            # Collect non-empty metadata fields for context
            skip_keys = {"page_url", "title", "Title", "group", "doc_count",
                         "doc_url", "doc_urls", "Link to item",
                         title_col}
            meta_bits = []
            for k, v in r.items():
                if k not in skip_keys and v and str(v).strip():
                    meta_bits.append(f"{k}={v}")
            meta_str = "; ".join(meta_bits[:4]) if meta_bits else "—"
            sections.append(f"| {i} | {title} | {url} | {meta_str} |")
        if len(no_pdf_rows) > 30:
            sections.append(f"\n*... and {len(no_pdf_rows) - 30} more (see metadata CSV for full list)*")
        sections.append("")
        decisions_needed.append(
            f"{len(no_pdf_rows)} documents have no PDF URL — review table above"
        )

    # --- Failed downloads ---
    if failed:
        sections.append("## Failed Downloads")
        sections.append("")
        sections.append("These URLs were attempted but the download failed.")
        sections.append("**Decision needed:** retry, investigate, or accept the loss.")
        sections.append("")
        for url in failed:
            sections.append(f"- {url}")
        sections.append("")
        decisions_needed.append(
            f"{len(failed)} downloads failed — review URLs above"
        )

    # --- Zero-byte files ---
    if zero_byte:
        sections.append("## Zero-Byte Downloads")
        sections.append("")
        sections.append("These files were downloaded but are 0 bytes (corrupted or empty).")
        sections.append("**Decision needed:** re-download or remove.")
        sections.append("")
        for name in sorted(zero_byte):
            sections.append(f"- `{name}`")
        sections.append("")
        decisions_needed.append(
            f"{len(zero_byte)} zero-byte files on disk — likely corrupted downloads"
        )

    # --- Metadata completeness ---
    sections.append("## Metadata Completeness")
    sections.append("")

    if rows:
        # Collect all metadata keys
        skip_keys = {"page_url", "title", "group", "doc_count", "doc_url", "doc_urls"}
        all_keys = []
        seen = set()
        for r in rows:
            for k in r:
                if k not in skip_keys and k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        sections.append("| Field | Filled | Total | % | Gap pattern |")
        sections.append("|-------|--------|-------|---|-------------|")

        for key in all_keys:
            filled = sum(1 for r in rows if r.get(key, "").strip())
            pct = filled / len(rows) * 100 if rows else 0
            gap = len(rows) - filled

            # Analyse gap pattern: is it correlated with any other field?
            pattern = "—"
            if 0 < gap < len(rows):
                missing_rows = [r for r in rows if not r.get(key, "").strip()]
                # Check if missing rows cluster by date/year
                years = [r.get("year", r.get("year_tabled", r.get("date", "")))[:4]
                         for r in missing_rows
                         if r.get("year", r.get("year_tabled", r.get("date", "")))]
                if years:
                    year_counts = Counter(years)
                    top_years = year_counts.most_common(3)
                    if top_years and top_years[0][1] > gap * 0.3:
                        year_strs = [f"{y} ({c})" for y, c in top_years]
                        pattern = f"clusters in {', '.join(year_strs)}"

            sections.append(f"| {key} | {filled} | {len(rows)} | {pct:.0f}% | {pattern} |")

            if pct < 80:
                decisions_needed.append(
                    f"Field '{key}' is only {pct:.0f}% complete ({gap} missing)"
                )

        sections.append("")

    # --- Duplicate detection ---
    if rows:
        page_urls = [r.get("page_url", r.get("Link to item", "")) for r in rows]
        titles = [r.get(title_col, "") for r in rows]
        dup_urls = [url for url, count in Counter(page_urls).items() if count > 1 and url]
        dup_titles = [t for t, count in Counter(titles).items() if count > 1 and t]

        if dup_urls or dup_titles:
            sections.append("## Duplicates")
            sections.append("")
            if dup_urls:
                sections.append(f"**{len(dup_urls)} duplicate page URLs:**")
                for url in dup_urls[:20]:
                    sections.append(f"- {url}")
                sections.append("")
                decisions_needed.append(f"{len(dup_urls)} duplicate page URLs")
            if dup_titles:
                sections.append(f"**{len(dup_titles)} duplicate titles:**")
                for t in dup_titles[:20]:
                    sections.append(f"- {t}")
                sections.append("")

    # --- Decisions summary ---
    sections.append("## Decisions Needed")
    sections.append("")
    if decisions_needed:
        for i, d in enumerate(decisions_needed, 1):
            sections.append(f"{i}. {d}")
    else:
        sections.append("No decisions needed — scrape looks complete.")
    sections.append("")

    report_text = "\n".join(sections)

    # Write report
    out_path = CORPORA_DIR / domain / "scrape_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")
    print(f"Report written to {out_path}")

    return report_text
