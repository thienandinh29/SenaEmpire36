"""Real SQL persistence and HTTP wiring; synthetic content uses fake model audits."""

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg_pool import ConnectionPool

from app.config import Settings
from app.content.learning import graph_revision
from app.content.models import Graph
from app.content.repository import Repository
from app.db import create_pool
from app.guardrails.answerability import verify_item
from app.main import create_content_app
from app.migrate import apply_migrations
from app.services.graph_confirmation import GraphConfirmations
from tests.content.fakes import FakeGateway, topic

from .conftest import ADMIN_URL


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    name = "nodetrail_test_confirmation_" + uuid4().hex[:8]
    with psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
        url = ADMIN_URL.rsplit("/", 1)[0] + "/" + name
        try:
            apply_migrations(url)
            yield url
        finally:
            admin.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(name)))


@pytest.fixture
def material(database_url: str) -> Iterator[tuple[Repository, ConnectionPool, str, Graph]]:
    with create_pool(database_url) as pool:
        store = Repository(lambda: pool)
        with store.transaction() as conn:
            conn.execute("delete from subjects where slug='python-conditions'")
            learner = conn.execute(
                "insert into learners(display_name) values('Confirmation test') returning id"
            ).fetchone()
            assert learner
        sources, chunks, graph, _ = topic()
        store.save_material("python-conditions", sources, chunks)
        store.save_graph("python-conditions", graph)
        yield store, pool, str(learner[0]), graph


def test_confirmation_persists_and_is_scoped(
    database_url: str, material: tuple[Repository, ConnectionPool, str, Graph]
) -> None:
    store, _, learner, graph = material
    service = GraphConfirmations(database_url)
    service.require_schema()
    snapshot, revision = service.snapshot(learner, "python-conditions")
    assert snapshot == graph and revision == graph_revision(graph)
    assert not service(learner, "python-conditions", revision)
    service.confirm(learner, "python-conditions", revision)
    restarted = GraphConfirmations(database_url)
    assert restarted(learner, "python-conditions", revision)
    assert not restarted(str(uuid4()), "python-conditions", revision)
    assert not restarted(learner, "another-subject", revision)
    assert not restarted(learner, "python-conditions", "0" * 64)
    assert not restarted("invalid-uuid", "python-conditions", revision)
    with store.transaction() as conn:
        assert conn.execute(
            "select relrowsecurity from pg_class where oid='learner_graph_confirmations'::regclass"
        ).fetchone() == (True,)


def test_graph_change_and_reversion_require_new_acceptance(
    database_url: str, material: tuple[Repository, ConnectionPool, str, Graph]
) -> None:
    store, _, learner, graph = material
    service = GraphConfirmations(database_url)
    revision = graph_revision(graph)
    service.confirm(learner, "python-conditions", revision)
    store.save_graph("python-conditions", graph)
    assert service(learner, "python-conditions", revision)  # Unchanged replay is not a new graph.
    changed = graph.model_copy(
        update={
            "concepts": [
                graph.concepts[0].model_copy(update={"name_vi": "Tên đã sửa"}),
                *graph.concepts[1:],
            ]
        }
    )
    store.save_graph("python-conditions", changed)
    assert not service(learner, "python-conditions", revision)
    with pytest.raises(HTTPException) as stale:
        service.confirm(learner, "python-conditions", revision)
    assert stale.value.status_code == 409
    with store.transaction() as conn:
        assert conn.execute(
            "select count(*) from learner_graph_confirmations where learner_id=%s", (learner,)
        ).fetchone() == (0,)
    service.confirm(learner, "python-conditions", graph_revision(changed))
    store.save_graph("python-conditions", graph)
    assert not service(learner, "python-conditions", revision)
    assert not service(learner, "python-conditions", graph_revision(changed))


@pytest.mark.parametrize(
    "learner,subject,revision,expected",
    [
        ("bad-uuid", "python-conditions", "0" * 64, 422),
        (str(uuid4()), "python-conditions", "0" * 64, 404),
        (None, "missing-subject", "0" * 64, 404),
        (None, "python-conditions", "invalid-revision", 422),
    ],
)
def test_invalid_acceptance_writes_nothing(
    database_url: str,
    material: tuple[Repository, ConnectionPool, str, Graph],
    learner: str | None,
    subject: str,
    revision: str,
    expected: int,
) -> None:
    store, _, actual_learner, _ = material
    with pytest.raises(HTTPException) as failure:
        GraphConfirmations(database_url).confirm(learner or actual_learner, subject, revision)
    assert failure.value.status_code == expected
    with store.transaction() as conn:
        assert conn.execute(
            "select count(*) from learner_graph_confirmations where learner_id=%s",
            (actual_learner,),
        ).fetchone() == (0,)


def test_repeated_acceptance_is_one_row_and_callback_does_not_borrow_pool(
    database_url: str, material: tuple[Repository, ConnectionPool, str, Graph]
) -> None:
    store, pool, learner, graph = material
    revision = graph_revision(graph)
    service = GraphConfirmations(database_url)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(
            executor.map(
                lambda _: service.confirm(learner, "python-conditions", revision), range(4)
            )
        )
    with store.transaction() as conn:
        assert conn.execute(
            "select count(*) from learner_graph_confirmations where learner_id=%s", (learner,)
        ).fetchone() == (1,)
    with ExitStack() as stack:
        for _ in range(pool.max_size):
            stack.enter_context(pool.connection())
        assert service(learner, "python-conditions", revision)


def test_p2_factory_uses_durable_confirmation_without_bypassing_content_gate(
    database_url: str, material: tuple[Repository, ConnectionPool, str, Graph]
) -> None:
    store, _, learner, graph = material
    settings = Settings(
        _env_file=None, database_url=database_url, allow_unauthenticated_local_dev=True
    )
    app = create_content_app(settings, repository=store, gateway=FakeGateway())
    request = {"learner_id": learner, "subject": "python-conditions"}
    with TestClient(app) as client:
        assert client.get("/graph", params=request).status_code == 200
        assert client.post("/placement/next", json=request).status_code == 409
        # Simulate an authenticated boundary recording the learner's explicit action.
        app.state.graph_confirmations.confirm(learner, "python-conditions", graph_revision(graph))
        assert client.post("/placement/next", json=request).status_code == 503
        _, chunks, _, items = topic()
        checked = []
        for index, item in enumerate(items):
            item = item.model_copy(update={"difficulty": (0.25, 0.5, 0.75)[index % 3]})
            gateway = FakeGateway()
            gateway.item = item
            gateway.chunks = [chunk for chunk in chunks if chunk.chunk_id in item.chunk_ids]
            checked.append(asyncio.run(verify_item(item, chunks, gateway)))
        store.save_items("python-conditions", checked)
        response = client.post("/placement/next", json=request)
        assert response.status_code == 200, response.text
        assert set(response.json()["item"]) == {"id", "kind", "prompt_vi", "options"}
    restarted = create_content_app(settings, repository=store, gateway=FakeGateway())
    with TestClient(restarted) as client:
        assert client.post("/placement/next", json=request).status_code == 200
