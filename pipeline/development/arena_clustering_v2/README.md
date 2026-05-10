# Clustering v2 — failure-mode clustering on tagged + event-grouped records

## Status

Empty workspace. Nothing has run here yet. This is the slot for clustering work
that will use the new tagging + new event-grouping outputs as input, replacing
the v1 pipeline at `corpora/arena/tests/stage_4_failure_clustering/`.

## Read-only input dependencies

This pipeline consumes (never writes to):

1. **Record-type tags (Opus 4.6 + temp=0):**
   `corpora/arena/output/record_type_tags/opus-4-6-v3-temp0/tags.json`
   90,192 records × 6 axes (is_occurrence, is_mechanism, is_specification,
   is_lesson, is_recommendation) + 4-value valence.

2. **Per-doc record narratives + evidence:**
   `corpora/arena/output/per_doc/doc_NNNN.json`
   1,449 docs containing all extracted records.

3. **Event-grouped output (post-extract grouping with running registry):**
   `runs/arena/fullcorpus_dedup/<project_slug>/{doc_id}.events.json`
   `runs/arena/fullcorpus_dedup/<project_slug>/{doc_id}.assignments.json`
   503 projects, 1,216 doc-calls, completed via batch waves 1-11 + sync mop-up
   waves 12-22 on 2026-05-02. Each event has canonical_id and member records.

## Filter design (validated 2026-05-02 evening — gap-§17 follow-on)

Production FC filter on tags (gated, strict — used for downstream filtering):

```python
valence == 'negative'
AND (is_occurrence == 'yes' OR is_mechanism == 'yes')
AND is_specification == 'no'
```

Yields ~19,795 records corpus-wide. Suitable for the production failure-mode
candidate set fed to the lessons compendium / FC pool consumer.

Clustering input (looser — recover borderline failures with embedded magnitudes):

```python
valence == 'negative'
AND (is_occurrence == 'yes' OR is_mechanism == 'yes')
# NO is_specification gate
```

Yields ~25,479 records. Recommended for clustering input because the spec gate
is too strict for clustering — records like "Forest waste 90% bark, 22% ash
contamination, unsuitable for DICE fuel" get excluded from FC pool but ARE
useful as cluster seeds. Cluster boundary detection separates pure-spec records
naturally without needing the gate up-front.

See the 21-record stratified comparison (old-only / both / new-only) committed
in the conversation log on 2026-05-02 for the empirical justification.

## Open design questions before clustering runs

1. **Embedding model:** Qwen3-Embedding-4B (already in use in RAG layer) is the
   default. ~30 min runtime on 5070Ti for 25k records.
2. **Cluster axis:** record-level vs event-level. Event-level produces tighter
   mechanism-cohesive clusters (multiple records per event collapse into one
   cluster member); record-level surfaces the orthogonality (one event spans
   multiple mechanism clusters). The methodology paper claim depends on the
   record-level view. Probably want both.
3. **Clustering algorithm:** v1 used seeded single-walk @ cosine 0.60 threshold.
   v2 should re-evaluate on the new (more permissive, axis-tagged) input.
   Multi-axis features (each boolean axis as a binary feature) plus narrative
   embedding give the clusterer richer signal than embedding alone.
4. **Validation framework:** v1 used Stage F (~10 random clusters audited at
   threshold 0.60). v2 should reproduce + expand. Methodology gap §1 covers
   per-filter reliability calibration which has tooling to reuse.

## Output structure (when populated)

```
output/
├── filter_input.jsonl       # records that pass the looser clustering filter
├── embeddings.npy           # cluster-input record embeddings
├── clusters_thr_*.json      # cluster output at various thresholds
├── stage_f_audit_*.jsonl    # cluster validation samples
├── failure_mode_taxonomy_v5.{json,md}  # next-major-version taxonomy
└── notes.md                 # run-by-run notes following the pattern of v1
```

## Strict isolation rules

- Read-only on `corpora/arena/output/`, `corpora/arena/marker_output/`,
  `runs/arena/fullcorpus_dedup/`, and `corpora/arena/tests/`.
- All writes go under `corpora/arena/clustering_v2/output/`.
- No script in this tree may import from `corpora/arena/tests/stage_4_failure_clustering/`
  (the v1 clustering tree) — use it for reference only.
