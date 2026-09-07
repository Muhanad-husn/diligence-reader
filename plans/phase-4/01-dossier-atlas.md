# 01: Dossier on sample 1: document set, timeline, names, figures, models blind to it

Issue: [#63](https://github.com/Muhanad-husn/RLM/issues/63)

## Goal

`runs/atlas/dossier.md` exists, written by `python -m rlm.dossier samples/atlas runs/atlas`
from the map, the index, the sections and the pinned notes with no model call. Its first
matter's document set holds all fourteen required documents and none of the five decoys, and
every required document is ranked above every decoy. The dossier carries the matter's
timeline, the names each function gave it, its figures with sources, and the models blind to
it. Two runs are byte-identical. The map's one-per-matter cap on consequences is lifted and
its cluster cut is brought in, as the founder approved on 2026-09-07; sample 1's cluster is
expected near fourteen.

## Acceptance criterion

Given `runs/atlas/index.jsonl`, `runs/atlas/sections.jsonl` and the pinned `runs/atlas/notes/`
matching `tests/phase2-digests.json`,
when `python -m rlm.map samples/atlas runs/atlas` runs, then `python -m rlm.dossier
samples/atlas runs/atlas` runs twice, the second time into a temporary directory, and then
`pytest -q tests/test_phase3.py tests/test_phase4.py` runs,
then `dossier.md` exists with one trailing newline and the two runs are byte-identical; the
first matter's `Documents` section lists every id in the key's `matter-documents` fact and no
id in the key's `decoys`; every document of `matter-documents` appears in the dossier's ranked
document list above every decoy; every phase 1 and phase 2 fact of the key has a row whose
quote or figure carries the fact's value (after straightening) and whose anchor parses,
belongs to one of the fact's documents and is a section anchor of that document; the `Names`
section lists every name the notes' cross references give the matter (the key's `workstream`,
`programme` and `ticket` facts name them), each with a document and an anchor; the `Models
blind to it` section carries two series breaks (DR-048 and DR-050, both at 2025-10-20) and two
models after (DR-096 and DR-005), each with its anchor; the map's first matter carries the
same four consequences; `tests/phase3-digests.json` is repinned to the new `map.json` and
every phase 3 test passes; and the readout prints, for the sample, document set size, planted
recall as a percentage, decoys in the set, rows, names, consequences, and seconds.

## Mechanism

Survey in order. No skill, plugin or MCP fits. No library: the dossier is a sort over rows
read from four JSON files, written as markdown by string formatting; no templating engine, no
new dependency. No model call.

`src/rlm/map.py`: `CONSEQUENCE_SHARE` and the one-per-kind selection in `series_break` and
`model_after` give way to every series that turns within `DATE_WINDOW` of the matter date and
every model dated after it that shares a figure with a cluster document; `CLUSTER_SHARE`
rises from a hundredth of the top score to the fixed rule the builder finds holds the
fourteen with no decoy on sample 1 and, in slice 03, the four on `northwind` and the three
on `northstar-dental`. The rule is one constant or one comparison, stated in the docstring.

`src/rlm/dossier.py`: reads `map.json`, `index.jsonl`, `sections.jsonl` and `notes/`, writes
`dossier.md` and a `main(argv)`. Sections per matter, in this order: `Documents` (the
cluster, one line per document with title, folder, date, status words and its rank),
`Timeline` (every dated figure and dated flag quote of the set's notes, one row per statement,
sorted by date), `Names` (every `cross_references` value of kind ticket, code or name that two
or more set documents share, with the documents and one anchor each), `Figures` (every figure
of the set's notes with its quote and anchor, sorted by document then anchor), `Models blind
to it` (the map's consequences, one row each: kind, document, period or date, series name or
figure shared, anchor). The comparisons and the lesser matters are empty sections filled in
slice 02.

Row grammar, fixed for the phase: `- <date or figure> | <doc> | <quote> | <anchor>`; a
`Documents` line is `- <rank>. <doc> | <title> | <folder> | <date> | <status>`. Quotes are the
notes' quotes verbatim.

`tests/test_phase4.py` follows `tests/test_phase3.py`: a module-level fixture that runs the
dossier twice, per-sample tests parametrised through `tests/conftest.py`, a
`readout(terminalreporter)`, and a sample whose inputs are absent is skipped. The test reads
the key's `matter-documents`, `decoys`, and the phase 1 and 2 facts' values and documents, and
nothing else.

## Files

```aeo-independence
slice: 01-dossier-atlas
edits: src/rlm/map.py
edits: tests/test_phase3.py
edits: tests/phase3-digests.json
creates: src/rlm/dossier.py
creates: tests/test_phase4.py
```

## Out of scope

The seven comparison rows and the lesser matters (slice 02). Samples 2 and 3 (slice 03).
Digests, the status row and the founder's reading (slice 04). A required document outside
the set or a decoy inside it is not acceptable; it is reported with the document's map score
and the edges that carry it, and the map's scoring is revised, not the test loosened.
