"""Step 5: sync Haiku tagging of findings against proposed axes + fill-rate report."""
from __future__ import annotations

import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        "\nReturn JSON with exactly these keys: "
        + ", ".join(a["name"] for a in axes["axes"])
        + ". Each value is either the name of the chosen axis value (string) "
          "or null if no value fits. No prose.\n\nFinding:\n"
    )
    return "\n".join(lines)


def _tag_one(
    client: anthropic.Anthropic,
    model: str,
    system: str,
    idx: int,
    f: dict,
    max_tokens: int,
    valid: dict[str, set[str]],
) -> tuple[int, dict | None, list[tuple[str, str]]]:
    body = f"gloss: {f['gloss']}\ntrigger: {f['trigger']}"
    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": system + body}],
        ) as stream:
            msg = stream.get_final_message()
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return idx, None, []
        parsed = json.loads(m.group(0))
    except Exception:
        return idx, None, []
    invalid: list[tuple[str, str]] = []
    cleaned: dict = {}
    for axis_name, allowed in valid.items():
        v = parsed.get(axis_name)
        if v is None:
            cleaned[axis_name] = None
        elif isinstance(v, str) and v in allowed:
            cleaned[axis_name] = v
        else:
            invalid.append((axis_name, str(v)))
            cleaned[axis_name] = None
    return idx, cleaned, invalid


def tag_findings_sync(
    findings: list[dict],
    axes: dict,
    tags_out: Path,
    *,
    model: str = "claude-haiku-4-5-20251001",
    concurrency: int = 20,
    max_tokens: int = 64_000,
) -> dict[int, dict]:
    """Tag every finding in parallel with Haiku. Writes tags_out, returns map idx→tags."""
    system = _build_tag_prompt(axes)
    valid = {a["name"]: {v["name"] for v in a["values"]} for a in axes["axes"]}
    client = anthropic.Anthropic()
    tags: dict[int, dict] = {}
    invalid_counts: Counter = Counter()
    invalid_total = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [
            ex.submit(_tag_one, client, model, system, i, f, max_tokens, valid)
            for i, f in enumerate(findings)
        ]
        for n, fut in enumerate(as_completed(futs), 1):
            idx, res, invalid = fut.result()
            if res is not None:
                tags[idx] = res
            for axis_name, bad in invalid:
                invalid_counts[(axis_name, bad)] += 1
                invalid_total += 1
            if n % 50 == 0:
                print(f"  {n}/{len(findings)}")
    tags_out.write_text(
        json.dumps([{**f, "tags": tags.get(i, {})} for i, f in enumerate(findings)], indent=2)
    )
    print(f"tagged {len(tags)}/{len(findings)}")
    if invalid_total:
        print(f"dropped {invalid_total} out-of-vocab tag values:")
        for (axis_name, bad), c in invalid_counts.most_common(20):
            print(f"  {axis_name} = {bad!r}: {c}")
        invalid_path = tags_out.with_name(tags_out.stem + "_invalid.json")
        invalid_path.write_text(json.dumps(
            [{"axis": a, "value": v, "count": c} for (a, v), c in invalid_counts.most_common()],
            indent=2,
        ))
    return tags


def write_fill_rate_report(
    findings: list[dict],
    axes: dict,
    tags: dict[int, dict],
    report_path: Path,
    *,
    title: str = "Fill-rate report",
) -> None:
    axis_names = [a["name"] for a in axes["axes"]]
    lines = [f"# {title}\n", f"Findings: {len(findings)}  Tagged: {len(tags)}\n"]
    for name in axis_names:
        vals = [tags.get(i, {}).get(name) for i in range(len(findings))]
        nonnull = [v for v in vals if v]
        fill = len(nonnull) / max(len(vals), 1)
        dist = Counter(str(v) for v in nonnull)
        lines.append(f"\n## {name}")
        lines.append(f"- fill rate: {fill:.1%}")
        lines.append("- value distribution:")
        for val, n in dist.most_common():
            pct = n / max(len(nonnull), 1)
            flag = "  ⚠️" if pct > 0.40 or pct < 0.05 else ""
            lines.append(f"  - {val}: {n} ({pct:.1%}){flag}")
    report_path.write_text("\n".join(lines))
    print(f"wrote {report_path}")
