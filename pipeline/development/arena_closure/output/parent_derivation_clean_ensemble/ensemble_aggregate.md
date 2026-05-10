# Deliberation-rich parent-derivation ensemble — 59 reps

59 single-shot Opus 4.7 derivations from the 4,150 raw parent labels of the original 50-rep ensemble. Same prompt (parent_derivation_clean.md), same input. Apples-to-apples-or-better N vs the original 50-rep untargeted ensemble.

## Per-rep counts

| stat | n_parents | n_deliberated |
|---|---:|---:|
| min | 84 | 30 |
| max | 115 | 89 |
| mean | 97.4 | 49.7 |
| median | 98 | — |
| sd | 7.24 | 11.21 |
| p10 | 89 | — |
| p90 | 110 | — |

## Cross-rep tier distribution (Jaccard ≥0.30 on parent names)

**Distinct mechanism classes detected across 59 reps:** 298

| tier | n classes |
|---|---:|
| core_>=90% | 43 |
| high_70-89% | 28 |
| boundary_40-69% | 26 |
| rare_20-39% | 25 |
| singleton_<20% | 176 |

## Comparison vs original 50-rep untargeted ensemble

| | original (50 reps, untargeted prompt) | refined (this run, deliberation-rich) |
|---|---:|---:|
| n_parents per rep mean | 83.0 | 97.4 |
| n_parents per rep sd | 13.6 | 7.24 |
| core ≥90% Jaccard classes | 1 | 43 |
| high 70-89% | 3 | 28 |
| singleton <20% | 1104 | 176 |
| total distinct classes | 1206 | 298 |

## Top 50 most-recurring mechanism classes

| n_runs | freq | name(s) |
|---:|---:|---|
| 59 | 100% | Missing or inaccessible data / Missing or inaccessible data and documentation |
| 59 | 100% | Data quality, format and integration defects / Data quality, format, and integration defects / Data quality, format, and semantic defects / Data quality, format, and semantic integration defects / Dat |
| 59 | 100% | Measurement and sensing inadequacy / Measurement and sensing limitations / Measurement instrument and sensing limitations |
| 59 | 100% | Lab-to-field and pilot-to-scale translation failure / Pilot-to-scale and lab-to-field translation failure |
| 59 | 100% | Test, validation, and commissioning coverage gaps / Test, validation, and verification coverage gaps / Test, validation, and verification scope gaps / Test, validation, verification, and counterfactua |
| 59 | 100% | Material, chemical and physical-property limits / Material, chemical, and physical limits / Material, chemical, and physical property limits / Material, chemical, and physical-property limits / Materi |
| 59 | 100% | Equipment operating outside design envelope |
| 59 | 100% | Spatial, geometric and siting constraints / Spatial, geometric, and siting constraints |
| 59 | 100% | Environmental and external hazard exposure / Environmental and external-event exposure / Environmental and weather exposure / Environmental and weather exposure damage / Environmental and weather-driv |
| 59 | 100% | Capacity, sizing and headroom shortfalls / Capacity, sizing, and headroom inadequacy / Capacity, sizing, and headroom mismatch / Capacity, sizing, and headroom shortfall / Capacity, sizing, and headro |
| 59 | 100% | Inverter-based resource and grid stability dynamics / Inverter-based resource and grid stability interaction / Inverter-based resource and grid stability interactions / Inverter-based resource and gri |
| 59 | 100% | Configuration, parameter and commissioning errors / Control logic, configuration, and parameter errors / Control logic, configuration, and protection coordination errors / Control logic, configuration |
| 59 | 100% | Interface, protocol, and interoperability incompatibility / Interoperability and interface incompatibility / Interoperability, interface and standards incompatibility / Interoperability, interface, an |
| 59 | 100% | Cybersecurity and access control exposures / Cybersecurity and access-control exposure / Cybersecurity, authentication, and access control / Cybersecurity, authentication, and access-control / Cyberse |
| 59 | 100% | Manufacturing and fabrication defects / Manufacturing and fabrication variability / Manufacturing and fabrication variability and defects / Manufacturing variability and fabrication defects / Manufact |
| 59 | 100% | Coupled trade-off between competing service obligations / Coupled trade-offs and competing design objectives / Coupled trade-offs and competing objectives / Coupled trade-offs and competing optimisati |
| 59 | 100% | Regulatory framework absence or gap / Regulatory framework absence or gap for novel cases / Regulatory framework absence or gap for novel technology / Regulatory framework absence or gap for novelty / |
| 59 | 100% | Jurisdictional fragmentation and conflicting regulatory authority / Jurisdictional fragmentation and regulatory conflict / Regulatory ambiguity and jurisdictional fragmentation / Regulatory ambiguity, |
| 59 | 100% | Regulatory and approval process delay / Regulatory and approval process delay and friction / Regulatory and approval process delay and procedural friction / Regulatory and approval process latency and |
| 59 | 100% | Compliance burden and enforcement gaps / Compliance burden and verification disproportionality / Compliance enforcement and verification gaps / Compliance verification and enforcement gap / Compliance |
| 59 | 100% | Multi-party coordination and interface friction / Multi-party coordination and interface gaps / Multi-party coordination and responsibility gaps / Multi-party coordination and responsibility-allocatio |
| 59 | 100% | Vendor dependency and proprietary lock-in / Vendor dependency, lock-in, and proprietary closure / Vendor lock-in and proprietary closure |
| 59 | 100% | Supply chain and logistics disruption / Supply chain and procurement disruption / Supply chain availability and lead-time disruption / Supply chain disruption and lead-time exposure / Supply chain dis |
| 59 | 100% | Inadequate planning, scoping, and contingency / Project planning and scoping inadequacy / Project planning, scoping and contingency underestimation / Project planning, scoping, and contingency inadequ |
| 59 | 100% | Optimisation objective and metric design errors / Optimisation objective and metric misalignment / Optimisation objective and metric misspecification / Optimisation objective and metric-design misspec |
| 59 | 100% | Hard-to-abate decarbonisation residuals / Hard-to-abate emissions and decarbonisation residual / Hard-to-abate residual and decarbonisation ceiling / Hard-to-abate residual and decarbonisation ceiling |
| 59 | 100% | Funding instrument and milestone misfit / Funding instrument and milestone structural misfit / Funding instrument and milestone structure misfit / Funding instrument and milestone structure mismatch / |
| 58 | 98% | Capital cost and financing barriers / Capital cost and investment-return barriers / Capital cost and investment-threshold barriers / Capital cost and upfront investment barriers / Capital cost and upf |
| 58 | 98% | Volatile and external price exposure / Volatile or correlated input and output prices / Volatile or correlated input price exposure / Volatile or correlated input prices / Volatile or correlated input |
| 58 | 98% | Customer and participant recruitment and conversion shortfalls / Customer and participant recruitment shortfalls / Customer engagement, recruitment, and conversion shortfall / Customer engagement, rec |
| 58 | 98% | Information asymmetry and disclosure barriers / Information asymmetry and disclosure barriers between parties / Information asymmetry between actors / Information asymmetry between parties / Informati |
| 58 | 98% | Centralised single-point and shared-resource exposure / Centralised single-point-of-failure and shared-resource exposure / Single point of failure and common-mode dependency / Single point of failure  |
| 58 | 98% | Manual process and automation gap / Manual process and automation gaps / Manual process bottleneck and automation gap / Manual process bottlenecks and automation gap / Manual process bottlenecks and a |
| 57 | 97% | Model and forecast inaccuracy / Model and forecast representational error / Model and simulation representational error / Model, simulation, and forecast inaccuracy / Model, simulation, and forecast r |
| 57 | 97% | Personnel turnover and key-person dependency |
| 57 | 97% | Late discovery and design rework / Late discovery and design rework cascade / Late discovery and design rework cascades / Late discovery and design-rework cascade / Late discovery and design-rework ca |
| 56 | 95% | Heterogeneity defeating uniform design / Heterogeneity defeating uniform/standardised design / Heterogeneity defeats one-size-fits-all design / Heterogeneity defeats uniform design / Heterogeneity def |
| 55 | 93% | Geographic mismatch between resource and demand / Geographic mismatch between resource, demand, and infrastructure / Temporal and seasonal mismatch between supply and demand / Temporal and seasonal su |
| 55 | 93% | Policy and regulatory uncertainty deters commitment / Policy uncertainty and instability / Policy uncertainty and instability deter commitment / Policy uncertainty and instability deterring commitment |
| 55 | 93% | Chicken-and-egg and two-sided coordination deadlocks / Chicken-and-egg coordination deadlock / Chicken-and-egg coordination deadlocks / Chicken-and-egg deployment deadlocks / Multi-party coordination  |
| 55 | 93% | Fundamental mechanism understanding gap / Mechanism understanding and characterisation gap / Mechanism understanding and characterisation gaps / Mechanism understanding and reproducibility gap / Mecha |
| 55 | 93% | Aggregator and demand response delivery shortfall / Aggregator and demand-response delivery shortfall / Aggregator and demand-response delivery shortfalls / Aggregator/DER visibility, dispatch, and de |
| 54 | 92% | Misaligned incentives across actors / Misaligned incentives across decision-makers / Misaligned incentives across parties / Misaligned incentives and split benefits between actors / Misaligned incenti |
| 53 | 90% | Workforce skill, capability, and availability gaps / Workforce skill, capability, and capacity gaps / Workforce skill, capability, and capacity scarcity / Workforce skills and capability gaps / Workfo |
| 53 | 90% | Sample selection and representativeness bias / Sample, selection, and representativeness bias / Sample, selection, and self-selection bias / Sample, selection, and trial representativeness bias / Samp |
| 52 | 88% | Cost competitiveness and unit economics / Cost competitiveness and unit economics shortfall / Cost competitiveness and unit-economics gap / Cost exceeds threshold or unit-economics non-viability / Cos |
| 52 | 88% | Price signal absent, distorted or perverse / Price signal absent, distorted, or perverse / Price signals absent, distorted, or perverse |
| 52 | 88% | Contract scope, structure, and term misalignment / Contract structure and term inadequacy / Contract structure and term misalignment / Contract structure and term misfit / Contract structure and term  |
| 52 | 88% | Technology immaturity and TRL gap / Technology immaturity and first-of-kind execution / Technology immaturity and readiness gap / Technology immaturity and readiness gaps / Technology immaturity and u |
| 52 | 88% | Equity and distributional access barriers / Equity and distributional barriers / Equity and distributional outcomes / Equity, access, and distributional barriers / Equity, access, and distributional o |