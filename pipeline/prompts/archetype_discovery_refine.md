You are analysing delivery events from {domain_name}-funded {{category}} projects that were NOT captured by the existing failure archetype taxonomy. Your task: find ADDITIONAL specific recurring patterns among these unclustered events.

EXISTING TAXONOMY (do NOT rediscover these — they already exist):
{{existing_taxonomy_text}}

CRITICAL RULES:
- Name the SPECIFIC thing that fails, breaks, or is absent. Not the category of failure.
- Each archetype must be specific enough that a portfolio manager could ask a due diligence
  question based on the name alone.
- TEST: "Could a decision-maker ask a proponent a specific question about this?" If not, it's too vague.
- Group events where the SAME SPECIFIC THING keeps going wrong across multiple projects.
- Minimum {min_events_refine} events to warrant a new archetype (smaller pool than initial discovery).
- If events genuinely don't cluster into anything specific, that's fine — leave them for the
  existing "Other ... failures" catch-alls. Do NOT force weak clusters.
- Do NOT create new parent categories unless none of the existing ones fit.
- Each NEW parent category (if any) MUST have an "Other [parent category name] failures" catch-all.
- Do NOT repeat or rename any archetype from the existing taxonomy above.

For each NEW archetype, provide:
- A specific name (under 80 characters, noun phrase not sentence)
- A one-sentence description
- The count of events matching this pattern
- 2-3 example event titles

Respond with JSON only (no markdown, no explanation):
{{"archetypes": [{{"name": "...", "parent_category": "...", "description": "...", "count": N, "example_titles": ["...", "..."]}}]}}
