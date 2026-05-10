"""Human review checklist for generated scraper scripts.

Runs 7 automated checks against a domain's scrape.py and reports results.
Some checks require human confirmation (marked CONFIRM).

Usage:
    from pipeline.ingest.checklist import run_checklist
    run_checklist("anao")
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = ROOT / "domains"
CORPORA_DIR = ROOT / "corpora"


def _load_scraper(domain: str):
    """Dynamically import domains/<domain>/scrape.py and return the Scraper class."""
    scrape_path = DOMAINS_DIR / domain / "scrape.py"
    if not scrape_path.exists():
        raise FileNotFoundError(
            f"No scrape.py at {scrape_path}"
        )

    spec = importlib.util.spec_from_file_location(f"domains.{domain}.scrape", scrape_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "Scraper"):
        raise AttributeError(f"{scrape_path} has no Scraper class")

    return module.Scraper, getattr(module, "EXPECTED_COUNT", None)


def _load_source_config(domain: str) -> dict:
    """Load source section from domain.yaml."""
    import yaml
    domain_yaml = DOMAINS_DIR / domain / "domain.yaml"
    if not domain_yaml.exists():
        return {}
    with open(domain_yaml) as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("source", {})


def run_checklist(domain: str, discover_limit: int | None = None):
    """Run the 7-item checklist against a domain's scraper."""

    print(f"=== Checklist: {domain} ===\n")
    results = {
        "domain": domain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }

    # Load scraper
    try:
        ScraperCls, expected_count = _load_scraper(domain)
    except (FileNotFoundError, AttributeError) as e:
        print(f"FATAL: {e}")
        return results

    source = _load_source_config(domain)
    if expected_count is None:
        expected_count = source.get("estimated_count")

    scraper = ScraperCls(domain, rate_limit=source.get("rate_limit_seconds", 1.0))

    # --- Check 1: Discovery smoke test ---
    print("1. Discovery smoke test")
    if discover_limit:
        print(f"   (limited to {discover_limit} records for testing)")
    try:
        records = scraper.discover(limit=discover_limit)
        count = len(records)
        print(f"   discover() returned {count} records")
        if expected_count:
            pct = count / expected_count * 100 if expected_count else 0
            print(f"   Expected: ~{expected_count} ({pct:.1f}% coverage)")
        results["checks"]["discovery"] = {
            "status": "ok",
            "count": count,
            "expected": expected_count,
        }
    except Exception as e:
        print(f"   FAILED: {e}")
        results["checks"]["discovery"] = {"status": "error", "error": str(e)}
        _save_results(domain, results)
        return results

    # --- Check 2: Sample record inspection ---
    print("\n2. Sample record inspection")
    step = max(1, len(records) // 5)
    samples = records[0::step][:5]
    for i, rec in enumerate(samples):
        doc_count = len(rec.doc_urls)
        meta_keys = list(rec.metadata.keys())
        print(f"   [{i+1}] {rec.title[:70]}")
        print(f"       URL: {rec.page_url}")
        print(f"       docs: {doc_count}, metadata: {meta_keys}")
    results["checks"]["samples"] = {
        "status": "ok",
        "count": len(samples),
        "sample_titles": [r.title[:80] for r in samples],
    }

    # --- Check 3: Document URL validation ---
    print("\n3. Document URL validation")
    url_samples = []
    for rec in samples:
        if rec.doc_urls:
            url_samples.append(rec.doc_urls[0])
    if not url_samples:
        # Try to find any record with doc_urls
        for rec in records[:50]:
            if rec.doc_urls:
                url_samples.append(rec.doc_urls[0])
                if len(url_samples) >= 5:
                    break

    valid = 0
    for url in url_samples[:5]:
        info = scraper.head(url)
        if info and info["status"] == 200:
            ct = info["content_type"]
            size = info["content_length"]
            print(f"   OK: {url[:60]}... ({ct}, {size:,} bytes)")
            valid += 1
        else:
            status = info["status"] if info else "no response"
            print(f"   FAIL: {url[:60]}... (status: {status})")

    results["checks"]["url_validation"] = {
        "status": "ok" if valid == len(url_samples[:5]) else "warning",
        "valid": valid,
        "tested": len(url_samples[:5]),
    }

    # --- Check 4: Coverage estimate ---
    print("\n4. Coverage estimate")
    if expected_count:
        pct = count / expected_count * 100
        status = "ok" if pct >= 90 else "warning"
        print(f"   Discovered {count} vs expected ~{expected_count} ({pct:.1f}%)")
        if pct < 90:
            print(f"   WARNING: coverage below 90% — investigate missing documents")
    else:
        status = "info"
        print(f"   No estimated_count in config — cannot assess coverage")
        print(f"   Discovered: {count}")
    results["checks"]["coverage"] = {
        "status": status,
        "found": count,
        "expected": expected_count,
    }

    # --- Check 5: Duplicate check ---
    print("\n5. Duplicate check")
    unique_pages = len(set(r.page_url for r in records))
    all_doc_urls = [u for r in records for u in r.doc_urls]
    unique_docs = len(set(all_doc_urls))
    dup_pages = count - unique_pages
    dup_docs = len(all_doc_urls) - unique_docs
    print(f"   {unique_pages} unique page URLs ({dup_pages} duplicates)")
    print(f"   {unique_docs} unique doc URLs ({dup_docs} duplicates)")
    results["checks"]["duplicates"] = {
        "status": "ok" if dup_pages == 0 else "warning",
        "unique_pages": unique_pages,
        "duplicate_pages": dup_pages,
        "unique_docs": unique_docs,
        "duplicate_docs": dup_docs,
    }

    # --- Check 6: Multi-document check ---
    print("\n6. Multi-document check")
    multi = [r for r in records if len(r.doc_urls) > 1]
    no_doc = [r for r in records if len(r.doc_urls) == 0]
    max_docs = max((len(r.doc_urls) for r in records), default=0)
    print(f"   {len(multi)} records have multiple documents (max: {max_docs})")
    print(f"   {len(no_doc)} records have no document URLs")
    if multi:
        example = multi[0]
        print(f"   Example: {example.title[:60]} ({len(example.doc_urls)} docs)")
    results["checks"]["multi_document"] = {
        "status": "info",
        "multi_count": len(multi),
        "no_doc_count": len(no_doc),
        "max_docs": max_docs,
    }

    # --- Check 7: Metadata completeness ---
    print("\n7. Metadata completeness")
    all_keys = set()
    for r in records:
        all_keys.update(r.metadata.keys())

    if all_keys:
        for key in sorted(all_keys):
            filled = sum(1 for r in records if r.metadata.get(key))
            pct = filled / count * 100 if count else 0
            print(f"   {key}: {filled}/{count} ({pct:.0f}%)")
    else:
        print(f"   No metadata fields extracted")

    results["checks"]["metadata"] = {
        "status": "ok" if all_keys else "info",
        "fields": {
            key: sum(1 for r in records if r.metadata.get(key))
            for key in sorted(all_keys)
        },
    }

    # --- Summary ---
    print(f"\n=== Summary ===")
    warnings = sum(1 for c in results["checks"].values() if c.get("status") == "warning")
    errors = sum(1 for c in results["checks"].values() if c.get("status") == "error")
    print(f"  Checks: 7  Warnings: {warnings}  Errors: {errors}")

    if warnings == 0 and errors == 0:
        print(f"  All checks passed. Ready to run --phase scrape")
    else:
        print(f"  Review warnings/errors before proceeding")

    _save_results(domain, results)
    return results


def _save_results(domain: str, results: dict):
    """Write checklist results to JSON."""
    out_dir = CORPORA_DIR / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ".checklist_result.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Results: {out_path}")
