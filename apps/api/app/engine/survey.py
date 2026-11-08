"""Three direct, difficulty-aware probes per curriculum concept.

Ratings are an Elo-style initial estimate, not an empirically calibrated item bank.
No correct or incorrect answer on one concept marks other concepts as assessed.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.engine.graph import UNSEEN_P_KNOWN, Graph
from app.engine.trace import DecisionTrace, Evidence, utc_now

DIFFICULTIES = (0.25, 0.5, 0.75)
LEVEL_NAMES = ("Dễ", "Vừa", "Khó")
INITIAL_RATING = 1200.0
K_FACTOR = 240.0


def level(difficulty: float) -> int:
    return 0 if difficulty < 0.375 else 1 if difficulty < 0.625 else 2


def item_rating(difficulty: float) -> float:
    return 400 + 1600 * difficulty


@dataclass(frozen=True)
class Answer:
    slug: str
    correct: bool
    difficulty: float
    item_id: str | None = None


def rating(answers: Sequence[Answer]) -> float:
    value = INITIAL_RATING
    for answer in answers:
        expected = 1 / (1 + 10 ** ((item_rating(answer.difficulty) - value) / 400))
        value += K_FACTOR * (float(answer.correct) - expected)
    return value


def seed_mastery(graph: Graph, answers: Sequence[Answer]) -> dict[str, float]:
    result = {}
    for slug in graph.order:
        direct = [answer for answer in answers if answer.slug == slug]
        result[slug] = (
            min(0.85, max(0.15, 1 / (1 + 10 ** ((1200 - rating(direct)) / 400))))
            if direct
            else UNSEEN_P_KNOWN
        )
    return result


def next_question(
    graph: Graph, answers: Sequence[Answer], *, now: datetime | None = None
) -> tuple[str | None, float, DecisionTrace]:
    if not graph.order:
        raise ValueError("cannot survey an empty graph")
    if any(answer.slug not in graph for answer in answers):
        raise ValueError("survey answer references an unknown concept")
    seen = {(answer.slug, level(answer.difficulty)) for answer in answers}
    for slug in graph.order:
        for index, difficulty in enumerate(DIFFICULTIES):
            if (slug, index) in seen:
                continue
            reason = (
                f"Khảo sát «{graph.name_vi(slug)}» · {LEVEL_NAMES[index]} "
                f"(Elo mục tiêu {round(item_rating(difficulty))}). "
                f"Mỗi kiến thức gồm 3 mức dễ, vừa, khó; đã khảo sát "
                f"{len(seen)}/{len(graph) * 3} câu. Elo là ước tính ban đầu."
            )
            return (
                slug,
                difficulty,
                DecisionTrace(
                    kind="placement_step",
                    concept_slug=slug,
                    at=now or utc_now(),
                    prior=seed_mastery(graph, answers)[slug],
                    evidence=Evidence(),
                    rule=f"placement.survey.level_{index}",
                    rule_vi=reason,
                ),
            )
    return (
        None,
        0.5,
        DecisionTrace(
            kind="placement_step",
            concept_slug=graph.order[-1],
            at=now or utc_now(),
            evidence=Evidence(),
            rule="placement.done.multilevel",
            rule_vi="Đã khảo sát trực tiếp cả 3 mức độ khó cho từng kiến thức trong tài liệu.",
        ),
    )
