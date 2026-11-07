# Plan

Reuse P3's gateway and httpx transport. Add a DeepSeek adapter using the official
chat-completions endpoint, JSON mode for schemas, and thinking disabled for
bounded generation latency. Validate returned JSON with the requested Pydantic
schema. Export secret-masked credentials and exact model IDs from P2 settings.

Prepend DeepSeek to generation routes; leave verifier routes Gemini/Claude.
Extend actual generator-family tracking so fallback still selects a different
family. Test provider payload/errors, routing/fallback, verification and settings.
Run main's full API checks before a normal fast-forward push to main.

References: https://api-docs.deepseek.com/quick_start/agent_integrations/
and https://api-docs.deepseek.com/guides/json_mode/.
