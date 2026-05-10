#!/usr/bin/env python3
"""Verify extracted delivery insight records against source documents.

Config-driven version of scripts/04b_verify_extractions.py.
Uses domain config for model selection.

Usage:
    python -m pipeline.verify --domain arena --docs 1-4
    python -m pipeline.verify --domain arena --batch submit
    python -m pipeline.verify --domain arena --batch collect
    python -m pipeline.verify --domain arena --resume
"""

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed")

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed")

from pipeline.config import DomainConfig

ROOT = Path(__file__).resolve().parents[1]
MAX_TOKENS = 1024
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10
DEFAULT_WINDOW = 3000
MAX_FALLBACK = 40_000
BATCH_SIZE = 10_000


def get_dirs(cfg):
    """Get input/output/markdown directories for this domain."""
    input_dir = ROOT / "runs" / cfg.domain.name.lower() / "per_doc"
    if not input_dir.exists():
        input_dir = ROOT / "insights" / "per_doc"
    qa_dir = ROOT / "runs" / cfg.domain.name.lower() / "per_doc_qa"
    if not qa_dir.exists() and (ROOT / "insights" / "per_doc_qa").exists():
        qa_dir = ROOT / "insights" / "per_doc_qa"
    md_dir = ROOT / "markdown" / "all"
    return input_dir, qa_dir, md_dir


def load_groups_md_lookup():
    """Load markdown path lookup from legacy groups file (ARENA backward compat)."""
    groups_file = ROOT / "all_agent_groups_v2.json"
    if not groups_file.exists():
        return {}
    with open(groups_file, encoding="utf-8") as f:
        groups = json.load(f)
    lookup = {}
    for group in groups:
        for doc in group:
            mp = doc.get("md_path", "")
            if mp:
                lookup[Path(mp).name] = mp
    return lookup


def resolve_md_path(records, md_dir, md_lookup):
    """Find the source markdown document for a set of records."""
    for r in records:
        fn = r.get("markdown_filename") or ""
        if fn:
            candidate = md_dir / fn
            if candidate.exists():
                return candidate
            if fn in md_lookup:
                return Path(md_lookup[fn])
    return None


def extract_window(source, record, window):
    """Extract context window around evidence excerpt, page marker, or fallback."""
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


def build_record_yaml(record):
    """Build YAML representation of record for verification."""
    return yaml.dump(
        {k: v for k, v in record.items()
         if k in ("record_id", "what_happened", "lesson_learnt", "failure_mode",
                   "outcome_class", "lifecycle_phase", "evidence_excerpt",
                   "issue_severity", "intervention_note", "project_type",
                   "project_scale_band", "proponent_type", "delay_category")
         and v},
        allow_unicode=True, default_flow_style=False
    ).strip()


def build_prompt(record, source, window, prompt_template):
    """Build verification prompt with passage."""
    passage = extract_window(source, record, window)
    return prompt_template.format(
        record_yaml=build_record_yaml(record),
        source_passage=passage,
    )


def parse_qa_response(response, record_id):
    """Parse YAML response from API."""
    text = re.sub(r"^```(?:yaml)?\s*\n?", "", response.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict) and "grounding_verdict" in result:
            result["record_id"] = record_id
            return result
    except yaml.YAMLError:
        pass
    return {"record_id": record_id, "grounding_verdict": "parse_error",
            "classification_verdict": "parse_error", "classification_note": None,
            "source_text": None, "source_page": None,
            "grounding_note": f"parse failed: {response[:200]}"}


def load_per_doc_yaml(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


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


def tally(results):
    g = defaultdict(int)
    c = defaultdict(int)
    for r in results:
        g[r.get("grounding_verdict", "error")] += 1
        c[r.get("classification_verdict", "error")] += 1
    return g, c


def print_summary(all_results):
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


def run_sequential(per_doc_files, md_dir, md_lookup, qa_dir, window, model, prompt_template):
    """Process documents one at a time with retries."""
    client = anthropic.Anthropic()
    print(f"Verifying {len(per_doc_files)} document(s) sequentially using {model}")
    print(f"Context window: ±{window} chars\n")

    all_results = []
    for per_doc_path in per_doc_files:
        qa_path = qa_dir / per_doc_path.name.replace(".yaml", "_qa.yaml")
        records = load_per_doc_yaml(per_doc_path)
        if not records:
            continue

        md_path = resolve_md_path(records, md_dir, md_lookup)
        title = (records[0].get("source_title") or per_doc_path.stem)[:60]
        print(f"\n[{per_doc_path.stem}] {title} — {len(records)} record(s)")

        if not md_path:
            print("  SKIP: markdown not found")
            continue

        source = md_path.read_text(encoding="utf-8", errors="replace")
        qa_results = []

        for record in records:
            record_id = record.get("record_id", "unknown")
            prompt = build_prompt(record, source, window, prompt_template)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    msg = client.messages.create(
                        model=model, max_tokens=MAX_TOKENS,
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


def run_batch_submit(per_doc_files, md_dir, md_lookup, qa_dir, window, model, prompt_template):
    """Build all prompts and submit to Anthropic Batch API."""
    client = anthropic.Anthropic()
    batch_state = qa_dir / "batch_state.json"
    print(f"Building prompts for {len(per_doc_files)} documents...")

    requests = []
    skipped_docs = 0

    for per_doc_path in per_doc_files:
        records = load_per_doc_yaml(per_doc_path)
        if not records:
            continue
        md_path = resolve_md_path(records, md_dir, md_lookup)
        if not md_path:
            skipped_docs += 1
            continue
        source = md_path.read_text(encoding="utf-8", errors="replace")

        for record in records:
            record_id = record.get("record_id", "unknown")
            custom_id = f"{per_doc_path.stem}__{record_id}"
            prompt = build_prompt(record, source, window, prompt_template)
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": model,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
            })

    print(f"  {len(requests)} requests built  ({skipped_docs} docs skipped — no markdown)")

    batch_ids = []
    for i in range(0, len(requests), BATCH_SIZE):
        chunk = requests[i: i + BATCH_SIZE]
        batch = client.messages.batches.create(requests=chunk)
        batch_ids.append(batch.id)
        print(f"  Submitted batch {len(batch_ids)}: {batch.id}  ({len(chunk)} requests)")

    state = {"batch_ids": batch_ids, "total_requests": len(requests)}
    with open(batch_state, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"\nBatch IDs saved to {batch_state}")


def run_batch_collect(qa_dir):
    """Retrieve completed batch results and write per-doc QA yaml files."""
    batch_state = qa_dir / "batch_state.json"
    if not batch_state.exists():
        raise SystemExit(f"No batch state found at {batch_state}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(batch_state, encoding="utf-8") as f:
        state = json.load(f)

    doc_results = defaultdict(list)
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

    written = 0
    for doc_stem, results in sorted(doc_results.items()):
        qa_path = qa_dir / f"{doc_stem}_qa.yaml"
        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(results, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        written += 1

    print(f"\nWritten {written} QA files  ({len(all_results)} of {total_requests} results collected)")
    print_summary(all_results)


def main():
    parser = argparse.ArgumentParser(description="Verify extracted records against source documents")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. arena)")
    parser.add_argument("--batch", choices=["submit", "collect"], default=None)
    parser.add_argument("--docs", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    args = parser.parse_args()

    cfg = DomainConfig.load(args.domain)
    input_dir, qa_dir, md_dir = get_dirs(cfg)
    qa_dir.mkdir(parents=True, exist_ok=True)

    model = cfg.domain.verification_model
    prompt_template = cfg.prompt("qa_verification")

    if args.batch == "collect":
        run_batch_collect(qa_dir)
        return

    md_lookup = load_groups_md_lookup()
    per_doc_files = sorted(input_dir.glob("doc_*.yaml"))
    total = len(per_doc_files)

    if args.docs:
        wanted = set(parse_doc_range(args.docs, total))
        per_doc_files = [p for i, p in enumerate(per_doc_files, 1) if i in wanted]

    if args.resume and not args.batch:
        per_doc_files = [
            p for p in per_doc_files
            if not (qa_dir / p.name.replace(".yaml", "_qa.yaml")).exists()
        ]
        print(f"Resuming: {len(per_doc_files)} documents remaining")

    if not per_doc_files:
        print("Nothing to do.")
        return

    if args.batch == "submit":
        run_batch_submit(per_doc_files, md_dir, md_lookup, qa_dir, args.window, model, prompt_template)
    else:
        run_sequential(per_doc_files, md_dir, md_lookup, qa_dir, args.window, model, prompt_template)


if __name__ == "__main__":
    main()
