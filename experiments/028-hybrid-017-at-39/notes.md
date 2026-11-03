# Experiment 028 - notes: 027's record agent hands over to 017 at level 39

Plan: [plan.md](plan.md); held-out protocol: [predeclared.md](predeclared.md) (committed
with the plan, before any game; not used). Owner's go-ahead 2026-11-03. Code 2448e2d
(Opus-reviewed, nothing serious), ABI 26. Every run recorded a clean commit.

**Result: not promoted at screening. 028 is a failure; nothing went on to development or
held-out.** The record stays 027's `e29_k4`, 2,132,514.

## Question

027's record agent `e29_k4` trails 017 at 39+ (held-out: 247k against 277k given reaching
39). The stored games showed why: at 39+ 017 builds 2.7 Tetrises a game, `e29_k4` 1.0
(mostly singles, but more lines). Does handing the 39+ play to 017 (`h39`: `e29_k4` to
38, 017 from 39) score more?

## Wiring (`wiring_check.json`, 9/9 matched)

Never switching reproduces 027's stored `e29_k4` games; switching at 0 reproduces 017's
registered games input for input; `h39` under a 320-line cap plays `e29_k4`'s game.

## Screening (100 screening seeds, `screening.json`)

| arm | mean | vs e29_k4 (95% CI) | wins vs e29_k4 | vs 017 (95% CI) | P(39) | 39+ given 39 | line cap | Tetris rate | s/game | promoted |
|---|---|---|---|---|---|---|---|---|---|---|
| e29_k4 | 2,140k | - | - | +362k (+299k, +419k) | 97% | 248k | 55% | 57.6% | 239 | - |
| 017 | 1,778k | -362k | - | - | 92% | 255k | 38% | 49.0% | 414 | - |
| h39 | 2,142k | **+1.8k (-31k, +36k)** | 48 (49 lower, 3 equal) | +364k (+296k, +429k) | 97% | 250k | 37% | 62.9% | 236 | **no** (bar +10k) |

All of the difference is at 39+ (the bands below are identical by construction).

At 39+, per game reaching 39 (screening; from the games' per-level stats):

| | lines | Tetrises | singles | Tetris share of lines | points | line cap | holes entering 39 |
|---|---|---|---|---|---|---|---|
| 017 alone | 66 | 2.50 | 30 | 15% | 255k | 41% | 0.53 |
| e29_k4 | 93 | 1.11 | 53 | 5% | 248k | 57% | 0.21 |
| h39 (017 on e29_k4's boards) | 65 | 2.40 | 30 | 15% | 250k | 38% | 0.21 |

## What we learned

* **017's Tetris play does transfer onto `e29_k4`'s boards**: from 39 on it makes 2.4
  Tetrises a game there, as on its own boards. But it also tops out as early as it does
  alone (65 lines at 39+ against `e29_k4`'s 93; line cap 38% against 57%).
* **The two styles score about the same at 39+**: Tetrises with early top-outs (017) and
  long survival with singles (`e29_k4`) both give ~250k given reaching 39 here. Swapping
  one for the other gains nothing (+1.8k, interval -31k to +36k).
* So neither agent is "better at 39+" in a way a hand-over can capture. The next gain has
  to do both at once: survive like `e29_k4` *and* build Tetrises like 017 (BetaTetris
  ~380k at 39+ does). That needs a better 39+ evaluation, not a different existing agent:
  e.g. teaching V at 39+ from search results or from 017's 39+ Tetris play (Direction
  Phase 3), or a 39+ objective that values Tetris readiness.
* Better boards entering 39 (0.21 holes against 017's own 0.53) did not make 017 survive
  longer at 39+; its top-outs come from its own 39+ play.
* Screening on 100 seeds is noisy at 39+ (sd of 39+ points ~87k); a real effect of
  +10-20k could hide in this interval, but the per-game numbers above show the mechanism
  (more Tetrises, fewer lines) cancelling out, not a small hidden gain.
