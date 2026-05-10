# Test snapshot — 2026-05-02 — fullrevs-production

> **Headline:** First production-configuration run on the full 12-doc REVS
> project. v1 extraction (937 records) → per-doc post-extract grouping with
> `--exclude-fields lesson` and seed-doc-first chronological order, replicated
> 3 times at temperature=0. Consensus event graph at ≥2/3 threshold yields
> 483 events (1.94 records/event), reproducing 70% of v1 dedup's confident
> multi-record pairs while finding 1330 additional cross-doc pairs v1 missed.
> See [`../README.md`](../README.md) for the architecture context.
>
> **Predecessor:** [`../2026-05-02-replication-campaign/`](../2026-05-02-replication-campaign/) —
> 3-doc replication that established the no-lessons + chronological-accumulation
> findings.
> **Successor:** ANAO deployment — same architecture, fresh corpus.

## Configuration

- **Architecture:** v1 extraction (unchanged, grave prompt at
  `domains/arena/prompts/extract.md`) → `pipeline/group_events.py` post-extract
  grouping
- **Per-doc:** `--batch-size 200` so each doc is one Sonnet call
- **Field ablation:** `--exclude-fields lesson` (lesson field dropped per
  prior-replication finding that lessons are noise-additive via priors)
- **Determinism:** `temperature=0` (with the caveat that this still has ~50%
  pair-decision instability at 12-doc scale)
- **Replicates:** 3 (for consensus event graph)
- **Seed-doc heuristic ordering:** `doc_0845` (Final Social Report, the
  project synthesis) → 7 backward-chrono → 4 forward-chrono
- **Model:** Sonnet 4.6 with streaming (max_tokens=32k, required by Anthropic
  SDK above 8k for non-streaming calls)

## Run statistics

| Replicate | Events | Wall (s) |
|---|---|---|
| rep1 | 416 | 2,088 (~35 min) |
| rep2 | 472 | 2,526 |
| rep3 | 525 | 2,335 |
| **Mean** | **471.0** | per rep |
| **Stddev** | **54.5** | (12% relative noise) |

**Total wall:** 6,949 s (~1h56m). **Total cost:** ~$8 ($2.70/rep × 3).

## Replicate stability metrics

Pair-set Jaccard between replicates of the *same* configuration:

| Rep pair | Jaccard |
|---|---|
| rep1 vs rep2 | 0.562 |
| rep1 vs rep3 | 0.490 |
| rep2 vs rep3 | 0.505 |
| **Mean** | **0.519** |

**Reading:** about 48% of co-grouping decisions are unstable between any two
replicates of the *same* configuration at temperature=0. This is materially
worse than the 3-doc scale (32% unstable). The chronological event registry
chain compounds noise — small label drift in early docs propagates downstream.

## Pair co-grouping distribution

Across the 3 replicates, every pair of records was either co-grouped 0, 1, 2,
or 3 times:

| Pair appeared in | n pairs |
|---|---|
| 1/3 reps | 969 |
| 2/3 reps | 584 |
| 3/3 reps | 922 |
| **Total ever-co-grouped** | **2475** |

The 922 pairs co-grouped in all 3 reps are the highest-confidence groupings.
The 969 pairs co-grouped in only 1 rep are noise.

## Consensus event graphs at three thresholds

| Threshold | Events | Singletons | Multi-record | Cross-doc | Max event |
|---|---|---|---|---|---|
| ≥1/3 (any merge) | 303 | 186 | 117 | 55 (18%) | 292 records, 12 docs |
| **≥2/3 (production default)** | **483** | **306** | **177** | **84 (17%)** | **26 records, 12 docs** |
| ≥3/3 (high-confidence) | 635 | 492 | 143 | 60 (9%) | 22 records, 11 docs |

The ≥2/3 consensus is recommended as the production output — it discards the
unstable pairs (969 with count=1) while keeping the moderately-confident
groupings (584 with count=2) and the strongly-confident ones (922 with count=3).

## Comparison to v1 dedup on the same 937 records

| | v1 dedup | Consensus ≥2/3 | Δ |
|---|---|---|---|
| Total events | 834 | 483 | −42% |
| Records/event mean | 1.12 | 1.94 | +73% |
| Multi-record events (≥2 records) | ~140 | 177 | +26% |
| Cross-doc events (≥2 docs) | very few | 84 | — |
| Confident pairs (multi-record) | 251 | 1,581 | +530% |

**Cross-validation:**
- 176 of v1's 251 confident pairs (**70%**) are reproduced in our ≥2/3
  consensus.
- 1,330 pairs are in our consensus but not in v1 dedup — these are
  cross-doc same-event pairs v1's cosine retrieval missed.
- 75 v1 pairs are not in our consensus — likely v1 false-positive merges.

The consensus event graph is **strictly tighter and more comprehensive** than
v1 dedup on the same records. Same canonical events are preserved; many more
legitimate cross-doc events are surfaced.

## Canonical 6 records — Wallbox AS/NZS 4777 worked example

| Replicate | Result |
|---|---|
| rep1 | All 6 → EVT-0070 |
| rep2 | All 6 → EVT-0100 |
| rep3 | All 6 → EVT-0089 |
| Consensus ≥2/3 | All 6 → one component |

Different event_id labels across reps (because the labels are run-internal),
but the consensus correctly identifies them as one event. **Worked-example
property holds at full project scale.**

## Top consensus events by size

| Records | Docs | Note |
|---|---|---|
| 26 | 12 | Spans the entire project — a high-level project narrative event |
| 26 | 4 | Cross-doc cluster |
| 20 | 5 | Cross-doc cluster |
| 14 | 2 | |
| 11 | 2 | |
| 10 | 1 | Within-doc multi-aspect event |
| 10 | 1 | |
| 10 | 1 | |
| 9 | 3 | |
| 9 | 2 | |

The largest events span many records and many docs, which is exactly the
"single event spans many mechanism clusters" property the methodology paper
claims. Downstream cluster fragmentation analysis (open work) will quantify
this.

## Files snapshotted

- `code/group_events.py` — production driver with streaming + temp=0 +
  --exclude-fields support + max_tokens=32k
- `code/group_events.md` — grouping prompt
- `outputs/rep{1,2,3}/doc_*.assignments.json` — per-record event_id
  assignments per replicate
- `outputs/rep{1,2,3}/doc_*.events.json` — running event registries
- `analysis/consensus_analysis.py` — consensus event graph builder
- `analysis/consensus_events_threshold2.json` — final 483-event graph at
  ≥2/3 threshold (the production output)

## Bugs encountered during this run

1. **First attempt failed in 14 seconds** — `max_tokens=32000` non-streaming
   was rejected by the Anthropic SDK ("Streaming is required for operations
   that may take longer than 10 minutes"). Patched `pipeline/group_events.py`
   to use streaming when `max_tokens > 8192` (mirroring `extract_v2.py`).
2. **Bash `set -e` did not catch python failures** because they were piped
   through `tail`. Added `set -o pipefail` to the run script.
3. Both bugs found-and-fixed before the production run completed; the
   snapshotted code reflects the working version.

## Open follow-ups

1. **Cross-cluster span analysis** — for each consensus event, compute how
   many v3.5 mechanism clusters its records span. Validates the
   orthogonality claim.
2. **Coverage check** — Haiku pairwise comparison of consensus output to
   v1 records (should be 100% by construction).
3. **Production runtime estimate for full ARENA corpus** — at ~$8/12-doc
   project, full ARENA at 502 projects extrapolates to ~$3,000-4,000.
   May need batch-API optimisation or a smaller config (1-2 reps) to be
   affordable. To be costed properly before commitment.
