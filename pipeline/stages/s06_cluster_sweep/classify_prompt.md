You are classifying {corpus_short_description} records against an existing catalogue of failure-mode clusters.

For each record, decide: does its causal failure mechanism match one of the catalogue entries? If yes, return that cluster_id. If no clear match exists in the catalogue, return cluster_id="orphan".

CRITICAL: Do NOT force-fit. It is better to mark a record as 'orphan' than to assign it to a cluster that doesn't actually capture its mechanism. Orphans will be processed by a separate clustering pass that may create new clusters for them. Force-fitting damages the catalogue.

Match on MECHANISM, not on:
- {topic_axis_examples}
- Surface text similarity
- Topic similarity (just because both are about a similar topic doesn't mean same mechanism)

Two records share a cluster only if they describe the SAME causal pathway.

# CATALOGUE OF FAILURE-MODE CLUSTERS{catalogue_block}

# RECORDS TO CLASSIFY{records_block}

# OUTPUT FORMAT

Return JSON only:
{{
  "assignments": [
    {{"record_id": "{record_id_prefix}-XXXX-NNNN", "cluster_id": "{cluster_id_prefix}042"}},
    {{"record_id": "{record_id_prefix}-XXXX-NNNN", "cluster_id": "orphan"}}
  ]
}}

One assignment per input record, in input order. cluster_id must be either an existing catalogue id (e.g. "{cluster_id_prefix}042") or the literal string "orphan".
