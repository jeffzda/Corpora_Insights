# Post-extract grouping — fullrevs scaffolding (code + processing-order snapshot)

**Date:** 2026-05-02. **Reconstructed from folder contents + git history.**

## What this folder is

A **scaffolding snapshot** for the full 12-doc REVS scale-up experiment. It contains:

- `code/group_events.py` — per-doc grouping driver state at this scale-up
- `code/group_events.md` — the grouping prompt at this state
- `processing_order.json` — the **seed-doc heuristic output** for REVS: `doc_0845` (Final Social Report, the project synthesis) selected as seed, followed by 7 backward-chronological docs and 4 forward-chronological docs (937 records across 12 docs total)

The `outputs/` subfolder is empty — this folder is the *configuration snapshot* showing what was set up for the scale-up. The full experimental run with replicate outputs lives at:

- **`../2026-05-02-fullrevs-production/`** — 3 replicates × 12 docs at temperature=0 with `--exclude-fields lesson`. Mean 471 events / rep (stddev 54.5, ~12% relative noise). Total cost ~$8. Consensus event graph at ≥2/3 threshold yields 483 events; reproduces 70% of v1 dedup's confident pairs while finding 1,330 new cross-doc pairs v1 missed.

## What `processing_order.json` shows

The seed-doc heuristic at `canonical/narrative/seed_doc_heuristic.py` selects:

```
seed:      doc_0845  (rule: synthesis title)
order:     0845, 1347, 0382, 0494, 0832, 1348, 1083, 0950, 0844, 0313, 0415, 0708
records:   937 total
```

Per the heuristic (validated at `seed_doc_heuristic.md`): "Tier 0 — synthesis-title docs (across all doc_types), interim/draft excluded; pick latest, then largest by tokens". `doc_0845` is REVS's Final Social Report — the project-synthesis-level doc that establishes the canonical event names which subsequent docs anchor to.

## Why this scale-up matters for the methodology paper

The 3-doc REVS subset (`doc_0844`, `doc_1347`, `doc_1348`) was the testbed for all the architectural variants documented in the runs/README.md table. This 12-doc scale-up tests whether the chosen architecture (per-doc seed-first chronological with `--exclude-fields lesson`) holds at production scale, before being deployed to the full 502-project ARENA corpus.

The `fullrevs-production/` notes.md documents that it does — but with caveats: replicate Jaccard drops from 0.786 (3-doc, no-lessons) to ~0.519 (12-doc, no-lessons). Noise compounds through the chronological registry chain because the running event registry passed between docs is itself rep-dependent. Mitigation: run 3 replicates and take the consensus at ≥2/3 threshold.

## Files in this snapshot

- `code/group_events.py` — driver
- `code/group_events.md` — prompt
- `processing_order.json` — seed + chronological order for REVS

## Cross-references

- `../2026-05-02-fullrevs-production/notes.md` — full experimental results (this folder's "successor")
- `../2026-05-02-replication-campaign/notes.md` — 3-doc noise-floor characterisation that motivated the production config
- `../seed_doc_heuristic.md` (in `canonical/narrative/`) — the rule that produced this `processing_order.json`
