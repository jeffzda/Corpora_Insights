# Post-extract grouping — no-lessons variant (code snapshot)

**Date:** 2026-05-02. **Reconstructed from folder contents + git history.**

## What this folder is

A **code-state snapshot** of the per-doc grouping driver at the moment the `--exclude-fields lesson` capability was first exercised. The `outputs/` subfolder is empty — no full experimental results landed here. This folder documents *the configuration that was tested*; the actual results are in:

- **`../2026-05-02-replication-campaign/`** — formalised the comparison as one of the three configs (`perdoc_no_lessons` vs `perdoc_baseline` vs `oneshot`), 3 replicates each. **That's where the headline finding lives:** dropping the `lesson` field improves replicate Jaccard from 0.678 → 0.786.
- **`../2026-05-02-fullrevs-production/`** — production deployment of the chosen no-lessons config on the full 12-doc REVS project, 3 replicates.

## Why the lesson field was excluded

The hypothesis (Jeff's, going into the replication campaign) was that the `lesson` field — model-synthesised text incorporating cross-context inference, per `legacy/narrative/failure_mode_methodology/methodology_notes.md` §6.5 — destabilises pair-grouping decisions because the synthesis itself is noisy across replicates.

Removing it leaves only `narrative` + `evidence` (closer to source-faithful content) for grouping decisions. The replication campaign confirmed this empirically; the production run adopted `--exclude-fields lesson` as the canonical default.

## Files in this snapshot

- `code/group_events.py` — driver state at the moment the `--exclude-fields` flag was added
- `code/group_events.md` — prompt at this state

## Cross-references

- The `--exclude-fields lesson` flag was added in commit `fb13195` (the same commit that introduced the replication campaign)
- The default in `pipeline/group_events_corpus.py` is now `--exclude-fields lesson` (per the production deployment)
