# Experiment 020 - a learned value network

Status: stopped 2026-10-31 at step 3 by the plan's stop rule: V0, then step 3's one fix (V1),
both far below 015's agent (V0 on 60 held-back training seeds only, as a scratch check; V1 on
dev seeds 0-99). Plan in `plan.md`; no `predeclared.md`, no held-out run. The bar stays 017's
agent: 1,800k, 393.0 lines on 012's held-out seeds.

## Question

Can a small network that reads the raw board (231 inputs -> 256 -> 128 -> 1), trained
on the points 015's games went on to score after each board, replace the hand-built board
score inside the search?

## Answer

**No, not trained this way.** The network predicts the future score about as well as 013's
linear model, and the agent that picks moves by it collapses:

| dev seeds 0-99 | net (V1, 015's best 2 moves) | 015's agent | 017's agent |
| --- | --- | --- | --- |
| mean score | 209k | 1,323k | 1,810k |
| mean lines | 118.4 | 361.4 | 393.6 |
| Tetris rate | 11.2% | 37.3% | 48.5% |
| seconds per game | 0.8 | 1.6 | 470 |

Paired against 015: -1,113k (95% CI -1,183k to -1,040k), lower on 99 of 100 seeds.

## What happened, step by step

* **Data (step 1).** 20,000 games of 015's agent on fresh training seeds, 17.4M boards, mean
  1,141k and 335.9 lines, 66% reaching level 39. Exploration was 1%, not the plan's 5%: on 60
  scratch seeds 5% let only 1 game in 60 reach level 39 (015 alone: 48), so the data would
  have had almost no killscreen boards.
* **V0 fit (step 2).** Validation error (whole held-back games, in level-18 Tetrises squared)
  103.4 against 104.7 for 013's linear model and 118.1 for "lines left x points per line": only
  1.2% below the linear model, so the step 2 stop rule (10%) fired. The probe of 013's failure
  passed (Tetris-ready stacks 8, 12, 16 high lose value, faster at 39+). Both models stall at
  R^2 0.67: one game's future is so noisy that this error cannot tell a good value from a weak
  one. The owner chose to play V0 anyway.
* **V0 plays (step 3, scratch).** These checks ran on 60 held-back round-0 training seeds
  and are not kept in files; V0's ran on the step 3 code before it was committed (`8f57909`).
  015's agent there: 1,360k and 366.4 lines. V0's search with no prefilter topped out within a
  few pieces: in one traced game it built towers in columns 8-9 that its value rated *higher*
  (50 -> 56 Tetrises), boards 015 never makes. The plan's prefilter (015's search keeps its best
  k placements, the network picks among them) did not save it: k = 2 gave 112k and 90 lines,
  k = 4, 8 and 12 gave 12k, 6k and 3k. In six traced k = 2 games it cleared 10-128 singles and
  0-3 Tetrises before topping out. So even choosing between 015's own two best moves, the
  network chose worse than 015.
* **The one fix: more data (round 1).** 10,000 games by the V0 + prefilter-2 agent itself
  (mean 88k, 69 lines, 2.1M boards), so the network sees where its choices lead; V1 refitted
  on rounds 0 + 1. On the mixed check set V1's error is 17% below the linear model's, but only
  because the linear model fits the mixed data much worse (139.1, against 104.7 on round 0
  alone); the network's own error rose (115.4 against 103.4), and `fit_round1.json` records
  `stop: true`. Its probe fails at 39+ (V rises from 8 to 12 high). It played as badly: 174k
  and 114.3 lines on the 60 scratch seeds, and 209k on the dev seeds (the table above).

## What was learned

* **Predicting the future score is not the same as ranking moves.** Our reading (not
  measured directly): the search compares boards that differ by one piece, and the data held
  mostly the boards the playing agent chose (1% were random), never their alternatives, so
  the network's differences between sibling boards are mostly error, and taking the best of
  30-900 boards picks that error. The validation error, the probe and the C++/PyTorch match
  (within the test's 1e-4; 2e-6 in a scratch check on 695 boards) all looked fine; only games
  showed it.
* **Lines left carries most of the value.** "Lines left x points per line" alone reaches R^2
  0.629 on round 0's check games, against the network's 0.675 (`fit_round0.json`); V0 values
  each line still to come at about 2,900 points (a scratch finite difference on an empty
  board). The board's own worth, which is all a move choice turns on, is a small, noisy part
  of one game's future.
* **Fixing it needs targets that compare moves**, not more of the same: values of sibling
  boards from the same position (several rollouts each, as 016/017 do online), or training
  on the search's own choices (the policy side of BetaTetris's actor-critic). One round of
  self-play from a policy this weak only taught the network about very short games.
* The prefilter narrows only the current piece; the preview's placements are all valued, so
  the network's errors are likely still picked at the second ply. A prefilter there too was
  not tried.

## Record

* `config.json`, `seeds.json` (200 dev seeds `fallgorithm020/dev/v1`, training seeds
  `fallgorithm020/train/v0` and `/v1`; the 16-bit seeds hold only 30,720 distinct start states).
* `fit_round0.json`, `value_round0.bin` (V0, sha256 in the record); `fit_round1.json`,
  `value_round1.bin` (V1, on rounds 0 + 1).
* `dev_check_value_round1_k2_part0.json` (V1, prefilter 2) and `dev_baselines.json` (015's
  and 017's agents on dev seeds 0-99, reusable; 017's 1,810k is close to its held-out
  1,800k).
* Data in `runs/020-data/round0` and `round1` (not kept in git; each game is a pure function
  of its seed and settings). Round 0 was played on `9d04796`, round 1 on `7fdfaa8`, both clean;
  Block Stack `4d46782`, clean. No `result.json`, as for 018 and 019 (no held-out run).
* The fit and dev-check records say "working-tree" only because each writes an output file
  into this directory (the weights, `dev_baselines.json`) before it records the versions; the
  code was `9d04796` (fit 0) and `7fdfaa8` (fit 1, dev check) unchanged.
* Not in the `fallgorithm` launcher: like 018 and 019, there is no agent worth playing.

```
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment020 seeds
.venv/bin/python -m block_stack_ai.experiment020 collect                # ~16 min on 30 workers
.venv/bin/python -m block_stack_ai.experiment020 fit runs/020-data/round0   # ~4 min on one GPU
.venv/bin/python -m block_stack_ai.experiment020 seeds --round 1
.venv/bin/python -m block_stack_ai.experiment020 collect --round 1      # ~3 min
.venv/bin/python -m block_stack_ai.experiment020 fit runs/020-data/round0 runs/020-data/round1
.venv/bin/python -m block_stack_ai.experiment020 dev-check experiments/020-value-net/value_round1.bin --prefilter 2   # ~1 min; ~30 min more if dev_baselines.json is absent (017's games)
```

Fit 0 ran `9d04796`'s single-directory `fit` (its record has `data.directory`); today's code
writes `data.directories`. Fit 1 wrote `value_round1.bin` and `fit_round1.json` here; both were
moved to `runs/020-v1/` for the dev check (so its baselines record is clean) and moved back
afterwards (same sha256).

## Next

* **Learn from comparisons, not single futures:** fit the network to the rollout values of
  each candidate at a decision (018's data has them; 018's linear re-ranker failed, a network
  on the raw board was not tried), or to the search's choices directly.
* **Keep the network away from boards it has not seen:** prefilter the preview as well, or
  use the network only to break near-ties of 015's search.
* 019's candidates (a better rollout policy at 39+, the rollout return there) are untouched.
