# ARENA Delivery Insight Extraction Prompt
**Version 1.3 | March 2026**

The taxonomy (injected below) is the complete guide to what to extract, what fields to populate, and how to classify. This prompt provides only the task framing and output format.

---

## Prompt template

```
You are extracting structured delivery insight records from ARENA knowledge-bank documents.
Follow the ARENA Delivery Insight Taxonomy v1.3 (appended below) exactly — it defines what to extract, all field schemas, allowed values, boundary guidance, and quality rules.

Extract every discrete delivery insight record the document warrants. There is no upper limit — do not stop early, do not anchor only on the executive summary. Read the full document including appendices, methodology sections, and tables. If a dense report warrants 30 records, extract 30.

---

## Output format

Output a YAML list. Each record is one item. Use null for unpopulated fields. Do not use empty strings.

If the document contains no extractable delivery insight records, output exactly:
no records extracted

```yaml
- record_id: ARENA-DLV-0001
  source_title: "Origin - Mortlake Power Station Battery Project - Lessons Learnt No.1"
  publish_date: "2024-08"
  project_name: "Mortlake Power Station Battery Project"
  what_happened: "Grid connection approval took 14 months and required two full resubmissions after the network operator imposed additional technical requirements not communicated at the outset."
  lesson_learnt: "Engage the network operator before finalising technical design — connection standards imposed after design freeze required two full resubmissions and added 14 months to the schedule."
  issue_severity: major
  project_type: storage
  project_scale_band: first commercial/FOAK
  lifecycle_phase: approvals/contracting
  proponent_type: utility/energy retailer
  delay_category: grid connection/system studies
  failure_mode: schedule slippage
  outcome_class: delayed but recoverable
  secondary_failure_mode: null
  intervention_note: "Engaged a specialist grid connection consultant and worked directly with the NSP — the third application was approved within 6 weeks."
  transferability: broad
  delay_magnitude: 1–3 years
  technology_domain: battery storage
  source_pages: [7]
  evidence_excerpt: "The connection application was resubmitted three times over 14 months before receiving approval."
  confidence_note: null
```

---

## Taxonomy and extraction guidance

[TAXONOMY_CONTENT]

---

## Document to process

[Document list and markdown content appended by the orchestrating script]

Start record_id numbering at ARENA-DLV-[START_ID].
```

---

## How the prompt is used

The extraction script (`scripts/03b_extract_registry_per_doc.py`) injects:
- `[TAXONOMY_CONTENT]` — full text of `ARENA_Taxonomy_v1.3.md`
- The document markdown and metadata
- The record_id start number
