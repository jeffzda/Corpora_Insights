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

## Part 5: Test Pass Results (500-record sample, Haiku)

A test LLM pass was run on a stratified sample of 500 records using claude-haiku-4-5 to
validate the challenge framework. Each record was classified with:
- Which challenges (0, 1, or multiple) are being addressed
- Confidence score (0.0–1.0) for each tag
- Outcome: failure / success / neutral for each challenge

### Key validation results

**The three-way outcome classification works reliably.**
Across all challenges, the split is roughly 60% failure / 25% success / 15% neutral. Confidence
is high: 93.5% of tags are 0.7+, with 51% above 0.85. The model isn't guessing.

**Coverage is good.** Only 9.4% of records received no challenge tag. 34.6% matched exactly
one challenge, 51.4% matched two, 4.6% matched three or more. The six categories provide
near-comprehensive coverage without excessive overlap.

**Success records are genuine.** High-confidence success examples include:
- 1.25 MW electrolyser demonstrating sub-1-minute start-up (scale-up, conf 0.88)
- Community engagement on Lord Howe Island starting 5 years before contract (site/env, conf 0.92)
- DVMS trial retained in production after successful demonstration (software, conf 0.88)

### Challenge → Failure Mode signatures

Each challenge produces a **distinct failure mode distribution** that differs meaningfully from
the baseline. This is the core validation — challenges are not just relabelled failure modes,
they're causal drivers with different downstream patterns.

| Challenge | Strongest signal vs baseline |
|---|---|
| **Regulatory** | regulatory misfit 27% (vs 9% baseline, **+18pp**) |
| **Software/controls** | tech underperformance 25% + integration 12% + data quality 14% (triple lift) |
| **Supply chain** | schedule slippage 17% + resource shortfall 12% (delivery problems) |
| **Grid connection** | tech underperformance 21% + integration 13% (technical/interop) |
| **Scaling to field** | design assumption failure 44% (vs 28%, **+16pp**) — scaling magnifies design errors |
| **Site/environment** | design assumption 35% + cost overrun 9% (vs 2%) — context invalidates plans |

### Severity escalation by challenge and outcome

The failure-only severity ratios are the strongest finding:

| Challenge | Overall ratio | Failure-only ratio | Interpretation |
|---|---|---|---|
| **Regulatory** | 0.50 | **0.72** | When regulatory fails, it fails hard |
| **Grid connection** | 0.48 | **0.74** | Same — severe when it goes wrong |
| Scaling to field | 0.23 | 0.33 | Moderate severity |
| Supply chain | 0.24 | 0.32 | Moderate severity |
| Software/controls | 0.20 | 0.29 | Frequent but manageable |
| Site/environment | 0.15 | 0.21 | Frequent but manageable |

This directly informs milestone design: grid and regulatory challenges need hard gates before
committing capital; software and site challenges can be managed iteratively.

### Comparison: challenge analysis vs reference class matrices

The challenge-filtered analysis produces stronger signals than the existing dashboard matrices:

- **Matrices** answer: "What's the base rate for this cell?" (e.g., hydrogen × pilot = 75%
  adversity). This is static and can't explain *why*.
- **Challenge analysis** answers: "What specifically goes wrong when projects face the same
  difficulties you're about to face, and how bad does it get?" This is causal and actionable.
- **Combined with severity ratio**, challenges enable statements like: "Grid connection failures
  have a severity ratio of 0.74 — structure a hard gate on connection approval. Software
  failures have a ratio of 0.29 — use iterative checkpoints instead."

The matrices retain their role as the **entry point** — quick risk profile lookup for a
reference class. The challenge layer provides the **analytical depth** underneath.

### Known limitation: success rates are not comparable across challenges

Success rates are not surfaced in dashboard matrices. Proponents are more inclined to report
on technical successes (grid integration, scale-up) that represent material delivery milestones
than on supporting considerations (supply chain, regulations) that went smoothly. If procurement
or regulatory approval goes to plan, there is little incentive to document it — but a successful
grid connection or first-of-kind deployment is a reportable achievement. This reporting bias
systematically under-represents supply chain and regulatory successes relative to technical
successes, making cross-challenge success rate comparisons unreliable.

Failure mode distributions and severity ratios are not materially affected by this bias —
when something goes wrong, it gets reported regardless of whether it's a technical problem or
a procurement problem, because the purpose of KB documents is to share what was learned from
difficulties. The asymmetry in reporting incentives applies mainly to the success side.

The success/failure/neutral classification remains valuable for the LLM synthesis step (Level 3)
— when filtering records and generating a brief, having the successes in the set lets the
synthesis contrast what went wrong against what went right. But the aggregate success *rate*
per challenge should not be presented as a comparable statistic.

### Downstream application: LLM-generated briefings

The challenge tags enable a powerful workflow for proposal assessment:
1. PM receives proposal (e.g., hydrogen electrolyser pilot, consortium-led, grid-connected)
2. Filter records: `arena_category = Hydrogen` + `activity_type = Pilot/demonstration` +
   challenge = `GRID_CONNECTION`
3. This produces a focused set of 40-80 records, filtered to the specific intersection
4. Feed filtered records to an LLM: "Summarise the distinct failure patterns, what severity
   they reach, and what successful projects did differently"
5. Output: a 2-page empirical brief contrasting failures against successes for the exact
   combination of technology, activity, and challenge

The success/failure/neutral classification is critical here — the LLM synthesis can contrast
what went wrong against what went right in the same challenge context, rather than just listing
problems.

### Multiple records from the same project addressing the same challenge

A single project may produce multiple records that reference the same challenge at different
points in time — e.g., a grid connection barrier at commissioning (failure) followed by
resolution after 12 months of renegotiation (success). These are **not confounding** — they
are distinct delivery events that capture different information:

- Record 1 tells you that grid connection challenges cause failures at commissioning
- Record 2 tells you they're recoverable, and how recovery happens

Both are true and both are needed. Collapsing them into a single outcome (was this project's
grid connection a failure or a success?) loses the phase-specific information that makes the
analysis actionable.

**Effect on aggregate success rate:** A challenge that always fails first and then gets resolved
generates one failure record and one success record, producing a 50% success rate. This is more
informative than either "100% adversity" or "100% eventually succeeded" — it accurately
represents "this fails reliably but is recoverable."

**Effect on severity ratio:** The failure record carries the higher severity (major/critical
during the crisis); the success record carries lower severity (none/minor after resolution).
The ratio reflects severity at the point of failure, not diluted by recovery. This is correct
behaviour.

**Implication for LLM synthesis:** When generating a brief from filtered records, the synthesis
prompt should instruct the LLM to recognise that multiple records from the same project
describing the same challenge at different times represent a narrative arc (failure → recovery),
not independent evidence. This is a prompt design consideration for Level 3, not a data
structure problem.

### Confidence thresholds

The test pass showed that questionable tags tend to have lower confidence scores (0.65–0.78),
while clearly correct tags are typically 0.85+. A confidence threshold of **0.80** for
dashboard display would filter out most noise while keeping legitimate tags. This would shift
the dual-tag rate from 51% to approximately 35–40%.

Low confidence often indicates "this project probably involved this challenge, but this
specific record doesn't describe the project addressing it" — the model is inferring from
context rather than reading about the challenge being confronted. This is the right reason to
have low confidence and the right reason to filter it out.

---

## Part 6: Revised Analytical Architecture

The dashboard and analysis tools should flow through three levels:

**Level 1 — Reference class matrices (existing)**
Quick lookup: arena_category × activity_type → adversity rate, severity ratio, top failure
modes. Entry point for any assessment. Static, pre-computed.

**Level 2 — Challenge breakdown (new)**
For a given reference class, what challenges do projects in this class face? Per challenge:
failure mode distribution, severity ratio, success rate. Pre-computed from the challenge tags.

**Level 3 — Synthesised brief (new, on-demand)**
For a specific combination of reference class + challenges, generate an LLM-written summary
from the filtered records. Contrasts failures against successes. Generated on demand, not
pre-computed.

---

## Part 7: Dropping `outcome_class`

### Why it's being removed

`outcome_class` (8 values: successful demonstration, partial success, delayed but recoverable,
re-scoped/adapted, knowledge generated despite setback, discontinued/not progressed, follow-on
scale-up enabled, policy/market influence only) is removed entirely in v3.

**It's a record-level guess at a project-level property.** A record about a procurement delay
in month 6 gets classified as "delayed but recoverable" — but the LLM doesn't know whether
the project eventually succeeded or was discontinued. It's inferring outcome from the tone of
a single paragraph.

**"Knowledge generated despite setback" absorbed 39% of all records.** This label communicates
nothing — every failure in a lessons-learned report generates knowledge by definition. It's
the path of least resistance for the LLM when classifying any failure described in positive
framing. 39% of records tagged with it is equivalent to saying "something went wrong and
someone wrote about it."

**It overlaps with severity without adding independent information.** Analysis showed:
- 83% of discontinued records are major or critical severity
- 60% of critical records are discontinued
- "Partial success", "re-scoped/adapted", and "delayed but recoverable" are effectively
  severity judgements (how bad was it?) rather than outcomes (what ultimately happened?)

**The only value with real information is "discontinued/not progressed"** (1% of records),
which is usually stated explicitly in the source text. But discontinuation is a project-level
fact, not a record-level classification — and it's already available from the portfolio CSV
(`project_status`) and from explicit statements in the source documents.

### What replaces it

Nothing directly. The information outcome_class was trying to capture is covered by:
- **Issue severity** — how bad the event was (more reliable, 2.5% QA dispute rate)
- **Challenge outcome tags** (failure/success/neutral) — whether the challenge was navigated
  successfully, assessed per-record with respect to the specific challenge being addressed
- **Portfolio CSV project_status** — whether the project is past/active (project-level fact)
- **Discontinuation** — derivable from records that explicitly state it, flagged at the
  project profile level rather than inferred per-record

### Origin

`outcome_class` was not from ARENA data — it was designed in the v1.0 taxonomy as the
"Flyvbjerg dimension: outcome" to support reference class forecasting. The values were our own
invention. The intent was sound (capture project-level outcomes) but the implementation was
flawed (per-record LLM inference from narrative tone). The challenge framework's three-way
outcome classification (failure/success/neutral) serves the analytical purpose better because
it's scoped to the record's relationship with a specific challenge, not a guess at the
project's ultimate fate.

---

## Part 8: Field Disposition — Active vs Legacy

### Decision: drop `delay_category` and `delay_magnitude`

`delay_category` (9 values) maps almost 1:1 to `failure_mode`:

| delay_category | Equivalent failure_mode |
|---|---|
| approvals/regulatory | regulatory misfit |
| grid connection/system studies | integration failure / regulatory misfit |
| procurement/supply chain | schedule slippage / cost overrun |
| financing/commercial close | commercial/demand failure |
| construction/installation | schedule slippage |
| commissioning/integration | integration failure |
| data/validation/testing | data quality/measurement failure |
| stakeholder/land/community | governance/coordination failure |
| internal governance/resourcing | resource/capability shortfall |

It's a parallel classification of the same event — "what kind of problem was it" vs "what
phase did the delay occur in" — but the LLM answers the same question twice in different words.
52% of records have "no material delay stated" or no value at all.

`delay_magnitude` is almost entirely empty: only **584 of 16,931 records (3.4%)** have an
actual time range. Of the 6,371 records with a delay category, **91% have no quantified
magnitude** — the LLM noted a delay but couldn't quantify it from the source text. The 584
quantified records are spread thinly across 9 categories, too sparse for meaningful analysis.

Both fields join the legacy pile. The temporal information they were trying to capture is
already covered by `lifecycle_phase` (when it happened) and `failure_mode` (what kind of
problem), and the source documents rarely contain enough specificity to populate delay_magnitude.

### Active taxonomy fields (v3)

**Deterministic (from metadata, not LLM-inferred):**
- `arena_category` (14 values) — from KB metadata via ARENA_CATEGORY_MAP
- `activity_type` (Study / Pilot / Deployment / R&D) — from projects CSV keywords
- `is_consortium` (boolean) — from original proponent_type
- `in_arena_portfolio` (boolean) — from projects CSV match

**LLM-inferred, actively used in filters/matrices/analysis:**
- `failure_mode` — being redesigned (currently 10, target TBD from bottom-up clustering)
- `issue_severity` (none / minor / moderate / major / critical) — low dispute rate, strong metric
- `lifecycle_phase` (8 values) — when in the project lifecycle the event occurred
- `proponent_type` (10 values) — who is delivering
- `transferability` (narrow / moderate / broad) — how widely the lesson applies

**New in v3:**
- `technical_challenge` — list of challenge tags per record (7 categories, multi-valued)
- Challenge outcome (failure / success / neutral) — per challenge tag

### Legacy fields (preserved on record for traceability, not in filters/display)

- `outcome_class` — dropped: record-level guess at project-level property (see Part 7)
- `project_type` — superseded by `arena_category` (deterministic)
- `project_scale_band` — original LLM-inferred scale band
- `technology_domain` — superseded by `arena_category` (deterministic)
- `delay_category` — dropped: redundant shadow of failure_mode (see above)
- `delay_magnitude` — dropped: 96.6% empty (see above)
- `proponent_type_original` — pre-reclassification value (consortium records only)
- `lifecycle_phase_original` — pre-remap value (variation/re-scope records only)
- `failure_mode_v2` — original v2 failure mode label (after reclassification)

---

## Part 9: Failure Mode Redesign — Bottom-Up Approach

### Revised methodology

The initial top-down redesign (Part 1) proposed 7 categories but risked replacing one catch-all
("design assumption failure") with another ("design & planning error") and lost signal by
over-bundling categories that were working fine (integration failure, schedule slippage, data
quality/measurement failure).

**New approach:** bottom-up clustering from the data.

1. **Sample 500 records** from the 4 problematic failure mode categories:
   - 200 × design assumption failure (the catch-all, 3,457 total)
   - 100 × integration failure (fuzzy boundary with technical underperformance, 645 total)
   - 100 × schedule slippage (consequence not cause, 982 total)
   - 100 × data quality/measurement failure (rarely primary, 730 total)

2. **Phase 1 — Root-cause tagging** (Haiku batch): For each record, ask "what specifically
   went wrong?" with no predefined categories. Output: a 5-10 word concrete root cause per
   record. Batch submitted April 2026.

3. **Phase 2 — Clustering** (Sonnet): Feed all 500 root-cause tags to a single call, ask it
   to identify natural groupings and propose 6-12 categories that emerge from the data.

4. **Phase 3 — Evaluation:** Compare proposed categories against the 6 failure modes that are
   working fine (technical underperformance, regulatory misfit, commercial/demand failure,
   resource/capability shortfall, governance/coordination failure, and possibly others). Decide
   which existing categories to keep, which to merge, and what new categories the clustering
   reveals.

The goal is to fix what's broken without losing signal from categories that work. The 5,814
records across the 4 problematic categories (34% of adverse records) need reclassification;
the remaining 6,562 adverse records in working categories may not.

---

## Part 10: Validation Pass Results (2,533-record sample)

### Methodology

A stratified 20% sample of all adverse records (2,533 records across all 10 v2 failure modes,
with a floor of 100 per category) was classified by Haiku against the proposed 8-category
taxonomy. Each record was assigned exactly one v3 category, a confidence score, and a free-form
root-cause tag. Cost: ~$4.

### Key findings

**1. "Technical assumptions" became a 30% catch-all.**

| v3 Category | Count | % | Severity Ratio |
|---|---|---|---|
| Technical assumptions | 759 | 30.0% | 0.34 |
| Poor scoping | 517 | 20.4% | 0.21 |
| Commercial & market | 312 | 12.3% | 0.59 |
| Coordination & stakeholders | 254 | 10.0% | 0.14 |
| Regulatory & approvals | 243 | 9.6% | 0.60 |
| Data & measurement | 203 | 8.0% | 0.14 |
| Execution & logistics | 172 | 6.8% | 0.28 |
| Capability shortfall | 73 | 2.9% | 0.24 |

We dissolved "design assumption failure" because it was a 20% catch-all. "Technical
assumptions" at 30% is worse. It absorbed 52% of design assumption failure, 73% of technical
underperformance, and 36% of integration failure — three different source categories collapsing
into one bucket.

**2. Capability shortfall failed the prevalence test at 2.9%.** The confusion matrix showed
resource/capability shortfall dispersed: 39% stayed as capability shortfall, 25% went to
execution & logistics, 16% to poor scoping. It's not a coherent standalone category.

**3. Severity ratios are genuinely distinct across categories.** Regulatory & approvals (0.60)
and commercial & market (0.59) produce hard failures. Coordination & stakeholders (0.14) and
data & measurement (0.14) are nuisance-level. This is strong evidence the categories carry
independent analytical signal.

**4. Zero low-confidence records.** Haiku classified everything at 0.77+ confidence, suggesting
it's not flagging genuine boundary ambiguity. The confidence scores may not be reliable for
identifying boundary cases.

**5. Confusion matrix validated most migration patterns:**
- Commercial/demand → commercial & market: 72% (clean 1:1)
- Data quality → data & measurement: 86% (cleanest)
- Regulatory misfit → regulatory & approvals: 76% (clean 1:1)
- Governance/coordination → coordination & stakeholders: 72% (clean 1:1)
- Design assumption failure → technical assumptions 57% + poor scoping 33% (splits as expected)
- Technical underperformance → technical assumptions 73% (validates dissolving it)
- Schedule slippage → poor scoping 30% + execution & logistics 33% + regulatory 22% (disperses)
- Cost overrun → poor scoping 51% (most cost overruns were actually scoping failures)

**6. JSD analysis flagged two merge candidates:**
- Poor scoping + coordination & stakeholders (JSD < 0.05 across all dimensions) — but severity
  ratios differ (0.21 vs 0.14), so they carry different analytical weight. Keep separate.
- Technical assumptions + data & measurement (JSD < 0.05) — but severity ratios differ
  (0.34 vs 0.14). Keep separate.

### Decision: split "technical assumptions" into 3 sub-categories

Sub-clustering of the 759 records classified as "technical assumptions" revealed 4 natural
sub-groups, each with a distinct PM due diligence question:

| Sub-group | % of 759 | PM question |
|---|---|---|
| Unvalidated performance | 42% (~319) | "Does this work here?" |
| Unvalidated integration | 22% (~167) | "Do these work together?" |
| Unvalidated design parameters | 22% (~167) | "Are our numbers right for this context?" |
| Unvalidated commercial viability | 14% (~106) | "Does the market context hold?" |

Sub-group 4 (commercial viability, 14%) overlaps with the existing "commercial & market"
category and falls below the 5% prevalence threshold when extrapolated to the full corpus
(~4.2%). It is absorbed back into "commercial & market."

The remaining 3 sub-groups each pass prevalence when extrapolated:
- Unvalidated performance: ~12.6% of corpus
- Unvalidated integration: ~6.6% of corpus
- Unvalidated design parameters: ~6.6% of corpus

**Note on "unvalidated integration":** This is distinct from the dissolved "system integration
failure" (Part 1). "System integration failure" was a consequence ("the systems didn't work
together"). "Unvalidated integration" is a mechanism ("the interface between systems was never
validated before deployment"). The broken thing is the absent validation step, not the
observable outcome. It passes the mechanism test.

### Decision: absorb "capability shortfall" into adjacent categories

At 2.9% prevalence, capability shortfall doesn't justify a standalone category. The confusion
matrix shows its records naturally distribute to execution & logistics (25%) and poor scoping
(16%). The coding rule for the remaining categories already handles the edge cases: if the team
lacked skills and made wrong assumptions, classify by what was broken (the assumption), not why
(the skill gap).

### No established taxonomy covers this level of detail

A search of existing frameworks (IPA/Merrow, Flyvbjerg, PMI RBS, FMEA, AACE) found no
off-the-shelf taxonomy that classifies project delivery failure mechanisms at this level of
specificity. The closest is the PMI Risk Breakdown Structure, which has "design, technology,
execution" under technical risks — roughly mapping to parameters, performance, and integration.
IPA's detailed frameworks are proprietary. The four-way split that emerged from the data is
more granular than anything in the published literature.

---

## Part 11: Final v3 Failure Mode Taxonomy (9 categories)

| # | Failure mode | Mechanism | Severity Ratio |
|---|---|---|---|
| 1 | Poor scoping | Scope definition failed to capture what the project needed | 0.21 |
| 2 | Unvalidated performance | Technology/component not proven to work in deployment context | ~0.40* |
| 3 | Unvalidated design parameters | Numerical inputs borrowed from wrong context without validation | ~0.25* |
| 4 | Unvalidated integration | Interfaces between systems never validated before deployment | ~0.35* |
| 5 | Regulatory & approvals | Regulatory pathway unmapped, misunderstood, or underestimated | 0.60 |
| 6 | Commercial & market | Business case rested on unvalidated or unviable commercial conditions | 0.59 |
| 7 | Coordination & stakeholders | Parties who needed to work together weren't set up to do so | 0.14 |
| 8 | Data & measurement | Data infrastructure inadequate for design, verification, or operations | 0.14 |
| 9 | Execution & logistics | Delivery plan insufficient for physical realities of implementation | 0.28 |

*Severity ratios for categories 2–4 are estimated from sub-cluster proportions; actual ratios
will be confirmed after full corpus reclassification.

### What changed from the 8-category proposal

- **"Technical assumptions" dissolved** — it was 30% of records, a catch-all. Split into
  three mechanism-level categories (#2, #3, #4) each answering a different PM question.
- **"Capability shortfall" absorbed** — 2.9% prevalence, records distribute naturally into
  #1 (poor scoping), #9 (execution & logistics), and others.
- **"Commercial viability" sub-cluster absorbed into #6** — overlaps with commercial & market
  and below prevalence threshold.
- **Net result: 9 categories**, up from 8, but with no catch-all and each category passing
  the mechanism, distinctiveness, actionability, and prevalence tests.

### Implementation: reclassification pass

The full corpus reclassification will use Haiku batch to classify all 12,376 adverse records
against the 9 v3 categories. Estimated cost: ~$8-12. The existing `failure_mode` field is
preserved as `failure_mode_v2`. The reclassification prompt is derived from
`FAILURE_MODE_DEFINITIONS_V3.md`, which must be updated to reflect the 9-category taxonomy
before the pass is run.

---

## Open Questions

1. Should the "no major failure stated" records be reclassified? Some may contain minor issues
   that were missed in v2 extraction. Others are genuine positive observations.

2. ~~Should `delay_category` be revised alongside `failure_mode`?~~ **Resolved: dropped entirely
   alongside `delay_magnitude`. Both are legacy fields.** (See Part 8.)

3. Can the failure mode reclassification and challenge tagging be done in a single LLM pass to
   reduce cost and ensure consistency? (Estimated combined cost: ~$10-15 for full corpus on
   Haiku batch.)

4. What minimum sample size should be required before surfacing challenge-based failure mode
   distributions in the dashboard?

5. ~~Should the "scaling to field" challenge's high design-assumption-failure rate (44%) be
   treated as signal or as evidence that design assumption failure is still acting as a
   catch-all?~~ **Resolved: design assumption failure is dissolved. The challenge analysis
   will be re-run after failure mode reclassification.**

6. The test pass showed 51% of records match exactly 2 challenges. Is this the right level of
   overlap, or should challenge definitions be tightened to increase exclusivity?

7. ~~After bottom-up clustering, how many of the original 10 failure modes survive intact vs
   need splitting or merging?~~ **Resolved: 9 categories. See Part 11.**

8. The validation pass showed zero low-confidence records (all ≥0.77). Is Haiku's confidence
   calibration reliable, or should a manual review of 50 boundary cases be done before full
   reclassification?
