# Experiment 027 - predeclared protocol for the held-out run

Written with the plan, before any game of any arm. It is not edited afterwards. Owner's
go-ahead 2026-11-02 ("Fix level 39+ ... let d3 look even deeper there"). The held-out
run happens only if development chooses an arm (plan.md's rule); there is no
confirmation stage (no unused seeds are left).

## Question

Does development's chosen arm (026's record agent `d3_d1b_k8` plus `set_deep2` at the
level and k of that arm; native `deep_net_game`, ABI 25) beat the record, 026's
`d3_d1b_k8` (2,071,704), on Experiment 012's 1,000 held-out seeds, at 30 Hz / 300 ms?
No setting changes after development.

## Gates and order

1. Before any game, on this build: 017's frozen agent replays the first 28 of its stored
   held-out record games, and `d3_d1b_k8` replays the first 28 of 026's stored held-out
   record games, each input for input; the run stops unless all 56 match
   (`heldout_replay_check.json`).
2. The chosen arm plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
   start level 18, 430-line cap, frame cap as frozen); every game is replayed on the engine
   through the Python binding and its counters checked (`register.checked_game`).
3. Baselines (stored): 026's record games of `d3_d1b_k8`
   (`../026-deeper-v/games/heldout-d3_d1b_k8.json.gz`) for the rule; 017's record games
   (1,799,692) reported.

## Success rule

Success (a new record) if the 95% bootstrap confidence interval (`experiment012.paired`:
10,000 resamples, RNG seed 12, percentile method) of the paired mean score difference
(arm minus `d3_d1b_k8`) on the 1,000 held-out seeds lies entirely above 0.

Whatever the outcome, also report against both baselines: mean score, mean and median
lines, line-cap share, Tetris rate, P(reach 29), P(reach 39), score by band (paired),
39+ points given reaching 39, seconds per game.
