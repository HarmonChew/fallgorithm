# Experiment 032 - notes: V18, a level 18-28 value taught by search (stopped at screening)

Plan: [plan.md](plan.md) (version 2, Opus-reviewed); protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-06 ("okay follow your recommendations"). Chain `runs/032-chain.sh`, log
`runs/032-chain.log`: wiring aec8d95, round 0 4d81de4, loop (10 sweeps) 30341ad, choice
fe660d0, screening f9870f8. The chain then stopped with "develop failed: screening did not
promote v18". This is the predeclared rule working, not a crash.

## Question

The record `v39r` (2,409,955) is ~16k under the BetaTetris hybrid, and the whole gap is
before level 29 (-40k at 18, -66k at 19-28). Below 230 lines it still uses 023's `v15`.
Does a network taught by its own two-piece search (030's recipe one band down), V18, in
place of `v15` win those points back?

## Outcome in one line

**No new record. V18 did win points at 18-28 (+62k on screening, both bands' CIs above 0),
but the agent gave most of that back from level 29 on. Screening total +13.3k (CI -70k,
+97k) against `v39r`, under the +15k bar, so it was not promoted.** Development and
held-out were not played. The record stays `v39r` 2,409,955.

## Sweeps (probe: 500 fresh seeds, paired against `v39r`; `v39r` there 2,396,689: 18 616.5k, 19-28 569.1k, 29-38 779.2k, 39+ 431.8k; level 18 25.9 Tetrises / 16.1 singles; 19-28 17.9 / 15.4; board at 29's entry: aggregate height 41.1, holes 0.38)

| sweep | paired vs v39r (95% CI) | 18 | 19-28 | 29-38 | 39+ | P(29) | under 230 | Tetrises 18 / 19-28 | singles 18 | 29 entry agg. height / holes | odd loss 18-28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | -1,341.9k (-1,435k, -1,246k) | -189.8k | -372.6k | -500.3k | -279.1k | 34.8% | 65.2% | 17.5 / 12.5 | 18.9 | 28.4 / 0.54 | 7.32 |
| 2 | -30.7k (-77k, +14k) | +7.6k | -12.8k | -11.5k | -14.1k | 98.0% | 2.0% | 26.3 / 17.8 | 15.3 | 34.0 / 0.68 | 7.62 |
| 3 | +2.5k (-39k, +45k) | +16.6k | -0.4k | -6.2k | -7.5k | 98.6% | 1.4% | 26.7 / 18.1 | 14.8 | 34.7 / 0.62 | 7.46 |
| 4 | -6.2k (-50k, +36k) | +15.5k | +2.2k | -13.8k | -10.1k | 98.2% | 1.8% | 26.7 / 18.2 | 14.5 | 36.8 / 0.57 | 7.49 |
| 5 | +15.4k (-29k, +58k) | +21.6k | +18.5k | -15.9k | -8.9k | 98.0% | 2.0% | 27.0 / 18.9 | 13.6 | 38.3 / 0.43 | 6.84 |
| 6 | +56.1k (+12k, +100k) | +26.7k | +34.6k | -7.3k | +2.2k | 98.6% | 1.4% | 27.3 / 19.4 | 13.0 | 40.1 / 0.38 | 6.75 |
| 7 | -109.4k (-173k, -46k) | +7.3k | -12.6k | -75.3k | -28.8k | 91.0% | 9.0% | 26.3 / 18.7 | 14.6 | 43.2 / 0.45 | 6.63 |
| 8 | +39.8k (-7k, +88k) | +27.5k | +27.2k | -19.5k | +4.6k | 97.2% | 2.8% | 27.3 / 19.2 | 12.7 | 53.4 / 0.68 | 6.56 |
| **9** | **+61.5k (+20k, +104k)** | +26.5k | +31.3k | -15.4k | +19.0k | 98.4% | 1.6% | 27.2 / 19.2 | 12.5 | 60.4 / 0.84 | 6.58 |
| 10 | +42.4k (-1k, +86k) | +29.4k | +34.1k | -25.2k | +4.0k | 98.8% | 1.2% | 27.4 / 19.3 | 12.5 | 65.3 / 1.09 | 6.47 |

Sweep 1 (warm start from `v15` on round 0's targets) collapsed: 65% of games topped out
before 230 lines. Sweep 2 recovered. The best probe came at sweep 9. Sweep 10 was not a new
best, and the stop rule (from sweep 5, 3 sweeps without a new best) was not met before the
maximum of 10. **Choice: sweep 9** (`value_sweep9.bin`, +61.5k). From sweep 5 on, V18 is
steadily ahead at 18 (+22k to +29k) and 19-28 (+19k to +35k): more Tetrises (27.2 vs 25.9 at
18, 19.2 vs 17.9 at 19-28) and fewer singles (12.5 vs 16.1 at 18). It is behind at 29-38 in
every sweep (-7k to -25k, sweep 7 -75k). Over the sweeps it hands V29 a taller and holier
stack at level 29's entry: aggregate height 41 -> 60-65, holes 0.38 -> 0.84-1.09. This is
030's hand-over problem one band lower: V29 was never taught on these stacks.

### Calibration (`roundK.json`; round K = sweep K's V18, 0.5% exploration; units: a Tetris at level 18 = 22,800 points)

V18's value minus its target's definition (points to the hand-over board plus V29's plain
value of it), by 20-line steps:

| round | 0-19 | 20-39 | 40-59 | 60-79 | 80-99 | 100-119 | 120-139 | 140-159 | 160-179 | 180-199 | 200-219 | 220-229 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | +22.3 | +21.2 | +21.9 | +18.7 | +16.3 | +8.0 | -1.4 | -6.8 | -6.2 | -5.8 | -4.2 | -3.0 |
| 2 | -18.9 | -16.6 | -15.4 | -13.9 | -12.9 | -11.4 | -10.3 | -8.7 | -7.2 | -5.8 | -4.0 | -2.3 |
| 3 | -19.3 | -17.5 | -15.8 | -14.4 | -13.1 | -11.6 | -10.2 | -9.1 | -7.4 | -6.0 | -3.8 | -1.8 |
| 4 | -18.2 | -16.6 | -15.4 | -13.6 | -12.7 | -11.5 | -9.9 | -8.2 | -6.6 | -5.6 | -3.3 | -1.3 |
| 5 | -18.7 | -16.9 | -15.2 | -14.1 | -12.7 | -10.9 | -9.7 | -8.1 | -6.5 | -5.4 | -3.4 | -1.1 |
| 6 | -19.3 | -18.1 | -16.6 | -15.4 | -14.2 | -12.9 | -11.3 | -9.4 | -7.4 | -5.6 | -2.9 | -0.7 |
| 7 | -14.6 | -13.7 | -12.9 | -11.7 | -11.6 | -10.8 | -10.1 | -8.9 | -7.2 | -5.5 | -2.8 | -0.5 |
| 8 | -17.6 | -15.8 | -14.2 | -13.1 | -11.3 | -10.0 | -9.2 | -7.6 | -5.5 | -4.0 | -1.8 | -0.0 |
| 9 | -19.2 | -17.4 | -15.7 | -13.9 | -12.7 | -11.0 | -9.5 | -8.1 | -6.0 | -4.1 | -1.7 | -0.0 |

V18 minus what the game actually went on to score is ~-28 to -30 at 220-229 and ~-45 at
0-19 in rounds 2-9. The extra ~-28 comes from V29's plain value of the hand-over board,
which undervalues the rest of the game (030 found the same).

**The preview bias showed up.** From round 2 on, V18 sits under its own target's definition
by a gap that grows steadily toward 0 lines: ~0 at 220-229, about -11 at 100-119 and about
-19 (~-430k points) at 0-19. That is about 0.08 Tetrises lost per line of distance, the
pattern the plan predicted for a preview-blind backup. It was the same size in every round
from 2 to 9. It did not compound from sweep to sweep. A uniform offset per line count does
not change decisions. What this table cannot show is whether the offset differs between
ragged and clean boards at the same line count, which is where the bias would cost moves.
Round 1 (sweep 1's broken network) overvalued early boards instead.

## Screening (100 screening seeds, `screening.json`)

| | mean score | mean / median lines | line cap | P(29) | P(39) | 39+ given 39 | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| 017 | 1,778,089 | 387.3 / 393 | 38% | 100.0% | 92.0% | 255k | 49.0% | 414 |
| v39 | 2,322,643 | 405.2 / 429 | 29% | 99.0% | 96.0% | 411k | 64.0% | 225 |
| v29 | 2,375,740 | 407.3 / 429 | 31% | 99.0% | 97.0% | 419k | 65.1% | 224 |
| v39r (record) | 2,441,804 | 409.7 / 429 | 42% | 99.0% | 97.0% | 484k | 66.0% | 241 |
| **v18** | **2,455,063** | 406.4 / 429 | 41% | 100.0% | 97.0% | 455k | 68.3% | 227 |

Paired against `v39r` (the rule): **+13.3k (95% CI -70.0k, +96.7k)**, 49 wins / 51 losses;
lines -3.3 (-13.2, +6.7). **Not promoted** (bar +15k). The per-seed score correlation is
0.00: V18's games split from the first piece, so pairing removes nothing (as plan.md
expected). Against `v29` +79.3k (-1.7k, +161.5k); `v39` +132.4k (+51.5k, +213.2k); 017
+677.0k (+600.8k, +754.7k), 96/100 wins.

By band against `v39r`:

| band | v18 | v39r | paired (95% CI) |
|---|---|---|---|
| 18 | 646.5k | 614.0k | **+32.5k (+22.0k, +43.1k)** |
| 19-28 | 600.7k | 571.2k | **+29.5k (+11.8k, +47.2k)** |
| 29-38 | 766.3k | 787.5k | -21.2k (-55.5k, +16.9k) |
| 39+ | 441.5k | 469.1k | -27.6k (-89.7k, +34.4k) |

Style (per game reaching the band):

| | 18: lines | Tetrises | singles | Tetris share | 19-28: lines | Tetrises | singles | Tetris share | 29-38: Tetrises | singles | share | 39+: games | Tetrises | singles | share | 44+: games | Tetrises | share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 017 | 131.3 | 20.04 | 22.9 | 61.1% | 99.8 | 14.33 | 19.4 | 57.4% | 10.75 | 24.6 | 44.8% | 92 | 2.50 | 29.7 | 15.3% | 61 | 1.46 | 16.0% |
| v39 | 131.1 | 25.73 | 16.7 | 78.5% | 99.9 | 17.96 | 15.4 | 71.9% | 16.44 | 17.8 | 66.0% | 96 | 5.10 | 30.5 | 25.9% | 78 | 2.59 | 24.1% |
| v29 | 131.1 | 25.73 | 16.7 | 78.5% | 99.9 | 17.96 | 15.4 | 71.9% | 17.75 | 15.9 | 71.8% | 97 | 5.23 | 32.1 | 25.9% | 81 | 2.54 | 23.2% |
| v39r | 131.1 | 25.73 | 16.7 | 78.5% | 99.9 | 17.96 | 15.4 | 71.9% | 17.85 | 15.5 | 72.4% | 97 | 6.49 | 31.4 | 31.0% | 84 | 3.83 | 34.9% |
| **v18** | 131.4 | **27.38** | **12.3** | **83.4%** | 100.1 | **19.13** | **12.6** | **76.4%** | 16.96 | 17.5 | 68.2% | 97 | 6.12 | 28.1 | 31.5% | 75 | 4.05 | 37.2% |

Board at level 29's entry: v18 max height 9.1, aggregate 62.0, holes 0.71; `v39r` 7.3,
44.9, 0.44.

### Development and held-out

Not played. By the predeclared rule (screening below +15k), the chain stopped before
development.

## What we learned

* **V18 plays levels 18-28 better.** +62k across 18 and 19-28 on screening, with both
  bands' CIs above 0. That is the same size as on the probe (+58k at sweep 9). It makes 1.2
  to 1.6 more Tetrises a band and 3-4 fewer singles, with no early top-outs on screening
  (P(29) 100%).
* **The gain does not reach the final score because of the hand-over.** V18 builds taller
  stacks to get those Tetrises and hands V29 boards it was never taught on: at 29's entry,
  aggregate height ~45 -> ~60 and holes ~0.4 -> ~0.7-0.8. 29-38 loses ~15-21k on the probe
  and on screening. 030 had the same seam one band higher (V29's stacks cost V39 -16k at
  39+). Screening's 39+ (-28k) is mostly noise (CI ±60k; probe +19k).
* **Measured odds matched the plan.** The best of 10 probes (+61.5k) overstated the chosen
  sweep, as predicted (~+25k). A true total near +30-40k fits both the probe and screening.
  The plan gave about 40% to pass every stage at +40k. With per-seed correlation ~0, 100
  screening games cannot resolve +15k.
* **The preview-blind backup bias is real and steady** (calibration above). It grows with
  distance from 230 lines and holds steady across sweeps.
* **Candidate follow-ups (not decided):**
  1. Re-teach V29 on the games of `v39r` with V18, so the 29-38 network learns the stacks
     V18 hands it. This is the step that worked for V39 in 031b.
  2. A preview-aware backup for V18 (the plan's follow-up for the bias).

## Cost

Round 0 ~1.2 h; 10 sweeps ~27 h (2026-11-06 17:35 -> 11-07 21:29); screening ~16 min
(227 s a game). The machine was shared with chess training on both GPUs.
