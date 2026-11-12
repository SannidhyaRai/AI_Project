"""API request/response shapes. CONTRACT: web/src/api.ts mirrors these; change both together."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NewGameRequest(BaseModel):
    rows: int = Field(3, ge=1, le=7)
    cols: int = Field(3, ge=1, le=7)
    bot: str = "random"  # bot spec, see dnb/bots/registry.py; ignored when `level` is set
    level: int | None = None  # difficulty level (dnb.difficulty.levels); overrides `bot`
    human_first: bool = True
    player_id: str = Field("guest", min_length=1, max_length=40)


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
    level: int | None = None  # set when the game was started from a difficulty level
    human_player: int
    current_player: int
    moves: list[PlayedMove]
    box_owners: list[int]  # -1 = unclaimed
    scores: list[int]
    is_over: bool
    winner: int | None


class LevelOut(BaseModel):
    level: int
    name: str
    bot: str  # bot spec behind the level
    available: bool  # False until the bot behind the level is implemented


class PlayerStatsOut(BaseModel):
    """Mirrors dnb.difficulty.stats.PlayerStats (Person 3) plus the player id."""

    player_id: str
    games_played: int
    win_rate: float
    boxes_given_away_per_game: float
    rating: float
    level: int  # the level the adjuster recommends next ("Auto" in the picker uses it)


class GameSummaryOut(BaseModel):
    """One finished game in a player's history (profile screen)."""

    id: str
    bot: str
    level: int | None
    rows: int
    cols: int
    score_human: int
    score_bot: int
    result: float  # for the human: 1 win, 0.5 draw, 0 loss
    finished_at: str  # UTC, "YYYY-MM-DD HH:MM:SS"


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
