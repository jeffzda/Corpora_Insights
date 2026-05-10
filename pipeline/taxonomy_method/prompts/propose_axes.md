You are given a list of atomic findings extracted from {{corpus_plural_noun}}.
Each finding has a short mechanism-level gloss and
a verbatim trigger phrase.

Your task: propose 2 to 4 orthogonal classification axes that together span
these findings. For each axis:

  - name: a short snake_case identifier
  - description: one sentence explaining what the axis classifies
  - values: 5 to 10 values, each with:
      - name (snake_case)
      - definition (one sentence)
      - 2 example gloss strings drawn verbatim from the findings list
  - independence_justification: why this axis does NOT covary with the
    others — ideally by naming a pair of findings that share this axis
    value but differ on every other axis
  - exhaustiveness_justification: why the value set covers the full
    range seen in the corpus, and what (if anything) is left over

Orthogonality is the hard constraint. If two axes you propose secretly
share a latent dimension (e.g. both implicitly encode lifecycle stage),
collapse them. It is better to propose 2 clean axes than 4 muddy ones.

Return JSON with this shape:
{
  "axes": [
    {"name": "...", "description": "...", "values": [...],
     "independence_justification": "...", "exhaustiveness_justification": "..."}
  ],
  "notes": "any caveats about borderline findings or axes you considered and rejected"
}

No prose before or after the JSON.

Findings:

