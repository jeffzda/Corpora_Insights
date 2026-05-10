You are reading a single {{domain_noun}}. Extract every
finding of note — a finding is any statement where the {{author_noun}} identifies a
deficiency, risk, gap, or positive observation in the {{unit_noun}}'s
governance, processes, or performance.

For each finding, produce:
  - gloss: one short clause (≤20 words) describing the mechanism of the
    finding, at a level that abstracts from the specific subject matter.
    State it in the {{author_noun}}'s diagnostic voice, not promotional voice.
    Example: "Risk register not maintained after initial creation"
  - trigger: the verbatim phrase or sentence from the source that
    supports the gloss (≤300 chars). Quote exactly.

Do NOT assign categories, tags, themes, or a taxonomy. Do NOT group findings.
Do NOT editorialise. Extract atomic findings only.

Return a JSON array. No prose before or after. Example:

[
  {"gloss": "Absence of independent assurance over data collection", "trigger": "The entity did not have any independent assurance mechanism in place for the data it reported."},
  {"gloss": "Failure to update risk plan after scope change", "trigger": "Following the 2019 expansion, the risk management plan was not revised."}
]

Source document follows.

---

