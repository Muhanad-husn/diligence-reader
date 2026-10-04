# Slice 04: The web page

Milestone `Phase 8`. Issue: [#139](https://github.com/Muhanad-husn/diligence-reader/issues/139). Spec: `PLAN.md#4c-phase-8-the-product`. Depends on: slice 03 of this phase, 03-api.

## Deliverable

A page in web/ served by the app: upload a room (a folder or a zip); connect the key by OpenRouter's sign-in (PKCE: openrouter.ai/auth with a code challenge, the code exchanged at openrouter.ai/api/v1/auth/keys) or paste one; the key kept in the page's memory and sent with each request, never in localStorage; the estimate shown and confirmed; progress per stage with documents noted and dollars; the report rendered with each citation opening the cited section with the cited line marked; export buttons for md, docx, PDF, CSV; an error card per code with its fix and a retry from the stage that stopped; for `unknown`, a Report a problem link to a prefilled GitHub new-issue URL with run id, version, stage, code and dollars, labelled user-report. The page also checks once a day for a newer release, by one request from the browser to GitHub's latest-release address that carries no document data, and shows the version and the one update command (`docker pull`, `pipx upgrade` or `helm upgrade`); `RLM_UPDATE_CHECK=off` switches it off.

## Mechanism

Plain HTML, CSS and JavaScript with no build step; the browser's EventSource reads the AG-UI stream; the `marked` library vendored as one file in web/vendor/ to render Markdown, because the page must work with no internet beyond OpenRouter.

Survey: no skill or MCP ships a page; a framework adds a build step for one page; a model call has no place; the chosen approach is vanilla JavaScript with vendored dependencies, so the page runs on the user's machine with no build process and no npm.

## Acceptance criterion

Given the app serving on localhost with sample 3, when a Playwright test drives the page (upload, paste key, confirm), then every stage shows finished, the report text in the page grades recall 100, a citation click shows the source section with the cited line marked, the four export links download non-empty files; with a refused key the error card shows `key-refused` with its fix and a retry; the Report a problem URL carries run id, version, stage, code and dollars and contains neither the key nor any document text; with a routed fake of GitHub's latest-release answer naming a newer version, the page shows the update notice; the sign-in button builds a PKCE request to openrouter.ai/auth with a localhost callback, and the code exchange is checked against a routed fake of the OpenRouter endpoint.

## Tests

tests/test_phase8_web.py with pytest-playwright (dev dependency); sample 3.

## Money

About $0.10.

## Files

```aeo-independence
slice: 04-web
creates: web/index.html
creates: web/app.js
creates: web/style.css
creates: web/vendor/marked.min.js
creates: tests/test_phase8_web.py
edits: pyproject.toml
depends-on: 03-api
```

## Out of scope

Accounts, saved history across machines, chat, a hosted copy.
