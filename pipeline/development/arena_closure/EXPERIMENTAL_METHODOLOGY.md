# Parent-archetype experimental methodology
## v2 closure phase — 2026-05-04 / 06

This document covers the experimental work that produced the v2 extended parent set (86 parents, 16 themes). The companion document at `output/parent_derivation_clean_ensemble/SESSION_WRITEUP.md` summarises the build outcome; this one documents the methodology that informed the build.

## TL;DR

The v1 single-pass parent set (71 parents) was a single arbitrary draw from the model's distribution. Building v2 required deciding: how do we know which parents belong in the canonical set rather than which the model happened to produce on one occasion? The answer was a **deliberation-rich ensemble** with explicit threshold-defensibility analysis.

The campaign produced four substantive findings beyond the parent set itself:
1. **Naming examples in taxonomy prompts is a 50pp priming hazard.** Candidate categories named in the prompt are retained at materially different rates than equivalent categories not named.
2. **Single-rep arbitrariness is high (sd 13.6 in original 50-rep ensemble).** Variance halves (sd 7.24) when the prompt is deliberation-rich and tuned for the load-bearing decision points.
3. **Layer-cost asymmetry favours ensembles at affordable layers.** Parent / glossary / threshold ensembles cost ~$25 each; cluster-layer ensembles cost $1,500–5,000. The parent layer is where ensembles are economically defensible.
4. **Threshold defensibility requires clean LLM judgement on the canonical set, not analysis grounded in the v1 set.** Otherwise the threshold decision depends on an artefact of single-pass arbitrariness.

Everything below is the working out of these findings.

---

## Phase 1 — single-pass v1 (script 12)

The v1 derivation was a single Opus call that ingested the 1,141-cluster v2 catalogue and emitted a 71-parent set. This produced canonical artefacts (`parents_v1.json`, `cluster_to_parent_assignments.jsonl`, `themes_and_parent_audit_v1.json`) and was used to build the worked-example outputs (cluster reports, project reports, glossary).

But the question that emerged: how would we know if those 71 parents were the right 71? A second draw would produce a different set. Without variance evidence, "v1 has 71 parents" is a single observation — not a defensible claim about what the corpus contains.

This question is the load-bearing one for the methodology paper. The rest of the campaign is its answer.

---

## Phase 2 — original 50-rep ensemble (scripts 19-20)

Script 19 ran 50 independent Opus reps of the parent-derivation prompt over the 1,141-cluster catalogue. Each rep proposed its own parent set; the 50 reps collectively produced 4,150 raw parent labels. Script 20 consolidated these by Jaccard ≥0.30 name-token clustering into **126 canonical mechanism classes** with rep-count tiering.

Variance was high: parent counts per rep ranged 60–110, sd 13.6. Some categories appeared in nearly every rep (the dominant mechanism families); others appeared in only one (idiosyncratic naming). No per-rep parent set looked like any other per-rep parent set in detail.

The 126 canonical classes were the input to all subsequent campaign work.

### Tier breakdown (50-rep)
| tier | rep agreement | n classes |
|---|---|---|
| core | ≥90% | small (~30) |
| high | 70–89% | medium |
| boundary | 40–69% | medium |
| rare | 20–39% | small |
| singleton | <20% | large tail |

### What 50 reps showed but didn't resolve
- The variance is real
- The dominant categories are stable
- The boundary tier is contested
- The rarer classes are noise OR genuinely-narrow-but-real mechanisms
- Threshold for inclusion is undefined

The original consolidation step (script 20) used a Sonnet pass to collapse the 4,150 labels into the 126 classes. This was the first inflection: should the canonical layer be derived from the consolidated classes, or directly from the 4,150 raw labels with the load-bearing decisions made in the same pass? See script 36 below.

---

## Phase 3 — diagnostic experiments (scripts 21-30)

Several analytical passes were run on the v1 parent set + 50-rep ensemble before the v2 redesign. The relevant findings for parent design:

**Script 23 (abstraction_rating).** Each v1 parent rated for abstraction level (1–5) by Opus. Distribution skewed toward parent-grain (3) but with notable mass at theme-grain (4-5) and cluster-grain (2). Implication: v1 was internally inconsistent in granularity — some parents were closer to themes, some closer to clusters. v2 needed explicit granularity discipline.

**Script 25-26 (causal_chain).** 88% of v2 mechanism clusters formed valid causal chains (X→Y→Z structure rather than mere co-occurrence). This is the corpus-level evidence that the cluster layer captures genuine mechanism structure, not just text neighbourhood. It informed the parent-derivation prompt's emphasis on "mechanism class, not topic."

**Script 27 (event_coherence_audit).** 98% event-coherence on multi-parent stratum: when a cluster's records spanned multiple v1 parents, the parents really did describe distinct mechanisms. The few violations were ambiguous events. This validated that v1 was not over-fitting parents to artificially separate truly-related content.

**Script 28 (grouping_rep_stability).** Stage-internal stability of the parent ensemble was high (rep-pair agreement ~95% on naming overlap). But high stability doesn't equal high accuracy — model can confidently miscalibrate on loose-boundary axes. This finding became the "stability ≠ accuracy" memory note: ensemble agreement is necessary but not sufficient for taxonomy correctness.

---

## Phase 4 — soft-balance constraint experiments (scripts 29-30)

A specific concern: did the original prompt produce balanced coverage across mechanism families, or did it over-cluster on dominant areas (regulatory, capital) and under-cluster on others (equity, behavioural)?

**Script 29 (parent_ensemble_softbalance).** The original prompt was modified with a soft-balance instruction: "ensure equity, behavioural, and similar under-represented mechanisms are at least sampled in your parent set." The soft-balance prompt produced equity-related parents in 75% of reps vs 24% in the unmodified prompt — a 51pp shift.

**Initial interpretation:** the soft-balance constraint was working as intended.

**Then script 30 (parent_ensemble_softbalance_clean).** The same soft-balance constraint with the *example phrasings removed*. Equity dropped back to 25%. The 51pp shift wasn't from the constraint — it was from the prompt naming "equity" as an example of what to look for.

### The priming-hazard finding

Naming a candidate category in the prompt — even as an illustrative example — produces a strong retention bias for that exact category. The mechanism is straightforward: the model is more likely to surface a category when its name is provided as a primer than to derive it from corpus structure alone.

This finding generalises beyond the soft-balance experiment. The original parent_derivation prompt (script 12) named four illustrative mechanism types (informational / physical-technical / control-technical / economic) as examples. Reps including those types had elevated retention; reps for unnamed-but-equivalent types (e.g. governance, behavioural) had lower retention. The structure of the prompt was shaping the structure of the output.

**Methodology consequence:** the production parent-derivation prompt for v2 (`parent_derivation_clean.md`) removes all named example categories. Mechanism families must emerge from the corpus, not from prompt priming. This is the practical generalisation worth carrying into future taxonomy work.

Memory note: `feedback_no_named_examples_in_taxonomy_prompts.md`.

---

## Phase 5 — parent gap audit (script 31)

With the priming concern raised, we asked the inverse question: was v1 *missing* any parents the 4,150 raw labels supported? Script 31 ran an LLM gap audit comparing v1's 71 parents against the full 4,150-label corpus.

Result: 8 mechanism families with ≥40 raw-label support that v1 either subsumed under broader parents or omitted. Six were defensibly subsumed; two (governance scope/ambit failures, observability/visibility gaps) were genuinely under-represented.

The gap audit informed the boundary-tier extension later in the campaign — it was the first evidence that v1's threshold for inclusion had cut off real signal.

---

## Phase 6 — threshold defensibility (scripts 32-35)

**The setup.** The 126 canonical classes from the 50-rep ensemble were tiered by rep agreement. Where to draw the line for canonical inclusion? 90%? 70%? 40%? The choice has direct consequences: a higher threshold gives a tighter, more-defensible parent set; a lower threshold catches more mechanism diversity at the cost of including some rep-noise.

**Initial approach (rejected).** Compare the 126-class output against v1's 71 parents — see which threshold reproduces v1 most closely. *Problem:* the v1 set is itself a single arbitrary draw. Defending a threshold via comparison to v1 would propagate v1's idiosyncrasy into the threshold decision.

**Replacement (script 32 threshold_defensibility).** Clean LLM judgement on the 126 canonical set alone. Opus rated each class for inclusion under PM-purpose framing without any reference to v1. Result: ~70% rep agreement was the boundary the model judged as the natural cut between "this names a real mechanism family" and "this is a single-rep idiosyncrasy."

**Validation (scripts 33-35).** Two independent ensemble passes:
- **Threshold judgement ensemble (script 34):** 10 reps of Opus rating each canonical class for inclusion under the same prompt. Agreement on which classes belong was high (sd ≪ original 13.6).
- **Category selection ensemble (script 35):** 10 reps of Opus selecting which canonical classes to include in a final v2 set, without explicit threshold framing. Agreement again high. Both modes converged on the ≥70% rep-agreement threshold as the natural cut.

These three passes (single-shot judgement + threshold-judgement ensemble + category-selection ensemble) gave threshold-defensibility evidence that doesn't depend on the v1 artefact.

Memory notes: `feedback_two_validation_routes.md` (stage-internal vs use-case demos), `feedback_data_driven_reference_class.md` (filter, don't hand-pick).

---

## Phase 7 — deliberation-rich ensemble (scripts 36-38)

The original 50-rep ensemble used a relatively terse prompt; the consolidation step (script 20) collapsed 4,150 labels via Jaccard token overlap. This left two distinct concerns:

1. **Token-overlap consolidation is a heuristic.** Two labels with the same mechanism but different vocabulary stay separate; two labels with shared vocabulary but different mechanisms collapse together. The 126 canonical classes carried this heuristic-induced noise into all downstream decisions.

2. **The original prompt didn't deliberate.** It produced parent sets without showing reasoning on borderline boundary decisions. Whether to split or merge a near-pair was an internal model decision; the prompt didn't surface those decision points.

**The deliberation-rich prompt (`parent_derivation_clean.md`).** Script 36 introduced a redesigned prompt with three changes:
- **PM-purpose framing.** The prompt explicitly names the audience (an ARENA portfolio manager scanning failure-mode space) and the use case (navigable diagnostic vocabulary). Parent-design decisions are anchored in user need, not abstract elegance.
- **No named example categories.** Per the priming-hazard finding.
- **Deliberation as a load-bearing output field.** The model must surface every borderline split/merge decision as an explicit `deliberated_mechanisms` entry with verdict and reason. This makes the model's reasoning legible and auditable.

**Direct synthesis from raw labels.** The new pipeline skipped the token-overlap consolidation step entirely. Each rep ingests all 4,150 raw labels directly and synthesises a parent set, with the deliberation field surfacing the load-bearing boundary decisions.

### Ensemble execution

| script | reps | model | mode | cost |
|---|---|---|---|---|
| 36 (rep_01) | 1 | Opus 4.7 | single-shot | $2.15 |
| 37 (reps 02-10) | 9 | Opus 4.7 | Batches API | $5.30 |
| 38 (reps 11-59) | 49 | Opus 4.7 | Batches API | $30.00 |
| **Total ensemble** | **59 reps** | | | **~$37** |

### Variance reduction

The deliberation-rich 59-rep ensemble produced parent counts in a tighter band than the original 50-rep:

| ensemble | parent count range | sd |
|---|---|---|
| Original 50-rep (terse) | 60–110 | 13.6 |
| **Deliberation-rich 59-rep** | **89–105** | **7.24** |

Variance halved. The deliberation-rich prompt anchors the model on the load-bearing decisions, reducing per-rep idiosyncrasy without sacrificing legitimate mechanism coverage.

### Tier breakdown (59-rep, deliberation-rich)
| tier | rep agreement | n classes |
|---|---|---|
| core | ≥90% (≥53 reps) | 43 |
| high | 70–89% (41–52 reps) | 28 |
| boundary | 40–69% (24–40 reps) | 26 |
| rare | 20–39% (12–23 reps) | 25 |
| singleton | <20% (<12 reps) | 176 |

The 43 core classes are the universally-surfaced mechanism families. The 28 high-tier classes are well-supported but didn't reach core consensus. Together (71 classes) they sit at the threshold the validation passes (Phase 6) judged defensible.

---

## Phase 8 — consolidation and extension (scripts 39, 41, 42)

**Script 39 (v2 consolidation).** Single Opus 4.7 call covering two tasks:
1. Consolidate the 43 core classes into final v2 parent definitions (canonical name + 2-4 sentence description + one-sentence mechanism criterion + 3-5 exemplar cluster IDs).
2. Judge the 28 high-tier classes for promote/hold/merge verdicts.

Result: 43 core + 27 promoted high-tier = **70 v2 parents**. 1 high-tier merged (high_24 unintended-consequences into p19 coupled-trade-offs). $0.39, 152s.

**Phase-7 question that script 39 leaves open:** what about the 26 boundary-tier classes (40–69% rep agreement)? They weren't shown to the model — excluded by the consolidation script's input filter. The model didn't reject them; they were never seen.

**Script 40 (v1↔v2 coverage audit).** Single Opus call comparing v1's 71 parents against v2's 70 parents. Identified 8 v1 parents flagged "missing" from v2 by audit. Local cross-check against the 59-rep ensemble: 5 of 8 missing-from-v2 were boundary-tier; 1 was rare; 2 were singleton. So most of the v1 "missing" parents corresponded to boundary-tier signal that v2's threshold cut off.

**Script 41 (boundary-tier extension).** Single Opus call presenting the 26 boundary-tier classes alongside the existing 70-parent v2 set, asking for promote/merge/reject verdicts on each. Result: 16 promoted (13 unique after de-duplication), 9 merged, 1 rejected. $0.17, 67s.

This filled the methodological hole. Every mechanism family with ≥40% ensemble support is now explicitly included or explicitly rejected with reasoning. Below 40% (rare + singleton) is excluded by threshold, defended on the rep-frequency curve.

**Script 42 (extended consolidation).** Single Opus 4.7 call producing unified canonical definitions for all 86 promoted classes (43 core + 27 high-promoted + 16 boundary-promoted). Output: thematic ordering, source-tier provenance per parent, n_reps_min. $0.63, 226s.

---

## Phase 9 — Pass 2 and Pass 3 (scripts 43-44)

**Script 43 (Pass 2 cluster-to-parent assignment).** Single one-shot Opus call assigning every one of the 1,141 v2 mechanism clusters to one of the 86 parents. 1,141/1,141 placed; 502 high-confidence / 632 medium / 7 low; 0 'none' assignments. $2.29, 809s.

Distribution checks: every parent absorbs ≥3 clusters; max 50 clusters/parent (p07 model/forecast representational error); median 11. No parent absorbed more than 5% of clusters — the mechanism-class differentiation paid off.

**Script 44 (Pass 3 theme audit + grouping).** Single Opus call auditing each parent and grouping parents into themes. Result: 86/86 keep verdict; 85/86 tight mechanism coherence; 16 themes; 0 unthemed parents. $0.95, 114s.

The 16 themes form 14 mechanism-family groupings: information & evaluation, physical & resource limits, asset & process engineering, spatial & temporal mismatch, power-system & grid, control/IT/interfaces, systemic fragility, capital & economics, market design, supply chain & lifecycle, regulation & policy, commercial instruments, coordination & social, workforce & execution.

---

## Total cost and time

| campaign | $ | wall |
|---|---|---|
| Original 50-rep ensemble (scripts 19-20) | ~$25 | ~12h batches |
| Diagnostic experiments (21-28) | ~$15 | spread |
| Soft-balance experiments (29-30) | ~$12 | ~3h |
| Parent gap audit (31) | ~$2 | minutes |
| Threshold defensibility (32-35) | ~$10 | ~6h batches |
| Deliberation-rich ensemble (36-38) | ~$37 | ~24h batches |
| v2 build passes (39-44) | $4.84 | ~30 min |
| **Campaign total** | **~$106** | spread over 2 days |

The build phase (39-44) is the cheapest part by a large margin. The expensive parts are the experimental work that established what parent-derivation should look like — the priming-hazard discovery, the threshold-defensibility validation, the variance-reduction comparison, the deliberation-rich prompt design.

---

## What this gives the methodology paper

Four publishable claims emerge from the campaign:

**1. Single-pass taxonomy derivations are arbitrary.** sd 13.6 across 50 reps with the same prompt and same input. The "the model produced N parents" framing is misleading; any one rep is one draw from a wide distribution. Methodology rigour requires ensemble methods or equivalent variance evidence.

**2. Naming examples in taxonomy prompts is a 50pp priming hazard.** The soft-balance A/B/clean experiment isolates the effect to the example phrasings, not to the constraint itself. Implication: production taxonomy-derivation prompts should not name candidate categories. If the constraint matters, frame it abstractly ("ensure under-represented dimensions are surfaced") without specifying which dimensions.

**3. Deliberation-rich prompts halve variance.** The redesign at scripts 36-38 reduced sd from 13.6 to 7.24 without sacrificing legitimate mechanism coverage. The mechanism is straightforward: making the model surface its load-bearing decisions in a structured output field anchors it to the decisions that matter, reducing per-rep idiosyncrasy on borderline cases.

**4. Threshold defensibility requires reasoning grounded in the canonical set, not the prior.** Defending a threshold by comparing to v1 propagates v1's arbitrariness into the threshold decision. The clean approach is independent LLM judgement on the canonical set with explicit purpose framing — and validating via two independent ensemble passes that converge on the same threshold.

These four claims, plus the worked example artefacts (the 86-parent v2 set and 16 themes built from them), constitute the methodology paper's parent-derivation section. The paper claim isn't "we built a parent set"; it's "this is what rigorous parent-set derivation looks like, and here's the variance, priming, and threshold evidence that supports it."

---

## Standing-instruction lessons (for future Claude sessions on this corpus)

1. **Never use single-pass derivation as canonical.** The variance evidence (sd 13.6) is decisive. Any parent set with methodological weight needs an ensemble or equivalent.
2. **Never name candidate categories as examples in taxonomy prompts.** Priming hazard is 50pp.
3. **Threshold decisions require reasoning grounded in the canonical set, not the prior.** Comparing v1 to v2 was rejected as a defence vehicle; clean LLM judgement on the canonical 126 was the replacement.
4. **Layer cost asymmetry matters for ensemble design.** Parent / glossary / threshold ensembles are ~$25 each — affordable; cluster-layer ensembles are $1500–5000 — only affordable on toy datasets. Choose ensemble layers accordingly.
5. **Each parent in the canonical set must carry provenance.** Source tier (core / high / boundary), n_reps_min, source class IDs. Without this, defending an inclusion against a "but this is just one model's choice" challenge is impossible.

---

## Files produced by the campaign

### Code (`code/`)
| range | scripts | role |
|---|---|---|
| 19-20 | parent_ensemble_batch, consolidate_ensemble | original 50-rep + 126-class consolidation |
| 21-28 | misc diagnostic | abstraction, coherence, causal-chain, stability |
| 29-30 | parent_ensemble_softbalance{,_clean} | priming-hazard A/B |
| 31 | parent_gap_audit | v1 vs 4,150-label gap |
| 32-35 | threshold_defensibility, threshold_selection_judgement, threshold_judgement_ensemble, category_selection_ensemble | threshold defensibility |
| 36-38 | parent_derivation_clean{,_ensemble,_extension} | deliberation-rich 59-rep ensemble |
| 39-42 | v2_consolidation, v1_v2_coverage_audit, v2_boundary_extension, v2_extended_consolidation | build phase |
| 43-44 | assign_clusters_v2_extended, themes_audit_v2_extended | Pass 2 + Pass 3 |

### Prompts (`prompts/`)
- `12_derive_parents.md` — original derivation prompt (named examples, single-pass)
- `12_derive_parents_softbalance{,_clean}.md` — soft-balance A/B
- `parent_derivation_clean.md` — production deliberation-rich prompt (no named examples, PM-purpose, deliberation field)
- `threshold_selection.md` — threshold-defensibility judgement prompt
- `category_selection{,_deliberation_rich}.md` — category-selection mode for ensemble validation
- `13_assign_clusters.md` — Pass 2 prompt
- `14_themes_audit.md` — Pass 3 prompt
- `15_parent_report.md` — parent-level analytical report prompt

### Outputs (`output/parent_derivation_clean_ensemble/` and adjacent)
- 59-rep raw responses, parsed runs, ensemble aggregate
- v2_parents.json (70-parent), v2_parents_extended.json (86-parent canonical)
- v2_boundary_extension.json (boundary judgement)
- v1_v2_coverage_audit.json
- cluster_to_parent_assignments_v2_extended.jsonl (Pass 2)
- themes_and_parent_audit_v2_extended.json (Pass 3)
- `blinded_validation/` — independent same-rubric review of Pass 2 (2026-05-08).
  Three layers:
  - v1/v2 fixed-parent confidence-rating tests ($0.40): 68/91 assignments
    confirmed clean fits; 0 two-step disagreements; medium-confidence shown
    to track selection ambiguity rather than fit-criterion uncertainty.
  - v3 selection-task with primary+optional-secondary, single pilot + 9-rep
    batched ensemble ($3.60): 73.6% of assignments in top-2 across ALL
    10 reps; 5 strong reassignment candidates identified; p25↔p18
    single-boundary signal confirmed at ensemble scale.
  - v3 full-corpus ensemble: 10 reps × 1,141 clusters × 86 parents (~$22
    batched). Headline: 73.5% always-in-top-2, 64.8% unanimous primary, 80
    strong reassignment candidates, 94 unanimous disagreements. 86×86
    adjacency heatmap + network diagram; cross-theme bridges identified
    (p18↔t06 hub, t11↔t12 economic-policy interface, t09↔t13 technical-
    coordination cascade).
  - **Documented gap** — `CLUSTER_SIGNATURE_DRIFT.md`: cluster signatures
    derived at minting time, not re-synthesised after membership
    stabilisation. Long-tail boundary adjacencies may include drift
    artefacts. Fix costed at ~$170 batched + ~$25 re-ensemble; not committed.
  See `blinded_validation/README.md`, `PILOT_ENSEMBLE_2026-05-08.md`, and
  `full_corpus_ensemble_v3/full_summary.md`.
- ../parent_gap_audit.{json,md} — v1 gap audit
- ../parent_ensemble_softbalance/ and softbalance_clean/ — A/B outputs
