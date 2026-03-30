#!/usr/bin/env python3
"""
Step 4b: Verify extracted delivery insight records against their source documents.

For each record in a per_doc YAML, an LLM verifier reads the source markdown and
independently assesses whether the record could have come from it, locates the
supporting text, and flags fabrication or unsupported claims.

Reads:
  insights/per_doc/doc_NNNN.yaml      — extracted records
  markdown/all/<markdown_filename>    — source document
  all_agent_groups_v2.json            — md_path lookup by doc index

Outputs:
  insights/per_doc_qa/doc_NNNN_qa.yaml — one QA result per record

Usage:
    python scripts/04b_verify_extractions.py                  # all per_doc YAMLs
    python scripts/04b_verify_extractions.py --docs 1-11      # range
    python scripts/04b_verify_extractions.py --resume         # skip completed

Model: claude-haiku-4-5 (fast, cheap — verification is simpler than extraction)
Cost:  ~$0.005 per record at $0.25/M input tokens
       ~$15-20 for full 7,000-record corpus
"""

import argparse
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

ROOT = Path(__file__).resolve().parents[1]
GROUPS_FILE = ROOT / "all_agent_groups_v2.json"
PER_DOC_DIR = ROOT / "insights" / "per_doc"
QA_DIR = ROOT / "insights" / "per_doc_qa"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024   # QA response is short — verdict + quote + page + note
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10

VERIFY_PROMPT = """\
You are verifying an extracted delivery insight record against its source document.

For the record below, assess whether it could have reasonably come from the source document.

Output ONLY a YAML mapping with these four fields — nothing else:

verdict: confirmed|plausible|unsupported|fabricated
source_text: "exact quote from the document that best supports or contradicts the record"
source_page: N   # integer page number from the nearest preceding <!-- page N --> marker to your quoted text; null if no markers present
note: "one sentence explaining your verdict, especially if not confirmed"

Verdict definitions:
- confirmed: what_happened and lesson_learnt are clearly supported by specific text in the document
- plausible: consistent with the document but the exact supporting text is ambiguous or indirect
- unsupported: makes claims not evidenced anywhere in the document
- fabricated: contains specific details (dates, figures, names, quotes) not present in the document

For source_text: quote the single most relevant passage verbatim. If unsupported/fabricated,
quote the passage that is closest to what the record claims (to show the gap).

---

## Record to verify

{record_yaml}

---

## Source document

{source_content}
"""


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


def load_per_doc_yaml(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, list):
        return data
    return []


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


def call_api(client: anthropic.Anthropic, prompt: str) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except anthropic.RateLimitError as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"    Rate limit (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s")
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = RETRY_BASE_DELAY * attempt
                print(f"    Server error {e.status_code} (attempt {attempt}/{MAX_RETRIES}), waiting {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"API failed after {MAX_RETRIES} attempts")


def parse_qa_response(response: str, record_id: str) -> dict | None:
    # Strip markdown fences if present
    text = re.sub(r"^```(?:yaml)?\s*\n?", "", response.strip())
    text = re.sub(r"\n?```\s*$", "", text)
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict) and "verdict" in result:
            result["record_id"] = record_id
            return result
    except yaml.YAMLError:
        pass
    print(f"    WARNING: could not parse QA response for {record_id}")
    return {"record_id": record_id, "verdict": "parse_error", "source_text": None,
            "source_page": None, "note": f"QA response parse failed: {response[:200]}"}


def main():
    parser = argparse.ArgumentParser(description="Verify extracted records against source documents")
    parser.add_argument("--docs", type=str, default=None,
                        help="Documents to process: '1-11', '5', '1,3,5'. Default: all.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip documents that already have QA output files.")
    args = parser.parse_args()

    QA_DIR.mkdir(parents=True, exist_ok=True)
    docs = load_documents()
    total = len(docs)

    if args.docs:
        doc_indices = [d - 1 for d in parse_doc_range(args.docs, total)]
    else:
        doc_indices = list(range(total))

    # Only process indices that have a per_doc YAML
    doc_indices = [i for i in doc_indices if (PER_DOC_DIR / f"doc_{i+1:04d}.yaml").exists()]

    if args.resume:
        doc_indices = [i for i in doc_indices
                       if not (QA_DIR / f"doc_{i+1:04d}_qa.yaml").exists()]
        print(f"Resuming: {len(doc_indices)} documents to QA")

    if not doc_indices:
        print("Nothing to do.")
        return

    client = anthropic.Anthropic()
    print(f"Verifying records in {len(doc_indices)} document(s) using {MODEL}")

    total_records = 0
    confirmed = plausible = unsupported = fabricated = errors = 0

    for idx in doc_indices:
        doc_num = idx + 1
        doc = docs[idx]
        per_doc_path = PER_DOC_DIR / f"doc_{doc_num:04d}.yaml"
        qa_path = QA_DIR / f"doc_{doc_num:04d}_qa.yaml"

        records = load_per_doc_yaml(per_doc_path)
        if not records:
            print(f"[{doc_num:04d}] No records — skipping")
            continue

        md_path = doc.get("md_path", "")
        title = doc.get("Title", "Unknown")[:60]
        print(f"\n[{doc_num:04d}] {title} — {len(records)} record(s)")

        if not md_path or not Path(md_path).exists():
            print(f"  SKIP: markdown not found")
            continue

        source_content = Path(md_path).read_text(encoding="utf-8", errors="replace")

        qa_results = []
        for record in records:
            record_id = record.get("record_id", "unknown")
            record_yaml = yaml.dump(
                {k: v for k, v in record.items()
                 if k in ("record_id", "what_happened", "lesson_learnt", "failure_mode",
                           "outcome_class", "lifecycle_phase", "evidence_excerpt",
                           "issue_severity", "intervention_note")
                 and v},
                allow_unicode=True, default_flow_style=False
            ).strip()

            prompt = VERIFY_PROMPT.format(
                record_yaml=record_yaml,
                source_content=source_content,
            )

            response = call_api(client, prompt)
            result = parse_qa_response(response, record_id)
            if result:
                qa_results.append(result)
                v = result.get("verdict", "")
                if v == "confirmed":    confirmed += 1
                elif v == "plausible":  plausible += 1
                elif v == "unsupported": unsupported += 1
                elif v == "fabricated": fabricated += 1
                else:                   errors += 1
                print(f"  {record_id}: {v}")

        with open(qa_path, "w", encoding="utf-8") as f:
            yaml.dump(qa_results, f, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)
        print(f"  → {qa_path.name}")
        total_records += len(qa_results)

    print(f"\nDone. {total_records} records verified.")
    print(f"  confirmed={confirmed}  plausible={plausible}  "
          f"unsupported={unsupported}  fabricated={fabricated}  errors={errors}")
    if total_records:
        pct = lambda n: f"{100*n/total_records:.0f}%"
        print(f"  Supported rate: {pct(confirmed+plausible)}  "
              f"Problem rate: {pct(unsupported+fabricated)}")


if __name__ == "__main__":
    main()
