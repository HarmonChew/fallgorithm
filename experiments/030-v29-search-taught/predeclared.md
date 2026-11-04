# Experiment 030 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md version 2, before any game of Experiment 030. It is not edited
afterwards. Owner's go-ahead 2026-11-04 ("okay lets just work on V29"). There is no
confirmation stage (no unused register seeds are left).

## The agent

029's record agent `v39` (027's `e29_k4` with 029's chosen V39, `t2/value_sweep8.bin`, for
every decision at 320 lines or more; native `late_hybrid_game` with no 017 switch: commit
29, adjust k 8 to 28, deep2 29 k 4) with the V29 that `choose` picks (plan.md: among all
probed sweeps whose "commit 29-38" ranking loss below 320 lines is no worse than v15's,
the highest paired probe mean) as the mid network for every decision at 230-319 lines.
No exploration. Nothing changes after `choose`.

## Stages and rules

Primary metric: mean final score, paired by seed against 029's stored `v39` games, 95%
bootstrap interval of `experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build: 017's frozen agent replays the first 28 of its stored
     held-out record games, `e29_k4` the first 28 of 027's, and `v39` (no mid network) the
     first 28 of 029's, each input for input; the run stops unless all 84 match.
   * The agent plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
     start level 18, 430-line cap, frame cap as frozen); every game is replayed on the
     engine through the Python binding and its counters checked (`register.checked_game`).
   * **Success (a new record)** if the interval of the paired difference against 029's
     record games of `v39` (`../029-v39-search-taught/games/heldout-v39.json.gz`,
     2,315,238) lies entirely above 0.

This is the fourth record attempt on 012's held-out seeds (after 025, 026/027 and 029).

Whatever the outcome, report against `v39`, `e29_k4` (2,132,514) and 017 (1,799,692):
mean score, mean and median lines, line-cap share, Tetris rate, P(reach 29), P(reach 39),
share of games below 330 lines, score by band (paired), lines / Tetrises / singles at
29-38 and at 39+, 39+ points given reaching 39, seconds per game.
