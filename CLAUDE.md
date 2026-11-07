@MAP.md
@SPEC.md

# NodeTrail

AI tutor for any subject. The user states a goal ("Tôi muốn học Python") or uploads a syllabus;
NodeTrail builds a Knowledge Graph from trusted textbooks and runs the loop
assess → learn → practice → adjust → review. Mascot: **Sena** the monkey.
Full brief: `context/product-brief.vi.md`.

## Owner & working agreement
- Team of 5 (lead: student, aspiring ML engineer), each driving an AI coding agent. Lanes, owned paths,
  contracts and the 24-hour timeline are in `TEAM.md`; stay inside your lane's paths.
- **Current goal: competition demo built in 24 hours** by the 5 lanes in `TEAM.md`: the judge names any topic or
  uploads a file and NodeTrail builds a cited path live. Stay inside your lane and the demo scope in `SPEC.md`;
  if a task grows, propose a cut instead of extending it.
- Even in the sprint, keep the architecture clean (engine pure + tested, LLM behind the gateway) so nothing must be rewritten later.
- **Reply in English.** Detailed answers with the reasoning behind decisions.
- **Ask before** committing, pushing, adding dependencies, or making architectural changes.
- **Run tests/lint before saying anything is done** (see `/verify` skill). Report failures honestly with output.
  The owner re-checks everything afterwards.

## Team plan (read on demand, not auto-loaded)
`TEAM.md` is the single source of truth for the contest plan; `PLAN.md` only summarizes it. They are not loaded into
every session to save context. Your lane is set in your git-ignored `CLAUDE.local.md` (copy
`CLAUDE.local.md.example`), which loads your start guide from `team/`. Before a task, read from `TEAM.md`:
- your row in **Lanes** (the paths you may edit) and your column in **Timeline** for the current window;
- the **Contracts** subsection for any shape you produce or consume (copy shapes exactly, never from memory);
- **Git workflow** before touching migrations, dependencies or branches.

Rules that always apply, even without reading `TEAM.md`:
- Edit only your lane's paths; never change a contract (only P1, announced at a checkpoint); contracts freeze at H3.
- **Handoff board** (`TEAM.md`): read it at session start and before waiting on another lane. If you are blocked, add
  `⏳ waiting on P_: <what> (ready/<tag>)` to *your own row* and push it yourself: a small PR `[P_] board: …` touching
  only that row, merged by you once CI is green (no review needed). **Do not wait idle:** keep working on fixtures and
  stubs, and check `git fetch --tags && git tag -l "ready/*"`; when your tag exists **or the owner's row is ticked on
  `main`**, delete the `⏳` line, rebase and continue. When you finish something others wait on, merge it, push the tag
  `ready/<what>` and tick your row; if the tag push is refused (HTTP 403), do not retry or work around it: tick your
  row and tell the contact, who creates the tag. After each checkpoint tag (`checkpoint-h3`, `-h8`, `-h12`) rebase
  your lane branch onto it and run tests. P1 (P2 while P1 sleeps) is the contact whose job is that nobody waits on
  another lane. Your own board row is the one thing outside your lane's paths you may edit; never touch another
  lane's row.
- Never push to `main`, never force push, never read `.env`.
- Migrations use the reserved numbers in `TEAM.md`; additive only except `0003`.
- Feature freeze at H18: after that, bug fixes only.
- Spec Kit before code: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks`, one page each; stay on your lane branch.
  Exempt: bug fixes, changes under ~30 min inside an existing spec, and anything after H18 (short PR description
  instead). New routes, contract fields or modules always need a spec.

## Language rules
- All code, identifiers, comments, commit messages, and dev docs: **English**.
- Product is for **Vietnamese learners**: all user-facing UI text, Sena's dialogue, tutor responses,
  and sample content default to **Vietnamese**. Keep UI strings in i18n files (`vi` default, `en` secondary),
  never hard-coded in components.
- Handle Vietnamese text correctly: UTF-8 everywhere, NFC normalization, diacritic-aware search/tokenization.

## Core architecture principle
LLM is **not** the decision maker. It sits inside a harness:
- **Learning Engine** decides what to learn next: Bayesian Knowledge Tracing, rule engine (graph-walk placement, root-cause remediation), FSRS.
- **Graders** score work objectively: answer keys now (MCQ); test cases and rubrics later.
- **LLM + RAG** only explains, always with citations to source textbooks. No citation → don't present it as fact.
- Socratic tutor never hands over the final answer; it gives step-by-step hints.
- Sena praises only real understanding (mastery), never speed or streaks.

## Stack (decided — details and contracts in `TEAM.md`)
- Web: `apps/web` — Next.js App Router, TypeScript strict, Tailwind + shadcn/ui, React Flow + `dagre` auto-layout; Vercel.
- API: `apps/api` — Python 3.12, FastAPI, Pydantic v2, uv; Docker on a GPU VM on Google Cloud (AWS backup VM, roles
  swappable), Singapore, via a named Cloudflare Tunnel (`--protocol http2`) on the team's domain; the VM opens no
  ports. Multi-stage images from GHCR, auto-updated by Watchtower. The API image has no ML runtime; bge-m3 runs in a
  TEI container whose weights live on the VM disk.
- Jobs: `topic_jobs` table in Postgres as the queue (`SELECT … FOR UPDATE SKIP LOCKED`); the worker is a separate
  compose service from the same image (Redis after the contest). Never long work inside a request; SSE progress
  with a heartbeat every 15–20 s.
- Data: Supabase — Postgres + pgvector (`halfvec`), Storage; ~30k-chunk budget on the free tier.
  Migrations in `supabase/migrations/`.
- Embeddings: BAAI/bge-m3 (1024 dims) served by TEI, behind `Embedder`; API and worker call TEI over HTTP with an
  async client. Switching to another embedding model requires re-indexing.
- LLM: only through `app/llm/gateway.py` (adapters: Vertex AI primary, Bedrock, OpenRouter fallback);
  `app/llm/routing.yaml` maps (tier, task) → ordered `provider:model` list. The verifier is always a different model
  family from the generator. Never call an LLM SDK or HTTP API directly from features.
- Observability: structlog JSON logs + Langfuse (OpenTelemetry and Sentry after the contest).

## Code conventions
- Python: full type hints, `ruff` (lint + format) and `pytest` required in CI; `mypy` runs but only warns. Learning-engine math must have unit tests.
- TypeScript: `strict: true`, no `any`, ESLint + Prettier, Vitest for logic.
- Small modules, pure functions for algorithms (BKT/FSRS/Elo) so they are testable without DB or LLM.
- Secrets only in `.env` (never commit, never paste in chat). Document every new variable in `.env.example`.

## Folders
- `context/` — reference material for Claude (brief, research, textbook notes). Read when relevant.
- `outputs/` — generated deliverables (reports, exports, diagrams). Not source code.
