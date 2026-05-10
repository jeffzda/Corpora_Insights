# Cluster→primary+secondary parent assignment (boundary-mapping pilot)

You are assigning failure-mode clusters to one or two parent categories from a fixed taxonomy of 86 parents. For each cluster:

1. Assign a **primary parent** — the parent whose mechanism criterion the cluster's mechanism most cleanly satisfies.
2. **Optionally** assign a **secondary parent** — a different parent whose mechanism criterion the cluster's mechanism *also* genuinely satisfies.

## Critical rubric for secondary

A secondary parent is one whose mechanism criterion the cluster's mechanism **also genuinely satisfies** — not merely a parent that is topically adjacent, that the cluster could plausibly be discussed under, or that you would pick if forced to rank a runner-up.

**If no other parent's criterion is genuinely satisfied, return `secondary_parent_id: null`.**

Most clusters should have a single home; expect many `null` secondaries. A real secondary indicates structural mechanism overlap between parent categories, which is the analytical signal we are trying to measure. Don't manufacture one.

## Confidence rubric (applies to both primary and secondary)

- **high** — cluster mechanism is an unambiguous instance of the parent's criterion
- **medium** — cluster mechanism plausibly fits but partial match means it is not unambiguous
- **low** — cluster mechanism only weakly satisfies the criterion

Mechanism, not topic: a cluster about a different domain that fails through the same mechanism still belongs in the parent.

## Output

Strict JSONL, one record per cluster, in input order. No commentary, no preamble, no fences.

```json
{"cluster_id":"cNNN","primary_parent_id":"pNN","primary_confidence":"low|medium|high","primary_rationale":"<≤25 words>","secondary_parent_id":"pNN or null","secondary_confidence":"low|medium|high or null","secondary_rationale":"<≤25 words or null>"}
```

## Parents (86 total)

- **p01** Missing or inaccessible data — *criterion:* A required information artefact is structurally absent, unrecorded, or inaccessible at the point of need.
- **p02** Data quality, format, and semantic defects — *criterion:* Available data produces wrong or unusable downstream outputs because of quality, format, schema, semantic, or integration defects.
- **p03** Measurement and sensing limitations — *criterion:* A sensor or measurement instrument fails to faithfully observe its target physical quantity due to physical or instrumental capability limits.
- **p04** Aggregation and granularity mismatch — *criterion:* Aggregation, averaging, or coarse granularity destroys individual-level information required for correct operation, attribution, or decision-making.
- **p05** Visibility and observability gaps — *criterion:* Insufficient observability or situational awareness over distributed assets, conditions, or populations prevents effective management.
- **p06** Documentation and configuration management gaps — *criterion:* An action fails because the relevant documentation or configuration record is missing, outdated, or has drifted from actual system state.
- **p07** Model and forecast representational error — *criterion:* A model, forecast, or simulation yields outputs materially diverging from reality because of how it represents the system, not because of missing inputs.
- **p08** Computational and algorithmic tractability limits — *criterion:* Computational or algorithmic resource requirements exceed what is available within the operational time window or fidelity required.
- **p09** Optimisation objective and metric misspecification — *criterion:* The chosen optimisation objective, metric, or scoring rule produces outcomes systematically misaligned with intended system value.
- **p10** Externalities and lifecycle accounting omissions — *criterion:* An analytical, accounting, or valuation framework omits material externalities, lifecycle effects, or boundary flows, biasing decisions or claims.
- **p11** Counterfactual and baseline measurement difficulty — *criterion:* Effect quantification or attribution fails because the required counterfactual baseline cannot be reliably measured or constructed.
- **p12** Sample, selection, and representativeness bias — *criterion:* Conclusions are biased because the observed sample is systematically unrepresentative of the population to which results will be applied.
- **p13** Test, validation, and verification coverage gaps — *criterion:* A defect or condition escapes detection because the verification regime does not exercise the relevant conditions, duration, or stimuli.
- **p14** Lab-to-field and pilot-to-scale translation failure — *criterion:* Performance demonstrated at one scale or controlled environment fails to transfer because deployment conditions, dynamics, or constraints diverge from the validation context.
- **p15** Commissioning, handover, and integration discovery failures — *criterion:* Failures emerge at first integrated operation or organisational handover that earlier phases did not detect.
- **p16** Mechanism understanding and scientific knowledge gaps — *criterion:* Insufficient mechanistic understanding prevents reliable prediction, control, or scale-up.
- **p17** Subsurface and resource characterisation uncertainty — *criterion:* Inability to characterise a natural resource before commitment, or its change after intervention, drives performance shortfall.
- **p18** Material, chemical, and physical-property limits — *criterion:* An intrinsic physical, chemical, thermal, or material property constrains, degrades, or precludes the desired behaviour.
- **p19** Coupled trade-offs and competing objectives — *criterion:* An irreducible coupling forces a trade-off where gain on one axis produces loss on another.
- **p20** Diminishing returns and saturation effects — *criterion:* Marginal benefit of additional input, capacity, or intervention falls sharply because the system is saturating or threshold-bound.
- **p21** Hard-to-abate residuals and decarbonisation ceilings — *criterion:* Decarbonisation is constrained because residuals arise from structural process or feedstock characteristics without commercial low-emission alternatives.
- **p22** Equipment operating outside design envelope — *criterion:* An asset is operated under conditions exceeding or differing from its design envelope, producing degradation, derating, or failure.
- **p23** Capacity, sizing, and headroom shortfall — *criterion:* An asset's rated capacity, duration, or headroom is structurally below the duty placed on it.
- **p24** Auxiliary loads and parasitic consumption — *criterion:* Auxiliary or parasitic consumption substantially reduces net deliverable output below gross capability.
- **p25** Feedstock and input variability — *criterion:* Input feedstock or material variability or contamination exceeds the tolerance of the consuming process.
- **p26** Manufacturing, fabrication, and installation defects — *criterion:* A defect originating in production, fabrication, or installation workmanship causes the deployed unit to fail or underperform.
- **p27** Environmental and external hazard exposure — *criterion:* An external environmental, weather, biological, or natural event physically degrades, damages, or disrupts assets or operations.
- **p28** Safety hazard and risk-classification consequences — *criterion:* A safety hazard or reclassification triggers cost, restriction, or design overhead disproportionate to ordinary engineering.
- **p29** Spatial, geometric, and siting constraints — *criterion:* A spatial, geometric, terrain, or land-availability constraint physically blocks or constrains deployment.
- **p30** Geographic and locational mismatch — *criterion:* Spatial separation between resource, demand, or infrastructure imposes a binding cost or feasibility penalty.
- **p31** Temporal and seasonal supply-demand mismatch — *criterion:* Temporal misalignment between when a resource is produced and when it is needed prevents direct utilisation.
- **p32** Network capacity and physical grid constraints — *criterion:* A physical electrical-network capacity, hosting, or topology constraint prevents or restricts intended power flows or connections.
- **p33** Inverter-based resource and grid-stability dynamics — *criterion:* Inverter-based resource dynamics interact with grid characteristics in ways incompatible with frameworks built around synchronous plant.
- **p34** Curtailment and headroom-allocation conflicts — *criterion:* An operational rule or allocation conflict forces non-utilisation of available output capacity or service.
- **p35** Control logic, configuration, and protection errors — *criterion:* An adjustable parameter, control rule, or coordination logic is wrong or miscoordinated, causing incorrect behaviour from capable equipment.
- **p36** Cadence, latency, and timing mismatch in control — *criterion:* A timing, cadence, or update-frequency mismatch between coupled processes causes incorrect or stale operation.
- **p37** Communication and connectivity failures — *criterion:* Information or commands fail to traverse a communication path correctly because of channel, bandwidth, or protocol-layer limits.
- **p38** Interoperability and interface incompatibility — *criterion:* Integration fails at a defined boundary because interface specifications, protocols, formats, or semantics do not align between parties.
- **p39** Standards absence, obsolescence, or fragmentation — *criterion:* A shared standard, benchmark, or methodology is missing, outdated, or inconsistent across actors.
- **p40** Software, firmware, and IT system fragility — *criterion:* A failure originates in software, firmware, or IT-platform characteristics rather than data, hardware, or external constraints.
- **p41** Cybersecurity, authentication, and access-control exposure — *criterion:* Security, authentication, or access-control mechanisms cause failure, expose risk, or impede legitimate operation.
- **p42** Architectural rigidity and modularity limits — *criterion:* Architectural coupling or absent modularity prevents independent modification, substitution, or scaling of subcomponents.
- **p43** Legacy infrastructure incompatibility — *criterion:* Legacy infrastructure structurally blocks new requirements because its embedded assumptions no longer match current needs.
- **p44** Single point of failure and shared-resource fragility — *criterion:* A shared centralised dependency creates correlated common-mode failure or bottleneck across multiple dependent functions.
- **p45** Aggregate correlation and concentration risk — *criterion:* Nominally independent units exhibit correlated or synchronised behaviour producing aggregate effects beyond individual analysis.
- **p46** Heterogeneity defeats one-size-fits-all design — *criterion:* A standardised design produces poor outcomes because real-world variation across the population exceeds what one configuration absorbs.
- **p47** Technology immaturity and readiness gap — *criterion:* The technology or its supporting ecosystem has not reached the maturity level required by the deployment context attempted.
- **p48** Capital cost and upfront-investment barriers — *criterion:* Upfront capital cost, financing structure, or return threshold prevents commitment despite technical viability.
- **p49** Investment risk and bankability barriers — *criterion:* Financing fails or is overpriced because risk perception or financial-instrument design cannot accommodate the project's characteristics.
- **p50** Cost structure and unit-economics infeasibility — *criterion:* Total or unit cost structurally exceeds value or competing benchmark due to cost composition or scale disadvantage.
- **p51** Volatile or correlated price exposure — *criterion:* External price volatility or correlation erodes project viability beyond the commercial structure's ability to hedge.
- **p52** Price signal absent, distorted, or perverse — *criterion:* A price, tariff, or settlement signal does not reflect underlying cost or value, producing misaligned behaviour.
- **p53** Value not capturable through market mechanisms — *criterion:* Value created cannot be captured because no market mechanism translates it into revenue.
- **p54** Market structure and incumbent advantage — *criterion:* Market structure or incumbent power systematically distorts competitive outcomes for new technologies or actors.
- **p55** Vendor lock-in and proprietary closure — *criterion:* Proprietary closure or vendor-controlled access blocks independent action, substitution, or third-party engagement.
- **p56** Lock-in, switching costs, and stranded-asset risk — *criterion:* Prior irreversible commitments structurally constrain optionality or expose to stranding risk.
- **p57** Supply chain and lead-time disruption — *criterion:* External supply-chain disruption or lead-time exposure impairs procurement of required goods or services.
- **p58** End-of-life, recycling, and circularity gaps — *criterion:* End-of-life, recycling, or disposal pathway is missing, inadequate, or uneconomic.
- **p59** Regulatory framework absence for novel cases — *criterion:* An activity is blocked because no regulatory framework or approval pathway has been defined for it.
- **p60** Regulatory framework misalignment with current reality — *criterion:* An existing regulation produces perverse or inappropriate outcomes because its underlying assumptions no longer match current technology, scale, or context.
- **p61** Regulatory ambiguity and jurisdictional fragmentation — *criterion:* Multiple regulatory bodies, jurisdictions, or rule sets produce ambiguous, conflicting, or fragmented obligations.
- **p62** Regulatory process delay and procedural friction — *criterion:* Regulatory or approval procedural mechanics impose delay, rework, or cost beyond what rule substance requires.
- **p63** Compliance burden disproportionate to scale — *criterion:* Fixed compliance or administrative overhead is disproportionate to activity scale, suppressing participation.
- **p64** Compliance verification and enforcement gaps — *criterion:* Enforcement, verification, or monitoring is insufficient to ensure adherence to a stated obligation.
- **p65** Policy uncertainty and instability — *criterion:* Uncertainty or volatility about future policy state deters or distorts commitment.
- **p66** Subsidy and incentive design distortions — *criterion:* An incentive scheme's structural design causes outcomes to diverge from its stated objective.
- **p67** Funding instrument and milestone-structure misfit — *criterion:* Funding-instrument design imposes timing, scope, or reporting structures incompatible with the funded activity.
- **p68** Contract structure and term misalignment — *criterion:* A contract's structure, scope, or terms produce gaps or unworkable obligations relative to actual situation.
- **p69** Procurement and tendering process pathologies — *criterion:* Procurement or tender process design produces adverse selection, pricing, or contracting outcomes independent of technical fit.
- **p70** Multi-party coordination overhead — *criterion:* Coordinating actions across multiple independent parties produces delivery friction beyond what any one party can address.
- **p71** Responsibility and accountability gaps — *criterion:* An action goes unperformed because responsibility for it is unassigned, ambiguous, or contested.
- **p72** Misaligned incentives between actors — *criterion:* Decision rights and consequence-bearing are split across parties with structurally divergent incentives.
- **p73** Information asymmetry between parties — *criterion:* One party holds information another party needs, but it is not shared.
- **p74** Chicken-and-egg coordination deadlocks — *criterion:* Mutual prerequisite dependency between parties or investments prevents either from moving first.
- **p75** Trust, perception, and social licence — *criterion:* Trust, perception, or social-licence dynamics suppress adoption or progress regardless of technical or economic substance.
- **p76** Equity, distributional, and access barriers — *criterion:* Cost or benefit distribution disadvantages a subgroup because of access, eligibility, or fixed-cost barriers.
- **p77** Customer recruitment, conversion, and retention friction — *criterion:* Recruitment, onboarding, or retention pipeline design loses prospects between awareness and committed participation.
- **p78** Behavioural rebound and unintended response — *criterion:* An intervention triggers a compensating response that erodes or reverses its intended effect.
- **p79** Demand response and aggregator delivery shortfall — *criterion:* Aggregated or contracted demand-response capacity under-delivers at activation.
- **p80** Workforce skills and capability scarcity — *criterion:* Required human capability or workforce capacity is insufficient to deliver the work at the required time and place.
- **p81** Personnel turnover and key-person dependency — *criterion:* Loss of specific personnel disrupts continuity because critical knowledge or relationships were concentrated in them.
- **p82** Manual process bottlenecks and automation gaps — *criterion:* A manual process step caps throughput, introduces errors, or prevents scaling because it has not been automated.
- **p83** Project planning, scoping, and contingency inadequacy — *criterion:* Inadequate upfront planning, scoping, or contingency causes downstream rework or capability gaps.
- **p84** Late discovery forcing rework — *criterion:* An issue or requirement is identified after a commitment point, forcing costly rework that earlier discovery would have avoided.
- **p85** Schedule cascade and dependency delays — *criterion:* Sequential dependency structure causes a single delay to cascade across the project schedule.
- **p86** Conservative-margin and over-specification bias — *criterion:* Conservatism in response to uncertainty drives systematic over-design or excess restriction relative to actual need.

## Clusters to assign (91 total)

- **c014** | Inertia Shortfall From Thermal Generator Retirement
  - mechanism: Grid inertia falls below secure operating levels because synchronous thermal generators are retired and replaced by inverter-based renewables that do not inherently provide inertia, creating a system security shortfall.
- **c026** | Biomass Handling Causing Bridging and Flow Blockages
  - mechanism: Biomass feedstock bridges or ratholes in hoppers and conveyors because compaction during transport increases bulk density and cohesion, blocking gravity-driven flow and requiring mechanical intervention.
- **c032** | Strict Eligibility Criteria Reducing Addressable Customer Pool
  - mechanism: Customer acquisition targets are missed because eligibility criteria exclude a large proportion of the potential customer base, reducing the pool of recruitable participants below what is needed to meet program scale objectives.
- **c039** | Overcomplicated Product Offering Reducing Customer Conversion
  - mechanism: Customer uptake of new energy products is lower than expected because the sales process is too long, the product is perceived as too expensive or technically complex, and competing programs in the market create confusion that reduces conversion rates…
- **c043** | Renewable Product Specification Shortfall Without Fractionation
  - mechanism: Renewable fuel products fail to meet specification limits for key quality parameters (viscosity, flash point) because the production process lacks a fractionation or separation step that would remove off-spec components.
- **c044** | Long Technology Development Lead Time Risking Market Obsolescence
  - mechanism: Technology or platform development projects risk deploying outdated solutions because the lengthy build time required for a full-featured system allows the market context to evolve faster than the development cycle.
- **c527** | Raw Material Batch Variability Causing Process Re-optimisation Delays
  - mechanism: Manufacturing or fabrication projects are delayed because inconsistent raw material quality between supply batches requires repeated identification of batch defects and re-optimisation of production processes.
- **c538** | IBR grid-forming instability near network transfer capability limits
  - mechanism: Inverter-based resources produce oscillations or destabilising power swings when operating near or above network transfer capability limits because high system sensitivity or absence of a feasible steady-state operating point prevents stable power in…
- **c550** | Regulatory Fragmentation Prevents Harmonised Grid Connection Standards
  - mechanism: Inconsistent technical requirements across jurisdictions persist because no institutional mechanism has authority to enforce harmonisation across network service providers.
- **c551** | Consumer Unfamiliarity With Market Mechanisms Limits DER Participation
  - mechanism: Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **c555** | Voltage Transition Rate Sensitivity Causes Inverter Spurious Trip
  - mechanism: An inverter curtails output or trips during a voltage disturbance when the voltage edge transition rate exceeds a threshold, even though the same disturbance magnitude with a slower transition is ridden through without interruption.
- **c559** | Renewable Penetration Shifts Network Harmonic Resonance Frequencies
  - mechanism: Displacement of synchronous generation by inverter-based resources alters network harmonic impedance characteristics, shifting resonant frequencies to lower values where power-electronics emissions cause greater harmonic disturbance.
- **c605** | Participant Engagement Materials Underutilised Reducing Program Effectiveness
  - mechanism: Program outcomes are limited because a substantial proportion of participants do not engage with educational or informational materials provided, reducing the behaviour change or capability uplift the program was designed to achieve.
- **c608** | Feedstock Calorific Value Insufficient for Thermal Self-Sufficiency
  - mechanism: Process heat shortfall occurs because the feedstock's net calorific value is too low to sustain a thermally neutral operation, requiring supplementary fuel input and incurring ongoing operating costs.
- **c611** | Demand Response Participation Rate Decline Over Program Duration
  - mechanism: Total load reduction from demand response programs decreases over time because participant engagement rates decline progressively from program start to end, reducing the active proportion of registered participants.
- **c612** | Grid-Forming Inverter Fault Contribution Increases Arc Flash Risk
  - mechanism: Grid-forming inverters sustain fault current after network disconnection unlike grid-following inverters, increasing incident energy for arc faults because longer clearing times result from the continued fault contribution.
- **c627** | Siloxane Combustion Deposits Damage Gas Processing Equipment
  - mechanism: Siloxanes present in biogas decompose during combustion or processing to form silica and silicate deposits that accumulate on and damage gas processing equipment.
- **c628** | Inadequate Customer Communication Causes Confusion and Negative Sentiment
  - mechanism: Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- **c629** | Annual Participant Recruitment Creates Recurring Resource Burden
  - mechanism: Demand response programs that require fresh participant recruitment each year incur a growing and disproportionate administrative cost because no roll-over or automatic enrolment mechanism exists.
- **c641** | Concurrent Large Infrastructure Programme Disrupts Demonstration Project Operation
  - mechanism: A co-located major capital works programme causes operational interruptions to a demonstration project because shared infrastructure must be taken offline or reconfigured to accommodate the larger programme.
- **c650** | Renewable Penetration Increase Raising Ancillary Service Costs
  - mechanism: Growing variable renewable energy penetration increases ancillary service costs because forecast uncertainty and reduced system inertia require more frequent and larger frequency control interventions.
- **c651** | Opt-In Default Causing Low Uptake of Available Schemes
  - mechanism: Beneficial schemes achieve low participation because opt-in defaults require active consumer choice, and most consumers remain on legacy arrangements through inertia.
- **c660** | Upstream Process Change Removes Co-Product Feedstock
  - mechanism: Transitioning to a cleaner primary process eliminates a co-product that downstream processes depend on as feedstock, creating a new supply gap that requires an alternative and potentially costly source.
- **c718** | IT System Dependency Creating Single Point of Operational Failure
  - mechanism: Critical operational functions become unavailable when underlying IT or software systems fail because the operational process has no adequate fallback and relies entirely on continuous IT system availability.
- **c722** | Shared Infrastructure Market Congestion Degrades System Performance Near Deadline
  - mechanism: Shared server or market infrastructure degrades in performance near operational deadlines because simultaneous submissions from multiple participants overload the shared resource, and the problem worsens as participant numbers grow.
- **c740** | Inverter Fault Current Incompatibility With Protection Schemes
  - mechanism: Inverter-based resources produce fault current levels materially different from synchronous plant, causing existing protection settings to misoperate or require redesign because the protection system was calibrated for conventional fault current magn…
- **c751** | Jurisdictional Accountability Impedes Cross-Regional Optimisation
  - mechanism: State-level accountability for energy security causes suboptimal national outcomes because decision-makers prioritise local control over cross-regional resource sharing and coordination.
- **c762** | High-Ash Feedstock Causes Particle Agglomeration In Thermal Systems
  - mechanism: Elevated ash content in non-conventional feedstock causes particle agglomeration and deposit accumulation in thermal processing equipment because ash chemistry and quantity exceed design tolerances established for lower-ash fuels.
- **c814** | Regulatory Rule Conflict Prevents Practical Application
  - mechanism: A regulatory rule or guidance instrument cannot be applied in practice because it conflicts with another rule or creates practical difficulties that make compliance impossible or inconsistent with existing registered arrangements.
- **c826** | Power Outage Triggers Disproportionate Downstream Production Loss
  - mechanism: A brief power interruption causes production losses far exceeding the outage duration because downstream processes require extended reset, re-entry, or recovery procedures before normal operations can resume.
- **c843** | Low-Grade Feedstock Incompatibility with Emerging Clean Processes
  - mechanism: Decarbonisation pathways are blocked because locally abundant low-grade feedstocks are incompatible with emerging clean conversion processes that require high-grade inputs, forcing costly export or pre-treatment.
- **c869** | Long Contract Duration Deterring Customer Participation
  - mechanism: Customers decline to participate because multi-year contract terms are perceived as an unacceptable commitment, reducing sign-up rates.
- **c886** | Balanced-Grid Control Degradation Under Asymmetric Fault Conditions
  - mechanism: Inverter control strategies designed for balanced grid conditions produce uncontrollable double-frequency oscillations and unbalanced current or active power drops because their control loops cannot handle the negative-sequence components introduced …
- **c895** | Centralised Shared Infrastructure Creates Common-Mode Failure Exposure
  - mechanism: Centralising a critical support function in a single shared asset creates a common-mode failure risk because the outage of that single asset simultaneously degrades or disables all dependent systems.
- **c910** | Feed Gas Contaminant Variability Undermines Upgrader Technology Selection
  - mechanism: Biogas upgrader technologies pass through or are sensitive to feed-gas contaminants whose composition varies, causing residual contamination risk that cannot be fully eliminated by technology choice alone.
- **c915** | Regulatory Authority Conflicting Requirements Causing Site Rejection
  - mechanism: Sites are rejected or designs fail because requirements imposed by one regulatory or approval authority are structurally incompatible with requirements imposed by a separate authority.
- **c916** | Inverter-Based Resource Instability Under Low System Strength
  - mechanism: Inverter-based plant performance degrades because low system strength increases the likelihood of power quality disturbances that adversely interact with inverter control systems.
- **c936** | Inconsistent Federal-State Regulatory Frameworks Creating Compliance Uncertainty
  - mechanism: Projects face compliance uncertainty because federal and state regulatory requirements are inconsistent or uncoordinated, forcing project teams to navigate conflicting obligations without a clear authoritative pathway.
- **c949** | Biomass and Biological Feedstock Variability Limits Scale-Up
  - mechanism: Scaling biological or biomass-based production processes fails because feedstock availability, variability, contamination, and transport costs impose constraints that cannot be resolved at large scale.
- **c952** | High-Biochar Blend Causes Dryer and Combustion Process Disruption
  - mechanism: Increasing biochar blend ratios degrades process control and combustion quality because biochar's physical properties (low density, high dust generation, moisture sensitivity) exceed the handling and combustion tolerances of equipment designed for th…
- **c957** | Shared Research Equipment Unreliability Causes Non-Repeatable Results
  - mechanism: Non-repeatable experimental results occur because shared multi-user equipment cannot be maintained in a consistent state between users.
- **c1001** | Grid-Forming Inverter Additional Tuning Complexity Versus Grid-Following
  - mechanism: Grid-forming inverters require additional control loops absent in grid-following inverters, and these loops demand significant tuning and coordination effort to ensure stable operation.
- **c1012** | Biomass Storage Microbial Activity Causes Feedstock Loss and Emissions
  - mechanism: Microbial breakdown of stored biomass causes dry matter loss and greenhouse gas emissions because anaerobic and aerobic zones within stored material generate CH4, CO2, and N2O.
- **c1019** | Harmonic Emission Profile Variation Across Operational Modes
  - mechanism: Harmonic compliance failures or ambiguities arise because inverter harmonic emission profiles change with operational mode or allocation methodology, causing either underutilisation of network capacity or non-compliance with grid standards.
- **c1027** | Mandatory Retailer Switch Barrier to Program Participation
  - mechanism: Program uptake is suppressed because customers must change their energy retailer as a precondition of participation, and customer inertia to switch exceeds the perceived benefit of joining.
- **c1041** | Grid-Forming Inverter Behaviour Triggers Legacy Protection False Operations
  - mechanism: Grid-forming inverter active correction behaviour causes false triggering of protection systems designed for grid-following plants because the corrective response generates signals that legacy detection logic interprets as faults.
- **c1053** | Harmonic Distortion Causing Multi-System Equipment Degradation
  - mechanism: Elevated harmonic distortion causes thermal aging, protection maloperation, and equipment lifetime reduction because non-linear current waveforms increase losses and interfere with control systems across transformers, rotating machines, and power-ele…
- **c1068** | Delayed Re-engagement Causes Customer Acquisition Failure
  - mechanism: Customer acquisition fails because the elapsed time between initial interest registration and follow-up contact causes prospective participants to disengage before enrolment is completed.
- **c1115** | Regulatory Ambiguity Creates Overlapping Compliance Obligations
  - mechanism: Participants face duplicated or unclear compliance obligations because regulatory frameworks were not designed for novel business models or technologies, causing administrative burden and uncertainty.
- **c1131** | Participant Dropout from Unexpected Minor Cost Barriers
  - mechanism: Trial or program participants disengage because even small unexpected costs or friction points encountered during onboarding erode commitment, particularly when the primary offering is provided at no charge.
- **c1133** | Absent Review Pathway Forces Escalation to Governance Bodies
  - mechanism: Lack of a formal reconsideration or appeal process causes aggrieved parties to bypass intended channels and escalate directly to senior governance bodies because no intermediate remedy exists.
- **c1144** | Automated Communication Insufficient for High-Engagement Participants
  - mechanism: Automated messaging fails to secure participant commitment because some customers require personalised dialogue to confirm participation, necessitating human follow-up that the automated system cannot replace.
- **c1149** | Absent consumer information pathway blocking technology adoption
  - mechanism: Technology uptake is impeded because no single authoritative information source or structured customer journey exists to guide prospective purchasers through the buying process.
- **c1183** | Positive Attitude Fails to Convert to Active Participation
  - mechanism: Expressed consumer support for a technology or program does not translate into enrolment or adoption because attitudinal positivity and behavioural commitment are driven by different motivational factors.
- **c1184** | Infrastructure Sharing Constraint Reduces Asset Utilisation
  - mechanism: Shared physical infrastructure that cannot be segregated or reconfigured forces co-mingling of distinct product streams or asset groups, reducing the utilisation or discoverability of individual assets because separation would require prohibitive new…
- **c1192** | Social Media Outperforms Broadcast Channels for Niche Recruitment
  - mechanism: Broad-channel outreach such as mail-outs fails to recruit or engage target participants because awareness is low, whereas targeted social media or community-leveraging approaches yield stronger uptake.
- **c1196** | Incentive Redemption Friction Reduces Participant Uptake
  - mechanism: Participants disengage from incentive programs because indirect or multi-step redemption processes reduce the perceived monetary value compared to direct bill reductions.
- **c1239** | Inverter Current Ceiling Limits Inertial Response Headroom
  - mechanism: Inverters reach their maximum output limit earlier than synchronous machines during grid disturbances because inverters have much lower overload ratings, constraining their ability to provide sustained inertial or frequency response.
- **c1251** | Solar Inverter Anomalous Electrical Signature During Grid Events
  - mechanism: Solar generation sites exhibit disproportionately elevated negative-sequence voltage and impedance responses during grid disturbance events because inverter-based generation interacts with the network differently from synchronous plant.
- **c1266** | Dense Particle Morphology Preventing Complete Thermal Treatment
  - mechanism: Dense or large feedstock particles resist complete thermal processing because heat and reactive gases cannot penetrate to the particle core, leaving residual contaminants or unconverted material.
- **c1269** | Grid-Forming vs Grid-Following Damping Sensitivity to Renewable Penetration
  - mechanism: Grid-following inverter-based resources lose damping capability as renewable penetration increases because their control response depends on a stable grid reference, whereas grid-forming resources maintain damping independently of penetration level.
- **c1272** | Jurisdictional Policy Inconsistency Creating Geographic Investment Disparity
  - mechanism: Financial attractiveness of a project varies by location because different jurisdictions apply inconsistent policy instruments such as levies, subsidies, or mandates, creating uneven incentive landscapes for the same technology.
- **c1273** | Islanded Voltage-Source Operation More Demanding Than Grid-Following
  - mechanism: Providing backup or islanded power is more technically challenging than grid-connected operation because the device must generate its own voltage waveform rather than synchronise to an existing grid reference.
- **c1276** | Renewable fuel reformulation introduces new safety or quality deficiencies
  - mechanism: Removing or substituting a conventional fuel component to meet renewable or low-emission targets eliminates a functional property that the original component provided, requiring additional additives or process steps to restore minimum performance spe…
- **c1282** | Iron ore feedstock structure impedes hydrogen direct reduction performance
  - mechanism: Magnetite-based iron ore resists hydrogen direct reduction and causes sticking because its dense structure limits reducibility, while the broader fossil-carbon dependency of iron and steel production creates a structural barrier to decarbonisation.
- **c1287** | Customer engagement strategy misaligned with actual participant motivations
  - mechanism: Recruitment or engagement campaigns underperform because the value proposition communicated to potential participants does not match their primary motivations, causing low uptake or disengagement.
- **c1290** | Bidirectional Power Flow Increases Control Complexity
  - mechanism: Bidirectional energy devices cause increased design and control complexity because supporting power flow in both directions requires more controlled elements and must satisfy additional grid code requirements.
- **c1293** | Participant Competing Commitments Reduce Program Engagement
  - mechanism: Program participants deliver inconsistent engagement because concurrent personal or professional obligations reduce available time and bandwidth for program activities.
- **c1323** | Biomass High Volatile Yield Causing Elevated Tar in Gasification
  - mechanism: Biomass gasification produces high tar concentrations in product gas because biomass has very high volatile yields upon heating, releasing a large fraction as gaseous volatiles that include condensable tar compounds.
- **c1334** | Onboarding Process Complexity Adding Customer Friction in CER Integration
  - mechanism: Customer experience is degraded and procedural complexity is increased when CER integration platforms require customers to be temporarily removed from and then re-enrolled in retail or service arrangements during commissioning.
- **c1348** | Fuel Contamination Degrades Downstream Conversion Technology Performance
  - mechanism: Trace contaminants in a fuel or feedstock stream poison or degrade downstream conversion equipment because the conversion technology has low tolerance for those species, requiring additional purification steps that add cost and complexity.
- **c1351** | Inverter Tripping Post-Fault Causes Secondary Voltage Instability
  - mechanism: Tripping inverter-based resources following a grid fault causes a secondary voltage depression that threatens the transient stability of nearby plant, because the sudden loss of reactive support compounds the original disturbance.
- **c1356** | Scrap Availability Limiting EAF Decarbonisation Pathway
  - mechanism: Electric arc furnace steelmaking with renewable electricity cannot displace more than half of global steel production because scrap steel availability and quality are insufficient to meet total demand, requiring continued virgin iron production.
- **c1371** | High-Strength Wastewater Requiring Pre-Treatment Before Anaerobic Digestion
  - mechanism: High-strength industrial wastewaters cannot be directly processed by anaerobic digestion because suspended solids must first be removed to prevent process inhibition and equipment fouling.
- **c1416** | Undifferentiated Messaging Reduces Recruitment And Engagement Effectiveness
  - mechanism: Broad undifferentiated outreach and messaging reduces recruitment and engagement effectiveness because different customer or stakeholder segments have distinct motivations and barriers that a single generic message cannot address.
- **c1438** | Regulatory Ambiguity Creates Overlapping Or Absent Compliance Jurisdiction
  - mechanism: Compliance obligations cannot be clearly assigned or enforced because multiple regulatory bodies have overlapping or unclear jurisdictional boundaries, leaving some safety or legal responsibilities unaddressed.
- **c1442** | Biomass Gasification Contaminant Volatilisation Degrading Product Gas
  - mechanism: Inorganic species and volatile-char interaction products contaminate raw gasification product gas because high potassium and other inorganic content volatilises easily during the gasification process.
- **c1447** | Hydrogen DRI Carbon Deficit Requiring External Carburisation
  - mechanism: Hydrogen-reduced DRI contains insufficient carbon for optimal EAF steelmaking because pure hydrogen reduction produces zero-carbon DRI whereas the process requires 1.5–3% carbon, necessitating external carbon addition.
- **c1455** | Synchronous Device Instability Under High Renewable Penetration Contingency
  - mechanism: Synchronous generators and condensers lose synchronism during network contingency events because transient and voltage instability propagates through the system even to devices not directly involved in the initiating fault.
- **c1464** | Increased System Complexity Raising Operational Failure Risk
  - mechanism: Adding more moving parts or switching operations to a system increases the probability of failure because each additional component or transition introduces an independent failure mode.
- **c1468** | Unloaded Transformer Energisation Causing Ferroresonance Overvoltage
  - mechanism: Closing a breaker onto an unloaded transformer in a low short-circuit power system causes ferroresonance because filter capacitances resonate with transformer magnetising inductance at low system stiffness.
- **c1475** | Oversized Particle Incomplete Carbonisation Spontaneous Combustion Risk
  - mechanism: Particles exceeding the maximum thickness for the available heating time are not fully carbonised, leaving reactive material that presents a spontaneous combustion hazard in the product.
- **c1479** | Transhipment Routing Breaks Trade Agreement Eligibility
  - mechanism: Goods transhipped through an intermediate country lose preferential trade agreement benefits because the bill of lading records the transit country as country of import rather than the true country of origin, violating direct-shipment requirements.
- **c1485** | Digital Marketing Channels Fail to Convert Renewable Energy Leads
  - mechanism: Mass digital and direct marketing channels produce very low conversion rates for renewable energy product uptake because they fail to create genuine purchase urgency or reach decision-ready customers, extending the sales cycle beyond initial forecast…
- **c1494** | Regulatory Fragmentation Impedes Distributed Energy Participation
  - mechanism: Distributed energy resource participation in markets and networks is impeded because rules, responsibilities, and regulatory frameworks are fragmented, unclear, or absent across multiple governance layers.
- **c1499** | Transmission Disturbance Propagation To Distribution Layer Inverters
  - mechanism: Rooftop inverters experience disturbances because faults or events at the transmission layer propagate through transformer connections and distribution lines to the distribution layer where inverters are connected, with the transfer mechanism amplify…
- **c1509** | Wind Farm Frequency Reference Dependency Causes Supply Loss
  - mechanism: Wind farms lose generation when grid-connected transmission lines trip because they require an external frequency reference to operate, causing simultaneous loss of both local load and wind generation.
- **c1536** | Yeast Inhibition by Fermentation By-Products Increases Processing Costs
  - mechanism: Inhibitory chemical by-products of biomass hydrolysis suppress conventional yeast strains, requiring process adjustments such as dilution that increase downstream energy and material consumption.
- **c1556** | Prior Campaign Exposure Required for Direct-Response Media Effectiveness
  - mechanism: Direct-response media placements fail to convert audiences who have not previously been exposed to campaign touchpoints because awareness and intent have not been established prior to the call to action.
- **c1571** | Duplicate App Requirement Undermines Channel Partner Integration
  - mechanism: Platform adoption fails in channel partner contexts because requiring end-users to install a separate application duplicates functionality already provided by the partner's own richer interface, creating friction without added value.
- **c1587** | Feedstock mono-digestion causes acidic overloading instability
  - mechanism: Anaerobic digestion becomes unstable and acidic because processing a single high-fermentability feedstock alone overwhelms buffering capacity, whereas co-digestion with a complementary substrate stabilises the process.
