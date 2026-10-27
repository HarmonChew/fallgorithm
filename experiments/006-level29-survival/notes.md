# Experiment 006 — survive level 29

## Question

Experiment 005's `search_plan` either ran to the frame cap or died early. Does
lowering the well plan's stack-height budget from 8 to 5 once the game reaches
level 28 reduce top-outs without lowering mean lines?

## Autopsy

Every game in Experiment 005 ended at level 29 or later. Starting at level 18,
the engine reaches level 29 at 230 lines, and from then on a piece falls one row
every frame (`block-stack/core/src/rules.cpp`). `probes/autopsy.py` replays a
retained Experiment 005 record and prints the board at each spawn.

Both early search deaths (seed 30033 at 241 lines, seed 54626 at 401) followed
the same spiral:

1. With the stack six to eight rows high, a few holes appeared that were never
   cleared (30033 reached level 29 already nine rows high with seven holes).
2. The stack rose past ten rows and the well column filled in.
3. At one row per frame a piece can only reach a few columns from a high stack.
   The reachable columns shrank from 0–9 to 4–6, and the centre topped out.

The search games that survived averaged about 4.5 rows and under one hole at
level 29.

## Development

`probes/variants.py` compares one-knob changes to `search_plan` that switch on at
a given level, on 20 development seeds: Experiment 005's ten published seeds,
whose outcomes were already known, plus ten from `SHA256("fallgorithm006/dev/<i>")`.
The cap is 200,000 frames. `probes/development.json` holds the result.

| variant | top-outs / 20 | mean lines | min lines | mean score | Tetris line rate |
| --- | --- | --- | --- | --- | --- |
| `search_plan` unchanged | 14 | 1,606 | 241 | 9.41M | 0.0502 |
| no well from level 29 | 3 | 1,925 | 241 | 8.90M | 0.0065 |
| no well from level 28 | 3 | 1,941 | 241 | 9.02M | 0.0064 |
| no well from level 27 | 2 | 2,028 | 985 | 9.49M | 0.0067 |
| no well from 29, SPEND hole charge tripled | 7 | 1,668 | 368 | 7.85M | 0.0119 |
| budget 4 from level 29 | 3 | 1,915 | 241 | 9.01M | 0.0067 |
| budget 5 from level 29 | 4 | 1,855 | 241 | 9.19M | 0.0103 |
| budget 6 from level 29 | 5 | 1,811 | 241 | 9.54M | 0.0188 |
| **budget 5 from level 28** | **3** | **1,982** | **241** | **10.01M** | **0.0110** |
| budget 5 from 29, SPEND hole charge tripled | 11 | 1,632 | 419 | 7.68M | 0.0148 |

Every survival rule cut top-outs sharply, and every one cut the Tetris rate to
about a fifth, because the well is held far less often at level 29. A heavier hole
charge made things worse. Budget 5 from level 28 was chosen: it ties for the
fewest top-outs apart from one game, has the highest score, and keeps the most
Tetrises of the rules that survive. The single extra survivor of "no well from
27" is seed 30033, too small a difference to choose on.

## Agent

`survival_plan` (`src/block_stack_ai/survivalplan.py`) is `search_plan` below
level 28. From level 28 it plans with a height budget of 5 instead of 8, so the
well plan spends sooner. Nothing else changes. The search is repeated in that
module with the phase rule passed in, because Experiments 004 and 005 check their
retained records against the bytes of `searchplan.py` and `wellplan.py`; a unit
test keeps the copy equal to the original. Replaying the 20 development seeds
with the agent reproduces the chosen variant's lines and score in every game.

## Evaluation protocol (fixed before the evaluation run)

* Seeds: 30 held-out seeds from `SHA256("fallgorithm006/holdout/v1/<i>")`,
  skipping any whose native start state (seed field erased, as in Experiment
  005) matches a seed in an earlier experiment's JSON, a documented development
  seed or a 006 development seed. `probes/seeds.json` lists them and the 53
  excluded seeds.
* Game: `classic_ntsc_extended`, endless, start level 18, as in Experiment 005.
  The cap is raised to 400,000 frames so surviving games separate further.
* Agents: `search_plan` (unchanged Experiment 005 baseline) and `survival_plan`.
* Primary: `survival_plan` has fewer top-outs than `search_plan`.
* Secondary: `survival_plan` mean lines are at least `search_plan`'s.
* Reported without a threshold: minimum lines, mean score, Tetris line rate
  (expected to fall), and per-seed wins.

## Results

Measured on 2026-10-27 from clean commit `e5eff7d`, which fixed the protocol
before any evaluation game was played. The retained record is
`records/run.json.gz` (originally `runs/20261027T102555111733Z-006/run.json.gz`);
`result.json` is generated from it.

| agent | top-outs | cap stops | mean lines | min lines | mean score | Tetris line rate | mean pieces |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `search_plan` | 30 | 0 | 1,737.3 | 260 | 12,281,644.8 | 0.045665 | 4,378.7 |
| `survival_plan` | 13 | 17 | 3,446.2 | 589 | 32,036,534.8 | 0.006693 | 8,633.9 |

Both rules are met. `survival_plan` topped out in 13 of 30 games against all
30, cleared 1.98x the mean lines and scored 2.6x as much, and outlasted
`search_plan` on 23 of the 30 seeds. Seventeen of its games reached the
400,000-frame cap, so its line and score totals are lower bounds.

The cost is the expected one: the Tetris line rate fell from 4.6% to 0.7%.
The higher score comes from playing much longer at level 29 or later, not from
better scoring per line.

`survival_plan` is not uniformly better: on 7 seeds it died earlier than
`search_plan`, three of them below 1,000 lines (589, 873, 932). Its 13 remaining
deaths are the next thing to look at.

## Validation

`verify` replayed all 60 games' inputs and matched every outcome and final
hash, and `verify --decisions` re-ran both agents and reproduced every input.
The unit (328), native integration (40) and desktop (13) suites passed on
this branch, against the same dirty engine checkout.

## Reproduce

```sh
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment006 run
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment006 verify experiments/006-level29-survival/records/run.json.gz
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment006 verify experiments/006-level29-survival/records/run.json.gz --decisions
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment006 summarize experiments/006-level29-survival/records/run.json.gz
PYTHONPATH=src .venv/bin/python experiments/006-level29-survival/probes/variants.py /tmp/development.json
```

`verify` replays the recorded inputs on the native engine and compares lines,
score, frames, stop reason and final state hash; `--decisions` also re-runs both
agents and requires the same inputs. Both need the same engine as the run (see
Limitations).

## Limitations

* The sibling engine is the same dirty working tree at `8ca4158` that Experiment
  005 used; the record names its fingerprint, but its uncommitted changes are not
  retained, so the engine commit alone cannot rebuild it.
* `survival_plan` is not registered in the `block-stack-ai` launcher; use the
  module commands above.
* 30 seeds is still a finite sample, and capped games' totals are lower bounds.
