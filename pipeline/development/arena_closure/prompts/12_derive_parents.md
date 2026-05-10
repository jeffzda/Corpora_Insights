# Parent-category derivation from v2 mechanism-level failure clusters

## Context

You are proposing parent categories for a taxonomy of failure-mode clusters extracted from a corpus of government-funded clean-energy project documents (the ARENA Knowledge Bank, ~1,440 documents). Each cluster represents a recurring failure pattern — multiple project authors, across different projects and technologies, independently asserted the same underlying causal mechanism in their own words.

You will not see the records themselves; you will see only each cluster's **id**, **canonical name**, **mechanism signature** (one sentence describing the causal pathway), and **n_records** (how many records the cluster aggregates).

## Task

Read all the clusters listed below. Propose parent categories that group them by **mechanism class** — the kind of thing that goes wrong, not the topic or technology domain it goes wrong in.

Examples of mechanism class:
- *informational* (data absent, knowledge missing, signal not transmitted)
- *physical-technical* (material limit, thermal limit, spatial constraint)
- *control-technical* (cadence mismatch, protocol incompatibility, measurement gap)
- *economic* (cost exceeds threshold, price signal absent, value not captured)

These are illustrative, not prescriptive. Derive whatever parent set the data actually warrants.

## Constraints

1. **Emergent count.** Return as many parents as the clusters genuinely require, no more and no fewer. There is no preset number. If the corpus warrants 30 parents, return 30; if 90, return 90.

2. **Mechanism class, not topic.** Two clusters about different technologies that fail through the same mechanism should land in the same parent. Two clusters about the same technology that fail through different mechanisms should land in different parents. Do not group by technology domain (solar / battery / hydrogen / etc.) — that information is in project metadata elsewhere.

3. **Tightness over breadth.** Prefer narrower, well-defined parents that genuinely fit their members over broad parents that absorb anything loosely related. If a parent's description has to use "or" to span structurally different mechanisms, split it.

4. **Honest unfit reporting.** If some clusters do not cleanly fit any proposed parent, do not stretch a parent to absorb them. Return them under an `unassigned` bucket and explain why each does not fit. Forcing membership reduces taxonomy quality.

5. **Mid-tail attention.** The cluster list contains both larger (10+ record) and smaller (3-5 record) clusters. Do not let larger clusters dominate the parent design — smaller clusters often instantiate tighter, more specific mechanisms that matter for the parent definition.

6. **Independence of axes.** Try to make parents distinguishable on mechanism class alone. If two parents differ only in which industry or life-cycle stage their members come from, they are likely the same mechanism class differently labelled.

## Output

Strict JSON, no extra text:

```json
{
  "parents": [
    {
      "parent_id": "p01",
      "name": "<short noun phrase, 3-7 words>",
      "description": "<2-4 sentences naming the mechanism class and the criterion for membership>",
      "mechanism_criterion": "<one sentence: what must be true of a cluster's mechanism for it to belong here>",
      "exemplar_cluster_ids": ["<ids of 3-5 clusters that most cleanly instantiate this parent>"],
      "estimated_population": "<rough fraction of total clusters expected to fit, e.g. '5-8%'>"
    }
  ],
  "unassigned": [
    {"cluster_id": "<cNNN>", "reason": "<why no parent fits>"}
  ],
  "notes": "<optional: anything you noticed about the cluster distribution worth flagging>"
}
```

Number parents `p01`, `p02`, ... in the order you list them.

## Input

The following clusters are listed in arbitrary order. Each entry is:

  cluster_id | canonical_name | mechanism_signature | n_records

{cluster_block}
