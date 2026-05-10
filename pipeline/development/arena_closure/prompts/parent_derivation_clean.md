# Parent-archetype derivation from 50-rep ensemble labels — PM-purpose, deliberation-rich

## Context

We've run 50 independent reps of a parent-archetype derivation task over a 1,141-cluster catalogue extracted from the ARENA Knowledge Bank corpus (~1,440 government clean-energy project documents). Each rep produced its own proposed parent set; together the 50 reps produced 4,150 raw parent labels, listed below.

Your task is to derive a **single canonical parent set** by working directly with these 4,150 labels. You'll see each label's **name** and **mechanism criterion** (one sentence: what must be true of a member cluster's mechanism for it to belong here). Repeated labels across reps signal mechanism families that recur reliably; one-off labels may be sampling noise OR genuinely-narrow-but-real mechanisms — you'll need to judge.

Conceptually, this collapses two pipeline steps (raw-label consolidation followed by parent-set selection) into a single deliberate derivation governed by the PM-purpose criteria below.

## Purpose of the parent set

The parent-archetype taxonomy has a specific user and use case. The reader is an ARENA portfolio manager evaluating a current or prospective project. They use the parent set as a **navigable diagnostic vocabulary**: scanning the parent names and definitions to surface every important failure mechanism that could plausibly arise within their project, and grounding their assessment of forward-looking risk in the corpus evidence that sits beneath each mechanism. The taxonomy therefore needs to:

- **Cover the mechanism space comprehensively.** A PM scanning the list should not encounter a project risk that has no corresponding parent. Missing categories produce blind spots in risk assessment.
- **Remain navigable at a glance.** Too many parents and the PM can't scan them efficiently; too few and the taxonomy collapses genuinely-distinct mechanisms together. The set is a *working tool*, not a complete enumeration.
- **Support defensible claims about future project risk.** Each parent must name a mechanism the PM can cite as a structurally real failure pattern the corpus has shown recurring — i.e., the parent must be backed by enough cluster-level evidence to underwrite a claim that the mechanism could affect the PM's project.

## Your task

Read all 4,150 raw labels listed below. **Synthesise a single canonical parent set** by recognising recurring mechanism families across reps, distinguishing genuinely-distinct mechanisms, and merging near-duplicates. Optimise the parent set for the PM-facing purpose stated above.

### Constraints on parent design

1. **Mechanism class, not topic.** Two raw labels about different technologies that name the same mechanism should map to the same canonical parent. Two labels about the same technology that name different mechanisms should map to different parents. Do not group by technology domain (solar / battery / hydrogen / etc.).

2. **Tightness over breadth.** Prefer narrower, well-defined parents that genuinely fit their constituent labels over broad parents that absorb anything loosely related. If a parent's description has to use "or" to span structurally different mechanisms, split it.

3. **Recurrence as signal, not constraint.** Labels that appear in many reps (high recurrence) are more likely to name structurally real mechanism families. Labels appearing in only one or two reps may be noise OR may name narrow-but-real mechanisms PMs would still need vocabulary for. Make per-parent judgements; do not auto-exclude low-recurrence content.

4. **Honest unfit reporting.** If some labels do not cleanly fit any proposed parent, list the most-frequent-but-unassigned label families with reasons; don't stretch parents to absorb them.

5. **Independence of axes.** Make parents distinguishable on mechanism class alone. If two parents differ only in which industry or life-cycle stage their members come from, they are likely the same mechanism class differently labelled.

6. **PM-purpose calibration.** Choose the parent count and granularity that best serves the PM as a diagnostic vocabulary. Cover the mechanism space, stay navigable, ensure each parent has enough recurrence + structural distinctness to underwrite forward-looking risk claims.

## Output

Strict JSON, no extra text:

```json
{
  "parents": [
    {
      "parent_id": "p01",
      "name": "<short noun phrase, 3-7 words>",
      "description": "<2-4 sentences naming the mechanism class and the criterion for membership>",
      "mechanism_criterion": "<one sentence: what must be true of a member's mechanism for it to belong here>",
      "exemplar_label_ids": ["<3-5 of the input label_ids (run_NN:pXX) that most cleanly instantiate this parent>"],
      "estimated_recurrence": "<rough fraction of the 50 reps in which this mechanism family was proposed, e.g. '~80%'>"
    }
  ],
  "deliberated_mechanisms": [
    {
      "candidate_name": "<the mechanism family or parent-boundary decision you considered>",
      "verdict": "include_as_parent | merge_into_<parent_id> | reject",
      "reason": "<one sentence on why this was a deliberation point and how it was resolved>"
    }
  ],
  "rationale": "<≤250 words explaining the parent set's overall structure, the principles used for boundary decisions, and how recurrence informed inclusion/exclusion. Cite specific label_ids where relevant>",
  "notes": "<optional: structural observations about the label set, recurrence patterns, redundancy clusters, or limitations of single-pass derivation>"
}
```

### Constraints on output

- `parents`: as many as the label set genuinely warrants given the PM-purpose. No preset count.
- `deliberated_mechanisms` is the **load-bearing output for methodological transparency**. Include **every mechanism family or parent-boundary decision that was a genuine close call** — i.e., where you considered creating a separate parent vs merging into an adjacent one, or where parent scope had to be drawn deliberately because adjacent mechanisms were structurally similar but distinguishable. Each entry needs a one-sentence reason. There is no upper or lower limit; produce as many as the label set genuinely warrants. Routine parent-creation decisions (where the mechanism is unambiguous and structurally distinct) do not need a deliberation entry.
- `rationale` must be grounded in observations of the actual labels, citing specific label_ids where relevant.

## Input — 4,150 raw parent labels from 50 reps

Each entry: `[run_NN:pXX] name | mechanism_criterion`

{labels_block}
