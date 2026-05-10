# Documented gap: cluster signatures drift from membership

> **Status: known methodology gap, not fixed in v2 substrate.** Identified during
> boundary-mapping analysis on 2026-05-09. Affects interpretation of the
> cross-theme adjacency findings.

## What the gap is

Each v2 cluster carries a canonical_name and a mechanism_signature. These were
written **at cluster birth** — when the cluster was first minted by the sweep
algorithm, based on the records present in that founding batch (typically
5-10 records). As reclassification, singleton sweep, and residual passes added
more records to the cluster, the signature **was not updated**.

A cluster with a final membership of 30 records may therefore carry a
mechanism description derived from its first 5-10 members. The signature has
drifted from what the cluster actually represents.

This affects every downstream layer that consumes cluster signatures:

- **Parent-assignment** (s10) — Opus matches cluster *signatures* against parent
  *mechanism criteria*. Drift-affected signatures cause a fraction of medium-
  confidence "selection ambiguity" cases to be ambiguous artificially: the
  cluster's true mechanism (across all members) might cleanly fit one parent,
  but its birth-time signature is broad enough to plausibly fit two.
- **Theme audit** (s11) — operates on parents, so it's one layer removed.
  Indirect impact through parent assignment quality.
- **Boundary mapping** (this directory) — the cross-theme adjacency strengths
  we report are partly real mechanism cousinship and partly signature drift.
  Strong, consistent edges (≥10/10 reps, ≥40 events) are robust to drift; the
  noisy long tail (small-event-count edges) likely contains drift artefacts.
- **Cluster reports** (the c042-style synthesis) — read off the canonical_name
  for narrative framing. Birth-signature names occasionally don't capture the
  cluster's full breadth (e.g. a cluster founded by one technology may receive
  records from neighbouring technologies during reclassification).

## Why it happened

The sweep architecture (200-record batches, sequential state) treats cluster
catalogue maintenance as monotonic-add: new records come in, catalogue grows,
existing entries are not revisited. This was a deliberate cost choice — re-
synthesising signatures every batch would have multiplied the per-iteration
cost. The trade-off was acceptable for the substrate's primary purpose
(producing a stable cluster ID for each record) but creates the drift for
any downstream task that reads signatures as faithful descriptions of
cluster contents.

## What the fix would look like

For each of the 1,141 clusters in the v2 catalogue, run a one-shot Opus call
that takes the cluster's full member record set and re-derives:

- canonical_name (≤10 words)
- mechanism_signature (1-3 sentences, member-faithful)
- a brief synthesis rationale describing what the records share

Schema is identical to current; only the values change.

Cost estimate (2026-05-09 pricing):
- ~1,141 calls
- Median cluster has ~10-15 records — input ~5-8k tokens including each
  record's narrative + evidence
- Output ~200-400 tokens per cluster
- Per-call sync: ~$0.30 (~$340 total sync); batched: ~$170

## Why we're not doing it

Cost. ~$170 is real money for a marginal improvement on a finding that's
already publishable, and the v2 substrate has been in use for two months
without this fix. Adding it now would invalidate prior cluster-report
artefacts (c042 etc) which would need re-running.

## How to interpret current ensemble results given this gap

- **High-confidence assignments stand** — 95.8% of original-high cluster→parent
  assignments hold up under blinded review. High-confidence is robust to
  signature drift because both runs see the same drifted signature and reach
  the same conclusion; if the cluster's true mechanism is consistent with the
  birth signature, both runs converge.
- **Medium-confidence selection-ambiguity finding stands too** — 54.8% of
  medium → blinded high indicates the original was being cautious in a
  multi-option panel. Drift would push these toward more ambiguity, not less,
  so the finding is conservative.
- **Cross-theme adjacency rankings are reliable for the top edges** — p18↔p19
  at 130 events, p83↔p84 at 92 events, etc. Drift can't manufacture 130-event
  bidirectional adjacency from nothing; the strongest edges are real
  mechanism overlap.
- **The long tail (10-30 event count edges) should be discounted** — not
  treated as zero, but reads more like "possible adjacency, drift-affected"
  than "demonstrated adjacency". Specifically the cross-theme bridges in the
  10-15 event range are where drift would most plausibly contaminate.

## Methodological note for the paper

The substrate has a **layer-of-inference dependency**: records → clusters →
cluster signatures → parents → themes. Each layer should ideally be
synthesised from the layer below *after* its membership stabilises. The v2
substrate does this correctly at the parent layer (parents synthesised from
cluster signatures after assignment) and theme layer (themes from parents
after assignment). It skips this step at the **cluster signature layer** —
signatures are written at birth, not after membership stabilisation.

This is a transparent gap to disclose in §16 known limitations: "Cluster
mechanism signatures are derived at cluster minting time and not re-
synthesised after the full membership stabilises. Boundary-mapping
adjacencies in the long tail (≤30 events) may include signature-drift
artefacts. The fix is a $170 batched re-synthesis pass on all 1,141 clusters
followed by a fresh parent-assignment ensemble (~$25). The cost has been
documented but not committed to date."
