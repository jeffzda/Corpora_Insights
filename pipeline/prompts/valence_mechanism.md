You will read one extracted insight record from a renewable energy project document. The record has already been classified as containing an author-stated cause-effect relationship. Your job is to determine two things about the causal claim:

1. **Valence**: does the asserted cause-effect produce a desired outcome (positive), an undesired outcome (negative), or is the outcome value-neutral / descriptive (neutral)?

2. **Mechanism named**: does the record explicitly name the *causal mechanism* — the specific *how* or *why* — or does it just assert an outcome without explaining the mechanism?

## Valence guidance

- `negative` — author asserts that something caused an undesired outcome (delays, cost overruns, performance shortfalls, failures, problems, risks, gaps, deficiencies, things that broke or fell short)
- `positive` — author asserts that something caused a desired outcome (capability gains, cost reductions, performance improvements, successful demonstrations, mitigations that worked)
- `neutral` — the cause-effect is descriptive without value loading (e.g. "X varies with Y", "design A produces output B" without A being good or bad)

Be willing to call neutral when the author hasn't actually loaded value onto the outcome.

## Mechanism-named guidance

- `yes` — the record names a specific causal mechanism: a concrete *how* (e.g. "stakeholder issues caused delays because the consultation process required more iterations than planned", "voltage dropped because the inverter switched to fault-ride-through mode")
- `no` — the record asserts an outcome but doesn't explain *why* at the mechanism level (e.g. "the project was delayed by stakeholder issues" — outcome named, mechanism for why stakeholder issues produced delay is missing)

A mechanism is named when the *causal pathway* is articulated, not just the cause-label. "X caused Y because of Z" — Z is the mechanism. "X caused Y" without Z — outcome named, mechanism missing.

## Output

Strict JSON, no extra text:

```json
{"valence": "positive|neutral|negative", "mechanism_named": "yes|no", "mechanism_phrase": "<verbatim phrase from the record naming the mechanism, or empty if mechanism_named=no>", "confidence": "low|medium|high"}
```

The `mechanism_phrase` should be the verbatim string from the record that articulates the causal mechanism. If `mechanism_named=no`, leave it empty.

## Record context

You also have:
- The verbatim causal connective the author used (e.g. "due to", "led to")
- A short rationale from a prior classifier explaining why this record was judged causal

These are hints — not binding. Read the narrative and judge.

## Record

Connective: {connective}
Prior rationale: {rationale}

Narrative:
{narrative}
