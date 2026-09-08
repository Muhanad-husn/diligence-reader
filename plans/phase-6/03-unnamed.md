# 03: The matter named nowhere, linked only by dates and numbers

Issue: [#98](https://github.com/Muhanad-husn/RLM/issues/98)

## Goal

The unnamed knob removes every name the matter is known by across functions (AURORA, NQ-17,
Trust Reset, "login friction", "credential hygiene") and the two file-name identifiers that link
its documents (`legacy_uap_backup_2021.tar.gz`, `vpauth-legacy-2019`), replacing each with a
plain phrase fixed per identifier (for example "the programme", "the ticket", "the archive",
"the signing key"), the same phrase in every document. Dates, record counts, amounts, people and
organisations are untouched. Key by construction: the identifier facts for the removed names are
dropped and listed in the README; quote facts whose text carried one carry the rewritten text.

## Acceptance criterion

Given slice 01 is merged,
when the generator, the chain and `pytest -q tests/test_phase6.py tests/test_phase6_unnamed.py`
run,
then no file of the variant contains any removed name (case-insensitive, the knob-specific test);
the key holds 53 minus the dropped identifier facts, each drop named in the README; regeneration
byte-identical; harness passes or names the first failing phase; digests pinned in
`tests/phase6-unnamed-digests.json`.

## Mechanism

New module `src/rlm/widen/unnamed.py`. New test module `tests/test_phase6_unnamed.py` checking
no removed name in any file (case-insensitive), key drops listed in README. Replacement phrases
fixed per identifier, deterministic.

## Files

```aeo-independence
slice: 03-unnamed
creates: src/rlm/widen/unnamed.py
creates: tests/test_phase6_unnamed.py
creates: tests/phase6-unnamed-digests.json
creates: samples/atlas-unnamed/
depends-on: 01-generator-control
```

## Out of scope

Removing dates or numbers. Fixing the map.
