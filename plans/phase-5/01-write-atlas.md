# 01: Report on sample 1, one call from the dossier, cited, recall 100 by code

Issue: [#79](https://github.com/Muhanad-husn/RLM/issues/79)

## Goal

`runs/atlas/report.md` exists, written by `python -m rlm.write samples/atlas runs/atlas`
from `brief.md` and `dossier.md` in one gateway call, in the five sections the brief asks
for, every sentence cited as `[<doc> | <anchor>]`, and `rlm.grade.measure_recall` reads 100
over the key's 53 facts.

## Acceptance criterion

Given `runs/atlas/dossier.md` matches `tests/phase4-digests.json` and `OPENROUTER_API_KEY`
is set,
when `python -m rlm.write samples/atlas runs/atlas` runs and then `pytest -q
tests/test_phase5.py` runs,
then `report.md` exists with one trailing newline and five second-level headings in the
brief's order (executive summary, findings ranked by materiality, the most material issue
quantified, lesser issues, open items); every sentence outside the recommendation line and
`Calculation:` lines ends in one or more citations `[<doc> | <anchor>]` whose doc and anchor
appear together on one row of the dossier; `measure_recall` over the key reads 100 and the
readout prints the missed ids when it does not; the gateway printed the estimated input
tokens and the price before the call and `LEDGER.md` gained one phase 5 line for `atlas`
with the gateway's reported tokens; the writer's default model is `z-ai/glm-5.3-flash` and
`--model` takes any id of the price table; the writer refuses to run when the dossier is
absent; no line of code outside the tests reads the key.

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency; one model call. A new
module `src/rlm/write.py` with `build_messages(brief, dossier)`, `parse_reply`,
`write_report`, `main(argv)`. The prompt: the brief's deliverables as the five headings; the
citation grammar; the rule that quotes, figures, dates and names are copied from the dossier
rows and never paraphrased; the rule that the recommendation carries one number and a range
on a `Calculation:` line naming its operands; the rule that certainty words are the source's.
The dossier goes in whole as the user message. `Gateway.complete` gains a `json` flag,
default true, false for this call; nothing else in the gateway changes. Output cap 8000
tokens. The ledger batch is opened by `rlm.write.main` with phase 5, exactly as `rlm.notes`
does. `tests/test_phase5.py` follows `tests/test_phase4.py`: module fixture, per-sample tests
through `tests/conftest.py`, `readout(terminalreporter)` printing recall, missed ids, the
citation count, dollars and seconds per sample, skip when `report.md` is absent. Tests
committed red first.

## Files

```aeo-independence
slice: 01-write-atlas
edits: src/rlm/gateway.py
creates: src/rlm/write.py
creates: tests/test_phase5.py
```

## Out of scope

The verifier and the return-once loop (slice 02). The rubric grade, the second write and the
spread (slice 03). Samples 2 and 3 and any model but the default (slice 05). A recall under
100 is reported with the missed ids and the dossier rows that carry them; the prompt is
revised, and the test is not loosened. Two failures are the phase's second attempt under
`RULES.md` gate 3.
