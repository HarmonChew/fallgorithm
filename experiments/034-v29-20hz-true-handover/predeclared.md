# Experiment 034 - predeclared protocol for the staged evaluation and the held-out run

Written with plan.md (version 2), before any game of Experiment 034. It is not edited
afterwards. Owner's go-ahead: pending.

## The format

033's: 008/012's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap,
frame cap and agent params as frozen) with tap_hz 20 and reaction 300 ms. Every game
below is played in it, except the 30 Hz part of the held-out replay gate.

## The agents

* `v29r20`: 033's 20 Hz record agent (023's v15 below 230 lines, 033's sweep 6 V29@20 at
  230-319, 031b's V39' from 320; the same native search as `v39r`), unchanged. It is not
  played again in the stages. Its stored games in `../033-v29-20hz/games/`
  (`screening-v29r20`, `development-v29r20`, `heldout-v29r20`) are the base.
* `v29t20`: `v29r20` with the V29@20 that `experiment034 choose` picks (the probed sweep
  with the highest paired probe mean against `v29r20`, if above 0; otherwise none and 034
  ends without a staged evaluation) for every decision at 230-319 lines. No exploration.
  Nothing changes after `choose`.

## Training values (fixed before round 0)

The hand-over value is the actual rest of the game, and hand-over boards are training rows
with that target. 320+ children get max(0, c x V39''s backup2), with c from
`handover_calibration.json` (written by `experiment034 calibrate` from 033's rounds 6-8
before any 034 game, committed, never refit). Lambda is 0.99.

Stop rule: at least 5 sweeps, at most 10. From sweep 5, stop after 3 sweeps without a new
best probe mean, and only once the latest round's V29@20 value minus the actual rest of
game is within ±2 Tetrises at every 10-line step from 270 to 319.

## Stages and rules

Primary metric: mean final score of `v29t20` minus `v29r20`, paired by seed, 95% bootstrap
interval of `experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

Guards on every stage (any failure stops the stage):

* On every seed, `v29t20`'s inputs equal the stored `v29r20` game's up to its first
  decision at 230+ lines (or the whole game, if it ends before then).
* Before the stage, the first 28 stored `v29r20` games of that stage's set are re-played
  by running the agent (not just an engine input replay) in the 20 Hz format, and all
  inputs match.
* Every result records the native library's sha and ABI version. The ABI must equal
  033's (28). A different library sha is noted.

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), Experiment 012's 1,000 held-out seeds, only if kept:
   * Before any game, on this build:
     * 017's frozen agent, `e29_k4`, `v39`, `v29` and `v39r` each replay the first 28 of
       their stored 30 Hz held-out record games (140/140).
     * At 20 Hz, the first 28 stored held-out games of `v29r20` and the first 28
       development games of `v29t20` are re-run (56/56).
     * The run stops unless all match.
   * `v29t20` plays all 1,000 seeds in the 20 Hz format. Every game is replayed on the
     engine through the Python binding with its counters checked
     (`register.checked_game`), and checked for the 20 Hz tap spacing.
   * **Success (a new 20 Hz / 300 ms record)** if the interval of the paired difference
     lies entirely above 0.

Honest odds, at the measured paired spread of ~160k (033's probe; it is measured again on
034's probe and reported):

* Development's interval clears 0 at an observed ~+14k, so its +15k bar binds there.
  Held-out's clears 0 at ~+10k.
* Passing every stage: a true +15k about 25% of the time, +30k about 80%, +40k about 95%.

Reported, not part of the rule: points by band (paired), P(reach 320), P(reach 39), share
of games under 330 lines, deaths by 10-line step at 230-329, style at 29-38 and 39+,
seconds per game; BetaTetris's 20 Hz / 300 ms figures if the owner's table has arrived
(other seeds: rough only).
