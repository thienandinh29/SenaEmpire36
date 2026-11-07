# Tasks: H8 Vietnamese model test

| # | Task | Owner | When |
|---|---|---|---|
| T1 | Freeze spec, gates, thresholds and the cost cap (written, committed) | P1 | by H6 |
| T2 | Candidate list with exact reachable model IDs; smoke call each | P3 | H5–H6 |
| T3 | Case files: chunks for topic #3 (+ held-out chunks), planted-wrong items (10 flipped + 10 untouched) | P4 | by H6 |
| T4 | Runner: same prompt to a list of models, logs tokens, latency, cost, raw output; deterministic checks G1–G4 | P3 (checks: P1 specifies) | H6–H7 |
| T5 | Run gates on all candidates, then verifier pairs; re-run single failures once | P3 + P1 | H7 |
| T6 | Blind rating of finalists by two Vietnamese speakers | two team members | H7–H8 |
| T7 | Decision memo + `results-<date>.json`; P3 writes `routing.yaml` | P1, P3 | H8 |
| T8 | Re-check the tutor choice with P4's real tutor prompts | P1 + P4 | H12–H18 |

Open question for P1: where the deterministic checks live. `app/llm/` is P3's; a small `app/evalkit/` would be P1's but is
a new module (needs its own spec). Decide at T4.
