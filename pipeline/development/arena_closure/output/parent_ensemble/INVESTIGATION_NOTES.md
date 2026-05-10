# Substrate Defensibility & Reproducibility — Investigation Notes

**Status:** session record as of 2026-05-04. The position resolved here is the empirical basis for `pipeline/EXTRACTION_DEFENSIBILITY.md` and the methodology-paper claims that depend on it.

This document summarises a sequence of empirical experiments interrogating the v2 record substrate's validity. Read sequentially: each phase is a question, the answer found, and (where applicable) the corrected position and what was retracted along the way.

---

## Phase 1 — Bridge typology (script 16)

**Question.** Do the 71 v2 parent archetypes correspond to formal academic frameworks the field invokes? If yes, the substrate is doing aggregation; if no, the substrate is exposing gaps where the field lacks a shared formal vocabulary for mechanisms it routinely encounters.

**Method.** For each of 71 parents, identified the canonical academic framework (or `None` if no canonical framework exists). Searched the *records* corpus (13.8M chars) and the *raw markdown* corpus (94.7M chars) for invocations of each framework's diagnostic vocabulary at per-million-token density. Classified each parent by frequency-density signature.

**Outputs.**
- `closure/output/framework_bridge_typology.json`

**Findings.**

Five-way typology over the 71 parents:

| Type | Count | What it indicates |
|---|---:|---|
| ABSENT | 15 | Frame missing from both source and records — clean bridge opportunity |
| LLM_STRIPPED | 11 | Source uses the frame; extraction strips it |
| LLM_AMPLIFIED | 11 | Records over-invoke vocabulary not present in source |
| PARITY (low / high) | 11 | Frame already in active circulation at parity rates |
| NO_FRAMEWORK | 23 | No canonical academic framework exists for the mechanism class |

**Key finding.** ~31% of parents (ABSENT + LLM_STRIPPED) name mechanisms whose formal academic frameworks are essentially absent from the field's working language — the substrate exposes structural gaps in how the field reasons about its own failure modes. Examples: real options / Dixit-Pindyck (p25), Pareto-front / multi-objective optimisation (p18), STRIDE / threat modelling (p55), Modigliani-Miller (p43), Goodhart's law (p26), incomplete contracts (p30).

**Discovered along the way.** Initial sweeps using only the records corpus mis-classified parents because record vocabulary reflects model voice as much as author voice. Symmetric records-vs-markdown comparison was needed to separate genuine field-language signal from extraction artefact. **Two parent classes (p19, p29) flipped from "informal-only" → "extraction-amplified" once the symmetric test was run** — the records said "principal-agent / information-asymmetry" but the source markdown didn't. These are LLM_AMPLIFIED, not field-level absences.

---

## Phase 2 — Extraction voice audit (script 17)

**Question.** Records carry the LLM's stock voice. Does that voice change *concepts*, or just *language*? If voice injects content the source doesn't have, the substrate's foundations are compromised.

**Method.** Corpus-wide n-gram comparison: for unigrams (≥200 occurrences), bigrams (≥50), and trigrams (≥20) in the records corpus, computed per-million-token density vs source markdown.

**Outputs.**
- `closure/output/extraction_voice_audit.json`

**Findings.**
- **0 unigrams** above the frequency threshold are completely absent from markdown.
- **0 bigrams** above threshold are completely absent from markdown.
- **6 trigrams** absent — and every one is an extraction-narrative summary pattern: *"this is identified," "workshop participants identified," "identified as specific," "the pilot found," "scoping survey identified," "as factor that."* No domain content.
- Top-amplified bigrams: *"is identified" (40.9×), "trial found" (27.8×), "was identified" (23.1×), "this caused" (10.9×), "barrier to" (8.3×).* Passive constructions, narrative-summary verbs, causal connectives — the model's voice for packaging findings.

**Key finding.** The model has a voice (stock summary register, passive constructions, narrative connectives) but **does not invent content concepts at scale.** ~96% of n-grams in records that are absent from the local evidence excerpt are paraphrases of source content (whether the local paragraph or elsewhere), not invented content. Voice is rephrasing; concepts are preserved.

---

## Phase 3 — Narrative-vs-evidence audit (script 18)

**Question.** A natural defence of the substrate had been: "each record carries whole-document context bound into it via one-shot extraction — paragraph-chunked retrieval can't replicate this." Is that empirically true?

**Method.** 50-record stratified sample across parents. For each record, compared `narrative` vs `evidence` 3-grams; for novel 3-grams (in narrative, not evidence), checked whether they appear elsewhere in the source markdown. High doc-context-rate would support the cross-paragraph-binding claim.

**Outputs.**
- `closure/output/narrative_vs_evidence_audit.json`

**Findings.**

| Verdict | n records | % |
|---|---:|---:|
| DOC_CONTEXT_DRAWN (≥50% novel content from elsewhere) | 2 | 4% |
| MIXED (20-50%) | 14 | 28% |
| VOICE_OR_IMPUTED (<20%) | 34 | 68% |

Average doc-context rate: 13% (lower bound; strict 3-gram exact-phrase match undercounts paraphrased meaning).

**Key finding — and an important retraction.** The "one-shot whole-document context bound into each atomic record" claim was **overstated**. Only ~30% of records show meaningful cross-paragraph context drawing. Most narrative content (~68%) is local-paragraph paraphrase. The architectural advantage of one-shot extraction over paragraph-chunked extraction operates at the margin (~30% of records), not as a categorical departure.

**Retracted framing.** Earlier session memory had the cross-paragraph-binding as a load-bearing claim. Corrected position: the substrate's value comes from *atomicity through selection-and-segmentation* (next phase), not from cross-paragraph context binding.

---

## Phase 4 — Selection-and-segmentation worked examples

**Question.** If atomicity-via-paragraph-paraphrase is the dominant pattern, what categorical advantage does one-shot extraction have over a paragraph-chunked retrieval system?

**Method.** Two worked examples on representative documents.

### doc_0121 — Segmentation across atomic-claim boundaries

ARENA Information Session presentation. 31 substantive paragraphs, **68 atomic records** (ratio 2.19×).

The single 1,652-char paragraph #19 (a 6-row table of eligibility criteria) was decomposed into **8 records**: one per table row plus a meta-record ("Six eligibility criteria. All must be met to proceed to merit assessment") that synthesises the table's structure.

Bullet-list paragraphs similarly fragmented per-bullet (paragraph #2: 6 records from a 6-bullet DER definition; paragraph #15: 6 records from a 6-bullet funding-rules list).

**Implication.** Paragraph boundaries are layout artefacts. Atomic-claim boundaries are the real unit. Identifying them requires reading the document and recognising that table rows, bullets, and multi-claim prose paragraphs each carry distinct atomic claims. Paragraph-chunking either loses this (one chunk = one record means 6-criterion table → 1 record, massive information loss) or requires its own intra-paragraph segmentation logic (which *is* document-aware judgement, just relocated).

**Corpus statistic.** 174 documents have ≥30 substantive paragraphs *and* produce more records than paragraphs. Multi-claim-per-paragraph is common, not rare.

### doc_0031 — Selection of claim content from non-claim scaffolding

ARENA Vehicle-to-Grid Insights Final Report. 123 substantive paragraphs, 60 records, **22 paragraphs (18%) skipped**.

Sampled skipped paragraphs:
- *Front-matter:* "To the best of ARENA and Energeia's knowledge, no conflict of interest..."
- *Copyright:* "ARENA retains and owns the copyright for this commissioned report..."
- *Methodology bridge:* "This section reports on the type and quality of data generated... ActewAGL supplied the data..."
- *Tutorial exposition:* "The FCAS lower market involves managing excess electricity supply by making use of spare capacity..."

All correctly skipped — none carry mechanism-bearing content. The selection step is doing semantic filtering between claim-content and non-claim scaffolding.

**Caveat raised in discussion.** The FCAS exposition paragraph #107 is a *weak* test case for "document-aware redundancy filtering" specifically — its skip can be explained by paragraph-shape filtering (it reads as exposition regardless of doc context) without invoking cross-document reasoning. A stronger test would find a paragraph that *isolated* looks like a finding but was rejected because the same content was covered more specifically elsewhere. That test was not run.

---

## Phase 5 — 50-run parent ensemble (scripts 19, 20)

**Question.** How reproducible is the parent layer? If we re-run Pass-1 (parent derivation) 50 times on the same input, do we get the same parent vocabulary? If not, what's the variance pattern?

**Method.**
- 50 identical Pass-1 requests submitted via Anthropic Batches API. Same prompt, same input (1,141 v2 mechanism clusters), seed=42 fixed across all runs. Variance comes purely from sampling.
- Single Opus 4.7 consolidation call to merge the 4,150 parent labels (50 runs × ~83 parents avg) into a canonical mechanism vocabulary.

**Outputs.**
- `parent_ensemble/raw_responses.jsonl` — 50 raw Anthropic responses
- `parent_ensemble/parsed_runs.jsonl` — 50 parsed parent lists with criteria + exemplars
- `parent_ensemble/canonical_vocabulary.json` — 126 canonical classes with member-label mapping
- `parent_ensemble/canonical_vocabulary.md` — human-readable summary
- `parent_ensemble/ensemble_summary.json` — aggregate stats (granularity dist, etc.)

**Cost & time.** $26.23 batch (50 runs) + $4.47 consolidation = **$30.70 total**. Batch wall: 17 min. Consolidation wall: 17 min. Far under the 24h SLA.

**Findings — granularity distribution.**

| Statistic | Value |
|---|---|
| n_parents per run, min / mean / max | **52 / 83 / 115** |
| sd | 13.6 |
| p10 / p50 / p90 | 64 / 84 / 100 |

The model's discretion about how many parents to produce spans factor-of-2.2 across draws. The canonical Run A's 71 parents sits in the **lower third** of this distribution.

**Findings — canonical vocabulary frequency tiers (after Opus consolidation).**

| Tier | n classes |
|---|---:|
| core (≥90%) | 24 |
| high (70-89%) | 23 |
| boundary (40-69%) | 44 |
| rare (20-39%) | 26 |
| singleton (<20%) | 9 |
| **Total distinct canonical classes** | **126** |

Three classes appeared in **50/50 runs** (100%): *Measurement and sensing limitations; Model, simulation, and forecast inaccuracy; Material, chemical, and physical-property limits.* These are the model's most-canonical mechanism classes.

**Initial framing.** "126 canonical mechanism classes is the ensemble vocabulary; 24 stable-core classes are the model-canonical mechanism vocabulary." The methodology paper would lead with this.

---

## Phase 6 — Coherence test (script 21)

**Question raised by Jeff after Phase 5.** Hypothesis: 126 canonical classes may not be a coherent atomic taxonomy but rather a granularity-blurred union with substantial conceptual overlap. Each individual run produces internally-consistent partitions, but aggregating across runs creates a superset where canonical class boundaries are ambiguous because different runs draw the cuts in different places. If that's right, "126 canonical classes" is misleading — it's an over-merge of run-level boundary choices.

**Method.** For each canonical class, count how many of the 50 runs contributed 2+ parent labels. Each run produces internally-distinct parents (no within-run overlap), so any single run contributing 2+ labels to one canonical class means that run treated those as *distinct* mechanism classes. The canonical class then merges what the run treated as separate — i.e., is **coarser-than-run** for that subdivision.

**Outputs.**
- `parent_ensemble/coherence_test.json`
- `parent_ensemble/coherence_test.md`

**Findings — empirically confirms Jeff's hypothesis.**

Of 126 canonical classes:
- **35 (28%) are atomic** — no run ever subdivided them.
- **91 (72%) have at least one run contributing 2+ labels** — meaning some run treated the canonical class as 2-4 distinct mechanism classes.

By tier:

| Tier | n classes | % atomic |
|---|---:|---:|
| **core (≥90%)** | 24 | **0%** |
| high (70-89%) | 23 | 9% |
| boundary (40-69%) | 44 | 23% |
| rare (20-39%) | 26 | 58% |
| singleton (<20%) | 9 | 89% |

**The most-agreed-upon canonical classes are the least atomic.** Every single core class (24/24) has at least one run that treated it as 2-4 distinct mechanism classes. Top examples:

| Canonical class | Runs containing | Runs splitting | Max labels/run |
|---|---:|---:|---:|
| Model, simulation, and forecast inaccuracy | 50 | 20 | 3 |
| Material, chemical, and physical-property limits | 50 | 19 | **4** |
| Control logic, configuration, and parameter errors | 49 | 16 | **4** |
| Lab-to-field and pilot-to-scale translation failure | 49 | 12 | 3 |

**Important retraction.** "126 canonical mechanism classes" was a misleading headline. The 126 number is the union of run-level boundary choices, not a coherent atomic taxonomy. The correct framing distinguishes *mechanism territory* (what regions of mechanism space are covered, robustly and reproducibly) from *atomic boundaries* (where the cuts fall, which is draw-dependent at fine granularity).

---

## Phase 7 — Atomic sub-class decomposition (script 22)

**Question raised by Jeff after Phase 6.** If 91 of 126 canonical classes are non-atomic, can we observe how each one has been split across runs and treat each run-level split as a separate atomic label, building the "real superset" of distinctions runs collectively make? The convergence limit of this recursion would be back at the 1,141 cluster names.

**Method.** Single Opus 4.7 call given all 91 non-atomic canonical classes with their member labels. For each, identify the recurring atomic sub-classes that the run-level distinctions name. The 35 atomic canonical classes pass through unchanged.

**Outputs.**
- `parent_ensemble/atomic_subclass_decomposition.json`
- `parent_ensemble/atomic_subclass_decomposition.md`

**Findings.**

| Stage | n classes |
|---|---:|
| Canonical (script 20) | 126 |
| ├─ Atomic pass-through | 35 |
| └─ Non-atomic decomposed | 91 |
| Sub-classes produced | 334 |
| **Total atomic vocabulary** | **369** |

Vocabulary growth factor: 2.93× over canonical 126.

**Tier-shape shift:**

| Tier | Canonical (126) | Atomic (369) | Δ |
|---|---:|---:|---:|
| core (≥90%) | 24 | 17 | -7 |
| high (70-89%) | 23 | 27 | +4 |
| boundary (40-69%) | 44 | 46 | +2 |
| rare (20-39%) | 26 | 34 | +8 |
| singleton (<20%) | 9 | **245** | +236 |

**Key observations.**

1. **245 singletons** dominate the new vocabulary — these are within-canonical sub-distinctions only some runs make.
2. **The 17 atomic-core sub-classes are all `.s1`** — i.e., the *most-populated* sub-class within each canonical class. They represent the **central instance of each mechanism** that runs most consistently produce.
3. **44 atomic sub-classes at ≥70%** is the stable atomic vocabulary. Compare to 47 canonical at ≥70% — similar count, but the atomic version names central-instance distinctions runs converge on rather than blurred-merger consensus.
4. **Cost & quality:** $2.89, 12 min. 30 of 91 (33%) had minor coverage issues (1-2 labels swapped between adjacent canonical classes during decomposition). Acceptable noise.

**The substrate's coarsening hierarchy** (Jeff's framing, now empirically anchored):

```
1,141 cluster names           — corpus's most-granular reproducible atomic taxonomy
   ↓ ~3× coarsening (this decomposition implies)
369 atomic sub-classes        — atomic vocabulary, runs' collective boundary set
   ↓ ~3× coarsening (script 20 consolidation)
126 canonical classes         — granularity-blurred union, boundary-merged
   ↓ ~1.5× coarsening (per-run granularity choice)
~83 parents per run           — first-level grouping; each run picks one carving
   ↓ ~7× coarsening (Pass-3 themes audit)
12 themes                     — high-level mechanism families
```

The substrate is best understood as a **stack of coarsenings**, each level with its own reproducibility characteristics. The "real" atomic mechanism count for this corpus is somewhere between 369 (model's collective boundary union at parent layer) and 1,141 (cluster-level atomic descriptions). Going below 369 toward cluster-level granularity is what the cluster-reproducibility experiment ($2k pitch) would test.

---

## Resolved methodological position

After this sequence of experiments, the position to take in the methodology paper:

### What is robust

1. **Mechanism-territory coverage at coarse granularity is highly reproducible.** ~24 high-frequency canonical classes cover regions of mechanism space that *every* run navigates, even if individual runs choose different cut-points within those regions. This is strong evidence that the underlying clusters being grouped are themselves stably meaningful — otherwise the parent layer couldn't converge across 50 independent draws onto the same broad mechanism territories.

2. **Run-internal partitioning is coherent.** Each individual run produces a self-consistent partition with non-overlapping parents at its chosen granularity. Run-level work is not noise.

3. **The model has a stable preferred granularity.** N_parents per run distribution is mean 83, sd 14, with most density between 64 and 100. The model is not making wildly inconsistent granularity choices.

4. **Voice is rephrasing, not concept injection.** The extraction model's stock summary voice is a real but bounded phenomenon. Cluster identity tracks situational similarity in source documents, not imputed conceptual structure.

5. **Atomicity at corpus scale requires inference.** Selection (filtering claim content from scaffolding) and segmentation (identifying atomic-claim boundaries within paragraphs) are document-aware tasks that paragraph-chunked extraction cannot replicate. The doc_0121 worked example demonstrates segmentation; the doc_0031 worked example demonstrates selection.

### What is draw-dependent

1. **Where the cuts fall at fine granularity.** The boundary between "forecast inaccuracy" and "model-assumption failure" is real but contested — different runs draw it differently. ~72% of canonical classes have at least one run that treats them as multiple sub-classes.

2. **Total count of distinct classes per run.** Range 52-115. Any single run is one realisation of the model's granularity-discretion distribution.

3. **The "ensemble union vocabulary" of 126 canonical classes is broader than any individual run's atomic partition.** It is not "the canonical fine-grained taxonomy"; it is an over-merge resulting from different runs drawing boundaries in different places.

### What was retracted along the way

1. The **"two-corpus architecture"** framing as a methodological pillar (Jeff's intervention: I had elevated his passing observation that markdown is cheap to query into a labelled architectural feature; correctly cut from `EXTRACTION_DEFENSIBILITY.md`).

2. The **"one-shot whole-document context bound into each atomic record"** claim, when empirical audit found only ~30% of records show meaningful cross-paragraph context drawing.

3. The **"126 canonical mechanism classes"** headline framing, when the coherence test showed only 28% are atomic and 100% of core classes have run-level subdivisions.

4. **Records-side vocabulary frequency as evidence about field-language uptake** — the records-vs-markdown ratio diagnoses extraction voice, not field practice.

---

## What this enables for the methodology paper

This investigation provides a defensible empirical record for several methodology-paper claims:

1. **Substrate validity.** The 50-run ensemble + voice audit + narrative-vs-evidence audit jointly establish that the substrate is doing real work (selection, segmentation, atomic rendering) without inventing content concepts at scale.

2. **Reproducibility characterisation.** Granularity-distribution + canonical-vocabulary-with-coherence-test gives a quantified picture of *what is robust* (coarse mechanism territory) and *what is draw-dependent* (fine atomic boundaries) at the parent layer.

3. **Demonstration of method, scalable to clusters.** The full procedure (N independent runs → consolidation → coherence test) can in principle be applied at the cluster layer to test whether the underlying 1,141 mechanism clusters are themselves reproducible at corpus scale. Cost projection for the cluster-level version: ~$2,000 (50 full clusterings × ~$40 each). The parent-layer demo is the proof-of-concept that justifies the grant ask.

4. **Honesty about model discretion.** The methodology paper can claim *more* by being explicit about what is and isn't a model-discretionary call, rather than presenting the canonical 71-parent run as a definitive answer. The principled framing — "the model partitions mechanism space coherently at run-internal granularity, with stable territory coverage and draw-dependent fine boundaries" — is more credible than overselling reproducibility we don't have.

---

## Folder organisation

The full set of artefacts from this investigation is split across two locations:

```
closure/output/
├── framework_bridge_typology.json          ← Phase 1
├── extraction_voice_audit.json             ← Phase 2
├── narrative_vs_evidence_audit.json        ← Phase 3
└── parent_ensemble/                        ← Phases 5 + 6
    ├── batch_id.txt
    ├── batch_meta.json
    ├── raw_responses.jsonl                  (50 raw Anthropic responses)
    ├── parsed_runs.jsonl                    (50 parsed parent lists)
    ├── ensemble_summary.json                (granularity stats)
    ├── ensemble_summary.md
    ├── canonical_vocabulary.json            (126 classes + member mapping)
    ├── canonical_vocabulary.md              (human-readable)
    ├── canonical_vocabulary_meta.json       (call cost/timing)
    ├── coherence_test.json                  (atomicity per canonical class)
    ├── coherence_test.md
    └── INVESTIGATION_NOTES.md               (this document)
```

Phase 4's worked-example artefacts (doc_0121, doc_0031) are in the source markdown corpus at `corpora/arena/markdown/` and per-doc records at `corpora/arena/output/per_doc/`.

The substrate-defensibility work would benefit from consolidation under a shared parent folder (e.g. `closure/output/substrate_defensibility/`). Currently scripts 16/17/18 outputs are mixed with the original roll-up artefacts in `closure/output/`. Proposed but not executed.

---

## Reproducibility — re-running this investigation

```bash
# Phase 1: bridge typology (free, ~1 min)
python3 corpora/arena/clustering_v2/closure/code/16_framework_bridge_typology.py

# Phase 2: voice audit (free, ~1 min)
python3 corpora/arena/clustering_v2/closure/code/17_extraction_voice_audit.py

# Phase 3: narrative-vs-evidence audit (free, ~1 min)
python3 corpora/arena/clustering_v2/closure/code/18_narrative_vs_evidence_audit.py

# Phase 5: 50-run ensemble (~$26 batch, ~17 min)
python3 corpora/arena/clustering_v2/closure/code/19_parent_ensemble_batch.py --dry        # validate
python3 corpora/arena/clustering_v2/closure/code/19_parent_ensemble_batch.py --submit     # submit batch
python3 corpora/arena/clustering_v2/closure/code/19_parent_ensemble_batch.py --status     # poll
python3 corpora/arena/clustering_v2/closure/code/19_parent_ensemble_batch.py --retrieve   # download
python3 corpora/arena/clustering_v2/closure/code/19_parent_ensemble_batch.py --analyse    # initial summary (Jaccard-based, over-fragmented)

# Phase 5b: canonical vocabulary consolidation (~$5, ~17 min)
python3 corpora/arena/clustering_v2/closure/code/20_consolidate_ensemble.py

# Phase 6: coherence test (free, ~1 sec)
python3 corpora/arena/clustering_v2/closure/code/21_canonical_coherence_test.py

# Phase 7: atomic sub-class decomposition (~$3, ~12 min)
python3 corpora/arena/clustering_v2/closure/code/22_subclass_decomposition.py
```

**Reproducibility note.** With seed=42 fixed across all 50 runs, the *prompt* is byte-identical each invocation but the *Anthropic model output* varies due to sampling. Re-running the experiment will produce a different 50-run ensemble; the granularity distribution shape and tier counts should be similar but not identical. The *retraced* statistical claims (mean 83 ± sd 14; ~24 core; ~28% atomic) should be reproducible within sampling error at N=50.
