#!/usr/bin/env python3
"""
Step 3b: Extract delivery insight records one document at a time via Anthropic API.

Replaces 03_extract_registry.py. Processes each document individually rather than
grouping ~10 documents per call, eliminating the 80k character truncation that
affected 315 of 1,448 documents in the original run.

Key differences from 03_extract_registry.py:
  - One API call per document (not per group of ~10)
  - No per-document character truncation
  - 10 ID slots per document (vs 50 per group)
  - max_tokens raised to 4096 (full budget for one document's records)
  - Documents over 600k chars are skipped (6 oversized reference docs that
    exceed the model's context window — see SKIPPED_DOCS below)

Reads:
  all_agent_groups_v2.json      — source of document list and md_paths
  pilot_100_reports/EXTRACTION_PROMPT.md — extraction prompt template
  pilot_100_reports/taxonomy/ARENA_Taxonomy_v1.1.md — taxonomy (embedded in prompt)
  manifest.csv local_path column — used to stamp kb_document_folder on each record

Outputs (one file per document, resumable):
  insights/per_doc/doc_0001.yaml ... doc_1442.yaml

Usage:
    python scripts/03b_extract_registry_per_doc.py
    python scripts/03b_extract_registry_per_doc.py --docs 1-10    # range
    python scripts/03b_extract_registry_per_doc.py --docs 1       # single doc
    python scripts/03b_extract_registry_per_doc.py --resume       # skip completed
    python scripts/03b_extract_registry_per_doc.py --dry-run      # print prompt, no API call

Requires:
    pip install anthropic pyyaml
    export ANTHROPIC_API_KEY=sk-ant-...

ID allocation:
    Document N → record IDs ARENA-DLV-((N-1)*10+1) to ARENA-DLV-(N*10)
    e.g. doc 1 → ARENA-DLV-0001 to ARENA-DLV-0010
         doc 2 → ARENA-DLV-0011 to ARENA-DLV-0020
"""

import argparse
import json
import html as html_module
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
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[1]
GROUPS_FILE = ROOT / "all_agent_groups_v2.json"
PROMPT_FILE = ROOT / "pilot_100_reports" / "EXTRACTION_PROMPT.md"
TAXONOMY_FILE = ROOT / "ARENA_Taxonomy_v1.3.md"
PROJECTS_FILE = ROOT / "arena-projects-export_1772932404.csv"
TABLES_DIR = ROOT / "tables"
OUT_DIR = ROOT / "insights" / "per_doc"

MODEL = "claude-sonnet-4-6"
IDS_PER_DOC = 50       # ID slots per doc — generous ceiling; no record cap applied
MAX_TOKENS = 64000     # full output budget; streaming always engaged (>8192)
MAX_CHARS = 600_000    # docs over this are skipped (exceed context window)

# ---------------------------------------------------------------------------
# Document type filter
#
# Based on analysis of arena-kb-export_1772889492.csv (1,548 documents):
#
#   Type                        Total  Linked  Unlinked%  Decision
#   Reports                       880     749       15%   INCLUDE
#   Reports, Lessons              322     319        1%   INCLUDE  ← highest signal
#   Presentation                   82      24       71%   EXCLUDE  ← poor markdown + mostly unlinked
#   InsightNewsletter              58       0      100%   EXCLUDE  ← ARENA comms, no project link
#   Lessons                        36      34        6%   INCLUDE
#   Reports, Milestones            30      30        0%   INCLUDE
#   Insights                       27      13       52%   INCLUDE  ← borderline; keep, low cost
#   Infographics                   25      22       12%   INCLUDE  ← small volume, mostly linked
#   Reports, Insights              22       8       64%   INCLUDE  ← borderline; keep, low cost
#   Videos                         17       0      100%   EXCLUDE  ← markdown from video = garbage
#   Reports, Guides                10      10        0%   INCLUDE
#   Insights, InsightNewsletter     4       0      100%   EXCLUDE
#   Podcast                         4       0      100%   EXCLUDE
#   Insights, Videos                3       0      100%   EXCLUDE
#   (others <3 docs each)                           —    INCLUDE  ← too small to matter
#
# Exclusion rationale:
#   - InsightNewsletter / Podcast / Videos / Insights,Videos: zero project linkage,
#     no delivery content, markdown conversion of non-text media is low quality
#   - Presentation: 71% unlinked, slide decks convert poorly to markdown, linked
#     presentations are typically superseded by a full report in the same KB entry
#   - Insights,InsightNewsletter: same as InsightNewsletter
#
# To revisit: if a future KB export shows Presentations gaining project links, or
# if linked Presentations are found to yield high-quality records in QC, remove
# "Presentation" from this set.
#
# ~160 documents skipped by this filter → saves ~$0.60 API cost and avoids
# polluting the registry with low-signal records.
# ---------------------------------------------------------------------------
EXCLUDED_DOC_TYPES = {
    "InsightNewsletter",
    "Insights, InsightNewsletter",
    "Videos",
    "Insights, Videos",
    "Reports, Videos",
    "Podcast",
    "Presentation",
    "Lessons, Presentation",
    "Insights, Presentation",
}

# ---------------------------------------------------------------------------
# KB data quality overrides
#
# These documents are misattributed in the KB export — the kb_associated_project
# field points to the wrong ARENA project. Keyed by 1-based document index
# (position in the deduplicated list from all_agent_groups_v2.json).
#
# Each entry maps to a dict of field overrides applied after KB stamping.
# Use kb_associated_project: null to break the wrong project association.
#
# Known misattributions:
#   doc_0299 — RMIT solar hydrogen poster tagged as "30MW Concentrating Solar Thermal
#              Power Plant" (wrong project entirely)
#   doc_1278 — UQ Gatton 3.3MW PV connection review tagged as "AGL Solar Project"
#              (likely nearest available project under the Australian Solar Institute
#              program at the time of KB curation; UQ Gatton is a separate project)
# ---------------------------------------------------------------------------
KB_OVERRIDES: dict[int, dict] = {
    299: {
        "kb_associated_project": None,
        "project_page_url": None,
        "in_arena_portfolio": False,
        "arena_funding": None,
        "total_project_value": None,
        "lead_organisation": None,
        "arena_program": None,
        "project_status": None,
        "project_start_date": None,
        "location": None,
        "project_partners": None,
    },
    1278: {
        "kb_associated_project": None,
        "project_page_url": None,
        "in_arena_portfolio": False,
        "arena_funding": None,
        "total_project_value": None,
        "lead_organisation": None,
        "arena_program": None,
        "project_status": None,
        "project_start_date": None,
        "location": None,
        "project_partners": None,
    },
}

MAX_RETRIES = 5
RETRY_BASE_DELAY = 10  # seconds


def find_document_tables(local_path: str) -> list:
    """Find extracted table CSVs for a document via the shared 6-char hash.

    Naming convention: <DocName>_<hash>_p<page>_t<index>.csv
    The hash is extracted from the PDF local_path, e.g.:
      local_path: pdfs/Reports/Ballarat_BESS__Knowledge_Sharing_Report_aacad5.pdf
      tables:     Ballarat_BESS__Knowledge_Sharing_Report_aacad5_p006_t00.csv

    Only returns root-level tables (excludes noise/, broken/, merged/ subdirs).
    """
    if not TABLES_DIR.exists():
        return []
    m = re.search(r'_([a-f0-9]{6})\.pdf$', local_path)
    if not m:
        return []
    doc_hash = m.group(1)
    return sorted(TABLES_DIR.glob(f'*_{doc_hash}_p*_t*.csv'))


def normalise_project_name(name: str) -> str:
    """Normalise project name for matching: decode HTML entities, strip tags, normalise quotes."""
    name = html_module.unescape(name)
    name = re.sub(r'<[^>]+>', '', name)
    name = name.replace('\u2013', "'").replace('\u2014', "'")  # en/em dash → apostrophe (matches portfolio encoding)
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')
    return name.strip()


def load_portfolio() -> dict[str, dict]:
    """Load the full ARENA project portfolio, keyed by normalised project name.

    Returns a dict of normalised_name → project row, enabling both coverage
    flagging (in_arena_portfolio) and metadata enrichment (funding, lead org, etc).
    """
    if not PROJECTS_FILE.exists():
        return {}
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return {normalise_project_name(row["Project"]): row
                for row in __import__("csv").DictReader(f)}


def load_documents(source: str | None = None) -> list[dict]:
    """Load the document list for extraction.

    Default (source=None): flattens all_agent_groups_v2.json, deduplicating
    by md_path.

    Alternate source (e.g. insights/newsletter_manifest.json): loads a flat
    JSON list of doc dicts directly — used for newsletters and other
    supplementary corpora that are not in the main groups file.
    """
    if source:
        source_path = Path(source) if Path(source).is_absolute() else ROOT / source
        with open(source_path, encoding="utf-8") as f:
            docs = json.load(f)
        # Deduplicate by md_path in case of re-runs
        seen, unique = set(), []
        for doc in docs:
            mp = doc.get("md_path", "")
            if mp and mp not in seen:
                seen.add(mp)
                unique.append(doc)
        return unique

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


def load_prompt_template() -> tuple[str, str]:
    """Load extraction prompt and taxonomy, returning (prompt_template, taxonomy_text).

    The prompt template is wrapped in an outer ``` fence which itself contains a
    nested ```yaml example block. A simple non-greedy regex stops at the inner
    fence, so we instead find the opening fence and use rfind to locate the final
    closing fence before the 'How the prompt is used' section.

    The taxonomy is loaded from TAXONOMY_FILE and injected at the [TAXONOMY_CONTENT]
    placeholder within the prompt template.
    """
    text = PROMPT_FILE.read_text(encoding="utf-8")

    # Find the section boundary so we don't accidentally grab later fences
    section_end = text.find("## How the prompt is used")
    section = text[:section_end] if section_end != -1 else text

    # Find the opening ``` after "## Prompt template"
    header_pos = section.find("## Prompt template")
    open_fence = section.find("```", header_pos)
    if open_fence == -1:
        return text, ""  # fallback

    # Content starts after the opening fence line
    content_start = section.index("\n", open_fence) + 1

    # Closing fence is the last ``` in the section
    close_fence = section.rfind("```")
    if close_fence <= open_fence:
        return text, ""

    prompt_template = section[content_start:close_fence].strip()

    # Load and inject taxonomy
    taxonomy_text = TAXONOMY_FILE.read_text(encoding="utf-8") if TAXONOMY_FILE.exists() else ""
    if not taxonomy_text:
        print(f"WARNING: taxonomy file not found at {TAXONOMY_FILE}")
    prompt_template = prompt_template.replace("[TAXONOMY_CONTENT]", taxonomy_text)

    return prompt_template, taxonomy_text


def build_prompt(doc: dict, start_id: int, prompt_template: str,
                 skip_type_filter: bool = False) -> str | None:
    """
    Build the prompt for a single document.
    Returns None if the document should be skipped (missing file or oversized).

    skip_type_filter: bypass EXCLUDED_DOC_TYPES — used when processing an
    alternate source (e.g. newsletters) that was deliberately scraped despite
    being an otherwise-excluded type.
    """
    md_path = doc.get("md_path", "")
    title = doc.get("Title", Path(md_path).stem if md_path else "Unknown")
    kb_url = doc.get("Link to item", "")

    if not md_path or not Path(md_path).exists():
        print(f"  SKIP: markdown not found for '{title}'")
        return None

    doc_type = doc.get("Type", "").strip()
    if not skip_type_filter and doc_type in EXCLUDED_DOC_TYPES:
        print(f"  SKIP: document type '{doc_type}' excluded from extraction")
        return None

    content = Path(md_path).read_text(encoding="utf-8", errors="replace")

    if len(content) > MAX_CHARS:
        print(f"  SKIP: '{title}' is {len(content):,} chars (over {MAX_CHARS:,} limit)")
        return None

    doc_section = (
        f"--- DOCUMENT ---\n"
        f"Title: {title}\n"
        f"KB URL: {kb_url}\n"
        f"Markdown filename: {Path(md_path).name}\n\n"
        f"{content}"
    )

    # Append extracted table CSVs for this document (linked via 6-char hash)
    tables = find_document_tables(doc.get("local_path", ""))
    if tables:
        table_blocks = []
        total_chars = 0
        for tbl in tables:
            if total_chars > 40_000:   # cap to prevent context overflow on table-heavy docs
                break
            txt = tbl.read_text(encoding="utf-8", errors="replace").strip()
            if len(txt) < 30:          # skip trivially empty tables
                continue
            pm = re.search(r'_p(\d+)_t(\d+)\.csv$', tbl.name)
            label = f"page {int(pm.group(1))}, table {int(pm.group(2))}" if pm else tbl.stem
            table_blocks.append(f"### Extracted table ({label})\n```\n{txt}\n```")
            total_chars += len(txt)
        if table_blocks:
            doc_section += (
                "\n\n## Extracted tables from this document\n\n"
                + "\n\n".join(table_blocks)
            )
            print(f"  Tables: {len(table_blocks)} injected ({total_chars:,} chars)")

    # Inject document content and record_id start into prompt template
    prompt = prompt_template
    prompt = prompt.replace(
        "[Document list and markdown content appended by the orchestrating script]",
        doc_section,
    )
    prompt = prompt.replace(
        "Start record_id numbering at ARENA-DLV-[START_ID].",
        f"Start record_id numbering at ARENA-DLV-{start_id:04d}.",
    )

    return prompt


def call_api(client: anthropic.Anthropic, prompt: str, doc_num: int, max_tokens: int = MAX_TOKENS) -> str:
    """Call Claude API with retry on rate limit / server errors.
    Uses streaming for large max_tokens values (required by SDK for >10 min operations).
    Returns (response_text, input_tokens, output_tokens).
    """
    use_streaming = max_tokens > 8192

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_streaming:
                with client.messages.stream(
                    model=MODEL,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    msg = stream.get_final_message()
                    usage = msg.usage
                    return msg.content[0].text, usage.input_tokens, usage.output_tokens
            else:
                message = client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                usage = message.usage
                return message.content[0].text, usage.input_tokens, usage.output_tokens
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  Rate limit (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s: {e}")
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"  Server error {e.status_code} (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"Doc {doc_num}: API failed after {MAX_RETRIES} attempts")


def parse_yaml_response(response: str, doc_num: int, out_dir: Path = OUT_DIR) -> list[dict]:
    """Extract YAML records from model response, handling common formatting issues."""
    # Detect explicit no-records response before attempting YAML parse
    no_record_phrases = [
        "no records extracted",
        "no delivery insight records",
        "does not contain delivery insight",
        "no meaningful delivery",
    ]
    if any(p in response.lower() for p in no_record_phrases):
        print(f"  No delivery records in this document (model confirmed)")
        return []

    yaml_match = re.search(r"```(?:yaml)?\s*(.*?)```", response, re.DOTALL)
    if yaml_match:
        yaml_text = yaml_match.group(1).strip()
        truncated = False
    else:
        # No closing fence — response was likely truncated at token limit.
        # Strip the opening fence line if present and attempt to parse what we have.
        yaml_text = re.sub(r"^```(?:yaml)?\s*\n?", "", response.strip())
        truncated = True

    # Fix common issue: unquoted colons in string values
    yaml_text = re.sub(
        r'^(\s*\w[\w_]*:\s+)([^"\n]*:[^"\n]*)$',
        lambda m: m.group(1) + '"' + m.group(2).replace('"', '\\"') + '"',
        yaml_text,
        flags=re.MULTILINE,
    )

    try:
        records = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        if truncated:
            # Truncated mid-record — walk back to last complete record boundary (a "- record_id:" line)
            lines = yaml_text.splitlines()
            cut = 0
            for i in range(len(lines) - 1, 0, -1):
                if re.match(r'^- record_id:', lines[i]):
                    cut = i
                    break
            if cut:
                trimmed = "\n".join(lines[:cut])
                try:
                    records = yaml.safe_load(trimmed)
                    print(f"  NOTE: response truncated — recovered records up to line {cut}")
                except yaml.YAMLError as e2:
                    print(f"  WARNING: YAML parse error in doc {doc_num} (truncated): {e2}")
                    raw_path = out_dir / f"doc_{doc_num:04d}_raw_error.txt"
                    raw_path.write_text(response, encoding="utf-8")
                    print(f"  Raw response saved to {raw_path.name}")
                    return []
            else:
                print(f"  WARNING: truncated response with no recoverable records in doc {doc_num}")
                return []
        else:
            print(f"  WARNING: YAML parse error in doc {doc_num}")
            raw_path = out_dir / f"doc_{doc_num:04d}_raw_error.txt"
            raw_path.write_text(response, encoding="utf-8")
            print(f"  Raw response saved to {raw_path.name}")
            return []

    if isinstance(records, list):
        return records
    if isinstance(records, dict) and "records" in records:
        return records["records"]
    print(f"  WARNING: unexpected YAML structure in doc {doc_num}")
    return []


PROJECT_LEVEL_FIELDS = ["project_type", "project_scale_band", "proponent_type"]


def find_source_page(doc: dict, evidence_excerpt: str) -> int | None:
    """
    Search the source PDF for the evidence_excerpt and return the page number (1-indexed).
    Returns None if PyMuPDF is unavailable, the PDF is missing, or the text is not found.
    """
    if not PYMUPDF_AVAILABLE or not evidence_excerpt:
        return None

    local_path = doc.get("local_path", "")
    if not local_path:
        return None

    pdf_path = ROOT / local_path
    if not pdf_path.exists():
        return None

    # Use first 120 chars of excerpt for matching — avoids formatting drift in long quotes
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


def reconcile_project_fields(records: list[dict]) -> list[dict]:
    """
    Enforce consistency of project-level fields across all records from the same document.

    For each of project_type, project_scale_band, and proponent_type:
      - Find the most common non-null value across all records
      - Apply it to every record
      - Append a reconciliation note ONLY to records whose value was actually overridden,
        not to the majority records that already held the winning value. This avoids
        cluttering single-project documents where near-unanimity (e.g. 50/51) is expected.

    This prevents the same document yielding conflicting project classifications
    across its records, which would otherwise require Tier 2 majority-vote cleaning.
    """
    if len(records) <= 1:
        return records

    for field in PROJECT_LEVEL_FIELDS:
        values = [r.get(field) for r in records if r.get(field)]
        if not values:
            continue

        # Count occurrences
        counts: dict[str, int] = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1

        winner = max(counts, key=lambda v: counts[v])
        winner_count = counts[winner]
        total_votes = len(values)
        unanimous = winner_count == total_votes

        if not unanimous:
            # Build a readable vote summary for the confidence_note
            vote_summary = ", ".join(
                f"{v} ({n}/{total_votes})" for v, n in
                sorted(counts.items(), key=lambda x: -x[1])
            )
            note = f"{field} reconciled to '{winner}' from: {vote_summary}"

        for record in records:
            overridden = record.get(field) != winner and record.get(field) is not None
            record[field] = winner
            # Only stamp the note on records that were actually overridden
            if not unanimous and overridden:
                existing = record.get("confidence_note")
                if existing:
                    record["confidence_note"] = f"{existing}; {note}"
                else:
                    record["confidence_note"] = note

    return records


def parse_doc_range(spec: str, total: int) -> list[int]:
    """Parse --docs argument: '1-10', '45', or '1,3,5'."""
    docs = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            docs.extend(range(int(a), int(b) + 1))
        else:
            docs.append(int(part))
    return [d for d in docs if 1 <= d <= total]


BATCH_META_FILE = ROOT / "insights" / "batch_meta.json"
# Sonnet pricing (USD per million tokens)
PRICE_INPUT  = 3.0
PRICE_OUTPUT = 15.0


def stamp_and_save(records: list[dict], doc: dict, doc_num: int,
                   portfolio: dict, out_path: Path) -> None:
    """Stamp KB metadata onto records and write to YAML. Shared by sync and batch paths."""
    records = reconcile_project_fields(records)
    kb_proj = doc.get("Associated project name") or ""
    portfolio_row = portfolio.get(normalise_project_name(kb_proj)) if kb_proj else None

    for record in records:
        record["source_url"]       = doc.get("Link to item") or None
        record["project_page_url"] = doc.get("Link to project page") or None
        record["kb_category"]      = doc.get("Category") or None
        record["kb_publish_date"]  = doc.get("Publish date") or None
        record["kb_year"]          = doc.get("Year") or None
        record["kb_associated_project"] = kb_proj or None
        record["kb_document_type"] = doc.get("Type") or None
        local_path = doc.get("local_path", "")
        record["kb_document_folder"] = Path(local_path).parent.name if local_path else None
        record["kb_project_status"] = doc.get("Project Status") or None
        record["in_arena_portfolio"] = portfolio_row is not None
        record["arena_funding"]      = portfolio_row.get("Arena funding provided") or None if portfolio_row else None
        record["total_project_value"]= portfolio_row.get("Total project value") or None if portfolio_row else None
        record["lead_organisation"]  = portfolio_row.get("Lead organisation") or None if portfolio_row else None
        record["arena_program"]      = portfolio_row.get("Arena program") or None if portfolio_row else None
        record["project_status"]     = portfolio_row.get("Status") or None if portfolio_row else None
        record["project_start_date"] = portfolio_row.get("Start date") or None if portfolio_row else None
        record["location"]           = portfolio_row.get("Location") or None if portfolio_row else None
        record["project_partners"]   = portfolio_row.get("Project partners") or None if portfolio_row else None
        record["pdf_url"]            = doc.get("pdf_url") or None
        doc_md_path = doc.get("md_path", "")
        record["markdown_filename"]  = Path(doc_md_path).name if doc_md_path else None
        record["source_page_pdf"]    = find_source_page(doc, record.get("evidence_excerpt"))

    if doc_num in KB_OVERRIDES:
        for record in records:
            record.update(KB_OVERRIDES[doc_num])
        print(f"  NOTE: KB data quality override applied for doc_{doc_num:04d}")

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(
        description="Extract ARENA delivery insights per document via Anthropic API"
    )
    parser.add_argument("--docs", type=str, default=None,
                        help="Documents to process: '1-1442', '45', '1,3,5'. Default: all.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip documents that already have output files.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print first prompt and exit without calling API.")
    parser.add_argument("--batch", action="store_true",
                        help="Submit as Anthropic Message Batch (50%% discount, async). "
                             "Saves batch ID to insights/batch_meta.json.")
    parser.add_argument("--retrieve", type=str, default=None, metavar="BATCH_ID",
                        help="Retrieve completed batch results and write per_doc YAMLs.")
    parser.add_argument("--source", type=str, default=None,
                        help="Path to an alternate doc manifest JSON (e.g. insights/newsletter_manifest.json). "
                             "Default: all_agent_groups_v2.json. Output files use doc_NNNN.yaml "
                             "numbered from 1 within the source list.")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Output directory for YAML files. Default: insights/per_doc. "
                             "Use a separate directory when running supplementary corpora "
                             "(newsletters, docx) to avoid overwriting main corpus outputs. "
                             "e.g. --out-dir insights/newsletters  or  --out-dir insights/docx")
    args = parser.parse_args()

    # Resolve output directory — default or override
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir and not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = load_documents(source=args.source)
    total = len(docs)
    print(f"Loaded {total} unique documents")
    print(f"Output directory: {out_dir}")

    if args.docs:
        doc_indices = [d - 1 for d in parse_doc_range(args.docs, total)]
    else:
        doc_indices = list(range(total))

    if args.resume:
        doc_indices = [
            i for i in doc_indices
            if not (out_dir / f"doc_{i+1:04d}.yaml").exists()
        ]
        print(f"Resuming: {len(doc_indices)} documents remaining")

    prompt_template, _ = load_prompt_template()
    portfolio = load_portfolio()
    client = anthropic.Anthropic()

    # ------------------------------------------------------------------
    # RETRIEVE mode: download completed batch results → per_doc YAMLs
    # ------------------------------------------------------------------
    if args.retrieve:
        batch_id = args.retrieve
        # Load doc index mapping saved at submission time
        if not BATCH_META_FILE.exists():
            raise SystemExit(f"No batch metadata found at {BATCH_META_FILE}")
        with open(BATCH_META_FILE) as f:
            meta = json.load(f)
        if meta.get("batch_id") != batch_id:
            raise SystemExit(f"batch_meta.json has id {meta.get('batch_id')}, not {batch_id}")

        batch = client.messages.batches.retrieve(batch_id)
        print(f"Batch {batch_id}: {batch.processing_status}")
        if batch.processing_status != "ended":
            print(f"  Not complete yet — request_counts: {batch.request_counts}")
            return

        id_to_docnum = {r["custom_id"]: r["doc_num"] for r in meta["requests"]}
        processed = skipped = 0
        failed_doc_nums = []
        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            doc_num = id_to_docnum.get(custom_id)
            if doc_num is None:
                print(f"  WARNING: unknown custom_id {custom_id}")
                continue
            doc = docs[doc_num - 1]
            out_path = out_dir / f"doc_{doc_num:04d}.yaml"
            title = doc.get("Title", "Unknown")[:60]
            if result.result.type == "errored":
                print(f"  [doc_{doc_num:04d}] ERROR: {result.result.error}")
                failed_doc_nums.append(doc_num)
                skipped += 1
                continue
            response_text = result.result.message.content[0].text
            records = parse_yaml_response(response_text, doc_num, out_dir=out_dir)
            if records:
                stamp_and_save(records, doc, doc_num, portfolio, out_path)
                print(f"  [doc_{doc_num:04d}] {len(records)} records → {out_path.name}  ({title})")
                processed += 1
            else:
                print(f"  [doc_{doc_num:04d}] No records extracted  ({title})")
        print(f"\nDone. Written: {processed}, Errors/empty: {skipped}")
        if failed_doc_nums:
            failed_str = ",".join(str(n) for n in sorted(failed_doc_nums))
            print(f"\nFailed docs — rerun with:")
            print(f"  python3 scripts/03b_extract_registry_per_doc.py --docs {failed_str}")
        return

    # ------------------------------------------------------------------
    # Build prompts (shared by sync and batch modes)
    # ------------------------------------------------------------------
    if not doc_indices:
        print("Nothing to do.")
        return

    requests_to_send = []   # (doc_num, doc, prompt)
    skipped = 0

    for idx in doc_indices:
        doc_num = idx + 1
        doc = docs[idx]
        start_id = idx * IDS_PER_DOC + 1
        title = doc.get("Title", "Unknown")[:70]

        prompt = build_prompt(doc, start_id, prompt_template,
                              skip_type_filter=bool(args.source))
        if prompt is None:
            skipped += 1
            continue

        if args.dry_run:
            print(f"\n--- DRY RUN PROMPT [{doc_num:04d}] (first 2000 chars) ---\n{prompt[:2000]}\n...")
            break

        requests_to_send.append((doc_num, doc, prompt))

    if args.dry_run:
        return

    # ------------------------------------------------------------------
    # BATCH mode: submit all prompts as one Anthropic Message Batch
    # ------------------------------------------------------------------
    if args.batch:
        print(f"\nSubmitting {len(requests_to_send)} requests as Message Batch...")
        batch_requests = [
            {
                "custom_id": f"doc_{doc_num:04d}",
                "params": {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
            }
            for doc_num, doc, prompt in requests_to_send
        ]
        batch = client.messages.batches.create(requests=batch_requests)
        print(f"Batch submitted: {batch.id}")
        print(f"Status: {batch.processing_status}")

        meta = {
            "batch_id": batch.id,
            "submitted_at": batch.created_at.isoformat() if hasattr(batch.created_at, 'isoformat') else str(batch.created_at),
            "request_count": len(batch_requests),
            "requests": [{"custom_id": f"doc_{doc_num:04d}", "doc_num": doc_num}
                         for doc_num, doc, prompt in requests_to_send],
        }
        with open(BATCH_META_FILE, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Metadata saved to {BATCH_META_FILE}")
        print(f"\nTo retrieve when complete:")
        print(f"  python3 scripts/03b_extract_registry_per_doc.py --retrieve {batch.id}")
        return

    # ------------------------------------------------------------------
    # SYNC mode: process documents one at a time
    # ------------------------------------------------------------------
    processed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for doc_num, doc, prompt in requests_to_send:
        out_path = out_dir / f"doc_{doc_num:04d}.yaml"
        title = doc.get("Title", "Unknown")[:70]
        print(f"\n[{doc_num:04d}/{total}] {title}")

        response_text, in_tok, out_tok = call_api(client, prompt, doc_num)
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        cost = (in_tok / 1_000_000 * PRICE_INPUT) + (out_tok / 1_000_000 * PRICE_OUTPUT)
        print(f"  Tokens: {in_tok:,} in / {out_tok:,} out  (${cost:.3f})")

        records = parse_yaml_response(response_text, doc_num, out_dir=out_dir)
        if records:
            stamp_and_save(records, doc, doc_num, portfolio, out_path)
            print(f"  {len(records)} records → {out_path.name}")
            processed += 1
        else:
            print(f"  WARNING: no records extracted for doc {doc_num}")

    total_cost = (total_input_tokens / 1_000_000 * PRICE_INPUT) + (total_output_tokens / 1_000_000 * PRICE_OUTPUT)
    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")
    print(f"Tokens: {total_input_tokens:,} input / {total_output_tokens:,} output")
    print(f"Estimated cost: ${total_cost:.2f} (Sonnet $3/M in, $15/M out)")


if __name__ == "__main__":
    main()
