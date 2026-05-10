# Corpora Insights

A generalised pipeline for extracting structured knowledge from government document corpora. The pipeline takes PDFs (converted to markdown) plus a human-written domain configuration and produces a four-layer queryable artefact: atomic records → mechanism clusters → canonical parents → themes.

The pipeline is corpus-agnostic by design. It has been applied to two structurally distinct corpora to date — the **Australian Renewable Energy Agency (ARENA)** Knowledge Bank (1,440 documents, full v3 substrate) and the **Australian National Audit Office (ANAO)** performance audit corpus (1,452 documents; N=100 stratified demo) — using only token-substitution-level changes in domain configuration files. Both applications were instances of the methodology, not the source of it.

## What's in this repository

- `pipeline_methods.md` — the full methodology writeup (~14k words). Start here.
- `pipeline/` — the domain-agnostic engine.
  - `stages/s01_extract … s11_theme_audit/` — the canonical 11-stage pipeline. Each stage is a `stage.py` plus co-located prompt template(s).
  - `glossary/g01 … g11/` — parallel glossary sub-pipeline (regex + NER candidates → normalise → define → merge → fingerprint → finalise → inverse signatures).
  - `ingest/` — PDF download + marker_single conversion.
  - `prompts/` — domain-agnostic prompt templates (the canonical "grave" extraction prompt lives here).
  - `development/` — preserved per-corpus scripts and methodology paper trail.
    - `arena_canonical/`, `arena_canonical_pilot/`, `arena_clustering_v2/`, `arena_closure/`, `arena_glossary/` — the original ARENA scripts that produced the v3 substrate, with co-located narrative documentation (123 markdown files: methodology notes, run snapshots, ensemble investigation notes, boundary-mapping writeups, cluster-signature-drift disclosure, session writeups).
    - `anao_n100_demo/` — the ANAO N=100 demo scripts.
- `domains/arena/` — ARENA-specific configuration.
  - `domain.yaml` — model selection per stage, prompt_tokens, stratification field, batch sizes.
  - `scrape.py` — bespoke scraper inheriting from `pipeline/ingest/base.py`.
  - `enums.yaml`, `category_map.yaml`, etc. — ARENA-specific cleaning + taxonomy rules.
  - `prompts/domain_context.md` — the corpus description injected into engine prompts.
- `pipeline_methods_reading.md` — the 1.3MB concatenation of 68 source documents that grounds the methods paper. Each `[T1|T2|T3]` per-section block is a primary source for one or more paper sections.
- `pipeline_methods_gap_analysis.md` — diff of the methods paper against the source documents (paper trail of the rewrite).
- `CLAUDE.md` — project context and standing instructions.
- `timestamps/` — GPG public key + OpenTimestamps proofs anchoring HEAD to the Bitcoin blockchain.

## Pipeline overview

The pipeline produces four layers of structure with synthesis at each layer once membership stabilises:

1. **Atomic records** — extracted from each document via the canonical "grave" prompt (`pipeline/prompts/extract.md`); all factual observations a future practitioner could carry forward.
2. **Mechanism clusters** — records grouped by causal mechanism (not topic / project / technology). Six-axis Opus 4.6 multi-label tagging filters records to the predicate-bearing subset before clustering.
3. **Canonical parents** — clusters grouped by mechanism class. Derived via a 59-rep deliberation-rich Opus 4.7 ensemble; the ARENA canonical layer is 86 parents (a subset of 126 candidate classes, gated on rep agreement and source-tier judgement).
4. **Themes** — parents grouped by failure-mode family. Derived by a single Opus 4.7 audit-and-grouping call. ARENA's theme layer is 16 themes covering all 86 parents.

A parallel glossary sub-pipeline produces a per-corpus terminology catalogue plus per-project distinguishing-vocabulary signatures.

## Validation

Two routes:

- **Stage-internal tests** — substrate voice and grounding; six-axis classification stability; one-shot vs chunked attention test; cluster→parent agreement at 93.8% high-high under blinded same-rubric re-review (n=91); parent ensemble variance reduction (sd 13.6 → 7.24); cross-project diversity at 17.8 projects per cluster; within-tech distinctness with 0 Opus-proposed merges on a top-50 battery-dominated subset; causal-chain coherence at 88%; event-coherence on multi-parent stratum at 98%.
- **Use-case demonstrations** — c042 worked example showing cross-tech / cross-time / cross-provider synthesis; ANAO N=100 cross-corpus reproduction; ANAO↔ARENA parent-overlap audit (9 cleanly-shared mechanism classes, 17/19 corpus-specific extensions).

## Generalisability

The pipeline was built corpus-agnostic. Empirical confirmation: 62.3% of the 1,141 mechanism clusters produced from the ARENA application describe causal pathways applicable beyond renewable energy contexts (top general domains: program design, infrastructure project delivery, data systems integration, regulatory framework design); the 86-parent layer is a corpus-agnostic diagnostic vocabulary for programme-evaluation work; and the ANAO N=100 reproduction shows the engine runs end-to-end on a structurally distinct corpus with no engine modifications. Neither corpus shaped the methodology — they are validation instances.

## Cost economics

ARENA v3 substrate: ~$335 total (extraction + tagging + clustering + parent derivation campaign + closure). ANAO N=100 demo: parents pass $0.41 (single Opus 4.7 call). Full ANAO extraction (estimated): $200–250. A 10-rep full-clustering-stage ensemble for stability characterisation: $360–550 batched.

## Engine-vs-configuration boundary

Adding a new corpus should require only files under `domains/<corpus>/` and `corpora/<corpus>/` — no edits to `pipeline/`. Domain configuration provides:

- A bespoke `scrape.py` (web structure is too varied to generalise).
- A `domain.yaml` with `prompt_tokens` (substituted into engine prompt templates) and `stages` (per-stage model, batch size, stratification field, output paths).
- A `prompts/domain_context.md` description of the corpus.

This separation is the methodology's IP boundary; it is what makes the pipeline reusable rather than a collection of bespoke scripts.

## Provenance and evidence

- Commits are GPG-signed (key fingerprint `64E0128D…671FB0ECF38C06BB`, UID `mail@jeffcumpston.com`).
- The signed tag `evidence-snapshot-2026-05-10` anchors HEAD at a known time.
- HEAD is anchored to the Bitcoin blockchain via OpenTimestamps; proof file at `timestamps/HEADS_*.ots`.
- Verify the chain locally: `gpg --verify` on tags + `ots verify` on the proof file.

## Authorship

The methodology and the engine code are the intellectual property of Broad Learnings (Jeff Cumpston) and are corpus-independent. They were authored independently of any specific application corpus. Records, clusters, parents, themes, and other artefacts produced by running the methodology over any input corpus are also owned by Broad Learnings.
