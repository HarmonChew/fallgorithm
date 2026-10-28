"""Run, verify and summarise Experiment 008 (the benchmark format).

    python -m block_stack_ai.experiment008 select-seeds [--count N]
    python -m block_stack_ai.experiment008 run [--jobs N]
    python -m block_stack_ai.experiment008 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment008 summarize RECORD

``run`` plays every (format, seed) pair of ``config.json`` in parallel with
:class:`block_stack_ai.benchplan.BenchAgent`, using its own small episode loop,
and writes one gzipped record under ``runs/``. A game ends at a top-out, at the
line cap, or at a frame safety cap. ``verify`` replays the recorded inputs on the
native engine and checks every outcome. ``summarize`` writes ``result.json``.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment006, runner
from .benchplan import BENCH_AGENT, BenchAgent
from .engine import EngineError, create_game
from .limits import Limits

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "008-benchmark-format"
CONFIG = EXPERIMENT_ROOT / "config.json"
SCHEMA = "fallgorithm.experiment008.run/1"
SEED_LABEL = "fallgorithm008/bench/v1/{}"
LEVEL_MARKS = (29, 39)
# BetaTetris's published hybrid agent in the same format (betatetris-tablebase README).
REFERENCE = {
    "source": "betatetris-tablebase README, hybrid agent, 30 Hz / 300 ms, 1100 games",
    "mean_lines": 399.9, "median_lines": 419, "mean_score": 2426105,
    "median_score": 2459060, "p5_score": 1992180, "p10_score": 2057200,
    "p90_score": 2745740,
}


def _load(path: Path) -> Any:
    return experiment006._load(path)


def prior_seeds() -> list[int]:
    """Every seed used by Experiments 000-007 (configs, probes, development seeds)."""
    seeds: set[int] = set()
    for path in sorted((runner.PROJECT_ROOT / "experiments").glob("00[0-7]-*/**/*.json")):
        seeds |= experiment006._seeds_in(_load(path))
    seeds |= {1, 3, 5, 7, 9, 15, 17, 19, 21, 23, 41, 43, 45}
    seeds |= {experiment006._label_seed(experiment006.DEVELOPMENT_LABEL, i) for i in range(10)}
    return sorted(seed for seed in seeds if 0 <= seed <= 65535)


def select_seeds(count: int) -> dict[str, Any]:
    """Fresh seeds whose native start states differ from every earlier game."""
    game = _load(CONFIG)["game"]
    excluded = prior_seeds()
    seen = {experiment006.native_identity(game, seed) for seed in excluded}
    selected, index = [], 0
    while len(selected) < count:
        seed = experiment006._label_seed(SEED_LABEL, index)
        identity = experiment006.native_identity(game, seed)
        if identity not in seen:
            selected.append({"seed": seed, "candidate_index": index,
                             "initial_state_sha256": identity})
            seen.add(identity)
        index += 1
    return {
        "selection": ("SHA256(fallgorithm008/bench/v1/<index>), first two bytes big-endian; "
                      "skip any seed whose seed-erased native start state matches an earlier "
                      "experiment's or an already selected one; no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
        "selected": selected,
    }


def _stop_reason(state: Any, frames: int, config: dict[str, Any]) -> str | None:
    if state.terminal:
        return runner._terminal_reason(state)
    if state.lines >= config["line_cap"]:
        return "line_cap"
    if frames >= config["frame_cap"]:
        return "frame_limit"
    return None


def _result(state: Any, reason: str, marks: dict[int, int | None], game: Any) -> dict[str, Any]:
    return {
        "lines": state.lines, "score": state.score, "frames": state.frame,
        "stopping_reason": reason, "level": state.level,
        "level_29_score": marks[29], "level_39_score": marks[39],
        "final_state_hash": runner._hash(game),
    }


def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """One game: the agent picks a mask each frame until a stopping condition."""
    index, fmt, seed, config = job
    agent = BenchAgent(Limits(fmt["tap_hz"], fmt["reaction_ms"]))
    inputs = bytearray()
    marks: dict[int, int | None] = {level: None for level in LEVEL_MARKS}
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
        state = game.state
        while (reason := _stop_reason(state, len(inputs), config)) is None:
            mask = agent.act(state)
            state, _ = game.step(mask)
            inputs.append(mask)
            for level in LEVEL_MARKS:
                if marks[level] is None and state.level >= level:
                    marks[level] = state.score
        result = _result(state, reason, marks, game)
    result.update(pieces=agent.pieces, adjusts=agent.adjusts, switches=agent.switches)
    return {"format": index, "seed": seed, "initial_state_hash": initial_hash,
            "inputs": base64.b64encode(bytes(inputs)).decode("ascii"), "result": result}


def _jobs(config: dict[str, Any]) -> list[tuple[int, dict[str, Any], int, dict[str, Any]]]:
    return [(index, fmt, seed, config) for index, fmt in enumerate(config["formats"])
            for seed in config["seeds"]]


def _sources() -> dict[str, str]:
    package = Path(__file__).parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(package.glob("*.py"))}


def run(jobs: int) -> Path:
    config = _load(CONFIG)
    # Slowest games first (reaction searches cost the most) so the pool stays busy.
    ordered = sorted(_jobs(config), key=lambda job: -job[1]["reaction_ms"])
    done: list[dict[str, Any]] = []
    with Pool(jobs) as pool:
        for episode in pool.imap_unordered(_play, ordered):
            done.append(episode)
            print(f"{len(done)}/{len(ordered)} format {episode['format']} seed "
                  f"{episode['seed']}: {episode['result']['lines']} lines, "
                  f"{episode['result']['stopping_reason']}", file=sys.stderr, flush=True)
    order = {(index, seed): n for n, (index, _, seed, _) in enumerate(_jobs(config))}
    episodes = sorted(done, key=lambda e: order[(e["format"], e["seed"])])
    record = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config,
        "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": _sources(),
        "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-008"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def _replay(episode: dict[str, Any], config: dict[str, Any]) -> list[str]:
    where = f"format {episode['format']} seed {episode['seed']}"
    marks: dict[int, int | None] = {level: None for level in LEVEL_MARKS}
    inputs = base64.b64decode(episode["inputs"])
    with create_game(**config["game"], seed=episode["seed"]) as game:
        if runner._hash(game) != episode["initial_state_hash"]:
            return [f"{where}: initial state hash differs"]
        state = game.state
        for frame, action in enumerate(inputs):
            if _stop_reason(state, frame, config):
                return [f"{where}: game should have stopped before recorded frame {frame}"]
            state, _ = game.step(action)
            for level in LEVEL_MARKS:
                if marks[level] is None and state.level >= level:
                    marks[level] = state.score
        reason = _stop_reason(state, len(inputs), config)
        if reason is None:
            return [f"{where}: recorded inputs stop before any stopping condition"]
        replayed = _result(state, reason, marks, game)
    recorded = episode["result"]
    return [f"{where}: {field} recorded {recorded[field]!r}, replayed {value!r}"
            for field, value in replayed.items() if recorded[field] != value]


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 008 record"]
    config = record["configuration"]
    expected = [(index, seed) for index in range(len(config["formats"]))
                for seed in config["seeds"]]
    if [(e["format"], e["seed"]) for e in record["episodes"]] != expected:
        return ["episodes do not match the configured formats and seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(_replay, [(episode, config) for episode in record["episodes"]],
                             chunksize=1)
    return [problem for problems in found for problem in problems]


def _percentile(values: list[float], percent: float) -> float:
    """Linear-interpolation percentile (the same rule as numpy's default)."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _spread(values: list[int]) -> dict[str, float]:
    return {"mean": round(sum(values) / len(values), 1),
            "median": round(_percentile(values, 50), 1),
            "p5": round(_percentile(values, 5), 1),
            "p10": round(_percentile(values, 10), 1),
            "p90": round(_percentile(values, 90), 1)}


def _format_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    games = len(rows)

    def percent(count: int) -> float:
        return round(100 * count / games, 1)

    pieces = sum(row["pieces"] for row in rows)
    return {
        "games": games,
        "lines": _spread([row["lines"] for row in rows]),
        "score": _spread([row["score"] for row in rows]),
        "top_out_pct": percent(sum(row["stopping_reason"] == "game_over" for row in rows)),
        "reached_level_29_pct": percent(sum(row["level_29_score"] is not None for row in rows)),
        "reached_level_39_pct": percent(sum(row["level_39_score"] is not None for row in rows)),
        "reached_line_cap_pct": percent(sum(row["stopping_reason"] == "line_cap" for row in rows)),
        "frame_limit_stops": sum(row["stopping_reason"] == "frame_limit" for row in rows),
        "adjust_switch_pct": round(100 * sum(row["switches"] for row in rows) / pieces, 1),
    }


def summarize(path: Path) -> dict[str, Any]:
    record = _load(path)
    config = record["configuration"]
    rows = [{"format": e["format"], "seed": e["seed"], **e["result"]} for e in record["episodes"]]
    metrics = []
    for index, fmt in enumerate(config["formats"]):
        metrics.append({"format": fmt,
                        **_format_metrics([row for row in rows if row["format"] == index])})
    return {
        "experiment": "008-benchmark-format",
        "question": ("How strong is survival_plan's evaluation under human-like limits "
                     "(30 Hz or 15 Hz tapping, 0 or 300 ms reaction, level 39 double "
                     "killscreen, level 49 line cap), and how much did it depend on "
                     "instant reactions?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"],
        "engine_fingerprint": record["engine_fingerprint"],
        "configuration": {key: value for key, value in config.items() if key != "seeds"}
        | {"seed_count": len(config["seeds"])},
        "formats": metrics,
        "reference_betatetris_hybrid": REFERENCE,
        "episodes": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment008")
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select-seeds", help="print fresh native-state-disjoint seeds")
    select.add_argument("--count", type=int, default=300)
    run_parser = commands.add_parser("run", help="play the configured formats and seeds")
    run_parser.add_argument("--jobs", type=int, default=30)
    verify_parser = commands.add_parser("verify", help="replay a record on the native engine")
    verify_parser.add_argument("record", type=Path)
    verify_parser.add_argument("--jobs", type=int, default=30)
    summary_parser = commands.add_parser("summarize", help="write result.json from a record")
    summary_parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-seeds":
            print(json.dumps(select_seeds(args.count), indent=1))
        elif args.command == "run":
            path = run(args.jobs)
            for row in summarize(path)["formats"]:
                print(json.dumps(row))
            print(f"Record: {path}")
        elif args.command == "verify":
            problems = verify(args.record.resolve(), args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print(f"Verified: {args.record}")
        else:
            document = summarize(args.record.resolve())
            output = EXPERIMENT_ROOT / "result.json"
            output.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
            print(f"Wrote {output}")
    except (EngineError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
