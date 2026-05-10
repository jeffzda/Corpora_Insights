# Cluster→parent fit review

You're given five candidate parent categories from a failure-mode taxonomy and the failure-mode clusters that have been provisionally assigned to each. Your task is to judge whether each cluster fits its assigned parent.

## Parents

### p25: Feedstock and input variability
**Description:** Process performance is degraded because input feedstock or material composition varies, contaminates, or falls outside the design tolerance of the consuming process.
**Mechanism criterion:** Input feedstock or material variability or contamination exceeds the tolerance of the consuming process.

### p33: Inverter-based resource and grid-stability dynamics
**Description:** A power-system electrical or stability phenomenon arises from inverter-based resource behaviour, or from displacement of synchronous-machine services, that legacy frameworks were not designed for.
**Mechanism criterion:** Inverter-based resource dynamics interact with grid characteristics in ways incompatible with frameworks built around synchronous plant.

### p44: Single point of failure and shared-resource fragility
**Description:** A single shared centralised dependency creates a failure mode that simultaneously impairs many dependent systems, or a capacity bottleneck across multiple dependent functions.
**Mechanism criterion:** A shared centralised dependency creates correlated common-mode failure or bottleneck across multiple dependent functions.

### p61: Regulatory ambiguity and jurisdictional fragmentation
**Description:** Compliance falters because regulatory rules, jurisdictions, or interpretations conflict, overlap, or fragment authority across multiple bodies, producing ambiguous or contradictory obligations.
**Mechanism criterion:** Multiple regulatory bodies, jurisdictions, or rule sets produce ambiguous, conflicting, or fragmented obligations.

### p77: Customer recruitment, conversion, and retention friction
**Description:** Programme participation falls short because the recruitment, conversion, onboarding, or retention pathway loses prospective participants at identifiable friction points or due to audience-design mismatch.
**Mechanism criterion:** Recruitment, onboarding, or retention pipeline design loses prospects between awareness and committed participation.

## Task

For every (cluster_id, parent_id) pair below, output one JSON line with:

```json
{"cluster_id": "cNNN", "parent_id": "pNN", "verdict": "fit|borderline|misfit", "rationale": "<one sentence>"}
```

Definitions:
- **fit**: the cluster's mechanism is a clear instance of the parent's mechanism criterion
- **borderline**: the cluster could plausibly fit, but a different mechanism class would describe it more naturally; or only weakly satisfies the parent's criterion
- **misfit**: the cluster's mechanism does not satisfy the parent's criterion at all

Output strict JSONL, no commentary, no preamble, one record per line. Process all clusters in input order.

## Cluster assignments to review

### Assigned to p25

- **c026** | Biomass Handling Causing Bridging and Flow Blockages
  - mechanism: Biomass feedstock bridges or ratholes in hoppers and conveyors because compaction during transport increases bulk density and cohesion, blocking gravity-driven flow and requiring mechanical interventi…
- **c043** | Renewable Product Specification Shortfall Without Fractionation
  - mechanism: Renewable fuel products fail to meet specification limits for key quality parameters (viscosity, flash point) because the production process lacks a fractionation or separation step that would remove …
- **c527** | Raw Material Batch Variability Causing Process Re-optimisation Delays
  - mechanism: Manufacturing or fabrication projects are delayed because inconsistent raw material quality between supply batches requires repeated identification of batch defects and re-optimisation of production p…
- **c608** | Feedstock Calorific Value Insufficient for Thermal Self-Sufficiency
  - mechanism: Process heat shortfall occurs because the feedstock's net calorific value is too low to sustain a thermally neutral operation, requiring supplementary fuel input and incurring ongoing operating costs.
- **c627** | Siloxane Combustion Deposits Damage Gas Processing Equipment
  - mechanism: Siloxanes present in biogas decompose during combustion or processing to form silica and silicate deposits that accumulate on and damage gas processing equipment.
- **c660** | Upstream Process Change Removes Co-Product Feedstock
  - mechanism: Transitioning to a cleaner primary process eliminates a co-product that downstream processes depend on as feedstock, creating a new supply gap that requires an alternative and potentially costly sourc…
- **c762** | High-Ash Feedstock Causes Particle Agglomeration In Thermal Systems
  - mechanism: Elevated ash content in non-conventional feedstock causes particle agglomeration and deposit accumulation in thermal processing equipment because ash chemistry and quantity exceed design tolerances es…
- **c843** | Low-Grade Feedstock Incompatibility with Emerging Clean Processes
  - mechanism: Decarbonisation pathways are blocked because locally abundant low-grade feedstocks are incompatible with emerging clean conversion processes that require high-grade inputs, forcing costly export or pr…
- **c910** | Feed Gas Contaminant Variability Undermines Upgrader Technology Selection
  - mechanism: Biogas upgrader technologies pass through or are sensitive to feed-gas contaminants whose composition varies, causing residual contamination risk that cannot be fully eliminated by technology choice a…
- **c949** | Biomass and Biological Feedstock Variability Limits Scale-Up
  - mechanism: Scaling biological or biomass-based production processes fails because feedstock availability, variability, contamination, and transport costs impose constraints that cannot be resolved at large scale…
- **c952** | High-Biochar Blend Causes Dryer and Combustion Process Disruption
  - mechanism: Increasing biochar blend ratios degrades process control and combustion quality because biochar's physical properties (low density, high dust generation, moisture sensitivity) exceed the handling and …
- **c1012** | Biomass Storage Microbial Activity Causes Feedstock Loss and Emissions
  - mechanism: Microbial breakdown of stored biomass causes dry matter loss and greenhouse gas emissions because anaerobic and aerobic zones within stored material generate CH4, CO2, and N2O.
- **c1266** | Dense Particle Morphology Preventing Complete Thermal Treatment
  - mechanism: Dense or large feedstock particles resist complete thermal processing because heat and reactive gases cannot penetrate to the particle core, leaving residual contaminants or unconverted material.
- **c1276** | Renewable fuel reformulation introduces new safety or quality deficiencies
  - mechanism: Removing or substituting a conventional fuel component to meet renewable or low-emission targets eliminates a functional property that the original component provided, requiring additional additives o…
- **c1282** | Iron ore feedstock structure impedes hydrogen direct reduction performance
  - mechanism: Magnetite-based iron ore resists hydrogen direct reduction and causes sticking because its dense structure limits reducibility, while the broader fossil-carbon dependency of iron and steel production …
- **c1323** | Biomass High Volatile Yield Causing Elevated Tar in Gasification
  - mechanism: Biomass gasification produces high tar concentrations in product gas because biomass has very high volatile yields upon heating, releasing a large fraction as gaseous volatiles that include condensabl…
- **c1348** | Fuel Contamination Degrades Downstream Conversion Technology Performance
  - mechanism: Trace contaminants in a fuel or feedstock stream poison or degrade downstream conversion equipment because the conversion technology has low tolerance for those species, requiring additional purificat…
- **c1356** | Scrap Availability Limiting EAF Decarbonisation Pathway
  - mechanism: Electric arc furnace steelmaking with renewable electricity cannot displace more than half of global steel production because scrap steel availability and quality are insufficient to meet total demand…
- **c1371** | High-Strength Wastewater Requiring Pre-Treatment Before Anaerobic Digestion
  - mechanism: High-strength industrial wastewaters cannot be directly processed by anaerobic digestion because suspended solids must first be removed to prevent process inhibition and equipment fouling.
- **c1442** | Biomass Gasification Contaminant Volatilisation Degrading Product Gas
  - mechanism: Inorganic species and volatile-char interaction products contaminate raw gasification product gas because high potassium and other inorganic content volatilises easily during the gasification process.
- **c1447** | Hydrogen DRI Carbon Deficit Requiring External Carburisation
  - mechanism: Hydrogen-reduced DRI contains insufficient carbon for optimal EAF steelmaking because pure hydrogen reduction produces zero-carbon DRI whereas the process requires 1.5–3% carbon, necessitating externa…
- **c1475** | Oversized Particle Incomplete Carbonisation Spontaneous Combustion Risk
  - mechanism: Particles exceeding the maximum thickness for the available heating time are not fully carbonised, leaving reactive material that presents a spontaneous combustion hazard in the product.
- **c1536** | Yeast Inhibition by Fermentation By-Products Increases Processing Costs
  - mechanism: Inhibitory chemical by-products of biomass hydrolysis suppress conventional yeast strains, requiring process adjustments such as dilution that increase downstream energy and material consumption.
- **c1587** | Feedstock mono-digestion causes acidic overloading instability
  - mechanism: Anaerobic digestion becomes unstable and acidic because processing a single high-fermentability feedstock alone overwhelms buffering capacity, whereas co-digestion with a complementary substrate stabi…

### Assigned to p33

- **c014** | Inertia Shortfall From Thermal Generator Retirement
  - mechanism: Grid inertia falls below secure operating levels because synchronous thermal generators are retired and replaced by inverter-based renewables that do not inherently provide inertia, creating a system …
- **c538** | IBR grid-forming instability near network transfer capability limits
  - mechanism: Inverter-based resources produce oscillations or destabilising power swings when operating near or above network transfer capability limits because high system sensitivity or absence of a feasible ste…
- **c555** | Voltage Transition Rate Sensitivity Causes Inverter Spurious Trip
  - mechanism: An inverter curtails output or trips during a voltage disturbance when the voltage edge transition rate exceeds a threshold, even though the same disturbance magnitude with a slower transition is ridd…
- **c559** | Renewable Penetration Shifts Network Harmonic Resonance Frequencies
  - mechanism: Displacement of synchronous generation by inverter-based resources alters network harmonic impedance characteristics, shifting resonant frequencies to lower values where power-electronics emissions ca…
- **c612** | Grid-Forming Inverter Fault Contribution Increases Arc Flash Risk
  - mechanism: Grid-forming inverters sustain fault current after network disconnection unlike grid-following inverters, increasing incident energy for arc faults because longer clearing times result from the contin…
- **c650** | Renewable Penetration Increase Raising Ancillary Service Costs
  - mechanism: Growing variable renewable energy penetration increases ancillary service costs because forecast uncertainty and reduced system inertia require more frequent and larger frequency control interventions…
- **c740** | Inverter Fault Current Incompatibility With Protection Schemes
  - mechanism: Inverter-based resources produce fault current levels materially different from synchronous plant, causing existing protection settings to misoperate or require redesign because the protection system …
- **c886** | Balanced-Grid Control Degradation Under Asymmetric Fault Conditions
  - mechanism: Inverter control strategies designed for balanced grid conditions produce uncontrollable double-frequency oscillations and unbalanced current or active power drops because their control loops cannot h…
- **c916** | Inverter-Based Resource Instability Under Low System Strength
  - mechanism: Inverter-based plant performance degrades because low system strength increases the likelihood of power quality disturbances that adversely interact with inverter control systems.
- **c1001** | Grid-Forming Inverter Additional Tuning Complexity Versus Grid-Following
  - mechanism: Grid-forming inverters require additional control loops absent in grid-following inverters, and these loops demand significant tuning and coordination effort to ensure stable operation.
- **c1019** | Harmonic Emission Profile Variation Across Operational Modes
  - mechanism: Harmonic compliance failures or ambiguities arise because inverter harmonic emission profiles change with operational mode or allocation methodology, causing either underutilisation of network capacit…
- **c1041** | Grid-Forming Inverter Behaviour Triggers Legacy Protection False Operations
  - mechanism: Grid-forming inverter active correction behaviour causes false triggering of protection systems designed for grid-following plants because the corrective response generates signals that legacy detecti…
- **c1053** | Harmonic Distortion Causing Multi-System Equipment Degradation
  - mechanism: Elevated harmonic distortion causes thermal aging, protection maloperation, and equipment lifetime reduction because non-linear current waveforms increase losses and interfere with control systems acr…
- **c1239** | Inverter Current Ceiling Limits Inertial Response Headroom
  - mechanism: Inverters reach their maximum output limit earlier than synchronous machines during grid disturbances because inverters have much lower overload ratings, constraining their ability to provide sustaine…
- **c1251** | Solar Inverter Anomalous Electrical Signature During Grid Events
  - mechanism: Solar generation sites exhibit disproportionately elevated negative-sequence voltage and impedance responses during grid disturbance events because inverter-based generation interacts with the network…
- **c1269** | Grid-Forming vs Grid-Following Damping Sensitivity to Renewable Penetration
  - mechanism: Grid-following inverter-based resources lose damping capability as renewable penetration increases because their control response depends on a stable grid reference, whereas grid-forming resources mai…
- **c1273** | Islanded Voltage-Source Operation More Demanding Than Grid-Following
  - mechanism: Providing backup or islanded power is more technically challenging than grid-connected operation because the device must generate its own voltage waveform rather than synchronise to an existing grid r…
- **c1290** | Bidirectional Power Flow Increases Control Complexity
  - mechanism: Bidirectional energy devices cause increased design and control complexity because supporting power flow in both directions requires more controlled elements and must satisfy additional grid code requ…
- **c1351** | Inverter Tripping Post-Fault Causes Secondary Voltage Instability
  - mechanism: Tripping inverter-based resources following a grid fault causes a secondary voltage depression that threatens the transient stability of nearby plant, because the sudden loss of reactive support compo…
- **c1455** | Synchronous Device Instability Under High Renewable Penetration Contingency
  - mechanism: Synchronous generators and condensers lose synchronism during network contingency events because transient and voltage instability propagates through the system even to devices not directly involved i…
- **c1468** | Unloaded Transformer Energisation Causing Ferroresonance Overvoltage
  - mechanism: Closing a breaker onto an unloaded transformer in a low short-circuit power system causes ferroresonance because filter capacitances resonate with transformer magnetising inductance at low system stif…
- **c1499** | Transmission Disturbance Propagation To Distribution Layer Inverters
  - mechanism: Rooftop inverters experience disturbances because faults or events at the transmission layer propagate through transformer connections and distribution lines to the distribution layer where inverters …
- **c1509** | Wind Farm Frequency Reference Dependency Causes Supply Loss
  - mechanism: Wind farms lose generation when grid-connected transmission lines trip because they require an external frequency reference to operate, causing simultaneous loss of both local load and wind generation…

### Assigned to p44

- **c044** | Long Technology Development Lead Time Risking Market Obsolescence
  - mechanism: Technology or platform development projects risk deploying outdated solutions because the lengthy build time required for a full-featured system allows the market context to evolve faster than the dev…
- **c641** | Concurrent Large Infrastructure Programme Disrupts Demonstration Project Operation
  - mechanism: A co-located major capital works programme causes operational interruptions to a demonstration project because shared infrastructure must be taken offline or reconfigured to accommodate the larger pro…
- **c718** | IT System Dependency Creating Single Point of Operational Failure
  - mechanism: Critical operational functions become unavailable when underlying IT or software systems fail because the operational process has no adequate fallback and relies entirely on continuous IT system avail…
- **c722** | Shared Infrastructure Market Congestion Degrades System Performance Near Deadline
  - mechanism: Shared server or market infrastructure degrades in performance near operational deadlines because simultaneous submissions from multiple participants overload the shared resource, and the problem wors…
- **c826** | Power Outage Triggers Disproportionate Downstream Production Loss
  - mechanism: A brief power interruption causes production losses far exceeding the outage duration because downstream processes require extended reset, re-entry, or recovery procedures before normal operations can…
- **c895** | Centralised Shared Infrastructure Creates Common-Mode Failure Exposure
  - mechanism: Centralising a critical support function in a single shared asset creates a common-mode failure risk because the outage of that single asset simultaneously degrades or disables all dependent systems.
- **c957** | Shared Research Equipment Unreliability Causes Non-Repeatable Results
  - mechanism: Non-repeatable experimental results occur because shared multi-user equipment cannot be maintained in a consistent state between users.
- **c1184** | Infrastructure Sharing Constraint Reduces Asset Utilisation
  - mechanism: Shared physical infrastructure that cannot be segregated or reconfigured forces co-mingling of distinct product streams or asset groups, reducing the utilisation or discoverability of individual asset…
- **c1464** | Increased System Complexity Raising Operational Failure Risk
  - mechanism: Adding more moving parts or switching operations to a system increases the probability of failure because each additional component or transition introduces an independent failure mode.

### Assigned to p61

- **c550** | Regulatory Fragmentation Prevents Harmonised Grid Connection Standards
  - mechanism: Inconsistent technical requirements across jurisdictions persist because no institutional mechanism has authority to enforce harmonisation across network service providers.
- **c751** | Jurisdictional Accountability Impedes Cross-Regional Optimisation
  - mechanism: State-level accountability for energy security causes suboptimal national outcomes because decision-makers prioritise local control over cross-regional resource sharing and coordination.
- **c814** | Regulatory Rule Conflict Prevents Practical Application
  - mechanism: A regulatory rule or guidance instrument cannot be applied in practice because it conflicts with another rule or creates practical difficulties that make compliance impossible or inconsistent with exi…
- **c915** | Regulatory Authority Conflicting Requirements Causing Site Rejection
  - mechanism: Sites are rejected or designs fail because requirements imposed by one regulatory or approval authority are structurally incompatible with requirements imposed by a separate authority.
- **c936** | Inconsistent Federal-State Regulatory Frameworks Creating Compliance Uncertainty
  - mechanism: Projects face compliance uncertainty because federal and state regulatory requirements are inconsistent or uncoordinated, forcing project teams to navigate conflicting obligations without a clear auth…
- **c1115** | Regulatory Ambiguity Creates Overlapping Compliance Obligations
  - mechanism: Participants face duplicated or unclear compliance obligations because regulatory frameworks were not designed for novel business models or technologies, causing administrative burden and uncertainty.
- **c1133** | Absent Review Pathway Forces Escalation to Governance Bodies
  - mechanism: Lack of a formal reconsideration or appeal process causes aggrieved parties to bypass intended channels and escalate directly to senior governance bodies because no intermediate remedy exists.
- **c1272** | Jurisdictional Policy Inconsistency Creating Geographic Investment Disparity
  - mechanism: Financial attractiveness of a project varies by location because different jurisdictions apply inconsistent policy instruments such as levies, subsidies, or mandates, creating uneven incentive landsca…
- **c1438** | Regulatory Ambiguity Creates Overlapping Or Absent Compliance Jurisdiction
  - mechanism: Compliance obligations cannot be clearly assigned or enforced because multiple regulatory bodies have overlapping or unclear jurisdictional boundaries, leaving some safety or legal responsibilities un…
- **c1479** | Transhipment Routing Breaks Trade Agreement Eligibility
  - mechanism: Goods transhipped through an intermediate country lose preferential trade agreement benefits because the bill of lading records the transit country as country of import rather than the true country of…
- **c1494** | Regulatory Fragmentation Impedes Distributed Energy Participation
  - mechanism: Distributed energy resource participation in markets and networks is impeded because rules, responsibilities, and regulatory frameworks are fragmented, unclear, or absent across multiple governance la…

### Assigned to p77

- **c032** | Strict Eligibility Criteria Reducing Addressable Customer Pool
  - mechanism: Customer acquisition targets are missed because eligibility criteria exclude a large proportion of the potential customer base, reducing the pool of recruitable participants below what is needed to me…
- **c039** | Overcomplicated Product Offering Reducing Customer Conversion
  - mechanism: Customer uptake of new energy products is lower than expected because the sales process is too long, the product is perceived as too expensive or technically complex, and competing programs in the mar…
- **c551** | Consumer Unfamiliarity With Market Mechanisms Limits DER Participation
  - mechanism: Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **c605** | Participant Engagement Materials Underutilised Reducing Program Effectiveness
  - mechanism: Program outcomes are limited because a substantial proportion of participants do not engage with educational or informational materials provided, reducing the behaviour change or capability uplift the…
- **c611** | Demand Response Participation Rate Decline Over Program Duration
  - mechanism: Total load reduction from demand response programs decreases over time because participant engagement rates decline progressively from program start to end, reducing the active proportion of registere…
- **c628** | Inadequate Customer Communication Causes Confusion and Negative Sentiment
  - mechanism: Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires r…
- **c629** | Annual Participant Recruitment Creates Recurring Resource Burden
  - mechanism: Demand response programs that require fresh participant recruitment each year incur a growing and disproportionate administrative cost because no roll-over or automatic enrolment mechanism exists.
- **c651** | Opt-In Default Causing Low Uptake of Available Schemes
  - mechanism: Beneficial schemes achieve low participation because opt-in defaults require active consumer choice, and most consumers remain on legacy arrangements through inertia.
- **c869** | Long Contract Duration Deterring Customer Participation
  - mechanism: Customers decline to participate because multi-year contract terms are perceived as an unacceptable commitment, reducing sign-up rates.
- **c1027** | Mandatory Retailer Switch Barrier to Program Participation
  - mechanism: Program uptake is suppressed because customers must change their energy retailer as a precondition of participation, and customer inertia to switch exceeds the perceived benefit of joining.
- **c1068** | Delayed Re-engagement Causes Customer Acquisition Failure
  - mechanism: Customer acquisition fails because the elapsed time between initial interest registration and follow-up contact causes prospective participants to disengage before enrolment is completed.
- **c1131** | Participant Dropout from Unexpected Minor Cost Barriers
  - mechanism: Trial or program participants disengage because even small unexpected costs or friction points encountered during onboarding erode commitment, particularly when the primary offering is provided at no …
- **c1144** | Automated Communication Insufficient for High-Engagement Participants
  - mechanism: Automated messaging fails to secure participant commitment because some customers require personalised dialogue to confirm participation, necessitating human follow-up that the automated system cannot…
- **c1149** | Absent consumer information pathway blocking technology adoption
  - mechanism: Technology uptake is impeded because no single authoritative information source or structured customer journey exists to guide prospective purchasers through the buying process.
- **c1183** | Positive Attitude Fails to Convert to Active Participation
  - mechanism: Expressed consumer support for a technology or program does not translate into enrolment or adoption because attitudinal positivity and behavioural commitment are driven by different motivational fact…
- **c1192** | Social Media Outperforms Broadcast Channels for Niche Recruitment
  - mechanism: Broad-channel outreach such as mail-outs fails to recruit or engage target participants because awareness is low, whereas targeted social media or community-leveraging approaches yield stronger uptake…
- **c1196** | Incentive Redemption Friction Reduces Participant Uptake
  - mechanism: Participants disengage from incentive programs because indirect or multi-step redemption processes reduce the perceived monetary value compared to direct bill reductions.
- **c1287** | Customer engagement strategy misaligned with actual participant motivations
  - mechanism: Recruitment or engagement campaigns underperform because the value proposition communicated to potential participants does not match their primary motivations, causing low uptake or disengagement.
- **c1293** | Participant Competing Commitments Reduce Program Engagement
  - mechanism: Program participants deliver inconsistent engagement because concurrent personal or professional obligations reduce available time and bandwidth for program activities.
- **c1334** | Onboarding Process Complexity Adding Customer Friction in CER Integration
  - mechanism: Customer experience is degraded and procedural complexity is increased when CER integration platforms require customers to be temporarily removed from and then re-enrolled in retail or service arrange…
- **c1416** | Undifferentiated Messaging Reduces Recruitment And Engagement Effectiveness
  - mechanism: Broad undifferentiated outreach and messaging reduces recruitment and engagement effectiveness because different customer or stakeholder segments have distinct motivations and barriers that a single g…
- **c1485** | Digital Marketing Channels Fail to Convert Renewable Energy Leads
  - mechanism: Mass digital and direct marketing channels produce very low conversion rates for renewable energy product uptake because they fail to create genuine purchase urgency or reach decision-ready customers,…
- **c1556** | Prior Campaign Exposure Required for Direct-Response Media Effectiveness
  - mechanism: Direct-response media placements fail to convert audiences who have not previously been exposed to campaign touchpoints because awareness and intent have not been established prior to the call to acti…
- **c1571** | Duplicate App Requirement Undermines Channel Partner Integration
  - mechanism: Platform adoption fails in channel partner contexts because requiring end-users to install a separate application duplicates functionality already provided by the partner's own richer interface, creat…

