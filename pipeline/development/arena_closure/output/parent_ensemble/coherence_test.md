# Canonical Vocabulary Coherence Test

Of the **126 canonical classes** produced by Opus consolidation of the
50-run ensemble, only **35 (28%)** are *atomic* in the sense
that no individual run ever produced 2+ distinct parent labels falling under them.

The other **91 (72%)** are *boundary-blurred*: at least one run
treated them as 2-4 distinct mechanism classes, meaning the canonical class is
coarser-than-run for those splits.

## By tier

| Tier | n classes | atomic | with-multi | % atomic |
|---|---:|---:|---:|---:|
| core_>=90% | 24 | 0 | 24 | 0% |
| high_70-89% | 23 | 2 | 21 | 9% |
| boundary_40-69% | 44 | 10 | 34 | 23% |
| rare_20-39% | 26 | 15 | 11 | 58% |
| singleton_<20% | 9 | 8 | 1 | 89% |

## Interpretation

**Atomicity decreases with frequency.** The most-agreed-upon canonical classes
are the *least* atomic — every single core (≥90%) class has at least one run
splitting it. The high-frequency consensus is at a *coarser granularity* than
individual runs typically work at.

**The canonical 126 is not a fine-grained atomic taxonomy.** It is the union
of run-level boundary choices, where ~72% of the canonical classes merge
distinctions some runs treat as separate.

## Top-20 most-merged canonical classes (most run-level splits)

| class | n_runs | runs splitting | max labels/run | tier | name |
|---|---:|---:|---:|---|---|
| c04 | 50 | 20 | 3 | core_>=90% | Model, simulation, and forecast inaccuracy |
| c79 | 44 | 20 | 3 | high_70-89% | Legacy infrastructure and architecture incompatibility |
| c06 | 50 | 19 | 4 | core_>=90% | Material, chemical, and physical-property limits |
| c11 | 49 | 16 | 4 | core_>=90% | Control logic, configuration, and parameter errors |
| c20 | 42 | 16 | 3 | high_70-89% | Aggregate, correlation, and diversity-loss effects |
| c61 | 49 | 14 | 3 | core_>=90% | Project planning, scoping, and contingency inadequacy |
| c24 | 44 | 13 | 3 | high_70-89% | Cost structure and unit-economics infeasibility |
| c59 | 44 | 13 | 2 | high_70-89% | Customer behavioural and motivation barriers |
| c05 | 49 | 12 | 3 | core_>=90% | Lab-to-field and pilot-to-scale translation failure |
| c31 | 44 | 12 | 3 | high_70-89% | Market structure and incumbent advantage |
| c07 | 40 | 11 | 3 | high_70-89% | Equipment operating outside design envelope |
| c55 | 39 | 11 | 2 | high_70-89% | Stakeholder engagement and consultation failures |
| c43 | 46 | 10 | 3 | core_>=90% | Policy uncertainty and instability |
| c86 | 38 | 10 | 2 | high_70-89% | Externalities and lifecycle accounting omissions |
| c50 | 48 | 9 | 2 | core_>=90% | Supply chain and logistics disruption |
| c09 | 46 | 9 | 3 | core_>=90% | Environmental and weather exposure |
| c51 | 48 | 8 | 2 | core_>=90% | Workforce skills and capability shortage |
| c58 | 48 | 8 | 2 | core_>=90% | Customer recruitment, conversion, and retention shortfalls |
| c91 | 32 | 8 | 2 | boundary_40-69% | Trial design and validation infrastructure limitations |
| c14 | 49 | 7 | 3 | core_>=90% | Inverter-based resource and grid stability dynamics |

## All 35 atomic canonical classes (no run ever subdivided)

| class | n_runs | tier | name |
|---|---:|---|---|
| c29 | 38 | high_70-89% | Subsidy and incentive design distortions |
| c77 | 36 | high_70-89% | Communications and connectivity failures |
| c16 | 33 | boundary_40-69% | Temporal mismatch between supply and demand |
| c35 | 31 | boundary_40-69% | Regulatory framework misfit or obsolescence |
| c45 | 27 | boundary_40-69% | Responsibility, ownership, and accountability gaps |
| c68 | 25 | boundary_40-69% | Equipment degradation, wear, and ageing |
| c18 | 24 | boundary_40-69% | Resource intermittency and variability |
| c52 | 23 | boundary_40-69% | Personnel turnover and key-person dependency |
| c28 | 22 | boundary_40-69% | Volatile or correlated input price exposure |
| c83 | 21 | boundary_40-69% | Mechanism understanding and scientific knowledge gap |
| c88 | 21 | boundary_40-69% | Hard-to-abate residual emissions |
| c57 | 20 | boundary_40-69% | Community opposition and social licence |
| c99 | 18 | rare_20-39% | Demand response and aggregator delivery shortfall |
| c25 | 17 | rare_20-39% | Price signal absent, distorted, or perverse |
| c74 | 17 | rare_20-39% | Subsurface and reservoir characterisation uncertainty |
| c82 | 17 | rare_20-39% | First-of-kind execution and precedent absence |
| c115 | 17 | rare_20-39% | Standardisation absence forcing bespoke effort |
| c66 | 14 | rare_20-39% | Site-specific physical conditions discovered late |
| c72 | 14 | rare_20-39% | Process by-product, contamination, and fouling |
| c103 | 14 | rare_20-39% | Diminishing returns and saturation effects |
| c65 | 13 | rare_20-39% | Commissioning and handover defects |
| c111 | 13 | rare_20-39% | Equity and distributional barriers |
| c120 | 13 | rare_20-39% | Maintenance, access, and serviceability constraints |
| c114 | 12 | rare_20-39% | Computational and algorithmic tractability limits |
| c73 | 10 | rare_20-39% | Resource depletion and natural-resource availability |
| c94 | 10 | rare_20-39% | Performance metric and benchmark design flaws |
| c112 | 10 | rare_20-39% | Confidentiality and data-sharing barriers |
| c102 | 8 | singleton_<20% | Rare-event and tail-condition exposure |
| c110 | 8 | singleton_<20% | Self-reporting, gaming, and verification weakness |
| c119 | 8 | singleton_<20% | Emerging technology demand-side and ecosystem immaturity |
| c125 | 7 | singleton_<20% | Insurance and risk-transfer market gaps |
| c118 | 5 | singleton_<20% | Inverter capacity allocation conflicts |
| c123 | 4 | singleton_<20% | Coordinated-control granularity and addressing limits |
| c124 | 3 | singleton_<20% | Pre-existing/concurrent activity interference |
| none | 0 | singleton_<20% | No fit |