"""Reproducible P1 measurements; leaves Person 2's arena implementation untouched.

Run from the repository root: uv run python -m scripts.benchmark_person1
"""

from __future__ import annotations

import argparse
import json
import platform
import random
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from time import perf_counter

from dnb.arena import play_game
from dnb.bots.greedy import GreedyBot
from dnb.bots.minimax import MinimaxBot
from dnb.engine import GameState


def sample_positions(size: int) -> dict[str, GameState]:
    rng = random.Random(2026)
    state = GameState.new(size, size)
    positions = {"opening": state}
    edges = state.layout.num_edges
    for ply in range(1, 2 * edges // 3 + 1):
        state = state.apply(rng.choice(state.legal_moves()))
        if ply == edges // 3:
            positions["middle"] = state
        if ply == 2 * edges // 3:
            positions["late"] = state
    return positions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depths", nargs="+", type=int, default=[1, 2, 3, 4])
    parser.add_argument("--sizes", nargs="+", type=int, default=[3, 4])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--games", type=int, default=100, help="per size; even for balanced seats")
    parser.add_argument("--match-depth", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("results/person1.json"))
    args = parser.parse_args()
    if args.games < 2 or args.games % 2 or args.repeats < 1:
        parser.error("games must be positive and even (>=2); repeats must be positive")
    if any(size < 1 or size > 7 for size in args.sizes):
        parser.error("sizes must be in 1..7")
    if any(depth < 1 for depth in [*args.depths, args.match_depth]):
        parser.error("depths must be positive")

    report = {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "method": "choose_move wall time; 3 seeded positions per size; paired greedy seeds",
        "timings": [],
        "matches": [],
    }
    for size in args.sizes:
        for depth in args.depths:
            bot = MinimaxBot(depth=depth)
            for phase, state in sample_positions(size).items():
                elapsed = []
                for _ in range(args.repeats):
                    start = perf_counter()
                    bot.choose_move(state)
                    elapsed.append((perf_counter() - start) * 1000)
                row = {
                    "size": size,
                    "depth": depth,
                    "phase": phase,
                    "drawn_edges": state.drawn_edges(),
                    "repeats": args.repeats,
                    "median_ms": median(elapsed),
                    "min_ms": min(elapsed),
                    "max_ms": max(elapsed),
                }
                report["timings"].append(row)
                print(f"{size}x{size} depth {depth} {phase}: {median(elapsed):.2f} ms", flush=True)

        wins = losses = draws = 0
        think_time = 0.0
        moves = 0
        records = []
        for seed in range(args.games // 2):
            for seat in (0, 1):
                minimax = MinimaxBot(depth=args.match_depth)
                greedy = GreedyBot(seed=seed)
                bots = (minimax, greedy) if seat == 0 else (greedy, minimax)
                record = play_game(*bots, rows=size, cols=size)
                if record.winner is None:
                    draws += 1
                elif record.winner == seat:
                    wins += 1
                else:
                    losses += 1
                think_time += record.think_time[seat]
                moves += sum(player == seat for player, _ in record.moves)
                records.append({"seed": seed, "minimax_seat": seat, "scores": record.scores})
            if (seed + 1) % 5 == 0:
                print(f"{size}x{size}: {2 * (seed + 1)}/{args.games} games", flush=True)
        row = {
            "size": size,
            "depth": args.match_depth,
            "games": args.games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": wins / args.games,
            "mean_minimax_ms_per_move": 1000 * think_time / moves,
            "games_detail": records,
        }
        report["matches"].append(row)
        print(f"{size}x{size}: {wins} wins, {losses} losses, {draws} draws", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
