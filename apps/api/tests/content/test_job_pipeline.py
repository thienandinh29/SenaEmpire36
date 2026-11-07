"""Real orchestration with in-memory test ports/fake models; not a live-model demo."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.content.gateway import ModelReply
from app.content.models import Graph, Item, ModelIdentity
from app.content.ports import process_claimed_job
from app.content.repository import ContentUnavailable, Repository, StoredItem
from app.guardrails.answerability import is_currently_verified
from app.research.reader import SourceError
from tests.content.fakes import FakeGateway, topic


class MemoryRepository(Repository):
    """Test double for SQL storage. Database guarantees are tested separately."""

    def __init__(self) -> None:
        self.sources, self.chunks, self.kg, self.fixture_items = topic()
        self.saved: dict[str, Item] = {}
        self.graph_saved = False
        self.progress: list[tuple[object, ...]] = []
        self.fail_save = False

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        yield self

    def execute(self, query: str, params: tuple[object, ...] = ()) -> "MemoryRepository":
        self.query, self.params = query, params
        if query.startswith("update topic_jobs set status="):
            if params[0] == "ready":
                assert len(self.saved) >= 6
                assert all(is_currently_verified(item, self.chunks) for item in self.saved.values())
            self.progress.append(params)
        return self

    def fetchall(self) -> list[Any]:
        if "s.slug,r.p4_metadata" in self.query:
            return [("python-conditions", self.sources[0].model_dump(mode="json"))]
        if "select c.id" in self.query:
            return [(c.chunk_id,) for c in self.chunks]
        raise AssertionError(self.query)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.fetchall())

    def material(self, conn: Any, ids: list[Any]):  # type: ignore[no-untyped-def]
        assert set(ids) == {c.chunk_id for c in self.chunks}
        return self.sources, self.chunks

    def graph(self, conn: Any, subject: str) -> Graph:
        if not self.graph_saved:
            raise ContentUnavailable("graph not ready")
        return self.kg

    def save_graph(self, subject: str, graph: Graph) -> None:
        self.kg, self.graph_saved = graph, True

    def item_ids(self, conn: Any, subject: str) -> list[str]:
        return list(self.saved)

    def current(self, conn: Any, external_id: str) -> StoredItem | None:
        item = self.saved.get(external_id)
        if item and is_currently_verified(item, self.chunks):
            return StoredItem(uuid4(), "unit-subject", item, self.chunks, self.sources, 0)
        return None

    def save_items(self, subject: str, items: list[Item]) -> None:
        if self.fail_save:
            raise ContentUnavailable("Simulated SQL transaction failure")
        self.saved.update({item.id: item for item in items})


class Model(FakeGateway):
    def __init__(self) -> None:
        super().__init__()
        self.generate_count = 0
        self.reject = False

    async def generate(
        self,
        *,
        task: str,
        tier: str,
        system: str,
        payload: dict[str, object],
        schema: type[BaseModel],
        exclude_family: str | None = None,
    ) -> ModelReply:
        _, chunks, graph, items = topic()
        if task in {"extract_graph", "generate_items"}:
            if task == "extract_graph":
                data: object = graph.model_dump(mode="json", by_alias=True)
            else:
                self.generate_count += 1
                selected = [items[i] for i in [0, 3, 6, 9, 12, 1]]
                data = {
                    "items": [
                        item.model_dump(
                            mode="json",
                            exclude={
                                "kind",
                                "status",
                                "generator",
                                "verification",
                                "verification_history",
                                "human_review",
                            },
                        )
                        for item in selected
                    ]
                }
            return ModelReply(
                content=data,
                identity=ModelIdentity(
                    provider="fake", model="fake-gemini", family="gemini", identity_source="gateway"
                ),
            )
        if task == "verify_item":
            self.item = next(item for item in items if item.prompt_vi == payload["question"])
            self.chunks = [c for c in chunks if c.chunk_id in self.item.chunk_ids]
            self.overrides = {"supported": False} if self.reject else {}
        return await super().generate(
            task=task,
            tier=tier,
            system=system,
            payload=payload,
            schema=schema,
            exclude_family=exclude_family,
        )


def test_claimed_job_runs_p3_pipeline_p4_generation_gate_and_idempotent_retry() -> None:
    repo, models = MemoryRepository(), Model()
    job: dict[str, object] = {
        "id": uuid4(),
        "goal_vi": "Tôi muốn học Python",
        "tier": "free",
        "mode": "quick",
    }
    asyncio.run(process_claimed_job(repo, models, job))
    first = set(repo.saved)
    assert len(first) == 6 and repo.progress[-1][0] == "ready"
    assert models.generate_count == 1
    asyncio.run(process_claimed_job(repo, models, job))
    assert set(repo.saved) == first and models.generate_count == 1
    assert all("item-" in key for key in first)


@pytest.mark.parametrize("failure", ["rejected", "save_error"])
def test_job_never_becomes_ready_before_verified_content_is_saved(failure: str) -> None:
    repo, models = MemoryRepository(), Model()
    models.reject = failure == "rejected"
    repo.fail_save = failure == "save_error"
    with pytest.raises(SourceError):
        asyncio.run(
            process_claimed_job(repo, models, {"id": uuid4(), "goal_vi": "Python", "tier": "free"})
        )
    assert repo.progress[-1][0] == "failed"
    assert not any(row[0] == "ready" for row in repo.progress)
