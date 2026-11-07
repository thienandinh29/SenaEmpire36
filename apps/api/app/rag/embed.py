"""Text embeddings behind a small protocol, so tests use a fake and never load the model."""

from collections.abc import Sequence
from typing import Any, Protocol

EMBEDDING_DIM = 1024  # must match chunks.embedding vector(1024)


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class BgeM3Embedder:
    """BAAI/bge-m3 dense vectors: multilingual, so Vietnamese questions match English text.

    Needs the optional `embed` extra (`uv sync --extra embed`). First use downloads ~2.3 GB.
    """

    model_name = "BAAI/bge-m3"
    dim = EMBEDDING_DIM

    def __init__(self, batch_size: int = 16) -> None:
        # Imported here so the API and CI run without PyTorch installed.
        from sentence_transformers import SentenceTransformer

        self._model: Any = SentenceTransformer(self.model_name, device="cpu")
        self._batch_size = batch_size

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,  # unit length, so cosine distance == the HNSW index metric
            show_progress_bar=len(texts) > 64,
        )
        return [[float(x) for x in v] for v in vectors]


def to_pgvector(vector: Sequence[float]) -> str:
    """pgvector text literal; avoids a numpy-based adapter dependency."""
    return "[" + ",".join(f"{x:.7g}" for x in vector) + "]"
