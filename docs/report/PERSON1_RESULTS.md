# Person 1 measured results

Depth-4 minimax won a majority of the games against zero-randomness greedy on both
tested board sizes. These are seeded local measurements, not a universal strength claim.

## Match results

| Board | Minimax depth | Wins | Losses | Draws | Win rate | Mean minimax time per move |
|---|---|---|---|---|---|---|
| 3x3 | 4 | 64 | 36 | 0 | 64% | 42.32 ms |
| 4x4 | 4 | 60 | 27 | 13 | 60% | 253.62 ms |

Each size uses 100 games: greedy seeds 0-49, each played twice with the starting
player swapped. Minimax is deterministic. Win rate counts draws as non-wins.
Greedy uses `randomness=0`; equal greedy choices still use its seeded random tie break.
This completes the P1 majority-win acceptance check for the recorded depth-4 sample.

## Depth timings

Median wall time for `choose_move`, with three repetitions at each fixed position.
Opening is empty; middle and late are sampled after roughly one-third and two-thirds
of edges have been drawn by a reproducible random sequence (seed 2026). Each size has
one position per phase, so these are timing examples rather than worst-case bounds.

| Board | Depth | Opening | Middle | Late |
|---|---|---|---|---|
| 3x3 | 1 | 0.13 ms | 0.09 ms | 0.05 ms |
| 3x3 | 2 | 1.99 ms | 0.90 ms | 0.91 ms |
| 3x3 | 3 | 23.26 ms | 12.49 ms | 1.38 ms |
| 3x3 | 4 | 83.69 ms | 20.20 ms | 4.52 ms |
| 4x4 | 1 | 0.16 ms | 0.15 ms | 0.08 ms |
| 4x4 | 2 | 8.76 ms | 4.31 ms | 0.84 ms |
| 4x4 | 3 | 261.10 ms | 76.41 ms | 17.54 ms |
| 4x4 | 4 | 1056.71 ms | 232.43 ms | 88.53 ms |

The default minimax depth remains 3. The strength results above use depth 4.
A shallow box-margin horizon can miss chains and sacrifices; higher depth is not
guaranteed to be stronger in every position. Full-depth searches on large openings
can be expensive. Use these measurements to choose demo settings on the actual hardware.

## Reproduce

```bash
uv sync --locked --all-extras
uv run python -m scripts.benchmark_person1 --games 100 --output results/person1.json
```

Recorded at UTC: `2026-11-10T10:03:20.229439+00:00` (run start).
Python: `3.12.13`. Platform: `Windows-11-10.0.26200-SP0`.
Processor: `Intel64 Family 6 Model 197 Stepping 2, GenuineIntel`.

Timing depends on machine load. Per-phase min/max timings, exact replay edge lists,
and individual match scores are in [the raw JSON](person1-benchmark.json).
Person 2 still owns the full cross-bot arena, charts and calibration data.

Validation: 128 Python tests pass, including the independent minimax oracle,
full HTTP games, hint/review integration, and the existing random-bot checkpoint.
Ruff lint and formatting checks pass. The full suite emits one existing dependency
deprecation warning from FastAPI/Starlette about httpx; no test fails.

See [the handoff](../PERSON1_HANDOFF.md) for implementation details and contracts.
