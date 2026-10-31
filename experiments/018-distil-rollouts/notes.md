# Experiment 018 - distil the rollouts into a fast re-ranker

Status: stopped at step 2 (2026-10-31) by the plan's stop rule. Plan in `plan.md`, fit in
`rerank.json`. No dev check, retune or held-out run.

## Question

Can a linear score, fitted to 017's rollout choices, pick among the search's top 4
placements about as well as the rollouts, at about 015's speed?

## Answer

**No.** On the 40 checked games (of 200 fresh distil seeds, `fallgorithm018/distil/v1`;
fitted on the other 160), the fitted score picks worse than the search alone in every
decision kind:

| decisions (40 checked games) | count | search picks rollouts' best | score picks it | search's loss | score's loss |
| --- | --- | --- | --- | --- | --- |
| preview, 18-28 | 22,950 | 86.4% | 85.3% | 1.38 | 1.69 |
| commit, 29-38 | 9,758 | 74.8% | 74.1% | 8.77 | 9.51 |
| commit, 39+ | 7,937 | 76.3% | 71.0% | 7.93 | 12.21 |

(Loss: the rollouts' mean return of the rollouts' best minus that of the pick, per
decision.) On the fitted games themselves it is no better (a tie at 29-38, worse elsewhere;
`rerank.json`'s `fitted_games`), so this is not overfitting: the 27 features simply do not carry what the rollouts see.

## What was learned

* What the rollouts add is not a linear function of the settled board's features: the
  search's own total already holds most of it, and the rest depends on the pieces to come.
* So CEM with rollouts in the loop stays out of reach at ~8 minutes a game; the numbers
  stay 015's.

## Record

Data: `runs/20261030T155116071076Z-018-distil/data.jsonl.gz` (017's agent on the 200
distil seeds, mean score 1,812,796, on `2bcc863`, clean; not committed, it is large and
each game is a pure function of its seed). `rerank.json`:
`.venv/bin/python -m block_stack_ai.experiment018 fit <data>`.

## Next

Experiment 019: spend the rollouts where they pay (longer rollouts at 39+, rollouts at the
29-38 adjust decision).
