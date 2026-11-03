# Experiment 028 - predeclared protocol for the held-out run

Written with the plan, before any game of the arm. It is not edited afterwards. Owner's
go-ahead 2026-11-03 ("lets just move ahead with experiment 28"). The held-out run happens
only if development chooses the arm (plan.md's rule); there is no confirmation stage (no
unused seeds are left).

## Question

Does `h39` (027's record agent `e29_k4` below level 39, 017's frozen agent from 39 on;
native `deep_hybrid_game`, ABI 26) beat the record, 027's `e29_k4` (2,132,514), on
Experiment 012's 1,000 held-out seeds, at 30 Hz / 300 ms? No setting changes after
development.

## Gates and order

1. Before any game, on this build: 017's frozen agent replays the first 28 of its stored
   held-out record games, and `e29_k4` replays the first 28 of 027's stored held-out record
   games, each input for input; the run stops unless all 56 match
   (`heldout_replay_check.json`).
2. The arm plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen, start
   level 18, 430-line cap, frame cap as frozen); every game is replayed on the engine
   through the Python binding and its counters checked (`register.checked_game`).
3. Baselines (stored): 027's record games of `e29_k4`
   (`../027-deeper-39/games/heldout-e29_k4.json.gz`) for the rule; 017's record games
   (1,799,692) reported.

## Success rule

Success (a new record) if the 95% bootstrap confidence interval (`experiment012.paired`:
10,000 resamples, RNG seed 12, percentile method) of the paired mean score difference
(arm minus `e29_k4`) on the 1,000 held-out seeds lies entirely above 0.

Whatever the outcome, also report against both baselines: mean score, mean and median
lines, line-cap share, Tetris rate, P(reach 29), P(reach 39), score by band (paired),
39+ points given reaching 39, Tetrises and singles at 39+, seconds per game.
