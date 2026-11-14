# Experiment 038 - predeclared protocol for step 0

Written from plan.md (version 1) before any game of step 0. It is not edited afterwards.
Owner's go-ahead: 2026-11-15 ("implement and execute"). Stage 1 and stage 2 get their own
protocol (`predeclared-stage1.md`), written only if step 0 names an arm.

## Choices left open in plan.md, as taken

1. 038 before 039 (the owner's go-ahead for 038 as planned).
2. Step 0's rule keeps the plan's numbers: lead +3 rows, at most 15k lost before 330, P(330)
   down by at most 2 points.
3. A step 0 arm whose total beats `v36` is noted as a record candidate only. It plays no
   development or held-out game unless the owner says so after reading step 0's result.
4. No new confirmation set: the final evaluation, if any, is development then held-out, as
   036's.

## The format

033's: 008/012's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap,
frame cap and agent params as frozen) at 20 taps a second and 300 ms reaction.

## The agent

036's `v36` (decision.json: `stage2/value_sweep2.bin` below 230 lines, `stage3/value_sweep1.bin`
at 230-319, 031b's V39' `value_sweep5.bin` from 320; networks' shas checked) with 035's
`search_for_036`. No network is trained or changed in step 0.

The only change, NetSearcher::set_lead_bonus (native, `fn_lead_game`): for a decision whose
position has `L` lines or more and fewer than 330, every leaf value the search computes gets

    beta x (min(height of column 0, 16) - mean height of columns 1-9)

added, in Tetrises at level 18 (22,800 points). Beta 0 is `v36`'s search exactly.

| arm | L | beta |
|---|---|---|
| `t300_a` | 300 | 0.25 |
| `t300_b` | 300 | 0.75 |
| `t315_a` | 315 | 0.25 |
| `t315_b` | 315 | 0.75 |

The native ABI stays at 29: `fn_lead_game` is a new function and the existing ones are
unchanged, so 036's code (predeclared on ABI 29) still runs and its gate can be re-run on
this library. (plan.md said "ABI raised"; this is the only departure, and it changes no game.)

## Seeds

Probe A: 035's seeds 14,200-14,699 of 029's list (036's `seeds.json`, "probe" A). Screening
only, seen by 035 and 036. `v36`'s stored probe A games (036's `stage3-sweep1-A.json.gz`)
are copied into `games/v36-A.json.gz` and are the base; `v36` is not re-played.

## Order

1. Wiring check on the new library, before any arm: the first 28 stored `v36` probe A
   games re-run through `fn_lead_game` with beta 0 must match input for input
   (`wiring_check.json`).
2. The four arms in the order of the table, 500 games each.
3. The summary (`step0.json`).

## Guards

* Every game is replayed on the engine with its counters checked (`register.checked_game`)
  and checked for the 20 Hz tap spacing.
* On every seed an arm's inputs must equal `v36`'s stored game's up to the frame that game
  first has `L` lines (the whole game if it never does). A mismatch stops the arm.
* Every result records the native library's sha and ABI version.

## Measurement

The board at 330: a game's first piece at 330 lines or more (replayed); its lead is column
0's height minus the mean height of columns 1-9 (the free look's measure, not capped).

* Lead at 330: the mean over the games that reach 330 lines, arm minus `v36`.
* Cost: the points a game has at its board at 330 (its final score if it never gets
  there), `v36` minus the arm, paired by seed, mean with a 95% bootstrap interval (10,000
  resamples, RNG seed 12).
* P(330): the share of games reaching 330 lines, `v36` minus the arm.

## The rule

* An arm **qualifies** if its lead at 330 rises by 3 rows or more, its paired cost is at
  most 15,000 (mean), and P(330) falls by at most 2 points.
* Stage 1 takes the qualifying arm with the largest lead at 330 (the first in the table on
  a tie). **If none qualifies, 038 stops**: column 0 cannot be built ahead cheaply at 20 Hz.
* The arms' totals are reported, not judged (V39' does not know how to use a built-up column
  0). An arm with a paired total above `v36`'s and the interval's lower end above 0 is
  noted as a record candidate (choice 3 above).

Reported, not part of the rule: the lead paired on the seeds where both reach 330; mean
column heights at 330; points and lines from 330 on (paired), clears by size from 330 on;
lines after 330 by lead (arms against `v36`: the first causal reading of the free look's
correlation); 035's style figures; seconds a game.

## Odds

From three smoke-test games of `t300_b` (seeds whose `v36` game reaches 330; not part of
the result): the agent builds columns 0 and 1 up together, so the lead moves less than
column 0 does, and those games scored less before 330. A failing step 0 is a plausible
outcome; the plan put it at about one in three.
