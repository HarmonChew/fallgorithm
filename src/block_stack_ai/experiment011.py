"""Run and check Experiment 011 (a C++ ``reach_plan``).

    python -m block_stack_ai.experiment011 reference [--jobs N]
    python -m block_stack_ai.experiment011 parity [--jobs N]
    python -m block_stack_ai.experiment011 diverge RECORD [--baseline RECORD]
    python -m block_stack_ai.experiment011 bench [--jobs N]
    python -m block_stack_ai.experiment011 evaluate [--jobs N]
    python -m block_stack_ai.experiment011 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment011 summarize RECORD [--jobs N]

``reference`` plays Experiment 009's training seeds with the Python ``reach_plan``
(Experiment 010's ``_play``) in the three training formats of ``config.json``, and
times each game. Its record is what the C++ games are compared with, and its 30 Hz /
300 ms batch was timed too, but other work ran during it, so ``bench`` times Python and
C++ back to back instead. ``parity`` plays the same games with the C++ ``reach_plan``
(:func:`block_stack_ai.native.play_game`) and compares each one with the reference:
the same start, the same input bytes and the same results. ``diverge`` reports, for a
game that differs, the first decision where the two choose differently. ``verify``
replays a record's games on the engine and checks every result (Experiment 009's
``_replay``).

``bench`` is the predeclared speed measurement (training seeds only): the Python and
then the C++ batch of the 24 training games at 30 Hz / 300 ms, and the per-decision
times. ``evaluate`` plays Experiment 008's 300 held-out seeds with the C++ and compares
every game with Experiment 010's record; ``summarize`` writes ``result.json``.

Like Experiment 010's, every command writes its record under ``runs/`` only; the
retained copies in ``records/`` (``reference.json.gz``, ``run.json.gz``) are copied
there by hand.

A C++ game's result is not computed by new C++ accounting: its inputs are replayed
on the Python binding with Experiment 009's ``replay_outcome``, and the C++'s own
final counters must agree with that replay. ``decision_seconds`` holds the C++
game's wall time.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment008 as e8, experiment009 as e9, experiment010 as e10, runner
from . import native, reachplan, wellplan
from .engine import create_game
from .limits import Flight, Limits, next_wait
from .pathaware import LEFT, RIGHT, ROTATE_CCW, ROTATE_CW, grid_columns

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "011-native-speed"
CONFIG = EXPERIMENT_ROOT / "config.json"
RECORDS = EXPERIMENT_ROOT / "records"
REFERENCE = RECORDS / "reference.json.gz"
HELDOUT = RECORDS / "run.json.gz"
BENCH = EXPERIMENT_ROOT / "bench.json"
RESULT = EXPERIMENT_ROOT / "result.json"
FINAL_PARAMS = e10.FINAL_PARAMS  # Experiment 009's learned numbers, unchanged
BASELINE_RECORD = e10.EXPERIMENT_ROOT / "records" / "run.json.gz"
TIMING_GAMES, TIMING_STRIDE = 12, 20
CEM_GAMES = 32 * 24  # one Experiment 009 iteration: 32 candidates x 24 seeds
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


def play_native(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """One game like Experiment 010's ``_play``, played by the C++ ``reach_plan``."""
    index, fmt, seed, config = job
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    tick = time.perf_counter()
    played = native.play_game(config["game"], seed, line_cap=config["line_cap"],
                              frame_cap=config["frame_cap"],
                              limits=Limits(fmt["tap_hz"], fmt["reaction_ms"]),
                              params=native.params(config["params"]))
    seconds = time.perf_counter() - tick
    if played["initial_state_hash"] != initial_hash:
        raise ValueError(f"seed {seed}: the C++ engine starts in another state than the "
                         "binding's; rebuild both from the same Block Stack checkout")
    episode = {"format": index, "seed": seed, "initial_state_hash": initial_hash,
               "inputs": base64.b64encode(played["inputs"]).decode("ascii")}
    result, problem = e9.replay_outcome(episode, config)
    if problem:
        raise ValueError(f"seed {seed}: the C++ game does not replay: {problem}")
    differ = [name for name in ("score", "lines", "frames", "level", "stopping_reason",
                                "final_state_hash") if result[name] != played[name]]
    if differ:
        raise ValueError(f"seed {seed}: the C++ counters disagree with the replay on {differ}")
    result.update(pieces=played["pieces"], adjusts=played["adjusts"],
                  switches=played["switches"], decision_seconds=round(seconds, 3))
    episode["result"] = result
    episode["wall_seconds"] = round(seconds, 3)
    return episode


def _exact(value: Any) -> str:
    """A value as JSON writes it, so 1 and 1.0 (or True and 1) are different."""
    return json.dumps(value, sort_keys=True)


# The launcher (quickplay) plays a new game through ``_play``, as for 008-010.
_play = play_native


def compare(found: list[dict[str, Any]], expected: list[dict[str, Any]]) -> list[str]:
    """Differences between two records' games: start, input bytes, results but timing."""
    if [(e["format"], e["seed"]) for e in found] != [(e["format"], e["seed"]) for e in expected]:
        return ["the records do not hold the same formats and seeds in the same order"]
    problems = []
    for new, old in zip(found, expected):
        where = f"format {new['format']} seed {new['seed']}"
        if new["initial_state_hash"] != old["initial_state_hash"]:
            problems.append(f"{where}: different initial state")
        if new["inputs"] != old["inputs"]:
            problems.append(f"{where}: different inputs")
        new_fields = set(new["result"]) - {"decision_seconds"}
        old_fields = set(old["result"]) - {"decision_seconds"}
        if new_fields != old_fields:
            problems.append(f"{where}: result fields {sorted(new_fields ^ old_fields)} in one only")
        changed = sorted(f for f in new_fields & old_fields
                         if _exact(new["result"][f]) != _exact(old["result"][f]))
        if changed:
            problems.append(f"{where}: different {', '.join(changed)}")
    return problems


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
    return _write(record, "reference")


def decisions(episode: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Every search a recorded ``reach_plan`` game made, with the arguments it was given.

    The game is replayed from its inputs, and the agent's own state (its frame count,
    tap timers and drought) is rebuilt as :meth:`BenchAgent.act` keeps it, so each
    entry holds exactly what :func:`reachplan.search` was called with: ``"commit"`` at
    a spawn (the preview not known yet) and ``"adjust"`` at the reaction frame, or one
    ``"full"`` search at the spawn when the reaction time is 0. ``"at"`` is the index of
    the input frame the decision was made on.
    """
    fmt = config["formats"][episode["format"]]
    limits = Limits(fmt["tap_hz"], fmt["reaction_ms"])
    reaction, interval = limits.reaction_frames, limits.tap_interval
    found: list[dict[str, Any]] = []
    piece_count, frame, shift_wait, rotate_wait = -1, 0, 0, 0
    drought = before = 0

    def take(kind: str, state: Any, preview: str | None) -> None:
        found.append({
            "kind": kind, "at": at, "columns": grid_columns(wellplan.visible_grid(state.board)),
            "piece": state.current_piece, "next_piece": preview,
            "flight": Flight(state.orientation, state.x, state.y, state.gravity_counter,
                             state.first_delay_remaining, state.previous_input,
                             state.das_counter, shift_wait, rotate_wait, frame),
            "drought": drought, "level": state.level, "lines": state.lines,
            "start_level": state.start_level, "ruleset": state.ruleset})

    with create_game(**config["game"], seed=episode["seed"]) as game:
        state = game.state
        for at, mask in enumerate(base64.b64decode(episode["inputs"])):
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


def parity(jobs: int) -> tuple[Path, list[str]]:
    """The C++ ``reach_plan`` on the reference record's games, compared with them."""
    reference_record = _load(REFERENCE)
    config = reference_record["configuration"]
    work = [(e["format"], config["formats"][e["format"]], e["seed"], config)
            for e in reference_record["episodes"]]
    with Pool(jobs) as pool:
        episodes = pool.map(play_native, work, chunksize=1)
    record = {
        "schema": SCHEMA, "kind": "native-training",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": sources(), "episodes": episodes,
    }
    return _write(record, "parity"), compare(episodes, reference_record["episodes"])


def diverge(path: Path, baseline: Path = REFERENCE) -> list[str]:
    """How each game of ``path`` differs from the same game in ``baseline`` (a Python
    record: the training reference, or Experiment 010's for the held-out seeds).

    For different inputs it finds the first decision of the baseline game at which the
    Python and the C++ choose differently, replaying the baseline up to the first
    differing input.
    """
    base = _load(baseline)
    config = base["configuration"]
    by_game = {(e["format"], e["seed"]): e for e in base["episodes"]}
    native_params = native.params(config["params"])
    lines = []
    for episode in _load(path)["episodes"]:
        where = f"format {episode['format']} seed {episode['seed']}"
        old = by_game.get((episode["format"], episode["seed"]))
        if old is None:
            lines.append(f"{where}: no such game in {baseline.name}")
            continue
        problems = compare([episode], [old])
        if not problems:
            continue
        if episode["inputs"] == old["inputs"]:
            lines.append(f"{where}: same inputs, but " + "; ".join(problems))
            continue
        before, after = base64.b64decode(old["inputs"]), base64.b64decode(episode["inputs"])
        first = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b),
                     min(len(before), len(after)))
        where += f": inputs differ from frame {first}"
        if first == min(len(before), len(after)):
            where += f" (baseline {len(before)} inputs, this record {len(after)})"
        fmt = config["formats"][old["format"]]
        limits = Limits(fmt["tap_hz"], fmt["reaction_ms"])
        for decision in decisions(old, config):
            if decision["at"] > first:
                lines.append(f"{where}; every decision before it agrees")
                break
            kwargs = {key: decision[key] for key in
                      ("flight", "drought", "level", "lines", "start_level", "ruleset")}
            option = reachplan.search(decision["columns"], decision["piece"],
                                      decision["next_piece"], limits=limits,
                                      params=config["params"], **kwargs)
            python = None if option is None else (option[0].orientation, option[0].x,
                                                  option[0].y, option[0].masks)
            cpp = native.search(decision["columns"], decision["piece"], decision["next_piece"],
                                limits=limits, params=native_params, **kwargs)
            if python != cpp:
                lines.append(f"{where}; first different decision at frame {decision['at']} "
                             f"({decision['kind']}, piece {decision['piece']}, preview "
                             f"{decision['next_piece']}, level {decision['level']}): Python "
                             f"{python}, C++ {cpp}; columns {decision['columns']}, "
                             f"flight {decision['flight']}, drought {decision['drought']}")
                break
        else:
            lines.append(f"{where}; every decision agrees")
    return lines


# ---------------------------------------------------------------- speed

def _decision_kwargs(decision: dict[str, Any], limits: Limits) -> dict[str, Any]:
    return {key: decision[key] for key in
            ("flight", "drought", "level", "lines", "start_level", "ruleset")} | {"limits": limits}


def decision_times(record: dict[str, Any]) -> dict[str, Any]:
    """Per-decision time, one process: each sampled piece's commit plus adjust search.

    Every ``TIMING_STRIDE``-th piece of the first ``TIMING_GAMES`` 30 Hz / 300 ms games,
    with the recorded arguments. The Python's reach cache is emptied before each piece.
    """
    from . import reach
    config = record["configuration"]
    fmt = config["formats"][0]
    limits = Limits(fmt["tap_hz"], fmt["reaction_ms"])
    native_params = native.params(config["params"])
    bands = {"level_18_28": lambda v: v < 29, "level_29_38": lambda v: 29 <= v < 39,
             "level_39_plus": lambda v: v >= 39}
    seconds: dict[str, dict[str, list[float]]] = {band: {"python": [], "cpp": []} for band in bands}
    games = [e for e in record["episodes"] if e["format"] == 0][:TIMING_GAMES]
    for episode in games:
        pieces: list[list[dict[str, Any]]] = []
        for decision in decisions(episode, config):
            if decision["kind"] == "commit":
                pieces.append([decision])
            else:
                pieces[-1].append(decision)  # the same piece's adjust
        for piece in pieces[::TIMING_STRIDE]:
            band = next(name for name, inside in bands.items() if inside(piece[0]["level"]))
            reach._cached_search.cache_clear()
            tick = time.perf_counter()
            for d in piece:
                reachplan.search(d["columns"], d["piece"], d["next_piece"],
                                 params=config["params"], **_decision_kwargs(d, limits))
            seconds[band]["python"].append(time.perf_counter() - tick)
            tick = time.perf_counter()
            for d in piece:
                native.search(d["columns"], d["piece"], d["next_piece"], params=native_params,
                              **_decision_kwargs(d, limits))
            seconds[band]["cpp"].append(time.perf_counter() - tick)
    out = {}
    for band, values in seconds.items():
        python, cpp = statistics.mean(values["python"]), statistics.mean(values["cpp"])
        out[band] = {"pieces": len(values["python"]), "python_ms": round(1000 * python, 2),
                     "cpp_ms": round(1000 * cpp, 3), "speedup": round(python / cpp, 1)}
    return out


def bench(jobs: int = 24) -> dict[str, Any]:
    """The predeclared speed measurement; writes ``bench.json``."""
    load_before = [round(value, 2) for value in os.getloadavg()]
    config = training_configuration()
    fmt, seeds = config["formats"][0], config["format_seeds"][0]
    work = [(0, fmt, seed, config) for seed in seeds]
    batches = {}
    for name, play in (("python", _timed_python_game), ("cpp", play_native)):
        tick = time.perf_counter()
        with Pool(min(jobs, len(work))) as pool:
            games = pool.map(play, work, chunksize=1)
        batches[name] = {"games": games, "wall": time.perf_counter() - tick}
        print(f"{name}: {len(games)} games in {batches[name]['wall']:.1f} s", file=sys.stderr,
              flush=True)
    problems = compare(batches["cpp"]["games"], batches["python"]["games"])
    per_game = {name: statistics.mean(g["wall_seconds"] for g in batch["games"])
                for name, batch in batches.items()}
    result = {
        "load_average_before": load_before, "workers": min(jobs, len(work)),
        "format": fmt, "seeds": seeds,
        "python_seconds_per_game": round(per_game["python"], 2),
        "cpp_seconds_per_game": round(per_game["cpp"], 3),
        "per_game_speedup": round(per_game["python"] / per_game["cpp"], 1),
        "python_batch_wall_seconds": round(batches["python"]["wall"], 1),
        "cpp_batch_wall_seconds": round(batches["cpp"]["wall"], 1),
        "cpp_batch_identical_to_python_batch": not problems, "differences": problems,
        "per_decision": decision_times(_load(REFERENCE)),
        "versions": runner._record_versions(), "sources": sources(),
    }
    BENCH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


# ---------------------------------------------------------------- the held-out run

def heldout_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    seeds = _load(e8.CONFIG)["seeds"]
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "agent", "formats")} | {
        "format_seeds": [seeds], "seeds": seeds, "params": _load(FINAL_PARAMS)["resolved"]}


def evaluate(jobs: int = 30) -> tuple[Path, list[str]]:
    """The C++ on the 300 held-out seeds; returns the record and its differences from 010's."""
    config = heldout_configuration()
    work = [(0, config["formats"][0], seed, config) for seed in config["seeds"]]
    tick = time.perf_counter()
    with Pool(jobs) as pool:
        episodes = pool.map(play_native, work, chunksize=1)
    wall = time.perf_counter() - tick
    record = {
        "schema": SCHEMA, "kind": "native-heldout",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": sources(), "workers": jobs, "wall_seconds": round(wall, 1),
        "episodes": episodes,
    }
    return _write(record, "heldout"), compare(episodes, _load(BASELINE_RECORD)["episodes"])


def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    record = _load(path)
    base = _load(BASELINE_RECORD)
    differences = compare(record["episodes"], base["episodes"])
    replay_problems = verify(path, jobs)
    speed = _load(BENCH)
    cpp_seconds = [e["wall_seconds"] for e in record["episodes"]]
    python_seconds = [e["result"]["decision_seconds"] for e in base["episodes"]]
    exact = not differences and not replay_problems
    fast = speed["per_game_speedup"] >= 50
    return {
        "experiment": "011-native-speed",
        "question": ("Does the C++ reach_plan play exactly the same games as the Python "
                     "reach_plan of Experiment 010, at least 50 times faster?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "baseline": str(BASELINE_RECORD.relative_to(runner.PROJECT_ROOT)),
        "heldout_games": len(record["episodes"]),
        "identical_games": (0 if any(not d.startswith("format ") for d in differences) else
                            len(record["episodes"]) - len({d.split(":")[0] for d in differences})),
        "differences": differences, "replay_problems": replay_problems,
        "speed": {key: speed[key] for key in (
            "load_average_before", "workers", "python_seconds_per_game", "cpp_seconds_per_game",
            "per_game_speedup", "python_batch_wall_seconds", "cpp_batch_wall_seconds",
            "cpp_batch_identical_to_python_batch", "per_decision")},
        "heldout_run": {
            "workers": record["workers"], "wall_seconds_with_replay": record["wall_seconds"],
            "cpp_seconds_per_game_mean": round(statistics.mean(cpp_seconds), 3),
            # computed (the C++ seconds of all games / workers), not a measured wall clock
            "cpp_seconds_summed_per_worker": round(sum(cpp_seconds) / record["workers"], 1),
            "python_010_decision_seconds_per_game_mean": round(statistics.mean(python_seconds), 1),
        },
        "cem_iteration_seconds_projected": round(
            CEM_GAMES * statistics.mean(cpp_seconds) / record["workers"], 1),
        "success_rule": ("exact: all 300 held-out games identical to Experiment 010's record and "
                         "verified on the engine; fast: per-game speed-up on the training seeds "
                         "at least 50"),
        "success": {"exact": exact, "fast": fast, "both": exact and fast},
        "metrics": e9.metrics([{"seed": e["seed"], **e["result"]} for e in record["episodes"]]),
    }


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
    par = commands.add_parser("parity", help="the C++ reach_plan on the reference games, compared")
    par.add_argument("--jobs", type=int, default=30)
    div = commands.add_parser("diverge", help="the first differing decision of each differing game")
    div.add_argument("record", type=Path)
    div.add_argument("--baseline", type=Path, default=REFERENCE,
                     help="the Python record to compare with (default: the training reference)")
    speed = commands.add_parser("bench", help="the predeclared speed measurement (training seeds)")
    speed.add_argument("--jobs", type=int, default=24)
    held = commands.add_parser("evaluate", help="the C++ on the 300 held-out seeds")
    held.add_argument("--jobs", type=int, default=30)
    summary = commands.add_parser("summarize", help="write result.json from a held-out record")
    summary.add_argument("record", type=Path)
    summary.add_argument("--jobs", type=int, default=30)
    check = commands.add_parser("verify", help="replay a record on the engine")
    check.add_argument("record", type=Path)
    check.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "reference":
            print(reference(args.jobs))
        elif args.command == "parity":
            path, problems = parity(args.jobs)
            print(path)
            for problem in problems:
                print(problem, file=sys.stderr)
            print("identical to the reference" if not problems else f"{len(problems)} differences")
            return 1 if problems else 0
        elif args.command == "diverge":
            for line in diverge(args.record.resolve(), args.baseline.resolve()) or \
                    [f"no game differs from {args.baseline}"]:
                print(line)
        elif args.command == "bench":
            result = bench(args.jobs)
            print(json.dumps({k: v for k, v in result.items() if k not in ("sources", "seeds")},
                             indent=1))
        elif args.command == "evaluate":
            path, problems = evaluate(args.jobs)
            print(path)
            for problem in problems:
                print(problem, file=sys.stderr)
            print("all games identical to Experiment 010's" if not problems
                  else f"{len(problems)} differences from Experiment 010's record")
            return 1 if problems else 0
        elif args.command == "summarize":
            RESULT.write_text(json.dumps(summarize(args.record.resolve(), args.jobs), indent=1)
                              + "\n", encoding="utf-8")
            print(f"Wrote {RESULT}")
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
