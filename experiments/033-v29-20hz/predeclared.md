# Experiment 033 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md, before any game of Experiment 033. It is not edited afterwards.
Owner's go-ahead 2026-11-08.

## The format

008/012's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap, frame
cap and agent params as frozen) with tap_hz 20 and reaction 300 ms. Every game below is
played in it, except the replay gate (30 Hz stored records) and the reported side check.

## The agents

* `v39r20`: 031b's record agent `v39r` (023's v15 below 230 lines, 030's V29 at 230-319,
  031b's V39' from 320; native `late_hybrid_game`, no 017 switch: commit 29, adjust k 8 to
  28, deep2 29 k 4), unchanged, in the 20 Hz format.
* `v29r20`: `v39r20` with the V29@20 that `experiment033 choose` picks (the probed sweep
  with the highest paired probe mean against `v39r20`, if above 0; otherwise none and 033
  ends without a staged evaluation) for every decision at 230-319 lines. No exploration.
  Nothing changes after `choose`.

## Stages and rules

Primary metric: mean final score of `v29r20` minus `v39r20`, paired by seed (both played
in this experiment on this build), 95% bootstrap interval of `experiment012.paired`
(10,000 resamples, RNG seed 12, percentile).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build: 017's frozen agent, `e29_k4`, `v39`, `v29` and `v39r`
     each replay the first 28 of their stored held-out record games (30 Hz) input for
     input; the run stops unless all 140 match.
   * Then the first 28 development games of `v39r20` and of `v29r20` are replayed input
     for input in the 20 Hz format; the run stops unless all 56 match.
   * `v39r20` and `v29r20` play all 1,000 seeds in the 20 Hz format; every game is replayed
     on the engine through the Python binding and its counters checked
     (`register.checked_game`) and checked for the 20 Hz tap spacing (no two presses of
     the same kind closer than 3 frames).
   * **Success (the first 20 Hz / 300 ms record)** if the interval of the paired
     difference lies entirely above 0. `v39r20`'s held-out mean is reported as the 20 Hz
     baseline either way.

Honest odds: at a per-seed spread of ~600k, development's interval clears 0 at an observed
~+53k and held-out at ~+37k; a true +40k passes development about 30% of the time and
held-out about 55%; a true +80k passes nearly always.

The training hand-over value (V39''s backup2 or, by plan.md's predeclared round-0 rule, the
actual rest of game) is fixed after round 0 and before sweep 1.

Reported, not part of the rule: points by band (18, 19-28, 29-38, 39+, paired), P(reach
320), P(reach 39), share of games under 330 lines, style at 29-38, 39+ and 44+, seconds per
game; BetaTetris's 20 Hz / 300 ms figures (owner's table, other seeds: rough only); side
check: `v29r20` at 30 Hz on the screening seeds, paired against 031b's stored `v39r` games.
