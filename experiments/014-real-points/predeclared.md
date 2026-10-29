# Experiment 014 - predeclared protocol

Written before training started and before any held-out game. It is not edited
afterwards.

## Question

Does 013's deep search (`reach_plan_extra_ply`) with the NES randomizer's piece odds,
a real-points clear term (`clear_points`) and its own BUILD height budget from level 39
(`killscreen_budget`), together `native.play_game_ex("reach_plan_014", ...)`, with its
22 numbers re-tuned by CEM, beat Experiment 013 on 012's 1,000 held-out seeds, at
30 Hz / 300 ms?

## Training

* CEM as in Experiment 013 (`experiment009.sample`, `cem_update`) over
  `experiment014.NAMES` (009's twenty, then `clear_points`, `killscreen_budget`):
  population 48, elite 12, 30 iterations, sampling RNG seed 14 (Python `random`), spread
  floor 5% of the starting spread.
* Starting mean: Experiment 013's final numbers (`final_params.json`, resolved),
  `clear_points` 0, `killscreen_budget` 2. Starting spread:
  `experiment009.initial_spread()`, then 10 and 2.
* Fitness: mean score over 012's 96 training seeds, played by the C++ `reach_plan_014`
  in 008's game setup (classic_ntsc_double_killscreen, endless, start level 18, 430-line
  cap, 150,000-frame cap).
* The result is the final CEM mean, resolved by `native.resolve` (`final_params.json`).

## Held-out evaluation

On Experiment 012's 1,000 held-out seeds, the C++ plays:

* **points**: `reach_plan_014` with the final CEM mean (resolved),
* **deep**: 013's `reach_plan_extra_ply` with 013's final numbers (resolved),
* **deep_nes** (secondary): `reach_plan_014` with 013's final numbers.

Every game is replayed on the engine through the Python binding and its counters are
checked (`experiment014.play_native`); `verify` replays the whole record again.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12, percentile
method) of the paired mean score difference (points minus deep) on the 1,000 held-out seeds
lies entirely above 0.

Whatever the outcome, also report for all three agents: mean, median, p5, p10, p90 of
score and lines; top-out rate; share reaching level 29, level 39 and the line cap; the
Tetris rate and score per line; the paired lines difference with its interval; points
against deep_nes and deep_nes against deep; the training curve; the final mean's
training-seed score (in-sample) next to its held-out score; and the singles diagnostic
rerun on the final agent (dev seeds).
