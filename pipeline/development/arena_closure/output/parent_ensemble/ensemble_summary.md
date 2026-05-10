# Pass-1 Parent-Derivation Ensemble — 50-Run Summary

**Model:** `claude-opus-4-7`  |  **Prompt seed:** 42 (identical across all runs)  |  **Total cost:** $26.23 batch ($52.46 sync-equivalent)


## Granularity distribution (n_parents per run)

- min / mean / max: **52 / 83 / 115**
- sd: 13.6, p10/p50/p90: 64/84/100

## Coverage (n_unassigned per run, of 1,141 input clusters)

- min / mean / max: **4 / 10.72 / 37**
- sd: 6.1, p10/p50/p90: 6/9/17

## Mechanism-class frequency tiers (across 50 runs)

Distinct mechanism classes detected (Jaccard ≥ 0.30 grouping): **1206**

| Tier | n classes |
|---|---:|
| core_>=90% | 1 |
| high_70-89% | 3 |
| boundary_40-69% | 23 |
| rare_20-39% | 75 |
| singleton_<20% | 1104 |

## Union vocabulary size at minimum-runs threshold

| Min runs | n classes |
|---:|---:|
| ≥ 1 | 1206 |
| ≥ 5 | 229 |
| ≥ 10 | 102 |
| ≥ 25 | 15 |
| ≥ 45 | 1 |

## Top 30 most-frequent mechanism classes

| Runs | Frequency | Example labels |
|---:|---:|---|
| 49/50 | 98% | Missing or absent data and measurement / Missing or inaccessible data and metadata / Missing or inaccessible information at decision point |
| 44/50 | 88% | Multi-Party Coordination and Responsibility Gaps / Stakeholder coordination and multi-party alignment failure / Multi-party coordination and responsibility gaps |
| 40/50 | 80% | Physical material or chemical limits / Material, chemical and reaction limits / Material physical-property limits |
| 37/50 | 74% | Spatial, geographic and siting constraints / Spatial, geometric, and siting constraints / Geometric, spatial and structural constraints |
| 31/50 | 62% | Measurement instrument and sensing limits / Measurement and sensing limits / Measurement and sensing limitations |
| 30/50 | 60% | Tariff and price-signal design distortions / Price signal absence or distortion / Tariff, market, and price-signal misalignment |
| 29/50 | 58% | Regulatory delay and process friction / Regulatory process complexity and approval delay / Regulatory approval delay and process friction |
| 28/50 | 56% | Chicken-and-egg and coordinated-deployment deadlocks / Chicken-and-egg deployment deadlock / Chicken-and-egg coordination deadlocks |
| 28/50 | 56% | Compliance Verification and Enforcement Gaps / Compliance verification and enforcement gaps / Compliance enforcement and self-compliance reliance |
| 27/50 | 54% | Operating envelope mismatch between equipment and use / Equipment design-envelope and capability mismatch / Off-design operating conditions |
| 27/50 | 54% | Network capacity and hosting constraints / Network topology and capacity constraints / Network capacity and topology constraints |
| 27/50 | 54% | Regulatory framework absence or technology-novel gap / Regulatory and standards framework absence or obsolescence / Regulatory framework absence or gap |
| 26/50 | 52% | Demand-supply temporal misalignment / Temporal supply-demand mismatch / Temporal mismatch between supply and demand profiles |
| 26/50 | 52% | Regulatory framework misfit to current technology or scale / Regulatory framework gap or absence / Regulatory framework misfit with novel technology or actor |
| 25/50 | 50% | Inherent multi-objective trade-offs and coupled optimisation / Coupled trade-offs and optimisation conflicts / Coupled multi-objective optimisation conflicts |
| 24/50 | 48% | Supply chain, vendor, and logistics constraints / Supply-chain and procurement disruption / Supply chain and logistics disruption |
| 24/50 | 48% | Stakeholder/community engagement and social licence / Community engagement and social-licence breakdown / Community opposition and social licence |
| 23/50 | 46% | Trial and validation infrastructure gaps / Test and validation environment limitations / Test, validation, and verification gaps |
| 23/50 | 46% | Lab-to-scale process translation failure / Lab-to-scale translation gaps / Lab-to-field and scale-up translation failure |
| 23/50 | 46% | Regulatory ambiguity, conflict, or uncertainty / Regulatory ambiguity and jurisdictional overlap / Regulatory ambiguity, conflict, or jurisdictional overlap |
| 22/50 | 44% | Data quality, granularity, and metadata defects / Data quality, format, and integration defects / Data quality, schema and pipeline integrity |
| 22/50 | 44% | Self-selection / sampling bias / Self-selection and participation bias / Self-selection / participation bias degrading program outcomes |
| 22/50 | 44% | Data quality, format, and semantic mismatch / Data quality, semantic and format inconsistency / Data quality, format, or semantic integration failure |
| 21/50 | 42% | Capital cost and upfront economics / Capital cost and upfront investment barriers / Investment-return horizon and capital-structure barriers |
| 21/50 | 42% | Equipment design and capacity mismatch / Spec, capacity, or sizing shortfall / Asset sizing and capacity mismatch with demand |
| 20/50 | 40% | Fabrication and manufacturing defects / Manufacturing yield and fabrication-process defects / Process chemistry and feedstock variability |
| 20/50 | 40% | Misaligned incentives across actors / Incentive misalignment between actors / Knowledge asymmetry between actors |
| 19/50 | 38% | Model, forecast, and simulation fidelity gaps / Model and forecast representational inadequacy / Model and forecast representational error |
| 19/50 | 38% | Subsidy, incentive, and reward misalignment / Subsidy or incentive distortion / Policy instability and incentive-design distortion |
| 19/50 | 38% | End-of-life / degradation lifecycle gap / Lifecycle and end-of-life accounting gap / Lifecycle and end-of-life design inadequacy |