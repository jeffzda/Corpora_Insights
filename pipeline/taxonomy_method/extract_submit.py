"""Step 2: submit free-form mechanism extraction batch."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import anthropic

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_findings.md"


def load_prompt(substitutions: dict[str, str]) -> str:
    """Fill {{var}} placeholders in the prompt template."""
    text = PROMPT_PATH.read_text()
    for key, val in substitutions.items():
        text = text.replace("{{" + key + "}}", val)
    if "{{" in text:
        raise SystemExit(f"unfilled placeholder in extract prompt; substitutions={substitutions}")
    return text


def build_extract_requests(
    picks: list[dict],
    *,
    md_path_fn: Callable[[dict], Path],
    custom_id_fn: Callable[[dict], str],
    prompt_substitutions: dict[str, str],
    model: str = "claude-sonnet-4-6",
    max_chars: int = 500_000,
    max_tokens: int = 128_000,
    min_chars: int = 500,
    skip_log: Callable[[str, int], None] | None = None,
) -> list[dict]:
    """Build the list of batch requests from sample picks.

    Separate from submission so wrappers can dry-run (dump requests to JSON
    without hitting the API).
    """
    prompt = load_prompt(prompt_substitutions)
    reqs: list[dict] = []
    for pick in picks:
        md = md_path_fn(pick).read_text(errors="replace")
        if len(md) > max_chars:
            md = md[:max_chars] + "\n\n[TRUNCATED at 500k chars]"
        if len(md.strip()) < min_chars:
            if skip_log:
                skip_log(custom_id_fn(pick), len(md))
            else:
                print(f"skip tiny: {custom_id_fn(pick)} ({len(md)} chars)")
            continue
        reqs.append({
            "custom_id": custom_id_fn(pick),
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{
                    "role": "user",
                    "content": prompt + md,
                }],
            },
        })
    return reqs


def submit_extract_batch(
    requests: list[dict],
    state_path: Path,
) -> str:
    """Submit the batch, persist state, return batch id."""
    client = anthropic.Anthropic()
    print(f"submitting {len(requests)} requests")
    batch = client.messages.batches.create(requests=requests)
    print(f"batch id: {batch.id}")
    print(f"status: {batch.processing_status}")
    state_path.write_text(json.dumps({
        "batch_id": batch.id,
        "n": len(requests),
        "custom_ids": [r["custom_id"] for r in requests],
    }, indent=2))
    return batch.id
