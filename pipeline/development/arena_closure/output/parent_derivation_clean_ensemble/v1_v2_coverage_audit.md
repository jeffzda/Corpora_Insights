# v1 vs v2 parent-taxonomy coverage audit

**v1**: 71 parents (single Opus pass).  **v2**: 70 parents (43 core ≥90% + 27 promoted high-tier from 59-rep ensemble).
**Cost:** $0.41, 158s wall.

## Verdict

v2 coverage is broadly complete but has roughly seven genuine gaps relative to v1: aggregate-vs-individual scale mismatch (p19), process/reactor design limits (p51), long-term reliability/maintenance burden (p53), safety-hazard burden (p54), knowledge dissemination/benchmarking (p60), parasitic load/round-trip losses (p64), and diminishing returns/saturation (p67). Of these, p53, p54, and p64 are the most consequential for an energy-tech PM and should be re-added as first-class parents; p19 and p67 are analytically distinct enough to warrant addition; p51 could be folded into a refined process/feedstock parent alongside high_06; p60 and p61 (communication) could be accepted as subsumed into trust/social-licence and information-asymmetry. v2 adds material new coverage v1 lacked — price volatility (p23), residual emissions (p24), key-person dependency (p36), DR/aggregator delivery (p41), automation gaps (p43), technology immaturity (high_19), observability (high_25), subsurface characterisation (high_27), and procurement pathologies (high_28) — reflecting the deliberation-rich ensemble surfacing climate-tech and operational mechanisms the single-pass v1 missed. Net: v2 is the stronger taxonomy, but should re-add ~3–5 v1 parents covering lifecycle reliability, safety burden, parasitic losses, aggregate-scale effects, and process-design limits.

## Mechanisms missing from v2 (8)

| v1_ids | mechanism_class | evidence | recommendation |
|---|---|---|---|
| p19 | Aggregate vs. individual scale mismatch | Correlation/phase effects causing aggregate behaviour to diverge from sum of individual behaviours (e.g., coincident peaks, portfolio diversification failure) has no clear v2 home; distinct from heterogeneity (p21) and temporal mismatch (p18). | add_as_new_parent |
| p51 | Process design or reactor performance limit | Process/reactor-design-induced shortfalls (selectivity, conversion, side-products) are distinct from material limits (p08) and feedstock variability (high_06); a PM scanning chemical/process tech has no clean landing. | add_as_new_parent |
| p53 | Long-term operating reliability and maintenance burden | Cumulative ageing, degradation, and lifetime O&M burden is a major asset-class failure mode with no v2 parent; p09 (envelope) and p13 (defects) cover acute, not cumulative, issues. | add_as_new_parent |
| p54 | Safety hazard creates new control or cost burden | Safety-driven engineering/compliance burden (e.g., hydrogen, battery thermal runaway, high-voltage) is a distinct mechanism not captured by regulatory or material-limit parents. | add_as_new_parent |
| p60 | Knowledge dissemination and benchmarking gap | Cross-industry learning, benchmarking, and dissemination-structure failures sit between scientific-knowledge gap (p05) and information asymmetry (p32) but are neither; ecosystem-level mechanism uncovered. | add_as_new_parent |
| p61 | Communication clarity and content design failure | Failures of message framing/clarity to audiences (regulators, customers, communities) are distinct from trust (high_16) and recruitment (p39); no v2 home. | merge_into_high_16 |
| p64 | Parasitic load and round-trip energy loss | Conversion/auxiliary energy losses eroding net output (RTE in storage, parasitic loads in DAC/electrolysis) are a fundamental energy-tech mechanism with no v2 parent. | add_as_new_parent |
| p67 | Diminishing returns or marginal-effect saturation | Marginal-return saturation (more data, more sensors, more capacity yielding less benefit) is a distinct decision-relevant mechanism not captured anywhere in v2. | add_as_new_parent |

## Mechanisms new in v2 (9)

| v2_ids | mechanism_class | evidence |
|---|---|---|
| p23 | Volatile or correlated price exposure | v1 had price-signal distortion (p21) and cost-benefit (p20) but no parent for revenue/input-price volatility eroding viability — a distinct hedging/commercial-structure mechanism. |
| p24 | Hard-to-abate residual emissions | Climate-tech-specific mechanism: process or feedstock characteristics leave residual emissions with no commercial low-emissions alternative; not in v1. |
| p36 | Personnel turnover and key-person dependency | v1's workforce parent (p34) covers skill scarcity but not key-person concentration/continuity loss; v2 isolates this. |
| p41 | Demand response and aggregator delivery shortfall | Aggregator/DR under-delivery at activation is a distinct grid/market mechanism not isolated in v1. |
| p43 | Manual process bottlenecks and automation gaps | Manual-process throughput caps and automation-gap failures absent from v1; partially overlaps with p35 but mechanistically distinct. |
| high_19 | Technology immaturity / deployment readiness | TRL/readiness as a top-level mechanism distinct from lab-to-field translation (p07) or knowledge gap (p05); v1 lacked an immaturity parent. |
| high_25 | Visibility and observability gaps | Operational observability for distributed/DER systems is a distinct mechanism beyond data absence (p01) and measurement limits (p03); v1 lacked it. |
| high_27 | Subsurface/resource characterisation uncertainty | Pre-commitment natural-resource (geothermal, CCS, mining, wind) characterisation uncertainty is a distinct upstream mechanism not in v1. |
| high_28 | Procurement/tender process pathologies | Procurement/tender-design failures distinct from contract structure (high_14) and coordination (p30); v1 had no parent for this. |

## v1 → v2 mapping (71 entries)

Verdict counts: {'mapped': 46, 'merged': 10, 'split': 7, 'missing': 8}

| v1_id | v1_name | verdict | v2_targets | reason |
|---|---|---|---|---|
| p01 | Missing or inaccessible data | mapped | p01 | Direct match on data absence/inaccessibility. |
| p02 | Measurement and instrumentation inadequacy | mapped | p03 | Direct match on sensing/measurement faithfulness. |
| p03 | Model and forecast inaccuracy from assumption mismatch | mapped | p04 | Model representational error covers assumption mismatch. |
| p04 | Forecast skill ceiling under inherent uncertainty | merged | p04 | Subsumed into model/forecast error; intrinsic-uncertainty distinction lost but covered. |
| p05 | Knowledge gap or information asymmetry | split | p05, p32 | Split into scientific knowledge gap and inter-party information asymmetry. |
| p06 | Material, thermal, or chemical physical limit | mapped | p08 | Direct match on material/chemical/physical limits. |
| p07 | Geometric, spatial, or footprint constraint | mapped | p11 | Direct match on spatial/geometric constraints. |
| p08 | Environmental exposure and external physical disturbance | mapped | p10 | Direct match on environmental/weather exposure. |
| p09 | Operating-envelope and design-envelope mismatch | mapped | p09 | Direct match on operating outside design envelope. |
| p10 | Capacity, sizing, or rating shortfall | split | p12, high_01 | Split into asset sizing and network capacity constraints. |
| p11 | Control architecture and control-loop failure | mapped | p15 | Direct match on control logic/configuration errors. |
| p12 | Cadence, latency, or timing mismatch | mapped | high_02 | Direct match on cadence/latency mismatches. |
| p13 | Interface, protocol, and interoperability failure | split | p16, high_03, high_04 | Split into interoperability, communication channels, and standards absence. |
| p14 | Legacy or pre-existing design incompatibility | merged | p16, high_18 | Subsumed into interoperability and architectural rigidity; legacy framing softened. |
| p15 | Inverter-based resource grid-interaction failure | mapped | p14 | Direct match on IBR/grid-stability dynamics. |
| p16 | Scale-up and lab-to-field translation failure | mapped | p07 | Direct match on lab-to-field/pilot-to-scale translation. |
| p17 | Heterogeneity defeats uniform treatment | mapped | p21 | Direct match on heterogeneity vs one-size-fits-all. |
| p18 | Coupled-objective trade-off | mapped | p19 | Direct match on coupled trade-offs/competing objectives. |
| p19 | Aggregate vs. individual scale mismatch | missing |  | No v2 parent captures aggregate-vs-individual divergence from correlation/phase effects. |
| p20 | Cost-benefit threshold not crossed | mapped | high_08 | Maps to cost-structure/unit-economics infeasibility. |
| p21 | Price signal absent, distorted, or misaligned | mapped | high_09 | Direct match on distorted price/tariff signals. |
| p22 | Value capture blocked by market or regulatory structure | mapped | high_10 | Direct match on missing-market/value capture. |
| p23 | Regulatory framework gap or misfit for novel context | mapped | p25 | Direct match on regulatory framework absence. |
| p24 | Regulatory approval timing and process friction | mapped | p27 | Direct match on regulatory procedural friction. |
| p25 | Regulatory policy uncertainty and instability | mapped | p28 | Direct match on policy uncertainty/instability. |
| p26 | Regulatory metric or method design distortion | merged | p20 | Subsumed into metric/objective misspecification at higher abstraction. |
| p27 | Multi-party coordination overhead | mapped | p30 | Direct match on multi-party coordination overhead. |
| p28 | Unclear responsibility or governance gap | merged | p26, p30 | Subsumed into jurisdictional fragmentation and coordination overhead. |
| p29 | Misaligned incentives between parties | mapped | p31 | Direct match on misaligned incentives between actors. |
| p30 | Contractual rigidity or scope gap | mapped | high_14 | Direct match on contract structure misalignment. |
| p31 | Stakeholder trust, opposition, and social licence | mapped | high_16 | Direct match on trust and social licence. |
| p32 | Customer engagement and recruitment shortfall | mapped | p39 | Direct match on customer recruitment/conversion. |
| p33 | Behavioural friction and inertia | merged | high_17, p39 | Behavioural mechanisms partly captured via rebound and recruitment friction. |
| p34 | Workforce capacity, skill, or availability shortfall | mapped | high_15 | Direct match on workforce skill scarcity. |
| p35 | Organisational change and process maturity gap | merged | p43, p37 | Partially covered via manual-process gaps and planning inadequacy; org-change framing softened. |
| p36 | Project planning and scoping inadequacy | mapped | p37 | Direct match on project planning/scoping. |
| p37 | Late-discovered constraint or hidden site condition | mapped | p38 | Direct match on late discovery forcing rework. |
| p38 | Commissioning and integration testing exposure | merged | p06 | Subsumed into broader test/validation coverage gaps. |
| p39 | External shock or supply-chain disruption | mapped | p35 | Direct match on supply chain disruption. |
| p40 | Vendor dependency and lock-in | mapped | p34 | Direct match on vendor lock-in. |
| p41 | Standards, certification, and compliance specification gap | mapped | high_04 | Direct match on standards absence/obsolescence. |
| p42 | Compliance verification and enforcement weakness | mapped | p29 | Direct match on verification/enforcement gaps. |
| p43 | Investment finance and risk-transfer gap | mapped | high_13 | Direct match on investment risk/bankability. |
| p44 | Chicken-and-egg deployment deadlock | mapped | p33 | Direct match on chicken-and-egg deadlocks. |
| p45 | Market-structure barrier or competitive distortion | mapped | high_11 | Direct match on market structure/incumbent advantage. |
| p46 | Incumbent technology displacement and transition friction | mapped | high_11 | Covered by market structure and incumbent advantage. |
| p47 | Demand-supply temporal or spatial mismatch | split | p18, high_07 | Split into temporal and geographic/locational mismatch. |
| p48 | System-wide intermittency and balancing stress | merged | p14, p18 | Partially covered via grid-stability and temporal mismatch; system-balancing framing softened. |
| p49 | Network connection and hosting capacity limit | mapped | high_01 | Direct match on network capacity constraints. |
| p50 | Feedstock and resource quality variability | mapped | high_06 | Direct match on feedstock/input quality variability. |
| p51 | Process design or reactor performance limit | missing |  | No v2 parent captures process/reactor-design-induced performance limits as distinct from material limits. |
| p52 | Manufacturing yield and fabrication quality | mapped | p13 | Direct match on manufacturing/fabrication defects. |
| p53 | Long-term operating reliability and maintenance burden | missing |  | No v2 parent captures cumulative ageing/maintenance burden over asset lifetime. |
| p54 | Safety hazard creates new control or cost burden | missing |  | No v2 parent captures safety-hazard-induced engineering or compliance burden. |
| p55 | Cyber security and IT system fragility | split | p17, high_05 | Split into cybersecurity and software/IT fragility. |
| p56 | Software development and integration constraint | mapped | high_05 | Direct match on software/firmware/IT fragility. |
| p57 | Pilot and trial design representativeness limit | mapped | high_20 | Direct match on selection/sampling representativeness. |
| p58 | Validation infeasibility and absent ground truth | split | p06, high_21 | Split into verification coverage gaps and counterfactual/baseline difficulty. |
| p59 | Data infrastructure and pipeline inadequacy | mapped | p02 | Maps to data quality/format/integration defects. |
| p60 | Knowledge dissemination and benchmarking gap | missing |  | No v2 parent captures cross-industry learning, benchmarking, or dissemination structure failures. |
| p61 | Communication clarity and content design failure | missing |  | No v2 parent captures communication content/framing failures to audiences. |
| p62 | Optimisation objective or scope misspecification | split | p20, high_23 | Split into metric misspecification and lifecycle/externalities scope omissions. |
| p63 | Trust-or-distrust dynamic between parties | merged | high_16 | Subsumed into trust/social licence; inter-party trust framing partly preserved. |
| p64 | Parasitic load and round-trip energy loss | missing |  | No v2 parent captures conversion/auxiliary energy losses eroding net output. |
| p65 | Complexity-induced failure proliferation | merged | p40 | Partly covered via single-point-of-failure; complexity-cascade framing softened. |
| p66 | Modularity and reconfigurability absence | mapped | high_18 | Direct match on architectural rigidity. |
| p67 | Diminishing returns or marginal-effect saturation | missing |  | No v2 parent captures marginal-return saturation as a distinct mechanism. |
| p68 | Lifecycle and life-of-asset accounting mismatch | mapped | high_23 | Maps to lifecycle/externalities accounting omissions. |
| p69 | Conservatism bias inflates cost or constraint | mapped | high_22 | Direct match on conservative-margin/over-specification bias. |
| p70 | Customer or counterparty data accuracy failure | mapped | p02 | Maps to data quality/semantic defects. |
| p71 | Equity and distributional outcome failure | mapped | high_26 | Direct match on equity/distributional barriers. |

## v2 → v1 mapping (70 entries)

Verdict counts: {'descended_from_v1': 43, 'refined_from_v1': 18, 'new_in_v2': 9}

| v2_id | v2_name | verdict | v1_sources | reason |
|---|---|---|---|---|
| p01 | Missing or inaccessible data | descended_from_v1 | p01 | Same mechanism class. |
| p02 | Data quality, format, and semantic defects | refined_from_v1 | p59, p70 | Refined from data infrastructure and customer-data accuracy. |
| p03 | Measurement and sensing limitations | descended_from_v1 | p02 | Same mechanism class. |
| p04 | Model and forecast representational error | descended_from_v1 | p03, p04 | Same model/forecast inaccuracy class. |
| p05 | Mechanism understanding and scientific knowledge gap | refined_from_v1 | p05 | Refined from broader knowledge gap by separating scientific from inter-party. |
| p06 | Test, validation, and verification coverage gaps | refined_from_v1 | p38, p58 | Refined from commissioning exposure and validation infeasibility. |
| p07 | Lab-to-field and pilot-to-scale translation failure | descended_from_v1 | p16 | Same scale-up mechanism. |
| p08 | Material, chemical, and physical-property limits | descended_from_v1 | p06 | Same physical-limits mechanism. |
| p09 | Equipment operating outside design envelope | descended_from_v1 | p09 | Same envelope-mismatch class. |
| p10 | Environmental and weather exposure | descended_from_v1 | p08 | Same environmental exposure class. |
| p11 | Spatial, geometric, and siting constraints | descended_from_v1 | p07 | Same spatial-constraint class. |
| p12 | Capacity, sizing, and headroom shortfall | refined_from_v1 | p10 | Refined from capacity shortfall, separating asset-level from network. |
| p13 | Manufacturing, fabrication, and installation defects | descended_from_v1 | p52 | Same manufacturing-defect class, expanded to installation. |
| p14 | Inverter-based resource and grid-stability dynamics | descended_from_v1 | p15 | Same IBR/grid-interaction class. |
| p15 | Control logic, configuration, and protection errors | descended_from_v1 | p11 | Same control-architecture class. |
| p16 | Interoperability and interface incompatibility | refined_from_v1 | p13 | Refined from broader interface failure into bilateral interop. |
| p17 | Cybersecurity, authentication, and access-control exposure | refined_from_v1 | p55 | Refined from cyber/IT fragility, separating cyber from software. |
| p18 | Temporal mismatch between supply and demand | refined_from_v1 | p47 | Refined from temporal/spatial mismatch into temporal-only. |
| p19 | Coupled trade-offs and competing objectives | descended_from_v1 | p18 | Same trade-off class. |
| p20 | Optimisation objective and metric misspecification | descended_from_v1 | p62, p26 | Same optimisation/metric misspecification class. |
| p21 | Heterogeneity defeats one-size-fits-all design | descended_from_v1 | p17 | Same heterogeneity class. |
| p22 | Capital cost and upfront-investment barriers | refined_from_v1 | p20 | Refined from cost-benefit threshold, narrowed to capital-cost focus. |
| p23 | Volatile or correlated price exposure | new_in_v2 |  | No v1 parent named price volatility/correlation as a distinct mechanism. |
| p24 | Hard-to-abate residual emissions | new_in_v2 |  | No v1 parent captures residual-emissions abatement constraint. |
| p25 | Regulatory framework absence or gap | descended_from_v1 | p23 | Same regulatory framework gap class. |
| p26 | Regulatory ambiguity and jurisdictional fragmentation | refined_from_v1 | p28 | Refined from governance gap with regulatory-fragmentation framing. |
| p27 | Regulatory process delay and procedural friction | descended_from_v1 | p24 | Same regulatory procedural-friction class. |
| p28 | Policy uncertainty and instability | descended_from_v1 | p25 | Same policy uncertainty class. |
| p29 | Compliance verification and enforcement gaps | descended_from_v1 | p42 | Same verification/enforcement class. |
| p30 | Multi-party coordination overhead | descended_from_v1 | p27 | Same coordination-overhead class. |
| p31 | Misaligned incentives between actors | descended_from_v1 | p29 | Same misaligned-incentive class. |
| p32 | Information asymmetry between parties | refined_from_v1 | p05 | Refined from knowledge-gap parent into inter-party asymmetry. |
| p33 | Chicken-and-egg coordination deadlocks | descended_from_v1 | p44 | Same chicken-and-egg class. |
| p34 | Vendor lock-in and proprietary closure | descended_from_v1 | p40 | Same vendor lock-in class. |
| p35 | Supply chain and logistics disruption | descended_from_v1 | p39 | Same supply-chain disruption class. |
| p36 | Personnel turnover and key-person dependency | new_in_v2 |  | No v1 parent isolates key-person/turnover dependency. |
| p37 | Project planning and scoping inadequacy | descended_from_v1 | p36 | Same planning/scoping class. |
| p38 | Late discovery forcing rework | descended_from_v1 | p37 | Same late-discovery class. |
| p39 | Customer recruitment and conversion friction | descended_from_v1 | p32 | Same customer-recruitment class. |
| p40 | Single point of failure and shared-resource exposure | refined_from_v1 | p65 | Refined from complexity/proliferation toward shared-dependency framing. |
| p41 | Demand response and aggregator delivery shortfall | new_in_v2 |  | No v1 parent captures aggregator/DR delivery shortfall as distinct mechanism. |
| p42 | Funding instrument and milestone-structure misfit | refined_from_v1 | p30 | Refined from contractual rigidity into funding-instrument focus. |
| p43 | Manual process bottlenecks and automation gaps | new_in_v2 |  | No v1 parent captures manual/automation bottlenecks distinctly. |
| high_01 | Network capacity constraints | refined_from_v1 | p49 | Refined from network connection/hosting capacity limit. |
| high_02 | Cadence/latency mismatches in coupled control loops | descended_from_v1 | p12 | Same cadence/latency class. |
| high_03 | Communication channel and connectivity failures | refined_from_v1 | p13 | Refined from interface failure, isolating connectivity. |
| high_04 | Standards absence/obsolescence | descended_from_v1 | p41 | Same standards-gap class. |
| high_05 | Software/firmware/IT fragility | descended_from_v1 | p56, p55 | Same software/IT fragility class. |
| high_06 | Feedstock and input-quality variability | descended_from_v1 | p50 | Same feedstock variability class. |
| high_07 | Geographic/locational mismatch | refined_from_v1 | p47 | Refined from temporal/spatial mismatch, isolating spatial. |
| high_08 | Cost-structure and unit-economics infeasibility | descended_from_v1 | p20 | Same cost-benefit threshold class. |
| high_09 | Distorted price/tariff signals | descended_from_v1 | p21 | Same price-signal distortion class. |
| high_10 | Value not capturable by available market mechanisms | descended_from_v1 | p22 | Same missing-market class. |
| high_11 | Market structure and incumbent advantage | descended_from_v1 | p45, p46 | Same market-structure/incumbent class. |
| high_12 | Subsidy/incentive design distortions | refined_from_v1 | p26, p21 | Refined from regulatory metric distortion and price-signal misalignment. |
| high_13 | Investment risk and bankability barriers | descended_from_v1 | p43 | Same finance/risk-transfer class. |
| high_14 | Contract structure misalignment | descended_from_v1 | p30 | Same contractual rigidity class. |
| high_15 | Workforce skill scarcity | descended_from_v1 | p34 | Same workforce/skill class. |
| high_16 | Trust and social licence | descended_from_v1 | p31, p63 | Same trust/social-licence class. |
| high_17 | Behavioural rebound | refined_from_v1 | p33 | Refined from behavioural friction toward rebound-specific mechanism. |
| high_18 | Architectural rigidity | descended_from_v1 | p66, p14 | Same modularity-absence/legacy class. |
| high_19 | Technology immaturity | new_in_v2 |  | No v1 parent isolates deployment-readiness/TRL immaturity as distinct mechanism. |
| high_20 | Selection/sampling representativeness bias | descended_from_v1 | p57 | Same pilot-representativeness class. |
| high_21 | Counterfactual/baseline measurement difficulty | refined_from_v1 | p58 | Refined from validation infeasibility, isolating baseline/attribution. |
| high_22 | Conservative-margin and over-specification bias | descended_from_v1 | p69 | Same conservatism-bias class. |
| high_23 | Externalities and lifecycle accounting omissions | descended_from_v1 | p68, p62 | Same lifecycle/scope-omission class. |
| high_25 | Visibility and observability gaps | new_in_v2 |  | No v1 parent isolates operational observability/visibility for DER. |
| high_26 | Equity and distributional barriers | descended_from_v1 | p71 | Same equity/distributional class. |
| high_27 | Subsurface/resource characterisation uncertainty | new_in_v2 |  | No v1 parent isolates pre-commitment subsurface/resource characterisation uncertainty. |
| high_28 | Procurement/tender process pathologies | new_in_v2 |  | No v1 parent captures procurement/tender process pathologies distinctly. |