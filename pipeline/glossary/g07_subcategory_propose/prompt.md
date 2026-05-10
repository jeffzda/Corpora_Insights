# Sub-clustering proposal — corpus glossary

You are designing a more navigable taxonomy for {corpus_full_name} study-guide glossary aimed at {audience_persona}. The current glossary has top-level categories that are too big to navigate. The categories below are the ones to refine.

## Audience and use

The reader is {audience_persona}. Their workflow includes reading synthesis reports that cite many acronyms and named entities, looking up "what is X" or "what kind of X is this" for entries they don't recognise. They benefit from sub-categories that map to their mental model: kinds of thing that recur in this corpus.

Don't propose categories that exist for taxonomic completeness without serving the workflow. Don't make the categories too fine — 4-8 subcategories per top category is the right granularity. Each subcategory name should be self-explanatory.

## Task

For each of the categories below, propose:

1. A set of subcategories — 4-8 each, more if genuinely needed.
2. A short rationale (one sentence per subcategory) explaining what fits there.
3. A sample assignment — for each subcategory, list 3-6 example terms from the input.
4. An "edge cases" note where some entries don't fit cleanly.

Output strict JSON, no commentary or markdown fences:

```json
{{
  "<category-name>": {{
    "subcategories": [
      {{"name": "...", "description": "...", "examples": ["TERM1", "TERM2"]}}
    ],
    "edge_cases": "..."
  }}
}}
```

## Input data

Each entry below is `[term] expansion | n_docs corpus coverage | definition`.

{categories_block}

Return only the JSON proposal. No commentary.
