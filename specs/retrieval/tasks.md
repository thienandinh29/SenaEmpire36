# Tasks: Cited retrieval

- [x] T1 `TeiEmbedder` (sync + async, batching, retries, validation) + `ThreadedEmbedder`, `make_embedder`
- [x] T2 `Retriever.search` / `search`: subject-scoped cosine, NFC query, iterative scan, exact re-sort
- [x] T3 Tests: fake TEI server (`httpx.MockTransport`); real pgvector with and without the HNSW index
- [x] T4a `ingest` CLI can use the TEI server (`--embedder tei`), builds the index once (`--build-index`); local model picks the GPU when PyTorch sees one
- [ ] T4b Live check on the host machine: query embedding < ~1 s (needs the TEI container running there, H2)
- [ ] T5 Retrieval evaluation on golden topic #1: recall@5, MRR (needs P4's questions + chunks, H3); data in `data/eval/`
- [ ] T6 Reranker decision at H8 from T5; `rerank.py` only if recall is weak
