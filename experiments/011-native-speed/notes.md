# Experiment 011 - a native (C++) reach_plan

## Question

Can a C++ port of `reach_plan` (Experiment 010's agent with Experiment 009's numbers)
play **exactly the same games** as the Python one, at least **50x faster**?
(`plan.md` is the plan; `predeclared.md` was committed, as 0395ec8, before the speed
measurement and before any held-out game was played in C++.)

This does not make the agent stronger. It makes the next steps affordable: full CEM
training, more seeds, deeper search, and later a learned value function.

## Why the whole game moved to C++

A profile of the Python agent (one process, level 18) showed 89 ms of deciding per
piece: the movement search (`reach.py`) about 48%, the board evaluation about 47%,
settling pieces about 4%, and the engine itself under 1% (9.4 microseconds a frame).
Porting only the search would have left the Python frame loop (about 50 frames per
piece through ctypes) as the limit, near 50x. So the agent's per-frame logic and the
game loop moved too: a C++ game runs on the engine's own `blocks_core` library and
returns the input bytes.

## What was built

* `native/` (C++20, built by `scripts/build_native.py` into `.build/native/`):
  `board.hpp` (settling, board features, gravity, levels), `eval.hpp` (`tuned_plan`'s
  value and phase rule), `reach.hpp` (`reach.py`), `search.hpp` (`reachplan.search`),
  `agent.hpp` (`BenchAgent.act` and the game loop), `c_api.cpp` (C functions).
* `src/block_stack_ai/native.py` loads it with ctypes (no new Python dependency) and
  refuses a library older than the sources it is built from, including the engine core.
* `src/block_stack_ai/experiment011.py`: `reference`, `parity`, `diverge`, `bench`,
  `evaluate`, `verify`, `summarize` (see Reproduce).
* The Python agent files are unchanged and stay the reference: where the two disagree,
  the Python is right.

A C++ game's result is not counted by new C++ code. Its inputs are replayed on the
Python binding with Experiment 009's `replay_outcome`, which builds the result, and the
C++'s own counters and start and end state hashes must agree with that replay.

## How exactness was checked

The translation was done in four steps, each compared with the Python directly, each
reviewed independently before its commit:

1. Board and evaluation: settled boards bit for bit, values compared with `==` (no
   rounding tolerance) on random boards and parameter sets.
2. Movement search: every placement, in the same order, with the same input masks.
3. Search: the chosen placement and masks on recorded and random positions, exact ties,
   the level changes at 130, 230 and 330 lines, and the unknown-piece average itself.
4. Whole games: the 40 Python reference games on Experiment 009's training seeds (24 at
   30 Hz / 300 ms, 8 at 15 Hz / 300 ms, 8 at 30 Hz / 0 ms) and edge games (line and frame
   caps, start level 0 and 4, challenge mode, 1000 ms reaction).

Each test was also run against deliberately broken copies of the C++ (built in a
scratch folder, not kept in the repo) to check that it notices. Things that had to be copied exactly, not just "the same
idea" (all in `plan.md`'s list):

* `reach.py` keeps each frame's possible states in a dict and walks it in insertion
  order; that order picks which input sequence is stored for a placement. The C++ keeps
  the same order.
* Python adds and multiplies doubles one step at a time. The C++ is built without fused
  multiply-add and without fast-math, so every value rounds the same way.
* Ties: the first placement wins, in `reach.py`'s sorted order.
* The plan's phase (build or spend) uses the real level at every ply of the search;
  only gravity uses the level after the clears.

## Results

The reported runs were made from the committed code (fallgorithm e855a71, clean tree;
Block Stack 4d46782): first `evaluate`, then `bench`. An earlier pair of runs, made the
same way from a working tree (0395ec8 plus the then-uncommitted step-5 harness), gave
the same verdicts; its numbers are given below where they differ.

### Speed (training seeds only, as predeclared; `bench.json`)

24 games at 30 Hz / 300 ms on 24 workers, the Python batch, then the C++ batch. Load
average before (32 threads): 7.9 over 1 minute, because the held-out run had just
finished, and 3.9 over 15 minutes (the earlier run: 1.9 and 2.2).

| | Python | C++ | Speed-up |
| --- | --- | --- | --- |
| Seconds per game | 107.2 | 0.81 | **133.3x** (earlier run 131.7x: 107.7 s and 0.82 s) |
| Whole batch (wall clock) | 120.1 s | 1.5 s* | 80x |

\* The C++ batch's wall clock also includes the Python replay that builds each result
and starting the worker pool; the per-game C++ figure is the game call alone.

The C++ batch was identical to the Python batch, game for game.

Per decision, one process (commit plus adjust search of every 20th piece of 12
training games, with the recorded arguments):

| Level | Pieces | Python ms | C++ ms | Speed-up |
| --- | --- | --- | --- | --- |
| 18-28 | 356 | 69.9 | 0.86 | 81x |
| 29-38 | 141 | 59.2 | 0.67 | 88x |
| 39+ | 25 | 35.3 | 0.40 | 89x |

### Exactness (Experiment 008's 300 held-out seeds, 30 Hz / 300 ms)

All 300 C++ games have the same start, the same input bytes and the same results
(everything but the timing field) as Experiment 010's retained record, and `verify`
replays all 300 on the engine with every result matching (both runs). The numbers are
therefore Experiment 010's: mean score 607,113, mean lines 330.9, every game tops out.

The 300-game run took **16.2 s** on 30 workers, including the Python replay that builds
the record (Experiment 010's took about 25 minutes). The C++ alone spent 0.91 s per
game there, against 140.0 s of deciding per game for the Python in Experiment 010's run.
A wall clock without the replay was not measured (the protocol asked for one): summing
the C++ game times and dividing by the 30 workers gives 9.1 s, a computed figure.

### Success

Both predeclared rules are met: **exact** (300 of 300 identical, verified on the engine)
and **fast** (133.3x per game, above 50x).

## What it shows

* The hot path really was search and evaluation in Python. A direct translation, with
  no new algorithms, no caching and one thread per game, is about 80-90x faster per
  decision and about 130x per game.
* One Experiment 009-style CEM iteration (32 candidates x 24 seeds = 768 games) would
  take about 23 s on 30 workers (projected from the held-out run), against about 46
  minutes for the Python `reach_plan` (768 x 107.2 s / 30). (Experiment 009's iterations,
  with the faster fixed-route `tuned_plan`, took 17-35 minutes.) All 12 of 009's
  predeclared iterations would take about 5 minutes.
* Exactness is practical to keep: a mismatch would show up as a different input byte,
  and `diverge` names the first decision where the two disagree.

## Honest limits

* **Two measurements.** The first `bench` and `evaluate` were a working-tree run (0395ec8
  plus uncommitted harness edits); after the review the code was committed and both were
  run again from the clean commit. The reported numbers are the second run's; both runs
  met both rules. In the second run `evaluate` came first, so `bench` started with a
  1-minute load average of 7.9.
* **Exact on these games, not proven in general.** 340 whole games, the edge games and
  the tests agree; a state none of them reaches could still differ. The C++ must be
  built without fused multiply-add (the build sets this).
* **One port.** Only `reach_plan` at the benchmark rules. `tuned_plan` (`limits.py`) and
  the 004-006 agents are not ported.
* **Speed on one machine.** 32 threads, 24 or 30 workers; per-game Python times are
  under that load. The C++ time is the game call only; the Python replay that builds the
  record adds about 0.4 s per game (it is not part of the agent, and training can skip
  it).
* **Two copies of the agent.** Any change to the agent now has to be made in both, or
  the Python dropped as the reference and this experiment's games kept as a regression
  check. The next experiment should decide which.
* The training reference record was timed while other work ran on the machine, so its
  times were not used; the speed numbers come from `bench`, run back to back.
* The reference record (`records/reference.json.gz`) is itself a working-tree run
  (fd2048c plus uncommitted step-3 files); the Python agent files it ran were the
  committed ones, and its source digests are in the record.

## Reproduce

```sh
.venv/bin/python scripts/build_native.py                              # build native/
.venv/bin/python -m block_stack_ai.experiment011 reference --jobs 24  # Python games, about 4 minutes
.venv/bin/python -m block_stack_ai.experiment011 parity               # C++ on the same games, compared
.venv/bin/python -m block_stack_ai.experiment011 bench --jobs 24      # the speed measurement, about 3 minutes
.venv/bin/python -m block_stack_ai.experiment011 evaluate             # 300 held-out games, about 20 seconds (runs/ only)
.venv/bin/python -m block_stack_ai.experiment011 verify experiments/011-native-speed/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment011 summarize experiments/011-native-speed/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment011 diverge RECORD [--baseline RECORD]   # if games ever differ
```

Records are written under `runs/` only and copied into `records/` by hand. The reported
held-out run's temporary record was `runs/20261028T122719046771Z-011-heldout/run.json.gz`;
the retained copy is `records/run.json.gz`. The earlier run's was
`runs/20261028T121633663012Z-011-heldout/run.json.gz` (not retained).
