# feat(phase-1): the index: dates, amounts, names, identifiers, on sample 1 [slice 02]

**Issue:** to be filed · **Spec:** PLAN.md#4-phases, row "1 Ingest" · **Plan:** plans/phase-1/02-index-atlas.md
**Depends on:** 01-sections-atlas
**Labels:** phase-1

## Deliverable

`runs/atlas/index.jsonl`, carrying every planted number, date and identifier of sample 1 against one of its own documents. A record carries `kind`, `surface`, `value`, `unit`, `docs`, `anchors` and `context`, with `docs` and `anchors` as lists so the three kinds slice 03 adds need no second shape. `kind` is one of `date`, `amount`, `name`, `identifier`, `status`, `version-pair`, `series`; this slice writes the first four.

## Mechanism

Regular expressions over section text and workbook cells, plus one normaliser module, `src/rlm/amounts.py`, holding `normalise_amount(surface) -> (value, unit)` and `normalise_date(surface) -> str`. The test applies the same two functions to the key's own values, so no rule is written against a key string. This is what the phase turns on: the source says `$12,400,000` and the key says `$12.4m`; the source says `45 days` and the key says `45-day`; the Kestrel access log carries `18 October 2025` and `2025-10-18` in the same column. `unit` is one of `USD`, `percent`, `records`, `months`, `days`, `count`, or null. The spelled-out `twenty-four (24) months` is read from its parenthesised digits, not from an English number table. An amount in a workbook cell takes its unit from the sheet's header where the header says one and carries null where it does not. A key fact of kind `identifier` is satisfied by a record of kind `identifier` or `name`, because the boundary between the two is not worth a rule. No model call, no gateway call.

## Acceptance criterion

Given `runs/atlas/sections.jsonl` is built by slice 01,
when `pytest -q tests/test_phase1.py -k index` runs,
then `runs/atlas/index.jsonl` is written, two runs are byte identical, every index anchor resolves to a section slice 01 wrote, and each of the twenty-nine phase 1 facts in `samples/atlas/key.json` has an index record whose kind matches, whose `docs` intersect the fact's documents, and whose normalised value equals the fact's value through the same normaliser: `912.8m`, `286m`, `8.4m`, `$240m`, `$465m`, `$12m`, `45-day`, `36 months`, `twenty-four (24) months`, `$410m`, `615`, `408`, `$34m`, the eight dates to ISO, and the eight identifiers `NQ-17`, `AURORA`, `Trust Reset`, `IronLake`, `Juniper & Rowe`, `Kestrel`, `vpauth-legacy-2019`, `legacy_uap_backup_2021.tar.gz`.

## Files

```aeo-independence
slice: 02-index-atlas
creates: src/rlm/index.py
creates: src/rlm/amounts.py
edits: src/rlm/ingest.py
edits: tests/test_phase1.py
depends-on: 01-sections-atlas
```

## Out of scope

Status words, version pairs and series, which are slice 03. Samples 2 and 3. Grouping two names that look like the same entity: names are grouped by identifier only, and where that fails it is priced in phase 6.
