You are designing a structured extraction schema for a document corpus.

## Domain description

{domain_description}

## Sample documents

Below are {n_samples} sample documents from this corpus. Read them carefully to understand:
1. What kinds of structured information recur across documents
2. What enumerated fields would capture the key dimensions of each record
3. What the natural "unit of extraction" is (one record per finding? per recommendation? per project event?)

{sample_documents}

## Your task

Design a complete extraction schema for this corpus. For each field:
1. Give it a clear name (snake_case)
2. Write a one-sentence description of what it captures
3. List all valid enum values (if enumerated) or describe the expected format (if free text)
4. Mark whether it is mandatory, inferred (when evidence supports), or optional

Think about:
- What would a portfolio manager / decision-maker want to filter and cross-tabulate?
- What fields enable reference class forecasting (base rates of outcomes by category)?
- What fields provide traceability back to source documents?

## Output format

Respond with a YAML document containing:

```yaml
domain:
  name: "Short name"
  full_name: "Full organisation/corpus name"
  description: "One sentence"
  record_id_prefix: "PREFIX"

unit_of_extraction: "One sentence describing what constitutes a single record"

fields:
  mandatory:
    - name: field_name
      description: "What this captures"
      type: enum|text|date|integer|boolean
      values: [list, of, valid, values]  # for enum type only

  inferred:
    - name: field_name
      description: "What this captures"
      type: enum|text
      values: [list, of, valid, values]

  optional:
    - name: field_name
      description: "What this captures"
      type: enum|text
      values: [list, of, valid, values]

categories:
  - name: "Category name"
    description: "What documents fall in this category"

severity_scale:
  - value: none
    description: "No adverse outcome"
  - value: minor
    description: "..."
  # etc.
```

Be specific and grounded in what you observed in the sample documents. Do not invent fields
that have no basis in the samples. Prefer fewer, well-defined fields over many speculative ones.
