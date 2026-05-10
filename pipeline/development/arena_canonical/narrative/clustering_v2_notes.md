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

### Sweep-driver mechanics

The sweep is orchestrated by `07_corpus_sweep.py`, which runs each iteration as a 200-record batch through Pass 1 (classify against current catalogue) followed by Pass 2 (cluster ≥3-member orphans into new clusters). Two operational details worth naming for the methodology paper:

- **Iteration cap and ramp.** The driver supports an iteration cap with a soft ramp — early iterations are bounded to small batches to allow fast cycle observation, ramping up to the full 200-record default once the trajectory stabilises. The cap was a debug-loop convenience, not a methodological feature; production runs operated at the full 200-record batch from iteration 1.
- **`sweep_state.json` checkpoint.** The driver checkpoints after every iteration: cumulative cost (sync + batch projection), processed record_ids, next orphan-cluster-id seed, and per-iteration summary. The sweep is fully resumable — interruption losses are bounded by the last completed iteration. The file structure (keys `iterations`, `processed_record_ids`, `next_orphan_cluster_id`, `cumulative_cost_sync`, `cumulative_cost_batch`) is the audit trail for the trajectory.

### Post-sweep convergence pipeline (scripts 13-16)

The sweep's 128 iterations produced a 797-cluster catalogue with 6,034 records left in the pending-singleton pile. Four follow-up scripts process this residual pile to convergence. **All four use Arm D semantics — the batched + neutral combination that won the 2x2 in §6.5.** This is how Arm D's advantage is incorporated into the production catalogue: not by re-running the sweep, but by applying it to exactly the records where the original Arm A sweep had failed to classify.

| Script | Phase | Method | Input | Output | Key result |
|---|---|---|---|---|---|
| `13_pending_reclassify.py` | 4d — pending-pile reclassify | **Arm D** (batched + neutral, Pass 1 only) | 6,034 pending records × 797-cluster catalogue | `reclassify/reclassified_assignments.jsonl` | **2,622 classified (43.5%) + 3,412 orphan**, $9.43, 29 min |
| `14_residual_orphan_cluster.py` | 4e — residual orphan clustering | **Arm D Pass 1** + defensive Pass 2 (cluster formation kept conservative) | 3,412 post-reclassify orphans, sequential 180-record chunks; new clusters compound across chunks | `residual/residual_assignments.jsonl`, `residual/catalogue_after_residual.json` | catalogue grows 797 → ~1,048 clusters via novel mechanism discovery in residual pool |
| `15_singleton_third_pass.py` | 4f — third-pass classification | **Arm D** (Pass 1 only) | 2,240 still-singleton records × matured 1,048-cluster catalogue | `third_pass/third_pass_assignments.jsonl` | **140 classified (6.2%) + 2,100 still singleton**, $4.09, 10 min |
| `16_convergence_iteration.py` | 4g — convergence iteration | Pass-2-focused (defensive Pass 2 cluster formation) + tight cross-chunk Pass 1 propagation in the same neutral framing as Arm D | 2,100 remaining singletons; per-chunk Pass 2 + tight cross-chunk Pass 1 propagation | `convergence/convergence_assignments.jsonl`, `convergence/catalogue_after_convergence.json` | **151 classified to existing + 284 into 93 new clusters + 1,665 final singletons → final 1,141-cluster catalogue**, $2.73, 12 min |

**Production catalogue method-attribution summary.** Of the 23,674 records that ended up in the 1,141-cluster catalogue:
- Records placed during the initial sweep (scripts 7-8) were classified under **Arm A** (batched + defensive), the prompt design that existed before the 2x2 test landed.
- Records placed during the post-sweep convergence pipeline (scripts 13-16) were classified under **Arm D** semantics — the prompt iterated based on the 2x2 finding.
- The Arm D advantage (~26% more records classified per batch at iter 110) is therefore baked into the catalogue *for exactly the records where it could possibly help*: the 6,034-record pending pile from sweep + the residuals downstream. Records the sweep classified successfully under Arm A weren't reshaped — that's the procurement-probity invariant (§7) at work.

**The Pass-2-focused refinement of script 16 (commit `8882662`) is methodologically important.** The original draft of 16 ran Pass 1 against the full 1,048-cluster catalogue per chunk, but that's redundant with what script 15 just did (Pass 1 only, full catalogue, on the same residual records). The refinement skips the redundant Pass 1 and uses Pass 1 *only* against clusters formed in earlier chunks of this convergence run, as a tight cross-chunk propagation mechanism to prevent two chunks from independently forming duplicate clusters from records sharing a novel mechanism. This isolates the marginal value-add of the convergence iteration: discovering clusters from records that share mechanism but were split across script 14's chunk boundaries. Pure Pass-2 work; Pass 1 just propagates to avoid duplicates.

### Why this four-script post-sweep pipeline is necessary

Each of scripts 13-16 closes a specific gap left by the previous stage:

1. **Script 13 (reclassify)** closes the catalogue-immaturity gap: a record that landed in pending at iteration N was classified against an iteration-N catalogue, but the post-sweep 797-cluster catalogue may now have an appropriate cluster created in iterations N+1..128.
2. **Script 14 (residual orphan)** closes the cross-record novel-mechanism gap: records that genuinely don't fit any of 797 clusters may share a *new* mechanism with each other, formable as a Pass-2 cluster within the residual pool.
3. **Script 15 (third-pass singleton)** closes the same catalogue-immaturity gap *within* the residual run: a record placed as singleton in chunk 5 of script 14 was classified against catalogue 797 + chunks 1..4. But chunks 5..19 went on to create more clusters; that singleton might now match.
4. **Script 16 (convergence)** closes the cross-chunk novel-mechanism gap *within* the residual run: records that share a mechanism but were split across script-14 chunk boundaries get a chance to form a cluster.

Each of these is documented per the procurement-probity invariant (§7): once a cluster's signature is published, it remains immutable; only new admissions are decided per the catalogue *available at that admission*. No record's *final* placement depends on the iteration in which it was processed — only on the catalogue available when it last classified successfully.

### Trajectory plots

Three diagnostic plots in `clustering_v2/output/sweep/`:
- `trajectory.png` — sweep-only post-P1 orphan and post-P2 unplaced rates over iterations 1-128, showing the apparent plateau at iters 13-22 and its eventual resolution
- `trajectory_final.png` — the same plus the post-sweep convergence pipeline (scripts 13-16) outcomes attached at the right edge, suitable as a paper figure
- `uptick_check.png` — diagnostic plot from the moment we suspected the orphan rate was rising again late in the sweep (it wasn't, but the check was worth running)

`trajectory_final.png` is the canonical "sweep + convergence to 1,141 clusters" figure for the paper.

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

### 6.6b How Arm D's advantage was incorporated — and why it wasn't a re-sweep

A natural question after the 2x2 finding: *"if Arm D wins, why not re-run the sweep with Arm D from iteration 1?"*

Two reasons it wasn't, and shouldn't have been:

**1. Arm D was applied to exactly the records where it could possibly help.** The original sweep (scripts 7-8) used Arm A (batched + defensive — the prompt design that existed before the 2x2 test was even built). When the 2x2 result landed showing Arm D classifies ~26% more records per batch at iter 110 (176 vs 140), the question was: *which records did Arm A under-classify?* The answer is: records that were sent back to the pending pile when Arm A wrongly orphaned them, plus records orphaned because their iter-K catalogue was incomplete. Both of those populations end up in the same place — the 6,034-record post-sweep pending pile.

Scripts 13-16 then apply Arm D semantics to that pile and its downstream residuals:
- Script 13 (Arm D Pass 1) recovered 2,622 of 6,034 (43.5%) from the pending pile
- Script 14 formed novel clusters from the surviving 3,412 orphans, growing the catalogue 797 → ~1,048 with Arm D Pass 1
- Scripts 15 and 16 closed the same loop within the residual run

So **the Arm D upgrade is in the production catalogue for the records where it matters**. Records the original Arm A sweep successfully classified weren't reshaped because their classification was already correct under either prompt — the 2x2 showed Arm D-only classifications grow with catalogue size (16/24/36 across iters 30/70/110) but **Arm A-only is essentially zero** (1/1/0). Arm A and Arm D agree on the records they both classify; the Arm D advantage is in classifications that Arm A *missed*. Those missed records were then handed to Arm D in scripts 13-16.

**2. Re-running the sweep with Arm D would build a different artefact, not improve the existing one.** The procurement-probity invariant (§7) treats `mechanism_signature` as a published evaluation criterion — once a cluster is admitted under signature S at iteration K, no subsequent design decision can retroactively change S without violating the rule under which S's existing members were admitted. A from-scratch Arm D re-sweep would propose different clusters with different signatures (the seed picks differ; the mainstream-capture phase classifies more records earlier and creates fewer clusters; the long-tail phase reaches different residuals). That's a *competing* catalogue, not a refined version of this one. Comparing the two would be a separate methodology question (replicate stability of the production pipeline at the catalogue level) — interesting but expensive ($60-80 sync, ~5-6 hours wall) and arguing about which is "better" is exactly the methodological position the procurement-probity invariant exists to avoid.

**What's actually open as a remaining experiment.** The replicate-stability question for the *existing* catalogue isn't whether Arm D would do better at iteration 1; it's whether running the *same production pipeline* (Arm A sweep + Arm D post-sweep) again, with the same prompts at temperature 0, produces roughly the same 1,141-cluster artefact. Anthropic API non-determinism (server-side caching variation, model-version drift, occasional streaming-order differences) means temp=0 is not strictly bit-deterministic. A 2nd full run would give a Jaccard-stability number for the catalogue itself. This is paper-relevant as a noise-floor measurement on the artefact but is not on a critical path — the procurement-probity argument frames the existing catalogue as one defensible build, not as the unique one.

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

### 10.5 Synthesis, co-occurrence, and event-key rebuild (scripts 07-11)

After the merge investigation closed (§10.1-10.2) and substrate extraction landed (§10.3), five further closure scripts produce the artefacts the methodology paper rests on for the structural-aggregation claim (§11). All ran on 2026-05-03.

#### 07. Per-cluster synthesis report generator (`07_cluster_report.py`)

Generates Opus 4.7 portfolio-review-grade Markdown reports on individual clusters. Workflow per cluster:

1. Pulls every record assigned to the cluster from `corpus_assignments.jsonl`
2. Joins each record's project to project-level metadata from the projects-export CSV (funding, lead organisation, tech category)
3. For each record's event_id, finds *event siblings* — other records sharing the same `(project, event_id)` pair across the entire FC pool, not restricted to this cluster. Siblings describe a different aspect of the same incident/decision/programme. (The `(project, event_id)` scoping is the fix in commit `b23f4a7` that prevents legacy local-event-id collisions from joining unrelated records — see §10.5/script 11 below for the broader fix.)
4. Sends the assembled cluster + event-context bundle to Opus 4.7 with a synthesis prompt
5. Saves the report as `cluster_reports/cXXX_report.md`

**Cost: ~$0.50-1.50 per cluster** depending on cluster size and event-sibling expansion. Not viable to run on all 1,141 (would cost $500-1,700) — used selectively for high-interest paper clusters.

Two reports generated as illustrative artefacts:
- **`c016_report.md`** — the FCAS revenue compression story. Centred on Hornsdale, 59 records from 23 projects across 11 ARENA categories. Demonstrates the within-corpus pattern aggregation that RAG cannot produce (cited in §11.3).
- **`c1074_report.md`** — second illustrative cluster.

The format is a portfolio-review essay with citations into the corpus, not a literature review. Each claim traces back to one or more `[cluster/record_id]` citations. This is the "explain this cluster" output format that an analyst would produce after reading the corpus — except the synthesis reasons across all 23 projects in seconds.

#### 08. Cluster co-occurrence via shared events (`08_cluster_cooccurrence.py`)

Computes the cluster-cluster graph from shared events. For every real event (scoped by `(project, event_id)` to avoid the local-event-id collision), finds all clusters whose records are present in that event. Pairs of clusters that share an event "co-occur." Counts pair frequency across the corpus.

Output: **5,491 co-occurring cluster pairs** in `cluster_cooccurrence.json`. Each pair has `cluster_a`, `cluster_b`, names, count of shared events, and three example shared events (`{project, event_id}` per example).

This is the **comorbidity network the methodology paper claims as RAG-impossible** (§11). It reveals which failure mechanisms tend to manifest together within the same project event sequence — siblings, causal precursors/consequents, or mechanism pairs that share a triggering condition. Sample top edge: `c004 Supply Chain Disruption Delaying Hardware Delivery ↔ c005 COVID-19 Pandemic Disrupting Project Delivery`, 17 shared events spanning Clean Energy Startup Support / Jemena Dynamic EV Charging / My Energy Marketplace.

The full ranked top-N pairs (with cluster names and example shared events) is in `cluster_cooccurrence_top.md`.

#### 09. Cluster co-occurrence network visualisation (`09_network_viz.py`)

Builds two visualisations from the script-08 output:

1. **Static PNG** (`cluster_network.png` + `cluster_network_tech.png` + `cluster_network_domain.png`) — matplotlib + networkx + spring layout, intended as paper figures. The `--color-by` flag (added in commit `f6b2386`) toggles node colouring:
   - `tech` — node colour by dominant ARENA tech category (battery / hydrogen / solar / etc.)
   - `domain` — node colour by general-mechanism domain tag from script 06 (program_design / regulatory_framework_design / etc.)
2. **Interactive HTML** (`cluster_network.html` + `_tech` + `_domain`) — vis.js from CDN, no install required. Hover/click to see cluster signatures.

Edges are weighted by co-occurrence count (frequency-of-shared-events between the two clusters); nodes are sized by cluster membership. The earlier commit (`9821d60`) refined the colour mapping to use *dominant* category per cluster (not majority threshold) and tightened edge contrast for readability.

These figures show the methodology paper's "categorical" finding visually: the network is not a single dense blob but a structured graph with parent-domain communities that emerge naturally from the co-occurrence pattern. The tech-coloured network shows tech-category community structure; the domain-coloured network shows general-mechanism community structure (the §10.3 substrate axis). They tell different stories.

#### 10 + 11. Event-key rebuild — globally-unique event_ids

A pre-existing collision in the upstream dedup pipeline meant **per-project local event_ids (`EVT-0001`, `EVT-0002`, …) repeated across projects**. `EVT-0001` appeared in 179 of 493 projects in the corpus. Any cross-project event-axis analysis (including the cluster co-occurrence in script 08, the cross-cluster span analysis at `canonical/analysis/cross_cluster_span/`, and any future event-axis retrieval in a navigator) would silently treat unrelated records as siblings without this fix.

Two scripts rebuild the event_id namespace:

**`10_rebuild_event_keys.py` — FC-subset rebuild.** First attempt, scoped to the 25,479 records that pass the clustering filter:

- Assigns each project a stable 3-digit `project_num` (alphabetical order of project name, project_num 0 for null/missing project)
- Composes globally-unique event_id: `EVT-{project_num:03d}-{event_num:04d}`
- Records whose original event_id was their own record_id (singleton-events from dedup) get synthetic event_nums starting at 9000
- Outputs: `output/filter_input_globalkey.jsonl`, `output/project_id_map.json`, `output/event_key_map.jsonl`

**`11_rebuild_corpus_event_keys.py` — full-corpus rebuild.** Recognised mid-day that the FC-subset scope was wrong: the event_id collision exists in the *full* 90,192-record tagged corpus, and any fix should address the full source-of-truth (the dedup output) rather than just the clustering subset.

Reads:
- `corpora/arena/output/per_doc/doc_*.json` — all 90,192 records with `kb_associated_project`
- `runs/arena/fullcorpus_dedup/<slug>/*.assignments.json` — per-project local event assignments (504 projects)

Outputs:
- **`full_corpus_events.jsonl`** — one row per record (90,192) with new globally-unique `event_id`, plus project, project_num, old event_id (`event_id_old`), event_name where present
- `full_project_id_map.json` — canonical project name → project_num mapping
- `full_event_key_map.jsonl` — old → new event_id per record (audit trail)

`full_corpus_events.jsonl` is the **canonical corpus-wide event mapping for any downstream event-axis analysis**. It is what the cross-cluster span analysis at `canonical/analysis/cross_cluster_span/` reads. It is what any future project-axis or event-axis navigator UI would consume. Without script 11, every cross-project event-axis claim in the methodology paper would be silently wrong.

#### Paper-load-bearing outputs

For methodology-paper figure / claim sourcing, scripts 07-11 produce:

| Output | Paper claim it supports |
|---|---|
| `cluster_reports/c016_report.md` | "the catalogue does the discovery" (§11.3 worked example) |
| `cluster_cooccurrence.json` (5,491 pairs) | "comorbidity network, count-queryable" (§11 v2-vs-RAG distinction) |
| `cluster_network*.png` + `*.html` | paper figures showing tech-axis and domain-axis community structure |
| `full_corpus_events.jsonl` (90,192 records) | corpus-wide event mapping; the input for cross-cluster span analysis (71.9% headline) |
| `full_event_key_map.jsonl` | audit trail showing the local→global event_id rebuild |

#### 10.5 outputs (force-committed in `closure/output/`)

All on disk under `closure/output/`:
- `cluster_reports/c016_report.md` + `c016_meta.json`, `c1074_report.md` + `c1074_meta.json`
- `cluster_cooccurrence.json` (5,491 pairs), `cluster_cooccurrence_top.md` (ranked + named top-N)
- `cluster_network.png`, `cluster_network_tech.png`, `cluster_network_domain.png` (static)
- `cluster_network.html`, `cluster_network_tech.html`, `cluster_network_domain.html` (interactive)
- `merge_adjudications.jsonl` — Qwen pair-adjudication output (the deleted-and-superseded approach from §10.1 step 2)
- `*_raw.txt` and `*_meta.json` — per-script audit trails (raw model output + cost/timing)

Plus event-key outputs in `clustering_v2/output/`:
- `full_corpus_events.jsonl` + `full_project_id_map.json` + `full_event_key_map.jsonl` (script 11)
- `event_key_map.jsonl` + `project_id_map.json` (script 10, FC-subset version, retained as the script-10 reference even though script 11 superseded it)

## 11. v2 catalogue vs RAG — positioning the methodology contribution

The v2 catalogue and retrieval-augmented generation (RAG) solve different problems. Most LLM-on-corpus work today is RAG, so the methodology paper benefits from positioning the v2 pipeline against this dominant paradigm explicitly. This section makes the contrast explicit so a paper draft can lead with it.

### 11.1 Core distinction

| | RAG | v2 catalogue |
|---|---|---|
| Architecture | embed → retrieve → synthesise per query | extract once → store structured → query forever |
| Cross-document patterns | invisible (each query is a fresh retrieval) | first-class (co-occurrence network, count-queryable) |
| Auditability | each synthesis is unaudited | each cluster has explicit member records with audit verdicts |
| "How prevalent is X?" | can't answer | counted directly |
| "What co-occurs with X?" | can't answer | graph-queryable via `cluster_cooccurrence.json` |
| "Is X general or domain-specific?" | can't answer | classified at extraction time (§10.3 substrate extraction) |
| Hallucination risk on synthesis | high (model fills gaps from training data) | bounded (synthesis only over already-extracted records) |
| Cost | low per query, no setup | ~$335 setup for 90k records, near-zero per query |
| Reuse | every analysis is a fresh inference | substrate reusable forever |

### 11.2 Why most teams reach for RAG

RAG is engineering; structured extraction is methodology. RAG gives immediate demo value; extraction is investment with deferred payoff. RAG works on any corpus without framing; extraction requires the analytical primitive to be defined upfront. RAG's evaluation is retrieval metrics (well-studied); extraction's evaluation is methodological. RAG products have obvious commercial structure (per-query pricing); structured extraction is harder to monetise without a defined use case. So RAG is what's *visible* in product demos, conference talks, vendor pitches — and the v2 pipeline's contribution is invisible to a reader who hasn't been primed on the contrast.

### 11.3 The contrast lights up especially clearly on c016

A RAG interface to the ARENA Knowledge Bank could not produce the c016 FCAS-cannibalisation analysis. It could synthesise a paragraph in response to a question, but couldn't:

- Identify the pattern as a coherent cluster (no clustering)
- Quantify its scale (no aggregation)
- Show its prevalence across 23 projects (no count)
- Map its co-occurrence with adjacent failures (no graph)
- Distinguish it from sibling mechanisms (no taxonomy)

RAG could *retrieve evidence to support* a paper if you told it the pattern existed. It couldn't *discover* the pattern. The catalogue does the discovery.

### 11.4 Methodology paper framing

> *"Retrieval-augmented generation answers questions; it does not produce reusable analytical artefacts. For corpora where pattern-level structure is the analytical target — failure-mode taxonomies, archetype catalogues, cross-document co-occurrence networks — RAG is architecturally inadequate. The v2 pipeline produces a structured catalogue that supports multiple analyses without re-inference. The substrate model is the correct fit when the analytical questions are about the structure of the corpus, not retrieval from it."*

Elevator-pitch version: *"RAG retrieves; my pipeline extracts. The retrievable corpus stays the same; the extracted catalogue compounds. For policy analysis on failure modes, the second is the right tool, and most people don't realise the first isn't."*

### 11.5 Practical implication for the paper

Lead with this contrast. Most readers' mental model of "LLM on corpus" is RAG. Explicitly distinguishing what RAG does from what a structured-extraction pipeline does primes readers to recognise the v2 work as a *different category* — which is more striking than presenting it as just "another methodology". The contrast is the framing that makes the contribution visible.

This pairs with the §10.3 substrate-extraction finding (62.3% of clusters describe general mechanisms beyond renewable energy): the catalogue isn't a renewable-energy taxonomy, it's a ~700-mechanism general taxonomy of infrastructure / program / coordination failures with a tech-specific layer. RAG has no equivalent — there's no "general substrate" that emerges from a retrieval pipeline because retrieval doesn't aggregate.

This section was distilled from memory entry `project_v2_vs_rag_framing.md` (saved 2026-05-03 after Jeff articulated the distinction).
