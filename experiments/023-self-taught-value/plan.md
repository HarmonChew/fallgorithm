# Experiment 023 - plan: a value that teaches itself through the search

Status: chosen by the owner 2026-11-01 ("go for it, no need for my review"). Started the
same day; results in `notes.md`.

## Why

Every strong agent needs a sense of what a board is worth. Ours is still the hand-built
score (eval.hpp, value.hpp): 018-022 all tried to beat 017 by learning from 017's own
choices or from noisy futures, and none did. StackRabbit computes a surface table by
value iteration over the pieces' shapes alone; BetaTetris trains a big network by
reinforcement learning and plays it mostly without search. This experiment does neither:
it teaches a value network with the search itself.

## The idea

The **backup** of a settled board (the next piece not yet known) is the average, over
the next piece by the NES odds, of that piece's best placement from the spawn (the
commit search's reach at the board's speed): its clear points plus V of the board it
leaves. A piece with nowhere to go adds 0 (the game is over). It is exact (all 7 pieces,
every placement, no random futures), so unlike 022's playouts it carries no noise.

A **sweep** backs up a set of boards with the last V and fits the next V to the backups
(020's network shape, warm-started). The set:

* **base**: 500,000 boards of 015's games (020's round 0), fitted to the plain backup;
* **children**: for every base board, the 7 boards V itself picks next (one per next
  piece), so V is taught on the boards its own choices lead to (020's failure was a
  network that only ever saw the chosen boards of another agent);
* **play**: whole games of the network agent itself (020's NetSearcher, 1% exploration),
  fitted to lambda-returns (lambda 0.95) along their game: the backup mixed with what the
  game went on to score, so a death far ahead reaches the board that caused it.

A loop: play with V_k, sweep to V_{k+1}, probe. V0 is 020's round 0 network.

## Checks and rules

* **Probe** after each sweep: 100 probe seeds (`fallgorithm023/probe/v1`, no dev or
  held-out start state), the network agent against 015's and 021's agents there. Only
  probe and play seeds steer the loop.
* The loop stops when the probe's mean has not improved for 3 sweeps, or after 20.
* **Milestone 1** (dev check, 020's dev seeds 100-199): the best probe V's agent against
  015 (1,385k there) and 021's rank agent (1,591k), paired.
* **Milestone 2**, only if milestone 1 beats 015 with CI above 0: V in 017's rollouts in
  place of the hand value (new code), against 017 (1,840k) on dev 100-199; a keeper is
  confirmed on dev 0-99, then `predeclared.md` and the held-out run against 017's record
  (1,800k).
