# Experiment 026 - notes: more search for the frozen V (Direction Phase 1)

Plan: [plan.md](plan.md) (approved 2026-11-02 for screening and development). Code
2d3b9d2, 681c307, 4a0619c (Opus-reviewed; D2 was redesigned after the review, before any
game: the first version kept the best k *pairs*, which mostly share one current
placement, so it could hardly change a choice). ABI 24. Every run recorded a clean
commit.

## Question

023's V agent (frozen `v15`) looks one piece ahead at the commit decision (the only
decision at 39+, most of them at 29-38) and two (current + preview) at the adjust. Does
the same V play better with one more piece of search?

## Arms (one search change each; off = V input for input, `wiring_check.json`)

* `d1a` / `d1b`: commit decision from level 39 / 29: points + `backup` (expectimax over
  the unknown next piece by the NES odds, its best placement by points + V) instead of
  points + V.
* `d2_k4` / `d2_k8`: adjust decision at 18-28: the best k current placements, each with
  its best k preview placements rescored with `backup` of the board both leave.
* `d3_d1b_k8`: the best promoted D1 with the best promoted D2 (the plan's rule).

## Screening (100 screening seeds, `screening.json`)

| arm | mean | vs V (95% CI) | vs 017 (95% CI) | P(39) | line cap | s/game | promoted |
|---|---|---|---|---|---|---|---|
| V | 1,676k | - | -102k | 80% | 21% | 3.7 | - |
| 017 | 1,778k | +102k | - | 92% | 38% | 414 | - |
| d1a | 1,728k | +52k (+31k, +73k) | -50k (-122k, +23k) | 80% | 40% | 13 | yes |
| d1b | 1,933k | +257k (+212k, +303k) | +155k (+89k, +220k) | 99% | 44% | 31 | yes |
| d2_k4 | 1,830k | +153k (+74k, +229k) | +52k (-33k, +130k) | 78% | 18% | 27 | yes |
| d2_k8 | 1,863k | +186k (+118k, +253k) | +85k (+18k, +149k) | 83% | 20% | 94 | yes |
| d3_d1b_k8 | 2,062k | +385k (+314k, +453k) | +284k (+219k, +345k) | 97% | 43% | 118 | yes |

## Development (500 development seeds, `development.json`)

| arm | mean | vs V (95% CI) | vs 017 (95% CI) | wins vs 017 | P(29) | P(39) | 39+ given 39 | line cap | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|---|---|
| V | 1,719k | - | -78k | 195 | 98.0% | 84.4% | 145k | 17% | 52.0% | 3.9 |
| 017 | 1,797k | +78k | - | - | 99.2% | 93.4% | 275k | 42% | 48.5% | 422 |
| d1a | 1,769k | +50k (+40k, +59k) | -28k (-60k, +4k) | 224 | 98.0% | 84.4% | 203k | 36% | 50.1% | 13 |
| d1b | 1,921k | +202k (+182k, +220k) | +124k (+94k, +154k) | 342 | 98.0% | 96.2% | 221k | 48% | 50.8% | 30 |
| d2_k4 | 1,856k | +137k (+105k, +167k) | +58k (+27k, +89k) | 300 | 98.6% | 83.0% | 156k | 20% | 58.3% | 27 |
| d2_k8 | 1,862k | +143k (+113k, +173k) | +65k (+34k, +95k) | 293 | 99.0% | 85.4% | 150k | 19% | 58.5% | 93 |
| **d3_d1b_k8** | **2,069k** | **+350k (+321k, +378k)** | **+272k (+243k, +300k)** | **427** | 99.0% | 95.4% | 225k | 46% | 57.0% | 118 |

**Rule: every arm is kept (>= +40k and CI above 0 against V); the chosen arm is
`d3_d1b_k8`.** Against 025's record hybrid `v_h29` on the same 500 seeds (1,852k): d3
+217k (95% CI +186k, +247k), 378/500 wins (computed after the rule, not part of it).

Paired against V by band (development):

| arm | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| d1a | 0 | 0 | 0 | +50k |
| d1b | 0 | 0 | +111k | +91k |
| d2_k8 | +79k | +53k | +4k | +6k |
| d3_d1b_k8 | +79k | +53k | +124k | +93k |

The two changes add up almost exactly (d1b +202k and d2_k8 +143k; together +350k).

## Bellman residual (`residual.json`, V's own boards from 20 screening games)

`backup(x) - V(x)` in points: mean +339 (18), +327 (19-28), +756 (29-38), -472 (39+);
sd 3.4k, 3.5k, 3.8k, 5.4k, against values of 1.08M, 703k, 328k, 171k. On average V agrees
with its own one-piece lookahead; board by board it is off by a few thousand points
(about 0.2 Tetris), most at 39+. The search gain comes from correcting those per-board
errors, not from a bias in V.

## What we learned

* **One more piece of exact search with the same V is worth +350k.** No training, no
  new network: V with a two-piece expectimax at the commit from level 29 and a deeper
  adjust at 18-28 beats 017 by +272k and 025's hybrid by +217k on development, at 118 s
  a game (017 ~450 s).
* **The biggest single gain is the commit decision from 29** (d1b, +202k at 30 s a
  game): V's weakness at 29+ was mostly its one-piece search, not V itself. It now
  reaches level 39 in 96% of games (V 84%, 017 93%).
* **At 39+ deeper V is still behind 017** (221-225k given reaching 39 against 275k), and
  d1a alone loses to 017 (-28k). The 39+ gap to BetaTetris (380k) remains the hardest part.
* d2 raises the Tetris rate (52% to 58%) and the early bands; k=8 is barely better than
  k=4 for 3.5x the time.
* Screening overstated d3 a little (+385k against +350k); the effects are large enough
  that it does not matter here.
* Direction Phase 1's gate ("about +40k, confirmed by the staged procedure") is passed
  on screening and development; there is no fresh confirmation set (025 used it).

## Held-out (012's 1,000 seeds, `heldout.json`) - a new record

Owner's go-ahead 2026-11-02 for a record attempt without a confirmation stage (no unused
seeds left). `predeclared.md` was committed before any game. Before any d3 game, 28 of
017's and 28 of 025's v_h29 stored record games replayed input for input on this build
(56/56, `heldout_replay_check.json`).

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,799,692 | 393.0 / 415 | 46% | 99.5% | 93.8% | 277k | 48.2% | 493* |
| v_h29 (record before) | 1,835,513 | 386.4 / 407 | 41% | 96.6% | 92.0% | 270k | 52.1% | 171* |
| **d3_d1b_k8** | **2,071,704** | 414.6 / 429 | 48% | 99.1% | 96.2% | 231k | 56.8% | 113 |

\* from their own runs.

Paired against v_h29 (the rule): **+236.2k (95% CI +211.9k, +259.9k)**, 799/1,000 wins.
**The predeclared rule is met: d3_d1b_k8 is the new record, 2,071,704.** Against 017:
+272.0k (+251.7k, +292.9k), 843/1,000 wins.

By band against v_h29: +84k (18), +58k (19-28), +120k (29-38), -26k (39+); against 017:
+114k, +88k, +108k, -38k. The held-out gain matches development (+217k against v_h29,
+272k against 017): no shrinkage this time. Early top-outs (before 29) fall from 34 to 9.

The one band where d3 is behind is 39+: 231k given reaching 39 against 017's 277k. That
is the clearest next target (BetaTetris ~380k at 39+).
