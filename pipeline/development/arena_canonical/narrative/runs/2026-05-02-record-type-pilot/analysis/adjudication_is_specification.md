# Hand-adjudication: is_specification (contested records)

## How to use this document

Read each record's `narrative` and `evidence` (the only fields the model saw).
Apply the axis definition below. Fill in the `Adjudicator:` line as `yes` or `no`.

Then run `python3 analysis/score_adjudication.py` to score each format against your judgments.

**Important — only judge from `narrative` + `evidence`.** Do not pull in other fields 
(lesson, intervention, etc.) — the model didn't see them, so the comparison would be unfair.

---

## Axis definition (verbatim from v3 prompt)

## `is_specification` — yes | no

**`yes`** if the record describes parameters, scope, magnitudes, equipment IDs,
organisational structures, dates, or program design — descriptive properties
without causal framing or outcome valence.

**`no`** if the record is fundamentally about an outcome, a mechanism, or a
prescription rather than a descriptive parameter.

---

## Records (36 contested)

Model opinions are hidden so they don't anchor you. Judge from the source content alone.

---

### Record 1 of 36 — `ARENA-DLV-1361-0015`

**narrative:** Local stores in remote SETuP communities have limited construction tools and equipment in stock. If project planning does not factor in contingencies for hardware and equipment, this creates schedule risk.

**evidence:** Local stores have limited construction tools and equipment in stock, which can create schedule risk if planning does not factor in contingencies for hardware and equipment

**Adjudicator:** No

**Notes (optional):** 

---

### Record 2 of 36 — `ARENA-DLV-0729-0084`

**narrative:** The SETuP program's Tranche 1 year-on-year PV yield increase was 17% (from 4,643 MWh to 5,441 MWh), while Daly River increased by 4% (from 1,588 MWh to 1,654 MWh). The Tranche 1 improvement is attributed to operational improvements including minimum load reductions and low-load engine deployments.

**evidence:** Increase year-on-year: Tranche 1: 17%, Daly River: 4%. The initiatives taken by service delivery teams have made a significant contribution to improving yield, including proactive trials of lower minimum load settings on existing diesel assets, and priority deployments of low load capable replacement engines at a number of sites.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 3 of 36 — `ARENA-DLV-0732-0008`

**narrative:** The NT SETuP program is expected to deliver lower operational costs (especially diesel fuel purchase), reduced exposure to diesel market price risk, and a lower frequency of diesel refuelling trips.

**evidence:** The overall project will lead to lower operational costs (especially the purchase of diesel fuel), a reduced exposure to diesel market price risk, and a lower frequency of diesel refuelling trips.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 4 of 36 — `ARENA-DLV-0732-0033`

**narrative:** Some NT SETuP communities benefited from additional diesel generator replacements where traditional generators (with a limit of around 60% RPF) that were at end of life were replaced by low-load diesel generators, which can tolerate up to 90% RPF.

**evidence:** traditional diesel generators (which have a limit of around 60% RPF) which were at the end of life were replaced by low load diesel generators, which can tolerate up to 90% RPF.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 5 of 36 — `ARENA-DLV-0911-0019`

**narrative:** The cooling system developed by Power and Water for the Minjilang low-load diesel deployment uses separate remote radiator circuits for engine and charge air cooling, providing independent temperature control of each circuit, which is important for effective running at low loads.

**evidence:** The cooling system developed by Power and Water and its partners has separate remote radiator circuits for engine and charge air cooling. This provides independent control of each circuit's temperature which is also important for effective running at low loads.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 6 of 36 — `ARENA-DLV-0911-0077`

**narrative:** Solar at medium contribution levels in Power and Water grids does not replace diesel capacity; sufficient diesel capacity is retained to service the community's entire electricity demand to ensure supply security during evening/night-time peak loads, cloud events and solar system maintenance outages. The business case for solar investment has been based on displacing diesel fuel only and minimising operating costs.

**evidence:** None of Power and Water's solar projects to date have displaced diesel capacity, i.e. sufficient diesel capacity is retained in order to service the community's entire electricity demand. This is done to ensure the supply security is maintained in the event of evening/night-time peak loads and also throughout the day during cloud events or at times when the solar system is taken offline for maintenance.

**Adjudicator:** Yes

**Notes (optional):** "at medium contribution levels" is a specification with a correlate following

---

### Record 7 of 36 — `ARENA-DLV-0912-0007`

**narrative:** The NT SETuP program is expected to deliver lower operational costs (especially diesel fuel purchase), reduced exposure to diesel market price risk, and a lower frequency of diesel refuelling trips — the latter being critical for top-end communities that can become inaccessible for months during the wet season.

**evidence:** a lower frequency of diesel refuelling trips, which is an important consideration for many top-end communities which can become inaccessible for months at a time during the wet season.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 8 of 36 — `ARENA-DLV-0912-0030`

**narrative:** Since project conception, some NT SETuP communities have benefited from additional diesel generator replacements where traditional generators (with a limit of around 60% RPF) at end of life were replaced by low-load diesel generators that can tolerate up to 90% RPF.

**evidence:** some NT SETuP communities have benefited from additional diesel generator replacements, where traditional diesel generators (which have a limit of around 60% RPF) which were at the end of life were replaced by low load diesel generators, which can tolerate up to 90% RPF.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 9 of 36 — `ARENA-DLV-1361-0001`

**narrative:** Health services in remote communities served by the SETuP program in the Northern Territory are limited, and medical evacuation procedures may be complex. This creates elevated safety risk for project personnel working in these locations.

**evidence:** Health services are limited and medical evacuation may be complex

**Adjudicator:** No

**Notes (optional):** 

---

### Record 10 of 36 — `ARENA-DLV-1361-0002`

**narrative:** Police are often not present in remote communities involved in the SETuP program, and community unrest may arise without warning. This creates an unpredictable security environment for project teams.

**evidence:** Police are often not present in communities and community unrest may arise without warning

**Adjudicator:** No

**Notes (optional):** 

---

### Record 11 of 36 — `ARENA-DLV-1361-0003`

**narrative:** Animal risks in remote Northern Territory communities are significantly elevated compared to urban worksites, including hazards from camp dogs, snakes, buffalos, camels, pigs, and crocodiles. These risks must be factored into site safety planning.

**evidence:** Animal risks are increased including: camp dogs, snakes, buffalos, camels, pigs, crocodiles etc.

**Adjudicator:** No

**Notes (optional):** 

---

### Record 12 of 36 — `ARENA-DLV-1361-0004`

**narrative:** Travel to remote SETuP communities involved use of small aircraft and long driving distances on dirt roads, both of which increase travel risk compared to standard project travel. Wild camels were specifically identified as a significant driving hazard on routes such as the Docker River Road.

**evidence:** Travel risks are higher due to small aircraft and long driving distances travelled on dirt roads; wild camels are a significant driving risk

**Adjudicator:** No

**Notes (optional):** 

---

### Record 13 of 36 — `ARENA-DLV-1361-0006`

**narrative:** Regular Passenger Transport (RPT) services to remote SETuP communities are often non-existent or, where available, limited and infrequent. This constrains the ability to mobilise and demobilise personnel and equipment on schedule.

**evidence:** Regular Passenger Transport (RPT) is often non-existent or limited and infrequent

**Adjudicator:** No

**Notes (optional):** 

---

### Record 14 of 36 — `ARENA-DLV-1361-0007`

**narrative:** RPT services to remote communities impose limited baggage allowances and will not guarantee carriage of excess baggage, restricting the amount of tools, equipment, and materials that can be transported by air.

**evidence:** RPTs have limited baggage allowance and won't guarantee carriage of excess baggage

**Adjudicator:** No

**Notes (optional):** 

---

### Record 15 of 36 — `ARENA-DLV-1361-0010`

**narrative:** For many remote communities in the SETuP program, bulk material delivery was only possible by barge, which is considerably more expensive than road transport. This significantly increases material supply costs.

**evidence:** For many remote communities, bulk material delivery is only possible by barge which can be considerably more expensive than road transport

**Adjudicator:** No

**Notes (optional):** 

---

### Record 16 of 36 — `ARENA-DLV-1361-0011`

**narrative:** Roads to remote SETuP communities are often not constructed for all-weather access, introducing schedule risks during the wet season when roads may become impassable. This can delay construction and delivery activities.

**evidence:** Roads are often not constructed for all-weather access which introduces schedule risks in the wet season

**Adjudicator:** No

**Notes (optional):** 

---

### Record 17 of 36 — `ARENA-DLV-1361-0012`

**narrative:** Volatile substance limitations are in place in many remote communities, restricting access to petrol, aerosols, and similar materials. These restrictions can impede access to essential goods required for project delivery.

**evidence:** Volatile substance limitations are in place in many communities: petrol, aerosols, etc., which can be a challenge to accessing essential goods for project delivery

**Adjudicator:** No

**Notes (optional):** 

---

### Record 18 of 36 — `ARENA-DLV-1361-0013`

**narrative:** Alcohol restrictions apply in many remote communities involved in the SETuP program, with severe penalties for non-compliance. Project personnel must be made aware of and strictly adhere to these restrictions.

**evidence:** Alcohol restrictions apply in many communities with severe penalties for non-compliance

**Adjudicator:** No

**Notes (optional):** 

---

### Record 19 of 36 — `ARENA-DLV-1361-0014`

**narrative:** Travel permits are often required to access worksites in remote communities, and routes may be diverted to accommodate road closures for cultural reasons. Failure to obtain permits or anticipate diversions can delay project activities.

**evidence:** Travel permits are often required to travel to worksites, and routes may be diverted to accommodate for road closures for cultural reasons

**Adjudicator:** No

**Notes (optional):** 

---

### Record 20 of 36 — `ARENA-DLV-1361-0016`

**narrative:** Local specialist labour skills are scarce in remote communities, limiting the ability to source local contractors to rectify defects during or after the SETuP program. This increases dependence on expensive mobilisation of external specialists.

**evidence:** Local specialist labour skills are scarce which limits the ability to source local contractors to rectify defects

**Adjudicator:** No

**Notes (optional):** 

---

### Record 21 of 36 — `ARENA-DLV-1361-0017`

**narrative:** Local inventory of plant and machinery in remote SETuP communities is very limited, and what exists is often non-functional or unreliable for project use. Project teams cannot depend on sourcing plant locally.

**evidence:** Local inventory of Plant and machinery are very limited and often non-functional or unreliable to use on a project

**Adjudicator:** No

**Notes (optional):** 

---

### Record 22 of 36 — `ARENA-DLV-1361-0018`

**narrative:** Light vehicles are limited in remote communities and other transport options are often not available, constraining the mobility of project teams once on site.

**evidence:** Light vehicles are limited, other transport options are often not available

**Adjudicator:** No

**Notes (optional):** 

---

### Record 23 of 36 — `ARENA-DLV-1361-0019`

**narrative:** Accommodation and food preparation services in remote communities are often very limited, requiring project teams to be fully self-sufficient in these areas. Failure to plan for self-sufficiency can compromise team welfare and productivity.

**evidence:** Project teams need to be self-sufficient as accommodation and food preparation services are often very limited

**Adjudicator:** No

**Notes (optional):** 

---

### Record 24 of 36 — `ARENA-DLV-1361-0020`

**narrative:** Mobile phone coverage is lacking in many remote areas served by the SETuP program, and where service exists it is often intermittent and unreliable. This creates communication gaps that can affect safety and coordination.

**evidence:** Lack of mobile phone coverage in many areas, those areas with service are often intermittent and unreliable

**Adjudicator:** No

**Notes (optional):** 

---

### Record 25 of 36 — `ARENA-DLV-1361-0021`

**narrative:** Access to office equipment such as printers and scanners is minimal in remote communities, and such equipment is often not connected to the internet. This limits the ability to perform document-intensive project administration tasks on site.

**evidence:** Minimal access to office equipment such as printers and scanners which are often not connected to the internet

**Adjudicator:** No

**Notes (optional):** 

---

### Record 26 of 36 — `ARENA-DLV-1361-0026`

**narrative:** Handling of hazardous waste such as oil and paints is problematic in remote communities due to the absence of appropriate disposal facilities and infrastructure.

**evidence:** Handling of hazardous waste such as oil and paints is problematic

**Adjudicator:** No

**Notes (optional):** 

---

### Record 27 of 36 — `ARENA-DLV-1363-0093`

**narrative:** The SETuP program hybridised approximately 50% of Power and Water's remote diesel power stations with PV, adding 10 MW of PV generation capacity across approximately 30 communities. This critical mass of hybrid systems normalised renewable energy in the NT energy mix and transformed organisational practice from one-off projects to business as usual.

**evidence:** The goal of SETuP is to transform the way energy is produced in remote communities of the Northern Territory. The program has resulted in approximately 50% of all remote diesel power stations managed by Power and Water's subsidiary, Indigenous Essential Services Pty Ltd (IES), being hybridised and will normalise the contribution of renewable energy in the Northern Territory energy mix.

**Adjudicator:** Yes

**Notes (optional):** 

---

### Record 28 of 36 — `ARENA-DLV-0729-0044`

**narrative:** Active curtailment by the control system to maintain diesel generator minimum loading levels is identified as the most significant expected impact on SETuP PV yield. The level of curtailment at any moment depends on both available PV power and the 'solar contribution window' (the difference between total station load and the minimum load requirement of the operating diesel generator).

**evidence:** The most significant expected impact on SETuP PV yield is active curtailment by the control system in order to balance supply and demand and maintain the prioritised minimum loading levels on the diesel generators. The level of PV curtailment at any moment is dependent on both the available PV power and the 'solar contribution window', being the difference between the total station load and the minimum load requirement of the operating diesel generator(s).

**Adjudicator:** No

**Notes (optional):** 

---

### Record 29 of 36 — `ARENA-DLV-0730-0031`

**narrative:** The most significant expected impact on SETuP PV yield is active curtailment by the control system to balance supply and demand and maintain minimum loading levels on diesel generators. The level of curtailment at any moment depends on both available PV power and the 'solar contribution window' (the difference between total station load and the minimum load requirement of the operating diesel generator).

**evidence:** The most significant expected impact on SETuP PV yield is active curtailment by the control system in order to balance supply and demand, and maintain the prioritised minimum loading levels on the diesel generators... The level of PV curtailment at any moment is dependent on both the available PV power and the 'solar contribution window', being the difference between the total station load and the minimum load requirement of the operating diesel generator(s).

**Adjudicator:** No

**Notes (optional):** 

---

### Record 30 of 36 — `ARENA-DLV-0731-0025`

**narrative:** Active curtailment by the control system to balance supply and demand and maintain minimum diesel generator loading levels is identified as the most significant expected impact on SETuP PV yield. The level of curtailment at any moment depends on both available PV power and the 'solar contribution window' — the difference between total station load and the minimum load requirement of the operating diesel generator(s).

**evidence:** The most significant expected impact on SETuP PV yield is active curtailment by the control system in order to balance supply and demand and maintain the prioritised minimum loading levels on the diesel generators... The level of PV curtailment at any moment is dependent on both the available PV power and the 'solar contribution window', being the difference between the total station load and the minimum load requirement of the operating diesel generator(s).

**Adjudicator:** No

**Notes (optional):** 

---

### Record 31 of 36 — `ARENA-DLV-0919-0079`

**narrative:** Each crew had a satellite phone, but data could not be sent by this method and the phone operation was unfamiliar. In some communities, Power and Water landline phones and fax at power stations provided backup communications.

**evidence:** Each crew had a satellite phone, but data could not be sent by this method (fax/email) and the phone operation was unfamiliar. In some communities, the availability of the Power and Water landline phone and fax at the power stations meant that the crew was not completely without communications.

**Adjudicator:** Yes

**Notes (optional):** Mostly intended as observation but there is a statement about each crew member having a satellite phone with is a project specification and given multiple tags are allowed I am writing 'yes' for this record

---

### Record 32 of 36 — `ARENA-DLV-1362-0021`

**narrative:** Materials were delivered to remote SETuP sites in containers pre-packed to suit the specific site and the planned sequence of construction activities at that site.

**evidence:** Deliver materials to site in containers pre‐packed to suit the site and the sequence of events at site.

**Adjudicator:** Yes

**Notes (optional):** Details a project decision on how materials were delivered to site. 

---

### Record 33 of 36 — `ARENA-DLV-0729-0047`

**narrative:** Deploying a low-load rated replacement engine before end-of-life is a large outlay when accounting for mobilisation, demobilisation, labour costs, and the increasingly limited value of redeploying the removed engine.

**evidence:** Deploying a low-load rated replacement engine before end-of-life is a large outlay taking in to account mobilisation and demobilisation, labour costs, and the increasingly limited value of redeploying the removed engine.

**Adjudicator:** No 

**Notes (optional):** 

---

### Record 34 of 36 — `ARENA-DLV-0730-0034`

**narrative:** Deploying a low-load rated replacement engine before end-of-life is identified as a large outlay when accounting for mobilisation, demobilisation, labour costs and the limited value of redeploying the removed engine.

**evidence:** Deploying a lowload rated replacement engine before end-of-life is a large outlay taking in to account mobilisation and demobilisation, labour costs and the increasingly limited value of redeploying the removed engine.

**Adjudicator:** No

**Notes (optional):** duplicate of 0729-0047

---

### Record 35 of 36 — `ARENA-DLV-0731-0029`

**narrative:** Deploying a low-load rated replacement engine before end-of-life is identified as a large outlay, taking into account mobilisation and demobilisation, labour costs, and the increasingly limited value of redeploying the removed engine.

**evidence:** Deploying a lowload rated replacement engine before end-of-life is a large outlay taking in to account mobilisation and demobilisation, labour costs and the increasingly limited value of redeploying the removed engine.

**Adjudicator:** No

**Notes (optional):** duplicate of 0729-0047

---

### Record 36 of 36 — `ARENA-DLV-0911-0026`

**narrative:** The purchase of new low-load-capable engines is being prioritised for solar hybrid sites in Power and Water's asset replacement programme, which may result in a mix of different manufacturers' engines at those sites and may also result in the low-load engine carrying a larger proportion of run hours, reducing its replacement period.

**evidence:** The purchase of new low load capable engines is being prioritised for solar sites to maximise value from the solar investment. This may result in a mix of different manufacturer's engines at those sites. It may also result in the low load engine carrying a larger proportion of run hours, reducing the replacement period for that set.

**Adjudicator:** Yes

**Notes (optional):** 

---
