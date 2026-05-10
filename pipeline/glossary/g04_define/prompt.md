# Corpus glossary pass

You are producing a study-guide glossary for {corpus_full_name}. Each input entry is an acronym or term that the entity-extraction pipeline found in this corpus, ranked by frequency.

{glossary_purpose}

## Input

Each line below is `[surface] (n_total_mentions, n_unique_docs)  variants: [variant1, variant2, ...]`.

The surfaces are extracted programmatically. Most are technical or domain-specific terms used in the corpus. Some entries will be ambiguous (multiple expansions) or noise (sentence fragments, generic English words). Handle each honestly.

## Task

For every input term, return one JSON entry with these fields:

- `term`: the canonical surface, exactly as given.
- `expansion`: the full phrase this acronym/term abbreviates. If genuinely ambiguous given the {corpus_short_description} context, include the most likely expansion and note alternatives in `notes`. If no plausible expansion exists (it's not really an acronym, e.g. a phrase fragment), set `expansion` to null.
- `category`: one of: `technology`, `market`, `regulation`, `organisation`, `programme`, `standard`, `concept`, `location`, `unit`, `event`, `person`, `noise`. Use `noise` for sentence fragments, generic English words mis-caught as terms, or anything that should not appear in a glossary.
- `definition`: one to three plain-English sentences explaining what the term means in the {corpus_short_description} context. Aim for ~30-60 words; longer only if needed for a hard concept. Do NOT define `noise` entries — return null.
- `context`: one short sentence on how the term typically shows up in {corpus_short_description} (which kinds of documents, common phrases, what a {audience_persona} should know about it). One short sentence; null for `noise`.
- `notes`: optional. Use for ambiguity flags ("also stands for X in some industries"), date-bound caveats, or important sub-terms. null if none.
- `uncertainty`: true if you're not confident the expansion or definition is correct in the {corpus_short_description} context (e.g. multiple plausible expansions and you can't pick from priors alone). The downstream pipeline will run a corpus-grounded follow-up pass on uncertain entries.

## Style guide

- Australian English spelling (organisation, optimise, programme).
- {style_guidance}
- Don't invent named programmes or grants. If unsure whether a term is corpus-specific or general, mark `uncertainty: true`.
- Don't pad. Empty fields with null, not "N/A".
- Be honest about noise. If a "term" is "Project" or a sentence fragment, mark `category: noise` and don't fabricate a definition.

## Output

Strict JSON, no extra text. Single object with one key:

```json
{{"entries": [
  {{"term": "<TERM>", "expansion": "<full expansion>", "category": "<category>",
    "definition": "<plain-English definition>",
    "context": "<one sentence on how it shows up in this corpus>",
    "notes": null, "uncertainty": false}}
]}}
```

Return one entry per input term, in input order. No commentary, no preamble, no markdown fences.

## Input — {n_terms} terms

{terms_block}
