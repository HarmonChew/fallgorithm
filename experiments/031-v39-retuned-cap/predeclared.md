# Experiment 031 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md version 3, before any game of Experiment 031. It is not edited
afterwards. Owner's go-ahead 2026-11-05 ("Okay"). There is no confirmation stage (no unused
register seeds are left).

## The agent

030's record agent `v29` (027's `e29_k4` search; v15 below 230 lines; 030's chosen V29,
`../030-v29-search-taught/value_sweep8.bin`, at 230-319 lines) with the V39' that
`experiment031 choose` picks as the late network for every decision at 320 lines or more
(plan.md: among all probed sweeps of the arms run whose "commit 39+" ranking loss (odd
rollouts) is no worse than 029's V39's, the highest paired probe mean). Native
`late_hybrid_game` with no 017 switch: commit 29, adjust k 8 to 28, deep2 29 k 4. No
exploration. Nothing changes after `choose`. If Phase D runs, its sweeps join the same
choice.

## Stages and rules

Primary metric: mean final score, paired by seed against 030's stored `v29` games
(`../030-v29-search-taught/games/<stage>-v29.json.gz`), 95% bootstrap interval of
`experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build: 017's frozen agent replays the first 28 of its stored
     held-out record games, `e29_k4` the first 28 of 027's, `v39` the first 28 of 029's
     and `v29` (this runner with 029's V39 as the late network) the first 28 of 030's,
     each input for input; the run stops unless all 112 match.
   * The agent plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
     start level 18, 430-line cap, frame cap as frozen); every game is replayed on the
     engine through the Python binding and its counters checked (`register.checked_game`).
   * **Success (a new record)** if the interval of the paired difference against 030's
     record games of `v29` (`heldout-v29.json.gz`, 2,346,354) lies entirely above 0.

This is the fifth record attempt on 012's held-out seeds (after 025, 026/027, 029, 030).

Whatever the outcome, report against `v29`, `v39` (2,315,238), `e29_k4` (2,132,514) and 017
(1,799,692): mean score, mean and median lines, line-cap share, Tetris rate, P(reach 29),
P(reach 39), share of games below 330 lines, score by band (paired), lines / Tetrises /
singles / Tetris share of lines at 29-38, at 39+ and at 44+ (380 lines on), 39+ points
given reaching 39, seconds per game.
