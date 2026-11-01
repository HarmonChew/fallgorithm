# Experiment 022 - plan: score the killscreen by real points to the game's end

Status: chosen by the owner 2026-11-01 ("a better target"); step 0 done and its direct
playouts stopped the same day (`notes.md`: they lose to 017 on 11 of 12 probe games);
step 3 (train on the playout scores, `step3.md`) started the same day and stopped at
round 1's fit (the network's checked loss 0.448 is not below the search's 0.403; notes.md).
022 is closed: no dev check, no `predeclared.md`, no held-out run; the bar stays 017.

## Why

017 (1,800k) picks its level 29+ moves by 16 rollouts of 10 pieces each, scored by the
hand-built placement value. 021 showed that copying that score more closely never plays
better: the score itself is the cap. At level 39+ (double killscreen) a game has only
at most 100 lines (~250 pieces) left before it dies or reaches the 430-line cap, so we can afford to play
every rollout **to the end of the game** with the fast agent, and score it by **the real
points it earns**. Dying early then costs exactly the points it loses, nothing invented.

## The idea in one paragraph

At each level 39+ decision, 017's commit search proposes its best 4 placements. For each,
play 16 futures to the game's end: fresh pieces with the NES odds, each placed the way the
fast agent really places it at 39+ (the commit search with the preview hidden, from the
spawn, re-ranked by 021's rank network), until it tops out or reaches 430 lines. Keep the
placement whose futures earn the most points on average. Below level 39 the agent is
017's, unchanged.

## Variants (dev check)

* `rank_n16`: the futures placed by 021's rank agent (`rank_pilot.bin`).
* `search_n16`: the futures placed by the commit search alone (015's agent), to see
  whether the network's picks help as a playout policy.

## Steps

0. **Code** (`rollout.hpp` `set_playout`, `fn_playout_game`, ABI 19,
   `experiment022.py`). With playouts off the game is byte-identical to 017's. Timing
   probe on 021's distil seeds only.
1. **Dev check** on 020's dev seeds 100-199 (the fair ones for rollout settings, 019),
   paired against 017's stored games there (1,840k). Keeper: a paired mean above 017
   with its CI above 0. Confirm on dev seeds 0-99 (017 = 1,810k): paired mean above 0.
2. **Held-out**: `predeclared.md`, then 012's 1,000 held-out seeds against 017's record
   (1,800k). Hand-off prompt if it runs longer than a session.
3. **Train on those scores** (the second half of the idea, planned after step 1): record
   each playout-scored decision's candidates and mean points on fresh seeds, fit 021's
   network shape on them, and use it where playouts are too slow (29-38, whose games run
   ~350 pieces to the end) or to make the 39+ agent fast.

## Stop rule

If neither variant has a paired mean above 017 on dev seeds 100-199, stop 022 there
(notes.md) before step 2. Step 3 is still worth a look only if the playout target ranks
candidates differently from 017's rollouts at 39+ (dump comparison), since a network
trained on it could then still beat 017 elsewhere.

## Cost

Measured in step 0's probe: 4-19 minutes a game for rank_n16 (`notes.md`).
