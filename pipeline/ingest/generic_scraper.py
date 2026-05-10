"""Naive generic scraper.

Given only a landing page URL, attempts to:
1. Reconnaissance — analyse the page to find document links, pagination,
   export/download mechanisms, and metadata sources
2. Discover — follow pagination or export mechanisms to find all documents
3. Download — fetch PDFs from discovered document pages

The only human input is the landing page URL. Everything else is inferred.

Usage:
    from pipeline.ingest.generic_scraper import NaiveScraper
    scraper = NaiveScraper("anao", landing_url="https://www.anao.gov.au/pubs/performance-audit")
    recon = scraper.reconnaissance()
    records = scraper.discover(limit=10)
"""

from __future__ import annotations

import csv
import html as html_mod
import io
import json
import re
from collections import Counter
from urllib.parse import urljoin, urlparse
from pathlib import Path

from pipeline.ingest.base import BaseScraper, DocumentRecord


class ReconReport:
    """Structured output from page reconnaissance."""

    def __init__(self):
        self.landing_url = ""
        self.page_title = ""
        self.total_links = 0
        self.internal_links = []        # (href, text) pairs
        self.external_links = []
        self.pdf_links = []             # direct PDF links on the landing page
        self.pagination = None          # dict if found: {type, next_url, page_param, ...}
        self.export_mechanisms = []     # list of dicts: {type, url, label}
        self.document_link_candidates = []  # (pattern, count, sample_hrefs)
        self.metadata_sources = []      # identified metadata mechanisms
        self.item_count_hint = None     # any visible count on the page
        self.human_actions = []         # list of dicts: {action, reason, file_hint}
        self.js_dependent = False       # True if key features require JavaScript
        self.manual_files_found = []    # CSV/JSON files already in corpus dir
        self.sitemap_urls = []          # URLs from sitemap.xml matching landing path
        self.api_endpoints = []         # intercepted JSON API endpoints: {url, records, fields}
        self.wp_api = None              # WordPress REST API: {post_type, api_url, total, ...}
        self.openapi_spec = None        # OpenAPI/Swagger spec: {spec_url, title, version, endpoints, ...}

    def summary(self) -> str:
        lines = [
            f"# Reconnaissance: {self.landing_url}",
            f"Page title: {self.page_title}",
            f"Total links: {self.total_links}",
            f"Internal links: {len(self.internal_links)}",
            f"PDF links on landing page: {len(self.pdf_links)}",
            "",
        ]

        if self.export_mechanisms:
            lines.append("## Export / bulk download mechanisms")
            for m in self.export_mechanisms:
                lines.append(f"  - [{m['type']}] {m['label']}: {m['url']}")
            lines.append("")

        if self.pagination:
            lines.append(f"## Pagination: {self.pagination}")
            lines.append("")

        if self.document_link_candidates:
            lines.append("## Document link patterns (by URL path prefix)")
            for pattern, count, samples in self.document_link_candidates:
                lines.append(f"  {pattern}: {count} links")
                for s in samples[:3]:
                    lines.append(f"    - {s}")
            lines.append("")

        if self.metadata_sources:
            lines.append("## Metadata sources")
            for src in self.metadata_sources:
                lines.append(f"  - {src}")
            lines.append("")

        if self.item_count_hint:
            lines.append(f"## Item count hint: {self.item_count_hint}")
            lines.append("")

        if self.sitemap_urls:
            lines.append(f"## Sitemap: {len(self.sitemap_urls)} URLs matching landing path")
            lines.append("")

        if self.openapi_spec:
            spec = self.openapi_spec
            lines.append(f"## OpenAPI: {spec['title']} v{spec['version']}")
            lines.append(f"  Spec URL: {spec['spec_url']}")
            for ep in spec.get("endpoints", []):
                lines.append(f"  {ep['method']:6s} {ep['path']}  — {ep.get('summary', '')}")
            lines.append("")

        if self.api_endpoints:
            best = self.api_endpoints[0]
            source = best.get("source", "intercepted")
            lines.append(f"## API ({source}): {best['record_count']} records, "
                         f"{len(best['fields'])} fields")
            lines.append(f"  Endpoint: {best['url']}")
            lines.append(f"  Fields: {', '.join(best['fields'][:15])}")
            lines.append("")

        if self.wp_api:
            wp = self.wp_api
            lines.append(f"## WordPress REST API: {wp['name']} ({wp['post_type']})")
            lines.append(f"  Endpoint: {wp['api_url']}")
            lines.append(f"  Total items: {wp['total']}")
            if wp.get("has_acf_download"):
                lines.append(f"  PDF downloads available via ACF field")
            lines.append("")

        if self.manual_files_found:
            lines.append("## Manual files found in corpus directory")
            for f in self.manual_files_found:
                lines.append(f"  - {f}")
            lines.append("")

        if self.human_actions:
            lines.append("## Human actions required")
            lines.append("")
            for i, action in enumerate(self.human_actions, 1):
                lines.append(f"  {i}. {action['action']}")
                lines.append(f"     Why: {action['reason']}")
                if action.get("file_hint"):
                    lines.append(f"     Save as: corpora/<domain>/{action['file_hint']}")
                lines.append("")

        if not self.human_actions:
            lines.append("## No human actions required — automated discovery should work")

        return "\n".join(lines)


class NaiveScraper(BaseScraper):
    """Scraper that starts from a landing page URL with no prior knowledge."""

    def __init__(self, domain: str, landing_url: str, **kwargs):
        super().__init__(domain, **kwargs)
        self.landing_url = landing_url
        self.landing_parsed = urlparse(landing_url)
        self.site_base = f"{self.landing_parsed.scheme}://{self.landing_parsed.netloc}"
        self._recon: ReconReport | None = None
        self._chosen_strategy = None
        self._export_csv_rows = None   # cached CSV rows if export found
        self._field_whitelist: set[str] | None = None  # curated fields after LLM selection
        self._curation_samples: list[dict] = []       # raw metadata from first N pages
        self._curation_buffer: list[DocumentRecord] = []  # records awaiting retroactive filtering
        self._curation_sample_target = 5              # pages to sample before curating
        self._soup_cache: dict[str, BeautifulSoup] = {}  # pop-on-use to avoid stale data
        self._checkpoint_path = self.corpus_dir / ".discovery_checkpoint.json"
        self._checkpoint_interval = 100  # save every N records

    def fetch_soup(self, url: str, timeout: int = 60) -> BeautifulSoup | None:
        """Rate-limited fetch + parse, with pop-on-use cache.

        If the URL was pre-cached (e.g. from reconnaissance), returns the
        cached soup and removes it from the cache to prevent stale reuse.
        """
        cached = self._soup_cache.pop(url, None)
        if cached is not None:
            return cached
        return super().fetch_soup(url, timeout=timeout)

    # ---- Checkpointing ----

    def _save_checkpoint(self, strategy: str, records: list[DocumentRecord],
                         last_page: int = 0):
        """Write discovery checkpoint for resumption after interruption."""
        data = {
            "landing_url": self.landing_url,
            "strategy": strategy,
            "last_page": last_page,
            "record_count": len(records),
            "records": [r.to_dict() for r in records],
        }
        with open(self._checkpoint_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_checkpoint(self) -> dict | None:
        """Load and validate a discovery checkpoint. Returns None if invalid."""
        if not self._checkpoint_path.exists():
            return None
        try:
            with open(self._checkpoint_path) as f:
                data = json.load(f)
            if data.get("landing_url") != self.landing_url:
                print(f"  Checkpoint exists but for different URL — ignoring")
                return None
            print(f"  Resuming from checkpoint: {data['record_count']} records, "
                  f"strategy={data['strategy']}, last_page={data['last_page']}")
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    def _clear_checkpoint(self):
        """Delete checkpoint on successful completion."""
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()

    @staticmethod
    def _records_from_checkpoint(data: dict) -> list[DocumentRecord]:
        """Reconstruct DocumentRecords from checkpoint data."""
        records = []
        for rd in data.get("records", []):
            rec = DocumentRecord(
                page_url=rd.get("page_url", ""),
                doc_urls=rd.get("doc_urls", []),
                title=rd.get("title", ""),
                metadata=rd.get("metadata", {}),
            )
            records.append(rec)
        return records

    # ---- Reconnaissance ----

    def reconnaissance(self) -> ReconReport:
        """Analyse the landing page to understand site structure."""
        recon = ReconReport()
        recon.landing_url = self.landing_url

        # Check for manually-provided files in the corpus directory
        self._check_manual_files(recon)

        print(f"  Fetching landing page: {self.landing_url}")
        soup = self.fetch_soup(self.landing_url)
        if soup is None:
            print("  FAILED to fetch landing page")
            self._recon = recon
            return recon

        # Page title
        h1 = soup.find("h1")
        recon.page_title = h1.get_text(strip=True) if h1 else ""
        print(f"  Page title: {recon.page_title}")

        # Collect all links
        all_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)[:100]
            full_url = urljoin(self.landing_url, href)
            parsed = urlparse(full_url)

            if parsed.netloc == self.landing_parsed.netloc or not parsed.netloc:
                all_links.append((href, full_url, text, "internal"))
                recon.internal_links.append((full_url, text))
            else:
                recon.external_links.append((full_url, text))

        recon.total_links = len(all_links) + len(recon.external_links)

        # Find direct PDF links
        for href, full_url, text, loc_type in all_links:
            if re.search(r"\.pdf(\?|$)", href, re.I):
                recon.pdf_links.append((full_url, text))
        print(f"  Direct PDF links: {len(recon.pdf_links)}")

        # Find export / bulk download mechanisms
        self._find_export_mechanisms(soup, recon)

        # Find pagination
        self._find_pagination(soup, recon)

        # Analyse link patterns to identify document link candidates
        self._analyse_link_patterns(all_links, recon)

        # Look for item counts on the page
        self._find_item_count(soup, recon)

        # --- API-first discovery ---
        # Step 1: Probe for OpenAPI/Swagger docs (cheapest — single GET)
        self._probe_api_docs(soup, recon)

        # Step 2: If no API found via docs, try headless browser interception
        js_app_mount = self._detect_js_app_mount(soup)
        if js_app_mount:
            print(f"  JS app mount detected: {js_app_mount} — treating as JS shell")

        has_content = (
            recon.pagination
            or recon.export_mechanisms
            or recon.document_link_candidates
            or recon.pdf_links
        )
        if js_app_mount:
            has_content = False

        if recon.api_endpoints:
            # API already found via OpenAPI spec — skip headless entirely
            pass
        elif not has_content and not recon.manual_files_found:
            # Full headless: page is a JS shell — intercept APIs AND
            # re-analyse the rendered DOM for links/pagination
            rendered_soup = self._try_headless_render(recon)
            if rendered_soup:
                # Re-run analysis on the rendered DOM
                recon.internal_links.clear()
                recon.external_links.clear()
                recon.pdf_links.clear()

                all_links = []
                for a in rendered_soup.find_all("a", href=True):
                    href = a["href"].strip()
                    text = a.get_text(strip=True)[:100]
                    full_url = urljoin(self.landing_url, href)
                    parsed = urlparse(full_url)
                    if parsed.netloc == self.landing_parsed.netloc or not parsed.netloc:
                        all_links.append((href, full_url, text, "internal"))
                        recon.internal_links.append((full_url, text))
                    else:
                        recon.external_links.append((full_url, text))

                recon.total_links = len(all_links) + len(recon.external_links)

                for href, full_url, text, loc_type in all_links:
                    if re.search(r"\.pdf(\?|$)", href, re.I):
                        recon.pdf_links.append((full_url, text))

                self._find_export_mechanisms(rendered_soup, recon)
                self._find_pagination(rendered_soup, recon)
                self._analyse_link_patterns(all_links, recon)
                self._find_item_count(rendered_soup, recon)

                print(f"  After headless render: {recon.total_links} links, "
                      f"{len(recon.pdf_links)} PDFs, "
                      f"{len(recon.document_link_candidates)} doc patterns")
        else:
            # Static page has content but no API found yet — try headless
            # for API interception (skip DOM re-analysis)
            self._try_headless_render(recon, api_only=True)

        # Check sitemap as a fallback discovery mechanism
        self._check_sitemap(recon)

        # Check for WordPress REST API (wp-content in HTML → probe wp-json)
        self._check_wp_api(soup, recon)

        # Respect robots.txt crawl-delay
        self._check_robots_txt()

        # Generate human action items based on what we found
        self._generate_human_actions(recon)

        # Cache the landing page soup so discovery doesn't re-fetch it
        # (pop-on-use: consumed once by pagination page 0, then discarded)
        if soup is not None:
            self._soup_cache[self.landing_url] = soup

        self._recon = recon
        return recon

    @staticmethod
    def _detect_js_app_mount(soup) -> str | None:
        """Detect JS framework mount points that indicate a SPA/JS shell.

        Returns a description string if detected, None otherwise.
        Checks for React, Angular, Vue, and generic app containers
        that are empty or near-empty in the static HTML.
        """
        # Common SPA mount-point IDs and attributes
        mount_ids = ("app", "root", "react-root", "react-app", "__next",
                     "vue-app", "main-app", "application")
        for mid in mount_ids:
            el = soup.find(id=mid)
            if el and len(el.get_text(strip=True)) < 50:
                return f'<{el.name} id="{mid}"> (empty)'

        # React: data-reactroot on an empty element
        react_el = soup.find(attrs={"data-reactroot": True})
        if react_el and len(react_el.get_text(strip=True)) < 50:
            return "data-reactroot (empty)"

        # Angular: <app-root> element
        app_root = soup.find("app-root")
        if app_root and len(app_root.get_text(strip=True)) < 50:
            return "<app-root> (Angular)"

        # Generic: script tags that reference JS app bundles in main content
        # when the main content area has very little text
        main = soup.find("main") or soup.find(id="content") or soup.find(
            class_=re.compile(r"(main|content)[-_]?(area|body|container)", re.I))
        if main:
            scripts = main.find_all("script", src=True)
            main_text = main.get_text(strip=True)
            if scripts and len(main_text) < 100:
                return f"main content area has {len(scripts)} scripts, {len(main_text)} chars text"

        return None

    def _find_export_mechanisms(self, soup, recon: ReconReport):
        """Look for CSV export buttons, download links, API endpoints."""
        export_patterns = [
            # Links/buttons with export-related text
            (r"export|download.*(csv|excel|data)|bulk.*download|^csv$|spreadsheet|get\s+data|download.*grid",
             "text_match"),
            # Links with export-related URL params
            (r"[?&](cust=Export|format=csv|export=|action=export|download=)",
             "url_param"),
            # Links to CSV/Excel files
            (r"\.(csv|xlsx?|json)(\?|$)",
             "file_extension"),
        ]

        def _check_export(tag, href, text, full_url):
            """Check a single element against export patterns, add to recon."""
            for pattern, match_type in export_patterns:
                target = text if match_type == "text_match" else href
                if re.search(pattern, target, re.I):
                    if match_type == "text_match" and len(text) > 40:
                        continue
                    mechanism = {
                        "type": match_type,
                        "url": full_url,
                        "label": text[:80] or href[:80],
                        "href": href,
                    }
                    if not any(m["url"] == full_url for m in recon.export_mechanisms):
                        recon.export_mechanisms.append(mechanism)
                    return True
            # Also check title and aria-label attributes — export buttons
            # often have icon-only visible text with descriptive attributes
            for attr in ("title", "aria-label"):
                attr_val = tag.get(attr, "")
                if attr_val and re.search(export_patterns[0][0], attr_val, re.I):
                    if len(attr_val) <= 80:
                        mechanism = {
                            "type": "attr_match",
                            "url": full_url,
                            "label": attr_val[:80],
                            "href": href,
                        }
                        if not any(m["url"] == full_url for m in recon.export_mechanisms):
                            recon.export_mechanisms.append(mechanism)
                        return True
            return False

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)
            full_url = urljoin(self.landing_url, href)
            _check_export(a, href, text, full_url)

        # Also check <button> elements — JS-triggered exports won't be <a> tags
        for btn in soup.find_all("button"):
            text = btn.get_text(strip=True)
            # Buttons don't have href; use landing URL as placeholder
            href = btn.get("data-href", "") or btn.get("data-url", "") or ""
            full_url = urljoin(self.landing_url, href) if href else self.landing_url
            _check_export(btn, href, text, full_url)

        # Also check for buttons/forms with export actions
        for form in soup.find_all("form"):
            action = form.get("action", "")
            if re.search(r"export|download|csv", action, re.I):
                recon.export_mechanisms.append({
                    "type": "form",
                    "url": urljoin(self.landing_url, action),
                    "label": f"Form action: {action}",
                    "href": action,
                })

        if recon.export_mechanisms:
            print(f"  Export mechanisms found: {len(recon.export_mechanisms)}")
            for m in recon.export_mechanisms:
                print(f"    [{m['type']}] {m['label'][:60]}: {m['url'][:80]}")

    def _find_pagination(self, soup, recon: ReconReport):
        """Detect pagination patterns."""
        # Check for rel="next"
        next_link = soup.find("a", rel="next")
        if next_link:
            href = next_link.get("href", "")
            recon.pagination = {
                "type": "rel_next",
                "next_url": urljoin(self.landing_url, href),
                "next_href": href,
            }
            # Try to extract page param
            page_match = re.search(r"[?&](page)=(\d+)", href)
            if page_match:
                recon.pagination["page_param"] = page_match.group(1)
                recon.pagination["next_page"] = int(page_match.group(2))
            print(f"  Pagination: rel=next found → {recon.pagination['next_url']}")
            return

        # Check for pager elements (common in Drupal, WordPress)
        pager = soup.find(["nav", "ul", "div"],
                          class_=lambda c: c and any(
                              p in (c if isinstance(c, str) else " ".join(c))
                              for p in ["pager", "pagination", "page-numbers"]
                          ))
        if pager:
            page_links = pager.find_all("a", href=True)
            if page_links:
                # Find highest page number from URL params, link text, or aria-label
                max_page = 0
                is_js_pager = False
                for pl in page_links:
                    href = pl["href"]
                    page_match = re.search(r"[?&]page=(\d+)", href)
                    if page_match:
                        max_page = max(max_page, int(page_match.group(1)))
                    elif href in ("javascript:void(0)", "javascript:;", "#", ""):
                        is_js_pager = True
                    # Extract page number from link text (e.g. " 3 ")
                    text = pl.get_text(strip=True)
                    if text.isdigit():
                        max_page = max(max_page, int(text))
                    # Extract from aria-label (e.g. "page 5")
                    aria = pl.get("aria-label", "")
                    aria_match = re.search(r"page\s+(\d+)", aria, re.I)
                    if aria_match:
                        max_page = max(max_page, int(aria_match.group(1)))
                pag_type = "js_pagination" if is_js_pager else "pager_widget"
                recon.pagination = {
                    "type": pag_type,
                    "max_page": max_page,
                    "page_links_count": len(page_links),
                }
                print(f"  Pagination: {pag_type}, up to page {max_page}")
                return

        # Check for "load more" buttons (AJAX pagination)
        load_more = soup.find(["a", "button"],
                              string=re.compile(r"load more|show more|next", re.I))
        if load_more:
            href = load_more.get("href", "")
            recon.pagination = {
                "type": "load_more",
                "element": load_more.name,
                "text": load_more.get_text(strip=True),
                "href": href,
            }
            print(f"  Pagination: 'load more' button found")
            return

        # Query param scan: check all links for ?page=N, ?p=N, ?start=N, ?offset=N
        page_params = re.compile(r"[?&](page|p|start|offset)=(\d+)")
        page_numbers = set()
        for a in soup.find_all("a", href=True):
            for m in page_params.finditer(a["href"]):
                page_numbers.add((m.group(1), int(m.group(2))))
        if len(page_numbers) >= 2:
            param_name = Counter(p for p, _ in page_numbers).most_common(1)[0][0]
            max_val = max(n for p, n in page_numbers if p == param_name)
            recon.pagination = {
                "type": "query_param",
                "page_param": param_name,
                "max_value": max_val,
                "distinct_pages": len(page_numbers),
            }
            print(f"  Pagination: query param '{param_name}', max={max_val}")
            return

        # Numbered link sequences: 3+ adjacent <a>/<button> with sequential
        # integer text (1, 2, 3...) — works even without a wrapper class
        all_clickable = soup.find_all(["a", "button"])
        run_start = None
        run_count = 0
        last_num = None
        for el in all_clickable:
            txt = el.get_text(strip=True)
            if txt.isdigit():
                num = int(txt)
                if last_num is not None and num == last_num + 1:
                    run_count += 1
                else:
                    run_start = num
                    run_count = 1
                last_num = num
            else:
                if run_count >= 3:
                    break
                run_start = None
                run_count = 0
                last_num = None
        if run_count >= 3:
            recon.pagination = {
                "type": "numbered_sequence",
                "start": run_start,
                "length": run_count,
            }
            print(f"  Pagination: numbered link sequence ({run_start}..{run_start + run_count - 1})")
            return

        # JS pagination signals: links with href="javascript:void(0)" or "#"
        # that have page-related text, aria-labels, or data attributes
        js_page_re = re.compile(r"next|prev|page|first|last|\d+", re.I)
        js_page_links = []
        for el in soup.find_all(["a", "button"]):
            href = el.get("href", "")
            if href not in ("javascript:void(0)", "javascript:;", "#", ""):
                continue
            text = el.get_text(strip=True)
            aria = el.get("aria-label", "")
            if js_page_re.search(text) or js_page_re.search(aria):
                js_page_links.append(text or aria)
        if len(js_page_links) >= 3:
            recon.pagination = {
                "type": "js_pagination",
                "signals": js_page_links[:10],
                "count": len(js_page_links),
            }
            print(f"  Pagination: JS-only pagination detected ({len(js_page_links)} controls)")

    def _analyse_link_patterns(self, all_links, recon: ReconReport):
        """Group internal links by URL path prefix to identify document patterns."""
        # Count links by path prefix (first 2-3 segments)
        prefix_counter = Counter()
        prefix_samples = {}

        for href, full_url, text, loc_type in all_links:
            if loc_type != "internal":
                continue
            parsed = urlparse(full_url)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(parts) < 2:
                continue

            # Use first 2 path segments as prefix
            prefix = "/" + "/".join(parts[:2]) + "/"
            prefix_counter[prefix] += 1
            if prefix not in prefix_samples:
                prefix_samples[prefix] = []
            if len(prefix_samples[prefix]) < 5:
                prefix_samples[prefix].append(full_url)

        # Filter out patterns that match the landing page URL itself
        # (these are self-references, filters, and nav links, not document links)
        landing_path = urlparse(recon.landing_url).path.rstrip("/") + "/"
        candidates = []
        for prefix, count in prefix_counter.most_common(15):
            # Skip if this prefix IS the listing page
            if landing_path.startswith(prefix) or prefix.startswith(landing_path):
                continue
            # Skip obvious non-document paths
            if any(nav in prefix for nav in [
                "/about/", "/contact", "/careers/", "/search/",
                "/login/", "/privacy/", "/accessibility/",
            ]):
                continue
            if count >= 3:
                candidates.append((prefix, count, prefix_samples[prefix]))

        recon.document_link_candidates = candidates
        if candidates:
            print(f"  Document link patterns:")
            for prefix, count, _ in candidates[:5]:
                print(f"    {prefix}: {count} links")

    def _find_item_count(self, soup, recon: ReconReport):
        """Look for visible item/result counts on the page."""
        # Common patterns: "Showing 1-20 of 1,452", "1,452 results", etc.
        page_text = soup.get_text()
        patterns = [
            r"(\d[\d,]+)\s+(?:results?|items?|documents?|reports?|records?)",
            r"(?:of|total)\s+(\d[\d,]+)",
            r"(?:showing|displaying)\s+\d+\s*[-–]\s*\d+\s+of\s+(\d[\d,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                count_str = match.group(1).replace(",", "")
                count = int(count_str)
                if count > 10:  # Ignore tiny numbers
                    recon.item_count_hint = count
                    print(f"  Item count hint: {count}")
                    break

    def _check_manual_files(self, recon: ReconReport):
        """Check for CSV/JSON files manually placed in the corpus directory.

        These are files the human has downloaded from export buttons,
        data portals, or other sources that the scraper can't access
        automatically (JavaScript triggers, login-gated downloads, etc.).
        """
        manual_dir = self.corpus_dir
        if not manual_dir.exists():
            return

        for f in sorted(manual_dir.iterdir()):
            if f.suffix.lower() in (".csv", ".json", ".xlsx") and f.stat().st_size > 0:
                # Skip internal state files
                if f.name.startswith("."):
                    continue
                recon.manual_files_found.append(f.name)

        if recon.manual_files_found:
            print(f"  Manual files in corpus dir: {recon.manual_files_found}")

    def _try_headless_render(self, recon: ReconReport, api_only: bool = False):
        """Render the landing page with a headless browser.

        When api_only=False (default): full headless render for JS-shell
        pages. Returns a BeautifulSoup of the combined rendered DOM.

        When api_only=True: only intercepts network traffic to discover
        JSON APIs. Skips pagination click-through and DOM re-analysis.
        Returns None (static analysis already done).

        Also intercepts XHR/fetch responses to discover JSON APIs that
        the frontend consumes. If found, the structured API data is
        stored on recon.api_endpoints — far richer than scraping HTML.
        """
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            print("  Headless rendering unavailable (playwright not installed)")
            return None

        if api_only:
            print(f"  Hybrid page with JS features — running headless for API interception...")
        else:
            print(f"  Static page appears to be a JS shell — trying headless render...")

        # Collect intercepted JSON API responses
        # Key: base URL (without pagination params) → accumulated hits
        api_responses: list[dict] = []
        api_accumulator: dict[str, list] = {}  # base_url → list of hit lists

        # Capture POST request bodies for API replay
        request_bodies: dict[str, str] = {}  # url → post_data

        def _on_request(request):
            if request.method == "POST" and request.post_data:
                request_bodies[request.url] = request.post_data

        def _on_response(response):
            """Capture JSON responses that look like document listings."""
            url = response.url
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type and "javascript" not in content_type:
                return
            if response.status != 200:
                return
            # Skip common non-data endpoints
            if any(skip in url for skip in (
                "analytics", "tracking", "gtm", "google", "facebook",
                "hotjar", "sentry", "chunk", "webpack",
                "fonts", "icons", "manifest",
            )):
                return
            try:
                body = response.json()
            except Exception:
                return
            # Attach captured POST body if present
            post_data = request_bodies.get(url)
            self._analyse_api_response(
                url, body, api_responses, api_accumulator,
                post_data=post_data,
            )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Intercept network requests and responses
                page.on("request", _on_request)
                page.on("response", _on_response)

                page.goto(self.landing_url, wait_until="domcontentloaded",
                          timeout=60000)

                # Wait for JS app to render content — try networkidle
                # first but fall back gracefully if it never settles
                # (common with analytics/telemetry connections)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass  # proceed with whatever has loaded

                # Wait for content to appear
                try:
                    page.wait_for_selector(
                        "article, .listing, .results, [class*='card'], "
                        "[class*='item'], [class*='result'], table tr, "
                        "[class*='search'], [class*='document']",
                        timeout=15000,
                    )
                except Exception:
                    pass

                if not api_only:
                    # If a paginated API was already intercepted on first load,
                    # skip clicking through pages — we'll paginate the API directly
                    api_has_pagination = any(
                        r.get("pagination") and r["pagination"].get("total", 0) > r["record_count"]
                        for r in api_responses
                    )
                    if api_has_pagination:
                        print("  API with pagination detected — skipping page click-through")
                        all_html_parts = [page.content()]
                    else:
                        # Collect HTML from all pages (pagination may replace content)
                        all_html_parts = [page.content()]
                        self._headless_load_all(page, all_html_parts)

                browser.close()

            # Report intercepted APIs
            if api_responses:
                # Sort by record count descending — richest response first
                api_responses.sort(key=lambda x: x["record_count"], reverse=True)
                recon.api_endpoints = api_responses
                best = api_responses[0]
                print(f"  Intercepted {len(api_responses)} JSON API(s)")
                print(f"    Best: {best['record_count']} records, "
                      f"{len(best['fields'])} fields")
                print(f"    Endpoint: {best['url']}")
                print(f"    Fields: {', '.join(best['fields'][:10])}")

            # In api_only mode, we only wanted network interception — no DOM
            if api_only:
                return None

            # Merge all page HTML into one soup
            # Parse each, extract just the body links and content
            combined_links = set()
            first_soup = None
            for html_part in all_html_parts:
                soup = BeautifulSoup(html_part, "html.parser")
                if first_soup is None:
                    first_soup = soup
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    text = a.get_text(strip=True)[:100]
                    combined_links.add((href, text))

            if not first_soup:
                return None

            # Inject all discovered links into the first soup so
            # downstream analysis sees the complete set
            body = first_soup.find("body") or first_soup
            for href, text in combined_links:
                if not body.find("a", href=href):
                    new_a = first_soup.new_tag("a", href=href)
                    new_a.string = text
                    body.append(new_a)

            total_links = len(first_soup.find_all("a", href=True))
            print(f"  Headless render: {total_links} links across "
                  f"{len(all_html_parts)} pages")

            if total_links <= len(recon.internal_links) + len(recon.external_links):
                print("  Headless render did not yield more links than static — skipping")
                return None

            # Update page title
            h1 = first_soup.find("h1")
            if h1:
                recon.page_title = h1.get_text(strip=True)

            return first_soup

        except Exception as e:
            print(f"  Headless rendering failed: {e}")
            return None

    def _analyse_api_response(
        self, url: str, body, results: list[dict],
        accumulator: dict[str, list] | None = None,
        post_data: str | None = None,
    ):
        """Check if a JSON response looks like a document listing API.

        Heuristics:
        - Response contains an array of objects (the document list)
        - Each object has fields that look like document metadata
          (title, url/href/link, date, description, type, etc.)
        - Array has at least 5 items (not a config/nav endpoint)

        When accumulator is provided, hits from the same base URL are
        merged across paginated calls (e.g. Algolia search returns
        20 hits per page, but headless rendering clicks through all pages).
        """
        # Find the array — it might be the root, nested under a key,
        # or inside a search-results wrapper (e.g. Algolia: {results: [{hits: [...]}]})
        items = None
        pagination_info = {}

        if isinstance(body, list) and len(body) >= 5:
            items = body
        elif isinstance(body, dict):
            # Check for search-engine response patterns first
            # Algolia: {"results": [{"hits": [...], "nbHits": N, ...}, ...]}
            # Elasticsearch: {"hits": {"hits": [...]}}
            items, pagination_info = self._extract_search_hits(body)

            if items is None:
                # Fall back to generic: find the largest array value
                best_key = None
                best_len = 0
                for key, val in body.items():
                    if isinstance(val, list) and len(val) > best_len:
                        best_key = key
                        best_len = len(val)
                    # Capture pagination metadata
                    if isinstance(val, int) and key.lower() in (
                        "total", "count", "total_count", "totalcount",
                        "total_results", "totalresults", "total_items",
                    ):
                        pagination_info["total"] = val
                    elif isinstance(val, int) and key.lower() in (
                        "page", "current_page", "page_number",
                    ):
                        pagination_info["current_page"] = val
                    elif isinstance(val, int) and key.lower() in (
                        "per_page", "page_size", "pagesize", "limit",
                    ):
                        pagination_info["per_page"] = val
                    elif isinstance(val, (str, int)) and key.lower() in (
                        "next", "next_page", "next_url",
                    ):
                        pagination_info["next"] = val

                if best_key and best_len >= 5:
                    items = body[best_key]

        if items is None:
            return

        # Verify items are objects with document-like fields
        if not all(isinstance(item, dict) for item in items[:10]):
            return

        # Collect all field names across the first few items
        all_fields = set()
        for item in items[:20]:
            all_fields.update(item.keys())

        # Heuristic: must have at least one URL-like and one title-like field
        url_fields = {f for f in all_fields if any(
            kw in f.lower() for kw in ("url", "href", "link", "path", "slug")
        )}
        title_fields = {f for f in all_fields if any(
            kw in f.lower() for kw in ("title", "name", "heading", "label")
        )}

        if not url_fields and not title_fields:
            return

        # Accumulate hits from the same base URL across paginated calls
        # Use URL path (without query params) as the grouping key
        base_url = url.split("?")[0]

        if accumulator is not None and base_url in accumulator:
            # Merge new items into existing accumulation
            existing = accumulator[base_url]
            # Deduplicate by objectID or by full dict comparison
            seen_ids = set()
            for item in existing:
                oid = item.get("objectID") or item.get("id") or item.get("_id")
                if oid is not None:
                    seen_ids.add(oid)

            for item in items:
                oid = item.get("objectID") or item.get("id") or item.get("_id")
                if oid is not None and oid in seen_ids:
                    continue
                existing.append(item)
                if oid is not None:
                    seen_ids.add(oid)

            # Update the existing result entry
            for r in results:
                if r["url"].split("?")[0] == base_url:
                    r["record_count"] = len(existing)
                    r["_all_records"] = existing
                    break
            return

        # First time seeing this endpoint
        all_items = list(items)
        if accumulator is not None:
            accumulator[base_url] = all_items

        result = {
            "url": url,
            "post_data": post_data,
            "record_count": len(all_items),
            "fields": sorted(all_fields),
            "url_fields": sorted(url_fields),
            "title_fields": sorted(title_fields),
            "pagination": pagination_info or None,
            "sample_records": [dict(item) for item in all_items[:3]],
            "_all_records": all_items,  # keep full data for discovery
        }
        results.append(result)

    @staticmethod
    def _extract_search_hits(body: dict) -> tuple[list | None, dict]:
        """Extract document hits from search-engine response formats.

        Supports:
        - Algolia multi-query: {"results": [{"hits": [...], "nbHits": N}]}
        - Algolia single-query: {"hits": [...], "nbHits": N}
        - Elasticsearch: {"hits": {"total": N, "hits": [{"_source": {...}}]}}

        Returns (items, pagination_info) or (None, {}) if no match.
        """
        pagination_info = {}

        # Algolia multi-query: {"results": [{...}, {...}, ...]}
        if "results" in body and isinstance(body["results"], list):
            # Pick the result set with the most hits
            best_result = None
            best_count = 0
            for r in body["results"]:
                if not isinstance(r, dict):
                    continue
                hits = r.get("hits", [])
                nb_hits = r.get("nbHits", 0)
                if isinstance(hits, list) and len(hits) > 0 and nb_hits > best_count:
                    best_result = r
                    best_count = nb_hits

            if best_result:
                items = best_result["hits"]
                pagination_info = {
                    "total": best_result.get("nbHits", len(items)),
                    "per_page": best_result.get("hitsPerPage", len(items)),
                    "current_page": best_result.get("page", 0),
                    "total_pages": best_result.get("nbPages"),
                    "search_engine": "algolia",
                    "index": best_result.get("index"),
                }
                return items, pagination_info

        # Algolia single-query: {"hits": [...], "nbHits": N}
        if "hits" in body and "nbHits" in body:
            items = body["hits"]
            if isinstance(items, list) and len(items) > 0:
                pagination_info = {
                    "total": body.get("nbHits", len(items)),
                    "per_page": body.get("hitsPerPage", len(items)),
                    "current_page": body.get("page", 0),
                    "total_pages": body.get("nbPages"),
                    "search_engine": "algolia",
                    "index": body.get("index"),
                }
                return items, pagination_info

        # Elasticsearch: {"hits": {"total": N, "hits": [{"_source": {}}]}}
        if "hits" in body and isinstance(body["hits"], dict):
            inner = body["hits"]
            es_hits = inner.get("hits", [])
            if isinstance(es_hits, list) and es_hits:
                # Unwrap _source if present
                items = [
                    h.get("_source", h) if isinstance(h, dict) else h
                    for h in es_hits
                ]
                total = inner.get("total")
                if isinstance(total, dict):
                    total = total.get("value", len(items))
                pagination_info = {
                    "total": total or len(items),
                    "search_engine": "elasticsearch",
                }
                return items, pagination_info

        return None, {}

    def _headless_load_all(self, page, html_parts: list) -> bool:
        """Click through pagination to load all content.

        Captures the rendered HTML after each page transition into
        html_parts, so the caller can merge links from all pages
        (important when pagination replaces content rather than appending).

        Handles three patterns:
        1. Numbered page buttons (1, 2, 3, ...) — clicks each in sequence
        2. "Next" buttons — clicks until exhausted
        3. "Load more" buttons — clicks until exhausted (appends, no capture needed)

        Returns True if all content was loaded, False if we hit the safety cap.
        """
        max_clicks = 200  # safety cap
        clicks = 0

        # Strategy 1: Numbered page buttons (e.g. PC uses buttons "1", "2", ... "7")
        # These are dynamic — clicking one re-renders the button set to show
        # a sliding window of page numbers. We navigate forward by always
        # clicking the highest visible page number until no new pages appear.
        numbered = self._find_numbered_buttons(page)

        if len(numbered) >= 3:
            print(f"  Headless: found numbered pagination "
                  f"(buttons: {[n for n, _ in numbered]})")
            seen_pages = {1}  # we already captured page 1
            current_page = 1

            while clicks < max_clicks:
                # Find the next page to click (smallest unseen)
                target = None
                for page_num, btn in numbered:
                    if page_num not in seen_pages and page_num > current_page:
                        target = (page_num, btn)
                        break

                if target is None:
                    break

                page_num, btn = target
                try:
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    html_parts.append(page.content())
                    seen_pages.add(page_num)
                    current_page = page_num
                    clicks += 1

                    if clicks % 10 == 0:
                        print(f"    ... page {current_page} "
                              f"({clicks} clicks)", flush=True)

                    # Re-scan — the button set changes after each click
                    numbered = self._find_numbered_buttons(page)
                except Exception:
                    break

            if clicks > 0:
                print(f"  Headless: clicked through {clicks} numbered pages "
                      f"(reached page {current_page})")
            return clicks < max_clicks

        # Strategy 2: "Next" button (replaces content — capture each page)
        while clicks < max_clicks:
            next_btn = page.query_selector(
                "a[rel='next'], "
                "a:has-text('Next'), "
                "button:has-text('Next'), "
                "[aria-label='Next page'], "
                "[aria-label*='next']"
            )
            if next_btn and next_btn.is_visible():
                try:
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    html_parts.append(page.content())
                    clicks += 1
                    if clicks % 20 == 0:
                        print(f"    ... loaded {clicks} pages", flush=True)
                    continue
                except Exception:
                    break
            break

        # Strategy 3: "Load more" button (appends content — just wait for it)
        while clicks < max_clicks:
            load_more = page.query_selector(
                "button:has-text('Load more'), "
                "a:has-text('Load more'), "
                "[class*='load-more']"
            )
            if load_more and load_more.is_visible():
                try:
                    load_more.click()
                    page.wait_for_timeout(2000)
                    clicks += 1
                    if clicks % 20 == 0:
                        print(f"    ... loaded {clicks} pages", flush=True)
                    continue
                except Exception:
                    break
            break

        # Capture final state after load-more clicks (all content in one DOM)
        if clicks > 0:
            html_parts[-1] = page.content()  # update last capture
            print(f"  Headless: clicked through {clicks} pages to load all content")
        return clicks < max_clicks

    @staticmethod
    def _find_numbered_buttons(page) -> list[tuple[int, object]]:
        """Find visible buttons with pure numeric text (page numbers)."""
        numbered = []
        for btn in page.query_selector_all("button"):
            text = btn.text_content().strip()
            if text.isdigit() and btn.is_visible():
                numbered.append((int(text), btn))
        numbered.sort(key=lambda x: x[0])
        return numbered

    def _probe_api_docs(self, soup, recon: ReconReport):
        """Probe for OpenAPI/Swagger API documentation.

        Many government sites expose a public API with Swagger docs at
        standard locations. Finding this is far more reliable than
        headless browser interception — gives us the full API surface,
        request/response schemas, and download URL patterns.

        Discovery strategy:
        1. Scan static HTML for API base URLs (links to /api/, /public-api/, etc.)
        2. Probe standard Swagger/OpenAPI paths on each candidate base
        3. If a spec is found, parse endpoints and probe the search/list
           endpoint to populate recon.api_endpoints directly
        """
        # Collect candidate API bases from the page HTML
        html_str = str(soup) if soup else ""
        candidates: set[str] = set()

        # Look for links/references to API paths
        for match in re.finditer(
            r'(https?://[^"\s<>]+?/(?:public-api|api|rest|v[12]))/?\b',
            html_str,
        ):
            base = match.group(1).rstrip("/")
            candidates.add(base)

        # Also check for script src pointing to a different subdomain
        # (common pattern: app at www.example.com, API at api.example.com)
        for script in (soup.find_all("script", src=True) if soup else []):
            src = script["src"]
            if src.startswith("//"):
                src = f"https:{src}"
            parsed = urlparse(src)
            if parsed.netloc and parsed.netloc != self.landing_parsed.netloc:
                # Try this host as an API base
                api_base = f"https://{parsed.netloc}"
                candidates.add(api_base)
                candidates.add(f"{api_base}/api")
                candidates.add(f"{api_base}/public-api")

        # Also try the landing site itself
        candidates.add(f"{self.site_base}/api")
        candidates.add(f"{self.site_base}/public-api")

        # Try common API subdomains (api.example.com, otd.example.com, etc.)
        # Many government sites host the API on a separate subdomain
        domain_parts = self.landing_parsed.netloc.split(".")
        if len(domain_parts) >= 2:
            # Find the registrable domain (e.g. "aph.gov.au" from "www.aph.gov.au")
            # For .gov.au, .org.au, .com.au etc. the SLD is 3 parts
            tld2 = ".".join(domain_parts[-2:])  # "gov.au"
            if tld2 in ("gov.au", "org.au", "com.au", "edu.au", "ac.uk",
                         "co.uk", "org.uk", "gov.uk", "go.jp", "or.jp"):
                # 3-part TLD: need org.tld2
                base_domain = ".".join(domain_parts[-3:]) if len(domain_parts) >= 3 else tld2
            else:
                base_domain = tld2
            for prefix in ("api", "public-api", "otd", "data", "rest"):
                candidates.add(f"https://{prefix}.{base_domain}")
                candidates.add(f"https://{prefix}.{base_domain}/api")
                candidates.add(f"https://{prefix}.{base_domain}/public-api")

        if not candidates:
            return

        # Probe standard Swagger/OpenAPI paths
        swagger_paths = [
            "swagger/v1/swagger.json",
            "swagger.json",
            ".well-known/openapi.json",
            "openapi.json",
            "api-docs",
        ]

        # Collect all valid specs — prefer "public" APIs over internal ones
        found_specs: list[tuple[dict, str]] = []
        for base in candidates:
            for swagger_path in swagger_paths:
                probe_url = f"{base}/{swagger_path}"
                try:
                    resp = self.session.get(probe_url, timeout=10)
                    if resp.status_code != 200:
                        continue
                    ct = resp.headers.get("content-type", "")
                    if "json" not in ct and "yaml" not in ct:
                        continue
                    doc = resp.json()
                    if ("paths" in doc and
                            ("info" in doc or "swagger" in doc or "openapi" in doc)):
                        found_specs.append((doc, probe_url))
                except Exception:
                    continue

        if not found_specs:
            return

        # Prefer specs with "public" in the URL or title
        def _public_score(item):
            doc, url = item
            title = doc.get("info", {}).get("title", "").lower()
            score = 0
            if "public" in url.lower():
                score += 2
            if "public" in title:
                score += 1
            if "internal" in title:
                score -= 2
            return -score  # lower = better

        found_specs.sort(key=_public_score)
        spec_doc, spec_url = found_specs[0]

        # Parse the spec
        info = spec_doc.get("info", {})
        title = info.get("title", "Unknown API")
        version = info.get("version", "?")
        print(f"  OpenAPI spec found: {title} v{version}")
        print(f"    {spec_url}")

        endpoints = []
        search_endpoint = None
        file_endpoint = None
        for path, methods in spec_doc.get("paths", {}).items():
            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue
                summary = (details.get("summary", "")
                           or details.get("operationId", ""))
                ep = {"method": method.upper(), "path": path,
                      "summary": summary}
                endpoints.append(ep)
                print(f"    {method.upper():6s} {path}  — {summary}")

                # Identify the search/list endpoint
                path_lower = path.lower()
                if (method.lower() == "post" and "search" in path_lower):
                    search_endpoint = ep
                elif (method.lower() == "get" and not search_endpoint
                      and any(kw in path_lower
                              for kw in ("list", "documents", "items"))
                      and "{" not in path):
                    search_endpoint = ep

                # Identify file download pattern
                if ("file" in path_lower and "{" in path
                        and method.lower() == "get"):
                    file_endpoint = ep

        recon.openapi_spec = {
            "spec_url": spec_url,
            "title": title,
            "version": version,
            "endpoints": endpoints,
            "search_endpoint": search_endpoint,
            "file_endpoint": file_endpoint,
            "api_base": re.split(r"/swagger[/.]", spec_url)[0]
                        if re.search(r"/swagger[/.]", spec_url)
                        else spec_url.rsplit("/", 1)[0],
            "_spec": spec_doc,
        }

        # If we found a search endpoint, probe it to populate api_endpoints
        if search_endpoint:
            api_base = recon.openapi_spec["api_base"]
            search_url = f"{api_base}{search_endpoint['path']}"
            self._probe_openapi_search(search_url, search_endpoint, spec_doc,
                                       recon)

    def _probe_openapi_search(self, search_url: str, endpoint: dict,
                              spec_doc: dict, recon: ReconReport):
        """Probe a discovered search endpoint to get sample data.

        Constructs a minimal request from the OpenAPI schema, fires it,
        and populates recon.api_endpoints with the result — same format
        as headless API interception, so downstream discovery works
        identically.
        """
        method = endpoint["method"]

        # Build a minimal request body from the schema
        body = None
        schemas = spec_doc.get("components", {}).get("schemas", {})

        if method == "POST":
            # Find the request body schema
            path_spec = spec_doc["paths"].get(endpoint["path"], {})
            post_spec = path_spec.get("post", {})
            req_body = post_spec.get("requestBody", {})
            content = req_body.get("content", {})
            json_spec = content.get("application/json", {})
            schema_ref = json_spec.get("schema", {}).get("$ref", "")

            if schema_ref:
                schema_name = schema_ref.split("/")[-1]
                schema = schemas.get(schema_name, {})

                # Collect all properties — resolve allOf references
                all_props = dict(schema.get("properties", {}))
                for sub in schema.get("allOf", []):
                    if "$ref" in sub:
                        parent_name = sub["$ref"].split("/")[-1]
                        parent = schemas.get(parent_name, {})
                        all_props.update(parent.get("properties", {}))
                    if "properties" in sub:
                        all_props.update(sub["properties"])

                body = {}
                for prop, details in all_props.items():
                    # Resolve $ref to get the actual type
                    if "$ref" in details and not details.get("type"):
                        ref_name = details["$ref"].split("/")[-1]
                        ref_schema = schemas.get(ref_name, {})
                        # Enum schemas have type + enum values
                        if ref_schema.get("type") == "string":
                            details = dict(details)
                            details["type"] = "string"
                            if "enum" in ref_schema:
                                details["_enum"] = ref_schema["enum"]

                    prop_type = details.get("type", "")
                    nullable = details.get("nullable", False)
                    pl = prop.lower()
                    if prop_type == "string":
                        enum_vals = details.get("_enum", [])
                        if "date" in pl and nullable:
                            body[prop] = None
                        elif "direction" in pl:
                            # Prefer "descending" if in enum, else first value
                            body[prop] = next(
                                (v for v in enum_vals
                                 if "desc" in v.lower()),
                                enum_vals[0] if enum_vals else "descending")
                        elif "sort" in pl or "order" in pl:
                            body[prop] = next(
                                (v for v in enum_vals
                                 if "relev" in v.lower()),
                                enum_vals[0] if enum_vals else "relevance")
                        else:
                            body[prop] = "" if not nullable else None
                    elif prop_type == "integer":
                        if "page" in pl and "size" not in pl:
                            body[prop] = 1
                        elif "size" in pl or "limit" in pl:
                            body[prop] = 20
                        else:
                            body[prop] = 0
                    elif prop_type == "boolean":
                        body[prop] = True
                    elif prop_type == "array":
                        body[prop] = []
                    elif nullable:
                        body[prop] = None
                    else:
                        body[prop] = None

        # Try the request — if schema-based body fails (400), extract
        # required field names from the error response and retry
        data = None
        try:
            if method == "POST":
                if body is None:
                    body = {}
                resp = self.session.post(search_url, json=body, timeout=30)

                # If 400, the error often lists required fields — learn from it
                if resp.status_code == 400:
                    try:
                        err = resp.json()
                        errors = err.get("errors", {})
                        if isinstance(errors, dict):
                            for field, msgs in errors.items():
                                if field not in body:
                                    # Guess type from field name
                                    fl = field.lower()
                                    if any(kw in fl for kw in
                                           ("page",)) and "size" not in fl:
                                        body[field] = 1
                                    elif "size" in fl or "limit" in fl:
                                        body[field] = 20
                                    elif any(kw in fl for kw in (
                                        "table", "include", "is", "has",
                                        "enable", "active",
                                    )):
                                        body[field] = True
                                    elif "direction" in fl:
                                        body[field] = "descending"
                                    elif any(kw in fl for kw in (
                                        "sort", "order",
                                    )):
                                        body[field] = "relevance"
                                    else:
                                        body[field] = ""
                            # Retry with enriched body
                            resp = self.session.post(
                                search_url, json=body, timeout=30)
                    except Exception:
                        pass

                if resp.status_code != 200:
                    print(f"    Search probe: {resp.status_code}")
                    return
                data = resp.json()
            else:
                resp = self.session.get(search_url, timeout=30)
                if resp.status_code != 200:
                    print(f"    Search probe: {resp.status_code}")
                    return
                data = resp.json()
        except Exception as e:
            print(f"    Search probe failed: {e}")
            return

        # Parse the response using the same analyser as headless interception
        api_responses: list[dict] = []
        self._analyse_api_response(
            search_url, data, api_responses,
            post_data=json.dumps(body) if body else None,
        )

        if api_responses:
            for r in api_responses:
                r["source"] = "openapi"
            api_responses.sort(key=lambda x: x["record_count"], reverse=True)
            recon.api_endpoints = api_responses
            best = api_responses[0]
            print(f"    Search probe: {best['record_count']} records, "
                  f"{len(best['fields'])} fields")

    def _check_wp_api(self, soup, recon: ReconReport):
        """Detect WordPress REST API and probe for a matching custom post type.

        WordPress sites expose /wp-json/wp/v2/types which lists all post types.
        If the landing path matches a post type's slug, that API endpoint provides
        structured data with pagination — richer than CSV export or HTML scraping.
        """
        if soup is None:
            return

        # Quick check: is this a WordPress site?
        html = str(soup)
        if "/wp-content/" not in html and "/wp-json/" not in html:
            return

        # Probe the types endpoint
        types_url = f"{self.site_base}/wp-json/wp/v2/types"
        print(f"  WordPress detected — probing REST API...")
        types_text = self.fetch(types_url)
        if not types_text:
            print(f"  WP REST API not accessible")
            return

        try:
            types_data = json.loads(types_text)
        except (json.JSONDecodeError, ValueError):
            return

        # Find post type whose slug matches the landing URL path
        landing_path = self.landing_parsed.path.strip("/")
        # e.g. "knowledge-bank" from "/knowledge-bank/"
        path_segments = [s for s in landing_path.split("/") if s]

        best_match = None
        for slug, info in types_data.items():
            if not isinstance(info, dict):
                continue
            rest_base = info.get("rest_base", slug)
            # Check if any path segment matches the post type slug or rest_base
            if slug in path_segments or rest_base in path_segments:
                best_match = (slug, rest_base, info.get("name", slug))
                break

        if not best_match:
            print(f"  WP REST API: no post type matches landing path '{landing_path}'")
            return

        slug, rest_base, name = best_match
        # Probe the collection endpoint to get total count
        api_url = f"{self.site_base}/wp-json/wp/v2/{rest_base}"
        probe = self.head(api_url + "?per_page=1")
        if not probe or probe["status"] != 200:
            # HEAD might not return WP headers; try a GET
            probe_text = self.fetch(api_url + "?per_page=1")
            if not probe_text:
                return

        # Get pagination headers via a minimal GET
        import requests
        try:
            resp = self.session.get(api_url + "?per_page=1", timeout=30)
            total = int(resp.headers.get("X-WP-Total", 0))
            total_pages = int(resp.headers.get("X-WP-TotalPages", 0))
        except Exception:
            total = 0
            total_pages = 0

        if total == 0:
            print(f"  WP REST API: {name} endpoint exists but returned 0 items")
            return

        # Get a sample record to check available fields
        sample_text = self.fetch(api_url + "?per_page=1")
        sample_fields = []
        has_download = False
        if sample_text:
            try:
                sample = json.loads(sample_text)
                if isinstance(sample, list) and sample:
                    sample_fields = sorted(sample[0].keys())
                    # Check for ACF download field
                    acf = sample[0].get("acf", {})
                    if isinstance(acf, dict) and acf.get("download"):
                        has_download = True
            except (json.JSONDecodeError, ValueError):
                pass

        recon.wp_api = {
            "post_type": slug,
            "rest_base": rest_base,
            "name": name,
            "api_url": api_url,
            "total": total,
            "total_pages_at_100": (total // 100) + 1,
            "fields": sample_fields,
            "has_acf_download": has_download,
        }
        print(f"  WP REST API: {name} ({slug}) — {total} items, "
              f"{len(sample_fields)} fields")
        if has_download:
            print(f"    ACF download field detected — PDFs available via API")

    def _check_sitemap(self, recon: ReconReport):
        """Check for a sitemap.xml and extract URLs matching the landing path.

        Sitemaps are a reliable discovery mechanism when the listing page is
        JS-rendered or otherwise inaccessible to static scraping. We filter
        to URLs whose path starts with the landing page's path prefix, then
        keep only depth-1 pages (the main document pages, not sub-pages).
        """
        import xml.etree.ElementTree as ET

        sitemap_url = f"{self.site_base}/sitemap.xml"
        print(f"  Checking sitemap: {sitemap_url}")
        sitemap_text = self.fetch(sitemap_url)
        if not sitemap_text:
            print("  No sitemap found")
            return

        try:
            root = ET.fromstring(sitemap_text)
        except ET.ParseError:
            print("  Failed to parse sitemap XML")
            return

        # Handle XML namespace
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        all_urls = []
        for url_elem in root.findall('.//ns:url', ns):
            loc = url_elem.find('ns:loc', ns)
            if loc is not None and loc.text:
                all_urls.append(loc.text.strip())

        if not all_urls:
            # Try without namespace (some sitemaps omit it)
            for url_elem in root.findall('.//url'):
                loc = url_elem.find('loc')
                if loc is not None and loc.text:
                    all_urls.append(loc.text.strip())

        print(f"  Sitemap total URLs: {len(all_urls)}")

        # Filter to URLs under the landing page path prefix
        landing_path = self.landing_parsed.path.rstrip("/")
        matching = []
        for url in all_urls:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            if path.startswith(landing_path) and path != landing_path:
                matching.append(url)

        if not matching:
            print("  No sitemap URLs match landing path prefix")
            return

        # Keep only depth-1 pages (direct children of the landing path)
        # e.g. /inquiries-and-research/aged-care but not
        #      /inquiries-and-research/aged-care/report
        landing_depth = len([p for p in landing_path.split("/") if p])
        depth1 = []
        for url in matching:
            parsed = urlparse(url)
            parts = [p for p in parsed.path.rstrip("/").split("/") if p]
            if len(parts) == landing_depth + 1:
                depth1.append(url)

        recon.sitemap_urls = depth1
        print(f"  Sitemap URLs matching landing path: {len(matching)} total, "
              f"{len(depth1)} depth-1 (document pages)")

    def _check_robots_txt(self):
        """Check robots.txt for crawl-delay and apply if higher than configured."""
        from urllib.robotparser import RobotFileParser

        robots_url = f"{self.site_base}/robots.txt"
        robots_text = self.fetch(robots_url)
        if not robots_text:
            return

        rp = RobotFileParser()
        rp.parse(robots_text.splitlines())

        delay = rp.crawl_delay("*")
        if delay is not None and delay > self.rate_limit:
            old_rate = self.rate_limit
            self.rate_limit = float(delay)
            print(f"  robots.txt crawl-delay: {delay}s "
                  f"(overrides configured {old_rate}s)")
        elif delay is not None:
            print(f"  robots.txt crawl-delay: {delay}s "
                  f"(configured {self.rate_limit}s is higher — keeping)")

        # Check if our landing path is disallowed
        if not rp.can_fetch("*", self.landing_url):
            print(f"  WARNING: robots.txt disallows {self.landing_url}")

    def _generate_human_actions(self, recon: ReconReport):
        """Based on what recon found, generate actionable items for the human.

        Most JS-dependent features are now handled by headless browser,
        so human actions are only needed for truly unsupported patterns.
        """
        # Check if pagination is JavaScript-only
        if recon.pagination:
            pag_type = recon.pagination.get("type", "")
            pag_href = recon.pagination.get("href", "")
            if pag_type == "load_more" and (not pag_href or pag_href == "#"):
                recon.js_dependent = True
                # Only add action if we don't already have an export action
                if not recon.human_actions:
                    recon.human_actions.append({
                        "action": (
                            "Document listing uses JavaScript-only pagination "
                            "(Load More button). Check if the site has a "
                            "CSV/data export, a sitemap, or an API that lists "
                            "all documents. Download and save to corpus directory."
                        ),
                        "reason": (
                            "The scraper cannot follow JavaScript pagination. "
                            "A bulk document list is needed."
                        ),
                        "file_hint": "catalogue_export.csv",
                    })

        # If no automated discovery path is viable, say so clearly
        has_viable_path = (
            recon.manual_files_found
            or (recon.pagination and not recon.js_dependent)
            or recon.sitemap_urls
            or recon.document_link_candidates
            or recon.pdf_links
        )
        if not has_viable_path and not recon.human_actions:
            recon.human_actions.append({
                "action": (
                    "No automated discovery path found. Investigate the site "
                    "manually: look for sitemaps, data exports, API endpoints, "
                    "or alternative listing pages."
                ),
                "reason": (
                    "The landing page has no followable pagination, no export "
                    "mechanisms, and no identifiable document link patterns."
                ),
                "file_hint": "catalogue_export.csv",
            })

        if recon.human_actions:
            print(f"  Human actions needed: {len(recon.human_actions)}")
            for a in recon.human_actions:
                print(f"    - {a['action'][:80]}...")

    # ---- Strategy selection ----

    def _choose_strategy(self) -> str:
        """Based on reconnaissance, decide how to discover documents."""
        if not self._recon:
            self.reconnaissance()

        recon = self._recon

        # Priority 1: Intercepted JSON API (structured data, pagination,
        # file URLs — the richest and most reliable discovery path)
        if recon.api_endpoints:
            best = recon.api_endpoints[0]
            self._chosen_strategy = "api_intercept"
            print(f"\n  Strategy: intercepted API ({best['record_count']} records, "
                  f"{len(best['fields'])} fields)")
            return "api_intercept"

        # Priority 2: WordPress REST API (specific API type detected
        # without headless — already confirmed structured)
        if recon.wp_api:
            wp = recon.wp_api
            self._chosen_strategy = "wp_api"
            print(f"\n  Strategy: WordPress REST API — {wp['name']} "
                  f"({wp['total']} items)")
            return "wp_api"

        # Priority 3: CSV/data export (rich metadata — click via headless)
        csv_exports = [m for m in recon.export_mechanisms
                       if re.search(r"csv|export|data", m["url"], re.I)
                       or re.search(r"csv|export", m["label"], re.I)]
        if csv_exports:
            self._chosen_strategy = "csv_export"
            print(f"\n  Strategy: CSV export via {csv_exports[0]['url']}")
            return "csv_export"

        # Priority 5: Pagination we can follow (not JS-only)
        if recon.pagination:
            pag_type = recon.pagination.get("type", "")
            pag_href = recon.pagination.get("href", "")
            # "load_more" with href="#" is JavaScript-only — can't follow
            if pag_type == "load_more" and (not pag_href or pag_href == "#"):
                print(f"\n  Pagination is JavaScript-only (Load More with href='#') — skipping")
            else:
                self._chosen_strategy = "paginated_listing"
                print(f"\n  Strategy: paginated listing")
                return "paginated_listing"

        # Priority 6: Sitemap-based discovery (when listing is JS-rendered)
        if recon.sitemap_urls:
            self._chosen_strategy = "sitemap"
            print(f"\n  Strategy: sitemap discovery ({len(recon.sitemap_urls)} URLs)")
            return "sitemap"

        # Priority 7: Document link patterns on the landing page
        if recon.document_link_candidates:
            self._chosen_strategy = "link_harvest"
            print(f"\n  Strategy: link harvest from landing page")
            return "link_harvest"

        # Priority 8: Direct PDF links on the landing page
        if recon.pdf_links:
            self._chosen_strategy = "direct_pdfs"
            print(f"\n  Strategy: direct PDF links from landing page")
            return "direct_pdfs"

        # Fallback: manual CSV already in the corpus directory
        if recon.manual_files_found:
            csv_files = [f for f in recon.manual_files_found
                         if f.endswith(".csv")]
            if csv_files:
                self._chosen_strategy = "manual_csv"
                print(f"\n  Strategy: manual CSV file(s): {csv_files}")
                return "manual_csv"

        self._chosen_strategy = "direct_pdfs"
        print(f"\n  Strategy: direct PDF links from landing page (no better option)")
        return "direct_pdfs"

    # ---- Discovery ----

    def discover(self, limit: int | None = None) -> list[DocumentRecord]:
        if not self._recon:
            self.reconnaissance()

        # Check for existing checkpoint from a previous interrupted run
        checkpoint = self._load_checkpoint()
        if checkpoint:
            records = self._records_from_checkpoint(checkpoint)
            if limit and len(records) >= limit:
                self._clear_checkpoint()
                return records[:limit]
            # Resume from where we left off
            self._chosen_strategy = checkpoint["strategy"]
            # TODO: pass checkpoint to individual strategies for page-level resume
            print(f"  Resuming discovery with {len(records)} existing records")

        strategy = self._choose_strategy()

        # Strategy chain with automatic fallback: if the chosen strategy
        # returns no records, try the next strategy down the priority list
        strategy_chain = [
            ("api_intercept", self._discover_via_api),
            ("wp_api", self._discover_via_wp_api),
            ("csv_export", self._discover_via_export),
            ("paginated_listing", self._discover_via_pagination),
            ("sitemap", self._discover_via_sitemap),
            ("link_harvest", self._discover_via_links),
            ("direct_pdfs", self._discover_direct_pdfs),
            ("manual_csv", self._discover_via_manual_csv),
        ]

        # Start from the chosen strategy and fall through on failure
        started = False
        for name, method in strategy_chain:
            if name == strategy:
                started = True
            if not started:
                continue
            records = method(limit)
            if records:
                self._clear_checkpoint()
                return records
            if name == strategy:
                print(f"\n  Strategy '{name}' returned no records — "
                      f"trying next fallback...")

        return []

    def _discover_via_manual_csv(self, limit: int | None) -> list[DocumentRecord]:
        """Use a manually-provided CSV file as the document catalogue.

        The human has downloaded an export (e.g. clicked a JS-triggered export
        button) and placed the CSV in the corpus directory. We auto-detect
        URL and title columns and treat every row as a document.
        """
        recon = self._recon
        csv_files = [f for f in recon.manual_files_found if f.endswith(".csv")]
        if not csv_files:
            return []

        # Use the largest CSV file (most likely to be the full catalogue)
        best_file = None
        best_size = 0
        for name in csv_files:
            path = self.corpus_dir / name
            size = path.stat().st_size
            if size > best_size:
                best_size = size
                best_file = path

        print(f"\n  Loading manual CSV: {best_file.name} ({best_size:,} bytes)")
        with open(best_file, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        if not rows:
            print("  CSV is empty")
            return []

        return self._build_records_from_csv(rows, limit)

        return records

    def _discover_via_wp_api(self, limit: int | None) -> list[DocumentRecord]:
        """Paginate the WordPress REST API to discover all documents.

        WordPress REST API uses per_page + page params with X-WP-Total/
        X-WP-TotalPages headers. Each record contains structured metadata
        and optionally ACF fields with direct download URLs.
        """
        recon = self._recon
        if not recon.wp_api:
            return []

        wp = recon.wp_api
        api_url = wp["api_url"]
        total = wp["total"]
        per_page = 100

        print(f"\n  WP REST API: {api_url}")
        print(f"  Total items: {total}, fetching {per_page}/page...")

        all_items = []
        page = 1
        max_pages = (total // per_page) + 1

        while True:
            url = f"{api_url}?per_page={per_page}&page={page}"
            text = self.fetch(url)
            if not text:
                print(f"    Page {page}: FAILED")
                break

            try:
                items = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                break

            if not isinstance(items, list) or not items:
                break

            all_items.extend(items)
            if page % 5 == 0 or page == 1:
                print(f"    Page {page}/{max_pages}: {len(all_items)}/{total} records")

            if limit and len(all_items) >= limit:
                break
            if len(items) < per_page:
                break
            page += 1

        print(f"  Fetched {len(all_items)} items from WP API")

        # Build records
        records = []
        for item in all_items:
            title = ""
            title_obj = item.get("title")
            if isinstance(title_obj, dict):
                title = title_obj.get("rendered", "")
            elif isinstance(title_obj, str):
                title = title_obj
            # WordPress renders HTML entities in title.rendered
            if title:
                title = html_mod.unescape(title)

            page_url = item.get("link", "")

            # Extract PDF/document URL from ACF download field
            doc_urls = []
            acf = item.get("acf", {})
            if isinstance(acf, dict):
                dl = acf.get("download")
                if isinstance(dl, dict) and dl.get("url"):
                    doc_urls.append(dl["url"])
                # Some sites use a "files" array
                files = acf.get("files")
                if isinstance(files, list):
                    for f in files:
                        if isinstance(f, dict) and f.get("url"):
                            doc_urls.append(f["url"])

            # Build metadata from all non-internal fields
            metadata = {}
            for key in ("date", "modified", "slug", "status", "type"):
                val = item.get(key)
                if val:
                    metadata[key] = str(val)

            # ACF custom fields (flatten one level)
            if isinstance(acf, dict):
                for key, val in acf.items():
                    if key in ("download", "files", "content", "hero_image",
                               "mobile_banner", "tabs", "select_carousel",
                               "after_carousel_content"):
                        continue
                    if val is None or val is False or val == "":
                        continue
                    if isinstance(val, dict):
                        # Nested post object (e.g. project) — extract title
                        nested_title = val.get("post_title", "")
                        if nested_title:
                            metadata[f"acf_{key}"] = nested_title
                    elif isinstance(val, list):
                        metadata[f"acf_{key}"] = json.dumps(val, default=str)
                    else:
                        metadata[f"acf_{key}"] = str(val)

            # Taxonomy terms
            for tax_key in ("technology", "priority", "portfolio"):
                val = item.get(tax_key)
                if val and val != "":
                    metadata[tax_key] = str(val)

            # Primary category if present
            pcat = item.get("primary_category_title")
            if isinstance(pcat, dict) and pcat.get("name"):
                metadata["category"] = pcat["name"]

            if not page_url and not title:
                continue

            records.append(DocumentRecord(
                page_url=page_url,
                doc_urls=doc_urls,
                title=title or page_url.rstrip("/").split("/")[-1],
                metadata=metadata,
            ))

            if limit and len(records) >= limit:
                break

            if len(records) % self._checkpoint_interval == 0 and len(records) > 0:
                self._save_checkpoint("wp_api", records, page)

        print(f"  Records from WP API: {len(records)}")
        if records:
            has_pdf = sum(1 for r in records if r.doc_urls)
            print(f"  With download URLs: {has_pdf}/{len(records)}")
            print(f"  Metadata fields: {list(records[0].metadata.keys())}")

        self._flush_curation_buffer()
        return records

    def _discover_via_export(self, limit: int | None) -> list[DocumentRecord]:
        """Use a discovered export mechanism to get document list + metadata.

        Tries static fetch first. If that returns HTML (JS-triggered export),
        falls back to headless browser: clicks the export button and captures
        the downloaded file.
        """
        recon = self._recon
        csv_exports = [m for m in recon.export_mechanisms
                       if re.search(r"csv|export|data", m["url"], re.I)
                       or re.search(r"csv|export", m["label"], re.I)]
        if not csv_exports:
            return []

        export_mech = csv_exports[0]
        export_url = export_mech["url"]
        export_label = export_mech.get("label", "")

        # Try 1: static fetch (works for direct download links)
        print(f"\n  Fetching export: {export_url}")
        text = self.fetch(export_url)
        if text:
            stripped = text.strip()
            if not (stripped.startswith("<!") or stripped.startswith("<html")):
                rows = self._try_parse_csv(text)
                if rows is not None:
                    return self._build_records_from_csv(rows, limit)

        # Try 2: headless browser — click the export button and capture download
        print("  Static fetch returned HTML or failed — trying headless download...")
        text = self._headless_download_export(export_label, export_url)
        if text:
            rows = self._try_parse_csv(text)
            if rows is not None:
                return self._build_records_from_csv(rows, limit)

        print("  CSV export failed — falling back to next strategy")
        return []

    def _try_parse_csv(self, text: str) -> list[dict] | None:
        """Try to parse text as CSV. Returns list of dicts or None."""
        try:
            rows = list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            print(f"  Failed to parse as CSV: {e}")
            return None

        if not rows:
            print("  CSV is empty")
            return None

        # Sanity check: CSV columns should be short strings, not HTML fragments
        if any(len(col) > 200 for col in rows[0].keys()):
            print("  CSV columns look like HTML fragments — not valid CSV")
            return None

        print(f"  CSV rows: {len(rows)}")
        return rows

    def _headless_download_export(
        self, button_label: str, export_url: str,
    ) -> str | None:
        """Use headless browser to click an export button and capture the download."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  Headless browser not available")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.landing_url, wait_until="networkidle",
                          timeout=30000)

                # Find the export button/link by matching label text
                # Try several selectors
                btn = None
                if button_label:
                    # Exact text match
                    btn = page.query_selector(
                        f"a:has-text('{button_label}'), "
                        f"button:has-text('{button_label}')"
                    )

                if not btn:
                    # Broader: look for export/download/CSV keywords
                    for selector in [
                        "a:has-text('Export')", "button:has-text('Export')",
                        "a:has-text('Download CSV')", "button:has-text('Download CSV')",
                        "a:has-text('Download')", "button:has-text('Download')",
                        f"a[href='{export_url}']",
                    ]:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            break
                        btn = None

                if not btn:
                    print("  Could not find export button in headless browser")
                    browser.close()
                    return None

                label = btn.text_content().strip()[:50]
                print(f"  Found export button: '{label}'")

                # Click and capture the download
                with page.expect_download(timeout=30000) as download_info:
                    btn.click()

                download = download_info.value
                # Read the downloaded file content
                download_path = download.path()
                if download_path:
                    with open(download_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        text = f.read()
                    print(f"  Downloaded: {download.suggested_filename} "
                          f"({len(text):,} bytes)")
                    browser.close()
                    return text

                browser.close()
                return None

        except Exception as e:
            print(f"  Headless export download failed: {e}")
            return None

    def _build_records_from_csv(
        self, rows: list[dict], limit: int | None,
    ) -> list[DocumentRecord]:
        """Build DocumentRecords from parsed CSV rows.

        Shared by csv_export (static + headless) and manual_csv strategies.
        """
        # Identify URL column and title column
        url_col = self._detect_url_column(rows)
        title_col = self._detect_title_column(rows)
        print(f"  URL column: {url_col or '(none found)'}")
        print(f"  Title column: {title_col or '(none found)'}")
        print(f"  All columns: {list(rows[0].keys())}")

        self._export_csv_rows = rows

        # Build records — every CSV column is potential metadata
        records = []
        hrefs_to_visit = []

        for row in rows:
            page_url = str(row.get(url_col, "") or "" if url_col else "").strip()
            title = str(row.get(title_col, "") or "" if title_col else "").strip()

            if not page_url and not title:
                continue

            metadata = {}
            for col, val in row.items():
                if col in (url_col, title_col):
                    continue
                if val and str(val).strip():
                    metadata[col] = str(val).strip()

            records.append(DocumentRecord(
                page_url=page_url or "",
                doc_urls=[],
                title=title or page_url.rstrip("/").split("/")[-1],
                metadata=metadata,
            ))

            if page_url:
                hrefs_to_visit.append((len(records) - 1, page_url))

        print(f"  Records from CSV: {len(records)}")
        print(f"  Records with page URLs: {len(hrefs_to_visit)}")
        print(f"  Metadata fields per record: "
              f"{len(rows[0]) - (1 if url_col else 0) - (1 if title_col else 0)}")

        # Visit document pages to find PDF URLs
        if limit:
            hrefs_to_visit = hrefs_to_visit[:limit]

        if hrefs_to_visit:
            print(f"\n  Visiting {len(hrefs_to_visit)} pages for PDF URLs...")
            for idx, page_url in hrefs_to_visit:
                self._visit_for_pdfs(records[idx], skip_metadata=True)

        if limit:
            records = records[:limit]

        return records

    def _discover_via_api(self, limit: int | None) -> list[DocumentRecord]:
        """Use intercepted API data to build document records.

        The headless renderer captured JSON API responses that the frontend
        consumes. We use the structured data directly — much richer than
        scraping the rendered HTML.

        If the intercepted response only contains one page of results,
        we attempt to paginate the API to get the full dataset.
        """
        recon = self._recon
        if not recon.api_endpoints:
            return []

        best = recon.api_endpoints[0]
        all_items = best["_all_records"]
        api_url = best["url"]
        url_fields = best["url_fields"]
        title_fields = best["title_fields"]
        pagination = best.get("pagination")

        print(f"\n  API endpoint: {api_url}")
        print(f"  Records in initial response: {len(all_items)}")
        print(f"  Fields: {', '.join(best['fields'][:15])}")

        # If the API has pagination info, try to fetch remaining pages
        if pagination and pagination.get("total"):
            total = pagination["total"]
            per_page = pagination.get("per_page") or len(all_items)
            if total > len(all_items) and per_page > 0:
                print(f"  API reports {total} total records "
                      f"({per_page}/page) — fetching remaining pages...")
                all_items = list(all_items)  # copy
                post_data = best.get("post_data")
                search_engine = pagination.get("search_engine")
                if search_engine == "algolia" and post_data:
                    all_items = self._paginate_algolia(
                        api_url, all_items, total, per_page, post_data
                    )
                else:
                    all_items = self._paginate_api(
                        api_url, all_items, total, per_page, pagination
                    )

        print(f"  Total API records: {len(all_items)}")

        # Pick the best URL field and title field
        best_url_field = self._pick_best_field(url_fields, all_items, "url")
        best_title_field = self._pick_best_field(title_fields, all_items, "title")
        print(f"  URL field: {best_url_field or '(none)'}")
        print(f"  Title field: {best_title_field or '(none)'}")

        # Build records
        records = []
        for item in all_items:
            page_url = ""
            if best_url_field:
                raw_url = str(item.get(best_url_field, "")).strip()
                if raw_url:
                    # Could be a full URL or a relative path/slug
                    if raw_url.startswith("http"):
                        page_url = raw_url
                    elif raw_url.startswith("/"):
                        page_url = f"{self.site_base}{raw_url}"
                    else:
                        # Might be a slug — join to the landing URL
                        page_url = urljoin(self.landing_url, raw_url)

            # Fallback: if no URL field, construct from item ID + landing path
            if not page_url:
                item_id = item.get("id") or item.get("Id") or item.get("ID")
                if item_id is not None:
                    landing_path = self.landing_parsed.path.rstrip("/")
                    page_url = f"{self.site_base}{landing_path}/{item_id}"

            title = ""
            if best_title_field:
                title = str(item.get(best_title_field, "")).strip()

            if not page_url and not title:
                continue

            # All API fields become metadata
            metadata = {}
            for key, val in item.items():
                if key in (best_url_field, best_title_field):
                    continue
                if key.startswith("_"):
                    continue
                if val is not None and str(val).strip():
                    # Flatten nested objects to string
                    if isinstance(val, (dict, list)):
                        metadata[key] = json.dumps(val, default=str)
                    else:
                        metadata[key] = str(val).strip()

            records.append(DocumentRecord(
                page_url=page_url,
                doc_urls=[],
                title=title or page_url.rstrip("/").split("/")[-1],
                metadata=metadata,
            ))

        print(f"  Records from API: {len(records)}")
        if records and records[0].metadata:
            print(f"  Metadata fields: {list(records[0].metadata.keys())[:10]}")

        # Try to extract file download URLs directly from API metadata
        # (avoids slow per-page visits when the API provides file info)
        api_base = api_url.rsplit("/", 1)[0]  # strip last path segment
        files_extracted = self._extract_files_from_api(
            records, all_items, api_base)

        # Visit pages for PDF URLs only for records that don't already have them
        to_visit = records[:limit] if limit else records
        need_visit = [r for r in to_visit if not r.doc_urls]
        if need_visit:
            print(f"\n  Visiting {len(need_visit)} pages for PDF URLs"
                  f" ({len(to_visit) - len(need_visit)} already have file URLs)...")
            for i, record in enumerate(need_visit):
                if record.page_url:
                    self._visit_for_pdfs(record)
                if (i + 1) % self._checkpoint_interval == 0:
                    self._save_checkpoint("api_intercept", to_visit[:i+1])
        elif files_extracted:
            print(f"\n  All {len(to_visit)} records have file URLs from API"
                  f" — skipping page visits")

        return to_visit

    def _extract_files_from_api(
        self, records: list, raw_items: list[dict], api_base: str,
    ) -> int:
        """Extract file download URLs from API metadata fields.

        Many APIs include a 'files' array with fileId/name/size objects.
        When present, we construct download URLs directly rather than
        visiting each detail page.

        Probes common URL patterns:
          {api_base}/documents/{doc_id}/files/{file_id}
          {api_base}/files/{file_id}
          {api_base}/document/{doc_id}/file/{file_id}

        Returns the number of records that got file URLs.
        """
        if not raw_items or not records:
            return 0

        # Find the files field: look for list-of-dicts with fileId/id + name
        files_field = None
        id_field = None
        file_id_key = None
        for key, val in raw_items[0].items():
            if isinstance(val, list) and val:
                if isinstance(val[0], dict):
                    for fk in ("fileId", "file_id", "id"):
                        if fk in val[0] and "name" in val[0]:
                            files_field = key
                            file_id_key = fk
                            break
            if key == "id" and isinstance(val, (int, str)):
                id_field = key

        if not files_field or not file_id_key:
            return 0

        # Find the document ID field
        if not id_field:
            for key in ("id", "documentId", "doc_id", "Id"):
                if key in raw_items[0]:
                    id_field = key
                    break

        if not id_field:
            return 0

        # Probe to find the correct download URL pattern
        sample_item = raw_items[0]
        sample_files = sample_item[files_field]
        sample_doc_id = sample_item[id_field]
        sample_file_id = sample_files[0][file_id_key]

        url_patterns = [
            f"{api_base}/documents/{sample_doc_id}/files/{sample_file_id}",
            f"{api_base}/files/{sample_file_id}",
            f"{api_base}/document/{sample_doc_id}/file/{sample_file_id}",
        ]

        working_pattern = None
        for test_url in url_patterns:
            try:
                # Try HEAD first (cheap), fall back to GET+stream
                # if the server returns 405 Method Not Allowed
                resp = self.session.head(test_url, timeout=15, allow_redirects=True)
                if resp.status_code == 405:
                    resp = self.session.get(
                        test_url, timeout=15, allow_redirects=True, stream=True)
                    resp.close()
                ct = resp.headers.get("content-type", "")
                if resp.status_code == 200 and (
                    "pdf" in ct or "octet" in ct or "zip" in ct
                    or resp.headers.get("content-disposition", "")
                ):
                    working_pattern = test_url.replace(
                        str(sample_doc_id), "{doc_id}"
                    ).replace(str(sample_file_id), "{file_id}")
                    print(f"  File download URL pattern: {working_pattern}")
                    break
            except Exception:
                continue

        if not working_pattern:
            return 0

        # Apply the pattern to all records
        count = 0
        for record, item in zip(records, raw_items):
            files = item.get(files_field, [])
            doc_id = item.get(id_field, "")
            if not files or not doc_id:
                continue
            for f in files:
                fid = f.get(file_id_key)
                if not fid:
                    continue
                url = working_pattern.replace("{doc_id}", str(doc_id)).replace(
                    "{file_id}", str(fid))
                record.doc_urls.append(url)
            if record.doc_urls:
                count += 1

        print(f"  Extracted file URLs for {count}/{len(records)} records")
        return count

    def _paginate_api(
        self, base_url: str, items: list, total: int,
        per_page: int, pagination: dict,
    ) -> list:
        """Fetch remaining pages from a paginated JSON API.

        Tries common pagination patterns:
        1. page=N query parameter
        2. offset=N query parameter
        3. cursor/after parameter from response
        """
        from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

        parts = urlsplit(base_url)
        params = parse_qs(parts.query, keep_blank_values=True)

        # Detect which pagination param is already in the URL
        page_param = None
        for candidate in ("page", "p", "pageNumber", "page_number"):
            if candidate in params:
                page_param = candidate
                break

        offset_param = None
        for candidate in ("offset", "skip", "start"):
            if candidate in params:
                offset_param = candidate
                break

        max_pages = (total // per_page) + 1
        max_pages = min(max_pages, 200)  # safety cap

        fetched_pages = 1
        while len(items) < total and fetched_pages < max_pages:
            fetched_pages += 1

            # Build next page URL
            if page_param:
                params[page_param] = [str(fetched_pages)]
            elif offset_param:
                params[offset_param] = [str(len(items))]
            else:
                # Guess: try adding page= parameter
                page_param = "page"
                params[page_param] = [str(fetched_pages)]

            new_query = urlencode(params, doseq=True)
            next_url = urlunsplit((
                parts.scheme, parts.netloc, parts.path,
                new_query, parts.fragment,
            ))

            text = self.fetch(next_url)
            if not text:
                break

            try:
                body = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                break

            # Extract items from response (same structure as initial)
            page_items = None
            if isinstance(body, list):
                page_items = body
            elif isinstance(body, dict):
                for key, val in body.items():
                    if isinstance(val, list) and len(val) > 0:
                        if all(isinstance(v, dict) for v in val[:5]):
                            page_items = val
                            break

            if not page_items:
                break

            items.extend(page_items)

            if fetched_pages % 10 == 0:
                print(f"    ... API page {fetched_pages}, "
                      f"{len(items)}/{total} records", flush=True)

        print(f"  API pagination: {fetched_pages} pages, "
              f"{len(items)} records (target: {total})")
        return items

    def _paginate_algolia(
        self, api_url: str, items: list, total: int,
        per_page: int, post_data: str,
    ) -> list:
        """Paginate an Algolia search API by replaying the POST with page=N.

        Algolia multi-query sends a POST body like:
        {"requests": [{"indexName": "...", "params": "query=&page=0&..."}]}

        We identify the main query (the one returning hits), modify its
        page parameter, and replay the request.
        """
        import time
        try:
            body = json.loads(post_data)
        except (json.JSONDecodeError, TypeError):
            print("  Could not parse Algolia POST body — falling back")
            return items

        requests_list = body.get("requests", [])
        if not requests_list:
            return items

        # Find the query that returns the main result set (hitsPerPage > 0)
        main_idx = None
        for i, req in enumerate(requests_list):
            params = req.get("params", "")
            if f"hitsPerPage={per_page}" in params or "hitsPerPage" in params:
                # Check this isn't a count-only query (hitsPerPage=0)
                if "hitsPerPage=0" not in params:
                    main_idx = i
                    break

        if main_idx is None:
            # Fallback: pick the first query
            main_idx = 0

        total_pages = (total + per_page - 1) // per_page
        total_pages = min(total_pages, 200)  # safety cap
        seen_ids = {item.get("objectID") for item in items
                    if item.get("objectID") is not None}

        import requests as http_requests

        for page_num in range(1, total_pages):
            # Modify the page parameter in the main query
            req = requests_list[main_idx]
            params = req.get("params", "")

            if "page=" in params:
                import re as _re
                new_params = _re.sub(r"page=\d+", f"page={page_num}", params)
            else:
                new_params = params + f"&page={page_num}"

            # Build modified request body (only change the main query)
            modified_body = json.loads(post_data)
            modified_body["requests"][main_idx]["params"] = new_params

            try:
                resp = http_requests.post(
                    api_url,
                    json=modified_body,
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )
                resp.raise_for_status()
                resp_body = resp.json()
            except Exception as e:
                print(f"  Algolia page {page_num} failed: {e}")
                break

            # Extract hits from the main result
            results = resp_body.get("results", [])
            if main_idx < len(results):
                hits = results[main_idx].get("hits", [])
            else:
                break

            if not hits:
                break

            new_count = 0
            for hit in hits:
                oid = hit.get("objectID")
                if oid is not None and oid in seen_ids:
                    continue
                items.append(hit)
                if oid is not None:
                    seen_ids.add(oid)
                new_count += 1

            if new_count == 0:
                break

            if (page_num + 1) % 10 == 0:
                print(f"    ... Algolia page {page_num + 1}/{total_pages}, "
                      f"{len(items)}/{total} records", flush=True)

            time.sleep(1.0)  # rate limit

        print(f"  Algolia pagination: {min(page_num + 1, total_pages)} pages, "
              f"{len(items)} records (target: {total})")
        return items

    @staticmethod
    def _pick_best_field(
        candidates: list[str], items: list[dict], field_type: str,
    ) -> str | None:
        """Pick the best field name from candidates based on actual values."""
        if not candidates or not items:
            return candidates[0] if candidates else None

        # Score each candidate by how many items have a non-empty value
        scores = {}
        for field in candidates:
            filled = sum(1 for item in items[:50]
                         if item.get(field) and str(item[field]).strip())
            scores[field] = filled

        # For URL fields, prefer ones whose values look like URLs
        if field_type == "url":
            for field in candidates:
                sample = str(items[0].get(field, ""))
                if sample.startswith("http") or sample.startswith("/"):
                    scores[field] += 100  # strong signal

        # For title fields, prefer exact "title" over compound names
        if field_type == "title":
            for field in candidates:
                if field.lower() == "title":
                    scores[field] += 100

        if not scores:
            return candidates[0] if candidates else None
        return max(scores, key=scores.get)

    def _discover_via_pagination(self, limit: int | None) -> list[DocumentRecord]:
        """Follow pagination to collect document page URLs, then visit each."""
        recon = self._recon
        if not recon.pagination:
            return []

        # Identify which link pattern is most likely to be documents
        doc_pattern = None
        if recon.document_link_candidates:
            # Use the pattern with the most links
            doc_pattern = recon.document_link_candidates[0][0]
            print(f"  Document link pattern: {doc_pattern}")

        # Paginate and collect document URLs
        all_doc_urls = set()
        current_url = self.landing_url
        page = 0

        while True:
            print(f"  Page {page}... ", end="", flush=True)

            if page == 0:
                soup = self.fetch_soup(current_url)
            else:
                soup = self.fetch_soup(current_url)

            if soup is None:
                print("FAILED")
                break

            # Find document links on this page
            page_urls = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full_url = urljoin(current_url, href)
                parsed = urlparse(full_url)

                # Only internal links
                if parsed.netloc != self.landing_parsed.netloc:
                    continue

                # Match against document pattern if we have one
                if doc_pattern:
                    if parsed.path.startswith(doc_pattern.rstrip("/")):
                        # But not the pattern itself (which is the listing page)
                        if parsed.path.rstrip("/") != doc_pattern.rstrip("/"):
                            page_urls.add(full_url.split("?")[0])
                else:
                    # Without a pattern, take all internal links that look like
                    # document pages (have a slug, aren't navigation)
                    parts = [p for p in parsed.path.strip("/").split("/") if p]
                    if len(parts) >= 2 and not any(
                        nav in parsed.path for nav in [
                            "/search", "/login", "/about", "/contact",
                            "/privacy", "/accessibility",
                        ]
                    ):
                        page_urls.add(full_url.split("?")[0])

            new = page_urls - all_doc_urls
            all_doc_urls.update(page_urls)
            print(f"{len(new)} new (total: {len(all_doc_urls)})")

            if not new:
                break
            if limit and len(all_doc_urls) >= limit:
                break

            # Find next page
            next_link = soup.find("a", rel="next")
            if next_link:
                current_url = urljoin(current_url, next_link["href"])
                page += 1
            else:
                # Try incrementing page param
                pag = recon.pagination
                if pag.get("page_param"):
                    page += 1
                    sep = "&" if "?" in self.landing_url else "?"
                    current_url = f"{self.landing_url}{sep}{pag['page_param']}={page}"
                else:
                    break

        # Deduplicate: if URL A is a prefix of URL B, keep only A
        # (e.g. /doc/latest and /doc/latest/downloads → keep /doc/latest)
        deduped = set()
        for url in sorted(all_doc_urls, key=len):
            url_path = urlparse(url).path.rstrip("/") + "/"
            if not any(url_path.startswith(urlparse(existing).path.rstrip("/") + "/")
                       for existing in deduped):
                deduped.add(url)
        if len(deduped) < len(all_doc_urls):
            print(f"  Deduplicated: {len(all_doc_urls)} → {len(deduped)} "
                  f"(removed sub-page URLs)")

        sorted_urls = sorted(deduped)
        if limit:
            sorted_urls = sorted_urls[:limit]

        print(f"\n  Total document URLs: {len(sorted_urls)}")
        print(f"  Visiting each for title, PDFs, and metadata...\n")

        # Visit each document page
        records = []
        for i, doc_url in enumerate(sorted_urls):
            slug = doc_url.rstrip("/").split("/")[-1]
            tag = f"[{i+1}/{len(sorted_urls)}]"
            print(f"  {tag} {slug}... ", end="", flush=True)

            rec = DocumentRecord(
                page_url=doc_url,
                doc_urls=[],
                title=slug,
                metadata={},
            )
            self._visit_for_pdfs(rec)
            self._extract_page_metadata(rec)
            records.append(rec)

            if len(records) % self._checkpoint_interval == 0:
                self._save_checkpoint("paginated_listing", records, page)

        self._flush_curation_buffer()
        return records

    def _discover_via_sitemap(self, limit: int | None) -> list[DocumentRecord]:
        """Use sitemap URLs to discover documents.

        Visits each depth-1 page under the landing path prefix. Each page
        is checked for PDFs and metadata. If no PDFs are found directly on
        the page, follows sub-page links (e.g. /report, /draft) to find
        PDFs one level deeper — common on sites like PC where the main
        inquiry page links to a separate report download page.
        """
        recon = self._recon
        if not recon.sitemap_urls:
            return []

        doc_urls = sorted(recon.sitemap_urls)
        if limit:
            doc_urls = doc_urls[:limit]

        print(f"  Sitemap URLs to visit: {len(doc_urls)}")
        print(f"  Visiting each for title, PDFs, and metadata...\n")

        records = []
        for i, doc_url in enumerate(doc_urls):
            slug = doc_url.rstrip("/").split("/")[-1]
            tag = f"[{i+1}/{len(doc_urls)}]"
            print(f"  {tag} {slug}... ", end="", flush=True)

            rec = DocumentRecord(
                page_url=doc_url,
                doc_urls=[],
                title=slug,
                metadata={},
            )
            self._visit_for_pdfs(rec)
            records.append(rec)

            if len(records) % self._checkpoint_interval == 0:
                self._save_checkpoint("sitemap", records)

        self._flush_curation_buffer()
        return records

    def _follow_subpages_for_pdfs(self, record: DocumentRecord):
        """Follow sub-page links from a document page to find PDFs.

        Some sites (e.g. Productivity Commission) put PDFs on sub-pages
        like /report or /draft rather than the main inquiry page.
        Only follows internal links that are direct children of the
        document's URL path.
        """
        soup = self.fetch_soup(record.page_url)
        if soup is None:
            return

        page_path = urlparse(record.page_url).path.rstrip("/")
        subpage_urls = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(record.page_url, href)
            parsed = urlparse(full_url)

            # Only internal links
            if parsed.netloc != self.landing_parsed.netloc:
                continue

            sub_path = parsed.path.rstrip("/")
            # Must be a direct child of this page's path
            if sub_path.startswith(page_path + "/"):
                remainder = sub_path[len(page_path) + 1:]
                # Only one level deep, no further nesting
                if "/" not in remainder and remainder:
                    subpage_urls.append(full_url.split("?")[0])

        subpage_urls = list(dict.fromkeys(subpage_urls))  # dedupe, preserve order

        # Prioritise report/draft pages (most likely to have PDFs)
        priority_slugs = {"report", "draft", "final-report", "final",
                          "interim", "supplement"}
        subpage_urls.sort(
            key=lambda u: (0 if u.rstrip("/").split("/")[-1] in priority_slugs else 1)
        )

        for sub_url in subpage_urls[:5]:  # cap to avoid over-crawling
            sub_slug = sub_url.rstrip("/").split("/")[-1]
            sub_soup = self.fetch_soup(sub_url)
            if sub_soup is None:
                continue

            found = 0
            for a in sub_soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r"\.pdf(\?|$)", href, re.I):
                    pdf_url = urljoin(sub_url, href)
                    if pdf_url not in record.doc_urls:
                        record.doc_urls.append(pdf_url)
                        found += 1

            if found:
                print(f" +{found} PDF from /{sub_slug}", end="")
                break  # found PDFs, no need to check more sub-pages

    def _discover_via_links(self, limit: int | None) -> list[DocumentRecord]:
        """Use document links found on the landing page (no pagination)."""
        recon = self._recon
        if not recon.document_link_candidates:
            return []

        # Use the dominant pattern
        pattern, count, samples = recon.document_link_candidates[0]
        doc_urls = samples  # We already have these from recon

        if limit:
            doc_urls = doc_urls[:limit]

        records = []
        for i, doc_url in enumerate(doc_urls):
            slug = doc_url.rstrip("/").split("/")[-1]
            tag = f"[{i+1}/{len(doc_urls)}]"
            print(f"  {tag} {slug}... ", end="", flush=True)

            rec = DocumentRecord(
                page_url=doc_url,
                doc_urls=[],
                title=slug,
                metadata={},
            )
            self._visit_for_pdfs(rec)
            self._extract_page_metadata(rec)
            records.append(rec)

        self._flush_curation_buffer()
        return records

    def _discover_direct_pdfs(self, limit: int | None) -> list[DocumentRecord]:
        """Use direct PDF links found on the landing page."""
        recon = self._recon
        pdf_links = recon.pdf_links
        if limit:
            pdf_links = pdf_links[:limit]

        records = []
        for url, text in pdf_links:
            records.append(DocumentRecord(
                page_url=self.landing_url,
                doc_urls=[url],
                title=text or url.rstrip("/").split("/")[-1],
                metadata={},
            ))
        return records

    # ---- Page visiting helpers ----

    @staticmethod
    def _extract_title(soup) -> str | None:
        """Extract document title from a page, trying multiple sources.

        Priority:
        1. dcterms.title meta tag (Dublin Core — most reliable)
        2. og:title meta tag
        3. <h1> that isn't generic site chrome (>10 chars, not repeated)
        4. First <h2> if <h1> looks like a site name
        """
        # Dublin Core
        dc_title = soup.find("meta", attrs={"name": "dcterms.title"})
        if dc_title and dc_title.get("content", "").strip():
            return dc_title["content"].strip()

        # Open Graph
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content", "").strip():
            return og_title["content"].strip()

        # <h1> — but skip generic site-wide headings
        h1s = soup.find_all("h1")
        for h1 in h1s:
            text = h1.get_text(strip=True)
            if not text or len(text) < 5:
                continue
            # Skip screen-reader-only headings
            classes = h1.get("class", [])
            if any(c in ("sr-only", "visually-hidden") for c in classes):
                continue
            # If there are multiple h1s and this one is short/generic, skip it
            if len(h1s) > 1 and len(text) < 30:
                continue
            return text

        # Fallback: first h1 regardless
        if h1s:
            text = h1s[0].get_text(strip=True)
            if text:
                return text

        # Last resort: <h2>
        h2 = soup.find("h2")
        if h2:
            text = h2.get_text(strip=True)
            if text and len(text) > 5:
                return text

        return None

    @staticmethod
    def _find_doc_links(soup, record: DocumentRecord):
        """Extract PDF/document download links from a parsed page."""
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title_attr = a.get("title", "")
            is_pdf = re.search(r"\.pdf(\?|$)", href, re.I)
            is_doc_link = (
                re.search(r"/pdf$|/word$|format=pdf", href, re.I)
                or re.search(r'download.*\.(pdf|docx?)"?$', title_attr, re.I)
            )
            if is_pdf or is_doc_link:
                full_url = urljoin(record.page_url, href)
                if full_url not in record.doc_urls:
                    record.doc_urls.append(full_url)

    def _follow_download_subpages(self, soup, record: DocumentRecord):
        """When no PDFs on main page, check sub-pages that look like download tabs.

        Follows internal links that are direct children of the document's URL
        path, prioritising paths containing 'download', 'document', 'file',
        or 'report'. At most 3 sub-pages are visited.
        """
        page_path = urlparse(record.page_url).path.rstrip("/")
        subpage_urls = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(record.page_url, href)
            parsed = urlparse(full_url)

            # Must be same host
            if parsed.netloc != self.landing_parsed.netloc:
                continue

            sub_path = parsed.path.rstrip("/")
            # Must be a direct child path
            if not sub_path.startswith(page_path + "/"):
                continue
            # Only one extra segment
            remainder = sub_path[len(page_path) + 1:]
            if "/" in remainder:
                continue
            if sub_path == page_path:
                continue

            subpage_urls.append((full_url, remainder.lower()))

        # Prioritise download-looking sub-pages
        download_hints = ("download", "document", "file", "report", "pdf")
        subpage_urls.sort(
            key=lambda x: (0 if any(h in x[1] for h in download_hints) else 1, x[1])
        )

        for sub_url, _ in subpage_urls[:3]:
            sub_soup = self.fetch_soup(sub_url)
            if sub_soup:
                self._find_doc_links(sub_soup, record)
                if record.doc_urls:
                    break

    def _visit_for_pdfs(self, record: DocumentRecord, skip_metadata: bool = False):
        """Visit a document page to find PDF links and optionally extract metadata.

        When skip_metadata=False (default), also runs aggressive metadata
        extraction from the page HTML — appropriate when pages are the
        primary metadata source (pagination/link strategies).

        When skip_metadata=True, only discovers PDF links and updates the
        title — appropriate when metadata already comes from a CSV export.
        """
        if not record.page_url:
            print("NO URL")
            return

        soup = self.fetch_soup(record.page_url)
        if soup is None:
            print("FAILED")
            return

        # Update title from page — but only if the record doesn't already
        # have a meaningful title (e.g. from an API response)
        title = self._extract_title(soup)
        if title and (not record.title or record.title == record.page_url.rstrip("/").split("/")[-1]):
            record.title = title

        # --- PDF/document links ---
        self._find_doc_links(soup, record)

        # If no PDFs found, check sub-pages (e.g. /downloads tab)
        if not record.doc_urls:
            self._follow_download_subpages(soup, record)

        # --- Metadata extraction (only when pages are the primary source) ---
        if not skip_metadata:
            self._extract_metadata_from_soup(soup, record)

            # Field curation: buffer first N pages, curate from richest, apply retroactively
            if self._field_whitelist is not None:
                self._apply_field_whitelist(record)
            else:
                self._curation_samples.append(dict(record.metadata))
                self._curation_buffer.append(record)
                if len(self._curation_samples) >= self._curation_sample_target:
                    self._curate_from_samples()

        status = f"OK ({len(record.doc_urls)} PDF)" if record.doc_urls else "NO PDF"
        print(status)

    def _extract_page_metadata(self, record: DocumentRecord):
        """Extract metadata from a document page (separate fetch).

        Use _visit_for_pdfs instead when possible — it combines PDF
        discovery and metadata extraction in a single request.
        """
        soup = self.fetch_soup(record.page_url)
        if soup is None:
            return
        self._extract_metadata_from_soup(soup, record)
        if self._field_whitelist is not None:
            self._apply_field_whitelist(record)

    def _extract_metadata_from_soup(self, soup, record: DocumentRecord):
        """Extract all available metadata from a parsed page.

        Uses multiple strategies in order of specificity:
        1. <time> elements (most reliable for dates)
        2. <meta> tags (Dublin Core, Open Graph, etc.)
        3. Semantic div class names — divs whose class name describes
           their content (e.g. report_date, report-num, audit-objective)
        4. CMS label-value field patterns (Drupal, WordPress)
        """
        # --- Strategy 1: <time> elements ---
        time_el = soup.find("time")
        if time_el:
            record.metadata["date"] = time_el.get(
                "datetime", time_el.get_text(strip=True)
            )

        # --- Strategy 2: <meta> tags ---
        # 2a. Standard name-based meta tags
        NAME_WHITELIST = {
            "date", "author", "description", "keywords",
            "dcterms.title", "dcterms.date", "dcterms.creator",
            "dcterms.subject", "dcterms.identifier", "dcterms.language",
        }
        for meta in soup.find_all("meta", attrs={"name": True}):
            name = meta["name"].lower()
            content = meta.get("content", "")
            if content and name in NAME_WHITELIST:
                key = name.replace("dcterms.", "meta_")
                record.metadata.setdefault(key, content)

        # 2b. Open Graph (property="og:*") and Twitter (name="twitter:*")
        for meta in soup.find_all("meta"):
            prop = (meta.get("property") or meta.get("name") or "").lower()
            content = meta.get("content", "").strip()
            if not content:
                continue
            if prop == "og:title":
                record.metadata.setdefault("og_title", content)
                # Many sites use "Document Title - Report Type" in og:title
                if " - " in content:
                    parts = content.rsplit(" - ", 1)
                    if len(parts[1]) < 80:
                        record.metadata.setdefault("report_type", parts[1])
            elif prop == "og:description":
                record.metadata.setdefault("description", content)
            elif prop == "og:url":
                record.metadata.setdefault("og_url", content)
            elif prop in ("twitter:title", "twitter:description"):
                pass  # redundant with og: equivalents

        # --- Strategy 3: Semantic div class names ---
        # Many government sites use descriptive class names for data fields.
        # Harvest any div with a short, semantic class name that contains
        # short text and isn't a layout container.
        LAYOUT_CLASSES = {
            "container", "wrapper", "row", "col", "grid", "hidden",
            "block", "region", "page", "dialog", "toolbar", "menu",
            "header", "footer", "sidebar", "nav", "main", "content",
            "clearfix", "contextual", "view", "views", "panel",
        }

        for div in soup.find_all("div", class_=True):
            classes = div.get("class", [])
            if not classes:
                continue

            # Skip if any class looks like a layout/framework class
            class_str = " ".join(classes)
            if any(lc in cl.lower() for cl in classes for lc in LAYOUT_CLASSES):
                continue
            # Skip deeply nested containers
            if len(list(div.find_all("div", recursive=False))) > 3:
                continue

            text = div.get_text(strip=True)
            # Only interested in data-sized text (not empty, not huge sections)
            if not text or len(text) > 2000:
                continue

            # Derive a key from the class name
            # Use the most specific (longest) class as the key
            best_class = max(classes, key=len)
            key = re.sub(r"[^a-z0-9]+", "_", best_class.lower()).strip("_")

            # Skip if the key is too generic or already captured
            if len(key) < 4 or key in record.metadata:
                continue
            # Skip class names that are just style modifiers
            if key in ("field", "item", "items", "label", "value", "text",
                       "field__item", "field__items", "field__label"):
                continue

            record.metadata[key] = text

        # --- Strategy 4: CMS label-value field patterns ---
        # Drupal, WordPress, and similar CMSes use a pattern:
        # <div class="field">
        #   <div class="field__label">Entity</div>
        #   <div class="field__item">Department of X</div>
        # </div>
        for div in soup.find_all("div", class_=lambda c: c and "field" in (
            c if isinstance(c, str) else " ".join(c)
        )):
            label_el = div.find(
                ["div", "span", "dt", "label", "h3", "h4"],
                class_=lambda c: c and "label" in (
                    c if isinstance(c, str) else " ".join(c)
                ),
            )
            if not label_el:
                continue
            label = label_el.get_text(strip=True).rstrip(":")

            # Get value: try multiple child patterns
            value_parts = []
            for value_el in div.find_all(
                ["div", "span", "dd"],
                class_=lambda c: c and "item" in (
                    c if isinstance(c, str) else " ".join(c)
                ),
            ):
                val = value_el.get_text(strip=True)
                if val:
                    value_parts.append(val)

            if label and value_parts and len(label) < 50:
                key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
                value = "; ".join(value_parts)
                record.metadata[key] = value

    # ---- LLM field curation ----

    def _load_field_whitelist(self) -> set[str] | None:
        """Load cached field whitelist from disk if it exists."""
        cache_path = self.corpus_dir / ".field_whitelist.json"
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            whitelist = set(data.get("fields", []))
            print(f"  Loaded cached field whitelist: {len(whitelist)} fields")
            return whitelist
        return None

    def _save_field_whitelist(self, whitelist: set[str]):
        """Cache field whitelist to disk for reuse across runs."""
        cache_path = self.corpus_dir / ".field_whitelist.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "fields": sorted(whitelist),
            "domain": self.domain,
            "landing_url": self.landing_url,
        }, indent=2))

    def _curate_fields_via_llm(self, sample_metadata: dict) -> set[str]:
        """Use an LLM to select contextually relevant metadata fields.

        Given ~50 raw field names and sample values scraped from a document
        page, asks the model which fields describe document context,
        provenance, or subject matter — vs layout noise or CMS boilerplate.

        One call on a single sample page; the resulting whitelist is applied
        to all subsequent pages and cached to disk.
        """
        import anthropic

        # Build the sample display
        field_lines = []
        for key, value in sorted(sample_metadata.items()):
            # Truncate long values for the prompt
            display_val = str(value)[:200]
            field_lines.append(f"  {key}: {display_val}")
        fields_block = "\n".join(field_lines)

        prompt = f"""You are curating metadata fields scraped from a government document page.

Below are all field names and sample values extracted from one document page. Many are useful document metadata (dates, authors, categories, report numbers, subjects, entities). Others are CMS/layout noise (Drupal block IDs, framework class names, navigation text, repeated boilerplate).

FIELDS AND SAMPLE VALUES:
{fields_block}

Select ONLY the fields that describe:
- Document provenance (dates, report numbers, authors, publishers)
- Document subject matter (topics, categories, entities, portfolios)
- Document scope (audit objectives, summaries, key findings)
- Document relationships (related documents, parent projects)

Reject fields that are:
- CMS/layout boilerplate (block IDs, Drupal class derivatives, menu text)
- Navigation elements (breadcrumbs, sidebar content)
- Duplicates of other fields with slightly different names (keep the cleaner one)
- Page chrome (share buttons, print links, accessibility notices)

Return ONLY a JSON array of the selected field names, nothing else. Example:
["date", "report_number", "entity", "portfolio", "audit_objective_summary"]"""

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response — expect a JSON array
        text = response.content[0].text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        try:
            fields = json.loads(text)
            if isinstance(fields, list):
                whitelist = set(fields)
                print(f"  LLM field curation: {len(sample_metadata)} raw → "
                      f"{len(whitelist)} selected")
                return whitelist
        except json.JSONDecodeError:
            pass

        # Fallback: try to extract field names from the text
        found = re.findall(r'"([^"]+)"', text)
        if found:
            whitelist = set(found)
            print(f"  LLM field curation (parsed): {len(sample_metadata)} raw → "
                  f"{len(whitelist)} selected")
            return whitelist

        print(f"  LLM field curation failed to parse response — keeping all fields")
        return set(sample_metadata.keys())

    def _curate_from_samples(self):
        """Pick the richest sample from the buffer, curate fields, apply retroactively.

        Called once after the first N pages have been visited, or when
        discovery ends (via _flush_curation_buffer) if fewer than N pages exist.
        """
        if self._field_whitelist is not None:
            return

        # Try cache first
        cached = self._load_field_whitelist()
        if cached is not None:
            self._field_whitelist = cached
            for rec in self._curation_buffer:
                self._apply_field_whitelist(rec)
            self._curation_buffer.clear()
            self._curation_samples.clear()
            return

        if not self._curation_samples:
            return

        # Pick the sample with the most fields — richest page
        richest = max(self._curation_samples, key=len)

        # Heuristic: skip LLM curation if fields are already clean
        # (small count, no CSS-like names, no overly long names, consistent)
        if self._fields_already_clean(richest):
            self._field_whitelist = set(richest.keys())
            self._save_field_whitelist(self._field_whitelist)
            print(f"\n  Metadata fields look clean ({len(richest)} fields) — skipping LLM curation")
        else:
            print(f"\n  Curating metadata fields via LLM "
                  f"(richest of {len(self._curation_samples)} samples: "
                  f"{len(richest)} fields)...")
            self._field_whitelist = self._curate_fields_via_llm(richest)
        self._save_field_whitelist(self._field_whitelist)
        print(f"  Whitelist cached to .field_whitelist.json\n")

        # Retroactively filter buffered records
        for rec in self._curation_buffer:
            self._apply_field_whitelist(rec)
        self._curation_buffer.clear()
        self._curation_samples.clear()

    @staticmethod
    def _fields_already_clean(sample: dict) -> bool:
        """Heuristic: are metadata fields clean enough to skip LLM curation?

        Returns True if: ≤15 fields, no CSS-like names (__, --, block_,
        widget), no overly long names (>60 chars), and fields are
        consistently named (all lowercase or all camelCase).
        """
        keys = list(sample.keys())
        if len(keys) > 15:
            return False
        css_noise = ("__", "--", "block_", "widget", "module_", "theme_")
        for k in keys:
            if len(k) > 60:
                return False
            if any(noise in k for noise in css_noise):
                return False
        return True

    def _flush_curation_buffer(self):
        """Flush the curation buffer if discovery ended before N samples.

        Called at the end of each discover_via_* method to handle corpora
        with fewer pages than the sample target.
        """
        if self._field_whitelist is None and self._curation_samples:
            self._curate_from_samples()

    def _apply_field_whitelist(self, record: DocumentRecord):
        """Filter a record's metadata to only whitelisted fields."""
        if self._field_whitelist is None:
            return
        # Always keep fields that exactly match the whitelist
        # Also keep fields from CSV sources (they were curated by the export)
        filtered = {
            k: v for k, v in record.metadata.items()
            if k in self._field_whitelist
        }
        record.metadata = filtered

    # ---- Column detection helpers ----

    def _detect_url_column(self, rows: list[dict]) -> str | None:
        """Auto-detect which CSV column contains document page URLs."""
        if not rows:
            return None

        # Check column names first
        url_name_hints = ["url", "link", "href", "page", "uri"]
        for col in rows[0]:
            col_lower = col.lower()
            if any(hint in col_lower for hint in url_name_hints):
                # Verify it actually contains URLs
                sample = rows[0].get(col, "")
                if sample and ("http" in sample or sample.startswith("/")):
                    return col

        # Fall back to checking values
        for col in rows[0]:
            val = rows[0].get(col, "")
            if val and val.startswith("http"):
                return col

        return None

    def _detect_title_column(self, rows: list[dict]) -> str | None:
        """Auto-detect which CSV column contains document titles."""
        if not rows:
            return None

        title_hints = ["title", "name", "heading", "subject", "report"]
        for col in rows[0]:
            col_lower = col.lower()
            if any(hint in col_lower for hint in title_hints):
                return col
        return None
