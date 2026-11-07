# NodeTrail web — P5

Vietnamese-first Next.js frontend on lane `p5/web`. The default mode is an explicitly labeled local Python demonstration. A separate, guarded API adapter consumes the documented TEAM.md endpoints through a same-origin server proxy. No backend learning routes or integration credentials are available in this checkout, so live integration is **not verified**. No production deployment or push has been performed.

## Run

Requires Node.js 20.9+ and pnpm 10.

```sh
pnpm install
pnpm dev
```

On Windows without pnpm on PATH, use `npm.cmd exec --yes --package=pnpm@10.20.0 -- pnpm dev` (replace `dev` with the needed script). This session used the pnpm 10.20.0 executable cached by npm. No system execution-policy change is required. The dependency lockfile is included; P2 should use `pnpm install --frozen-lockfile`.

Default mock mode needs no environment values. For live mode, see [server environment and Vercel handoff](docs/P2-handoff.md) and `.env.example`. Never expose API credentials through `NEXT_PUBLIC_` variables.

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

The selected stack follows TEAM.md. Accessible dialogs use Radix; the local button primitive follows shadcn's cva/clsx/tailwind-merge pattern. No shadcn/Figma MCP was available in this session. No deployment, account setup, secrets, or backend modifications are included.

## Integration handoff

- `lib/contracts.ts` mirrors the documented graph, topic, public item, upload, hint, review and DecisionTrace shapes. `lib/decode.ts` validates incoming responses, rejects invalid graphs/cycles and strips nonpublic item fields. Generate replacements with openapi-typescript when P1 publishes OpenAPI; these types are not claimed as generated or frozen.
- `lib/data-client.ts` separates asynchronous mock and live operations using the same consumer types. Default mock mode has deterministic sample grading and configurable failure/empty scenarios. Mock feedback values are illustrative, not BKT/FSRS.
- `lib/layout.ts` uses dagre for all positions. React Flow renders the map; there are no manually positioned concept nodes.
- Navigation and copy default to Vietnamese. `messages/en.ts` is a secondary navigation vocabulary, not a complete English locale or a locale switch.
- `components/use-learning.ts` holds per-node item, answer, result, hint and trace context across navigation. Mock mode has a hand-authored lesson for every sample graph node, each with a chapter citation. These are UI fixtures, not P4 golden topics or pipeline-verified items.
- API topic progress uses snapshot polling, cancellation, error/retry and state refresh. No live percentage is fabricated because the contract does not define the unit of `progress`. SSE streaming/reconnection is not implemented or tested yet; polling is the documented snapshot recovery fallback. Tutor uses the documented JSON hint response, not an invented streaming protocol.
- API uploads, answer submission and hint-level numbering stay disabled until their undocumented conventions are configured after P2/P3 confirmation. No lesson-content endpoint is invented: API mode can request placement at subject level, while direct per-node content is unavailable. Deep Research and Free/Pro in mock mode are explicitly simulations; selecting Pro in API mode requests a tier and does not grant an entitlement.
- Sena is a local code-native SVG in `public/sena.svg`.

See [verification evidence and pending browser checks](docs/verification.md), [P1/P2/P3 integration questions](docs/integration-questions.md), and [backup demo script/recorder](demo/README.md). A backup video has **not** been recorded.

## Manual E2E checklist

- Desktop: open overview, map, learning, review, sources and about using sidebar.
- Mobile (390px): confirm navigation, cards, map controls and dialogs fit with no page-level horizontal overflow.
- New topic: select a suggestion or enter a goal. Deep on Free opens the Pro explanation; choosing demo Pro permits deep selection. Free resets to quick. No payment is performed.
- Attach a nonempty PDF/DOCX under 10 MiB; verify simulated receipt, removal and invalid-file error. In default mock mode, the file is never transmitted or parsed. API limits and field names require confirmation.
- Submit goal; simulated snapshots complete; open the labeled Python sample map. Changing form drafts must not change the submitted research goal. New topics reset the learning session after successful creation.
- Click map nodes to view mastery and descriptions. Use zoom/fit controls and keyboard focus.
- Select different nodes and verify distinct lessons. Answer incorrectly, inspect prerequisite remediation/trace, retry correctly, then inspect the updated graph and sample review card. Navigate away/back and verify the item, answer, hints and feedback persist for that node.
- Ask for both hints; verify no final answer is provided and citations open the chapter for the selected sample concept. Inspect trace history, including correct=false and zero-valued evidence if supplied.
- Open/close dialogs using keyboard, Escape and close buttons; focus is trapped and restored by Radix.
- Reload: all state resets, consistent with the demo notice.
- About → demo state controls: choose fail once, apply, and retry the next upload/topic/graph/hint operation. Choose empty, apply, reload the graph, and verify the empty state. Return to normal and reload before recording.
