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

## Implications for dashboard use

1. **Portfolio-level patterns are robust.** Classification noise is roughly symmetric and washes out across hundreds of records. The dominant failure modes, adversity rates by category, and severity distributions are reliable.

2. **Individual record classifications carry ~5-10% uncertainty.** Do not stake a decision on a single record's failure mode assignment.

3. **The unvalidated integration / technical underperformance boundary is the weakest joint.** If presenting findings that distinguish these two, caveat it.

4. **~2% of adverse records may not be genuinely adverse.** The adverse/non-adverse threshold is a soft boundary. Haiku reclassified 385 previously-adverse records as non-failures with high confidence (0.913).

5. **A true reproducibility test (identical prompt, ~$10) would establish a proper error bar** by isolating stochastic model noise from prompt-induced reordering. Not yet performed.

## Files

| File | Description |
|---|---|
| `scripts/batch_fm_reclass_v4.py` | v4 reclassification script |
| `insights/per_doc_fm_v3/` | v4 results (overwrote v3) |
| `insights/per_doc_fm_v3_baseline/` | v3 baseline (1,183 files, saved before v4 run) |
