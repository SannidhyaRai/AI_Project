"""Greedy bot (owner: Person 1).

Takes a box whenever it can; otherwise avoids moves that leave a box with 3 sides
(giving the opponent a free box); otherwise plays randomly.
"""

from __future__ import annotations

import random

from dnb.bots.base import Bot, MoveResult
from dnb.engine import GameState


class GreedyBot(Bot):
    name = "greedy"

    def __init__(self, seed: int | None = None, randomness: float = 0.0) -> None:
        # `randomness` = chance of playing a random move instead (Person 3 uses it for Easy levels).
        if not 0.0 <= randomness <= 1.0:
            raise ValueError("randomness must be between 0 and 1")
        self.rng = random.Random(seed)
        self.randomness = randomness

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        """Local tactical scores, not a prediction of the final box margin.

        Capturing one/two boxes scores 0.5/1; safe moves score 0; giving away
        one/two three-sided boxes scores -0.5/-1. A capture keeps the turn,
        so creating another three-sided box on that move is not penalised.
        """
        scores = {}
        for move in state.legal_moves():
            captured = state.boxes_completed_by(move)
            danger = sum(state.sides(box) == 2 for box in state.layout.edge_boxes[move])
            scores[move] = captured / 2 if captured else -danger / 2
        return scores

    def choose_move(self, state: GameState) -> MoveResult:
        scores = self.evaluate_moves(state)
        if not scores:
            raise ValueError("cannot choose a move in a finished game")
        if self.randomness and self.rng.random() < self.randomness:
            move = self.rng.choice(list(scores))
        else:
            best = max(scores.values())
            move = self.rng.choice([move for move, score in scores.items() if score == best])
        return MoveResult(move=move, score=scores[move])
