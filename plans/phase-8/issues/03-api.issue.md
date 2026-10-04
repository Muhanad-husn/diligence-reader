# feat(phase-8): a local API that starts a run, streams its progress as AG-UI events and serves the report and its exports [slice 03]

**Issue:** #138 · **Spec:** PLAN.md#4c-phase-8-the-product · **Plan:** plans/phase-8/03-api.md
**Depends on:** 02-command (slice 02 of this batch)
**Labels:** phase-8

## Deliverable

A FastAPI app in app/ started as `uvicorn app.main:app --host 127.0.0.1 --port 8000`. Endpoints: POST /runs (multipart upload of a room's files or one zip; the key in the `X-OpenRouter-Key` header), GET /runs/{id}/estimate, POST /runs/{id}/confirm, GET /runs/{id}/events (AG-UI events over server-sent events: RUN_STARTED, STEP_STARTED and STEP_FINISHED per stage, STATE_DELTA with documents noted and dollars spent, RUN_ERROR with its code, RUN_FINISHED), GET /runs/{id}/report, GET /runs/{id}/sections/{anchor} (the cited section's text, for the citation viewer), GET /runs/{id}/export/{md|docx|pdf|csv}, POST /runs/{id}/retry. A Runner interface (start, status, cancel, and an optional router the app mounts) with one implementation here, LocalRunner, a background process running `diligence-reader run` with the key in that child's environment only; the runner is chosen by the `RLM_RUNNER` environment variable, `local` by default, and `kubernetes` is imported lazily from app/runner_k8s.py, which slice 05 writes. The app mounts web/ as static files when the folder exists. The server books LEDGER.md only when started with `RLM_PHASE=8`, which the tests and the gate set and a user never does.

## Mechanism

Library. FastAPI and uvicorn; the `ag-ui-protocol` package for the event types; server-sent events through FastAPI's streaming response. Events are derived from run.json as it changes.

Survey: no skill or MCP serves a local API; a model call has no place here.

## Acceptance criterion

Given samples 2 and 3 uploaded through the API with a key, when the estimate is confirmed, then the event stream carries RUN_STARTED, STEP_STARTED and STEP_FINISHED for each stage in order, at least one STATE_DELTA with documents noted and dollars, and RUN_FINISHED; the fetched report grades recall 100, as the command line does; all four exports download; the key string appears in no file under the run folder and nowhere in the server log; a bad key gives RUN_ERROR with `key-refused`, and a retry with a good key resumes at the stage that stopped.

## Files

```aeo-independence
slice: 03-api
creates: app/__init__.py
creates: app/main.py
creates: app/runner.py
creates: app/events.py
creates: tests/test_phase8_api.py
edits: pyproject.toml
depends-on: 02-command
```

## Out of scope

The web page, the Kubernetes runner, auth (the server listens on localhost only), CopilotKit and chat.
