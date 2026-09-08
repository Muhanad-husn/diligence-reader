# feat(phase-6): twice the documents [slice 05]

**Issue:** #100 · **Spec:** PLAN.md#4-phases, row "6 Widen" · **Plan:** plans/phase-6/05-twice.md
**Depends on:** #96
**Labels:** phase-6

## Deliverable

`python -m rlm.widen twice samples/atlas samples/atlas-twice` clones the 81 documents of sample 1
that are neither required nor decoys into a sister entity's room under `data_room/09_Sister_Entity/`,
ids DR-201 up: the entity's name replaced by a fixed second name, every date shifted back two years,
every amount and count multiplied by a fixed factor and rounded as the source rounds, every identifier
given a fixed suffix. The 19 largest of those clones are cloned a second time with a different factor
and shift, so the room holds exactly 200 documents. Code checks that no planted value of the key
(numbers, dates, identifiers, quotes) appears in any clone and refuses to write the variant if one
does. Key by construction: sample 1's 53 facts, documents, decoys, answer, rubric and bar unchanged.
The chain runs, the harness passes or names the first failing phase. Ledger phase 6 rows for
`atlas-twice` under $2. Digests pinned.

## Mechanism

New module `src/rlm/widen/twice.py`. New test module `tests/test_phase6_twice.py` checking 200
documents, no planted value in any clone. First 81 clones with dates shifted two years back, amounts
and counts multiplied by factor and rounded, identifiers given suffix; 19 largest cloned again with
different factor and shift. All deterministic, seeded.

## Acceptance criterion

Given slice 01 is merged,
when the generator, the chain and `pytest -q tests/test_phase6.py tests/test_phase6_twice.py` run,
then 200 documents; no planted value in any clone (the knob-specific test); regeneration byte-identical;
harness passes or names the first failing phase; ledger phase 6 rows for `atlas-twice` under $2;
digests pinned.

## Files

```aeo-independence
slice: 05-twice
creates: src/rlm/widen/twice.py
creates: tests/test_phase6_twice.py
creates: tests/phase6-twice-digests.json
creates: samples/atlas-twice/
depends-on: 01-generator-control
```

## Out of scope

Cloning required or decoy documents. A fifth knob.
