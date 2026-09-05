# RLM Audit Run

This directory contains standalone Python scripts for the REPL code that
was executed during one RLM session.

- Run all saved steps from a clean replay checkpoint:
  `python replay_all.py`
- Run one step directly:
  `python steps/step_0001.py`
- Live replay calls `llm_query` / `llm_query_map` again, so LLM text may
  differ from the original run.
- Replay state is written to `replay_state.pkl`; the original live REPL
  state is not modified.
