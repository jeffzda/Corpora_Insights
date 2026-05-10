# Extraction Defensibility: Why the v2 Record Substrate Is Methodologically Sound Despite Carrying LLM Voice

**Status:** resolved position as of 2026-05-04, derived from empirical audits (`corpora/arena/clustering_v2/closure/code/16-18`).
**Audience:** methodology-paper drafting; future contributors evaluating the substrate.
**TL;DR:** the records produced by `pipeline/extract.py` carry the extraction model's stock summary voice, but voice is rephrasing rather than concept injection, semantics are preserved with high fidelity, and the architectural work (selection, segmentation, self-containment) cannot be replicated by paragraph-chunked extraction. The substrate is defensible.

---

## 1. The question

The v2 substrate (90,192 atomic records over 1,440 documents) is the analytical surface on top of which clustering, parent-archetype derivation, theme grouping, and synthesis reports operate. Each record was produced by a one-shot LLM extraction pass over a whole source document — `narrative`, `evidence`, `lesson`, and supporting fields are the model's structured rendering of mechanism content from the source.

A natural objection: if every record is a model-rendered paraphrase, isn't the whole substrate sitting on inference? Could the clusters and parent archetypes be detecting the model's vocabulary patterns rather than real corpus structure? Could "the field uses framework X" claims based on record term-frequencies be measuring the extraction model's voice rather than the field's language?

The short answer to each: voice exists and is real, but the substrate is defensible because (a) voice is rephrasing not concept injection, and (b) atomicity at corpus scale requires multi-layer inference that no paragraph-chunked alternative can replicate.

The remainder of this document substantiates each leg.

---

## 2. Voice exists. Here's what it is.

The corpus-wide voice audit (`closure/code/17_extraction_voice_audit.py`) compared n-gram densities in records vs source markdown. Records (13.8M chars) and markdown (94.7M chars) were tokenised; for n-grams above frequency thresholds (200 for unigrams, 50 for bigrams, 20 for trigrams), the per-million-token incidence was compared.

Top "amplified" bigrams (records vs markdown):

| Bigram | rec/Mtok | md/Mtok | Ratio |
|---|---:|---:|---:|
| "is identified" | 274.6 | 6.71 | 40.9× |
| "trial found" | 33.7 | 1.21 | 27.8× |
| "project identified" | 123.2 | 4.45 | 27.7× |
| "was identified" | 566.8 | 24.6 | 23.1× |
| "identified as" | 1021.5 | 44.6 | 22.9× |
| "this caused" | 32.7 | 2.99 | 10.9× |
| "barrier to" | 236.9 | 28.5 | 8.3× |
| "described as" | 116.2 | 10.5 | 11.1× |

Top amplified unigrams: "causing", "insufficient", "requiring", "indicating", "delays", "caused", "creating".

These are the model's voice — passive constructions, causal connectives, narrative-summary verbs. They are *not* domain content. The model packages findings in a consistent stylistic register that the source documents use less often. This is what voice means in this substrate.

**What voice is not:** zero unigrams and zero bigrams above the frequency threshold are completely absent from markdown. Six trigrams are absent — *"this is identified"*, *"workshop participants identified"*, *"identified as specific"*, *"the pilot found"*, *"scoping survey identified"*, *"as factor that"* — and every one is an extraction-summary pattern, not domain content. The model paraphrases consistently; it does not invent content concepts at scale.

The narrative-vs-evidence audit (`closure/code/18_narrative_vs_evidence_audit.py`) corroborates this at the per-record level. Across a 50-record stratified sample, ~96% of novel n-grams in `narrative` (those not present in the record's `evidence` excerpt) are paraphrases of source content (whether the local paragraph or elsewhere in the same document), not invented content.

So: voice is real and quantifiable, but it operates at the rendering layer, not the conceptual layer. The same situations that authors describe are described again in records, in a different register.

---

## 3. Why atomicity requires inference at corpus scale

The temptation, given the voice findings, is to ask whether a less interpretive extraction approach — paragraph-chunked indexing of the raw markdown — could do the same job without imposing model voice. It cannot, and the reasons are structural rather than implementation-detail. The substrate's analytical work depends on *atomicity* (each record is one mechanism claim, self-contained, comparable across documents), and atomicity at corpus scale requires inference at four distinct layers.

### 3.1 Selection — distinguishing claim content from non-claim scaffolding

Source documents contain large fractions of content that are not atomic mechanism claims: front-matter (copyright statements, conflict-of-interest disclosures, licensing terms), methodology bridging text (procedural narrative about how data was gathered), tutorial exposition (textbook-style explanations of background concepts), references, citations.

Empirically, the extraction model skips ~18-20% of substantive paragraphs (>100 chars) on the median document, and inspection shows the skipped paragraphs are exactly the right kind. A representative example from `doc_0031` (ARENA Vehicle-to-Grid Insights Final Report, 123 substantive paragraphs, 60 records, 22 paragraphs skipped):

> *"To the best of ARENA and Energeia's knowledge, no conflict of interest arose during the course of preparing this report..."*
> *"ARENA retains and owns the copyright for this commissioned report. With the exception of the Commonwealth Coat of Arms..."*
> *"This section reports on the type and quality of data generated throughout the trial. ActewAGL supplied the data used and answered Energeia's questions as they arose..."*

These were correctly skipped. None carry mechanism-bearing content; all of them would clutter a paragraph-chunked retrieval index without contributing to atomic-claim analysis.

Doing this distinction at corpus scale (1,440 documents, ~187,000 substantive paragraphs) is itself an LLM-scale task. There is no shallow heuristic — based on length, position, formatting, or surface keywords — that reliably distinguishes "this paragraph is a mechanism claim" from "this paragraph is exposition or boilerplate" across 30 years and 14 ARENA categories of project documentation. The selection step requires paragraph-level inference, and at 187k paragraphs that inference must be done by an LLM.

### 3.2 Segmentation — atomic-claim boundaries don't follow paragraph boundaries

The unit of analysis is the atomic mechanism claim. Atomic-claim boundaries are not paragraph boundaries. Tables, bullet lists, and multi-claim prose paragraphs all violate the assumption that one paragraph = one claim.

A representative example from `doc_0121` (ARENA Information Session presentation, 31 substantive paragraphs, 68 records, ratio 2.19×):

> **Paragraph #19** — a 1,652-character table of six eligibility criteria, formatted in HTML as a `<table>` with rows for "A — eligible applicant", "B — eligible Activity", "C — take place in Australia", "D — knowledge sharing", "E — intellectual property", "F — compliance".

The model produced **eight records** from this single paragraph:
- One per table row (six records, each a self-contained eligibility criterion).
- A meta record — *"Six eligibility criteria. All must be met to proceed to merit assessment"* — that synthesises the structure of the table itself, not extractable from any single row.
- A record about CV submission timing that is content-adjacent (likely from a nearby paragraph my crude word-overlap matching merged with this one).

The same pattern appears with bullet lists. Paragraph #2 of the same document, a 786-char bullet list defining DER and projecting 2030 deployment, becomes six records — one per bullet (consumer-owned generation/storage; ARENA's <5MW focus; rooftop-PV dominance; BNEF projections; EV uncertainty; hosting-capacity definition).

A paragraph-chunked extractor faces a category error here: chunking on paragraph boundaries either yields one record per multi-claim paragraph (massive information loss when a 6-criterion table compresses to one record) or requires its own intra-paragraph segmentation logic — which *is* document-aware judgement, just relocated. There is no lossless paragraph-shaped representation of atomic mechanism content.

The corpus statistics support this as a common rather than rare pattern: 174 documents have at least 30 substantive paragraphs *and* produce more records than paragraphs, with ratios up to 2.19×.

### 3.3 Self-containment — atomic records must read alone

An atomic record functions on a cross-document analytical surface — it must be interpretable in isolation, possibly cited in a synthesis report alongside records from completely different projects. Source paragraphs are typically not self-contained. They use anaphora ("the project," "this issue"), implicit context ("the trial enabled..." — which trial?), and assumed referents.

Concretely, a record's `evidence` excerpt might be a short fragment such as:

> *"Restrictions on channel access or exclusion zones around the inlet/outlet structure"*

The corresponding `narrative` is:

> *"Community concern was raised about restrictions on channel access or exclusion zones around the inlet/outlet structure of the seawater PHES facility."*

The narrative adds: who was concerned (the community), what kind of facility (seawater PHES), and frames the concern as a finding rather than a fragment. None of this exists in the evidence excerpt as a standalone unit; the model has read the document, identified the surrounding context, and rendered a self-contained version.

This is where the voice is imposed. The price of self-containment is that every record passes through a rendering step that gives it the model's narrative register. A paragraph-chunked retrieval system avoids this cost by not producing self-contained units at all — but then it cannot support the cross-document synthesis (e.g. the c042 cluster report spanning 8 ARENA categories and 14 years; the p18 parent report spanning 24 mechanism clusters and 153 projects) that is the substrate's headline contribution.

### 3.4 Local synthesis where needed

A minority of records (~30% in a 50-record stratified sample) draw substantive content from elsewhere in the source document — adding project names from the title page, prior decisions from earlier chapters, related findings from elsewhere in the report. This is the smallest of the four layers, and it does not need to carry the architectural argument. Selection and segmentation are sufficient on their own to establish that the substrate's work cannot be replicated by paragraph-chunking.

The earlier framing in this project — "one-shot extraction binds whole-document context into every atomic record" — overstated this layer. Empirically, ~30% of records show meaningful cross-paragraph context drawing; the dominant pattern (68%) is local-paragraph paraphrase plus the segmentation and self-containment work above. The corrected position keeps the strong claim (selection-and-segmentation are categorical advantages) and treats the cross-paragraph layer as marginal reinforcement, not load-bearing.

---

## 4. Cluster validity is not contingent on voice fidelity

The natural worry is that if records carry model voice, the clusters that group records by similarity might be detecting voice patterns rather than situational similarity. This worry is partially right (cluster *names* and parent *labels* carry the model's vocabulary register) but mostly wrong (cluster *identity* tracks the underlying situations).

Two pieces of evidence:

**Cross-axial cluster composition.** Cluster c042 ("Electrode Material Degradation From Chemical Incompatibility") contains 150 records from 51 projects across 8 ARENA categories spanning 14 years (2010–2024). The cross-cut spans authors who wrote in completely different operational vocabularies — geothermal casing in 2010 Cooper Basin reports, Spiro-OMeTAD oxidation in 2018 ACAP perovskite annual reports, polymer binder failure in 50 wt% NaOH in 2025 Fortescue iron-electrochemistry reports. If the cluster were detecting model voice, it would group records that the model phrased similarly regardless of underlying content; instead it groups records describing the same underlying causal mechanism (electrode-environment chemical incompatibility) across radically different domain vocabularies. The model's voice may be the indexing language, but the *referent* — the actual project situation — is what cross-cuts.

**Manual cluster-name verification.** When the 24 clusters under parent p18 ("Coupled-Objective Trade-Off") were reviewed cluster-by-cluster against the parent's mechanism criterion, 20 of 24 cleanly fit (capacity-headroom trade-offs, FCAS reservation versus arbitrage, thermodynamic-versus-kinetic process tuning, etc.). Where the substrate places situations is consistent with what the situations actually are.

Both checks are the kind of evidence that a methodology paper can present. Neither requires voice fidelity to record-level vocabulary; both rely on the substrate's situational fidelity, which is what the clustering is built on.

---

---

## 5. The position in one paragraph (the version for the paper)

Atomicity at corpus scale requires multi-layer interpretive synthesis. The model selects atomic-claim content from non-claim scaffolding (skipping front-matter, methodology, exposition); it segments atomic claims at boundaries that do not follow paragraph boundaries (one record per table row, one per bullet, often multiple per multi-claim prose paragraph); and it renders each unit as a self-contained statement that can stand alone in cross-document analytical use. The model's stock summary voice is the cost of the rendering step. Empirical audit shows that voice is rephrasing rather than concept injection — n-grams in records that are absent from source markdown are extraction-narrative patterns, not invented content. Cluster identity tracks situational similarity in source documents rather than model vocabulary, as shown by cross-axial cluster compositions spanning radically different domain vocabularies and by manual cluster-name verification.

---

## 6. References to the empirical record

| Artefact | What it shows |
|---|---|
| `corpora/arena/clustering_v2/closure/code/16_framework_bridge_typology.py` + `framework_bridge_typology.json` | 5-way typology of 71 parents by framework-vocabulary density in records vs markdown |
| `corpora/arena/clustering_v2/closure/code/17_extraction_voice_audit.py` + `extraction_voice_audit.json` | Corpus-wide n-gram comparison; voice is summary boilerplate, not concept injection |
| `corpora/arena/clustering_v2/closure/code/18_narrative_vs_evidence_audit.py` + `narrative_vs_evidence_audit.json` | 50-record stratified audit; ~96% of novel narrative content is paraphrase of source, not invention |
| `corpora/arena/clustering_v2/closure/output/cluster_reports/c042_report.md` | Cross-axial synthesis spanning 8 ARENA categories, 51 projects, 14 years |
| `corpora/arena/clustering_v2/closure/output/parent_reports/p18_report.md` | Parent-level synthesis on 24 clusters, 393 records, 153 projects |
| `doc_0121` (ARENA Information Session) | Worked example of segmentation: 31 paragraphs → 68 records via table-row and bullet-level decomposition |
| `doc_0031` (ARENA V2G Insights Final Report) | Worked example of selection: 18% of paragraphs skipped, all front-matter/methodology/exposition |
