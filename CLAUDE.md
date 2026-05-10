# Broad Learnings — Knowledge Extraction Pipeline

## Standing instructions

- **After every code modification, create a git commit** — stage the changed files and commit with a concise message describing what changed and why.
- **Do NOT trigger API calls without explicit instruction** — always check existing outputs first. Give honest cost estimates before large API runs.
- **Never cap `max_tokens` below the model's ceiling on any generative task** — set `max_tokens` to the model's maximum (e.g. 128000 for Opus 4.6 and Sonnet 4.6). Truncated output wastes the whole call: you pay for the input and the partial output, get nothing usable, and still have to re-run. The cost of occasional over-allocation is trivial compared to the cost of a single wasted call. This applies to structured JSON/YAML output, clustering, synthesis, extraction, and any task where the model decides how long its response needs to be. Constraining output length almost never saves money and frequently costs it.
- **Never use `project_name` for grouping records** — use the canonical project identifier from the metadata catalogue (e.g. `kb_associated_project` for ARENA).
- **All long-running scripts must emit verbose progress output** so Jeff can monitor live. Use `print(..., flush=True)` (or `python3 -u`), emit a heartbeat line every N items / every ~30 s with current count, rate, and ETA, and never pipe through `tail` for backgrounded runs. Silent multi-minute runs are unmonitorable. Applies to extraction loops, embedding passes, clustering, validation — anything that takes >30 seconds.

---

## What this project is

A generalised pipeline for extracting structured knowledge from government document
corpora. The pipeline takes a corpus of PDFs (converted to markdown) and a human-written
domain configuration, and produces a queryable registry of atomic insight records.

The methodology has been proven on the ARENA Knowledge Bank (1,440 documents). The
v3 substrate produced 90,192 atomic records → 1,141 mechanism clusters → 86 canonical
parents → 16 themes. (The earlier v1 produced 16,931 archetype-classified records;
v1 outputs are preserved at `corpora/arena/legacy/`.) The methodology has been
extended to ANAO performance audit reports (1,452 documents) as proof of
generalisation; an N=100 stratified demo run has produced 4,617 records, 207
clusters, and 50 parents. All ANAO data and scripts live under `corpora/anao/` —
this is the canonical location; do not reach into any sibling `~/ANAO/` tree.

The full methodology writeup lives at `pipeline_methods.md` (root). A public-facing
mirror of the pipeline + ARENA configuration + methods paper is published at
`https://github.com/jeffzda/Corpora_Insights` (private), with GPG-signed commits and
an OpenTimestamps proof of HEAD anchored to the Bitcoin blockchain (see
`timestamps/`). Use signed commits going forward (the local key is configured;
fingerprint `64E0128D...671FB0ECF38C06BB`, UID `mail@jeffcumpston.com`).

The owner (Jeff) is starting as a portfolio manager at ARENA and plans to pursue an adjunct
position at ANU (ICEDS) to publish on the methodology. Broad Learnings is the company
entity. The pipeline and ANAO dataset are owned by Broad Learnings. ARENA derivative
data will be licensed to ARENA in perpetuity with a licence back to ANU for research.

---

## Generalisation boundary: engine vs. config

The pipeline's IP value depends on a clean separation between the **engine** (generic
code) and the **domain config** (corpus-specific settings). This distinction must be
maintained rigorously — if domain-specific logic leaks into the engine, the pipeline
becomes a collection of bespoke scripts rather than reusable IP.

**Engine (generic, domain-agnostic code):**
- Document ingestion: BaseScraper contract, download/resume, PDF→markdown conversion
- Extraction loop: chunking, LLM calls, structured output parsing, deduplication
- QA verification: check extracted records against source text
- Taxonomy machinery: informed taxonomy derivation from extracted records, or predefined taxonomy application
- Archetype discovery: clustering similar insights across documents
- State management, checkpointing, cost tracking

**Domain config (per-corpus, lives in `domains/<name>/`):**
- `scrape.py` — bespoke scraping script (websites are too varied to generalise)
- `domain.yaml` — model selection, thresholds, field mappings
- Prompt templates — what to extract and what shape the output takes
- Schema definitions — field names, enum values, taxonomy structure
- Cleaning/remap rules — domain-specific data quality fixes

**The test:** if adding a new corpus requires modifying any file under `pipeline/`,
that's a generalisation failure. New corpora should only add files under `domains/`
and `corpora/`. The exception is genuine capability gaps (e.g. a new chunking
strategy), which should be added as a generic option selectable via config, not as
a domain-specific code path.

Note: scraping was the first place this distinction was tested. Website HTML structure
is too arbitrary to generalise, so each domain has a bespoke `scrape.py`. This is
fine — scraping is config, not engine. The extraction/analysis pipeline is where
generalisation actually matters for the IP argument.

---

## ARENA pipeline layout (post-reorg, 2026-05-04)

The ARENA corpus is organised into three top-level subfolders that separate
**shared infrastructure**, the **canonical post-extraction pipeline**, and the
**legacy 6-stage failure-mode pipeline** that has been preserved alongside
canonical work. See `corpora/arena/PIPELINES.md` for the overarching narrative
and `corpora/arena/methodology_lessons.md` for cross-cutting findings.

- `corpora/arena/shared/` — extraction code (symlink to `pipeline/extract.py`),
  the 90,192-record extraction output, and the grave-prompt evolution
  narrative (the systematic A→B→C→D→D'→E→E2→E3 campaign that produced the
  canonical prompt). The grave prompt itself now lives at
  `pipeline/prompts/extract.md` — domain-agnostic, no per-corpus copy.
- `corpora/arena/canonical/` — post-extraction pipeline (per-doc grouping →
  6-axis Opus 4.6 record-type tagging → v2 clustering → closure). Code is
  symlinks to `pipeline/`; the v3 labelling prompt is at
  `canonical/prompts/label_record_types_v3.md`. Canonical-decision narrative
  lives in `canonical/narrative/runs/` (8 dated test-run snapshots).
- `corpora/arena/clustering_v2/closure/` — parent derivation (59-rep ensemble),
  parent assignment, theme audit, and boundary-mapping ensemble (86×86
  adjacency, 10-rep blinded validation). Output at
  `output/parent_derivation_clean_ensemble/blinded_validation/`.
- `corpora/arena/legacy/` — the older 6-stage failure-mode pipeline (8,311
  records / 660 clusters / 9 themes / 46 parents) plus the interactive HTML
  navigator. Self-contained; superseded `pipeline/*.py` scripts are *copied*
  here so the legacy pipeline remains runnable in isolation.

The dead-code modules at `pipeline/event_type.py` and `pipeline/label_axes.py`
are kept in `pipeline/` until a follow-up audit verifies safe deletion. They
are also copied under `legacy/code/pipeline/`.

## Canonical 11-stage pipeline (post-2026-05-04 consolidation)

The generalised engine lives at `pipeline/stages/sNN_<stage>/stage.py` plus
co-located prompt templates. Stages: s01_extract, s02_group_events,
s03_label_record_types, s04_cluster_filter, s05_cluster_seed, s06_cluster_sweep,
s07_cluster_singleton, s08_cluster_residual, s09_parent_derive, s10_parent_assign,
s11_theme_audit. Glossary build is a parallel sub-pipeline at
`pipeline/glossary/g01..g11/`. Per-corpus configuration sits in
`domains/<corpus>/domain.yaml` (with `prompt_tokens` and `stages` blocks);
extraction prompt is read from `pipeline/prompts/extract.md`.

The original per-corpus scripts that produced ARENA v3 and ANAO N=100 are
preserved at `pipeline/development/<corpus>_<context>/` (95 .py + 123 .md
across 6 subfolders) for paper-trail purposes. The methodology decisions
documented there ground the methods paper at `pipeline_methods.md`.

## Repository layout

```
broadlearnings/
├── CLAUDE.md                          — this file
├── pipeline_methods.md                — full methodology writeup (14k words)
├── pipeline/                          — generalised extraction framework (ENGINE)
│   ├── __init__.py
│   ├── run.py                         — CLI: python -m pipeline.run --domain <name> --step <step>
│   ├── config.py                      — DomainConfig loader (prompt_tokens + stages blocks)
│   ├── ingest/                        — document ingestion sub-pipeline
│   │   ├── __init__.py                — CLI: python -m pipeline.ingest --domain <name> --phase <phase>
│   │   ├── base.py                    — BaseScraper + DocumentRecord contract
│   │   ├── checklist.py               — 7-item scraper validation
│   │   └── marker_convert.py          — PDF → structured markdown via marker_single
│   ├── stages/                        — canonical 11-stage pipeline
│   │   ├── shared/                    — stream + parse helpers
│   │   ├── s01_extract/               — atomic record extraction (grave prompt)
│   │   ├── s02_group_events/          — per-document event grouping
│   │   ├── s03_label_record_types/    — 6-axis Opus 4.6 multi-label tagging
│   │   ├── s04_cluster_filter/        — predicate filter (negative + occurrence/mechanism)
│   │   ├── s05_cluster_seed/          — stratified-sample seed clustering
│   │   ├── s06_cluster_sweep/         — corpus-wide classify + orphan reconciliation
│   │   ├── s07_cluster_singleton/     — neutral-prompt singleton sweep
│   │   ├── s08_cluster_residual/      — residual-orphan clustering
│   │   ├── s09_parent_derive/         — deliberation-rich 59-rep parent ensemble
│   │   ├── s10_parent_assign/         — cluster→parent assignment + boundary mapping
│   │   └── s11_theme_audit/           — single-call theme grouping (16 themes)
│   ├── glossary/                      — parallel glossary sub-pipeline (g01..g11)
│   ├── development/                   — preserved per-corpus scripts + paper trail
│   │   ├── arena_canonical/           — original ARENA canonical scripts + narrative
│   │   ├── arena_canonical_pilot/     — record-type prompt evolution
│   │   ├── arena_clustering_v2/       — original v2 clustering scripts + notes
│   │   ├── arena_closure/             — parent/theme/boundary-mapping work + writeups
│   │   ├── arena_glossary/            — original glossary scripts + session writeups
│   │   └── anao_n100_demo/            — ANAO N=100 demo scripts
│   ├── prompts/                       — domain-agnostic prompt templates
│   ├── chunk.py, rag.py               — semantic-search-layer (RAG) helpers
│   ├── extract.py, group_events.py, label_record_types.py — earlier flat-layout
│   │                                    drivers; canonical engine is in stages/
│   └── utils/
├── domains/                           — per-domain configuration (CONFIG)
│   ├── anao/                          — ANAO Performance Audits
│   ├── arena/                         — ARENA Knowledge Bank
│   ├── aph/                           — APH Committee Reports (ingestion in progress)
│   ├── leg/                           — Legislation
│   ├── pc/                            — Productivity Commission (RAG only)
│   └── rc/                            — Royal Commissions
├── corpora/                           — runtime output (gitignored)
│   ├── <domain>/pdfs/                 — downloaded documents
│   ├── <domain>/markdown/             — converted markdown
│   └── <domain>/tables/               — extracted table CSVs
├── timestamps/                        — GPG public key + OpenTimestamps proofs
│   ├── HEADS_<utc>.txt                — HEAD snapshot for evidence anchor
│   ├── HEADS_<utc>.txt.ots            — OpenTimestamps proof file
│   └── jeffzda_pubkey.asc             — GPG public key (mail@jeffcumpston.com)
└── docs/                              — methodology documentation
```

---

## Pipeline architecture

### Phase 0: Corpus characterisation (to build)

Before extraction, profile the corpus to determine document structure:
- Stratified sampling across metadata dimensions (year, entity, category, size)
- Structural analysis: heading hierarchy, numbered sections, repeating patterns
- Output: structure profile per metadata-defined clump
- Determines extraction path: deterministic parsing vs LLM extraction vs hybrid

### Phase 1: Pre-process

- Parse document structure (if structured), strip boilerplate
- Join to metadata catalogue CSV
- Route each document to appropriate extraction path

### Phase 2: Extract

- **Structured path** (e.g. ANAO): deterministic parser extracts atomic records
  (recommendations, findings), LLM enriches only where synthesis needed
- **Unstructured path** (e.g. ARENA): LLM identifies and extracts atomic records
- Output: atomic insight records with consistent metadata envelope

### Phase 3: Enrich

- Taxonomy derivation: design informed taxonomy from a sample of extracted records
- Classification: assign taxonomy labels to records as a separate labelling pass
- QA verification: verify records against source documents
- Failure archetype discovery and classification

### Domain configuration

Each corpus requires a human-written domain config that specifies:
- What the corpus is and what we care about (domain_context.md)
- `scrape.py` — bespoke scraping script (inherits from BaseScraper)
- `domain.yaml` — model selection per pipeline step, thresholds, field mappings
- Prompt templates — what to extract (schema) and domain context
- Enum values (if taxonomy already defined) or empty (if taxonomy will be derived post-extraction)

---

## Two extraction approaches

**Taxonomy-first (legacy ARENA approach):** taxonomy defined upfront, records
classified during extraction. Faster but couples extraction to taxonomy — the
model's attention is shaped by the taxonomy categories, potentially biasing which
observations get extracted. Taxonomy revisions require re-extraction.

**Extraction-first (canonical approach):** taxonomy-agnostic extraction produces
pure factual records (pass 1), an informed taxonomy is designed from a sample of
those records (pass 2), taxonomy labels are applied as a separate classification
pass (pass 3). More expensive initially but decouples extraction from taxonomy —
taxonomy revisions only require re-running the cheap labelling pass, not
re-extraction. This is the approach the generalised pipeline now implements.

Note: "extraction-first" is not "bottom-up." The taxonomy is still designed by a
researcher (or LLM acting as proxy) who reads records and makes interpretive
judgments about useful dimensions. That's informed top-down design. The key
distinction is *when* the taxonomy is defined relative to extraction, not *how*
it's derived.

---

## Two output layers

The pipeline produces two distinct output layers. They serve different purposes
and should not be conflated.

**Semantic search layer (RAG):** markdown documents are chunked (`pipeline/chunk.py`
for structure-aware, `pipeline/rag.py` for indexing), embedded, and stored in
ChromaDB for cross-corpus retrieval. Every corpus participates in this layer once
its PDFs are converted to markdown. Chunks are indexing units — they carry
positional metadata (paragraph ID, chapter, section, page) but no analytical
enrichment. Currently indexed: ARENA, ANAO, PC (~3,100 documents).

**Taxonomy/insights layer:** extracted atomic records (findings, recommendations,
events) enriched with taxonomy labels, QA verification, archetype classification.
This is the analytical dataset that supports the research methodology — pattern
matrices, archetype discovery, cross-document synthesis. Only corpora that have
been through the extraction pipeline participate. Currently: ARENA (16,931
records), ANAO (in progress). Not every corpus needs this layer — it depends on
whether taxonomy-level analysis is the goal.

---

## Current state

### ARENA corpus
- **Source:** 1,440 regular + 8 oversized documents from ARENA Knowledge Bank
- **v3 substrate (canonical):** 90,192 atomic records → 1,141 mechanism clusters
  → 86 canonical parents (subset of 126 from a 59-rep deliberation-rich Opus 4.7
  ensemble) → 16 themes. Boundary-mapping ensemble validated at 73.5%
  ≥top-2 stability across 10 reps; blinded re-review of cluster→parent
  assignments at 93.8% high-high agreement.
- **v3 cost:** ~$335 total (tagging $141, dedup $121, clustering ~$73, parent
  derivation campaign $106, closure substrate $4.59).
- **v1 (legacy, preserved):** 16,931 records, QA verified (92.2% grounding,
  89.6% classification); 241 canonical archetypes across 3,136 classified events;
  v1 cost ~$80. Outputs preserved at `corpora/arena/legacy/`.
- **Glossary:** 503 project signatures; 1,141-class glossary catalogue.
- **RAG:** indexed in semantic search layer.

### ANAO corpus
- **Source:** 1,452 performance audit markdown files in `corpora/anao/markdown/`
- **Size:** median 169k chars, max 867k, total 250MB
- **Structure:** highly consistent template across 30 years (1996-2025)
- **N=100 stratified demo (complete, 2026-05-06):** 4,617 atomic records,
  4,483 events, 207 mechanism clusters, 50 parents (single Opus 4.7 call, $0.41).
  Cross-corpus parent-overlap audit identifies 9 cleanly-shared mechanism classes
  with ARENA. The pipeline reproduced end-to-end with token-substitution-only
  config changes — no engine modification required. This is the load-bearing
  evidence for the methodology's generalisability claim.
- **Pre-processing:** regex parser (`corpora/anao/scripts/03_parse_structure.py`)
  yields 32,617 summary paragraphs across 1,086 files plus 219,409 chapter
  paragraphs (85-90% deterministic extraction).
- **Full-corpus extraction:** estimated $200-250 for pass 1; not yet committed.
- **RAG:** indexed in semantic search layer.

### PC corpus (semantic search only)
- **Source:** ~1,500 Productivity Commission documents in `corpora/pc/markdown/`
- **RAG:** indexed in semantic search layer
- **Extraction:** not planned — test corpus for scraper validation, not pursuing
  taxonomy work

### APH corpus (ingestion in progress)
- **Source:** committee reports from Senate, House, and Joint committees (38th–48th
  parliaments, 1996–present). ~1,650 PDFs from OTD API already converted to
  markdown; discovery run in progress finding ~11,000 additional report PDFs from
  committee web pages.
- **Chunking:** structure-aware chunker built (`pipeline/chunk.py`). 819/1,648
  files use paragraph-level chunking (chapter.paragraph IDs); 829 use fallback.
  272k chunks from current files, 173k numbered paragraphs, 5k recommendations.
- **RAG:** not yet indexed — pending completion of PDF download and conversion
- **Extraction:** TBD

---

## Key technical decisions

- **Prompt templates use two-pass rendering:** `{single_braces}` for domain defaults
  filled at config load, `{{double_braces}}` for runtime placeholders
- **Each domain specifies models per step:** Sonnet for extraction/discovery/synthesis,
  Haiku for classification/reconciliation/verification
- **Metadata always comes from the catalogue CSV** — not model-inferred
- **Confidence semantics:** classification confidence reflects how well the archetype
  DESCRIBES the event, not ranking against alternatives
- **Archetype granularity:** defined by the action boundary — specific enough that
  mitigation is the same for all events, general enough to have multiple instances

---

## Hardware

Jeff's machine: 5070Ti 16GB + 9950x. Can run local inference for classification tasks.
