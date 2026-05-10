"""PDF/DOCX → structured markdown conversion.

Domain-agnostic. Converts PDFs using PyMuPDF with:
- Font-size heading detection (H1-H4)
- Table extraction to CSV files
- Page markers preserved

Usage:
    from pipeline.ingest.convert import run_convert
    run_convert("anao", workers=8, force=False, limit=None)
"""

import argparse
import csv
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
CORPORA_DIR = ROOT / "corpora"


def _corpus_paths(domain: str) -> tuple[Path, Path, Path, Path]:
    """Return (pdf_dir, md_dir, table_dir, metadata_csv) for a domain."""
    base = CORPORA_DIR / domain
    return (
        base / "pdfs",
        base / "markdown",
        base / "tables",
        base / "reports_metadata.csv",
    )


# ---------------------------------------------------------------------------
# Font-size heading detection
# ---------------------------------------------------------------------------

H1_RATIO = 1.45
H2_RATIO = 1.20
H3_RATIO = 1.05
FLAG_BOLD = 2 ** 4


def _compute_body_size(doc) -> float:
    """Return the modal font size across the document."""
    sizes = []
    for page in list(doc)[:30]:
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
    return Counter(sizes).most_common(1)[0][0]


def _classify_heading(size: float, flags: int, body_size: float) -> str | None:
    ratio = size / body_size if body_size > 0 else 1.0
    if ratio >= H1_RATIO:
        return "# "
    if ratio >= H2_RATIO:
        return "## "
    if ratio >= H3_RATIO:
        return "### "
    if (flags & FLAG_BOLD) and ratio >= 0.95:
        return "#### "
    return None


def _clean_cell(text: str) -> str:
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.I)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_table_to_csv(table, csv_path: Path) -> tuple[int, int]:
    rows_data = []
    for row in table.extract():
        cells = [_clean_cell(str(c) if c is not None else "") for c in row]
        if any(cells):
            rows_data.append(cells)
    max_cols = max((len(r) for r in rows_data), default=0)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows_data:
            writer.writerow(row + [""] * (max_cols - len(row)))
    return len(rows_data), max_cols


# ---------------------------------------------------------------------------
# Per-page conversion
# ---------------------------------------------------------------------------

def _convert_page(page, page_num: int, body_size: float, slug: str,
                  table_counter: list, tables_dir: Path) -> str:
    """Convert one PDF page to structured markdown."""
    lines_out = [f"\n<!-- page {page_num} -->\n"]

    try:
        tables = page.find_tables()
        table_list = tables.tables if hasattr(tables, "tables") else list(tables)
    except Exception:
        table_list = []

    table_bboxes = [fitz.Rect(t.bbox) for t in table_list]

    def overlaps_table(block_rect) -> bool:
        for tb in table_bboxes:
            inter = block_rect & tb
            if inter.is_empty:
                continue
            block_area = block_rect.width * block_rect.height
            inter_area = inter.width * inter.height
            if block_area > 0 and inter_area / block_area > 0.50:
                return True
        return False

    events = []

    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        block_rect = fitz.Rect(block["bbox"])
        if overlaps_table(block_rect):
            continue
        block_texts = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"]
                if not text.strip():
                    continue
                prefix = _classify_heading(span["size"], span["flags"], body_size)
                block_texts.append((prefix, text.strip()))
        if block_texts:
            events.append((block["bbox"][1], "text", block_texts))

    for t_idx, table in enumerate(table_list):
        t_rect = fitz.Rect(table.bbox)
        events.append((t_rect.y0, "table", (t_idx, table, t_rect)))

    events.sort(key=lambda e: e[0])

    prev_heading = None
    for _, kind, data in events:
        if kind == "text":
            i = 0
            while i < len(data):
                prefix, text = data[i]
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
            csv_path = tables_dir / csv_filename
            caption = prev_heading or ""

            try:
                nrows, ncols = _extract_table_to_csv(table, csv_path)
            except Exception as e:
                lines_out.append(f"\n[TABLE EXTRACTION ERROR: {e}]\n")
                continue

            cap_display = f' | Caption: "{caption}"' if caption else ""
            lines_out.append(
                f"\n[TABLE: tables/{csv_filename}{cap_display} | Rows: {nrows} | Cols: {ncols}]\n"
            )

    return "\n".join(lines_out)


# ---------------------------------------------------------------------------
# Per-document conversion (designed for ProcessPoolExecutor)
# ---------------------------------------------------------------------------

def _convert_document(entry: dict) -> dict:
    """Convert one PDF to structured markdown."""
    pdf_path = Path(entry["pdf_path"])
    title = entry["title"]
    slug = entry["slug"]
    out_dir = Path(entry["md_dir"])
    tables = Path(entry["table_dir"])
    md_path = out_dir / f"{slug}.md"

    stats = {"slug": slug, "pages": 0, "tables": 0, "chars": 0, "error": None}

    try:
        import fitz as _fitz
        doc = _fitz.open(str(pdf_path))
    except Exception as e:
        stats["error"] = str(e)
        return stats

    stats["pages"] = len(doc)
    body_size = _compute_body_size(doc)
    table_counter = [0]
    page_chunks = []

    for page_num, page in enumerate(doc, start=1):
        chunk = _convert_page(page, page_num, body_size, slug, table_counter, tables)
        page_chunks.append(chunk)

    doc.close()
    stats["tables"] = table_counter[0]

    header = f"# {title}\n\nSource PDF: pdfs/{slug}.pdf\n\n---\n"
    full_text = header + "\n".join(page_chunks)
    stats["chars"] = len(full_text)

    out_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(full_text, encoding="utf-8")

    return stats


# ---------------------------------------------------------------------------
# Main convert runner
# ---------------------------------------------------------------------------

def run_convert(domain: str, workers: int | None = None, force: bool = False,
                limit: int | None = None):
    """Convert downloaded PDFs to structured markdown."""
    if fitz is None:
        raise ImportError("pymupdf not installed. Run: pip install pymupdf")

    pdfs_path, md_out, tables_out, meta_csv = _corpus_paths(domain)

    if not pdfs_path.exists():
        raise FileNotFoundError(f"No PDF directory at {pdfs_path}. Run --phase scrape first.")

    # Build file list from metadata CSV if available, else scan directory
    pdfs = []
    seen_paths = set()
    if meta_csv.exists():
        with open(meta_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                # Collect all doc URLs: doc_url (single) + doc_urls (comma-separated)
                urls = []
                doc_url = row.get("doc_url", "")
                if doc_url:
                    urls.append(doc_url)
                doc_urls_raw = row.get("doc_urls", "")
                if doc_urls_raw:
                    # doc_urls is semicolon-separated (from BaseScraper.to_dict)
                    urls.extend(u.strip() for u in doc_urls_raw.split(";") if u.strip())

                for url in urls:
                    # Strip query params for filename matching
                    filename = url.rstrip("/").split("/")[-1].split("?")[0]
                    if not filename:
                        continue
                    fp = pdfs_path / filename
                    if fp.exists() and str(fp) not in seen_paths:
                        seen_paths.add(str(fp))
                        slug = filename.rsplit(".", 1)[0]
                        pdfs.append({
                            "pdf_path": str(fp),
                            "title": row.get("title", slug),
                            "slug": slug,
                            "md_dir": str(md_out),
                            "table_dir": str(tables_out),
                        })
    # Also scan for any PDFs not found via metadata (including subdirectories)
    for fp in sorted(pdfs_path.rglob("*.pdf")):
        if str(fp) not in seen_paths:
            seen_paths.add(str(fp))
            slug = fp.stem
            pdfs.append({
                "pdf_path": str(fp),
                "title": slug.replace("-", " ").replace("_", " ").title(),
                "slug": slug,
                "md_dir": str(md_out),
                "table_dir": str(tables_out),
            })

    # Filter already converted
    if not force:
        before = len(pdfs)
        pdfs = [p for p in pdfs if not (md_out / f"{p['slug']}.md").exists()]
        skipped = before - len(pdfs)
    else:
        skipped = 0

    if limit:
        pdfs = pdfs[:limit]

    md_out.mkdir(parents=True, exist_ok=True)
    tables_out.mkdir(parents=True, exist_ok=True)

    n_workers = workers or (cpu_count() or 4)
    print(f"Documents to convert: {len(pdfs)}  (skipped {skipped} already done)")
    print(f"Workers: {n_workers}")

    # Parallel conversion using pool.map for ordered results
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        iterator = pool.map(_convert_document, pdfs)
        if tqdm is not None:
            iterator = tqdm(iterator, total=len(pdfs), desc="Converting",
                            unit="doc")
        results = list(iterator)

    # Tally stats
    total_tables = total_chars = total_pages = errors = 0
    for stats in results:
        if stats["error"]:
            print(f"  ERROR: {stats['slug']} — {stats['error']}")
            errors += 1
        else:
            total_tables += stats["tables"]
            total_chars += stats["chars"]
            total_pages += stats["pages"]

    print(f"\nDone.")
    print(f"  Converted:    {len(results) - errors}")
    print(f"  Skipped:      {skipped}")
    print(f"  Errors:       {errors}")
    print(f"  Total pages:  {total_pages:,}")
    print(f"  Total tables: {total_tables:,}")
    print(f"  Total chars:  {total_chars:,}")
