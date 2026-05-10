You are classifying delivery insight records from {domain_name} ({domain_full_name}) projects.

Each record describes something that happened (or was observed) during a project. Your job is to classify TWO things:

## 1. EVENT TYPE — what kind of record is this?

Choose exactly one:

**realised_delivery_event**: The project experienced a concrete adverse outcome — a delay, cost increase, performance shortfall, equipment failure, scope change, or cancellation. The cause can be internal OR external (weather, pandemic, regulatory change, market shift) — what matters is that the project SUFFERED A MEASURABLE CONSEQUENCE. If a risk was identified AND it materialised during the project, this is a realised delivery event, not an identified future risk.

**design_technical_finding**: Analysis, testing, simulation, or modelling revealed a technical limitation, constraint, or unexpected behaviour. Nothing went wrong operationally — the finding IS the output of the work, not a failure of the work. Examples: lab experiments showing material degradation, modelling revealing a design constraint, testing showing equipment behaviour differs from assumptions.

**identified_future_risk**: A study or assessment flagged something that COULD happen but HAS NOT MATERIALISED. Risk register entries, "there is a risk that...", scenario modelling of potential outcomes. CRITICAL: if the risk actually materialised during the project (the project experienced the consequence), classify as realised_delivery_event instead.

**contextual_observation**: The project is COMMENTING ON market conditions, policy gaps, industry structure, cost curves, or other external context — not suffering from them. The record describes the environment, not a project event. Examples: "no market mechanism exists for X", "the cost of technology X has declined".

## 2. CONSEQUENCE LEVEL — how bad was it? (only for realised_delivery_event)

If event_type is realised_delivery_event, also classify the consequence:

**adaptation_required**: The project adjusted scope, design, timeline, or approach, but there is no evidence of quantifiable damage. The team adapted and moved on.

**material_impact**: There is evidence of quantifiable cost, schedule, or performance impact — dollar amounts, specific delay durations, measurable performance shortfalls, liquidated damages, budget overruns.

**project_threatening**: The project's viability was in question — references to potential cancellation, fundamental commercial unviability, existential technical challenges, inability to secure financing or offtake.

**project_terminated**: The project was discontinued, abandoned, or not progressed. The record explicitly states the project did not proceed.

If event_type is NOT realised_delivery_event, set consequence_level to null.

## KEY DECISION RULES

- If the project experienced a CONSEQUENCE (cost, delay, performance loss, scope change), it is realised_delivery_event regardless of whether the cause was external.
- "The project found that X is not commercially viable" from a feasibility study that was DESIGNED to answer that question = design_technical_finding (the finding is the deliverable).
- "The project was discontinued because X was not commercially viable" = realised_delivery_event with consequence project_terminated.
- "There is a risk that X could happen" where X did NOT happen = identified_future_risk.
- "X happened, causing Y delay/cost" = realised_delivery_event.
- Generic industry commentary with no project-specific consequence = contextual_observation.

Respond ONLY with a JSON object (no markdown, no explanation):
{{"event_type": "realised_delivery_event", "consequence_level": "material_impact", "confidence": 0.9}}

For non-delivery events:
{{"event_type": "contextual_observation", "consequence_level": null, "confidence": 0.85}}
