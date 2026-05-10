#!/usr/bin/env python3
"""Closure phase 2 (Option B, executed properly): Opus 4.7 one-shot merge-group finder.

Reads the entire 1,141-cluster catalogue in one call to Opus 4.7. Asks for groups
of clusters that describe the same causal mechanism. Output: a single list of
proposed merge groups across the whole catalogue.

Why one-shot over the whole catalogue (not chunked, not shortlisted):
  - Embeddings shortlist on vocabulary, missing same-mechanism-different-perspective
    pairs (we showed c027 ↔ c738 at only cos 0.56 despite being a real merge candidate)
  - Qwen 7B 4-bit was too weak for the judgement task itself (force-fit AND over-reject)
  - Sonnet/Opus 4.6/4.7 have 200k+ context — the whole 57k-token catalogue fits
  - The "one-shot beats chunked on rule-application tasks" finding (validated today
    in dedup and clustering) argues for one call over chunking
  - Cross-region candidates that any chunking design would miss are caught

Why Opus (not Sonnet):
  - Subtle semantic-mechanism discrimination is exactly the failure axis where
    smaller models err. Spend $1.60 instead of $0.50 to get the right answer.

Estimate: ~$1-2 sync, ~3-5 min wall.
"""
import argparse
import json
import re
import time
from pathlib import Path

import anthropic

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
GROUPS_OUT = CLOSURE_OUT / 'merge_groups_opus.json'
RAW_OUT = CLOSURE_OUT / 'opus_raw_output.txt'
META_OUT = CLOSURE_OUT / 'opus_groupfinder_meta.json'


PROMPT_HEADER = """You are auditing a catalogue of failure-mode clusters extracted from a renewable-energy project corpus. Each cluster has a canonical name and a mechanism signature (a one-sentence statement of the causal pathway it describes).

Your task: identify any GROUPS of clusters in this catalogue that describe the SAME causal failure mechanism — clusters that should be merged. Two clusters belong in a merge group if their mechanism signatures describe the same causal pathway, even if:
- they use different surface vocabulary
- they look at the mechanism from different perspectives (e.g., one party's loss is another party's gain — same mechanism, opposite framings)
- they apply to different technologies / projects / domains as long as the causal structure is identical

Two clusters do NOT belong in a merge group if:
- they share topic vocabulary but describe different causal pathways (e.g., both about "voltage" but one is about regulation, one about disconnection)
- they are mechanistically adjacent but distinct (e.g., siblings within a parent category, but with different proximate causes)
- one is a more general statement than the other (categorical containment is not equivalence)

Most clusters in the catalogue will not belong to any merge group. Be precise — only flag groups where you are confident the clusters describe the same mechanism. A group can be 2 clusters or more.

# CATALOGUE
"""

PROMPT_FOOTER = """\

# OUTPUT FORMAT — STRICT

Return JSON only. First character `{`, last character `}`. No preamble, no markdown fences.

Schema:
{
  "merge_groups": [
    {"members": ["c001", "c042"], "rationale": "<one sentence stating the shared mechanism>"},
    ...
  ]
}

If no merge groups exist, return {"merge_groups": []}."""


def stream_call(client, prompt, model, max_tokens=32000, raw_path=None):
    """Stream with progress + accumulate. Returns (text, msg)."""
    raw_f = open(raw_path, 'w') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []
    msg = None
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for ev in stream.text_stream:
                if raw_f: raw_f.write(ev); raw_f.flush()
                parts.append(ev); text_chars += len(ev)
                now = time.time()
                if now - last_print >= 5:
                    rate = (text_chars - last_chars) / max(now - last_print, 1)
                    print(f"  [{int(now - started)}s] {text_chars:,} chars  +{rate:.0f} c/s",
                          flush=True)
                    last_print = now; last_chars = text_chars
            msg = stream.get_final_message()
    finally:
        if raw_f: raw_f.close()
    return ''.join(parts), msg


def parse_response(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text
    first = body.find('{'); last = body.rfind('}')
    if first >= 0 and last > first:
        try: return json.loads(body[first:last+1])
        except: pass
    # Tolerant: extract complete {...} objects following "members"
    groups = []
    for m in re.finditer(r'\{\s*"members"\s*:\s*\[([^\]]*)\]\s*,?\s*"rationale"\s*:\s*"([^"]*)"\s*\}',
                          body, re.DOTALL):
        try:
            members = [x.strip().strip('"') for x in m.group(1).split(',') if x.strip()]
            members = [m for m in members if m]
            groups.append({'members': members, 'rationale': m.group(2)})
        except: pass
    return {'merge_groups': groups, '_recovered': True} if groups else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='claude-opus-4-7')
    args = ap.parse_args()

    print(f"Loading catalogue from {CATALOGUE}...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    print(f"  {len(catalogue)} clusters", flush=True)

    # Build full-catalogue block
    block_lines = []
    for c in catalogue:
        block_lines.append(f"\n[{c['cluster_id']}] {c['canonical_name']}")
        block_lines.append(f"  mechanism: {c.get('mechanism_signature','')}")
    catalogue_block = ''.join(block_lines)
    prompt = PROMPT_HEADER + catalogue_block + PROMPT_FOOTER
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model}...", flush=True)
    t0 = time.time()
    text, msg = stream_call(client, prompt, args.model, raw_path=RAW_OUT)
    wall = time.time() - t0
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out", flush=True)
    # Opus 4.7 pricing: $15/M input, $75/M output
    cost = msg.usage.input_tokens/1e6*15 + msg.usage.output_tokens/1e6*75
    print(f"  cost: ${cost:.2f}", flush=True)

    parsed = parse_response(text)
    if not parsed or 'merge_groups' not in parsed:
        print(f"\n  PARSE ERROR — see {RAW_OUT}", flush=True)
        return
    groups = parsed['merge_groups']
    valid_ids = {c['cluster_id'] for c in catalogue}
    cleaned = []
    for g in groups:
        members = sorted({m for m in (g.get('members') or []) if m in valid_ids})
        if len(members) >= 2:
            cleaned.append({'members': members, 'rationale': g.get('rationale', '')})
    cleaned.sort(key=lambda g: -len(g['members']))

    GROUPS_OUT.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False))
    META_OUT.write_text(json.dumps({
        'model': args.model,
        'input_tokens': msg.usage.input_tokens,
        'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3),
        'wall_seconds': round(wall, 1),
        'n_groups_proposed': len(groups),
        'n_groups_cleaned': len(cleaned),
        'catalogue_size': len(catalogue),
    }, indent=2))

    print(f"\n=== DONE ===")
    print(f"  merge groups proposed: {len(groups)}")
    print(f"  after cleaning (≥2 valid members): {len(cleaned)}")
    from collections import Counter
    sz = Counter(len(g['members']) for g in cleaned)
    print(f"  size distribution:")
    for s in sorted(sz):
        print(f"    {s}-cluster groups: {sz[s]}")
    n_clusters_affected = len({m for g in cleaned for m in g['members']})
    print(f"  total clusters in proposed merges: {n_clusters_affected} of {len(catalogue)} "
          f"({100*n_clusters_affected/len(catalogue):.1f}%)")


if __name__ == "__main__":
    main()
