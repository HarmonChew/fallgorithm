# Experiment 009 - predeclared protocol

Written before training started. It is not edited afterwards.

## Question

Can CEM-learned evaluation parameters raise `bench_plan`'s mean score at 30 Hz /
300 ms reaction on held-out seeds?

## What is tuned

`tuned_plan` (`src/block_stack_ai/tunedplan.py`) is `bench_plan` with every number
in its evaluation as a parameter (20 in all):

* the 8 BUILD-phase weights (tetrises, premature_clear, holes, aggregate_height,
  bumpiness, max_height, reserve, overflow),
* the 5 SPEND-phase weights (lines_cleared, holes, aggregate_height, bumpiness,
  max_height) plus 3 extra SPEND features that start at 0 (row_transitions,
  column_transitions, edge_depth),
* 4 whole numbers: height_budget (8), survival_budget (5), survival_level (28),
  drought_bound (9). These are sampled as floats, rounded, and clamped to budgets
  2-14, level 19-38, drought 4-20.

With the default values it plays exactly like `bench_plan` (checked by a test).

## Training (CEM)

* Population 32, elite 8, 12 iterations, sampling RNG seed 9 (Python `random`).
* The mean starts at the defaults. The starting spread is 50% of each weight's
  magnitude, 1.0 for the zero-start features and 2 for the whole numbers. The spread
  can never fall below 5% of its starting value.
* Fitness of a candidate: its mean score over 24 training seeds, at 30 Hz / 300 ms,
  in 008's game setup (ruleset classic_ntsc_double_killscreen, start level 18,
  430-line cap, 150,000-frame cap).
* Training seeds: `SHA256("fallgorithm009/train/v1/<i>")`, first two bytes, skipping
  every seed used by Experiments 000-008 (including 008's 300) and any seed with
  the same native start state as one of those. Listed in `seeds.json`.
* The final CEM mean (not the best sample) is the result.
* `bench_plan` is also played once on the 24 training seeds to give a training baseline.

## Held-out evaluation

The final mean is played on Experiment 008's 300 seeds at 30 Hz / 300 ms, with the
same game setup. The baseline is the 30 Hz / 300 ms games kept in Experiment 008's
record, on the same seeds, so the comparison is paired. Games are recorded with
their inputs and clear sizes and verified by replaying them on the engine.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, fixed RNG seed
9, percentile method) of the paired mean score difference (tuned minus 008) lies
entirely above 0.

Whatever the outcome, also report: mean, median, p5, p10, p90 of score and lines;
top-out rate; share of games reaching level 29, level 39 and the line cap; the
Tetris rate (lines cleared as Tetrises over all lines); and the paired lines
difference.
