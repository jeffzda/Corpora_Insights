# Category-selection ensemble — 10 reps (no threshold framing)

10 single-shot Opus 4.7 judgements asking the model to **directly select** the canonical classes that best serve the PM-facing diagnostic vocabulary purpose. No threshold variable in the prompt — the model makes per-class judgements without the pressure of finding a frequency cutoff.

Pairs with the threshold-judgement ensemble (script 34) — same 126 input classes, same model, same PM-purpose framing. Comparison below.

**Total cost:** $1.17, 311s wall.

## n_selected distribution across 10 reps

| stat | value |
|---|---:|
| n_reps | 10 |
| min | 77 |
| max | 110 |
| mean | 95.3 |
| median | 96.0 |
| sd | 8.5 |

**All n_selected values:** 99, 95, 89, 94, 97, 94, 101, 97, 77, 110

## Comparison to threshold-judgement ensemble

| stat | threshold-mode | selection-mode |
|---|---:|---:|
| min | 84 | 77 |
| max | 97 | 110 |
| mean | 91.6 | 95.3 |
| median | 93.5 | 96.0 |
| sd | 4.5 | 8.5 |

**Threshold-mode consensus (above-threshold in all 10 reps):** 83 classes
**Selection-mode consensus (selected in all 10 reps):** 72 classes

**Consensus overlap:** 60 classes in both consensus sets
**Only-threshold-consensus:** 23 classes
**Only-selection-consensus:** 12 classes

## Per-rep recommendations

| rep | n_selected | rationale excerpt |
|---:|---:|---|
| 1 | 99 | I selected classes that name structurally distinct failure mechanisms a PM could plausibly encounter on an ARENA project, prioritising coverage breadt... |
| 2 | 95 | I selected ~95 classes that span the full mechanism space a PM would need to scan: physical/material limits (c06,c07,c08,c09), data/model/measurement ... |
| 3 | 89 | The selection aims to give a PM a comprehensive but scannable diagnostic vocabulary covering the main mechanism families: physical/material constraint... |
| 4 | 94 | The set is built to give a PM a comprehensive yet scannable diagnostic vocabulary spanning physical/technical (c03-c20, c67-c79), economic/market (c23... |
| 5 | 97 | I selected classes that name structurally distinct failure mechanisms a PM would need to assess, while collapsing near-duplicates and dropping classes... |
| 6 | 94 | I selected ~94 classes that span the distinct mechanism families a PM would need to assess: physical/material limits (c06,c07,c08,c09), data/model/mea... |
| 7 | 101 | Selection principle: keep a parent if it names a structurally distinct mechanism a PM could plausibly need to flag on a real ARENA project, and drop c... |
| 8 | 97 | The selection prioritises mechanism-distinct categories a PM can use as a diagnostic checklist across the engineering, commercial, regulatory, social,... |
| 9 | 77 | I selected 77 classes that cover the mechanism space a PM must scan while collapsing near-duplicates. The set spans: physical/material constraints (c0... |
| 10 | 110 | Selected classes that name structurally distinct failure mechanisms a PM would plausibly need to assess. The set spans physical/technical limits (c03,... |

## Cross-rep agreement on selection

**Classes selected in ALL 10 reps:** 72

**Contested classes** (selected in some reps but not all): 41

| class | n selected | freq | name |
|---|---:|---:|---|
| c12 | 9/10 | 68% | Cadence, latency, and timing mismatches |
| c33 | 9/10 | 96% | Chicken-and-egg coordination deadlocks |
| c36 | 9/10 | 82% | Regulatory ambiguity, fragmentation, and jurisdictional conflict |
| c40 | 9/10 | 60% | Compliance enforcement and verification gaps |
| c48 | 9/10 | 58% | Procurement and tendering process distortions |
| c60 | 9/10 | 62% | Behavioural rebound and unintended response |
| c74 | 9/10 | 34% | Subsurface and reservoir characterisation uncertainty |
| c77 | 9/10 | 72% | Communications and connectivity failures |
| c78 | 9/10 | 58% | Single point of failure and common-mode dependency |
| c80 | 9/10 | 54% | Architectural rigidity and modularity limits |
| c90 | 9/10 | 62% | Sample, selection, and representativeness bias |
| c96 | 9/10 | 62% | Forecast uncertainty and actionability limits |
| c41 | 9/10 | 84% | Test, validation, and verification coverage gaps |
| c42 | 8/10 | 58% | Standards mismatch, obsolescence, or absence |
| c28 | 7/10 | 44% | Volatile or correlated input price exposure |
| c66 | 7/10 | 28% | Site-specific physical conditions discovered late |
| c92 | 7/10 | 48% | Counterfactual and baseline measurement difficulty |
| c113 | 7/10 | 48% | Stakeholder alignment and expectation divergence |
| c112 | 7/10 | 20% | Confidentiality and data-sharing barriers |
| c83 | 7/10 | 42% | Mechanism understanding and scientific knowledge gap |
| c22 | 6/10 | 68% | Aggregation and granularity mismatch |
| c52 | 6/10 | 46% | Personnel turnover and key-person dependency |
| c65 | 6/10 | 26% | Commissioning and handover defects |
| c88 | 6/10 | 42% | Hard-to-abate residual emissions |
| c109 | 6/10 | 42% | Unintended secondary consequences |
| c25 | 5/10 | 34% | Price signal absent, distorted, or perverse |
| c38 | 5/10 | 48% | Regulatory metric and methodology design flaws |
| c97 | 5/10 | 46% | Curtailment and headroom-driven output loss |
| c69 | 4/10 | 36% | Latent defects revealed in operation |
| c71 | 3/10 | 32% | Process chemistry and conversion limits |

**Classes never selected (across 10 reps):** 12

## Deliberated-class verdicts (model-flagged borderline)

| class | freq | mentions | include / exclude | name |
|---|---:|---:|---:|---|
| c125 | 14% | 10/10 | 10 / 0 | Insurance and risk-transfer market gaps |
| c102 | 16% | 9/10 | 9 / 0 | Rare-event and tail-condition exposure |
| c64 | 30% | 8/10 | 0 / 8 | Scope change and rework cascades |
| c91 | 64% | 6/10 | 0 / 6 | Trial design and validation infrastructure limitations |
| c118 | 10% | 6/10 | 0 / 6 | Inverter capacity allocation conflicts |
| c121 | 16% | 5/10 | 0 / 5 | Conservative-design self-defeating overspecification |
| c100 | 28% | 5/10 | 1 / 4 | Cumulative compounding and small-effect aggregation |
| c69 | 36% | 5/10 | 0 / 5 | Latent defects revealed in operation |
| c54 | 34% | 3/10 | 0 / 3 | Documentation and configuration management gaps |
| c93 | 42% | 3/10 | 0 / 3 | Optimisation objective misspecification |
| c22 | 68% | 3/10 | 0 / 3 | Aggregation and granularity mismatch |
| c101 | 38% | 3/10 | 3 / 0 | System inertia and synchronous-service shortfall |
| c122 | 26% | 3/10 | 3 / 0 | Stranded value and discrete-threshold/eligibility exclusion |
| c66 | 28% | 3/10 | 0 / 3 | Site-specific physical conditions discovered late |
| c94 | 20% | 2/10 | 0 / 2 | Performance metric and benchmark design flaws |
| c25 | 34% | 2/10 | 0 / 2 | Price signal absent, distorted, or perverse |
| c38 | 48% | 2/10 | 0 / 2 | Regulatory metric and methodology design flaws |
| c107 | 40% | 2/10 | 2 / 0 | Long-horizon commitment and stranded asset risk |
| c124 | 6% | 2/10 | 0 / 2 | Pre-existing/concurrent activity interference |
| c19 | 52% | 2/10 | 0 / 2 | Geographic and locational mismatch |
| c106 | 54% | 2/10 | 0 / 2 | Manual processes and automation gaps |
| c39 | 30% | 1/10 | 0 / 1 | Compliance burden disproportionate to scale |
| c113 | 48% | 1/10 | 0 / 1 | Stakeholder alignment and expectation divergence |
| c114 | 24% | 1/10 | 0 / 1 | Computational and algorithmic tractability limits |
| c111 | 26% | 1/10 | 1 / 0 | Equity and distributional barriers |

## Headline read

n_selected variance across 10 reps: range [77, 110], mean 95.3, sd 8.5.

**Consensus selected set** (in every rep): 72 classes — the methodologically-defensible v2 candidate set under selection-mode.
**Contested boundary**: 41 classes selected in some reps but not all.
**Never selected**: 12 classes the model agreed to exclude.

If the selection-mode consensus differs from the threshold-mode consensus (script 34), that's the more interesting finding — it shows the framing of the task changes which classes get included, beyond just changing the cutoff.
