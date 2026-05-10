"""Streaming + cost calculation helper for Anthropic API calls.

Extracted from corpora/arena/clustering_v2/closure/code/03_opus_groupfinder.py
and standardised across pipeline stages.

Standing-instruction compliance:
- Heartbeat output every ~5s with cumulative chars + rate
- Never silent; flush=True everywhere
- Returns (text, msg, cost_usd, wall_seconds)
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Optional, Tuple, Any


# Anthropic pricing (USD per million tokens). See reference_anthropic_pricing memory.
PRICING = {
    'claude-opus-4-7':       (5.0,  25.0),
    'claude-opus-4-6':       (5.0,  25.0),
    'claude-sonnet-4-6':     (3.0,  15.0),
    'claude-haiku-4-5-20251001': (0.80, 4.0),
}


def model_cost(model: str, in_tokens: int, out_tokens: int, batch_discount: bool = False) -> float:
    """Compute cost in USD for a given (model, input_tokens, output_tokens)."""
    if model not in PRICING:
        # Conservative fallback to Opus pricing
        in_per_m, out_per_m = 5.0, 25.0
    else:
        in_per_m, out_per_m = PRICING[model]
    multiplier = 0.5 if batch_discount else 1.0
    return (in_tokens / 1e6 * in_per_m + out_tokens / 1e6 * out_per_m) * multiplier


def stream_call(
    client: Any,
    prompt: str,
    model: str,
    max_tokens: int,
    raw_path: Optional[Path] = None,
    label: str = 'call',
    temperature: Optional[float] = None,
    heartbeat_seconds: float = 5.0,
) -> Tuple[str, Any, float, float]:
    """Stream an Anthropic message call with progress heartbeat.

    Returns (text, msg, cost_usd, wall_seconds).

    - `client`: anthropic.Anthropic() instance
    - `prompt`: full user message text
    - `model`: model id (must be a key in PRICING for accurate cost)
    - `max_tokens`: ceiling for output. Per CLAUDE.md, never cap below model ceiling.
    - `raw_path`: optional Path to write streaming text incrementally (audit trail)
    - `label`: prefix for heartbeat lines (e.g. 'p1-i7' or 'batch3/14')
    - `temperature`: optional; some models (Opus 4.7) reject temperature
    - `heartbeat_seconds`: seconds between progress lines
    """
    raw_f = open(raw_path, 'w', encoding='utf-8') if raw_path else None
    started = time.time()
    last_print = 0.0
    last_chars = 0
    text_chars = 0
    parts = []
    msg = None

    stream_kwargs = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if temperature is not None:
        stream_kwargs['temperature'] = temperature

    try:
        with client.messages.stream(**stream_kwargs) as stream:
            for ev in stream.text_stream:
                if raw_f:
                    raw_f.write(ev)
                    raw_f.flush()
                parts.append(ev)
                text_chars += len(ev)
                now = time.time()
                if now - last_print >= heartbeat_seconds:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    print(f'  [{label}] [{int(now - started)}s] {text_chars:,} chars  +{rate:.0f} c/s',
                          flush=True)
                    last_print = now
                    last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f:
            raw_f.close()

    text = ''.join(parts)
    wall = time.time() - started
    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    cost = model_cost(model, in_tok, out_tok)
    print(f'  [{label}] done: {wall:.0f}s  {in_tok:,}in/{out_tok:,}out  ${cost:.3f}',
          flush=True)
    return text, msg, cost, wall
