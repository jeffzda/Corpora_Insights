---
**category:** battery storage  
**date_generated:** 2025-01-27  
**record_count:** 2,597  
**project_count:** 54  
---

# Battery storage — Delivery Risk Profile

## Executive Summary

Battery storage projects face significant technical and regulatory complexity, with grid-forming (GFM) technology introducing new integration challenges that can extend connection timelines by 3+ months. Technical underperformance (18% of adverse records) and regulatory navigation (16%) dominate the risk landscape, while multi-vendor control system integration creates recurring commissioning failures. Project managers should expect iterative tuning processes, anticipate OEM documentation gaps, and budget conservatively for grid connection durations — particularly for first-of-type GFM deployments that lack established precedent with network operators.

## Coverage and Data Quality

This profile draws on 2,597 adverse delivery records across 54 battery storage projects spanning 2012–2024. The portfolio encompasses grid-scale systems (100 MW+), community batteries (100 kW–5 MW), and hybrid solar-battery configurations. Recent records (2022+, 34% of data) reflect current market conditions including GFM technology deployment and updated NER requirements. Only 8.4% of records carry temporal warnings for outdated technology or market conditions. The dataset provides strong coverage of grid connection, software integration, and operational challenges, with moderate coverage of community engagement and financing dimensions.

## Risk Landscape by Delivery Dimension

**Grid connection (701 records, 27% of portfolio)** emerges as the highest-risk dimension, driven by regulatory complexity (32% of issues) and commercial impacts (19%). GFM battery projects routinely face 20-month grid connection timelines versus 17 months for grid-following equivalents. The NER Generator Performance Standards, designed for synchronous machines, create compliance conflicts for GFM inverters where reactive current settling requirements directly contradict grid-forming control behaviour. Recent projects show regulatory uncertainty cascading into commercial risk when system strength charges ($2-3M annually) drive technology selection decisions.

**Software & controls (593 records, 23% of portfolio)** represents a critical integration bottleneck. Unvalidated integration failures (25% of issues) dominate, particularly around Power Plant Controller (PPC) compatibility with GFM inverters where third-party PPCs cannot provide required Vref signals. Battery Management System (BMS) issues plague early production units, and communications protocol customisation (IEEE 2030.5) can consume multiple years when advanced DNSP control requirements exceed off-the-shelf capabilities.

**Design (732 records, 28% of portfolio)** shows technical underperformance as the primary failure mode (31%), concentrated in inverter oversizing requirements for GFM operations (limiting to 86% of rated capacity), harmonic filter needs discovered late in GPS modelling, and Asset Protection Zone miscalculations forcing layout redesigns. Regulatory requirements (18%) compound design risk through evolving standards like SSIAG v2.2 updates during active connection processes.

**Procurement (618 records, 24% of portfolio)** demonstrates execution risk (26%) from international equipment vendors failing Australian standards compliance (ASME, AS3000, EEHA) and coordination failures (19%) between multiple OEMs. Battery commodity price volatility caused late-stage increases of 40%+ in some projects when lithium carbonate prices spiked from 150,000 to 400,000+ Chinese yuan.

**Operations (493 records, 19% of portfolio)** shows technical underperformance (37%) from manufacturing defects in early battery production batches that can derate systems by 50%+ and commercial risk (20%) from unexpected outage patterns driven by network operator maintenance windows.

## Failure Mode Deep-Dive

**Technical underperformance (18% occurrence, 30% severity escalation)** manifests most critically in multi-vendor control system incompatibilities. At Blyth BESS, the third-party PPC could not interface with GFM inverters, requiring costly hardware and firmware updates. Manufacturing quality emerges as a persistent risk: Yadlamalka's Invinity modules suffered electrolyte imbalances affecting 13 units, reducing available discharge power from 2.3 MW to 1.0 MW over 10 weeks. GFM inverter tuning creates fundamental trade-offs where optimising inertial response degrades fault-clearance damping, requiring iterative negotiation with AEMO and NSPs.

**Regulatory & approvals (16% occurrence, 30% severity escalation)** reflects the regulatory framework's poor alignment with battery technology. GPS clause S5.2.5.5 demands simultaneous high reactive current injection and rapid active power recovery — requirements that are dynamically coupled in GFM controls and cannot be optimised independently. The Liddell BESS required extensive negotiation because standard Automatic Access Standards create conflicting requirements for VSM-based inverters. Mid-process regulatory changes compound risk: SSIAG v2.2 release during active applications forces rework, while technical note updates occur without prominent circulation.

**Coordination & stakeholders (16% occurrence, 15% severity escalation)** centers on information gaps between project parties. OEM technical documentation often proves insufficient for GPS modelling, forcing trial-and-error approaches that extend connection timelines significantly. At Mortlake BESS, inadequate OEM technical memoranda caused incorrect modelling assumptions and GPS rework. Multi-OEM arrangements create coordination overhead where commercially sensitive information sharing between inverter and PPC vendors impedes rapid problem resolution.

**Commercial & market (16% occurrence, 23% severity escalation)** demonstrates two distinct patterns. Early projects (pre-2020) faced immature cost curves and FCAS market evolution that collapsed revenue streams. Recent projects encounter commodity price volatility and system strength charge structures that can render projects uneconomic overnight. The Electric Avenue trial saw FCAS market changes eliminate a key revenue stream during the project timeline, forcing early closure before full commercial operation.

## Temporal Trends

The risk profile has shifted markedly across the dataset timeline. Early projects (2012-2018) faced technology immaturity and market development challenges, with cost uncertainties and evolving FCAS frameworks. The 2019-2021 period shows regulatory standardisation reducing some risks while GFM technology introduction created new complexity around GPS compliance and control system integration.

Recent projects (2022+) face a mature but rapidly evolving landscape where regulatory frameworks lag technology capability. GFM deployment has accelerated dramatically, but each project encounters bespoke GPS negotiation because no standardised assessment methodology exists. System strength requirements have shifted from optional optimisation to mandatory connection prerequisite in low-SCR areas, fundamentally altering project economics.

Manufacturing quality has improved but remains variable, particularly for early production batches. Flow battery and second-life battery technologies show persistent commercial challenges despite technical progress, with logistics costs and supply chain constraints offsetting theoretical cost advantages.

## Key Watchpoints for Due Diligence

1. **Grid connection pathway clarity**: For GFM projects, verify NSP and AEMO assessment team experience with grid-forming technology. Budget 20-month timelines and confirm calculation methodologies for reactive current compliance upfront to avoid mid-process disputes.

2. **Multi-vendor integration risk**: Scrutinise PPC-inverter compatibility for GFM applications. Require OEMs to provide detailed control interface documentation and consider single-vendor solutions for critical control paths to avoid Blyth BESS-style integration failures.

3. **Manufacturing batch validation**: For new battery technologies or early production runs, require OEM quality certification at cell-stack level and maintain 10% spare inventory for rapid replacement. Manufacturing defects can cause 50%+ capacity derating and multi-month outages.

4. **Regulatory framework alignment**: Map current NER requirements against proposed technology configuration early. Legacy GPS frameworks create compliance conflicts for GFM systems that require regulatory negotiation, not technical fixes.

5. **Commodity price protection**: Implement price hedging or indexation mechanisms for battery supply contracts. Lithium price volatility created 40%+ cost increases on projects with unprotected supply agreements.

6. **System strength economics**: For projects in low-SCR areas, assess whether GFM capability is mandatory for connection approval rather than optional for charge avoidance. The connection access regime is shifting toward requiring grid-forming capability for any connection approval.

7. **Communications integration scope**: For community-scale batteries requiring DNSP integration, treat SCADA and telemetry integration as a major workstream requiring bespoke protocol configuration. Integration costs can reach hundreds of thousands of dollars and delay commissioning if underestimated.