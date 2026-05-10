# v2 extended parent set — 59-rep ensemble + boundary-tier extension

Single Opus 4.7 call. 86 promoted mechanism classes consolidated into 86 unified v2 parent definitions.
**Cost:** $0.63, 226s wall.

**Tier breakdown:** {'core': 43, 'boundary': 16, 'high': 27}

## Parent set

| parent | name | tier | n_reps_min | mechanism criterion |
|---|---|---|---|---|
| p01 | Missing or inaccessible data | core | 59 | A required information artefact is structurally absent, unrecorded, or inaccessible at the point of need. |
| p02 | Data quality, format, and semantic defects | core | 59 | Available data produces wrong or unusable downstream outputs because of quality, format, schema, semantic, or integratio |
| p03 | Measurement and sensing limitations | core | 59 | A sensor or measurement instrument fails to faithfully observe its target physical quantity due to physical or instrumen |
| p04 | Aggregation and granularity mismatch | boundary | 36 | Aggregation, averaging, or coarse granularity destroys individual-level information required for correct operation, attr |
| p05 | Visibility and observability gaps | high | 51 | Insufficient observability or situational awareness over distributed assets, conditions, or populations prevents effecti |
| p06 | Documentation and configuration management gaps | boundary | 27 | An action fails because the relevant documentation or configuration record is missing, outdated, or has drifted from act |
| p07 | Model and forecast representational error | core | 57 | A model, forecast, or simulation yields outputs materially diverging from reality because of how it represents the syste |
| p08 | Computational and algorithmic tractability limits | boundary | 31 | Computational or algorithmic resource requirements exceed what is available within the operational time window or fideli |
| p09 | Optimisation objective and metric misspecification | core | 59 | The chosen optimisation objective, metric, or scoring rule produces outcomes systematically misaligned with intended sys |
| p10 | Externalities and lifecycle accounting omissions | high | 46 | An analytical, accounting, or valuation framework omits material externalities, lifecycle effects, or boundary flows, bi |
| p11 | Counterfactual and baseline measurement difficulty | high | 51 | Effect quantification or attribution fails because the required counterfactual baseline cannot be reliably measured or c |
| p12 | Sample, selection, and representativeness bias | high | 53 | Conclusions are biased because the observed sample is systematically unrepresentative of the population to which results |
| p13 | Test, validation, and verification coverage gaps | core | 59 | A defect or condition escapes detection because the verification regime does not exercise the relevant conditions, durat |
| p14 | Lab-to-field and pilot-to-scale translation failure | core | 59 | Performance demonstrated at one scale or controlled environment fails to transfer because deployment conditions, dynamic |
| p15 | Commissioning, handover, and integration discovery failures | boundary | 38 | Failures emerge at first integrated operation or organisational handover that earlier phases did not detect. |
| p16 | Mechanism understanding and scientific knowledge gaps | core | 55 | Insufficient mechanistic understanding prevents reliable prediction, control, or scale-up. |
| p17 | Subsurface and resource characterisation uncertainty | high | 43 | Inability to characterise a natural resource before commitment, or its change after intervention, drives performance sho |
| p18 | Material, chemical, and physical-property limits | core | 59 | An intrinsic physical, chemical, thermal, or material property constrains, degrades, or precludes the desired behaviour. |
| p19 | Coupled trade-offs and competing objectives | core | 59 | An irreducible coupling forces a trade-off where gain on one axis produces loss on another. |
| p20 | Diminishing returns and saturation effects | boundary | 36 | Marginal benefit of additional input, capacity, or intervention falls sharply because the system is saturating or thresh |
| p21 | Hard-to-abate residuals and decarbonisation ceilings | core | 55 | Decarbonisation is constrained because residuals arise from structural process or feedstock characteristics without comm |
| p22 | Equipment operating outside design envelope | core | 59 | An asset is operated under conditions exceeding or differing from its design envelope, producing degradation, derating,  |
| p23 | Capacity, sizing, and headroom shortfall | core | 59 | An asset's rated capacity, duration, or headroom is structurally below the duty placed on it. |
| p24 | Auxiliary loads and parasitic consumption | boundary | 39 | Auxiliary or parasitic consumption substantially reduces net deliverable output below gross capability. |
| p25 | Feedstock and input variability | high | 47 | Input feedstock or material variability or contamination exceeds the tolerance of the consuming process. |
| p26 | Manufacturing, fabrication, and installation defects | core | 59 | A defect originating in production, fabrication, or installation workmanship causes the deployed unit to fail or underpe |
| p27 | Environmental and external hazard exposure | core | 59 | An external environmental, weather, biological, or natural event physically degrades, damages, or disrupts assets or ope |
| p28 | Safety hazard and risk-classification consequences | boundary | 34 | A safety hazard or reclassification triggers cost, restriction, or design overhead disproportionate to ordinary engineer |
| p29 | Spatial, geometric, and siting constraints | core | 59 | A spatial, geometric, terrain, or land-availability constraint physically blocks or constrains deployment. |
| p30 | Geographic and locational mismatch | high | 43 | Spatial separation between resource, demand, or infrastructure imposes a binding cost or feasibility penalty. |
| p31 | Temporal and seasonal supply-demand mismatch | core | 55 | Temporal misalignment between when a resource is produced and when it is needed prevents direct utilisation. |
| p32 | Network capacity and physical grid constraints | high | 49 | A physical electrical-network capacity, hosting, or topology constraint prevents or restricts intended power flows or co |
| p33 | Inverter-based resource and grid-stability dynamics | core | 59 | Inverter-based resource dynamics interact with grid characteristics in ways incompatible with frameworks built around sy |
| p34 | Curtailment and headroom-allocation conflicts | boundary | 32 | An operational rule or allocation conflict forces non-utilisation of available output capacity or service. |
| p35 | Control logic, configuration, and protection errors | core | 59 | An adjustable parameter, control rule, or coordination logic is wrong or miscoordinated, causing incorrect behaviour fro |
| p36 | Cadence, latency, and timing mismatch in control | high | 50 | A timing, cadence, or update-frequency mismatch between coupled processes causes incorrect or stale operation. |
| p37 | Communication and connectivity failures | high | 51 | Information or commands fail to traverse a communication path correctly because of channel, bandwidth, or protocol-layer |
| p38 | Interoperability and interface incompatibility | core | 59 | Integration fails at a defined boundary because interface specifications, protocols, formats, or semantics do not align  |
| p39 | Standards absence, obsolescence, or fragmentation | high | 42 | A shared standard, benchmark, or methodology is missing, outdated, or inconsistent across actors. |
| p40 | Software, firmware, and IT system fragility | high | 45 | A failure originates in software, firmware, or IT-platform characteristics rather than data, hardware, or external const |
| p41 | Cybersecurity, authentication, and access-control exposure | core | 59 | Security, authentication, or access-control mechanisms cause failure, expose risk, or impede legitimate operation. |
| p42 | Architectural rigidity and modularity limits | high | 45 | Architectural coupling or absent modularity prevents independent modification, substitution, or scaling of subcomponents |
| p43 | Legacy infrastructure incompatibility | boundary | 37 | Legacy infrastructure structurally blocks new requirements because its embedded assumptions no longer match current need |
| p44 | Single point of failure and shared-resource fragility | core | 58 | A shared centralised dependency creates correlated common-mode failure or bottleneck across multiple dependent functions |
| p45 | Aggregate correlation and concentration risk | boundary | 28 | Nominally independent units exhibit correlated or synchronised behaviour producing aggregate effects beyond individual a |
| p46 | Heterogeneity defeats one-size-fits-all design | core | 56 | A standardised design produces poor outcomes because real-world variation across the population exceeds what one configu |
| p47 | Technology immaturity and readiness gap | high | 52 | The technology or its supporting ecosystem has not reached the maturity level required by the deployment context attempt |
| p48 | Capital cost and upfront-investment barriers | core | 58 | Upfront capital cost, financing structure, or return threshold prevents commitment despite technical viability. |
| p49 | Investment risk and bankability barriers | high | 43 | Financing fails or is overpriced because risk perception or financial-instrument design cannot accommodate the project's |
| p50 | Cost structure and unit-economics infeasibility | high | 52 | Total or unit cost structurally exceeds value or competing benchmark due to cost composition or scale disadvantage. |
| p51 | Volatile or correlated price exposure | core | 58 | External price volatility or correlation erodes project viability beyond the commercial structure's ability to hedge. |
| p52 | Price signal absent, distorted, or perverse | high | 52 | A price, tariff, or settlement signal does not reflect underlying cost or value, producing misaligned behaviour. |
| p53 | Value not capturable through market mechanisms | high | 51 | Value created cannot be captured because no market mechanism translates it into revenue. |
| p54 | Market structure and incumbent advantage | high | 49 | Market structure or incumbent power systematically distorts competitive outcomes for new technologies or actors. |
| p55 | Vendor lock-in and proprietary closure | core | 59 | Proprietary closure or vendor-controlled access blocks independent action, substitution, or third-party engagement. |
| p56 | Lock-in, switching costs, and stranded-asset risk | boundary | 41 | Prior irreversible commitments structurally constrain optionality or expose to stranding risk. |
| p57 | Supply chain and lead-time disruption | core | 59 | External supply-chain disruption or lead-time exposure impairs procurement of required goods or services. |
| p58 | End-of-life, recycling, and circularity gaps | boundary | 36 | End-of-life, recycling, or disposal pathway is missing, inadequate, or uneconomic. |
| p59 | Regulatory framework absence for novel cases | core | 59 | An activity is blocked because no regulatory framework or approval pathway has been defined for it. |
| p60 | Regulatory framework misalignment with current reality | boundary | 24 | An existing regulation produces perverse or inappropriate outcomes because its underlying assumptions no longer match cu |
| p61 | Regulatory ambiguity and jurisdictional fragmentation | core | 59 | Multiple regulatory bodies, jurisdictions, or rule sets produce ambiguous, conflicting, or fragmented obligations. |
| p62 | Regulatory process delay and procedural friction | core | 59 | Regulatory or approval procedural mechanics impose delay, rework, or cost beyond what rule substance requires. |
| p63 | Compliance burden disproportionate to scale | boundary | 33 | Fixed compliance or administrative overhead is disproportionate to activity scale, suppressing participation. |
| p64 | Compliance verification and enforcement gaps | core | 59 | Enforcement, verification, or monitoring is insufficient to ensure adherence to a stated obligation. |
| p65 | Policy uncertainty and instability | core | 55 | Uncertainty or volatility about future policy state deters or distorts commitment. |
| p66 | Subsidy and incentive design distortions | high | 47 | An incentive scheme's structural design causes outcomes to diverge from its stated objective. |
| p67 | Funding instrument and milestone-structure misfit | core | 59 | Funding-instrument design imposes timing, scope, or reporting structures incompatible with the funded activity. |
| p68 | Contract structure and term misalignment | high | 52 | A contract's structure, scope, or terms produce gaps or unworkable obligations relative to actual situation. |
| p69 | Procurement and tendering process pathologies | high | 42 | Procurement or tender process design produces adverse selection, pricing, or contracting outcomes independent of technic |
| p70 | Multi-party coordination overhead | core | 59 | Coordinating actions across multiple independent parties produces delivery friction beyond what any one party can addres |
| p71 | Responsibility and accountability gaps | boundary | 40 | An action goes unperformed because responsibility for it is unassigned, ambiguous, or contested. |
| p72 | Misaligned incentives between actors | core | 54 | Decision rights and consequence-bearing are split across parties with structurally divergent incentives. |
| p73 | Information asymmetry between parties | core | 58 | One party holds information another party needs, but it is not shared. |
| p74 | Chicken-and-egg coordination deadlocks | core | 55 | Mutual prerequisite dependency between parties or investments prevents either from moving first. |
| p75 | Trust, perception, and social licence | high | 51 | Trust, perception, or social-licence dynamics suppress adoption or progress regardless of technical or economic substanc |
| p76 | Equity, distributional, and access barriers | high | 52 | Cost or benefit distribution disadvantages a subgroup because of access, eligibility, or fixed-cost barriers. |
| p77 | Customer recruitment, conversion, and retention friction | core | 58 | Recruitment, onboarding, or retention pipeline design loses prospects between awareness and committed participation. |
| p78 | Behavioural rebound and unintended response | high | 42 | An intervention triggers a compensating response that erodes or reverses its intended effect. |
| p79 | Demand response and aggregator delivery shortfall | core | 55 | Aggregated or contracted demand-response capacity under-delivers at activation. |
| p80 | Workforce skills and capability scarcity | high | 53 | Required human capability or workforce capacity is insufficient to deliver the work at the required time and place. |
| p81 | Personnel turnover and key-person dependency | core | 57 | Loss of specific personnel disrupts continuity because critical knowledge or relationships were concentrated in them. |
| p82 | Manual process bottlenecks and automation gaps | core | 58 | A manual process step caps throughput, introduces errors, or prevents scaling because it has not been automated. |
| p83 | Project planning, scoping, and contingency inadequacy | core | 59 | Inadequate upfront planning, scoping, or contingency causes downstream rework or capability gaps. |
| p84 | Late discovery forcing rework | core | 57 | An issue or requirement is identified after a commitment point, forcing costly rework that earlier discovery would have  |
| p85 | Schedule cascade and dependency delays | boundary | 34 | Sequential dependency structure causes a single delay to cascade across the project schedule. |
| p86 | Conservative-margin and over-specification bias | high | 51 | Conservatism in response to uncertainty drives systematic over-design or excess restriction relative to actual need. |

## Full definitions

### p01 — Missing or inaccessible data

*tier: core, n_reps_min: 59, sources: core_01*

A required information artefact does not exist, was never collected, or cannot be obtained by the party that needs it at the time of need. This is structural absence rather than a quality defect in available data.

**Mechanism criterion:** A required information artefact is structurally absent, unrecorded, or inaccessible at the point of need.

**Exemplar clusters:** c001, c002, c003

### p02 — Data quality, format, and semantic defects

*tier: core, n_reps_min: 59, sources: core_02*

Available data produces wrong or unusable downstream outputs because of quality, format, schema, semantic, or integration defects. The data exists but its content, structure, or meaning is corrupted, inconsistent, or incompatible with the consuming process.

**Mechanism criterion:** Available data produces wrong or unusable downstream outputs because of quality, format, schema, semantic, or integration defects.

**Exemplar clusters:** c004, c005, c006

### p03 — Measurement and sensing limitations

*tier: core, n_reps_min: 59, sources: core_03*

An instrument or measurement method fails to faithfully observe its target physical quantity due to its design, capability, or deployment characteristics. This concerns the physical limits of sensing, not data handling downstream.

**Mechanism criterion:** A sensor or measurement instrument fails to faithfully observe its target physical quantity due to physical or instrumental capability limits.

**Exemplar clusters:** c007, c008, c009

### p04 — Aggregation and granularity mismatch

*tier: boundary, n_reps_min: 36, sources: bdry_13*

Aggregation, averaging, or coarse granularity destroys information about individual-level conditions required for correct decision, control, or attribution. The data exists but is at the wrong resolution for the use case.

**Mechanism criterion:** Aggregation, averaging, or coarse granularity destroys individual-level information required for correct operation, attribution, or decision-making.

**Exemplar clusters:** c010, c011, c012

### p05 — Visibility and observability gaps

*tier: high, n_reps_min: 51, sources: high_25*

Operational management fails because the controlling party lacks observability or coordination authority over distributed assets, behaviours, or states. Critical for DER coordination and operator situational awareness.

**Mechanism criterion:** Insufficient observability or situational awareness over distributed assets, conditions, or populations prevents effective management.

**Exemplar clusters:** c013, c014, c015

### p06 — Documentation and configuration management gaps

*tier: boundary, n_reps_min: 27, sources: bdry_04*

An action fails or is reworked because authoritative documentation, records, or registry is missing, stale, or has drifted from the actual system state. As-built diverges from as-documented.

**Mechanism criterion:** An action fails because the relevant documentation or configuration record is missing, outdated, or has drifted from actual system state.

**Exemplar clusters:** c016, c017, c018

### p07 — Model and forecast representational error

*tier: core, n_reps_min: 57, sources: core_04*

A model, forecast, or simulation produces inaccurate outputs because of structural assumptions, parameterisation, scope, or training-data limits in the model itself, not because of input data absence.

**Mechanism criterion:** A model, forecast, or simulation yields outputs materially diverging from reality because of how it represents the system, not because of missing inputs.

**Exemplar clusters:** c019, c020, c021

### p08 — Computational and algorithmic tractability limits

*tier: boundary, n_reps_min: 31, sources: bdry_23*

Computational complexity, algorithmic tractability, or compute resource exceeds what is feasible within the required time window or fidelity. The approach is in principle correct but computationally infeasible.

**Mechanism criterion:** Computational or algorithmic resource requirements exceed what is available within the operational time window or fidelity required.

**Exemplar clusters:** c022, c023, c024

### p09 — Optimisation objective and metric misspecification

*tier: core, n_reps_min: 59, sources: core_38*

Outcomes diverge from intent because the chosen optimisation objective, evaluation metric, or scoring rule is misspecified relative to the real goal. Systems optimise the proxy at the expense of the underlying value.

**Mechanism criterion:** The chosen optimisation objective, metric, or scoring rule produces outcomes systematically misaligned with intended system value.

**Exemplar clusters:** c025, c026, c027

### p10 — Externalities and lifecycle accounting omissions

*tier: high, n_reps_min: 46, sources: high_23*

Decision outputs are distorted because the analytical scope or accounting boundary excludes relevant externalities, lifecycle stages, or co-impacts. Material flows or effects lie outside the framework that governs the decision.

**Mechanism criterion:** An analytical, accounting, or valuation framework omits material externalities, lifecycle effects, or boundary flows, biasing decisions or claims.

**Exemplar clusters:** c028, c029, c030

### p11 — Counterfactual and baseline measurement difficulty

*tier: high, n_reps_min: 51, sources: high_21*

Outcomes, benefits, or settlements cannot be reliably attributed because the counterfactual or baseline cannot be measured or constructed. Particularly acute for climate impact and avoided-emissions claims.

**Mechanism criterion:** Effect quantification or attribution fails because the required counterfactual baseline cannot be reliably measured or constructed.

**Exemplar clusters:** c031, c032, c033

### p12 — Sample, selection, and representativeness bias

*tier: high, n_reps_min: 53, sources: high_20*

Inferences are biased because the observed sample, participant pool, or trial conditions are systematically unrepresentative of the target population or deployment context. Pilot conclusions fail to generalise.

**Mechanism criterion:** Conclusions are biased because the observed sample is systematically unrepresentative of the population to which results will be applied.

**Exemplar clusters:** c034, c035, c036

### p13 — Test, validation, and verification coverage gaps

*tier: core, n_reps_min: 59, sources: core_06*

Verification activities pass but fail to cover stimuli, durations, or conditions that occur in real operation. Defects, behaviours, or non-compliance escape detection because the regime does not exercise the relevant conditions.

**Mechanism criterion:** A defect or condition escapes detection because the verification regime does not exercise the relevant conditions, duration, or stimuli.

**Exemplar clusters:** c037, c038, c039

### p14 — Lab-to-field and pilot-to-scale translation failure

*tier: core, n_reps_min: 59, sources: core_05*

A solution validated at one scale or controlled context fails when transferred because the conditions enabling validation do not transfer to the deployment context. Distinct from validation coverage gaps in that the validation itself was sound for its scope.

**Mechanism criterion:** Performance demonstrated at one scale or controlled environment fails to transfer because deployment conditions, dynamics, or constraints diverge from the validation context.

**Exemplar clusters:** c040, c041, c042

### p15 — Commissioning, handover, and integration discovery failures

*tier: boundary, n_reps_min: 38, sources: bdry_17*

Latent faults or integration issues become visible only at commissioning, handover, or first integrated operation under real conditions. Distinct from validation gaps because no prior phase had the integrated context to discover them.

**Mechanism criterion:** Failures emerge at first integrated operation or organisational handover that earlier phases did not detect.

**Exemplar clusters:** c043, c044, c045

### p16 — Mechanism understanding and scientific knowledge gaps

*tier: core, n_reps_min: 55, sources: core_37*

Progress is constrained because scientific or mechanistic understanding of the underlying phenomenon is insufficient for reliable design, prediction, or replication. Distinct from data or measurement gaps.

**Mechanism criterion:** Insufficient mechanistic understanding prevents reliable prediction, control, or scale-up.

**Exemplar clusters:** c046, c047, c048

### p17 — Subsurface and resource characterisation uncertainty

*tier: high, n_reps_min: 43, sources: high_27*

Subsurface or natural-resource conditions cannot be adequately characterised before irreversible commitment, exposing the project to physical performance risk. Resource may also change after intervention in unforeseen ways.

**Mechanism criterion:** Inability to characterise a natural resource before commitment, or its change after intervention, drives performance shortfall.

**Exemplar clusters:** c049, c050, c051

### p18 — Material, chemical, and physical-property limits

*tier: core, n_reps_min: 59, sources: core_07*

An intrinsic physical, chemical, thermal, or material property bounds, degrades, or precludes desired behaviour regardless of operational or design choices within the current architecture. Hard physical ceiling rather than engineering shortfall.

**Mechanism criterion:** An intrinsic physical, chemical, thermal, or material property constrains, degrades, or precludes the desired behaviour.

**Exemplar clusters:** c052, c053, c054

### p19 — Coupled trade-offs and competing objectives

*tier: core, n_reps_min: 59, sources: core_17*

An irreducible coupling between two performance objectives prevents simultaneous optimisation; gain on one axis structurally produces loss on the other through shared physics or constraints.

**Mechanism criterion:** An irreducible coupling forces a trade-off where gain on one axis produces loss on another.

**Exemplar clusters:** c055, c056, c057

### p20 — Diminishing returns and saturation effects

*tier: boundary, n_reps_min: 36, sources: bdry_10*

Marginal returns to further input, capacity, or intervention collapse because the system is approaching a saturation, depletion, threshold, or addressable-market ceiling. Pilots that worked at low penetration deliver less at scale.

**Mechanism criterion:** Marginal benefit of additional input, capacity, or intervention falls sharply because the system is saturating or threshold-bound.

**Exemplar clusters:** c058, c059, c060

### p21 — Hard-to-abate residuals and decarbonisation ceilings

*tier: core, n_reps_min: 55, sources: core_39*

Further decarbonisation or improvement is structurally blocked because residual emissions or losses arise from process or feedstock characteristics that lack commercially viable low-emission alternatives.

**Mechanism criterion:** Decarbonisation is constrained because residuals arise from structural process or feedstock characteristics without commercial low-emission alternatives.

**Exemplar clusters:** c061, c062, c063

### p22 — Equipment operating outside design envelope

*tier: core, n_reps_min: 59, sources: core_08*

Performance degrades or equipment fails because operating conditions exceed or differ from the design envelope assumed by the equipment's specification, producing degradation, derating, or accelerated wear.

**Mechanism criterion:** An asset is operated under conditions exceeding or differing from its design envelope, producing degradation, derating, or failure.

**Exemplar clusters:** c064, c065, c066

### p23 — Capacity, sizing, and headroom shortfall

*tier: core, n_reps_min: 59, sources: core_11*

A specific component or asset's installed capacity, rating, duration, or headroom is structurally insufficient for the load, demand, or service it must provide.

**Mechanism criterion:** An asset's rated capacity, duration, or headroom is structurally below the duty placed on it.

**Exemplar clusters:** c067, c068, c069

### p24 — Auxiliary loads and parasitic consumption

*tier: boundary, n_reps_min: 39, sources: bdry_09*

Auxiliary, parasitic, or balance-of-system consumption substantially erodes net deliverable output relative to gross capability. The gross-vs-net gap defeats expected economics or service.

**Mechanism criterion:** Auxiliary or parasitic consumption substantially reduces net deliverable output below gross capability.

**Exemplar clusters:** c070, c071, c072

### p25 — Feedstock and input variability

*tier: high, n_reps_min: 47, sources: high_06*

Process performance is degraded because input feedstock or material composition varies, contaminates, or falls outside the design tolerance of the consuming process.

**Mechanism criterion:** Input feedstock or material variability or contamination exceeds the tolerance of the consuming process.

**Exemplar clusters:** c073, c074, c075

### p26 — Manufacturing, fabrication, and installation defects

*tier: core, n_reps_min: 59, sources: core_16*

A defect or variability introduced during manufacturing, fabrication, assembly, or installation propagates into operational failure or quality loss in the deployed unit.

**Mechanism criterion:** A defect originating in production, fabrication, or installation workmanship causes the deployed unit to fail or underperform.

**Exemplar clusters:** c076, c077, c078

### p27 — Environmental and external hazard exposure

*tier: core, n_reps_min: 59, sources: core_10*

An exogenous environmental, weather, biological, or natural-event factor acts physically on assets or operations to cause damage, degradation, or disruption.

**Mechanism criterion:** An external environmental, weather, biological, or natural event physically degrades, damages, or disrupts assets or operations.

**Exemplar clusters:** c079, c080, c081

### p28 — Safety hazard and risk-classification consequences

*tier: boundary, n_reps_min: 34, sources: bdry_08*

An intrinsic or newly-recognised safety hazard, or hazard reclassification, imposes additional controls, restrictions, or design overhead beyond the original plan and beyond ordinary engineering.

**Mechanism criterion:** A safety hazard or reclassification triggers cost, restriction, or design overhead disproportionate to ordinary engineering.

**Exemplar clusters:** c082, c083, c084

### p29 — Spatial, geometric, and siting constraints

*tier: core, n_reps_min: 59, sources: core_09*

Available physical space, geometry, terrain, or land-availability characteristics block or distort the intended deployment, operation, or maintenance configuration.

**Mechanism criterion:** A spatial, geometric, terrain, or land-availability constraint physically blocks or constrains deployment.

**Exemplar clusters:** c085, c086, c087

### p30 — Geographic and locational mismatch

*tier: high, n_reps_min: 43, sources: high_07*

Spatial separation between resource and demand, or asset and market, imposes a binding cost, transport, or feasibility penalty that cannot be cheaply bridged.

**Mechanism criterion:** Spatial separation between resource, demand, or infrastructure imposes a binding cost or feasibility penalty.

**Exemplar clusters:** c088, c089, c090

### p31 — Temporal and seasonal supply-demand mismatch

*tier: core, n_reps_min: 55, sources: core_18*

Supply and demand or two coupled processes are misaligned in time such that the resource or output is unavailable when it is needed, causing curtailment, shortfall, or storage demand.

**Mechanism criterion:** Temporal misalignment between when a resource is produced and when it is needed prevents direct utilisation.

**Exemplar clusters:** c091, c092, c093

### p32 — Network capacity and physical grid constraints

*tier: high, n_reps_min: 49, sources: high_01*

A pre-existing physical electrical-network capacity, voltage, thermal, hosting, or topology limit constrains achievable connection, flow, or operation. Distinct from asset-level sizing.

**Mechanism criterion:** A physical electrical-network capacity, hosting, or topology constraint prevents or restricts intended power flows or connections.

**Exemplar clusters:** c094, c095, c096

### p33 — Inverter-based resource and grid-stability dynamics

*tier: core, n_reps_min: 59, sources: core_12*

A power-system electrical or stability phenomenon arises from inverter-based resource behaviour, or from displacement of synchronous-machine services, that legacy frameworks were not designed for.

**Mechanism criterion:** Inverter-based resource dynamics interact with grid characteristics in ways incompatible with frameworks built around synchronous plant.

**Exemplar clusters:** c097, c098, c099

### p34 — Curtailment and headroom-allocation conflicts

*tier: boundary, n_reps_min: 32, sources: bdry_20*

Output is curtailed or operations restricted because operational rules, capacity-allocation conflicts, or reserved-headroom requirements force non-utilisation of physically available capacity.

**Mechanism criterion:** An operational rule or allocation conflict forces non-utilisation of available output capacity or service.

**Exemplar clusters:** c100, c101, c102

### p35 — Control logic, configuration, and protection errors

*tier: core, n_reps_min: 59, sources: core_13*

A control rule, configuration parameter, threshold, or protection coordination is wrong or miscoordinated, causing incorrect system behaviour from otherwise capable equipment.

**Mechanism criterion:** An adjustable parameter, control rule, or coordination logic is wrong or miscoordinated, causing incorrect behaviour from capable equipment.

**Exemplar clusters:** c103, c104, c105

### p36 — Cadence, latency, and timing mismatch in control

*tier: high, n_reps_min: 50, sources: high_02*

Control or signal performance fails because timing characteristics — latency, cadence, refresh rate, response window — of one element do not match the timescale of the coupled process. Distinct from communication failure: the channel works but is too slow or out of phase.

**Mechanism criterion:** A timing, cadence, or update-frequency mismatch between coupled processes causes incorrect or stale operation.

**Exemplar clusters:** c106, c107, c108

### p37 — Communication and connectivity failures

*tier: high, n_reps_min: 51, sources: high_03*

A communication channel, protocol, or connectivity infrastructure fails to deliver signals reliably or with sufficient capacity, due to physical-layer, channel, or protocol-layer limits.

**Mechanism criterion:** Information or commands fail to traverse a communication path correctly because of channel, bandwidth, or protocol-layer limits.

**Exemplar clusters:** c109, c110, c111

### p38 — Interoperability and interface incompatibility

*tier: core, n_reps_min: 59, sources: core_14*

Two systems fail to interoperate at a defined boundary because their interface specifications, protocols, formats, or semantics do not align or are unstable.

**Mechanism criterion:** Integration fails at a defined boundary because interface specifications, protocols, formats, or semantics do not align between parties.

**Exemplar clusters:** c112, c113, c114

### p39 — Standards absence, obsolescence, or fragmentation

*tier: high, n_reps_min: 42, sources: high_04*

A shared standard, specification, benchmark, certification scheme, or methodology is absent, obsolete, fragmented across actors, or scope-misaligned with the deployment context. Distinct from bilateral interface mismatch: the ecosystem-level common reference is missing.

**Mechanism criterion:** A shared standard, benchmark, or methodology is missing, outdated, or inconsistent across actors.

**Exemplar clusters:** c115, c116, c117

### p40 — Software, firmware, and IT system fragility

*tier: high, n_reps_min: 45, sources: high_05*

A failure originates in software, firmware, IT-platform, or computational-system design, capability, maintenance, or capacity rather than data, hardware, or external constraints.

**Mechanism criterion:** A failure originates in software, firmware, or IT-platform characteristics rather than data, hardware, or external constraints.

**Exemplar clusters:** c118, c119, c120

### p41 — Cybersecurity, authentication, and access-control exposure

*tier: core, n_reps_min: 59, sources: core_15*

Security, authentication, credential, or access-control architecture creates operational failure, friction, or risk exposure, either by being breached or by impeding legitimate operation.

**Mechanism criterion:** Security, authentication, or access-control mechanisms cause failure, expose risk, or impede legitimate operation.

**Exemplar clusters:** c121, c122, c123

### p42 — Architectural rigidity and modularity limits

*tier: high, n_reps_min: 45, sources: high_18*

System architecture cannot accommodate growth, substitution, or independent component change because of coupling, modularity, or scaling limits in the design itself.

**Mechanism criterion:** Architectural coupling or absent modularity prevents independent modification, substitution, or scaling of subcomponents.

**Exemplar clusters:** c124, c125, c126

### p43 — Legacy infrastructure incompatibility

*tier: boundary, n_reps_min: 37, sources: bdry_25*

Pre-existing physical infrastructure or installed-base architecture embeds prior-paradigm assumptions incompatible with new requirements, blocking economical retrofit. Distinct from architectural rigidity in concerning the embedded installed base rather than current design choice.

**Mechanism criterion:** Legacy infrastructure structurally blocks new requirements because its embedded assumptions no longer match current needs.

**Exemplar clusters:** c127, c128, c129

### p44 — Single point of failure and shared-resource fragility

*tier: core, n_reps_min: 58, sources: core_36*

A single shared centralised dependency creates a failure mode that simultaneously impairs many dependent systems, or a capacity bottleneck across multiple dependent functions.

**Mechanism criterion:** A shared centralised dependency creates correlated common-mode failure or bottleneck across multiple dependent functions.

**Exemplar clusters:** c130, c131, c132

### p45 — Aggregate correlation and concentration risk

*tier: boundary, n_reps_min: 28, sources: bdry_01*

Nominally independent assets, events, or actors exhibit correlated or synchronised behaviour, producing aggregate-level stress or loss of diversity beyond what individual analysis predicts. Distinct from single-point-of-failure: no shared dependency, just correlated exposure.

**Mechanism criterion:** Nominally independent units exhibit correlated or synchronised behaviour producing aggregate effects beyond individual analysis.

**Exemplar clusters:** c133, c134, c135

### p46 — Heterogeneity defeats one-size-fits-all design

*tier: core, n_reps_min: 56, sources: core_43*

A standardised approach fails because real-world heterogeneity across the target population exceeds what the uniform design or parameter can absorb.

**Mechanism criterion:** A standardised design produces poor outcomes because real-world variation across the population exceeds what one configuration absorbs.

**Exemplar clusters:** c136, c137, c138

### p47 — Technology immaturity and readiness gap

*tier: high, n_reps_min: 52, sources: high_19*

Deployment fails or is over-costed because the technology, its supply chain, or its operational track record is at insufficient readiness for the role demanded — distinct from successful validation that fails to translate.

**Mechanism criterion:** The technology or its supporting ecosystem has not reached the maturity level required by the deployment context attempted.

**Exemplar clusters:** c139, c140, c141

### p48 — Capital cost and upfront-investment barriers

*tier: core, n_reps_min: 58, sources: core_19*

Investment is blocked or deferred because upfront capital, payback horizon, or financing-instrument structure does not meet investor or adopter return criteria, despite operational viability.

**Mechanism criterion:** Upfront capital cost, financing structure, or return threshold prevents commitment despite technical viability.

**Exemplar clusters:** c142, c143, c144

### p49 — Investment risk and bankability barriers

*tier: high, n_reps_min: 43, sources: high_13*

Financing fails to close or is non-competitive because the asset's risk profile, novelty, or time horizon does not match available financial instruments or investor risk tolerance. Distinct from capital threshold magnitude.

**Mechanism criterion:** Financing fails or is overpriced because risk perception or financial-instrument design cannot accommodate the project's characteristics.

**Exemplar clusters:** c145, c146, c147

### p50 — Cost structure and unit-economics infeasibility

*tier: high, n_reps_min: 52, sources: high_08*

Operating economics fail because cost structure — fixed/variable composition, dominant component, scale disadvantage — exceeds achievable revenue or competitive benchmark at the achievable scale or utilisation.

**Mechanism criterion:** Total or unit cost structurally exceeds value or competing benchmark due to cost composition or scale disadvantage.

**Exemplar clusters:** c148, c149, c150

### p51 — Volatile or correlated price exposure

*tier: core, n_reps_min: 58, sources: core_20*

Project viability is undermined by external price volatility or correlation in inputs, outputs, or currency that exceeds what commercial structures can absorb or hedge.

**Mechanism criterion:** External price volatility or correlation erodes project viability beyond the commercial structure's ability to hedge.

**Exemplar clusters:** c151, c152, c153

### p52 — Price signal absent, distorted, or perverse

*tier: high, n_reps_min: 52, sources: high_09*

A pricing, tariff, or settlement mechanism transmits a signal misaligned with underlying physical cost or value, distorting behaviour or producing perverse responses.

**Mechanism criterion:** A price, tariff, or settlement signal does not reflect underlying cost or value, producing misaligned behaviour.

**Exemplar clusters:** c154, c155, c156

### p53 — Value not capturable through market mechanisms

*tier: high, n_reps_min: 51, sources: high_10*

Demonstrated value cannot be commercialised because no market mechanism, settlement product, methodology, or contract pathway exists to translate it into revenue. A missing-market structural failure.

**Mechanism criterion:** Value created cannot be captured because no market mechanism translates it into revenue.

**Exemplar clusters:** c157, c158, c159

### p54 — Market structure and incumbent advantage

*tier: high, n_reps_min: 49, sources: high_11*

Outcomes deviate from competitive efficiency because of market concentration, incumbent power, or structural barriers to entry/access, systematically disadvantaging new entrants or technologies.

**Mechanism criterion:** Market structure or incumbent power systematically distorts competitive outcomes for new technologies or actors.

**Exemplar clusters:** c160, c161, c162

### p55 — Vendor lock-in and proprietary closure

*tier: core, n_reps_min: 59, sources: core_28*

Proprietary control by a vendor — over IP, interfaces, parts, certification, or credentials — prevents independent third-party action, substitution, or engagement with a system component.

**Mechanism criterion:** Proprietary closure or vendor-controlled access blocks independent action, substitution, or third-party engagement.

**Exemplar clusters:** c163, c164, c165

### p56 — Lock-in, switching costs, and stranded-asset risk

*tier: boundary, n_reps_min: 41, sources: bdry_18*

Path-dependent prior commitments, sunk capital, or installed base structurally prevent adoption of better alternatives because switching cost exceeds incremental benefit, or expose the asset to stranding risk. Distinct from vendor lock-in: concerns the user's prior commitment, not vendor closure.

**Mechanism criterion:** Prior irreversible commitments structurally constrain optionality or expose to stranding risk.

**Exemplar clusters:** c166, c167, c168

### p57 — Supply chain and lead-time disruption

*tier: core, n_reps_min: 59, sources: core_29*

External supply-chain dynamics — availability, lead time, transport, or supplier capacity — disrupt receipt of required materials, equipment, or services for project delivery or operations.

**Mechanism criterion:** External supply-chain disruption or lead-time exposure impairs procurement of required goods or services.

**Exemplar clusters:** c169, c170, c171

### p58 — End-of-life, recycling, and circularity gaps

*tier: boundary, n_reps_min: 36, sources: bdry_07*

An asset's or material's end-of-life, recycling, or disposal pathway is missing, infeasible, or uneconomic, creating waste, stranded value, or environmental cost.

**Mechanism criterion:** End-of-life, recycling, or disposal pathway is missing, inadequate, or uneconomic.

**Exemplar clusters:** c172, c173, c174

### p59 — Regulatory framework absence for novel cases

*tier: core, n_reps_min: 59, sources: core_21*

No applicable regulatory framework, classification, or approval pathway exists for the activity in question, blocking or stalling progress because regulators have not yet defined how to govern it.

**Mechanism criterion:** An activity is blocked because no regulatory framework or approval pathway has been defined for it.

**Exemplar clusters:** c175, c176, c177

### p60 — Regulatory framework misalignment with current reality

*tier: boundary, n_reps_min: 24, sources: bdry_02*

An applicable regulation imposes inappropriate or perverse requirements because it was calibrated for a different technology, scale, or context, embedding stale assumptions. Distinct from absence: regulation exists and applies but misfits.

**Mechanism criterion:** An existing regulation produces perverse or inappropriate outcomes because its underlying assumptions no longer match current technology, scale, or context.

**Exemplar clusters:** c178, c179, c180

### p61 — Regulatory ambiguity and jurisdictional fragmentation

*tier: core, n_reps_min: 59, sources: core_22*

Compliance falters because regulatory rules, jurisdictions, or interpretations conflict, overlap, or fragment authority across multiple bodies, producing ambiguous or contradictory obligations.

**Mechanism criterion:** Multiple regulatory bodies, jurisdictions, or rule sets produce ambiguous, conflicting, or fragmented obligations.

**Exemplar clusters:** c181, c182, c183

### p62 — Regulatory process delay and procedural friction

*tier: core, n_reps_min: 59, sources: core_23*

The procedural execution of regulatory, certification, or approval processes imposes delay, rework, or cost beyond what the substantive rule content requires.

**Mechanism criterion:** Regulatory or approval procedural mechanics impose delay, rework, or cost beyond what rule substance requires.

**Exemplar clusters:** c184, c185, c186

### p63 — Compliance burden disproportionate to scale

*tier: boundary, n_reps_min: 33, sources: bdry_22*

Per-unit or fixed compliance, certification, or administrative overhead is large relative to activity size or value, deterring participation regardless of substantive rule. Particularly affects small-scale and distributed activities.

**Mechanism criterion:** Fixed compliance or administrative overhead is disproportionate to activity scale, suppressing participation.

**Exemplar clusters:** c187, c188, c189

### p64 — Compliance verification and enforcement gaps

*tier: core, n_reps_min: 59, sources: core_25*

An obligation exists but verification, monitoring, or enforcement mechanisms are insufficient to ensure adherence, leaving rules effectively non-binding or open to gaming.

**Mechanism criterion:** Enforcement, verification, or monitoring is insufficient to ensure adherence to a stated obligation.

**Exemplar clusters:** c190, c191, c192

### p65 — Policy uncertainty and instability

*tier: core, n_reps_min: 55, sources: core_24*

Decisions are deferred or distorted because policy or regulatory direction is uncertain, unstable, or expected to change over the relevant horizon, deterring commitment despite current readiness.

**Mechanism criterion:** Uncertainty or volatility about future policy state deters or distorts commitment.

**Exemplar clusters:** c193, c194, c195

### p66 — Subsidy and incentive design distortions

*tier: high, n_reps_min: 47, sources: high_12*

An incentive or subsidy scheme produces distorted, perverse, or excluding outcomes because of its structural design — eligibility, structure, gaming surface — rather than its level. Distinct from policy uncertainty.

**Mechanism criterion:** An incentive scheme's structural design causes outcomes to diverge from its stated objective.

**Exemplar clusters:** c196, c197, c198

### p67 — Funding instrument and milestone-structure misfit

*tier: core, n_reps_min: 59, sources: core_41*

Funding-instrument design — timing, milestones, eligibility, reporting, scope flexibility — is structurally misaligned with the realities of the activity it funds, impeding delivery.

**Mechanism criterion:** Funding-instrument design imposes timing, scope, or reporting structures incompatible with the funded activity.

**Exemplar clusters:** c199, c200, c201

### p68 — Contract structure and term misalignment

*tier: high, n_reps_min: 52, sources: high_14*

A contract's structure, scope, terms, or rigidity produces operational gaps, lock-ins, or unworkable obligations that block intended operation. Distinct from funding-instrument or incentive design.

**Mechanism criterion:** A contract's structure, scope, or terms produce gaps or unworkable obligations relative to actual situation.

**Exemplar clusters:** c202, c203, c204

### p69 — Procurement and tendering process pathologies

*tier: high, n_reps_min: 42, sources: high_28*

Procurement or tender process design causes adverse supplier selection, pricing, risk-allocation, or delivery outcomes independent of underlying technical capability or contract terms.

**Mechanism criterion:** Procurement or tender process design produces adverse selection, pricing, or contracting outcomes independent of technical fit.

**Exemplar clusters:** c205, c206, c207

### p70 — Multi-party coordination overhead

*tier: core, n_reps_min: 59, sources: core_26*

Action fails or stalls because coordination across multiple independent parties imposes friction, delay, gaps, or duplication that scales with party count.

**Mechanism criterion:** Coordinating actions across multiple independent parties produces delivery friction beyond what any one party can address.

**Exemplar clusters:** c208, c209, c210

### p71 — Responsibility and accountability gaps

*tier: boundary, n_reps_min: 40, sources: bdry_15*

An action goes unperformed because no party has clear, accepted responsibility or authority for it, or responsibility is contested between parties. Distinct from misaligned incentives: the issue is decision-rights ambiguity itself.

**Mechanism criterion:** An action goes unperformed because responsibility for it is unassigned, ambiguous, or contested.

**Exemplar clusters:** c211, c212, c213

### p72 — Misaligned incentives between actors

*tier: core, n_reps_min: 54, sources: core_27*

An outcome is suboptimal because decision rights and consequence-bearing reside with different parties whose incentives or payoffs are structurally divergent.

**Mechanism criterion:** Decision rights and consequence-bearing are split across parties with structurally divergent incentives.

**Exemplar clusters:** c214, c215, c216

### p73 — Information asymmetry between parties

*tier: core, n_reps_min: 58, sources: core_34*

An action is impeded because relevant information is held by one party but not communicated to another that needs it, due to confidentiality, strategic, or legal barriers.

**Mechanism criterion:** One party holds information another party needs, but it is not shared.

**Exemplar clusters:** c217, c218, c219

### p74 — Chicken-and-egg coordination deadlocks

*tier: core, n_reps_min: 55, sources: core_35*

Mutual prerequisite dependency between two parties or investments prevents either from moving first, blocking deployment of two-sided systems.

**Mechanism criterion:** Mutual prerequisite dependency between parties or investments prevents either from moving first.

**Exemplar clusters:** c220, c221, c222

### p75 — Trust, perception, and social licence

*tier: high, n_reps_min: 51, sources: high_16*

Project outcomes are degraded by trust, perception, or social-licence dynamics — including community opposition or social-licence withdrawal — independent of technical or economic substance.

**Mechanism criterion:** Trust, perception, or social-licence dynamics suppress adoption or progress regardless of technical or economic substance.

**Exemplar clusters:** c223, c224, c225

### p76 — Equity, distributional, and access barriers

*tier: high, n_reps_min: 52, sources: high_26*

Cost or benefit distribution falls inequitably on a population subgroup because of structural access, eligibility, or capacity barriers they cannot overcome.

**Mechanism criterion:** Cost or benefit distribution disadvantages a subgroup because of access, eligibility, or fixed-cost barriers.

**Exemplar clusters:** c226, c227, c228

### p77 — Customer recruitment, conversion, and retention friction

*tier: core, n_reps_min: 58, sources: core_33*

Programme participation falls short because the recruitment, conversion, onboarding, or retention pathway loses prospective participants at identifiable friction points or due to audience-design mismatch.

**Mechanism criterion:** Recruitment, onboarding, or retention pipeline design loses prospects between awareness and committed participation.

**Exemplar clusters:** c229, c230, c231

### p78 — Behavioural rebound and unintended response

*tier: high, n_reps_min: 42, sources: high_17*

An intervention triggers compensating behavioural or system responses that erode, offset, or reverse its intended effect.

**Mechanism criterion:** An intervention triggers a compensating response that erodes or reverses its intended effect.

**Exemplar clusters:** c232, c233, c234

### p79 — Demand response and aggregator delivery shortfall

*tier: core, n_reps_min: 55, sources: core_40*

Contracted demand-side or aggregated capacity fails to deliver expected response when called, due to participant, dispatch, measurement, or aggregation-layer issues.

**Mechanism criterion:** Aggregated or contracted demand-response capacity under-delivers at activation.

**Exemplar clusters:** c235, c236, c237

### p80 — Workforce skills and capability scarcity

*tier: high, n_reps_min: 53, sources: high_15*

A required combination of skills, training, specialist expertise, or labour capacity is unavailable when and where needed to deliver the work.

**Mechanism criterion:** Required human capability or workforce capacity is insufficient to deliver the work at the required time and place.

**Exemplar clusters:** c238, c239, c240

### p81 — Personnel turnover and key-person dependency

*tier: core, n_reps_min: 57, sources: core_30*

Loss or unavailability of specific personnel disrupts continuity of agreements, knowledge, or relationships because critical capability was concentrated in those individuals.

**Mechanism criterion:** Loss of specific personnel disrupts continuity because critical knowledge or relationships were concentrated in them.

**Exemplar clusters:** c241, c242, c243

### p82 — Manual process bottlenecks and automation gaps

*tier: core, n_reps_min: 58, sources: core_42*

Operational performance is constrained because a process step is performed manually where automation would be required for scale, accuracy, or speed.

**Mechanism criterion:** A manual process step caps throughput, introduces errors, or prevents scaling because it has not been automated.

**Exemplar clusters:** c244, c245, c246

### p83 — Project planning, scoping, and contingency inadequacy

*tier: core, n_reps_min: 59, sources: core_31*

Project execution is impaired because upfront planning, scoping, estimation, or contingency did not adequately anticipate the work required, causing rework or capability gaps when reality diverges from plan.

**Mechanism criterion:** Inadequate upfront planning, scoping, or contingency causes downstream rework or capability gaps.

**Exemplar clusters:** c247, c248, c249

### p84 — Late discovery forcing rework

*tier: core, n_reps_min: 57, sources: core_32*

Decision-relevant information surfaces after a commitment point at which acting on it would have been substantially cheaper, forcing costly rework or redesign.

**Mechanism criterion:** An issue or requirement is identified after a commitment point, forcing costly rework that earlier discovery would have avoided.

**Exemplar clusters:** c250, c251, c252

### p85 — Schedule cascade and dependency delays

*tier: boundary, n_reps_min: 34, sources: bdry_05*

An initial delay or disruption is amplified into broader schedule failure because activities are sequentially dependent and lack parallel paths or buffer. Concerns dependency topology rather than the originating shock.

**Mechanism criterion:** Sequential dependency structure causes a single delay to cascade across the project schedule.

**Exemplar clusters:** c253, c254, c255

### p86 — Conservative-margin and over-specification bias

*tier: high, n_reps_min: 51, sources: high_22*

Cost, curtailment, or scope is unnecessarily inflated because conservative responses to uncertainty exceed what physical or operational risk justifies, driving systematic over-design or excess restriction.

**Mechanism criterion:** Conservatism in response to uncertainty drives systematic over-design or excess restriction relative to actual need.

**Exemplar clusters:** c256, c257, c258

## Notes

All 86 input classes were retained as distinct parents — no consolidation was needed because the boundary-tier classes were already deliberately differentiated from adjacent core/high parents (e.g. bdry_18 stranded-asset risk vs p55 vendor lock-in; bdry_25 legacy infrastructure vs p42 architectural rigidity; bdry_15 responsibility gaps vs p72 misaligned incentives). Output count = 86. Thematic ordering: (1) information & evaluation [p01–p15] covering data, measurement, models, validation, commissioning; (2) physical & resource limits [p16–p21]; (3) asset & process engineering [p22–p28]; (4) spatial & temporal mismatch [p29–p31]; (5) power-system & grid [p32–p34]; (6) control, IT & interfaces [p35–p43]; (7) systemic fragility [p44–p47]; (8) capital & economics [p48–p51]; (9) market design [p52–p56]; (10) supply chain & lifecycle [p57–p58]; (11) regulation & policy [p59–p66]; (12) commercial instruments [p67–p69]; (13) coordination & social [p70–p79]; (14) workforce & execution [p80–p86]. Tensions: p55/p56 (vendor lock-in vs path-dependent stranding) and p42/p43 (architectural rigidity vs legacy installed base) are deliberately kept separate per boundary-tier rationale; PMs scanning for either should find both adjacent.
