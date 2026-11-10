"""Hint button + danger highlight."""

from __future__ import annotations

import random

from dnb.bots import Bot, MoveResult, make_bot
from dnb.engine import GameState

HINT_BOT = "random"  # TODO(P4): switch to the strongest bot once the arena says which one it is
TIE_TOLERANCE = 1e-9


def is_dangerous(state: GameState, move: int) -> bool:
    """True if `move` makes a box 3-sided and ends the turn, handing the opponent a free box.

    A move that also completes a box is not dangerous: the same player moves again and can take
    the 3-sided box themselves. Dangerous is not the same as wrong, since sacrificing boxes is
    sometimes the best play.
    """
    if state.boxes_completed_by(move):
        return False
    return any(state.sides(box) == 2 for box in state.layout.edge_boxes[move])


def dangerous_moves(state: GameState) -> list[int]:
    """Legal moves that would leave a box with 3 sides (a free box for the opponent)."""
    return [move for move in state.legal_moves() if is_dangerous(state, move)]


def hint(state: GameState, bot: Bot | None = None, rng: random.Random | None = None) -> MoveResult:
    """Best move for the player to move, according to HINT_BOT.

    Ties go to a safe move where there is one, picked at random. Otherwise early hints would
    always point at the lowest-numbered edge, because `Bot.choose_move` takes the first maximum.
    """
    if state.is_over():
        raise ValueError("the game is over, there is nothing to hint")
    scores = (bot or make_bot(HINT_BOT)).evaluate_moves(state)
    best_score = max(scores.values())
    tied = [move for move, score in scores.items() if score >= best_score - TIE_TOLERANCE]
    safe = [move for move in tied if not is_dangerous(state, move)]
    move = (rng or random).choice(safe or tied)
    return MoveResult(move=move, score=scores[move])
