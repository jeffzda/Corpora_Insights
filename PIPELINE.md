# ARENA Delivery Registry — Pipeline

End-to-end pipeline for extracting, verifying, and analysing delivery insights
from ARENA Knowledge Bank project reports.

---

## Overview

```
PDFs (1,440)
    │
    ▼  [step 01] download_pdfs.py              — download PDFs from KB
    ▼  [step 02] convert_to_markdown.py        — PDF → markdown (PyMuPDF)
    ▼  [step 03] extract_registry.py           — markdown → YAML records (Anthropic API)
    ▼  [step 04] consolidate_registry.py       — merge groups, fingerprint deduplication
    ▼  [step 05] clean_registry.py             — taxonomy fixes, majority-vote harmonisation
    ▼  [step 05b] reconcile_contested.py       — LLM resolution of contested fields (Anthropic API)
    ▼  [step 06] build_document_mapping.py     — records → KB page URLs + markdown files
    ▼  [step 07] run_analysis.py               — YAML → reference class matrix reports
    ▼  [step 08] sense_check.py                — spot-check records against source files
```

---

## Requirements

```bash
pip install anthropic pyyaml rapidfuzz pymupdf
export ANTHROPIC_API_KEY=sk-ant-...
```

Python 3.10+. All scripts run from the project root.

---

## Step 1 — Download PDFs

```bash
python download_pdfs.py
```

Downloads PDFs from ARENA Knowledge Bank. Source manifest: `manifest.csv`.
Output: `pdfs/`

Already complete for the current corpus. Only re-run when new reports are available.

---

## Step 2 — Convert PDFs to Markdown

```bash
python pilot_100_reports/scripts/02_convert_to_markdown.py
```

Converts PDFs to plain text markdown using PyMuPDF.
Output: `markdown/all/*.md` (1,440 files)

Already complete. Only re-run if new PDFs are added.

---

## Step 3 — Extract Registry (Anthropic API)

The main extraction step. Reads grouped markdown files and asks Claude to
extract structured delivery insight records.

```bash
# Run all 150 groups
python scripts/03_extract_registry.py

# Resume a partial run (skips groups that already have output files)
python scripts/03_extract_registry.py --resume

# Run a specific range or single group
python scripts/03_extract_registry.py --groups 1-10
python scripts/03_extract_registry.py --groups 45

# Dry run — print the first prompt without calling the API
python scripts/03_extract_registry.py --dry-run
```

**Inputs:**
- `all_agent_groups_v2.json` — 150 groups of ~10 markdown files each
- `pilot_100_reports/EXTRACTION_PROMPT.md` — prompt template
- `pilot_100_reports/taxonomy/ARENA_Taxonomy_v1.1.md` — taxonomy schema

**Output:** `insights/full_run/group_001.yaml` … `group_150.yaml`

**Notes:**
- Each group uses 50 record ID slots: group N → IDs `(N-1)*50+1` to `N*50`
- Resumable — safe to interrupt and re-run with `--resume`
- Rate limit errors are retried with exponential backoff (up to 5 attempts)
- Cost: ~21M input tokens at claude-sonnet-4-6 pricing ≈ $20–30 USD for a full run

---

## Step 4 — Consolidate and Deduplicate

```bash
python scripts/04_consolidate_registry.py
```

Merges all group YAML files and removes structural duplicates (same project +
same failure_mode + lifecycle_phase fingerprint).

```bash
# Custom paths
python scripts/04_consolidate_registry.py \
    --batch-dir insights/full_run \
    --out-prefix insights/ARENA_delivery_registry_full_v1
```

**Outputs:**
- `insights/ARENA_delivery_registry_full_v1.yaml` — raw (all records)
- `insights/ARENA_delivery_registry_full_v1_clean.yaml` — deduplicated
- `insights/ARENA_delivery_registry_full_v1_removed_dupes.yaml` — audit trail

Review the removed_dupes file after running to confirm no legitimate records
were dropped. The criterion is conservative and should not affect distinct records.

---

## Step 5 — Clean and Harmonise

```bash
python scripts/05_clean_registry.py
```

Two tiers of cleaning:
- **Tier 1** — Deterministic fixes: taxonomy remapping (technology_domain,
  project_type, failure_mode), leaked lifecycle values, fuzzy project name
  canonicalisation across variant spellings
- **Tier 2** — Majority-vote harmonisation of project-level fields
  (project_type, project_scale_band, proponent_type) where ≥70% of records
  for the same project agree. Contested projects (no clear majority) are
  flagged in `confidence_note` for Tier 3 resolution.

```bash
# Custom paths
python scripts/05_clean_registry.py \
    --input  insights/ARENA_delivery_registry_full_v1_clean.yaml \
    --output insights/ARENA_delivery_registry_full_v2_clean.yaml
```

**Outputs:**
- `insights/ARENA_delivery_registry_full_v2_clean.yaml`
- `insights/ARENA_delivery_registry_full_v2_audit.yaml` — all changes logged

---

## Step 5b — Reconcile Contested Fields (Anthropic API)

```bash
python scripts/05b_reconcile_contested.py
```

Reads projects flagged as 'harmonisation-contested' by Step 5 and asks
Claude (Haiku — fast and cheap) to make a single authoritative classification
for each contested field.

```bash
# Custom paths
python scripts/05b_reconcile_contested.py \
    --input  insights/ARENA_delivery_registry_full_v2_clean.yaml \
    --output insights/ARENA_delivery_registry_full_v3_clean.yaml
```

**Outputs:**
- `insights/ARENA_delivery_registry_full_v3_clean.yaml`
- `insights/ARENA_delivery_registry_full_v3_audit.yaml`

**Notes:**
- Typically ~200 contested projects per full run
- Cost: ~$0.50 USD (Haiku pricing, ~256 tokens per decision)
- If a project has no contested fields, the input is copied to output unchanged

---

## Step 6 — Build Document Mapping

```bash
python scripts/06_build_document_mapping.py
```

Maps every registry record to its ARENA Knowledge Bank page URL and local
markdown source file, using six matching strategies in priority order.

```bash
# Point at a specific registry version
python scripts/06_build_document_mapping.py \
    --registry insights/ARENA_delivery_registry_full_v3_clean.yaml \
    --kb-csv arena-kb-export_1772889492.csv \
    --markdown-root markdown/all

# Verbose: print records with no KB match
python scripts/06_build_document_mapping.py --verbose
```

**Outputs:**
- `insights/registry_to_document_mapping.csv` — full 14-column mapping
- `insights/insight_to_source.csv` — simplified `record_id → kb_document_page`

**If coverage is below ~99%:** Run with `--verbose` to identify unmatched titles.
The most common cause is a KB title that is drastically shortened relative to
the document title. Add these as manual overrides in the script.

---

## Step 7 — Run Analysis

```bash
python scripts/07_run_analysis.py
```

Produces the reference class matrix report from the clean registry.

```bash
# Point at a specific registry
python scripts/07_run_analysis.py \
    --registry insights/ARENA_delivery_registry_full_v3_clean.yaml \
    --out insights/reports/ARENA_reference_class_matrix.md

# Adjust minimum cell size for Matrix A (default 15)
python scripts/07_run_analysis.py --min-n 20
```

**Output:** `insights/reports/ARENA_reference_class_matrix.md`

Contains:
- **Matrix A** — `project_type × scale_band`: base rate reference class lookup
- **Matrix B** — `technology_domain × lifecycle_phase`: phase risk watch-list
- **Matrix C** — `proponent_type`: adversity rate adjustment factor
- Discontinuation risk summary table

---

## Step 8 — Sense Check (quality audit)

```bash
# Stratified random sample of 100 records
python sense_check.py --sample 100 --seed 42 \
    --markdown-root markdown/all \
    --out insights/reports/sense_check_$(date +%Y%m%d).md

# Check specific records by ID
python sense_check.py --ids ARENA-DLV-0512 ARENA-DLV-1064 \
    --markdown-root markdown/all

# Target a specific technology domain
python sense_check.py --sample 20 --filter technology_domain "battery storage" \
    --markdown-root markdown/all

# Verbose output — see which phrases failed
python sense_check.py --ids ARENA-DLV-XXXX --verbose
```

Verdicts:
- **Exact** — ≥2 phrases found verbatim in source document
- **Substantive** — content words present; exact match blocked by PDF artefacts
- **Unverified** — fewer than 2 phrases match at any level (warrants manual review)

See `docs/sense_check_methodology.md` for full interpretation guide.

---

## Key files

| File | Description |
|---|---|
| `all_agent_groups_v2.json` | 150 document groups for extraction |
| `arena-kb-export_1772889492.csv` | ARENA KB catalogue (1,548 entries) |
| `arena-projects-export_*.csv` | ARENA project list |
| `markdown/all/` | 1,440 markdown files converted from PDFs |
| `insights/full_run/group_*.yaml` | Raw extraction outputs (one per group) |
| `insights/ARENA_delivery_registry_full_v1_clean.yaml` | After step 4 — deduplicated |
| `insights/ARENA_delivery_registry_full_v2_clean.yaml` | After step 5 — taxonomy cleaned |
| `insights/ARENA_delivery_registry_full_v3_clean.yaml` | After step 5b — fully harmonised |
| `insights/registry_to_document_mapping.csv` | Full record → KB page → markdown mapping |
| `insights/insight_to_source.csv` | Simplified record → KB page mapping |
| `insights/reports/` | Analysis and sense check outputs |
| `pilot_100_reports/taxonomy/ARENA_Taxonomy_v1.1.md` | Extraction taxonomy |
| `pilot_100_reports/EXTRACTION_PROMPT.md` | LLM extraction prompt |
| `sense_check.py` | Data quality verification tool |
| `docs/sense_check_methodology.md` | Sense check interpretation guide |

---

## Adding new ARENA reports to the corpus

1. Download new PDFs and convert to markdown in `markdown/all/`
2. Create a new groups JSON file for the new documents
3. Run step 3 for the new groups only: `--groups 151-160`
4. Re-run steps 4–7 using the expanded batch directory
5. Run step 8 on a sample that includes new records

Increment the registry version (`_v4`, etc.) each time the corpus is expanded,
and record the update in the taxonomy validation history table.
