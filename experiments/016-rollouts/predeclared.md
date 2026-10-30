# Experiment 016 - predeclared protocol

Written after the dev-seed depth check and before any held-out game. It is not edited
afterwards.

## Question

Does Experiment 015's agent (`fast_deep`: 015's final numbers with its commit ply) with
rollout re-ranking at levels 18-28 (`native.play_game_ex("reach_plan_016", ...)`,
`config.json`'s `rollout`: beam 4, 32 rollouts, depth 5, death 1000) beat 015's agent
on 012's 1,000 held-out seeds, at 30 Hz / 300 ms?

## Agents

No training: both agents use 015's final numbers (`experiments/015-fast-commit/
final_params.json`, resolved) with 015's commit ply (`commit_ply_level` 29,
`commit_beam` 2).

* **rollout**: `reach_plan_016` with `config.json`'s `rollout` settings,
* **fast_deep**: `reach_plan_014` (015's agent).

The rollout settings were chosen on Experiment 013's first 100 dev seeds
(`depth_check.json`): the variant with the best paired mean score against fast_deep.

## Held-out evaluation

On Experiment 012's 1,000 held-out seeds, in 008's game setup (classic_ntsc_double_
killscreen, endless, start level 18, 430-line cap, 150,000-frame cap), both agents play
every seed. Every game is replayed on the engine through the Python binding and its
counters are checked (`experiment016.play_native`); `verify` replays the whole record
again.

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12, percentile
method) of the paired mean score difference (rollout minus fast_deep) on the 1,000
held-out seeds lies entirely above 0.

Whatever the outcome, also report for both agents: mean, median, p5, p10, p90 of score
and lines; top-out rate; share reaching level 29, level 39 and the line cap; the Tetris
rate and score per line; the paired lines difference with its interval; the decision
time per game; and the dev-seed depth check and reaction check.
