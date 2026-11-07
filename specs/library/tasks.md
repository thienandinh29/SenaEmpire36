# Tasks: Library ingestion

- [x] T1 Contract: `DocBlock`, `ParsedDocument`, `SourceMeta` (ND licence rejected); example book under `specs/contracts/library-example/`
- [x] T2 `chunker.py`: `split_text`, `pack`, `chunk_document`; randomised no-oversize / no-loss tests (broken versions fail them)
- [x] T3 `Chunk.page` stored; `chapter_no` optional; `SourceInfo` author/url optional
- [x] T4 `library.py`: validate-all-then-embed, replace on re-run, `--build-index`; plain one-line errors
- [ ] T5 P3: readers (HTML, PDF/DOCX, link) and `build_library` emit one folder per book (handoff board)
- [ ] T6 P3 + P1 at H5: one real HTML book and one real PDF end to end; chunk-size spread; 10-question spot check
- [ ] T7 P2: run `python -m app.rag.library <library> --tei-url ... --build-index` on the host GPU (H5–H7)
- [ ] T8 Tidy: let `notebook.py` use `chunker.py` (not needed for the demo)
