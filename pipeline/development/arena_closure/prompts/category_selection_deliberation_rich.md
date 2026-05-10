# Category selection for parent-archetype taxonomy — direct PM-purpose assessment, deliberation-rich

## Context

We've run 50 independent replicates of a parent-archetype derivation prompt over a corpus of 1,141 mechanism-level failure clusters extracted from the ARENA Knowledge Bank (a corpus of ~1,440 government clean-energy project documents). Each replicate produced a parent set; across the 50 reps we obtained 4,150 raw parent labels. We then consolidated those 4,150 labels into 126 distinct canonical mechanism classes via a separate Opus pass.

Each canonical class carries an empirical frequency: the number of distinct reps (out of 50) in which a parent of that class was proposed. Frequencies range from 100% (proposed in every rep) down to 2% (proposed in one rep only). The frequency is provided as contextual information about how often the canonical class surfaced in independent reps; it is not a constraint on your selection.

## Purpose of the parent set

The parent-archetype taxonomy has a specific user and use case. The reader is an ARENA portfolio manager evaluating a current or prospective project. They use the parent set as a **navigable diagnostic vocabulary**: scanning the parent names and definitions to surface every important failure mechanism that could plausibly arise within their project, and grounding their assessment of forward-looking risk in the corpus evidence that sits beneath each mechanism. The taxonomy therefore needs to:

- **Cover the mechanism space comprehensively.** A PM scanning the list should not encounter a project risk that has no corresponding parent. Missing categories produce blind spots in risk assessment.
- **Remain navigable at a glance.** Too many parents and the PM can't scan them efficiently; too few and the taxonomy collapses genuinely-distinct mechanisms together. The set is a *working tool*, not a complete enumeration.
- **Support defensible claims about future project risk.** Each parent must name a mechanism the PM can cite as a structurally real failure pattern the corpus has shown recurring — i.e., the parent must be backed by enough cluster-level evidence to underwrite a claim that the mechanism could affect the PM's project.

## Your task

Read all 126 canonical classes below. **Select the subset that best serves the PM-facing purpose described above.** Make per-class judgements based on:

1. The structure and content of each canonical class (its name, definition, mechanism criterion).
2. The relationship between classes — whether one is a near-duplicate of another, or carves a structurally distinct mechanism worth keeping.
3. Whether the class names a failure mechanism a PM would plausibly need to assess on a real project.
4. Whether the class is backed by enough recurrence and structural distinctness to underwrite forward-looking risk claims.

The frequency of each class is provided as contextual information — you may use it to inform your judgement (e.g. a class proposed in only 1 rep may indicate noise or a genuinely-rare-but-real mechanism), but you are not constrained to pick by frequency cutoff. Make per-class decisions on the merits.

Approach this as a fresh judgement task. Do NOT reference any external taxonomy or prior parent layer. Evaluate the canonical set purely on its own merits.

## Output

Strict JSON, no preamble:

```json
{
  "selected_class_ids": ["c01", "c02", ...],
  "n_selected": N,
  "rationale": "<≤200 words explaining the selection principle and the structure of the chosen set, grounded in observations about the canonical-class content. Cite specific class_ids where relevant>",
  "deliberated_classes": [
    {"class_id": "cNN", "frequency": 0.XX, "verdict": "include|exclude", "reason": "<one sentence on why this class was a deliberation point and how it was resolved>"}
  ],
  "notes": "<optional: structural observations about the canonical set — redundancy patterns, coverage gaps, multi-class clusters worth flagging — and any limitations of single-pass selection>"
}
```

Constraints on output:

- `selected_class_ids` should list the canonical class_ids you choose to include. No specific count is required; pick what you judge serves the PM-purpose.
- `n_selected` should match the length of `selected_class_ids`.
- `deliberated_classes` is the **load-bearing output** of this task. Include **every canonical class that you considered a genuine close call** — i.e., a class where the include/exclude decision was non-trivial because of redundancy, marginal mechanism distinctness, low frequency despite content relevance, high frequency despite content redundancy, or PM-utility ambiguity. There is **no upper or lower limit** on the number of deliberated entries; produce as many as the canonical set genuinely warrants. A clear-cut routine include or routine exclude does not need a deliberation entry. Each entry needs a one-sentence reason. Aim for full coverage of the borderline zone — if you find yourself thinking through a class for more than a moment before committing, that class belongs in `deliberated_classes`.
- `rationale` must be grounded in observations of the actual canonical classes, not abstract reasoning. Cite specific class_ids where relevant.

## Input — 126 canonical classes, sorted by frequency descending

Each entry: `[class_id] freq=X% — name :: definition :: mechanism_criterion`

{canonical_block}
