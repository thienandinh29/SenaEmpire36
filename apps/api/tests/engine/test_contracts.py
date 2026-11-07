"""Contract shapes (app/schemas.py, app/engine/trace.py) match TEAM.md and reject bad fixtures."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.engine.trace import Alternative, DecisionTrace, Evidence
from app.schemas import (
    AttemptCreate,
    GraphView,
    ItemSet,
    KnowledgeGraph,
    PlacementStep,
    PublicItem,
    TopicCreate,
)


def test_duplicate_item_ids_rejected() -> None:
    data = deepcopy(ITEMS)
    data["items"].append(deepcopy(data["items"][0]))
    with pytest.raises(ValidationError, match="item ids must be unique"):
        ItemSet.model_validate(data)


def test_distinct_item_ids_still_load() -> None:
    data = deepcopy(ITEMS)
    second = deepcopy(data["items"][0])
    second["id"] = "plr-002"
    data["items"].append(second)
    assert len(ItemSet.model_validate(data).items) == 2


GRAPH: dict[str, Any] = {
    "concepts": [
        {
            "slug": "cell-structure",
            "name_vi": "Cấu trúc tế bào",
            "name_en": "Cell structure",
            "sources": ["https://openstax.org/books/biology-2e/pages/4-1"],
        },
        {
            "slug": "photosynthesis-light-reactions",
            "name_vi": "Pha sáng của quang hợp",
            "name_en": "Light reactions",
            "description_vi": "...",
            "sources": ["https://openstax.org/books/biology-2e/pages/8-2"],
        },
    ],
    "edges": [{"from": "cell-structure", "to": "photosynthesis-light-reactions"}],
}

ITEMS: dict[str, Any] = {
    "concept": "photosynthesis-light-reactions",
    "misconceptions": [
        {"slug": "oxygen-from-co2", "description_vi": "Nghĩ rằng O2 sinh ra từ CO2"}
    ],
    "items": [
        {
            "id": "plr-001",
            "kind": "mcq",
            "prompt_vi": "Oxy sinh ra trong quang hợp có nguồn gốc từ đâu?",
            "difficulty": 0.4,
            "source": "https://openstax.org/books/biology-2e/pages/8-2",
            "chunk_ids": ["7f3c", "a91e"],
            "status": "verified",
            "options": [
                {"label": "Từ nước (H2O)", "correct": True},
                {"label": "Từ CO2", "correct": False, "misconception": "oxygen-from-co2"},
            ],
        }
    ],
}


def _graph(**changes: Any) -> dict[str, Any]:
    return {**GRAPH, **changes}


def test_team_md_graph_example_loads_and_round_trips_from() -> None:
    graph = KnowledgeGraph.model_validate(GRAPH)
    assert graph.edges[0].from_ == "cell-structure"
    assert graph.model_dump()["edges"][0] == {
        "from": "cell-structure",
        "to": "photosynthesis-light-reactions",
    }


def test_graph_rejects_cycles() -> None:
    edges = [*GRAPH["edges"], {"from": "photosynthesis-light-reactions", "to": "cell-structure"}]
    with pytest.raises(ValidationError, match="cycle"):
        KnowledgeGraph.model_validate(_graph(edges=edges))


@pytest.mark.parametrize(
    "edges",
    [
        [{"from": "cell-structure", "to": "missing"}],
        [{"from": "cell-structure", "to": "cell-structure"}],
        [GRAPH["edges"][0], GRAPH["edges"][0]],
    ],
)
def test_graph_rejects_bad_edges(edges: list[dict[str, str]]) -> None:
    with pytest.raises(ValidationError):
        KnowledgeGraph.model_validate(_graph(edges=edges))


def test_graph_rejects_non_kebab_slugs_and_unknown_keys() -> None:
    bad_slug = [{**GRAPH["concepts"][0], "slug": "Cell_Structure"}]
    with pytest.raises(ValidationError):
        KnowledgeGraph.model_validate(_graph(concepts=bad_slug, edges=[]))
    with pytest.raises(ValidationError):
        KnowledgeGraph.model_validate(_graph(extra_key=1))


def test_team_md_items_example_loads() -> None:
    items = ItemSet.model_validate(ITEMS)
    assert items.items[0].status == "verified"


def _item_with_options(options: list[dict[str, Any]]) -> dict[str, Any]:
    return {**ITEMS, "items": [{**ITEMS["items"][0], "options": options}]}


@pytest.mark.parametrize(
    "options",
    [
        [{"label": "A", "correct": True}, {"label": "B", "correct": False}],  # no misconception
        [{"label": "A", "correct": True}, {"label": "B", "correct": True}],  # two correct
        [
            {"label": "A", "correct": True},
            {"label": "B", "correct": False, "misconception": "not-defined"},
        ],
    ],
)
def test_items_reject_bad_options(options: list[dict[str, Any]]) -> None:
    with pytest.raises(ValidationError):
        ItemSet.model_validate(_item_with_options(options))


def test_items_default_to_needs_review() -> None:
    raw = {k: v for k, v in ITEMS["items"][0].items() if k != "status"}
    items = ItemSet.model_validate({**ITEMS, "items": [raw]})
    assert items.items[0].status == "needs_review"


def test_public_item_cannot_carry_the_answer() -> None:
    with pytest.raises(ValidationError):
        PublicItem.model_validate(
            {
                "id": "plr-001",
                "kind": "mcq",
                "prompt_vi": "?",
                "options": [{"label": "A", "correct": True}],
            }
        )


def test_topic_needs_goal_or_upload() -> None:
    with pytest.raises(ValidationError):
        TopicCreate.model_validate({"mode": "quick", "tier": "free"})
    TopicCreate.model_validate({"goal_vi": "Tôi muốn học Python", "mode": "deep", "tier": "pro"})


def test_attempt_answer_is_an_option_index() -> None:
    assert (
        AttemptCreate.model_validate({"learner_id": "l", "item_id": "i", "answer": 1}).answer == 1
    )
    with pytest.raises(ValidationError):
        AttemptCreate.model_validate({"learner_id": "l", "item_id": "i", "answer": -1})


def _trace() -> DecisionTrace:
    return DecisionTrace(
        kind="root_cause",
        concept_slug="boolean-expressions",
        at=datetime(2026, 11, 7, 9, 0, tzinfo=UTC),
        prior=0.31,
        evidence=Evidence(item_id="loop-003", correct=False, misconception="off-by-one"),
        posterior=0.31,
        rule="root_cause.lowest_p_known",
        rule_vi="Sai ở vòng lặp → kiểm tra nền tảng biểu thức boolean (p_known thấp nhất 0,31)",
        alternatives=[
            Alternative(
                concept_slug="variables",
                p_known=0.82,
                why_not_vi="Đã nắm khá vững (0,82)",
            )
        ],
    )


def test_decision_trace_has_the_team_md_fields() -> None:
    dumped = _trace().model_dump(mode="json")
    assert set(dumped) == {
        "kind",
        "concept_slug",
        "at",
        "prior",
        "evidence",
        "posterior",
        "rule",
        "rule_vi",
        "alternatives",
    }
    assert set(dumped["evidence"]) == {"item_id", "correct", "misconception", "slip", "guess"}
    assert set(dumped["alternatives"][0]) == {"concept_slug", "p_known", "why_not_vi"}
    assert DecisionTrace.model_validate(dumped) == _trace()


def test_decision_trace_rejects_out_of_range_probabilities() -> None:
    with pytest.raises(ValidationError):
        DecisionTrace.model_validate({**_trace().model_dump(), "prior": 1.2})


def test_api_responses_embed_trace_and_graph() -> None:
    step = PlacementStep(item=None, done=True, gap_slug="boolean-expressions", trace=_trace())
    assert PlacementStep.model_validate(step.model_dump(mode="json")) == step
    view = GraphView.model_validate(
        {
            "nodes": [
                {"slug": "a", "name_vi": "A", "p_known": 0.2, "mastered": False},
                {"slug": "b", "name_vi": "B", "p_known": 0.96, "mastered": True},
            ],
            "edges": [{"from": "a", "to": "b"}],
        }
    )
    assert view.model_dump(mode="json")["edges"] == [{"from": "a", "to": "b"}]
