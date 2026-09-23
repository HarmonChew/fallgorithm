# fallgorithm

Fallgorithm is a small workspace for incremental AI experiments with the
headless [Block Stack](../block-stack/README.md) game. Stage 0 is only a
connection test: send a fixed controller script to the native simulation, save
the outcome, and replay the executed inputs to check it. There is no playing
algorithm or machine learning yet.

## Setup

Place the game checkout beside this project as `../block-stack`, or set
`BLOCK_STACK_ROOT` to its checkout path. You need Python 3.10+, pip, CMake
3.20+, and a C++20 compiler. The following commands were run successfully on
this machine with Python 3.12:

```sh
python3.12 -m venv .venv
.venv/bin/python scripts/setup_engine.py
.venv/bin/python -m pip install -e . pytest
```

The setup script configures a Release headless build, builds `blocks_native`
and `block_stack_headless` into ignored `.build/engine/`, then installs the
game's Python package from its sibling checkout into the virtual environment.
Fallgorithm's own editable package provides the `block-stack-ai` command. The
native library is selected from that build directory on the local platform.
`BLOCKS_NATIVE_LIB` overrides the selected library if the engine already has
a suitable build elsewhere. No tracked file in the game checkout is changed.

## Run and verify

From the fallgorithm root:

```sh
.venv/bin/block-stack-ai doctor
.venv/bin/block-stack-ai run --config experiments/000-connection/config.json
.venv/bin/block-stack-ai verify runs/<run-id>/run.json
```

`doctor` prints the resolved checkout, Git version, binding and library paths,
and performs a create/read/step/close smoke check. `run` prints the stopping
reason, frames, score, lines, final native state hash, and the unique saved
record path. Use that path in `verify`. The record contains the resolved game
configuration and 16-bit seed, scripted masks and durations, actual executed
mask for each frame, event totals, outcome, initial/final native state hashes,
and Git commit/dirty status for both repositories. A dirty or no-commit run is
labeled a working-tree run; a matching hash verifies this replay, while the Git
commit alone cannot restore uncommitted edits.

Only gameplay masks 0–31 are used. A `0` frame releases held buttons. Rotation
fires on a new press edge, so the connection script inserts release frames
between rotations. The frame limit bounds every episode, and terminal game or
challenge states stop it immediately. The AI calls the headless engine directly
through its Python binding; it does not press physical keys or read screenshots.
The JSON run record is not the game's desktop replay format.

## Tests and experiment notes

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -m 'not integration'
.venv/bin/python -m pytest -q -p no:cacheprovider -m integration
```

The first command tests configuration, deterministic scripted inputs, release
frames, stop reasons, and missing-path diagnostics without the native engine.
The second requires the completed setup and tests native state reads, logical
frame counts, seeded hash determinism, and run-record verification. Integration
tests are never treated as passing when the native library is unavailable.
The measured Stage 0 result is in
[experiments/000-connection](experiments/000-connection/notes.md), and
[experiments/README.md](experiments/README.md) describes the small record
convention. `runs/`, `.build/`, `.venv/`, caches, and future large model files
are ignored. Temporary run output is disposable.

## Later stages

The runner can keep supplying observations and accepting one frame mask at a
time while later experiments replace the scripted agent with a hand-written
heuristic, search planner, learned evaluator, or learned frame controller.
Those approaches should reuse the same engine connection and run-recording
workflow. None is implemented in Stage 0.
