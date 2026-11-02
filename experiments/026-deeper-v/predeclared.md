# Experiment 026 - predeclared protocol for the held-out run

Written after the development result and before any held-out game of the arm. It is not
edited afterwards. Owner's go-ahead 2026-11-02 ("go with your recommendation": a record
attempt without a confirmation stage, since no unused seeds are left).

## Question

Does `d3_d1b_k8` (the frozen V agent, `v15`, with 026's two search changes: at the
commit decision from level 29, points + `backup` instead of points + V; at the adjust
decision at levels 18-28, the best 8 current placements, each with its best 8 preview
placements rescored with `backup`; native `deep_net_game`, ABI 24) beat the record,
025's hybrid `v_h29`, on Experiment 012's 1,000 held-out seeds, at 30 Hz / 300 ms?

`d3_d1b_k8` was chosen by the plan's rule (screening on 100 seeds, development on 500:
+350k against V, +217k against v_h29 on the same seeds). No setting changes after this
file.

## Gates and order

1. Before any game, on this build: 017's frozen agent replays the first 28 of its stored
   held-out record games, and 025's hybrid replays the first 28 of its stored held-out
   record games, each input for input; the run stops unless all 56 match
   (`heldout_replay_check.json`).
2. `d3_d1b_k8` plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
   start level 18, 430-line cap, frame cap as frozen); every game is replayed on the
   engine through the Python binding and its counters checked (`register.checked_game`).
3. Baselines (stored, not replayed in full): 025's record games of `v_h29`
   (`../025-hybrids/games/heldout-v_h29.json.gz`, mean 1,835,513) for the rule; 017's
   record games (mean 1,799,692) reported.

## Success rule

Success (a new record) if the 95% bootstrap confidence interval (`experiment012.paired`:
10,000 resamples, RNG seed 12, percentile method) of the paired mean score difference
(`d3_d1b_k8` minus `v_h29`) on the 1,000 held-out seeds lies entirely above 0.

Whatever the outcome, also report against both baselines: mean score, mean and median
lines, line-cap share, Tetris rate, P(reach 29), P(reach 39), games ending before level
29, score by band (paired), 39+ points given reaching 39, boards at 29 and 39, seconds per
game (the baselines' from their own runs), and the paired lines difference.

## Seeds

012's 1,000 held-out seeds are the established record benchmark, used once for each
record attempt (012 to 017, 025). This is one attempt with one configuration.
