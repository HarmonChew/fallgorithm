# Experiment 029 - notes: a level-39+ value taught by search (V39)

Plan: [plan.md](plan.md) (version 2, after an Opus plan review); held-out protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-03 ("follow your recommendation"). Code a206bbb (ABI 27, Opus-reviewed,
nothing serious); staged evaluation 5964e0c / e39a9f9 (Opus-reviewed, its fix made).
Runs: wiring d11f458, round 0 dda3fab, arm t1 ce667b8, arm t2 ff14da7, choice 6b48d2f,
screening b143d5b, development 6bbbf72, held-out f75414f (engine 4d46782).

## Question

At 39+ the record agent `e29_k4` (027, 2,132,514) survives long but clears mostly singles
(~94 lines, ~1 Tetris a game reaching 39); 017 builds Tetrises but tops out early. Both
score ~250k at 39+; BetaTetris ~380k. Can a second value network for the end (`V39`, every
decision from 320 lines), taught by its own search like 023 taught V, give survival *and*
Tetrises?

## Setup (as plan.md)

`V39` warm-started from `v15`; play before 320 lines is `e29_k4`'s exactly (wiring check:
no late network and `v15` as the late network both reproduce 027's games). Round 0:
`e29_k4` and `h39` (028) on 300 training seeds, 143,248 boards at 320-429 lines. Each
sweep: targets on all boards so far plus their children (own-play boards: lambda-returns
0.95 on the arm's backups; 017's boards and children: plain backup), teacher = the arm's
previous V39, then a probe (023's 100 probe seeds, paired against `e29_k4`), a ranking
check (024's 017-decision check at 39+, odd rollouts) and an own round of 200 games (1%
exploration from 300 lines). Arms: `t1` backup (one unknown piece), `t2` backup2 k 4 (two
unknown pieces).

## Sweeps (probe: 023's 100 probe seeds; `e29_k4` there: 2,115,586, 39+ given 39 251k, 95.3 lines / 1.06 Tetrises / 54.1 singles at 39+)

Both arms ran the maximum 8 sweeps: the probe mean was still rising at sweep 8 (the stop
rule never fired). The 39+ odd loss of `v15` is 23.97; every sweep was at or below it
(all eligible).

### Arm `t1` (one-piece backups)

| sweep | paired vs e29_k4 (95% CI) | 39+ given 39 | lines at 39+ | Tetrises at 39+ | singles at 39+ | Tetris share | line cap | 39+ odd loss |
|---|---|---|---|---|---|---|---|---|
| 1 | +11.6k (-8k, +30k) | 253k | 94.0 | 1.18 | 53.4 | 5.0% | 42% | 22.94 |
| 2 | +19.3k (-5k, +42k) | 248k | 89.2 | 1.28 | 50.0 | 5.8% | 49% | 22.52 |
| 3 | +48.3k (+28k, +68k) | 274k | 93.1 | 1.60 | 50.6 | 6.9% | 49% | 23.06 |
| 4 | +65.3k (+41k, +89k) | 291k | 91.4 | 2.04 | 49.8 | 8.9% | 50% | 22.94 |
| 5 | +62.9k (+38k, +88k) | 290k | 86.2 | 2.23 | 44.5 | 10.3% | 33% | 22.49 |
| 6 | +75.0k (+48k, +103k) | 299k | 83.1 | 2.54 | 40.2 | 12.2% | 36% | 22.27 |
| 7 | +107.3k (+78k, +136k) | 335k | 83.7 | 3.20 | 38.2 | 15.3% | 38% | 22.66 |
| 8 | +133.5k (+102k, +165k) | 357k | 80.8 | 3.83 | 34.7 | 19.0% | 33% | 22.01 |

Calibration on the arm's own rounds (V39's mean value / what the games went on to score, in Tetrises at level 18):

| round (V39 of sweep) | 320-339 | 340-359 | 360-379 | 380-399 | 400-419 | 420-439 |
|---|---|---|---|---|---|---|
| 1 | 9.3 / 9.8 | 9.2 / 8.1 | 8.9 / 6.4 | 8.2 / 4.9 | 7.3 / 3.0 | 5.0 / 1.3 |
| 2 | 9.6 / 10.0 | 9.3 / 8.2 | 9.0 / 6.5 | 8.4 / 4.6 | 7.1 / 2.7 | 4.7 / 1.0 |
| 3 | 9.9 / 10.7 | 9.4 / 8.5 | 9.1 / 6.6 | 8.2 / 4.7 | 6.8 / 2.8 | 4.3 / 1.2 |
| 4 | 10.2 / 11.2 | 9.5 / 8.9 | 9.1 / 7.0 | 8.5 / 5.3 | 6.9 / 3.1 | 4.1 / 1.3 |
| 5 | 10.5 / 11.7 | 9.6 / 8.9 | 9.0 / 6.6 | 8.3 / 4.9 | 6.4 / 2.7 | 3.5 / 1.0 |
| 6 | 10.6 / 11.9 | 9.5 / 9.9 | 9.2 / 8.0 | 8.4 / 5.8 | 6.5 / 3.0 | 3.3 / 1.1 |
| 7 | 10.8 / 12.5 | 9.6 / 10.3 | 9.2 / 8.2 | 7.9 / 5.8 | 6.0 / 3.2 | 3.1 / 1.0 |

### Arm `t2` (two-piece backups, k 4)

| sweep | paired vs e29_k4 (95% CI) | 39+ given 39 | lines at 39+ | Tetrises at 39+ | singles at 39+ | Tetris share | line cap | 39+ odd loss |
|---|---|---|---|---|---|---|---|---|
| 1 | -5.2k (-26k, +15k) | 238k | 90.2 | 1.03 | 51.6 | 4.6% | 36% | 23.14 |
| 2 | +39.6k (+16k, +62k) | 267k | 92.0 | 1.49 | 49.4 | 6.5% | 43% | 22.77 |
| 3 | +65.3k (+39k, +90k) | 290k | 87.8 | 2.22 | 45.9 | 10.1% | 44% | 22.72 |
| 4 | +81.6k (+54k, +108k) | 309k | 87.3 | 2.62 | 43.3 | 12.0% | 39% | 21.95 |
| 5 | +108.2k (+79k, +136k) | 335k | 83.2 | 3.28 | 37.8 | 15.8% | 38% | 21.37 |
| 6 | +164.7k (+130k, +198k) | 388k | 85.5 | 4.34 | 37.2 | 20.3% | 36% | 21.46 |
| 7 | +174.5k (+135k, +214k) | 403k | 82.1 | 4.80 | 33.3 | 23.4% | 38% | 20.99 |
| 8 | +178.6k (+139k, +219k) | 404k | 80.8 | 4.83 | 31.9 | 23.9% | 29% | 21.29 |

Calibration on the arm's own rounds (V39's mean value / what the games went on to score, in Tetrises at level 18):

| round (V39 of sweep) | 320-339 | 340-359 | 360-379 | 380-399 | 400-419 | 420-439 |
|---|---|---|---|---|---|---|
| 1 | 9.4 / 9.9 | 9.2 / 8.3 | 9.0 / 6.5 | 8.2 / 4.7 | 7.3 / 3.0 | 5.0 / 1.3 |
| 2 | 9.8 / 11.0 | 9.2 / 8.5 | 9.2 / 6.7 | 8.4 / 4.7 | 7.2 / 2.9 | 4.6 / 1.2 |
| 3 | 10.1 / 11.6 | 9.3 / 9.1 | 9.3 / 7.3 | 8.4 / 5.0 | 7.1 / 2.9 | 4.3 / 1.0 |
| 4 | 10.4 / 12.1 | 9.5 / 9.7 | 9.2 / 7.5 | 8.3 / 5.1 | 6.8 / 2.8 | 3.9 / 1.0 |
| 5 | 10.9 / 12.7 | 9.4 / 9.3 | 9.2 / 7.7 | 8.4 / 5.3 | 6.5 / 2.8 | 3.5 / 1.0 |
| 6 | 10.9 / 13.1 | 9.7 / 10.7 | 9.3 / 8.6 | 8.1 / 5.9 | 6.2 / 3.3 | 3.2 / 1.1 |
| 7 | 11.2 / 13.8 | 9.9 / 11.2 | 9.5 / 9.0 | 8.0 / 5.7 | 5.8 / 3.2 | 2.9 / 1.1 |

**Choice (`choose`): `t2` sweep 8** (`t2/value_sweep8.bin`), probe +178.6k (+139k,
+219k), odd loss 21.29. Picked as the best of 16 probes, so the probe overstates it
somewhat; the stages below are on fresh seeds.

## Screening (100 screening seeds, `screening.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,140,027 | 419.0 / 432 | 55% | 99.0% | 97.0% | 248k | 57.6% | 239 |
| 017 | 1,778,089 | 387.3 / 393 | 38% | 100.0% | 92.0% | 255k | 49.0% | 414 |
| **v39** | **2,322,643** | 405.2 / 429 | 29% | 99.0% | 96.0% | 411k | 64.0% | 225 |

Paired against `e29_k4`: **+182.6k (+138.8k, +224.9k)**, 75 wins / 22 losses / 3 ties;
by band 0, 0, +28.7k (29-38), +153.9k (39+). **Promoted** (bar +15k).

## Development (500 development seeds, `development.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,139,763 | 421.1 / 432 | 57% | 99.0% | 98.0% | 253k | 57.3% | 243 |
| 017 | 1,797,286 | 391.8 / 412 | 42% | 99.2% | 93.4% | 275k | 48.5% | 422 |
| **v39** | **2,306,109** | 404.1 / 429 | 27% | 99.0% | 97.6% | 394k | 64.1% | 231 |

Paired against `e29_k4`: **+166.3k (+147.0k, +185.5k)**, 376 / 116 / 8; by band 0, 0,
+30.4k (29-38), +136.0k (39+). Against 017: +508.8k (+474.9k, +541.9k), 39+ +127.9k.
**Kept** (>= +15k and CI above 0).

## Held-out (012's 1,000 seeds, `heldout.json`) - a new record

Before any `v39` game, 28 of 017's and 28 of `e29_k4`'s stored record games replayed input
for input on this build (56/56, `heldout_replay_check.json`).

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,799,692 | 393.0 / 415 | 46% | 99.5% | 93.8% | 277k | 48.2% | 493* |
| e29_k4 (record before) | 2,132,514 | 420.0 / 432 | 59% | 99.1% | 97.5% | 247k | 57.3% | 241* |
| **v39** | **2,315,238** | 406.2 / 429 | 32% | 99.1% | 97.4% | **404k** | 63.8% | 230 |

\* from their own runs.

Paired against `e29_k4` (the rule): **+182.7k (95% CI +170.0k, +195.7k)**, 775 wins /
201 losses / 24 ties. **The predeclared rule is met: `v39` (e29_k4 with t2 sweep 8's V39
from 320 lines) is the new record, 2,315,238.** Against 017: +515.5k (+492.3k, +538.6k),
927/1,000 wins.

By band against `e29_k4`: 0 (18), 0 (19-28), **+30.2k (29-38)**, **+152.5k (39+)**;
against 017: +114k, +88k, +180k, **+134k (+118k, +150k)** (was -19k for `e29_k4`).

Style at 39+ (games reaching 39, per game):

| | games reaching 39 | lines | Tetrises | singles | Tetris share of lines |
|---|---|---|---|---|---|
| e29_k4 | 975 | 93.9 | 1.04 | 53.6 | 4.5% |
| 017 | 938 | 70.8 | 2.69 | 32.0 | 15.2% |
| **v39** | 974 | 79.1 | **4.98** | 31.2 | **25.2%** |

## What we learned

* **Teaching the end its own value works: +183k on held-out**, three times 027's gain,
  with no extra search cost (230 s a game against 241 s). 39+ given reaching 39 went
  247k -> 404k: past 017 (277k) and past our BetaTetris estimate (~380k).
* **It is the style the plan aimed at: Tetrises without dying early.** At 39+ V39 makes
  5.0 Tetrises a game (e29_k4 1.0, 017 2.7) and half the singles, and still reaches 39 as
  often (97.4%). It clears fewer lines at 39+ (79 against 94) and hits the 430-line cap
  far less (32% against 59%): it now takes risks for points, and the risk pays.
* **+30k at 29-38 comes from lines 320-329** (the last ten lines of level 38, where V39
  already plays): setting up the 39+ stack before the speed-up.
* **Two-piece targets beat one-piece ones** (t2 +179k against t1 +133k at sweep 8, and
  t2 ahead from sweep 2 on), though after sweep 1 the arms also differ by their own
  rounds' boards.
* **The loop had not converged**: both arms still gained at sweep 8 (t2 +4k, t1 +27k at
  the last sweep), the plan's maximum. More sweeps may give more.
* **Ranking and calibration**: the 39+ ranking loss of 017's decisions fell from v15's 24.0
  to 21.0-21.3 (t2): V39 agrees a bit more with 017's rollouts at 39+. Calibration on own
  play is still off in a cap-shaped way: near the cap (400-439 lines) V39 overvalues
  boards about 2x (e.g. 2.9 against 1.1 Tetrises at 420-439), and at 320-339 it
  undervalues them (11.2 against 13.8). V39 does not know how many lines are left before
  the cap.

## Next candidates (not decided)

* Run the same loop longer (sweeps 9-16 of t2): the probe was still rising.
* Make V39 cap-aware (lines left to 430 as an input, or targets that end at the cap):
  calibration says the value is wrong exactly where the cap ends games.
* The same recipe one band down: a V29 for 230-319 lines (29-38 is where 027 gained most).
* Third unknown piece at 29-38 (027's idea), now on top of V39.
