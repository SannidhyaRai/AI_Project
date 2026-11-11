"""Hint button + danger highlight."""

from __future__ import annotations

import random

from dnb.bots import Bot, MoveResult, make_bot
from dnb.engine import GameState

TIE_TOLERANCE = 1e-9

# Hints and reviews use minimax, the strongest bot until Person 2's arena says otherwise. Its depth
# is picked per position so a hint takes about a second at most: the fewer edges are left, the
# further it can look ahead. (legal moves left, depth), from timings on 2x2 to 7x7 boards.
SEARCH_DEPTHS = ((8, 8), (12, 6), (20, 5), (40, 4), (60, 3))
FALLBACK_DEPTH = 2
LARGE_BOARD_EDGES = 60  # bigger than 5x5: every search step costs more, so look one edge less
MIN_DEPTH = 2  # depth 1 can't see the opponent taking a box you gave away


def search_depth(state: GameState) -> int:
    left = len(state.legal_moves())
    depth = next((depth for limit, depth in SEARCH_DEPTHS if left <= limit), FALLBACK_DEPTH)
    if state.layout.num_edges > LARGE_BOARD_EDGES:
        depth -= 1
    return max(depth, MIN_DEPTH)


def coach_bot(state: GameState) -> Bot:
    """The bot that hints and reviews use for this position."""
    return make_bot(f"minimax:depth={search_depth(state)}")


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
    """Best move for the player to move, according to `coach_bot` unless a bot is given.

    Ties go to a safe move where there is one, picked at random. Otherwise early hints would
    always point at the lowest-numbered edge, because `Bot.choose_move` takes the first maximum.
    """
    if state.is_over():
        raise ValueError("the game is over, there is nothing to hint")
    scores = (bot or coach_bot(state)).evaluate_moves(state)
    best_score = max(scores.values())
    tied = [move for move, score in scores.items() if score >= best_score - TIE_TOLERANCE]
    safe = [move for move in tied if not is_dangerous(state, move)]
    move = (rng or random).choice(safe or tied)
    return MoveResult(move=move, score=scores[move])
