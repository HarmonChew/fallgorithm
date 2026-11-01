# Experiment 024 - plan: teach the self-taught value the late levels from real outcomes

Status: chosen by the owner 2026-11-01 after 023's milestone 2 failed. Results in
`notes.md`.

## Why

023's value V (sweep 15) plays levels 18-28 better than 017's rollouts but loses from 29
on, in its own agent and inside 017's rollouts (023 milestone 2). A check on data already
on disk (`diagnose_sweep0_023play15_explore.json`) shows why:

* **Optimism.** On V's own 2,000 games (023's play15), V's value of a 39+ board averages
  7.2 Tetrises (level-18 Tetrises still to come) against 3.6 that the game actually went on
  to score; at 410-429 lines 5.4 against 1.1. Those games had 023's 1% random placements,
  which cost about 16%; the review replayed 280 of them without (V 7.6 against 4.2 at 39+,
  14.7 against 18.1 at 29-38, 47.3 against 65.1 at 18). So V is too high on the killscreen
  and too low everywhere before it.
* **Ranking.** At 017's rollout-ranked commit decisions in 021's 300 games of 017's agent,
  judged by the odd rollouts (the half that did not pick), V's pick loses 14.8 (29-38) and
  24.0 (39+) in the rollouts' points units against the hand search's 10.8 and 11.6 (the
  rollouts end in the hand value, which leans this check its way).

A third of the training boards are 29+, so it is not a lack of boards. The likely cause is
the targets: most are V's own one-piece backup, and the max over placements of a slightly
wrong V leans high; on the killscreen the death that matters comes several pieces later,
past what one piece of lookahead sees, and the error feeds on itself sweep after sweep.

## The change

023's loop unchanged except two things. The targets of boards with 230 lines or more
(level 29 on):

* **play boards** (V's own games): lambda 1 from 230 lines on, so the target is what the
  game actually went on to score from the board (below 230 lambda stays 0.95, so those
  returns run into the real outcomes once the game reaches 230);
* **base boards** (015's games) **and children** (V's own picks one piece on) at 230 lines
  or more are left out: their only target is the backup.

And the play rounds have no random placements, so the real outcomes are the agent's own.

Everything else is 023's: network shape, fit, 4 play rounds kept, 2,000 play games a
round, the probe. V0 = 023's sweep 15. Sweep 1 trains on four fresh rounds of V0's games
(0-1 to 0-4); each later sweep plays a new round with the last V first. A late board's
target is its game's outcome, so the 29+ targets rest on ~8,000 games' luck, not millions
of independent boards: expect noisier fits there.

## Checks and rules

* After each sweep: the probe (023's 100 probe seeds, against 015's and 021's agents) and
  the diagnostic (`diagnose_sweepK.json`: V against real outcomes by band on its own new
  play round, and its ranking on 021's 017 games; `diagnose_sweep0.json` is V0 on round
  0-4). Only probe and play seeds steer the
  loop.
* At most 10 sweeps; stop when the probe mean has not improved for 3 sweeps.
* **Milestone 1** (dev check, 020's dev seeds 100-199): the best probe V's agent against
  023 sweep 15's agent (1,736k there), paired; met if the CI is above 0.
* **Milestone 2**, only if milestone 1 is met: V in 017's rollouts (023's dev-check-leaf
  code, from levels 18, 29 and 39) against 017 (1,840k) on dev 100-199; a keeper is
  confirmed on dev 0-99, then `predeclared.md` and the held-out run against 017's record
  (1,800k).
