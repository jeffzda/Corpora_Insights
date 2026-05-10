"""Step 2 (part b): poll the extract batch and flatten to findings.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic


def _parse_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except Exception as e:
        print(f"  parse error: {e}")
        return []


def collect_extract_batch(
    state_path: Path,
    raw_out: Path,
    findings_out: Path,
) -> dict:
    """Poll the batch; if ended, write raw jsonl and flattened findings.json.

    Returns a small stats dict.
    """
    state = json.loads(state_path.read_text())
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    print(f"status: {batch.processing_status}")
    print(f"counts: {batch.request_counts}")
    if batch.processing_status != "ended":
        return {"status": batch.processing_status}

    raw_lines: list[str] = []
    findings: list[dict] = []
    n_ok = n_err = 0
    for result in client.messages.batches.results(state["batch_id"]):
        cid = result.custom_id
        if result.result.type != "succeeded":
            n_err += 1
            print(f"  {cid}: {result.result.type}")
            continue
        text = result.result.message.content[0].text
        raw_lines.append(json.dumps({"custom_id": cid, "text": text}))
        parsed = _parse_array(text)
        for f in parsed:
            if isinstance(f, dict) and "gloss" in f and "trigger" in f:
                findings.append({
                    "source": cid,
                    "gloss": f["gloss"],
                    "trigger": f["trigger"],
                })
        n_ok += 1
        print(f"  {cid}: {len(parsed)} findings")

    raw_out.write_text("\n".join(raw_lines))
    findings_out.write_text(json.dumps(findings, indent=2))
    print(f"\n{n_ok} succeeded, {n_err} errored")
    print(f"{len(findings)} findings across {n_ok} docs "
          f"(avg {len(findings)/max(n_ok,1):.1f})")
    print(f"wrote {findings_out}")
    return {"status": "ended", "n_ok": n_ok, "n_err": n_err,
            "n_findings": len(findings)}
