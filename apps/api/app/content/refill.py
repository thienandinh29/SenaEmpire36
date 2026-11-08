"""Bounded question refills from an existing concept's verified source material."""

import asyncio
import logging
from uuid import UUID, uuid4

from app.content.gateway import Gateway, GatewayError
from app.content.models import Graph
from app.content.pipeline import generate_items
from app.content.repository import ContentUnavailable, Repository
from app.engine import survey
from app.llm.gateway import GatewayError as ModelGatewayError

logger = logging.getLogger(__name__)


class NeedQuestions(Exception):
    def __init__(self, subject: str, slug: str, difficulty: float, *, assessment: bool) -> None:
        super().__init__("Verified question refill required")
        self.subject, self.slug, self.difficulty = subject, slug, difficulty
        self.assessment = assessment


class QuestionRefiller:
    def __init__(self, repository: Repository, gateway: Gateway | None) -> None:
        self.repo, self.gateway = repository, gateway
        self.locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def ensure(self, request: NeedQuestions, learner: UUID) -> bool:
        if self.gateway is None:
            return False
        key = (request.subject, request.slug)
        async with self.locks.setdefault(key, asyncio.Lock()):

            def load():  # type: ignore[no-untyped-def]
                with self.repo.transaction() as conn:
                    graph = self.repo.graph(conn, request.subject)
                    concept = next((c for c in graph.concepts if c.slug == request.slug), None)
                    if concept is None:
                        raise ContentUnavailable(
                            "The requested concept is no longer in the curriculum"
                        )
                    sources, chunks = self.repo.material(conn, concept.chunk_ids)
                    attempted = {
                        row[0]
                        for row in conn.execute(
                            "select item_id from attempts where learner_id=%s",
                            (learner,),
                        )
                    }
                    bank = [
                        bundle
                        for item_id in self.repo.item_ids(conn, request.subject)
                        if (bundle := self.repo.current(conn, item_id)) is not None
                        and bundle.item.concept == request.slug
                    ]
                    usable = [
                        bundle
                        for bundle in bank
                        if bundle.db_id not in attempted
                        and self.repo.servable(conn, bundle.item.id) is not None
                    ]
                    assessed_levels = {
                        survey.level(row[0])
                        for row in conn.execute(
                            "select coalesce((a.answer->>'difficulty')::double precision,"
                            "i.difficulty) "
                            "from attempts a join items i on i.id=a.item_id "
                            "join concepts c on c.id=i.concept_id "
                            "where a.learner_id=%s and c.subject_id=%s and c.slug=%s "
                            "and a.answer->>'phase'='placement'",
                            (learner, self.repo._subject(conn, request.subject), request.slug),
                        )
                    }
                    targets = (
                        [
                            value
                            for value in survey.DIFFICULTIES
                            if survey.level(value) not in assessed_levels
                            and not any(
                                survey.level(b.item.difficulty) == survey.level(value)
                                for b in usable
                            )
                        ]
                        if request.assessment
                        else [request.difficulty] * (0 if usable else 3)
                    )
                    definitions = {
                        (bundle.item.concept, m.slug): m.description_vi
                        for bundle in bank
                        for m in bundle.item.misconceptions
                    }
                    return (
                        Graph(
                            concepts=[
                                concept.model_copy(
                                    update={"sources": sorted({s.url for s in sources})}
                                )
                            ],
                            edges=[],
                        ),
                        sources,
                        chunks,
                        bank,
                        targets,
                        definitions,
                    )

            feedback = None
            for _attempt in range(2):
                try:
                    graph, sources, chunks, bank, targets, definitions = await asyncio.to_thread(
                        load
                    )
                    if not targets:
                        return True
                    generated = await generate_items(
                        graph,
                        chunks,
                        sources,
                        self.gateway,
                        tier="free",
                        count=len(targets),
                        id_namespace=f"{request.subject}:refill-{uuid4().hex}",
                        difficulty_targets=targets,
                        existing_prompts=[bundle.item.prompt_vi for bundle in bank],
                        misconception_descriptions=definitions,
                        verification_attempts=1,
                        allow_partial=True,
                        repair_feedback=feedback,
                    )
                    existing = {bundle.item.prompt_vi.strip().casefold() for bundle in bank}
                    unique = []
                    for item in generated:
                        prompt = item.prompt_vi.strip().casefold()
                        if prompt not in existing:
                            existing.add(prompt)
                            unique.append(item)
                    # save_items reloads current sources; servable rechecks verification/hash
                    # against those rows before any question can reach the learner.
                    if unique:
                        await asyncio.to_thread(
                            self.repo.save_items,
                            request.subject,
                            unique,
                            preserve_publication=True,
                        )
                    _, _, _, _, remaining, _ = await asyncio.to_thread(load)
                    if not remaining:
                        return True
                    feedback = (
                        "The previous batch did not supply verified questions for every requested "
                        "difficulty level. Generate only the supplied difficulty_targets, "
                        "in order. "
                        "Use the exact concept slug, source URLs and chunk IDs. Give each option "
                        "a distinct ID and answer text, with exactly one source-supported answer. "
                        "Do not repeat avoid_questions."
                    )
                except (
                    GatewayError,
                    ModelGatewayError,
                    ValueError,
                    ContentUnavailable,
                    TimeoutError,
                ) as error:
                    logger.warning("Question refill attempt failed: %s", type(error).__name__)
                    if isinstance(error, ModelGatewayError):
                        logger.warning("Question refill model error: %s", error)
                    feedback = (
                        "Repair the batch schema and citations; use only supplied source data."
                    )
            return False
