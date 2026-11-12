"""FastAPI server (owner: Person 5).

Run:  uv run uvicorn dnb.server.app:app --reload
Docs: http://localhost:8000/docs

With DNB_SERVE_WEB=1 the built web app (web/dist) is served too, so the demo needs one port
(see `scripts/dev.py --demo`).
"""

from __future__ import annotations

import os
import threading
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from dnb.bots import BOTS, Bot, make_bot
from dnb.coach.explain import explain_mistakes
from dnb.coach.hints import dangerous_moves, hint
from dnb.coach.review import review_game
from dnb.difficulty.levels import LEVELS
from dnb.difficulty.stats import compute_stats
from dnb.engine import GameState, IllegalMoveError
from dnb.server import db
from dnb.server.schemas import (
    DangerOut,
    GameOut,
    GameSummaryOut,
    HintOut,
    LevelOut,
    MoveRequest,
    MoveReviewOut,
    NewGameRequest,
    PlayedMove,
    PlayerStatsOut,
    ReviewOut,
)


@dataclass
class Session:
    id: str
    player_id: str
    bot_spec: str
    level: int | None
    bot: Bot
    human_player: int
    state: GameState
    moves: list[tuple[int, int]] = field(default_factory=list)


# Live games live in memory; finished games are saved to SQLite.
GAMES: dict[str, Session] = {}

# A review can be slow and spends LLM calls, so each game is only reviewed once. The lock covers
# two requests arriving together, which React StrictMode does in dev.
REVIEWS: dict[str, ReviewOut] = {}
REVIEW_LOCK = threading.Lock()

app = FastAPI(title="Dots and Boxes AI")
api = APIRouter(prefix="/api")


def _game_out(
    game_id: str,
    bot_spec: str,
    level: int | None,
    human_player: int,
    state: GameState,
    moves: list[tuple[int, int]],
) -> GameOut:
    return GameOut(
        id=game_id,
        rows=state.rows,
        cols=state.cols,
        bot=bot_spec,
        level=level,
        human_player=human_player,
        current_player=state.current_player,
        moves=[PlayedMove(player=p, edge=e) for p, e in moves],
        box_owners=list(state.owners),
        scores=list(state.scores),
        is_over=state.is_over(),
        winner=state.winner(),
    )


def _out(s: Session) -> GameOut:
    return _game_out(s.id, s.bot_spec, s.level, s.human_player, s.state, s.moves)


def _play(s: Session, edge: int) -> None:
    s.moves.append((s.state.current_player, edge))
    s.state = s.state.apply(edge)


@cache
def bot_available(spec: str) -> bool:
    """True if the bot behind `spec` can move. Bots that are still stubs raise NotImplementedError.

    Checked on a fresh bot and a 1x1 board, so it is instant and never touches a seeded bot's
    random numbers. Cached per process, so restart the server after a teammate ships a bot.
    """
    try:
        make_bot(spec).choose_move(GameState.new(1, 1))
    except (NotImplementedError, ValueError, TypeError):  # stub bot, or a typo in the spec
        return False
    return True


def _bot_turns(s: Session) -> None:
    """Let the bot move until it's the human's turn again (extra-turn rule) or the game ends."""
    while not s.state.is_over() and s.state.current_player != s.human_player:
        try:
            result = s.bot.choose_move(s.state)
        except NotImplementedError as e:
            raise HTTPException(501, f"bot {s.bot_spec!r} is not implemented yet") from e
        _play(s, result.move)
    if s.state.is_over():
        with closing(db.connect()) as conn:
            db.save_game(
                conn,
                game_id=s.id,
                player_id=s.player_id,
                bot_spec=s.bot_spec,
                level=s.level,
                rows=s.state.rows,
                cols=s.state.cols,
                human_player=s.human_player,
                moves=s.moves,
                scores=s.state.scores,
            )


def _get(game_id: str) -> Session:
    if game_id not in GAMES:
        raise HTTPException(404, "game not found")
    return GAMES[game_id]


def _finished_game(game_id: str) -> tuple[int, int, list[tuple[int, int]], int]:
    """(rows, cols, moves, human_player), from SQLite if the server has restarted since the game."""
    if game_id in GAMES:
        s = GAMES[game_id]
        if not s.state.is_over():
            raise HTTPException(409, "the game is not finished")
        return s.state.rows, s.state.cols, s.moves, s.human_player
    with closing(db.connect()) as conn:
        game = db.load_game(conn, game_id)
    if game is None:
        raise HTTPException(404, "game not found")
    return game["rows"], game["cols"], game["moves"], game["human_player"]


@api.get("/bots")
def list_bots() -> list[str]:
    return sorted(BOTS)


@api.get("/levels")
def list_levels() -> list[LevelOut]:
    return [
        LevelOut(level=n, name=lv["name"], bot=lv["bot"], available=bot_available(lv["bot"]))
        for n, lv in sorted(LEVELS.items())
    ]


@api.post("/games")
def new_game(req: NewGameRequest) -> GameOut:
    if req.level is None:
        spec = req.bot
    elif req.level in LEVELS:
        spec = LEVELS[req.level]["bot"]
    else:
        raise HTTPException(400, f"unknown level {req.level}; known: {sorted(LEVELS)}")
    try:
        bot = make_bot(spec)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e)) from e
    if not bot_available(spec):
        raise HTTPException(501, f"bot {spec!r} is not implemented yet")
    s = Session(
        id=uuid.uuid4().hex,
        player_id=req.player_id,
        bot_spec=spec,
        level=req.level,
        bot=bot,
        human_player=0 if req.human_first else 1,
        state=GameState.new(req.rows, req.cols),
    )
    GAMES[s.id] = s
    _bot_turns(s)
    return _out(s)


@api.get("/games/{game_id}")
def get_game(game_id: str) -> GameOut:
    if game_id in GAMES:
        return _out(GAMES[game_id])
    # A finished game from an earlier server run: rebuild it from the saved moves.
    with closing(db.connect()) as conn:
        saved = db.load_game(conn, game_id)
    if saved is None:
        raise HTTPException(404, "game not found")
    state = GameState.new(saved["rows"], saved["cols"])
    for _, edge in saved["moves"]:
        state = state.apply(edge)
    return _game_out(
        game_id, saved["bot_spec"], saved["level"], saved["human_player"], state, saved["moves"]
    )


@api.post("/games/{game_id}/move")
def play_move(game_id: str, req: MoveRequest) -> GameOut:
    s = _get(game_id)
    if s.state.is_over() or s.state.current_player != s.human_player:
        raise HTTPException(409, "not your turn")
    try:
        _play(s, req.edge)
    except IllegalMoveError as e:
        raise HTTPException(400, str(e)) from e
    _bot_turns(s)
    return _out(s)


@api.get("/games/{game_id}/hint")
def get_hint(game_id: str) -> HintOut:
    s = _get(game_id)
    if s.state.is_over() or s.state.current_player != s.human_player:
        raise HTTPException(409, "not your turn")
    result = hint(s.state)
    return HintOut(move=result.move, score=result.score)


@api.get("/games/{game_id}/danger")
def get_danger(game_id: str) -> DangerOut:
    # Separate from /hint because it needs no bot search, so the UI can call it every turn.
    return DangerOut(edges=dangerous_moves(_get(game_id).state))


@api.get("/games/{game_id}/review")
def get_review(game_id: str) -> ReviewOut:
    with REVIEW_LOCK:
        if game_id not in REVIEWS:
            rows, cols, moves, human = _finished_game(game_id)
            reviews = review_game(rows, cols, moves, human)
            explanations = explain_mistakes(reviews)
            REVIEWS[game_id] = ReviewOut(
                game_id=game_id,
                moves=[
                    MoveReviewOut(**asdict(r), explanation=explanations.get(r.ply)) for r in reviews
                ],
            )
        return REVIEWS[game_id]


@api.get("/players/{player_id}/games")
def player_games(player_id: str, limit: int = Query(20, ge=1, le=100)) -> list[GameSummaryOut]:
    with closing(db.connect()) as conn:
        games = db.recent_games(conn, player_id, limit)
    return [GameSummaryOut(bot=g.pop("bot_spec"), **g) for g in games]


@api.get("/players/{player_id}/stats")
def player_stats(player_id: str) -> PlayerStatsOut:
    try:
        stats = compute_stats(player_id)
    except NotImplementedError as e:
        raise HTTPException(501, "player stats are not implemented yet") from e
    return PlayerStatsOut(player_id=player_id, **asdict(stats))


app.include_router(api)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if os.environ.get("DNB_SERVE_WEB") == "1" and WEB_DIST.is_dir():
    # Mounted last so /api/* and /docs win. html=True serves index.html for "/".
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
