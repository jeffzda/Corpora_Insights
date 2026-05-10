# Parent-category audit and theme grouping

## Context

You are auditing a candidate parent-category set proposed for a taxonomy of failure-mode clusters extracted from {corpus_short_description}. Each cluster represents a recurring failure pattern asserted by multiple records. You will see:

1. Each cluster's id, canonical name, and mechanism signature.
2. A candidate parent-category set with names, descriptions, and mechanism criteria.
3. The per-cluster assignment of clusters to parents.

Audit the candidate parent set independently of how it was generated, then propose a smaller set of themes that groups the parents.

## Task

### Part A — audit the candidate parents

For each candidate parent, judge:
- **Mechanism coherence**: does the parent describe a single mechanism class, or does its definition use "or" / "and" to bundle structurally distinct mechanisms that should be split?
- **Distinctness from neighbours**: is this parent meaningfully different in mechanism from every other parent, or could it be merged?
- **Population fit**: do the actual cluster assignments to this parent reflect a real corpus pattern, or is the parent over-claiming (drawing in clusters that don't fit) or under-claiming (genuine pattern with too few clusters)?
- **Missing mechanisms**: are there mechanism classes you would expect to see in this corpus that no candidate parent represents?

Return a per-parent assessment plus a list of any mechanism classes you think the candidate set is missing.

### Part B — propose themes

Group the candidate parents into a smaller number of higher-level themes, where each theme captures a structural family of mechanism classes (e.g. "informational failures" might contain several specific data-level parents).

Constraints:
- Themes should be derived from **mechanism similarity**, not from the candidate parent names. Two candidate parents with different names that describe the same structural mechanism family should land in the same theme.
- Some candidate parents may not fit any theme cleanly; return those under `unthemed_parents` rather than forcing a fit.
- The number of themes is emergent. There is no preset.
- **Every parent must appear exactly once** — either in a theme's `parent_ids` list, or in `unthemed_parents`.

## Output

Strict JSON, no extra text:

```json
{{
  "audit": {{
    "per_parent": [
      {{
        "parent_id": "p01",
        "mechanism_coherence": "tight | mixed | bundled",
        "distinctness": "distinct | overlaps_with_<pNN>",
        "population_fit": "right | over-claimed | under-claimed",
        "verdict": "keep | split | merge_with_<pNN> | drop",
        "rationale": "<5-15 words>"
      }}
    ],
    "missing_mechanism_classes": [
      {{"name": "<short name>", "description": "<one sentence>", "evidence_clusters": ["<{cluster_id_prefix}NNN>"]}}
    ]
  }},
  "themes": [
    {{
      "theme_id": "t01",
      "name": "<short noun phrase>",
      "description": "<2-3 sentences>",
      "mechanism_family": "<one sentence: what unifies this theme>",
      "parent_ids": ["<pNN>"]
    }}
  ],
  "unthemed_parents": [
    {{"parent_id": "<pNN>", "reason": "<why no theme fits>"}}
  ],
  "notes": "<optional observations>"
}}
```

## Input

### Candidate parent set

{parent_block}

### Per-cluster assignments

{assignment_block}

### Failure-mode clusters

The following clusters are listed in arbitrary order. Each entry is:

  cluster_id | canonical_name | mechanism_signature | n_records

{cluster_block}
