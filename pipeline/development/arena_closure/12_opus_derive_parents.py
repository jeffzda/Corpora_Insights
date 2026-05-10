#!/usr/bin/env python3
"""Pass 1 of the v2 parent-archetype roll-up.

Single Opus 4.7 call that derives an emergent parent-category set from all
1,141 v2 mechanism-level clusters. Mirrors the legacy stage-5 design
(legacy/code/stage_5_parent_taxonomy/69_rederive_parents.py) with two
deliberate changes:

  1. Opus 4.7 throughout (legacy used Sonnet for this pass).
  2. Catalogue-only inputs — no general_mechanisms, no cooccurrence, no
     candidate merge groups. The roll-up is the new canonical layer; it
     should not inherit unvalidated upstream tagging.

Inputs:
  - corpora/arena/clustering_v2/output/sweep/convergence/catalogue_after_convergence.json
  - corpora/arena/clustering_v2/closure/prompts/12_derive_parents.md

Outputs:
  - corpora/arena/clustering_v2/closure/output/parents_v1.json
  - corpora/arena/clustering_v2/closure/output/parents_v1_meta.json

Cost target: ~$2.20 (anchored to c042 actuals @ Opus 4.7 $15/$75 per M tok).
Wall: ~2 min streaming.
"""
from __future__ import annotations
import json
import random
import re
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]  # corpora/arena/clustering_v2
CATALOGUE = ROOT / 'output/sweep/convergence/catalogue_after_convergence.json'
PROMPT_FILE = ROOT / 'closure/prompts/12_derive_parents.md'
OUT_DIR = ROOT / 'closure/output'
OUT = OUT_DIR / 'parents_v1.json'
META = OUT_DIR / 'parents_v1_meta.json'

MODEL = 'claude-opus-4-7'
MAX_TOKENS = 128000  # Opus 4.7 ceiling — never cap below per project standing instruction
# Opus 4.7 (1M context, claude-opus-4-7) pricing
PRICE_IN_PER_M = 5
PRICE_OUT_PER_M = 25


def build_cluster_block(clusters: list[dict]) -> str:
    """Render clusters as one line each: cluster_id | name | signature | n_records."""
    lines = []
    for c in clusters:
        cid = c['cluster_id']
        name = (c.get('canonical_name') or '').replace('|', '/').strip()
        sig = (c.get('mechanism_signature') or '').replace('|', '/').replace('\n', ' ').strip()
        n = len(c.get('supporting_record_ids', []))
        lines.append(f"  {cid} | {name} | {sig} | {n}")
    return '\n'.join(lines)


def parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1] if '\n' in raw else raw
        if raw.endswith('```'):
            raw = raw.rsplit('```', 1)[0]
    s, e = raw.find('{'), raw.rfind('}')
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(raw[s:e+1])
    except Exception as ex:
        print(f"  JSON parse error: {ex}", flush=True)
        return None


def main():
    print("Loading v2 catalogue...", flush=True)
    cat = json.load(CATALOGUE.open())
    clusters = cat['clusters']
    print(f"  {len(clusters)} clusters loaded", flush=True)

    # Shuffle so input order doesn't anchor the model on any incidental ordering
    random.seed(42)
    shuffled = list(clusters)
    random.shuffle(shuffled)

    print("Loading prompt template...", flush=True)
    prompt_template = PROMPT_FILE.read_text()
    cluster_block = build_cluster_block(shuffled)
    prompt = prompt_template.replace('{cluster_block}', cluster_block)
    print(f"  Prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)", flush=True)

    print(f"\nCalling {MODEL} (max_tokens={MAX_TOKENS:,})...", flush=True)
    client = anthropic.Anthropic()
    parts = []
    started = time.time()
    last_print = started; last_chars = 0; text_chars = 0
    with client.messages.stream(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for ev in stream.text_stream:
            parts.append(ev); text_chars += len(ev)
            now = time.time()
            if now - last_print >= 5:
                rate = (text_chars - last_chars) / max(now - last_print, 1)
                print(f"  [{int(now-started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                      flush=True)
                last_print = now; last_chars = text_chars
        msg = stream.get_final_message()
    raw = ''.join(parts)
    wall = time.time() - started

    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    cost = in_tok / 1e6 * PRICE_IN_PER_M + out_tok / 1e6 * PRICE_OUT_PER_M
    print(f"\n  Wall: {wall:.0f}s  in/out tokens: {in_tok:,}/{out_tok:,}  cost ${cost:.3f}",
          flush=True)
    print(f"  Stop reason: {msg.stop_reason}", flush=True)
    if msg.stop_reason != 'end_turn':
        print(f"  ! Stop reason was {msg.stop_reason!r} — output may be truncated", flush=True)

    parsed = parse_json(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if parsed:
        parents = parsed.get('parents', [])
        unassigned = parsed.get('unassigned', [])
        print(f"\n========== PARENTS PROPOSED ({len(parents)}) ==========")
        for p in parents:
            pid = p.get('parent_id', '?')
            name = p.get('name', '?')
            est = p.get('estimated_population', '?')
            n_ex = len(p.get('exemplar_cluster_ids', []))
            print(f"  [{pid}] {name}  (~{est}, {n_ex} exemplars)")
        if unassigned:
            print(f"\nUnassigned: {len(unassigned)} clusters")
        if parsed.get('notes'):
            print(f"\nNotes: {parsed['notes'][:400]}")
        OUT.write_text(json.dumps(parsed, indent=2))
        print(f"\nWrote {OUT}", flush=True)
    else:
        # Save raw so we don't lose the spend
        OUT.write_text(json.dumps({'parsed_failed': True, 'raw_response': raw}, indent=2))
        print(f"\n! JSON parse failed; raw response saved to {OUT}", flush=True)

    META.write_text(json.dumps({
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'input_tokens': in_tok,
        'output_tokens': out_tok,
        'cost_usd': round(cost, 4),
        'wall_seconds': round(wall, 1),
        'stop_reason': msg.stop_reason,
        'prompt_chars': len(prompt),
        'output_chars': len(raw),
        'n_clusters_input': len(clusters),
        'n_parents_output': len(parsed.get('parents', [])) if parsed else None,
        'n_unassigned_output': len(parsed.get('unassigned', [])) if parsed else None,
    }, indent=2))
    print(f"Wrote {META}", flush=True)


if __name__ == '__main__':
    main()
