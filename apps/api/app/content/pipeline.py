"""Source -> validated graph -> draft items -> independent verification."""

from pydantic import Field

from app.content.gateway import Gateway, parse_reply
from app.content.models import (
    Chunk,
    Graph,
    Item,
    Misconception,
    Option,
    Record,
    Source,
    cited_chunks,
    validate_references,
)
from app.content.prompts import GRAPH_SYSTEM, ITEM_SYSTEM, marked_chunks
from app.guardrails.answerability import verify_item


def require_model_permission(sources: list[Source]) -> None:
    if not sources or any(not source.model_ingestion_allowed for source in sources):
        raise ValueError("source permission for model ingestion is not confirmed")


class DraftItem(Record):
    id: str
    concept: str
    prompt_vi: str
    difficulty: float = Field(ge=0, le=1)
    source: str
    source_ids: list[str]
    chunk_ids: list[str]
    options: list[Option]
    answer_id: str
    explanation_vi: str
    misconceptions: list[Misconception]


class DraftBatch(Record):
    items: list[DraftItem] = Field(min_length=1)


def validate_items(
    items: list[Item], chunks: list[Chunk], sources: list[Source], graph: Graph
) -> None:
    validate_references(chunks, sources, graph)
    if len({i.id for i in items}) != len(items):
        raise ValueError("duplicate item IDs")
    urls = {s.source_id: s.url for s in sources}
    slugs = {c.slug for c in graph.concepts}
    for item in items:
        cited_chunks(item, chunks)
        if item.concept not in slugs:
            raise ValueError("unknown item concept")
        if any(s not in urls for s in item.source_ids):
            raise ValueError("unknown item source")
        if item.source not in {urls[s] for s in item.source_ids}:
            raise ValueError("item URL does not match its source")


async def generate_graph(
    chunks: list[Chunk], sources: list[Source], gateway: Gateway, *, tier: str = "pro"
) -> Graph:
    validate_references(chunks, sources)
    require_model_permission(sources)
    reply = await gateway.generate(
        task="extract_graph",
        tier=tier,
        system=GRAPH_SYSTEM,
        payload={
            "source_data": marked_chunks(chunks),
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        schema=Graph,
    )
    graph = parse_reply(reply, Graph)
    validate_references(chunks, sources, graph)
    require_model_permission(sources)
    return graph


async def generate_items(
    graph: Graph,
    chunks: list[Chunk],
    sources: list[Source],
    gateway: Gateway,
    *,
    tier: str = "pro",
    count: int = 15,
) -> list[Item]:
    if count < 1 or count > 50:
        raise ValueError("count must be 1..50")
    validate_references(chunks, sources, graph)
    reply = await gateway.generate(
        task="generate_items",
        tier=tier,
        system=ITEM_SYSTEM,
        payload={
            "graph": graph.model_dump(mode="json", by_alias=True),
            "source_data": marked_chunks(chunks),
            "count": count,
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        schema=DraftBatch,
    )
    batch = parse_reply(reply, DraftBatch)
    if len(batch.items) != count:
        raise ValueError("generator returned an unexpected item count")
    items = [
        Item.model_validate(
            {
                **draft.model_dump(mode="json"),
                "generator": reply.identity.model_dump(mode="json"),
                "status": "needs_review",
            }
        )
        for draft in batch.items
    ]
    validate_items(items, chunks, sources, graph)
    return [await verify_item(item, chunks, gateway, tier=tier) for item in items]
