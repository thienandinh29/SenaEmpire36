# P5 integration questions and missing inputs

Source of truth: [TEAM.md](../../../TEAM.md), especially Contracts, Stack and Lanes. No AGENTS.md was found in the repository or the checked ancestor directories. `team/P5.md` and CLAUDE.md were read. No additional integration guide, P1 schemas/OpenAPI, API learning routes, P4 golden fixtures, Spec Kit setup or assets/sena files were present. The existing public/sena.svg was retained.

No project-authorized messaging channel for P1/P2/P3 is configured. No messages were sent. Forward this concise list to the owners; frontend work continues using labeled fixtures.

## P1 — consumer contract confirmation

1. Publish the frozen OpenAPI/Pydantic schema. Confirm the current web consumer shapes for topic snapshots, public MCQs and DecisionTrace, including nullability. The web mirrors TEAM.md and validates responses; generated types cannot yet be produced.
2. Citations are inconsistent across documents: the lane promises `source_uri + page`, while tutor JSON defines `{title, section, url}` and public graph/items have no citation or lesson-content fields. Confirm the actual citation schema and how private Storage paths become authorized browser URLs. P5 will not concatenate storage paths or invent signed URLs.
3. Confirm how a selected graph node links to lesson content or a question. Current placement requests accept `{learner_id, subject}` only; they do not accept a concept slug. Live direct-per-node lesson content remains unavailable. Mock mode has a fixture per node.
4. Confirm `progress` units, initial/empty evidence semantics and review trace probability fields. P5 shows backend step/trail without assuming live percentage units.

## P3 — endpoint and request conventions

1. Provide the real base URL, working routes, auth header convention (with P2), and error/retry contract. Never send secret values in this document/chat.
2. Uploads: exact multipart field, size/page limits, supported MIME/content checks, scanned-file behavior, timeouts and `text_ok=false` handling. Live upload stays disabled until `NODETRAIL_UPLOAD_FIELD` and `NODETRAIL_MAX_UPLOAD_BYTES` are confirmed. The mock-only 10 MiB cap is not presented as a backend guarantee.
3. MCQ attempts: is `answer` a zero-based option index, option label, or another representation? Configure `index0` or `label` only if confirmed; other formats require adapting the consumer after the contract is published. No silent guess is made.
4. Tutor: first hint `level`, maximum levels, exhausted-hint behavior, and any streaming protocol. Current contract is one JSON hint with citations, so frontend uses JSON. Hint requests stay disabled until the first level is confirmed.
5. Confirm idempotency/retry policy for topic creation and submissions. The frontend retries on explicit user action and prevents duplicate in-flight operations; it does not automatically replay submissions or invent idempotency headers.

## P2 — deployment and operations

1. Configure the Vercel project root as apps/web, the supported Node runtime and pnpm 10.20.0. Set server-only environment values listed in `.env.example`; configure the shared API-key header name and value securely.
2. Confirm request-body limits and timeouts on the actual Vercel plan/API. The Next proxy bounds JSON requests and uploads; it does not replace backend validation or authorize a larger upload than the hosting plan permits.
3. Confirm allowed origins for the chosen production and preview URLs, and deployment protection if required. Frontend POST proxy requests reject mismatched Origin; no user authentication is invented for the no-login demo.
4. Publish topic SSE heartbeat/event details and hosting duration limits if switching from the current cancellable snapshot polling implementation to SSE. Reconnection is not yet claimed.
5. MAP.md needs a P1-owned update for the new web app/data client/docs. P5 has not edited it because it is outside the authorized paths.

## Sprint window

H0 has not been provided. P5 does not infer H12 or the feature-freeze deadline from the local clock. The sleep handoff note is [P2-handoff.md](P2-handoff.md); update it before the actual H12:00–H13:30 break once H0 is known.
