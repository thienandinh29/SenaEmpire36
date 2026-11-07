"""Isolated PostgreSQL + HTTP acceptance; model/lesson publication are explicit fixtures."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.content.gateway import ModelReply
from app.content.learning import graph_revision
from app.content.repository import Repository
from app.db import create_pool
from app.school.main import create_school_app
from app.school.models import Outline
from app.school.service import School
from tests.content.fakes import FakeGateway, topic
from tests.content.test_runtime_database import database_url as database_url
from tests.content.test_runtime_database import store as store


def outline() -> dict[str, Any]:
    return {
        "title": "Khóa học Python",
        "goal": "Học Python từ nền tảng đến ứng dụng đơn giản",
        "lessons": [
            {
                "module": "Nền tảng",
                "title": "Điều kiện",
                "goal": "Python: hiểu biểu thức điều kiện và if",
            },
            {
                "module": "Ứng dụng",
                "title": "Vòng lặp",
                "goal": "Python: dùng vòng lặp for với danh sách",
            },
        ],
    }


class OutlineModels(FakeGateway):
    async def generate(self, **kwargs: Any) -> ModelReply:
        self.calls.append(kwargs)
        return ModelReply(content=outline(), identity=self.item.generator)


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    settings = Settings(database_url=database_url, api_key="school-test-key")
    with TestClient(
        create_school_app(settings, gateway=OutlineModels()),
        headers={"X-API-Key": "school-test-key"},
    ) as current:
        yield current


def learner(client: TestClient, name: str = "Giảng viên") -> str:
    response = client.post("/learners", json={"display_name": name})
    assert response.status_code == 200
    return str(response.json()["learner_id"])


def course(client: TestClient) -> dict[str, Any]:
    response = client.post("/school/curricula", json=outline())
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], client.get("/school/curricula/" + response.json()["id"]).json())


def publish_fixture(database_url: str, lesson: str) -> tuple[str, list[UUID], str]:
    """Fixture only: no real research, model quality or ready-state evidence is claimed."""
    sources, chunks, graph, _ = topic()
    replacements = {chunk.chunk_id: uuid4() for chunk in chunks}
    chunks = [
        chunk.model_copy(update={"chunk_id": replacements[chunk.chunk_id]}) for chunk in chunks
    ]
    concept = graph.concepts[0].model_copy(
        update={"chunk_ids": [replacements[cid] for cid in graph.concepts[0].chunk_ids]}
    )
    graph = graph.model_copy(update={"concepts": [concept], "edges": []})
    subject = "school-test-" + uuid4().hex
    with create_pool(database_url) as pool:
        repo = Repository(lambda: pool)
        repo.save_material(subject, sources, chunks)
        repo.save_graph(subject, graph)
    with psycopg.connect(database_url) as conn:
        job = conn.execute(
            "insert into topic_jobs(goal_vi,tier,status,subject_slug,graph_ready,items_ready) "
            "values('Test fixture','pro','ready',%s,true,true) returning id",
            (subject,),
        ).fetchone()
        assert job
        conn.execute("update school_lessons set topic_id=%s where id=%s", (job[0], lesson))
        ids = [
            r[0]
            for r in conn.execute(
                "select c.id from concepts c join subjects s on s.id=c.subject_id "
                "where s.slug=%s and c.slug=%s",
                (subject, concept.slug),
            ).fetchall()
        ]
    return subject, ids, graph_revision(graph)


def test_private_classes_and_unassessed_students(client: TestClient, database_url: str) -> None:
    teacher = learner(client)
    info = course(client)
    created = client.post(
        "/school/classes", json={"name": "Lớp A", "curriculum_id": info["id"]}
    ).json()
    assert created["role"] == "teacher"
    key = created["teacher_key"]
    class_path = "/school/classes/" + created["id"]
    client.cookies.clear()
    assert client.get(class_path).status_code == 404
    assert client.get(class_path, headers={"X-Class-Key": "x" * 43}).status_code == 404
    assert client.get(class_path, headers={"X-Class-Key": key}).status_code == 200
    learner(client, "Học viên mới")
    assert client.get("/school/curricula/" + info["id"]).status_code == 404
    for _ in range(2):
        assert (
            client.post(
                "/school/classes/join", json={"invite_code": created["invite_code"]}
            ).status_code
            == 200
        )
    assert client.get("/school/curricula/" + info["id"]).status_code == 200
    assert client.get(class_path).status_code == 404  # Membership never grants teacher access.
    dashboard = client.get(class_path, headers={"X-Class-Key": key}).json()
    assert len(dashboard["students"]) == 1
    student = dashboard["students"][0]
    assert student["mean_mastery"] is None and student["correct_rate"] is None
    assert student["attempts"] == 0 and student["completed"] == 0
    assert "teacher_key" not in dashboard
    assert (
        client.post(
            "/school/classes", json={"name": "Copied", "curriculum_id": info["id"]}
        ).status_code
        == 403
    )
    with psycopg.connect(database_url) as conn:
        stored = conn.execute(
            "select owner_id,teacher_key_hash from school_classes where id=%s", (created["id"],)
        ).fetchone()
        assert stored and str(stored[0]) == teacher and stored[1] != key


def test_mastery_confirmation_and_current_graph_control_progress(
    client: TestClient, database_url: str
) -> None:
    lid = learner(client)
    info = course(client)
    base = "/school/curricula/" + info["id"]
    first, second = info["lessons"]
    assert first["state"] == "not_started" and second["state"] == "locked"
    assert client.post(base + "/lessons/" + second["id"] + "/start", json={}).status_code == 409
    subject, concepts, revision = publish_fixture(database_url, first["id"])
    with psycopg.connect(database_url) as conn:
        for cid in concepts:
            conn.execute(
                "insert into mastery(learner_id,concept_id,p_known) values(%s,%s,.99)", (lid, cid)
            )
    assert client.get(base).json()["lessons"][0]["state"] != "completed"
    with psycopg.connect(database_url) as conn:
        row = conn.execute("select id from subjects where slug=%s", (subject,)).fetchone()
        assert row
        sid = row[0]
        conn.execute(
            "insert into learner_graph_confirmations(learner_id,subject_id,graph_revision) "
            "values(%s,%s,%s)",
            (lid, sid, revision),
        )
    progress = client.get(base).json()
    assert progress["completed"] == 1 and progress["lessons"][1]["state"] == "not_started"
    material = client.get(base + "/lessons/" + first["id"] + "/material")
    assert material.status_code == 200 and material.json()["passages"]
    with psycopg.connect(database_url) as conn:
        conn.execute("delete from learner_graph_confirmations where learner_id=%s", (lid,))
    assert client.get(base).json()["lessons"][1]["state"] == "locked"


def test_concurrent_start_and_explicit_retry_do_not_duplicate_jobs(
    client: TestClient, database_url: str
) -> None:
    lid = UUID(learner(client))
    info = course(client)
    course_id, lesson_id = UUID(info["id"]), UUID(info["lessons"][0]["id"])
    service = School(database_url)
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = list(
            executor.map(lambda _: service.start(course_id, lesson_id, lid).topic_id, range(2))
        )
    assert jobs[0] == jobs[1]
    with psycopg.connect(database_url) as conn:
        row = conn.execute("select goal_vi,mode from topic_jobs where id=%s", (jobs[0],)).fetchone()
        assert row == (outline()["lessons"][0]["goal"], "deep")
        conn.execute(
            "update topic_jobs set status='failed',step_vi='Source unavailable' where id=%s",
            (jobs[0],),
        )
    base = f"/school/curricula/{course_id}/lessons/{lesson_id}"
    assert client.get(base + "/material").status_code == 409
    assert client.post(base + "/start", json={}).status_code == 409
    new = client.post(base + "/start", json={"retry": True})
    assert new.status_code == 200 and new.json()["topic_id"] != str(jobs[0])


def test_weak_concepts_exclude_unassessed_and_other_classes(
    client: TestClient, database_url: str
) -> None:
    learner(client)
    info = course(client)
    created = client.post(
        "/school/classes", json={"name": "Scope", "curriculum_id": info["id"]}
    ).json()
    _, ids, _ = publish_fixture(database_url, info["lessons"][0]["id"])
    client.cookies.clear()
    lid = learner(client, "Needs support")
    client.post("/school/classes/join", json={"invite_code": created["invite_code"]})
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "insert into mastery(learner_id,concept_id,p_known) values(%s,%s,.3)", (lid, ids[0])
        )
    client.cookies.clear()
    learner(client, "Not assessed")
    client.post("/school/classes/join", json={"invite_code": created["invite_code"]})
    dashboard = client.get(
        "/school/classes/" + created["id"], headers={"X-Class-Key": created["teacher_key"]}
    ).json()
    assert dashboard["concepts"][0]["weak"] == 1
    assert dashboard["concepts"][0]["unassessed"] == 1
    assert dashboard["students"][1]["mean_mastery"] is None
    other = course(client)
    other_class = client.post(
        "/school/classes", json={"name": "Other", "curriculum_id": other["id"]}
    ).json()
    client.cookies.clear()
    assert (
        client.get(
            "/school/classes/" + other_class["id"], headers={"X-Class-Key": created["teacher_key"]}
        ).status_code
        == 404
    )


def test_ai_outline_requires_session_and_remains_a_plan(client: TestClient) -> None:
    payload = {"goal": "Học Python từ căn bản", "lesson_count": 2}
    assert client.post("/school/curricula/outline", json=payload).status_code == 401
    learner(client)
    planned = client.post("/school/curricula/outline", json=payload)
    assert planned.status_code == 200
    checked = Outline.model_validate(planned.json())
    assert len(checked.lessons) == 2 and checked.goal == payload["goal"]
    assert client.get("/school/curricula").json() == []


def test_teacher_can_assign_only_currently_verified_public_content(
    client: TestClient, database_url: str, store: Repository
) -> None:
    learner(client)
    info = course(client)
    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            "insert into topic_jobs(goal_vi,tier,status,subject_slug,graph_ready,items_ready) "
            "values('Controlled fixture','pro','ready','python-conditions',true,true) returning id"
        ).fetchone()
        assert row
        topic_id = str(row[0])
    library = client.get("/school/library")
    assert library.status_code == 200
    assert any(entry["topic_id"] == topic_id for entry in library.json())
    base = "/school/curricula/" + info["id"]
    path = base + "/lessons/" + info["lessons"][0]["id"] + "/link"
    assert client.post(path, json={"topic_id": topic_id}).status_code == 200
    updated = client.get(base).json()
    assert updated["lessons"][0]["state"] == "ready"
    assert updated["lessons"][0]["material_goal"] == "Controlled fixture"
    assert client.post(path, json={"topic_id": topic_id}).status_code == 409
    duplicate = base + "/lessons/" + info["lessons"][1]["id"] + "/link"
    assert client.post(duplicate, json={"topic_id": topic_id}).status_code == 409
    other = course(client)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "update items set status='needs_review' where external_id=any(%s)",
            (store.item_ids(conn, "python-conditions"),),
        )
    path = "/school/curricula/" + other["id"] + "/lessons/" + other["lessons"][0]["id"] + "/link"
    assert client.post(path, json={"topic_id": topic_id}).status_code == 409
