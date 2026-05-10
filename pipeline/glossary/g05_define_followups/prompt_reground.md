# Corpus glossary — corpus-grounded re-grounding

Producing a study-guide glossary for {corpus_full_name}. Each input was flagged as uncertain by an earlier pass.

For each, you have the earlier model's first attempt PLUS up to 3 sample narrative snippets from the corpus where the term actually appears. Use the corpus context to confirm or correct the prior expansion/definition. If the corpus context resolves the ambiguity → set `u: false`. If still ambiguous after seeing the context → keep `u: true` and explain in `n`.

## Schema (compact — single-letter keys)

- `t`: the canonical surface, exactly as given.
- `e`: full expansion. null if no plausible expansion.
- `c`: ONE of: technology, market, regulation, organisation, programme, standard, concept, location, unit, event, person, noise.
- `d`: plain-English definition. **HARD CAP: 30 words.** null if `c` is `noise`.
- `x`: ONE sentence on how the term shows up in the corpus.
- `n`: notes — surface any remaining ambiguity here.
- `u`: true if still uncertain after seeing corpus context; false if context resolved it.

## Style

- Australian English spelling.
- {style_guidance}
- Use the corpus snippets as evidence. If they contradict the prior attempt, override.

## Output

Strict JSON, no extra text:

```json
{{"entries": [{{"t":"<TERM>","e":"<expansion>","c":"<category>","d":"<<=30-word def>","x":"<one sentence or null>","n":null,"u":false}}]}}
```

One entry per input term, in input order.

## Input — {n_terms} terms

{terms_block}
