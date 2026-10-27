"""Run, verify and summarise Experiment 006 (level-29 survival).

    python -m block_stack_ai.experiment006 select-seeds
    python -m block_stack_ai.experiment006 run [--jobs N]
    python -m block_stack_ai.experiment006 verify RECORD [--decisions]
    python -m block_stack_ai.experiment006 summarize RECORD

``run`` plays every (agent, seed) pair of the experiment's ``config.json`` in
parallel through the runner's own episode loop and writes one gzipped record
under ``runs/``. ``verify`` replays the recorded inputs on the native engine
and compares every outcome; ``--decisions`` also rebuilds the agents and checks
that they choose the same inputs again. ``summarize`` writes ``result.json``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, runner, searchplan, survivalplan
from .engine import EngineError, create_game

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "006-level29-survival"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS_FILE = EXPERIMENT_ROOT / "probes" / "seeds.json"
SCHEMA = "fallgorithm.experiment006.run/1"
AGENTS = {
    searchplan.SEARCH_AGENT: searchplan.SearchAgent,
    survivalplan.SURVIVAL_AGENT: survivalplan.SurvivalAgent,
}
SEED_COUNT = 30
SEED_LABEL = "fallgorithm006/holdout/v1/{}"
# Seeds the variant comparison was tuned on; probes/variants.py lists them too.
DEVELOPMENT_LABEL = "fallgorithm006/dev/{}"
RESULT_FIELDS = ("lines", "score", "frame_count", "stopping_reason", "final_state_hash")


def _load(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _label_seed(label: str, index: int) -> int:
    return int.from_bytes(hashlib.sha256(label.format(index).encode()).digest()[:2], "big")


def native_identity(game: dict[str, Any], seed: int) -> str:
    """Experiment 005's seed-erased native initial state identity."""
    with create_game(**game, seed=seed) as native:
        state = asdict(native.state)
    state.pop("seed")
    raw = json.dumps(state, sort_keys=True, separators=(",", ":"),
                     default=lambda value: value.tolist()).encode()
    return hashlib.sha256(raw).hexdigest()


def _seeds_in(value: Any) -> set[int]:
    if isinstance(value, dict):
        found = set()
        for key, child in value.items():
            if key == "seed" and type(child) is int:
                found.add(child)
            elif key == "seeds" and isinstance(child, list):
                found.update(seed for seed in child if type(seed) is int)
            else:
                found |= _seeds_in(child)
        return found
    if isinstance(value, list):
        return set().union(*(_seeds_in(child) for child in value)) if value else set()
    return set()


def prior_seeds() -> list[int]:
    """Every seed in an earlier experiment's JSON, plus the documented development seeds."""
    seeds: set[int] = set()
    for path in sorted((runner.PROJECT_ROOT / "experiments").glob("00[0-5]-*/**/*.json")):
        seeds |= _seeds_in(_load(path))
    seeds |= {1, 3, 5, 7, 9, 15, 17, 19, 21, 23, 41, 43, 45}
    seeds |= {_label_seed(DEVELOPMENT_LABEL, index) for index in range(10)}
    return sorted(seed for seed in seeds if 0 <= seed <= 65535)


def select_seeds() -> dict[str, Any]:
    """Pick fresh seeds whose native start states differ from every prior game."""
    game = _load(CONFIG)["game"]
    excluded = prior_seeds()
    seen = {native_identity(game, seed) for seed in excluded}
    selected = []
    index = 0
    while len(selected) < SEED_COUNT:
        seed = _label_seed(SEED_LABEL, index)
        identity = native_identity(game, seed)
        if identity not in seen:
            selected.append({"seed": seed, "candidate_index": index,
                             "initial_state_sha256": identity})
            seen.add(identity)
        index += 1
    return {
        "selection": ("SHA256(fallgorithm006/holdout/v1/<index>), first two bytes big-endian; "
                      "skip any seed whose seed-erased native start state matches an excluded "
                      "or already selected one; no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
        "selected": selected,
    }


def _play(job: tuple[str, int, dict[str, Any], int]) -> dict[str, Any]:
    agent, seed, game, frame_limit = job
    episode = runner._play(dict(game, seed=seed), frame_limit, AGENTS[agent](), create_game)
    return {"agent": agent, "seed": seed, **runner._persisted(episode)}


def _jobs(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any], int]]:
    return [(agent, seed, config["game"], config["frame_limit"])
            for agent in config["agents"] for seed in config["seeds"]]


def _sources() -> dict[str, str]:
    package = Path(__file__).parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(package.glob("*.py"))}


def run(jobs: int) -> Path:
    config = _load(CONFIG)
    with Pool(jobs) as pool:
        episodes = pool.map(_play, _jobs(config))
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
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-006"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def _replay(episode: dict[str, Any], game: dict[str, Any]) -> list[str]:
    where = f"{episode['agent']} seed {episode['seed']}"
    with create_game(**game, seed=episode["seed"]) as native:
        if runner._hash(native) != episode["initial_state_hash"]:
            return [f"{where}: initial state hash differs"]
        state = native.state
        for frame, action in enumerate(episode["inputs"]):
            if state.terminal:
                return [f"{where}: game ended before recorded frame {frame}"]
            state, _ = native.step(action)
        replayed = {
            "lines": state.lines, "score": state.score, "frame_count": state.frame,
            "stopping_reason": runner._terminal_reason(state) or "frame_limit",
            "final_state_hash": runner._hash(native),
        }
    return [f"{where}: {field} recorded {episode['result'][field]!r}, replayed {replayed[field]!r}"
            for field in RESULT_FIELDS if episode["result"][field] != replayed[field]]


def verify(path: Path, *, decisions: bool, jobs: int) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 006 record"]
    config = record["configuration"]
    expected = [(agent, seed) for agent in config["agents"] for seed in config["seeds"]]
    if [(e["agent"], e["seed"]) for e in record["episodes"]] != expected:
        return ["episodes do not match the configured agents and seeds"]
    problems = []
    for episode in record["episodes"]:
        problems += _replay(episode, config["game"])
    if decisions:
        with Pool(jobs) as pool:
            for recorded, fresh in zip(record["episodes"], pool.map(_play, _jobs(config))):
                if recorded != fresh:
                    problems.append(f"{recorded['agent']} seed {recorded['seed']}: "
                                    "a fresh agent chose different inputs or outcomes")
    return problems


def changed_sources(path: Path) -> list[str]:
    """Package modules whose bytes differ from the ones the record was made with."""
    recorded, current = _load(path)["sources"], _sources()
    return sorted(name for name in set(recorded) | set(current)
                  if recorded.get(name) != current.get(name))


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [row["lines"] for row in rows]
    tetrises = sum(row["clear_sizes"]["tetrises"] for row in rows)
    return {
        "games": len(rows),
        "top_outs": sum(row["stopping_reason"] == "game_over" for row in rows),
        "frame_limit_stops": sum(row["stopping_reason"] == "frame_limit" for row in rows),
        "mean_lines": round(sum(lines) / len(rows), 1),
        "min_lines": min(lines),
        "mean_score": round(sum(row["score"] for row in rows) / len(rows), 1),
        "tetris_line_rate": round(4 * tetrises / sum(lines), 6) if sum(lines) else 0.0,
        "mean_pieces": round(sum(row["pieces_placed"] for row in rows) / len(rows), 1),
    }


def summarize(path: Path) -> dict[str, Any]:
    record = _load(path)
    config = record["configuration"]
    rows = [{"agent": e["agent"], "seed": e["seed"], "pieces_placed": e["pieces_placed"],
             "clear_sizes": e["clear_sizes"], **{f: e["result"][f] for f in RESULT_FIELDS}}
            for e in record["episodes"]]
    metrics = {agent: _metrics([row for row in rows if row["agent"] == agent])
               for agent in config["agents"]}
    baseline, survival = metrics[searchplan.SEARCH_AGENT], metrics[survivalplan.SURVIVAL_AGENT]
    by_seed = {(row["agent"], row["seed"]): row for row in rows}
    paired = [by_seed[(survivalplan.SURVIVAL_AGENT, seed)]["lines"]
              - by_seed[(searchplan.SEARCH_AGENT, seed)]["lines"] for seed in config["seeds"]]
    return {
        "experiment": "006-level29-survival",
        "question": ("Does lowering the well plan's height budget from 8 to 5 at level 28 "
                     "reduce top-outs without lowering mean lines?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"],
        "engine_fingerprint": record["engine_fingerprint"],
        "configuration": config,
        "metrics": metrics,
        "paired_lines": {"survival_more": sum(d > 0 for d in paired),
                         "search_more": sum(d < 0 for d in paired),
                         "equal": sum(d == 0 for d in paired)},
        "acceptance": {
            "primary_fewer_top_outs": survival["top_outs"] < baseline["top_outs"],
            "secondary_mean_lines_not_lower": survival["mean_lines"] >= baseline["mean_lines"],
        },
        "episodes": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment006")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("select-seeds", help="print fresh native-state-disjoint seeds")
    run_parser = commands.add_parser("run", help="play the configured agents and seeds")
    run_parser.add_argument("--jobs", type=int, default=30)
    verify_parser = commands.add_parser("verify", help="replay a record on the native engine")
    verify_parser.add_argument("record", type=Path)
    verify_parser.add_argument("--decisions", action="store_true",
                               help="also re-run the agents and compare their inputs")
    verify_parser.add_argument("--jobs", type=int, default=30)
    summary_parser = commands.add_parser("summarize", help="write result.json from a record")
    summary_parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-seeds":
            print(json.dumps(select_seeds(), indent=1))
        elif args.command == "run":
            path = run(args.jobs)
            for agent, values in summarize(path)["metrics"].items():
                print(agent, json.dumps(values))
            print(f"Record: {path}")
        elif args.command == "verify":
            problems = verify(args.record.resolve(), decisions=args.decisions, jobs=args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            changed = changed_sources(args.record.resolve())
            if changed:
                print(f"Note: package sources changed since the run: {', '.join(changed)}")
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
