#!/usr/bin/env python3
"""Closure phase 2 (Option B): Qwen-driven merge-candidate group identification.

Replaces the embedding-cosine-threshold shortlister with a local Qwen2.5-7B-Instruct
run that reads chunks of clusters and proposes groups of clusters describing
the same mechanism. Qwen catches semantic-mechanism similarity that raw
embeddings miss (e.g., c027 ↔ c738 which embeddings rate at only 0.56 despite
describing the same mechanism from opposite perspectives).

Chunking strategy: embedding-guided regions, NOT random.

  1. Embed all 1,141 clusters with Qwen3-Embedding-4B (already done by step 01)
  2. K-means cluster the embeddings into ~25 regions of ~45 clusters each
  3. Each region contains clusters that are mostly similar by topic/vocabulary;
     within-region candidates are the most likely merge targets
  4. Run Qwen on each region: "identify groups of clusters describing the same
     mechanism"
  5. Aggregate proposed groups; output merge_groups.json

Cross-region candidates are missed by this design, but the embedding-region
pre-grouping ensures most merge candidates fall within a region anyway. A
follow-up cross-region pass can be added later.

Outputs:
  merge_groups.json — list of proposed merge groups
  region_assignments.json — cluster → region_id, for diagnostic / future use
"""
import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import torch

V2_OUT = Path(__file__).resolve().parents[2] / 'output'
CLOSURE_OUT = Path(__file__).resolve().parent.parent / 'output'
EMB_FILE = CLOSURE_OUT / 'cluster_embeddings.npy'
IDS_FILE = CLOSURE_OUT / 'cluster_ids.json'
CATALOGUE = V2_OUT / 'sweep' / 'convergence' / 'catalogue_after_convergence.json'
GROUPS_OUT = CLOSURE_OUT / 'merge_groups.json'
REGIONS_OUT = CLOSURE_OUT / 'region_assignments.json'
RAW_OUT = CLOSURE_OUT / 'qwen_raw_outputs.jsonl'

MODEL_NAME = 'Qwen/Qwen2.5-7B-Instruct'
MAX_NEW_TOKENS = 1500


PROMPT_TEMPLATE = """You are auditing a catalogue of failure-mode clusters. Below is a region of clusters from the catalogue (clusters in this region are topically related by embedding similarity).

Your task: identify any GROUPS of clusters that describe the SAME causal failure mechanism. Two clusters belong in the same group if their mechanism signatures describe the same causal pathway, even if they use different vocabulary or look at the mechanism from different perspectives. Different mechanisms that happen to share topic or technology vocabulary should NOT be grouped — only same causal pathway counts.

Most clusters in this region will NOT belong to any merge group. Only flag groups where you are confident the clusters describe the same mechanism. A group can be 2 clusters or more.

# CLUSTERS IN THIS REGION
{clusters_block}

# OUTPUT FORMAT
Return JSON only:
{{"merge_groups": [
  {{"members": ["c001", "c042"], "rationale": "<one sentence>"}},
  ...
]}}

If no merge groups exist in this region, return {{"merge_groups": []}}."""


def parse_response(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    body = m.group(1).strip() if m else text
    first = body.find('{')
    last = body.rfind('}')
    if first >= 0 and last > first:
        try: return json.loads(body[first:last+1])
        except: pass
    # Loose recovery: extract any [{"members": [...]}, ...] blocks
    groups = []
    for m in re.finditer(r'\{\s*"members"\s*:\s*(\[[^\]]+\])\s*(?:,\s*"rationale"\s*:\s*"([^"]+)")?', body):
        try:
            members = json.loads(m.group(1))
            groups.append({'members': members,
                           'rationale': m.group(2) or ''})
        except: pass
    return {'merge_groups': groups, '_recovered': True} if groups else None


def kmeans(embs, k, seed=0, n_iter=20):
    """Simple k-means on unit-normalised vectors (cosine distance ≈ Euclidean)."""
    rng = np.random.default_rng(seed)
    n = embs.shape[0]
    centroids = embs[rng.choice(n, k, replace=False)].copy()
    labels = np.zeros(n, dtype=np.int64)
    for it in range(n_iter):
        sims = embs @ centroids.T
        new_labels = sims.argmax(axis=1)
        if it > 0 and (new_labels == labels).all():
            break
        labels = new_labels
        for c in range(k):
            mask = labels == c
            if mask.sum() > 0:
                centroids[c] = embs[mask].mean(axis=0)
                centroids[c] /= np.linalg.norm(centroids[c])
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-regions', type=int, default=25,
                    help='Number of k-means regions to partition the catalogue into')
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    print("Loading inputs...", flush=True)
    embs = np.load(EMB_FILE)
    cluster_ids = json.load(open(IDS_FILE))
    catalogue = json.load(open(CATALOGUE))['clusters']
    cid_to_meta = {c['cluster_id']: c for c in catalogue}
    print(f"  embeddings: {embs.shape}", flush=True)
    print(f"  catalogue: {len(catalogue)}", flush=True)

    print(f"\nK-means partitioning into {args.n_regions} regions...", flush=True)
    labels = kmeans(embs, args.n_regions, seed=args.seed)
    region_sizes = [int((labels == c).sum()) for c in range(args.n_regions)]
    print(f"  region sizes: min={min(region_sizes)} max={max(region_sizes)} "
          f"median={int(np.median(region_sizes))}", flush=True)

    region_assignments = {cluster_ids[i]: int(labels[i]) for i in range(len(cluster_ids))}
    REGIONS_OUT.write_text(json.dumps(region_assignments, indent=2))

    # Load model
    print(f"\nLoading {MODEL_NAME} in 4-bit on GPU...", flush=True)
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                              bnb_4bit_quant_type='nf4')
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map='auto',
        torch_dtype=torch.bfloat16,
    )
    model.eval()
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print(f"  loaded; VRAM {torch.cuda.memory_allocated()/1e9:.1f} GB", flush=True)

    raw_f = open(RAW_OUT, 'w')
    started = time.time()
    all_groups = []
    cluster_id_set = set(cluster_ids)

    for region_id in range(args.n_regions):
        region_cluster_ids = [cluster_ids[i] for i in range(len(cluster_ids))
                              if labels[i] == region_id]
        if len(region_cluster_ids) < 2:
            continue
        # Build clusters block
        block_lines = []
        for cid in region_cluster_ids:
            c = cid_to_meta[cid]
            block_lines.append(f"\n[{cid}] {c['canonical_name']}")
            block_lines.append(f"  mechanism: {c.get('mechanism_signature','')}")
        clusters_block = ''.join(block_lines)
        prompt = PROMPT_TEMPLATE.format(clusters_block=clusters_block)

        chat_prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(chat_prompt, return_tensors='pt', truncation=False).to('cuda')
        n_input = inputs['input_ids'].shape[1]
        t0 = time.time()
        with torch.inference_mode():
            outputs = model.generate(
                **inputs, max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False, temperature=None, top_p=None,
                pad_token_id=tokenizer.eos_token_id,
            )
        gen_only = outputs[0, n_input:]
        text = tokenizer.decode(gen_only, skip_special_tokens=True)
        wall = time.time() - t0

        parsed = parse_response(text)
        groups = (parsed or {}).get('merge_groups') or []
        # Filter: only keep groups whose members are valid cluster_ids in this region
        clean_groups = []
        for g in groups:
            members = [m for m in (g.get('members') or [])
                       if m in cluster_id_set and m in region_cluster_ids]
            if len(members) >= 2:
                clean_groups.append({
                    'members': sorted(set(members)),
                    'rationale': g.get('rationale', ''),
                    'region_id': region_id,
                })
        all_groups.extend(clean_groups)

        raw_f.write(json.dumps({
            'region_id': region_id, 'n_clusters': len(region_cluster_ids),
            'n_groups': len(clean_groups), 'input_tokens': int(n_input),
            'output_text_chars': len(text), 'wall_seconds': round(wall, 1),
        }) + '\n')
        raw_f.flush()
        print(f"  region {region_id+1}/{args.n_regions}: {len(region_cluster_ids)} clusters → "
              f"{len(clean_groups)} merge groups  ({wall:.0f}s, "
              f"{n_input}in/{len(text)}out chars)", flush=True)

    raw_f.close()

    # Deduplicate groups by member-set
    seen = {}
    for g in all_groups:
        key = tuple(sorted(g['members']))
        if key not in seen:
            seen[key] = g
        else:
            # If duplicate, prefer one with rationale
            if not seen[key]['rationale'] and g['rationale']:
                seen[key] = g
    final_groups = list(seen.values())
    final_groups.sort(key=lambda g: -len(g['members']))

    GROUPS_OUT.write_text(json.dumps(final_groups, indent=2, ensure_ascii=False))
    print(f"\n=== DONE ===")
    print(f"  Regions processed: {args.n_regions}")
    print(f"  Total proposed groups: {len(all_groups)}")
    print(f"  After dedup: {len(final_groups)}")
    print(f"  Wall: {(time.time()-started)/60:.1f} min")

    # Group-size distribution
    from collections import Counter
    sizes = Counter(len(g['members']) for g in final_groups)
    print(f"\nGroup-size distribution:")
    for s in sorted(sizes):
        print(f"  size {s}: {sizes[s]} groups")


if __name__ == "__main__":
    main()
