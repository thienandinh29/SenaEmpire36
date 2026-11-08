"""Regression checks for complete curriculum maps, independent of lesson size."""

import asyncio
from typing import Any
from uuid import uuid4

import pytest

from app.content.gateway import ModelReply
from app.content.models import Edge, Graph
from app.content.pipeline import _merge_graphs, generate_graph
from app.content.ports import ContentPorts
from app.content.prompts import GRAPH_VERSION
from app.research.pipeline import PreparedChunk
from tests.content.fakes import FakeGateway, topic
from tests.content.test_job_pipeline import MemoryRepository, Model


def test_long_curriculum_preserves_every_batch_and_merges_shared_knowledge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, original, fixture, _ = topic()
    base = fixture.concepts[0]
    source_chunk = next(c for c in original if c.chunk_id in base.chunk_ids)
    chunks = [source_chunk.model_copy(update={"chunk_id": uuid4()}) for _ in range(4)]
    monkeypatch.setattr("app.content.pipeline.GRAPH_BATCH_CHARS", 1)

    class Curriculum(FakeGateway):
        batch = 0

        async def generate(self, **kwargs: Any) -> ModelReply:
            index = self.batch
            chunk = chunks[index]
            assert str(chunk.chunk_id) in kwargs["payload"]["source_data"]
            assert all(
                str(other.chunk_id) not in kwargs["payload"]["source_data"]
                for other in chunks
                if other != chunk
            )
            if index:
                assert len(kwargs["payload"]["existing_graph"]["concepts"]) == 1 + 2 * index
            concepts = [
                base.model_copy(
                    update={
                        "slug": f"shared-{index}",
                        "name_vi": "Kiến thức chung",
                        "chunk_ids": [chunk.chunk_id],
                        "pages": [],
                    }
                ),
                *[
                    base.model_copy(
                        update={
                            "slug": f"rule-{index}-{part}",
                            "name_vi": f"Quy tắc riêng {index}-{part}",
                            "chunk_ids": [chunk.chunk_id],
                            "pages": [],
                        }
                    )
                    for part in range(2)
                ],
            ]
            graph = Graph(
                concepts=concepts,
                edges=[
                    Edge.model_validate(
                        {
                            "from": concepts[0].slug,
                            "to": concepts[1].slug,
                            "chunk_ids": [chunk.chunk_id],
                            "rationale_vi": "Fixture prerequisite",
                            "evidence_kind": "source_explicit",
                        }
                    )
                ],
            )
            self.batch += 1
            return ModelReply(
                content={
                    "relevant_to_goal": True,
                    "graph": graph.model_dump(mode="json", by_alias=True),
                    "reason_vi": "Fixture",
                },
                identity=self.item.generator,
            )

    gateway = Curriculum()
    result = asyncio.run(generate_graph(chunks, sources, gateway, goal="Python"))
    assert gateway.batch == 4
    assert len(result.concepts) == 9
    assert len(result.edges) == 4
    assert set(result.concepts[0].chunk_ids) == {chunk.chunk_id for chunk in chunks}
    assert all(edge.prerequisite == "shared-0" for edge in result.edges)
    assert result.source_chunk_ids == [chunk.chunk_id for chunk in chunks]
    assert result.extraction_version == GRAPH_VERSION


def test_merging_batches_rejects_a_cross_batch_cycle() -> None:
    _, _, graph, _ = topic()
    edge = graph.edges[0]
    reverse = edge.model_copy(update={"prerequisite": edge.to, "to": edge.prerequisite})
    with pytest.raises(ValueError, match="cycle"):
        _merge_graphs(graph, Graph(concepts=graph.concepts, edges=[reverse]))


@pytest.mark.parametrize("version", [None, "p4-graph-v3", GRAPH_VERSION])
def test_only_current_extraction_checkpoints_are_reused(version: str | None) -> None:
    repo = MemoryRepository()
    repo.graph_saved = True
    repo.kg = repo.kg.model_copy(
        update={
            "source_chunk_ids": [chunk.chunk_id for chunk in repo.chunks],
            "extraction_version": version,
        }
    )

    class CountingModel(Model):
        extractions = 0

        async def generate(self, **kwargs: Any) -> ModelReply:
            if kwargs["task"] == "extract_graph":
                self.extractions += 1
            return await super().generate(**kwargs)

    gateway = CountingModel()
    ports = ContentPorts(repo, gateway, "python-conditions")
    ports.chunks, ports.sources = repo.chunks, repo.sources
    prepared = [
        PreparedChunk(
            id=str(chunk.chunk_id),
            text=chunk.content,
            source_uri=next(
                source.url for source in repo.sources if source.source_id == chunk.source_id
            ),
        )
        for chunk in repo.chunks
    ]
    asyncio.run(ports.build_graph("Python", prepared, "free"))
    assert gateway.extractions == (0 if version == GRAPH_VERSION else 1)
    assert ports.graph is not None and ports.graph.extraction_version == GRAPH_VERSION
