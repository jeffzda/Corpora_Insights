# Failure Mode Definitions — Taxonomy v3.0

**Status: Draft — subject to revision after empirical classification pass.**
**Date: April 2026**

---

## What is a failure mode?

A failure mode names the specific mechanism by which a project's capacity to deliver its
intended outcome was degraded. It names what broke or was absent — not what happened as a
result (consequence) and not why it was broken in some deeper organisational or political
sense (root cause).

**Failure mode vs consequence.** A consequence is an observable outcome — cost overrun,
schedule slippage, underperformance against spec. These are measures of damage, not
explanations. Test: "Could two projects exhibit this same outcome through completely
different mechanisms?" If yes, it's a consequence. Cost overrun, schedule slippage, and
technical underperformance all fail this test.

**Failure mode vs symptom.** A symptom is a mid-project observable that signals something
is wrong but doesn't identify what — contractor disputes, repeated design changes, missed
milestones. Test: "Does naming this tell you where in the project architecture the problem
sits?" Symptoms don't localise; failure modes do.

**Failure mode vs root cause.** A root cause explains why the failure mode was present —
organisational culture, incentive structures, politics, individual decisions. Test: "Could
this same mechanism appear in projects with completely different institutional and political
contexts?" If yes, you're at the right level. If you're naming a specific decision-maker's
motivation, you've gone too deep.

**Analogy:** In medical diagnosis, the failure mode is the pathology (arterial blockage),
not the symptom (chest pain), not the outcome (cardiac arrest), and not the root cause
(diet, genetics). A portfolio manager screens for pathologies before symptoms appear.

---

## Inclusion tests

Every category in this taxonomy must pass all four tests:

1. **Mechanism test.** Does it name a broken or absent mechanism, not a consequence, symptom,
   or root cause?
2. **Distinctiveness test.** If removed, could the remaining categories absorb its records
   without losing actionable information?
3. **Actionability test.** Does it point to a specific area of pre-funding due diligence? It
   should map to 3–6 PM questions that are substantially different from every other category.
4. **Prevalence test.** Does it capture at least ~5% of adverse records in a representative
   sample?

---

## Coding rule

Classify based on **what was broken**, not **why it was broken**. If technical assumptions
were wrong because the team lacked expertise to recognise the flaw, that's still "unvalidated
technical assumptions" — the broken mechanism is the unvalidated assumption. If the team knew
what to do but couldn't physically execute it, that's "execution & logistics".

---

## The 8 failure modes

### 1. Poor scoping

**Definition:** The project committed to a definition of what it would deliver — objectives,
boundaries, scale, requirements, constraints, success criteria — that was inadequate,
premature, or internally inconsistent. Critical scope items were not identified before design
was locked.

**The broken mechanism:** The scope definition process failed to capture what the project
actually needed to deliver or operate within.

**PM due diligence questions:**
1. How was the project scope determined? What feasibility work preceded it?
2. Have all physical, regulatory, and operational constraints been identified?
3. What site characterisation has been completed (geotechnical, environmental, grid, community)?
4. Have all required infrastructure interfaces been scoped (roads, utilities, grid connection)?
5. What would trigger a scope revision, and is there a mechanism for it?

**What belongs here:**
- Scope items omitted from estimates or designs (civil works, balance-of-plant, decommissioning)
- Site conditions not assessed before design (subsurface, structural, environmental)
- Operating parameters left undefined during feasibility (duty cycles, throughput, availability)
- Success criteria not defined or internally inconsistent
- Project scale chosen without evidence (e.g. 10MW when 2MW was the right proving point)

**What does NOT belong here:**
- A scope item was identified but the assumption about its value was wrong → **Unvalidated
  technical assumptions**
- The scope was correct but the regulatory pathway to deliver it wasn't understood →
  **Regulatory & approvals**
- The scope was correct but measurement systems to verify it were absent → **Data &
  measurement**
- The scope was correct but the delivery plan was inadequate → **Execution & logistics**

**Boundary rule with Unvalidated technical assumptions:** Scoping is about *what* the project
decided to attempt. Technical assumptions are about *what the project believed would be true*
about performance or parameters within that scope. If the item was never on anyone's radar as
something that needed to be confirmed, it's poor scoping. If the item was identified but the
team adopted an untested value, it's unvalidated technical assumptions.

**Examples from corpus:**
- Solar field expansion and road upgrades excluded from preliminary estimate
- Wharf structural condition not assessed before project planning
- Operation hours of resource recovery facility not defined during initial feasibility scope
- Development application submitted with exact final site dimensions instead of conservative buffer

---

### 2. Unvalidated technical assumptions

**Definition:** The team adopted technical assumptions — about technology performance,
component behaviour, design parameters, or empirical inputs — that were not validated for the
actual deployment context. The assumption may have been about whether a technology works here
(performance) or about the numerical inputs describing the situation (parameters). Both are
the same underlying mechanism: reliance on unverified technical beliefs.

**The broken mechanism:** Technical assumptions were adopted without adequate validation for
the specific site, scale, climate, feedstock, or operating context. The project relied on
manufacturer claims, lab results, overseas benchmarks, literature values, or adjacent-context
data without field-testing or local verification.

**Why this is one category:** The boundary between "the technology didn't perform" and "the
design numbers were wrong" is a matter of framing, not mechanism. A PV plant with soiling
losses 3× the design assumption is simultaneously an unvalidated performance claim (the
panels didn't perform) and an unvalidated parameter (the soiling rate was borrowed from the
wrong climate). The PM due diligence is the same: "Have we verified that our technical
beliefs hold in this specific context?"

**PM due diligence questions:**
1. Has each critical performance claim been independently tested under conditions that match
   the actual deployment context?
2. Are performance expectations based on lab data, manufacturer claims, or real-world field
   evidence from comparable conditions?
3. Has the technology been deployed at this scale, in this climate, and with this feedstock
   before?
4. What is the actual TRL for this specific application (not the headline TRL)?
5. Are all critical numerical inputs — cost benchmarks, performance parameters, physical
   constants, demand profiles — derived from sources that match the actual context?
6. Are design values based on site-specific measurements or on generic literature?
7. Where technology is immature or unproven at scale, what is the fallback?

**What belongs here:**
- Lab or pilot performance extrapolated to field scale without validation
- Hardware specifications incompatible with actual operating conditions (temperature,
  humidity, voltage, frequency)
- Technology treated as mature when specific variants or applications remained unproven
- Technology deployed before cost curves, supply chains, or standards were ready
- Algorithm or control system performance assumed without field testing
- Component degradation or reliability assumptions not validated for local conditions
- Equipment sized using literature values instead of site-specific data (feedstock analysis,
  solar irradiance, wind profiles, load patterns)
- Cost parameters adopted from international benchmarks without local validation
- Soiling rates, temperature coefficients, or degradation curves from different climates
- Manufacturer fuel curves not validated against site-specific operational data
- Load profiles or demand patterns assumed from international studies

**What does NOT belong here:**
- Two separately-functional systems failed at their interface → **Unvalidated integration**
- The assumption was never identified as something to validate → **Poor scoping**
- The business case assumption was about commercial viability, not technical performance →
  **Commercial & market**
- The measurement system to verify performance or collect data was inadequate → **Data &
  measurement**
- The work was attempted and done badly (execution quality, not wrong beliefs) →
  **Execution & logistics**

**Boundary rule with Poor scoping:** Scoping is about *what* the project decided to attempt.
Technical assumptions are about *what the project believed would be true* within that scope.
If the item was never on anyone's radar as something that needed to be confirmed, it's poor
scoping. If the item was identified but the team adopted an untested value or unverified
performance claim, it's unvalidated technical assumptions.

**Boundary rule with Unvalidated integration:** If a single component or technology failed to
meet its own specification or was designed with wrong parameters, it's unvalidated technical
assumptions. If two separately-functioning components failed at their interface, it's
unvalidated integration. This category involves one system's assumptions; integration involves
at least two systems' interaction.

**Boundary rule with Data & measurement:** If the right data existed but the team used wrong
values from the wrong context (method error — wrong soiling rates, wrong cost benchmarks),
it's unvalidated technical assumptions. If the right data did not exist because the
measurement infrastructure was absent or inadequate (availability error), it's data &
measurement.

**Boundary rule with Execution & logistics:** If the work was designed based on wrong beliefs
about what would work (wrong assumptions about performance, parameters, or context), it's
unvalidated technical assumptions. If the work was attempted and done badly (construction
defects, supply chain mismanagement, workforce shortfalls), it's execution & logistics. The
test: "Was the problem in the plan's beliefs, or in the plan's execution?"

**Examples from corpus:**
- Copper metallisation performance unvalidated at commercial scale
- Grid-forming inverter performance unvalidated for transmission applications
- Heat pump startup controls not validated for cold ambient conditions
- Perovskite stability thresholds for moisture and field strength unvalidated
- Laboratory fabrication method assumed viable at commercial scale
- Soiling rates assumed from Middle East data without local validation
- Transport cost assumptions based on US benchmarks not validated locally
- PV module temperature coefficients unvalidated for site conditions
- Manufacturer fuel curves not validated against site-specific operational data
- Generic soiling model assumptions invalid for Australian conditions

---

### 3. Unvalidated integration

**Definition:** The team assumed that two or more separately-functioning components, systems,
standards, or processes would work correctly in combination, but the interface, interaction,
or compatibility was never validated before the integrated system was committed to or
deployed.

**The broken mechanism:** Interface or interaction behaviour between components was assumed,
not verified. The individual pieces may each work in isolation; the failure is at the
boundary between them.

**Note:** This is distinct from the dissolved "system integration failure" from v2. That was
framed as a consequence ("the systems didn't work together"). This category is framed as a
mechanism ("the interface validation step was absent"). The broken thing is the missing
validation, not the observable outcome.

**PM due diligence questions:**
1. Have all critical system interfaces — hardware-to-hardware, software-to-hardware, and
   standard-to-standard — been validated together under realistic operating conditions?
2. Are there proprietary or vendor-locked interfaces that prevent third-party integration?
3. Has end-to-end testing been conducted, or only component-level testing?
4. Are communication protocols and control interfaces confirmed compatible?

**What belongs here:**
- Hardware from different vendors with incompatible operational characteristics
- Proprietary architectures preventing third-party control
- Communication protocols or API standards immature or conflicting
- Control system interactions not validated before commissioning
- SCADA/BMS/inverter combinations untested as integrated system
- Protection settings or trip configurations not coordinated across fleet

**What does NOT belong here:**
- A single component failed to meet its own specification → **Unvalidated technical
  assumptions**
- The interface was never identified as a scope item → **Poor scoping**
- The integration failure was caused by organisational coordination gaps between parties →
  **Coordination & stakeholders**

**Boundary rule with Unvalidated technical assumptions:** Technical assumptions involve one
system's performance or parameters being wrong. Unvalidated integration requires at least two
systems whose *interface* was not validated. If a battery doesn't hold charge, that's
technical assumptions. If a battery and inverter can't communicate, that's integration.

**Boundary rule with Coordination & stakeholders:** If the integration failure was caused by
technical interface specifications being wrong or absent, it's unvalidated integration. If
it was caused by organisations failing to coordinate (e.g., each party built to different
standards because nobody managed the interface), it could be either — classify by whether the
primary gap was technical (interface spec) or organisational (governance of the interface).

**Examples from corpus:**
- Battery-inverter communications protocols immature, unvalidated at scale
- PPC-inverter combination performance not validated in hardware
- AS4777.2 anti-islanding functions incompatible with inverter-formed grid impedance
- Hybrid microgrid control interactions not validated pre-commissioning
- BMS-inverter compatibility assumed without pre-dispatch testing

---

### 4. Regulatory & approvals

**Definition:** The project entered execution without a viable, well-understood pathway
through the relevant regulatory, permitting, standards, or compliance landscape. The
complexity, duration, novelty, or sequencing of statutory processes was not adequately
accounted for.

**The broken mechanism:** The regulatory pathway was unmapped, misunderstood, or
underestimated.

**PM due diligence questions:**
1. What approvals, permits, and compliance certifications are required?
2. What is the sequencing and critical path through regulatory processes?
3. Are there novel or multi-jurisdiction requirements with no established precedent?
4. Have grid connection standards and processes been confirmed for this technology type?
5. What regulatory changes are foreseeable, and how resilient is the project to them?

**What belongs here:**
- Multiple overlapping regulatory frameworks not coordinated into a single pathway
- Grid connection standards inadequate for novel technology configurations
- Regulatory processes initiated too late (e.g. ring-fencing waiver after design finalised)
- Land tenure complexity not mapped upfront (mining lease, pastoral lease, native title)
- Compliance requirements underestimated for novel or critical grid assets
- Standards or certification pathways not yet established for the technology
- Policy or rule changes mid-project that invalidate prior assumptions

**What does NOT belong here:**
- A commercial counterparty or community group blocked progress → **Coordination &
  stakeholders** (unless the blocking party is a statutory authority)
- The regulatory environment was understood but the technology couldn't comply →
  **Unvalidated technical assumptions**
- The regulatory pathway was mapped but the team couldn't execute against it → **Execution
  & logistics**

**Boundary rule with Coordination & stakeholders:** Classify by the blocking entity. If a
government body, regulator, or network operator with statutory powers is the party whose
process was underestimated, it's regulatory & approvals. If a private party, community, or
commercial counterparty whose cooperation was needed is the blocking party, it's coordination
& stakeholders. Where both apply (e.g. Indigenous land use agreement requiring both
Traditional Owner consent and government registration), classify by the dominant blocking
mechanism.

**Examples from corpus:**
- Five separate legislative frameworks across Commonwealth and State not coordinated
- NER connection process lacked procedures for hybrid wind/solar/storage on weak networks
- System strength remediation requirements not anticipated during project planning
- Electrolyser vendors lacked Australian compliance expertise, adding 6 months

---

### 5. Commercial & market

**Definition:** The project's business case rested on commercial or market conditions —
demand, price, offtake, cost trajectory, revenue model, competitor landscape — that proved
wrong, were never adequately validated, or changed materially during delivery.

**The broken mechanism:** The commercial pathway was unviable or unvalidated.

**PM due diligence questions:**
1. Does the revenue model depend on market conditions that demonstrably exist today?
2. Are there competing technologies or market shifts that could undermine the economics?
3. Is there demonstrated customer or offtaker demand at the assumed price point?
4. How sensitive is the business case to input cost changes?
5. What happens to the commercial case if the project is delayed by 12–24 months?

**What belongs here:**
- Business case assumptions (demand, price, cost) invalidated by market reality
- Revenue model dependent on market conditions that didn't materialise
- Customer demand insufficient or customer behaviour different from assumptions
- Competing technologies made the project's economics unviable
- Offtake agreements or commercial arrangements not secured
- Input cost changes (commodity prices, exchange rates) undermining viability

**What does NOT belong here:**
- A technology didn't perform to spec, or design parameters (costs, yields) were borrowed
  from the wrong context → **Unvalidated technical assumptions** (the commercial failure is
  a consequence of the technical validation gap)
- A regulatory change made the business model unviable → **Regulatory & approvals**
- A commercial counterparty couldn't be engaged or aligned → **Coordination & stakeholders**

**Boundary rule with Unvalidated technical assumptions:** If the business case failed because
a technology didn't perform or a design parameter was wrong, classify by the broken mechanism
(technical assumptions). The commercial failure is the consequence. If the technology
performed as expected and the parameters were correct but market conditions changed, it's
commercial & market.

**Scope note:** This category also absorbs records where the unvalidated assumption was
specifically about commercial viability — demand levels, customer behaviour, revenue
stacking, price signals — rather than technical performance. The PM question "Does the
market context hold?" belongs here.

**Examples from corpus:**
- EV battery resale values lacked established market benchmarks
- MLF overestimation undermining project economics
- Customer willingness to pay for green hydrogen below production cost
- Competing grid-scale storage technologies drove prices below project's cost base

---

### 6. Coordination & stakeholders

**Definition:** Parties who needed to work together — whether within the project (internal
governance), between project organisations (inter-party coordination), or with external
communities and counterparties (stakeholder engagement) — were not adequately aligned,
engaged, or coordinated. Decision rights, responsibilities, incentives, or engagement
timelines were unclear or insufficient.

**The broken mechanism:** The governance, coordination, or engagement structure was absent
or inadequate for the number and complexity of parties involved.

**Scope note:** This category intentionally covers internal governance, inter-organisational
coordination, and external stakeholder engagement as a single failure mode. Analysis showed
that splitting these into separate categories would leave each below the 5% prevalence
threshold, and the PM due diligence questions are the same family: "Are all parties who need
to work together actually set up to work together?"

**PM due diligence questions:**
1. Have all parties whose cooperation is required been identified?
2. Are decision rights and escalation pathways clear at every interface?
3. Do all parties have aligned incentives, or are conflicts identified and managed?
4. Have external stakeholders been engaged early enough for meaningful consultation?
5. Is the governance structure adequate for the number and complexity of parties?
6. Have commercial agreements and data-sharing arrangements been secured?

**What belongs here:**
- Internal governance: unclear decision rights, inadequate oversight, unresolved reporting
  lines, accountability gaps
- Inter-organisational: data sharing failures, access disputes, scope change coordination,
  technology handoff problems between parties
- External stakeholders: community engagement too late, landholder negotiations delayed,
  customer recruitment insufficient, commercial counterparty misalignment
- Consortium-specific: partner incentives misaligned, IP ownership disputes, contribution
  imbalances

**What does NOT belong here:**
- A statutory authority or regulator blocked progress → **Regulatory & approvals** (unless
  the issue was the project's failure to engage the regulator, not the regulatory process
  itself)
- The coordination failure was actually about inadequate technical interface specification →
  **Unvalidated integration** (if the interface was identified but not validated) or **Poor
  scoping** (if the interface was never identified)

**Boundary rule with Regulatory & approvals:** Classify by the blocking entity. Statutory
authority = regulatory & approvals. Private party, community, or commercial counterparty =
coordination & stakeholders. See Regulatory & approvals entry for detail.

**Examples from corpus:**
- Lease acquisition engagement with Traditional Owners delayed until formal application stage
- Site host agreements not prioritised as critical path dependency
- Meter Data Provider lacked commercial incentive to support third-party integration
- Multiple competing API standards developed by different parties without convergence

---

### 7. Data & measurement

**Definition:** The project could not generate, access, or rely on data of sufficient
quality, resolution, coverage, or timeliness to support design decisions, performance
verification, or operational control. The data infrastructure, collection protocols, or
governance frameworks were inadequate or not established before they were needed.

**The broken mechanism:** The data collection, measurement, or governance system was absent
or insufficient for the project's information needs.

**PM due diligence questions:**
1. Is the monitoring and measurement infrastructure in place and validated?
2. Is baseline data of sufficient duration and quality to support design decisions?
3. Are data governance protocols (ownership, quality, access, retention) established?
4. Are measurement standards and methodologies defined and appropriate?
5. Is the data pipeline robust (redundancy, validation, granularity)?

**What belongs here:**
- Monitoring infrastructure deployed too late or at insufficient granularity
- Baseline data inadequate for design or verification (too short, too sparse, unrepresentative)
- Data governance absent — no defined protocols for quality, ownership, or access
- Measurement systems producing corrupted or unreliable data (e.g. GPS sync failures)
- Training data contaminated by unfiltered exogenous variables
- Cost or performance categorisation inconsistent across project parties
- Single points of failure in data architecture causing data loss

**What does NOT belong here:**
- The project had good data but used wrong values from the wrong context → **Unvalidated
  technical assumptions**
- The project scoped its measurement needs incorrectly (never identified what data was
  needed) → **Poor scoping**
- The data problem was actually a commercial insight (customer behaviour different from
  assumed) → **Commercial & market**

**Boundary rule with Unvalidated technical assumptions:** If the right data existed but the
team used wrong values from a different context (method error — wrong soiling rates, wrong
cost benchmarks), it's unvalidated technical assumptions. If the right data did not exist or
could not be collected because the infrastructure was absent or inadequate (availability
error), it's data & measurement.

**Boundary rule with Poor scoping:** If the project never identified that certain data would
be needed, that's poor scoping. If the project identified the data need but the measurement
system was inadequate to fulfil it, that's data & measurement.

**Examples from corpus:**
- SCADA systems configured to log at 5-10 minute intervals, insufficient for 5-minute forecasting
- PMU devices deployed without GPS lock validation, allowing silent data corruption
- Data governance framework not established before project start
- Proponents used different cost categorisation methods without standardised definitions

---

### 8. Execution & logistics

**Definition:** The project had a sound design and understood its requirements, but the plan
for physically delivering the work — construction management, supply chain procurement,
workforce deployment, site logistics, quality assurance — was inadequate for the realities
of implementation.

**The broken mechanism:** The delivery and implementation plan was insufficient for the
physical demands of the project.

**PM due diligence questions:**
1. Is the construction or installation methodology proven for this context?
2. Are supply chain risks identified, and are critical-path inputs secured or buffered?
3. Is workforce capacity adequate, including for remote or concurrent deployment?
4. Are site logistics feasible (access, transport, accommodation, weather windows)?
5. Are quality assurance and inspection processes defined for construction?
6. Are long-lead items and critical spares identified and pre-ordered?

**What belongs here:**
- Construction or assembly quality defects not caught during delivery
- Supply chain delays, supplier insolvency, or single-supplier dependency
- Workforce capacity insufficient for delivery schedule (too few installers, too few
  concurrent crews)
- Site logistics failures (road access, camp capacity, equipment transport)
- Long-lead procurement not initiated early enough
- Quality assurance gaps during physical delivery

**What does NOT belong here:**
- The design itself was wrong → **Unvalidated technical assumptions** or **Poor scoping**
- A regulatory process delayed physical works → **Regulatory & approvals**
- A stakeholder or counterparty blocked site access → **Coordination & stakeholders**
- Supply chain disruption caused by an external shock (pandemic, geopolitical event) →
  classify here if the project should have buffered for foreseeable disruption; consider
  whether the record is better described as commercial & market if the shock fundamentally
  changed project viability rather than just delaying delivery

**Scope note:** This category also absorbs records where the primary failure was that the
team or supply chain lacked the capacity, workforce, or specialist resources to physically
execute the delivery plan. The former "capability shortfall" category (2.9% prevalence,
below threshold) is absorbed here when the capability gap manifested as a delivery execution
problem. Where capability gaps caused wrong technical assumptions, classify by the broken
assumption instead.

**Tiebreaker with Unvalidated technical assumptions:** If the work was attempted and done
badly, it's execution & logistics. If the work was designed based on wrong beliefs about what
would work, it's unvalidated technical assumptions. The test: "Was the problem in what they
believed, or in how they carried it out?"

**Examples from corpus:**
- Sales targets exceeded realistic installation capacity (700 committed, 250 delivered)
- Assembly quality defects not caught until commissioning
- Critical spare parts not procured before commissioning began
- Remote site installations scheduled without verifying accommodation capacity
- International BESS supply chain lead times not adequately buffered

---

## Residual: no material failure stated

Records where the narrative describes a positive observation, a successful outcome, or a
neutral factual report with no identifiable adverse delivery event retain the existing label
**"no major failure stated"**. This is not a failure mode — it is the absence of one.
Approximately 27% of records (4,555) carry this label.

---

## Summary

| # | Failure mode | Mechanism (one sentence) | PM question |
|---|---|---|---|
| 1 | Poor scoping | Scope definition failed to capture what the project needed | "Was the full scope confirmed before design was locked?" |
| 2 | Unvalidated technical assumptions | Technical beliefs about performance or parameters not validated for context | "Have we verified our technical assumptions for this context?" |
| 3 | Unvalidated integration | Interfaces between systems never validated | "Do these work together?" |
| 4 | Regulatory & approvals | Regulatory pathway unmapped or underestimated | "Is the regulatory pathway mapped and buffered?" |
| 5 | Commercial & market | Business case rested on unvalidated commercial conditions | "Does the market context hold?" |
| 6 | Coordination & stakeholders | Parties who needed to work together weren't set up to | "Are all parties set up to work together?" |
| 7 | Data & measurement | Data infrastructure inadequate for design or verification | "Is the data infrastructure in place?" |
| 8 | Execution & logistics | Delivery plan insufficient for physical realities | "Is the delivery plan robust?" |

---

## Fields removed from v2 (with rationale)

| Former failure mode | Disposition | Rationale |
|---|---|---|
| design assumption failure | Dissolved → #1, #2 | Catch-all (20%); not a mechanism |
| technical underperformance | Dissolved → #2, others | Consequence, not mechanism |
| integration failure | Dissolved → #3, #6, others | Reframed as mechanism (#3) |
| schedule slippage | Dissolved → #4, #6, #8 | Consequence (fails mechanism test) |
| cost overrun | Dissolved → #1, #8, others | Consequence; 1.1% prevalence |
| data quality/measurement failure | Renamed → #7 | Validated by clustering |
| regulatory misfit | Merged → #4 | Kept with expanded scope |
| commercial/demand failure | Merged → #5 | Kept; absorbs commercial viability sub-cluster |
| resource/capability shortfall | Dissolved → #8, #1, others | 2.9% prevalence (below threshold) |
| governance/coordination failure | Merged → #6 | Kept with expanded scope |
