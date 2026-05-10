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

The methodology has been proven on the ARENA Knowledge Bank (1,440 documents, 16,931
records) and is being extended to ANAO performance audit reports (1,450 documents) as
proof of generalisation. All ANAO data and scripts live under `corpora/anao/` — this
is the canonical location; do not reach into any sibling `~/ANAO/` tree.

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
  the v1 grave prompt (symlink to `domains/arena/prompts/extract.md`), the
  90,192-record extraction output, and the grave-prompt evolution narrative
  (the systematic A→B→C→D→D'→E→E2→E3 campaign that produced the prompt).
- `corpora/arena/canonical/` — post-extraction pipeline (per-doc grouping →
  6-axis Opus 4.6 record-type tagging → v2 clustering → closure). Code is
  symlinks to `pipeline/`; the v3 labelling prompt is now at
  `canonical/prompts/label_record_types_v3.md`. Canonical-decision narrative
  lives in `canonical/narrative/runs/` (8 dated test-run snapshots).
- `corpora/arena/legacy/` — the older 6-stage failure-mode pipeline (8,311
  records / 660 clusters / 9 themes / 46 parents) plus the interactive HTML
  navigator. Self-contained; superseded `pipeline/*.py` scripts are *copied*
  here so the legacy pipeline remains runnable in isolation.

The dead-code modules at `pipeline/event_type.py` and `pipeline/label_axes.py`
are kept in `pipeline/` until a follow-up audit verifies safe deletion. They
are also copied under `legacy/code/pipeline/`.

## Repository layout

```
broadlearnings/
├── CLAUDE.md                          — this file
├── pipeline/                          — generalised extraction framework (ENGINE)
│   ├── __init__.py
│   ├── run.py                         — CLI: python -m pipeline.run --domain <name> --step <step>
│   ├── ingest/                        — document ingestion sub-pipeline
│   │   ├── __init__.py                — CLI: python -m pipeline.ingest --domain <name> --phase <phase>
│   │   ├── base.py                    — BaseScraper + DocumentRecord contract
│   │   ├── checklist.py               — 7-item scraper validation
│   │   └── convert.py                 — PDF/DOCX → structured markdown
│   ├── config.py                      — DomainConfig loader
│   ├── extract.py                     — per-document insight extraction via Anthropic API
│   ├── event_type.py                  — classify event_type and consequence_level
│   ├── verify.py                      — QA verification against source documents
│   ├── clean.py                       — Tier 1+2 keyword/remap cleaning
│   ├── reconcile.py                   — Tier 3 LLM reconciliation of contested fields
│   ├── synthesise.py                  — project-level event synthesis
│   ├── discover.py                    — failure archetype discovery per category
│   ├── classify.py                    — failure archetype classification
│   ├── matrix.py                      — archetype × category cross-reference matrix
│   ├── prompts/                       — prompt templates (domain-agnostic)
│   └── utils/
├── domains/                           — per-domain configuration (CONFIG)
│   ├── anao/                          — ANAO Performance Audits
│   │   ├── domain.yaml                — settings (estimated_count, rate_limit, models)
│   │   └── scrape.py                  — paginated listing scraper
│   ├── arena/                         — ARENA Knowledge Bank
│   │   ├── domain.yaml                — settings + extraction config
│   │   ├── scrape.py                  — CSV catalogue + per-page PDF discovery
│   │   ├── enums.yaml, category_map.yaml, etc. — taxonomy and cleaning rules
│   │   └── prompts/domain_context.md  — domain description for prompt injection
│   ├── pc/                            — Productivity Commission
│   │   ├── domain.yaml
│   │   └── scrape.py                  — sitemap-based discovery
│   └── rc/                            — Royal Commissions
│       ├── domain.yaml
│       └── scrape.py                  — central document library scraper
├── corpora/                           — runtime output (gitignored)
│   ├── <domain>/pdfs/                 — downloaded documents
│   ├── <domain>/markdown/             — converted markdown
│   └── <domain>/tables/               — extracted table CSVs
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

### ARENA corpus (complete)
- **Source:** 1,440 regular + 8 oversized documents from ARENA Knowledge Bank
- **Extraction:** 16,931 records, QA verified (92.2% grounding, 89.6% classification)
- **Taxonomy:** v2.0 (14 arena_categories, 3 activity_types, 10 proponent_types)
- **Failure archetypes:** 241 canonical archetypes across 3,136 classified events
- **Archetype index:** denormalised join from archetype → event → source record
- **RAG:** indexed in semantic search layer
- **Dashboard:** deployed to root@85.155.188.202
- **Original repo:** ~/ARENA/ (pipeline code + data, to be migrated)
- **Cost:** ~$80 total (extraction + QA + reconciliation + matching)

### ANAO corpus (in progress)
- **Source:** 1,452 performance audit markdown files in `corpora/anao/markdown/`
- **Size:** median 169k chars, max 867k, total 250MB
- **Structure:** highly consistent template across 30 years (1996-2025)
- **Approach:** two-pass (free-form extraction, then derived taxonomy)
- **Pre-processing:** regex parser (`corpora/anao/scripts/03_parse_structure.py`) for
  metadata, recommendations, entity responses, paragraph segmentation, boilerplate
  stripping (85-90% deterministic extraction). Current run yields 32,617 summary
  paragraphs across 1,086 files plus 219,409 chapter paragraphs.
- **Estimated cost:** ~$200-250 for pass 1, ~$5-10 for classification passes
- **RAG:** indexed in semantic search layer
- **Status:** structural parser built and validated; follow-up passes TBD

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
