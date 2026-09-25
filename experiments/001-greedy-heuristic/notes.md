# 001: Greedy heuristic placement baseline

**Question:** Does a one-piece greedy heuristic that scores the settled board
outperform a uniform random legal-placement baseline on identical fixed seeds,
using only the existing engine connection and run-recording path?

**What was tested:** Two placement agents over the same 10 fixed seeds
(`2, 4, 6, 8, 10, 12, 14, 16, 18, 20`), level 18 endless
(`classic_ntsc_extended`, matching [000](../000-connection/notes.md)), frame
limit 60000, in [config.json](config.json). Each agent enumerates the unique
rotations and legal columns of the current piece, simulates the straight drop,
locks and clears lines, scores the resulting board, and executes the chosen
placement with frame-level masks (rotate, one press per horizontal step, then
Down held). Only the placement choice differs: the heuristic takes the highest
score, the baseline picks uniformly from the same list with a Python RNG seeded
from the episode seed. 20 episodes, the CLI doctor and the then-current 36 unit
and five native integration tests were run; the saved suite record was replayed
with `verify`.

**Heuristic:** Fixed weights, never tuned against these seeds, per
[`src/block_stack_ai/heuristic.py`](../../src/block_stack_ai/heuristic.py):
score = `1.0 * lines_cleared - 1.0 * holes - 0.5 * aggregate_height -
0.5 * bumpiness - 1.0 * max_height`. Features are conventional: a hole is an
empty visible cell below the topmost filled cell of its column, heights count
visible rows only, bumpiness is the sum of adjacent column-height differences.
Ties break by taking the first placement in canonical enumeration order
(orientation ascending, then column ascending), which is the leftmost or
lowest-orientation of the equal-scoring candidates.

**Observed result:** All 20 episodes ended by topping out; the frame limit was
never reached.

| Agent | Score mean / median (min-max) | Lines mean / median (min-max) | Frames mean / median (min-max) | Pieces mean | Games |
| --- | --- | --- | --- | --- | --- |
| random | 162.1 / 165.5 (124-203) | 0.0 / 0.0 (0-0) | 765.3 / 780.0 (623-948) | 21.2 | 10 game over |
| greedy | 106621.7 / 77953.5 (22482-334495) | 118.9 / 97.0 (28-309) | 15792.1 / 12911.0 (4663-38158) | 336.3 | 10 game over |

The heuristic survived about 20 times longer, cleared about 119 lines per game
against none, and scored about 650 times higher. Score includes the engine's
soft-drop bonus for both agents because both hold Down after aligning, and the
level rises after the start-level threshold (130 lines at level 18), so per-line
score grows in longer episodes. The random baseline never completed a row:
random columns spread the stack instead of filling rows.

**Model fidelity:** Replaying all ten heuristic episodes, 3324 of 3353 locks
(99.1%) landed exactly where the model predicted; the model predicted 1206 line
clears where the engine cleared 1189. The 29 divergences all came from a
blocked column path: the piece could not slide to the chosen column above a
tall stack, so it locked early (29 column differences, four of them also stuck
in the wrong orientation).

Ceiling behaviour is modelled exactly. The native lock compacts the visible
board alone and reports the two hidden rows as a separate buffer that it never
shifts, so a piece locked above the visible field keeps its hidden minos when a
lower visible row clears, and the empty row reopens at the top of the visible
field. A native lock that straddles the ceiling and clears the row below it
settles to the same grid the model's `settle` returns, cell for cell, and the
reviewed alternative that shifts the hidden rows down with the cleared row
produces a grid the native engine does not. The unit tests
`test_settle_keeps_hidden_rows_in_place_when_a_visible_line_clears` and
`test_settle_shifts_visible_rows_above_a_cleared_row_downward` and the
integration test
`test_placement_model_matches_a_native_lock_straddling_the_ceiling` pin both
sides. These were added after the run above, so the suite is now 38 unit and
six native integration tests; `settle` and enumeration behaviour is unchanged
and the recorded metrics stand.

**Limitations and useful failures:**

- The model assumes a straight drop from above the stack. It ignores the
  horizontal path from the spawn column and overhangs, which is exactly the
  29-case divergence above.
- The controller does not replan around a blocked rotation or move: it keeps
  pressing until the piece locks. Near the ceiling this abandons the plan.
- No next-piece lookahead, hold, weight tuning or learning; the classic preset
  offers no wall kicks to model.
- Minos that come to rest in the hidden rows are outside the height features:
  only visible rows are scored, although those hidden cells still block
  placement. A hidden row that fills is never cleared, because the engine scans
  the visible board alone.
- The suite verifier first accepted any record of the right length whose
  recorded agent and seed were each merely members of the configured lists, so a
  tampered record could duplicate one episode identity and omit another and
  still verify. `verify` now requires the recorded `(agent, seed)` sequence to
  equal the configured Cartesian product in `run_suite` order (agent order, then
  seed order); a unit test duplicates and swaps episode identities and confirms
  rejection. The retained record above still verifies.
- Adjacent seeds are not independent. With seeds `1..10` the greedy episodes
  for `(2,3)`, `(4,5)`, `(6,7)` and `(8,9)` were identical in every recorded
  field, and reading the spawned pieces directly showed the same first twelve
  pieces for each pair: the engine's LFSR drops bit 0 on its first advance and
  piece selection reads only the high byte, so `2k` and `2k+1` share a piece
  sequence. The random baseline still differed within a pair, because its own
  choice stream is seeded from the episode seed. The recorded seeds are the
  even values `2..20`, which give ten distinct trajectories. This is an engine
  property, not a defect of the agents.

**Reproduce:** From the project root, after the setup in the
[project README](../../README.md):

```sh
.venv/bin/block-stack-ai doctor
.venv/bin/block-stack-ai run --config experiments/001-greedy-heuristic/config.json
.venv/bin/block-stack-ai verify runs/<new-run-id>/run.json
```

This is a **working-tree run**. The engine was dirty at commit
`0e56c3beb7e4165e793ff326e3600d973e236cb8` and fallgorithm was dirty at commit
`970c849b65ef8f0410096824b1e0b5ec16f700a9`, so the Git metadata alone cannot
reconstruct the uncommitted source. Environment: the read-only sibling checkout
at `../block-stack` through the installed `block_stack` binding, the native
library from `.build/engine/libblocks_native.so` (`BLOCKS_NATIVE_LIB`), Python
3.12.14, no NumPy (board rows arrive as tuples), and no native-engine change.
The temporary record is `runs/20260925T073542509599Z-14e63372/run.json`
(1.8 MB, format version 2, every frame mask retained); [result.json](result.json)
is the compact retained summary. Verifying the record replays all 20 episodes
against the native engine and warns that the engine is a working-tree run.

**Lesson:** The placement model, the enumerated scoring and the frame-level
execution are reproducible end to end, so this is a usable baseline for later
approaches. The remaining gap is modelling where the piece can actually travel,
which the 29 divergences and the top-outs on tall stacks come from. The next
experiment can add one-piece lookahead or a planner on top of this enumeration
and compare against these numbers.
