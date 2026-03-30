# CareerVault Taxonomy v3.0
**Enduring tagging standard for long-horizon career evidence**

## Purpose
CareerVault exists to make professional judgement, influence, and impact retrievable years later.
This taxonomy is designed for:
- durable use across roles, sectors, and LLM generations
- low tag entropy
- high retrieval quality for selection criteria, salary cases, performance reviews, board applications, and pattern analysis
- consistent tagging of "high-impact insights" rather than generic work logs

This file governs **both**:
1. the canonical tag set
2. the protocol for how records are normalized and tagged

---

## Design principles

1. **Tags are for durable retrieval pivots.**
   If a concept is likely to be queried years later, it may deserve a tag.
   If it is mainly contextual, local, or variable, it belongs in a field.

2. **Fields carry specificity; tags carry abstraction.**
   Tag: `#governance`
   Field: `tradeoff: governance integrity vs delivery momentum`

3. **Use the smallest tag set that preserves meaning.**
   Fewer, cleaner tags are better than exhaustive tagging.

4. **The unit of capture is the evidence record, not the meeting or task.**
   Record separate items only when they demonstrate judgement, influence, consequence, or meaningful capability.

5. **Level is about judgement altitude, not audience prestige.**
   A meeting with executives is not automatically `#directorlevel`.
   Tag the level at which you actually operated.

6. **Consistency beats cleverness.**
   Never invent ad hoc tags in weekly capture.
   Use canonical tags only.

---

## Record eligibility test
Create a standalone CareerVault evidence record when **one or more** of these is true:

- you made or materially shaped a consequential decision
- you identified, contained, or mitigated a meaningful risk
- you balanced competing priorities or constraints
- you advised above your formal level
- you designed or changed a process, governance arrangement, operating model, or framework
- you resolved a blocked, broken, or non-compliant situation
- you built capability in a person, team, or partner
- you created a narrative, framework, or concept that others adopted
- you progressed or protected value, continuity, governance integrity, or strategic direction

If none apply, keep the item in the weekly log but do not force a standalone evidence record.

---

## Canonical record schema

### Required fields
- `date`
- `organisation`
- `role`
- `what`
- `who`
- `outcome`
- `tags`

### Strongly recommended fields
- `how`
- `why`
- `tradeoff`
- `forum`
- `artifact_type`
- `project_or_initiative`
- `subject_matter`
- `impact_type`
- `decision_role`

### Optional fields
- `notes`
- `source_file`
- `source_excerpt`

---

## Required field definitions

### `what`
One sentence describing what happened or what you produced.

### `who`
Key stakeholders, decision-makers, counterparties, or affected parties.

### `outcome`
One sentence stating what changed, was protected, was clarified, or was progressed.
Do not leave this implicit.
If the final result is pending, state the immediate outcome anyway.

Examples:
- Proposal progressed to committee without normalising harmful precedent.
- Continuity of service was preserved pending procurement pathway.
- Executive reporting was simplified and better aligned to decision timeframes.

---

## Strongly recommended field definitions

### `how`
Method, reasoning, judgement, or approach used.

### `why`
Why the item mattered organisationally, strategically, financially, or reputationally.

### `tradeoff`
The key tension, if any, stated in plain language.

Format:
`tradeoff: X vs Y`

Examples:
- governance integrity vs delivery momentum
- innovation vs risk
- system integrity vs local convenience
- speed vs rigour
- short-term continuity vs procurement discipline

**Rule:** if `tradeoff` is populated and materially shaped the action, also apply `#tradeoff`.

### `forum`
Where the work was situated.
Use the controlled vocabulary below.

### `artifact_type`
What kind of output or intervention this was.
Use the controlled vocabulary below.

### `project_or_initiative`
Project, program, committee, review, investment, or initiative name.

### `subject_matter`
The substantive topic area.
Use the controlled vocabulary below where possible.

### `impact_type`
The main type of effect created.
Use one or two values from the controlled vocabulary below.

### `decision_role`
The functional position in the decision dynamic.

---

## Controlled field vocabularies

### `forum`
Use one value unless two are genuinely central.

- `team`
- `program`
- `executive`
- `committee`
- `board`
- `external_partnership`
- `cross_sector`
- `public`
- `one_to_one_advice`

### `artifact_type`
Use one primary value.

- `brief`
- `email`
- `meeting_paper`
- `governance_advice`
- `investment_advice`
- `decision_note`
- `operating_plan`
- `business_case`
- `aip`
- `ivp`
- `contract_variation`
- `review_summary`
- `workshop_design`
- `framework`
- `options_analysis`
- `communication`
- `presentation`

### `subject_matter`
This vocabulary is intentionally extensible, but do not add terms casually.
Use the nearest existing term unless a new one is truly necessary.

Seed vocabulary:
- `ai`
- `analytics`
- `data_governance`
- `data_infrastructure`
- `cybersecurity`
- `digital_platforms`
- `ip`
- `commercialisation`
- `investment_process`
- `public_funding`
- `procurement`
- `research_governance`
- `research_tools`
- `portfolio_oversight`
- `renewables`
- `storage`
- `hydrogen`
- `agriculture`
- `cross_rdc_collaboration`

### `impact_type`
Use one or two.

- `decision_enabled`
- `risk_mitigated`
- `precedent_protected`
- `governance_strengthened`
- `continuity_preserved`
- `process_improved`
- `strategy_clarified`
- `value_protected`
- `funding_progressed`
- `partnership_advanced`
- `capability_built`
- `issue_resolved`
- `narrative_reframed`

### `decision_role`
Use one or none.
- `decision_owner`
- `delegated_decision_maker`
- `executive_advisor`
- `governance_reviewer`
- `technical_authority`
- `strategist`
- `coordinator`
- `implementer`
- `advisor`


---

## Canonical tag axes

### Tag count rule
Each record should usually have **3 to 5 tags**:
- exactly 1 operating-level tag
- 1 primary capability-domain tag
- 1 primary judgement tag
- optional 1 secondary domain or judgement tag
- optional 1 trajectory tag

Do not exceed 5 tags unless there is a compelling reason.

### Standard tag order
For consistency, write tags in this order:
1. operating level
2. capability domain(s)
3. judgement tag(s)
4. trajectory tag

---

## 1. Operating level tags (mandatory: exactly one)

### `#operationallevel`
Execution within established frameworks, with limited discretion over direction or governance settings.

Use when:
- you delivered a required output
- you implemented an already-decided process
- you coordinated routine reporting or administration

Do not use when the record involves meaningful design, advisory judgement, or process shaping across a team or program.

### `#managerlevel`
Shaping how work is done across a project, stream, team, or program.

Use when:
- you designed an approach or workflow
- you coordinated multiple parties toward an outcome
- you improved a process or operating model
- you applied judgement over scope, sequencing, or implementation

### `#directorlevel`
Advising on, shaping, or protecting strategic, governance, investment, or organisational direction.

Use when:
- you influenced senior or executive decision-making
- you interpreted governance or policy with broader implications
- you framed strategy, priorities, or system-level tradeoffs
- you identified risks or precedents with organisation-level implications

### `#executivelevel`
Making or directly shaping enterprise-level direction, institutional commitments, or board/executive decisions.

Use sparingly.
Only use when your role in the record genuinely operated at that altitude, not merely because executives were present.

---

## 2. Capability-domain tags (choose 1; max 2)

### `#governance`
Oversight, accountability, compliance, probity, decision rights, and process integrity.

### `#strategy`
Direction-setting, prioritisation, framing, future positioning, or shaping organisational choices.

### `#investment`
Assessment, progression, governance, structuring, or value-for-money judgement relating to investment decisions.

### `#portfolio`
Oversight or coordination across multiple projects, initiatives, or funding streams.

### `#delivery`
Execution, implementation, continuity, or getting important work across the line.

### `#contracts`
Variations, procurement pathways, commercial terms, and formal funding or service instruments.

### `#technical`
Use of specialist technical knowledge, including domain expertise, system logic, or technical feasibility.

### `#data`
Data governance, data infrastructure, analytics, interoperability, stewardship, or information architecture.

### `#commercialisation`
Translation of outputs toward business, industry, licensing, or market-facing value.

### `#policy`
Interpretation or application of formal policies, agreements, frameworks, or rules.

### `#peopleleadership`
Leading, directing, coaching, or building the capability of people, teams, or partners.

### `#partnerships`
Building, repairing, or structuring relationships across organisations, groups, or coalitions where the relationship itself materially matters.

---

## 3. Judgement tags (choose 1; max 2)

### `#advice`
Providing expert counsel that another person or body relies on to think, decide, or act.

Use when the core value was the guidance itself.

### `#influence`
Shaping decisions, framing, or outcomes above or beyond your formal authority.

Use when your input materially moved the position, direction, or action of others.

### `#decisionmaking`
Reaching, recommending, or materially shaping a consequential choice under uncertainty or ambiguity.

Use when a decision was central, not incidental.

### `#duediligence`
Scrutinising a proposal, project, partner, or arrangement before commitment in order to identify risks, gaps, or non-compliance.

### `#tradeoff`
Balancing materially competing priorities or constraints.

Use only when the tension mattered to the substance of the record.
Always pair with a populated `tradeoff` field.

### `#problemsolving`
Diagnosing and resolving a blocked, broken, delayed, non-compliant, or otherwise stuck situation.

### `#analysis`
Applying structured reasoning, evidence, logic, or quantitative assessment to reach a defensible position.

### `#design`
Designing a framework, model, process, template, architecture, or practical structure that others will use.

### `#changemanagement`
Changing how an organisation, program, team, or process operates.

Use when the change itself is central, not merely a consequence.

### `#negotiation`
Reaching or progressing agreement on terms, scope, conditions, roles, or pathways with other parties.

### `#evaluation`
Assessing outcomes, effectiveness, benefit realisation, or whether something worked.

### `#thoughtleadership`
Originating or articulating a framing, concept, or point of view that others adopt, build on, or use to guide action.

### `#riskmanagement`
Identifying, assessing, containing, or mitigating financial, legal, operational, reputational, or strategic risk.

### `#peopledevelopment`
Building the capability of another person or group through coaching, mentoring, supervision, support, or developmental guidance.

Use when the developmental effect is central and evidenced.

---

## 4. Trajectory tags (optional: choose 0 or 1)

Trajectory tags are for long-term career narrative and transferability.
Use sparingly.

### `#crosssector`
Work that bridges sectors, institutions, or contexts in a way that supports transferability of your capability.

### `#publicgovernance`
Work demonstrably relevant to public-sector governance, public funding, public accountability, or formal public decision systems.

### `#datainfrastructure`
Work demonstrably relevant to large-scale data systems, interoperability, repositories, or infrastructure-like information assets.

### `#ai`
Work materially related to AI strategy, AI governance, AI adoption, AI tools, or AI-enabled systems.

### `#renewables`
Work with a credible and defensible line of relevance to the renewable energy transition or adjacent energy-system capability.

Do not use casually.
Use only when you could defend the relevance in an interview.

### `#researchtranslation`
Work bridging research activity and practical, commercial, policy, or industry use.

### `#sectorvisibility`
Work that builds profile, reputation, or recognised external standing in a target sector or field.

---

## Tagging decision protocol

Apply tags in this sequence.

### Step 1: determine operating level
Ask:
"At what altitude did the judgement operate?"

### Step 2: choose the primary capability domain
Ask:
"What enduring professional capability would I want this found under in five years?"

### Step 3: choose the primary judgement tag
Ask:
"What kind of judgement was most central to the value of this record?"

### Step 4: choose one optional secondary tag
Add only if it independently improves future retrieval.

### Step 5: choose one optional trajectory tag
Add only if the record genuinely supports future positioning or transferability.

---

## Tie-break rules

### `#advice` vs `#influence`
- Use `#advice` when the value was the counsel.
- Use `#influence` when the value was the effect on others' thinking or action.
- Use both only when both are clearly central.

### `#decisionmaking` vs `#advice`
- Use `#decisionmaking` when the record turned on a consequential choice.
- Use `#advice` when the record was mainly about informing another person's choice.
- Use both if you both advised and materially shaped the decision outcome.

### `#analysis` vs `#duediligence`
- Use `#analysis` for general structured reasoning.
- Use `#duediligence` for pre-commitment scrutiny of a proposal, partner, or arrangement.

### `#strategy` vs `#design`
- Use `#strategy` when the main value was direction or prioritisation.
- Use `#design` when the main value was constructing a practical mechanism, framework, or template.

### `#governance` vs `#policy`
- Use `#governance` for oversight, probity, decision rights, and institutional integrity.
- Use `#policy` when the substance turned on reading, applying, or interpreting a rule or agreement.

### `#delivery` vs `#portfolio`
- Use `#delivery` for implementation and getting work done.
- Use `#portfolio` when the record concerns coordination or oversight across multiple initiatives or streams.

### `#peopleleadership` vs `#peopledevelopment`
- Use `#peopleleadership` as the capability domain when leading or coordinating people is central.
- Use `#peopledevelopment` as the judgement tag when the developmental act itself is the evidence.

### `#riskmanagement` vs `#tradeoff`
- Use `#riskmanagement` when risk identification or mitigation was central.
- Use `#tradeoff` when balancing competing priorities was central.
- Use both when both clearly matter.

---

## What should NOT usually be tags

These are usually better captured through fields or prose, not canonical tags:
- meetings
- writing
- correspondence
- reporting
- review
- executiveengagement
- boardlevel

Why:
- they describe channel, format, or venue
- they create tag clutter
- they are often recoverable from fields or source text

Represent them instead through:
- `forum`
- `artifact_type`
- `what`
- `outcome`

---

## Legacy alias map
Use this to convert older records to the canonical standard.

### Direct carry-over (same meaning; keep as-is if canonical)
- `#governance -> #governance`
- `#strategy -> #strategy`
- `#delivery -> #delivery`
- `#contracts -> #contracts`
- `#analysis -> #analysis`
- `#decisionmaking -> #decisionmaking`
- `#problemsolving -> #problemsolving`
- `#advice -> #advice`
- `#influence -> #influence`
- `#changemanagement -> #changemanagement`
- `#duediligence -> #duediligence`
- `#commercialisation -> #commercialisation`
- `#operationallevel -> #operationallevel`
- `#managerlevel -> #managerlevel`
- `#directorlevel -> #directorlevel`
- `#crosssector -> #crosssector`
- `#sectorvisibility -> #sectorvisibility`
- `#thoughtleadership -> #thoughtleadership`

### Convert to canonical tag + field
- `#executiveengagement -> forum: executive`
- `#boardlevel -> forum: committee` or `forum: board`
- `#meetings -> artifact_type: meeting_paper` or forum/prose only`
- `#writing -> artifact_type: brief/business_case/operating_plan/etc`
- `#correspondence -> artifact_type: email` or `communication`
- `#reporting -> artifact_type: review_summary` or `communication`
- `#review -> #evaluation` or `artifact_type: review_summary`
- `#businesscase -> artifact_type: business_case` (and often `#investment`)
- `#strategicplanning -> #strategy` and often `#design`
- `#innovation -> #thoughtleadership` or `#changemanagement`, depending on substance

### Convert to canonical tag combinations or field vocabularies
- `#investmentgovernance -> #investment + #governance`
- `#policyinterpretation -> #policy` and often `#analysis` or `#advice`
- `#financialanalysis -> #analysis` + `subject_matter: public_funding` or a more specific finance-related subject_matter if added
- `#programmanagement -> #portfolio` and often `#delivery`
- `#datagovernance -> #data` and often `#governance`
- `#ipstrategy -> #commercialisation` or `#policy` + `subject_matter: ip`
- `#technoeconomic -> #technical + #analysis`
- `#researchmanagement -> #partnerships` or `#governance` + `subject_matter: research_governance`
- `#capacitybuilding -> #peopleleadership` or `#peopledevelopment`
- `#leadership -> prefer level + capability/judgement tags rather than a standalone canonical tag`

---

## Change-control rules
This is what keeps the taxonomy usable in 10 years.

### Rule 1: do not add a new canonical tag casually
Add a new tag only if **all** are true:
1. the concept recurs at least 8 times across approximately 12 weeks of records
2. it cannot be represented well by existing tags plus fields
3. it is likely to be a retrieval pivot in future queries
4. its definition can be written clearly without overlapping too heavily with existing tags

### Rule 2: prefer extending field vocabularies before tag vocabularies
If a new idea is mostly topical or contextual, add it to:
- `subject_matter`
- `artifact_type`
- `impact_type`
- `forum`

not to the canonical tag set.

### Rule 3: versioning
- Increment **minor version** when clarifying definitions, examples, or field vocabularies.
- Increment **major version** only when adding, removing, or renaming canonical tags.

### Rule 4: annual calibration review
Once per year:
- review the last 3 to 6 months of records
- identify overused tags
- identify tags rarely used or used inconsistently
- check whether fields are carrying enough specificity
- refine definitions, not the tag count, unless clearly necessary

---

## Calibration examples

### Example 1
A proposal was non-compliant with an agreement clause, but you framed a path for committee consideration without setting a harmful precedent.

Tags:
- `#directorlevel`
- `#governance`
- `#duediligence`
- `#riskmanagement`

Fields:
- `tradeoff: project progression vs governance precedent`
- `forum: committee`
- `artifact_type: governance_advice`
- `impact_type: precedent_protected`
- `outcome: Proposal could proceed for consideration without normalising a harmful precedent.`

### Example 2
You redesigned an operating-plan template to improve executive oversight and reduce narrative clutter.

Tags:
- `#managerlevel`
- `#governance`
- `#design`
- `#changemanagement`

Fields:
- `forum: executive`
- `artifact_type: operating_plan`
- `impact_type: process_improved`
- `outcome: Executive reporting became clearer and better aligned to decision needs.`

### Example 3
You advised on national-scale data repository models and shaped how the issue should be framed for executives.

Tags:
- `#directorlevel`
- `#data`
- `#advice`
- `#influence`
- `#crosssector`

Fields:
- `forum: executive`
- `subject_matter: data_infrastructure`
- `impact_type: strategy_clarified`
- `outcome: Decision-makers received a clearer and more usable framing of national repository options.`

---

## Final operating rules for future LLMs
When converting weekly notes into CareerVault records:

1. Normalize the prose first.
2. Write the `outcome` sentence explicitly.
3. Populate `tradeoff` whenever a real tension is present.
4. Choose level based on judgement altitude.
5. Choose one primary domain and one primary judgement tag.
6. Add extra tags only if they improve future retrieval.
7. Use canonical tags only.
8. Prefer fields over tags for specificity.
9. If uncertain, choose the narrower, more defensible interpretation.
10. Never optimize for the current week at the expense of future consistency.

---

## Recommended weekly capture prompt
"Convert these weekly notes into CareerVault evidence records using Taxonomy v3.0.
For each record:
- preserve the underlying meaning
- produce explicit `outcome`
- add `tradeoff` if present
- apply exactly 1 operating-level tag
- apply 1 primary capability-domain tag
- apply 1 primary judgement tag
- add at most 2 additional tags if genuinely central
- use only canonical tags from this file
- prefer structured fields over extra tags"

