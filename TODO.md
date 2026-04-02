# ARENA Delivery Registry — TODO

## QA / Data Quality

- [ ] **Retry 11 parse-error records from full-doc recheck** — doc_0394 (9 records: DLV-19654–19678) + DLV-12526, DLV-4423, DLV-37417. These replaced meaningful verdicts with `parse_error`, likely because Haiku truncated mid-YAML on a very long prompt. Cheap (~11 API calls). Use `04d_recheck_fulldoc.py` or a targeted batch.

- [ ] **Retry 313 parse-error QA records from original verification pass** — Haiku occasionally returns malformed YAML. Worth a batch retry pass (<$1).

- [ ] **Classification recheck for ~49 remaining `wrong` records** — one-per-document scattered records not yet addressed by full-doc passes. Run `04c_recheck_flagged.py --field classification_verdict --verdicts wrong --batch submit`.

## Registry Maintenance

- [ ] **Monthly KB export refresh** — pull a fresh `arena-kb-export_XXXXXXXXXX.csv`, diff against previous with the pattern used on 2026-04-02 to identify new documents. There is a ~weeks-to-months lag between ARENA publishing documents and them appearing in the KB catalogue, so monthly checks will catch new additions reliably. Extract lessons learnt reports as a priority. 31 new documents were found in the April 2026 refresh — 14 are lessons learnt reports not yet in the registry.

## Dashboard

- [ ] **Portfolio coverage view** — show which of the 769 ARENA projects have KB documents vs not, filterable by year/type.

- [ ] **Document quality indicator** — surface per-doc QA stats (% confirmed, % wrong) on cards or in a separate tab.
