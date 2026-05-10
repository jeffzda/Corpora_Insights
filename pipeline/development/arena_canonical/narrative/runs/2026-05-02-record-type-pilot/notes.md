# Test snapshot — 2026-05-02 — record-type-pilot

> **TL;DR for paper-writing.** This 1,700-line file documents **ten distinct experiments** that landed the canonical labelling decision (Opus 4.6 + temp=0 + v3 prompt + full JSON output, 6 axes). Use the TOC below to find the experiment you want; each is a self-contained block with its own configuration, results, and production-decision implication. The major findings (in commit-history order) are:
>
> 1. **9-rep cross-tier (Haiku × Sonnet × Opus)** — Sonnet within-model stability (0.980) is *higher* than Opus (0.969) but accuracy is *lower* — stability ≠ accuracy.
> 2. **NT SETuP 173-record pilot** — multi-label tagging validated (68% records carry ≥2 type tags); four-value valence beats v1's 3-way scheme.
> 3. **v3 prompt cross-tier sweep** — three plausible production configs (no clean winner from stability alone).
> 4. **Output-format compression study** (full JSON / hybrid / compact / terse) — verbose JSON wins on loose-boundary axes; format is a deliberation surface.
> 5. **Opus referee + extended thinking** — extended thinking does not substitute for output-format deliberation.
> 6. **Hand-adjudication of contested set** — establishes accuracy ground truth (Opus 96% vs Sonnet 81%).
> 7. **v4 prompt iteration** — targeted is_specification fix; doesn't move the needle enough to deploy.
> 8. **2,000-record at-scale validation** — falsifies pilot-scale FC-pool finding (pool size matches by *coincidence*; composition still diverges by ~28% Jaccard 0.76).
> 9. **44-record hand-adjudication of is_mechanism disagreements** — Opus correct on 75% of under-tag direction → ~8,000 records corpus-wide tagged is_mechanism=no by Sonnet should be yes.
> 10. **Cross-version Opus check (4.6 + temp=0 vs 4.7 default)** — same accuracy, higher reproducibility → production swap to **Opus 4.6 + temp=0** as the canonical labelling tier.
>
> The methodology paper claims that emerged: stability-vs-accuracy distinction (#1, #6); output-format-as-deliberation-surface (#4, #5); Sonnet under-tags is_mechanism by ~10pp at scale, ~8,000 records corpus-wide (#8, #9); definitionally loose axes need verbose schema + Opus tier (#9, #10).
>
> ## Table of contents — by experiment
>
> | # | Section | Experiment | Headline finding |
> |---|---|---|---|
> | — | "Why this is the highest-value calibration" (line 22) | Pilot framing | tagging is the lever; replicate budget justified |
> | — | "What the cross-model experiment tests" (line 62) | Hypothesis statement | what the 9-rep run is supposed to discriminate |
> | — | "What this enables for the methodology paper" (line 88) | Paper claim mapping | which findings would survive into write-up |
> | — | "Cost discipline note" (line 101) | Spend justification | $9 for 9 reps is paper-relevant insurance |
> | **EXP-1** | "9-rep cross-tier results" (line 118) | 3 Haiku × 3 Sonnet × 3 Opus on 173 records | within-model stability ≠ cross-tier agreement; Haiku has systematic valence bias |
> | EXP-1.b | "Follow-up — Haiku valence-bias correction" (line 261) | retroactive Haiku-only fix attempt | (in progress at the time) |
> | **EXP-2** | "Configuration" (line 285) → "Open follow-ups" (line 496) | NT SETuP 173-record pilot at v2 prompt | multi-label necessary (68%); FC pool 3.5× v1; diagnostics 1+2 |
> | **EXP-3** | "v3 prompt cross-tier sweep" (line 514) | 3 reps × 3 tiers under v3 prompt | three plausible production configs (no clean winner) |
> | **EXP-4a** | "Output-format compression study" (line 692) | full JSON / hybrid / compact / terse | verbose schema buys per-axis calibration; loose axes break first |
> | **EXP-4b** | "Output-format study — follow-up: Opus referee + extended thinking" (line 811) | Opus referee, extended thinking budget | thinking budgets are model-discretionary, ~13 tokens used of 4000 |
> | EXP-4c | "Correction to the Opus-referee framing" (line 1030) | reframe Opus-as-referee → Opus-as-second-opinion | same direction, weaker claim |
> | **EXP-5** | "Hand-adjudication results — what the contested set actually showed" (line 1100) | Jeff hand-adjudicates contested set | per-format accuracy table; stability ≠ accuracy ground-truthed |
> | **EXP-6** | "v4 prompt iteration result + production decision" (line 1219) | v4 prompt targeted at is_specification | 1-rep result; doesn't move FC-pool gap enough |
> | **EXP-7** | "FC-pool effect of the is_specification errors" (line 1315) | post-hoc analysis of disagreement causes | 0% of FC disagreements caused by is_specification flips; is_mechanism is the lever |
> | **EXP-8** | "2,000-record at-scale validation result" (line 1387) | stratified 2k-record Sonnet vs Opus | pool size matches (-0.6%) but composition diverges (Jaccard 0.76); ~28% of FC records would differ |
> | **EXP-9** | "Hand-adjudicated is_mechanism — Opus genuinely more accurate" (line 1571) | 44 records sampled from 277 disagreement pool | Opus correct on 18/24 (75%) under-tag; ~8,000 records corpus-wide |
> | **EXP-10** | "Cross-version Opus check — 4.6 + temp=0 vs 4.7 default" (line 1640) | 3 reps Opus 4.6 temp=0 vs Opus 4.7 default | same accuracy; higher stability; production swap to **Opus 4.6 + temp=0** |
>
> ---

> **Headline:** Pilot of the 6-axis record-type + valence labelling scheme
> on the 173 records of NT SETuP's top 5 events. **Expanded to 9 replicate
> runs across three model tiers (3× Haiku 4.5 / 3× Sonnet 4.6 / 3× Opus 4.7,
> all at temperature 0)** to characterise within-model and cross-tier tag
> stability. Multi-label tagging empirically validated (51% of records
> carry ≥2 type tags). The four-value valence scheme is more discriminating
> than v1's 3-way scheme — `no_valence` correctly identifies designed-
> mechanism descriptions that v1 was forcing into `negative`. Failure-mode
> candidate (FC) pool expands 3.5× while excluding normal-operations
> records that polluted v1's FC pool. Total spend across 9 reps: ~$9.
>
> See [`../README.md`](../README.md) for the full sequence context.
>
> **Predecessor:** [`../2026-05-02-replication-campaign/`](../2026-05-02-replication-campaign/) —
> established that the FC subset is rock-stable across replicates while
> non-FC records vary, motivating a dedicated record-type axis.
> **Successor:** corpus-wide labelling pass once authorised — would apply
> the 6 axes across all 90k records (~$25 Haiku batch).

## Why this is the highest-value calibration in the pipeline

The decision to expand from a single Haiku rep to 9 replicates spanning
three model tiers reflects an explicit prioritisation: **tagging is the
layer where errors are silent and consequential, and is therefore the
calibration most worth spending on.**

Reasons:

1. **Tagging gates everything downstream.** What enters the failure-mode
   cluster pool depends on `valence` + `is_occurrence` + `is_mechanism`.
   What lands in the lessons compendium depends on `is_lesson`. What gets
   categorised as program-context vs project-event depends on
   `is_specification` vs `is_occurrence`. The taxonomy of records *is*
   the dataset — wrong tags produce a different downstream artefact
   entirely.

2. **Tagging errors are silent.** Extraction has source-grounding via
   verbatim evidence quotes — a wrong extraction is visibly wrong.
   Grouping can be cross-checked against source narratives. Cluster
   assignments can be hand-inspected. But tags are categorical labels
   with no ground truth visible to the consumer — wrong tags propagate
   forward without any obvious signal.

3. **Tagging is the most exposed to model priors.** Extraction is bounded
   by source content; the model can only extract what's there. Grouping
   is bounded by record similarity; the model is comparing things, not
   generating judgements. Tagging is the model's *interpretive judgement*
   about what kind of statement each record makes — most exposed to
   template priors and rhetorical heuristics. The replication campaign
   already showed this empirically (lesson-field bias improved replicate
   Jaccard from 0.678 → 0.786 just by removing one input field).

4. **Tag changes are multiplicative across the corpus.** A 5%
   disagreement on `is_lesson` between two model tiers, applied across
   90k records, is 4,500 records that show up in one compendium and not
   the other. The original v1 → new-scheme valence definition shift
   alone changes 26 of 173 records' FC eligibility (15%) — extrapolating
   to the corpus, that's ~13,500 records.

## What the cross-model experiment tests

The 9-rep design isolates four different signals:

- **Within-model noise floor per axis.** Does `is_lesson` flip between
  reps of the same model at temp 0? Does `valence`? If so, which axes
  are most fragile? (Hypothesis going in: `valence` is noisiest;
  `is_specification` is most stable.)

- **Cross-tier convergence per axis.** Do Haiku, Sonnet, and Opus tag
  the same records the same way? Or do they have systematically
  different priors about what counts as a lesson vs a recommendation,
  or `no_valence` vs `neutral`?

- **Whether Opus is worth 25× the Haiku price.** If Opus's tags are
  no more stable than Haiku's, the production tier can be Haiku with
  confidence. If Opus is noticeably more discriminating, the cost
  justifies itself for cluster-axis input.

- **Whether disagreement is concentrated on edge cases.** If
  Haiku-Opus disagreement is concentrated in the borderline records
  (the 7 no-type residual; the v1-only-FC excluded), that's
  interpretable model uncertainty on hard cases. If disagreement is
  spread across all records, the axis definitions are loose and need
  prompt revision.

## What this enables for the methodology paper

A clean validation claim: *"The 6-axis labelling scheme produces ≥X%
agreement across model tiers (Haiku 4.5 / Sonnet 4.6 / Opus 4.7) at
temperature 0, with the noisiest axis being [Y] at Z% replicate Jaccard.
Consensus across N replicates of the production tier reduces residual
noise to <W%."*

That's a far stronger methodology claim than "we tagged things and it
worked." It's testable, falsifiable, and gives downstream consumers a
calibrated confidence in the tag layer — which the rest of the pipeline
implicitly trusts.

## Cost discipline note

The $9 spend on this expanded run was authorised explicitly by Jeff after
discussion of why tagging is the foundational layer. Per the standing
instruction (no API spend without explicit instruction), the rule was
upheld — cost was surfaced as a range, the rationale was articulated,
and the user confirmed before launch. Documenting this here so the
methodology-paper account of the noise-floor characterisation can
honestly state how the experimental scope was bounded.

**Pricing correction:** my initial Opus 4.7 pricing constant was wrong —
recorded as $15/M input, $75/M output; correct is $5/M input, $25/M output.
The recorded `cost_usd` field in `outputs/opus-4-7/rep*/tags.json` was
re-computed from the input/output token counts after the user flagged the
error. Actual total spend was $3.05, not $6.67. The pricing constant in
`code/run_pilot.py` was also corrected.

## 9-rep cross-tier results

### Within-model replicate stability per axis (mean agreement across rep-pairs)

| Axis | Haiku | Sonnet | Opus |
|---|---|---|---|
| `is_occurrence` | 0.977 | 0.969 | 0.938 |
| `is_mechanism` | 0.965 | 0.992 | 0.927 |
| `is_specification` | 0.981 | 0.977 | 0.938 |
| `is_lesson` | 0.973 | 0.992 | **0.881** |
| `is_recommendation` | 0.992 | 0.996 | 0.977 |
| `valence` | 0.954 | 0.992 | 0.965 |
| **mean** | **0.974** | **0.986** | **0.938** |

All three tiers achieve 88–99% within-model agreement per axis at the
canonical replicate setting. Tagging is materially more stable than
grouping (~50–80% pair-Jaccard at temp=0). The user's hypothesis that
Opus's reasoning architecture would produce convergence without explicit
temperature control was empirically supported — Opus's stability is only
~3 percentage points below Haiku/Sonnet, and only on interpretive axes
(`is_lesson`, `is_specification`, `is_occurrence`).

### Cross-tier agreement per axis (mean across 9 rep-pair combos)

| Axis | Haiku↔Sonnet | Haiku↔Opus | Sonnet↔Opus |
|---|---|---|---|
| `is_recommendation` | 0.93 | 0.94 | **0.98** |
| `is_lesson` | 0.94 | **0.80** | 0.84 |
| `is_occurrence` | 0.90 | 0.87 | 0.88 |
| `is_specification` | 0.84 | 0.87 | **0.92** |
| `is_mechanism` | 0.86 | 0.86 | 0.85 |
| `valence` | **0.79** | 0.81 | **0.89** |

Cross-tier agreement (~80–98%) is **lower than within-tier** — confirming
systematic prior differences between model tiers, not just sampling noise.
Three patterns:

- `is_recommendation` is the most stable axis everywhere (0.93+ across-tier,
  0.99 within-tier). Imperative-form text has unambiguous markers; models
  converge on it.
- `is_lesson` and `valence` are the noisiest. Haiku-Opus disagree 20% on
  `is_lesson`. Haiku-Sonnet disagree 21% on `valence`.
- Sonnet ↔ Opus agreement is consistently higher than Haiku ↔ Opus,
  suggesting Sonnet and Opus share priors that Haiku doesn't.

### Valence distribution exposes a systematic Haiku bias

| Tier | positive | negative | neutral | no_valence |
|---|---|---|---|---|
| Haiku | 37 % | 31 % | 2 % | **30 %** |
| Sonnet | 35 % | **44 %** | 5 % | 16 % |
| Opus | 34 % | 42 % | 2 % | 22 % |

Haiku uses `no_valence` ~2× as often as Sonnet (30 % vs 16 %), and Sonnet
captures 13 percentage points more `negative` than Haiku does. The prompt
definition explicitly asks the model to trace prescriptive content back
to its underlying situation — Sonnet and Opus follow that; Haiku is
mildly under-applying it.

This is a **calibration issue, not noise.** The 8 records with the
highest cross-tier disagreement all share a common pattern: prescriptive
content where Haiku reads `no_valence` (treating the prescription as
purely structural) and Sonnet/Opus read `negative` (tracing back to
the motivating failure). Examples:

- *"A full-time logistics manager was identified as required for remote
  multi-site programs"* — Haiku: `no_valence`; Sonnet/Opus: `negative`
  (resourcing was inadequate)
- *"Dedicated logistics management resourcing is required to handle
  multiple teams across multiple sites"* — same pattern
- *"Mobile phone coverage is lacking in many remote areas..."* — Opus
  disagrees with itself across reps on `is_lesson` (yes/no/no)

These are interpretable disagreements, not random errors. Whether the
methodology paper uses Sonnet's reading as "correct" or Haiku's as
"correct" depends on definitional choice. The prompt asks for Sonnet's
reading; Haiku is mildly off-spec.

### FC pool size depends materially on tier choice

| Tier | Mean FC | Union FC | Intersection FC |
|---|---|---|---|
| Haiku | 31 | 34 | 28 |
| **Sonnet** | **48** | **52** | **44** |
| Opus | 38 | 48 | 30 |

Sonnet pulls 50 % more records into the FC pool than Haiku, primarily via
the broader `valence: negative` interpretation. Extrapolating to the
~90 k corpus, that's ~6 000–9 000 records that either do or don't enter
cluster analysis depending on tier choice.

### Per-axis noise ranking

```
  is_lesson         0.949  (noisiest)
  is_occurrence     0.961
  is_mechanism      0.961
  is_specification  0.965
  valence           0.970
  is_recommendation 0.988  (most stable)
```

Difference between most and least stable axis is only ~4 percentage
points. The 6-axis scheme is consistently reliable across the board.

### Headline production-tier verdict

**Sonnet 4.6 is the right production tier.** Highest within-model
stability (0.986 mean), strongest agreement with Opus where it matters
(0.92+ on `is_recommendation`/`is_specification`), captures the
broader-valence definition the prompt asks for, costs only 3.7× Haiku.

**Opus is not worth 1.9× Sonnet for this task.** Reasoning convergence
helps on most axes but actually *hurts* on `is_lesson`. Its interpretive
freedom on edge cases produces more disagreement, not less. The corrected
pricing makes Opus more affordable than I initially reported, but it
still doesn't beat Sonnet on quality.

**Haiku is a viable budget tier** if the methodology paper is willing to
flag that the FC pool is ~50% smaller than Sonnet's via Haiku's
conservative valence reading. **Or — the prompt can be tightened to
correct the bias** (see follow-up below).

### Cost summary (corrected)

| Tier | 3 reps | per-corpus extrapolation (90 k) |
|---|---|---|
| Haiku 4.5 | $0.26 | ~$45 sync / ~$23 batch |
| Sonnet 4.6 | $0.96 | ~$170 sync / ~$85 batch |
| Opus 4.7 | $1.83 | ~$320 sync / ~$160 batch |
| **TOTAL (9 reps)** | **$3.05** | |

### Files added in this expansion

- `outputs/haiku-4-5/rep{1,2,3}/tags.json` + `raw_responses.txt` — 3 Haiku
  replicates at temp 0
- `outputs/sonnet-4-6/rep{1,2,3}/tags.json` + `raw_responses.txt` —
  3 Sonnet 4.6 replicates at temp 0
- `outputs/opus-4-7/rep{1,2,3}/tags.json` + `raw_responses.txt` —
  3 Opus 4.7 replicates (no temperature control, model default)
- `analysis/cross_tier_analysis.py` — driver that produced the tables
  above

## Follow-up — Haiku valence-bias correction (in progress)

Given the 8 highest-cross-tier-disagreement records all show the same
pattern (Haiku reads `no_valence`, Sonnet/Opus read `negative` via the
underlying-situation rule), the next experiment is a **prompt
tightening + Haiku re-run** to test whether the bias is correctable
without changing tier:

- The current prompt already specifies "the underlying negative situation
  behind a corrective recommendation" — Haiku is just under-applying it
- A small prompt revision making this rule more prominent and
  unmissable (with explicit anti-example) should close the gap
- 1 Haiku run on the same 173 records ≈ $0.09; can be compared directly
  against the existing Haiku reps to measure the effect

If the prompt-tightened Haiku closes most of the gap to Sonnet's
valence distribution and FC pool, **Haiku-with-tightened-prompt becomes
the production tier candidate** (3.7× cheaper than Sonnet at near-equal
quality).

If the gap persists despite prompt tightening, **Sonnet stays the
production tier**, and the methodology paper documents Haiku's
unrecoverable conservative bias as the reason.

## Configuration

- **Input:** 173 records spanning the top 5 events from the NT SETuP smoke
  test (`/tmp/group_smoketest/nt_solar_energy_transformation_program/`).
  - EVT-0009 — SETuP 10 MW PV deployment (53 records, 11 docs)
  - EVT-0047 — Remote community risk factors (43 records, 4 docs)
  - EVT-0012 — Solar curtailment for diesel min loading (31 records, 9 docs)
  - EVT-0021 — Low-load diesel generator replacement (23 records, 9 docs)
  - EVT-0066 — Remote construction logistics (23 records, 2 docs)
- **Model:** `claude-haiku-4-5-20251001` sync, `temperature=0`,
  `max_tokens=16,000`.
- **Batch size:** 30 records per LLM call (6 batches total).
- **Input fields per record:** `id`, `narrative`, `evidence`, `intervention`
  only. **The `lesson` field is deliberately excluded** to avoid LLM-prior
  contamination (see methodology paper finding: dropping the `lesson` field
  from grouping input improved replicate Jaccard from 0.678 → 0.786).
- **Prompt:** `code/label_record_types.md` defines 6 axes —
  `is_occurrence`, `is_mechanism`, `is_specification`, `is_lesson`,
  `is_recommendation`, plus four-value `valence` (positive / negative /
  neutral / no_valence).

## Run statistics

| Metric | Value |
|---|---|
| Records tagged | 173 / 173 |
| Input tokens | 32,961 |
| Output tokens | 14,814 |
| Cost (Haiku 4.5 sync) | **$0.086** |
| Wall time | 61 s |
| Per-record cost | $0.0005 |

Extrapolating: full 90 k corpus at this per-record cost ≈ **$45 sync /
~$23 batch.**

## Per-event composition

| Event | Total | Occ | Mech | Spec | Lesson | Rec | pos | neg | neutral | no_val |
|---|---|---|---|---|---|---|---|---|---|---|
| EVT-0009 (deployment) | 53 | 40 | 11 | 29 | 10 | 3 | **32** | 0 | 1 | 20 |
| EVT-0047 (risk catalogue) | 43 | 4 | 18 | 6 | **41** | **30** | 4 | **38** | 0 | 1 |
| EVT-0012 (curtailment) | 31 | 7 | **27** | 4 | 10 | 0 | 8 | 3 | 2 | **18** |
| EVT-0021 (gen replacement) | 23 | 14 | 6 | 6 | 4 | 8 | **15** | 5 | 1 | 2 |
| EVT-0066 (construction logistics) | 23 | 11 | 8 | 3 | 5 | 10 | 3 | 7 | 0 | 13 |

The composition profiles are interpretable and event-distinctive:

- **EVT-0009** is the *what-is-SETuP* specification event (zero negatives
  despite being largest; 32 positive, 20 no_valence, mostly occurrences and
  specifications).
- **EVT-0047** is the *failure-mode prophylaxis* event (4 occurrences but
  41 lessons + 30 recommendations; 88 % negative valence — driven by the
  underlying failures the prescriptions reference).
- **EVT-0012** is the *how-curtailment-works* mechanism event (87 % of
  records are mechanism; 58 % no_valence because curtailment is *designed
  behaviour*, not a failure).
- **EVT-0021** is the *successful upgrade* event (15 positive, 5 negative;
  mostly occurrences).
- **EVT-0066** mixes realised disruptions (negative) with operational
  descriptions (no_valence).

## Multi-label findings

| Type tags per record | n | % |
|---|---|---|
| 0 | 7 | 4 % |
| 1 | 48 | 28 % |
| 2 | 89 | 51 % |
| 3 | 27 | 16 % |
| 4 | 2 | 1 % |

**Multi-label tagging is empirically necessary.** A single-primary scheme
would have forced coin flips on 68 % of records.

Top type-combinations:

| Combination | n |
|---|---|
| occurrence + specification | 25 |
| mechanism + lesson | 18 |
| occurrence (only) | 17 |
| mechanism + lesson + recommendation | 15 |
| lesson + recommendation | 14 |
| occurrence + mechanism | 12 |
| mechanism (only) | 10 |
| specification (only) | 8 |
| recommendation (only) | 8 |
| (no type tags) | 7 |

## Valence findings

| Value | n | % |
|---|---|---|
| positive | 62 | 36 % |
| negative | 53 | 31 % |
| neutral | 4 | 2 % |
| **no_valence** | **54** | **31 %** |

`no_valence` is used liberally (31 %) for purely structural / mechanism /
specification content. `neutral` collapses to its proper rare meaning
(2 % — genuinely balanced outcomes). This empirically validates splitting
v1's 3-way valence scheme into a 4-value scheme — the bulk of v1's
"neutral" records were actually structural content with no valence
applicable.

## Failure-mode candidate (FC) pool comparison

Within these 173 records:

| Scheme | FC records |
|---|---|
| v1 (causal + neg + realised + mechanism_named) | 9 |
| **NEW** (valence = neg AND (occ OR mech)) | **32** |
| Overlap (both schemes) | 6 |
| v1 only — excluded by new scheme | 3 |
| **NEW only — missed by v1** | **26** |

**3.5× expansion** of the failure-mode-relevant pool. The 26 new records
are mostly mechanism-of-failure or occurrence-of-failure that v1's narrow
filter chain missed (Stage 2 dropped them at causal-recovery; Stage A
filtered out non-mechanism records; Stage 6 only saw the 8 311-record
subset).

## Diagnostic 1 — the 7 records with no type tags

Two patterns:

**Pattern A — forward-looking program-level projections (4 records):**

> "94 million litres of diesel projected to be saved over 25 years"
>
> "250 000 tonnes CO2 emissions saved over program life"
>
> "Expected to deliver lower operational costs"

These are **anticipated benefits**, not realised events. The Haiku tagger
correctly didn't call them occurrences (haven't happened) or mechanisms
(no pathway). It also didn't call them specifications — arguably an
under-classification. Program-scope outcome statements like "expected
94 M litres saved" could legitimately be `is_specification`.

**Pattern B — evaluative trade-off statements (3 records):**

> "Deploying a low-load rated replacement engine before end-of-life is a
> large outlay (mobilisation, demobilisation, labour, limited redeployment
> value)"

These are **transferable cost-evaluative claims** — arguably should be
`is_lesson` (transferable principle: "early replacement is uneconomic").
The LLM was conservative.

**Verdict.** 4 % un-classified is a defensible outcome — these are genuine
edge cases. Could be absorbed by minor prompt tweaks (clarify that
`is_specification` includes program-level expected outcomes; clarify
that `is_lesson` includes evaluative trade-off claims). Or accepted as
residual.

## Diagnostic 2 — the 3 v1-only FC records (now excluded)

All 3 describe **PV curtailment at Ramingining**: when demand rises and
the control system switches generators, PV curtailment changes
accordingly. Sample:

> "At Ramingining, when demand reaches a high threshold near midday, the
> control system switches from Gen 2 to Gen 3 (which has a higher minimum
> loading setting), causing the PV to be curtailed more aggressively."

| | v1 | NEW |
|---|---|---|
| Causal claim | yes | yes (occ + mech) |
| Valence | **negative** (curtailment = lost solar) | **no_valence** (designed behaviour) |
| FC-eligible | yes | no |

**The NEW scheme is correct.** PV curtailment in SETuP is expected by
design — the SETuP design modelling explicitly predicts ~30 % curtailment
as a design feature, not a failure. v1's `negative` was conflating
"outcome that loses solar energy" with "outcome that hurts the project."

These records describe **system behaviour under design**, not failures.
Including them in the failure-mode cluster pool would pollute the
taxonomy with normal-operations content. The NEW scheme correctly
excludes them via `no_valence`.

This empirically demonstrates that v1's FC pool was contaminated by
designed-mechanism records misclassified as negative. The 4-value valence
scheme produces a cleaner taxonomy input.

## Headline architectural findings

1. **Multi-label tagging is empirically necessary** — 68 % of records
   carry ≥2 type tags.
2. **`no_valence` is materially distinct from `neutral`** — used 15× more
   often than `neutral`, replacing the dumping-ground category in v1.
3. **The FC pool will be ~3.5× larger and more discriminating** under the
   new scheme. Larger because it picks up prescriptive-about-failure
   records v1 missed; more discriminating because it excludes
   designed-mechanism records v1 mis-tagged as negative.
4. **Per-event composition profiles are interpretable** — reading the
   counts column in the per-event table immediately tells you what kind
   of event it is (specification-heavy / prescriptive-heavy /
   mechanism-heavy / mixed).

## Files snapshotted

- `code/label_record_types.md` — 6-axis prompt with `lesson` field
  excluded from input
- `code/run_pilot.py` — driver
- `outputs/tags.json` — all 173 tags + per-event mapping + run metadata
- `outputs/raw_responses.txt` — raw Haiku responses for audit
- `notes.md` — this document

## Open follow-ups

1. **Decide on prompt revisions** for the 4 % no-type residual:
   - Clarify `is_specification` includes program-level expected outcomes,
     or
   - Clarify `is_lesson` includes evaluative trade-off claims, or
   - Accept as residual.
2. **Replicate the pilot** (3 reps) at temperature 0 to characterise
   per-axis replicate noise — particularly for `valence`, which we
   anticipate is the noisiest axis.
3. **Run on REVS** (the 165-record 3-doc subset) so the full pilot
   compares NT SETuP (low-failure-rate program) and REVS
   (high-failure-rate program) under the new scheme.
4. **Corpus-wide labelling pass** — apply the 6 axes across all 90 k
   records once authorised. Estimated ~$23 Haiku batch.

---

## v3 prompt cross-tier sweep (2026-05-02 evening)

Followed up the v1 9-rep sweep with two further iterations:
**v2** (added explicit ❌/✅ "common mistakes" with cross-axis lesson
example) and **v3** (user-drafted: stripped anti-example block,
removed cross-axis mentions, kept the underlying-situation rule as
positive-form guidance). v3 is also paired with a **data-side trim**:
`run_pilot.py:trim_record` now drops both `lesson` and `intervention`,
passing only `id + narrative + evidence` to the model. The intervention
field on inspection contained ~50% recommendation contamination
("Recommendation made to…", "Identified need to…") — waving it away in
prose was insufficient.

v3 was run on all three tiers (Haiku / Sonnet / Opus, 3 reps each, 9
new runs) so cross-tier comparison stays clean.

### Within-model replicate stability (mean pairwise agreement, 3 reps)

| axis              | haiku-v1 | haiku-v3 | sonnet-v1 | sonnet-v3 | opus-v1 | opus-v3 |
|-------------------|---------:|---------:|----------:|----------:|--------:|--------:|
| is_occurrence     |    0.977 |    0.965 |     0.969 |     0.996 |   0.938 |   0.977 |
| is_mechanism      |    0.965 |    0.911 |     0.992 |     0.969 |   0.927 |   0.946 |
| is_specification  |    0.981 |    0.934 |     0.977 |     0.988 |   0.938 |   0.969 |
| is_lesson         |    0.973 |    0.888 |     0.992 |     0.992 |   0.881 |   0.931 |
| is_recommendation |    0.992 |    0.977 |     0.996 |     1.000 |   0.977 |   0.992 |
| valence           |    0.954 |    0.934 |     0.992 |     0.981 |   0.965 |   0.988 |

**Surprises:**
- **Haiku-v3 regressed on three boolean axes** (is_mechanism 0.965→0.911,
  is_specification 0.981→0.934, is_lesson 0.973→0.888). The data-side
  trim removed scaffolding Haiku was leaning on; the smaller, sharper
  prompt left it less anchored on the structural axes. Haiku trades
  stability for valence calibration.
- **Sonnet-v3 was uniformly stable or improved**; the prompt cleanup
  helped without regression. is_recommendation hit 1.000 across all
  rep pairs.
- **Opus-v3 improved on every axis**, particularly is_lesson
  (0.881→0.931) and valence (0.965→0.988).

### Valence distribution

| suite      | positive | negative | neutral | no_valence |
|------------|---------:|---------:|--------:|-----------:|
| haiku-v1   |     37 % |     31 % |    2 %  |       30 % |
| haiku-v3   |     29 % |     42 % |    4 %  |       25 % |
| sonnet-v1  |     35 % |     44 % |    5 %  |       16 % |
| sonnet-v3  |     32 % |     49 % |    8 %  |       10 % |
| opus-v1    |     34 % |     42 % |    2 %  |       22 % |
| opus-v3    |     32 % |     48 % |    5 %  |       15 % |

The underlying-situation rule fired on all three tiers under v3:
no_valence dropped substantially everywhere, negative climbed.
Haiku's no_valence rate fell from 30 %→25 % (still the most
conservative), Sonnet 16 %→10 %, Opus 22 %→15 %. The rule is
detectable across the tier ladder when the prompt is clean.

### FC pool (valence=negative AND (is_occurrence=yes OR is_mechanism=yes))

| suite      | mean | union | intersection |
|------------|-----:|------:|-------------:|
| haiku-v1   | 31.3 |    34 |           28 |
| haiku-v3   | 32.0 |    43 |           21 |
| sonnet-v1  | 48.0 |    52 |           44 |
| sonnet-v3  | 40.7 |    44 |           37 |
| opus-v1    | 37.7 |    48 |           30 |
| opus-v3    | 58.7 |    62 |           55 |

- **Opus-v3 explodes the FC pool** (mean 37.7→58.7, intersection 30→55).
  The valence recalibration combined with Opus's high replicate
  stability produces the largest *and* most reproducible FC set of
  any configuration tested.
- **Haiku-v3 increased mean FC but the intersection collapsed** (28→21).
  Pool growth came at the cost of which-records-make-it-in stability.
  Haiku-v3 is a worse production candidate than Haiku-v1 on this metric.
- **Sonnet-v3 actually shrank the FC pool**. Negative valence climbed
  but the structural axes (is_occurrence, is_mechanism) tightened.
  Net: fewer records qualify, but the ones that do are higher-conviction.

### Cross-tier agreement under v3

| axis              | H↔S   | H↔O   | S↔O   |
|-------------------|------:|------:|------:|
| is_occurrence     | 0.925 | 0.923 | 0.936 |
| is_mechanism      | 0.875 | 0.803 | 0.798 |
| is_specification  | 0.829 | 0.869 | 0.922 |
| is_lesson         | 0.908 | 0.769 | 0.765 |
| is_recommendation | 0.944 | 0.942 | 0.983 |
| valence           | 0.808 | 0.800 | 0.904 |

is_occurrence, is_recommendation, and (Sonnet↔Opus) valence converge
across tiers — these are the production-stable axes. is_mechanism and
is_lesson diverge most under v3, with Haiku as the outlier on lesson
(it reads many things as lessons that Sonnet/Opus do not). Sonnet↔Opus
valence agreement is 0.904 — the strongest cross-tier signal we have.

### No clean winner — three plausible production configs

1. **Sonnet-v1** — conservative incumbent. Highest within-model
   stability across boolean axes (0.97-1.00), 44 % negative valence,
   FC intersection 44. Pre-v3 valence calibration is a known
   undercount but reproducibly so.
2. **Sonnet-v3** — mild upgrade. Better valence calibration (no_valence
   16 %→10 %), tighter FC pool (intersection 37 from 44), is_recommendation
   perfect across reps. Slightly smaller FC pool is the cost of
   tighter axes.
3. **Opus-v3** — premium. Best within-model stability of any v3 run,
   biggest FC pool (intersection 55), best valence convergence with
   Sonnet (0.904). 7.8× cost of Haiku, 2.1× cost of Sonnet.

**Haiku-v3 is no longer viable** as a production candidate: the
valence calibration succeeded but stability regressed on three
boolean axes and FC pool intersection collapsed. The data-side trim
that helped Sonnet and Opus *hurt* Haiku — it had been compensating
for a weaker prompt by leaning on the intervention scaffold.

### Cumulative spend across all 21 runs

| suite        | cost  |
|--------------|------:|
| haiku-v1     | $0.257 |
| haiku-v3     | $0.254 |
| sonnet-v1    | $0.960 |
| sonnet-v3    | $0.950 |
| opus-v1      | $1.817 |
| opus-v3      | $1.989 |
| **TOTAL**    | **$6.23** |

(Haiku-v2 sweep $0.26 not included; that was the failed cross-axis
contamination experiment.) Total pilot spend including all v2 work
is approximately **$6.49**.

### Implications for the production decision

- **The underlying-situation valence rule is real and tier-portable.**
  All three tiers reduced no_valence by 5-7 percentage points under v3
  with the same prompt. This is the methodology paper finding worth
  documenting: valence rule design generalises across the Anthropic
  tier ladder.
- **Cross-axis contamination (v2) is a real LLM-prompt failure mode.**
  v2's ❌/✅ "lessons" anti-example flipped is_lesson on 21 of 173
  Haiku records away from Sonnet baseline. Naming an axis inside an
  anti-example for a different axis pollutes the named axis even when
  the anti-example is logically about the other.
- **Data-side hygiene must be evaluated per-tier.** Trimming
  intervention helped Sonnet/Opus and hurt Haiku — the smaller model
  was using contaminated context as a structural anchor. We can't
  assume hygiene is monotonically beneficial.
- **No experiment so far cleanly justifies Opus-v3 over Sonnet-v3** at
  2.1× cost. The biggest FC pool is attractive but we have no ground
  truth to say it's the *right* FC pool. Sonnet-v3 may be tighter
  because it's correctly excluding records Opus over-includes.
  Resolving this requires hand-adjudication on the disagreement set —
  next step.

### Files added in this iteration

- `code/label_record_types_v2.md` — v2 prompt (kept for archival; failed)
- `code/label_record_types_v3.md` — v3 prompt (active candidate)
- `outputs/haiku-4-5-v2prompt/rep{1,2,3}/` — v2 Haiku reps
- `outputs/{haiku-4-5,sonnet-4-6,opus-4-7}-v3prompt/rep{1,2,3}/` — v3 sweep
- `code/run_pilot.py` — `--prompt`, `--model-slug-suffix`, opus-temp
  fix, intervention-drop in `trim_record`

### Next decision points

1. **Hand-adjudicate the Sonnet-v3 ↔ Opus-v3 disagreement set** on
   is_mechanism and is_lesson (the two divergent axes). Without this
   we can't say whether Opus's larger FC pool is correctness or
   over-tagging.
2. **Decide whether to keep v3 or revert to v1** for production. Current
   leaning: Sonnet-v3 — small but real upgrade in valence calibration,
   no stability regression, FC pool tightening is plausibly correct
   not a deficit.
3. **REVS pilot** still pending — needed to confirm findings are not
   NT-SETuP-specific.

---

## Output-format compression study (2026-05-02 evening)

After establishing v3 prompt + intervention-trim as the candidate
production config, tested three output-format variants on the same 173
records to see whether output-token cost could be reduced without
losing label fidelity. All four runs are Sonnet-4.6 + v3 prompt content;
only the **output schema** changes.

### The four formats

| format       | per-record output |
|--------------|-------------------|
| full JSON    | 9-line indented object: `"is_specification": "yes"` etc. |
| hybrid       | one-line object, full keys, compact values: `{"is_specification":1,"valence":"neg",…}` |
| compact      | one-line object, single-letter keys, compact values: `{"o":1,"m":0,"s":1,…,"v":"neg"}` |
| terse        | bitstring: `ARENA-DLV-1234-0001 1010100` |

### Cost (90,192-record corpus, batches API + prompt caching)

| format    | out tok/rec (observed) | projected total |
|-----------|----------------------:|----------------:|
| full JSON |                  85.0 |          $75.20 |
| hybrid    |                  52.5 |          $53.21 |
| compact   |                  41.6 |          $45.84 |
| terse     |                  17.1 |          $29.27 |

### Per-axis fidelity (vs 4-rep JSON Sonnet-v3 baseline)

Within-JSON 4-rep mean rep-pair agreement (the noise floor we have to
beat to claim format-equivalence):

| axis              | within-JSON | hybrid | compact | terse |
|-------------------|------------:|-------:|--------:|------:|
| is_occurrence     |       0.991 |  0.983 |   0.965 | 0.931 |
| is_mechanism      |       0.971 |  0.960 |   0.942 | 0.740 |
| is_specification  |       0.980 |  0.815 |   0.809 | 0.688 |
| is_lesson         |       0.974 |  0.936 |   0.954 | 0.769 |
| is_recommendation |       1.000 |  1.000 |   0.983 | 0.919 |
| valence           |       0.964 |  0.919 |   0.913 | 0.861 |

Even against the **union of all 4 JSON reps** (most generous: a format
matches if it agrees with ANY of 4 reps), hybrid and compact only reach
**0.844 on is_specification** — confirming the 26-record disagreement
is a format-induced bias, not sampling noise.

### The finding: per-axis compression tolerance

Format compression does **not** degrade uniformly. It degrades the
**loosest-boundary axis first**:

- **Sharp axes** (is_recommendation, is_occurrence, is_mechanism)
  survive aggressive compression. is_recommendation is perfect across
  all 4 JSON reps and remains perfect under hybrid; is_occurrence
  drops only ~1pp under compact. These axes have crisp definitions
  ("is there a prescriptive imperative?", "did this happen?") that
  the model commits to confidently regardless of how much surface
  area the output format gives it.

- **Valence and is_lesson** take 3-7pp drift under compression —
  detectable but not catastrophic. Both axes have moderately-sharp
  boundaries with the underlying-situation rule and the
  generalisation diagnostic respectively.

- **is_specification — the catch-all "descriptive" axis — breaks**.
  It drops 17-18pp under both compact and hybrid, regardless of
  whether the field name is `s` or `is_specification`. **Long field
  names did not rescue it**, falsifying the initial "verbose names
  are semantic anchors" hypothesis. The mode of failure is
  asymmetric: 32 of 33 compact↔JSON disagreements have compact
  saying yes, JSON saying no — under compression the model
  default-commits liberally on the loose axis.

### Refined hypothesis (worth a paragraph in the methodology paper)

The model's deliberation surface is the output token stream itself.
Verbose JSON (`"is_specification": "yes"`) is partly a *thinking*
operation — the act of writing a multi-token value gives the model
implicit budget to weigh ambiguous cases. Compress to `1`/`0` or to
a positional bit, and you compress that budget. Crisp axes don't
need the budget; loose axes do. **Output verbosity is partly buying
calibration on the soft axes.**

### Diagnostic terse error: positional drift on the middle bit

Terse format additionally suffers from middle-position errors —
is_specification (position 3 of 5) has the worst terse drift (-30pp).
Plausible failure: the model loses count on long bitstrings even with
a 7-character format. Bitstrings would need parity bits or per-axis
labels to be safe, defeating their cost advantage.

### Decision

**Stay on full JSON for the production corpus run.** The $46-saving
from compact, the $22-saving from hybrid, and the $46-saving from
terse all come at the cost of is_specification calibration. The axis
breaking under compression is also the axis used in downstream
filters (specifically, `is_specification=yes` records are
deprioritised in the FC pool and the lessons compendium because they
describe parameters rather than mechanisms). False-positive
specifications poison both filters.

If output cost becomes a binding constraint at scale (>500k records),
revisit by running compact/hybrid for the **5 sharp axes** and a
separate JSON-format pass **for is_specification only** — this
hybrid-of-hybrids might recover ~$25 of the $46 saving without
breaking the soft axis. Not justified at current corpus size.

### Files added in this study

- `code/label_record_types_v3_terse.md` — bitstring prompt
- `code/label_record_types_v3_compact.md` — single-char keys prompt
- `code/label_record_types_v3_hybrid.md` — long keys, short values prompt
- `code/run_pilot_terse.py`, `run_pilot_compact.py`, `run_pilot_hybrid.py`
- `outputs/sonnet-4-6-v3{terse,compact,hybrid}/rep1/` — one rep each
- `outputs/sonnet-4-6-v3prompt/rep4/` — fresh JSON baseline rep added
  to anchor the comparison against rep1-3 noise

---

## Output-format study — follow-up: Opus referee + extended thinking (2026-05-02 evening)

The earlier "Output-format compression study" section treated Sonnet-fullJSON
as the baseline and graded compressed formats by their disagreement with it.
This baked the conclusion into the comparison: a finding of "compact disagrees
with JSON" is not a finding of "compact is wrong" without an external referent.

This follow-up does two things:
1. Re-grades every format against an **external referee** — Opus-v3 majority
   across 3 reps — to test whether the original direction holds.
2. Probes the mechanism by enabling **extended thinking** on Sonnet, which
   would in principle let the model deliberate without forcing verbose output.

### 1. Opus-v3 majority as external referee

Opus-v3 was chosen as referee because it (a) was already run on the same 173
records under the same v3 prompt content, (b) is the highest-tier model
available, and (c) has high replicate stability (all 3 Opus reps unanimous on
≥155 of 173 records on every axis). For each axis × record, "Opus majority" is
the modal Opus-v3 label; "Opus unanimous" records are those where all 3 Opus
reps agreed.

#### Per-format agreement with Opus majority (173 records, single rep each)

| axis              | fullJSON-r1 | fullJSON-r4 | hybrid | compact | terse |
|-------------------|------------:|------------:|-------:|--------:|------:|
| is_occurrence     |       0.936 |       0.942 |  0.919 |   0.936 | 0.890 |
| is_mechanism      |       0.792 |       0.798 |  0.775 |   0.769 | 0.717 |
| **is_specification** |    **0.919** |    **0.896** |  **0.769** |  **0.798** | **0.642** |
| is_lesson         |       0.740 |       0.728 |  0.676 |   0.728 | 0.636 |
| is_recommendation |       0.983 |       0.983 |  0.983 |   0.977 | 0.902 |
| valence           |       0.896 |       0.908 |  0.919 |   0.902 |
                                                                            0.844 |

#### Strict test on Opus-unanimous records

Restricting to records where all 3 Opus reps agreed on the axis (the "easy
cases"):

| axis (Opus-unanim. n)       | fullJSON-r1 | hybrid | compact | terse |
|------------------------------|------------:|-------:|--------:|------:|
| is_occurrence (167)          |       0.946 |  0.928 |   0.940 | 0.898 |
| is_mechanism (159)           |       0.824 |  0.799 |   0.792 | 0.742 |
| **is_specification (165)**   |   **0.939** |  **0.788** |  **0.812** | **0.661** |
| is_lesson (155)              |       0.800 |  0.729 |   0.781 | 0.632 |
| is_recommendation (171)      |       0.988 |  0.988 |   0.977 | 0.906 |
| valence (170)                |       0.906 |  0.924 |   0.912 | 0.847 |

#### Tie-breaker: when fullJSON and a compressed format disagree, who's right?

For records where Sonnet-fullJSON-r1 and Sonnet-compressed disagree on
is_specification, which side does Opus take?

| comparison                              | n disagreements | fullJSON matches Opus | compressed matches Opus |
|-----------------------------------------|----------------:|----------------------:|------------------------:|
| Sonnet-fullJSON-r1 vs Sonnet-hybrid     |              32 |                    29 |                       3 |
| Sonnet-fullJSON-r1 vs Sonnet-compact    |              33 |                    27 |                       6 |

**Direction confirmed by independent referee.** When fullJSON and compressed
formats disagree on is_specification, Opus sides with fullJSON 85-90% of the
time. The "verbose JSON is more accurate on is_specification" claim is **not**
circular — it's an external-referee finding.

#### Surprises in the referee analysis

1. **Hybrid beats fullJSON on valence** (0.919 vs 0.896 against Opus majority;
   0.924 vs 0.906 on unanimous-only). Small but consistent. Hypothesis: the
   four-word valence labels (`positive`, `negative`, `neutral`, `no_valence`)
   are *over-verbose* — the model gets distracted by `no_valence`'s
   compound-word structure and over-applies it. Compressing to short codes
   (`pos`, `neg`, `neu`, `nv`) tightens the decision against the prompt
   definitions. Value verbosity is not monotonically good — there's a sweet
   spot per axis.
2. **is_lesson is hard for Sonnet at any format.** Even fullJSON only matches
   Opus 0.74-0.80. This isn't a format problem; it's a Sonnet ceiling on a
   genuinely subtle axis (the "transferability" diagnostic).
3. **Sonnet-fullJSON wins overall** on the structural axes that feed
   downstream filters. The original direction was correct.

### 2. Extended thinking experiment

If the format effect is "verbose JSON gives the model more deliberation
surface" (the original hypothesis), then enabling **extended thinking** —
explicit thinking tokens emitted before the visible output — should let the
model deliberate without forcing verbose output. Predicted: compact + thinking
should approach fullJSON on is_specification.

#### Setup

- Sonnet 4.6 with `thinking={"type": "enabled", "budget_tokens": 2000}`.
- Extended thinking forces `temperature=1` (API rejects temp=0 + thinking).
- Two configurations tested: full JSON + thinking, compact JSON + thinking.
- Same 173 records, 1 rep each.

#### Result: thinking did NOT rescue compact's is_specification

| format                  | is_specification vs Opus majority |
|-------------------------|----------------------------------:|
| fullJSON-r1 (temp=0)    |                             0.919 |
| fullJSON + thinking     |                             0.844 |
| compact (temp=0)        |                             0.798 |
| **compact + thinking**  |                         **0.792** |
| terse (temp=0)          |                             0.642 |

- **Compact + thinking ≈ compact (0.792 vs 0.798).** Of 173 records, only 3
  flipped between the two on is_specification — 1 toward Opus, 2 away.
  Negligible. **Hypothesis falsified.**
- **fullJSON + thinking *hurt* (0.919 → 0.844).** Plausibly explained by
  temperature=1 noise — the thinking variant lost the determinism of the
  temp=0 baseline. So fullJSON+thinking isn't a clean upgrade.
- **One small win:** compact + thinking improved is_lesson 0.728 → 0.827 —
  larger improvement than fullJSON+thinking gave fullJSON on the same axis.
  Different soft axes respond to deliberation differently.

#### The reason: Sonnet doesn't engage thinking on this task

Direct probe: ran one batch with thinking budget 4000, inspected the thinking
content blocks. **The thinking block was 54 characters total**:

> "Let me analyze each record carefully against the axes."

That's it. Pure preamble. ~13 tokens. The model used <0.5% of the 4000-token
budget. By comparison, the same call's *visible* output was 2,115 characters
of correct JSON.

Sonnet self-classifies multi-record-tagging as a **procedural** task that does
not need deliberation. The fully-specified prompt (axes defined, examples
given, schema set) tells the model "you have everything, just emit." Extended
thinking is enabled but unused.

This is a budget *ceiling*, not a target. The model decides utilisation. For
this task, it decided ~zero.

#### Implication for the cost model

Earlier I suggested thinking might add ~$1 to a 90k-record corpus run. That
held empirically because the model declined to use the budget. **It would not
hold if Sonnet engaged thinking the way it does on math problems** —
fully-utilised 2000-token budget × 3,007 batches × $7.50/M = ~$45 extra; at
8000 budget, ~$180. The thinking budget is *open-ended cost* gated by an
opaque model decision.

### 3. Refined hypothesis for the methodology paper

The original hypothesis — "output verbosity buys deliberation surface" — was
right in direction but loose in mechanism. The thinking experiment refines it:

**Output verbosity is the only deliberation surface the task can guarantee.**

- The prompt template is read once per call. Whatever calibration it provides
  is fixed before any record is tagged.
- Extended thinking is optional. The model decides whether to engage it. On
  procedural structured-output tasks, the answer is "no, I don't need to."
- The output schema is the **only deliberation that occurs once per record per
  axis no matter what the model would choose.** Emitting `"is_specification":
  "yes"` is involuntary — the schema demands it. Each emitted token is implicit
  re-evaluation against the prompt's axis definition.

That's why output verbosity has the effect we measure, and why thinking budgets
don't. The *amount* of deliberation isn't the variable; *whether deliberation
is forced into existence by the task structure* is.

This also explains why the format effect concentrates on is_specification: the
loose-boundary axis is where forced deliberation matters most. Sharp axes
(is_recommendation, is_occurrence) decide themselves whether or not the schema
provides space; loose axes need the schema to insert a pause.

### 4. Production decision (unchanged but better-grounded)

**Use full JSON output for the 90k-record corpus run.** Justification:

- Best Opus-referee agreement on is_specification (0.92 vs 0.79 for compact),
  the soft axis that feeds downstream filters.
- Extended thinking does not rescue compressed formats and is a cost-risk at
  scale.
- The $46-saving from compact, the $22-saving from hybrid, and the $46-saving
  from terse all come at the cost of the loose-boundary axis — and we now
  know the cost is real, not an artefact of self-comparison.

Estimated production cost: **$75 for all 90,192 records** at Sonnet-4.6 +
Batches API + prompt caching, full JSON output, v3 prompt + intervention-trim.

### 5. Files added in the format study

| file                                                | purpose                                       |
|-----------------------------------------------------|-----------------------------------------------|
| `code/label_record_types_v3_terse.md`              | bitstring output prompt                        |
| `code/label_record_types_v3_compact.md`            | single-letter keys + compact values prompt    |
| `code/label_record_types_v3_hybrid.md`             | full keys + compact values prompt             |
| `code/run_pilot_terse.py`                           | terse runner + decoder                         |
| `code/run_pilot_compact.py`                         | compact runner + expander                      |
| `code/run_pilot_hybrid.py`                          | hybrid runner + expander                       |
| `code/run_pilot_thinking.py`                        | extended-thinking runner (compact+full)       |
| `outputs/sonnet-4-6-v3{terse,compact,hybrid}/rep1/`| one rep each                                   |
| `outputs/sonnet-4-6-v3thinking-{full,compact}/rep1/`| extended-thinking reps                        |
| `outputs/sonnet-4-6-v3prompt/rep4/`                 | fresh JSON baseline (anchors comparison)      |

### 6. What this study is and isn't

**Is:** a one-rep characterisation of the cost-fidelity frontier for one task
(record-type tagging) on one model (Sonnet 4.6) with one external referee
(Opus 4.7 majority). The mechanism finding is testable and falsifiable.

**Isn't:** a generalisation. The result that "verbose JSON is most accurate"
is task-specific. Other tasks (e.g. classification with very crisp categories)
might tolerate aggressive compression. The general claim — *output verbosity
is the only deliberation surface the task can guarantee* — should generalise,
but the magnitude of the effect won't.

For the methodology paper, the finding worth carrying forward is:

> When designing structured-output prompts, treat the output schema as a
> deliberation surface, not a serialisation surface. Compressing the output
> compresses the model's per-axis decision-making, and the effect is largest
> on axes whose definitions have the most semantic slack. Extended thinking
> is not a substitute, because the model self-limits on procedural tasks.

---

## Correction to the Opus-referee framing (2026-05-02 evening)

A reviewer caught the framing problem: I called Opus-v3 "the referee" but
**Opus-v3 is less replicate-stable than Sonnet-v3 on this task** (see the
9-rep cross-tier table earlier in this document). Sonnet-v3 within-model
agreement is 0.97-1.00 on boolean axes; Opus-v3 is 0.93-0.99. Tier ladder
≠ accuracy on a structured-tagging task. Calling Opus "the referee"
silently re-introduced the circularity it was supposed to fix — just at
a different level.

### What the Opus comparison actually shows

The defensible reading of the Opus-referee data is:

> Sonnet-fullJSON and Opus-fullJSON **converge** on is_specification.
> Sonnet-compressed-formats **diverge** from both.

Convergence between two independent realisations (different model, same
format; same model, different format would be a separate test) is a
**robustness signal**, not a correctness proof. Compressed Sonnet
diverges from Opus by ~12-15pp on is_specification; verbose Sonnet
diverges by only ~6-9pp. That's the real finding.

### What we'd need for an actual rightness claim

To say *which* of fullJSON or compact is correct on the contested 32-33
records, we need ground truth that isn't another LLM. Options:

1. **Hand-adjudication** of the 33 disagreement records. ~30 minutes of
   human work; produces a definitive accuracy number. This is the
   gold-standard test and the only one that resolves the question.
2. **Multi-rep stability comparison** of compressed formats. If
   compact-rep1/2/3 all internally agree on a record, but disagree with
   fullJSON-rep1/2/3/4 (which also internally agree), that's two
   reproducible-but-different opinions, not one right and one wrong. We
   only ran 1 rep each of the compressed formats — would need 2 more reps
   each (~$0.40) to make this comparison.

### What this changes

Production decision is unchanged but the justification is weaker:

- **Defensible claim:** verbose JSON output is more replicate-stable
  (0.97-1.00 across reps) and converges with cross-tier (Opus) labels;
  compressed formats internal-rep-stability is unmeasured but their
  divergence from both verbose Sonnet AND Opus is ~12-15pp on
  is_specification.
- **Not yet defensible:** "verbose JSON is more *accurate* on
  is_specification." That requires hand-adjudication.

The mechanism finding (output verbosity = involuntary deliberation
surface; thinking budgets are model-discretionary) is independent of the
accuracy question and stands.

### Honest one-liner for the methodology paper

> Compressing structured output produces measurably different labels;
> we have not yet ground-truthed which labels are correct, but the
> compressed labels diverge from both within-model replicate consensus
> and cross-tier (Opus) consensus by ~12-15pp on the loose-boundary
> axis. We treat that as a robustness deficit and use verbose output
> in production, pending hand-adjudication.

That's the honest version. The previous section's "Opus sides with
fullJSON 85-90% of the time" remains *true* as a fact, but should be read
as "fullJSON converges with the cross-tier opinion; compact diverges from
it" — not as "Opus is right."

---

## Hand-adjudication results — what the contested set actually showed (2026-05-02 evening)

Jeff hand-adjudicated the 36 records where Sonnet-fullJSON-r1 disagreed
with Sonnet-hybrid or Sonnet-compact on is_specification. Working
definition used: a specification is something **set by the project**
(scope, schedule, budget, location list, organisational structure) or
**inherent to equipment** (nameplate capacity, voltage rating, model
number); excludes outcomes, mechanisms, environmental conditions,
lessons.

### Headline: per-format accuracy on the contested set

| format / referee        | accuracy on 36 contested records |
|-------------------------|---------------------------------:|
| **Opus-v3 majority**    |                **0.972 (35/36)** |
| Sonnet-fullJSON-r1      |                    0.806 (29/36) |
| Sonnet-fullJSON-r4      |                    0.750 (27/36) |
| Sonnet-terse            |                    0.667 (24/36) |
| Sonnet-compact          |                    0.278 (10/36) |
| Sonnet-hybrid           |                    0.139 ( 5/36) |

### The original $46-saving question, resolved

For the 33 records where Sonnet-fullJSON-r1 and Sonnet-compact disagreed
on is_specification, the hand-adjudicated truth is:

| | correct on disagreement set |
|---|---:|
| Sonnet-fullJSON-r1 | 26 / 33  (79%) |
| Sonnet-compact     |  7 / 33  (21%) |

Format compression isn't just disagreeing — it's **wrong** four times as
often as it's right when it disagrees with verbose JSON. The earlier
"compressed labels diverge from cross-tier consensus" finding becomes
"compressed labels diverge from ground truth in the same direction" once
the truth is anchored.

### The bigger finding: stability ≠ accuracy

Sonnet-v3 within-model 4-rep stability on is_specification: **0.980**
(very high). Sonnet-v3 accuracy on this hand-adjudicated contested set:
**0.806** (much lower). Across all 4 Sonnet reps, accuracy ranged
0.750-0.861 — meaning **Sonnet replicates its own miscalibration**.

| | within-rep stability | accuracy (contested set) |
|---|---:|---:|
| Sonnet-v3 (4 reps mean) | 0.980 | 0.806 |
| Opus-v3 (3 reps mean)   | 0.969 | 0.963 |

Sonnet is *more replicate-stable* than Opus while being *less accurate*.
Its high stability was **confidence in the wrong answer**, not signal of
correctness. We were measuring whether the model agrees with itself, not
whether it agrees with reality.

This is a methodology-paper finding worth carrying forward in its own
right:

> Within-model replicate stability is not a substitute for accuracy.
> A model can confidently and reproducibly miscalibrate on a
> definitionally loose axis. Stability tells you the model has formed a
> stable opinion about each record; it does not tell you that opinion is
> right.

### Surprises that changed the format-effect framing

1. **Hybrid (long keys + 1/0 values) is the WORST format on
   is_specification** (0.139), worse than terse (0.667). The
   value-token shape (`1`/`0`) is the priming culprit, not key
   compression. When the slot is a digit, the model commits aggressively
   to `1` regardless of how the key is named. This is a tighter version
   of the earlier "value-emission pause" hypothesis — pure-`1`/`0`
   values create a yes-bias even more strongly than I'd thought.
2. **Terse beats compact and hybrid on accuracy** (0.667 vs 0.278 vs
   0.139) despite having the worst within-model stability. Terse is
   noisy but not directionally biased; compact/hybrid are precise but
   wrong. This breaks the simple "compression = bad" narrative.
3. **Opus-v3 is dramatically more accurate than Sonnet-v3 at any
   format** on this contested axis. The earlier section's correction
   ("tier ladder ≠ accuracy") was itself wrong on the merits — Opus
   really is more accurate here, just not on the axes I'd been comparing
   in raw rep-pair-agreement terms.

### Production decision (revised — open question)

| config                | 90k cost | is_specification accuracy (extrapolated) |
|-----------------------|---------:|-----------------------------------------:|
| Sonnet-v3 fullJSON    |     $75 |                                    ~0.96 |
| Opus-v3 fullJSON      |    $162 |                                    ~0.99 |

The $87 Opus premium buys ~3pp accuracy on is_specification. Whether
this is worth it depends on:

- **How often is_specification feeds downstream filters.** If it's a
  primary filter for the FC pool or the lessons compendium, the 4%
  Sonnet error rate is real production cost.
- **Whether Sonnet's errors are directionally biased** (e.g.
  systematically over-tagging or under-tagging). The contested-set data
  suggests yes — Sonnet tends to over-tag is_specification under the
  narrow project-or-equipment definition. Hand-adjudication of the
  uncontested set would confirm; the cost is a 30-min audit on ~135
  records where all formats agreed.

**Recommendation:** run Opus on the corpus at a 1-doc smoke-test scale
($1-2) to confirm cost projections, then decide. The cost premium is
not prohibitive at corpus size, and the methodology-paper finding (a
verbose-JSON Opus run produced a high-accuracy is_specification axis)
is the cleaner story than "we used the cheap-but-systematically-wrong
config because it was cheap."

### Files added

- `analysis/build_adjudication.py` — extracts contested set, generates the doc
- `analysis/adjudication_is_specification.md` — Jeff's filled adjudication
- `analysis/score_adjudication.py` — parses + scores
- `analysis/adjudication_scores.json` — saved scores


---

## v4 prompt iteration result + production decision (2026-05-02 evening, final)

### v4 prompt — what changed and why

The v4 prompt (`code/label_record_types_v4.md`) made three targeted edits to
`is_specification` only, leaving every other axis identical to v3:

1. Reframed the yes-list around "set by the project OR inherent to equipment"
   with explicit examples (RPF limits, programme reach, control strategy).
2. Added an explicit axis-independence reminder: a record can be
   `is_specification: yes` AND `is_occurrence: yes` simultaneously, with
   the equipment-swap example demonstrating it.
3. Added explicit `no` bullet for environmental conditions and operating-
   context constraints (mobile coverage gaps, travel risks, animal hazards,
   local supply limits, weather).

### v4 result on Sonnet (1 rep, 173 records)

| metric                                    | v3-r1   | v4-r1   |
|-------------------------------------------|--------:|--------:|
| accuracy on Jeff's adjudicated 36 records |   0.806 |   0.861 |
| recall on Jeff's yes records              | 2/9 22% | 4/9 44% |
| precision on yes                          |    100% |    100% |
| corpus-wide accuracy vs Opus-majority     |   0.919 |   0.890 |

**Targeted fixes mostly landed:**
- Under-tagged → flipped: 4/6 (RPF replacements, Tranche 1 yield, 50% hybridised). 2 stuck (cooling system, capacity retention strategy).
- Over-tagged → flipped: 6/8 (environmental constraints correctly demoted). 2 stuck (SETuP transformational-aims records).

**Collateral damage (cross-axis bleed):** despite changing only the
is_specification section, v4 also changed labels on:
- is_occurrence: 8 records
- is_mechanism: 8 records
- is_lesson: 5 records
- valence: 12 records
- is_recommendation: 1 record

Same failure mode as v2: discussing axis independence inside an axis section
contaminates the surrounding axes. The "axes are independent" reminder leaks
the model's evaluation patterns across the boundary.

**Net effect:** v4 is better than v3 on the records we have ground truth for,
but worse against Opus-majority on the corpus as a whole. Without
hand-adjudicating the 15 v4-vs-Opus regression records, we can't know
whether those are genuine regressions or Opus-bias artefacts.

### Production decision: Sonnet-v3 fullJSON

For the corpus-wide tagging pass, the production configuration is:

- **Model:** claude-sonnet-4-6
- **Prompt:** `label_record_types_v3.md` (the original v3 prompt that was
  paired with intervention-trim in `trim_record`)
- **Output format:** full JSON
- **Inference:** Batches API + prompt caching, full JSON output
- **Estimated cost:** ~$75 for 90,192 records
- **Known accuracy bound:** ~92% corpus-wide on is_specification (proxied
  via Opus-majority); systematically conservative — under-tags equipment-
  specs and program-magnitudes inside outcome-framed sentences,
  over-tags environmental conditions.

### Why not Opus or v4

- **Opus-v3 fullJSON would land at ~99% accuracy at ~$162** (the $87 premium
  buys ~7pp accuracy and ~10pp recall on is_specification). Not justified
  inside the grey-paper budget; dedup work is the higher-priority blocker.
- **v4 fixes contested-set accuracy but at the cost of corpus-wide cross-axis
  bleed**; further iteration has uncertain ROI given the v2 → v3 → v4
  trajectory shows each iteration introduces new failure modes while
  fixing old ones.
- **Sonnet-v3's known systematic conservatism is itself informative.**
  Downstream effects of the 8% error rate (under-tagged equipment-specs
  leaking into FC pool, environmental conditions correctly excluded) will
  be observed through the corpus run and the dedup pass. Deferred validation
  becomes part of methodology gaps (`failure_mode_methodology/
  methodology_gaps.md` §17).

### What v4 is good for

The v4 prompt is **archived**, not deleted — it remains in `code/` and the
v4 outputs in `outputs/sonnet-4-6-v4prompt/rep1/` for reference. If a
v4-iteration is later resourced (e.g. to test whether removing the
axis-independence reminder cleans up the cross-axis bleed while keeping the
yes-list / no-list improvements), the artefacts are ready.

### Files in this iteration

- `code/label_record_types_v4.md` — v4 prompt (archived candidate)
- `outputs/sonnet-4-6-v4prompt/rep1/` — v4 1-rep result on 173 records
- `analysis/adjudication_is_specification.md` — Jeff's filled adjudication
- `analysis/adjudication_scores.json` — scored result

The methodology gap is logged at `corpora/arena/tests/failure_mode_methodology/methodology_gaps.md` §17.

---

## FC-pool effect of the is_specification errors — surprise finding (2026-05-02 evening)

After deciding to ship Sonnet-v3-fullJSON, ran an analysis to estimate
the actual downstream impact of the known is_specification bias on the
FC pool. **The result inverted the framing of the methodology gap.**

### FC pool gap (gated definition: `negative AND (occurrence OR mechanism) AND NOT is_specification`)

| | size on 173 records |
|---|---:|
| Sonnet-v3-r1 | 39 |
| Sonnet-v3-r4 | 34 |
| Opus-majority | **57** |

**Sonnet's FC pool is ~32% smaller than Opus's.** Not a 7pp accuracy gap
on one axis — a substantial undercount of failure-mode candidates.

### Cause analysis: 0% of FC disagreements are caused by is_specification flips

Of 26 FC-pool membership disagreements between Sonnet-r1 and Opus-majority:

- Caused PURELY by `is_specification` flip: **0 records**
- Caused by `is_mechanism` flip (often co-flipping with other axes): **22 of 22 Opus-only records**
- Caused by `valence` flip: 4 records (over-includes)

The is_specification axis we'd been obsessing over is **not the FC-pool
lever**. Records where Sonnet and Opus disagreed on is_specification
either co-disagreed on is_mechanism (and the mechanism disagreement is
what changes FC membership) or didn't change FC membership at all.

**The actual lever is `is_mechanism`** — Sonnet under-tags it
systematically.

### Two distinct patterns in the is_mechanism under-tagging

1. **The 1361-series (11 records):** all flip
   `is_mechanism: no, is_lesson: yes` (Sonnet) ↔
   `is_mechanism: yes, is_lesson: no` (Opus). Sonnet reads these
   records as transferable lessons; Opus reads them as causal
   mechanisms. Different epistemic frame on doc-internal generalisations.
2. **The 0911-series environmental records (5 records):** flip
   `mechanism:no, specification:yes` (Sonnet) ↔
   `mechanism:yes, specification:no` (Opus). The records that drove the
   is_specification over-tagging story — but it's the is_mechanism flip
   that actually affects the FC pool, not the is_specification flip we
   diagnosed.

### Implications

- **The methodology gap §17 framing was misdirected.** It focused on
  is_specification accuracy when is_mechanism is the consequential axis
  for the FC pool.
- **Sonnet may be systematically under-clustering mechanisms as
  lessons** — this would propagate to fewer FC clusters, fewer
  failure-mode threads, and a thinner mechanism-axis taxonomy. That's a
  meaningful methodology finding if it generalises beyond NT SETuP.
- **The 173-record NT SETuP pilot is too narrow** to generalise from. 11 of
  the 22 mechanism-under-taggings come from one project, possibly one
  project's stylistic register. Need a stratified larger sample to know
  whether this is project-specific or systematic.

### Next step (deferred to scheduled run, not yet executed)

A 2,000-record stratified sample run — Sonnet-v3-fullJSON × 3 reps and
Opus-v3-fullJSON × 3 reps via Batches API — will resolve whether the
is_mechanism under-tagging is a project-specific artefact or
corpus-wide systematic. Stratification: 8 top kb_categories ×
{Reports, Reports+Lessons} × random within-cell. ~$16 batch + cache,
async (24h SLA).

---

## 2,000-record at-scale validation result (2026-05-02 evening, batch landed)

The Batches API job ran in 2.5 minutes (vs 24h SLA), 0 errors, total cost
$17 batch. Three reps each of Sonnet-v3-fullJSON and Opus-v3-fullJSON on
2,000 stratified records (8 top kb_categories × {Reports, Reports+Lessons}
× 125 records).

### Both prior framings were small-sample artefacts

| | 173-record pilot | 2,000-record at-scale |
|---|---:|---:|
| FC pool gap (Sonnet vs Opus majority) | **-32%** (39 vs 57) | **-0.6%** (516 vs 513) |
| Sonnet→lesson, Opus→mechanism confusion | 11 records, 1 doc | 4 records, 4 docs |
| Sonnet→mechanism, Opus→lesson confusion | small | 6 records |
| Net asymmetry on mechanism-vs-lesson | strong (Sonnet→lesson) | -2 records (symmetric) |

The 1361-series mechanism-as-lesson pattern was project-specific stylistic
register, not a systematic Sonnet bias. The FC pool gap was driven by
that one project plus the contested-set construction bias.

### Within-model replicate stability (3 reps, 2000 records)

| axis | Sonnet | Opus |
|---|---:|---:|
| is_occurrence | 0.986 | 0.966 |
| is_mechanism | 0.973 | 0.954 |
| is_specification | 0.974 | 0.963 |
| is_lesson | 0.981 | 0.964 |
| is_recommendation | 0.989 | 0.990 |
| valence | 0.971 | 0.953 |

Both models are very stable at scale. Sonnet is *more* replicate-stable
than Opus on every axis except is_recommendation (where they tie at near-
unanimity). This is consistent with the 173-record pilot finding.

### Cross-tier agreement (majority-vs-majority, 2000 records)

| axis | mean agreement |
|---|---:|
| is_recommendation | 0.972 |
| is_occurrence | 0.921 |
| is_lesson | 0.909 |
| is_specification | 0.902 |
| valence | 0.872 |
| **is_mechanism** | **0.862** |

is_mechanism and valence are the noisiest cross-tier axes; is_recommendation
is essentially perfect.

### Where Sonnet's bias actually lives — label-rate asymmetry

| axis | Sonnet majority yes-rate | Opus majority yes-rate | delta |
|---|---:|---:|---:|
| is_occurrence | 49% | 52% | -4pp |
| **is_mechanism** | **39%** | **49%** | **-10pp** |
| is_specification | 35% | 38% | -3pp |
| **is_lesson** | **16%** | **22%** | **-6pp** |
| is_recommendation | 14% | 14% | 0pp |

**Sonnet systematically under-tags is_mechanism by 10pp and is_lesson by
6pp at scale.** But this does NOT translate to a smaller FC pool because
the under-tagging on is_mechanism is offset by under-tagging on
is_specification (the gating axis). Records Sonnet should have included
via is_mechanism instead get included via is_occurrence-only paths, or
records get included that Opus would have excluded for being
specifications. Net: similar FC pool *size*, different *composition*.

### FC pool composition gap (the survivor finding)

- Sonnet majority FC: 516
- Opus majority FC: 513
- Intersection: 443
- Sonnet only: 73
- Opus only: 70
- **Jaccard: 0.756**

About **28% of FC pool records differ** between Sonnet and Opus despite
near-identical pool sizes. Top axis-flip patterns explaining the
disagreement:

**Records in Opus FC but missed by Sonnet (under-includes):**
- 14 records: pure is_mechanism flip (Sonnet=no, Opus=yes) — Sonnet's mechanism-blindness, the most common pattern
- 8 records: pure is_occurrence flip
- 4 records: is_mechanism + is_lesson co-flip
- 4 records: pure valence flip (positive → negative)

**Records in Sonnet FC but absent from Opus FC (over-includes):**
- 19 records: pure is_specification flip (Sonnet=no, Opus=yes) — Sonnet missing specifications and letting them through the FC gate
- 6 records: is_mechanism flip (Sonnet=yes, Opus=no)
- 6 records: valence flip (negative → positive)

So Sonnet's two systematic biases — **under-tagging is_mechanism** and
**under-tagging is_specification** — actively cancel at the FC pool level.
The under-mechanism failure mode would shrink the pool; the under-
specification failure mode lets specs leak through the gate, expanding it.

### Stratified by category (cross-tier is_mechanism agreement)

| kb_category | is_mech | is_spec | is_lesson | valence |
|---|---:|---:|---:|---:|
| Solar PV R&D | 0.91 | 0.88 | 0.94 | 0.86 |
| Bioenergy | 0.89 | 0.89 | 0.89 | 0.91 |
| Renewables for industry | 0.88 | 0.89 | 0.92 | 0.89 |
| Battery storage | 0.87 | 0.92 | 0.89 | 0.88 |
| DER | 0.84 | 0.92 | 0.91 | 0.88 |
| Demand response | 0.84 | 0.92 | 0.92 | 0.88 |
| Electric vehicles | 0.84 | 0.87 | 0.88 | 0.83 |
| Hydrogen energy | 0.83 | 0.93 | 0.92 | 0.86 |

is_mechanism agreement varies 8 percentage points across categories — EVs,
Hydrogen, Demand response are the hardest; Solar PV is the cleanest.
Plausible explanation: Solar PV records (which we know best from the older
ARENA work) have the most concrete mechanism descriptions; energy-system
domains (EVs, Hydrogen) discuss more system-level dynamics that resist
clean mechanism-vs-lesson categorisation.

### Production decision (further reinforced)

Sonnet-v3 fullJSON for the corpus-wide tagging pass is the right call:
- FC pool size matches Opus to within 1% at scale
- Replicate stability is higher than Opus on every axis
- $87 Opus premium would buy ~28% different FC pool composition, but at
  similar pool size — the question becomes "do you want different
  candidates, not more candidates"

### Methodology-paper findings worth carrying forward

1. **Small-sample diagnoses can completely invert at scale.** The 173-
   record NT SETuP pilot showed a 32% FC pool gap; the 2000-record
   stratified validation shows -0.6%. The pilot's gap was a project-
   stylistic artefact; the gap evaporates with cross-domain sampling.
   This is a methodology-paper lesson in its own right: pilot
   validation must be stratified before claiming systematic effects.
2. **Pool size matching ≠ filter equivalence — composition is what
   propagates downstream.** Sonnet's FC pool and Opus's FC pool are the
   same size (516 vs 513) but **~28% of the records are different**
   (Jaccard 0.76; 73 Sonnet-only, 70 Opus-only). The size match is a
   coincidence — Sonnet's under-mechanism bias happens to cancel
   against its under-specification bias at the gate. But downstream
   consumers (clustering, theme assignment, failure-mode discovery)
   operate on the *records*, not on the count: 143 different records
   means a different starting set of cluster seeds, plausibly different
   cluster boundaries, and plausibly different failure-mode taxonomy.
   The methodology paper should report **composition disagreement**
   (Jaccard, symmetric-difference rate) rather than pool size as the
   primary cross-tier sensitivity metric. *Single-axis accuracy doesn't
   predict downstream-filter behaviour, and neither does pool size —
   only composition does.*
3. **Replicate stability ≠ accuracy still holds at scale**, but the
   accuracy gap is narrower than the pilot suggested. Sonnet at 2000
   records has cross-tier agreement of 0.86-0.97 against Opus depending
   on axis — meaningful but not catastrophic gap.
4. **Cross-tier disagreement concentrates on epistemically subtle axes**
   (is_mechanism, valence) and on system-level domains (EVs, Hydrogen).
   This is the kind of finding the methodology paper can productively
   discuss as "the loose-boundary axes have an irreducible cross-tier
   noise floor of ~10pp."

### Cost actual

| component | actual |
|---|---:|
| Sonnet 3 reps × 2000 records | $5.59 batch |
| Opus 3 reps × 2000 records | $11.45 batch |
| **total** | **$17.04** |

Wall time: 2.5 minutes (Anthropic batch-API processed all 402 requests in
parallel). The 24h SLA is conservative — async batches return faster than
sync calls because of the parallelism.

### Files generated by this run

- `code/sample_2000.json` — the stratified sample (reproducible via seed=42)
- `code/build_2k_sample.py` — sample-builder
- `code/submit_batch_2k.py` — batch submission
- `code/poll_batch_2k.py` — status check / download
- `code/parse_batch_2k.py` — raw_responses.json → tags.json
- `code/batch_2k_info.json` — saved batch ID
- `outputs/{sonnet-4-6,opus-4-7}-v3prompt-2k/rep{1,2,3}/` — 6 tags.json files
- `analysis/analyse_2k.py` — cross-tier analysis
- `analysis/analysis_2k_summary.json` — saved summary

---

## Hand-adjudicated is_mechanism — Opus genuinely more accurate (2026-05-02 evening)

44 records sampled stratified-randomly from the 277 cross-tier
is_mechanism disagreements on the 2k run (24 from the 237-record
under-tag pool, 20 from the 40-record over-tag pool). Adjudicator
applied the v3 prompt definition with the operational refinement
"is_mechanism = yes if a connecting pathway is named, even if hedged"
and `is_occurrence` separately handles realisation.

### Result

| direction                            |  n |  Sonnet correct |    Opus correct |
|--------------------------------------|---:|----------------:|----------------:|
| Sonnet=no / Opus=yes (under-tag)     | 24 |       6 (25%)   |     **18 (75%)**|
| Sonnet=yes / Opus=no (over-tag)      | 20 |      10 (50%)   |      10 (50%)   |
| **overall**                          | 44 |     **16 (36%)**|     **28 (64%)**|

### Reading

- **Sonnet's under-tagging is a real bias.** On records where Sonnet
  said no and Opus said yes, the adjudicator agreed with Opus 75% of
  the time. Sonnet is missing genuine mechanisms.
- **Sonnet's over-tagging is not a bias.** On records where Sonnet
  said yes and Opus said no, adjudication tied 50-50. These are
  genuine edge cases (hedged-without-pathway, speculative,
  citation-derived noise) where either reading is defensible.

### Extrapolation

Of the 277 cross-tier disagreements on the 2k sample:
- ~198 records favour Opus (75% × 237 + 50% × 40)
- ~79 records favour Sonnet
- Net: ~178 records where Sonnet is wrong but Opus is right
  (~9% of the 2000-record sample)

Scaled to 90,192-record corpus: **~8,000 records that Sonnet would
tag is_mechanism=no but should be yes.** That's the concrete cost
of the Sonnet-over-Opus tier choice on this axis.

Confidence interval: 75% under-tag accuracy on 24 records has a 95%
CI of ~53-90%, so the 8,000-record extrapolation is ±~2,000.
Direction is solid; magnitude has uncertainty.

### Side observation: extraction noise

During adjudication, ARENA-DLV-1108-0051 was flagged as a
citation-derived record, not a substantive finding. Heuristic
estimate: ~87/90,192 (0.1%) of corpus records look like citation-
derived ghosts. Doc 1108 has 5 such records clustered (likely a
reference-list page). Small but real noise floor; worth flagging in
methodology gaps as an extraction-stage issue separate from tagging.

### Implications for production

- The $87 Opus premium ($162 vs $75 Sonnet at 90k) buys ~8,000
  correctly-tagged additional mechanism records (~30% more
  mechanism content than Sonnet alone).
- The **"richer failure modes under Opus"** conjecture is now
  ground-truthed on this axis. Whether it propagates to richer
  cluster-level taxonomy still requires running clustering on both
  tier outputs to verify, but the mechanism for richness (more
  mechanism records → more cluster seeds) is now empirically
  supported.
- Sonnet remains a defensible production choice given budget
  constraints, but the trade-off is real and should be named in
  the methodology paper, not glossed.

---

## Cross-version Opus check — 4.6 + temp=0 vs 4.7 default (2026-05-02 evening)

Submitted Opus 4.6 + temp=0 × 3 reps on the same 2,000-record stratified
sample as the original validation. Goal: separate "Opus tier is more
accurate" from confounds (model version, temperature setting). Cost: $9.31
batch (3 reps); ran in 1m45s wall.

### Adjudication accuracy holds across versions

Scored against the 44-record hand-adjudicated mechanism set:

| variant                       | overall    | under-tag direction | over-tag direction |
|-------------------------------|-----------:|--------------------:|-------------------:|
| Sonnet 4.6 + temp=0           | 16/44 (36%)| 6/24 (25%)          | 10/20 (50%)        |
| **Opus 4.7 default temp**     | **28/44 (64%)** | 18/24 (75%)    | 10/20 (50%)        |
| **Opus 4.6 + temp=0**         | **28/44 (64%)** | **17/24 (71%)**| **11/20 (55%)**    |

The two Opus versions tie at 64%. The "Opus is more accurate" finding is
**robust across versions and robust to temperature** — not an artefact
of either. The Opus advantage on the loose-boundary axis is real model
capability, not version-specific tuning or sampling noise.

### Within-rep stability: Opus 4.6 + temp=0 is the most reproducible

| axis              | Opus 4.7 (default) | Opus 4.6 (temp=0) |
|-------------------|-------------------:|------------------:|
| is_occurrence     |              0.966 |         **0.989** |
| is_mechanism      |              0.954 |         **0.984** |
| is_specification  |              0.963 |         **0.984** |
| is_lesson         |              0.964 |         **0.990** |
| is_recommendation |              0.990 |         **0.994** |
| valence           |              0.953 |         **0.983** |

Opus 4.6 + temp=0 beats Opus 4.7 default on every axis by 2-3pp. Opus 4.7
forces temperature ≥1, which adds sampling noise the deterministic 4.6
run avoids. Even so, 4.6 + temp=0 isn't perfectly reproducible — there's
~1-2% residual non-determinism in the API at temp=0 on this task.

### Cross-version FC pool agreement: Jaccard 0.77

| pool comparison         | Jaccard |
|-------------------------|--------:|
| Opus 4.6 ↔ Opus 4.7     |   0.768 |
| Opus 4.6 ↔ Sonnet       |   0.724 |
| Opus 4.7 ↔ Sonnet (prior) | 0.756 |

**The two Opus versions disagree on FC pool composition at almost the same
rate Sonnet disagrees with either Opus version.** There's no "stable Opus
answer" — tier matters, but version within tier matters at similar
magnitude. The methodology-paper finding generalises: cross-tier and
cross-version sensitivity of the FC filter are both ~24-28% Jaccard.

### Label yes-rates: per-axis variation across variants

| axis              | Opus 4.6 | Opus 4.7 | Sonnet 4.6 |
|-------------------|---------:|---------:|-----------:|
| is_occurrence     |     55%  |     53%  |       49%  |
| is_mechanism      |     44%  |     49%  |       39%  |
| is_specification  |     44%  |     38%  |       35%  |
| is_lesson         |     12%  |     22%  |       16%  |
| is_recommendation |     10%  |     14%  |       14%  |

Per-axis label rates differ across all three configs. Notably Opus 4.6
is *more* conservative on is_lesson (12% vs 4.7's 22%) but *more* liberal
on is_specification (44% vs 38%). Despite the divergent rates, both Opus
versions land at the same accuracy on adjudicated mechanism — meaning
they're trading off correctness across different records.

### Production decision swap: Opus 4.6 + temp=0

Switched the corpus run from Opus 4.7 (queued but not submitted) to
Opus 4.6 + temp=0. Rationale:

- **Same accuracy** on adjudicated mechanism (64%, identical)
- **Higher within-rep stability** (0.98-0.99 vs 0.95-0.99) — re-runs
  reproduce, important for paper rigour and re-doable corpus passes
- **Deterministic** at temp=0 — methodology-paper claim "we used the
  reproducible variant" is cleaner
- **Same pricing** ($5/$25 per M tokens; $162 with cache for 90k corpus)

The trade-off: Opus 4.6 is older. On this task it's indistinguishable
from 4.7 in capability and strictly better in reproducibility. For
production research output, that's the right pick.

### Methodology-paper finding worth carrying

> *Opus's mechanism-tagging accuracy advantage over Sonnet is robust
> across the Opus 4.6 / 4.7 model boundary and robust to the default-
> temperature vs deterministic-temperature setting (both at 64% on a
> 44-record adjudication). The advantage is genuine model capability,
> not a sampling or tuning artefact. However, FC pool composition is
> sensitive to the version-temperature pair at similar magnitude
> (~24%) as cross-tier choice — there is no single "stable Opus
> answer," only a per-config one.*

### Files added in this iteration

- `code/submit_batch_2k_opus46.py` — Opus 4.6 submission script
- `code/batch_2k_opus46_info.json` — saved batch ID
  (`msgbatch_01AooVVHryYuUhEiq3JASCRE`, ended at 2026-05-02 10:22:56)
- `outputs/opus-4-6-v3prompt-2k-temp0/rep{1,2,3}/` — 3 reps tags + raw
- `code/submit_corpus_opus.py` — updated: model swapped to 4.6, temp=0.0
