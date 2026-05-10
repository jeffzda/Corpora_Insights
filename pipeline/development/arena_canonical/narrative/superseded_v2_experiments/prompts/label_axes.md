You are labelling extracted insight records with a fixed set of categorical axis tags. The records were extracted from documents in the following corpus:

{domain_context}

Each record describes a single finding from a project document. Your job is to read each record and assign **independent** values for every axis below, based only on what the record's own text states or implies. Do not infer beyond what the record itself says.

---

## Output format

You will receive a YAML list of records under the heading `## records`. For each record, output **exactly one** YAML entry with the same `record_id` and the axis tags below — nothing else. Output as a YAML list inside a single `yaml` code block.

```yaml
- record_id: ARENA-DLV-0001
  causal_claim_made: yes
  causal_connective: "led to"
  valence: negative
  mechanism_named: yes
  mechanism_phrase: "AS/NZS 4777 voltage-ride-through requirements more onerous than EU equivalents"
  realisation: realised
  stakeholder: vendor
  interface_locus: regulatory
  outcome_class: schedule
```

If a record genuinely doesn't admit a value for a given axis, use `unspecified` for enum fields and `null` for verbatim-phrase fields. **Do not skip records** — emit one labelled entry per input record, in the same order.

---

## Axes

### `causal_claim_made` — yes | no
Did the record's text state or imply a causal relationship? "Yes" if the record uses connectives like *because, due to, led to, resulting in, caused by, drove, meant that, attributable to, as a result of, contributed to, enabled, prevented*. "No" if the record states facts without claiming causation.

### `causal_connective` — verbatim phrase | null
If `causal_claim_made: yes`, the verbatim connective phrase that signals the causation. Quote it exactly from the record's `what_happened` or `evidence_excerpt` field. Null if `causal_claim_made: no`.

### `valence` — positive | neutral | negative
Was the outcome described favourable (`positive`), neutral/descriptive (`neutral`), or unfavourable/failure-mode (`negative`) from the project's perspective?

### `mechanism_named` — yes | no
Does the record identify a *specific causal mechanism* (not just an outcome category)? "Yes" if it names a concrete physical, technical, organisational, regulatory, or behavioural pathway (e.g. "the AS/NZS 4777 voltage-ride-through requirements were more onerous than EU equivalents"). "No" if only an outcome or general category is stated without explanatory mechanism.

### `mechanism_phrase` — verbatim phrase | null
If `mechanism_named: yes`, the verbatim phrase from the record that names the mechanism. Null if `mechanism_named: no`.

### `realisation` — realised | anticipated | generic | mixed
- `realised` — describes something that actually occurred in the project.
- `anticipated` — describes a forward-looking expectation, plan, or risk.
- `generic` — describes a general principle not tied to a specific occurrence.
- `mixed` — combines realised and anticipated/generic content (use sparingly).

### `stakeholder` — proponent | customer | vendor | network | regulator | end_user | researcher | unspecified
Whose action, position, or constraint is the record primarily about? Use `unspecified` only when the record genuinely cannot be attributed to one stakeholder type.

### `interface_locus` — design | commissioning | operations | commercial | regulatory | pre_execution | unspecified
Where in the project lifecycle does the finding sit? Use `unspecified` when the record applies across phases.

### `outcome_class` — schedule | cost | safety | scope | commercial | reputational | equity | technical_performance | unspecified
What kind of outcome was affected? Use `unspecified` when the record is mechanism-only without a clear outcome.

---

## Records to label

## records

[Records appended by the orchestrating script]
