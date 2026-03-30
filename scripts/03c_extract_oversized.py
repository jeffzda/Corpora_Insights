#!/usr/bin/env python3
"""
Step 3c: Extract delivery insight records from the 8 oversized documents
that were skipped by 03b (>600k chars, exceeding single-call context limits).

Strategy: chunk each document into ~150k-char segments and make one API call
per chunk. Each call receives a compact list of records already extracted from
earlier chunks so the model can avoid duplicates and track its position in the
document.

ID allocation:
    Oversized docs use a reserved range starting at ARENA-DLV-72001,
    well above the 03b ceiling of 1440 × 50 = 72000.
    Each oversized doc gets 200 slots (generous ceiling — no hard cap).

    doc_0001 → ARENA-DLV-72001 to ARENA-DLV-72200
    doc_0011 → ARENA-DLV-72201 to ARENA-DLV-72400
    ... etc.

Usage:
    python scripts/03c_extract_oversized.py               # all 8 docs
    python scripts/03c_extract_oversized.py --docs 1,3    # by position in list (1-indexed)
    python scripts/03c_extract_oversized.py --resume      # skip docs with output already
    python scripts/03c_extract_oversized.py --dry-run     # print first chunk prompt, no API call

Outputs:
    insights/per_doc/doc_NNNN.yaml   (same format as 03b outputs)
"""

import argparse
import html as html_module
import json
import re
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed. Run: pip install anthropic")

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

import csv

ROOT = Path(__file__).resolve().parents[1]
GROUPS_FILE   = ROOT / "all_agent_groups_v2.json"
PROMPT_FILE   = ROOT / "pilot_100_reports" / "EXTRACTION_PROMPT.md"
TAXONOMY_FILE = ROOT / "ARENA_Taxonomy_v1.3.md"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
OUT_DIR       = ROOT / "insights" / "per_doc"

MODEL          = "claude-sonnet-4-6"
MAX_TOKENS     = 64000
CHUNK_SIZE     = 150_000   # chars per chunk
CHUNK_OVERLAP  = 500       # chars of trailing context carried into next chunk
IDS_PER_DOC    = 200       # generous slot ceiling per oversized doc
ID_BASE        = 72001     # first ID in the oversized reserved range

MAX_RETRIES    = 4
RETRY_DELAYS   = [10, 30, 60, 120]

# ---------------------------------------------------------------------------
# Oversized doc list — doc numbers (1-indexed) within all_agent_groups_v2.json
# Each entry: (doc_num, approximate_size_chars)
# ---------------------------------------------------------------------------
OVERSIZED_DOCS = [
    1,    # Australian Energy Resource Assessment 2014          — 1.3M chars
    11,   # Stocktake: Database of Renewable Energy Grid Integration Projects — 1.2M chars
    21,   # AEMO Project EDGE Final Report                      — 1.0M chars
    30,   # ESCRI South Australia General Project Report Phase 1 — 803k chars
    39,   # 2024 Annual Report – ACAP                           — 751k chars
    49,   # 2022 Annual Report – ACAP                           — 642k chars
    59,   # 2016 Annual Report – ACAP                           — 634k chars
    69,   # 2023 Annual Report – ACAP                           — 604k chars
]


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
    seen, docs = set(), []
    for group in groups:
        for doc in group:
            mp = doc.get("md_path", "")
            if mp and mp not in seen:
                seen.add(mp)
                docs.append(doc)
    return docs


def load_portfolio() -> dict[str, dict]:
    if not PROJECTS_FILE.exists():
        return {}
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return {normalise_project_name(row["Project"]): row
                for row in csv.DictReader(f)}


def load_prompt_template() -> str:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    # Load taxonomy and inject
    if TAXONOMY_FILE.exists():
        taxonomy = TAXONOMY_FILE.read_text(encoding="utf-8")
        text = text.replace("[TAXONOMY_CONTENT]", taxonomy)
    section_end = text.find("## How the prompt is used")
    section = text[:section_end] if section_end != -1 else text
    header_pos = section.find("## Prompt template")
    open_fence = section.find("```", header_pos)
    if open_fence == -1:
        return text
    content_start = section.index("\n", open_fence) + 1
    close_fence = section.rfind("```")
    return section[content_start:close_fence].strip()


def split_into_chunks(content: str) -> list[str]:
    """
    Split content into CHUNK_SIZE segments, breaking at paragraph boundaries
    (double newlines) where possible. Carries CHUNK_OVERLAP chars of trailing
    context into the start of the next chunk so the model doesn't miss records
    that straddle a split point.
    """
    chunks = []
    pos = 0
    while pos < len(content):
        end = min(pos + CHUNK_SIZE, len(content))
        if end < len(content):
            # Try to break at a paragraph boundary within the last 2000 chars
            boundary = content.rfind("\n\n", end - 2000, end)
            if boundary > pos:
                end = boundary + 2
        chunk = content[pos:end]
        chunks.append(chunk)
        # Next chunk starts CHUNK_OVERLAP chars before the end of this chunk
        # so we don't miss cross-boundary records
        pos = end - CHUNK_OVERLAP if end < len(content) else end
    return chunks


def format_prior_records(records: list[dict]) -> str:
    """
    Compact representation of records already extracted from earlier chunks.
    Gives the model enough context to avoid duplicates and track document position.
    """
    if not records:
        return "(none yet)"
    lines = []
    for r in records:
        rid = r.get("record_id", "?")
        what = r.get("what_happened", "")[:120].replace("\n", " ")
        lines.append(f"- {rid}: {what}")
    return "\n".join(lines)


def build_chunk_prompt(
    doc: dict,
    chunk_text: str,
    chunk_num: int,
    total_chunks: int,
    start_id: int,
    prior_records: list[dict],
    prompt_template: str,
) -> str:
    title = doc.get("Title", "Unknown")
    kb_url = doc.get("Link to item", "")
    md_name = Path(doc.get("md_path", "")).name

    prior_section = (
        f"\n\n--- RECORDS ALREADY EXTRACTED (earlier chunks — do not re-extract these) ---\n"
        f"{format_prior_records(prior_records)}\n"
        f"--- END OF PRIOR RECORDS ---\n"
    )

    doc_section = (
        f"--- DOCUMENT (chunk {chunk_num} of {total_chunks}) ---\n"
        f"Title: {title}\n"
        f"KB URL: {kb_url}\n"
        f"Markdown filename: {md_name}\n"
        f"{prior_section}\n"
        f"--- DOCUMENT TEXT (chunk {chunk_num}/{total_chunks}) ---\n"
        f"{chunk_text}"
    )

    prompt = prompt_template
    prompt = prompt.replace(
        "[Document list and markdown content appended by the orchestrating script]",
        doc_section,
    )
    prompt = prompt.replace(
        "Start record_id numbering at ARENA-DLV-[START_ID].",
        f"Start record_id numbering at ARENA-DLV-{start_id:04d}. "
        f"This is chunk {chunk_num} of {total_chunks} — only extract records from the text "
        f"in this chunk. Skip anything already in the prior-records list above.",
    )
    return prompt


def call_api(client: anthropic.Anthropic, prompt: str, label: str) -> str:
    """Call Claude API with retry. Always streams (max_tokens > 8192)."""
    for attempt in range(MAX_RETRIES):
        try:
            full_text = ""
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    print(text, end="", flush=True)
            print()
            return full_text
        except anthropic.RateLimitError:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"\n  [{label}] Rate limit — waiting {delay}s...")
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                print(f"\n  [{label}] Server error {e.status_code} — waiting {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"[{label}] API failed after {MAX_RETRIES} attempts")


def parse_yaml_response(response: str, label: str) -> list[dict]:
    """Extract YAML records from API response text."""
    # Strip markdown fences
    text = re.sub(r'^```(?:yaml)?\s*', '', response.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)

    # Find first record start
    first = re.search(r'^- record_id:', text, re.MULTILINE)
    if not first:
        return []
    text = text[first.start():]

    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, list):
            return [r for r in parsed if isinstance(r, dict) and r.get("record_id")]
    except yaml.YAMLError as e:
        print(f"  [{label}] YAML parse error: {e}")

    return []


def find_source_page(doc: dict, evidence_excerpt: str | None) -> int | None:
    if not PYMUPDF_AVAILABLE or not evidence_excerpt:
        return None
    local_path = doc.get("local_path", "")
    if not local_path:
        return None
    pdf_path = ROOT / local_path
    if not pdf_path.exists():
        return None
    search_text = evidence_excerpt[:120].strip()
    try:
        pdf = fitz.open(str(pdf_path))
        for page_num, page in enumerate(pdf, 1):
            if page.search_for(search_text):
                pdf.close()
                return page_num
        pdf.close()
    except Exception:
        pass
    return None


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
        record["source_page_pdf"]      = find_source_page(doc, record.get("evidence_excerpt"))
    return records


def process_doc(doc_num: int, doc: dict, id_start: int,
                portfolio: dict, prompt_template: str,
                client: anthropic.Anthropic, dry_run: bool) -> list[dict]:
    """
    Chunk and extract records from one oversized document.
    Returns the full list of stamped canonical records.
    """
    title = doc.get("Title", "Unknown")[:70]
    md_path = ROOT / doc.get("md_path", "")
    content = md_path.read_text(encoding="utf-8", errors="replace")
    chunks = split_into_chunks(content)

    print(f"\n  {len(content):,} chars → {len(chunks)} chunks")

    all_records: list[dict] = []
    seen_ids: set[str] = set()
    next_id = id_start

    for i, chunk in enumerate(chunks, 1):
        label = f"doc_{doc_num:04d} chunk {i}/{len(chunks)}"
        print(f"\n  --- {label} ({len(chunk):,} chars, next_id=ARENA-DLV-{next_id:04d}) ---")

        prompt = build_chunk_prompt(
            doc, chunk, i, len(chunks), next_id, all_records, prompt_template
        )

        if dry_run:
            print(f"  DRY RUN — prompt length {len(prompt):,} chars")
            print(prompt[:1000])
            print("  ...")
            if i == 1:
                break
            continue

        response = call_api(client, prompt, label)
        new_records = parse_yaml_response(response, label)

        added = 0
        for r in new_records:
            rid = r.get("record_id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                all_records.append(r)
                added += 1
                # Advance next_id past whatever the model used
                m = re.search(r'(\d+)$', rid)
                if m:
                    next_id = max(next_id, int(m.group(1)) + 1)

        print(f"  +{added} new records (total so far: {len(all_records)})")

    if not dry_run and all_records:
        stamp_records(all_records, doc, portfolio)

    return all_records


def main():
    parser = argparse.ArgumentParser(
        description="Extract delivery insight records from oversized KB documents"
    )
    parser.add_argument(
        "--docs", type=str, default=None,
        help="Positions in the oversized list to process (1-indexed, e.g. '1,3' or '2-5'). "
             "Default: all 8."
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip docs that already have a per_doc output file."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print first chunk prompt and exit without calling API."
    )
    args = parser.parse_args()

    # Resolve which oversized docs to process
    positions = list(range(1, len(OVERSIZED_DOCS) + 1))
    if args.docs:
        positions = []
        for part in args.docs.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                positions.extend(range(int(a), int(b) + 1))
            else:
                positions.append(int(part))
        positions = [p for p in positions if 1 <= p <= len(OVERSIZED_DOCS)]

    print("Loading document list...")
    docs = load_documents()
    print(f"  {len(docs)} documents")

    print("Loading portfolio...")
    portfolio = load_portfolio()
    print(f"  {len(portfolio)} portfolio projects")

    print("Loading prompt template...")
    prompt_template = load_prompt_template()

    client = None if args.dry_run else anthropic.Anthropic()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for pos in positions:
        doc_num = OVERSIZED_DOCS[pos - 1]
        doc = docs[doc_num - 1]
        title = doc.get("Title", "Unknown")[:70]
        out_path = OUT_DIR / f"doc_{doc_num:04d}.yaml"
        id_start = ID_BASE + (pos - 1) * IDS_PER_DOC

        print(f"\n{'='*70}")
        print(f"[{pos}/{len(OVERSIZED_DOCS)}] doc_{doc_num:04d}: {title}")
        print(f"  ID range: ARENA-DLV-{id_start:05d} to ARENA-DLV-{id_start+IDS_PER_DOC-1:05d}")

        if args.resume and out_path.exists():
            print(f"  SKIP: output already exists ({out_path.name})")
            continue

        md_path = ROOT / doc.get("md_path", "")
        if not md_path.exists():
            print(f"  SKIP: markdown not found at {md_path}")
            continue

        records = process_doc(
            doc_num, doc, id_start, portfolio, prompt_template,
            client, args.dry_run
        )

        if args.dry_run:
            continue

        if records:
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
            print(f"\n  Written: {out_path.name} ({len(records)} records)")
        else:
            print(f"\n  No records extracted — no output file written")

    print("\nDone.")


if __name__ == "__main__":
    main()
