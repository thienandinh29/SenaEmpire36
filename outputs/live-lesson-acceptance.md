# Live lesson acceptance

The supplied `ly_thuyet_bat_phuong_trinh_bac_hai.pdf` was selected, consented to,
uploaded and submitted in the real Edge UI at http://localhost:3000. Its content
was not hardcoded into the application and no question fixture was imported.

- Job: `3cbb1cf0-ce45-482e-acdb-17567bfdb2bc`.
- Upload: `e5df1d4a-7512-4e15-8c1f-226e90ffe268`.
- Three source pages, four durable chunks, four real bge-m3 embeddings.
- Model: `BAAI/bge-m3`, 1,024 dimensions; TEI health, info and an actual embedding
  request all succeeded. The existing Docker named volume retains model files.
- Three graph concepts; graph explicitly confirmed through the UI.
- Seven questions pass the repository's current verification/hash checks.
- Answers were submitted and graded; three verified hints were persisted and
  rendered with source/page citations. Generator: DeepSeek; verifier: Gemini.
- Elapsed from initial submission through successful retry: 162.66 seconds.
  The initial attempt stopped on the new local store's unsupported URI scheme;
  correcting it to the existing `storage://` scheme and retrying reused the job.
- Screenshots: `pdf-lesson-live.png`, `pdf-lesson-verified-hint.png`.
- Machine-readable counts and PDF SHA-256: `live-lesson-acceptance.json`.

## Source behavior

The three-source/two-publisher condition stays in Deep Research for external
research. A supplied document is assessed for explanatory content sufficient for
one small lesson. Sufficient theory skips external research in either mode.
An outline identifies missing teaching topics and supplements according to the
selected mode: curated library in Quick; web research in Deep. Verification,
grounded chunk IDs and citation checks remain enforced.

Long PDFs with a goal can select relevant page windows plus initial provenance
pages, retaining original page numbers. Extraction is bounded to scanning 2,000
pages and the existing 20 MB/text limits; it does not claim complete coverage of
an entire long book. Selected web PDF pages now retain page numbers through
research and indexing. Blocked, unreadable or unlicensed sources emit concrete
reasons and the bounded search continues with alternatives.

## Readiness and retry

The live API refuses new jobs until TEI health and model identity pass. The
worker checks readiness before claiming work. Health distinguishes loading,
unavailable, error and model mismatch; vector parsing still enforces 1,024
dimensions. The UI gates submission and displays dependency failures.

Identical requests serialize under a PostgreSQL transaction advisory lock and
reuse active jobs. Failed requests requeue the same job: stable chunks, existing
embeddings and current verified artifacts are reusable. Source changes clear a
graph checkpoint; existing verification hashes and invalidation gates protect
questions/hints. Polling restarts even when retry returns the same ID. Worker
inactivity and browser polling have bounded failure states.

## Independent Python check

Goal `tôi muốn học Python`, selected mode Deep, no upload:
`afd01a9f-0c0d-486d-8a7b-c188c789e872`.

This separate real UI request failed after 90.95 seconds in source collection:
it did not obtain three eligible teaching sources from two publishers. The
trail records blocked access, missing licensing and nonteaching catalog/syllabus
pages. No Python lesson was published. PDF success is not evidence of automatic
source-discovery success; that path remains unresolved.

## Regression checks

250 backend tests and 32 web tests passed. Targeted coverage includes upload
theory versus outline, Deep-only source quota, long-PDF page provenance,
embedding readiness/refusal, concurrent deduplication, failed-job reuse and
graph invalidation after changed source content. Ruff, ESLint and TypeScript
checks passed for the changed implementation. A pre-existing Starlette/httpx
deprecation warning remains.

Run the local API and worker with `scripts/run_live.py --service api
--local-uploads` and `--service worker --local-uploads`; the flag enables the
existing demo consent policy and private workspace object storage. No database
schema changes, model substitutions, dependency additions, commits or pushes
were performed for these fixes.
