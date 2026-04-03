#!/usr/bin/env python3
"""
Cluster failure mode narratives bottom-up to discover natural categories.

Phase 1 (batch submit): Send 500 sampled records to Haiku. For each record,
         ask the LLM to describe the root cause in 5-10 words — no predefined
         categories, just "what actually went wrong here?"

Phase 2 (batch collect): Retrieve results, write root-cause tags alongside
         the original narratives.

Phase 3 (cluster): Feed all 500 root-cause tags to a single LLM call and ask
         it to propose natural groupings.

Reads:   insights/failure_mode_sample.yaml  (500 records from 4 problematic categories)
Writes:  insights/failure_mode_cluster/batch_state.json
         insights/failure_mode_cluster/tagged_records.yaml
         insights/failure_mode_cluster/proposed_clusters.md

Usage:
    python scripts/cluster_failure_modes.py --batch submit
    python scripts/cluster_failure_modes.py --batch collect
    python scripts/cluster_failure_modes.py --cluster
"""

import argparse
import json
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

ROOT        = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT / "insights" / "failure_mode_sample.yaml"
OUT_DIR     = ROOT / "insights" / "failure_mode_cluster"
BATCH_STATE = OUT_DIR / "batch_state.json"
TAGGED_FILE = OUT_DIR / "tagged_records.yaml"
CLUSTER_FILE = OUT_DIR / "proposed_clusters.md"

MODEL       = "claude-haiku-4-5-20251001"
MAX_TOKENS  = 256

TAG_PROMPT = """\
You are analysing a delivery insight record from an Australian renewable energy project.

The record describes something that went wrong during the project. Your job is to identify
the specific root cause — not the consequence, not the category, just what concretely went
wrong.

Respond with ONLY a YAML block like this:

```yaml
root_cause: "<5-10 word description of what specifically went wrong>"
cause_detail: "<1 sentence elaborating on the root cause>"
```

Rules:
- Be concrete and specific, not abstract. "Inverter couldn't handle site temperatures" not
  "design assumption failure" or "technical issue."
- Describe the CAUSE, not the CONSEQUENCE. "Supplier went bankrupt" not "schedule slippage."
  "Grid connection standards changed mid-project" not "regulatory misfit."
- If the record describes multiple things going wrong, pick the primary/root cause.
- Do NOT use any existing taxonomy labels. Use plain language.

Here is the record:

record_id: {record_id}

what_happened: {what_happened}

lesson_learnt: {lesson_learnt}

evidence_excerpt: {evidence_excerpt}
"""


def load_sample() -> list[dict]:
    with open(SAMPLE_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def parse_tag_response(text: str, record_id: str) -> dict:
    """Extract root_cause and cause_detail from LLM response."""
    import re
    result = {"record_id": record_id, "root_cause": None, "cause_detail": None}

    # Try to parse YAML block
    yaml_match = re.search(r"```yaml\s*\n(.*?)```", text, re.DOTALL)
    content = yaml_match.group(1) if yaml_match else text

    try:
        parsed = yaml.safe_load(content)
        if isinstance(parsed, dict):
            result["root_cause"] = parsed.get("root_cause")
            result["cause_detail"] = parsed.get("cause_detail")
            return result
    except yaml.YAMLError:
        pass

    # Fallback: look for root_cause: line
    for line in text.split("\n"):
        line = line.strip()
        if line.lower().startswith("root_cause:"):
            result["root_cause"] = line.split(":", 1)[1].strip().strip('"')
        elif line.lower().startswith("cause_detail:"):
            result["cause_detail"] = line.split(":", 1)[1].strip().strip('"')

    if not result["root_cause"]:
        result["root_cause"] = f"parse_error: {text[:100]}"

    return result


# ── Batch submit ─────────────────────────────────────────────────────────────

def run_batch_submit():
    client = anthropic.Anthropic()
    records = load_sample()
    print(f"Building prompts for {len(records)} sampled records...")

    requests = []
    for rec in records:
        record_id = rec.get("record_id", "unknown")
        prompt = TAG_PROMPT.format(
            record_id=record_id,
            what_happened=rec.get("what_happened", ""),
            lesson_learnt=rec.get("lesson_learnt", ""),
            evidence_excerpt=rec.get("evidence_excerpt", ""),
        )
        # custom_id: only [a-zA-Z0-9_-], max 64 chars
        custom_id = record_id.replace("-", "_")
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    batch = client.messages.batches.create(requests=requests)
    print(f"  Submitted batch: {batch.id}  ({len(requests)} requests)")

    state = {"batch_id": batch.id, "total_requests": len(requests)}
    with open(BATCH_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"  Batch state saved to {BATCH_STATE}")
    print("  Run with --batch collect when processing is complete.")


# ── Batch collect ────────────────────────────────────────────────────────────

def run_batch_collect():
    if not BATCH_STATE.exists():
        raise SystemExit(f"No batch state at {BATCH_STATE}. Run --batch submit first.")

    client = anthropic.Anthropic()
    with open(BATCH_STATE, encoding="utf-8") as f:
        state = json.load(f)

    batch_id = state["batch_id"]
    batch = client.messages.batches.retrieve(batch_id)
    print(f"Batch {batch_id}: {batch.processing_status}")

    if batch.processing_status != "ended":
        print("  Not ready yet — try again later.")
        return

    # Load original sample for joining
    sample = load_sample()
    sample_by_id = {r["record_id"]: r for r in sample}

    tagged = []
    errors = 0
    for result in client.messages.batches.results(batch_id):
        record_id = result.custom_id.replace("_", "-", 3)  # restore ARENA-DLV-NNNN
        # More robust: ARENA_DLV_NNNNN → ARENA-DLV-NNNNN
        record_id = record_id.replace("ARENA_DLV_", "ARENA-DLV-", 1)

        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            tag = parse_tag_response(text, record_id)
        else:
            tag = {"record_id": record_id, "root_cause": "api_error",
                   "cause_detail": str(result.result)[:200]}
            errors += 1

        # Join with original record
        orig = sample_by_id.get(record_id, {})
        tagged.append({
            "record_id": record_id,
            "original_failure_mode": orig.get("failure_mode"),
            "what_happened": orig.get("what_happened"),
            "lesson_learnt": orig.get("lesson_learnt"),
            "root_cause": tag["root_cause"],
            "cause_detail": tag["cause_detail"],
        })

    with open(TAGGED_FILE, "w", encoding="utf-8") as f:
        yaml.dump(tagged, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"\n{len(tagged)} records tagged  ({errors} errors)")
    print(f"Written to {TAGGED_FILE}")

    # Print some examples
    print("\nSample root causes:")
    for rec in tagged[:20]:
        print(f"  [{rec['original_failure_mode'][:20]:20s}] {rec['root_cause']}")

    print(f"\nRun with --cluster to propose natural groupings.")


# ── Cluster ──────────────────────────────────────────────────────────────────

def run_cluster():
    if not TAGGED_FILE.exists():
        raise SystemExit(f"No tagged records at {TAGGED_FILE}. Run --batch collect first.")

    with open(TAGGED_FILE, encoding="utf-8") as f:
        tagged = yaml.safe_load(f) or []

    print(f"Clustering {len(tagged)} root-cause tags...")

    # Build a compact list for the LLM
    lines = []
    for rec in tagged:
        lines.append(f"- [{rec.get('original_failure_mode', '?')}] {rec['root_cause']}"
                      f" — {rec.get('cause_detail', '')}")

    cluster_prompt = f"""\
You are helping design a failure mode taxonomy for a registry of delivery insight records
from Australian renewable energy projects funded by ARENA.

Below are 500 root-cause descriptions extracted from project failure narratives. Each line
shows the original (flawed) taxonomy label in brackets, followed by a concrete root-cause
description and a one-sentence elaboration.

Your job:
1. Read all 500 root causes
2. Identify natural clusters — groups of root causes that describe the same KIND of thing
   going wrong, at the same level of abstraction
3. Propose 6-12 failure mode categories that emerge from the data
4. For each proposed category:
   - Name it (clear, concrete, 2-5 words)
   - Define it in one sentence
   - List 5-8 example root causes from the data that belong in it
   - Estimate what % of the 500 records would fall into it
   - Note which of the original taxonomy labels it draws from
5. Flag any root causes that don't fit cleanly into any category
6. Note any categories where boundary ambiguity is likely to cause classification disputes

Design principles:
- Categories should be CAUSES, not CONSEQUENCES (no "cost overrun" or "schedule delay")
- Categories should be at a consistent level of abstraction
- Categories should be mutually exclusive in most cases
- Each category should answer a specific PM due diligence question
- Avoid catch-all categories that could absorb anything

Root causes:

{chr(10).join(lines)}
"""

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": cluster_prompt}],
    )

    output = msg.content[0].text

    with open(CLUSTER_FILE, "w", encoding="utf-8") as f:
        f.write("# Failure Mode Clustering — Bottom-Up Analysis\n\n")
        f.write(f"Based on {len(tagged)} root-cause tags from sampled records.\n\n")
        f.write("---\n\n")
        f.write(output)

    print(f"\nClustering complete. Written to {CLUSTER_FILE}")
    print(f"\nFirst 2000 chars of output:\n")
    print(output[:2000])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cluster failure mode narratives bottom-up")
    parser.add_argument("--batch", choices=["submit", "collect"],
                        help="Batch API: 'submit' to send, 'collect' to retrieve")
    parser.add_argument("--cluster", action="store_true",
                        help="Run clustering on collected root-cause tags (uses Sonnet)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch == "submit":
        run_batch_submit()
    elif args.batch == "collect":
        run_batch_collect()
    elif args.cluster:
        run_cluster()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
