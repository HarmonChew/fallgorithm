# Experiment 025 - predeclared protocol for the held-out run

Written after the development result and before any confirmation or held-out game of the
hybrid (017's own confirmation games were playing while this was written; none of the
hybrid's). It is not edited afterwards.

## Question

Does the hybrid `v_h29` (023's V agent below level 29, 017's agent from level 29, both
exactly as frozen in `experiments/register/frozen/017.json` and `v15.json`; native
`hybrid_game`, ABI 23) beat 017 on Experiment 012's 1,000 held-out seeds, at 30 Hz /
300 ms?

`v_h29` was chosen on the screening seeds (one of three arms) and kept on the 500
development seeds (+55k paired against 017, 95% CI +21k to +88k). No setting is changed
after this file.

## Order and gates

1. Confirmation: `experiment025 confirm` plays `v_h29` on the register's 200 confirmation
   seeds, paired against 017's games there (`register play confirmation 017`). It passes
   if the paired interval's lower end is above 0 (plan.md, step 3). If it fails, the
   held-out run is not played and 025 stops there.
2. Held-out: `experiment025 heldout`. Before any hybrid game, 017's frozen agent replays
   the first 28 of its stored held-out record games on this build
   (`register.check_frozen("017", 28)`); the run stops unless all 28 match input for
   input (`heldout_replay_check.json`). Then `v_h29` plays all 1,000 seeds in 008's game
   setup (classic_ntsc_double_killscreen, start level 18, 430-line cap, frame cap as
   frozen). Every game is replayed on the engine through the Python binding and its
   counters checked (`register.checked_game`).
3. Baseline: 017's stored held-out record games
   (`experiments/017-commit-rollouts/records/run.json.gz`, agent `commit_rollout`, mean
   1,799,692), not replayed in full.

## Success rule

Success (a new record) if the 95% bootstrap confidence interval (`experiment012.paired`:
10,000 resamples, RNG seed 12, percentile method) of the paired mean score difference
(`v_h29` minus 017) on the 1,000 held-out seeds lies entirely above 0.

Whatever the outcome, also report for both: mean score, mean and median lines, line-cap
share, Tetris rate, P(reach 29), P(reach 39), score by band (18, 19-28, 29-38, 39+)
paired, 39+ points given reaching 39, the board at 29 and 39, seconds per game (017's
from its own run on another build and load, so not like for like), and the paired
lines difference.

## Seeds

012's 1,000 held-out seeds are the established record benchmark, used once for each
record attempt (012 to 017). This is one attempt with one configuration.
