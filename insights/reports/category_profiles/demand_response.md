---
**Category:** Demand response  
**Date Generated:** 2024-12-19  
**Record Count:** 1,401  
**Project Count:** 110  

# Demand Response — Delivery Risk Profile

## Executive Summary

Demand response projects face structural barriers that prevent scaling beyond pilot stage. Regulatory frameworks designed before widespread CER adoption systematically exclude most loads, with the Wholesale Demand Response Mechanism achieving only 0.2% of peak demand participation despite four years of operation. Technical interoperability remains fragmented, requiring bespoke OEM integrations that drive up costs and prevent standardisation. Most critically, the controlled load fleet — the primary addressable resource for hot water flexibility — is declining by 25% due to household defection, creating a shrinking asset base that undermines long-term flexibility potential.

## Coverage and Data Quality

This profile draws from 1,401 records across 110 projects spanning 2012–2024, with the heaviest concentration in 2019–2021 (694 records). Only 119 records (8.5%) carry temporal warnings for pre-2021 technology conditions. The dataset provides strong coverage of hot water demand response (the largest category), residential battery/solar orchestration, and EV charging trials. Coverage is weaker for commercial refrigeration and large C&I demand response due to limited pilot activity in these segments.

## Risk Landscape by Delivery Dimension

**Software & Controls** emerges as the highest-risk dimension with 388 adverse records, driven primarily by data & measurement failures (31% of dimension records) and unvalidated integration issues (20%). The fragmentation of communication protocols across OEMs forces bespoke integration work for each device brand. Even CSIP-AUS, designed as a common standard, shows inconsistent implementation—some OEMs only partially comply and rely on aggregation platforms to fill gaps.

**Grid Connection** shows 291 adverse records dominated by data & measurement problems (25%) and regulatory barriers (18%). The core challenge is that network rules were written before widespread CER adoption exists. Each DNSP operates different standards for controlled load implementation, while bilateral retailer-network negotiations for each arrangement create complex, time-consuming processes that impede scaling.

**Operations** (310 records) faces commercial & market challenges (26%) and data & measurement issues (26%). The controlled load fleet—the primary hot water flexibility resource—is deteriorating, with approximately 25% of circuits inactive across all states. This represents a structural erosion of the addressable flexible demand resource.

**Community Engagement** shows 218 adverse records split between commercial barriers (45%) and coordination challenges (38%). Consumer adoption is constrained by complexity, lack of technical awareness, and reluctance to cede device control to third parties.

## Failure Mode Deep-Dive

**Commercial & Market (26% of adverse records)**: The fundamental business case problem reflects regulatory design gaps. Baseline measurement methodologies exclude up to 80% of loads, while energy efficiency certificate schemes inadvertently suppress demand for flexible technologies by subsidising heat pumps but excluding smart electric systems. The declining controlled load fleet represents a $1 billion missed opportunity—ISF modelling shows Business as Usual scenarios achieving only 9 GW of flexible capacity by 2040 versus 24 GW under active policy intervention.

**Data & Measurement (19% of adverse records)**: Interoperability failures manifest consistently across projects. In the PLUS ES trial, managing 14,000 smart meters proved more challenging than anticipated because prior tests used smaller data subsets. Field meters triggered different API error messages than lab devices, while NMI-level data access remained complex. Even successful platforms like Intellihub's deX encountered persistent OEM platform changes requiring ongoing integration maintenance.

**Coordination & Stakeholders (18% of adverse records)**: Multi-party programs face systematic coordination burdens. The Energy Masters pilot with seven partners found early project management consumed significantly more time than anticipated due to IP protections, cybersecurity requirements, and differing delivery paces. OEM vendors without structured agreements frequently implemented incorrect signal prioritisation, requiring significant rework.

**Technical Underperformance (11% of adverse records)**: Heat pumps particularly suffer from control logic mismatches. Standard controlled load schedules designed for resistive electric systems interrupt heat pump compressor operations, which manufacturers warn reduces unit lifecycle. In the PLUS ES trial, 13.1% of heat pump instances used 100% or more of their allowed heating window, indicating frequent operational interruptions.

## Temporal Trends

Recent projects (2022+) show increasing sophistication in platform architecture but persistent fundamental barriers. The Intellihub platform achieved 1.07 GW of aggregated load across 278,622 devices by integrating over 30 OEMs—demonstrating technical feasibility at scale. However, regulatory barriers have calcified rather than resolved. The WDRM remains limited to one participant after four years, while the absence of national CSIP-AUS frameworks forces each DNSP to develop bespoke solutions.

Early projects (2016–2018) focused on proving technical concepts and typically encountered basic integration challenges. Modern projects have largely solved technical integration but now face structural market design problems that require policy intervention rather than engineering solutions.

## Key Watchpoints for Due Diligence

1. **Controlled Load Fleet Status**: Verify the active proportion of controlled load circuits in target areas—25% inactivity is consistent across states and materially reduces addressable capacity compared to nameplate figures.

2. **OEM Integration Scope**: Map required OEM integrations against project timeline—each manufacturer requires intensive collaboration during development, and voluntary standards like Sunspec provide insufficient relief due to inconsistent implementation.

3. **Regulatory Pathway Clarity**: For WDRM-dependent revenue streams, confirm alternative pathways exist—only one provider is registered under WDRM after four years, effectively blocking access to LTESAs and CIS for most proponents.

4. **Heat Pump Control Logic**: Verify that control schedules are designed specifically for heat pump operation rather than resistive loads—standard schedules interrupt compressor operations and risk equipment damage.

5. **Multi-Party Coordination**: For projects with more than three partners, explicitly resource project management as a core function—coordination overhead scales non-linearly and consistently exceeds expectations.

6. **Market Access Dependencies**: Assess whether revenue streams depend on bilateral DNSP-retailer negotiations—the requirement for separate negotiation with every network creates a complex, time-consuming process that limits scaling potential.

7. **Consumer Segment Alignment**: Validate recruitment assumptions against actual demographic participation—trials consistently over-represent technology-engaged owner-occupiers and systematically under-represent renters and strata residents despite targeted outreach.