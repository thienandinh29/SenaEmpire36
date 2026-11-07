# P5 verification evidence

## Executed checks

- ESLint, strict TypeScript and the Next.js production build passed in the implementation session.
- Vitest: 26 tests passed across graph layout, the mock learning journey, malformed API data, citation/upload validation and the same-origin server proxy. Tests use no real backend or LLM calls.
- The production server started at http://localhost:3000. `node scripts/smoke.mjs` passed mock SSR, Vietnamese locale, Sena, eight JS/CSS assets and proxy route/configuration/origin guards.
- A subsequent HTTP check returned 200. This is HTTP evidence, not browser end-to-end acceptance.
- A final pre-push lint/typecheck/test/build run is performed before publishing this branch; see the accompanying handoff report for its outcome.

## Not verified

- Browser automation reported an unavailable browser host. Native Chrome inspection failed, then Computer Use was stopped with the physical Escape key. No further UI input was attempted after that stop.
- Desktop/mobile layout, keyboard focus, interactive upload, map controls, learning context, hints, trace dialogs, Free/Pro and retry states still require actual browser verification.
- No real learning endpoints, integration schema/OpenAPI, authentication convention or deployment credentials were supplied. The API checkout contains only /health. Live upload/attempt/hint conventions remain gated by confirmed configuration.
- API Python checks were unavailable through uv on PATH; no backend files were changed.
- No video was recorded. ffmpeg and a window-only recording wrapper are available; do not present the wrapper or script as a completed recording.

## Browser acceptance checklist — pending

- [ ] Open the production build on desktop and a 390px mobile viewport; check overflow, typography and contrast.
- [ ] Navigate every screen using keyboard; check visible focus, dialog trap/restore, Escape and reduced motion.
- [ ] Enter a goal, select a valid PDF/DOCX, observe loading/receipt, remove it, then test invalid/empty/oversized files.
- [ ] Submit Quick mode; observe labeled mock snapshots and source trail, then open the map.
- [ ] Pan, zoom and fit; select nodes with long labels and use both graph and alternative concept-list controls.
- [ ] Open each node's sample lesson; verify source chapter, question and hints match that node.
- [ ] Answer incorrectly; inspect remediation and supplied trace evidence. Retry correctly; check mastery/review updates.
- [ ] Navigate away/back; confirm per-node answers, results, hints and trace history are retained.
- [ ] Open valid citations in a protected new tab; check missing/invalid URL handling.
- [ ] About → demo controls: exercise fail-once/retry and empty-result cases; restore Normal before recording.
- [ ] Free → Pro explanation; check the demo/no-payment notice and Deep mode gating.
- [ ] After backend handoff, repeat in API mode and confirm failures never display sample results as live data.
- [ ] Record, replay and inspect the backup video only after these interactive checks pass.
