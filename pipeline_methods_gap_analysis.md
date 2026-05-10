# Gap analysis — `pipeline_methods_v1.md` vs `pipeline_methods_reading.md`

**Method.** The paper draft (592 lines, §1–§10) was read end to end, then each section was checked against the source-banner block(s) that the reading file co-locates under that section. Tier weighting (T1 load-bearing, T2 depth, T3 worked examples) was applied: gaps relative to T1 narrative documents are flagged most heavily; T3 cluster/parent/project reports are mined for §7 (Demonstration) only. Where the paper is already faithful, the section is parked in the "Sections judged faithful" list.

---

## §Abstract

**Paper claims (current):** Pipeline produces (a) record substrate, (b) cluster catalogue, (c) parent/theme taxonomy, (d) glossary; engine/config separation; demonstrated on ARENA (1,440 docs / 90,192 records / 1,141 clusters / 86 parents / 16 themes / 760-term glossary) and partially on ANAO (1,452 docs / 590-term glossary / N=100 clustering pilot).

**Source docs say (delta):**
- The 16-theme number is correct in the paper but the source's headline ARENA pipeline cost is articulated more concretely: ~$262 day-1 (tagging $141 + dedup $121) + ~$73 day-2 (clustering); blinded validation was $0.40 + $3.60 + $22 batched; parent-derivation campaign ~$106; closure substrate-extraction $4.59 (`arena_clustering_v2/notes.md` §8; `EXPERIMENTAL_METHODOLOGY.md`). The abstract gives no headline cost figure.
- Source documents make the **two-axis retrieval architecture (mechanism axis = clusters, occurrence axis = events)** a load-bearing methodology claim (`methodology_gaps.md` §10). The abstract does not mention it.
- Source documents make the **62.3% general-mechanism substrate** finding a paper-headline finding (`arena_clustering_v2/notes.md` §10.3 — "the v2 methodology produced … not a renewable-energy taxonomy, but a ~700-mechanism general taxonomy of infrastructure / program / coordination failures"). The abstract does not mention it.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** Append two sentences to the abstract: (1) "Of the 1,141 clusters, 711 (62.3%) describe mechanisms whose causal pathways apply beyond renewable energy contexts, suggesting the substrate functions as a general infrastructure-failure taxonomy with a renewable-bound layer." (2) "The pipeline produces two orthogonal retrieval axes from one extraction — a mechanism axis (clusters) and an occurrence axis (events) — with provenance preserved on each." Optionally add a one-line cost summary so reviewers can size the artefact's marginal cost.

**Source citations:** `pipeline/development/arena_clustering_v2/notes.md` §10.3; `pipeline/development/arena_canonical/narrative/methodology_gaps.md` §10; `pipeline/development/arena_closure/EXPERIMENTAL_METHODOLOGY.md`.

---

## §1 Introduction

**Paper claims (current):** Frames the gap (manual vs full-text retrieval), positions the four-layer hierarchy (records → clusters → parents → themes), states corpus-independence, and positions the artefact as a "research substrate rather than an operational tool" with named bounded uncertainty.

**Source docs say (delta):**
- `methodology_notes.md` §11 ("Pipeline as measurement instrument — traceable uncertainty (locked, 2026-05-01)") makes the **measurement-instrument framing with efficiency-chain reliability** the strongest single argument for the paper's contribution: η_total = ∏ η_i, with per-filter reliabilities tabulated and a live joint-reliability readout proposed. The paper's introduction gestures at "named, bounded uncertainty" but does not name the efficiency-chain framing or the per-filter reliability table.
- The introduction names the counterfactual ("portfolio manager who needs a structured, queryable representation") but does not adopt the source's **value-against-counterfactual** framing (`methodology_notes.md` §8): "the right comparison is not a hand-curated gold standard … but the counterfactual scenario where the PM reads 1,440 documents personally."

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** Add a paragraph before "This pipeline addresses that gap..." that names the measurement-instrument framing: "The pipeline is positioned as a measurement instrument with traceable, decomposable, computable uncertainty: every filter applied during retrieval has an associated label-reliability, and the joint reliability of any query is the product of per-filter reliabilities along the retrieval chain (the efficiency-chain frame; see §6). This is a meaningfully harder claim than most synthesis taxonomies offer, because every uncertainty source is named and independently measurable." Cite `methodology_notes.md` §11.

**Source citations:** `pipeline/development/arena_canonical/narrative/methodology_notes.md` §8, §11.

---

## §2 Related work

**Paper claims (current):** Names five adjacent literatures — computational content analysis, LLM-based information extraction, knowledge graph construction, document clustering / topic modelling, glossary construction — with citations to be filled in by hand.

**Source docs say (delta):** No direct source coverage in the reading file (the development notes do not contain a literature review; the paper acknowledges this explicitly). One framing detail worth incorporating: source documents repeatedly contrast the pipeline against **RAG** ("RAG retrieves; v2 pipeline extracts structured artefacts" — Jeff's memory note). The paper's §2.4 ("Document clustering and topic modelling") is the natural home for an explicit RAG contrast, but it currently treats LLM-mediated clustering only.

**Gap type:** MISSING (small).

**Recommended delta:** Add a sixth bullet on **retrieval-augmented generation**: "RAG systems retrieve passages by similarity to a query; the pipeline differs in producing extracted, classified, clustered structured records that survive review *outside* of a query context. RAG is a query-time tool; the pipeline produces a persistent analytical substrate. The two are complementary — the pipeline's outputs can be embedded for RAG, but RAG cannot produce the cluster, parent, or theme layers."

**Source citations:** Jeff's memory note `feedback_v2_vs_rag_framing.md` (referenced via CLAUDE.md memory index — not in reading file directly, so cite carefully or omit).

---

## §3 System overview

**Paper claims (current):** ASCII diagram of the two sub-pipelines (failure-mode s01–s11; glossary g01–g11) sharing a markdown rendering stage; lists outputs per sub-pipeline; names the CLI dispatcher.

**Source docs say (delta):**
- `arena_canonical/PIPELINE.md` (T1, line 1357) provides a **stage-by-stage diagram** of the canonical pipeline that more clearly separates the seed/sweep/singleton/residual sub-stages of clustering and the closure phase. The paper's diagram collapses these.
- The source's pipeline diagram explicitly names that the canonical pipeline runs *post-extraction grouping decoupled from extraction* (per `runs/README.md`'s 7-way comparison — `runs/2026-05-02-postextract-grouping-perdoc/notes.md`); the paper's overview alludes to this but does not foreground the architectural decision.

**Gap type:** UNDERSPECIFIED (architecture diagram is present but compressed).

**Recommended delta:** Either expand the ASCII diagram to show the seed → sweep → singleton → residual loop and the closure phase, or add a short paragraph noting that grouping is run *post-extraction* (decoupled), citing the 7-way runs comparison that demonstrated decoupled grouping wins on every axis (records preserved, event tightness, multi-record event size, cross-doc rate, singleton rate, cost).

**Source citations:** `pipeline/development/arena_canonical/PIPELINE.md`; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-postextract-grouping/notes.md`; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-postextract-grouping-perdoc/notes.md`.

---

## §4.0 Document ingestion

**Paper claims (current):** Describes BaseScraper contract, marker conversion, parallel workers, marker output preservation of tables / figures / footnotes / page boundaries.

**Source docs say (delta):** The ANAO N=100 demo (`anao_n100_demo/notes.md`) found that **flat markdown vs marker-rendered.md materially affects extraction quality** on ANAO: flat markdown collapses bullets into paragraphs (joining with `•`), partially loses heading hierarchy, and adds a wrapping header line. The 100-doc marker run produced 100% strict-parse success vs 67/97 strict-parse on flat markdown, and median 50 records/doc vs 47, with max 120 vs 70. The paper notes marker preserves tables but does not name this corpus-tested empirical finding.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** After "the downstream clustering and glossary stages depend on this", append: "The ANAO N=100 demonstration confirmed this empirically: flat markdown (bullets collapsed into paragraphs) produced 67/97 strict-parse success and 47 records/doc median; marker-rendered.md produced 100% strict-parse and 50 records/doc median, with maximum records/doc rising from 70 to 120. The extraction prompt explicitly treats each bullet as a distinct finding, so bullet preservation materially affects atomicity."

**Source citations:** `pipeline/development/anao_n100_demo/notes.md` Part 1.

---

## §4.1 s01 extract

**Paper claims (current):** One-shot per-document extraction; taxonomy-agnostic prompt; voice audit + narrative-vs-evidence audit; 92.2% legacy grounding.

**Source docs say (delta):**
- The **grave-prompt evolution campaign** (A→B→C→D→D'→E→E2→E3) is mentioned in the CLAUDE.md project layout but the paper says nothing about why the v1 grave prompt is canonical or how it was arrived at. The reading file's §4.5 and source-banner blocks for `2026-05-01-mechanism-coherent-grave/`, `occurrence-coherent-grave/`, `occurrence-merge-permissive/` document a 7-way comparison: v2 extraction with mechanism-coherent same-event criterion vs occurrence-coherent vs merge-permissive vs decoupled post-hoc grouping. The decisive empirical finding is that **decoupling grouping from extraction** (per-doc post-extract with chronological registry) wins on every axis. The paper does not capture this.
- The voice-audit numerics in the paper are right (6 trigrams absent, 96% novel n-grams in narrative are paraphrases) but the source has more: top-amplified bigrams "is identified" (40.9×), "trial found" (27.8×), "was identified" (23.1×), "this caused" (10.9×), "barrier to" (8.3×) (`INVESTIGATION_NOTES.md` Phase 2). These are concrete and cite-worthy.
- A **retraction worth reporting:** the source `INVESTIGATION_NOTES.md` Phase 3 retracted the "one-shot whole-document context bound into each atomic record" framing — only ~30% of records show meaningful cross-paragraph context drawing; ~68% are local-paragraph paraphrase. The paper §5.1 alludes to this with the doc_0121 worked example but does not name the retraction.

**Gap type:** MISSING (grave-prompt evolution; specific voice-audit numbers); STALE (cross-paragraph context-binding implication if paper relies on it).

**Recommended delta:** (a) Add a paragraph naming the prompt-evolution campaign: "The canonical v1 grave prompt is the survivor of a campaign comparing extraction-time grouping (mechanism-coherent / occurrence-coherent / merge-permissive variants) to decoupled post-extract grouping. The decisive finding (`canonical/narrative/runs/`) was that bundling extraction with grouping conflates two concerns: extraction yield changes with grouping policy. Decoupling them (v1 grave extraction + post-extract grouping) preserves orthogonality between the event-axis and the mechanism-axis substrates and produces the tightest event consolidation across a 7-way comparison." (b) Strengthen the voice-audit subsection by quoting the specific top-amplified bigrams. (c) In §5.1 explicitly disclose the cross-paragraph-binding retraction.

**Source citations:** `pipeline/development/arena_canonical/narrative/runs/README.md` (the 7-way synthesis); `pipeline/development/arena_canonical/narrative/runs/2026-05-02-postextract-grouping-perdoc/notes.md`; `pipeline/development/arena_closure/output/parent_ensemble/INVESTIGATION_NOTES.md` Phase 2 + Phase 3.

---

## §4.2 s02 group_events

**Paper claims (current):** Per-document event grouping; pair-decision instability ~32% at 3-doc scale, ~50% at 12-doc scale; replicate stability at corpus scale unmeasured.

**Source docs say (delta):**
- The **chronological accumulation** finding is missing from the paper. The 7-way comparison isolates *cross-doc chronological accumulation* (running event registry passed between docs in seed-doc-first order) as the consolidation lever; within-doc batching is incidental. One-shot all-records produces 63 events / 17% cross-doc; per-doc chronological with running registry produces 47 events / 26% cross-doc on identical input (`runs/2026-05-02-postextract-grouping-perdoc/notes.md`).
- The **`--exclude-fields lesson`** decision: dropping the lesson field from grouping input improved replicate Jaccard from 0.678 → 0.786 — a 16% stability gain. The mechanism: lessons are model-synthesised text that incorporates cross-context inference; paraphrase similarity in synthesised lesson text is itself noisy across reps. The paper does not mention this load-bearing input-design decision.
- The **replication campaign** quantifies the 12-doc stability picture: mean 471 events/rep (sd 54.5 = 12% relative noise); pair-set Jaccard 0.519 mean across reps; consensus event graph at ≥2/3 threshold yields 483 events / 1,581 confident pairs, reproducing 70% of v1 dedup's confident pairs while finding 1,330 new cross-doc pairs v1 missed. The paper gives ~50% pair-Jaccard but does not give the consensus-graph remediation.
- The **seed-doc heuristic** (synthesis-title docs first; then largest by tokens) is defined in `narrative/seed_doc_heuristic.md` and validated against REVS. The paper mentions seed docs in passing but does not define the heuristic.

**Gap type:** MISSING (chronological accumulation finding; lesson-field exclusion finding; consensus-graph remediation; seed-doc heuristic).

**Recommended delta:** Expand §4.2 substantially. Add four sub-points: (1) "Chronological accumulation across docs (running event registry, seed-doc first) is the consolidation lever; within-doc batching is incidental. Demonstrated by a 7-way comparison: one-shot all-records produces 63 events / 17% cross-doc, per-doc chronological produces 47 events / 26% cross-doc on the same 165-record input." (2) "The `lesson` field is excluded from grouping input by default. Replicate Jaccard improves 0.678→0.786 (16%) when lessons are dropped: lessons carry model-synthesised cross-context inference, and paraphrase similarity in synthesised text destabilises pair-grouping decisions." (3) "Replicate stability at scale was characterised on REVS (12 docs, 937 records, 3 reps): mean 471 events/rep (sd 54.5, 12% relative noise); pair-set Jaccard 0.519. The production output is the consensus event graph at ≥2/3 threshold (483 events; reproduces 70% of v1 dedup's confident pairs and finds 1,330 cross-doc pairs v1 missed)." (4) Define the seed-doc heuristic.

**Source citations:** `pipeline/development/arena_canonical/narrative/runs/2026-05-02-postextract-grouping-perdoc/notes.md`; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-postextract-grouping-oneshot/notes.md`; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-replication-campaign/notes.md`; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-fullrevs-production/notes.md`; `pipeline/development/arena_canonical/narrative/seed_doc_heuristic.md`.

---

## §4.3 s03 label_record_types

**Paper claims (current):** Six axes; Opus 4.6 + temp=0; Sonnet under-tags is_mechanism by ~10pp (8,000 records corpus-wide); verbose JSON wins on loose-boundary axes (92% / 14% / 28%); stability vs accuracy decoupling (Sonnet 0.980/0.806; Opus 0.969/0.963).

**Source docs say (delta):**
- The **record-type-pilot** ran *ten distinct experiments* (see TOC in `runs/2026-05-02-record-type-pilot/notes.md`). The paper covers EXP-1 (cross-tier), EXP-4 (output format), EXP-5 (hand-adjudication), EXP-9 (is_mechanism adjudication), and EXP-10 (cross-version Opus). It does not capture: EXP-2 (NT SETuP 173-record pilot — multi-label tagging validated, 68% records carry ≥2 type tags); EXP-3 (v3 prompt cross-tier sweep with three plausible production configs); EXP-7 (post-hoc analysis showing 0% of FC disagreements caused by is_specification flips — is_mechanism is the lever); EXP-8 (2,000-record at-scale validation: pool size matches by *coincidence* but composition diverges by ~28%, Jaccard 0.76).
- **Multi-label justification** (paper does not state explicitly): single-primary scheme would force coin flips on 68% of records (51% carry exactly 2 type tags; 16% carry 3; 1% carry 4).
- **Four-value valence (with `no_valence`)** vs v1's three-way: 31% no_valence in pilot data — collapses neutral to its proper rare meaning (2%). The paper does not name the four-value scheme as a methodological refinement.
- **Cross-tier disagreement is structurally interpretable** — Haiku reads "no_valence" where Sonnet/Opus read "negative" via the underlying-situation rule. This is calibration, not noise. The paper does not capture this.
- **Hand-adjudication numerics** in the paper (18/24, 75% under-tag direction) are correct but the source frames them with a corpus extrapolation: ~28% of FC records would differ between Sonnet and Opus tiers; pool size matching is coincidental.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** Add to §4.3: (a) State the multi-label-tagging validation: "Multi-label tagging is empirically necessary: 68% of records carry ≥2 type tags; a single-primary scheme would force coin flips on those records." (b) Name the four-value valence scheme: "valence is four-value (positive / negative / neutral / no_valence) — `no_valence` correctly identifies designed-mechanism descriptions and structural content; v1's three-way scheme was forcing these into `negative` or `neutral`." (c) Add the at-scale validation: "On a 2,000-record stratified validation, FC pool size between Sonnet and Opus matches within 0.6% by coincidence; composition diverges (Jaccard 0.76, ~28% of FC records would differ)." (d) Cite the structural interpretability of cross-tier disagreement as a calibration, not noise, finding.

**Source citations:** `pipeline/development/arena_canonical/narrative/runs/2026-05-02-record-type-pilot/notes.md` EXP-2, EXP-3, EXP-7, EXP-8; `pipeline/development/arena_canonical/narrative/runs/2026-05-02-record-type-pilot/analysis/adjudication_is_mechanism.md`; `analysis/adjudication_is_specification.md`.

---

## §4.4 s04 cluster_filter

**Paper claims (current):** Predicate `valence == 'negative' AND (is_occurrence OR is_mechanism)`; ARENA retains 25,479 records; legitimacy-filter argument from §9 of methodology lessons.

**Source docs say (delta):** `arena_clustering_v2/README.md` documents that the paper's predicate is the **clustering-input filter** (looser, no is_specification gate). The **production FC filter** (used for downstream consumers like the lessons compendium) is `valence == 'negative' AND (is_occurrence OR is_mechanism) AND is_specification == 'no'` and yields ~19,795 records. The paper conflates the two filters. The justification for using the looser filter for clustering specifically is empirical: records like "Forest waste 90% bark, 22% ash contamination" get excluded by spec gate but ARE useful as cluster seeds; cluster boundary detection separates pure-spec records naturally.

**Gap type:** UNDERSPECIFIED (paper states the filter but does not distinguish clustering input from production FC pool).

**Recommended delta:** After "valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes')", add: "This is the *clustering-input* predicate. A stricter *production FC* predicate adds `is_specification == 'no'` and yields ~19,795 records, used for downstream consumers (lessons compendium, FC pool exports). The looser clustering-input predicate is justified empirically: records like equipment-specification statements that include mechanism content are useful as cluster seeds; the cluster boundary then separates pure-spec from mechanism-bearing records naturally without an upstream gate."

**Source citations:** `pipeline/development/arena_clustering_v2/README.md` filter design section.

---

## §4.5 s05 cluster_seed

**Paper claims (current):** Stratified sample of 360 records (8 categories × 3 axis combos × 15); single Sonnet call; 45 seed clusters.

**Source docs say (delta):** Numerics correct. No major gap.

**Gap type:** Faithful.

---

## §4.6 s06 cluster_sweep

**Paper claims (current):** 200-record batches; Pass 1 + Pass 2 in single response; ≥3-record threshold; pending singletons accumulate; 2x2 falsification (A=140 / B=107 / C=156 / D=176 records classified at iter 110); procurement-probity invariant.

**Source docs say (delta):**
- The 2x2 result in the paper is correct but the **trajectory** is missing: at iter 30 (catalogue 333), at iter 70 (catalogue 571), at iter 110 (catalogue 734). The growing D-only-classified count (16 / 24 / 36) shows the defensive prompt suppresses *more* legitimate classifications as the catalogue grows.
- **The sweep ran 128 iterations**; final state is 797 clusters / 17,164 classified (67.4%) / 6,034 pending singletons (23.7%). The paper says "the sweep is the central clustering stage" but does not give the trajectory or final state — useful for sizing the iteration count.
- The "44% plateau" was a transient feature, not equilibrium. The paper does not document this lesson.
- **Three-component precision envelope** (`arena_clustering_v2/notes.md` §6.8): LLM nondeterminism floor ~3-5%; batch-composition sensitivity ~3-7%; cluster-boundary fuzziness ~10-22%. These compound. "Identical-input replication is ~85-90%; identical-input-but-different-batch-composition is ~80-85%; among records both regimes classify, agreement on which cluster is ~75-90%." The paper makes no quantitative precision claim at this stage — this is a substantive gap.
- **Haiku 4.5 vs Sonnet 4.6 A/B**: Haiku force-fits on vocabulary (Sonnet right ~17/20 of disagreements; Haiku right ~2-3/20). Cost differential not affordable. The paper does not name this finding.

**Gap type:** UNDERSPECIFIED (precision envelope and Haiku force-fit finding both missing).

**Recommended delta:** (a) Add the iteration trajectory and final state. (b) Add a precision-envelope paragraph: "The sweep's per-record precision is the compound of three measurable terms: LLM nondeterminism floor (~3-5%), batch-composition sensitivity (~3-7%), and cluster-boundary fuzziness (~10-22%). Identical-input replication is ~85-90%; identical-input-but-different-batch is ~80-85%; among records both regimes classify, agreement on cluster choice is ~75-90%. Closure-phase merge operations can directly reduce the third term; the first two are model and method properties." (c) Add a one-line note on Haiku unsuitability: "Haiku 4.5 was tested as the per-record classifier (cost reduction ~75%) but force-fits on vocabulary; on a 60-disagreement hand-inspection Sonnet was correct on ~17/20 and Haiku on ~2-3/20. The cost differential is real but the precision loss is unaffordable for a methodology-paper artefact."

**Source citations:** `pipeline/development/arena_clustering_v2/notes.md` §3 (sweep trajectory), §5 (Haiku A/B), §6 (2x2), §6.8 (precision envelope).

---

## §4.7 s07 cluster_singleton

**Paper claims (current):** Pending singletons revisited against matured catalogue using Arm-D semantics (batched + neutral).

**Source docs say (delta):** The paper is faithful. The reclassify pass cost was ~$6 (vs $120 per-record-cached estimate), validating the batched approach.

**Gap type:** Faithful.

---

## §4.8 s08 cluster_residual

**Paper claims (current):** Residual orphans presented as a final cohort to one Pass 2 call; convergence at 1,141 clusters.

**Source docs say (delta):** Faithful. The source confirms the convergence count.

**Gap type:** Faithful.

---

## §4.9 s09 parent_derive

**Paper claims (current):** Opus 4.7; mechanism-class focus; emergent count; tightness over breadth; honest unfit reporting; 59-rep ensemble producing canonical 70-parent + 16-parent boundary extension = 86-parent canonical taxonomy.

**Source docs say (delta):**
- The paper does not explain **why an ensemble was needed** or what was learned from the ensemble process. The source `EXPERIMENTAL_METHODOLOGY.md` is built around **four publishable findings** that the paper omits or compresses:
  1. **Single-pass taxonomy derivations are arbitrary.** sd 13.6 across the original 50-rep ensemble; parent counts ranged 60–110.
  2. **Naming examples in taxonomy prompts is a 50pp priming hazard.** The soft-balance A/B/clean experiment isolates the effect to the example phrasings, not the constraint itself. Equity drops 75% → 25% when example names are removed.
  3. **Deliberation-rich prompts halve variance.** sd 13.6 → 7.24 by surfacing borderline split/merge decisions in a structured `deliberated_mechanisms` output field.
  4. **Threshold defensibility requires reasoning grounded in the canonical set, not the prior.** Comparing v2 to v1 was rejected as a threshold defence because it propagates v1's arbitrariness; clean LLM judgement on the 126 canonical classes converged on ≥70% rep agreement as the natural cut, validated by two independent ensemble passes.
- The **coherence test** finding (`INVESTIGATION_NOTES.md` Phase 6) — only 28% of canonical classes are atomic; 100% of core classes (≥90% rep agreement) have at least one run that subdivided them — is a substantive retraction of the "126 canonical mechanism classes" framing and is not in the paper.
- **Atomic sub-class decomposition** (Phase 7): produces 369 atomic vocabulary; the substrate is best understood as a stack of coarsenings (1,141 clusters → 369 atomic sub-classes → 126 canonical → 83 parents/run → 12-16 themes), each with its own reproducibility characteristics. Not in the paper.
- The paper says "the canonical 70-parent set + 16-parent boundary extension" but the source describes the build as 43 core + 27 promoted high-tier (= 70) then + 16 boundary-promoted (= 86). The paper's count is right but the provenance per parent (core / high / boundary, n_reps_min) is not surfaced.
- The paper's theme count is **16** (s11 paragraph); the source's `INVESTIGATION_NOTES.md` Phase 7 shows **12** themes when grouping is done from the deliberation-rich ensemble's 70-parent layer. The actual production theme count from `EXPERIMENTAL_METHODOLOGY.md` Phase 9 is **16 themes** on the 86-parent set. CLAUDE.md memory note says "12 themes". This may be inconsistent across the source documents themselves; **flag for Jeff to confirm the canonical theme count** before paper publication.

**Gap type:** MISSING (priming-hazard finding; deliberation-rich variance reduction; coherence test; atomic sub-class decomposition); UNDERSPECIFIED (provenance per parent).

**Recommended delta:** Substantially expand §4.9 into multiple sub-paragraphs:
- "Single-pass parent derivation is arbitrary. The original 50-rep ensemble produced parent counts ranging 60–110 (sd 13.6) on identical input; any one rep is one draw from a wide distribution."
- "Naming candidate categories as illustrative examples in taxonomy prompts is a 50-percentage-point priming hazard. The soft-balance A/B/clean experiment isolated the effect to the example phrasings, not the constraint itself: when prompted to ensure equity coverage with named examples, equity-related parents appeared in 75% of reps; without the named examples, 25%. Production parent-derivation prompts must avoid named example categories."
- "A deliberation-rich prompt (PM-purpose framing + no named examples + a `deliberated_mechanisms` structured output field surfacing every borderline split/merge decision) halved per-rep variance: sd 13.6 → 7.24."
- "Threshold defensibility requires reasoning grounded in the canonical set, not the prior. Defending a threshold by comparison to v1 propagates v1's single-draw arbitrariness; the clean approach is independent LLM judgement on the 126 canonical classes plus two validation ensembles (threshold-judgement and category-selection), all converging on ≥70% rep agreement as the natural inclusion cut."
- "Disclose the coherence-test retraction: 91 of 126 canonical classes (72%) have at least one run that subdivided them; 100% of core classes (≥90% rep agreement) are non-atomic. The 126 'canonical classes' is a granularity-blurred union of run-level boundary choices, not a coherent atomic taxonomy."
- "Per-parent provenance: each parent in the canonical 86-parent set carries source tier (core / high / boundary), n_reps_min, and source class IDs. This provenance is required to defend the inclusion against 'this is just one model's choice' challenges."

**Source citations:** `pipeline/development/arena_closure/EXPERIMENTAL_METHODOLOGY.md`; `pipeline/development/arena_closure/output/parent_ensemble/INVESTIGATION_NOTES.md` Phases 5–7; `pipeline/development/arena_closure/output/parent_ensemble/abstraction_ratings.md`; `pipeline/development/arena_closure/output/parent_ensemble/coherence_test.md`; `pipeline/development/arena_closure/output/parent_ensemble/atomic_subclass_decomposition.md`; `pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/SESSION_WRITEUP.md`.

---

## §4.10 s10 parent_assign

**Paper claims (current):** Opus 4.7; one-of-86 (or 'none'); blinded validation in three layers (74.7% clean fits / 0 high↔low; 73.6% always-in-top-2; 64.8% unanimous primary; 80 strong reassignment candidates; 94 unanimous disagreements; cluster signature drift gap).

**Source docs say (delta):** The paper covers this section the most faithfully of any. Minor refinements:
- The paper says "74.7% clean fits" — verify this is the right interpretation. The source's `blinded_validation/README.md` reports: 45/91 high-high (clean), 23/91 medium→high (clean — selection ambiguity), 14/91 medium-medium (genuine criterion-fit medium), 5/91 medium→low (flag for review), 3/91 high→medium (flag), 1/91 low-low. The "68/91 = 74.7%" tally is `45 + 23 = 68` (high or medium-upgraded-to-high). The paper's framing is correct but the *what counts as clean* deserves a sentence.
- The 95.8% high-high agreement number cited in the paper is actually 45/48 = **93.8%** in the source (`blinded_validation/README.md`). **The paper has the wrong number.**
- The pilot-ensemble cost numbers in the paper ($0.40 + $3.60 + ~$22) match the source. The 91-cluster sample's 5 strong reassignment candidates (c1133, c1276, c1282, c1447, c1479) and the p25↔p18 unanimous reassignment cluster (c1282 = 10/10 unanimous) are not named in the paper but would strengthen it.
- The **two diagnostic shapes** finding (single-boundary p25↔p18 with 75% concentration on one alternative; structural fragmentation p77 spreading across 8 alternatives) is a **methodology contribution** in its own right per the source: "boundary-mapping doesn't just say 'where are the boundaries fuzzy' — it distinguishes 'this line should be redrawn' from 'this parent should be split'." The paper does not name this contribution.

**Gap type:** CONTRADICTED (95.8% should be 93.8%); UNDERSPECIFIED (two-shapes contribution; named cases).

**Recommended delta:** (a) **Correct the 95.8% to 93.8%** (45/48 = 93.75%, rounds to 93.8%). (b) Add the two-shapes paragraph: "Boundary-mapping ensembles produce two distinguishable diagnostic shapes, distinguished by *concentration of disagreements at one alternative parent*. p25↔p18 (Feedstock variability ↔ Material limits) shows the **single-boundary** shape — 75% of p25's disagreements concentrate on p18, indicating a criterion that should be sharpened or merged. p77 (Customer recruitment) shows the **fragmentation** shape — disagreements spread across 8 distinct alternatives with 18% top-1 concentration, indicating a parent that should be split into more specific neighbours. The same disagreement data produces qualitatively different diagnoses; this is a methodological contribution beyond the headline ensemble agreement numbers." (c) Optionally name c1282 as a worked example of a 10/10 unanimous reassignment.

**Source citations:** `pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/README.md`; `PILOT_boundary_mapping_2026-05-08.md`; `PILOT_ENSEMBLE_2026-05-08.md`; `full_corpus_ensemble_v3/full_summary.md`.

---

## §4.11 s11 theme_audit

**Paper claims (current):** Two-task call (audit + theme grouping); 86 keep / 16 themes / 0 unthemed / 4 candidate missing mechanism classes for ARENA.

**Source docs say (delta):**
- The 16 themes are listed by name and parent membership in `full_corpus_ensemble_v3/adjacency_heatmap_themes.md`. The paper does not enumerate the themes; for a methodology paper this is fine, but a one-line summary of the theme families (information & evaluation / physical & resource limits / asset & process engineering / spatial & temporal mismatch / power-system & grid / control IT interfaces / systemic fragility / capital & economics / market design / supply chain & lifecycle / regulation & policy / commercial instruments / coordination & social / workforce & execution) would help readers see the breadth.
- The **`parent_gap_audit`** (`output/parent_gap_audit.md`) compared the v1 71-parent layer against 126 canonical ensemble classes and identified high-priority gaps: schedule cascade (88% ensemble agreement), regulatory ambiguity / fragmentation (82%), technology readiness gap (76%), communications and connectivity failures (72%). These are the four candidate missing classes the paper alludes to — naming them would strengthen the section.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** (a) List the 16 theme names in a single comma-separated paragraph. (b) Name the four candidate missing classes from the parent_gap_audit: schedule cascade and dependency delays (88% ensemble agreement); regulatory ambiguity, fragmentation, and jurisdictional conflict (82%); technology readiness and maturity gap (76%); communications and connectivity failures (72%).

**Source citations:** `pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/full_corpus_ensemble_v3/adjacency_heatmap_themes.md`; `pipeline/development/arena_closure/output/parent_gap_audit.md`.

---

## §4.12 Glossary sub-pipeline (g01–g11)

**Paper claims (current):** Eleven stages described concisely; 760 entries / 100 noise / 11 categories on ARENA; 590 entries / 10 noise / 9 categories / 24 sub-categories on ANAO; 69 shared terms with ~30% polysemous false friends.

**Source docs say (delta):**
- The **session writeup** (`arena_glossary/SESSION_WRITEUP_2026-05-05.md`) reports total spend ~$2.04 across all four model passes (Pass 1 acronyms $1.00, Pass 2 tail/titlecase/reground $0.65, subcategory propose+apply $0.39). The paper does not give a glossary cost — useful for cross-corpus deployment cost estimates.
- **The `reground` mode is the methodologically-distinctive piece** per the source: greps the corpus for narrative snippets containing the surface, feeds 2-3 to the model alongside Pass 1's first attempt, resolves uncertainty by giving the model corpus context. Resolved REVS / MATCH / EPWA which a priors-only pass couldn't have placed. The paper mentions reground but does not flag it as the methodologically-distinctive mode.
- The **distinctiveness ratio derivation** (Pass 6 in the source) is robustly described in the paper §5.5 but the source has cite-worthy worked examples: DERMS at 65% in DER projects (7.94× corpus base); HVDC at 65% in System security & reliability (16.3×); these are the kind of fingerprint examples that ground the abstract metric.
- The **median-mention-year vs corpus-median** (vs naive first-third / last-third) is a deliberate calibration choice in the source: GFM shows as rising (median 2023), LCOE as falling (median 2016 vs 2019 baseline), TRL as rising. The paper §4.12 does not mention the year-trajectory metric calibration.
- The **inverse signatures** (`g11`) yield: 489 project signatures from 503 projects; 14 projects had <10 mentions and yield genuinely thin signatures (correctly excluded). Distribution: 44 thin / 119 medium / 199 rich / 127 capped at 25. Paper says "489 project vocabulary signatures" but does not give the distribution.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** (a) Add total glossary cost (~$2 per corpus). (b) Flag `reground` as the methodologically-distinctive mode: "The `reground` mode is the methodologically-distinctive sub-stage: for each Pass-1-uncertain term, the script greps the corpus for narrative snippets containing the surface and feeds 2-3 to the model alongside Pass 1's first attempt. Sonnet either confirms the original definition or rewrites with corpus context, resolving terms a priors-only pass cannot place (e.g. REVS as the V2G trial, MATCH as the UNSW DER study)." (c) Add fingerprint worked examples (DERMS, HVDC). (d) Note the year-trajectory calibration. (e) Add the project-signatures distribution.

**Source citations:** `pipeline/development/arena_glossary/SESSION_WRITEUP_2026-05-05.md`.

---

## §5.1 Atomic-claim substrate as foundational artefact

**Paper claims (current):** Records-vs-paragraph 1:2 ratio; doc_0121 8-record table example; substrate is voice-affected but not concept-injected.

**Source docs say (delta):**
- The **doc_0121 worked example** (`INVESTIGATION_NOTES.md` Phase 4): 31 substantive paragraphs / 68 atomic records (ratio 2.19×). The single 1,652-char paragraph #19 (a 6-row table) was decomposed into 8 records (one per row + meta-record + content-adjacent record). The paper has this right.
- The **doc_0031 worked example** (selection): ARENA Vehicle-to-Grid Insights Final Report. 123 substantive paragraphs / 60 records / 22 paragraphs (18%) skipped. Sampled skipped paragraphs are front-matter, copyright, methodology bridge, tutorial exposition — none carry mechanism-bearing content. The paper does not include this; it complements doc_0121 by demonstrating the *selection* dimension of atomicity (vs the *segmentation* dimension).
- The **174-document corpus statistic**: 174 documents have ≥30 substantive paragraphs *and* produce more records than paragraphs. Multi-claim-per-paragraph is common, not rare.
- The **four-layer atomicity-via-inference framing** (Jeff's resolved methodology position from `feedback_substrate_defensibility_unified.md` per CLAUDE.md memory): atomicity requires inference at four layers (selection, segmentation, self-containment, local synthesis); voice is rephrasing not invention. The paper alludes to this in §5.1 but does not name the four layers.
- **The retraction worth disclosing here** (per `INVESTIGATION_NOTES.md` Phase 3): the "one-shot whole-document context bound into each atomic record" framing was overstated. Only ~30% of records show meaningful cross-paragraph context drawing; ~68% are local-paragraph paraphrase. The substrate's value comes from atomicity-through-selection-and-segmentation, not from cross-paragraph context binding. The paper should disclose this retraction explicitly.

**Gap type:** MISSING (doc_0031 selection example; 174-document statistic; retraction).

**Recommended delta:** (a) Add a paragraph after the doc_0121 example: "A complementary worked example demonstrates the *selection* dimension. ARENA's V2G Insights Final Report (doc_0031) has 123 substantive paragraphs and produces 60 records — 22 paragraphs (18%) are skipped. The skipped paragraphs are front-matter, copyright, methodology bridge, and tutorial exposition; none carry mechanism-bearing content. Atomicity therefore operates at four layers — selection (filtering claim content from scaffolding), segmentation (identifying atomic-claim boundaries within paragraphs), self-containment (each record carries enough context to be read alone), and local synthesis (the lesson field articulates implications)." (b) Add the corpus statistic: "174 documents in ARENA have ≥30 substantive paragraphs *and* produce more records than paragraphs; multi-claim-per-paragraph extraction is common, not rare." (c) Disclose the cross-paragraph retraction: "An earlier framing claimed that one-shot extraction binds whole-document context into each atomic record. Empirical audit (50-record stratified sample) found only ~30% of records show meaningful cross-paragraph context drawing; ~68% are local-paragraph paraphrase. The substrate's categorical advantage over paragraph-chunked retrieval operates at selection and segmentation, not at cross-paragraph context binding."

**Source citations:** `pipeline/development/arena_closure/output/parent_ensemble/INVESTIGATION_NOTES.md` Phases 3, 4.

---

## §5.2 Extraction-first taxonomy posture

**Paper claims (current):** Hybrid sample-informed-then-frozen; not bottom-up vs top-down; the honest distinction is *when* taxonomy is defined relative to extraction.

**Source docs say (delta):** The paper is faithful to Jeff's framing in `feedback_taxonomy_framing.md` (memory). No major source-content gap.

**Gap type:** Faithful.

---

## §5.3 The legitimacy filter — recurrence threshold as downstream calibration

**Paper claims (current):** ≥3-record threshold absorbs upstream filter false positives into singletons; relieves precision pressure on upstream filter.

**Source docs say (delta):** Faithful to `methodology_lessons.md` §9 and Jeff's memory note. No gap.

**Gap type:** Faithful.

---

## §5.4 Engine versus configuration

**Paper claims (current):** Engine includes ingestion, extraction, 11-stage failure-mode pipeline, 11-stage glossary; per-corpus config is scrape.py + domain.yaml + prompt overrides + stoplist; the test is "if adding a new corpus requires modifying any file under `pipeline/`, that's a generalisation failure."

**Source docs say (delta):** Faithful, but the **ANAO N=100 demo** is the empirical proof: same v1 grave prompt, same group_events prompt, same engine code; only `domains/anao/domain.yaml` and `domains/anao/scrape.py` differ. The paper §7 covers this but §5.4 could cite it.

**Gap type:** Faithful (§5.4 itself); UNDERSPECIFIED (cross-reference to §7 ANAO demo would strengthen).

**Recommended delta:** Add at end of §5.4: "The empirical proof of the engine-config separation is the ANAO N=100 demonstration (§7). The same canonical extraction prompt and the same group_events prompt produced 4,765 atomic records and 4,483 events from 100 ANAO performance audits with no engine modification; only `domain.yaml` and `scrape.py` differ between ARENA and ANAO."

**Source citations:** `pipeline/development/anao_n100_demo/notes.md`.

---

## §5.5 Distinctiveness over raw frequency

**Paper claims (current):** Observed-share / base-share ratio; corpus-agnostic; TF-IDF analogy.

**Source docs say (delta):** Faithful. The DERMS / HVDC examples from §4.12 above could ground this section but are stylistic not substantive.

**Gap type:** Faithful.

---

## §5.6 Hybrid GPU-NLP plus LLM architecture

**Paper claims (current):** Glossary alternates deterministic GPU-NLP and LLM passes; allocates work to the right tool; same pattern at coarser granularity in failure-mode pipeline.

**Source docs say (delta):** Faithful.

**Gap type:** Faithful.

---

## §5.7 Multi-pass LLM strategy with targeted follow-up modes

**Paper claims (current):** g04+g05 pattern: first pass on highest-coverage candidates plus targeted follow-ups (tail recovery, titlecase, reground).

**Source docs say (delta):** Faithful. Minor: the source `SESSION_WRITEUP_2026-05-05.md` reports that compact JSON keys saved ~40% output tokens — a quantitative grounding for the "targeted follow-up" cost rationale. Worth a one-line addition.

**Gap type:** UNDERSPECIFIED (small).

**Recommended delta:** Add: "Compact JSON output schemas (single-letter keys) saved ~40% output tokens vs verbose schemas at the same content density in glossary follow-up passes; verbose schemas were retained for the loose-boundary record-type tagging stage where output schema is a deliberation surface (§4.3)."

**Source citations:** `pipeline/development/arena_glossary/SESSION_WRITEUP_2026-05-05.md`.

---

## §5.8 Layer-of-inference dependency and re-synthesis

**Paper claims (current):** Each layer should be synthesised after its membership stabilises; pipeline does this at parent and theme but not cluster signature; cluster signature drift is a documented gap with $170 batched fix.

**Source docs say (delta):** Faithful. The source emphasises the **drift effect on long-tail boundary adjacencies (≤30 events) but robustness of top edges (≥40 events)** — the paper captures this but could quantify more sharply: "The fix is a one-shot re-synthesis pass; ~$170 batched per re-derive plus ~$25 re-ensemble." Source agrees.

**Gap type:** Faithful.

---

## §6.1 What has been validated

**Paper claims (current):** Substrate voice/grounding; six-axis stability vs accuracy; one-shot vs chunked; cluster→parent quality; glossary engine reproducibility; cross-domain demonstration on ANAO; cross-corpus polysemy.

**Source docs say (delta):**
- The **cross-project diversity validation** (`arena_clustering_v2/notes.md` §4) — workhorse clusters mean 17.8 projects per cluster, mean 6.9 ARENA categories per cluster — is named in CLAUDE.md but **not in the paper's §6.1**. This is a load-bearing validation: it directly addresses the project-vocabulary-confound concern that motivated v2 over v1's 36% single-project-bound clusters. It belongs in §6.1.
- The **within-tech distinctness probe** (`arena_clustering_v2/notes.md` §10.1 Step 6): top-50 battery-storage-dominated clusters → 0 Opus-proposed merges. Confirms cluster mechanism-level distinction holds within tech, not just across tech. Not in paper.
- The **causal-chain validation** (`EXPERIMENTAL_METHODOLOGY.md` Phase 3, script 25-26): 88% of v2 mechanism clusters form valid causal chains (X→Y→Z structure rather than mere co-occurrence). Corpus-level evidence that the cluster layer captures genuine mechanism structure, not text neighbourhood. Not in paper.
- The **event-coherence audit** (script 27): 98% event-coherence on multi-parent stratum — when a cluster's records spanned multiple parents, the parents really did describe distinct mechanisms. Not in paper.

**Gap type:** MISSING (four substantive validations absent from the validation summary).

**Recommended delta:** Add four bullets to §6.1:
- "**Cross-project diversity.** On 15 stratified-sample workhorse clusters (size 21–50), mean 17.8 unique projects per cluster and mean 6.9 unique ARENA categories per cluster. The same mechanism appears in solar PV, hydrogen electrolyser, biomass scale-up, and storage projects — the cross-project pattern that v1's 36% single-project-bound clusters could not surface."
- "**Within-tech distinctness.** A top-50 battery-storage-dominated cluster subset (size ≥10, battery_share 42–95%) was passed to Opus 4.7 with the same merge-finding question as the catalogue-wide pass: zero merges proposed. The catalogue's mechanism-level distinctions hold within a single tech category, not just across categories."
- "**Causal-chain coherence.** 88% of v2 mechanism clusters form valid causal chains (X→Y→Z structure) rather than mere co-occurrence patterns; corpus-level evidence that the cluster layer captures mechanism structure rather than text neighbourhood."
- "**Event-coherence on multi-parent records.** 98% of multi-parent stratum events have parent assignments that describe genuinely distinct mechanisms; the few violations are ambiguous events. Confirms parents are not over-fit to artificially separate truly-related content."

**Source citations:** `pipeline/development/arena_clustering_v2/notes.md` §4, §10.1 Step 6; `pipeline/development/arena_closure/EXPERIMENTAL_METHODOLOGY.md` Phase 3 (scripts 23, 25-27); `pipeline/development/arena_closure/output/use_case_demos/causal_chain_full.md`; `event_coherence_audit.md`.

---

## §6.2 What has not been validated

**Paper claims (current):** Formal claim-level fidelity; replicate stability of grouping and clustering at full corpus; cluster coherence audit on canonical 1,141; parent-derivation across multiple ensemble runs at corpus scale; reassignment candidate audit; cluster signature re-synthesis; expert ground truth.

**Source docs say (delta):** Mostly faithful. Two refinements:
- The **traceable-uncertainty placeholder list** from `methodology_gaps.md` §1 names specific uncalibrated filters: Pass 3 realisation, Pass 2 parent assignment, Stage F cluster membership. ~300 hand-tags would close this. The paper alludes to this but does not enumerate the three uncalibrated stages.
- The **cluster-layer ensemble cost correction** ($360-550 batched, NOT $1500-5000) is a load-bearing economic correction in `PILOT_ENSEMBLE_2026-05-08.md` and Jeff's memory note. The paper does not include this correction; if §6.2 says "replicate stability at corpus scale unmeasured" without naming the correct cost, readers may underestimate the affordability of the missing validation.

**Gap type:** UNDERSPECIFIED.

**Recommended delta:** (a) In the "filter-chain calibration" item, enumerate the three uncalibrated stages by name (Pass 3 realisation; Pass 2 parent assignment; Stage F cluster membership). (b) In the "replicate stability of clustering" item, add the corrected cost: "A 10-rep full-clustering-stage ensemble at full corpus is ~$360–550 batched (not $1,500–5,000 as previously documented). The blocker is structural — cluster IDs aren't stable across reps — and the fix is record-pair co-occurrence analysis across reps to derive consensus partitions; this is a methodology design problem, not a budget problem."

**Source citations:** `pipeline/development/arena_canonical/narrative/methodology_gaps.md` §1, §2; `pipeline/development/arena_closure/output/parent_derivation_clean_ensemble/blinded_validation/PILOT_ENSEMBLE_2026-05-08.md` Cost economics section.

---

## §7 Demonstration

**Paper claims (current):** ARENA: 90,192 records / 1,141 clusters / 86 parents / 16 themes / 760-term glossary / 489 project vocabularies. ANAO: 1,454 markdown / 590-term glossary / N=100 clustering pilot.

**Source docs say (delta):**
- The **ANAO N=100 demo's structural finding** is missing from the paper's §7 description: "Per-doc event derivation's effectiveness is bounded by extraction's atomicity choices. The aspect-merging logic transfers across corpora; the corpus-level dedup ratio depends on whether extraction emits records the grouper can recognise as aspects of one occurrence. ANAO's audit-doc extraction emits records sliced at sub-issue grain — different years, different sub-aspects, different audit-finding angles — that the grouper can't merge without sacrificing precision." (`anao_n100_demo/notes.md`). This is a structural cross-corpus finding, not just a count. The N=100 yield was 4,765 atomic records → 4,483 events (dedup 1.03×).
- The **ANAO ↔ ARENA parent overlap audit** (`anao_n100_arena_overlap.md`) is absent from §7 and is the single best cross-corpus convergent-validity finding in the source: 9 mechanisms map cleanly (data quality, sample bias, IT systems, cybersecurity, workforce capacity, multi-party coordination, policy uncertainty, equity exclusion, contract specification); 19 ANAO-only (Westminster-government accountability machinery — upward misrepresentation, transparency compliance, statutory authority alignment, machinery-of-government transitions, deferral-normalisation, etc.); 17 ARENA-only (physical-engineering, power-system, project-finance). The two taxonomies are substantially independent rather than nested, which is itself a finding.
- The **ANAO 50-parent set** (`anao_n100_parents.md`) — derived from 207 mechanism clusters in a single Opus 4.7 call — is a concrete artefact for the paper to cite as evidence that the engine produces a coherent parent layer on a different corpus.
- The **c042 cluster report** (`cluster_reports/c042_report.md`) is the single best worked example of the v2 substrate's analytical output: cross-tech (electrochemistry, perovskite PV, supercritical CO₂, hydrogen, materials), cross-time (2010–2026 project years), cross-provider (Fortescue, ACAP, ASTRI, SunDrive, Cavendish, Cooper Basin, etc.), 150 records / 56 projects / 8 ARENA categories. Per Jeff's memory note `project_c042_synthesis_validation.md`: "first end-to-end Opus 4.7 cluster report (cross-tech/time/provider) visibly delivered the v2 substrate's design promise; lead the methodology paper with c042 as worked example." The paper §7 does not mention c042 or any worked-example output.
- The **other worked-example T3 artefacts** in the reading file (c016, c1074, p18 parent report, neoen_big_battery project report, h2biomass refclass memo, foak_rag_vs_v2 demo, parent_archetypes_register) are evidence-grade demonstrations the paper §7 could cite. The `foak_rag_vs_v2.md` demo is particularly useful for the §2 RAG contrast.

**Gap type:** MISSING (cross-corpus parent overlap audit; ANAO 50-parent set; c042 worked example; ANAO atomicity-bound finding).

**Recommended delta:** Substantially expand §7. Specifically:
- (a) Add a paragraph in the ANAO subsection: "Per-doc event derivation on the ANAO N=100 sample yielded 4,765 atomic records → 4,483 events (dedup 1.03× vs ARENA's 1.16×). Spot-checking 5 random multi-record events shows ~80% accuracy on aspect-merging. The low dedup ratio is a structural finding about ANAO, not a prompt-transfer failure: ANAO performance audits use a 'summary-with-restatement-and-detail-shift' pattern where each restatement adds new information rather than just rephrasing — different years, different sub-organisations, different finding angles — that the grouper correctly does not merge. ARENA's project-doc extraction emits aspect-distinct records (cause / mechanism / intervention / outcome / lesson) under one occurrence, which the grouper recognises and consolidates."
- (b) Add the parent-overlap finding: "An ANAO 50-parent set was derived from 207 mechanism clusters in a single Opus 4.7 call ($0.41). Comparing to the ARENA 86-parent set: 9 mechanisms map cleanly (data quality, sample bias, IT system inadequacy, cybersecurity, workforce capacity scarcity, multi-party coordination, policy uncertainty, equity exclusion, contract specification defects); 19 are ANAO-only (Westminster-government accountability machinery — upward misrepresentation, statutory authority alignment, machinery-of-government transitions, deferral-normalising non-delivery); 17 are ARENA-only (physical-engineering, power-system dynamics, project-finance, lock-in/supply-chain). The two taxonomies are substantially independent rather than nested — ANAO is a specialised vocabulary for accountability and administrative compliance, not a programme-failure superset with ARENA's clean-energy specifics carved off."
- (c) Add a worked-example subsection naming c042: "**c042 — Electrode Material Degradation From Chemical Incompatibility.** A representative cluster spanning 150 records, 56 projects, and 8 ARENA categories, with project years 2010–2024 and publish dates through early 2026. Records are integrated across green hydrogen, direct electrochemical reduction of iron, perovskite and tandem PV, concentrated solar thermal, advanced batteries, biofuels, and hydrogen blending — concretely demonstrating that the v2 substrate aggregates mechanism evidence across tech / time / provider boundaries that no single project's report would expose."

**Source citations:** `pipeline/development/anao_n100_demo/notes.md`; `pipeline/development/anao_n100_demo/output/anao_n100_arena_overlap.md`; `pipeline/development/anao_n100_demo/output/anao_n100_parents.md`; `pipeline/development/arena_closure/output/cluster_reports/c042_report.md`.

---

## §8 Limitations

**Paper claims (current):** Unvalidated analytical outputs; LLM dependence; mechanism inference is shallow; concentration-by-counterparty artefacts; cross-domain validation partial; cluster signature drift; single-rep production at corpus scale; output schema design as free parameter; polysemy detected but not resolved.

**Source docs say (delta):**
- The paper's "single-rep production at corpus scale" item could be sharpened with the §16 source numerics: pair-set Jaccard 0.519 at 12-doc REVS, mean 471 events/rep (sd 54.5 = 12% relative noise). The consensus-graph mitigation (≥2/3 threshold) is a partial answer.
- The paper does not name the **lesson-field model-invention finding** (`methodology_notes.md` §6.5): lessons mix grounded synthesis (e.g. "price suppression" generalising a documented price-reduction claim) with pure model invention (e.g. "capacity market or contract-for-difference mechanisms" — zero hits in source markdown for any of those terms). 7 of 9 cause-and-effect framing terms in lessons returned zero hits in source. This affects how downstream analyses should treat lesson-field content. The paper §4.1 mentions the substrate is voice-affected but does not call out the lesson-field-specific issue.
- The paper's "mechanism-level causal inference is shallow" is right but understated. The source's **locked epistemic position** (`methodology_notes.md` §7) is a stronger framing: "We trust document authors to surface causal relationships they consider important. If a cause-effect relationship was not stated explicitly in source, we do not presume to assert it ourselves. Inferring causation across atomic records is an analytical layer that does not generalise reliably across a whole document corpus and is therefore not part of the pipeline." This is a methodologically-stronger position than "shallow causal inference"; the paper should adopt it.

**Gap type:** UNDERSPECIFIED (lesson-field invention; epistemic-position framing).

**Recommended delta:** (a) Add a limitation: "**Lesson-field content carries two epistemic layers.** The extraction prompt's `lesson` field is reserved for synthesis (the transferable implication). On a hand-traced subset (Middleback Ranges PHES section 10.3), 7 of 9 cause-and-effect framing terms in lessons returned zero hits in source markdown; mitigation suggestions like 'capacity market' or 'contract-for-difference' are model-prior vocabulary, not document-grounded. The lesson field mixes grounded cross-record synthesis (e.g. 'price suppression' generalising a measured price-reduction claim) with pure model invention. Mitigation language that does not match content in source documents should be treated as suggested rather than evidenced." (b) Adopt the locked epistemic position explicitly: "The pipeline extracts cause-effect relationships that document authors chose to make explicit through grammatical signalling ('because', 'due to', 'as a result of'). It does not infer causal relationships from co-occurring observations across records. This restricts the failure-mode taxonomy to author-asserted causation and produces a smaller but more evidentiary-grounded dataset." (c) Sharpen the single-rep limitation with the 0.519 Jaccard / 12% relative noise figure.

**Source citations:** `pipeline/development/arena_canonical/narrative/methodology_notes.md` §6.5, §7, §8.

---

## §9 Future work

**Paper claims (current):** Formal validation; cluster signature re-synthesis ($170); replicate-stability characterisation; full-corpus parent-assignment audit; cluster-layer boundary mapping ($10-20 batched); cross-corpus convergent-validity testing; filter-chain calibration; methodological hardening of relationship classifications; APH/PC/RC; schema-compression study; cluster co-occurrence and event matching.

**Source docs say (delta):**
- The paper's **cluster-layer boundary mapping cost ($10-20 batched)** is correct per `PILOT_ENSEMBLE_2026-05-08.md`. Good.
- The paper does not name the **two validation routes** distinction (`feedback_two_validation_routes.md` per CLAUDE.md memory): stage-internal testing vs use-case demos. The latter (e.g. h2biomass reference-class memo, foak rag-vs-v2 demo) can substitute when the goal is utility, not "true" structure. The future-work section could identify which gaps are stage-internal-test-shaped vs use-case-demo-shaped.
- The **adjunct-engagement positioning** (CLAUDE.md memory `project_v2_positioning_via_adjunct.md`): the substrate is a research-topic generator and memo producer, not a tool to push for adoption; deliverables are publishable case studies. This is consistent with §9 but the paper could explicitly position the future-work items as research-programme deliverables.

**Gap type:** UNDERSPECIFIED (small).

**Recommended delta:** Add a closing paragraph: "These items partition into stage-internal validation tests (filter-chain calibration; replicate-stability characterisation; per-cluster fit_pct audit) and use-case demonstrations (cluster reports, project reports, reference-class memos). Either route can substantiate the methodology paper's claims; use-case demonstrations are particularly useful when the goal is utility rather than ground-truth verification."

**Source citations:** Jeff's memory notes `feedback_two_validation_routes.md`, `project_v2_positioning_via_adjunct.md` (referenced via CLAUDE.md memory index).

---

## §10 Conclusion

**Paper claims (current):** Pipeline produces four-layer structure + glossary; engine/config separation; ARENA full + ANAO partial; eight methodological design choices summarised; what has been validated vs what has not.

**Source docs say (delta):** Faithful summary. Could add a one-line nod to the 62.3% general-mechanism finding ("the v2 substrate is best understood as a general infrastructure-failure taxonomy with a renewable-bound layer") and the two-axis retrieval architecture if those go into the abstract.

**Gap type:** Faithful (consistent with abstract).

---

## Sections judged faithful

- **§4.5 s05 cluster_seed** — numerics correct.
- **§4.7 s07 cluster_singleton** — Arm-D semantics correctly captured.
- **§4.8 s08 cluster_residual** — convergence to 1,141 confirmed.
- **§5.2 Extraction-first taxonomy posture** — consistent with Jeff's framing.
- **§5.3 The legitimacy filter** — consistent with `methodology_lessons.md` §9.
- **§5.5 Distinctiveness over raw frequency** — consistent with metadata fingerprint design.
- **§5.6 Hybrid GPU-NLP plus LLM architecture** — consistent.
- **§5.8 Layer-of-inference dependency** — consistent (numerics agree on $170 fix).
- **§10 Conclusion** — consistent with paper's body and abstract.

---

## Source files in the reading not tied to a paper section

The following T3 worked-example artefacts are partially or wholly absent from the paper §7 demonstration:

- `cluster_reports/c016_report.md`, `cluster_reports/c1074_report.md` — additional cluster-synthesis worked examples beyond c042.
- `parent_reports/p18_report.md` — parent-level analytical synthesis (Material, chemical, and physical-property limits — the parent c042 maps to).
- `project_reports/neoen_big_battery_western_downs_deployment_project_report.md` — project-axis retrieval worked example demonstrating cross-document narrative reconstruction for one project.
- `use_case_demos/h2biomass_refclass_memo.md`, `h2biomass_refclass_v2_data_driven.md` — reference-class memo demonstrating how the substrate supports portfolio-decision diligence (filter-by-tech then read cross-tech standout clusters).
- `use_case_demos/foak_rag_vs_v2.md` — explicit RAG-vs-v2 contrast worked demo (relevant for §2 related-work RAG contrast and §7).
- `use_case_demos/causal_chain_full.md`, `causal_chain_test.md` — 88% causal-chain validation evidence (relevant for §6.1).
- `use_case_demos/grouping_rep_stability.md` — supplementary replicate-stability evidence.
- `use_case_demos/parent_archetypes_register.md` — register format demonstrating parent-layer as diagnostic vocabulary.
- `use_case_demos/event_coherence_audit.md` — 98% event-coherence validation evidence (relevant for §6.1).

These can be cited from §6.1 (causal_chain, event_coherence), §7 (cluster reports, parent report, project report, h2biomass demo, foak demo), or appendices.

The reading file's `arena_canonical/narrative/runs/2026-05-02-fullcorpus-1rep/` (full-corpus orchestrator infrastructure / wave-batched Anthropic Batches API design) and `seed_doc_heuristic.md` are infrastructure-level evidence relevant to §4.0 / §4.2 ingestion and grouping but currently uncited.

---

## Top-10 prioritised punch list

The highest-impact deltas to make first, in priority order:

1. **§4.10 — Correct the high-high agreement number from 95.8% to 93.8%** (45/48 = 93.75%). The paper has the wrong number; this is a factual error that an alert reviewer would spot.

2. **§4.9 — Add the priming-hazard finding (50pp), the deliberation-rich variance reduction (sd 13.6 → 7.24), and the threshold-defensibility argument** (canonical-set judgement, not v1 comparison). These three findings are the parent-derivation methodology contribution; the current paper presents only the output (86 parents) without the methodology that generates them defensibly. Cite `EXPERIMENTAL_METHODOLOGY.md`.

3. **§6.1 — Add four missing validations: cross-project diversity (17.8 projects/cluster, 6.9 categories/cluster), within-tech distinctness (top-50 battery subset, 0 merges), causal-chain coherence (88%), event-coherence on multi-parent stratum (98%).** These are load-bearing validations that the paper currently omits from its validation summary. Cite `arena_clustering_v2/notes.md` §4 + §10.1, `EXPERIMENTAL_METHODOLOGY.md` Phase 3.

4. **§7 — Add the c042 worked example, the ANAO ↔ ARENA parent overlap audit, and the ANAO atomicity-bound structural finding.** These three are the most concrete demonstrations of the substrate's analytical value (c042) and cross-corpus generalisation (overlap audit + ANAO structural finding). The paper §7 currently lists counts only. Cite `cluster_reports/c042_report.md`, `anao_n100_arena_overlap.md`, `anao_n100_demo/notes.md`.

5. **§4.10 — Add the two-shapes diagnostic-signal contribution.** Boundary-mapping ensembles distinguish single-boundary (sharpen criterion) from structural fragmentation (split parent) by concentration of top-1 alternative. This is a methodological contribution beyond the headline ensemble agreement numbers. Cite `PILOT_boundary_mapping_2026-05-08.md`.

6. **Abstract + §1 — Add the measurement-instrument framing with efficiency-chain reliability and the 62.3% general-mechanism finding.** These are the paper's strongest single arguments per the source documents and are currently absent from the abstract and introduction. Cite `methodology_notes.md` §11, `arena_clustering_v2/notes.md` §10.3.

7. **§4.2 — Add the chronological-accumulation finding, the lesson-field exclusion (Jaccard 0.678 → 0.786), and the consensus-graph mitigation.** These are load-bearing input-design and corpus-scale stability decisions that the paper alludes to but does not capture. Cite `runs/2026-05-02-postextract-grouping-perdoc/notes.md`, `runs/2026-05-02-replication-campaign/notes.md`, `runs/2026-05-02-fullrevs-production/notes.md`.

8. **§4.6 — Add the three-component precision envelope** (LLM nondeterminism ~3-5%, batch-composition sensitivity ~3-7%, cluster-boundary fuzziness ~10-22%). The paper currently makes no quantitative precision claim at the sweep stage; this stack of three measured terms is the substantive answer. Cite `arena_clustering_v2/notes.md` §6.8.

9. **§5.1 — Disclose the cross-paragraph context-binding retraction** (only ~30% of records show meaningful cross-paragraph context drawing; ~68% are local-paragraph paraphrase) and add the doc_0031 selection worked example. The paper's §5.1 implies a stronger context-binding claim than the empirical audit supports. Cite `INVESTIGATION_NOTES.md` Phase 3 + Phase 4.

10. **§8 — Adopt the locked epistemic position explicitly and add the lesson-field model-invention finding.** The paper says causal inference is "shallow"; the source's stronger framing is "we trust document authors to surface causation; we do not infer it from co-occurring observations". The lesson-field finding (mitigation language ungrounded in source markdown) is a concrete instance worth disclosing. Cite `methodology_notes.md` §6.5, §7.

---

**Minor issues to verify with Jeff before publication:**

- The theme count: paper says **16 themes**, source `INVESTIGATION_NOTES.md` Phase 7 says 12, `EXPERIMENTAL_METHODOLOGY.md` Phase 9 says 16 / 14 mechanism families, `full_summary.md` lists 16 themes (t01–t16). The 16-theme number appears to be canonical for the 86-parent extended set; the 12-theme number applies to an earlier 70-parent build. Confirm before paper draft.
- The cluster-signature-drift fix cost: paper says ~$170 batched, source confirms $170 batched + ~$25 re-ensemble. Paper could state the total ($195).
- The cross-corpus glossary "69 shared terms with ~30% polysemous false friends": the polysemy fraction is from CLAUDE.md / paper §4.12 but the reading file does not include the explicit 30% computation — this number may be from a session not captured in the reading file. Verify provenance.
