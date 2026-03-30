# ARENA Delivery Insight Taxonomy v1.3
**Version history:** v1.0–v1.1 March 2026 (1,752 records, 1,440 docs) · v1.2 post-analysis guidance update · v1.3 pre-v2-run redesign: added `lesson_learnt`, `issue_severity`, `intervention_note`, `secondary_failure_mode`, `transferability`, `delay_magnitude`; moved all extraction guidance into taxonomy

---

## Purpose

Extract **project-delivery knowledge** from ARENA knowledge-bank documents, structured for two uses:
1. **Reference-class analysis** — categorise delivery events so past projects inform forecasts for new ones
2. **Intervention planning** — capture what resolved or mitigated issues so a portfolio manager can identify successful interventions for recurring failure patterns

---

## What to extract

- Delivery events: failures, delays, rescopes, cost issues, successes
- Transferable lessons a future project manager could act on
- Phase-specific findings grounded in specific project evidence
- Patterns that repeat or are explicitly generalised in the document

## What NOT to extract

- Generic statements not grounded in specific evidence ("stakeholder engagement is important")
- Promotional content ("this project demonstrated world-leading results")
- Pure technical performance data with no delivery implication (efficiency measurements, energy output figures)
- Repeated descriptions of the same event at different levels of detail — extract once at the most specific level

## Extracted tables

Tables from the source document are provided as CSV blocks under the heading
**"Extracted tables from this document"**, labelled by page number and table index
(e.g. "page 6, table 0"). Use these in preference to reconstructing table data from
prose references — the CSV blocks contain the clean extracted data. The page number
in each label can be used to populate `source_pages` when the evidence comes from a table.

---

## How many records per document

Extract as many as the document genuinely warrants — do not pad, do not truncate. There is no upper limit. If a document warrants 30 records, extract 30. Prioritise by signal quality:
1. Failures, delays, rescopes with clear lessons
2. Successful delivery events with transferable lessons (what worked and why)
3. Phase-specific findings a project manager at that phase could act on
4. General project-level observations — lowest priority

---

## Mandatory fields

### `record_id`
System-generated. Do not modify.

---

### `source_title`
Normalised document title, extracted from the document header.

---

### `publish_date`
Format: YYYY-MM or YYYY-MM-DD. Use document metadata or header.

---

### `project_name`
Canonical project name as used in the document.

---

### `what_happened`
1–2 sentences. The delivery event — what occurred. State the facts in neutral delivery language.

**Distinction from `lesson_learnt`:** `what_happened` = the event. `lesson_learnt` = the implication.

**Document-type trap:** Most ARENA KB documents are final reports or lessons-learnt reports. Do not write in the tone of the document ("this report found that..."). Describe the underlying project event.

✓ "Grid connection approval took 14 months and required two full resubmissions after the network operator imposed additional technical requirements not communicated at the outset."

✗ "The project experienced important learnings in relation to grid connection that will inform future deployments."

---

### `lesson_learnt`
1–2 sentences. The transferable implication — what a future project manager should do differently, watch for, or replicate.

If the document states an explicit lesson, use it verbatim or near-verbatim. If not, infer from the event — but only when the implication is unambiguous.

**Quality floor:** The lesson must be specific enough that a project manager in a similar situation would know what to do. Test: could someone act on this without reading the source document? If not, make it more specific. Generic platitudes are not acceptable.

✓ "Engage the network operator before finalising technical design — connection standards imposed after design freeze required two full resubmissions and added 14 months."

✗ "Early planning reduces delays."
✗ "Stakeholder engagement is important for successful project delivery."

---

### `issue_severity`
Magnitude of the delivery issue. Enables severity-weighted reference-class analysis.

**Allowed values:**
- `none` — no delivery issue; project proceeded as planned or with trivial friction. Use with `failure_mode: no major failure stated`.
- `minor` — delay under 1 month, cost variance under 5%, or a technical issue resolved within normal contingency; no material effect on final outcomes.
- `moderate` — delay 1–6 months, cost variance 5–20%, or a technical issue requiring meaningful rework; outcomes achieved but with friction.
- `major` — delay over 6 months, cost variance over 20%, significant rescope, or an issue that substantially changed what the project delivered.
- `critical` — project discontinued, abandoned, or so fundamentally altered as to represent a different project.

When no financial or schedule data is available, calibrate from the event description. A rework resolved within days is `minor`; one that consumed a construction season is `major`.

---

## Inferred fields
*Populate when evidence supports medium confidence or better. Leave null if unclear — do not guess.*

### `project_type`
Reference-class grouping by delivery archetype. Classify by the dominant delivery object, not every technology mentioned.

**Allowed values:** generation · storage · network/grid · DER/customer-side · transport electrification · industrial decarbonisation · manufacturing/supply chain · software/data/digital · enabling infrastructure · multi-technology/hybrid

A solar farm with co-located battery storage is `generation` if the solar component drove delivery; `storage` if the battery integration was the primary delivery challenge; `multi-technology/hybrid` only if genuinely inseparable.

---

### `project_scale_band`
Use the smallest reliable scale band the document supports.

**Allowed values:** lab/bench · pilot · demonstration · first commercial/FOAK · commercial expansion · utility/large-scale · programmatic/portfolio-level

**Demonstration vs. first commercial/FOAK boundary:** Use `demonstration` when the project's primary goal is proving technical feasibility — designed to generate evidence, not to operate commercially. Use `first commercial/FOAK` when the project is structured as a real commercial deployment that happens to be the first of its kind. When in doubt, look for a commercial revenue stream or offtake agreement. If one exists, use `first commercial/FOAK`.

---

### `lifecycle_phase`
The phase in which the main issue or insight *occurred* — not the project's overall current phase and not the phase of the document.

**Allowed values:** concept/feasibility · development/design · approvals/contracting · procurement · construction/installation · commissioning/integration · operations · variation/re-scope · close-out/post-project review

**Document-type trap:** Most ARENA KB documents are final reports or lessons-learnt reports written during close-out. Do not assign `close-out/post-project review` because the document is a final report. Assign the phase the event took place in. A commissioning failure documented in a final report is `commissioning/integration`.

**Commissioning/integration vs. operations boundary:** Use `commissioning/integration` for first-time activation, integration testing, control system configuration, grid connection commissioning, or any event before stable commercial operation. Use `operations` when the asset was already in stable commercial operation and the issue arose during ongoing service. When unclear: default to `commissioning/integration` for technical failures; `operations` for commercial or demand failures discovered after go-live.

**Invalid value:** `data/validation/testing` belongs to `delay_category`, not `lifecycle_phase`. Never use it here.

---

### `proponent_type`
The lead delivery actor — the organisation primarily responsible for delivery outcomes. ARENA is a funder and facilitator, not a proponent.

**Allowed values:** project developer · utility/energy retailer · network business · industrial operator · fleet/logistics operator · manufacturer/OEM · technology vendor · research organisation/university · consortium/multi-party venture · government/public-sector body · community/local body

---

### `delay_category`
Use only when delay is a meaningful part of the lesson. Leave null if timing friction is implied but not clearly described. Use `no material delay stated` only when the document positively confirms the project ran to schedule.

**Allowed values:** no material delay stated · approvals/regulatory · grid connection/system studies · procurement/supply chain · financing/commercial close · construction/installation · commissioning/integration · data/validation/testing · stakeholder/land/community · internal governance/resourcing

---

### `failure_mode`
Dominant failure mode. Use `no major failure stated` when the document presents a positive lesson with no failure. If a second failure mode is independently and clearly evidenced, populate `secondary_failure_mode`.

**Allowed values:** no major failure stated · technical underperformance · integration failure · schedule slippage · cost overrun · resource/capability shortfall · commercial/demand failure · regulatory misfit · data quality/measurement failure · design assumption failure · governance/coordination failure

**Cost overrun — indirect language:** ARENA documents rarely state cost overruns directly. Also code `cost overrun` when the document uses: "required additional funding", "contingency was consumed", "budget was revised upward", "scope was reduced to remain within budget", "required additional ARENA funding". These are substantive evidence of cost variance even without a percentage figure. Note: cost overrun appeared in only 1% of v1 records — implausibly low. Apply the indirect language guidance to improve capture.

---

### `outcome_class`
What the project event ultimately produced. Not a moral judgment — a compact description of the result.

**Allowed values:** successful demonstration · partial success · delayed but recoverable · re-scoped/adapted · knowledge generated despite setback · discontinued/not progressed · follow-on scale-up enabled · policy/market influence only

A project that failed technically but generated significant learning is `knowledge generated despite setback`, not `discontinued/not progressed`.

---

## Optional overlay fields
*Populate when clearly evidenced. Leave null otherwise.*

### `secondary_failure_mode`
A second failure mode, independently and clearly evidenced — not implied, not a minor secondary effect, not the same issue described twice. Same allowed values as `failure_mode`, excluding `no major failure stated`.

---

### `intervention_note`
1 sentence. What was specifically done to resolve or mitigate the issue.

**Strongly recommended** when `failure_mode` ≠ `no major failure stated`. Leave null only if the document does not describe a resolution or mitigation.

✓ "Engaged a specialist grid connection consultant and worked directly with the NSP — the third application was approved within 6 weeks."
✗ "The team worked hard to resolve the issues."

---

### `transferability`
How broadly applicable the lesson is across the ARENA portfolio.

**Allowed values:**
- `narrow` — specific to this technology type, regulatory context, or project configuration; unlikely to transfer without significant adaptation
- `moderate` — applies to similar project types, technology families, or proponent archetypes; requires some adaptation
- `broad` — applies across most ARENA-funded project types regardless of technology domain

---

### `delay_magnitude`
Duration band. Only populate when `delay_category` is populated. Use `not quantified` when a delay is described but no duration given — do not leave null when duration can be estimated from context ("missed two construction seasons" → 1–3 years).

**Allowed values:** <1 month · 1–3 months · 3–12 months · 1–3 years · >3 years · not quantified

---

### `technology_domain`
Secondary to delivery structure. Populate for technology retrieval.

**Allowed values:** battery storage · hydrogen · solar PV · solar thermal · wind · DER · demand response · EV · bioenergy · industrial renewables · grid/system stability · hybrid systems · pumped hydro · other

---

### `source_pages`
The page number(s) in the source document where the evidence for this record appears.

The document text contains HTML comments marking each page boundary in the format `<!-- page N -->`. Identify which page(s) the `evidence_excerpt` falls on by finding the nearest preceding `<!-- page N -->` marker(s). If the evidence spans multiple pages, list all of them.

**Format:** a YAML list of integers, e.g. `[12]` for a single page or `[12, 13]` for a span. Leave null only if no page markers are present in the document or the evidence cannot be located to a specific page.

This field enables direct deep-links to the source page in the PDF from the dashboard (`pdf_url#page=N`).

---

### `evidence_excerpt`
Direct quote or specific data point from the source document.

**Strongly recommended — treat as near-mandatory.** This is the only field directly verifiable by text search against the source. It is the primary quality assurance anchor. Leave null only when the document contains no quotable text relevant to the record (rare — applies mainly to interview or workshop-format documents).

---

### `confidence_note`
Note when a field classification was genuinely ambiguous or two valid values were close. Also used by the reconciliation step to record majority-vote outcomes.

---

## Field population summary

| Field | Status |
|-------|--------|
| record_id, source_title, publish_date, project_name | Always populate |
| what_happened, lesson_learnt, issue_severity | Always populate |
| project_type, project_scale_band, lifecycle_phase, proponent_type | Populate at medium+ confidence |
| delay_category, failure_mode, outcome_class, technology_domain | Populate at medium+ confidence |
| evidence_excerpt, intervention_note | Strongly recommended |
| source_pages | Strongly recommended — extract from `<!-- page N -->` markers |
| secondary_failure_mode, transferability, delay_magnitude, confidence_note | Populate when clearly evidenced |
