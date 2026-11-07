# Live source discovery diagnosis

Checked on 2026-11-08 against the configured live model/search providers, using the production ResearchAgent and SafeReader. No upload, fixture, preloaded questions, or source-count bypass was used.

## Findings

- Search authentication/network works: the provider returned real Python textbook results.
- HTTPS fetching works for OpenStax, LibreTexts, MIT OCW and Saylor. This is not a general backend network outage.
- OpenStax pages explicitly restrict ingestion into language models without permission and are rejected by the existing policy.
- BCcampus and Wikibooks returned HTTP 403 in the live probes. No access-control workaround was attempted.
- Some LibreTexts pages lack detectable open-license evidence; others were successfully accepted in the baseline probe.
- MIT/Saylor results frequently lead to course landing pages rather than instructional content.
- Open Textbook Library responses were rejected for unsupported media type; its catalog entries would still require discovering actual book content and verifying access/license.

## Backend fixes

- Preserve the total 12-read/15-search budget while allocating reads across remaining publishers. Previously early publishers could consume all reads before Wikibooks was attempted.
- Use the existing LibreTexts content-region extractor when reading live HTML sources. Keep full-page license evidence separately so cleaning navigation cannot discard license restrictions or grants.
- Added regressions for late publisher access after early failures and preservation of license evidence outside cleaned lesson content.

## Verification and deployment

- Research/upload regression suites: 115 passed; one existing Starlette deprecation warning.
- Ruff checks passed on the four changed files.
- Baseline live Python probe failed after 71.2 seconds; the updated live probe reached all seven configured publishers and failed after 84.5 seconds. No Python lesson was created or claimed.
- Production worker was not restarted during this check: an active researching job fd312b6e-0a29-4670-b5ca-42ed90ecff28 was present. These changes require a worker restart after that job terminates.

Remaining issue: the current candidate set still does not provide three eligible teaching sources from two publishers. Access errors, license restrictions, catalog results and missing license evidence must be resolved through suitable source discovery, without weakening verification or claiming that a PDF acceptance proves web discovery.
