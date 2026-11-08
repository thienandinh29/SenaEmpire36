"""First-answer evidence and a deterministic source-grounded review order."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.content.repository import Connection
from app.engine.graph import Graph


class Mistake(BaseModel):
    question: str
    chosen_answer: str
    misconception_vi: str | None


class ConceptAssessment(BaseModel):
    slug: str
    correct: int
    incorrect: int
    priority: Literal["gap", "foundation", "unassessed", "maintenance"]
    important: bool
    mistakes: list[Mistake]


class Assessment(BaseModel):
    answered: int
    correct: int
    incorrect: int
    concepts: list[ConceptAssessment]


def summarize(conn: Connection, learner: UUID, subject: UUID, graph: Graph) -> Assessment:
    rows = conn.execute(
        "select distinct on (a.item_id) c.slug,a.is_correct,"
        "coalesce(a.answer->>'question',i.prompt),"
        "coalesce(a.answer->>'chosen_answer',"
        "i.payload->'p4_item'->'options'->(a.answer->>'option_index')::int->>'label',''),"
        "m.description_vi from attempts a join items i on i.id=a.item_id "
        "join concepts c on c.id=i.concept_id "
        "left join misconceptions m on m.id=a.misconception_id "
        "where a.learner_id=%s and c.subject_id=%s order by a.item_id,a.created_at,a.id",
        (learner, subject),
    ).fetchall()
    wrong = {row[0] for row in rows if not row[1]}
    foundations = {p for slug in wrong for p in graph.ancestors(slug)}
    concepts = []
    for slug in graph.order:
        evidence = [row for row in rows if row[0] == slug]
        priority = (
            "gap"
            if slug in wrong
            else "foundation"
            if slug in foundations
            else "unassessed"
            if not evidence
            else "maintenance"
        )
        concepts.append(
            ConceptAssessment(
                slug=slug,
                correct=sum(bool(row[1]) for row in evidence),
                incorrect=sum(not row[1] for row in evidence),
                priority=priority,
                important=bool(graph.descendants(slug)) or not graph.parents[slug],
                mistakes=[
                    Mistake(question=row[2], chosen_answer=row[3], misconception_vi=row[4])
                    for row in evidence
                    if not row[1]
                ],
            )
        )
    order = {"gap": 0, "foundation": 1, "unassessed": 2, "maintenance": 3}
    concepts.sort(key=lambda c: (order[c.priority], not c.important, graph.depth[c.slug], c.slug))
    return Assessment(
        answered=len(rows),
        correct=sum(bool(row[1]) for row in rows),
        incorrect=sum(not row[1] for row in rows),
        concepts=concepts,
    )
