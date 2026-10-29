# Experiment 015 - predeclared protocol

Written before training started and before any held-out game. It is not edited
afterwards.

## Question

Does Experiment 014's agent (`native.play_game_ex("reach_plan_014", ...)`) with 013's
extra ply added to its commit search from level 29 (`commit_ply_level` 29,
`commit_beam` 2), with its 22 numbers re-tuned by CEM, beat Experiment 014 on 012's
1,000 held-out seeds, at 30 Hz / 300 ms?

## Training

* CEM as in Experiment 014 (`experiment009.sample`, `cem_update`) over
  `experiment015.NAMES` (014's 22): population 48, elite 12, 30 iterations, sampling RNG
  seed 15 (Python `random`), spread floor 5% of the starting spread.
* Starting mean: Experiment 014's final numbers (`final_params.json`, resolved). Starting
  spread: `experiment009.initial_spread()`, then 10 (`clear_points`) and 2
  (`killscreen_budget`).
* Fitness: mean score over 012's 96 training seeds, played by the C++ `reach_plan_014`
  with `config.json`'s search settings (`commit_ply_level` 29, `commit_beam` 2), in
  008's game setup (classic_ntsc_double_killscreen, endless, start level 18, 430-line
  cap, 150,000-frame cap).
* The result is the final CEM mean, resolved by `native.resolve` (`final_params.json`).

## Held-out evaluation

On Experiment 012's 1,000 held-out seeds, the C++ `reach_plan_014` plays:

* **fast_deep**: the final CEM mean (resolved) with the search settings,
* **points**: Experiment 014's final numbers (resolved), without them,
* **points_ply** (secondary): 014's final numbers with the search settings.

Every game is replayed on the engine through the Python binding and its counters are
checked (`experiment015.play_native`); `verify` replays the whole record again.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12, percentile
method) of the paired mean score difference (fast_deep minus points) on the 1,000 held-out
seeds lies entirely above 0.

Whatever the outcome, also report for all three agents: mean, median, p5, p10, p90 of
score and lines; top-out rate; share reaching level 29, level 39 and the line cap; the
Tetris rate and score per line; the paired lines difference with its interval; fast_deep
against points_ply and points_ply against points; the training curve; the final mean's
training-seed score (in-sample) next to its held-out score; and the band diagnostic
rerun on the final agent (dev seeds).
