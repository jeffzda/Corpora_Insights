You are classifying {corpus_short_description} records against a catalogue of failure-mode clusters.

For each record, your goal is to assign it to one of the listed clusters if one of them reasonably describes the causal failure mechanism the record discusses. If no existing cluster fits, return cluster_id="orphan".

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
