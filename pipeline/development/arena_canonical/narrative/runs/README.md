# Event-grouping experiments — synthesis

This folder contains every architectural variant we tested for the
extraction-and-event-identity stage of the ARENA pipeline. Each subfolder
is a self-contained snapshot: the prompt, the driver script, and the outputs
exactly as they ran. This README is the entry point — read this first, then
drill into individual run folders for full detail.

## What problem we were trying to solve

ARENA's v1 pipeline ran extraction (the "grave" prompt at
`domains/arena/prompts/extract.md`) followed by post-hoc dedup
(`dedup_haiku/prompt_v2.md`) using cosine similarity + Haiku ratification of
high-cosine pairs. v1 dedup left 84% of "events" as singleton records
because cosine retrieval missed same-event pairs across documents (§8a in
`failure_mode_methodology/methodology_gaps.md`).

The methodology paper relies on a two-axis claim — the **event axis**
(singular occurrences) is **orthogonal to the mechanism axis**
(failure-mode clusters). One occurrence can span multiple mechanism
clusters; the worked example is the Wallbox Quasar AS/NZS 4777
certification challenge, where 6 records of one event spread across 4
mechanism clusters under the v3.5 taxonomy. v1 dedup only marginally
demonstrated this property because most "events" were singletons, so
cross-cluster spans were rare.

We wanted an architecture that:

1. Preserves all extracted records (no extraction-yield loss).
2. Produces tight multi-record events that genuinely span mechanism
   families — so downstream cluster fragmentation surfaces the orthogonality.
3. Operates cleanly under chronological, cross-document corpus structure.
4. Decouples grouping policy from extraction selectivity (so we can
   recalibrate the grouping prompt without re-extracting).

## TL;DR — recommended architecture

**v1 grave-prompt extraction (unchanged) → per-doc post-extract grouping in
seed-doc-first chronological order with running event registry.** Driver:
`pipeline/group_events.py` invoked with `--batch-size 200` so each doc is
one Sonnet call. Snapshotted in
[`2026-05-02-postextract-grouping-perdoc/`](2026-05-02-postextract-grouping-perdoc/).

On REVS 3-doc subset: 165 records → 47 events; 28% singleton rate (vs v1
dedup's 90%); 26% of events span ≥2 docs (vs v1 dedup's 0%); $0.56 per
project. The 6 canonical Wallbox-Quasar worked-example records all collapse
onto a single event, preserving the cross-cluster-span property.

## All approaches tested — empirical comparison

Same input data: the 3 most-substantive REVS docs (`doc_0844` Crossing
Sectors Report, `doc_1347` Lessons Learnt 2, `doc_1348` Lessons Learnt 1).
v1 extracted 165 records from these 3 docs in total.

| # | Approach | Records | Events | r/e | Singleton% | Cross-doc% | Max event | Cost | Wall |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v1 extract → v1 dedup (cosine + Haiku) | 165 | 141 | 1.17 | 90% | 0% | 6 | — | — |
| 2 | v2 extraction with mechanism-coherent same-event criterion | 156 | 56 | 2.79 | 39% | 23% | 14 | $1.17 | ~9m |
| 3 | v2 occurrence-coherent + v1-dedup-style split rules | 149 | 76 | 1.96 | 57% | 13% | 14 | $1.16 | ~12m |
| 4 | v2 occurrence-coherent merge-permissive | 138 | 64 | 2.16 | 47% | 20% | 9 | $1.12 | ~18m |
| 5 | v1 extract → post-extract grouping batched (8-call) | 165 | 44 | 3.75 | 32% | 25% | 22 | $0.76 | 8m |
| 6 | v1 extract → post-extract grouping one-shot (1-call) | 165 | 63 | 2.62 | 40% | 17% | 8 | $0.45 | 5m |
| **7** | **v1 extract → post-extract grouping per-doc (3-call)** | **165** | **47** | **3.51** | **28%** | **26%** | **11** | **$0.56** | **6m** |

Approach 7 (per-doc one-shot post-extract) wins on singleton rate, cross-doc
rate, and cost-effectiveness. It is the recommended production architecture.

## Three findings that fell out of these experiments

### Finding 1 — bundled axis-tagging at extraction is a contamination risk

Earlier in the experiment sequence we tried adding factual axis tags
(causal_claim_made, valence, mechanism_named, realisation, stakeholder,
interface_locus, outcome_class) to the extraction prompt. The user
intervened: extraction should be source-faithful, all categorical labelling
is downstream. The same principle later resolved the event-grouping
confound — see Finding 3.

The labelling pass now lives at `pipeline/label_axes.py` and operates on
already-extracted records; not part of these experiments but architecturally
sibling work.

### Finding 2 — chunked extraction does not recover saturation losses below ~150k input tokens

`methodology_gaps.md` §15 originally claimed that single-pass extraction
saturates above ~10k input tokens, projecting ~92k records lost
corpus-wide. The first v2 run (mechanism-coherent with default chunking)
appeared to confirm this. But on apples-to-apples comparison with v1 (both
on Sonnet 4.6), chunking *cost* records on small/medium docs and added
only ~10% on the 97k-char doc. The §15 claim was retracted to the narrow
case of docs above ~150k tokens (17 docs in the ARENA corpus). Default
v2 chunking threshold raised to 600k chars in `pipeline/extract_v2.py`.

### Finding 3 — extraction selectivity and event grouping must be decoupled

The three v2-extraction prompt variants (rows 2-4 above) produced
**different total record counts**: 156, 149, 138. If extraction yield
were independent of grouping policy, the same source content should
produce the same number of records. It didn't, because the event-grouping
instructions ("attach lessons to existing events," "merge aspect-distinct
records," etc.) were leaking into the model's extraction selectivity:
the model was treating "this finding is already covered by EVT-0017" as
a signal to skip extracting it.

Decoupling extraction from grouping (rows 5-7 — extract once with the
v1 grave prompt, then group as a separate Sonnet pass on the records)
preserved all 165 source records and produced empirically tighter event
graphs than any extraction-time grouping variant.

### Finding 4 — chronological cross-doc accumulation is what consolidates events

Approach 6 (one-shot, all 165 records to a single Sonnet call) and
Approach 7 (per-doc, 3 calls with running event registry) used the
same prompt and the same source records. The only difference was
whether the model saw the records all at once or one doc at a time
with previously-established events as context.

Result: one-shot produced 63 events with 17% cross-doc rate; per-doc
produced 47 events with 26% cross-doc rate. The chronological-with-running-
registry framing materially tightens consolidation. The 6 canonical
worked-example records grouped onto one event under per-doc but split
across 2 events under one-shot.

The mechanism: the seed doc (the project synthesis report) establishes a
small set of high-scope event names. Subsequent docs see those names as
anchors and pull aspect-distinct records from later reports onto them.
Without that chronological anchoring, the model decomposes naturally into
finer-grained sub-events.

This is the §13 chronological-event-identity framing, validated empirically
in a setting where it didn't have to be true (extraction was decoupled).
The §13 mechanism is a real architectural lever, not an artefact of
extraction-time grouping decisions.

## How to read each subfolder

Each `runs/<test-name>/` folder contains:

- `code/` — the prompt(s), driver script(s), and any predecessor versions,
  exactly as they ran. Do not rely on the canonical
  `pipeline/extract_v2.py` matching what's in here — that file evolves.
- `outputs/<project>/` — per-doc extraction output (`doc_NNNN.json`,
  `doc_NNNN.events.json`) and any raw API responses (`_raw/`).
- `notes.md` — what was tested, the result, and how it relates to other runs.

## Subfolder index, in test sequence order

1. [`2026-05-01-mechanism-coherent-grave/`](2026-05-01-mechanism-coherent-grave/) —
   v2 extraction with mechanism conjunct in same-event criterion
   (`same actors AND same time AND same locus AND same causal mechanism`).
   First successful v2 build on the grave prompt. Hornsdale FCAS + REVS
   3-doc.
2. [`2026-05-01-occurrence-coherent-grave/`](2026-05-01-occurrence-coherent-grave/) —
   dropped the mechanism conjunct, added v1-dedup-style explicit MERGE/SPLIT
   rules. Surprisingly produced *more* singletons than mechanism-coherent —
   the v1-dedup split rules ("different recommendations are typically
   different events") gave the model new reasons to split.
3. [`2026-05-02-occurrence-merge-permissive/`](2026-05-02-occurrence-merge-permissive/) —
   stripped the v1-dedup split rules, kept occurrence-coherent + strong
   merge instructions. Fragmented the Wallbox cert story into 8 separate
   events; the largest event was 9 records vs mechanism-coherent's 14.
   Surfaced the orthogonality confound.
4. [`2026-05-02-postextract-grouping/`](2026-05-02-postextract-grouping/) —
   first decoupled run. v1 extraction unchanged; new grouping pass at
   `pipeline/group_events.py` operating on already-extracted records.
   Batched per ~20 records per call (8 calls on REVS 3-doc). Tightest
   event graph yet: 44 events, max event size 22, all 6 canonical records
   on one event. Validated the decoupled architecture.
5. [`2026-05-02-postextract-grouping-oneshot/`](2026-05-02-postextract-grouping-oneshot/) —
   variant: send all 165 records to a single Sonnet call. Surprisingly
   *less* consolidated than batched (63 events, max event size 8). The
   canonical 6 records split across 2 events. Showed that within-doc
   batching is not the consolidation mechanism.
6. [`2026-05-02-postextract-grouping-perdoc/`](2026-05-02-postextract-grouping-perdoc/) —
   variant: one Sonnet call per doc (3 calls), seed-doc first, running
   event registry between docs. **Lowest singleton rate (28%) and highest
   cross-doc rate (26%) of any approach.** Isolated the
   chronological-accumulation finding. **This is the recommended
   production architecture.**
7. [`2026-05-02-postextract-grouping-fullrevs/`](2026-05-02-postextract-grouping-fullrevs/) —
   scale test: per-doc grouping run on the full 12-doc REVS project
   (937 v1 records). Replicate Jaccard 0.519 (worse than 3-doc); 483
   consensus events at ≥2/3 threshold; reproduces 70% of v1 dedup's
   confident pairs and finds 1330 new cross-doc pairs.
8. [`2026-05-02-replication-campaign/`](2026-05-02-replication-campaign/) —
   3 reps × 3 configs (perdoc-baseline, perdoc-no_lessons, oneshot) on
   REVS 3-doc to characterise noise floor at temperature=0. **Key
   findings: dropping `lesson` from grouping input materially improves
   replicate Jaccard (0.678 → 0.786); the FC subset of grouped records
   is essentially deterministic across reps (Jaccard 1.000 between rep2
   and rep3) even when the full event groupings have ~21% noise.**
9. [`2026-05-02-record-type-pilot/`](2026-05-02-record-type-pilot/) —
   first pilot of the 6-axis record-type + 4-value valence labelling
   scheme on 173 records of NT SETuP's top 5 events. Multi-label
   tagging empirically necessary (68% of records have ≥2 type tags).
   `no_valence` correctly distinguishes designed-mechanism descriptions
   from genuine failures; FC pool expands 3.5× while excluding
   normal-operations records that polluted v1's FC pool. Cost $0.086
   Haiku for 173 records → ~$23 batch projection for 90k corpus.

## Cross-axis: orthogonality validation — DONE 2026-05-04

The methodology paper claim — that one event spans multiple mechanism
clusters — has been validated empirically on the canonical pipeline.
See [`../../analysis/cross_cluster_span/notes.md`](../../analysis/cross_cluster_span/notes.md)
for the full analysis.

**Headline (full corpus, 90,192 records):** strictly-comparable metric
(events with ≥2 FC-pool member records, fraction spanning ≥2 clusters):
**71.9% — 3,120 of 4,341 events** spanning ≥2 distinct mechanism
clusters. Span distribution has a long tail to 14 clusters per event.
Substantially higher than legacy methodology_gaps.md §8a's 52% on v3p5.

12-doc REVS test-subset reference (3 reps, temp=0): 74.1% / 81.0% /
81.8% (mean 79.0%) — within reason of the corpus-wide finding.

The orthogonality claim is empirically supported at production scale
and stronger on canonical than it was on legacy. Two architectural
contributors: canonical's 1,141-cluster catalogue is finer than
legacy's 660-cluster v3p5; canonical per-doc grouping is aspect-
permissive by design where legacy stage-1 dedup was conservative-split.

Caveat to disclose honestly: the canonical grouping is single-rep
production. Replicate-stability of the 71.9% number itself is
unmeasured (3-rep REVS subset showed ~7pp range, 74-82%; full-corpus
rep-noise unknown).

## Production handoff checklist

Before running this on ANAO or as the canonical ARENA pipeline, the
following remain open:

1. **Coverage check on per-doc grouping output** — by construction it
   should be 100% record preservation; verify with
   `corpora/arena/tests/extraction/check_v2_coverage.py` or simpler
   set-equality check.
2. **Event-coherence check** — sample N events from the per-doc output,
   ask Haiku "do the records assigned to this event_id describe one
   singular occurrence?" Different from coverage; tests the *grouping
   quality*, not the *record content fidelity*.
3. **Cross-cluster span analysis** — for the per-doc grouping events,
   compute how many v3.5 clusters each event spans. The worked example
   claims 4 clusters for a 6-record event; check whether the larger
   per-doc events (10+ records) span more clusters.
4. **Full ARENA scale test** — extrapolate from the REVS 12-doc cost
   ($3-4 estimated) to the 502-project corpus: ~$200-300 total grouping
   pass on top of v1 extraction. Plausible.
5. **ANAO architecture decision** — the same architecture should work
   on ANAO as long as v1-style extraction runs there first. Project
   structure in ANAO is different (single-audit per program); the
   seed-doc heuristic collapses to "the audit report itself."
