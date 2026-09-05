# 02: The index: dates, amounts, names, identifiers, on sample 1

Issue: to be filed

## Goal

`runs/atlas/index.jsonl` carries every planted number, date and identifier of sample 1 against
one of its own documents, matched on a normalised value, not on the surface string.

## Acceptance criterion

Given `runs/atlas/sections.jsonl` is built by slice 01,
when `pytest -q tests/test_phase1.py -k index` runs,
then `runs/atlas/index.jsonl` is written, two runs are byte identical, and for each of the
twenty-nine phase 1 facts in `samples/atlas/key.json` there is an index record whose kind
matches the fact's kind, whose `docs` intersect the fact's documents, and whose normalised
value equals the fact's value put through the same normaliser: `912.8m` to `912800000.0`
records, `$240m` and `$465m` to USD, `$12m`, `45-day` to `45.0` days, `36 months` and
`twenty-four (24) months` to months, `615` and `408` to counts, `$34m` and `$410m` to USD, the
eight dates to ISO, and the eight identifiers verbatim, `NQ-17`, `AURORA`, `Trust Reset`,
`IronLake`, `Juniper & Rowe`, `Kestrel`, `vpauth-legacy-2019` and
`legacy_uap_backup_2021.tar.gz`. Every index record's anchor resolves to a section written by
slice 01.

## Mechanism

- No skill, plugin or MCP fits. Regular expressions over section text and workbook cells, plus
  one normaliser module.
- `src/rlm/amounts.py` holds `normalise_amount(surface) -> (value, unit)` and
  `normalise_date(surface) -> str`. The test applies the same functions to the key's values, so
  no rule is written against a key string. `unit` is one of `USD`, `percent`, `records`,
  `months`, `days`, `count`, or null.
- The spelled-out form `twenty-four (24) months` in `Seller_Representation_Schedule.pdf` is read
  from its parenthesised digits, not from an English number table.
- An amount inside a workbook cell takes its unit from the sheet's own header text where the
  header says one, and carries a null unit where it does not. The northstar workbook proves this
  matters: its key value `24.8` is a bare cell in a sheet whose header says USD millions.
- Names and identifiers: a token that repeats across documents and is not a dictionary word, plus
  the capitalised multi-word forms. `Trust Reset` and `Juniper & Rowe` are names; `NQ-17`,
  `vpauth-legacy-2019` and `legacy_uap_backup_2021.tar.gz` are identifiers. The key's
  `identifier` facts are satisfied by a record of kind `identifier` or `name`, because the
  boundary between the two is not worth a rule.
- No model call, no gateway call.

## The index shape

```json
{"kind": "amount",
 "surface": "912.8m",
 "value": 912800000.0,
 "unit": "records",
 "docs": ["data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"],
 "anchors": ["data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf#p2l14"],
 "context": "The legacy backup object holds 912.8m records."}
```

`kind` is one of `date`, `amount`, `name`, `identifier`, `status`, `version-pair`, `series`.
This slice writes the first four. `docs` and `anchors` are lists on every record so that the
three kinds slice 03 adds need no second shape. Records are written sorted by kind, then value,
then first anchor.

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

Status words, version pairs and series, which are slice 03. Samples 2 and 3. Any grouping of two
names that look like the same entity: names are grouped by identifier only, and where that fails
it is priced in phase 6, not fixed here.
