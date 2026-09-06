# 01: Map on sample 1: document graph, and the matter's cluster

Issue: [#53](https://github.com/Muhanad-husn/RLM/issues/53)

## Goal

`runs/atlas/map.json` exists, written by `python -m rlm.map samples/atlas runs/atlas` from the
index, the sections and the pinned notes with no model call. Its top-ranked matter's cluster
holds all fourteen required documents and none of the five decoys. Two runs are byte-identical.

## Acceptance criterion

Given `runs/atlas/index.jsonl`, `runs/atlas/sections.jsonl` and the pinned `runs/atlas/notes/`
matching `tests/phase2-digests.json`,
when `python -m rlm.map samples/atlas runs/atlas` runs twice, the second time into a temporary
directory, and then `pytest -q tests/test_phase3.py` runs,
then `map.json` parses with sorted keys and one trailing newline; the two runs are
byte-identical; every document the key names is a node; every edge names its two documents,
its kind (one of `identifier`, `cross-reference`, `date`, `version`), the shared value, and
one resolving anchor in each document (a `date` edge's anchors are the two dated sections);
the first matter's `cluster` contains every document of the key's phase 3 `matter-documents`
fact and no document of the key's `decoys`; no test reads a key value into the map; and the
readout prints, for the sample, nodes, edges by kind, matters, the cluster size, planted
cluster recall as a percentage, decoys in the cluster, and seconds.

## Mechanism

Survey in order. No skill, plugin or MCP fits. No library: a graph of at most a few hundred
nodes with weighted edges needs dictionaries and a sort, not `networkx`; no new dependency. No
model call. `src/rlm/map.py` reads the three inputs and writes `map.json` and a `main(argv)`.

The design points the builder starts from, open to change against the test:

- **Nodes** come from the key's `documents` order, with title, folder, first date and status
  words from the index.
- **Edges**: `identifier` from index records of kind `identifier` and one-word upper-case
  `name` records shared by two or more documents (the rule `index._shared_identifiers`
  already uses); `cross-reference` from a note's `cross_references` whose value is carried by
  another document's index or note; `date` for two documents whose dated sections fall within
  seven days; `version` from the index's `version-pair` records.
- **Weight**: a shared value's weight falls with the number of documents that carry it (AURORA
  in 16 documents weighs less than `vpauth-legacy-2019` in 4), and a value the note wrote as a
  cross reference or inside a flag weighs more than one only the index saw.
- **A matter** is seeded from the documents whose notes carry flags or concealed items and
  share the rarest values. Its cluster is the documents whose weighted links to the seed clear
  a cut. The cut is a fixed rule of the code, not a number tuned to sample 1's fourteen. The
  room's own index (DR-001) and Q&A log (DR-004) are documents like the others and their
  notes' cross references count.
- **Tests** follow `tests/test_phase1.py`: a module-level fixture that runs the map twice,
  per-sample tests parametrised through `tests/conftest.py`, a `readout(terminalreporter)`.

## The map shape

```json
{"sample": "atlas",
 "documents": [{"doc": "DR-069", "path": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf",
                "folder": "05_Security_IT_and_Infrastructure", "date": "2025-11-12", "status": ["draft"]}],
 "edges": [{"a": "DR-069", "b": "DR-074", "kind": "identifier", "value": "vpauth-legacy-2019",
            "anchors": {"a": "...#p3l2", "b": "...#p1l7"}, "weight": 0.25}],
 "matters": [{"id": 1, "seed": ["DR-069", "DR-068", "DR-073"], "date": "2025-10-18",
              "cluster": ["DR-013", "DR-029", "DR-035", "DR-048", "DR-050", "DR-068", "DR-069", "DR-073", "DR-074", "DR-081", "DR-082", "DR-087", "DR-088", "DR-096"],
              "ranked": [{"doc": "DR-069", "score": 3.1, "why": ["vpauth-legacy-2019", "legacy_uap_backup_2021.tar.gz"]}],
              "versions": [], "consequences": []}]}
```

`ranked` lists every document in the room in descending score; `cluster` is the prefix above
the cut, sorted by id. `versions` and `consequences` are empty in this slice and filled in
slice 02. Documents in a sample whose key has no `DR-` ids, as `northwind` and
`northstar-dental`, use the path as `doc`.

## Files

```aeo-independence
slice: 01-map-atlas
creates: src/rlm/map.py
creates: tests/test_phase3.py
depends-on: 00-repin-notes
```

## Out of scope

Consequence links, version pairs inside the matter, lesser matters ranked by money (slice 02).
Samples 2 and 3 (slice 03). Digests and the status row (slice 04).
