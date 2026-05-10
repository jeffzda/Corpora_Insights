"""ARENA Knowledge Bank scraper.

LLM-generated, then manually corrected.
Source: Two CSV exports fetched automatically via GET:
  1. KB export:       GET arena.gov.au/knowledge-bank/?cust=ExportKB
     Contains: KB item titles, page URLs, categories, project associations
  2. Projects export: GET arena.gov.au/projects/?cust=Export
     Contains: project-level metadata (funding, location, partners, etc.)

The KB CSV drives discovery (one row per document). The projects CSV provides
additional project-level metadata, joined via "Link to project page".
The scraper visits each KB page only to find the PDF download URL.
"""

import csv
import io
import re
from urllib.parse import urljoin

from pipeline.ingest.base import BaseScraper, DocumentRecord

EXPECTED_COUNT = 1440

KB_EXPORT_URL = "https://arena.gov.au/knowledge-bank/?cust=ExportKB"
PROJECTS_EXPORT_URL = "https://arena.gov.au/projects/?cust=Export"


class Scraper(BaseScraper):

    def _fetch_csv(self, url: str, label: str) -> list[dict]:
        """Fetch a CSV export and return rows as list of dicts."""
        print(f"  Fetching {label}: {url}")
        text = self.fetch(url)
        if not text:
            print(f"  FAILED to fetch {label}")
            return []
        rows = list(csv.DictReader(io.StringIO(text)))
        print(f"  {label}: {len(rows)} rows")
        return rows

    def _load_projects_index(self) -> dict:
        """Fetch projects CSV and index by project URL."""
        rows = self._fetch_csv(PROJECTS_EXPORT_URL, "projects catalogue")
        index = {}
        for row in rows:
            url = (row.get("Link to project") or "").strip()
            if url:
                index[url] = row
        return index

    def discover(self, limit: int | None = None) -> list[DocumentRecord]:
        """Fetch KB catalogue CSV, join with projects CSV, visit each KB page for PDF links."""
        # Fetch KB catalogue
        kb_rows = self._fetch_csv(KB_EXPORT_URL, "KB catalogue")
        if not kb_rows:
            return []

        # Filter to KB items only
        rows = [r for r in kb_rows
                if (r.get("Link to item") or "").startswith("https://arena.gov.au/knowledge-bank/")]
        print(f"  KB items: {len(rows)}")

        # Fetch projects index for enrichment
        projects = self._load_projects_index()

        if limit:
            rows = rows[:limit]
            print(f"  (limited to {limit} for testing)")

        # Visit each KB page to find PDF link
        records = []
        for i, row in enumerate(rows):
            page_url = row["Link to item"].strip()
            slug = page_url.rstrip("/").split("/")[-1]
            tag = f"[{i + 1}/{len(rows)}]"
            print(f"  {tag} {slug}... ", end="", flush=True)

            soup = self.fetch_soup(page_url)
            if soup is None:
                print("FAILED")
                continue

            # Title from page, fallback to CSV
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else row.get("Title", slug)

            # Find PDF links on the page
            doc_urls = []
            for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
                href = a["href"]
                full = urljoin(page_url, href)
                if full not in doc_urls:
                    doc_urls.append(full)

            # Metadata from KB CSV
            metadata = {
                "publish_date": row.get("Publish date", ""),
                "category": row.get("Category", ""),
                "associated_project": row.get("Associated project name", ""),
                "type": row.get("Type", ""),
                "year": row.get("Year", ""),
                "project_status": row.get("Project Status", ""),
                "project_url": row.get("Link to project page", ""),
            }

            # Enrich with project-level metadata if available
            project_url = (row.get("Link to project page") or "").strip()
            proj = projects.get(project_url)
            if proj:
                for key, val in proj.items():
                    if key not in ("Link to project",) and val:
                        pkey = f"project_{key.lower().replace(' ', '_')}"
                        metadata.setdefault(pkey, val)

            status = f"OK ({len(doc_urls)} doc)" if doc_urls else "NO PDF"
            print(status)

            records.append(DocumentRecord(
                page_url=page_url,
                doc_urls=doc_urls,
                title=title,
                metadata=metadata,
                group=row.get("Associated project name", ""),
            ))

        return records


if __name__ == "__main__":
    Scraper.cli("arena")
