# v2 parent set — consolidated from 59-rep ensemble

Single Opus 4.7 call. 43 core mechanism classes (≥90% rep agreement) consolidated into final v2 parent definitions; 28 high-tier classes (70-89%) judged for promote/hold/merge.

**Cost:** $0.39, 152s wall.

**v2 core parents:** 43
**High-tier verdicts:** {'promote': 27, 'merge_into_*': 1}

## v2 Parent definitions (core)

| parent | name | mechanism criterion |
|---|---|---|
| p01 | Missing or inaccessible data | A required information artefact is structurally absent, unrecorded, or inaccessible at the point of  |
| p02 | Data quality, format, and semantic defects | Available data produces wrong or unusable downstream outputs because of quality, format, schema, sem |
| p03 | Measurement and sensing limitations | An instrument or measurement method fails to faithfully observe its target physical quantity due to  |
| p04 | Model and forecast representational error | A model, simulation, or forecast produces inaccurate outputs because of its internal representation  |
| p05 | Mechanism understanding and scientific knowledge gap | Insufficient mechanistic or scientific understanding of the relevant phenomenon prevents reliable de |
| p06 | Test, validation, and verification coverage gaps | A defect, behaviour, or non-compliance escapes detection because the verification regime does not ex |
| p07 | Lab-to-field and pilot-to-scale translation failure | Performance demonstrated at one scale or context fails to transfer because the conditions enabling i |
| p08 | Material, chemical, and physical-property limits | A failure or hard limit is the direct consequence of a material's, chemical's, or substance's intrin |
| p09 | Equipment operating outside design envelope | An asset is operated under conditions that exceed or differ materially from its design envelope, pro |
| p10 | Environmental and weather exposure | An external environmental, weather, biological, or natural event physically degrades, damages, or di |
| p11 | Spatial, geometric, and siting constraints | A spatial, geometric, terrain, or land-availability constraint physically blocks or constrains deplo |
| p12 | Capacity, sizing, and headroom shortfall | A specific asset's or interface's installed capacity, rating, duration, or headroom is structurally  |
| p13 | Manufacturing, fabrication, and installation defects | A defect or variation introduced during manufacturing, fabrication, or installation causes operation |
| p14 | Inverter-based resource and grid-stability dynamics | A power-system electrical or stability phenomenon arises from inverter-based resource behaviour inco |
| p15 | Control logic, configuration, and protection errors | An adjustable parameter, control rule, threshold, or coordination logic is wrong or miscoordinated,  |
| p16 | Interoperability and interface incompatibility | Two systems fail to interoperate because their interfaces, protocols, formats, or specifications are |
| p17 | Cybersecurity, authentication, and access-control exposure | Security, authentication, or access-control mechanisms cause failure, expose risk, or impede legitim |
| p18 | Temporal mismatch between supply and demand | Supply and demand or two coupled processes are misaligned in time such that the resource cannot be u |
| p19 | Coupled trade-offs and competing objectives | An irreducible coupling between two performance objectives prevents simultaneous optimisation, so ga |
| p20 | Optimisation objective and metric misspecification | The chosen optimisation objective, metric, or scoring rule produces outcomes systematically misalign |
| p21 | Heterogeneity defeats one-size-fits-all design | A uniform or standardised design produces poor outcomes because real-world variation across the targ |
| p22 | Capital cost and upfront-investment barriers | Upfront capital cost, financing structure, or return threshold prevents commitment despite technical |
| p23 | Volatile or correlated price exposure | External price volatility or correlation erodes project viability beyond the commercial structure's  |
| p24 | Hard-to-abate residual emissions | Further decarbonisation is constrained because residual emissions arise from process or feedstock ch |
| p25 | Regulatory framework absence or gap | No applicable regulatory framework, classification, or approval pathway exists for the activity in q |
| p26 | Regulatory ambiguity and jurisdictional fragmentation | Regulatory rules, jurisdictions, or interpretations conflict, overlap, or fragment authority across  |
| p27 | Regulatory process delay and procedural friction | Regulatory or approval procedural mechanics impose delay, rework, or cost beyond what rule substance |
| p28 | Policy uncertainty and instability | Uncertainty or instability in future policy or regulatory state deters or distorts commitment despit |
| p29 | Compliance verification and enforcement gaps | An obligation is not delivered in practice because verification, monitoring, or enforcement mechanis |
| p30 | Multi-party coordination overhead | Coordinating actions across multiple independent parties produces delivery friction, gaps, or duplic |
| p31 | Misaligned incentives between actors | Decision-rights and consequence-bearing are split across parties with structurally divergent incenti |
| p32 | Information asymmetry between parties | One party holds information another party needs, but it is not shared due to confidentiality, strate |
| p33 | Chicken-and-egg coordination deadlocks | Mutual prerequisite dependency between two parties or investments prevents either from progressing w |
| p34 | Vendor lock-in and proprietary closure | Proprietary closure or vendor-controlled access blocks independent action, substitution, or third-pa |
| p35 | Supply chain and logistics disruption | External supply-chain disruption, lead-time exposure, or sourcing constraint impairs procurement of  |
| p36 | Personnel turnover and key-person dependency | Loss or change of specific personnel disrupts continuity because critical knowledge or relationships |
| p37 | Project planning and scoping inadequacy | Inadequate upfront planning, scoping, estimation, or contingency causes execution shortfall when rea |
| p38 | Late discovery forcing rework | Information surfaces after a commitment point at which acting on it would have been substantially ch |
| p39 | Customer recruitment and conversion friction | Recruitment, conversion, onboarding, or retention pipeline design loses prospects between awareness  |
| p40 | Single point of failure and shared-resource exposure | A single shared dependency creates a failure mode that affects many downstream functions simultaneou |
| p41 | Demand response and aggregator delivery shortfall | Aggregated or contracted demand-response capacity under-delivers at activation due to participation, |
| p42 | Funding instrument and milestone-structure misfit | Funding-instrument design imposes timing, scope, or reporting structures incompatible with the activ |
| p43 | Manual process bottlenecks and automation gaps | A manual process step caps throughput, introduces errors, or prevents scaling because it has not bee |

### Full descriptions

#### p01 — Missing or inaccessible data

A required information artefact does not exist, was never collected, or cannot be obtained by the party that needs it at the time of need. Membership requires that the data gap is structural absence or inaccessibility rather than a quality defect in available data.

**Mechanism criterion:** A required information artefact is structurally absent, unrecorded, or inaccessible at the point of need.


#### p02 — Data quality, format, and semantic defects

Data exists and is accessible, but its quality, format, schema, semantics, or integration produces wrong, unusable, or misleading downstream outputs. Membership requires that the defect lies in the data artefact itself rather than its absence or in the model consuming it.

**Mechanism criterion:** Available data produces wrong or unusable downstream outputs because of quality, format, schema, semantic, or integration defects.


#### p03 — Measurement and sensing limitations

A sensor or measurement instrument cannot faithfully observe its target physical quantity due to its physical, instrumental, or deployment characteristics. Membership requires the limitation to be intrinsic to the instrument or method, not to data handling downstream.

**Mechanism criterion:** An instrument or measurement method fails to faithfully observe its target physical quantity due to its own design, capability, or deployment characteristics.


#### p04 — Model and forecast representational error

A model, simulation, or forecast yields outputs that diverge from reality because of structural assumptions, parameterisation, scope, or training-data limits in the model itself. Membership requires the error to originate in the model's representation rather than in input data absence or quality.

**Mechanism criterion:** A model, simulation, or forecast produces inaccurate outputs because of its internal representation rather than missing or defective inputs.


#### p05 — Mechanism understanding and scientific knowledge gap

Progress is constrained because scientific or engineering understanding of the underlying mechanism is insufficient for reliable prediction, control, or scale-up. Membership requires the gap to be in fundamental knowledge or characterisation rather than in data, models, or instrumentation.

**Mechanism criterion:** Insufficient mechanistic or scientific understanding of the relevant phenomenon prevents reliable design, prediction, or replication.


#### p06 — Test, validation, and verification coverage gaps

A defect or condition escapes detection because the verification regime does not exercise the relevant stimuli, durations, or environments. Membership requires that the failure mode existed but was not caught by validation activities whose scope or methodology was inadequate.

**Mechanism criterion:** A defect, behaviour, or non-compliance escapes detection because the verification regime does not exercise the relevant conditions, duration, or stimuli.


#### p07 — Lab-to-field and pilot-to-scale translation failure

A solution validated at one scale, site, or controlled environment fails when transferred because the conditions enabling its success do not transfer to the deployment context. Membership requires demonstrated success at validation scale and structural failure at the target scale.

**Mechanism criterion:** Performance demonstrated at one scale or context fails to transfer because the conditions enabling it do not hold at the target scale or context.


#### p08 — Material, chemical, and physical-property limits

An intrinsic physical, chemical, thermal, or material property bounds, degrades, or precludes the desired behaviour regardless of design choices within the current architecture. Membership requires the limit to follow directly from substance properties rather than from operating choices or workmanship.

**Mechanism criterion:** A failure or hard limit is the direct consequence of a material's, chemical's, or substance's intrinsic property under operating conditions.


#### p09 — Equipment operating outside design envelope

Performance degrades or equipment fails because operating conditions exceed or differ from the design envelope assumed in its specification. Membership requires capable equipment exposed to conditions beyond what its design contemplated.

**Mechanism criterion:** An asset is operated under conditions that exceed or differ materially from its design envelope, producing degradation, derating, or failure.


#### p10 — Environmental and weather exposure

An exogenous environmental, weather, biological, or natural-event factor acts physically on assets or operations to cause damage, degradation, or disruption. Membership requires an external natural agent rather than an operational, design, or material-property cause.

**Mechanism criterion:** An external environmental, weather, biological, or natural event physically degrades, damages, or disrupts assets or operations.


#### p11 — Spatial, geometric, and siting constraints

Available physical space, geometry, terrain, or location characteristics block or constrain the intended deployment, operation, or maintenance. Membership requires a binding spatial or land-availability constraint independent of network, regulatory, or social factors.

**Mechanism criterion:** A spatial, geometric, terrain, or land-availability constraint physically blocks or constrains deployment, operation, or maintenance.


#### p12 — Capacity, sizing, and headroom shortfall

A specific component, asset, or interface's installed capacity, rating, duration, or headroom is structurally insufficient for the load or service demanded of it. Membership requires a sizing mismatch at a specific asset rather than a network-wide or temporal-mismatch issue.

**Mechanism criterion:** A specific asset's or interface's installed capacity, rating, duration, or headroom is structurally insufficient relative to the demand placed on it.


#### p13 — Manufacturing, fabrication, and installation defects

A defect or variability introduced during production, fabrication, assembly, or installation propagates into operational failure or quality loss in the deployed unit. Membership requires the root cause to be in workmanship or production variability rather than design, materials, or operation.

**Mechanism criterion:** A defect or variation introduced during manufacturing, fabrication, or installation causes operational failure or performance loss in deployment.


#### p14 — Inverter-based resource and grid-stability dynamics

An undesired electrical or stability phenomenon arises from inverter-based resource behaviour or from displacement of synchronous machine services that legacy frameworks were not designed for. Membership requires a power-system dynamic specifically tied to IBR characteristics.

**Mechanism criterion:** A power-system electrical or stability phenomenon arises from inverter-based resource behaviour incompatible with frameworks built around synchronous plant.


#### p15 — Control logic, configuration, and protection errors

An adjustable parameter, control rule, threshold, or protection coordination is wrong or miscoordinated, causing incorrect system behaviour from otherwise capable equipment. Membership requires the error to lie in settings or logic rather than hardware capability or software defects.

**Mechanism criterion:** An adjustable parameter, control rule, threshold, or coordination logic is wrong or miscoordinated, causing incorrect system behaviour from otherwise capable equipment.


#### p16 — Interoperability and interface incompatibility

Integration fails at a defined boundary because interface specifications, protocols, formats, APIs, or semantics do not align between components or parties. Membership requires a mismatch at a specific interface rather than absence of any standard at all.

**Mechanism criterion:** Two systems fail to interoperate because their interfaces, protocols, formats, or specifications are mutually incompatible or undefined.


#### p17 — Cybersecurity, authentication, and access-control exposure

A failure, friction, or risk exposure arises from cybersecurity, authentication, credential, or access-control mechanisms rather than from underlying functionality. Membership requires the security architecture itself to be the mechanism — whether through breach, lockout, or operational impediment.

**Mechanism criterion:** Security, authentication, or access-control mechanisms cause failure, expose risk, or impede legitimate operation.


#### p18 — Temporal mismatch between supply and demand

Supply and demand or two coupled processes are misaligned in time such that one's output is unavailable when the other needs it. Membership requires a timing or seasonal mismatch driving curtailment, shortfall, or storage demand rather than a spatial or sizing gap.

**Mechanism criterion:** Supply and demand or two coupled processes are misaligned in time such that the resource cannot be used when needed.


#### p19 — Coupled trade-offs and competing objectives

Two desirable objectives are coupled through shared physics or constraints such that they cannot be simultaneously optimised; gain on one axis structurally produces loss on the other. Membership requires an irreducible coupling rather than a solvable engineering trade-off.

**Mechanism criterion:** An irreducible coupling between two performance objectives prevents simultaneous optimisation, so gain in one structurally produces loss in the other.


#### p20 — Optimisation objective and metric misspecification

Outcomes diverge from intent because the chosen optimisation objective, evaluation metric, or scoring rule does not align with the underlying intended goal. Membership requires the metric design itself to drive perverse behaviour, not its measurement or enforcement.

**Mechanism criterion:** The chosen optimisation objective, metric, or scoring rule produces outcomes systematically misaligned with the intended system value.


#### p21 — Heterogeneity defeats one-size-fits-all design

A standardised approach fails because real-world variation across the target population, sites, or conditions exceeds what a single uniform configuration can absorb. Membership requires that population heterogeneity, not the design's intrinsic adequacy, is what breaks it.

**Mechanism criterion:** A uniform or standardised design produces poor outcomes because real-world variation across the target population exceeds what one configuration can absorb.


#### p22 — Capital cost and upfront-investment barriers

Investment is blocked or deferred because upfront capital, payback horizon, or financing-instrument structure does not meet investor or adopter return criteria despite technical viability. Membership requires the barrier to be the capital threshold or its financing structure, not ongoing cost competitiveness.

**Mechanism criterion:** Upfront capital cost, financing structure, or return threshold prevents commitment despite technical viability.


#### p23 — Volatile or correlated price exposure

Project viability is undermined by external price volatility or correlation in inputs, outputs, or currency that exceeds what commercial structures can absorb or hedge. Membership requires exogenous price movements rather than design-level cost-structure issues.

**Mechanism criterion:** External price volatility or correlation erodes project viability beyond the commercial structure's ability to hedge.


#### p24 — Hard-to-abate residual emissions

Decarbonisation or improvement is structurally blocked because residual emissions or losses arise from processes lacking commercially viable low-emission alternatives. Membership requires the absence of an abatement pathway as the binding constraint, not cost or policy.

**Mechanism criterion:** Further decarbonisation is constrained because residual emissions arise from process or feedstock characteristics with no commercially viable low-emissions alternative.


#### p25 — Regulatory framework absence or gap

An activity is blocked or stalled because no applicable regulatory framework, classification, or approval pathway has been defined for it. Membership requires absence or paradigm mismatch rather than conflict, delay, or uncertainty within an existing framework.

**Mechanism criterion:** No applicable regulatory framework, classification, or approval pathway exists for the activity in question.


#### p26 — Regulatory ambiguity and jurisdictional fragmentation

Compliance falters because multiple regulatory bodies, jurisdictions, or rule sets impose ambiguous, conflicting, or fragmented obligations on the same activity. Membership requires the conflict or overlap to be the mechanism, not absence of any rule or its slow execution.

**Mechanism criterion:** Regulatory rules, jurisdictions, or interpretations conflict, overlap, or fragment authority across multiple bodies.


#### p27 — Regulatory process delay and procedural friction

Project execution is delayed or burdened by the timing, pace, or procedural mechanics of regulatory and approval processes rather than the substance of the rules. Membership requires the cost to come from procedural execution rather than rule content or absence.

**Mechanism criterion:** Regulatory or approval procedural mechanics impose delay, rework, or cost beyond what rule substance requires.


#### p28 — Policy uncertainty and instability

Decisions are deferred or distorted because policy or regulatory direction is uncertain, unstable, or expected to change over the relevant horizon. Membership requires forward-signal volatility, not the substance of any current rule.

**Mechanism criterion:** Uncertainty or instability in future policy or regulatory state deters or distorts commitment despite current readiness.


#### p29 — Compliance verification and enforcement gaps

A rule or obligation exists but verification, monitoring, or enforcement is insufficient to ensure adherence in practice. Membership requires the gap to be in detection or enforcement rather than rule design or absence.

**Mechanism criterion:** An obligation is not delivered in practice because verification, monitoring, or enforcement mechanisms are absent or inadequate.


#### p30 — Multi-party coordination overhead

Action stalls or fails because coordination across multiple independent parties imposes friction, delays, or because responsibility is split, undefined, or contested. Membership requires the friction to scale with party count rather than from misaligned incentives or information asymmetries between two parties.

**Mechanism criterion:** Coordinating actions across multiple independent parties produces delivery friction, gaps, or duplication beyond what any one party can address.


#### p31 — Misaligned incentives between actors

An outcome is suboptimal because decision rights and consequence-bearing reside with different parties whose payoffs are structurally divergent. Membership requires a structural split-incentive mechanism rather than coordination overhead or information asymmetry alone.

**Mechanism criterion:** Decision-rights and consequence-bearing are split across parties with structurally divergent incentives, producing misaligned action.


#### p32 — Information asymmetry between parties

An action is impeded because relevant information is held by one party but not communicated to another that needs it, due to confidentiality, strategic, or legal barriers. Membership requires asymmetric information across parties rather than absence of information altogether.

**Mechanism criterion:** One party holds information another party needs, but it is not shared due to confidentiality, strategic, or legal barriers.


#### p33 — Chicken-and-egg coordination deadlocks

Mutual prerequisite dependency between two parties or investments prevents either from moving first. Membership requires a two-sided commitment trap rather than general multi-party coordination overhead or single-actor risk aversion.

**Mechanism criterion:** Mutual prerequisite dependency between two parties or investments prevents either from progressing without the other moving first.


#### p34 — Vendor lock-in and proprietary closure

Proprietary control over technology, interfaces, parts, certification, or credentials prevents independent action, substitution, or third-party engagement. Membership requires deliberate or structural closure by a vendor rather than absence of standards or interoperability mismatches.

**Mechanism criterion:** Proprietary closure or vendor-controlled access blocks independent action, substitution, or third-party engagement with a system component.


#### p35 — Supply chain and logistics disruption

External supply-chain dynamics — availability, lead time, transport, or supplier capacity — disrupt project delivery or operations. Membership requires the disruption to lie in upstream sourcing rather than internal manufacturing defects or planning errors.

**Mechanism criterion:** External supply-chain disruption, lead-time exposure, or sourcing constraint impairs procurement of required goods or services.


#### p36 — Personnel turnover and key-person dependency

Loss or unavailability of specific personnel disrupts continuity of progress, knowledge, agreements, or relationships that the project depended on. Membership requires concentration of critical capability or relationships in identifiable individuals.

**Mechanism criterion:** Loss or change of specific personnel disrupts continuity because critical knowledge or relationships were concentrated in those individuals.


#### p37 — Project planning and scoping inadequacy

Project execution is impaired because upfront planning, scoping, estimation, or contingency did not adequately anticipate the work required. Membership requires the failure to originate in planning quality rather than late-emerging information or external disruption.

**Mechanism criterion:** Inadequate upfront planning, scoping, estimation, or contingency causes execution shortfall when reality diverges from plan.


#### p38 — Late discovery forcing rework

Decision-relevant information surfaces after a commitment point at which acting on it would have been substantially cheaper, forcing costly rework or redesign. Membership requires a lifecycle-timing mechanism rather than a planning-quality or coverage-gap mechanism.

**Mechanism criterion:** Information surfaces after a commitment point at which acting on it would have been substantially cheaper, forcing rework.


#### p39 — Customer recruitment and conversion friction

Programme participation falls short because the recruitment, conversion, onboarding, or retention pathway loses prospective participants at identifiable friction points. Membership requires the loss to occur in the participation funnel rather than from product value or equity barriers.

**Mechanism criterion:** Recruitment, conversion, onboarding, or retention pipeline design loses prospects between awareness and committed participation.


#### p40 — Single point of failure and shared-resource exposure

A shared centralised dependency creates a failure mode that simultaneously impairs many dependent systems through correlated common-mode failure or capacity bottleneck. Membership requires correlated impact across multiple dependents from one shared dependency.

**Mechanism criterion:** A single shared dependency creates a failure mode that affects many downstream functions simultaneously.


#### p41 — Demand response and aggregator delivery shortfall

Aggregated or contracted demand-side capacity under-delivers at activation due to participant behaviour, dispatch design, or measurement-layer issues. Membership requires shortfall at the aggregation or response layer rather than from observability or contracting issues alone.

**Mechanism criterion:** Aggregated or contracted demand-response capacity under-delivers at activation due to participation, dispatch, or measurement-layer issues.


#### p42 — Funding instrument and milestone-structure misfit

Funding-instrument design — its timing, milestones, eligibility, reporting, or scope flexibility — is structurally misaligned with the activity it funds, impeding delivery. Membership requires the misfit to lie in instrument structure rather than capital availability or financing risk.

**Mechanism criterion:** Funding-instrument design imposes timing, scope, or reporting structures incompatible with the activity it funds.


#### p43 — Manual process bottlenecks and automation gaps

Operational performance is constrained because a process step is performed manually where automation would be required for scale, accuracy, or speed. Membership requires the bottleneck to be the absence of automation rather than software fragility or workforce shortage.

**Mechanism criterion:** A manual process step caps throughput, introduces errors, or prevents scaling because it has not been automated.



## High-tier verdicts (28 candidates)

| class | verdict | reason |
|---|---|---|
| high_01 | promote | Network capacity constraints are a distinct power-system mechanism not captured by asset-level sizing (p12) or grid-stability (p14), and PMs need it as a first-class diagnostic. |
| high_02 | promote | Cadence/latency mismatches in coupled control loops are mechanistically distinct from communication failures and from generic interoperability issues. |
| high_03 | promote | Communication channel and connectivity failures are a high-frequency infrastructure mechanism distinct from interoperability mismatches and from cadence/timing. |
| high_04 | promote | Standards absence/obsolescence is a distinct ecosystem-level mechanism that interoperability (p16) addresses only at the bilateral interface level. |
| high_05 | promote | Software/firmware/IT fragility is mechanistically distinct from data defects, control configuration, and manual-process gaps and is core to modern energy-tech failures. |
| high_06 | promote | Feedstock and input-quality variability is a distinct process-input mechanism not covered by material-property limits (p08) or design-envelope (p09). |
| high_07 | promote | Geographic/locational mismatch is a distinct spatial mechanism that p11 (siting) and p18 (temporal) do not capture. |
| high_08 | promote | Cost-structure and unit-economics infeasibility is a fundamental commercial mechanism distinct from upfront capital barriers (p22) and price volatility (p23). |
| high_09 | promote | Distorted price/tariff signals are a distinct market-design mechanism that drives behaviour misalignment beyond incentive-design (high_12) or metric-misspecification (p20). |
| high_10 | promote | Value not capturable by available market mechanisms is a distinct missing-market structural failure central to climate-tech commercialisation. |
| high_11 | promote | Market structure and incumbent advantage operate at a different level (concentration, entry barriers) from missing markets and price signal distortion. |
| high_12 | promote | Subsidy/incentive design distortions are a distinct policy-instrument mechanism that PMs need to scan for separately from policy uncertainty (p28). |
| high_13 | promote | Investment risk and bankability barriers operate on risk-perception and instrument-fit rather than on capital threshold magnitude (p22). |
| high_14 | promote | Contract structure misalignment is a distinct commercial-instrument mechanism that funding-instrument misfit (p42) and incentive design (high_12) do not cover. |
| high_15 | promote | Workforce skill scarcity is a high-frequency capability-gap mechanism mechanistically distinct from personnel turnover (p36) and planning inadequacy (p37). |
| high_16 | promote | Trust and social licence is a distinct socio-political mechanism with strong evidentiary support that no core parent captures. |
| high_17 | promote | Behavioural rebound is a distinct intervention-response mechanism, although it overlaps with high_24; both deserve separate treatment given evidence support. |
| high_18 | promote | Architectural rigidity is a distinct system-design mechanism not captured by interoperability or coupled trade-offs. |
| high_19 | promote | Technology immaturity is a high-frequency, top-level deployment-readiness mechanism distinct from lab-to-field translation (p07) which assumes successful validation. |
| high_20 | promote | Selection/sampling representativeness bias is a distinct evaluation-validity mechanism not captured by data quality (p02) or coverage gaps (p06). |
| high_21 | promote | Counterfactual/baseline measurement difficulty is a distinct attribution mechanism critical for climate impact and settlement claims. |
| high_22 | promote | Conservative-margin and over-specification bias is a distinct decision-under-uncertainty mechanism that drives systematic over-build. |
| high_23 | promote | Externalities and lifecycle accounting omissions is a distinct framing/scope-of-analysis mechanism not captured by metric misspecification (p20). |
| high_24 | merge_into_p19 | Unintended secondary consequences from interventions overlap substantively with behavioural rebound (high_17, promoted) and with coupled trade-offs (p19); merging into p19 captures the system-coupling essence while rebound stays distinct. |
| high_25 | promote | Visibility and observability gaps are a distinct operational-awareness mechanism critical for distributed/DER systems and not captured by measurement limits (p03) or data absence (p01). |
| high_26 | promote | Equity and distributional barriers are a distinct outcome-incidence mechanism well-supported and not captured by recruitment friction (p39) or trust (high_16). |
| high_27 | promote | Subsurface/resource characterisation uncertainty is a distinct pre-commitment natural-resource mechanism not adequately covered by mechanism-knowledge gap (p05) or measurement limits (p03). |
| high_28 | promote | Procurement/tender process pathologies are a distinct commercial-process mechanism not captured by contract structure (high_14) or coordination overhead (p30). |

## Notes

I've ordered parents in thematic families: information/measurement/models (p01–p05); validation and translation (p06–p07); physical/material/environmental (p08–p11); asset and component-level engineering (p12–p15); integration and security (p16–p17); temporal and design trade-offs (p18–p21); commercial and market economics (p22–p24); regulatory and policy (p25–p29); coordination and institutional (p30–p34); execution and delivery (p35–p43). Of 28 high-tier classes, 27 promoted and 1 merged (high_24 into p19), reflecting that the high-tier cohort largely represents legitimate distinct mechanisms with slightly lower naming convergence rather than redundant ones. The PM-facing v2 set will thus be ~70 parents — large but each genuinely scannable as a distinct diagnostic axis. Notable residual redundancy worth flagging: p18 (temporal mismatch) vs high_07 (geographic mismatch) are siblings that could be unified at v3; high_17 (rebound) and high_24 (unintended consequences) are close but I kept rebound distinct as the more specific behavioural mechanism; p30 (coordination overhead) and p33 (chicken-and-egg) are siblings differing in party-count structure.