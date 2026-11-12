"""Game history in SQLite (owner: Person 5). Persons 3 and 4 read from these tables.

Schema is part of the team contract: add columns freely, but don't rename or remove them
without telling Persons 3 and 4.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("DNB_DB_PATH", "data/games.sqlite"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id           TEXT PRIMARY KEY,
    player_id    TEXT NOT NULL,
    bot_spec     TEXT NOT NULL,
    level        INTEGER,             -- difficulty level, NULL if a bot was picked directly
    rows         INTEGER NOT NULL,
    cols         INTEGER NOT NULL,
    human_player INTEGER NOT NULL,    -- 0 or 1
    moves        TEXT NOT NULL,       -- JSON list of [player, edge]
    score_human  INTEGER NOT NULL,
    score_bot    INTEGER NOT NULL,
    result       REAL NOT NULL,       -- for the human: 1 win, 0.5 draw, 0 loss
    finished_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS games_by_player ON games (player_id, finished_at);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_game(
    conn: sqlite3.Connection,
    *,
    game_id: str,
    player_id: str,
    bot_spec: str,
    level: int | None,
    rows: int,
    cols: int,
    human_player: int,
    moves: list[tuple[int, int]],
    scores: tuple[int, int],
) -> None:
    human, bot = scores[human_player], scores[1 - human_player]
    result = 1.0 if human > bot else 0.5 if human == bot else 0.0
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO games (id, player_id, bot_spec, level, rows, cols,"
            " human_player, moves, score_human, score_bot, result)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                game_id,
                player_id,
                bot_spec,
                level,
                rows,
                cols,
                human_player,
                json.dumps(moves),
                human,
                bot,
                result,
            ),
        )


def load_game(conn: sqlite3.Connection, game_id: str) -> dict[str, Any] | None:
    """One saved game with `moves` decoded to [(player, edge)], or None if there is no such game."""
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        return None
    game = dict(row)
    game["moves"] = [(player, edge) for player, edge in json.loads(game["moves"])]
    return game


def recent_games(conn: sqlite3.Connection, player_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """A player's finished games, newest first, without the move lists."""
    rows = conn.execute(
        "SELECT id, bot_spec, level, rows, cols, score_human, score_bot, result,"
        " finished_at FROM games WHERE player_id = ? ORDER BY finished_at DESC, rowid DESC"
        " LIMIT ?",
        (player_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]
