# Rules

One page. Read before any work in this repository.

## The gates

1. **The product is one number.** The end-to-end report exists from phase 0 on, scored against
   the key. Every change reruns the whole chain. A change that moves none of score, dollars or
   two-run spread does not merge.
2. **One artefact per phase, the key checked at every artefact.** A phase passes when its tests
   pass on samples 1, 2 and 3 with no code change between. The next phase does not start until
   then. A gap found later is fixed in the phase that owns it, and every later phase reruns.
3. **Two attempts per phase, then replace.** A phase that fails its gate twice is not fixed a
   third time. Its method is swapped for the simplest thing that can pass, or the phase is
   dropped and the score says what that cost.
4. **Money is a ceiling the code enforces.** $50 total. `LEDGER.md` is written by the code that
   makes the call. No call before its input tokens are counted and its price printed. Past the
   phase cap, the call refuses.
5. **Kill line.** Phase 5 under 70 on sample 1 after $25 spent means the method is wrong. Stop
   and redesign; no more dollars on the same shape.

## The two rules that stop the loop

- **A stage earns its place by removal.** Take it out, rerun, compare. If the score holds
  without it, it is deleted, whatever it cost.
- **No fix is aimed at a check.** Work is aimed at a phase's artefact against the key. A missed
  fact is traced to the phase that dropped it by the phase tests, never guessed at.

## Models

Luna, DeepSeek V4 Flash, DeepSeek V4 Pro, GLM 5.3, GLM 5.3 Flash. Chosen per task by the
bake-off table, cheapest that passes. No Gemini. No pair judge without the founder's word.

## Reporting

One message per phase and per day: score, dollars, spread, one recommendation with its number.
Nothing else.

## Prose

Plain. No marketing register. No em dashes. Certainty words come from the source, never
invented. A docstring says what the function does now and cites nothing.
