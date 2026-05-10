# Test snapshot — 2026-05-02 — occurrence-merge-permissive

> **Headline:** v2 extraction with occurrence-coherent + strong-merge instructions
> and split-aggressive rules removed. REVS: 138 records → 64 events. Split the
> Wallbox cert story across 8 separate events (max event size 9). Surfaced the
> orthogonality confound — extraction yield was changing with grouping policy,
> revealing the architectural problem with bundling extraction and grouping.
> See [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Predecessor:** [`../2026-05-01-occurrence-coherent-grave/`](../2026-05-01-occurrence-coherent-grave/) —
> had the v1-dedup split rules that this run stripped.
> **Successor:** [`../2026-05-02-postextract-grouping/`](../2026-05-02-postextract-grouping/) —
> first decoupled-extraction-from-grouping run.

**Prompt change vs predecessor (occurrence-coherent-grave):** kept the
occurrence-coherent same-event criterion (no mechanism conjunct) but stripped
the v1-dedup-style aggressive SPLIT rules. Specifically removed:
- "Different RECOMMENDATIONS or design decisions on the same subsystem are typically distinct events"
- "Generalised principles vs project-specific occurrences are different events"
- The standalone "Different MAGNITUDES" rule

Replaced with stronger MERGE language including "Recommendations or design
suggestions arising from an occurrence merge with that occurrence" and
"Specification + finding about specified equipment merge."

**Run results — REVS (3 docs):**

| Doc | Records | Events cumulative |
|---|---|---|
| Crossing Sectors (seed) | 85 | 51 |
| LL2 | 23 | 54 |
| LL1 | 30 | 64 |
| **Total** | **138** | **64** |

**Result vs prior runs:**

| | Records | Events | Records/event | Singleton% | Cross-doc% | Max event |
|---|---|---|---|---|---|---|
| v1 dedup | 165 | 141 | 1.17 | 90% | 0% | 6 |
| mechanism-coherent | 156 | 56 | 2.79 | 39% | 23% | **14** |
| occurrence-coherent + v1 split rules | 149 | 76 | 1.96 | 57% | 13% | 14 |
| **occurrence-merge-permissive** (this run) | **138** | **64** | **2.16** | **47%** | **20%** | **9** |

**Surprising finding.** The merge-permissive prompt produced *less* consolidated
events than the original mechanism-coherent prompt. The Wallbox certification
narrative split across **8 distinct events** under this prompt, vs **12 events
of which one had 14 records** under mechanism-coherent. The largest event
under merge-permissive has 9 records (vs 14 under mechanism-coherent).

**Why.** The model interprets "same singular occurrence" more narrowly when
given an occurrence-only criterion than when given a mechanism conjunct. With
the mechanism conjunct, the model groups by mechanism family (e.g. "all things
about AS/NZS 4777 mismatch with overseas standards") and merges aspect-distinct
records under that family. Without the mechanism conjunct, the model treats
"the cert process," "the slow FCAS response," "the EU/UK comparison," "the
classification problem" as separate occurrences within the certification story
— each gets its own event_id even though they're all consequences of the
same underlying AS/NZS 4777 mismatch.

**Empirical conclusion.** The mechanism-coherent prompt — which I'd flagged as
problematic because of theoretical concern about cross-cluster span — actually
produces the *best* aggregation of the three prompt variants tested. Its
"same causal mechanism" criterion is interpreted by the model as "same broad
causal driver," which produces tight multi-record events that *do* span multiple
mechanism families when grouped by record content. The 14-record certification
event under that prompt covers vendor-capability, regulatory-framework,
skills-gap, and physical-EMC mechanisms — exactly the cross-mechanism span the
methodology paper wants.

**Files snapshotted:**
- `code/extract_v2.py` — pipeline driver as run
- `code/extract_v2.md` — merge-permissive prompt
- `code/extract_v2.md.predecessor` — occurrence-coherent + v1 split rules prompt
  (the version this run iterated from)
- `code/check_v2_coverage.py` — coverage script
- `outputs/revs/` — 3 doc.json + doc.events.json files plus _raw responses

**Coverage check:** not run for this run.

**Recommendation.** Revert to the mechanism-coherent prompt for ANAO and
methodology paper. The empirical case for it is now strong: it produces the
best multi-record events while still preserving cross-mechanism span when the
records cover multiple mechanism aspects of one occurrence.
