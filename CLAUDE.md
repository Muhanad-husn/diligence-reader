# RLM handbook

Read `RULES.md` first, then `PLAN.md`. Both are short and both are binding. This file says how a
session works here; it does not repeat them.

**What this is.** A rebuild, from scratch, of a tool that does what a recursive language model
did on a 100-document diligence data room: reproducible in the middle, cheap, and runnable on
other document sets. The method, the phases, the samples and the money are in `PLAN.md`.

**Who decides.** Muhanad. He merges. He sets the phase 5 bar and the answer to every open
decision in `PLAN.md` section 10. He does not want options lists; he wants one recommendation
with the number behind it. He does not want reminders about what is uncommitted.

**How work moves.** One phase at a time, in the order `PLAN.md` gives. A phase is a branch and
one pull request. Its tests are parametrised over the three samples and are the specification.
There are no reviewer or verifier roles, no evidence packets, no fix rounds: one reader reads
the pull request, and the founder merges or not.

**Money.** `LEDGER.md` is the only record of spend and the code writes it. Before any gateway
call, print the input token count and the price. The phase caps and the $50 total are in
`PLAN.md`; the code refuses past them. The RLM comparison in phase 7 runs on the Claude Code
subscription, never through the gateway.

**Keys.** `samples/README.md` names each sample's key, brief and planted facts. Nothing is
"found" unless a test reads it out of the artefact against that key. The `atlas` key was the
answer key of the first build's sealed folder; it is open now, and every rule in this
repository is written after having read it. That is stated once here and is not a concern:
the generalisation test is samples 2, 3 and 4, not blindness to sample 1.

**Runs.** Artefacts go under `runs/<sample>/` and are never committed. A long run is launched
detached (PowerShell `Start-Process`), and progress is read from the artefact, not the shell.

**Tests.** `pytest -q`. Never `python -m pytest`.

**Prose.** Plain, no em dashes, certainty words inherited from the source. This applies to
code comments, commit messages, pull request bodies and the report the tool writes.

**Reporting.** Score, dollars, spread, one recommendation. One message per phase and per day.
