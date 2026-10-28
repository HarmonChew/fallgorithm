"""Run and check Experiment 011 (a C++ ``reach_plan``).

    python -m block_stack_ai.experiment011 reference [--jobs N]
    python -m block_stack_ai.experiment011 verify RECORD [--jobs N]

``reference`` plays Experiment 009's training seeds with the Python ``reach_plan``
(Experiment 010's ``_play``) in the three training formats of ``config.json``, and
times each game. Its record is what the C++ games are compared with, and its 30 Hz /
300 ms batch is the Python side of the speed rule; it runs that batch alone, one game
per worker. ``verify`` replays a record's games on the engine and checks every
result (Experiment 009's ``_replay``).
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment008 as e8, experiment009 as e9, experiment010 as e10, runner
from . import wellplan
from .engine import create_game
from .limits import Flight, Limits, next_wait
from .pathaware import LEFT, RIGHT, ROTATE_CCW, ROTATE_CW, grid_columns

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "011-native-speed"
CONFIG = EXPERIMENT_ROOT / "config.json"
RECORDS = EXPERIMENT_ROOT / "records"
REFERENCE = RECORDS / "reference.json.gz"
NATIVE_SOURCES = runner.PROJECT_ROOT / "native"
SCHEMA = "fallgorithm.experiment011.run/1"


def _load(path: Path) -> Any:
    return e10._load(path)


def training_configuration() -> dict[str, Any]:
    """The training formats, each with its prefix of 009's training seeds."""
    config = _load(CONFIG)
    seeds = _load(e9.SEEDS)["train_seeds"]
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "agent")} | {
        "formats": [{"tap_hz": f["tap_hz"], "reaction_ms": f["reaction_ms"]}
                    for f in config["training"]["formats"]],
        "format_seeds": [seeds[:f["seed_count"]] for f in config["training"]["formats"]],
        "params": _load(e10.FINAL_PARAMS)["resolved"]}


def sources() -> dict[str, str]:
    """Digests of the package's Python files and of ``native/``."""
    native = {f"native/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(NATIVE_SOURCES.iterdir()) if path.is_file()}
    return e8._sources() | native


def _timed_python_game(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    tick = time.perf_counter()
    episode = e10._play(job)
    episode["wall_seconds"] = round(time.perf_counter() - tick, 3)
    return episode


def _write(record: dict[str, Any], tag: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-011-{tag}"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def reference(jobs: int) -> Path:
    """Python ``reach_plan`` on the training seeds, each format a separate timed batch."""
    config = training_configuration()
    episodes, batches = [], []
    for index, (fmt, seeds) in enumerate(zip(config["formats"], config["format_seeds"])):
        work = [(index, fmt, seed, config) for seed in seeds]
        workers = min(jobs, len(work))
        tick = time.perf_counter()
        with Pool(workers) as pool:
            found = pool.map(_timed_python_game, work, chunksize=1)
        batches.append({"format": index, "games": len(work), "workers": workers,
                        "wall_seconds": round(time.perf_counter() - tick, 2)})
        episodes += found
        print(f"format {fmt}: {len(work)} games in {batches[-1]['wall_seconds']} s",
              file=sys.stderr, flush=True)
    record = {
        "schema": SCHEMA, "kind": "python-reference",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": sources(), "batches": batches, "episodes": episodes,
    }
    path = _write(record, "reference")
    RECORDS.mkdir(exist_ok=True)
    shutil.copyfile(path, REFERENCE)
    return path


def decisions(episode: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Every search a recorded ``reach_plan`` game made, with the arguments it was given.

    The game is replayed from its inputs, and the agent's own state (its frame count,
    tap timers and drought) is rebuilt as :meth:`BenchAgent.act` keeps it, so each
    entry holds exactly what :func:`reachplan.search` was called with: ``"commit"`` at
    a spawn (the preview not known yet) and ``"adjust"`` at the reaction frame, or one
    ``"full"`` search at the spawn when the reaction time is 0.
    """
    fmt = config["formats"][episode["format"]]
    limits = Limits(fmt["tap_hz"], fmt["reaction_ms"])
    reaction, interval = limits.reaction_frames, limits.tap_interval
    found: list[dict[str, Any]] = []
    piece_count, frame, shift_wait, rotate_wait = -1, 0, 0, 0
    drought = before = 0

    def take(kind: str, state: Any, preview: str | None) -> None:
        found.append({
            "kind": kind, "columns": grid_columns(wellplan.visible_grid(state.board)),
            "piece": state.current_piece, "next_piece": preview,
            "flight": Flight(state.orientation, state.x, state.y, state.gravity_counter,
                             state.first_delay_remaining, state.previous_input,
                             state.das_counter, shift_wait, rotate_wait, frame),
            "drought": drought, "level": state.level, "lines": state.lines,
            "start_level": state.start_level, "ruleset": state.ruleset})

    with create_game(**config["game"], seed=episode["seed"]) as game:
        state = game.state
        for mask in base64.b64decode(episode["inputs"]):
            if state.phase == "active" and not state.terminal:
                if state.piece_count != piece_count:
                    piece_count, frame, shift_wait, rotate_wait = state.piece_count, 0, 0, 0
                    before = drought
                    if reaction == 0:
                        drought = 0 if "I" in (state.current_piece, state.next_piece) else before + 1
                        take("full", state, state.next_piece)
                    else:
                        drought = 0 if state.current_piece == "I" else before + 1
                        take("commit", state, None)
                elif reaction > 0 and frame == reaction:
                    drought = 0 if "I" in (state.current_piece, state.next_piece) else before + 1
                    take("adjust", state, state.next_piece)
                shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
                rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)), interval)
                frame += 1
            state, _ = game.step(mask)
    return found


def _replay(episode: dict[str, Any], config: dict[str, Any]) -> list[str]:
    return e9._replay(episode, config)


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 011 record"]
    config = record["configuration"]
    expected = [(index, seed) for index, seeds in enumerate(config["format_seeds"])
                for seed in seeds]
    if [(e["format"], e["seed"]) for e in record["episodes"]] != expected:
        return ["episodes do not match the configured formats and seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(_replay, [(e, config) for e in record["episodes"]], chunksize=1)
    return [problem for problems in found for problem in problems]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment011")
    commands = parser.add_subparsers(dest="command", required=True)
    ref = commands.add_parser("reference", help="Python reach_plan on the training seeds")
    ref.add_argument("--jobs", type=int, default=24)
    check = commands.add_parser("verify", help="replay a record on the engine")
    check.add_argument("record", type=Path)
    check.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "reference":
            print(reference(args.jobs))
        elif args.command == "verify":
            problems = verify(args.record.resolve(), args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            print("verified" if not problems else f"{len(problems)} problems")
            return 1 if problems else 0
    except e10.EngineError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
