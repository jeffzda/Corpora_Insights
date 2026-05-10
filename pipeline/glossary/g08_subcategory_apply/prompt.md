# Sub-category assignment

You proposed a sub-categorisation scheme for {corpus_full_name} glossary's largest categories. Now apply it: assign each entry to one subcategory.

## The taxonomy

{taxonomy_block}

## Task

For each input entry below, return its subcategory using the EXACT subcategory name from above. If an entry genuinely doesn't fit any subcategory in its top-level (rare), assign it `"other"` and the reader will fall back to the top-level label.

If an entry is genuinely cross-cutting, pick the subcategory it primarily fits and let the reader infer the rest from context — don't multi-tag.

## Output

Strict JSON, no extra text. Compact schema:

```json
{{"assignments": [{{"t": "TERM1", "s": "Subcategory name"}}]}}
```

One entry per input term, in input order. No commentary.

## Input — {n_total} entries grouped by top category

{entries_block}
