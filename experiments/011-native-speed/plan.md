# Experiment 011 - plan: a native (C++) reach_plan

Status: plan, written 2026-10-28 and revised after an independent review the same
day. Progress through the steps is in the Git history. Before the held-out run,
`predeclared.md` is written from the "Success rule" section and is not edited
afterwards.

## Question

Can a C++ port of `reach_plan` (Experiment 010's agent with Experiment 009's
numbers) play **exactly the same games** as the Python one, at least **50x faster**?

The port does not make the agent stronger on its own. It makes the next steps
affordable: a full CEM run (009 stopped at 4 of 12 iterations because each took
17-35 minutes), more training seeds, deeper search, and later a learned value
function that needs millions of positions.

## Where the time goes now

Measured on 2026-10-28, one process, `reach_plan` at 30 Hz / 300 ms, seed 12345 (not
a held-out seed), first 20,000 frames (304 pieces, level 18):

| Part | Share of the time | Notes |
| --- | --- | --- |
| `reach._search` (movement search) | about 48% | about 170 searches per piece (commit and adjust) |
| `value_of` (board evaluation) | about 47% | about 4,800 boards scored per piece; `column_heights`, `field_features`, the transition features |
| `settle_columns` | about 4% | one per option |
| Engine `game.step` (ctypes) | under 1% | 9.4 microseconds per frame |

That is 89 ms of deciding per piece in one process. In 010's real run (30 games at
once) a game spent about 140 s deciding (860 pieces, 43,000 frames on average) and
the 300-game evaluation took about 25 minutes.

**Why the game loop goes to C++ too.** If only the search moves to C++ (about 1 ms per
piece), the Python frame loop is what's left: about 50 frames per piece at roughly
10-15 microseconds each (ctypes step plus the agent's per-frame bookkeeping), so
about 0.75 ms per piece. That caps the speed-up near 50x. With the whole game in C++
(the engine's own `blocks_core` library, no ctypes per frame), the estimate is about
1 ms per piece and **80-100x**. These are estimates from the profile; the experiment
measures the real numbers.

## What gets built

Everything new lives in fallgorithm. `../block-stack` is not edited; the C++ links
its `blocks_core` static library (the same engine source the Python binding's native
library is built from, so the engine fingerprint is recorded as before).

```
native/
  CMakeLists.txt        builds .build/native/libfallgorithm_native.so; adds ../block-stack
                        (app, tests, python targets off) and links blocks_core
  board.hpp             column bitmasks (same layout as pathaware: bits 0-1 hidden,
                        2-21 visible), settle_columns, gravity, level_for_lines
  eval.hpp              tuned_plan's value_of and phase rule, from 20 params
  reach.hpp             reach.py's frame-by-frame search and the walk back to masks
  search.hpp            reachplan.search: commit (preview unknown) and adjust (preview
                        known), beam of two, average over the seven unknown pieces
  agent.hpp             BenchAgent.act: the per-frame state machine (commit at spawn,
                        adjust at the reaction frame, tap timers, drought counter)
                        (the headers hold the code itself, so the search can inline it)
  play.cpp              one whole game on blocks::Game with 008's stop rules
                        (top-out, line cap, frame cap)
  c_api.cpp             extern "C" entry points (below)
scripts/build_native.py one command to configure and build (like setup_engine.py)
src/block_stack_ai/native.py        ctypes loader and thin wrappers (like engine.py)
src/block_stack_ai/experiment011.py harness: parity, bench, evaluate, verify, summarize
tests/test_native.py                differential tests (Python vs C++)
```

C entry points (ctypes, no new Python dependency, same style as block-stack's own
binding):

* `fn_settle`, `fn_value`, `fn_reach` - one function each, for the differential tests.
* `fn_decide` - one commit or adjust decision from a position: returns the chosen
  placement `(orientation, x, y)` and its masks. Used by the tests and to find the
  first differing decision if two games ever diverge.
* `fn_play_game` - one whole game from a seed, the format, the 20 resolved params and
  the caps. Returns the input bytes, the engine's final score, lines, level and frame
  count, the stop reason and the agent's `pieces`, `adjusts`, `switches`.

**The Python stays the reference.** `reach.py`, `reachplan.py`, `tunedplan.py`,
`benchplan.py`, `limits.py` and `wellplan.py` are not touched. The C++ is a
translation that must agree with them; when they disagree, the Python is right.

**Results are still checked by the engine through Python.** Each recorded game's
inputs are replayed on the Python binding with 009's existing `replay_outcome` (which
uses 008's `_stop_reason` and `_result`), so the per-game result dict (score, lines,
level marks, clear sizes) is built by the same code as 009's and 010's records, not by
new C++ accounting. `pieces`, `adjusts` and `switches` come from the C++ agent, and
`decision_seconds` holds the C++ game's wall time (010's `summarize` reads that
field). `verify` then checks the record with 009's `_replay`. The C++'s own final
counters must match the replay.

**Scope.** Only `reach_plan` at the benchmark rules (`classic_ntsc_double_killscreen`,
endless mode, start level 18). Not `limits.py` / `tuned_plan`, not the 004-006 agents
(their retained checks pin their Python files anyway). The 3-ply shape and the beam of
two are hard-coded as in the Python; making depth or beam a setting belongs to the
experiment that needs it.

## The traps that would break "exactly the same"

Found while reading the Python. Each one gets a test.

1. **Dict order in `reach.py`.** The live states of a frame are a dict keyed by
   `(shift timer, rotate timer)` and are walked in insertion order. That order decides
   which state is stored for a lock (`locks.setdefault`) and which predecessor
   `_walk_back` picks, so it decides the masks. The lock spot is the same either way,
   but different masks give a different mid-flight state at the adjust frame, and the
   game can then split. The C++ keeps each frame's states in a small vector in
   insertion order, not in an array indexed by timers.
2. **Floating-point order.** `value_of` adds its terms left to right; `unknown_value`
   does `total += value * (1/7)` from 0.0 in I, J, L, O, S, T, Z order. GCC's default
   (`-ffp-contract=fast`) can fuse `a * b + c` into one FMA instruction, which rounds
   differently from Python. Build with `-ffp-contract=off`, never `-ffast-math`, and
   compare doubles with `==` in the tests.
3. **Tie-breaks and option order.** `reach.py` returns the placements sorted by
   `(orientation, x, y)`, not in the order the locks were found, and that order decides
   every tie (equal values are common: different boards often have the same features).
   `_best`: the first option wins ties (strict `>`), and it keeps the first option even
   when every value is `-inf`. The commit search starts at `current[0]` / `-inf`. The
   beam is a stable sort on `(-value, order)`, top two; within it, branches without a
   preview placement are skipped and `beam[0]` is the fallback.
4. **`-inf`.** An unknown piece with no placement contributes `-inf`; sums and
   comparisons with `-inf` must behave as in Python (they do with IEEE doubles, as long
   as nothing produces a NaN).
5. **Zero-weight extras are skipped**, not multiplied by 0 (`make_rules` builds
   `extras` only for non-zero weights). Same result in practice, but copy it exactly.
6. **The observation.** Only the 20 visible rows; the hidden rows are erased
   (`visible_grid`). Python ints are unbounded and `reach.py` uses negative masks for
   walls and the floor; the C++ uses signed 64-bit integers with arithmetic right
   shift (defined behaviour in C++20), which matches Python's `>>`.
7. **Flights and levels.** Commit and adjust start from the real piece state
   (position, gravity counter, first-piece delay, tap timers). The preview and unknown
   plies start from a fresh spawn (`SPAWN`) at the level after the clears
   (`level_for_lines`), but **only their gravity uses that level**: the phase rule is
   built once per search from the engine's real level (`phase_rule(level)` in
   `reachplan.search`) and its height budget is used at every ply. With 009's
   `survival_level` of 29, taking the ply's level for the phase would split games at
   the 28-to-29 level-up. Gravity: period capped at level 29, two rows per tick from
   level 39 on this ruleset.
8. **The agent's state machine.** The drought counts the current piece only at commit,
   and the current or the preview piece at adjust (and at spawn when the reaction time
   is 0). Masks are indexed by `frame - base`; the tap timers update after every frame's
   mask; the adjust runs at `frame == reaction_frames` only if the piece has not locked.
   The piece counter starts at -1 (the engine's `piece_count` is unsigned, so the C++
   needs a signed copy). `switches` compares `(orientation, x)` only, not `y`, and the
   previous target is cleared at each spawn.
9. **`reach.py` details.** The 600-frame cap; the overlapped-spawn rule (a piece that
   cannot leave an overlapped spawn is a top-out, not a placement); `_walk_back` drops
   the trailing idle frames.

## Steps

Each step ends at a commit with its tests green, after an independent Opus review (as
in 008-010). Coding steps can go to Sonnet subagents with narrow, file-level briefs.

1. **Build and board.** `native/` skeleton, `scripts/build_native.py`, `native.py`
   loader (a clear error if the library is not built), `settle`, `level_for_lines`,
   gravity, and `value_of` in both phases. Test: random boards (including tall and holey
   ones) with 009's params and with random params; settled boards, cleared counts and
   values equal to Python's exactly.
2. **Reach.** Port `reach.py`. Test: random boards (overhangs, tall stacks, cells in
   the hidden rows), all seven pieces, levels 18/19/28/29/38/39/45, tap intervals 2-5,
   random first-piece delays, gravity counters, tap timers and mid-flight poses; the
   C++ placement list **in the same order, with every placement's masks**, equals
   Python's.
3. **Python reference games, then the search.** 009 kept only the score and lines of
   its training games, so first play the 24 training seeds with Python `reach_plan`
   (about 3 minutes on 24 workers; 010's `_play`) and keep that record: it is the
   reference for step 4 and the Python timing for the speed rule. Then port
   `reachplan.search` (commit and adjust). Test: positions taken from that record with
   010's `spawns()`, with and without the preview, and mid-flight adjust states; the
   same chosen placement and masks.
4. **Agent and game loop.** Port `BenchAgent.act` and the game loop on `blocks::Game`.
   Test: the C++ plays the 24 training seeds; each game's input bytes must equal the
   step-3 Python record's, and the engine replay must give the same results. Also 8
   training seeds each at 15 Hz / 300 ms and 30 Hz / 0 ms against fresh Python games
   (covers a 4-frame tap interval and the no-commit branch), and a short test with tiny
   caps (5 lines, 2,000 frames) against Python `_play`, because no recorded game
   reaches the 430-line or 150,000-frame caps. If games split, `experiment011 diverge`
   reports the first decision where they differ, with the board and both choices.
5. **Speed, then the held-out run.** Write `predeclared.md`. Measure speed on the
   training seeds only (see below). Then play Experiment 008's 300 held-out seeds at
   30 Hz / 300 ms with the C++ agent, write the record (010's episode format, so
   009/010 tools read it), verify it on the engine, and compare it with Experiment
   010's retained record (made on the same engine commit, 4d46782): for every seed,
   the same initial state hash, the same input bytes, and the same result fields
   except `decision_seconds`. (The whole files cannot match: the creation time, code
   versions and source digests differ.) Notes, `result.json`, README section, the
   experiments index row, and an 011 entry in `quickplay.EXPERIMENTS` for the launcher
   (play a new game, watch a recorded one, run the evaluation).

## How speed is measured

Same machine, same session, nothing else heavy running, training seeds only:

* **Per game:** mean seconds per game for the 24 training seeds on 24 workers, Python
  `reach_plan` against C++ (the C++ figure includes the ctypes call, not the Python
  replay). This is the number the success rule uses.
* **Per decision:** one process, the same sampled positions for both, by level band
  (18-28, 29-38, 39+), commit plus adjust, caches emptied first as in 010.
* **Reported as well:** wall-clock time of the 300-game held-out evaluation at 30
  workers (010 took about 25 minutes), and the time of the Python replay that builds
  the record (it costs about 0.4 s per game and is not part of the agent).

## Success rule (draft for `predeclared.md`)

1. **Exact:** on all 300 held-out seeds, the C++ agent's input bytes and result fields
   (all but `decision_seconds`) are identical to Experiment 010's retained record, and
   `verify` replays all 300 on the engine with every result matching. Also identical on
   the 24 training seeds and the two extra formats' 8 seeds each. A single difference is
   a failure: it is reported and fixed in the C++, never accepted.
2. **Fast:** the per-game speed-up on the training seeds (above) is at least 50x.

Reported whatever the outcome: the per-decision speed-up per level band, the 300-game
wall-clock time, and the projected cost of one 009-style CEM iteration (32 candidates x
24 seeds = 768 games).

## Open questions and risks

* **Hidden divergence sources** beyond the list above. The step-by-step tests are there
  so a mismatch is found at the smallest piece (a value, a reach set, a decision)
  before whole games are compared.
* **The engine API.** The game loop reads `blocks::State` directly: `x`, `y`,
  `orientation`, `gravity_counter`, `first_delay_remaining`, `piece_count`, `phase`,
  `current`, `next`, the 200-cell board, `lines` and `level`, the same fields the
  Python binding copies. `terminal` comes from `Game::terminal()` and the start level
  and ruleset from `game.config()`. To mirror: the piece enum has `PIECES`' order,
  `Phase::Active` is `"active"`, a board cell is filled when non-zero, and board row r
  is model bit r + 2. The loop must stop exactly where 008's `_stop_reason` does
  (top-out, line cap 430, frame cap 150,000, checked before each frame's input).
* **The build.** The C++ needs the block-stack source beside fallgorithm (already a
  requirement) and a C++20 compiler (already used for the engine). Tests that need
  the library get a `native` marker and are skipped when it is not built.
* **If it is only 30x.** Still useful for training; the rule says it fails the 50x bar,
  and the notes say where the remaining time goes.

## What it unlocks (later experiments, not this one)

* Finish 009's CEM: all 12 iterations, more seeds, and train with reach (009's numbers
  were tuned for the fixed-route model). At about 1 s per game an iteration would take
  under a minute on 30 workers instead of 17-35 minutes.
* Deeper or wider search (a 4th ply, a wider beam), which 010's autopsy points at.
* A learned value function from self-play, which needs millions of evaluated positions.
