"""Verify the real content adapter passes question context into the existing BKT."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.content.repository import Repository
from app.content.runtime import create_app
from app.engine import bkt
from app.services.learning import save_mastery
from tests.content.fakes import FakeGateway
from tests.content.test_runtime_database import (
    ConfirmedGraphs,
)
from tests.content.test_runtime_database import (
    confirmed_graphs as confirmed_graphs,
)
from tests.content.test_runtime_database import database_url as database_url
from tests.content.test_runtime_database import (
    store as store,
)


def test_real_review_uses_stored_difficulty_and_persists_the_same_result(
    store: Repository,
    database_url: str,
    confirmed_graphs: ConfirmedGraphs,
) -> None:
    with store.transaction() as conn:
        subject = store._subject(conn, "python-conditions")
        slug = store.graph(conn, "python-conditions").concepts[0].slug
        questions = [
            bundle
            for key in store.item_ids(conn, "python-conditions")
            if (bundle := store.servable(conn, key)) and bundle.item.concept == slug
        ]
    application = create_app(
        Settings(_env_file=None, database_url=database_url, allow_unauthenticated_local_dev=True),
        repository=store,
        gateway=FakeGateway(),
        confirmation=confirmed_graphs,
    )
    scores = {}
    with TestClient(application) as client:
        for question in questions:
            learner = client.post("/learners", json={"display_name": "BKT context fixture"}).json()[
                "learner_id"
            ]
            confirmed_graphs.confirm(store, learner, "python-conditions")
            with store.transaction() as conn:
                concept = conn.execute(
                    "select concept_id from items where id=%s", (question.db_id,)
                ).fetchone()
                assert concept is not None
                save_mastery(conn, UUID(learner), concept[0], 0.5)
                conn.execute(
                    "insert into p4_learning_sessions(learner_id,subject_id,phase,pending_item) "
                    "values(%s,%s,'review',%s)",
                    (learner, subject, question.db_id),
                )
            answer = next(i for i, option in enumerate(question.item.options) if option.correct)
            body = {
                "learner_id": learner,
                "item_id": question.item.id,
                "answer": answer,
                "client_attempt_id": str(uuid4()),
            }
            response = client.post("/attempts", json=body)
            assert response.status_code == 200, response.text
            result = response.json()
            params = bkt.mcq_params(
                question.item.difficulty, len(question.item.options), correct=True
            )
            expected = bkt.update(0.5, True, params)
            assert result["p_known"] == pytest.approx(expected)
            assert result["traces"][0]["evidence"]["guess"] == params.p_guess
            assert client.post("/attempts", json=body).json() == result
            scores[question.item.difficulty] = result["p_known"]
            with store.transaction() as conn:
                assert conn.execute(
                    "select p_known from mastery where learner_id=%s and concept_id=%s",
                    (learner, concept[0]),
                ).fetchone() == pytest.approx((expected,))
    assert 0.5 < scores[0.25] < scores[0.5] < scores[0.75] < 0.60
