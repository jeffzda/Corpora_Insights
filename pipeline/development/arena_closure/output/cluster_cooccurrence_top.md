# Cluster co-occurrence via shared events

For every real event (project, event_id with size 2-30), recorded which clusters had records in that event. Pairs of distinct clusters that share an event co-occur. Counts measure how often the two failure mechanisms manifest together within the same project event sequence.

- Multi-cluster events: 2,418
- Unique cluster pairs that co-occur: 5,491
- Showing top 60 pairs by co-occurrence count

## Top co-occurring cluster pairs


### 1. [c004] × [c005] — co-occur in 17 events
- **[c004] Supply Chain Disruption Delaying Hardware Delivery** (cluster size 172)
  > External shocks (pandemic, geopolitical conflict, chip shortages) disrupt international supply chains, extending equipment lead times beyond contracted or planned schedules and causing project delays.
- **[c005] COVID-19 Pandemic Disrupting Project Delivery** (cluster size 282)
  > COVID-19 restrictions force cancellation of physical activities, restrict site access, and destabilise supply chains, causing project delays and requiring pivot to remote or virtual delivery modes.
- Example events:
  - EVT-0052 in *Clean Energy Startup Support Programs*
  - EVT-0013 in *Jemena Dynamic Electric Vehicle Charging Trial*
  - EVT-0001 in *My Energy Marketplace*

### 2. [c039] × [c551] — co-occur in 14 events
- **[c039] Overcomplicated Product Offering Reducing Customer Conversion** (cluster size 98)
  > Customer uptake of new energy products is lower than expected because the sales process is too long, the product is perceived as too expensive or technically complex, and competing programs in the market create confusion that reduces conversion rates.
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- Example events:
  - EVT-0042 in *Consumer Energy Systems Providing Cost-Effective Grid Support*
  - EVT-0036 in *Consumer Energy Systems Providing Cost-Effective Grid Support*
  - EVT-0018 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*

### 3. [c551] × [c628] — co-occur in 11 events
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **[c628] Inadequate Customer Communication Causes Confusion and Negative Sentiment** (cluster size 91)
  > Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- Example events:
  - EVT-0019 in *Consumer Energy Systems Providing Cost-Effective Grid Support*
  - EVT-0108 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0018 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*

### 4. [c555] × [c558] — co-occur in 10 events
- **[c555] Voltage Transition Rate Sensitivity Causes Inverter Spurious Trip** (cluster size 44)
  > An inverter curtails output or trips during a voltage disturbance when the voltage edge transition rate exceeds a threshold, even though the same disturbance magnitude with a slower transition is ridden through without interruption.
- **[c558] Compliance Test Scope Gap Allows Non-Compliant Field Behaviour** (cluster size 73)
  > Devices pass certification but fail in operational conditions because the compliance test procedure covers only a subset of real-world stimuli, leaving untested response modes unverified.
- Example events:
  - EVT-0001 in *UNSW Addressing Barriers to Efficient Renewable Integration*
  - EVT-0044 in *UNSW Addressing Barriers to Efficient Renewable Integration*
  - EVT-0030 in *Horizon Power Business Model Pilot Phase 1*

### 5. [c013] × [c551] — co-occur in 10 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- Example events:
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0033 in *EnergyAustralia Demand Response Program*
  - EVT-0074 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 6. [c525] × [c551] — co-occur in 10 events
- **[c525] Consumer Distrust of Energy Industry Reducing Novel Model Uptake** (cluster size 108)
  > Uptake of new energy service models is reduced because consumers distrust energy companies and are sceptical of claimed benefits, requiring transparent community-oriented governance structures to overcome the barrier.
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- Example events:
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0044 in *Brighte - Electrify 2515 Community Pilot*
  - EVT-0084 in *Project Converge ACT Distributed Energy Resources Demonstration Pilot*

### 7. [c003] × [c679] — co-occur in 10 events
- **[c003] Regulatory Gap Slowing Novel Technology Approval** (cluster size 218)
  > Novel technology deployment is delayed or blocked because no applicable regulatory framework, compliance pathway, or approval precedent exists for the technology in the relevant jurisdiction.
- **[c679] Regulatory Standard Misalignment With Novel Technology Requirements** (cluster size 76)
  > Novel technologies cause delays and rework because existing regulatory standards were not designed for their characteristics, requiring reinterpretation, negotiation, or workarounds to achieve compliance.
- Example events:
  - EVT-0006 in *The Hazer Process: Commercial Demonstration Plant*
  - EVT-0103 in *Realising Electric Vehicle-to-Grid Services*
  - EVT-0007 in *Yuri Renewable Hydrogen to Ammonia Project*

### 8. [c013] × [c525] — co-occur in 9 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c525] Consumer Distrust of Energy Industry Reducing Novel Model Uptake** (cluster size 108)
  > Uptake of new energy service models is reduced because consumers distrust energy companies and are sceptical of claimed benefits, requiring transparent community-oriented governance structures to overcome the barrier.
- Example events:
  - EVT-0169 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*
  - EVT-0083 in *Realising Electric Vehicle-to-Grid Services*
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*

### 9. [c500] × [c554] — co-occur in 8 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c554] Retrofit Hardware Addition Blocked by Insufficient Physical Space** (cluster size 85)
  > Required hardware cannot be added to an existing installation because the original site layout was designed without provision for the additional equipment, leaving no physical space for retrofitting.
- Example events:
  - EVT-0005 in *Hybrid Concentrating Solar Thermal Systems*
  - EVT-0015 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0016 in *Enel X Commercial Refrigeration Flexible Demand Project*

### 10. [c025] × [c715] — co-occur in 8 events
- **[c025] Lengthy Multi-Party Permitting Delaying Construction Start** (cluster size 152)
  > Construction is delayed because multiple independent permitting authorities must each grant approval before work can commence, and each approval process has its own timeline that cannot be fully parallelised.
- **[c715] Regulatory or Certification Process Causing Deployment Timeline Overrun** (cluster size 51)
  > Mandatory certification or approval processes cause significant schedule delays because the procedural requirements are more complex and time-consuming than anticipated at project outset.
- Example events:
  - EVT-0017 in *Resilient Wind Energy for Telecommunication Sites*
  - EVT-0042 in *Increasing the Uptake of Solar PV in Strata Residential Developments*
  - EVT-0009 in *Yuri Renewable Hydrogen to Ammonia Project*

### 11. [c012] × [c024] — co-occur in 8 events
- **[c012] Traditional Voltage Regulation Insufficient for Full PV Hosting** (cluster size 105)
  > Conventional voltage regulation solutions (tap changers, fixed voltage targets, off-the-shelf batteries) are exhausted before 100% PV hosting capacity is achieved on distribution feeders because they cannot address the full range of voltage violations caused by high solar penetra
- **[c024] High-Voltage Grid Conditions Causing Inverter Disconnection** (cluster size 102)
  > Solar inverters disconnect or curtail export during periods of high solar generation and low load because distribution network voltages rise above inverter trip thresholds, reducing system output and customer revenue.
- Example events:
  - EVT-0009 in *NOJA Power Intelligent Switchgear*
  - EVT-0067 in *Distributed Energy Resources Hosting Capacity Study*
  - EVT-0048 in *Horizon Power Business Model Pilot Phase 1*

### 12. [c013] × [c628] — co-occur in 7 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c628] Inadequate Customer Communication Causes Confusion and Negative Sentiment** (cluster size 91)
  > Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- Example events:
  - EVT-0015 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0065 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*

### 13. [c039] × [c628] — co-occur in 7 events
- **[c039] Overcomplicated Product Offering Reducing Customer Conversion** (cluster size 98)
  > Customer uptake of new energy products is lower than expected because the sales process is too long, the product is perceived as too expensive or technically complex, and competing programs in the market create confusion that reduces conversion rates.
- **[c628] Inadequate Customer Communication Causes Confusion and Negative Sentiment** (cluster size 91)
  > Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- Example events:
  - EVT-0018 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0014 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0074 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 14. [c519] × [c574] — co-occur in 7 events
- **[c519] Insufficient DER Penetration Limiting Voltage Control Effectiveness** (cluster size 42)
  > Network voltage control interventions fail to produce measurable voltage change because the proportion of DER devices with the required capability is too small relative to the total DER population continuing to push voltage in the opposite direction.
- **[c574] Static Export Limits Constrain DER Installation and Utilisation** (cluster size 118)
  > Customers install smaller DER systems and export less renewable energy than technically possible because static network export limits restrict connection capacity regardless of real-time network conditions.
- Example events:
  - EVT-0149 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*
  - EVT-0041 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0004 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 15. [c563] × [c628] — co-occur in 7 events
- **[c563] OEM Monitoring App Data Contradicts Customer Expectations Causing Confusion** (cluster size 45)
  > Customers lose confidence in their DER assets because OEM monitoring applications display system behaviour that contradicts their expectations, and no contextual explanation is provided.
- **[c628] Inadequate Customer Communication Causes Confusion and Negative Sentiment** (cluster size 91)
  > Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- Example events:
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0079 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0170 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 16. [c500] × [c537] — co-occur in 7 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c537] EV charger installation barriers reduce conversion from interest to deployment** (cluster size 83)
  > Conversion from customer interest to charger installation is reduced because physical site constraints such as multi-unit dwellings and complex civil works make installation impractical or prohibitively expensive.
- Example events:
  - EVT-0084 in *Simply Energy Virtual Power Plant (VPP)*
  - EVT-0019 in *EnergyAustralia Demand Response Program*
  - EVT-0028 in *My Energy Marketplace*

### 17. [c617] × [c739] — co-occur in 7 events
- **[c617] Fragmented Flexibility Markets Inhibit Value Stream Stacking** (cluster size 78)
  > The economic value of flexible resources is reduced because wholesale, ancillary service, and network support markets operate in isolation without coordination, producing competing signals and preventing cross-market optimisation.
- **[c739] Absent Market Incentive Suppresses Advanced Technology Adoption** (cluster size 127)
  > Advanced capability remains undeployed because no market mechanism exists to value or reward it, removing the financial incentive for proponents to invest.
- Example events:
  - EVT-0171 in *Community Models for Deploying and Operating DER*
  - EVT-0012 in *AGL Virtual Trial of Peer-to-Peer Energy Trading*
  - EVT-0074 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 18. [c024] × [c574] — co-occur in 7 events
- **[c024] High-Voltage Grid Conditions Causing Inverter Disconnection** (cluster size 102)
  > Solar inverters disconnect or curtail export during periods of high solar generation and low load because distribution network voltages rise above inverter trip thresholds, reducing system output and customer revenue.
- **[c574] Static Export Limits Constrain DER Installation and Utilisation** (cluster size 118)
  > Customers install smaller DER systems and export less renewable energy than technically possible because static network export limits restrict connection capacity regardless of real-time network conditions.
- Example events:
  - EVT-0043 in *Advancing Renewables with PCM Thermal Energy Storage*
  - EVT-0043 in *evolve DER Project*
  - EVT-0026 in *Simply Energy Virtual Power Plant (VPP)*

### 19. [c551] × [c605] — co-occur in 7 events
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **[c605] Participant Engagement Materials Underutilised Reducing Program Effectiveness** (cluster size 39)
  > Program outcomes are limited because a substantial proportion of participants do not engage with educational or informational materials provided, reducing the behaviour change or capability uplift the program was designed to achieve.
- Example events:
  - EVT-0017 in *PLUS ES South Australia Demand Flexibility Trial*
  - EVT-0024 in *Solar and Storage Trial at Alkimos Beach Residential Development*
  - EVT-0036 in *Solar and Storage Trial at Alkimos Beach Residential Development*

### 20. [c500] × [c560] — co-occur in 7 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c560] Installer Knowledge Gap Undermines Customer Outcome Quality** (cluster size 104)
  > Customers receive suboptimal or incomplete solutions because installers lack sufficient technical knowledge to advise holistically across the full range of relevant products and options.
- Example events:
  - EVT-0071 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0055 in *SA Power Networks Flexible Exports for Solar PV Trial*
  - EVT-0029 in *Testing the Performance of Lithium Ion Batteries*

### 21. [c538] × [c916] — co-occur in 7 events
- **[c538] IBR grid-forming instability near network transfer capability limits** (cluster size 54)
  > Inverter-based resources produce oscillations or destabilising power swings when operating near or above network transfer capability limits because high system sensitivity or absence of a feasible steady-state operating point prevents stable power injection.
- **[c916] Inverter-Based Resource Instability Under Low System Strength** (cluster size 57)
  > Inverter-based plant performance degrades because low system strength increases the likelihood of power quality disturbances that adversely interact with inverter control systems.
- Example events:
  - EVT-0001 in *Stability Enhancing Measures for Weak Grids Study*
  - EVT-0008 in *Monash Grid Oscillation Project (Study and Software Development)*
  - EVT-0027 in *AGL Broken Hill Grid-Forming Battery*

### 22. [c536] × [c551] — co-occur in 6 events
- **[c536] Unfamiliarity with novel technology causes risk-averse adoption delay** (cluster size 229)
  > Potential adopters delay or reject technically mature technology because they lack firsthand operational experience, causing perceived risk to exceed actual risk and requiring staged de-risking approaches before commitment.
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- Example events:
  - EVT-0136 in *SA Strategic Regional Electric Vehicle Adoption Program*
  - EVT-0100 in *Consumer Energy Systems Providing Cost-Effective Grid Support*
  - EVT-0035 in *Increasing the Uptake of Solar PV in Strata Residential Developments*

### 23. [c501] × [c560] — co-occur in 6 events
- **[c501] Novel Technology Unfamiliarity Causes Local Maintenance Failure** (cluster size 82)
  > Locally novel equipment causes maintenance and fault-rectification failures because regional technicians lack the specialised knowledge to diagnose and repair it despite training.
- **[c560] Installer Knowledge Gap Undermines Customer Outcome Quality** (cluster size 104)
  > Customers receive suboptimal or incomplete solutions because installers lack sufficient technical knowledge to advise holistically across the full range of relevant products and options.
- Example events:
  - EVT-0033 in *Brighte - Electrify 2515 Community Pilot*
  - EVT-0069 in *SA Power Networks Flexible Exports for Solar PV Trial*
  - EVT-0055 in *SA Power Networks Flexible Exports for Solar PV Trial*

### 24. [c002] × [c642] — co-occur in 6 events
- **[c002] Overseas Equipment Non-Compliance With Australian Standards** (cluster size 184)
  > Equipment designed to international norms fails to meet Australian-specific standards because overseas manufacturers are unfamiliar with local requirements, forcing costly redesign, replacement, or re-certification.
- **[c642] Overseas Supplier Disinterest Limits Local Equipment Availability** (cluster size 70)
  > Technology options available internationally are inaccessible domestically because overseas manufacturers consider the local market too small or remote to justify market entry, restricting procurement choices for project developers.
- Example events:
  - EVT-0012 in *Yarwun Hydrogen Calcination Pilot Demonstration Program*
  - EVT-0029 in *New Energies Service Station Geelong Demonstration Project*
  - EVT-0025 in *New Energies Service Station Geelong Demonstration Project*

### 25. [c013] × [c563] — co-occur in 6 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c563] OEM Monitoring App Data Contradicts Customer Expectations Causing Confusion** (cluster size 45)
  > Customers lose confidence in their DER assets because OEM monitoring applications display system behaviour that contradicts their expectations, and no contextual explanation is provided.
- Example events:
  - EVT-0169 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0030 in *Consumer Energy Systems Providing Cost-Effective Grid Support*

### 26. [c010] × [c500] — co-occur in 6 events
- **[c010] Lack of DER Interoperability Standard Forcing Bespoke Integration** (cluster size 256)
  > Integrating diverse DER assets requires disproportionate effort because vendor- and model-specific APIs are not consistently implemented to a common industry standard, preventing plug-and-play deployment.
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- Example events:
  - EVT-0013 in *Hardwick Meatworks Heat Pump Installation and Power Upgrade Demonstration*
  - EVT-0008 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0029 in *Testing the Performance of Lithium Ion Batteries*

### 27. [c534] × [c581] — co-occur in 6 events
- **[c534] Raise service provision requires curtailment of variable renewable output** (cluster size 45)
  > Variable renewable generators cannot simultaneously maximise energy output and provide raise frequency services because headroom for upward response requires operating below maximum available power, making curtailment structurally unavoidable.
- **[c581] Plant Controller Output Constraint Creates Minimum Enablement Floor** (cluster size 39)
  > A minimum operational threshold is imposed on ancillary service participation because the plant controller must take generating units offline to meet low setpoints, which disables the control mode required for frequency services below that threshold.
- Example events:
  - EVT-0051 in *Hornsdale Wind Farm Stage 2 FCAS Trial*
  - EVT-0050 in *Hornsdale Wind Farm Stage 2 FCAS Trial*
  - EVT-0006 in *Lake Bonney Battery Energy Storage System*

### 28. [c003] × [c715] — co-occur in 6 events
- **[c003] Regulatory Gap Slowing Novel Technology Approval** (cluster size 218)
  > Novel technology deployment is delayed or blocked because no applicable regulatory framework, compliance pathway, or approval precedent exists for the technology in the relevant jurisdiction.
- **[c715] Regulatory or Certification Process Causing Deployment Timeline Overrun** (cluster size 51)
  > Mandatory certification or approval processes cause significant schedule delays because the procedural requirements are more complex and time-consuming than anticipated at project outset.
- Example events:
  - EVT-0042 in *Increasing the Uptake of Solar PV in Strata Residential Developments*
  - EVT-0005 in *Charge Together Phase 2*
  - EVT-0008 in *Horizon Power Denham Hydrogen Demonstration*

### 29. [c011] × [c824] — co-occur in 6 events
- **[c011] Data Privacy and Sharing Barriers Impeding Network Intelligence** (cluster size 166)
  > Useful operational data cannot be shared between parties because legal ambiguity, privacy obligations, or commercial sensitivity create hesitancy or prohibition, leaving network operators without the information needed to manage DER.
- **[c824] Data Absence or Inaccessibility Blocks Project Execution** (cluster size 58)
  > Project activities cannot proceed as planned because required data either does not exist in the trial area, is locked behind commercial or legal arrangements, or has not yet been collected, leaving analytical or operational gaps.
- Example events:
  - EVT-0011 in *Zen Ecosystems Demand Response*
  - EVT-0062 in *Project SHIELD - Synchronising Heterogeneous Information to Evaluate Limits for DNSP*
  - EVT-0015 in *Low-Cost Integration of On-Site Solar PV for Large-Scale Industrial Heat Supply*

### 30. [c010] × [c011] — co-occur in 6 events
- **[c010] Lack of DER Interoperability Standard Forcing Bespoke Integration** (cluster size 256)
  > Integrating diverse DER assets requires disproportionate effort because vendor- and model-specific APIs are not consistently implemented to a common industry standard, preventing plug-and-play deployment.
- **[c011] Data Privacy and Sharing Barriers Impeding Network Intelligence** (cluster size 166)
  > Useful operational data cannot be shared between parties because legal ambiguity, privacy obligations, or commercial sensitivity create hesitancy or prohibition, leaving network operators without the information needed to manage DER.
- Example events:
  - EVT-0125 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0065 in *AEMO – CER Data Exchange Industry Co-Design*
  - EVT-0013 in *AEMO – CER Data Exchange Industry Co-Design*

### 31. [c010] × [c950] — co-occur in 6 events
- **[c010] Lack of DER Interoperability Standard Forcing Bespoke Integration** (cluster size 256)
  > Integrating diverse DER assets requires disproportionate effort because vendor- and model-specific APIs are not consistently implemented to a common industry standard, preventing plug-and-play deployment.
- **[c950] Declared Compatibility Without Comprehensive Interoperability Testing** (cluster size 25)
  > Stated performance specifications are not realised in practice because compatibility declarations are made without comprehensive testing of component interactions under real operating conditions.
- Example events:
  - EVT-0039 in *AGL Demand Response*
  - EVT-0103 in *SA Power Networks Flexible Exports for Solar PV Trial*
  - EVT-0029 in *Testing the Performance of Lithium Ion Batteries*

### 32. [c040] × [c680] — co-occur in 6 events
- **[c040] Defect Formation During Crystal Growth Reducing Cell Performance** (cluster size 125)
  > Solar cell performance is reduced because defects introduced during the silicon or absorber crystal growth process increase recombination, and these defects cannot be fully eliminated by post-growth processing.
- **[c680] Real-World Operating Conditions Accelerate Degradation Beyond Manufacturer Specifications** (cluster size 78)
  > Equipment degrades faster than manufacturer specifications predict because laboratory test conditions do not replicate real-world stressors such as elevated temperature or operational cycling profiles.
- Example events:
  - EVT-0012 in *Machine Learning Applications for Utility-Scale PV*
  - EVT-0005 in *Improving World-Record Commercial High-Efficiency N-Type Solar Cells*
  - EVT-0002 in *Hydrogenated Bifacial PERL Silicon PV Cells*

### 33. [c561] × [c903] — co-occur in 5 events
- **[c561] Market Rule Finalisation After Technical Scoping Causes Rework** (cluster size 49)
  > Technical integration work must be redone or extended because market or regulatory design is finalised after the technical scoping baseline is agreed, introducing requirements not captured in the original scope.
- **[c903] Regulatory or Market Rule Change Reduces Previously Viable Opportunity** (cluster size 58)
  > A change in regulatory settings or market rules reduces the operational opportunity or economic value that a project or technology was designed to capture.
- Example events:
  - EVT-0018 in *Enel X Demand Response Project*
  - EVT-0005 in *Neoen Victorian Big Battery (Moorabool) Retrofit*
  - EVT-0032 in *Darlington Point Energy Storage System*

### 34. [c040] × [c807] — co-occur in 5 events
- **[c040] Defect Formation During Crystal Growth Reducing Cell Performance** (cluster size 125)
  > Solar cell performance is reduced because defects introduced during the silicon or absorber crystal growth process increase recombination, and these defects cannot be fully eliminated by post-growth processing.
- **[c807] Scale-Up Causes Efficiency Loss Due to Material Resistance** (cluster size 37)
  > Increasing device area causes efficiency reduction because the sheet resistance or material property that is negligible at laboratory scale becomes a dominant loss mechanism at larger dimensions.
- Example events:
  - EVT-0013 in *Heterocontact-Polysilicon Hybrid Interdigitated Back Contact Solar Cells*
  - EVT-0012 in *Heterocontact-Polysilicon Hybrid Interdigitated Back Contact Solar Cells*
  - EVT-0022 in *New Materials and Architectures for Organic Solar Cells*

### 35. [c018] × [c501] — co-occur in 5 events
- **[c018] Unprecedented Project Scope Requiring All Deliverables From Scratch** (cluster size 138)
  > Project execution costs and timelines are significantly higher than anticipated because no prior precedent exists for the technology or configuration, forcing the contractor to develop all engineering deliverables, procedures, and documentation without reference material.
- **[c501] Novel Technology Unfamiliarity Causes Local Maintenance Failure** (cluster size 82)
  > Locally novel equipment causes maintenance and fault-rectification failures because regional technicians lack the specialised knowledge to diagnose and repair it despite training.
- Example events:
  - EVT-0099 in *Australian Hydrogen Centre*
  - EVT-0009 in *DeGrussa Solar Project*
  - EVT-0019 in *TransGrid Wallgrove Battery*

### 36. [c614] × [c662] — co-occur in 5 events
- **[c614] Limited DER Visibility Impairs Network Operational Planning** (cluster size 131)
  > Inadequate situational awareness and forward planning occur because active DER are not sufficiently visible to network operators and market participants, preventing effective operational and investment decisions.
- **[c662] Grid Impedance Data Gaps Undermine Network Modelling Accuracy** (cluster size 50)
  > Network power-flow models produce unreliable results because source impedance data contains systematic gaps or errors in phase connectivity, neutral grounding, and component values.
- Example events:
  - EVT-0090 in *Project Converge ACT Distributed Energy Resources Demonstration Pilot*
  - EVT-0172 in *Project Converge ACT Distributed Energy Resources Demonstration Pilot*
  - EVT-0043 in *evolve DER Project*

### 37. [c551] × [c563] — co-occur in 5 events
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **[c563] OEM Monitoring App Data Contradicts Customer Expectations Causing Confusion** (cluster size 45)
  > Customers lose confidence in their DER assets because OEM monitoring applications display system behaviour that contradicts their expectations, and no contextual explanation is provided.
- Example events:
  - EVT-0019 in *Solar and Storage Trial at Alkimos Beach Residential Development*
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0170 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*

### 38. [c018] × [c500] — co-occur in 5 events
- **[c018] Unprecedented Project Scope Requiring All Deliverables From Scratch** (cluster size 138)
  > Project execution costs and timelines are significantly higher than anticipated because no prior precedent exists for the technology or configuration, forcing the contractor to develop all engineering deliverables, procedures, and documentation without reference material.
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- Example events:
  - EVT-0069 in *AGL Solar Project*
  - EVT-0027 in *Hardwick Meatworks Heat Pump Installation and Power Upgrade Demonstration*
  - EVT-0028 in *United Energy Low Voltage Battery Trial*

### 39. [c022] × [c500] — co-occur in 5 events
- **[c022] OEM Model Opacity Causing Incorrect Modelling Assumptions** (cluster size 97)
  > Grid connection modelling produces incorrect results requiring rework because the OEM provides insufficient technical detail to support accurate model development, leading to wrong assumptions by the modelling engineer.
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- Example events:
  - EVT-0069 in *AGL Solar Project*
  - EVT-0028 in *United Energy Low Voltage Battery Trial*
  - EVT-0037 in *Lake Bonney Battery Energy Storage System*

### 40. [c025] × [c537] — co-occur in 5 events
- **[c025] Lengthy Multi-Party Permitting Delaying Construction Start** (cluster size 152)
  > Construction is delayed because multiple independent permitting authorities must each grant approval before work can commence, and each approval process has its own timeline that cannot be fully parallelised.
- **[c537] EV charger installation barriers reduce conversion from interest to deployment** (cluster size 83)
  > Conversion from customer interest to charger installation is reduced because physical site constraints such as multi-unit dwellings and complex civil works make installation impractical or prohibitively expensive.
- Example events:
  - EVT-0001 in *Metro Advertising Revenue Funded Electric Vehicle Charging Trial*
  - EVT-0019 in *Evie Networks Future Fuels Public Fast Charging*
  - EVT-0002 in *Intellihub Street Power Pole EV Charger with Grid Integration*

### 41. [c537] × [c668] — co-occur in 5 events
- **[c537] EV charger installation barriers reduce conversion from interest to deployment** (cluster size 83)
  > Conversion from customer interest to charger installation is reduced because physical site constraints such as multi-unit dwellings and complex civil works make installation impractical or prohibitively expensive.
- **[c668] Existing Grid Infrastructure Capacity Bottleneck Blocks New Load Connection** (cluster size 94)
  > New electrical loads cannot be connected or expanded because existing transmission or distribution infrastructure lacks sufficient capacity and requires costly upgrade before deployment can proceed.
- Example events:
  - EVT-0001 in *Metro Advertising Revenue Funded Electric Vehicle Charging Trial*
  - EVT-0019 in *Evie Networks Future Fuels Public Fast Charging*
  - EVT-0022 in *Europcar Electric Vehicle Infrastructure Project*

### 42. [c788] × [c916] — co-occur in 5 events
- **[c788] Renewable Resource Siting Conflict With Grid Strength** (cluster size 33)
  > Optimal renewable generation sites cause compounding grid stability problems because they are located in weak grid areas far from load centres.
- **[c916] Inverter-Based Resource Instability Under Low System Strength** (cluster size 57)
  > Inverter-based plant performance degrades because low system strength increases the likelihood of power quality disturbances that adversely interact with inverter control systems.
- Example events:
  - EVT-0016 in *AGL Broken Hill Grid-Forming Battery*
  - EVT-0001 in *AGL Broken Hill Grid-Forming Battery*
  - EVT-0001 in *Stability Enhancing Measures for Weak Grids Study*

### 43. [c636] × [c681] — co-occur in 5 events
- **[c636] Regulatory Framework Absence Removes NSP Timeliness Incentive** (cluster size 38)
  > Network service providers complete connection processes slowly because the regulatory framework provides no meaningful incentive or penalty for timely completion, creating schedule risk for project developers.
- **[c681] Grid Connection Requirement Uncertainty Causes Iterative Rework** (cluster size 79)
  > Connection proponents incur repeated study and negotiation cycles because network service provider requirements are not pre-specified and evolve during the connection process.
- Example events:
  - EVT-0001 in *Sustainable transport in tourism*
  - EVT-0015 in *Moree Solar Farm*
  - EVT-0037 in *Lake Bonney Battery Energy Storage System*

### 44. [c001] × [c622] — co-occur in 5 events
- **[c001] Inaccurate SOC Estimation Causing Operational Unreliability** (cluster size 102)
  > Incorrect state-of-charge estimation causes over-discharge, protection-mode triggering, or capacity test inconsistency because the BMS or inverter cannot accurately track actual battery state.
- **[c622] Repeated Cycling Accelerates Battery Degradation and Efficiency Loss** (cluster size 46)
  > Providing frequency or ancillary services from batteries causes additional charge-discharge cycling that increases round-trip efficiency losses and accelerates capacity degradation, raising the effective cost of service delivery.
- Example events:
  - EVT-0011 in *Project Fulfil*
  - EVT-0021 in *Testing the Performance of Lithium Ion Batteries*
  - EVT-0011 in *Testing the Performance of Lithium Ion Batteries*

### 45. [c582] × [c656] — co-occur in 5 events
- **[c582] Inconsistent Multi-Partner Interpretation Causes Project Misalignment** (cluster size 81)
  > Project delays and cost overruns occur because consortium members hold divergent interpretations of shared coordination mechanisms or project scope, causing them to develop incompatible solutions that must be reconciled during integration.
- **[c656] Misaligned Stakeholder Interests Slow Collaborative Progress** (cluster size 58)
  > Collaborative initiatives progress slowly because participating parties have differing expectations, risk appetites, or value perceptions that prevent coordinated action.
- Example events:
  - EVT-0007 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0039 in *Increasing the Uptake of Solar PV in Strata Residential Developments*
  - EVT-0001 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*

### 46. [c551] × [c879] — co-occur in 5 events
- **[c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation** (cluster size 185)
  > Consumers fail to engage with or benefit from distributed energy programs because they lack awareness of how market arrangements, trading mechanisms, or program structures work.
- **[c879] Terminology Ambiguity Causes Stakeholder Misunderstanding of Concepts** (cluster size 37)
  > Stakeholders misinterpret technical or policy concepts because the terminology used does not intuitively convey the intended meaning, leading to confusion about scope or boundaries.
- Example events:
  - EVT-0048 in *Brighte - Electrify 2515 Community Pilot*
  - EVT-0014 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0033 in *Project Converge ACT Distributed Energy Resources Demonstration Pilot*

### 47. [c501] × [c701] — co-occur in 5 events
- **[c501] Novel Technology Unfamiliarity Causes Local Maintenance Failure** (cluster size 82)
  > Locally novel equipment causes maintenance and fault-rectification failures because regional technicians lack the specialised knowledge to diagnose and repair it despite training.
- **[c701] Remote Support Latency From Offshore Vendor Time Zone Gap** (cluster size 21)
  > Operational issues take longer to resolve because the technology vendor's support team is located in a distant time zone, creating communication delays until local presence is established.
- Example events:
  - EVT-0042 in *Project Fulfil*
  - EVT-0039 in *Testing the Performance of Lithium Ion Batteries*
  - EVT-0021 in *AGL Solar Project*

### 48. [c500] × [c501] — co-occur in 5 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c501] Novel Technology Unfamiliarity Causes Local Maintenance Failure** (cluster size 82)
  > Locally novel equipment causes maintenance and fault-rectification failures because regional technicians lack the specialised knowledge to diagnose and repair it despite training.
- Example events:
  - EVT-0018 in *Rottnest Island Water and Renewable Energy Nexus (WREN) Project*
  - EVT-0055 in *SA Power Networks Flexible Exports for Solar PV Trial*
  - EVT-0039 in *Testing the Performance of Lithium Ion Batteries*

### 49. [c500] × [c813] — co-occur in 5 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c813] Legacy Equipment Incompatibility Blocks Participation in New Schemes** (cluster size 57)
  > Older installed assets lack the hardware interfaces or communication capabilities required by new control or market schemes, preventing their participation because the schemes were designed around modern equipment specifications.
- Example events:
  - EVT-0018 in *Rottnest Island Water and Renewable Energy Nexus (WREN) Project*
  - EVT-0008 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0113 in *G & K O’Connor - Closing the Loop on Red Meat Processing Energy and Emissions*

### 50. [c525] × [c563] — co-occur in 5 events
- **[c525] Consumer Distrust of Energy Industry Reducing Novel Model Uptake** (cluster size 108)
  > Uptake of new energy service models is reduced because consumers distrust energy companies and are sceptical of claimed benefits, requiring transparent community-oriented governance structures to overcome the barrier.
- **[c563] OEM Monitoring App Data Contradicts Customer Expectations Causing Confusion** (cluster size 45)
  > Customers lose confidence in their DER assets because OEM monitoring applications display system behaviour that contradicts their expectations, and no contextual explanation is provided.
- Example events:
  - EVT-0169 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*
  - EVT-0026 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0030 in *Consumer Energy Systems Providing Cost-Effective Grid Support*

### 51. [c500] × [c681] — co-occur in 5 events
- **[c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns** (cluster size 198)
  > Inadequate upfront technical scoping causes project delays and increased costs because integration requirements and site constraints are only discovered during execution.
- **[c681] Grid Connection Requirement Uncertainty Causes Iterative Rework** (cluster size 79)
  > Connection proponents incur repeated study and negotiation cycles because network service provider requirements are not pre-specified and evolve during the connection process.
- Example events:
  - EVT-0071 in *Kennedy Energy Park*
  - EVT-0037 in *Lake Bonney Battery Energy Storage System*
  - EVT-0068 in *Kennedy Energy Park*

### 52. [c018] × [c517] — co-occur in 5 events
- **[c018] Unprecedented Project Scope Requiring All Deliverables From Scratch** (cluster size 138)
  > Project execution costs and timelines are significantly higher than anticipated because no prior precedent exists for the technology or configuration, forcing the contractor to develop all engineering deliverables, procedures, and documentation without reference material.
- **[c517] Multi-party parallel contract negotiation causing project delays** (cluster size 97)
  > Projects are delayed because finalising interdependent contracts with multiple counterparties simultaneously requires aligning separate commercial interests, regulatory expectations, and funding-body requirements that cannot be sequenced independently.
- Example events:
  - EVT-0121 in *Project Converge ACT Distributed Energy Resources Demonstration Pilot*
  - EVT-0067 in *Kennedy Energy Park*
  - EVT-0074 in *Ballarat Energy Storage System (BESS)*

### 53. [c605] × [c628] — co-occur in 5 events
- **[c605] Participant Engagement Materials Underutilised Reducing Program Effectiveness** (cluster size 39)
  > Program outcomes are limited because a substantial proportion of participants do not engage with educational or informational materials provided, reducing the behaviour change or capability uplift the program was designed to achieve.
- **[c628] Inadequate Customer Communication Causes Confusion and Negative Sentiment** (cluster size 91)
  > Poorly coordinated or absent participant communication during program events causes customers to misattribute negative outcomes to the program, generating confusion and dissatisfaction that requires reactive remediation.
- Example events:
  - EVT-0017 in *PLUS ES South Australia Demand Flexibility Trial*
  - EVT-0024 in *AEMO Virtual Power Plant Demonstrations*
  - EVT-0036 in *Solar and Storage Trial at Alkimos Beach Residential Development*

### 54. [c009] × [c041] — co-occur in 5 events
- **[c009] High Upfront Capital Preventing Positive Investment Return** (cluster size 346)
  > Projects are cash-positive at an operating level but deliver negative or sub-threshold investor returns because the high upfront capital cost pushes simple payback or IRR beyond acceptable investment thresholds.
- **[c041] Incentive Mismatch Between System Designer and End Beneficiary** (cluster size 132)
  > Shared energy systems produce inefficient outcomes because the parties who design and configure the system are not the parties who bear the operational consequences, creating misaligned incentives that persist after deployment.
- Example events:
  - EVT-0032 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0040 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0034 in *Battery of the Nation Future State NEM Analysis (Stage 2)*

### 55. [c010] × [c526] — co-occur in 5 events
- **[c010] Lack of DER Interoperability Standard Forcing Bespoke Integration** (cluster size 256)
  > Integrating diverse DER assets requires disproportionate effort because vendor- and model-specific APIs are not consistently implemented to a common industry standard, preventing plug-and-play deployment.
- **[c526] Expanded Cyber Attack Surface from Consumer-Sited DER Devices** (cluster size 95)
  > DER deployments create a fundamentally larger and less controllable cyber security attack surface because devices are installed in untrusted public environments, use open internet protocols, and lack the physical and network isolation of traditional grid infrastructure.
- Example events:
  - EVT-0025 in *Flinders Island Hybrid Energy Hub*
  - EVT-0127 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0061 in *AEMO – CER Data Exchange Industry Co-Design*

### 56. [c004] × [c648] — co-occur in 5 events
- **[c004] Supply Chain Disruption Delaying Hardware Delivery** (cluster size 172)
  > External shocks (pandemic, geopolitical conflict, chip shortages) disrupt international supply chains, extending equipment lead times beyond contracted or planned schedules and causing project delays.
- **[c648] Cascading Infrastructure Connection Delays From Sequential Dependencies** (cluster size 49)
  > A single upstream procurement or approval failure triggers a cascade of downstream delays because each connection step is sequentially dependent on the prior one completing successfully.
- Example events:
  - EVT-0075 in *Kidston Pumped Hydro Energy Storage*
  - EVT-0019 in *CSIRO - Solar Thermochemical Hydrogen Research and Development*
  - EVT-0016 in *Co-located Vanadium Flow Battery Storage and Solar*

### 57. [c011] × [c623] — co-occur in 5 events
- **[c011] Data Privacy and Sharing Barriers Impeding Network Intelligence** (cluster size 166)
  > Useful operational data cannot be shared between parties because legal ambiguity, privacy obligations, or commercial sensitivity create hesitancy or prohibition, leaving network operators without the information needed to manage DER.
- **[c623] Incompatible Data Formats Block Cross-Jurisdiction Analytics** (cluster size 33)
  > Heterogeneous data formats used by different jurisdictions or organisations prevent datasets from being ingested by a common analytics platform, requiring bespoke workarounds that delay or limit analysis.
- Example events:
  - EVT-0066 in *Project SHIELD - Synchronising Heterogeneous Information to Evaluate Limits for DNSP*
  - EVT-0062 in *Project SHIELD - Synchronising Heterogeneous Information to Evaluate Limits for DNSP*
  - EVT-0065 in *AEMO – CER Data Exchange Industry Co-Design*

### 58. [c013] × [c041] — co-occur in 5 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c041] Incentive Mismatch Between System Designer and End Beneficiary** (cluster size 132)
  > Shared energy systems produce inefficient outcomes because the parties who design and configure the system are not the parties who bear the operational consequences, creating misaligned incentives that persist after deployment.
- Example events:
  - EVT-0065 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*
  - EVT-0060 in *AGL Demand Response*
  - EVT-0069 in *Western Australia Distributed Energy Resources Orchestration Pilot (Project Symphony)*

### 59. [c013] × [c039] — co-occur in 5 events
- **[c013] Customer Reluctance to Cede Remote Device Control** (cluster size 112)
  > Demand response automation and remote control programs fail to achieve target participation because customers are unwilling to grant third parties direct control over their equipment, regardless of the financial or system benefits offered.
- **[c039] Overcomplicated Product Offering Reducing Customer Conversion** (cluster size 98)
  > Customer uptake of new energy products is lower than expected because the sales process is too long, the product is perceived as too expensive or technically complex, and competing programs in the market create confusion that reduces conversion rates.
- Example events:
  - EVT-0033 in *EnergyAustralia Demand Response Program*
  - EVT-0074 in *AEMO - Project EDGE (Energy Demand and Generation Exchange)*
  - EVT-0070 in *Simply Energy Virtual Power Plant (VPP)*

### 60. [c532] × [c647] — co-occur in 5 events
- **[c532] Measurement system mismatch causes data inconsistency between parties** (cluster size 84)
  > Discrepancies arise between independently operated measurement systems because differences in meter type, location, timing, or data completeness produce irreconcilable readings of the same physical quantity.
- **[c647] Missing or Incomplete Data Degrading Automated System Outputs** (cluster size 51)
  > Gaps in real-time telemetry or historical data cause automated calculation or forecasting systems to produce degraded or unreliable outputs because the algorithms cannot distinguish missing data from valid zero-value signals.
- Example events:
  - EVT-0079 in *Project SHIELD - Synchronising Heterogeneous Information to Evaluate Limits for DNSP*
  - EVT-0055 in *Lake Bonney Stages 2/3*
  - EVT-0005 in *Solar Power Ensemble Forecaster*

## Top self-co-occurring clusters
(Same mechanism manifesting multiple times within one project event sequence)

- [c005] COVID-19 Pandemic Disrupting Project Delivery — 55 events
- [c002] Overseas Equipment Non-Compliance With Australian Standards — 30 events
- [c003] Regulatory Gap Slowing Novel Technology Approval — 30 events
- [c500] Insufficient Technical Scoping Causes Installation Delays and Cost Overruns — 27 events
- [c010] Lack of DER Interoperability Standard Forcing Bespoke Integration — 25 events
- [c006] Demand Response Baseline Methodology Mis-measuring Actual Curtailment — 24 events
- [c009] High Upfront Capital Preventing Positive Investment Return — 24 events
- [c011] Data Privacy and Sharing Barriers Impeding Network Intelligence — 22 events
- [c551] Consumer Unfamiliarity With Market Mechanisms Limits DER Participation — 21 events
- [c042] Electrode Material Degradation From Chemical Incompatibility — 21 events
- [c025] Lengthy Multi-Party Permitting Delaying Construction Start — 21 events
- [c004] Supply Chain Disruption Delaying Hardware Delivery — 21 events
- [c536] Unfamiliarity with novel technology causes risk-averse adoption delay — 20 events
- [c022] OEM Model Opacity Causing Incorrect Modelling Assumptions — 20 events
- [c012] Traditional Voltage Regulation Insufficient for Full PV Hosting — 18 events
- [c526] Expanded Cyber Attack Surface from Consumer-Sited DER Devices — 17 events
- [c013] Customer Reluctance to Cede Remote Device Control — 17 events
- [c015] Undocumented Site History Creating Brownfield Construction Surprises — 16 events
- [c556] Wi-Fi Connectivity Dropouts Disrupting Remote Device Control — 16 events
- [c040] Defect Formation During Crystal Growth Reducing Cell Performance — 16 events