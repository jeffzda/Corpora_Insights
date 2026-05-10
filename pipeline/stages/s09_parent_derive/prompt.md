# Parent-category derivation from mechanism-level failure clusters

## Context

You are proposing parent categories for a taxonomy of failure-mode clusters extracted from {corpus_short_description}. Each cluster represents a recurring failure pattern — multiple records across different sources independently asserting the same underlying causal mechanism.

You will not see the records themselves; you will see only each cluster's **id**, **canonical name**, **mechanism signature** (one sentence describing the causal pathway), and **n_records** (how many records the cluster aggregates).

## Audience

The reader is {audience_persona} {audience_use_case}. They use the parent set as a **navigable diagnostic vocabulary**: scanning the parent names and definitions to surface every important failure mechanism that could plausibly arise in their context, and grounding their assessment of forward-looking risk in the corpus evidence beneath each mechanism. The taxonomy needs to:

- **Cover the mechanism space comprehensively** so a reader scanning the list does not encounter a real risk with no corresponding parent.
- **Remain navigable at a glance** — too many parents and the reader can't scan them efficiently; too few and the taxonomy collapses genuinely-distinct mechanisms together.
- **Support defensible claims about future risk** — each parent must name a mechanism the reader can cite as a structurally real failure pattern the corpus has shown recurring.

## Task

Read all the clusters listed below. Propose parent categories that group them by **mechanism class** — the kind of thing that goes wrong, not the topic or domain it goes wrong in.

## Constraints

1. **Emergent count.** Return as many parents as the clusters genuinely require, no more and no fewer. There is no preset number.

2. **Mechanism class, not topic.** Two clusters from different domains that fail through the same mechanism should land in the same parent. Two clusters from the same domain that fail through different mechanisms should land in different parents. Do not group by {topic_axis_examples}.

3. **Tightness over breadth.** Prefer narrower, well-defined parents that genuinely fit their members over broad parents that absorb anything loosely related. If a parent's description has to use "or" to span structurally different mechanisms, split it.

4. **Honest unfit reporting.** If some clusters do not cleanly fit any proposed parent, return them under an `unassigned` bucket with reasons. Forcing membership reduces taxonomy quality.

5. **Mid-tail attention.** The cluster list contains both larger (50+ record) and smaller (3-5 record) clusters. Do not let larger clusters dominate the parent design — smaller clusters often instantiate tighter, more specific mechanisms that matter for the parent definition.

6. **Independence of axes.** Make parents distinguishable on mechanism class alone. If two parents differ only in which {topic_axis_examples} their members come from, they are likely the same mechanism class differently labelled.

## Output

Strict JSON, no extra text:

```json
{{
  "parents": [
    {{
      "parent_id": "p01",
      "name": "<short noun phrase, 3-7 words>",
      "description": "<2-4 sentences naming the mechanism class and the criterion for membership>",
      "mechanism_criterion": "<one sentence: what must be true of a cluster's mechanism for it to belong here>",
      "exemplar_cluster_ids": ["<ids of 3-5 clusters that most cleanly instantiate this parent>"],
      "estimated_population": "<rough fraction of total clusters expected to fit, e.g. '5-8%'>"
    }}
  ],
  "unassigned": [
    {{"cluster_id": "<{cluster_id_prefix}NNN>", "reason": "<why no parent fits>"}}
  ],
  "notes": "<optional: anything you noticed about the cluster distribution worth flagging>"
}}
```

Number parents `p01`, `p02`, ... in the order you list them. Order them thematically so adjacent parents are mechanism-related families.

## Input — {n_clusters} clusters

Each entry: `cluster_id | canonical_name | mechanism_signature | n_records`

{cluster_block}
