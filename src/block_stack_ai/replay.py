"""Export verified inputs through the engine's own desktop replay writer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from .engine import EngineError, engine_executable
from .runner import VerificationError, verify_run


def export_replay(record_path: Path) -> tuple[Path, list[str]]:
    warnings = verify_run(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    config = record["configuration"]["game"]
    expected = record["result"]
    executable = engine_executable("block_stack_headless")
    replay_path = record_path.with_suffix(".rep")
    if replay_path.resolve() == record_path.resolve():
        raise ValueError("The run record must not have a .rep extension")

    # Keep the writer in C++, and compare its result with the Python run too:
    # BLOCKS_NATIVE_LIB may point to a different build from this executable.
    with TemporaryDirectory(prefix="replay-", dir=record_path.parent) as directory:
        temporary = Path(directory)
        inputs = temporary / "inputs.bin"
        replay = temporary / "run.rep"
        state = temporary / "state.json"
        inputs.write_bytes(bytes(record["inputs"]))
        command = [
            str(executable), "--rules", config["ruleset"], "--mode", config["mode"],
            "--level", str(config["start_level"]), "--height", str(config["height"]),
            "--seed", str(config["seed"]), "--frames", str(len(record["inputs"])),
            "--input-file", str(inputs.resolve()), "--replay-out", str(replay.resolve()),
            "--dump-state", str(state.resolve()),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            raise EngineError(f"Replay export failed: {error.stderr.strip()}") from error
        actual = json.loads(state.read_text(encoding="utf-8"))
        if (f"{actual['hash']:016x}" != expected["final_state_hash"]
                or actual["frame"] != expected["frame_count"]):
            raise VerificationError(
                "Desktop replay differs from the recorded run. Rebuild the engine "
                "and check BLOCKS_NATIVE_LIB; the replay was not replaced."
            )
        replay.replace(replay_path)
    return replay_path, warnings


def watch_run(record_path: Path) -> int:
    executable = engine_executable("block_stack")
    replay_path, warnings = export_replay(record_path)
    print(f"Replay: {replay_path}", flush=True)
    for warning in warnings:
        print(f"Warning: {warning}", flush=True)
    print("Starts paused. P: play/pause; .: one frame; [ / ]: speed; F1: debug.", flush=True)
    return subprocess.run([
        str(executable), "--replay", str(replay_path.resolve()), "--paused",
    ], check=False).returncode
