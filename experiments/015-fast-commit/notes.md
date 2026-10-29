# Experiment 015 - a deeper commit search at the fast levels

Status: done 2026-10-29. Plan in `plan.md`, protocol in `predeclared.md` (committed
before training and before any held-out game).

## Question

Does 014's agent with 013's extra ply added to the commit search from level 29 (beam 2),
with its 22 numbers re-tuned by CEM, beat Experiment 014 on 012's 1,000 held-out seeds,
at 30 Hz / 300 ms?

## Answer

**Yes.** The fast_deep agent averages **1,361k** against **1,261k** for 014 on the same
seeds: a paired difference of **+100k** (95% interval +78k to +122k), higher on 634 of
the 1,000 seeds. The predeclared success rule is met.

Most of it is the search, not the re-tuning. 014's own numbers with the commit
ply (points_ply) gain +84k (+68k to +101k). Re-tuning adds +16k on top, and its interval
(-8k to +39k) includes zero. The gain also comes with lines: +11.2 (+5.7 to +16.7), and
36% of games reach the line cap against 24%.

| 1,000 held-out seeds | fast_deep (015) | points_ply | points (014) |
| --- | --- | --- | --- |
| mean score | **1,360,503** | 1,344,953 | 1,260,573 |
| median score | 1,410,970 | 1,378,820 | 1,288,110 |
| p5 / p10 / p90 score | 839k / 992k / 1,650k | 836k / 988k / 1,641k | 827k / 949k / 1,525k |
| mean lines | 368.7 | 370.1 | 357.5 |
| p5 / p10 / median / p90 lines | 244 / 279 / 377.5 / 430 | 246 / 274 / 383 / 430 | 246 / 272 / 353 / 430 |
| score per line | 3,690 | 3,634 | 3,526 |
| Tetris rate (lines as Tetrises) | 37.3% | 36.4% | 36.0% |
| singles per game | 116.3 | 119.0 | 117.2 |
| Tetrises per game | 34.3 | 33.7 | 32.2 |
| top-outs | 64.1% | 64.1% | 75.8% |
| reached level 29 / 39 | 97.3% / 81.0% | 98.2% / 81.1% | 98.2% / 77.3% |
| reached the line cap | 35.9% | 35.9% | 24.2% |

Paired differences (score; lines):

| | score | lines | higher on |
| --- | --- | --- | --- |
| fast_deep - points | +100k (+78k to +122k) | +11.2 (+5.7 to +16.7) | 634 / 1,000 |
| points_ply - points | +84k (+68k to +101k) | +12.6 (+7.7 to +17.5) | 643 / 1,000 (21 equal) |
| fast_deep - points_ply | +16k (-8k to +39k) | -1.4 (-6.9 to +4.4) | 530 / 1,000 |

The 21 equal games end before or early in level 29 (18 before it, 3 at level 29),
where points_ply plays exactly 014's game.

Where games end (held-out):

| | before 29 | levels 29-38 | 39-42 | 43+ (died) | line cap |
| --- | --- | --- | --- | --- | --- |
| fast_deep | 27 | 163 | 281 | 170 | 359 |
| points_ply | 18 | 171 | 266 | 186 | 359 |
| points | 18 | 209 | 352 | 179 | 242 |

The deeper commit search mainly keeps games alive: 46 fewer deaths at 29-38 and 71
fewer at 39-42, so 117 more games reach the cap.

## Why it worked (step 0, dev seeds)

The agent decides each piece twice (`native/agent.hpp`): a commit search at the spawn
(the preview is not usable yet: one ply), and an adjust search at the reaction frame (the
preview plus 013's extra ply). At levels 29+ the piece usually locks before the reaction
frame. Share of pieces that reached their adjust search (`bands.json`, 014's agent):
99.9% at level 18, 97% at 19-28, **12.6% at 29-38 and 0% at 39+**. From level 29 the
agent was deciding two plies shallower than below it. 015 gives the commit search the
extra ply from level 29, for its two best options.

The depth check (`depth_check.json`, 014's numbers, 200 dev seeds) predicted the
untuned gain well: +107k (+70k to +143k) on dev against +84k held-out. Beam 4 was no
better (+104k) and slower. A killscreen budget of 4 still lost 70k with the deeper
search, so building at the double killscreen stays off.

## What the training found

* `clear_points` 16.5 -> **37.7**, and `spend_lines_cleared` 0.95 -> 2.05: clears are
  worth more again, in both phases. `clear_points` was still moving at iteration 29
  (final spread 2.1, well above its floor), as were `build_tetrises`,
  `spend_lines_cleared` and `drought_bound`.
* `build_tetrises` 33.6 -> 29.8 (the points term now carries more of a Tetris's value),
  `build_holes` -14.1 -> -15.3.
* `build_overflow` -0.01 -> **+1.29**: a small reward per row over the height budget.
* `survival_budget` 2 -> 3 (it only decides level 38), `drought_bound` 16 -> 18,
  `killscreen_budget` 2 -> 1 (raw 1.32, near the rounding edge): at 39+ the agent spends
  from an even lower stack.

Training curve (elite mean on 012's 96 training seeds): 014's numbers with the commit
ply scored 1,306k before training; elite mean 923k at iteration 0 (wide spread), 1,247k
at 4, 1,355k at 7, then 1.35-1.40M from iteration 8 to 29. The final mean scores 1,352k
on the training seeds against 1,361k held-out. Training took 113 minutes (30 iterations,
138,240 games).

## Where the points are now (dev seeds, `bands_fast_deep.json`)

Score through each band, per game, for 014, 014 with the commit ply, and 015, next to
BetaTetris's published hybrid (other seeds and randomizer, so only a rough guide):

| through level | points (014) | ply_beam2 | fast_deep (015) | BetaTetris |
| --- | --- | --- | --- | --- |
| 18 | 426k | 426k | 430k | 658k |
| 28 | 830k | 830k | 837k | 1,294k |
| 38 | 1,169k | 1,237k | 1,240k | 2,039k |
| whole game | 1,254k | 1,360k | 1,365k | 2,426k |

| per band (fast_deep) | 18 | 19-28 | 29-38 | 39+ |
| --- | --- | --- | --- | --- |
| adjust share | 99.9% | 97.2% | 14.8% | 0% |
| lines per game | 130.9 | 99.5 | 90.0 | 50.6 |
| Tetris share of lines | 48% | 45% | 31% | 3% |
| I pieces that become Tetrises | 34% | 32% | 22% | 2% |

The re-tuned agent plays much like the untuned one by band (at 39+ slightly fewer lines,
50.6 against 55.0, and more Tetrises, 3.2% against 1.6%); the held-out +16k
from re-tuning is within noise. The gap to BetaTetris is still spread over every band:
about 460k by level 28, another 340k at 29-38 and 260k at 39+.

## Honest limits

* One CEM run with one sampling seed. `clear_points` had not settled, and the re-tuning
  gain (+16k) is not distinguishable from zero.
* fast_deep may lose a little before level 29: 27 games end there against 18 for
  points_ply, on different seeds (within noise: sign test p about 0.23; dev bands 18-28
  are slightly higher). The greedier points term may cost some
  early safety; this experiment cannot tell.
* The commit ply is 013's greedy extra ply (each unknown piece's best placement, then the
  seven-piece average), not a full expectimax over two unknown pieces. Its beam is 2.
* Building at the double killscreen still does not pay (step 0's lever check); 39+ is 3%
  Tetrises against BetaTetris's roughly 35%.
* One format only (30 Hz / 300 ms, double killscreen, 430-line cap).

## Reproduce

```sh
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment015 bands --agents points,ply_beam2,ply_beam4  # step 0, renamed bands.json
.venv/bin/python -m block_stack_ai.experiment015 depth-check
.venv/bin/python -m block_stack_ai.experiment015 train              # ~113 min, 30 workers
.venv/bin/python -m block_stack_ai.experiment015 evaluate           # ~4 min
.venv/bin/python -m block_stack_ai.experiment015 summarize runs/<run>/run.json.gz
.venv/bin/python -m block_stack_ai.experiment015 bands --agents fast_deep
```

Code: harness `29c151a`; step 0 data and protocol `3d3e796`; training outputs
`ba09430`. The held-out record (`records/run.json.gz`, from
`runs/20261029T121807447857Z-015/`) names `ba09430`, clean, and Block Stack `4d46782`:
3,000 games in 218 s on 30 workers, each replayed on the Python binding. `summarize`
replays the whole record again before writing `result.json`.

## Next

The fast_deep agent is the new bar: 1,361k and 368.7 lines on 012's held-out seeds.
Candidates for 016:

* **Levels 18-28** hold the largest remaining gap (~460k by level 28) and already get
  the deep search, so the lever there is evaluation quality. A learned evaluation that
  only re-ranks the search's top few moves cannot pick a move the hand-tuned search
  rules out, so it cannot extrapolate the way 013's linear value did.
* **Height budgets from reachability**, as StackRabbit does (the tallest stack where a
  5-tap move still works at the current gravity), in place of tuned budgets. That would
  give each gravity band its own budget without new CEM numbers, and might make building
  at 39+ pay.
* **More commit search at 29+**: a full expectimax over the two unknown pieces for the
  top option or two, now that the greedy version is known to pay.
