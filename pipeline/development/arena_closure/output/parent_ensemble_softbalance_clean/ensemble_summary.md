# Pass-1 Parent-Derivation Ensemble — 20-Run Summary

**Model:** `claude-opus-4-7`  |  **Prompt seed:** 42 (identical across all runs)  |  **Total cost:** $10.13 batch ($20.26 sync-equivalent)


## Granularity distribution (n_parents per run)

- min / mean / max: **54 / 72.3 / 91**
- sd: 10.74, p10/p50/p90: 60/73/90

## Coverage (n_unassigned per run, of 1,141 input clusters)

- min / mean / max: **5 / 9.95 / 24**
- sd: 4.86, p10/p50/p90: 6/8/21

## Mechanism-class frequency tiers (across 20 runs)

Distinct mechanism classes detected (Jaccard ≥ 0.30 grouping): **563**

| Tier | n classes |
|---|---:|
| core_>=90% | 3 |
| high_70-89% | 3 |
| boundary_40-69% | 32 |
| rare_20-39% | 74 |
| singleton_<20% | 451 |

## Union vocabulary size at minimum-runs threshold

| Min runs | n classes |
|---:|---:|
| ≥ 1 | 563 |
| ≥ 5 | 79 |
| ≥ 10 | 25 |
| ≥ 25 | 0 |
| ≥ 45 | 0 |

## Top 30 most-frequent mechanism classes

| Runs | Frequency | Example labels |
|---:|---:|---|
| 19/20 | 95% | Physical and material limits / Physical and Material Limits / Material, chemical, and physical degradation |
| 18/20 | 90% | Lab-to-Field Translation Gaps / Scale and Throughput Translation Failures / Lab-to-field and pilot-to-scale translation failure |
| 18/20 | 90% | Multi-party coordination and governance gap / Multi-Party Coordination and Interface Friction / Stakeholder coordination and multi-party governance gaps |
| 17/20 | 85% | Missing or Inaccessible Data and Documentation / Missing or Inaccessible Information / Missing or Inaccessible Data and Knowledge |
| 16/20 | 80% | Regulatory Process and Approval Burden / Regulatory Process Delay and Approval Lag / Regulatory Process Delay and Approval Gating |
| 14/20 | 70% | Capacity and Sizing Mismatch / Asset Sizing and Capacity Mismatch / Capacity, Sizing, and Headroom Mismatch |
| 13/20 | 65% | Customer/participant recruitment and retention / Customer recruitment, conversion and retention barriers / Customer Recruitment, Conversion and Retention |
| 13/20 | 65% | Trust, Acceptance, and Social Licence / Stakeholder engagement, trust, and social licence / Stakeholder communication, trust and engagement quality |
| 13/20 | 65% | Manufacturing yield, quality, and fabrication failures / Manufacturing/Fabrication Defect and Yield Loss / Fabrication, Manufacturing, and Scale-Up Defects |
| 13/20 | 65% | Regulatory Framework Gaps and Misfits / Regulatory Framework Absence, Gap, or Misfit / Regulatory Framework Gaps and Misfit |
| 12/20 | 60% | Tightly coupled trade-offs and irreducible conflicts / Coupled trade-offs and constraint conflicts / Inherent technology trade-offs and coupled objectives |
| 12/20 | 60% | Regulatory framework gap or misfit to novel technology / Regulatory Gap or Absence / Regulatory framework absence or gap |
| 11/20 | 55% | Measurement, sensing, and instrumentation inadequacy / Measurement and Sensing Inadequacy / Sensing, measurement and instrumentation gaps |
| 11/20 | 55% | Feedstock supply and quality variability / Feedstock and resource quality variability / Feedstock, Input, and Resource Quality Variability |
| 11/20 | 55% | Communication, latency, and connectivity failures / Communication and Latency Failures / Connectivity and Communication Infrastructure Failures |
| 11/20 | 55% | Network capacity and connection bottlenecks / Network Capacity, Hosting, and Connection Constraints / Network Capacity and Voltage Constraints |
| 10/20 | 50% | Model and Forecast Misspecification / Simulation and modelling fidelity gaps / Model, forecast, or simulation fidelity gap |
| 10/20 | 50% | Spatial, Geometric, and Site Constraints / Physical, spatial, and geometric constraints / Physical/thermal/spatial design limits and trade-offs |
| 10/20 | 50% | Component Integration and Interface Mismatch / Interoperability and Interface Standardisation Gaps / Interoperability and integration interface failure |
| 10/20 | 50% | Procurement, supply chain and logistics disruption / Supply chain, logistics, and global trade disruption / Supply Chain Disruption and Logistics |
| 10/20 | 50% | Workforce skills and capability shortage / Workforce Skills, Capability, and Capacity Gaps / Workforce, Skills, and Knowledge Capacity Gaps |
| 10/20 | 50% | Chicken-and-egg / coordination market failure / Chicken-and-egg and bootstrapping deadlocks / Chicken-and-egg coordination deadlock |
| 10/20 | 50% | Revenue and Value-Capture Mechanism Absent / Market price signal and revenue capture failure / Revenue Capture and Market Value Gaps |
| 10/20 | 50% | Vendor lock-in and proprietary closure / Vendor lock-in and proprietary access restriction / Vendor Lock-in and Proprietary Closure |
| 10/20 | 50% | Test, validation and commissioning coverage gaps / Test Coverage and Validation Method Gaps / Test, validation and commissioning gap |
| 9/20 | 45% | Environmental and weather exposure / Environmental and weather exposure damage / Environmental Stressor Damage to Assets |
| 9/20 | 45% | Data Quality, Integrity, and Pipeline Failures / Data quality, semantic, and integration defects / Data Quality, Format, and Schema Defects |
| 9/20 | 45% | Measurement and Sensing Limits / Measurement and Sensing Errors / Measurement instrument and sensing limitations |
| 9/20 | 45% | Project management, scope and planning failures / Project Scoping, Estimation, and Planning Defects / Governance, Scope, and Project Planning Failures |
| 9/20 | 45% | Hazard reclassification and safety-driven cost escalation / Hazard, Safety, and Risk-Profile Increases / Hazard, Safety, and Risk-Profile Constraints |

## Records-per-parent within-run distribution (exemplar-sum proxy)

Each parent has 3-5 exemplar clusters; sum of their `n_records` gives a proxy for the parent's population. The within-run *spread* of this measure tells us whether parents are population-balanced.

| metric | baseline 50-run (no constraint) | soft-balance 20-run (this run) | delta |
|---|---:|---:|---:|
| n_runs | 50 | 20 | -30 |
| mean_n_parents | 83 | 72.3 | -10.7 |
| mean_max_over_median | 1.42 | 1.41 | -0.01 |
| mean_records_per_parent_sd | 4.2 | 4.5 | +0.3 |
| mean_median_records | 20.6 | 24.1 | +3.5 |
| max_records_observed | 45 | 48 | +3 |
| min_records_observed | 3 | 6 | +3 |

**Reading:** if the soft-balance constraint bit, expect *mean_max_over_median* and *mean_records_per_parent_sd* to be notably lower in soft-balance vs baseline; expect *mean_n_parents* to shift modestly (toward fewer parents if the model dropped rare-narrow categories, toward more if it split broad ones). If the constraint was too soft to bite, all metrics within sampling noise of baseline.
