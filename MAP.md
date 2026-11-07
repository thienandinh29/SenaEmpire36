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
| `specs/` | GitHub Spec Kit: one folder per feature (spec, plan, tasks); `engine/` (P1), `contracts/review.md` (open contract decisions), `contracts/mocks/` (generated mock JSON for P5, `tests/engine/mocks.py`) |
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
| `apps/api/` | FastAPI backend (uv, Python 3.12): `app/main.py` app factory + `/health` |
| `apps/api/app/config.py` | Settings from repo-root `.env` (pydantic-settings) |
| `apps/api/app/migrate.py` | Applies `supabase/migrations/*.sql` once each (`uv run python -m app.migrate`) |
| `apps/api/tests/` | pytest; `conftest.py` makes a throwaway migrated DB per run |
| `apps/api/app/schemas.py` | Contracts (P1): Knowledge Graph + Items YAML models with validators, `Citation`, every API body |
| `apps/api/app/engine/` | Pure, tested decision logic: `bkt.py` (mastery), `srs.py` (FSRS review scheduling); traced wrappers `update_traced`/`review_traced`; `trace.py` (`DecisionTrace`) |
| `apps/api/app/engine/graph.py` | `Graph` (prerequisite DAG: topological order, depth, ancestors/descendants) + `root_cause` to the weakest prerequisite, traced |
| `apps/api/app/engine/placement.py` | Graph-walk placement: `next_question`, `gap`, `seed_mastery`; stateless, traced; opt-in `verify` mode |
| `apps/api/app/graders/` _(planned, P3)_ | MCQ grading |
| `apps/api/app/tutor/` _(planned, P4)_ | Socratic hint ladder |
| `apps/api/app/research/` _(planned, P3)_ | Deep Research agent (allowlisted web search and reading) |
| `apps/api/app/uploads/` _(planned, P3)_ | Uploaded PDF/DOCX/link reader |
| `apps/api/app/content/` _(planned, P4)_ | Sources → Knowledge Graph → MCQs with misconception per wrong option |
| `apps/api/app/guardrails/` _(planned, P4)_ | `answerability.py` (items and tutor hints must be supported by cited chunks), `metrics.py` (error rate on the labelled set) |
| `data/guardrails/` _(planned, P4)_ | Human-labelled sample: ~50 generated items + ~20 tutor hints marked correct/wrong |
| `data/golden/` _(planned, P4)_ | 2–3 hand-checked golden topics (chunks, graph, items): test data, labelled sample, demo fallback |
| `apps/api/app/jobs/` _(planned, P2)_ | `topic_jobs` queue in Postgres, background worker, SSE progress with heartbeat |
| `apps/api/app/observability/` _(planned, P2)_ | structlog + Langfuse setup (OpenTelemetry, Sentry after the contest) |
| `apps/api/app/rag/` | `notebook.py` (ipynb → chunks), `store.py` (`build_vector_index` after bulk load), `embed.py` (bge-m3; TEI client and managed-API fallback planned), `ingest.py` CLI; `retrieve.py` and optional `rerank.py` planned (P1) |
| `data/raw/thinkpython/` | Downloaded Think Python 3e notebooks + `SOURCE_SHA` (git-ignored; re-download to rebuild) |
| `apps/api/app/llm/` _(planned, P3)_ | LLM gateway (Vertex AI, Bedrock, OpenRouter adapters) + `routing.yaml` (tier × task → ordered provider:model list) |
| `data/sources/` _(planned, P3)_ | Allowlist of open-education sites + library manifest |
| `data/kg/` _(planned)_ | Knowledge Graph YAML fixtures |
| `data/items/` _(planned)_ | MCQ item fixtures with misconception tags |
| `apps/web/` _(planned, P5)_ | Next.js web app on Vercel: topic input, research trail, map, learning, tutor |
| `apps/web/messages/` _(planned)_ | i18n strings (`vi` default, `en`) |
| `supabase/migrations/` | Database schema (Postgres + pgvector); `0001_init.sql` = schema v1, `0002` = chunk provenance (chapter, section, kind, url), `0003` = `halfvec(1024)`, `url` → `source_uri`, HNSW dropped (rebuilt after load) |
