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
from the episode seed. 20 episodes, the CLI doctor and the current 64 unit and
nine native integration tests were run; the saved suite record was replayed
with `verify`.

**Placement model:** A placement is a straight drop that enters its column at
the engine's spawn origin row and then descends only downward, through
consecutive free origins, stopping at the first obstruction or the floor. The
model's `y` is the engine's own piece-origin row (engine row = model row -
`HIDDEN_ROWS`), and the entry row is the measured spawn origin
`SPAWN_ORIGIN_Y = 0`: `Game::spawn` (`core/src/game.cpp:197`) sets `state_.y = 0`
and `Game::process_rotation` leaves the origin untouched. Probed directly on the
registered read-only library, not assumed: a spawn trace reports
`(x=5, y=0, orientation=0)`, `set_piece` reports origin row 0 for every piece at
every orientation, and a clockwise press re-reads the same origin. Lateral
movement during the descent and entering in one column and sliding over to
another are **out of scope**; the controller aligns the piece at the spawn row
and then holds Down, so the enumerated set is what it can actually execute. A
column blocked at its spawn origin contributes no placement at all.

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

| Agent | Score mean / median (min-max) | Lines mean / median (min-max) | Frames mean / median (min-max) | Pieces placed mean | Games |
| --- | --- | --- | --- | --- | --- |
| random | 162.9 / 168.0 (124-203) | 0.0 / 0.0 (0-0) | 786.7 / 807.0 (623-948) | 19.9 | 10 game over |
| greedy | 106621.9 / 77953.5 (22482-334495) | 118.9 / 97.0 (28-309) | 15801.3 / 12911.0 (4686-38158) | 334.7 | 10 game over |

The heuristic survived about 20 times longer (15801.3 against 786.7 frames),
cleared about 119 lines per game against none, and scored about 650 times
higher. Score includes the engine's soft-drop bonus for both agents because
both hold Down after aligning, and the level rises after the start-level
threshold (130 lines at level 18), so per-line score grows in longer episodes.
The random baseline never completed a row: random columns spread the stack
instead of filling rows.

The **`Pieces placed`** column is the number of pieces the engine actually wrote
to the board, counted from the engine's `locked` events minus the failed
topping-out lock: `Game::lock` (`core/src/game.cpp:242`) raises `locked` before
its `fits` check and writes the board only when the piece fits, so the lock that
ends an endless game places nothing, and a piece still in play at a frame-limit
stop has not locked at all. At game over every spawned piece has locked, so the
count is one below `state.stats.pieces` and two below the engine's RNG/preview
selection counter `state.piece_count`, which also counts the initial and next
preview. The runner used to record that preview counter as `pieces`, so the
earlier values of this column (21.9 and 336.7) were two too high; records now
carry the placed count as `pieces_placed` (the older `pieces` key is still read
under its original meaning). The greedy total of **3347** placed pieces is one
below the **3357** lock events the model-fidelity measurement below counts, the
difference being the ten topping-out locks that wrote nothing.

**Model fidelity:** Re-measured on the regenerated record by replaying each
recorded greedy episode and comparing the engine's locked origin with the
placement the greedy policy would have chosen at that piece's spawn state:
**3328 of 3357 locks (99.1%) landed exactly where the model predicted**, and the
model predicted **1208** line clears where the engine cleared **1189**. The 3357
are lock events, one per spawned piece, including the ten topping-out locks that
wrote nothing, so they are one above the `Pieces placed` total of 3347. All 29
divergences show a column difference, nine of them also a wrong orientation and
27 also a different row. The mechanism is unchanged: the piece cannot slide to
the chosen column above a tall stack, so it locks early in the spawn column —
the model's `y` is right for the column it wanted, not for the column it got.
The measurement method is anchored to the previously published numbers: run over
the pre-fix record with the legacy drop rule it reproduces exactly the earlier
3324/3353 locks, 29 divergences, four orientation differences and 1206 model
against 1189 engine clears, so the values above are directly comparable to that
record rather than carried over from it. The metric correction does not move
these numbers: the regenerated record's episodes are identical to the previous
record's in inputs, results and initial hashes (only the piece field differs),
so the replay is the same.

Ceiling behaviour is modelled exactly. The native lock compacts the visible
board alone and keeps the two hidden rows as a separate buffer, so a piece
locked above the visible field keeps its hidden minos when a lower visible row
clears, and the empty row reopens at the top of the visible field. Re-checked
directly against the registered native library in four cases: a hidden-only lock
with no clear, a ceiling-straddling lock that clears visible row 0, a mid-field
clear with the hidden buffer already occupied, and a double clear. In each of
the three clearing cases the engine's `state_.hidden_rows` was exactly the
buffer the lock had written, byte for byte, and the full 22-row board matched
the model's `settle` cell for cell, while the reviewed alternative that shifts
the hidden rows down with the cleared row produced a grid the native engine does
not. The disagreement is a review assumption, not an
engine behaviour: `Game::clear_rows` (`core/src/game.cpp:229`) builds a compact
copy of the 20-row visible board and assigns it to `state_.board`, and never
reads or writes `state_.hidden_rows`; hidden cells are only written on lock when
a mino rests above the ceiling (`Game::lock`). The unit tests
`test_settle_keeps_hidden_rows_in_place_when_a_visible_line_clears` and
`test_settle_shifts_visible_rows_above_a_cleared_row_downward` and the
integration tests
`test_placement_model_matches_a_native_lock_straddling_the_ceiling` and
`test_hidden_rows_survive_a_later_clear_below_the_ceiling` pin both sides. All
three hidden-row regressions fail against a mutant `settle` that compacts the
whole 22-row grid instead (integration 2 failed / 6 passed, unit 1 failed / 42
passed), and the double-clear branch is exercised by the second integration
test. These tests were added after the first run; `settle` itself is unchanged
across every review round, and the hidden rows stay fixed.

**Limitations and useful failures:**

- The model enters at the engine's spawn origin row and descends only downward.
  It ignores lateral movement during the descent and entering in one column and
  sliding over to another, which is exactly the 29-case divergence above: a tall
  stack can block the horizontal path to the chosen column, and the controller
  keeps pressing until the piece locks somewhere else.
- The enumeration's entry rule was wrong until this round. It used to start at
  the top of the 22-row grid — with the piece's topmost cell at grid row 0, two
  rows above the engine's spawn origin for the flat pieces (and coincidentally
  equal for the vertical I). That rule (a) rejected columns the engine can spawn
  into, when the hidden cells were occupied but the visible spawn rows were
  free, and (b) enumerated placements resting *above* the spawn origin that no
  straight drop can reach. The entry is now the measured spawn origin. Probed
  before the change: with both hidden rows of columns 0 and 1 filled, `_drop_y`
  returned `None` for the O at `x = 1` and the T at `x = 1` (the old rule tested
  the hidden cells; the engine spawns an O at visible rows 0 and 1 and accepts
  it); with visible row 0 filled at columns 4 and 5 and every cell below free,
  `_drop_y` returned `y = -2` for the O at `x = 5` and the enumeration offered
  three placements above the spawn origin (`x = 4, 5, 6` at `y = -2`), none of
  which the engine can reach. After the change the first pair is enumerated
  (`(0, 1, 18)`) and the second contributes no placement. Regression tests
  `test_enumeration_accepts_a_column_obstructed_only_in_the_hidden_rows` and
  `test_enumeration_stops_at_an_obstructed_spawn_origin_instead_of_resting_above_it`
  both fail against the legacy rule (at `tests/test_heuristic.py:122` and
  `:143`), and the board-derived
  `test_every_enumerated_placement_falls_through_consecutive_free_origins` now
  also asserts that no placement sits above the spawn origin and fails against
  the legacy rule too.
- The whole-set gate is
  `test_enumeration_matches_engine_straight_drops_from_the_spawn_origin`
  (integration): on two constructed boards — a visible overhang over a stack,
  and minos occupying the hidden buffer while the visible field is empty — it
  drives the engine from the spawn origin for **every** piece, orientation and
  legal column (162 trials per board), via `set_piece` plus Down held until
  lock, and requires the enumerated placement set to equal the engine-reachable
  set. It is sensitive in both directions: a legacy top-of-grid `_drop_y` fails
  it at `('overhang', 'I', 0, 3)` with `y = -1`, and a model that ignores the
  hidden buffer in `fits` fails it at `('hidden-buffer', 'I', 1, 8)`; both
  mutants were run and recorded.
- Effect of the fix on the fixed seeds (supersedes the earlier "6 = 3+1+2"
  account): **6 of 20 episodes are unchanged** (greedy seeds 6, 12, 16, 20 and
  random seeds 8, 10); 14 changed, seven of them only in the executed masks and
  seven also in score, frames or pieces. Piece figures here use the corrected
  placed count (board placements, two below the preview counter the earlier
  draft quoted for a game-over episode).
  - Greedy, six changed: seeds 2, 8 and 14 in the masks only, with identical
    score, frames and pieces; seed 4 (frames 8236 → 8257, pieces 172 → 173),
    seed 18 (frames 4663 → 4686, pieces 107 → 108) and seed 10 (score
    150514 → 150516, frames 23408 → 23456, pieces 478 → 480) also in the result
    fields.
  - Random, eight changed: seeds 2, 4, 6 and 18 in the masks only; seed 12
    (frames 755 → 757), seed 14 (score 179 → 178, frames 851 → 918, pieces
    21 → 23), seed 16 (score 165 → 169, frames 807 → 891, pieces 20 → 23) and
    seed 20 (score 161 → 163, frames 693 → 726, pieces 17 → 18) also in the
    result fields.
  - Masks change while the result stands when the model now picks a reachable
    placement that the controller executes to the same resting position the
    unreachable one described. The greedy summary barely moved (mean score
    106621.7 → 106621.9, frames 15792.1 → 15801.3, pieces 334.3 → 334.7; lines
    mean, median, min and max are identical), while the random baseline samples
    uniformly from the enumeration, so eight of its ten episodes moved (mean
    score 162.4 → 162.9, frames 768.1 → 786.7, pieces 19.3 → 19.9). The record
    below was regenerated after the change and verifies.
- The controller does not replan around a blocked rotation or move: it keeps
  pressing until the piece locks. Near the ceiling this abandons the plan.
- No next-piece lookahead, hold, weight tuning or learning; the classic preset
  offers no wall kicks to model.
- Minos that come to rest in the hidden rows are outside the height features:
  only visible rows are scored, although those hidden cells still block
  placement (the whole-set gate exercises exactly that, on its second board). A
  hidden row that fills is never cleared, because the engine scans the visible
  board alone.
- The suite verifier first accepted any record of the right length whose
  recorded agent and seed were each merely members of the configured lists, so a
  tampered record could duplicate one episode identity and omit another and
  still verify. `verify` now requires the recorded `(agent, seed)` sequence to
  equal the configured Cartesian product in `run_suite` order (agent order, then
  seed order), and the recorded identity must have the written types before the
  values are compared: JSON `true` compares equal to the integer `1`, so a
  boolean seed for a configured seed of `1` would otherwise pass. A unit test
  duplicates, swaps and boolean-seeds episode identities and confirms rejection.
  The retained record above still verifies.
- The version-1 scripted verifier compared the recorded inputs and `result`
  fields but ignored the top-level `pieces` count the writer records beside
  them, so that count could be tampered with or deleted and the record still
  verified. `verify` now compares it whenever the record carries it and leaves
  records that omit it — older records — verifying exactly as before. A unit
  test writes a scripted record through `run_and_save` and checks an untampered
  record, tampered counts (the frame count, `5`, `null`, `true`) and an omitted
  count.
- The reported piece count was the wrong engine field. The runner recorded
  `state.piece_count`, the RNG/preview selection counter, which is incremented
  once for the initial preview and once for `next`, so it is above the number of
  pieces actually placed. The native contract is unambiguous: `Game::reset`
  (`core/src/game.cpp:137`) and `Game::spawn` (`core/src/game.cpp:196`) advance
  `state_.piece_count` for each preview selection and `state_.stats.pieces` for
  each piece that enters play, and a probe on the registered library confirms
  `piece_count == stats.pieces + 1` at spawn and at game over. The count is now
  the number of pieces written to the board, taken from the engine's `locked`
  events minus the failed topping-out lock: `Game::lock` raises `locked` before
  its `fits` check and writes the board only on success, so neither the
  topping-out lock nor a piece still in play at a frame-limit stop is counted
  (`stats.pieces` counts both as soon as they spawn, and a one-frame episode has
  `stats.pieces == 1` with zero locks). Records now carry the placed count as
  **`pieces_placed`** and the summary key is renamed with it; the older `pieces`
  key is still compared against `piece_count`, so every previously saved record
  keeps verifying under its original meaning. The retained record below was
  regenerated with the corrected field (its episodes are otherwise byte-identical
  to the previous one, and all 20 ended at game over, so the count is one below
  both the lock events and `stats.pieces`), and the previous record still
  verifies. Regressions: a unit test pins the offset on a stop where nothing is
  in play, another pins a stop with an unlocked piece, another pins the failed
  topping-out lock, unit tests round-trip the new and legacy keys of both record
  formats (rejecting a legacy `pieces` that holds the placed count), unit tests
  reject a boolean seed identity and a boolean piece count that would compare
  equal to a configured seed of 1 and a count of 0, and an integration test
  drives a full native top-out and a one-frame stop and requires the recorded
  count to equal the native board placements.
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

`run` writes its record under the ignored project-root `runs/` directory, and
`verify` replays that path directly. To keep a copy beside the experiment, copy
the directory and verify the copy:

```sh
mkdir -p experiments/001-greedy-heuristic/runs
cp -r runs/<new-run-id> experiments/001-greedy-heuristic/runs/
.venv/bin/block-stack-ai verify experiments/001-greedy-heuristic/runs/<new-run-id>/run.json
```

The record used here was copied that way to the retained, still-ignored
`experiments/001-greedy-heuristic/runs/20260926T054458996351Z-697e2202/run.json`
(1.8 MB, format version 2, every frame mask retained) and verifies from there,
with the CLI's own copy left at
`runs/20260926T054458996351Z-697e2202/run.json`. Its episodes are identical to
the previous retained record's in inputs, results and initial hashes, differing
only in the piece field: `pieces_placed` here is two below the legacy `pieces`
there (the preview counter, above the spawned count and the placed count). That
previous record,
`experiments/001-greedy-heuristic/runs/20260926T020359855832Z-12e7c9a3/run.json`,
is kept beside it and still verifies under the legacy semantics, which is the
backward-compatibility check on a real artifact.

This is a **working-tree run**. The engine was dirty at commit
`0e56c3beb7e4165e793ff326e3600d973e236cb8` and fallgorithm was dirty at commit
`d5d0d9c2222e3e7709db8ec1912e0f21739b2faa`, so the Git metadata alone cannot
reconstruct the uncommitted source. Environment: the read-only sibling checkout
at `../block-stack` through the installed `block_stack` binding, the native
library from `.build/engine/libblocks_native.so` (`BLOCKS_NATIVE_LIB`), Python
3.12.14, no NumPy (board rows arrive as tuples), and no native-engine change.
[result.json](result.json) is the compact retained summary of this record.

**Lesson:** The placement model, the enumerated scoring and the frame-level
execution are reproducible end to end, and the enumeration now matches the
engine's whole reachable placement set on the boards the gate covers, so this is
a usable baseline for later approaches. The remaining gap is still modelling
where the piece can actually travel horizontally, which the 29 divergences and
the top-outs on tall stacks come from. The next experiment can add one-piece
lookahead or a planner on top of this enumeration and compare against these
numbers.
