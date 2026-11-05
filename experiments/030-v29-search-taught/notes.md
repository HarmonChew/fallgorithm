# Experiment 030 - notes: a level-29-38 value taught by search (V29)

Plan: [plan.md](plan.md) (version 2, after an Opus plan review); held-out protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-04 ("okay lets just work on V29"). Code 6f383ae (ABI 28, Opus-reviewed).
Runs (chain `runs/030-chain.sh`, log `runs/030-chain.log`): wiring ed274be, round 0
54fba75, loop 04435c4, choice b887cab, screening 0cecd3e, development da16644, held-out
14ede74 (engine 4d46782).

## Question

029's V39 fixed the end (39+ given 39: 404k, past our ~380k BetaTetris estimate), so the
gap to the BetaTetris hybrid (2.43M) is now before 39. Can a third network, V29, for every
decision at 230-319 lines (levels 29-38), taught with 029's winning recipe (arm t2,
two-piece backups), add points there on top of the record `v39`?

## Setup (as plan.md)

`v39` with V29 at 230-319 lines (v15 below 230, 029's V39 frozen from 320). Wiring check:
no mid network and v15 as the mid network both reproduce 029's `v39` games. Round 0: `v39`
on 400 training seeds, 88,478 boards from 230 lines (backup2 at 29-38: 0.09 s a board x
jobs). Each sweep: backup2 (k 4) targets under the previous V29, lambda-returns 0.95 on own
play handing over to backup2 under V39 at 320; children of a third of the boards (those at
320+ anchored to V39); warm-start fit. Then a probe (300 seeds, paired against `v39`
there: 2,303,371), the ranking check (024's 017 "commit 29-38" decisions below 320, odd
rollouts) and an own round of 200 games (1% exploration at 210-319 lines). Sweep s trains
on round 0 (minus 40 check seeds) and the last 3 rounds (~165k boards + ~485k children,
targets ~29 min a sweep).

## Sweeps (probe: 300 seeds; `v39` there 2,303,371, 29-38: 99.3 lines / 16.27 Tetrises / 18.3 singles / 65.5% Tetris share; P(39) 96.0%; 5.07 Tetrises at 39+)

The loop ran the maximum 10 sweeps (best probe at sweep 8, so the 3-without-a-new-best
rule had not fired). v15's odd loss on the 29-38 decisions below 320 is 15.00; every sweep
was below it (all eligible).

| sweep | paired vs v39 (95% CI) | 29-38 band | 39+ | P(39) | lines / Tetrises / singles at 29-38 | Tetris share 29-38 | Tetrises at 39+ | ended before 330 | line cap | odd loss <320 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | +10.6k (-21k, +42k) | +9.5k | +1.1k | 96.0% | 99.7 / 16.54 / 17.8 | 66.4% | 5.15 | 4.0% | 36% | 14.54 |
| 2 | -13.8k (-51k, +24k) | +4.5k | -18.3k | 94.3% | 98.4 / 16.46 / 17.3 | 66.9% | 4.88 | 5.7% | 30% | 14.47 |
| 3 | +6.9k (-29k, +43k) | +16.9k | -10.0k | 96.0% | 99.3 / 16.76 / 16.9 | 67.5% | 4.99 | 4.0% | 29% | 14.18 |
| 4 | +34.9k (+3k, +68k) | +26.6k | +8.2k | 96.0% | 99.2 / 17.07 / 16.4 | 68.8% | 5.29 | 4.0% | 32% | 14.16 |
| 5 | +14.8k (-21k, +51k) | +27.8k | -13.0k | 94.0% | 98.5 / 17.13 / 15.9 | 69.5% | 5.08 | 6.0% | 31% | 14.29 |
| 6 | +38.2k (+3k, +74k) | +48.9k | -10.7k | 94.7% | 99.4 / 17.70 / 15.4 | 71.2% | 4.91 | 5.3% | 37% | 14.11 |
| 7 | +23.3k (-12k, +59k) | +41.2k | -17.9k | 95.7% | 99.3 / 17.48 / 15.9 | 70.4% | 4.82 | 4.3% | 33% | 14.05 |
| **8** | **+50.1k (+14k, +87k)** | +37.2k | +12.9k | 95.0% | 99.2 / 17.40 / 16.0 | 70.1% | 5.40 | 5.0% | 36% | 13.96 |
| 9 | +5.9k (-32k, +44k) | +25.0k | -19.1k | 95.0% | 98.3 / 17.07 / 16.1 | 69.5% | 4.81 | 5.0% | 31% | 14.16 |
| 10 | +27.7k (-7k, +63k) | +35.8k | -8.2k | 96.0% | 99.1 / 17.32 / 16.2 | 69.9% | 5.01 | 4.0% | 32% | 14.35 |

The 29-38 band gain grew to ~+35-49k from sweep 6 on; the total moved with the noisy 39+
part (the 39+ CIs are about +-30k on 300 seeds).

Calibration on the own rounds (V29's mean value / what the games went on to score / the
target's own definition: points to 320 + V39 of the hand-over board; Tetrises at level 18):

| round (V29 of sweep) | 230-249 | 250-269 | 270-289 | 290-309 | 310-319 |
|---|---|---|---|---|---|
| 1 | 21.0 / 45.3 / 37.1 | 18.4 / 39.3 / 31.3 | 15.6 / 34.1 / 25.8 | 12.9 / 27.8 / 19.5 | 11.0 / 22.9 / 15.0 |
| 3 | 22.0 / 45.4 / 37.9 | 19.5 / 39.9 / 32.6 | 16.9 / 33.6 / 26.2 | 14.2 / 27.5 / 20.0 | 12.8 / 22.7 / 15.4 |
| 5 | 22.9 / 45.4 / 37.7 | 20.5 / 40.1 / 32.4 | 18.1 / 34.3 / 26.5 | 15.6 / 27.9 / 20.1 | 13.9 / 23.0 / 15.2 |
| 7 | 24.1 / 45.8 / 37.4 | 21.6 / 39.8 / 31.4 | 19.4 / 34.4 / 25.7 | 16.9 / 28.3 / 19.6 | 14.8 / 23.3 / 15.0 |
| 9 | 25.1 / 45.4 / 37.5 | 22.9 / 39.8 / 31.9 | 20.7 / 34.4 / 26.4 | 17.9 / 28.1 / 20.0 | 15.5 / 23.0 / 15.4 |

**Choice (`choose`): sweep 8** (`value_sweep8.bin`), probe +50.1k (+14k, +87k), odd loss
13.96. Best of 10 probes, so the probe overstates it; the stages below are on fresh seeds.

## Screening (100 screening seeds, `screening.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,140,027 | 419.0 / 432 | 55% | 99.0% | 97.0% | 248k | 57.6% | 239 |
| 017 | 1,778,089 | 387.3 / 393 | 38% | 100.0% | 92.0% | 255k | 49.0% | 414 |
| v39 | 2,322,643 | 405.2 / 429 | 29% | 99.0% | 96.0% | 411k | 64.0% | 225 |
| **v29** | **2,375,740** | 407.3 / 429 | 31% | 99.0% | 97.0% | 419k | 65.1% | 224 |

Paired against `v39`: **+53.1k (-14.0k, +117.9k)**, 58 wins / 41 losses / 1 tie; by band
0, 0, +41.3k (29-38), +11.8k (39+). **Promoted** (bar +15k).

## Development (500 development seeds, `development.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,139,763 | 421.1 / 432 | 57% | 99.0% | 98.0% | 253k | 57.3% | 243 |
| 017 | 1,797,286 | 391.8 / 412 | 42% | 99.2% | 93.4% | 275k | 48.5% | 422 |
| v39 | 2,306,109 | 404.1 / 429 | 27% | 99.0% | 97.6% | 394k | 64.1% | 231 |
| **v29** | **2,351,233** | 404.0 / 429 | 33% | 99.0% | 97.2% | 389k | 65.4% | 241 |

Paired against `v39`: **+45.1k (+16.8k, +73.3k)**, 277 / 218 / 5; by band 0, 0, **+50.9k
(+38.7k, +63.0k)** (29-38), -5.8k (-30.3k, +18.9k) (39+). **Kept** (>= +15k and CI above 0).

## Held-out (012's 1,000 seeds, `heldout.json`) - a new record

Before any `v29` game, 28 of 017's, 28 of `e29_k4`'s and 28 of `v39`'s stored record games
replayed input for input on this build (84/84, `heldout_replay_check.json`).

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,799,692 | 393.0 / 415 | 46% | 99.5% | 93.8% | 277k | 48.2% | 493* |
| e29_k4 | 2,132,514 | 420.0 / 432 | 59% | 99.1% | 97.5% | 247k | 57.3% | 241* |
| v39 (record before) | 2,315,238 | 406.2 / 429 | 32% | 99.1% | 97.4% | 404k | 63.8% | 230* |
| **v29** | **2,346,354** | 403.1 / 429 | 32% | 99.1% | 96.8% | 390k | 65.5% | 239 |

\* from their own runs.

Paired against `v39` (the rule): **+31.1k (95% CI +11.0k, +51.2k)**, 546 wins / 443
losses / 11 ties. **The predeclared rule is met: `v29` (v39 with sweep 8's V29 at 230-319
lines) is the new record, 2,346,354.** Against `e29_k4`: +213.8k (+196.8k, +230.5k);
against 017: +546.7k (+522.9k, +570.8k), 929/1,000 wins.

By band against `v39`: 0 (18), 0 (19-28), **+47.5k (+39.3k, +55.7k) (29-38)**, **-16.4k
(-33.8k, +0.8k) (39+)**.

Style (per game reaching the band):

| | 29-38: lines | Tetrises | singles | Tetris share | 39+: games | lines | Tetrises | singles | Tetris share |
|---|---|---|---|---|---|---|---|---|---|
| e29_k4 | 98.6 | 15.42 | 18.9 | 62.5% | 975 | 93.9 | 1.04 | 53.6 | 4.5% |
| 017 | 96.7 | 10.98 | 25.1 | 45.4% | 938 | 70.8 | 2.69 | 32.0 | 15.2% |
| v39 | 99.4 | 16.18 | 18.3 | 65.1% | 974 | 79.1 | 4.98 | 31.2 | 25.2% |
| **v29** | 99.3 | **17.60** | **15.8** | **70.9%** | 968 | 76.4 | 4.79 | 29.9 | 25.1% |

## What we learned

* **029's recipe works one band down too: +31k on held-out, a new record (2,346,354)**, at
  about the same cost (239 s a game against 230 s). Smaller than 029's +183k, as the plan
  expected (+20-40k): there was less to win at 29-38, where v15 was already good.
* **The gain is exactly where V29 plays: +47.5k at 29-38**, very consistent across stages
  (+41k screening, +51k development, +47k held-out, tight CIs). Same lines, more Tetrises
  (17.6 against 16.2 a game) and fewer singles (15.8 against 18.3): Tetris share of lines at
  29-38 went 65% -> 71%.
* **It costs some of that back at 39+: -16k** (CI just touching 0; -6k development). P(39)
  fell slightly (97.4% -> 96.8%) and 39+ given 39 went 404k -> 390k. Likely the hand-over:
  V29 enters 320 with stacks V39 was not trained on, and V39 is not re-tuned for them (a
  "not done on purpose" item in the plan). The probe showed the same pattern (39+ mostly
  negative on the sweeps).
* **The probe was noisy and peaked at sweep 8**, so the loop did not clearly converge: the
  band gain flattened at ~+35-49k from sweep 6, the total swung by the 39+ part.
* **V29 still undervalues 29-38 boards** against its own target definition, increasingly far
  from the hand-over (25 against 37 Tetrises at 230-249, right at 310-319), and is climbing
  only ~0.5 a sweep. The bootstrapped target moves slowly; the ranking (odd loss 15.0 ->
  14.0) is what improved.
* Gap to BetaTetris's hybrid (2.43M): ~85k, now split across 29-38 and the hand-over at 39.

## Next candidates (not decided)

* Re-tune V39 on v29's own games (a few 029-style sweeps with V29 frozen): win back the -16k
  at 39+ by teaching V39 the new hand-over stacks.
* Make V39 cap-aware (029's open item: it overvalues boards near the 430-line cap).
* Fix V29's offset: more sweeps, or a target with less bootstrap (higher lambda / longer
  rollouts) so values reach their definition.
* A V19 for 19-28 with the same recipe (the remaining v15 band below 230).
