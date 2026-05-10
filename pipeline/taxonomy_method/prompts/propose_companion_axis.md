You are given a list of atomic findings extracted from {{corpus_plural_noun}}.
Each finding has a short mechanism-level gloss and a verbatim trigger phrase.

A primary classification axis has already been fixed. It is non-negotiable
and you must not propose anything that overlaps with it:

## Pinned axis: {{pinned_axis_name}}
{{pinned_axis_block}}

Your task: propose ONE additional axis that is genuinely orthogonal to
the pinned axis above. Orthogonal means: knowing a finding's value on
the pinned axis tells you essentially nothing about its value on your
proposed axis.

Anti-patterns to avoid (these failed in a prior iteration):

  - Lifecycle / project-stage axes. They proxy for the layer being worked
    on (a market-and-policy stage finding is almost always at the
    market-and-policy layer). Reject any axis where the values look like
    "research → planning → construction → operations".
  - Barrier-kind axes whose values restate the pinned-axis values from
    a different angle (e.g. a "regulatory_barrier" value when the pinned
    axis already has a "policy" layer). Test: if any value of your
    proposed axis is >2× more likely to co-occur with one specific value
    of the pinned axis, the axes are not orthogonal.
  - Identity axes (technology family, proponent type) — these belong in
    the catalogue, not the taxonomy.

What to look for instead: an axis that cuts ACROSS layers — something
that varies within every layer of the pinned axis. Examples of the
shape (not the substance) we want:

  - failure mode: capability gap vs. unknown unknown vs. mis-coordination
    vs. cost-benefit shortfall
  - epistemic status: confirmed mechanism vs. hypothesis vs. negative
    result vs. open question
  - actionability: lesson vs. recommendation vs. observation vs. metric

Pick whatever shape the corpus actually supports — these are
illustrative only.

For your proposed axis, return:
  - name: short snake_case
  - description: one sentence
  - values: 5–10 values, each with name (snake_case), definition (one
    sentence), and 2 example gloss strings drawn verbatim from the
    findings list
  - independence_justification: name a pair of findings that share your
    axis value but sit at DIFFERENT pinned-axis values. Then name a pair
    that share a pinned-axis value but sit at different values of your
    axis. Both pairs must be cited verbatim.
  - exhaustiveness_justification: why the value set covers the corpus
    range, and what (if anything) is left over

Return JSON with this shape:
{
  "pinned_axis": "{{pinned_axis_name}}",
  "axes": [
    {"name": "...", "description": "...", "values": [...],
     "independence_justification": "...", "exhaustiveness_justification": "..."}
  ],
  "notes": "axes you considered and rejected, and why"
}

No prose before or after the JSON.

Findings:

