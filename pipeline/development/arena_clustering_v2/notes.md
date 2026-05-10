# v2 Failure-Mode Clustering — Methodology and Findings

This document captures the v2 clustering architecture, the iterative-sweep results,
the controlled experiments that revealed prompt-by-method interactions, and the
implications for the methodology paper. Written 2026-05-03 covering work that ran
day 1 (corpus tagging + dedup, ~$262 spend) and day 2 (clustering rebuild).

---

## 1. Why v2

The v1 pipeline used embedding-based agglomerative clustering of record narratives,
followed by an LLM naming pass on the resulting neighbourhoods. After ~660 leaf-level
clusters were produced, a project-vocabulary diagnostic showed **~36% of clusters
were single-project-bound** — the embedding similarity was capturing project /
equipment / technology vocabulary, not causal mechanism.

The v2 architecture rebuilds with mechanism as the clustering primitive, by
delegating both *cluster formation* and *record classification* to an LLM with
explicit mechanism-form instructions. The defensibility argument: a methodology
paper wanting to claim cross-project pattern matrices needs the clustering primitive
to be the causal pathway, not lexical neighbourhood.

---

## 2. Architecture

### 2.1 Pipeline phases

| Phase | Script | Purpose |
|---|---|---|
| Phase 1 — Filter | 01 | Build `filter_input.jsonl` from corpus-wide tags + dedup events. Loose filter: `valence='negative' AND (is_occurrence OR is_mechanism)`. **No specification gate** — kept for richer evidence. 25,479 records survive. |
| Phase 2 — Embed | 02 | Qwen3-Embedding-4B in bf16 of `narrative + evidence`. (Used for the early embedding-clustering experiment that informed the v2 redesign; not used in production v2.) |
| Phase 3 — Cluster (legacy) | 03 | GPU pairwise cosine + scipy linkage, multi-threshold. Retained for diagnostic comparison only. |
| Phase 4a — Seed | 05 | Stratified sample of 360 records (8 categories × 3 axis-combos × 15 records). Single Sonnet call: produce mechanism-form clusters with ≥3 supporting records. Output: 45 seed clusters. |
| Phase 4b — Sweep | 07 | Iterate over remaining records in 200-record batches. Pass 1: classify each record against running catalogue. Pass 2: cluster *this-batch's* orphans into new ≥3-member clusters. Catalogue grows. |
| Phase 4c — Closure | 08+ | Per-record final pass on pending singletons; merge/split/late-bind descriptions. |

### 2.2 Core design choices

**Two-pass per batch.** Classification (cheap, batched) is separated from orphan-clustering (expensive, combinatorial). The two operations have different attention demands and different scaling properties; bundling them would dilute both.

**≥3-record threshold for cluster definition.** Refusing to canonise singletons. A cluster proposed by 1-2 records on this batch's evidence stays as singletons in the pending pile; if more matching records arrive in later batches, the cluster forms then.

**Late-binding descriptions.** Cluster definitions during the sweep are just `canonical_name + mechanism_signature`. Rich descriptions are deferred to closure, so they don't bias future classifications by anchoring on early-member vocabulary.

**"Do not force-fit" instruction in batched calls.** Records that don't match any cluster's mechanism are flagged orphan; the model is not asked to pick the closest. Orphans become Pass 2 candidates. (See §6 for the discovered limitation of this instruction in per-record contexts.)

**Procurement-probity invariant.** Once a cluster's `canonical_name + mechanism_signature` is published, it is immutable. Records joined the cluster under that signature; changing it would retroactively alter the matching rule. Allowed scope-preserving variations are merge, split, late-bind description, and demote — none of which alter the rule under which existing members were admitted. This invariant has a second-order benefit: any past iteration's catalogue state is exactly reconstructible from the current catalogue minus late-arriving entries, because no entry's text changed.

**Set-aside pending pile, not periodic re-injection.** Orphans from earlier iterations don't get re-passed in later iterations; they accumulate into a pending pile. Procedural-fairness defence: every record was given the catalogue available *at exit*, plus a final-sweep pass against the matured catalogue. No record's *final* placement depends on the iteration in which it was processed — only on the catalogue available when it last classified successfully.

---

## 3. Sweep trajectory

The corpus sweep ran 128 iterations over 25,479 records.

### Phase progression

| Phase | Iters | Catalogue | Post-P1 orphan | Post-P2 unplaced |
|---|---|---|---|---|
| Bootstrap | 1-2 | 45→75 | ~78% | ~54% |
| Mainstream capture | 3-12 | 75→200 | 78→43% | 33-44% |
| Apparent plateau | 13-22 | 200→292 | 43-49% | 22-40% |
| Decline resumed | 23-90 | 292→650 | 35-40% | 19-29% |
| Long-tail equilibrium | 91-128 | 650→797 | 22-30% | 15-22% |

### Final state

- **797 clusters** in catalogue (45 seed + 752 created in Pass 2)
- **17,164 records (67.4%)** classified to existing clusters
- **2,281 records (9.0%)** placed as new-cluster founders
- **6,034 records (23.7%)** in pending-singleton pile
- **$39 sync / $19.50 batch** total spend, ~3 hours wall

### Cluster size distribution

| Band | Clusters | Records | % of clustered |
|---|---|---|---|
| 1-2 | 1 | 2 | 0.0% |
| 3-5 | 232 | 870 | 4.5% |
| 6-10 | 140 | 1,066 | 5.5% |
| 11-20 | 159 | 2,334 | 12.0% |
| **21-50 (workhorse)** | **165** | **5,463** | **28.1%** |
| 51-100 | 65 | 4,472 | 23.0% |
| 101-200 | 30 | 3,871 | 19.9% |
| 201-346 | 5 | 1,331 | 6.8% |

Largest cluster: 346 records = 1.8% of clustered. **No monster cluster** — the failure-mode space is genuinely diverse. Top 10 cover 11.5%; top 100 cover 49.8%.

### Why the "44% plateau" wasn't actually equilibrium

Mid-sweep (iters 13-22), the post-P1 orphan rate sat at ~43-48% across 10 iterations. We initially framed this as an attention-dilution equilibrium (catalogue-coverage growth offset by attention dilution as the prompt got longer). But running another 100+ iterations showed the rate continued declining to ~22-30% by the end. The plateau was a transient feature, probably reflecting a transition phase between mainstream-mechanism capture and long-tail discovery. Lesson: don't call a 10-iter plateau an equilibrium until you've run substantially longer.

---

## 4. Cross-project diversity validation

The central design claim of v2 — that mechanism-form clustering captures patterns
across project-vocabulary boundaries — is empirically confirmed.

For 15 stratified-sample workhorse clusters (size 21-50):

| Metric | Value |
|---|---|
| Mean unique projects per cluster | **17.8** |
| Mean unique arena categories per cluster | **6.9** (out of 20 total) |
| Records-per-project ratio | **1.58** |

Compared to v1's ~36% single-project-bound rate, v2 clusters consistently aggregate
evidence from 10-35 distinct projects spanning 5-12 of the 20 ARENA categories.
The same mechanism appears in solar PV, hydrogen electrolyser, biomass scale-up,
and storage projects — exactly the cross-project pattern matrix substrate the
methodology requires. This is one of the strongest validation moves available
for the paper.

---

## 5. Haiku 4.5 vs Sonnet 4.6 A/B

To explore using Haiku for the final per-record classification (cost reduction
~$120 → ~$30), an A/B test was run: 3 random 100-record samples from the pending
pile, each classified by both models against the 797-cluster catalogue.

| Model | Classified | Cost | Cost/call |
|---|---|---|---|
| Sonnet 4.6 | 42 / 300 (14%) | $4.37 | $0.0146 |
| Haiku 4.5 | 145 / 300 (48%) | $2.02 | $0.0067 |

**Agreement when both classify: 45.5%.** Hand-inspection of 20 disagreements:
- Sonnet correct: ~17/20
- Haiku correct: ~2-3/20

**Haiku force-fits on vocabulary** despite the explicit prompt instruction not to.
Examples: UV degradation of EVA encapsulant → Haiku c042 *Electrode Material
Degradation* (matched on "degradation"); iron-ore fines sticking in fluidised
bed → Haiku c042 same cluster (matched on "iron"); harmonic impedance polygon
methodology → Haiku c845 about meter sensitivity (mechanism unrelated).

**Conclusion:** Haiku is unsuitable for this classification task. Vocabulary
matching is the dominant failure mode; mechanism discrimination is unreliable.
Use Sonnet for the final pass. The cost differential is real but the precision
loss is unaffordable for a methodology-paper artefact.

---

## 6. Attention-degradation A/B test — and the prompt-method interaction

The hypothesis: as the catalogue grows, batched Pass 1 classification (200 records
× ~700 clusters in one call) misses true matches because attention dilutes across
record × cluster pairs. The per-record final sweep should recover those misses.

### 6.1 Test design

For target iters K = 30, 70, 110 (catalogue sizes 333, 571, 734):
1. Reconstruct the iter-K-start catalogue (procurement-probity invariant lets us
   do this exactly: signatures haven't changed).
2. Pull the 200 records classified in iter K from `corpus_assignments.jsonl`.
3. Run those records through both:
   - **Arm A**: batched Sonnet Pass 1, original sweep prompt (replication of the
     iter-K call in the production sweep)
   - **Arm B**: per-record Sonnet, same prompt language ("CRITICAL: Do NOT force-fit"
     + bullet list of mechanism-vs-vocabulary warnings)

### 6.2 Initial result (Arm A vs Arm B)

| Iter | Cat | A classified | B classified | Recovery (A-orph, B-clf) | Reverse (A-clf, B-orph) | Cross |
|---|---|---|---|---|---|---|
| 30 | 333 | 131 | 75 | 2 | **58** | 15 |
| 70 | 571 | 139 | 107 | 8 | 40 | 21 |
| 110 | 734 | 140 | 107 | 7 | 40 | 25 |

**Reverse rate (29-44%) dwarfed Recovery rate (3-13%).** The attention-degradation
hypothesis predicted the opposite. Initial interpretation: batched Pass 1 was
*over*-classifying (force-fitting), and per-record full attention was correctly
rejecting those force-fits.

### 6.3 Hand inspection of 12 Reverse cases

| Verdict | Count |
|---|---|
| Per-record (orphan) correct — batched force-fit on vocabulary or topic | 5-6 |
| Batched (classified) correct — per-record over-rejected a real match | 3 |
| Borderline | 3-4 |

Examples of legitimate force-fits batched made:
- *5-year project costed during COVID-19* → batched picked c005 *COVID-19 Pandemic
  Disrupting Project Delivery*. Real mechanism: long development period drives CPI
  escalation. COVID was incidental vocabulary.
- *Australia's macro fossil-fuel export exposure* → batched picked c587 *Long-Lived
  Fossil Equipment Stranded Asset Risk*. Different scale (national economy vs
  equipment investment).

Examples of records per-record (defensive prompt) wrongly orphaned:
- *Harmonics on inverter waveform visible only in field, not GridSim bench testing*
  → batched correctly placed in c652 *Test Environment Limitation Preventing Full
  Integration Test Coverage*. Per-record orphaned this exact-match record.
- *Sensitivity scenario for ash use in construction is mislabelled — only models
  removing ash landfilling, not full LCA* → batched correctly placed in c778
  *Scope Exclusion Causes Incomplete CBA*. Per-record orphaned it.

So per-record (Arm B) wasn't uniformly more correct — it was more *conservative*,
in a way that introduced its own errors symmetric to batched's force-fits.

### 6.4 The neutral-prompt experiment (Arm C, then Arm D)

Hypothesis: per-record's over-conservatism is driven by the defensive prompt
framing ("CRITICAL: Do NOT force-fit" + bullet list of don'ts). In a per-record
context with no neighbour-record calibration, the warning may bias the model
toward "orphan" as the safe default.

Initial test (Arm C): re-run per-record classification on the same iter-30/70/110
records with a **neutral, matter-of-fact prompt**:

> Your goal: assign the record to one of the listed clusters if one of them
> reasonably describes the causal failure mechanism the record discusses. If
> no existing cluster fits, the record remains unassigned (return "orphan").

No "CRITICAL" warning. No bullet list of mechanism-vs-vocabulary don'ts.

Then to verify the implicit calibration claim ("defensive is right for batched,
neutral for per-record"), the missing 2x2 cell was filled with Arm D: batched +
neutral prompt on the same records.

### 6.5 The 2x2 result

|              | Batched | Per-record |
|--------------|---------|-----------|
| Defensive    | A | B |
| Neutral      | **D** | C |

Classified records out of 200 per iter:

| Iter | A (batch+def) | B (per+def) | C (per+neutral) | **D (batch+neutral)** |
|---|---|---|---|---|
| 30 (cat 333) | 131 | 75 | 123 | **146** |
| 70 (cat 571) | 139 | 107 | 151 | **162** |
| 110 (cat 734) | 140 | 107 | 156 | **176** |

**Ordering is consistent: D > C > A > B at every iter.**

**A vs D** (batched, defensive vs neutral):
- A-only classifies (records A keeps that D drops): **1, 1, 0** — essentially zero
- D-only classifies: **16, 24, 36** — growing with catalogue size
- Same cluster among shared: 119, 123, 121
- Different cluster among shared: 11, 15, 19 (~10%)

The defensive prompt suppressed legitimate classifications in batched mode too,
just less aggressively than in per-record. ~16-36 records per batch wrongly
orphaned, with almost no D-classification getting reverted to orphan by A.

**C vs D** (neutral prompt held constant; only the method varies — the cleanest
test of attention dilution):
- C-only classifies: 9, 11, **2**
- D-only classifies: **32, 22, 22**
- Same cluster among shared: 89, 105, 115
- Different cluster among shared: 25, 35, 39 (~22%)

**Batched classifies more records than per-record at every iter, even with prompt
held constant.** This overturns the attention-dilution hypothesis I'd been
operating on. Cross-record calibration in batched mode is *helping*, not hurting.

### 6.6 Implications (corrected)

1. **The attention-dilution framing was wrong.** Batched > per-record at every
   prompt condition. The intuition that "per-record full attention should be
   more accurate" is an artefact of older models. Sonnet 4.6's long-context
   capability means batched processing is at least as good attention-wise, and
   gains a calibration signal from cross-record comparison.

2. **The defensive prompt was over-correcting in *both* methods.** The "do not
   force-fit" + bullet list of don'ts suppressed legitimate classifications.
   Per-record more so (since there's no neighbour calibration to anchor the
   model), but batched too (16-36 records per batch).

3. **Best single-method choice: batched + neutral prompt.** Cheaper than per-
   record, faster, and produces the most classifications without introducing
   reversals.

4. **The original sweep under-classified.** It used Arm A semantics (batched +
   defensive). Re-running with Arm D semantics (batched + neutral) on pending
   records should recover ~8-18% of records the defensive prompt wrongly
   orphaned, plus additional records orphaned because their iter-K catalogue
   was incomplete (the final 797-cluster catalogue covers more mechanisms).

5. **Cross-class disagreement (~10-22%) holds across all method/prompt
   combinations** — this is the catalogue-redundancy + LLM-nondeterminism
   floor, not method bias. Closure-phase merges should reduce it.

6. **The earlier "30% of classifications are wrong" panic from Arm B alone was
   wrong.** The Reverse-rate finding was a prompt artefact in per-record
   context. Under Arm D vs A comparison, the genuine over-classification rate
   in the original sweep is ~5-9% (the cross-class A-vs-D rate among records
   both classify), and almost no records get re-orphaned (~0.5%).

### 6.7 Methodological note

This is the kind of finding the paper should foreground:

- The naive interpretation of Arm B's results would have been "the catalogue
  has 30% mis-classifications; run a $310 audit reclassify."
- After running Arm C: "no, defensive prompting interacts with per-record badly;
  per-record + neutral is the answer."
- After running Arm D (the missing 2x2 cell): "no, attention dilution isn't even
  the main story — batched > per-record at any prompt. The right answer is
  batched + neutral."

Each step would have been a defensible-sounding conclusion if we'd stopped there.
Each was wrong. Only the full 2x2 reveals the actual structure: prompt and method
both matter, they interact, and the older intuition that 'per-record is the
gold-standard' is obsolete on Sonnet 4.6.

The prompt-by-method interaction was only visible because we ran a controlled
experiment that varied both factors at fixed catalogue snapshots. The procurement-
probity invariant made these snapshots reconstructible at zero extra
instrumentation cost.

**The unifying principle** (cross-confirmed by an earlier dedup-stage experiment
in this codebase, commits 885826e + 921c4c9 + 698e860): *for tasks that apply a
rule across a set of items, present the items together*. Co-presented items give
the model cross-item comparison as an implicit calibration anchor; chunking or
per-item processing strips it away. Modern Sonnet's long-context capability
means you pay almost nothing in attention quality for the larger context, and
you gain calibration. The older GPT-3 / Claude-2 intuition that "smaller prompts
are better" is obsolete on Sonnet 4.6 and should be inverted: *default to one-
shot / batched unless you have a hard reason not to*.

---

### 6.8 Precision envelope — three components compounding

A separate observation from the residual orphan-clustering run (script 14)
sharpens the precision picture. Each chunk's Pass 1 classifies the chunk's
~180 residual records against the same matured 797-cluster catalogue that
script 13 had already rejected them against. In an ideal world this should
classify zero records (they've all already been determined to be orphan
relative to that exact catalogue).

In practice, **~8% of residuals classify into the original catalogue** in
this Pass 1, despite having been rejected by the same prompt+catalogue+model
in the previous run. With chunk-level variance (1-20% across chunks; 20% in
chunk 1).

This is higher than pure LLM nondeterminism alone (3-13% replication jitter
measured earlier in Arm A vs original sweep). The chunk-level variance and
the batch-by-batch instability suggest a real *batch-composition sensitivity*
effect on top of the nondeterminism floor.

**Three components of the precision envelope (additive, all real):**

1. **LLM nondeterminism floor (~3-5%)** — same model, same input, slightly
   different output. Inherent in temperature=0 sampling at scale; can't be
   eliminated.

2. **Batch-composition sensitivity (~3-7%)** — same record + same prompt +
   same catalogue, but *different neighbouring records in the batch* produces
   different classifications. The cross-record calibration signal that helps
   batched mode (vs per-record) is also a source of variance: it's calibrated
   to the actual neighbours, and different neighbours → different calibration.
   Consistent with the one-shot-vs-chunked finding (§6.7): cross-record
   comparison is real signal, but it's contextual signal.

3. **Cluster-boundary fuzziness (~10-22%)** — when both methods (or both
   prompt conditions) classify a record, they pick *different clusters* a
   substantial fraction of the time. This isn't classifier error; it's the
   catalogue itself having adjacent / near-redundant clusters where the
   choice between them is genuinely ambiguous. Closure-phase merges should
   reduce this.

**For the methodology paper (honest framing):**

> Identical-input replication is ~85-90% (component 1). Identical-input-but-
> different-batch-composition replication is ~80-85% (components 1+2). Among
> records that two regimes both classify into *some* cluster, agreement on
> *which* cluster is ~75-90% (components 1+2+3). Each component is small
> individually but they compound, and they're bounded rather than dismissed.

This is much more defensible than claiming "the catalogue is correct" or
"records are placed accurately" without quantification. The artefact's
precision is a stack of three measured terms; readers can judge whether the
stack is acceptable for the claims being made.

**Closure-phase implication:** the third component (cluster-boundary fuzziness)
is the only one closure-phase work can directly reduce. The first two are
properties of the model and method; the third is a property of the catalogue
and is amenable to merge/split operations on near-redundant clusters.

---

## 7. Procurement-probity invariant — design-decision compounding

The probity rule (cluster signatures are immutable post-publication) was
introduced for defensibility: you can't retroactively change the matching rule
under which records joined a cluster, any more than you can change tender
criteria post-award.

That decision compounded:

1. **Reconstructibility for free.** Any past iteration's catalogue state is
   reconstructible from the current catalogue (subset by creation iter). No
   per-iteration snapshots needed. This made the attention A/B test possible
   without prior instrumentation.

2. **Auditable reclassification policy.** When considering an audit-reclassify
   pass on the catalogue's classified records, the founders (records that
   *defined* a cluster's signature) are exempt — reassigning them would unfound
   the cluster. Subsequent classifications under that signature are auditable
   applications of the criterion. The probity rule cleanly separates the two
   populations:

   | Population | Count | Status |
   |---|---|---|
   | Orphan-pass founders | 2,281 | Untouchable |
   | Seed-pass founders | 143 | Untouchable |
   | Subsequent classifications (audit pool) | 16,999 | Auditable |
   | Pending singletons | 6,034 | Final-sweep target |

3. **Cross-batch fairness defence.** The argument that no record's *final*
   placement depends on processing order rests on the immutability rule plus
   the final per-record sweep against the matured catalogue. Without the
   invariant the argument collapses.

For the methodology paper: framing this as *procurement probity* (rather than
*reproducibility* or *invariant-preserving design*) connects to a regulatory
discipline the audience already understands. Government infrastructure readers
recognise the principle instantly.

---

## 8. Cost summary

| Operation | Cost (sync) | Cost (batch API) |
|---|---|---|
| Tagging (day 1) | $141 | — |
| Dedup (day 1) | $121 | — |
| Seed pass | ~$1 | — |
| Iterative sweep (128 iters × 200 records) | $39 | $19.50 |
| Haiku-vs-Sonnet A/B | $6 | — |
| Attention A/B (Arms A, B, C) | $26 | — |
| 2x2 completion (Arm D) | $1 | — |
| **Subtotal day 2** | **~$73** | |
| **Day 1 + Day 2 total** | **~$335** | |

Pending operations (revised under Arm D semantics — batched + neutral):

| Operation | Records | Estimate |
|---|---|---|
| Pending-pile reclassify (Arm D, 31 batches × 200) | 6,034 | ~$6 |
| Final residual orphan-clustering (1 combinatorial call) | ~3-4k | ~$5 |
| Closure pass (merge/split/late-bind descriptions) | catalogue review | ~$5-10 |
| Optional: audit reclassify of classified pool (Arm D, 86 batches × 200) | 17,164 | ~$17 |

Way cheaper than the per-record-cached estimate ($120 → $6 for the pending sweep).
Batched + cached caching is unnecessary; the prompt is the same across calls in
a single batch and the per-batch overhead is small.

---

## 9. Defensible plateau and the 4-day plan

The v2 work has reached its defensible plateau. The next cheapest validation
step (hand-adjudicated ground-truth precision/recall on a sample) would take a
focused week; adding ANAO as a proof-of-generalisation would take weeks more.
Both push past the 2026-05-07 grey-paper deadline. What's already demonstrated
already constitutes a paper-grade contribution.

The remaining 4 days are *consolidate, write, present* — not another lap of
validation.

### Next steps

1. **Re-run the pending pile (6,034 records) under Arm D — batched + neutral.**
   31 batches of 200, against the matured 797-cluster catalogue. Expected
   yield: 30-60% classify into existing clusters (~1,800-3,600 records); the
   rest are genuine residual orphans. Runtime ~30 min, cost ~$6.

2. **Final residual orphan-clustering** (one combinatorial call on whatever
   doesn't classify in step 1, with neutral prompt). Forms any genuinely
   novel mechanism clusters that survive the larger pile.

3. **Optional audit reclassify of the 17,164 classified records under Arm D.**
   Expected effect: ~10% (~1,700) shift to a different (usually neighbouring)
   cluster; ~0.5% (~85) get re-orphaned. Most cluster-shift cases are
   catalogue-redundancy artefacts that the closure pass should resolve via
   merges. Worth doing for the methodology paper to report a consensus number,
   but probably not strictly needed for the artefact.

4. **Closure pass.** Merge near-duplicate clusters (~7-10% rate observed),
   split heterogeneous clusters, generate late-bound descriptions. Done after
   step 1 (and optionally 3) so populations are full.

5. **Methodology paper draft** (deadline 2026-05-07). The key sections write
   themselves now: cross-project diversity validation, the **2x2 prompt-method
   experiment finding** (batched + neutral wins, batched > per-record on
   modern Sonnet), procurement-probity framing, two-pass cascade design,
   closure-phase taxonomy of allowed post-hoc operations, and the unifying
   one-shot-vs-chunked principle.

---

## 10. Closure phase — merge investigation and substrate extraction

After the iterative sweep + reclassify + residual + convergence pipeline produced the final 1,141-cluster catalogue, the closure phase investigated:
1. Cluster-redundancy via merge identification (multiple methods, multiple models)
2. Substrate-extraction: classifying clusters as renewable-bound vs general

Both produced strong validation results. **Merges are not being applied** — the test confirmed redundancy is too low (<2%) to justify the audit cost. Substrate extraction produced a paper-headline finding (62.3% of mechanisms are general beyond renewable energy).

### 10.1 Merge investigation — five methods tried

The merge investigation cycled through several approaches as we learned what worked. Workspace: `closure/code/`.

**Step 1 — Embedding shortlist (`01_identify_merge_candidates.py`).** Embedded all 1,141 clusters' `canonical_name + mechanism_signature` with Qwen3-Embedding-4B; computed pairwise cosine similarity matrix (650k pairs in milliseconds via GPU matmul). Output:

| Threshold | Pairs |
|---|---|
| 0.80 | 1 |
| 0.75 | 11 |
| 0.70 | 78 |
| 0.65 | 363 |

Hand-spot-checked three known-merge pairs we'd identified earlier:
- c027 ↔ c738 (tariff structure, customer-side vs network-side): cos **0.56** — embeddings miss
- c744 ↔ c591 (environmental contamination): cos **0.43** — embeddings miss
- c003 ↔ c679 (regulatory misalignment with novel tech): cos higher, would shortlist

**Lesson:** embeddings catch *semantic-form* near-duplicates well but miss *same-mechanism-different-perspective* pairs. The c027/c738 type cases — where the underlying mechanism is identical but the language is genuinely different — fall below any defensible cosine threshold.

**Step 2 (deleted) — Qwen 7B pair adjudication.** Initial design: send the 363 embedding-shortlisted pairs to local Qwen2.5-7B-Instruct in 4-bit for merge/keep-separate verdicts. Built `02_adjudicate_merges_local.py` then deleted it after Jeff's correction: he wanted Qwen to do the *candidate identification* step (replacing the embedding shortlister), not just adjudicate an embedding-derived shortlist.

**Step 2 (rebuilt) — Qwen 7B chunked group-finder (`02_qwen_groupfinder.py`).** K-means partition of cluster embeddings into 25 regions of ~45 clusters each; for each region, run Qwen with a "find merge groups within this region" prompt. Result: **2 merge groups proposed across 25 regions**, both poorly chosen:
- c004 + c005 (Supply Chain Disruption + COVID-19 Pandemic): force-fit on "disruption + delivery" vocabulary — different mechanisms
- c003 + c550 (regulatory): plausible, single confirmed match

Qwen 7B 4-bit was too weak for the subtle semantic-mechanism discrimination this task requires. Both failure modes were present simultaneously: over-conservative (missing real merges) AND force-fit-on-vocabulary (wrong merges). Unsuitable.

**Step 3 — Opus 4.7 one-shot over full catalogue (`03_opus_groupfinder.py`).** Pivoted to the right tool. The whole 1,141-cluster catalogue (~84k input tokens) fits comfortably in Opus's 200k context. One call, one output. Result:

- **17 merge groups** (15 two-cluster, 2 three-cluster), 36 clusters affected (3.2% of catalogue)
- $1.74 sync, 24 seconds wall

Hand-judged the 17:
- Strong same-mechanism: 5 (c5+c9 chicken-and-egg, c12 lab-vs-field, c15 transport-emissions, c16 new-tech failures, c17 multi-party coordination)
- Plausible: 3 (c4 high-capital, c7 community opposition, c14 policy uncertainty)
- Borderline / category-level: 5 (Group 1 rework cascade variants, Group 2 late-discovery variants)
- Wrong (force-fits): 2 (Group 3 supply-chain shock vs steady-state logistics, Group 11 unfamiliarity vs regulatory uncertainty)
- Spurious (Opus included a "do NOT merge" group): 1

Then spot-checked the three known-merge candidates: **all three were missed by Opus.** That's evidence that the one-shot result is an undercount.

**Step 4 — Opus 4.7 with greedy-NN-ordered catalogue (`04_opus_groupfinder_nnpath.py`).** Hypothesis (Jeff's): the catalogue order in script 03 was cluster_id-numerical, putting similar clusters far apart in the prompt. A greedy nearest-neighbour walk through the embedding space would put each cluster adjacent to its embedding-nearest neighbour, exploiting Opus's local-attention windows.

Result: **17 merge groups** (same count as cluster_id-order), 33 clusters affected, $1.74. Adjacent-pair sim: mean 0.56, max 0.80.

Known-pair recovery vs cluster_id-order:
- c027 + c738: still missed (cos 0.56 — the NN walk didn't put them adjacent because each had multiple high-similarity competitors)
- c744 + c591: still missed (cos 0.43 — too low)
- **c003 + c679: CAUGHT** ← NN-ordering helped on this one

The NN-ordered run found *partially different* groups from the cluster_id-order run. Combining both runs → ~24 union pairs; 8 intersection pairs.

**Step 5 — Sonnet 4.6 with NN-ordered catalogue (`04_*` with `--model claude-sonnet-4-6`).** Jeff's intuition: Sonnet sometimes outperforms Opus, worth checking.

Result: **338 merge groups, 615 of 1,141 clusters affected (53.9%).** Catastrophic over-collapse — Sonnet treated *any two related mechanisms* as merge candidates, including obvious siblings within parent categories. $0.53, 433 seconds wall.

This was a decisive empirical finding: same prompt + same data, Opus → 17, Sonnet → 338. **20× discrepancy.** Strong evidence that Sonnet has very different failure-mode tolerance for cross-item pattern-detection tasks than for per-item attribute-tagging (where it under-flags). Saved as memory `feedback_match_model_to_task_failure_mode.md`.

**Reconciliation: Opus ∩ Sonnet.** 8 intersection pairs (highest-confidence merges). Hand-judged: ~88% precision (7 of 8 are clear/strong merges; 1 is borderline siblings).

20-pair sample of Sonnet-only (the 332 Sonnet flagged but Opus didn't): hand-judged distribution:
- Strong merges: 1 (c1107+c1181 inverter kVA saturation — Sonnet caught what Opus missed)
- Plausible: 4
- Borderline siblings: 4
- Clearly wrong (force-fit): 11 (55%)

Extrapolating: 332 × 25% real merge rate ≈ ~80 real merges hidden in Sonnet-only output, but ~180 false positives. Signal-to-noise too low to apply Sonnet-only results without filtering.

**Step 6 — Within-tech distinctness probe (`05_opus_battery_subset.py`).** Selected the top-50 battery-storage-dominated clusters (size ≥10, battery_share 42-95%). Asked Opus the same merge-finding question but on only this 50-cluster subset (~4k input tokens, full attention).

Result: **0 merge groups proposed.** $0.08, 3 seconds.

This rules out the "Opus's 17 was attention-limited at the 1,141-cluster scale" hypothesis. With 50 closely-related (same-tech) clusters in a focused prompt, Opus still finds zero merges. The catalogue's mechanism-level distinction holds *within* a single tech category, not just across categories. Saved as memory `project_v2_within_tech_distinct.md`.

### 10.2 Final merge picture and decision

| Metric | Value |
|---|---|
| Embedding shortlist pairs (cos≥0.65) | 363 |
| Opus catalogue-wide (cluster_id order) | 17 groups |
| Opus catalogue-wide (NN order) | 17 groups |
| Sonnet catalogue-wide (NN order) | 338 groups (over-collapse) |
| Opus battery-subset | 0 groups |
| Opus + Sonnet intersection | 8 pairs (88% precision) |
| Hand-identified known merges (3) | 1 caught by Opus (NN), 2 missed by all automated methods |

**Realistic true merge count: ~15-25 pairs out of 1,141 clusters (~1.5-2% of catalogue).**

**Decision: not applying the merges.** Cost-benefit doesn't justify it:
- Each merge requires hand-review + cluster_id retag + downstream re-stat
- Net effect on the artefact: cluster IDs change for ~30 records; analytical conclusions don't
- The *non-application* itself preserves procurement-probity cleanly: signatures stay literally immutable from the sweep

**Methodology paper framing:** "Merge candidates were identified empirically through embedding similarity (363 pairs above cos 0.65), one-shot Opus and Sonnet group-finding (17 vs 338 — Sonnet's over-collapsing was diagnostic of model-task mismatch), within-tech subset probe (0 merges in a 50-cluster battery-dominated focus), and hand-identified semantic-perspective pairs. True redundancy was quantified at <2% of catalogue. Merges were not applied because the marginal artefact improvement did not justify the audit cost; the non-application preserves the procurement-probity invariant in its strict form."

### 10.3 Substrate extraction (`06_extract_general_mechanisms.py`)

Separately, Opus classified all 1,141 clusters as either GENERAL (causal pathway applies broadly beyond renewable energy) or TECH_SPECIFIC (depends on physics/equipment/markets specific to renewable). For general clusters, also tagged 1-3 broader-domain tags.

Result: **711 of 1,141 (62.3%) are general mechanisms.** Top domain tags: program_design (150), infrastructure_project_delivery (147), data_systems_integration (116), regulatory_framework_design (103), modelling_methodology (99), supply_chain (95), equipment_lifecycle (91), novel_technology_adoption (82). $4.59, 4.5 min.

**Caveat — boundary fuzziness:** sample of "tech_specific" clusters revealed that ~30-40% are actually domain instances of general patterns (Jevons paradox, design trade-offs, collective-action failures, system-architecture trade-offs) that didn't match the prompt's domain-tag vocabulary. Real general fraction is probably 70-80%, not 62%. The 62% is a defensible *lower bound* — anyone challenging it can only push it higher. Decision: don't refine further; the lower-bound framing works for the paper.

**Methodology paper framing:** "Of 1,141 clusters, at least 711 (62.3%) describe mechanisms whose causal pathways apply beyond renewable energy contexts. The remaining 430 are renewable-bound by Opus's binary classification, though many are domain instances of more general patterns identifiable in adjacent infrastructure corpora."

This reframes what the v2 methodology produced: not a renewable-energy taxonomy, but a **~700-mechanism general taxonomy of infrastructure / program / coordination failures**, plus a tech-specific layer. The general substrate is what transfers to ANAO, PC, APH, and any future infrastructure corpus.

### 10.4 Outputs (force-committed under gitignored corpora/)

All in `closure/output/`:
- `cluster_embeddings.npy` + `cluster_ids.json` — Qwen3-4B embeddings of all 1,141 cluster signatures
- `merge_candidates.json` — 363 embedding-shortlisted pairs with cosine scores
- `merge_groups_opus.json` — Opus cluster_id-order: 17 groups
- `merge_groups_opus_nnpath.json` — Opus NN-order: 17 groups
- `merge_groups_sonnet_nnpath.json` — Sonnet NN-order: 338 groups (over-collapse reference)
- `merge_groups_battery_subset.json` — Opus on battery subset: 0 groups
- `general_mechanisms.json` — all 1,141 classifications with domain tags
- `nn_path_order.json`, `region_assignments.json` — auxiliary

All committed in git history (force-added) for durability.
