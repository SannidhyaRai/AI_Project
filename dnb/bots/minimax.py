"""Minimax bot with alpha-beta pruning (owner: Person 1).

Careful: because of the extra-turn rule, the player to move does NOT simply alternate.
Decide max/min from `state.current_player`, never from depth parity.
"""

from __future__ import annotations

from dnb.bots.base import Bot
from dnb.engine import GameState


class MinimaxBot(Bot):
    name = "minimax"

    def __init__(self, depth: int = 3) -> None:
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
            raise ValueError("depth must be a positive integer")
        self.depth = depth

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        """Score every legal move with its own full alpha-beta window.

        Depth counts edges, including the candidate move and extra turns.
        Leaf values are the box margin / total boxes, from the ORIGINAL
        player's perspective. They are estimates unless the search ends the game.
        Full root windows ensure review receives values, not pruning bounds.
        """
        player = state.current_player
        total = state.layout.num_boxes
        # Only exact results are cached. Pruned nodes may return bounds.
        memo: dict[tuple[int, tuple[int, int], int, int], float] = {}

        def search(node: GameState, remaining: int, alpha: float, beta: float) -> float:
            if remaining == 0 or node.is_over():
                return (node.scores[player] - node.scores[1 - player]) / total
            key = (node.drawn, node.scores, node.current_player, remaining)
            if key in memo:
                return memo[key]
            low, high = alpha, beta
            maximizing = node.current_player == player
            value = float("-inf") if maximizing else float("inf")
            for move in self._ordered_moves(node):
                score = search(node.apply(move), remaining - 1, alpha, beta)
                if maximizing:
                    value = max(value, score)
                    alpha = max(alpha, value)
                else:
                    value = min(value, score)
                    beta = min(beta, value)
                if alpha >= beta:
                    break
            if low < value < high:
                memo[key] = value
            return value

        return {
            move: search(state.apply(move), self.depth - 1, float("-inf"), float("inf"))
            for move in self._ordered_moves(state)
        }

    @staticmethod
    def _ordered_moves(state: GameState) -> list[int]:
        """Captures, then safe edges, then sacrifices; edge index breaks ties.

        Ordering improves pruning and gives the inherited choose_move a sensible,
        deterministic tie break when shallow searches see equal margins.
        """

        def priority(move: int) -> tuple[int, int, int]:
            captured = state.boxes_completed_by(move)
            danger = sum(state.sides(box) == 2 for box in state.layout.edge_boxes[move])
            return (-captured, 0 if captured else danger, move)

        return sorted(state.legal_moves(), key=priority)
