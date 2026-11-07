# P4 sequential verification handoff

Scope: use the existing P3 gateway and P4 blind verifier; add safe checkpoints,
bounded retries, provider Retry-After classification and paired evaluation. No DB
migration or learner publication is performed by this command.

From `apps/api`, with the current root `.env` configured:

```powershell
.venv/Scripts/python.exe -m app.content.verify_batch ../../data/golden/python-conditions --checkpoint ../../data/guardrails/python-conditions-checkpoint.json --interval 15 --retries 2
```

This command reads the existing golden authorship metadata unchanged. These are
agent-authored golden questions, not evidence of live DeepSeek generation.
Gemini receives only question/options/cited chunks through `blind_request`.
The backend compares the independent response to the candidate answer.

The checkpoint contains full validated Item results under `items[id].result`,
fingerprints, audits, actual gateway identity, provider attempts and a summary.
P2 should deserialize results with `Item.model_validate` and check
`is_currently_verified(item, current_chunks)` before using the existing repository
import path. Never import a result based only on its stored status. Unfinished
questions remain in the original golden file as needs_review.

Resume reuses only currently verified results with identical item/source/config.
The summary's `elapsed_seconds` covers the latest invocation; attempts and token
totals are cumulative across checkpoint resumes. Unknown token usage/cost is null.
Expected evaluation labels are agent labels; human review is pending.

The 20 evaluation records pair 10 unchanged questions with 10 flipped backend keys.
Question/options/chunks remain identical, so one independent verdict is reused for
both keys. The receipt reports actual calls separately from reused results.
Infrastructure failures are unfinished cases, not correct detections or false alarms.

Retry stops on classified daily/zero quota or configuration failures. Unknown 429
is treated as transient with a finite retry budget, not assumed to mean rate limit.
Provider raw bodies, key values and user-specific error text are never persisted.

Completion requires >=6 current verified items, >=3 concepts and an edge/chain in
the accepted graph. Human map acceptance is distinct from the structural golden DAG;
this runner does not pretend a learner or a teammate accepted the graph.
