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
were wrong because the team lacked expertise to recognise the flaw, that's still "technical
assumptions" — the broken mechanism is the unvalidated assumption. "Capability shortfall" is
reserved for cases where the team knew what to do but couldn't do it.

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
- A scope item was identified but the assumption about its value was wrong → **Technical
  assumptions**
- The scope was correct but the regulatory pathway to deliver it wasn't understood →
  **Regulatory & approvals**
- The scope was correct but the team couldn't deliver it → **Capability shortfall**
- The scope was correct but measurement systems to verify it were absent → **Data &
  measurement**

**Boundary rule with Technical assumptions:** Scoping is about *what* the project decided to
attempt. Technical assumptions is about *what the project believed would be true* about how
technology would perform within that scope. If the item was never on anyone's radar as
something that needed to be confirmed, it's poor scoping. If the item was identified but the
team adopted an untested value or method, it's technical assumptions.

**Examples from corpus:**
- Solar field expansion and road upgrades excluded from preliminary estimate
- Wharf structural condition not assessed before project planning
- Operation hours of resource recovery facility not defined during initial feasibility scope
- Development application submitted with exact final site dimensions instead of conservative buffer

---

### 2. Technical assumptions

**Definition:** A critical technical design choice, parameter value, or performance
expectation was adopted without adequate empirical validation for the specific project
conditions — including cases where the technology itself was insufficiently mature for the
deployment context. Reality differed from assumption.

**The broken mechanism:** The validation step was absent or inadequate. The project relied on
unverified beliefs about how technology, equipment, or systems would perform.

**Scope note:** This category includes technology readiness and maturity misjudgements —
cases where a technology was committed to at a stage of development, market availability, or
standards maturity insufficient for the project's requirements. The PM question is the same
family: "Has this been proven in a context relevant to this project?"

**PM due diligence questions:**
1. Has each critical technical parameter been validated against site-specific or
   application-specific evidence?
2. Are design values based on tested data from comparable conditions, or on generic
   literature, international benchmarks, or manufacturer claims?
3. Has the technology been deployed at this scale, in this climate, and in this market before?
4. What is the actual TRL for this specific application (not the headline TRL)?
5. Are performance claims independently verified, or do they rely on vendor assertions?
6. Where technology is immature, what is the fallback if it doesn't perform?

**What belongs here:**
- Equipment sized using literature values instead of site-specific data (feedstock analysis,
  solar irradiance, wind profiles, load patterns)
- Performance assumptions based on international studies not validated locally
- Hardware specifications incompatible with actual operating conditions (temperature,
  humidity, voltage, frequency)
- Technology treated as mature when specific variants or applications remained unproven
- Technology deployed before cost curves, supply chains, or standards were ready
- Component interactions assumed to work without end-to-end testing
- Lab or pilot performance extrapolated to field scale without validation

**What does NOT belong here:**
- The parameter was never identified as something to validate → **Poor scoping**
- The technology assumption was correct but the regulatory pathway wasn't → **Regulatory &
  approvals**
- The business case assumption (demand, price, offtake) was wrong → **Commercial & market**
- The measurement system to verify performance was inadequate → **Data & measurement**
- Two separately-validated systems failed at their interface due to coordination gaps →
  **Coordination & stakeholders** (if the failure was organisational) or re-examine whether
  the interface specification was actually an unvalidated assumption (if so, it stays here)

**Boundary rule with Poor scoping:** If the item was identified in scope but the team adopted
an untested value, it's technical assumptions. If the item was never identified at all, it's
poor scoping.

**Boundary rule with Data & measurement:** If the flawed belief was about the technology's
performance characteristics, it's technical assumptions. If the flaw was in the project's
ability to observe, measure, or demonstrate outcomes (instrumentation, baselines,
methodology), it's data & measurement.

**Examples from corpus:**
- Digester and CHP equipment sized using literature values instead of actual feedstock analysis
- Home charging ratio assumption based on international studies not validated locally
- Polymer binder glass transition temperature below operating temperature
- Ice-based storage technology unproven at required deployment scale
- Communication standards for DER assets were not mature at project start
- Solar cell technology evolved faster than project scope anticipated

---

### 3. Regulatory & approvals

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
  **Technical assumptions**
- The regulatory pathway was mapped but the team couldn't navigate it → **Capability
  shortfall**

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

### 4. Commercial & market

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
- A technology didn't perform to the spec the business case assumed → **Technical
  assumptions** (the commercial failure is a consequence of the technical assumption failure)
- A regulatory change made the business model unviable → **Regulatory & approvals**
- A commercial counterparty couldn't be engaged or aligned → **Coordination & stakeholders**

**Boundary rule with Technical assumptions:** If the business case failed because a
technology parameter was wrong (e.g. capacity factor lower than modelled), classify by what
was broken. If the parameter was an unvalidated technical assumption, it's technical
assumptions — the commercial failure is the consequence. If the technology performed as
expected but the market conditions around it changed, it's commercial & market.

**Examples from corpus:**
- EV battery resale values lacked established market benchmarks
- MLF overestimation undermining project economics
- Customer willingness to pay for green hydrogen below production cost
- Competing grid-scale storage technologies drove prices below project's cost base

---

### 5. Capability shortfall

**Definition:** The project required skills, experience, organisational capacity, or
specialist resources that the delivery team or supply chain did not possess. The team knew
what needed to be done but couldn't do it, or didn't have the right people to recognise what
needed to be done.

**The broken mechanism:** Organisational or team capability was insufficient for the project's
requirements.

**PM due diligence questions:**
1. Does this proponent have a track record delivering projects of comparable complexity?
2. Are the required specialist skills available in-house or through confirmed subcontractors?
3. Is the team sized appropriately for the scope and timeline?
4. Has the proponent identified its own knowledge gaps and how it will address them?
5. Are key-person dependencies managed?

**What belongs here:**
- Team lacked specialist technical knowledge required for the project
- Organisation had no experience with projects of this type or scale
- Key personnel departed and couldn't be replaced
- Supply chain partner lacked capacity or expertise to deliver their component
- Proponent underestimated internal resource requirements
- Talent scarcity in the relevant technical domain

**What does NOT belong here:**
- The team had the skills but made a wrong technical assumption → **Technical assumptions**
- The team had the skills but the organisations couldn't coordinate → **Coordination &
  stakeholders**
- The team had the skills but the physical delivery plan was inadequate → **Execution &
  logistics**

**Coding rule reminder:** Classify based on what was broken, not why. If technical
assumptions were wrong because the team lacked the expertise to recognise the flaw, that's
still technical assumptions — the broken mechanism is the unvalidated assumption. Capability
shortfall is reserved for cases where the mechanism was directly the absence of required
capability, not cases where capability gaps contributed to another failure mode.

**Examples from corpus:**
- Small installer businesses lacked financial and operational capacity for concurrent jobs
- Proponent had no prior experience with hydrogen systems at this scale
- Vendor required additional months for gap analysis due to unfamiliarity with Australian context

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
- The team lacked skills to coordinate → **Capability shortfall**
- The coordination failure was actually about inadequate technical interface specification →
  **Technical assumptions** (if the interface parameters were wrong) or **Poor scoping**
  (if the interface was never identified)

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
- The project had good data but made wrong technical assumptions from it → **Technical
  assumptions**
- The project scoped its measurement needs incorrectly (never identified what data was
  needed) → **Poor scoping**
- The data problem was actually a commercial insight (customer behaviour different from
  assumed) → **Commercial & market** or **Technical assumptions** depending on the mechanism

**Boundary rule with Technical assumptions:** If the right data existed but the team used the
wrong methodology or wrong data for the context (method error), it's technical assumptions.
If the right data did not exist or could not be collected because the infrastructure was
absent or inadequate (availability error), it's data & measurement.

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
- The design itself was wrong → **Technical assumptions** or **Poor scoping**
- The team lacked skills to manage delivery → **Capability shortfall**
- A regulatory process delayed physical works → **Regulatory & approvals**
- A stakeholder or counterparty blocked site access → **Coordination & stakeholders**
- Supply chain disruption caused by an external shock (pandemic, geopolitical event) →
  classify here if the project should have buffered for foreseeable disruption; consider
  whether the record is better described as commercial & market if the shock fundamentally
  changed project viability rather than just delaying delivery

**Boundary rule with Capability shortfall:** Capability shortfall is about the team not
having the skills or knowledge. Execution & logistics is about the delivery plan being
inadequate even if the team was competent. "The team didn't know how to do X" = capability
shortfall. "The team knew how to do X but the plan didn't account for Y" = execution &
logistics.

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

| # | Failure mode | Mechanism (one sentence) |
|---|---|---|
| 1 | Poor scoping | Scope definition failed to capture what the project needed to deliver |
| 2 | Technical assumptions | Critical technical parameters adopted without adequate validation |
| 3 | Regulatory & approvals | Regulatory pathway unmapped, misunderstood, or underestimated |
| 4 | Commercial & market | Business case rested on unvalidated or unviable commercial conditions |
| 5 | Capability shortfall | Team or supply chain lacked required skills, experience, or capacity |
| 6 | Coordination & stakeholders | Parties who needed to work together weren't set up to do so |
| 7 | Data & measurement | Data infrastructure inadequate for design, verification, or operations |
| 8 | Execution & logistics | Delivery plan insufficient for the physical realities of implementation |

---

## Fields removed from v2 (with rationale)

| Former failure mode | Disposition | Rationale |
|---|---|---|
| design assumption failure | Dissolved → #1, #2 | Catch-all (20% of records); not a mechanism |
| technical underperformance | Dissolved → #2, others | Consequence, not mechanism (fails Test 1) |
| integration failure | Dissolved → #2, #6, others | Consequence/symptom depending on framing |
| schedule slippage | Dissolved → #3, #6, #8 | Consequence (fails Test 1) |
| cost overrun | Dissolved → #1, #8, others | Consequence (fails Test 1); 1.1% prevalence |
| data quality/measurement failure | Renamed → #7 | Kept; validated by bottom-up clustering |
| regulatory misfit | Merged → #3 | Kept with expanded scope |
| commercial/demand failure | Renamed → #4 | Kept |
| resource/capability shortfall | Renamed → #5 | Kept |
| governance/coordination failure | Merged → #6 | Kept with expanded scope |
