"""Train, run, verify and summarise Experiment 009 (CEM-learned evaluation for bench_plan).

    python -m block_stack_ai.experiment009 select-seeds
    python -m block_stack_ai.experiment009 train [--jobs N]
    python -m block_stack_ai.experiment009 evaluate [--jobs N]
    python -m block_stack_ai.experiment009 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment009 summarize RECORD [--jobs N]

The cross-entropy method (CEM) in short: keep a Gaussian guess (a mean and a spread
for each parameter). Each iteration, draw a population of parameter sets from it, play
every one on the training seeds, keep the best few (the elite), and make the next
guess the elite's mean and spread. The guess narrows toward what worked. The mean
starts at ``bench_plan``'s hand-picked numbers, so training starts from a good player.

``train`` is resumable: it saves ``training.json`` after every iteration. ``evaluate``
plays the final mean on Experiment 008's 300 held-out seeds at 30 Hz / 300 ms and
writes a gzipped record in the shape of 008's (one format) plus per-game clear sizes.
Games use :class:`block_stack_ai.tunedplan.TunedAgent` and 008's own stopping rules.
"""

from __future__ import annotations

import argparse
import base64
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

from . import experiment005, experiment006, experiment008 as e8, runner
from .benchplan import BenchAgent
from .engine import EngineError, create_game
from .limits import Limits
from .tunedplan import DEFAULTS, TunedAgent, resolve

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "009-cem-score"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
TRAINING = EXPERIMENT_ROOT / "training.json"
FINAL_PARAMS = EXPERIMENT_ROOT / "final_params.json"
RESULT = EXPERIMENT_ROOT / "result.json"
BASELINE_RECORD = e8.EXPERIMENT_ROOT / "records" / "run.json.gz"
SCHEMA = "fallgorithm.experiment009.run/1"
SEED_LABEL = "fallgorithm009/train/v1/{}"
NAMES = list(DEFAULTS)
CLEAR_NAMES = {1: "singles", 2: "doubles", 3: "triples", 4: "tetrises"}
BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED = 10_000, 9


def _load(path: Path) -> Any:
    return experiment006._load(path)


def _write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8")
    temporary.replace(path)


# ---------------------------------------------------------------- seeds

def excluded_seeds() -> list[int]:
    """Every seed used by Experiments 000-008 (008's 300 held-out seeds included)."""
    seeds = set(e8.prior_seeds())
    for path in sorted((runner.PROJECT_ROOT / "experiments").glob("008-*/**/*.json")):
        seeds |= experiment006._seeds_in(_load(path))
    return sorted(seed for seed in seeds if 0 <= seed <= 65535)


def select_seeds(count: int = 24) -> dict[str, Any]:
    """Fresh training seeds, not used by 000-008 and not native-state twins of any of them."""
    game = _load(CONFIG)["game"]
    excluded = excluded_seeds()
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
        "selection": ("SHA256(fallgorithm009/train/v1/<index>), first two bytes big-endian; "
                      "skip any seed used by Experiments 000-008 and any seed whose seed-erased "
                      "native start state matches an earlier experiment's or an already "
                      "selected one; no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
        "selected": selected,
        "train_seeds": [item["seed"] for item in selected],
    }


# ---------------------------------------------------------------- playing

def _agent(fmt: dict[str, Any], params: dict[str, float] | None) -> Any:
    limits = Limits(fmt["tap_hz"], fmt["reaction_ms"])
    return BenchAgent(limits) if params is None else TunedAgent(limits, params)


def _tally(state: Any, before: int, sizes: dict[str, int], marks: dict[int, int | None]) -> None:
    """After one step: count a line clear by its size and mark the first frame at each level."""
    if state.lines > before:
        sizes[CLEAR_NAMES[state.lines - before]] += 1
    for level in e8.LEVEL_MARKS:
        if marks[level] is None and state.level >= level:
            marks[level] = state.score


def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """One game, like 008's, with ``config["params"]`` (``None`` means plain bench_plan)."""
    index, fmt, seed, config = job
    agent = _agent(fmt, config.get("params"))
    inputs = bytearray()
    marks: dict[int, int | None] = {level: None for level in e8.LEVEL_MARKS}
    sizes = dict.fromkeys(CLEAR_NAMES.values(), 0)
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
        state = game.state
        while (reason := e8._stop_reason(state, len(inputs), config)) is None:
            mask = agent.act(state)
            before = state.lines
            state, _ = game.step(mask)
            inputs.append(mask)
            _tally(state, before, sizes, marks)
        result = e8._result(state, reason, marks, game)
    result.update(pieces=agent.pieces, adjusts=agent.adjusts, switches=agent.switches,
                  clear_sizes=sizes)
    return {"format": index, "seed": seed, "initial_state_hash": initial_hash,
            "inputs": base64.b64encode(bytes(inputs)).decode("ascii"), "result": result}


def _fitness_game(job: tuple[int, int, dict[str, Any], dict[str, Any]]) -> tuple[int, int, int]:
    """Training worker: ``(candidate, score, lines)`` for one candidate on one seed."""
    candidate, seed, config, params = job
    episode = _play((0, config["formats"][0], seed, dict(config, params=params)))
    return candidate, episode["result"]["score"], episode["result"]["lines"]


# ---------------------------------------------------------------- CEM

def initial_mean() -> list[float]:
    return [float(DEFAULTS[name]) for name in NAMES]


def initial_spread() -> list[float]:
    """About half of each weight's size; 1.0 for the zero-start features; 2 for whole numbers."""
    spread = []
    for name in NAMES:
        if name in ("height_budget", "survival_budget", "survival_level", "drought_bound"):
            spread.append(2.0)
        else:
            spread.append(0.5 * abs(DEFAULTS[name]) or 1.0)
    return spread


def sample(mean: list[float], spread: list[float], rng: random.Random,
           count: int) -> list[list[float]]:
    """Draw ``count`` parameter vectors, one Gaussian per parameter."""
    return [[rng.gauss(m, s) for m, s in zip(mean, spread)] for _ in range(count)]


def cem_update(samples: list[list[float]], fitness: list[float], elite: int,
               floor: list[float]) -> tuple[list[float], list[float]]:
    """New (mean, spread): the elite samples' mean and standard deviation, spread kept >= floor.

    The elite are the ``elite`` highest-fitness samples (ties keep the earlier sample).
    """
    order = sorted(range(len(samples)), key=lambda i: (-fitness[i], i))[:elite]
    chosen = [samples[i] for i in order]
    mean, spread = [], []
    for dimension in range(len(chosen[0])):
        values = [vector[dimension] for vector in chosen]
        centre = sum(values) / len(values)
        deviation = (sum((v - centre) ** 2 for v in values) / len(values)) ** 0.5
        mean.append(centre)
        spread.append(max(deviation, floor[dimension]))
    return mean, spread


def as_params(vector: list[float]) -> dict[str, float]:
    return dict(zip(NAMES, vector))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def train(jobs: int) -> None:
    config = _load(CONFIG)
    seeds = _load(SEEDS)["train_seeds"]
    settings = config["train"]
    population, elite, iterations = settings["population"], settings["elite"], settings["iterations"]
    rng = random.Random(settings["rng_seed"])
    mean, spread = initial_mean(), initial_spread()
    floor = [settings["spread_floor"] * s for s in spread]
    state = _load(TRAINING) if TRAINING.exists() else {
        "settings": settings, "initial_mean": as_params(mean), "initial_spread": as_params(spread),
        "spread_floor": as_params(floor), "train_seeds": seeds, "iterations": []}
    started = time.time()
    with Pool(jobs) as pool:
        if "baseline_bench_plan" not in state:
            games = pool.map(_fitness_game, [(0, seed, config, None) for seed in seeds],
                             chunksize=1)
            state["baseline_bench_plan"] = {"mean_score": _mean([g[1] for g in games]),
                                            "mean_lines": _mean([g[2] for g in games])}
            _write(TRAINING, state)
            print(f"bench_plan on training seeds: {state['baseline_bench_plan']}",
                  file=sys.stderr, flush=True)
        for done in state["iterations"]:  # resume: replay the draws and take the saved guess
            sample(mean, spread, rng, population)
            mean, spread = list(done["mean_params"].values()), list(done["spread"].values())
        for iteration in range(len(state["iterations"]), iterations):
            tick = time.time()
            samples = sample(mean, spread, rng, population)
            work = [(c, seed, config, as_params(vector))
                    for c, vector in enumerate(samples) for seed in seeds]
            scores: list[list[int]] = [[] for _ in samples]
            for candidate, score, _ in pool.imap_unordered(_fitness_game, work, chunksize=1):
                scores[candidate].append(score)
            fitness = [_mean(s) for s in scores]
            mean, spread = cem_update(samples, fitness, elite, floor)
            ranked = sorted(range(population), key=lambda i: (-fitness[i], i))
            best = ranked[0]
            state["iterations"].append({
                "iteration": iteration, "best": fitness[best],
                "elite_mean": _mean([fitness[i] for i in ranked[:elite]]),
                "population_mean": _mean(fitness), "best_params": as_params(samples[best]),
                "mean_params": as_params(mean), "spread": as_params(spread),
                "wall_seconds": round(time.time() - tick, 1)})
            _write(TRAINING, state)
            print(f"iteration {iteration}: best {fitness[best]:.0f} elite "
                  f"{state['iterations'][-1]['elite_mean']:.0f} population "
                  f"{_mean(fitness):.0f} ({time.time() - tick:.0f}s)", file=sys.stderr, flush=True)
        games = pool.map(_fitness_game, [(0, seed, config, as_params(mean)) for seed in seeds],
                         chunksize=1)
        state["final_mean_fitness"] = {"mean_score": _mean([g[1] for g in games]),
                                       "mean_lines": _mean([g[2] for g in games])}
    state["total_wall_seconds"] = round(sum(i["wall_seconds"] for i in state["iterations"]), 1)
    _write(TRAINING, state)
    _write(FINAL_PARAMS, {"params": as_params(mean), "resolved": resolve(as_params(mean))})
    print(f"Wrote {FINAL_PARAMS} after {time.time() - started:.0f}s", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- evaluate / verify

def heldout_seeds() -> list[int]:
    return _load(e8.CONFIG)["seeds"]


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "agent", "formats")} | {
        "params": _load(FINAL_PARAMS)["resolved"], "seeds": heldout_seeds()}


def evaluate(jobs: int) -> Path:
    config = record_configuration()
    work = [(0, config["formats"][0], seed, config) for seed in config["seeds"]]
    with Pool(jobs) as pool:
        episodes = []
        for episode in pool.imap(_play, work, chunksize=1):
            episodes.append(episode)
            result = episode["result"]
            print(f"{len(episodes)}/{len(work)} seed {episode['seed']}: {result['lines']} lines, "
                  f"score {result['score']}, {result['stopping_reason']}", file=sys.stderr,
                  flush=True)
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e8._sources(), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-009"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def replay_outcome(episode: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Replay recorded inputs: ``(result fields, problem)``; the problem is a string or ``None``."""
    marks: dict[int, int | None] = {level: None for level in e8.LEVEL_MARKS}
    sizes = dict.fromkeys(CLEAR_NAMES.values(), 0)
    inputs = base64.b64decode(episode["inputs"])
    with create_game(**config["game"], seed=episode["seed"]) as game:
        if runner._hash(game) != episode["initial_state_hash"]:
            return {}, "initial state hash differs"
        state = game.state
        for frame, action in enumerate(inputs):
            if e8._stop_reason(state, frame, config):
                return {}, f"game should have stopped before recorded frame {frame}"
            before = state.lines
            state, _ = game.step(action)
            _tally(state, before, sizes, marks)
        reason = e8._stop_reason(state, len(inputs), config)
        if reason is None:
            return {}, "recorded inputs stop before any stopping condition"
        return e8._result(state, reason, marks, game) | {"clear_sizes": sizes}, None


def _replay(episode: dict[str, Any], config: dict[str, Any]) -> list[str]:
    where = f"seed {episode['seed']}"
    replayed, problem = replay_outcome(episode, config)
    if problem:
        return [f"{where}: {problem}"]
    recorded = episode["result"]
    return [f"{where}: {field} recorded {recorded[field]!r}, replayed {value!r}"
            for field, value in replayed.items() if recorded[field] != value]


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 009 record"]
    config = record["configuration"]
    if [e["seed"] for e in record["episodes"]] != config["seeds"]:
        return ["episodes do not match the configured seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(_replay, [(e, config) for e in record["episodes"]], chunksize=1)
    return [problem for problems in found for problem in problems]


# ---------------------------------------------------------------- summarize

def bootstrap_mean_ci(differences: list[float], resamples: int = BOOTSTRAP_RESAMPLES,
                      seed: int = BOOTSTRAP_SEED) -> dict[str, float]:
    """Mean of the paired differences with a percentile bootstrap 95% interval."""
    rng = random.Random(seed)
    count = len(differences)
    means = sorted(sum(rng.choices(differences, k=count)) / count for _ in range(resamples))
    return {"mean": sum(differences) / count,
            "ci95_low": means[int(0.025 * resamples)],
            "ci95_high": means[int(0.975 * resamples) - 1],
            "resamples": resamples, "rng_seed": seed}


def tetris_rate(rows: list[dict[str, Any]]) -> float:
    """Lines cleared as Tetrises over all lines cleared."""
    lines = sum(row["lines"] for row in rows)
    return round(4 * sum(row["clear_sizes"]["tetrises"] for row in rows) / lines, 4) if lines else 0.0


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """008's per-format statistics plus the clear-size totals and the Tetris rate."""
    totals = {name: sum(row["clear_sizes"][name] for row in rows) for name in CLEAR_NAMES.values()}
    return e8._format_metrics(rows) | {"clear_sizes": totals, "tetris_rate": tetris_rate(rows)}


def success(ci: dict[str, float]) -> bool:
    """The predeclared rule: the paired mean-score difference's 95% interval is wholly above 0."""
    return ci["ci95_low"] > 0


def _baseline_row(episode: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """An 008 game as a row, with clear sizes recovered by replaying its inputs."""
    replayed, problem = replay_outcome(episode, config)
    if problem:
        raise ValueError(f"008 seed {episode['seed']}: {problem}")
    return {"seed": episode["seed"], **episode["result"], "clear_sizes": replayed["clear_sizes"]}


def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    record = _load(path)
    config = record["configuration"]
    rows = [{"seed": e["seed"], **e["result"]} for e in record["episodes"]]
    base = _load(BASELINE_RECORD)
    base_config = base["configuration"]
    index = [f"{f['tap_hz']:g}hz-{f['reaction_ms']:g}ms" for f in base_config["formats"]].index("30hz-300ms")
    base_episodes = [e for e in base["episodes"] if e["format"] == index]
    with Pool(jobs) as pool:
        base_rows = pool.starmap(_baseline_row, [(e, base_config) for e in base_episodes],
                                 chunksize=1)
    by_seed = {row["seed"]: row for row in base_rows}
    seeds = [row["seed"] for row in rows]
    if set(seeds) != set(by_seed):
        raise ValueError("009 and 008 games are not on the same seeds")
    paired = {name: [row[name] - by_seed[row["seed"]][name] for row in rows]
              for name in ("score", "lines")}
    ci = bootstrap_mean_ci(paired["score"])
    training = _load(TRAINING) if TRAINING.exists() else None
    return {
        "experiment": "009-cem-score",
        "question": ("Can CEM-learned evaluation parameters raise bench_plan's mean score at "
                     "30 Hz / 300 ms on held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "params": config["params"],
        "tuned_plan": metrics(rows), "bench_plan_008": metrics(base_rows),
        "paired_score_difference": ci,
        "paired_lines_difference": bootstrap_mean_ci(paired["lines"]),
        "paired_score_wins": {"tuned_higher": sum(d > 0 for d in paired["score"]),
                              "bench_higher": sum(d < 0 for d in paired["score"]),
                              "equal": sum(d == 0 for d in paired["score"])},
        "success_rule": "95% CI of the paired mean score difference entirely above 0",
        "success": success(ci),
        "training_baseline": None if training is None else training.get("baseline_bench_plan"),
        "episodes": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment009")
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select-seeds", help="write seeds.json with fresh training seeds")
    select.add_argument("--count", type=int, default=24)
    for name, text in (("train", "run CEM on the training seeds"),
                       ("evaluate", "play the final mean on the held-out seeds"),
                       ("verify", "replay a record on the native engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-seeds":
            document = select_seeds(args.count)
            _write(SEEDS, document)
            print(f"Wrote {SEEDS}: {document['train_seeds']}")
        elif args.command == "train":
            train(args.jobs)
        elif args.command == "evaluate":
            path = evaluate(args.jobs)
            print(f"Record: {path}")
        elif args.command == "verify":
            problems = verify(args.record.resolve(), args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print(f"Verified: {args.record}")
        else:
            document = summarize(args.record.resolve(), args.jobs)
            _write(RESULT, document)
            print(f"Wrote {RESULT}")
    except (EngineError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
