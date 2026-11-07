# DeepSeek generation through the shared gateway

P1/P3 approval and publishing to main were explicitly confirmed by P2 in this
session. Add DeepSeek as a generator without changing the different-family
verification rule. Preserve the delivered P3 gateway's schema validation,
bounded fallback and sanitized telemetry. Never relabel DeepSeek as Gemini/Claude.

Acceptance: DeepSeek generates validated Vietnamese JSON through the gateway;
Gemini/Claude remain the configured verifier routes. Missing keys, malformed or
truncated output and missing verifiers fail explicitly. Offline tests must not
call paid services. A live call requires the owner's configured credentials.

Scope includes the existing standalone P3 LLM module needed on main, P2 runtime
settings, local TEI deployment and the completed chapter indexing receipt.
The broader ptest2 API/worker/frontend integration is not part of this change.
