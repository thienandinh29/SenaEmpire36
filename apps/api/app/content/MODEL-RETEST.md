# P4 real-model retest with corrected Gemini configuration

Source receipt: data/guardrails/gemini-reconfigured.json.
No credential is recorded. Golden authorship remains agent_session/gpt.
One independent Gemini verdict passed; exact current Item/audit exported to
data/golden/python-conditions/items.verified.jsonl. Load using Item.model_validate
and recheck is_currently_verified against current chunks before persistence/serving.

| Item | Concept | State |
|---|---|---|
| python-conditions-001 | remainder | verified |
| python-conditions-002 | remainder | needs_review |
| python-conditions-003 | remainder | not_run |
| python-conditions-004 | comparison | not_run |
| python-conditions-005 | comparison | not_run |
| python-conditions-006 | comparison | not_run |
| python-conditions-007 | boolean-logic | not_run |
| python-conditions-008 | boolean-logic | not_run |
| python-conditions-009 | boolean-logic | not_run |
| python-conditions-010 | if-else | not_run |
| python-conditions-011 | if-else | not_run |
| python-conditions-012 | if-else | not_run |
| python-conditions-013 | elif-order | not_run |
| python-conditions-014 | elif-order | not_run |
| python-conditions-015 | elif-order | not_run |

Current coverage:1 verified,1 concept (remainder); no prerequisite edge is covered.
Graph human acceptance and content human review remain pending; neither is inferred.
Probe succeeded in76.766s,632 input/201 output tokens. Resume reused it without
another call, then item002 encountered3 failures (2 transport,1 HTTP503) and stopped.
The inspected HTTP503 response said the model was experiencing high demand,
UNAVAILABLE. This is not a key rejection or a new quota finding.
Request count4 includes1 success and3 infrastructure failures;2 are retry requests.
Token632/201 are provider-reported successful usage; failed requests have unknown
usage. Actual billing is unavailable/null. No estimated cost is asserted.
Continuation elapsed218.203s; initial probe76.766s, excluding operator time.

Evaluation: wrong blocked1/1 valid, wrong allowed0/1 valid, unchanged rejected0/1 valid;
18 cases infrastructure/uncompleted. One successful model verdict supports two
backend candidate evaluations, not20 successful API calls. Expected labels are
agent-reviewed; human labels pending. No quality claim is made from one question.

From apps/api resume the SAME checkpoint after service availability recovers:

    uv run python -m app.content.verify_batch ../../data/golden/python-conditions --checkpoint ../../data/guardrails/gemini-reconfigured.json --max-items 1 --retries 0 --request-timeout 90

Only after another successful audit, continue sequentially without max-items,
using --interval 15 --retries 2. Production HTTP defaults unchanged;90s is explicit
for this CLI. Successful valid questions are reused, not called again.

P2 may import the exported verified Item with existing Repository.save_items after
save_material/save_graph. No DB import, learner confirmation or tutor live success
was performed on P4's machine. Graph confirmation still requires the existing
learner/topic/revision callback through the agreed P2/P3/P5 operation.
Target6 verified/3 concepts/accepted prerequisite chain and full20 cases NOT reached.
