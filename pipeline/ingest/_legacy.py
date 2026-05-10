#!/usr/bin/env python3
"""Config-driven document ingestion pipeline.

Four phases:
  bootstrap  — LLM analyses seed URL / catalogue CSV to generate source config
  scrape     — discover document URLs and download PDFs/DOCX
  convert    — PDF/DOCX → structured markdown with table extraction
  enrich     — scrape structured metadata from each report's web page

Handles two discovery types:
  web_listing  — paginated listing page (e.g. ANAO performance audits)
  catalogue    — CSV file with document page URLs (e.g. ARENA knowledge bank)

Usage:
    python -m pipeline.ingest --domain anao --phase bootstrap [--dry-run]
    python -m pipeline.ingest --domain anao --phase scrape [--limit N]
    python -m pipeline.ingest --domain anao --phase convert [--workers N] [--force]
    python -m pipeline.ingest --domain anao --phase enrich [--workers N]
"""

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from urllib.parse import urljoin

import yaml

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DOMAINS_DIR = ROOT / "domains"
CORPORA_DIR = ROOT / "corpora"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def corpus_dir(domain: str) -> Path:
    return CORPORA_DIR / domain


def pdf_dir(domain: str) -> Path:
    return corpus_dir(domain) / "pdfs"


def md_dir(domain: str) -> Path:
    return corpus_dir(domain) / "markdown"


def table_dir(domain: str) -> Path:
    return corpus_dir(domain) / "tables"


def metadata_csv(domain: str) -> Path:
    return corpus_dir(domain) / "reports_metadata.csv"


def enriched_csv(domain: str) -> Path:
    return corpus_dir(domain) / "reports_metadata_enriched.csv"


def state_file(domain: str, phase: str) -> Path:
    return corpus_dir(domain) / f".{phase}_state.json"


# ---------------------------------------------------------------------------
# Config loading (minimal — does not require full DomainConfig)
# ---------------------------------------------------------------------------

def load_source_config(domain: str) -> dict:
    """Load just the source section from domain.yaml."""
    domain_yaml = DOMAINS_DIR / domain / "domain.yaml"
    if not domain_yaml.exists():
        raise FileNotFoundError(f"No domain.yaml at {domain_yaml}")
    with open(domain_yaml) as f:
        raw = yaml.safe_load(f)
    source = raw.get("source")
    if not source:
        raise ValueError(
            f"No 'source' section in {domain_yaml}. "
            f"Run --phase bootstrap to generate one."
        )
    return source


def load_domain_description(domain: str) -> str:
    """Load domain description from domain.yaml."""
    domain_yaml = DOMAINS_DIR / domain / "domain.yaml"
    if not domain_yaml.exists():
        return ""
    with open(domain_yaml) as f:
        raw = yaml.safe_load(f) or {}
    parts = []
    if raw.get("full_name"):
        parts.append(raw["full_name"])
    if raw.get("description"):
        parts.append(raw["description"])
    return " — ".join(parts) if parts else domain


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

SESSION = None


def get_session() -> requests.Session:
    global SESSION
    if SESSION is None:
        if requests is None:
            raise ImportError("requests not installed. Run: pip install requests")
        SESSION = requests.Session()
        SESSION.headers.update({
            "User-Agent": "BroadLearnings-Ingest/1.0 (research pipeline)"
        })
    return SESSION


def fetch_html(url: str, timeout: int = 60) -> str | None:
    """Fetch URL and return decoded HTML, or None on failure."""
    try:
        resp = get_session().get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    FETCH FAILED: {url} — {e}")
        return None


def download_file(url: str, filepath: Path, timeout: int = 120) -> bool:
    """Download a file to disk. Returns True on success."""
    try:
        resp = get_session().get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return filepath.exists() and filepath.stat().st_size > 0
    except Exception as e:
        print(f"    DOWNLOAD FAILED: {url} — {e}")
        return False


# ---------------------------------------------------------------------------
# HTML stripping for bootstrap (reduce token count)
# ---------------------------------------------------------------------------

def strip_html_for_llm(html: str, max_chars: int = 80000) -> str:
    """Strip scripts/styles/nav from HTML, keep structure for LLM analysis."""
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 not installed")
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # Keep the full HTML structure but compress whitespace
    text = soup.prettify()
    text = re.sub(r"\n\s*\n+", "\n", text)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated ...]"
    return text


# ---------------------------------------------------------------------------
# Phase: bootstrap
# ---------------------------------------------------------------------------

def phase_bootstrap(domain: str, dry_run: bool = False, model: str = "claude-sonnet-4-20250514"):
    """LLM analyses seed URL / catalogue to generate source config."""
    domain_yaml = DOMAINS_DIR / domain / "domain.yaml"
    if not domain_yaml.exists():
        raise FileNotFoundError(
            f"No domain.yaml at {domain_yaml}. "
            f"Create one with at least: source: {{ seed_url: '...' }}"
        )

    with open(domain_yaml) as f:
        raw = yaml.safe_load(f) or {}

    source = raw.get("source", {})
    seed_url = source.get("seed_url")
    catalogue_hint = source.get("catalogue")
    description = load_domain_description(domain)

    # Determine discovery type
    if catalogue_hint:
        discovery_type = "catalogue"
    elif seed_url:
        discovery_type = "web_listing"  # may upgrade to "sitemap" below
    else:
        raise ValueError(
            "domain.yaml source section needs either 'seed_url' (for web listing) "
            "or 'catalogue' (for CSV-driven). Add one and re-run."
        )

    print(f"Bootstrap: domain={domain}, type={discovery_type}")

    # Gather materials for the LLM
    materials_parts = []

    if discovery_type == "web_listing":
        print(f"  Fetching listing page: {seed_url}")
        listing_html = fetch_html(seed_url)
        if listing_html is None:
            raise RuntimeError(f"Could not fetch seed URL: {seed_url}")

        materials_parts.append(
            f"### Listing page: {seed_url}\n\n"
            f"```html\n{strip_html_for_llm(listing_html, max_chars=60000)}\n```"
        )

        # Follow a few sample report links to see report page structure
        # First, try to identify the dominant link pattern in the listing
        soup = BeautifulSoup(listing_html, "html.parser")
        all_hrefs = [a["href"].split("?")[0] for a in soup.find_all("a", href=True)]

        # Find the most common path prefix (likely the report pattern)
        prefix_counts = Counter()
        for href in all_hrefs:
            parts = [p for p in href.split("/") if p]
            if len(parts) >= 3 and href.startswith("/"):
                prefix = "/" + "/".join(parts[:2]) + "/"
                prefix_counts[prefix] += 1

        # Use the most frequent deep prefix as report pattern
        sample_links = []
        if prefix_counts:
            top_prefix = prefix_counts.most_common(1)[0][0]
            seen = set()
            for href in all_hrefs:
                if href.startswith(top_prefix) and href not in seen:
                    seen.add(href)
                    sample_links.append(href)

        # Fallback: any deep links
        if not sample_links:
            seen = set()
            for href in all_hrefs:
                parts = [p for p in href.split("/") if p]
                if len(parts) >= 3 and href.startswith("/") and href not in seen:
                    seen.add(href)
                    sample_links.append(href)

        # If the listing page has very few content links (JS-rendered site),
        # check for a sitemap as an alternative discovery method
        sitemap_urls = []
        if len(sample_links) < 5:
            base_domain = seed_url.split("//")[0] + "//" + seed_url.split("//")[1].split("/")[0]
            sitemap_url = base_domain + "/sitemap.xml"
            print(f"  Few links on listing page — checking sitemap: {sitemap_url}")
            sitemap_xml = fetch_html(sitemap_url)
            if sitemap_xml and len(sitemap_xml) > 500:
                # Extract URLs from sitemap
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(sitemap_xml)
                    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                    sitemap_urls = [
                        loc.text for loc in root.findall(".//s:loc", ns)
                        if loc.text
                    ]
                except ET.ParseError:
                    sitemap_urls = re.findall(r"<loc>(.*?)</loc>", sitemap_xml)

                # Filter to URLs that match the seed_url path
                seed_path = seed_url.rstrip("/").replace(base_domain, "")
                relevant = [u for u in sitemap_urls if seed_path in u]
                print(f"  Sitemap: {len(sitemap_urls)} total, {len(relevant)} matching {seed_path}")

                if relevant:
                    discovery_type = "sitemap"

                    # Analyse URL depth structure for the LLM
                    depth_counts = Counter()
                    depth_examples = {}
                    for u in relevant:
                        rel_path = u.replace(base_domain + seed_path, "").strip("/")
                        depth = rel_path.count("/") if rel_path else 0
                        depth_counts[depth] += 1
                        if depth not in depth_examples:
                            depth_examples[depth] = []
                        if len(depth_examples[depth]) < 5:
                            depth_examples[depth].append(u)

                    sitemap_summary = f"### Sitemap analysis: {sitemap_url}\n\n"
                    sitemap_summary += f"**Total URLs:** {len(sitemap_urls)}\n"
                    sitemap_summary += f"**Matching `{seed_path}`:** {len(relevant)}\n\n"
                    sitemap_summary += "**URL depth distribution:**\n\n"
                    for d in sorted(depth_counts):
                        sitemap_summary += f"- Depth {d}: {depth_counts[d]} URLs\n"
                        for ex in depth_examples[d]:
                            sitemap_summary += f"  - `{ex}`\n"
                    materials_parts.append(sitemap_summary)

                    # Use sitemap URLs as sample link source
                    sample_links = [u for u in relevant]

        # Pick 3 diverse samples (spread across the list)
        if sample_links:
            step = max(1, len(sample_links) // 3)
            samples = sample_links[0::step][:3]
            for href in samples:
                url = href if href.startswith("http") else urljoin(seed_url, href)
                print(f"  Fetching sample report: {url}")
                html = fetch_html(url)
                if html:
                    materials_parts.append(
                        f"### Sample report page: {url}\n\n"
                        f"```html\n{strip_html_for_llm(html, max_chars=30000)}\n```"
                    )
                time.sleep(1.0)

    elif discovery_type == "catalogue":
        # Find the CSV
        csv_pattern = catalogue_hint.get("file_pattern", "*.csv")
        # Search in corpus dir first, then home directory project dirs
        search_dirs = [
            corpus_dir(domain),
            Path.home() / domain.upper(),
            Path.home() / domain,
        ]
        csv_candidates = []
        for d in search_dirs:
            if d.exists():
                csv_candidates.extend(sorted(d.glob(csv_pattern)))
            if csv_candidates:
                break

        if not csv_candidates:
            raise FileNotFoundError(
                f"No CSV matching '{csv_pattern}' found. "
                f"Place the catalogue CSV in {corpus_dir(domain)}/"
            )

        csv_path = csv_candidates[0]
        print(f"  Reading catalogue: {csv_path}")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            sample_rows = []
            for i, row in enumerate(reader):
                sample_rows.append(row)
                if i >= 4:
                    break

        materials_parts.append(
            f"### Catalogue CSV: {csv_path.name}\n\n"
            f"**Columns:** {', '.join(headers)}\n\n"
            f"**Sample rows ({len(sample_rows)}):**\n\n"
            f"```json\n{json.dumps(sample_rows, indent=2)}\n```"
        )

        # Fetch a sample report page from the CSV
        url_col = catalogue_hint.get("url_column")
        if not url_col:
            # Try to guess: look for columns with "url" or "link" in name
            for col in headers:
                if "link" in col.lower() or "url" in col.lower():
                    url_col = col
                    break

        if url_col and sample_rows:
            for row in sample_rows[:2]:
                page_url = row.get(url_col, "")
                if page_url and page_url.startswith("http"):
                    print(f"  Fetching sample page: {page_url}")
                    html = fetch_html(page_url)
                    if html:
                        materials_parts.append(
                            f"### Sample report page: {page_url}\n\n"
                            f"```html\n{strip_html_for_llm(html, max_chars=30000)}\n```"
                        )
                    time.sleep(1.0)

    # Build the prompt
    template = (PROMPTS_DIR / "ingest_bootstrap.md").read_text()
    prompt = template.format(
        domain_description=description,
        discovery_type=discovery_type,
        materials="\n\n".join(materials_parts),
    )

    print(f"\n  Prompt: {len(prompt):,} chars ({len(prompt) // 4:,} est. tokens)")

    if dry_run:
        # Save prompt for review
        out_path = DOMAINS_DIR / domain / "_bootstrap_ingest_prompt.md"
        out_path.write_text(prompt)
        print(f"  Dry run — prompt saved to {out_path}")
        print(f"\n  First 2000 chars of prompt:\n")
        print(prompt[:2000])
        return

    # Call the LLM
    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic not installed. Run: pip install anthropic")

    print(f"\n  Calling {model}...")
    client = anthropic.Anthropic()
    response_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text
    print()

    # Save raw response
    resp_path = DOMAINS_DIR / domain / "_bootstrap_ingest_response.md"
    resp_path.write_text(response_text)
    print(f"\n  Response saved to {resp_path}")

    # Try to extract the YAML block
    yaml_match = re.search(r"```yaml\s*\n(.*?)```", response_text, re.DOTALL)
    if yaml_match:
        yaml_text = yaml_match.group(1).strip()
        parsed = yaml.safe_load(yaml_text)

        # Merge into domain.yaml
        if "source" in parsed:
            raw["source"] = parsed["source"]
        else:
            raw["source"] = parsed

        with open(domain_yaml, "w") as f:
            yaml.dump(raw, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"  Source config merged into {domain_yaml}")
        print(f"  REVIEW the config before running --phase scrape")
    else:
        print(f"  No YAML block found in response. Check {resp_path}")


# ---------------------------------------------------------------------------
# Phase: scrape
# ---------------------------------------------------------------------------

def phase_scrape(domain: str, limit: int | None = None):
    """Discover and download documents using the source config."""
    if requests is None:
        raise ImportError("requests not installed")
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 not installed")

    source = load_source_config(domain)
    source_type = source.get("type", "web_listing")
    delay = source.get("delay", 1.0)
    max_retries = source.get("max_retries", 3)
    doc_types = source.get("document_types", ["pdf"])

    pdf_dir(domain).mkdir(parents=True, exist_ok=True)

    # Load state for resumability
    sf = state_file(domain, "scrape")
    state = json.loads(sf.read_text()) if sf.exists() else {
        "phase": "discover", "report_urls": [], "downloaded": [], "failed": []
    }

    # Step 1: Discover report page URLs
    if source_type == "web_listing":
        report_urls = _discover_web_listing(domain, source, state, limit)
    elif source_type == "sitemap":
        report_urls = _discover_sitemap(domain, source, state, limit)
    elif source_type == "catalogue":
        report_urls = _discover_catalogue(domain, source, state, limit)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    # Step 2: Visit each report page and download documents
    print(f"\n=== Downloading documents ({len(report_urls)} pages) ===")

    already_done = set(state.get("downloaded", []))
    metadata_rows = []
    meta_csv = metadata_csv(domain)
    if meta_csv.exists():
        with open(meta_csv, encoding="utf-8") as f:
            metadata_rows = list(csv.DictReader(f))

    # Report page config
    rp = source.get("report_page", {})
    pdf_pattern = rp.get("pdf_pattern", r"\.pdf$")
    pdf_exclude = rp.get("pdf_exclude", [])
    docx_pattern = rp.get("docx_pattern")
    title_selector = rp.get("title_selector", "h1")

    total = len(report_urls)
    downloaded = len(already_done)
    no_doc = 0
    errors = list(state.get("failed", []))

    for i, entry in enumerate(report_urls):
        # entry is either a URL string or a dict with url + pre-existing metadata
        if isinstance(entry, dict):
            page_url = entry.get("url", "")
            pre_meta = {k: v for k, v in entry.items() if k != "url"}
        else:
            page_url = entry
            pre_meta = {}

        if not page_url:
            continue

        slug = page_url.rstrip("/").split("/")[-1]
        tag = f"[{i + 1}/{total}]"

        if page_url in already_done:
            continue

        print(f"  {tag} {slug}... ", end="", flush=True)

        html = fetch_html(page_url)
        if html is None:
            print("FETCH FAILED")
            errors.append(page_url)
            time.sleep(delay)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title_el = soup.select_one(title_selector)
        title = title_el.get_text(strip=True) if title_el else slug

        # Find document link
        doc_url = None
        doc_ext = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(pdf_pattern, href, re.I):
                if not any(ex in href.lower() for ex in pdf_exclude):
                    doc_url = urljoin(page_url, href)
                    doc_ext = "pdf"
                    break
        if not doc_url and docx_pattern:
            for a in soup.find_all("a", href=True):
                if re.search(docx_pattern, a["href"], re.I):
                    doc_url = urljoin(page_url, a["href"])
                    doc_ext = "docx"
                    break

        if not doc_url:
            print("NO DOCUMENT")
            no_doc += 1
            row = {"title": title, "url": page_url, "doc_url": "", "filename": ""}
            row.update(pre_meta)
            metadata_rows.append(row)
            already_done.add(page_url)
            time.sleep(delay)
            continue

        filename = f"{slug}.{doc_ext}"
        filepath = pdf_dir(domain) / filename

        if filepath.exists() and filepath.stat().st_size > 0:
            size_mb = filepath.stat().st_size / 1048576
            print(f"EXISTS ({size_mb:.1f} MB)")
            downloaded += 1
        else:
            ok = download_file(doc_url, filepath)
            if ok:
                size_mb = filepath.stat().st_size / 1048576
                print(f"OK ({size_mb:.1f} MB)")
                downloaded += 1
            else:
                print("DL FAILED")
                errors.append(page_url)
                time.sleep(delay)
                continue

        row = {
            "title": title, "url": page_url, "doc_url": doc_url,
            "filename": filename, "date": "",
        }
        row.update(pre_meta)

        # Extract date from <time> element if present
        time_el = soup.find("time")
        if time_el:
            row["date"] = time_el.get("datetime", time_el.get_text(strip=True))

        metadata_rows.append(row)
        already_done.add(page_url)

        # Periodic checkpoint
        if (i + 1) % 50 == 0:
            state["downloaded"] = list(already_done)
            state["failed"] = errors
            sf.write_text(json.dumps(state, indent=2))
            _write_metadata(meta_csv, metadata_rows)
            print(f"    >>> checkpoint: {downloaded} ok, {no_doc} no-doc, {len(errors)} err")

        time.sleep(delay)

    # Final save
    state["downloaded"] = list(already_done)
    state["failed"] = errors
    state["phase"] = "done"
    sf.write_text(json.dumps(state, indent=2))
    _write_metadata(meta_csv, metadata_rows)

    print(f"\n=== Done ===")
    print(f"  Reports:    {total}")
    print(f"  Downloaded: {downloaded}")
    print(f"  No doc:     {no_doc}")
    print(f"  Errors:     {len(errors)}")
    if errors:
        for e in errors[:10]:
            print(f"    {e}")
    print(f"\n  Documents: {pdf_dir(domain)}")
    print(f"  Metadata:  {meta_csv}")


def _discover_web_listing(domain: str, source: dict, state: dict, limit: int | None) -> list:
    """Paginate a listing page to collect report URLs."""
    if state.get("report_urls") and state.get("phase") != "discover":
        urls = state["report_urls"]
        print(f"Resuming: {len(urls)} report URLs from state, "
              f"{len(state.get('downloaded', []))} already done.")
        return urls[:limit] if limit else urls

    seed_url = source["seed_url"]
    pagination = source.get("pagination", {})
    pag_type = pagination.get("type", "query_param")
    listing = source.get("listing", {})
    link_pattern = listing.get("link_pattern", ".*")

    print(f"=== Discovering report URLs from {seed_url} ===")

    all_hrefs = set()
    page = 0

    while True:
        if pag_type == "query_param":
            param = pagination.get("param", "page")
            items = pagination.get("items_per_page", 100)
            url = f"{seed_url}?items_per_page={items}&page={page}"
        elif pag_type == "none":
            url = seed_url
        else:
            url = seed_url

        print(f"  Page {page}... ", end="", flush=True)
        html = fetch_html(url)
        if html is None:
            print("FAILED")
            break

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=re.compile(link_pattern))
        page_hrefs = {link["href"].split("?")[0] for link in links}

        new = page_hrefs - all_hrefs
        all_hrefs.update(page_hrefs)
        print(f"{len(new)} new (total: {len(all_hrefs)})")

        if not new:
            break
        if pag_type == "none":
            break

        # Check for next page
        if pag_type == "query_param":
            if not soup.find("a", {"rel": "next"}):
                break
        elif pag_type == "next_link":
            next_sel = pagination.get("selector", "a[rel=next]")
            if not soup.select_one(next_sel):
                break

        page += 1
        time.sleep(source.get("delay", 1.0))

    # Build full URLs
    base = source.get("seed_url", "").split("//")[0] + "//" + source["seed_url"].split("//")[1].split("/")[0]
    report_urls = sorted(urljoin(base, href) for href in all_hrefs)

    state["report_urls"] = report_urls
    state["phase"] = "scraping"
    state_file(domain, "scrape").write_text(json.dumps(state, indent=2))

    print(f"  Total: {len(report_urls)} unique report URLs\n")
    return report_urls[:limit] if limit else report_urls


def _discover_sitemap(domain: str, source: dict, state: dict, limit: int | None) -> list:
    """Discover document URLs from sitemap.xml."""
    if state.get("report_urls") and state.get("phase") != "discover":
        urls = state["report_urls"]
        print(f"Resuming: {len(urls)} report URLs from state, "
              f"{len(state.get('downloaded', []))} already done.")
        return urls[:limit] if limit else urls

    sitemap_cfg = source.get("sitemap", {})
    sitemap_url = sitemap_cfg.get("url")

    # Derive sitemap URL from seed_url if not specified
    if not sitemap_url:
        seed = source.get("seed_url", "")
        base = seed.split("//")[0] + "//" + seed.split("//")[1].split("/")[0]
        sitemap_url = base + "/sitemap.xml"

    url_pattern = sitemap_cfg.get("url_pattern", "")
    page_filter = sitemap_cfg.get("page_filter")  # e.g. depth or regex to select report pages

    print(f"=== Discovering URLs from sitemap: {sitemap_url} ===")

    xml_text = fetch_html(sitemap_url)
    if not xml_text:
        raise RuntimeError(f"Could not fetch sitemap: {sitemap_url}")

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        all_urls = [loc.text for loc in root.findall(".//s:loc", ns) if loc.text]
    except ET.ParseError:
        all_urls = re.findall(r"<loc>(.*?)</loc>", xml_text)

    print(f"  Total sitemap URLs: {len(all_urls)}")

    # Filter by URL pattern
    if url_pattern:
        filtered = [u for u in all_urls if re.search(url_pattern, u)]
    else:
        filtered = all_urls

    # Apply page_filter if specified (e.g. only depth-1 sub-pages that contain reports)
    if page_filter:
        filter_pattern = page_filter.get("pattern", "")
        if filter_pattern:
            filtered = [u for u in filtered if re.search(filter_pattern, u)]

    report_urls = sorted(filtered)

    state["report_urls"] = report_urls
    state["phase"] = "scraping"
    state_file(domain, "scrape").write_text(json.dumps(state, indent=2))

    print(f"  Matching URLs: {len(report_urls)}\n")
    return report_urls[:limit] if limit else report_urls


def _discover_catalogue(domain: str, source: dict, state: dict, limit: int | None) -> list:
    """Read document URLs from a catalogue CSV."""
    cat = source.get("catalogue", {})
    csv_pattern = cat.get("file_pattern", "*.csv")
    url_column = cat.get("url_column")
    meta_columns = cat.get("metadata_columns", [])

    # Find the CSV
    csv_candidates = sorted(corpus_dir(domain).glob(csv_pattern))
    if not csv_candidates:
        raise FileNotFoundError(
            f"No CSV matching '{csv_pattern}' in {corpus_dir(domain)}/. "
            f"Place the catalogue CSV there first."
        )

    csv_path = csv_candidates[0]
    print(f"=== Reading catalogue: {csv_path.name} ===")

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not url_column:
        raise ValueError("catalogue.url_column not set in source config")

    entries = []
    for row in rows:
        page_url = row.get(url_column, "").strip()
        if not page_url:
            continue
        entry = {"url": page_url}
        for mapping in meta_columns:
            csv_col = mapping.get("csv_column", "")
            field = mapping.get("field", "")
            if csv_col and field and csv_col in row:
                entry[field] = row[csv_col]
        entries.append(entry)

    print(f"  {len(entries)} entries with URLs\n")
    return entries[:limit] if limit else entries


# ---------------------------------------------------------------------------
# Phase: convert
# ---------------------------------------------------------------------------

# Font-size heading detection parameters (same as ANAO converter)
MIN_HEADING_RATIO = 1.05
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

            # Find caption
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


def _convert_document(entry: dict) -> dict:
    """Convert one PDF to structured markdown. Designed for ProcessPoolExecutor."""
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


def phase_convert(domain: str, workers: int | None = None, force: bool = False,
                  limit: int | None = None):
    """Convert downloaded PDFs to structured markdown."""
    if fitz is None:
        raise ImportError("pymupdf not installed. Run: pip install pymupdf")

    pdfs_path = pdf_dir(domain)
    md_out = md_dir(domain)
    tables_out = table_dir(domain)

    if not pdfs_path.exists():
        raise FileNotFoundError(f"No PDF directory at {pdfs_path}. Run --phase scrape first.")

    # Build file list from metadata CSV if available, else scan directory
    meta_csv = metadata_csv(domain)
    pdfs = []
    if meta_csv.exists():
        with open(meta_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                filename = row.get("filename", "")
                if not filename:
                    continue
                fp = pdfs_path / filename
                if fp.exists():
                    slug = filename.rsplit(".", 1)[0]
                    pdfs.append({
                        "pdf_path": str(fp),
                        "title": row.get("title", slug),
                        "slug": slug,
                        "md_dir": str(md_out),
                        "table_dir": str(tables_out),
                    })
    else:
        for fp in sorted(pdfs_path.glob("*.pdf")):
            slug = fp.stem
            pdfs.append({
                "pdf_path": str(fp),
                "title": slug.replace("-", " ").title(),
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

    total_tables = total_chars = total_pages = errors = completed = 0

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_convert_document, entry): entry for entry in pdfs}
        for future in as_completed(futures):
            entry = futures[future]
            completed += 1
            try:
                stats = future.result()
            except Exception as e:
                print(f"  [{completed:4d}/{len(pdfs)}] CRASH: {entry['slug']} — {e}")
                errors += 1
                continue

            if stats["error"]:
                print(f"  [{completed:4d}/{len(pdfs)}] ERROR: {stats['slug']} — {stats['error']}")
                errors += 1
                continue

            total_tables += stats["tables"]
            total_chars += stats["chars"]
            total_pages += stats["pages"]

            if completed % 50 == 0 or completed == len(pdfs):
                print(f"  [{completed:4d}/{len(pdfs)}] {stats['slug']} — "
                      f"{stats['pages']}p {stats['tables']}t {stats['chars']:,}c  "
                      f"(cumul: {total_pages:,}p {total_tables:,}t {total_chars:,}c)")

    print(f"\nDone.")
    print(f"  Converted:    {completed - errors}")
    print(f"  Skipped:      {skipped}")
    print(f"  Errors:       {errors}")
    print(f"  Total pages:  {total_pages:,}")
    print(f"  Total tables: {total_tables:,}")
    print(f"  Total chars:  {total_chars:,}")


# ---------------------------------------------------------------------------
# Phase: enrich
# ---------------------------------------------------------------------------

def _extract_metadata_from_page(args: tuple) -> dict:
    """Scrape metadata from a single report page. Designed for ProcessPoolExecutor."""
    row, metadata_fields, base_url = args

    url = row.get("url", "")
    result = dict(row)

    if not url:
        result["_error"] = "no_url"
        return result

    try:
        import requests as _req
        resp = _req.get(url, timeout=60, headers={
            "User-Agent": "BroadLearnings-Ingest/1.0 (research pipeline)"
        })
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        result["_error"] = f"fetch_failed: {e}"
        return result

    from bs4 import BeautifulSoup as _BS
    soup = _BS(html, "html.parser")

    for field_name, field_cfg in metadata_fields.items():
        method = field_cfg.get("method", "label_value")
        max_len = field_cfg.get("max_length")

        value = ""
        if method == "label_value":
            label = field_cfg.get("label", "")
            for div in soup.find_all("div", class_=lambda c: c and (
                "field--label-above" in c or "field--label-inline" in c
            )):
                label_el = div.find("div", class_="field__label")
                if label_el and label_el.get_text(strip=True) == label:
                    items = div.find_all("div", class_="field__item")
                    value = "; ".join(item.get_text(strip=True) for item in items)
                    break

        elif method == "selector":
            selector = field_cfg.get("selector", "")
            el = soup.select_one(selector)
            if el:
                value = el.get_text(strip=True)

        elif method == "attribute":
            selector = field_cfg.get("selector", "")
            attr = field_cfg.get("attribute", "")
            el = soup.select_one(selector) if selector else None
            if el and attr:
                value = el.get(attr, "")

        if max_len and len(value) > max_len:
            value = value[:max_len]
        result[field_name] = value

    result["_error"] = ""
    return result


def phase_enrich(domain: str, workers: int | None = None, limit: int | None = None):
    """Scrape structured metadata from report pages."""
    source = load_source_config(domain)
    rp = source.get("report_page", {})
    metadata_fields = rp.get("metadata_fields", {})

    if not metadata_fields:
        print("No metadata_fields configured in source.report_page — nothing to enrich.")
        return

    meta_csv = metadata_csv(domain)
    if not meta_csv.exists():
        raise FileNotFoundError(f"No metadata CSV at {meta_csv}. Run --phase scrape first.")

    with open(meta_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Check what's already enriched
    out_csv = enriched_csv(domain)
    done_urls = set()
    enriched_rows = []
    sf = state_file(domain, "enrich")
    if sf.exists():
        state = json.loads(sf.read_text())
        done_urls = set(state.get("done_urls", []))
        if out_csv.exists():
            with open(out_csv, encoding="utf-8") as f:
                enriched_rows = list(csv.DictReader(f))
        print(f"Resuming: {len(done_urls)} already enriched.")

    todo = [r for r in rows if r.get("url", "") not in done_urls]
    if limit:
        todo = todo[:limit]

    base_url = source.get("seed_url", "")
    n_workers = workers or min(cpu_count() or 4, 24)
    print(f"To enrich: {len(todo)}  Workers: {n_workers}")

    completed = errors = 0
    work_args = [(row, metadata_fields, base_url) for row in todo]

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_extract_metadata_from_page, a): a for a in work_args}
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result()
            except Exception as e:
                print(f"  [{completed}/{len(todo)}] CRASH: {e}")
                errors += 1
                continue

            if result.get("_error"):
                print(f"  [{completed}/{len(todo)}] FAILED: {result.get('url', '?')}")
                errors += 1

            enriched_rows.append(result)
            done_urls.add(result.get("url", ""))

            if completed % 100 == 0 or completed == len(todo):
                _write_metadata(out_csv, enriched_rows)
                sf.write_text(json.dumps({"done_urls": list(done_urls)}))
                print(f"  [{completed}/{len(todo)}] checkpoint — {errors} errors")

    _write_metadata(out_csv, enriched_rows)
    sf.write_text(json.dumps({"done_urls": list(done_urls)}))

    print(f"\nDone. Enriched: {completed - errors}, Errors: {errors}")
    print(f"  Output: {out_csv}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_metadata(csv_path: Path, rows: list[dict]):
    """Write metadata rows to CSV, preserving all columns."""
    if not rows:
        return
    all_keys = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen and not k.startswith("_"):
                all_keys.append(k)
                seen.add(k)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Document ingestion pipeline",
        usage="python -m pipeline.ingest --domain <name> --phase <phase> [options]",
    )
    parser.add_argument("--domain", required=True, help="Domain name (e.g. anao)")
    parser.add_argument("--phase", required=True,
                        choices=["bootstrap", "scrape", "convert", "enrich"],
                        help="Ingestion phase to run")
    parser.add_argument("--dry-run", action="store_true",
                        help="(bootstrap) Save prompt without calling LLM")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="(bootstrap) Model to use")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N items")
    parser.add_argument("--workers", type=int, default=None,
                        help="(convert/enrich) Number of parallel workers")
    parser.add_argument("--force", action="store_true",
                        help="(convert) Re-convert even if output exists")
    args = parser.parse_args()

    # Ensure domain directory exists
    domain_dir = DOMAINS_DIR / args.domain
    if not domain_dir.exists():
        domain_dir.mkdir(parents=True)
        (domain_dir / "prompts").mkdir()
        print(f"Created domain directory: {domain_dir}")

    # Ensure corpus directory exists
    corpus_dir(args.domain).mkdir(parents=True, exist_ok=True)

    if args.phase == "bootstrap":
        phase_bootstrap(args.domain, dry_run=args.dry_run, model=args.model)
    elif args.phase == "scrape":
        phase_scrape(args.domain, limit=args.limit)
    elif args.phase == "convert":
        phase_convert(args.domain, workers=args.workers, force=args.force,
                      limit=args.limit)
    elif args.phase == "enrich":
        phase_enrich(args.domain, workers=args.workers, limit=args.limit)


if __name__ == "__main__":
    main()
