You are given a list of atomic findings extracted from {{corpus_plural_noun}}.
Each finding has a short mechanism-level gloss and a verbatim trigger
phrase.

Your task: propose a small set of orthogonal classification axes that
together span these findings.

## The structural rule for axes

Every classification axis is one of two kinds:

**Substantive axes** classify *what the finding is about* — the subject
matter. Their values name domains, system parts, kinds of object,
categories of actor, or topical areas. Two findings that share a
substantive-axis value are about the same kind of thing.

**Framing axes** classify *how the finding stands* — its stance, status,
or character independent of what it is about. Their values name
properties of the finding itself: its epistemic status (e.g. confirmed
vs. hypothesised vs. unknown), its kind of deficiency (e.g. absence vs.
mis-execution vs. wrong-design vs. mis-timing), its resolution maturity
(e.g. open vs. mitigated vs. accepted), its valence, its severity, its
actionability, its scope. Two findings that share a framing-axis value
have the same *shape* of finding regardless of subject matter.

The structural rule for proposing axes:

> **At most ONE substantive axis. At least one framing axis. Optionally,
> per-finding flags (binary or small-enum attributes that don't deserve
> their own axis).**

### Why

A finding has only one piece of subject-matter content. Two substantive
axes attempting to classify that single content will inevitably end up
slicing the same cake from slightly different angles — they will
covary, because what the finding is about determines its position on
both axes. Empirically this manifests as high mutual information
between the axes: knowing the value on one tells you the value on the
other.

Framing axes do not have this problem. The kind of deficiency a finding
describes (e.g. an absence vs. a mis-execution) is independent of the
subject matter (e.g. procurement vs. workforce). Findings about the
same subject can have different framings; findings with the same
framing can be about different subjects. So you can have multiple
framing axes without collapse, as long as each framing axis captures
a genuinely independent facet of the finding's stance.

### Per-finding flags

Properties with only 2–3 values, or properties that apply only to a
subset of findings, are better expressed as flags than axes. A flag
attaches to a finding without participating in the cross-tabulated
matrix. Common flag candidates: valence (negative/positive/mixed),
shared-vs-internal locus, presence-of-recommendation. Use a flag when
either (a) the value distribution is heavily skewed (>80% one value),
or (b) the property is meaningful only for some findings.

## What to return

For each axis (substantive or framing):

  - `name`: short snake_case identifier
  - `kind`: `"substantive"` or `"framing"` — explicit declaration
  - `description`: one sentence explaining what the axis classifies
  - `values`: 5–10 values, each with `name` (snake_case),
    `definition` (one sentence), and 2 example gloss strings drawn
    verbatim from the findings list

For each per-finding flag:

  - `name`: short snake_case
  - `description`: one sentence
  - `values`: 2–4 enum values with definitions
  - `rationale`: why this is a flag rather than an axis

For the proposal as a whole:

  - `independence_justification`: explain how the framing axes are
    independent of one another and of the substantive axis. For each
    framing axis, name a verbatim finding pair that share that axis
    value but differ on the substantive axis, and another verbatim
    pair that share the substantive value but differ on the framing
    axis.
  - `notes`: any axes you considered and rejected and why

Return JSON with this shape:

```
{
  "axes": [
    {"name": "...", "kind": "substantive" | "framing",
     "description": "...", "values": [...]}
  ],
  "flags": [
    {"name": "...", "description": "...", "values": [...],
     "rationale": "..."}
  ],
  "independence_justification": "...",
  "notes": "..."
}
```

No prose before or after the JSON.

Findings:

