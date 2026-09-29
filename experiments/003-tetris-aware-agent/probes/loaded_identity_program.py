"""The reviewer's counterexample, as a program: the load order that separates a
record's identity from the file on the tree.

The ordering is the whole point, so this has to run in a fresh process against a
copy of the tree under test:

1. the modules the objective's choices run through are imported — this is the
   code the process will execute;
2. one of their source files is edited, so the bytes on the tree and the bytes
   that were loaded now differ;
3. only then is the module that writes records imported, because that is where
   the writer binds the identity it stamps on every record it writes.

A writer that reads each module's path at step 3 records the post-edit bytes
while ``sys.modules`` still executes the pre-edit code, and a later verification
reads the same post-edit file, so the record's provenance is certified although
the code that chose its inputs was never what the identity names. A writer that
takes the identity from the loader that read the source records the loaded bytes,
and verification then reports the record because the file it names has moved on.

Usage::

    PYTHONPATH=<tree>/src python loaded_identity_program.py {clean,edit,reload} <workdir>

``clean`` is the control: the file is not touched, so the loaded bytes, the tree
and the recorded identity must all agree and the record must verify. ``edit``
runs the counterexample. ``reload`` runs a second counterexample of the same
family, in the opposite direction: the covered module is loaded, the file is
edited, the module is **reloaded** from the edited file, and only then is a run
built. The code the process executes from that point on is the edited code, so a
writer that keeps an identity bound when it was imported records the pre-reload
bytes and names an implementation that no longer computes the choices — the
mirror image of ``edit``, where the loader's record rather than the file is the
truth. Both modes' edit appends a comment, so the reloaded code chooses exactly
what the code it replaced chose: the recorded identity is the only thing that can
separate the two, which is what makes the counterexample sharp. The
program prints one JSON object (``package``, ``before``, ``on_disk``,
``loaded``, ``loader``, ``tree``, ``record``, ``outcome``) and exits 0; the
drivers — ``tests/test_unit.py`` and ``prechange_probe.py``'s ``loaded_identity``
and ``loaded_identity_reload`` rows — assert the contract on that JSON, so the
program itself does not decide what the contract is.

The stand-in game ignores the mask it is given, so every episode replays exactly
as it was recorded and only the identity can separate a verified record from a
reported one.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

EDIT = b"\n# edited after the load\n"
# ``reload`` edits and reloads the wrapper that drives the objective rather than
# the objective module itself: the wrapper is what hands the objective its state
# and executes the placement it returns, and a reload of *that* module rebinds the
# names its classes resolve at call time, so the reloaded source is the code that
# computes the later choices. A reload of the objective module alone would leave
# the wrapper's own binding of ``tetris_choice`` pointing at the module object it
# imported, which is the same code as before the reload — nothing the reloaded
# bytes hold would run. That partial reload is ``mixed``: it is the case a writer
# must *refuse* rather than name, because one digest cannot describe both the
# reloaded module and the object the running code still calls.
MODE = sys.argv[1]
# The module the edit lands in, and the modules reloaded after it. ``reload`` is
# the coherent case: the wrapper that computes the choices is reloaded together
# with the writer that holds its factory by value, so nothing runs the replaced
# objects. ``mixed`` reloads the objective module alone (the wrapper keeps the
# callable it imported) and ``mixed-caller`` reloads the wrapper alone (the writer
# keeps the factory it imported), and both are the closures a writer has to refuse
# rather than name.
EDIT_SUBJECT = ("block_stack_ai.agents" if MODE in ("reload", "mixed-caller")
                else "block_stack_ai.tetris")
RELOADED = {
    "clean": (),
    "edit": (),
    "reload": ("block_stack_ai.agents", "block_stack_ai.runner"),
    "mixed": ("block_stack_ai.tetris",),
    "mixed-caller": ("block_stack_ai.agents",),
}[MODE]
SUBJECT = EDIT_SUBJECT

# 1. The modules whose code a choice runs through are imported first.
import block_stack_ai.agents
import block_stack_ai.tetris

source = Path(sys.modules[SUBJECT].__file__)
before = hashlib.sha256(source.read_bytes()).hexdigest()

# 2. One of their files is edited after that code was loaded. The ``edit``
# counterexample stops here; the ``reload`` counterexample edits the file only
# after the writer has been imported, below.
if MODE == "edit":
    source.write_bytes(source.read_bytes() + EDIT)

# 3. Only now is the writer imported; this is where it takes its identity. The
# recorder module is asked for only where it exists: the trees this program is run
# against predate it by design (they are the trees whose identity handling the
# rows measure), so its absence is reported as ``None`` rather than aborting a
# counterexample that does not need it.
from block_stack_ai import runner  # noqa: E402

try:  # noqa: SIM105
    from block_stack_ai import sourceidentity  # noqa: E402
except ImportError:  # a tree older than the recorder, measured by the clean/edit rows
    sourceidentity = None  # type: ignore[assignment]

# The second counterexample: a long-lived process that reloads a covered module
# after the writer was imported. The reload re-reads the edited file, so from here
# on the loader's record and the code the process executes are both the edited
# source, while an identity bound at import still names the bytes it bound. The
# ``mixed`` mode does the same for the objective module alone, whose callable the
# wrapper holds by value: the loader's record moves to the edited source while the
# code that would compute a choice does not, which is the closure a writer has to
# refuse instead of naming.
if RELOADED:
    source.write_bytes(source.read_bytes() + EDIT)
    for name in RELOADED:
        importlib.reload(sys.modules[name])

on_disk = hashlib.sha256(source.read_bytes()).hexdigest()


def writer_loaded_identity() -> str:
    """The subject module's identity the tree's writer would record right now.

    Read through whichever view the tree under test carries: ``reload`` compares
    the writer's own answer with the loader's record (``loader`` below), so this
    has to be the writer's view rather than a second read of the same record.
    """
    reader = getattr(runner, "_loaded_objective_sources", None)
    if reader is not None:
        return reader()[SUBJECT]
    return runner._LOADED_OBJECTIVE_SOURCES[SUBJECT]



class FakeState:
    """The placement-agent fields of an engine state, on an empty board."""

    def __init__(self) -> None:
        self.frame = 0
        self.score = 0
        self.lines = 0
        self.terminal = False
        self.phase = "active"
        self.piece_count = 0
        self.current_piece = "T"
        self.next_piece = "O"
        self.board = ((0,) * 10,) * 20
        self.hidden_rows = ((0,) * 10,) * 2
        self.orientation = 0
        self.x = 5
        self.level = 18
        self.start_level = 18
        self.first_delay_remaining = 0
        self.ruleset = "classic_ntsc_extended"
        self.mode = "endless"


class FakeGame:
    """One locked line per step; the mask is ignored, so a replay is exact."""

    def __init__(self, **_: object) -> None:
        self.state = FakeState()
        self.steps = 0

    def __enter__(self) -> "FakeGame":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def state_hash(self) -> int:
        return self.state.frame

    def step(self, mask: int):
        self.steps += 1
        self.state.frame += 1
        self.state.lines += 1
        self.state.piece_count = self.steps
        self.state.terminal = self.steps >= 2
        fields = {name: 0 for name in (
            "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
            "game_over", "challenge_completed", "lines_cleared", "score_delta")}
        fields["locked"] = True
        fields["lines_cleared"] = 1
        fields["game_over"] = int(self.state.terminal)
        return self.state, SimpleNamespace(**fields)


def main() -> int:
    root = Path(sys.argv[2])
    config = root / "config.json"
    config.write_text(json.dumps({
        "game": {"ruleset": "classic_ntsc_extended", "mode": "endless",
                 "start_level": 18, "height": 0},
        "frame_limit": 2,
        "seeds": [1],
        "agents": ["lookahead", "tetris"],
    }), encoding="utf-8")
    # The record's provenance is what is under test, not this machine's Git state.
    runner.engine_root = lambda: Path("/engine")
    runner.git_info = lambda root: {"commit": "abc123", "dirty": False,
                                    "kind": "committed"}
    # A writer asked to name a mixed closure is expected to refuse it rather than
    # stamp a record; the refusal is the observation the driver asserts on, so it
    # is reported as data instead of aborting the program.
    refused = False
    refusal: str | None = None
    try:
        path = runner.run_and_save(config, root / "runs", FakeGame)
    except runner.VerificationError as error:
        refused, refusal = True, str(error)
        record: dict = {}
    else:
        record = json.loads(path.read_text(encoding="utf-8"))
    if refused:
        outcome: dict[str, object] = {"verified": None}
    else:
        try:
            runner.verify_run(path, FakeGame)
            outcome = {"verified": True}
        except runner.VerificationError as error:
            outcome = {"verified": False, "error": str(error)}
    # The writer's own view is asked for last, and it refuses the same mixed
    # closure the writer refused: the refusal is the observation either way.
    try:
        loaded: str | None = writer_loaded_identity()
    except runner.VerificationError as error:
        loaded = None
        if not refused:
            refused, refusal = True, str(error)
    print(json.dumps({
        "package": block_stack_ai.__file__,
        "mode": MODE,
        "subject": SUBJECT,
        "before": before,
        "on_disk": on_disk,
        "loaded": loaded,
        "loader": (sourceidentity.loaded_source_digest(SUBJECT)
                   if sourceidentity is not None else None),
        "tree": runner._objective_sources()[SUBJECT],
        "record": (record.get("objective", {}).get("sources", {}).get(SUBJECT)
                   if record else None),
        "refused": refused,
        "refusal": refusal,
        "outcome": outcome,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
