import json
import random
from functools import cache
from pathlib import Path

import pytest

from dnb.bots import make_bot
from dnb.bots.minimax import MinimaxBot
from dnb.engine import GameState


@cache
def reference_value(state, depth, player):
    """Unpruned minimax, deliberately independent of production ordering/cache."""
    if depth == 0 or state.is_over():
        return (state.scores[player] - state.scores[1 - player]) / state.layout.num_boxes
    values = [reference_value(state.apply(m), depth - 1, player) for m in state.legal_moves()]
    return (max if state.current_player == player else min)(values)


def expected_scores(state, depth):
    return {
        m: reference_value(state.apply(m), depth - 1, state.current_player)
        for m in state.legal_moves()
    }


def test_full_depth_scores_match_every_reachable_one_by_two_position():
    pending = [GameState.new(1, 2)]
    seen = set()
    while pending:
        state = pending.pop()
        if state in seen:
            continue
        seen.add(state)
        bot = MinimaxBot(depth=7)
        assert bot.evaluate_moves(state) == expected_scores(state, 7)
        pending.extend(state.apply(move) for move in state.legal_moves())


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_all_scores_match_unpruned_search_on_seeded_two_by_two_positions(depth):
    rng = random.Random(123)
    state = GameState.new(2, 2)
    bot = MinimaxBot(depth=depth)
    while not state.is_over():
        before = state
        scores = bot.evaluate_moves(state)
        assert scores == expected_scores(state, depth)
        assert state == before
        assert bot.choose_move(state).score == max(scores.values())
        state = state.apply(rng.choice(state.legal_moves()))


def test_extra_turn_can_capture_a_chain_instead_of_switching_to_minimizing():
    fixture = Path(__file__).parent / "fixtures" / "minimax_extra_turn_chain.json"
    data = json.loads(fixture.read_text())
    state = GameState.new(data["rows"], data["cols"])
    for edge in data["drawn"]:
        state = state.apply(edge)
    assert state.current_player == data["current_player"]
    assert state.apply(5).current_player == 1
    assert MinimaxBot(depth=2).evaluate_moves(state) == {5: 1.0, 6: -1.0}


def test_depth_one_counts_the_candidate_edge():
    state = GameState.new(1, 2)
    for edge in (0, 2, 4, 1, 3):
        state = state.apply(edge)
    assert MinimaxBot(depth=1).evaluate_moves(state) == {5: 0.5, 6: 0.0}


def test_ties_prefer_safe_edges_and_are_repeatable():
    state = GameState.new(1, 2).apply(0).apply(2)
    bot = MinimaxBot(depth=1)
    move = bot.choose_move(state).move
    assert move not in (4, 5)
    assert bot.choose_move(state).move == move


@pytest.mark.parametrize("depth", [0, -1, 1.5, True, "3"])
def test_invalid_depth(depth):
    with pytest.raises(ValueError):
        MinimaxBot(depth=depth)


def test_registry_and_finished_game():
    bot = make_bot("minimax:depth=4")
    assert bot.depth == 4
    state = GameState.new(1, 1)
    for move in range(4):
        state = state.apply(move)
    assert bot.evaluate_moves(state) == {}
    with pytest.raises(ValueError):
        bot.choose_move(state)


@pytest.mark.parametrize("size", [(1, 1), (1, 7), (7, 1), (3, 3), (4, 4), (7, 7)])
@pytest.mark.parametrize(
    "spec", ["random:seed=1", "greedy:seed=1", "greedy:seed=1,randomness=1", "minimax:depth=1"]
)
def test_full_games_preserve_bot_and_engine_contracts(size, spec):
    state = GameState.new(*size)
    bot = make_bot(spec)
    while not state.is_over():
        scores = bot.evaluate_moves(state)
        assert set(scores) == set(state.legal_moves())
        assert all(-1 <= score <= 1 for score in scores.values())
        state = state.apply(bot.choose_move(state).move)
    assert sum(state.scores) == size[0] * size[1]
