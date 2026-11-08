"""Real SQL refills with fake generators/verifiers; no live model-quality claim."""

import asyncio
from typing import Any

import pytest
from psycopg.types.json import Jsonb

from app.content.gateway import ModelReply
from app.content.models import ModelIdentity
from app.content.refill import NeedQuestions, QuestionRefiller
from app.content.repository import Repository
from app.jobs.queue import enqueue
from tests.content.fakes import FakeGateway, topic
from tests.content.test_runtime_database import database_url as database_url
from tests.content.test_runtime_database import store as store


class RefillModel(FakeGateway):
    def __init__(self, concept: str, *, reject: bool) -> None:
        super().__init__()
        self.concept, self.reject = concept, reject
        self.generations = 0
        self.drafts: dict[str, Any] = {}

    async def generate(self, **kwargs: Any) -> ModelReply:
        if kwargs["task"] == "generate_items":
            self.generations += 1
            assert len(kwargs["payload"]["graph"]["concepts"]) == 1
            assert kwargs["payload"]["graph"]["concepts"][0]["slug"] == self.concept
            items = []
            for index, difficulty in enumerate(kwargs["payload"]["difficulty_targets"]):
                item = self.item.model_copy(
                    update={
                        "id": f"draft-{index}",
                        "concept": self.concept,
                        "difficulty": difficulty,
                        "prompt_vi": f"Fixture source probe {index}",
                    }
                )
                self.drafts[item.prompt_vi] = item
                items.append(
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
                )
            return ModelReply(
                content={"items": items},
                identity=ModelIdentity(
                    provider="fixture",
                    model="fixture-gemini",
                    family="gemini",
                    identity_source="gateway",
                ),
            )
        if kwargs["task"] == "verify_item":
            self.item = self.drafts[kwargs["payload"]["question"]]
            self.overrides = {"supported": not self.reject}
        return await super().generate(**kwargs)


@pytest.mark.parametrize("reject", [False, True])
def test_refill_publishes_only_source_scoped_independently_verified_items(
    store: Repository,
    reject: bool,
) -> None:
    _, chunks, graph, items = topic()
    concept = graph.concepts[0].model_copy(update={"slug": "new-probe", "name_vi": "Fixture probe"})
    graph = graph.model_copy(update={"concepts": [*graph.concepts, concept]})
    store.save_graph("python-conditions", graph)
    model = RefillModel(concept.slug, reject=reject)
    model.item = items[0]
    model.chunks = [chunk for chunk in chunks if chunk.chunk_id in concept.chunk_ids]
    with store.transaction() as conn:
        created = conn.execute(
            "insert into learners(display_name) values('refill fixture') returning id"
        ).fetchone()
        assert created is not None
        learner = created[0]
    request = NeedQuestions("python-conditions", concept.slug, 0.25, assessment=True)
    refiller = QuestionRefiller(store, model)
    assert asyncio.run(refiller.ensure(request, learner)) is (not reject)
    with store.transaction() as conn:
        served = [
            bundle
            for key in store.item_ids(conn, "python-conditions")
            if (bundle := store.servable(conn, key)) is not None
            and bundle.item.concept == concept.slug
        ]
    assert len(served) == (0 if reject else 3)
    assert all(set(bundle.item.chunk_ids) <= set(concept.chunk_ids) for bundle in served)
    if not reject:
        assert sorted(bundle.item.difficulty for bundle in served) == [0.25, 0.5, 0.75]
        asyncio.run(refiller.ensure(request, learner))
        assert model.generations == 1
        with store.transaction() as conn:
            easy = next(bundle for bundle in served if bundle.item.difficulty == 0.25)
            conn.execute(
                "insert into attempts(learner_id,item_id,answer,is_correct) values(%s,%s,%s,false)",
                (learner, easy.db_id, Jsonb({"phase": "placement", "difficulty": 0.25})),
            )
        assert asyncio.run(refiller.ensure(request, learner))
        assert model.generations == 1


@pytest.mark.parametrize("reject", [False, True])
def test_refill_drafts_keep_existing_published_questions_available(
    store: Repository,
    reject: bool,
) -> None:
    _, chunks, graph, items = topic()
    concept = graph.concepts[0]
    model = RefillModel(concept.slug, reject=reject)
    model.item = items[0]
    model.chunks = [chunk for chunk in chunks if chunk.chunk_id in concept.chunk_ids]
    with store.transaction() as conn:
        created = conn.execute(
            "insert into learners(display_name) values('review fixture') returning id"
        ).fetchone()
        assert created is not None
        learner = created[0]
        for key in store.item_ids(conn, "python-conditions"):
            bundle = store.servable(conn, key)
            if bundle and bundle.item.concept == concept.slug:
                conn.execute(
                    "insert into attempts(learner_id,item_id,answer,is_correct) "
                    "values(%s,%s,%s,false)",
                    (learner, bundle.db_id, Jsonb({"option_index": 0})),
                )
        job = enqueue(conn, "Fixture review", "free")
        conn.execute(
            "update topic_jobs set subject_slug='python-conditions',status='ready',"
            "graph_ready=true,items_ready=true where id=%s",
            (job,),
        )
    asyncio.run(
        QuestionRefiller(store, model).ensure(
            NeedQuestions("python-conditions", concept.slug, 0.5, assessment=False),
            learner,
        )
    )
    with store.transaction() as conn:
        assert conn.execute(
            "select status,items_ready from topic_jobs where id=%s", (job,)
        ).fetchone() == ("ready", True)
        usable = [
            bundle
            for key in store.item_ids(conn, "python-conditions")
            if (bundle := store.servable(conn, key)) and bundle.item.concept == concept.slug
        ]
        assert len(usable) == (3 if reject else 6)
