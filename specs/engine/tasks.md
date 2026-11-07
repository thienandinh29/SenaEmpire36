# Tasks: Learning engine

Window per `TEAM.md` timeline. `[x]` done. Tests in `apps/api/tests/engine/`.

## H0–H1 (contracts)
- [x] T1 `app/engine/trace.py`: `DecisionTrace` per contract; round-trip test
- [x] T2 `app/schemas.py`: KG + Items (cycle, misconception, one-correct validators), `Citation`, API bodies
- [x] T3 Migration `0003` (`halfvec(1024)`, `url` → `source_uri`, HNSW dropped) + `store.py` casts, `build_vector_index`

## H1–H3
- [x] T4 `bkt.update_traced`, `srs.review_traced` + tests (prior/posterior/slip/guess in the trace)
- [x] T5 `graph.py`: `Graph.from_contract`, ancestors/descendants/depth/topo order + tests on chain, wide, diamond
- [x] T6 `graph.root_cause` + tests (nearest weak prerequisite, ties, no weak prerequisite, alternatives listed)

## H3–H7
- [x] T7 `placement.py`: inference, `next_question`, `gap`, `seed_mastery`, opt-in `verify` + tests (stops ≤ 6, deterministic)
- [~] T8 Simulated-learner test. **Noiseless: gap located exactly, ≤ 6 questions, every planted gap on 4 shapes (met).
  With slip 0.10 / guess 0.25 noise the ≥ 90% criterion is NOT met** (seeded, 400 runs per planted gap):
  plain 43–55% exact (mean 2.5–4.7 questions), `verify=True` 56–64% (3.2–5.6 questions). Decision needed from P1:
  relax the criterion, make `verify` the default, or move to probabilistic placement (see spec.md note)
- [ ] T9 Traces on every engine output; hand the trace list to P3's `/attempts` and `/placement/next`

## H8–H11
- [ ] T10 Remediation rules on top of `root_cause` (misconception → concept hints), varied graph shapes
