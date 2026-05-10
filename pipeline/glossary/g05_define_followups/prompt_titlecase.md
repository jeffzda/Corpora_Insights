# Corpus glossary — titlecase pass

Producing a study-guide glossary for {corpus_full_name}. Each input term was extracted from this corpus via title-case proper-noun matching and ranked by frequency.

These are titlecase surfaces — organisation names, programme names, standards, conference names, concept phrases. Many will be named programmes or initiatives, organisations, market mechanisms, or standards bodies. Some will be project-specific names that the catalogue should already cover — for those, set `c: noise` since they don't belong in a generic glossary. Person names → `c: person`. Locations → `c: location`. Single-occurrence project codenames → `c: noise`.

## Schema (compact — single-letter keys)

- `t`: the canonical surface, exactly as given.
- `e`: full expansion. null if it's already a full name (not abbreviated).
- `c`: ONE of: technology, market, regulation, organisation, programme, standard, concept, location, unit, event, person, noise.
- `d`: plain-English definition in the {corpus_short_description} context. **HARD CAP: 30 words.** null if `c` is `noise`.
- `x`: ONE sentence on how the term shows up in the corpus. **Only populate if ≥50 unique docs.**
- `n`: notes. null if none.
- `u`: true if you're not confident; false otherwise.

## Style

- Australian English spelling.
- {style_guidance}
- Be honest about noise.
- Don't pad. null over "N/A".

## Output

Strict JSON, no extra text:

```json
{{"entries": [{{"t":"<TERM>","e":"<expansion>","c":"<category>","d":"<<=30-word def>","x":"<one sentence or null>","n":null,"u":false}}]}}
```

One entry per input term, in input order.

## Input — {n_terms} terms

{terms_block}
