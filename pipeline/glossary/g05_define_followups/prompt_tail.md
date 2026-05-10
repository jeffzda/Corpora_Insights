# Corpus glossary — tail recovery

Producing a study-guide glossary for {corpus_full_name}. Each input term was extracted from this corpus and ranked by frequency.

These are the lowest-frequency acronyms from the top-N cohort that the initial pass truncated before reaching. Same task as the initial pass: produce a glossary entry for each.

## Schema (compact — single-letter keys)

For each input term, return one JSON entry with these fields:

- `t`: the canonical surface, exactly as given.
- `e`: full expansion of the abbreviation/term. null if no plausible expansion.
- `c`: ONE of: technology, market, regulation, organisation, programme, standard, concept, location, unit, event, person, noise.
- `d`: plain-English definition in the {corpus_short_description} context. **HARD CAP: 30 words. No exceptions.** null if `c` is `noise`.
- `x`: ONE short sentence on how the term shows up in the corpus. **Only populate if the term has high coverage (≥50 unique docs in input metadata); else null.**
- `n`: notes — ambiguity flags or important sub-terms. null if none.
- `u`: true if you're not confident in the expansion or definition; false otherwise.

## Style

- Australian English spelling.
- {style_guidance}
- Be honest about noise — sentence fragments, generic English mis-caught, ambiguous abbreviations → `c: noise`, `d: null`.
- Don't pad. null over "N/A".
- Don't invent named programmes; if unsure, set `u: true`.

## Output

Strict JSON, no extra text:

```json
{{"entries": [{{"t":"<TERM>","e":"<expansion>","c":"<category>","d":"<<=30-word def>","x":"<one sentence or null>","n":null,"u":false}}]}}
```

One entry per input term, in input order.

## Input — {n_terms} terms

{terms_block}
