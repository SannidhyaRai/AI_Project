# Architecture

```
 Browser  web/  (React + Vite + TS)                                 Person 5
    │  HTTP/JSON, /api/*  (Vite proxies to :8000 in dev)
    ▼
 FastAPI  dnb/server/  + SQLite game history                        Person 5
    │  plain Python calls
    ├──────────────────────┬──────────────────────┬────────────────────
    ▼                      ▼                      ▼
 dnb/difficulty/  P3    dnb/coach/  P4         dnb/arena/  P2
 levels, Elo,          hints, danger,          bot vs bot,
 auto-adjust, stats    review, LLM explain     win-rate charts
    └──────────────────────┴──────────────────────┘
                           │  make_bot("minimax:depth=3")
                           ▼
 dnb/bots/   one Bot interface + registry                           P1, P2
 random, greedy, minimax (P1) · montecarlo (P2)
                           │
                           ▼
 dnb/engine/   GameState, legal moves, scoring, extra-turn rule     P1
```

Dependencies only point **down** this diagram. The engine imports nothing from the project, bots
import only the engine, and so on. If you find yourself importing upward, ask in the chat first.

## The contracts

These four interfaces are what lets five people work at the same time. They are **frozen**: any
change to them needs a PR labelled `contract` and approved by the whole team.

### 1. Engine: `dnb/engine/state.py`

- A move is an **int edge index**. Horizontal edges come first, then vertical edges (formula in
  the module docstring). `edge_coords()` converts an index to `("h"|"v", r, c)`.
- `GameState` is **immutable**: `state.apply(move)` returns a new state. That makes search and
  simulation safe, since nothing has to be undone.
- `GameState.new(rows, cols)`, `.legal_moves()`, `.apply(m)`, `.is_over()`, `.winner()`,
  `.current_player`, `.scores`, `.owners`, `.sides(box)`, `.boxes_completed_by(m)`.
- **Extra-turn rule:** `current_player` stays the same after a move that completes a box. Never
  assume players alternate.

Person 1 may make the internals faster at any time (bitboards, caching) as long as these
signatures and the tests stay the same.

### 2. Bot: `dnb/bots/base.py`

```python
class Bot:
    def evaluate_moves(self, state) -> dict[int, float]: ...  # score every legal move
    def choose_move(self, state) -> MoveResult: ...  # MoveResult(move, score, info)
```

Scores are always in **[-1, 1], from the point of view of the player to move**. That way the
review (Person 4) and difficulty (Person 3) can compare any two bots.

### 3. Registry: `dnb/bots/registry.py`

Bots are created from text specs: `"random"`, `"greedy:randomness=0.3"`, `"minimax:depth=4"`,
`"montecarlo:sims=2000,greedy_playouts=true"`. A difficulty level is just a spec
(`dnb/difficulty/levels.py`), and the arena, server and hints all use the same specs.

### 4. API and database: `dnb/server/schemas.py`, `dnb/server/db.py`, `web/src/api.ts`

| Method | Path | Owner | Status |
|---|---|---|---|
| GET  | `/api/bots` | P5 | working |
| GET  | `/api/levels` | P3 + P5 | working (levels from `levels.py`, `available: false` while a bot is a stub) |
| POST | `/api/games` | P5 | working (`level` picks the bot from `levels.py`; else `bot` spec) |
| GET  | `/api/games/{id}` | P5 | working (finished games also load from SQLite after a restart) |
| POST | `/api/games/{id}/move` | P5 | working (bot replies, including extra turns) |
| GET  | `/api/games/{id}/hint` | P4 + P5 | working (best move, needs a bot search) |
| GET  | `/api/games/{id}/danger` | P4 + P5 | working (no search, cheap enough for every turn) |
| GET  | `/api/games/{id}/review` | P4 + P5 | working (finished games, cached per game) |
| GET  | `/api/players/{id}/games` | P5 | working (recent finished games, newest first, `?limit=`) |
| GET  | `/api/players/{id}/stats` | P3 + P5 | wired: returns 501 until `compute_stats` is implemented |

A bot that still raises `NotImplementedError` never crashes a game: `/api/levels` marks it
unavailable, and `POST /api/games` answers 501 so the UI can say so. The web app's "Auto" level
uses `PlayerStats.level` from the stats endpoint, so it switches on when Person 3 ships stats.

`schemas.py` and `web/src/api.ts` must change in the **same PR**. Finished games go to the SQLite
`games` table (schema in `db.py`). Persons 3 and 4 read from it.

## Board sizes

The default is 3×3 boxes (24 edges). Minimax at full depth is only practical on small boards.
Bots must work on any size from 1×1 to 7×7, and difficulty levels may also change the board size.

## LLM explanations

`dnb/coach/explain.py` has an `LLMProvider` interface with `MockProvider` (used by tests and CI)
and `GeminiProvider` (used when `GEMINI_API_KEY` is set in `.env`). The prompt only gets
**facts computed by the review** (which move, which better move, how many boxes it gave away), so
the LLM rephrases what happened rather than analysing the game itself. If the call fails or the
answer contradicts those facts, a template sentence built from the same facts is shown instead.
