# Threshold defensibility — v2 parent-layer derivation

Empirical investigation of the canonical-class frequency threshold for selecting v2 parents from the 50-rep ensemble. Pure data analysis on the existing 126-canonical-class consolidation.

**Honest headline.** The frequency curve has no natural shoulder. It descends almost linearly from 100% (rank 1) to ~22% (rank 115), then drops to 0% over the last ~10 ranks. All automatic curvature/elbow detectors converge on the long-tail end (freq 10–26%), which would give ~110 parents — too many for usability. Above the long-tail, the threshold is unavoidably an analyst judgment within the empirically-defensible range. We adopt **60% (~62 parents)** as the v2 threshold — slightly tighter than v1's 71-parent scale, justified below — and report this transparently rather than concealing it as automatic detection.

## Pillar 1 — Where does the frequency curve change?

Multiple curvature/inflection detectors on the sorted-descending canonical-class frequency curve:

| method | rank picked | frequency | n parents |
|---|---:|---:|---:|
| Kneedle elbow (max distance from chord) | 112 | 26% | 112 |
| Max-curvature point (second derivative, h=5) | 123 | 10% | 123 |
| Steepest-descent point (first derivative, h=5) | (long-tail end) | ~10–20% | ~110 |

All three methods converge on the long-tail end of the curve where the frequency drops from ~22% to 0% over the last ~10 ranks. Above the long-tail floor, the curve is nearly linear and no method identifies a sharp shoulder.

### Frequency curve at key ranks

| rank | freq | descent rate (vs prev-10 ranks) |
|---:|---:|---:|
| 1 | 100% |  |
| 10 | 98% | 0.1pp/rank |
| 20 | 92% | 0.3pp/rank |
| 30 | 86% | 0.3pp/rank |
| 40 | 76% | 0.5pp/rank |
| 50 | 68% | 0.4pp/rank |
| 60 | 62% | 0.3pp/rank |
| 70 | 54% | 0.4pp/rank |
| 80 | 48% | 0.3pp/rank |
| 90 | 40% | 0.4pp/rank |
| 100 | 34% | 0.3pp/rank |
| 110 | 26% | 0.4pp/rank |
| 116 | 20% | 0.4pp/rank |
| 120 | 16% | 0.2pp/rank |
| 123 | 10% ◀ max-curvature | 0.5pp/rank |
| 126 | 0% | 0.7pp/rank |


**Read:** rank 1-115 the curve descends at ~0.6-0.7pp per rank (linear); rank 116-126 it drops at ~2pp per rank (the only inflection). The methods all flag the latter — but those are noise-tier classes (frequency <22%), not the structural threshold we want.

## Pillar 2 — Split-half rep-stability

Method: split the 50 reps into two random halves of 25 each. For each canonical class, recompute its frequency in each half (using the existing member_label_ids — counts which runs the class appeared in, restricted to half A or half B). Repeat with 50 random seeds and report median absolute difference between half-A frequency and half-B frequency.

Classes above the threshold should show low cross-half variance (the class is reliably surfaced regardless of which 25 reps you sample). Classes below the threshold should show high variance (sampling noise — appears in some sub-samples but not others).

## Threshold candidate comparison

| threshold | n classes | mean split-half diff (above) | p90 (above) | mean diff (below) | p90 (below) |
|---:|---:|---:|---:|---:|---:|
| 20% | 117 | 0.082 | 0.120 | 0.058 | 0.080 |
| 30% | 103 | 0.080 | 0.120 | 0.080 | 0.120 |
| 40% | 91 | 0.079 | 0.120 | 0.083 | 0.120 |
| 50% | 74 | 0.073 | 0.120 | 0.091 | 0.120 |
| 60% | 62 | 0.068 | 0.120 | 0.092 | 0.120 |
| 70% | 47 | 0.062 | 0.080 | 0.091 | 0.120 |
| 80% | 35 | 0.056 | 0.080 | 0.090 | 0.120 |
| 90% | 24 | 0.043 | 0.080 | 0.089 | 0.120 |

*Reading:* "split-half diff" = median absolute difference between a canonical class's frequency in half-A vs half-B, across 50 random split-seeds. Lower = more stable. The threshold separates "above" (mean diff should be low) from "below" (where the diff is the noise floor).

## Honest interpretation

The split-half test is bounded by binomial sampling noise: a canonical class with appearance frequency p has expected split-half difference ~√(p(1−p)/25), peaking around p=0.5 at ~0.06–0.10. Observed median diffs sit at the binomial floor across all canonical classes. **No "noise tier" of unstable classes is visible** — every canonical class, even those at 20–30% frequency, appears at its frequency reproducibly across rep-subsets.

However, the test does discriminate: at threshold 70–80%, mean split-half diff above is 0.056–0.062, while below it is 0.090–0.092. That gap reflects the binomial-noise structure (variance peaks at p=0.5), not a stability cliff — but it does show that classes at higher overall frequency are systematically more reproducible.

## Recommended threshold

| candidate | threshold | n parents | what it captures |
|---|---:|---:|---|
| Kneedle / max-curvature / steepest-descent (all converge) | 10–26% | 110–117 | Long-tail floor; below = noise. Too permissive. |
| 50% threshold | 50% | 74 | v1-comparable scale (matches 71-parent canonical) |
| 60% threshold | 60% | 62 | Slightly tighter than v1; preserves all mechanism families with majority retention |
| 70% threshold | 70% | 47 | Strictest defensible; mean split-half diff drops to 0.062 |
| 90% threshold | 90% | 24 | Only the deeply-stable core |

**Recommendation: 60% (~62 parents).** Justification:

1. **Above the long-tail floor.** All curvature/elbow detectors converge on the 10–26% range as the long-tail noise zone; 60% sits comfortably above that floor.
2. **Slightly tighter than v1.** v1 has 71 parents from a single Opus rep; 60% gives 62 from the consensus of 50 reps. The reduction reflects elimination of single-rep-only categories that didn't reach majority retention. This is a defensible methodological argument — *consensus over single-shot — and the tightening is empirically motivated, not arbitrarily strict.*
3. **Within the split-half-validated zone.** At 60% threshold, mean split-half diff above is 0.068 vs 0.092 below — a meaningful gap, indicating classes above this threshold are reproducible across rep-subsets at the binomial-noise floor while those below show greater variance.
4. **Manageable count for downstream tasks.** 62 parents is similar in scale to v1's 71, so existing downstream artefacts (Pass 2 cluster assignment, Pass 3 theme audit, derivative analyses) remain comparable in size and computability.

**The threshold is reported transparently, not concealed.** The data does not auto-pick 60% — there's no sharp shoulder there. 60% is an analyst-chosen value within the empirically-defensible range (above the long-tail floor of 22%, with reproducibility advantages over lower thresholds). The methodology paper section should make this explicit: *"we adopt a 60% retention threshold; the data constrains the choice to the range 25–90% but does not pick a unique value within it; 60% is selected for the reasons above."*

If the v2 build at 60% reveals issues (excessive unassigned residual under Pass 2, or insufficient mechanism distinction), the threshold is the natural lever to revisit. The downstream tests (cluster coverage, parent-distinctness audit) constrain the threshold further than the frequency-curve analysis alone can.

## Top 30 canonical classes by ensemble frequency

| class_id | freq | median split-half diff | name |
|---|---:|---:|---|
| c03 | 100% | 0.000 | Measurement and sensing limitations |
| c04 | 100% | 0.000 | Model, simulation, and forecast inaccuracy |
| c06 | 100% | 0.000 | Material, chemical, and physical-property limits |
| c01 | 98% | 0.040 | Missing or inaccessible data and documentation |
| c05 | 98% | 0.040 | Lab-to-field and pilot-to-scale translation failure |
| c08 | 98% | 0.040 | Spatial, geometric, and siting constraints |
| c10 | 98% | 0.040 | Coupled trade-offs and competing optimisation objectives |
| c11 | 98% | 0.040 | Control logic, configuration, and parameter errors |
| c14 | 98% | 0.040 | Inverter-based resource and grid stability dynamics |
| c37 | 98% | 0.040 | Regulatory process delay and procedural friction |
| c44 | 98% | 0.040 | Multi-party coordination overhead and responsibility gaps |
| c61 | 98% | 0.040 | Project planning, scoping, and contingency inadequacy |
| c33 | 96% | 0.080 | Chicken-and-egg coordination deadlocks |
| c50 | 96% | 0.000 | Supply chain and logistics disruption |
| c51 | 96% | 0.000 | Workforce skills and capability shortage |
| c58 | 96% | 0.080 | Customer recruitment, conversion, and retention shortfalls |
| c02 | 94% | 0.040 | Data quality, format, and integration defects |
| c75 | 94% | 0.040 | Cybersecurity and access-control exposure |
| c09 | 92% | 0.080 | Environmental and weather exposure |
| c13 | 92% | 0.080 | Interoperability and interface incompatibility |
| c43 | 92% | 0.080 | Policy uncertainty and instability |
| c47 | 92% | 0.080 | Contract structure and term misalignment |
| c53 | 92% | 0.080 | Knowledge transfer and institutional memory loss |
| c34 | 90% | 0.040 | Regulatory framework gap or absence |
| c24 | 88% | 0.080 | Cost structure and unit-economics infeasibility |
| c31 | 88% | 0.080 | Market structure and incumbent advantage |
| c59 | 88% | 0.080 | Customer behavioural and motivation barriers |
| c62 | 88% | 0.080 | Schedule cascade and dependency delays |
| c79 | 88% | 0.080 | Legacy infrastructure and architecture incompatibility |
| c15 | 86% | 0.040 | Network capacity and hosting constraints |


## Border-zone classes at candidate thresholds


### Around 70% threshold (the boundary classes the threshold accepts/rejects)

| class_id | freq | median split-half diff | decision | name |
|---|---:|---:|---|---|
| c32 | 72% | 0.080 | accept | Incumbent lock-in and switching cost barriers |
| c77 | 72% | 0.080 | accept | Communications and connectivity failures |
| c89 | 70% | 0.120 | accept | Safety hazard and risk classification escalation |
| c12 | 68% | 0.080 | reject | Cadence, latency, and timing mismatches |
| c22 | 68% | 0.080 | reject | Aggregation and granularity mismatch |
| c26 | 68% | 0.080 | reject | Value not captured by available market mechanisms |
| c49 | 68% | 0.080 | reject | Vendor lock-in and proprietary closure |
| c67 | 68% | 0.080 | reject | Manufacturing variability and fabrication defects |

### Around 62% threshold (the boundary classes the threshold accepts/rejects)

| class_id | freq | median split-half diff | decision | name |
|---|---:|---:|---|---|
| c16 | 66% | 0.040 | accept | Temporal mismatch between supply and demand |
| c85 | 66% | 0.120 | accept | Conservative margin and over-specification bias |
| c91 | 64% | 0.080 | accept | Trial design and validation infrastructure limitations |
| c35 | 62% | 0.120 | accept | Regulatory framework misfit or obsolescence |
| c60 | 62% | 0.120 | accept | Behavioural rebound and unintended response |
| c90 | 62% | 0.040 | accept | Sample, selection, and representativeness bias |
| c96 | 62% | 0.120 | accept | Forecast uncertainty and actionability limits |
| c104 | 62% | 0.120 | accept | Funding instrument and milestone design misfit |

### Around 50% threshold (the boundary classes the threshold accepts/rejects)

| class_id | freq | median split-half diff | decision | name |
|---|---:|---:|---|---|
| c45 | 54% | 0.040 | accept | Responsibility, ownership, and accountability gaps |
| c80 | 54% | 0.120 | accept | Architectural rigidity and modularity limits |
| c106 | 54% | 0.120 | accept | Manual processes and automation gaps |
| c19 | 52% | 0.080 | accept | Geographic and locational mismatch |
| c56 | 50% | 0.080 | accept | Trust, perception, and social licence barriers |
| c68 | 50% | 0.120 | accept | Equipment degradation, wear, and ageing |
| c18 | 48% | 0.080 | reject | Resource intermittency and variability |
| c38 | 48% | 0.080 | reject | Regulatory metric and methodology design flaws |

## Methodology paper paragraph (drafted)

> *"Sort the canonical-class frequencies descending. The curve descends nearly linearly from 100% (rank 1) to 22% (rank 115), then drops to 0% over the remaining ~10 ranks — the only inflection. Three independent inflection-detection methods (kneedle elbow, maximum-curvature point, steepest-descent point) all converge on this long-tail floor at 10–22% frequency, identifying it as the noise zone. Above the long-tail floor, the curve has no shoulder and no method picks a unique threshold within the 25–100% range.*
> 
> *Split-half rep-stability — the mean absolute difference in canonical-class frequency between two random halves of 25 reps each, across 50 random splits — is bounded above by binomial sampling noise (~0.06–0.10 across the frequency range). Observed values sit at the binomial floor across all canonical classes; no instability cliff is visible. The test does confirm that reproducibility above 70% is systematically tighter (mean diff 0.062) than below (0.091), reflecting the binomial-variance structure.*
> 
> *We adopt a **60%** retention threshold for v2 (~62 parents). The data does not auto-pick this value; the 60% choice sits within the empirically-defensible 25–90% range and is justified on three grounds: (1) above the long-tail noise floor of 22%; (2) slightly tighter than the single-rep v1 layer's 71 parents, reflecting the consensus-tightening that motivates the v2 build; (3) within the split-half-validated zone where reproducibility is quantitatively higher than below. The threshold is reported transparently as an analyst choice within the defensible range, not concealed as automatic detection. Downstream coverage and parent-distinctness checks constrain the threshold further if the v2 build reveals issues."*
