# Experiment 009 - learning the evaluation numbers with CEM

## Question

Can CEM-learned evaluation parameters raise `bench_plan`'s mean score at 30 Hz /
300 ms reaction on held-out seeds? (`predeclared.md`, written before training,
holds the protocol and the success rule.)

## Background in plain words

`bench_plan` (Experiment 008) picks where to put each piece by scoring the board it
would leave behind. The score is a sum of hand-picked weights times board features
(holes, how bumpy the surface is, how tall the stack is, a reward for a Tetris, and
so on). It averaged 320 lines but only 412,000 points, because its numbers were
tuned to survive, not to score: Tetrises (four lines at once) score far more than
single lines, and it gave them up.

Instead of picking the numbers by hand, this experiment lets a computer search for
them. The search is the **cross-entropy method (CEM)**:

1. Keep a bell-curve guess for every number: a centre (mean) and a width (spread).
   The centre starts at the hand-picked values.
2. Draw 32 candidate sets of numbers from that guess.
3. Play each candidate on 24 training games and record its average score.
4. Keep the best 8 (the "elite"). Make the new centre their average and the new
   width their spread, never letting a width shrink below 5% of its start.
5. Repeat. The guess narrows toward what scored well.

CEM does not need gradients, only scores, so it suits a game-playing agent that is
slow to run.

## What was tuned

`tuned_plan` is `bench_plan` with its numbers as parameters: 20 in all.
8 BUILD weights, 5 SPEND weights, 3 new SPEND features that started at weight 0
(row transitions, column transitions, edge depth, from Experiment 007), and 4 whole
numbers (height budget 8, survival budget 5, survival level 28, drought bound 9;
sampled as decimals, rounded, and clamped). With the default numbers it makes the same
choices and plays the same inputs as `bench_plan` (tests check both).

## Training

* 24 training seeds (`seeds.json`), none used by Experiments 000-008.
* Fitness = mean score over those 24 games at 30 Hz / 300 ms with a 430-line cap.
  The line cap stops fitness saturating, which was Experiment 007's problem.
* Population 32, elite 8, sampling seed 9.
* **Iterations: 4, not the predeclared 12.** An iteration took 17 minutes at the
  start and 35 minutes once candidates survived to long games (the machine was also
  shared with another job). 12 would have taken about 6 hours, so training was
  stopped after iteration 3 (index 3) to stay near the 2.5 hour budget (1.95 hours of
  iterations in the end). `predeclared.md` was left as written. Training started with 12 iterations (the
  `settings` in `training.json` are the copy taken at the start); `config.json` was
  set to 4 during the run, using training data only, and the run was resumed to
  write the final mean. The curve was still rising,
  so this is an under-trained result.

| Iteration | Best candidate | Elite mean | Population mean | Minutes |
|---|---|---|---|---|
| 0 | 461,488 | 364,671 | 150,013 | 16.8 |
| 1 | 566,051 | 458,932 | 302,747 | 29.7 |
| 2 | 626,173 | 540,866 | 435,224 | 35.6 |
| 3 | 610,949 | 582,649 | 505,247 | 34.7 |

`bench_plan` on the same 24 training seeds: 391,318 (309.0 lines). The final CEM mean
on them: 614,517 (334.0 lines). The training seeds are what the numbers were fitted
to, so the held-out result below is the real test. The population mean rose every
iteration (150k to 505k) mostly because the guess moved away from the poor candidates
that wide random sampling produces.

## Learned versus hand-picked numbers (final CEM mean)

| Parameter | Hand | Learned |
|---|---|---|
| BUILD tetrises | 8 | 11.28 |
| BUILD premature_clear | -1 | -1.29 |
| BUILD holes | -2 | -3.87 |
| BUILD aggregate_height | -0.5 | -0.38 |
| BUILD bumpiness | -0.5 | -0.61 |
| BUILD max_height | -1 | -1.09 |
| BUILD reserve | 6 | 7.10 |
| BUILD overflow | -2 | -0.92 |
| SPEND lines_cleared | 1 | 1.37 |
| SPEND holes | -1 | -1.27 |
| SPEND aggregate_height | -0.5 | -0.44 |
| SPEND bumpiness | -0.5 | -0.55 |
| SPEND max_height | -1 | -0.84 |
| SPEND row_transitions | 0 | -0.31 |
| SPEND column_transitions | 0 | -1.70 |
| SPEND edge_depth | 0 | -0.40 |
| height_budget | 8 | 9 |
| survival_budget | 5 | 6 |
| survival_level | 28 | 29 |
| drought_bound | 9 | 9 |

The unrounded values are in `final_params.json`. Reading them: a larger Tetris reward,
a heavier hole penalty in BUILD, a higher survival budget (so it holds the well longer
at high levels) and a strong new penalty on column transitions (a stack with few
changes between filled and empty going down each column, i.e. fewer holes and overhangs).
With one run and a still-wide spread (see `training.json`) I would not read much into
the small changes.

## Held-out results (Experiment 008's 300 seeds, 30 Hz / 300 ms)

| | bench_plan (008) | tuned_plan (009) |
|---|---|---|
| Mean score | 411,676 | 590,203 |
| Median score | 423,200 | 588,990 |
| Score p5 / p10 / p90 | 269,518 / 307,584 / 489,314 | 445,979 / 474,984 / 691,974 |
| Mean lines | 319.8 | 332.8 |
| Median lines | 331 | 335 |
| Lines p5 / p10 / p90 | 242.8 / 268.8 / 346.1 | 289.8 / 330.0 / 348.0 |
| Top-out rate | 100% | 100% |
| Reached level 29 | 97.0% | 100% |
| Reached level 39 | 69.7% | 92.7% |
| Reached the 430-line cap | 0% | 0% |
| Tetris rate (lines in Tetrises / all lines) | 3.2% | 10.2% |
| Tetrises per game | 2.6 | 8.5 |

Paired by seed, the score difference is +178,527 per game (95% bootstrap CI
165,371 to 191,225; 10,000 resamples, seed 9). The tuned agent scored higher on 286 of 300
seeds. The paired lines difference is +13.0 (CI 8.2 to 17.9).
BetaTetris's hybrid averages 2.43M and 399.9 lines for comparison.

Verification: `verify` replayed all 300 inputs on the engine and every result and
clear size matched. 008's clear sizes were recovered by replaying its inputs.

## Success rule

The predeclared rule: the paired mean score difference's 95% CI is entirely above 0.
It is (165,371 to 191,225), so **the rule is met**.

## What it shows

* Learning the evaluation numbers helped substantially: +43% score on held-out
  seeds, mostly by playing about three times as many Tetrises, plus a smaller
  gain in lines, and games lasted longer (level 39 reached in 92.7% of games
  against 69.7%; p5 score 270k to 446k), though every game still topped out.
* It did not fix the main limit. Every game still tops out (none reaches the
  430-line cap), mostly soon after level 39, and the score is a quarter of
  BetaTetris's. The evaluation numbers were part of the gap, not all of it.

## Honest limits

* One CEM run with one sampling seed; no estimate of run-to-run variation.
* Only 24 training seeds. The training fit (614k) is above the held-out score (590k),
  a small sign of fitting to those seeds, though far less than the gain.
* Training was cut from 12 to 4 iterations for time; the spread had not collapsed and
  the gain was probably not exhausted.
* The 20 parameters are only a few of the choices (the search depth, beam, and the
  structure of the well plan are unchanged). The BUILD and SPEND parts, the single
  well column, and the drought rule all remain hand-designed.
* The held-out seeds are the ones Experiment 008 reported, so they were seen before
  but not used in training or any choice made here.
* Movement-model simplifications inherited from 008 apply (tap timing and reaction
  are modelled, not measured on a person; no soft drop; one tap model for all pieces).
* The bootstrap interval covers sampling of seeds only, not training randomness.

## Reproduce

```sh
.venv/bin/python -m block_stack_ai.experiment009 select-seeds
.venv/bin/python -m block_stack_ai.experiment009 train --jobs 30
.venv/bin/python -m block_stack_ai.experiment009 evaluate --jobs 30
.venv/bin/python -m block_stack_ai.experiment009 verify experiments/009-cem-score/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment009 summarize experiments/009-cem-score/records/run.json.gz
```

`train` resumes from `training.json`. Watch a game with
`fallgorithm watch-record experiments/009-cem-score/records/run.json.gz --seed N --format 30hz-300ms`
or play a fresh one with `fallgorithm play-game --experiment 009`.
