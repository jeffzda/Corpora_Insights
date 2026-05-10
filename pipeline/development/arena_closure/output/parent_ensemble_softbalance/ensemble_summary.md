# Pass-1 Parent-Derivation Ensemble — 20-Run Summary

**Model:** `claude-opus-4-7`  |  **Prompt seed:** 42 (identical across all runs)  |  **Total cost:** $10.13 batch ($20.26 sync-equivalent)


## Granularity distribution (n_parents per run)

- min / mean / max: **52 / 70.3 / 93**
- sd: 12.03, p10/p50/p90: 56/69/90

## Coverage (n_unassigned per run, of 1,141 input clusters)

- min / mean / max: **6 / 11.2 / 20**
- sd: 3.75, p10/p50/p90: 7/11/15

## Mechanism-class frequency tiers (across 20 runs)

Distinct mechanism classes detected (Jaccard ≥ 0.30 grouping): **544**

| Tier | n classes |
|---|---:|
| core_>=90% | 4 |
| high_70-89% | 7 |
| boundary_40-69% | 22 |
| rare_20-39% | 79 |
| singleton_<20% | 432 |

## Union vocabulary size at minimum-runs threshold

| Min runs | n classes |
|---:|---:|
| ≥ 1 | 544 |
| ≥ 5 | 80 |
| ≥ 10 | 18 |
| ≥ 25 | 0 |
| ≥ 45 | 0 |

## Top 30 most-frequent mechanism classes

| Runs | Frequency | Example labels |
|---:|---:|---|
| 19/20 | 95% | Model, forecast, and simulation error / Forecasting and predictive model error / Model, forecast, and simulation inaccuracy |
| 19/20 | 95% | Scale-up and lab-to-field translation gaps / Pilot/lab to scale translation failure / Pilot-to-scale or lab-to-field translation failure |
| 19/20 | 95% | Multi-party coordination and responsibility gap / Multi-party coordination and responsibility gaps / Multi-party coordination and responsibility-allocation failure |
| 18/20 | 90% | Regulatory and approval process delay or rework / Regulatory compliance burden and process delay / Regulatory Process Friction and Delay |
| 17/20 | 85% | Measurement, sensing and instrumentation gaps / Measurement instrument and sensing inadequacy / Measurement instrument and sensor inadequacy |
| 16/20 | 80% | Data quality, format and pipeline integrity failures / Data Quality, Integration and Pipeline Failures / Data quality, granularity, and representativeness defects |
| 15/20 | 75% | Physical material, thermal, and chemical limits / Material, chemical, and thermal physical limits / Material, chemical and physical-process limits |
| 15/20 | 75% | Regulatory and Standards Framework Gaps / Regulatory Framework Misfit or Misalignment / Regulatory framework gap or absence |
| 15/20 | 75% | Equity and distributional outcome failure / Distributional and equity outcomes / Equity / Distributional Outcome |
| 14/20 | 70% | Project planning and scope inadequacy / Project planning, scoping, and contingency inadequacy / Project planning and scoping inadequacy |
| 14/20 | 70% | Supply-chain, procurement, and lead-time disruption / Supply Chain Disruption and Procurement Constraints / Supply chain disruption and lead-time risk |
| 12/20 | 60% | Chicken-and-egg / coordination deadlock / Chicken-and-Egg / Coordination Deadlock / Chicken-and-egg deployment deadlocks |
| 11/20 | 55% | Technology readiness and maturity gap / Scale-up Maturity and Technology Readiness Gaps / Commercial maturity and technology readiness gaps |
| 11/20 | 55% | Knowledge transfer and learning capture failures / Knowledge Transfer and Lessons-Capture Failure / Documentation, handover, and knowledge transfer failures |
| 11/20 | 55% | Manufacturing, fabrication, and yield defects / Manufacturing, Fabrication and Assembly Defects / Manufacturing and fabrication defect |
| 10/20 | 50% | Power-system stability and inverter-grid interaction / Inverter / IBR control behaviour and grid interaction / Inverter / Power-Electronics Grid-Interaction Failures |
| 10/20 | 50% | Test, validation, and verification gap / Confounded Field Validation and Empirical Verification / Verification, validation, and benchmarking shortfalls |
| 10/20 | 50% | Subsurface and reservoir characterisation uncertainty / Subsurface and Resource Characterisation Risk / Resource characterisation and uncertainty |
| 9/20 | 45% | Network / Grid Capacity, Strength, or Topology Constraint / Network Capacity, Hosting, and Voltage Constraints / Grid capacity, connection, and network constraint |
| 9/20 | 45% | Feedstock variability, quality and processability constraints / Feedstock variability and quality constraint / Feedstock Variability and Quality Constraints |
| 9/20 | 45% | Spatial, geometric, and siting constraint / Spatial, geographic, and siting constraints / Spatial, geographic, and siting constraint |
| 9/20 | 45% | Knowledge transfer and learning deficits / Knowledge transfer and institutional learning failure / Knowledge transfer and institutional learning gaps |
| 9/20 | 45% | Missing or Inaccessible Data and Knowledge / Missing or Inaccessible Data and Documentation / Missing or inaccessible information |
| 9/20 | 45% | Environmental and Weather Stressors / Environmental exposure and weather-driven damage / Environmental and weather exposure |
| 9/20 | 45% | Capital allocation, financing, and investment-return barriers / Capital Cost and Financing Threshold Barriers / Capital-cost and high-upfront-investment barriers |
| 9/20 | 45% | Hazard, Safety and Risk-Triggered Constraint / Safety and Hazard Emergence / Hazard, safety and risk envelope expansion |
| 9/20 | 45% | Coupled Trade-offs and Multi-Objective Conflicts / Coupled trade-off / multi-objective optimisation conflict / Coupled-objective and trade-off mechanisms |
| 9/20 | 45% | Communication, Latency, and Connectivity / Communications, latency and connectivity failures / Stakeholder communication and trust failures |
| 8/20 | 40% | Data Absence and Information Gaps / Data and information absence / Data Absence or Inaccessibility |
| 8/20 | 40% | Resource intermittency, variability, and seasonality / Resource Variability and Intermittency / Resource intermittency, variability, and seasonality mismatch |

## Records-per-parent within-run distribution (exemplar-sum proxy)

Each parent has 3-5 exemplar clusters; sum of their `n_records` gives a proxy for the parent's population. The within-run *spread* of this measure tells us whether parents are population-balanced.

| metric | baseline 50-run (no constraint) | soft-balance 20-run (this run) | delta |
|---|---:|---:|---:|
| n_runs | 50 | 20 | -30 |
| mean_n_parents | 83 | 70.3 | -12.7 |
| mean_max_over_median | 1.42 | 1.42 | +0.0 |
| mean_records_per_parent_sd | 4.2 | 4.3 | +0.1 |
| mean_median_records | 20.6 | 22.7 | +2.1 |
| max_records_observed | 45 | 60 | +15 |
| min_records_observed | 3 | 9 | +6 |

**Reading:** if the soft-balance constraint bit, expect *mean_max_over_median* and *mean_records_per_parent_sd* to be notably lower in soft-balance vs baseline; expect *mean_n_parents* to shift modestly (toward fewer parents if the model dropped rare-narrow categories, toward more if it split broad ones). If the constraint was too soft to bite, all metrics within sampling noise of baseline.
