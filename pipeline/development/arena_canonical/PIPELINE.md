# Canonical pipeline — stage-by-stage diagram

Four stages after the shared v1 grave extraction. Each stage's row gives the model, the prompt path, the input directory, the output directory, and the rough cost.

## Stage 1 — per-doc event grouping

| | |
|---|---|
| **Code** | `pipeline/group_events.py`, orchestrated by `pipeline/group_events_corpus.py` |
| **Prompt** | `pipeline/prompts/group_events.md` (symlinked at `canonical/prompts/group_events.md`) |
| **Model** | Sonnet 4.6 (sync or Batches API) |
| **Input** | `corpora/arena/output/per_doc/doc_NNNN.json` (the shared extraction) |
| **Output** | `corpora/arena/canonical/output/grouping/<project>/doc_NNNN.events.json` |
| **Cost** | ~$0.56 per project on the REVS 3-doc test → ~$200-300 corpus-wide projection |
| **Decision** | Per-doc with seed-doc-first chronological ordering and running event registry. Documented in `narrative/runs_synthesis.md` table row 7 (winning approach) |

What it does: takes already-extracted records, groups them into events. One occurrence may span many records (cause, consequence, lesson, mitigation, design decision are aspects of one occurrence). The grouping pass runs per project, sorted by `publish_date` ascending, with the running event registry passed forward as docs are processed. Each call returns a `doc_NNNN.events.json` mapping each record to an `event_id`.

The `--batch-size 200` flag puts each doc into one Sonnet call (most ARENA docs have <200 records). The chronological accumulation framing materially tightens consolidation: per-doc with the running registry produces 47 events with 26% cross-doc rate vs one-shot's 63 events / 17% cross-doc on the REVS 3-doc test.

## Stage 2 — 6-axis record-type labelling

| | |
|---|---|
| **Code** | `pipeline/label_record_types.py` (productionised wrapper; pilot scripts at `narrative/runs/2026-05-02-record-type-pilot/code/run_pilot.py` and `submit_corpus_opus.py`) |
| **Prompt** | `corpora/arena/canonical/prompts/label_record_types_v3.md` |
| **Model** | **Opus 4.6** + temp=0, batched |
| **Input** | `corpora/arena/output/per_doc/doc_NNNN.json` (each record's `narrative` + `evidence`) |
| **Output** | `corpora/arena/output/record_type_tags/opus-4-6-v3-temp0/tags.json` |
| **Cost** | ~$162 batch for the 90,192-record corpus (Opus 4.6 + 1h prompt cache) |
| **Decision** | Opus 4.6 over Sonnet 4.6 because Sonnet under-tags `is_mechanism` by ~10pp at scale (~8,000 missed mechanisms corpus-wide, ground-truthed via 44-record hand-adjudication). Documented in `methodology_lessons.md` §8 and `methodology_gaps.md` §17 |

Six axes per record:

```yaml
- id: ARENA-DLV-XXXX-NNNN
  is_occurrence: yes | no
  is_mechanism: yes | no
  is_specification: yes | no
  is_lesson: yes | no
  is_recommendation: yes | no
  valence: positive | neutral | negative
```

These six axes subsume the legacy pipeline's separate stage 2 (causal recovery) + stage A (valence + mechanism) + stage 6 (realisation) calls. The earlier `pipeline/label_axes.py` (9-axis bundled) and `pipeline/event_type.py` (4-class realised/design/risk/contextual) are both **superseded** and live under `legacy/code/pipeline/` for cold-start reference.

## Stage 3 — v2 clustering

| | |
|---|---|
| **Code** | `corpora/arena/clustering_v2/code/01_*.py` through `16_*.py` |
| **Prompts** | inside `corpora/arena/clustering_v2/code/` (per-script) |
| **Model** | Sonnet 4.6 (primary), Haiku 4.5 + Opus 4.7 in A/B sweeps |
| **Input** | record_type_tags + per_doc records, filtered by `valence=negative AND (is_occurrence OR is_mechanism)` (~25,479 records) |
| **Output** | `corpora/arena/clustering_v2/output/sweep/convergence/catalogue_after_convergence.json` (1,141 clusters), `convergence_assignments.jsonl` |
| **Cost** | ~$2.73 sync (729 s wall) for the convergence run |
| **Decision** | Single-walk seeded clustering + iterative orphan reclassification + final residual sweep. Threshold ≥3 records absorbs upstream-filter false positives into singletons (per `methodology_lessons.md` §9). Cluster signatures are immutable mid-sweep (procurement-probity framing — `methodology_lessons.md` §10) |

Pipeline overview (the numbered scripts under `clustering_v2/code/`):

| Script | What it does |
|---|---|
| 01 | Build clustering input filter (FC candidates) |
| 02 | Fetch embeddings (all-mpnet-base-v2, 384-d) |
| 03 | Cluster at thresholds 50–65 (cosine) |
| 04 | Inspect clusters (sanity check) |
| 05 | Seed-cluster run (Sonnet groups top representative sample) |
| 06 | Classify and cluster orphans |
| 07–08 | Sweep remaining singletons (third-pass) |
| 09–10 | A/B tests (Haiku vs Sonnet, attention mechanism) |
| 11–12 | Neutral-prompt test variants |
| 13–16 | Convergence iteration (reclassify pending, residual orphans, final singletons) |

The catalogue at `sweep/convergence/catalogue_after_convergence.json` (1,141 clusters, 1,665 final singletons) is the canonical mechanism taxonomy.

## Stage 4 — closure

| | |
|---|---|
| **Code** | `corpora/arena/clustering_v2/closure/code/01_*.py` through `11_*.py` |
| **Model** | Mix — Qwen2.5-7B local (script 02), Opus 4.7 (scripts 03-06), Sonnet for syntheses |
| **Input** | `catalogue_after_convergence.json` + corresponding embeddings |
| **Output** | `corpora/arena/clustering_v2/output/`: `full_corpus_events.jsonl`, `full_event_key_map.jsonl`, `cluster_cooccurrence.json`, `event_key_map.jsonl` |
| **Cost** | ~$30-50 across the 11 scripts |

Closure does the post-convergence integration work:

| Script | What it does |
|---|---|
| 01 | Identify merge-candidate pairs via embedding similarity |
| 02 | Local Qwen2.5-7B merge-pair adjudication |
| 03 | Opus 4.7 one-shot merge-group finder over full catalogue |
| 04 | Opus groupfinder with greedy NN catalogue ordering |
| 05 | Opus merge restricted to battery-dominated subset |
| 06 | Extract general (non-renewable-specific) mechanisms |
| 07 | Per-cluster synthesis report generator |
| 08 | Cluster co-occurrence via shared events |
| 09 | Network visualisation of cluster co-occurrence |
| 10 | Rebuild event_ids with global uniqueness |
| 11 | Rebuild corpus-wide event keys (~90k records) |

The closure outputs are the corpus-wide measurement instrument's final form: every record has an `event_id`, every cluster has a synthesis report, cluster-cluster co-occurrence is computable, and the network visualisation is renderable.

## Cumulative cost

For a one-shot deployment on the existing 90,192-record corpus (assumes shared extraction has already been run):

| Stage | Sync | Batches |
|---|---|---|
| 1. Per-doc grouping | ~$200-300 | ~$100-150 |
| 2. 6-axis labelling | ~$300 | ~$162 |
| 3. v2 clustering | ~$3 | n/a |
| 4. Closure | ~$30-50 | ~$30-50 |
| **Total** | **~$530-650** | **~$290-360** |

## What the canonical pipeline does not have

- **No project-axis retrieval UI.** Methodology gap §12 noted that adding a project axis (show me all events for project X) to a navigator would let users recover project-scale narratives. Not built. The legacy `cluster_navigator.html` browses the legacy 660-cluster taxonomy, not this pipeline's 1,141 clusters.
- **No cross-cluster span analysis run on the per-doc grouping output.** The runs/README.md flagged this as the methodology paper's spine claim and "not yet done as part of these runs." Open follow-up.
- **No live joint-reliability readout** (methodology_gaps.md §9). The §11 traceable-uncertainty framing requires per-filter reliability point estimates that haven't been calibrated against human ground truth.
