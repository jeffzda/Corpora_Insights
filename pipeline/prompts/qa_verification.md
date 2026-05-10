You are sense-checking an extracted delivery insight record against a passage from its source document.

You have two jobs:

1. GROUNDING: Is what_happened and lesson_learnt supported by the passage?
2. CLASSIFICATION: Are the applied taxonomy labels defensible given the passage?
   You are not re-classifying — just flagging labels that are clearly wrong or implausible.
   A label is defensible if a reasonable person could apply it given the text, even if another
   label might also fit.

Output ONLY a YAML mapping with these six fields — nothing else:

grounding_verdict: confirmed|plausible|unsupported|fabricated
classification_verdict: ok|questionable|wrong
classification_note: "one sentence — only flag specific labels that are clearly misapplied; null if ok"
source_text: "exact quote from the passage that best supports or contradicts the record"
source_page: N   # integer page number from nearest preceding <!-- page N --> marker; null if absent
grounding_note: "one sentence explaining grounding verdict, especially if not confirmed; null if confirmed"

Grounding verdict definitions:
- confirmed: what_happened and lesson_learnt are clearly supported by specific text in the passage
- plausible: consistent with the passage but supporting text is ambiguous or indirect
- unsupported: makes claims not evidenced in the passage
- fabricated: contains specific details (dates, figures, names, quotes) not present in the passage

Classification verdict definitions:
- ok: all applied labels are defensible given the passage
- questionable: one or more labels seem like a stretch but could be argued
- wrong: one or more labels are clearly inconsistent with what the passage describes

---

## Record to verify

{{record_yaml}}

---

## Source passage

{{source_passage}}
