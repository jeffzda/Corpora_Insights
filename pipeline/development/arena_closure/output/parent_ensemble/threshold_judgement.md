# Threshold-selection judgement — clean LLM assessment

Single-shot Opus 4.7 judgement on the 126 canonical classes from the 50-rep ensemble. Operates purely on the canonical content; no reference to v1 or any prior parent layer. PM-facing purpose framing in the prompt.

**Cost:** $0.11, 30s.

## Recommendation

**Threshold: 0.34 (=34% if numeric)**

**Classes included: 95**

**Verification:** 100 canonical classes have frequency ≥ threshold.

## Rationale

The frequency distribution descends nearly linearly with no shoulder, so the threshold must be argued on content rather than a natural break. At ≥34%, the included set covers all major mechanism families a PM needs: physical/material limits (c06,c08,c15), data and modelling (c01-c04), market/finance (c23,c24,c27,c28), regulation (c34-c40), social/stakeholder (c55-c57), workforce/coordination (c44,c51,c52), execution/rework (c61-c66), and IBR/grid dynamics (c14,c101). Crucially, it retains low-frequency but coverage-critical classes: c57 community opposition (40%) is structurally distinct from c56 trust; c82 first-of-kind (34%) and c74 subsurface uncertainty (34%) name mechanisms with no near-substitute; c108 external shocks (36%) and c107 stranded-asset risk (40%) cover risks PMs explicitly assess. Below 34%, classes either narrow into specialist sub-mechanisms (c118,c123 inverter-internal; c74 already retained), duplicate retained parents (c64 scope change vs c63 late discovery; c116 iterative rework vs c64; c66 site conditions vs c63), or fragment risk types already covered (c102 tail events ⊂ c41/c91; c110 gaming ⊂ c40). 95 parents is large but scannable when grouped; cutting further would create coverage gaps more harmful than navigation cost.

## Borderline classes

| class | freq | verdict | reason |
|---|---:|---|---|
| c57 | 40% | include | Active community opposition is a distinct binding mechanism PMs must assess separately from generic trust deficit (c56); excluding would create a visible blind spot. |
| c82 | 34% | include | First-of-kind premium is a structurally real, frequently-cited risk for ARENA's innovation-stage portfolio with no substitute parent in the retained set. |
| c74 | 34% | include | Subsurface characterisation uncertainty is domain-specific (geothermal/CCS/hydrogen storage) and not subsumed by c83 or c04; PM coverage requires it. |
| c115 | 34% | include | Standardisation absence is distinct from c42 (standards mismatch) — it captures the bespoke-effort cost of no standard at all, a real PM-facing barrier. |
| c71 | 32% | exclude | Process chemistry limits are largely subsumed by c06 (material/chemical/physical-property limits); marginal distinction does not justify inclusion below threshold. |
| c39 | 30% | exclude | Compliance burden disproportion overlaps materially with c37 (procedural friction) and c34 (framework gap); the structural distinction is too fine for a navigable diagnostic vocabulary. |

## Notes

Single-threshold caveats: (1) Redundancy persists ABOVE the threshold — c63 (late discovery), c64 (scope change), c66 (site conditions late), and c116 (design churn) are near-duplicates; c56/c57 and c34/c35/c36/c38 also cluster tightly. A consolidation pass could reduce 95→~75 without coverage loss. (2) Two below-threshold classes deserve discretionary inclusion despite the cutoff: c102 rare-event/tail exposure (16%) and c110 gaming/self-reporting weakness (16%) name mechanisms a PM would plausibly need vocabulary for; consider promoting via override. (3) c118 and c123 are genuinely specialist (inverter-internal) and appropriately excluded — they belong in a child layer beneath c14/c101, not as parents. (4) The 22% floor before the cliff to 0% suggests the canonicalisation pass already filtered noise; classes 14-22% are mostly real but narrow. The 34% threshold is defensible but the analyst should expect to apply 5-10 manual overrides (both promotions and demotions) rather than treat the cutoff as final.
