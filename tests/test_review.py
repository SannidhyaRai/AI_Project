import pytest

from dnb.bots import Bot
from dnb.coach.review import review_game
from dnb.engine import GameState


class FixedScores(Bot):
    def __init__(self, scores: dict[int, float], default: float = 0.0) -> None:
        self.scores = scores
        self.default = default

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        return {m: self.scores.get(m, self.default) for m in state.legal_moves()}


class PerfectBot(Bot):
    """Solves small boards exactly, on the same scale minimax uses: a real scorer for the tests."""

    def __init__(self) -> None:
        self.memo: dict[int, int] = {}

    def _future_margin(self, state: GameState) -> int:
        """Boxes the player to move can still win minus the opponent's, with perfect play."""
        if state.is_over():
            return 0
        if state.drawn not in self.memo:
            self.memo[state.drawn] = max(self._move_margin(state, m) for m in state.legal_moves())
        return self.memo[state.drawn]

    def _move_margin(self, state: GameState, move: int) -> int:
        after = state.apply(move)
        me = state.current_player
        future = self._future_margin(after)
        return (
            after.scores[me]
            - state.scores[me]
            + (future if after.current_player == me else -future)
        )

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        me = state.current_player
        margin = state.scores[me] - state.scores[1 - me]
        total = state.layout.num_boxes
        return {m: (margin + self._move_margin(state, m)) / total for m in state.legal_moves()}


@pytest.mark.parametrize(
    ("rows", "gap", "label"),
    [
        (3, 0.0, "good"),
        (3, 0.03, "good"),  # less than half a box of margin
        (3, 0.1, "okay"),
        (3, 2 / 9, "mistake"),  # exactly one box going to the opponent
        (3, 0.5, "mistake"),
        (5, 0.1, "mistake"),  # the same gap costs more boxes on a bigger board
    ],
)
def test_labels_depend_on_boxes_lost_not_the_raw_gap(rows, gap, label):
    bot = FixedScores({0: 0.5 - gap}, default=0.5)
    [review] = review_game(rows, rows, [(0, 0)], human=0, bot=bot)
    assert review.label == label
    assert review.gap == pytest.approx(gap)


def test_a_move_that_ties_for_best_is_its_own_best_move():
    [review] = review_game(3, 3, [(0, 5)], human=0, bot=FixedScores({}))
    assert review.best_move == 5


def test_a_worse_move_points_at_the_best_one():
    [review] = review_game(3, 3, [(0, 5)], human=0, bot=FixedScores({9: 1.0}))
    assert review.best_move == 9
    assert review.score == 0.0
    assert review.best_score == 1.0


def test_only_the_humans_moves_are_reviewed():
    moves = [(0, 0), (1, 2), (0, 1), (1, 3)]
    reviews = review_game(1, 2, moves, human=1, bot=FixedScores({}))
    assert [r.ply for r in reviews] == [1, 3]
    assert [r.move for r in reviews] == [2, 3]


def test_extra_turns_are_both_reviewed():
    # 1x2 board. Player 1 takes box 0 with edge 5, then box 1 with edge 6 straight after.
    moves = [(0, 0), (1, 2), (0, 4), (1, 1), (0, 3), (1, 5), (1, 6)]
    reviews = review_game(1, 2, moves, human=1, bot=PerfectBot())
    extra_turn = reviews[-2:]
    assert [r.ply for r in extra_turn] == [5, 6]
    assert [r.boxes_taken for r in extra_turn] == [1, 1]
    assert [r.boxes_given_away for r in extra_turn] == [0, 0]
    assert [r.label for r in extra_turn] == ["good", "good"]


def test_real_scorer_catches_a_blunder():
    # Edge 5 wins both boxes. Player 1 plays edge 6 instead and hands both to the opponent.
    moves = [(0, 0), (1, 2), (0, 4), (1, 1), (0, 3), (1, 6), (0, 5)]
    review = review_game(1, 2, moves, human=1, bot=PerfectBot())[-1]
    assert review.ply == 5
    assert review.move == 6
    assert review.best_move == 5
    assert review.score == -1.0
    assert review.best_score == 1.0
    assert review.label == "mistake"
    assert review.boxes_given_away == 2
    assert review.left_three_sided


def test_boxes_given_away_counts_the_opponents_whole_turn():
    # Player 0's edge 4 lets the opponent take box 0 and then box 1 as two separate moves.
    moves = [(0, 0), (1, 2), (0, 1), (1, 3), (0, 4), (1, 5), (1, 6)]
    review = review_game(1, 2, moves, human=0, bot=PerfectBot())[-1]
    assert review.ply == 4
    assert review.boxes_given_away == 2
    assert review.left_three_sided


def test_boxes_given_away_stops_when_the_turn_comes_back():
    # 2x2 board. The opponent takes box 0 with edge 7, then passes with edge 1.
    moves = [(0, 0), (1, 2), (0, 6), (1, 7), (1, 1), (0, 3)]
    review = review_game(2, 2, moves, human=0, bot=FixedScores({}))
    assert [r.ply for r in review] == [0, 2, 5]
    assert review[1].boxes_given_away == 1


def test_default_bot_reviews_a_full_game():
    moves = [(0, 0), (1, 1), (0, 2)]
    reviews = review_game(2, 2, moves, human=0)
    assert [r.label for r in reviews] == ["good", "good"]


def test_moves_played_out_of_turn_are_rejected():
    with pytest.raises(ValueError):
        review_game(2, 2, [(0, 0), (0, 1)], human=0, bot=FixedScores({}))
