"""Course progression uses current graph mastery; classroom reports never grade students."""

import hashlib
import secrets
from collections import defaultdict
from typing import Any
from uuid import UUID

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from app.content.learning import graph_revision
from app.content.models import Graph
from app.content.repository import Repository
from app.engine.bkt import MASTERY_THRESHOLD
from app.engine.graph import WEAK_THRESHOLD
from app.jobs.queue import enqueue
from app.school.models import (
    ClassCreated,
    ClassSummary,
    Curriculum,
    CurriculumSummary,
    Dashboard,
    Lesson,
    LibraryLesson,
    NewClass,
    Outline,
    StudentProgress,
    WeakConcept,
)

Connection = psycopg.Connection[Any]


class School:
    def __init__(self, database_url: str, repository: Repository | None = None) -> None:
        self.database_url = database_url
        self.repository = repository

    def library(self) -> list[LibraryLesson]:
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(
                "select j.id,j.goal_vi,s.p4_graph from topic_jobs j "
                "join subjects s on s.slug=j.subject_slug where j.status='ready' and j.graph_ready "
                "and j.items_ready and not j.fixture and j.upload_id is null "
                "order by j.updated_at desc limit 50"
            ).fetchall()
            return [
                LibraryLesson(
                    topic_id=row[0],
                    goal=row[1],
                    concepts=[concept.name_vi for concept in Graph.model_validate(row[2]).concepts],
                )
                for row in rows
                if row[2]
            ]

    def link(self, course: UUID, lesson: UUID, learner: UUID, topic: UUID) -> None:
        with psycopg.connect(self.database_url) as conn:
            info = self._course(conn, course, learner)
            if info["owner_id"] != learner:
                raise HTTPException(403, "Chỉ người tạo khóa học được chọn học liệu cho bài.")
            conn.execute("select id from school_curricula where id=%s for update", (course,))
            current = conn.execute(
                "select j.status from school_lessons l left join topic_jobs j on j.id=l.topic_id "
                "where l.id=%s and l.curriculum_id=%s",
                (lesson, course),
            ).fetchone()
            if current is None:
                raise HTTPException(404, "Không tìm thấy bài học.")
            # Changing published content would invalidate an enrolled class's progress.
            if current[0] is not None and current[0] != "failed":
                raise HTTPException(409, "Chỉ được gán học liệu cho bài chưa tạo hoặc đã thất bại.")
            if conn.execute(
                "select 1 from school_lessons where curriculum_id=%s and topic_id=%s and id<>%s",
                (course, topic, lesson),
            ).fetchone():
                raise HTTPException(409, "Học liệu này đã được dùng cho một bài trong khóa học.")
            row = conn.execute(
                "select subject_slug from topic_jobs where id=%s and status='ready' "
                "and graph_ready and items_ready and not fixture and upload_id is null",
                (topic,),
            ).fetchone()
            if row is None or self.repository is None:
                raise HTTPException(
                    409, "Học liệu chưa sẵn sàng hoặc không thuộc thư viện web chung."
                )
            graph = self.repository.graph(conn, row[0])
            bundles = [
                self.repository.servable(conn, key)
                for key in self.repository.item_ids(conn, row[0])
            ]
            items = [item.item for item in bundles if item is not None]
            active = {concept.slug for concept in graph.concepts}
            items = [item for item in items if item.concept in active]
            if len(items) < 6 or not active <= {item.concept for item in items}:
                raise HTTPException(
                    409, "Học liệu không còn đủ câu hỏi đã kiểm chứng cho bản đồ hiện tại."
                )
            conn.execute("update school_lessons set topic_id=%s where id=%s", (topic, lesson))

    @staticmethod
    def _course(conn: Connection, course: UUID, learner: UUID) -> dict[str, Any]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select c.* from school_curricula c where c.id=%s and "
                "(c.owner_id=%s or exists(select 1 from school_classes cl "
                "join school_members m on m.class_id=cl.id "
                "where cl.curriculum_id=c.id and m.learner_id=%s))",
                (course, learner, learner),
            )
            row = cur.fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy khóa học trong tài khoản này.")
        return row

    @staticmethod
    def _lessons(conn: Connection, course: UUID) -> list[dict[str, Any]]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select l.*,j.status,j.step_vi,j.subject_slug,j.graph_ready,j.items_ready,"
                "j.goal_vi as material_goal,"
                "s.id as subject_id,s.p4_graph from school_lessons l "
                "left join topic_jobs j on j.id=l.topic_id "
                "left join subjects s on s.slug=j.subject_slug "
                "where l.curriculum_id=%s order by l.position",
                (course,),
            )
            rows = cur.fetchall()
        for row in rows:
            row["concepts"] = {}
            row["revision"] = None
            if row["status"] == "ready" and row["graph_ready"] and row["items_ready"]:
                if not row["p4_graph"]:
                    raise HTTPException(503, "Bản đồ hiện tại của bài học chưa đọc được.")
                graph = Graph.model_validate(row["p4_graph"])
                row["revision"] = graph_revision(graph)
                concepts = conn.execute(
                    "select id,slug,name_vi from concepts where subject_id=%s and slug=any(%s)",
                    (row["subject_id"], [c.slug for c in graph.concepts]),
                ).fetchall()
                if len(concepts) != len(graph.concepts):
                    raise HTTPException(503, "Các khái niệm hiện tại của bài học chưa đồng bộ.")
                row["concepts"] = {c[0]: {"slug": c[1], "name": c[2]} for c in concepts}
        return rows

    @staticmethod
    def _evidence(
        conn: Connection, lessons: list[dict[str, Any]], learners: list[UUID]
    ) -> dict[str, Any]:
        concept_ids = [cid for lesson in lessons for cid in lesson["concepts"]]
        subjects = [lesson["subject_id"] for lesson in lessons if lesson["concepts"]]
        mastery = {
            (lid, cid): float(p)
            for lid, cid, p in conn.execute(
                "select learner_id,concept_id,p_known from mastery "
                "where learner_id=any(%s) and concept_id=any(%s)",
                (learners, concept_ids),
            ).fetchall()
        }
        confirmations = dict(
            ((lid, sid), rev)
            for lid, sid, rev in conn.execute(
                "select learner_id,subject_id,graph_revision from learner_graph_confirmations "
                "where learner_id=any(%s) and subject_id=any(%s)",
                (learners, subjects),
            ).fetchall()
        )
        attempts = {
            (lid, sid): (count, correct, last)
            for lid, sid, count, correct, last in conn.execute(
                "select a.learner_id,c.subject_id,count(*),"
                "sum(a.is_correct::int),max(a.created_at) from attempts a "
                "join items i on i.id=a.item_id join concepts c on c.id=i.concept_id "
                "where a.learner_id=any(%s) and c.id=any(%s) group by a.learner_id,c.subject_id",
                (learners, concept_ids),
            ).fetchall()
        }
        return {"mastery": mastery, "confirmations": confirmations, "attempts": attempts}

    @staticmethod
    def _progress(
        rows: list[dict[str, Any]], learner: UUID, evidence: dict[str, Any]
    ) -> list[Lesson]:
        result = []
        unlocked = True
        for row in rows:
            values = [evidence["mastery"].get((learner, cid)) for cid in row["concepts"]]
            assessed = sum(p is not None for p in values)
            mastered = sum(p is not None and p >= MASTERY_THRESHOLD for p in values)
            confirmed = bool(row["revision"]) and (
                evidence["confirmations"].get((learner, row["subject_id"])) == row["revision"]
            )
            state = row["status"] or "not_started"
            if state == "ready":
                if not row["graph_ready"] or not row["items_ready"] or not values:
                    state = "failed"
                elif mastered == len(values) and confirmed:
                    state = "completed"
                elif assessed:
                    state = "learning"
            if not unlocked:
                state = "locked"
            result.append(
                Lesson(
                    id=row["id"],
                    position=row["position"],
                    module=row["module"],
                    title=row["title"],
                    goal=row["goal"],
                    state=state,
                    topic_id=row["topic_id"],
                    subject=row["subject_slug"],
                    step_vi=row["step_vi"] or "",
                    concepts=len(values),
                    assessed=assessed,
                    mastered=mastered,
                    confirmed=confirmed,
                    material_goal=row["material_goal"],
                )
            )
            unlocked = unlocked and state == "completed"
        return result

    def list_curricula(self, learner: UUID) -> list[CurriculumSummary]:
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(
                "select c.id,c.title,c.goal,count(l.id) from school_curricula c "
                "join school_lessons l on l.curriculum_id=c.id "
                "where c.owner_id=%s or exists(select 1 from school_classes cl "
                "join school_members m on m.class_id=cl.id where cl.curriculum_id=c.id "
                "and m.learner_id=%s) group by c.id order by c.created_at desc",
                (learner, learner),
            ).fetchall()
        return [CurriculumSummary(id=r[0], title=r[1], goal=r[2], lesson_count=r[3]) for r in rows]

    def create_curriculum(self, learner: UUID, outline: Outline) -> UUID:
        with psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "insert into school_curricula(owner_id,title,goal) values(%s,%s,%s) returning id",
                (learner, outline.title, outline.goal),
            ).fetchone()
            assert row
            for position, lesson in enumerate(outline.lessons, 1):
                conn.execute(
                    "insert into school_lessons(curriculum_id,position,module,title,goal) "
                    "values(%s,%s,%s,%s,%s)",
                    (row[0], position, lesson.module, lesson.title, lesson.goal),
                )
            return row[0]  # type: ignore[no-any-return]

    def curriculum(self, course: UUID, learner: UUID) -> Curriculum:
        with psycopg.connect(self.database_url) as conn:
            info = self._course(conn, course, learner)
            rows = self._lessons(conn, course)
            lessons = self._progress(rows, learner, self._evidence(conn, rows, [learner]))
            return Curriculum(
                id=course,
                title=info["title"],
                goal=info["goal"],
                completed=sum(entry.state == "completed" for entry in lessons),
                can_manage=info["owner_id"] == learner,
                lessons=lessons,
            )

    def start(self, course: UUID, lesson: UUID, learner: UUID, *, retry: bool = False) -> Lesson:
        with psycopg.connect(self.database_url) as conn:
            self._course(conn, course, learner)
            # Serialize all starts in a course; concurrent students share one lesson job.
            conn.execute("select id from school_curricula where id=%s for update", (course,))
            rows = self._lessons(conn, course)
            progress = self._progress(rows, learner, self._evidence(conn, rows, [learner]))
            target = next((entry for entry in progress if entry.id == lesson), None)
            if target is None:
                raise HTTPException(404, "Không tìm thấy bài học.")
            if target.state == "locked":
                raise HTTPException(409, "Hãy hoàn thành bài trước để mở bài tiếp theo.")
            if target.state == "failed" and not retry:
                raise HTTPException(409, "Bài học chưa tạo được. Xem lỗi trước khi chọn thử lại.")
            if target.topic_id is None or target.state == "failed":
                job = enqueue(conn, target.goal, "pro", mode="deep")
                conn.execute("update school_lessons set topic_id=%s where id=%s", (job, lesson))
                target = target.model_copy(update={"topic_id": job, "state": "queued"})
            return target

    def material(self, course: UUID, lesson: UUID, learner: UUID) -> dict[str, Any]:
        progress = self.curriculum(course, learner)
        target = next((entry for entry in progress.lessons if entry.id == lesson), None)
        if target is None:
            raise HTTPException(404, "Không tìm thấy bài học.")
        if target.state not in {"ready", "learning", "completed"}:
            raise HTTPException(409, "Bài học chưa mở hoặc chưa có nội dung đã kiểm chứng.")
        with psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "select p4_graph from subjects where slug=%s", (target.subject,)
            ).fetchone()
            assert row
            graph = Graph.model_validate(row[0])
            ids = list({cid for concept in graph.concepts for cid in concept.chunk_ids})
            chunks = conn.execute(
                "select c.id,c.content,c.page,c.source_uri,s.title,s.license "
                "from chunks c join sources s on s.id=c.source_id where c.id=any(%s) "
                "order by c.page nulls last,c.chunk_index",
                (ids,),
            ).fetchall()
            return {
                "graph": graph.team_payload(),
                "passages": [
                    {
                        "id": str(r[0]),
                        "text": r[1],
                        "page": r[2],
                        "url": r[3],
                        "title": r[4],
                        "license": r[5],
                    }
                    for r in chunks
                ],
            }

    def create_class(self, learner: UUID, value: NewClass) -> ClassCreated:
        with psycopg.connect(self.database_url) as conn:
            course = self._course(conn, value.curriculum_id, learner)
            if course["owner_id"] != learner:
                raise HTTPException(403, "Chỉ người tạo khóa học được mở lớp cho khóa học này.")
            invite = secrets.token_urlsafe(12)
            key = secrets.token_urlsafe(32)
            row = conn.execute(
                "insert into school_classes"
                "(owner_id,curriculum_id,name,invite_code,teacher_key_hash) "
                "values(%s,%s,%s,%s,%s) returning id",
                (
                    learner,
                    value.curriculum_id,
                    value.name,
                    invite,
                    hashlib.sha256(key.encode()).hexdigest(),
                ),
            ).fetchone()
            assert row
            return ClassCreated(
                id=row[0],
                name=value.name,
                curriculum_id=value.curriculum_id,
                curriculum_title=course["title"],
                role="teacher",
                invite_code=invite,
                teacher_key=key,
            )

    def list_classes(self, learner: UUID) -> list[ClassSummary]:
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(
                "select cl.id,cl.name,cl.curriculum_id,c.title,cl.owner_id=%s "
                "from school_classes cl join school_curricula c on c.id=cl.curriculum_id "
                "where cl.owner_id=%s or exists(select 1 from school_members m "
                "where m.class_id=cl.id and m.learner_id=%s) order by cl.created_at desc",
                (learner, learner, learner),
            ).fetchall()
            return [
                ClassSummary(
                    id=r[0],
                    name=r[1],
                    curriculum_id=r[2],
                    curriculum_title=r[3],
                    role="teacher" if r[4] else "student",
                )
                for r in rows
            ]

    def join(self, learner: UUID, invite: str) -> ClassSummary:
        with psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                "select cl.id,cl.name,cl.curriculum_id,c.title from school_classes cl "
                "join school_curricula c on c.id=cl.curriculum_id "
                "where cl.invite_code=%s for update of cl",
                (invite,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Mã mời không tồn tại.")
            exists = conn.execute(
                "select 1 from school_members where class_id=%s and learner_id=%s",
                (row[0], learner),
            ).fetchone()
            count = conn.execute(
                "select count(*) from school_members where class_id=%s", (row[0],)
            ).fetchone()
            assert count
            if not exists and count[0] >= 200:
                raise HTTPException(409, "Lớp đã đủ 200 học viên.")
            conn.execute(
                "insert into school_members(class_id,learner_id) values(%s,%s) "
                "on conflict do nothing",
                (row[0], learner),
            )
            return ClassSummary(
                id=row[0],
                name=row[1],
                curriculum_id=row[2],
                curriculum_title=row[3],
                role="student",
            )

    def dashboard(self, class_id: UUID, learner: UUID | None, key: str | None) -> Dashboard:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "select cl.*,c.title as curriculum_title from school_classes cl "
                    "join school_curricula c on c.id=cl.curriculum_id where cl.id=%s",
                    (class_id,),
                )
                info = cur.fetchone()
            permitted = info is not None and (
                info["owner_id"] == learner
                or (
                    key is not None
                    and len(key) == 43
                    and secrets.compare_digest(
                        hashlib.sha256(key.encode()).hexdigest(), info["teacher_key_hash"]
                    )
                )
            )
            if not permitted or info is None:
                raise HTTPException(404, "Không tìm thấy lớp hoặc quyền giảng viên không hợp lệ.")
            members = conn.execute(
                "select l.id,l.display_name from school_members m "
                "join learners l on l.id=m.learner_id "
                "where m.class_id=%s order by m.joined_at,l.id",
                (class_id,),
            ).fetchall()
            rows = self._lessons(conn, info["curriculum_id"])
            evidence = self._evidence(conn, rows, [r[0] for r in members])
            students = []
            concept_values: dict[UUID, list[float]] = defaultdict(list)
            for lid, name in members:
                lessons = self._progress(rows, lid, evidence)
                values = []
                counts = correct = 0
                activity = []
                for row in rows:
                    for cid in row["concepts"]:
                        p = evidence["mastery"].get((lid, cid))
                        if p is not None:
                            values.append(p)
                            concept_values[cid].append(p)
                    stats = evidence["attempts"].get((lid, row["subject_id"]))
                    if stats:
                        counts += stats[0]
                        correct += stats[1]
                        activity.append(stats[2])
                students.append(
                    StudentProgress(
                        learner_id=lid,
                        name=name,
                        completed=sum(entry.state == "completed" for entry in lessons),
                        lessons=len(rows),
                        assessed_concepts=len(values),
                        mean_mastery=sum(values) / len(values) if values else None,
                        attempts=counts,
                        correct_rate=correct / counts if counts else None,
                        last_active=max(activity) if activity else None,
                        lesson_states=[entry.state for entry in lessons],
                    )
                )
            concepts = []
            for row in rows:
                for cid, concept in row["concepts"].items():
                    values = concept_values[cid]
                    concepts.append(
                        WeakConcept(
                            lesson=row["title"],
                            name=concept["name"],
                            assessed=len(values),
                            weak=sum(p < WEAK_THRESHOLD for p in values),
                            unassessed=len(members) - len(values),
                            mean_mastery=sum(values) / len(values) if values else None,
                        )
                    )
            concepts.sort(
                key=lambda c: (-c.weak, c.mean_mastery if c.mean_mastery is not None else 1)
            )
            return Dashboard(
                id=class_id,
                name=info["name"],
                curriculum_id=info["curriculum_id"],
                curriculum_title=info["curriculum_title"],
                role="teacher",
                invite_code=info["invite_code"],
                total_lessons=len(rows),
                students=students,
                concepts=concepts,
            )
