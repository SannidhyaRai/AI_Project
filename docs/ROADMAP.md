# 20-day roadmap

Each phase is a GitHub milestone. Each checkbox below becomes an issue labelled `p1`-`p5`.

| Phase | Days | Goal | Checkpoint (checked together) |
|---|---|---|---|
| 1 · Set up | 1-3 | Repo, contracts agreed, everyone knows their task | Two random bots play a full game ✅ *(already in CI)* |
| 2 · Build | 4-11 | Each person builds their part alone | Each part works on its own |
| 3 · Connect | 12-16 | Everything plugged into the app, bug fixing | A person can play, get hints and see a review |
| 4 · Finish | 17-20 | Arena results, report, demo practice | Report written and demo rehearsed |

**Day 1-2 for everyone:** read docs/ARCHITECTURE.md, run the quick start, and comment on the
contracts. After day 3 they are frozen.

## Person 1: Engine and classic bots
- [x] Review and own the engine; add more rule tests (edge cases, 1×N boards)
- [x] Greedy bot (`dnb/bots/greedy.py`), including the `randomness` option for Easy levels. **Ship by day 4, others need it.**
- [x] Minimax + alpha-beta (`dnb/bots/minimax.py`). Handle the extra-turn rule!
- [x] Depth setting; measure time per move at each depth on 3×3 and 4×4
- [x] Done: minimax beats greedy in most games (depth 4: 64/100 wins on 3×3; 60/100 on 4×4)
- [ ] Stretch: smarter evaluation (chain counting), faster engine internals

Implementation and integration notes: [Person 1 handoff](PERSON1_HANDOFF.md).
Recorded measurements: [Person 1 results](report/PERSON1_RESULTS.md).

## Person 2: Monte Carlo and arena
- [ ] Monte Carlo bot (`dnb/bots/montecarlo.py`) with random playouts
- [ ] Greedy playouts (`greedy_playouts=true`)
- [ ] `sims` strength setting
- [ ] Arena: every bot vs every bot, ~100 games, swap who starts, CSV output
- [ ] Charts (win rate, think time) with matplotlib
- [ ] Done: MC beats greedy; arena table compares all bots
- [ ] Stretch: full MCTS (UCT) as a separate bot

## Person 3: Adaptive difficulty
- [ ] Elo (`dnb/difficulty/elo.py`) with tests
- [ ] Level table (`levels.py`), calibrated with arena results from Person 2
- [ ] Auto-adjust (`adjuster.py`): target ~50% win rate
- [ ] Player stats from the `games` table (`stats.py`) + `/api/players/{id}/stats` with Person 5
- [ ] Done: always-losing test player goes down, always-winning goes up
- [ ] Stretch: human-like mistakes

## Person 4: Hints and review
- [x] Danger highlight: moves that leave a 3-sided box (works with just the engine, so start here)
- [x] Hint: best move from the strongest bot (minimax for now; revisit after the arena)
- [x] Move review: Good / Okay / Mistake using `evaluate_moves`
- [x] LLM explanations with Gemini, fact-only prompts, MockProvider in tests
- [x] `/hint` and `/review` endpoints with Person 5 (plus `/danger`, cheap enough for every turn)
- [ ] Done: hints and review work in the app; explanations match what happened
- [ ] Stretch: move-quality heatmap

Hints and reviews use minimax with its depth picked per position (`dnb/coach/hints.py`): about a
second at most per hint on 2x2 to 7x7 boards, and a few seconds for a full 4x4 or 5x5 review.

## Person 5: Web app, server, integration
- [ ] Set up GitHub: branch protection, CODEOWNERS usernames, project board, milestones
- [x] Board UI polish: scores, turn indicator, last move, box colours
- [x] Difficulty picker, hint button + danger overlay, review screen, profile screen
- [x] Server: level-based games, stats endpoint, hint/review wiring
- [x] `scripts/dev.py` one-command demo (`--demo` serves everything on one port)
- [ ] Weekly integration check
- [ ] Done: anyone can open the app, pick a level and play a full game
- [ ] Stretch: feedback survey
