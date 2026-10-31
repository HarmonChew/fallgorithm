# Experiment 021 step 4 - plan: the rank network as the rollout policy

Status: DRAFT 2026-10-31, awaiting the owner's review. The owner chose this branch of step 4
after step 3 (`notes.md`).

## Why

017's rollouts play each future with 015's search alone. The rank agent picks better moves
than that search (+206k on dev seeds 100-199) at the same speed, so rollouts played by it
should be better futures, giving the outer decision a better estimate of each candidate,
at about 017's cost (~430-470 s a game). If that agent beats 017, its games are better
targets for the next network: the improvement loop (play, fit, play with the new network).

## The catch: rollouts only make preview-known decisions

Inside a rollout every placement knows the next piece. The network learnt three kinds:
preview-known at 18-28, and commit (preview unknown) at 29-38 and 39+. So:

* **18-28 (016's rollouts):** the in-rollout decisions are exactly the kind the network
  learnt. No mismatch.
* **29+ (017's commit rollouts):** the in-rollout decisions are preview-known at 29+, a kind
  the network never saw (the real game plays them with the search alone, at the adjust
  step). Two ways to use it there, both tried:
  * **hide the preview:** score the candidates of the in-rollout search with the commit model
    (29-38 or 39+), the preview input left at 0. Its inputs are off-distribution (the
    search's totals come from a preview-known search), so it may help or hurt.
  * **search alone at 29+ inside rollouts** (017 as now), the network only at 18-28.

## Steps

0. **Code.** `RolloutSearcher` gets an optional rollout policy that re-ranks the policy
   search's top 4 with the rank network, the same way the rank agent does
   (`rollout_net_to_level`: the last level where rollouts use it; 28 = 18-28 only, 99 = all,
   with the preview hidden at 29+). A new `fn_rank_rollout_game` and a `dev-check-rollouts`
   command. Tests: network off -> byte-identical to 017's games; network on with no rollouts
   -> the rank agent's games.
1. **Dev check** on 020's dev seeds 100-199 (017 = 1,840k, unbiased for 017's settings), both
   variants (18-28 only; all levels), paired against 017. ~25 min each on 30 workers.
   **Stop** if neither is above 017 by its paired mean; then the notes record it and we go
   back to the owner (the other step 4 branch: the CEM retune).
2. **Confirm** the better variant on dev seeds 0-99 (017 = 1,810k).
3. **Round 1 data:** 300 games of the new agent on fresh seeds `fallgorithm021/distil/v2`,
   same dump (~1.5 h). Refit (pilot + round 1, the rank agent's settings) -> `rank_round1.bin`.
4. **Round 1 checks:** the fast rank agent with the round 1 network on dev 100-199 against the
   pilot network (1,591k), and the rollout agent with it against step 1's. A round that
   lifts neither ends the loop.
5. **Held-out** (012's 1,000 seeds, `predeclared.md` first) for the best agent that beats
   017 on dev. Bar 1,800k. ~2.5 h on 30 workers at 017's speed.

## Honest odds

The network beats the search on its own decisions, but most of 017's lead over 015 is at 39+,
where the matching in-rollout kind is the one the network never learnt. The 18-28-only
variant is the safe one and touches the smaller part of the gap (-40k to -57k a band at 18
and 19-28). If the preview-hidden variant fails at 29+, the next fix is a fourth kind: dump
the in-rollout 29+ decisions and train on them (round 1 data with rollouts at 29+).
