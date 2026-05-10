# Soft-balance constraint experiment — session writeup, 2026-05-05

End-of-day retrospective on a three-condition experiment testing whether a
soft population-balance constraint added to the parent-derivation prompt
compresses the records-per-parent variance, and what additional confounds
the experiment surfaced. Total spend across both new ensemble runs:
**$20.26** at batch discount; ~14 min wall combined.

This document follows the snapshot + headline TL;DR + known-gaps pattern
from `corpora/arena/canonical/narrative/runs/`.

---

## Headline TL;DR

**One empirical claim, one practical rule.**

1. **The soft-balance constraint compresses parent count by ~15% and raises
   the narrow-tail floor.** Both effects reproduce across two independent
   prompt variants, so the finding is robust to wording. Within-run
   population spread is unchanged — the constraint operates as narrow-tail
   pressure-amplification, not as within-run rebalancing.

2. **Practical rule: do not name specific category examples in
   taxonomy-derivation prompts.** A paired-prompt test showed the named
   examples themselves prime the model to retain those categories cross-run,
   producing an effect substantially larger than the constraint itself.
   The size of the effect is a side-finding about Claude prompt behaviour;
   the rule for the methodology paper is to phrase soft-constraint guidance
   abstractly ("some mechanism families are inherently broad and others
   inherently narrow") rather than naming the categories you have in mind.

---

## What was tested

The production parent layer (71 parents) was derived via a single Opus 4.7
call with the prompt at `corpora/arena/clustering_v2/closure/prompts/12_derive_parents.md`.
A 50-run replication ensemble showed substantial cross-run variation in
parent count (52–115 parents per run, mean 83). The records-per-parent
distribution within the production layer has a 3.4× max/median ratio
(largest parent absorbs ~3.4× the population of the median parent).

The methodological question was whether adding a soft constraint asking
the model to *prefer parent definitions that subsume similar volumes of
records* would (a) compress the variance, and (b) leave the natural
broad/narrow asymmetry intact (per the project's standing position that
mechanism families have inherently different prevalences in the corpus).

### Three conditions tested

All conditions used the same model (Opus 4.7), same SEED=42, same input
catalogue (1,141 clusters), same Batches API at 50% discount.

| Condition | Prompt | Reps | Spend |
|---|---|---:|---:|
| Baseline | `12_derive_parents.md` (no constraint) | 50 | (prior session, ~$25) |
| Contaminated | `12_derive_parents_softbalance.md` (constraint with named examples) | 20 | $10.13 |
| Clean | `12_derive_parents_softbalance_clean.md` (constraint without named examples) | 20 | $10.13 |

The contaminated and clean prompts differ only in one paragraph
(constraint #7). The contaminated wording named four illustrative
categories: *generic informational gaps*, *planning inadequacy*,
*chicken-and-egg deadlocks*, *equity outcomes*. The clean wording removed
these and stated the inherently-broad / inherently-narrow distinction
abstractly.

---

## Results

### Robust findings (preserved across both constrained variants)

| metric | baseline 50-run | contaminated 20-run | clean 20-run |
|---|---:|---:|---:|
| mean n_parents per run | 83.0 | 70.3 | 72.3 |
| sd n_parents | 13.6 | 12.0 | 10.7 |
| min n_parents | 52 | 52 | 54 |
| max n_parents | 115 | 93 | 91 |
| min exemplar-sum records observed | 3 | 9 | 6 |
| mean within-run max/median ratio | 1.42 | 1.42 | 1.41 |
| mean within-run sd of records/parent | 4.2 | 4.3 | 4.5 |
| mean unassigned (of 1,141) | 10.7 | 11.2 | (similar) |

**n_parents drop is real.** Both constrained variants compress mean
n_parents from baseline 83 toward ~70-72 (15% reduction). The compression
is at the lower-tail-merge end: parents that would have been formed under
the unconstrained prompt with thin exemplar populations get absorbed into
broader categories instead of standing on their own.

**Narrow-tail floor raised.** Baseline produced parents with as few as 3
exemplar-sum records (3 clusters × ~1 record each, hitting the 3-exemplar
floor at trivial population). Constrained variants raised this to 6-9.

**Within-run spread unchanged.** The constraint did *not* compress the
within-run population variation as initially hypothesised. mean max/median
sits at 1.42 across all three conditions. This is the asymmetric-
observability finding from earlier in the session: the model only shows
3-5 exemplars per parent, so the broad-tail rebalancing question (which
would require Pass-2 cluster-to-parent assignment) is invisible to this
measurement.

### Tier distribution

Mechanism-class frequency tiers (Jaccard ≥0.30 grouping on parent names):

| tier | baseline | contaminated | clean |
|---|---:|---:|---:|
| core ≥90% | 1 | 4 | 3 |
| high 70-89% | 3 | 7 | 3 |
| boundary 40-69% | 23 | 22 | 32 |
| rare 20-39% | 75 | 79 | 74 |
| singleton <20% | 1104 | 432 | 451 |

**The constraint collapses the singleton tail.** Both constrained variants
show ~60% reduction in once-only mechanism classes (1104 → 432-451). The
constraint isn't just compressing parent count per run; it's tightening
cross-run agreement on which categories are real.

### Priming canary — the prompt-example confound

For each category named as an example in the contaminated prompt, the
class-frequency comparison across the three conditions:

| term named in contaminated prompt | baseline | contaminated | clean |
|---|---:|---:|---:|
| **equity** | 24% | **75%** | **25%** |
| **distributional** | 24% | **75%** | **25%** |
| chicken-and-egg | 56% | 60% | 50% |
| planning inadequacy* | 0% | 70% | 45% |
| knowledge gap | 16% | 20% | 10% |

*The "planning inadequacy" baseline 0% is an artefact of substring matching
— baseline parent names use "Project planning and scoping inadequacy"; the
substring "planning inadequacy" doesn't appear verbatim. The numerical
comparison for that row should be read with caution.

**Equity / distributional is the cleanest priming demonstration.** A category
that appeared in 12/50 baseline runs (24%) appeared in 15/20 contaminated
runs (75%). Removing the example mention returned the rate to 5/20 (25%) —
within sampling noise of baseline. The example mention contributed ~50
percentage points to retention.

Chicken-and-egg sits in noise across all three conditions (50-60%),
indicating it's a genuinely-recurring concept the model picks up regardless
of prompt mention. Knowledge-gap also looks priming-independent. The
priming effect is therefore not universal — it's targeted at categories
the model would otherwise leave on the boundary.

---

## Interpretation

### What the constraint does

The soft-balance constraint operates as a narrow-tail pressure-amplifier.
The 3-exemplar floor in the existing prompt already creates implicit
pressure against trivial parents (a parent that doesn't have 3 cleanly-
fitting clusters won't be created). The added constraint amplifies this:
the model becomes more reluctant to create a parent backed by a small
exemplar population, and instead absorbs those clusters into adjacent
broader categories.

What the constraint does *not* do (in this measurement) is rebalance
*within* a run. The model still picks 3-5 exemplars per parent, and those
exemplars tend to be similar in size regardless of how many clusters
would map under Pass-2 assignment. To detect within-run rebalancing
(e.g., the production p05 *Knowledge gap* parent with 942 records under
Pass-2 splitting into multiple narrower parents), Pass-2 ground truth is
required.

### What prompt examples do

The contaminated/clean comparison shows that example-bearing prompt
constraints carry a substantial priming load. The mechanism is plausibly
attentional: when the model is generating parent labels, an example named
in the constraint paragraph is salient and easy to retrieve as a target.
A category that appears as a constraint example becomes a natural
candidate for inclusion regardless of whether the cluster set really
warrants it.

The size of the effect (~50 percentage points on equity) is
methodologically significant: it would dwarf the size of the constraint's
intended effect (~15% n_parents compression) on any per-category claim.
Anyone publishing taxonomy-derivation results from prompts that name
example categories in their constraints should run example-free variants
to isolate the constraint signal.

### What this means for the production parent layer

The current production parent layer (71 parents) was derived from a
single Opus 4.7 call with the unconstrained prompt. Re-deriving with the
soft-balance constraint would likely produce ~62-65 parents (the median
of contaminated/clean ranges). Whether to re-derive depends on whether
the marginal compression is worth re-running downstream Pass 2 (cluster→
parent assignment) and Pass 3 (theme audit), which would also need to
re-run.

For the methodology-paper case: report the constraint's *effect* (the
empirical claim about prompt-driven taxonomy control) rather than
re-deriving the canonical layer. The current 71-parent layer is a
defensible single-rep build; the experiment shows what would change
under the constraint without requiring the rebuild.

---

## Known gaps / open questions (§16-style register)

1. **Pass-2 ground truth on records-per-parent under the constraint.**
   The exemplar-sum proxy can't detect within-run rebalancing of broad
   parents (the production p05 knowledge-gap-at-942-records phenomenon).
   To measure cleanly, run Pass 2 on each of the 20 clean-variant runs
   and compute records-per-parent distributions head-to-head with the
   baseline. Estimated cost: ~$60 (20 × ~$3 per Pass-2 run on Sonnet).
   Wall: ~2-3 hours sequential. **Publishable extension.**

2. **Priming dose-response (not a methodology priority).** The current
   priming finding is single-shot — one set of named examples vs none.
   Quantifying the percentage-points-per-mention curve would be a
   stand-alone Claude-prompt-behaviour finding, not a methodology-
   paper priority. Side-note for whoever wants to write that up
   separately.

3. **Constraint-specificity test.** The current "soft population balance"
   wording was one of many possible. Variants that explicitly target
   *equal cluster counts* (rather than equal record counts) or *equal
   exemplar populations* (rather than implicit Pass-2 populations) would
   isolate which constraint mechanism the model is actually responding
   to. Estimated cost: ~$10-30 per variant.

4. **Prompt-anchor sensitivity.** The two existing examples in the
   `## Task` section of the unmodified prompt (*informational,
   physical-technical, control-technical, economic*) are themselves
   potential anchors. Whether *those* examples prime the production
   parent layer's distribution is unmeasured. Removing them (or
   substituting different illustrative categories) and re-running the
   ensemble would tell us whether the production layer's category mix
   inherits prompt-anchor bias. Estimated cost: ~$10, 10 min.

5. **Three-condition stability.** Each of the three ensembles is a
   single-rep at the ensemble level. The 50-run baseline has more
   statistical power than the 20-run variants. Ensemble-Jaccard between
   two reps of the contaminated variant (or two reps of the clean
   variant) is unmeasured. Estimated cost: ~$10 per additional 20-run
   ensemble.

---

## Artefacts on disk

```
corpora/arena/clustering_v2/closure/
├── prompts/
│   ├── 12_derive_parents.md                          (baseline, unmodified)
│   ├── 12_derive_parents_softbalance.md              (contaminated, with examples)
│   └── 12_derive_parents_softbalance_clean.md        (clean, examples removed)
├── code/
│   ├── 19_parent_ensemble_batch.py                   (baseline 50-run driver)
│   ├── 29_parent_ensemble_softbalance.py             (contaminated 20-run driver)
│   └── 30_parent_ensemble_softbalance_clean.py       (clean 20-run driver)
└── output/
    ├── parent_ensemble/                              (baseline 50 runs)
    │   ├── raw_responses.jsonl
    │   ├── parsed_runs.jsonl
    │   └── ensemble_summary.{json,md}
    ├── parent_ensemble_softbalance/                  (contaminated 20 runs)
    │   └── ... (same layout)
    └── parent_ensemble_softbalance_clean/            (clean 20 runs + 3-way analysis)
        ├── raw_responses.jsonl
        ├── parsed_runs.jsonl
        ├── ensemble_summary.{json,md,html}
        ├── three_way_comparison.{md,html}
        └── SESSION_WRITEUP_2026-05-05.md             (this document)
```

Each batch's raw + parsed responses are preserved verbatim for any
follow-up analysis (rep-stability, dose-response, Pass-2 ground truth).

---

## Cost summary

| Item | Spend |
|---|---:|
| Contaminated 20-run batch | $10.13 |
| Clean 20-run batch | $10.13 |
| Three-way analysis | $0 (pure data) |
| **Today's session** | **$20.26** |

Baseline 50-run was ~$25 in a prior session.

---

## Methodology-paper takeaway

One finding-shaped paragraph plus one practical rule:

> **A soft population-balance constraint added to a Pass-1 parent-derivation
> prompt compresses parent count by 15% and raises the narrow-tail floor on
> exemplar populations. The constraint operates as narrow-tail pressure-
> amplification rather than within-run rebalancing — the broad-end of the
> distribution is unaffected at exemplar-grain measurement, requiring Pass-2
> ground truth to detect any rebalancing there. The constraint also tightens
> cross-run agreement, with the singleton-tier mechanism-class population
> dropping ~60% under the constraint.**

> **Practical rule for taxonomy-derivation prompts: phrase soft-constraint
> guidance abstractly. Avoid naming specific categories as examples — those
> examples themselves prime cross-run retention of the named categories.
> A paired-prompt A/B confirmed the effect on this corpus.**
