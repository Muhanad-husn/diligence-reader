# 01: The key shape, and sample 1's key and brief

Issue: [#1](https://github.com/Muhanad-husn/RLM/issues/1)

## Goal

`samples/atlas/key.json` loads through `src/rlm/key.py`, and every document it names resolves
to one file in the data room.

## Acceptance criterion

Given `samples/atlas/key.json` and `samples/atlas/brief.md` exist,
when `pytest -q tests/test_phase0.py -k key` runs,
then for sample `atlas` the key loads, every fact's documents resolve to existing files, every
fact names a phase from 1 to 5, the fourteen required documents and the five decoys are
disjoint, the answer carries the number 400 with range 375 to 525, and the brief exists.
Samples `northwind` and `northstar-dental` are skipped with the reason "no key.json yet".

## Mechanism

- No skill, plugin or MCP fits: the key is data written by hand from
  `samples/atlas/key/expected_findings.json` and `ANSWER_KEY_DO_NOT_INGEST.md`.
- Library: `openpyxl` (already a dependency) reads `Data_Room_Index.xlsx` once, at authoring
  time, to derive the `DR-###` to file map the way the winner's `extract_corpus.py` did
  (title tokens against file names). The map is pinned into `key.json` so no later phase
  derives it again. Any id that does not match one file is resolved by hand and noted.
- No model call.

## The key shape

```json
{
  "sample": "atlas",
  "brief": "brief.md",
  "documents": {"DR-069": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"},
  "required_documents": ["DR-069", "..."],
  "decoys": [{"document": "DR-031", "why": "Sales/use tax nexus, $6m to $9m, an order of magnitude smaller."}],
  "facts": [
    {"id": "records-total", "kind": "number", "value": "912.8m", "documents": ["DR-069", "DR-073"], "phase": 1},
    {"id": "bulk-export-probable", "kind": "quote", "value": "bulk export is probable", "documents": ["DR-069"], "phase": 2},
    {"id": "reserve-vs-exposure", "kind": "comparison", "value": "$12m against $240m to $465m", "documents": ["DR-029", "DR-088"], "phase": 4}
  ],
  "answer": {"action": "reprice or escrow", "number": 400, "low": 375, "high": 525, "unit": "USD millions"},
  "rubric": [{"id": 1, "criterion": "Identifies the undisclosed account-data incident", "points": 20, "earns": "..."}],
  "bar": {"perfect": 100, "wrong_under": 40}
}
```

`kind` is one of `number`, `date`, `identifier`, `quote`, `document`, `comparison`. `phase` is
the first phase whose artefact must carry the fact: 1 for numbers, dates and identifiers the
index must hold; 2 for quotes the notes must verify; 3 for cluster membership; 4 for
comparisons the dossier makes; 5 for the answer. Sample 1's facts come from `key_terms`,
`required_documents`, `decoy_documents` and the price bridge in the answer key; the rubric is
the nine rows of `scoring_rubric.md` verbatim.

`samples/atlas/brief.md` is `data_room/README.md` copied, so every sample has its brief at the
same path. The data room copy stays where it is because the winner's trail read it there.

## Files

```aeo-independence
slice: 01-key-atlas
creates: samples/atlas/key.json
creates: samples/atlas/brief.md
creates: src/rlm/key.py
creates: tests/test_phase0.py
edits: tests/conftest.py
```

## Out of scope

The grader, the perfect and wrong reports, and the keys of samples 2 and 3. The phase 1 check
that every planted number is in the index; this slice only checks that the key is well formed
and its documents exist.
