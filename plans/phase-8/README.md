# Phase 8: The product

Milestone `Phase 8`. Spec: `PLAN.md` section 4c, row "8 Product". Cap $3, from the reserve on 2026-10-04. The last phase. One thing is shipped: the seven stages run unchanged from one command, `diligence-reader run <room>`, and from a web page served on the user's machine, through the user's own OpenRouter key; a run writes report.docx, report.pdf and evidence.csv beside report.md; packaged as a Docker image, a PyPI package and a Helm chart published together when a release is cut and a Helm chart tested on kind.

The outcome: `diligence-reader` on the path; the image on ghcr.io; the Helm chart in deploy/helm/diligence-reader; a run on samples 1, 2 and 3 from the web page in the image gives planted-fact recall 100 / 100 / 100, every planted fact reads out of the docx, the PDF and the CSV, spread over two runs printed; the same recall from the command line; PLAN.md section 4a's phase 8 row written.

## The bar

Samples 1, 2 and 3 run twice from the web page in the Docker image built from main. Recall on the first runs matches the command line, 100 / 100 / 100. Every planted fact reads out of each run's docx, report.pdf and evidence.csv. The spread over the two runs is printed. The verifier passes on every run.

## The shape decisions this phase fixes

- **A user's run writes no LEDGER.md row and meets no cap.** The build's own runs, the tests and the gate, pass `--phase 8`, which books LEDGER.md under a new `8: 3.0` entry in `PHASE_CAPS` in src/rlm/gateway.py; without `--phase` the gateway keeps the dollars in memory for run.json only.

- **The run folder is the state.** `runs/<id>/run.json` holds the stage, status, error code, documents noted, dollars spent and version; the command writes it, the API streams it, the page reads it. Retry resumes at the first stage whose artefact is missing.

- **The key is held in memory only.** It reaches the command through the child process environment, reaches a Kubernetes Job by a one-time fetch from the API pod over the cluster network, and is never in a file, a log, a Secret, a ConfigMap or a pod spec.

- **A room without a brief gets the package's default brief,** `src/rlm/brief.md`, a buyer's brief in sample 1's shape with no sample's names. The rubric subagent is not part of the product: a run grades recall by code only when the room carries a key.json.

- **One unreadable file does not fail a run:** it is skipped and listed on the run under the code `unreadable-file`. A run fails with that code only when no file could be read.

- **Error codes, each with its fix on the error card:** `key-refused`, `no-credits` with a link to top up at openrouter.ai, `rate-limited`, `empty-reply`, `unreadable-file`, `verify-failed`. Anything else is `unknown` and gets the Report a problem button, which opens a prefilled GitHub new-issue URL labelled `user-report` with run id, version, stage, code and dollars, never document text and never the key.

- **Users get a change when the founder cuts a release, never on a merge.** A release tag publishes the image, the PyPI package and the chart at one version. Nothing updates itself: the page shows a notice when a newer release exists, with the one command to update.

## Money

Expected about $1.6 of the $3: slice 01 $0, slice 02 about $0.45 (sample 1 once end to end about $0.30, samples 2 and 3 a few cents each), slice 03 about $0.15, slice 04 about $0.10, slice 05 about $0.10, slice 06 about $0.80 (three samples twice from the web).

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | Export: docx, PDF and CSV from report.md | [01-export.md](01-export.md) | #136 | none |
| 02 | The command | [02-command.md](02-command.md) | #137 | 01 |
| 03 | The API, the local runner and the progress stream | [03-api.md](03-api.md) | #138 | 02 |
| 04 | The web page | [04-web.md](04-web.md) | #139 | 03 |
| 05 | The image, the release build, the Helm chart and weekly upkeep | [05-package.md](05-package.md) | #140 | 03 |
| 06 | Phase 8 gate | [06-gate.md](06-gate.md) | #141 | 04, 05 |

Order of work: slice 01 first; slice 02 after 01 is merged; slice 03 after 02 is merged; slices 04 and 05 at the same time after 03 is merged; slice 06 after both 04 and 05 are merged.

## Risks to name

A fresh notes pass can drop northwind's `tidewater-subprocessor-gap`, the pass b miss the phase 2 bake-off recorded; if the gate meets it, it is phase 2's known miss, reported against the command line's own run, not a phase 8 defect. WeasyPrint needs Pango; on Windows it is installed from conda-forge into the `rlm` env, in the image from Debian packages. kind and helm are not installed on the founder's machine; slice 05 installs them with winget. OpenRouter's sign-in may refuse a localhost callback on the served port; slice 04 checks this first and, if refused, ships the pasted key alone and says so in its pull request.
