# Seed-doc selection heuristic for v2 chronological-event extraction

**Status:** specified and validated on ARENA Past multi-doc projects (211/503). Implementation: `seed_doc_heuristic.py`.

## Architecture context

The v2 extraction architecture (§13 in `methodology_gaps.md`) processes a project's documents in three phases:

1. **Seed pass** — extract events from one designated *seed document*, with no prior event context. The seed's events become the project's initial event list.
2. **Backward walk** — pre-seed documents in reverse chronological order, each receiving the running event list. New records either assign to an existing event or declare a new one.
3. **Forward walk** — post-seed documents in chronological order, with the now-extended event list.

Seeding from a synthesis document (typically a Final Report or Knowledge Sharing Report) anchors the project's event ontology against its most reflective view, dissolving the "first-encounter prototype problem" inherent in pure-chronological extraction.

This document specifies **how the seed document is chosen automatically** from project metadata, without reading the documents.

## Selection logic (v3)

```
Tier 0  Synthesis-titled docs (across all doc_types), interim/draft excluded
        → pick latest, then largest by tokens

Tier 1  Filter to docs tagged 'Reports' (or 'Lessons' if no Reports)

Tier 2  Collapse numbered series (Milestone N, Lessons Learnt N, …)
        → keep only highest-N entry per series

Tier 3  Pick largest by input_tokens (or char-count for un-extracted corpora)
```

### Title patterns

**Synthesis match (Tier 0):**

```regex
\bfinal\s+(?:\w+\s+)?(?:report|ks|knowledge|lessons|project|dissemination)\b
| \bproject\s+(?:results|summary|completion)\b
| \bconsolidated\b | \bpublic\s+dissemination\b
| \b(?:final\s+)?knowledge\s+sharing\s+report\b(?!\s*\d)
| \blessons\s+learn(?:t|ed)\s+report\b(?!\s*\d)
```

**Negative filter (excluded from Tier 0):**

```regex
\b(?:interim|draft|preliminary)\b
```

**Numbered-series detection (Tier 2):**

`milestone N` · `knowledge sharing report N` · `lessons learnt [report] N` · `performance report N` · `operational report #N` · `trial N`

## Validation results

Tested against 211 ARENA Past multi-doc projects with ≥2 dated docs. "Project end" proxied by latest publish-date among project's docs.

| Metric | v1 (size only) | v3 (this spec) | Δ |
|---|---|---|---|
| Seed within 6 months of latest doc | 71% | **82%** | +11 pp |
| Seed within 12 months of latest doc | 80% | **91%** | +11 pp |
| Seed IS the latest doc | 58% | **72%** | +14 pp |
| Mean seed→latest gap | 194 d | **91 d** | −103 d |
| 22-outlier fix rate | — | **17/22** | |

Rule-firing split across the 211 projects: **47% match Tier 0 (synthesis-title)**; 53% fall through to size-based fallback.

## Scope and applicability

### Where the heuristic + recency claim both hold

| Population | Count (ARENA) | Heuristic applies | Recency validated |
|---|---|---|---|
| **Past, multi-doc** | **211** | **Yes** | **Yes (91%)** |
| Past, single-doc | 199 | n/a (no event-walk) | n/a |
| Current, multi-doc | 53 | Yes, with caveats | **No — out of scope** |
| Current, single-doc | 40 | n/a (no event-walk) | n/a |

### Single-doc projects (239 / 503 in ARENA)

No event-walk required. Extract that one document; every event is a first-encounter declaration. The seed-doc heuristic doesn't run.

### Current projects (53 multi-doc in ARENA)

The heuristic still runs and picks a seed. **40% match a synthesis-title pattern**; 60% fall to size-based fallback. **But the recency claim does not transfer** — the latest doc in a Current project is "what's been published so far," not project close. The seed represents *best-available synthesis at the moment of extraction*, not *the project's settled view*.

Implications:

- **The seed for a Current project may be an early synthesis** (e.g. Lessons Learnt 1 published year-1 of a 5-year project). The architecture's backward-walk has limited material; the forward-walk has many docs not yet published.
- **Seed selection should be re-runnable.** When a new doc lands or status flips Current → Past, the heuristic should re-pick. If the new pick differs from the old, run a within-project event-name dedup pass to reconcile events from the old seed against the new (richer) one. Cheap.
- **Methodology-paper claims about seed quality must scope to Past projects.** The 91%/72% headline numbers are Past-only. Current projects are deployable but un-validated against a settled-view ground truth.

### Cross-corpus generalisation

The Past/Current distinction is an ARENA-specific catalogue field. Other corpora handle this differently:

- **ANAO** — performance audits are typically one-shot deliverables. Project ≈ audit; seed selection collapses to "the audit report itself." No event-walk per "project," but possibly an event-walk *across* audits of the same auditee or program area, depending on how project boundaries are defined for ANAO.
- **Generic recommendation** — when applying this heuristic to a new corpus, first verify that there's a project-level grouping with multiple docs over time. If the corpus is one-doc-per-project, this whole subsystem is unnecessary.

## Remaining failure modes (5/211 unfixed)

The five Past-project cases v3 still places >2 yr from project end:

1. **NT SETuP** — synthesis match fired on 2019 Lessons Learnt; project ran to 2023 with Performance Report 4. Real ambiguity about which is the canonical synthesis.
2. **evolve DER** — 5 standalone technical reports, none titled "final" or part of a numbered series.
3. **Enel X** — 7-doc Knowledge Sharing Report series; the largest is #2, not the actual final #7. Series regex catches this but synthesis-match fires first on the unnumbered titles.
4. **ESCRI** — 2-doc project; the older doc IS the legitimate synthesis. Architecture is correct here; the gap is real.
5. **Frasers** — Lessons Learnt 1 → 2 → 3 series where #1 is largest. Series regex matches but synthesis-match fires first on a different doc.

For projects in the size-based fallback bucket (53% of Past, ~60% of Current), an LLM seed-selector pass (~$0.001/project) could close most of the remaining gap by reading short title+abstract sets and identifying the best synthesis candidate. Not a deal-breaker for the architecture — fallback selections are defensible — but available as an enhancement.

## Re-running the script

```bash
python3 corpora/arena/tests/extraction/seed_doc_heuristic.py
```

Reads `corpora/arena/output/per_doc/doc_*.json`, prints the validation summary above. The `select_seed()` function takes any list of doc-dicts with the required keys and is the engine entry point — corpus-agnostic.
