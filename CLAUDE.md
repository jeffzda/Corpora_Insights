# ARENA Delivery Registry — Claude Context

This project extracts structured delivery insight records from 1,440 ARENA Knowledge Bank PDFs
using the Anthropic API, producing a cleaned, harmonised registry for reference-class analysis
and an interactive dashboard.

**Current status: v1 pipeline complete (v3_clean registry). v2 per-document extraction script
built and tested on 10 documents. Full re-extraction run not yet started — planned for the
owner's two-week break before starting at ARENA as a portfolio manager.**

---

## Context and intent

The owner is joining ARENA as a portfolio manager in ~6 weeks. The goal is to have a polished,
complete dataset and working dashboard before day one. The dashboard is for personal use
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
│   ├── 03b_extract_registry_per_doc.py      — NEW: per-document extraction (use this)
│   ├── 04_consolidate_registry.py           — merge + fingerprint dedup
│   ├── 05_clean_registry.py                 — Tier 1+2 taxonomy cleaning + majority-vote
│   ├── 05b_reconcile_contested.py           — Tier 3 LLM resolution of contested fields
│   ├── 06_build_document_mapping.py         — SUPERSEDED: mapping now baked into 03b
│   ├── 07_run_analysis.py                   — YAML → reference class matrix report
│   └── build_dashboard.py                   — NEW: generates insights.html from per_doc YAMLs
├── sense_check.py                           — QA spot-check against source markdown
├── pilot_100_reports/
│   ├── EXTRACTION_PROMPT.md                 — LLM extraction prompt template
│   └── taxonomy/ARENA_Taxonomy_v1.1.md      — core 12-field schema and allowed values
├── insights/
│   ├── full_run/group_001.yaml … group_150.yaml   — v1 extraction outputs (DO NOT USE)
│   ├── per_doc/doc_0001.yaml … doc_1440.yaml      — v2 per-doc outputs (in progress)
│   ├── ARENA_delivery_registry_full_v3_clean.yaml — v1 final registry (superseded by v2 run)
│   ├── ARENA_delivery_registry_full_v3_audit.yaml — v1 audit trail
│   └── reports/                                   — analysis outputs and sense check reports
└── dashboard/
    └── insights.html                        — single-file interactive dashboard (open in browser)
```

---

## New per-document extraction script (03b) — key design decisions

`scripts/03b_extract_registry_per_doc.py` replaces `03_extract_registry.py`. Run this for all
future extraction work.

**Key differences from the original:**
- One API call per document (not per group of ~10)
- No per-document character truncation (full content sent)
- Documents over 600k chars skipped (6 oversized reference docs — see below)
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

**The 6 documents skipped (over 600k chars — exceed model context window):**
- Australian Energy Resource Assessment 2014 (1.3M chars)
- Stocktake: Database of Renewable Energy Grid Integration Projects (1.2M chars)
- AEMO Project EDGE Final Report (1.0M chars)
- ESCRI South Australia General Project Report Phase 1 (798k chars)
- ACAP 2024 Annual Report (747k chars)
- ACAP 2022 Annual Report (639k chars)
These are broad reference/annual report documents unlikely to yield targeted delivery records.

**Usage:**
```bash
python3 scripts/03b_extract_registry_per_doc.py                  # all documents
python3 scripts/03b_extract_registry_per_doc.py --docs 1-10      # range
python3 scripts/03b_extract_registry_per_doc.py --resume         # skip completed
python3 scripts/03b_extract_registry_per_doc.py --dry-run        # no API call
```

---

## YAML record schema (v2 — full field list, Taxonomy v1.3)

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
```

---

## Pipeline for v2 run

| Step | Script | Notes |
|------|--------|-------|
| Extract | `03b_extract_registry_per_doc.py` | Per-doc, ~$50-70 total, resumable |
| Consolidate | `04_consolidate_registry.py` | Point at `insights/per_doc/` |
| Clean Tier 1+2 | `05_clean_registry.py` | Taxonomy fixes, majority-vote |
| Clean Tier 3 | `05b_reconcile_contested.py` | LLM reconciliation (~$0.50) |
| Analysis | `07_run_analysis.py` | Reference class matrices |
| Dashboard | `build_dashboard.py` | Regenerate after each pipeline step |
| QA | `sense_check.py` | Stratified sample, ~200 records recommended |

Step 6 (`06_build_document_mapping.py`) is **no longer needed** — KB metadata is stamped
directly onto records during extraction.

---

## Dashboard

`dashboard/insights.html` — single self-contained file, open in any browser.

```bash
python3 scripts/build_dashboard.py                                    # default
python3 scripts/build_dashboard.py --input insights/per_doc --output dashboard/insights.html
```

**Filters:** failure mode, outcome, project type, scale, proponent, lifecycle phase,
technology domain, ARENA project (by KB name), full-text search.

**Each record:** colour-coded failure mode + outcome badges, evidence excerpt, all
classification tags, link to ARENA KB source page and project page.

**Stats bar:** records shown, ARENA portfolio coverage (X of 769 projects, X%),
failure mode counts — all update live as filters change.

---

## Portfolio coverage analysis

- **Full ARENA portfolio:** 769 projects (`arena-projects-export_1772932404.csv`)
- **Covered by KB documents:** ~491 projects exact name match (63.8%)
- **Coverage by start year:** poor 2011–2013 (16–38%), excellent 2017–2022 (79–96%),
  declining 2023+ (projects still active, reports not yet published)
- **239 projects have only 1 KB document** — only 12% of these are clearly final reports;
  majority are posters, summaries, mid-project reports. Genuine rich coverage is ~30–40%.

## Planned analyses (next session)

1. **Document quality scoring** — classify each project's KB documents by type
   (final report, lessons learnt, interim, poster etc.) to identify which projects have
   *meaningful* coverage vs thin coverage. Surface this in the dashboard.

2. **Lifecycle phase coverage audit** — cross-tab `lifecycle_phase` against project count
   to identify which delivery stages are systematically underdocumented in the knowledge bank.
   Expected to find large gaps at `approvals/contracting` and `procurement` phases.

3. **Dashboard enhancements** — add portfolio coverage view, document quality indicator
   per project, and lifecycle phase distribution chart.

---

## Key corpus statistics (v1 run — will update after v2)

- **Source documents:** 1,440 with markdown files
- **Document size:** mean 65,714 chars, median 31,563 chars; 315 (22%) truncated at 80k in v1
- **v1 records:** 1,968 raw → 1,752 after dedup → 1,703 after Tier 3 + 12 manual fixes
- **v2 expected yield:** ~5 records/doc average (vs 1.2 in v1) → ~7,000+ records

## Key findings (v1 v3_clean — expect to shift after v2)

- Design assumption failure: 18% (n=310) — largest single failure mode
- Regulatory misfit: 15% (n=256)
- No major failure: 13% (n=234)
- Integration failure: 11% (n=193)
- Transport electrification: 98% any-failure rate (highest project type)
- Consortia: 96% any-failure rate (highest proponent type)
- 26.7% of projects have ≥2 failure modes

---

## Cost reference

- v2 extraction (Sonnet, 1,434 docs individually): ~$50–70 USD
- Tier 3 reconciliation (Haiku): ~$0.50 USD
- Do NOT run API calls without explicit instruction — check existing outputs first
