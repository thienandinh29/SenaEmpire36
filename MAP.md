# MAP — where things are

Keep this file current when adding top-level folders or important modules.
Planned entries are marked _(planned)_ until they exist.

## Review and functional testing (`ptest`)

`ptest` combines `origin/p1/ml-core` (`5245e56`), `origin/p2/platform`
(`651bc7b`) and `origin/p3` (`f8239ee`). Dependency conflicts were resolved by
keeping both lanes' requirements and regenerating `apps/api/uv.lock` with `uv lock`.

Start the local database with `docker compose up -d db`. From `apps/api`, run
`uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy .` and `uv run pytest -q`.

Review `docker/LOCAL.md` for the P2 platform runbook and
`specs/p3-integration/MERGE.md` for P3's integration checklist. P3's router
factories and pipeline are included, but their production adapters, route mounting
and worker wiring still need integration. P4/P5 are outside this branch's scope;
passing module tests does not establish full learner-flow acceptance.

Verified on this merge: Ruff lint/format and mypy pass; pytest reports 1,125 passed
with one upstream Starlette/httpx deprecation warning. No web app is included.

| Included path | Purpose |
|---|---|
| `.specify/memory/constitution.md` | Project principles for Spec Kit |
| `docker/LOCAL.md`, `planv2.md`, `specs/p2-local/` | P2 setup, local platform plan and verification |
| `apps/api/app/jobs/`, `apps/api/app/services/`, `apps/api/app/observability/` | P2 queue/worker, learning persistence and logging |
| `apps/api/app/api/` | P3 learning, topic and tutor router factories |
| `apps/api/app/graders/` | Deterministic MCQ grading |
| `apps/api/app/llm/` | Gateway, providers, routing and smoke CLI |
| `apps/api/app/research/`, `apps/api/app/uploads/` | Research pipeline, source acquisition and document readers |
| `data/sources/`, `scripts/build_library.py` | Source allowlist, library manifests/reports and acquisition CLI |
| `specs/p3-integration/` | P3 contracts, integration instructions and validation records |
| `supabase/migrations/0006_platform.sql`, `supabase/migrations/0007_uploads.sql` | Platform queue/LLM calls and upload metadata |

## Repository paths

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules and working agreement for Claude (auto-loaded; imports only `MAP.md` and `SPEC.md`) |
| `CLAUDE.local.md.example` | One-line lane selector; copy to git-ignored `CLAUDE.local.md` |
| `SPEC.md` | What NodeTrail must do: features, behaviors, non-goals |
| `PLAN.md` | Phased build plan and current status |
| `TEAM.md` | 24-hour team plan: lanes, owned paths, stack, contracts, timeline, git workflow, risks |
| `team/` | Start guide per lane (`P1.md`–`P5.md`): setup, first task, first prompt; `TEAM.md` wins if they differ |
| `specs/` | GitHub Spec Kit: one folder per feature (spec, plan, tasks); `engine/`, `next-item/`, `retrieval/`, `library/`, `remediation/`, `model-test/`, `guardrails/` (P1; includes the labelling protocol), `contracts/review.md` (open contract decisions), `contracts/mocks/` (generated mock JSON for P5, `tests/engine/mocks.py`) |
| `.specify/` | Spec Kit project memory: `memory/constitution.md`; templates planned |
| `docker/` | `LOCAL.md` platform runbook; deployment image/compose and host setup scripts planned |
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
| `apps/api/app/evalkit/` | Evaluation helpers (P1): exact intervals and kappa (`stats.py`), the labelled-sample format (`labels.py`), guardrail scoring with notes on what the sample cannot show (`guardrail.py`) |
| `apps/api/app/evalkit/model_checks.py` | Offline H8 G1–G4 screening against P1 contracts; mandatory review remains explicit (`specs/model-test/offline-checks.md`) |
| `apps/api/app/evalkit/model_metrics.py` | H8 receipt scoring: verifier catches/false alarms with intervals, p95 latency, task and combined topic cost; missing evidence remains explicit (`specs/model-test/receipts.md`) |
| `specs/contracts/p1-h7-review.md` | P1 source review, H7 engine acceptance sequence, library issues and placement limitation |
| `specs/contracts/h7-run-sheet.md` | P1's run sheet for the H7 end-to-end run: go/no-go list, 12 steps with expected results, what to record, a blank result table |
| `specs/model-test/run-procedure.md` | P1's run procedure for the H8 model test: US$2.00 run cap and US$0.50 per-topic cap (proposals), settings, order, evidence to keep, stop rules |
| `apps/api/tests/engine/test_learning_flow.py` | JSON-replayed placement/remediation/mastery/review flow; optional P3 real grader on an integration checkout; no live DB/worker claim |
| `apps/api/app/engine/path.py` | The next step when nothing just went wrong (`next_step`: resume, overdue review, continue, learn, confirm, done) with a target difficulty; traced |
| `apps/api/app/engine/remediation.py` | Remediation rules after a wrong answer (`remediate`: weakest prerequisite, repeated misconception, practise again) and `resume`; traced |
| `apps/api/app/engine/placement.py` | Graph-walk placement: `next_question`, `gap`, `seed_mastery`; stateless, traced; `verify` re-check on by default |
| `apps/api/app/graders/` | Deterministic MCQ grading (`mcq.py`) |
| `apps/api/app/tutor/` | P4 three-level Socratic hints with independent verification and safe release |
| `apps/api/app/research/` | Deep Research agent, allowlisted search/readers, library acquisition and pipeline |
| `apps/api/app/uploads/` | PDF/DOCX/link readers and upload metadata validation |
| `apps/api/app/content/` | P4 schemas, generation, P3 gateway adapter, canonical conversions and runtime repositories/ports |
| `apps/api/app/guardrails/` | Blind verification, current-hash release gate, human-label metrics; live model acceptance pending |
| `data/guardrails/` | 50 evaluation questions + 20 hints and human annotation templates; human labels pending |
| `data/eval/` | Labelled retrieval question sets (Vietnamese question → answer passage) + format README; scored by `app/rag/evaluate.py` |
| `data/golden/` | Three agent-reviewed topics, 45 pending MCQs and 15 chunks; model/human approval pending |
| `apps/api/app/jobs/` | Committed Postgres queue, durable progress/trail, configurable P3 pipeline factory and P4 runtime processor |
| `apps/api/app/observability/` | Logging setup; structlog/Langfuse integration planned |
| `apps/api/app/rag/` | `notebook.py` (ipynb → chunks), `store.py` (`build_vector_index` after bulk load), `embed.py` (`TeiEmbedder` sync + async, local bge-m3, `make_embedder`; managed-API fallback planned), `chunker.py` (`ParsedDocument` → size-safe `Chunk`s), `library.py` (index every book folder), `retrieve.py` (`Retriever.search` → `Citation`s), `evaluate.py` (retrieval metrics on a labelled question set), `ingest.py` CLI (`--embedder tei|local`, `--build-index`); optional `rerank.py` planned (P1) |
| `data/raw/thinkpython/` | Downloaded Think Python 3e notebooks + `SOURCE_SHA` (git-ignored; re-download to rebuild) |
| `apps/api/app/llm/` | LLM gateway (DeepSeek generation, Gemini verification; legacy Vertex AI, Bedrock and OpenRouter adapters), `routing.yaml`, smoke CLI and setup README |
| `data/sources/` | Open-education allowlist, library manifests and acquisition/index reports |
| `data/kg/` _(planned)_ | Knowledge Graph YAML fixtures |
| `data/items/` _(planned)_ | MCQ item fixtures with misconception tags |
| `apps/web/` _(planned, P5)_ | Next.js web app on Vercel: topic input, research trail, map, learning, tutor |
| `apps/web/messages/` _(planned)_ | i18n strings (`vi` default, `en`) |
| `supabase/migrations/` | Database schema (Postgres + pgvector); `0001_init.sql` = schema v1, `0002` = chunk provenance (chapter, section, kind, url), `0003` = `halfvec(1024)`, `url` → `source_uri`, HNSW dropped (rebuilt after load), `0004` = `decision_traces` (the "Vì sao?" audit trail) |

| `apps/api/app/research/pipeline.py` | P3 topic orchestration; optional async Retriever with explicit indexed subject, citation identity checks and original reading order; validates P1 KnowledgeGraph before publication |

| `apps/api/app/research/smoke.py` | Explicit live canonical graph/items and blind verification route smoke; preflight reads a small public book chapter without model calls |
| `specs/p3-integration/p3-follow-up.md` | P3 follow-up, validated checks, live blockers and P2/P4 integration instructions |
