"""Step 5 (batch variant): Haiku batch-tag findings against proposed axes.

Alternative to `tag_sync` — use when throughput matters more than latency.
`tag_sync` is simpler and faster for small (<5k) finding sets.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic


def _build_tag_prompt(axes: dict) -> str:
    lines = ["You will tag a single finding against the following axes."]
    for ax in axes["axes"]:
        lines.append(f"\n## {ax['name']}")
        lines.append(ax["description"])
        lines.append("Values:")
        for v in ax["values"]:
            lines.append(f"  - {v['name']}: {v['definition']}")
    lines.append(
        "\nTag the finding below. Return JSON with keys matching "
        "axis names, plus a 'null_reasons' object mapping axis "
        "names to a short reason if the axis is not applicable "
        "(omit the axis name entirely if it IS applicable). "
        "Use null for an axis value when no value fits."
    )
    lines.append("\nReturn JSON only, no prose.\n\nFinding:\n")
    return "\n".join(lines)


def submit_tag_batch(
    findings: list[dict],
    axes: dict,
    state_path: Path,
    *,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 64_000,
) -> str:
    prompt = _build_tag_prompt(axes)
    client = anthropic.Anthropic()
    reqs = []
    for i, f in enumerate(findings):
        body = f"gloss: {f['gloss']}\ntrigger: {f['trigger']}"
        reqs.append({
            "custom_id": f"f{i:05d}",
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt + body}],
            },
        })
    batch = client.messages.batches.create(requests=reqs)
    print(f"batch id: {batch.id} ({len(reqs)} reqs)")
    state_path.write_text(json.dumps({"batch_id": batch.id, "n": len(reqs)}, indent=2))
    return batch.id


def collect_tag_batch(
    findings: list[dict],
    state_path: Path,
) -> dict[int, dict]:
    state = json.loads(state_path.read_text())
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"status: {batch.processing_status}  counts: {batch.request_counts}")
    if batch.processing_status != "ended":
        return {}

    tags_by_idx: dict[int, dict] = {}
    for result in client.messages.batches.results(state["batch_id"]):
        if result.result.type != "succeeded":
            continue
        idx = int(result.custom_id[1:])
        text = result.result.message.content[0].text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            continue
        try:
            tags_by_idx[idx] = json.loads(m.group(0))
        except Exception:
            continue
    return tags_by_idx
