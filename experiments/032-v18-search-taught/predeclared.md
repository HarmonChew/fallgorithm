# Experiment 032 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md version 2, before any game of Experiment 032. It is not edited
afterwards. Owner's go-ahead 2026-11-06 ("okay follow your recommendations").

## The agent

031b's record agent `v39r` (027's `e29_k4` search; 030's chosen V29,
`../030-v29-search-taught/value_sweep8.bin`, at 230-319 lines; 031b's chosen V39',
`../031-v39-retuned-cap/value_sweep5.bin`, from 320 lines) with the V18 that `experiment032
choose` picks as the network for every decision below 230 lines, in place of 023's `v15`
(plan.md: the probed sweep with the highest paired probe mean against `v39r`, if above 0;
otherwise none, and 032 ends without a staged evaluation). Native `late_hybrid_game` with no
017 switch: commit 29, adjust k 8 to 28, deep2 29 k 4. No exploration. Nothing changes after
`choose`.

## Stages and rules

Primary metric: mean final score, paired by seed against 031b's stored `v39r` games
(`../031-v39-retuned-cap/games/<stage>-v39r.json.gz`), 95% bootstrap interval of
`experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build: 017's frozen agent replays the first 28 of its stored
     held-out record games, `e29_k4` the first 28 of 027's, `v39` the first 28 of 029's,
     `v29` the first 28 of 030's and `v39r` the first 28 of 031b's, each input for input;
     the run stops unless all 140 match.
   * The agent plays all 1,000 seeds in 008's game setup (classic_ntsc_double_killscreen,
     start level 18, 430-line cap, frame cap as frozen); every game is replayed on the
     engine through the Python binding and its counters checked (`register.checked_game`).
   * **Success (a new record)** if the interval of the paired difference against 031b's
     record games of `v39r` (`heldout-v39r.json.gz`, 2,409,955) lies entirely above 0.

Reported, not part of the rule: paired against 030's `v29`, 029's `v39` and 017; points by
band (18, 19-28, 29-38, 39+); P(reach 29); share of games under 230 lines; style at 18,
19-28, 29-38, 39+ and 44+.

Honest odds (plan.md): V18's games split from the first piece, so the per-seed spread is
large; development needs a mean of about +35k and held-out about +25k. A true +20k passes
every stage about 5% of the time, a true +40k about 40%.

This is the sixth record attempt on 012's held-out seeds to play games (after 025, 026/027,
029, 030, 031b).
