# ARENA Delivery Insight Taxonomy v1.2
**Lean extraction schema for project-delivery insights from ARENA knowledge documents**

**Version history**
- v1.0 March 2026 — pilot (100 documents, 267 records)
- v1.1 March 2026 — full corpus (1,440 documents, 1,752 records); no schema changes from v1.0
- v1.2 March 2026 — post-analysis update; no allowed-value changes; added extraction guidance, known distortions, traceability fields, and one confirmed field error correction

---

## Purpose

This taxonomy is designed to extract **project-delivery-relevant knowledge** from ARENA knowledge-bank documents.

It is deliberately biased toward:
- delivery characteristics
- reference-class learning
- failure and delay patterns
- outcome patterns
- future transferability for similar projects

It is **not** primarily a technical-topic taxonomy.

---

## Design rules

1. **Lean beats complete.**
   Use 12 high-fill fields rather than a larger sparse schema.

2. **Preserve raw metadata separately.**
   Keep CSV/source metadata in an ingest layer, not in the core analytic schema.

3. **Separate facts from inference.**
   Every field must be labeled as either:
   - `extractable` — directly stated in source metadata or text
   - `inferred` — assigned by analyst/model from available evidence

4. **Only infer when confidence is medium or high.**
   If the document does not support a field clearly enough, leave it null.

5. **Optimise for reference-class retrieval.**
   The schema must support retrieval across:
   - project type
   - scale
   - phase
   - proponent type
   - delay category
   - failure mode
   - outcome

6. **Do not design for sparse information.**
   If a field cannot be populated in at least ~60% of documents, it should not be core.

---

## Ingest envelope (preserved, not part of the 12 core fields)

Retain these raw fields exactly as supplied by source metadata:

- `source_title_raw`
- `source_type_raw`
- `publish_date_raw`
- `project_name_raw`
- `category_raw`
- `project_status_raw`
- `year_raw`
- `source_url_raw` (if available)

**From v1.2 — add at point of extraction:**
- `markdown_filename` — the local markdown filename the record was extracted from (e.g. `neoen_victorian_big_battery_moorabool_retrofit_lessons_learnt_report_1.md`)
- `kb_document_page` — the public ARENA Knowledge Bank URL for the source document (e.g. `https://arena.gov.au/knowledge-bank/neoen-victorian-big-battery-...`)

Capturing these at extraction time removes the need for post-hoc document matching. In the v1.1 corpus, document matching was performed retrospectively and required multi-strategy fuzzy matching to achieve 100% coverage. Future runs should populate both fields directly from the extraction context.

These are not analytical fields. They are provenance and normalisation support.

---

## Core analytic schema (12 fields)

### 1. `record_id`
**type:** extractable / system-generated  
**purpose:** stable unique identifier

### 2. `source_title`
**type:** extractable  
**purpose:** normalized source title for citation and traceability

### 3. `publish_date`
**type:** extractable  
**purpose:** publication date or best available source date

### 4. `project_name`
**type:** extractable  
**purpose:** canonical project name

### 5. `what_happened`
**type:** extractable  
**purpose:** one- or two-sentence neutral summary of the delivery-relevant event, lesson, issue, or result

**rule:**  
State the event in delivery language, not promotional language.

---

### 6. `project_type`
**type:** inferred  
**Flyvbjerg dimension:** project type  
**purpose:** reference-class grouping by delivery archetype

**allowed values:**
- generation
- storage
- network / grid
- DER / customer-side
- transport electrification
- industrial decarbonisation
- manufacturing / supply chain
- software / data / digital
- enabling infrastructure
- multi-technology / hybrid

**rule:**  
Classify by the dominant delivery object, not by every technology mentioned.

---

### 7. `project_scale_band`
**type:** inferred  
**Flyvbjerg dimension:** scale  
**purpose:** normalize projects for reference-class comparison

**allowed values:**
- lab / bench
- pilot
- demonstration
- first commercial / FOAK
- commercial expansion
- utility / large-scale
- programmatic / portfolio-level

**rule:**  
Use the smallest reliable scale band supported by the document.  
Do not force exact MW / MWh / $ values into the core schema.

---

### 8. `lifecycle_phase`
**type:** inferred
**Flyvbjerg dimension:** phase
**purpose:** identify where the insight arose in the project lifecycle

**allowed values:**
- concept / feasibility
- development / design
- approvals / contracting
- procurement
- construction / installation
- commissioning / integration
- operations
- variation / re-scope
- close-out / post-project review

**rule:**
Choose the phase in which the main issue or insight occurred, not necessarily the project’s overall current phase.

**Boundary guidance — commissioning/integration vs. operations:**
In the 1,752-record corpus, `operations` is the single largest phase (419 records) and `commissioning/integration` is the second (308 records). The boundary between them is material and is a known source of inconsistency. Use `commissioning/integration` when the insight concerns first-time activation, integration testing, control system configuration, grid connection commissioning, or any event that occurred before the asset reached stable commercial operation. Use `operations` when the asset was already in stable commercial operation and the issue arose during ongoing service. If the document does not clearly distinguish these, default to `commissioning/integration` for technical failures and `operations` for commercial or demand failures discovered after go-live.

**Known error in v1.1 corpus:** One record has `lifecycle_phase: data/validation/testing`, which is a `delay_category` value incorrectly assigned to this field. This value is not valid for `lifecycle_phase`.

---

### 9. `proponent_type`
**type:** inferred  
**Flyvbjerg dimension:** proponent type  
**purpose:** support comparison by delivery actor

**allowed values:**
- project developer
- utility / energy retailer
- network business
- industrial operator
- fleet / logistics operator
- manufacturer / OEM
- technology vendor
- research organisation / university
- consortium / multi-party venture
- government / public-sector body
- community / local body

**rule:**  
Use the lead delivery actor, not every participant.

---

### 10. `delay_category`
**type:** inferred  
**Flyvbjerg dimension:** delay category  
**purpose:** normalize schedule drag into reusable categories

**allowed values:**
- no material delay stated
- approvals / regulatory
- grid connection / system studies
- procurement / supply chain
- financing / commercial close
- construction / installation
- commissioning / integration
- data / validation / testing
- stakeholder / land / community
- internal governance / resourcing

**rule:**  
Use only when delay is a meaningful part of the lesson.  
If timing friction is implied but not clear, leave null.

---

### 11. `failure_mode`
**type:** inferred  
**Flyvbjerg dimension:** failure mode  
**purpose:** support retrieval of what actually went wrong

**allowed values:**
- no major failure stated
- technical underperformance
- integration failure
- schedule slippage
- cost overrun
- resource / capability shortfall
- commercial / demand failure
- regulatory misfit
- data quality / measurement failure
- design assumption failure
- governance / coordination failure

**rule:**
Capture the dominant failure mode only.
If the document presents a positive lesson with no failure, use `no major failure stated`.

**Known distortion — `cost overrun`:**
In the 1,752-record full corpus, `cost overrun` appears in only 17 records (1%). This is implausibly low as a true incidence rate and reflects disclosure norms, not actual cost performance. ARENA knowledge bank documents rarely disclose cost overruns with sufficient specificity to code this failure mode. Extractors should code `cost overrun` when the document explicitly states it; analysts should not draw conclusions about portfolio cost performance from the resulting counts.

---

### 12. `outcome_class`
**type:** inferred  
**Flyvbjerg dimension:** outcome  
**purpose:** classify the project-level result of the event or lesson

**allowed values:**
- successful demonstration
- partial success
- delayed but recoverable
- re-scoped / adapted
- knowledge generated despite setback
- discontinued / not progressed
- follow-on scale-up enabled
- policy / market influence only

**rule:**  
This is not a moral judgment.  
It is a compact description of what the project event ultimately produced.

---

## Field population rules

### Must always be populated
- `record_id`
- `source_title`
- `publish_date`
- `project_name`
- `what_happened`

### Populate when evidence supports medium confidence or better
- `project_type`
- `project_scale_band`
- `lifecycle_phase`
- `proponent_type`
- `delay_category`
- `failure_mode`
- `outcome_class`

### Leave null when unclear
Do not guess.

---

## What is deliberately excluded from the core schema

The following are useful, but should be optional overlays rather than core fields unless a fill-rate audit proves they exceed ~60%:

- exact technology subtype
- geography
- exact MW / MWh / $ scale
- barrier text
- enabler text
- recommendation text
- evidence excerpt
- transferability score
- policy relevance
- impact tags
- tradeoff

These can be added later as:
- optional overlay fields, or
- derived tags

---

## Minimal optional overlay layer

Only add these after validating fill rates.

### `technology_domain`
High-value retrieval field, but secondary to delivery structure.

**allowed values:**
- battery storage
- hydrogen
- solar PV
- solar thermal
- wind
- DER
- demand response
- EV
- bioenergy
- industrial renewables
- grid / system stability
- hybrid systems
- pumped hydro
- other

### `evidence_excerpt`
Short quote or data point grounding the record.

**Treat as strongly recommended, not optional.** In the 1,752-record full corpus, `evidence_excerpt` is the only field verifiable by text search against source documents. It is the anchor for data quality assurance. Populate it whenever a quotable phrase exists in the source — which is the case for the large majority of records. Leave null only when the document contains no quotable text relevant to the record (rare: applies primarily to interview-format documents).

### `confidence_note`
Optional note when classification was difficult.

---

## Extraction guidance

### Good `what_happened`
“Grid connection approval took 14 months and required repeated resubmission due to unclear technical requirements.”

### Bad `what_happened`
“The project experienced important learnings in relation to stakeholder engagement and successful future deployment.”

---

## Corpus validation history

| Version | Date | Records | Documents | Field value audit | Evidence verification |
|---|---|---|---|---|---|
| v1.0 | March 2026 | 267 | 100 | — | — |
| v1.1 | March 2026 | 1,752 | 1,440 | All field values confirmed within allowed lists (one `lifecycle_phase` rogue value: `data/validation/testing`) | 100-record stratified sense check: 52 Exact, 47 Substantive, 1 Unverified — no hallucinated content |

**Consistency note:** The 1,752 records were extracted across 150 batches using a consistent prompt and taxonomy. No formal inter-rater reliability audit has been conducted. Field-value distribution is stable across technology domains, suggesting consistent application, but taxonomy label correctness has not been independently verified for individual records — only that record text is grounded in source documents.

---

## Example record

```yaml
record_id: ARENA-DLV-0001
source_title: "Origin - Mortlake Power Station Battery Project - Lessons Learnt No.1"
publish_date: 2024-08-15
project_name: "Mortlake Power Station Battery Project"
what_happened: "Grid connection approval took 14 months and required repeated resubmission due to unclear technical requirements."

project_type: storage
project_scale_band: first commercial / FOAK
lifecycle_phase: approvals / contracting
proponent_type: utility / energy retailer
delay_category: grid connection / system studies
failure_mode: schedule slippage
outcome_class: delayed but recoverable