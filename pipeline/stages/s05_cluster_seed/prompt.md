You are building an initial catalogue of FAILURE-MODE CLUSTERS for the {corpus_short_description}.

Each input record is a piece of extracted insight from a source document. The records below have all been pre-tagged as failure-mode-relevant (negative valence + occurrence-or-mechanism). Read all records and infer the set of failure-mode clusters that exist in this sample.

CRITICAL: Cluster by MECHANISM (the 'how' or 'why' something fails), NOT by:
- {topic_axis_examples}
- Surface text similarity
- Domain vocabulary

Two records share a cluster if they describe the SAME causal pathway, even if the {topic_axis_examples} and surface vocabulary differ.

YOUR JOB: produce a CATALOGUE of failure-mode cluster LABELS. Each cluster must be supported by at least 3 records sharing the same causal mechanism. Records that don't have at least 2 other records sharing their mechanism should be returned as singletons — listed by record_id but NOT promoted to a cluster definition.

You are NOT assigning records to clusters in this step beyond identifying which records justified each cluster (no full member lists), and you are NOT writing descriptions yet (those come later, after all assignment is done across the full corpus).

For each cluster you identify, output:
- cluster_id: {cluster_id_prefix}001, {cluster_id_prefix}002, ... (zero-padded 3 digits)
- canonical_name: 4-12 word descriptive name (locks forever; do not change later)
- mechanism_signature: 1 sentence of the abstracted causal logic. Either form is fine:
  - "X causes Y because Z" (when there is a clear triggering condition)
  - "Y because Z" (when the cause is the property/condition itself, with no separate trigger)
- supporting_record_ids: list of 3+ record_ids from the input that share this mechanism (just the ids, no descriptions). Used to verify the ≥3 threshold and to seed downstream classification.

Then list every record that did NOT get grouped into a cluster as a singleton, by record_id.

CRITICAL THRESHOLD RULE:
- Do NOT propose a cluster supported by fewer than 3 records. A pattern observed in 1 or 2 records is a hypothesis, not a cluster — leave those records as singletons.
- Singletons may later become clusters when subsequent batches contribute matching records.

Rules:
- Aim for clusters that are tightly mechanism-bound, not breadth-bound.
- Prefer specificity over breadth. Vague labels lose information; the right resolution is mechanism-specific.
- DO NOT cluster by {topic_axis_examples} — the test is mechanism, not topic.
- Avoid corpus-specific vocabulary in the canonical_name and signature. The label should generalise.
- It is fine — preferred, even — to leave many records as singletons. The catalogue is only for patterns with ≥3 evidence.

Output valid JSON, schema:
{{
  "clusters": [
    {{
      "cluster_id": "{cluster_id_prefix}001",
      "canonical_name": "...",
      "mechanism_signature": "...",
      "supporting_record_ids": ["{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN"]
    }}
  ],
  "singletons": ["{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN"]
}}

# Records to cluster
