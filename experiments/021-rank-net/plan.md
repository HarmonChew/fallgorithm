# Experiment 021 - plan: a network that ranks the search's top moves

Status: approved by the owner 2026-10-31. `predeclared.md` is written after
the dev checks and before any held-out game.

## Why

017's rollouts (1,800k) are the best move-picker we have, but cost ~8 minutes a game, so
nothing can be tuned or built on top of them. Two attempts to copy them cheaply failed:

* 018: a linear score on 27 hand features, fitted to the rollouts' choices, picked worse
  than the search alone.
* 020: a network on the raw board, fitted to *one game's future* after the chosen board,
  could not tell sibling boards apart (it never saw the alternatives) and collapsed.

021 joins the two halves that each failed for a known reason: the raw-board network of
020, trained on 018's kind of target (**the rollouts' value of every candidate at the
same decision**), and used only where it was trained (**to re-rank the search's top 4**,
exactly the choice 017's rollouts make). It never ranks a board the search would not
already consider, and the preview's placements stay with the search.

## The idea in one paragraph

At each decision 015's search proposes its best 4 placements; 017 plays 16-32 short
random futures from each and keeps the one that scored best. We record those decisions
(each candidate's settled board plus its rollout average), and teach a small network to
predict, from the board, how much better or worse each candidate is than its siblings.
Then the agent asks the network instead of playing the rollouts: about 4 network calls
per decision instead of ~100 simulated pieces.

## What the network sees and says

* Input per candidate: 020's 231 inputs (200 cells, `value.hpp`'s 18 features,
  level band, lines left, drought, last piece), plus the decision kind (preview 18-28,
  commit 29-38, commit 39+), the known preview piece (one-hot, preview decisions only),
  and the search's own totals for that candidate (`search_total`, `extra_ply_total`), so
  the network only has to learn the *correction* to the search.
* Output: one number per candidate. Loss: the candidate's rollout mean **minus its
  decision's average** (squared error), so only differences between siblings count.
* Size: 020's 256 -> 128 -> 1 and its C++ translation unit (`net.cpp`), reused.

## Data

* Fresh seeds `fallgorithm021/distil/v1`. 017's agent with `fn_distil_game` extended to
  write each candidate's 231-input row too, and its rollout mean split into two halves
  (even and odd rollouts), which tells us how noisy the target is: the "noise ceiling"
  no copy can beat.
* 018's data cannot be reused (it kept features only, not boards).
* Pilot 300 games (~1.8 h on 30 workers, ~300k decisions); 600 more only if step 2
  shows the fit still improving with data.

## Steps

0. **Code**: the extended dump, the fit (PyTorch, 020's `value` extra), the re-rank in
   C++ (`RolloutSearcher`'s place, same decisions, same beam 4). Tests: C++ matches
   PyTorch to 1e-4; with the network off, games are byte-identical to 015's.
1. **Collect** the pilot data.
2. **Offline check** on 60 held-back games, 018's table: per decision kind, how often
   each picks the rollouts' best, and the average loss against it, for the search alone,
   the network, and the half-rollouts. **Stop** if the network's loss is not below the
   search's in all three kinds (018's line: 1.38 / 8.77 / 7.93).
3. **Dev check** on 020's dev seeds 0-99 (`dev_baselines.json` already has 015 = 1,323k
   and 017 = 1,810k there), confirm a keeper on 100-199. Milestone 1: clearly beat 015
   at a few seconds a game. **Stop** if, after one fix (more data or a bigger net), it is
   still not above 015.
4. **What it unlocks**, chosen after step 3 with the owner:
   * a CEM retune of the search's weights with the network in the loop (now cheap);
   * **the network as the rollout policy inside 017's rollouts**: better futures give
     better targets, then refit: the BetaTetris-style improvement loop, and the route
     past 1,800k.
5. **Held-out** (012's 1,000 seeds) only for an agent that beats 017 on dev. Bar 1,800k.

## Honest odds

The pilot answers the key question in ~2 hours: can a raw-board network see what the
rollouts see? 018 says the features can't; the half-rollout ceiling tells us how much is
there to learn at all. By itself a good copy only makes 017 fast (~1,800k at seconds a
game); the score gain comes from step 4.
