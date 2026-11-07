# NodeTrail web: live learning

The application uses the real API exclusively. It starts with an empty graph,
loads published research jobs and source citations, requires explicit server-backed
graph confirmation, and continues from placement to next-item practice. Attempts,
mastery, reviews and cited tutor hints come from the backend. Backend fixture
responses are rejected; unavailable services never produce a sample lesson.

## Local startup (PowerShell, repository root)

Keep credentials in the repository `.env`. Do not put model or database credentials
in `NEXT_PUBLIC_` variables or copy them into the web directory. The launcher reads
settings and forwards only the shared proxy key and API URL to the web process.

Install Docker Desktop with a working Linux engine, then start infrastructure:

```powershell
docker compose up -d --wait db tei
```

TEI downloads the real BAAI/bge-m3 weights on first start. Review the database URL
before applying migrations. For the private local database:

```powershell
Set-Location apps/api
.venv/Scripts/python -m app.migrate
Set-Location ../..
apps/api/.venv/Scripts/python scripts/run_live.py --service check
```

Open three terminals at the repository root:

```powershell
apps/api/.venv/Scripts/python scripts/run_live.py --service api
apps/api/.venv/Scripts/python scripts/run_live.py --service worker
apps/api/.venv/Scripts/python scripts/run_live.py --service web
```

Open http://127.0.0.1:3000. The API factory is
`app.main:create_content_app`; the worker uses `--pipeline`, never `--fixture`.
The web can also start while infrastructure is unavailable; its status and requests
then report that the real service is unavailable. `--api-url` selects an existing
team API when launching the web against a separately configured host.

Choose Deep Research for a new web-sourced goal. Quick mode requires an already
indexed, relevant textbook. No index or verified learning content is fabricated.
Only published jobs with both graph_ready/items_ready may enter learning. Review
the map, explicitly confirm it, answer placement questions, continue to practice
and request cited hints. Reloading restores the topic identifiers; the opaque
learner credential stays in an HttpOnly cookie. Stale graph acceptance requires
fresh review. Upload UI is not exposed until private storage rollout is ready.

## Verification

From apps/web: `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd test`,
`npm.cmd run build`. These use synthetic fixtures for regression testing only;
they do not call paid models or establish live end-to-end acceptance.

Types are generated from `specs/live-learning/openapi.json`, exported from the
current content app without opening a database connection. Runtime decoders remain
required. To regenerate from a refreshed snapshot:

```powershell
npm.cmd exec --yes --package=openapi-typescript@7.10.1 -- openapi-typescript ../../specs/live-learning/openapi.json -o lib/api.generated.ts
npm.cmd exec -- prettier --write lib/api.generated.ts
```

See [live integration spec](../../specs/live-learning/spec.md) and its validation
handoff for the current infrastructure and acceptance status.
