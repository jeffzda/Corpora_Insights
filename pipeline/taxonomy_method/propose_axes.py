"""Step 3: single Sonnet call that proposes 2-4 orthogonal axes over findings."""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

PROMPT_PATH = Path(__file__).parent / "prompts" / "propose_axes.md"


def _load_prompt(substitutions: dict[str, str]) -> str:
    text = PROMPT_PATH.read_text()
    for k, v in substitutions.items():
        text = text.replace("{{" + k + "}}", v)
    if "{{" in text:
        raise SystemExit(f"unfilled placeholder in propose-axes prompt; substitutions={substitutions}")
    return text


def propose_axes(
    findings: list[dict],
    out_path: Path,
    *,
    prompt_substitutions: dict[str, str],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 128_000,
    prompt_path: Path = PROMPT_PATH,
) -> dict:
    """Build prompt, call model, parse JSON, write to out_path. Return parsed dict."""
    text = prompt_path.read_text()
    for k, v in prompt_substitutions.items():
        text = text.replace("{{" + k + "}}", v)
    if "{{" in text:
        raise SystemExit(f"unfilled placeholder in prompt {prompt_path.name}; substitutions={prompt_substitutions}")
    body = text + json.dumps(findings, indent=1)
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": body}],
    ) as stream:
        msg = stream.get_final_message()
    text = msg.content[0].text
    if "```" in text:
        chunks = text.split("```")
        for c in chunks:
            c = c.lstrip()
            if c.startswith("json\n"):
                c = c[5:]
            if c.lstrip().startswith("{"):
                text = c
                break
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start:end + 1]
    try:
        parsed = json.loads(text)
    except Exception as e:
        print(f"parse error: {e}")
        out_path.with_suffix(".raw.txt").write_text(msg.content[0].text)
        raise
    out_path.write_text(json.dumps(parsed, indent=2))
    print(f"wrote {out_path}")
    print(f"axes proposed: {[a['name'] for a in parsed.get('axes', [])]}")
    print(f"input tokens: {msg.usage.input_tokens}  output: {msg.usage.output_tokens}")
    return parsed
