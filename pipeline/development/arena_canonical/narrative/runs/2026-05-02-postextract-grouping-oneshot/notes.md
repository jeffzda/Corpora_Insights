# Test snapshot — 2026-05-02 — postextract-grouping-oneshot

> **Headline:** All 165 v1 REVS records sent in a single Sonnet call (no
> chronological accumulation). REVS: 165 records → 63 events, max event size 8.
> Counter-intuitively *less* consolidated than the batched run; the canonical 6
> worked-example records split across 2 events. Showed that within-doc batching
> isn't the consolidation mechanism — chronological accumulation across docs is.
> See [`../README.md`](../README.md) for the full 7-way comparison.
>
> **Predecessor:** [`../2026-05-02-postextract-grouping/`](../2026-05-02-postextract-grouping/) —
> the batched 8-call run this variant compared against.
> **Successor:** [`../2026-05-02-postextract-grouping-perdoc/`](../2026-05-02-postextract-grouping-perdoc/) —
> isolated chronological accumulation as the lever, with one call per doc.

**Architecture variant:** identical to the post-extract grouping pass except
all 165 v1 REVS records are sent to a single Sonnet call instead of being
batched per-doc with a running event registry. Tests whether seeing everything
at once produces tighter event consolidation than chronological batching.

**Run results:**

- 165 records, 63 events, 305s wall, $0.45.
- Single call: 46,899 input tokens / 20,587 output tokens.

**Surprising finding — batched beats one-shot on consolidation:**

| | Batched (3-call) | One-shot (1-call) |
|---|---|---|
| Events | **44** | 63 |
| Records/event | **3.75** | 2.62 |
| Singleton% | **32%** | 40% |
| Cross-doc% | **25%** | 17% |
| Max event size | **22** | 8 |
| Cost | $0.76 | $0.45 |
| Wall | 479s | 305s |

**The canonical 6 worked-example records split in one-shot mode** — 5 to
EVT-0005 (cert event) but 1 (`ARENA-DLV-1348-0029`, vendor-confidence record)
to EVT-0062 (single-vendor dependency). Batched grouped all 6 correctly.

**The Wallbox cert constellation fragmented into 7 parallel events** under
one-shot (main cert at 8 records, FCAS slow-raise as separate 8-record event,
classification gap as 6, PAJ ambiguity as 6, single-vendor as 6, earthing as
3, EMC fix as 3) vs 1 umbrella 22-record event under batched.

**Why batched wins.** When `doc_0844` (Crossing Sectors synthesis doc) is
processed first, it establishes a small set of high-scope event names. LL2
and LL1 records then attach as aspect-distinct records to those anchors. In
one-shot, the model has no anchor framework — every record is evaluated
simultaneously, and aspect-distinct sub-events get declared as parallel events
rather than merged under a single occurrence.

**Validates §13 (chronological event identity) at the architectural level.**
Even decoupled from extraction, chronological batching with a running event
registry materially tightens event consolidation. Seed-doc-first walk +
accumulating event registry does real work — each previously-established
event name acts as a coarse-grained anchor that pulls aspect-distinct records
from subsequent docs into the same umbrella.

**Recommendation for production pipeline.** Use the batched
`pipeline/group_events.py` (not the one-shot variant in this run) with
seed-doc-first ordering. The one-shot variant remains useful as a control for
methodology-paper experiments.

**Files snapshotted:**
- `code/group_events_oneshot.py` — new one-shot driver
- `code/group_events.py` — batched driver (for reference)
- `code/group_events.md` — grouping prompt (shared with batched run)
- `code/group_events.{py,md}.predecessor` — pre-edit state of the
  batched driver and prompt
- `outputs/revs/all.assignments.json` — all 165 record→event_id assignments
- `outputs/revs/all.assignments.events.json` — final 63-event registry
- `outputs/revs/all.assignments.raw.txt` — raw model response
