from datetime import UTC, datetime

import pytest

from app.engine import bkt
from app.engine.trace import DecisionTrace


def traced(
    prior: float,
    correct: bool,
    difficulty: float,
    *,
    option_count: int = 4,
    hints_used: int = 0,
    previous_attempts: int = 0,
) -> tuple[float, DecisionTrace]:
    return bkt.update_item_traced(
        prior,
        correct,
        difficulty=difficulty,
        option_count=option_count,
        concept_slug="concept",
        now=datetime(2026, 11, 8, tzinfo=UTC),
        hints_used=hints_used,
        previous_attempts=previous_attempts,
    )


@pytest.mark.parametrize("difficulty", [0, 0.25, 0.5, 0.75, 1])
def test_item_context_uses_the_existing_bkt_formula(difficulty: float) -> None:
    params = bkt.mcq_params(difficulty, 4, correct=True)
    result, trace = traced(0.5, True, difficulty)
    assert result == bkt.update(0.5, True, params)
    assert trace.evidence.guess == params.p_guess
    assert trace.evidence.slip == params.p_slip


@pytest.mark.parametrize("options", [2, 3, 4, 6])
@pytest.mark.parametrize("prior", [0.1, 0.2, 0.5, 0.8, 0.95])
def test_easy_correct_answers_add_less_evidence_than_hard_ones(options: int, prior: float) -> None:
    easy = traced(prior, True, 0.25, option_count=options)[0]
    hard = traced(prior, True, 0.75, option_count=options)[0]
    assert prior < easy < hard
    assert easy < bkt.update(prior, True, bkt.DEFAULT_PARAMS["mcq"])
    assert (
        traced(prior, False, 0.25, option_count=options)[0]
        < traced(prior, False, 0.75, option_count=options)[0]
        < prior
    )


def test_easy_questions_no_longer_turn_fifty_percent_into_eighty_percent() -> None:
    easy, _ = traced(0.5, True, 0.25)
    medium, _ = traced(0.5, True, 0.5)
    hard, _ = traced(0.5, True, 0.75)
    assert 0.5 < easy < 0.54
    assert easy < medium < hard < 0.60


@pytest.mark.parametrize("correct", [False, True])
def test_hints_reduce_the_strength_of_evidence(correct: bool) -> None:
    plain = traced(0.5, correct, 0.5)[0]
    assisted = traced(0.5, correct, 0.5, hints_used=2)[0]
    assert abs(assisted - 0.5) < abs(plain - 0.5)


def test_correct_repeated_questions_do_not_inflate_mastery() -> None:
    result, trace = traced(0.8, True, 0.75, previous_attempts=3)
    assert result == trace.prior == trace.posterior == 0.8
    assert trace.rule == "bkt.repeated_correct"


def test_fewer_options_mean_less_evidence_from_a_correct_answer() -> None:
    assert traced(0.5, True, 0.5, option_count=2)[0] < traced(0.5, True, 0.5, option_count=4)[0]


def test_wrong_answers_never_receive_an_automatic_learning_bonus() -> None:
    for prior in (0.001, 0.1, 0.5):
        for difficulty in (0, 0.25, 0.75, 1):
            params = bkt.mcq_params(difficulty, 4, correct=False)
            assert params.p_transit == 0
            assert traced(prior, False, difficulty)[0] < prior
