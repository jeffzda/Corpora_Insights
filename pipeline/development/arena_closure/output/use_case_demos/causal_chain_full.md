# Causal-chain test — full corpus run

Applied the v2 parent-layer causal-chain diagnostic to **367 ARENA events** spanning ≥4 distinct parent archetypes each. The empirical question: do real failure events display causal-chain structure when traced through the parent layer, or are multi-parent events bundles of orthogonal failures within the same project?

**Cost:** $1.99, 1166s wall across 13 batches.

## Verdict distribution

| verdict | n | % |
|---|---:|---:|
| causal_chain | 206 | 56% |
| single_root_with_multiple_consequences | 63 | 17% |
| partial_chain | 53 | 14% |
| cluster_of_orthogonal_failures | 45 | 12% |

## Confidence distribution

| confidence | n |
|---|---:|
| high | 204 |
| medium | 163 |

## 20 longest reconstructed chains

### EVT-0037 — Lake Bonney Battery Energy Storage System

**Verdict:** `causal_chain` · confidence: `high` · chain length: 8 links

**Chain:**

- p36 -> p24
- p36 -> p05
- p05 -> p24
- p24 -> p38
- p38 -> p23
- p23 -> p28
- p28 -> p49
- p37 -> p24

**Evidence:** 0651-0008: 'major consideration overlooked during site selection' (p36); 0651-0071: black-boxed PSCAD models (p05) caused integration failure; 0651-0070: model loading failure (p38); 0651-0069: FSSIA took 5 months, no applicant visibility (p23/p28); 0651-0077: brownfield BESS investment deterred (p49).

### EVT-0004 — Musselroe Wind Farm FCAS Trial

**Verdict:** `causal_chain` · confidence: `high` · chain length: 7 links

**Chain:**

- p14 -> p09
- p09 -> p11
- p11 -> p13
- p13 -> p24
- p24 -> p36
- p36 -> p38
- p38 -> p16

**Evidence:** 1292-0021: existing plant 'did not facilitate Active Power dispatch' (p14); 0720-0040: retrofit created additional complexity (p09); 1292-0010: PPC logic 'did not adhere to plant limits' (p11); 0721-0020: control signal incompatibility (p13); 0721-0009: many iterations for AEMO conformance (p24); 1292-0028: incremental testing required (p38).

### EVT-0062 — Project SHIELD - Synchronising Heterogeneous Information to Evaluate Limits for DNSP

**Verdict:** `causal_chain` · confidence: `high` · chain length: 5 links

**Chain:**

- p01 -> p13
- p13 -> p58
- p01 -> p67
- p17 -> p13
- p13 -> p20

**Evidence:** 1335-0041: data privacy barriers left only 50 devices (p01); 0809-0013: heterogeneous sources (p17) caused incompatible formats (p13); 0809-0057: inferred rather than measured data undermined validation (p58); 0811-0024: low density (p67); 1336-0042: low quantity made integration cost-prohibitive (p20).

### EVT-0006 — United Energy Distribution Demand Response

**Verdict:** `causal_chain` · confidence: `high` · chain length: 5 links

**Chain:**

- p14 -> p49
- p49 -> p11
- p11 -> p67
- p53 -> p49
- p02 -> p49

**Evidence:** 1439-0026: legacy voltage regulation insufficient (p14); 1439-0032/1440-0025: long feeders and tap exhaustion (p49); 1007-0046: voltage spread causes control failure (p11); 1439-0034/1440-0039: unbalanced circuits prevent DVMS improvement (p67); 1440-0026: seized tap screws (p53) and 1440-0042: nameplate mismatch (p02) blocked remediation.

### EVT-0008 — Lake Bonney Battery Energy Storage System

**Verdict:** `causal_chain` · confidence: `high` · chain length: 5 links

**Chain:**

- p39 -> p25
- p25 -> p49
- p49 -> p18
- p18 -> p62
- p17 -> p18

**Evidence:** 0648-0009: transmission tower collapse caused SA islanding (p39); 0648-0044: AEMO imposed binding FCAS constraints (p25); 0647-0025/0648-0021: BESS constrained to contingency FCAS only (p49); 0648-0053/0648-0083: regulation FCAS and arbitrage revenue limited (p18); 0648-0069/0647-0079: uniform SOC range suboptimal (p17→p62).

### EVT-0030 — Horizon Power Business Model Pilot Phase 1

**Verdict:** `causal_chain` · confidence: `high` · chain length: 5 links

**Chain:**

- p15 -> p27
- p15 -> p19
- p19 -> p11
- p41 -> p15
- p02 -> p58

**Evidence:** 0572-0015: 'highest aggregate PV variations caused by synchronised inverter tripping' not clouds (p15→p27); 0572-0017: 41 inverters tripped simultaneously (p19→p11); 0572-0037: inverters 'too easily tripped' due to compliance gap (p41→p15); 0572-0020: specific inverters trip more frequently suggesting p11 configuration issues; 0572-0018/0572-0058: Wattwatcher vs SCADA discrepancy (p02→p58).

### EVT-0095 — Project Converge ACT Distributed Energy Resources Demonstration Pilot

**Verdict:** `causal_chain` · confidence: `medium` · chain length: 5 links

**Chain:**

- p14 -> p11
- p14 -> p69
- p69 -> p17
- p17 -> p12
- p12 -> p41

**Evidence:** 0801-0045/0801-0076: legacy voltage regulation insufficient under increasing DER (p14→p11); 0802-0058: FOE violations at current penetration (p69); 0801-0043: perfect controllability assumed but real-world limited (p17→p12); 0799-0027: FOE produces temporal allocation mismatch (p12); 0801-0042: violations under FCAS worst-case not in compliance scope (p41); 0897-0039: voltage limits breached blocking demand response (p11).

### EVT-0019 — Energy Storage for Commercial Renewable Integration (ESCRI) Phase 2

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p36 -> p62
- p62 -> p18
- p18 -> p21
- p22 -> p18

**Evidence:** 0480-0045/0481-0030: MVP software 'does not optimise energy arbitrage' (p36→p62); 0481-0025/0481-0026: FCAS bias forces high SOC conflicting arbitrage (p18); 0483-0033: arbitrage revenue consistently very low (p21); 0482-0064/0481-0061: cap derivatives not offered despite identified opportunity (p22).

### EVT-0003 — Aeolius Wind Forecasting Project

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p02 -> p04
- p04 -> p03
- p03 -> p16
- p17 -> p04

**Evidence:** 1119-0031: anemometers on turbines 'fundamental limitation' (p02); 1121-0005: turbulence 'cannot be accurately predicted' causing turning-point failure (p04); 1121-0003: lag behaviour similar to AWEFS (p03); 1121-0006: site-specific randomness limits transferability (p16); 1121-0007: averaging defeats turbine-level features (p17→p04).

### EVT-0007 — Neoen Victorian Big Battery (Moorabool) Retrofit

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p09 -> p15
- p15 -> p23
- p23 -> p46
- p46 -> p26

**Evidence:** 0077-0019: 500V inverter terminal vs 220kV connection point large impedance (p09); 0077-0036: GFM performance 'more technically demanding at connection point' (p15); 1302-0010/1303-0015: k-factor increase causes active power drop violating NER (p23); 1302-0011: HPR connected under different rules avoided this conflict (p46); 1303-0017: impedance induces higher losses requiring higher k-factor (p26).

### EVT-0006 — AEMO - Project EDGE (Energy Demand and Generation Exchange)

**Verdict:** `partial_chain` · confidence: `medium` · chain length: 4 links

**Chain:**

- p19 -> p13
- p17 -> p13
- p13 -> p62
- p02 -> p26

**Evidence:** 0208-0051/0209-0088: LSE viable only with sufficient concentrated DER (p19); 1095-0063: C&I atypical demand unsuitable (p17); 0208-0052: DER data hub standardisation needed (p13); 1095-0062: 90% compliance threshold forces overshoot (p26→p62); 1095-0064: smart meter data insufficient for voltage compliance verification (p02). p06 battery degradation (1095-0097) is orthogonal.

### EVT-0029 — Testing the Performance of Lithium Ion Batteries

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p13 -> p36
- p13 -> p38
- p13 -> p05
- p05 -> p11

**Evidence:** 0338-0033/0593-0008/0661-0003: 'no standardised approach to battery-inverter communications' (p13) is root; 0593-0034: BMS integration 'most challenging aspect' (p36→p38); 0594-0038/0594-0039: unclear BMS parameters caused incorrect configuration (p05→p11); 0661-0085: rapid battery market development outpaces inverter compatibility (p38).

### EVT-0117 — Port Kembla Steelworks Renewables & Emissions Reduction Study

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p44 -> p45
- p45 -> p47
- p47 -> p16
- p16 -> p50

**Evidence:** 1322-0001: 'no established supply chain for bulk biochar in Australia' (p44); 0789-0008/1322-0003: small fragmented producers (p45) unable to supply required volume; 1322-0007: trial scope reduced to match available supply (p47); 0789-0093: 965 dmt 'very small relative to normal trials' limiting representativeness (p16); 1324-0004: batch variability caused re-optimisation (p50).

### EVT-0020 — Consumer Energy Systems Providing Cost-Effective Grid Support

**Verdict:** `partial_chain` · confidence: `medium` · chain length: 4 links

**Chain:**

- p26 -> p19
- p19 -> p42
- p42 -> p33
- p21 -> p32

**Evidence:** 0368-0016: peak forecasting bias creates false payments (p26→p19); 0368-0017: OPF sensitivity to forecast errors (p19); 0368-0018: commitment problem enables gaming (p42→p33); 0369-0075: payments 'not motivated to change energy practices' (p21→p32); 0369-0077: 11 households lacked detail to choose payment type (p61) — p61 partially orthogonal.

### EVT-0058 — Achieving Cost-Affective Abatement

**Verdict:** `causal_chain` · confidence: `medium` · chain length: 4 links

**Chain:**

- p46 -> p20
- p20 -> p25
- p25 -> p22
- p22 -> p34

**Evidence:** 0403-0009: 'no coal-fired stations demonstrating CCS at commercial scale' (p46→p20); 0403-0055: CCS doubles generation cost to ~$110/MWh (p20); 0403-0074: IEA called for 'immediate policy action' due to deployment risk (p25); 0403-0075: no specific financial incentives for operational CCS (p22); 0403-0010: government cut funding causing capability attrition (p34).

### EVT-0043 — evolve DER Project

**Verdict:** `partial_chain` · confidence: `medium` · chain length: 4 links

**Chain:**

- p27 -> p49
- p49 -> p10
- p01 -> p49
- p69 -> p01

**Evidence:** 0760-0001: 'without appropriate coordination' DER causes grid problems (p27→p49); 0760-0026: peak solar breaches limits when demand low (p49→p10); 0760-0039: limited network visibility requires state estimation (p01→p49); 0761-0026: static export limits curtail DER financially (p69→p01); 0760-0076: proprietary control systems (p40) partially orthogonal.

### EVT-0018 — Enel X Demand Response Project

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p23 -> p30
- p30 -> p18
- p18 -> p36
- p36 -> p22

**Evidence:** 0499-0040/0500-0046: NER 3.20.3(j) interpretation conflict (p23→p30); 0499-0037/0500-0043: RERT contract makes FCAS ineligible during ITT (p30→p18); 0499-0039/0503-0064: opportunity cost of foregone FCAS revenue (p18); 0499-0065/0500-0047: ITT process not decided until program start causing scoping failure (p36); 0504-0069: fragmented markets block value stacking (p22).

### EVT-0113 — G & K O'Connor - Closing the Loop on Red Meat Processing Energy and Emissions

**Verdict:** `single_root_with_multiple_consequences` · confidence: `high` · chain length: 4 links

**Chain:**

- p14 -> p36
- p14 -> p13
- p14 -> p01
- p14 -> p12

**Evidence:** ARENA-DLV-1211-0011 'plant of varying ages and standards of automation' (p14) is root; ARENA-DLV-1211-0012 'absence of site-wide communications network' (p32/p14); ARENA-DLV-1211-0013 'integrating metering data across different systems' (p13); ARENA-DLV-1211-0014 'absence of long-term plant data storage' (p01); ARENA-DLV-1211-0016 'meters read manually' (p12). Legacy infrastructure drives all sub-problems.

### EVT-0007 — AGL Electric Vehicle Orchestration Trial

**Verdict:** `causal_chain` · confidence: `high` · chain length: 4 links

**Chain:**

- p46 -> p41
- p41 -> p13
- p41 -> p24
- p24 -> p27

**Evidence:** ARENA-DLV-1101-0010 'V2G at very early stage of development' (p46); ARENA-DLV-1101-0032 'must comply with AS4777.2 different from global standards' (p41); ARENA-DLV-0215-0079 'could not support remote OCPP-based orchestration' (p13); ARENA-DLV-1102-0024 'timeframe for certification extended by many months' (p24); ARENA-DLV-1102-0015 'software development had not commenced due to delays' (p27).

### EVT-0021 — AGL Solar Project

**Verdict:** `single_root_with_multiple_consequences` · confidence: `high` · chain length: 4 links

**Chain:**

- p05 -> p41
- p05 -> p34
- p05 -> p12
- p05 -> p45

**Evidence:** ARENA-DLV-1062-0001 'Australia had minimal experience in utility-scale solar' (p05) is root; ARENA-DLV-0218-0061 'contractor unfamiliar with Australian regulatory framework' (p41); ARENA-DLV-1062-0006 'commissioning reliant on international capabilities' (p34); ARENA-DLV-1062-0014 'commissioning specialists sent from USA base' (p12); ARENA-DLV-1062-0004 'domestic supply chain insufficient' (p45).


## All diagnoses (compact)

| event | project | verdict | confidence | chain length |
|---|---|---|---|---:|
| EVT-0009 | Project SHIELD - Synchronising Heterogeneous Information to  | single_root_with_multiple_consequences | high | 0 |
| EVT-0037 | Lake Bonney Battery Energy Storage System | causal_chain | high | 8 |
| EVT-0074 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0062 | Project SHIELD - Synchronising Heterogeneous Information to  | causal_chain | high | 5 |
| EVT-0032 | George Weston Foods - Feasibility Study into Onsite Thermal  | single_root_with_multiple_consequences | medium | 0 |
| EVT-0005 | Impact and Management of Harmonic Distortion for Large Renew | single_root_with_multiple_consequences | medium | 0 |
| EVT-0004 | Musselroe Wind Farm FCAS Trial | causal_chain | high | 7 |
| EVT-0124 | Port Kembla Steelworks Renewables & Emissions Reduction Stud | single_root_with_multiple_consequences | high | 0 |
| EVT-0028 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | single_root_with_multiple_consequences | medium | 0 |
| EVT-0006 | United Energy Distribution Demand Response | causal_chain | high | 5 |
| EVT-0019 | Energy Storage for Commercial Renewable Integration (ESCRI)  | causal_chain | high | 4 |
| EVT-0008 | Lake Bonney Battery Energy Storage System | causal_chain | high | 5 |
| EVT-0030 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 0 |
| EVT-0023 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 0 |
| EVT-0003 | Aeolius Wind Forecasting Project | causal_chain | high | 4 |
| EVT-0008 | Neoen Victorian Big Battery (Moorabool) Retrofit | causal_chain | high | 3 |
| EVT-0007 | Neoen Victorian Big Battery (Moorabool) Retrofit | causal_chain | high | 4 |
| EVT-0006 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | partial_chain | medium | 4 |
| EVT-0099 | Australian Hydrogen Centre | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0029 | Testing the Performance of Lithium Ion Batteries | causal_chain | high | 4 |
| EVT-0117 | Port Kembla Steelworks Renewables & Emissions Reduction Stud | causal_chain | high | 4 |
| EVT-0020 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | partial_chain | medium | 4 |
| EVT-0030 | Horizon Power Business Model Pilot Phase 1 | causal_chain | high | 5 |
| EVT-0058 | Achieving Cost-Affective Abatement | causal_chain | medium | 4 |
| EVT-0043 | evolve DER Project | partial_chain | medium | 4 |
| EVT-0018 | Enel X Demand Response Project | causal_chain | high | 4 |
| EVT-0001 | Latrobe Valley Microgrid Feasibility Study | single_root_with_multiple_consequences | medium | 0 |
| EVT-0020 | NT Solar Energy Transformation Program | single_root_with_multiple_consequences | high | 0 |
| EVT-0056 | NT Solar Energy Transformation Program | single_root_with_multiple_consequences | high | 0 |
| EVT-0095 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | medium | 5 |
| EVT-0007 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | cluster_of_orthogonal_failures | high | 0 |
| EVT-0043 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 1 |
| EVT-0203 | Western Australia Distributed Energy Resources Orchestration | cluster_of_orthogonal_failures | high | 0 |
| EVT-0018 | Rottnest Island Water and Renewable Energy Nexus (WREN) Proj | causal_chain | medium | 3 |
| EVT-0014 | United Energy Low Voltage Battery Trial | causal_chain | high | 3 |
| EVT-0028 | My Energy Marketplace | single_root_with_multiple_consequences | high | 3 |
| EVT-0023 | Yuri Renewable Hydrogen to Ammonia Project | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0113 | G & K O'Connor - Closing the Loop on Red Meat Processing Ene | single_root_with_multiple_consequences | high | 4 |
| EVT-0095 | My Energy Marketplace | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0030 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | causal_chain | high | 3 |
| EVT-0007 | AGL Electric Vehicle Orchestration Trial | causal_chain | high | 4 |
| EVT-0006 | AGL Demand Response | partial_chain | medium | 3 |
| EVT-0021 | AGL Solar Project | single_root_with_multiple_consequences | high | 4 |
| EVT-0101 | Australian Hydrogen Centre | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0017 | Zen Ecosystems Demand Response | partial_chain | medium | 2 |
| EVT-0011 | Accelerating the Growth Development of Energy Monitoring | cluster_of_orthogonal_failures | high | 0 |
| EVT-0075 | Advancing Renewables with PCM Thermal Energy Storage | causal_chain | high | 3 |
| EVT-0005 | Application of Advanced Short Term Power Generation Forecast | causal_chain | high | 3 |
| EVT-0039 | Testing the Performance of Lithium Ion Batteries | single_root_with_multiple_consequences | high | 3 |
| EVT-0026 | Testing the Performance of Lithium Ion Batteries | causal_chain | medium | 3 |
| EVT-0017 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0050 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | single_root_with_multiple_consequences | high | 3 |
| EVT-0001 | Comparison of Dispatchable Renewable Electricity Options | cluster_of_orthogonal_failures | high | 0 |
| EVT-0011 | United Energy Distribution Demand Response | causal_chain | high | 3 |
| EVT-0029 | Energy Storage for Commercial Renewable Integration (ESCRI)  | causal_chain | high | 3 |
| EVT-0022 | Europcar Electric Vehicle Infrastructure Project | cluster_of_orthogonal_failures | high | 0 |
| EVT-0026 | Gridded Renewables Nowcasting Demonstration over South Austr | causal_chain | medium | 3 |
| EVT-0007 | Integrating Concentrating Solar Thermal Energy | single_root_with_multiple_consequences | medium | 3 |
| EVT-0092 | Kidston Pumped Hydro Energy Storage | partial_chain | medium | 3 |
| EVT-0142 | NT Solar Energy Transformation Program | causal_chain | high | 3 |
| EVT-0103 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | high | 2 |
| EVT-0053 | Project SHIELD - Synchronising Heterogeneous Information to  | single_root_with_multiple_consequences | high | 0 |
| EVT-0110 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0074 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0126 | Western Australia Distributed Energy Resources Orchestration | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0075 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 2 |
| EVT-0040 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 4 |
| EVT-0001 | Renewable Energy Hub Marketplace | causal_chain | high | 3 |
| EVT-0001 | Capacity Improvement and Flow Balancing of CST Heating/Cooli | causal_chain | high | 4 |
| EVT-0029 | Wind Forecasting Demonstration Project | single_root_with_multiple_consequences | high | 3 |
| EVT-0030 | My Energy Marketplace | causal_chain | high | 2 |
| EVT-0032 | My Energy Marketplace | partial_chain | medium | 3 |
| EVT-0005 | ANC - Last Mile Delivery EV | causal_chain | medium | 3 |
| EVT-0006 | ANC - Last Mile Delivery EV | single_root_with_multiple_consequences | high | 3 |
| EVT-0011 | ANC - Last Mile Delivery EV | partial_chain | medium | 2 |
| EVT-0005 | Improving World-Record Commercial High-Efficiency N-Type Sol | causal_chain | high | 3 |
| EVT-0018 | Simply Energy Virtual Power Plant (VPP) | partial_chain | high | 2 |
| EVT-0017 | UNSW Addressing Barriers to Efficient Renewable Integration | causal_chain | medium | 3 |
| EVT-0071 | Conversion of Coal to Hybrid Solar Thermal/Gas | single_root_with_multiple_consequences | high | 1 |
| EVT-0019 | Evie Networks Future Fuels Public Fast Charging | causal_chain | high | 3 |
| EVT-0010 | Neoen Big Battery (Blyth) Deployment Project | causal_chain | high | 3 |
| EVT-0009 | Neoen Victorian Big Battery (Moorabool) Retrofit | causal_chain | high | 3 |
| EVT-0010 | Neoen Victorian Big Battery (Moorabool) Retrofit | causal_chain | high | 3 |
| EVT-0001 | Sustainable transport in tourism | causal_chain | high | 4 |
| EVT-0019 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | partial_chain | medium | 3 |
| EVT-0015 | Fulcrum3D CloudCAM Solar Forecasting | causal_chain | medium | 2 |
| EVT-0008 | Hornsdale Power Reserve Upgrade | partial_chain | medium | 3 |
| EVT-0001 | NOJA Power Intelligent Switchgear | single_root_with_multiple_consequences | medium | 4 |
| EVT-0012 | NT Solar Energy Transformation Program | causal_chain | high | 3 |
| EVT-0029 | 5B Maverick Solar PV Automated Assembly & Deployment | cluster_of_orthogonal_failures | high | 0 |
| EVT-0062 | AEMO – CER Data Exchange Industry Co-Design | single_root_with_multiple_consequences | high | 0 |
| EVT-0063 | AEMO – CER Data Exchange Industry Co-Design | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0068 | AEMO – CER Data Exchange Industry Co-Design | partial_chain | medium | 2 |
| EVT-0068 | AEMO Virtual Power Plant Demonstrations | partial_chain | medium | 3 |
| EVT-0035 | AEMO Virtual Power Plant Demonstrations | causal_chain | high | 3 |
| EVT-0011 | AGL Solar Project | single_root_with_multiple_consequences | high | 0 |
| EVT-0137 | Australian Hydrogen Centre | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0053 | Achieving Cost-Affective Abatement | single_root_with_multiple_consequences | high | 0 |
| EVT-0054 | Advanced Planning of PV-Rich Distribution Networks Study | causal_chain | high | 3 |
| EVT-0010 | Advancing Renewables with PCM Thermal Energy Storage | causal_chain | medium | 3 |
| EVT-0040 | Alice Springs Future Grid Project | partial_chain | medium | 3 |
| EVT-0008 | Powerlink Cost-Effective System Strength Study | causal_chain | medium | 3 |
| EVT-0013 | Barcaldine Remote Community Solar Farm | causal_chain | high | 3 |
| EVT-0009 | Testing the Performance of Lithium Ion Batteries | single_root_with_multiple_consequences | high | 0 |
| EVT-0001 | Testing the Performance of Lithium Ion Batteries | partial_chain | medium | 2 |
| EVT-0034 | Battery of the Nation Future State NEM Analysis (Stage 2) | causal_chain | medium | 3 |
| EVT-0070 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | single_root_with_multiple_consequences | high | 0 |
| EVT-0043 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | partial_chain | medium | 2 |
| EVT-0052 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0038 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | causal_chain | medium | 3 |
| EVT-0091 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | partial_chain | medium | 2 |
| EVT-0007 | Chargefox Electric Vehicle Charging Network Project | causal_chain | high | 3 |
| EVT-0075 | Business Renewables Centre Australia | partial_chain | medium | 2 |
| EVT-0028 | DeGrussa Solar Project | causal_chain | high | 3 |
| EVT-0045 | EnergyAustralia Demand Response Program | partial_chain | medium | 2 |
| EVT-0119 | EnergyAustralia Demand Response Program | cluster_of_orthogonal_failures | high | 0 |
| EVT-0041 | Energy Storage for Commercial Renewable Integration (ESCRI)  | partial_chain | medium | 2 |
| EVT-0158 | Realising Electric Vehicle-to-Grid Services | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0049 | Enel X Demand Response Project | causal_chain | high | 3 |
| EVT-0041 | Enel X Demand Response Project | causal_chain | medium | 3 |
| EVT-0024 | TransGrid Wallgrove Battery | causal_chain | high | 3 |
| EVT-0008 | Flinders Island Hybrid Energy Hub | partial_chain | medium | 3 |
| EVT-0016 | Gannawarra Energy Storage System (GESS) | causal_chain | high | 3 |
| EVT-0068 | Hornsdale Power Reserve Upgrade | causal_chain | high | 4 |
| EVT-0009 | Impact and Management of Harmonic Distortion for Large Renew | causal_chain | high | 3 |
| EVT-0014 | Flow Power Energy Under Control Demand Response | single_root_with_multiple_consequences | high | 0 |
| EVT-0075 | Kidston Pumped Hydro Energy Storage | causal_chain | high | 4 |
| EVT-0042 | Lake Bonney Battery Energy Storage System | causal_chain | medium | 4 |
| EVT-0002 | Snowy 2.0 Feasibility Study | partial_chain | medium | 3 |
| EVT-0003 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | high | 3 |
| EVT-0032 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 4 |
| EVT-0046 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0062 | Western Australia Distributed Energy Resources Orchestration | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0054 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 0 |
| EVT-0039 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0051 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 4 |
| EVT-0106 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0058 | Western Australia Distributed Energy Resources Orchestration | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0071 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0113 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0027 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 4 |
| EVT-0198 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0118 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 4 |
| EVT-0025 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 0 |
| EVT-0035 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0417 | Realising Electric Vehicle-to-Grid Services | causal_chain | high | 4 |
| EVT-0021 | Relectrify Second-Life Battery Trial | causal_chain | high | 4 |
| EVT-0010 | Dynamic Limits DER Feasibility Study | causal_chain | high | 3 |
| EVT-0077 | Networks Renewed | cluster_of_orthogonal_failures | high | 0 |
| EVT-0060 | United Energy Low Voltage Battery Trial | cluster_of_orthogonal_failures | high | 0 |
| EVT-0051 | CSP Pilot Plant | causal_chain | high | 4 |
| EVT-0026 | AEMO Virtual Power Plant Demonstrations | single_root_with_multiple_consequences | medium | 2 |
| EVT-0029 | New Energies Service Station Geelong Demonstration Project | partial_chain | medium | 3 |
| EVT-0104 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 4 |
| EVT-0019 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0052 | Co-located Vanadium Flow Battery Storage and Solar | causal_chain | high | 3 |
| EVT-0026 | Co-located Vanadium Flow Battery Storage and Solar | causal_chain | high | 3 |
| EVT-0010 | Decentralised Energy Exchange (deX) Program | causal_chain | medium | 3 |
| EVT-0068 | AGL Broken Hill Grid-Forming Battery | causal_chain | high | 4 |
| EVT-0007 | ANC - Last Mile Delivery EV | single_root_with_multiple_consequences | medium | 2 |
| EVT-0034 | Advanced Energy Resources Wind, Solar and Battery Project | causal_chain | high | 4 |
| EVT-0033 | Brown Family Wine Group - Electrification and Thermal Energy | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0034 | Brown Family Wine Group - Electrification and Thermal Energy | single_root_with_multiple_consequences | high | 4 |
| EVT-0046 | Brimbank Aquatic and Wellness Centre Integrated Energy Syste | causal_chain | medium | 4 |
| EVT-0026 | Indra Monash Smart City | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0045 | Intellihub Demand Flexibility Platform Project | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0255 | Realising Electric Vehicle-to-Grid Services | causal_chain | high | 3 |
| EVT-0078 | SA Power Networks - Electrification and Demand Flexibility | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0054 | Simply Energy Virtual Power Plant (VPP) | partial_chain | medium | 2 |
| EVT-0001 | Zenobē - EV Delivery Truck Charging Facility | causal_chain | high | 4 |
| EVT-0022 | Gullen Solar Farm | causal_chain | high | 4 |
| EVT-0005 | SA Power Networks Market Active Solar Trial | causal_chain | high | 3 |
| EVT-0017 | Gridded Renewables Nowcasting Demonstration over South Austr | causal_chain | high | 3 |
| EVT-0067 | Lake Bonney Stages 2/3 | partial_chain | medium | 3 |
| EVT-0046 | Malabar Biomethane Injection Project | causal_chain | high | 3 |
| EVT-0008 | Neoen Big Battery (Blyth) Deployment Project | causal_chain | high | 3 |
| EVT-0005 | Neoen Victorian Big Battery (Moorabool) Retrofit | causal_chain | high | 3 |
| EVT-0010 | Origin Energy Mortlake Power Station Battery | causal_chain | high | 3 |
| EVT-0031 | PLUS ES South Australia Demand Flexibility Trial | partial_chain | medium | 3 |
| EVT-0024 | Rheem Active Hot Water Control | causal_chain | high | 3 |
| EVT-0025 | Yarwun Hydrogen Calcination Pilot Demonstration Program | causal_chain | high | 3 |
| EVT-0022 | 5B Maverick Solar PV Automated Assembly & Deployment | single_root_with_multiple_consequences | high | 0 |
| EVT-0032 | 5B Maverick Solar PV Automated Assembly & Deployment | partial_chain | medium | 2 |
| EVT-0066 | AEMO – CER Data Exchange Industry Co-Design | cluster_of_orthogonal_failures | high | 0 |
| EVT-0069 | AEMO – CER Data Exchange Industry Co-Design | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0169 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | single_root_with_multiple_consequences | medium | 0 |
| EVT-0001 | AEMO Connections Tool Project | causal_chain | high | 3 |
| EVT-0004 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | single_root_with_multiple_consequences | medium | 0 |
| EVT-0075 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | causal_chain | medium | 3 |
| EVT-0028 | Hornsdale Wind Farm Stage 2 FCAS Trial | causal_chain | high | 3 |
| EVT-0009 | AGL Electric Vehicle Orchestration Trial | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0021 | AGL Electric Vehicle Orchestration Trial | single_root_with_multiple_consequences | medium | 0 |
| EVT-0038 | AGL Demand Response | causal_chain | high | 3 |
| EVT-0039 | AGL Demand Response | causal_chain | high | 3 |
| EVT-0060 | AGL Demand Response | partial_chain | medium | 2 |
| EVT-0071 | AGL Demand Response | single_root_with_multiple_consequences | high | 0 |
| EVT-0005 | AGL Solar Project | single_root_with_multiple_consequences | medium | 0 |
| EVT-0059 | Atlas of Pumped Hydro Energy Storage | cluster_of_orthogonal_failures | high | 0 |
| EVT-0018 | APA Fortescue Solar Gas Hybrid Project | single_root_with_multiple_consequences | high | 0 |
| EVT-0005 | APA Fortescue Solar Gas Hybrid Project | causal_chain | medium | 2 |
| EVT-0009 | Zen Ecosystems Demand Response | causal_chain | high | 3 |
| EVT-0005 | Australian Energy Council Double-Sided Causer Pays Study | partial_chain | medium | 2 |
| EVT-0016 | Accelerating the Growth Development of Energy Monitoring | causal_chain | high | 3 |
| EVT-0014 | Advancing Marine Microalgae Biofuel to Commercialisation | single_root_with_multiple_consequences | medium | 0 |
| EVT-0006 | Advancing Renewables in the Manufacturing Sector | cluster_of_orthogonal_failures | high | 0 |
| EVT-0018 | Advancing Renewables in the Manufacturing Sector | causal_chain | high | 3 |
| EVT-0013 | Alcoa - Renewable Powered Electric Calcination Pilot | causal_chain | high | 3 |
| EVT-0015 | Alice Springs Future Grid Project | causal_chain | high | 2 |
| EVT-0110 | Alice Springs Future Grid Project | causal_chain | high | 2 |
| EVT-0018 | Solar and Storage Trial at Alkimos Beach Residential Develop | partial_chain | medium | 2 |
| EVT-0060 | Advanced VPP Grid Integration | causal_chain | medium | 3 |
| EVT-0025 | Ballarat Energy Storage System (BESS) | causal_chain | medium | 3 |
| EVT-0031 | Ballarat Energy Storage System (BESS) | causal_chain | high | 3 |
| EVT-0005 | Testing the Performance of Lithium Ion Batteries | single_root_with_multiple_consequences | high | 2 |
| EVT-0010 | Testing the Performance of Lithium Ion Batteries | causal_chain | medium | 2 |
| EVT-0024 | Testing the Performance of Lithium Ion Batteries | partial_chain | medium | 2 |
| EVT-0045 | Testing the Performance of Lithium Ion Batteries | cluster_of_orthogonal_failures | high | 0 |
| EVT-0020 | Tasmanian Pumped Hydro Energy Storage Opportunities Stage 2 | cluster_of_orthogonal_failures | high | 0 |
| EVT-0021 | Utilising Biogas in Sugarcane Transport and Milling | causal_chain | medium | 3 |
| EVT-0033 | Brighte - Electrify 2515 Community Pilot | single_root_with_multiple_consequences | high | 3 |
| EVT-0024 | Brimbank Aquatic and Wellness Centre Integrated Energy Syste | partial_chain | medium | 2 |
| EVT-0013 | Brimbank Aquatic and Wellness Centre Integrated Energy Syste | causal_chain | medium | 3 |
| EVT-0036 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | causal_chain | medium | 3 |
| EVT-0037 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | single_root_with_multiple_consequences | medium | 3 |
| EVT-0042 | Consumer Energy Systems Providing Cost-Effective Grid Suppor | causal_chain | medium | 3 |
| EVT-0168 | Achieving Cost-Affective Abatement | causal_chain | high | 3 |
| EVT-0010 | Horizon Power Business Model Pilot Phase 1 | causal_chain | high | 2 |
| EVT-0036 | Horizon Power Business Model Pilot Phase 1 | causal_chain | medium | 2 |
| EVT-0039 | Horizon Power Business Model Pilot Phase 1 | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0025 | Clean Energy Startup Support Programs | causal_chain | medium | 3 |
| EVT-0036 | Advanced Planning of PV-Rich Distribution Networks Study | single_root_with_multiple_consequences | high | 2 |
| EVT-0254 | Realising Electric Vehicle-to-Grid Services | causal_chain | high | 3 |
| EVT-0017 | DER 2.0: Customer Focused Design for DER Participation | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0014 | DeGrussa Solar Project | single_root_with_multiple_consequences | medium | 3 |
| EVT-0005 | United Energy Distribution Demand Response | causal_chain | medium | 3 |
| EVT-0003 | Development of Novel Hydrogen Trapping Techniques | causal_chain | high | 3 |
| EVT-0030 | Improving Efficiency, Durability & Cost-effectiveness of III | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0013 | Enel X Demand Response Project | causal_chain | medium | 3 |
| EVT-0037 | Enel X Demand Response Project | causal_chain | high | 2 |
| EVT-0002 | Energy Storage for Commercial Renewable Integration | causal_chain | high | 3 |
| EVT-0075 | TransGrid Wallgrove Battery | partial_chain | medium | 2 |
| EVT-0006 | Fortescue - low temperature direct electrochemical reduction | single_root_with_multiple_consequences | medium | 0 |
| EVT-0004 | Wind Forecasting for the NEM | causal_chain | high | 3 |
| EVT-0005 | Wind Forecasting for the NEM | causal_chain | high | 3 |
| EVT-0034 | Gannawarra Energy Storage System (GESS) | causal_chain | medium | 3 |
| EVT-0005 | Advancing Renewables with PCM Thermal Energy Storage | causal_chain | high | 3 |
| EVT-0014 | Advancing Renewables with PCM Thermal Energy Storage | causal_chain | high | 3 |
| EVT-0033 | Hornsdale Power Reserve Upgrade | causal_chain | high | 3 |
| EVT-0010 | Impact and Management of Harmonic Distortion for Large Renew | causal_chain | high | 3 |
| EVT-0002 | Impact and Management of Harmonic Distortion for Large Renew | causal_chain | high | 3 |
| EVT-0003 | Impact and Management of Harmonic Distortion for Large Renew | partial_chain | medium | 2 |
| EVT-0006 | Impact and Management of Harmonic Distortion for Large Renew | causal_chain | high | 3 |
| EVT-0015 | High Efficiency Silicon Solar Cell Technology | causal_chain | medium | 3 |
| EVT-0048 | Horizon Power Business Model Pilot Phase 1 | partial_chain | medium | 2 |
| EVT-0009 | Hybridisation of Concentrated Solar Thermal | causal_chain | medium | 3 |
| EVT-0035 | Testing the Performance of Lithium Ion Batteries | causal_chain | high | 3 |
| EVT-0013 | Increasing the Uptake of Solar PV in Strata Residential Deve | partial_chain | medium | 2 |
| EVT-0041 | Increasing the Uptake of Solar PV in Strata Residential Deve | causal_chain | medium | 3 |
| EVT-0047 | Increasing the Uptake of Solar PV in Strata Residential Deve | partial_chain | medium | 2 |
| EVT-0003 | Jemena Power to Gas Demonstration | causal_chain | high | 3 |
| EVT-0001 | Metro Advertising Revenue Funded Electric Vehicle Charging T | causal_chain | high | 3 |
| EVT-0022 | Flow Power Energy Under Control Demand Response | causal_chain | high | 2 |
| EVT-0024 | Flow Power Energy Under Control Demand Response | causal_chain | high | 3 |
| EVT-0025 | Flow Power Energy Under Control Demand Response | partial_chain | medium | 2 |
| EVT-0067 | Kennedy Energy Park | causal_chain | high | 3 |
| EVT-0025 | Lake Bonney Battery Energy Storage System | partial_chain | medium | 2 |
| EVT-0030 | Lake Bonney Battery Energy Storage System | causal_chain | high | 3 |
| EVT-0033 | Lake Bonney Battery Energy Storage System | causal_chain | high | 3 |
| EVT-0011 | Latrobe Valley Microgrid Feasibility Study | causal_chain | high | 3 |
| EVT-0103 | Mechanical Vapour Recompression for Low Carbon Alumina Refin | causal_chain | high | 3 |
| EVT-0523 | Realising Electric Vehicle-to-Grid Services | single_root_with_multiple_consequences | medium | 0 |
| EVT-0004 | Ararat Wind Farm | causal_chain | medium | 3 |
| EVT-0005 | Ararat Wind Farm | single_root_with_multiple_consequences | high | 0 |
| EVT-0008 | NSW Schools Energy Productivity Program (SEPP) Pilot | causal_chain | medium | 3 |
| EVT-0133 | NT Solar Energy Transformation Program | causal_chain | high | 3 |
| EVT-0144 | NT Solar Energy Transformation Program | causal_chain | high | 3 |
| EVT-0019 | NT Solar Energy Transformation Program | partial_chain | medium | 2 |
| EVT-0007 | Networks Renewed | causal_chain | medium | 3 |
| EVT-0076 | TransGrid New England Renewable Energy Zone | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0008 | Next Generation Electric Bus Depot | causal_chain | high | 2 |
| EVT-0008 | Normanton Solar Farm | single_root_with_multiple_consequences | high | 0 |
| EVT-0062 | Powerlink Cost-Effective System Strength Study | causal_chain | medium | 3 |
| EVT-0006 | AGL Virtual Trial of Peer-to-Peer Energy Trading | causal_chain | medium | 3 |
| EVT-0031 | Intermittent Dynamic Electrowinning Using Renewable Energy | partial_chain | medium | 2 |
| EVT-0012 | Pilot Landfill Solar Project | single_root_with_multiple_consequences | high | 0 |
| EVT-0018 | Pilot Landfill Solar Project | causal_chain | medium | 3 |
| EVT-0006 | Advanced Energy Resources Wind, Solar and Battery Project | partial_chain | medium | 2 |
| EVT-0011 | Advanced Energy Resources Wind, Solar and Battery Project | causal_chain | high | 3 |
| EVT-0053 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | medium | 3 |
| EVT-0101 | Project Converge ACT Distributed Energy Resources Demonstrat | partial_chain | medium | 3 |
| EVT-0110 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | high | 3 |
| EVT-0121 | Project Converge ACT Distributed Energy Resources Demonstrat | causal_chain | medium | 3 |
| EVT-0005 | Project Marinus: Further Bass Strait Interconnection | causal_chain | high | 3 |
| EVT-0067 | Project SHIELD - Synchronising Heterogeneous Information to  | single_root_with_multiple_consequences | medium | 0 |
| EVT-0069 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0295 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 3 |
| EVT-0048 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0034 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0066 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0100 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0102 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 2 |
| EVT-0018 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0041 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0056 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 2 |
| EVT-0111 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0125 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0052 | Western Australia Distributed Energy Resources Orchestration | causal_chain | medium | 3 |
| EVT-0080 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | high | 0 |
| EVT-0013 | RayGen Solar Power Plant Demonstration | single_root_with_multiple_consequences | medium | 0 |
| EVT-0012 | Dynamic Limits DER Feasibility Study | causal_chain | medium | 3 |
| EVT-0005 | Rottnest Island Water and Renewable Energy Nexus (WREN) Proj | causal_chain | high | 2 |
| EVT-0015 | Rottnest Island Water and Renewable Energy Nexus (WREN) Proj | cluster_of_orthogonal_failures | high | 0 |
| EVT-0053 | SA Power Networks Flexible Exports for Solar PV Trial | causal_chain | medium | 3 |
| EVT-0070 | SA Power Networks Flexible Exports for Solar PV Trial | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0029 | Social Access Solar Gardens | cluster_of_orthogonal_failures | high | 0 |
| EVT-0007 | Solar-Driven Supercritical CO2 Brayton Cycle | causal_chain | high | 3 |
| EVT-0005 | Solar Power Ensemble Forecaster | causal_chain | high | 3 |
| EVT-0042 | Commercialisation of SunDrive Copper Metallisation | causal_chain | high | 3 |
| EVT-0006 | Affordable Heating and Cooling Innovation Hub (iHub) | causal_chain | medium | 3 |
| EVT-0043 | TransGrid Wallgrove Battery | causal_chain | high | 3 |
| EVT-0013 | TransGrid Wallgrove Battery | causal_chain | high | 3 |
| EVT-0054 | Project MATCH | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0002 | United Energy Low Voltage Battery Trial | causal_chain | high | 3 |
| EVT-0003 | United Energy Distribution Demand Response | causal_chain | high | 3 |
| EVT-0022 | United Energy Low Voltage Battery Trial | causal_chain | high | 3 |
| EVT-0015 | CSP Pilot Plant | causal_chain | high | 3 |
| EVT-0064 | AEMO Virtual Power Plant Demonstrations | causal_chain | medium | 2 |
| EVT-0112 | AEMO Virtual Power Plant Demonstrations | cluster_of_orthogonal_failures | high | 0 |
| EVT-0046 | AGL Virtual Power Plant | causal_chain | high | 3 |
| EVT-0057 | My Energy Marketplace | causal_chain | medium | 3 |
| EVT-0105 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 2 |
| EVT-0081 | Western Australia Distributed Energy Resources Orchestration | single_root_with_multiple_consequences | medium | 0 |
| EVT-0015 | Western Australia Distributed Energy Resources Orchestration | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0065 | Western Australia Distributed Energy Resources Orchestration | partial_chain | medium | 2 |
| EVT-0008 | Western Australia Distributed Energy Resources Orchestration | causal_chain | high | 3 |
| EVT-0055 | Decentralised Energy Exchange (deX) Program | causal_chain | medium | 3 |
| EVT-0053 | AEMO Virtual Power Plant Demonstrations | causal_chain | medium | 3 |
| EVT-0071 | AGL Broken Hill Grid-Forming Battery | causal_chain | high | 3 |
| EVT-0002 | ANC - Last Mile Delivery EV | single_root_with_multiple_consequences | high | 2 |
| EVT-0008 | ANC - Last Mile Delivery EV | single_root_with_multiple_consequences | medium | 0 |
| EVT-0047 | Amber - Automating EV Charging in line with Wholesale Pricin | cluster_of_orthogonal_failures | high | 0 |
| EVT-0033 | Charge Together Phase 2 | causal_chain | medium | 3 |
| EVT-0065 | Brighte - Electrify 2515 Community Pilot | causal_chain | high | 3 |
| EVT-0064 | Horizon Power Business Model Pilot Phase 1 | causal_chain | medium | 3 |
| EVT-0015 | Ararat Wind Farm | causal_chain | high | 3 |
| EVT-0024 | Resilient Wind Energy for Telecommunication Sites | causal_chain | high | 3 |
| EVT-0023 | Enel X Commercial Refrigeration Flexible Demand Project | causal_chain | medium | 3 |
| EVT-0016 | Enel X Commercial Refrigeration Flexible Demand Project | causal_chain | high | 3 |
| EVT-0103 | SA Power Networks Flexible Exports for Solar PV Trial | causal_chain | high | 3 |
| EVT-0032 | Frasers Property Net Zero Energy Demand Homes | single_root_with_multiple_consequences | medium | 2 |
| EVT-0046 | Gridded Renewables Nowcasting Demonstration over South Austr | causal_chain | medium | 3 |
| EVT-0032 | The Hazer Process: Commercial Demonstration Plant | causal_chain | high | 3 |
| EVT-0008 | High-Temperature Solar Thermal Energy Storage | single_root_with_multiple_consequences | medium | 2 |
| EVT-0005 | Indra Monash Smart City | single_root_with_multiple_consequences | high | 3 |
| EVT-0005 | Model for Community-Owned Solar | causal_chain | high | 3 |
| EVT-0029 | Musselroe Wind Farm FCAS Trial | causal_chain | high | 3 |
| EVT-0142 | AEMO - Project EDGE (Energy Demand and Generation Exchange) | cluster_of_orthogonal_failures | medium | 0 |
| EVT-0011 | Project Fulfil | causal_chain | high | 3 |
| EVT-0058 | APA Fortescue Solar Gas Hybrid Project | causal_chain | high | 3 |
| EVT-0072 | SA Power Networks - Electrification and Demand Flexibility | causal_chain | high | 3 |
| EVT-0070 | Simply Energy Virtual Power Plant (VPP) | single_root_with_multiple_consequences | medium | 0 |
| EVT-0104 | evolve DER Project | causal_chain | high | 3 |
| EVT-0005 | Wyndham City Council – Local Council BEV Integration Project | single_root_with_multiple_consequences | high | 0 |
| EVT-0001 | UNSW Addressing Barriers to Efficient Renewable Integration | causal_chain | high | 2 |
| EVT-0002 | Gullen Solar Farm | causal_chain | high | 3 |
| EVT-0003 | Gullen Solar Farm | causal_chain | high | 2 |
| EVT-0083 | Conversion of Coal to Hybrid Solar Thermal/Gas | partial_chain | medium | 2 |