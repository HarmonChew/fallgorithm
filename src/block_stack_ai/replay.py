"""Export verified inputs through the engine's own desktop replay writer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable

from .engine import EngineError, engine_executable
from .runner import VerificationError, verify_run


def _replay_sections(record: dict, record_path: Path) -> tuple[dict, list[int], dict]:
    """The game, executed inputs and expected result of a replayable record.

    A scripted record holds its one game in its own fields. A suite record is
    replayable when it holds exactly one episode: a live game is saved by
    ``LiveSession`` as a one-episode suite, and the desktop replay writer needs
    the same seed, game settings, inputs and final result from it. A headless
    suite with several games stays unsupported, as it always was, and names the
    record rather than exporting a replay of an arbitrary episode.
    """
    configuration = record["configuration"]
    if "episodes" in record:
        episodes = record["episodes"]
        if not isinstance(episodes, list) or len(episodes) != 1:
            count = len(episodes) if isinstance(episodes, list) else "an unknown number of"
            raise ValueError(
                f"{record_path} holds {count} episodes; only a single-game record "
                "can be exported to a desktop replay"
            )
        episode = episodes[0]
        return ({**configuration["game"], "seed": episode["seed"]},
                episode["inputs"], episode["result"])
    return configuration["game"], record["inputs"], record["result"]


def export_replay(record_path: Path, *,
                  verifier: Callable[[Path], list[str]] | None = None) -> tuple[Path, list[str]]:
    """Verify a record and export its inputs through the engine's replay writer.

    ``verifier`` lets a command whose record carries an experiment-specific
    identity — Experiment 005's search records — supply the verifier that
    re-derives it; the default is the stock verifier.
    """
    verify = verify_run if verifier is None else verifier
    warnings = verify(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    config, inputs, expected = _replay_sections(record, record_path)
    executable = engine_executable("block_stack_headless")
    replay_path = record_path.with_suffix(".rep")
    if replay_path.resolve() == record_path.resolve():
        raise ValueError("The run record must not have a .rep extension")

    # Keep the writer in C++, and compare its result with the Python run too:
    # BLOCKS_NATIVE_LIB may point to a different build from this executable.
    with TemporaryDirectory(prefix="replay-", dir=record_path.parent) as directory:
        temporary = Path(directory)
        input_file = temporary / "inputs.bin"
        replay = temporary / "run.rep"
        state = temporary / "state.json"
        input_file.write_bytes(bytes(inputs))
        command = [
            str(executable), "--rules", config["ruleset"], "--mode", config["mode"],
            "--level", str(config["start_level"]), "--height", str(config["height"]),
            "--seed", str(config["seed"]), "--frames", str(len(inputs)),
            "--input-file", str(input_file.resolve()), "--replay-out", str(replay.resolve()),
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


def watch_run(record_path: Path, *,
              verifier: Callable[[Path], list[str]] | None = None) -> int:
    executable = engine_executable("block_stack")
    replay_path, warnings = export_replay(record_path, verifier=verifier)
    print(f"Replay: {replay_path}", flush=True)
    for warning in warnings:
        print(f"Warning: {warning}", flush=True)
    print("Starts paused. P: play/pause; .: one frame; [ / ]: speed; F1: debug.", flush=True)
    return subprocess.run([
        str(executable), "--replay", str(replay_path.resolve()), "--paused",
    ], check=False).returncode
