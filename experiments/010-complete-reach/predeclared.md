# Experiment 010 - predeclared protocol

Written before any held-out game was evaluated. It is not edited afterwards.

## Question

Does a complete reachability search, which finds every placement reachable under the
same tap and reaction limits, raise `tuned_plan`'s score and survival on the same
held-out seeds, with Experiment 009's learned parameters unchanged?

## What changes

`reach_plan` (`src/block_stack_ai/reachplan.py`) is `tuned_plan` with Experiment 009's
`final_params.json` (resolved values), the same 3-ply search and beam, and the same
commit/adjust reaction model. The only change is that every set of reachable
placements (current piece, preview, unknown pieces, adjust step) comes from
`reach.py` (all placements reachable by any legal tap sequence) instead of
`limits.py` (one fixed route per target). Format: 30 Hz taps, 300 ms reaction,
`classic_ntsc_double_killscreen`, start level 18, 430-line cap, 150,000-frame cap.

## Seeds and timing decision

Experiment 008's 300 held-out seeds, all of them. A timing wave of 30 games (one per
worker on 30 workers) took 144 s, so 300 games is about 25 minutes, well under the
2-hour limit; no prefix is used (`seed_count` = 300 in `config.json`). The baseline is
the `tuned_plan` games kept in Experiment 009's record on the same seeds (paired by
seed).

## Success rule

Primary success: the 95% bootstrap confidence interval (10,000 resamples, fixed RNG
seed 9, percentile method) of the paired mean score difference (reach_plan minus
tuned_plan) lies entirely above 0.

Secondary, reported whatever the outcome: the paired lines difference (same
bootstrap), the top-out rate, and the share of games reaching level 39 and the line
cap. Also reported: mean/median/p5/p10/p90 of score and lines, level 29 reach, Tetris
rate, the mean number of reachable placements per piece at level 29 and at level 39+
for both models, and the average decision time.
