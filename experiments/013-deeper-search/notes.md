# Experiment 013 - deeper search, with the 20 numbers re-tuned for it

Status: done 2026-10-29. Plan in `plan.md`, protocol in `predeclared.md` (committed
before training and before any held-out game).

## Question

Does `reach_plan` with one more ply of lookahead at the adjust search, with its 20
numbers re-tuned for it by CEM, beat Experiment 012 on 012's 1,000 held-out seeds, at
30 Hz / 300 ms?

## Answer

**Yes.** The deep agent averages **1,138k** against **993k** for 012 on the same seeds:
a paired difference of **+144k** (95% interval +126k to +163k), higher on 674 of the
1,000 seeds. The predeclared success rule is met.

It gets there with more Tetrises, not more lines: the Tetris rate goes from 22.8% to
31.7% and score per line from 2,732 to 3,253, while mean lines *fall* by 13.8 (interval
-18.9 to -8.6) and fewer games reach the line cap.

| 1,000 held-out seeds | deep (013) | cem_extra_ply | cem (012) |
| --- | --- | --- | --- |
| mean score | **1,137,882** | 1,051,980 | 993,477 |
| median score | 1,159,500 | 1,069,310 | 1,006,910 |
| p5 / p10 / p90 score | 745k / 817k / 1,411k | 700k / 777k / 1,296k | 662k / 737k / 1,229k |
| mean lines | 349.8 | 363.0 | 363.7 |
| p5 / p10 / median / p90 lines | 243 / 261 / 344.5 / 430 | 247 / 276 / 364 / 430 | 249 / 270 / 367 / 430 |
| score per line | 3,253 | 2,898 | 2,732 |
| Tetris rate (lines as Tetrises) | 31.7% | 25.7% | 22.8% |
| singles per game | 120.7 | 141.6 | 149.6 |
| Tetrises per game | 27.7 | 23.4 | 20.7 |
| top-outs | 80.4% | 77.2% | 75.9% |
| reached level 29 / 39 | 98.9% / 74.0% | 99.2% / 82.0% | 99.3% / 82.0% |
| reached the line cap | 19.6% | 22.8% | 24.1% |

Paired differences (score; lines):

| | score | lines | higher on |
| --- | --- | --- | --- |
| deep - cem | +144k (+126k to +163k) | -13.8 (-18.9 to -8.6) | 674 / 1,000 |
| cem_extra_ply - cem | +59k (+41k to +76k) | -0.6 (-5.7 to +4.6) | 584 / 1,000 |
| deep - cem_extra_ply | +86k (+67k to +105k) | -13.2 (-18.5 to -8.0) | 626 / 1,000 |

So the gain splits roughly 40/60: the deeper search alone with 012's numbers gives
+59k at no cost in lines; re-tuning for it gives another +86k by trading lines for
Tetrises.

Where games end (held-out):

| | before 29 | levels 29-38 | 39-42 | 43+ (died) | line cap |
| --- | --- | --- | --- | --- | --- |
| deep | 11 | 249 | 375 | 169 | 196 |
| cem_extra_ply | 8 | 172 | 348 | 244 | 228 |
| cem | 7 | 173 | 332 | 247 | 241 |

## What the training found

The biggest changes from 012's numbers:

* `build_tetrises` 14.8 -> **25.3** and `build_holes` -7.4 -> **-11.8**: value a Tetris
  much more, and punish holes harder while building.
* `build_overflow` -2.1 -> -0.1: almost no extra penalty for building over the height
  budget.
* `survival_level` 37 -> 38: keep building one level longer.

With one more piece of lookahead the agent can see further whether a tall, Tetris-ready
stack will get its I piece in time, and CEM turned that into a greedier build. The cost
shows up where 012's did: more games die at levels 29-38 (249 against 173) and fewer
reach level 39 (74% against 82%). The mean still gains because the extra Tetrises at
levels 18-38 are worth more than the lines lost.

Training curve (elite mean on 012's 96 training seeds): 012's numbers with the extra ply
scored 1,062k before training; elite mean 731k at iteration 0 (wide spread), 1,093k at
7, 1,156k at 14, then about 1.16-1.18M from iteration 15 to 29. The final mean scores
1,175k on the training seeds against 1,138k held-out (in-sample, about 3% higher).
Training took 96 minutes (30 iterations, 138,240 games).

## Step 0 and the learned value

* **Depth check** (`depth_check.json`, 200 dev seeds): 012's numbers with the extra ply,
  983k -> 1,057k (+73k, interval +31k to +116k). The held-out result for the same agent
  (+59k) agrees.
* **Learned value** (`value_probe.json`, self-play seeds only): a linear value of 114
  weights (`native/value.hpp`) fitted to self-play outcomes never beat 012. Value agent
  mean score by round (thousands) for five settings (exploration rate, rounds kept,
  random starting pieces): (0, all, 0) 0 / 0 / 7 / 6; (0.05, 2, 0) 618 / 7 / 38 / 75;
  (0.05, all, 0) 618 / 7 / 106 / 452; (0.02, all, 0) 1 / 1 / 2 / 47; (0.01, all, 40)
  2 / 3 / 142 / 276. The cause is extrapolation: in 012's games a taller, Tetris-ready
  stack always meant more points, and a linear model carries that to the top of the
  board. The code stays as groundwork; a later attempt needs a model that does not
  extrapolate (a surface table, a nonlinear model, or re-ranking a search's top moves).

## A diagnostic after training (not part of this experiment's protocol)

While training ran, a throwaway script replayed 012's agent on the 200 dev seeds and
counted every clear by level band and phase. Per game: at levels 18-28 in the BUILD
phase the agent clears **60 singles** (against 13 Tetrises); only 21% of I pieces become
Tetrises at 18-28, 11% at 29-38 and none at 39+ (always SPEND). A likely reason is in the
numbers: a premature single costs `1.58 * 3 = 4.7` while removing a row's nine field cells
earns roughly `9 * 0.48 = 4.3` in aggregate height (before the smaller max-height and
well-reserve terms), so a single is nearly free in the BUILD formula. This points at the next experiment; the script will be committed with it.

## Honest limits

* One CEM run with one sampling seed; another seed could land a little higher or lower.
* The training-seed score (1,175k) is in-sample, about 3% above held-out.
* One format only (30 Hz / 300 ms, double killscreen, 430-line cap).
* The gain costs lines, level-39 reach and top-outs; a format scored on lines would rank
  the agents differently.
* The diagnostic is not yet backed by a committed script or data file.

## Next

The deep agent is the new bar: 1,138k and 349.8 lines on 012's held-out seeds. Score per
line, not survival, is the gap to BetaTetris, and the diagnostic says most lines go out
as singles while building. Candidates for 014: score clears by their real points
(level-scaled) so a single is no longer nearly free; let the agent go for Tetrises at
level 39+ (separate weights per level band instead of the hard SPEND switch); and the
NES randomizer's real piece odds in the unknown-piece average (an I follows an I about
1 time in 28, not 1 in 7). Start with the diagnostic committed and run on the deep agent.

## Scale

For scale (different piece generator and seeds, as noted in 008): BetaTetris's hybrid
averages 2.43M and 399.9 lines in this format. Score per line is now 3,253 against its
about 6,100.

## Reproduce

```sh
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment013 depth-check
.venv/bin/python -m block_stack_ai.experiment013 value-probe --explore 0.05 --keep 2 --start-max 0
.venv/bin/python -m block_stack_ai.experiment013 train
.venv/bin/python -m block_stack_ai.experiment013 evaluate
.venv/bin/python -m block_stack_ai.experiment013 verify experiments/013-deeper-search/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment013 summarize experiments/013-deeper-search/records/run.json.gz
```

Harness commit c7c38c8; training outputs c089952; the held-out record
(`records/run.json.gz`, from `runs/20261029T042213766041Z-013/`) was made from c089952
with a clean tree, 3,000 games in 186 s on 30 workers, each replayed on the Python
binding. `summarize` replays the whole record again before writing `result.json`.
