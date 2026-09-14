# diligence-reader

Reads an acquisition data room and writes a findings report a deal team can act on: the
matter that connects across the documents under different names, weighed against what the
seller disclosed and reserved, a recommendation with a number, and every sentence cited to
the page it came from and checked against it by code.

Project page: [muhanad-husn.github.io/diligence-reader](https://muhanad-husn.github.io/diligence-reader/)

It is a fixed rebuild of the recursive language model (RLM) run that John Adeojo published
on his Project Atlas data room ([brainqub3/claude_code_RLM](https://github.com/brainqub3/claude_code_RLM),
[brainqub3/synthetic-dataRoom](https://github.com/brainqub3/synthetic-dataRoom)). The RLM
improvises its program per run; this tool keeps the shape of his winning run and replaces
every improvised step with one that is the same on every run. Two of seven stages call a
model. The rest is code that is byte-identical across runs.

| | |
|---|---|
| **100 / 100** | Rubric score on Project Atlas, two runs, spread 0 |
| **82 / 84** | The RLM skill as shipped, same corpus, same grader |
| **about $0.30** | One end-to-end run of the 100-document room |
| **$18.95** | The whole build, 5 to 9 September 2026, every dollar in `LEDGER.md` |

Full results, method and what still stands against it: [`REPORT.md`](REPORT.md).

## How it works

| Stage | Kind | What it does |
|---|---|---|
| Ingest | code | PDF, XLSX, CSV, TXT, EML, MBOX and markdown into sections with anchors, plus an index of dates, amounts, names, identifiers, status words, version pairs and series |
| Notes | model, one call per document | A note under a fixed JSON schema. Every quote and figure is checked against the source by code; a failed note is re-asked once, then dropped and logged |
| Map | code | A document graph over shared identifiers, cross-references, dates and versions. Clusters the matter; consequence links catch a series that breaks at the matter's date and a model dated after it |
| Dossier | code | Per matter: timeline, every name each function gave it, figures with sources, draft against final, reserve against estimate, deadlines against actions, models blind to it, lesser matters ranked by money |
| Write | model, one call | The five-section report from the dossier alone. Every sentence cites; certainty words are copied from the source and never raised |
| Verify | code | Every citation resolves, every number exists in its source, no certainty word climbed, decoys ranked below the main matter. Failures go back to the writer once |
| Grade | code + subagent | Planted-fact recall by code against the sample's key; rubric score by a Claude subagent; spread between two runs |

The stage modules live in `src/rlm/`, one per stage. The package keeps the name `rlm` after
the run it rebuilds.

## Samples

Four corpora ship with the repository or fetch from a public source. Each has a machine-readable
key; nothing is "found" unless a test reads it out of an artefact against that key.

| Sample | What it is | Result |
|---|---|---|
| `atlas` | Project Atlas: 100 documents, six formats, one planted matter across six functions, five decoys, a 100-point rubric | recall 100, rubric 100, spread 0 |
| `northwind` | Eleven contracts and a board deck; a change-of-control cliff on a 30.1% customer, a decoy contract on the same template | recall 100 |
| `northstar-dental` | A numeric contradiction: the CIM claims 18.0% growth, the workbook shows 11.7% | recall 100 |
| `yahoo` | Real SEC filings, Verizon and Yahoo 2016 to 2017, no planted facts; key from the public record. Fetched at run time | recall 86.4 |

Five generated variants of `atlas` (misspelled names, an unnamed matter, a second matter, a
doubled room, a control) are described in `REPORT.md` section 3 and `PLAN.md` section 10.
Details of every sample and its key: [`samples/README.md`](samples/README.md).

## Run it

Python 3.13. Model calls go through OpenRouter; the tool refuses to call a model before it
has counted the input tokens, printed the price and checked the ledger against the ceiling.

```
pip install -e ".[dev]"
export OPENROUTER_API_KEY=...        # or put it in .env

python -m rlm.ingest  samples/atlas runs/atlas
python -m rlm.notes   samples/atlas runs/atlas     # model: GLM 5.3 Flash by default
python -m rlm.map     samples/atlas runs/atlas
python -m rlm.dossier samples/atlas runs/atlas
python -m rlm.write   samples/atlas runs/atlas --passes 2   # model: GLM 5.3 by default;
                                                             # writes, verifies, grades, prints the spread
```

`rlm.write` runs the verifier and the grader itself and prints recall, rubric score and the
spread between the two passes. They can also be run alone:
`python -m rlm.verify samples/atlas runs/atlas` and
`python -m rlm.grade samples/atlas runs/atlas/report.md runs/atlas <name>`.

Artefacts land under `runs/<sample>/` and are never committed. For the real filings,
`python -m rlm.yahoo fetch samples/yahoo` downloads the seven documents from SEC EDGAR
first. `python -m rlm.widen <knob> samples/atlas samples/atlas-<knob>` generates a variant.

Tests: `pytest -q`. The phase tests are parametrised over the three gate samples and pinned by
digest; the model-calling phases replay from pinned artefacts and need no key.

## Why it was built this way

- **The key is the only test.** A phase passes when its artefact carries every planted fact
  on all three gate samples with no code change between.
- **One artefact per phase, in order.** A fact dropped later is traced to the phase that
  dropped it and fixed there; every later phase reruns.
- **Money is enforced by code.** `LEDGER.md` is written by the code that makes the call.
  Past a phase cap or the $50 total, the call refuses.
- **Cheapest model that passes.** Five candidates, a bake-off per model-calling phase, no
  preference, only the table.
- **A stage earns its place by removal.** Take it out, rerun, compare.

The plan of record is [`PLAN.md`](PLAN.md); the one page of rules is [`RULES.md`](RULES.md);
how a build session ran is [`CLAUDE.md`](CLAUDE.md).

## What it does not do yet

Five known misses on the generated variants, each a knob removing the only thing that tied
one document to the matter; the pairwise model judge that would reach them is priced and not
built. The writer needs a Pro-tier model; the notes run on Flash. Samples 2 to 4 have no
rubric, so their bar is recall and the verifier. See `REPORT.md` section 5.

## Credit and licence

The task, the room, the key, the rubric and the winning shape are John Adeojo's. The rebuild
would not exist without a published run to measure against.

Code and documentation: Apache License 2.0, see [`LICENSE`](LICENSE). Third-party samples
keep their own licences, listed in [`NOTICE`](NOTICE).

Built by [MergeSeat](https://mergeseat.com), a one-person software shop whose line is that
machine output is only usable if you can check it and refuse it. The verifier stage is that
line as code.
