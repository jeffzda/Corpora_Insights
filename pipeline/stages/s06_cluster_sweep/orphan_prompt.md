You are extending the catalogue of FAILURE-MODE CLUSTERS for the {corpus_short_description}.

The records below were rejected as 'orphans' by the classifier — they did not match any existing catalogue cluster's mechanism. Your job is to identify any NEW failure-mode clusters these orphans collectively support.

CRITICAL: Cluster by MECHANISM, not by {topic_axis_examples} vocabulary. Two records share a cluster only if they describe the SAME causal pathway, even with different surface vocabulary.

THRESHOLD RULE: A cluster must be supported by at least 3 records. Do NOT propose a cluster justified by 1 or 2 records — simply leave those records out of your output. Records you don't list will be treated as singletons by post-processing.

For each new cluster you identify, output:
- cluster_id: must NOT collide with existing catalogue ids; use a high range starting from {cluster_id_prefix}500
- canonical_name: 4-12 word descriptive name (locks forever)
- mechanism_signature: 1 sentence ("X causes Y because Z" OR "Y because Z")
- supporting_record_ids: list of 3+ record_ids from the orphan set that share this mechanism

DO NOT emit a singletons list. Records you do not place in any cluster are automatically treated as singletons by post-processing.

Rules:
- It IS expected that many orphans will remain unclustered — that is the correct behaviour for genuinely unique mechanisms or patterns with only 1-2 examples in this batch.
- Avoid corpus-specific vocabulary in the canonical_name and signature.
- The catalogue is only for patterns with ≥3 evidence.

# OUTPUT FORMAT — STRICT

Return a single JSON object and NOTHING ELSE. No prose, markdown fences, working notes, or per-record commentary. The very first character must be `{{` and the last character must be `}}`.

Schema:
{{
  "clusters": [
    {{
      "cluster_id": "{cluster_id_prefix}501",
      "canonical_name": "4-12 word descriptive name",
      "mechanism_signature": "1 sentence",
      "supporting_record_ids": ["{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN", "{record_id_prefix}-XXXX-NNNN"]
    }}
  ]
}}

No record_id may appear in more than one cluster. Cluster supporting_record_ids must contain at least 3 ids drawn from the input orphan set.

# ORPHAN RECORDS{orphan_records_block}
