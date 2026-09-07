# feat(phase-5): map rescoring, measured: sample 1's document set from 68 towards fourteen, kept or deleted by its delta on score, dollars and spread [slice 04]

**Issue:** #82 · **Spec:** PLAN.md#4-phases, row "5 Report" and the Phase 5 milestone note · **Plan:** plans/phase-5/04-map-rescoring-measured.md
**Depends on:** #81
**Labels:** phase-5

## Deliverable

The map's document scoring is redesigned so sample 1's first matter's document set comes down
from 68 documents towards the key's fourteen with no decoy, explained by the map's own edges
and not cut at a count. Every phase 3 and 4 test still passes on the three samples and both
digest files are repinned. The slice 03 chain is rerun on the new dossier and the pull request
carries before and after, side by side: set size, dossier tokens, rubric score a and b,
spread, recall, dollars. The founder keeps or deletes the redesign on that table, as
`RULES.md` gate 1 asks.

## Mechanism

In `src/rlm/map.py`, the proposed rule, tested against its consumer: the set is a tight core,
documents sharing a defining value of the matter with the seed's note, plus every document a
consequence link or a version pair reaches from the core; `CLUSTER_SHARE` is replaced by that
rule. DR-029, rank 48 today, is reached by the reserve figure `rlm.dossier.reserve_rows`
already joins to DR-088. The four rescorings the phase 4 builder tried (personalised PageRank,
reseeding on the top k, core share, dropping bare count edges) pushed DR-029 lower and are not
retried. The writes are the slice 03 calls, about $0.10. If the rule cannot hold the fourteen
with no decoy on sample 1 while `northwind` keeps its four and drops Granite, the pull request
says so with the ranks and edges and the founder decides between the 68 and a second attempt.

## Acceptance criterion

Given slice 03 is merged and pass a's `grade.json` on the 68-document dossier is on disk,
when the map is rescored, `python -m rlm.map` and `python -m rlm.dossier` run on the three
samples, `python -m rlm.pin --maps` and `--dossiers` repin them, `python -m rlm.write
samples/atlas runs/atlas --passes 2` reruns, and `pytest -q` runs,
then every phase 3, 4 and 5 test passes on `atlas`, `northwind` and `northstar-dental`; the
map's readout prints sample 1's cluster size and the dossier's readout prints its set size
and estimated tokens, both smaller than before; every document in sample 1's set is reached
from the seed by an edge the map names in its `why` (a shared value of the matter, a
consequence link or a version pair); the pull request body carries, side by side, before and
after: set size, dossier tokens, rubric score a and b, spread, recall, dollars of the two
passes; `tests/phase3-digests.json` and `tests/phase4-digests.json` are repinned in the same
pull request.

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
