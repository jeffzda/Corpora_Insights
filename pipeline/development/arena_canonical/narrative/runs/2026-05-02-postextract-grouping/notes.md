# Test snapshot — 2026-05-02 — postextract-grouping

> **Headline:** First decoupled run. v1 extraction unchanged; new grouping pass
> at `pipeline/group_events.py` operating on already-extracted records, batched
> ~20 records per LLM call (8 calls on REVS 3-doc). REVS: 165 records → 44
> events, max event size 22, 25% cross-doc rate. All 6 canonical worked-example
> records on one event. Validated the decoupled architecture as the right
> direction. See [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Predecessor:** [`../2026-05-02-occurrence-merge-permissive/`](../2026-05-02-occurrence-merge-permissive/) —
> last v2-extraction-time-grouping run before decoupling.
> **Successor:** [`../2026-05-02-postextract-grouping-oneshot/`](../2026-05-02-postextract-grouping-oneshot/) —
> tested whether one-shot beats batched (it didn't).

**Architecture change:** separated extraction from event grouping. Inputs are
v1's already-extracted records (`corpora/arena/output/per_doc/doc_{0844,1347,1348}.json`).
The new `pipeline/group_events.py` driver + `pipeline/prompts/group_events.md`
prompt operate as a downstream pass: read records + project's running event
registry, batch them ~20 per LLM call, emit per-record event_id assignments
plus updated registry.

This tests the orthogonality hypothesis the user surfaced: extraction yield
should be invariant to event-grouping policy. v2's prompt variants all
conflated extraction selectivity with grouping rules, producing different
record counts (138, 149, 156). Separating the two concerns isolates the
grouping decision.

**Run order (seed-doc heuristic):** Crossing Sectors → LL2 → LL1.

**Run results — REVS (3 docs):**

| Doc | Records | Events cumulative |
|---|---|---|
| Crossing Sectors (seed) | 89 | 33 |
| LL2 | 32 | 35 (+2) |
| LL1 | 44 | 44 (+9) |
| **Total** | **165** | **44** |

**Cost:** $0.76 ($0.44 + $0.13 + $0.19), 8 batches over 3 docs.

**Headline result.** All 6 canonical worked-example records mapped to one
22-record event (EVT-0005) spanning all 3 docs. Downstream clustering will
fragment EVT-0005's 22 records across 4+ mechanism clusters — exactly the
"one event spans 4 clusters" finding the methodology paper claims.

**Comparison across 5 approaches (same REVS 3-doc data):**

| Approach | Records | Events | r/e | Singleton% | Cross-doc% | Max event |
|---|---|---|---|---|---|---|
| v1 extract → v1 dedup | 165 | 141 | 1.17 | 90% | 0% | 6 |
| v2 mechanism-coherent | 156 | 56 | 2.79 | 39% | 23% | 14 |
| v2 occurrence-coherent + v1 split rules | 149 | 76 | 1.96 | 57% | 13% | 14 |
| v2 occurrence-merge-permissive | 138 | 64 | 2.16 | 47% | 20% | 9 |
| **v1 extract → post-hoc grouping** (this) | **165** | **44** | **3.75** | **32%** | **25%** | **22** |

Post-extract grouping wins on every axis: most records preserved, tightest
event graph, largest multi-record events, highest cross-doc rate, lowest
singleton rate, cheapest overall.

**Why this works.** When grouping runs on already-extracted records, the LLM
sees a batch of 20 records together and reasons about which describe the same
occurrence using their full content. Extraction-time grouping forces
one-record-at-a-time decisions while the model is also generating records,
and those two decisions interfere — this is the source of the v2 prompt
variants' different record counts.

The user's earlier concern that "atomic records don't capture all the context
that could help inform grouping" empirically didn't materialise: narrative +
lesson + evidence + intervention is enough signal for the grouping pass to
produce coherent multi-record events that include aspect-distinct records
(cause + mechanism + intervention + outcome + lesson + recommendation).

**Files snapshotted:**
- `code/group_events.py` — new grouping driver
- `code/group_events.md` — grouping prompt (occurrence-coherent merge-permissive
  framing, identical philosophy to the prompt that under-performed when used
  for extraction-time grouping)
- `code/extract_v2.py` + `code/extract_v2.md.predecessor` — for reference; this
  run uses v1 extraction output, not v2 extraction
- `code/check_v2_coverage.py` — for reference; coverage not yet run
- `outputs/revs/doc_*.assignments.json` — per-record event_id assignments
- `outputs/revs/doc_*.events.json` — running event registries

**Recommendation.** This is the architecture for ANAO and the methodology
paper. v1's grave-prompt extraction stays unchanged; the post-hoc grouping
pass replaces both v1 dedup AND v2's extraction-time event-identity scheme.
The orthogonality between event-axis (groupings) and mechanism-axis (failure
clusters) is preserved by design.
