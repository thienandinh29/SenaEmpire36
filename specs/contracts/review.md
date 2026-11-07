# Contract review (H0–H1 draft) — reply "OK" or list problems by the deadline P1 sets

Implemented in `apps/api/app/schemas.py` and `apps/api/app/engine/trace.py`, tested in
`apps/api/tests/engine/test_contracts.py`. `TEAM.md` → "Contracts" stays the source of truth; the points below are
the choices the code makes where `TEAM.md` is silent. Each needs an answer before the H3 freeze.

| # | Decision in the draft | Affects |
|---|---|---|
| 1 | `POST /attempts.answer` and `/tutor/hint.last_answer` are the **option index** (0-based, order as sent), not the label | P3, P5 |
| 2 | Item ids in the API are the **fixture id string** (e.g. `plr-001`); the DB `items.id` is a uuid, so `0005` should add a unique `items.external_id` (or P3 maps them) | P3, P4, P2 |
| 3 | `CitationRef` (hint/ask citations) adds optional `page` beside `{title, section, url}` so the web opens the right PDF page | P3, P4, P5 |
| 4 | `DecisionTrace.prior` / `posterior` may be `null` (e.g. a `review` trace); all `evidence` fields optional | P2, P5 |
| 5 | Every contract model rejects **unknown keys** (`extra="forbid"`): typos in YAML or requests fail loudly | all |
| 6 | Items without `status` load as `needs_review` (safe default: never served until verified) | P4 |
| 7 | `Concept.sources` needs ≥ 1 entry; `Item.chunk_ids` ≥ 1; slugs are kebab-case, ≤ 80 chars | P4 |
| 8 | `/tutor/hint.level` is 1–4; `HintResponse.citations` needs ≥ 1 (no citation, no hint) | P4, P5 |
| 9 | `retrieve.search` returns `Citation{chunk_id, source_title, publisher?, license, chapter?, section?, source_uri, page?, content, score}` | P3, P4 |
| 10 | SSE `GET /topics/{id}/events` sends `TopicState` as the event payload; event names `state` and `heartbeat` | P2, P5 |
| 11 | Migration `0003` drops the HNSW index; `app.rag.store.build_vector_index(conn)` rebuilds it after bulk loading | P2 |
| 12 | `placement.gap(...)` returns `str \| None` (None = no gap found, e.g. top question answered correctly), matching the optional `gap_slug` | P3 |
| 13 | Placement is stateless: P3 loads the learner's placement answers `[(concept_slug, correct, item_id)]` and calls `next_question(graph, answers)`; P2 persists `placement.seed_mastery(...)` as the starting `p_known` | P2, P3 |
| 14 | An item is attached to a concept (`ItemSet.concept`), so P3 picks an unserved `verified` item of the slug placement returns | P3, P4 |
| 15 | `retrieve.search` needs a pool and an embedder, so P3 builds one `Retriever(pool, embedder)` at startup and calls `await retriever.search(query, subject, k)` (also `search(..., retriever=)`); it is **async** | P3, P2 |
| 16 | P2 adds `EMBEDDING_BACKEND` (`tei`\|`local`), `TEI_URL`, optional `TEI_API_KEY` to `config.py` and `.env.example`, then `make_embedder(...)` builds the client | P2 |
| 17 | `sources` has no publisher column, so `Citation.publisher` is always `None`; the web's source list needs one (additive migration, P3's `0007` is the natural place) | P3, P2 |
| 18 | `httpx` moved from dev to runtime dependencies in `apps/api/pyproject.toml` (already locked; P2 owns the lockfile, please re-check) | P2 |

