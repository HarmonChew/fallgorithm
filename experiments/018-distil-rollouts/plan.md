# Experiment 018 - plan: distil the rollouts, retune, then rollouts on top

Status: stopped at step 2 (2026-10-31) by its stop rule: the fitted score lost more than
the search alone; see `notes.md`. Steps 3-5 were not run.

## Goal

Beat 017's agent (1,800k, 393.0 lines on 012's held-out seeds) clearly.

## Why this route

017's agent re-ranks the search's best placements by sampled rollouts: at 18-28 with the
preview known (016) and at the commit decision from 29 (017). That gained +439k over 015,
but costs ~493 s per game. The numbers are still 015's, tuned for an agent without
rollouts, and tuning them again (CEM, worth +100k to +370k in 012-015) needs ~4,600 games
per iteration: impossible at 8 minutes a game.

The rollouts only ever choose among the search's top 4 placements: a narrow, local job.
A cheap linear score fitted to the rollouts' choices may keep much of their gain at about
015's speed (~1.4 s per game). With it in the loop, CEM can retune the numbers; the final
agent then puts the full rollouts back on top of the retuned numbers.

013's lesson applies: a linear value of the whole board fitted to the score to come
extrapolated badly. Here the score only compares a handful of options the search already
rates highly, fitted to the differences between them, and is judged on how often it picks
what the rollouts pick.

## What changes (C++, off by default)

* **Data dump** (`fn_distil_game`): 017's agent plays as usual and, at every
  rollout-ranked decision, writes each candidate's features and the rollouts' mean
  return. The dump does not change the game (tested).
* **Re-rank agent** (`reach_plan_018`, ABI 12): the same agent with
  `w[model] . x(candidate)` in place of the rollouts, at the same decisions and over the
  same candidates. Three models: preview decisions (18-28), commit 29-38, commit 39+.
  `x` (27 numbers): whether it is the search's own choice, the search's total, whether
  that total includes 015's extra ply, whether it was -inf (some piece had no placement;
  the own value stands in), its own value, four cleared-rows flags, and value.hpp's 18
  board features. The search's choice
  wins ties, so all-zero weights play 015's game exactly (tested).
* **Fit** (Python): least squares of each candidate's mean on its features, both centred
  within the decision, per model (013's solver, tiny ridge).

## Steps

1. Harness and tests; committed before any data run.
2. **Collect and fit.** 017's agent on 200 fresh distil seeds (`fallgorithm018/distil/v1`,
   none of 012's or 013's seeds or their start-state twins); ~1 h on 30 workers. Fit on
   the first 160 games; on the other 40 report, per model, how often the score picks the
   rollouts' best and the mean return lost against it, next to the search alone.
   **Stop rule:** if the score loses about as much as the search alone, stop and record it.
3. **Dev check.** Re-rank agent against 015's agent on 013's first 100 dev seeds (paired,
   by band, s/game), with 016's and 017's dev means for reference.
4. **Retune.** CEM on 015's numbers with the re-rank agent in the loop (012's recipe:
   population 48, elite 12, 012's 96 training seeds; the re-rank weights fixed). Optional:
   collect and fit again with the retuned numbers if the score's picks drift.
5. **Rollouts on top.** 017's agent with the retuned numbers, dev check against 017's
   agent, then `predeclared.md` and the held-out run against 017's record.

## Question and success rule (fixed in `predeclared.md` before step 5's held-out run)

Proposed: does the final agent beat 017's agent on 012's 1,000 held-out seeds (95%
bootstrap CI of the paired mean score difference above 0)? Also reported: the re-rank
agent alone against 015 and 017, and seconds per game.
