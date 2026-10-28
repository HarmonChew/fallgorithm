"""Watch one game from an experiment record in the desktop window.

    python -m block_stack_ai.watchrecord RECORD --seed N [--agent NAME | --format F] [--export-only]

Experiments 006 and later keep their own records rather than going through
:mod:`block_stack_ai.runner`, so ``block-stack-ai watch`` cannot open them.
Every such record holds the game configuration and, per episode, the seed and
the frame inputs, so this module picks one episode, writes it through the
engine's own replay writer and opens the replay. The replay's final state is
checked against the recorded result first, so a stale engine build is reported
instead of shown.

``--agent`` picks the agent in a record of several agents (Experiment 006).
``--format`` picks the input-limit format of an Experiment 008 record, either
by index or as ``30hz-300ms``.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

from .engine import EngineError, engine_executable
from .runner import PROJECT_ROOT

WATCH_DIR = PROJECT_ROOT / "runs" / "watch"


def load_record(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def format_name(entry: dict[str, Any]) -> str:
    return f"{entry['tap_hz']:g}hz-{entry['reaction_ms']:g}ms"


def _format_index(record: dict[str, Any], value: str) -> int:
    formats = record["configuration"].get("formats")
    if not formats:
        raise ValueError("This record has no formats; drop --format.")
    names = [format_name(entry) for entry in formats]
    if value.isdigit() and int(value) < len(formats):
        return int(value)
    if value.lower() in names:
        return names.index(value.lower())
    raise ValueError(f"Unknown format {value!r}; choose one of: {', '.join(names)}")


def select_episode(record: dict[str, Any], seed: int, *, agent: str | None = None,
                   format_value: str | None = None) -> dict[str, Any]:
    """The one episode matching the seed and, where needed, agent or format."""
    episodes = [episode for episode in record["episodes"] if episode["seed"] == seed]
    if agent is not None:
        episodes = [episode for episode in episodes if episode.get("agent") == agent]
    if format_value is not None:
        index = _format_index(record, format_value)
        episodes = [episode for episode in episodes if episode.get("format") == index]
    if not episodes:
        raise ValueError(f"No episode with seed {seed} matches; see --list.")
    if len(episodes) > 1:
        raise ValueError(f"Seed {seed} has several episodes; choose one with "
                         f"--agent or --format (options: {', '.join(describe(record, e) for e in episodes)}).")
    return episodes[0]


def episode_inputs(episode: dict[str, Any]) -> bytes:
    """Frame inputs, stored as a list (006) or as base64 (008)."""
    inputs = episode["inputs"]
    return base64.b64decode(inputs) if isinstance(inputs, str) else bytes(inputs)


def describe(record: dict[str, Any], episode: dict[str, Any]) -> str:
    if "agent" in episode:
        return f"agent {episode['agent']}"
    if "format" in episode:
        return f"format {format_name(record['configuration']['formats'][episode['format']])}"
    return "the only episode"


def list_episodes(record: dict[str, Any]) -> list[str]:
    rows = []
    for episode in record["episodes"]:
        result = episode["result"]
        rows.append(f"seed {episode['seed']:>5}  {describe(record, episode):<24} "
                    f"lines {result['lines']:>5}  score {result['score']:>9}  "
                    f"{result['stopping_reason']}")
    return rows


def export(record: dict[str, Any], episode: dict[str, Any], replay_path: Path) -> Path:
    """Write the episode through the engine's replay writer and check its end state."""
    game = record["configuration"]["game"]
    inputs = episode_inputs(episode)
    result = episode["result"]
    frames = result.get("frame_count", result.get("frames"))
    if frames is None:
        raise ValueError("The record's result has no frame count, so the replay cannot be checked.")
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="watch-", dir=replay_path.parent) as directory:
        temporary = Path(directory)
        input_file = temporary / "inputs.bin"
        replay = temporary / "game.rep"
        state = temporary / "state.json"
        input_file.write_bytes(inputs)
        command = [
            str(engine_executable("block_stack_headless")), "--rules", game["ruleset"],
            "--mode", game["mode"], "--level", str(game["start_level"]),
            "--height", str(game["height"]), "--seed", str(episode["seed"]),
            "--frames", str(len(inputs)), "--input-file", str(input_file.resolve()),
            "--replay-out", str(replay.resolve()), "--dump-state", str(state.resolve()),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            raise EngineError(f"Replay export failed: {error.stderr.strip()}") from error
        actual = json.loads(state.read_text(encoding="utf-8"))
        if f"{actual['hash']:016x}" != result["final_state_hash"] or actual["frame"] != frames:
            raise EngineError("The replay does not end where the record does. Rebuild the "
                              "engine with scripts/setup_engine.py --desktop.")
        replay.replace(replay_path)
    return replay_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch one game from an experiment record.")
    parser.add_argument("record", type=Path, help="record file, e.g. experiments/008-*/records/run.json.gz")
    parser.add_argument("--seed", type=int, help="the game's seed")
    parser.add_argument("--agent", help="agent, when the record has several")
    parser.add_argument("--format", dest="format_value", help="format index or name such as 30hz-300ms")
    parser.add_argument("--list", action="store_true", help="list the record's games and exit")
    parser.add_argument("--export-only", action="store_true", help="write the .rep without opening it")
    args = parser.parse_args(argv)
    if not args.list and args.seed is None:
        parser.error("--seed is required (use --list to see the games)")
    try:
        record = load_record(args.record)
        if args.list:
            print("\n".join(list_episodes(record)))
            return 0
        episode = select_episode(record, args.seed, agent=args.agent, format_value=args.format_value)
        label = describe(record, episode).split(" ", 1)[-1].replace(" ", "-")
        name = f"{args.record.name.split('.')[0]}-{args.record.parent.parent.name}-{args.seed}-{label}.rep"
        replay_path = export(record, episode, WATCH_DIR / name)
    except (ValueError, EngineError, OSError, KeyError) as error:
        print(error, file=sys.stderr)
        return 1
    result = episode["result"]
    print(f"Replay: {replay_path}")
    print(f"Seed {args.seed}, {describe(record, episode)}: {result['lines']} lines, "
          f"score {result['score']}, {result['stopping_reason']}.")
    if args.export_only:
        return 0
    print("Starts paused. P: play/pause; .: one frame; [ / ]: speed; F1: debug.", flush=True)
    return subprocess.run([str(engine_executable("block_stack")), "--replay",
                           str(replay_path.resolve()), "--paused"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
