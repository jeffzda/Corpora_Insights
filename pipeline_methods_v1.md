# A pipeline for atomic-claim extraction, mechanism-coherent clustering, and structured taxonomy derivation from institutional document corpora

**System version: v1 (configuration date 2026-05-09)**
**Document type: methods**

## Abstract

This document describes a pipeline that takes a corpus of PDF documents and a domain configuration, and produces (a) a registry of atomic insight records grounded in source text, (b) a mechanism-coherent cluster catalogue derived from those records, (c) a hierarchical taxonomy of parent mechanism classes and themes derived from the catalogue, and (d) a parallel corpus glossary with metadata fingerprints that maps the corpus's named entities and recurring concepts. The architecture separates a domain-independent engine from per-corpus configuration so that adding a new corpus requires no changes to engine code. The pipeline orchestrates twenty-two configured stages across two parallel sub-pipelines, combining deterministic regex / NER / embedding passes for candidate harvest and statistical aggregation with LLM passes for atomic extraction, classification, clustering, taxonomy derivation, and audit. The methodological contributions claimed are: a defensible atomic-claim substrate that survives a voice audit at the rephrasing layer; a multi-pass clustering architecture in which a downstream recurrence threshold absorbs upstream filter false positives; an extraction-first taxonomy posture in which categorisation is a labelling pass over an already-extracted record substrate; and a documented separation between engine and corpus-specific configuration. The system has been demonstrated end-to-end on the Australian Renewable Energy Agency Knowledge Bank (1,440 documents, 90,192 records, 1,141 clusters, 86 parents, 16 themes, 760-term glossary) and partially demonstrated on the Australian National Audit Office performance-audit corpus (1,452 documents, 590-term glossary, N=100 clustering pilot). Formal validation of the analytical outputs against expert ground truth has not been undertaken; the current state is that the pipeline produces structured, plausible outputs across two distinct corpora.

---

## 1. Introduction

Institutional knowledge corpora — government audit reports, agency-funded project reports, regulatory determinations, parliamentary committee inquiries — accumulate substantial analytical material over decades. Individual documents in these corpora are produced and read one at a time: an audit report is written for a specific tabling, a project report for a specific funding milestone, a committee inquiry for a specific reference. The corpus-level signal — what these reports *collectively* show about how programs fail, how interventions perform, what mechanisms recur — is largely inaccessible without an aggregation pass.

The aggregation pass has historically been done either (a) manually by sectoral specialists who read at human throughput and produce narrative literature reviews, or (b) by retrieval over full-text indexes that surface documents matching a query but do not produce structured findings. Neither approach scales to the case of a portfolio manager or policy analyst who needs a structured, queryable representation of corpus content with confident provenance back to source.

This pipeline addresses that gap by extracting atomic insight records from each document, clustering records by causal mechanism rather than topic, deriving a parent-class taxonomy from the cluster catalogue, and grouping parents into themes — producing a four-layer hierarchy (records → clusters → parents → themes) in which any element can be traced back to its source documents and any source document can be located in the hierarchy. The methodology is corpus-independent: the engine handles document ingestion, extraction, clustering, taxonomy derivation, glossary construction, and downstream synthesis without per-corpus code changes; the per-corpus configuration is a single YAML file plus a corpus-specific scraper.

The system is positioned as a research substrate rather than an operational tool. The substrate is a v1 measurement instrument with named, bounded uncertainty; formal validation against expert ground truth and replicate-stability characterisation at corpus scale are documented gaps the methodology paper presents as publishable extensions rather than completed work.

---

## 2. Related work

<!-- Citations to be filled in by hand; the following sub-sections name the topical neighbours the pipeline sits among. -->

The pipeline draws on five adjacent areas of work:

**Computational content analysis** of institutional and policy corpora. Work in this area has traditionally used dictionary methods, named-entity recognition, topic modelling (LDA, NMF), and supervised classification over hand-coded training sets. The pipeline departs from this tradition in producing atomic *claim*-level records rather than document- or paragraph-level codes, and in treating taxonomy derivation as a downstream pass over the claim substrate rather than an a-priori classification scheme applied during reading.

**LLM-based information extraction.** A growing body of work uses large language models to extract structured information (entities, relations, events, claims) from unstructured text. The pipeline's extraction stage is in this lineage, with three architectural choices that distinguish it: a one-shot per-document extraction call (rather than paragraph-chunked extraction); a deliberately taxonomy-agnostic prompt that asks for findings without classifying them; and a downstream voice audit that quantifies the rephrasing layer the model imposes on extracted records (Section 5.1).

**Knowledge graph construction.** Pipelines that build typed knowledge graphs from text typically commit to an ontology before extraction. The pipeline sidesteps this commitment by treating the cluster catalogue as a learned mid-layer between extraction and taxonomy. Mechanism-level clusters are derived from records and then organised by Opus 4.7 into parent classes; the parent and theme taxonomies are derivative artefacts, not extraction targets.

**Document clustering and topic modelling.** The clustering sub-pipeline (Section 4, stages s05-s08) is most directly comparable to LLM-mediated clustering approaches that rely on embedding similarity plus LLM-based merge / label decisions. The pipeline differs in (a) operating on extracted atomic records rather than document chunks, (b) using a one-shot batched LLM call to classify *and* mint new clusters in the same pass, and (c) the procurement-probity invariant that cluster signatures are frozen during a sweep so that records admitted under a published criterion remain admitted under that same criterion.

**Glossary construction and entity normalisation.** The corpus glossary sub-pipeline (Section 4, stages g01-g11) draws on entity-extraction toolchains (regex-based candidate harvest, spaCy NER, embedding-based normalisation) combined with LLM definition passes and a deterministic metadata-fingerprint computation. The contribution is the integration: per-term frequency, document coverage, and metadata-axis distinctiveness ratios are computed against gazetteer-validated localities and corpus base rates, producing a glossary that is *empirically grounded* rather than a hand-curated reference resource.

References to the specific works in each area should be filled in at this point; the development notes do not contain a literature review.

---

## 3. System overview

The pipeline takes a corpus of PDFs and a domain configuration as input and produces a four-layer structured representation as output. Two sub-pipelines run from a shared markdown-rendering stage: a **failure-mode pipeline** that produces records, clusters, parents, and themes, and a **glossary pipeline** that produces a corpus glossary with metadata fingerprints.

```
┌───────────────────────────────────────────────────────────┐
│  Document ingestion                                        │
│  domains/<corpus>/scrape.py → corpora/<corpus>/pdfs/       │
│  pipeline/ingest/marker_convert.py → marker rendered.md    │
└──────────────────────────────┬─────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
   ┌─────────────────────┐           ┌─────────────────────────┐
   │ Failure-mode        │           │ Glossary sub-pipeline    │
   │ pipeline            │           │ (parallel branch from   │
   │ (s01–s11)           │           │  markdown; never rejoins)│
   └─────────────────────┘           └─────────────────────────┘
   │ s01 extract                     │ g01 regex candidates
   │ s02 group_events                │ g02 NER candidates (sm + trf)
   │ s03 label_record_types          │ g03 normalise (embedding +
   │ s04 cluster_filter              │     catalogue match)
   │ s05 cluster_seed                │ g04 define
   │ s06 cluster_sweep               │ g05 define_followups
   │ s07 cluster_singleton           │ g06 merge
   │ s08 cluster_residual            │ g07 subcategory_propose
   │ s09 parent_derive               │ g08 subcategory_apply
   │ s10 parent_assign               │ g09 metadata_fingerprint
   │ s11 theme_audit                 │ g10 finalise
   ▼                                 │ g11 inverse_signatures
   records → clusters →               ▼
   parents → themes                  glossary entries with
                                     fingerprints + inverse
                                     signatures
```

The failure-mode pipeline produces:

- **Records**: atomic claim records, each with `narrative`, `evidence`, `lesson`, `significance`, `intervention`, `pages`, and a stable record id grounded in document order.
- **Tagged records**: each record receives six axis tags (`is_occurrence`, `is_mechanism`, `is_specification`, `is_lesson`, `is_recommendation`, `valence`).
- **Cluster catalogue**: each cluster has a stable id, a canonical name, a mechanism signature, and a set of member record ids.
- **Parent classes**: each parent has a name, description, mechanism criterion, and a set of member cluster ids.
- **Themes**: each theme has a name, description, and a set of member parent ids.

The glossary pipeline produces:

- **Glossary entries**: term, expansion, category, sub-category, definition, context note, frequency stats, sources.
- **Metadata fingerprints** per term: distinctiveness ratios across project / category / programme / lead-organisation / year axes versus corpus base rates.
- **Inverse signatures**: per-project term-distinctiveness profile (project_vocabularies) and per-term project-distinctiveness profile (term_top_projects).

The CLI dispatcher (`pipeline/run.py`) exposes every configured stage as a `--step <name>` argument under `python -m pipeline.run --domain <corpus>`. The `STEPS` dictionary in `run.py` is the canonical registry of available stages.

---

## 4. Pipeline stages

This section describes each configured stage. For each, the description names: what the stage does, what it consumes, what it produces, the canonical model selection, and the non-obvious design decisions documented in the development notes. Parameter values are referenced from `domains/<corpus>/domain.yaml` rather than reconstructed from code.

### 4.0 Document ingestion

**Stage modules:** `pipeline/ingest/base.py`, `pipeline/ingest/marker_convert.py`, `pipeline/ingest/render_json.py`, plus `domains/<corpus>/scrape.py` per corpus.

The ingestion sub-pipeline downloads source PDFs and converts them to structured markdown. Scraping is treated as corpus-specific configuration: each domain provides a `scrape.py` that subclasses `BaseScraper` and implements `discover()`. The base class (`pipeline/ingest/base.py`) provides HTTP session management, rate limiting, state and resume, download, and metadata CSV writing. A 7-item checklist (`pipeline/ingest/checklist.py`) validates each scraper against the contract.

PDF→markdown conversion uses `marker` (an open-source layout-aware PDF parser). The Python wrapper at `pipeline/ingest/marker_convert.py` walks `corpora/<corpus>/pdfs/` (recursive, configurable glob), skips PDFs whose `<stem>/<stem>.rendered.md` already exists, and for each remaining PDF runs `marker_single` to produce JSON output and then `render_json.py` to serialise that JSON to markdown with footnote rewriting, page markers, and broken-encoding fixups. Resumable; emits per-PDF heartbeat with rate and ETA per CLAUDE.md long-running-script convention. A bash variant (`marker_convert.sh`) is preserved for shell-only invocation but is documented as superseded.

The pipeline supports parallel workers (`--workers N`) via `ProcessPoolExecutor`. Marker uses GPU; the practical concurrency limit is determined by GPU memory rather than CPU cores.

**Note on marker output specifically.** Marker preserves table structure (HTML tables with row and column structure intact in the markdown), figure captions with cross-references, footnote markers and bodies, and page boundaries. The downstream clustering and glossary stages depend on this: cluster signatures derived from per-document records benefit from atomic claims that include numeric quantities and named entities recoverable from tables; the glossary's titlecase candidate sweep matches on multi-word phrases that marker's prose-faithful rendering preserves.

### 4.1 s01 extract — atomic-claim extraction

**Module:** `pipeline/extract.py` (called via `pipeline/stages/s01_extract/stage.py`).
**Prompt:** `domains/<corpus>/prompts/extract.md`.
**Models used to date:** Sonnet 4.6 (ARENA), Opus 4.7 (ANAO config).

The extraction stage is one LLM call per document. It receives the document's full rendered markdown and a domain prompt (the ARENA prompt at `domains/arena/prompts/extract.md` is the canonical reference; ANAO uses a derivative). The prompt is deliberately taxonomy-agnostic: it asks the model to extract every "finding" — defined broadly to include outcomes, mechanisms, constraints, methodology observations, operational patterns, recommendations, identified risks, and positive insights — without classifying them. Findings are emitted as atomic JSON records, each with the fields `id`, `title`, `narrative`, `lesson`, `significance` (1-5), `intervention`, `pages`, and `evidence`. Atomicity is enforced by prompt: one record per mechanism, with bullet lists and table rows producing one record per item.

**Configuration knobs** (per `stages.extract` in `domain.yaml`):
- `model`, `max_tokens`: model identifier and output ceiling. The pipeline's standing instruction is to set `max_tokens` to the model's maximum (128k for Sonnet 4.6 and Opus 4.6; 64k for Opus 4.7) on every generative task. Truncated structured output wastes the entire call.
- `output_dir`: per-document JSON output directory.
- `ids_per_document`, `record_id_prefix`: pre-allocated record id range and prefix.
- `max_document_chars`: split threshold for documents over the model's effective context.

**Validation completed:** a corpus-wide voice audit (`corpora/arena/clustering_v2/closure/code/17_extraction_voice_audit.py`) and a narrative-vs-evidence audit (`closure/code/18`) on the ARENA substrate. The voice audit compared n-gram densities in the 13.8M-character record substrate against the 94.7M-character source markdown and identified the model's voice as a consistent stylistic register (passive constructions, causal connectives, narrative-summary verbs) that operates at the rendering layer and not at the conceptual layer. Six trigrams were absent from the source markdown; all six are extraction-summary patterns ("workshop participants identified", "the pilot found", etc.) rather than domain content. The narrative-vs-evidence audit on a 50-record stratified sample found that ~96% of novel n-grams in `narrative` (those not present in the record's `evidence` excerpt) are paraphrases of source content. The substrate is voice-affected but not concept-injected; see `pipeline/EXTRACTION_DEFENSIBILITY.md` for the resolved methodological position.

**Validation outstanding:** formal claim-level fidelity assessment against hand-labelled ground truth has not been done. The substrate's faithfulness rests on the voice audit plus a 92.2% grounding rate from the legacy v1.3 verification pass, which is not strictly comparable to the v2 substrate.

### 4.2 s02 group_events — per-document event grouping

**Module:** `pipeline/stages/s02_group_events/stage.py`.
**Models used:** Sonnet 4.6 (ARENA), Opus 4.7 (ANAO config).

After extraction, a single document may contain multiple records that describe the same underlying event (e.g. an outage event that several paragraphs describe with different framings). The group_events stage takes the per-document records and asks the model to assign each record to an event id; records describing the same event share an id.

The output is a per-document `<doc>.events.json` with assignments and event-level metadata. Cross-document event matching is *not* attempted at this stage; it is treated as a post-clustering analytical question.

**Configuration knobs** (per `stages.group_events`):
- `model`, `max_tokens`, `output_dir`.

**Validation completed:** a 3-doc replication campaign (`canonical/narrative/runs/2026-05-02-replication-campaign/`) and a 12-doc REVS production run characterised replicate-stability of the grouping pass. Pair-decision instability at temperature=0 was approximately 32% at 3-doc scale and approximately 50% pair-Jaccard at 12-doc scale.

**Validation outstanding:** replicate-stability at full corpus scale is unmeasured. A documented publishable extension (re-run twice, report Jaccard) is in §16.6 of `corpora/arena/methodology_lessons.md`.

### 4.3 s03 label_record_types — six-axis tagging

**Module:** `pipeline/stages/s03_label_record_types/stage.py`.
**Prompt:** `corpora/arena/canonical/prompts/label_record_types_v3.md` (canonical) or domain-specific override.
**Model used:** Opus 4.6 (`temperature=0.0`, `max_tokens=128000`, batched via Anthropic Batches API).

Each record receives six axis tags:

| axis | semantics |
|---|---|
| `is_occurrence` | The record describes something that happened (a realised event). |
| `is_mechanism` | The record describes a causal mechanism (how or why something occurs). |
| `is_specification` | The record describes a specification (a stated requirement, target, or design choice). |
| `is_lesson` | The record names a lesson learned from the described situation. |
| `is_recommendation` | The record contains a forward-looking recommendation. |
| `valence` | `positive` / `negative` / `neutral` — the affective/evaluative orientation of the described event or mechanism. |

The first five axes are independently `yes` / `no`; a single record can be (and often is) several of them simultaneously.

**Why Opus 4.6 over Sonnet:** the lessons document in `corpora/arena/methodology_lessons.md` §8 reports that Sonnet 4.6 systematically under-tags `is_mechanism` by approximately 10 percentage points at corpus scale (yes-rate 39% vs Opus's 49% on a 2,000-record stratified validation sample). Hand-adjudication of 24 records sampled from the under-tag disagreement pool found Opus correct on 18/24 (75%) and Sonnet on 6/24 (25%) in the under-tag direction, with the over-tag direction tied 50-50. Extrapolated to the 90,192-record ARENA corpus, this translates to approximately 8,000 records tagged `is_mechanism=no` by Sonnet that should be `yes`. The corpus-wide canonical run is therefore Opus 4.6, accepting the higher cost in exchange for reduced false-negative rate on the mechanism axis.

**Why a verbose JSON output schema:** the lessons document §5 reports that loose-boundary axes (`is_specification` particularly) break under output-schema compression. Verbose JSON (`"is_specification": "yes"`, indented) produced 92% accuracy on a contested hand-labelled set; hybrid (full keys + `1`/`0` values, single-line) collapsed to 14%; compact (single-letter keys + `1`/`0`) recovered to 28%. Sharp-boundary axes (`is_recommendation`, `is_occurrence`) survive aggressive compression; loose-boundary axes do not. The output schema is a deliberation surface, not just a serialisation format. Extended thinking does not substitute: Sonnet on procedural multi-record tagging engages on average ~13 tokens of thinking out of a 4,000-token budget, treating the task as "no need to think". Forcing extended thinking adds sampling noise (it requires `temperature=1`) without adding deliberation.

**Configuration knobs** (per `stages.label_record_types`):
- `model`, `temperature`, `max_tokens`, `records_per_call`: model and batching.
- `input_records`, `output_dir`.

**Validation completed:** stability-vs-accuracy decoupling characterised on a contested set: Sonnet's within-model rep-pair agreement at temperature=0 was 0.980 with hand-adjudicated accuracy of 0.806; Opus's was 0.969 / 0.963. Stability is a confidence proxy, not a quality signal. The methodology lessons document §6 names this as a generalisable principle for the methodology paper.

**Validation outstanding:** the 8,000-record `is_mechanism` under-tag estimate is based on a 2,000-record stratified sample; the corpus-scale extrapolation has a confidence interval of approximately ±2,000 records.

### 4.4 s04 cluster_filter — predicate filter

**Module:** `pipeline/stages/s04_cluster_filter/stage.py`.

This stage applies a configurable predicate to the tagged records to produce the input to clustering. The default predicate is `valence == 'negative' AND (is_occurrence == 'yes' OR is_mechanism == 'yes')`. The output is a JSONL of records that pass the predicate, with each record's metadata fields joined from the source per-doc record (project name, category, etc., per `stages.cluster_filter.record_meta_fields`).

**Configuration knobs** (per `stages.cluster_filter`):
- `predicate_valence`, `predicate_axes_any_of`: the filter predicate components.
- `tags_path`, `records_path`, `events_path`: input artefacts.
- `output_path`, `output_summary`: output JSONL and summary CSV.
- `record_meta_fields`: which metadata fields to copy from each source record.

**Why this filter:** the methodology lessons document §9 articulates the design principle: in a two-stage pipeline (upstream attribute filter + downstream clustering with a recurrence threshold), the upstream filter does not have to be perfect. A `≥3-record` recurrence threshold downstream absorbs upstream false positives gracefully into singletons rather than contaminating the clustered catalogue. This relieves precision pressure on the upstream filter and means the predicate can be set to favour recall.

**Validation completed:** for ARENA, the predicate kept 25,479 of 90,192 records as candidates for clustering. Inspection of records that pass on attribute grounds but fail to cluster confirmed the design intent: macro/industry context, regulatory observations from other jurisdictions, and scene-setting paragraphs end up as singletons.

### 4.5 s05 cluster_seed — initial catalogue from a stratified sample

**Module:** `pipeline/stages/s05_cluster_seed/stage.py`.
**Prompt:** `pipeline/stages/s05_cluster_seed/prompt.md`.
**Model used:** Sonnet 4.6.

The seed stage produces an initial cluster catalogue from a stratified sample of filtered records. Stratification is by `stratification_field` (ARENA: `kb_category`; ANAO: `portfolio`) crossed with axis combinations (`occ_mech`, `mech_only`, `occ_only`); the top N stratification-field values × axis combinations × `per_cell` records produce the sample. The stage submits the sample to one Sonnet 4.6 call that asks for a cluster catalogue — each cluster a `cluster_id`, `canonical_name`, and `mechanism_signature` — that organises the sampled records by mechanism class.

**Configuration knobs** (per `stages.cluster_seed`):
- `model`, `max_tokens`, `seed`: model, output ceiling, deterministic sample seed.
- `input_path`, `output_catalogue`, `output_sample`, `output_raw`: artefact paths.
- `stratification_field`, `top_n_categories`, `axis_combos`, `per_cell`: sample design parameters.

**Why a seed stage:** the sweep stage that follows (s06) requires a starting catalogue against which records are classified. Starting from an empty catalogue would mean every batch's records initially go to Pass 2 (orphan clustering), which is more expensive and less stable than Pass 1 (classification against an existing catalogue). The seed catalogue gives the sweep a calibrated starting point.

### 4.6 s06 cluster_sweep — iterative bootstrap-merge

**Module:** `pipeline/stages/s06_cluster_sweep/stage.py`.
**Prompts:** `s06_cluster_sweep/classify_prompt.md` (Pass 1), `s06_cluster_sweep/orphan_prompt.md` (Pass 2).
**Model used:** Sonnet 4.6, batched at `batch_size=200` records per LLM call.

The sweep is the central clustering stage. It iterates over the filtered records in `batch_size`-record batches; for each batch the LLM call performs both Pass 1 and Pass 2 in a single combined response.

**Pass 1 (classify):** each record in the batch is matched against the current cluster catalogue using each cluster's `mechanism_signature` as the criterion. Records that match are assigned to existing clusters with a confidence label.

**Pass 2 (orphan cluster):** records in the batch that did not match any existing cluster (the batch's orphans) are clustered into new ≥3-record clusters with new ids, canonical names, and mechanism signatures. New clusters are appended to the catalogue.

**Pending singletons:** records that even Pass 2 cannot cluster (because the batch contains only one or two records of a particular mechanism) accumulate as pending singletons for the singleton sweep stage.

**Configuration knobs** (per `stages.cluster_sweep`):
- `model`, `max_tokens`, `batch_size`, `seed`.
- `input_path`, `seed_catalogue_path`, `output_dir`.

**Why one-shot Pass 1 + Pass 2 in a batch:** the methodology lessons document §4 reports that batched classification (Pass 1 with all 200 batch records co-presented to the model) outperforms per-record cached classification on the same task. The 2x2 falsification experiment (Arm A: batched + defensive prompt; Arm B: per-record + defensive; Arm C: per-record + neutral; Arm D: batched + neutral) produced classification rates of 140 / 107 / 156 / 176 records per 200-record batch at iteration 110. Co-presented items give the model cross-item comparison as an implicit calibration anchor; chunking strips this calibration cue and the model classifies more conservatively. This finding was contrary to the older intuition that smaller prompts produce more focused attention on each item.

**Why frozen cluster signatures during a sweep:** the methodology lessons document §10 articulates the procurement-probity invariant. When iteratively classifying records against published `mechanism_signature` criteria, the signatures must remain frozen during the sweep. Updating signatures mid-sweep retroactively alters the criteria under which existing members were admitted; this has the same shape as the procurement-probity rule that published evaluation criteria are immutable post-award. Allowed post-sweep operations are scope-preserving: merge near-duplicates, split heterogeneous clusters, demote spurious clusters (members return to the orphan pool). None of these alter the rule under which existing members were admitted. This framing is stronger than "scientific reproducibility" for institutional audiences (audit, government infrastructure) who recognise procurement probity instantly.

**Checkpointing:** each iteration writes an `iteration_NNN_summary.json` capturing the catalogue state, classification rate, orphan rate, and per-iteration cost. The sweep is fully resumable and the iteration history is auditable.

### 4.7 s07 cluster_singleton — pending-singleton reclassification

**Module:** `pipeline/stages/s07_cluster_singleton/stage.py`.
**Prompt:** `s07_cluster_singleton/classify_neutral_prompt.md`.
**Model used:** Sonnet 4.6, batched.

Pending singletons (records the sweep could not cluster because their mechanism class was sparse in any single batch) are revisited after the sweep against the now-matured catalogue. The full catalogue, having been built over the entire corpus, is dense enough that many records that were singletons mid-sweep can now be classified.

The neutral prompt design is taken from the 2x2 falsification (Arm D won at the sweep stage); the singleton stage uses the same neutral framing.

### 4.8 s08 cluster_residual — residual cohort clustering

**Module:** `pipeline/stages/s08_cluster_residual/stage.py`.
**Prompt:** `s08_cluster_residual/orphan_prompt.md`.
**Model used:** Sonnet 4.6.

Records that survive both the sweep and the singleton sweep — the residual orphans — are presented to one final Pass 2 call as a cohort. Any clusters that emerge from this final pass are appended to the catalogue. Records that still cannot cluster after this stage are recorded as terminal singletons and remain in the corpus as un-clustered records.

For the ARENA v2 substrate, this final pass added a small number of clusters and the catalogue converged at 1,141 clusters.

### 4.9 s09 parent_derive — parent-class derivation

**Module:** `pipeline/stages/s09_parent_derive/stage.py`.
**Prompt:** `pipeline/stages/s09_parent_derive/prompt.md`.
**Model used:** Opus 4.7.

The parent-derivation stage takes the converged cluster catalogue (1,141 clusters for ARENA) and asks Opus 4.7 to propose parent categories that group clusters by **mechanism class** — the kind of thing that goes wrong, not the topic or domain it goes wrong in. The prompt is explicit on this point: two clusters from different domains that fail through the same mechanism should land in the same parent; two clusters from the same domain that fail through different mechanisms should land in different parents.

The prompt also specifies:
- Emergent count (no preset number of parents).
- Tightness over breadth (prefer narrow well-defined parents over broad "or"-bundled ones).
- Honest unfit reporting (clusters that don't cleanly fit any parent return under an `unassigned` bucket with reasons).
- Mid-tail attention (don't let large clusters dominate the parent design).
- Independence of axes (parents must be distinguishable on mechanism class alone).

The output is a JSON list of parent objects with `parent_id`, `name`, `description`, `mechanism_criterion`, `exemplar_cluster_ids`, and `estimated_population`.

**Configuration knobs** (per `stages.parent_derive`):
- `model`, `max_tokens`.
- `catalogue_path`, `assignments_paths`: input cluster catalogue and member-record assignments.
- `output_json`, `output_md`, `output_raw`.

**Ensemble validation campaign:** the v1 production parent set was a single run; subsequent ensemble validation derived a 59-rep ensemble producing a canonical 70-parent set, plus a 27-parent boundary extension for parents that appeared in 40-69% of the 59 reps but cleared a tier criterion. The combined v2 extended set is the 86-parent canonical taxonomy used in the cluster→parent assignment stage. The ensemble process and tier definitions are documented under `corpora/arena/clustering_v2/closure/output/parent_derivation_clean_ensemble/`.

### 4.10 s10 parent_assign — cluster→parent assignment

**Module:** `pipeline/stages/s10_parent_assign/stage.py`.
**Prompt:** `pipeline/stages/s10_parent_assign/prompt.md`.
**Model used:** Opus 4.7.

The assignment stage takes the parent set and the cluster catalogue, and asks the model to assign every cluster to exactly one parent (or `none` if no parent fits). For each assignment, the model returns `cluster_id`, `parent_id`, `confidence` (low/medium/high), and a one-line `rationale`. The prompt explicitly instructs the model to be willing to call low-confidence or `none` rather than stretch a cluster into a parent that doesn't fit; this is an instance of the methodology lessons §11 principle that confidence should reflect fit, not ranking.

**Configuration knobs** (per `stages.parent_assign`):
- `model`, `max_tokens`.
- `catalogue_path`, `parents_path`, `output_path`, `output_meta`.

**Validation completed (multi-layer):**

A blinded re-review campaign (see `corpora/arena/clustering_v2/closure/output/parent_derivation_clean_ensemble/blinded_validation/`) executed three layers of independent validation on the cluster→parent assignments:

- **v1/v2 fixed-parent confidence-rating tests** ($0.40 total). For 91 cluster→parent pairs (5 medium-sized parents × 91 clusters), an independent Opus 4.7 reviewer received the cluster and the assigned parent only — no original confidence label, no rationale — and was asked to rate confidence using the same rubric the original assignment used. 68 of 91 (74.7%) of the resulting verdicts were "fit"; zero two-step disagreements (no high↔low). Original-high-confidence assignments showed 95.8% blinded high-high agreement; original-medium showed 66.7% mid-high agreement (the "selection ambiguity" finding).

- **v3 selection-task pilot ensemble** ($3.60). The same 91-cluster sample was put through a 10-rep ensemble with the full 86-parent panel visible and a primary + optional-secondary parent assignment task. Across reps: 73.6% of original assignments appeared in the top-2 always; 5 strong reassignment candidates emerged (original parent never in any rep's top-2); 7 unanimous disagreements (10/10 reps agree on a non-original primary). Five of the seven unanimous disagreements concentrated on the p25↔p18 boundary (Feedstock variability ↔ Material limits), confirming a single-boundary signal at ensemble scale.

- **v3 full-corpus ensemble** (~$22 batched, 120 calls). All 1,141 clusters × all 86 parents × 10 reps. Headlines: 73.5% always-in-top-2; 64.8% unanimous primary; 80 strong reassignment candidates; 94 unanimous disagreements. An 86×86 adjacency matrix was produced (heatmap and network diagram artefacts), and cross-theme bridges were identified — for example p18 functions as a hub connecting four physical-mechanism cousins; the t11↔t12 (Financial ↔ Regulatory) interface produces consistent boundary-bleed at market-design and price-signal pairs; t09↔t13 (technical-control ↔ inter-party coordination) at p38↔p70 (Interoperability ↔ Multi-party coordination overhead) shows a cascade pattern in which technical-layer interop failures propagate to coordination-layer failures.

**Validation outstanding:** the full set of 80 strong reassignment candidates and 94 unanimous disagreements have not been hand-adjudicated. A spot-check of 20 of the highest-confidence-original cases confirmed the ensemble's verdict; a complete audit would close the remaining gap.

A further documented gap (see `CLUSTER_SIGNATURE_DRIFT.md`) affects interpretation: cluster signatures were written at cluster-minting time during the sweep, not re-synthesised after membership stabilised through reclassification and the residual pass. Long-tail boundary adjacencies (≤30 events across reps) may include signature-drift artefacts; top edges (≥40 events) are robust to drift. The fix is a ~$170 batched signature re-synthesis pass plus ~$25 re-ensemble; not committed.

### 4.11 s11 theme_audit — parent audit and theme grouping

**Module:** `pipeline/stages/s11_theme_audit/stage.py`.
**Prompt:** `pipeline/stages/s11_theme_audit/prompt.md`.
**Model used:** Opus 4.7.

The theme-audit stage performs two distinct tasks in one call:

**Part A — audit the candidate parents.** For each parent the model judges:
- *Mechanism coherence* (`tight` / `mixed` / `bundled`): does the parent's definition describe a single mechanism class, or is it bundling structurally distinct mechanisms?
- *Distinctness from neighbours* (`distinct` / `overlaps_with_<pNN>`): is this parent meaningfully different from every other parent, or could it be merged?
- *Population fit* (`right` / `over-claimed` / `under-claimed`): do the actual cluster assignments to this parent reflect a real corpus pattern?
- *Verdict* (`keep` / `split` / `merge_with_<pNN>` / `drop`).
- *Missing mechanism classes*: any mechanism classes the model would expect to see in this corpus but no candidate parent represents.

**Part B — propose themes.** Group the parents into a smaller number of higher-level themes by mechanism similarity. Themes have `theme_id`, `name`, `description`, `mechanism_family`, and `parent_ids`. The prompt requires that every parent appears exactly once — either in a theme's `parent_ids` list, or in `unthemed_parents`. The number of themes is emergent.

For ARENA, the theme audit returned all 86 parents as `keep` (no merges, splits, or drops proposed) and grouped them into 16 themes with zero unthemed. The model identified four candidate missing mechanism classes for the corpus.

**Configuration knobs** (per `stages.theme_audit`):
- `model`, `max_tokens`.
- `catalogue_path`, `parents_path`, `assignments_path`, `output_path`, `output_meta`.

### 4.12 Glossary sub-pipeline (g01–g11)

The glossary sub-pipeline forks from the markdown rendering and never rejoins the failure-mode pipeline. It produces a corpus-wide term registry organised by category, sub-category, and metadata fingerprint. The 11 stages are described together because they form a tighter unit than the failure-mode stages.

**g01 regex_candidates** (deterministic) sweeps every markdown file with three regex patterns: acronyms (`\b[A-Z]{2,8}\b`, with a generic English stoplist plus a per-corpus stoplist), initialisms (multiple letter+period sequences like "U.S.A."), and title-case noun phrases (multi-word capitalised phrases with lowercase connectors like "of", "and", "the"). Output: `candidates_raw.csv` (one row per surface mention) and `candidate_frequencies.csv` (one row per unique surface). Per-corpus configuration: `markdown_dir`, `markdown_glob`, `doc_id_strategy` (`parent_name` for marker layout, `stem` for flat layout), `stoplist_path`.

**g02 ner_candidates** (deterministic, multi-process) runs spaCy NER over every markdown file. The default `--variant sm` uses `en_core_web_sm` (CPU-friendly); `--variant trf` uses `en_core_web_trf` (GPU-recommended). Default labels: ORG, PRODUCT, EVENT, FAC, WORK_OF_ART. Output: `ner_candidates.csv` and `ner_candidate_frequencies.csv` with the same shape as g01's frequency file. Per-corpus configuration: `spacy_model`, `transformer_model`, `workers`, `labels`.

**g03 normalise** (embedding-based) combines the regex and NER frequency tables, filters to surfaces with ≥`min_mentions` total occurrences, embeds each candidate surface and each catalogue string (project titles + lead organisations from the per-corpus catalogue) using `all-mpnet-base-v2`, and clusters surfaces at cosine ≥`cluster_threshold` (default 0.85). Each cluster's centroid is matched against the catalogue at threshold ≥`catalogue_match_threshold` (default 0.80). Output: `entity_index.csv` with one row per canonical entity (cluster of variants), including frequency, document coverage, primary pattern, source NER pass(es), top variants, and catalogue-match status. Per-corpus configuration: `catalogue_path`, `project_title_column`, `lead_org_column`, `embedding_model`, `min_mentions`, thresholds.

**g04 define** (LLM, Sonnet 4.6) takes the top-N catalogue-unmatched acronyms with ≥`min_unique_docs` document coverage, asks the model to produce structured glossary entries with fields `term`, `expansion`, `category`, `definition`, `context`, `notes`, `uncertainty`. The prompt is parameterised by per-corpus tokens (`{audience_persona}`, `{corpus_full_name}`, `{corpus_short_description}`, `{glossary_purpose}`, `{style_guidance}`); the same engine prompt template renders distinct prompts for ARENA and ANAO based on the configuration.

**g05 define_followups** (LLM, Sonnet 4.6) runs three modes:
- `--mode tail`: define acronyms truncated from the g04 pass.
- `--mode titlecase`: define titlecase surfaces (organisations, programmes, standards, person names, locations).
- `--mode reground`: re-ground entries g04 flagged as uncertain, using corpus snippet retrieval from per-doc records.

The tail and titlecase modes use compact-schema output (single-letter keys, hard 30-word definition cap) to maximise records-per-call and minimise truncation risk.

**g06 merge** (deterministic) combines g04 confident entries with g05 followup outputs into a single merged glossary, applying per-source provenance and overriding rules (reground replaces uncertain v1; tail and titlecase additively extend). Output: `glossary.json`, `glossary.md`, `glossary.html`.

**g07 subcategory_propose** (LLM, Sonnet 4.6) asks the model to propose 4-8 sub-categories for each large top-level category in the merged glossary (`refine_categories` config). The proposal includes sub-category name, description, and example terms. The output is reviewed before applying.

**g08 subcategory_apply** (LLM, Sonnet 4.6) applies the proposed sub-category schema to the merged glossary entries, assigning each entry in a refined category to one sub-category. Compact schema (`{t: term, s: subcategory_name}`).

**g09 metadata_fingerprint** (deterministic, no LLM) computes per-term metadata distinctiveness ratios. For each glossary term, the stage aggregates corpus mentions across configured metadata axes (`project`, `category`, `programme`, `lead_org`, `year`) and computes the observed share of each value within the term's mentions versus the corpus base rate share for that value. Distinctiveness is the ratio (observed share / base share). The catalogue is the canonical metadata source: `catalogue_path`, `catalogue_slug_column`, and `catalogue_slug_pattern` (a regex with one capture group) configure the slug-extraction; column names are domain-configurable (`catalogue_project_column`, `catalogue_category_column`, etc.). The pipeline does not use extracted insight records (per-doc JSON) as a metadata source; this was a deliberate refactor (see Section 5.4) because the catalogue carries the same metadata fields more reliably and removes a coupling between the glossary and failure-mode pipelines.

**g10 finalise** (deterministic) combines the merged glossary, sub-category assignments, and metadata fingerprints into the canonical v3 glossary artefact (`glossary_v3.{json,md,html}`).

**g11 inverse_signatures** (deterministic) produces two inverse views:
- `project_vocabularies`: per project, the glossary terms appearing at disproportionately high rates compared to the corpus base. Per-project distinctiveness signature.
- `term_top_projects`: per term, the projects where it is most distinctively concentrated. The inverse: per-term project-distinctiveness profile.

Both views are computed from the same per-term × per-project mention matrix; the inverse is taken at presentation time.

**Configuration knobs** for the glossary sub-pipeline are all under `glossary:` in `domain.yaml`, parallel to the `stages:` block. The structure is `glossary.<sub-stage>.<knob>` (e.g. `glossary.candidate.markdown_dir`, `glossary.fingerprint.catalogue_path`). The full schema is in the engine README at `pipeline/glossary/README.md`.

**Validation completed:** for ARENA, g09 reproduces 860 fingerprints; g10 reproduces 760 entries / 100 noise / 11-category distribution that the original (development-script) run produced bit-shape identically. For ANAO, the full pipeline produced 590 entries / 10 noise across 9 categories with 24 sub-categories, including ANAO-specific neighbourhoods (Defence acquisition, social welfare, Indigenous affairs) that did not appear in ARENA.

**Cross-corpus comparison:** of 760 ARENA terms and 590 ANAO terms, 69 are shared. Of those, the top categories of overlap are `location` (state codes), `organisation` (Australian government bodies), and `concept` (generic policy / finance vocabulary). Approximately 30% of overlapping terms are polysemous false friends — same acronym, materially different referents (e.g. DMO = Default Market Offer in ARENA vs Defence Materiel Organisation in ANAO; TGA = Thermogravimetric Analysis vs Therapeutic Goods Administration; AEC = Alkaline Electrolysis Cell vs Australian Electoral Commission). The cross-corpus glossary therefore exposes domain-specific polysemy that naive cross-corpus retrieval would conflate.

---

## 5. Methodology

This section articulates the cross-cutting design principles that operate across stages and that distinguish the system from a collection of corpus-specific scripts.

### 5.1 Atomic-claim substrate as foundational artefact

The pipeline treats the records produced by s01 — the 90,192 atomic claim records for ARENA — as the foundational analytical surface on which every downstream layer operates. The choice was deliberate: alternatives include paragraph-chunked retrieval (operate directly on rendered markdown), document-level summary records (one or a few records per document), or topic-modelled latent vectors. Each was rejected.

Paragraph-chunked retrieval cannot do *atomic-claim* analysis at corpus scale because atomic-claim boundaries do not follow paragraph boundaries. Tables, bullet lists, and multi-claim prose paragraphs all violate the "one paragraph = one claim" assumption. A documented worked example from `pipeline/EXTRACTION_DEFENSIBILITY.md`: a single 1,652-character HTML table of six eligibility criteria in `doc_0121` (an ARENA Information Session presentation) produced eight records — one per row, plus a meta-record synthesising the structure of the table itself, plus a content-adjacent record. Paragraph-chunked retrieval cannot produce these. Across the ARENA corpus, the average record-to-paragraph ratio is approximately 1:2 (tables and bullet lists drive this above 1:1; some narrative paragraphs produce zero records).

Document-level summary records collapse the analytical question to "what is this document about", which is what existing retrieval over full-text indexes already does. The corpus-level signal — what mechanisms recur across documents — is invisible at the document-summary granularity.

Topic-modelled latent vectors do not produce structured records that can be cited back to source. The pipeline's analytical use cases (portfolio-management briefings, audit-finding cross-referencing, methodology paper) require source citation as a first-class affordance.

The atomic-claim substrate, by contrast, supports each downstream layer cleanly: clusters are defined as sets of records sharing a mechanism; parents are defined as sets of clusters sharing a mechanism class; themes are defined as sets of parents in the same mechanism family; provenance from any layer back to a specific evidence quote in a specific page of a specific document is preserved.

The substrate carries the extraction model's voice (Section 4.1, `EXTRACTION_DEFENSIBILITY.md`). Voice operates at the rendering layer, not the conceptual layer. The substrate is voice-affected but not concept-injected. The methodology paper's strongest single claim about extraction is this voice-vs-concept decoupling: the substrate's analytical work is grounded in the same situations the source documents describe, rephrased into a consistent stylistic register, with the rephrasing layer empirically characterised.

### 5.2 Extraction-first taxonomy posture

The pipeline takes an *extraction-first* posture toward taxonomy: extraction is taxonomy-agnostic (s01 prompt deliberately asks for findings without classification), and every taxonomy-bearing layer (record-type tags, clusters, parents, themes) is a downstream pass over the already-extracted record substrate. Taxonomy revisions only require re-running the cheap labelling and clustering passes, not re-extraction.

The honest framing is **not** "bottom-up versus top-down" — both are misleading. Even when taxonomy is derived from extracted records (as the parent and theme layers are), the derivation involves a researcher (or LLM proxy) reading a sample, forming a mental model of the relevant dimensions, and articulating the structure. That is informed top-down design. True bottom-up would be unsupervised clustering with no interpretive layer, and even there the cluster names impose structure. The honest distinction is *when* the taxonomy is defined relative to extraction.

ARENA's specific posture is **hybrid**: a sample-informed, then frozen, taxonomy. Approximately 20 representative documents were read; taxonomy dimensions were articulated from the sample plus broader domain review; the taxonomy was frozen and applied at extraction. It is not growing across documents at runtime; it is not pure top-down from cold domain knowledge.

### 5.3 The legitimacy filter — recurrence threshold as downstream calibration

The clustering sweep enforces a `≥3-record` recurrence threshold for new cluster minting. This threshold is not only a filter against spurious clusters — it functions as a *legitimacy filter* on the upstream attribute predicate (s04 cluster_filter).

The argument: in a two-stage pipeline (upstream attribute filter + downstream clustering with a recurrence threshold), the upstream filter does not have to be perfect. Records that pass the upstream filter on attribute grounds but are not actually instances of the target type — for example, scene-setting paragraphs that mention a negative outcome in passing, regulatory observations from other jurisdictions cited as context, or macro/industry framings — cannot form ≥3-member clusters with each other because they describe distinct contextual observations rather than recurring mechanisms. They end up as singletons. The mechanism catalogue stays clean; the contextual observations are still preserved (in the singleton pile, readable separately).

This is the design principle articulated in `corpora/arena/methodology_lessons.md` §9. It generalises: when designing a two-stage filter pipeline, the upstream filter does not have to be perfect if a `≥N` recurrence threshold downstream absorbs false positives.

### 5.4 Engine versus configuration

The pipeline distinguishes between a domain-independent engine and per-corpus configuration. The test, articulated in CLAUDE.md, is: "if adding a new corpus requires modifying any file under `pipeline/`, that's a generalisation failure. New corpora should only add files under `domains/` and `corpora/`."

The engine includes:
- Document ingestion infrastructure (`pipeline/ingest/`), including the `BaseScraper` contract and the `marker_convert` driver.
- The extraction loop (`pipeline/extract.py`).
- The 11-stage failure-mode pipeline (`pipeline/stages/sNN_<stage>/`).
- The 11-stage glossary sub-pipeline (`pipeline/glossary/gNN_<stage>/`).
- Shared utilities (`pipeline/stages/shared/`, `pipeline/glossary/shared/`).
- The configuration loader (`pipeline/config.py`) and CLI dispatcher (`pipeline/run.py`).

Per-corpus configuration includes:
- A bespoke scraper (`domains/<corpus>/scrape.py`).
- A canonical configuration file (`domains/<corpus>/domain.yaml`).
- Per-corpus prompt overrides where domain-specific framing is needed (under `domains/<corpus>/prompts/`).
- A per-corpus stoplist for the glossary candidate sweep (`domains/<corpus>/glossary_stoplist.txt`).

Prompts in the engine use `{token}` substitution for corpus-dependent text. Each engine prompt is rendered by `DomainConfig.prompt()` with the per-corpus `prompt_tokens` block from `domain.yaml` substituted in. For example, the parent-derivation prompt uses `{audience_persona}`, `{audience_use_case}`, `{corpus_short_description}`, and `{topic_axis_examples}`; ARENA renders these as "ARENA portfolio manager" / "evaluating a current or prospective renewable energy project" / "ARENA-funded renewable energy and clean technology projects" / "project / equipment / technology / domain"; ANAO renders as "Commonwealth program manager" / "evaluating a current or prospective Commonwealth program" / "ANAO performance audits of Commonwealth programs and entities" / "agency / programme / sector".

The two corpora have distinct configurations (`domains/arena/domain.yaml` and `domains/anao/domain.yaml`) but share an engine. Adding a third corpus (e.g. PC, the Productivity Commission, currently demonstrated for marker conversion only) requires:
- A scraper in `domains/pc/scrape.py`.
- A configuration in `domains/pc/domain.yaml` with the corpus-specific paths, models, prompt_tokens, and metadata field maps.
- No engine changes.

The test was first applied to scraping (website HTML structure is too arbitrary to generalise; each domain has a bespoke scraper, fine), and has held across the failure-mode and glossary pipelines since. A recent refactor (see Section 5.4 cluster signature drift documentation) eliminated a coupling between the glossary metadata fingerprint stage and per-doc extraction records by routing fingerprint metadata through the catalogue directly; this preserves the engine-config boundary even where it would have been tempting to leak corpus-specific record-schema knowledge into the engine.

### 5.5 Distinctiveness over raw frequency

Several stages compute distinctiveness ratios rather than raw frequencies. The metadata-fingerprint stage (g09) computes per-term observed-share-vs-corpus-base across project / category / programme / lead-organisation / year axes. The inverse-signatures stage (g11) computes per-project per-term distinctiveness for both directions (project vocab; term top projects). The cluster-fingerprint analysis at the parent layer uses similar logic.

The argument: raw frequency conflates "this term/cluster is common everywhere" with "this term/cluster is concentrated here". A term mentioned 200 times across 50 projects is different from a term mentioned 200 times in 2 projects, even though both have the same raw frequency. Distinctiveness ratios separate these cases by computing the ratio of observed share (how concentrated the term is in this cohort) to base share (how common the term is in the corpus overall). A ratio of 1.0 means the term is no more concentrated in this cohort than the corpus average; a ratio of 5.0 means it is 5× as concentrated; a ratio of 0.2 means it is 5× less concentrated. The interpretation follows the same logic as TF-IDF and as distinctive-words analysis in computational linguistics.

The distinctiveness construction is corpus-agnostic. The methodology depends only on the existence of metadata axes per record / term and a sensible cohort definition; the specific axes are configured per corpus.

### 5.6 Hybrid GPU-NLP plus LLM architecture

The glossary sub-pipeline alternates between deterministic GPU-accelerated NLP (regex sweeps, spaCy NER, sentence-transformer embeddings) and LLM-based passes (definition, sub-category proposal, sub-category application, reground). The deterministic stages produce candidate sets and statistical aggregates; the LLM stages produce structured definitions, taxonomy, and disambiguation.

The design allocates work to the right tool. Candidate harvest is a recall task: regex and NER are cheap and high-recall. Catalogue cross-reference and variant collapsing are similarity tasks: sentence embeddings plus agglomerative clustering at cosine ≥0.85 are well-matched. Definition writing and sub-category proposal are conceptual tasks: LLMs are the natural choice. Metadata fingerprinting and inverse-signature computation are statistical aggregations: deterministic SQL-style queries are appropriate.

The same architectural pattern appears in the failure-mode pipeline at a coarser granularity: deterministic stages (s04 filter, s07/s08 cohort handling) bracket LLM stages (s01 extract, s03 label, s05/s06 cluster, s09–s11 taxonomy). The pipeline does not use LLMs where deterministic methods are sufficient.

### 5.7 Multi-pass LLM strategy with targeted follow-up modes

The glossary's g04 + g05 pattern — a first-pass pass over the highest-coverage candidates, plus targeted follow-up modes (tail recovery, titlecase pass, corpus-grounded reground) — is a model for how the pipeline approaches LLM tasks where one-shot is impractical and chunking degrades quality.

The first pass operates on the most informative subset (e.g. acronyms with ≥5 unique-doc coverage). Follow-up modes are designed for *specific failure modes* of the first pass: the tail mode recovers entries truncated by the model's output ceiling; the titlecase mode covers a different candidate population entirely; the reground mode revisits entries the model flagged as uncertain in the first pass, using corpus snippet retrieval to give the model the context it lacked.

This pattern is more disciplined than either "run one big pass" (high truncation risk; quality degrades on long outputs) or "run many small passes" (loss of cross-item calibration; expensive on per-call overhead). It uses one well-constrained pass for the core, plus diagnostic-driven follow-ups for the specific failure modes.

### 5.8 Layer-of-inference dependency and re-synthesis

The pipeline's four-layer hierarchy (records → clusters → parents → themes) has a layer-of-inference dependency: each layer should ideally be synthesised from the layer below *after* its membership stabilises. The pipeline correctly does this at the parent layer (parents are derived from cluster signatures after cluster assignment) and the theme layer (themes are derived from parents after parent assignment). It currently does *not* do this at the cluster signature layer: cluster signatures (canonical_name + mechanism_signature) are written when a cluster is first minted by the sweep, based on the records present in the founding batch (typically 5-10 records). As reclassification adds more records to the cluster, the signature is not updated. The signature drifts from membership.

This is a documented gap (see `CLUSTER_SIGNATURE_DRIFT.md`). The fix is a one-shot re-synthesis pass: for each cluster, give the model the full member record set and ask it to re-derive `canonical_name` and `mechanism_signature`. Cost estimate: ~$170 batched. The fix has not been committed because the v2 substrate has been in use for two months and re-synthesising would invalidate prior cluster reports. The methodology paper should disclose the gap as a §16 known limitation; the layer-of-inference principle is a methodological observation worth articulating in its own right.

---

## 6. Validation

This section names what has been done to test the pipeline, and is honest about what has not.

### 6.1 What has been validated

**Substrate voice and grounding.** The corpus-wide voice audit (`corpora/arena/clustering_v2/closure/code/17_extraction_voice_audit.py`) and the narrative-vs-evidence audit (`closure/code/18`) on the ARENA substrate. The voice audit found that the model's voice operates at the rendering layer and not the conceptual layer. The narrative-vs-evidence audit on a 50-record stratified sample found that ~96% of novel n-grams in `narrative` (not present in the record's `evidence` excerpt) are paraphrases of source content rather than invented content.

**Six-axis tagging stability vs accuracy.** A controlled pilot on the canonical 6-axis prompt with two model variants and three output schemas characterised the relationship between within-model rep-pair stability (at temperature=0) and hand-adjudicated accuracy. Sonnet's stability was 0.980 with accuracy 0.806; Opus's was 0.969 with accuracy 0.963. Stability is a confidence proxy and not a quality signal. The corpus-wide canonical labelling pass uses Opus 4.6 on this evidence.

**One-shot vs chunked classification.** The 2x2 falsification at clustering iteration 110 demonstrated batched classification (Pass 1 + Pass 2 in a single 200-record call with neutral prompt framing) classifies ~26% more records than per-record cached classification with the same neutral prompt. Co-presented items provide cross-item calibration; chunking strips this signal.

**Cluster→parent assignment quality.** The blinded validation campaign at three layers (v1/v2 fixed-parent rating, v3 selection-task pilot ensemble, v3 full-corpus 10-rep ensemble) found 73.5% of original assignments always-in-top-2 across the full-corpus ensemble; 64.8% unanimous primary; 80 strong reassignment candidates and 94 unanimous disagreements identified. The 86×86 adjacency matrix with cross-theme bridges is a derivative artefact.

**Glossary engine reproducibility on ARENA.** The deterministic stages g09 and g10 reproduce the original (development-script) outputs bit-shape identically (860 fingerprints, 760 glossary entries, 100 noise entries, 11 categories). The catalogue-only refactor (Section 5.4) eliminated a coupling without changing output shape.

**Cross-domain demonstration on ANAO.** The full glossary pipeline produced 590 entries / 10 noise / 9 categories / 24 sub-categories, including ANAO-specific neighbourhoods that do not appear in ARENA. The clustering N=100 demo produced a representative cluster catalogue and parent set on a stratified sample. Engine code was not modified between the two domains; only `domain.yaml` differs.

**Cross-corpus polysemy disclosed.** The 69-term overlap between the ARENA and ANAO glossaries includes approximately 30% polysemous false friends (DMO, TGA, AEC, etc.); this is itself a finding about cross-corpus retrieval that the glossary pipeline surfaces.

### 6.2 What has not been validated

**Formal claim-level fidelity.** No hand-labelled ground-truth comparison of extracted records against source text has been undertaken. The substrate's faithfulness rests on the voice audit, the narrative-vs-evidence audit on a 50-record sample, and the legacy v1.3 verification pass at 92.2% grounding (which used a different prompt and is not strictly comparable to the v2 substrate).

**Replicate stability of grouping at full corpus scale.** The 3-doc and 12-doc REVS replication runs characterised noise on `s02 group_events`; full-corpus replicate stability is unmeasured. A documented publishable extension (re-run twice, report Jaccard at the catalogue level) is named in `methodology_lessons.md` §16.6.

**Replicate stability of clustering at full corpus scale.** The cluster catalogue is one production run. Replicate-stability of the catalogue itself is unmeasured. The pilot-scope ensemble at 91 clusters demonstrates that the methodology converges; the full-corpus equivalent is documented as a publishable extension.

**Cluster coherence audit on the canonical 1,141.** The legacy v3p5 pipeline included a Stage F per-record fit_pct verdict (median 0.88 on its 8,311-record substrate). The canonical 1,141-cluster catalogue does not have an equivalent. Informal sampling on a small number of clusters suggests an audit would surface structural issues in 1/4 to 1/3 of large clusters; this is the highest-leverage open evidentiary gap and is named as such in `methodology_lessons.md` §16.3.

**Parent-derivation across multiple ensemble runs at corpus scale.** The 86-parent canonical taxonomy is derived from a 59-rep ensemble; the ensemble was operated on a single cluster catalogue. Re-running the ensemble on a re-clustered corpus (after the documented re-synthesis pass) is not done.

**Reassignment candidate audit.** Of the 80 strong reassignment candidates and 94 unanimous disagreements identified by the full-corpus parent-assignment ensemble, only a 20-cluster spot-check has been hand-adjudicated. A complete audit of all 174 (with overlap; the actual unique count is approximately 120) would close the assignment-quality gap.

**Cluster signature re-synthesis.** Cluster signatures are written at minting time and not re-synthesised after membership stabilises. Long-tail boundary adjacencies (≤30 events across reps in the full-corpus ensemble) may include signature-drift artefacts. The fix is documented at `CLUSTER_SIGNATURE_DRIFT.md`.

**Outputs against domain-expert ground truth.** No ARENA portfolio managers, ANAO auditors, or other domain experts have hand-reviewed the outputs end-to-end and assessed whether the parent / theme structure matches their mental model of the failure-mode space. This is the broadest outstanding validation and the one most directly relevant to claims about analytical utility.

The current state is that the pipeline produces structured, plausible outputs across two distinct corpora. The substrate is voice-affected but voice-bounded; the cluster catalogue is one defensible build, not the unique build; the parent taxonomy is internally consistent under blinded re-review with documented assignment-quality figures; the glossary outputs are reproducible bit-shape across engine refactors; the cross-domain transfer is clean (ANAO required no engine changes). What is *not* yet established is that the analytical outputs match what a domain expert would produce given the same source corpus, or that the artefacts would survive expert audit at the per-cluster or per-parent granularity.

---

## 7. Demonstration

The pipeline has been demonstrated on two corpora.

**ARENA Knowledge Bank.** Source: 1,440 publicly accessible reports from the Australian Renewable Energy Agency Knowledge Bank, plus 8 oversized documents handled separately. Categories include solar, wind, battery storage, hydrogen, bioenergy, distributed energy resources, system security, and renewables-for-industry; date range 2009–2025. End-to-end pipeline outputs:
- 90,192 atomic claim records (from s01 extract, Sonnet 4.6, ~$80 sync).
- 6-axis tags on 90,192 records (s03 label, Opus 4.6, batched).
- 1,141 clusters (s06 sweep + s07 singleton + s08 residual, Sonnet 4.6, ~$55 sync / ~$36 batched).
- 86 extended parent classes (s09 derive, Opus 4.7 ensemble; canonical 70-parent set + 16-parent boundary extension).
- 16 themes (s11 audit, Opus 4.7).
- 760-term glossary with 100 noise / 11 categories (g01–g10).
- 489-project vocabulary signatures and 760-term project-distinctiveness profiles (g11).

End-to-end provenance: any record can be traced to its document and page; any cluster's members can be enumerated; any parent's clusters can be enumerated; any theme's parents can be enumerated. The blinded validation campaign on the cluster→parent assignment is the most thoroughly characterised single layer.

**ANAO performance audits.** Source: 1,452 ANAO performance audit reports tabled 1996–2025. Categories include audited entity, portfolio (ministerial), sector, year tabled. End-to-end pipeline outputs to date:
- Document ingestion complete; 1,454 marker-rendered markdown files.
- 590-term glossary with 10 noise / 9 categories / 24 sub-categories (g01–g10), including ANAO-specific neighbourhoods (Defence acquisition, social welfare, Indigenous affairs).
- N=100 stratified-sample clustering pilot (s06 + parent derivation) producing a representative cluster catalogue and parent set.

The full-corpus failure-mode pipeline has not been run on ANAO. The glossary is end-to-end on the full corpus and required no engine modifications between corpora; only `domains/anao/domain.yaml` differs from `domains/arena/domain.yaml`.

The two demonstrations establish that the pipeline:
- Produces structured outputs at corpus scale on a 1,440-document corpus (ARENA, full pipeline).
- Produces glossary outputs at full-corpus scale on a 1,452-document corpus from a different domain with no engine changes (ANAO, glossary).
- Produces representative outputs at sample scale on a different domain (ANAO N=100 clustering pilot).

The demonstrations are not findings about ARENA or ANAO. They are evidence that the pipeline runs end-to-end without corpus-specific engine code.

---

## 8. Limitations

A reviewer evaluating the system on its merits would correctly raise the following.

**Unvalidated analytical outputs.** Section 6.2 enumerates this. The strongest single claim the pipeline could make — that the analytical outputs match what a domain expert would produce — is not yet established. The artefact is a v1 measurement instrument; published work using its outputs as evidence should disclose the un-audited status.

**Dependence on LLM behaviour at multiple stages.** The pipeline uses LLM calls at extraction (s01), event grouping (s02), tagging (s03), seed clustering (s05), the sweep (s06), singleton reclassification (s07), residual clustering (s08), parent derivation (s09), parent assignment (s10), theme audit (s11), glossary definition (g04, g05), and sub-category proposal/application (g07, g08). Model behaviour is not fully reproducible; specific findings about model behaviour (the Sonnet `is_mechanism` under-tag, the schema-compression effect on loose-boundary axes) are stage-specific calibration evidence, not stage-specific guarantees.

**Mechanism-level causal inference is shallow.** The cluster signatures and parent definitions describe causal mechanisms (the kind of thing that goes wrong, how it goes wrong, what it leads to), but the inference is at the level of *naming* the mechanism, not at the level of formal causal modelling. Cross-cluster relationships visible in the adjacency matrix are co-occurrence patterns in the assignment data, not formally identified causal pathways.

**Concentration-by-counterparty artefacts.** Where a single counterparty (a research institution, a major proponent, a regulator) accounts for a disproportionate share of records on a given mechanism, the cluster's signature can be skewed by that counterparty's framing. The cross-project diversity validation on the ARENA workhorse clusters (mean 17.8 projects per cluster, mean 6.9 categories per cluster) addresses the average case but does not preclude per-cluster concentration artefacts.

**Cross-domain validation is partial.** The ANAO demonstration shows engine-level transfer (glossary at full corpus, clustering at sample scale). It does not show that ANAO-derived parents and themes match what an ANAO-domain expert would produce. The ARENA full pipeline is the only end-to-end run; cross-corpus convergent-validity arguments rest on partial data.

**Cluster signatures drift from membership.** Cluster signatures are written at minting time; reclassified records added later do not update the signature. Long-tail boundary adjacencies in the parent-assignment ensemble may include drift artefacts. Documented at `CLUSTER_SIGNATURE_DRIFT.md`.

**Single-rep production at corpus scale.** The 1,141-cluster catalogue, the corpus-wide event grouping, and the parent assignment are each one production run. Replicate-stability at corpus scale is unmeasured for the first two; the parent assignment has been validated with a 10-rep ensemble that is bounded by the cluster signature drift caveat.

**Output schema design is a free parameter the system depends on.** The schema-compression finding (Section 4.3) shows that loose-boundary axes break under compression. The system's choice of verbose JSON for the labelling stage is calibrated, but any future schema redesign must re-validate.

**Polysemy is detected but not resolved across corpora.** The cross-corpus glossary surfaces polysemous false friends (DMO, TGA, AEC). The pipeline does not currently resolve these into separate entries with corpus-specific senses; the polysemy is exposed but not handled.

---

## 9. Future work

Each item below corresponds to a documented gap with a costed extension.

**Formal validation against domain-expert ground truth.** The single largest evidentiary gap. For each of the 1,141 clusters in ARENA (or a stratified sample), a domain expert reviews the canonical name, mechanism signature, and a sample of member records and verdicts the cluster as `coherent` / `partial` / `incoherent` with a brief rationale. Equivalent for the parent and theme layers. Approximately 100-300 hand-labels closes the largest open gap. No incremental API spend; researcher time only.

**Cluster signature re-synthesis.** Re-derive each cluster's `canonical_name` and `mechanism_signature` from the full member set after the substrate stabilises. Approximately $170 batched. Then re-run the parent-assignment ensemble (~$25 batched) to validate that boundary-mapping findings hold under the tightened signatures.

**Replicate-stability characterisation at corpus scale.** Re-run the production failure-mode pipeline twice end-to-end and compute Jaccard at the cluster catalogue level, the parent set level, and the per-record cluster assignment level. Approximately $300-500 sync, $150-250 batched.

**Full-corpus parent-assignment audit.** Hand-adjudicate all 80 strong reassignment candidates and 94 unanimous disagreements (approximately 120 unique cases) from the parent-assignment ensemble. Researcher time only.

**Cluster-layer boundary mapping.** Apply the parent-assignment ensemble methodology at the cluster→cluster proximity level — identifying for each cluster its nearest mechanism cousins. Produces a 1,141×1,141 cluster-adjacency matrix supporting merge analysis and cluster-report neighbourhood definition. Approximately $10-20 batched.

**Cross-corpus convergent-validity testing.** Run the full failure-mode pipeline on ANAO at corpus scale and assess whether ANAO-derived parents and themes preserve the structural shape of the ARENA-derived equivalents in the regions where the corpora overlap (regulatory, financial, coordination, technical). The cross-corpus glossary's polysemy detection is a small downpayment on this.

**Filter-chain calibration against ground truth.** Per `methodology_lessons.md` §16.7, several filter-chain reliability values feeding the substrate's traceable-uncertainty framing are placeholders. ~300 hand-tags spread across the un-calibrated filters (Pass 3 realisation, Pass 2 parent assignment, Stage F cluster membership). No API spend; researcher time only.

**Methodological hardening of relationship classifications.** The 6-axis tagging schema is independently calibrated per axis. Cross-axis relationships (e.g. records that are both `is_mechanism` and `is_lesson`, or both `is_occurrence` and negative-valence) are emergent from the conjunction of axis decisions and have not been validated as a coherent multi-axis substrate.

**Application to additional corpora.** APH (Australian parliamentary committee reports), PC (Productivity Commission), and Royal Commissions are documented as candidate next corpora. APH ingestion is in progress (~1,650 PDFs converted, ~11,000 in discovery); the engine and configuration are ready. Each new corpus deployment is a small-cost test of the engine-config separation.

**Schema-compression study at axis level.** The 92% / 14% / 28% / 67% accuracy result on `is_specification` under different output schemas is one stage's evidence. A systematic study across all six axes and two model variants would calibrate the cost-quality trade-off.

**Cluster co-occurrence and event matching.** The current pipeline does not match cross-document events (the s02 stage is per-document only). A cluster-cluster co-occurrence analysis at the document level (clusters whose member records frequently co-occur in the same document) is a downstream stage that the substrate supports but does not currently run.

---

## 10. Conclusion

The pipeline takes PDF document corpora and produces a four-layer structured representation: atomic claim records, mechanism-coherent clusters, parent mechanism classes, and themes — together with a corpus glossary and metadata fingerprints in a parallel sub-pipeline. The architecture separates a domain-independent engine from per-corpus configuration. The system has been demonstrated end-to-end on the ARENA Knowledge Bank (1,440 documents, full pipeline) and partially on the ANAO performance-audit corpus (1,452 documents, glossary at full scale, clustering at sample scale). The methodological design choices — atomic-claim substrate over paragraph-chunked retrieval; extraction-first taxonomy posture over a-priori classification; downstream recurrence threshold as legitimacy filter; engine versus per-corpus configuration; distinctiveness over raw frequency; hybrid GPU-NLP plus LLM architecture; multi-pass LLM strategy with targeted follow-up modes; layer-of-inference dependency in the synthesis hierarchy — are documented in the development notes and substantiated by stage-specific empirical findings.

What has been validated within the pipeline (substrate voice, six-axis tagging accuracy, one-shot vs chunked classification, cluster→parent assignment quality, glossary engine reproducibility, cross-domain engine transfer) is named alongside what has not (formal claim-level fidelity, replicate stability at corpus scale, cluster coherence audit, parent-assignment audit, expert ground-truth validation). The current state of the system is a v1 measurement instrument with named, bounded uncertainty; the items in Section 9 are the publishable extensions that would convert it into a research instrument with formally validated uncertainty.
