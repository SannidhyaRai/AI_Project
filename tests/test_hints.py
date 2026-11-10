import json
import random
from pathlib import Path

import pytest

from dnb.bots import Bot
from dnb.coach.hints import dangerous_moves, hint, is_dangerous
from dnb.engine import GameState

FIXTURES = Path(__file__).parent / "fixtures"


def position(*edges: int, rows: int = 2, cols: int = 2) -> GameState:
    state = GameState.new(rows, cols)
    for edge in edges:
        state = state.apply(edge)
    return state


def load_fixture(name: str) -> tuple[GameState, dict]:
    data = json.loads((FIXTURES / name).read_text())
    state = position(*data["drawn"], rows=data["rows"], cols=data["cols"])
    assert state.current_player == data["current_player"]
    return state, data


class FixedScores(Bot):
    def __init__(self, scores: dict[int, float], default: float = 0.0) -> None:
        self.scores = scores
        self.default = default

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        return {m: self.scores.get(m, self.default) for m in state.legal_moves()}


def test_nothing_is_dangerous_on_an_empty_board():
    assert dangerous_moves(GameState.new(3, 3)) == []


def test_moves_that_make_a_box_three_sided_are_dangerous():
    state, data = load_fixture("danger_two_sided_box.json")
    assert dangerous_moves(state) == data["bad_moves"]


def test_completing_a_box_is_not_dangerous_even_if_it_makes_another_three_sided():
    state, data = load_fixture("danger_completing_move_is_safe.json")
    assert data["best_moves"] == [5]
    assert not is_dangerous(state, 5)
    assert dangerous_moves(state) == data["bad_moves"]


def test_every_remaining_move_can_be_dangerous():
    # All four boxes have 2 sides (the outer ring is half drawn), so nothing is safe.
    state = position(0, 1, 4, 5, 6, 8, 9, 11)
    assert all(state.sides(box) == 2 for box in range(4))
    assert dangerous_moves(state) == state.legal_moves()


def test_hint_returns_the_best_scored_move():
    state = GameState.new(2, 2)
    result = hint(state, bot=FixedScores({7: 0.5, 3: -0.5}))
    assert result.move == 7
    assert result.score == 0.5


def test_hint_breaks_ties_towards_a_safe_move():
    state, _ = load_fixture("danger_two_sided_box.json")
    # 2 and 7 are dangerous; 1 is safe and ties with them.
    bot = FixedScores({2: 0.5, 7: 0.5, 1: 0.5}, default=-1.0)
    assert {hint(state, bot=bot, rng=random.Random(s)).move for s in range(20)} == {1}


def test_hint_ties_are_not_always_the_lowest_edge():
    state = GameState.new(3, 3)
    moves = {hint(state, bot=FixedScores({}), rng=random.Random(s)).move for s in range(20)}
    assert len(moves) > 1


def test_hint_can_still_recommend_a_dangerous_move_that_scores_best():
    state, _ = load_fixture("danger_two_sided_box.json")
    assert hint(state, bot=FixedScores({7: 1.0})).move == 7


def test_default_hint_is_a_legal_move():
    state = GameState.new(2, 2)
    assert hint(state).move in state.legal_moves()


def test_hint_rejects_a_finished_game():
    state = position(0, 1, 2, rows=1, cols=1)
    state = state.apply(3)
    assert state.is_over()
    with pytest.raises(ValueError):
        hint(state)
