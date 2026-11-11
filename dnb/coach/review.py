"""Post-game review: label each human move Good / Okay / Mistake vs. the bot's best move."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dnb.bots import Bot
from dnb.coach.hints import TIE_TOLERANCE, coach_bot, is_dangerous
from dnb.engine import GameState

Label = Literal["good", "okay", "mistake"]

# Thresholds are in boxes of margin (my boxes - their boxes), so they mean the same on every board
# size. Minimax margins are whole boxes: 0 is good, 1 is okay, and 2 or more is a mistake, which is
# the cost of one box going to the opponent instead of you. These need recalibrating if the review
# ever uses Monte Carlo, whose scores are win rates instead.
OKAY_MARGIN = 0.5
MISTAKE_MARGIN = 2.0


@dataclass
class MoveReview:
    ply: int  # index into the game's move list
    move: int
    best_move: int  # same as `move` when the played move ties for best
    score: float  # score of the played move, [-1, 1]
    best_score: float
    label: Label
    # Facts for the explanation, all read from the replay so the LLM has nothing to guess.
    rows: int
    cols: int
    boxes_taken: int  # boxes this move completed
    boxes_given_away: int  # boxes the opponent claimed on the turn right after this move
    left_three_sided: bool  # this move made a box 3-sided and ended the turn

    @property
    def gap(self) -> float:
        return self.best_score - self.score


def label_for(gap: float, num_boxes: int) -> Label:
    margin = round(gap * num_boxes, 9)  # rounded so that exactly one box's cost counts as a mistake
    if margin >= MISTAKE_MARGIN:
        return "mistake"
    return "okay" if margin >= OKAY_MARGIN else "good"


def _replay(rows: int, cols: int, moves: list[tuple[int, int]]) -> list[GameState]:
    """States[i] is the position before moves[i]; the last state is the final position."""
    states = [GameState.new(rows, cols)]
    for ply, (player, edge) in enumerate(moves):
        if player != states[-1].current_player:
            raise ValueError(f"move {ply} was played by player {player} out of turn")
        states.append(states[-1].apply(edge))
    return states


def _boxes_given_away(states: list[GameState], ply: int, human: int) -> int:
    after = states[ply + 1]
    opponent = 1 - human
    if after.current_player != opponent:
        return 0  # the move completed a box, so the human moves again
    end = ply + 1
    while end < len(states) - 1 and states[end].current_player == opponent:
        end += 1
    return states[end].scores[opponent] - after.scores[opponent]


def review_game(
    rows: int, cols: int, moves: list[tuple[int, int]], human: int, bot: Bot | None = None
) -> list[MoveReview]:
    """moves: (player, edge) in order. Reviews only the human's moves."""
    states = _replay(rows, cols, moves)
    reviews = []
    for ply, (player, move) in enumerate(moves):
        if player != human:
            continue
        state = states[ply]
        scores = (bot or coach_bot(state)).evaluate_moves(state)
        best_move = max(scores, key=scores.__getitem__)
        score, best_score = scores[move], scores[best_move]
        reviews.append(
            MoveReview(
                ply=ply,
                move=move,
                best_move=move if score >= best_score - TIE_TOLERANCE else best_move,
                score=score,
                best_score=best_score,
                label=label_for(best_score - score, state.layout.num_boxes),
                rows=rows,
                cols=cols,
                boxes_taken=state.boxes_completed_by(move),
                boxes_given_away=_boxes_given_away(states, ply, human),
                left_three_sided=is_dangerous(state, move),
            )
        )
    return reviews
