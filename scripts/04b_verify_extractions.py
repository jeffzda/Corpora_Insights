#!/usr/bin/env python3
"""
Step 4b: Verify extracted delivery insight records against their source documents.

Checks both grounding (is the text supported?) and classification (are taxonomy
labels defensible?). Uses windowed source passages to keep prompts small.

Source context strategy (in order):
  1. Find evidence_excerpt in source → extract ±WINDOW chars around match
  2. Find source_pages page marker → extract ±WINDOW chars around that page
  3. Fall back to first MAX_FALLBACK chars of document

Modes:
  sequential  — default, processes docs one at a time (good for small batches)
  batch       — submits all records to Anthropic Batch API in one shot (recommended
                for full corpus — 50% cheaper, no rate limits, runs overnight)

Reads:
  insights/per_doc/doc_NNNN.yaml      — extracted records
  markdown/all/<markdown_filename>    — source documents
  all_agent_groups_v2.json            — fallback md_path lookup

Outputs:
  insights/per_doc_qa/doc_NNNN_qa.yaml  — QA results per doc
  insights/per_doc_qa/batch_state.json  — batch IDs (batch mode only)

Usage:
    # Sequential (small batches / testing)
    python scripts/04b_verify_extractions.py --docs 1-4
    python scripts/04b_verify_extractions.py --resume

    # Batch (full corpus — submit then collect later)
    python scripts/04b_verify_extractions.py --batch submit
    python scripts/04b_verify_extractions.py --batch collect

    python scripts/04b_verify_extractions.py --batch submit --docs 1-100  # subset
    python scripts/04b_verify_extractions.py --window 5000                # wider window

Model: claude-haiku-4-5 (fast, cheap)
Cost:  ~$0.001-0.003 per record  (~$20-50 for full corpus, ~50% less via batch API)
"""

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed. Run: pip install anthropic")

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed. Run: pip install pyyaml")

ROOT         = Path(__file__).resolve().parents[1]
GROUPS_FILE  = ROOT / "all_agent_groups_v2.json"
MARKDOWN_DIR = ROOT / "markdown" / "all"
PER_DOC_DIR  = ROOT / "insights" / "per_doc"
QA_DIR       = ROOT / "insights" / "per_doc_qa"
BATCH_STATE  = QA_DIR / "batch_state.json"

MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10
DEFAULT_WINDOW = 3000
MAX_FALLBACK   = 40_000
BATCH_SIZE     = 10_000   # Anthropic batch API limit per request

VERIFY_PROMPT = """\
You are sense-checking an extracted delivery insight record against a passage from its source document.

You have two jobs:

1. GROUNDING: Is what_happened and lesson_learnt supported by the passage?
2. CLASSIFICATION: Are the applied taxonomy labels defensible given the passage?
   You are not re-classifying — just flagging labels that are clearly wrong or implausible.
   A label is defensible if a reasonable person could apply it given the text, even if another
   label might also fit.

Output ONLY a YAML mapping with these six fields — nothing else:

grounding_verdict: confirmed|plausible|unsupported|fabricated
classification_verdict: ok|questionable|wrong
classification_note: "one sentence — only flag specific labels that are clearly misapplied; null if ok"
source_text: "exact quote from the passage that best supports or contradicts the record"
source_page: N   # integer page number from nearest preceding <!-- page N --> marker; null if absent
grounding_note: "one sentence explaining grounding verdict, especially if not confirmed; null if confirmed"

Grounding verdict definitions:
- confirmed: what_happened and lesson_learnt are clearly supported by specific text in the passage
- plausible: consistent with the passage but supporting text is ambiguous or indirect
- unsupported: makes claims not evidenced in the passage
- fabricated: contains specific details (dates, figures, names, quotes) not present in the passage

Classification verdict definitions:
- ok: all applied labels are defensible given the passage
- questionable: one or more labels seem like a stretch but could be argued
- wrong: one or more labels are clearly inconsistent with what the passage describes

---

## Record to verify

{record_yaml}

---

## Source passage

{source_passage}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_groups_md_lookup() -> dict:
    if not GROUPS_FILE.exists():
        return {}
    with open(GROUPS_FILE, encoding="utf-8") as f:
        groups = json.load(f)
    lookup = {}
    for group in groups:
        for doc in group:
            mp = doc.get("md_path", "")
            if mp:
                lookup[Path(mp).name] = mp
    return lookup


def resolve_md_path(records: list[dict], md_lookup: dict) -> Path | None:
    for r in records:
        fn = r.get("markdown_filename") or ""
        if fn:
            candidate = MARKDOWN_DIR / fn
            if candidate.exists():
                return candidate
            if fn in md_lookup:
                return Path(md_lookup[fn])
    return None


def extract_window(source: str, record: dict, window: int) -> str:
    excerpt = (record.get("evidence_excerpt") or "").strip()
    if excerpt and len(excerpt) >= 20:
        pos = source.lower().find(excerpt[:60].lower())
        if pos != -1:
            return source[max(0, pos - window): min(len(source), pos + len(excerpt) + window)]

    pages = record.get("source_pages") or []
    if isinstance(pages, int):
        pages = [pages]
    if pages:
        marker = f"<!-- page {pages[0]} -->"
        pos = source.find(marker)
        if pos != -1:
            return source[max(0, pos - 500): min(len(source), pos + window * 2)]

    what = (record.get("what_happened") or "").strip()
    if what and len(what) >= 20:
        pos = source.lower().find(what[:50].lower())
        if pos != -1:
            return source[max(0, pos - window): min(len(source), pos + window)]

    return source[:MAX_FALLBACK]


def build_record_yaml(record: dict) -> str:
    return yaml.dump(
        {k: v for k, v in record.items()
         if k in ("record_id", "what_happened", "lesson_learnt", "failure_mode",
                   "outcome_class", "lifecycle_phase", "evidence_excerpt",
                   "issue_severity", "intervention_note", "project_type",
                   "project_scale_band", "proponent_type", "delay_category")
         and v},
        allow_unicode=True, default_flow_style=False
    ).strip()


def build_prompt(record: dict, source: str, window: int) -> str:
    passage = extract_window(source, record, window)
    return VERIFY_PROMPT.format(
        record_yaml=build_record_yaml(record),
        source_passage=passage,
    )


def parse_qa_response(response: str, record_id: str) -> dict:
    text = re.sub(r"^```(?:yaml)?\s*\n?", "", response.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict) and "grounding_verdict" in result:
            result["record_id"] = record_id
            return result
    except yaml.YAMLError:
        pass
    print(f"    WARNING: could not parse QA response for {record_id}")
    return {"record_id": record_id, "grounding_verdict": "parse_error",
            "classification_verdict": "parse_error", "classification_note": None,
            "source_text": None, "source_page": None,
            "grounding_note": f"parse failed: {response[:200]}"}


def load_per_doc_yaml(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def parse_doc_range(spec: str, total: int) -> list[int]:
    docs = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            docs.extend(range(int(a), int(b) + 1))
        else:
            docs.append(int(part))
    return [d for d in docs if 1 <= d <= total]


def tally(results: list[dict]) -> tuple[dict, dict]:
    g = defaultdict(int)
    c = defaultdict(int)
    for r in results:
        g[r.get("grounding_verdict", "error")] += 1
        c[r.get("classification_verdict", "error")] += 1
    return g, c


def print_summary(all_results: list[dict]):
    n = len(all_results)
    if not n:
        return
    g, c = tally(all_results)
    pct = lambda x: f"{100*x/n:.0f}%"
    print(f"\nDone. {n} records verified.")
    print(f"  Grounding:      confirmed={g['confirmed']} plausible={g['plausible']} "
          f"unsupported={g['unsupported']} fabricated={g['fabricated']} errors={g['parse_error']+g['error']}")
    print(f"  Classification: ok={c['ok']} questionable={c['questionable']} "
          f"wrong={c['wrong']} errors={c['parse_error']+c['error']}")
    print(f"  Grounding supported: {pct(g['confirmed']+g['plausible'])}  "
          f"Classification ok: {pct(c['ok'])}")


# ── Sequential mode ───────────────────────────────────────────────────────────

def run_sequential(per_doc_files: list[Path], md_lookup: dict, window: int):
    client = anthropic.Anthropic()
    print(f"Verifying {len(per_doc_files)} document(s) sequentially using {MODEL}")
    print(f"Context window: ±{window} chars\n")

    all_results = []
    for per_doc_path in per_doc_files:
        qa_path = QA_DIR / per_doc_path.name.replace(".yaml", "_qa.yaml")
        records = load_per_doc_yaml(per_doc_path)
        if not records:
            continue

        md_path = resolve_md_path(records, md_lookup)
        title = (records[0].get("source_title") or per_doc_path.stem)[:60]
        print(f"\n[{per_doc_path.stem}] {title} — {len(records)} record(s)")

        if not md_path:
            print("  SKIP: markdown not found")
            continue

        source = md_path.read_text(encoding="utf-8", errors="replace")
        qa_results = []

        for record in records:
            record_id = record.get("record_id", "unknown")
            prompt = build_prompt(record, source, window)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    msg = client.messages.create(
                        model=MODEL, max_tokens=MAX_TOKENS,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    result = parse_qa_response(msg.content[0].text, record_id)
                    break
                except anthropic.RateLimitError:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"    Rate limit, waiting {delay}s")
                    time.sleep(delay)
                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        time.sleep(RETRY_BASE_DELAY * attempt)
                    else:
                        raise
            else:
                result = parse_qa_response("", record_id)

            qa_results.append(result)
            all_results.append(result)
            gv = result.get("grounding_verdict", "")
            cv = result.get("classification_verdict", "")
            print(f"  {record_id}: grounding={gv}  classification={cv}")

        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(qa_results, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"  → {qa_path.name}")

    print_summary(all_results)


# ── Batch mode ────────────────────────────────────────────────────────────────

def run_batch_submit(per_doc_files: list[Path], md_lookup: dict, window: int):
    """Build all prompts and submit to Anthropic Batch API."""
    client = anthropic.Anthropic()
    print(f"Building prompts for {len(per_doc_files)} documents...")

    requests = []       # list of batch request dicts
    skipped_docs = 0

    for per_doc_path in per_doc_files:
        records = load_per_doc_yaml(per_doc_path)
        if not records:
            continue
        md_path = resolve_md_path(records, md_lookup)
        if not md_path:
            skipped_docs += 1
            continue
        source = md_path.read_text(encoding="utf-8", errors="replace")

        for record in records:
            record_id = record.get("record_id", "unknown")
            # custom_id encodes doc stem + record_id for routing on collect
            # only [a-zA-Z0-9_-] allowed, max 64 chars — use __ as separator
            custom_id = f"{per_doc_path.stem}__{record_id}"
            prompt = build_prompt(record, source, window)
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
            })

    print(f"  {len(requests)} requests built  ({skipped_docs} docs skipped — no markdown)")

    # Submit in chunks of BATCH_SIZE
    batch_ids = []
    for i in range(0, len(requests), BATCH_SIZE):
        chunk = requests[i: i + BATCH_SIZE]
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Submitted batch {len(batch_ids)}: {batch.id}  ({len(chunk)} requests)")

    state = {"batch_ids": batch_ids, "total_requests": len(requests)}
    with open(BATCH_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"\nBatch IDs saved to {BATCH_STATE}")
    print(f"Run with --batch collect when processing is complete (usually <1 hour).")


def run_batch_collect():
    """Retrieve completed batch results and write per-doc QA yaml files."""
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state found at {BATCH_STATE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    doc_results: dict = defaultdict(list)   # doc_stem → list of qa result dicts
    all_results = []
    total_requests = state.get("total_requests", "?")

    for batch_id in state["batch_ids"]:
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Batch {batch_id}: {batch.processing_status}")
        if batch.processing_status != "ended":
            print("  Not ready yet — try again later.")
            continue

        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            doc_stem, record_id = custom_id.split("__", 1)

            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                qa = parse_qa_response(text, record_id)
            else:
                error_msg = str(result.result)[:200]
                qa = {"record_id": record_id, "grounding_verdict": "api_error",
                      "classification_verdict": "api_error", "classification_note": None,
                      "source_text": None, "source_page": None,
                      "grounding_note": f"Batch API error: {error_msg}"}

            doc_results[doc_stem].append(qa)
            all_results.append(qa)

    # Write per-doc QA files
    written = 0
    for doc_stem, results in sorted(doc_results.items()):
        qa_path = QA_DIR / f"{doc_stem}_qa.yaml"
        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(results, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        written += 1

    print(f"\nWritten {written} QA files  ({len(all_results)} of {total_requests} results collected)")
    print_summary(all_results)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify extracted records against source documents")
    parser.add_argument("--batch", choices=["submit", "collect"], default=None,
                        help="Batch API mode: 'submit' to send all, 'collect' to retrieve results")
    parser.add_argument("--docs", type=str, default=None,
                        help="Documents to process: '1-100', '5', '1,3,5'. Default: all.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip documents that already have QA output files (sequential only).")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"Context window chars around anchor (default {DEFAULT_WINDOW})")
    args = parser.parse_args()

    QA_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch == "collect":
        run_batch_collect()
        return

    # Resolve file list (used by both sequential and batch submit)
    md_lookup = load_groups_md_lookup()
    per_doc_files = sorted(PER_DOC_DIR.glob("doc_*.yaml"))
    total = len(per_doc_files)

    if args.docs:
        wanted = set(parse_doc_range(args.docs, total))
        per_doc_files = [p for i, p in enumerate(per_doc_files, 1) if i in wanted]

    if args.resume and not args.batch:
        per_doc_files = [
            p for p in per_doc_files
            if not (QA_DIR / p.name.replace(".yaml", "_qa.yaml")).exists()
        ]
        print(f"Resuming: {len(per_doc_files)} documents remaining")

    if not per_doc_files:
        print("Nothing to do.")
        return

    if args.batch == "submit":
        run_batch_submit(per_doc_files, md_lookup, args.window)
    else:
        run_sequential(per_doc_files, md_lookup, args.window)


if __name__ == "__main__":
    main()
