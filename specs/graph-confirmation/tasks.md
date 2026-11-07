# Tasks: graph confirmation contract

- [x] P1: `GraphView.revision`, `GraphConfirm`, `GraphConfirmed` in `app/schemas.py`, with tests.
- [x] P1: regenerate mocks; update the mocks README and the `TEAM.md` API table.
- [x] P2: `GraphConfirmations` service and migration `0012` (delivered, see `specs/p2-graph-confirmation/handoff.md`).
- [ ] P3: `GET /graph` returns `revision` from the same snapshot it projects; `POST /graph/confirm`; 409 on stale; a
      route test that `revision` is never `None`.
- [ ] P3: authenticated learner at the boundary (not the browser-supplied id).
- [ ] P5: keep and echo `revision`; explicit accept control; allow `graph/confirm` in the proxy; re-fetch on 409.
- [ ] P5: regenerate the API types and decoder; a test against `graph-confirm.*` mocks.
- [ ] P1: re-run step 2a of `specs/contracts/h7-run-sheet.md` through the real routes when P3 and P5 are in.
