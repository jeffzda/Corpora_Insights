# ARENA v2 parent archetypes — full register

The 71 parent failure-mode categories derived from the ARENA Knowledge Bank corpus (1,440 documents → 90,192 records → 1,141 mechanism clusters → 71 parent archetypes → 12 themes). Each parent represents a structural family of failure mechanisms that recurred across the corpus.

Parents are organised here by theme. Within each parent: name (italicised tagline), description (paragraph), mechanism criterion (the specific structural condition that defines the parent — used as the diagnostic test for whether a record / event / artefact instantiates this mechanism family).

---

## t01 — Information, data, and knowledge failures

_Mechanisms in which the failure hinges on what is known or knowable: data not existing, instruments unable to resolve it, models misrepresenting reality, knowledge unevenly distributed, or dissemination structures absent. Unified by failures of the epistemic layer over the physical or institutional system._

**Mechanism family:** Inadequate, missing, distorted, or non-transferable information about the system being acted on.

**Parents:** 10

### p01 — *Missing or inaccessible data*

Failures in which a required data element, signal, measurement, or record is absent, withheld, delayed, or locked behind access barriers, preventing analysis, control, or decision-making. Membership requires the failure to hinge on data not existing, not being collected, not being shared, or not being timely.

**Mechanism criterion:** The proximate cause is the absence, inaccessibility, or untimely arrival of a needed data element or signal.

### p02 — *Measurement and instrumentation inadequacy*

Failures arising from the measurement apparatus itself: sensor placement, sensitivity, calibration, resolution, contamination, or geometry that prevent the target physical signal from being captured accurately. Distinct from missing data because the data is being collected but the instrument cannot resolve or correctly represent the underlying quantity.

**Mechanism criterion:** The instrument or measurement method exists and runs but cannot faithfully represent the physical quantity it is meant to measure.

### p03 — *Model and forecast inaccuracy from assumption mismatch*

Failures in which a model, forecast, simulation, or analysis produces wrong outputs because its assumptions, parameters, training data, or scope do not match the actual system being represented. The mechanism is a representational gap between the model's internal logic and reality.

**Mechanism criterion:** A computational, statistical, or analytical model produces incorrect outputs because its embedded assumptions diverge from the real system.

### p04 — *Forecast skill ceiling under inherent uncertainty*

Forecasts fail not because of model error but because the underlying physical process is intrinsically hard to predict at the required resolution, or because operational forecasts cannot match the perfect-foresight assumed by downstream tools. The mechanism is irreducible uncertainty rather than fixable model bias.

**Mechanism criterion:** Forecast inadequacy stems from the inherent unpredictability of the variable at the required spatial or temporal scale, not from a correctable assumption.

### p05 — *Knowledge gap or information asymmetry*

Failures where one party lacks knowledge held by another, or where required know-how, documentation, or operational history is absent, leading to wrong decisions, rework, or stalled adoption. The mechanism is the distribution or absence of knowledge among human actors.

**Mechanism criterion:** A human party lacks knowledge that another party holds or that has not yet been generated, and the gap drives the failure.

### p58 — *Validation infeasibility and absent ground truth*

Failures where validation is impossible because no independent reference, baseline, or test infrastructure exists. Includes simulation circular validation, baseline absence, manufacturer claims unverified, intermediate test scale missing, and demonstration projects not operational.

**Mechanism criterion:** Verification or validation cannot be performed because the necessary independent reference or infrastructure is missing.

### p59 — *Data infrastructure and pipeline inadequacy*

Failures from data infrastructure: insufficient tooling, schema divergence, manual entry workflows, untagged records, register-platform mismatch, fragmented data sources. The mechanism is the data system rather than data content.

**Mechanism criterion:** Data system architecture or workflow infrastructure drives the analytical or operational failure.

### p60 — *Knowledge dissemination and benchmarking gap*

Failures from absent or fragmented industry-wide knowledge sharing: non-standardised metrics, commercially sensitive omissions, ignored negative findings, decoupled milestone reporting. The mechanism is lack of cross-project learning infrastructure.

**Mechanism criterion:** Cross-project or industry-wide learning is impeded by absent benchmarking, sharing, or dissemination structures.

### p61 — *Communication clarity and content design failure*

Failures where communication content (terminology, message complexity, customer-facing metrics, language, undifferentiated messaging) fails to convey intent to its audience. Distinct from engagement shortfall because the issue is in the message itself rather than uptake.

**Mechanism criterion:** The content or framing of communication fails to convey intended meaning to its audience.

### p70 — *Customer or counterparty data accuracy failure*

Failures from inaccurate, self-reported, or stale customer data: equipment self-description errors, identity mismatches in notifications, outdated customer plans, mass-onboarding data quality. The mechanism is data accuracy at the customer or counterparty interface.

**Mechanism criterion:** Inaccurate customer or counterparty-supplied data produces downstream failure.

---

## t02 — Physical, material, and environmental limits

_Mechanisms grounded in the physical world: intrinsic material/thermal/chemical properties, geometric and spatial constraints, external environmental agents, parasitic energy losses, and process/reactor design limits. The binding cause is a physical reality that engineering cannot fully circumvent._

**Mechanism family:** Hard physical, chemical, geometric, or environmental constraints on what equipment can do.

**Parents:** 6

### p06 — *Material, thermal, or chemical physical limit*

Failures driven by an intrinsic physical, chemical, or material property that limits performance, lifetime, or compatibility. Includes degradation mechanisms, thermal limits, chemical incompatibility, and material physics that cannot be engineered away within current technology.

**Mechanism criterion:** A material property, chemical reaction, or thermodynamic constraint imposes the limit, regardless of design choices.

### p07 — *Geometric, spatial, or footprint constraint*

Failures caused by physical space, terrain, geometry, or layout: the required equipment doesn't fit, the site shape prevents access, or the geometry of one element conflicts with another. Distinct from material limits because the issue is dimensional rather than property-based.

**Mechanism criterion:** A spatial, geometric, or dimensional constraint at a site or in equipment produces the failure.

### p08 — *Environmental exposure and external physical disturbance*

Failures caused by external environmental conditions impinging on equipment or operations: weather, fauna, vibration, particulates, lightning, fire smoke, moisture. The mechanism is an external physical agent acting on the system.

**Mechanism criterion:** An external environmental or physical agent damages, degrades, or disrupts the system.

### p51 — *Process design or reactor performance limit*

Failures rooted in specific process or reactor design choices that produce inefficiencies, side products, or operational instability. Includes reactor design, fermentation by-products, ammonia combustion NOx, and process turndown limits.

**Mechanism criterion:** A specific process or reactor design choice produces an unavoidable performance shortfall or side effect.

### p52 — *Manufacturing yield and fabrication quality*

Failures during manufacturing, fabrication, or assembly that reduce yield or introduce latent defects. Includes substrate bowing, manual handling damage, batch variability, residue contamination, and crystallisation defects.

**Mechanism criterion:** A manufacturing or fabrication step itself produces defects, low yield, or latent failures.

### p64 — *Parasitic load and round-trip energy loss*

Failures where energy losses in conversion, storage, or transport consume a significant fraction of useful output. Includes V2G round-trip loss, hydrogen storage energy, parasitic auxiliary loads, and cryogenic boil-off.

**Mechanism criterion:** Energy is lost to conversion, storage, or auxiliary loads, eroding net output below useful threshold.

---

## t03 — Capacity, sizing, and feedstock-resource mismatches

_Mechanisms where a quantitative capacity, throughput, supply, or input-quality value falls short of demand or design need. Includes undersized assets, network hosting limits, system-level balancing stress, supply-demand temporal/spatial mismatch, and feedstock variability._

**Mechanism family:** A throughput, capacity, or input-quality quantity is insufficient or misaligned with what the system requires.

**Parents:** 5

### p10 — *Capacity, sizing, or rating shortfall*

Failures where the size, capacity, throughput, or rating of an asset or interconnection is insufficient for the demand placed on it. Includes undersized BESS, charger ratings, interconnection capacity, storage duration, and similar shortfalls.

**Mechanism criterion:** A capacity, throughput, or rating value is too small for the load or task it must serve.

### p47 — *Demand-supply temporal or spatial mismatch*

Failures where energy or feedstock supply is available but not aligned in time or location with demand, causing curtailment, mismatch, or unrealised opportunity. Includes seasonal mismatch, waste-heat timing, geographic separation, and load-diversity gaps.

**Mechanism criterion:** Supply and demand exist but are misaligned in time or space, preventing utilisation.

### p48 — *System-wide intermittency and balancing stress*

Failures arising from variable renewable generation imposing balancing, ancillary service, or curtailment requirements at the system level. Includes inertia shortfall, ancillary cost growth, curtailment from minimum loads, and renewable-induced supply imbalance.

**Mechanism criterion:** Variable renewable generation imposes system-level balancing or stability requirements that drive the adverse outcome.

### p49 — *Network connection and hosting capacity limit*

Failures where physical network connection capacity, voltage limits, fault levels, or hosting capacity bound what assets can connect or operate. Distinct from broader balancing because the constraint is a specific local network parameter.

**Mechanism criterion:** A specific local network constraint (capacity, voltage, fault level, hosting limit) bounds what can connect or export.

### p50 — *Feedstock and resource quality variability*

Failures where input feedstock or resource quality varies, contaminates downstream processes, or imposes pre-treatment costs that erode economics. Includes biomass variability, contaminant carryover, ash content, microbial losses, and impurity issues.

**Mechanism criterion:** Variability or contamination in input feedstock or resource quality degrades downstream process or product.

---

## t04 — System integration, control, and timing failures

_Mechanisms in which sound components fail when combined: control-loop instability, timing/cadence mismatch, interface incompatibility, IBR-grid interaction, envelope mismatch, scale translation, commissioning exposure, and IT/cyber fragility. Unified by emergent failure at the integration boundary._

**Mechanism family:** Failure emerges at the boundary, transition, or integration of otherwise functional elements.

**Parents:** 9

### p09 — *Operating-envelope and design-envelope mismatch*

Failures where equipment is operated outside conditions for which it was designed, or where its rated envelope does not match deployment conditions, causing derating, accelerated wear, or unsafe behaviour. The hardware itself is sound but is being used outside its design assumptions.

**Mechanism criterion:** A mismatch between equipment design envelope and actual operating conditions produces underperformance or damage.

### p11 — *Control architecture and control-loop failure*

Failures in the design or operation of control logic, configuration parameters, control loops, or coordination between control layers. Includes oscillations, false trips, parameter mismatches, race conditions, and tuning conflicts.

**Mechanism criterion:** A control system, algorithm, or configuration setting produces incorrect or unstable behaviour even though the underlying hardware is functional.

### p12 — *Cadence, latency, or timing mismatch*

Failures driven by mismatch between the cadence, latency, or response time of a system and the rate or timing required by the task. Includes communication latency, dispatch interval boundaries, response-time limits, polling frequencies, and notification delays.

**Mechanism criterion:** A timing, cadence, or latency parameter is incompatible with the temporal requirement of the task.

### p13 — *Interface, protocol, and interoperability failure*

Failures where two systems, components, or parties cannot exchange information or function together because of protocol, API, format, schema, or interface incompatibility. Distinct from control-loop failures because the issue is at a boundary between systems.

**Mechanism criterion:** Two systems fail to interoperate at a defined interface (API, protocol, schema, format, connector).

### p15 — *Inverter-based resource grid-interaction failure*

Failures specific to power-electronic generation interacting with grid dynamics: low system strength instability, harmonic resonance shift, fault-current mismatch with protection, IBR damping, ferroresonance, voltage-edge sensitivity. The mechanism is the structural difference between IBR and synchronous-machine grid behaviour.

**Mechanism criterion:** A failure arises from inverter-based resource dynamics interacting with grid network characteristics differently from synchronous plant.

### p16 — *Scale-up and lab-to-field translation failure*

Failures where a process or technology that works at one scale or in one context does not transfer to another (lab to pilot, pilot to commercial, single-site to fleet). The mechanism is that previously negligible variables or absent constraints become dominant at the new scale or context.

**Mechanism criterion:** Performance valid at one scale or context fails at another because previously latent variables become controlling.

### p38 — *Commissioning and integration testing exposure*

Failures revealed only when components are integrated and operated together for the first time: latent connector issues, integration test gaps, downstream-only failure modes, sequential prerequisite delays. Distinct from scale-up because the issue is the first integrated operation rather than a different scale.

**Mechanism criterion:** Failures emerge during the act of first integrated operation or commissioning that were not detectable in component testing.

### p55 — *Cyber security and IT system fragility*

Failures arising from IT system fragility, cyber-attack surface, single points of failure, or institutional IT-security barriers. The mechanism is digital infrastructure vulnerability or restriction.

**Mechanism criterion:** Digital system fragility, security, or institutional IT restriction produces the failure.

### p56 — *Software development and integration constraint*

Failures specific to software development practice: bespoke code maintenance burden, scope flexibility, regression testing, codebase divergence, off-the-shelf gaps, and open-source licensing complexity.

**Mechanism criterion:** A software development, maintenance, or licensing constraint drives the failure outcome.

---

## t05 — Heterogeneity, scale, and aggregation effects

_Mechanisms where uniform treatment fails across heterogeneous populations, where aggregate behaviour diverges from individual, or where complexity itself proliferates failure modes or defeats modularity. The unifying axis is mismatch of grain or composition._

**Mechanism family:** Population variance, scale, or composition effects defeat single-grain solutions.

**Parents:** 4

### p17 — *Heterogeneity defeats uniform treatment*

Failures where applying a single uniform parameter, design, model, or strategy fails because the underlying population of assets, customers, or conditions is heterogeneous in ways the uniform treatment cannot accommodate.

**Mechanism criterion:** A single uniform setting, design, or assumption cannot accommodate genuine variation across the population it is applied to.

### p19 — *Aggregate vs. individual scale mismatch*

Failures where action or measurement at one level (aggregate, individual, fleet, site) does not produce equivalent results at another level because of phase, geographic, or composition effects. Includes aggregate measures masking phase violations and correlated geographic exposure.

**Mechanism criterion:** Behaviour at the aggregate scale diverges from the sum of individual-scale behaviours due to correlation or phase effects.

### p65 — *Complexity-induced failure proliferation*

Failures where adding components, parts, or moving elements increases overall failure probability or operational risk because each addition introduces independent failure modes. The mechanism is monotonic complexity-failure scaling.

**Mechanism criterion:** Increased component count or system complexity itself raises aggregate failure probability.

### p66 — *Modularity and reconfigurability absence*

Failures from monolithic, integrated, or fixed-asset designs that prevent staged or incremental adaptation. Includes fixed turbine geometry, integrated system architecture, and absent staged-expansion pathways.

**Mechanism criterion:** Lack of modular or reconfigurable design prevents adaptation to changing requirements or staged deployment.

---

## t06 — Optimisation trade-offs and decision-frame distortions

_Mechanisms in which the analytical or decision frame itself produces wrong outcomes: coupled-objective trade-offs, misspecified optimisation scope, lifecycle-horizon mismatches, conservatism bias, and diminishing returns saturation. Unified by failures of the chosen decision frame, not the underlying system._

**Mechanism family:** The decision or optimisation frame is structurally mis-set, producing wrong outputs from sound inputs.

**Parents:** 5

### p18 — *Coupled-objective trade-off*

Failures where two desired performance objectives are physically or structurally coupled such that improving one degrades the other, preventing simultaneous optimisation. The mechanism is a binding trade-off, not an engineering oversight.

**Mechanism criterion:** Two objectives share a coupling that makes simultaneous optimisation impossible.

### p62 — *Optimisation objective or scope misspecification*

Failures where an optimisation algorithm, dispatch logic, or analytical scope is set against the wrong objective or excludes relevant terms, producing locally optimal but globally suboptimal outputs. Includes scope exclusion in CBA, externality omission, and optimisation artefacts.

**Mechanism criterion:** An optimisation or analytical objective is incorrectly specified or scoped, producing wrong recommendations.

### p67 — *Diminishing returns or marginal-effect saturation*

Failures where additional effort, data, or scale yields progressively smaller returns to a saturation point. Includes diminishing forecast input value, peripheral collector efficiency, marginal participant effect, and abatement cost escalation.

**Mechanism criterion:** Marginal returns to further investment, data, or scale fall to a point that defeats the intended benefit.

### p68 — *Lifecycle and life-of-asset accounting mismatch*

Failures where the time horizon over which value is assessed is mismatched to asset life or relevant accounting frame: project horizon shorter than asset lifetime, NPV timing of capex, declining grid emissions factor, scope-3 omission.

**Mechanism criterion:** An accounting or planning time horizon is mismatched to the asset or value lifetime, producing wrong decisions.

### p69 — *Conservatism bias inflates cost or constraint*

Failures where conservative thresholds, design margins, or trigger settings imposed under uncertainty produce excess cost, curtailment, or restriction beyond what actual conditions warrant. Includes conservative DER limits, conservative third-party engineers, and over-trigger curtailment.

**Mechanism criterion:** Conservative settings adopted under uncertainty produce systematic over-restriction or over-cost.

---

## t07 — Economic and financial structure failures

_Mechanisms where economic logic blocks deployment: cost-benefit thresholds, absent or distorted price signals, blocked value capture, finance/risk-transfer gaps, chicken-and-egg deadlocks, market-structure barriers, and incumbent displacement friction._

**Mechanism family:** Economic, pricing, finance, or market-structure conditions prevent technically sound activity.

**Parents:** 7

### p20 — *Cost-benefit threshold not crossed*

Failures where the upfront capital, fixed cost, transaction cost, or incremental cost exceeds the benefit, return, or payback acceptable to the decision-maker. The mechanism is purely economic: the numbers do not support adoption or continuation.

**Mechanism criterion:** Economic value at the relevant decision horizon falls below the threshold required for adoption, regardless of technical merit.

### p21 — *Price signal absent, distorted, or misaligned*

Failures where a price signal that would drive efficient behaviour is absent, blunted, perverse, or misaligned with intended outcomes. Includes tariff design, FiT floors, subsidy distortion, dispatch averaging, and missing market mechanisms.

**Mechanism criterion:** A pricing or incentive signal needed to drive intended behaviour is absent, dampened, or perverse.

### p22 — *Value capture blocked by market or regulatory structure*

Failures where a technically delivered service has real value but cannot be monetised because regulations, market rules, or accounting frameworks do not recognise or compensate it. Distinct from absent price signals because the structural barrier blocks any value flow.

**Mechanism criterion:** A real service or benefit cannot be monetised because the market or regulatory framework does not recognise or compensate it.

### p43 — *Investment finance and risk-transfer gap*

Failures where capital cannot be assembled because risk-transfer, hedging, insurance, or bankability mechanisms are inadequate for the asset class. Includes lender risk aversion, immature insurance, thin forward markets, and uncertain return horizons.

**Mechanism criterion:** Project finance is unavailable or expensive because risk-transfer or bankability instruments are insufficient.

### p44 — *Chicken-and-egg deployment deadlock*

Failures where two interdependent investments each require the other to move first, producing self-reinforcing deployment deadlock. Includes infrastructure-adoption deadlocks and feedstock-aggregation deadlocks.

**Mechanism criterion:** Two interdependent investments are blocked because each is contingent on the other's prior commitment.

### p45 — *Market-structure barrier or competitive distortion*

Failures where market structure (concentration, monopoly, fragmentation, small share, dominant incumbent) distorts pricing, blocks entry, or impedes new entrants. The mechanism is the configuration of market participants rather than rules.

**Mechanism criterion:** The structural composition of the market (concentration, fragmentation, participant types) drives the adverse outcome.

### p46 — *Incumbent technology displacement and transition friction*

Failures where existing committed assets, contracts, or industry positions resist or delay adoption of competing technologies. Includes infrastructure lock-in, stranded asset risk, incumbent disruption, and prior partial deployment.

**Mechanism criterion:** Pre-existing committed assets or industry positions create friction that delays or blocks adoption of an alternative.

---

## t08 — Regulatory, standards, and compliance failures

_Mechanisms grounded in the rules layer: regulatory framework gaps, approval-process friction, policy uncertainty, metric/method design distortion, legacy design embedded in standards, standards-specification mismatch, and weak enforcement. Unified by the rule system as proximate cause._

**Mechanism family:** Rules, standards, or their execution and enforcement produce or fail to prevent the adverse outcome.

**Parents:** 7

### p14 — *Legacy or pre-existing design incompatibility*

Failures where existing equipment, infrastructure, models, or standards were designed under prior assumptions that no longer hold (unidirectional flow, synchronous generation, single-substance, older voltage standards), and cannot accommodate new conditions.

**Mechanism criterion:** A pre-existing design or standard built around superseded assumptions cannot accommodate the current operating context.

### p23 — *Regulatory framework gap or misfit for novel context*

Failures where existing regulations, classifications, standards, or approval processes cannot accommodate a novel technology, configuration, or actor type. The mechanism is a regulatory framework that was not designed for the case at hand.

**Mechanism criterion:** An existing regulatory framework lacks provisions, classifications, or pathways for the technology, configuration, or actor in question.

### p24 — *Regulatory approval timing and process friction*

Failures from the duration, sequencing, or procedural friction of regulatory or third-party approval processes, including iterative rework, late-discovered requirements, lapsed approvals, and multi-authority sequencing. The framework exists but its execution introduces delay or cost.

**Mechanism criterion:** The procedural execution of approvals (iteration, sequencing, expiry, late discovery) imposes delay or cost beyond the framework itself.

### p25 — *Regulatory policy uncertainty and instability*

Failures where unpredictable, unstable, or competing policy signals deter investment or create options-value to wait. The mechanism is uncertainty about future rules rather than current rules being inadequate.

**Mechanism criterion:** Investment or commitment is deferred or distorted because future policy direction is uncertain or unstable.

### p26 — *Regulatory metric or method design distortion*

Failures where a specific regulatory or market metric, baseline method, or calculation rule produces perverse, misleading, or unintended outcomes because of how the metric is constructed (e.g. baseline methods, MLF asymmetry, contribution-factor lag).

**Mechanism criterion:** A specific metric or calculation method embedded in a rule produces outcomes that diverge from the intended objective.

### p41 — *Standards, certification, and compliance specification gap*

Failures where a specific standard, test scope, or certification process is inadequate, mismatched to scale, or imposes disproportionate burden. Distinct from regulatory gap because the issue is the specific technical specification of the standard or test rather than the broader regulatory framework.

**Mechanism criterion:** A specific standard, certification, or test specification is inadequate, mismatched, or disproportionate for the application.

### p42 — *Compliance verification and enforcement weakness*

Failures where rules exist but verification, enforcement, or compliance monitoring is absent or ex-post only, allowing non-compliance or gaming. The mechanism is insufficient enforcement infrastructure rather than rule absence.

**Mechanism criterion:** Compliance fails because verification or enforcement mechanisms cannot validate or ensure participant behaviour.

---

## t09 — Multi-party coordination and contractual failures

_Mechanisms arising between parties: coordination overhead, governance/responsibility gaps, misaligned incentives, contractual rigidity, trust dynamics, and vendor lock-in. The unifying axis is the inter-party interface._

**Mechanism family:** Failure at the interface between organisations, contracts, or commercial actors.

**Parents:** 6

### p27 — *Multi-party coordination overhead*

Failures where progress requires alignment among multiple independent parties whose interests, timetables, or processes are not mutually scheduled, causing delay, scope gaps, or contractual deadlock. The mechanism is the coordination cost itself, not any party's individual failure.

**Mechanism criterion:** Failure arises from the cost or breakdown of coordination among multiple independent parties.

### p28 — *Unclear responsibility or governance gap*

Failures where no party owns a needed action, accountability is split or undefined, or governance roles are ambiguous, leaving the action undone or escalated. The mechanism is missing or contested authority rather than coordination cost.

**Mechanism criterion:** A required action goes undone or contested because responsibility is unassigned, split, or unclear.

### p29 — *Misaligned incentives between parties*

Failures where two parties whose cooperation is required have structurally divergent or opposed incentives, causing one to behave in ways that defeat the other's objective. Includes split-incentive, gaming, principal-agent, and intermediary-channel disincentives.

**Mechanism criterion:** Two parties' incentives are structurally misaligned such that rational behaviour by one undermines the other's objective.

### p30 — *Contractual rigidity or scope gap*

Failures where contracts cannot be amended, do not anticipate the actual scope, or impose terms that exclude needed actions. Includes stale scope, take-or-pay, fixed-fee overruns, fixed contract durations, and ambiguous obligations.

**Mechanism criterion:** A contract's specific terms or rigidity prevents the action or accommodation needed.

### p40 — *Vendor dependency and lock-in*

Failures from dependence on a single vendor, OEM, or proprietary technology that retains exclusive control over support, IP, or interfaces, foreclosing third-party action or independent diagnosis. Distinct from interoperability failure because the lock-in is contractual or proprietary rather than technical incompatibility.

**Mechanism criterion:** Exclusive vendor or OEM control over support, IP, or interface limits the user's options or imposes ongoing cost.

### p63 — *Trust-or-distrust dynamic between parties*

Failures where erosion or absence of inter-party trust drives commitment failure: stakeholder commitment reversal, contractor commitment erosion, late-arriving trust collapse. Distinct from coordination because the mechanism is interpersonal trust dynamics.

**Mechanism criterion:** Erosion or absence of trust between specific parties drives breakdown of commitment.

---

## t10 — Human, organisational, and behavioural failures

_Mechanisms involving people and the host organisation: stakeholder opposition, customer recruitment shortfall, behavioural friction, workforce/skill scarcity, organisational change cycles, and equity-distributional outcomes._

**Mechanism family:** Individual behaviour, workforce, organisational maturity, or social response drives the failure.

**Parents:** 6

### p31 — *Stakeholder trust, opposition, and social licence*

Failures where community opposition, distrust, or absence of social licence delays, alters, or blocks projects. The mechanism is collective social response to the project, not technical or economic feasibility.

**Mechanism criterion:** Public, community, or stakeholder opposition or distrust drives the failure outcome.

### p32 — *Customer engagement and recruitment shortfall*

Failures in recruiting, retaining, or engaging participants in programmes or trials, where uptake falls below required threshold due to communication, motivation, friction, or demographic mismatch. The mechanism is the gap between programme design and participant behavioural response.

**Mechanism criterion:** Customer or participant uptake, conversion, or engagement falls below required levels because of design-behaviour mismatch.

### p33 — *Behavioural friction and inertia*

Failures where individual behaviour, habit, or rebound effects produce outcomes contrary to programme or design intent. Includes consumer reluctance, manual override, demand rebound, and lock-in inertia.

**Mechanism criterion:** Individual human behaviour, habit, or psychological response drives the deviation from intended outcome.

### p34 — *Workforce capacity, skill, or availability shortfall*

Failures where required labour, expertise, or specialist personnel are unavailable, undertrained, or scheduled elsewhere, delaying or degrading project outcomes. Includes vendor scheduling, multidisciplinary scarcity, key-person loss, volunteer fatigue, and workforce planning absence.

**Mechanism criterion:** Insufficient skilled labour or specialist availability is the proximate cause of delay or quality loss.

### p35 — *Organisational change and process maturity gap*

Failures where the host organisation's internal change cycle, process maturity, or operational practices cannot accommodate the project's requirements within its timeline. Includes long change cycles, BAU integration gaps, internal approval procedures, and organisational fragmentation.

**Mechanism criterion:** Internal organisational processes or maturity prevent timely or effective adoption or operation of the project.

### p71 — *Equity and distributional outcome failure*

Failures where programme design produces regressive or equity-impairing outcomes, excluding specific demographic or low-income groups from benefits. The mechanism is design that does not accommodate distributional differences.

**Mechanism criterion:** Programme design systematically excludes or disadvantages specific demographic or income groups.

---

## t11 — Project execution and operational lifecycle failures

_Mechanisms tied to how a project is planned, discovered, and run over time: front-end scoping inadequacy, late-discovered site/counterparty conditions, exogenous shocks, long-term operating reliability burden, and pilot-design generalisability limits._

**Mechanism family:** Project lifecycle realities — planning, discovery, shock, ageing — drive the failure.

**Parents:** 5

### p36 — *Project planning and scoping inadequacy*

Failures driven by inadequate upfront scoping, contingency, baseline, or design definition, leading to discovery of problems mid-execution that could have been anticipated. The mechanism is insufficient front-end loading rather than external surprise.

**Mechanism criterion:** Front-end planning, scoping, or design definition was insufficient and the gap surfaces during execution.

### p37 — *Late-discovered constraint or hidden site condition*

Failures where a constraint, hazard, or condition is discovered after commitment or installation, forcing rework. Includes brownfield surprises, contamination, undocumented history, undisclosed counterparty information, and post-approval site issues.

**Mechanism criterion:** A site, asset, or counterparty condition unknown at commitment is discovered later and forces rework.

### p39 — *External shock or supply-chain disruption*

Failures driven by external macro events: pandemics, geopolitical conflict, currency moves, industrial action, supply chain shocks, that the project did not cause and could not control. The mechanism is exogenous shock rather than internal failing.

**Mechanism criterion:** An exogenous external event disrupts inputs, schedules, or costs in ways the project could not foresee or control.

### p53 — *Long-term operating reliability and maintenance burden*

Failures arising from cumulative operational realities: progressive degradation, maintenance access difficulty, spare parts logistics, ageing assets, recurring downtime that exceed initial planning. The mechanism is operational lifetime burden rather than initial design.

**Mechanism criterion:** Cumulative operational, maintenance, or ageing burden over lifetime drives the failure.

### p57 — *Pilot and trial design representativeness limit*

Failures where pilot or trial design conditions limit external validity: short duration, opt-in self-selection, atypical weather windows, gifting bias, unrepresentative demographics. The mechanism is generalisability gap due to pilot design.

**Mechanism criterion:** Pilot or trial design choices limit the generalisability of results to broader deployment contexts.

---

## t12 — Safety hazard burden

_Mechanisms in which a specific physical hazard imposes additional engineering, classification, or operational burden distinct from regulatory gap or material limit alone._

**Mechanism family:** Real physical hazard creates compounding control or compliance load.

**Parents:** 1

### p54 — *Safety hazard creates new control or cost burden*

Failures where a specific safety hazard (fire, gas group, hazardous area, refrigerant flammability, hydrogen, BESS fire risk, CO accumulation) creates additional engineering, classification, or cost burden. Distinct from regulatory gap because the hazard is real and physical.

**Mechanism criterion:** A specific physical safety hazard imposes additional engineering, control, or compliance burden.

---
