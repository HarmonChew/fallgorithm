# Experiment 037 - predeclared protocol: step 0, stages A and B, the choice of `v37` and the record attempt

Written 2026-11-14 with plan.md (version 2), before any 037 game. Step 0's rule was fixed
and committed (0298344) before step 0 ran; the rest is fixed before stage A's round 0 and
not edited after the run starts. Code: `src/block_stack_ai/experiment037.py`,
`experiment037eval.py`. The owner said (2026-11-14) to go on and hand long runs
over without waiting; plan.md's open choices were not answered explicitly and are taken on
the agent's recommendations (both stages, the margins below, a new training seed list),
reported to the owner when the run started.

## Format, search, base

036's format (classic_ntsc_double_killscreen, start level 18, 430-line cap, tap_hz 20,
reaction 300 ms, frozen agent params) and 035's `search_for_036`, in every game. The base
is `v36` (036's record, 1,915,044): V18@20 `036/stage2/value_sweep2.bin` below 230,
V29@20 `036/stage3/value_sweep1.bin` at 230-319, 031b's V39' from 320. It is not played
again: its stored games are the base (probe A copied to `base_games/probeA-v36.json.gz`
from `runs/036/games/stage3-sweep1-A.json.gz`; probe B, development and held-out in
`../036-20hz-full-reteach/games/`).

## Step 0 (offline, no games)

As plan.md "Step 0" (fixed before it ran): per network, fitted once at lambda 0.95, 0.98,
0.99, 1.0; the network's lambda is the smallest of 0.98 / 0.99 / 1.0 whose risk bias on a
held-out round is at most a third of 0.95's in size and whose rms is at most 5% above
0.95's (`step0.json`). A network with no lambda is not taught; if neither has one, 037
stops after step 0.

## The stages

* **Stage A** (V29@20, 230-319, if step 0 gave V29 a lambda): agent `v36` with the stage's
  V29@20. Warm start `v36`'s V29@20. Targets: 036 stage 3's recipe (backup2 k 4 under the
  previous sweep's network for the played boards and a third of their children,
  lambda-returns at step 0's lambda, every value at 320+ max(0, c x V39' backup2), c =
  0.248). Sweeps: at least 3, at most 6.
* **Stage B** (V18@20, below 230, if step 0 gave V18 a lambda; after stage A): agent
  stage A's choice if stage A went on, else `v36`, with the stage's V18@20. Warm start
  `v36`'s V18@20. Targets: 036 stage 2's recipe at step 0's lambda, every value at 230+
  the backup2 of the stage's V29@20. Sweeps: at least 2, at most 4.
* Round 0: 400 games of the stage's agent with its warm start, no exploration. Own rounds:
  200 games with the sweep's network, 0.5% exploration in 036's bands (stage A 210-319,
  stage B 0-229). Training set of sweep s: round 0 without its first 40 seeds (check
  boards, reported only) and the last 3 own rounds; 023's fit settings, warm-started from
  the previous sweep; torch seed 23 + 37,000 + 100 x ord(stage) + s.
* 036's target checks on every sweep (stage A as 036's stage 3, two-sided; stage B as
  036's stage 2, one-sided). A sweep that fails them is not fitted and its stage ends.
* Stop rule: from a stage's minimum on, stop after 2 sweeps without a new best probe A
  measure (every probed sweep counts, eligible or not); at the maximum, stop.

## New guards

* **Stage A, per probe:** deaths at 230-319 on the half at most `v36`'s on the same half
  + 10. A sweep that fails is not eligible (the stage goes on).
* **Stage B, after each fit:** the garbage gap (mean over 10-line steps below 130 of the
  value of boards with 10+ holes minus that of boards with no holes, on 036 stage 2's
  round 3 boards below 130 lines) no less negative than `v36`'s V18's. **Per probe:** games
  with 40+ singles at level 18 at most `v36`'s on the same half + 3. A sweep that fails
  either is not eligible and the stage ends there (a sweep failing the garbage check is
  not probed).
* The stage's guard also applies to its choice's probe B: a choice whose probe B fails it
  cannot be `v37`.

## Probes and the choice

* Probe seeds: 036's (035's 14,200-14,699 probe A, 14,700-15,199 probe B). Screening only.
* The probe measure, against all 2,500 stored `v36` games (probe A, probe B, development,
  held-out): stage A (plays `v36`'s own game below 230; the prefix guard stops a step on
  any seed that differs before 230 lines) mean points at levels 29 and up minus the
  2,500's; stage B mean final score minus the 2,500's. 95% two-sample percentile bootstrap,
  10,000 resamples, RNG seed 12. The seed-paired difference against `v36` is reported.
* A stage's choice: its eligible sweep (1 or later) with the highest probe A measure. If
  that measure is above 0 the choice plays probe B once and the stage goes on; otherwise it
  does not.
* **`v37`**: the stage choice (of those that went on, its probe B passing the stage's
  guard) with the highest probe B measure, if above 0; otherwise no final evaluation and the record stays `v36`. Its probe B figure is
  reported as selected.

## Final evaluation

Primary metric: mean final score of `v37` minus the stored `v36` games on the same seeds,
paired by seed, 95% bootstrap interval of `experiment012.paired` (10,000 resamples, RNG
seed 12).

1. **Gate**, before any `v37` game: 032's 30 Hz replay gate (140 stored record games) and
   the first 28 stored `v36` development and held-out games re-run (56). All must match.
2. **Development** (the register's 500): kept if the paired mean is +15,000 or more and
   the interval's lower end is above 0.
3. **Held-out** (012's 1,000), only if kept: a new 20 Hz / 300 ms record if the interval's
   lower end is above 0; `v36`'s 1,915,044 is the previous record.

## Guards

* Every game is replayed on the engine with its counters checked and checked for the 20
  Hz tap spacing (036's game and checked-game path).
* Before any game: a clean tree outside `experiments/037-longer-horizon-targets`; plan,
  this file, `step0.json`, `seeds.json`, the base games and every input network committed;
  the wiring check (the first 28 stored `v36` development and held-out games re-run)
  matched on the library that plays.
* A step interrupted part-way resumes from its partial file only if no commit happened
  since it started; otherwise it is replayed.

## Seeds

New training seeds (`seeds.json`): labelled seeds `fallgorithm-training/037/v1/<i>`, one
per start state, none sharing a start state with 029's training list, the register's sets,
012's held-out seeds or 023's probe seeds (7,944 such start states exist). Stage A: round
0's 400 and 5 rounds of 200; stage B: 400 and 3 rounds of 200.
