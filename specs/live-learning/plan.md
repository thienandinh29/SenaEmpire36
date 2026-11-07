# Implementation plan

1. Make the web configuration and client API-only; remove sample UI navigation.
2. Connect published graph review and explicit revision confirmation.
3. Complete placement-to-practice and update mastery from actual decision traces.
4. Provide a local launcher that forwards only web configuration and the shared
   API key to Next.js; keep model credentials in API/worker processes.
5. Verify client/proxy regression tests, lint, types and build. Start configured
   real services if available; report infrastructure blockers explicitly.
