# Run and integrate

From the repository root, configure the ignored local environment as for the
existing backend, then:

```powershell
cd apps/api
uv run python -m app.migrate
uv run uvicorn app.school.main:create_school_app --factory --host 0.0.0.0 --port 8019
```

Use the existing worker against the same database. Its normal command is
`uv run python -m app.jobs.worker --pipeline`; do not start extra workers merely
to use the class dashboard. Research and question fixes belong in that worker's
checkout and can be merged independently.

Set `apps/web/.env.local` locally: `NODETRAIL_DATA_MODE=api`,
`NODETRAIL_API_URL=http://127.0.0.1:8019`, `NODETRAIL_API_KEY_HEADER=X-API-Key`
and `NODETRAIL_API_KEY` matching the backend. Keep these values server-side.
Build with `pnpm build --webpack` and start with
`pnpm start --hostname 0.0.0.0 --port 3019`. Open `http://localhost:3019/school`.
For another device, use the host machine's LAN address; firewall/network access
must already permit the selected port. Internet publishing was not performed.

## Routes

All routes retain the existing server API-key boundary. Learner identity is
resolved from the existing HttpOnly cookie.

| Route | Purpose |
|---|---|
| `GET /school/session` | Resume the current learner without creating a new identity |
| `POST /school/curricula/outline` | Editable AI outline; no lesson publication |
| `GET, POST /school/curricula` | Visible courses / save approved outline |
| `GET /school/curricula/{id}` | Current per-learner progress and locks |
| `POST /school/curricula/{id}/lessons/{lesson}/start` | Start or explicitly retry a lesson job |
| `GET /school/curricula/{id}/lessons/{lesson}/material` | Current graph and original cited passages |
| `GET /school/library` | Candidates from ready public-web topics |
| `POST /school/curricula/{id}/lessons/{lesson}/link` | Owner-approved reuse after current verification checks |
| `GET, POST /school/classes` | Own/member classes / create class |
| `POST /school/classes/join` | Idempotent invite-based enrollment |
| `GET /school/classes/{id}` | Owner/private-key dashboard; students receive 404 |

Teacher links place the key in the URL fragment; the new proxy forwards it only
as `X-Class-Key` to the exact class dashboard. Save the link when creating the
class. Cookies remain the normal way the owner returns to their classes. Raw
keys are not recoverable from the database. Clearing the learner cookie creates
a separate anonymous identity rather than restoring a lost student profile.

## Evidence and limits

The backend regression passes **1,558 tests**. Web tests, typecheck, lint and the
production build pass; browser evidence and final counts are recorded below.
Native browser preview/capture were unavailable. Headless system Chrome uses
isolated contexts and the real production UI/API, with desktop and 390px mobile
checks. Local test tools and receipts are under `outputs/`; session credentials
and developer-only answer lookups use ignored `.env.school-*.json` files.

The live AI outline and student invitation flow passed. On-demand lesson job
`958b85c8-55fe-4aeb-9ba7-b53e6641b97c` selected three sources but failed at
`questions_failed`. That failure is retained. This feature did not weaken the
gate or change the question/research implementation. Existing independently
verified public topics can be assigned through the teacher UI while that work
continues; this is an explicit product action, not a fabricated ready state.

## Final browser and database acceptance

The production UI was exercised with separate teacher and student browser
contexts, desktop 1440px and mobile 390px. Actual UI actions created/edited the
AI outline, saved a course, created a class, joined via invite and resumed after
refresh. A member's roster request returned 404; a private teacher link worked
in another browser context. Screenshots were inspected and the mobile page had
no horizontal overflow. Foreign-origin writes and route/body bounds have
regression tests. Final web verification: **69 tests**, TypeScript and ESLint pass.

A second, explicitly teacher-curated course
`f8810e25-a15a-4471-b901-c221539faeb2` assigned two different, previously live
verified public topics through the owner UI: DSA interface/implementation and
conditional probability/independence. The simulated learner used normal HTTP/UI
placement and practice, explicit graph confirmation and the real BKT engine.
Developer-only correct-answer lookup stayed outside the learner API/UI.

Both lessons completed, all five concepts exceeded the mastery threshold, and
the next lesson unlocked after the first. Refresh retained **2/2 completion**.
Class `b184b1f9-7d4c-48f1-bb79-9961316c2b04` reported the actual **15 attempts,
13 correct, mean recorded mastery 0.962149106**. A deliberately incorrect practice
answer produced one assessed weak concept while the three unassessed future
concepts remained separately marked unassessed. No mastery/readiness flags were
manually changed in the live database. Browser-driver synchronization failures
were corrected and the same learner resumed; this is not a first-attempt
educational success-rate measurement.

A hint request during that run returned 503 from the existing verification gate.
It remained blocked, and the learner could continue practising. This feature
does not fix research/question/tutor quality; the separate content work remains
necessary. Current recorded success is the multi-lesson progression and private
class reporting, not unrestricted subject coverage or validated learning gains.
