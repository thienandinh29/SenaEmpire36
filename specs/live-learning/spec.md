# Live learner flow

The user requested removal of the demonstration and a browser flow using real
data and models, without pulling or pushing. The web app must use the existing
API exclusively. No sample graph, simulated grading, sample lessons or local
approval may substitute for unavailable services.

Use the existing learner cookie, published topic polling, graph review/revision,
explicit graph confirmation, placement, next-item, attempts and cited tutor APIs.
Preserve server-side credentials and verification gates. Missing infrastructure
must produce an actionable unavailable state, never a successful sample result.

PostgreSQL with pgvector and bge-m3 embeddings remain required. Do not replace
them with in-memory persistence or fake embeddings to make a test appear live.
