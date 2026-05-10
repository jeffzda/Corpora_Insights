# Threshold-judgement ensemble — 10 reps

10 single-shot Opus 4.7 judgements on the same 126-canonical-class input. Same prompt, same model, no temperature variation. Tests how reproducible the threshold-selection judgement is across reps.

**Total cost (rep 02-10):** $0.95, 258s wall.

## Threshold distribution across 10 reps

| stat | value |
|---|---:|
| n_reps | 10 |
| min | 0.3 |
| max | 0.46 |
| mean | 0.37 |
| median | 0.34 |
| sd | 0.061 |

**All threshold values:** 34%, 34%, 42%, 30%, 40%, 34%, 46%, 34%, 46%, 30%

## n_classes distribution

| stat | value |
|---|---:|
| min | 84 |
| max | 97 |
| mean | 91.6 |
| median | 93.5 |
| sd | 4.5 |

**All n_classes values:** 95, 95, 89, 95, 87, 95, 84, 92, 87, 97

## Per-rep recommendations

| rep | threshold | n_classes | rationale excerpt |
|---:|---:|---:|---|
| 1 | 0.34 | 95 | The frequency distribution descends nearly linearly with no shoulder, so the threshold must be argued on content rather than a natural break. At ≥34%,... |
| 2 | 0.34 | 95 | The distribution descends nearly linearly without a natural shoulder, so the threshold must be chosen on PM-utility grounds. At 34% we retain 95 class... |
| 3 | 0.42 | 89 | A threshold of 42% balances comprehensive mechanism coverage against navigability and per-parent evidentiary defensibility. Above 42%, the canonical s... |
| 4 | 0.3 | 95 | A 30% threshold yields ~95 parents — large but navigable in a structured diagnostic vocabulary, and it captures the substantive mechanism breadth a PM... |
| 5 | 0.4 | 87 | The distribution descends nearly linearly with no natural shoulder, so the threshold must be chosen on PM-utility grounds. A 0.40 cut yields 87 parent... |
| 6 | 0.34 | 95 | A 34% threshold yields ~95 parents, which is at the upper edge of navigability but defensible because the canonical set is unusually well-disambiguate... |
| 7 | 0.46 | 84 | A 46% threshold cuts at a defensible point: above it, 84 classes each appeared in at least 23/50 reps, supplying a per-parent evidentiary basis the PM... |
| 8 | 0.34 | 92 | A threshold of 34% retains 92 classes — large but defensible for a navigable diagnostic vocabulary, given the corpus spans the entire clean-energy pro... |
| 9 | 0.46 | 87 | The distribution descends nearly linearly with no shoulder, so the threshold must be argued from content, not curve shape. At 46% we retain 87 classes... |
| 10 | 0.3 | 97 | A threshold of 30% retains 97 classes — large but defensible for a navigable diagnostic tool that prioritises coverage. The distribution is nearly lin... |

## Cross-rep agreement on inclusion

**Classes ABOVE threshold in ALL 10 reps:** 83 (the consensus parent set)

**Contested classes** (above-threshold in some reps but not all): 20

| class | n above | freq | name |
|---|---:|---:|---|
| c28 | 8/10 | 44% | Volatile or correlated input price exposure |
| c83 | 8/10 | 42% | Mechanism understanding and scientific knowledge gap |
| c88 | 8/10 | 42% | Hard-to-abate residual emissions |
| c93 | 8/10 | 42% | Optimisation objective misspecification |
| c98 | 8/10 | 42% | Visibility, observability, and monitoring gaps |
| c109 | 8/10 | 42% | Unintended secondary consequences |
| c57 | 7/10 | 40% | Community opposition and social licence |
| c107 | 7/10 | 40% | Long-horizon commitment and stranded asset risk |
| c101 | 6/10 | 38% | System inertia and synchronous-service shortfall |
| c69 | 6/10 | 36% | Latent defects revealed in operation |
| c99 | 6/10 | 36% | Demand response and aggregator delivery shortfall |
| c108 | 6/10 | 36% | External shocks and force-majeure disruption |
| c25 | 6/10 | 34% | Price signal absent, distorted, or perverse |
| c54 | 6/10 | 34% | Documentation and configuration management gaps |
| c74 | 6/10 | 34% | Subsurface and reservoir characterisation uncertainty |
| c82 | 6/10 | 34% | First-of-kind execution and precedent absence |
| c115 | 6/10 | 34% | Standardisation absence forcing bespoke effort |
| c71 | 2/10 | 32% | Process chemistry and conversion limits |
| c39 | 2/10 | 30% | Compliance burden disproportionate to scale |
| c64 | 2/10 | 30% | Scope change and rework cascades |

## Borderline-class verdicts across reps

Classes raised by at least one rep in its borderline set, with cross-rep verdict tally:

| class | freq | mentions | include / exclude | name |
|---|---:|---:|---:|---|
| c39 | 30% | 6/10 | 2 / 4 | Compliance burden disproportionate to scale |
| c64 | 30% | 5/10 | 2 / 3 | Scope change and rework cascades |
| c82 | 34% | 4/10 | 4 / 0 | First-of-kind execution and precedent absence |
| c74 | 34% | 4/10 | 4 / 0 | Subsurface and reservoir characterisation uncertainty |
| c115 | 34% | 4/10 | 4 / 0 | Standardisation absence forcing bespoke effort |
| c66 | 28% | 4/10 | 0 / 4 | Site-specific physical conditions discovered late |
| c57 | 40% | 3/10 | 2 / 1 | Community opposition and social licence |
| c71 | 32% | 2/10 | 0 / 2 | Process chemistry and conversion limits |
| c98 | 42% | 2/10 | 1 / 1 | Visibility, observability, and monitoring gaps |
| c107 | 40% | 2/10 | 1 / 1 | Long-horizon commitment and stranded asset risk |
| c101 | 38% | 2/10 | 0 / 2 | System inertia and synchronous-service shortfall |
| c69 | 36% | 2/10 | 0 / 2 | Latent defects revealed in operation |
| c23 | 46% | 2/10 | 2 / 0 | Capital cost and upfront investment barriers |
| c52 | 46% | 2/10 | 2 / 0 | Personnel turnover and key-person dependency |
| c28 | 44% | 2/10 | 0 / 2 | Volatile or correlated input price exposure |
| c83 | 42% | 2/10 | 0 / 2 | Mechanism understanding and scientific knowledge gap |
| c54 | 34% | 1/10 | 1 / 0 | Documentation and configuration management gaps |
| c109 | 42% | 1/10 | 1 / 0 | Unintended secondary consequences |
| c65 | 26% | 1/10 | 0 / 1 | Commissioning and handover defects |
| c111 | 26% | 1/10 | 0 / 1 | Equity and distributional barriers |
| c108 | 36% | 1/10 | 0 / 1 | External shocks and force-majeure disruption |
| c97 | 46% | 1/10 | 1 / 0 | Curtailment and headroom-driven output loss |
| c92 | 48% | 1/10 | 1 / 0 | Counterfactual and baseline measurement difficulty |
| c113 | 48% | 1/10 | 1 / 0 | Stakeholder alignment and expectation divergence |
| c72 | 28% | 1/10 | 0 / 1 | Process by-product, contamination, and fouling |

## Headline read

Threshold variance across 10 reps: range [0.3, 0.46], mean 0.37, sd 0.061.

n_classes variance: range [84, 97], mean 91.6, sd 4.5.

**Consensus parent set** (above-threshold in every rep): 83 classes.
**Contested boundary** (above in some reps but not all): 20 classes.

The consensus set is the methodologically-defensible v2 candidate. The contested set is where the override-list discussion happens — these are the classes that need explicit per-class judgement rather than mechanical threshold application.
