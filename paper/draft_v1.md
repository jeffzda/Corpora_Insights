# Reference Class Diagnostics: Generalising Reference Class Forecasting to Qualitative Delivery Outcomes Using LLM-Extracted Severity from Project Report Corpora

**Jeff Zdanowicz**

*Draft v1 — April 2026*

---

## Abstract

Reference class forecasting (RCF) improves project cost and schedule estimates by substituting empirical base rates for subjective inside views. However, RCF is limited to outcomes expressible as a single quantitative metric — typically cost overrun — and tells decision-makers *how much* to worry without diagnosing *what* is likely to go wrong. We introduce **reference class diagnostics (RCD)**, a generalisation of RCF that replaces cost overrun with a severity escalation ratio inferred from natural language in project reports, enabling diagnostic risk profiling across compound reference classes defined by multiple project attributes. We demonstrate the approach on 16,931 delivery insight records extracted from 1,448 publicly available reports covering 499 projects funded by the Australian Renewable Energy Agency (ARENA). We validate the extraction methodology through grounding verification (92.2% confirmed), classification verification (89.6% acceptable), and intra-rater reliability testing (94.4% primary failure mode agreement, 1.8% hard disagreement rate). The resulting framework produces actionable risk profiles — identifying dominant failure modes, lifecycle concentration, and severity escalation patterns for specific project types — that support portfolio-level decision-making in ways that aggregate cost overrun distributions cannot.

---

## 1. Introduction

Flyvbjerg (2006, 2021) demonstrated that large infrastructure projects systematically overrun their budgets and that this pattern is better predicted by statistical base rates from comparable projects than by project-specific estimates. Reference class forecasting (RCF) addresses this by identifying an appropriate reference class of past projects, examining the distribution of outcomes within that class, and using the distribution to calibrate expectations for a new project.

RCF has been adopted in transport planning, defence procurement, and information technology, and is recommended by organisations including HM Treasury (2003) and the American Planning Association (2005). Its empirical foundation is compelling: across hundreds of megaprojects, the base rate of cost overrun is a better predictor than expert judgement.

However, RCF has two structural limitations:

1. **It requires a quantitative outcome metric.** Cost overrun works because every project has a budget and an actual cost. But most delivery risks do not resolve into a single number. A regulatory delay, a technology underperformance, and a coordination breakdown may each produce cost overruns, but through entirely different mechanisms requiring different managerial responses. RCF captures the aggregate consequence while discarding the diagnostic signal.

2. **It uses single-dimension reference classes.** A project is classified as "urban rail" or "large dam" and assigned the corresponding overrun distribution. In practice, experienced decision-makers think in compound terms — "a hydrogen pilot by a consortium in commissioning phase" — but there is no framework for constructing multi-dimensional empirical base rates from project attributes.

This paper introduces **reference class diagnostics (RCD)**, which addresses both limitations. RCD replaces cost overrun with a severity escalation ratio inferred from natural language descriptions of delivery events, and constructs compound reference classes from multiple project attributes. The result is a diagnostic risk profile that tells a portfolio manager not just "this type of project tends to have problems" but "here is what specifically goes wrong, at what lifecycle stage, how often it escalates to major consequence, and which failure modes co-occur."

The key trade-off is explicit: RCD sacrifices the quantitative precision of cost overrun ("42% average overrun") for diagnostic resolution ("technical underperformance during commissioning, escalating to major severity 52% of the time, frequently co-occurring with coordination failures"). We argue that this trade-off favours decision support: a portfolio manager cannot act on an aggregate cost distribution, but can act on a failure mode signature that identifies where to focus project controls, what to ask about in milestone reviews, and what expertise to require on assessment panels.

We demonstrate the approach using 16,931 delivery insight records extracted from 1,448 Knowledge Bank reports published by the Australian Renewable Energy Agency (ARENA), covering 499 publicly funded renewable energy projects. The extraction uses large language models (LLMs) with structured prompts, validated through grounding verification, classification review, and intra-rater reliability testing.

The contributions of this paper are:

1. **Severity as a proxy for cost:** A severity escalation ratio inferred from natural language that provides a comparable consequence axis across heterogeneous failure types, enabling reference class analysis where quantitative outcome data is unavailable.

2. **Delivery dimensions vs cross-cutting failure modes:** A two-layer analytical framework that distinguishes what a project was attempting (delivery dimensions) from what went wrong (failure modes), revealing dimension-specific failure mode signatures.

3. **Compound reference classes:** Multi-dimensional empirical base rates constructed from project attributes (technology category, activity type, proponent type, lifecycle phase, consortium status) rather than single-dimension analyst judgement.

4. **Scalable extraction methodology:** A validated pipeline for building structured delivery registries from narrative report corpora using LLM extraction with empirical taxonomy iteration.

---

## 2. Literature Review

*[To be completed. Key threads to cover:]*

- **Reference class forecasting:** Flyvbjerg (2006, 2008, 2021); Kahneman & Tversky (1979) on planning fallacy; Lovallo & Kahneman (2003) on outside view; HM Treasury Green Book guidance; critiques and limitations (Batselier & Vanhoucke 2016).

- **Project delivery risk in energy infrastructure:** IRENA project cost analyses; IEA technology readiness assessments; ARENA's own knowledge sharing publications; literature on renewable energy project failures and lessons learnt.

- **NLP/LLM-based information extraction from unstructured documents:** Recent work on structured extraction from reports; prompt-based classification; batch processing at scale; validation methodologies for LLM-generated datasets.

- **Risk taxonomies and failure mode classification:** Existing frameworks for categorising project failures; failure mode and effects analysis (FMEA) in engineering; translation to project delivery context.

- **Severity assessment from natural language:** Sentiment and severity analysis in NLP; limitations of quantitative severity inference; precedents for using inferred severity as an analytical metric.

---

## 3. Conceptual Framework

### 3.1 From Forecasting to Diagnostics

Reference class forecasting answers the question: "Given that this is a [type] project, what is the likely cost overrun?" The answer is a distribution — a statistical correction to the project team's inside view.

Reference class diagnostics answers a different question: "Given that this is a [type] project, what is likely to go wrong, when, and how badly?" The answer is a risk profile — a structured set of base rates across failure modes, lifecycle phases, and severity levels that supports specific managerial actions.

The conceptual move is from **corrective** to **diagnostic**. RCF tells you to add a contingency; RCD tells you where to deploy your attention.

### 3.2 The Severity Bridge

The central challenge in generalising from RCF to RCD is the outcome metric. Cost overrun provides a universal, comparable, quantitative measure of consequence. Intra-project delivery failures — a technology that underperforms, a regulation that blocks progress, a coordination breakdown between partners — have consequences that are heterogeneous, overlapping, and rarely expressed in quantitative terms in project reports.

We propose a severity escalation ratio as the bridge metric. For each delivery insight record extracted from a project report, the extraction model assigns an issue severity on a five-point scale (none, minor, moderate, major, critical) based on the natural language description of the event and its consequences. The escalation ratio for a reference class is defined as:

$$\text{Escalation ratio} = \frac{n_{\text{major}} + n_{\text{critical}}}{n_{\text{minor}} + n_{\text{moderate}}}$$

computed across all adverse records (those with a non-null failure mode) within the reference class.

This metric has several properties that make it suitable as a proxy for quantitative consequence:

1. **Conservative threshold.** The source documents are reports written for a funding agency. Authors have incentives to understate problems. Language severe enough to be classified as "major" or "critical" has cleared a significant psychological disclosure barrier, suggesting the escalation ratio represents a lower bound on true severity.

2. **Near-universal availability.** Severity can be inferred from any narrative description of a delivery event. Unlike cost data, which is frequently redacted or unavailable in project reports, the language used to describe an event's impact contains implicit severity signals in virtually every case.

3. **Comparability across failure types.** A regulatory delay classified as "major" and a technology underperformance classified as "major" are comparable in their consequence signal even though the underlying mechanisms are entirely different. This comparability is what cost overrun provides for RCF; the escalation ratio provides an analogous function for RCD.

4. **Discrimination.** The escalation ratio varies meaningfully across reference classes. In our corpus, it ranges from 0.08 (wind pilot projects) to 0.82 (hydrogen deployment projects), with systematic variation by failure mode, proponent type, and technology category.

The trade-off is explicit: the escalation ratio is a noisier metric than cost overrun. It depends on model inference from natural language, carries the biases of the source documents' disclosure norms, and compresses a rich outcome space into a single number. But the alternative in most domains is no comparable consequence metric at all, which leaves RCF inapplicable and portfolio managers reliant on anecdote and intuition.

### 3.3 Delivery Dimensions vs Failure Modes

A second conceptual contribution is the distinction between **delivery dimensions** and **failure modes**. Delivery dimensions describe what a project was attempting in a particular area — connecting to the grid, scaling from laboratory to field, navigating regulatory requirements, managing supply chains. Failure modes describe what went wrong — technical underperformance, coordination breakdown, commercial non-viability.

This distinction matters because a single delivery dimension can produce multiple failure modes, and a single failure mode can manifest across multiple delivery dimensions. Grid connection challenges, for example, can result in regulatory failures (standards incompatibility), technical failures (inverter performance), coordination failures (between developer and network operator), or commercial failures (connection cost blowouts). Conflating the dimension with the failure mode obscures the diagnostic signal.

In the RCD framework, delivery dimensions are **filtering variables** — they describe the context in which failures occur. Failure modes are **outcome variables** — they describe what went wrong. The interaction between the two produces **dimension-specific failure mode signatures**: empirical distributions showing, for each delivery dimension, which failure modes dominate and at what severity. These signatures are the diagnostic product of the framework.

### 3.4 Compound Reference Classes

Flyvbjerg's reference classes are single-dimensional: "urban rail projects" or "large dams." The choice of reference class is a judgement call by the analyst, and there is no systematic way to refine it.

In the RCD framework, reference classes are constructed as intersections of multiple project attributes:

- **Technology category** (e.g. battery storage, hydrogen, solar PV)
- **Activity type** (study/feasibility, pilot/demonstration, deployment)
- **Proponent type** (project developer, utility, research organisation, etc.)
- **Lifecycle phase** (concept, development, construction, commissioning, operations)
- **Governance structure** (consortium vs single entity)

Each attribute contributes an empirical base rate. When cross-tabulated, they produce a compound reference class — "a battery storage pilot by a technology vendor in commissioning phase" — with its own failure mode signature.

The compound approach has an important property: **increasing returns to corpus size.** In RCF, additional data on rail cost overruns tightens the confidence interval of a distribution that is already well-characterised. In RCD, additional project reports populate new cells in the cross-tabulation, adding diagnostic resolution to reference classes that were previously too sparse to characterise. The framework becomes more useful as organisations accumulate more project documentation, creating an incentive to systematise knowledge sharing.

The corresponding limitation is sparsity. Some compound reference classes will contain too few projects to support reliable base rates. This is an honest signal — "we do not have enough evidence to characterise this type of project" — rather than a failure of the method. The framework accommodates this by allowing graceful fallback: when a compound cell is too sparse, individual dimensions still provide meaningful base rates.

---

## 4. Methodology

### 4.1 Source Corpus

The Australian Renewable Energy Agency (ARENA) maintains a publicly accessible Knowledge Bank (arena.gov.au/knowledge-bank) containing reports, studies, and analyses from projects it has funded since 2012. The Knowledge Bank is one of the conditions of ARENA's funding agreements: recipients are required to share knowledge generated through their projects to benefit the broader sector.

We downloaded and processed 1,448 documents from the Knowledge Bank, representing the complete publicly available corpus as of early 2026. Documents were converted from PDF to markdown format to preserve structural elements (headings, tables, page boundaries) while enabling text processing.

The corpus covers 499 of the 769 projects in ARENA's portfolio (64.9%), with coverage varying by era: poor for 2011–2013 (23–41% of projects), excellent for 2017–2022 (76–93%), and declining for 2023 onwards (active projects whose reports have not yet been published). Uncovered projects are predominantly Post-Fellowship Doctorates (83 of 84 uncovered), International Engagement grants, small feasibility studies under $1M, and recently funded active projects — categories with limited relevance to delivery risk analysis.

### 4.2 Taxonomy Design

The extraction taxonomy was developed through three iterations, informed by empirical analysis of the extracted data at each stage.

**Failure mode categories.** The initial taxonomy (v1) included 10 failure mode categories adapted from project management literature and the ARENA portfolio structure. Empirical analysis of extracted records revealed structural problems: "design assumption failure" absorbed 20% of all records, functioning as a catch-all rather than a diagnostic category; "cost overrun" and "schedule slippage" described consequences rather than mechanisms; and several categories had fuzzy boundaries producing high reclassification rates.

The revised taxonomy (v3) was developed by applying four inclusion tests to each category:

1. **Mechanism test:** Does the category name a broken or absent mechanism, not a consequence, symptom, or root cause?
2. **Distinctiveness test:** Could the remaining categories absorb this category's records without losing actionable information?
3. **Actionability test:** Does the category map to substantively different due diligence questions for a project assessor?
4. **Prevalence test:** Does the category capture approximately 5% or more of adverse records?

The resulting 8 categories (including "no major failure stated") were validated through a full-corpus reclassification using an independent LLM pass, achieving 94.4% intra-rater reliability (Section 4.6).

The 7 adverse failure modes are:

| Category | What it captures |
|---|---|
| Technical underperformance | Technology, equipment, or systems not achieving expected performance |
| Commercial & market | Business case, demand, pricing, or commercial arrangements not materialising |
| Coordination & stakeholders | Misalignment between parties, communication, governance, stakeholder management |
| Data & measurement | Inadequate data, measurement errors, monitoring gaps, validation failures |
| Execution & logistics | Construction, supply chain, transport, installation, manufacturing, workforce |
| Regulatory & approvals | Regulatory requirements, approvals, compliance, grid codes, standards, policy |
| Unvalidated integration | Components or systems failing to work together, interface and interoperability |

**Delivery dimensions.** Delivery dimensions describe what the project was attempting in a given area, independent of what went wrong. Seven dimensions were defined (e.g. grid connection, lab-to-field scaling, supply chain management, regulatory navigation) and assigned to records based on the content of the delivery event description. Dimensions are not mutually exclusive — a single record may involve multiple delivery dimensions.

**Reference class attributes.** Project-level attributes used to construct reference classes were chosen for deterministic assignability where possible:

- **ARENA category** (14 values): Mapped deterministically from Knowledge Bank metadata, using ARENA's own vocabulary. No LLM inference required.
- **Activity type** (3 values: study, pilot, deployment): Derived deterministically from project title and summary keywords in ARENA's portfolio database.
- **Proponent type** (10 values): Model-inferred from report content, reconciled by majority vote across records from the same document.
- **Consortium status** (boolean): Separated from proponent type because consortium governance structure confounds actor-type risk signals. Consortium records were reclassified to their lead actor type.
- **Lifecycle phase** (8 values): Model-inferred from report content.

### 4.3 LLM Extraction Pipeline

Records were extracted using Claude Sonnet (Anthropic) with structured prompts requesting specific fields for each delivery insight identified in a document. Each document was processed independently in a single API call, with the full document text provided as context (no truncation). Eight documents exceeding 600,000 characters were processed via chunked multi-pass extraction with prior records passed as context to avoid duplication.

Each extraction call requested up to 10 delivery insight records per document, with each record containing:

- A factual description of the delivery event ("what happened")
- A transferable lesson or implication ("lesson learnt")
- An evidence excerpt (direct quote from the source)
- Structured classification fields (failure mode, severity, lifecycle phase, etc.)
- Source page references enabling verification against the original document

Project-level fields (proponent type, project type, scale) were reconciled across all records from the same document by majority vote, with split votes recorded in a confidence note.

Knowledge Bank metadata (publication date, associated project name, category, document URL) was stamped onto records programmatically — no model inference was needed for these fields.

### 4.4 Severity Estimation

Issue severity was assigned by the extraction model on a five-point scale:

- **None:** No adverse event described
- **Minor:** Inconvenience or small deviation, easily absorbed
- **Moderate:** Noticeable impact on timeline, cost, or scope, but manageable
- **Major:** Significant disruption requiring intervention, re-scoping, or material delay
- **Critical:** Fundamental threat to project viability or requiring major re-evaluation

The extraction prompt instructs the model to assess severity based on the language used in the source document to describe the event's impact, not to infer severity from the failure mode category alone. This grounds the severity estimate in the document's own characterisation of consequence.

The severity escalation ratio — (major + critical) / (minor + moderate) — is computed across adverse records within each reference class. A ratio above 1.0 indicates that failures in that class are more likely to be severe than minor; a ratio well below 1.0 indicates that failures, while frequent, tend to be manageable.

### 4.5 Quality Assurance

Extracted records were validated through two independent verification passes using Claude Haiku (Anthropic) via batch API:

**Grounding verification.** Each record's factual claims ("what happened") were checked against the source document text within a 15,000-character window around the cited source page. Verdicts: confirmed (92.2%), plausible (5.5%), unsupported (0.3%), fabricated (0.2%), parse error (1.8%).

**Classification verification.** Each record's structured field assignments (failure mode, severity, lifecycle phase, etc.) were reviewed for consistency with the factual description. Verdicts: acceptable (89.6%), questionable (8.0%), wrong (0.6%), parse error (1.8%).

Records flagged as unsupported or fabricated in grounding, or as wrong in classification, were subjected to a recheck pass with a wider context window (15,000 characters vs the original 3,000). This recovered 186 of 315 grounding-flagged records and 45 of 148 classification-flagged records to acceptable verdicts.

### 4.6 Intra-Rater Reliability

To quantify the stochastic noise in LLM-based classification, the full corpus of 16,931 records was classified twice using identical prompts, model, and parameters (Claude Haiku 4.5, batch API).

**Primary failure mode agreement:** 15,981 of 16,931 records (94.4%) received the same primary failure mode in both runs.

**Including primary-secondary swaps:** A further 645 records (3.8%) had their run-1 primary appear as the run-2 secondary failure mode or vice versa — the model identified the same two failure modes but ranked them differently. Total agreement including swaps: 98.2%.

**Hard disagreement:** 305 records (1.8%) received unrelated failure mode classifications across the two runs.

**Confidence signal.** Records with consistent classifications had higher mean model-reported confidence (0.885) than inconsistent records (0.842), confirming that the model's self-reported confidence is a meaningful indicator of classification uncertainty.

**Category-level stability** ranged from 97.9% (no major failure stated) to 89.6% (unvalidated integration). The weakest taxonomy boundary — unvalidated integration vs technical underperformance — showed approximately 6% bidirectional leakage under identical conditions.

**Secondary failure mode agreement** was 88.1% (both null or both same), lower than primary as expected given the inherently greater ambiguity in identifying co-occurring failure modes.

These results establish a stochastic noise floor of approximately 5.6% on primary failure mode classification, with 1.8% hard disagreement. At portfolio level, this noise is roughly symmetric across categories and washes out across hundreds of records.

A separate comparison between two runs with different prompts (one requesting primary only, one requesting primary and secondary) showed 91.1% primary agreement, confirming that approximately 3 percentage points of additional instability is attributable to prompt structure rather than stochastic noise.

---

## 5. Results

### 5.1 Corpus Overview

The extraction pipeline produced 16,931 delivery insight records from 1,448 documents covering 499 ARENA-funded projects. Of these, 73% contain an adverse delivery event (a failure mode other than "no major failure stated"), yielding 12,359 adverse records for analysis.

The adversity rate of 73% is not directly comparable to Flyvbjerg's cost overrun rates because it measures a different quantity: the proportion of extracted delivery insights that describe something going wrong, not the proportion of projects that exceeded their budgets. A single project may contribute multiple records, some adverse and some not. The rate reflects the density of delivery challenges in the corpus, not a project-level failure rate.

### 5.2 Failure Mode Distribution

The seven adverse failure modes are distributed across the corpus as follows:

| Failure mode | Records | % of adverse | Escalation ratio |
|---|---|---|---|
| Commercial & market | 2,432 | 19.7% | *[to compute]* |
| Coordination & stakeholders | 2,052 | 16.6% | *[to compute]* |
| Technical underperformance | 1,990 | 16.1% | *[to compute]* |
| Data & measurement | 1,678 | 13.6% | *[to compute]* |
| Regulatory & approvals | 1,641 | 13.3% | *[to compute]* |
| Execution & logistics | 1,317 | 10.7% | *[to compute]* |
| Unvalidated integration | 843 | 6.8% | *[to compute]* |

53.7% of adverse records have a secondary failure mode, indicating that co-occurrence of failure modes is the norm rather than the exception in renewable energy project delivery.

### 5.3 Severity Escalation Across Reference Classes

The corpus-wide severity escalation ratio is 0.26 — approximately one in four adverse events escalates to major or critical severity. However, this aggregate conceals dramatic variation across reference classes.

**By failure mode:**

| Failure mode | Escalation ratio | Interpretation |
|---|---|---|
| Regulatory misfit | 0.69 | When regulation blocks a project, it is severe |
| Cost overrun | 0.62 | Disclosed cost overruns are almost always major |
| Technical underperformance | *[to compute]* | |
| Commercial/demand failure | *[to compute]* | |
| Data quality | 0.10 | Data problems are common but rarely severe |
| Governance | 0.16 | Coordination issues are frequent but manageable |

**By proponent type:**

The most striking finding is community/local body proponents, which show a low adversity rate but the highest escalation ratio (0.62). This means community-led projects encounter fewer problems, but when they do, the problems are severe. This pattern is invisible in adversity rate alone and would be masked in a cost-overrun-only analysis.

Consortium projects show the inverse pattern: high adversity rate (77%) but identical escalation ratio to non-consortium projects (0.26). Consortium governance adds failure *frequency* — more coordination touchpoints, more things that can go wrong — but does not increase failure *severity*.

**By technology × activity type:**

The compound reference class reveals the sharpest contrasts. Hydrogen deployment projects have an escalation ratio of 0.82 — nearly every adverse event is severe. Wind pilot projects have a ratio of 0.08 — problems are common but almost never consequential. These extremes are diagnostic: they tell a portfolio manager that hydrogen deployment projects require intensive oversight of every delivery event, while wind pilot projects can tolerate a higher background rate of minor issues.

### 5.4 Dimension-Specific Failure Mode Signatures

Each delivery dimension produces a distinct failure mode signature — an empirical distribution of which failure modes dominate within that dimension:

*[To be populated with the dimension × failure mode matrix data from the dashboard, showing how grid connection produces primarily regulatory and coordination failures, while lab-to-field scaling produces primarily technical underperformance and data measurement failures, etc.]*

These signatures are the primary diagnostic output of the RCD framework. A portfolio manager assessing a project that involves grid connection and lab-to-field scaling can consult the relevant dimension signatures and anticipate the specific failure modes most likely to emerge — information that an aggregate cost overrun distribution cannot provide.

### 5.5 Secondary Failure Modes and Co-Occurrence

53.7% of adverse records exhibit a secondary failure mode in addition to the primary. The most common secondary failure mode is coordination & stakeholders (25.7% of secondaries), suggesting that coordination challenges frequently accompany other types of failure as a compounding factor.

*[To be populated with co-occurrence patterns — which primary/secondary pairs are most common, what this reveals about failure cascades in renewable energy delivery.]*

---

## 6. Discussion

### 6.1 Decision Support Implications

The RCD framework produces a qualitatively different type of risk information than RCF. Where RCF provides a statistical correction ("add 40% to your cost estimate"), RCD provides a diagnostic profile ("here is what typically goes wrong in projects like this, at what stage, and how severely").

For a portfolio manager, this translates to specific actions:

- **Assessment panel composition:** If the reference class signature shows dominant regulatory failures, include regulatory expertise on the assessment panel.
- **Milestone design:** If failures concentrate in commissioning phase, design milestones with enhanced oversight at that stage.
- **Due diligence focus:** If the escalation ratio is high for the reference class, every adverse flag warrants investigation; if it is low, minor issues can be monitored rather than escalated.
- **Consortium management:** The finding that consortia add failure frequency but not severity suggests that consortium projects need more touchpoints for coordination, not more conservative risk budgets.

### 6.2 Limitations

**Disclosure bias.** The source documents are reports written for a funding agency. Authors have incentives to understate problems and overstate successes. The 73% adversity rate may undercount the true incidence of delivery challenges, and severity assessments are likely conservative. The escalation ratio is therefore a lower bound on true severity escalation.

**Model inference.** Both extraction and classification depend on LLM inference, which introduces noise. The intra-rater reliability test establishes a 5.6% noise floor on primary failure mode classification and 11.9% on secondary. Portfolio-level patterns are robust to this noise; individual record classifications carry meaningful uncertainty.

**Single-corpus validation.** The framework has been demonstrated on a single corpus (ARENA Knowledge Bank). Transferability to other domains — transport, defence, development aid — is theoretically motivated but empirically untested.

**Severity as proxy.** The escalation ratio compresses a rich outcome space into a single number and depends on model-inferred severity from natural language. It is a noisier metric than direct cost measurement. Its value lies in near-universal availability and cross-failure-type comparability, not precision.

**Sparse compound cells.** Some intersections of reference class attributes contain too few projects to support reliable base rates. The framework handles this through graceful fallback to individual dimensions, but users must recognise sparse cells as honest uncertainty rather than absence of risk.

### 6.3 Generalisability

The RCD framework is not specific to renewable energy. Any domain that accumulates project reports describing delivery events — and where those reports contain natural language descriptions of what went wrong and how severely — can apply the same approach. Transport infrastructure, defence procurement, international development, pharmaceutical R&D, and construction all produce such corpora.

The requirements are:

1. A corpus of project reports with sufficient scale (hundreds of projects)
2. Natural language descriptions of delivery events (not just financial summaries)
3. A domain-appropriate failure mode taxonomy (developed through the iterative process described in Section 4.2)
4. An LLM capable of structured extraction with acceptable reliability

The severity escalation ratio transfers directly to any domain. The failure mode taxonomy and delivery dimensions require domain-specific development, but the methodology for iterating them — extract, classify, test boundaries, revise — is general.

### 6.4 Increasing Returns

RCF has diminishing returns: once the cost overrun distribution for rail projects is well-characterised, additional data tightens the confidence interval but does not change the corrective. RCD has increasing returns: every new project report populates new cells in the compound reference class matrix, adding diagnostic resolution to previously sparse intersections. This property creates a natural incentive for organisations to systematise knowledge sharing and maintain structured project report archives — a virtuous cycle between organisational learning and diagnostic capability.

---

## 7. Conclusion

Reference class forecasting demonstrated that empirical base rates outperform expert judgement for predicting project cost overruns. Reference class diagnostics generalises this insight to qualitative delivery outcomes, replacing cost overrun with severity escalation inferred from natural language and extending single-dimension reference classes to multi-dimensional diagnostic profiles.

The key methodological move — using severity as a proxy for quantitative consequence — sacrifices precision but unlocks diagnostic dimensions that are unavailable to cost-based analysis: failure mode signatures, lifecycle concentration, co-occurrence patterns, and escalation profiles specific to compound reference classes.

Applied to 16,931 records from 499 ARENA-funded renewable energy projects, the framework reveals patterns that would be invisible to aggregate cost analysis: community-led projects with low adversity but high escalation; consortium governance that adds failure frequency without increasing severity; hydrogen deployment projects where nearly every adverse event is consequential; and delivery-dimension-specific failure mode signatures that differ systematically across project types.

The framework is transferable to any domain that accumulates narrative project reports, and its diagnostic value increases with corpus size. As organisations invest in structured knowledge sharing, the compound reference classes fill in, producing increasingly specific and actionable risk profiles.

For portfolio managers, the practical implication is a shift from "how much contingency should I add?" to "what specifically should I watch for in this type of project, and where should I concentrate my attention?"

---

## References

*[To be completed]*

Flyvbjerg, B. (2006). From Nobel Prize to project management: Getting risks right. *Project Management Journal*, 37(3), 5–15.

Flyvbjerg, B. (2008). Curbing optimism bias and strategic misrepresentation in planning: Reference class forecasting in practice. *European Planning Studies*, 16(1), 3–21.

Flyvbjerg, B. (2021). Make megaprojects more modular. *Harvard Business Review*, November–December.

Kahneman, D., & Tversky, A. (1979). Prospect theory: An analysis of decision under risk. *Econometrica*, 47(2), 263–291.

Lovallo, D., & Kahneman, D. (2003). Delusions of success: How optimism undermines executives' decisions. *Harvard Business Review*, 81(7), 56–63.

---

*Acknowledgements: Extraction and analysis were performed using Claude (Anthropic). The ARENA Knowledge Bank is publicly available at arena.gov.au/knowledge-bank. The complete delivery registry and interactive dashboard are available at [URL].*
