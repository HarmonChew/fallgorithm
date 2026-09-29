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

    PYTHONPATH=<tree>/src python loaded_identity_program.py {clean,edit} <workdir>

``clean`` is the control: the file is not touched, so the loaded bytes, the tree
and the recorded identity must all agree and the record must verify. ``edit``
runs the counterexample. The program prints one JSON object (``package``,
``before``, ``on_disk``, ``loaded``, ``tree``, ``record``, ``outcome``) and exits
0; the drivers — ``tests/test_unit.py``, ``evidence.py loaded-identity`` and
``prechange_probe.py loaded_identity`` — assert the contract on that JSON, so the
program itself does not decide what the contract is.

The stand-in game ignores the mask it is given, so every episode replays exactly
as it was recorded and only the identity can separate a verified record from a
reported one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

EDIT = b"\n# edited after the load\n"

# 1. The modules whose code a choice runs through are imported first.
import block_stack_ai.agents
import block_stack_ai.tetris

source = Path(sys.modules["block_stack_ai.tetris"].__file__)
before = hashlib.sha256(source.read_bytes()).hexdigest()

# 2. One of their files is edited after that code was loaded.
if sys.argv[1] == "edit":
    source.write_bytes(source.read_bytes() + EDIT)
on_disk = hashlib.sha256(source.read_bytes()).hexdigest()

# 3. Only now is the writer imported; this is where it binds its identity.
from block_stack_ai import runner


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
    path = runner.run_and_save(config, root / "runs", FakeGame)
    record = json.loads(path.read_text(encoding="utf-8"))
    try:
        runner.verify_run(path, FakeGame)
        outcome: dict[str, object] = {"verified": True}
    except runner.VerificationError as error:
        outcome = {"verified": False, "error": str(error)}
    print(json.dumps({
        "package": block_stack_ai.__file__,
        "before": before,
        "on_disk": on_disk,
        "loaded": runner._LOADED_OBJECTIVE_SOURCES["block_stack_ai.tetris"],
        "tree": runner._objective_sources()["block_stack_ai.tetris"],
        "record": record["objective"]["sources"]["block_stack_ai.tetris"],
        "outcome": outcome,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
