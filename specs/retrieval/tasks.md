# Tasks: Cited retrieval

- [x] T1 `TeiEmbedder` (sync + async, batching, retries, validation) + `ThreadedEmbedder`, `make_embedder`
- [x] T2 `Retriever.search` / `search`: subject-scoped cosine, NFC query, iterative scan, exact re-sort
- [x] T3 Tests: fake TEI server (`httpx.MockTransport`); real pgvector with and without the HNSW index
- [ ] T4 Live check on the VM: query embedding < ~1 s (needs P2's TEI container, H2)
- [ ] T5 Retrieval evaluation on golden topic #1: recall@5, MRR (needs P4's questions + chunks, H3); data in `data/eval/`
- [ ] T6 Reranker decision at H8 from T5; `rerank.py` only if recall is weak
