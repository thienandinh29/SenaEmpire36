# Shared LLM gateway

This module brings P3's existing bounded gateway to main and adds DeepSeek API
generation, as agreed by P1/P3/P2. It does not supply P4's content pipeline or
merge the separate ptest2 API/worker/frontend integration.

## Local setup

Fill the root `.env` on the host (never commit credentials):

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_FREE_MODEL=deepseek-flash
DEEPSEEK_PRO_MODEL=deepseek-flash
```

The current official quickstart lists `deepseek-flash` and `deepseek-v4-pro`.
These are candidates, not model-quality acceptance. Confirm availability through
the authenticated `/models` endpoint and run P1's Vietnamese model evaluation.

Configure at least one independent Gemini/Claude verifier in the existing
`VERTEX_VERIFY_MODEL`, `BEDROCK_VERIFY_MODEL`, or `OPENROUTER_VERIFY_MODEL` slot,
with that provider's credentials. DeepSeek is not included in default verifier
routes. Missing credentials or verifiers fail explicitly.

From `apps/api`:

```powershell
uv sync --locked
uv run python -m app.llm.smoke
uv run python -m app.llm.smoke --live --provider deepseek --tier free --task items
```

The first command after sync checks configured routes without paid requests.
The `--live` command explicitly calls the API and may incur a charge. It validates
a short Vietnamese JSON response; it does not establish content quality or
generator/verifier acceptance. The CLI loads root Settings and exports provider
environment values without logging credentials; shell values take precedence.

Application entry points remain environment-based. API/worker startup must call
`get_settings().export_worker_environment()` before constructing the gateway.

## Verification and fallback

Use `complete_with_metadata(...)` for generation and pass the actual
`Completion.route.family` to `verification_scope(...)`. This includes fallback:
if generation falls back to Claude, verification must exclude Claude, rather
than excluding the configured primary DeepSeek family.

All providers run through `app.llm.gateway`: bounded retries/timeouts, Pydantic
JSON validation, token/latency metadata and sanitized failures. DeepSeek uses
`https://api.deepseek.com/chat/completions`, thinking disabled, and JSON-object
mode when a schema is supplied. Blank/truncated/invalid responses are rejected.

P3 handoff: update callers to preserve actual generator metadata; configure and
smoke-call generator and independent verifier; run real graph/item-schema and
Vietnamese quality checks with P4. Record latency/tokens/failures before claiming
live readiness. P2 supplies the adapter/settings/routing and local infrastructure.

Official references:
- https://api-docs.deepseek.com/quick_start/agent_integrations/
- https://api-docs.deepseek.com/api/list-models/
- https://api-docs.deepseek.com/guides/json_mode/
