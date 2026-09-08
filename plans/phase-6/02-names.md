# 02: Names spelled inconsistently

Issue: [#97](https://github.com/Muhanad-husn/RLM/issues/97)

## Goal

The names knob respells the names of people and organisations (the target company, the acquirer,
counsel, the forensic firm, the insurer, named executives) with a seeded choice per document among
fixed variants: case changes, initials for first names, surname first, a dropped or added corporate
suffix, a space or hyphen inside a compound name, one transposed-letter misspelling. Identifiers,
numbers and dates are not touched. Fact values by construction: quote facts whose text carries a
respelled name carry the text as it stands in the fact's first document; the rest are unchanged.

## Acceptance criterion

Given slice 01 is merged,
when `python -m rlm.widen names samples/atlas samples/atlas-names` runs, the chain runs, and
`pytest -q tests/test_phase6.py tests/test_phase6_names.py` runs,
then at least ten distinct names are respelled and every respelled name appears in at least three
spellings across the room (the knob-specific test reads the README's list against the files);
regeneration is byte-identical; the harness's phase 1 to 5 tests pass on `atlas-names` or the
readout names the first phase that fails; digests pinned in `tests/phase6-names-digests.json`.

## Mechanism

New module `src/rlm/widen/names.py`. New test module `tests/test_phase6_names.py` checking at
least ten distinct names respelled, every respelled name in at least three spellings, matching
the README's list against the files. Respelling variants fixed per name, seeded per document,
deterministic.

## Files

```aeo-independence
slice: 02-names
creates: src/rlm/widen/names.py
creates: tests/test_phase6_names.py
creates: tests/phase6-names-digests.json
creates: samples/atlas-names/
depends-on: 01-generator-control
```

## Out of scope

Respelling identifiers or numbers. Fixing the map.
