---
category: "Battery storage"
date_generated: 2025-01-09
record_count: 2597
project_count: 54
---

# Battery Storage — Delivery Risk Profile

## Executive Summary

Battery storage projects face three fundamental delivery challenges: grid connection complexity that scales exponentially with grid-forming capabilities, software integration failures across multi-vendor control systems, and regulatory frameworks racing to catch up with technology capabilities. 

Grid-forming projects require 20 months for GPS approval versus 17 months for grid-following equivalents, but can avoid $2-3 million per annum in system strength charges — making the additional complexity economically justified. The evidence shows control system integration is the primary failure mode, accounting for 25% of all adverse outcomes and creating cascade effects across procurement, commissioning, and operations.

Recent data shows improving conditions: connection approval timeframes fell from 11.8 months (FY2022) to 9.4 months (FY2025), and approved capacity grew from 4.2 GW to 15.7 GW. However, first-of-kind projects still face material schedule risk from immature vendor models, unclear OEM responsibilities across multi-vendor consortiums, and evolving NER requirements that can invalidate completed technical work mid-process.

Commercial risks centre on market revenue volatility — FCAS market value declined materially during multiple project timelines, forcing strategy shifts from FCAS-first to energy arbitrage models. Long-term Battery Storage Service Agreements with creditworthy counterparties have proven essential for project finance, with DPESS demonstrating that fixed-payment structures can transfer merchant risk while preserving operational optimisation.

## The Evidence Base

This profile draws from 2,597 records across 54 ARENA battery storage projects spanning 2012-2024. The evidence skews toward recent projects: 884 records from 2022-2024 provide the most representative view of current conditions, with 405 records from future projects (2025+) offering forward-looking insights. Only 217 records (8.4%) carry temporal warnings about pre-2021 cost or technology assumptions.

Coverage is comprehensive across delivery dimensions, with particularly rich datasets on software & controls (593 records), design (732 records), and grid connection (701 records). The portfolio includes both grid-following and grid-forming projects, community-scale and utility-scale deployments, and DC-coupled hybrid systems.

## Where Things Go Wrong

### Control System Integration: The Dominant Failure Mode

Software and control system integration drives 25% of unvalidated integration failures and represents the single biggest delivery risk. The pattern is consistent across projects: battery management systems, inverters, Power Plant Controllers, and Energy Management Systems from different vendors simply don't work together without extensive additional engineering.

"EMS and control system integration was widely characterised as one of the most underestimated aspects of community battery deployment. Battery vendors, inverter suppliers, and EMS providers were frequently separate entities with incompatible systems and limited integration experience," reports the ARENA Community Battery Round 1 portfolio analysis.

The Blyth BESS exemplifies the cascade effects. The project selected a third-party Power Plant Controller from a different OEM than the inverter supplier. "It was found the PPC operating in that way was not compatible with the GFM inverters as the PCC could only provide the P and Q signals and not the Vref signal that the inverters required to operate in GFM mode." This incompatibility wasn't discovered until after GFM contracts were executed, necessitating complete PPC replacement.

### Grid Connection: Regulatory Frameworks Racing Technology

Grid connection represents 32% of regulatory & approvals failures, with grid-forming projects bearing additional complexity. The May 2025 NER rule change removed reactive current settling time requirements and accommodated inertial response — changes that arose directly from grid-forming project experiences demonstrating existing standards were inappropriate for voltage-source inverters.

ARENA's second-round grid-forming projects faced a consistent challenge: "In the second round, the aim of achieving stability under normal operation while sacrificing the speed of the inverters during faults posed challenges to meet the reactive current rise time requirement specified in the minimum access standard of the NER." Multiple projects required extensive negotiation with AEMO and NSPs because standard automatic access standards created unachievable conflicts for grid-forming control.

The Liddell BESS GPS process illustrates both the challenge and the solution: "Achieving AAS across all GPS clauses simultaneously was infeasible due to intrinsic trade-offs (e.g., iq-rise speed vs frequency stability)," but early engagement between AGL Energy, Power Electronics, Fluence, AEMO and Transgrid enabled targeted solutions for priority clauses.

### Procurement Risk: OEM Maturity and Responsibility Gaps

Multi-vendor procurement creates accountability gaps that become critical during commissioning. The BHBESS project exemplifies this: "The complex nature of standard multi-party agreements for delivery of projects like a large-scale battery mean it can become unclear when requirements changed for GFM, to the point it is not possible to determine with certainty where within the multi-party arrangement technical requirements and responsibilities lie."

International supply chains add another layer of risk. The Yuri hydrogen project discovered that "Overseas vendors and sub-vendors' compliance with ASME code, AS3000 (Australian Standard for Electrical Installations) and EEHA (Electrical Equipment in Hazardous Areas) has been a major challenge for this project, resulting in delays during engineering, procurement, and equipment assembly."

OEM model maturity varies dramatically. Recipients found that "Selection of an OEM with established local market presence, proven models, and strong track record registering and commissioning in the NEM derisks the grid connection process. Once an inverter's dynamic model is well-tested and proven to meet the performance standards, this gives high confidence in the approval process."

## Failure Mode Deep-Dives

### Technical Underperformance: The Multi-Vendor Integration Tax

Technical underperformance accounts for 18% of all adverse records but drives cascade effects across multiple dimensions. The fundamental issue is that batteries, inverters, PPCs, and EMS systems are designed independently and integrated on-site for the first time during commissioning.

The United Energy Low Voltage Battery Trial found that "Off-the-shelf versions of IEEE 2030.5 were insufficient; advanced control, FCAS, and visibility required modifications. Complex DNSP control needs can exceed standard protocol functionality, requiring specialised development."

Even mature technologies struggle with integration. The Yadlamalka project reported: "Significant commissioning delays occurred because multi-vendor OEM equipment (VFBs, MVPS, DC-DC converters, Power Plant Controller) did not function as a system on connection, requiring on-site diagnosis by specialist engineers from each OEM supplier."

First-of-kind battery chemistries face additional challenges. Manufacturing defects in early Invinity VS3 cell stacks caused "electrolyte imbalances and stack-level instability in 13 modules. Combined with precautionary idling of additional at-risk modules, available discharge power fell from ~2.3 MW to approximately 1.0 MW, reducing battery availability to 43%."

### Commercial & Market Risk: Revenue Model Brittleness

Commercial and market failures represent 16% of adverse records, with a clear pattern: value stacking models dependent on volatile wholesale markets are inherently fragile.

The Electric Avenue project provides the clearest example: "Over the course of the project the FCAS market changed, and our retail partner advised that it was no longer economic to register for the Victorian contingency FCAS markets. This is due to contingency prices (and projected revenues) decreasing significantly," forcing project closure before full commercial operation.

FCAS market changes cascaded across multiple projects. The DPESS operator noted: "With FCAS market value declining, there is greater value in energy arbitrage opportunities. This shift means the site achieves a higher state of charge (SOC) during periods of low prices, enabling effective discharge during peak demand periods."

The solution that emerged was long-term contracted revenue structures. DPESS demonstrated that "The revenues of DPESS are wholly captured in a long-term Battery System Services Agreement (BSSA) between DPESS and EnergyAustralia. The BSSA entitles EnergyAustralia to full operational rights over DPESS, as they relate to charge and discharge decisions in both energy and FCAS markets."

### Regulatory & Approvals: The Moving Target Problem

The 16% of records attributed to regulatory & approvals failures reflect an industry where standards are being written in real-time based on project experience. Mid-process rule changes regularly invalidate completed work.

The Mortlake project exemplifies this: "The introduction of SSIAG v2.2 and ongoing updates to the SSQ methodology during the connection assessment period created challenges in keeping up with the latest applicable rules and technical notes."

Fire safety standards present particular challenges for community batteries: "The regulatory landscape for fire safety standards was described as 'evolving', with conflicting interpretations from fire authorities and certifiers across jurisdictions. Several projects discovered late in the process that their specified systems lacked compliant fire detection or suppression hardware."

DNSPs themselves struggle with consistency. The community battery portfolio found: "Network connection processes were a major bottleneck for some projects, often delaying commissioning and adding unanticipated cost or complexity. Batteries in the 100 kW to 1 MW range didn't neatly fit some existing DNSP frameworks."

### Coordination & Stakeholders: The Knowledge Management Challenge

Coordination failures account for 16% of adverse records, with staff turnover and knowledge transfer as persistent themes across the portfolio.

The community battery programme found: "With most deployments stretching over multiple years, staff turnover was common, both within project teams and among stakeholders or delivery partners. Several teams found themselves having to re-brief new decision-makers midstream, often without the benefit of structured onboarding materials."

Skills shortages compound coordination challenges: "There are a limited number of individuals with prior experience on GFM connections and in cases where individuals leave AEMO or NSPs for OEMs or project teams, as has been observed to occur, this can lead to loss of institutional knowledge."

The Tesla support experience at VBB illustrates OEM resource constraints: "Whilst this shift in prioritisation has introduced some minor delays in the upgrade works for the VBB legacy product, it also reflects the dynamic landscape in which adaptions and improvements are being actively pursued," as OEM resources shifted to newer products and larger projects.

## What Has Changed Over Time

### Improving Fundamentals

Several metrics show material improvement in battery storage delivery. Grid connection approval timeframes fell from 11.8 months (FY2022) to 9.4 months (FY2025), while approved capacity grew from 4.2 GW to 15.7 GW. This represents genuine system-level improvement in connection process efficiency.

Battery technology reliability has stabilised. DPESS achieved 99.6% battery pack availability after resolving initial teething issues, and battery degradation of "approximately 7% from the commencement of commercial operation" in Year 1 aligns with manufacturer expectations.

Grid-forming capabilities have moved from experimental to commercial. DPESS demonstrated that "grid-forming BESS can be preferred over synchronous condensers in network investment decisions (RIT-T outcomes), providing a commercially validated pathway for BESS to provide system strength services." Origin Energy's Mortlake project showed that "an early decision to switch the Mortlake BESS from grid-following (GFL) to grid-forming (GFM) inverter operation, avoiding system strength connection charges of $2–3 million per annum."

### Emerging Risks

Cyber security has emerged as a systematic gap. The community battery portfolio found: "Many proponents assumed vendors would 'bring their own' cybersecurity protocols, only to discover late in the process that integration, compliance, and ownership issues were unresolved."

International supply chain complexity is increasing. The Hydro Tasmania portfolio noted "variable and unpredictable international supply chain lead times for BESS procurement" and dangerous goods compliance requirements that were "not fully anticipated at project outset."

Market structure evolution continues to outpace project timelines. Multiple projects experienced FCAS market changes during development that fundamentally altered business cases, and this pattern shows no sign of stabilising.

### Technology Maturation

Grid-forming inverter capabilities have matured significantly since 2020. The May 2025 NER rule change reflected industry experience: "The settling time requirement for reactive current injection has been removed and a commencement time added" and "The definition of 'continuous uninterrupted operation' has been amended to permit inherent responses opposing phase angle jumps and frequency changes."

Second-life battery economics remain marginal. The Relectrify trial found: "The anticipated cost advantages of second-life batteries were largely offset by challenges in battery supply, logistics, and additional compliance overheads" with "limited availability of used batteries, high transport and handling costs, and extra certification effort."

## Due Diligence Checklist

### Grid Connection Strategy
- **For grid-forming projects**: Verify the inverter OEM has a proven track record of NER connection approvals for that specific inverter model. Ask for successful GPS compliance examples from recent projects, not just technical specifications.
- **Connection timeline**: Budget 20 months for grid-forming GPS approval versus 17 months for grid-following. If the applicant claims materially faster timelines for GFM systems, probe the basis for this confidence.
- **System strength assessment**: Request analysis of system strength charges under SSIAG versus GFM avoidance costs. Projects in low SCR areas should demonstrate that GFM is a connection prerequisite, not just an optimisation.

### Control System Integration
- **Vendor compatibility**: Ask whether the battery, inverter, and PPC come from the same OEM. If not, require evidence of successful integration with the specific OEM combination in prior projects.
- **FCAS capability**: If FCAS revenue is targeted, verify hardware certification, frequency injection testing capability, and EMS/SCADA integration at the procurement stage. Retrofitting FCAS capability post-commissioning is technically difficult and expensive.
- **Software ownership**: Establish clear ownership of control system performance across battery BMS, inverter controls, PPC, and EMS. Ask who will be accountable on-site when the integrated system doesn't perform as specified.

### Commercial Structure
- **Revenue certainty**: Projects relying on merchant BESS revenues should demonstrate a stress-test against FCAS market decline and energy price volatility. Ask whether the business case remains viable if FCAS revenue disappears entirely.
- **Offtake structure**: Assess whether a long-term Battery Storage Service Agreement with a creditworthy counterparty is in place. If not, understand how the project will access debt finance without contracted revenues.
- **Market participation timing**: Verify when FCAS registration will commence relative to commercial operations. Financial models assuming Day 1 FCAS participation consistently prove optimistic.

### Procurement Risk Management
- **OEM maturity**: For novel or recently upgraded battery technologies, ask about prior commercial deployments at scale. Manufacturing defects in early production batches can derate capacity by >50%.
- **International supply**: Assess dangerous goods compliance, shipping logistics costs, and OEM after-sales support availability. International shipping of used batteries can cost 2-4× initial estimates.
- **Warranty alignment**: Verify warranty coverage aligns with project finance tenor. Ask whether extended OEM warranties (20+ years) have been secured.

### Regulatory Compliance
- **Fire safety**: Confirm fire safety studies are completed and approved before construction commencement. Ask whether battery chemistry and thermal management comply with local fire authority requirements.
- **Standards evolution**: Understand how the project will adapt to evolving NER requirements. Projects with >2-year delivery timelines should demonstrate flexibility for mid-process rule changes.
- **Local authority engagement**: For community-scale projects, verify Development Application approval and assess whether DNSP connection thresholds could push the application into a higher cost category.

### Red Flags
- **Unproven integration**: Any project combining battery, inverter, and PPC from different OEMs without prior successful integration evidence.
- **Aggressive timelines**: Grid-forming projects claiming <18-month connection approval timelines without substantial precedent.
- **Merchant-only revenue**: Projects without contracted revenue depending entirely on volatile wholesale markets.
- **Late-stage technology changes**: Any project switching between grid-following and grid-forming after initial connection applications.
- **Offshore-only support**: OEM arrangements with no demonstrated local technical support capability.