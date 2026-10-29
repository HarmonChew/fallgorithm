# Experiment 013 - predeclared protocol

Written before training started and before any held-out game. It is not edited
afterwards.

## Question

Does `reach_plan` with one more ply of lookahead at the adjust search (`native/search.hpp`,
`set_extra_ply`), with its 20 numbers re-tuned for it by CEM, beat Experiment 012 on 012's
1,000 held-out seeds, at 30 Hz / 300 ms?

## Training

* CEM as in Experiment 012 (`experiment009.sample`, `cem_update`): population 48, elite 12,
  30 iterations, sampling RNG seed 13 (Python `random`), spread floor 5% of the starting
  spread.
* Starting mean: Experiment 012's final numbers (`final_params.json`, resolved). Starting
  spread: `experiment009.initial_spread()`.
* Fitness: mean score over 012's 96 training seeds, played by the C++ `reach_plan` with the
  extra ply (`native.play_game_ex("reach_plan_extra_ply", ...)`) in 008's game setup
  (classic_ntsc_double_killscreen, endless, start level 18, 430-line cap, 150,000-frame
  cap).
* The result is the final CEM mean, resolved (`final_params.json`).

## Held-out evaluation

On Experiment 012's 1,000 held-out seeds, the C++ plays:

* **deep**: the extra ply with the final CEM mean (resolved),
* **cem**: 012's `reach_plan` with 012's final numbers (resolved),
* **cem_extra_ply** (secondary): the extra ply with 012's final numbers.

Every game is replayed on the engine through the Python binding and its counters are
checked (`experiment013.play_native`); `verify` replays the whole record again.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12, percentile
method) of the paired mean score difference (deep minus cem) on the 1,000 held-out seeds
lies entirely above 0.

Whatever the outcome, also report for all three agents: mean, median, p5, p10, p90 of
score and lines; top-out rate; share reaching level 29, level 39 and the line cap; the
Tetris rate; the paired lines difference with its interval; deep against cem_extra_ply and
cem_extra_ply against cem; the training curve; and the final mean's training-seed score
(in-sample) next to its held-out score.
