# Plan: graph confirmation contract

Spec: `specs/graph-confirmation/spec.md`.

## Done by P1 (this change, additive)
- `app/schemas.py`: `GraphView.revision` (optional, 1-128 chars), `GraphConfirm`, `GraphConfirmed`. All `extra="forbid"`
  like the other bodies, so an unknown key is rejected.
- Mocks regenerated with `uv run python -m tests.engine.mocks`: `graph.response` carries a `revision`; new
  `graph-confirm.request` and `graph-confirm.response`. P5's `parseGraph` reads fields explicitly, so the extra key
  is ignored until P5 uses it.
- `TEAM.md` API table updated (the `GET /graph` row and the new `POST /graph/confirm` row); mocks README updated.

## Why optional on `GraphView`
`revision: str | None = None` keeps every existing response, test and stub valid. The real route must set it; a test
on the route (P3) should assert it is never `None` there.

## Needed from others (not done here)
- **P3:** the route. Obtain the authenticated learner at the boundary, call P2's `snapshot` for `GET /graph` (project
  the public graph and the revision from the same snapshot) and `confirm` for `POST /graph/confirm`; return 409 on a
  stale revision. Do not serialize P4's private graph model.
- **P5:** show the map, keep its `revision`, send it on an explicit accept; allow `graph/confirm` in the proxy's
  exact-path list; handle 409 by re-fetching the graph; regenerate `api.generated.ts` and the decoder.
- **P2:** keep `GraphConfirmations` and migration `0012` as delivered; no contract change on their side.

## Risks
Two different meanings of 409 (stale revision, not yet confirmed). Accepted for the demo; if it confuses the client,
add a machine-readable `code` later, which is additive.
