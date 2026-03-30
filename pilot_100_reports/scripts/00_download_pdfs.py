#!/usr/bin/env python3
"""
Download ARENA knowledge bank PDFs and associate them with CSV metadata.

For each record in the CSV:
1. Fetch the knowledge bank page from "Link to item"
2. Find the PDF download link on the page
3. Download the PDF into pdfs/<Type>/ directory
4. Write a manifest CSV mapping each PDF filename back to all original metadata
"""

import csv
import os
import re
import time
import hashlib
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# --- Config ---
CSV_FILE = "arena-kb-export_1772889492.csv"
OUTPUT_DIR = Path("pdfs")
MANIFEST_FILE = "manifest.csv"
LOG_FILE = "download.log"

REQUEST_DELAY = 1.0      # seconds between requests (be polite)
REQUEST_TIMEOUT = 30     # seconds
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ARENA-KB-Downloader/1.0; "
        "+https://github.com/user/arena-kb)"
    )
}

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Turn an arbitrary string into a safe filename component."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = name[:max_len]
    return name or "unnamed"


def sanitize_dirname(name: str) -> str:
    """Turn a Type/Category value into a safe directory name."""
    # strip any HTML entities and illegal chars
    name = re.sub(r"&[a-z]+;", "", name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f,]', "_", name.strip())
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Other"


def get_with_retry(session: requests.Session, url: str) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * attempt * 2)
    return None


def find_pdf_url(page_url: str, html: str) -> str | None:
    """
    Parse the knowledge-bank page HTML and return the first PDF href found.
    Tries several heuristics in order of specificity.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Any <a> whose href ends with .pdf (absolute or relative)
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.lower().endswith(".pdf"):
            return urljoin(page_url, href)

    # 2. Any <a> whose href contains '.pdf?' (query-string style)
    for tag in soup.find_all("a", href=True):
        if ".pdf" in tag["href"].lower():
            return urljoin(page_url, tag["href"])

    return None


def derive_local_path(record: dict, pdf_url: str) -> Path:
    """
    Build  pdfs/<RecordType>/<sanitized_title>_<hash6>.pdf
    Using the record Type field for the subdirectory keeps files grouped
    by record type as requested.
    """
    record_type = sanitize_dirname(record.get("Type", "Other"))
    title = sanitize_filename(record.get("Title", "untitled"))

    # short hash to avoid collisions for very similar titles
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:6]
    filename = f"{title}_{url_hash}.pdf"

    subdir = OUTPUT_DIR / record_type
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / filename


def load_manifest() -> dict[str, dict]:
    """Load existing manifest so we can skip already-downloaded files."""
    existing: dict[str, dict] = {}
    if Path(MANIFEST_FILE).exists():
        with open(MANIFEST_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["link_to_item"]] = row
    return existing


def write_manifest(rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(MANIFEST_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Read all CSV records
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    log.info("Loaded %d records from %s", len(records), CSV_FILE)

    existing = load_manifest()
    log.info("%d records already downloaded (from manifest)", len(existing))

    manifest_rows: list[dict] = list(existing.values())
    session = requests.Session()

    for i, record in enumerate(records, start=1):
        page_url = record.get("Link to item", "").strip()
        if not page_url:
            log.warning("Row %d has no 'Link to item', skipping.", i)
            continue

        # Skip if already processed
        if page_url in existing:
            log.info("[%d/%d] Already downloaded: %s", i, len(records), page_url)
            continue

        log.info("[%d/%d] Fetching page: %s", i, len(records), page_url)
        time.sleep(REQUEST_DELAY)

        page_resp = get_with_retry(session, page_url)
        if page_resp is None:
            log.error("Could not fetch page: %s", page_url)
            manifest_rows.append({
                **record,
                "pdf_url": "",
                "local_path": "",
                "status": "page_fetch_failed",
            })
            continue

        pdf_url = find_pdf_url(page_url, page_resp.text)
        if not pdf_url:
            log.warning("No PDF found on page: %s", page_url)
            manifest_rows.append({
                **record,
                "pdf_url": "",
                "local_path": "",
                "status": "no_pdf_found",
            })
            continue

        local_path = derive_local_path(record, pdf_url)

        # Download PDF if not already on disk
        if local_path.exists():
            log.info("PDF already on disk: %s", local_path)
            status = "already_on_disk"
        else:
            log.info("Downloading PDF: %s -> %s", pdf_url, local_path)
            time.sleep(REQUEST_DELAY)
            pdf_resp = get_with_retry(session, pdf_url)
            if pdf_resp is None:
                log.error("Could not download PDF: %s", pdf_url)
                manifest_rows.append({
                    **record,
                    "pdf_url": pdf_url,
                    "local_path": "",
                    "status": "pdf_download_failed",
                })
                continue

            with open(local_path, "wb") as f:
                f.write(pdf_resp.content)
            log.info("Saved %d bytes to %s", len(pdf_resp.content), local_path)
            status = "downloaded"

        manifest_rows.append({
            **record,
            "pdf_url": pdf_url,
            "local_path": str(local_path),
            "status": status,
        })

        # Save manifest incrementally every 25 records
        if i % 25 == 0:
            write_manifest(manifest_rows)
            log.info("Manifest saved (%d rows).", len(manifest_rows))

    write_manifest(manifest_rows)
    log.info("Done. Manifest written to %s with %d rows.", MANIFEST_FILE, len(manifest_rows))

    # Summary
    statuses: dict[str, int] = {}
    for row in manifest_rows:
        s = row.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1
    log.info("Summary: %s", statuses)


if __name__ == "__main__":
    main()
