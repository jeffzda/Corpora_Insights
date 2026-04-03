# Taxonomy v3.0 — Design Notes

**Working document capturing design thinking for the next taxonomy iteration.**
**Status: Design phase — not yet implemented.**
**Date: April 2026**

---

## Context

After completing the v2.0 taxonomy and analysing 16,931 records across 1,448 documents, several
issues emerged that motivate a v3 revision:

1. **QA classification disputes concentrate on failure_mode, delay_category, and lifecycle_phase**
   — each cited in ~20% of the 1,452 flagged records (8.1% questionable + 0.5% wrong). Severity
   is rarely disputed (2.5% of flags). The disputes are boundary ambiguity, not extraction errors.

2. **"Design assumption failure" is a super-category** absorbing 20% of all records. Almost any
   failure can be framed as "an assumption was wrong." It's also the most common secondary
   failure mode (508 records), confirming it co-occurs with everything because it's the root cause
   of everything.

3. **The severity escalation ratio** ((major+critical) / (minor+moderate)) emerged as the strongest
   analytical metric. It reveals risk profiles that adversity rate masks — e.g., community/local
   bodies have low adversity but the highest escalation ratio (0.62). This metric is robust to
   failure mode boundary disputes because it aggregates across all modes.

4. **No causal layer exists.** The taxonomy captures what went wrong (failure mode) but not what
   made it hard (the underlying technical challenge). A portfolio manager assessing a new proposal
   needs both: "what kinds of problems occur?" and "what about this project's characteristics
   will drive those problems?"

---

## Part 1: Failure Mode Redesign

### The problem with the current 10 failure modes

Reading 80+ unstratified random `what_happened` narratives (seed=42, no stratification by
existing labels to avoid circular reasoning), the following issues became clear:

#### "Design assumption failure" is not a failure mode
It's a root cause that underlies other failures. The narratives classified as "design assumption
failure" include:
- Incorrect site/environmental assumptions (bridge too narrow, wildlife incompatible with
  fencing standard, Pilbara heat exceeding OEM ratings) — these are **context mismatches**
- Wrong performance expectations (solar variability 80% in 6 seconds vs 40% design basis) —
  these are **technical performance gaps**
- Market/economic misjudgements (MLF overestimation, business case assumptions) — these are
  **commercial viability gaps** or **regulatory/market structure** issues

At 3,457 records (20%), it's the largest category precisely because it's the default when the
LLM can't pick a more specific mode. It's also the #1 secondary failure mode (508 records),
confirming it co-travels with everything.

#### "Cost overrun" and "schedule slippage" are consequences, not causes
Cost overruns are caused by procurement surprises, scope changes, regulatory delays, capability
gaps. Schedule slippage is caused by the same things. The co-occurrence data confirms this:
cost overrun's top secondary is schedule slippage (25) and vice versa (71). They're symptoms
that co-travel with the actual underlying failure.

Cost overrun is also extremely rare (194 records, 1.1%) — likely because KB reports rarely
disclose cost figures. Analysis of 59 final reports for Solar PV, Battery storage, and DER
found **zero** containing both planned and actual project cost figures.

#### "Technical underperformance" and "integration failure" overlap heavily
Integration failure has 45.9% secondary prevalence (highest of any mode), with technical
underperformance as the top secondary (85 records). When a battery inverter can't provide the
right signal to a third-party controller, is that technical underperformance or integration
failure? The boundary is inherently fuzzy.

#### "Data quality/measurement failure" is rarely primary
At 730 records with the lowest severity ratio (0.10), it's almost never a serious standalone
failure — it's a symptom of planning gaps or technical limitations.

### Proposed v3 failure modes (7 categories)

| # | Category | What it captures | PM question |
|---|---|---|---|
| 1 | **Technical performance gap** | Technology/equipment didn't meet spec, lab-to-field gap, degradation, underperformance | "Will the technology actually work at this scale/site?" |
| 2 | **Design & planning error** | Incorrect site assumptions, scope gaps, missing requirements, inadequate due diligence | "Has the team thought through site-specific and operational realities?" |
| 3 | **Regulatory & market structure** | Regulatory barriers, missing frameworks, market design gaps, standards incompatibility, policy changes mid-project | "Is the regulatory and market environment ready for this?" |
| 4 | **Commercial viability gap** | Unviable economics, demand shortfall, competing technologies, missing revenue streams | "Does the business case hold under realistic conditions?" |
| 5 | **Capability & resourcing gap** | Team skill gaps, talent scarcity, organisational capacity, knowledge deficits | "Can this proponent actually deliver this?" |
| 6 | **Delivery execution failure** | Procurement surprises, construction issues, schedule slippage, cost escalation, supply chain problems | "What can go wrong during physical delivery?" |
| 7 | **Coordination & stakeholder failure** | Multi-party governance, stakeholder management, community engagement, land access, internal coordination | "Are the governance and stakeholder arrangements robust?" |

### What changed and why

**Removed:**
- **"Design assumption failure"** — dissolved. Contents redistribute to "design & planning error"
  (site/scope assumptions), "technical performance gap" (performance assumptions), and
  "regulatory & market structure" (market assumptions). The catch-all is gone.
- **"Cost overrun"** and **"schedule slippage"** — absorbed into "delivery execution failure."
  They're consequences, not causes. The narrative data shows they almost always co-occur with
  a causal failure mode.
- **"Integration failure"** — split between "technical performance gap" (for component/system
  interoperability issues) and other modes depending on the root cause (regulatory for connection
  standards, delivery execution for procurement of integration components).
- **"Data quality/measurement failure"** — absorbed into "design & planning error" (inadequate
  measurement/validation planning) and "technical performance gap" (instrument/data system
  failures). At 730 records with severity ratio 0.10, it was rarely a primary failure.

**Renamed/refined:**
- "Technical underperformance" → **"Technical performance gap"** (broader, includes lab-to-field)
- "Regulatory misfit" → **"Regulatory & market structure"** (explicitly includes market design gaps)
- "Commercial/demand failure" → **"Commercial viability gap"** (reframed from failure to gap)
- "Resource/capability shortfall" → **"Capability & resourcing gap"**
- "Governance/coordination failure" → **"Coordination & stakeholder failure"** (explicitly includes
  stakeholder/community dimension)

### Key properties
- **7 categories instead of 10** — fewer boundaries to dispute
- **No catch-all** — "design assumption failure" is gone
- **Causes, not consequences** — cost overrun and schedule slippage are no longer separate
- **Maps to PM due diligence questions** — each category corresponds to an area of assessment
- **Requires LLM reclassification pass** — existing labels cannot be deterministically remapped
  because "design assumption failure" must be split based on narrative content

---

## Part 2: Technical Challenge Tags (New Dimension)

### The distinction between failure modes and technical challenges

A failure mode is **what went wrong** — the observable outcome. A technical challenge is **what
the project was attempting to do that made it hard** — the causal driver. The same technical
challenge can manifest as different failure modes.

Example: "Connecting to the grid" (challenge) can result in:
- Regulatory & market structure (connection standards block you)
- Technical performance gap (inverter can't comply)
- Delivery execution failure (connection process takes 18 months)
- Design & planning error (underestimated connection complexity)

The current taxonomy only captures the failure mode layer. The challenge layer answers a
different question: "given that this project involves X, what kinds of failures should I expect?"

### Why challenges are not the same as failure modes

Initial attempts to define technical challenges kept producing lists that were actually failure
modes rewritten as activities (e.g., "regulatory & standards readiness" — which is just
"regulatory misfit" wearing a different hat). The correct framing is challenges as **things the
project is doing** that a PM can identify from a proposal:

- **Wrong:** "Regulatory & standards readiness" (this is a failure mode)
- **Right:** "Operating in a new or uncertain regulatory environment" (this is a yes/no question
  about the project)

This confusion is extremely prevalent in project risk literature, which overwhelmingly describes
"what goes wrong" rather than "what makes it hard." The training data for LLMs reinforces this
pattern, making it the default framing.

### Proposed technical challenge tags (7 categories)

Each is framed as a yes/no question a PM can ask of a proposal:

| # | Challenge | PM question |
|---|---|---|
| 1 | **Connecting to the grid** | Is this project connecting to or interacting with the electricity network? |
| 2 | **Scaling from lab/pilot to field** | Is this project taking something from smaller scale to larger? |
| 3 | **Building or integrating new software/control systems** | Does this project depend on unproven software? |
| 4 | **Sourcing and assembling physical components** | Does it depend on specialised equipment or thin supplier markets? |
| 5 | **Operating in a new or uncertain regulatory environment** | Is this project doing something the rules weren't written for? |
| 6 | **Deploying in a difficult or unfamiliar site context** | Is the physical environment or community situation demanding? |
| 7 | **General / other** | Challenges that don't fit the above |

### Why "connecting to the grid" is not elevated to a special structural role

An early design considered making grid integration a boolean flag (like `is_consortium`),
implicitly asserting it as THE primary technical challenge across all ARENA investments.

Keyword analysis of all 12,376 adverse records showed this is not supported:

| Theme | Prevalence | Exclusive records |
|---|---|---|
| Regulatory/standards | 61.1% | 587 |
| Grid/network | 55.9% | 363 |
| Software/control/digital | 22.0% | 535 |
| Supply chain/procurement | 21.5% | 480 |
| Site/environment | 14.5% | 407 |
| Stakeholder/community | 12.9% | 225 |
| Market/commercial structure | 11.7% | 157 |

Grid is second in raw prevalence but **fifth in exclusivity** — it co-occurs with everything
(especially regulatory) rather than being a distinct standalone challenge. No single technical
dimension dominates enough to warrant special structural treatment. Elevating grid alone would
implicitly assert a primacy the data doesn't support.

Instead, grid integration is one of 7 challenge tags, treated equally with the others.

### Why challenges are tagged at the record level, not the project level

This was extensively debated. The arguments:

**For project-level tagging:**
- Challenges are properties of the project, not individual records
- Simpler LLM pass (~500 projects vs ~12,000 records)
- Denominator is clean — every record from a grid-connected project counts
- No ambiguity about which records to tag

**For record-level tagging:**
- Enables direct correlation between specific challenges and specific failure modes
- "Of records where grid integration was being addressed, X% succeeded, Y% failed, and
  failures were: regulatory 40%, delivery execution 25%, technical 20%"
- Project-level would say "of projects involving grid connection, Z% had failures" — but
  doesn't tell you whether the failures were *caused by* grid connection
- Records where no challenge applies simply don't enter the analysis — they're not false
  negatives, they're irrelevant to the question
- Multi-tagging is natural (a record can involve both grid connection and software integration)

**Resolution: record-level tagging.**

The key insight was that success records can also be tagged with challenges when the narrative
describes navigating a challenge successfully. A sample of 30 "no failure" records showed that
roughly half describe successfully addressing a recognisable challenge:
- DLV-16504: operational vs test RTE gap (challenge: scaling to field)
- DLV-68601: uncertain integration proved straightforward (challenge: software/control)
- DLV-69663: BESS noise managed by daytime operation (challenge: difficult site context)

The other half are pure observations with no challenge dimension (FCAS revenue reporting,
customer motivation surveys, knowledge sharing metrics). These correctly receive no tag.

This means the analytical output is: "Of the N records where challenge X was being addressed,
Y% navigated it successfully, Z% experienced failure, and those failures broke down as..."
The denominator includes both successes and failures *against that specific challenge*, giving
an honest base rate.

### Why this is a low-risk enrichment

The technical challenge tags are an independent layer that does not modify any existing fields
or analysis. The existing failure modes, severity ratings, reference class matrices, and
severity escalation ratios are unchanged.

If the challenge tags prove analytically useless (e.g., failure mode distributions don't differ
meaningfully between tagged and untagged records), they can be ignored. The data sits on records
and costs nothing if not surfaced.

---

## Part 3: Implementation Notes

### Failure mode reclassification
- **Requires LLM pass** on all 12,376 adverse records (4,555 "no major failure stated" records
  can stay as-is)
- Input per record: `what_happened`, `lesson_learnt`, `evidence_excerpt`, plus 7 new category
  definitions
- Estimated cost: Haiku batch, ~$5 for full corpus
- Existing `failure_mode` preserved as `failure_mode_v2` for traceability
- Multi-valued not permitted — each record gets exactly one failure mode

### Technical challenge tagging
- **Requires LLM pass** on all 16,931 records (including "no failure" records)
- Input per record: `what_happened`, `lesson_learnt`, `evidence_excerpt`, plus 7 challenge
  definitions framed as yes/no questions
- Output: list of applicable challenge tags (zero, one, or multiple per record)
- Estimated cost: Haiku batch, ~$8 for full corpus
- Can be combined with failure mode reclassification in a single pass to reduce cost

### Severity escalation ratio
- Already implemented in dashboard (Matrix 1, Matrix 3, Matrix 5, Matrix 6)
- Corpus baseline: 0.27
- Key finding: regulatory misfit (0.69) and cost overrun (0.62) escalate most; data
  quality (0.10) and governance (0.16) rarely escalate
- Consortium uplift disappears at the ratio level (0.26 both ways) — consortium adds
  frequency, not severity
- Community/local body has the highest escalation ratio (0.62) despite low adversity rate

---

## Part 4: Supporting Analysis

### Adversity vs final report availability
Projects with final reports show 98.1% adversity vs 90.5% without (+7.7pp). The effect is
modest because the baseline is already high. The hypothesis that categories with fewer final
reports under-report adversity has limited explanatory power, except for:
- **Hybrid technologies** — only 8% have final reports, adversity drops to 50% without them
- **Grid stability** — +22pp gap
- **Bioenergy** — +18pp gap
- **Solar PV** — negative delta (-3pp), suggesting solar is so well-documented that interim
  reports already capture the full picture

### Final reports lack quantitative cost data
Scanning 59 final reports for Solar PV, Battery storage, and DER found **zero** containing both
planned and actual project cost figures. This rules out Flyvbjerg-style quantitative reference
class forecasting (measuring magnitude of cost/schedule deviation from plan) using the KB corpus
alone. The quantitative outcome data lives in ARENA's internal project management systems.

### What the taxonomy is and isn't
This is **empirical risk profiling**, not forecasting. It answers "given a project with these
properties, what kinds of problems have historically shown up, at what phase, and how often?"
— which is the question a portfolio manager needs at proposal assessment time. The value chain:
1. New proposal arrives
2. Reference class lookup (category, activity type, proponent, challenges)
3. Failure mode probability distribution for that class
4. Phase watch-list for when problems typically occur
5. PM asks the right due diligence questions in assessment

---

## Open Questions

1. Should the "no major failure stated" records be reclassified? Some may contain minor issues
   that were missed in v2 extraction. Others are genuine positive observations.

2. Should `delay_category` be revised alongside `failure_mode`? The same boundary issues apply,
   and 52% of records have blank delay_category.

3. Should the technical challenge definitions be refined further before the LLM pass? The
   current list is based on narrative analysis but hasn't been validated against a stratified
   sample.

4. Can the failure mode reclassification and challenge tagging be done in a single LLM pass to
   reduce cost and ensure consistency?

5. What minimum sample size should be required before surfacing challenge-based failure mode
   distributions in the dashboard?
