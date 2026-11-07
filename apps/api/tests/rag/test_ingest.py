import json
from pathlib import Path

import psycopg
import pytest

from app.rag.embed import to_pgvector
from app.rag.ingest import ingest
from tests.rag.fixtures import NOTEBOOK, FakeEmbedder


@pytest.fixture
def book_dir(tmp_path: Path) -> Path:
    (tmp_path / "chap05.ipynb").write_text(json.dumps(NOTEBOOK), encoding="utf-8")
    (tmp_path / "SOURCE_SHA").write_text("abc123\n")
    return tmp_path


def _chunks(database_url: str) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as conn:
        return conn.execute(
            "select c.chunk_index, c.chapter_no, c.section, c.kind, c.url,"
            " vector_dims(c.embedding), s.version, s.license"
            " from chunks c join sources s on s.id = c.source_id order by c.chunk_index"
        ).fetchall()


def test_ingest_stores_chunks_with_provenance(database_url: str, book_dir: Path) -> None:
    count = ingest(book_dir, database_url, FakeEmbedder())
    rows = _chunks(database_url)
    assert count == len(rows) == 6
    assert [r[0] for r in rows] == list(range(6))
    assert all(r[1] == 5 and r[5] == 1024 for r in rows)
    assert rows[0][6] == "abc123"
    assert "CC BY-NC-SA" in str(rows[0][7])
    assert {r[3] for r in rows} == {"text", "glossary", "exercise"}


def test_reingest_replaces_instead_of_duplicating(database_url: str, book_dir: Path) -> None:
    ingest(book_dir, database_url, FakeEmbedder())
    ingest(book_dir, database_url, FakeEmbedder())
    assert len(_chunks(database_url)) == 6
    with psycopg.connect(database_url) as conn:
        sources = conn.execute("select count(*) from sources").fetchone()
    assert sources == (1,)


def test_nearest_neighbour_finds_identical_text(database_url: str, book_dir: Path) -> None:
    embedder = FakeEmbedder()
    ingest(book_dir, database_url, embedder)
    with psycopg.connect(database_url) as conn:
        target = conn.execute(
            "select section, content, chapter from chunks where kind = 'glossary'"
        ).fetchone()
        assert target is not None
        query = embedder.embed([f"{target[2]} > {target[0]}\n\n{target[1]}"])[0]
        best = conn.execute(
            "select section from chunks order by embedding <=> %s::vector limit 1",
            (to_pgvector(query),),
        ).fetchone()
    assert best == ("Glossary",)


def test_wrong_dimension_is_rejected(database_url: str, book_dir: Path) -> None:
    class Short(FakeEmbedder):
        dim = 1024

        def embed(self, texts: object) -> list[list[float]]:
            return [[0.0] * 3 for _ in texts]  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="dim"):
        ingest(book_dir, database_url, Short())


def test_empty_directory_is_an_error(database_url: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no chapter notebooks"):
        ingest(tmp_path, database_url, FakeEmbedder())
