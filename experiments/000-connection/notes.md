# 000: Connection and replay

**Question:** Can fallgorithm load the sibling Block Stack engine, control it
through frame inputs, and reproduce a recorded run?

**What was tested:** A Release build of `blocks_native` and
`block_stack_headless` in this project's ignored `.build/engine/` directory;
the installed local Python binding; the CLI doctor check; 16 unit tests; three
native integration tests; and the 31-frame script in [config.json](config.json).
The script taps left, releases, rotates clockwise twice with a release between
presses, taps right, holds Down, then releases. Every mask goes through
`Game.step()` on the actual native engine.

**Observed result:** Setup and doctor succeeded. All 16 unit and three native
integration tests passed. The run ended by completing the script after 31
frames, at score 0 and lines 0. The native engine reported two moves, two
rotations, nine soft-drop events, and one gravity drop. Initial state hash:
`04cccfd1b5b72607`; final state hash: `41dfca77676d6d79`. The `verify`
command replayed the recorded inputs in a fresh game and matched the final
hash and outcome fields. The full temporary record is
`runs/20260923T082257031259Z-76932b9a/run.json`; the compact retained summary
is [result.json](result.json).

**Reproduce:** From the project root, create the virtual environment and run
the setup commands in the [project README](../../README.md), then:

```sh
.venv/bin/block-stack-ai doctor
.venv/bin/block-stack-ai run --config experiments/000-connection/config.json
.venv/bin/block-stack-ai verify runs/<new-run-id>/run.json
```

The script configuration and seed should produce the stated outcome with the
same engine code. The run record captures the Git commit and dirty status of
both repositories. The engine was dirty at commit
`0e56c3beb7e4165e793ff326e3600d973e236cb8`; fallgorithm was a new local
repository with no commit. This is a **working-tree run**, so the Git metadata
cannot reconstruct the uncommitted source. Preserve those source edits if an
exact future rebuild is needed. The ignored `runs/` directory is disposable;
retain important artifacts deliberately elsewhere. This JSON record is a
fallgorithm format, not the game's desktop replay format.

**Lesson:** The native frame API and state hash are enough for a small,
repeatable input experiment. Later agents can use the same connection and
recording path while changing only how masks are chosen.

## Review and local playback, 2026-09-27

No blocking defect was found within this connection test's scope. A fresh run
with the unchanged configuration reproduced both hashes, all event totals,
31 frames, score 0, and lines 0. This demonstrates input delivery and replay
determinism. It does not evaluate decision quality, piece placement, line
clearing, or full-game survival: the script locks no pieces and ignores the
observation. The working-tree provenance limitation above still applies.

The local environment was rebuilt, both editable packages were installed, and
`doctor` passed. All **22 tests passed**: 16 unit tests and six native integration
cases. The added cases export the original experiment, a Strict Challenge
configuration, and a frame-limited run through the engine's replay writer,
then validate each `.rep` with `block_stack_replay`. They also check that a
record with a wrong final hash cannot replace an existing valid replay.

Visual playback is now available through `run --watch` and `watch <record>`.
The desktop was built against the installed SDL3 runtime; matching headers
were unpacked into ignored `.build/deps/sdl3/`. To rebuild this machine's setup:

```sh
.venv/bin/python scripts/setup_engine.py --desktop --sdl3-include-dir .build/deps/sdl3/usr/include
.venv/bin/block-stack-ai run --config experiments/000-connection/config.json --watch
```

The desktop starts at frame 0, paused, with an unobstructed board. Use `.` to
step, P to play/pause, and brackets to change speed. This displays the completed
run's recorded inputs in the actual game; it is not a live decision-making
agent. The SDL dummy video/audio drivers were used for rendering checks:
initial and frame-31 screenshots were inspected, paused playback stayed at
frame 0 for 60 render frames, and the existing keyboard smoke check passed.
The complete `run --watch` command launched successfully and was deliberately
stopped after two seconds by `timeout` (expected status 124).

The fresh temporary record and exported replay are
`runs/20260926T160259860824Z-57c9c899/run.json` and its neighboring `run.rep`.
The replay writer reached `41dfca77676d6d79` after 31 frames, matching the run.
Both repositories were dirty: engine commit
`0e56c3beb7e4165e793ff326e3600d973e236cb8`, fallgorithm commit
`5494363120bdd182e9dab51a8ea5b20c918f71d3`. The desktop startup flag and pause
indicator changes are in the sibling engine working tree.
