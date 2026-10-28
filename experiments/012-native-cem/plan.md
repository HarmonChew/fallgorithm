# Experiment 012 - plan: finish CEM training on the native reach_plan

Status: done 2026-10-29; see `notes.md` for the result. Before the held-out run,
`predeclared.md` is written from the "Success rule" section and is not edited afterwards.

## Question

With training now about 100 times cheaper (Experiment 011), does a full CEM run on
the native `reach_plan` beat Experiment 009's numbers (4 of 12 iterations, curve
still rising) on fresh held-out seeds?

This is the baseline step before learning a value function from self-play (the
next experiment): it gives the strongest hand-built evaluation we can get, so a
learned one has an honest bar to clear.

## What changes

Only the 20 evaluation numbers (`tunedplan.DEFAULTS`: 16 weights and 4 whole
numbers). The agent is 011's C++ `reach_plan` unchanged; no C++ or Python agent code
is edited.

## Training (CEM)

The same method as 009 (`experiment009.sample` and `cem_update`, reused), sized
for the native speed:

* Population 48, elite 12, 30 iterations, sampling RNG seed 12.
* The mean starts at Experiment 009's final numbers (`final_params.json`,
  resolved). The starting spread is 009's starting spread
  (`experiment009.initial_spread`, about half of each default weight; 1.0 for the
  zero-start features; 2 for the whole numbers), so the search widens again around
  009's answer. Spread floor 5% of the starting spread, as in 009.
* Fitness: a candidate's mean score over 96 training seeds at 30 Hz / 300 ms, in
  008's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap,
  150,000-frame cap).
* Training games are played by `native.play_game` alone (no Python replay), since
  only score and lines are needed. The result is the final CEM mean (not the best
  sample).
* Timing (measured 2026-10-29 on 009's training seeds, 30 workers): about 0.033 s
  per game, so an iteration of 4,608 games is about 2.5 minutes and the run about
  75 minutes. `train` saves after every iteration and can resume.

## Seeds

All seeds are 0-65535 and chosen without looking at any game outcome.

* **Training**: 96 seeds, `SHA256("fallgorithm012/train/v1/<i>")`, first two bytes.
* **Held-out**: 1,000 seeds, `SHA256("fallgorithm012/heldout/v1/<i>")`.
* Both skip every seed used by Experiments 000-011 (found in their JSON files and
  gzipped records, 008's 300 and 009's 24 training seeds included, plus 12345, which
  011 used for profiling and which appears only in prose), and any seed with the same
  native start state as one of those (the 009 rule). Training seeds are selected
  first; held-out seeds also skip every training seed and its start-state twins.
  Written to `seeds.json`.

Why fresh held-out seeds: 008's 300 seeds have now been looked at by 009, 010 and
011, and choices were made after seeing them. The whole evaluation (2,300 games,
each replayed on the Python binding) takes about 2.5 minutes, and 1,000 seeds give
a tighter interval. 008's 300 are still played, as a secondary
table for comparison with earlier experiments.

## Held-out evaluation

`evaluate` plays two agents on the 1,000 held-out seeds, both with the native
`reach_plan`, recorded with inputs (011's `play_native`, which replays every game
on the Python engine binding and checks the C++ counters against it):

* **cem**: the final CEM mean.
* **baseline**: 009's numbers (what 010 and 011 play).

The comparison is paired by seed. It also plays the cem numbers on 008's 300 seeds
(secondary; the baseline there is 011's retained record).

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12,
percentile method; `experiment009.bootstrap_mean_ci`) of the paired mean score
difference (cem minus baseline) on the 1,000 held-out seeds lies entirely above 0.

Also reported, for both agents: mean, median, p5, p10, p90 of score and lines;
top-out rate; share reaching level 29, level 39 and the line cap; the Tetris rate;
the paired lines difference with its interval; the training curve (best, elite mean
and population mean per iteration); and the final mean's training-seed score next
to its held-out score. The training-seed score is in-sample and inflated by picking
elites on noisy fitness, so it is reported only to show how much the numbers fitted
the training seeds. The 4 whole numbers can drift outside their clamp range in the
CEM mean; `final_params.json` keeps both the raw and the resolved values, and only
the resolved values are played.

## The Python copy (011's open question)

Decided here: the C++ `reach_plan` is the agent from now on. The Python copy stays
as the frozen reference for 011's parity tests and is not extended. This experiment
changes only numbers both copies already take, so nothing has to be ported. New
agent features (the learned value next) are written in C++ only, and 011's records
plus `tests/test_native.py` stay as regression checks.

## What gets built

```
src/block_stack_ai/experiment012.py   select-seeds, train, evaluate, verify, summarize
experiments/012-native-cem/           config.json, seeds.json, training.json,
                                      final_params.json, predeclared.md, records/,
                                      result.json, notes.md
tests/test_experiment012.py           seed selection rules, resume, config shape
src/block_stack_ai/quickplay.py       012 in the launcher (plays 012's numbers)
```

## Steps (each a reviewed commit)

1. This plan.
2. `experiment012.py`, `config.json`, tests; `select-seeds` run and `seeds.json`
   committed. Timing checks use training seeds only.
3. `predeclared.md`, then `train` (committed harness first; `training.json` and
   `final_params.json` committed after).
4. `evaluate`, `verify`, `summarize`; `result.json`, `notes.md`, launcher entry.

## Process rules

* Commit the harness before any timed or held-out run, so records name a clean
  commit; `evaluate` writes under `runs/` only, records are copied into `records/`
  by hand.
* No held-out game is played before `predeclared.md` is committed and training has
  finished.
