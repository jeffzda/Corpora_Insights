You will read one extracted insight record and three candidate failure-mode cluster descriptions. Your job is to determine which cluster (if any) genuinely describes this record's underlying failure mode.

For each candidate cluster you have:
- A cluster name (short noun phrase)
- A cluster description (2-3 sentences explaining the failure-mode pattern)
- A mechanism signature (3-7 words capturing the *how*)

Your task: pick the cluster whose **failure-mode pattern** matches this record's mechanism. Not just topical similarity — the actual underlying failure mode must align.

## Decision rule

- If the record clearly fits one cluster's failure-mode pattern (its mechanism is an instance of that pattern), assign to that cluster.
- If the record could plausibly fit two clusters, pick the better fit. Don't split.
- If **no cluster clearly fits the record's failure mode** (the record describes a different kind of failure), return `eject`. The record will become a singleton — that's the right outcome when no cluster pattern actually describes it.

Be willing to eject. The clusters were formed by embedding similarity which can group records with related vocabulary but different underlying mechanisms. Your job is to make the semantic call. A misfit ejected to singleton is the right outcome.

## Output

Strict JSON, no extra text:

```json
{"verdict": "A|B|C|eject", "rationale": "<5-15 words explaining the choice>"}
```

## Record

mechanism_phrase: "{mechanism_phrase}"
connective: "{connective}"
narrative: "{narrative}"

## Candidate clusters

### A: {cluster_a_name}
mechanism signature: {cluster_a_signature}
description: {cluster_a_description}

### B: {cluster_b_name}
mechanism signature: {cluster_b_signature}
description: {cluster_b_description}

### C: {cluster_c_name}
mechanism signature: {cluster_c_signature}
description: {cluster_c_description}
