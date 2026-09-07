# 04: Map rescoring, measured, the set from 68 towards fourteen, kept by its delta

Issue: [#82](https://github.com/Muhanad-husn/RLM/issues/82)

## Goal

The map's document scoring is redesigned so that sample 1's first matter's document set
comes down from 68 documents towards the key's fourteen with no decoy, every phase 3 and 4
test still passes on the three samples, and the slice 03 chain rerun on the new dossier
gives a measured delta on score, dollars and spread. The redesign is kept when a number
moves in its favour and deleted when none does.

## Acceptance criterion

Given slice 03 is merged and pass a's `grade.json` on the 68-document dossier is on disk,
when the map is rescored, `python -m rlm.map` and `python -m rlm.dossier` run on the three
samples, `python -m rlm.pin --maps` and `--dossiers` repin them, `python -m rlm.write
samples/atlas runs/atlas --passes 2` reruns, and `pytest -q` runs,
then every phase 3, 4 and 5 test passes on `atlas`, `northwind` and `northstar-dental`; the
map's readout prints sample 1's cluster size and the dossier's readout prints its set size
and estimated tokens, both smaller than before; every document in sample 1's set is reached
from the seed by an edge the map names in its `why` (a shared value of the matter, a
consequence link or a version pair), so the set is explained and not cut at a count; the
pull request body carries, side by side, before and after: set size, dossier tokens, rubric
score a and b, spread, recall, dollars of the two passes; and the founder's decision to keep
or delete is taken on that table. `tests/phase3-digests.json` and `tests/phase4-digests.json`
are repinned in the same pull request.

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency; the writes are the model
calls of slice 03, about $0.10. In `src/rlm/map.py` the proposed shape, tested against its
consumer: the set is a tight core, documents that share a defining value of the matter with
the seed's note, plus every document a consequence link or a version pair reaches from the
core; `CLUSTER_SHARE` is replaced by that rule. The audit committee's DR-029, at rank 48
today, is reached by the reserve figure that `rlm.dossier.reserve_rows` already joins to
DR-088; the four rescorings the phase 4 builder tried (personalised PageRank, reseeding on
the top k, core share, dropping bare count edges) are recorded in the Phase 5 milestone as
having pushed DR-029 lower and are not retried. If the rule cannot hold the fourteen with no
decoy on sample 1 while `northwind` keeps its four and drops Granite, the pull request says
so with the ranks and the edges, and the founder decides between the 68 and a second
attempt.

## Files

```aeo-independence
slice: 04-map-rescoring-measured
edits: src/rlm/map.py
edits: src/rlm/dossier.py
edits: tests/test_phase3.py
edits: tests/test_phase4.py
edits: tests/phase3-digests.json
edits: tests/phase4-digests.json
depends-on: 03-grade-spread-atlas
```

## Out of scope

The bake-off (slice 05). Any change to the writer, the verifier or the grader. A hard-coded
document id or a cut tuned to rank 48. Any map change that moves a decoy into a set or a
planted document out of one on any sample.
