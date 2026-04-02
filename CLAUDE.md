# ARENA Delivery Registry — Claude Context

## Standing instructions

- **After every code modification, create a git commit** — stage the changed files and commit with a concise message describing what changed and why.

This project extracts structured delivery insight records from 1,440 ARENA Knowledge Bank PDFs
using the Anthropic API, producing a cleaned, harmonised registry for reference-class analysis
and an interactive dashboard.

**Current status: v2 pipeline complete + QA verified + rechecked + project matching done +
taxonomy v2.0 stamped. 16,931 records from 1,440 documents (+ 8 oversized). QA: 92.2%
confirmed grounding, 89.6% classification ok. 499 ARENA projects covered (64.9%).
Taxonomy v2.0: arena_category (14 values, deterministic), activity_type (3 values,
deterministic), is_consortium flag, proponent_type reclassified (10 values).
Dashboard deployed to root@85.155.188.202 (/var/www/arena/).**

---

## Context and intent

The owner is joining ARENA as a portfolio manager shortly. The dashboard is for personal use
initially — to surface insights casually in meetings when relevant, not to be formally presented.
ARENA is "looking into" AI KB analysis itself but is likely 2–3 years away from anything
comparable. Do not mention this project proactively; let it emerge naturally.

---

## Repository layout

```
ARENA/
├── PIPELINE.md                              — original pipeline docs (Step 3 now superseded by 03b)
├── CLAUDE.md                                — this file
├── all_agent_groups_v2.json                 — 150 groups used for the v1 extraction run
├── arena-kb-export_1772889492.csv           — ARENA KB catalogue (1,548 entries)
├── arena-projects-export_1772932404.csv     — full ARENA project portfolio (769 projects)
├── manifest.csv                             — PDF download manifest (1,546 rows)
├── markdown/all/*.md                        — 1,440 markdown files converted from PDFs
├── pdfs/                                    — raw downloaded PDFs
├── scripts/
│   ├── 03_extract_registry.py               — SUPERSEDED: grouped extraction (v1 run)
│   ├── 03b_extract_registry_per_doc.py      — per-document extraction (v2 pipeline)
│   ├── 03c_extract_oversized.py             — chunked extraction for 8 oversized docs (>600k chars)
│   ├── 04_consolidate_registry.py           — merge + fingerprint dedup (v1 only)
│   ├── 04b_verify_extractions.py            — QA verification (grounding + classification) via Haiku batch
│   ├── 04c_recheck_flagged.py               — re-check fabricated/unsupported QA verdicts with wider window
│   ├── 04c_dedup_within_project.py          — within-project dedup → per_project/ + registry_deduped.yaml
│   ├── 05_clean_registry.py                 — Tier 1+2 taxonomy cleaning + majority-vote
│   ├── 05b_reconcile_contested.py           — Tier 3 LLM resolution of contested fields
│   ├── 06_build_document_mapping.py         — SUPERSEDED: mapping now baked into 03b
│   ├── 07_run_analysis.py                   — SUPERSEDED for regular use: matrices now in dashboard
│   ├── fix_taxonomy_violations.py           — deterministic fix for known taxonomy violations
│   ├── match_unassigned_projects.py         — fuzzy + Haiku batch matching of unmatched project names
│   ├── stamp_recovered_docs.py              — stamp KB metadata onto per_doc YAMLs missing it
│   ├── stamp_temporal_confidence.py         — flag pre-2021 time-sensitive records
│   ├── arena_category_map.py                — taxonomy v2: category mapping + consortium reclassification
│   ├── classify_activity_type.py            — taxonomy v2: deterministic activity type from projects CSV
│   ├── stamp_taxonomy_v2.py                 — taxonomy v2: stamp new fields onto per_doc YAMLs
│   └── build_dashboard.py                   — generates insights.html from per_doc YAMLs
├── sense_check.py                           — QA spot-check against source markdown
├── pilot_100_reports/
│   ├── EXTRACTION_PROMPT.md                 — LLM extraction prompt template (v1.3, with temporal flag)
│   ├── taxonomy/ARENA_Taxonomy_v1.1.md      — v1 schema (12 core fields, superseded)
│   └── taxonomy/ARENA_Taxonomy_v2.0.md      — v2 schema (reference class framework, current)
├── insights/
│   ├── full_run/group_001.yaml … group_150.yaml   — v1 extraction outputs (DO NOT USE)
│   ├── per_doc/doc_0001.yaml … doc_1440.yaml      — v2 per-doc outputs (16,931 records)
│   ├── per_doc/doc_72001.yaml … doc_72nnn.yaml    — oversized doc outputs (8 docs, IDs 72001+)
│   ├── per_doc_qa/doc_NNNN_qa.yaml                — QA verdicts per doc (grounding + classification)
│   ├── per_doc_qa/batch_state.json                — last batch API state
│   ├── per_project/<slug>.yaml                    — canonical deduped records per project
│   ├── project_name_matches.yaml                  — fuzzy + Haiku project name match log
│   ├── registry_deduped.yaml                      — flat deduped registry (15,457 records)
│   ├── registry_deduped_clean.yaml                — after Tier 1+2 cleaning
│   ├── registry_deduped_reconciled.yaml           — after Tier 3 LLM reconciliation (use this)
│   ├── ARENA_delivery_registry_full_v3_clean.yaml — v1 final registry (superseded)
│   └── reports/                                   — analysis outputs and sense check reports
└── dashboard/
    └── insights.html                        — single-file interactive dashboard
```

---

## New per-document extraction script (03b) — key design decisions

`scripts/03b_extract_registry_per_doc.py` replaces `03_extract_registry.py`. Run this for all
future extraction work.

**Key differences from the original:**
- One API call per document (not per group of ~10)
- No per-document character truncation (full content sent)
- Documents over 600k chars handled by `03c_extract_oversized.py` instead
- 10 ID slots per document: doc N → ARENA-DLV-((N-1)*10+1) to ARENA-DLV-(N*10)
- `max_tokens` raised to 4096 (full output budget per document)
- Extraction cap raised to 10 records per document (was effectively ~2-3 due to shared budget)
- Project-level fields reconciled in post-processing (no inter-document inconsistency)
- KB metadata stamped directly onto every record — no separate mapping step needed

**Fields stamped automatically (no model inference needed):**
- `source_url` — direct KB page link (arena.gov.au/knowledge-bank/...)
- `project_page_url` — ARENA project page link
- `kb_category` — KB category
- `kb_publish_date` — publish date from KB export
- `kb_year` — year from KB export
- `kb_associated_project` — canonical ARENA project name from KB export
- `in_arena_portfolio` — bool: whether project appears in arena-projects-export CSV
- `source_page` — PDF page number where evidence_excerpt was found (via PyMuPDF)

**Project-level field reconciliation:**
After extraction, `project_type`, `project_scale_band`, and `proponent_type` are reconciled
across all records from the same document by majority vote. Split votes are recorded in
`confidence_note` with the full vote tally (e.g. "technology vendor (8/10), consortium (2/10)").
This eliminates the need for Tier 2 majority-vote cleaning for within-document consistency.

**The 8 oversized documents (handled by 03c_extract_oversized.py):**
- Australian Energy Resource Assessment 2014 (1.3M chars)
- Stocktake: Database of Renewable Energy Grid Integration Projects (1.2M chars)
- AEMO Project EDGE Final Report (1.0M chars)
- ESCRI South Australia General Project Report Phase 1 (798k chars)
- ACAP 2024 Annual Report (747k chars)
- ACAP 2022 Annual Report (639k chars)
- + 2 others
These are extracted via 150k-char chunked multi-pass with prior records passed as context.
IDs start at 72001 with 200 slots per doc. Produced ~495 records.

**Usage:**
```bash
python3 scripts/03b_extract_registry_per_doc.py                  # all documents
python3 scripts/03b_extract_registry_per_doc.py --docs 1-10      # range
python3 scripts/03b_extract_registry_per_doc.py --resume         # skip completed
python3 scripts/03b_extract_registry_per_doc.py --dry-run        # no API call
```

---

## YAML record schema (v2 — full field list, Taxonomy v2.0)

```yaml
# Extracted by model — mandatory
record_id: ARENA-DLV-NNNN
source_title: "..."
publish_date: "YYYY-MM"
project_name: "..."                 # model-inferred canonical name
what_happened: "..."                # 1-2 sentences: the delivery event (facts, not lesson)
lesson_learnt: "..."                # 1-2 sentences: transferable implication, specific enough to act on
issue_severity: none|minor|moderate|major|critical

# Extracted by model — inferred when evidence supports medium+ confidence
project_type: generation|storage|network/grid|DER/customer-side|transport electrification|
              industrial decarbonisation|manufacturing/supply chain|software/data/digital|
              enabling infrastructure|multi-technology/hybrid
project_scale_band: lab/bench|pilot|demonstration|first commercial/FOAK|
                    commercial expansion|utility/large-scale|programmatic/portfolio-level
lifecycle_phase: concept/feasibility|development/design|approvals/contracting|procurement|
                 construction/installation|commissioning/integration|operations|
                 variation/re-scope|close-out/post-project review
proponent_type: project developer|utility/energy retailer|network business|
                industrial operator|fleet/logistics operator|manufacturer/OEM|
                technology vendor|research organisation/university|
                consortium/multi-party venture|government/public-sector body|
                community/local body
delay_category: no material delay stated|approvals/regulatory|grid connection/system studies|
                procurement/supply chain|financing/commercial close|construction/installation|
                commissioning/integration|data/validation/testing|
                stakeholder/land/community|internal governance/resourcing
failure_mode: no major failure stated|technical underperformance|integration failure|
              schedule slippage|cost overrun|resource/capability shortfall|
              commercial/demand failure|regulatory misfit|
              data quality/measurement failure|design assumption failure|
              governance/coordination failure
outcome_class: successful demonstration|partial success|delayed but recoverable|
               re-scoped/adapted|knowledge generated despite setback|
               discontinued/not progressed|follow-on scale-up enabled|
               policy/market influence only

# Extracted by model — optional overlays
secondary_failure_mode: "..."       # same values as failure_mode; only when co-present
intervention_note: "..."            # 1 sentence: what resolved/mitigated the issue
transferability: narrow|moderate|broad
delay_magnitude: <1 month|1–3 months|3–12 months|1–3 years|>3 years|not quantified
technology_domain: battery storage|hydrogen|solar PV|solar thermal|wind|DER|
                   demand response|EV|bioenergy|industrial renewables|
                   grid/system stability|hybrid systems|pumped hydro|other
source_pages: [N]                   # page numbers from <!-- page N --> markers; enables pdf_url#page=N deep links
evidence_excerpt: "direct quote from source"
confidence_note: "classification difficulty or reconciliation note"

# Stamped by script (not model-inferred)
source_url: "https://arena.gov.au/knowledge-bank/..."
project_page_url: "https://arena.gov.au/projects/..."
pdf_url: "https://arena.gov.au/assets/..."   # direct PDF download URL
markdown_filename: "filename.md"             # source markdown file
kb_category: "..."
kb_publish_date: "DD/MM/YYYY"
kb_year: "YYYY"
kb_associated_project: "..."        # canonical name from KB export — use for joins
in_arena_portfolio: true|false      # present in arena-projects-export CSV
location: "..."                     # project location from portfolio CSV
project_partners: "..."             # project partners from portfolio CSV
source_page_pdf: N                  # PDF page number verified via PyMuPDF (or null)

# Stamped by taxonomy v2 (stamp_taxonomy_v2.py)
arena_category: ["Battery storage", "..."]  # list, from kb_category via ARENA_CATEGORY_MAP (14 values)
activity_type: "Deployment"          # from projects CSV keywords (Study/Pilot/Deployment/R&D/null)
is_consortium: true|false            # true if original proponent_type was consortium
proponent_type_original: "..."       # pre-reclassification value (consortium records only)
lifecycle_phase_original: "..."      # pre-remap value (variation/re-scope records only)
```

---

## Pipeline for v2 run

| Step | Script | Notes |
|------|--------|-------|
| Extract (regular) | `03b_extract_registry_per_doc.py` | Per-doc, resumable |
| Extract (oversized) | `03c_extract_oversized.py` | 8 docs >600k chars, chunked |
| Stamp metadata | `stamp_recovered_docs.py` | Fix any per_doc YAMLs missing KB metadata |
| Temporal flags | `stamp_temporal_confidence.py` | Flag pre-2021 time-sensitive records |
| Fix violations | `fix_taxonomy_violations.py` | Deterministic taxonomy fixes |
| Dedup | `04c_dedup_within_project.py` | → `per_project/` + `registry_deduped.yaml` |
| Clean Tier 1+2 | `05_clean_registry.py` | → `registry_deduped_clean.yaml` |
| Clean Tier 3 | `05b_reconcile_contested.py` | → `registry_deduped_reconciled.yaml` |
| QA verify | `04b_verify_extractions.py --batch submit/collect` | Haiku batch, ~$25 for full corpus |
| QA recheck | `04c_recheck_flagged.py --run` | Re-run fabricated/unsupported with wider window (~$3) |
| Project matching | `match_unassigned_projects.py --pass1 --pass2-submit/collect` | Fuzzy + Haiku; MAX_TOKENS=2048 |
| **Taxonomy v2** | `stamp_taxonomy_v2.py` | Stamps arena_category, activity_type, is_consortium; reclassifies consortium; remaps lifecycle_phase |
| Dashboard | `build_dashboard.py` | Reads `per_doc/` + `per_doc_qa/`, outputs `dashboard/insights.html` |
| Deploy | `scp dashboard/insights.html root@85.155.188.202:/var/www/arena/index.html` | |
| QA spot-check | `sense_check.py` | Stratified sample, ~200 records recommended |

Steps 6 and 7 (`06_build_document_mapping.py`, `07_run_analysis.py`) are **no longer needed**
for regular use — KB metadata is stamped during extraction, and reference class matrices are
now embedded in the dashboard Analysis tab.

---

## Dashboard

`dashboard/insights.html` — single self-contained file. Deployed to `root@85.155.188.202:/var/www/arena/index.html`.

```bash
python3 scripts/build_dashboard.py                    # rebuild (reads per_doc/)
scp dashboard/insights.html root@85.155.188.202:/var/www/arena/index.html  # deploy
```

**Tabs:**
- **Delivery Records** — filterable card view with project panel, full-text search, synthesis
- **Analysis** — 8 charts (failure modes by ARENA category, lifecycle phase, outcomes, severity,
  co-occurrence) + 4 reference class matrix tables (Matrix 1: arena_category × activity_type,
  Matrix 2: arena_category × lifecycle_phase, Matrix 3: proponent_type + consortium adjustment,
  Matrix 4: discontinuation risk)
- **Benchmarks** — LCOE, capex, LCOH, capacity factor, abatement cost, storage performance tables
- **Reports** — (stub)

**Filters:** ARENA category, activity type, failure mode, outcome, proponent, lifecycle phase,
severity, consortium (yes/no), transferability, QA verdict, full-text search.

---

## Portfolio coverage analysis

- **Full ARENA portfolio:** 769 projects (`arena-projects-export_1772932404.csv`)
- **Covered by corpus:** 499 projects (64.9%) — after KB exact match + fuzzy + Haiku name matching
- **Coverage by start year:** poor 2011–2013 (23–41%), excellent 2017–2022 (76–93%),
  declining 2023+ (active projects, reports not yet published), 2025–2026 near-zero
- **Uncovered projects are mostly:** Post-Fellowship Doctorates (83/84 uncovered — no KB docs),
  International Engagement grants (12/13), small <$1m R&D feasibility studies, and recent
  active projects. Not a meaningful gap for delivery insight analysis.
- **12 KB-linked project names not in portfolio CSV** — minor omissions (e.g. AEMO CER Data
  Exchange, Hysata electrolyser). Worth cross-referencing once inside ARENA.
- **239 projects have only 1 KB document** — only 12% of these are clearly final reports;
  majority are posters, summaries, mid-project reports. Genuine rich coverage is ~30–40%.

---

## Key corpus statistics (v2 — current)

- **Source documents:** 1,440 regular + 8 oversized = 1,448 total
- **Records extracted:** 16,931 total in `per_doc/` (dashboard source)
- **After within-project dedup:** 15,457 records (`registry_deduped.yaml`)
- **Temporal confidence flags:** 945 records flagged (~5.7%) for pre-2021 time-sensitive claims
- **Taxonomy violations fixed:** 550 (462 en-dash, 88 field cross-contamination)

## Key findings (v2 — 16,931 records)

- **Adversity rate:** 73% of records have a failure mode
- Design assumption failure: 20% — largest single failure mode
- Technical underperformance: 10%
- Commercial/demand failure: 10%
- Governance/coordination failure: 7%
- Regulatory misfit: 7%
- Top project types: DER/customer-side (3,730), storage (2,363), generation (2,093)
- Highest adversity proponent: community/local body (83%), consortium (77%)

---

## QA verification summary (complete)

- **Grounding:** 92.2% confirmed, 5.5% plausible, 0.3% unsupported, 0.2% fabricated, 1.8% parse errors
- **Classification:** 89.6% ok, 8.0% questionable, 0.6% wrong, 1.8% parse errors
- Both metrics reflect two recheck passes with 15k-char window (vs original 3k):
  - Pass 1: 315 grounding-flagged records → 186 upgraded to confirmed/plausible
  - Pass 2: 148 classification-wrong records → 27 upgraded to ok, 18 to questionable
- **313 parse errors** (Haiku occasionally returns malformed YAML) — worth a retry pass someday
- QA verdicts stored in `insights/per_doc_qa/` and merged into dashboard cards at build time
- `04c_recheck_flagged.py` supports `--field grounding_verdict|classification_verdict` and
  `--batch submit/collect` (use batch mode — sequential hits rate limits)

---

## Cost reference

- v2 extraction (Sonnet, 1,440 docs): ~$50–70 USD (complete)
- Oversized doc extraction (Sonnet, 8 docs chunked): ~$1 USD (complete)
- Tier 3 reconciliation (Haiku): ~$0.50 USD (complete)
- QA verification (Haiku batch, 16,931 records): ~$25 USD (complete)
- QA recheck grounding (Haiku, 315 records, wider window): ~$3 USD (complete)
- QA recheck classification (Haiku batch, 148 records, wider window): ~$0.50 USD (complete)
- Project matching (Haiku batch, ~540 names): <$1 USD (complete)
- Do NOT run API calls without explicit instruction — check existing outputs first
