"""Train, run, verify and summarise Experiment 012 (a full CEM run on the native reach_plan).

    python -m block_stack_ai.experiment012 select-seeds
    python -m block_stack_ai.experiment012 train [--jobs N]
    python -m block_stack_ai.experiment012 evaluate [--jobs N]
    python -m block_stack_ai.experiment012 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment012 summarize RECORD [--jobs N]

Experiment 009's CEM (``experiment009.sample`` and ``cem_update``), started from 009's
final numbers, with the games played by Experiment 011's C++ ``reach_plan``. Training
games call ``native.play_game`` only (score and lines are all CEM needs); held-out games
go through ``experiment011.play_native``, which replays each one on the Python engine
binding. ``train`` saves ``training.json`` after every iteration and can resume.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment006, experiment008 as e8, experiment009 as e9
from . import experiment011 as e11, experiment005, native, runner
from .engine import EngineError
from .limits import Limits
from .tunedplan import resolve

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "012-native-cem"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
TRAINING = EXPERIMENT_ROOT / "training.json"
FINAL_PARAMS = EXPERIMENT_ROOT / "final_params.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
START_PARAMS = e9.FINAL_PARAMS  # Experiment 009's learned numbers: the CEM's starting mean
BASELINE_008_RECORD = e11.HELDOUT  # 011's retained run of 009's numbers on 008's seeds
SCHEMA = "fallgorithm.experiment012.run/1"
TRAIN_LABEL = "fallgorithm012/train/v1/{}"
HELDOUT_LABEL = "fallgorithm012/heldout/v1/{}"
PROFILING_SEEDS = {12345}  # used to profile in Experiment 011's plan
BOOTSTRAP_SEED = 12


def _load(path: Path) -> Any:
    return experiment006._load(path)


def _write(path: Path, value: Any) -> None:
    e9._write(path, value)


# ---------------------------------------------------------------- seeds

def excluded_seeds() -> list[int]:
    """Every seed used by Experiments 000-011, plus 011's profiling seed."""
    seeds = set(e9.excluded_seeds()) | PROFILING_SEEDS | set(_load(e9.SEEDS)["train_seeds"])
    for prefix in ("008", "009", "010", "011"):
        for suffix in ("json", "json.gz"):
            for path in sorted((runner.PROJECT_ROOT / "experiments").glob(f"{prefix}-*/**/*.{suffix}")):
                seeds |= experiment006._seeds_in(_load(path))
    return sorted(seed for seed in seeds if 0 <= seed <= 65535)


def select_seeds(train_count: int = 96, heldout_count: int = 1000) -> dict[str, Any]:
    """Fresh training then held-out seeds; no seed, or native start-state twin, used twice."""
    game = _load(CONFIG)["game"]
    excluded = excluded_seeds()
    seen = {experiment006.native_identity(game, seed) for seed in excluded}
    document: dict[str, Any] = {
        "selection": ("SHA256(<label with index>), first two bytes big-endian; skip any seed "
                      "used by Experiments 000-011 (their JSON and gzipped records, 009's "
                      "training seeds, and 12345, 011's profiling seed) and any seed whose seed-erased native start "
                      "state matches an excluded or already selected one; training seeds are "
                      "selected first; no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
    }
    for name, label, count in (("train", TRAIN_LABEL, train_count),
                               ("heldout", HELDOUT_LABEL, heldout_count)):
        selected, index = [], 0
        while len(selected) < count:
            seed = experiment006._label_seed(label, index)
            identity = experiment006.native_identity(game, seed)
            if identity not in seen:
                selected.append({"seed": seed, "candidate_index": index})
                seen.add(identity)
            index += 1
        document[f"{name}_label"] = label.replace("{}", "<index>")
        document[f"{name}_selected"] = selected
        document[f"{name}_seeds"] = [item["seed"] for item in selected]
    return document


# ---------------------------------------------------------------- CEM

def start_mean() -> list[float]:
    """Experiment 009's final numbers, resolved, in ``experiment009.NAMES`` order."""
    resolved = _load(START_PARAMS)["resolved"]
    return [float(resolved[name]) for name in e9.NAMES]


def _fitness_game(job: tuple[int, int, dict[str, Any], dict[str, float]]) -> tuple[int, int, int]:
    """Training worker: ``(candidate, score, lines)`` for one candidate on one seed."""
    candidate, seed, config, params = job
    fmt = config["formats"][0]
    played = native.play_game(config["game"], seed, line_cap=config["line_cap"],
                              frame_cap=config["frame_cap"],
                              limits=Limits(fmt["tap_hz"], fmt["reaction_ms"]),
                              params=native.params(params))
    return candidate, played["score"], played["lines"]


def _score_on(pool: Any, config: dict[str, Any], seeds: list[int],
              params: dict[str, float]) -> dict[str, float]:
    games = pool.map(_fitness_game, [(0, seed, config, params) for seed in seeds], chunksize=1)
    return {"mean_score": e9._mean([g[1] for g in games]),
            "mean_lines": e9._mean([g[2] for g in games])}


def train(jobs: int) -> None:
    config = _load(CONFIG)
    seeds = _load(SEEDS)["train_seeds"]
    settings = config["train"]
    population, elite, iterations = settings["population"], settings["elite"], settings["iterations"]
    rng = random.Random(settings["rng_seed"])
    mean, spread = start_mean(), e9.initial_spread()
    floor = [settings["spread_floor"] * s for s in spread]
    state = _load(TRAINING) if TRAINING.exists() else {
        "settings": settings, "initial_mean": e9.as_params(mean),
        "initial_spread": e9.as_params(spread), "spread_floor": e9.as_params(floor),
        "train_seeds": seeds, "iterations": []}
    if (state["settings"], state["train_seeds"]) != (settings, seeds):
        raise ValueError(f"{TRAINING} was made with other settings or seeds; move it away first")
    started = time.time()
    with Pool(jobs) as pool:
        if "baseline_009_params" not in state:
            state["baseline_009_params"] = _score_on(pool, config, seeds, e9.as_params(mean))
            _write(TRAINING, state)
            print(f"009's numbers on training seeds: {state['baseline_009_params']}",
                  file=sys.stderr, flush=True)
        for done in state["iterations"]:  # resume: replay the draws and take the saved guess
            e9.sample(mean, spread, rng, population)
            mean, spread = list(done["mean_params"].values()), list(done["spread"].values())
        for iteration in range(len(state["iterations"]), iterations):
            tick = time.time()
            samples = e9.sample(mean, spread, rng, population)
            work = [(c, seed, config, e9.as_params(vector))
                    for c, vector in enumerate(samples) for seed in seeds]
            scores: list[list[int]] = [[] for _ in samples]
            for candidate, score, _ in pool.imap_unordered(_fitness_game, work, chunksize=4):
                scores[candidate].append(score)
            fitness = [e9._mean(s) for s in scores]
            mean, spread = e9.cem_update(samples, fitness, elite, floor)
            ranked = sorted(range(population), key=lambda i: (-fitness[i], i))
            best = ranked[0]
            state["iterations"].append({
                "iteration": iteration, "best": fitness[best],
                "elite_mean": e9._mean([fitness[i] for i in ranked[:elite]]),
                "population_mean": e9._mean(fitness), "best_params": e9.as_params(samples[best]),
                "mean_params": e9.as_params(mean), "spread": e9.as_params(spread),
                "wall_seconds": round(time.time() - tick, 1)})
            _write(TRAINING, state)
            print(f"iteration {iteration}: best {fitness[best]:.0f} elite "
                  f"{state['iterations'][-1]['elite_mean']:.0f} population "
                  f"{e9._mean(fitness):.0f} ({time.time() - tick:.0f}s)", file=sys.stderr,
                  flush=True)
        state["final_mean_fitness"] = _score_on(pool, config, seeds, e9.as_params(mean))
    state["total_wall_seconds"] = round(sum(i["wall_seconds"] for i in state["iterations"]), 1)
    _write(TRAINING, state)
    _write(FINAL_PARAMS, {"params": e9.as_params(mean), "resolved": resolve(e9.as_params(mean))})
    print(f"Wrote {FINAL_PARAMS} after {time.time() - started:.0f}s", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- evaluate / verify

# (agent, seed set) pairs played by ``evaluate``, in record order
RUNS = (("cem", "heldout"), ("baseline", "heldout"), ("cem", "008"))


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "agent", "formats")} | {
        "params": {"cem": _load(FINAL_PARAMS)["resolved"],
                   "baseline": _load(START_PARAMS)["resolved"]},
        "seeds": {"heldout": _load(SEEDS)["heldout_seeds"], "008": _load(e8.CONFIG)["seeds"]},
        "runs": [list(run) for run in RUNS]}


def _play(job: tuple[str, str, int, dict[str, Any]]) -> dict[str, Any]:
    agent, seeds, seed, config = job
    episode = e11.play_native((0, config["formats"][0], seed, config | {
        "params": config["params"][agent]}))
    return {"agent": agent, "seeds": seeds} | episode


def _work(config: dict[str, Any]) -> list[tuple[str, str, int, dict[str, Any]]]:
    return [(agent, seeds, seed, config) for agent, seeds in config["runs"]
            for seed in config["seeds"][seeds]]


def evaluate(jobs: int) -> Path:
    iterations = _load(CONFIG)["train"]["iterations"]
    if not PREDECLARED.exists() or len(_load(TRAINING)["iterations"]) < iterations:
        raise ValueError("held-out games wait for predeclared.md and the finished training")
    config = record_configuration()
    tick = time.perf_counter()
    with Pool(jobs) as pool:
        episodes = pool.map(_play, _work(config), chunksize=4)
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e11.sources(), "workers": jobs,
        "wall_seconds": round(time.perf_counter() - tick, 1), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-012"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 012 record"]
    config = record["configuration"]
    expected = [(agent, seeds, seed) for agent, seeds, seed, _ in _work(config)]
    if [(e["agent"], e["seeds"], e["seed"]) for e in record["episodes"]] != expected:
        return ["episodes do not match the configured runs and seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(e9._replay, [(e, config) for e in record["episodes"]], chunksize=4)
    return [problem for problems in found for problem in problems]


# ---------------------------------------------------------------- summarize

def _rows(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"seed": e["seed"], **e["result"]} for e in episodes]


def paired(rows: list[dict[str, Any]], base_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Paired score and lines differences (rows minus base rows) on the same seeds."""
    by_seed = {row["seed"]: row for row in base_rows}
    if [row["seed"] for row in rows] != [row["seed"] for row in base_rows]:
        raise ValueError("the two runs are not on the same seeds in the same order")
    differences = {name: [row[name] - by_seed[row["seed"]][name] for row in rows]
                   for name in ("score", "lines")}
    return {"score": e9.bootstrap_mean_ci(differences["score"], seed=BOOTSTRAP_SEED),
            "lines": e9.bootstrap_mean_ci(differences["lines"], seed=BOOTSTRAP_SEED),
            "wins": {"higher": sum(d > 0 for d in differences["score"]),
                     "lower": sum(d < 0 for d in differences["score"]),
                     "equal": sum(d == 0 for d in differences["score"])}}


def success(score_ci: dict[str, float]) -> bool:
    """The predeclared rule: the paired mean-score difference's 95% interval is wholly above 0."""
    return score_ci["ci95_low"] > 0


def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    problems = verify(path, jobs)
    if problems:
        raise ValueError(f"{path} does not verify: {problems[:3]}")
    record = _load(path)
    params = record["configuration"]["params"]
    if params["cem"] != _load(FINAL_PARAMS)["resolved"]:
        raise ValueError("the record's cem numbers are not final_params.json's")
    if _load(BASELINE_008_RECORD)["configuration"]["params"] != params["baseline"]:
        raise ValueError("Experiment 011's record did not play the baseline numbers")
    runs = {(agent, seeds): _rows([e for e in record["episodes"]
                                   if (e["agent"], e["seeds"]) == (agent, seeds)])
            for agent, seeds in RUNS}
    cem, baseline = runs["cem", "heldout"], runs["baseline", "heldout"]
    base_008 = _rows(_load(BASELINE_008_RECORD)["episodes"])
    main_pair = paired(cem, baseline)
    training = _load(TRAINING)
    return {
        "experiment": "012-native-cem",
        "question": ("Does a full CEM run on the native reach_plan beat Experiment 009's numbers "
                     "on fresh held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "params": record["configuration"]["params"],
        "heldout": {"games": len(cem), "cem": e9.metrics(cem), "baseline": e9.metrics(baseline),
                    "paired_cem_minus_baseline": main_pair},
        "seeds_008": {"games": len(runs["cem", "008"]), "cem": e9.metrics(runs["cem", "008"]),
                      "baseline_011_record": e9.metrics(base_008),
                      "paired_cem_minus_baseline": paired(runs["cem", "008"], base_008)},
        "training": {"curve": [{key: item[key] for key in
                                ("iteration", "best", "elite_mean", "population_mean")}
                               for item in training["iterations"]],
                     "baseline_009_params": training["baseline_009_params"],
                     "final_mean": training["final_mean_fitness"],
                     "total_wall_seconds": training["total_wall_seconds"]},
        "success_rule": ("95% CI of the paired mean score difference (cem minus baseline) on the "
                         "1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment012")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("select-seeds", help="write seeds.json with fresh training and held-out seeds")
    for name, text in (("train", "run CEM on the training seeds"),
                       ("evaluate", "play the final and baseline numbers on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-seeds":
            document = select_seeds()
            _write(SEEDS, document)
            print(f"Wrote {SEEDS}: {len(document['train_seeds'])} training, "
                  f"{len(document['heldout_seeds'])} held-out seeds")
        elif args.command == "train":
            train(args.jobs)
        elif args.command == "evaluate":
            print(f"Record: {evaluate(args.jobs)}")
        elif args.command == "verify":
            problems = verify(args.record.resolve(), args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print(f"Verified: {args.record}")
        else:
            _write(RESULT, summarize(args.record.resolve(), args.jobs))
            print(f"Wrote {RESULT}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
