# Tasks: Learning engine

Window per `TEAM.md` timeline. `[x]` done. Tests in `apps/api/tests/engine/`.

## H0–H1 (contracts)
- [x] T1 `app/engine/trace.py`: `DecisionTrace` per contract; round-trip test
- [x] T2 `app/schemas.py`: KG + Items (cycle, misconception, one-correct validators), `Citation`, API bodies
- [x] T3 Migration `0003` (`halfvec(1024)`, `url` → `source_uri`, HNSW dropped) + `store.py` casts, `build_vector_index`

## H1–H3
- [ ] T4 `bkt.update_traced`, `srs.review_traced` + tests (prior/posterior/slip/guess in the trace)
- [ ] T5 `graph.py`: `Graph.from_contract`, ancestors/descendants/depth/topo order + tests on chain, wide, diamond
- [ ] T6 `graph.root_cause` + tests (nearest weak prerequisite, ties, no weak prerequisite, alternatives listed)

## H3–H7
- [ ] T7 `placement.py`: inference, `next_question`, `gap` + tests (stops ≤ 6, deterministic)
- [ ] T8 Simulated-learner test: planted gap located ≥ 90% across golden topics #1–3 (seeded)
- [ ] T9 Traces on every engine output; hand the trace list to P3's `/attempts` and `/placement/next`

## H8–H11
- [ ] T10 Remediation rules on top of `root_cause` (misconception → concept hints), varied graph shapes
