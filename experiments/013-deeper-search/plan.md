# Experiment 013 - plan: deeper search, with the 20 numbers re-tuned for it

Status: done 2026-10-29; see `notes.md` for the result. Before training, `predeclared.md`
was written from the "Success rule" section and is not edited afterwards. (The 951k below
is from an earlier, uncommitted trial; `value_probe.json` holds the committed reruns.)

## How this plan came about

013 started as a learned value function: a linear guess of the score still to come
(`native/value.hpp`, 114 weights over 18 board features in three level bands), fitted by
least squares to self-play outcomes (Monte Carlo fitted value iteration), in place of
the 20 numbers inside the same search. Short trials on self-play seeds only (no dev or
held-out game) did not work:

* Fitted to 012's own games, the model rates a 19-row stack at the start of a game
  above an empty board: in that data a taller, Tetris-ready stack always meant more
  points, and a linear model carries that on to the top of the board. The value agent
  dies within a few lines.
* With random exploration in the self-play games, one fit came close to 012 (951k on 300
  self-play seeds), but later rounds of self-play got worse, not better (391k, then
  71k). Lower exploration, exploring starts and step-shaped height inputs did not fix it.
  This matches what is known about linear value iteration in Tetris (it oscillates and
  loses to CEM).

`value-probe` reruns these trials from committed code into `value_probe.json`. The
learned-value code stays as groundwork for a later experiment with a design that does
not depend on extrapolation.

Step 0 of the original plan, a depth check, did show a gain: 012's numbers with one
more ply of lookahead scored +73k on 200 dev seeds (95% interval +31k to +116k), at
about 1.3 times the cost per game. So 013 became the deeper search.

## Question

Does `reach_plan` with one more ply of lookahead, with its 20 numbers re-tuned for it
by CEM, beat Experiment 012 on 012's 1,000 held-out seeds, at 30 Hz / 300 ms?

## What changes

* **The search** (`native/search.hpp`, C++ only): at the adjust search (the preview
  known), each of the two beam paths ends not with the seven-piece average on the board
  it leaves, but with, for each of the seven unknown pieces, its best placement's value
  plus the seven-piece average on the board *that* leaves. The commit search is
  unchanged (it is replaced by the adjust search at the reaction frame, and an extra ply
  there would cost about ten times more). Off by default, so 011's and 012's agent is
  unchanged; `tests/test_native.py` still checks it against the Python reference.
* **The 20 numbers**: re-tuned by CEM for the deeper search.

## Training (CEM)

012's method unchanged (`experiment009.sample` and `cem_update`), with the extra ply in
every game:

* Population 48, elite 12, 30 iterations, sampling RNG seed 13, spread floor 5% of the
  starting spread.
* Starting mean: 012's final numbers (resolved). Starting spread:
  `experiment009.initial_spread()`, as in 012, so the search widens again around 012's
  answer.
* Fitness: mean score over 012's 96 training seeds, in 008's game setup
  (classic_ntsc_double_killscreen, start level 18, 430-line cap, 150,000-frame cap).
* The result is the final CEM mean (not the best sample).
* Timing (step 0, dev seeds): about 1.3 times 012's games, so about 90 minutes.

## Seeds

* **Training**: 012's 96 training seeds.
* **Dev**: 200 fresh seeds, `SHA256("fallgorithm013/dev/v1/<i>")`, skipping every seed
  used by Experiments 000-012 and any native start-state twin. Used for step 0 only.
* **Held-out**: 012's 1,000 held-out seeds. They were played once by 012's two agents;
  no choice in 013 has looked at them.
* **Self-play** (value probe only): labelled draws that skip the dev and held-out start
  states.

## Held-out evaluation

`evaluate` plays three agents on the 1,000 held-out seeds, every game replayed on the
Python engine binding with its counters checked:

* **deep**: the extra ply with the final CEM mean,
* **cem**: 012's agent and numbers (the baseline),
* **cem_extra_ply**: the extra ply with 012's numbers (secondary: it splits the gain
  between the deeper search and the re-tuning).

## Success rule

Success if the 95% bootstrap confidence interval (10,000 resamples, RNG seed 12,
percentile method) of the paired mean score difference (deep minus cem) on the 1,000
held-out seeds lies entirely above 0.

Also reported, for all three agents: mean, median, p5, p10, p90 of score and lines;
top-out rate; share reaching level 29, level 39 and the line cap; the Tetris rate; the
paired lines difference with its interval; deep against cem_extra_ply and cem_extra_ply
against cem; the training curve; and the final mean's training-seed score (in-sample)
next to its held-out score.

## What gets built

```
native/search.hpp                     the extra ply (off by default)
native/value.hpp                      the learned value and its search (groundwork)
native/agent.hpp                      agent generic over its search; self-play exploration
native/c_api.cpp, native.py           fn_play_game_ex and the value helpers
src/block_stack_ai/experiment013.py   select-seeds, depth-check, value-probe, train,
                                      evaluate, verify, summarize
experiments/013-deeper-search/        config.json, seeds.json, depth_check.json,
                                      value_probe.json, training.json, final_params.json,
                                      predeclared.md, records/, result.json, notes.md
tests/test_experiment013.py
src/block_stack_ai/quickplay.py       013 in the launcher
```

## Steps (each a reviewed commit)

1. This plan, `predeclared.md`, the code and tests, `seeds.json`.
2. `depth-check` and `value-probe` from the committed code, then `train`;
   `depth_check.json`, `value_probe.json`, `training.json`, `final_params.json`.
3. `evaluate`, `verify`, `summarize`; `result.json`, `notes.md`, launcher entry.

## Process rules

* Commit the harness before any timed or held-out run, so records name a clean commit;
  `evaluate` writes under `runs/` only, and the record is copied into `records/` by hand.
* No held-out game is played before `predeclared.md` is committed and training has
  finished.
