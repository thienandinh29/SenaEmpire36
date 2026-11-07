import asyncio
from collections.abc import Sequence

import pytest

from app.api.topics import TopicInput
from app.graders.mcq import Item
from app.research.agent import ChosenSource, OnEvent
from app.research.pipeline import GraphDraft, PreparedChunk, Progress, TopicPipeline, marked_chunks
from app.research.reader import SourceError
from app.uploads.reader import Document, Page
from tests.graders.test_mcq import item


class Ports:
    def __init__(self) -> None:
        self.upload = Document("private/uploads/u1.pdf", (Page(1, "Nguồn học tập"),), True)
        self.items = [item().model_copy(update={"id": f"q{i}"}) for i in range(6)]
        self.graph_saved = self.items_saved = False
        self.supported = True

    async def load_upload(self, upload_id: str) -> Document | None:
        return self.upload if upload_id == "u1" else None

    async def quick_sources(self, goal: str) -> Sequence[ChosenSource]:
        return [ChosenSource("Book", "Publisher", "https://books.example/a", "CC BY 4.0", "text")]

    async def index(
        self, sources: Sequence[ChosenSource], upload: Document | None
    ) -> Sequence[PreparedChunk]:
        return [
            PreparedChunk(id="chunk-1", text="Nguồn", source_uri="https://books.example/a", page=1)
        ]

    async def build_graph(
        self, goal: str, chunks: Sequence[PreparedChunk], tier: str
    ) -> GraphDraft:
        return GraphDraft(subject_slug="biology", graph={"concepts": []}, supported=self.supported)

    async def save_graph(self, graph: GraphDraft) -> None:
        self.graph_saved = True

    async def build_items(
        self,
        graph: GraphDraft,
        chunks: Sequence[PreparedChunk],
        tier: str,
        count: int,
    ) -> Sequence[Item]:
        return self.items

    async def save_items(self, subject_slug: str, items: Sequence[Item]) -> None:
        self.items_saved = True


def test_quick_upload_pipeline_never_searches_and_publishes_only_after_persistence() -> None:
    ports = Ports()
    states: list[Progress] = []

    async def progress(value: Progress) -> None:
        if value.graph_ready:
            assert ports.graph_saved
        if value.items_ready:
            assert ports.items_saved
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        pytest.fail("Quick mode must never search")

    result = asyncio.run(
        TopicPipeline(ports).run(
            TopicInput(upload_id="u1", mode="quick", tier="free"),
            progress,
            event,
        )
    )
    assert result.subject_slug == "biology" and len(result.item_ids) == 6
    assert [s.status for s in states] == ["researching", "indexing", "graph", "items", "ready"]


@pytest.mark.parametrize("failure", ["pending", "citation", "duplicate", "graph"])
def test_pipeline_does_not_publish_invalid_items_or_graph(failure: str) -> None:
    ports = Ports()
    if failure == "pending":
        ports.items[0] = ports.items[0].model_copy(update={"status": "needs_review"})
    elif failure == "citation":
        ports.items[0] = ports.items[0].model_copy(update={"chunk_ids": ["foreign-chunk"]})
    elif failure == "duplicate":
        ports.items[0] = ports.items[1]
    else:
        ports.supported = False
    states: list[Progress] = []

    async def progress(value: Progress) -> None:
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        pass

    with pytest.raises(SourceError):
        asyncio.run(
            TopicPipeline(ports).run(
                TopicInput(goal_vi="biology", mode="quick", tier="free"),
                progress,
                event,
            )
        )
    assert states[-1].status == "failed" and not ports.items_saved
    assert all(not state.items_ready for state in states)


def test_deadline_cancels_job_and_reports_failed() -> None:
    class SlowPorts(Ports):
        async def quick_sources(self, goal: str) -> Sequence[ChosenSource]:
            await asyncio.sleep(100)
            return []

    states: list[Progress] = []

    async def progress(value: Progress) -> None:
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        pass

    with pytest.raises(SourceError, match="hết thời gian"):
        asyncio.run(
            TopicPipeline(SlowPorts(), quick_seconds=0.01).run(
                TopicInput(goal_vi="biology", mode="quick", tier="free"),
                progress,
                event,
            )
        )
    assert states[-1].status == "failed"


def test_long_context_markers_preserve_ids_and_provenance() -> None:
    text = marked_chunks(
        [PreparedChunk(id="c1", text="Nội dung", source_uri="private/u.pdf", page=3)]
    )
    assert "[chunk_id=c1]" in text and "page: 3" in text and "private/u.pdf" in text


def test_deep_pipeline_uses_research_and_preserves_source_summaries() -> None:
    ports = Ports()
    states: list[Progress] = []
    events: list[dict[str, str]] = []

    async def deep(goal: str, event: OnEvent) -> list[ChosenSource]:
        await event({"kind": "search", "text_vi": "Đang tìm nguồn…"})
        return [
            ChosenSource(
                f"Book {i}",
                f"Publisher {i % 2}",
                f"https://books.example/{i}",
                "CC BY 4.0",
                "source",
            )
            for i in range(3)
        ]

    async def progress(value: Progress) -> None:
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        events.append(value)

    result = asyncio.run(
        TopicPipeline(ports, research_runner=deep).run(
            TopicInput(goal_vi="biology", mode="deep", tier="pro"),
            progress,
            event,
        )
    )
    assert len(result.sources) == 3 and len(states[-1].sources) == 3
    assert "at" in events[0]
    assert not hasattr(states[-1].sources[0], "text")


def test_missing_upload_and_internal_failure_are_not_reported_ready() -> None:
    states: list[Progress] = []

    async def progress(value: Progress) -> None:
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        pass

    with pytest.raises(SourceError, match="Không tìm thấy"):
        asyncio.run(
            TopicPipeline(Ports()).run(
                TopicInput(upload_id="missing", mode="quick", tier="free"),
                progress,
                event,
            )
        )
    assert states[-1].status == "failed"


def test_worker_shutdown_propagates_cancellation_without_failed_write() -> None:
    class CancelledPorts(Ports):
        async def quick_sources(self, goal: str) -> Sequence[ChosenSource]:
            raise asyncio.CancelledError

    states: list[Progress] = []

    async def progress(value: Progress) -> None:
        states.append(value)

    async def event(value: dict[str, str]) -> None:
        pass

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            TopicPipeline(CancelledPorts()).run(
                TopicInput(goal_vi="biology", mode="quick", tier="free"),
                progress,
                event,
            )
        )
    assert all(state.status != "failed" for state in states)


def test_progress_sink_failure_does_not_expose_internal_error() -> None:
    async def progress(value: Progress) -> None:
        raise RuntimeError("secret database connection details")

    async def event(value: dict[str, str]) -> None:
        pass

    with pytest.raises(SourceError) as caught:
        asyncio.run(
            TopicPipeline(Ports()).run(
                TopicInput(goal_vi="biology", mode="quick", tier="free"),
                progress,
                event,
            )
        )
    assert "secret" not in str(caught.value)
