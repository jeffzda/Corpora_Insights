# ARENA 100-Report Delivery Insight Pilot
**Version 1.0 | March 2026**

A reproducible end-to-end pipeline for extracting structured project-delivery insights from 100
ARENA knowledge bank report documents, using reference-class analysis aligned with the Flyvbjerg
delivery insight framework.

---

## What this pilot produced

- **267 structured delivery insight records** extracted from 100 report documents
- **256 clean records** after deduplication (11 duplicate records removed)
- **5 delivery reference classes** identified through cross-cutting analysis
- **14 analytical cuts** across failure mode, scale band, proponent type, lifecycle phase,
  and technology domain

Key finding: **79% of records document a substantive failure mode.** Design assumption failure
is the single largest (18%). Utility/large-scale projects have a 69% adverse outcome rate.

See `analysis/ARENA_delivery_reference_class_analysis.md` for the full findings.

---

## Folder structure

```
pilot_100_reports/
├── README.md                          ← this file
├── EXTRACTION_PROMPT.md               ← canonical agent prompt (for reproducibility)
│
├── data/
│   ├── arena-kb-export_1772889492.csv ← original ARENA knowledge bank export (1,548 items)
│   ├── manifest.csv                   ← download manifest (1,450 downloaded, 94 no PDF found)
│   ├── reports_sample_100.json        ← 100 selected documents with quality scores + md_path
│   ├── report_batches.json            ← intermediate batching by text size
│   └── agent_groups.json              ← 10 balanced groups for parallel agents
│
├── taxonomy/
│   ├── ARENA_Taxonomy_v1.0.md         ← v1.0: technology insight taxonomy (insight type/stage/domain)
│   └── ARENA_Taxonomy_v1.1.md         ← v1.1: delivery insight taxonomy (Flyvbjerg dimensions) ← USE THIS
│
├── insights/
│   ├── raw_batches/
│   │   ├── group_01.yaml              ← raw output from agent 1 (19 records)
│   │   ├── ...
│   │   └── group_10.yaml              ← raw output from agent 10 (31 records)
│   ├── ARENA_delivery_registry_v1.yaml           ← raw consolidated (267 records)
│   ├── ARENA_delivery_registry_v1_clean.yaml     ← deduplicated (256 records) ← USE THIS
│   └── ARENA_delivery_registry_v1_removed_dupes.yaml  ← audit trail (11 records)
│
├── analysis/
│   ├── ARENA_delivery_reference_class_analysis.md  ← primary output: 5 reference classes
│   └── ARENA_insight_synthesis_report.md           ← earlier 30-doc pilot synthesis (for comparison)
│
└── scripts/
    ├── 00_download_pdfs.py            ← download PDFs from ARENA knowledge bank website
    ├── 01_select_reports.py           ← select 100 docs from manifest.csv
    ├── 02_convert_to_markdown.py      ← PDF → markdown text (requires pymupdf)
    ├── 03_build_agent_groups.py       ← balance docs into 10 groups by text size
    ├── 04_consolidate_registry.py     ← merge group YAMLs → master registry + dedup
    └── 05_run_analysis.py             ← run 14 reference class analytical cuts
```

---

## Prerequisites

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install pymupdf pyyaml requests beautifulsoup4
```

You also need:
- The original CSV export from the ARENA knowledge bank website
  (`data/arena-kb-export_1772889492.csv` — included in this folder)
- Access to Claude Code with a valid Anthropic API key (for the extraction agent step)

---

## Full reproduction pipeline

### Step 0 — Download PDFs from the ARENA knowledge bank

```bash
# Copy the CSV to the ARENA working directory (parent of this folder)
cp data/arena-kb-export_1772889492.csv ../

# Run the download script from the ARENA root
cd ..
python pilot_100_reports/scripts/00_download_pdfs.py
cd pilot_100_reports
```

The script:
- Reads each row in the CSV and fetches the ARENA knowledge bank page at `Link to item`
- Finds the PDF download link on the page (heuristic: first `<a href="*.pdf">`)
- Downloads to `pdfs/<RecordType>/<sanitized_title>_<hash6>.pdf`
- Writes a `manifest.csv` tracking every row with its download status and local path
- Is resumable: skips rows already in `manifest.csv`
- Polite: 1-second delay between requests, 3 retries with backoff

**Expected outcome:** ~1,450 PDFs downloaded (~3.1 GB), ~94 records with no PDF found.
Wall-clock time: ~45–60 minutes on a typical connection.

The completed `manifest.csv` is included in `data/` so you can skip this step.

---

### Step 1 — Select 100 high-quality report documents

```bash
python scripts/01_select_reports.py
```

Reads `manifest.csv` from the ARENA root directory. Filters to report-type subdirectories.
Scores each document on quality indicators. Selects 100 proportionally by technology domain.

Output: `data/reports_sample_100.json`

**Quality scoring logic (higher is better):**

| Condition | Points |
|---|---|
| File size 300 KB–5 MB (text-dense, not unwieldy) | +3 |
| Year 2020–2025 | +3 |
| Year 2017–2019 | +2 |
| Project Status = Past (completed project) | +1 |
| Subdir = Reports_Lessons | +3 |
| Subdir = Reports_Milestones | +2 |
| Title contains "Final Report / Lessons Learnt / Feasibility" | +2 |
| Title contains "Newsletter / Brochure / Infographic" | −5 |

**Proportional allocation across technology domains:**

| Domain | Pool size | Selected |
|---|---|---|
| solar_pv | 386 | 29 |
| der | 98 | 12 |
| battery_storage | 74 | 9 |
| hydrogen | 65 | 8 |
| ev | 57 | 7 |
| solar_thermal | 56 | 7 |
| demand_response | 52 | 7 |
| industrial_decarbonisation | 48 | 5 |
| bioenergy | 36 | 5 |
| other | 189 | 11 |

Note: the category field in the CSV contains HTML entities (`&amp;` instead of `&`).
The script applies `html.unescape()` before category matching — this is required to
correctly identify the "Solar energy, Solar PV R&D" category (188 records).

---

### Step 2 — Convert PDFs to markdown text

```bash
python scripts/02_convert_to_markdown.py
```

Converts each selected PDF to plain text using pymupdf (fitz).
Adds `<!-- page N -->` markers between pages.
Output files written to `../../markdown/reports/` (relative to this folder).
Updates `data/reports_sample_100.json` with a `md_path` field per record.

Average output: ~37 KB text per document (~9,400 tokens).

---

### Step 3 — Build balanced agent groups

```bash
python scripts/03_build_agent_groups.py --groups 10
```

Assigns documents to 10 balanced groups using round-robin by text size (largest first).
This ensures no single agent receives a disproportionate text volume.

Output: `data/agent_groups.json` — list of 10 groups, each a list of record dicts.

---

### Step 4 — Run extraction agents (Claude Code)

This step requires Claude Code and uses the Anthropic API.

See `EXTRACTION_PROMPT.md` for the exact prompt used for each agent.

**How to run in Claude Code:**

Launch 10 parallel agents from Claude Code. Each agent should:
1. Receive the extraction prompt from `EXTRACTION_PROMPT.md`
2. Receive its document group from `data/agent_groups.json`
3. Read the markdown text for each document in its group
4. Output a YAML list of records to `insights/raw_batches/group_NN.yaml`

Record ID offsets (to avoid collisions):
- Group 01: start at ARENA-DLV-0001
- Group 02: start at ARENA-DLV-0031
- Group 03: start at ARENA-DLV-0061
- ... (30 ID slots per group)

**Cost estimate:** ~$3–5 at Sonnet 4.6 pricing (March 2026 rates) for 100 documents.

The completed batch files are included in `insights/raw_batches/`.

---

### Step 5 — Consolidate and deduplicate

```bash
python scripts/04_consolidate_registry.py
```

Merges all `group_NN.yaml` files into a single registry.
Automatically flags likely duplicates: same `project_name` + same
(`failure_mode`, `lifecycle_phase`) structural fingerprint.
Keeps the record with more text; saves the other to the audit trail.

**Review flagged candidates manually** — automated deduplication is conservative.
11 confirmed duplicates were found in this pilot (same finding reported across
sequential lessons learnt documents for the same project).

Outputs:
- `insights/ARENA_delivery_registry_v1.yaml` — raw (267 records)
- `insights/ARENA_delivery_registry_v1_clean.yaml` — deduplicated (256 records)
- `insights/ARENA_delivery_registry_v1_removed_dupes.yaml` — audit trail

---

### Step 6 — Run reference class analysis

```bash
python scripts/05_run_analysis.py --output analysis/reference_class_analysis.md
```

Runs 14 structured analytical cuts across the clean registry.
Output is a markdown report with tables.

For the full narrative synthesis (5 reference classes, portfolio manager implications),
see `analysis/ARENA_delivery_reference_class_analysis.md` — this was produced by a
separate Claude agent that interpreted the raw analytical output from step 6.

---

## Corpus notes

- **Source documents:** 100 ARENA knowledge bank PDFs, 2016–2025
- **Document types:** Reports, Lessons Learnt, Milestone Reports
- **Unique projects represented:** 64 (36 documents are sequential reports on the same project)
- **Records extracted:** 267 raw → 256 after deduplication
- **Average records per document:** 2.7
- **Field population rates:**
  - record_id / source_title / project_name / what_happened: 100%
  - project_type / failure_mode / outcome_class: ~99%
  - delay_category: ~71% (only populated when delay is a meaningful part of the lesson)

---

## Limitations

1. **6.5% corpus coverage.** 100 documents from 1,548. Under-represented: wind energy,
   pumped hydro, research-stage findings.

2. **Sequential reports inflate project count.** 64 unique projects across 100 documents.
   Deduplication removes exact fingerprint duplicates but similar findings across sequential
   reports may persist.

3. **Cost data suppressed.** Only 6 cost overrun records. Cost data is commercially
   sensitive and rarely disclosed in ARENA lessons learnt documents.

4. **Extraction model dependency.** Claude claude-sonnet-4-6 (March 2026). Re-running
   with a different model version may produce different record counts and classifications.

---

## Scaling to the full corpus

To process all ~1,500 documents:
1. Set `TARGET_COUNT = 1500` in `01_select_reports.py`
2. Use `--groups 50` in `03_build_agent_groups.py`
3. Run 50 parallel extraction agents
4. Expect ~$150–200 API cost at Sonnet 4.6 pricing
5. Wall-clock time: 4–6 hours with 50 parallel agents
