# Experiment 012 - predeclared protocol

Written before training started and before any held-out game. It is not edited
afterwards.

## Question

Does a full CEM run on the native `reach_plan` beat Experiment 009's numbers on fresh
held-out seeds, at 30 Hz / 300 ms?

## Training

* CEM as in Experiment 009 (`experiment009.sample`, `cem_update`): population 48,
  elite 12, 30 iterations, sampling RNG seed 12 (Python `random`), spread floor 5% of
  the starting spread.
* Starting mean: Experiment 009's final numbers (`final_params.json`, resolved).
  Starting spread: `experiment009.initial_spread()`.
* Fitness: mean score over the 96 training seeds of `seeds.json`, played by the C++
  `reach_plan` (`native.play_game`) in 008's game setup (classic_ntsc_double_killscreen,
  endless, start level 18, 430-line cap, 150,000-frame cap).
* The result is the final CEM mean, resolved (`final_params.json`).

## Held-out evaluation

On the 1,000 held-out seeds of `seeds.json`, the C++ `reach_plan` plays:

* **cem**: the final CEM mean (resolved),
* **baseline**: Experiment 009's numbers (resolved).

Every game is replayed on the engine through the Python binding and its counters are
checked (`experiment011.play_native`); `verify` replays the whole record again.

Secondary (not part of the success rule): **cem** on Experiment 008's 300 seeds,
against `experiments/011-native-speed/records/run.json.gz`.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12,
percentile method) of the paired mean score difference (cem minus baseline) on the
1,000 held-out seeds lies entirely above 0.

Whatever the outcome, also report for both agents: mean, median, p5, p10, p90 of score
and lines; top-out rate; share reaching level 29, level 39 and the line cap; the Tetris
rate; the paired lines difference with its interval; the training curve; and the final
mean's training-seed score (in-sample) next to its held-out score.
