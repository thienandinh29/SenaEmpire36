# Reference-driven mock studio

## Field journal overview

Developed on `p5-ui-test` and approved by the user for merging into `p5`. The branch uses a hyphen because Git cannot create `p5/ui-test` while the local `p5` ref exists.

The overview uses Dancing Script display titles and Be Vietnam Pro small headings, warm paper surfaces, a dedicated knowledge atlas, contextual Sena guidance and compact study shortcuts. Existing mock logic, lesson flows and theme persistence remain intact. Dagre still positions every graph node. Mastery rings replace rectangular cards; the focused/all camera adapts to canvas width and respects reduced motion. Selecting a concept updates Sena's panel and displays its saved note when present. Draft approval still precedes teaching.

Check desktop/mobile widths, both themes, node selection, focus/all controls and links to lessons, notes, reviews and calendar. Browser access is unavailable in this session, so visual acceptance remains pending. Lint, TypeScript, 36 existing tests, production build and HTTP SSR/assets checks passed; these do not replace browser acceptance.

The frontend follows the supplied business brief and Sena image. The ui-ux-pro-max minimal dashboard guidance was adapted to a warm ivory/indigo palette; its landing-page pattern was rejected as unsuitable. Sena is a reference-inspired local vector component with six expressions, not an extracted raster asset.

## Run locally

With dependencies already installed: `npm run dev` in `apps/web`. The default data mode is mock. No backend, credentials, added dependencies, deployment, commit or push is needed. `npm run build` and `npm run start` serve the production version.

## Demo journey

1. Open the overview and start a topic. Enter a goal or choose a local PDF/DOCX. Choose the IELTS sample explicitly to preview its graph. Files are validated but never parsed or sent in mock mode.
2. Follow the simulated research steps, open the draft graph and confirm it before learning. Python lessons retain the existing concept-specific MCQ and source/hint flows. IELTS is graph-only.
3. Open placement for a short adaptive question sequence with a real ten-minute countdown. Results are per skill; unassessed skills are marked accordingly.
4. Open the practice studio. Select a wrong range answer twice (retry between submissions) to see prerequisite remediation. Try fill-in, code ordering with keyboard-accessible arrow buttons, and the code editor. Code output is a deterministic fixture matcher, not Python execution. Correct the loop bound to `n + 1` to preview passing test output.
5. Open notes, choose a concept, type a note, insert heading/list/code/formula/table snippets (a trailing slash is replaced), and save. A note-linked flashcard is upserted. Notes and cards persist in versioned localStorage. This is a Markdown-style mock editor, not a full rich block editor.
6. Open reviews, flip a card and rate recall. Rating writes a mock due date; future cards leave the due queue. The restart button deliberately brings all cards back for testing. Wrong practice answers also add a diagnostic card.
7. Open the calendar and select an exam date 3–90 days away. The final 14 study sessions are shown, each limited to 20 minutes. The two sessions directly before the exam are reserved for final review. Selecting a day shows details.

## Integration boundary

The existing `LearningClient` and guarded API proxy remain intact. New practice, notebook and calendar state is deliberately mock-only and has no invented backend endpoints or shared contract fields. BKT values, adaptive decisions and review intervals are illustrative. Actual Pyodide execution, BKT/FSRS, syllabus extraction, rich note rendering and model-generated Socratic dialogue remain backend/runtime integration work. Browser refresh resets transient practice/placement state; notes and flashcards persist locally.

## Verification

ESLint, TypeScript, Vitest, production build and HTTP SSR/static-asset smoke checks are run during implementation. Browser access host and native helper are unavailable in this session, so desktop/mobile visual acceptance and actual click-through checks are pending. Do not interpret HTTP checks as browser acceptance.

Final checks: ESLint and TypeScript passed; 32 Vitest tests passed across 5 files; production build passed; targeted Prettier check passed; HTTP smoke passed for Vietnamese SSR, Sena, 8 static assets and API proxy guards. The production preview is running on http://localhost:3000. Browser visual acceptance remains pending because both browser access host attempts failed.

## Light and dark appearance

Use the sun/moon button in the top bar to toggle appearance. First visit follows the operating system. Explicit choices use the versioned nodetrail-theme-v1 localStorage key, restore before first paint, and sync between tabs. If storage is blocked, switching still works for the current page. The dark palette covers the workspace, graph, learning panels, notebook, reviews, calendar, dialogs and loading/error states. No additional package or backend is used. Theme bootstrap behavior has four automated tests; browser visual acceptance remains pending because browser access is unavailable.
