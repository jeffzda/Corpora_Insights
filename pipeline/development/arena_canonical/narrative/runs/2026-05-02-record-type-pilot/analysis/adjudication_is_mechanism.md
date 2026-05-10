# Hand-adjudication: is_mechanism (Sonnet vs Opus disagreement subset)

## How to use this document

Read each record's `narrative` and `evidence` (the only fields the model saw).
Apply the axis definition below. Fill in the `Adjudicator:` line as `yes` or `no`.

Model opinions are hidden so they don't anchor you.

Then run `python3 analysis/score_mechanism_adjudication.py` to score Sonnet vs Opus.

---

## Axis definition (verbatim from v3 prompt)

## `is_mechanism` — yes | no

**`yes`** if the record names a *causal or technical pathway*: how or why
something works, fails, or has the property it does. Physical mechanisms,
organisational mechanisms, regulatory mechanisms all qualify, among other
similar items. The record explains the *how*, not just the *what*.

**`no`** if the record states a fact or outcome without explaining a causal
pathway.

---

## Records (44 total: 25 cases of Sonnet=no/Opus=yes + 25 cases of Sonnet=yes/Opus=no, randomised)

---

### Record 1 of 44 — `ARENA-DLV-0784-0058`

**narrative:** The Cutler Merz study exposes the difficulty in estimating SAPS benefits given the wide range of geographically heterogeneous cases, shifting cost basis of new technology, and impacts on human life. Estimating effects on quality of life or impact on life support systems is not straightforward, and traditional cost-benefit analysis may expose limits as the climate changes.

**evidence:** the study also exposes the difficulty in estimating benefits given the wide range of geographically heterogeneous cases, shifting cost basis of new technology, and impacts on human life. Estimating the effects on quality of life or impact on life support systems is not straight forward... the changing climate may expose limits in traditional cost-benefit analysis.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 2 of 44 — `ARENA-DLV-1175-0037`

**narrative:** The EMRC's August 2016 tender established as a fundamental principle that councils must not be exposed to waste volume or composition risk, driving the adoption of the waste arising contract structure.

**evidence:** It was a fundamental principle for the EMRC in its August 2016 tender that the Councils not be exposed to waste volume or composition risk

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 3 of 44 — `ARENA-DLV-1143-0087`

**narrative:** The trial found that the installer plays a critical role as an intermediary in the DER installation process but generally lacked the knowledge to adequately educate the customer about grid participation.

**evidence:** Installers were found to be key intermediaries in the installation process but generally lacked the knowledge to adequately educate the customer.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 4 of 44 — `ARENA-DLV-0784-0074`

**narrative:** Australian 15-year bond yields of 4.47% are used as an indication of the risk-free return rate for community battery project comparison. Positive IRR returns shown in the modelling mostly indicate returns below this interest rate threshold, meaning projects may not cover the cost of debt.

**evidence:** Australian 15-year bond yields, 4.47%, are provided as an indication of the risk free return rate... Positive returns shown above zero mostly indicate returns below interest rate thresholds.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 5 of 44 — `ARENA-DLV-1395-0008`

**narrative:** The LV DERMS procurement was based on recommendations from the previous milestone's design and market assessment. The system is now operational but remains in early stages of development, limiting the functions available to DNSPs.

**evidence:** LV DERMS is operational but remains in its early stages of development, limiting the functions available to Distributed Network Service Providers (DNSPs).

**Adjudicator:** No

**Notes (optional):** 

---

### Record 6 of 44 — `ARENA-DLV-1134-0033`

**narrative:** The naming convention lesson from HEMS was identified as having broader implications for other new energy technologies, with 'virtual power plants' cited as another example where consumer-unfriendly terminology may impede understanding and uptake.

**evidence:** This learning offers an important lens for the naming conventions for new energy technologies: Improved household understanding can facilitate recruitment, and therefore easily understandable naming conventions may be important to consider elsewhere (e.g. 'virtual power plants').

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 7 of 44 — `ARENA-DLV-1271-0002`

**narrative:** Traditional I-V testers used at the end of solar cell production lines require constant updates as cell technology changes and have limited throughput relative to current industry demand. These constraints make them costly to maintain and a bottleneck in manufacturing.

**evidence:** I-V testers need to be constantly updated as cell technology changes. Moreover, their throughput is limited compared to the current demand of the industry.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 8 of 44 — `ARENA-DLV-1123-0003`

**narrative:** The Solar Connect VPP Battery trial was designed so that batteries connected to the VPP would be scheduled to charge and discharge at optimal times of day to accommodate more solar in the community, while participants received a one-off payment and a monthly VPP credit.

**evidence:** Batteries connected to the VPP will be scheduled to charge and discharge at optimal times of day to accommodate more solar in the community. Participants received a one-off payment and a monthly VPP credit.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 9 of 44 — `ARENA-DLV-0261-0086`

**narrative:** The German government's collapse of the governing coalition is expected to bring forward federal elections to February 2025 (from September 2025), creating uncertainty around the future of German renewable energy policy, particularly if a Conservative government is elected. H2Global is supported by federal grants, making it potentially subject to policy change.

**evidence:** German Federal elections are currently scheduled to be held in September 2025, although it is expected that they will be brought forward to February 2025, due to the collapse of the governing coalition. This is currently creating some uncertainties around the future of German renewable energy policy, particularly if a Conservative government is elected.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 10 of 44 — `ARENA-DLV-0775-0009`

**narrative:** The P2P conceptual cost stack contains three principal variable components: the P2P export price paid to the prosumer (must exceed the feed-in tariff), variable network charges ($/kWh representing marginal cost of local network assets), and an administration fee (proxy for DLT hosting and administration costs). Fixed network and retail connection charges are treated as sunk costs and excluded from the model.

**evidence:** The P2P 'export' price is the price paid by the market to the prosumer who can export their surplus PV power... The variable network charges are applied in $/kWh and represent the marginal cost of utilising the localised network assets... The administration fee is a proxy to represent the cost of hosting and administering the distributed ledger.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 11 of 44 — `ARENA-DLV-0769-0085`

**narrative:** Fleet site assessments required engagement with multiple stakeholders including sustainability managers, facilities managers, and contracting/procurement stakeholders, as electrical works contracting needed to be negotiated.

**evidence:** In the process numerous stakeholders would be engaged with from sustainability managers, facilities managers as well as contracting/procurement stakeholders as contracting of the electrical works was negotiated.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 12 of 44 — `ARENA-DLV-1247-0081`

**narrative:** The WSGHH project demonstrated that cleaning steel pipelines to achieve fuel-cell-grade hydrogen purity (99.97%) was a novel challenge with limited precedent in Australia, requiring the development of a new cleaning methodology for carbon steel pipelines.

**evidence:** This was the first of its kind for carbon steel pipelines in Australia. Jemena developed a cleaning methodology for the pipeline following the commissioning of the plant to remove construction debris and purge the gas via a complete removal of contaminants, which led to a hydrogen purity of 99.97 % from the first sample at the outlet.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 13 of 44 — `ARENA-DLV-1308-0012`

**narrative:** Most bus depots in Australia are exposed sites, making them vulnerable to weather-related construction delays. Contracts for such projects did not adequately provision for extension of time due to severe weather events.

**evidence:** When building on an exposed depot, which is most of the depots in Australia, severe weather such as floods, thunderstorms and prolonged wet spells should be provisioned in the contracts to allow extension of time for the project programme.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 14 of 44 — `ARENA-DLV-1409-0033`

**narrative:** Maintaining open and transparent communication with stakeholders when construction challenges arise was identified as essential for managing expectations and building trust between the delivery team and operational staff.

**evidence:** Maintaining open, transparent communication with stakeholders when challenges arise. Proactive engagement helps manage expectations and builds trust between the delivery team and operational staff.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 15 of 44 — `ARENA-DLV-0667-0027`

**narrative:** The full-scale Biosolids Gasification Facility at Loganholme WWTP has been fully operational since February 2023. A demonstration plant, partially funded by ARENA, informed the design parameters for the full-scale facility.

**evidence:** Gasification is a relatively new technology, and the full-scale Biosolids Gasification Facility has been fully operational at Loganholme since February 2023. A demonstration plant, partially funded by ARENA (Loganholme Wastewater Treatment Plant Gasification Facility Demonstration Project) informed the design parameters for the full-scale facility.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 16 of 44 — `ARENA-DLV-0725-0044`

**narrative:** From a wholesale market perspective, the benefit of a half-hour average demand reduction following the implementation of the five-minute market settlement is questionable for AS4755-based air conditioner control.

**evidence:** From a wholesale market perspective, the benefit of a half-hour average demand reduction following the implementation of the five-minute market is questionable.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 17 of 44 — `ARENA-DLV-1249-0024`

**narrative:** Considerable delays occurred between the establishment of the original project concept and timelines and the final project approval and announcement, resulting in a shrinkage of several months in the time available for JET Charge to plan, mobilise, undertake product development, and test. An additional month was added to the timeframe but did not offset the time lost.

**evidence:** There were considerable delays between the establishment of original project concept and timelines and the final project approval and announcement. This led to shrinkage of several months in the time available for the development of the deliverables for JET Charge... this did not offset the time lost to plan in detail, mobilise, undertake product development and test.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 18 of 44 — `ARENA-DLV-0793-0050`

**narrative:** Price signals for voltage management should incentivise west-facing PV orientation to account for the impact PV has on voltage.

**evidence:** Orientate PV to account for the impact PV has on voltage (e.g., incentivize west-facing orientation).

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 19 of 44 — `ARENA-DLV-0566-0003`

**narrative:** The pilot plant trial campaign consisted of eight single-day trials, each targeting up to 1,000 kg of biomass processed, with 12 hours of elapsed time per trial including start-up and shutdown. Longer continuous trials were not conducted due to skills availability, space, and material handling constraints at the pilot plant.

**evidence:** The pilot plant trial campaign consisted of eight x single day trials targeting up to 1,000kg of biomass processed per trial. The expected time for each trial given the start up and shutdown requirements of the plant was 12 hours of elapsed time. Longer trials were not considered as it was impractical to run the pilot plant on a continuous 24 hour basis due to skills availability, space and material handling constraints.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 20 of 44 — `ARENA-DLV-1108-0051`

**narrative:** Temperature was identified as a key variable affecting hydrotreatment behaviour of pyrolysis bio-oil and coke formation in a continuous hydrotreatment reactor, with a published study (Gholizadeh et al., Fuel Processing Technology, 2016) examining these effects.

**evidence:** M. Gholizadeh, R. Gunawan, X. Hu, F. de Miguel Mercader, R. Westerhof, W. Chaitwat, M.M. Hasana, D. Mourant and C.-Z. Li, Effects of temperature on the hydrotreatment behaviour of pyrolysis bio-oil and coke formation in a continuous hydrotreatment reactor, Fuel Processing Technology, 2016, 148, 175-183.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 21 of 44 — `ARENA-DLV-0202-0052`

**narrative:** Industry participant build, test, and deploy costs are estimated by extrapolating AEMO's build costs using proportionality factors derived from the MITE business case: DNSPs at 0.14x AEMO's total build cost per participant, retailers at 0.07x, and others at 0.05x.

**evidence:** DNSPs – 0.14x; Retailers – 0.07x; Other – 0.05x. (that is, each DNSP's build, test, deploy cost is estimated to be 0.14x AEMO's total build, test and deploy cost)

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 22 of 44 — `ARENA-DLV-0782-0010`

**narrative:** The smaller commercial building (approximately 120 m², fewer than 5 control points) had its AC set-points increased by 3°C via ZenHQ during DR events, and the business reported that the HVAC did in fact turn off for a significant portion of the event (more than one hour).

**evidence:** Smaller commercial building; ~120m2, < 5x control points, provided HVAC load controlled remotely via ZenHQ. During an event the set-points of the AC systems were increased by 3ᵒC by Zen Ecosystems via ZenHQ... reports from the business are that the HVAC did in fact turn off for a significant portion of the event (>1hr).

**Adjudicator:** No

**Notes (optional):** 

---

### Record 23 of 44 — `ARENA-DLV-0564-0050`

**narrative:** Additional thermal storage beyond what is currently installed would further maximise heat recovery from existing equipment and enable load shifting.

**evidence:** Additional thermal storage would further maximise heat recovery from existing equipment and enable load shifting.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 24 of 44 — `ARENA-DLV-1247-0040`

**narrative:** The WSGHH facility was designed to accommodate behind-the-meter (BtM) solar panels and recycled water for electrolysis, but these were excluded from the final design due to budget limitations and not being essential to the test program requirements.

**evidence:** A number of further design changes were considered that primarily focused on accessing renewable resources for electrolysis, such as local behind-the-meter (BtM) solar panels and recycled water. Ultimately, these were not included due to budget limitations and not being essential to the test program requirements.

**Adjudicator:** Yes    

**Notes (optional):** 

---

### Record 25 of 44 — `ARENA-DLV-0775-0030`

**narrative:** IBM proposed that the DLT should record: (1) trading instructions and parameters provided by prosumers and consumers, and (2) the history of net P2P trading positions between retailers for the aggregated volume of P2P trades undertaken by their contracted consumers and prosumers. This design puts clear boundaries between DLT and existing systems.

**evidence:** a strong case can be made for using DLT(s) to support and enable future P2P renewable energy trading markets; particularly if the DLT were configured to record: 1. trading instructions and parameters provided by prosumers and consumers, and 2. the history of net P2P trading positions between retailers for the aggregated volume of P2P trades undertaken by their contracted consumers and prosumers.

**Adjudicator:** Yes

**Notes (optional):** Based on evidence excerpt rather than narrative

---

### Record 26 of 44 — `ARENA-DLV-1400-0061`

**narrative:** A legislated or industry-accepted Hydrogen Fuel Quality Standard would enable supply contracts to include provisions to remedy instances where off-specification product is supplied.

**evidence:** specific terms and conditions may include: Provision to remedy instances where off-specification product is supplied.

**Adjudicator:**  Yes

**Notes (optional):** 

---

### Record 27 of 44 — `ARENA-DLV-0527-0002`

**narrative:** The WGB was found to provide an inertial response when configured in virtual machine mode (VMM), but observation of performance through grid disturbance and subsequent modelling indicates that the currently implemented technology cannot be tuned to provide a like-for-like substitution for inertia from synchronous generation in all operating conditions.

**evidence:** While the WGB was found to provide an inertial response when configured in virtual machine mode (VMM), observation of the performance through grid disturbance and subsequent modelling indicates that the currently implemented technology cannot be tuned to provide a like-for-like substitution for inertia from synchronous generation in all the operating conditions.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 28 of 44 — `ARENA-DLV-0586-0120`

**narrative:** Low-emissions methanol can be made using low-emissions hydrogen combined with CO2 from biomass, direct air capture or waste CO2 streams. However, capturing atmospheric CO2 is currently financially prohibitive and high-concentration CO2 streams from biomass are not easily available in Australia.

**evidence:** Capturing atmospheric CO2 is currently financially prohibitive and high-concentrations streams from biomass or other sources are not easily available in Australia.

**Adjudicator:**  Yes

**Notes (optional):** 

---

### Record 29 of 44 — `ARENA-DLV-1293-0014`

**narrative:** Wattwatchers developed a Jupyter Notebook tool to enable MEM data services users to download anonymised data from the Wattwatchers API without requiring deep software development capability. The Notebook allows users to edit simple parameters (API key, start and end dates) and download data in CSV format, and also serves as a 'how to' guide with Python code examples.

**evidence:** Wattwatchers developed a tool using Jupyter Notebook, which is a web application for creating and sharing computational documents... the reference code provided by Wattwatchers that enables users to edit a few simple parameters (like an API key and start and end dates) and then the data can be downloaded in simple CSV formats.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 30 of 44 — `ARENA-DLV-1269-0039`

**narrative:** The project demonstrates that LV BESS can increase network capacity to allow more homes to connect and export from rooftop solar PV systems.

**evidence:** increasing the network capacity to allow more homes to connect and export from rooftop solar PV systems.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 31 of 44 — `ARENA-DLV-1316-0022`

**narrative:** Network operators (specifically AEMO) expect higher reactive current support from IBRs during fault ride-through, which requires a special operating mode. This expectation applies to GFM as well as GFL inverter-based resources.

**evidence:** Network operators expect higher reactive current support from IBRs during fault ride-through, which requires a special operating mode.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 32 of 44 — `ARENA-DLV-1273-0006`

**narrative:** Moving upgrader manufacturing to Australia is expected to limit and remove all future Australian Standards compliance issues for that supplier on subsequent projects. This is identified as a positive long-term outcome of the compliance challenge encountered on the Malabar project.

**evidence:** Given the manufacturing moved to Australia it will limit and remove all future issues associated with Australian compliance with that supplier.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 33 of 44 — `ARENA-DLV-0326-0052`

**narrative:** In Coordinated action LNG production decreases 36% by 2030 and 73% by 2050 (aligned with IEA NZE), reducing supply-chain emissions 91% by 2050 — driven by 25% from operational changes and 66% from demand decline.

**evidence:** the Australian Industry ETI assumes a 36 per cent reduction in Australian LNG exports between 2020 and 2030 and a 73 per cent reduction between 2020 and 2050...91 per cent: a 25 per cent reduction due to operational changes and a 66 per cent reduction due to changes in demand

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 34 of 44 — `ARENA-DLV-1222-0002`

**narrative:** During the detailed engineering phase, the control philosophy for the high-temperature heat pump required thorough review when integrating with existing ammonia refrigeration plant and existing thermal storage tanks. Although sizing of major plant assets had been completed during feasibility, detailed integration and control logic still needed to be finalised at the engineering stage.

**evidence:** Lessons for this phase of the works mainly revolved around the detailed review of the control philosophy for the high temperature heat pump when used in conjunction with existing ammonia refrigeration plant and existing thermal storage tanks. Whilst the sizing of the larger plant assets (i.e. Heat Pump and HV assets had previously been developed during the feasibility phase of the work, the detailed integration and control of the heat pump, refrigeration condenser and water management needed to be finalised.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 35 of 44 — `ARENA-DLV-1132-0073`

**narrative:** Most organisations were found to have limited access to fleet data, creating a significant barrier to using data-driven fleet transition tools.

**evidence:** Most organisations have limited access to data

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 36 of 44 — `ARENA-DLV-0495-0019`

**narrative:** Experimental boron distribution coefficients measured at 1500°C for slag A (no initial alumina) were 1.5–1.55 and for slag D (35 wt-% alumina) were approximately 2.0–2.5 after 2–6 hours of reaction time. These values are lower than FactSage predictions, confirming the positive correlation between alumina content and boron removal but at a smaller magnitude than simulated.

**evidence:** sample (slag) A, which has initially zero alumina content has LB values of 1.5 – 1.55 after 2 to 6 hours of reaction time with the silicon whereas sample (slag) D which has initially 35 wt. pct. alumina in the slag have approximately 2 – 2.5 after 2 to 6 hours of reaction time.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 37 of 44 — `ARENA-DLV-0327-0034`

**narrative:** Switching existing electricity use at steelmaking plants (including BF-BOF plants such as BlueScope's Port Kembla) from fossil fuel-based grid to renewables would eliminate around 9% of BlueScope's current emissions. Australia-wide, decarbonising existing electricity use would remove around 19% of emissions from the iron and steel supply chain.

**evidence:** Switching this electricity away from a fossil fuel based grid to renewables would eliminate around 9% of BlueScope's current emissions. Australia-wide, decarbonising existing electricity use would remove around 19% of emissions from the Iron and steel supply chain.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 38 of 44 — `ARENA-DLV-1364-0093`

**narrative:** Renewable hydrogen is likely to be used predominantly for large long-haul vehicles, trains, and shipping (the latter in the form of ammonia), while renewable electricity will mostly be used for smaller vehicles. Investing in both electric and renewable hydrogen fuelled vehicles is identified as a mechanism to reduce investment risks.

**evidence:** It is likely that renewable electricity will mostly be used for smaller vehicles and renewable hydrogen will be used for large long-haul vehicles, trains and shipping (the latter in the form of ammonia). Investing in the use and manufacture of both electric and renewable hydrogen fuelled vehicles could be one mechanism to reduce investment risks.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 39 of 44 — `ARENA-DLV-1029-0063`

**narrative:** Post blending, the blended SAF product is quality tested and batched as Jet A-1 under DEF STAN 91-091 before delivery to Brisbane Airport via pipeline, where it is comingled with jet fuel supplied by all JUHI JV partners.

**evidence:** Post blending, product quality testing will batch the blended traditional jet and neat SAF product as jet fuel, Jet-A1, under DefStan 91-091, before delivering to Brisbane Airport via pipeline.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 40 of 44 — `ARENA-DLV-1176-0018`

**narrative:** With the current forecast BESS deployment in the NEM, widespread adoption of grid-forming controls across future BESS projects could have a material positive impact on system strength and network stability at a sector scale.

**evidence:** With the current forecast BESS deployment in the NEM, could have a material positive impact on system strength and network stability.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 41 of 44 — `ARENA-DLV-1172-0002`

**narrative:** EV charging equipment manufacturers selected for the Future Fuels Program have incorporated MID metering equipment into the EVCS to comply with European jurisdiction requirements. ENGIE understands there is currently no requirement for NMI pattern and verification of metering in the EVCS in Australia, though NMI is understood to be considering trade (revenue) measurement policy for EVCS going forward.

**evidence:** EV charging equipment manufacturers selected for the Future Fuels Program have incorporated MID metering equipment into the EVCS (to comply with European jurisdiction where MID metering is required for revenue metering). ENGIE understands there is currently no requirement for NMI pattern and verification of metering in the EVCS.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 42 of 44 — `ARENA-DLV-1385-0057`

**narrative:** Emergency responders in Australia and New Zealand use the ANCAP Rescue app to access vehicle rescue sheets. BEV operators should ensure their vehicles' rescue sheets are available on the ANCAP Rescue app, or alternatively attach a visible QR code sticker providing direct access to the rescue sheet.

**evidence:** Emergency responders utilise the ANCAP Rescue app to access rescue sheets for a broad range of vehicles in Australia and New Zealand. Ensure your BEVs rescue sheet is available on the ANCAP Rescue app or alternatively attach a visible QR code sticker to provide direct access to the vehicle rescue sheet.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 43 of 44 — `ARENA-DLV-1234-0011`

**narrative:** Ease of doing business encompasses regulatory complexity, access to physical infrastructure such as electricity, and the overall business environment. Hysata uses ease-of-doing-business indices as a starting point and supplements them with insights from active discussions with each jurisdiction's trade offices and from the experiences of other companies operating in those geographies.

**evidence:** Ease-of-doing-business indices can be a helpful starting point. Hysata draws additional insights on each region by being in active discussion with each jurisdiction's trade offices, as well as learning from the experiences of other companies operating in those geographies.

**Adjudicator:** Yes

**Notes (optional):** From evidence excerpt

---

### Record 44 of 44 — `ARENA-DLV-1216-0028`

**narrative:** When the PCM TES is discharged at Reef HQ (and Montague), the discharge Coefficient of Performance (COP) is 40–70 depending on the discharge profile, compared to a COP of 4–5 for the ammonia refrigeration system. This represents an order-of-magnitude efficiency advantage for stored thermal energy discharge.

**evidence:** the discharge COP of the PCM TES is 40-70 depending on the discharge profile, compared to the ammonia system which has a COP of 4-5.

**Adjudicator:** No

**Notes (optional):** 

---
