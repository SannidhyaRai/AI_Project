"""API request/response shapes. CONTRACT: web/src/api.ts mirrors these; change both together."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NewGameRequest(BaseModel):
    rows: int = Field(3, ge=1, le=7)
    cols: int = Field(3, ge=1, le=7)
    bot: str = "random"  # bot spec, see dnb/bots/registry.py
    level: int | None = None  # TODO(P3/P5): when set, pick the bot from dnb.difficulty.levels
    human_first: bool = True
    player_id: str = "guest"


class MoveRequest(BaseModel):
    edge: int


class PlayedMove(BaseModel):
    player: int
    edge: int


class GameOut(BaseModel):
    id: str
    rows: int
    cols: int
    bot: str
    human_player: int
    current_player: int
    moves: list[PlayedMove]
    box_owners: list[int]  # -1 = unclaimed
    scores: list[int]
    is_over: bool
    winner: int | None


class HintOut(BaseModel):
    move: int
    score: float  # [-1, 1], higher is better for the player to move


class DangerOut(BaseModel):
    edges: list[int]  # legal moves that would leave a box with 3 sides


class MoveReviewOut(BaseModel):
    ply: int  # index into GameOut.moves
    move: int
    best_move: int  # same as move when the played move ties for best
    score: float
    best_score: float
    label: Literal["good", "okay", "mistake"]
    boxes_taken: int
    boxes_given_away: int
    left_three_sided: bool
    explanation: str | None = None  # only the 2-3 biggest mistakes have one


class ReviewOut(BaseModel):
    game_id: str
    moves: list[MoveReviewOut]  # the human's moves only
