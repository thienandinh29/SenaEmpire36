# P1 review of `ptest2` (and a look at `p4`) — 2026-11-07

Reviewed read-only against `main` `3b3dba0`: `ptest2` `46045c5` (P2's integration of P2 + P3 + P5 + P1's `92d5592`)
and, for the overlap only, `p4` `bc7da3e` (P4's own integration). This is a source review plus the checks below. It
is **not** a runtime acceptance: nothing here ran against real TEI, real models or Supabase.
**`main` moved to `71b7b07` while this was written; see "Update after `main` moved" below.**

## Result

`ptest2` is mechanically healthy and its engine wiring is faithful, but it is not demo-ready, and the biggest problem is
that **two integrations exist that conflict** (finding 1). Findings are ranked; each names an owner and a check.

| Check | Result |
|---|---|
| `ptest2` merged into `main` | clean |
| ruff, ruff format, mypy (120 files) | pass |
| Python tests | 1,215 pass, 0 skipped (the P3-grader flow test now runs) |
| Web: frozen install, lint, typecheck | pass |
| Web: vitest | 38 pass (includes `canonical-contracts.test.ts`) |
| Secrets, risky file names | none found |
| `.claude/settings.json`, hooks, auto-run commands | not changed; none added |
| Lane boundaries | P3 and P5 inside their paths; P2 added `planv2.md` and `tests/test_platform.py` (minor) |

## Findings

| # | Sev | Owner | Finding | Evidence | Fix and check |
|---|---|---|---|---|---|
| 1 | High | P1 decides; P2, P4 merge | Two integrations, neither contains the other: `ptest2` lacks P4's content, verification, tutor and migration `0005`; `p4` lacks P2's latest wiring and the integrated web app. Merging them conflicts in 9 files (`learn.py`, `jobs/queue.py`, `jobs/worker.py`, `apps/web/lib/{api.generated,contracts,decode}.ts`, `apps/web/components/trace-panel.tsx`, `MAP.md`, `tests/api/test_learning.py`); 132 files are changed by both. | `git merge origin/p4` on `ptest2`; `git merge-base --is-ancestor` of each side's unique commits | **Confirmed by P1 (2026-11-07):** `ptest2` is the trunk (P2 is the integrator). P2 merges `p4` into it, each owner resolving their own files, then one PR to `main`. **After `71b7b07` each also conflicts with `main` (see Update).** Merge `main` into the trunk first. Check: one branch passes lint, mypy, pytest and the web checks. |
| 2 | High | P2 (`services/backend.py`) | `/next-item` never excludes items the learner already answered, so the same question repeats and mastery rises on memory. A concept with no verified items returns `None` forever and blocks the path. | `backend.py:224-227` (`min(items, key=...)`, no exclusion). Reproduced: two verified items, every answer wrong → served `A, A, A, A`, then `A`. P2's own test answers one item nine times. | Exclude answered item ids when choosing (fall back to the least recently served once all are seen); if a concept has no usable item, take the next candidate instead of `None`. Add the regression test below. |
| 3 | High | P5 | After placement the web app cannot ask for the next question: no `nextItem` in the client, and `next-item` is not in the proxy allowlist (`topics/{id}/events` is not either; polling `GET /topics/{id}` is fine). | `app/api/backend/[...path]/route.ts:5`; `lib/data-client.ts` has `placement, attempt, hint, reviews, graph, topic, upload, learner` only | Add `nextItem` to the client and `next-item` to the allowlist; wire the practice screen to it. |
| 4 | Med | P2 | API authentication is off by default: `api_key = ""` skips the check, and nothing refuses to start. | `config.py` `api_key: str = ""`; `main.py:73-79` | Refuse to start without a key unless an explicit local-dev flag is set (or warn loudly when the host is not loopback). |
| 5 | Med | P2 | `POST /attempts` is not safe to retry or double-click: a duplicate counts twice in BKT and in the review schedule. | no idempotency key; H7 review step 6 | Accept a client attempt id and dedupe on `(learner, item, attempt id)`; one transaction already makes the write atomic. |
| 6 | Med | P2 | Phase is inferred from the order of the last trace rows, and a wrong answer during placement also runs `remediate` and opens a resume origin. | `backend.py:262-273`, `:207-218` | `phase = placement` only until a `placement.done.*` trace exists; no remediation during placement; `resume_origin` only from practice-phase wrong answers. |
| 7 | Med | P2 + P4 | Items are found by `payload->>'id'`; two subjects reusing an id returns 503 on every attempt. | `backend.py:137-145`; no unique index | Unique expression index now, or P4's `0005` external id (`review.md` #2, #21). |
| 8 | Med | P2 | CI has no web job, so P5's lint, typecheck and tests never run there. | `.github/workflows/ci.yml` | Add `pnpm install --frozen-lockfile`, `lint`, `typecheck`, `test` for `apps/web`. |
| 9 | Resolved | P3 | The model family was `Literal["gemini", "claude"]`. On `main` `71b7b07` it now includes `deepseek`, and the verifier still excludes the actual generator's family. | `llm/gateway.py:28`, `:94` on `main` | None. Live acceptance of the DeepSeek route is still pending (no credentials configured). |
| 10 | Low | P3 | `SafeReader` treats `64:ff9b::7f00:1` (NAT64) and `::127.0.0.1` as global. Not exploitable without attacker DNS and a NAT64 network. | `ipaddress.is_global` check on this Python | Also reject `64:ff9b::/96` and `::/96`. |
| 11 | Low | P2 | SSE polls the database once a second per client against a pool of 5. | `main.py:146-175`, `db.py` | Fine for one demo; revisit before more than a few viewers. |
| 12 | Low | P2 | `/learners` uses its own model (`max_length=200`; the contract says 80); `GET /topics/{id}` returns a raw `JSONResponse`, so the contract model is not enforced there. | `main.py:30,141-144` | Use the contract models. |
| 13 | Info | P2, P4 | `/exam-plan` returns 503 (not handed over) and `/tutor/*` returns 503 until P4's runtime is merged. | `backend.py:369`, `main.py:63` | Expected; part of finding 1. |

Withdrawn: my earlier concern that progress is stored 0–100 against the contract's 0–1 is handled (`jobs/queue.py:52`
divides by 100).

## Update after `main` moved (`71b7b07`, same day)

`71b7b07` ("Add DeepSeek generation gateway and verified local TEI setup"; authored by P2, pushed by the GitHub user
`fromdevtocwithlove1`) went **directly to `main`**: there is no PR, and CI passed on it (run 52). It brings P3's gateway (with a DeepSeek provider), settings, TEI notes and
`docker/p2-readiness.json` onto `main`. I did not review that code (the provider and the gateway changes); I only checked
the commit for credentials (none; I may not read `.env.example`, so that file is not covered).

- **Routing note on `main`.** `TEAM.md` there carries "Approved routing update (P1/P3/P2)": DeepSeek is now an optional first
  generation candidate in both tiers, with Vertex, Bedrock and OpenRouter as fallbacks (as of `71b7b07`; `f4cd74f` then
  removed the generation fallbacks and made Gemini the verifier), and verifiers still gemini or claude. It says it does not replace the H8 quality gates. **Confirmed by P1 (2026-11-07):** generation DeepSeek, verification
  Gemini, embedding bge-m3; see the Model decision in `TEAM.md`.
- **Finding 1 is bigger.** `ptest2` now conflicts with `main` in 12 files and `p4` in 10, mostly the gateway files each
  carries its own copy of (`llm/*`), plus `config.py`, `pyproject.toml` and `.env.example`. Whoever merges first, the next
  one resolves against `main`, so `main` should be merged into the trunk before anything else.
- **Live evidence from P2** (`docker/p2-readiness.json`, P2's own measurement, not re-run by me): migrations `0003` and
  `0004` applied to a local database; Think Python chapter 1 ingested with the TEI CPU image (16 chunks, 14.7 s, **1.09
  chunks/s**, TEI memory about 4 GiB, sampled); a Vietnamese query returned the right section first in **0.16 s** (target
  about 1 s); the identical text ranked first. This is the first live check of retrieval and ingestion.
- **What that means for indexing.** At 1.09 chunks/s, P3's 17,390-chunk export would take about **4.4 hours** and 30,000
  chunks about 7.7 hours. The sample is small (16 chunks, includes warm-up), so treat it as an order of magnitude, but it does
  not fit the H5–H7 window. Options: index only the books the golden topics need first (4,000 chunks is about 1 hour), and/or
  run the bulk on a GPU machine (Colab, per the risk table; same model, so no re-index). P1 decides the subset; P2 proposes.

## What is good (keep it)

- **Engine wiring:** `placement`, `next_step`, `remediate`, FSRS and BKT are called as designed; each learner's state
  change is one transaction under a `for update` row lock; earlier misconceptions are read *before* the new attempt is
  saved; placement seeds mastery once; every decision's trace is stored with its attempt.
- **Link fetching (SSRF):** HTTPS and port 443 only, no embedded credentials, every resolved address must be global, the
  connection is pinned to the checked IP (no rebinding), each redirect is re-validated, size and time are capped,
  proxy variables are ignored.
- **Web proxy:** exact-path allowlist, traversal guard, same-origin check on writes, key kept server-side, streamed size
  limits, `redirect: "error"`.
- **Contracts:** both lanes' request and response shapes match `app/schemas.py`; P3's duplicate data shapes are the only
  maintenance risk (replace with imports once merged).

## Not reviewed

P3's research agent, pipeline and prompts; the gateway's provider adapters and error redaction; P5's UI components
(`workspace.tsx` is 1,294 lines) and accessibility; the row-level security in `0007`; P4's 209 files; behaviour with real
TEI, models, Supabase or the worker under failure.

## Regression test for finding 2 (acceptance)

With one concept and two verified items (difficulty 0.3 and 0.6), a learner who answers each served item wrong must be
served both items before either repeats, and a learner who has answered every item must still be served something
(least recently served) instead of a dead end. A concept with no verified items must not stop `next-item` from returning
another concept. Reproduction used: seed as in `tests/test_learning_backend.py::learning_data`, then
`GET /next-item` → `POST /attempts` four times.

## Re-review

When finding 1 has a trunk, P1 re-runs: lint, mypy, full pytest, the web checks, the finding-2 test, and a placement →
wrong answer → remediation → resume → correct answer → review pass through the HTTP routes.
