# Dots and Boxes AI

A web game where you play Dots and Boxes against AI bots of different strengths. The game adapts
to your level, gives hints, and explains your mistakes. Semester project, team of five, 20 days.
Full brief: [docs/project-brief.pdf](docs/project-brief.pdf).

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Node.js 20+.

```bash
uv sync --all-extras          # Python 3.12 + all dependencies, identical for everyone
cd web && npm install && cd ..
uv run python scripts/dev.py  # starts the API (:8000) and the web app (:5173)
```

Open http://localhost:5173. API docs: http://localhost:8000/docs.

For the presentation, `uv run python scripts/dev.py --demo` builds the web app once and serves
everything from http://localhost:8000, with no auto-reload.

Everyday commands:

```bash
uv run pytest                        # all tests
uv run ruff check . --fix            # lint
uv run ruff format .                 # format
uv run python -m dnb.arena.run_arena # bot-vs-bot table
```

## Who owns what

| Person | Area | Folder |
|---|---|---|
| 1 | Game engine, random / greedy / minimax bots | `dnb/engine/`, `dnb/bots/` |
| 2 | Monte Carlo bot, bot arena, result charts | `dnb/bots/montecarlo.py`, `dnb/arena/` |
| 3 | Difficulty levels, Elo, auto-adjust, player stats | `dnb/difficulty/` |
| 4 | Hints, danger highlight, move review, LLM explanations | `dnb/coach/` |
| 5 | Web app, FastAPI server, game history, CI, demo | `web/`, `dnb/server/`, `scripts/` |

Read these before your first PR:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the parts fit, and the contracts.
- [CONTRIBUTING.md](CONTRIBUTING.md): branches, PRs, reviews.
- [docs/ROADMAP.md](docs/ROADMAP.md): the 20-day plan and each person's task list.
- [docs/PERSON1_HANDOFF.md](docs/PERSON1_HANDOFF.md): engine and classic bots, usage, contracts,
  tests, measurements and integration notes for teammates.
