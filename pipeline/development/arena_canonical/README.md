# Canonical pipeline — current production path

The canonical pipeline reads the shared v1 grave extraction (`shared/extraction/output/per_doc/`, ~90,000 records) and produces a queryable corpus-wide measurement instrument. This README is the entry point for running the pipeline and finding its outputs.

For why this pipeline exists alongside the legacy one, see `corpora/arena/PIPELINES.md`. For the testing narrative behind each canonical decision, see `narrative/README.md`.

## Layout

```
canonical/
├── README.md                          this file
├── PIPELINE.md                        stage-by-stage diagram with model, prompt, IO, cost
├── code/                              symlinks to live pipeline code
│   ├── group_events.py                → ../../../../pipeline/group_events.py
│   ├── group_events_corpus.py         → ../../../../pipeline/group_events_corpus.py
│   ├── clustering_v2/                 → ../../clustering_v2/code/  (scripts 01-16)
│   └── closure/                       → ../../clustering_v2/closure/code/  (scripts 01-11)
├── prompts/
│   ├── group_events.md                → ../../../../pipeline/prompts/group_events.md
│   └── label_record_types_v3.md       (the v3 prompt, moved here from inside a test-run folder)
├── output/                            symlinks to live artefacts
│   ├── record_type_tags/              → ../../output/record_type_tags/
│   ├── grouping/                      per-doc event-grouping outputs (centralised)
│   ├── clustering/                    → ../../clustering_v2/output/sweep/convergence/
│   └── closure/                       → ../../clustering_v2/output/  (full_corpus_events, etc.)
└── narrative/
    ├── README.md                      reading order for canonical decisions
    ├── runs_synthesis.md              the 8-run synthesis
    ├── runs/                          all 8 dated test-run snapshots
    ├── methodology_gaps.md            (copy — same content as in legacy/)
    ├── methodology_notes.md           (copy)
    ├── clustering_v2_notes.md         v2 sweep iteration notes
    ├── clustering_v2_inspection_notes.md
    ├── seed_doc_heuristic.md          the seed-doc-first decision
    ├── seed_doc_heuristic.py          (the picker script)
    ├── check_v2_coverage.py           record-preservation check used during the runs
    └── check_footnote_handling.py     diagnostic from a related concern
```

## Running the canonical pipeline

The canonical pipeline reads the shared extraction and runs four stages:

1. **Per-doc event grouping** — group records into events via Sonnet 4.6, per-doc with seed-doc-first chronological ordering and a running event registry.
2. **6-axis record-type labelling** — tag every record with `is_occurrence`, `is_mechanism`, `is_specification`, `is_lesson`, `is_recommendation`, `valence` via Opus 4.6 batched.
3. **v2 clustering** — embed records, single-walk cluster, sweep through orphan reclassification, converge to the 1,141-cluster catalogue.
4. **Closure** — derive cluster co-occurrence via shared events, assign global event_ids, build the corpus-wide event-key map.

```bash
# Stage 1 — event grouping (input: shared/extraction/output/per_doc/)
python -m pipeline.group_events_corpus --domain arena
# (writes to canonical/output/grouping/)

# Stage 2 — 6-axis Opus 4.6 record-type labelling
python -m pipeline.label_record_types --domain arena --batch submit --in canonical/output/per_doc/
python -m pipeline.label_record_types --domain arena --batch collect

# Stage 3 — clustering (run scripts in numbered order)
cd corpora/arena/clustering_v2/code
python 01_build_clustering_input.py
python 02_fetch_embeddings.py
python 03_cluster.py
# ... continue through script 16 (convergence)

# Stage 4 — closure
cd ../closure/code
python 01_identify_merge_candidates.py
# ... continue through script 11 (rebuild corpus event keys)
```

Per-stage details (model, prompt, IO, cost) in `PIPELINE.md`.

## Outputs

After a full run, the live artefacts live at:

- `corpora/arena/output/per_doc/doc_NNNN.json` (90,192 records, shared with legacy)
- `corpora/arena/output/record_type_tags/opus-4-6-v3-temp0/tags.json` (90,192 × 6 axes)
- `corpora/arena/canonical/output/grouping/*.events.json` (per-doc event groupings)
- `corpora/arena/clustering_v2/output/sweep/convergence/catalogue_after_convergence.json` (1,141 clusters)
- `corpora/arena/clustering_v2/output/sweep/convergence/convergence_assignments.jsonl`
- `corpora/arena/clustering_v2/output/full_corpus_events.jsonl` (corpus-wide event-keyed records)
- `corpora/arena/clustering_v2/output/full_event_key_map.jsonl`
- `corpora/arena/clustering_v2/output/cluster_cooccurrence.json`

The `canonical/output/` folder is a symlinked view of the same artefacts.

## What the canonical pipeline did *not* do

Important caveats for the methodology paper, repeated from `PIPELINES.md`:

1. **Extraction was *not* re-run.** The §15 retraction in `methodology_gaps.md` validated the existing 90,192-record extraction. Only the 17 docs >150k tokens warrant chunking; that re-extraction has not been done.
2. **At-extraction-time event-identity was *not* deployed.** §13 is implemented as a post-extraction grouping pass (`pipeline/group_events.py`), not as an extraction-prompt change. The runs/README.md synthesis showed decoupled grouping outperforms extraction-time grouping because grouping instructions leak into extraction selectivity.

## Next steps (open at the time of reorg)

From `runs_synthesis.md`'s production handoff checklist, items still open:

1. Coverage check on full per-doc grouping output — `check_v2_coverage.py` confirms record preservation.
2. Event-coherence check — sample N events, ask Haiku "do these records describe one occurrence?"
3. Cross-cluster span analysis — for each per-doc grouping event, compute how many clusters its records span.
4. Full-corpus grouping run (currently runs are at REVS scale) and its cost confirmation against the projection.

See `narrative/README.md` for which test-run snapshots ground each open item.
