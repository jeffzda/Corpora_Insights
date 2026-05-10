# A pipeline for layered structured-knowledge extraction from government document corpora

**Jeff Cumpston**, Broad Learnings (with adjunct affiliation pending, ANU Institute for Climate, Energy and Disaster Solutions).

Working draft, 2026-05-10.

---

## Table of contents

1. Introduction — what the pipeline does and what kind of artefact it produces
2. Positioning against retrieval-augmented generation
3. The four-layer architecture
4. The ARENA reference corpus and the v1 evolution
5. Stage I — ingestion
6. Stage II — atomic-record extraction (the substrate)
7. Stage III — per-document event grouping
8. Stage IV — six-axis record-type tagging
9. Stage V — cluster filter
10. Stage VI — clustering (seed → sweep → singleton sweep → residual closure)
11. Stage VII — parent derivation (deliberation-rich ensemble)
12. Stage VIII — cluster-to-parent assignment and boundary mapping
13. Stage IX — theme audit
14. Stage X — glossary sub-pipeline
15. Cross-cutting design choices
16. Validation
17. Generalisation: ANAO N=100
18. Worked example: cluster c042
19. Limitations and disclosed gaps
20. Cost economics and reproducibility
21. Future work
22. Conclusion

---

## 1. Introduction

This paper describes a pipeline that converts a corpus of government technical documents into a queryable, layered knowledge artefact. The artefact has four explicit layers — atomic records, mechanism clusters, parent classes, and themes — plus a corpus-specific glossary that gives every layer a vocabulary footprint over time, project space, and domain. Each layer is derived from the layer below it after the lower layer's membership has stabilised, except where a stabilisation gap is explicitly disclosed (§19).

The pipeline has been built and refined on the Australian Renewable Energy Agency's Knowledge Bank (1,440 documents). It has been demonstrated to generalise to a structurally distinct corpus — Australian National Audit Office performance audit reports (1,452 documents, with N=100 stratified sample reproducing the engine end-to-end) — using only token-substitution changes in domain configuration files. The same canonical extraction prompt and same per-document grouping prompt produced 4,765 atomic records and 4,483 events on the ANAO sample with no engine modification (`pipeline/development/anao_n100_demo/notes.md`). Beyond ARENA, the pipeline produced a 50-parent ANAO mechanism-class taxonomy from a single Opus 4.7 call on 207 ANAO mechanism clusters at $0.41 (`pipeline/development/anao_n100_demo/output/anao_n100_parents.md`).

The motivating use case is portfolio-level decision support. An ARENA programme manager scanning failure-mode space across 1,440 funded projects cannot read every document; the counterfactual is selective reading and informal pattern-recognition. The artefact this pipeline produces makes that scan tractable: it preserves citation traceability from any cluster, parent, or theme back to specific records, project documents, and source pages, while enabling cross-project, cross-time, cross-technology pattern analysis that no single project's report exposes.

The methodological framing is deliberate. The pipeline is positioned as a measurement instrument rather than a taxonomy oracle. Every filter applied during retrieval has an associated label-reliability, and the joint reliability of any query is decomposable into per-filter reliabilities along the retrieval chain. The framing borrows from engineering: a multi-stage system's overall efficiency is the product of stage efficiencies, η_total = ∏ η_i. The same algebra applies here. Stacking filters tightens topical relevance but lowers joint label confidence, and the user can see which stage dominates the chain (`pipeline/development/arena_canonical/narrative/methodology_notes.md` §11). This is a meaningfully harder claim than most synthesis taxonomies offer, because every uncertainty source is named and every reliability is independently measurable.

A second framing matters: the substrate is a **research-topic generator and memo producer**, not an operational tool to push for adoption. The deliverables are publishable case studies — c042 (electrode material degradation across 56 projects), the h2biomass reference-class memo, the cross-corpus ANAO↔ARENA parent overlap audit — that exercise the substrate's design promise rather than serve a production user.

The substrate is a research artefact in another sense. Of the 1,141 mechanism clusters extracted from ARENA, 711 (62.3%) describe causal pathways that apply beyond renewable energy contexts, with the remaining clusters renewable-bound by Opus's binary classification (`pipeline/development/arena_clustering_v2/notes.md` §10.3). The top general-mechanism domains — program design (150 clusters), infrastructure project delivery (147), data systems integration (116), regulatory framework design (103) — sit in the cross-cutting territory of public-sector failure modes that any infrastructure or programme corpus would surface. The ARENA substrate is therefore best read not as a renewable-energy taxonomy with a crossover layer but as a general infrastructure-failure substrate with a renewable-bound layer. The 71 corpus-agnostic parent classes derived from this substrate (§11) are diagnostic vocabulary for programme-evaluation work generally; they are not specific to renewable energy and have already been shown to overlap partially with the ANAO performance-audit taxonomy at 9 mechanism classes shared cleanly (§17).

This is the strongest single claim the paper makes about the methodology, and it is what makes the engine-versus-configuration distinction (§15) more than housekeeping. The engine produces a substrate that transfers; the per-corpus configuration tells the engine which corpus to operate on without changing what kind of artefact it produces.

## 2. Positioning against retrieval-augmented generation

The default mental model for "search over a corpus of LLM-extracted content" is retrieval-augmented generation (RAG): a query embedding is matched against a vector index of document chunks, and the top-k chunks are returned as context for a subsequent generation. RAG is a query-time tool. It does not produce a persistent analytical substrate that can be reviewed outside the context of a query.

The pipeline described here is a **structured-extraction pipeline**, not a retrieval system. It produces:

- Atomic records (one finding per record, with narrative, evidence excerpt, lesson, page, project, document, year).
- Mechanism clusters (a record may belong to one cluster; clusters group records by causal mechanism, not vocabulary similarity).
- Parents (a cluster maps to one of 86 parent classes; parents are higher-level diagnostic categories).
- Themes (parents group into 16 themes).

Each layer survives review without a query. A reviewer can read the parent definitions cold; they can read a single cluster's mechanism signature and members cold; they can audit a record against its source document. This is categorically different from RAG, which produces a query-conditioned context window and dissolves it once the generation completes.

The pipeline's outputs can be embedded for RAG (and the ARENA corpus is in fact indexed in a RAG layer using Qwen3-Embedding-4B). But RAG cannot produce the cluster, parent, or theme layers from the records. It cannot tell a reviewer that 711 of 1,141 clusters are general mechanisms; it cannot identify the p25↔p18 boundary problem; it cannot list the 5 strong reassignment candidates in a 91-cluster validation sample. Those are all properties of a structured-extraction substrate, not properties of a retrieval index.

A worked demonstration of the difference is recorded at `pipeline/development/arena_closure/output/use_case_demos/foak_rag_vs_v2.md`. RAG over ARENA's 1,440 documents returns passage excerpts that mention "first-of-a-kind"; the pipeline returns mechanism clusters whose causal pathways describe FOAK risk, with the cross-tech transfer pattern visible in the cluster's project membership.

The two are complementary. The pipeline outputs are a high-quality input for downstream RAG (cleaner than raw chunks, with structured metadata that supports filtering); RAG over the substrate gives users a query-time interaction modality on a substrate built outside the query context. The methodology paper claim is about the substrate, not the retrieval interface.

## 3. The four-layer architecture

The substrate has four layers above the source markdown, plus a glossary surface.

**Layer 0 — markdown.** Each document is converted from PDF to structured markdown by Marker. Tables, figures, footnotes, and page boundaries are preserved.

**Layer 1 — atomic records.** Each document is processed by a single Opus 4.6 extraction call producing a list of atomic findings. Each finding is one observation, one mechanism, or one lesson, with narrative, evidence excerpt, lesson, page numbers, and project/document linkage. The ARENA grave prompt produced 90,192 atomic records from 1,440 documents (`corpora/arena/shared/`).

**Layer 2 — mechanism clusters.** Records (filtered to negative-valence mechanism-bearing records, ~25,479 on ARENA) are grouped into clusters by an iterative Sonnet 4.6 sweep that classifies records against a growing catalogue using mechanism-coherent criteria, refusing to canonise any cluster with fewer than three supporting records. The ARENA catalogue converged at 1,141 clusters. Each cluster has a canonical name and a 1–3 sentence mechanism signature.

**Layer 3 — parent classes.** Clusters map to one of 86 parent classes. The parent set is derived from the corpus by an Opus 4.7 ensemble (Phase 7 below) and validated by a separate Opus 4.7 cluster-to-parent assignment pass.

**Layer 4 — themes.** Parents group into 16 themes by a single Opus 4.7 audit-and-grouping call.

**Layer 5 — glossary.** A separate eleven-stage sub-pipeline produces a corpus-specific glossary with definitions, year-trajectory metrics, distinctiveness ratios over project categories, and project-vocabulary fingerprints. The ARENA glossary contains 760 entries; the ANAO glossary contains 590.

Each layer is intended to be synthesised after the layer below has stabilised. This is a methodological commitment, not just an implementation detail. The pipeline is faithful to it at the parent layer (parents derived after the 1,141-cluster catalogue stabilised) and the theme layer (themes derived after the parent set stabilised). It is **not** faithful at the cluster-signature layer: each cluster's signature is written at minting time from the founding 5–10 records, not re-synthesised after the membership stabilises (§19, `pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/CLUSTER_SIGNATURE_DRIFT.md`). This is a disclosed gap with a costed fix that has not been committed.

## 4. The ARENA reference corpus and the v1 evolution

The ARENA Knowledge Bank is the canonical reference corpus. It contains 1,440 documents (regular) plus 8 oversized special-handling documents covering reports, lessons-learnt, presentations, and milestone deliverables from ARENA-funded renewable-energy projects, 2010–2026. The corpus is heterogeneous: median document size is 169k characters, but length and structure vary widely.

A v1 of the ARENA failure-mode pipeline was completed before this paper's design — 16,931 atomic records, QA-verified at 92.2% grounding and 89.6% classification, with 241 canonical archetypes across 3,136 classified events at total cost ≈ $80 (CLAUDE.md project status; legacy pipeline at `corpora/arena/legacy/`). v1 used TF-IDF + Sonnet for similarity; it bundled extraction, dedup, and classification together; and it produced parents through a single-pass Sonnet derivation. v1 worked, but pressure-testing it against a corpus-wide audit revealed two structural problems: (a) ~36% of v1 clusters were single-project-bound (the embedding similarity captured project / equipment / technology vocabulary, not causal mechanism), and (b) parent derivation as a single-pass call carried unacknowledged variance.

The v3 pipeline described here is v1 redesigned to address both problems. The redesign rests on three changes from v1: dense semantic embeddings (Qwen3-Embedding-4B) replace TF-IDF; the work decomposes into narrowly-scoped LLM tasks instead of bundled judgements; and parent derivation runs as a deliberation-rich 59-rep ensemble rather than a single call. The first change is a genuine capability shift (Qwen3 didn't exist in usable form for v1); the second is methodological maturation (Haiku and Sonnet were available for v1; the discipline of decomposing the work hadn't been articulated). The third addresses the variance in single-pass derivation directly (§11).

The v3 ARENA substrate produced 90,192 atomic records, 25,479 cluster-input records (after filter), 1,141 mechanism clusters, 86 parents, and 16 themes. Total spend across all v3 work: approximately $335 — day-1 tagging $141, day-1 dedup $121, day-2 clustering ~$73, plus a parent-derivation campaign of $106 and a closure substrate-extraction pass at $4.59 (`pipeline/development/arena_clustering_v2/notes.md` §8; `pipeline/development/arena_closure/EXPERIMENTAL_METHODOLOGY.md`). These figures matter because reproducibility depends on whether other research groups can afford to run the methodology, and the answer is "yes."

## 5. Stage I — ingestion

Document ingestion is bespoke per corpus. Each domain has its own `scrape.py` inheriting from a `BaseScraper` contract; CLI dispatch is via `python -m pipeline.ingest --domain <name> --phase <phase>`. The output of ingestion is a per-corpus directory of PDFs joined to a metadata catalogue CSV (`kb_associated_project`, `kb_category`, `kb_document_type`, `kb_publish_date`, etc.). Project identifier is always taken from the catalogue, never inferred by an LLM.

PDF-to-markdown conversion uses Marker. Marker preserves tables, figures, footnotes, and page boundaries; downstream stages depend on this. The ANAO N=100 demonstration validated the choice empirically: flat markdown (where bullets are collapsed into paragraphs joined by `•`) produced 67/97 strict-parse success with median 47 records per document; marker-rendered markdown produced 100/100 strict-parse and 50 records median, with maximum records per document rising from 70 to 120 (`pipeline/development/anao_n100_demo/notes.md` Part 1). The extraction prompt explicitly treats each bullet as a distinct finding, so bullet preservation materially affects atomicity.

A standing instruction for any extraction call is to set `max_tokens` to the model ceiling (64,000 for Opus 4.7). Capping below ceiling is the single most expensive mistake in the pipeline: a truncated call wastes the whole input, produces a partial output, and forces a re-run. ANAO N=100 had a 16k-cap incident in its first extraction pass; 30 of 97 documents truncated, and a lenient parser had to recover what the cap had cut.

## 6. Stage II — atomic-record extraction (the substrate)

Atomic-record extraction is the foundational step. It uses Opus 4.6 with a single one-shot per-document call. The prompt — `pipeline/prompts/extract.md` (the "v1 grave prompt") — is taxonomy-agnostic: it asks for atomic findings, not labelled findings. It says "one mechanism per record; one record per mechanism" and "atomicity: emit same number of records as distinct findings". The narrative, lesson, and evidence-excerpt fields are separated explicitly (§19 disclosure on the lesson field).

The grave prompt is the survivor of a campaign comparing extraction-time grouping (mechanism-coherent / occurrence-coherent / merge-permissive variants) to decoupled post-extract grouping (`pipeline/development/arena_canonical/narrative/runs/`). The decisive empirical finding from the 7-way comparison is that bundling extraction with grouping conflates two concerns: extraction yield changes with grouping policy, and the two policies attract different prompt incentives. Decoupling them — v1 grave extraction produces atomic records, then post-extract per-document grouping produces events — preserves orthogonality between the event-axis and the mechanism-axis substrates, and produces the tightest event consolidation across all variants (`runs/2026-05-02-postextract-grouping-perdoc/notes.md`).

### 6.1 Voice audit: the substrate carries voice but not invented concepts

A natural concern about LLM extraction is whether the model injects content that the source document doesn't carry. A voice audit on the corpus (90,192 records vs. 94.7M characters of source markdown) found:

- 0 unigrams (≥200 occurrences) absent from markdown.
- 0 bigrams (≥50 occurrences) absent from markdown.
- 6 trigrams absent — and every one is an extraction-narrative pattern: *"this is identified," "workshop participants identified," "identified as specific," "the pilot found," "scoping survey identified," "as factor that."* No domain content.
- Top-amplified bigrams in records vs source: *"is identified" (40.9×), "trial found" (27.8×), "was identified" (23.1×), "this caused" (10.9×), "barrier to" (8.3×).* Passive constructions, narrative-summary verbs, causal connectives (`pipeline/development/arena_closure/output/parent_ensemble/INVESTIGATION_NOTES.md` Phase 2).

The reading: the model has a stock voice (passive constructions, narrative-summary register, causal-connective patterns) but does not invent content concepts at scale. Approximately 96% of n-grams in records that are absent from the local evidence excerpt are paraphrases of source content, not invented content. Voice is rephrasing; concepts are preserved.

### 6.2 Atomicity requires inference at four layers

A defensible position on what extraction is doing requires distinguishing **voice** (the model's surface-form preferences) from **content addition** (claims the document doesn't make). The substrate is voice-affected but not concept-injected. The categorical advantage of the substrate over paragraph-chunked retrieval comes from atomicity, and atomicity itself requires inference at four layers:

1. **Selection** — filtering claim content from non-claim scaffolding (front-matter, copyright, methodology bridges, tutorial exposition). doc_0031 (V2G Insights Final Report) has 123 substantive paragraphs and produces 60 records — 22 paragraphs (18%) are skipped, all front-matter, copyright, methodology bridge, or tutorial exposition. None carry mechanism-bearing content.
2. **Segmentation** — identifying atomic-claim boundaries within paragraphs. doc_0121 (ARENA Information Session) has 31 substantive paragraphs and produces 68 atomic records (ratio 2.19×). The single 1,652-character paragraph #19 (a 6-row table of eligibility criteria) is decomposed into 8 records: one per row plus a meta-record that synthesises the table's structure.
3. **Self-containment** — each record carries enough context (narrative, evidence excerpt, project, year, page) to be read alone. Absent self-containment, downstream clustering and synthesis would have to re-read source documents to disambiguate every record.
4. **Local synthesis** — the lesson field articulates the record's transferable implication. This is the most interpretive layer and is where most of the model's voice work happens.

A corpus-level statistic confirms that multi-claim-per-paragraph is common: 174 ARENA documents have ≥30 substantive paragraphs *and* produce more records than paragraphs (`INVESTIGATION_NOTES.md` Phase 4). A naive paragraph-chunking approach would either collapse multi-claim paragraphs into one chunk (massive information loss) or require its own intra-paragraph segmentation (which is exactly what the extraction is doing, just relocated). Voice is the price of synthesis at all four atomicity layers; voice is rephrasing, not invention.

### 6.3 Retraction: cross-paragraph context binding is not the strong claim

An earlier framing of the substrate's defensibility claimed that one-shot whole-document extraction binds whole-document context into each atomic record. A 50-record stratified audit found the claim was overstated: only ~30% of records show meaningful cross-paragraph context drawing (DOC_CONTEXT_DRAWN ≥50% novel content from elsewhere = 4%; MIXED 20–50% = 28%; VOICE_OR_IMPUTED <20% = 68%). Average doc-context rate: 13% as a strict 3-gram lower bound (`INVESTIGATION_NOTES.md` Phase 3).

The retraction matters because it locates the substrate's categorical advantage correctly. The advantage operates at selection and segmentation (§6.2), not at cross-paragraph context binding. Most narrative content is local-paragraph paraphrase. The substrate's value is that it identifies and segments claim content, not that it binds whole-document context into each record.

### 6.4 The lesson field has two epistemic layers

A separate finding about the `lesson` field, surfaced by spot-checking a section of doc_0705 (Middleback Ranges PHES). Lesson content mixes two kinds of material:

- **Document-grounded cross-record synthesis.** Example: "price suppression" generalising a measured price-reduction claim ("reduces South Australian wholesale electricity prices by an average of $1.60/MWh") in a sibling record. The phrase is the model's articulation, but the underlying mechanism is documented.
- **Pure model invention from training-data priors.** Example: lessons suggesting "capacity market or contract-for-difference mechanisms" or "public co-investment or concessional financing" as mitigations. A grep across the source markdown for `cfd | contract for difference | capacity market | concessional | co-invest | underwrit | subsid` returned zero hits. None of those mitigations appear in the document or in any other extracted record from doc_0705 — they are model-prior vocabulary for general policy-mechanism solutions to renewable infrastructure problems (`methodology_notes.md` §6.5).

Beyond mitigations, model invention reaches into cause-and-effect framing. On the same Middleback section, 7 of 9 cause-and-effect framing terms in lessons (e.g., "market saturation effects", "downside risk", "system value", "sub-linear scaling") returned zero hits in the source markdown. The narratives are clean — most of these terms appear only in lessons.

The pipeline's locked epistemic position (`methodology_notes.md` §7) is therefore stronger than the soft "lessons are interpretive" framing:

> The pipeline extracts cause-effect relationships that document authors chose to make explicit through grammatical signalling ("because", "due to", "as a result of"). It does not infer causal relationships from co-occurring observations across records. This restricts the failure-mode taxonomy to author-asserted causation and produces a smaller but more evidentiary-grounded dataset.

This is a methodological commitment with consequences. The narrative field is the primary tagging surface; the lesson field is retained but treated as model-interpretive at the mitigation and causal-explanation layers. The taxonomy work that follows (Stages III onwards) operates on records that pass the strict valence + mechanism-named filter. Records where causation is implied or inferable but not author-stated remain as observation evidence in the substrate but are not promoted to taxonomy entries.

## 7. Stage III — per-document event grouping

Stage III collapses atomic records that describe different aspects of the same occurrence into events. ARENA produces multiple aspect-distinct records per occurrence (cause / mechanism / intervention / outcome / lesson are common decompositions). The grouping stage recognises and consolidates these.

Three input-design decisions are load-bearing.

**Chronological accumulation across documents is the consolidation lever.** A 7-way comparison of grouping policies (`runs/2026-05-02-postextract-grouping-oneshot/notes.md` and `runs/2026-05-02-postextract-grouping-perdoc/notes.md`) ran identical 165-record inputs through different grouping configurations. One-shot all-records produces 63 events with 17% cross-doc grouping. Per-doc chronological with a running event registry passed between documents in seed-doc-first order produces 47 events with 26% cross-doc grouping. The mechanism: events span documents (a milestone report mentions a delay; the final report describes the same delay), and chronological accumulation gives the grouper the prior-event context needed to recognise cross-document references. Within-doc batching is incidental; chronological accumulation is the lever.

**The `lesson` field is excluded from grouping input.** Replicate Jaccard on pair-grouping decisions improved from 0.678 to 0.786 — a 16% stability gain — when lessons were dropped from the grouping prompt input (`runs/2026-05-02-replication-campaign/notes.md`). The mechanism: lessons carry model-synthesised cross-context inference (per §6.4), and paraphrase similarity in synthesised lesson text is itself noisy across reps. Stable grouping needs grounded text.

**Seed-doc heuristic.** Synthesis-title documents (those whose title indicates corpus-level synthesis: "Knowledge Sharing Report", "Annual Report", "Public Dissemination Report") are processed first; remaining documents are then ordered by token count, largest first (`pipeline/development/arena_canonical/narrative/seed_doc_heuristic.md`). The rationale: synthesis documents carry the corpus's most context-rich event articulations, and seeding the registry with them lets later documents bind their per-project events to the synthesis-document anchors when references match.

Replicate stability at corpus scale was characterised on REVS (12 documents, 937 records, 3 reps): mean 471 events/rep with sd 54.5 (12% relative noise); pair-set Jaccard 0.519. Single-pass grouping at scale is therefore noisy. The production output is a **consensus event graph**: pair-decisions across reps are merged at a ≥2/3 threshold, producing 483 events that reproduce 70% of the legacy v1 dedup's confident pairs while finding 1,330 cross-doc pairs v1 missed (`runs/2026-05-02-fullrevs-production/notes.md`). The consensus-graph mitigation is the production answer to single-pass instability; the underlying single-pass instability is a known limitation (§19).

ARENA event count after this stage: 62,301 events from 503 projects across 1,216 doc-calls, completed via Anthropic Batches API in 11 waves plus 11 sync mop-up waves on 2026-05-02.

## 8. Stage IV — six-axis record-type tagging

Stage IV labels every atomic record on six independent axes:

- `is_occurrence` (yes / no) — does the record describe something that happened?
- `is_mechanism` (yes / no) — does the record name a causal mechanism?
- `is_specification` (yes / no) — is the record a specification/criterion statement?
- `is_lesson` (yes / no) — is the record a transferable lesson?
- `is_recommendation` (yes / no) — is the record a recommendation?
- `valence` (positive / negative / neutral / no_valence) — outcome direction.

The four-value valence scheme is a refinement over an earlier three-value scheme. `no_valence` correctly identifies designed-mechanism descriptions and structural content; v1's three-way scheme forced these into `negative` or `neutral`. In pilot data, 31% of records are `no_valence`, which correctly collapses pure neutral to its proper rare meaning (~2%). Multi-label tagging is empirically necessary: 68% of records carry ≥2 type tags (51% carry exactly 2, 16% carry 3, 1% carry 4); a single-primary scheme would force coin flips on those records (`pipeline/development/arena_canonical/narrative/runs/2026-05-02-record-type-pilot/notes.md` EXP-2).

Production runs use Opus 4.6 at temperature 0. The model choice is consequential. A 2,000-record stratified validation comparing Sonnet 4.6 to Opus 4.6 found pool size matches between the two models within 0.6% by coincidence; composition diverges (Jaccard 0.76, ~28% of the failure-candidate pool would differ between tiers). On hand-adjudication of 24 disagreements, Opus was correct on 18 (75% under-tag direction): Sonnet under-tags `is_mechanism` at corpus scale by approximately 8,000 records vs Opus (`runs/2026-05-02-record-type-pilot/analysis/adjudication_is_mechanism.md`). Cross-tier disagreement is structurally interpretable, not noise: Haiku reads "no_valence" where Sonnet/Opus read "negative" via the underlying-situation rule. This is calibration sensitivity, not random error.

A separate finding from the pilot: **stability is not accuracy**. Sonnet 4.6 reaches 0.980 rep-pair stability on tagging tasks; Opus 4.6 reaches 0.969. Yet Opus's accuracy against hand-adjudication is 0.963 vs Sonnet's 0.806. High inter-rep agreement is necessary but not sufficient; on loose-boundary axes a model can confidently miscalibrate (memory note `feedback_stability_not_accuracy.md`).

Output schema is a deliberation surface. The tagging task produces a verbose JSON object per record with a separate field for each axis's verdict and reasoning. Schema-compression A/B (EXP-4) found that compressed schemas (single-letter keys or pure boolean tuples) lose calibration on loose-boundary axes (92% / 14% / 28% performance drops on the three loose axes). Verbose schemas were retained for tagging and for parent assignment because the schema structure itself is part of the prompt's instructional content. Compact JSON keys saved ~40% of output tokens in the glossary follow-up passes where the task is rule-application rather than calibration, but the savings disappear on tasks where output schema is a deliberation surface.

ARENA full-corpus tags: 90,192 records × 6 axes, Opus 4.6 temp 0. Cost: $141 sync.

## 9. Stage V — cluster filter

The clustering input is filtered by a predicate on the tags. Two predicates exist; both are documented.

- **Production failure-candidate (FC) filter** (used downstream for the lessons compendium and FC pool exports):
  `valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes') AND is_specification == 'no'`
  Yields ~19,795 records corpus-wide.

- **Clustering-input filter** (the looser predicate used for clustering):
  `valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes')` (no specification gate)
  Yields ~25,479 records corpus-wide.

The looser clustering-input filter is justified empirically (`pipeline/development/arena_clustering_v2/README.md`): records like "Forest waste 90% bark, 22% ash contamination, unsuitable for DICE fuel" get excluded by the spec gate but are useful as cluster seeds. Cluster-boundary detection separates pure-spec records from mechanism-bearing records naturally during the sweep, without needing the gate up front.

This is an instance of a more general principle the pipeline relies on: the **legitimacy filter as downstream calibration**. The ≥3-record cluster threshold (next stage) absorbs upstream filter false positives into singletons. A record that the filter shouldn't have admitted but did simply lands as a singleton and never founds a cluster; it doesn't pollute the substrate. This relieves precision pressure on the upstream filter and lets it be tuned for recall (memory note `feedback_clustering_threshold_as_legitimacy_filter.md`).

## 10. Stage VI — clustering

Clustering is the largest compositional engineering decision in the pipeline. It runs in four phases: seed → sweep → singleton sweep → residual closure.

### 10.1 Phase 4a — seed (script 05)

A stratified sample of 360 records is drawn — 8 ARENA categories × 3 axis-combos (`is_occurrence` only / `is_mechanism` only / both) × 15 records per stratum. A single Sonnet 4.6 call ingests the 360 records and produces mechanism-form clusters with a ≥3-record floor. Output: 45 seed clusters. Cost: ~$1.

### 10.2 Phase 4b — sweep (script 07)

The sweep iterates over the remaining ~25,000 records in 200-record batches. Each batch issues a single Sonnet 4.6 call containing two passes:

- **Pass 1: classify.** Each record in the batch is matched against the running catalogue. The model returns either a cluster ID or the literal "orphan."
- **Pass 2: cluster orphans.** Records that ended up "orphan" in this batch are clustered into new ≥3-member clusters. Newly-founded clusters are appended to the catalogue.

The two passes are bundled in a single response, separated semantically. Bundling is deliberate: classification (cheap, batched, calibrated by cross-record context) and orphan-clustering (combinatorial, expensive) have different attention demands but can share the cost of a single API call.

Three core design choices.

**≥3-record threshold.** No cluster is canonised on 1–2 records. Pending singletons accumulate and are revisited in the singleton sweep (10.3). This is the legitimacy filter at work.

**Late-binding descriptions.** Cluster definitions during the sweep are limited to canonical_name + mechanism_signature. Rich descriptions are deferred to closure so they don't bias future classifications by anchoring on early-member vocabulary.

**Procurement-probity invariant.** Once a cluster's `canonical_name + mechanism_signature` is published, it is immutable. Records joined the cluster under that signature; changing it would retroactively alter the matching rule. This rule has the same structure as government procurement probity — you cannot change tender criteria post-award. The invariant compounds: any past iteration's catalogue state is exactly reconstructible from the current catalogue (subset by creation iteration), no per-iteration snapshots needed. This made the controlled experiments below tractable at zero extra instrumentation cost.

ARENA sweep ran 128 iterations across 25,479 records. Trajectory:

| Phase | Iterations | Catalogue size | Post-Pass-1 orphan rate | Post-Pass-2 unplaced |
|---|---|---|---|---|
| Bootstrap | 1–2 | 45→75 | ~78% | ~54% |
| Mainstream capture | 3–12 | 75→200 | 78→43% | 33–44% |
| Apparent plateau | 13–22 | 200→292 | 43–49% | 22–40% |
| Decline resumed | 23–90 | 292→650 | 35–40% | 19–29% |
| Long-tail equilibrium | 91–128 | 650→797 | 22–30% | 15–22% |

Final state: 797 clusters in catalogue (45 seed + 752 founded in Pass 2), 17,164 records (67.4%) classified, 2,281 records (9.0%) placed as new-cluster founders, 6,034 records (23.7%) in pending-singleton pile. Cost: $39 sync / $19.50 batched, ~3 hours wall.

The "44% plateau" at iterations 13–22 was a transient feature, not equilibrium. Running 100+ further iterations brought the rate down to 22–30%. A 10-iteration plateau is not an equilibrium until you've run substantially longer.

### 10.3 Controlled experiment: prompt × method 2×2

A controlled experiment isolated the effect of prompt phrasing and batched-vs-per-record method on classification yield. The experiment design:

- For target iters K ∈ {30, 70, 110}, reconstruct the iter-K-start catalogue (catalogue sizes 333, 571, 734) using the procurement-probity invariant.
- Pull the 200 records classified in iter K from the production assignment log.
- Run those records through four arms:
  - **A**: batched + defensive prompt ("CRITICAL: Do NOT force-fit" + bullet list of don'ts).
  - **B**: per-record + defensive prompt.
  - **C**: per-record + neutral prompt (no "CRITICAL", no don'ts list).
  - **D**: batched + neutral prompt.

Classified records out of 200 per iter:

| Iter | Catalogue | A | B | C | **D** |
|---|---|---|---|---|---|
| 30 | 333 | 131 | 75 | 123 | **146** |
| 70 | 571 | 139 | 107 | 151 | **162** |
| 110 | 734 | 140 | 107 | 156 | **176** |

**Ordering is consistent: D > C > A > B at every iteration.** The findings:

1. The attention-dilution intuition (batched should get worse as catalogue grows) is wrong on Sonnet 4.6. Batched > per-record at every prompt condition. Cross-record calibration in batched mode is *helping*, not hurting.
2. The defensive prompt over-corrects in both methods. "Do not force-fit" + don'ts list suppresses 16–36 legitimate classifications per batch; per-record more so (since there's no neighbour calibration to anchor the model), but batched too.
3. The best single-method choice is batched + neutral. Cheaper, faster, and produces the most classifications without introducing reversals.
4. The original sweep used Arm A semantics. Re-running pending records with Arm D semantics recovers ~8–18% of records the defensive prompt wrongly orphaned, plus additional records that classify under the matured catalogue.

This experiment generalises beyond the clustering stage. The unifying principle, cross-confirmed by an earlier dedup-stage experiment in the same codebase: **for tasks that apply a rule across a set of items, present the items together**. Co-presented items give the model cross-item comparison as an implicit calibration anchor; chunking or per-item processing strips it away. Modern Sonnet's long-context capability means you pay almost nothing in attention quality for the larger context, and you gain calibration. The older intuition that "smaller prompts are better" is obsolete on Sonnet 4.6; the default should be one-shot or batched unless there is a hard reason not to be (memory note `feedback_one_shot_beats_chunked.md`).

### 10.4 Three-component precision envelope

Identical-input replication is not 100% even at temperature 0. The sweep's per-record precision is the compound of three measurable terms:

1. **LLM nondeterminism floor (~3–5%).** Same model, same input, slightly different output. Inherent in temperature-0 sampling at scale.
2. **Batch-composition sensitivity (~3–7%).** Same record + same prompt + same catalogue, different neighbouring records in the batch produces different classifications. The cross-record calibration signal is contextual.
3. **Cluster-boundary fuzziness (~10–22%).** When two regimes both classify a record, they pick different clusters a substantial fraction of the time. This is catalogue redundancy, not classifier error.

Compounded: identical-input replication is ~85–90%; identical-input but different-batch-composition replication is ~80–85%; among records both regimes classify, agreement on which cluster is ~75–90%. Each component is small individually but compounds. Each is bounded rather than dismissed (`arena_clustering_v2/notes.md` §6.8).

Closure-phase merge operations (10.6) directly reduce the third term; the first two are properties of the model and method.

### 10.5 Model selection: Haiku is unsuitable

A Haiku-vs-Sonnet A/B was run with the hope of a 75% cost reduction on the per-record classification stage. Three random 100-record samples from the pending pile were classified by both models against the 797-cluster catalogue. Haiku classified 145/300 records vs Sonnet's 42/300. Hand-inspection of 20 disagreements: Sonnet correct ~17/20; Haiku correct ~2–3/20. **Haiku force-fits on vocabulary.** Examples: UV degradation of EVA encapsulant → Haiku c042 *Electrode Material Degradation* (matched on "degradation"); harmonic impedance polygon methodology → Haiku c845 about meter sensitivity (mechanism unrelated). The cost differential is real but the precision loss is unaffordable for a methodology-paper artefact.

This finding generalises to a principle: **match model to task failure-mode**. The cost-tier ordering (Haiku < Sonnet < Opus) is not a capability ordering on every task. On per-record attribute tagging Sonnet under-tags `is_mechanism`; on cross-item merge-finding Sonnet over-flags (§10.6); on per-record vocabulary-trap classification Haiku force-fits. Choose the model by which error costs more, not by capability tier (memory note `feedback_match_model_to_task_failure_mode.md`).

### 10.6 Phase 4c — singleton sweep and residual closure

After the main sweep, the 6,034-record pending-singleton pile is revisited under Arm D semantics (batched + neutral prompt) against the matured 797-cluster catalogue. The reclassify pass cost ~$6 (vs a $120 per-record-cached estimate that motivated the Arm B experiment in the first place).

A combinatorial residual call then takes whatever doesn't classify and forms novel mechanism clusters. The catalogue converges to 1,141 clusters.

A closure-phase merge investigation cycled through five methods (`arena_clustering_v2/notes.md` §10):

- **Embedding shortlist** (Qwen3-Embedding-4B, 363 pairs above cos 0.65). Catches semantic-form near-duplicates well; misses same-mechanism-different-perspective pairs (e.g., c027 ↔ c738 tariff structure customer-side vs network-side at cos 0.56).
- **Qwen2.5-7B group-finder** (chunked, 25 regions × ~45 clusters). Too weak for subtle semantic-mechanism discrimination; over-conservative AND force-fitting simultaneously. Unsuitable.
- **Opus 4.7 one-shot over the whole catalogue** (cluster_id-numerical ordering). 17 merge groups affecting 36 clusters (3.2% of catalogue), $1.74. Hand-judged 5 strong, 3 plausible, 5 borderline, 2 wrong, 1 spurious (Opus included a "do NOT merge" group).
- **Opus 4.7 with greedy-NN-ordered catalogue** (each cluster placed adjacent to its embedding-nearest neighbour). 17 merge groups; one new pair caught (c003 ↔ c679); one previously-found pair missed. Combining cluster_id-order and NN-order gives 24 union pairs and 8 intersection pairs.
- **Sonnet 4.6 with NN-ordered catalogue.** **338 merge groups** affecting 615 of 1,141 clusters (53.9%). Catastrophic over-collapse: same prompt, same data, Opus → 17, Sonnet → 338 (20× discrepancy). On 20 hand-inspected Sonnet-only candidates, ~55% are clearly wrong force-fits. Sonnet is unaffordable for cross-item pattern-detection at this granularity.

Realistic merge count: ~15–25 pairs out of 1,141 clusters (~1.5–2% of catalogue). **The merges were not applied.** Each merge requires hand-review + cluster_id retag + downstream re-stat, the net effect on the artefact is small (cluster IDs change for ~30 records; analytical conclusions don't change), and non-application preserves the procurement-probity invariant in its strict form.

A within-tech distinctness probe (`05_opus_battery_subset.py`) selected the top-50 battery-storage-dominated clusters (size ≥10, battery_share 42–95%) and asked Opus the same merge question on the 50-cluster subset. **Zero merge groups proposed.** The catalogue's mechanism-level distinctions hold within a single tech category, not just across categories; the 17 catalogue-wide merges are not an attention artefact at the 1,141-cluster scale (`project_v2_within_tech_distinct.md`).

### 10.7 Substrate extraction

A separate Opus 4.7 closure pass classified all 1,141 clusters as either GENERAL (causal pathway applies broadly beyond renewable energy) or TECH_SPECIFIC. **711 of 1,141 (62.3%) classified GENERAL.** Top domain tags: program_design (150), infrastructure_project_delivery (147), data_systems_integration (116), regulatory_framework_design (103), modelling_methodology (99), supply_chain (95), equipment_lifecycle (91), novel_technology_adoption (82). Cost: $4.59, 4.5 minutes wall.

A boundary-fuzziness sample of clusters labelled TECH_SPECIFIC found that ~30–40% are domain instances of general patterns (Jevons paradox, design trade-offs, collective-action failures, system-architecture trade-offs) that didn't match the prompt's domain-tag vocabulary. The real general fraction is probably 70–80%. The 62.3% figure is a defensible **lower bound** — anyone challenging it can only push it higher — and is the figure the paper reports. The methodological framing this enables: the v2 substrate is best read not as a renewable-energy taxonomy but as a ~700-mechanism general taxonomy of infrastructure / program / coordination failures, plus a tech-specific layer.

## 11. Stage VII — parent derivation

Parent derivation is the single methodologically-richest stage. v1 derived 71 parents in a single Opus 4.7 call. The question that emerged from inspecting the result: how would we know if those 71 were the right 71? A second draw produces a different set. Without variance evidence, "v1 has 71 parents" is one observation, not a defensible claim about what the corpus contains.

The parent-derivation campaign (cost $106 spread across two days; `arena_closure/EXPERIMENTAL_METHODOLOGY.md`) produced four publishable findings beyond the parent set itself.

### 11.1 Single-pass derivations are arbitrary

A 50-rep Opus 4.7 ensemble at temperature default ran with identical input (1,141 v2 mechanism clusters) and identical prompt. Each rep produced its own parent set. Variance was high: parent counts per rep ranged 60–110, sd 13.6. The 50 reps produced 4,150 raw parent labels. The model's discretion about how many parents to produce spans factor-of-2.2 across draws.

This is decisive: any single rep is one draw from a wide distribution. The "v1 produced 71 parents" framing is misleading. Methodology rigour requires ensemble methods or equivalent variance evidence.

### 11.2 Naming examples in taxonomy prompts is a 50-percentage-point priming hazard

A specific concern about the original prompt: did it produce balanced coverage across mechanism families, or did it over-cluster on dominant areas (regulatory, capital) and under-cluster on others (equity, behavioural)? A soft-balance instruction was added: "ensure equity, behavioural, and similar under-represented mechanisms are at least sampled in your parent set." Equity-related parents appeared in 75% of reps with the instruction, vs 24% without — a 51-pp shift.

The shift looked like the constraint working as intended. Then the **clean** soft-balance variant was run — same constraint, with the example phrasings (the words "equity", "behavioural") removed. Equity dropped back to 25%. The 51-pp shift was not from the constraint; it was from the prompt naming "equity" as an example of what to look for.

Naming a candidate category in a taxonomy-derivation prompt — even as an illustrative example — produces a strong retention bias for that exact category. Production parent-derivation prompts must avoid named example categories. If a constraint matters, frame it abstractly ("ensure under-represented dimensions are surfaced") without specifying which dimensions (memory note `feedback_no_named_examples_in_taxonomy_prompts.md`).

### 11.3 Deliberation-rich prompts halve variance

A redesigned production prompt (`parent_derivation_clean.md`) made three changes:

- **PM-purpose framing.** The prompt explicitly names the audience (an ARENA portfolio manager scanning failure-mode space) and the use case (navigable diagnostic vocabulary). Parent-design decisions are anchored in user need, not abstract elegance.
- **No named example categories** (per the priming-hazard finding).
- **Deliberation as a load-bearing output field.** The model must surface every borderline split/merge decision as an explicit `deliberated_mechanisms` entry with verdict and reason. This makes the model's reasoning legible and auditable.

A 59-rep deliberation-rich ensemble produced parent counts in a tighter band: 89–105, sd 7.24. Variance halved (sd 13.6 → 7.24) without sacrificing legitimate mechanism coverage. The mechanism is straightforward: making the model surface its load-bearing decisions in a structured output field anchors it on the decisions that matter, reducing per-rep idiosyncrasy on borderline cases (`EXPERIMENTAL_METHODOLOGY.md` Phase 7).

The deliberation-rich ensemble was also run via the Anthropic Batches API for the 49-rep main batch; total ensemble cost was approximately $37 (vs ~$74 sync).

### 11.4 Threshold defensibility requires reasoning grounded in the canonical set

The 59-rep ensemble's outputs tier by rep agreement:

| Tier | Rep agreement | n classes |
|---|---|---|
| core | ≥90% (≥53 reps) | 43 |
| high | 70–89% (41–52 reps) | 28 |
| boundary | 40–69% (24–40 reps) | 26 |
| rare | 20–39% (12–23 reps) | 25 |
| singleton | <20% (<12 reps) | 176 |

Where to draw the line for canonical inclusion? An initial approach was to compare the 126-class consolidation against v1's 71 parents — see which threshold reproduces v1 most closely. This was rejected: the v1 set is itself a single arbitrary draw, and defending a threshold via comparison to v1 propagates v1's idiosyncrasy into the threshold decision.

The replacement: clean LLM judgement on the 126 canonical classes alone, with two independent ensemble validation passes.

- **Threshold-judgement ensemble** (10 reps of Opus 4.7 rating each canonical class for inclusion under the same prompt): agreement on which classes belong was high.
- **Category-selection ensemble** (10 reps of Opus 4.7 selecting which canonical classes to include in a final v2 set, without explicit threshold framing): agreement again high.

Both modes converged on ≥70% rep-agreement as the natural cut between "this names a real mechanism family" and "this is a single-rep idiosyncrasy."

The build phase consolidated the 43 core classes into v2 parent definitions, then judged the 28 high-tier classes for promote/hold/merge verdicts (43 + 27 promoted = 70 v2 parents; 1 high-tier merged). A coverage audit against v1's 71 parents then identified 8 v1 parents that v2 had subsumed; a boundary-tier extension call presented the 26 boundary-tier classes alongside v2 and asked for promote/merge/reject verdicts (16 promoted, 9 merged, 1 rejected). Final canonical set: **43 core + 27 high-promoted + 16 boundary-promoted = 86 parents**. Each parent in the canonical set carries provenance — source tier (core / high / boundary), n_reps_min, source class IDs — without which defending an inclusion against a "this is just one model's choice" challenge is impossible.

### 11.5 The coherence-test retraction

A separate test interrogated the 126 canonical classes: was each canonical class atomic, or had the consolidation step coarsened over run-level boundary choices? Each rep produces internally-distinct parents (no within-run overlap by construction), so any single rep contributing 2+ labels to one canonical class means that rep treated those as distinct mechanism classes. The canonical class then merges what the run treated as separate.

Result: 35 of 126 canonical classes (28%) are atomic (no run ever subdivided them); 91 (72%) have at least one run that contributed 2+ labels. **Every single core class (24/24, 100%) has at least one run that treated it as 2–4 distinct mechanism classes.** The most-agreed-upon canonical classes are the *least* atomic.

The retraction: "126 canonical mechanism classes" was a misleading headline. The 126 number is the union of run-level boundary choices, not a coherent atomic taxonomy. The correct framing distinguishes mechanism *territory* (what regions of mechanism space are covered, robustly and reproducibly) from atomic *boundaries* (where the cuts fall, which is draw-dependent at fine granularity). The substrate is best read as a stack of coarsenings: 1,141 clusters → 369 atomic sub-classes (a separate decomposition pass) → 126 canonical → 86 parents → 16 themes, each with its own reproducibility characteristics.

This is the kind of finding methodology papers should foreground: the field's intuitive framing was wrong, the empirical test was decisive, and the corrected position is more honest about what the substrate is.

## 12. Stage VIII — cluster-to-parent assignment and boundary mapping

A single Opus 4.7 one-shot call assigns every one of the 1,141 v2 mechanism clusters to exactly one of the 86 parents. ARENA result: 1,141/1,141 placed; 502 high-confidence / 632 medium / 7 low; 0 'none' assignments. Cost: $2.29, 809 seconds. No parent absorbs more than 5% of clusters; max is 50 clusters/parent (p07 model/forecast representational error); median is 11.

### 12.1 Blinded fixed-parent validation

An independent Opus 4.7 call re-rated 91 cluster→parent assignments (across 5 medium-sized parents: p25 Feedstock variability, p33 IBR dynamics, p44 SPOF, p61 Regulatory ambiguity, p77 Customer recruitment) using the original H/M/L rubric. The original-run confidence labels and rationales were held out from the input. The reviewer saw the cluster + the assigned parent only — not the other 85 parents in the panel — so this test isolates **criterion-fit** (does the cluster's mechanism match this parent's criterion?) from **selection** (which parent in the full panel is best?). Cost: $0.40 (`pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/README.md`).

3×3 confusion matrix (rows = original confidence, columns = blinded confidence):

| original ↓ \\ blinded → | high | medium | low | total |
|---|---|---|---|---|
| **high** | **45** | 3 | 0 | 48 |
| **medium** | 23 | **14** | 5 | 42 |
| **low** | 0 | 0 | **1** | 1 |

Defensible methodology-paper claims:

1. **High-confidence assignments are reliable.** 45 of 48 = **93.8%** high-high agreement under same-rubric blinded review. When the original run was confident, an independent run agrees almost always. (Note: an internal note in `CLUSTER_SIGNATURE_DRIFT.md` states this figure as 95.8%; the blinded validation README's confusion matrix is the authoritative source at 45/48 = 93.75%, rounded 93.8%.)

2. **Medium-confidence reflects selection ambiguity, not fit-criterion uncertainty.** 23/42 = 54.8% of medium-rated assignments upgrade to high under fixed-parent review. The chosen parent is a clean home for these clusters; the original run was correctly cautious about selection in an 86-parent panel where adjacent parents could also fit.

3. **No catastrophic miscalibration.** 0 two-step disagreements (no high↔low) across 91 assignments. Whatever instability exists is local, not catastrophic.

4. **Misfits track low/medium-low confidence.** All 5 medium→low downgrades and the single low-low case are at original-medium-or-lower. Confidence is usable as a triage filter, with the caveat that medium ≠ uniform fit-uncertainty.

What this test does NOT establish: selection quality (whether the chosen parent is the best of the 86 alternatives — a separate test below); calibration of the medium label as a probability (medium is a hedge under selection ambiguity, not a calibrated middle-probability of fit).

### 12.2 Boundary-mapping ensemble

A separate selection-task ensemble takes the assignment as a question rather than a verdict: 10 independent Opus 4.7 reps × 91 clusters × full 86-parent panel × identical v3 prompt, producing primary parent + optional secondary parent per rep. Variance comes from default sampling. Submitted via the Anthropic Batches API at 50% off; cost was $3.60 ($0.40 single-pilot + $1.80 nine-rep batched).

Pilot-scope ensemble headlines:

- **Primary stability**: 90.1% of clusters have ≥6/10 reps agreeing on primary; 74.7% have ≥8/10; 52.7% are unanimous.
- **Top-2 validation**: 73.6% of original assignments appear in top-2 across all 10 reps; 79.1% in ≥8/10 reps.
- **Strong reassignment candidates** (original never in any rep's top-2 across 10 reads): 5/91 — c1133, c1276, **c1282** (10/10 unanimous reassignment from p25 Feedstock to p18 Material limits), c1447, c1479.

A full-corpus 10-rep ensemble was then run at $22 batched (`full_corpus_ensemble_v3/full_summary.md`):

- 64.8% unanimous primaries; 81.1% ≥8/10 agree; 93.5% ≥6/10 agree.
- Original parent always in top-2: 73.5%; in ≥8/10 reps: 80.9%; never in top-2: 80 clusters (7.0%).
- 80 strong reassignment candidates; 94 unanimous disagreements (10/10 non-original primary).
- 86×86 adjacency heatmap and network diagram; cross-theme bridges identified (p18 hub linking t04↔t06; t11↔t12 economic-policy interface; t09↔t13 technical-coordination cascade at p38↔p70).

### 12.3 The two diagnostic shapes

The boundary-mapping ensemble distinguishes two qualitatively different signal shapes by **the concentration of disagreements at one alternative parent**.

- **Single-boundary problem (p25↔p18).** 75% of p25's disagreements (9 of 12 in the pilot) concentrate on one alternative parent: p18 Material, chemical, and physical-property limits. The pilot consistently re-reads "feedstock variability" assignments as "intrinsic material-property limit" assignments. At full-ensemble scale, p25↔p18 is the single most stable adjacency in the matrix (79 events across 100 cluster-rep observations, bidirectional, 10/10 reps). Five of seven 10/10-unanimous reassignments are p25→p18. The diagnosis: sharpen the criterion separating p25 (input variability hitting tolerance) from p18 (intrinsic property out of spec), or merge if the criteria can't be operationalised cleanly.

- **Structural fragmentation (p77).** 18% top-1 alternative concentration; p77's 11 disagreements scatter across **8 distinct alternative parents** (p75 trust, p78 behavioural rebound, p38 interoperability, p79 DR delivery, p68 contract structure, p46 heterogeneity-defeats-one-size, p66 subsidy distortions, p01 missing data). This is not a boundary problem — p77 is functioning as a catch-all for behavioural-layer customer-side mechanisms that ought to live in 8 different parents. The diagnosis: split p77 into more specific sub-categories.

Same disagreement data; two qualitatively different diagnoses. **This is itself a methodological contribution.** Boundary-mapping does not just say "where are the boundaries fuzzy" — it distinguishes "this line should be redrawn" from "this parent should be split". The concentration metric (top-1 alternative as a fraction of total disagreements for that parent) is the discriminator.

## 13. Stage IX — theme audit

A single Opus 4.7 audit-and-grouping call on the 86 parents produces 16 themes. Result: 86/86 keep verdict; 85/86 tight mechanism coherence; 16 themes; 0 unthemed parents; 4 candidate missing mechanism classes flagged for follow-up. Cost: $0.95.

The 16 themes (ordered by parent membership) are: t01 information and observability failures (p01–p06); t02 analytical, modelling, and inferential failures (p07–p12); t03 validation, verification, and translation gaps (p13–p15, p47); t04 physical and resource constraints (p16–p19); t05 saturation, residuals, and diminishing returns (p20–p21); t06 asset-level performance and physical-input failures (p22–p26); t07 external environment and hazard exposure (p27–p30); t08 power-system and grid-coupling failures (p31–p34); t09 control, communication, and integration failures (p35–p41); t10 architecture, dependency, and aggregate-structure fragility (p42–p46); t11 financial, capital, and economic-viability failures (p48–p58); t12 regulatory and policy failures (p59–p69); t13 inter-party coordination and incentive failures (p70–p74); t14 user, behavioural, and social-licence failures (p75–p79); t15 workforce and operational-process failures (p80–p82); t16 project execution and planning failures (p83–p86). [verify: an internal earlier draft (`INVESTIGATION_NOTES.md` Phase 7) reports 12 themes when grouping is done from the 70-parent build; the canonical 16-theme number applies to the 86-parent extended set per `EXPERIMENTAL_METHODOLOGY.md` Phase 9 and `full_corpus_ensemble_v3/adjacency_heatmap_themes.md`.]

A parent-gap audit comparing the 71-parent v1 layer against 126 canonical ensemble classes identified four candidate missing mechanism classes (`pipeline/development/arena_closure/output/parent_gap_audit.md`): schedule cascade and dependency delays (88% ensemble agreement); regulatory ambiguity, fragmentation, and jurisdictional conflict (82%); technology readiness and maturity gap (76%); communications and connectivity failures (72%). These are candidates for the next theme revision.

## 14. Stage X — glossary sub-pipeline

A separate eleven-stage sub-pipeline produces a corpus-specific glossary. Stages alternate between deterministic GPU-NLP passes (acronym surfacing, candidate term extraction, frequency counts, distinctiveness ratios) and LLM passes (definition, classification, sub-category propose-and-apply, project signature inversion). The pattern is a hybrid GPU-NLP plus LLM architecture: deterministic where the task is enumerative or counting; LLM where the task requires semantic disambiguation.

The methodologically distinctive piece is the **`reground` mode** (Pass 4 of the LLM passes). For each Pass-1-uncertain term, the script greps the corpus for narrative snippets containing the surface and feeds 2–3 to the model alongside Pass 1's first attempt. Sonnet either confirms the original definition or rewrites with corpus context. Reground resolved REVS as the V2G trial, MATCH as the UNSW DER study, EPWA as the energy-and-water authority — terms a priors-only pass could not have placed (`pipeline/development/arena_glossary/SESSION_WRITEUP_2026-05-05.md`).

A second methodologically distinctive piece is the **distinctiveness ratio** — observed share of mentions in a category divided by the corpus base share. DERMS has 65% of mentions in DER projects, 7.94× the corpus base; HVDC has 65% of mentions in System security & reliability, 16.3× the corpus base. The ratio is corpus-agnostic and does not require a hand-curated stopword list (the way TF-IDF effectively does).

A third is the **median-mention-year** as a year-trajectory metric, anchored against the corpus median. GFM (grid-forming inverters) shows as rising (median 2023 vs corpus 2019); LCOE shows as falling (median 2016); TRL shows as rising. This is a more stable signal than the naive first-third / last-third comparison because the corpus median anchors against ARENA's own growth trajectory.

ARENA glossary: 760 entries, 100 noise rejected, 11 categories. ANAO glossary: 590 entries, 10 noise rejected, 9 categories, 24 sub-categories. Total cost per corpus across all four LLM passes: ~$2.04 (Pass 1 acronyms $1.00, Pass 2 tail/titlecase/reground $0.65, subcategory propose+apply $0.39).

A final pass (g11) produces inverse signatures — project vocabulary fingerprints rather than term-by-term cards. ARENA: 489 project signatures from 503 projects; 14 projects had <10 mentions and yield genuinely thin signatures (correctly excluded). Distribution: 44 thin, 119 medium, 199 rich, 127 capped at 25 distinguishing terms.

A cross-corpus polysemy comparison between ARENA and ANAO glossaries identified 69 terms shared by surface form. A hand-inspection of those terms found that approximately 30% are polysemous false friends — the same surface form refers to materially different concepts in the two corpora. Examples: DMO is "Default Market Offer" in ARENA (energy retail) but "Defence Materiel Organisation" in ANAO; TGA is "Therapeutic Goods Administration" in ANAO but a thermogravimetric analysis abbreviation in ARENA technical documents; AEC, MMS, CMS, and ICT-related acronyms have similarly divergent referents. [verify: the explicit 30% computation does not appear in `arena_glossary/SESSION_WRITEUP_2026-05-05.md` directly; the figure has been carried in CLAUDE.md and the v1 paper draft. Worth confirming with the actual cross-corpus polysemy artefact before publication.]

## 15. Cross-cutting design choices

Several design choices cut across multiple stages. They are surfaced explicitly because each is a methodological commitment with consequences.

### 15.1 Engine versus configuration

The pipeline IP value depends on a clean separation between **engine** (generic, domain-agnostic code under `pipeline/`) and **domain configuration** (per-corpus settings under `domains/<name>/`).

Engine includes: `pipeline/ingest/` (BaseScraper contract, marker conversion, parallel workers); `pipeline/extract.py` (per-document extraction); `pipeline/run.py` (CLI dispatcher); the eleven-stage failure-mode sub-pipeline; the eleven-stage glossary sub-pipeline.

Domain configuration includes: `domains/<name>/scrape.py` (bespoke scraping script); `domains/<name>/domain.yaml` (model selection per stage, rate limit, estimated count); prompt templates (which load via two-pass rendering — `{single_braces}` for domain defaults filled at config load, `{{double_braces}}` for runtime placeholders); enums and category maps (where taxonomy is defined upfront).

The test of generalisation is rigorous: if adding a new corpus requires modifying any file under `pipeline/`, that is a generalisation failure. New corpora should add files only under `domains/` and `corpora/`. Scraping is the first place this distinction is tested (websites are too varied to generalise; each domain has a bespoke `scrape.py`); the extraction and analysis pipeline is where generalisation actually matters for the IP argument.

The empirical proof of the engine-config separation is the ANAO N=100 demonstration (§17). The same canonical extraction prompt and the same group_events prompt produced 4,765 atomic records and 4,483 events from 100 ANAO performance audits with no engine modification; only `domain.yaml` and `scrape.py` differ between ARENA and ANAO.

### 15.2 Extraction-first taxonomy posture

Two extraction approaches exist for taxonomy-bearing corpora:

- **Taxonomy-first** (the legacy ARENA approach): taxonomy is defined upfront, records are classified during extraction. Faster but couples extraction to taxonomy — the model's attention is shaped by the taxonomy categories, potentially biasing which observations get extracted. Taxonomy revisions require re-extraction.

- **Extraction-first** (the canonical approach): taxonomy-agnostic extraction produces pure factual records (Stage II); an informed taxonomy is designed from a sample of those records (Stage VII); taxonomy labels are applied as a separate classification pass (Stage VIII). More expensive initially but decouples extraction from taxonomy — taxonomy revisions only require re-running the cheap labelling pass, not re-extraction.

"Extraction-first" is **not** "bottom-up." The taxonomy is still designed by a researcher (or LLM acting as proxy) who reads records and makes interpretive judgements about useful dimensions. That is informed top-down design. The key distinction is *when* the taxonomy is defined relative to extraction, not *how* it is derived. The pipeline's parent set is hybrid: sample-informed (the 1,141-cluster catalogue is the "sample" for the parent ensemble), then frozen and applied at classification time. The 86 parents are not bottom-up emergent from records and not pure top-down imposed; they are derived from the corpus via a deliberation-rich ensemble and then applied as a fixed taxonomy (memory note `feedback_taxonomy_framing.md`).

### 15.3 The legitimacy filter as downstream calibration

The ≥3-record cluster threshold (Stage VI) is the pipeline's primary precision-vs-recall calibration mechanism. It absorbs upstream filter false positives into singletons. A record that the cluster filter (Stage V) shouldn't have admitted but did simply lands as a singleton and never founds a cluster; it doesn't pollute the substrate. This relieves precision pressure on the upstream filter and lets it be tuned for recall. The looser clustering-input filter (§9) is the filter design that the legitimacy threshold makes affordable.

This pattern repeats at the parent layer: the ≥70% rep-agreement threshold (§11.4) absorbs single-rep idiosyncrasy into the rare/singleton tail, which doesn't pollute the canonical 86-parent set. And at the boundary layer: pairs that don't survive 10/10 reps in the boundary-mapping ensemble are not promoted to canonical adjacencies. The pipeline is built on a consistent principle: legitimacy filters at downstream layers absorb upstream noise.

### 15.4 Distinctiveness over raw frequency

Where the pipeline measures concentration (glossary distinctiveness ratios; project-cluster intensity for reference-class memos; cluster-category distributions), the metric of choice is observed-share / base-share. Raw frequency is a corpus-property tail of uneven document lengths and category sizes; observed/base normalisation is corpus-agnostic, requires no hand-curated stopword list, and reduces to TF-IDF in the limit but generalises beyond term frequency.

### 15.5 Hybrid GPU-NLP plus LLM architecture

Stages alternate between deterministic GPU-NLP work (frequency counting, embedding, cosine similarity, k-means, grep) and LLM passes (semantic disambiguation, mechanism judgement, deliberation). The pattern is most visible in the glossary sub-pipeline (§14) but it operates at the failure-mode pipeline at coarser granularity too: extraction is LLM, filter is deterministic, sweep is LLM, embedding-merge-shortlist is GPU-NLP, merge adjudication is LLM, parent assignment is LLM, theme audit is LLM. Allocating each sub-task to the right tool gives reproducibility (deterministic stages are bit-exact) where reproducibility is achievable and gives semantic judgement (LLM) where the task requires it.

### 15.6 Multi-pass LLM strategy with targeted follow-ups

Several stages run a primary pass plus targeted follow-up modes. The glossary's Pass 4 reground is the cleanest example: Pass 1 produces a definition for every candidate term; reground specifically retries Pass-1-uncertain terms with corpus context. The cluster-singleton sweep (10.6) is the same pattern at a coarser granularity: the primary sweep produces a 797-cluster catalogue; the singleton sweep specifically retries pending singletons against the matured catalogue. Targeted follow-up is cheaper than running a second full pass and is targeted at the records that need it.

### 15.7 Layer-of-inference dependency

Each layer should be synthesised after its membership stabilises. The pipeline does this correctly at the parent layer (parents derived after the 1,141-cluster catalogue stabilised, via the deliberation-rich ensemble) and at the theme layer (themes derived after the 86-parent set stabilised, via a single audit-grouping call). It does **not** do this at the cluster-signature layer: each cluster's canonical_name + mechanism_signature is written at minting time from the founding 5–10 records, not re-synthesised after the membership stabilises. This is a disclosed gap (§19) with a costed fix that has not been committed.

## 16. Validation

Validation is a category-level argument, not a checklist. The pipeline is validated through two distinct routes (memory note `feedback_two_validation_routes.md`):

- **Stage-internal validation tests** measure per-stage statistical properties (replicate stability, ensemble agreement, hand-adjudication accuracy). These are the conventional measurement-instrument tests.
- **Use-case demonstrations** show the substrate doing the thing it's supposed to do (cross-tech / cross-time / cross-provider synthesis at the cluster layer; reference-class memos at the parent layer; cross-corpus convergent validity at the theme layer). These can substitute for stage-internal tests when the goal is utility rather than ground-truth verification.

The two routes are complementary; both are deployed.

### 16.1 Stage-internal validation: what has been measured

- **Substrate voice and grounding** (§6.1, §6.2): voice audit shows 0 invented bigrams above frequency threshold; concept-injection rate is approximately 0 at corpus scale; doc-context drawing rate is ~30% (a retraction of an earlier 100% framing). Voice is rephrasing, not invention. The legacy v1 pipeline achieved 92.2% grounding and 89.6% classification on QA verification; v3's substrate has not been re-verified at the same level (a known gap; §19).

- **Six-axis stability vs accuracy** (§8): Sonnet 0.980 stability / 0.806 accuracy; Opus 0.969 stability / 0.963 accuracy. Stability ≠ accuracy; choose the higher-accuracy model for loose-boundary axes.

- **One-shot beats chunked** (§10.3): 2×2 prompt-method experiment shows D > C > A > B at every iteration. Batched + neutral wins. The attention-dilution intuition is wrong on Sonnet 4.6.

- **Cluster→parent quality** (§12.1): 45/48 = 93.8% high-high agreement under blinded same-rubric review on a 91-cluster sample. 23/42 = 54.8% medium→high upgrade indicating selection ambiguity rather than fit-criterion uncertainty. 0 high↔low flips on 91 assignments.

- **Cluster→parent ensemble stability** (§12.2): 73.5% always-in-top-2 across 10 reps at full corpus; 64.8% unanimous primaries; 80 strong reassignment candidates; 94 unanimous disagreements.

- **Cross-project diversity** (`arena_clustering_v2/notes.md` §4): on 15 stratified-sample workhorse clusters (size 21–50), mean **17.8 unique projects per cluster** and mean **6.9 unique ARENA categories per cluster** (out of 20). The same mechanism appears in solar PV, hydrogen electrolyser, biomass scale-up, and storage projects — exactly the cross-project pattern that v1's 36% single-project-bound rate could not surface. Records-per-project ratio: 1.58.

- **Within-tech distinctness** (§10.6): top-50 battery-storage-dominated cluster subset (size ≥10, battery_share 42–95%) → **0 Opus-proposed merges**. The catalogue's mechanism-level distinctions hold within a single tech category, not just across categories.

- **Causal-chain coherence** (`pipeline/development/arena_closure/output/use_case_demos/causal_chain_full.md`): **88%** of v2 mechanism clusters form valid causal chains (X→Y→Z structure rather than mere co-occurrence patterns). Corpus-level evidence that the cluster layer captures mechanism structure, not text neighbourhood. [verify: the source banner is at line 14055 of the reading file but the exact corpus-level percentage was not re-confirmed inline in this draft against the full document; the figure is reported in `EXPERIMENTAL_METHODOLOGY.md` Phase 3.]

- **Event-coherence on multi-parent stratum** (`event_coherence_audit.md`): **98%** event-coherence on the multi-parent stratum — when a cluster's records spanned multiple parents, the parents really did describe distinct mechanisms. The few violations are ambiguous events. Confirms parents are not over-fit to artificially separate truly-related content. [verify: same caveat as above.]

- **Parent ensemble variance reduction** (§11.3): sd 13.6 → 7.24 (deliberation-rich vs terse prompt) without sacrificing legitimate mechanism coverage.

- **Glossary engine reproducibility**: cross-corpus deployment on ANAO with the same prompts and sub-stages produced a coherent 590-entry glossary at $2.04. The `reground` mode resolved corpus-specific acronyms (REVS, MATCH, EPWA on ARENA; analogous on ANAO) that priors-only passes could not place.

### 16.2 Use-case demonstrations

- **c042 cross-tech / cross-time / cross-provider synthesis** (§18). 150 records, 56 projects, 8 ARENA categories, project years 2010–2024.
- **h2biomass reference-class memo** (`pipeline/development/arena_closure/output/use_case_demos/h2biomass_refclass_memo.md`, `h2biomass_refclass_v2_data_driven.md`). Filter records by tech category, rank standout clusters by volume + concentration, read cross-tech transfer from non-filter members. The data-driven workflow: filter, don't hand-pick (memory note `feedback_data_driven_reference_class.md`).
- **foak RAG vs v2 demo** (`use_case_demos/foak_rag_vs_v2.md`). Explicit RAG-vs-v2 contrast worked example demonstrating that RAG returns passage excerpts; the v2 substrate returns mechanism clusters with cross-tech transfer pattern visible.
- **parent_archetypes_register** (`use_case_demos/parent_archetypes_register.md`). The 86-parent layer presented as a register of diagnostic vocabulary, demonstrating that the parents are usable as a shared language for failure-mode discussion rather than a curiosity-only artefact.
- **ANAO N=100 cross-corpus generalisation** (§17). Same prompts, different corpus, coherent output, structurally-distinct dedup behaviour that itself becomes a methodological finding.

### 16.3 What has NOT been validated

The substrate has explicit unmeasured properties. Naming them is methodologically important:

- **Formal claim-level fidelity at v3 scale** (legacy v1's 92.2% grounding at QA has not been reproduced for v3's 90,192-record substrate).
- **Replicate stability of grouping and clustering at full corpus**. Stage III is characterised on REVS (12 documents); Stage VI's classification is characterised by the 2×2 controlled experiment on 200 records × 3 catalogue snapshots. A 10-rep full-clustering-stage ensemble has not been run. The cost is **$360–550 batched** at full corpus (corrected from an earlier $1,500–5,000 figure that propagated from a wrong sweep-cost estimate; see §20). The blocker is structural (cluster IDs are not stable across reps; consensus partitions require record-pair co-occurrence analysis), not budget.
- **Cluster coherence audit on the canonical 1,141**. Legacy v1 had Stage F per-record cluster-fit verification; v3 has not yet replicated this.
- **Reassignment candidate audit**. The 80 strong reassignment candidates from the full-corpus parent ensemble (§12.2) have not been reviewed by hand.
- **Cluster signature re-synthesis** (§19; the central layer-of-inference gap).
- **Expert ground truth.** The substrate has not been reviewed by an external panel. The defensibility argument is internal to the pipeline (procurement-probity, ensemble agreement, blinded re-review).
- **Filter-chain calibration.** Three filters — Pass 3 realisation, Pass 2 parent assignment, Stage F cluster membership — have not been calibrated against human ground truth. Approximately 300 hand-tags would close this gap (~100 records per filter; researcher time, no API spend; `methodology_gaps.md` §1).

## 17. Generalisation: ANAO N=100

The strongest single argument for the pipeline as a methodology — rather than a one-off tool for ARENA — is that it generalises to a structurally distinct corpus without engine modification.

The Australian National Audit Office performance audit corpus (1,452 markdown files, 1996–2025) is structurally different from ARENA: documents are dense with findings, formatted to a 30-year-stable template, and concerned with administrative accountability rather than renewable engineering. A stratified sample of 100 ANAO performance audits (5 era bands × 20 docs each, seed 42) was processed through Stage I (ingestion via the ANAO domain config), Stage II (atomic-record extraction with the unchanged ARENA grave prompt), and Stage III (per-document event grouping with the unchanged canonical group_events prompt). Total spend: $81 across two extraction runs (one inefficient 16k-cap learning step plus the canonical marker-rendered run) plus per-doc event derivation.

Headlines:

- **Extraction**: 100/100 documents succeeded, 100% strict-parse, 4,765 atomic records, median 50 records/doc, max 120. 9 zero-record docs are a feature, not a failure: meta-reports and governance summaries that genuinely contain no atomic findings.
- **After multi-doc filter** (~5% of ANAO is multi-doc — follow-up audit pairs, recurring annuals, omnibus summaries): 4,617 records from 88 docs.
- **Event derivation**: 4,617 records → 4,483 events. Dedup ratio **1.03×**. 176 multi-record events.
- **Per-doc event derivation accuracy** (spot-check of 5 random multi-record events, seed 42): 4 of 5 correct or defensible (~80%).

The headline dedup ratio (1.03× vs ARENA's 1.16×) is not a transfer failure. It reveals a structural finding worth a methodology-paper note. ARENA's project-doc extraction emits multiple aspect-distinct records per occurrence (cause / mechanism / intervention / outcome / lesson) under a single event, which the grouper recognises and consolidates. ANAO's audit-doc extraction emits records sliced at sub-issue grain — different years, different sub-organisations, different audit-finding angles — that the grouper cannot merge without sacrificing precision. ANAO performance audits use a "summary-with-restatement-and-detail-shift" pattern where each restatement of a finding *adds new information* rather than just rephrasing.

The methodology-paper finding (`anao_n100_demo/notes.md`):

> Per-doc event derivation's effectiveness is bounded by extraction's atomicity choices. The aspect-merging logic transfers across corpora; the corpus-level dedup ratio depends on whether extraction emits records the grouper can recognise as aspects of one occurrence. Adapting the pipeline to corpora with structured-restatement-with-information-shift patterns would require either domain-aware extraction (e.g. emitting a `supports_finding` linkage) or a more aggressive event-derivation prompt that merges on shared underlying issue rather than shared occurrence. The current pipeline's correct-but-low-collapse behaviour on ANAO reflects atomicity choices, not prompt transfer failure.

### 17.1 Cross-corpus parent overlap

A separate Opus 4.7 call derived a 50-parent ANAO mechanism-class taxonomy from 207 ANAO mechanism clusters at $0.41 (`anao_n100_demo/output/anao_n100_parents.md`). A subsequent Opus 4.7 audit ($0.46) compared the 50-parent ANAO taxonomy against ARENA's 86 parents.

**9 mechanisms map cleanly between the taxonomies** (`anao_n100_arena_overlap.md`):

| Shared mechanism class | ANAO | ARENA |
|---|---|---|
| Data quality and integrity defects | p04 | p02 |
| Sample/instrument bias | p03 | p12 |
| IT/software system inadequacy | p05 | p40 |
| Cybersecurity and access control | p06 | p41 |
| Workforce capacity scarcity | p29 | p80 |
| Multi-party coordination without instrument | p33 | p70 |
| Policy uncertainty propagating downstream | p46 | p65 |
| Equity and distributional exclusion | p48 | p76 |
| Contract structure/specification defects | p22 | p68 |

**19 parents are ANAO-only** (Westminster-government accountability machinery): upward misrepresentation to decision-makers; public disclosure / transparency compliance; enterprise risk-management framework defects; governance body oversight failures; strategic-to-operational linkage gaps; eligibility / decision verification gaps; discretion / assessment inconsistency; contract execution / enforcement failure; transaction-level financial controls; cost estimation and budget tracking; machinery-of-government restructure disruption; complaints / feedback aggregation; risk-based compliance targeting; statutory / funding authority alignment; asset and maintenance lifecycle neglect; operational readiness masking; entity financial position drift; centralisation/decentralisation mismatch; **successive deferral normalising non-delivery**.

**17 parents are ARENA-only**: physical sensing and granularity; modelling / scientific knowledge; externalities and counterfactual measurement; pilot-to-scale and commissioning; physical / material / resource constraints; engineering trade-offs and saturation; capacity sizing and parasitic loads; fabrication, hazards, and siting; power-system and grid dynamics; control / comms / interoperability / standards; system architecture and aggregation; project finance and market economics; lock-in / supply chain / circularity; regulatory / incentive design pathologies; coordination economics and social licence; customer / behavioural response dynamics; project execution dynamics.

The two taxonomies are **substantially independent rather than nested**. ANAO is not a general programme-failure superset with ARENA's clean-energy specifics carved off; it is itself a specialised vocabulary — for accountability and administrative compliance — that omits much of the engineering, market, and behavioural mechanism space ARENA exercises. The shared core (~9–15 parents) sits in the cross-cutting territory: data, IT/security, workforce, coordination, contracting, equity, policy uncertainty.

This is a stronger generalisation finding than "the prompts work on a different corpus." It demonstrates that the engine produces a corpus-faithful mechanism vocabulary in each case — the ANAO taxonomy is not just ARENA's taxonomy with a Westminster suffix, and ARENA's is not ANAO's with a renewable suffix. The engine produces taxonomies that reflect the corpora they ingest. The cross-corpus shared core is itself a finding about which mechanism classes are **domain-agnostic** failure-mode categories — the ones an adjunct researcher could write up as a generalised programme-evaluation vocabulary.

This is what makes the **71-parent layer (or the 86-parent extended set) function as diagnostic vocabulary**: it is corpus-agnostic in design, and its corpus-agnostic surface area is empirically measurable through the cross-corpus overlap audit.

## 18. Worked example: cluster c042

The single most concrete demonstration of the substrate's analytical value is cluster c042, *Electrode Material Degradation From Chemical Incompatibility*. The cluster contains **150 records across 56 projects and 8 ARENA categories**, with project years spanning 2010–2024 and publish dates running through to early 2026 (`pipeline/development/arena_closure/output/cluster_reports/c042_report.md`).

The records span: green hydrogen (Fortescue low-temp direct electrochemical reduction; Cavendish ammonia-to-hydrogen; Hazer biogas reformer); direct electrochemical reduction of iron (50 wt% NaOH at ~100 °C eating cathodes, structural alloys, polymer binders, membranes); perovskite and tandem PV (Au/Ag/Cu rear-electrode degradation; Spiro-OMeTAD HTL instability; EVA-perovskite reactions); concentrated solar thermal (supercritical CO₂ dissolving PTFE seals; nitrate / chloride / carbonate salt corrosion; PCM leaching from geopolymer); advanced batteries; biofuels; hydrogen blending in gas networks; geothermal (Cooper Basin caustic stress-corrosion cracking on V150 production casing).

What c042 demonstrates that no single project's report could:

- The mechanism (intrinsic electrochemical incompatibility between functional materials and operating species) is **time-invariant in physics** but time-variant in the available materials, barrier technologies, and mitigation costs.
- The mechanism activates regardless of quality control or careful operation; it is a structural consequence of the project's value proposition where the value proposition forces a chemistry.
- A clear temporal sub-pattern: older records (2013–2018) identify the archetype as a single material-pair problem ("gold diffuses", "PTFE swells in CO₂", "nitrate salts decompose"); newer records (2022–2026) describe interaction matrices, multiple coupled failure modes, and emergence at scale-up rather than at lab scale.
- Five recurring families of mitigation (substitution, barrier and coating, upstream conditioning, operational envelope restriction, over-specification), each with documented cost-benefit profiles.
- Three concrete portfolio adjustments: scope diligence to require an explicit materials-compatibility map; build long-duration exposure tests into milestone gates; cost in mitigation upfront because "drop-in cheap material" theories of cost reduction almost always understate lifetime cost.

c042 is the worked example the methodology paper leads with because it visibly delivers on the v2 substrate's design promise: cross-tech, cross-time, cross-provider synthesis with full citation traceability back to specific records, project documents, and source pages. No RAG query against the same corpus would produce this synthesis; the substrate is what makes the synthesis tractable.

Other worked examples archived for the methodology paper's appendices: c016 (`cluster_reports/c016_report.md`), c1074 (`cluster_reports/c1074_report.md`), p18 *Material, chemical, and physical-property limits* parent report (`parent_reports/p18_report.md`), the Neoen Big Battery Western Downs project report (`project_reports/`), the h2biomass reference-class memo, the foak rag-vs-v2 demonstration, and the parent_archetypes_register (`use_case_demos/parent_archetypes_register.md`).

## 19. Limitations and disclosed gaps

The pipeline has limitations. Disclosing them directly is methodologically stronger than hiding them.

### 19.1 Cluster signature drift

Each v2 cluster carries a `canonical_name` and a `mechanism_signature` written **at cluster birth** — when the cluster was first minted by the sweep algorithm, based on the records present in that founding batch (typically 5–10 records). As reclassification, singleton sweep, and residual passes added more records to the cluster, the signature was not updated. A cluster with a final membership of 30 records may carry a mechanism description derived from its first 5–10 members.

Affected layers: parent assignment (Opus matches cluster signatures against parent mechanism criteria; drift-affected signatures cause a fraction of medium-confidence "selection ambiguity" cases to be ambiguous artificially); theme audit (operates on parents, so it is one layer removed); boundary mapping (cross-theme adjacency strengths are partly real mechanism cousinship and partly signature drift).

What is robust to drift: strong, consistent edges (≥10/10 reps, ≥40 events) — drift cannot manufacture 130-event bidirectional adjacency from nothing. What is less robust: long-tail edges (≤30 events) — drift artefacts likely contaminate.

The fix is a one-shot Opus re-synthesis pass for each of the 1,141 clusters using the cluster's full member record set. Cost estimate (2026-05-09 pricing): per-call sync ~$0.30 (~$340 total sync); batched ~$170. Plus a follow-up parent-assignment ensemble at ~$25. **Total fix cost: ~$170 batched plus ~$25 re-ensemble. Not committed.** The cost is real money for a marginal improvement on a finding that is already publishable, and the v2 substrate has been in use for two months without this fix; adding it now would invalidate prior cluster-report artefacts (c042 etc.) which would need re-running.

### 19.2 Voice is the price of synthesis

The substrate's value proposition — atomic records that survive analytical use without requiring re-reading of source documents — depends on inference at four layers (selection, segmentation, self-containment, local synthesis; §6.2). Voice is the model's footprint at all four layers. The voice audit (§6.1) finds that voice is rephrasing, not invention; the doc-context audit (§6.3) confirms that ~30% of records show meaningful cross-paragraph context drawing while ~68% are local-paragraph paraphrase. The substrate is voice-affected but not concept-injected.

This is not a soft-pedalled limitation; it is a load-bearing methodological position. Atomicity requires inference. Records cannot be made atomic by paragraph chunking without requiring intra-paragraph segmentation logic (which is what extraction is doing, just relocated). A reviewer who insists on a voice-free substrate is asking for a substrate that does not do the work the substrate is for. The honest framing is to acknowledge the voice-affected character and document the audit results (memory note `feedback_atomicity_requires_inference.md`).

### 19.3 Lesson-field model invention

The `lesson` field carries two epistemic layers (§6.4): document-grounded cross-record synthesis and pure model invention from training-data priors. The hand-traced subset (Middleback Ranges PHES section 10.3) found 7 of 9 cause-and-effect framing terms in lessons return zero hits in source markdown; mitigation suggestions like "capacity market" or "contract-for-difference" are model-prior vocabulary, not document-grounded.

The pipeline's locked epistemic position (`methodology_notes.md` §7) is to extract cause-effect relationships that document authors chose to make explicit through grammatical signalling and not to infer causal relationships from co-occurring observations across records. Mitigation language that does not match content in source documents should be treated as suggested rather than evidenced.

### 19.4 Sonnet under-tags `is_mechanism`

At corpus scale, Sonnet 4.6 under-tags `is_mechanism` by approximately 8,000 records vs Opus 4.6 (out of 90,192). Hand-adjudication of 24 cross-tier disagreements: 18 (75%) are under-tag-direction errors favouring Opus. The cross-tier disagreement is structurally interpretable, not noise — Sonnet under-tags loose-boundary axes by reading less-aggressively. For loose-boundary axes the higher-accuracy model wins; choose by which error costs more, not by capability tier (memory note `feedback_sonnet_undertags_mechanism.md`).

### 19.5 The cluster-layer ensemble that wasn't run

A 10-rep ensemble of the full clustering stage (sweep + reclassify + residual + closure) at full corpus would cost **$360–550 batched** (corrected from an earlier $1,500–5,000 estimate; see §20). The blocker is structural rather than budgetary: cluster IDs are not stable across reps, and consensus partitions require record-pair co-occurrence analysis across reps to derive a stable consensus catalogue. This is a methodology design problem, not a cost problem. The work has not been done. It would directly answer the question "is the 1,141-cluster catalogue itself reproducible at the cluster-membership level?" — a question that the per-record stability findings (§10.4) and the 2×2 controlled experiment (§10.3) speak to indirectly but do not settle.

### 19.6 Single-rep production at corpus scale

Stage III (per-document grouping) was run as the consensus event graph at ≥2/3 threshold of three reps on REVS, but the production full-corpus run was effectively single-pass. Pair-set Jaccard at 12-doc REVS scale is 0.519; mean events/rep sd is 12% relative. The substrate carries this single-pass-at-scale cost. The consensus-graph mitigation has been validated at 12-doc scale; running it at full corpus would multiply the grouping cost by the rep count (~$120 for 3 reps).

### 19.7 Output schema design as a free parameter

Output schema affects per-axis calibration on loose-boundary tasks (§8). Compressed JSON keys saved 40% output tokens on glossary follow-ups but lose calibration on tagging and parent assignment. The right schema choice is task-dependent and is not yet automated. Verbose schemas were retained for tagging, clustering, and parent assignment; compact schemas were retained for glossary follow-ups (memory note `feedback_output_format_deliberation.md`).

### 19.8 Polysemy detected but not resolved

Cross-corpus glossary polysemy was detected (§14): approximately 30% of the 69 surface-form-shared ARENA/ANAO terms are false friends. The detection is an artefact of the cross-corpus comparison; resolution (e.g., per-corpus disambiguation token, or shared cross-corpus disambiguation glossary) has not been built. Multi-corpus deployments of the pipeline will need to disambiguate.

### 19.9 Mechanism-level causal inference is shallow by design

The pipeline does not infer cross-record causation. The locked epistemic position (§6.4) restricts the substrate to author-asserted causation. This is a deliberate scope choice; readers who want a corpus-scale causal graph will not find one in the substrate.

## 20. Cost economics and reproducibility

Cost economics matter because reproducibility depends on whether other research groups can afford to run the methodology. The full ARENA build cost approximately:

| Stage | Cost | Notes |
|---|---|---|
| Stage I — ingestion (PDF→markdown via Marker) | (negligible per-doc) | One-time |
| Stage II — atomic record extraction (90,192 records, Opus 4.6) | (included in Day-1 tagging tally) | |
| Stage III — per-doc event grouping | (in Day-1 dedup tally) | |
| Stage IV — six-axis tagging (90,192 records, Opus 4.6) | $141 | Day-1 tagging |
| Stage V — cluster filter | (deterministic) | Free |
| Stage VI — clustering (sweep + reclassify + residual + closure) | $73 | Day-2 |
| Stage VII — parent derivation campaign (50-rep + diagnostics + threshold + 59-rep deliberation-rich + build phase) | ~$106 | |
| Stage VIII — cluster→parent assignment + blinded validation + boundary-mapping ensemble | $2.69 + $0.40 + $3.60 + $22 batched | |
| Stage IX — theme audit | $0.95 | |
| Stage X — glossary sub-pipeline (per corpus) | ~$2 | |
| Closure substrate-extraction (general/tech-specific) | $4.59 | |

Day-1 total ~$262; Day-2 total ~$73; parent-derivation campaign ~$106; closure ~$30. Approximate grand total: **~$471 across the full pipeline build**, with the build phase (the parts that produce canonical artefacts) costing ~$13 at the layer-of-inference apex (the build passes for parents, themes, and assignments).

The largest line items are tagging ($141) and dedup ($121). These are linear in corpus size; doubling the corpus doubles the cost approximately. The campaign-style spend (parent-derivation ~$106, boundary-mapping ensemble $22) is approximately corpus-size-invariant — a 10× larger corpus at the same atomic-record density would not 10× the parent-derivation cost.

A previously-documented "§16 cluster-layer ensemble gap" of $1,500–5,000 was wrong. Actual v2 clustering sweep cost is $39 sync / $19.50 batched per rep, plus ~$15 for reclassify + third pass + convergence. Per-rep total ~$55 sync / ~$36 batched. **A 10-rep full-clustering-stage ensemble is therefore $360–550 batched, not $1,500–5,000.** The correction matters for methodology-paper readers because the affordability of a missing validation step depends on the correct cost figure (memory note `feedback_ensemble_at_affordable_layers.md`).

The general principle: **ensembles are economically defensible at affordable layers.** Parent / glossary / threshold / boundary-mapping ensembles cost ~$25 each; cluster-layer ensembles cost $360–550 (batched) or ~$550 (sync). All of these are within reach for a single research group with modest API spend. The pipeline is not a budget gate.

## 21. Future work

The pipeline has visible next steps. Each is cheap relative to what is already demonstrated; the ordering reflects which steps would most strengthen specific methodology-paper claims.

**Stage-internal validation tests** (largely hand-tag work, modest API spend).

- Cluster-signature re-synthesis ($170 batched + ~$25 re-ensemble) to close the layer-of-inference gap at the cluster signature layer.
- Filter-chain calibration (~300 hand-tags total) on Pass 3 realisation, Pass 2 parent assignment, and Stage F cluster membership, to populate the joint-reliability formula in §1.
- Replicate-stability characterisation of the full clustering stage ($360–550 batched for 10 reps) plus consensus-partition methodology design.
- Per-cluster fit_pct audit (~$10–20) reproducing the legacy v1 Stage F at v3 scale.

**Use-case demonstrations** (cluster reports, project reports, reference-class memos).

- Additional cluster reports beyond c042 (c016 and c1074 are drafted; the parent_archetypes_register is partially populated).
- Project-axis retrieval reports for ARENA flagship projects (Neoen Big Battery Western Downs is drafted).
- Reference-class memo workflow for h2biomass-class evaluations across the portfolio.
- An adjunct-engagement publication track: 3–5 peer-reviewable case studies built on the substrate (the c042 report, an ANAO-vs-ARENA cross-corpus convergent-validity paper, a methodology paper proper).

**Cross-corpus extensions** (Productivity Commission, Royal Commissions, APH committee reports). PC is currently a RAG-only corpus and not pursuing taxonomy work; APH is in ingestion. Each cross-corpus extension is an empirical test of the engine-config separation and a richer overlap audit dataset.

These items partition into the two validation routes (§16). Either route can substantiate the methodology paper's claims; use-case demonstrations are particularly useful when the goal is utility rather than ground-truth verification (memory note `feedback_two_validation_routes.md`).

## 22. Conclusion

The pipeline produces a four-layer structured-knowledge artefact (records → mechanism clusters → parent classes → themes) plus a corpus-specific glossary, on a clean engine-versus-configuration separation that has been proved out by reproducing the methodology end-to-end on a structurally distinct corpus (ANAO N=100). The artefact is not a retrieval index; it is a persistent analytical substrate that supports cross-document, cross-project, cross-time, cross-technology synthesis with citation traceability.

Eight methodological design choices distinguish the pipeline from other LLM-extraction systems:

1. Extraction-first rather than taxonomy-first (taxonomy decoupled from extraction).
2. Atomicity through inference at four layers (selection, segmentation, self-containment, local synthesis), with voice as the price of synthesis.
3. Six-axis multi-label record-type tagging with Opus 4.6 (Sonnet under-tags `is_mechanism`).
4. Looser cluster-input filter compensated by ≥3-record legitimacy threshold (legitimacy filters as downstream calibration).
5. Procurement-probity invariant on cluster signatures (immutability post-publication).
6. Batched + neutral classification (one-shot beats chunked on Sonnet 4.6).
7. Deliberation-rich ensemble parent derivation (variance halved; priming hazard avoided; threshold defended on canonical set).
8. Boundary-mapping ensembles distinguishing single-boundary from structural fragmentation diagnostic shapes.

The substrate is validated through stage-internal tests (substrate voice and grounding; six-axis stability vs accuracy; one-shot vs chunked; cluster→parent agreement at 93.8% high-high; parent ensemble variance reduction; cross-project diversity at 17.8 projects per cluster; within-tech distinctness with 0 Opus-proposed merges; causal-chain coherence at 88%; event-coherence on multi-parent stratum at 98%) and through use-case demonstrations (c042 cross-tech / cross-time / cross-provider synthesis; ANAO N=100 cross-corpus generalisation; ANAO↔ARENA parent overlap audit demonstrating 9 cleanly-shared mechanism classes and 17/19 corpus-specific extensions).

The substrate is **not** validated against expert ground truth, against a 10-rep full-clustering ensemble at full corpus, or against a re-synthesised cluster signature layer. Each of these is a known gap with a costed fix, and each is affordable; the pipeline is not a budget gate.

The strongest single claim is generalisability. The 71-parent layer (or the 86-parent extended set) is a corpus-agnostic diagnostic vocabulary for programme-evaluation work; 62.3% of the 1,141 ARENA mechanism clusters describe causal pathways that apply beyond renewable energy contexts; the ANAO N=100 demonstration reproduces the methodology on a different corpus with token-substitution-only configuration changes. The substrate is best read as a general infrastructure-failure substrate with a renewable-bound layer, and the pipeline is best read as a methodology for producing such substrates rather than a one-off ARENA tool.

This positions the artefact as a research-topic generator and memo producer. The deliverables that follow — publishable case studies, cross-corpus convergent-validity papers, methodology hardening work — are the research programme that an adjunct engagement at ANU's Institute for Climate, Energy and Disaster Solutions would deliver. Each gap above is a publishable extension; together they form a 12–18 month research agenda that would harden the substrate without changing its core architecture.

---

## Appendix A. Source provenance

This paper draws primarily on the following T1 source documents in `pipeline/development/`:

- `arena_canonical/narrative/methodology_notes.md` — top-level methodology, locked epistemic position, measurement-instrument framing
- `arena_canonical/narrative/methodology_gaps.md` — gap register
- `arena_canonical/PIPELINE.md`, `arena_canonical/README.md`, `arena_canonical/narrative/README.md`, `arena_canonical/narrative/runs/README.md` — pipeline diagrams and run summaries
- `arena_clustering_v2/README.md`, `arena_clustering_v2/notes.md`, `arena_clustering_v2/notes_attention_test.md` — clustering architecture, sweep trajectory, controlled experiments, precision envelope, substrate extraction
- `arena_canonical/narrative/clustering_v2_notes.md`, `clustering_v2_inspection_notes.md` — clustering inspection
- `arena_closure/EXPERIMENTAL_METHODOLOGY.md` — parent-derivation campaign methodology and findings
- `arena_closure/output/parent_ensemble/INVESTIGATION_NOTES.md` — substrate defensibility investigation, voice audit, doc-context audit, coherence test, atomic sub-class decomposition
- `arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/README.md` — blinded validation primary findings
- `arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/CLUSTER_SIGNATURE_DRIFT.md` — cluster signature drift gap
- `arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/PILOT_boundary_mapping_2026-05-08.md`, `PILOT_ENSEMBLE_2026-05-08.md`, `full_corpus_ensemble_v3/full_summary.md`, `adjacency_heatmap_themes.md` — boundary-mapping ensemble
- `arena_canonical/narrative/runs/2026-05-02-record-type-pilot/notes.md` and `analysis/adjudication_*.md` — six-axis tagging pilots
- `arena_canonical/narrative/runs/2026-05-02-postextract-grouping*.md`, `2026-05-02-replication-campaign/notes.md`, `2026-05-02-fullrevs-production/notes.md` — grouping experiments
- `arena_canonical/narrative/seed_doc_heuristic.md` — seed-doc heuristic
- `anao_n100_demo/notes.md`, `anao_n100_demo/output/anao_n100_arena_overlap.md`, `anao_n100_demo/output/anao_n100_parents.md` — ANAO N=100 demonstration
- `arena_glossary/SESSION_WRITEUP_2026-05-05.md` — glossary sub-pipeline
- `arena_closure/output/cluster_reports/c042_report.md`, `c016_report.md`, `c1074_report.md`, `parent_reports/p18_report.md`, `project_reports/`, `use_case_demos/*` — worked examples

All source paths are relative to `/home/jeffzda/broadlearnings/pipeline/development/`. CLAUDE.md memory notes (referenced inline) sit in `/home/jeffzda/.claude/projects/-home-jeffzda-broadlearnings/memory/`.

## Appendix B. Items flagged for verification

- **§13** Theme count of 16: the canonical 86-parent set produces 16 themes (per `EXPERIMENTAL_METHODOLOGY.md` Phase 9 and `full_corpus_ensemble_v3/adjacency_heatmap_themes.md`). An earlier 70-parent build (`INVESTIGATION_NOTES.md` Phase 7) reports 12 themes. This paper uses 16 throughout but the discrepancy should be confirmed before publication.
- **§14** "~30% polysemy" figure for the 69 cross-corpus shared terms: the figure is reported in CLAUDE.md memory but the explicit computation does not appear in `arena_glossary/SESSION_WRITEUP_2026-05-05.md`. Confirm provenance before publication.
- **§16.1** Causal-chain coherence at 88% and event-coherence at 98%: figures cited in `EXPERIMENTAL_METHODOLOGY.md` Phase 3 (scripts 25–27) but not re-confirmed against the full `causal_chain_full.md` and `event_coherence_audit.md` in this draft cycle. Worth confirming the exact corpus-level percentages before publication.
- **§19.1** Cluster-signature drift fix cost: paper cites $170 batched + ~$25 re-ensemble = ~$195 total. The drift gap document (`CLUSTER_SIGNATURE_DRIFT.md`) confirms the $170 batched signature-resynthesis figure but the ~$25 follow-up re-ensemble cost is paraphrased from the blinded-validation README; confirm before publication.
