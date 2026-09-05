# The winner's trail, step by step

The 98.5-point run: the RLM skill in Claude Code, Opus as the root, Sonnet 4.6 as the leaf,
36 minutes 32 seconds end to end, 22 June 2026. Read from `samples/atlas/winner/trail/steps/`
and `manifest.json` on 2026-09-05. This is the shape `PLAN.md` replaces piece by piece.

| Step | Seconds | Kind | What it did | In | Out |
|---|---|---|---|---|---|
| 1 to 3 | 43 | code | Split `corpus.txt` (387k chars, built by `extract_corpus.py` from the index and the files) into 100 documents by header; first regex failed on CRLF, fixed on the third try | 387k chars | 100 documents, 356k chars of body |
| 4 | 542 | model, leaf | One prompt per document, eight in parallel: what it is, red flags with any euphemism and its consequence, every figure and date quoted verbatim, cross-references (codename, ticket, person, regulator, document), a two-sentence smell test | 100 documents | 100 notes, 581k chars |
| 5 | 29 | code | Save the notes as `findings_inventory.md` | | |
| 6 | 20 | root | **A hard-coded list of 25 document ids**, typed by the root after reading the notes. No selection code. 96k chars, about 24k tokens | | 25 ids |
| 7 | 366 | model, one call | The 25 full texts with a six-part prompt: master timeline, what actually happened, divergent framing by function, who knew what when, disclosure and rep risk, every figure and count | 101k chars | 39k chars, `incident_synthesis.md` |
| 8 | 506 | model, one call | The notes of the other 75 documents: rank the distinct material issues, and flag any that connect back to the incident | 445k chars | 27k chars, `lesser_issues.md` |
| 9 | 400 | root | The report, written by the root from the two syntheses, and a 2k-char summary returned as `FINAL` | | `report.md`, 4,435 words |

Total 32 minutes of REPL time inside the 36 minute run.

## What to take from it

- The map was not derived. The root read 100 summaries and typed 25 ids. Whatever selected
  them lived in the root's context and left no trace. The rebuild's map is code over the
  notes' cross-reference field, which is the same information made explicit.
- The three documents a corpus-only map misses (user metrics, VistaMail KPIs, synergy model)
  are not in the 25 either. The winner reached them through step 8's "connect anything back"
  instruction over the notes. The rebuild reaches them through consequence links in the map
  and the dossier's blind-model check.
- Cost lives in step 4's output (about 150k tokens) and in reading the cluster's full text
  and the notes again in steps 7 and 8. The rebuild keeps step 4 with a tighter schema and
  replaces 7 and 8 with code and one short write.
- Nothing in the trail verified a quote against a source. The 91-point Haiku run lost its
  points on exactly that: probable stated as confirmed, and several claims the evaluator
  called source-stretching. The rebuild's verify stage is the answer to that row of the
  verdict.
- Reproducibility: the manifest's own note reads "LLM outputs are not expected to be
  byte-for-byte reproducible", and the trail's replay calls the model live. The rebuild pins
  the notes and makes everything after them code.
