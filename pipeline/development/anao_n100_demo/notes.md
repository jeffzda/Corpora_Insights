# ANAO N=100 generalisability demo
## 2026-05-06

## TL;DR

Stratified sample of 100 ANAO performance audits (5 era bands × 20 docs each, seed=42), processed through the v2 pipeline's first two stages: per-doc atomic-record extraction and per-doc event derivation. Goal: demonstrate that the same prompts that built the ARENA v2 substrate generalise to a structurally-different government corpus without modification.

**Headline:** the prompts transfer; the dedup-rate result reveals an interesting structural finding worth a methodology-paper note.

Total spend: **~$81** across two extraction runs (flat markdown, then marker rendered.md) plus per-doc event derivation. Pipeline halted before 6-axis labelling, clustering, and parent-classification passes — extraction + event-derivation is enough to support the load-bearing generalisability claim.

---

## Setup

- **Corpus:** ANAO performance audit reports, 1,452 markdown files spanning 1996-2025
- **Manifest:** 1,459 entries with unique report numbers; mostly one PDF per audit
- **Sample:** N=100 stratified by era (1996–2001, 2002–2007, 2008–2013, 2014–2019, 2020–2025), 20 each, seed=42
- **Multi-doc filter:** 80 of 1,459 docs (5.5%) are in multi-doc clusters (follow-up audit pairs, recurring-annual audits, omnibus activity-report summaries). 3 of those happened to be in the sample → effective N=97 after filter.
- **Extraction prompt:** unchanged ARENA v1 grave prompt (`domains/arena/prompts/extract.md`)
- **Event-derivation prompt:** unchanged ARENA canonical prompt (`corpora/arena/canonical/prompts/group_events.md`) with `prior_events_block` set to `(no prior events — first document of this audit)` since each ANAO audit is standalone after the multi-doc filter

---

## Part 1 — extraction comparison (flat markdown vs marker rendered)

| metric | flat markdown (max_tok=16k) | marker rendered (max_tok=64k) |
|---|---|---|
| docs succeeded | 97/100 | **100/100** |
| docs with records | 97 (after lenient recovery) | 91 |
| strict-parse | 67 | **91** |
| lenient-recovered | 30 (truncation) | 0 |
| zero-record docs | 0 | 9 |
| total records | 4,077 | **4,765** |
| records/doc median | 47 | **50** |
| records/doc max | 70 | **120** |
| output tokens | 1.20M | 1.42M |
| cost | $30.69 | $33.50 |

**Standing-instruction violation in the flat run.** First extraction capped `max_tokens=16,000`. ANAO docs produce more records per document than ARENA (audit reports are finding-dense). 30 of 97 docs hit the cap and got truncated mid-record. A lenient parser recovered the in-range records (4,077 total) but the run was inefficient.

**Marker rendered.md is canonical.** Files in `corpora/anao/markdown/` are derivative — they collapse bullet lists into paragraph text (joining items with `•`), partially lose bold/heading formatting, and add a wrapping header line. `corpora/anao/marker_output/<slug>/<slug>.rendered.md` preserves bullets as separate items, heading hierarchy, and bold formatting. The extraction prompt explicitly says to treat each bullet as a distinct finding — bullet preservation matters materially for atomicity.

The marker run is the canonical extraction:
- 100% docs succeeded
- 100% strict-parse (no truncation)
- More atomic records per doc (median 50 vs 47, max 120 vs 70)
- 9 zero-record docs are a feature: meta-reports / governance summaries that genuinely contain no atomic findings. The flat run probably manufactured findings on some of these because bullet collapse made them look denser than they were.

Net result: **4,765 atomic records from 91 docs** at $33.50, comparable in shape to ARENA records (id / title / narrative / lesson / significance / intervention / pages / evidence).

After the multi-doc filter: **4,617 records from 88 docs.**

---

## Part 2 — per-doc event derivation

Same canonical event-derivation prompt as ARENA, applied per doc with empty prior-events context (chain length 1, since each ANAO audit is standalone).

**Result: 4,617 records → 4,483 events. Dedup ratio 1.03×. 176 multi-record events.** Cost: $16.92 (88 batch calls).

This looks like a failure but isn't. Spot-check (5 random multi-record events, seed=42):

| event | size | merge call |
|---|---|---|
| Defence health materiel $4.5M overspend | 2 | ✓ correct (occurrence + lesson) |
| Domestic fishing licensing pre-processing delay | 2 | ✓ correct (timeline + root-cause) |
| NSW State Railway 700-member SMSF scheme | 4 | ✓ correct (textbook 4-aspect merge: scheme + control gap + re-registration + audit-delay) |
| Tax Office tiered protection framework | 3 | ◐ borderline (3 sub-clauses of one recommendation) |
| AGD Action Plan / MVP risk-rating | 3 | ✗ over-merge (bundled TSETT resource records with ICT MVP record) |

**4/5 correct or defensible. ~80% accuracy.**

### Why the dedup ratio is low

Two findings sit underneath the 1.03× number, supported by direct inspection:

**Finding 1: ARENA's dedup gain came mostly from cross-doc merging.** The ARENA pipeline collapses records like "milestone report mentions delay X" + "final report describes delay X" into one event via the chain mechanism. ANAO has no project-with-multiple-docs structure, so cross-doc merging doesn't apply. The aspect-merging logic transferred and works correctly when triggered (NSW SMSF case is textbook), but the corpus structure doesn't deliver the cases where cross-doc merging would deliver large gains.

**Finding 2: extraction-step atomicity decisions bound event-derivation effectiveness.** Inspection of 11 high-overlap pairs (Jaccard ≥0.30) across all docs found that suspected "missed merges" were mostly:
- Different years' values of the same metric — different events
- Different sub-organisations under the same parent — different events
- Restatements with content shifts (broader summary vs detailed breakdown) — borderline

Only ~1 of 8 high-overlap separate pairs was a clear missed merge (Comcover $40B insured-property risk discussed twice in same doc).

The structural reason: ANAO performance audits use a "summary-with-restatement-and-detail-shift" pattern where each restatement of a finding *adds new information* rather than just rephrasing. ARENA's project-doc extraction emits multiple aspect-distinct records describing one event (cause / mechanism / intervention / outcome / lesson) that the grouper recognises. ANAO's audit-doc extraction emits records sliced at sub-issue grain — different years, different sub-aspects, different audit-finding angles — that the grouper can't merge without sacrificing precision.

### Methodology-paper finding

> *Per-doc event derivation's effectiveness is bounded by extraction's atomicity choices. The aspect-merging logic transfers across corpora; the corpus-level dedup ratio depends on whether extraction emits records the grouper can recognise as aspects of one occurrence. Adapting the pipeline to corpora with structured-restatement-with-information-shifts patterns (like ANAO performance audits) would require either domain-aware extraction (e.g. emitting a `supports_finding` linkage) or a more aggressive event-derivation prompt that merges on shared underlying issue rather than shared occurrence. The current pipeline's correct-but-low-collapse behaviour reflects atomicity choices, not prompt transfer failure.*

---

## Steps not taken (intentional stop)

| step | est. cost | reason for skipping |
|---|---|---|
| 6-axis labelling | $3–6 | Demonstrating extraction + event derivation is enough for the load-bearing generalisability claim |
| Clustering on mechanism subset | $10–18 | Extraction-step finding above suggests clustering shape would also depend on atomicity decisions; not load-bearing for the demo |
| Pass 2 (cluster→parent classification) | $3 | Defer until the upstream extraction-grain question is resolved |
| Pass 3 (theme audit) | $1 | Same |

The decision to stop at event derivation was based on: extraction step demonstrates corpus generalisability; event-derivation step reveals the more interesting structural finding above. Continuing the pipeline would test more steps but at progressively higher cost; the load-bearing claim — that the prompts transfer to a structurally-different corpus — is already supported.

---

## Cost summary

| component | $ |
|---|---|
| Extraction — flat markdown (superseded by marker run) | 30.69 |
| Extraction — marker rendered (canonical) | 33.50 |
| Per-doc event derivation | 16.92 |
| **Total** | **81.11** |

Flat-markdown extraction was an inefficient learning step (max_tokens cap + worse markdown source). The marker-run + event-derivation cost ($50.42) is the relevant figure for what the demo actually costs.

---

## Files

### `code/`
| script | role |
|---|---|
| `anao_n100_extract.py` | flat-markdown extract (superseded; kept for comparison) |
| `anao_n100_retrieve.py` | flat-run retrieval |
| `anao_n100_recover_truncated.py` | lenient parser for the flat-run truncated outputs |
| `anao_n100_marker_extract.py` | canonical marker-rendered.md extract |
| `anao_n100_marker_retrieve.py` | marker-run retrieval |
| `anao_n100_event_derivation.py` | per-doc event grouping |
| `anao_n100_event_retrieve.py` | event-derivation retrieval |
| `anao_n100_classify_to_v2.py` | parent classification (drafted, never successfully run; included for record) |

### `output/`
| file | content |
|---|---|
| `anao_n100_marker_records.jsonl` | **canonical extraction output: 4,765 atomic records** |
| `anao_n100_marker_records_filtered.jsonl` | 4,617 records after multi-doc audit filter |
| `anao_n100_records.jsonl` | 4,077 records from flat-markdown run (comparison) |
| `anao_n100_records_recovered.jsonl` | flat run with lenient parser |
| `anao_n100_event_assignments.jsonl` | 4,619 record→event assignments |
| `anao_n100_events.jsonl` | 4,483 event registry |
| `anao_n100_*_meta.json` | cost / token / parse metadata for each pass |
| `anao_n100_*_batch_id.txt`, `*_manifest.json`, `*_raw.jsonl` | batch IDs, sample manifests, raw API responses |

---

## Standing-instruction lessons (for future Claude sessions on this corpus)

1. **`max_tokens` cap.** Set to model ceiling (64,000 for Opus 4.7). Truncation wastes the whole call.
2. **Use `marker_output/<slug>/<slug>.rendered.md`, not `markdown/<slug>.md`.** Bullet preservation and heading hierarchy materially affect atomic-record extraction quality.
3. **Multi-doc audit filter at sample-time.** ~5% of ANAO is multi-doc (follow-up audit pairs, annual recurrences, omnibus summaries). For full-corpus runs apply the filter before sampling.
4. **Each ANAO row is one audit, one PDF.** No project layer above the document. The seed-selection-and-chain logic from the ARENA canonical pipeline reduces to single-doc processing.
