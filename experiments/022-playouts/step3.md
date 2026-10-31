# Experiment 022 step 3 - train on the playout scores

Status: started 2026-11-01 after step 0 stopped the direct playouts (owner: "push forward
to get experiment 22 done").

## Why

Step 0's playouts lost for two reasons we could not separate: noise (16 futures to the end
barely tell 4 moves apart) and bias (the futures are played by the fast agent, much weaker
than 017 at 39+). A network fitted to many decisions' playout scores averages the noise
away (021's network beat its own rollouts' noise offline). Bias is handled by repeating:
the network's agent plays the next round's playouts, a stronger policy each round
(policy iteration).

## A round

1. `experiment022 seeds N`: 400 fresh seeds (`fallgorithm022/collect/vN`).
2. `experiment022 collect N`: each game is 021's rank agent below level 39 (fast) and, from
   39, decides by 16 playouts per candidate placed by the round's playout network (round 1:
   021's `rank_pilot.bin`; round N: round N-1's killscreen network). Every 39+ decision's
   4 candidates are kept with their mean points (`runs/022-data/roundN`, resumable).
3. `experiment022 fit N`: one network (021's shape) on rounds 1..N's data, fitted to each
   candidate's mean minus its decision's average; checked on each round's last 20% of
   games against the playouts' best (`fit_roundN.json`, `killscreen_roundN.bin`).
4. `experiment022 dev-check-net N` on dev seeds 100-199: `017_ks` (017 below 39, the
   network at 39+ instead of rollouts) against 017 (1,840k), and `rank_ks` (the rank agent
   with it) against the rank agent.

## Rules

* Fit stop: the network's checked loss is not below the search's -> stop the round.
* Keeper: `017_ks` paired mean above 017 with CI above 0 -> confirm on dev 0-99 (paired
  mean above 0), then `predeclared.md` and the held-out run against 017's record.
* Next round: if `rank_ks` beats the rank agent (the policy got better) but `017_ks` does
  not beat 017, run round N+1 (its playouts use the better policy). Stop after round 3, or
  as soon as a round's `rank_ks` gain is not significant.
* Time on round seeds only; dev seeds only through `dev-check-net`.

## Cost

Collect ~2 h per round (30 workers); fit ~3 min on the GPU; dev check ~25 min.
