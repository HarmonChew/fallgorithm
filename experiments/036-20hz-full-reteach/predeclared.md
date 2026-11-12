# Experiment 036 - predeclared protocol: the stages, the choice of `v36` and the record attempt

Written 2026-11-12 with plan.md (version 4, after its independent review), before any game
of Experiment 036. It is not edited after the owner's go-ahead, which the notes record.
Code: `src/block_stack_ai/experiment036.py`, `experiment036eval.py`.

## The format and the search

033's format: 008/012's game setup (classic_ntsc_double_killscreen, start level 18,
430-line cap, frame cap and agent params as frozen) with tap_hz 20 and reaction 300 ms.
Every game is played in it, except the 30 Hz part of the replay gate.

Every 036 game uses 035's `search_for_036`: deeper commit and second unknown piece (k 4)
from level 18, adjust on the best 8 x 8 to level 28, third unknown piece at the commit from
level 29 (`deep3` [29, 1000, 2, 2, 2]).

## The agents

* Base `v29r20d`: 035b's record agent (023's v15 below 230 lines, 033's sweep 6 V29@20 at
  230-319, 031b's V39' from 320). It is not played again: its stored games are the base
  (`../035-20hz-search-probes/games/`: `combined` on the probe seeds,
  `development-v29r20d`, `heldout-v29r20d`).
* Stage 1 agent: `v29r20d` with a stage 1 V29@20 at 230-319.
* Stage 2 agent: the stage 1 agent with a stage 2 V18@20 below 230.
* Stage 3 agent: the stage 2 agent with a stage 3 V29@20 at 230-319.
* `v36`: the one of those chosen below. V39' (from 320) is never changed. No exploration
  outside the own rounds.

## Training values (fixed before round 0 of stage 1)

* Stages 1 and 3: targets are backup2 (k 4, 20 Hz) under the previous sweep's V29@20 and
  lambda-returns at lambda 0.95. Every value at 320+ lines, in the returns and for the
  children alike, is max(0, c x V39' backup2) with c = 0.248
  (`../034-v29-20hz-true-handover/handover_calibration.json`, never refit). No row has a
  game outcome as its target.
* Stage 2: 032's recipe at 20 Hz, lambda 0.95. Every value at 230+ lines, in the returns
  and for the children alike, is the backup2 of stage 1's chosen V29@20.
* Warm starts: stage 1 from 034's `value_sweep10.bin`; stage 2 from the better of v15 and
  032's `value_sweep9.bin` by paired mean on probe A in the stage 2 agent; stage 3 from
  stage 1's choice.
* Round 0 (400 games, no exploration): stage 1's is played with its warm start at 230-319,
  the first 200 seeds with v15 and the last 200 with 032's `value_sweep9.bin` below 230;
  stage 2's by the stage 1 agent with stage 2's warm start below 230; stage 3's by the
  stage 2 agent. Own rounds: 200 games with the sweep's network (stage 1: v15 below 230),
  0.5% exploration in the taught band (and the 20 lines before it for stages 1 and 3, as
  033).
* Training set of sweep s, as 033: round 0 without its first 40 seeds (their boards are
  check boards, reported only) and the last 3 own rounds; the children of a random third
  of the boards; 023's fit settings.

## Checks on every sweep's targets

In Tetrises at level 18 (22,800 points), by 10-line step of the taught band, computed on
the sweep's training targets before the fit. The played boards are the lambda-return rows
of the sweep's training parts; children are binned by their own line count; the mean
hand-over value is over those parts' hand-over boards. A step with no rows of either kind
fails. A sweep that breaks a check is not fitted or probed and its stage's loop ends there
(earlier sweeps stay eligible).

* Stages 1 and 3 (the 9 steps of 230-319):
  * the children's mean target minus the played boards' mean target is at most +2.0 at
    every step;
  * the children's mean target at 310-319 minus at 320-329 is within 2.0 of the played
    boards' drop there (their mean target at 310-319 minus the mean hand-over value).
* Stage 2 (the 23 steps of 0-229), one-sided: the children's mean minus the played
  boards' at most +2.0 at every step, and the children's drop from 220-229 to 230-239 at
  most 2.0 above the played boards' drop (their mean target at 220-229 minus the mean
  hand-over value). The negative direction is reported only.

## Sweeps and probes

* Sweeps: stages 1 and 3 at least 5 and at most 8; stage 2 at least 6 and at most 10. From
  the minimum on, a stage's loop stops after 3 sweeps without a new best probe A measure
  (sweeps 1 and later count; sweep 0 and the warm-start candidates do not).
* Probe seeds: 029's training list, indices 14,200-15,199 (035's). Probe A is 14,200-14,699,
  probe B is 14,700-15,199. Screening only: no record is claimed from them.
* **The probe measure**, against all 2,500 stored `v29r20d` games (probe, development and
  held-out: mean score 1,855,457, mean points at levels 29 and up 632,434), because the
  stored games' probe halves differ from that mean by -12k (A) and +11k (B):
  * an agent with a network other than v15 below 230: its mean final score on the probe
    half minus 1,855,457;
  * an agent with v15 below 230: its mean points at levels 29 and up on the probe half
    minus 632,434.
  Interval: 95% two-sample bootstrap, percentile (the agent's games and the 2,500 each
  resampled, 10,000 resamples, RNG seed 12). The seed-paired difference of
  `experiment012.paired` is reported next to it and decides nothing.
* Every sweep is probed on probe A (stage 1's sweep 0 and stage 2's two warm-start
  candidates too; of those two, the higher probe A measure is the warm start). A stage's
  **choice** is its sweep (1 or later) with the highest probe A measure among those that
  passed the checks.

## Rules between the stages

1. **Stage 1 go / no-go (owner, 2026-11-11):** if the choice's probe A measure is not
   above 0, or no sweep passed the checks, the run ends: no probe B, no stage 2 or 3, no
   final evaluation. Otherwise the choice plays probe B once.
2. **Stage 2:** its choice plays probe B once. If that measure is below -30,000 with the
   interval's upper end under 0, or no stage 2 sweep passed the checks, stage 2 is stopped
   and there is no stage 3.
3. Stage 3 runs otherwise, and its choice plays probe B once. If none of its sweeps passed
   the checks it has no choice.
4. **`v36`** is the stage choice (of the stages not stopped) with the highest probe B
   measure. If that is not above 0, there is no final evaluation and the record stays
   `v29r20d`. Nothing changes after this choice. `v36`'s probe B figure is reported as
   selected (the best of up to three).

## Final evaluation

Primary metric: mean final score of `v36` minus the stored `v29r20d` games' on the same
seeds, paired by seed, 95% bootstrap interval of `experiment012.paired` (10,000 resamples,
RNG seed 12). (The stored games' means on these two sets are within 3k of the 2,500-game
mean.)

1. **Gate**, on the build that plays, before any `v36` game: 032's 30 Hz replay gate (28
   each of 017's, e29_k4's, v39's, v29's and v39r's stored held-out games, 140) and the
   first 28 stored `v29r20d` development and held-out games re-run by the agent (56). All
   must match input for input; otherwise nothing is played and the gate is reported.
2. **Development**, the register's 500 development seeds: **kept** if the paired mean is
   +15,000 or more and the interval's lower end is above 0.
3. **Held-out**, 012's 1,000 held-out seeds, only if kept: **a new 20 Hz / 300 ms record**
   if the interval's lower end is above 0. The record then names `v36` and its held-out
   mean; `v29r20d`'s 1,854,852 is the previous record.

No screening stage: the probes are the screen.

Odds (from the stored `v29r20d` games' spread: sd 170k on development, 138k on held-out):
if `v36` has a new below-230 network the arms do not pair, the standard error is ~10.8k on
development and ~6.2k on held-out, and the intervals clear 0 at an observed ~+21k and
~+12k. Passing both: a true +15k about 20% of the time, +20k about 40%, +30k about 80%,
+50k about 99%. If `v36` is stage 1's choice the arms pair (~7k and ~5k) and development's
+15k bar binds. The probe B gate before it has a standard error of ~6-7.5k.

## Guards

* Every game is replayed on the engine with its counters checked (`register.checked_game`)
  and checked for the 20 Hz tap spacing.
* An agent with v15 below 230 lines (stage 1's, and `v36` if it is stage 1's choice) must
  equal the stored `v29r20d` game's inputs on every seed up to the frame that game first
  has 230 lines (the whole game if it ends before). Any mismatch stops the step.
* The tree is clean outside `experiments/036-20hz-full-reteach`; the plan, this file, the
  seed reservation (`seeds.json`, `register/SEEDS.md`: training indices 15,200-20,999) and
  every input network are committed before round 0; the wiring check matched on the
  library that plays.
* A step interrupted part-way resumes from its partial file only if no commit happened
  since it started; otherwise it is replayed.
* Every record names the native library's sha256 and ABI version (29) and both code
  versions. If the library changes during the run, the wiring check and the 20 Hz part of
  the gate are repeated on the new one before any further game.

## Reported, not part of any rule

Per sweep and per stage choice: points by band (paired), P(130), P(230), P(320), P(39),
deaths by 10-line step, Tetrises / singles / Tetris share by band, the boards at 29's and
39's entry, the two checks' tables, the value against the actual rest of game by 10-line
step, the drift of c x V39' backup2 against the actual rest of game on each round's
hand-over boards, seconds a game. Each stage choice against the previous
stage's choice on the probe seeds both played. For the final evaluation the same tables on
development and held-out.
