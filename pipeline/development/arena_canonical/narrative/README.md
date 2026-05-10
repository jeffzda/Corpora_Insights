# Canonical narrative — reading order

The canonical pipeline's design rests on a sequence of test runs and methodology arguments. Read in this order.

## 1. The 8-run synthesis

`runs_synthesis.md` (canonical narrative entry point). Compares 7 grouping architectures on the same 165-record REVS 3-doc input and identifies per-doc seed-doc-first chronological grouping with a running event registry as the winning architecture (28% singleton rate, 26% cross-doc rate, $0.56/project).

The synthesis names three findings that fell out of these experiments:

- **Bundled axis-tagging at extraction is a contamination risk.** Adding factual axis tags to the extraction prompt was abandoned; categorical labelling lives downstream.
- **Chunked extraction does not recover saturation losses below ~150k tokens.** The §15 retraction in `methodology_gaps.md` justifies retaining the v1 grave extraction.
- **Extraction selectivity and event grouping must be decoupled.** Three v2-extraction prompt variants produced different total record counts (156, 149, 138) on the same source. Decoupling preserved all 165 records.

Plus a fourth finding documented in the runs:

- **Chronological cross-doc accumulation is what consolidates events.** One-shot grouping (all records in one Sonnet call) produced 63 events with 17% cross-doc rate; per-doc with running registry produced 47 events with 26% cross-doc rate.

## 2. The 8 dated test-run snapshots

`runs/` holds each experiment in chronological order. Each subfolder has its own `notes.md` describing what was tested and how it relates to siblings. Reading them top-to-bottom traces the design path.

| Snapshot | Why it matters |
|---|---|
| `2026-05-01-mechanism-coherent-grave/` | First v2 extraction variant — mechanism conjunct in same-event criterion. Gives the headline 56 events on REVS 3-doc (39% singleton). |
| `2026-05-01-occurrence-coherent-grave/` | Dropped mechanism conjunct, added v1-dedup-style explicit MERGE/SPLIT rules. Surprisingly *more* singletons (57%) — split rules backfired. |
| `2026-05-02-occurrence-merge-permissive/` | Stripped split rules, kept occurrence-coherent + strong merge instructions. Fragmented Wallbox cert into 8 events. Surfaced the orthogonality confound. |
| `2026-05-02-postextract-grouping/` | First decoupled run. v1 extraction unchanged; new grouping pass operating on already-extracted records. 44 events; max event size 22; all 6 canonical Wallbox records on one event. **Validated the decoupled architecture.** |
| `2026-05-02-postextract-grouping-oneshot/` | Variant: send all 165 records to a single Sonnet call. *Less* consolidated than batched. Showed that within-doc batching is not the consolidation mechanism. |
| `2026-05-02-postextract-grouping-perdoc/` | Variant: one Sonnet call per doc, seed-doc first, running event registry. **Lowest singleton rate (28%) and highest cross-doc rate (26%). Recommended production architecture.** |
| `2026-05-02-postextract-grouping-fullrevs/` | Scale test on full 12-doc REVS project (937 v1 records). Replicate Jaccard 0.519, 483 consensus events at ≥2/3 threshold, reproduces 70% of v1 dedup's confident pairs. |
| `2026-05-02-replication-campaign/` | 3 reps × 3 configs at temperature=0 to characterise noise floor. Dropping `lesson` from grouping input materially improves replicate Jaccard (0.678 → 0.786). FC subset is essentially deterministic across reps. |
| `2026-05-02-record-type-pilot/` | First pilot of the 6-axis record-type + 4-value valence labelling scheme on 173 records of NT SETuP's top 5 events. **The Sonnet vs Opus is_mechanism finding** that drove the canonical labelling choice. |

The other folders (`2026-05-02-fullcorpus-1rep/`, `2026-05-02-postextract-grouping-no-lessons/`, `2026-05-02-fullrevs-production/`) are scale extensions of the architectures above.

## 3. v2 clustering and closure

`clustering_v2_notes.md` (~630 lines) walks through the v2 sweep iteration history: seed-cluster runs, orphan reclassification, attention A/B test, neutral-prompt variants, the convergence iteration. Some lessons are repeated from `methodology_lessons.md` (one-shot beats chunked, signature immutability) but with the empirical evidence specific to clustering attached.

`clustering_v2_inspection_notes.md` is the closure-phase inspection notes — what each closure script produced and how to read it.

## 4. The cross-pipeline methodology

`methodology_gaps.md` (copied here from `legacy/narrative/failure_mode_methodology/`) is a 17-gap research roadmap. The gaps relevant to the canonical pipeline:

- **§8a — events vs mechanism-clusters orthogonality.** The legacy diagnostic that motivated the rewrite. 52% of multi-record events span ≥2 clusters under top-10 Stage F validation.
- **§13 — chronological event-identity.** Implemented post-extraction in `pipeline/group_events.py`, not at extraction time as originally proposed (because §15 retraction validated retaining the v1 extraction).
- **§14 — bundled per-record axis tagging.** Implemented as the 6-axis Opus 4.6 labelling pass, not as a bundled extraction-time schema.
- **§15 — retraction.** Justifies retaining the v1 grave extraction. Saturation behaviour is real only above ~150k tokens (17 of 1,440 ARENA docs).
- **§17 — Sonnet under-tags is_mechanism.** Drives the Opus 4.6 choice for canonical labelling.

`methodology_notes.md` locks the epistemic position (§7 — trust author-stated causation only) and pragmatic execution stance (§8 — first-pass framing, value-against-counterfactual rather than gold-standard). These aren't canonical-pipeline-specific but they shape what the canonical pipeline is allowed to claim.

## 5. The seed-doc heuristic

`seed_doc_heuristic.md` describes the rule for picking the first document per project (the document whose extracted records establish the canonical event names that subsequent docs anchor to). `seed_doc_heuristic.py` implements it. Empirically: project-synthesis-level reports beat per-component reports when used as the seed.

## 6. Coverage and footnote checks

`check_v2_coverage.py` confirms the per-doc grouping output preserves all input records (by construction it should — set-equality check). `check_footnote_handling.py` is the diagnostic from `methodology_gaps.md` §16 about how marker-rendered footnotes flow through extraction.
