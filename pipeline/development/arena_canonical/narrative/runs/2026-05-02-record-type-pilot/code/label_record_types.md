You are tagging extracted insight records with structural and valence axes. Each record describes a single finding from a project document. Read the record's `narrative`, `evidence`, and `intervention` (where present) and assign the axis values below. Do NOT use any lesson, recommendation, summary, or interpretive prose that may appear elsewhere — base your judgement only on the supplied fields.

# Inputs

You will receive a JSON list of records under the heading `## records`. Each record has:
- `id`: the record's unique ID
- `narrative`: 1-4 sentence factual description of the finding
- `evidence`: verbatim quote or close paraphrase from the source document
- `intervention`: action taken or null

# Output

Return one JSON object with a single top-level key `assignments` mapping to an array. Each assignment has the same `id` plus the six axis values below. No prose, no markdown fences, no commentary outside the JSON.

```
{
  "assignments": [
    {
      "id": "ARENA-DLV-XXXX-NNNN",
      "is_occurrence": "yes",
      "is_mechanism": "no",
      "is_specification": "no",
      "is_lesson": "no",
      "is_recommendation": "no",
      "valence": "negative"
    }
  ]
}
```

# Axes

## `is_occurrence` — yes | no
**`yes`** if the record describes a specific thing that *happened* during the project — an action taken, an outcome observed, a decision made, a result measured at a specific time and place. Realised events. Failures, successes, milestones all qualify.

**`no`** if the record is a general principle, a property description, a recommendation, or refers only to anticipated/possible events without describing them as having occurred.

## `is_mechanism` — yes | no
**`yes`** if the record names a *causal or technical pathway*: how or why something works, fails, or has the property it does. Physical mechanisms, organisational mechanisms, regulatory mechanisms all qualify. The record explains the *how*, not just the *what*.

**`no`** if the record states a fact or outcome without explaining a causal pathway.

## `is_specification` — yes | no
**`yes`** if the record describes parameters, scope, magnitudes, equipment IDs, organisational structures, dates, or program design — descriptive properties without causal framing or outcome valence.

**`no`** if the record is fundamentally about an outcome, a mechanism, or a prescription rather than a descriptive parameter.

## `is_lesson` — yes | no
**`yes`** if the record states a *generalised, transferable principle* derived from project experience. Phrased to apply beyond this specific project ("in similar situations…", "for V2G generally…", "when working in remote communities…"). The transferability is the diagnostic.

**`no`** if the record is purely about this specific project's facts.

## `is_recommendation` — yes | no
**`yes`** if the record states a *specific actionable directive* — a prescriptive imperative naming an action and (often) a target. "Engage X early", "Allocate Y", "Do Z before W". May be project-specific or forward-looking.

**`no`** if the record is descriptive rather than prescriptive.

## `valence` — positive | negative | neutral | no_valence
The valence captures whether the record references a positively or negatively coloured situation, including the underlying situation behind any prescriptive content.

- **`positive`** — the record references something that helped, worked, succeeded, or enabled. Includes positive outcomes (a project achievement) and positive properties (an enabling capability).
- **`negative`** — the record references something that hurt, failed, was constrained, or created friction. Includes negative outcomes (failures, delays), negative situations (a regulatory mismatch causing trouble), and the underlying negative situation behind a corrective recommendation ("don't assume X" → the underlying situation was a failure of assumption).
- **`neutral`** — the record references an outcome that's genuinely balanced or descriptive, neither helping nor hurting (e.g. a deployment that happened on schedule with no commentary on its result).
- **`no_valence`** — the record is purely structural, descriptive, or mechanism-focused with no positive or negative coloration. Specifications, factual statements about how things work, or unconditional design parameters typically land here. **Use `no_valence` whenever the record genuinely doesn't carry positive or negative colour, rather than defaulting to `neutral`.**

# Important

- Multiple boolean axes can be `yes` for one record. A record can be both `is_lesson` and `is_recommendation`, or both `is_mechanism` and `is_specification`. Tag honestly; do not force a single primary type.
- The boolean axes are independent — pick each one on its own merits, not relative to the others.
- For `valence`, prefer `no_valence` over `neutral` when the record is purely descriptive without outcome reference. `neutral` is reserved for records where there *is* an outcome but it's balanced.

# Records to tag

## records

[Records appended by the orchestrating script]
