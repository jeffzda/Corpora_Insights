#!/usr/bin/env python3
"""V2 extraction with chunked backward-walk + event-identity passing + bundled axis tagging.

Differences from v1 (`pipeline/extract.py`):
  - Documents above a configurable size threshold are chunked from the END backwards,
    so the synthesis-rich conclusion/discussion is processed first. Each chunk's
    extraction is fed the running event registry so subsequent chunks can assign
    records to existing events instead of redeclaring them. Mitigates §15
    extraction-saturation under-extraction on large docs.
  - Per-record axis tags (causal_claim_made, valence, mechanism_named,
    mechanism_phrase, realisation, stakeholder, interface_locus, outcome_class)
    are emitted at extraction time, replacing downstream Stages 2 / A / 6.
    See methodology_gaps.md §14.
  - Event identity (event_id, event_name) is part of every record's output,
    replacing post-hoc dedup. Cross-document event registry can be passed in
    via `--prior-events PATH` (a JSON file produced by a prior doc's extraction
    on the same project). See methodology_gaps.md §13.

Usage:
    # Single-doc smoke test
    python -m pipeline.extract_v2 --domain arena --docs 29 --dry-run

    # Pilot on 5 docs sync (reads/writes default per_doc dir)
    python -m pipeline.extract_v2 --domain arena --docs 1-5

    # With prior events from another doc on the same project
    python -m pipeline.extract_v2 --domain arena --docs 30 \\
        --prior-events corpora/arena/runs_v2/per_doc/doc_0029.events.json

    # Full project-aware run (caller orchestrates seed-doc selection then walks)
    # See corpora/arena/tests/extraction/seed_doc_heuristic.py
"""

import argparse
import json
import re
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

try:
    import httpx
except ImportError:
    httpx = None

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

from pipeline.config import DomainConfig
from pipeline.extract import (
    ROOT, MAX_RETRIES, RETRY_BASE_DELAY,
    PRICE_INPUT, PRICE_OUTPUT,
    get_dirs, normalise_project_name, resolve_md_path,
    load_documents_from_catalogue, load_documents_from_json,
    find_document_tables, find_source_page,
    load_catalogue, parse_doc_range,
)

# Chunking is only triggered for very large docs. The original §15
# claim that yield saturates at ~10k tokens did not hold under v1-vs-v2
# comparison: chunking on small/medium docs cost records, not added them.
# The genuine saturation regime is the very high end (≥150k input tokens
# / ≥600k chars), where round-number record clustering at 200/150/140
# indicates soft-cap behaviour. For docs below that threshold, v2 runs
# single-pass with event-identity passing only — no chunking.
DEFAULT_CHUNK_CHARS = 30_000
DEFAULT_CHUNK_OVERLAP_CHARS = 3_000
# Default threshold: chunk only if char-count > this. Set to ~600k chars
# (≈150k tokens) — above ARENA's v1 max_document_chars and aligned with
# the empirically-observed soft-cap regime.
SINGLE_CHUNK_THRESHOLD_CHARS = 600_000


def chunk_document_backward(content, chunk_chars=DEFAULT_CHUNK_CHARS,
                             overlap_chars=DEFAULT_CHUNK_OVERLAP_CHARS):
    """Split a document into chunks ordered END-FIRST.

    Boundaries are snapped to paragraph breaks (double-newline) where possible to
    avoid mid-sentence cuts. Each chunk overlaps the next by ~overlap_chars to
    preserve cross-section context. Returns a list of (chunk_idx, total_chunks,
    text) tuples in BACKWARD reading order: chunk 1 is the END of the document,
    chunk N is the BEGINNING.

    For documents shorter than SINGLE_CHUNK_THRESHOLD_CHARS, returns a single
    chunk (chunk_idx=1, total_chunks=1).
    """
    n = len(content)
    if n <= SINGLE_CHUNK_THRESHOLD_CHARS:
        return [(1, 1, content)]

    # Build backward chunks. Start at the end, take chunk_chars, then step
    # backward by (chunk_chars - overlap_chars) for the next chunk.
    bounds = []  # list of (start, end) in original-text coords
    end = n
    while end > 0:
        start = max(0, end - chunk_chars)
        # Snap start backward to nearest paragraph boundary if not at 0
        if start > 0:
            snap = content.rfind("\n\n", max(0, start - 2000), start + 2000)
            if snap > 0 and abs(snap - start) <= 2000:
                start = snap + 2
        bounds.append((start, end))
        if start == 0:
            break
        # Next chunk's end is start + overlap (so chunks overlap)
        end = start + overlap_chars
        if end >= bounds[-1][1]:
            # Avoid infinite loop on tiny progress
            break

    total = len(bounds)
    return [(i + 1, total, content[s:e]) for i, (s, e) in enumerate(bounds)]


def build_chunk_context_block(chunk_idx, total_chunks):
    """Render the chunk-position preamble for the prompt."""
    if total_chunks == 1:
        return ("This is the **complete document** — no chunking is in effect. "
                "Process it as a single unit.")
    if chunk_idx == 1:
        position = "the **last (end-of-document) chunk** of"
    elif chunk_idx == total_chunks:
        position = "the **first (start-of-document) chunk** of"
    else:
        position = f"chunk **{chunk_idx} (working backward)** of"
    return (
        f"You are processing {position} a {total_chunks}-chunk extraction sweep over a "
        f"large document. Chunks are processed end-first so the conclusion / discussion "
        f"/ lessons-learnt sections are read before the body. Every event you encounter "
        f"that you cannot match to the prior events list below should be declared as a "
        f"new event so subsequent chunks (which contain earlier portions of the same "
        f"document) can attach their records to your declarations."
    )


def build_prior_events_block(prior_events):
    """Render the prior-events list for the prompt.

    prior_events: list of {event_id, event_name, description, exemplar_mechanism_phrase}.
    """
    if not prior_events:
        return ("none — this is the first extraction on this document and project. "
                "Every event you find is a new declaration. Number new events "
                "starting at EVT-0001.")
    next_n = 1
    for ev in prior_events:
        m = re.search(r"EVT-(\d+)", ev.get("event_id", ""))
        if m:
            next_n = max(next_n, int(m.group(1)) + 1)
    lines = [
        f"{len(prior_events)} events already established by earlier chunks and/or "
        f"earlier documents on this project. Assign records to these existing events "
        f"verbatim by `event_id` whenever a record describes the same singular "
        f"occurrence. Number any newly-declared events starting at EVT-{next_n:04d} "
        f"to avoid collisions.\n\n"
        "**Reminder: the prior events list is a naming dictionary, not a coverage "
        "claim. Never skip extracting a finding because it broadly relates to an "
        "existing event — emit a record and attach it to the existing event_id. "
        "Multiple records sharing one event_id is the desired output.**\n",
    ]
    for ev in prior_events:
        eid = ev.get("event_id", "EVT-XXXX")
        name = ev.get("event_name", "")
        desc = ev.get("description", "") or ""
        ex = ev.get("exemplar_mechanism_phrase", "") or ""
        block = f"- `{eid}` — **{name}**"
        if desc:
            block += f"\n    Description: {desc}"
        if ex:
            block += f"\n    Exemplar mechanism phrase: \"{ex}\""
        lines.append(block)
    return "\n".join(lines)


def load_prompt_template_v2(cfg):
    """Load v2 extraction prompt template (grave-prompt-derived).

    Reads pipeline/prompts/extract.md (the canonical grave prompt). Returns
    the raw template with {{double}} placeholders intact — they're substituted
    per-chunk in build_chunk_prompt.
    """
    return (ROOT / "pipeline" / "prompts" / "extract.md").read_text()


def build_chunk_prompt(doc, chunk_text, chunk_idx, total_chunks,
                        prior_events, start_id, prompt_template, cfg, tables_dir):
    """Build the v2 extraction prompt for a single chunk.

    The grave-derived template uses {{double-brace}} placeholders for runtime
    substitution. This function fills them with chunk-specific values.
    """
    md_path = doc.get("md_path", "")
    title = doc.get("Title", doc.get("title", Path(md_path).stem if md_path else "Unknown"))

    # Tables: inject on chunk 1 (end-of-doc) only.
    if chunk_idx == 1:
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
                label = (f"page {int(pm.group(1))}, table {int(pm.group(2))}"
                         if pm else tbl.stem)
                table_blocks.append(f"### Extracted table ({label})\n```\n{txt}\n```")
                total_chars += len(txt)
            if table_blocks:
                chunk_text += (
                    "\n\n## Extracted tables from this document\n\n"
                    + "\n\n".join(table_blocks)
                )

    if total_chunks > 1:
        chunk_position = (
            f"Chunk {chunk_idx} of {total_chunks}, processed end-first "
            "(conclusion / discussion read before the body). "
            "If a chunk-bounded passage references material outside this chunk "
            "(e.g. 'as discussed in section 3'), still extract any finding "
            "stated within this chunk's text — surrounding chunks handle their "
            "own portions."
        )
    else:
        chunk_position = "Complete document — no chunking is in effect."

    prior_events_block = build_prior_events_block(prior_events)
    prefix = cfg.domain.record_id_prefix
    # Build the doc-prefix (e.g. ARENA-DLV-1162). For multi-chunk docs we
    # append a chunk suffix so record IDs don't collide across chunks.
    doc_num = doc.get("doc_num")
    if doc_num is None:
        # Derive from md path or assume the v2 caller passed it in
        doc_num_match = re.search(r"doc_(\d+)", str(doc.get("md_path", "")))
        doc_num = int(doc_num_match.group(1)) if doc_num_match else 0
    if total_chunks > 1:
        chunk_prefix = f"{prefix}-{doc_num:04d}-c{chunk_idx}"
    else:
        chunk_prefix = f"{prefix}-{doc_num:04d}"

    prompt = prompt_template
    prompt = prompt.replace("{{prefix}}", chunk_prefix)
    prompt = prompt.replace("{{title}}", title)
    prompt = prompt.replace("{{chunk_position}}", chunk_position)
    prompt = prompt.replace("{{prior_events_block}}", prior_events_block)
    prompt = prompt.replace("{{text}}", chunk_text)
    return prompt


def call_api(client, prompt, doc_num, chunk_idx, model, max_tokens):
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
                return (message.content[0].text,
                        usage.input_tokens, usage.output_tokens)
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  Rate limit (doc {doc_num} chunk {chunk_idx}, "
                  f"attempt {attempt}/{MAX_RETRIES}), waiting {delay}s: {e}", flush=True)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"  Server error {e.status_code} (doc {doc_num} chunk {chunk_idx}, "
                      f"attempt {attempt}/{MAX_RETRIES}), waiting {delay}s",
                      flush=True)
                time.sleep(delay)
            else:
                raise
        except (anthropic.APIConnectionError,) + (
                (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError)
                if httpx else ()) as e:
            delay = RETRY_BASE_DELAY * attempt
            print(f"  Network error ({type(e).__name__}: {e}) (doc {doc_num} "
                  f"chunk {chunk_idx}, attempt {attempt}/{MAX_RETRIES}), "
                  f"waiting {delay}s", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"Doc {doc_num} chunk {chunk_idx}: API failed after {MAX_RETRIES} attempts")


def parse_v2_response(response, doc_num, chunk_idx, out_dir):
    """Extract records + events from a v2 model response.

    The grave-derived v2 prompt requires a single JSON object with two keys:
    `records` (array of finding records) and `events` (array of registry
    entries). Returns (records, events).
    """
    # Strip any markdown fences if the model added them despite instructions.
    text = response.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # Find the first { … } JSON object spanning the whole text.
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to recover by trimming to the outermost { … }
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            try:
                parsed = json.loads(text[first:last+1])
            except json.JSONDecodeError as e:
                print(f"  WARNING: doc {doc_num} chunk {chunk_idx} — JSON parse failed: {e}",
                      flush=True)
                raw_path = out_dir / f"doc_{doc_num:04d}_chunk{chunk_idx:02d}_raw_error.txt"
                raw_path.write_text(response, encoding="utf-8")
                return [], []
        else:
            return [], []

    if not isinstance(parsed, dict):
        return [], []
    records = parsed.get("records", []) or []
    events = parsed.get("events", []) or []
    if not isinstance(records, list):
        records = []
    if not isinstance(events, list):
        events = []
    return records, events


def _parse_events_block(response):
    """Parse the `## events` block from the model response.

    Tolerates: fenced or unfenced yaml after the heading; ## / ### / **events**
    forms; events keyed by `events:` inside a combined yaml block. Falls back
    to scanning all fenced blocks for one whose items look like events.
    """
    # Strategy 1: ## events heading + fenced yaml block (any prose ≤200 chars between).
    m = re.search(
        r"(?:^|\n)\s*(?:#{1,4}\s*events|\*\*events\*\*)\s*\n.{0,200}?```(?:yaml)?\s*\n(.*?)\n```",
        response, re.DOTALL | re.IGNORECASE)
    if m:
        ev = _try_parse_events_yaml(m.group(1))
        if ev:
            return ev

    # Strategy 2: ## events heading + UNFENCED yaml list (model elides fences).
    # Capture from after the heading until end-of-response or the next markdown
    # heading / horizontal rule / triple-backtick fence.
    m = re.search(
        r"(?:^|\n)\s*(?:#{1,4}\s*events|\*\*events\*\*)\s*\n+(.*?)(?=\n#{1,4}\s|\n---\s*\n|\n```|\Z)",
        response, re.DOTALL | re.IGNORECASE)
    if m:
        body = m.group(1).strip()
        ev = _try_parse_events_yaml(body)
        if ev:
            return ev

    # Strategy 3: any fenced block whose items are events (have event_id +
    # event_name and NO record_id).
    for fm in re.finditer(r"```(?:yaml)?\s*\n(.*?)\n```", response, re.DOTALL):
        body = fm.group(1).strip()
        if "event_id" not in body or "event_name" not in body:
            continue
        try:
            parsed = yaml.safe_load(body)
        except yaml.YAMLError:
            continue
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            if "record_id" in parsed[0]:
                continue
            if "event_id" in parsed[0] and "event_name" in parsed[0]:
                return parsed
        if isinstance(parsed, dict) and "events" in parsed:
            ev = parsed["events"]
            if isinstance(ev, list):
                return ev
    return []


def _try_parse_events_yaml(body):
    """Try parsing a YAML body into an events list. Returns [] on failure."""
    try:
        parsed = yaml.safe_load(body)
    except yaml.YAMLError:
        return []
    if isinstance(parsed, list):
        # Reject if items have record_id (records list, not events)
        if parsed and isinstance(parsed[0], dict) and "record_id" in parsed[0]:
            return []
        return parsed
    if isinstance(parsed, dict) and "events" in parsed:
        ev = parsed["events"]
        return ev if isinstance(ev, list) else []
    return []


def merge_event_registries(running, new_events):
    """Merge new events into the running registry, preferring existing entries.

    Existing event_ids keep their description / exemplar_phrase verbatim so the
    seed chunk's framing is canonical. Newly-declared events are appended.
    """
    by_id = {ev["event_id"]: ev for ev in running}
    for ev in new_events:
        eid = ev.get("event_id")
        if not eid:
            continue
        if eid not in by_id:
            by_id[eid] = ev
    return list(by_id.values())


def stamp_records(records, doc, doc_num, chunk_idx, catalogue_rows, field_map,
                   portfolio_cfg, portfolio, cfg):
    """Stamp catalogue metadata onto records (mirrors v1 stamp_and_save body).

    Note: records are stamped per-chunk; the doc-level YAML aggregates them.
    """
    join_key = (cfg.domain.catalogue.get("join_key", "md_path")
                if cfg.domain.catalogue else "md_path")
    cat_row = catalogue_rows.get(doc.get(join_key, ""), {})

    for record in records:
        for csv_col, record_field in field_map.items():
            record[record_field] = cat_row.get(csv_col) or doc.get(csv_col) or None

        doc_md_path = doc.get("md_path", "")
        record["markdown_filename"] = Path(doc_md_path).name if doc_md_path else None
        local_path = doc.get("local_path", "")
        record["source_document_folder"] = (Path(local_path).parent.name
                                              if local_path else None)
        record["source_page_pdf"] = find_source_page(
            doc, record.get("evidence") or record.get("evidence_excerpt"))
        record["chunk_idx"] = chunk_idx

        if portfolio_cfg and portfolio:
            join_csv_col = portfolio_cfg.get("join_key", "Associated project name")
            proj_name = cat_row.get(join_csv_col, "") or doc.get(join_csv_col, "")
            portfolio_row = (portfolio.get(normalise_project_name(proj_name))
                              if proj_name else None)
            port_field_map = portfolio_cfg.get("field_map", {})
            for csv_col, record_field in port_field_map.items():
                record[record_field] = ((portfolio_row.get(csv_col) or None)
                                         if portfolio_row else None)


def extract_one_document(doc, doc_num, prior_events, prompt_template, cfg,
                          tables_dir, catalogue_rows, field_map, portfolio_cfg,
                          portfolio, client, model, max_tokens, out_dir,
                          chunk_chars, chunk_overlap, dry_run=False):
    """Run extraction over one document with backward chunking + event passing.

    Returns (all_records, final_events_registry, total_in_tokens, total_out_tokens).
    """
    md_path = doc.get("md_path", "")
    if not md_path or not Path(md_path).exists():
        title = doc.get("Title", doc.get("title", "Unknown"))
        print(f"  SKIP doc {doc_num}: markdown not found for '{title}'", flush=True)
        return None, prior_events, 0, 0

    content = Path(md_path).read_text(encoding="utf-8", errors="replace")
    # v2 uses chunking, so the v1 max_document_chars limit no longer applies.
    # Documents are split into chunk_chars-sized pieces regardless of total size.

    chunks = chunk_document_backward(content, chunk_chars, chunk_overlap)
    print(f"  Doc {doc_num}: {len(content):,} chars → {len(chunks)} chunk(s)", flush=True)

    ids_per_doc = cfg.domain.ids_per_document
    base_id = (doc_num - 1) * ids_per_doc + 1
    running_events = list(prior_events)
    all_records = []
    total_in = total_out = 0

    for chunk_idx, total_chunks, chunk_text in chunks:
        chunk_start_id = base_id + len(all_records)
        prompt = build_chunk_prompt(doc, chunk_text, chunk_idx, total_chunks,
                                     running_events, chunk_start_id,
                                     prompt_template, cfg, tables_dir)

        if dry_run:
            print(f"\n--- DRY RUN doc {doc_num} chunk {chunk_idx}/{total_chunks} (first 3000 chars) ---")
            print(prompt[:3000])
            print("\n[... remainder elided ...]\n")
            continue

        response, in_tok, out_tok = call_api(client, prompt, doc_num, chunk_idx,
                                              model, max_tokens)
        total_in += in_tok
        total_out += out_tok
        cost = (in_tok / 1_000_000 * PRICE_INPUT) + (out_tok / 1_000_000 * PRICE_OUTPUT)
        print(f"    chunk {chunk_idx}/{total_chunks}: {in_tok:,} in / {out_tok:,} out  (${cost:.3f})",
              flush=True)

        # Save raw response for debugging / audit
        raw_dir = out_dir / "_raw"
        raw_dir.mkdir(exist_ok=True)
        raw_path = raw_dir / f"doc_{doc_num:04d}_chunk{chunk_idx:02d}.txt"
        raw_path.write_text(response, encoding="utf-8")

        records, new_events = parse_v2_response(response, doc_num, chunk_idx, out_dir)
        stamp_records(records, doc, doc_num, chunk_idx, catalogue_rows, field_map,
                       portfolio_cfg, portfolio, cfg)
        all_records.extend(records)
        running_events = merge_event_registries(running_events, new_events)
        print(f"      {len(records)} records, {len(new_events)} events in registry "
              f"(running total: {len(running_events)})", flush=True)

    return all_records, running_events, total_in, total_out


def write_doc_outputs(all_records, events_registry, doc, doc_num, out_dir,
                      kb_overrides=None):
    """Write per-doc records JSON (matching v1/grave schema) + events JSON.

    Records are written as JSON (not YAML) to match the v1/grave schema:
    {records: [...], _meta: {...}}. The events registry is a sibling
    .events.json file consumable as the next doc's --prior-events input.
    """
    if kb_overrides and doc_num in kb_overrides:
        for record in all_records:
            record.update(kb_overrides[doc_num])
        print(f"  NOTE: KB data quality override applied for doc_{doc_num:04d}",
              flush=True)

    records_path = out_dir / f"doc_{doc_num:04d}.json"
    with open(records_path, "w", encoding="utf-8") as f:
        json.dump({"records": all_records}, f, indent=2, ensure_ascii=False)

    events_path = out_dir / f"doc_{doc_num:04d}.events.json"
    payload = {
        "doc_num": doc_num,
        "doc_title": doc.get("Title", doc.get("title", "")),
        "md_path": doc.get("md_path", ""),
        "n_records": len(all_records),
        "n_events": len(events_registry),
        "events": events_registry,
    }
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return records_path, events_path


def load_prior_events(path):
    """Load a prior-events JSON file (output of an earlier doc's extraction)."""
    if not path:
        return []
    p = Path(path) if Path(path).is_absolute() else ROOT / path
    if not p.exists():
        raise SystemExit(f"--prior-events file not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("events", []) if isinstance(data, dict) else (data or [])


def main():
    parser = argparse.ArgumentParser(
        description="V2 extraction with chunked backward-walk + event passing + axis tagging")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena, anao)")
    parser.add_argument("--docs", type=str, default=None,
                         help="Doc range (1-based). e.g. '1-5' or '29,30,42'")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                         help="Print first chunk's prompt and exit")
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--out-dir", type=str, default=None,
                         help="Per-doc output directory (default: runs/<domain>/per_doc_v2)")
    parser.add_argument("--prior-events", type=str, default=None,
                         help="Path to a prior doc's .events.json (for cross-doc walks)")
    parser.add_argument("--model", type=str, default=None,
                         help="Override the extraction model (default: domain config)")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS,
                         help=f"Chunk size in chars (default {DEFAULT_CHUNK_CHARS:,})")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP_CHARS,
                         help=f"Chunk overlap in chars (default {DEFAULT_CHUNK_OVERLAP_CHARS:,})")
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    # v2 default is Sonnet 4.6 (claude-sonnet-4-6). The domain config's
    # extraction_model may still pin the deprecated Sonnet 4.0 for v1
    # reproducibility — v2 doesn't inherit that. Override with --model if
    # you want a different model.
    model = args.model or "claude-sonnet-4-6"
    # max_tokens depends on the model. Older Sonnet 4.0 caps at 64k; Sonnet 4.6
    # and Opus 4.7 support 128k. Detect by model name.
    if any(tag in model.lower() for tag in ("sonnet-4-6", "opus-4-7", "haiku-4-5")):
        max_tokens = 128_000
    else:
        max_tokens = 64_000

    # Output dir defaults to runs/<domain>/per_doc_v2 to keep v2 outputs separate
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = ROOT / "runs" / cfg.domain.name.lower() / "per_doc_v2"
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    domain_lower = cfg.domain.name.lower()
    tables_dir = ROOT / "corpora" / domain_lower / "tables"
    if not tables_dir.exists():
        tables_dir = ROOT / "tables"

    excluded_types = set(cfg.excluded_doc_types) if cfg.excluded_doc_types else None
    kb_overrides = cfg.kb_overrides or {}
    kb_overrides = {int(k): v for k, v in kb_overrides.items()} if kb_overrides else {}

    catalogue_rows, field_map, portfolio_cfg, portfolio = load_catalogue(cfg)

    if args.source:
        docs = load_documents_from_json(args.source)
    else:
        docs = load_documents_from_catalogue(cfg)
    total = len(docs)
    print(f"Loaded {total} unique documents for {cfg.domain.name}")
    print(f"V2 output directory: {out_dir}")

    if args.docs:
        doc_indices = [d - 1 for d in parse_doc_range(args.docs, total)]
    else:
        doc_indices = list(range(total))

    if args.resume:
        doc_indices = [
            i for i in doc_indices
            if not (out_dir / f"doc_{i+1:04d}.json").exists()
        ]
        print(f"Resuming: {len(doc_indices)} documents remaining")

    if not doc_indices:
        print("Nothing to do.")
        return

    prompt_template = load_prompt_template_v2(cfg)
    client = anthropic.Anthropic()

    # Filter out excluded doc types up front
    filtered = []
    for idx in doc_indices:
        doc = docs[idx]
        doc_type = doc.get("Type", doc.get("type", "")).strip()
        if (not args.source) and excluded_types and doc_type in excluded_types:
            title = doc.get("Title", doc.get("title", "Unknown"))[:60]
            print(f"  SKIP doc {idx+1}: type '{doc_type}' excluded ({title})", flush=True)
            continue
        filtered.append(idx)

    # Load any prior events from disk
    running_events = load_prior_events(args.prior_events)
    if running_events:
        print(f"Loaded {len(running_events)} prior events from {args.prior_events}")

    total_in = total_out = 0
    processed = 0

    for idx in filtered:
        doc_num = idx + 1
        doc = docs[idx]
        doc["doc_num"] = doc_num  # so build_chunk_prompt can derive the prefix
        title = doc.get("Title", doc.get("title", "Unknown"))[:70]
        print(f"\n[{doc_num:04d}/{total}] {title}", flush=True)

        result = extract_one_document(
            doc, doc_num, running_events, prompt_template, cfg, tables_dir,
            catalogue_rows, field_map, portfolio_cfg, portfolio, client, model,
            max_tokens, out_dir, args.chunk_chars, args.chunk_overlap,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            return
        records, running_events, in_tok, out_tok = result
        total_in += in_tok
        total_out += out_tok

        if records is None:
            continue

        if records:
            yaml_path, events_path = write_doc_outputs(
                records, running_events, doc, doc_num, out_dir, kb_overrides)
            print(f"  Doc {doc_num}: {len(records)} records → {yaml_path.name}; "
                  f"{len(running_events)} events → {events_path.name}", flush=True)
            processed += 1
        else:
            print(f"  WARNING: no records extracted for doc {doc_num}", flush=True)

    total_cost = ((total_in / 1_000_000 * PRICE_INPUT) +
                   (total_out / 1_000_000 * PRICE_OUTPUT))
    print(f"\nDone. Processed: {processed}/{len(filtered)}")
    print(f"Tokens: {total_in:,} input / {total_out:,} output")
    print(f"Estimated cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
