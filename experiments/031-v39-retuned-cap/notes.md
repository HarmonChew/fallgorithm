# Experiment 031 - notes: V39 re-taught on v29's own games (031 stopped at `choose`; 031b a new record)

Plan: [plan.md](plan.md) (version 3, after two Codex reviews); held-out protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-05 ("Okay"). Code 4866a26 (Opus-reviewed, fixes made). Runs (chains
`runs/031-chain.sh` + `runs/031-eval-chain.sh`, logs `runs/031-chain.log`,
`runs/031-eval-chain.log`): wiring 6dd2065, round 0 bddd4a6, Phase A 457438b, loop
b0b5169, choice 28c3254 (none eligible). The loop crashed after sweep 8 trying to play an
own round 8 that had no seeds (the seed budget covered rounds 1-7); fixed in 054d131 (skip
it; Opus-reviewed) and resumed from the cached sweeps, nothing re-run.

## Question

030's record `v29` (2,346,354) stops building Tetris-ready wells near the 430-line cap, and
029's V39 overvalues the future there. Does re-teaching V39 on v29's own games (029's t2
recipe, warm start from 029's V39, V29 frozen) give more Tetrises at 39+ and a higher score?

## Outcome in one line

**031b (below) evaluated sweep 5 under an amended choice rule: a new record, 2,409,955 on
012's held-out seeds, +63.6k over `v29` (95% CI +46.1k, +81.6k).** 031 itself: **no
candidate was evaluated.** By the predeclared choice rule a sweep is eligible only if
its "commit 39+" ranking loss (odd rollouts) is no worse than 029's V39's (21.29). All 8
sweeps were worse (22.39 to 24.16), so `choose` picked none and the staged evaluation did
not start. On the probe, though, the re-taught networks played as hoped: more Tetrises at
39+ and +35-38k paired against `v29` at sweeps 5, 6 and 8.

## Phase A (offline audit on round 0, v29's own games; `phase_a.json`)

Re-searched commit decision agrees with the game 100% in every band.

| lines | decisions | a well placement offered | well placement taken | declined | future term decides the decline | I reaches a ready well |
|---|---|---|---|---|---|---|
| 330-339 | 7,618 | 20.7% | 86.2% | 217 | 31% | 98.2% |
| 340-349 | 9,513 | 18.3% | 90.1% | 173 | 39% | 100% |
| 350-359 | 9,024 | 20.8% | 90.9% | 171 | 45% | 99.3% |
| 360-369 | 8,705 | 21.0% | 90.7% | 169 | 45% | 99.9% |
| 370-379 | 8,582 | 23.9% | 90.2% | 201 | 50% | 99.4% |
| 380-389 | 8,143 | 21.8% | 91.9% | 144 | 34% | 99.4% |
| 390-399 | 7,905 | 19.6% | 92.8% | 112 | 41% | 98.9% |
| 400-409 | 7,088 | 17.6% | 92.6% | 92 | 37% | 99.3% |
| 410-419 | 6,505 | 13.6% | 92.4% | 67 | 40% | 96.7% |
| 420-429 | 9,398 | 12.2% | 91.9% | 93 | 71% | 97.6% |

Gate (a) for Phase D at 400-427: the future term decides 80 of 203 declines (39% < 50%):
most declines take a clear instead (reward higher in 122). **No Phase D.** V39 on these
boards (value / what the game went on to score, Tetrises at 18): 10.9 / 17.8 at 330-339,
9.8 / 11.1 at 370-379, 9.1 / 9.0 at 380-389, 6.6 / 5.4 at 400-409, 2.8 / 1.5 at 420-429.

## Sweeps (probe: 300 seeds; `v29` there 2,344,479; 39+: 5.26 Tetrises / 32.6 singles, 25.6% Tetris share; 44+: 2.79 Tetrises, 24.8%; P(39) 95.0%; line cap 39%; 39+ given 39 424k)

029's V39's odd loss on the 39+ decisions: **21.29** (the eligibility bar).

| sweep | paired vs v29 (95% CI) | 29-38 | 39+ | P(39) | 39+ given 39 | 39+ Tetrises / singles | 39+ Tetris share | 44+ Tetrises / share | line cap | odd loss 39+ |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | +12.0k (-18k, +43k) | +2.7k | +9.3k | 95.7% | 431k | 5.53 / 30.4 | 27.7% | 3.06 / 28.4% | 36% | 22.39 |
| 2 | +10.0k (-21k, +41k) | 0.0k | +10.0k | 96.0% | 430k | 5.62 / 30.4 | 28.6% | 3.19 / 30.3% | 32% | 23.46 |
| 3 | +18.3k (-13k, +50k) | 0.0k | +18.4k | 96.0% | 439k | 5.77 / 29.6 | 29.4% | 3.45 / 32.7% | 37% | 24.16 |
| 4 | +0.4k (-33k, +35k) | -0.1k | +0.4k | 95.0% | 425k | 5.63 / 28.4 | 29.9% | 3.59 / 34.3% | 32% | 24.09 |
| 5 | **+38.4k (+7k, +70k)** | -0.5k | +38.9k | 95.7% | 462k | 6.26 / 29.3 | 31.4% | 3.68 / 35.1% | 35% | 24.08 |
| 6 | +34.8k (+3k, +67k) | +0.4k | +34.4k | 95.7% | 457k | 6.17 / 29.5 | 31.4% | 3.81 / 35.3% | 37% | 24.10 |
| 7 | +19.6k (-12k, +50k) | -1.2k | +20.8k | 95.0% | 446k | 5.94 / 29.2 | 30.3% | 3.66 / 35.2% | 28% | 23.99 |
| 8 | +37.8k (+7k, +69k) | +0.6k | +37.2k | 95.3% | 462k | 6.09 / 30.2 | 29.8% | 3.62 / 34.2% | 32% | 23.78 |

The loop ran the maximum 8 sweeps (best at sweep 5, a near-tie at 8). The 29-38 band is ~0
by design (V29 frozen; differences there are only from different game paths). Probe numbers
are the best of 8 on the same 300 seeds, so they overstate the true gain.

**Choice (`choose`): none.** Every sweep's odd loss (22.4-24.2) is above V39's 21.29, so no
sweep was eligible; `experiment031eval screen` stopped with "no eligible V39'". No
screening, development or held-out games were played, and the record stays `v29`
2,346,354.

## Own rounds: board statistics (`roundK.json`; round 0 = v29, no exploration; rounds 1-7 = sweep K's V39', 1% exploration at 300-429)

Ready-well share of boards / Tetris share of lines cleared / Tetrises a game, by lines:

| round | games | mean score | 330-379 | 380-409 | 410-419 | 420-427 | 429 |
|---|---|---|---|---|---|---|---|
| 0 (v29) | 400 | 2,351,604 | 16.2 / 26.2 / 2.96 | 15.8 / 25.4 / 1.74 | 10.8 / 18.4 / 0.43 | 7.8 / 12.5 / 0.24 | 14.7 / 83.8 / 0.42 |
| 1 | 200 | 2,244,946 | 14.5 / 24.9 / 2.42 | 13.7 / 23.0 / 1.49 | 11.9 / 21.9 / 0.53 | 12.8 / 14.4 / 0.26 | 15.1 / 73.0 / 0.40 |
| 2 | 200 | 2,261,257 | 15.2 / 23.9 / 2.35 | 17.2 / 28.0 / 1.76 | 19.3 / 31.0 / 0.72 | 19.5 / 25.7 / 0.43 | 19.4 / 73.1 / 0.36 |
| 3 | 200 | 2,294,284 | 14.8 / 24.3 / 2.55 | 15.3 / 25.2 / 1.70 | 17.6 / 24.8 / 0.56 | 16.8 / 25.0 / 0.40 | 23.6 / 71.6 / 0.43 |
| 4 | 200 | 2,268,936 | 14.0 / 22.0 / 2.19 | 16.9 / 30.8 / 2.01 | 19.7 / 31.4 / 0.70 | 13.2 / 25.9 / 0.47 | 18.9 / 69.2 / 0.43 |
| 5 | 200 | 2,292,536 | 16.9 / 26.1 / 2.62 | 15.0 / 28.2 / 1.82 | 24.7 / 31.8 / 0.71 | 18.9 / 28.5 / 0.47 | 23.7 / 80.0 / 0.46 |
| 6 | 200 | 2,246,633 | 13.9 / 22.1 / 2.26 | 16.3 / 25.7 / 1.56 | 17.6 / 31.6 / 0.73 | 18.2 / 31.9 / 0.54 | 17.8 / 67.6 / 0.33 |
| 7 | 200 | 2,292,195 | 14.7 / 23.5 / 2.29 | 15.5 / 23.2 / 1.53 | 20.5 / 36.2 / 0.84 | 23.0 / 41.2 / 0.68 | 23.5 / 81.7 / 0.44 |

(Rounds 1-7 are on different seeds from round 0 and use exploration, so their mean scores
are not comparable to it; the per-board shares are.) No round 8: no seeds were budgeted for
it (see the top).

Calibration (V39' / 029's V39 / what the games went on to score, Tetrises at 18):

| round | 320-329 | 330-339 | 360-369 | 380-389 | 400-409 | 410-419 | 420-429 |
|---|---|---|---|---|---|---|---|
| 1 | 12.8 / 12.3 / 15.5 | 10.6 / 10.1 / 13.7 | 10.1 / 9.7 / 11.0 | 8.8 / 8.5 / 8.7 | 6.5 / 6.5 / 5.7 | 4.7 / 4.8 / 3.7 | 2.5 / 2.7 / 1.6 |
| 3 | 13.7 / 12.4 / 17.6 | 11.6 / 10.4 / 14.9 | 10.8 / 9.8 / 11.3 | 9.2 / 8.7 / 8.7 | 5.8 / 5.8 / 5.2 | 4.1 / 4.3 / 3.5 | 2.2 / 2.5 / 1.7 |
| 5 | 14.5 / 12.4 / 16.6 | 12.3 / 10.4 / 13.7 | 11.1 / 9.6 / 11.0 | 9.5 / 8.8 / 8.9 | 6.2 / 6.2 / 5.9 | 4.2 / 4.4 / 3.8 | 2.1 / 2.4 / 1.9 |
| 7 | 15.1 / 12.3 / 16.1 | 12.7 / 10.2 / 13.6 | 11.6 / 9.8 / 11.4 | 9.5 / 8.7 / 9.0 | 5.7 / 5.8 / 5.8 | 4.2 / 4.4 / 4.2 | 2.2 / 2.6 / 1.8 |

Phase D gate (b) (C's choice still has a near-cap deficit) was not reached: there is no
choice, and gate (a) had already failed.

## What we learned

* **The re-taught V39 does what the plan aimed at in play.** Near the cap it builds and
  cashes more wells: on own rounds the ready-well share at 420-427 went 7.8% -> 13-23% and
  the Tetris share of lines there 12.5% -> 25-41%; on the probe 39+ Tetrises went 5.26 ->
  ~6.1-6.3 a game, 44+ Tetris share 25% -> 34-35%, singles 32.6 -> ~29-30, and 39+ given 39
  424k -> 457-462k at sweeps 5-8.
* **Its values got closer to the truth.** The late overvaluation is mostly gone (420-429:
  2.0-2.2 against an actual 1.8-1.9, where 029's V39 says 2.4-2.7) and the undervaluation at
  320-379 shrank (330-339: 12.7 against 13.6, V39 10.2).
* **But it fails the ranking check, and by the rule that ends the experiment.** On 029's
  "commit 39+" decisions (late boards from earlier agents' games, ranked by rollouts) every
  sweep ranks worse than V39 (22.4-24.2 against 21.3), worse already after sweep 1. The
  likely reason: those boards come from earlier agents' play, not v29's, and V39' has been
  re-fitted to v29's own stacks. The check guards against a network that probes well by luck;
  here it and the probe disagree, and the protocol fixed beforehand that the check wins.
* **The probe gain is plausible but unproven.** +38k (CI +7k, +69k) at sweep 5 is the best of
  8 on the same 300 seeds; 030's best probe (+50k) became +31k on held-out. A real gain of
  ~+15-30k at 39+ is consistent with these numbers, but only fresh seeds can show it.
* Phase A: v29 takes a well placement ~90% of the time it is offered; what drops near the cap
  is how often one is offered (21% -> 12%), and declines are mostly a clear worth more now,
  not the future term. Yet re-teaching V39 raised the ready-well share near the cap, so the
  value change seems to work earlier, through the stacks it builds, rather than through the
  final pick (not audited on the new rounds).

## Next candidates (not decided; the owner's call)

* **A follow-up run with an amended, predeclared eligibility check**: the ranking check
  rebuilt on v29's own late boards (rollout-ranked like 029's), or dropped in favour of the
  staged seeds, then screen sweep 5 (or 8) against `v29`. This is a new protocol, not a
  rescue of this one: it must be written down before any screening game.
* V19 for 19-28 (plan.md's "after 031").
* Cap-aware lambda ramp (Phase D) only with new evidence: Phase A says the future term is not
  what drives the declines.

## 031b: sweep 5 through the staged evaluation (`predeclared_031b.md`) - a new record

Owner's go-ahead 2026-11-06. `choose-b` (0f22fb7, `chosen_031b.json`) took the highest probe
with no ranking check: **sweep 5** (`value_sweep5.bin`, probe +38.4k, CI +7k to +70k). Arm
`v39r` = 030's record `v29` with sweep 5's V39' from 320 lines. Chain `runs/031b-eval-chain.sh`
(log `runs/031b-eval-chain.log`): screening 4e992a4, development 940d0a4, held-out a0ebea4.
Rule throughout: paired by seed against 030's stored `v29` games.

### Screening (100 screening seeds, `screening.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,140,027 | 419.0 / 432 | 55% | 99.0% | 97.0% | 248k | 57.6% | 239 |
| 017 | 1,778,089 | 387.3 / 393 | 38% | 100.0% | 92.0% | 255k | 49.0% | 414 |
| v39 | 2,322,643 | 405.2 / 429 | 29% | 99.0% | 96.0% | 411k | 64.0% | 225 |
| v29 | 2,375,740 | 407.3 / 429 | 31% | 99.0% | 97.0% | 419k | 65.1% | 224 |
| **v39r** | **2,441,804** | 409.7 / 429 | 42% | 99.0% | 97.0% | 484k | 66.0% | 241 |

Paired against `v29`: **+66.1k (+8.3k, +122.9k)**, 55 / 42 / 3; by band 0, 0, +3.5k (29-38),
+62.6k (39+). **Promoted** (bar +15k). Against `v39` +119.2k, `e29_k4` +301.8k, 017 +663.7k.

### Development (500 development seeds, `development.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,139,763 | 421.1 / 432 | 57% | 99.0% | 98.0% | 253k | 57.3% | 243 |
| 017 | 1,797,286 | 391.8 / 412 | 42% | 99.2% | 93.4% | 275k | 48.5% | 422 |
| v39 | 2,306,109 | 404.1 / 429 | 27% | 99.0% | 97.6% | 394k | 64.1% | 231 |
| v29 | 2,351,233 | 404.0 / 429 | 33% | 99.0% | 97.2% | 389k | 65.4% | 241 |
| **v39r** | **2,418,981** | 407.1 / 428 | 37% | 99.0% | 97.2% | 461k | 66.2% | 247 |

Paired against `v29`: **+67.7k (+43.7k, +92.4k)**, 303 / 185 / 12; by band 0, 0, -1.5k
(-4.2k, +1.1k) (29-38), **+69.3k (+45.3k, +94.2k) (39+)**. **Kept** (>= +15k and CI above
0). Against `v39` +112.9k, `e29_k4` +279.2k, 017 +621.7k.

### Held-out (012's 1,000 seeds, `heldout.json`) - a new record

Before any `v39r` game, 28 each of 017's, `e29_k4`'s, `v39`'s and `v29`'s stored record
games replayed input for input on this build (112/112, `heldout_replay_check.json`).

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,799,692 | 393.0 / 415 | 46% | 99.5% | 93.8% | 277k | 48.2% | 493* |
| e29_k4 | 2,132,514 | 420.0 / 432 | 59% | 99.1% | 97.5% | 247k | 57.3% | 241* |
| v39 | 2,315,238 | 406.2 / 429 | 32% | 99.1% | 97.4% | 404k | 63.8% | 230* |
| v29 (record before) | 2,346,354 | 403.1 / 429 | 32% | 99.1% | 96.8% | 390k | 65.5% | 239* |
| **v39r** | **2,409,955** | 406.0 / 427 | 34% | 99.1% | 96.7% | 458k | 66.3% | 238 |

\* from their own runs.

Paired against `v29` (the rule): **+63.6k (95% CI +46.1k, +81.6k)**, 601 wins / 371 losses /
28 ties; lines +2.9 (+0.2, +5.6). **The predeclared rule is met: `v39r` (v29 with 031's
sweep 5 V39' from 320 lines) is the new record, 2,409,955.** Against `v39`: +94.7k (+73.5k,
+115.7k); against `e29_k4`: +277.4k (+259.6k, +295.0k); against 017: +610.3k (+585.7k,
+635.6k), 943/1,000 wins.

By band against `v29`: 0 (18), 0 (19-28), -1.4k (-3.2k, +0.4k) (29-38), **+65.0k (+47.7k,
+82.6k) (39+)**.

Style (per game reaching the band):

| | 29-38: lines | Tetrises | singles | Tetris share | 39+: games | lines | Tetrises | singles | Tetris share | 44+: games | Tetrises | Tetris share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e29_k4 | 98.6 | 15.42 | 18.9 | 62.5% | 975 | 93.9 | 1.04 | 53.6 | 4.5% | 908 | 0.66 | 5.3% |
| 017 | 96.7 | 10.98 | 25.1 | 45.4% | 938 | 70.8 | 2.69 | 32.0 | 15.2% | 655 | 1.64 | 15.7% |
| v39 | 99.4 | 16.18 | 18.3 | 65.1% | 974 | 79.1 | 4.98 | 31.2 | 25.2% | 778 | 2.61 | 23.8% |
| v29 | 99.3 | 17.60 | 15.8 | 70.9% | 968 | 76.4 | 4.79 | 29.9 | 25.1% | 739 | 2.59 | 23.5% |
| **v39r** | 99.2 | 17.57 | 15.8 | 70.8% | 967 | 79.5 | **6.17** | 29.6 | **31.0%** | 802 | **3.65** | **34.8%** |

### What 031b learned

* **The probe was right and the ranking check was the wrong guard here.** +38k on the probe
  became +64-68k on every fresh stage (screening, development, held-out), all of it at 39+.
  The check ranked boards from earlier agents' games; on v29's own play the re-taught V39'
  is better. A future eligibility check should use the evaluated agent's own late boards.
* **It is the cap-aware play 031 aimed at.** At 39+ the record now makes 6.2 Tetrises a game
  (v29 4.8), Tetris share 31% (25%), near the cap (44+) 3.65 Tetrises and 35% share (2.6,
  23.5%), and survives as long (79.5 lines at 39+ against 76.4; P(39) unchanged, 29-38 play
  identical). 39+ given 39 rose 390k -> 458k (017 277k, BetaTetris ~380k).
* Same cost (238 s a game). Gap to the BetaTetris hybrid (~2.43M): ~20k, down from ~85k.

