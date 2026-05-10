#!/usr/bin/env python3
"""Extract taxonomy-agnostic insight records from documents via Anthropic API.

Config-driven extraction that produces rich factual records without taxonomy
labels. Taxonomy is applied as a separate downstream step.

Usage:
    python -m pipeline.extract --domain arena
    python -m pipeline.extract --domain anao
    python -m pipeline.extract --domain arena --docs 1-10
    python -m pipeline.extract --domain arena --resume
    python -m pipeline.extract --domain arena --dry-run
    python -m pipeline.extract --domain arena --batch
    python -m pipeline.extract --domain arena --retrieve BATCH_ID
"""

import argparse
import json
import html as html_module
import re
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10

# Sonnet pricing (USD per million tokens)
PRICE_INPUT = 3.0
PRICE_OUTPUT = 15.0


def get_dirs(cfg):
    """Get output directory for this domain."""
    domain_lower = cfg.domain.name.lower()
    out_dir = ROOT / "runs" / domain_lower / "per_doc"
    if not out_dir.exists() and (ROOT / "insights" / "per_doc").exists():
        out_dir = ROOT / "insights" / "per_doc"
    return out_dir


def normalise_project_name(name):
    """Normalise project name for matching: decode HTML entities, strip tags, normalise quotes."""
    name = html_module.unescape(name)
    name = re.sub(r'<[^>]+>', '', name)
    name = name.replace('\u2013', "'").replace('\u2014', "'")
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')
    return name.strip()


def resolve_md_path(row, md_dir, title_field="Title"):
    """Derive md_path for a catalogue row by matching against markdown directory.

    Tries in order:
    1. Explicit md_path column (if present and file exists)
    2. Title as-is (some corpora use the title directly as filename)
    3. Title slugified with underscores
    4. Partial prefix match as fallback
    """
    # 1. Explicit md_path
    mp = row.get("md_path", "").strip()
    if mp:
        p = Path(mp) if Path(mp).is_absolute() else ROOT / mp
        if p.exists():
            return str(p)

    title = row.get(title_field, row.get("title", "")).strip()
    if not title:
        return None

    # 2. Title as-is (e.g. ANAO uses hyphenated slugs as titles)
    candidate = md_dir / f"{title}.md"
    if candidate.exists():
        return str(candidate)

    # 3. Slugified title (e.g. ARENA uses underscored slugs from PDF names)
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
    candidate = md_dir / f"{slug}.md"
    if candidate.exists():
        return str(candidate)

    # 4. Partial prefix match as fallback
    prefix = slug[:30]
    for md_file in sorted(md_dir.glob("*.md")):
        if prefix in md_file.stem:
            return str(md_file)

    return None


def load_documents_from_catalogue(cfg):
    """Load the document list from the domain's catalogue CSV.

    The catalogue CSV is the single source of truth for document metadata.
    If md_path is not an explicit column, it is derived by matching the
    title against markdown filenames in the corpus directory.
    """
    import csv

    cat_cfg = cfg.domain.catalogue
    cat_file = cat_cfg.get("file", "catalogue.csv") if cat_cfg else "catalogue.csv"
    domain_lower = cfg.domain.name.lower()
    cat_path = ROOT / "corpora" / domain_lower / cat_file

    if not cat_path.exists():
        raise SystemExit(
            f"Catalogue CSV not found: {cat_path}\n"
            f"The catalogue CSV is the document list for extraction. "
            f"Run the domain scraper or use --source to provide a JSON document list."
        )

    with open(cat_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit(f"Catalogue CSV is empty: {cat_path}")

    md_dir = ROOT / "corpora" / domain_lower / "markdown"
    title_field = cat_cfg.get("title_field", "Title") if cat_cfg else "Title"

    seen, docs = set(), []
    skipped = 0
    for row in rows:
        mp = resolve_md_path(row, md_dir, title_field)
        if not mp or mp in seen:
            skipped += 1
            continue
        seen.add(mp)
        row["md_path"] = mp
        docs.append(row)

    if skipped:
        print(f"  Catalogue: {skipped} rows skipped (no matching markdown)")

    return docs


def load_documents_from_json(source):
    """Load documents from a JSON file (flat list or nested groups).

    Supports both flat list format and legacy grouped format (list of lists).
    """
    source_path = Path(source) if Path(source).is_absolute() else ROOT / source
    if not source_path.exists():
        raise SystemExit(f"Document list not found: {source_path}")

    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    # Detect format: flat list vs nested groups
    if data and isinstance(data[0], list):
        # Nested groups — flatten
        flat = [doc for group in data for doc in group]
    else:
        flat = data

    seen, docs = set(), []
    for doc in flat:
        mp = doc.get("md_path", "")
        if not mp or mp in seen:
            continue
        seen.add(mp)
        docs.append(doc)
    return docs


def load_prompt_template(cfg):
    """Load extraction prompt via DomainConfig prompt rendering.

    Uses pipeline/prompts/extract.md with domain context injected.
    """
    return cfg.prompt("extract")


def find_document_tables(local_path, tables_dir):
    """Find extracted table CSVs for a document via shared hash."""
    if not tables_dir or not tables_dir.exists():
        return []
    m = re.search(r'_([a-f0-9]{6})\.pdf$', local_path)
    if not m:
        return []
    doc_hash = m.group(1)
    return sorted(tables_dir.glob(f'*_{doc_hash}_p*_t*.csv'))


def build_prompt(doc, start_id, prompt_template, cfg, tables_dir,
                 excluded_types=None, skip_type_filter=False):
    """Build the extraction prompt for a single document."""
    md_path = doc.get("md_path", "")
    title = doc.get("Title", doc.get("title", Path(md_path).stem if md_path else "Unknown"))

    if not md_path or not Path(md_path).exists():
        print(f"  SKIP: markdown not found for '{title}'")
        return None

    doc_type = doc.get("Type", doc.get("type", "")).strip()
    if not skip_type_filter and excluded_types and doc_type in excluded_types:
        print(f"  SKIP: document type '{doc_type}' excluded from extraction")
        return None

    content = Path(md_path).read_text(encoding="utf-8", errors="replace")
    max_chars = cfg.domain.max_document_chars

    if len(content) > max_chars:
        print(f"  SKIP: '{title}' is {len(content):,} chars (over {max_chars:,} limit)")
        return None

    # Build document header with available metadata
    source_url = doc.get("Link to item", doc.get("source_url", ""))
    header_lines = [
        "--- DOCUMENT ---",
        f"Title: {title}",
    ]
    if source_url:
        header_lines.append(f"Source URL: {source_url}")
    header_lines.append(f"Markdown filename: {Path(md_path).name}")

    doc_section = "\n".join(header_lines) + "\n\n" + content

    # Append extracted tables if available
    tables = find_document_tables(doc.get("local_path", ""), tables_dir)
    if tables:
        table_blocks = []
        total_chars = 0
        for tbl in tables:
            if total_chars > 40_000:
                break
            txt = tbl.read_text(encoding="utf-8", errors="replace").strip()
            if len(txt) < 30:
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

    prefix = cfg.domain.record_id_prefix
    prompt = prompt_template
    prompt = prompt.replace(
        "[Document list and markdown content appended by the orchestrating script]",
        doc_section,
    )
    prompt = prompt.replace(
        f"Start record_id numbering at {prefix}-[START_ID].",
        f"Start record_id numbering at {prefix}-{start_id:04d}.",
    )

    return prompt


def call_api(client, prompt, doc_num, model, max_tokens):
    """Call Claude API with retry on rate limit / server errors."""
    use_streaming = max_tokens > 8192

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_streaming:
                with client.messages.stream(
                    model=model, max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    msg = stream.get_final_message()
                    usage = msg.usage
                    return msg.content[0].text, usage.input_tokens, usage.output_tokens
            else:
                message = client.messages.create(
                    model=model, max_tokens=max_tokens,
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


def parse_yaml_response(response, doc_num, out_dir):
    """Extract YAML records from model response."""
    no_record_phrases = [
        "no records extracted",
        "no delivery insight records",
        "does not contain delivery insight",
        "no meaningful delivery",
        "no insight records",
        "no extractable insight",
    ]
    if any(p in response.lower() for p in no_record_phrases):
        print(f"  No records in this document (model confirmed)")
        return []

    yaml_match = re.search(r"```(?:yaml)?\s*(.*?)```", response, re.DOTALL)
    if yaml_match:
        yaml_text = yaml_match.group(1).strip()
        truncated = False
    else:
        yaml_text = re.sub(r"^```(?:yaml)?\s*\n?", "", response.strip())
        truncated = True

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
                except yaml.YAMLError:
                    raw_path = out_dir / f"doc_{doc_num:04d}_raw_error.txt"
                    raw_path.write_text(response, encoding="utf-8")
                    return []
            else:
                return []
        else:
            raw_path = out_dir / f"doc_{doc_num:04d}_raw_error.txt"
            raw_path.write_text(response, encoding="utf-8")
            return []

    if isinstance(records, list):
        return records
    if isinstance(records, dict) and "records" in records:
        return records["records"]
    return []


def find_source_page(doc, evidence_excerpt):
    """Search the source PDF for the evidence_excerpt and return the page number."""
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


def load_catalogue(cfg):
    """Load the catalogue CSV for metadata stamping.

    Returns a dict keyed by join_key value -> row dict, plus the field_map.
    """
    cat_cfg = cfg.domain.catalogue
    if not cat_cfg or not cat_cfg.get("field_map"):
        return {}, {}, None, {}

    cat_file = cat_cfg.get("file", "catalogue.csv")
    join_key = cat_cfg.get("join_key", "md_path")
    field_map = cat_cfg["field_map"]

    cat_path = ROOT / "corpora" / cfg.domain.name.lower() / cat_file
    if not cat_path.exists():
        print(f"  WARNING: catalogue CSV not found: {cat_path}")
        return {}, field_map, None, {}

    import csv
    with open(cat_path, encoding="utf-8") as f:
        rows = {row.get(join_key, ""): row for row in csv.DictReader(f)}

    # Load portfolio CSV if configured (secondary join)
    portfolio_cfg = cat_cfg.get("portfolio")
    portfolio = {}
    if portfolio_cfg:
        port_file = portfolio_cfg.get("file", "portfolio.csv")
        port_path = cfg.domain_dir / port_file
        if not port_path.exists():
            port_path = ROOT / "corpora" / cfg.domain.name.lower() / port_file
        if port_path.exists():
            with open(port_path, encoding="utf-8") as f:
                match_field = portfolio_cfg.get("match_field", "Project")
                portfolio = {normalise_project_name(row.get(match_field, "")): row
                             for row in csv.DictReader(f)}

    return rows, field_map, portfolio_cfg, portfolio


def stamp_and_save(records, doc, doc_num, catalogue_rows, field_map,
                   portfolio_cfg, portfolio, out_path, cfg, kb_overrides=None):
    """Stamp catalogue metadata onto records and write to YAML.

    Uses the config-driven field_map from domain.yaml to map CSV column names
    to record field names. Domain-agnostic — no hardcoded column names.
    """
    join_key = cfg.domain.catalogue.get("join_key", "md_path") if cfg.domain.catalogue else "md_path"
    cat_row = catalogue_rows.get(doc.get(join_key, ""), {})

    for record in records:
        # Stamp fields from catalogue CSV via field_map
        for csv_col, record_field in field_map.items():
            record[record_field] = cat_row.get(csv_col) or doc.get(csv_col) or None

        # Always stamp these engine-level fields
        doc_md_path = doc.get("md_path", "")
        record["markdown_filename"] = Path(doc_md_path).name if doc_md_path else None
        local_path = doc.get("local_path", "")
        record["source_document_folder"] = Path(local_path).parent.name if local_path else None
        record["source_page_pdf"] = find_source_page(doc, record.get("evidence_excerpt"))

        # Portfolio enrichment (optional secondary join)
        if portfolio_cfg and portfolio:
            join_csv_col = portfolio_cfg.get("join_key", "Associated project name")
            proj_name = cat_row.get(join_csv_col, "") or doc.get(join_csv_col, "")
            portfolio_row = portfolio.get(normalise_project_name(proj_name)) if proj_name else None
            port_field_map = portfolio_cfg.get("field_map", {})
            for csv_col, record_field in port_field_map.items():
                record[record_field] = (portfolio_row.get(csv_col) or None) if portfolio_row else None

    # Apply KB data quality overrides
    if kb_overrides and doc_num in kb_overrides:
        for record in records:
            record.update(kb_overrides[doc_num])
        print(f"  NOTE: KB data quality override applied for doc_{doc_num:04d}")

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(records, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def parse_doc_range(spec, total):
    docs = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            docs.extend(range(int(a), int(b) + 1))
        else:
            docs.append(int(part))
    return [d for d in docs if 1 <= d <= total]


def main():
    parser = argparse.ArgumentParser(description="Extract taxonomy-agnostic insights per document")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena, anao)")
    parser.add_argument("--docs", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--retrieve", type=str, default=None, metavar="BATCH_ID")
    parser.add_argument("--source", type=str, default=None,
                        help="Path to document list JSON (overrides default)")
    parser.add_argument("--out-dir", type=str, default=None)
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    model = cfg.domain.extraction_model
    ids_per_doc = cfg.domain.ids_per_document
    max_tokens = 128000  # model ceiling — never cap below this

    # Resolve paths
    out_dir = Path(args.out_dir) if args.out_dir else get_dirs(cfg)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load domain-specific config
    domain_lower = cfg.domain.name.lower()
    tables_dir = ROOT / "corpora" / domain_lower / "tables"
    if not tables_dir.exists():
        tables_dir = ROOT / "tables"

    # Load excluded doc types and KB overrides from domain config
    excluded_types = set(cfg.excluded_doc_types) if cfg.excluded_doc_types else None
    kb_overrides = cfg.kb_overrides or {}
    kb_overrides = {int(k): v for k, v in kb_overrides.items()} if kb_overrides else {}

    # Load catalogue and portfolio via config-driven field mapping
    catalogue_rows, field_map, portfolio_cfg, portfolio = load_catalogue(cfg)

    # Load document list: from --source JSON if given, else from catalogue CSV
    if args.source:
        docs = load_documents_from_json(args.source)
    else:
        docs = load_documents_from_catalogue(cfg)
    total = len(docs)
    print(f"Loaded {total} unique documents for {cfg.domain.name}")
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

    prompt_template = load_prompt_template(cfg)
    client = anthropic.Anthropic()
    batch_meta_file = out_dir / "batch_meta.json"

    # RETRIEVE mode
    if args.retrieve:
        batch_id = args.retrieve
        if not batch_meta_file.exists():
            raise SystemExit(f"No batch metadata found at {batch_meta_file}")
        with open(batch_meta_file) as f:
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
        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            doc_num = id_to_docnum.get(custom_id)
            if doc_num is None:
                continue
            doc = docs[doc_num - 1]
            out_path = out_dir / f"doc_{doc_num:04d}.yaml"
            title = doc.get("Title", doc.get("title", "Unknown"))[:60]
            if result.result.type == "errored":
                print(f"  [doc_{doc_num:04d}] ERROR: {result.result.error}")
                skipped += 1
                continue
            response_text = result.result.message.content[0].text
            records = parse_yaml_response(response_text, doc_num, out_dir)
            if records:
                stamp_and_save(records, doc, doc_num, catalogue_rows, field_map,
                               portfolio_cfg, portfolio, out_path, cfg, kb_overrides)
                print(f"  [doc_{doc_num:04d}] {len(records)} records → {out_path.name}  ({title})")
                processed += 1
            else:
                print(f"  [doc_{doc_num:04d}] No records extracted  ({title})")
        print(f"\nDone. Written: {processed}, Errors/empty: {skipped}")
        return

    # Build prompts
    if not doc_indices:
        print("Nothing to do.")
        return

    requests_to_send = []
    skipped = 0

    for idx in doc_indices:
        doc_num = idx + 1
        doc = docs[idx]
        start_id = idx * ids_per_doc + 1

        prompt = build_prompt(doc, start_id, prompt_template, cfg, tables_dir,
                              excluded_types, skip_type_filter=bool(args.source))
        if prompt is None:
            skipped += 1
            continue

        if args.dry_run:
            print(f"\n--- DRY RUN PROMPT [{doc_num:04d}] (first 2000 chars) ---\n{prompt[:2000]}\n...")
            break

        requests_to_send.append((doc_num, doc, prompt))

    if args.dry_run:
        return

    # BATCH mode
    if args.batch:
        print(f"\nSubmitting {len(requests_to_send)} requests as Message Batch...")
        batch_requests = [
            {
                "custom_id": f"doc_{doc_num:04d}",
                "params": {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            }
            for doc_num, doc, prompt in requests_to_send
        ]
        batch = client.messages.batches.create(requests=batch_requests)
        print(f"Batch submitted: {batch.id}")

        meta = {
            "batch_id": batch.id,
            "request_count": len(batch_requests),
            "requests": [{"custom_id": f"doc_{doc_num:04d}", "doc_num": doc_num}
                         for doc_num, doc, prompt in requests_to_send],
        }
        with open(batch_meta_file, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Metadata saved to {batch_meta_file}")
        print(f"\nTo retrieve when complete:")
        print(f"  python -m pipeline.extract --domain {domain_lower} --retrieve {batch.id}")
        return

    # SYNC mode
    processed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for doc_num, doc, prompt in requests_to_send:
        out_path = out_dir / f"doc_{doc_num:04d}.yaml"
        title = doc.get("Title", doc.get("title", "Unknown"))[:70]
        print(f"\n[{doc_num:04d}/{total}] {title}")

        response_text, in_tok, out_tok = call_api(client, prompt, doc_num, model, max_tokens)
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        cost = (in_tok / 1_000_000 * PRICE_INPUT) + (out_tok / 1_000_000 * PRICE_OUTPUT)
        print(f"  Tokens: {in_tok:,} in / {out_tok:,} out  (${cost:.3f})")

        records = parse_yaml_response(response_text, doc_num, out_dir)
        if records:
            stamp_and_save(records, doc, doc_num, catalogue_rows, field_map,
                           portfolio_cfg, portfolio, out_path, cfg, kb_overrides)
            print(f"  {len(records)} records → {out_path.name}")
            processed += 1
        else:
            print(f"  WARNING: no records extracted for doc {doc_num}")

    total_cost = (total_input_tokens / 1_000_000 * PRICE_INPUT) + (total_output_tokens / 1_000_000 * PRICE_OUTPUT)
    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")
    print(f"Tokens: {total_input_tokens:,} input / {total_output_tokens:,} output")
    print(f"Estimated cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
