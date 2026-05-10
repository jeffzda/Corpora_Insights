# Replication campaign — characterise the noise floor at temperature=0

**Date:** 2026-05-02. **Commit:** `fb13195` ("test: 9-rep replication campaign + 12-doc fullrevs production run"). **Reconstructed from commit message + driver code + `analysis/consensus_analysis.py`.**

## Hypothesis

Up to this run, several architectural claims about the post-extract grouping pass had been made on single-replicate evidence:

- Per-doc batched grouping produces 44 events vs one-shot's 63 events on REVS 3-doc (the headline contrast that drove the recommended-architecture choice in `runs/README.md`)
- Including the `lesson` field as input to grouping helps because it conveys cross-record synthesis the model wouldn't otherwise see
- Temperature=0 produces stable replicates suitable for a single-rep production run

All three claims rest on a presumption that the noise floor at temp=0 is small relative to the architectural effects. **This run measures that noise floor empirically** by running 3 replicates × 3 grouping configs on the same REVS 3-doc input (165 records).

## Design

3 configs × 3 replicates each = 9 runs at temperature=0.

| Config | Driver | Inputs |
|---|---|---|
| `perdoc_baseline` | `code/group_events.py` per-doc with running event registry | record narrative + lesson + evidence (default fields) |
| `perdoc_no_lessons` | same driver, `--exclude-fields lesson` | narrative + evidence only |
| `oneshot` | `code/group_events_oneshot.py` (single Sonnet call over all 165 records) | narrative + lesson + evidence |

Same input data: 3 most-substantive REVS docs (`doc_0844` Crossing Sectors Report, `doc_1347` Lessons Learnt 2, `doc_1348` Lessons Learnt 1). 165 v1 records.

Driver patches landed in this run:
- `temperature=0` made the default in `group_events.py` and `group_events_oneshot.py` (was previously absent → API default 1.0)
- Streaming used when `max_tokens > 8192` (the first fullrevs attempt failed in 14 seconds with a non-streaming SDK error; second attempt with streaming + pipefail succeeded)
- `--exclude-fields lesson` CLI flag added so the no-lessons config could be tested without forking the prompt
- Default `max_tokens` raised to 32k

## Results

### Event counts per replicate

| Config | rep1 | rep2 | rep3 | mean | stddev |
|---|---|---|---|---|---|
| perdoc_baseline | 44 | 47 | 51 | 47.3 | 3.5 |
| perdoc_no_lessons | 48 | 51 | 56 | 51.7 | 4.0 |
| oneshot | 50 | 53 | 61 | 54.7 | 5.7 |

### Replicate Jaccard (pair-set agreement across reps within each config)

| Config | Jaccard | Interpretation |
|---|---|---|
| **perdoc_no_lessons** | **0.786** | **Most stable.** Dropping lesson improved replicate agreement by ~16% over baseline. |
| perdoc_baseline | 0.678 | Baseline (~32% of pair-grouping decisions are unstable across reps). |
| oneshot | 0.664 | Worst; comparable to baseline despite simpler architecture. |

`analysis/consensus_analysis.py` builds the pairwise co-grouping matrix per config and computes Jaccard at the pair-set level (not at the event-membership level). For each pair of records, it counts how many replicates of a config place them in the same event; Jaccard between replicates is `|A∩B| / |A∪B|` over those pair-sets. Same script computes consensus-event graphs at thresholds 1/3, 2/3, 3/3 by taking pairs with co-grouping count ≥ threshold and computing connected components.

## Findings

**1. Replicate noise floor at temp=0: ~32% of pair-grouping decisions are unstable across reps of the same config at 3-doc scale.**

This is *substantial*. Several earlier architectural claims were inside this noise envelope:
- "44 events batched vs 47 events perdoc" (cited in `runs/README.md` table) is sampling fluctuation, not an architectural difference. The two means are within 1 stddev of each other.
- The "max event size" column in the synthesis table is similarly volatile across reps.
- Anything claiming a per-config event-count difference smaller than ~5 events on this scale is unsafe.

**2. Dropping the `lesson` field IMPROVES replicate stability (Jaccard 0.786 vs 0.678).** This was a user hypothesis going in and was confirmed empirically. The mechanism: lessons are model-synthesised text that incorporates cross-context inference (per `legacy/narrative/failure_mode_methodology/methodology_notes.md` §6.5 on lesson-field model invention). When the grouping prompt sees lessons, the model's pair-grouping decisions are influenced by paraphrase-similarity in the *synthesised* lesson text — and that paraphrase similarity is itself noisy across reps. Removing lessons leaves only narrative + evidence (which are closer to source-faithful) and the model's grouping decisions become more reproducible.

This is methodologically important: **replicate stability is not just a quality metric; it's a signal that the input fields are appropriate for the task.** The lesson field carries useful synthesis content but it actively destabilises grouping.

The drop-lesson decision was adopted as the production default (`group_events_corpus.py --exclude-fields lesson`) for the subsequent full-corpus run.

**3. The chronological-accumulation finding survives the noise floor — barely.** The canonical 6-record Wallbox-Quasar event grouped onto one event in 3/3 perdoc replicates but only 1/3 oneshot replicates. The headline event-count gap (perdoc 47.3 vs oneshot 54.7) sits at z=1.9 — borderline-significant. The architectural choice (per-doc with chronological registry over one-shot) is supported but not by an order-of-magnitude effect.

**4. The FC subset is essentially deterministic across reps** even when the full event groupings have ~21% pair-noise. (Filed as memory finding `feedback_stability_not_accuracy.md` cross-reference: replicate-pair agreement was 1.000 between rep2 and rep3 on the FC subset alone, vs 0.786 on full event set.) Mechanism: the records that land in failure-mode-candidate clusters are the ones with sharp negative-valence + named-mechanism content, which the model groups consistently. The records contributing to noise are the borderline / context-only records.

## Implication for the production architecture

The recommended production architecture (per-doc grouping with `--exclude-fields lesson`) was finalised on this evidence:

```
v1 grave extraction → group_events_corpus.py per-doc seed-doc-first chronological
                      with --exclude-fields lesson, temperature=0
```

The next run (`2026-05-02-postextract-grouping-fullrevs`) deployed this configuration on the full 12-doc REVS project at 3 replicates to test whether stability holds at scale.

## Files in this snapshot

- `code/group_events.py` — per-doc grouping driver (state at this run; differs from canonical pipeline/group_events.py which has since evolved)
- `code/group_events_oneshot.py` — one-shot variant
- `code/group_events.md` — the prompt at this run's state
- `analysis/consensus_analysis.py` — co-grouping matrix + consensus event graphs at multiple thresholds

## Cross-references

- `2026-05-02-postextract-grouping-fullrevs/notes.md` — the next-step scale test that built on this run
- `runs/README.md` — synthesis (rows 5-7 + Finding 4 reference back to this campaign for the within-noise-floor caveat)
- Memory: `feedback_stability_not_accuracy.md` (within-rep stability ≠ accuracy), `feedback_one_shot_beats_chunked.md` (related Sonnet-4.6 finding on rule-application tasks)

Total cost across the 9 replicates: roughly $5 (Sonnet 4.6 sync). Wall: ~3 hours.
