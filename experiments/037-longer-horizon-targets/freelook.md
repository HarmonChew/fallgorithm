# Experiment 037 - free look: what 036 left on the table (no new games but one diagnostic pair)

Done 2026-11-14 after 036, before 037's plan. Read-only on 036's stored data. Scripts in
`freelook/` (run with `PYTHONPATH=src` from the repository root; they write their outputs to
the current directory): `mid_deaths.py` (part 1; output `freelook/mid_deaths.json.gz`),
`a1.py`-`a7.py` (part 2). The only games played: seed 6572 under 036 stage 2's sweeps 2 and
6, to dump its boards.

## Part 1 - why v36 dies at 230-319 lines

012's 1,000 held-out seeds, `v36` against `v29r20d` (stored games replayed; 035's
`classify`).

| | reach 230 | die 230-319 | I drought / tall stack / low hole | 230 entry: agg height / max / holes | mean agg height at 230-319 |
|---|---|---|---|---|---|
| `v29r20d` | 997 | 28 | 15 / 2 / 11 | 40.0 / 6.8 / 0.24 | 47.4 |
| `v36` | 987 | 102 | 68 / 16 / 18 | 55.2 / 8.4 / 0.48 | 52.0 |

Death rate at 230-319 by the aggregate height at 230 lines:

| entry agg height | 0-35 | 35-45 | 45-55 | 55-65 | 65-80 | 80+ |
|---|---|---|---|---|---|---|
| `v29r20d` | 2.5% (444) | 2.8% (176) | 1.8% (163) | 1.9% (105) | 7.6% (66) | 4.7% (43) |
| `v36` | 9.0% (133) | 6.7% (225) | 7.6% (225) | 10.9% (137) | 13.6% (132) | 18.5% (135) |

* **The taller hand-over explains little.** `v36` dies 3-4x as often at every entry height.
  `v29r20d`'s rates on `v36`'s entry boards give ~33 deaths, not 102: the hand-over explains
  ~5 of the 74 extra deaths, V29's own play the rest. Paired by seed: 100 seeds where only
  `v36` dies there, 25 where only `v29r20d` does, 2 both.
* **Two thirds are I droughts:** 16.6 pieces without an I when the board is lost, the stack
  ~13.6 rows. Median death at 280 lines.
* **It is in every true-scale V29.** Deaths at 230-319 on 036's probe A (500 seeds):
  `v29r20d` 20, 034's sweep 10 (036 stage 1 sweep 0) 33, stage 1 sweeps 35-51, stage 3
  sweeps 43-63 (more with each sweep). Probe B: `v29r20d` 12, stage 1's choice (v15 below
  230) 31. Tetris share at 29-38 rose with it (53% -> 58-59%).
* **V29 under-prices risk, a little.** `v36`'s V29 against the actual rest of game on
  stage 3's round boards at 230-319 (245k boards): overall 0.6 Tetrises below actual; on
  boards with an I drought of 25+ +0.1, at max height 14-20 +0.2. Relative to safe boards it
  over-values long-drought and tall boards by ~0.3-0.9 Tetrises (7-20k points).
* With the true 20 Hz hand-over value (~3.8 Tetrises after 320, accurate) reaching 320 is
  worth little, so part of the extra risk is a priced trade. But a death there is costly:
  `v36`'s dying games average 1.56M against 1.98M for those reaching 320. Winning back the
  extra deaths without losing Tetrises is worth at most ~20-30k a game.

## Part 2 - why 036's stage 2 (V18@20) got worse after sweep 2

* **The decline is a growing tail of wrecked games.** Probe A games with 40+ singles at
  level 18 (each ~99 singles, 0 Tetrises at 18, final 0.2-0.5M): 032's V18 0, sweeps 1-6:
  0, 1, 4, 9, 16, **97** of 500. Without them, sweeps 2-6 score the same (~1.93M; sweep 6
  1.948M). Paired against sweep 2: sweep 5 -50k (-89k, -13k), sweep 6 -288k.
* **What one looks like** (seed 6572, sweep 6): 20 holes after 4 pieces, 37 after 12, still
  at 0 lines; then ~450 pieces of singles. Sweep 2 plays the same seed cleanly.
* **The network stops penalising garbage, one sweep at a time.** A 20-hole board at line 0
  against a clean one: -3.0 Tetrises under 032's V18, -1.3 under sweep 2, 0.0 under sweep 6.
* **The targets drive it.** Early (< 130 lines) played rows with 10+ holes, mean target
  against the actual rest of game: sweep 1 45.4 / 61.7, sweep 4 43.3 / 34.8, sweep 6
  **45.8 / 23.0**. Rows with 20+ holes grew 33 -> 14,489. The targets are bootstrapped
  (backup2 under the previous net, lambda-returns at 0.95, a horizon of ~20 pieces), and a
  garbage board's cost (~100 lines without a Tetris) shows only hundreds of pieces later.
  So each sweep inherits the previous net's mild penalty, which makes more garbage games,
  which make more over-valued garbage rows. Clean boards' targets are ~27 Tetrises too low
  at 0-9 lines (51 against ~78): the value range is compressed.
* **Not the cause:** ordinary choices (on 3,000 fixed boards every sweep agrees 86-88% with
  sweep 2, same single / Tetris rates); the uniform +0.27 a sweep value rise; exploration
  (the probes have none). **The checks could not see it:** garbage rows are < 1% of a
  10-line step, so the means did not move.
* Every stage 2 fit moved the net further from the new targets on the check boards (rms
  0.15 -> 0.24-0.26); stages 1 and 3 improved it. Stage 2's sweeps after the first add
  noise.
* **Stage 3's decline is different:** no wrecked-game tail (at most one game with 45+
  singles at 29-38), and small (sweep 5 against 1: -14.3k, CI -31.3k, +2.3k).

Confidence: high that the wrecked games are the whole stage 2 decline and that the garbage
penalty faded sweep by sweep (measured). Medium-high that the bootstrapped targets drive it
(consistent with every number, not tested by re-training).

## What the two parts share

Both are slow costs that a short-horizon bootstrapped target cannot see: a drought death
unfolds over 15-25 pieces at 230-319, and a garbage board at level 18 costs hundreds of
pieces later. In both, the network is relatively too kind to the risky boards. That is
037's question.
