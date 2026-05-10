# Test snapshot — 2026-05-02 — postextract-grouping-perdoc

> **Headline: ★ recommended production architecture ★**
>
> v1 extraction unchanged. Per-doc post-extract grouping (one Sonnet call per
> doc, seed-doc first, running event registry between docs). REVS: 165 records
> → 47 events; **lowest singleton rate (28%) and highest cross-doc rate (26%)
> of any approach**; all 6 canonical worked-example records on one event;
> $0.56 / 6m wall. Isolated chronological cross-doc accumulation as the
> consolidation lever (within-doc batching is incidental). See
> [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Predecessor:** [`../2026-05-02-postextract-grouping-oneshot/`](../2026-05-02-postextract-grouping-oneshot/) —
> all-records single-call run that lacked chronological anchoring.
> **Successor:** [`../2026-05-02-postextract-grouping-fullrevs/`](../2026-05-02-postextract-grouping-fullrevs/) —
> scale test on the full 12-doc REVS project.

**Architecture variant:** one Sonnet call per source document, processed in
seed-doc-first chronological order, with running event registry passed
between docs. 3 calls total for 165 records on REVS (vs 8 calls for
batched-with-default-batch-size-20). Implemented by reusing the existing
`pipeline/group_events.py` driver with `--batch-size 200` (effectively
making each doc one batch).

This isolates two architectural effects we'd previously confounded:
1. **Within-doc batching** (small batches per doc, current default behaviour)
2. **Cross-doc chronological accumulation** (running event registry passed
   between docs)

**Run results — REVS (3 docs):**

| Doc | Records | Events cumulative | Cost |
|---|---|---|---|
| Crossing Sectors (seed) | 89 | 36 | $0.25 |
| LL2 | 32 | 41 (+5) | $0.11 |
| LL1 | 44 | 47 (+6) | $0.20 |
| **Total** | **165** | **47** | **$0.56**, 6m wall |

**Headline result.** Lowest singleton rate (28%) and highest cross-doc rate
(26%) of any approach tested. Records/event mean 3.51 (vs batched 3.75 and
all-records-one-shot 2.62). All 6 canonical worked-example records grouped
on EVT-0005.

**7-way comparison:**

| Approach | Records | Events | r/e | Singleton% | Cross-doc% | Max | Cost |
|---|---|---|---|---|---|---|---|
| v1 extract → v1 dedup | 165 | 141 | 1.17 | 90% | 0% | 6 | — |
| v2 mechanism-coherent extraction | 156 | 56 | 2.79 | 39% | 23% | 14 | $1.17 |
| v2 occurrence-coherent + split rules | 149 | 76 | 1.96 | 57% | 13% | 14 | $1.16 |
| v2 occurrence-merge-permissive | 138 | 64 | 2.16 | 47% | 20% | 9 | $1.12 |
| v1 → post-extract batched (8-call) | 165 | 44 | 3.75 | 32% | 25% | 22 | $0.76 |
| v1 → post-extract one-shot (1-call) | 165 | 63 | 2.62 | 40% | 17% | 8 | $0.45 |
| **v1 → post-extract per-doc (3-call)** | **165** | **47** | **3.51** | **28%** | **26%** | **11** | **$0.56** |

**Architectural finding.** Cross-doc chronological accumulation is the
mechanism producing event consolidation — within-doc batching is incidental.
The one-shot all-records run (no chronological anchoring) produces the
poorest consolidation (63 events, 17% cross-doc); both batched runs that
process docs sequentially with running event registry produce ~46-47 events
with ~25-26% cross-doc rate.

**Per-doc one-shot is the right production architecture.** It captures the
chronological-accumulation benefit while avoiding within-doc fragmentation
that arises from sub-doc batching. Per-doc gives:
- Lowest singleton rate (28%)
- Highest cross-doc rate (26%)
- Records/event near the batched best (3.51 vs 3.75)
- 26% cheaper than batched, 24% more than all-shot
- Granular but still cross-doc-coherent event decomposition: the Wallbox
  cert constellation breaks into 8 events including a 10-record cross-doc
  cert event + an 11-record cross-doc FCAS-slow-raise event + 6 smaller
  sub-events. Arguably more plausible than the batched 22-record umbrella
  which may over-merge.

**Files snapshotted:**
- `code/group_events.py` — batched driver, used at --batch-size 200 to make
  each doc one effective batch
- `code/group_events.md` — grouping prompt (shared across batched, per-doc,
  and one-shot runs)
- `outputs/revs/doc_*.assignments.json` — per-record event_id assignments
- `outputs/revs/doc_*.events.json` — running event registries

**Recommendation.** This is the architecture for ANAO and the methodology
paper. v1 grave-prompt extraction (unchanged) → per-doc post-extract
grouping in seed-doc-first chronological order with `--batch-size 200` →
mechanism clustering. The orthogonality between event-axis and mechanism-axis
is preserved by design; the worked example's "one event spans multiple
clusters" property holds (EVT-0005 spans multiple mechanism families).
