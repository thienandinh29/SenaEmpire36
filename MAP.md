# MAP — where things are

Keep this file current when adding top-level folders or important modules.
Planned entries are marked _(planned)_ until they exist.

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules and working agreement for Claude (auto-loaded; imports only `MAP.md` and `SPEC.md`) |
| `CLAUDE.local.md.example` | One-line lane selector; copy to git-ignored `CLAUDE.local.md` |
| `SPEC.md` | What NodeTrail must do: features, behaviors, non-goals |
| `PLAN.md` | Phased build plan and current status |
| `TEAM.md` | 24-hour team plan: lanes, owned paths, stack, contracts, timeline, git workflow, risks |
| `team/` | Start guide per lane (`P1.md`–`P5.md`): setup, first task, first prompt; `TEAM.md` wins if they differ |
| `specs/` | GitHub Spec Kit: one folder per feature (spec, plan, tasks); `engine/`, `next-item/`, `retrieval/`, `library/`, `remediation/`, `model-test/`, `guardrails/` (P1; includes the labelling protocol), `contracts/review.md` (open contract decisions), `contracts/mocks/` (generated mock JSON for P5, `tests/engine/mocks.py`) |
| `.specify/` _(planned, P2)_ | Spec Kit project memory: constitution (from `CLAUDE.md` principles), templates |
| `docker/` _(planned, P2)_ | API image, compose for the cloud VM (API + worker + TEI for bge-m3, Watchtower, named Cloudflare Tunnel), VM setup script |
| `context/product-brief.vi.md` | Original product brief (Vietnamese) |
| `context/` | Reference material: research, textbook notes, algorithm papers |
| `outputs/` | Generated deliverables, not source code |
| `.claude/settings.json` | Pre-approved commands for Claude Code |
| `.claude/skills/verify/` | `/verify` — run all lint, type checks, tests |
| `.env.example` | Every env var the project uses (copy to `.env`) |
| `docker-compose.yml` | Local Postgres 16 + pgvector on port 54322 (`docker compose up -d`) |
| `.github/workflows/ci.yml` | CI: ruff, mypy, pytest against a pgvector service |
| `apps/api/` | FastAPI backend (uv, Python 3.12): P2 app factory, platform endpoints and mounted P3 routers; concrete learning/topic/tutor adapters still require registration |
| `apps/api/app/config.py` | Settings from repo-root `.env` (pydantic-settings) |
| `apps/api/app/migrate.py` | Applies `supabase/migrations/*.sql` once each (`uv run python -m app.migrate`) |
| `apps/api/tests/` | pytest; `conftest.py` makes a throwaway migrated DB per run |
| `apps/api/app/schemas.py` | Contracts (P1): Knowledge Graph + Items YAML models with validators, `Citation`, every API body |
| `apps/api/app/engine/` | Pure, tested decision logic: `bkt.py` (mastery), `srs.py` (FSRS review scheduling); traced wrappers `update_traced`/`review_traced`; `trace.py` (`DecisionTrace`) |
| `apps/api/app/engine/graph.py` | `Graph` (prerequisite DAG: topological order, depth, ancestors/descendants) + `root_cause` to the weakest prerequisite, traced |
| `apps/api/app/evalkit/` | Evaluation helpers (P1): exact intervals and kappa (`stats.py`), the labelled-sample format (`labels.py`), guardrail scoring with notes on what the sample cannot show (`guardrail.py`) |
| `apps/api/app/engine/path.py` | The next step when nothing just went wrong (`next_step`: resume, overdue review, continue, learn, confirm, done) with a target difficulty; traced |
| `apps/api/app/engine/remediation.py` | Remediation rules after a wrong answer (`remediate`: weakest prerequisite, repeated misconception, practise again) and `resume`; traced |
| `apps/api/app/engine/placement.py` | Graph-walk placement: `next_question`, `gap`, `seed_mastery`; stateless, traced; `verify` re-check on by default |
| `apps/api/app/graders/` | P3 deterministic MCQ grading and safe public projection |
| `apps/api/app/tutor/` | P4 three-level Socratic hint generation, independent verification and safe release |
| `apps/api/app/research/` | P3 allowlisted research/readers and TopicPipeline orchestration; worker ports not yet configured |
| `apps/api/app/uploads/` | PDF/DOCX/link reader and upload metadata; durable storage adapter pending |
| `apps/api/app/content/` | P4 source/graph/item schemas, prompts, generation CLI, actual P3 gateway adapter and P1/P3 conversion helpers |
| `apps/api/app/guardrails/` | Blind item verification, current-hash release gate and human-label metrics; real model verification still pending |
| `data/guardrails/` | 50 evaluation questions + 20 hints, agent expected labels and pending human annotation templates; no fabricated human scores |
| `data/eval/` | Labelled retrieval question sets (Vietnamese question → answer passage) + format README; scored by `app/rag/evaluate.py` |
| `data/golden/` | Three agent-reviewed topics, 45 pending MCQs, 15 chunks and source/review files; human/model approval pending |
| `apps/api/app/jobs/` | P2 Postgres queue and worker skeleton; fixture mode labelled, actual TopicPipeline binding still pending |
| `apps/api/app/observability/` | P2 JSON logging; live model telemetry/Langfuse integration still pending |
| `apps/api/app/rag/` | `notebook.py` (ipynb → chunks), `store.py` (`build_vector_index` after bulk load), `embed.py` (`TeiEmbedder` sync + async, local bge-m3, `make_embedder`; managed-API fallback planned), `chunker.py` (`ParsedDocument` → size-safe `Chunk`s), `library.py` (index every book folder), `retrieve.py` (`Retriever.search` → `Citation`s), `evaluate.py` (retrieval metrics on a labelled question set), `ingest.py` CLI (`--embedder tei|local`, `--build-index`); optional `rerank.py` planned (P1) |
| `data/raw/thinkpython/` | Downloaded Think Python 3e notebooks + `SOURCE_SHA` (git-ignored; re-download to rebuild) |
| `apps/api/app/llm/` | P3 gateway, provider adapters, routing, metadata/family scopes and offline/live probes; actual model IDs/credentials not configured here |
| `data/sources/` | P3 allowlist, library manifests and acquisition/index reports; raw textbook data is not committed |
| `data/kg/` _(planned)_ | Knowledge Graph YAML fixtures |
| `data/items/` _(planned)_ | MCQ item fixtures with misconception tags |
| `apps/web/` | P5 Next.js frontend, labelled mock/API modes, P1 fixture compatibility tests and generated integrated API wire types; no deployment implied |
| `apps/web/messages/` | Vietnamese UI strings and partial secondary English vocabulary |
| `specs/integration/` | Five-lane local merge provenance, actual integrated OpenAPI, checks and remaining DB/worker/model blockers |
| `supabase/migrations/` | Database schema (Postgres + pgvector); `0001_init.sql` = schema v1, `0002` = chunk provenance (chapter, section, kind, url), `0003` = `halfvec(1024)`, `url` → `source_uri`, HNSW dropped (rebuilt after load), `0004` = `decision_traces` (the "Vì sao?" audit trail) |
