#!/usr/bin/env python3
"""
Step 4c: Re-check records flagged as 'fabricated' or 'unsupported' (grounding) or
'wrong'/'questionable' (classification) with a wider context window.

Reads the existing per_doc_qa/ files, finds records with those verdicts, re-runs
them against the source markdown with a larger window, and patches the QA files
in place with updated verdicts.

Usage:
    python scripts/04c_recheck_flagged.py                            # dry run (grounding)
    python scripts/04c_recheck_flagged.py --run                      # run (grounding)
    python scripts/04c_recheck_flagged.py --field classification --verdicts wrong --run
    python scripts/04c_recheck_flagged.py --field classification --verdicts wrong,questionable --run
    python scripts/04c_recheck_flagged.py --window 15000             # default 15000
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
MARKDOWN_DIR = ROOT / "markdown" / "all"
PER_DOC_DIR  = ROOT / "insights" / "per_doc"
QA_DIR       = ROOT / "insights" / "per_doc_qa"

MODEL          = "claude-haiku-4-5-20251001"
MAX_TOKENS     = 1024
MAX_RETRIES    = 5
RETRY_BASE     = 10
DEFAULT_WINDOW = 15_000
RECHECK_STATE  = QA_DIR / "recheck_batch_state.json"

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


def load_per_doc_yaml(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


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


def extract_window(source: str, record: dict, window: int) -> str:
    """Try multiple anchors; return widest useful passage found."""
    # 1. evidence_excerpt anchor
    excerpt = (record.get("evidence_excerpt") or "").strip()
    if excerpt and len(excerpt) >= 20:
        pos = source.lower().find(excerpt[:60].lower())
        if pos != -1:
            return source[max(0, pos - window): min(len(source), pos + len(excerpt) + window)]

    # 2. source_pages page marker anchor
    pages = record.get("source_pages") or []
    if isinstance(pages, int):
        pages = [pages]
    if pages:
        marker = f"<!-- page {pages[0]} -->"
        pos = source.find(marker)
        if pos != -1:
            return source[max(0, pos - 1000): min(len(source), pos + window * 2)]

    # 3. what_happened keyword anchor
    what = (record.get("what_happened") or "").strip()
    if what and len(what) >= 20:
        pos = source.lower().find(what[:50].lower())
        if pos != -1:
            return source[max(0, pos - window): min(len(source), pos + window)]

    # 4. fallback — beginning of doc up to window*3 (no point sending the whole thing)
    return source[:window * 3]


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


def collect_flagged(target_verdicts: set[str], field: str) -> dict[str, list[str]]:
    """Return {doc_stem: [record_id, ...]} for records with target verdicts."""
    flagged = defaultdict(list)
    for qa_path in sorted(QA_DIR.glob("doc_*_qa.yaml")):
        records = load_per_doc_yaml(qa_path)
        doc_stem = qa_path.name.replace("_qa.yaml", "")
        for r in records:
            if r.get(field) in target_verdicts:
                flagged[doc_stem].append(r["record_id"])
    return dict(flagged)


def build_requests(flagged: dict, field: str, window: int) -> list[dict]:
    """Build batch API request dicts for all flagged records."""
    requests = []
    for doc_stem, record_ids in sorted(flagged.items()):
        per_doc_path = PER_DOC_DIR / f"{doc_stem}.yaml"
        if not per_doc_path.exists():
            continue
        source_records = {r["record_id"]: r for r in load_per_doc_yaml(per_doc_path)}
        md_filename = next((r.get("markdown_filename") for r in source_records.values()
                            if r.get("markdown_filename")), None)
        if not md_filename:
            continue
        md_path = MARKDOWN_DIR / md_filename
        if not md_path.exists():
            continue
        source = md_path.read_text(encoding="utf-8", errors="replace")
        qa_path = QA_DIR / f"{doc_stem}_qa.yaml"
        qa_by_id = {r["record_id"]: r for r in load_per_doc_yaml(qa_path)}

        for record_id in record_ids:
            record = source_records.get(record_id)
            if not record:
                continue
            old_verdict = qa_by_id.get(record_id, {}).get(field, "?")
            passage = extract_window(source, record, window)
            prompt = VERIFY_PROMPT.format(
                record_yaml=build_record_yaml(record),
                source_passage=passage,
            )
            requests.append({
                "custom_id": f"{doc_stem}__{record_id}",
                "params": {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
                "_old_verdict": old_verdict,   # stored locally, not sent to API
            })
    return requests


def apply_recheck_results(results: list[dict], field: str) -> dict:
    """Patch QA files with new verdicts. Returns change tallies."""
    # Group by doc_stem
    by_doc = defaultdict(list)
    for r in results:
        by_doc[r["doc_stem"]].append(r)

    changed = defaultdict(int)
    for doc_stem, items in sorted(by_doc.items()):
        qa_path = QA_DIR / f"{doc_stem}_qa.yaml"
        qa_results = load_per_doc_yaml(qa_path)
        qa_by_id = {r["record_id"]: r for r in qa_results}

        for item in items:
            record_id = item["record_id"]
            new_qa = item["new_qa"]
            old_verdict = item["old_verdict"]
            new_verdict = new_qa.get(field, "?")
            changed[f"{old_verdict}→{new_verdict}"] += 1
            qa_by_id[record_id] = new_qa
            flip = " ✓" if new_verdict != old_verdict else ""
            print(f"  {record_id}: {old_verdict} → {new_verdict}{flip}")

        patched = [qa_by_id.get(r["record_id"], r) for r in qa_results]
        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(patched, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return changed


def main():
    parser = argparse.ArgumentParser(description="Re-check flagged QA verdicts with wider window")
    parser.add_argument("--batch", choices=["submit", "collect"], default=None,
                        help="Batch API mode (recommended — no rate limits)")
    parser.add_argument("--run", action="store_true",
                        help="Sequential mode (slow, hits rate limits)")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"Context window chars (default {DEFAULT_WINDOW})")
    parser.add_argument("--field", type=str, default="grounding_verdict",
                        choices=["grounding_verdict", "classification_verdict"],
                        help="QA field to filter on (default: grounding_verdict)")
    parser.add_argument("--verdicts", type=str, default=None,
                        help="Comma-separated verdicts to recheck. "
                             "Defaults: fabricated,unsupported (grounding) or wrong (classification)")
    args = parser.parse_args()

    if args.batch == "collect":
        if not RECHECK_STATE.exists():
            raise SystemExit(f"No batch state at {RECHECK_STATE}. Run --batch submit first.")
        client = anthropic.Anthropic()
        with open(RECHECK_STATE) as f:
            state = json.load(f)

        results = []
        for batch_id in state["batch_ids"]:
            batch = client.messages.batches.retrieve(batch_id)
            print(f"Batch {batch_id}: {batch.processing_status}")
            if batch.processing_status != "ended":
                print("  Not ready yet.")
                return
            id_map = state["id_map"]
            for result in client.messages.batches.results(batch_id):
                custom_id = result.custom_id
                doc_stem, record_id = custom_id.split("__", 1)
                old_verdict = id_map.get(custom_id, "?")
                if result.result.type == "succeeded":
                    new_qa = parse_qa_response(result.result.message.content[0].text, record_id)
                else:
                    new_qa = {"record_id": record_id, "grounding_verdict": "api_error",
                              "classification_verdict": "api_error"}
                results.append({"doc_stem": doc_stem, "record_id": record_id,
                                 "old_verdict": old_verdict, "new_qa": new_qa})

        changed = apply_recheck_results(results, state["field"])
        print(f"\nDone. {len(results)} records updated.")
        print("Verdict changes:")
        for transition, count in sorted(changed.items(), key=lambda x: -x[1]):
            print(f"  {transition}: {count}")
        return

    # Resolve target verdicts
    if args.verdicts:
        target_verdicts = set(v.strip() for v in args.verdicts.split(","))
    elif args.field == "classification_verdict":
        target_verdicts = {"wrong"}
    else:
        target_verdicts = {"fabricated", "unsupported"}

    print(f"Field: {args.field}  Target verdicts: {target_verdicts}")
    flagged = collect_flagged(target_verdicts, args.field)
    total = sum(len(v) for v in flagged.values())
    print(f"Found {total} flagged records across {len(flagged)} documents")

    if not args.run and args.batch != "submit":
        print("\nDry run — pass --batch submit (recommended) or --run to execute.")
        for doc_stem, ids in sorted(flagged.items())[:20]:
            print(f"  {doc_stem}: {ids}")
        if len(flagged) > 20:
            print(f"  ... and {len(flagged)-20} more documents")
        return

    if args.batch == "submit":
        client = anthropic.Anthropic()
        requests = build_requests(flagged, args.field, args.window)
        # Strip internal _old_verdict before sending; keep id_map for collect
        id_map = {r["custom_id"]: r.pop("_old_verdict") for r in requests}
        print(f"Submitting {len(requests)} requests to Batch API...")
        batch = client.messages.batches.create(requests=requests)
        state = {"batch_ids": [batch.id], "field": args.field, "id_map": id_map}
        with open(RECHECK_STATE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"Submitted: {batch.id}")
        print(f"Run --batch collect when done.")
        return

    # Sequential fallback (kept for small runs)
    client = anthropic.Anthropic()
    changed = defaultdict(int)
    all_updated = 0

    for doc_stem, record_ids in sorted(flagged.items()):
        qa_path = QA_DIR / f"{doc_stem}_qa.yaml"
        per_doc_path = PER_DOC_DIR / f"{doc_stem}.yaml"
        if not per_doc_path.exists():
            continue
        source_records = {r["record_id"]: r for r in load_per_doc_yaml(per_doc_path)}
        md_filename = next((r.get("markdown_filename") for r in source_records.values()
                            if r.get("markdown_filename")), None)
        if not md_filename:
            continue
        md_path = MARKDOWN_DIR / md_filename
        if not md_path.exists():
            continue
        source = md_path.read_text(encoding="utf-8", errors="replace")
        qa_results = load_per_doc_yaml(qa_path)
        qa_by_id = {r["record_id"]: r for r in qa_results}

        for record_id in record_ids:
            record = source_records.get(record_id)
            if not record:
                continue
            old_verdict = qa_by_id.get(record_id, {}).get(args.field, "?")
            passage = extract_window(source, record, args.window)
            prompt = VERIFY_PROMPT.format(
                record_yaml=build_record_yaml(record),
                source_passage=passage,
            )
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    msg = client.messages.create(
                        model=MODEL, max_tokens=MAX_TOKENS,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    new_qa = parse_qa_response(msg.content[0].text, record_id)
                    break
                except anthropic.RateLimitError:
                    delay = RETRY_BASE * (2 ** (attempt - 1))
                    print(f"    Rate limit, waiting {delay}s")
                    time.sleep(delay)
                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        time.sleep(RETRY_BASE * attempt)
                    else:
                        raise
            else:
                new_qa = parse_qa_response("", record_id)

            new_verdict = new_qa.get(args.field, "?")
            changed[f"{old_verdict}→{new_verdict}"] += 1
            qa_by_id[record_id] = new_qa
            all_updated += 1
            flip = " ✓" if new_verdict != old_verdict else ""
            print(f"  {record_id}: {old_verdict} → {new_verdict}{flip}")

        patched = [qa_by_id.get(r["record_id"], r) for r in qa_results]
        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(patched, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"\nDone. {all_updated} records re-checked.")
    print("Verdict changes:")
    for transition, count in sorted(changed.items(), key=lambda x: -x[1]):
        print(f"  {transition}: {count}")


if __name__ == "__main__":
    main()
