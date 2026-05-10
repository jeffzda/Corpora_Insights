"""Base scraper contract and shared infrastructure.

Every domains/<name>/scrape.py must define a Scraper class inheriting from
BaseScraper and implementing discover(). The base class provides HTTP session
management, rate limiting, state/resume, download, and metadata CSV writing.

Usage in generated scraper:

    from pipeline.ingest.base import BaseScraper, DocumentRecord

    class Scraper(BaseScraper):
        def discover(self) -> list[DocumentRecord]:
            ...
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class DocumentRecord:
    """A single document (or multi-volume set) discovered by a scraper.

    Attributes:
        page_url:  The web page where the document was found.
        doc_urls:  Direct download URLs for PDFs/DOCXs. May have multiple
                   entries for multi-volume reports.
        title:     Human-readable title.
        metadata:  Arbitrary key-value pairs scraped from the page.
        group:     Optional grouping key (e.g. commission name, inquiry slug).
    """
    page_url: str
    doc_urls: list[str]
    title: str
    metadata: dict = field(default_factory=dict)
    group: str = ""

    def to_dict(self) -> dict:
        """Flatten for CSV output."""
        row = {
            "page_url": self.page_url,
            "title": self.title,
            "group": self.group,
            "doc_count": len(self.doc_urls),
        }
        # First doc_url gets its own column for simple corpora
        if self.doc_urls:
            row["doc_url"] = self.doc_urls[0]
        # All doc_urls as semicolon-separated for multi-volume
        row["doc_urls"] = "; ".join(self.doc_urls)
        row.update(self.metadata)
        return row


@dataclass
class DownloadReport:
    """Summary statistics from a download run."""
    total: int = 0
    downloaded: int = 0
    already_existed: int = 0
    no_document: int = 0
    failed: int = 0
    failed_urls: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Base scraper
# ---------------------------------------------------------------------------

class BaseScraper:
    """Base class for domain-specific scrapers.

    Subclasses must implement discover(). Everything else is provided.
    """

    def __init__(self, domain: str, corpus_dir: Path | None = None,
                 rate_limit: float = 1.0):
        from pipeline.ingest import CORPORA_DIR
        self.domain = domain
        self.corpus_dir = corpus_dir or (CORPORA_DIR / domain)
        self.pdf_dir = self.corpus_dir / "pdfs"
        self.metadata_csv = self.corpus_dir / "reports_metadata.csv"
        self.state_path = self.corpus_dir / ".scrape_state.json"
        self.rate_limit = rate_limit
        self._session = None
        self._last_request = 0.0

    # --- HTTP helpers (rate-limited) ---

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            if requests is None:
                raise ImportError("requests not installed. Run: pip install requests")
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "BroadLearnings-Ingest/1.0 (research pipeline)"
            })
        return self._session

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def fetch(self, url: str, timeout: int = 60) -> str | None:
        """Rate-limited HTTP GET returning decoded text, or None on failure."""
        self._throttle()
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"    FETCH FAILED: {url} — {e}")
            return None

    def fetch_soup(self, url: str, timeout: int = 60) -> BeautifulSoup | None:
        """Rate-limited fetch + parse. Returns BeautifulSoup or None."""
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4 not installed")
        html = self.fetch(url, timeout=timeout)
        if html is None:
            return None
        return BeautifulSoup(html, "html.parser")

    def head(self, url: str, timeout: int = 30) -> dict | None:
        """Rate-limited HEAD request. Returns dict with status, content_type, content_length."""
        self._throttle()
        try:
            resp = self.session.head(url, timeout=timeout, allow_redirects=True)
            return {
                "status": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": int(resp.headers.get("Content-Length", 0)),
            }
        except Exception:
            return None

    def download_file(self, url: str, filepath: Path, timeout: int = 120) -> bool:
        """Download a file to disk. Returns True on success."""
        self._throttle()
        try:
            resp = self.session.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            return filepath.exists() and filepath.stat().st_size > 0
        except Exception as e:
            print(f"    DOWNLOAD FAILED: {url} — {e}")
            return False

    # --- State management ---

    def load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"downloaded": [], "failed": []}

    def save_state(self, state: dict):
        self.state_path.write_text(json.dumps(state, indent=2))

    # --- Core interface ---

    def discover(self, limit: int | None = None) -> list[DocumentRecord]:
        """Discover all documents. Subclasses must implement this.

        Args:
            limit: If set, stop discovery after finding this many records.
                   Used by the checklist for smoke testing without hitting
                   every page. Scrapers should check this periodically.
        """
        raise NotImplementedError

    def download(self, records: list[DocumentRecord],
                 limit: int | None = None) -> DownloadReport:
        """Download documents from discovered records. Resumes from state."""
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        state = self.load_state()
        already_done = set(state.get("downloaded", []))
        failed_urls = list(state.get("failed", []))

        report = DownloadReport(total=len(records))
        metadata_rows = []

        to_process = records[:limit] if limit else records

        for i, rec in enumerate(to_process):
            tag = f"[{i + 1}/{len(to_process)}]"
            slug = rec.page_url.rstrip("/").split("/")[-1]

            if rec.page_url in already_done:
                report.already_existed += 1
                metadata_rows.append(rec.to_dict())
                continue

            if not rec.doc_urls:
                print(f"  {tag} {slug}... NO DOCUMENT")
                report.no_document += 1
                metadata_rows.append(rec.to_dict())
                already_done.add(rec.page_url)
                continue

            # Download each document URL (supports multi-volume)
            all_ok = True
            for doc_url in rec.doc_urls:
                ext = "pdf"
                if ".docx" in doc_url.lower():
                    ext = "docx"

                # Build filename from slug + doc URL
                doc_slug = doc_url.rstrip("/").split("/")[-1]
                if not doc_slug.endswith(f".{ext}"):
                    doc_slug = f"{slug}.{ext}"
                filepath = self.pdf_dir / doc_slug

                if filepath.exists() and filepath.stat().st_size > 0:
                    size_mb = filepath.stat().st_size / 1048576
                    print(f"  {tag} {doc_slug}... EXISTS ({size_mb:.1f} MB)")
                else:
                    ok = self.download_file(doc_url, filepath)
                    if ok:
                        size_mb = filepath.stat().st_size / 1048576
                        print(f"  {tag} {doc_slug}... OK ({size_mb:.1f} MB)")
                    else:
                        print(f"  {tag} {doc_slug}... FAILED")
                        all_ok = False

            if all_ok:
                report.downloaded += 1
                already_done.add(rec.page_url)
            else:
                report.failed += 1
                failed_urls.append(rec.page_url)

            metadata_rows.append(rec.to_dict())

            # Checkpoint every 50
            if (i + 1) % 50 == 0:
                state["downloaded"] = list(already_done)
                state["failed"] = failed_urls
                self.save_state(state)
                self._write_metadata(metadata_rows)
                print(f"    >>> checkpoint: {report.downloaded} ok, "
                      f"{report.no_document} no-doc, {report.failed} err")

        # Final save
        state["downloaded"] = list(already_done)
        state["failed"] = failed_urls
        self.save_state(state)
        self._write_metadata(metadata_rows)

        report.failed_urls = failed_urls
        return report

    def _write_metadata(self, rows: list[dict]):
        """Write metadata rows to CSV."""
        if not rows:
            return
        all_keys = []
        seen = set()
        for r in rows:
            for k in r:
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)
        self.metadata_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def run(self, limit: int | None = None, discover_only: bool = False):
        """Full pipeline: discover → download → report."""
        print(f"=== Discovering documents for {self.domain} ===")
        records = self.discover(limit=limit)
        print(f"  Found {len(records)} records")

        if discover_only:
            self._write_metadata([r.to_dict() for r in records])
            print(f"  Metadata written to {self.metadata_csv}")
            return records

        print(f"\n=== Downloading documents ===")
        report = self.download(records, limit=limit)

        print(f"\n=== Done ===")
        print(f"  Total:     {report.total}")
        print(f"  Downloaded: {report.downloaded}")
        print(f"  Existed:   {report.already_existed}")
        print(f"  No doc:    {report.no_document}")
        print(f"  Failed:    {report.failed}")
        if report.failed_urls:
            for u in report.failed_urls[:10]:
                print(f"    {u}")
        print(f"\n  Documents: {self.pdf_dir}")
        print(f"  Metadata:  {self.metadata_csv}")

        # Generate diagnostic report
        try:
            from pipeline.ingest.report import generate_report
            print()
            generate_report(self.domain)
        except Exception as e:
            print(f"  (report generation failed: {e})")

        return records

    # --- CLI convenience ---

    @classmethod
    def cli(cls, domain: str):
        """Standard CLI entry point for generated scrapers."""
        import argparse
        parser = argparse.ArgumentParser(description=f"Scrape {domain} documents")
        parser.add_argument("--limit", type=int, default=None,
                            help="Download only first N documents")
        parser.add_argument("--discover-only", action="store_true",
                            help="Discover URLs only, don't download")
        parser.add_argument("--rate-limit", type=float, default=1.0,
                            help="Seconds between requests")
        args = parser.parse_args()

        scraper = cls(domain, rate_limit=args.rate_limit)
        scraper.run(limit=args.limit, discover_only=args.discover_only)
