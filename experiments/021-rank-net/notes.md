# Experiment 021 - a network that ranks the search's top moves

Status: steps 0-3 done 2026-10-31; milestone 1 met. Step 4 (what it unlocks) is next, chosen
with the owner. Plan in `plan.md`; no `predeclared.md` and no held-out run yet. The bar stays
017's agent: 1,800k, 393.0 lines on 012's held-out seeds.

## Question

Can a small network that reads each candidate's raw board (plus the search's own totals)
pick among the search's top moves the way 017's rollouts do, at the search's speed?

## Answer

**Partly, and enough to matter.** It beats 015's agent by about 200k a game on both halves of
020's dev seeds at the same speed, and gets about 40% of the way from 015 to 017:

| dev seeds | rank net (021) | 015's agent | 017's agent |
| --- | --- | --- | --- |
| 0-99: mean score | **1,532k** | 1,323k | 1,810k |
| 0-99: mean lines | 364.5 | 361.4 | 393.6 |
| 0-99: Tetris rate | 43.8% | 37.3% | 48.5% |
| 0-99: seconds per game | 1.5 | 1.6 | 470 |
| 100-199: mean score | **1,591k** | 1,385k | 1,840k |
| 100-199: mean lines | 374.3 | 374.5 | 398.6 |
| 100-199: seconds per game | 1.5 | 1.4 | 426 |

Paired against 015: +209k (95% CI +126k to +293k, higher on 76 of 100) on seeds 0-99, and
+206k (+137k to +277k, 74 of 100) on 100-199. Against 017: -278k and -249k (lower on 77 and
74 of 100).

## What happened, step by step

* **Data (step 1).** 300 games of 017's agent on the fresh distil seeds
  (`runs/021-data/pilot`, 4,639 s on 30 workers), mean 1,774k; 1.18M candidate rows. The
  first 240 games are fitted (237,804 decisions), the last 60 checked.
* **Fit (step 2).** 256 -> 128 -> 1, 30 epochs, 160 s on the GPU (`fit_pilot.json`,
  `rank_pilot.bin`). The checked games' loss was roughly flat over the last few checkpoints
  (39+ was lowest at step 12,537 of 13,930).
* **Offline check (step 2).** On the 60 checked games, average loss against the rollouts'
  best move (lower is better), and how often each picks it:

  | decision kind | decisions | search | **network** | even rollouts | picks best: search / network |
  | --- | --- | --- | --- | --- | --- |
  | preview 18-28 | 34,712 | 1.36 | **1.11** | 0.16 | 86.8% / 87.1% |
  | commit 29-38 | 14,110 | 8.11 | **5.96** | 2.44 | 75.3% / 77.4% |
  | commit 39+ | 10,259 | 8.79 | **5.91** | 1.92 | 76.3% / 75.6% |

  The stop rule (network below the search in all three kinds) passed: 18%, 27% and 33%
  lower. 018's linear re-ranker was worse than its search in all three (1.69 / 9.51 / 12.21
  against 1.38 / 8.77 / 7.93, on other checked games), so the raw board is what helps.
  Scored against the odd rollouts only, the network (1.29 / 8.45 / 7.71) matches or beats
  the even half of the rollouts at 29+ (0.64 / 10.04 / 7.91), but not at 18-28.
* **C++ check.** `native_max_difference` (C++ against PyTorch's float32 forward on the GPU,
  first 2,000 checked rows) is 3.4e-4, above the 1e-4 the test uses. It is float32 rounding.
  A one-off check (not saved) on the same rows against a float64 forward on the CPU: C++ is
  3.3e-4 off at most, PyTorch's own float32 forward 1.9e-4; this net's outputs reach +-558
  (the test's small net's stay small). The C++ net picked the same move as float64 in all
  506 decisions; the smallest gap between a decision's top two outputs was 0.085.
  (`fit_pilot.json` records the tree as dirty only because it writes `rank_pilot.bin` first.)
* **Dev check (step 3).** The table above. `dev_check_rank_pilot_part0.json` and `_part1`
  record the weights at `runs/021-aside/rank_pilot.bin` (moved there so the tree was clean;
  same sha256 as `rank_pilot.bin` here). Part 1 needed 015's and 017's games on seeds
  100-199 first, now in 020's `dev_baselines.json` (played on a clean tree); so part 1's
  own run records the tree as dirty, with only that file changed.

## What was learned

* **Ranking siblings works where predicting the future did not.** 020's value network,
  trained to predict the score to come, collapsed (209k); the same size of network trained
  only on differences between a decision's candidates beats the search.
* **The gain is in scoring, not survival.** Lines are unchanged against 015 while the
  Tetris rate rises from 37% to 44%; most of the extra points are at 29-38 (+133k and
  +118k). Fewer games reach the line cap (23% and 29% against 37% and 34%).
* **The gap to 017 is largest at 39+** (-107k and -112k of the -278k and -249k), where the
  network also picks the rollouts' best slightly less often than the search does.

## Step 4: the network inside 017's rollouts (stopped)

Plan in `step4.md`; code d551a36. 017's agent with the rank network re-ranking its rollouts'
own placements (the policy search's top 4), on dev seeds 100-199 against 017's games there
(`dev_check_rollouts_rank_pilot_all_part1.json`):

| dev seeds 100-199 | net in rollouts at 18-28 | net in rollouts at all levels | 017's agent |
| --- | --- | --- | --- |
| mean score | 1,776k | 1,807k | 1,840k |
| paired against 017 | -64k (CI -129k to +2k), 47 of 100 | -33k (-93k to +26k), 48 of 100 | |
| mean lines | 388.8 | 397.4 | 398.6 |
| seconds per game | 481 | 499 | 426 |

Neither is above 017, so step 4's stop rule fired. A better rollout policy did not make
better rollouts: our reading (not measured) is that a rollout's return is still summed by the
hand-built placement value over 10 pieces, and the network's moves are the ones that score
less on that sum now for more later, which a 10-piece rollout does not see.

## Step 4b: the network blended into 017's picks

The pilot's halves allow an offline test of a different use: pick by the even rollouts' mean
plus w times the network's output, judged on the odd rollouts (`blend_rank_pilot.json`).
The blend beats the 8 rollouts alone in every kind, on both halves of the checked games:

| odd-half loss | 8 rollouts alone | best blend | network alone |
| --- | --- | --- | --- |
| preview 18-28 | 0.636 | 0.578 (w 0.25) | 1.288 |
| commit 29-38 | 10.04 | 7.40 (w 2) | 8.45 |
| commit 39+ | 7.91 | 6.02 (w 1) | 7.71 |

017 averages 16 rollouts (half the noise), so the dev check plays both those weights
(`blend_full`) and half of them (`blend_half`), with no network inside the rollouts.
