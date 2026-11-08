from uuid import uuid4

from app.engine.graph import Graph
from app.services.assessment import summarize


def test_errors_and_their_foundations_precede_unassessed_and_correct_material():
    graph = Graph.from_edges(["base", "gap", "correct", "unasked"], [("base", "gap")])

    class Connection:
        def execute(self, query, params):
            assert "distinct on (a.item_id)" in query
            assert "a.created_at,a.id" in query
            return self

        def fetchall(self):
            return [
                ("base", True, "Base question", "A", None),
                ("gap", False, "Gap question", "Wrong choice", "Possible misconception"),
                ("correct", True, "Correct question", "B", None),
            ]

    result = summarize(Connection(), uuid4(), uuid4(), graph)
    assert (result.answered, result.correct, result.incorrect) == (3, 2, 1)
    assert [c.priority for c in result.concepts] == [
        "gap",
        "foundation",
        "unassessed",
        "maintenance",
    ]
    assert result.concepts[0].mistakes[0].chosen_answer == "Wrong choice"
    assert result.concepts[1].correct == 1 and result.concepts[1].important
    assert result.concepts[2].correct == 0 and result.concepts[2].incorrect == 0
