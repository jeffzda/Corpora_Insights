# Test snapshot — 2026-05-01 — mechanism-coherent-grave

> **Headline:** v2 extraction on grave prompt with mechanism conjunct in
> same-event criterion. REVS: 156 records → 56 events, max event size 14.
> First successful v2 build but the mechanism conjunct contaminated extraction
> selectivity (records-per-event coupled to grouping policy). See
> [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Sequence:** First in test series.
> **Successor:** [`../2026-05-01-occurrence-coherent-grave/`](../2026-05-01-occurrence-coherent-grave/) —
> dropped the mechanism conjunct.

**Prompt design:** the v2 prompt's same-event criterion required *"same actors,
same time-window, same physical/organisational locus, same causal mechanism."*
The "same causal mechanism" conjunctive criterion makes v2 events
**occurrence-AND-mechanism-coherent**.

**Effect on Wallbox Quasar / REVS:** the 6 v1 dedup records that mapped to one
canonical occurrence-coherent event (`ARENA-DLV-1348-0029`, the AS/NZS 4777
certification challenge) decompose under v2 into **12 distinct events** spanning
the same overall story: cert process (EVT-0011), COVID compounder (EVT-0007),
slow-raise FCAS constraint (EVT-0012), first/only certified milestone
(EVT-0084), EV-as-stationary-battery earthing mismatch (EVT-0085), ferrite EMC
fix (EVT-0086), various recommendations (EVT-0087, 0090, 0091, 0093), PAJ
testing findings (EVT-0094), DERlab methodology (EVT-0095), JET Charge 14s
delay (EVT-0092).

**Why this is wrong (per user feedback):** the methodology paper's worked
example specifically highlighted that the 6 v1 records of the cert challenge
*spanned 4 mechanism clusters* — that cross-cluster span was the headline
finding showing why occurrence-axis retrieval matters. v2's mechanism-coherent
extraction destroys that property by collapsing each mechanism family into its
own event before clustering ever runs. The v1 dedup prompt deliberately
defined events as occurrence-coherent so downstream clustering could surface
the cross-mechanism span as a feature, not a bug.

**Coverage results:**

- **Hornsdale FCAS (3 docs):** v1 200 records → v2 156 records.
  - v1→v2: 85% covered, 12% partial, 2% missing (5 records, all spec detail)
- **REVS (3 docs):** v1 165 records → v2 156 records.
  - v1→v2: 94% covered, 6% partial, 0% missing
  - v2→v1: 89% covered, 11% partial, 0% missing

Substantive content is preserved; only the event-graph organisation diverges.

**Files snapshotted:**
- `code/extract_v2.py` — pipeline driver as run
- `code/extract_v2.md` — prompt with mechanism-coherence in same-event criterion
- `code/check_v2_coverage.py` — coverage script
- `outputs/hornsdale_fcas/` — runs/arena/per_doc_v2_test contents
- `outputs/revs/` — runs/arena/per_doc_v2_revs contents

**Successor:** `2026-05-01-occurrence-coherent-grave` re-runs REVS after
relaxing the same-event criterion to match the v1 dedup prompt
(occurrence-coherent without the mechanism conjunct).
