#!/usr/bin/env python3
"""
Download and convert Word documents (.docx) from the ARENA Knowledge Bank.

Background
----------
The original PDF scraper only looked for .pdf links. Several KB entries —
particularly high-value Lessons Learnt documents — are published as .docx
files. This script finds and recovers them.

Scope (as of 2026-03-29 analysis):
  4 Lessons documents (all .docx) — high signal for delivery insights
  3 Tools (spreadsheets) — skipped, not extractable as delivery insights
  3 entries with no document link at all — genuinely unavailable

The 4 Lessons documents recovered:
  - PLUS ES South Australia Demand Flexibility Trial — Lessons Learnt 1
  - Future Fuels Lessons Learned — Perth (Chargefox)
  - Future Fuels Lessons Learned — Adelaide (Chargefox)
  - Evie Lessons Learnt Report May 2023 — Future Fuels (Evie Networks)

Process
-------
  1. Fetch each KB page to find the .docx asset URL
  2. Download the .docx to docx/
  3. Convert to plain text using python-docx (paragraphs + tables)
  4. Save as markdown in markdown/docx/
  5. Write docx_manifest.json in the same format as newsletter_manifest.json,
     ready for 03b_extract_registry_per_doc.py --source

Usage
-----
    python scripts/fetch_docx_documents.py
    python scripts/fetch_docx_documents.py --dry-run

Then extract:
    python scripts/03b_extract_registry_per_doc.py --source insights/docx_manifest.json

Requires
--------
    pip install python-docx
"""

import argparse
import csv
import html as html_module
import io
import json
import re
import time
import urllib.request
from pathlib import Path

try:
    import docx as python_docx
except ImportError:
    raise SystemExit("python-docx not installed. Run: pip install python-docx")

ROOT = Path(__file__).resolve().parents[1]
KB_EXPORT   = ROOT / "arena-kb-export_1772889492.csv"
MANIFEST_CSV = ROOT / "manifest.csv"
DOCX_DIR    = ROOT / "docx"
MD_DIR      = ROOT / "markdown" / "docx"
MANIFEST_OUT = ROOT / "insights" / "docx_manifest.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (research project)"}
FETCH_DELAY = 1.0

# Document types that are worth recovering (excludes tools, videos, etc.)
RECOVERABLE_TYPES = {"Lessons", "Reports", "Insights", "Reports, Lessons",
                     "Reports, Insights", "Insights, Presentation"}

# Known .docx URLs (pre-identified to avoid re-scraping; add new ones here)
KNOWN_DOCX = {
    "https://arena.gov.au/knowledge-bank/plus-es-south-australia-demand-flexibility-trial-lessons-learnt-1/":
        "https://arena.gov.au/assets/2024/07/PLUS-ES-SA-Demand-Flexibility-Trial-_Lessons-Learnt-Report-1.docx",
    "https://arena.gov.au/knowledge-bank/future-fuels-lessons-learned-perth/":
        "https://arena.gov.au/assets/2023/09/Chargefox-Future-Fuels-Lessons-Learned-Perth.docx",
    "https://arena.gov.au/knowledge-bank/future-fuels-lessons-learned-adelaide/":
        "https://arena.gov.au/assets/2023/09/Chargefox-Future-Fuels-Adelaide-v.2.docx",
    "https://arena.gov.au/knowledge-bank/evie-lessons-learnt-report-may-2023-future-fuels/":
        "https://arena.gov.au/assets/2023/08/Evie-Networks-ARENA-FFF-Lessons-Learnt-Report-May-2023-v0.1-2.docx",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_bytes(url: str) -> bytes | None:
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            print(f"    Attempt {attempt} failed: {e}")
            time.sleep(2)
    return None


def find_docx_url(kb_url: str) -> str | None:
    """Fetch a KB page and return the first .docx asset URL found."""
    if kb_url in KNOWN_DOCX:
        return KNOWN_DOCX[kb_url]
    data = fetch_bytes(kb_url)
    if not data:
        return None
    html = data.decode("utf-8", errors="replace")
    matches = re.findall(
        r'href=["\']([^"\']*arena\.gov\.au/assets/[^"\']*\.docx[^"\']*)["\']',
        html, re.I)
    return matches[0] if matches else None


def docx_to_text(docx_bytes: bytes) -> str:
    """Convert docx bytes to plain text, preserving paragraph and table structure."""
    doc = python_docx.Document(io.BytesIO(docx_bytes))
    lines = []

    for block in doc.element.body:
        tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

        if tag == "p":
            para = python_docx.text.paragraph.Paragraph(block, doc)
            text = para.text.strip()
            if text:
                lines.append(text)

        elif tag == "tbl":
            table = python_docx.table.Table(block, doc)
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    lines.append(" | ".join(cells))

    return "\n\n".join(lines)


def make_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')[:80]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch and convert ARENA .docx documents")
    parser.add_argument("--dry-run", action="store_true",
                        help="Find URLs and report, but do not download or write files")
    args = parser.parse_args()

    if not args.dry_run:
        DOCX_DIR.mkdir(parents=True, exist_ok=True)
        MD_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)

    # Load KB metadata for stamping
    with open(KB_EXPORT, encoding="utf-8") as f:
        kb_by_url = {r["Link to item"].strip(): r for r in csv.DictReader(f)}

    # Find no_pdf_found rows of recoverable types
    with open(MANIFEST_CSV, encoding="utf-8") as f:
        candidates = [r for r in csv.DictReader(f)
                      if r.get("status","") == "no_pdf_found"
                      and r.get("Type","") in RECOVERABLE_TYPES]

    print(f"Candidates to check: {len(candidates)}")
    if args.dry_run:
        print("(dry run — no files will be written)\n")

    manifest = []
    stats = {"found": 0, "no_docx": 0, "download_failed": 0, "saved": 0}

    for r in candidates:
        kb_url = r.get("Link to item","").strip()
        title  = r.get("Title","")
        doc_type = r.get("Type","")
        print(f"\n[{doc_type}] {title[:65]}")

        # Step 1: find docx URL
        docx_url = find_docx_url(kb_url)
        time.sleep(FETCH_DELAY)

        if not docx_url:
            print(f"  No .docx found — skipping")
            stats["no_docx"] += 1
            continue

        print(f"  Found: {docx_url[-60:]}")
        stats["found"] += 1

        if args.dry_run:
            continue

        # Step 2: download
        docx_bytes = fetch_bytes(docx_url)
        if not docx_bytes:
            print(f"  Download failed")
            stats["download_failed"] += 1
            continue

        slug = make_slug(title)
        docx_path = DOCX_DIR / f"{slug}.docx"
        docx_path.write_bytes(docx_bytes)

        # Step 3: convert to text
        try:
            text = docx_to_text(docx_bytes)
        except Exception as e:
            print(f"  Conversion error: {e}")
            stats["download_failed"] += 1
            continue

        if len(text) < 100:
            print(f"  Converted text too short ({len(text)} chars) — skipping")
            stats["no_docx"] += 1
            continue

        # Step 4: save markdown
        md_path = MD_DIR / f"{slug}.md"
        md_content = f"# {title}\n\nSource: {kb_url}\nDocument: {docx_url}\n\n---\n\n{text}"
        md_path.write_text(md_content, encoding="utf-8")

        # Step 5: build manifest entry (mirrors all_agent_groups_v2.json structure)
        kb_row = kb_by_url.get(kb_url, r)
        manifest.append({
            "Title": title,
            "Type": doc_type,
            "Category": kb_row.get("Category",""),
            "Publish date": kb_row.get("Publish date",""),
            "Year": kb_row.get("Year",""),
            "Link to item": kb_url,
            "Link to project page": kb_row.get("Link to project page",""),
            "Associated project name": kb_row.get("Associated project name",""),
            "Project Status": kb_row.get("Project Status",""),
            "md_path": str(md_path),
            "md_size": len(text),
            "docx_url": docx_url,
        })
        print(f"  Saved: {md_path.name} ({len(text):,} chars)")
        stats["saved"] += 1

    if not args.dry_run and manifest:
        MANIFEST_OUT.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nManifest written: {MANIFEST_OUT} ({len(manifest)} entries)")

    print(f"\nDone.")
    print(f"  .docx found:      {stats['found']}")
    print(f"  No docx:          {stats['no_docx']}")
    print(f"  Download failed:  {stats['download_failed']}")
    print(f"  Saved:            {stats['saved']}")


if __name__ == "__main__":
    main()
