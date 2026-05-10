# Test snapshot — 2026-05-01 — occurrence-coherent-grave

> **Headline:** v2 extraction with occurrence-coherent same-event criterion +
> v1-dedup-style explicit MERGE/SPLIT rules. REVS: 149 records → 76 events.
> Counter-intuitively produced *more* singletons than its predecessor — the
> v1-dedup split rules ("different recommendations are typically different
> events") gave the model new reasons to split. See
> [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Predecessor:** [`../2026-05-01-mechanism-coherent-grave/`](../2026-05-01-mechanism-coherent-grave/) —
> had the mechanism conjunct that this run dropped.
> **Successor:** [`../2026-05-02-occurrence-merge-permissive/`](../2026-05-02-occurrence-merge-permissive/) —
> stripped the over-aggressive split rules.

**Prompt change vs predecessor:** dropped `same causal mechanism` from the
same-event criterion. Added explicit MERGE and SPLIT sections borrowed from
`dedup_haiku/prompt_v2.md` (the v1 dedup prompt). Added strong anti-suppression
language. Goal was to reproduce v1 dedup's occurrence-coherent grouping where
aspect-distinct records of one occurrence (cause + mechanism + intervention +
outcome + lesson) all share an event_id, so downstream clustering can surface
the cross-mechanism span as a feature.

**Run results — REVS (3 docs):**

| Doc | Records | Events cumulative |
|---|---|---|
| Crossing Sectors (seed) | 88 | 52 |
| LL2 | 25 | 57 |
| LL1 | 36 | 76 |
| **Total** | **149** | **76** |

**Wallbox Quasar AS/NZS 4777 cert event:** EVT-0010 with **14 records spanning
all 3 docs** — same as the mechanism-coherent run. The headline cross-doc
multi-aspect event is preserved.

**Surprise — overall event distribution moved AWAY from consolidation:**

| | v1 dedup | mechanism-coherent | **occurrence-coherent (this run)** |
|---|---|---|---|
| Records | 165 | 156 | 149 |
| Events | 141 | 56 | **76** |
| Singleton events | 90% | 39% | **57%** |
| Cross-doc events (in ≥2 docs) | 0% | 23% | **13%** |
| Records/event mean | 1.16 | 2.79 | 1.96 |

The new prompt produced **more events** (76 vs 56) and **more singletons** (57%
vs 39%). The explicit SPLIT rules I copied from v1 dedup —
particularly *"Different RECOMMENDATIONS or design decisions on the same
subsystem are typically distinct events"* and *"Generalised principles vs
project-specific occurrences"* — gave the model new reasons to split, partly
counteracting the merge instruction. The user's intuition (events should be
occurrence-coherent multi-record) and the v1 dedup prompt text (which actually
splits aggressively, with v1 corpus-wide singleton rate of 84%) point in
opposite directions.

**Reading.** v1 dedup's *empirical* behaviour on the Wallbox cert (6 records →
1 event) was unusual — most v1 events are singletons. v2 already produces more
multi-record events than v1 under either prompt. The mechanism-coherent v2 run
actually has a *tighter* multi-record event distribution than the
occurrence-coherent run.

**Unresolved.** The "right" prompt depends on what we want: maximum
consolidation (mechanism-coherent), v1-dedup-prompt-text fidelity
(occurrence-coherent + split rules — this run), or something in between
(occurrence-coherent without the SPLIT-aggressive rules). Decision pending.

**Files snapshotted:**
- `code/extract_v2.py` — pipeline driver as run (with httpx retry patch added
  during the run after the first chunk failed mid-stream)
- `code/extract_v2.md` — prompt with occurrence-coherent same-event criterion,
  v1-dedup-style MERGE/SPLIT rules, anti-suppression instruction
- `code/check_v2_coverage.py` — coverage script
- `outputs/revs/` — 3 doc.json + doc.events.json files plus _raw responses

**Anomaly during run.** Doc 704's first call hit
`httpx.RemoteProtocolError: peer closed connection without sending complete
message body` mid-stream (Anthropic API transient issue). Added httpx
exception handling to extract_v2.py's `call_api` retry loop and re-ran;
succeeded on retry. The patched code is in this snapshot's `code/`
directory.

**Coverage check:** not run yet for this run (deferred until prompt design is
finalised).
