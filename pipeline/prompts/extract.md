You are extracting structured insight records from documents in the following corpus:

{domain_context}

Extract every discrete finding or insight the document warrants. There is no upper limit — do not stop early, do not anchor only on the executive summary. Read the full document including appendices, methodology sections, and tables. If a dense document warrants 30 records, extract 30.

Do NOT assign categories, themes, failure modes, or any taxonomy labels. Extract factual observations only. Taxonomy will be applied in a separate downstream step.

---

## What to extract

- Findings grounded in specific evidence within the document
- Deficiencies, risks, gaps, failures, or positive observations
- Transferable lessons — what a practitioner in a similar situation should do differently, watch for, or replicate
- Patterns that repeat or are explicitly generalised in the document

## What NOT to extract

- Generic statements not grounded in specific evidence ("stakeholder engagement is important")
- Promotional content ("this project demonstrated world-leading results")
- Pure data with no actionable implication (raw measurements, output figures with no delivery context)
- Repeated descriptions of the same finding at different levels of detail — extract once at the most specific level

## Extracted tables

Tables from the source document may be provided as CSV blocks under the heading
**"Extracted tables from this document"**, labelled by page number and table index
(e.g. "page 6, table 0"). Use these in preference to reconstructing table data from
prose references — the CSV blocks contain the clean extracted data. The page number
in each label can be used to populate `source_pages` when the evidence comes from a table.

---

## Output format

Output a YAML list. Each record is one item. Use null for unpopulated fields. Do not use empty strings.

If the document contains no extractable insight records, output exactly:
no records extracted

```yaml
- record_id: {record_id_prefix}-0001
  source_title: "Document title as stated in the document header"
  publish_date: "YYYY-MM or YYYY-MM-DD"
  what_happened: "Detailed narrative of the finding or event — cause, mechanism, and impact. Include specific numbers, durations, dollar amounts, and named entities where available. 2-4 sentences."
  lesson_learnt: "The transferable implication — what a practitioner in a similar situation should do differently, watch for, or replicate. Must be specific enough to act on without reading the source document. 1-2 sentences. Null if no lesson is stated or clearly implied."
  issue_severity: major
  intervention_note: "What was specifically done to resolve or mitigate the issue. 1 sentence. Null if not described."
  evidence_excerpt: "Verbatim quote from the source document that grounds this record. Near-mandatory."
  source_pages: [7]
  confidence_note: null
```

---

## Field guidance

### `what_happened`
1-4 sentences. The finding or event — what occurred or was observed. State the facts in neutral diagnostic language.

**Quality floor:** Must include enough concrete detail that a reader understands the specific mechanism, not just the category. Include quantities (dollar amounts, durations, percentages) and named entities (organisations, systems, locations) where the document provides them.

Good: "Grid connection approval took 14 months and required two full resubmissions after the network operator imposed additional technical requirements not communicated at the outset."

Bad: "The project experienced delays relating to grid connection."

### `lesson_learnt`
1-2 sentences. The transferable implication — what a practitioner should do differently, watch for, or replicate.

If the document states an explicit lesson, use it verbatim or near-verbatim. If not, infer from the finding — but only when the implication is unambiguous.

**Quality floor:** The lesson must be specific enough that a practitioner in a similar situation would know what to do. Generic platitudes are not acceptable.

Good: "Engage the network operator before finalising technical design — connection standards imposed after design freeze required two full resubmissions and added 14 months."

Bad: "Early planning reduces delays."

### `issue_severity`
Factual assessment of the magnitude of the finding.

**Allowed values:**
- `none` — no issue; things proceeded as planned or with trivial friction.
- `minor` — small impact resolved within normal contingency; no material effect on outcomes.
- `moderate` — meaningful rework, friction, or delay; outcomes achieved but with notable effort.
- `major` — significant impact on scope, cost, schedule, or outcomes.
- `critical` — fundamental failure, discontinuation, or issue so severe as to change the nature of the endeavour.

When no financial or schedule data is available, calibrate from the description.

### `intervention_note`
1 sentence. What was specifically done to resolve or mitigate the issue. Leave null only if the document does not describe a resolution or mitigation.

### `evidence_excerpt`
Direct quote or specific data point from the source document. **Near-mandatory** — this is the primary quality assurance anchor and the only field directly verifiable by text search against the source. Leave null only when the document contains no quotable text relevant to the record (rare).

### `source_pages`
Page number(s) where the evidence appears. The document text contains HTML comments marking page boundaries: `<!-- page N -->`. Find the nearest preceding marker(s) for the evidence_excerpt. Format: a YAML list of integers, e.g. `[12]` or `[12, 13]`. Leave null if no page markers are present.

### `confidence_note`
Note any genuine ambiguity, time-sensitivity, or quality concerns. For older documents, flag findings that may be superseded — e.g. "Published 2014 — cost and maturity findings likely superseded by subsequent deployment."

---

## How many records per document

Extract as many as the document genuinely warrants — do not pad, do not truncate. Prioritise by signal quality:
1. Findings with clear lessons and specific evidence
2. Significant observations with transferable implications
3. General observations — lowest priority

---

## Document to process

[Document list and markdown content appended by the orchestrating script]

Start record_id numbering at {record_id_prefix}-[START_ID].
