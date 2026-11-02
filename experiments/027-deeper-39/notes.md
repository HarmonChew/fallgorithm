# Experiment 027 - notes: the record agent looks two unknown pieces deep at 39+

Plan: [plan.md](plan.md); held-out protocol: [predeclared.md](predeclared.md) (committed
with the plan, before any game). Owner's go-ahead 2026-11-02 ("Fix level 39+ ... let d3
look even deeper there"; handing over to 017 at 39 was the fallback). Code 02afd45
(Opus-reviewed, nothing serious), ABI 25. Every run recorded a clean commit (screening
d3e0897, development 382890f, held-out 7a714cd; engine 4d46782).

## Question

026's record agent `d3_d1b_k8` (2,071,704 held-out) is behind 017 only at level 39+:
231k given reaching 39 against 017's 277k (BetaTetris ~380k). Does one more unknown piece
of exact search at the commit decision close that gap?

## Arms (one change each; off = d3 input for input, `wiring_check.json`)

`set_deep2(level, k)`: from `level` on, the commit decision's best `k` placements by d3's
own value (points + `backup`) are rescored by points + `backup2` (two unknown pieces
before V, NES odds, best `k` placements of each next piece).

| arm | from level | k |
|---|---|---|
| `e39_k2` | 39 | 2 |
| `e39_k4` | 39 | 4 (the owner's request) |
| `e29_k4` | 29 | 4 |

k 8 was dropped before any screening game (3 probe games identical to k 4's at twice the
cost).

## Screening (100 screening seeds, `screening.json`)

| arm | mean | vs d3 (95% CI) | vs 017 (95% CI) | P(39) | 39+ given 39 | line cap | s/game | promoted |
|---|---|---|---|---|---|---|---|---|
| d3_d1b_k8 | 2,062k | - | +284k (+219k, +345k) | 97% | 218k | 43% | 118 | - |
| 017 | 1,778k | -284k | - | 92% | 255k | 38% | 414 | - |
| e39_k2 | 2,082k | +20k (+1k, +40k) | +304k (+241k, +364k) | 97% | 240k | 63% | 129 | yes |
| e39_k4 | 2,087k | +25k (+6k, +44k) | +308k (+244k, +369k) | 97% | 244k | 55% | 175 | yes |
| e29_k4 | 2,140k | +78k (+42k, +114k) | +362k (+299k, +419k) | 97% | 248k | 55% | 239 | yes |

## Development (500 development seeds, `development.json`)

| arm | mean | vs d3 (95% CI) | wins vs d3 | vs 017 (95% CI) | wins vs 017 | P(39) | 39+ given 39 | line cap | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|---|---|
| d3_d1b_k8 | 2,069k | - | - | +272k (+243k, +300k) | 427 | 95.4% | 225k | 46% | 57.0% | 119 |
| 017 | 1,797k | -272k | - | - | - | 93.4% | 275k | 42% | 48.5% | 422 |
| e39_k2 | 2,090k | +22k (+14k, +29k) | 286 | +293k (+265k, +322k) | 429 | 95.4% | 248k | 58% | 56.6% | 130 |
| e39_k4 | 2,088k | +19k (+11k, +27k) | 283 | +290k (+261k, +319k) | 430 | 95.4% | 245k | 59% | 56.6% | 174 |
| **e29_k4** | **2,140k** | **+71k (+55k, +87k)** | 341 | **+343k (+313k, +372k)** | 446 | 98.0% | 253k | 57% | 57.3% | 243 |

**Rule: every arm is kept (>= +15k and CI above 0 against d3); the chosen arm is
`e29_k4`.** Wins vs d3 leave out ties (27, 27, 5).

Paired by band (development):

| arm | vs d3: 29-38 | vs d3: 39+ | vs 017: 29-38 | vs 017: 39+ |
|---|---|---|---|---|
| d3_d1b_k8 | - | - | +110k | -41k |
| e39_k2 | 0 | +22k | +110k | -20k |
| e39_k4 | 0 | +19k | +110k | -23k |
| e29_k4 | +38k | +33k | +148k | -8k |

(Bands 18 and 19-28 are 0 against d3 for every arm: the change starts at 29.)

## Held-out (012's 1,000 seeds, `heldout.json`) - a new record

Before any `e29_k4` game, 28 of 017's and 28 of d3's stored record games replayed input
for input on this build (56/56, `heldout_replay_check.json`).

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,799,692 | 393.0 / 415 | 46% | 99.5% | 93.8% | 277k | 48.2% | 493* |
| d3_d1b_k8 (record before) | 2,071,704 | 414.6 / 429 | 48% | 99.1% | 96.2% | 231k | 56.8% | 113* |
| **e29_k4** | **2,132,514** | 420.0 / 432 | 59% | 99.1% | 97.5% | 247k | 57.3% | 241 |

\* from their own runs.

Paired against d3_d1b_k8 (the rule): **+60.8k (95% CI +49.4k, +72.2k)**, 662/1,000 wins
(12 ties). **The predeclared rule is met: `e29_k4` is the new record, 2,132,514.**
Against 017: +332.8k (+312.7k, +352.5k), 900/1,000 wins.

By band against d3: 0 (18), 0 (19-28), **+41.7k (29-38)**, **+19.1k (39+)**; against
017: +114k, +88k, +150k, -19k (-30k, -7k).

## What we learned

* **Two unknown pieces at the commit from 29 is worth +61k on held-out** (development
  +71k, screening +78k: some shrinkage, but the interval stays well above 0). It costs
  ~2x the time (241 s a game against 113 s; still half of 017's).
* **Most of the gain is at 29-38, not 39+**: +42k against +19k on held-out (two thirds
  against one third). The owner's own arm (`e39_k4`, deeper search only at 39+) gave
  +19k on development; starting at 29 adds the 29-38 gain and also hands better boards
  to 39 (more games reach 39: 97.5% against 96.2%; on development 98.0% against 95.4%).
* **The 39+ gap to 017 is about one third closed on held-out**: 231k -> 247k given
  reaching 39, against 017's 277k (16k of a 46k gap; development looked better, 225k ->
  253k against 275k, 57%). Paired, 39+ went from -38k to -19k against 017. Against
  BetaTetris (~380k at 39+) the gap went from ~149k to ~132k: about 11% closed.
* **Width does not matter at 39+**: k 2 played as well as k 4 (+22k against +19k on
  development) at less cost; the gain is the extra piece of depth, not more candidates.
* The 430-line cap now binds in 59% of games (d3 48%, 017 46%), yet 017 still scores more
  at 39+ while reaching 39 less often. So the remaining 39+ gap is mostly points per line
  (Tetris-building at 39+), not survival (an inference from the summary numbers; the
  per-band Tetris rate is not recorded).

## Next candidates (not decided)

* Go deeper again from 29: a third unknown piece (top-k pruned), or `e29_k2` as a cheaper
  version of this record (k 2 matched k 4 at 39+).
* The fallback hybrid: `e29_k4` to 38, then 017 from 39 (017 is still +19k ahead at 39+
  on held-out; 017's rollout search is slower than d3's).
* Look at 39+ scoring per line: does V at 39+ know how many lines are left before the
  cap (a Tetris-or-nothing endgame)?
