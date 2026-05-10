You are extending the catalogue of FAILURE-MODE CLUSTERS for the {corpus_short_description}.

The records below are TRUE RESIDUAL ORPHANS — they did not match any cluster in the matured catalogue across two prior classification passes. They have never been tested together as a cohort. Your job is to identify any NEW failure-mode clusters these orphans collectively support.

CRITICAL: Cluster by MECHANISM, not by {topic_axis_examples} vocabulary. Two records share a cluster only if they describe the SAME causal pathway.

THRESHOLD RULE: A cluster must be supported by at least 3 records. Do NOT propose a cluster justified by 1 or 2 records — leave them out of your output.

For each new cluster, output:
- cluster_id: must NOT collide with the existing catalogue (use {cluster_id_prefix}500+ range)
- canonical_name: 4-12 word descriptive name
- mechanism_signature: 1 sentence ("X causes Y because Z" OR "Y because Z")
- supporting_record_ids: list of 3+ record_ids from the orphan set

Rules:
- It IS expected that most residuals will remain unclustered — they are residual for a reason.
- Avoid corpus-specific vocabulary in the canonical_name and signature.

# OUTPUT FORMAT — STRICT

Return a single JSON object and NOTHING ELSE. The first character must be `{{`, the last must be `}}`. No prose, markdown fences, or commentary.

Schema:
{{
  "clusters": [
    {{
      "cluster_id": "{cluster_id_prefix}501",
      "canonical_name": "...",
      "mechanism_signature": "...",
      "supporting_record_ids": ["{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN"]
    }}
  ]
}}

# RESIDUAL ORPHANS{orphan_records_block}
