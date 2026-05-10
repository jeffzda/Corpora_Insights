You are grouping already-extracted insight records into events.

An **event** is a *discrete, atomic occurrence* — a single thing that happened, was observed, was decided, or was found at a specific time and place during a project. Two records describe the SAME event when they describe the same singular occurrence, even if they cover different *aspects* of it: the cause, the mechanism, the intervention, the outcome, the lesson learnt, the recommendation derived from it, or contextual specification of the equipment or process involved. Records that share an event_id may legitimately describe different mechanism families — that is by design. Downstream clustering will reconnect them across the mechanism axis.

# Inputs

You receive:

1. **Prior events list**: events already established by earlier batches and/or earlier documents on this project. Each entry has `event_id` (e.g. `EVT-0017`), `event_name`, a 1-2 sentence description, and an exemplar mechanism phrase.
2. **Batch of records to group**: a JSON array of records. Each record has `id`, `narrative`, `lesson`, `evidence`, `intervention` and other context fields. They are extracted findings — your job is only to assign an event identity to each one, NOT to re-judge their content.

# Your task

For every record in the batch, output exactly one assignment:

- **Assign to an existing event** — if the record describes the same singular occurrence as a previously-listed event, set `event_id` to that event's ID and copy the `event_name` verbatim from the prior list.
- **Declare a new event** — if no existing event fits, generate a new `event_id` of the form `EVT-NNNN` (use the next available number; if the prior events list contains `EVT-0017` as the highest, your new events start at `EVT-0018`) and write a clear `event_name` (5-15 words; concrete; mechanism-aware).

A record may legitimately describe a transition between two events. Use `event_ids: [EVT-0001, EVT-0007]` (a JSON array) instead of a single `event_id` when this is the case. Use this sparingly — most records map to one event.

# When to MERGE (same event)

Bias strongly toward merging records into existing events when they describe the same singular occurrence:

- **Same physical occurrence described in two reports** — e.g. the same approval delay or design problem mentioned in a milestone report and an end-of-project assessment.
- **Aspect-distinct records of one occurrence**: a record describing the *cause* of a delay, a record describing the *mechanism*, a record describing the *intervention*, a record describing the *outcome*, a record describing the *lesson learnt*, and a record stating a *recommendation* derived from it should all share one event_id when they refer to the same singular occurrence. Different mechanism *families* across these records is expected and desired — downstream clustering uses that span as evidence.
- **Recommendations or design suggestions arising from an occurrence**: a record stating a lesson, recommendation, or design implication that flows from a specific project occurrence (e.g. "based on the certification difficulty, future projects should…") attaches to the same event_id as the records describing the occurrence itself.
- **Near-paraphrases of the same finding** — even when one carries an extra clarifying clause.
- **Specification + finding about the specified equipment**: when a record describes a piece of equipment's specification *as part of explaining* a finding about that equipment, both belong to the same event.

# When to SPLIT (different events)

Only split when records describe genuinely distinct occurrences. The bar for splitting is high; when in doubt, merge:

- **Different INSTANCES of the same kind of thing** — Phase 1 commissioning delay vs Phase 2 commissioning delay; two separate grid faults at different times; two distinct field trials; two distinct vendors' versions of the same problem. Distinct dates, locations, equipment IDs, or named instances → different events.
- **Standalone principles unrelated to a specific project occurrence** — a general statement of best practice that doesn't trace back to any particular project event in the document. Rare in practice; almost all "general principles" in project reports are actually lessons distilled from specific occurrences and merge under those.

# Output format

Return one JSON object with two top-level keys: `assignments` (a list, one entry per input record) and `events` (the registry of every event referenced in your assignments — both inherited and newly declared). No prose, no markdown fences, no commentary outside the JSON.

```
{
  "assignments": [
    {
      "record_id": "ARENA-DLV-0844-0005",
      "event_id": "EVT-0017",
      "event_name": "Wallbox Quasar AS/NZS 4777 certification underestimation"
    },
    {
      "record_id": "ARENA-DLV-0844-0019",
      "event_id": "EVT-0017",
      "event_name": "Wallbox Quasar AS/NZS 4777 certification underestimation"
    },
    {
      "record_id": "ARENA-DLV-1347-0010",
      "event_id": "EVT-0028",
      "event_name": "REVS recommendation to incorporate AS/NZS 4777 review at procurement"
    }
  ],
  "events": [
    {
      "event_id": "EVT-0017",
      "event_name": "Wallbox Quasar AS/NZS 4777 certification underestimation",
      "description": "1-2 sentence description of the event.",
      "exemplar_mechanism_phrase": "short phrase capturing the mechanism, drawn from source language"
    }
  ]
}
```

# Inputs to process

## Prior events list

{{prior_events_block}}

## Records to group

{{records_block}}
