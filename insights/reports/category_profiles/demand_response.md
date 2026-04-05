---
category: "Demand response"
date_generated: 2024-12-19
record_count: 1401
project_count: 110
---

# Demand response — Delivery Risk Profile

## Executive Summary

Demand response projects face a fundamentally different risk profile than traditional energy infrastructure: their success hinges not on engineering execution but on navigating fragmented regulatory frameworks, misaligned commercial incentives, and coordinating multiple stakeholders who weren't designed to work together. The evidence from 110 projects shows that while the technology largely works, the institutional infrastructure to deploy it at scale does not exist.

Three systemic barriers dominate: regulatory frameworks designed for centralised generation that actively exclude or disadvantage demand response; baseline measurement methodologies that structurally exclude 80-95% of potential participants; and revenue uncertainty so severe that one customer stated they "did not want to have to depend on a grid emergency" to earn money. These aren't implementation details—they're fundamental design flaws in how demand response interfaces with Australia's energy markets.

Unlike solar or batteries where the main risks are cost and performance, demand response projects consistently fail on commercial viability and regulatory compliance. Even technically successful demonstrations struggle to find sustainable business models, and many promising pilots collapse when transitioning from trial to commercial operation.

## The Evidence Base

This profile draws on 1,401 records across 110 projects spanning 2012-2024, with particularly strong representation from recent large-scale trials. Coverage includes residential (hot water, air conditioning, EVs), commercial & industrial (flexible loads, backup generation), and whole-system integration platforms. 119 records (8.5%) carry temporal warnings for pre-2021 cost or technology findings.

The dataset provides exceptional depth on regulatory barriers and commercial model failures—areas where institutional knowledge from multiple project post-mortems creates rare insight. Coverage is weaker on successful scale-up pathways, reflecting the reality that few demand response projects have achieved commercial sustainability beyond pilot stage.

## Where Things Go Wrong

### Regulatory & Approvals (Critical Risk)

Regulatory barriers are the primary project killer, affecting 9% of all adverse records but with 42% escalating to major or critical severity—the highest escalation rate of any failure mode. The problem isn't slow approvals; it's that the regulatory framework was built for a different energy system.

AEMO's baseline methodologies represent the clearest example. "AGL's experience in the RERT program demonstrated that the AEMO baseline works well for flat and/or highly predictable loads, but discounts DR from temperature sensitive loads and intermittent or fluctuating loads." Multiple providers reported "filtering out prospective customers they expected to fail the baseline test before attempting registration." This isn't a design refinement issue—it's a fundamental mismatch that excludes 80-95% of C&I loads from the Wholesale Demand Response mechanism.

The AS/NZS 4777 standard creates a parallel blocking effect for EV bidirectional charging: "The technical standard classes bidirectional EV chargers as a multiple model inverter as if it was connected to a stationary battery energy storage system. The standard requires that a battery is connected to an earthing point but with EVs, there is no need for one." This forced the REVS pilot to modify charger hardware, which then failed electromagnetic compatibility tests, ultimately causing AGL to abandon the V2G component entirely.

Even where standards exist, they often aren't mandatory. "AS/NZS 4755 is not mandatory for new storage water heaters" and many air-conditioning units "were not compliant with the AS-4755 technical standard and could not be remotely controlled," leading AGL to conclude air-conditioning demand response was "currently unviable."

### Commercial & Market (Critical Risk)

Commercial failures occur in 26% of adverse records, making this the most frequent failure mode. The core issue is revenue uncertainty coupled with high customer acquisition costs. "One of the strongest themes across the ARENA-funded projects reviewed in this study was the difficulty making the necessary business case when the valuation of demand flexibility across the different energy services remains uncertain."

Customer acquisition consistently emerged as the major cost centre. "Lengthy, expensive customer acquisition processes were identified as a recurring theme through almost most C&I, EV and residential projects reviewed in this study. There were common reports of long lead times, multiple site visits and bespoke negotiations."

The Demand Management Incentive Scheme illustrates how even well-funded mechanisms fail to drive participation. Despite "$1 billion of available investment," only "$3 million of projects were funded between 2017 and 2022—less than 0.3% of available funds utilised." The money exists; the commercial framework to access it doesn't.

Value stacking—combining multiple revenue streams to justify participation costs—proves largely illusory. "Combining RERT with network revenue streams is considered 'double-dipping'" and "there are barriers to combining more than two value streams." Projects consistently found they could access one significant revenue stream, which was insufficient to cover fixed costs.

### Coordination & Stakeholders (Major Risk)

Stakeholder coordination failures affect 18% of adverse records, with the challenge intensifying as project complexity increases. The Energy Masters pilot—involving seven partners across retailers, networks, appliance providers, and installers—found "the volume of project management in the early stages can easily be under-estimated or under-invested in but it is a key part of establishing complex, multi-partner projects."

The fragmented nature of energy market institutions creates structural coordination problems. "Each retailer must negotiate separately with every network, resulting in a complex and time-consuming process" for hot water load control. "Every DNSP region is different and no clear pathway to rollout capability" exists for demand management.

Professional capability gaps compound coordination challenges. "Many installers are unfamiliar with HEMS and have required close guidance to set them up in a way that takes advantage of their functionality." The Electrify 2515 pilot found "Few plumbers install heat pumps. Solar installers and electricians are diversifying" but "Professional education and training is needed to increase the number of tradies offering and promoting electrification services."

### Data & Measurement (Major Risk)

Measurement challenges affect 19% of adverse records and create cascading problems for commercial viability. The core issue is that demand response measurement is fundamentally harder than generation measurement. "AGL found in follow-up surveys that 25 per cent of household results were 'false negatives' (i.e. the household had taken action but no change was recorded) and 41 per cent of household results were 'false positives'."

Smart meter coverage outside Victoria creates a structural data barrier. "Outside of Victoria the coverage of smart meters is only around 30 per cent" and quality is poor—described by AGL as "anything but smart by 2021 standards" due to once-daily data collection.

Data access rights create additional friction. "Demand Response Service Providers' (DRSP) ability to access meter data can present challenges impacting the ability to acquire new customers." For research partnerships, even "anonymised data transfers between industry and university partners can require lengthy security assessments."

## Failure Mode Deep-Dives

### Commercial Model Collapse

The Pooled Energy case study illustrates how retail market exposure creates existential risk for demand response aggregators. Despite successfully orchestrating "2,062 pool pump systems for wholesale arbitrage and FCAS events," Pooled Energy "went bankrupt in 2022 alongside other small retailers during wholesale market turbulence." The technical model worked perfectly; the commercial structure was fatally flawed.

This pattern repeats across project types. The Rheem hot water pilot required "participants to switch retailers and sign up to a cost-reflective time-of-use tariff; since the tariff applied to all consumption (not just hot water), customers could not be guaranteed they would benefit financially and were reluctant to enrol." When customers can't be guaranteed savings, participation collapses.

State incentive schemes create additional commercial distortions. "Incentives for energy-efficient heat pump systems that are not available to the less-efficient but more flexible electric resistance heaters with demand response capacity have also undermined their capacity to recruit customers by dramatically altering the relative costs."

### Technology Integration Fragmentation

The absence of interoperability standards creates a many-to-many integration problem that scales poorly. "The HEMS development has required time-consuming, complex and bespoke integrations with each CER brand and model. The market fragmentation created by the absence of common technical standards across the HEMS market adds significant investment costs and slows product development."

Even where standards exist, implementation varies. "Despite CSIP-AUS being developed as a common standard for CER device integration, inconsistent implementation across OEMs meant that uniform equipment behaviour was not achieved—some OEMs only partially implemented the standard and relied on the deX platform to fill compliance gaps."

Device conflicts are common. In the Rheem pilot, "Competing claims on surplus rooftop solar between the Rheem smart hot water system and behind-the-meter batteries with proprietary controls caused devices to 'fight each other'—the battery would absorb surplus solar that could otherwise have supported an FCAS event."

### Regulatory Lock-Out Mechanisms

Multiple regulatory frameworks combine to create systematic exclusions. FCAS participation "requires metering capable of recording frequency response at 50 millisecond intervals; across the EV trials, only one commercially available 3-phase power meter was found capable of this response speed." The measurement requirement is a de facto exclusion mechanism.

For C&I customers, baseline methodologies create catch-22 situations. "Customers already on 'critical peak' network tariffs with Ausnet (Victoria) did not participate in RERT because they would face financial penalties even if they missed just 1 or 2 events." Customers who respond to one price signal become ineligible for another revenue stream.

Geographic exclusions compound the problem. "As one of 5 DNSPs in Victoria, Ausnet found it very hard to connect effectively with installers as part of a relatively small-scale trial" compared to jurisdictions with single DNSPs where network-wide programs are viable.

## What Has Changed Over Time

The risk profile has shifted substantially since early projects. Pre-2018 trials faced basic technology readiness issues; current projects deal with institutional barriers. "The end-to-end technical capacity and understanding of VPPs was insufficient at the start of the project" in 2018's Project Symphony, but by 2024 the Intellihub platform achieved "376MW+ of aggregated load across 110,000+ CER devices."

Regulatory responses have been mixed. South Australia has led with "regulations now require all new or upgraded systems to be capable of participating in flexible exports," while other jurisdictions lag. The CSIP-AUS standard emerged from trials and is now "supporting flexible export rollouts across three states."

The COVID-19 period created supply chain vulnerabilities that persist. "The global shortage of semiconductors chips resulted in significant increases in lead times (54 weeks in some cases, compared to around 18 weeks typically)" and chip costs increased 10-20%. Projects now build supply chain risk as a core consideration.

Recent trials show scale-up success in narrow domains. The PLUS ES trial achieved "smart meter-based DEWH load control at scale across 18,843 households with a 96%+ API load control success rate" with "negligible customer complaints, a 0.3% opt-out rate." This proves that residential hot water orchestration can work at scale within existing infrastructure.

## Due Diligence Checklist

**Regulatory Environment Assessment:**
- Confirm AEMO baseline methodology compatibility for target load profile. If load is temperature-sensitive, variable, or intermittent, expect 80-95% baseline failure rates unless deeming is used.
- For EV V2G projects, verify AS/NZS 4777 compliance pathway exists before hardware procurement. If not available, budget for standards modification advocacy or accept unidirectional charging only.
- Map all applicable state demand response certificate schemes (PDRS, REPS equivalents) and verify eligibility criteria. Exclude or flag schemes that don't recognise flexible demand technologies.

**Revenue Model Validation:**
- Identify maximum two viable revenue streams and build business case around these only. If business case requires value stacking across 3+ streams, restructure or abandon.
- For programs requiring customer tariff switching, conduct shadow pricing first. If customers can't be guaranteed savings, expect 70-80% recruitment failure.
- Map customer acquisition costs against lifetime value. If acquisition exceeds first-year revenue, restructure incentives or target different customer segments.

**Stakeholder Coordination Planning:**
- If project involves 4+ organisations, establish dedicated full-time project management resource and formal decision-making authority structure. Informal coordination will fail.
- For multi-retailer programs, resolve control hierarchy and data sharing protocols before technical development begins. Competing commercial interests require explicit arbitration.
- Audit installer capability for non-standard technology (HEMS, heat pumps). If <50% have relevant experience, plan training programs or restrict technology scope.

**Technology Integration Readiness:**
- For multi-device HEMS programs, list specific OEM compatibility requirements and confirm API access. If any high-market-share OEM restricts access, adjust recruitment targets accordingly.
- Test device interoperability in lab before field deployment. If devices from different OEMs "fight each other," implement master control hierarchy or exclude incompatible combinations.
- For smart meter programs outside Victoria, confirm meter coverage >80% in target geography or plan for meter upgrade costs at $500-1000 per site.

**Market Structure Dependencies:**
- Confirm data access rights with relevant DNSP and metering coordinator before recruitment begins. If access is restricted or requires customer consent, adjust participation assumptions.
- For trials requiring network tariff approvals, initiate AER processes 6+ months before planned launch. If new tariffs needed, expect 4-12 month regulatory delays minimum.
- Map supply chain for critical components, especially semiconductors. If lead times >26 weeks or single-source dependencies exist, secure inventory upfront or qualify alternatives.