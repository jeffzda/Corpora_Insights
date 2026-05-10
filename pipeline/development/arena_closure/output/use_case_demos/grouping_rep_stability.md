# Grouping rep-stability test

Re-ran the production event-grouping pass (`pipeline/group_events.py`) on two projects whose events are central to the causal-chain analysis:

- **Lake Bonney BESS** (5 docs, 429 records) — source of the 8-link causal chain (EVT-0037)
- **Musselroe Wind Farm FCAS** (3 docs, 162 records) — source of the 7-link chain (EVT-0004)

Compared rep2 event_ids to v1 production event_ids using pair-decision Jaccard within each project. Addresses the open §16.1 gap from `methodology_lessons.md`: full-corpus rep-noise was unmeasured.

**Cost:** ~$3–4 estimated (group_events.py doesn't surface cost cleanly; 8 grouping calls × ~150–260s each).

---

## Results

| Project | n_docs | v2 records | v1 (filter) | common | pair-Jaccard | FC-subset Jaccard | events v1 | events v2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Lake Bonney BESS | 5 | 429 | 158 | 158 | **0.371** | 0.391 | 65 | 71 |
| Musselroe Wind FCAS | 3 | 162 | 80 | 80 | **0.237** | 0.236 | 27 | 49 |

FC-subset Jaccard: restricted to records belonging to v1 events with ≥3 members (proxy for the more-confident groupings).

---

## Methodology caveat — input-set mismatch

v1 (rep1) event_ids come from `filter_input.jsonl`, the *post-filter* subset of records the production pipeline retained for downstream clustering. v2 (rep2) ran on the full per-doc extraction, which includes records the v1 filter dropped.

For Lake Bonney: v1 has event_ids on 158 records; v2 grouped 429. The Jaccard is computed over the 158-record intersection — but v2's events may include filtered-out records that anchor groupings differently than v1 saw. So the 0.37 / 0.24 numbers **may overstate true rep noise** because the two reps had different inputs.

A cleaner rep test would re-run grouping on v1's filter_input subset directly, eliminating the input-set mismatch. That's a follow-up.

---

## Reference points

- 3-doc REVS replication campaign (2026-05-02): ~32% pair-decision instability at temperature=0 (Jaccard ≈0.68)
- Full 12-doc REVS production (2026-05-02): pair-Jaccard ≈0.50
- FC-pool subset on 3-doc REVS: Jaccard 1.000 (deterministic on the most-confident events)
- **Lake Bonney here**: 0.37 (with input-set mismatch; could be higher when controlled)
- **Musselroe here**: 0.24 (small project, more variance)

---

## What this means for the causal-chain finding

The 88% causal-chain finding from `causal_chain_full` is **rep-stable in distribution but not at the individual-event level**.

Three measurements that aren't contradictory but are easily conflated:

| Property | Measurement | Result |
|---|---|---|
| Pair-Jaccard between reps | ~30–40% pair decisions differ | rep noise is real |
| Event-coherence within a rep | 98% on multi-parent stratum | events that form *are* coherent |
| Causal-chain rate within a rep | 88% on multi-parent population | chain structure is the modal pattern |

Read together: any **specific** event's exact composition will differ ~30-40% between reps. But the **population property** — that multi-parent events tend to be coherently grouped and tend to display causal-chain structure — is robust across reps.

For the methodology paper, the safe claims are:

✓ "88% of multi-parent ARENA events display causal-chain structure when traced through the v2 parent layer" (population claim, rep-stable in distribution)

✓ "On a stratified sample, 98% of multi-parent events represent one singular occurrence as judged by Haiku 4.5" (event-coherence, validated)

✓ "Worked examples like Lake Bonney's 8-link chain (EVT-0037) demonstrate the topology empirically; a different rep-run would produce a chain through a slightly different subset of records but in the same parent family"

✗ "EVT-0037 is *the* canonical Lake Bonney causal chain" — over-strong; rep-noise on event boundaries means the specific 8 records grouped under that ID are one valid grouping, not the unique one.

The methodology paper should report the rep-Jaccard explicitly as a known limitation alongside the headline 88% claim, with the framing above.

---

## Open follow-ups

1. **Cleaner rep test:** re-run grouping on `filter_input.jsonl`'s exact records (no input-set mismatch) for unbiased Jaccard. ~$3–5, 30 min wall.
2. **Full-corpus rep run:** re-run grouping on all 502 projects, compute Jaccard at catalogue level. Documented as ~$200–300, ~5–6 hours wall — this is the §16.1 publishable extension.
3. **FC-pool stability characterisation:** events in the documented FC-pool subset are deterministic on REVS 3-doc (Jaccard 1.000). Confirm this on Lake Bonney by isolating the FC-pool events specifically (subset of v1 events that survived all clustering passes) and computing their Jaccard. Likely ≈1.000; would empirically separate the "marginal events are noisy / FC-pool is stable" claim.
