---
**Metadata**
- Category: Off grid
- Date Generated: 2024-12-19
- Record Count: 386
- Project Count: 13
- Temporal Coverage: 2012-2024
- Records with Temporal Warnings: 12 (3.1%)

---

# Off grid — Delivery Risk Profile

## Executive Summary

Off-grid renewable energy projects face a distinctive risk landscape dominated by technical underperformance (25% of adverse records) and execution challenges (23% of records) that compound in remote environments. Lightning-related failures plague solar systems in the Northern Territory, while diesel generator integration constraints systematically limit renewable energy fractions below design targets. The combination of extreme remoteness, inadequate surge protection, and mismatched diesel fleet sizing creates a perfect storm where mobilisation costs for fault rectification can exceed daily solar savings by 20:1, making some failures economically prohibitive to fix promptly.

## Coverage and Data Quality

This profile draws on 386 records spanning 13 projects from 2012–2024, with strong coverage of Australia's largest off-grid solar program (SETuP) and the first major mine-scale hybrid microgrid (Agnew). Recent data (2022-2024) represents 68 records across 2 projects, providing current insights into mature technology deployment. Only 12 records (3.1%) carry temporal warnings about pre-2021 cost or capability data that may no longer reflect current conditions.

The dataset provides exceptional granularity on remote community solar-diesel hybrids and mining microgrids, with detailed failure mode attribution across the delivery spectrum. However, limited representation of other off-grid contexts (island systems, industrial processes) means findings may not generalise beyond these two dominant use cases.

## Risk Landscape by Delivery Dimension

**Design emerges as the highest-risk dimension** with 138 adverse records, driven primarily by technical underperformance (44% of design issues). Array sizing mismatched to diesel minimum loads, inadequate lightning protection design, and failure to account for curtailment in feasibility modelling systematically undermine project outcomes. Recent examples include the Agnew project's gas pipeline infrastructure creating a renewable fraction ceiling, and SETuP sites achieving only 20% of modelled yield due to stale estimates.

**Operations represents the second-highest risk** (92 records), where technical underperformance dominates (41% of operational issues). Lightning surge damage, cluster controller failures, and data quality problems create persistent yield losses. At SETuP sites, cluster controller failures alone accounted for 46% of all inverter downtime in 2020-21, while lightning damage drove PV unavailability from 1.6% to 15.3% in a single period.

**Siting risks** (88 records) are execution-heavy (50% of siting issues), driven by remote access challenges, contamination discoveries, and land acquisition delays averaging 18 months. The SETuP program's reduction from 34 to 24 communities exemplifies how siting constraints can force major scope reductions mid-delivery.

**Procurement challenges** (81 records) split between execution issues (38%) and technical underperformance (26%), reflecting the scarcity of suppliers experienced with remote hybrid systems and specialised equipment like wind farm cranes, which require 50+ truck loads to mobilise.

**Software & controls** (56 records) shows concerning failure patterns across data measurement (41%), technical underperformance (25%), and unvalidated integration (18%), indicating that control system complexity in multi-source hybrid systems frequently exceeds delivery team capabilities.

## Failure Mode Deep-Dive

**Technical Underperformance (25% of records, 28% severity escalation)** manifests distinctively in off-grid contexts. Lightning damage creates cascading failures across communication networks — a single storm at Daly River caused 29 of 40 inverters to require replacement despite extensive protection design. Diesel generator minimum load constraints systematically curtail solar output, with some sites experiencing 45-79% curtailment. The Titjikala array achieved only 15% of potential yield because 10 of 16 inverters were disabled to prevent reverse-powering. These aren't random failures but predictable design shortfalls that compound in remote environments where rectification is expensive and slow.

**Execution & Logistics (23% of records, 17% severity escalation)** represents the unique challenge of off-grid delivery. Remote communities require charter flights costing $4,000+ for day trips, while road access may be impossible during wet season. Material delivery by barge costs substantially more than road transport. Site contamination (asbestos at Umbakumba) or unsuitable land conditions force mid-program relocations. Even locally experienced contractors underestimate these challenges. Recent examples include COVID-19 halting university-based R&D for 3-4 months, and specialised wind farm crane mobilisation requiring 50+ truck loads.

**Data & Measurement (20% of records, 6% severity escalation)** failures often prove more damaging than their mild severity suggests. Arrays relocated mid-program retain stale modelling estimates, creating false performance benchmarks. Manual weekly fuel readings prevent granular diesel savings analysis. Weather stations aren't commissioned into data historians, undermining performance attribution. The Bulman array achieved only 20% of modelled output, but without updated modelling, operators couldn't distinguish stale estimates from genuine underperformance.

**Commercial & Market (12% of records, 36% severity escalation)** risks reflect the structural mismatch between finite mine life and 25-year renewable asset life, plus the requirement for grant funding to achieve cost-competitive outcomes. The Agnew project required ARENA funding to reach break-even, while Element 25 abruptly halted electrowinning R&D when pivoting to concentrate production during Phase 3.

## Temporal Trends

The risk profile shows three distinct evolution phases. **Early projects (2016-2018)** focused on proving basic solar-diesel integration but encountered fundamental design gaps around lightning protection and diesel fleet compatibility. The original SETuP design didn't account for planned/unplanned downtime, systematically overstating achievable renewable energy fractions.

**The maturation phase (2019-2021)** saw systematic learning application. SETuP array availability improved from 12.3% unavailability in 2018/19 to 3.4% in 2019/20 through targeted interventions. Control system retrofits and diesel minimum load optimisation delivered measurable yield improvements. However, new risks emerged around BESS integration — ferroresonance, protection scheme complexity, and fire safety compliance in remote locations.

**Recent projects (2022-2024)** demonstrate mature technology deployment but persistent systemic challenges. While the Agnew mine hybrid achieved its 54% renewable fraction target on time and budget, design decisions around gas infrastructure created a renewable ceiling that couldn't be economically overcome post-construction. Lightning protection remains an unresolved challenge despite years of experience — Daly River's PV unavailability jumped to 15.3% from lightning in 2020-21, and cluster controller obsolescence created fleet-wide vulnerability.

Failure modes around governance, coordination, and stakeholder management show remarkable time-stability. Land acquisition still averages 18 months, ARENA funding approval timing still disrupts financial close, and remote mobilisation costs still make minor repairs economically prohibitive.

## Key Watchpoints for Due Diligence

1. **Lightning protection depth and testing**: Verify that surge protection covers all communications pathways, not just power circuits. Require evidence of commissioning-phase lightning simulation testing under site-specific conditions. Ask for spare component inventories and replacement protocols. Recent SETuP data shows lightning can drive array unavailability above 15% despite "adequate" protection.

2. **Diesel fleet integration analysis**: Demand detailed curtailment modelling against actual minimum load settings for existing generators. Question any REF targets above 15-20% without accompanying battery storage or low-load generator upgrades. The relationship between array size and diesel fleet compatibility determines project viability more than solar resource quality.

3. **Remote operations economic model**: Scrutinise the cost-benefit calculation for fault response mobilisation. With charter flights costing $4,000+ and daily solar savings often under $200, many faults become economically rational to defer. Verify that component reliability assumptions and local operator training plans can minimise specialist mobilisation frequency.

4. **Control system obsolescence pathway**: For cluster controllers, protection relays, and other critical components, verify manufacturer support roadmaps and spare part availability over the 20-year asset life. Recent SETuP experience shows obsolete controllers becoming the largest single cause of downtime (46% of inverter-days lost) with no viable commercial replacement.

5. **Battery integration complexity**: If BESS is included, demand evidence of ferroresonance testing, adaptive protection scheme validation, and AS1851 fire system compliance costs for the specific site. Verify that Factory Acceptance Testing replicates worst-case site ambient conditions — Germany-based thermal testing may not validate performance in Northern Australian conditions.

6. **Land tenure and contamination risk**: For community or mining sites, verify that land acquisition/lease processes are complete before finalising array sizing. Recent programs show contamination discovery (asbestos, buried waste) and land acquisition delays (18-month average) routinely force site changes and capacity redistributions that undermine performance targets.

7. **Performance monitoring and commercial framework**: Examine whether monitoring systems can distinguish between curtailment, soiling, and genuine underperformance. Single-irradiance monitoring cannot perfectly model solar output, creating commercial risk under performance-based contracts. Verify that remodelling will occur if arrays are relocated or resized during delivery.