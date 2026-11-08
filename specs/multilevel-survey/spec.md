# Survey and source-grounded practice

The learner requested three questions for each curriculum concept: easy, medium
and hard. Difficulty uses an initial Elo-style scale; evidence from all three
questions contributes to the starting estimate. Untested concepts stay unassessed.
Review may generate new questions only from the concept's source material, behind
the existing independent verification gate. MCQ choices shuffle for presentation
while grading, diagnostic feedback and saved first answers use canonical indices.

Targets are difficulty 0.25/0.5/0.75 (initial Elo 800/1200/1600). Each concept's
rating starts at 1200, uses K=240 and contributes a bounded initial mastery
estimate; later review uses the existing BKT and prerequisite planner. This scale
is an initial estimate, not a claim of empirical item calibration. Refills add at
most three questions per request and preserve an unchanged published bank
atomically while drafts remain subject to independent verification.

Validation: 1,533 API tests and 62 web tests passed; web lint, TypeScript and the
production build passed. The live web-to-API survey probe generated two new
source-scoped questions, both accepted by independent DeepSeek/Gemini
verification, and served a medium-level question with HTTP 200. No answers were
submitted during this probe. See `outputs/multilevel-survey-live.json`.
