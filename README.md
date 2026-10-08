# fallgorithm

Fallgorithm is a small workspace for incremental AI experiments with the
headless [Block Stack](../block-stack/README.md) game. Stage 0 is a connection
test: send a fixed controller script to the native simulation, save the outcome,
and replay the executed inputs to check it. Experiment 001 adds the first
playing algorithms on top of that path: a one-piece greedy placement heuristic
and a uniform random legal-placement baseline. Experiment 002 adds a path-aware
agent: it only aims at placements its own frame controller can really execute
under the engine's gravity, and it uses the player-visible next piece for one
piece of lookahead. Experiment 003 records the per-step clear-size breakdown
(singles, doubles, triples and Tetrises) the line total alone discards, and adds
a Tetris-oriented agent on 002's reachable set. Experiment 004 adds a bounded
well plan: a designated well column, an explicit stack-height budget and a
spend-or-abandon rule at a self-tracked I-drought bound, on the same reachable
set, with the declared objective of whichever agent a suite selects recorded and
replayed. There is no machine learning yet.
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

## Interactive launcher

Launch without arguments to choose options in a terminal:

```sh
.venv/bin/block-stack-ai
```

`block-stack-ai menu` opens the same launcher. Type a menu option's number and
press Enter to select an experiment, then choose live play or full evaluation.
Live play offers the experiment's agents, a fresh or fixed seed, speed, and
whether to start paused. Full evaluation uses all agents and fixed seeds from
the saved experiment configuration. Scripted experiments offer a run or a run
followed by replay playback.

The launcher shows your selections and the equivalent command before you choose
**Start**. Choose **Choose again** to change them, or enter **q** at any prompt
to quit. The experiment and action always require an explicit selection; Enter
accepts the displayed defaults for the remaining options. The command exits
when the selected run or game window finishes. The menu requires an interactive
terminal; use the commands below in scripts.

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
edits. A suite record also states the fixed heuristic weights it used, and, when
it configures an agent that declares an objective of its own — `tetris` or
`tetris_plan` today, whichever one the configuration selects — that agent's
declared objective — the module that
declares it, the weights it publishes and the source identity of every module
its decisions run through, the agent wrapper that hands it the state included and
the module that decides which implementation is built — which `verify` compares
as it compares
the heuristic mapping, so a record cannot verify under a different objective
merely because the change preserved its replayed choices. That identity is the
source the run loaded: the package's own loader reads each module's source once,
digests it, and executes the code compiled from those same bytes — so neither a
later read of `module.__file__` nor a valid-but-stale `__pycache__` entry beside
an edited file can make a record name code that did not run. An edit that lands
after a module is imported is therefore reported by `verify` rather than
certified, because the file its identity names no longer holds the bytes that
were loaded. A record's
`format_version` says which sections its writer always recorded and which walk
produced that identity: versions 1 and 2
are the older formats, whose sections may be absent; version 3 is the current
scripted format, version 4 is the prior suite format, whose writer recorded the
declared objective without the source identity its successor adds, version 5 is
the suite format whose identity stopped at the modules the objective's own code
reaches and therefore missed the wrapper that drives it, version 6 records that
identity with the wrapper but names the shared factory as the builder of an agent
the factory defines, version 7 is the headless suite format, whose identity is
seeded from the runner's dispatch that builds every agent, so a Tetris record
covers the code that selects its implementation too, and version 8 is the live
suite format, whose writer is the interactive live session. A live record's
placements are chosen through `LiveSession.receive`, which reads each desktop
observation, hands it to the agent and executes the mask it returns; the root
objective-and-dispatch walk cannot reach that module, because it imports the
runner rather than the other way round, so the version-8 objective identity seeds
it beside the dispatch. Every version-8 record also carries a `controller`
section, the walk from `block_stack_ai.live` with the declared objectives
excluded, because the live session drives `greedy`, `random` and `lookahead` as
well: those agents declare no objective, so without the section none of their
live records would carry a source map at all. The version is additive rather
than a widening of version 7
because every retained headless record is compared against the identity its own
writer emitted: the headless writer still emits version 7 and the byte-for-byte
walk it always emitted, while the live writer emits version 8, so a change to the
controller that keeps the replayed masks and results is reported instead of
certified. A session whose live module was reloaded after the instance was
built is refused rather than recorded, because the retained class keeps
executing the previous `receive` while its globals come from the reloaded
module; construct a new session. The controller identity's loaded view runs the
same inconsistent-closure refusal the objective's does, so reloading a
controller dependency such as `block_stack_ai.agents` without its importers is
refused instead of recorded, and a version-8 record must configure exactly one
agent and one seed, the single game `play_live` runs. A version 3, 4, 5, 6, 7 or 8
record must carry the placed-piece count, the clear-size histogram and — for a
suite that configures an agent with its own declared objective — that objective,
and a version-8 record must carry the controller section as well.
That is why the version is compared rather than the absence: a section deleted
from a current record would otherwise be indistinguishable from a record that
predates it. `verify` re-derives
every episode from the recorded agent name and seed, which
must appear in the configured order: agent order, then seed order. Each episode
and summary reports `pieces_placed`, the number of pieces the engine wrote to
the board (its `locked` events minus the failed top-out lock; a piece still in
play at a frame-limit stop and the topping-out lock that places nothing are not
counted); records written before that field carry the legacy `pieces` key
holding the preview counter and still verify under that meaning. Each episode
and summary also reports `clear_sizes`, how many locks cleared one, two, three
and four rows, tallied from the engine's own per-step clear result; in a current
record the histogram is present on every episode and every agent summary, and in
a legacy one it is present on every one of them or on none — the summary's totals
are derived from the episodes, so a legacy record's summary re-derives without a
section its episodes never recorded — so a record written
before that field existed is an older format and still verifies.

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
experiment (default: `greedy` when the experiment offers it, otherwise the
experiment's first agent). Experiment 000 is a fixed controller script and
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

The first command also checks menu selection, live defaults and custom options,
input validation, cancellation, and dispatch without a native engine. It tests
configuration, deterministic scripted inputs, release
frames, stop reasons, missing-path diagnostics, the lock and line-clear grid
rule, placement enumeration including the spawn-origin entry and the
downward-only descent rule, board scoring, deterministic tie-breaking, the
placement controller, the placed-piece metric (the engine's board placements,
above which sit its lock and preview counters) in both record formats and the
suite record's episode identity check, the clear-size metric (the engine's own
per-step clear result tallied per episode and per agent, with the optional-field
replay compatibility that keeps older records verifying and the suite-wide rule
that the histogram is present on every episode and every agent summary or on
none), the declared objective's
recorded section — which follows the agent the configuration selects, `tetris` or
`tetris_plan` — and its comparison on replay, the refusal of a configuration that
names two such agents, the registry that dispatches each agent to the module that
builds it (the shared factory's own source is left untouched, so the identity of a
record written before the new agent still matches), the identity of every module
that
produces its choices (the agent wrapper that hands it the state, beside the
objective and its helpers) and the loaded code that identity names (a record
written by a process that imported the objective's modules, had one of their
files edited and only then imported the writer still carries the loaded bytes,
and `verify` reports it once the file has moved on), the version-keyed live
identity (the version-8 walk adds `block_stack_ai.live` — the module whose
`LiveSession.receive` hands each observation to the agent — so a changed
controller is reported for a live record, while the same change leaves a
version-7 record verifying against the headless walk its own writer emitted, and
the controller section covers the objective-less live agents, refuses a loaded
controller closure whose imports were reloaded out from under it, and is
required of a version-8 record that configures exactly one agent and one seed), its
clear, well and board terms, the new agent's own count of the pieces it has been
shown, and the new agents' choices on constructed boards, without the native
engine. The second
requires the completed setup and tests native state reads, logical frame counts,
seeded hash determinism, the placement model against native locks including a
lock that straddles the ceiling and hidden minos surviving a later clear, the
whole enumerated placement set against engine-reachable straight drops from the
spawn origin, the whole reachable plan set against the origins the engine locks
at when it is driven with each plan's masks, the recorded piece count against the
native engine's own counters,
run-record verification for both record formats, a record written by the frozen
Experiment 003-era writer still verifying (its declared objective identity still
matches this tree, and its inputs replay), the Tetris agent's four-line
clear and the plan agent's four-line clear on a ready native well, the suite
record's declared objective and the live
session's clear-size histogram, version-8 written record, live-seeded
declared objective and controller section, and desktop replay exports
through the native writer and verifier. The desktop checks additionally require
the SDL3 target; they exercise live input, pause/step/restart, record verification,
invalid masks and pipe closure using dummy video/audio. None needs a display.
Integration tests are never treated as passing when the native library is
unavailable. The measured results are in
[experiments/000-connection](experiments/000-connection/notes.md) and
[experiments/001-greedy-heuristic](experiments/001-greedy-heuristic/notes.md),
and [experiments/README.md](experiments/README.md) describes the small record
convention. Experiment 004's retained rows reproduce only against the read-only
sibling Block Stack checkout they name — commit
`8ca4158711c2d6339cab1ee8d78aa65bd624c89d`, recorded dirty (`kind:
working-tree`) — whose uncommitted local changes cannot be exported and are not
retained here: the dependency is identified by
[its fingerprint manifest](experiments/004-bounded-well-plan/probes/engine_fingerprint.json),
not reconstructed, and no clean reproducible-dependency CI is claimed.
`runs/`, `.build/`, `.venv/`, caches, and future large model files are ignored.
Temporary run output is disposable.

## Later stages

The runner can keep supplying observations and accepting one frame mask at a
time. Experiment 001 adds the hand-written greedy placement heuristic and its
random baseline, Experiment 002 the path-aware one-piece-lookahead agent,
Experiment 003 the Tetris-oriented objective on 002's reachable set, and
Experiment 004 the bounded well plan; later experiments can add a search planner,
a learned evaluator, or a learned frame controller on the same engine connection
and run-recording workflow. None of those is implemented yet.
