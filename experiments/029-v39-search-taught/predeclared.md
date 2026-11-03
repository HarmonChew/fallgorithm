# Experiment 029 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md version 2, before any game of Experiment 029. It is not edited
afterwards. Owner's go-ahead 2026-11-03 ("follow your recommendation"). There is no
confirmation stage (no unused seeds are left).

## The agent

027's record agent `e29_k4` (frozen `v15`, native `late_hybrid_game` with no 017 switch:
commit 29, adjust k 8 to 28, deep2 29 k 4) with the V39 that `choose` picks (plan.md:
among all probed sweeps of both arms whose 39+ ranking loss is no worse than v15's, the
highest paired probe mean) as the late network for every decision at 320 lines or more.
No exploration. Nothing changes after `choose`.

## Stages and rules

Primary metric: mean final score, paired by seed against 027's stored `e29_k4` games, 95%
bootstrap interval of `experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build: 017's frozen agent replays the first 28 of its stored
     held-out record games, and `e29_k4` replays the first 28 of 027's stored held-out
     record games, each input for input; the run stops unless all 56 match.
   * The agent plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
     start level 18, 430-line cap, frame cap as frozen); every game is replayed on the
     engine through the Python binding and its counters checked (`register.checked_game`).
   * **Success (a new record)** if the interval of the paired difference against 027's
     record games of `e29_k4` (`../027-deeper-39/games/heldout-e29_k4.json.gz`,
     2,132,514) lies entirely above 0.

Whatever the outcome, report against `e29_k4` and 017 (1,799,692): mean score, mean and
median lines, line-cap share, Tetris rate, P(reach 29), P(reach 39), score by band
(paired), 39+ points given reaching 39, lines / Tetrises / singles at 39+, seconds per
game.
