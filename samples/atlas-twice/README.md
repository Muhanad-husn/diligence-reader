# atlas-twice

Written by `python -m rlm.widen twice samples/atlas samples/atlas-twice`, from
`runs/atlas/sections.jsonl` as `tests/phase1-digests.json` pins it.

The knob is `twice`. The room is 200 markdown documents, one section of the source per block,
under `data_room/`. The key keeps the source's ids, required documents, decoys, answer, rubric
and bar, and points its `documents` map at the new paths.

Facts: 53.

Facts dropped: none

## The sister entity

The knob clones the 81 documents sample 1's key marks neither required nor a decoy into a sister
entity's room, `data_room/09_Sister_Entity/`, and clones the 19 of them that write the most
section text a second time, so the room holds 100 clones with the ids DR-201 to DR-300. Pass B
writes its own names and its own suffix as well as its own shift and its own factor, because 19
clones written the way pass A writes them would stand in the room as near duplicates of
documents already there.

| | pass A | pass B |
|---|---|---|
| clones | 81 | 19 |
| ids | DR-201 to DR-281 | DR-282 to DR-300 |
| years shifted back | 2 | 5 |
| factor | 1.46 | 0.64 |
| identifier suffix | `-SE` | `-SG` |

| sample 1 | pass A | pass B |
|---|---|---|
| `VistaPort` | `Beaconvale` | `Calderwood` |
| `Northstar` | `Eastridge` | `Southgate` |
| `AURORA` | `BOREALIS` | `ZEPHYR` |
| `Trust Reset` | `Confidence Rebuild` | `Loyalty Restart` |
| `IronLake` | `Stonecreek` | `Millbrook` |
| `Juniper & Rowe` | `Alder & Finch` | `Birch & Kane` |
| `Kestrel` | `Osprey` | `Harrier` |

After the rewrites 2 sections still held a planted quote and were dropped from their clone.

A clone carries none of the planted truth. Every clone is read against every fact of sample 1's
key before a file is written: a quote, a comparison and a document as a flattened lower cased
substring, an identifier and a number delimited, and a date both as its ISO value and as any
date surface that normalises to it. One match raises ValueError naming the fact, the clone and
the surface, and the run writes nothing.
