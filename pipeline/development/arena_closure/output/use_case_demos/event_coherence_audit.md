# Event-coherence audit

For a stratified sample of 85 events from the production grouping pass, asked Haiku 4.5 to judge whether the records assigned to each event_id genuinely describe **one singular occurrence**, or whether **multiple distinct occurrences were bundled** into the same event.

This addresses the open production-handoff item #2 from `corpora/arena/canonical/narrative/runs/README.md`: testing grouping quality directly, separate from coverage / record-content fidelity.

**Cost:** $0.10, 94s.

## Strata

| stratum | description | n |
|---|---|---:|
| A_multi_parent | events with ≥4 distinct parent archetypes (population for the causal-chain analysis) | 45 |
| B_medium | 3-5 records, 2-3 parents (control) | 20 |
| C_orthogonal | events the causal-chain test flagged `cluster_of_orthogonal_failures` (testing whether orthogonal verdicts correlate with bad grouping) | 20 |

## Verdict distribution overall

| verdict | n | % |
|---|---:|---:|
| coherent | 80 | 94% |
| partially_coherent | 3 | 4% |
| multiple_occurrences | 2 | 2% |

## Verdict by stratum

| stratum | coherent | partially_coherent | multiple_occurrences |
|---|---:|---:|---:|
| A_multi_parent | 44 (98%) | 1 (2%) | 0 (0%) |
| B_medium | 17 (85%) | 2 (10%) | 1 (5%) |
| C_orthogonal | 19 (95%) | 0 (0%) | 1 (5%) |

## Sample of `multiple_occurrences` verdicts (events flagged as bundled)

### EVT-0015 — Charge Together Phase 2 (stratum: B_medium)

**Inferred occurrences:** 2 · confidence: `high`

**Evidence:** Records 0519-0079, 0519-0097 describe Japan's hydrogen shift and EV supply constraints; record 0519-0111 describes vehicle taxation changes. These are distinct market/policy developments.

### EVT-0059 — Atlas of Pumped Hydro Energy Storage (stratum: C_orthogonal)

**Inferred occurrences:** 2 · confidence: `medium`

**Evidence:** Records 1–3 discuss generic renewable capacity constraints (biomass, wind, hydro availability globally/nationally). Records 4–5 discuss specific Murray-Darling Basin water conflict and bioenergy resource competition. No causal linkage; bundled background analysis.
