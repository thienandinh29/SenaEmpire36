"""Retriever against a real migrated pgvector database, with the deterministic fake embedder."""

import asyncio
import unicodedata
from collections.abc import Iterator

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from app.rag.embed import ThreadedEmbedder
from app.rag.notebook import Chunk, parse_notebook
from app.rag.retrieve import Retriever, search
from app.rag.store import SourceInfo, replace_chunks, upsert_source
from tests.rag.fixtures import NOTEBOOK, FakeEmbedder


def _info(slug: str, title: str) -> SourceInfo:
    return SourceInfo(
        subject_slug=slug,
        subject_name_vi=slug,
        subject_name_en=slug,
        title=title,
        author="Tác giả",
        license="CC BY-NC-SA 4.0",
        url="https://example.org/book",
        version="v1",
    )


@pytest.fixture
def retriever(database_url: str) -> Iterator[Retriever]:
    embedder = FakeEmbedder()
    chunks = parse_notebook(NOTEBOOK, 5)
    with psycopg.connect(database_url) as conn:
        conn.execute("delete from sources")  # tests share one database; start clean
        replace_chunks(conn, upsert_source(conn, _info("python", "Think Python")), chunks, embedder)
        other = [
            Chunk(1, "Cells", "Membranes", "text", "The cell membrane is a lipid bilayer.", "u/bio")
        ]
        replace_chunks(conn, upsert_source(conn, _info("biology", "Biology 2e")), other, embedder)
    pool = ConnectionPool(database_url, min_size=1, max_size=2, open=True)
    try:
        yield Retriever(pool, ThreadedEmbedder(embedder))
    finally:
        pool.close()


def _glossary_text() -> str:
    chunk = next(c for c in parse_notebook(NOTEBOOK, 5) if c.kind == "glossary")
    return chunk.embedding_text


def test_exact_text_is_the_top_hit_with_full_citation_fields(retriever: Retriever) -> None:
    hits = asyncio.run(retriever.search(_glossary_text(), "python", k=3))
    top = hits[0]
    assert top.score == pytest.approx(1.0, abs=1e-3)
    assert "modulus operator" in top.content
    assert top.source_title == "Think Python"
    assert top.license == "CC BY-NC-SA 4.0"
    assert top.chapter == "Conditionals and Recursion"
    assert top.section == "Glossary"
    assert top.source_uri.startswith("https://allendowney.github.io/ThinkPython/chap05.html")
    assert top.page is None and top.publisher is None
    assert top.chunk_id


def test_results_are_ranked_and_limited_to_k(retriever: Retriever) -> None:
    hits = asyncio.run(retriever.search(_glossary_text(), "python", k=4))
    assert len(hits) == 4
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_search_is_scoped_to_the_subject(retriever: Retriever) -> None:
    bio = asyncio.run(retriever.search(_glossary_text(), "biology", k=10))
    assert [h.source_title for h in bio] == ["Biology 2e"]  # one chunk only; no Python leakage
    py = asyncio.run(retriever.search("cell membrane", "python", k=50))
    assert py and all(h.source_title == "Think Python" for h in py)


def test_unknown_subject_returns_nothing_instead_of_failing(retriever: Retriever) -> None:
    assert asyncio.run(retriever.search("anything", "no-such-subject")) == []


def test_query_is_nfc_normalised_so_decomposed_vietnamese_matches(retriever: Retriever) -> None:
    composed = "Biểu thức boolean là gì?"
    decomposed = unicodedata.normalize("NFD", composed)
    a = asyncio.run(retriever.search(composed, "python", k=2))
    b = asyncio.run(retriever.search(decomposed, "python", k=2))
    assert [h.chunk_id for h in a] == [h.chunk_id for h in b]
    assert [h.score for h in a] == pytest.approx([h.score for h in b])


@pytest.mark.parametrize(("query", "k"), [("", 5), ("   ", 5), ("ok", 0), ("ok", 51)])
def test_bad_arguments_are_rejected(retriever: Retriever, query: str, k: int) -> None:
    with pytest.raises(ValueError):
        asyncio.run(retriever.search(query, "python", k))


def test_module_level_search_matches_the_contract_shape(retriever: Retriever) -> None:
    hits = asyncio.run(search(_glossary_text(), "python", retriever=retriever))
    assert len(hits) == 5  # default k


def test_works_with_the_hnsw_index_built(database_url: str, retriever: Retriever) -> None:
    from app.rag.store import build_vector_index, drop_vector_index

    with psycopg.connect(database_url) as conn:
        build_vector_index(conn)
    try:
        hits = asyncio.run(retriever.search(_glossary_text(), "python", k=3))
        assert hits[0].score == pytest.approx(1.0, abs=1e-3)
        assert len(hits) == 3
    finally:
        with psycopg.connect(database_url) as conn:
            drop_vector_index(conn)
