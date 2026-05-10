# Glossary build — session writeup, 2026-05-05

A study-guide companion to the ARENA Knowledge Bank, built on top of the existing
entity-extraction pipeline. End state: a 760-entry corpus-grounded glossary with
24 PM-useful subcategories and per-term metadata fingerprints, plus 489
characteristic-vocabulary signatures (one per project). Total spend across
nine Sonnet passes and pure-Python aggregation: approximately $2.30.

This document is the methodology-paper-shaped retrospective for the day's work.

---

## Origin

A prior session had built a four-stage entity-extraction pipeline at
`corpora/arena/entity_extraction/`:

| Stage | Code | Job |
|---|---|---|
| 01 | `01_regex_sweep.py` | Acronyms and capitalised proper-noun runs from raw markdown |
| 02 | `02_ner_sweep.py` | spaCy `en_core_web_sm` NER, parallel over 32 workers |
| 02b | `02b_ner_sweep_trf.py` | spaCy transformer-NER pass (high-confidence subset) |
| 03 | `03_normalise_and_match.py` | Cluster surface variants; join to portfolio CSV; classify matched / unmatched |

This produced an `entity_index.csv` of 38,721 canonical surfaces with frequency,
document coverage, source provenance (regex / NER-sm / NER-trf), and
match-status (matched-to-catalogue / unmatched). Working-state was uncommitted
when the session began; the diff turned out to be a parallelisation refactor
plus a third source (NER-trf) being added to the normalise step — a clean
improvement, committed as save-point (`1322591`).

The pipeline could *find* acronyms and named entities. It couldn't *say what they meant*.
That gap is what the glossary build closed.

---

## The build, in order

### Pass 1: top-600 acronyms (Sonnet 4.6 single-shot)

`04_glossary_pass.py`. Filtered `entity_index.csv` to:
- `match_status = unmatched`
- `pattern = acronym`
- `n_unique_docs >= 5`
- top 600 by `n_total_mentions`

Sent in one prompt with verbose JSON schema (term / expansion / category /
definition / arena_context / notes / uncertainty). Categories drawn from a
12-value schema (technology / market / regulation / organisation / programme /
standard / concept / location / unit / event / person / noise).

**Result:** $1.00, 1077s, 64k output tokens hit (`stop_reason: max_tokens`).
JSON truncated at entry 505 of 600. Recovered the 505 complete entries via
a per-entry brace-balanced parser rather than re-running. 85 entries
correctly classified as `noise` (sentence fragments, ambiguous abbreviations);
420 substantive glossary entries; 100 flagged uncertain.

**Diagnosis of the truncation:** definitions averaged 27 words (under my
30-60 target), so model verbosity wasn't the cause. The bloat was schema
overhead — about 150 chars per entry just for JSON keys + `arena_context`
field. `ARENA context` is a useful field but expensive at scale.

### Pass 2: three follow-up cohorts in parallel

`05_glossary_v2.py`, with `--mode {tail,titlecase,reground}`. Compact JSON schema
(`t/e/c/d/x/n/u` single-letter keys) saved ~40% output tokens vs Pass 1.

| Mode | Cohort | Wall | Cost | Result |
|---|---|---:|---:|---|
| `tail` | 95 acronyms truncated from Pass 1 | 94s | $0.09 | 95/95 returned, `end_turn` |
| `titlecase` | 300 multi-word surfaces (orgs / programmes / standards) | 308s | $0.32 | 300/300 returned, `end_turn` |
| `reground` | 100 uncertain-from-Pass-1 with 2-3 corpus snippets each | 195s | $0.23 | 100/100; 72 resolved cleanly, 28 still uncertain |

The `reground` mode is the methodologically-distinctive piece: for each
uncertain term, the script greps the corpus for narrative snippets containing
that surface and feeds 2-3 to the model alongside Pass 1's first attempt.
Sonnet then either confirms the original definition (uncertainty → false) or
rewrites with the corpus context. Resolved REVS as the V2G trial, MATCH as
the UNSW DER study, EPWA as Energy Policy WA — terms a priors-only pass
couldn't have placed.

### Pass 3: merge

`06_glossary_merge.py`. Combined Pass-1 confident entries with the three
Pass-2 cohorts. Reground entries override their Pass-1 counterparts.

**Output:** 760 substantive glossary entries + 100 noise. Categories led by
technology (231), organisation (186), concept (141). 48 entries still
flagged uncertain after reground (down from 100 in Pass 1).

### Pass 4: subcategory proposal (Sonnet)

`07_propose_subclustering.py`. The three biggest top-level buckets were too
big to navigate. Asked Sonnet to propose 4-8 subcategories per bucket,
PM-relevant rather than taxonomically complete. Cost: $0.12.

Result: 24 subcategories total. Highlights:
- **technology:** Solar generation / Energy storage / Grid infrastructure /
  DER & smart energy / EV & transport / Hydrogen & green fuels /
  Industrial decarbonisation / Digital, monitoring & simulation tools
- **organisation:** Market bodies & regulators / NSPs / Universities /
  Government departments / Industry companies / Tech suppliers / Professional
  services / International & peak bodies
- **concept:** Project lifecycle & delivery / Knowledge sharing & reporting /
  Financial & economic metrics / Tech & commercial readiness / Grid services
  & market concepts / Procurement & governance / ESG frameworks / Technical
  performance & measurement

Sonnet flagged its own edge cases: IBR/GFM straddle storage and grid;
EMS/ADMS straddle digital tools and grid infrastructure; CRC is a programme
not an organisation; LCOE and EPC each appear in two concept subcategories.

### Pass 5: subcategory apply

`08_apply_subclustering.py`. Sonnet assigned each of 558 entries (technology
+ organisation + concept) to one subcategory using the 24-name vocabulary
plus an `other` escape. Compact schema. Cost: $0.27, 181s.

Distribution: 24 subcategories all populated; 7 entries fell through to
`other`. Largest sub-buckets: Grid infrastructure (52), Solar generation
(45), Government departments (44), Digital tools (38), Energy storage (35).

### Pass 6: metadata fingerprint (no LLM)

`09_metadata_fingerprint.py`. Pure data analysis — for each glossary term:
1. Read `candidates_raw.csv` (825k rows) + the two NER candidate files for
   every mention with `(surface, doc_id, char_offset)`.
2. Map `doc_id` slug → modal project / category / year via per-doc records'
   `markdown_path`, with `kb_associated_project`, `kb_category`, `kb_year`
   pulled per record.
3. Join project → portfolio metadata (Lead organisation, ARENA programme).
4. Aggregate per term: top projects, top categories, top lead orgs, top
   programmes, year distribution.
5. Compute **distinctiveness** — observed share within term-mentions vs base
   rate share across the corpus. Values >2× flag the term as a marker for
   that cohort; values near 1× indicate general vocabulary.

**Coverage:** 860/860 target glossary terms ended with fingerprints; 1
single-doc orphan term didn't resolve to a portfolio project.

**Year-trajectory metric** (initial naive version was biased): replaced
"first-third vs last-third" with median-mention-year vs corpus-median (2019).
Now correctly classifies GFM as rising (median 2023), LCOE as falling
(median 2016 vs 2019 baseline — historical solar economics work), TRL as
rising (modern uptake of the framework). BESS, ARENA, VPP appear steady
around 2019-2020.

Two illustrative fingerprints worth pinning:
- **DERMS** — 65% in DER projects (7.94× corpus base), 53% from Evoenergy
  (627× — essentially a single-organisation term).
- **HVDC** — 65% in System security & reliability (16.3×), 55% from
  TasNetworks (326× — Project Marinus dominates).

### Pass 7: v3 merge

`10_glossary_v3_merge.py`. Combined the v2 merge + subcategory assignments
+ metadata fingerprints into a single artefact organised by category →
subcategory. Each entry now shows: term, expansion, definition, model-written
ARENA context, **and** an empirical fingerprint block (top projects,
distinctiveness for top categories/orgs, year trajectory, ARENA programme
concentration).

**Output:** `glossary_v3.{json,md,html}` — 760 entries, 24 subcategories
populated, 740k chars HTML.

### Pass 8: project vocabulary signatures

`11_project_vocabularies.py`. The inverse view — for each project, the
glossary terms that appear at disproportionately high rates vs the corpus
base. Pure data analysis again.

Initial thresholds were too defensive: ≥2 docs per project, ≥30 total
mentions. That filtered out 239 single-doc projects whose signatures were
still meaningful. Relaxed to ≥1 doc, ≥10 total mentions, ≥3× distinctiveness,
top-25 terms per project.

**Result:** 489 project signatures (out of 503 projects with corpus
presence; the other 14 had <10 mentions across all their docs and would
yield genuinely thin signatures). Distribution: 44 thin (2-4 terms), 119
medium (5-10), 199 rich (11-24), 127 capped at 25 (deepest-documented
projects).

Sample signatures, unedited:
- **ACAP** → AUSIAPV, QESST, UMG, BQR, ACAP Conference (academic photovoltaic R&D vocabulary)
- **Project Symphony** → CTZ, DCOA, DSO Platform, WEM Rules, Energy Policy WA, DER Roadmap (DER orchestration in WA-specific market context)
- **Project EDGE** → LSE, DER Marketplace, Scheduled Lite, DER Aggregators (DER market integration)
- **PV-Rich Distribution Networks** → Load Tap Changers, HV Feeder, OLTC, Watt and Volt (network engineering)
- **REVS V2G** → REVS, VGI, JET Charge, EV Council (vehicle-grid integration)

These signatures are computed without any LLM input — they fall directly
out of the term × project mention matrix once distinctiveness is defined.

---

## Spend tally

| Pass | Cost | Wall | Output |
|---|---:|---:|---|
| 04 — Pass 1, top-600 acronyms | $1.000 | 18 min | 505 entries (truncated, recovered) |
| 05 — Pass 2 tail | $0.093 | 94s | 95 entries |
| 05 — Pass 2 titlecase | $0.319 | 308s | 300 entries |
| 05 — Pass 2 reground | $0.233 | 195s | 100 entries |
| 07 — Subcategory proposal | $0.123 | 74s | 24 subcategories |
| 08 — Subcategory apply | $0.270 | 181s | 558 assignments |
| 09 — Metadata fingerprint | $0 | 3 min | 860 fingerprints |
| 10 — v3 merge | $0 | <1s | merged glossary |
| 11 — Project vocabularies | $0 | 5 min | 489 signatures |
| **Total** | **~$2.04** | ~30 min | full artefact stack |

(Cumulative across all four model passes: ~$2.04. Add the prior NER
pipeline runs which preceded this session.)

---

## Schema and metric decisions worth pinning

**Compact JSON keys (single-letter) save ~40% output tokens** vs verbose
keys at the same content density. Pass 1 hit `max_tokens` because the
verbose schema added ~150 chars per entry of structural overhead.
Pass 2's tail recovery returned the same 95 entries comfortably under the
cap with the compact schema. Worth defaulting to compact-keys whenever
output token budget is tight; merge step normalises back to verbose for
the final artefact.

**The 12-value category schema** (technology / market / regulation /
organisation / programme / standard / concept / location / unit / event /
person / noise) was big enough to handle every glossary surface without
forced bucketing. Two categories never fired on the acronym layer (event,
person — sensible, acronyms rarely name those). The titlecase pass populated
all 12.

**Sonnet-proposed subcategorisation** turned out to be a much better fit
than analyst-imposed subcategories would have been. The proposal reflected
*how the corpus uses these terms* (e.g. "Australian energy market bodies
and regulators" as one subcategory, separate from "Network service
providers" — a distinction that makes sense to a PM in this domain but
wouldn't be obvious to a generalist).

**Distinctiveness as a ratio** (observed share / base share) rather than
absolute count is the load-bearing metric. Absolute mention counts privilege
big projects; distinctiveness reveals what's *characteristic*. A term at
65% concentration with 8× distinctiveness is a marker; a term at 65%
concentration with 1.0× distinctiveness is just present at base rate.
Same surface count, very different signal.

**Median-mention-year vs corpus-median** for trajectory is robust to the
ARENA corpus's heavy-middle publish-year distribution. The earlier
first-third / last-third heuristic flagged most terms as "falling" because
recent years (2024-2025) carry less document mass than the 2019-2023 peak.
Median-vs-median centres the comparison.

---

## Lessons / what we'd do differently

1. **Default to compact schema for any LLM batch over ~200 entries.** Two
   sessions burned $1+ each on `max_tokens` truncation that compact keys
   would have prevented.
2. **Always define a pure-data baseline before reaching for an LLM.** The
   metadata fingerprint and project vocabulary signatures were computable
   from existing data joins. They produce stronger empirical claims than
   priors-grounded model assertions, and at zero cost. The "ARENA context"
   sentence Sonnet wrote per entry is now redundant with the empirical
   fingerprint — model-written context could be dropped from future builds.
3. **Year-trajectory metrics need calibration to corpus shape.** If
   document publish years cluster in a band, naive recency comparisons
   over-detect "decline." Use median-vs-median or Mann-Kendall on the
   weighted year series.
4. **Threshold-tuning is rarely "right the first time."** Project
   vocabulary signatures jumped from 260 to 489 by relaxing two filters
   that were defensive defaults. Surface the thresholds in the output
   and re-tune after seeing the distribution.

---

## Artefacts on disk

```
corpora/arena/entity_extraction/
├── code/
│   ├── 04_glossary_pass.py           — Pass 1, verbose schema, top-600 acronyms
│   ├── 05_glossary_v2.py             — Pass 2 (tail / titlecase / reground modes)
│   ├── 06_glossary_merge.py          — v1 + v2 merge
│   ├── 07_propose_subclustering.py   — Sonnet proposes 24 subcategories
│   ├── 08_apply_subclustering.py     — Sonnet assigns subcategories
│   ├── 09_metadata_fingerprint.py    — pure-data per-term fingerprint
│   ├── 10_glossary_v3_merge.py       — v3 merge incl. fingerprints
│   └── 11_project_vocabularies.py    — inverse view
├── output/
│   ├── glossary.{json,md,html}                    — v2 (760 entries flat)
│   ├── glossary_v3.{json,md,html}                 — v3 (760 entries × 24 subcats × fingerprints)
│   ├── glossary_metadata_fingerprint.json         — per-term fingerprints, 860 entries
│   ├── glossary_subcategories.json                — Sonnet's subcategory assignments
│   ├── glossary_subclustering_proposal.json       — Sonnet's subcategory taxonomy
│   ├── project_vocabularies.{json,md,html}        — 489 project signatures
│   └── glossary_v2_*.json                         — per-mode Pass-2 intermediates
└── SESSION_WRITEUP_2026-05-05.md                  — this document
```

Each output JSON is reproducible end-to-end from `entity_index.csv` (which is
itself reproducible from `corpora/arena/marker_output/` via stages 01-03).

---

## Open follow-ups

- **Drop model-written `arena_context`** from future glossary builds in
  favour of the empirical fingerprint. Saves ~30% output tokens and gives
  a stronger claim shape.
- **Inverse glossary by tech category** rather than just by project —
  e.g. characteristic vocabulary of "Battery storage" projects across the
  whole corpus. Simple aggregation; no LLM needed.
- **Time-series of vocabulary** — track when each glossary term first
  appeared in the corpus and how mention volume evolved year over year.
  Useful for spotting emergent concepts (e.g. when "GFM" or "VPP" first
  showed up).
- **Glossary cross-references** — for each term, link to the v2 cluster
  reports / project reports that cite it. Closes the loop between the
  reference-class memos and the glossary.
- **Public-facing variant.** With BL attribution as research-vehicle (not
  consultancy) — eyebrow-band byline, footer disclosure noting pre-employment
  IP. Suitable for LinkedIn / research positioning.

The methodology paper section on "vocabulary substrate" would lean directly
on this writeup. Total spend $2 makes the *whole stack* cheap enough that
running it on a second corpus (ANAO, APH committee reports) is a one-day
exercise once the entity-extraction pipeline runs there.
