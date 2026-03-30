#!/usr/bin/env python3
"""
Stamp KB metadata onto the 34 recovered YAML files that were missing it.

These files were reconstructed from raw error outputs and never had their
kb_associated_project, source_url, pdf_url, etc. fields stamped by the
normal stamp_and_save path in 03b_extract_registry_per_doc.py.

This script:
- Loads the same document list (from all_agent_groups_v2.json) used during extraction
- Identifies the 34 files missing kb_associated_project
- Stamps KB metadata onto each record
- Rewrites the YAML files in-place
"""
import csv
import html as html_module
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GROUPS_FILE = ROOT / "all_agent_groups_v2.json"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
OUT_DIR = ROOT / "insights" / "per_doc"


def normalise_project_name(name: str) -> str:
    name = html_module.unescape(name)
    name = re.sub(r'<[^>]+>', '', name)
    name = name.replace('\u2013', "'").replace('\u2014', "'")
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')
    return name.strip()


def load_documents() -> list[dict]:
    with open(GROUPS_FILE, encoding="utf-8") as f:
        groups = json.load(f)
    seen_paths = set()
    docs = []
    for group in groups:
        for doc in group:
            md_path = doc.get("md_path", "")
            if not md_path or md_path in seen_paths:
                continue
            seen_paths.add(md_path)
            docs.append(doc)
    return docs


def load_portfolio() -> dict[str, dict]:
    if not PROJECTS_FILE.exists():
        return {}
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return {normalise_project_name(row["Project"]): row
                for row in csv.DictReader(f)}


def stamp_records(records: list[dict], doc: dict, portfolio: dict) -> list[dict]:
    kb_proj = doc.get("Associated project name") or ""
    portfolio_row = portfolio.get(normalise_project_name(kb_proj)) if kb_proj else None

    for record in records:
        record["source_url"]           = doc.get("Link to item") or None
        record["project_page_url"]     = doc.get("Link to project page") or None
        record["kb_category"]          = doc.get("Category") or None
        record["kb_publish_date"]      = doc.get("Publish date") or None
        record["kb_year"]              = doc.get("Year") or None
        record["kb_associated_project"] = kb_proj or None
        record["kb_document_type"]     = doc.get("Type") or None
        local_path = doc.get("local_path", "")
        record["kb_document_folder"]   = Path(local_path).parent.name if local_path else None
        record["kb_project_status"]    = doc.get("Project Status") or None
        record["in_arena_portfolio"]   = portfolio_row is not None
        record["arena_funding"]        = portfolio_row.get("Arena funding provided") or None if portfolio_row else None
        record["total_project_value"]  = portfolio_row.get("Total project value") or None if portfolio_row else None
        record["lead_organisation"]    = portfolio_row.get("Lead organisation") or None if portfolio_row else None
        record["arena_program"]        = portfolio_row.get("Arena program") or None if portfolio_row else None
        record["project_status"]       = portfolio_row.get("Status") or None if portfolio_row else None
        record["project_start_date"]   = portfolio_row.get("Start date") or None if portfolio_row else None
        record["location"]             = portfolio_row.get("Location") or None if portfolio_row else None
        record["project_partners"]     = portfolio_row.get("Project partners") or None if portfolio_row else None
        record["pdf_url"]              = doc.get("pdf_url") or None
        doc_md_path = doc.get("md_path", "")
        record["markdown_filename"]    = Path(doc_md_path).name if doc_md_path else None
        # source_page_pdf left as-is (null) — would need PyMuPDF re-run to populate
    return records


def main():
    print("Loading document list...")
    docs = load_documents()
    print(f"  {len(docs)} documents")

    print("Loading portfolio...")
    portfolio = load_portfolio()
    print(f"  {len(portfolio)} portfolio projects")

    # Find files missing kb_associated_project
    to_stamp = []
    for path in sorted(OUT_DIR.glob("doc_*.yaml")):
        content = path.read_text(encoding="utf-8")
        if "kb_associated_project" not in content:
            to_stamp.append(path)

    print(f"\nFiles missing kb_associated_project: {len(to_stamp)}")

    stamped = skipped = 0
    for path in to_stamp:
        # Extract doc number from filename
        m = re.match(r'doc_(\d+)\.yaml', path.name)
        if not m:
            print(f"  SKIP: can't parse doc number from {path.name}")
            skipped += 1
            continue

        doc_num = int(m.group(1))
        if doc_num < 1 or doc_num > len(docs):
            print(f"  SKIP: doc_num {doc_num} out of range (have {len(docs)} docs)")
            skipped += 1
            continue

        doc = docs[doc_num - 1]
        kb_proj = doc.get("Associated project name") or ""
        title = doc.get("Title", "")[:60]

        # Load records
        with open(path, encoding="utf-8") as f:
            records = yaml.safe_load(f)

        if not isinstance(records, list) or not records:
            print(f"  SKIP {path.name}: empty or non-list YAML")
            skipped += 1
            continue

        # Stamp
        records = stamp_records(records, doc, portfolio)

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)

        in_portfolio = records[0].get("in_arena_portfolio", False)
        print(f"  {path.name}: {len(records)} records → '{kb_proj}' "
              f"({'in portfolio' if in_portfolio else 'NOT in portfolio'})  [{title}]")
        stamped += 1

    print(f"\nDone. Stamped: {stamped}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
