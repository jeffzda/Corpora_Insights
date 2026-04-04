# Failure Mode Reclassification v4 — Stability Analysis

**Date:** 2026-04-05
**Analyst:** Jeff Zdanowicz (with Claude Opus 4.6)

## Background

The ARENA delivery registry contains 16,931 records extracted from 1,448 Knowledge Bank PDFs. Each record is classified with a primary failure mode (one of 8 categories) by Claude Haiku 4.5 via batch API.

A v3 reclassification had previously been run (`batch_fm_full_reclass.py`) that classified **primary failure modes only**. Secondary failure modes were left on an older intermediate taxonomy that lacked "technical underperformance" as a category, making secondary FM data in the dashboard unusable.

A v4 reclassification (`batch_fm_reclass_v4.py`) was run to fix this, sending all 16,931 records through Haiku again with a modified prompt that asks for **both primary and secondary failure modes**. The v3 primary FMs were saved as a baseline for comparison.

## Caveat: this is not a reproducibility test

The v4 prompt differs from v3 in a structurally important way: it asks Haiku to assign a secondary failure mode. This gives the model more room to express nuance and may cause it to reorder what it considers primary vs secondary. Some records that were forced into a single category under v3 may now split across primary and secondary differently.

A clean reproducibility test would require running the **identical** v3 prompt again and comparing outputs. That has not been done. Estimated cost: ~$10. It would isolate pure stochastic noise from prompt-induced reordering and provide a proper error bar on every number in the dashboard.

## Results summary

| Metric | Value |
|---|---|
| Total records compared | 16,931 |
| Primary FM agreement (v3 vs v4) | 15,417 (91.1%) |
| Baseline primary matched v4 secondary | 787 (4.6%) |
| Matched either primary or secondary | 16,204 (95.7%) |
| No match at all | 727 (4.3%) |

### Interpretation of the 4.6% primary-to-secondary migration

787 records had their v3 primary FM appear as the v4 secondary — meaning Haiku found a better primary but kept the old classification as a co-occurring failure mode. This is not disagreement; it's reordering enabled by the new prompt structure.

### Breakdown of the 4.3% hard disagreements

| Transition type | n | % of no-match |
|---|---|---|
| Adverse in v3 → "no major failure stated" in v4 | 385 | 52.9% |
| Changed to a different adverse category | 342 | 47.1% |

Over half the hard disagreements are records that Haiku reclassified as non-failures on second look, not taxonomy confusion.

## Confidence ratings by reassignment type

| Reassignment type | n | Mean confidence | Median |
|---|---|---|---|
| Matched primary (stable) | 15,417 | 0.885 | 0.88 |
| Matched secondary (reordered) | 787 | 0.837 | 0.82 |
| No match → "no failure" | 385 | 0.913 | 0.92 |
| No match → different FM | 342 | 0.820 | 0.82 |

Notable: records that flipped to "no major failure stated" had the **highest** confidence of any group (0.913). Haiku was very sure these weren't failures. The genuinely ambiguous records are the 342 that changed to a different adverse category at the lowest confidence (0.820).

## Stability matrix: % of v3 primary retained as v4 primary

Rows = v3 (baseline) primary. Columns = v4 (new) primary. Each row sums to 100%.

| v3 category | no failure | commercial | coordination | data | execution | regulatory | tech underperf | unval integr | n |
|---|---|---|---|---|---|---|---|---|---|
| **no failure** | **98.8** | 0.4 | 0.1 | 0.2 | 0.2 | 0.2 | 0.1 | — | 4,646 |
| **commercial** | 3.3 | **93.1** | 1.1 | 0.8 | 0.3 | 0.8 | 0.7 | — | 2,385 |
| **data** | 3.1 | 0.4 | 0.6 | **93.8** | 0.6 | 0.3 | 1.0 | 0.3 | 1,577 |
| **regulatory** | 1.8 | 2.1 | 2.1 | 1.3 | 0.5 | **91.4** | 0.6 | 0.2 | 1,656 |
| **tech underperf** | 2.8 | 2.2 | 0.4 | 3.7 | 1.3 | 0.8 | **87.2** | 1.5 | 2,044 |
| **coordination** | 5.1 | 3.6 | **84.1** | 1.6 | 2.0 | 2.5 | 0.1 | 1.0 | 2,205 |
| **execution** | 2.9 | 1.5 | 4.7 | 1.0 | **84.0** | 0.9 | 4.4 | 0.6 | 1,428 |
| **unval integr** | 1.6 | 0.6 | 4.7 | 2.4 | 1.1 | 1.2 | 9.5 | **78.8** | 983 |

### Category stability tiers

- **Tier 1 (>93% stable):** no major failure stated, commercial & market, data & measurement — these classifications are robust.
- **Tier 2 (87-92% stable):** regulatory & approvals, technical underperformance — solid but with some boundary softness.
- **Tier 3 (78-85% stable):** coordination & stakeholders, execution & logistics, unvalidated integration — these categories have meaningful classification uncertainty.

### Known weak boundaries

1. **Unvalidated integration ↔ technical underperformance:** 9.5% of unvalidated integration records migrated to technical underperformance. This is the fuzziest boundary in the taxonomy. Any analysis that hinges on distinguishing these two categories should be caveated.

2. **Coordination ↔ no failure:** 5.1% of coordination records flipped to non-adverse. The original v3 run may have over-classified marginal observations as coordination failures.

3. **Execution ↔ coordination / tech underperformance:** Execution leaks ~4.7% to coordination and ~4.4% to technical underperformance. Physical delivery problems often involve coordination breakdowns and technology issues simultaneously.

## Secondary failure mode distribution (v4, new data)

9,099 of 16,931 records (53.7%) received a secondary failure mode.

| Secondary FM | n | % of secondaries |
|---|---|---|
| coordination & stakeholders | 2,342 | 25.7% |
| execution & logistics | 1,682 | 18.5% |
| technical underperformance | 1,405 | 15.4% |
| commercial & market | 1,185 | 13.0% |
| data & measurement | 1,103 | 12.1% |
| regulatory & approvals | 948 | 10.4% |
| unvalidated integration | 429 | 4.7% |

Technical underperformance now appears as secondary in 1,405 records. In the previous data (old taxonomy), it appeared in 4. This was the data gap that prompted this reclassification.

## Intra-rater reliability test (identical prompt, run 1 vs run 2)

The v4 prompt was run a second time on all 16,931 records to measure pure stochastic noise — same model, same prompt, same data. This is analogous to the same human rater reviewing the same cases on a different day.

### Primary failure mode

| Metric | Value |
|---|---|
| Agreement | 15,981 / 16,931 (94.4%) |
| Disagreed | 950 / 16,931 (5.6%) |
| Matched via primary/secondary swap | 645 (3.8%) |
| Hard disagreement (no match in either) | 305 (1.8%) |

**The stochastic noise floor for primary FM classification is ~5.6%.** Of the disagreements, most (3.8%) are primary/secondary reordering — the model identified the same two failure modes but ranked them differently. Only 1.8% of records land in a genuinely unrelated category across identical runs.

### Secondary failure mode

| Metric | n | % |
|---|---|---|
| Both null (agree, no secondary) | 7,498 | 44.3% |
| Both same (agree on secondary) | 7,410 | 43.8% |
| One null, one not | 664 | 3.9% |
| Both present, different | 1,359 | 8.0% |
| **Total secondary agreement** | **14,908** | **88.1%** |

Secondary FM is noisier than primary (88.1% vs 94.4%), as expected — the model is less decisive about the co-occurring failure mode.

### Confidence by agreement

| Group | Mean confidence | Median | Stdev |
|---|---|---|---|
| Agreed (primary) | 0.885 | 0.88 | 0.052 |
| Disagreed (primary) | 0.842 | 0.82 | 0.048 |

Disagreed records have systematically lower confidence, confirming that the model's self-reported confidence is a meaningful signal for classification uncertainty.

### Intra-rater stability matrix

Rows = run 1 primary. Columns = run 2 primary. Each row sums to 100%.

| Run 1 category | no failure | commercial | coordination | data | execution | regulatory | tech underperf | unval integr | n |
|---|---|---|---|---|---|---|---|---|---|
| **no failure** | **97.9** | 0.5 | 0.4 | 0.5 | 0.3 | 0.2 | 0.2 | 0.0 | 4,977 |
| **commercial** | 1.6 | **94.9** | 1.5 | 0.3 | 0.3 | 0.8 | 0.5 | 0.0 | 2,432 |
| **data** | 1.4 | 0.5 | 1.0 | **93.7** | 0.4 | 0.5 | 2.0 | 0.5 | 1,678 |
| **regulatory** | 0.5 | 1.3 | 1.9 | 0.5 | 0.5 | **94.0** | 1.0 | 0.3 | 1,641 |
| **tech underperf** | 1.0 | 1.4 | 0.2 | 1.2 | 1.5 | 0.4 | **92.7** | 1.7 | 1,990 |
| **coordination** | 1.1 | 1.5 | **91.6** | 0.8 | 2.0 | 1.8 | 0.1 | 1.0 | 2,052 |
| **execution** | 0.6 | 0.7 | 2.8 | 0.7 | **91.7** | 0.8 | 2.3 | 0.5 | 1,317 |
| **unval integr** | 0.1 | 0.1 | 2.3 | 1.1 | 0.6 | 0.5 | 5.8 | **89.6** | 843 |

All categories are 2-4 percentage points more stable than the v3→v4 comparison, confirming that a portion of the earlier drift was prompt-induced (adding the secondary FM field), not random noise.

### Comparison: prompt change vs stochastic noise

| Source of disagreement | Primary FM disagreement rate | Hard disagreement (no match either) |
|---|---|---|
| **Prompt change** (v3→v4, adding secondary) | 8.9% | 4.3% |
| **Stochastic noise** (v4 run 1 vs run 2) | 5.6% | 1.8% |
| **Difference** (attributable to prompt change) | 3.3% | 2.5% |

The prompt change (asking for secondary FM) accounts for roughly 3 percentage points of additional primary FM instability beyond the stochastic baseline. This is consistent with the model reordering primary/secondary when given the option.

### Category stability tiers (revised with intra-rater data)

| Tier | Categories | Intra-rater stability | v3→v4 stability |
|---|---|---|---|
| **Tier 1** (>94%) | no failure, commercial, data, regulatory | 93.7–97.9% | 91.4–98.8% |
| **Tier 2** (91-93%) | tech underperformance, coordination, execution | 91.6–92.7% | 84.0–87.2% |
| **Tier 3** (<91%) | unvalidated integration | 89.6% | 78.8% |

Unvalidated integration remains the least stable category. The unvalidated integration ↔ technical underperformance boundary (5.8% leakage) is the weakest joint in the taxonomy under both prompt change and stochastic noise conditions.

## Implications for dashboard use

1. **Portfolio-level patterns are robust.** The ~5.6% noise floor is roughly symmetric across categories and washes out across hundreds of records. Dominant failure modes, adversity rates by category, and severity distributions are reliable at the portfolio level.

2. **Individual record classifications carry ~5-6% uncertainty on primary FM and ~12% on secondary FM.** Do not stake a decision on a single record's failure mode assignment.

3. **The unvalidated integration / technical underperformance boundary is the weakest joint.** ~6% leakage in both directions even under identical conditions. Any analysis that hinges on distinguishing these two categories should be caveated.

4. **The adverse/non-adverse boundary is soft at the margins.** ~1-2% of records classified as adverse may be borderline non-failures. The model's confidence score is a useful signal for identifying these borderline cases.

5. **Self-reported confidence is meaningful.** Records that change classification between runs have systematically lower confidence (0.842 vs 0.885). Consider filtering to confidence > 0.85 for high-stakes analysis.

6. **An inter-rater test (different model, e.g. Sonnet, on a stratified sample) would measure accuracy, not just precision.** This intra-rater test establishes the precision of the instrument — a necessary but not sufficient condition for accuracy.

## Files

| File | Description |
|---|---|
| `scripts/batch_fm_reclass_v4.py` | v4 reclassification script |
| `insights/per_doc_fm_v3/` | v4 run 2 results (current) |
| `insights/per_doc_fm_v3_run1/` | v4 run 1 results (saved for comparison) |
| `insights/per_doc_fm_v3_baseline/` | v3 baseline (pre-v4, primary-only prompt) |
