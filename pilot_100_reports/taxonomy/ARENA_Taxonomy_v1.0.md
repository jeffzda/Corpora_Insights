# ARENA Knowledge Insight Taxonomy v1.0
**Enduring tagging standard for ARENA knowledge bank insights**

Adapted from CareerVault Taxonomy v3.0.
Designed for durable retrieval of technology insights across renewable energy R&D, deployment, and commercialisation.

---

## Purpose

This taxonomy makes technology insights from ARENA knowledge bank PDFs retrievable by:
- technology domain
- insight type (what kind of finding)
- deployment stage (how mature the technology is)
- impact type (what changed or was demonstrated)
- transferability signals (what makes this insight generalisable)

The **unit of capture** is a discrete insight — a finding, barrier, enabler, lesson, or recommendation that is non-obvious and reusable beyond the specific project.

---

## Design principles

1. **Tags are retrieval pivots.** Use them only for concepts likely to be queried across the corpus.
2. **Fields carry specificity; tags carry abstraction.** Tag `#barrier_identified`; field `barrier: grid connection approval delays caused by unclear AEMO processes`.
3. **Use the smallest tag set that preserves meaning.** 3–5 tags per insight record.
4. **Consistency beats cleverness.** Use canonical tags only. Do not invent ad hoc tags.
5. **The insight must be non-trivial.** If a finding is generic or expected, it does not warrant a standalone record.

---

## Record eligibility

Create a standalone insight record when one or more of these is true:
- A quantified performance or cost outcome was demonstrated
- A barrier to deployment, scale, or commercialisation was identified
- An unexpected technical or operational failure was documented
- A design, process, or operating approach was shown to work at scale
- A recommendation was made that applies beyond the specific project
- A market, regulatory, or financing insight was surfaced

---

## Canonical record schema

### Required fields
- `record_id` — unique identifier (e.g. ARENA-INS-0001)
- `source_title` — title from ARENA knowledge bank
- `source_type` — one of: Reports, Lessons, Milestones, Insights, Guides, Other
- `publish_date` — from CSV
- `category` — from CSV (e.g. Battery storage, Hydrogen energy)
- `project_name` — from CSV
- `project_status` — Current / Past
- `year` — from CSV
- `what` — one sentence: what finding, outcome, or lesson was captured
- `evidence` — the specific data point, quote, or observation that grounds the insight
- `outcome` — one sentence: what this means for the field, sector, or future projects
- `tags` — 3–5 canonical tags (see below)

### Strongly recommended fields
- `technology` — specific technology (e.g. BESS, PEM electrolyser, bifacial PV)
- `scale` — project scale (e.g. 50 MW / 100 MWh, 1 MW pilot)
- `geography` — state or region (e.g. SA, WA, Queensland)
- `tradeoff` — key tension, if any (format: `X vs Y`)
- `barrier` — if a barrier is identified, describe it in plain language
- `enabler` — if an enabler is identified, describe it in plain language
- `recommendation` — forward-looking guidance, if explicit in the source

### Optional fields
- `source_excerpt` — direct quote from the PDF supporting the insight
- `related_records` — IDs of related insight records
- `notes`

---

## Tag axes

### Tag count rule
Each record should have **3 to 5 tags**:
- exactly 1 technology-domain tag
- exactly 1 insight-type tag
- exactly 1 deployment-stage tag
- optional 1 impact-type tag
- optional 1 transferability tag

### Standard tag order
1. technology domain
2. insight type
3. deployment stage
4. impact type (optional)
5. transferability (optional)

---

## 1. Technology domain tags (mandatory: exactly one)

### `#battery_storage`
Grid-scale, behind-the-meter, or community battery systems (BESS, LDES, flywheel, etc.)

### `#hydrogen`
Green hydrogen production, storage, transport, export, and end-use (electrolysers, carriers, fuel cells, etc.)

### `#solar_pv`
Photovoltaic solar: utility-scale, commercial, distributed, manufacturing, and R&D

### `#solar_thermal`
Concentrated solar power (CSP), solar heat for industrial processes (SHIP), thermal storage

### `#wind`
Wind generation: onshore and offshore

### `#distributed_energy`
Distributed energy resources (DER): rooftop solar, home batteries, virtual power plants (VPP), dynamic operating envelopes (DOE), aggregation

### `#demand_response`
Demand flexibility, demand management, load shifting, smart tariffs, flexible demand programs

### `#electric_vehicles`
EV charging infrastructure, fleet electrification, V2G, heavy transport electrification

### `#bioenergy`
Bioenergy, biomethane, biogas, energy from waste, pyrolysis, hydrothermal processing

### `#renewables_industry`
Renewables for industrial processes: electrification of heat, green steel, green aluminium, industrial decarbonisation

### `#grid_stability`
System strength, inertia, frequency control, grid-forming inverters, oscillation management, ancillary services

### `#hybrid_systems`
Projects combining two or more of the above (e.g. solar + storage, hydrogen + renewables)

### `#pumped_hydro`
Pumped hydro energy storage (PHES)

---

## 2. Insight type tags (mandatory: exactly one)

### `#technical_performance`
A measured performance outcome: efficiency, capacity factor, yield, availability, degradation rate, system response time.
Use when specific performance data (with numbers) is the core finding.

### `#cost_finding`
A finding about capital cost (CAPEX), operating cost (OPEX), levelised cost, or economic viability.
Use when cost data or economic modelling is the core finding.

### `#barrier_identified`
An obstacle to deployment, commercialisation, scale, or operation that was documented.
Use when the finding is primarily about what prevented or constrained progress.

### `#enabler_identified`
A factor that facilitated deployment, scale, adoption, or performance.
Use when the finding is primarily about what made progress possible.

### `#lessons_learnt`
An operational or project management lesson: what went wrong, what was unexpected, what would be done differently.
Use for experiential findings that are not purely technical performance.

### `#innovation_demonstrated`
A novel technology, design, process, or approach that was proven to work.
Use when the finding centres on demonstrating something new.

### `#market_finding`
A finding about market conditions, commercial viability, customer or investor behaviour, or demand signals.

### `#regulatory_finding`
A finding about grid rules, standards, approval processes, policy settings, or regulatory barriers and enablers.

### `#environmental_finding`
A finding from LCA, emissions measurement, land use, water use, or environmental monitoring.

### `#best_practice`
A recommended design principle, operating standard, or process that has been validated and is replicable.

### `#recommendation`
A forward-looking guidance statement explicitly directed at industry, policy, or future projects.
Use when the source text explicitly recommends an action or approach.

---

## 3. Deployment stage tags (mandatory: exactly one)

### `#research`
Fundamental or applied research; lab-scale; proof-of-concept.

### `#feasibility`
Pre-feasibility or feasibility study; desktop or modelling work prior to physical deployment.

### `#pilot`
Pilot or demonstration scale; first-of-kind trials; limited deployment to prove concept in real conditions.

### `#commercial_scale`
Full commercial deployment; technology operating at scale in real market conditions.

---

## 4. Impact type tags (optional: one or two)

### `#cost_reduced`
Demonstrated or modelled cost reduction relative to baseline.

### `#risk_mitigated`
A risk was identified and managed, reducing project or technology risk.

### `#process_improved`
A workflow, installation process, operating procedure, or approval pathway was improved.

### `#capability_built`
New technical or organisational capability was developed.

### `#commercialisation_advanced`
A step toward commercial viability was demonstrated or enabled.

### `#barrier_removed`
A previously identified barrier was resolved or overcome.

### `#knowledge_gap_filled`
A previously unknown or uncertain aspect of technology performance or deployment was clarified.

### `#replication_enabled`
Findings are directly applicable to and usable by future projects.

---

## 5. Transferability tags (optional: exactly one)

### `#australia_first`
First-of-kind deployment or result in an Australian context.

### `#globally_leading`
Result or approach is at the global frontier of the technology.

### `#broadly_replicable`
Finding applies across many project types, sectors, or geographies — not specific to this project.

### `#policy_relevant`
Finding has direct implications for policy, regulation, standards, or grid rules.

### `#industry_benchmark`
Result sets a reference point for cost, performance, or approach that others can use.

---

## Tie-break rules

### `#barrier_identified` vs `#lessons_learnt`
- Use `#barrier_identified` when the finding is about a structural obstacle (regulatory, technical, market) that persists beyond this project.
- Use `#lessons_learnt` when the finding is about project execution: what the team would do differently.

### `#technical_performance` vs `#innovation_demonstrated`
- Use `#technical_performance` when established technology achieved a measured outcome.
- Use `#innovation_demonstrated` when novel technology or approach was proven.

### `#cost_finding` vs `#cost_reduced`
- `#cost_finding` is an insight type (core finding is about cost).
- `#cost_reduced` is an impact type (a cost reduction was the outcome).
- Use both together when appropriate.

### `#recommendation` vs `#best_practice`
- Use `#recommendation` when the source explicitly directs future actors to do something.
- Use `#best_practice` when the source documents an approach that was validated and is presented as a model.

---

## Canonical subject_matter vocabulary (field, not tag)

Use in the `technology` field for specificity:

**Battery storage:** BESS, LDES, grid-forming battery, community battery, V2G
**Hydrogen:** PEM electrolyser, alkaline electrolyser, capillary-fed electrolyser, ammonia, hydrogen powder (LOHC), green steel, DRI, hydrogen calcination
**Solar PV:** bifacial, silicon wafer, perovskite, floating solar, agrivoltaics, solar tracker, inverter, string inverter
**Solar thermal:** CSP, parabolic trough, solar tower, molten salt storage, SHIP
**DER/VPP:** DOE, aggregation, smart meter, DERMS, behind-the-meter
**EV:** BEV, heavy truck EV, electric bus, depot charging, V2G, DCFC
**Bioenergy:** pyrolysis, hydrothermal liquefaction (HTL), biomethane, biogas upgrading, syngas
**Grid:** grid-forming inverter, synchronous condenser, FCAS, virtual inertia, oscillation damping

---

## Change-control rules

### Rule 1: Do not add a new canonical tag casually
Add a new tag only if the concept recurs across at least 5 distinct projects, cannot be represented by existing tags, and is a credible future retrieval pivot.

### Rule 2: Prefer extending field vocabularies before tag vocabularies
If a new concept is topical, add it to `technology`, `barrier`, or `enabler` fields, not the tag set.

### Rule 3: Versioning
- Increment minor version for definition clarifications and field vocabulary additions.
- Increment major version for tag additions, removals, or renames.

---

## Calibration examples

### Example 1
Battery project achieves grid connection but faces 14-month AEMO approval delay.

```yaml
record_id: ARENA-INS-0001
source_title: "Origin - Mortlake Power Station Battery Project - Lessons Learnt No.1"
source_type: Lessons
category: Battery storage
what: Grid connection approval by AEMO took 14 months due to unclear technical requirements and multiple resubmission cycles.
evidence: "Project experienced three resubmission rounds for the connection application, each requiring updated simulation models."
outcome: Future BESS projects should budget 12–18 months for AEMO connection approval and engage early with technical consultants familiar with the process.
tags: [#battery_storage, #barrier_identified, #commercial_scale, #risk_mitigated, #policy_relevant]
technology: BESS
tradeoff: project timeline vs technical compliance rigour
barrier: AEMO connection approval process lacked clear upfront requirements, causing repeated resubmission
recommendation: Engage AEMO pre-lodgement consultation service before submitting connection application
```

### Example 2
Solar automated deployment reduces installation labour by 40%.

```yaml
record_id: ARENA-INS-0002
source_title: "5B Maverick Solar PV Automated Assembly & Deployment - Lessons Learnt 2"
source_type: Lessons
category: Solar energy
what: Automated solar panel pre-assembly (Maverick units) reduced on-site installation labour by ~40% compared to conventional methods.
evidence: "Site installation rate of 1.2 MW/day achieved with a crew of 8, versus 0.7 MW/day with 12 workers for conventional racking."
outcome: Automated assembly approaches are viable at commercial scale and offer significant labour cost reduction for utility solar.
tags: [#solar_pv, #technical_performance, #commercial_scale, #cost_reduced, #industry_benchmark]
technology: solar tracker, automated assembly
scale: ~10 MW deployment
```

### Example 3
EV heavy truck charging reveals grid capacity constraints at depot.

```yaml
record_id: ARENA-INS-0003
source_title: "Linfox - Heavy Truck Electrification Project - Lessons Learnt Report 1"
source_type: Lessons
category: Electric vehicles
what: Depot grid connection capacity was insufficient to support simultaneous overnight charging of the full electric truck fleet.
evidence: "Existing 400 kVA connection limited charging to 4 trucks simultaneously; full fleet requires 2.2 MVA."
outcome: Fleet electrification projects must conduct detailed network capacity assessments before procurement to avoid costly grid augmentation.
tags: [#electric_vehicles, #barrier_identified, #pilot, #risk_mitigated, #broadly_replicable]
technology: heavy truck EV, depot charging
barrier: existing grid connection capacity insufficient for fleet-scale overnight charging
recommendation: Conduct network capacity assessment and engage DNSP at earliest possible stage
```
