# Atomic Sub-Class Decomposition

Decomposes the 91 non-atomic canonical classes into atomic sub-classes,
using runs' own boundary choices as the source of within-class distinctions.
The 35 atomic canonical classes pass through unchanged.

Cost: $2.89, wall 720s, 243,478 in / 66,870 out tokens.

## Vocabulary expansion

| Stage | n classes |
|---|---:|
| Canonical (script 20) | 126 |
|   ├─ Atomic (pass through) | 35 |
|   └─ Non-atomic (decomposed) | 91 |
| Sub-classes produced from decomposition | 334 |
| **Total atomic vocabulary** | **369** |

Vocabulary growth factor: 2.93× over canonical 126.

## Frequency tiers (atomic vocabulary)

| Tier | n classes |
|---|---:|
| core_>=90% | 17 |
| high_70-89% | 27 |
| boundary_40-69% | 46 |
| rare_20-39% | 34 |
| singleton_<20% | 245 |

## Top decompositions (canonical classes split into the most sub-classes)

| Canonical | n_runs | n sub-classes | Names |
|---|---:|---:|---|
| **c61: Project planning, scoping, and contingency inadequacy** | 49 | 10 | Scope, schedule, budget, and contingency underestimation / Optimism bias in planning assumptions and benefit modelling / Premature commitment before sufficient maturity or scope definition / Project governance, methodology, and management practice deficits / Schedule pressure and contingency erosion / Operational expertise and routine maturity gaps / Stakeholder commitment instability (off-class) / Engineering scope and design freeze rework cascades / Subsidy/incentive program design defects (off-class) / Reactive policy formation (off-class) |
| **c43: Policy uncertainty and instability** | 46 | 9 | Policy uncertainty/instability deferring commitment / Reactive vs anticipatory governance and reform pace mismatch / Concurrent technology evolution / obsolescence risk / Regulatory process latency (off-class) / Multi-party coordination (off-class) / Lock-in / switching cost (off-class) / Jurisdictional fragmentation (off-class) / Legacy-system architecture incompatibility (off-class) / Forecast and price uncertainty exposure |
| **c24: Cost structure and unit-economics infeasibility** | 44 | 9 | Cost-competitiveness gap vs incumbent or threshold / Scale, fixed-cost amortisation, and utilisation diseconomy / Operating-cost burden and recurring-OPEX erosion / Cost-component dominance suppressing optimisation / Cost-exceeds-value or capital threshold breach / Tariff/price-signal misdesign (off-class) / Regulatory process latency (off-class) / Contract structure (off-class) / Volatile/correlated cost exposure |
| **c04: Model, simulation, and forecast inaccuracy** | 50 | 8 | Model assumption, parameterisation, and scope misspecification / Non-stationarity and structural-shift invalidation of calibrated models / Forecast error and predictive horizon limits / Idealised-foresight and design-assumption optimism / Modeller bias and causal confounding / Tool-output instability under inadequate input data / Misattribution and root-cause obscuring / Off-class data/measurement labels assigned here |
| **c44: Multi-party coordination overhead and responsibility gaps** | 49 | 8 | Multi-party coordination overhead and responsibility ambiguity / Strategic-coordination failure across actors and phases / Self-selection / participation bias / Insufficient demand or critical-mass deficit / Behavioural reluctance and trust barriers (off-class) / Architectural rigidity (off-class) / Workforce skills gaps (off-class) / Conservative design self-fulfilling (off-class) |
| **c09: Environmental and weather exposure** | 46 | 8 | Environmental, weather, and natural-event exposure damaging assets / Ambient atmospheric attenuation of physical signal / Reference/synchronisation drift (off-class) / Ecological/downstream side-effects of operation / Inverter-grid interaction (off-class) / Capacity-rating mismatch (off-class) / Operating envelope exceedance (off-class) / Coupled trade-offs (off-class) |
| **c79: Legacy infrastructure and architecture incompatibility** | 44 | 8 | Legacy/installed infrastructure incompatible with new requirements / Bidirectional / reverse-flow assumption breakage / Legacy market design / settlement systems mismatch / Hosted-system architectural philosophy mismatch / Communication channel / bandwidth (off-class) / Stale system state (off-class) / Coordination value-chain ecosystem failure (off-class) / Domain-specialised architectural mismatch (off-class) |
| **c20: Aggregate, correlation, and diversity-loss effects** | 42 | 8 | Aggregate correlation, synchronisation, and diversity-loss producing system stress / Uncoordinated independent decisions producing system effects / Race conditions and asynchronous control conflicts / Lock-in / commitment closing future options (off-class) / Inverter–grid interaction (off-class) / Operational variability/non-stationarity (off-class) / Maintenance / sustainment gaps (off-class) / Sample representativeness (off-class) |
| **c06: Material, chemical, and physical-property limits** | 50 | 7 | Material and chemical degradation or property limits / Thermal, pressure, and combustion process limits / Fundamental physical/thermodynamic efficiency ceilings / Containment, sealing, and ingress integrity / Mass-balance and weight-driven scaling penalties / Spatial/site geometric constraint mis-mapped here / Operating-envelope exceedance mis-mapped here |
| **c11: Control logic, configuration, and parameter errors** | 49 | 7 | Configuration, parameter, threshold, and setpoint errors / Control-loop instability, dynamic response, and tuning failure / Protection coordination and fault-handling miscoordination / Static or pre-computed limits inadequate for dynamic conditions / Latency, timing, and cadence mismatch in control / Emergency response and fallback inadequacy / Off-class labels assigned here |
| **c41: Test, validation, and verification coverage gaps** | 42 | 7 | Test/validation scope and coverage gap / Process by-product/contamination side-effect (off-class) / Tariff/incentive design failure (off-class) / Subsidy/procurement design distortions (off-class) / Compliance certification/standards-conformance gaps / Manufacturing/workmanship defect (off-class) / Market structure distortion (off-class) |
| **c46: Misaligned incentives between actors** | 41 | 7 | Split-incentive / principal-agent misalignment between cost-bearer and beneficiary / Pre-funding / uncompensated-effort burden / Multi-party coordination (off-class) / Behavioural responses (off-class) / Workforce/skills (off-class) / Procurement/tender pathology (off-class) / Personnel turnover (off-class) |
| **c10: Coupled trade-offs and competing optimisation objectives** | 49 | 6 | Coupled physical/design trade-offs preventing joint optimisation / Curtailment / dispatch-mode trade-off between competing services / Local-vs-system / component-vs-whole optimisation conflict / Process recycling and feedback-loop instability / Conservative-margin/oversizing overhead / Off-class labels assigned here |
| **c33: Chicken-and-egg coordination deadlocks** | 48 | 6 | Mutual-prerequisite deadlock between interdependent investments/parties / Cooperation withdrawal collapsing dependent value chain / Forecast skill / propagation (off-class) / Knowledge dissemination gap (off-class) / Behavioural rebound (off-class) / Procurement/competitive process design (off-class) |
| **c47: Contract structure and term misalignment** | 46 | 6 | Contract scope, term, rigidity, and risk-allocation misfit / Revenue/offtake structural barriers eroding contract economics / Investment risk and finance access (off-class) / Community/social licence (off-class) / Tariff/market-design (off-class) / Brownfield/retrofit constraints (off-class) |
| **c07: Equipment operating outside design envelope** | 40 | 6 | Operation beyond / off design envelope causing degradation or failure / Knowledge gaps in fundamental physical mechanisms (off-class) / Manufacturing yield (off-class) / Spatial/siting constraints (off-class) / Gaming / self-reporting integrity (off-class) / Latent constraint surfaces under new use (off-class) |
| **c70: Feedstock and input variability or quality** | 38 | 6 | Feedstock variability, contamination, and quality outside process tolerance / Process condition incompatibility between coupled steps / Auxiliary-load / parasitic loss (off-class) / Spatial/siting constraints (off-class) / Aggregation/diversity (off-class) / Control-system mismatch (off-class) |
| **c08: Spatial, geometric, and siting constraints** | 49 | 5 | Spatial, geometric, and footprint constraints on deployment / Land-use and resource-competition siting conflict / External weather/environmental events mis-mapped here / Equipment degradation/wear mis-mapped here / Process scale-up mis-mapped here |
| **c02: Data quality, format, and integration defects** | 47 | 5 | Data quality, format, schema, and semantic defects / Cross-system data synchronisation and provenance drift / Data infrastructure scaling and source-diversity limits / Communications/connectivity dependency (off-class) / Measurement/forecast inaccuracy mis-mapped here |
| **c31: Market structure and incumbent advantage** | 44 | 5 | Market concentration and incumbent structural advantage / Market design exclusion of novel actors / restricted value-stream access / Market thinness, liquidity, and bargaining-power limits / Investment / capital-access barriers (off-class) / Optimisation objective misspecification (off-class) |

## All atomic-vocabulary sub-classes (sorted by frequency)

| ID | Runs | Freq | Name | Parent canonical |
|---|---:|---:|---|---|
| c03.s1 | 49/50 | 98% | **Measurement instrument and sensing limitations** | Measurement and sensing limitations |
| c01.s1 | 49/50 | 98% | **Missing or inaccessible data, records, or documentation at point of need** | Missing or inaccessible data and documentation |
| c04.s1 | 48/50 | 96% | **Model assumption, parameterisation, and scope misspecification** | Model, simulation, and forecast inaccuracy |
| c08.s1 | 47/50 | 94% | **Spatial, geometric, and footprint constraints on deployment** | Spatial, geometric, and siting constraints |
| c14.s1 | 47/50 | 94% | **Inverter-based resource grid-interaction dynamics** | Inverter-based resource and grid stability dynamics |
| c37.s1 | 47/50 | 94% | **Regulatory/approval process latency and procedural friction** | Regulatory process delay and procedural friction |
| c33.s1 | 47/50 | 94% | **Mutual-prerequisite deadlock between interdependent investments/parties** | Chicken-and-egg coordination deadlocks |
| c50.s1 | 47/50 | 94% | **Supply chain disruption, lead time, and logistics for inputs** | Supply chain and logistics disruption |
| c51.s1 | 47/50 | 94% | **Specialist skills, training, and labour-market shortage** | Workforce skills and capability shortage |
| c44.s1 | 46/50 | 92% | **Multi-party coordination overhead and responsibility ambiguity** | Multi-party coordination overhead and responsibility gaps |
| c58.s1 | 46/50 | 92% | **Recruitment, conversion, and onboarding-funnel friction** | Customer recruitment, conversion, and retention shortfalls |
| c13.s1 | 46/50 | 92% | **Interface, protocol, API, and data-exchange incompatibility** | Interoperability and interface incompatibility |
| c06.s1 | 45/50 | 90% | **Material and chemical degradation or property limits** | Material, chemical, and physical-property limits |
| c05.s1 | 45/50 | 90% | **Lab/pilot-to-field translation failure** | Lab-to-field and pilot-to-scale translation failure |
| c02.s1 | 45/50 | 90% | **Data quality, format, schema, and semantic defects** | Data quality, format, and integration defects |
| c75.s1 | 45/50 | 90% | **Cybersecurity, authentication, and access-control architecture risk or friction** | Cybersecurity and access-control exposure |
| c53.s1 | 45/50 | 90% | **Knowledge transfer and institutional memory failure** | Knowledge transfer and institutional memory loss |
| c10.s1 | 44/50 | 88% | **Coupled physical/design trade-offs preventing joint optimisation** | Coupled trade-offs and competing optimisation objectives |
| c09.s1 | 44/50 | 88% | **Environmental, weather, and natural-event exposure damaging assets** | Environmental and weather exposure |
| c62.s1 | 44/50 | 88% | **Sequential dependency cascade amplifying upstream delay** | Schedule cascade and dependency delays |
| c61.s1 | 43/50 | 86% | **Scope, schedule, budget, and contingency underestimation** | Project planning, scoping, and contingency inadequacy |
| c43.s1 | 43/50 | 86% | **Policy uncertainty/instability deferring commitment** | Policy uncertainty and instability |
| c59.s1 | 43/50 | 86% | **Behavioural intent-action gap and motivation/inertia barriers** | Customer behavioural and motivation barriers |
| c47.s1 | 42/50 | 84% | **Contract scope, term, rigidity, and risk-allocation misfit** | Contract structure and term misalignment |
| c34.s1 | 42/50 | 84% | **Absent or paradigm-misfit regulatory framework for novel technology/actor** | Regulatory framework gap or absence |
| c07.s1 | 42/50 | 84% | **Operation beyond / off design envelope causing degradation or failure** | Equipment operating outside design envelope |
| c15.s1 | 41/50 | 82% | **Electrical network transfer/hosting capacity constraints** | Network capacity and hosting constraints |
| c79.s1 | 40/50 | 80% | **Legacy/installed infrastructure incompatible with new requirements** | Legacy infrastructure and architecture incompatibility |
| c36.s1 | 40/50 | 80% | **Cross-jurisdictional and inter-authority conflict, overlap, or ambiguity** | Regulatory ambiguity, fragmentation, and jurisdictional conf |
| c46.s1 | 40/50 | 80% | **Split-incentive / principal-agent misalignment between cost-bearer and beneficiary** | Misaligned incentives between actors |
| c20.s1 | 39/50 | 78% | **Aggregate correlation, synchronisation, and diversity-loss producing system stress** | Aggregate, correlation, and diversity-loss effects |
| c29 | 38/50 | 76% | **Subsidy and incentive design distortions** | (atomic pass-through) |
| c17.s1 | 38/50 | 76% | **Asset capacity, rating, or headroom insufficient for duty** | Capacity, sizing, and headroom shortfalls |
| c76.s1 | 38/50 | 76% | **Software/firmware defects, capability gaps, and maintenance burden** | Software, firmware, and IT system fragility |
| c55.s1 | 37/50 | 74% | **Engagement timing, depth, and design failures** | Stakeholder engagement and consultation failures |
| c86.s1 | 37/50 | 74% | **Externality, lifecycle, or accounting boundary omission** | Externalities and lifecycle accounting omissions |
| c77 | 36/50 | 72% | **Communications and connectivity failures** | (atomic pass-through) |
| c11.s1 | 36/50 | 72% | **Configuration, parameter, threshold, and setpoint errors** | Control logic, configuration, and parameter errors |
| c41.s1 | 36/50 | 72% | **Test/validation scope and coverage gap** | Test, validation, and verification coverage gaps |
| c70.s1 | 36/50 | 72% | **Feedstock variability, contamination, and quality outside process tolerance** | Feedstock and input variability or quality |
| c81.s1 | 36/50 | 72% | **Technology readiness, track-record, and ecosystem-maturity gap** | Technology readiness and maturity gap |
| c27.s1 | 35/50 | 70% | **Risk-perception, return-horizon, and financing-instrument mismatch** | Investment risk and financing barriers |
| c30.s1 | 35/50 | 70% | **Tariff/price-signal/settlement design producing perverse incentive** | Tariff and price-signal design distortions |
| c89.s1 | 35/50 | 70% | **Novel hazard classification triggering safety-driven redesign or restriction** | Safety hazard and risk classification escalation |
| c32.s1 | 34/50 | 68% | **Lock-in / sunk-cost / switching-cost barrier blocking adoption** | Incumbent lock-in and switching cost barriers |
| c49.s1 | 34/50 | 68% | **Proprietary closure / vendor lock-in blocking third-party action** | Vendor lock-in and proprietary closure |
| c67.s1 | 34/50 | 68% | **Fabrication, manufacturing, and assembly defects or yield loss** | Manufacturing variability and fabrication defects |
| c16 | 33/50 | 66% | **Temporal mismatch between supply and demand** | (atomic pass-through) |
| c31.s1 | 33/50 | 66% | **Market concentration and incumbent structural advantage** | Market structure and incumbent advantage |
| c12.s1 | 33/50 | 66% | **Control/data-system cadence, latency, and timing mismatch** | Cadence, latency, and timing mismatches |
| c22.s1 | 33/50 | 66% | **Aggregate-vs-individual visibility/control gap and granularity loss** | Aggregation and granularity mismatch |
| c26.s1 | 32/50 | 64% | **Absent revenue/value-capture mechanism for delivered service** | Value not captured by available market mechanisms |
| c35 | 31/50 | 62% | **Regulatory framework misfit or obsolescence** | (atomic pass-through) |
| c85.s1 | 31/50 | 62% | **Conservative-margin / risk-averse over-specification overhead** | Conservative margin and over-specification bias |
| c104.s1 | 31/50 | 62% | **Funding-instrument and milestone-structure mismatch with project work** | Funding instrument and milestone design misfit |
| c60.s1 | 30/50 | 60% | **Behavioural rebound and compensating user response** | Behavioural rebound and unintended response |
| c90.s1 | 30/50 | 60% | **Self-selection and sample-representativeness bias** | Sample, selection, and representativeness bias |
| c105.s1 | 30/50 | 60% | **Internal organisational change-cycle and governance friction** | Organisational governance and process inertia |
| c21.s1 | 28/50 | 56% | **Heterogeneity defeats one-size-fits-all design** | Heterogeneity defeats uniform design |
| c78.s1 | 28/50 | 56% | **Single-point/common-mode dependency cascading across dependents** | Single point of failure and common-mode dependency |
| c63.s1 | 28/50 | 56% | **Late discovery of constraints/conditions forcing rework after commitment** | Late discovery forcing rework |
| c87.s1 | 28/50 | 56% | **End-of-life, recycling, disposal, and lifecycle pathway absent or inadequate** | Lifecycle and end-of-life pathway gaps |
| c45 | 27/50 | 54% | **Responsibility, ownership, and accountability gaps** | (atomic pass-through) |
| c96.s1 | 27/50 | 54% | **Forecast skill ceilings and predictability limits** | Forecast uncertainty and actionability limits |
| c40.s1 | 27/50 | 54% | **Unenforced or unverifiable compliance with existing rule** | Compliance enforcement and verification gaps |
| c106.s1 | 27/50 | 54% | **Manual-process bottleneck and automation gap** | Manual processes and automation gaps |
| c48.s1 | 26/50 | 52% | **Procurement/tender process design producing suboptimal supplier outcomes** | Procurement and tendering process distortions |
| c80.s1 | 26/50 | 52% | **Architectural coupling, monolithic design, and modularity absence preventing incremental change** | Architectural rigidity and modularity limits |
| c19.s1 | 26/50 | 52% | **Geographic separation between resource and demand imposing transport/transmission cost** | Geographic and locational mismatch |
| c68 | 25/50 | 50% | **Equipment degradation, wear, and ageing** | (atomic pass-through) |
| c24.s1 | 25/50 | 50% | **Cost-competitiveness gap vs incumbent or threshold** | Cost structure and unit-economics infeasibility |
| c42.s1 | 25/50 | 50% | **Standard absence, obsolescence, or scope mismatch with deployment** | Standards mismatch, obsolescence, or absence |
| c18 | 24/50 | 48% | **Resource intermittency and variability** | (atomic pass-through) |
| c56.s1 | 24/50 | 48% | **Trust, perception, and social-licence withholding adoption** | Trust, perception, and social licence barriers |
| c95.s1 | 24/50 | 48% | **Information asymmetry distorting transactions or coordination** | Information asymmetry between parties |
| c52 | 23/50 | 46% | **Personnel turnover and key-person dependency** | (atomic pass-through) |
| c91.s1 | 23/50 | 46% | **Trial duration, scope, and representativeness limitations** | Trial design and validation infrastructure limitations |
| c84.s1 | 23/50 | 46% | **Auxiliary, balance-of-system, and parasitic consumption eroding net output** | Auxiliary load and parasitic consumption |
| c92.s1 | 23/50 | 46% | **Counterfactual, baseline, and attribution measurement difficulty** | Counterfactual and baseline measurement difficulty |
| c113.s1 | 23/50 | 46% | **Stakeholder expectation divergence and commitment instability** | Stakeholder alignment and expectation divergence |
| c23.s1 | 23/50 | 46% | **Upfront capital cost / payback threshold barrier** | Capital cost and upfront investment barriers |
| c28 | 22/50 | 44% | **Volatile or correlated input price exposure** | (atomic pass-through) |
| c83 | 21/50 | 42% | **Mechanism understanding and scientific knowledge gap** | (atomic pass-through) |
| c88 | 21/50 | 42% | **Hard-to-abate residual emissions** | (atomic pass-through) |
| c38.s1 | 21/50 | 42% | **Regulatory/settlement metric or methodology producing perverse outcomes** | Regulatory metric and methodology design flaws |
| c97.s1 | 21/50 | 42% | **Forced curtailment and operational headroom loss** | Curtailment and headroom-driven output loss |
| c93.s1 | 21/50 | 42% | **Optimisation objective, metric, or scoring misalignment with system goal** | Optimisation objective misspecification |
| c109.s1 | 21/50 | 42% | **Unintended secondary effect or emergent failure mode from intervention** | Unintended secondary consequences |
| c57 | 20/50 | 40% | **Community opposition and social licence** | (atomic pass-through) |
| c107.s1 | 20/50 | 40% | **Asset-lifetime / commitment-horizon mismatch and stranded-asset risk** | Long-horizon commitment and stranded asset risk |
| c101.s1 | 19/50 | 38% | **Inertia, system strength, and synchronous-service shortfall as fleet displaces** | System inertia and synchronous-service shortfall |
| c99 | 18/50 | 36% | **Demand response and aggregator delivery shortfall** | (atomic pass-through) |
| c98.s1 | 18/50 | 36% | **Operator/system visibility and observability shortfalls for distributed assets** | Visibility, observability, and monitoring gaps |
| c69.s1 | 18/50 | 36% | **Latent defect surfaced under operation, integration, or commissioning** | Latent defects revealed in operation |
| c25 | 17/50 | 34% | **Price signal absent, distorted, or perverse** | (atomic pass-through) |
| c74 | 17/50 | 34% | **Subsurface and reservoir characterisation uncertainty** | (atomic pass-through) |
| c82 | 17/50 | 34% | **First-of-kind execution and precedent absence** | (atomic pass-through) |
| c115 | 17/50 | 34% | **Standardisation absence forcing bespoke effort** | (atomic pass-through) |
| c31.s2 | 17/50 | 34% | **Market design exclusion of novel actors / restricted value-stream access** | Market structure and incumbent advantage |
| c54.s1 | 17/50 | 34% | **Documentation, version-control, and configuration-management drift** | Documentation and configuration management gaps |
| c24.s2 | 16/50 | 32% | **Scale, fixed-cost amortisation, and utilisation diseconomy** | Cost structure and unit-economics infeasibility |
| c108.s1 | 16/50 | 32% | **Exogenous shock, pandemic, geopolitical, or industrial-action disruption** | External shocks and force-majeure disruption |
| c50.s2 | 15/50 | 30% | **Vendor / counterparty / contractor capability or viability failure** | Supply chain and logistics disruption |
| c39.s1 | 15/50 | 30% | **Fixed compliance/administrative cost disproportionate to activity scale** | Compliance burden disproportionate to scale |
| c64.s1 | 15/50 | 30% | **Mid-project scope/requirement/specification change invalidating prior work** | Scope change and rework cascades |
| c66 | 14/50 | 28% | **Site-specific physical conditions discovered late** | (atomic pass-through) |
| c72 | 14/50 | 28% | **Process by-product, contamination, and fouling** | (atomic pass-through) |
| c103 | 14/50 | 28% | **Diminishing returns and saturation effects** | (atomic pass-through) |
| c06.s2 | 14/50 | 28% | **Thermal, pressure, and combustion process limits** | Material, chemical, and physical-property limits |
| c91.s2 | 14/50 | 28% | **Validation method circularity, proxy substitution, or independence absence** | Trial design and validation infrastructure limitations |
| c71.s1 | 14/50 | 28% | **Reaction kinetics, catalyst, and conversion-pathway limits** | Process chemistry and conversion limits |
| c65 | 13/50 | 26% | **Commissioning and handover defects** | (atomic pass-through) |
| c111 | 13/50 | 26% | **Equity and distributional barriers** | (atomic pass-through) |
| c120 | 13/50 | 26% | **Maintenance, access, and serviceability constraints** | (atomic pass-through) |
| c11.s2 | 13/50 | 26% | **Control-loop instability, dynamic response, and tuning failure** | Control logic, configuration, and parameter errors |
| c117.s1 | 13/50 | 26% | **Co-located/concurrent asset interaction and shared-resource contention** | Co-located asset interaction and shared-resource contention |
| c122.s1 | 13/50 | 26% | **Discrete threshold, eligibility cliff, or sizing-step exclusion** | Stranded value and discrete-threshold/eligibility exclusion |
| c114 | 12/50 | 24% | **Computational and algorithmic tractability limits** | (atomic pass-through) |
| c04.s2 | 12/50 | 24% | **Non-stationarity and structural-shift invalidation of calibrated models** | Model, simulation, and forecast inaccuracy |
| c55.s2 | 12/50 | 24% | **Communication content, channel, and language mismatch** | Stakeholder engagement and consultation failures |
| c116.s1 | 11/50 | 22% | **Iterative design rework triggered by mid-process change or late information** | Iterative rework and design churn |
| c73 | 10/50 | 20% | **Resource depletion and natural-resource availability** | (atomic pass-through) |
| c94 | 10/50 | 20% | **Performance metric and benchmark design flaws** | (atomic pass-through) |
| c112 | 10/50 | 20% | **Confidentiality and data-sharing barriers** | (atomic pass-through) |
| c43.s2 | 9/50 | 18% | **Reactive vs anticipatory governance and reform pace mismatch** | Policy uncertainty and instability |
| c100.s1 | 9/50 | 18% | **Cumulative or compounding small effects across pipeline/system** | Cumulative compounding and small-effect aggregation |
| c102 | 8/50 | 16% | **Rare-event and tail-condition exposure** | (atomic pass-through) |
| c110 | 8/50 | 16% | **Self-reporting, gaming, and verification weakness** | (atomic pass-through) |
| c119 | 8/50 | 16% | **Emerging technology demand-side and ecosystem immaturity** | (atomic pass-through) |
| c59.s2 | 8/50 | 16% | **User control aversion and override of automated dispatch** | Customer behavioural and motivation barriers |
| c125 | 7/50 | 14% | **Insurance and risk-transfer market gaps** | (atomic pass-through) |
| c06.s3 | 7/50 | 14% | **Fundamental physical/thermodynamic efficiency ceilings** | Material, chemical, and physical-property limits |
| c11.s3 | 7/50 | 14% | **Protection coordination and fault-handling miscoordination** | Control logic, configuration, and parameter errors |
| c24.s5 | 7/50 | 14% | **Cost-exceeds-value or capital threshold breach** | Cost structure and unit-economics infeasibility |
| c121.s1 | 7/50 | 14% | **Self-defeating complexity / recursive inefficiency from added components** | Conservative-design self-defeating overspecification |
| c05.s2 | 6/50 | 12% | **Site-specific non-transferability** | Lab-to-field and pilot-to-scale translation failure |
| c118 | 5/50 | 10% | **Inverter capacity allocation conflicts** | (atomic pass-through) |
| c05.s4 | 5/50 | 10% | **Off-class labels assigned here** | Lab-to-field and pilot-to-scale translation failure |
| c61.s4 | 5/50 | 10% | **Project governance, methodology, and management practice deficits** | Project planning, scoping, and contingency inadequacy |
| c79.s2 | 5/50 | 10% | **Bidirectional / reverse-flow assumption breakage** | Legacy infrastructure and architecture incompatibility |
| c91.s3 | 5/50 | 10% | **Test-coverage scope/methodology gap** | Trial design and validation infrastructure limitations |
| c96.s2 | 5/50 | 10% | **Forecast actionability gap (information available but not actionable)** | Forecast uncertainty and actionability limits |
| c123 | 4/50 | 8% | **Coordinated-control granularity and addressing limits** | (atomic pass-through) |
| c14.s2 | 4/50 | 8% | **Voltage, harmonic, and power-quality disturbance propagation** | Inverter-based resource and grid stability dynamics |
| c61.s3 | 4/50 | 8% | **Premature commitment before sufficient maturity or scope definition** | Project planning, scoping, and contingency inadequacy |
| c51.s2 | 4/50 | 8% | **Volunteer/unpaid-labour exhaustion** | Workforce skills and capability shortage |
| c58.s3 | 4/50 | 8% | **Participant attrition and engagement decay over time** | Customer recruitment, conversion, and retention shortfalls |
| c20.s2 | 4/50 | 8% | **Uncoordinated independent decisions producing system effects** | Aggregate, correlation, and diversity-loss effects |
| c98.s2 | 4/50 | 8% | **Diagnostic opacity and root-cause attribution failure** | Visibility, observability, and monitoring gaps |
| c124 | 3/50 | 6% | **Pre-existing/concurrent activity interference** | (atomic pass-through) |
| c04.s4 | 3/50 | 6% | **Idealised-foresight and design-assumption optimism** | Model, simulation, and forecast inaccuracy |
| c10.s2 | 3/50 | 6% | **Curtailment / dispatch-mode trade-off between competing services** | Coupled trade-offs and competing optimisation objectives |
| c10.s3 | 3/50 | 6% | **Local-vs-system / component-vs-whole optimisation conflict** | Coupled trade-offs and competing optimisation objectives |
| c11.s5 | 3/50 | 6% | **Latency, timing, and cadence mismatch in control** | Control logic, configuration, and parameter errors |
| c11.s7 | 3/50 | 6% | **Off-class labels assigned here** | Control logic, configuration, and parameter errors |
| c61.s2 | 3/50 | 6% | **Optimism bias in planning assumptions and benefit modelling** | Project planning, scoping, and contingency inadequacy |
| c71.s2 | 3/50 | 6% | **Process recycling and stream-coupling instability** | Process chemistry and conversion limits |
| c100.s2 | 3/50 | 6% | **Demand growth offsetting renewable/efficiency additions** | Cumulative compounding and small-effect aggregation |
| c04.s8 | 2/50 | 4% | **Off-class data/measurement labels assigned here** | Model, simulation, and forecast inaccuracy |
| c06.s5 | 2/50 | 4% | **Mass-balance and weight-driven scaling penalties** | Material, chemical, and physical-property limits |
| c05.s3 | 2/50 | 4% | **Physical scale-up penalties and reactor-size limits** | Lab-to-field and pilot-to-scale translation failure |
| c08.s2 | 2/50 | 4% | **Land-use and resource-competition siting conflict** | Spatial, geometric, and siting constraints |
| c10.s6 | 2/50 | 4% | **Off-class labels assigned here** | Coupled trade-offs and competing optimisation objectives |
| c11.s4 | 2/50 | 4% | **Static or pre-computed limits inadequate for dynamic conditions** | Control logic, configuration, and parameter errors |
| c14.s3 | 2/50 | 4% | **Inverter / IBR functional capability gap** | Inverter-based resource and grid stability dynamics |
| c14.s4 | 2/50 | 4% | **Off-class labels assigned here** | Inverter-based resource and grid stability dynamics |
| c61.s5 | 2/50 | 4% | **Schedule pressure and contingency erosion** | Project planning, scoping, and contingency inadequacy |
| c58.s2 | 2/50 | 4% | **Eligibility / addressable-market structural exclusion** | Customer recruitment, conversion, and retention shortfalls |
| c58.s4 | 2/50 | 4% | **Scope-reduction / standards specification (off-class)** | Customer recruitment, conversion, and retention shortfalls |
| c02.s3 | 2/50 | 4% | **Data infrastructure scaling and source-diversity limits** | Data quality, format, and integration defects |
| c02.s5 | 2/50 | 4% | **Measurement/forecast inaccuracy mis-mapped here** | Data quality, format, and integration defects |
| c75.s3 | 2/50 | 4% | **Operating envelope / investment risk (off-class)** | Cybersecurity and access-control exposure |
| c34.s2 | 2/50 | 4% | **Contract structure (off-class)** | Regulatory framework gap or absence |
| c31.s3 | 2/50 | 4% | **Market thinness, liquidity, and bargaining-power limits** | Market structure and incumbent advantage |
| c59.s3 | 2/50 | 4% | **Engagement design / customer-recruitment misfire (off-class)** | Customer behavioural and motivation barriers |
| c79.s3 | 2/50 | 4% | **Legacy market design / settlement systems mismatch** | Legacy infrastructure and architecture incompatibility |
| c56.s2 | 2/50 | 4% | **Behavioural friction (off-class)** | Trust, perception, and social licence barriers |
| c97.s2 | 2/50 | 4% | **Curtailment-induced measurement and metric bias** | Curtailment and headroom-driven output loss |
| c108.s2 | 2/50 | 4% | **Safety event triggering precautionary fleet restriction** | External shocks and force-majeure disruption |
| c108.s3 | 2/50 | 4% | **Crowding-out / competing-priority displacement** | External shocks and force-majeure disruption |
| c03.s2 | 1/50 | 2% | **Alarm and diagnostic signal-to-noise degradation** | Measurement and sensing limitations |
| c03.s3 | 1/50 | 2% | **Model/forecast inaccuracy mis-mapped to sensing class** | Measurement and sensing limitations |
| c04.s3 | 1/50 | 2% | **Forecast error and predictive horizon limits** | Model, simulation, and forecast inaccuracy |
| c04.s5 | 1/50 | 2% | **Modeller bias and causal confounding** | Model, simulation, and forecast inaccuracy |
| c04.s6 | 1/50 | 2% | **Tool-output instability under inadequate input data** | Model, simulation, and forecast inaccuracy |
| c04.s7 | 1/50 | 2% | **Misattribution and root-cause obscuring** | Model, simulation, and forecast inaccuracy |
| c06.s4 | 1/50 | 2% | **Containment, sealing, and ingress integrity** | Material, chemical, and physical-property limits |
| c06.s6 | 1/50 | 2% | **Spatial/site geometric constraint mis-mapped here** | Material, chemical, and physical-property limits |
| c06.s7 | 1/50 | 2% | **Operating-envelope exceedance mis-mapped here** | Material, chemical, and physical-property limits |
| c01.s2 | 1/50 | 2% | **Aggregation and discoverability of dispersed information** | Missing or inaccessible data and documentation |
| c08.s3 | 1/50 | 2% | **External weather/environmental events mis-mapped here** | Spatial, geometric, and siting constraints |
| c08.s4 | 1/50 | 2% | **Equipment degradation/wear mis-mapped here** | Spatial, geometric, and siting constraints |
| c08.s5 | 1/50 | 2% | **Process scale-up mis-mapped here** | Spatial, geometric, and siting constraints |
| c10.s4 | 1/50 | 2% | **Process recycling and feedback-loop instability** | Coupled trade-offs and competing optimisation objectives |
| c10.s5 | 1/50 | 2% | **Conservative-margin/oversizing overhead** | Coupled trade-offs and competing optimisation objectives |
| c11.s6 | 1/50 | 2% | **Emergency response and fallback inadequacy** | Control logic, configuration, and parameter errors |
| c37.s2 | 1/50 | 2% | **Regulatory ambiguity, jurisdictional conflict, or authority gap** | Regulatory process delay and procedural friction |
| c37.s3 | 1/50 | 2% | **Schedule cascade and dependency-driven delay (off-class)** | Regulatory process delay and procedural friction |
| c37.s4 | 1/50 | 2% | **Perverse regulatory/incentive metric (off-class)** | Regulatory process delay and procedural friction |
| c44.s2 | 1/50 | 2% | **Strategic-coordination failure across actors and phases** | Multi-party coordination overhead and responsibility gaps |
| c44.s3 | 1/50 | 2% | **Self-selection / participation bias** | Multi-party coordination overhead and responsibility gaps |
| c44.s4 | 1/50 | 2% | **Insufficient demand or critical-mass deficit** | Multi-party coordination overhead and responsibility gaps |
| c44.s5 | 1/50 | 2% | **Behavioural reluctance and trust barriers (off-class)** | Multi-party coordination overhead and responsibility gaps |
| c44.s6 | 1/50 | 2% | **Architectural rigidity (off-class)** | Multi-party coordination overhead and responsibility gaps |
| c44.s7 | 1/50 | 2% | **Workforce skills gaps (off-class)** | Multi-party coordination overhead and responsibility gaps |
| c44.s8 | 1/50 | 2% | **Conservative design self-fulfilling (off-class)** | Multi-party coordination overhead and responsibility gaps |
| c61.s6 | 1/50 | 2% | **Operational expertise and routine maturity gaps** | Project planning, scoping, and contingency inadequacy |
| c61.s7 | 1/50 | 2% | **Stakeholder commitment instability (off-class)** | Project planning, scoping, and contingency inadequacy |
| c61.s8 | 1/50 | 2% | **Engineering scope and design freeze rework cascades** | Project planning, scoping, and contingency inadequacy |
| c61.s9 | 1/50 | 2% | **Subsidy/incentive program design defects (off-class)** | Project planning, scoping, and contingency inadequacy |
| c61.s10 | 1/50 | 2% | **Reactive policy formation (off-class)** | Project planning, scoping, and contingency inadequacy |
| c33.s2 | 1/50 | 2% | **Cooperation withdrawal collapsing dependent value chain** | Chicken-and-egg coordination deadlocks |
| c33.s3 | 1/50 | 2% | **Forecast skill / propagation (off-class)** | Chicken-and-egg coordination deadlocks |
| c33.s4 | 1/50 | 2% | **Knowledge dissemination gap (off-class)** | Chicken-and-egg coordination deadlocks |
| c33.s5 | 1/50 | 2% | **Behavioural rebound (off-class)** | Chicken-and-egg coordination deadlocks |
| c33.s6 | 1/50 | 2% | **Procurement/competitive process design (off-class)** | Chicken-and-egg coordination deadlocks |
| c50.s3 | 1/50 | 2% | **Heterogeneity defeats one-size-fits-all (off-class)** | Supply chain and logistics disruption |
| c51.s3 | 1/50 | 2% | **Sequential schedule cascade (off-class)** | Workforce skills and capability shortage |
| c51.s4 | 1/50 | 2% | **Commissioning-revealed defect (off-class)** | Workforce skills and capability shortage |
| c02.s2 | 1/50 | 2% | **Cross-system data synchronisation and provenance drift** | Data quality, format, and integration defects |
| c02.s4 | 1/50 | 2% | **Communications/connectivity dependency (off-class)** | Data quality, format, and integration defects |
| c75.s2 | 1/50 | 2% | **System integration / architectural coupling (off-class)** | Cybersecurity and access-control exposure |
| c09.s2 | 1/50 | 2% | **Ambient atmospheric attenuation of physical signal** | Environmental and weather exposure |
| c09.s3 | 1/50 | 2% | **Reference/synchronisation drift (off-class)** | Environmental and weather exposure |
| c09.s4 | 1/50 | 2% | **Ecological/downstream side-effects of operation** | Environmental and weather exposure |
| c09.s5 | 1/50 | 2% | **Inverter-grid interaction (off-class)** | Environmental and weather exposure |
| c09.s6 | 1/50 | 2% | **Capacity-rating mismatch (off-class)** | Environmental and weather exposure |
| c09.s7 | 1/50 | 2% | **Operating envelope exceedance (off-class)** | Environmental and weather exposure |
| c09.s8 | 1/50 | 2% | **Coupled trade-offs (off-class)** | Environmental and weather exposure |
| c13.s2 | 1/50 | 2% | **Off-class price/market signal label** | Interoperability and interface incompatibility |
| c43.s3 | 1/50 | 2% | **Concurrent technology evolution / obsolescence risk** | Policy uncertainty and instability |
| c43.s4 | 1/50 | 2% | **Regulatory process latency (off-class)** | Policy uncertainty and instability |
| c43.s5 | 1/50 | 2% | **Multi-party coordination (off-class)** | Policy uncertainty and instability |
| c43.s6 | 1/50 | 2% | **Lock-in / switching cost (off-class)** | Policy uncertainty and instability |
| c43.s7 | 1/50 | 2% | **Jurisdictional fragmentation (off-class)** | Policy uncertainty and instability |
| c43.s8 | 1/50 | 2% | **Legacy-system architecture incompatibility (off-class)** | Policy uncertainty and instability |
| c43.s9 | 1/50 | 2% | **Forecast and price uncertainty exposure** | Policy uncertainty and instability |
| c47.s2 | 1/50 | 2% | **Revenue/offtake structural barriers eroding contract economics** | Contract structure and term misalignment |
| c47.s3 | 1/50 | 2% | **Investment risk and finance access (off-class)** | Contract structure and term misalignment |
| c47.s4 | 1/50 | 2% | **Community/social licence (off-class)** | Contract structure and term misalignment |
| c47.s5 | 1/50 | 2% | **Tariff/market-design (off-class)** | Contract structure and term misalignment |
| c47.s6 | 1/50 | 2% | **Brownfield/retrofit constraints (off-class)** | Contract structure and term misalignment |
| c53.s2 | 1/50 | 2% | **Operating-mode/transient regime gaps (off-class)** | Knowledge transfer and institutional memory loss |
| c53.s3 | 1/50 | 2% | **Operating-envelope exceedance (off-class)** | Knowledge transfer and institutional memory loss |
| c34.s3 | 1/50 | 2% | **Cybersecurity (off-class)** | Regulatory framework gap or absence |
| c34.s4 | 1/50 | 2% | **Investment uncertainty (off-class)** | Regulatory framework gap or absence |
| c24.s3 | 1/50 | 2% | **Operating-cost burden and recurring-OPEX erosion** | Cost structure and unit-economics infeasibility |
| c24.s4 | 1/50 | 2% | **Cost-component dominance suppressing optimisation** | Cost structure and unit-economics infeasibility |
| c24.s6 | 1/50 | 2% | **Tariff/price-signal misdesign (off-class)** | Cost structure and unit-economics infeasibility |
| c24.s7 | 1/50 | 2% | **Regulatory process latency (off-class)** | Cost structure and unit-economics infeasibility |
| c24.s8 | 1/50 | 2% | **Contract structure (off-class)** | Cost structure and unit-economics infeasibility |
| c24.s9 | 1/50 | 2% | **Volatile/correlated cost exposure** | Cost structure and unit-economics infeasibility |
| c31.s4 | 1/50 | 2% | **Investment / capital-access barriers (off-class)** | Market structure and incumbent advantage |
| c31.s5 | 1/50 | 2% | **Optimisation objective misspecification (off-class)** | Market structure and incumbent advantage |
| c59.s4 | 1/50 | 2% | **Organisational governance friction (off-class)** | Customer behavioural and motivation barriers |
| c62.s2 | 1/50 | 2% | **Asynchronous calendar/cycle conflict** | Schedule cascade and dependency delays |
| c62.s3 | 1/50 | 2% | **Heterogeneity defeats standardisation (off-class)** | Schedule cascade and dependency delays |
| c79.s4 | 1/50 | 2% | **Hosted-system architectural philosophy mismatch** | Legacy infrastructure and architecture incompatibility |
| c79.s5 | 1/50 | 2% | **Communication channel / bandwidth (off-class)** | Legacy infrastructure and architecture incompatibility |
| c79.s6 | 1/50 | 2% | **Stale system state (off-class)** | Legacy infrastructure and architecture incompatibility |
| c79.s7 | 1/50 | 2% | **Coordination value-chain ecosystem failure (off-class)** | Legacy infrastructure and architecture incompatibility |
| c79.s8 | 1/50 | 2% | **Domain-specialised architectural mismatch (off-class)** | Legacy infrastructure and architecture incompatibility |
| c15.s2 | 1/50 | 2% | **Lab-to-field translation (off-class)** | Network capacity and hosting constraints |
| c15.s3 | 1/50 | 2% | **Coupled trade-off (off-class)** | Network capacity and hosting constraints |
| c15.s4 | 1/50 | 2% | **Coupled-objective inverter mismatch (off-class)** | Network capacity and hosting constraints |
| c15.s5 | 1/50 | 2% | **Data quality (off-class)** | Network capacity and hosting constraints |
| c20.s3 | 1/50 | 2% | **Race conditions and asynchronous control conflicts** | Aggregate, correlation, and diversity-loss effects |
| c20.s4 | 1/50 | 2% | **Lock-in / commitment closing future options (off-class)** | Aggregate, correlation, and diversity-loss effects |
| c20.s5 | 1/50 | 2% | **Inverter–grid interaction (off-class)** | Aggregate, correlation, and diversity-loss effects |
| c20.s6 | 1/50 | 2% | **Operational variability/non-stationarity (off-class)** | Aggregate, correlation, and diversity-loss effects |
| c20.s7 | 1/50 | 2% | **Maintenance / sustainment gaps (off-class)** | Aggregate, correlation, and diversity-loss effects |
| c20.s8 | 1/50 | 2% | **Sample representativeness (off-class)** | Aggregate, correlation, and diversity-loss effects |
| c41.s2 | 1/50 | 2% | **Process by-product/contamination side-effect (off-class)** | Test, validation, and verification coverage gaps |
| c41.s3 | 1/50 | 2% | **Tariff/incentive design failure (off-class)** | Test, validation, and verification coverage gaps |
| c41.s4 | 1/50 | 2% | **Subsidy/procurement design distortions (off-class)** | Test, validation, and verification coverage gaps |
| c41.s5 | 1/50 | 2% | **Compliance certification/standards-conformance gaps** | Test, validation, and verification coverage gaps |
| c41.s6 | 1/50 | 2% | **Manufacturing/workmanship defect (off-class)** | Test, validation, and verification coverage gaps |
| c41.s7 | 1/50 | 2% | **Market structure distortion (off-class)** | Test, validation, and verification coverage gaps |
| c36.s2 | 1/50 | 2% | **Supply-chain constraints (off-class)** | Regulatory ambiguity, fragmentation, and jurisdictional conf |
| c46.s2 | 1/50 | 2% | **Pre-funding / uncompensated-effort burden** | Misaligned incentives between actors |
| c46.s3 | 1/50 | 2% | **Multi-party coordination (off-class)** | Misaligned incentives between actors |
| c46.s4 | 1/50 | 2% | **Behavioural responses (off-class)** | Misaligned incentives between actors |
| c46.s5 | 1/50 | 2% | **Workforce/skills (off-class)** | Misaligned incentives between actors |
| c46.s6 | 1/50 | 2% | **Procurement/tender pathology (off-class)** | Misaligned incentives between actors |
| c46.s7 | 1/50 | 2% | **Personnel turnover (off-class)** | Misaligned incentives between actors |
| c07.s2 | 1/50 | 2% | **Knowledge gaps in fundamental physical mechanisms (off-class)** | Equipment operating outside design envelope |
| c07.s3 | 1/50 | 2% | **Manufacturing yield (off-class)** | Equipment operating outside design envelope |
| c07.s4 | 1/50 | 2% | **Spatial/siting constraints (off-class)** | Equipment operating outside design envelope |
| c07.s5 | 1/50 | 2% | **Gaming / self-reporting integrity (off-class)** | Equipment operating outside design envelope |
| c07.s6 | 1/50 | 2% | **Latent constraint surfaces under new use (off-class)** | Equipment operating outside design envelope |
| c17.s2 | 1/50 | 2% | **Environmental damage (off-class)** | Capacity, sizing, and headroom shortfalls |
| c17.s3 | 1/50 | 2% | **Control logic misoperation (off-class)** | Capacity, sizing, and headroom shortfalls |
| c27.s2 | 1/50 | 2% | **Subsidy/incentive design (off-class)** | Investment risk and financing barriers |
| c27.s3 | 1/50 | 2% | **Vendor/proprietary lock-in (off-class)** | Investment risk and financing barriers |
| c27.s4 | 1/50 | 2% | **Customer heterogeneity (off-class)** | Investment risk and financing barriers |
| c27.s5 | 1/50 | 2% | **Contract rigidity (off-class)** | Investment risk and financing barriers |
| c55.s3 | 1/50 | 2% | **Trust / acceptance (off-class)** | Stakeholder engagement and consultation failures |
| c55.s4 | 1/50 | 2% | **Schedule rigidity (off-class)** | Stakeholder engagement and consultation failures |
| c76.s2 | 1/50 | 2% | **Network/feeder physical constraint (off-class)** | Software, firmware, and IT system fragility |
| c76.s3 | 1/50 | 2% | **Value-stream design absent (off-class)** | Software, firmware, and IT system fragility |
| c30.s2 | 1/50 | 2% | **Volatile/correlated cost exposure** | Tariff and price-signal design distortions |
| c30.s3 | 1/50 | 2% | **Jurisdictional conflict (off-class)** | Tariff and price-signal design distortions |
| c30.s4 | 1/50 | 2% | **Stakeholder commitment / community opposition (off-class)** | Tariff and price-signal design distortions |
| c70.s2 | 1/50 | 2% | **Process condition incompatibility between coupled steps** | Feedstock and input variability or quality |
| c70.s3 | 1/50 | 2% | **Auxiliary-load / parasitic loss (off-class)** | Feedstock and input variability or quality |
| c70.s4 | 1/50 | 2% | **Spatial/siting constraints (off-class)** | Feedstock and input variability or quality |
| c70.s5 | 1/50 | 2% | **Aggregation/diversity (off-class)** | Feedstock and input variability or quality |
| c70.s6 | 1/50 | 2% | **Control-system mismatch (off-class)** | Feedstock and input variability or quality |
| c81.s2 | 1/50 | 2% | **Aggregator/FRMP structural disadvantage (off-class)** | Technology readiness and maturity gap |
| c81.s3 | 1/50 | 2% | **Coupled trade-off (off-class)** | Technology readiness and maturity gap |
| c81.s4 | 1/50 | 2% | **Regulatory framework misfit (off-class)** | Technology readiness and maturity gap |
| c81.s5 | 1/50 | 2% | **Community opposition (off-class)** | Technology readiness and maturity gap |
| c86.s2 | 1/50 | 2% | **Dispatch / operating priority conflicts (off-class)** | Externalities and lifecycle accounting omissions |
| c86.s3 | 1/50 | 2% | **Incumbent advantage (off-class)** | Externalities and lifecycle accounting omissions |
| c32.s2 | 1/50 | 2% | **Stakeholder engagement design (off-class)** | Incumbent lock-in and switching cost barriers |
| c32.s3 | 1/50 | 2% | **Novel technology failure modes (off-class)** | Incumbent lock-in and switching cost barriers |
| c89.s2 | 1/50 | 2% | **Marketing/communication channel mismatch (off-class)** | Safety hazard and risk classification escalation |
| c12.s2 | 1/50 | 2% | **Site-specific transferability (off-class)** | Cadence, latency, and timing mismatches |
| c12.s3 | 1/50 | 2% | **Configuration/firmware errors (off-class)** | Cadence, latency, and timing mismatches |
| c22.s2 | 1/50 | 2% | **Standards obsolescence (off-class)** | Aggregation and granularity mismatch |
| c26.s2 | 1/50 | 2% | **Multi-party coordination (off-class)** | Value not captured by available market mechanisms |
| c26.s3 | 1/50 | 2% | **Compliance verification gap (off-class)** | Value not captured by available market mechanisms |
| c67.s2 | 1/50 | 2% | **Installer/field-execution workmanship variability** | Manufacturing variability and fabrication defects |
| c85.s2 | 1/50 | 2% | **Static rule vs dynamic system reality** | Conservative margin and over-specification bias |
| c85.s3 | 1/50 | 2% | **Demand response delivery shortfall (off-class)** | Conservative margin and over-specification bias |
| c85.s4 | 1/50 | 2% | **Unintended secondary effect (off-class)** | Conservative margin and over-specification bias |
| c60.s2 | 1/50 | 2% | **Stakeholder consultation (off-class)** | Behavioural rebound and unintended response |
| c90.s2 | 1/50 | 2% | **Behavioural rebound (off-class)** | Sample, selection, and representativeness bias |
| c96.s3 | 1/50 | 2% | **Correlation/synchronisation aggregate effects (off-class)** | Forecast uncertainty and actionability limits |
| c96.s4 | 1/50 | 2% | **Lab-to-scale translation (off-class)** | Forecast uncertainty and actionability limits |
| c105.s2 | 1/50 | 2% | **Confounding variables / identification failure (off-class)** | Organisational governance and process inertia |
| c105.s3 | 1/50 | 2% | **Verification gap (off-class)** | Organisational governance and process inertia |
| c40.s2 | 1/50 | 2% | **Personnel turnover (off-class)** | Compliance enforcement and verification gaps |
| c40.s3 | 1/50 | 2% | **Temporal mismatch supply/demand (off-class)** | Compliance enforcement and verification gaps |
| c40.s4 | 1/50 | 2% | **Regulator capacity (off-class)** | Compliance enforcement and verification gaps |
| c40.s5 | 1/50 | 2% | **Jurisdictional fragmentation (off-class)** | Compliance enforcement and verification gaps |
| c21.s2 | 1/50 | 2% | **Uncoordinated independent actor effects (off-class)** | Heterogeneity defeats uniform design |
| c21.s3 | 1/50 | 2% | **Gaming / self-reporting integrity (off-class)** | Heterogeneity defeats uniform design |
| c42.s2 | 1/50 | 2% | **Compliance burden / proportionality (off-class)** | Standards mismatch, obsolescence, or absence |
| c42.s3 | 1/50 | 2% | **Customer recruitment shortfall (off-class)** | Standards mismatch, obsolescence, or absence |
| c42.s4 | 1/50 | 2% | **Latent defect surfacing (off-class)** | Standards mismatch, obsolescence, or absence |
| c48.s2 | 1/50 | 2% | **Storage capacity insufficient (off-class)** | Procurement and tendering process distortions |
| c48.s3 | 1/50 | 2% | **Cost competitiveness (off-class)** | Procurement and tendering process distortions |
| c48.s4 | 1/50 | 2% | **Aggregate-individual mismatch (off-class)** | Procurement and tendering process distortions |
| c78.s2 | 1/50 | 2% | **Incentive misalignment (off-class)** | Single point of failure and common-mode dependency |
| c63.s2 | 1/50 | 2% | **Reversal in environmental/input conditions during operation** | Late discovery forcing rework |
| c80.s2 | 1/50 | 2% | **Latency/cadence (off-class)** | Architectural rigidity and modularity limits |
| c80.s3 | 1/50 | 2% | **Optimisation objective misspecification (off-class)** | Architectural rigidity and modularity limits |
| c19.s2 | 1/50 | 2% | **Compliance verification (off-class)** | Geographic and locational mismatch |
| c38.s2 | 1/50 | 2% | **Settlement attribution (off-class)** | Regulatory metric and methodology design flaws |
| c38.s3 | 1/50 | 2% | **Investor risk premium (off-class)** | Regulatory metric and methodology design flaws |
| c38.s4 | 1/50 | 2% | **Regulatory framework misfit (off-class)** | Regulatory metric and methodology design flaws |
| c84.s2 | 1/50 | 2% | **Coupled trade-off (off-class)** | Auxiliary load and parasitic consumption |
| c92.s2 | 1/50 | 2% | **Regulatory framework absence (off-class)** | Counterfactual and baseline measurement difficulty |
| c95.s2 | 1/50 | 2% | **Software development scope (off-class)** | Information asymmetry between parties |
| c95.s3 | 1/50 | 2% | **Communication style mismatch (off-class)** | Information asymmetry between parties |
| c113.s2 | 1/50 | 2% | **Supply chain disruption (off-class)** | Stakeholder alignment and expectation divergence |
| c107.s2 | 1/50 | 2% | **Manual processes / IT fragility (off-class)** | Long-horizon commitment and stranded asset risk |
| c101.s2 | 1/50 | 2% | **Aggregate heterogeneity (off-class)** | System inertia and synchronous-service shortfall |
| c69.s2 | 1/50 | 2% | **Network capacity (off-class)** | Latent defects revealed in operation |
| c71.s3 | 1/50 | 2% | **Spatial process non-uniformity** | Process chemistry and conversion limits |
| c39.s2 | 1/50 | 2% | **Reactive/slow regulatory reform (off-class)** | Compliance burden disproportionate to scale |
| c64.s2 | 1/50 | 2% | **Sample bias / unrepresentative populations (off-class)** | Scope change and rework cascades |
| c64.s3 | 1/50 | 2% | **Compliance enforcement gap (off-class)** | Scope change and rework cascades |
| c100.s3 | 1/50 | 2% | **Discontinuous-event amplification / cascading hazard** | Cumulative compounding and small-effect aggregation |
| c100.s4 | 1/50 | 2% | **Sample selection bias (off-class)** | Cumulative compounding and small-effect aggregation |
| c117.s2 | 1/50 | 2% | **Storage capacity/duration constraints (off-class)** | Co-located asset interaction and shared-resource contention |
| c121.s2 | 1/50 | 2% | **Process inflexibility blocking intermittent integration** | Conservative-design self-defeating overspecification |
| none | 0/50 | 0% | **No fit** | (atomic pass-through) |