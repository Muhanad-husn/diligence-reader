# feat(phase-6): a second matter [slice 04]

**Issue:** #99 · **Spec:** PLAN.md#4-phases, row "6 Widen" · **Plan:** plans/phase-6/04-second.md
**Depends on:** #96
**Labels:** phase-6

## Deliverable

`python -m rlm.widen second samples/atlas samples/atlas-second` adds sample 2's eleven documents
as a ninth folder `data_room/08_Northwind_Contracts/` with ids DR-101 to DR-111, copied byte for
byte from `samples/northwind/sample_data_room/Northwind_Logistics/`. Key by construction: sample 1's
53 facts plus sample 2's 16 facts with their documents remapped to the new ids; required documents
are the union of both; decoys are sample 1's five plus the Granite MSA; the answer stays sample 1's
(a 400m repricing outranks a 12.4m cliff); rubric and bar unchanged. The brief gains one paragraph
saying the room also holds the target's Northwind Logistics contracts and their ARR schedule. The
variant has 111 documents, the key has 69 facts, 24 required documents, 6 decoys. The report's first
finding cites sample 1's matter and a finding citing the Meridian MSA appears before any decoy. Recall
100 over all 69 facts. The chain runs, the harness passes or names the first failing phase. Digests pinned.

## Mechanism

New module `src/rlm/widen/second.py`. New test module `tests/test_phase6_second.py` checking 111
documents, 69 facts, 24 required, 6 decoys, first finding cites sample 1's matter, Meridian MSA
finding before decoys. Documents copied from sample 2; ids, key facts and briefs remapped deterministically.

## Acceptance criterion

Given slice 01 is merged,
when the generator, the chain and `pytest -q tests/test_phase6.py tests/test_phase6_second.py` run,
then the variant has 111 documents; the key has 69 facts, 24 required documents, 6 decoys; the report's
first finding cites sample 1's matter and a finding citing the Meridian MSA appears before any decoy
(the knob-specific test); recall 100 over all 69 facts; regeneration byte-identical; harness passes or
names the first failing phase; digests pinned.

## Files

```aeo-independence
slice: 04-second
creates: src/rlm/widen/second.py
creates: tests/test_phase6_second.py
creates: tests/phase6-second-digests.json
creates: samples/atlas-second/
depends-on: 01-generator-control
```

## Out of scope

A generated second matter. Changing the dossier's matter ranking.
