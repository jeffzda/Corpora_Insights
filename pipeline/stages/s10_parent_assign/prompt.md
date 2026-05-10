# Cluster-to-parent assignment

## Context

You previously proposed (or are now being shown) a parent-category set for a taxonomy of failure-mode clusters. Your task now is to assign **every cluster** in the corpus to exactly one parent (or to `none` if no parent fits cleanly).

## Task

For each cluster:
1. Pick the parent whose **mechanism criterion** the cluster best instantiates, OR
2. Return `parent_id: "none"` if no parent's mechanism criterion fits.
3. Indicate confidence (`low` / `medium` / `high`) based on how cleanly the cluster's mechanism matches the chosen parent's criterion.
4. Give a one-line rationale (≤ 25 words) — what about the cluster's mechanism makes this the right parent (or why none fits).

## Constraints

- **Be willing to call low-confidence or `none`.** The goal is correct placement, not maximum coverage. Stretching a cluster into a parent that doesn't quite fit corrupts the taxonomy.
- **Mechanism, not topic.** The parent's `mechanism_criterion` is the test. A cluster about a different domain that fails through the same mechanism still belongs in the parent.
- **Use the exact parent_id** from the parent set below (e.g. `p07`). Do not invent new ids.
- **Output every cluster** — your output line count must equal the input cluster count. Do not silently skip clusters.

## Output

Strict JSON, no extra text. The top-level field is `assignments`, a list with one entry per cluster (in the same order as the input):

```json
{{
  "assignments": [
    {{"cluster_id": "<cNNN>", "parent_id": "<pNN or 'none'>", "confidence": "low|medium|high", "rationale": "<≤ 25 words>"}}
  ]
}}
```

## Input

### Parent set

{parent_block}

### Clusters to assign

The following clusters are listed in arbitrary order. Each entry is:

  cluster_id | canonical_name | mechanism_signature | n_records

{cluster_block}
