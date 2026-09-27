# 002: Path-aware greedy with one-piece lookahead

**Question:** Can a placement agent that only aims at placements its own frame
controller can really execute under the engine's gravity, and that uses the
player-visible next piece for one piece of lookahead, beat the frozen 001
straight-drop greedy baseline on the same fixed seeds and gameplay config?

**Base and environment:** This worktree is based on the latest main,
`6d0b886cc325ca47df14a7e14b28ac36aa67f5c7` (`Merge pull request #7 from
HarmonChew/codex/experiment-menu`, tree
`d5467fc09bcb863103e185aa0fc17a30d5280fe3`), confirmed with `git rev-parse HEAD`
and `git log -1`. The brief named the PR #4 merge `a6fb73c` as the base; that
commit is an ancestor of this one (001 landed on it as `2bac938`) and main has
since merged live desktop control (#6) and the experiment launcher (#7), so the
recorded base is main's current tip. Issue #5 is absent from it: `frame_limit` is
a positive integer everywhere (`experiments/001-greedy-heuristic/config.json`
keeps 60000, this experiment uses 200000), no `frame_limit: null` path exists,
and there is no `experiments/002-whole-games` directory or uncapped execution.
The native dependency is the registered read-only Block Stack checkout at
`8ca41587` **recorded dirty** — a working-tree run — with the registered library
`/home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so`.
In this harness the registered virtualenv is
`/home/harmon-chew/projects/code/fallgorithm/.venv`; its editable `fallgorithm`
path points at a project root this worktree does not have, so every command
below selects this tree with `PYTHONPATH=<worktree>/src`. The validation probes
are retained in [`probes/`](probes/) so each recorded command can be re-run
without reading the harness transcript.
001's `result.json` records engine `0e56c3b`; re-running 001's config on this
engine reproduces 001's published summary exactly (evidence item 7 below), and
the `greedy` episodes of this experiment carry 001's published fidelity
(3328/3357 locks landed, 1208 predicted against 1189 engine clears), so the two
experiments are measured on the same gameplay.

**What was tested:** Two placement agents over the same 10 fixed seeds
(`2, 4, 6, 8, 10, 12, 14, 16, 18, 20`) and the same gameplay config as 001
(`classic_ntsc_extended`, endless, `start_level` 18, height 0), in
[config.json](config.json), with `frame_limit` 200000 (001's 60000 would cut the
new agent's game off; 200000 is a configured safety bound, not a game rule).
`greedy` is the frozen 001 agent: the same straight-drop enumeration and the same
fixed weights. Its config still parses and runs unchanged and reproduces
001's published summary exactly (evidence item 7), and the shared controller rule
reproduces the base controller's own masks on all 24 960 enumerated states
(evidence item 2), so the refactor did not move `greedy` or `random`.
`lookahead` is the new agent. 20
episodes, the CLI doctor, and the current 110 unit and 21 native integration
tests were run; the saved suite record was replayed with `verify` and a second
full run was compared against it. The commands, their stdout and their exit
status are in the validation evidence below.

**The preview piece (checked before implementing):** The registered binding
exposes the player-visible next piece on the same observation the runner passes
to `act(state)`: `block_stack/python/block_stack/__init__.py` builds
`State.next_piece` (field at line 227) from the native `next_piece` field (line
55) in `_state_from_native` (line 309), which `core/src/c_api.cpp:65` fills from
`State::next`. The engine sets `next` from the same piece-selection call the
runner counts in `Game::piece_count` (`Game::reset` `core/src/game.cpp:150`,
`Game::spawn` `:214`) and then promotes it into the current piece (`:198`), so it
is the preview the player is shown, not hidden RNG state. Probed directly on the
registered library (`evidence.py engine-preview`, item 8 below): a fresh game
reports `current J, next Z`, the piece the preview named spawned on each of the
next three spawns, a spawn tick reports `x 5, y 0, orientation 0, first_delay 0,
gravity 0, soft 0, previous_input 0`, and the module reads no RNG field. Nothing
in the agent reads `rng_state` or any other hidden field, and the engine is not
modified.

**Path-aware reachability:** A candidate is an `(orientation, x)` the controller
aims at. The plan is simulated frame by frame from the engine's native spawn
state with the very mask function the controller calls
(`pathaware.plan_mask`): rotate toward the aimed orientation by the shorter way,
one press per horizontal step, a release frame after every press, then Down held
until the engine locks the piece. Each simulated frame mirrors `Game::tick`'s
active phase order (`core/src/game.cpp:409`): horizontal first
(`:328`, including the engine's "a held Down suppresses shifting" rule and its
DAS counters), then rotation (`:354`, no wall kicks), then gravity/soft drop
(`:367`), with `gravity_counter`, `soft_drop_counter` and the first-piece delay
advanced exactly as the engine advances them, `Game::fits` (`:173`) deciding
every move, and `Game::lock` (`:251`) committing a failed downward attempt,
including its own final fit check that turns an origin the piece never left into
a top-out that writes nothing. `Game::spawn` (`:197`) has no collision test, so
an origin that does not fit is still playable: the first successful downward
attempt moves the piece off the overlap and the plan continues, which is what
the `overhang` board below pins. A candidate is admissible only when the
simulated lock is exactly the aimed `(orientation, x)` and the engine would
really write the piece there. Gravity is not a detail here: at level 18 it drops
the piece every third
active frame while the controller is still pressing, which is what lets the
piece slide under a two-row ceiling (`ceiling` board below) and what stops it
crossing a wall it would have fitted past from above (`wall` board below).
Boards are held as ten column bitmasks; the bitmask settle/feature code mirrors
`heuristic.settle`/`heuristic.board_features` and is pinned to them by a unit
test over constructed and random boards. The straight-drop enumeration and
001's greedy agent are untouched: on an unobstructed board with the first-piece
delay the reachable set equals `enumerate_placements` element for element,
scores included, and the 001 config still produces its published summary
unchanged.

**Lookahead:** For every admissible placement of the current piece, the piece is
locked into the model grid and the **next** piece is placed on the result by the
same reachable-set rule, scored with the existing fixed features and weights
(no tuning). The lookahead value of a current placement is the highest score
among that next piece's admissible placements; the current placement with the
best value is chosen. A current placement that leaves the next piece no
admissible placement at all has value `-inf`: the rejected Down fallback is not
a placement, and scoring its board would let a move that strands the preview
piece outrank one that leaves it a placement, so it loses to every placement
that leaves the next piece one and is kept only when every current placement
shares that fate. Ties keep the first placement in canonical enumeration
order (orientation ascending, then column ascending), the same rule and order
001's greedy uses, pinned by a unit test that shows two placements tied at
`-7.0` on the O of an empty board with an I preview. When no current placement
is admissible the agent keeps pressing Down where the piece spawned, exactly
001's fallback; that is what happens at the end of every game that tops out, and
it is reported below as the fallback top-out lock rather than as a placement.
The next piece's gravity uses the level the current placement's clear would
leave (`pathaware.level_for_lines`, mirroring `Game::update_level`,
`core/src/game.cpp:241`, including the strict wrap and the challenge mode that
never raises its level); the current piece uses the level the observation
reports.

**Observed result:** 20 episodes. The lookahead agent survived about 5.8 times
longer, cleared about 7.7 times as many lines and scored about 26 times higher
per game on average — and **one of its ten episodes stopped at the configured
frame cap instead of ending**, so that episode's figures are a safety stop, not
a game over.

| Agent | Score mean / median (min-max) | Lines mean / median (min-max) | Frames mean / median (min-max) | Pieces placed mean | Stopping reasons |
| --- | --- | --- | --- | --- | --- |
| greedy | 106621.9 / 77953.5 (22482-334495) | 118.9 / 97.0 (28-309) | 15801.3 / 12911.0 (4686-38158) | 334.7 | 10 game over |
| lookahead | 2822959.9 / 1513435.5 (256671-10334568) | 912.8 / 734.5 (254-2137) | 92024.9 / 76491.0 (33940-200000) | 2314.4 | 9 game over, 1 frame limit |

Per episode: greedy is identical to 001 (it is the same agent) and every one of
its games topped out. Nine of the ten lookahead games topped out too, at
33940-143005 frames (254-1515 lines, 669-3820 pieces). The tenth (seed 18) was
still alive at frame 200000 with 2137 lines, 5353 pieces and score 10334568; it
is a **configured safety stop**: the record says `frame_limit`, the episode has
no `game_over` event, and its 5353 locks equal its 5353 placed pieces (a game
that tops out has one more lock than placed pieces). Its figures are not
excluded from any summary; they are reported exactly as measured. Score includes
the engine's soft-drop bonus for both agents, and the level rises after the
start-level threshold (130 lines at level 18), so per-line score grows in the
longer episodes.

The **`Pieces placed`** column is the number of pieces the engine actually wrote
to the board, counted from the engine's `locked` events minus the failed
topping-out lock, as in 001 (a piece still in play at the frame-limit stop has
not locked and is not counted either). At game over the count is one below the
`locked` events; at the frame-limit stop the two are equal.

**Exact landing fidelity:** Replayed each recorded episode and compared the
placement the agent chose for each spawned piece with the origin the engine
actually locked it at (independently reproduced by `probes/evidence.py replay`,
section 4 of the validation evidence) (the method 001 used; the replayed inputs were compared
with the record first, so the comparison runs on the recorded trajectory):

| Agent | Locks landed exactly as predicted | Model divergences | Classification | Predicted clears | Engine clears |
| --- | --- | --- | --- | --- | --- |
| greedy | 3328 / 3357 (99.14%) | 29 | 29 column, 9 orientation, 27 row | 1208 | 1189 |
| lookahead | 23144 / 23153 (99.96%) | **0** | — | 9128 | 9128 |

The greedy row is exactly 001's published fidelity (3328/3357, 29 divergences,
29 column / 9 orientation / 27 row, 1208 against 1189 clears), which is the
expected result of replaying the same agent and re-confirms the two experiments
share a measurement. The lookahead agent's 9 remaining locks are the terminal
lock of each of the nine games that topped out: at that point no placement is
admissible, the controller falls back to holding Down where the piece spawned,
the first downward attempt fails and `Game::lock` rejects the origin (it is
occupied and the piece never moved off it), so nothing is written and the game
ends.
Each one is the last frame of its episode. **No lock diverged from a placement
the model admitted**, and the clears agree exactly (9128 predicted, 9128
cleared), which is what the reachable set is for: the 29 divergent greedy locks
were all placements the straight-drop model offered and the controller could not
execute.

**Validation evidence:** Every command below was executed in this
working tree with the registered virtualenv interpreter
(`/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python` and its
`block-stack-ai`), and each entry records the command, its complete stdout and
its exit status (no launch lines: every capture is the finished command's whole
output). The probes are retained in [`probes/`](probes/):
`prechange_probe.py` evaluates one regression's contract against pre-change
code, and `evidence.py` runs every other probe as a subcommand.

```sh
export PYTHONPATH=$PWD/src   # this worktree's src; the harness sets this too
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
$PY experiments/002-path-aware-lookahead/probes/evidence.py prechange --sandbox /tmp/exp002-prechange
$PY experiments/002-path-aware-lookahead/probes/evidence.py regressions --sandbox /tmp/exp002-prechange
$PY experiments/002-path-aware-lookahead/probes/evidence.py mask-identity --sandbox /tmp/exp002-prechange
$PY experiments/002-path-aware-lookahead/probes/evidence.py engine-contract
$PY experiments/002-path-aware-lookahead/probes/evidence.py engine-preview
$PY experiments/002-path-aware-lookahead/probes/evidence.py mutants
$PY experiments/002-path-aware-lookahead/probes/evidence.py determinism
$PY experiments/002-path-aware-lookahead/probes/evidence.py timing
$PY experiments/002-path-aware-lookahead/probes/evidence.py baseline
$PY experiments/002-path-aware-lookahead/probes/evidence.py compare runs/<first>/run.json runs/<repeat>/run.json
$PY experiments/002-path-aware-lookahead/probes/evidence.py replay runs/<first>/run.json runs/<repeat>/run.json
```

`evidence.py all` runs every one of those subcommands on this tree and exits 0
(`failures: 0`; 2m56.4s wall clock for the run that replayed the record and its
repeat), so the whole evidence set is reproducible with one command.

**1. Pre-change baseline, test by test.** The pre-change tree is
`git archive HEAD` of the recorded base (`6d0b886`, still `HEAD` because this
work is uncommitted); the driver builds it in `/tmp/exp002-prechange` and imports
*that* tree's `src`, so every probe below runs against pre-change code with the
recorded base commit's behaviour, not against a copy of the new module. A
baseline probe executes one new test's contract as far as pre-change code
can express it, and its exit status is read three ways:

* **`1`** — the base *ran* the contract and its value violates the assertion: a
  genuine failure-before, at the assertion level and never an import error.
* **`0`** — the base ran the analogous, pre-existing behaviour and already
  satisfies it (a frozen-side or fallback invariant).
* **`—`** — the base cannot evaluate the assertion at all, because the contract
  lives in `block_stack_ai.pathaware`, which the base does not have. Each such
  row carries an *executed* substitute (the frozen side, or the engine's own
  behaviour) plus the named mutant that fails when the pinned rule is broken.
  An unimportable module is never counted as a failure-before.

`evidence.py regressions` runs a second, side-by-side comparison by importing the
new test module into the base tree. The base side of *every* row in that run is
reported the same way: the module imports `block_stack_ai.pathaware`, which the
base does not have, so the base fails at collection before any assertion runs and
the driver prints "no pre-change counterpart" for it. Its summary — `1`
assertion-level red -> green (`suite_record`: `create_agent` exists at the base
and rejects `lookahead`), `14` no pre-change counterpart, `0` failures — is a
property of that driver, not the evidence count. The per-regression probes in the
table hold each contract to the pre-change tree on its own terms.

**Which new tests the brief's failing-before requirement applies to.** Not every
new test is a behaviour regression: some pin the new implementation to a
reference that already exists at the base. The 15 new tests split, disjoint and
exhaustive, as:

| Class | New tests | Pre-change evidence |
| --- | --- | --- |
| **A. Behaviour regressions** — assert new consumer-visible behaviour of the new agent | 6: `extra_columns`, `drop_unexecutable`, `rescue_overlapped`, `preview_choice`, the native whole-set gate, the suite record | Each has an executed probe that *fails at assertion level* on the pre-change tree (`1`) and passes here — 7 probes: `extra_columns`, `drop_unexecutable_model`, `native_fence`, `native_overhang`, `preview_choice`, `native_ceiling`, `agent_name`. Every one is a value the pre-change code really computes and that contradicts the new contract (the candidate set in three, the preview in one, the whole-set native gate in one, the agent name in one). |
| **B. Pins on a reference the base already satisfies** — assert the new code preserves pre-change behaviour | 3: `plan_mask`, `fallback`, `deterministic` | The pre-change probe passes (`0`), so a failing-before is impossible by construction: the base evaluates the pinned rule and satisfies it. `mask-identity` drives the base controller's own `act` over 24 960 enumerated states and its mask/release pair matches `plan_mask` on all 24 960 (0 mismatches, re-run on this tree); the Down fallback is the base agent's own behaviour where no straight placement fits; the frozen `GreedyPolicy.choose` is already deterministic. What these tests guard is the new code drifting from the frozen rule, which is what their mutants show. |
| **C. Pins on a reference the base does not have** — assert the new code agrees with the frozen functions or the engine | 6: `column_masks`, `settle_hidden`, `fits_predicate`, `reachable_equals_straight`, `stranded`, `level_for_lines` | Each asserts an equivalence with a reference that exists at the base (`heuristic.settle`/`board_features`/`fits`, the frozen enumeration, the engine's own clear and level) on a subject the base does not have: the base worktree contains neither `src/block_stack_ai/pathaware.py` nor `tests/test_pathaware.py`. The only pre-change failure available to them is an import error, which is not a behavioural failure-before and is never counted as one. Each row carries an *executed* pre-change substitute (the frozen function or the engine's own behaviour, run on the base tree) plus the named mutant that fails the test when the pinned rule is broken. The consumer-visible behaviour behind the last two is covered in class A: `preview_choice` for the preview term, and the native gate for the descent the level feeds. |

So every new *consumer-visible* behaviour the agent introduces has an executed
failing-before probe in class A, and the pinned references that cannot have one
are named, counted and separated as classes B and C rather than presented as
failures they cannot be.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_column_masks_match_the_grid_settle_and_features` | `prechange_probe.py column_masks` | — | No counterpart: `column_features`/`settle_columns` do not exist at the base. Executed substitute: the frozen side the test compares against runs at the base over the test's own 15-grid stream (19 205 `fits`/`settle`/`board_features` states, feature digest 4 362), and `git diff --quiet HEAD -- src/block_stack_ai/heuristic.py` exits 0, so it is the same file the test compares to. `height_off_by_one` fails the regression. |
| `test_settle_columns_keeps_the_hidden_buffer_across_a_clear` | `prechange_probe.py settle_hidden` | — | No counterpart: no `settle_columns`. Executed substitute: the frozen `heuristic.settle` runs at the base on the test's own two boards — `settle('O', x=1, y=-1)` clears 1 row and leaves the hidden buffer `((0,0,0,0,0,0,0,0,0,0), (1,1,0,0,0,0,0,0,0,0))`; `settle('O', x=5, y=18)` clears 2 rows and leaves `((0,0,0,0,0,0,0,0,0,0), (0,0,0,0,1,1,0,0,0,0))` with an empty visible field — and `heuristic.py` is unchanged. `hidden_bits_shifted` fails the regression. |
| `test_fits_predicate_matches_the_cell_by_cell_fit_rule` | `prechange_probe.py fits_predicate` | — | No counterpart: no `_TABLES`/`fits_at`. Executed substitute: the frozen `fits()` runs at the base over 55 176 states (55 176/55 176 pure) and `heuristic.py` is unchanged; the table's outcomes are then compared with the engine's own `fits` by the 1134-plan gate in row 13. |
| `test_reachable_placements_equal_straight_drops_on_an_unobstructed_board` | `prechange_probe.py reachable_equals_straight` | — | No counterpart: only the frozen `enumerate_placements` side exists at the base (162 placements on the empty board; the transcript gives the per-piece counts). Executed substitute: those counts, plus `gravity_removed`, which fails row 5 and so shows the new set comes from the plan simulation rather than a re-derived straight drop. The equivalence itself is asserted on the new tree. |
| `test_reachable_placements_add_columns_the_straight_drop_rejects` | `prechange_probe.py extra_columns` | 1 | The base's only candidate set for the O on the ceiling board is `[(0,1,18) … (0,6,18)]`; the required `(0,7) (0,8) (0,9)` are absent, so `straight < reachable` cannot hold. |
| `test_reachable_placements_drop_plans_the_controller_cannot_execute` | `prechange_probe.py drop_unexecutable_model`, `prechange_probe.py native_fence` | 1, 1 | The base straight model offers the plan `(1,3,0)`; driving the *base controller's* masks at `(1,3)` on the fence board locks the engine at `(1,4,18)`. That divergence is the mechanism behind 001's 29 column divergences. |
| `test_reachable_placements_rescue_an_overlapped_spawn` | `prechange_probe.py native_overhang` | 1 | The frozen straight-drop set omits `(0, 5)` for every piece on the overhang board (the origin is blocked), yet driving the *base controller's* masks from the occupied origin locks the engine at `(0, 5, 18)` with no game over: the pre-change model omits a placement the controller executes by descending out of the overlap. The `overlap_topout` mutant fails the regression. |
| `test_plan_mask_rotates_by_the_shorter_way_and_releases_every_press` | `prechange_probe.py plan_mask`, `evidence.py mask-identity` | 0, 0 | The base controller is driven through its own `PlacementAgent.act` over 24 960 states and emits a mask/release pair for each; the shared `plan_mask` matches all 24 960 with 0 mismatches, so the pinned rule was already the base's behaviour. |
| `test_fallback_holds_down_when_no_placement_is_admissible` | `prechange_probe.py fallback` | 0 | Pre-existing: `GreedyPolicy.choose(())` is `None` and the base agent emits `[4, 4, 4]` (Down) where no straight placement fits. The reachable-set half has no counterpart (`lookahead_choice` does not exist at the base). |
| `test_lookahead_choice_depends_on_the_preview_piece` | `prechange_probe.py preview_choice` | 1 | The base greedy choice is `(0, 1)` whatever the preview — its observation carries no preview field — so the required `(0, 9)` for the S preview cannot hold. The `greedy_value` and `last_maximum` mutants both fail this test. |
| `test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece` | `prechange_probe.py base_value_rule` | — | No counterpart: the base has no lookahead and no next-piece term. Executed substitute: the frozen value rule runs at the base on the three placements this board admits — J(0,5) −154.00, J(3,5) −154.50, J(3,6) −153.50 — and its own choice is J(1,2), so it never penalises a placement for stranding the preview piece and the regression's `-inf` cannot be expressed there. The `stranded_fallback_scored` mutant fails the regression with `assert -155.5 == -inf`. |
| `test_lookahead_choice_is_deterministic` | `prechange_probe.py base_choice` | 0 | The analogous behaviour already holds: the frozen `GreedyPolicy.choose` returns the same placement on five calls over the base's own enumeration (7 placements of the J on the dense board, all five `(1, 2)`), and `pathaware` imports no RNG. |
| `test_level_for_lines_mirrors_the_engine_transitions` | `prechange_probe.py engine_level` | — | No counterpart: the base has no level function. Executed substitute: the registered engine at start level 0 reports level 0 through 9 lines and level 1 first at exactly 10 lines, the threshold `FIRST_TRANSITION_LINES[0]` the mirror copies; `evidence.py engine-contract` then matches the mirror's tables with `core/src/rules.cpp` and the function with a transcription of `Game::update_level` over 160 080 states (0 mismatches), and the replay compares it with the engine's reported level at every one of 1 078 262 recorded frames (0 mismatches). The `level_threshold_inclusive` mutant fails the regression. |
| `test_reachable_placements_match_engine_locks_from_the_spawn_state` (integration) | `prechange_probe.py native_ceiling` | 1 | The base straight model excludes `(0,7) (0,8) (0,9)` on the ceiling board, yet the engine locks at `(0, 7, 18)` when the base controller's own masks aim there: the whole-set gate has no pre-change analogue. The `wrong_gravity_rate` mutant shows the gate catches a broken plan simulation; `gravity_removed` shows the same simulation is load-bearing for row 5. |
| `test_suite_record_with_the_lookahead_agent_runs_and_verifies` (integration) | `prechange_probe.py agent_name` | 1 | Base `AGENT_NAMES == ('random', 'greedy')`; `create_agent('lookahead', 2)` raises `ValueError: unknown agent: 'lookahead'`. The base can evaluate this contract, and `evidence.py regressions` classifies it as an assertion-level failure-before. |

Verbatim stdout of the sixteen pre-change probes
(`evidence.py prechange --sandbox /tmp/exp002-prechange`; the driver printed the
sandbox as `from git archive HEAD = 6d0b886cc325ca47df14a7e14b28ac36aa67f5c7`):

```text
# pre-change sandbox: /tmp/exp002-prechange from git archive HEAD = 6d0b886cc325ca47df14a7e14b28ac36aa67f5c7
########## prechange probe: column_masks
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py column_masks   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: column_masks
grids: 15
frozen settle/fits/board_features states executed: 19205
feature digest over the grids: 4362
frozen side exists and executes; the bitmask mirror it is compared to is new
pathaware importable at base: False
result: the base tree satisfies this probe
exit=0

########## prechange probe: settle_hidden
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py settle_hidden   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: settle_hidden
# single clear: frozen settle('O', x=1, y=-1) -> cleared=1
# single clear: frozen hidden buffer after the clear = ((0, 0, 0, 0, 0, 0, 0, 0, 0, 0), (1, 1, 0, 0, 0, 0, 0, 0, 0, 0))
# double clear: frozen settle('O', x=5, y=18) -> cleared=2
# double clear: frozen hidden buffer after the clear = ((0, 0, 0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 1, 1, 0, 0, 0, 0))
# double clear: frozen visible field after the clear = 0 filled cells (the two cleared rows were all of it)
frozen settle exists and executes; the bitmask settle_columns mirror it is new
pathaware importable at base: False
result: the base tree satisfies this probe
exit=0

########## prechange probe: fits_predicate
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py fits_predicate   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: fits_predicate
grids: 11
frozen fits() states the new table is compared against: 55176
frozen fits() is a pure function on them: 55176 / 55176
frozen side exists and executes; the precomputed _TABLES/fits_at mirror is new
result: the base tree satisfies this probe
exit=0

########## prechange probe: reachable_equals_straight
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py reachable_equals_straight   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: reachable_equals_straight
I: 17 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
J: 34 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
L: 34 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
O: 9 straight-drop placements, columns [1, 2, 3, 4, 5, 6, 7, 8, 9]
S: 17 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8]
T: 34 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
Z: 17 straight-drop placements, columns [0, 1, 2, 3, 4, 5, 6, 7, 8]
frozen enumerate_placements total on the empty board: 162
only the frozen side of the equivalence exists at the base
result: the base tree satisfies this probe
exit=0

########## prechange probe: extra_columns
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py extra_columns   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: extra_columns
# base candidate set for O (the only candidate set the base can build):
straight set = [(0, 1, 18), (0, 2, 18), (0, 3, 18), (0, 4, 18), (0, 5, 18), (0, 6, 18)]
placements the regression requires and the base set lacks: [(0, 7, 18), (0, 8, 18), (0, 9, 18)]
AssertionError: pre-change candidate set has no (0,7)/(0,8)/(0,9): the regression's 'reachable - straight == [(0, 7, 18), (0, 8, 18), (0, 9, 18)]' cannot hold
exit=1

########## prechange probe: drop_unexecutable_model
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py drop_unexecutable_model   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: drop_unexecutable_model
# base straight set for I on the fence board: [(0, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1), (0, 6, 19), (0, 7, 19), (0, 8, 19), (1, 0, 18), (1, 1, 18), (1, 2, 18), (1, 3, 0), (1, 4, 18), (1, 5, 18), (1, 6, 18), (1, 7, 18), (1, 8, 18), (1, 9, 18)]
AssertionError: pre-change straight-drop model still offers the plan (1,3,0), which the controller executes by locking in column 4 instead: the regression's '(1, 3) not in reachable' cannot hold
exit=1

########## prechange probe: plan_mask
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py plan_mask   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: plan_mask
base controller (PlacementAgent.act) states driven: 24960
states that set a release frame: 8556
base emits a mask and a release flag for every one of them
result: the base tree satisfies this probe
exit=0

########## prechange probe: base_choice
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py base_choice   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: base_choice
# frozen enumeration of J on the dense board: 7 placements
# base GreedyPolicy.choose, five calls: [(1, 2), (1, 2), (1, 2), (1, 2), (1, 2)]
the frozen choice rule is already a pure function of its inputs
result: the base tree satisfies this probe
exit=0

########## prechange probe: base_value_rule
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py base_value_rule   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: base_value_rule
# frozen straight-drop candidates for J on the dense board: [(0, 5, 0), (1, 2, 0), (1, 6, 0), (2, 5, 0), (3, 2, 0), (3, 5, 0), (3, 6, 0)]
# base rule for J(0, 5) at origin row 0: cleared 1, its own board scores -154.00
# base rule for J(3, 5) at origin row 0: cleared 1, its own board scores -154.50
# base rule for J(3, 6) at origin row 0: cleared 1, its own board scores -153.50
# the frozen rule's own choice on this board: J(1, 2) at origin row 0, score -151.50
the base rule has no next-piece term: it scores neither (0, 5) nor (3, 5)
worse for stranding the preview piece, so the regression's -inf has no
pre-change counterpart
result: the base tree satisfies this probe
exit=0

########## prechange probe: engine_level
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py engine_level   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: engine_level
# engine, start level 0: (lines, level) samples = [(2, 0), (4, 0), (6, 0), (8, 0), (10, 1), (12, 1)]
# engine: level 0 through 9 lines, level 1 first reported at 10 lines (the pinned threshold)
the engine itself raises the level at exactly the pinned threshold; the mirror function that copies it has no pre-change counterpart
result: the base tree satisfies this probe
exit=0

########## prechange probe: fallback
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py fallback   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: fallback
greedy policy on an empty candidate tuple: None
base PlacementAgent masks where no placement fits: [4, 4, 4]
the Down fallback is pre-existing base behaviour; the reachable set is new
result: the base tree satisfies this probe
exit=0

########## prechange probe: preview_choice
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py preview_choice   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: preview_choice
# base greedy choice on the empty board with an O: (0, 1)
the base reads no preview field at all: its observation has none
AssertionError: base greedy choice (0, 1) != (0, 9), the placement the regression requires for the S preview: the choice cannot depend on the preview
exit=1

########## prechange probe: agent_name
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py agent_name   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: agent_name
AGENT_NAMES = ('random', 'greedy')
create_agent('lookahead', 2) -> ValueError: unknown agent: 'lookahead'
AssertionError: the base has no lookahead agent, so the suite-record regression cannot hold
exit=1

########## prechange probe: native_ceiling
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py native_ceiling   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: native_ceiling
# base straight model's candidate set: [(0, 1, 18), (0, 2, 18), (0, 3, 18), (0, 4, 18), (0, 5, 18), (0, 6, 18)]
# base controller aiming at (0, 7) locks the engine at: (0, 7, 18, False)
AssertionError: the engine locked the aimed (0, 7) at (0, 7, 18, False) but the pre-change straight model's candidate set excludes it: the whole-set gate has no pre-change analogue
exit=1

########## prechange probe: native_fence
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py native_fence   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: native_fence
# base straight model offers (1, 3) at row 0: True
# base controller aiming at (1, 3) locks the engine at: (1, 4, 18, False)
AssertionError: the engine locked (1, 4, 18, False) instead of the aimed (1, 3): the pre-change model offers a placement the controller cannot execute
exit=1

########## prechange probe: native_overhang
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/probes/prechange_probe.py native_overhang   [{'PYTHONPATH': '/tmp/exp002-prechange/src'}]
# base module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# probe: native_overhang
# the frozen straight-drop set omits the plan (0, 5) for every piece: True ({'I': True, 'J': True, 'L': True, 'O': True, 'S': True, 'T': True, 'Z': True})
# base controller aiming at (0, 5) on the overlapped spawn locks the engine at: (0, 5, 18, False)
AssertionError: the engine locked (0, 5, 18, False) but the pre-change candidate set is [(0, 1, 18), (0, 7, 18), (0, 8, 18), (0, 9, 18)]: it omits a placement the controller executes by descending out of the overlap
exit=1
```

**2. Controller-rule identity.** `evidence.py mask-identity` runs the base
tree's `PlacementAgent.act` in a subprocess against the pre-change `src` and the
shared `plan_mask` here, for every piece, orientation, observed column, aim and
release flag:

```text
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python -c '<the base controller enumeration beneath>'
# base controller module: /tmp/exp002-prechange/src/block_stack_ai/__init__.py
# shared rule module: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/src/block_stack_ai/pathaware.py
plan states compared: 24960
mask/release mismatches: 0
```

**3. Native whole-set gate and mutation sensitivity.** The gate
`test_reachable_placements_match_engine_locks_from_the_spawn_state` drives the
engine from the spawn state with exactly the masks `plan_mask` emits and requires
the engine's locked `(orientation, x, y)` to equal the model's `PlanOutcome`; it
asserts `compared == 162 aims * 7 boards == 1134`. The aim count is
independently reproduced by `evidence.py engine-contract`
(`aims over every piece/orientation/legal column: 162`; the same 162 is the
straight-drop placement count on an empty board, from the `reachable_equals_straight`
transcript). Each load-bearing rule the new regressions pin was also run against
a copy of the finished module with exactly that rule broken (`evidence.py
mutants`; the trees are left in `/tmp/exp002-mutants`):

| Mutation | Target | Observed failure | Exit |
| --- | --- | --- | --- |
| gravity removed from the plan (only Down descends) | `test_reachable_placements_add_columns_the_straight_drop_rejects` | `AssertionError: plan simulation did not reach a lock` | 1 |
| wrong gravity rate (`return 1`) | native whole-set gate | `('ceiling', False, 'J', (3, 6), PlanOutcome(orientation=3, x=6, y=18, …), (3, 6, 0))` — model `y=18`, engine locks at `y=0` | 1 |
| lookahead value replaced by the current placement's own score | `test_lookahead_choice_depends_on_the_preview_piece` | `assert (0, 1) == (0, 9)` | 1 |
| tie-break keeps the last maximum | `test_lookahead_choice_depends_on_the_preview_piece` | `assert (0, 9) == (0, 1)` | 1 |
| off-by-one column height (`HEIGHT - top + 1`) | `test_column_masks_match_the_grid_settle_and_features` | `bumpiness: 21 != 20`, `max_height: 21 != 20` | 1 |
| stranded preview piece scored by the rejected Down fallback | `test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece` | `assert -155.5 == -inf` | 1 |
| hidden buffer dropped from the compaction (`low_mask = (1 << row) - 1`, no `_HIDDEN_MASK` carry) | `test_settle_columns_keeps_the_hidden_buffer_across_a_clear` | `assert (12, 12, 0, 0, 0, 0, …) == (10, 10, 0, 0, 0, 0, …)` | 1 |
| level threshold made inclusive (`lines <= threshold`) | `test_level_for_lines_mirrors_the_engine_transitions` | `assert 18 == 19` where `18 = level_for_lines(130, 18)` | 1 |
| overlapped spawn declared a top-out instead of descending out of it | `test_reachable_placements_rescue_an_overlapped_spawn` | `AssertionError: ('I', PlanOutcome(orientation=0, x=5, y=0, reached=True, top_out=True))` | 1 |

The same eight targets pass on the unmutated tree (`8 passed`, exit 0),
and `evidence.py determinism` reports:

```text
# module: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/src/block_stack_ai/pathaware.py
lookahead_choice on the ceiling board (T with an I preview), five calls: [(0, 8, 18), (0, 8, 18), (0, 8, 18), (0, 8, 18), (0, 8, 18)]
all five identical: True
pathaware imports no RNG: True
```

**4. Record replay, fidelity and determinism.** `evidence.py replay` replays
each saved episode from its `(agent, seed)`, requires the replayed inputs to
equal the recorded inputs, re-derives every landing, clear and level number from
the engine's own reported state, and re-checks the summary — an independent
reproduction of the record's `model_fidelity` block and of the level audit in
the limitations:

```text
########## replay runs/20260927T052746268934Z-dbeb0c30/run.json
# configuration: {"agents": ["greedy", "lookahead"], "frame_limit": 200000, "game": {"height": 0, "mode": "endless", "ruleset": "classic_ntsc_extended", "start_level": 18}, "seeds": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]}
greedy: locks 3357, landed exactly 3328, divergences 29 (column 29, orientation 9, row 27), fallback locks 0, predicted clears 1208, engine clears 1189, game overs 10, level mismatches 0
lookahead: locks 23153, landed exactly 23144, divergences 0 (column 0, orientation 0, row 0), fallback locks 9, predicted clears 9128, engine clears 9128, game overs 9, level mismatches 0
frames compared for the level mirror: 1078262
level mismatches: 0
replayed summary equals the recorded summary: True
replayed inputs equal the recorded inputs for all 20 episodes

########## replay runs/20260927T053031752624Z-708c8c0b/run.json
# configuration: {"agents": ["greedy", "lookahead"], "frame_limit": 200000, "game": {"height": 0, "mode": "endless", "ruleset": "classic_ntsc_extended", "start_level": 18}, "seeds": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]}
greedy: locks 3357, landed exactly 3328, divergences 29 (column 29, orientation 9, row 27), fallback locks 0, predicted clears 1208, engine clears 1189, game overs 10, level mismatches 0
lookahead: locks 23153, landed exactly 23144, divergences 0 (column 0, orientation 0, row 0), fallback locks 9, predicted clears 9128, engine clears 9128, game overs 9, level mismatches 0
frames compared for the level mirror: 1078262
level mismatches: 0
replayed summary equals the recorded summary: True
replayed inputs equal the recorded inputs for all 20 episodes


real	2m51.638s
user	2m52.600s
sys	0m0.135s
exit=0
```

`evidence.py compare` on the first and the repeat run:

```text
# first : runs/20260927T052746268934Z-dbeb0c30/run.json
# repeat: runs/20260927T053031752624Z-708c8c0b/run.json
configuration identical: True
episodes identical: True
summary identical: True
episode count equal: True
```

**5. `verify` on the saved records.** The first record is the one
[result.json](result.json) was written from; the repeat is the second full run of
the same configuration. Both replay every episode and exit 0, the only warning
being the recorded working-tree engine:

```text
$ export PYTHONPATH=/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/src
$ V=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/block-stack-ai
$ time $V verify runs/20260927T052746268934Z-dbeb0c30/run.json    # the record result.json was written from
Verified: runs/20260927T052746268934Z-dbeb0c30/run.json
Warning: The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.

real	1m25.943s
user	1m28.126s
sys	0m0.308s
exit=0
$ time $V verify runs/20260927T053031752624Z-708c8c0b/run.json    # the repeat run
Verified: runs/20260927T053031752624Z-708c8c0b/run.json
Warning: The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.

real	1m25.010s
user	1m25.489s
sys	0m0.085s
exit=0
```

**6. Suites, repeat run and wall clock.** The CLI doctor passes on the
registered environment (engine checkout `8ca41587`, working tree, dirty), and
the registered suites were run in exactly the registered form
(110 unit tests, 21 native integration tests, all passing; the new unit tests
use constructed boards, the pure Python model and one 400-frame lookahead
episode, and the native work is the 1134-plan whole-set gate above):

```text
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python -m block_stack_ai.cli doctor
Engine checkout: /home/harmon-chew/projects/code/block-stack
Engine Git: 8ca4158711c2d6339cab1ee8d78aa65bd624c89d (working-tree, dirty=True)
Python binding: /home/harmon-chew/projects/code/block-stack/python/block_stack/__init__.py (package 0.1.0)
Native library: /home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so
Smoke check: OK (frame 0 -> 1, hash 27cc82cf15f77a97)

real	0m0.068s
user	0m0.042s
sys	0m0.027s
exit=0
```

The recorded base tree collects 97 unit and 19 native integration tests; this
tree collects 110 and 21 — exactly the 13 new unit tests in
`tests/test_pathaware.py` and the 2 new integration tests (the whole-set gate and
the suite-record replay), with nothing removed, skipped or newly deselected:

```text
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python -m pytest -q -p no:cacheprovider -m 'not integration'
........................................................................ [ 65%]
......................................                                   [100%]
110 passed, 21 deselected in 0.48s

real	0m0.573s
user	0m0.539s
sys	0m0.036s
exit=0
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python -m pytest -q -p no:cacheprovider -m integration
.....................                                                    [100%]
21 passed, 110 deselected in 1.46s

real	0m1.557s
user	0m1.000s
sys	0m0.131s
exit=0
```

The 10-seed suite was re-run for the determinism comparison (85.5 s wall
clock; the record it is compared with took 86.0 s, and the two `verify`
replays below):

```text
Experiment: 002-path-aware-lookahead
Config: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/002-path-aware-lookahead/config.json
greedy: 10 games, score mean 106621.9, lines mean 118.9, frames mean 15801.3, (game_over 10)
lookahead: 10 games, score mean 2822959.9, lines mean 912.8, frames mean 92024.9, (frame_limit 1, game_over 9)
Record: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/runs/20260927T053031752624Z-708c8c0b/run.json

real	1m25.467s
user	1m25.997s
sys	0m0.127s
exit=0
```

The cost is the lookahead; `evidence.py timing` on a real mid-game board (120
greedy pieces, 56 filled cells, level 18) measures (best of five repetitions;
wall-clock figures vary a little between runs):

```text
mid-game board from the frozen greedy agent: 56 filled cells, level 18, 120 pieces played
  reachable_placements(I): best 0.10 ms, worst 0.12 ms
  reachable_placements(J): best 0.19 ms, worst 0.20 ms
  reachable_placements(L): best 0.19 ms, worst 0.19 ms
  reachable_placements(O): best 0.05 ms, worst 0.05 ms
  reachable_placements(S): best 0.09 ms, worst 0.10 ms
  reachable_placements(T): best 0.19 ms, worst 0.19 ms
  reachable_placements(Z): best 0.09 ms, worst 0.09 ms
  lookahead_choice(I, preview T): best 3.32 ms, worst 3.35 ms
  lookahead_choice(J, preview T): best 6.58 ms, worst 7.24 ms
  lookahead_choice(L, preview T): best 6.54 ms, worst 6.67 ms
  lookahead_choice(O, preview T): best 1.73 ms, worst 2.20 ms
  lookahead_choice(S, preview T): best 3.29 ms, worst 3.32 ms
  lookahead_choice(T, preview T): best 6.55 ms, worst 6.76 ms
  lookahead_choice(Z, preview T): best 3.27 ms, worst 3.28 ms
cheapest piece: O 0.05 ms; dearest piece: T 0.19 ms
```

**7. The frozen Experiment 001 baseline.** Experiment 001's own `config.json`
still parses and runs against this tree's `src` and reproduces the published 001
record: the re-run's configuration, weights record and per-agent summary equal
`experiments/001-greedy-heuristic/result.json`. Nothing in Experiment 001 is
touched — `git diff --quiet HEAD -- experiments/001-greedy-heuristic` and
`git diff --quiet HEAD -- src/block_stack_ai/heuristic.py` both exit 0, so its
record bytes and the straight-drop contract are the committed ones:

```text
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python experiments/002-path-aware-lookahead/probes/evidence.py baseline
$ PYTHONPATH=/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/src python -m block_stack_ai.cli run --config /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-002-path-aware-lookahead/experiments/001-greedy-heuristic/config.json
# 001 configuration identical: True
# 001 weights identical: True
# 001 summary for greedy identical to the published record: True
# 001 summary for random identical to the published record: True

real	0m2.255s
user	0m2.247s
sys	0m0.030s
exit=0
```

`baseline` runs 001's config in a temporary directory, so it writes no record
under `runs/`. The `greedy` half of that run is the same agent this experiment
ran: this experiment's recorded `greedy` summary and replayed fidelity
(3328/3357 locks landed, 29 divergences, 1208 predicted against 1189 engine
clears) are 001's published greedy figures, and the fresh 001 run's greedy
summary is identical because `greedy` is deterministic and 001's 60000-frame
limit binds none of its games (its longest is 38158 frames).

**8. The player-visible preview (acceptance criterion 3).** The one-piece
lookahead reads exactly one next-piece field, `State.next_piece`, from the
observation the runner passes to `act(state)`. Driven on the registered binding,
that field is the preview the engine promotes into play — never hidden RNG state:

```text
$ /home/harmon-chew/projects/code/fallgorithm/.venv/bin/python experiments/002-path-aware-lookahead/probes/evidence.py engine-preview
$ python -c '<drive the registered binding from a fresh game>'
# binding: /home/harmon-chew/projects/code/block-stack/python/block_stack/__init__.py
# native library: /home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so
# fresh game: current J, next Z, phase active, frame 0
# observation fields: next_piece 'Z' (id 6), rng_state 16384, piece_count 2
# spawn: the preview promised Z, the engine spawned Z, agreement True, next now T
# spawn: the preview promised T, the engine spawned T, agreement True, next now T
# spawn: the preview promised T, the engine spawned T, agreement True, next now T
# spawn tick: x 5, y 0, orientation 0, first_delay 0, gravity 0, soft 0, previous_input 0
# the agent reads only observation fields; the model never reads rng_state: True
# preview/spawn mismatches over three spawns: 0
exit=0
```

**Limitations and useful failures:**

- A lock that the engine rejects (top-out) is not a placement, so the agent has
  no admissible placement at that point and falls back to holding Down; the
  engine then locks there and ends the game. Nine of the ten lookahead episodes
  end this way. The fallback is greedy's, kept deliberately, and it is the only
  remaining model-versus-engine divergence.
- The plan is executed by a controller that never replans: if the aimed
  placement stops being reachable mid-piece, the piece locks wherever it got to.
  The reachable set removes the candidates where that would happen — including a
  blocked rotation, since the whole plan (rotation presses, shifts, descent) is
  simulated and a plan that cannot reach its aim is simply not admissible — so
  the chosen placement never diverges. The controller itself is unchanged.
- The simulation mirrors the engine's active-phase step function, not the whole
  game: entry delay, line-clear timing and RNG are out of scope because a plan
  ends at the lock, and the next piece is simulated from a fresh spawn with the
  preview the binding reports. The level the next piece's gravity uses is
  computed from the clear (`level_for_lines`) rather than read from the engine;
  it is exact for the two rulesets and both modes as long as the recorded level
  matches the cleared lines, which was checked rather than assumed: replaying the
  recorded inputs of all 20 episodes and comparing the engine's reported level
  with the mirrored function at every frame gave **1078262 frames, 0
  mismatches** (`probes/evidence.py replay` reproduces that count and every
  landing, clear and summary number in this note).
- The reachable set is derived for the *controller's* input sequence. A
  different controller (or hold, or a different press cadence) would need its own
  model; the straight-drop contract is preserved unchanged for `greedy` and
  `random`.
- No weight tuning, no learning, no hold, no deeper lookahead: the value uses the
  existing fixed weights, and the lookahead is exactly one piece (the preview).
  The agent reads only the observation the runner passes it.
- The frame limit is a configured safety bound: the one episode that reached it
  is reported as a safety stop and never as a game over, and no figure in the
  table hides it.
- **A plan-model defect found in review and fixed.** The first version declared
  an overlapped spawn a top-out at once. The engine has no collision test at
  spawn, so a piece whose origin is occupied can descend out of the overlap and
  lock normally; the model now follows the engine's first downward attempt (and
  uses the closed-form descent only when that attempt succeeds). It is pinned by
  `test_reachable_placements_rescue_an_overlapped_spawn`, the `overhang-spawn`
  board in the native whole-set gate, and the `overlap_topout` mutant. The fix
  changes no recorded episode — the pre-fix and post-fix records are
  episode-identical — so every figure here stands; the defect only ever *removed*
  admissible candidates, which is why it left the fidelity count untouched.
- Adjacent seeds are not independent (an engine property 001 documented: the LFSR
  drops bit 0 on its first advance and piece selection reads the high byte), so
  the recorded seeds are the even values `2..20`, which give ten distinct
  trajectories.
- The dependency is a working-tree run: the registered engine checkout is
  recorded dirty at `8ca41587` (001 measured on `0e56c3b`; item 7 re-runs 001's
  config on the current checkout and reproduces its published summary exactly, so
  the gameplay is the same) and the registered library is a build of that working
  tree, so the figures are reproducible by restoring the recorded code versions
  and rerunning `config.json`, not by verifying a checked-in artifact. Clean
  reproducible dependency CI is not claimed.

**Reproduce:** From the project root, after the setup in the
[project README](../../README.md):

```sh
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python   # or .venv/bin/... in a project checkout
export PYTHONPATH=$PWD/src
$PY -m block_stack_ai.cli doctor
$PY -m block_stack_ai.cli run --experiment 002
$PY -m block_stack_ai.cli verify runs/<new-run-id>/run.json
# the validation evidence: baseline probes, controller identity, engine tables,
# mutants, determinism, timings, the frozen 001 baseline, the repeat comparison
# and the record replay
$PY experiments/002-path-aware-lookahead/probes/evidence.py all
$PY experiments/002-path-aware-lookahead/probes/evidence.py prechange --rev <recorded base commit>
```

`run` writes its record under the ignored project-root `runs/` directory (11.9 MB
for this suite, every frame mask stored), and `verify` replays that path
directly. The record is temporary and disposable: `runs/` is ignored at any
depth, so a clean checkout holds only `config.json`, this note, the retained
[`probes/`](probes/) evidence scripts and the compact
[result.json](result.json) summary. Rerunning the configuration after restoring
the recorded code versions and any uncommitted edits recreates the record; every
measurement in this note was taken from such a local record, and the fidelity
measurement is reproduced by rerunning the configuration and comparing each
episode's chosen placement with its locked origin as described above.
