# RLM handbook

Read `RULES.md` first, then `PLAN.md`. Both are short and both are binding. This file says how a
session works here; it does not repeat them.

**What this is.** A rebuild, from scratch, of a tool that does what a recursive language model
did on a 100-document diligence data room: reproducible in the middle, cheap, and runnable on
other document sets. The method, the phases, the samples and the money are in `PLAN.md`.

**Who decides.** Muhanad. He merges. He sets the phase 5 bar and the answer to every open
decision in `PLAN.md` section 10. He does not want options lists; he wants one recommendation
with the number behind it. He does not want reminders about what is uncommitted.

**How work moves.** One phase at a time, in the order `PLAN.md` gives. A phase is a GitHub
milestone; it is sliced into issues, and every issue is one session and one pull request. The
phase's tests are parametrised over the three samples and are the specification. There are no
reviewer or verifier roles, no evidence packets, no fix rounds: one reader reads the pull
request, and the founder merges or not.

**How an issue is built** (the founder's rules, 2026-09-05):
1. One git worktree per issue.
2. Code is written by a dispatched agent: Opus for a hard slice, Sonnet for an easy one.
3. Prose (briefs, fixture reports, plan text, docs) is written by a dispatched Haiku agent.
4. Prose gets no mechanical test. Text-only work is read, diffed and fixed by hand.
5. A coding task starts with its behavioural tests. They are committed red; the builder makes
   them green with the minimum code; then refactor and retest.
6. Unblocked issues run concurrently, at most four at a time.
7. The founder is briefed in concise executive style: no jargon, actionable points, one
   recommendation.

**The aeo plugin: two lanes and one gate, nothing else.**
- `/aeo:sprint-plan`, typed by the founder once per phase, when the previous phase's closing
  issue is done. It slices the phase into issues under `plans/phase-N/` and files them on the
  founder's approval. A slice is a vertical piece that leaves a checkable artefact against the
  key, never a function or a library; the last slice of every phase is the closing issue below.
- `/aeo:status`, for the readout at any time.
- `block-merge`, the gate that keeps merging with the founder.
- Not used, and not to be invoked by description: `/aeo:sprint-start`, `/aeo:fix`,
  `/aeo:review`, `/aeo:verify`, `/aeo:triage`, `red-green-refactor`, `tdd-plan`, `tdd-ci`,
  `safe-pr`, `safe-cleanup`, `worker-dispatch`, `monitor-design`, and the builder, reviewer
  and verifier agents of the plugin. Building is done by plain dispatched agents under the
  rules below; the session opens the pull request with a short body: what the artefact is,
  the three numbers, the tests that passed on the three samples.

**Tracking.** Milestones `Phase 0` to `Phase 7` on GitHub, one issue per slice, labels
`phase-N`. Every phase ends with a closing issue named `Phase N gate` whose pull request runs
the phase's tests on all three samples and writes the three numbers into `PLAN.md`'s status
table. No issue of phase N+1 is filed until that issue is closed. A new session starts by
reading `RULES.md`, `PLAN.md`'s status table, and the one issue it is for; the session-start
hook lists the open issues and pull requests.

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
