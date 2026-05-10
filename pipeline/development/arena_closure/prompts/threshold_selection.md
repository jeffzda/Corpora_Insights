# Threshold selection for parent-archetype taxonomy — clean assessment

## Context

We've run 50 independent replicates of a parent-archetype derivation prompt over a corpus of 1,141 mechanism-level failure clusters extracted from the ARENA Knowledge Bank (a corpus of ~1,440 government clean-energy project documents). Each replicate produced a parent set; across the 50 reps we obtained 4,150 raw parent labels. We then consolidated those 4,150 labels into 126 distinct canonical mechanism classes via a separate Opus pass.

Each canonical class carries an empirical frequency: the number of distinct reps (out of 50) in which a parent of that class was proposed. Frequencies range from 100% (proposed in every rep) down to 2% (proposed in one rep only). The distribution descends nearly linearly from 100% to ~22% over the first 115 classes, then drops to 0% over the final ~10. There is no sharp shoulder above the long-tail floor.

## The methodological question

We need to select a subset of these 126 canonical classes as a v2 parent-archetype taxonomy. The decision is governed by a frequency threshold: include all classes with frequency ≥ X%, exclude below.

X is the analyst lever. Higher X → fewer, more reproducible parents. Lower X → more parents, including some that only a minority of reps surfaced. The data does not auto-pick X; the choice has to be made on structural grounds.

## Purpose of the parent set

The parent-archetype taxonomy has a specific user and use case. The reader is an ARENA portfolio manager evaluating a current or prospective project. They use the parent set as a **navigable diagnostic vocabulary**: scanning the parent names and definitions to surface every important failure mechanism that could plausibly arise within their project, and grounding their assessment of forward-looking risk in the corpus evidence that sits beneath each mechanism. The taxonomy therefore needs to:

- **Cover the mechanism space comprehensively.** A PM scanning the list should not encounter a project risk that has no corresponding parent. Missing categories produce blind spots in risk assessment.
- **Remain navigable at a glance.** Too many parents and the PM can't scan them efficiently; too few and the taxonomy collapses genuinely-distinct mechanisms together. The set is a *working tool*, not a complete enumeration.
- **Support defensible claims about future project risk.** Each parent must name a mechanism the PM can cite as a structurally real failure pattern the corpus has shown recurring — i.e., the parent must be backed by enough cluster-level evidence to underwrite a claim that the mechanism could affect the PM's project.

Optimise your threshold (and any structural notes) for this user and this use case.

## Your task

Read all 126 canonical classes below. Recommend a threshold based on:

1. The structure and content of the canonical classes themselves.
2. Their frequency distribution.
3. The PM-facing purpose stated above — comprehensive mechanism coverage, navigable scale, defensible per-parent evidentiary basis.
4. Any concerns about including low-frequency classes that name plausibly real mechanisms but didn't reach majority retention across reps (do they fill genuine coverage gaps?).
5. Any concerns about excluding mid-frequency classes that have valuable structural distinctions even if half the reps missed them.

Approach this as a fresh judgement task. Do NOT reference any external taxonomy or prior parent layer. Evaluate the canonical set purely on its own merits.

If you find that no single threshold captures the right set — for example, because some low-frequency classes fill genuine coverage gaps a PM would need while some high-frequency ones overlap heavily and are duplicative — say so explicitly in `notes`. The threshold is a constraint we'd like to satisfy if defensible, but the constraint has limits.

## Output

Strict JSON, no preamble:

```json
{
  "recommended_threshold": 0.XX,
  "n_classes_included": N,
  "rationale": "<≤200 words explaining the threshold choice, grounded in observations about the canonical-class content and frequency distribution>",
  "borderline_classes": [
    {"class_id": "cNN", "frequency": 0.XX, "verdict": "include|exclude", "reason": "<one sentence>"}
  ],
  "notes": "<optional: any structural observations about the distribution, redundancy patterns within the canonical set, or limitations of a single-threshold approach>"
}
```

Constraints on output:

- `recommended_threshold` is a float between 0 and 1.
- `n_classes_included` should match the count of canonical classes with frequency ≥ recommended_threshold.
- `borderline_classes` should be 3–5 classes near the threshold (within ±0.05) with explicit include/exclude decisions and reasoning.
- `rationale` must be grounded in observations of the actual canonical classes, not abstract reasoning. Cite specific class_ids where relevant.

## Input — 126 canonical classes, sorted by frequency descending

Each entry: `[class_id] freq=X% — name :: definition :: mechanism_criterion`

{canonical_block}
