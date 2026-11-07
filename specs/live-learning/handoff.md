# Live-only application handoff, 2026-11-08

The web app now exclusively uses the real backend. The mock client, sample graph,
handwritten lessons, practice simulator and fake notebook/exam screens were removed.
Contract test fixtures remain test-only. The proxy refuses X-Data-Fixture=true
responses. API-only configuration applies even if an old environment requests mock.

Published topics lead to graph review and explicit confirmation of the displayed
revision. The frontend checks the reviewed graph against the mastery graph and
does not auto-confirm. Stale revisions require fresh review. Placement completion
continues through next-item; attempts keep their retry identifier, and answer/hint
inputs are frozen once submission starts. Mastery and traces come from the engine;
the frontend does not grade. Tutor citations accept optional sections and PDF pages.
The topic identifiers survive reload; learner tokens remain HttpOnly cookies.

The current content app's OpenAPI was exported to openapi.json without starting
services and regenerated into the web types. No public contract was changed.

## Observed validation

- Web ESLint, TypeScript and 56 tests passed after removing obsolete simulator tests.
- API no-DB suite: 1,349 passed, 140 skipped; skipped tests do not establish SQL acceptance.
- Local launcher passed Ruff and mypy from the API project environment.
- Edge headless rendered the live-only empty overview with a real service unavailable
  message. Screenshot: outputs/live-overview.png. No sample concepts were present.
- Real model route smoke succeeded in the preceding session using the current .env;
  that is a connection test, not a real topic/learner acceptance run.

## Infrastructure blocker and next actions

Docker Desktop 4.98.0 is installed under C:/Program Files/Docker/Docker. The installer
was verified against WinGet SHA256
cd6273d9eaa4f07fa7593fc6813d37e1004381cebc3f26047a2554fa5db24388.
The initial successful installation enabled Microsoft-Windows-Subsystem-Linux and
explicitly logged that a computer restart is required. Docker was launched, but
docker info currently reports that Docker Desktop is unable to start. No automatic
restart was performed. PostgreSQL and TEI remain unavailable. No migration, library
indexing, topic generation or live learner run has been performed in this checkout.

After the user restarts Windows:

1. Start Docker Desktop and verify a Linux engine with docker info.
2. From the repo root run `docker compose up -d --wait db tei`; first startup
   downloads the actual images and bge-m3 weights.
3. Validate the private local database target, then run app.migrate with the API
   virtual environment from apps/api. No shared database should be migrated implicitly.
4. Run scripts/run_live.py --service check, then launch api, worker and web in
   separate terminals using that script (see apps/web/README.md).
5. Create a real Deep Research goal; require persisted independently verified item
   coverage, review/confirm the graph, and exercise placement, practice and cited hints.

The currently running web uses the real proxy credentials through the launcher;
with infrastructure down its requests fail explicitly. It never substitutes a demo.
No git pull, push or new commit was performed during this live-only change.
