"""P4 PipelinePorts: P3 orchestration + P1 chunker + P2's persistent database IDs."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.api.topics import TopicInput
from app.content.gateway import Gateway
from app.content.integration import pipeline_graph, pipeline_items
from app.content.models import Chunk, Graph, Item, Source
from app.content.pipeline import generate_graph, generate_items, require_model_permission
from app.content.repository import ContentUnavailable, Repository, stable_id
from app.graders.mcq import Item as GraderItem
from app.research.agent import ChosenSource, detect_license
from app.research.pipeline import GraphDraft, PreparedChunk, Progress, TopicPipeline
from app.uploads.metadata import UploadMetadata
from app.uploads.reader import Document


class ContentPorts:
    def __init__(
        self,
        repository: Repository,
        gateway: Gateway,
        subject: str,
        *,
        upload_model_permission: bool = False,
    ) -> None:
        self.repository, self.gateway, self.subject = repository, gateway, subject
        self.upload_model_permission = upload_model_permission
        self.sources: list[Source] = []
        self.chunks: list[Chunk] = []
        self.graph: Graph | None = None
        self.generated: list[Item] = []

    async def load_upload(self, upload_id: str) -> Document | None:
        def load() -> Document | None:
            from psycopg.rows import dict_row

            with self.repository.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute("select * from uploads where id=%s", (UUID(upload_id),))
                row = cur.fetchone()
                if not row:
                    return None
                row.pop("created_at", None)
                return UploadMetadata.model_validate(row).document()

        return await asyncio.to_thread(load)

    async def quick_sources(self, goal: str) -> Sequence[ChosenSource]:
        def select() -> list[ChosenSource]:
            with self.repository.transaction() as conn:
                rows = conn.execute(
                    "select s.slug,r.p4_metadata from sources r join subjects s "
                    "on s.id=r.subject_id order by s.slug,r.title"
                ).fetchall()
            selected = []
            for slug, metadata in rows:
                if not metadata:
                    continue
                source = Source.model_validate(metadata)
                tokens = [word for word in slug.split("-") if len(word) >= 3]
                if source.model_ingestion_allowed and any(
                    word in goal.casefold() for word in tokens
                ):
                    selected.append(
                        ChosenSource(source.title, source.publisher, source.url, source.license, "")
                    )
            return selected[:3]

        return await asyncio.to_thread(select)

    async def index(
        self, sources: Sequence[ChosenSource], upload: Document | None
    ) -> Sequence[PreparedChunk]:
        def prepare() -> None:
            from app.rag.chunker import chunk_document
            from app.schemas import DocBlock, ParsedDocument

            if upload:
                if not self.upload_model_permission:
                    raise ContentUnavailable("Upload model-use permission must be supplied by P2")
                source = Source(
                    source_id=upload.source_uri,
                    title="Tài liệu người học",
                    author="Người cung cấp",
                    publisher="Người cung cấp",
                    version="uploaded document",
                    url=upload.source_uri,
                    section="Tài liệu tải lên",
                    license="User-provided with model-use permission",
                    accessed_at=datetime.now(UTC).date().isoformat(),
                    attribution="Learner upload",
                    model_ingestion_allowed=True,
                )
                parsed = ParsedDocument(
                    blocks=[
                        DocBlock(
                            chapter=source.title,
                            section=f"Trang {page.number}",
                            text=page.text,
                            source_uri=upload.source_uri,
                            page=page.number,
                        )
                        for page in upload.pages
                    ]
                )
                split = chunk_document(parsed)
                self.sources = [source]
                self.chunks = [
                    Chunk(
                        chunk_id=stable_id("chunk", upload.source_uri, str(i)),
                        source_id=source.source_id,
                        section=c.section,
                        page=c.page,
                        content=c.content,
                        representation="verbatim",
                        license=source.license,
                    )
                    for i, c in enumerate(split)
                ]
                self.repository.save_material(self.subject, self.sources, self.chunks)
                return
            uris = [s.url for s in sources]
            with self.repository.transaction() as conn:
                ids = [
                    row[0]
                    for row in conn.execute(
                        "select c.id from chunks c join sources s on s.id=c.source_id "
                        "where s.url=any(%s) order by s.url,c.chunk_index",
                        (uris,),
                    )
                ]
                if ids:
                    self.sources, self.chunks = self.repository.material(conn, ids)
            if not self.chunks:
                # Deep-research pages have no indexed IDs yet; use P1's chunker once,
                # persist stable IDs before any model sees them, then reload those IDs.
                for document in sources:
                    license_name = detect_license(document.text + "\n" + document.license)
                    source = Source(
                        source_id=document.url,
                        title=document.title,
                        author="",
                        publisher=document.publisher,
                        version="research page",
                        url=document.url,
                        section=document.title,
                        license=license_name,
                        accessed_at=datetime.now(UTC).date().isoformat(),
                        attribution=document.publisher,
                        model_ingestion_allowed=True,
                    )
                    split = chunk_document(
                        ParsedDocument(
                            blocks=[
                                DocBlock(
                                    chapter=source.title,
                                    section=source.section,
                                    text=document.text,
                                    source_uri=document.url,
                                )
                            ]
                        )
                    )
                    self.sources.append(source)
                    self.chunks.extend(
                        Chunk(
                            chunk_id=stable_id("chunk", self.subject, document.url, str(i)),
                            source_id=source.source_id,
                            section=c.section,
                            page=c.page,
                            content=c.content,
                            representation="verbatim",
                            license=source.license,
                        )
                        for i, c in enumerate(split)
                    )
                self.repository.save_material(self.subject, self.sources, self.chunks)
            # A new topic may reuse library chunks in another subject without re-embedding.
            with self.repository.transaction() as conn:
                conn.execute(
                    "insert into subjects(id,slug,name_vi,name_en) values(%s,%s,%s,%s) "
                    "on conflict(slug) do nothing",
                    (stable_id("subject", self.subject), self.subject, self.subject, self.subject),
                )

        await asyncio.to_thread(prepare)
        require_model_permission(self.sources)
        return [
            PreparedChunk(
                id=str(c.chunk_id),
                text=c.content,
                page=c.page,
                source_uri=next(s.url for s in self.sources if s.source_id == c.source_id),
            )
            for c in self.chunks
        ]

    async def build_graph(
        self, goal: str, chunks: Sequence[PreparedChunk], tier: str
    ) -> GraphDraft:
        # IDs must be exactly the durable IDs returned by index, never model-invented IDs.
        if {c.id for c in chunks} != {str(c.chunk_id) for c in self.chunks}:
            raise ContentUnavailable("Prepared chunk IDs changed")
        try:
            with self.repository.transaction() as conn:
                self.graph = self.repository.graph(conn, self.subject)
            return pipeline_graph(self.subject, self.graph, self.chunks, self.sources)
        except ContentUnavailable:
            self.graph = await generate_graph(self.chunks, self.sources, self.gateway, tier=tier)
            return pipeline_graph(self.subject, self.graph, self.chunks, self.sources)

    async def save_graph(self, graph: GraphDraft) -> None:
        if self.graph is None or graph.subject_slug != self.subject:
            raise ContentUnavailable("Graph/job mismatch")
        await asyncio.to_thread(self.repository.save_graph, self.subject, self.graph)

    async def build_items(
        self, graph: GraphDraft, chunks: Sequence[PreparedChunk], tier: str, count: int
    ) -> Sequence[GraderItem]:
        if not self.graph:
            raise ContentUnavailable("Graph missing")

        def existing() -> list[Item]:
            with self.repository.transaction() as conn:
                return [
                    bundle.item
                    for key in self.repository.item_ids(conn, self.subject)
                    if (bundle := self.repository.current(conn, key)) is not None
                ]

        ready = await asyncio.to_thread(existing)
        if len(ready) >= count:
            self.generated = ready
        else:
            self.generated = await generate_items(
                self.graph,
                self.chunks,
                self.sources,
                self.gateway,
                tier=tier,
                count=count,
                id_namespace=self.subject,
            )
            # Save pending outcomes/audits too; P3 receives only currently verified projections.
            await asyncio.to_thread(self.repository.save_items, self.subject, self.generated)
        return pipeline_items(self.generated, self.chunks)

    async def save_items(self, subject_slug: str, items: Sequence[GraderItem]) -> None:
        if subject_slug != self.subject or not {i.id for i in items} <= {
            i.id for i in self.generated
        }:
            raise ContentUnavailable("Item/job mismatch")

        def recheck() -> None:
            with self.repository.transaction() as conn:
                if any(self.repository.current(conn, item.id) is None for item in items):
                    raise ContentUnavailable("An item changed before publication")

        await asyncio.to_thread(recheck)


async def process_claimed_job(
    repository: Repository, gateway: Gateway, job: dict[str, object]
) -> None:
    """Called AFTER P2 claim commits. All progress uses the existing topic_jobs row."""
    from dataclasses import asdict

    from psycopg.types.json import Jsonb

    subject = f"topic-{UUID(str(job['id'])).hex}"
    ports = ContentPorts(repository, gateway, subject)
    request = TopicInput.model_validate(
        {
            "goal_vi": job["goal_vi"],
            "tier": job["tier"],
            "mode": job.get("mode", "quick"),
            "upload_id": str(job["upload_id"]) if job.get("upload_id") else None,
        }
    )

    async def progress(state: Progress) -> None:
        def save() -> None:
            with repository.transaction() as conn:
                conn.execute(
                    "update topic_jobs set status=%s,step_vi=%s,progress=%s,graph_ready=%s,"
                    "items_ready=%s,subject_slug=%s,sources=%s,updated_at=now() where id=%s",
                    (
                        state.status,
                        state.step_vi,
                        state.progress,
                        state.graph_ready,
                        state.items_ready,
                        state.subject_slug,
                        Jsonb([asdict(s) for s in state.sources]),
                        job["id"],
                    ),
                )

        await asyncio.to_thread(save)

    async def event(value: dict[str, str]) -> None:
        def save() -> None:
            with repository.transaction() as conn:
                conn.execute(
                    "update topic_jobs set trail=trail||%s::jsonb,updated_at=now() where id=%s",
                    (Jsonb([value]), job["id"]),
                )

        await asyncio.to_thread(save)

    await TopicPipeline(ports).run(request, progress, event)
