#!/usr/bin/env python3
"""Closure phase 2 v2: Opus group-finder with greedy nearest-neighbour ordering.

Same one-shot Opus pass as 03_opus_groupfinder.py, but the catalogue is
rendered in a greedy nearest-neighbour path through the embedding space,
not in cluster_id order.

Why it should help:
  - In cluster_id order, similar clusters are scattered randomly across
    the 80k-token prompt. Opus's attention has to bridge long distances
    to compare them. Effect: pairs far apart in prompt order get missed
    (we showed Opus missed c027 ↔ c738 in the cluster_id-order pass)
  - In greedy NN order, every cluster is adjacent to its embedding-nearest
    neighbour. Similar clusters land next to each other in the prompt;
    Opus's local-attention windows naturally compare them
  - No chunk boundaries — every pair has a reachable position in the path

Algorithm (greedy nearest neighbour):
  1. Start at cluster index 0
  2. Find the nearest unvisited cluster (highest cosine similarity), add it
  3. Repeat until all visited
  4. Render catalogue in this order

The walk can occasionally make a long jump when a region is exhausted — this
is fine; it just means a region boundary in the path. We accept this for
simplicity (alternative: 2-opt or spectral ordering, marginal benefit).

Cost: same as v1 (~$1.74). Just different prompt order.
"""
import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import anthropic

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
EMB_FILE = CLOSURE_OUT / 'cluster_embeddings.npy'
IDS_FILE = CLOSURE_OUT / 'cluster_ids.json'
PATH_OUT = CLOSURE_OUT / 'nn_path_order.json'
# Output paths set per-model in main()


def greedy_nn_order(embs, start_idx=0):
    """Greedy nearest-neighbour traversal through unit-normalised embeddings."""
    n = embs.shape[0]
    visited = np.zeros(n, dtype=bool)
    order = []
    current = start_idx
    visited[current] = True
    order.append(current)
    for step in range(n - 1):
        sims = embs @ embs[current]
        sims[visited] = -np.inf
        next_idx = int(np.argmax(sims))
        order.append(next_idx)
        visited[next_idx] = True
        current = next_idx
    return order


PROMPT_HEADER = """You are auditing a catalogue of failure-mode clusters extracted from a renewable-energy project corpus. Each cluster has a canonical name and a mechanism signature (a one-sentence statement of the causal pathway).

The catalogue below has been ORDERED so that semantically-similar clusters appear adjacent (each cluster's neighbour in the listing is its nearest match by embedding similarity). Most genuine merge candidates will therefore appear in close proximity to each other in the listing.

Your task: identify any GROUPS of clusters that describe the SAME causal failure mechanism — clusters that should be merged. Two clusters belong in a merge group if their mechanism signatures describe the same causal pathway, even if:
- they use different surface vocabulary
- they look at the mechanism from different perspectives (e.g., one party's loss is another party's gain — same mechanism, opposite framings)
- they apply to different technologies / projects / domains as long as the causal structure is identical

Two clusters do NOT belong in a merge group if:
- they share topic vocabulary but describe different causal pathways
- they are mechanistically adjacent but distinct (siblings within a parent category, with different proximate causes — sibling ≠ duplicate)
- one is a more general statement than the other (categorical containment is not equivalence)
- the same outcome is reached through different proximate causes (different mechanisms, same outcome)

Be precise. Sibling mechanisms within the same category should remain SEPARATE — only merge when the underlying causal pathway is the same.

# CATALOGUE (ordered by greedy nearest-neighbour traversal)
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
    raw_f = open(raw_path, 'w') if raw_path else None
    started = time.time()
    last_print = 0; last_chars = 0; text_chars = 0
    parts = []; msg = None
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
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='claude-opus-4-7')
    ap.add_argument('--start-idx', type=int, default=0)
    args = ap.parse_args()
    # Output paths tagged by model (short tag)
    model_tag = 'opus' if 'opus' in args.model else ('sonnet' if 'sonnet' in args.model else 'haiku')
    GROUPS_OUT = CLOSURE_OUT / f'merge_groups_{model_tag}_nnpath.json'
    RAW_OUT = CLOSURE_OUT / f'{model_tag}_nnpath_raw.txt'
    META_OUT = CLOSURE_OUT / f'{model_tag}_nnpath_meta.json'

    print("Loading inputs...", flush=True)
    catalogue = json.load(open(CATALOGUE))['clusters']
    embs = np.load(EMB_FILE)
    cluster_ids_in_emb_order = json.load(open(IDS_FILE))
    print(f"  catalogue: {len(catalogue)} clusters; embeddings: {embs.shape}", flush=True)
    assert len(catalogue) == embs.shape[0]
    cid_to_meta = {c['cluster_id']: c for c in catalogue}

    # Greedy NN ordering
    print(f"Computing greedy nearest-neighbour ordering (start_idx={args.start_idx})...", flush=True)
    t0 = time.time()
    order = greedy_nn_order(embs, start_idx=args.start_idx)
    print(f"  ordering done in {time.time()-t0:.1f}s; {len(order)} clusters in path", flush=True)
    ordered_cluster_ids = [cluster_ids_in_emb_order[i] for i in order]
    PATH_OUT.write_text(json.dumps(ordered_cluster_ids, indent=2))

    # Path-quality metric: mean adjacent-pair similarity
    sims = [float(embs[order[i]] @ embs[order[i+1]]) for i in range(len(order)-1)]
    print(f"  adjacent-pair sim: mean {np.mean(sims):.3f}, "
          f"median {np.median(sims):.3f}, "
          f"min {min(sims):.3f}, max {max(sims):.3f}", flush=True)

    # Build prompt with NN-ordered catalogue
    block_lines = []
    for cid in ordered_cluster_ids:
        c = cid_to_meta[cid]
        block_lines.append(f"\n[{cid}] {c['canonical_name']}")
        block_lines.append(f"  mechanism: {c.get('mechanism_signature','')}")
    prompt = PROMPT_HEADER + ''.join(block_lines) + PROMPT_FOOTER
    print(f"  prompt size: {len(prompt):,} chars (~{len(prompt)//4:,} tok)", flush=True)

    client = anthropic.Anthropic()
    print(f"\nCalling {args.model} on NN-ordered catalogue...", flush=True)
    t0 = time.time()
    text, msg = stream_call(client, prompt, args.model, raw_path=RAW_OUT)
    wall = time.time() - t0
    print(f"\n  generation done: {len(text):,} chars in {wall:.0f}s", flush=True)
    PRICES = {'opus': (15, 75), 'sonnet': (3, 15), 'haiku': (0.80, 4)}
    in_p, out_p = PRICES.get(model_tag, (15, 75))
    cost = msg.usage.input_tokens/1e6*in_p + msg.usage.output_tokens/1e6*out_p
    print(f"  tokens: {msg.usage.input_tokens:,}in / {msg.usage.output_tokens:,}out", flush=True)
    print(f"  cost: ${cost:.2f}", flush=True)

    parsed = parse_response(text)
    groups = (parsed or {}).get('merge_groups') or []
    valid_ids = {c['cluster_id'] for c in catalogue}
    cleaned = []
    for g in groups:
        members = sorted({m for m in (g.get('members') or []) if m in valid_ids})
        if len(members) >= 2:
            cleaned.append({'members': members, 'rationale': g.get('rationale', '')})
    cleaned.sort(key=lambda g: -len(g['members']))

    GROUPS_OUT.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False))
    META_OUT.write_text(json.dumps({
        'model': args.model, 'ordering': 'greedy_nearest_neighbour',
        'start_idx': args.start_idx,
        'input_tokens': msg.usage.input_tokens, 'output_tokens': msg.usage.output_tokens,
        'cost_sync': round(cost, 3), 'wall_seconds': round(wall, 1),
        'n_groups': len(cleaned), 'n_clusters_affected': len({m for g in cleaned for m in g['members']}),
        'mean_adjacent_sim': round(float(np.mean(sims)), 4),
    }, indent=2))

    print(f"\n=== DONE ===")
    print(f"  merge groups: {len(cleaned)}")
    n_aff = len({m for g in cleaned for m in g['members']})
    print(f"  clusters affected: {n_aff} of {len(catalogue)} ({100*n_aff/len(catalogue):.1f}%)")
    from collections import Counter
    sz = Counter(len(g['members']) for g in cleaned)
    print(f"  size distribution: {dict(sz)}")

    # Did we catch the known-missed pairs?
    known = [('c027','c738'), ('c744','c591'), ('c003','c679')]
    print(f"\nKnown-missed pair recovery:")
    for a, b in known:
        found = any(a in g['members'] and b in g['members'] for g in cleaned)
        print(f"  {a}+{b}: {'CAUGHT' if found else 'still missed'}")


if __name__ == "__main__":
    main()
