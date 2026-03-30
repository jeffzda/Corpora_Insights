#!/usr/bin/env python3
"""
Step 2: Convert selected report PDFs to markdown text files.

Reads data/reports_sample_100.json (output of step 1).
Converts each PDF to text using pymupdf (fitz).
Output: ../../markdown/reports/<slug>.md

Requires: pip install pymupdf
"""

import json
import re
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    raise SystemExit("pymupdf not installed. Run: pip install pymupdf")

# --- Config ---
PILOT_ROOT = Path(__file__).resolve().parents[1]
ARENA_ROOT = PILOT_ROOT.parent
INPUT_FILE = PILOT_ROOT / "data" / "reports_sample_100.json"
OUTPUT_DIR = ARENA_ROOT / "markdown" / "reports"


def slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len]


def pdf_to_markdown(pdf_path: Path) -> str:
    """Extract text from PDF, one page at a time, with page markers."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"<!-- page {i} -->\n{text}")
    return "\n\n".join(pages)


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    for r in records:
        pdf_path = Path(r["local_path"])
        if not pdf_path.exists():
            print(f"MISSING: {pdf_path}")
            skipped += 1
            continue

        slug = slugify(r.get("Title", pdf_path.stem))
        out_path = OUTPUT_DIR / f"{slug}.md"

        if out_path.exists():
            r["md_path"] = str(out_path)
            skipped += 1
            continue

        try:
            md = pdf_to_markdown(pdf_path)
            out_path.write_text(md, encoding="utf-8")
            r["md_path"] = str(out_path)
            converted += 1
            size_kb = len(md.encode()) // 1024
            print(f"[{converted:3d}] {slug[:60]} ({size_kb} KB)")
        except Exception as e:
            print(f"ERROR converting {pdf_path}: {e}")
            skipped += 1

    # Save updated records with md_path
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"\nConverted: {converted} | Skipped/cached: {skipped}")
    print(f"Markdown files in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
