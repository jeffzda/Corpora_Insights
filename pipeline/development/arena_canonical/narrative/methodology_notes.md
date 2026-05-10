# Calibration / Tagging Methodology Notes

Written 2026-04-30. Captures the state of the prompt-calibration / per-record-tagging work as a checkpoint, including conceptual findings worth preserving for the grey report.

---

## 1. The 60-record calibration sample (verified accurate)

Built by `29_build_calibration_sample.py`. Output: `calibration_sample.md` (60 events, hand-tagged template) + `calibration_sample.json` (machine-readable manifest).

Stratification:

- **40 events: construct-neutral** stratified random across `(kb_category × kb_document_type × narrative_length_quartile)`. All three axes are metadata facts, not judgments about content. This is the baseline.
- **20 events: boundary-mining (hypothesis-driven, transparently labelled)** — 4 events from each of q5, q25, q50, q75, q95 NN-entropy quintiles of the 800-event prototype sample. Explicitly flagged in the markdown preamble as hypothesis-driven; comparing tag distributions between the neutral and boundary strata is itself diagnostic about whether NN-entropy maps to the construct.
- **Train/holdout split** — 41 train / 19 holdout, stratified within each kind. Train events become few-shot anchors; holdout events stay invisible to the prompt and serve as evaluation set.

Methodological reasoning behind the structure: an earlier version stratified directly on construct-laden bins (e.g. "stub claim" vs "mechanism-level"), which would have baked the prompt-designer's priors into where the boundaries sit. The construct-neutral stratification keeps the construct work with the human tagger.

## 2. Tagging schema (v1, in calibration_sample.md preamble)

Four axes, applied per record:

- **Generalisability**: low / mid / high — is the underlying mechanism transferable?
- **Valence**: negative / neutral / positive — causal evaluative load, not sentiment
- **Specificity**: substantive / stub — is a mechanism named?
- **PM-actionability**: actionable / informational / out_of_scope — can it become a deal-structure lever?

Plus per-record `candidate_failure_mode_label` (one-line abstraction) and `notes` (boundary-flag observations).

Five anti-patterns: topic-breadth ≠ generalisability, sentiment ≠ valence, recommendation-shape ≠ specificity, researcher-actionable ≠ PM-actionable, survival bias.

## 3. Multi-rater results

Three sources tagged the calibration set:

- **Jeff (hand)**: E01–E12 with full rationales, applying the construct rules through live discussion.
- **Opus 4.7 agent** (with original prompt + 4 of Jeff's tags as anchors): tagged the 56 non-anchor events.
- **Haiku 4.5 agent** (with refined v1 prompt + 6 anchors including 2 anti-anchors): tagged the same 56 events.

Inter-rater agreement on the 8 events Jeff hand-tagged that the agents also tagged (E02, E04, E06–E09, E11, E12):

| Axis | Opus vs Jeff | Haiku vs Jeff |
|---|---|---|
| generalisability | 50% | 75% |
| valence | 88% | 75% |
| specificity | 88% | 75% |
| PM-actionability | 75% | 62% |
| exact 4-axis match | 25% | 50% |

Opus vs Haiku on the full 56 events: gen 52%, val 79%, spec 86%, PM 70%, exact 21%.

Diagnostic findings:

- **Opus had a systematic gen-axis bias upward**: where Jeff said `low` (no transferable mechanism), Opus said `mid` (topic recurrence). The anti-pattern "topic-breadth ≠ generalisability" wasn't cutting through.
- **The refined v2 prompt (with anti-anchors) shifted Haiku's gen distribution closer to Jeff's**: 48% low / 38% mid / 14% high (vs Opus's 14% / 61% / 25%).
- **Haiku had a smaller-model penalty on val/spec/PM** of ~13pp each, mostly on records with implicit-but-strong causal claims.

## 4. The "did something happen?" binary primitive

Late in the work we ran a separate Haiku binary classifier asking just: *did the record describe something that actually happened on a specific project, or is it descriptive/conceptual/forward-looking content?*

Results on Jeff's 12 hand-tagged events:

- Strict match (val=neutral ↔ no_did_not_happen, val=non-neutral ↔ yes_happened): **11/12 = 92%**
- Lenient match (val=non-neutral must be yes_happened; neutral always ok): **12/12 = 100%**

Distribution on full 60: 23 yes_happened (38%) / 37 no_did_not_happen (62%) — tracks the conservative reading we wanted.

The single strict-match miss (E07, subcontractor contracts awarded) is genuinely borderline: contracts *were* awarded (yes_happened correct), but the outcome direction was just descriptive facts (Jeff val=neutral correct). The binary "did something happen?" is a strict subset of valence — "neutral" can be either "nothing happened" or "something happened with neutral outcome".

This decomposes valence into two clean stages:

- **Stage 1**: did something happen on a specific project? → yes / no
- **Stage 2 (only on yes_happened)**: outcome direction → positive / negative / neutral / not_stated

The four-way Stage 2 (introducing `not_stated`) separates "outcome was neutral" from "outcome wasn't on the page" — different epistemically; the latter may be recoverable from document context.

## 5. Conceptual findings worth preserving

### 5.1 Valence and specificity aren't fully orthogonal

Both axes depend on whether the record contains causal content. They decompose causation along different facets:

- **Valence** = the *outcome* side of causation (good / bad result asserted)
- **Specificity** = the *mechanism* side of causation (the *how* named)

A record can carry one without the other. The four-corner matrix:

| | spec=substantive | spec=stub |
|---|---|---|
| val=non-neutral | event + mechanism (failure-mode-shaped) | event + bare outcome (the stub-claim archetype) |
| val=neutral | mechanism in abstract (description without measured event) | neither — pure descriptive scaffolding |

All four corners are populated by real records. The val=non-neutral + spec=stub corner is the most diagnostic — these are records that *feel* like failure modes but don't yet carry transferable mechanism content.

### 5.2 Literal-tags + candidate-label split

Tags hug what the record literally says. The `candidate_failure_mode_label` field is where pattern abstraction happens — it can name the underlying failure mode even when the record's literal content is stub-level. This separation prevents tag distributions from drifting (everything looking gen=high if you squint) while preserving the abstraction signal for taxonomy work.

### 5.3 Strict event-detection discipline

Be very strict about "did something specifically happen on a project". Most records in synthesis / lessons / strategy documents are descriptive scaffolding (forecasts, definitions, market context, mechanism logic in the abstract, recommendation-shape language) — not events. The val=neutral cell is therefore much larger than initial intuition suggests; the val=non-neutral cell is correspondingly small but is exactly the failure-mode-rich subset we want.

Specifically: present-tense causal verbs ("X enables Y, which lowers Z") in general-principle exposition do NOT count as events. They describe how a mechanism works in concept, not what occurred on a specific project with measured outcomes.

### 5.4 Provenance / authorial commitment

Hedging constructions ("are described as", "is identified as", "is reported to be") obscure who's asserting and on what evidentiary basis. Without direct authorial commitment, valence claims default to neutral. This was originally a separate "provenance rule" but it folded cleanly into the strict event-detection discipline once we got the framing right.

---

## 6. The atomicity-vs-mechanism tradeoff (major structural finding)

### 6.1 The discovery

While checking whether the extraction prompt was calibrated to capture causal mechanisms, we found that **it was**: `pipeline/prompts/extract.md` says `what_happened: "cause, mechanism, and impact"` and the quality floor requires "the specific mechanism, not just the category". `domains/arena/prompts/extract.md` lists "mechanisms (how or why something happened)" as one of the explicit finding types.

But the extraction prompt also imposes an **atomicity rule**: "one mechanism per record; one record per mechanism" / "atomicity: emit same number of records as distinct findings".

These two instructions compete when source documents present mechanism content in **structurally adjacent** form — i.e. as separate bullet points where one bullet states the outcome and others explain why.

### 6.2 The Middleback Ranges PHES case

doc_0705 section 10.3 (Conclusions) presents four bullets:

1. *"Price arbitrage and FCAS revenues from a stand-alone pumped hydro facility are relatively modest compared to the capital cost of such a facility..."* (the outcome)
2. *"Revenue models are very sensitive to the assumptions on which they are based..."* (sensitivity to competing-asset penetration)
3. *"Increasing the size of the storage facility does not proportionally increase the revenues..."* (capacity-bounded arbitrage opportunity)
4. *"The direct public benefit ($21M p.a.) is more than the direct benefit a private investor would derive ($24M p.a. less OPEX of $8M)..."* (externality leakage to consumers)

Each bullet was correctly extracted as a separate atomic record (0054, 0048, 0049, 0053). Reading them together, they form a coherent multi-mechanism causal story for why pumped hydro revenues are modest:

- Market saturation in storage services (bullet 2)
- Capacity-bounded marginal revenue (bullet 3)
- Externality leakage to consumers (bullet 4)

Reading record 0054 (E08) *in isolation*, the mechanism story is invisible. The record looks like a stub claim. The mechanism was in the source document and was extracted — but distributed across separate atomic records.

### 6.3 Implications

- **spec=stub at per-record level may over-count true stubs.** Records that read as stubs in isolation may have mechanism content in adjacent records from the same document.
- **Per-record candidate labels capture record-level patterns, not parent failure modes.** The four bullets above would receive four different candidate labels (one for each aspect — modest revenues, model sensitivity, scaling, public-private divergence). They wouldn't naturally cluster by label, even though they describe different aspects of one underlying failure mode.
- **Failure-mode taxonomy synthesis cannot be a mechanical aggregation of per-record labels.** It requires synthesis across records that share an underlying failure mode but have different per-record content.

### 6.4 Architectural options for handling this

Important clarification first: **the dedup pipeline does not solve this**. We have been operating on event records (from `corpus_run/*_v2_dist999.json`), where each event is a seed record + corroborators. For Middleback Ranges (62 records, single document), the dedup output is 62 records → 62 events (zero reduction) — all four of records 0048, 0049, 0053, 0054 are their own singleton events. This is correct: dedup answers *"are these records describing the same finding?"*, and the four bullets describe distinct findings (revenue level, model sensitivity, scaling, public-private divergence). What's needed is a higher-level operation that answers *"do these distinct findings describe different aspects of the same underlying failure mode?"* — operating above the event level, not within it.

Three architectural options for that higher-level operation:

1. **Within-document failure-mode clustering as a downstream stage.** Take all events from one document (or one project), ask an LLM "which events describe different aspects of the same underlying failure mode?", produce failure-mode groups *across distinct events*, synthesise parent labels at the group level. Most tractable; doesn't require re-extraction.
2. **Re-extraction with explicit failure-mode tagging.** Each record carries a `failure_mode_tag` field assigned at extraction time so adjacent-bullet records share a tag. Expensive — full re-extraction.
3. **Multi-pass at taxonomy time.** Cluster on embeddings, then ask an LLM "what failure mode unifies this cluster?" with human review.

Option 1 is the path of least resistance for current work. Note that option 1 operates on *events*, not raw records — so it composes cleanly with the existing dedup output.

### 6.5 The `lesson` field carries the synthesis we were missing

After spot-checking the four Middleback records (0048, 0049, 0053, 0054) against their source bullets, a more important finding emerged: **a substantial portion of the cross-bullet synthesis is already happening at extraction time, but it lands in the `lesson` field rather than the `narrative` field.**

Extraction schema (per `pipeline/prompts/extract.md`) separates:
- `narrative` (what_happened): "Detailed narrative of the finding or event — cause, mechanism, and impact. Include specific numbers, durations, dollar amounts, and named entities."
- `lesson` (lesson_learnt): "The transferable implication — what a practitioner in a similar situation should do differently, watch for, or replicate. Must be specific enough to act on without reading the source document."
- `evidence` (evidence_excerpt): verbatim quote from source
- `intervention` (intervention_note): how it was resolved/mitigated

Per-record breakdown for the four bullets:

| Record | Narrative | Lesson |
|---|---|---|
| 0054 (bullet 1) | ≈ source bullet, literal claim | "Do not rely solely on merchant energy arbitrage... long asset life (50+ years) and **system value (price suppression, firming)** must be incorporated, potentially requiring capacity market or contract-for-difference" — pulls in bullet 4's externality concept ("price suppression") and adds mitigation suggestions not in source |
| 0048 (bullet 2) | ≈ source bullet | Bullet-local: explicit sensitivity analysis on battery penetration + Snowy 2.0 |
| 0049 (bullet 3) | Adds modelled revenue figures ($24M/$39M/$43M for 110/220/330 MW) NOT in bullet 3's literal text — pulls from elsewhere in section 10 | "market saturation effects cause revenues to grow sub-linearly" — connects to bullet 2's competitive-market argument |
| 0053 (bullet 4) | Local computation ($24M − $8M = $16M) + summarising sentence | "may require public co-investment or concessional financing" — synthesises the policy implication |

**Cross-bullet synthesis at the narrative level is partial** (most occurs in 0049 and 0053, both of which pull in adjacent material). **Cross-bullet and cross-record synthesis at the lesson level is much more pronounced** — lessons routinely incorporate context from elsewhere in the document and add model-inferred mitigations.

#### Implications

1. **The atomicity-vs-mechanism tradeoff is partially mitigated by the lesson field.** The extraction prompt deliberately reserves the lesson field for synthesis ("the transferable implication") — which is exactly the failure-mode-shaped abstraction we want. Spec=stub on a record's narrative does not necessarily mean the record carries no failure-mode content; the lesson field may carry it.

2. **We have been tagging only the narrative field.** The calibration_sample.json populates the `narrative` field as the input to taggers. This is correctly conservative for literal-claim purposes (e.g. dedup matching), but under-represents what the extraction has captured. For failure-mode taxonomy work, we should be tagging on **narrative + lesson together**, or primarily on `lesson`.

3. **Two-stage workflow**: narrative-level dedup (which we already have) → lesson-level taxonomy (which is the new operation). The two operations use different fields because they're asking different questions.

4. **Lesson is model-synthesised, not literal.** It's higher in epistemic interpretation than the narrative — it includes inferred mitigations and synthesised cross-context. That's a tradeoff: more failure-mode-shaped content but lower direct grounding. For the grey report, this should be acknowledged: the failure-mode taxonomy is built partly on extracted-and-synthesised content, not purely on document-literal claims.

#### Lessons mix grounded synthesis with model invention

A grounding check on the four Middleback records makes this explicit. Record 0054's lesson suggests "capacity market or contract-for-difference mechanisms"; record 0053's lesson suggests "public co-investment or concessional financing". A grep across the entire 462-line source markdown for `cfd | contract for difference | capacity market | concessional | co-invest | underwrit | subsid` returned **zero hits**. None of the suggested mitigations appear anywhere in the document or in any other extracted record from doc_0705 — they are **pure model invention** drawn from training-data priors about general policy-mechanism vocabulary for renewable infrastructure.

Compared to the lesson's *grounded* synthesis content:
- "price suppression" in 0054's lesson generalises a measured claim in record 0051 ("reduces South Australian wholesale electricity prices by an average of $1.60/MWh") — the term is the model's articulation, but the underlying mechanism is documented.
- "system value (firming)" — "firming" doesn't appear in source; this is model-prior vocabulary for the general capability of dispatchable storage. Not literally documented but consistent with the document's framing.

So the lesson field carries **two different kinds of content**:

| Kind | Example | Status |
|---|---|---|
| Document-grounded cross-record synthesis | "price suppression" generalising 0051's price-reduction claim | Useful; faithful to document evidence |
| Pure model invention from priors | CfD / capacity market / concessional financing mitigations | Plausible but ungrounded |

**Implication for the failure-mode taxonomy**: lessons should be treated as containing both flavors. For mitigation suggestions specifically (the part most prone to model invention), a grounding check against either source documents or extracted records' evidence fields would distinguish documented mitigations from model-suggested ones. For the grey report:

> "The failure-mode taxonomy uses extracted records' lesson fields, which combine document-grounded synthesis (cross-bullet mechanism unification) with model-suggested mitigations drawn from training-data priors. Mitigation language that does not match content in source documents should be treated as suggested rather than evidenced."

Three handling options:

1. **Accept and disclose** — use lessons; document the mixed content in methodology. Cheapest, honest if disclosed.
2. **Grounding check** — for any lesson term used in the taxonomy, require it to appear in source markdown or in a record's evidence field. Filters invention; loses some valuable model synthesis.
3. **Re-extract with stricter grounding** — modify extraction prompt to separate document-grounded lesson content from model-suggested mitigations into different fields. Most expensive.

Option 1 is the realistic choice for current work, with the methodology disclosure built in.

#### Model invention is not limited to mitigations — it also affects cause-and-effect framing in lessons

A grounding check on the cause-and-effect language (not the mitigations) used in the four Middleback lessons: 7 of 9 C&E framing terms returned zero hits in source. The narrative field is much cleaner — most C&E framing terms appear only in lessons:

| Term | Narrative hits | Lesson hits | Source markdown hits |
|---|---|---|---|
| "price suppression" | 0 | 2 | 0 |
| "system value" | 0 | 1 | 0 |
| "market saturation" | 0 | 1 | 0 |
| "sub-linear" | 0 | 1 | 0 |
| "downside risk" | 0 | 2 | 0 |
| "commercial basis" | 0 | 1 | 0 |
| "social return" | 1 | 0 | 0 |
| "firming" | n/a | n/a | 2 (grounded) |

The most consequential is "market saturation effects" in 0049's lesson. Bullet 3 states the *observation* (non-proportional scaling). The lesson adds a *causal explanation* (market saturation as the cause). The cause is the model's interpretation, not the document's claim.

This produces a layered epistemic structure:

1. **Observation layer** (grounded) — the document records that something happened (e.g. "scaling is non-proportional"). Lives in narrative; sometimes in evidence verbatim.
2. **Causal-explanation layer** (model-interpretive) — the model articulates the mechanism explaining the observation (e.g. "market saturation causes sub-linear scaling"). Lives mostly in lesson; uses model-prior vocabulary.
3. **Mitigation layer** (pure model invention) — proposed actions to address the failure mode (e.g. "capacity market, CfD"). Lives only in lesson; not in source.

For failure-mode taxonomy specifically: identifying that a failure mode *exists* and that it *recurs* can be grounded via narratives. Explaining *why* it occurs is partly model-interpretive. The grey report should disclose this layered structure rather than treating all extracted content as document-grounded.

For Jeff's stated focus (identifying failure modes, not prescribing mitigations), this is workable: the observations and pattern recognition can be grounded; the causal-explanation layer carries forward as model-interpretive context (useful but flagged); the mitigation layer is set aside.

#### Atomicity does not split explicitly-linked cause-effect pairs

A separate question: has atomicity fragmented documented cause-effect pairs into separate records (e.g. effect in one record, cause in another)? Empirical answer for doc_0705: **no**.

The source markdown contains 5 sentences with explicit causal connectives ("because", "due to", "attributing"). Each was captured as a single record with cause and effect preserved together:

| Source sentence (paraphrased) | Record |
|---|---|
| design not selected because considered premature | 0003 |
| AEMO forecasts supply risks due to interconnectedness with Victoria | 0007 |
| capital costs non-conclusive because project still evolving | 0039 |
| high plant redundancy warranted given high commercial value of availability | 0041 |
| consumer surplus analysis simplistic due to demand-elasticity assumptions | 0052 |

5 of 5 explicit cause-effect sentences captured as single records. The atomicity rule respects sentence boundaries; explicit "X because Y" pairs stay together.

Where atomicity *does* fragment is **implicit cause-effect relationships that span sentences or bullets without explicit linking**. The section 10.3 four-bullet case is an example, but those bullets are related observations rather than explicit cause-effect pairs — the source never asserted causal links between them. So atomicity isn't *splitting* explicit pairs in those cases; the explicit pairs never existed in source. The cross-record reconciliation needed isn't recovering documented cause-effect but **inferring** cause-effect from co-occurring observations.

This is a more reassuring finding than the lesson-field invention finding. Where the document explicitly stated causation, the extraction preserved it. The model-interpretive layer in lessons (market saturation, downside risk, etc.) fills in causes that the document never stated explicitly — which is interpretive but not corrupting documented evidence.

---

## 7. Epistemic position (locked, 2026-04-30)

After working through the lesson-field invention finding (§6) and the atomicity check (§6.6), the following epistemic stance is adopted as the methodological foundation for failure-mode taxonomy work:

> **We trust document authors to surface causal relationships they consider important. If a cause-effect relationship was not stated explicitly in source, we do not presume to assert it ourselves. Inferring causation across atomic records is an analytical layer that does not generalise reliably across a whole document corpus and is therefore not part of the pipeline.**

This is not a default position — it's a deliberate methodological commitment with consequences:

### Consequences for tagging

- **Narratives are the primary tagging field.** They are closest to author-stated content. Lessons may be retained but flagged as "model-interpretive" and not used for evidentiary causal claims.
- **The per-record schema becomes a strict filter for failure-mode candidacy.** A record qualifies as a failure-mode candidate only when:
  - `something_happened_on_project = yes`
  - `cause_stated = yes` (the document, not the model, stated the cause)
  - `outcome_stated = yes_negative` (for failure modes) or `yes_positive` (for success modes)
  Records missing any of the three are observation records or context records, not failure modes — regardless of how interesting they look.

### Consequences for taxonomy

- **Cross-record cause-effect synthesis is dropped** from the pipeline. The within-document failure-mode clustering stage previously sketched in §6.4 / option 1 becomes inappropriate under this stance — it would assert causal relationships that the document authors chose not to surface.
- **The four-bullet section 10.3 case becomes**: each bullet remains its own observation record; none qualifies as a failure mode in isolation; the document chose not to make the causal claims that would aggregate them; we do not add those claims. Records 0048, 0049, 0053, 0054 sit in the corpus as evidence without being elevated to taxonomy entries.
- **Taxonomy yield will be smaller but fully evidence-grounded.** In doc_0705, ≈5 of 62 records (~8%) have explicit author-stated cause-effect. Corpus-wide projection: 5,000–7,000 failure-mode candidates from 72k project-tagged records. Every taxonomy entry traceable to author-asserted causation.

### Consequences for the grey report

The methodology section will state explicitly:

> "The pipeline extracts cause-effect relationships that document authors chose to make explicit through grammatical signalling ('because', 'due to', 'as a result of', 'led to', 'attributable to', etc.). It does not infer causal relationships from co-occurring observations across records. This restricts the failure-mode taxonomy to author-asserted causation and produces a smaller but more evidentiary-grounded dataset. Records where causation is implied or inferable but not author-stated are retained as observation evidence but not elevated to taxonomy entries."

### What gets lost (acknowledged)

- Failure modes the document authors gestured at but did not state explicitly (e.g. the "modest pumped hydro revenues" pattern across the four section-10.3 bullets) will not appear in the taxonomy under this framework. They remain as observation records that a downstream analytical project — with its own validated methodology — could use to construct a richer failure-mode account. They are not destroyed; they're simply not promoted to taxonomy under this pipeline's authority.

This position will be reflected in:
- The refined per-record tagging schema (replacing the v1 four-axis approach)
- The Haiku prompt for the corpus-wide tagging pass (will look only for explicit author-stated cause + outcome)
- The taxonomy-derivation step (operates only on records that pass the strict filter)

---

## 8. Pragmatic execution stance (locked, 2026-04-30)

Adopted alongside the epistemic position to govern when to optimise the pipeline vs when to use its output:

**First-pass framing**: this is a v1 of the new taxonomy-free extraction pipeline. We expect to learn from executing it. Recall-validation infrastructure (Stratum A uniform random sampling, Stratum B negative sampling, adversarial anchors, source-document reading) is **valuable for v2 but not a blocker for v1**. The locked epistemic position guarantees correctness on what we extract; the recall question is "did we miss material we should have caught?", which is best answered after we've used the v1 output and seen what's missing in practice.

**Value-against-counterfactual framing**: the right comparison for the taxonomy is not a hand-curated gold standard (which we don't have) but the counterfactual scenario where the PM reads 1,440 documents personally to find patterns. Against that:

- v1 pipeline produces ~23k tagged failure-mode candidates with verbatim author-stated connectives, evidence-grounded under the locked epistemic position.
- Even at 80% recall / 90% precision, this enables analyses that weren't tractable before (cross-corpus pattern matching, candidate-failure-mode shortlisting, deal-clause sourcing for ARENA portfolio decisions).
- The grey-report defence becomes "this enables analyses that weren't tractable before" rather than "this approaches a gold standard".

**Practical consequences**:

1. The recall-validation work (Stratum A/B sampling, adversarial anchors, source-document reading) is descoped from v1 critical path. Queued for v2 once we know what failure modes we're looking for.
2. The next concrete step is **taxonomy derivation** on the ~23k failure-mode candidate records, not further pipeline tuning.
3. Documentation discipline: capture what works and what doesn't in v1 execution. The v2 pipeline design will be informed by actual taxonomy-derivation experience, not predicted issues.

This stance is methodologically aligned with grey-report norms: state the scope honestly, defend on counterfactual value rather than absolute accuracy, and treat the artefact as v1 with documented limitations rather than as a final product.

---

## 9. Two-step taxonomy methodology (locked, 2026-04-30)

After running the failure-mode clustering pipeline through validation (Stages A–F) on a stratified sample, the methodology that emerged has a clean two-step structure with separated purposes. This is the position adopted for v1 and forward.

**Step 1 — Clustering as category discovery.** Embedding-based seeded single-walk clustering produces candidate categories. The purpose is to surface *what kinds of failure-mode patterns exist* in the corpus, not to assign records correctly. This step:
- Is data-driven, cheap (free if embeddings already exist), and unbiased by prior taxonomy commitments
- Tolerates imperfection (some records cluster by vocabulary overlap rather than mechanism)
- Is prone to two failure modes: (a) misfits in clusters (records grouped by surface vocabulary, not actual mechanism), (b) missed members (records that should cluster but missed the seed during walk)
- Produces an output that is good enough to *name the categories* via LLM labelling but not good enough to *defend each membership decision*

**Step 2 — LLM validation as membership precision.** For each record, send to an LLM with the question "does this record's underlying failure mode match this category's pattern?" alongside top-N candidate categories. The LLM decides: stay, move, or eject. This step:
- Uses the right tool for boundary judgment (semantic LLM judgment, not vector cosine)
- Costs more than clustering but only on the validation pass, not on seed selection
- Cleans both failure modes from Step 1: ejects misfits (cluster-coherence problem) and recovers missed members (singleton-recovery problem)
- Each membership decision becomes individually defensible because it rests on an LLM judgment about pattern fit

**Why the two-step structure is methodologically defensible**:

1. **Separation of concerns**: clustering is for *category discovery* (what taxonomic entries should exist), validation is for *membership accuracy* (which records belong in each entry). These are different questions with different ideal tools.
2. **Step 1 imperfection is acceptable** because Step 2 explicitly cleans it. The clustering doesn't need to be highly accurate; it needs to surface the right *labels*. Cluster labels survive re-validation; cluster *members* are subject to revision.
3. **Iteration is built in**: each validation pass can re-cluster the ejected pool, re-label, re-validate. Semantic matching is inherently lossy at any single resolution; iteration converges.
4. **Auditability**: Step 1's clusters are reproducible from embeddings; Step 2's verdicts are individually inspectable. The taxonomy's defensibility is a per-decision property, not a global one.

**Empirical evidence from the validation sample**:

- Step 1 alone (after V2 label broadening): cluster coherence ~50–77% on n≥10 clusters (audit-measured)
- Step 1 + Step 2: misfits ejected (28% of records), singletons recovered (64% of single-record/2-record clusters absorbed correctly), final clusters audited as substantively coherent
- All 7 manually-identified misfits from earlier audit handled correctly by Step 2 (4 ejected, 3 reassigned)
- COVID cluster: n=8 → n=17 with 17/17 perfect fit (clean singleton recovery)
- Cost: ~$0.65 for validation on 623 records (~$10 projected for full ~10k corpus)

**Implication for the grey-report writeup**: the methodology is presented as a two-step process with clear epistemic responsibilities for each. Step 1 produces a *messy first iteration* that is defensible as a category-discovery scaffold; Step 2 lifts each membership decision to a defensible LLM judgment. Iteration is acknowledged as built-in because semantic matching is imperfect at any single pass.

**Cluster-label evolution alongside Step 2**: the v2-broadening prompt (Section §6) handles label-level imperfection. Step 2 handles membership-level imperfection. Together they address both axes of the clustering's failure modes.

### 9.1 Iteration is bounded by a noise floor

The two-step methodology is iterative in principle: each pass can re-cluster the ejected pool, re-label, re-validate. But the iteration converges to a noise floor where residuals have no internal coherence and no further taxonomy emerges.

**Empirical demonstration on the validation sample**: after iteration 1 + Stage F validation, 180 records remained as singletons or 2-record groups (records that didn't fit any substantive cluster's pattern). Running seeded single-walk clustering on these residuals at multiple thresholds:

| Threshold | Total clusters | Singletons | ≥3-record clusters | ≥5-record clusters | Top cluster size |
|---|---|---|---|---|---|
| 0.50 | 76 | 116 (64%) | 11 | 6 | 12 |
| 0.55 | 109 | 73 (41%) | 13 | 3 | 15 |
| 0.60 | 140 | 111 (62%) | 3 | 1 | 11 |
| 0.65 | 164 | 150 (83%) | 1 | 0 | 4 |
| 0.70 | 175 | 170 (94%) | 0 | 0 | 2 |

The clusters that form at loose thresholds (0.50–0.55) are random vocabulary associations rather than coherent failure modes. Reading the largest residual cluster (n=12 at 0.50): the seed was about Chromasun hydraulic imbalance, but members included customer confusion about rooftop solar requirements, Solar Hub design abandonment, and Bulgana wind farm limitations — no shared mechanism. At 0.65 the top cluster (n=4) mixed stakeholder coordination, ToU savings, data logger installation, and arbitrage charging — same incoherence at smaller scale. At 0.70, 94% are singletons.

**Methodological implication**: the iterative two-step methodology *converges to a noise floor* where residuals genuinely have no internal coherence. The recurring taxonomic patterns surfaced in iteration 1; the residuals represent project-specific findings that don't repeat enough times to form patterns at the sample's scale.

This means:
1. **Iteration count should be bounded empirically**, not assumed-infinite. Stop when iteration N+1 produces no new substantive clusters (defined as ≥5 records with audited coherence).
2. **The noise floor is sample-size-dependent**. At 623 candidates → 180 residuals → no new clusters. At ~10k candidates corpus-wide, some long-tail patterns might cluster meaningfully in iteration 2 because each potential cluster has more candidate members. But the same noise-floor effect applies eventually — probably after 2-3 iterations.
3. **Residual singletons are not pipeline failures.** They're records describing project-specific failures that happened to be unique in the sample. Their existence as singletons is a correct outcome under the "no forced broadening" principle; not an artefact to fix.

**For the grey-report defence**: the methodology produces a finite, bounded taxonomy with explicit residuals. Failure modes that didn't make the taxonomy aren't lost — they're retained as singleton evidence records. The iteration count is empirically determined by when residuals stop clustering meaningfully, not arbitrarily set in advance. This is more honest than a methodology that claims to capture every pattern.

#### Action item

Update the per-record tagging schema not just to capture the cleaner primitives (something_happened / cause_stated / outcome_stated) but to **specify which field (narrative, lesson, or both) is being tagged**. The dedup-side work (event identification) tags narratives; the failure-mode-taxonomy side should tag lessons or the pair. This is a substantial refinement to the architecture from §6.4.

### 6.5 What this means for the per-record schema

The current four-axis schema (gen, val, spec, PM-actionability) was designed for per-record content judgments, but conflates two questions:

- **Did the record itself capture a complete failure-mode entry?** (val + spec + label, all on the page)
- **Does the record contribute to a failure-mode entry that lives across multiple records?** (any subset of val + spec + label may be missing)

The simpler primitives Jeff has now articulated — **did something happen on this specific project**, **was the cause stated**, **was the outcome stated** — are cleaner because they're per-record content checks that can be aggregated at the cluster level. They don't require the per-record record to itself carry the full failure-mode story.

This is the schema refinement now scheduled in the todo list (see ARENA tagging section).

---

## 10. Methodology evolution from v1.3 (ARENA) to current pipeline

The current architecture is partly capability-driven, partly methodological-learning-driven. v1.3 of the ARENA failure-mode work used the tools that were available; the improvements come from (a) embeddings that didn't exist in usable form for v1.3 (Qwen3-Embedding-4B is recent), and (b) developing the *discipline of decomposing problems into narrowly-scoped Haiku-shaped sub-problems* — Haiku was available during v1.3, but Jeff's understanding of how to scope tasks for it had not yet matured.

Honest framing: the v1.3 architecture wasn't constrained by tool availability — it was constrained by the methodology not yet knowing how to use cheap models reliably. v1.3 leaned heavily on Sonnet because Sonnet handled bundled-judgement tasks robustly; Haiku could only handle narrower tasks well, and the discipline of decomposing the work into Haiku-handleable pieces hadn't been articulated. The improvements aren't because v1.3's methodology was wrong — they're because v3's methodology is more disciplined about problem decomposition AND has access to dense semantic embeddings that v1.3 didn't.

### v1.3 baseline (per CLAUDE.md and earlier work)

- **Source corpus**: 1,440 ARENA Knowledge Bank documents → ~16,085 atomic insight records (E2 extraction)
- **Dedup**: 16,085 records → 7,779 events (52% reduction). Methodology: Sonnet + **TF-IDF advisory hints** + within-project chronological seeded walk
- **Failure archetypes**: 241 canonical archetypes across 3 parent categories (Technology performance, Commercial viability, Market/policy conditions). Built via Sonnet-based archetype discovery + classify + refine prompts
- **Realised delivery events classified**: 3,136
- **Total cost (extraction + QA + reconciliation + archetype work)**: ~$80

### Current pipeline (v3, post-validation)

- **Source corpus**: 1,440 ARENA documents → 90,192 atomic insight records (E3-grave extraction; finer atomicity than E2)
- **Project-tagged subset**: 72,380 records
- **Within-project dedup**: same seeded-walk pattern as v1.3 but using Qwen3 embeddings (dense semantic) for similarity hints. 502 projects covered, 62,301 events
- **Causal recovery (4-stage)**: 22,517 YES records (~$21)
- **Failure-mode pipeline (6-stage A–F)**: ~10,000 candidate records → labelled v3 taxonomy with ~6 emergent parent categories and ~50–100 substantive clusters (~$30 projected)
- **Total causal-pipeline-plus-failure-mode cost**: ~$50 (excluding extraction/dedup which run separately)

### What changed and why it matters

**Similarity signal** (TF-IDF → Qwen3 embeddings):
- TF-IDF matches by surface-form vocabulary overlap. It would link "delays" with "delayed" via stemming but NOT "compounded by" with "exacerbated by" or "stemmed from".
- Dense embeddings capture paraphrastic similarity — exactly what the discovery prototype showed (records using "compounded by", "meant that", "accelerated by" surfaced via embedding similarity to anchor sentences using "led to", "due to").
- Practical implication: v1.3's dedup needed the chronological-walk-with-Haiku-confirmation backstop because TF-IDF advisory hints alone were too lexical. Current dedup's cosine signal is more reliable, and the failure-mode clustering wouldn't have been meaningful with TF-IDF at all.

**Per-record decomposition** (Sonnet-bundled → Haiku-decomposed):
- Haiku was available during v1.3. What wasn't available was the *methodology* of decomposing the work into narrow tasks that Haiku could handle reliably. The discipline of "ask Haiku one focused question at a time" had to be developed through experience.
- v1.3 leaned on Sonnet for bundled judgement (event-type + significance + relevance in one prompt) because Sonnet handles bundled tasks robustly. Decomposing into separately-handled sub-tasks looked unnecessary at the time and costlier per-decision.
- v3 decomposes into per-record steps: (a) is there author-stated cause-effect?, (b) what valence?, (c) is mechanism named?, (d) does this fit cluster X's pattern? Each is narrow enough for Haiku to handle reliably with the right prompt anchoring.
- The cost structure helps but isn't the binding constraint. Haiku pricing makes per-record validation ~5× cheaper than Sonnet, but the methodological insight — that narrow Haiku-handleable questions produce more inspectable outputs than bundled Sonnet judgements — would have been worth applying even at Sonnet pricing once articulated.
- Other narrow-task additions: per-record valence + mechanism tagging, per-record causal-vs-not classification, per-record cluster-fit validation. Each of these surfaced because the methodology evolved to ask narrower questions and accept more decision points, not because the tools became newly capable.

**Architectural separation** (combined → modular):
- v1.3 pipeline bundled clustering, labelling, and assignment into a tightly-coupled flow because each Sonnet call had to do as much as possible. The output is good but the decisions are not individually inspectable.
- Current pipeline separates: clustering (free, embedding-based), labelling (cheap Haiku per-cluster), validation (cheap Haiku per-record), parent synthesis (one Sonnet call). Each step has a clear epistemic responsibility and produces inspectable artefacts.
- Practical implication: defensibility is now per-decision rather than per-pipeline. The grey report can defend each membership claim by pointing to a Haiku verdict; v1.3 had to defend the methodology in aggregate.

### What hasn't changed

- Atomic extraction with separate fields for narrative, lesson, evidence — same approach as v1.3
- Seeded single-walk no-merge clustering pattern — same architectural commitment as dedup v2
- Trust in author-stated causation as the locked epistemic position — would have been the right move at v1.3 had it been articulated
- Failure-mode taxonomy as a portfolio-decision artefact — same downstream user

### Filtering — both v1.3 and current pipeline filter, differently

This is worth being precise about. Both pipelines filter the corpus before clustering; the difference is *how systematically*.

**v1.3 filter**: pure Sonnet judgement on a single binary axis — `realised_delivery_event: yes/no`. Records were classified through one bundled prompt covering event-type and significance simultaneously. ~3,136 of 7,779 events passed (~40%). Implicitly this was the v1.3 equivalent of "did something happen?" combined with relevance to delivery (excluding pure design/concept findings).

**Current pipeline filter**: a stack of explicitly-separated stages, each with its own defensible criterion:
1. Keyword regex (Stage 1) — author used a causal connective
2. Embedding similarity to causal anchors (Stage 2) — semantic shape of cause-effect
3. Haiku verdict YES on author-stated cause-effect (Stage 4) — actual causal claim, not paraphrastic similarity
4. Valence = negative + mechanism_named = yes (Stages A+B) — failure-mode-shaped subset
5. Cluster-fit validation (Stage F) — record's mechanism matches cluster's pattern

22,517 of 90,192 records pass through Stage 4 (~25%); ~10,000 expected through to failure-mode candidacy after Stages A+B.

The improvement isn't *more coverage* — both pipelines filter to roughly comparable retention rates. The improvement is in the *systematic, multi-stage filtering with separately-defensible criteria* vs v1.3's single bundled-Sonnet judgement. Each filter stage in the current pipeline produces inspectable per-record artefacts (keyword match, anchor similarity, Haiku verdict, valence tag, mechanism tag). v1.3's `realised_delivery_event=yes` was a single Sonnet decision per event.

### Other caveats

- v1.3 had **QA verification** (92.2% grounding, 89.6% classification) that the current pipeline hasn't done an equivalent for yet. Validation pass at Stage F provides per-record cluster-fit verification but not record-vs-source-document grounding.
- v1.3's 241 archetypes were derived from the realised_delivery_event subset and span the full failure space implicitly. Current pipeline's failure-mode candidates are explicitly filtered to negative-valence + mechanism-named, so the taxonomy will be more narrowly scoped to failure-shape content. Not strictly comparable to v1.3's archetype count.
- We can't directly compare taxonomy quality without re-running classification on the same record set.

### Implication for the grey report

The methodology evolution should be presented honestly:
- v1.3 demonstrated the methodology was viable using the available tools and the methodological understanding at the time
- v3 advances on two fronts simultaneously: (a) Qwen3 dense embeddings replace TF-IDF (genuine capability shift — these embeddings didn't exist in usable form for v1.3), (b) the discipline of decomposing the problem into narrow Haiku-handleable sub-tasks (methodological maturation — Haiku was available; the understanding of how to use it wasn't)
- The two-step structure (§9), the locked epistemic position (§7), and the noise-floor convergence (§9.1) are methodological commitments that emerged from v1.3 pressure-testing experience. v1.3's hand-audit of one cluster (where 8 of 15 members fit) gave the empirical signal that bundled-LLM clustering produces overconfident memberships — that signal drove the v3 Stage F design.
- The current architecture isn't a contradiction of v1.3 — it's v1.3's principles applied with embeddings that v1.3 didn't have and with methodological discipline that v1.3's experience forced us to develop. The methodology paper arc: hand-built taxonomy in v1.3 → audited and identified coherence limits → redesigned pipeline to make every membership decision individually verifiable, leveraging both new embeddings and learned discipline about narrow-task LLM use.

---

## 11. Pipeline as measurement instrument — traceable uncertainty (locked, 2026-05-01)

The synthesis pipeline is a **measurement instrument**, not a taxonomy oracle. Every filter applied during retrieval has an associated label-reliability, and the joint reliability of any query is decomposable into the per-filter reliabilities along the retrieval chain. The methodology paper claims *quantified, attributable, decomposable uncertainty* — not certainty.

### The efficiency-chain frame

Borrowed from engineering: a multi-stage system's overall efficiency is the product of stage efficiencies, `η_total = ∏ η_i`. The same algebra applies to filter reliabilities. For a query that combines `N` filters with per-filter reliability `r_i`, the joint probability that *every* label on a returned record is simultaneously correct is:

```
r_joint ≈ r_1 × r_2 × ... × r_N      (under independence)
```

Stacking filters increases per-record specificity but decreases joint label reliability. The pipeline doesn't claim zero error per record — it claims that a query's precision is the product of its per-stage label reliabilities, and that the user can see which stage dominates the chain.

### Per-filter reliability provenance (current best estimates)

| Stage | Label | Reliability source | Estimate |
|---|---|---|---|
| Stage 1 (causal recovery) | YES/NO author-stated causation | Hand-tagged calibration sample | ≈ 0.85 (precision) |
| Stage A — valence | negative/positive/neutral | Haiku 92% strict on calibration sample | ≈ 0.92 |
| Stage A — mechanism_named | yes/no | Haiku 92% strict on calibration sample | ≈ 0.92 |
| Stage F — cluster membership | which of N clusters | Opus full-corpus audit | per-cluster `fit_pct`, median 0.88, p25 0.77 |
| Pass 2 — parent assignment | which of 46 parents | Sonnet self-rated confidence | high=156 / medium=235 / low=36 (no IRR ground truth) |
| Pass 3 — realisation | realised/mixed/anticipated/generic | Haiku batch (74_) | not yet IRR-validated; estimate ≈ 0.85 pending hand-tag |
| Tech category | from project metadata CSV | Deterministic lookup | ≈ 1.00 |
| Theme assignment | which of 9 themes | Inherited from parent assignment | ≤ parent reliability |

### Three real caveats

1. **Independence is shaky.** Errors across filters can correlate — a hedged-language record will be judged borderline-causal *and* anticipated-modality with above-chance joint probability. Multiplying without correction produces a pessimistic lower bound on joint reliability. The honest correction is to estimate conditional reliabilities or measure correlation empirically; for a first-order paper claim, the unconditioned product is a defensible conservative envelope.

2. **"Reliability" means different things across filters.** Some are precision (binary YES/NO with hand ground truth), some are accuracy (multi-class against calibration), some are LLM-vs-LLM agreement (Stage F audit by Opus is *not* human ground truth — it inherits whatever bias both LLMs share). The methodology paper must distinguish *human-grounded* from *LLM-grounded* reliabilities and not present them as the same epistemic object.

3. **Reliability is a distribution, not a point.** Cluster-membership reliability is per-cluster: data-availability cluster scored 0.94 fit_pct, cluster #1 storage cost scored 0.67. The chain product must be computed per query against the specific cluster being filtered to, not as a global constant. The same applies to themes whose contained parents have heterogeneous reliabilities.

### Implementation: live joint-reliability readout

The right place to surface this is in the navigator: as the user stacks filters, a status line shows the *cumulative joint reliability* of the current query. Concretely, for *"Battery storage + Realised + Cluster #169"*:

```
Joint label reliability ≈ 1.00 × 0.85 × 0.79 ≈ 0.67
```

Reading: each record returned has roughly a 2-in-3 chance that *all* its filter labels are simultaneously correct. The user sees the trade-off: stacking filters tightens topical relevance but loosens joint label confidence.

This is a feature no document repository or generic retrieval tool offers, and it directly enables the methodology paper's epistemological claim — *we surface uncertainty rather than hide it*.

### What's needed to populate it properly

- **Hand-tagged sample** (≈100 records per filter) for any LLM-judged stage that hasn't been calibrated against human ground truth: realisation classifier (Pass 3), Pass 2 parent assignment, and Stage F cluster membership. Three filters × ~100 records ≈ 300 hand-tags. No API spend; researcher time.
- **Per-cluster fit_pct already exists** from the Opus audit (`cluster_audit_summary.json`); just needs to be wired into the navigator's reliability calculation.
- **Correlation analysis** between filter errors — post-hoc on whatever hand-tagged data is available — to size the independence-assumption error and decide whether to retain the simple product or move to a conditional formula.

### Implication for the methodology paper

This section is the strongest single argument for the paper's methodological contribution. The framing isn't "we built a taxonomy"; it's *"we built a measurement instrument whose outputs come with traceable, decomposable, computable uncertainty"*. That's a meaningfully harder claim than most synthesis taxonomies offer, and it's the one that survives reviewer scrutiny — because every uncertainty source is named, every reliability is independently measurable, and the user can interrogate the trust budget at query time.

The metaphor *"efficiency chain"* is the cleanest framing for this in the paper. It maps onto an established engineering convention, the algebra is unambiguous, and the analogy makes the *compositional* nature of pipeline trust explicit.

---

## 7. State of the artefacts

Files in `corpora/arena/tests/dedup_haiku/`:

- `calibration_sample.md` / `.json` — 60-event template + manifest
- `calibration_tags.json` — merged tags from Jeff + Opus agent (60 events, with `source` field)
- `agent_tags.json` — Opus agent's raw tags (56 events)
- `haiku_tags.json` — Haiku v1 agent's tags (56 events, refined prompt with anchors)
- `haiku_happened_classification.json` — Haiku binary classifier (60 events)
- `haiku_prompt_v2.md` — v2 prompt with all the refinements documented in this file (not yet run; superseded by the schema refinement queued in todo)

The next iteration will be triggered by the schema refinement in the todo list, not by re-running v2 of the four-axis schema.
