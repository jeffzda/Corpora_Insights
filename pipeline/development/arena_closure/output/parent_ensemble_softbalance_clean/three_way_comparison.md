# Three-way comparison: baseline vs contaminated vs clean soft-balance

Canary test for the prompt-priming hypothesis: the contaminated soft-balance run named "chicken-and-egg deadlocks" and "equity outcomes" as examples of inherently-narrow parents in its prompt. The clean variant removed those examples. If the equity 24%→75% jump in the contaminated run was prompt-priming, the clean run should show equity falling back toward baseline.

**All three ensembles**: same model (Opus 4.7), same SEED=42, same input catalogue. Only constraint #7 wording differs.

## n_parents distribution

| | baseline 50-run | contaminated 20-run | clean 20-run |
|---|---:|---:|---:|
| n_runs | 50 | 20 | 20 |
| mean | 83.0 | 70.3 | 72.3 |
| min | 52 | 52 | 54 |
| max | 115 | 93 | 91 |
| sd | 13.6 | 12.0 | 10.7 |

**Read:** the n_parents drop is robust to prompt-example wording. Both constrained variants compress n_parents from baseline ~83 to ~70-72.

## Tier distribution

| tier | baseline | contaminated | clean |
|---|---:|---:|---:|
| core_>=90% | 1 | 4 | 3 |
| high_70-89% | 3 | 7 | 3 |
| boundary_40-69% | 23 | 22 | 32 |
| rare_20-39% | 75 | 79 | 74 |
| singleton_<20% | 1104 | 432 | 451 |

## Frequency of terms named in the contaminated prompt (priming canary)

| term | baseline | contaminated | clean |
|---|---:|---:|---:|
| equity | 24% | 75% | 25% |
| distribut | 24% | 75% | 25% |
| chicken-and-egg | 56% | 60% | 50% |
| planning inadequacy | 0% | 70% | 45% |
| informational gap | 0% | 0% | 0% |
| knowledge gap | 16% | 20% | 10% |

## Interpretation

**Robust findings (independent of prompt wording):**
- n_parents compresses from baseline 83 to constrained ~70-72 (15% drop). The constraint reliably reduces parent count.
- Tier distribution shifts toward higher-frequency mechanism classes — both constrained variants concentrate the cross-run agreement.

**Priming-affected findings (caveat-required):**
- The equity/distributional frequency in the contaminated run was elevated by prompt example mention. The clean run shows the true effect of the constraint without that priming.

**Methodology paper takeaway:** when adding soft-constraint examples to prompts that derive taxonomies, the chosen examples themselves prime category retention. To measure constraint effect cleanly, run example-free variants alongside example-included variants. Report both numbers; the clean variant gives unbiased constraint signal.
