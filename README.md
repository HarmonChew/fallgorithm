# fallgorithm

Fallgorithm is a small workspace for incremental AI experiments with the
headless [Block Stack](../block-stack/README.md) game. Stage 0 is a connection
test: send a fixed controller script to the native simulation, save the outcome,
and replay the executed inputs to check it. Experiment 001 adds the first
playing algorithms on top of that path: a one-piece greedy placement heuristic
and a uniform random legal-placement baseline. There is no machine learning yet.
Development proceeds one measured experiment at a time, reusing this engine
connection and recording path.

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
and the headless/replay tools into ignored `.build/engine/`, then installs the
game's Python package from its sibling checkout into the virtual environment.
Fallgorithm's own editable package provides the `block-stack-ai` command. The
native library is selected from that build directory on the local platform.
`BLOCKS_NATIVE_LIB` overrides the selected library if the engine already has
a suitable build elsewhere. Setup does not change tracked files in the game
checkout.

## Run and verify

From the fallgorithm root:

```sh
.venv/bin/block-stack-ai doctor
.venv/bin/block-stack-ai experiments
.venv/bin/block-stack-ai run --experiment 000
.venv/bin/block-stack-ai run --experiment 001
.venv/bin/block-stack-ai verify runs/<run-id>/run.json
```

`experiments` lists the numbered directories and which agents support live play.
Both `run` and `play` require an explicit `--experiment` number or full directory
name (for example, `001` or `001-greedy-heuristic`). The selected name and resolved
config path are printed before starting. `--config path/to/config.json` remains
available for a custom configuration; it cannot be combined with `--experiment`.

`doctor` prints the resolved checkout, Git version, binding and library paths,
and performs a create/read/step/close smoke check. `run` prints the stopping
reason, frames, score, lines, final native state hash, and the unique saved
record path. Use that path in `verify`. A configuration either holds a `script`
(one scripted episode) or `seeds` and `agents` (one episode per agent and seed,
reported as a per-agent summary). The record contains the resolved game
configuration and 16-bit seed, the executed mask for each frame, event totals,
outcome, initial/final native state hashes, and Git commit/dirty status for both
repositories. A dirty or no-commit run is labeled a working-tree run; a matching
hash verifies this replay, while the Git commit alone cannot restore uncommitted
edits. A suite record also states the fixed heuristic weights it used, and
`verify` re-derives every episode from the recorded agent name and seed, which
must appear in the configured order: agent order, then seed order. Each episode
and summary reports `pieces_placed`, the number of pieces the engine wrote to
the board (its `locked` events minus the failed top-out lock; a piece still in
play at a frame-limit stop and the topping-out lock that places nothing are not
counted); records written before that field carry the legacy `pieces` key
holding the preview counter and still verify under that meaning.

Only gameplay masks 0–31 are used. A `0` frame releases held buttons. Rotation
fires on a new press edge, so the connection script and the placement agents
insert release frames between presses. The frame limit bounds every episode, and
terminal game or challenge states stop it immediately. The AI calls the headless
engine directly through its Python binding; it does not press physical keys or
read screenshots. The JSON run record is not the game's desktop replay format.

## Let the algorithm play a fresh game

Build the desktop once with SDL3 development files available (`libsdl3-dev` on
Ubuntu), then launch experiment 001's greedy agent:

```sh
.venv/bin/python scripts/setup_engine.py --desktop
.venv/bin/block-stack-ai play --experiment 001
```

The window starts a new game immediately, with a freshly selected seed printed
in the terminal and shown in the game. The existing Python agent chooses the
next input from the desktop's current state on every logical frame. The desktop
owns the game clock and renders that game as it runs. No recorded game is loaded.
The selected experiment supplies its game settings and frame limit; experiment
001 uses a 60,000-frame limit. `--agent` chooses an algorithm within that
experiment (default: `greedy`). Experiment 000 is a fixed controller script and
supports `run` and replay rather than live placement play.

**P** pauses, **.** advances one frame while paused, **R** restarts the same seed,
**[ / ]** changes speed, and **Esc** quits. A new invocation chooses a fresh seed.
To choose the seed, watch faster, or compare the random baseline:

```sh
.venv/bin/block-stack-ai play --experiment 001 --seed 2 --speed 4
.venv/bin/block-stack-ai play --experiment 001 --agent random
.venv/bin/block-stack-ai play --experiment 001 --seed 2 --paused
```

Each completed game or frame-limit stop saves a normal one-episode suite record
under `runs/`; use the printed path with `block-stack-ai verify`. The controller
checks every desktop state against the native library's predicted next state
before choosing another input. Closing or restarting an incomplete game excludes
it from experiment results; the desktop can still save its inputs with F5.

Live play requires the sibling game's `--controller-stdio` support. Rebuild
the desktop after updating that checkout. If SDL3 headers are unpacked locally,
add `--sdl3-include-dir /path/to/include` to the setup command as described below.

## Watch recorded inputs

The desktop client uses the same native simulation and can play the exact
recorded inputs. Build it once with SDL3 development files available
(`libsdl3-dev` on Ubuntu):

```sh
.venv/bin/python scripts/setup_engine.py --desktop
.venv/bin/block-stack-ai run --config experiments/000-connection/config.json --watch
```

`--watch` saves the run, verifies it, exports `run.rep` beside `run.json` using
the engine's own replay writer, checks that the exporter reaches the recorded
state hash and frame count, then opens Block Stack paused at frame 0. Press
**.** to advance one frame, **P** to play/pause, **[ / ]** to change speed, and
**F1** for debug counters and the state hash. Playback pauses at the end. Close
the window to return to the command line; rerun `watch` to watch it again.

For an existing run, or to export without opening a window:

```sh
.venv/bin/block-stack-ai watch runs/<run-id>/run.json
.venv/bin/block-stack-ai export-replay runs/<run-id>/run.json
```

Experiment 000 lasts only 31 frames (about half a second at normal speed).
You will see its fixed left/rotate/right/drop script, not a full-game AI player.
This is visual playback of a completed run; the current controller does not
make decisions live in the window. The commands in this section currently
handle the single-episode format used by experiment 000; experiment 001 stores
a suite of episodes.

If SDL3's runtime is installed but its headers are in a local directory, use
the following command with the directory containing `SDL3/`:

```sh
.venv/bin/python scripts/setup_engine.py --desktop --sdl3-include-dir /path/to/include
```

If the desktop reports an unknown `--paused` option, update the sibling game
checkout and rebuild with `--desktop`.

## Tests and experiment notes

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -m 'not integration'
.venv/bin/python -m pytest -q -p no:cacheprovider -m 'integration and not desktop'
.venv/bin/python -m pytest -q -p no:cacheprovider -m desktop
```

The first command tests configuration, deterministic scripted inputs, release
frames, stop reasons, missing-path diagnostics, the lock and line-clear grid
rule, placement enumeration including the spawn-origin entry and the
downward-only descent rule, board scoring, deterministic tie-breaking, the
placement controller, the placed-piece metric (the engine's board placements,
above which sit its lock and preview counters) in both record formats and the
suite record's episode identity check, without the native engine. The second
requires the completed setup and tests native state reads, logical frame counts,
seeded hash determinism, the placement model against native locks including a
lock that straddles the ceiling and hidden minos surviving a later clear, the
whole enumerated placement set against engine-reachable straight drops from the
spawn origin, the recorded piece count against the native engine's own counters,
run-record verification for both record formats, and desktop replay exports
through the native writer and verifier. The desktop checks additionally require
the SDL3 target; they exercise live input, pause/step/restart, record verification,
invalid masks and pipe closure using dummy video/audio. None needs a display.
Integration tests are never treated as passing when the native library is
unavailable. The measured results are in
[experiments/000-connection](experiments/000-connection/notes.md) and
[experiments/001-greedy-heuristic](experiments/001-greedy-heuristic/notes.md),
and [experiments/README.md](experiments/README.md) describes the small record
convention. `runs/`, `.build/`, `.venv/`, caches, and future large model files
are ignored. Temporary run output is disposable.

## Later stages

The runner can keep supplying observations and accepting one frame mask at a
time. Experiment 001 adds the hand-written greedy placement heuristic and its
random baseline; later experiments can add lookahead, a search planner, a
learned evaluator, or a learned frame controller on the same engine connection
and run-recording workflow. None of those is implemented yet.
