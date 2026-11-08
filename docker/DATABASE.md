# One database for all teams

The shared local target is `127.0.0.1:54322/nodetrail`. Set `DATABASE_URL` once in
the repository-root `.env`; shell environment overrides take precedence. API,
worker, indexing, confirmation and learner-session services use `Settings` from
`apps/api/app/config.py`. The legacy P4 factory also uses these shared settings.

| Component | Shared data |
|---|---|
| P1 learning/retrieval | subjects, sources, chunks, concepts/edges, mastery, reviews, traces |
| P2 platform | learners, uploads, attempts, attempt replay records |
| P3 research | topic jobs and model call records; indexed sources/chunks |
| P4 content/tutor | items/options, misconceptions, verification history, hints, learning sessions |
| P5 web | calls the same API; graph confirmations and learner sessions persist in the shared DB |

There is no second application DB or separate browser connection to Supabase.
Supabase object storage, when configured, stores uploaded files; relational records
still use `DATABASE_URL`. Tests and the P4 fixture demo retain dedicated
`nodetrail_test_*` databases and must not be merged into the application DB.

## Check and start

From the repository root, after installing dependencies:

```powershell
docker compose up -d --wait db tei
# Read-only schema and service checks; no model calls or data insertion.
apps/api/.venv/Scripts/python scripts/run_live.py --service check
```

The check validates every team's tables, all migrations under
`supabase/migrations`, validated foreign keys and `halfvec(1024)` embeddings.
For a detailed report, run from `apps/api`:

```powershell
.venv/Scripts/python -m app.database_status
```

If migrations are pending, review the configured target, then apply the canonical
migration runner from `apps/api`:

```powershell
.venv/Scripts/python -m app.migrate
```

Do not apply the historical `app/content/sql` copy separately. Open three
terminals at the repository root:

```powershell
apps/api/.venv/Scripts/python scripts/run_live.py --service api
apps/api/.venv/Scripts/python scripts/run_live.py --service worker
apps/api/.venv/Scripts/python scripts/run_live.py --service web
```

API and worker inherit the database target that passed preflight. The web launcher
sets the API URL and shared proxy credential from the same settings. When hosting
the web separately, configure its server-side `NODETRAIL_API_URL` and
`NODETRAIL_API_KEY` to point to this API. Keep DB/provider credentials in the API
environment. Inside Compose containers the same DB is reached as `db:5432`.

## Local validation receipt

The existing DB passed the read-only audit: all 13 canonical migrations, all
23 component tables and the migration ledger are present; foreign keys are validated and embeddings use
`halfvec(1024)`. API health and web-proxy health both returned HTTP 200 with
`db=ok` and `embedding=ready`. No data copying or schema migration was needed.
The audit preserved the existing 5 learners, 73 attempts, 36 mastery records and
30 review cards. Full counts are in [the audit report](../outputs/shared-database-audit.json).
