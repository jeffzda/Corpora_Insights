# Pilot: cluster→primary+secondary parent — boundary mapping (2026-05-08)

> **Status: exploratory pilot, not a finding.** A single Opus 4.7 call. The headline numbers below are illustrative of what an ensemble pass would surface, not load-bearing claims.
>
> **What's real about this run** — the prompt elicits useful structure on the first pass:
>
> - **75 of 91 original assignments (82.4%) appear as primary or secondary in the pilot's top 2.** All 48 original-high assignments match perfectly under selection-task review.
> - Disagreements have **two distinguishable diagnostic shapes**: a single-boundary signal at p25↔p18 (75% concentration on one alternative — candidate criterion-sharpening) and a fragmentation signal at p77 (18% concentration; spread across 8 alternatives — candidate parent-splitting).
> - Monotonic secondary-presence rate by confidence (71% high / 86% medium / 100% low) supports the "medium = selection ambiguity" framing from `verdicts_v2`.
>
> Numbers like primary-only agreement (61.5%) and non-null secondary rate (78%) are unstable on a single run and need ensemble + rubric tuning before any boundary-matrix claim can be defended.

## Sample, design, cost

- 91 cluster→parent assignments across the 5 medium-sized parents (p25, p33, p44, p61, p77) — the same sample as `verdicts_v2.jsonl`
- Reviewer: independent Opus 4.7 call, blind to original assignment + confidence + rationale
- Full 86-parent panel visible (unlike v2 which fixed the parent)
- Output: per cluster, primary parent + confidence + rationale; optional secondary parent (or null) + confidence + rationale
- Strict rubric: secondary only where the cluster's mechanism *genuinely satisfies* a different parent's criterion — not "second-best if forced"
- Cost: $0.39, 161s wall, 15.3k in / 12.7k out

## Result (illustrative)

### Headline number — top-2 selection agreement

> **75/91 (82.4%) of original assignments are validated as appearing among the pilot's top-2 picks** (either primary or secondary parent matches the original). **All 48 original-high assignments (100%) match in either slot** — strong validation under the harder selection task (full 86-parent panel) than was provided by the v2 fixed-parent test.

### Full agreement table

| metric | value |
|---|---:|
| Primary matches original | 56/91 (61.5%) |
| Secondary matches original | 19/91 (20.9%) |
| **Either primary or secondary matches original** | **75/91 (82.4%)** |
| Neither matches | 16/91 (17.6%) |

By original-run confidence:

| original | n | either-match rate |
|---|---:|---:|
| high | 48 | **48/48 = 100%** |
| medium | 42 | 27/42 = 64.3% |
| low | 1 | 0/1 = 0% |

**Reading:** strict primary-only agreement is 61.5% — substantial run-to-run drift in the *primary* choice. But the original parent shows up as a top-2 pick in 82.4% of cases. The original assignment is rarely *absent* from the pilot's top picks; it's just not always the strongest pick. That is consistent with selection-task ambiguity rather than wrong assignment.

### Disagreements have two distinct shapes — single-boundary vs structural fragmentation

Looking at *all* primary-disagreement events (35/91 across all confidence levels), the disagreements split cleanly into two diagnostic signal types, distinguishable by how concentrated each parent's disagreements are on a single alternative:

| original parent | disagreements / total | top-1 alternative concentration | distinct alternatives | shape |
|---|---:|---:|---:|---|
| **p25** Feedstock variability | 12/24 | 9 → p18 (**75%**) | 3 | **single-boundary** |
| **p77** Customer recruitment | 11/24 | 2 → p75 (**18%**) | **8** | **fragmentation** |
| p33 IBR dynamics | 4/23 | 2 → p35 (50%) | 3 | inconclusive (small n) |
| p44 SPOF | 5/9 | 3 → p42 (60%) | 3 | inconclusive (small n) |
| p61 Regulatory ambiguity | 3/11 | 1 → p59 (33%) | 3 | inconclusive (small n) |

**Single-boundary problem — p25↔p18.** 75% of p25's disagreements (9 of 12) concentrate on one alternative parent: p18 Material, chemical, and physical-property limits. The pilot consistently re-reads "feedstock variability" assignments as "intrinsic material-property limit" assignments. This is not 9 random reassignments — it is 9 votes for one specific taxonomy boundary problem. **Candidate response:** sharpen the criterion separating p25 (input variability hitting tolerance) from p18 (intrinsic property out of spec), or consider merging if the criteria can't be operationalised cleanly.

**Structural fragmentation problem — p77.** Only 18% concentration at top-1 alternative; p77's 11 disagreements scatter across **8 distinct alternative parents** (p75 trust, p78 behavioural rebound, p38 interoperability, p79 DR delivery, p68 contract structure, p46 heterogeneity-defeats-one-size, p66 subsidy distortions, p01 missing data). This is not a boundary problem — p77 is functioning as a catch-all for behavioural-layer customer-side mechanisms that ought to live in 8 different parents. **Candidate response:** consider splitting p77 into more specific sub-categories, or accept that "customer-side friction" is genuinely heterogeneous and re-classify these clusters into the more specific neighbours.

The same disagreement data produces two qualitatively different diagnoses (sharpen one criterion vs split the parent into more specific neighbours) distinguished by **the concentration metric: top-1 alternative as a fraction of total disagreements for that parent**. This is itself a small methodological contribution: boundary-mapping doesn't just say "where are the boundaries fuzzy" — it distinguishes "this line should be redrawn" from "this parent should be split".

### Other illustrative numbers

| metric | value | reading |
|---|---:|---|
| Non-null secondary rate | 71/91 (78.0%) | Much higher than the design hoped (20-50%). Either rubric was too permissive or the 86-parent panel has pervasive mechanism-criterion overlap. **Both interpretations want ensemble disambiguation.** |
| Distinct primary→secondary pairs | 58 across 71 events | Light replication — most pairs unique. Ensemble would produce a much sharper concentration. |
| 2-step disagreements at high confidence both directions | 0 | Local instability, not catastrophic — consistent with v2 finding. |

### Secondary-presence rate by original-run confidence — selection-ambiguity is real and graded

| original confidence | n | with secondary | rate |
|---|---:|---:|---:|
| high | 48 | 34 | **71%** |
| medium | 42 | 36 | **86%** |
| low | 1 | 1 | 100% (n=1) |

Monotonic ordering: original-medium clusters carry secondaries more often than original-high. **This is directional empirical support for the "medium = selection ambiguity" framing from `verdicts_v2`.**

The 71% secondary rate on original-high is initially surprising but reads more naturally when paired with the **100% top-2 match rate on original-high**: the pilot is willing to identify a real secondary fit AND keeps the original parent in the top 2. So high-confidence assignments are not "clean single home with no alternatives"; they are "clean primary home that may also fit a secondary parent". The original confidence label was rating the primary fit, not the absence of alternatives. That distinction matters for how the label is interpreted in downstream analyses.

### Pilot-flagged top boundary pairs

These are adjacencies that surfaced even in a single run; in an ensemble they would be the most likely to survive as stable boundaries:

| pair | events | mechanism overlap |
|---|---:|---|
| p25 ↔ p18 (Feedstock variability ↔ Material chemical/physical limits) | 8 (5+3) | Material-property failures sit at the boundary of "input variability hitting tolerance" vs "intrinsic property limit". Bidirectional adjacency. |
| p33 ↔ p35 (IBR dynamics ↔ Control logic/protection) | 4 (2+2 in disagreements) | Many inverter-based-resource issues are also control-logic issues; the difference is whether the failure traces to the IBR's physics or to its programmed response. |
| p33 → p43 (IBR ↔ Legacy infrastructure incompatibility) | 3 | IBR issues frequently arise *because* legacy infrastructure assumed synchronous plant. |
| p61 ↔ p65 (Regulatory ambiguity ↔ Policy uncertainty) | 2 | Sister regulatory categories — one about overlap/conflict in current rules, one about instability of rules over time. Adjacency unsurprising. |
| p77 ↔ p75 / p78 / p79 (Customer recruitment ↔ Trust/Behavioural rebound/DR delivery) | 4 spread across these | Customer-side mechanisms cluster together; the four parents partition behavioural-layer failures along trust, friction, rebound, and delivery axes. |

These are the kind of pairs an ensemble matrix would highlight — *plausible* boundary candidates from this single run.

### Pilot disagreements with original primary — possibly-better assignments worth investigating

Where the pilot picked a different primary AND the alternative looks more apt by reading the rationales (manual judgement, not formal):

- **c044** (Long Tech Development Lead Time) — orig p44 SPOF (low conf) → pilot p85 Schedule cascade. Pilot is clearly right; even the original's low confidence flagged this.
- **c660** (Upstream Process Removes Co-Product Feedstock) — orig p25 → pilot p57 Supply chain. Pilot distinguishes supply availability from input-variability — fits the rubric better.
- **c722** (Shared Server Capacity Insufficient) — orig p44 → pilot p23 Capacity/sizing shortfall. Pilot's reading is sharper (this is sizing, not common-mode SPOF).
- **c043, c608, c843, c1012** — orig p25 → pilot p18 Material limits / p21 Decarbonisation residuals. Pilot reads several "feedstock" clusters as intrinsic-material-limit clusters; defensible alternative reading.
- **c611** (DR Participation Decline) — orig p77 (high conf) → pilot p79 DR delivery shortfall. Pilot is sharper — this is a delivery problem, not a recruitment problem.

These are not corrections to the original taxonomy; they are *candidate reassignments* that an ensemble would either confirm or reject.

## What this pilot does NOT establish

1. **The 78% non-null secondary rate is unstable.** A second run with a slightly tighter rubric or different prompt phrasing could land at 40% or 90%. Until tuned and ensembled, this number is illustrative only.

2. **The 38.5% primary disagreement rate is unstable.** Two interpretations — original-run noisiness, pilot-run noisiness, or both — cannot be disambiguated without ensembling both. Likely both contribute.

3. **The 86×86 boundary matrix from this run is thin.** 58 distinct pairs across 71 events on a 91-cluster sample tells us very little about which adjacencies are real and which are run-noise. The full corpus pass at ensemble scale would produce a meaningful matrix.

4. **No claim of "the original taxonomy is wrong"**. The pilot's better-looking reassignments are anecdotes, not findings. They demonstrate the kind of structure an ensembled boundary-mapping run would surface.

## What ensemble + tuning would look like

Per the user's flag — to take this from interesting illustration to publishable claim:

1. **Rubric tuning** — pilot scale, 2-3 prompt variants varying the strictness of the secondary criterion. Goals:
   - Land secondary-null rate at the rate that's empirically right rather than rubric-driven
   - Verify same boundary pairs surface across variants (stable structure)
   - Identify the rubric phrasing that produces the cleanest boundary pair distribution

2. **Ensemble at full corpus** — winning rubric × 10 reps × 1141 clusters. Estimated $30-40 at Opus 4.7 pricing. Affordable, in the same band as the parent-derivation ensemble.

3. **Outputs at scale**:
   - Primary-choice agreement with original (per-cluster: stable / drifting / disputed)
   - 86×86 boundary heatmap (stable adjacency pairs only — pairs surviving N≥3 reps)
   - Distribution of secondary-null rates (corpus-level estimate of selection unambiguity)
   - List of stable reassignment candidates (clusters where ensemble consistently picks a different primary than the original)
   - Boundary-fuzziness metric per parent — count of distinct adjacency partners across ensemble

This is what a "boundary mapping" methodology section would deliver. The pilot is a demonstration of the design surface, not the finding.

## Files

- `prompt_v3_boundary_pilot.md` — full prompt with all 86 parent criteria
- `verdicts_v3.jsonl` — 91 records, primary + optional secondary
- `response_v3_raw.txt` — raw Opus 4.7 response
