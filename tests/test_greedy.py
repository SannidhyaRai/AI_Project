import pytest

from dnb.bots import make_bot
from dnb.bots.greedy import GreedyBot
from dnb.engine import GameState


def position(*edges, rows=1, cols=2):
    state = GameState.new(rows, cols)
    for edge in edges:
        state = state.apply(edge)
    return state


def test_capture_is_preferred_even_when_it_creates_another_three_sided_box():
    state = position(0, 2, 4, 1)
    bot = GreedyBot(seed=0)
    assert bot.choose_move(state).move == 5
    assert bot.evaluate_moves(state)[5] == 0.5
    assert state.apply(5).current_player == state.current_player


def test_double_capture_scores_higher_than_a_single_capture():
    # First two boxes share edge 7; third box can be captured with edge 9.
    state = position(0, 1, 2, 3, 4, 5, 6, 8, rows=1, cols=3)
    scores = GreedyBot().evaluate_moves(state)
    assert scores[7] == 1.0
    assert scores[9] == 0.5
    assert GreedyBot().choose_move(state).move == 7


def test_avoids_giving_away_a_box_when_a_safe_move_exists():
    state = position(0, 2)
    scores = GreedyBot().evaluate_moves(state)
    assert scores[4] == scores[5] == -0.5
    assert scores[1] == 0
    assert all(GreedyBot(seed=s).choose_move(state).move not in (4, 5) for s in range(20))


def test_two_box_sacrifice_is_worse_than_one():
    state = position(0, 1, 2, 3)
    scores = GreedyBot().evaluate_moves(state)
    assert scores[5] == -1.0
    assert scores[4] == scores[6] == -0.5


def test_randomness_one_samples_all_legal_moves_including_mistakes():
    state = position(0, 2, 4)
    bot = GreedyBot(seed=23, randomness=1)
    results = [bot.choose_move(state) for _ in range(100)]
    assert {result.move for result in results} == set(state.legal_moves())
    assert all(result.score == bot.evaluate_moves(state)[result.move] for result in results)


def test_intermediate_randomness_usually_captures_but_sometimes_makes_mistakes():
    state = position(0, 2, 4)
    bot = GreedyBot(seed=37, randomness=0.3)
    # One capture among four legal edges: P(capture) = 0.7 + 0.3/4 = 0.775.
    capture_rate = sum(bot.choose_move(state).move == 5 for _ in range(2000)) / 2000
    assert 0.74 < capture_rate < 0.81


def test_scoring_does_not_consume_randomness_or_change_the_position():
    state = GameState.new()
    first = GreedyBot(seed=5)
    second = GreedyBot(seed=5)
    assert first.evaluate_moves(state) == first.evaluate_moves(state)
    assert [first.choose_move(state) for _ in range(20)] == [
        second.choose_move(state) for _ in range(20)
    ]
    assert state == GameState.new()


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_randomness(value):
    with pytest.raises(ValueError):
        GreedyBot(randomness=value)


def test_registry_options_and_finished_game():
    bot = make_bot("greedy:seed=7,randomness=0.3")
    assert isinstance(bot, GreedyBot)
    assert bot.randomness == 0.3
    state = position(0, 1, 2, 3, rows=1, cols=1)
    assert bot.evaluate_moves(state) == {}
    with pytest.raises(ValueError):
        bot.choose_move(state)
