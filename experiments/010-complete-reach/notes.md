# Experiment 010 - complete reachability

## Question

`limits.py` gives each target placement one fixed route (rotate and shift as early as
the tap timers allow, give up if a press is blocked). Experiment 008 suspected this
misses placements that need waiting and moving late (slides under overhangs, tucks,
spins), most at high gravity, and that this causes the level-39 deaths. Does finding
*every* placement reachable under the same limits raise `tuned_plan`'s score and
survival, with Experiment 009's numbers unchanged? (`predeclared.md` was written before
the held-out run.)

## Timeline (added after review; predeclared.md is as first written)

* The 30-game timing wave (to decide whether all 300 seeds fit in the time budget) used
  the **first 30 of the 300 held-out seeds** (no other seeds). It finished at about
  15:13:29. I printed and read its summary before writing the success rule: reach_plan
  mean lines 332.0 and score 585,068 against 009's 326.5 and 577,219 on those 30 seeds.
  So the rule was written after seeing a small, unpaired-in-print look at held-out
  results for 10% of the seeds. The rule itself (CI of the paired score difference above
  0) is the same one 009 used and does not depend on those numbers, but the order is not
  clean.
* predeclared.md was saved at 15:13:42 and the evaluation was launched in the same shell
  command, seconds later (about 15:13:45; it finished at 15:37:40). Both were after the
  timing wave. The 30 timing games were thrown away; the reported run is a fresh full
  300 (the first 30 seeds were played again).
* Check on the seeds the timing wave never touched (added at review): on the 270
  held-out seeds after the first 30, the paired score difference is +17,918 with a
  bootstrap 95% CI of 3,054 to 32,386 (10,000 resamples, RNG seed 10), also entirely
  above 0. The success verdict does not depend on the 30 seeds seen early.

## The reach model (`src/block_stack_ai/reach.py`)

In plain words: instead of one script per target, on every frame the player may tap or
not, in any combination the timers allow. The same player as `limits.py`: a tap on a
timer must wait `tap_interval` frames, shift and rotate have separate timers, no soft
drop, no holding, gravity does the rest.

* Gravity does not depend on the player, so all live possibilities in one frame share
  the same row and gravity counter. A possibility is only (orientation, column, shift
  timer, rotate timer). The pieces' positions for one timer pair are the bits of one
  Python integer, so one frame is a few integer operations (shift bits, rotate bits, mask
  by "fits at this row"). A pose that cannot go down locks that frame.
* Blocked presses are never generated (they only waste the timer).
* It returns each distinct lock placement (orientation, x, y) once. The input sequence
  is built only when asked for, by walking backwards through the stored frames,
  preferring to idle late so presses come as early as possible. All sequences to one
  placement lock on the same frame (the row fixes it), so "shortest in frames" is
  automatic.
* Mid-flight start (the adjust step) works from the piece's pose, row, gravity counter,
  first-piece delay and tap timers, as `limits.reachable` does. Same function signature.
* Results are memoized per (board, piece, start state, gravity, tap interval) (LRU, 4096).

**Inputs during the entry delay (ARE) cannot help in this engine.** `Game::tick` only
counts the entry delay down. Shifts, rotations and DAS run in the active phase.
Carried between pieces: `previous_input` and `das_counter`. With fresh taps neither
matters (a fresh press always attempts and resets the counter). Holding a direction
through ARE could move the next piece on frame 0 only if a wall bump left the DAS
counter charged, and it would then repeat every 6 frames, slower than a 30 Hz tap (2
frames) or 15 Hz tap (4 frames); a tap can already move on frame 0. So no real
advantage from tapping early, and pieces start with idle timers (same as 008).
(Correction after review: the claim above is about ARE and plain holding only. See the
holding bullet in the limits; the `reach.py` docstring's statement that holding cannot
help is superseded by these notes.)

### Checked against the engine (`tests/test_reach_integration.py`)

Random boards (some tall), all seven pieces, levels 18/19/28/29/38/39/45, 30/15/12 Hz,
random first-piece delays and gravity counters: for every returned placement its masks
(then silence) lock the piece exactly there on the engine and the settled board and line
count match; the reach set contains the whole `limits.py` set (same rows); random legal
tap sequences on the engine never lock anywhere outside the reach set's boards; a
hand-built board (roof over columns 0-2, open row beneath) where a flat I reaches a
spot under the roof only by dropping past it and sliding left late is found, was not
found by `limits.py`, and works on the engine; a mid-flight test with running tap timers.

### Speed

Per call on random boards (40 per row, fresh cache for reach):

| level / tap | limits ms | reach ms | placements limits / reach |
| --- | --- | --- | --- |
| 18 / 30 Hz | 0.05 | 0.15 | 20.8 / 21.8 |
| 18 / 15 Hz | 0.06 | 0.31 | 23.8 / 25.6 |
| 29 / 30 Hz | 0.05 | 0.08 | 20.6 / 21.8 |
| 39 / 30 Hz | 0.06 | 0.06 | 17.8 / 18.1 |

(`limits.py` is fast because its scripts are cached; the first calls are slower.) One
decision (commit search plus adjust search, alone on the machine), 3-ply: tuned_plan 43 /
56 / 41 ms against reach_plan 68 / 68 / 46 ms at levels 18-28 / 29-38 / 39+. In the real
run (30 games at once) a game spent about 137 s deciding; 300 games took about 25 min
(reach_plan games take 130-145 s each against about the same for tuned_plan). No extra
speed work was needed.

## Autopsy (30 of 009's games, every 10th, last 10 spawns of each)

(`autopsy.json` has every row.)

* (Zero placements on the death piece is almost automatic at stack height about 20, so
  it says little by itself.) The **death piece** (last spawn): level 38.7 on average (28 of 30 died at levels 39-41: 20 at 39, 6 at 40, 2 at 41; two at
  29), stack height 19.9 of 20, 11.9 holes on average, and **0 placements under either
  model** in all 30 games. So the full search rescues nothing at the moment of death:
  the board is already lost.
* Looking back, average stack height over the last 10 spawns rises 12.4, 13.0, 13.7,
  14.4, 15.1, 16.1, 17.1, 18.5, 19.5, 19.9, with placements for the fixed-route model
  15.2 falling to 5.3 and then 3.1 two spawns before the end. Reach finds extra
  placements in 43 of the 300 windowed pieces (about 14%), but one that leaves a lower
  stack in only 5 of them (all within 6 to 4 spawns before death), and none in the last
  3 spawns.
* So these deaths were not caused by the fixed-route limitation (faster taps and
  holding were not tested). The stack is already about 12 high and holey
  ten pieces before the end; at that point the plan has too few safe placements, and
  the extra placements reach adds are usually not better.

## Held-out results (008's 300 seeds, 30 Hz / 300 ms, paired by seed against 009)

| | tuned_plan (009) | reach_plan (010) |
| --- | --- | --- |
| Mean score | 590,203 | 607,113 |
| Median score | 588,990 | 605,280 |
| Score p5 / p10 / p90 | 445,979 / 474,984 / 691,974 | 482,446 / 512,792 / 717,952 |
| Mean lines | 332.8 | 330.9 |
| Median lines | 335 | 335 |
| Lines p5 / p10 / p90 | 289.8 / 330.0 / 348.0 | 271.4 / 330.0 / 348.0 |
| Top-out rate | 100% | 100% |
| Reached level 29 / 39 / cap | 100% / 92.7% / 0% | 98.3% / 92.7% / 0% |
| Tetris rate | 10.2% | 11.2% |
| Tetrises per game | 8.5 | 9.3 |

Paired score difference +16,911 per game (95% bootstrap CI 3,191 to 30,499; 10,000
resamples, seed 9); reach_plan higher on 172 seeds, tuned_plan higher on 128.
Paired lines difference -1.9 (CI -6.4 to 2.4). `verify` replayed all 300 games on the
engine and every result and clear size matched.

Mean reachable placements per piece (on reach_plan's own boards): level 29, limits 23.26
against reach 23.27 (6,877 pieces); level 39+, 18.34 against 18.48 (12,208 pieces). On
009's boards: 22.92 / 22.93 and 18.47 / 18.59. Decision time: 0.163 s per piece on
average in the 30-process run (this includes both searches); 43-68 ms per search pair
alone (above).

## Success

The predeclared rule (paired mean score difference CI entirely above 0): **met**
(3,191 to 30,499).

## What it shows

* The gain is small: +2.9% score. The Tetris rate is higher (10.2% to 11.2%), which may
  be where the score comes from, but I did not measure that. Survival did not move. Lines, top-out and level-39 reach did not move (92.7% both).
* Reach finds only about 0.1 extra placement per piece (under 1%), even at 39+, and
  the death boards have none. The level-39 deaths in 009's games were not caused by the fixed-route limitation. The stack is already too high and too full of holes by then, which may point to the
  evaluation and the lookahead (not tested).
* reach_plan's own early deaths (5 before level 29, worse p5 lines) were not autopsied.
* The worse tail: 13 games ended below 250 lines (against 7 for 009;
  p5 lines 271 against 290) and 5 games died before level 29 (98.3% against 100%).
  Both p5 score and p10 score rose, so the extra score from Tetrises is bigger than
  the loss in the worst games, but the lines CI includes zero and the early deaths are
  a sign that extra late-timed placements carry risk (see limits).

## Honest limits

* One run; the score gain is small (CI lower end 3k, about 0.5%) and a paired lines
  difference near zero. The 009 parameters were tuned for the fixed-route model, so the
  learned numbers may not suit the larger set (not retrained).
* Late-press targets are executed from the commit plan until frame 18, then replanned
  from the real state. A target chosen at commit may be impossible after adjusting
  (the model handles that by replanning, but the fallback is the same as 008's).
* The reach model starts every piece with idle timers and no held button, as 008 does,
  and does not allow holding at all. Holding can beat the tap rate: a reviewer's
  brute-force search with holding found extra placements on 7 of 26 boards. A blocked
  press charges the DAS counter, so holding the direction then retries every frame
  without the tap timer, and a Left+Right chord moves right. These are excluded by the
  definition of the tap-limited player, not shown to be useless. The earlier claim that
  holding gives no advantage was wrong.
* The tap model allows pressing both a shift and a rotate each interval, left and right
  alternately each interval, with perfect timing; real play is less regular.
* The autopsy looks at 30 games and counts placements and resulting stack height only;
  "better" there means a lower stack, not a higher plan value.
* Where reach.py might differ from the engine: only via the engine behaviours covered by
  the tests above; an overlapped spawn (piece spawning into the stack) is treated as the
  engine does (a rescue by shift or rotation is possible, locking while overlapped is a
  top-out, not a placement).
* The decision-time figure under load is one number for both searches combined; the
  paired timing is on 522 sampled positions from the first 12 games.

## Reproduce

```sh
.venv/bin/python -m block_stack_ai.experiment010 evaluate --jobs 30     # about 25 minutes
.venv/bin/python -m block_stack_ai.experiment010 verify experiments/010-complete-reach/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment010 summarize experiments/010-complete-reach/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment010 autopsy
```
