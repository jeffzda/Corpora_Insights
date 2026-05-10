"""Incremental ARENA Knowledge Bank update.

Diffs the live KB CSV export against the local manifest.csv, downloads only
documents that are new or no longer present, and appends rows to manifest.csv.

This is the canonical mechanism for keeping the ARENA corpus current. The
full discover-and-download path in `scrape.py` is preserved for cold-start
rebuilds, but day-to-day refreshes should use this script — it does not
re-visit pages already in the manifest, and it will not re-download PDFs.

Usage:
    python -m domains.arena.scrape_incremental [--dry-run] [--limit N]

Outputs:
    corpora/arena/snapshots/arena-kb-export_<unix>.csv  — the live KB CSV at run time
    corpora/arena/manifest.csv                          — updated in place
    corpora/arena/pdfs/<Type>/<title>_<hash>.pdf        — new downloads
    corpora/arena/.scrape_incremental_log.csv           — append-only run log

See docs/arena_corpus_update.md for the end-to-end refresh procedure
(scrape → marker convert → re-index).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "corpora" / "arena"
MANIFEST = CORPUS_DIR / "manifest.csv"
SNAPSHOT_DIR = CORPUS_DIR / "snapshots"
PDFS_DIR = CORPUS_DIR / "pdfs"
LOG_PATH = CORPUS_DIR / ".scrape_incremental_log.csv"

KB_EXPORT_URL = "https://arena.gov.au/knowledge-bank/?cust=ExportKB"
PROJECTS_EXPORT_URL = "https://arena.gov.au/projects/?cust=Export"
PORTFOLIO_PATH = CORPUS_DIR / "portfolio.csv"
USER_AGENT = "BroadLearnings-Ingest/1.0 (research pipeline)"
RATE_LIMIT_S = 1.0
TITLE_MAX = 120  # truncate normalised title to this many chars before _<hash>.pdf


# ---------------------------------------------------------------------------
# Filename derivation — must match the historical convention used by the
# original scraper so new files slot into the same Type subfolders alongside
# existing ones. See `analyse_naming.py` (one-shot, not committed) for the
# derivation; verified against 1,545 existing rows.
# ---------------------------------------------------------------------------

def safe_title(title: str) -> str:
    """Replicate the historical title→filename rule used in pdfs/<Type>/."""
    s = title.replace(" ", "_")
    s = re.sub(r"[/\\:>]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s[:TITLE_MAX]


def safe_type(t: str) -> str:
    if not t:
        return "Other"
    return t.replace(", ", "_").replace(" ", "_")


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:6]


def local_path_for(title: str, type_: str, pdf_url: str) -> str:
    return f"pdfs/{safe_type(type_)}/{safe_title(title)}_{url_hash(pdf_url)}.pdf"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

class Throttled:
    def __init__(self, rate_limit_s: float = RATE_LIMIT_S):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.rate = rate_limit_s
        self._last = 0.0

    def _throttle(self):
        d = time.time() - self._last
        if d < self.rate:
            time.sleep(self.rate - d)
        self._last = time.time()

    def get_text(self, url: str, timeout: int = 60) -> str | None:
        self._throttle()
        try:
            r = self.s.get(url, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  FETCH FAIL: {url} — {e}", flush=True)
            return None

    def download(self, url: str, dest: Path, timeout: int = 180) -> bool:
        self._throttle()
        try:
            r = self.s.get(url, timeout=timeout, stream=True)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            return dest.exists() and dest.stat().st_size > 0
        except Exception as e:
            print(f"  DOWNLOAD FAIL: {url} — {e}", flush=True)
            return False


# ---------------------------------------------------------------------------
# Page → PDF URL resolution
# ---------------------------------------------------------------------------

PDF_RE = re.compile(r"\.pdf$", re.I)


def find_pdf_url(http: Throttled, page_url: str) -> str | None:
    html = http.get_text(page_url)
    if html is None:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=PDF_RE):
        return urljoin(page_url, a["href"])
    return None


# ---------------------------------------------------------------------------
# Manifest IO
# ---------------------------------------------------------------------------

MANIFEST_FIELDS = [
    "Title", "Publish date", "Category", "Associated project name",
    "Link to item", "Type", "Link to project page", "Year", "Project Status",
    "pdf_url", "local_path", "status",
]


def load_manifest() -> tuple[list[dict], set[str]]:
    if not MANIFEST.exists():
        return [], set()
    with open(MANIFEST, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen = {r["Link to item"].strip() for r in rows if r.get("Link to item")}
    return rows, seen


def append_manifest(new_rows: list[dict]):
    rows, _ = load_manifest()
    rows.extend(new_rows)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_log(run_ts: str, summary: dict):
    is_new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "run_ts", "live_rows", "manifest_rows_before", "new_in_live",
            "removed_from_live", "downloaded", "no_pdf", "failed",
        ])
        if is_new:
            w.writeheader()
        w.writerow({"run_ts": run_ts, **summary})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Diff only; do not download or modify manifest.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Process only first N new entries.")
    args = ap.parse_args()

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    http = Throttled()

    # 1a. Snapshot live KB CSV
    print(f"[1/4] Fetching live KB export...", flush=True)
    text = http.get_text(KB_EXPORT_URL)
    if text is None:
        print("FATAL: could not fetch KB CSV", file=sys.stderr)
        return 2
    run_ts_unix = int(time.time())
    snapshot_path = SNAPSHOT_DIR / f"arena-kb-export_{run_ts_unix}.csv"
    snapshot_path.write_text(text, encoding="utf-8")
    print(f"      snapshot: {snapshot_path.relative_to(ROOT)}", flush=True)

    # 1b. Snapshot live projects CSV and refresh canonical portfolio.csv
    print(f"      Fetching live projects export...", flush=True)
    proj_text = http.get_text(PROJECTS_EXPORT_URL)
    if proj_text is None:
        print("WARNING: could not fetch projects CSV — portfolio.csv not refreshed", file=sys.stderr)
    else:
        proj_snapshot = SNAPSHOT_DIR / f"arena-projects-export_{run_ts_unix}.csv"
        proj_snapshot.write_text(proj_text, encoding="utf-8")
        # Refresh canonical portfolio.csv that the pipeline loader looks for
        # (see pipeline/extract.py: cat_cfg['portfolio']['file'] = 'portfolio.csv').
        # The projects CSV columns match the portfolio field_map exactly.
        if not args.dry_run:
            PORTFOLIO_PATH.write_text(proj_text, encoding="utf-8")
            n_proj = sum(1 for _ in csv.DictReader(io.StringIO(proj_text)))
            print(f"      projects snapshot: {proj_snapshot.relative_to(ROOT)} ({n_proj:,} rows)", flush=True)
            print(f"      portfolio.csv refreshed: {PORTFOLIO_PATH.relative_to(ROOT)}", flush=True)
        else:
            print(f"      projects snapshot: {proj_snapshot.relative_to(ROOT)} (dry-run; portfolio.csv not refreshed)", flush=True)

    live = list(csv.DictReader(io.StringIO(text)))
    live = [r for r in live
            if (r.get("Link to item") or "").startswith("https://arena.gov.au/knowledge-bank/")]
    print(f"      live KB rows: {len(live):,}", flush=True)

    # 2. Diff
    print(f"[2/4] Diffing against manifest...", flush=True)
    existing_rows, existing_links = load_manifest()
    print(f"      manifest rows: {len(existing_rows):,}", flush=True)

    live_links = {r["Link to item"].strip() for r in live}
    new_rows = [r for r in live if r["Link to item"].strip() not in existing_links]
    removed_links = existing_links - live_links

    print(f"      NEW in live: {len(new_rows)}", flush=True)
    print(f"      removed from live: {len(removed_links)}", flush=True)

    if removed_links:
        print(f"      (note: removed entries are kept in manifest as historical record)", flush=True)

    if not new_rows:
        print("[3/4] No new documents. Done.", flush=True)
        append_log(datetime.utcnow().isoformat(), {
            "live_rows": len(live), "manifest_rows_before": len(existing_rows),
            "new_in_live": 0, "removed_from_live": len(removed_links),
            "downloaded": 0, "no_pdf": 0, "failed": 0,
        })
        return 0

    if args.limit:
        new_rows = new_rows[:args.limit]
        print(f"      (limited to first {args.limit})", flush=True)

    if args.dry_run:
        print(f"[3/4] DRY RUN — would process {len(new_rows)} entries:", flush=True)
        for r in new_rows[:50]:
            print(f"      {r['Publish date']:>10}  {r['Type'][:14]:14}  {r['Title'][:90]}", flush=True)
        return 0

    # 3. Resolve PDF URLs and download
    print(f"[3/4] Resolving PDF URLs and downloading {len(new_rows)} entries...", flush=True)
    appended = []
    n_dl = n_nopdf = n_fail = 0
    t0 = time.time()
    for i, r in enumerate(new_rows, 1):
        page_url = r["Link to item"].strip()
        title = r["Title"]
        type_ = r.get("Type", "")
        elapsed = time.time() - t0
        rate = i / elapsed if elapsed > 0 else 0
        eta_s = (len(new_rows) - i) / rate if rate > 0 else 0
        print(f"  [{i}/{len(new_rows)}] {rate:.2f}/s eta={eta_s:.0f}s  {title[:80]}", flush=True)

        pdf_url = find_pdf_url(http, page_url)
        if not pdf_url:
            print(f"    NO PDF on page", flush=True)
            n_nopdf += 1
            appended.append({**{k: r.get(k, "") for k in MANIFEST_FIELDS[:9]},
                             "pdf_url": "", "local_path": "", "status": "no_pdf"})
            continue

        local = local_path_for(title, type_, pdf_url)
        # local is recorded relative to the corpus directory (matches existing manifest convention)
        dest = CORPUS_DIR / local
        if dest.exists() and dest.stat().st_size > 0:
            status = "downloaded"
            print(f"    EXISTS {dest.stat().st_size/1048576:.1f} MB  {local}", flush=True)
        else:
            ok = http.download(pdf_url, dest)
            if ok:
                status = "downloaded"
                print(f"    OK     {dest.stat().st_size/1048576:.1f} MB  {local}", flush=True)
                n_dl += 1
            else:
                status = "failed"
                n_fail += 1

        appended.append({**{k: r.get(k, "") for k in MANIFEST_FIELDS[:9]},
                         "pdf_url": pdf_url, "local_path": local, "status": status})

    # 4. Append to manifest + log
    print(f"[4/4] Appending {len(appended)} rows to manifest...", flush=True)
    append_manifest(appended)
    append_log(datetime.utcnow().isoformat(), {
        "live_rows": len(live), "manifest_rows_before": len(existing_rows),
        "new_in_live": len(new_rows), "removed_from_live": len(removed_links),
        "downloaded": n_dl, "no_pdf": n_nopdf, "failed": n_fail,
    })

    print(f"\nDone.  downloaded={n_dl}  no_pdf={n_nopdf}  failed={n_fail}", flush=True)
    print(f"Snapshot: {snapshot_path.relative_to(ROOT)}", flush=True)
    print(f"Log:      {LOG_PATH.relative_to(ROOT)}", flush=True)
    print(f"\nNext step: run marker conversion on the new PDFs:")
    print(f"  bash pipeline/ingest/marker_convert.sh arena")
    return 0


if __name__ == "__main__":
    sys.exit(main())
