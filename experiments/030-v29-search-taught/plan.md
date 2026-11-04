# Experiment 030 - plan: a level-29-38 value taught by search (029's recipe one band down)

Status: owner's go-ahead 2026-11-04 ("okay lets just work on V29"; the cap-aware input is
not part of it). Version 2, after an independent Opus review of version 1 (section
"Review" at the end).

## Why

029's V39 made the end (320+ lines) as good as BetaTetris's or better (39+ given 39: 404k
against our ~380k estimate). The record `v39` (2,315,238) is still ~115k under the
BetaTetris hybrid (2.43M), so the gap is now before level 39. Rough split: BetaTetris's
pre-39 points ~2.43M - 0.97 x 380k ~ 2.06M against ours ~2.315M - 0.974 x 404k ~ 1.92M.
Levels 29-38 is where 027's deeper search gained most (+42k) and where BetaTetris's exact
tablebase plays; our play there is still `v15`, a network that has to judge every level.

029 showed that a network for one band, taught by its own two-piece search, changes the
style of play in that band (Tetrises without dying earlier) where more search with the same
network did not (027). This experiment does the same for 230-319 lines.

## The agent

`v39` (029's record: 027's `e29_k4` with V39 from 320 lines) with a third network, V29,
for every decision whose position has 230 to 319 lines (level 29 to the end of the first
nine-tenths of level 38). One network per decision, chosen by the position's lines:

| decision at | network | search (unchanged, e29_k4's) |
|---|---|---|
| 0-229 lines | v15 | adjust top-8x8 to 28, preview |
| 230-319 | **V29 (new)** | commit 2-ply from 29, deep2 k 4 |
| 320+ | V39 (029's chosen, frozen) | the same |

So play before 230 lines is `v39`'s exactly and nothing can leak into 18-28. From 320 on
the network is V39 unchanged, but the boards it meets change (V29 hands over different
stacks): that is intended and is counted in the score.

## Recipe (029's arm t2, which won, alone)

* **One arm, `t2` only**: backup2 targets with k 4 (two unknown pieces, the agent's own
  search from 29), the frozen teacher of sweep s being V29 of sweep s-1 (sweep 0 = v15).
  029's t1 lost to t2 from sweep 2 on; a second arm would double the time.
* **Training boards**: the boards of the agent's own games at 230-319 lines, plus children
  (below).
* **Lambda-returns on own play** (023/029, lambda 0.95), along each game's 230-319 boards,
  with an explicit hand-over (029's `lambda_returns` would treat the last stored board as
  the game's end and give a board at 319 the whole noisy rest of the game, 024's failure).
  The games' boards are dumped from 230 lines on, in order. For a board t at 230-319:
  * next board of the same game at 230-319: G_t = (1 - lam) B_t + lam (points until it + G_{t+1});
  * next board at 320 or more (the hand-over board h): G_t = (1 - lam) B_t + lam (points
    until h + A_h), with A_h = backup2 (k 4) of h under the frozen V39;
  * no next board (the game ended, before 320 or on the crossing piece): G_t = (1 - lam)
    B_t + lam (the game's rest of points), as 023.
  Tests pin all three cases.
* **Children**: for a random third of the training boards, their 7 next boards (one per
  next piece, the teacher's picks), kept from 230 lines on. Those below 320 get the plain
  backup2 under the teacher V29; those at 320+ (V29 values them in decisions at 316-319)
  get backup2 under the frozen V39, the same anchor as the hand-over. (The leaves at 320+
  inside V29's own backups stay under V29: one network per backup, as the agent's search.)
* **Fit**: warm start from the previous V29 (sweep 1 from v15), 023's settings (Adam,
  one-cycle, lr 3e-4, batch 4096, 3 epochs, MSE).

## Data (training seeds only)

Seeds: 029's training seeds (21,076, in order) after the first 1,700 that 029 used
(round 0's 300, then rounds 1-7 of 200, shared by both arms). None shares a start state
with the register's sets, 012's held-out seeds or 023's probe seeds (029's selection).
030 takes indices 1,700-1,899 as its 200 extra probe seeds, then round 0's 400
(1,900-2,299), then rounds 1-9 of 200 (2,300-4,099); `seeds.json` records the slice so a
later 029 run does not reuse it.

* Round 0: `v39` plays 400 training seeds, no exploration; its boards at 230 lines or more
  are kept (230-319 for training, 320+ only as the hand-over boards). The first 40 seeds'
  games are held out as check boards.
* After sweep s: round s, 200 games of the agent with V29 of sweep s on the next 200
  seeds (never reused), 1% exploration (a random reachable placement) per piece from 210
  to 319 lines (native gains an exploration end; none in V39's band, which would only
  bias the calibration). Sweep s trains on round 0 (minus the check seeds) and the last 3 rounds.

## Probe, diagnostics and stop rule (each sweep)

* Probe: 300 seeds, 023's 100 probe seeds plus 200 training seeds set aside for it (never
  used for rounds), paired against `v39` alone there (played once). The expected gain is
  ~20-40k and 100 seeds give a paired SE of ~20k, too coarse to choose among sweeps; 300
  give ~12k. (On 023's 100, `v39`'s V39 was itself chosen, so pairing there is slightly
  pessimistic.) Also: points at 29-38 (band score), P(reach 39), 39+ given 39, lines / Tetrises /
  singles / Tetris share of lines at 29-38, early top-outs (before 330 lines).
* Ranking (024's check): V29's commit picks at 017's rollout-ranked "commit 29-38"
  decisions in 021's games, judged by the odd rollouts; reported for all of them and for
  those below 320 lines (V29's own band); v15's figure computed once with the same code.
* Calibration: on the next round, V29's value against what each board's game went on to
  score (to its end), and against its own target definition (points to 320 + V39's
  hand-over value), by 20-line steps from 230. Also P(reach 39) and early top-outs every
  sweep: V39 undervalues 320-339 boards (029: 11.2 against 13.8 Tetrises), so anchoring to
  it can make V29 take too much risk before 39.
* Stop rule: at least 5 sweeps, at most 10; from sweep 5 on, stop after 3 sweeps without a
  new best probe mean.

**Choice for the staged evaluation**: of all probed sweeps whose 29-38 ranking loss is no
worse than v15's, the highest paired probe mean (`choose`). Best of up to 10 probes
overstates it a little; screening is on fresh seeds.

## Staged evaluation (predeclared.md)

predeclared.md is written and committed before any game. Primary metric: mean final
score paired by seed against 029's stored `v39` games. Honest odds: a true +20k passes the
+15k screen about 60% of the time, development about 50%. This is the fourth record attempt
on 012's held-out seeds (025, 026/027, 029 before it).

1. Screening (register's 100): promoted if the paired mean is +15k or more.
2. Development (register's 500): kept if at least +15k and the interval's lower end is
   above 0.
3. Held-out (record attempt): 012's 1,000 seeds after the replay gate (017, e29_k4 and
   v39 stored games replayed input for input); a new record if the interval's lower end
   against 029's record games of `v39` is above 0.

If nothing is promoted or kept: 030 is a failure, recorded with the diagnostics above.

## Code

* native (ABI 28): `NetSearcher::set_mid_net(net, from_lines)`: decisions at
  `mid_from <= lines < late_from` use it (late still wins from late_from); the game
  function gains `mid`/`mid_from_lines` (null is off). Off = `v39` input for input, checked
  on 029's stored screening games before any data game (also: v15 as the mid network gives
  the same games).
* Native also gains `explore_to_lines` (exploration only below it; default off = 029's).
* `experiment030.py` (from 029's: seeds, round0, loop, choose, probe base) and
  `experiment030eval.py` (from 029eval), tests as 029's.

## Not done (on purpose)

* No second data source like 029's h39 (017 from a level on): at 29-38 017 is worse than
  V (025: 017 at 29 lost there), so its style is not one to copy.
* No hand correction of V39's 320-339 offset: watched instead (P(39), early top-outs).
* V39 is not re-tuned for V29's hand-over stacks; if V29 changes them a lot, that is a
  later step.

## Cost (estimates, 28 workers)

`v39` games ~230 s. Round 0: 400 games ~55 min. Per sweep: targets (backup2 ~50 ms a
board: ~90k round-0 boards + 3 x ~45k round boards + ~2.3x children ~ 520k boards ~ 30
min, not measured at 29-38 where more placements are reachable: timed on a sample after
round 0), fit ~5 min, probe 300 games ~40 min, round 200 games ~30 min: ~1.8 h. 5-10
sweeps: 9-18 h. Staged evaluation ~5 h (held-out 1,000 games ~2.3 h).

## Review

Version 1 was reviewed by Opus (2026-11-04). Must-fixes, all made here: the hand-over
written as a spec with tests (029's lambda_returns would give boards at 319 the game's
real rest); children at 320+ anchored to V39 like the hand-over; a 300-seed probe
instead of 100. Should-fixes taken: exploration ends at 320; ranking reported below 320 and
v15's computed with the same code; backup2 timed at 29-38; P(39)/early top-outs watched;
predeclared.md first; odds and held-out reuse stated. Nice-to-haves taken: calibration
against the target's own definition; 030's seed slice recorded in seeds.json. Not taken: a
017 coverage source (see "Not done").
