from app.engine.graph import UNSEEN_P_KNOWN, Graph
from app.engine.survey import DIFFICULTIES, Answer, next_question, rating, seed_mastery


def test_each_concept_receives_three_distinct_levels_without_inference() -> None:
    graph = Graph.from_edges(["a", "b"], [("a", "b")])
    answers: list[Answer] = []
    seen = []
    for _ in range(6):
        slug, difficulty, trace = next_question(graph, answers)
        assert slug is not None
        seen.append((slug, difficulty))
        answers.append(Answer(slug, True, difficulty))
        assert trace.rule.startswith("placement.survey.")
        if len(answers) == 3:
            assert seed_mastery(graph, answers)["b"] == UNSEEN_P_KNOWN
    assert seen == [(slug, difficulty) for slug in ("a", "b") for difficulty in DIFFICULTIES]
    assert next_question(graph, answers)[0] is None


def test_harder_correct_answers_have_more_weight_and_wrong_answers_keep_evidence() -> None:
    easy = [Answer("a", True, 0.25)]
    hard = [Answer("a", True, 0.75)]
    assert rating(hard) > rating(easy)
    graph = Graph.from_edges(["a"], [])
    all_correct = [Answer("a", True, value) for value in DIFFICULTIES]
    all_wrong = [Answer("a", False, value) for value in DIFFICULTIES]
    mixed = [Answer("a", value != 0.75, value) for value in DIFFICULTIES]
    assert (
        0.15
        <= seed_mastery(graph, all_wrong)["a"]
        < seed_mastery(graph, mixed)["a"]
        < seed_mastery(graph, all_correct)["a"]
        <= 0.85
    )


def test_old_questions_on_one_level_do_not_replace_other_levels() -> None:
    graph = Graph.from_edges(["a"], [])
    assert next_question(graph, [Answer("a", True, 0.5)])[1] == 0.25
