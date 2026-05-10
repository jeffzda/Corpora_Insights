# Blinded validation of cluster→parent assignments (2026-05-08)

Independent same-rubric review of the s10 cluster→parent assignment for the 86-parent extended ensemble taxonomy. Tests whether the original Opus 4.7 assignments hold up under blinded re-review by a fresh Opus 4.7 call with original confidence labels and rationales held out from the input.

## Headline

> **68/91 (74.7%) of cluster→parent assignments are confirmed clean fits under fixed-parent same-rubric review. 14 are validated-medium (genuine criterion-fit ambiguity). 8 warrant follow-up review. 0 two-step disagreements (no high-low flips). Cost $0.40.**
>
> Medium-confidence labels in the original run primarily reflect *selection ambiguity* among adjacent parents in the 86-parent panel rather than fit-criterion uncertainty: 23 of 42 (54.8%) medium-rated assignments upgrade to high under fixed-parent review, indicating the chosen parent is a clean home even when alternatives were plausible.

## Sample

- 91 cluster→parent assignments across 5 medium-sized parents:
  - p25 Feedstock and input variability (24)
  - p33 Inverter-based resource and grid-stability dynamics (23)
  - p44 Single point of failure and shared-resource fragility (9)
  - p61 Regulatory ambiguity and jurisdictional fragmentation (11)
  - p77 Customer recruitment, conversion, and retention friction (24)
- Original-run confidence distribution: 48 high / 42 medium / 1 low
- Reviewer: independent Opus 4.7 call (no shared context, no chain-of-thought from original)

## Method

Two passes were run, both with the original-run confidence labels and rationales **held out from the input**:

1. `prompt_v1_fitscale.md` — fit/borderline/misfit verdict scale. Useful as a quality verdict but not directly comparable to the original H/M/L confidence rubric. Captured in `verdicts_v1.jsonl` ($0.21).

2. `prompt_v2_hml_rubric.md` — same H/M/L rubric used by the original assignment task, lifted verbatim from `pipeline/stages/s10_parent_assign/prompt.md`. This is the apples-to-apples test. Captured in `verdicts_v2.jsonl` ($0.19).

The v2 pass is the primary result; v1 is kept as an alternative quality lens.

### What the test does NOT do

The reviewer sees the cluster + the assigned parent only — not the other 85 parents in the panel. So this test isolates **criterion-fit** (does the cluster's mechanism match this parent's criterion?) from **selection** (which parent in the full panel is best?). The original run carried both uncertainty sources in a single confidence label. Disentangling them requires a separate test (full re-assignment with all 86 parents visible).

## Result

3×3 confusion matrix (rows = original run confidence, columns = blinded reviewer confidence):

| original ↓ \\ blinded → | high | medium | low | total |
|---|---:|---:|---:|---:|
| **high** | **45** | 3 | 0 | 48 |
| **medium** | 23 | **14** | 5 | 42 |
| **low** | 0 | 0 | **1** | 1 |

- Agreement (diagonal): 60/91 = **65.9%**
- Cohen's κ: **0.343** ("fair")
- 1-step disagreements: 31; 2-step (high↔low): **0**

### Reframed for assignment-quality interpretation

| original | blinded | n | interpretation |
|---|---|---:|---|
| high | high | 45 | Clean criterion fit, no selection ambiguity. **Confirmed clean.** |
| medium | high | 23 | Clean criterion fit; original-medium reflected selection ambiguity. **Confirmed clean.** |
| medium | medium | 14 | Genuine criterion-fit medium. Real ambiguity. |
| medium | low | 5 | Original probably overgenerous. **Flag for review.** |
| high | medium | 3 | Original possibly overconfident. **Flag for review.** |
| high | low | 0 | None. |
| low | low | 1 | Original-low correctly flags misfit. (Sample too small for rate.) |

**Validated clean fits**: 68/91 = 74.7%
**Validated medium**: 14/91
**Flagged for review**: 8/91
**No catastrophic disagreements**: 0/91 high↔low flips.

### Rationale parity at high-high cells

When both runs assign high, the rationales are near-verbatim equivalents (for the same cluster, both runs cite the same mechanism in similar words). Examples:

| cluster | original rationale | blinded rationale |
|---|---|---|
| c026 | Biomass feedstock physical properties exceed flow tolerance of handling equipment. | Biomass feedstock physical properties exceed handling system tolerance. |
| c627 | Siloxane contaminant in biogas damages downstream equipment. | Feedstock contaminant (siloxanes) damages consuming process. |
| c910 | Variable feed-gas contaminants exceed upgrader tolerance — input variability. | Feed gas contaminant variability exceeds upgrader tolerance. |

Confidence label stability ≠ rationale stability would be a problem; this is not that problem.

## Defensible methodology-paper claims

1. **High-confidence assignments are reliable.** 45/48 = 93.8% high-high agreement under same-rubric blinded review. When the original run was confident, an independent run agrees almost always.

2. **Medium-confidence reflects selection ambiguity, not fit-criterion uncertainty.** 23/42 = 54.8% of medium-rated assignments upgrade to high under fixed-parent review. The chosen parent is a clean home for these clusters; the original run was correctly cautious about selection in a 86-parent panel where adjacent parents could also fit.

3. **No catastrophic miscalibration.** 0 two-step disagreements (no high↔low) across 91 assignments. Whatever instability exists is local, not catastrophic.

4. **Misfits track low/medium-low confidence.** All 5 medium→low downgrades and the single low-low case are at original-medium-or-lower. This supports using confidence as a triage filter, with the caveat above (medium ≠ uniform fit-uncertainty).

## What this does NOT establish

- **Selection quality**: this test does not check whether the chosen parent was the *best* of the 86 alternatives. A medium→high cell could mean "this parent is one of two equally good homes" — the test can't distinguish best fit from acceptable fit. To answer that, run a full re-assignment over all 86 parents (~$2.30, biggest signal).

- **Calibration of the medium label as a probability**: medium is a hedge under selection ambiguity, not a calibrated middle-probability of fit. Treat the binary high-vs-not-high distinction as the primary signal.

- **Rate of low-confidence misfit**: the original run produced only 7 low-confidence labels across 1141 assignments (0.6%). This sample contains 1 low-confidence case. Insufficient for a rate claim.

## Methodological notes

The v1 pass (fit/borderline/misfit scale) was run before realising the rubric mismatch. Its result (74/91 = 81.3% fit) is an over-strict version of the same finding because borderline likely sits below the original "medium" threshold. Kept in this directory for transparency. The v2 H/M/L pass is the primary apples-to-apples test.

This validation was identified as flawed in earlier framings during the conversation that produced it. Specifically:
- An initial inline sense-check by the assistant was contaminated by visibility of the original confidence labels (priming).
- The first blinded re-run used a different scale (fit/borderline/misfit) that conflated quality and selection signals.
- The user identified that the same-rubric same-task constraint requires withholding rationales as well as confidence labels and using the H/M/L rubric verbatim.
- The v2 result here implements those corrections.

## Cost and files

- v1 fit/borderline/misfit pass: $0.21 (Opus 4.7, 9.9k in / 6.5k out, 84s wall)
- v2 H/M/L pass: $0.19 (Opus 4.7, 10.0k in / 5.5k out, 61s wall)
- **Total $0.40**

Files in this directory:
- `prompt_v2_hml_rubric.md` — primary blinded prompt
- `verdicts_v2.jsonl` — primary verdicts (91 records)
- `response_v2_raw.txt` — full raw model response
- `prompt_v1_fitscale.md` — alternative-scale prompt (kept for transparency)
- `verdicts_v1.jsonl`, `response_v1_raw.txt` — corresponding artefacts

## Boundary-mapping pilot + 10-rep ensemble (2026-05-08)

Full selection-task with primary+optional-secondary parent assignment on the
91-cluster sample. Run twice: as a single sync pilot ($0.39, see
`PILOT_boundary_mapping_2026-05-08.md`), then as a 9-rep batched ensemble
($1.80, see `PILOT_ENSEMBLE_2026-05-08.md`). Total 10 reps, $3.60.

**Ensemble headlines (load-bearing, 10 independent Opus 4.7 reps):**
- **Primary stability**: 90.1% of clusters have ≥6/10 reps agreeing on primary;
  74.7% have ≥8/10; 52.7% are unanimous.
- **Top-2 validation**: 73.6% of original assignments appear in top-2 across
  ALL 10 reps. 79.1% in ≥8/10 reps.
- **Strong reassignment candidates** (original never in any rep's top-2):
  5/91 — c1133, c1276, c1282, c1447, c1479. Defensible "the original is wrong"
  cases.
- **Unanimous reassignments** (10/10 reps agree on a non-original primary):
  7/91 — including 5 p25→p18 cases, confirming the p25↔p18 single-boundary
  signal at ensemble scale.
- **Stable adjacency pairs** (in 10/10 reps): p25↔p18 (79 events), p33↔p35,
  p33→p43, p38→p77, p61↔{p59,p60,p65,p71}, others.
- **Two diagnostic signal shapes confirmed**: p25 = single-boundary problem
  (75% concentration on p18); p77 = structural fragmentation (8 distinct
  alternative parents).

Cost economics correction: the previously documented "§16 cluster-layer
ensemble gap" of $1500-5000 was wrong. Actual v2 clustering sweep costs
$55 sync / $36 batched. **A 10-rep full-clustering-stage ensemble would be
$360-550 batched** — affordable, not budget-blocking.

Estimated cost for publishable boundary-mapping ensemble at full corpus:
~$10-30 batched (10 reps × 1141 clusters × winning rubric).

## Full-corpus ensemble — landed 2026-05-09

Ran in `full_corpus_ensemble_v3/` (~$22 batched, 120 calls). Headlines:
- 73.5% of original assignments always in top-2 across all 10 reps; 80 strong
  reassignment candidates (orig never in top-2); 94 unanimous disagreements
- 64.8% unanimous primaries; 81.1% ≥8/10 agree
- 86×86 adjacency heatmap + network diagram; cross-theme bridges identified
  (p18 hub linking t04↔t06; t11↔t12 economic-policy interface; t09↔t13
  technical-coordination cascade at p38↔p70).

## Documented gap — cluster signature drift

See `CLUSTER_SIGNATURE_DRIFT.md`. Cluster signatures are derived at minting
time, not re-synthesised after membership stabilises. Top adjacency edges
(≥40 events) are robust to drift; long-tail edges (≤30 events) may include
drift artefacts. Fix is a $170 batched signature re-synthesis pass + ~$25
re-ensemble. Not committed.
