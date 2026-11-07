# Tasks: graph confirmation contract

- [x] P1: `GraphView.revision`, `GraphConfirm`, `GraphConfirmed` in `app/schemas.py`, with tests.
- [x] P1: regenerate mocks; update the mocks README and the `TEAM.md` API table.
- [x] P2: `GraphConfirmations` service and migration `0012` (delivered, see `specs/p2-graph-confirmation/handoff.md`).
- [ ] P3: `GET /graph` returns `revision` from the same snapshot it projects; `POST /graph/confirm`; 409 on stale; a
      route test that `revision` is never `None`.
- [ ] P3: authenticated learner at the boundary (not the browser-supplied id).
- [ ] P5: keep and echo `revision`; explicit accept control; allow `graph/confirm` in the proxy; re-fetch on 409.
- [ ] P5: regenerate the API types and decoder; a test against `graph-confirm.*` mocks.
- [ ] P3: bump `P1_REVISION` in `apps/api/tests/api/test_p1_contracts.py` (now `5245e56`) to the commit that merges this change. The
      pinned old schema forbids extra fields, so on a full clone `test_p1_mock_round_trip[graph.response-...]` fails with
      `revision: Extra inputs are not permitted` (checked on a trial merge of this branch into `ptest2` `657c09f`). The test
      skips when the pinned commit is missing, so a shallow CI clone is unaffected; full local clones are not.
- [ ] P1: re-run step 2a of `specs/contracts/h7-run-sheet.md` through the real routes when P3 and P5 are in.
