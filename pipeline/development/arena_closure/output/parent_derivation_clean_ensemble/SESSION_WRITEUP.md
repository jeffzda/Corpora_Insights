# v2 extended parent taxonomy
## Session writeup — 2026-05-05 / 06

## TL;DR

86-parent extended v2 taxonomy + 16-theme hierarchy over 1,141 ARENA mechanism clusters. Ensemble-derived (59 reps) at ≥40% rep agreement. Replaces the original v1 single-pass 71-parent set. Each parent has provenance: source tier (core / high / boundary), n_reps_min, source class IDs.

Total cost: **$4.84** across 6 LLM passes.

For the ANAO generalisability demo run as part of the same session, see `corpora/anao/n100_demo/notes.md`.

---

## Pipeline

| pass | input | output | cost | wall |
|---|---|---|---|---|
| 1. Consolidation | 43 core (≥90% rep) + 28 high-tier (70-89%) classes from 59-rep ensemble | 43 core + 27 promoted high-tier = 70 v2 parents (1 high-tier merged into p19) | $0.39 | 152s |
| 2. v1↔v2 coverage audit | v1 71-parent set, original v2 70-parent set | 8 v1-flagged "missing", 9 v2-flagged "new" | $0.41 | 158s |
| 3. Boundary-tier extension | 26 boundary classes (40-69% rep agreement) | 16 promote, 9 merge, 1 reject (13 unique new parents) | $0.17 | 67s |
| 4. Extended consolidation | 43 core + 27 high-promoted + 16 boundary-promoted = 86 classes | 86 unified parent definitions (canonical names + descriptions + criteria) | $0.63 | 226s |
| 5. Pass 2 (cluster→parent) | 1,141 v2 mechanism clusters | 1,141/1,141 placed; 502 high / 632 medium / 7 low confidence | $2.29 | 809s |
| 6. Pass 3 (theme audit) | 86 parents + 1,141 assignments | 86/86 keep verdict (85 tight, 1 mixed); 16 themes; 0 unthemed | $0.95 | 114s |
| **Total** | | | **$4.84** | ~30 min |

---

## Key results

### Parent set structure

86 parents thematically ordered by Pass 3 into 16 themes covering 14 mechanism families:
- **t01** Information and observability failures (6 parents)
- **t02** Analytical, modelling, inferential failures (6)
- **t03** Validation, verification, translation gaps (4)
- **t04** Physical and resource constraints (4)
- **t05** Saturation, residuals, diminishing returns (2)
- **t06** Asset-level performance and physical-input failures (5)
- **t07** External environment and hazard exposure (4)
- **t08** Power-system and grid-coupling failures (4)
- **t09** Control, communication, and integration failures (7)
- **t10** Architecture, dependency, aggregate-structure fragility (5)
- **t11** Financial, capital, and economic-viability failures (11)
- **t12** Regulatory and policy failures (11)
- **t13** Inter-party coordination and incentive failures (5)
- **t14** User, behavioural, and social-licence failures (5)
- **t15** Workforce and operational-process failures (3)
- **t16** Project execution and planning failures (4)

### Provenance per parent

Each parent records source tier, n_reps_min, and source class IDs. Provenance defends each inclusion against a "single-pass arbitrariness" challenge — every parent has a documented rep-agreement signal anchoring it.

### v1↔v2 coverage scorecard

- v1 (71 parents) → original v2 (70): 8 mechanisms flagged as missing in v2 by audit
- After boundary extension: 6 of 8 plugged or subsumed; 2 unplugged (p51 process/reactor design, p53 long-term reliability) but both were singleton/rare-tier in the ensemble — defensibly excluded by methodology, not by oversight
- v2 extended adds **22 mechanisms v1 lacked**: price volatility, hard-to-abate residuals, technology immaturity, observability, subsurface characterisation, procurement pathologies, regulatory misfit with current reality, configuration drift, schedule cascade, EoL/circularity, granularity mismatch, accountability gaps, commissioning discovery, lock-in/stranding, curtailment/headroom, scale-disproportionate compliance, computational tractability, legacy infrastructure incompatibility, key-person dependency, DR/aggregator delivery, automation gaps

### Headline corpus-level findings

**p07 Model and forecast representational error is the largest mechanism by corpus weight** (151 records, 50 clusters). Misrepresentation — not material limits, not coordination, not regulatory failure — is the dominant ARENA failure mode by absorption rate. p18 material/chemical limits is second (147 / 49). p83 planning inadequacy is third (118 / 39).

**Boundary-tier rescue: p60.** "Regulatory framework misalignment with current reality" was nearly rejected by the ensemble (24/59 reps = 41%, just above the 40% boundary threshold). It turned out to be the 8th-largest parent by corpus weight (75 records, 24 clusters). Without the boundary-tier extension, those records would have been forced into adjacent ill-fitting parents. **Single-pass v1 derivation would not have surfaced this.** This is the strongest defence of the ensemble methodology in the v2 set.

**Distinguishing pairs preserved.** The model deliberately kept three close-but-distinct pairs that v1 conflated:
- p48 capital-cost-barrier (3 records) vs p50 unit-economics-infeasibility (73 records) — the splitting was vindicated by population: the actual recurring failure is "the LCOE is structurally too high," not "they couldn't raise the cap-ex"
- p42 architectural-rigidity vs p43 legacy-infrastructure — different mechanism: design-choice vs embedded-prior-asset
- p55 vendor-lock-in vs p56 stranded-asset-risk — supplier closure vs path-dependent capital exposure

---

## Files

### Outputs (in this directory)
| file | content |
|---|---|
| `v2_parents_extended.{json,md,html}` | **86 parent definitions (canonical)** |
| `cluster_to_parent_assignments_v2_extended.jsonl` | 1,141 cluster→parent assignments |
| `themes_and_parent_audit_v2_extended.json` | 16 themes + per-parent audit |
| `cluster_to_parent_assignments_v2_extended_meta.json` | Pass 2 cost/token/distribution meta |
| `themes_and_parent_audit_v2_extended_meta.json` | Pass 3 cost/token/distribution meta |
| `v2_parents.{json,md,html}` | original 70-parent set (predecessor; superseded) |
| `v2_boundary_extension.{json,md,html}` | boundary-tier judgement |
| `v1_v2_coverage_audit.{json,md,html}` | v1↔v2 audit |
| `parsed_runs.jsonl` | 59-rep ensemble parsed |
| `ensemble_aggregate.json` | class tier counts and rep-frequency stats |
| `*.raw.txt` | raw LLM responses (debug) |

### Code (in `corpora/arena/clustering_v2/closure/code/`)
| script | role |
|---|---|
| `36_parent_derivation_clean.py` | single-rep derivation (rep_01 of 59) |
| `37_parent_derivation_clean_ensemble.py` | reps 02-10 batch |
| `38_parent_derivation_clean_extension.py` | reps 11-59 batch |
| `39_v2_consolidation.py` | core + high-tier consolidation |
| `40_v1_v2_coverage_audit.py` | v1↔v2 audit |
| `41_v2_boundary_extension.py` | boundary-tier judgement |
| `42_v2_extended_consolidation.py` | unified 86-parent definitions |
| `43_assign_clusters_v2_extended.py` | Pass 2 cluster→parent |
| `44_themes_audit_v2_extended.py` | Pass 3 theme audit |

### Prompts (in `corpora/arena/clustering_v2/closure/prompts/`)
- `parent_derivation_clean.md` — deliberation-rich PM-purpose derivation prompt
