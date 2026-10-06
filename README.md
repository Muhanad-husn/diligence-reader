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

Three ways to run it.

**Docker**

The web page on the user's machine.

```
docker run -p 8000:8000 -v <runs>:/app/runs ghcr.io/muhanad-husn/diligence-reader
```

Open http://localhost:8000, connect an OpenRouter key (sign in or paste one; a run on Anthropic models only needs an Anthropic key in its own box instead), pick the model of each task under Models or pick the `client` preset, upload a room as a folder or zip, read the estimate, confirm, watch progress, read the report and export Word, PDF or the evidence CSV. Stop ends a run in progress and Retry resumes it from the stage that stopped; uploading a new room while a run is going asks first. Past runs lists every run on the machine with its status and dollars, and New room on the report clears the page back to the upload and keeps the key. The keys stay in the browser and go with each run; they are not written to disk. The models are saved on the machine, in the runs folder under Docker.

**pipx**

The command alone.

```
pipx install diligence-reader
diligence-reader run <room> --out <folder>
```

Set OPENROUTER_API_KEY (and ANTHROPIC_API_KEY for `anthropic/` models; `bedrock/` models use the usual AWS credentials). The command shows the price estimate and asks before the first model call; pass --yes to accept it. A rerun resumes from the stage that stopped.

**Helm**

For a firm that runs it on its own Kubernetes cluster.

```
helm install dr oci://ghcr.io/muhanad-husn/charts/diligence-reader
kubectl port-forward svc/dr-diligence-reader 8000:8000
```

Each run is one Kubernetes Job. The page is at http://localhost:8000.

**From the repository**

Python 3.13. Model calls go through OpenRouter; the tool refuses to call a model before it
has counted the input tokens, printed the price and checked the ledger against the ceiling. A user's own runs spend the user's OpenRouter credits; the limit is the one the user sets on the key.

```
pip install -e ".[dev]"
export OPENROUTER_API_KEY=...
```

Run one stage at a time: `python -m rlm.ingest`, `python -m rlm.notes`, `python -m rlm.map`, `python -m rlm.dossier`, `python -m rlm.write`. Tests: `pytest -q`. Artefacts land under `runs/` and are never committed.

## Models

Each run has three model tasks: the notes (one call per document), the group step (the tree's
calls, which run only when the report is built on the tree) and the writer. Each takes one model
id, from the page, from `--notes-model`, `--middle-model` and `--writer-model`, or from
the settings the page saved on this machine. An id names its provider by its prefix:

| Id | Runs on | Key |
|---|---|---|
| `claude-code/<model>` | headless Claude Code on this machine (not in the Docker image) | none |
| `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-5-5` | the Anthropic API | `ANTHROPIC_API_KEY`, or the Anthropic key box |
| `bedrock/claude-haiku-4-5`, `bedrock/claude-sonnet-5-5` | AWS Bedrock through boto3, in `--region` (default eu-central-1) | the standard AWS credential chain |
| anything else | OpenRouter | `OPENROUTER_API_KEY` |

An id the tool does not know is refused before any call, with its name in the message. With no
setting made, the notes run on GLM 5.3 Flash, and the group step and the writer on Claude Code's
Sonnet 5.5 when Claude Code is on the machine, else on the OpenRouter defaults. `--preset client`
(also on the page) is the all-Claude room: Haiku 4.5 for the notes, in a batch, and Sonnet 5.5
for the group step and the writer, built on the tree. `--batch` sends the notes through the
Message Batches API for half the price; it applies to `anthropic/` notes only, and the group step
and the writer always run live. Prompts that repeat are cached. The models are written into
`run.json`, and the report opens with a line naming the model of each task. Every call books its
tokens and dollars, cache reads and the batch discount included, in `LEDGER.md`.

## When a run stops

`diligence-reader run` exits non-zero with one of these codes and writes the same code to
`run.json` in the run folder. Running the same command again resumes from the stage that stopped.

| Code | What to do |
|---|---|
| `key-refused` | The provider refused the key (401 or 403): OpenRouter, Anthropic, or the AWS credentials. Check the key, or make a new one at openrouter.ai/keys. |
| `no-credits` | The key's account has no credits left (402). Add credits at the provider's page (openrouter.ai/settings/credits for OpenRouter), then run again. |
| `unknown-model` | A model id is not one this tool can run; the message names it. Pick it again. Nothing was sent. |
| `bad-settings` | The model settings cannot be run (an empty field, a bad region, a batch on notes that are not on the Anthropic API). Nothing was sent. |
| `rate-limited` | The provider kept answering 429. Wait a few minutes, then run again. |
| `empty-reply` | A model returned nothing twice for the same request. Run again; the stage is retried. |
| `unreadable-file` | A document in the room could not be read. Remove or convert the file named in the message, then run again. |
| `verify-failed` | The report did not pass the verifier after its one rewrite. Run again to write it once more. |
| `declined` | The estimate was not confirmed. Run again and answer y, or pass --yes. |
| `unexpected` | Anything else. Open an issue with the run's run.json attached; it holds no document text and no key. |

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
