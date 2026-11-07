# Shared LLM gateway

This module brings P3's existing bounded gateway to main and adds DeepSeek API
generation and Gemini verification, as agreed by P1/P3/P2. It does not supply P4's content pipeline or
merge the separate ptest2 API/worker/frontend integration.

## Local setup

Fill the root `.env` on the host (never commit credentials):

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_FREE_MODEL=deepseek-flash
DEEPSEEK_PRO_MODEL=deepseek-flash
GEMINI_API_KEY=
GEMINI_VERIFY_MODEL=gemini-3.8-flash
```

The current official quickstart lists `deepseek-flash` and `deepseek-v4-pro`.
These are candidates, not model-quality acceptance. Confirm availability through
the authenticated `/models` endpoint and run P1's Vietnamese model evaluation.

Gemini Developer API keys are sent only to `generativelanguage.googleapis.com`
in the `x-goog-api-key` header, never in a URL. This is separate from Vertex
authentication/billing; a working AI Studio key does not prove Vertex access
or Google Cloud credit eligibility. The host's key authenticated to the Gemini
Developer API; Vertex Express returned 403. The API reported that Gemini 2.5
Flash is unavailable to new users and recommended Gemini 3.8 Flash. Model
availability and content quality still need to be checked for each account.

Alternatively, configure `VERTEX_VERIFY_MODEL` with Vertex project/location and
ADC credentials to use Gemini via Vertex. These are two transports for the same
Gemini family. Neither DeepSeek nor Claude is in the default verifier routes.
Missing credentials or verifiers fail explicitly.

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

Default generation routes are DeepSeek-only; default verification routes are
Gemini-only. DeepSeek failure retries within bounds and then fails explicitly,
without switching generation to Gemini. The legacy Vertex/Bedrock/OpenRouter
adapters remain available for separately approved routing changes.

Use `complete_with_metadata(...)` for generation and pass the actual
`Completion.route.family` to `verification_scope(...)`. Family exclusions still
apply to custom routes: a model cannot grade its own family's output.

All providers run through `app.llm.gateway`: bounded retries/timeouts, Pydantic
JSON validation, token/latency metadata and sanitized failures. DeepSeek uses
`https://api.deepseek.com/chat/completions`, thinking disabled, and JSON-object
mode when a schema is supplied. Blank/truncated/invalid responses are rejected.
Gemini's billed output count includes thinking tokens; thought parts are not
mixed into the JSON content returned to the caller.

P3 handoff: update callers to preserve actual generator metadata; configure and
smoke-call generator and independent verifier; run real graph/item-schema and
Vietnamese quality checks with P4. Record latency/tokens/failures before claiming
live readiness. P2 supplies the adapter/settings/routing and local infrastructure.

Official references:
- https://api-docs.deepseek.com/quick_start/agent_integrations/
- https://api-docs.deepseek.com/api/list-models/
- https://api-docs.deepseek.com/guides/json_mode/
- https://ai.google.dev/api/generate-content
