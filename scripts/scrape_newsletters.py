#!/usr/bin/env python3
"""
Scrape ARENA Insights Newsletters from the ARENA Knowledge Bank.

Background
----------
ARENA Insights Newsletters are HTML email publications hosted on Campaign Monitor
(createsend.com). Each newsletter covers 2–4 ARENA projects in interview/summary
format. They are listed in the KB export as type 'InsightNewsletter' but have no
pdf_url — the original PDF scraper skipped them entirely.

This script:
  1. Reads the KB export to get all 62 newsletter KB page URLs
  2. Fetches each KB page to extract the Campaign Monitor archive URL
  3. Fetches the Campaign Monitor page and strips it to clean text
  4. Searches the text for known project names (from KB + portfolio CSVs)
  5. Saves each newsletter as a markdown file in markdown/newsletters/
  6. Writes newsletter_manifest.json — a doc list in the same format as
     all_agent_groups_v2.json entries, ready for 03b_extract_registry_per_doc.py

The manifest entries include:
  - md_path        — path to saved markdown file
  - Title          — newsletter title
  - Type           — "InsightNewsletter"
  - Category       — from KB export
  - Link to item   — KB page URL
  - matched_projects — list of project names found in the text (for QA)
  - campaign_url   — source Campaign Monitor URL

Usage
-----
    python scripts/scrape_newsletters.py
    python scripts/scrape_newsletters.py --dry-run   # fetch + parse, no file writes
    python scripts/scrape_newsletters.py --limit 10  # process first N newsletters

Then run extraction on the results:
    python scripts/03b_extract_registry_per_doc.py --source insights/newsletter_manifest.json

Rate limiting
-------------
Sleeps 1s between KB page fetches and 1s between Campaign Monitor fetches to
avoid hammering either server. Full run (~62 newsletters) takes ~3 minutes.

Outputs
-------
  markdown/newsletters/arena_insights_newsletter_edition_NN.md  (one per newsletter)
  insights/newsletter_manifest.json
"""

import argparse
import csv
import html as html_module
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB_EXPORT = ROOT / "arena-kb-export_1772889492.csv"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
OUT_DIR = ROOT / "markdown" / "newsletters"
MANIFEST_FILE = ROOT / "insights" / "newsletter_manifest.json"

FETCH_DELAY = 1.0   # seconds between requests (politeness)
HEADERS = {"User-Agent": "Mozilla/5.0 (research project; contact: arena-research)"}


# ---------------------------------------------------------------------------
# Name normalisation (mirrors 03b logic)
# ---------------------------------------------------------------------------

def normalise_name(name: str) -> str:
    name = html_module.unescape(name)
    name = re.sub(r'<[^>]+>', '', name)
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')
    name = re.sub(r'[\u2013\u2014]', '-', name)
    name = re.sub(r" ' ", " - ", name)
    return name.strip()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str, retries: int = 3) -> str | None:
    """Fetch URL and return decoded text, or None on failure."""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code} fetching {url} (attempt {attempt})")
            if e.code == 404:
                return None
        except Exception as e:
            print(f"    Error fetching {url} (attempt {attempt}): {e}")
        if attempt < retries:
            time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def extract_campaign_url(kb_html: str) -> str | None:
    """Find the Campaign Monitor archive link in a KB newsletter page.

    ARENA has used two Campaign Monitor domains over time:
      - createsend.com       (older editions, e.g. #30)
      - arena.createsend1.com (newer editions, e.g. #62)
      - arena.createsend1.com/t/ViewEmail/... (oldest editions, e.g. #1)
    All are Campaign Monitor — the subdomain difference is just ARENA's
    custom sending domain vs the shared platform domain.
    """
    pattern = r'href=["\']([^"\']*createsend[^"\']*)["\']'
    matches = re.findall(pattern, kb_html, re.I)
    if matches:
        return matches[0]
    return None


def clean_email_html(raw: str) -> str:
    """Strip HTML email markup and return readable plain text."""
    # Remove style and script blocks entirely
    raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
    # Decode entities and strip tags
    text = html_module.unescape(re.sub(r'<[^>]+>', ' ', raw))
    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Drop leading boilerplate (CSS artifacts before first real content)
    start = re.search(r'(ARENA Insights|Welcome to|This edition|Edition #\d)', text)
    if start:
        text = text[start.start():]
    return text.strip()


def find_project_matches(text: str, project_names: list[str]) -> list[str]:
    """Return project names (3+ words) found verbatim in newsletter text."""
    text_lower = text.lower()
    matches = []
    for name in project_names:
        if len(name.split()) >= 3 and name.lower() in text_lower:
            matches.append(name)
    # Sort longest first (most specific match at top)
    matches.sort(key=len, reverse=True)
    return matches


def make_slug(title: str) -> str:
    """Convert title to a safe filename slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:80]


# ---------------------------------------------------------------------------
# Load reference data
# ---------------------------------------------------------------------------

def load_project_names() -> list[str]:
    """Load all project names from both KB and portfolio exports."""
    names = set()
    with open(KB_EXPORT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = normalise_name(row.get("Associated project name", ""))
            if n:
                names.add(n)
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                n = normalise_name(row.get("Project", ""))
                if n:
                    names.add(n)
    return sorted(names)


def load_newsletters() -> list[dict]:
    """Return all InsightNewsletter rows from the KB export."""
    with open(KB_EXPORT, encoding="utf-8") as f:
        return [
            row for row in csv.DictReader(f)
            if row.get("Type", "").strip() in {"InsightNewsletter", "Insights, InsightNewsletter"}
        ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape ARENA Insights Newsletters")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and parse but do not write files")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N newsletters")
    args = parser.parse_args()

    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    newsletters = load_newsletters()
    if args.limit:
        newsletters = newsletters[:args.limit]

    project_names = load_project_names()
    print(f"Newsletters to process: {len(newsletters)}")
    print(f"Project names for matching: {len(project_names)}")
    print()

    manifest = []
    stats = {"fetched": 0, "no_campaign_url": 0, "no_content": 0, "saved": 0}

    for i, row in enumerate(newsletters, 1):
        title = row.get("Title", f"Newsletter {i}")
        kb_url = row.get("Link to item", "").strip()
        category = row.get("Category", "")

        print(f"[{i:02d}/{len(newsletters)}] {title}")

        if not kb_url:
            print("  SKIP: no KB URL")
            stats["no_campaign_url"] += 1
            continue

        # Step 1: fetch KB page to find Campaign Monitor URL
        kb_html = fetch(kb_url)
        time.sleep(FETCH_DELAY)

        if not kb_html:
            print("  SKIP: could not fetch KB page")
            stats["no_campaign_url"] += 1
            continue

        campaign_url = extract_campaign_url(kb_html)
        if not campaign_url:
            print("  SKIP: no Campaign Monitor link found in KB page")
            stats["no_campaign_url"] += 1
            continue

        print(f"  Campaign URL: {campaign_url[:70]}...")

        # Step 2: fetch Campaign Monitor archive
        campaign_html = fetch(campaign_url)
        time.sleep(FETCH_DELAY)

        if not campaign_html:
            print("  SKIP: could not fetch Campaign Monitor page")
            stats["no_content"] += 1
            continue

        # Step 3: clean to readable text
        text = clean_email_html(campaign_html)
        if len(text) < 200:
            print(f"  SKIP: content too short after cleaning ({len(text)} chars)")
            stats["no_content"] += 1
            continue

        # Step 4: find project name matches
        matched = find_project_matches(text, project_names)

        stats["fetched"] += 1
        print(f"  Content: {len(text):,} chars | Projects matched: {len(matched)}")
        if matched:
            for m in matched[:5]:
                print(f"    - {m}")

        # Step 5: save markdown and build manifest entry
        slug = make_slug(title)
        md_path = OUT_DIR / f"{slug}.md"
        md_content = f"# {title}\n\nSource: {kb_url}\nCampaign: {campaign_url}\n\n---\n\n{text}"

        if not args.dry_run:
            md_path.write_text(md_content, encoding="utf-8")

        manifest.append({
            "Title": title,
            "Type": row.get("Type", "InsightNewsletter"),
            "Category": category,
            "Publish date": row.get("Publish date", ""),
            "Year": row.get("Year", ""),
            "Link to item": kb_url,
            "Link to project page": row.get("Link to project page", ""),
            "Associated project name": row.get("Associated project name", ""),
            "Project Status": row.get("Project Status", ""),
            "md_path": str(md_path),
            "md_size": len(text),
            "campaign_url": campaign_url,
            "matched_projects": matched,
        })
        stats["saved"] += 1

    if not args.dry_run and manifest:
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
        print(f"\nManifest written to {MANIFEST_FILE} ({len(manifest)} entries)")

    print(f"\nDone.")
    print(f"  Fetched + saved: {stats['saved']}")
    print(f"  No Campaign URL: {stats['no_campaign_url']}")
    print(f"  No content:      {stats['no_content']}")


if __name__ == "__main__":
    main()
