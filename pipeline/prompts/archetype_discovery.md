You are analysing realised delivery events from {domain_name}-funded {{category}} projects to discover recurring failure patterns.

Your task: identify SPECIFIC, RECURRING delivery problems — not abstract categories.

CRITICAL RULES:
- Name the SPECIFIC thing that fails, breaks, or is absent. Not the category of failure.
- Each archetype must be specific enough that a portfolio manager could ask a due diligence
  question based on the name alone.
- TEST: "Could a decision-maker ask a proponent a specific question about this?" If not, it's too vague.
- Group events where the SAME SPECIFIC THING keeps going wrong across multiple projects.
  Two events where "the degradation model was wrong" are the same pattern.
  An event where "the degradation model was wrong" and one where "the firmware
  was locked" are DIFFERENT patterns, even though both are "technology performance."
- Minimum {min_events} events to warrant a named archetype. Below that, assign to a parent-level
  "other [parent category] failures" catch-all.
- Each parent category MUST have exactly one catch-all archetype named
  "other [parent category name] failures" for events below the clustering threshold.
- Parent categories should describe the DOMAIN of failure (what area of the project),
  not the mechanism (what type of mistake).

For each archetype, provide:
- A specific name (under 80 characters, noun phrase not sentence)
- A one-sentence description
- The count of events matching this pattern
- 2-3 example event titles

Respond with JSON only (no markdown, no explanation):
{{"archetypes": [{{"name": "...", "parent_category": "...", "description": "...", "count": N, "example_titles": ["...", "..."]}}]}}
