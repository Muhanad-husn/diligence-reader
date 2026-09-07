# 04: A second matter

Issue: [#99](https://github.com/Muhanad-husn/RLM/issues/99)

## Goal

The second knob adds sample 2's eleven documents as a ninth folder `data_room/08_Northwind_Contracts/`
with ids DR-101 to DR-111, copied byte for byte from `samples/northwind/sample_data_room/Northwind_Logistics/`.
Key by construction: sample 1's 53 facts plus sample 2's 16 facts with their documents remapped to the
new ids; required documents are the union; decoys are sample 1's five plus the Granite MSA; the answer
stays sample 1's (a 400m repricing outranks a 12.4m cliff); rubric and bar unchanged. The brief gains
one paragraph saying the room also holds the target's Northwind Logistics contracts and their ARR schedule.

## Acceptance criterion

Given slice 01 is merged,
when the generator, the chain and `pytest -q tests/test_phase6.py tests/test_phase6_second.py` run,
then the variant has 111 documents; the key has 69 facts, 24 required documents, 6 decoys; the report's
first finding cites sample 1's matter and a finding citing the Meridian MSA appears before any decoy
(the knob-specific test); recall 100 over all 69 facts; regeneration byte-identical; harness passes or
names the first failing phase; digests pinned.

## Mechanism

New module `src/rlm/widen/second.py`. New test module `tests/test_phase6_second.py` checking 111 documents,
69 facts, 24 required, 6 decoys, first finding cites sample 1's matter, Meridian MSA finding before decoys.
Documents copied from sample 2; ids, key facts and briefs remapped deterministically.

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
