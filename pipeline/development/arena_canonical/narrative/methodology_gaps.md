# Methodology Gaps — Outstanding Work Bridging Pragmatic to Research-Grade

**Status:** locked 2026-05-01, with §15 retraction sharpened and §16, §17 added 2026-05-02. Maintained intentionally as a research roadmap.

> **Classification banner (added 2026-05-04 during the legacy/canonical split).** This document was written *across the boundary* between the legacy v3p5 pipeline and canonical-pipeline development. Most of §1-15 was written 2026-05-01 (the same day as the navigator's last update); §16-17 were added 2026-05-02 alongside the canonical record-type tagging pilot. Each section below is tagged with one of three categories so a reader knows which pipeline it applies to:
>
> | Category | Sections | Meaning |
> |---|---|---|
> | **Legacy diagnostic** | §8a, §8b, §9, §11 | Findings about the v3p5 / 660-cluster legacy state. Don't apply to the canonical 1,141-cluster catalogue (or apply differently). |
> | **Canonical** | §5, §13, §14, §17 | Architectural ideas that *became* the canonical pipeline (per-doc grouping, 6-axis Opus 4.6 labelling, ANAO v2 testbed) or that validate canonical decisions (the Sonnet-vs-Opus mechanism finding). |
> | **Bridging** | Purpose + §1, §2, §3, §4, §6, §7, §10, §12, §15, §16 | Apply to either pipeline, or framing-level. §15's retraction in particular is the architectural justification for both pipelines sharing the v1 grave extraction. |
>
> Each section header below has a `[Category]` tag. See `corpora/arena/PIPELINES.md` for cross-pipeline framing.

## Purpose of this document
**[Bridging]**


The pipeline produces a defensible artefact when measured against the §8 pragmatic counterfactual (a portfolio manager reading 1,440 documents personally would not produce a structured cross-corpus failure-mode taxonomy with traceable citations). It does not yet produce a research-grade artefact under the standards required for an academic methodology paper.

The gap between *pragmatic-tool-in-comparison-to-counterfactual* and *research-grade-tool-with-well-defined-epistemology* is **enumerable, prioritisable, and tractable**. This document enumerates it.

The framing is deliberate. A grey paper or research-engagement proposal that names its gaps and shows the path to closing them is structurally stronger than one that pretends to fill them. Each gap below is a publishable extension; together they form the Broad Learnings research programme.

---

## How each gap is described
**[Bridging]**


For every entry:
- **What we built** — the pragmatic claim defensible today
- **What research-grade would require** — the formal extension
- **Effort** — researcher-weeks, hand-tag count, API spend
- **Dependencies** — what other gap or capability must close first
- **Status** — `open` / `parked` / `in-progress`
- **Anchor** — section of `methodology_notes.md` or related artefact

---

## 1. Per-filter reliability calibration against human ground truth
**[Bridging]** — applies to either pipeline's filter chain.


**Anchor:** §11

**What we built.** Each filter stage in the pipeline (Stage 1 causal recovery, Stage A valence + mechanism_named, Stage F cluster membership, Pass 2 parent assignment, Pass 3 realisation) emits a per-record label. Some have rough reliability estimates from incidental calibration; others have none. The §11 efficiency-chain framing computes a joint reliability across stages, but several `r_i` are placeholders.

**What research-grade would require.** A hand-tagged sample of ~100 records per filter where reliability is currently uncalibrated, with inter-rater agreement (Cohen's kappa or equivalent) measured against at least one second human rater. Specifically:
- Pass 3 realisation classifier (realised / mixed / anticipated / generic) — currently estimated, not measured
- Pass 2 parent assignment — only Sonnet self-rated confidence, no human ground truth
- Stage F cluster membership — Opus audit gives LLM-vs-LLM agreement, not human ground truth

**Concrete worked-example evidence motivating this gap (added 2026-05-01):**

The NT Solar Energy Transformation Program event (`ARENA-DLV-0728-0019`, 5 records) shows the realisation classifier giving inconsistent verdicts on **near-identical text**. Three NT SETuP performance reports each restate the seasonal-curtailment finding in essentially the same words; Haiku tagged Performance Report 3's record as `realised` but Performance Reports 1, 2, 4 as `generic`. The differentiating phrasing is small (one report says "a significant driver of curtailment", another "system load varies more..."). This is the kind of inter-record inconsistency that hand-tagging would surface as classifier instability — and it's currently invisible at the population statistics level.

**Effort.** ~300 hand-tags total (100 per filter), spread across one rater plus a second-rater overlap of ~30 records per filter for IRR. Roughly 2–3 researcher-days. No API spend.

**Dependencies.** None. Can run today.

**Status.** Open. Highest leverage of any item on this list because it directly populates the §11 traceable-uncertainty framing that the methodology paper rests on.

---

## 2. Stratum A recall validation (independent of retrieval method)
**[Bridging]** — recall question applies to either pipeline.


**Anchor:** todo.md ("Build a recall-validation sample independent of the retrieval method"); descoped from v1 critical path under the §8 pragmatic execution stance.

**What we built.** The pipeline measures *what it found*. The Opus audit measures whether *what it found* is correctly grouped. Neither measures whether the pipeline *missed material it should have caught*.

**What research-grade would require.** A uniform-random sample (~30 records) drawn from the full corpus *independent of the keyword regex and embedding retrieval*, hand-tagged for whether each record contains author-stated causation under the locked epistemic position. Compute pipeline recall as `(Stratum A causal records caught by pipeline) / (Stratum A causal records hand-tagged)`. Plus a negative-sampling stratum (~30 records sampled from records the pipeline did *not* flag, weighted toward low-cosine zones) to find connectives the retriever is currently missing.

Plus optional source-document reading on 3–5 documents (read full markdown, hand-mark every sentence with author-stated causation, check both extraction recall and retrieval recall).

**Effort.** ~60–100 hand-tags + 3–5 source-doc reads. Roughly 1 researcher-week.

**Dependencies.** None.

**Status.** Open. Currently the strongest known epistemic gap. Without it, the methodology paper can defend "these patterns exist in the corpus" but not "these are the dominant patterns".

**Concrete recall-miss evidence found 2026-05-01.** The Wallbox Quasar event (`ARENA-DLV-1348-0029`, 6 records) included the record `ARENA-DLV-0844-0019`:

> *"Prior to REVS there were no V2G capable chargers with AS/NZS 4777 compliance, **therefore** the decision was made to certify the Wallbox Quasar charger."*

This is an unambiguous author-stated causal claim using the word *therefore* — and the Stage 1 keyword regex missed it. The embedding-cosine fallback (top 5%) also failed to surface it. So even before Haiku was invoked at Stage 4, this record had been silently dropped from the candidate pool.

Two implications:
1. **"therefore" should be added to the connective regex.** Quick fix, plugs one named recall hole. ~30 minutes of work + replay against the existing record corpus.
2. **More importantly, this is a Stratum-A-style miss that the *event-axis retrieval* (Phase B navigator) would have recovered as a context record** — see gap #10. Worth flagging as a worked example of why Stratum A matters: this record contains a strong causal claim, was missed by the upstream retriever, but is recoverable via the event-context view of the v3.5 cluster that does mention it.

The existence of even one such miss (found incidentally, not via a Stratum A campaign) suggests the recall floor is meaningfully lower than 100%. A Stratum A campaign would quantify it.

---

## 3. Multi-axis tagging architecture
**[Bridging]** — partly closed by canonical's 6-axis labelling pass (§14 implementation); the multi-axis framing here is general.


**Anchor:** discussion 2026-04-30 / 05-01; note in todo.md

**What we built.** Single-cluster membership: each record belongs to exactly one cluster, exactly one parent, exactly one theme. Multi-mechanism records (~15–20% of the corpus per Sonnet's Pass-1 notes) are placed by primary mechanism, losing information about secondary mechanisms.

**What research-grade would require.** Decompose cluster labels into orthogonal axes (resource at issue / defect type / interface-locus / mechanism layer / stakeholder bearing the failure / outcome class) and tag each record on every axis independently. Synthesis becomes filter-and-compose rather than fixed-cluster retrieval. Validation: per-axis IRR, axis-correlation analysis to test orthogonality, and comparison with current single-membership taxonomy on representative queries.

**Effort.** Per-axis design (1–2 researcher-weeks) + ~50,000 LLM calls for tagging (8,311 records × 6 axes, batch + cache, ~$15) + audit (~$22 Opus) + analysis (1 researcher-week).

**Dependencies.** Independent-axis design discipline (memory: feedback_axis_independence.md) — failure to enforce it produces taxonomies collapsing to the diagonal.

**Status.** Parked. Methodology-paper-grade artefact, but a different artefact, not a fix to the current single-membership taxonomy.

---

## 4. Positive-valence symmetry test
**[Bridging]** — forward-looking; would test whether either pipeline's filter generalises beyond negative valence.


**Anchor:** discussion 2026-05-01

**What we built.** Failure-mode taxonomy derived from negative-valence + mechanism-named records (8,311 of 22,517 YES-causal records).

**What research-grade would require.** Run the same Stages B–F + parent-derivation + audit pipeline on the positive-valence + mechanism-named subset. Compare cluster-coherence rates, parent structures, and per-cluster Opus audit fit_pct between the two valences. Tests whether the architecture generalises across valence (i.e., whether the pipeline is finding *causal mechanism patterns* or *failure-specific language patterns*).

**Effort.** Stages B–F: ~$30 (matches the negative-valence run cost). Audit: ~$22 sync, ~$11 batch. Total: ~$50–60 + analysis (~1 researcher-week).

**Dependencies.** None. Stage A has already classified all 22,517 records.

**Status.** Open. Strongest controlled experiment available — same architecture on opposite valence, same corpus, no domain-language or document-genre confounds. Likely a more rigorous generalisation proof than cross-corpus (see #5 below).

---

## 5. Cross-corpus generalisation — ANAO as v2-architecture testbed
**[Canonical]** — ANAO is framed as the first deployment of the v2 architecture (canonical's per-doc grouping + 6-axis labelling), not a retrofit of legacy.


**Note added 2026-05-01:** ANAO is now framed as the **first deployment of the v2 extraction architecture** (combined §13 chronological event-identity + §14 bundled per-record axis tagging), not as a retrofit of the v1 pipeline applied to ARENA. The methodology paper's structure benefits: ARENA = v1 demonstration corpus; ANAO = v2 corrected-design corpus. The two-architecture comparison becomes part of the paper's contribution.



**Anchor:** memory: project_anao_corpus.md, project_pipeline_status.md; CLAUDE.md engine/config separation

**What we built.** Engine/config architectural separation enforced at the codebase level (everything under `pipeline/` is corpus-agnostic; per-corpus customisation lives in `domains/<name>/` and `corpora/<name>/`). Pipeline has been demonstrated on one corpus (ARENA) only, using the v1 architecture (per-document atomic extraction → post-hoc dedup → separate Stage 2/A/6 calls → clustering → parents).

**Deployment plan with v2 architecture (locked 2026-05-01).**

1. **Pilot:** Run §13 + §14 v2 extraction on 5–10 ANAO performance audit reports (one or two report years' worth). Hand-tag 20 records as ground truth. Validate the bundled-schema prompt design and the chronological event-identity passing. ~$5 + 1 researcher-day.

2. **Ground-truth calibration:** Use the pilot's hand-tags to compute initial reliability estimates per axis (causal_claim, valence, mechanism_named, realisation, plus the new stakeholder/interface/outcome axes). Populates the §11 efficiency-chain reliability table for ANAO directly. ~half a day.

3. **Full ANAO extraction:** Re-run on all 1,452 audit reports with v2 architecture. Cost ~$120-200 batch / ~$200-350 sync. Wall ~1-2 weeks counting orchestration. The structural parser output (`corpora/anao/scripts/03_parse_structure.py`, 32,617 summary paragraphs across 1,086 files) is the natural input.

4. **Clustering + parent derivation on ANAO:** Apply the same Stages C-F + parent derivation + audit pipeline used on ARENA. ~$50-80 incremental.

5. **v1 vs v2 comparison:** Run the v3.5 ARENA records through a one-time bundled re-tagging on the bundled-schema axes (without re-extracting), so ARENA can be reported with the same axis taxonomy as ANAO. Optional but useful for the paper's apples-to-apples comparison. ~$30-50.

**Total v2-deployment-via-ANAO cost: ~$250-400 + 2-4 researcher-weeks.**

**What research-grade would require.** Run the full v2 pipeline on at least one second corpus (ANAO is the prepared candidate). Demonstrate that the v2-architecture extraction (chronological event-identity + bundled axis tagging) produces a coherent taxonomy on different document genres, vocabulary, and authoring conventions. Compare per-cluster fit_pct distributions, parent-coverage, and per-axis label distributions between corpora.

**Dependencies.** ANAO structural parser output (already exists: 32,617 summary paragraphs from 1,086 files). Markdown reconvert (queued but not run).

**Status.** Open. Best framed as the **first major research deliverable** AND **the first deployment of the v2 architecture**. Doing both via the same workstream is structurally efficient: one extraction run produces the cross-corpus generalisation evidence and the v2-architecture validation.

---

## 6. Within-document failure-mode synthesis
**[Bridging]** — forward-looking; would relax the §7 epistemic position. Applies to either pipeline.


**Anchor:** §6 (atomicity-vs-mechanism tradeoff), §7 (locked epistemic position); methodology_notes.md notes a v2 within-doc clustering task was DROPPED 2026-04-30 under the locked position.

**What we built.** Records are atomic per the extraction. Failure-mode synthesis happens *across documents* via clustering on mechanism phrases. Mechanism content distributed across multiple atomic records *within a single document* (e.g., Middleback Ranges PHES section 10.3, where the failure mechanism is split across bullets 1–4 of one section) is *not* recombined; each atomic record clusters independently.

**What research-grade would require.** A within-document recombination stage. For each document, ask an LLM "which of these atomic records describe different aspects of the same underlying failure mechanism?". Output: within-document failure-mode groups. Compare to embedding-based clustering — does within-document grouping produce more cohesive parent failure modes than per-record clustering? The case for relaxing the locked epistemic position to permit within-document inference is itself a defensible research question with empirical handles.

**Effort.** Pilot on 5–10 documents to test the inference: ~$5. Full corpus: ~$50. Plus 1–2 researcher-weeks of analysis to compare the two synthesis approaches.

**Dependencies.** Conceptual decision on whether to relax the §7 locked position. Currently locked; the gap is *both* the experiment to relax it *and* the methodological argument for/against.

**Status.** Parked. Re-opens the strongest commitment in the methodology — the locked epistemic position — so the research argument has to come first.

---

## 7. Filter-error correlation analysis
**[Bridging]** — applies to §11 framing across either pipeline.


**Anchor:** §11

**What we built.** §11 computes joint filter reliability as the product `r_1 × r_2 × ... × r_N` under independence. Acknowledges that errors across filters can correlate (a hedged-language record is more likely to be tagged borderline-causal *and* anticipated-modality with above-chance joint probability).

**What research-grade would require.** On any hand-tagged sample (gap #1 or #2), measure correlation between filter errors empirically. Decide between:
- Retain the simple product as a defensible conservative envelope (acknowledged as such in the paper)
- Move to a conditional formula `r_joint = r_1 × P(filter 2 correct | filter 1 correct) × ...` if correlation is large enough to materially affect the lower bound

**Effort.** ~3 researcher-days. No new data collection beyond the hand-tags from #1 / #2.

**Dependencies.** Needs at least one hand-tagged sample (gap #1) to size correlation.

**Status.** Open. Cheap to do once hand-tagging exists. Probably moves the §11 framing from "defensible first-order envelope" to "empirically corrected joint reliability".

---

## 8a. Records-vs-events: dedup prompt's mechanism-coherent-events assumption is empirically violated
**[Legacy diagnostic]** — the 52% cluster-split rate is from the legacy v3p5 stage-4-plus-dedup architecture; this finding *motivated* the canonical rewrite (specifically informed §13). Canonical's per-doc grouping addresses this empirically.


**Anchor:** discussion 2026-05-01; commit `83bf20a` (post-hoc event counts); cluster-split diagnostic at `cluster_split_events.md`; the dedup prompt at `dedup_haiku/prompt_v2.md`

**What we built.** Stage 1 dedup operates on **occurrence identity** — the prompt explicitly defines an event as "a discrete, atomic occurrence". The prompt's design favours conservative-split: when uncertain, don't merge. The closing reassurance — *"the downstream archetype clustering layer will reconnect related events that share a failure mode"* — was an assumption that under-merging at dedup is safe because clustering will re-group cross-event records that share a mechanism.

Stages 2–6 of the failure-mode pipeline were built on the 90,192 raw extracted records, not on the 62,301 deduped events. The records-keyed pipeline produces a taxonomy directly; the deduped events were a parallel artefact.

**The assumption that's empirically violated.** The dedup prompt's design implicitly assumed *events would be mechanism-coherent* — i.e. once you merge records that describe the same occurrence, those records would share a failure mechanism, and so an event maps cleanly to a single failure-mode cluster.

The Phase B cluster-split diagnostic shows this is false: **52.1% of multi-record events have constituent records spanning ≥2 different failure-mode clusters under top-10 Stage F validation.** The reason is that the atomic-extraction layer (E3-grave) is finer-grained than occurrence identity. A single occurrence has multiple aspects (cause, consequence, lesson, mitigation, specification, design decision); atomic extraction emits each aspect as its own record; dedup groups these by occurrence; clustering then routes each aspect to its own mechanism cluster. **The records share an occurrence, not a mechanism.**

The original reassurance ("clustering will reconnect related events") was about cross-event consolidation that we haven't tested directly. The actual failure mode of the architecture is the opposite: clustering *breaks up* merged events along mechanism boundaries.

**What research-grade would require.** Three activities, in order of cost:

1. **Documentation correction (in progress).** Report both record and event counts at every pipeline stage. Phase B already produces parallel event-keyed jsonls alongside record-keyed jsonls. The 76_event_counts_by_stage.py analysis is the per-stage compression table. **Effort: complete in current pass.**

2. **Hand-audit the cluster-split sample.** The 20-row sample in `cluster_split_events.md` distinguishes legitimate multi-mechanism events (one occurrence with multiple aspects, each aspect a distinct mechanism — the architecture working under a corrected understanding) from pipeline inconsistency (different events wrongly merged, or same-mechanism records wrongly split). Without the audit, we don't know what fraction of the 52% is which. **Effort: ~half a researcher-day.**

3. **Mechanism-aware dedup (architectural fix).** Two paths:
   - **Path A — tighten dedup.** Add a constraint: only merge records that share mechanism content *as well as* occurrence. Records describing the cause vs the consequence of one occurrence become different events. Compression drops further (ratio likely ~1.02–1.05× from current 1.16×). The events that remain are mechanism-coherent.
   - **Path B — within-event re-splitting.** Take the existing event set; for any event whose member records span ≥2 clusters, break it into one event per cluster. Cheap to compute post-hoc with current data; reframes the existing dedup output rather than re-running.

   Either path produces an event set where the *event* is the natural unit for cluster-level reporting. **Effort: Path A ~$30 + 1 researcher-week to re-run dedup; Path B ~1 researcher-day to compute post-hoc.**

**Status.** Documentation correction landing now. Audit and mechanism-aware-dedup are open. The methodology paper should acknowledge the assumption-violation honestly: dedup was designed to under-merge with a safety reassurance that turns out not to apply in the way the designer intended.

**Refinement added 2026-05-01: same-parent vs cross-parent splits.** Cluster splits within a single dedup event are not all equivalent. Two distinguishable cases:

- **Same-parent split (near-miss adjacent):** event's records land in different clusters but those clusters share a parent. The mechanism family is preserved at the parent layer; only the fine-grained cluster axis fragments. Methodologically less concerning. *Worked example:* the NT SETuP seasonal-curtailment event has 4 records — three landed in *peak-period load and generation mismatch*, one landed in *Seasonal renewable output variance reduces operational capacity*. Both clusters live under parent *Generation-storage-offtake capacity mismatch*; the parent-axis still preserves the connection.
- **Cross-parent split:** event's records land in different parents (or different themes). The mechanism family fragments structurally. Methodologically more concerning. *Worked example:* the Wallbox Quasar event spans clusters under *Regulatory*, *Standards/interoperability*, *Vendor coordination*, and *Late discovery of requirements* — four distinct parents. The same occurrence speaks to four genuinely different mechanism families.

The 52% headline cluster-split rate should be broken down by parent-coincidence in the methodology paper. Same-parent splits are partial mechanism-coherence preservation; cross-parent splits are the genuine structural fragmentation. Likely ~half of the 52% is same-parent (preliminary observation; needs computation as a small follow-on).

---

## 8b. Canonical record may not represent all event content
**[Legacy diagnostic]** — about the legacy stage-1 dedup's seed-record selection. "Canonical" in the section title here means *canonical-record-of-an-event* (the seed), not the canonical pipeline.


**Anchor:** discussion 2026-05-01; methodology_notes.md §6 (atomicity-vs-mechanism tradeoff)

**What we built.** Stage 1 dedup defines an event by selecting the **richest** constituent record as the seed/canonical, with non-seed records attached as corroborators. The seed's content (mechanism phrase, narrative, lesson, evidence) becomes the event's representative content; corroborator-specific content is preserved in the per-project file but is **not** carried forward as the event's primary representation.

**What research-grade would require.** A test of the assumption that the seed record covers the event's content. For a sample of multi-record events, hand-read every constituent record and compare:

1. Does the seed's mechanism_phrase capture the mechanism content of all corroborators, or do corroborators add aspects the seed doesn't mention?
2. When carrying forward the event into downstream stages (clustering, parent assignment, realisation), would using the union/aggregate of constituent records' content produce a different placement than using the seed alone?
3. For event-keyed datasets (Phase B), should free-text fields be `seed_record_value` (current plan) or `concatenated_member_values` (alternative) — and how does that change the embedded-similarity computations downstream?

This is the structural question Phase B's per-event aggregation rules address only partially. The plan currently uses seed-record values for free-text fields and preserves member values in `member_<field>` lists; the *primary* representation remains seed-only.

**Effort.** Hand-read 30 multi-record events: ~3 researcher-days. Plus optional re-run of Stages C–F using concatenated event content: ~$15 + ~3 days.

**Dependencies.** Phase B event-keyed datasets (provides the substrate for the analysis). Best done after the folder split lands.

**Status.** Open. Cheap to investigate as a sub-task of #8a's deeper re-run.

---

## 9. Live joint-reliability readout in the navigator
**[Legacy]** — explicitly references the legacy navigator's `cluster_audit_summary.json` and the legacy stage-5 fit_pct values. The canonical pipeline does not currently have a navigator UI.


**Anchor:** §11; navigator implementation in `72_build_navigator.py`

**What we built.** Navigator surfaces per-filter selections, cluster fit_pct from the Opus audit lives in `cluster_audit_summary.json`, and the §11 framing describes a joint-reliability calculation. None of these are wired together in the live UI — the data exists, the computation exists, the user just doesn't see it as they stack filters.

**What research-grade would require.** Wire the per-filter reliability values (point estimates from §11 table) into the navigator JS. As the user adds filters, compute and display the running joint reliability. For cluster filtering, use the cluster-specific fit_pct rather than the global median. Update on every filter change.

**Effort.** ~half a researcher-day. No API spend, no data collection. Pure JS implementation.

**Dependencies.** Reliability point estimates from gap #1 (or proceed with §11 placeholders and tighten them as #1 lands).

**Status.** Open. Highest-impact-per-effort item on the list. Demonstrates the §11 epistemological position concretely instead of describing it abstractly. A reviewer reading the paper alongside the navigator sees the framing in action.

---

## 10. Two-axis retrieval architecture (mechanism axis + occurrence axis) — methodology paper claim
**[Bridging]** — describes both pipelines' outputs as orthogonal retrieval substrates. The framing originated in the legacy navigator (event view alongside cluster view) but is the canonical paper's spine claim.


**Anchor:** event-view in `failure_mode_navigator/cluster_navigator.html` (rebuilt 2026-05-01); `stories.md`; `cluster_story_depth.json`

**What we built.** Dedup output and failure-mode taxonomy were originally treated as a single linear pipeline. As of 2026-05-01, the navigator exposes them as **two independent retrieval axes** over the same source extraction:

- **Mechanism axis (clusters):** *"Show me records about cost-prohibitive storage."* Cross-project pattern retrieval. Filters by failure-mode mechanism class. What Stage 4-5-6 produced.
- **Occurrence axis (events):** *"Show me everything connected to the Wallbox Quasar certification on REVS."* Single-occurrence narrative reconstruction. Filters by what happened. What Stage 1 produced.

These are orthogonal. A cluster is a mechanism family; an event is an occurrence with multiple aspects. A cluster member's event neighbours are typically other aspects of the same occurrence — cause, lesson, outcome, decision — that may belong to different clusters. The navigator's record-detail pane now shows the event-context section listing siblings with their cluster assignments.

**Why this is a methodology-paper claim, not just a UI feature.** The pipeline produces two independently meaningful retrieval substrates from one extraction. Most synthesis tools offer one. The two-axis claim is *structurally* harder than the taxonomy claim alone — it argues that the architecture is queryable from multiple legitimate angles, with provenance preserved on each. Reviewers asking "does the pipeline support cross-document narrative reconstruction?" can be answered concretely; reviewers asking "does the pipeline support cross-project mechanism retrieval?" can be answered concretely; both with the same artefact.

**What research-grade would require.** Three things, all currently open:

1. **Article the claim in the methodology paper.** Currently the paper draft (not yet written) emphasises taxonomy. The two-axis claim is the stronger architectural finding and should be the paper's spine. Effort: writing.

2. **Quantify the recall recovery via event-axis.** For records dropped at Stage 2 or Stage A but recoverable as event-context (1,299 such records embedded in the navigator), how many describe failure-mode-relevant content? A small audit (~30 records hand-tagged) would give the rate at which event-axis retrieves what mechanism-axis missed. Combined with gap #2 (Stratum A), this gives a full recall picture: *"Mechanism-axis recall = X%; mechanism+event combined recall = Y%."* Effort: ~half a researcher-day.

3. **Wire event metadata into reliability calculations.** §11's joint-reliability framing currently treats each filter independently. Event-axis retrieval has its own reliability profile (dedup precision = high; dedup recall = unmeasured but bounded by within-project scope). The paper should report event-axis reliability separately, not absorbed into the filter chain. Effort: ~1 day analysis.

**Status.** Architecture is built; claim is unarticulated. Highest-leverage move for the methodology paper.

---

## 11. Per-cluster story-depth as a quality dimension complementary to fit_pct
**[Legacy]** — refers to `cluster_story_depth.json` from the legacy stage-5 audit. Not yet computed for the canonical 1,141-cluster catalogue.


**Anchor:** `cluster_story_depth.json`; `78_cluster_story_depth.py` (added 2026-05-01)

**What we built.** Stage 5's Opus audit gives per-cluster `fit_pct` — the rate at which member records' mechanism phrases legitimately match the cluster's stated mechanism. Story-depth is an independent quality dimension: the rate at which member records have surrounding event-context recoverable via the dedup mapping.

```
median story_depth_pct: 20%
≥50% deep:  77 clusters (12%)  — every member has substantial surrounding context
20-49%:    279 clusters (42%)
<20%:      304 clusters (46%) — thin clusters; members are mostly singleton observations
```

A cluster with high `fit_pct` and low `story_depth_pct` is "well-described but thinly evidenced" — the records that are in it really do fit, but each is a one-shot observation without surrounding narrative. A cluster with high `fit_pct` *and* high `story_depth_pct` is the strongest evidence — coherent mechanism membership and rich narrative substrate available for grey-paper citation.

**What research-grade would require.**

- **Report story-depth alongside fit_pct in cluster cards.** Two independent quality scores, both visible. Allows the methodology paper to distinguish "the technique correctly identified this pattern" (fit_pct) from "the corpus has rich evidence for this pattern" (story_depth). Effort: ~half a researcher-day to wire into the navigator.
- **Integrate into the joint-reliability calculation (§11).** Story-depth functions as an evidence-strength multiplier on top of label-reliability. Effort: research design + ~1 day implementation.
- **Surface in the methodology paper as a complementary quality dimension.** The strongest claims should be backed by clusters with both high fit and high story-depth; weaker claims (or claims warranting hedging) by either-but-not-both. Effort: writing.

**Status.** Metric computed and stored; not yet exposed in navigator UI; not yet woven into §11 reliability or paper draft.

---

## 12. Narrative-depth asymmetry — selectivity is in the dedup grouping, not in extraction
**[Bridging]** — extraction-level concern; both pipelines share the v1 grave extraction so the "primary sources have more depth than reconstructions" finding applies equally to canonical's per-doc-grouping events and legacy's stage-1 dedup events.


**Anchor:** comparison of v3.5 event-axis reconstructions to original markdown for AGL Nyngan (commit 0cf0f4e) and REVS / Wallbox Quasar (this conversation, 2026-05-01); detailed extraction trace 2026-05-01.

**Initial framing (incorrect, retained for honesty).** I had initially framed this gap as "the pipeline summarises away engineering depth that the primary sources contain". Detailed accountability tracing showed this framing was wrong. **The extraction prompt is fully accountable; the apparent narrative-depth loss is downstream and locatable.**

**Trace of accountability per pipeline stage.** Comparing source-document content against actually-extracted records for REVS Lessons Learnt 2 (`doc_1347`):

- **Extraction.** The prompt at `pipeline/prompts/extract.md` says *"Extract every discrete finding or insight the document warrants. There is no upper limit — do not stop early... If a dense document warrants 30 records, extract 30."* LL2 (~13 pages) yielded **32 records**. Every technical detail I had claimed was "missing" is in fact present: earthing-vs-rubber-tyres root cause (`1347-0003`), ferrite inductors fix (`1347-0005`), 16.67%-ramp-rate clauses (`1347-0015`), AEMO MASS conflict and two resolution pathways (`1347-0016, 0017, 0018, 0019`), 40 PAJ tests at DERlab (`1347-0024–0026`), CEC AS/NZS 5139 cascade (`1347-0028–0030`).

- **Dedup.** The prompt at `dedup_haiku/prompt_v2.md` says: *"OCCURRENCE vs derived LESSON/PRINCIPLE — different events"; "TECHNICAL MECHANISM vs STRATEGIC OUTCOME — different events"; "Different RECOMMENDATIONS or design decisions on the same subsystem — typically distinct events"; "When in doubt, split."* Dedup correctly applied these rules: it grouped 6 records as "the broad certification difficulty event" and *correctly split* the earthing-finding, EMC-fix, ramp-rate-conflict, PAJ-test-finding, and CEC-classification records into *separate events*. Each is a discrete sub-finding under the prompt's definitions.

- **Cluster.** Failure-mode clustering then routes each separate event's records by mechanism similarity. The earthing record clusters under standards-lag; the ramp-rate records under control-incompatibility; the PAJ records under sensing/measurement-gap; the CEC records under regulatory-cascade. **By design.**

**The actual finding.** What "felt missing" from the 6-record event reconstruction was not selectivity at extraction. It was **the consequence of correct prompt-following at every stage applied to a finer-grained input than the project-scale narrative requires**. Each sub-aspect of REVS's certification experience became its own dedup event, then its own cluster member. To recover the project-scale narrative, the user must either:

1. Read the source document directly (which is what the LL2 author wrote it for).
2. View *all dedup events for the project* — a project-axis retrieval not currently exposed in the navigator.
3. Read the cluster-axis index of records *filtered to one project* — the navigator's tech-category filter approximates this for tech-domain queries but doesn't operate at project granularity.

**Worked evidence in support of the initial AGL Nyngan asymmetry observation.** Some content is genuinely missing from extracted records on AGL Nyngan — Canola-oil-vs-Dustex dust suppression trial, the substation-bench drainage rationale, the access-road elevation design change, the Broken-Hill knowledge transfer. These weren't extracted. Whether the omission is prompt-accountable would require an equivalent record-by-record comparison on `doc_0220` (150 records — too large to enumerate inline here). **Likely the extractor got most of these and I missed them in the inline check; the per-doc record list shows AGL Nyngan generated 150 records for a 193-page report, density ~0.78 records per page, comparable to LL2 (~2.5 per page) and Crossing Sectors (~2.5 per page), suggesting the extraction floor was high.**

**What research-grade would require — corrected version.**

The correction sharpens what the methodology paper should claim:

1. **Extraction is prompt-accountable.** Every record's content traces to *what the prompt asked for*. We can defend the extraction's selectivity by pointing to the prompt's "what to extract" / "what NOT to extract" clauses. **The pipeline is not in the epistemically weak position of "the LLM made arbitrary content-selection decisions we can't explain"**. It's in the strong position of "the LLM followed a written prompt; the prompt says what we asked for; the records are what the prompt asked the model to extract".

2. **Dedup is also prompt-accountable.** Records grouped or split per the dedup prompt's stated criteria. The 52% cluster-split rate (§8a) is partly the consequence of dedup's deliberate atomicity — different sub-aspects of one occurrence become different events.

3. **Cluster assignment via Stage F is prompt-accountable.** Each record's cluster placement traces to the Haiku top-10 verdict prompt.

4. **Project-axis retrieval is the missing capability**, not narrative-depth recovery. The navigator currently exposes mechanism axis (clusters) and occurrence axis (events). Adding a **project axis** — *show me all events for project X* — would give the user the project-scale narrative reconstruction the source document provides. This is half a researcher-day to wire up and probably the single most useful navigator addition.

**Effort.**
- Documentation (lock corrected framing in paper): ~half a researcher-day.
- Add project-axis retrieval to navigator: ~half a researcher-day.
- Per-record extraction-accountability trace on the 1,448-document corpus (random-sample QA): ~1 researcher-week. *Not* needed before paper draft — the qualitative trace on REVS LL2 above is sufficient existence proof of accountability; the corpus-wide quantitative version is gap-#13 territory.

**Status.** Open. Initial framing was wrong; corrected here. The corrected finding is structurally stronger for the paper: extraction selectivity is not arbitrary, it's prompt-accountable, and we can defend it.

**Worked evidence — AGL Nyngan Final Report contained but pipeline did not capture:**
- Engineering decision: original access road was planned at existing ground level; rain risk forced the team to *raise the road elevation*.
- Operational detail: dust suppression trials of *Canola oil and Dustex* (longer-lasting but less cost-effective than water).
- Hydrology rationale: substation built on a *raised bench* specifically for drainage protection.
- Photo evidence (before/after rain) of the original access road.
- Forward-looking knowledge transfer to the Broken Hill project ("heightened sense of urgency for access road construction").

**Worked evidence — REVS Lessons Learnt 2 + Crossing Sectors Report contained but pipeline did not capture:**
- The *root cause* of the AS/NZS 4777 certification difficulty: the standard categorises bidirectional chargers as multi-mode inverters connected to a *stationary battery* presumed to provide an earthing point; EVs sit on insulating rubber tyres so they don't.
- The specific physical fix: *external ferrite inductors* added on input and output of the charger after EMC test failure post-earthing modification.
- A separate technical conflict: AS/NZS 4777's 16.67%-per-minute ramp rate (6 minutes to full power) directly conflicts with FCAS sub-6-second response requirements; firmware adjustment to satisfy AEMO would void cert.
- 40 phase-angle-jump tests at ANU's DERlab characterising charger ride-through behaviour, finding ambiguity in the standard's PAJ test specification.
- Six concrete standards-reform recommendations from the REVS team, with offers to contribute to standard drafting.
- The downstream regulatory chain: AS/NZS 4777 cert blocks → CEC compliance requires AS/NZS 5139 → impossible for vehicle-mounted batteries → blocks live FCAS market entry. Three regulatory frames in interaction, none of which our reconstruction surfaced.

**What research-grade would require.** The fix is not engineering — it is *correctly sizing the methodology paper's claim*:

> *"The pipeline provides cross-corpus mechanism retrieval and traceable evidence indexing over 90,192 atomic insights extracted from 1,448 documents. It is not a substitute for reading any individual project's authored documents. Where a project produced a comprehensive primary source — final report, technical lessons-learnt, or synthesis report — that document remains the richer narrative source on the project itself. The pipeline's role is to make that source findable when the user does not yet know which project to read, and to surface patterns that no single project's report would observe."*

This is a *stronger* and more defensible claim than "we reconstruct rich narratives". It positions the pipeline correctly: a horizontal tool (retrieval, pattern matching, evidence indexing across the corpus) that complements rather than substitutes vertical depth (close reading of primary sources).

**The asymmetry is genre-dependent.** AGL Nyngan produced one comprehensive Final Report — single-source close reading is possible. REVS produced 12 separate reports each focused on a single aspect — cross-document reconstruction *does* add narrative value because no single REVS document covers the full certification arc. Both still have the same asymmetry: primary sources, individually or in combination, have more engineering depth than the event-axis reconstruction.

**Effort.** Writing-only update to the methodology paper's framing and the navigator's "About" copy. ~half a researcher-day to articulate the claim sizing across the paper, README, and any user-facing copy.

**Status.** Open. The methodology paper has not been written; this is the framing that should be locked in *before* drafting, not retrofitted. Should be paired with §10 (two-axis retrieval architecture as paper claim).

**Implication for paper structure.** The paper should distinguish three quality dimensions of pipeline output explicitly:

1. **Cross-corpus retrieval value** — high. The pipeline scales to 1,448 documents; close reading does not. This is the strongest claim and the one the paper should lead with.
2. **Cross-document narrative reconstruction value** — moderate, genre-dependent. Strong for projects that produce only piecewise reports (REVS); weak for projects with a comprehensive Final Report (AGL Nyngan).
3. **Within-document narrative depth value** — *negative* relative to the primary source. The pipeline summarises away engineering, operational, and reasoning detail that the primary source contains.

Naming all three honestly is what makes the methodology defensible. Hiding (3) under marketing-style framing of (1) and (2) is the failure mode the paper should avoid.

---

## 13. V2 extraction with chronological event-identity assignment
**[Canonical]** — this section's architectural idea *became* canonical's `pipeline/group_events.py` per-doc grouping. The actual canonical implementation runs *post-extraction* (not at-extraction-time as proposed here) because the runs/README.md synthesis showed decoupled grouping outperforms extraction-time grouping. Read this section as the design proposal that informed the canonical decision; read `canonical/narrative/runs_synthesis.md` for what was actually built.


**Anchor:** discussion 2026-05-01 following §12 trace; current extraction prompt at `pipeline/prompts/extract.md`; current dedup prompt at `dedup_haiku/prompt_v2.md`; corpus_run/ output (62,301 events from 72,235 records).

**What we built.** Two-stage architecture: (1) per-document extraction via `pipeline/prompts/extract.md` produces atomic insight records, each independent. (2) Post-hoc within-project dedup via `20_pipeline_v2.py` surfaces same-event pairs by cosine + Haiku ratification, then groups them under canonical event IDs. This is the architecture that produced 90,192 records and 62,301 events on the ARENA corpus.

**Why the user proposed an alternative.** Examined how current dedup handles record sameness vs aspect-distinction (§8a, §12). Findings:
- The current dedup correctly splits aspect-distinct records under one occurrence (extraction → records of cause, intervention, outcome; dedup splits these as separate events). This is by prompt design.
- The dedup retrieval is cosine-bounded — same-event pairs that don't surface in the cosine top-N never get evaluated by Haiku. Recall is unmeasured.
- Event identity is reverse-derived from records, not first-class in the extraction output. Records carry no event identifier at extraction time.

**What research-grade would require: chronological event-identity extraction.** Process documents per project, sorted by `publish_date` ascending. For each document, the LLM receives:
- The document's content (as today)
- A list of *events already established* from earlier documents on the same project — each with `event_id`, canonical name, 1-2 sentence description, and exemplar mechanism phrase

Each extracted record carries an `event_id`. The LLM either:
- Assigns the record to an existing event by id (if it describes the same singular occurrence as a record already in that event), or
- Declares a new event with a new name + description (if no existing event fits)

Subsequent documents see the now-extended event list and continue the pattern.

**Why this is structurally better than current dedup.**

1. **Mechanism-aware dedup at extraction time.** The LLM sees full new-record content and full prior-event content together. It can decide sameness on actual semantic grounds rather than embedding-similarity proxies. Directly addresses §8a's mechanism-coherence assumption issue.

2. **Chronological accretion matches the documentation reality.** Early reports define event identities; later reports extend them. Mirrors how the consortium itself thought about the project as it evolved.

3. **Eliminates a full pipeline stage.** Post-hoc dedup goes away. Fewer prompt-accountability layers. Fewer artefacts to maintain. The 52% cluster-split rate (§8a) likely drops substantially because events are mechanism-cohesive by construction.

4. **Event identity becomes primary, not derived.** Currently `event_id` is reverse-derived from records via cosine + Haiku in a separate stage. In v2, `event_id` is part of the extraction output schema. Cleaner ontology.

5. **Event names become semantic anchors.** Stable event names across documents could anchor downstream cluster labelling, possibly improving cluster coherence — the event name is implicitly a higher-level abstraction than any single record's mechanism phrase.

**Concrete design considerations to lock before re-extraction.**

1. **Event-list prompt budget.** REVS has 834 events at project maturity. Passing all events to every subsequent extraction is expensive and pushes context-window limits. Mitigations: (a) cap at the N most-relevant events using lightweight similarity to the new document's title/abstract, surfacing 50-100 events; (b) prompt caching on the project context (lead org, project metadata, prior events list) — stable across multiple extractions on the same project, amortise across documents.

2. **Event-name stability.** Without constraint, the LLM may call the same event "AS/NZS 4777 cert difficulty" in doc 1 and "AS/NZS 4777 certification process" in doc 2. Two enforcement options: (a) require the LLM to either use a verbatim existing event name or declare a new one (JSON schema with strict enum-or-new pattern); (b) post-extraction audit pass that string-matches similar names within-project and consolidates.

3. **First-encounter prototype problem.** The first document on a project defines the canonical event names. If the first document's framing is poor (too narrow / too broad / vocabulary-idiosyncratic), all subsequent assignments inherit that framing. Mitigations: (a) emit events at a deliberately granular level on first-doc extraction so subsequent docs can consolidate up rather than splinter down; (b) allow an explicit "this is the same event as event X but framed differently" annotation that triggers a post-pass merge.

4. **Cross-document genuine-misses.** If the LLM doesn't recognise that doc-3's record describes the same event as doc-1's established event (vocabulary drift, focus shift), it creates a duplicate event. Symptom is the same as current dedup misses, but harder to detect after the fact. Safety net: a post-extraction within-project event-dedup pass that string-matches and embedding-matches event names, flagging candidate duplicates for human or LLM review. Cheap.

5. **Document-order bias.** Sorting by `publish_date` is the natural choice but has an edge case: documents published months apart may describe the same occurrence with different vocabulary because the author's understanding evolved. The model needs to recognise *occurrence sameness despite vocabulary evolution*. Including an exemplar mechanism phrase in the event description (rather than just a name) helps with this. Don't rely on name-matching alone for assignment.

6. **Records that span multiple events.** Some records legitimately describe a *transition* between two events (e.g. a record about "the certification difficulty *led to* the FCAS market exclusion" describes both the cert event and the market-exclusion event). Schema should allow `event_ids: [list]` rather than a single id.

**Cost / effort.**
- Re-running extraction on 1,448 ARENA documents: ~$200–300 sync (similar magnitude to the original extraction).
- With Batches API + 1h prompt cache on project context: **~$60–80 batch / ~$100–150 sync**.
- Pre-deployment pilot (one project, 5-10 docs) to test the prompt and surface design issues: ~$5 + 1 researcher-day.
- Full re-extraction: ~$80 + 1-2 weeks of orchestration / monitoring.

**Dependencies.** No external blockers. Could be the v2 extraction architecture for ANAO (gap #5) immediately, since ANAO extraction hasn't run yet — using the new architecture from the start avoids the post-hoc dedup retrofit.

**Status.** Open. Best framed as the **v2 corpus extraction architecture**, applicable to a re-run of ARENA OR as the first deployment for ANAO/cross-corpus generalisation. The clean way to land it is: pilot on one ARENA project (5-10 docs) → review event-quality → run full ANAO extraction with v2 architecture → eventual ARENA re-extraction if the v2 approach proves stronger. The pilot is the gate.

**Implication for §8a, §12, and the methodology paper.** §8a (records-vs-events) and §12 (selectivity in dedup grouping) both partially dissolve under this architecture — events become first-class, mechanism-cohesive by construction, and prompt-accountable at the moment of extraction. The cluster-split rate would drop. The "narrative-depth via project axis" framing in §12 might still apply, but the event-axis would carry meaningfully richer narrative coherence per event. The methodology paper would then have a v1 architecture (current) and a v2 architecture (chronological event-identity) to compare, and could report the empirical comparison as part of the contribution.

---

## 14. V2 extraction with bundled per-record axis tagging
**[Canonical]** — this section's architectural idea *became* canonical's 6-axis Opus 4.6 record-type labelling (`pipeline/label_record_types.py` + the v3 prompt at `canonical/prompts/label_record_types_v3.md`). Implementation diverged from the proposal: the schema is 6 axes (occurrence/mechanism/specification/lesson/recommendation + valence) rather than the 9 axes proposed here, and labelling runs as a separate post-extraction Opus batch rather than bundled into extraction. The earlier bundled attempt at `legacy_v1p3/code/label_axes.py` (now also at `canonical/narrative/superseded_v2_experiments/label_axes.py`) implemented this section's 9-axis form before being superseded.


**Anchor:** discussion 2026-05-01 following §13. Companion to §13 (chronological event identity); they're separable design decisions but compose cleanly.

**What we built (current architecture).** Per-record factual labels are produced across multiple downstream stages, each with its own prompt:
- **Stage 2 — causal recovery:** `causal_yes`, `causal_connective`, `causal_rationale` (Haiku, ~$30 in cumulative spend across keyword-discovery iterations)
- **Stage A — valence + mechanism tagging:** `valence`, `mechanism_named`, `mechanism_phrase` (Haiku, ~$18 for the full corpus)
- **Stage 6 — realisation classifier:** `realisation` (Haiku Batches API, ~$2)

Each runs as a separate per-record LLM call. Total ~$50 in cumulative downstream cost on the ARENA corpus. Each is independently calibratable (gap #1) but each adds its own prompt-accountability layer.

**What v2 would do.** Bundle all per-record source-grounded factual labels into a single extraction call. The expanded extraction schema would emit, per record:

```yaml
- record_id: ...
  source_title: ...
  publish_date: ...
  pages: [...]
  # === core extraction fields (current schema) ===
  what_happened: ...
  lesson_learnt: ...
  evidence_excerpt: ...
  intervention_note: ...
  issue_severity: ...
  # === new bundled per-record axis tags ===
  event_id: ...                         # from §13 chronological assignment
  event_name: ...                       # from §13
  causal_claim_made: yes | no            # was Stage 2 verdict
  causal_connective: "..." | null        # verbatim phrase signalling causation
  valence: positive | neutral | negative
  mechanism_named: yes | no
  mechanism_phrase: "..." | null         # verbatim
  realisation: realised | anticipated | generic | mixed
  # === optional new axes (gap #3 dimensions, brought forward) ===
  stakeholder: proponent | customer | vendor | network | regulator | end_user | unspecified
  interface_locus: design | commissioning | operations | commercial | regulatory | pre_execution | unspecified
  outcome_class: schedule | cost | safety | scope | commercial | reputational | equity | unspecified
```

**What stays as separate downstream stages.** Cluster assignment (Stage F), parent/theme assignment (Stage 5), and Opus audit (Stage 5 audit) remain as separate stages. These require *cross-document comparison*: the record alone doesn't tell the LLM which of N existing clusters it best fits. Folding these into extraction would either re-introduce taxonomy-coupling-at-extraction (the v1 mistake explicitly avoided in the methodology) or require the extractor to see the entire taxonomy structure, which doesn't scale.

**Why this is structurally cleaner than the current architecture.**

1. **Eliminates ~3 downstream stages.** Stage 2 (causal recovery), Stage A (valence + mechanism), Stage 6 (realisation classifier) all become parts of the extraction output schema. The pipeline shortens from 6 stages to 3 (extract → cluster → parent-assign). Fewer artefacts, fewer prompt-accountability layers.

2. **Single LLM read produces all per-record signal.** Currently every record is read at least 3 times by separate LLM calls (extraction, causal recovery, valence). v2 reads it once and emits all factual labels together. **Lower per-record cost overall**, faster end-to-end, simpler debugging.

3. **Source-grounded coherence.** All the bundled fields are source-grounded factual judgements: "did the author state causation?", "what's the valence?", "is the mechanism named?", "is this realised or anticipated?". Each is answerable from the record's own content. Bundling them lets the LLM produce internally-consistent labels rather than separate calls reaching independent conclusions on near-identical text (cf. §1's NT SETuP near-identical-text inconsistency case).

4. **Closes the multi-axis tagging gap (§3) at extraction time.** The optional new axes (`stakeholder`, `interface_locus`, `outcome_class`) capture the structural dimensions implicit in cluster labels. Tagging them per-record at extraction means downstream synthesis becomes filter-and-compose rather than fixed-cluster retrieval. Multi-axis decomposition becomes free, not a separate v5 effort.

**Risks and design considerations.**

1. **Compounding correlated errors.** Each of the bundled fields is currently produced by an independent LLM call. An error in one currently doesn't propagate to others — Stage A's valence call doesn't see Stage 2's verdict, so it can't be biased by it. Bundling means a single LLM judgement informs all fields jointly, which **may introduce correlated errors** (e.g., a record the LLM mis-reads as positive will get all its bundled labels biased in the positive direction). Mitigation: the field schema enforces independence via separate enum/free-text fields; the LLM is instructed to evaluate each axis independently. Whether this works in practice needs pilot validation.

2. **Loss of stage-by-stage debugging.** Currently a misfit in any stage's output is traceable to that stage. Bundled extraction makes per-axis debugging harder — if `valence=negative` is wrong, was that the extractor's mood-reading or its mechanism interpretation? Mitigation: extraction prompt requires brief per-axis rationale fields (`valence_rationale`, `realisation_rationale`) so each label carries its own evidence, restoring per-axis accountability.

3. **Larger output schema per record.** Output tokens per record grow ~2x. With Sonnet 4.6 batched at $7.50/M output, the marginal cost increase on a 90k-record extraction is ~$30-50 — bounded.

4. **Prompt complexity.** The expanded prompt is longer and asks for more axes. Risk of degraded quality on any single axis if the prompt is overloaded. Mitigation: structured JSON schema with clear field definitions; pilot validation on 5-10 records hand-tagged.

5. **Stakeholder/interface_locus/outcome_class taxonomy needs locking.** These are new axes. The enum values shown above are first-cut; need to be validated against a representative sample to confirm they cover the corpus. Pilot work.

**Cost / effort.**

| Component | Cost |
|---|---|
| Pilot on 5-10 records (one project) — validate prompt, surface issues | ~$1 + 1 researcher-day |
| Hand-tag 20 records as ground truth for v2 prompt validation | ~3 hours |
| Full ARENA re-extraction with bundled schema + chronological event-id (§13 + §14 combined) | ~$120-200 batch / ~$200-350 sync |
| Pipeline simplification (delete Stage 2, A, 6 from the codebase) | ~1 researcher-day |
| **Total v2 deployment cost (combined §13 + §14):** | **~$200 batch / ~$350 sync + 1-2 weeks orchestration** |

Compared to current v1 architecture cost (~$80-110 cumulative across stages on the existing extraction), v2 is roughly cost-neutral for full-corpus deployment but architecturally simpler and produces richer per-record output.

**Dependencies.** §13 (chronological event identity) is naturally co-deployed — both are extraction-prompt changes with one re-run. If §14 ships alone, the bundled-fields architecture works; if §13 ships alone, the event-identity architecture works; combining them gives the cleanest v2 pipeline.

**Status.** Open. Like §13, best deployed first via the ANAO corpus (gap #5) — uses the v2 architecture from extraction start. ARENA re-extraction is a separate decision dependent on whether the v2 architecture's pilot validates the schema design.

**Implication for other gaps.**
- §1 (per-filter reliability calibration): becomes simpler — fewer filter stages to calibrate, but the bundled extraction itself becomes a single calibration point with multiple per-axis reliabilities. The §11 efficiency-chain framing still applies, just with shorter chains.
- §3 (multi-axis tagging architecture): partially closed — the bundled extraction surfaces stakeholder/interface_locus/outcome_class at extraction time. Multi-axis filter-and-compose retrieval becomes available without a separate v5 effort.
- §11 (story-depth metric) and §12 (narrative-depth asymmetry): unaffected. Still relevant.

---

## 15. Single-pass extraction caps records on very large documents — narrow effect, not the broad shoulder originally claimed
**[Bridging]** — the retraction here is the architectural justification for **both pipelines retaining the v1 grave extraction**. The original "92k records lost to saturation" claim would have forced re-extraction; the retraction allows the existing 90,192-record extraction to be the shared base for canonical AND legacy.


**Update (2026-05-01, after Hornsdale FCAS pilot):** The original §15 claim — that yield saturates above ~10k input tokens and that ~92k records are likely missed corpus-wide — was overstated, and based on a model assumption that did not hold up empirically.

**The bad assumption.** The 10k-token "shoulder" was inferred by fitting a linear baseline of records-per-1k-tokens on small docs (~7 records/1k tokens) and projecting that yield onto larger docs. This implicitly assumed **constant insight density per token across document sizes**: that a 100k-token doc should produce ~10× the records of a 10k-token doc on the same author / project / topic. Any departure from that linear projection was attributed to model under-extraction.

**What we actually saw.** Single-pass extraction on docs up to ~150k tokens *beat* chunked backward-walk extraction on the same documents (run on the same model, Sonnet 4.6). Specifically:

  - Hornsdale FCAS 3-doc pilot: v1 single-pass 200 records, v2 chunked 159 records — chunking *cost* 41 records on docs that were supposedly in the saturation regime.
  - The biggest *positive* effect of chunking was +8 records on the largest doc (97k chars / ~24k tokens), and even that recovered <10% of the supposedly-missed records.
  - Below ~10k tokens, chunking can't help (the doc fits in one call). Above ~10k tokens but below ~150k tokens, chunking *hurt*.

**The corrected framing.** Insight density per token is **not constant with document size**. Larger reports legitimately have lower density per token because they contain more table data, more methodology repetition, more figures referenced in prose, more boilerplate, more cross-references to material elsewhere in the report. The yield decline measured in the descriptive data is mostly *real content density decline*, not extraction loss.

**Where the saturation claim still holds — narrowly.** Above ~150k tokens (~600k chars), there is independent evidence of a soft cap: round-number clustering at exactly 200, 150, and 140 records across docs of very different input sizes (34k–337k tokens). That clustering is signature self-stopping behaviour and cannot be explained by content density alone. So the saturation effect is real for the 17 docs in ARENA's >150k-token tail, but not for the bulk of the corpus.

**The threshold change in code.** `pipeline/extract_v2.py` updated to set `SINGLE_CHUNK_THRESHOLD_CHARS = 600_000`. Default v2 path is now single-pass extraction; chunking only fires for the genuine outliers above ~150k tokens. Section retained below to document the original retracted claim alongside what the data actually supports.

**This retraction is the architectural justification for continuing to use the v1 extraction corpus.** The original §15 claim implied v1's existing 90,192-record extraction was missing roughly half the corpus (~92k records lost to saturation), which would have forced a full re-extraction with chunking before any downstream pipeline could trust the corpus. With the retraction, v1's single-pass extraction is empirically validated for docs up to ~150k tokens — the bulk of the ARENA corpus. The production architecture (post-extract grouping at `pipeline/group_events.py`) therefore operates directly on v1's existing records without re-extraction. The only docs that warrant re-extraction are the 17 in the >150k-token tail, costing ~$15-25 in batch rather than the $200-300 of a full corpus re-extraction. The §15 retraction is what allows the pipeline to be production-ready without that spend.

**Anchor:** descriptive analysis on `output/per_doc/doc_*.json`; v1-vs-v2 pilot at `runs/arena/per_doc_v2_test/` (3 Hornsdale FCAS docs).

**What the descriptive data shows.** Records-per-1k-input-tokens (yield) declines monotonically with document size:

| Median input tokens (window) | Yield (rec/1k tok) |
|---|---|
| 4.8k | 7.81 (peak) |
| 8.3k | 6.25 |
| 10.8k | 5.64 |
| 16.8k | 4.60 |
| 52.1k | 2.30 |
| 150k+ | 0.65 |

This decline is real but is a confound of two effects, not one:

1. **Genuine content density decline.** Large synthesis reports have more table data, more methodology repetition, more figures referenced in prose, more boilerplate. Discrete extractable findings per token genuinely decrease. Small Lessons Learnt docs are denser per token than long Final Reports.
2. **Model self-capping at the very high end.** Round-number clustering at exactly 200 records (3 docs), 150 records (11 docs), 140 records (8 docs), across very different input sizes (34k–337k). This *is* signature soft-cap behaviour and is unambiguous.

**What the v1-vs-v2 chunking pilot showed.** On the Hornsdale Wind Farm Stage 2 FCAS Trial (3 docs, both runs on Sonnet 4.6):

| Doc | Size | v1 single-pass | v2 chunked | Δ |
|---|---|---|---|---|
| KS Report (seed) | 60k chars / ~15k tok | 75 records | 53 records | **−22** |
| Neoen FCAS | 24k chars / ~6k tok | 50 records | 23 records | **−27** |
| AEMO FCAS | 97k chars / ~24k tok | 75 records | 83 records | +8 |
| **Total** | | **200** | **159** | **−41** |

The largest *positive* effect from chunking was on the doc closest to the supposed saturation regime (97k chars), and even there the recovery was only +8 records. The largest *negative* effects were on docs well below the supposed saturation threshold. Chunking is not the saturation-recovery mechanism the original §15 claimed.

**Where the real architectural value of v2 actually lies.** The pilot also showed:
- v1 dedup compression on these 3 docs: 200 records → 174 events (13%, mean 1.15 records/event).
- v2 extraction-time event identity: 159 records → 76 events (52%, mean 2.09 records/event).

The v2 architecture's real value is **event-identity-at-extraction reducing duplicate-event proliferation across multi-doc projects**, not chunking-based record recovery. v1's dedup is essentially noise on multi-doc projects (84% of events are singleton records); v2 collapses these into mechanism-coherent multi-record events with full LLM context at extraction time.

**Where chunking is still genuinely required.**
- The 17 docs above 150k input tokens (≥600k chars). v1 cannot process the largest 8 docs at all (`max_document_chars` cap of 600k for ARENA skipped them). For these, the choice is "chunked extraction" vs "no extraction," and the soft-cap evidence (200/150 records on 337k-token doc) supports that single-pass would lose substantial content.
- ANAO if its largest audits exceed the same regime (median 169k chars ≈ 40k tokens; max 867k chars ≈ 210k tokens). The largest ANAO docs sit in the genuine-saturation tail and need chunking. The bulk of ANAO docs (median ~40k tokens) probably do not.

**Where chunking is not warranted.**
- ARENA docs below ~150k tokens (essentially the whole corpus minus 17 outliers). The pilot data says chunking *costs* records here, presumably because cross-doc event context makes the model conservative when it should still extract idiosyncratic per-doc evidence.
- Same conclusion likely applies to the median ANAO doc.

**Implications for other gaps.**
- **§13 / §14 / §5 (ANAO v2 deployment).** Drop "chunking is a first-class v2 component" framing. Chunking should be triggered conditionally for docs >150k tokens, not by default. Default v2 path is single-pass extraction with event-identity passing — same as v2 on small docs in the pilot.
- **§8a, §12.** Still hold. The v2 architecture's documented improvements (Hornsdale records/event 2.09 vs 1.15) are about extraction-time event identity, not chunking.
- **Seed-doc heuristic.** Independent of chunking. Stays.
- **Methodology paper claims.** Drop the "~92k records likely missed" projection. Tighter claim: "Single-pass extraction shows soft-cap behaviour at very high doc sizes (>150k tokens, 17/1448 docs); the broader yield decline reflects content density, not saturation."

**Effort.** Conditional chunking gate — trigger backward-walk chunking only for docs >150k input tokens (or whatever empirical threshold the pilot establishes). Trivial code change in `extract_v2.py` (raise `SINGLE_CHUNK_THRESHOLD_CHARS` to ~600k chars). The 17 affected ARENA docs would re-extract at ~$15-25 batch.

**Status.** Original broad claim retracted; narrow claim (soft-cap at the very top end) retained. Conditional chunking design is the open follow-up.

---

## 16. Footnotes are not reconciled with their body occurrences before extraction
**[Bridging]** — extraction-level concern; both pipelines share the v1 grave extraction and inherit this issue equally.


**Anchor:** observation 2026-05-02; marker-rendered markdown at `corpora/<domain>/marker_output/<stem>/<stem>.rendered.md`. Diagnostic script at `corpora/arena/tests/extraction/check_footnote_handling.py`.

**What we observe.** The marker-rendered markdown that v1 extraction reads emits footnotes as a Pandoc-style `[^N]:` definition block at the end of the doc, separated from the body by `---`. The body paragraphs contain `<sup>N</sup>` or `[^N]` reference anchors. There is no reconciliation step that pairs each anchor with its corresponding footnote text. The extraction prompt reads the body first and the footnote block second, with no in-context binding.

**Three patterns in the existing corpus** (per `check_footnote_handling.py` diagnostic):

- **A. Body refs + footnote block both present, mostly intact** (e.g. `doc_0211` AEMO Hornsdale W2 FCAS Trial: 27 body refs, 21 definitions). Most records come from body; ~1-2% from the footnote block.
- **B. Body refs + definitions, but with mismatch** (e.g. `doc_0198` AECOM Electrifying Road Freight: 11 body refs, 27 definitions, 16 unreferenced definitions). Definitions exist but are unanchored — extraction mostly ignores them.
- **C. Body refs but no definitions** (e.g. `doc_0191` 2024 ACAP Annual Report: 10 `<sup>N</sup>` markers, 0 definitions in the rendered markdown). Marker stripped the footnote text entirely. Definitions are gone from the rendered file before extraction sees it.
- **D. No footnote markup** (e.g. `doc_0573` Hornsdale KS Report). Nothing to reconcile.

**The right framing for the concern.** Orphan footnote records (records sourced from the footnote-block with no body context) would be poorly grounded and arguably worse than missing records altogether. Empirically, extraction mostly avoids creating them — across the docs we spot-checked, only 0-3% of records were sourced from the footnote block. **That's the desired outcome given the conversion limitations.**

The genuine loss is **specific evidence missing from body records that reference a footnote**. When the source says "the standard's response-time requirements are ambiguous[12]" and footnote 12 contains "specifically clauses 3.3.4.2 and 4.5.3", the resulting body record correctly captures the ambiguity finding but loses the specific clause references. This is a recall-of-detail issue, not a record-count issue. The body record is still a valid record; it's just less specific than it could be.

**Effect on existing v1 records.** Some fraction of records reference content that's footnoted in the source. Those records' `evidence_excerpt` and `narrative` will be slightly less specific than they could have been. The architecture of the records is correct; the detail in them is occasionally underspecified. We have no quantified estimate of how widespread this is and don't need one — the production pipeline (post-extract grouping → consensus) doesn't care about within-record specificity, only about which records belong to which event.

**What research-grade would require.** A pre-extraction reconciliation step in marker post-processing that inlines each footnote text adjacent to its body anchor (e.g. parenthetical insertion or HTML comment). One round of regex + string concatenation. Validation by re-extracting a sample and checking whether body-record narrative gains specific footnote detail. Effort: ~1 day. Re-extraction backfill on footnote-heavy docs: ~$50-100.

**Dependencies.** None. Independent of §13/§14/§15. Reconciliation also doesn't require re-extraction to be useful — could be applied to future corpora before extraction runs.

**Status.** Known limitation, deliberately deferred. Not blocking production architecture. The empirical observation that extraction mostly avoids creating orphan footnote-block records (which would be poorly grounded and harmful) means the current behaviour is acceptable: we lose some within-record detail specificity but don't introduce poorly-contextionalised records. Reconciliation would *improve* records but isn't required for production use.

---

## 17. Record-type tagging tier validation — Sonnet undercounts FC candidates by ~30% (is_mechanism, not is_specification, is the actual lever)
**[Canonical]** — explicitly about the canonical 6-axis Opus 4.6 v3 record-type pass. The Sonnet-vs-Opus mechanism finding here drove the canonical labelling production decision (Opus 4.6 + temp=0). Does not apply to legacy stage-A valence/mechanism tagging which used a different prompt and tier.


**The gap.** The corpus-wide record-type tagging pass uses Sonnet-4.6 with the v3 prompt and full JSON output. On the 173-record NT SETuP pilot, the headline accuracy figure (~92% on is_specification corpus-wide vs Opus-majority) understated the *downstream* effect:

- **Sonnet's FC pool is ~32% smaller than Opus's** on the same records (39 vs 57 under the gated definition `negative AND (occurrence OR mechanism) AND NOT is_specification`).
- **0 of 26 FC-pool membership disagreements are caused by is_specification flips.** All 22 Opus-only FC records have an `is_mechanism: no→yes` flip; is_specification flips co-occur on some but never alone.
- The diagnosed failure mode is **Sonnet systematically under-tagging is_mechanism**, particularly on records that present causal pathways inside generalisation framing (Sonnet reads them as `is_lesson: yes`; Opus reads them as `is_mechanism: yes`).
- The 11-record 1361-series in the NT SETuP pilot exhibits this pattern uniformly. The 0911-series environmental records (5 records) show the same is_mechanism flip, with co-flipping on is_specification that we'd previously misdiagnosed as the cause.

**Why this changes the picture.** A 7pp accuracy gap on a single axis doesn't justify the $87 Opus premium for a 90k corpus run. A 30% undercount of failure-mode candidates with systematic mechanism-vs-lesson confusion does — it propagates to fewer FC clusters, thinner mechanism-axis taxonomy, and possibly under-counted failure-mode discovery. The methodology finding may be that **Sonnet-v3 is reading mechanism-bearing records as lessons in a way that materially shrinks the failure-mode candidate set**.

**Two known un-validated questions:**

1. **Whether the is_mechanism under-tagging is project-specific or systematic.** The 173-record pilot is one project (NT SETuP); 11 of 22 under-mechanism records are from one document (1361). A 2,000-record stratified sample (8 top kb_categories × {Reports, Reports+Lessons}) resolves this — submitted as a Batches API job; ~$16 async.
2. **Whether v4 (or another) prompt iteration can close the Sonnet-v3 mechanism gap.** v4 targeted is_specification only; a future v5 should target the is_mechanism / is_lesson confusion specifically. Cross-axis bleed in v2/v4 means the iteration must be more surgical than past attempts.

**What was settled before deferral.** The format-compression study (full JSON / hybrid / compact / terse / extended-thinking) is closed: full JSON output is the production format. The verbose-output-as-deliberation-surface finding stands. The stability-vs-accuracy finding (Sonnet replicates its own miscalibration on loose-boundary axes) stands. See `corpora/arena/tests/extraction/runs/2026-05-02-record-type-pilot/notes.md` for the full record.

**Why production-deferred but actively investigating.** The 2,000-record stratified Batches API run is in flight (async, ~$16). When it lands it tells us whether Sonnet's mechanism under-tagging generalises beyond NT SETuP. That informs the production-tier decision much more cleanly than the headline-accuracy framing did. Until it lands, Sonnet-v3 fullJSON remains in production with the known caveat that the FC pool may be ~30% smaller than an Opus-tagged equivalent — which is itself an interesting methodology finding if the corpus run propagates it visibly to cluster sizing and failure-mode discovery rates.

**Validation plan when resourced.**

1. **In flight:** 2,000-record stratified Sonnet vs Opus comparison via Batches API. Resolves project-specificity of the is_mechanism finding. ~$16 async.
2. Quantify downstream-filter sensitivity: of the ~30% smaller Sonnet FC pool, how many of the missing records actually change cluster assignment, theme distribution, or failure-mode discovery rate?
3. If Opus changes are material: deploy Opus for the corpus-wide tagging pass (~$162) or attempt a v5 prompt iteration targeting the is_mechanism / is_lesson confusion specifically (must be more surgical than v2/v4 to avoid cross-axis bleed).
4. Hand-adjudicate a stratified sample of mechanism-disagreement records from the 2,000-record run to confirm whose call is correct.

**Status (updated after 2,000-record validation, 2026-05-02 evening).** The 2k stratified Batches API run landed in 2.5 minutes and falsified the FC-pool-*undercount* finding — but **not** the broader concern that tier choice affects downstream filter behaviour. The pool-size gap closed (Sonnet 516, Opus 513, -0.6%) only because Sonnet's under-mechanism bias cancels against its under-specification bias at the gate. **Pool composition still diverges by ~28%** (Jaccard 0.76, 73 Sonnet-only and 70 Opus-only out of ~516). 143 different records flow downstream depending on tier choice — different cluster seeds, plausibly different cluster boundaries, plausibly different failure-mode taxonomy. The size-match is a coincidence; the composition gap is the substantive finding.

Sonnet *does* under-tag is_mechanism by 10pp at scale (yes-rate 39% vs Opus's 49%) and is_lesson by 6pp. Cross-tier agreement floors at ~86% on is_mechanism and ~87% on valence — the epistemically loose axes with irreducible tier-disagreement at this prompt design.

**Production decision (Sonnet-v3 fullJSON) is a deliberate cost trade-off, not a clean win.** It saves $87 vs Opus but accepts that ~28% of FC pool records would have been different under Opus tagging. The downstream effect of that composition swap on emergent cluster structure is the open question. See `corpora/arena/tests/extraction/runs/2026-05-02-record-type-pilot/notes.md` "2,000-record at-scale validation result" section for the full tables.

**Remaining open question.** Whether the 28% FC-pool-composition difference materially changes which clusters surface, how they're named, and what failure-mode threads make it into the lessons compendium. This requires running clustering on both tier outputs and comparing emergent cluster structure — a much larger experiment, deferred behind the corpus dedup work and the grey-paper deadline. The headline statistic for the methodology paper should be **Jaccard 0.76 on the FC pool**, not "size matches within 1%."

**Ground-truth update (2026-05-02 evening).** A 44-record hand-adjudication sampled stratified-randomly from the 277 cross-tier `is_mechanism` disagreements on the 2k run resolved the under-vs-over framing:

- **Under-tag direction (Sonnet=no, Opus=yes):** Opus correct on 18/24 (75%); Sonnet correct on 6/24 (25%). **Sonnet's under-tagging is a real bias** — it systematically misses genuine mechanisms.
- **Over-tag direction (Sonnet=yes, Opus=no):** tied 50-50 on 20 records. These are genuine edge cases (hedged-without-pathway, speculative, citation-derived noise); not a Sonnet bias.

Extrapolated to the 277 disagreements: ~198 favour Opus, ~79 favour Sonnet. Scaled to the 90k-record corpus: **~8,000 records (±~2,000 CI) that Sonnet would tag `is_mechanism=no` but should be yes.** That's the concrete cost of choosing Sonnet on this axis. The **"richer failure modes under Opus"** conjecture is now empirically supported on the mechanism axis itself, with the propagation question (does it produce richer cluster-level taxonomy?) still requiring downstream clustering experiment.

**Production decision unchanged but trade-off is named:** Sonnet at $75 misses ~8,000 genuine mechanisms vs Opus at $162. The methodology paper should report this trade-off explicitly, not present Sonnet as a clean win.

**Cross-version Opus check (2026-05-02 evening).** Submitted Opus 4.6 + temp=0 × 3 reps on the same 2k sample to test whether the "Opus more accurate" finding was confounded by model version or temperature. **Result: Opus 4.6 + temp=0 ties Opus 4.7 default at 64% on adjudicated mechanism**, with higher within-rep stability (0.98-0.99 vs 0.95-0.99). The Opus accuracy advantage is robust to both version and temperature — genuine model capability, not artefact.

**However, FC pool composition is sensitive to Opus version too:** Opus 4.6 vs Opus 4.7 has Jaccard 0.77 — ~23% of FC records differ between the two Opus versions, similar magnitude to the cross-tier (Sonnet vs Opus) Jaccard of 0.76. There is no single "stable Opus answer"; the FC pool is a per-config object.

**Production swap.** Corpus tagging will use **Opus 4.6 + temp=0** instead of Opus 4.7 default. Same accuracy, higher reproducibility, same pricing. Better for methodology-paper rigour ("we used the deterministic variant"). Cost unchanged at $162 batch+cache.

---

## Prioritisation (as of 2026-05-01)
**[Bridging]** — written from the legacy pre-canonical viewpoint; some prioritisation is now obsolete because the canonical pipeline has implemented §13 + §14.


| Order | Gap | Why this rank |
|---|---|---|
| 1 | #12 Narrative-depth asymmetry (paper claim sizing) | Must lock the paper's framing *before* drafting; pairs with #10. ~half a day, writing only. |
| 2 | #10 Two-axis retrieval claim in paper | Highest-leverage paper move. Architecture is built; the methodology paper should claim it. ~writing only. |
| 3 | #9 Live joint-reliability readout | Half-day, no spend, demonstrates §11 concretely. |
| 4 | #11 Story-depth in navigator | Half-day to wire computed metric into UI. Two-dimensional cluster quality. |
| 5 | #2 (recall fix) "therefore" + similar formal connectives | ~30 minutes to add to keyword regex; replays existing data. Plugs the named recall hole. |
| 6 | #8a Records-vs-events documentation | In progress as part of the folder split + Phase B event-keyed datasets. ~1 day, no spend. |
| 7 | #1 Per-filter reliability calibration | Closes the biggest credibility gap in §11. ~300 hand-tags, no API spend. |
| 8 | #4 Positive-valence symmetry | Tighter generalisation proof than cross-corpus (no domain confounds). ~$60. |
| 9 | #2 (full Stratum A) Recall validation | The named-connective fix is part 1; full Stratum A is part 2. ~1 researcher-week. |
| 10 | #7 Filter-error correlation | Cheap follow-on once #1 lands. |
| 11 | #8b Canonical-record content coverage | Cheap sub-task of #8a's deeper re-run. ~3 days hand-reading. |
| 11.5 | #15 Extraction self-cap on very large docs (narrow scope after retraction) | Now scoped to the 17 ARENA docs >150k tokens + ANAO outliers. Conditional chunking gate — raise SINGLE_CHUNK_THRESHOLD_CHARS to ~600k; default path is single-pass. ~$15-25 to re-extract ARENA's 17 outliers. Architectural pre-req for ANAO is reduced to "have chunking available," not "use it by default." |
| 12 | **#5 + #13 + #14 — ANAO as v2-architecture testbed (combined deployment)** | The single biggest forward move. ANAO becomes the first v2 deployment (chronological event-id + bundled axis tagging + chunked extraction per §15). Pilot first (~$5 + 1 day) → full ANAO extraction (~$200 batch) → ANAO clustering + audit (~$50) → optional ARENA-on-v2-axes retrofit (~$30-50). Total ~$250-400 + 2-4 weeks. Methodology paper's strongest contribution: v1 (ARENA) vs v2 (ANAO) architecture comparison. Dissolves §8a, §12, §16 and partially closes §1, §3. |
| 13 | #6 Within-document failure-mode synthesis | Re-opens the locked epistemic position. Argument first, experiment second. |
| 14 | #8a-deep Records-vs-events sensitivity rerun | Tests whether v3.5 taxonomy is record-pipeline-artefact vs robust mechanism finding. ~$30 + 1 week. **Obviated by §13/§14 v2 architecture deployed via #5.** |

Items 1–9 are realistically completable inside a 1–4 week window before the grey paper deadline (2026-05-07) or shortly after. Items 10–14 are publication-pipeline work, with item 12 (combined ANAO + v2 deployment) being the single largest forward move and the natural anchor of the next research deliverable.

**Note on #13 + #14's relationship to other gaps.** Combined as the v2 extraction architecture, §13 (chronological event-identity) and §14 (bundled per-record axis tagging) dissolve or partially close several other items in this list:

- **§8a (records-vs-events)** dissolves under §13 — events become first-class, mechanism-cohesive by construction, and prompt-accountable at the moment of extraction.
- **§12 (selectivity in dedup grouping)** dissolves under §13 — selectivity moves from dedup-after-extraction to event-id-during-extraction with full LLM context.
- **§16 (records-vs-events sensitivity rerun)** is obviated by §13 — there's no records-vs-events distinction to test if events are extraction-time first-class.
- **§3 (multi-axis tagging architecture)** is partially closed under §14 — bundled extraction surfaces stakeholder, interface_locus, outcome_class at extraction time.
- **§1 (per-filter reliability calibration)** simplifies under §14 — fewer downstream filters, but the bundled extraction needs its own per-axis reliability calibration.

The combined v2 architecture is upstream of multiple downstream gaps, so the prioritisation reflects that solving #13+#14 *together* is more efficient than solving them separately or solving the dissolved-gaps independently.

---

## Pitch posture
**[Bridging]** — applies to the document as a whole regardless of pipeline.


This document is part of the deliverable, not a confession. When presenting the methodology paper:

> *"We've built a tool that beats the realistic counterfactual on a hard corpus. Here's the work that turns it into a research instrument with formally validated uncertainty. Each of those steps is a publishable extension. The research programme will deliver them."*

Reading the gap list as a research roadmap rather than a list of failures is the framing the paper and the methodology document should share.