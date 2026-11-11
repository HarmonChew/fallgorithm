# Experiment 035b - predeclared protocol: a 20 Hz record attempt for 035's combined search

Written 2026-11-11, after 035's results (27323dd) and notes (23e35c8), before any 035b game.
It is not edited afterwards. Owner's go-ahead 2026-11-11 ("just go with your
recommendations": bank the search gain as a record before 036, so 036 measures teaching
alone). Code: `src/block_stack_ai/experiment035eval.py`.

## Why

035 found that `v29r20` with a deeper search (the combined setting) scores +129.8k (95% CI
+110.1k, +150.4k) on 1,000 training seeds. Those were screening seeds, so no record was
claimed. 036 will re-teach the networks under that search. Measuring the search alone on
the record benchmark first separates the two gains, and banks this one.

## The format and the agents

033's format: 008/012's game setup (classic_ntsc_double_killscreen, start level 18,
430-line cap, frame cap and agent params as frozen) with tap_hz 20 and reaction 300 ms.

* Arm `v29r20d`: 033's `v29r20` with its networks unchanged (023's v15 below 230 lines,
  033's sweep 6 V29@20 at 230-319, 031b's V39' from 320) and 035's `search_for_036`:
  deeper commit and second unknown piece (k 4) from level 18, adjust on the best 8 x 8 to
  level 28, third unknown piece at the commit from level 29 (`deep3` [29, 1000, 2, 2, 2]).
* Base: 033's stored `v29r20` games on the same seeds (not re-played; the gate below shows
  this build still plays them).

## Order

1. **Gate**, on this build (ABI 29) before any arm game: 032's 30 Hz replay gate (28 each
   of 017's, e29_k4's, v39's, v29's and v39r's stored held-out games, 140) and the first 28
   stored `v29r20` development and held-out games re-run with `v29r20`'s own search (56).
   All must match input for input; otherwise nothing is played and the gate is reported.
2. **Development**: `v29r20d` on the register's 500 development seeds.
3. **Held-out**, only if development keeps it: `v29r20d` on 012's 1,000 held-out seeds.

No screening stage: 035's 1,000 probe seeds were the screen.

## Rules

Primary metric: mean final score of `v29r20d` minus the stored `v29r20` games' on the same
seeds, paired by seed, 95% bootstrap interval of `experiment012.paired` (10,000 resamples,
RNG seed 12).

* Development: **kept** if the paired mean is +15,000 or more and the interval's lower end
  is above 0.
* Held-out: **a new 20 Hz / 300 ms record** if the interval's lower end is above 0. The
  record then names `v29r20d` and its held-out mean; `v29r20`'s 1,710,180 is the previous
  record.

Odds: per-seed correlation in 035 was about 0 (the arms differ from the first piece), so
the standard error is about 14k on development and 10k on held-out from 035's own spread
(its combined interval, +110.1k to +150.4k on 1,000 seeds); 036's plan, from `v29r20`'s
held-out spread, puts it more cautiously at 17-19k and 12-13.5k. Development's interval
then clears 0 at an observed ~+28-37k, held-out's at ~+20-26k. With a true gain like 035's
(+130k), both stages pass almost surely; a true +40k would pass both about half to two
thirds of the time.

## Guards

* Every game is replayed on the engine with its counters checked (`register.checked_game`)
  and checked for the 20 Hz tap spacing.
* The tree is clean outside `experiments/035-20hz-search-probes`; 035's plan, protocol,
  seeds and this file are committed; 035's wiring check matched on this library; both
  stages need the gate matched on this very library, and the summaries re-check that the
  games' library, format, weights and search are the ones gated and declared.
* A stage interrupted part-way resumes from its partial file only if no commit happened
  since it started (the file's header holds the code versions); otherwise it is replayed.
* Every record names the native library's sha256 and ABI version and both code versions.

## Reported, not part of the rule

Points by band (paired), P(130), P(230), P(320), P(39), deaths by 10-line step, Tetrises /
singles / Tetris share by band, the boards at 29's and 39's entry, seconds a game.

## Cost

Gate ~15-20 min; development ~3 h (500 games at ~610 s, 28 at once); held-out ~6 h. About
9-10 hours unattended.
