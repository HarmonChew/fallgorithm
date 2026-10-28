# Experiment 012 - a full CEM run on the native reach_plan

Status: done 2026-10-29. Plan in `plan.md`, protocol in `predeclared.md` (committed
before training and before any held-out game).

## Question

With training about 100 times cheaper (Experiment 011), does a full CEM run on the
native `reach_plan` beat Experiment 009's numbers on fresh held-out seeds, at 30 Hz /
300 ms?

## Answer

**Yes, by a lot.** On 1,000 fresh held-out seeds the new numbers average **993k**
against **621k** for 009's numbers on the same seeds: a paired difference of **+373k**
(95% interval +360k to +386k). The new numbers score higher on 955 of the 1,000 seeds.
Lines go up too (+27.5, interval +23.6 to +31.3), and for the first time at 30 Hz /
300 ms games reach the 430-line cap (24%). The predeclared success rule is met.

| 1,000 held-out seeds | 012 (cem) | 009's numbers |
| --- | --- | --- |
| mean score | 993,477 | 620,613 |
| median score | 1,006,910 | 618,610 |
| p5 / p10 / p90 score | 661k / 737k / 1,229k | 481k / 509k / 741k |
| mean lines | 363.7 | 336.1 |
| p5 / p10 / median / p90 lines | 249 / 270 / 367 / 430 | 330 / 331 / 336 / 350 |
| score per line | 2,732 | 1,846 |
| Tetris rate (lines as Tetrises) | 22.8% | 11.2% |
| top-outs | 75.9% | 100% |
| reached level 29 / 39 | 99.3% / 82.0% | 99.7% / 95.9% |
| reached the line cap | 24.1% | 0% |

Where games end (held-out):

| | before 29 | levels 29-38 | 39-42 | 43+ (died) | line cap |
| --- | --- | --- | --- | --- | --- |
| 012 | 7 | 173 | 332 | 247 | 241 |
| 009's numbers | 3 | 38 | 941 | 18 | 0 |

On Experiment 008's 300 seeds (secondary, against 011's retained record) the picture
is the same: +380k mean score (interval +356k to +404k), +32.5 lines, 288 of 300
higher.

For scale (different piece generator and seeds, as noted in 008, so this shows scale
only): BetaTetris's hybrid averages 2.43M and 399.9 lines in this format. The gap
in lines has roughly halved (64 to 36). The gap in score is still more than 2x.

## What the training found

The CEM mean moved well away from 009's numbers. The biggest changes:

* `survival_level` 29 -> **37** and `survival_budget` 6 -> 2: keep building for
  Tetrises until level 37 instead of switching to safe play at 29.
* `build_tetrises` 11.3 -> 14.8 and `build_holes` -3.9 -> -7.4: value Tetrises more,
  and punish holes much harder while building.
* `drought_bound` 9 -> 14 and `height_budget` 9 -> 10: wait longer for an I piece
  and allow a taller stack.
* In the SPEND phase, transitions and edge depth matter more, and `spend_max_height`
  turns positive (+1.0). Any reading of that sign is a guess: these weights are
  correlated, and the CEM only sees the whole score.

So the agent plays a riskier, Tetris-heavy game through the level-29 to 38 band. That
trade-off shows up in the tail: 18% of games now die at levels 29-38 (against 4%), and
p5 lines fall from 330 to 249. The mean still gains, because Tetrises at level 29+ are
worth so much and a quarter of games now survive to the cap.

Training curve (mean score on the 96 training seeds): 009's numbers 602k; elite mean
551k at iteration 0 (wide spread), 893k at 9, 999k at 17, then flat at about 1.0-1.03M
up to iteration 29. The final mean scores 1,040k on the training seeds against 993k
held-out. The training figure is in-sample and inflated by choosing elites on noisy
fitness, so the gap (about 5%) is the expected fit to the training seeds, not a
problem.

## Why this worked when 009 was only modest

009 managed 4 iterations of 32 candidates on 24 seeds. This run did 30 iterations of
48 on 96 seeds: about 45 times the games (138,240 against 3,072), with 4 times the
seeds per candidate, so less noise. The curve
shows most of the gain came after iteration 4, so 009 had stopped while the CEM was
still climbing. The C++ port (011) was the enabler: 66 minutes for 138,000 training
games.

## Honest limits

* **The curve is flat, not finished.** From iteration 17 on the elite mean moved only
  about 3%, though the best sample was still rising (1,072k at iteration 29) and the
  5% spread floor limits fine-tuning. More iterations of the same 20 numbers would
  probably add little; my guess (not tested) is that the ceiling is the hand-built
  feature set and the 3-ply search.
* **Riskier tail.** p5 lines are worse than the baseline's, and 7 games ended before
  level 29. For score this is a good trade. If a later goal weighs consistency (like
  BetaTetris's "under 0.1% of games below 230 lines"), fitness should include it.
* **One format.** Trained and tested only at 30 Hz / 300 ms.
* **Fitness is mean score.** Line-cap games stop scoring at 430 lines, so the agent
  is not rewarded for anything past the cap.
* The 008-seed table is not independent evidence: those seeds have been looked at
  since 008. The 1,000 fresh seeds are the result.

## The Python copy (011's open question)

Decided in the plan: the C++ `reach_plan` is the agent from now on. The Python copy
stays frozen as the reference for 011's parity tests. This experiment changed only
numbers both copies take, so nothing was ported.

## Next

The learned value function (fitted value iteration from native self-play, C++ only).
Per this run, the bar is about 993k mean score and 364 lines on these 1,000 held-out
seeds, and the gap that matters is still the score: 2,732 per line against
BetaTetris's ~6,100.

## Reproduce

```sh
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment012 select-seeds   # seeds.json (deterministic)
.venv/bin/python -m block_stack_ai.experiment012 train          # about 66 minutes on 30 workers
.venv/bin/python -m block_stack_ai.experiment012 evaluate       # about 2 minutes (runs/ only)
.venv/bin/python -m block_stack_ai.experiment012 verify experiments/012-native-cem/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment012 summarize experiments/012-native-cem/records/run.json.gz
```

The held-out run was played from commit b7a4814 (clean tree; Block Stack 4d46782,
clean) on 30 workers in 124 s. Its temporary record was
`runs/20261028T181918497664Z-012/run.json.gz`; the retained copy is
`records/run.json.gz`. `summarize` verifies the record by replaying every game before
writing `result.json`.
