#!/usr/bin/env python3
"""
04d: Re-check specific flagged records by passing the full document + tables as context.

Used for documents where the evidence spans multiple sections or where the QA window
missed key context (e.g. project headers, data tables with specific figures).

Usage:
    python scripts/04d_recheck_fulldoc.py --docs 0251,0394          # dry run
    python scripts/04d_recheck_fulldoc.py --docs 0251,0394 --batch submit
    python scripts/04d_recheck_fulldoc.py --batch collect
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    import anthropic
except ImportError:
    raise SystemExit("anthropic not installed.")
try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed.")

ROOT         = Path(__file__).resolve().parents[1]
MARKDOWN_DIR = ROOT / "markdown" / "all"
TABLES_DIR   = ROOT / "tables"
MANIFEST     = ROOT / "manifest.csv"
PER_DOC_DIR  = ROOT / "insights" / "per_doc"
QA_DIR       = ROOT / "insights" / "per_doc_qa"
BATCH_STATE  = QA_DIR / "fulldoc_recheck_batch_state.json"

MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

VERIFY_PROMPT = """\
You are sense-checking an extracted delivery insight record against its full source document.

You have two jobs:

1. GROUNDING: Is what_happened and lesson_learnt supported by the document?
2. CLASSIFICATION: Are the applied taxonomy labels defensible given the document?
   You are not re-classifying — just flagging labels that are clearly wrong or implausible.
   A label is defensible if a reasonable person could apply it given the text, even if another
   label might also fit.

Output ONLY a YAML mapping with these six fields — nothing else:

grounding_verdict: confirmed|plausible|unsupported|fabricated
classification_verdict: ok|questionable|wrong
classification_note: "one sentence — only flag specific labels that are clearly misapplied; null if ok"
source_text: "exact quote from the document that best supports or contradicts the record"
source_page: N   # integer page number from nearest preceding <!-- page N --> marker; null if absent
grounding_note: "one sentence explaining grounding verdict, especially if not confirmed; null if confirmed"

Grounding verdict definitions:
- confirmed: what_happened and lesson_learnt are clearly supported by specific text in the document
- plausible: consistent with the document but supporting text is ambiguous or indirect
- unsupported: makes claims not evidenced anywhere in the document
- fabricated: contains specific details (dates, figures, names, quotes) not present anywhere in the document

Classification verdict definitions:
- ok: all applied labels are defensible given the document
- questionable: one or more labels seem like a stretch but could be argued
- wrong: one or more labels are clearly inconsistent with what the document describes

---

## Record to verify

{record_yaml}

---

## Source document

{source_document}
"""


def load_manifest_hash(md_filename: str) -> str | None:
    """Return the 6-char PDF hash for a markdown filename via manifest."""
    with open(MANIFEST, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            local = row.get("local_path", "")
            # Check if this manifest row corresponds to the markdown file
            # Match by normalising both filenames
            md_stem = Path(md_filename).stem.lower().replace(" ", "_")
            local_stem = Path(local).stem.lower().replace(" ", "_")
            if md_stem in local_stem or local_stem in md_stem:
                m = re.search(r'_([a-f0-9]{6})\.pdf$', local)
                if m:
                    return m.group(1)
    return None


def load_tables(doc_hash: str, cap_chars: int = 80_000) -> str:
    """Load extracted table CSVs for a document, up to cap_chars."""
    if not doc_hash:
        return ""
    tables = sorted(TABLES_DIR.glob(f"*_{doc_hash}_p*_t*.csv"))
    blocks = []
    total = 0
    for tbl in tables:
        txt = tbl.read_text(encoding="utf-8", errors="replace").strip()
        if len(txt) < 30:
            continue
        if total + len(txt) > cap_chars:
            break
        m = re.search(r'_p(\d+)_t(\d+)\.csv$', tbl.name)
        label = f"page {int(m.group(1))}, table {int(m.group(2))}" if m else tbl.stem
        blocks.append(f"### Extracted table ({label})\n```\n{txt}\n```")
        total += len(txt)
    if not blocks:
        return ""
    return "\n\n## Extracted tables\n\n" + "\n\n".join(blocks)


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


def parse_qa_response(text: str, record_id: str) -> dict:
    text = re.sub(r"^```(?:yaml)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict) and "grounding_verdict" in result:
            result["record_id"] = record_id
            return result
    except yaml.YAMLError:
        pass
    print(f"    WARNING: could not parse response for {record_id}")
    return {"record_id": record_id, "grounding_verdict": "parse_error",
            "classification_verdict": "parse_error", "grounding_note": f"parse failed: {text[:200]}"}


def get_flagged_records(doc_stems: list[str]) -> dict[str, list[str]]:
    """Return {doc_stem: [record_ids]} for negative verdicts in given docs."""
    flagged = {}
    for stem in doc_stems:
        qa = yaml.safe_load(open(QA_DIR / f"{stem}_qa.yaml")) or []
        ids = [r["record_id"] for r in qa
               if r.get("grounding_verdict") in ("fabricated", "unsupported")
               or r.get("classification_verdict") == "wrong"]
        if ids:
            flagged[stem] = ids
    return flagged


def build_source(md_filename: str, doc_hash: str) -> str:
    md_path = MARKDOWN_DIR / md_filename
    source = md_path.read_text(encoding="utf-8", errors="replace")
    tables = load_tables(doc_hash)
    return source + tables


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", type=str, default=None,
                        help="Comma-separated doc numbers, e.g. '0251,0394'")
    parser.add_argument("--batch", choices=["submit", "collect"], default=None)
    args = parser.parse_args()

    if args.batch == "collect":
        if not BATCH_STATE.exists():
            raise SystemExit(f"No batch state at {BATCH_STATE}.")
        client = anthropic.Anthropic()
        with open(BATCH_STATE) as f:
            state = json.load(f)

        by_doc = defaultdict(list)
        all_results = []
        for batch_id in state["batch_ids"]:
            batch = client.messages.batches.retrieve(batch_id)
            print(f"Batch {batch_id}: {batch.processing_status}")
            if batch.processing_status != "ended":
                print("  Not ready yet.")
                return
            for result in client.messages.batches.results(batch_id):
                doc_stem, record_id = result.custom_id.split("__", 1)
                old = state["id_map"].get(result.custom_id, {})
                if result.result.type == "succeeded":
                    new_qa = parse_qa_response(result.result.message.content[0].text, record_id)
                else:
                    new_qa = {"record_id": record_id, "grounding_verdict": "api_error",
                              "classification_verdict": "api_error"}
                by_doc[doc_stem].append((record_id, old, new_qa))
                all_results.append((doc_stem, record_id, old, new_qa))

        changed = defaultdict(int)
        for doc_stem, items in sorted(by_doc.items()):
            qa_path = QA_DIR / f"{doc_stem}_qa.yaml"
            qa_list = yaml.safe_load(open(qa_path)) or []
            qa_by_id = {r["record_id"]: r for r in qa_list}
            for record_id, old, new_qa in items:
                g_old = old.get("g", "?")
                g_new = new_qa.get("grounding_verdict", "?")
                c_old = old.get("c", "?")
                c_new = new_qa.get("classification_verdict", "?")
                changed[f"g:{g_old}→{g_new}"] += 1
                changed[f"c:{c_old}→{c_new}"] += 1
                flip = " ✓" if g_new != g_old or c_new != c_old else ""
                print(f"  {record_id}: grounding {g_old}→{g_new}  class {c_old}→{c_new}{flip}")
                qa_by_id[record_id] = new_qa
            patched = [qa_by_id.get(r["record_id"], r) for r in qa_list]
            with open(qa_path, "w", encoding="utf-8") as f:
                yaml.dump(patched, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        print(f"\nDone. {len(all_results)} records updated.")
        print("Changes:")
        for k, v in sorted(changed.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
        return

    # Resolve doc stems
    if not args.docs:
        raise SystemExit("Specify --docs or --batch collect.")
    doc_stems = [f"doc_{d.strip().zfill(4)}" for d in args.docs.split(",")]

    flagged = get_flagged_records(doc_stems)
    total = sum(len(v) for v in flagged.values())
    print(f"Flagged records: {total} across {len(flagged)} docs")

    if not args.batch:
        for stem, ids in flagged.items():
            print(f"  {stem}: {ids}")
        print("\nDry run — pass --batch submit to execute.")
        return

    # Build requests
    client = anthropic.Anthropic()
    requests = []
    id_map = {}

    for doc_stem, record_ids in flagged.items():
        per_doc_path = PER_DOC_DIR / f"{doc_stem}.yaml"
        source_records = {r["record_id"]: r for r in (yaml.safe_load(open(per_doc_path)) or [])}
        md_filename = next((r.get("markdown_filename") for r in source_records.values()
                            if r.get("markdown_filename")), None)
        if not md_filename:
            print(f"  SKIP {doc_stem}: no markdown_filename")
            continue

        doc_hash = load_manifest_hash(md_filename)
        source = build_source(md_filename, doc_hash or "")
        print(f"  {doc_stem}: {len(source):,} chars source ({len(record_ids)} records)")

        qa_by_id = {r["record_id"]: r
                    for r in (yaml.safe_load(open(QA_DIR / f"{doc_stem}_qa.yaml")) or [])}

        for record_id in record_ids:
            record = source_records.get(record_id)
            if not record:
                continue
            custom_id = f"{doc_stem}__{record_id}"
            old_qa = qa_by_id.get(record_id, {})
            id_map[custom_id] = {
                "g": old_qa.get("grounding_verdict", "?"),
                "c": old_qa.get("classification_verdict", "?"),
            }
            prompt = VERIFY_PROMPT.format(
                record_yaml=build_record_yaml(record),
                source_document=source,
            )
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
            })

    print(f"\nSubmitting {len(requests)} requests...")
    batch = client.messages.batches.create(requests=requests)

    # Merge with existing state if present
    if BATCH_STATE.exists():
        existing = json.load(open(BATCH_STATE))
        existing["batch_ids"].append(batch.id)
        existing["id_map"].update(id_map)
        state = existing
    else:
        state = {"batch_ids": [batch.id], "id_map": id_map}

    with open(BATCH_STATE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Submitted: {batch.id}")
    print(f"State now tracks {len(state['batch_ids'])} batch(es), {len(state['id_map'])} records.")
    print("Run --batch collect when done.")


if __name__ == "__main__":
    main()
