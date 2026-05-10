"""Document ingestion pipeline.

Phases:
    check      — run 7-item validation checklist on a domain's scraper
    scrape     — execute scraper: discover + download documents
    convert    — PDF/DOCX → structured markdown
    report     — generate post-scrape diagnostic report

Usage:
    python -m pipeline.ingest --domain anao --phase check
    python -m pipeline.ingest --domain anao --phase scrape [--limit N]
    python -m pipeline.ingest --domain anao --phase convert [--workers N] [--force]
"""

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = ROOT / "domains"
CORPORA_DIR = ROOT / "corpora"


def _load_scraper_class(domain: str):
    """Dynamically import domains/<domain>/scrape.py."""
    scrape_path = DOMAINS_DIR / domain / "scrape.py"
    if not scrape_path.exists():
        raise FileNotFoundError(f"No scrape.py at {scrape_path}")
    spec = importlib.util.spec_from_file_location(f"domains.{domain}.scrape", scrape_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Scraper


def main():
    parser = argparse.ArgumentParser(
        description="Document ingestion pipeline",
        usage="python -m pipeline.ingest --domain <name> --phase <phase> [options]",
    )
    parser.add_argument("--domain", required=True, help="Domain name (e.g. anao)")
    parser.add_argument("--phase", required=True,
                        choices=["check", "scrape", "convert", "report"],
                        help="Ingestion phase")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only first N items")
    parser.add_argument("--workers", type=int, default=None,
                        help="(convert) Number of parallel workers")
    parser.add_argument("--force", action="store_true",
                        help="(convert) Re-convert even if output exists")
    parser.add_argument("--discover-only", action="store_true",
                        help="(scrape) Discover URLs only, don't download")
    parser.add_argument("--rate-limit", type=float, default=None,
                        help="Seconds between requests (overrides config)")
    args = parser.parse_args()

    # Ensure directories exist
    domain_dir = DOMAINS_DIR / args.domain
    if not domain_dir.exists():
        domain_dir.mkdir(parents=True)
        print(f"Created domain directory: {domain_dir}")
    (CORPORA_DIR / args.domain).mkdir(parents=True, exist_ok=True)

    if args.phase == "check":
        from pipeline.ingest.checklist import run_checklist
        run_checklist(args.domain, discover_limit=args.limit)

    elif args.phase == "scrape":
        ScraperCls = _load_scraper_class(args.domain)

        # Load rate limit from config if not overridden
        import yaml
        rate = args.rate_limit
        if rate is None:
            domain_yaml = domain_dir / "domain.yaml"
            if domain_yaml.exists():
                with open(domain_yaml) as f:
                    raw = yaml.safe_load(f) or {}
                rate = raw.get("source", {}).get("rate_limit_seconds", 1.0)
            else:
                rate = 1.0

        scraper = ScraperCls(args.domain, rate_limit=rate)
        scraper.run(limit=args.limit, discover_only=args.discover_only)

    elif args.phase == "convert":
        from pipeline.ingest.convert import run_convert
        run_convert(args.domain, workers=args.workers, force=args.force,
                    limit=args.limit)

    elif args.phase == "report":
        from pipeline.ingest.report import generate_report
        generate_report(args.domain)


if __name__ == "__main__":
    main()
