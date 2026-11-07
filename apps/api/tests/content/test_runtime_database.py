"""Actual PostgreSQL adapter/trigger tests. --no-db skips these explicitly.

Model responses here are fake fixtures and never establish real content quality.
"""

import asyncio
import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.config import Settings
from app.content.demo import install_schema, local_only
from app.content.repository import Repository
from app.content.runtime import create_app
from app.db import create_pool
from app.guardrails.answerability import verify_item
from tests.content.fakes import FakeGateway, topic


@pytest.fixture
def store(database_url: str) -> Iterator[Repository]:
    with psycopg.connect(database_url) as conn:
        conn.execute("delete from subjects where slug='python-conditions'")
    with create_pool(database_url) as pool:
        repo = Repository(lambda: pool)
        sources, chunks, graph, items = topic()
        repo.save_material("python-conditions", sources, chunks)
        repo.save_graph("python-conditions", graph)
        checked = []
        for item in items:
            fake = FakeGateway()
            fake.item = item
            fake.chunks = [c for c in chunks if c.chunk_id in item.chunk_ids]
            checked.append(asyncio.run(verify_item(item, chunks, fake)))
        repo.save_items("python-conditions", checked)
        yield repo


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    # This module never alters the base suite's migrated database.
    admin_url = os.environ.get(
        "TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    local_only(admin_url, admin=True)
    name = "nodetrail_test_p4_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=2) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
        url = admin_url.rsplit("/", 1)[0] + "/" + name
        try:
            install_schema(url)
            yield url
        finally:
            admin.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(name)))


def test_repository_preserves_ids_and_retry_does_not_duplicate(store: Repository) -> None:
    with store.transaction() as conn:
        ids = store.item_ids(conn, "python-conditions")
        bundles = [store.current(conn, key) for key in ids]
        assert all(b is not None for b in bundles)
    store.save_items("python-conditions", [b.item for b in bundles if b])
    with store.transaction() as conn:
        assert store.item_ids(conn, "python-conditions") == ids
        assert conn.execute(
            "select count(*) from items where external_id=any(%s)", (ids,)
        ).fetchone() == (15,)
        _, chunks, _, _ = topic()
        actual = {
            r[0]
            for r in conn.execute(
                "select id from chunks where id=any(%s)", ([c.chunk_id for c in chunks],)
            )
        }
        assert actual == {c.chunk_id for c in chunks}


@pytest.mark.parametrize(
    "mutation",
    [
        "option_label",
        "option_key",
        "option_insert",
        "option_delete",
        "chunk_text",
        "chunk_relation",
        "concept_citation",
        "prompt",
    ],
)
def test_content_edits_atomically_invalidate_items_and_hint_cache(
    store: Repository, mutation: str
) -> None:
    from psycopg.types.json import Jsonb

    with store.transaction() as conn:
        bundle = store.current(conn, "python-conditions-001")
        assert bundle
        learner = uuid4()
        conn.execute("insert into learners(id,display_name) values(%s,'Test')", (learner,))
        conn.execute(
            "insert into p4_hint_cache(item_id,learner_id,cache_key,item_hash,level,attempt) "
            "values(%s,%s,%s,%s,1,%s)",
            (bundle.db_id, learner, str(learner), bundle.fingerprint, Jsonb({"fixture": True})),
        )
        if mutation == "option_label":
            conn.execute(
                "update item_options set label=label||' sửa' where item_id=%s", (bundle.db_id,)
            )
        elif mutation == "option_key":
            conn.execute(
                "update item_options set is_correct=not is_correct,misconception_id=null "
                "where item_id=%s",
                (bundle.db_id,),
            )
        elif mutation == "option_insert":
            conn.execute(
                "insert into item_options(item_id,label,is_correct,position) "
                "values(%s,'Mới',false,99)",
                (bundle.db_id,),
            )
        elif mutation == "option_delete":
            conn.execute(
                "delete from item_options where item_id=%s and position=0", (bundle.db_id,)
            )
        elif mutation == "chunk_text":
            conn.execute(
                "update chunks set content=content||' sửa' where id=%s", (bundle.item.chunk_ids[0],)
            )
        elif mutation == "chunk_relation":
            conn.execute("update items set chunk_ids=%s where id=%s", ([], bundle.db_id))
        elif mutation == "concept_citation":
            conn.execute(
                "delete from concept_sources where concept_id=(select concept"
                "_id from items where id=%s)",
                (bundle.db_id,),
            )
        else:
            conn.execute("update items set prompt=prompt||' sửa' where id=%s", (bundle.db_id,))
        assert conn.execute("select status from items where id=%s", (bundle.db_id,)).fetchone() == (
            "needs_review",
        )
        assert conn.execute(
            "select invalidated_at is not null from p4_hint_cache where item_id=%s", (bundle.db_id,)
        ).fetchone() == (True,)
        assert conn.execute(
            "select count(*)>0 from p4_verification_history where item_id"
            "=%s and kind='invalidation'",
            (bundle.db_id,),
        ).fetchone() == (True,)
    with store.transaction() as conn:
        assert store.current(conn, bundle.item.id) is None


def test_http_learning_and_verified_hint_use_real_repository_with_fake_models(
    store: Repository, database_url: str
) -> None:
    fake = FakeGateway()
    app = create_app(
        Settings(database_url=database_url, _env_file=None), repository=store, gateway=fake
    )
    with TestClient(app) as client:
        learner = client.post("/learners", json={"display_name": "P4 DB test"}).json()["learner_id"]
        placement = client.post(
            "/placement/next", json={"learner_id": learner, "subject": "python-conditions"}
        )
        assert placement.status_code == 200
        public = placement.json()["item"]
        assert set(public) == {"id", "kind", "prompt_vi", "options"}
        with store.transaction() as conn:
            bundle = store.current(conn, public["id"])
            assert bundle
        fake.item = bundle.item
        fake.chunks = bundle.chunks
        wrong = next(i for i, o in enumerate(bundle.item.options) if not o.correct)
        attempt = client.post(
            "/attempts",
            json={"learner_id": learner, "item_id": public["id"], "answer": wrong, "hints_used": 0},
        )
        assert attempt.status_code == 200 and attempt.json()["correct"] is False
        assert attempt.json()["traces"]
        hint = client.post(
            "/tutor/hint",
            json={"learner_id": learner, "item_id": public["id"], "level": 1, "tier": "free"},
        )
        assert hint.status_code == 200 and hint.json()["citations"]
        assert set(hint.json()) == {"hint_vi", "citations"}
        fake.overrides = {"no_answer_leak": False}
        denied = client.post(
            "/tutor/hint",
            json={"learner_id": learner, "item_id": public["id"], "level": 2, "tier": "free"},
        )
        assert denied.status_code == 503
