# Experiment 014 - plan: real points for clears, Tetrises past the killscreen, NES odds

Status: done 2026-10-29; see `notes.md` for the result. Before training,
`predeclared.md` was written from the "Success rule" section and is not edited
afterwards.

## Why

013's deep agent scores 3,253 per line against BetaTetris's ~6,100: too many lines go
out as singles. Step 0's diagnostic (`singles.json`, 200 dev seeds) counts, per game,
for 013's agent:

* levels 18-28, BUILD phase: **50 singles** against 18 Tetrises; 28% of I pieces become
  Tetrises at 18-28, 17% at 29-38, 0.8% at 39+;
* level 39+: about 100 pieces a game, ~99% of them in SPEND, 0.1 Tetrises a game.

Three things in the agent point there:

1. **Clears are not scored as points.** BUILD pays a fixed bonus for a Tetris and a
   small linear penalty for other clears; SPEND pays `spend_lines_cleared` per line, so
   a Tetris there is worth only four singles (in real points it is worth 30). Neither
   knows a clear at level 39 is worth twice one at level 18.
2. **No Tetrises past the killscreen.** The BUILD height budget from `survival_level`
   on is `survival_budget`, which `tunedplan.INTEGER_RANGES` holds at 2 or more, and
   `survival_level` is at most 38: from level 39 the agent builds only while the stack is
   under `survival_budget` rows, so it is always spending.
3. **Uniform piece odds.** The search weighs each unknown piece at 1/7. The engine deals
   with the NES randomizer (`block-stack core/src/rng.cpp`): a roll of 0-7, and a 7 or a
   repeat rerolls once, so an I follows an I 1 time in 32, not 1 in 7.

## Question

Does 013's deep search with the NES piece odds, a real-points clear term and its own
BUILD budget from level 39, with its 22 numbers re-tuned by CEM, beat Experiment 013 on
012's 1,000 held-out seeds, at 30 Hz / 300 ms?

## What changes (C++ only; `reach_plan_014` in `native.play_game_ex`)

* **NES odds** (`native/search.hpp`, `set_nes_odds`): the unknown pieces are weighed by
  the randomizer's odds after the piece before them: after the current piece at the
  commit search, after the preview at the adjust search, and after the first unknown
  piece at the extra ply. In 64ths: 8 for a piece other than the previous one, plus 2
  from the reroll (4 for the NES order's entry at the previous piece's spawn id mod 7).
* **`clear_points`** (`native/eval.hpp`): added to the plan value in both phases,
  `clear_points * NES points(lines) * (level + 1) / (1200 * 19)`, the level being the
  one after the clear (the engine updates the level, then scores), so a Tetris at level
  18 is worth 1.0 and a single there 1/30. The old clear terms stay; CEM can trade them off.
* **`killscreen_budget`** (`native/eval.hpp`): from level 39 (the double killscreen),
  the BUILD height budget, 0-14, in place of `survival_budget`.

Both new numbers are off by default (0 and -1): 011-013's agents play byte-identical
games (checked on 40 dev seeds against a library built from the commit before, and by
the tests). The extra ply stays on (013's deep search). The Python reference is not
extended.

## Step 0 (dev seeds, committed before training)

* `singles.json`: the diagnostic above, for 012's and 013's agents.
* `odds_check.json`: 181,576 piece pairs the engine dealt in 200 dev games against the
  computed odds; the largest difference is 0.7 percentage points (I after I: 3.12%
  observed, 1/32 computed).
* `lever_check.json`: each change alone on 013's numbers, 200 dev seeds, paired against
  013's agent: NES odds -25k (interval -72k to +21k); with the odds, a killscreen budget
  of 4 -71k (-115k to -27k) and of 8 -84k (-128k to -41k); `clear_points` 5 -32k (-78k
  to +13k) and 15 +34k (-10k to +77k). Untuned, building past level 39 costs more than
  it earns; CEM decides whether a re-tuned agent can use it.

## Training (CEM)

013's method unchanged (`experiment009.sample` and `cem_update`) over 22 numbers, with
`reach_plan_014` in every game:

* Population 48, elite 12, 30 iterations, sampling RNG seed 14, spread floor 5% of the
  starting spread.
* Starting mean: 013's final numbers (resolved), `clear_points` 0 and
  `killscreen_budget` 2 (013's behaviour at level 39, since its `survival_budget` is 2).
  Starting spread: `experiment009.initial_spread()` for the twenty, 10 for
  `clear_points`, 2 for `killscreen_budget`.
* Fitness: mean score over 012's 96 training seeds, in 008's game setup
  (classic_ntsc_double_killscreen, start level 18, 430-line cap, 150,000-frame cap).
* The result is the final CEM mean (not the best sample), resolved by `native.resolve`.
* Timing: about 013's (96 minutes).

## Seeds

* **Training**: 012's 96 training seeds.
* **Dev**: 013's 200 dev seeds (step 0 only).
* **Held-out**: 012's 1,000 held-out seeds, played so far by 012's and 013's agents. No
  choice in 014 has looked at them.

## Held-out evaluation

`evaluate` plays three agents on the 1,000 held-out seeds, every game replayed on the
Python engine binding with its counters checked:

* **points**: `reach_plan_014` with the final CEM mean,
* **deep**: 013's agent and numbers (the baseline),
* **deep_nes**: `reach_plan_014` with 013's numbers (secondary: it splits the gain
  between the odds and the re-tuning with the two new numbers).

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12,
percentile method) of the paired mean score difference (points minus deep) on the 1,000
held-out seeds lies entirely above 0.

Also reported, for all three agents: mean, median, p5, p10, p90 of score and lines;
top-out rate; share reaching level 29, level 39 and the line cap; the Tetris rate and
score per line; the paired lines difference with its interval; points against deep_nes
and deep_nes against deep; the training curve; the final mean's training-seed score
(in-sample) next to its held-out score; and the singles diagnostic rerun on the final
agent (dev seeds).

## What gets built

```
native/eval.hpp, search.hpp, c_api.cpp  clear_points, killscreen_budget, NES odds (off by default)
src/block_stack_ai/native.py            resolve(), value_at(), nes_odds(), reach_plan_014
src/block_stack_ai/experiment014.py     singles, odds-check, lever-check, train, evaluate,
                                        verify, summarize
experiments/014-real-points/            config.json, singles.json, odds_check.json,
                                        lever_check.json, training.json, final_params.json,
                                        predeclared.md, records/, result.json, notes.md
tests/test_experiment014.py, tests/test_native.py
src/block_stack_ai/quickplay.py         014 in the launcher
```

## Steps (each a reviewed commit)

0. The singles diagnostic and its data (done: `106f7f3`, `79eba81`).
1. This plan, `predeclared.md`, the code and tests, `odds_check.json`,
   `lever_check.json` (rerun from the committed code).
2. `train`; `training.json`, `final_params.json`.
3. `evaluate`, `verify`, `summarize`; `result.json`, `notes.md`, launcher entry.

## Process rules

* Commit the harness before any timed or held-out run, so records name a clean commit;
  `evaluate` writes under `runs/` only, and the record is copied into `records/` by hand.
* No held-out game is played before `predeclared.md` is committed and training has
  finished. Diagnostics that shape a later experiment use dev seeds, not held-out records.
