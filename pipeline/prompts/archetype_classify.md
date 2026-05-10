Classify this delivery event into failure archetypes from the {{category}} taxonomy.

RULES:
- Assign exactly ONE primary archetype that best describes the specific failure.
- Optionally assign ONE secondary archetype ONLY if a genuinely distinct second failure
  mechanism is present. The secondary MUST be a different archetype from the taxonomy below.
- Your primary and secondary MUST be one of the VALID NAMES listed below. Copy the name
  EXACTLY — do not paraphrase, abbreviate, or invent new names.
- NEVER use a parent category name as an archetype. Always pick the most specific matching
  archetype, or the "Other ... failures" catch-all for that parent category.
- Most events should have ONLY a primary archetype. A secondary is the exception, not the norm.
- If no archetype fits well, use the relevant "Other ... failures" catch-all.
- Confidence should reflect how well the archetype DESCRIBES the event, not how well it
  ranks against alternatives. If the fit is poor, use the Other catch-all with high confidence
  rather than the closest named archetype with high confidence.

TAXONOMY:
{{taxonomy_text}}

VALID NAMES (use these exact strings only):
{{valid_names}}

Respond with JSON only:
{{"primary": "archetype name", "primary_category": "parent category", "confidence": 0.0-1.0, "secondary": "archetype name or null", "secondary_category": "parent category or null"}}
