# Experiment 015 - plan: a deeper commit search at the fast levels

Status: planned 2026-10-29. Before training, `predeclared.md` was written from the
"Success rule" section and is not edited afterwards.

## Why

The agent decides each piece twice (`native/agent.hpp`):

* the **commit search** at the spawn. The preview is not known yet (300 ms reaction), so it
  looks one ply ahead: the current piece, then the odds-weighted average over the seven
  unknown pieces;
* the **adjust search** at the reaction frame (frame 18). The preview is known, and 013's
  extra ply looks one more unknown piece further. 013's whole gain came from this search.

The adjust search only runs if the piece is still falling at frame 18. At level 29
gravity is one row a frame, and at 39+ two, so from level 29 the commit search mostly
decides alone. The agent there looks two plies less far than at levels 18-28.

Step 0's band diagnostic (`bands.json`, 200 dev seeds, 014's agent) measures it. The
share of pieces that reach their adjust search is 99.9% at level 18, 97% at 19-28,
**12.6% at 29-38 and 0% at 39+**. It also shows where the points are lost against
BetaTetris's published hybrid. The comparison is rough: their seeds and randomizer differ.

| band | 014's score (dev) | BetaTetris hybrid | 014's Tetris share of lines |
| --- | --- | --- | --- |
| through level 18 | 426k | 658k | 48% |
| through level 28 | 830k | 1,294k | 45% (19-28) |
| through level 38 | 1,169k | 2,039k | 26% (29-38) |
| whole game | 1,254k | 2,426k | 1% (39+ only) |

The gap is spread over all the bands. Levels 18-28 already get the deep search, so
their gap is about evaluation and is left for later. Levels 29+ have both the worst
points per line and the shallow search, and this experiment targets that.

## Question

Does 014's agent with 013's extra ply added to the commit search from level 29 (beam 2),
with its 22 numbers re-tuned by CEM, beat Experiment 014 on 012's 1,000 held-out seeds,
at 30 Hz / 300 ms?

## What changes (C++ only; `reach_plan_014` with two search settings)

* `Params` gets two whole-number search settings (`native/eval.hpp`), fixed and not
  tuned: `commit_ply_level` (-1: never) and `commit_beam` (0).
* At the commit search, from `commit_ply_level` on (`native/search.hpp`), the options
  are ranked by their one-ply total as before, ties keeping the option order. For the
  best `commit_beam`, the seven-piece average is replaced by 013's `deeper_average`:
  each unknown piece's best placement, plus the seven-piece average on the board it
  leaves. The first of equal totals wins, as at the adjust search.
* 015 uses `commit_ply_level` 29 and `commit_beam` 2 (`config.json`'s `search`).
* Off by default: 011-014's agents play byte-identical games. This was checked on 120
  dev games, 40 each for `reach_plan`, `reach_plan_extra_ply` and `reach_plan_014`,
  against a library built from the commit before. With
  the setting at 29, games are identical to 014's until the first piece at level 29
  (tested). `native.resolve` adds the settings to a resolved dict only when they are
  given, so earlier experiments' numbers resolve as before. The Python reference is not
  extended.

## Step 0 (dev seeds, committed before training)

* `bands.json` (`bands --agents points,ply_beam2,ply_beam4`, written as
  `bands_points_ply_beam2_ply_beam4.json` and renamed): per level band (18, 19-28, 29-38, 39+), for 014's agent and for 014's
  numbers with the commit ply (beam 2 and 4): pieces, the share that reached the adjust
  search, score, lines, clears, Tetris share and I-to-Tetris rate.
* `depth_check.json`: 014's numbers with the commit ply (beam 2, beam 4), a killscreen
  budget of 4 alone, and both together, each paired against 014's agent on the 200 dev
  seeds, with seconds per game. Go rule, set before the run: at least +20k, with the
  interval not wholly below zero.

Results (dev seeds, run from step 1's commit `29c151a` with a clean tree):

* commit ply, beam 2: +107k (interval +70k to +143k), +18.0 lines, 1.38 s a game against
  1.16 s (+19%);
* beam 4: +104k (+66k to +142k), +15.2 lines, 1.57 s a game. No better than beam 2 (a tie
  within noise) and slower, so the beam is **2**;
* killscreen budget 4: -45k alone; with the beam-2 ply, -70k against the ply alone.
  Building at the double killscreen still does not pay, so `killscreen_budget` keeps
  014's starting spread of 2. (The go rule is applied to each change against the same
  agent without it: the budget with the ply passes against 014, +37k, only because of
  the ply; against the ply alone it loses 70k.)

The gain shows up at 29-38 (Tetris share 26% to 33%, +68k there) and at 39+ (+39k,
mostly from surviving longer: 55 lines there against 39). Levels 18-28 are unchanged.

## Training (CEM)

014's method unchanged (`experiment009.sample` and `cem_update`) over 014's 22 numbers,
with the commit ply (level 29, beam 2) in every game:

* Population 48, elite 12, 30 iterations, sampling RNG seed 15, spread floor 5% of the
  starting spread.
* Starting mean: 014's final numbers (resolved). Starting spread:
  `experiment009.initial_spread()` for the twenty, then 10 for `clear_points` and 2 for
  `killscreen_budget` (014's).
* Fitness: mean score over 012's 96 training seeds, in 008's game setup
  (classic_ntsc_double_killscreen, start level 18, 430-line cap, 150,000-frame cap).
* The result is the final CEM mean (not the best sample), resolved by `native.resolve`.
* Timing: about 014's 95 minutes plus 19%, so about 115 minutes.

## Seeds

* **Training**: 012's 96 training seeds.
* **Dev**: 013's 200 dev seeds (step 0 only).
* **Held-out**: 012's 1,000 held-out seeds, played so far by 012's, 013's and 014's
  agents. No choice in 015 has looked at them.

## Held-out evaluation

`evaluate` plays three agents on the 1,000 held-out seeds, every game replayed on the
Python engine binding with its counters checked:

* **fast_deep**: `reach_plan_014` with the final CEM mean and the commit ply,
* **points**: 014's agent and numbers (the baseline),
* **points_ply**: 014's numbers with the commit ply (secondary: it splits the gain
  between the search and the re-tuning).

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12,
percentile method) of the paired mean score difference (fast_deep minus points) on the
1,000 held-out seeds lies entirely above 0.

Also reported, for all three agents: mean, median, p5, p10, p90 of score and lines;
top-out rate; share reaching level 29, level 39 and the line cap; the Tetris rate and
score per line; the paired lines difference with its interval; fast_deep against
points_ply and points_ply against points; the training curve; the final mean's
training-seed score (in-sample) next to its held-out score; and the band diagnostic
rerun on the final agent (dev seeds).

## What gets built

```
native/eval.hpp, search.hpp, c_api.cpp  commit_ply_level, commit_beam (off by default), ABI 9
src/block_stack_ai/native.py            SEARCH_DEFAULTS; resolve() and params()
src/block_stack_ai/experiment015.py     bands, depth-check, train, evaluate, verify, summarize
experiments/015-fast-commit/            config.json, bands.json, depth_check.json,
                                        bands_fast_deep.json, training.json,
                                        final_params.json, predeclared.md,
                                        records/, result.json, notes.md
tests/test_experiment015.py, tests/test_native.py
src/block_stack_ai/quickplay.py         015 in the launcher
```

## Steps (each a reviewed commit)

1. The search settings, harness and tests.
2. This plan, `predeclared.md`, `config.json`'s beam and spread, `bands.json`,
   `depth_check.json` (run from step 1's clean commit).
3. `train`; `training.json`, `final_params.json`.
4. `evaluate`, `verify`, `summarize`; `result.json`, `notes.md`, the band diagnostic on
   the final agent, the launcher entry.

## Process rules

* Commit the harness before any timed or held-out run, so records name a clean commit;
  `evaluate` writes under `runs/` only, and the record is copied into `records/` by hand.
* No held-out game is played before `predeclared.md` is committed and training has
  finished. Diagnostics that shape a later experiment use dev seeds, not held-out records.
