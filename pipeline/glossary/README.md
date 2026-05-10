# Glossary sub-pipeline

A parallel branch from `pipeline/stages/`. Forks at markdown ingestion,
never rejoins. Produces a corpus glossary — terms × categories ×
metadata fingerprint — distinct from the failure-mode pipeline's
record/cluster/parent artefacts.

## Stage map

| Stage | Engine source | Type | Purpose |
|-------|---------------|------|---------|
| g01 regex_candidates       | `01_regex_sweep.py`              | deterministic | acronym / initialism / title-case sweep |
| g02 ner_candidates         | `02_ner_sweep.py` (+ `02b` trf)  | deterministic | spaCy NER (sm + transformer variants) |
| g03 normalise              | `03_normalise_and_match.py`      | embedding     | candidate normalisation + catalogue cross-ref |
| g04 define                 | `04_glossary_pass.py`            | LLM           | first-pass definitions (acronyms, ≥5 docs) |
| g05 define_followups       | `05_glossary_v2.py`              | LLM           | tail / titlecase / reground passes |
| g06 merge                  | `06_glossary_merge.py`           | deterministic | merge v1 confident + v2 followups |
| g07 subcategory_propose    | `07_propose_subclustering.py`    | LLM           | propose subcats for big categories |
| g08 subcategory_apply      | `08_apply_subclustering.py`      | LLM           | apply proposed subcats to entries |
| g09 metadata_fingerprint   | `09_metadata_fingerprint.py`     | deterministic | per-term metadata fingerprint vs base rate |
| g10 finalise               | `10_glossary_v3_merge.py`        | deterministic | merge → JSON / MD / HTML |
| g11 inverse_signatures     | `11_*` + `12_*`                  | deterministic | per-project vocab + per-term top-projects |

Engine sources copied to `pipeline/development/arena_glossary/` (no deletes from
their original `corpora/arena/entity_extraction/code/` location).

## Engine vs config

**Engine (this directory):** regex pattern set, NER call, embedding-normalise,
LLM define/followup/subcategory loops with `{token}` substitution, fingerprint
computation, inverse signature computation, render.

**Config (`domains/<corpus>/domain.yaml` `glossary:` block):**
- `prompt_tokens` — per-corpus values for `glossary_purpose`,
  `primary_grouping_field`, `secondary_grouping_field`, plus the standard
  top-level prompt tokens (`audience_persona`, `corpus_short_description` etc.)
- `candidate.stoplist_path` — per-corpus acronym false-positives
  (e.g. `domains/arena/glossary_stoplist.txt`)
- `normalise.catalogue_path` — per-corpus catalogue CSV
- `fingerprint.{project,category,programme,lead_org,year}_field` —
  per-corpus metadata field names (ARENA: `kb_associated_project`;
  ANAO: `audited_entity`)
- `subcategory.refine_categories` — which v1 categories to sub-cluster
  (corpus-dependent — the technology category dominates ARENA but not ANAO)

## Status (2026-05-08)

All 11 stages have full corpus-agnostic engine bodies driven by the
domain.yaml `glossary:` block. Verified end-to-end on ARENA:
deterministic stages g09/g10/g11 reproduce the original output bit-shape
identically (g09: 860 fingerprints, g10: 760 entries / 100 noise / 11
categories, g11: 489 projects + 760 terms with distinctive cohorts).
Worked example: `corpora/arena/entity_extraction/output/glossary_v3.{json,md,html}`.

LLM stages (g04, g05, g07, g08) use tokenised prompts with corpus-agnostic
text — verbatim ARENA references replaced by `{audience_persona}`,
`{corpus_full_name}`, `{corpus_short_description}`, `{glossary_purpose}`,
`{style_guidance}`. ANAO `glossary:` block is populated as a skeleton;
running ANAO requires an ANAO-shaped portfolio CSV (or accept the
catalogue-only fingerprint with portfolio_path null).

## Run

```
python -m pipeline.run --domain arena --step glossary_candidates
python -m pipeline.run --domain arena --step glossary_ner
...
python -m pipeline.run --domain arena --step glossary_finalise
python -m pipeline.run --domain arena --step glossary_inverses
```

`run.py` dispatch entries for all 11 stages live in `pipeline/run.py`.
