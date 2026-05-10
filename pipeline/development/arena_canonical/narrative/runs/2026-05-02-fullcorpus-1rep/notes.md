# Full-corpus orchestrator infrastructure (code + smoke-test snapshot)

**Date:** 2026-05-02. **Commit:** `14f356d` ("feat: full-corpus event grouping orchestrators (sync + batch variants)"). **Reconstructed from folder contents + commit message + driver code.**

## What this folder is

A **code snapshot of the full-corpus orchestrator infrastructure** at the moment it was first introduced. The `outputs/` subfolder is empty — this folder doesn't contain a corpus-wide experimental run; it documents the *infrastructure that was built to enable one*. The actual corpus-wide grouping run lands at `corpora/arena/canonical/output/grouping/` per the canonical pipeline (which post-dates this snapshot).

The folder contains two new orchestrators alongside the per-project grouping driver:

- **`code/group_events_corpus.py`** — sync-threaded orchestrator. For each project: apply seed-doc heuristic, order remaining docs backward-chronological (pre-seed) then forward-chronological (post-seed), then thread per-doc grouping calls *sequentially within the project* (because each doc's call depends on the previous doc's events.json via the running event registry). *Across* projects: ThreadPoolExecutor with bounded concurrency.

- **`code/group_events_corpus_batch.py`** — Anthropic Batches API variant. **Wave-batched**: every project's depth-N call goes in one batch; waves run sequentially because of within-project chronological dependency on the prior depth's events.json. Resumable via batch-meta checkpoints. Estimated 50% cheaper than sync but slower wall (each wave waits for batch to complete; up to 22 waves for the longest project in the corpus).

## The wave-batching insight

The within-project chronological chain prevents naive batching: doc N's grouping prompt includes events established up to doc N-1, so doc N can't be submitted before doc N-1 returns. But **across projects at the same depth, calls are independent**:

```
Wave 1: every project's seed-doc call (no prior events) — N projects
Wave 2: every project's 2nd-doc call — projects with ≥2 docs
Wave 3: every project's 3rd-doc call — projects with ≥3 docs
...
Wave M: longest project's last doc (M ≈ 22 for the longest ARENA project)
```

Each wave becomes one Anthropic Batches API submission. The depth-1 batch has ~500 requests (every multi-doc project's seed); the depth-22 batch has 1 request (the longest project's last doc). Total wall: M waves × per-wave Batches API turnaround (typically 15-90 min for ~500 calls).

## Smoke test (in commit message, not in this folder)

Run on 2 projects with the sync orchestrator at concurrency=2:

| Project | Docs | Records | Wall | Cost | Events |
|---|---|---|---|---|---|
| Project 1 | 1 | 55 | 60 s | $0.12 | 15 |
| NT SETuP | 14 | 884 | 33 min | $3.30 | 225 |

**Cost projection:** $3.30 for 939 records → roughly **$316 for the 90k-record corpus** in sync mode. Batches API would halve that to ~$158.

The actual full-corpus production run was deferred until after the replication campaign and fullrevs-production runs validated the chosen configuration (per-doc, seed-first chronological, `--exclude-fields lesson`, temperature=0).

## Driver patches that landed with this commit

- `pipeline/group_events.py` adds `--exclude-fields` CLI flag (so the no-lessons config can be tested without forking the prompt)
- Streaming used when `max_tokens > 8192` (Anthropic SDK requires it above that ceiling for non-streaming calls)
- Temperature=0 made the default
- Default `max_tokens` raised to 32k for large per-project calls

## Files in this snapshot

- `code/group_events_corpus.py` — sync-threaded orchestrator (the version that produced the canonical run)
- `code/group_events_corpus_batch.py` — Batches API wave-batched variant
- `code/group_events.py` — per-doc driver (state at this commit)
- `code/group_events.md` — prompt
- `code/seed_doc_heuristic.py` — seed-doc selection (now lives at `canonical/narrative/seed_doc_heuristic.py`)

## Cross-references

- `../2026-05-02-replication-campaign/notes.md` — 3-doc noise-floor characterisation that came after this infrastructure landed
- `../2026-05-02-fullrevs-production/notes.md` — production run on REVS that validated the chosen config
- `../README.md` — synthesis (rows 5-7 reference back to this orchestrator)
- `pipeline/group_events_corpus.py` — current state; `--out-dir` defaults to `corpora/<domain>/canonical/output/grouping/`
