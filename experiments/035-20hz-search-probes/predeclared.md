# Experiment 035 - predeclared protocol for the search probes

Written from plan.md's "Seeds, measurement, rules" (version 2), before any game of
Experiment 035. It is not edited afterwards. Owner's go-ahead: 2026-11-10 (build and run
035 after 034).

## The format

033's: 008/012's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap,
frame cap and agent params as frozen) with tap_hz 20 and reaction 300 ms. Every game is
played in it.

## The agents

No network is trained or changed. Every agent uses 023's v15 below 230 lines, 033's sweep 6
V29@20 at 230-319 and 031b's V39' from 320.

* `base`: `v29r20`'s search. Deeper commit (one unknown piece) from level 29; adjust on the
  best 8 x 8 up to level 28; second unknown piece from level 29, k 4.
* `c18`: `base` with the deeper commit from level 18.
* `c18_d18`: `c18` with the second unknown piece from level 18 (k 4).
* `adj12`: `base` with the adjust on the best 12 x 12.
* `d3`: `base` with a third unknown piece at the commit from level 29. After the second
  piece's rescoring, the two best root placements by points + backup2 are rescored: for
  each of the 7 next pieces (NES odds), the best 2 placements by points + V, each valued by
  points + backup2 with k 2; the piece's value is the better of the two; a piece with
  nowhere to go adds 0. The move is chosen between those two roots only (the first of equal
  values, that is the better by backup2, wins).

## Seeds

1,000 training seeds: 029's list, indices 14,200-15,199 (`seeds.json`), reserved in
`register/SEEDS.md` before any game. Screening only: no record is claimed from them. No
register set (screening, development, held-out) is played.

## Order

1. The free look (no games): the 56 stored held-out `v29r20` games that end before 230
   lines are classified by how they end. It is reported in the notes and changes nothing
   below.
2. Wiring check on the new library (ABI 29), before any game: the first 3 stored `v29r20`
   screening games of 033 are re-run with every arm off and must match input for input.
3. `base` on all 1,000 seeds, once.
4. `c18`, `c18_d18` and `adj12` on all 1,000 seeds.
5. `d3` is timed on the first 4 seeds (4 games at once). If its mean is more than 15
   minutes a game, the third piece runs only at levels 34-38 and that is noted. Then `d3`
   plays the first 500 seeds.
6. The combined setting, if two or more arms gain (below), on all 1,000 seeds.

## Guards

* Every game is replayed on the engine with its counters checked (`register.checked_game`)
  and checked for the 20 Hz tap spacing.
* `d3` changes nothing below level 29: on every seed its inputs must equal `base`'s up to
  the frame the `base` game first has 230 lines (the whole game if it ends before). Any
  mismatch stops the arm.
* Every result records the native library's sha and ABI version.

## Measurement and rules

Per arm: mean final score minus `base`'s on the same seeds, paired by seed, with the 95%
bootstrap interval of `experiment012.paired` (10,000 resamples, RNG seed 12, percentile).

* An arm **gains** if its paired mean is +15,000 or more and the interval's lower end is
  above 0.
* The combined setting takes every gaining arm. `c18_d18` contains `c18`: if both gain, the
  one with the higher paired mean is taken. With `d3` in it, it is compared on all 1,000
  seeds like the others.
* 036's search:
  * no arm gains: 033's search (`base`);
  * one arm gains: that arm, with no further games;
  * two or more gain: the combined setting if it gains by the same rule; otherwise the
    gaining arm with the highest paired mean.
* If the chosen search is slower than about 300 s a game, the float32 speed-up of the
  network is built before 036.

Odds, at the measured spreads (first-piece arms: per-seed correlation ~0, standard error
~13.5k on 1,000 seeds; `d3`: correlation ~0.8, ~7k on 500): a first-piece arm needs an
observed ~+27k; a true +30k passes about half the time, a true +50k about 95%.

Reported, not part of the rule: points by band (paired), P(130), P(230), P(320), deaths by
10-line step, Tetrises / singles / Tetris share by band, the boards at 29's and 39's
entry (230 and 330 lines), seconds a game.
