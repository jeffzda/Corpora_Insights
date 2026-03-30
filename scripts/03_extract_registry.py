#!/usr/bin/env python3
"""
Step 3: Extract delivery insight records from grouped markdown files via Anthropic API.

Reads:
  all_agent_groups_v2.json      — 150 groups of ~10 markdown files each
  pilot_100_reports/EXTRACTION_PROMPT.md — extraction prompt template
  pilot_100_reports/taxonomy/ARENA_Taxonomy_v1.2.md — taxonomy (embedded in prompt)

Outputs (one file per group, resumable):
  insights/full_run/group_001.yaml ... group_150.yaml

Usage:
    python scripts/03_extract_registry.py
    python scripts/03_extract_registry.py --groups 1-10        # range
    python scripts/03_extract_registry.py --groups 45          # single group
    python scripts/03_extract_registry.py --resume             # skip completed groups
    python scripts/03_extract_registry.py --dry-run            # print prompt, no API call

Requires:
    pip install anthropic pyyaml
    export ANTHROPIC_API_KEY=sk-ant-...

Notes:
  - Each group uses ~50 ID slots starting at (group_number - 1) * 50 + 1
  - Output files are only written on success; partial runs are safe to resume
  - Rate limit errors are retried with exponential backoff (up to 5 attempts)
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
PROMPT_FILE = ROOT / "pilot_100_reports" / "EXTRACTION_PROMPT.md"
TAXONOMY_FILE = ROOT / "pilot_100_reports" / "taxonomy" / "ARENA_Taxonomy_v1.1.md"
OUT_DIR = ROOT / "insights" / "full_run"

MODEL = "claude-sonnet-4-6"
IDS_PER_GROUP = 50
MAX_RETRIES = 5
RETRY_BASE_DELAY = 10  # seconds


def load_prompt_template() -> str:
    """Load extraction prompt, stripping the 'Documents to process' section placeholder."""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    # Extract just the prompt block inside the first ```...``` fence
    match = re.search(r"## Prompt template\s*```\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: return full file
    return text


def build_prompt(group: list[dict], start_id: int, prompt_template: str) -> str:
    """Assemble the full prompt for one group."""
    doc_sections = []
    for i, rec in enumerate(group, 1):
        md_path = rec.get("md_path", "")
        title = rec.get("Title", Path(md_path).stem if md_path else f"Document {i}")
        kb_url = rec.get("Link to item", "")
        if not md_path or not Path(md_path).exists():
            print(f"  WARNING: markdown not found for '{title}', skipping")
            continue
        content = Path(md_path).read_text(encoding="utf-8", errors="replace")
        # Cap at ~80KB per document to stay within context
        if len(content) > 80_000:
            content = content[:80_000] + "\n\n[TRUNCATED]"
        doc_sections.append(
            f"--- DOCUMENT {i} ---\n"
            f"Title: {title}\n"
            f"KB URL: {kb_url}\n"
            f"Markdown filename: {Path(md_path).name}\n\n"
            f"{content}"
        )

    docs_text = "\n\n".join(doc_sections)
    prompt = prompt_template.replace(
        "[Document list and markdown content appended by the orchestrating script]",
        docs_text,
    ).replace(
        "Start record_id numbering at ARENA-DLV-[START_ID].",
        f"Start record_id numbering at ARENA-DLV-{start_id:04d}.",
    )
    return prompt


def call_api(client: anthropic.Anthropic, prompt: str, group_num: int) -> str:
    """Call Claude API with retry on rate limit / server errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
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
    raise RuntimeError(f"Group {group_num}: API failed after {MAX_RETRIES} attempts")


def parse_yaml_response(response: str, group_num: int) -> list[dict]:
    """Extract YAML records from model response, handling common formatting issues."""
    # Try to find a YAML block
    yaml_match = re.search(r"```(?:yaml)?\s*(.*?)```", response, re.DOTALL)
    yaml_text = yaml_match.group(1).strip() if yaml_match else response.strip()

    # Fix common issue: unquoted colons in string values
    yaml_text = re.sub(
        r'^(\s*\w[\w_]*:\s+)([^"\n]*:[^"\n]*)$',
        lambda m: m.group(1) + '"' + m.group(2).replace('"', '\\"') + '"',
        yaml_text,
        flags=re.MULTILINE,
    )

    try:
        records = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        print(f"  WARNING: YAML parse error in group {group_num}: {e}")
        print("  Saving raw response for manual review.")
        raw_path = OUT_DIR / f"group_{group_num:03d}_raw_error.txt"
        raw_path.write_text(response, encoding="utf-8")
        return []

    if isinstance(records, list):
        return records
    if isinstance(records, dict) and "records" in records:
        return records["records"]
    print(f"  WARNING: unexpected YAML structure in group {group_num}")
    return []


def parse_group_range(spec: str, total: int) -> list[int]:
    """Parse --groups argument: '1-10', '45', or '1,3,5'."""
    groups = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            groups.extend(range(int(a), int(b) + 1))
        else:
            groups.append(int(part))
    return [g for g in groups if 1 <= g <= total]


def main():
    parser = argparse.ArgumentParser(description="Extract ARENA delivery insights via Anthropic API")
    parser.add_argument("--groups", type=str, default=None,
                        help="Groups to process: '1-150', '45', '1,3,5'. Default: all.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip groups that already have output files.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print first prompt and exit without calling API.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(GROUPS_FILE, encoding="utf-8") as f:
        all_groups = json.load(f)
    total = len(all_groups)
    print(f"Loaded {total} groups from {GROUPS_FILE.name}")

    if args.groups:
        group_indices = [g - 1 for g in parse_group_range(args.groups, total)]
    else:
        group_indices = list(range(total))

    if args.resume:
        group_indices = [
            i for i in group_indices
            if not (OUT_DIR / f"group_{i+1:03d}.yaml").exists()
        ]
        print(f"Resuming: {len(group_indices)} groups remaining")

    if not group_indices:
        print("Nothing to do.")
        return

    prompt_template = load_prompt_template()
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    for idx in group_indices:
        group_num = idx + 1
        group = all_groups[idx]
        start_id = idx * IDS_PER_GROUP + 1
        out_path = OUT_DIR / f"group_{group_num:03d}.yaml"

        print(f"\n[{group_num:03d}/{total}] {len(group)} docs, IDs {start_id}–{start_id + IDS_PER_GROUP - 1}")

        prompt = build_prompt(group, start_id, prompt_template)

        if args.dry_run:
            print(f"\n--- DRY RUN PROMPT (first 2000 chars) ---\n{prompt[:2000]}\n...")
            break

        response_text = call_api(client, prompt, group_num)
        records = parse_yaml_response(response_text, group_num)

        if records:
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(records, f, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
            print(f"  Saved {len(records)} records → {out_path.name}")
        else:
            print(f"  WARNING: no records extracted for group {group_num}")


if __name__ == "__main__":
    main()
