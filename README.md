# ARENA Insights

Knowledge-extraction pipeline applied to the ARENA Knowledge Bank corpus.

## Contents

- `pipeline/` — generalised extraction engine (ingestion, extraction, clustering, parent/theme derivation, glossary build).
- `domains/arena/` — ARENA-specific configuration: scraper, prompts, taxonomy, cleaning rules.
- `pipeline_methods_v1.md` — methods paper draft describing the end-to-end methodology.
- `CLAUDE.md` — project context and standing instructions.

See `pipeline_methods_v1.md` for the full methodology writeup and `CLAUDE.md` for the engine-vs-config separation principle that governs the layout.
