"""Ingest Think Python 3e notebooks into chunks + embeddings.

Usage (from apps/api, after `uv sync --extra embed`):
    uv run python -m app.rag.ingest ../../data/raw/thinkpython
"""

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

import psycopg

from app.config import get_settings
from app.rag.embed import Embedder
from app.rag.notebook import Chunk, parse_notebook
from app.rag.store import SourceInfo, replace_chunks, upsert_source

THINK_PYTHON = SourceInfo(
    subject_slug="python",
    subject_name_vi="Lập trình Python",
    subject_name_en="Python programming",
    title="Think Python, 3rd edition",
    author="Allen B. Downey",
    license="CC BY-NC-SA 4.0 (text), MIT (code)",
    url="https://allendowney.github.io/ThinkPython/",
    version="unknown",
)

CHAPTER_FILE = re.compile(r"chap(\d{2})\.ipynb$")


def load_chunks(directory: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("chap*.ipynb")):
        match = CHAPTER_FILE.search(path.name)
        if match is None:
            continue
        notebook = json.loads(path.read_text(encoding="utf-8"))
        chunks.extend(parse_notebook(notebook, int(match.group(1))))
    return chunks


def ingest(directory: Path, database_url: str, embedder: Embedder) -> int:
    sha_file = directory / "SOURCE_SHA"
    version = sha_file.read_text().strip() if sha_file.exists() else "unknown"
    chunks = load_chunks(directory)
    if not chunks:
        raise ValueError(f"no chapter notebooks found in {directory}")
    info = replace(THINK_PYTHON, version=version)
    with psycopg.connect(database_url) as conn:
        source_id = upsert_source(conn, info)
        return replace_chunks(conn, source_id, chunks, embedder)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    from app.rag.embed import BgeM3Embedder

    count = ingest(args.directory, get_settings().database_url, BgeM3Embedder())
    print(f"Ingested {count} chunks from {args.directory}", file=sys.stderr)


if __name__ == "__main__":
    main()
