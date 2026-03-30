#!/usr/bin/env python3
"""
Convert ARENA PDFs to structured markdown with section hierarchy and extracted tables.

Replaces 02_convert_to_markdown.py's flat text dump with a richer representation:

  - Section headings detected from font size/bold analysis (H1/H2/H3/H4)
  - Tables extracted to individual CSV files; cross-referenced in markdown
  - Page markers preserved (<!-- page N -->)
  - Output is intentionally minimal — body text retained as plain paragraphs
    so LLMs can decide which sections are worth deeper analysis

Output layout
-------------
  markdown/structured/{slug}.md          — structured markdown per document
  tables/{slug}_p{page:03d}_t{idx:02d}.csv  — one CSV per table found

Section heading detection
-------------------------
  1. Collect all font sizes across the document; compute modal (most common) size
     as the body baseline.
  2. Spans larger than baseline → candidate headings, bucketed into H1/H2/H3/H4
     by quantile of the size distribution above baseline.
  3. Bold body-size text is treated as H4 (bold paragraph header).
  4. Very short spans (< 3 chars) or all-whitespace are never headings.

Table extraction
----------------
  Uses PyMuPDF's page.find_tables() (available since PyMuPDF 1.23).
  Each table:
    - Saved as UTF-8 CSV to tables/ directory
    - Referenced in markdown as:
        [TABLE: tables/slug_p001_t00.csv | Caption: "..." | Rows: N | Cols: M]
      where Caption is the nearest preceding text line above the table bbox.
  <br> tags in cell content are replaced with spaces.

Resumable
---------
  Skips documents whose .md already exists in markdown/structured/ unless
  --force is passed.

Usage
-----
    python scripts/02b_convert_to_markdown_structured.py
    python scripts/02b_convert_to_markdown_structured.py --limit 50
    python scripts/02b_convert_to_markdown_structured.py --force
    python scripts/02b_convert_to_markdown_structured.py --dry-run

Requires
--------
    pip install pymupdf  (version >= 1.23 for find_tables)
"""

import argparse
import csv
import io
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("PyMuPDF not installed. Run: pip install pymupdf")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_CSV  = ROOT / "manifest.csv"
MD_OUT_DIR    = ROOT / "markdown" / "structured"
TABLE_OUT_DIR = ROOT / "tables"

# Only process successfully downloaded PDFs of document types worth extracting
SKIP_STATUSES = {"no_pdf_found", "skipped", "error"}

# ---------------------------------------------------------------------------
# Font-size heading detection parameters
# ---------------------------------------------------------------------------

# Minimum size ratio above body baseline to count as any heading
MIN_HEADING_RATIO = 1.05

# Size ratios (relative to body) that define heading levels.
# A span with size >= body * H1_RATIO → H1; >= H2_RATIO → H2; etc.
# These are tuned so typical ARENA report fonts (11-12pt body) map cleanly.
H1_RATIO = 1.45   # e.g. 18pt+ when body=12pt
H2_RATIO = 1.20   # e.g. 14-15pt when body=12pt
H3_RATIO = 1.05   # e.g. 12-13pt when body=12pt (if body=11pt)
# Bold body-size text → H4 (no separate ratio, detected via flags)

FLAG_BOLD = 2**4   # PyMuPDF font flag for bold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_slug(local_path: str) -> str:
    """Convert the manifest local_path to the same slug used for the markdown file."""
    # local_path looks like: pdfs/Reports/Some_Title_abc123.pdf
    stem = Path(local_path).stem   # Some_Title_abc123
    return stem


def compute_body_size(doc: fitz.Document) -> float:
    """Return the modal font size across the document (body text baseline)."""
    sizes = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if len(text) < 3:
                        continue
                    sizes.append(round(span["size"], 1))
    if not sizes:
        return 11.0
    counter = Counter(sizes)
    return counter.most_common(1)[0][0]


def classify_heading(size: float, flags: int, body_size: float) -> str | None:
    """Return heading level string ('# ', '## ', etc.) or None for body text."""
    ratio = size / body_size if body_size > 0 else 1.0
    if ratio >= H1_RATIO:
        return "# "
    if ratio >= H2_RATIO:
        return "## "
    if ratio >= H3_RATIO:
        return "### "
    # Bold at body size → H4
    if (flags & FLAG_BOLD) and ratio >= 0.95:
        return "#### "
    return None


def clean_cell(text: str) -> str:
    """Normalise a table cell: strip <br> artefacts, collapse whitespace."""
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def find_caption(page: fitz.Page, table_bbox: fitz.Rect, body_size: float) -> str:
    """
    Return the nearest text line directly above the table bbox, if any.
    Looks up to 40 points above the table top edge.
    """
    search_rect = fitz.Rect(
        table_bbox.x0,
        max(0, table_bbox.y0 - 40),
        table_bbox.x1,
        table_bbox.y0,
    )
    candidate_lines = []
    for block in page.get_text("dict", clip=search_rect)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_text = " ".join(s["text"] for s in line.get("spans", [])).strip()
            if len(line_text) > 3:
                candidate_lines.append(line_text)
    return candidate_lines[-1] if candidate_lines else ""


def extract_table_to_csv(table: fitz.table.Table, csv_path: Path) -> tuple[int, int]:
    """
    Write a fitz Table object to CSV. Returns (rows, cols).
    Cells are cleaned; blank rows are skipped.
    """
    rows_data = []
    for row in table.extract():
        cells = [clean_cell(str(c) if c is not None else "") for c in row]
        if any(cells):
            rows_data.append(cells)

    max_cols = max((len(r) for r in rows_data), default=0)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows_data:
            # Pad to consistent column count
            padded = row + [""] * (max_cols - len(row))
            writer.writerow(padded)

    return len(rows_data), max_cols


# ---------------------------------------------------------------------------
# Per-page conversion
# ---------------------------------------------------------------------------

def convert_page(
    page: fitz.Page,
    page_num: int,
    body_size: float,
    slug: str,
    table_counter: list,   # mutable list with one int — table index across doc
    dry_run: bool = False,
) -> str:
    """
    Convert one PDF page to structured markdown text.
    Returns the markdown string for this page (including <!-- page N --> marker).
    Writes CSV files for any tables found.
    """
    lines_out = [f"\n<!-- page {page_num} -->\n"]

    # Find tables first so we know which bboxes to skip in text extraction
    try:
        tables = page.find_tables()
        table_list = tables.tables if hasattr(tables, "tables") else list(tables)
    except Exception:
        table_list = []

    table_bboxes = [fitz.Rect(t.bbox) for t in table_list]

    # Build a set of (page-relative) y-ranges occupied by tables
    # We'll skip text blocks whose bbox overlaps significantly with a table
    def overlaps_table(block_rect: fitz.Rect) -> bool:
        for tb in table_bboxes:
            inter = block_rect & tb
            if inter.is_empty:
                continue
            # If >50% of the block is inside the table, skip it
            block_area = block_rect.width * block_rect.height
            inter_area = inter.width * inter.height
            if block_area > 0 and inter_area / block_area > 0.50:
                return True
        return False

    # Collect text blocks in reading order, inserting table markers at the right y
    # Build a merged list of events: (y_top, kind, data)
    events = []

    # Text blocks
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        block_rect = fitz.Rect(block["bbox"])
        if overlaps_table(block_rect):
            continue

        # Collect all spans in block
        block_texts = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"]
                if not text.strip():
                    continue
                size  = span["size"]
                flags = span["flags"]
                prefix = classify_heading(size, flags, body_size)
                block_texts.append((prefix, text.strip()))

        if block_texts:
            events.append((block["bbox"][1], "text", block_texts))

    # Table events
    for t_idx, table in enumerate(table_list):
        t_rect = fitz.Rect(table.bbox)
        events.append((t_rect.y0, "table", (t_idx, table, t_rect)))

    # Sort by y position (top of block)
    events.sort(key=lambda e: e[0])

    # Render
    prev_heading = None
    for _, kind, data in events:
        if kind == "text":
            # Merge spans into heading/paragraph chunks
            i = 0
            while i < len(data):
                prefix, text = data[i]
                # Merge consecutive spans with same heading level
                merged = text
                j = i + 1
                while j < len(data) and data[j][0] == prefix:
                    merged += " " + data[j][1]
                    j += 1
                i = j

                if prefix:
                    lines_out.append(f"\n{prefix}{merged}\n")
                    prev_heading = merged
                else:
                    lines_out.append(merged)

        elif kind == "table":
            t_local_idx, table, t_rect = data
            doc_table_idx = table_counter[0]
            table_counter[0] += 1

            csv_filename = f"{slug}_p{page_num:03d}_t{doc_table_idx:02d}.csv"
            csv_path = TABLE_OUT_DIR / csv_filename

            caption = find_caption(page, t_rect, body_size)
            if not caption and prev_heading:
                caption = prev_heading

            if not dry_run:
                try:
                    nrows, ncols = extract_table_to_csv(table, csv_path)
                except Exception as e:
                    lines_out.append(f"\n[TABLE EXTRACTION ERROR: {e}]\n")
                    continue
            else:
                # Count without writing
                try:
                    extracted = table.extract()
                    nrows = sum(1 for r in extracted if any(c for c in r if c))
                    ncols = max((len(r) for r in extracted), default=0)
                except Exception:
                    nrows, ncols = 0, 0

            cap_display = f' | Caption: "{caption}"' if caption else ""
            lines_out.append(
                f"\n[TABLE: tables/{csv_filename}{cap_display} | Rows: {nrows} | Cols: {ncols}]\n"
            )

    return "\n".join(lines_out)


# ---------------------------------------------------------------------------
# Per-document conversion
# ---------------------------------------------------------------------------

def convert_document(
    local_path: str,
    title: str,
    slug: str,
    dry_run: bool = False,
) -> dict:
    """
    Convert one PDF to structured markdown + table CSVs.
    Returns a stats dict.
    """
    pdf_path = ROOT / local_path
    md_path  = MD_OUT_DIR / f"{slug}.md"

    stats = {
        "slug": slug,
        "pages": 0,
        "tables": 0,
        "chars": 0,
        "error": None,
    }

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        stats["error"] = str(e)
        return stats

    stats["pages"] = len(doc)

    # Compute body font size across whole document
    body_size = compute_body_size(doc)

    table_counter = [0]   # mutable counter passed into convert_page
    page_chunks = []

    for page_num, page in enumerate(doc, start=1):
        chunk = convert_page(page, page_num, body_size, slug, table_counter, dry_run=dry_run)
        page_chunks.append(chunk)

    doc.close()

    stats["tables"] = table_counter[0]

    # Assemble full document
    header = f"# {title}\n\nSource PDF: {local_path}\n\n---\n"
    full_text = header + "\n".join(page_chunks)
    stats["chars"] = len(full_text)

    if not dry_run:
        MD_OUT_DIR.mkdir(parents=True, exist_ok=True)
        md_path.write_text(full_text, encoding="utf-8")

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    with open(MANIFEST_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(
        description="Convert ARENA PDFs to structured markdown with table extraction"
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N documents")
    parser.add_argument("--force", action="store_true",
                        help="Re-convert even if output .md already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse PDFs and report stats but write no files")
    parser.add_argument("--docs", default=None,
                        help="Specific doc range (e.g. 1-10) by manifest row number")
    args = parser.parse_args()

    rows = load_manifest()

    # Apply row range filter
    if args.docs:
        try:
            lo, hi = (int(x) for x in args.docs.split("-"))
            rows = rows[lo - 1: hi]
        except ValueError:
            raise SystemExit(f"Invalid --docs range: {args.docs!r}. Expected format: 1-10")

    # Filter to downloadable PDFs
    processable = [r for r in rows if r.get("status") not in SKIP_STATUSES
                   and r.get("local_path", "").endswith(".pdf")]

    if args.limit:
        processable = processable[:args.limit]

    if not args.dry_run:
        MD_OUT_DIR.mkdir(parents=True, exist_ok=True)
        TABLE_OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Documents to convert: {len(processable)}")
    if args.dry_run:
        print("(dry run — no files will be written)\n")

    total_tables = 0
    total_chars  = 0
    skipped      = 0
    errors       = 0

    for i, row in enumerate(processable, 1):
        title      = row.get("Title", "")
        local_path = row.get("local_path", "")
        slug       = make_slug(local_path)
        md_path    = MD_OUT_DIR / f"{slug}.md"

        if not args.force and not args.dry_run and md_path.exists():
            skipped += 1
            continue

        print(f"[{i:4d}/{len(processable)}] {title[:60]}")

        stats = convert_document(local_path, title, slug, dry_run=args.dry_run)

        if stats["error"]:
            print(f"  ERROR: {stats['error']}")
            errors += 1
            continue

        total_tables += stats["tables"]
        total_chars  += stats["chars"]
        print(f"  {stats['pages']} pages | {stats['tables']} tables | {stats['chars']:,} chars")

    print(f"\nDone.")
    print(f"  Converted:    {len(processable) - skipped - errors}")
    print(f"  Skipped:      {skipped} (already exist — use --force to redo)")
    print(f"  Errors:       {errors}")
    print(f"  Tables total: {total_tables:,}")
    print(f"  Chars total:  {total_chars:,}")
    print(f"\nOutputs:")
    if not args.dry_run:
        print(f"  markdown/structured/  — {len(processable) - skipped - errors} .md files")
        print(f"  tables/               — {total_tables} .csv files")
    print(f"  Body font size detection: modal size per document")
    print(f"  Heading ratios: H1>={H1_RATIO}x, H2>={H2_RATIO}x, H3>={H3_RATIO}x body; H4=bold body")


if __name__ == "__main__":
    main()
