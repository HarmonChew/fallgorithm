"""Run Experiment 013: deeper search, with the 20 numbers re-tuned for it by CEM.

    python -m block_stack_ai.experiment013 select-seeds
    python -m block_stack_ai.experiment013 depth-check [--jobs N]
    python -m block_stack_ai.experiment013 value-probe --explore E --keep K --start-max S [--jobs N]
    python -m block_stack_ai.experiment013 train [--jobs N]
    python -m block_stack_ai.experiment013 evaluate [--jobs N]
    python -m block_stack_ai.experiment013 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment013 summarize RECORD [--jobs N]

``depth-check`` (step 0) plays 012's numbers with and without one more ply of lookahead
(search.hpp's extra ply at the adjust search) on the dev seeds. ``train`` is 012's CEM
run again, with the extra ply in every game. ``value-probe`` records the learned-value
trials that came first (native/value.hpp, Monte Carlo fitted value iteration from
self-play): short runs on self-play seeds only, kept as groundwork for a later
experiment. All games are played by the C++ (``native.play_game_ex``); held-out games
are replayed on the Python binding.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment006, experiment009 as e9, experiment011 as e11
from . import experiment012 as e12, experiment005, native, runner
from .engine import EngineError, create_game
from .limits import Limits
from .tunedplan import resolve

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "013-deeper-search"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
DEPTH_CHECK = EXPERIMENT_ROOT / "depth_check.json"
TRAINING = EXPERIMENT_ROOT / "training.json"
FINAL_PARAMS = EXPERIMENT_ROOT / "final_params.json"
VALUE_PROBE = EXPERIMENT_ROOT / "value_probe.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
SCHEMA = "fallgorithm.experiment013.run/1"
DEV_LABEL = "fallgorithm013/dev/v1/{}"
SELFPLAY_LABEL = "fallgorithm013/selfplay/v1/{}/{}"  # round, index
BOOTSTRAP_SEED = 12
WEIGHTS = native.VALUE_WEIGHTS  # the learned value (value probe only)


def _load(path: Path) -> Any:
    return experiment006._load(path)


def _write(path: Path, value: Any) -> None:
    e9._write(path, value)


def cem_params() -> dict[str, Any]:
    """Experiment 012's final numbers (resolved): the baseline, CEM's starting mean, and the
    value probe's first player."""
    return _load(e12.FINAL_PARAMS)["resolved"]


# ---------------------------------------------------------------- seeds

def _heldout_seeds() -> list[int]:
    return _load(e12.SEEDS)["heldout_seeds"]


def select_seeds(dev_count: int = 200) -> dict[str, Any]:
    """Fresh dev seeds: none used by Experiments 000-012, nor a native start-state twin."""
    game = _load(CONFIG)["game"]
    used = _load(e12.SEEDS)
    excluded = sorted(set(e12.excluded_seeds()) | set(used["train_seeds"]) |
                      set(used["heldout_seeds"]))
    seen = {experiment006.native_identity(game, seed) for seed in excluded}
    selected, index = [], 0
    while len(selected) < dev_count:
        seed = experiment006._label_seed(DEV_LABEL, index)
        identity = experiment006.native_identity(game, seed)
        if identity not in seen:
            selected.append({"seed": seed, "candidate_index": index})
            seen.add(identity)
        index += 1
    return {
        "selection": ("SHA256(<label with index>), first two bytes big-endian; skip any seed "
                      "used by Experiments 000-012 (012's training and held-out seeds included) "
                      "and any seed whose seed-erased native start state matches an excluded "
                      "or already selected one; no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
        "dev_label": DEV_LABEL.replace("{}", "<index>"),
        "dev_selected": selected,
        "dev_seeds": [item["seed"] for item in selected],
        "heldout": "Experiment 012's 1,000 held-out seeds (experiments/012-native-cem/seeds.json)",
    }


def selfplay_seeds(round_index: int, count: int, protected: set[str]) -> list[int]:
    """One round's self-play seeds: labelled draws, no two with the same start state, and none
    with a start state in ``protected`` (the dev and held-out seeds', and any others the
    caller keeps apart)."""
    game = _load(CONFIG)["game"]
    seen = set(protected)
    seeds, index = [], 0
    while len(seeds) < count:
        seed = experiment006._label_seed(SELFPLAY_LABEL.format(round_index, "{}"), index)
        identity = experiment006.native_identity(game, seed)
        if identity not in seen:
            seeds.append(seed)
            seen.add(identity)
        index += 1
    return seeds


def _protected(config: dict[str, Any]) -> set[str]:
    seeds = _load(SEEDS)["dev_seeds"] + _heldout_seeds()
    return {experiment006.native_identity(config["game"], seed) for seed in seeds}


# ---------------------------------------------------------------- games

def _limits(config: dict[str, Any]) -> Limits:
    fmt = config["formats"][0]
    return Limits(fmt["tap_hz"], fmt["reaction_ms"])


def _agent_args(agent: str, config: dict[str, Any]) -> dict[str, Any]:
    """``play_game_ex``'s agent arguments for a record agent name."""
    if agent == "value":
        return {"agent": "value", "weights": config["weights"]}
    if agent == "deep":
        return {"agent": "reach_plan_extra_ply", "params": native.params(config["deep_params"])}
    kind = {"cem": "reach_plan", "cem_extra_ply": "reach_plan_extra_ply"}[agent]
    return {"agent": kind, "params": native.params(config["params"])}


def _quick_game(job: tuple[str, int, dict[str, Any], bool]) -> dict[str, Any]:
    """Training and dev worker: one game's counters. A ``fit`` game is a self-play game: it
    starts with a random number (up to ``config["explore_start_max"]``) of random placements,
    then explores at ``config["explore"]`` (the stream from ``config["round"]`` and the seed),
    and also returns its least-squares sums."""
    agent, seed, config, fit = job
    args = _agent_args(agent, config)
    stream = config["round"] << 16 | seed if fit else 0
    explore = {"explore": config["explore"], "explore_seed": stream,
               "explore_start": random.Random(stream).randint(0, config["explore_start_max"])} \
        if fit else {}
    played = native.play_game_ex(args.pop("agent"), config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=_limits(config), fit=fit, **explore, **args)
    del played["inputs"]
    return played | {"seed": seed}


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game (Experiment 011's ``play_native`` for any of 013's agents): played by
    the C++, replayed on the Python binding, the counters checked against the replay."""
    agent, seed, config = job
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    args = _agent_args(agent, config)
    tick = time.perf_counter()
    played = native.play_game_ex(args.pop("agent"), config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=_limits(config), **args)
    seconds = time.perf_counter() - tick
    if played["initial_state_hash"] != initial_hash:
        raise ValueError(f"seed {seed}: the C++ engine starts in another state than the "
                         "binding's; rebuild both from the same Block Stack checkout")
    episode = {"agent": agent, "format": 0, "seed": seed, "initial_state_hash": initial_hash,
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
    return episode


def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """The launcher's new game: the deep agent with ``config["params"]`` in format ``fmt``."""
    _, fmt, seed, config = job
    return play_native(("deep", seed, config | {"deep_params": config["params"],
                                                "formats": [fmt]}))


def _scores(games: list[dict[str, Any]]) -> dict[str, float]:
    return {"mean_score": e9._mean([g["score"] for g in games]),
            "mean_lines": e9._mean([g["lines"] for g in games])}


# ---------------------------------------------------------------- step 0: depth check

def depth_check(jobs: int) -> dict[str, Any]:
    """012's numbers with and without the extra ply on the dev seeds, paired by seed."""
    config = _load(CONFIG) | {"params": cem_params()}
    seeds = _load(SEEDS)["dev_seeds"]
    tick = time.time()
    with Pool(jobs) as pool:
        runs = {agent: pool.map(_quick_game, [(agent, seed, config, False) for seed in seeds],
                                chunksize=1)
                for agent in ("cem", "cem_extra_ply")}
    rows = {agent: [{"seed": g["seed"], "score": g["score"], "lines": g["lines"]} for g in games]
            for agent, games in runs.items()}
    return {
        "question": ("Does one more ply of lookahead (at the adjust search) help 012's numbers? "
                     "A diagnostic on the dev seeds, not part of the success rule."),
        "seeds": "dev_seeds", "games": len(seeds),
        "cem": _scores(runs["cem"]), "cem_extra_ply": _scores(runs["cem_extra_ply"]),
        "paired_extra_minus_cem": e12.paired(rows["cem_extra_ply"], rows["cem"]),
        "wall_seconds": round(time.time() - tick, 1),
    }


# ---------------------------------------------------------------- fitting

def solve(gram: list[float], target: list[float], ridge: float) -> list[float]:
    """Least squares with a relative ridge: (G + ridge * diag(G)) w = t, by Gaussian
    elimination with partial pivoting. A weight with no data (zero diagonal) is 0."""
    n = len(target)
    rows = [[gram[i * n + j] for j in range(n)] + [target[i]] for i in range(n)]
    for i in range(n):
        rows[i][i] += ridge * rows[i][i] if rows[i][i] > 0 else 1.0
    for column in range(n):
        pivot = max(range(column, n), key=lambda r: abs(rows[r][column]))
        rows[column], rows[pivot] = rows[pivot], rows[column]
        lead = rows[column][column]
        if lead == 0:
            raise ValueError("singular least-squares system")
        for r in range(column + 1, n):
            factor = rows[r][column] / lead
            if factor:
                row, top = rows[r], rows[column]
                for k in range(column, n + 1):
                    row[k] -= factor * top[k]
    weights = [0.0] * n
    for i in reversed(range(n)):
        weights[i] = (rows[i][n] - sum(rows[i][k] * weights[k] for k in range(i + 1, n))) / rows[i][i]
    return weights


def _sum_fits(games: list[dict[str, Any]]) -> dict[str, list[float]]:
    gram = [0.0] * (WEIGHTS * WEIGHTS)
    target = [0.0] * WEIGHTS
    totals = [0.0] * 3
    for game in games:
        gram = [a + b for a, b in zip(gram, game["gram"])]
        target = [a + b for a, b in zip(target, game["target"])]
        totals = [a + b for a, b in zip(totals, game["totals"])]
    return {"gram": gram, "target": target, "totals": totals}


def fit_quality(sums: dict[str, list[float]], weights: list[float]) -> dict[str, float]:
    """R^2 of the fit on the data it was fitted to, from the sums alone."""
    gram, target, (count, total, squares) = sums["gram"], sums["target"], sums["totals"]
    n = len(weights)
    quadratic = sum(weights[i] * gram[i * n + j] * weights[j] for i in range(n) for j in range(n)
                    if gram[i * n + j])
    residual = squares - 2 * sum(w * t for w, t in zip(weights, target)) + quadratic
    spread = squares - total * total / count
    return {"boards": count, "mean_target": total / count, "r2": 1 - residual / spread}


# ---------------------------------------------------------------- value probe

def value_probe(jobs: int, explore: float, keep: int, start_max: int, rounds: int = 4,
                games: int = 600, test_games: int = 300) -> dict[str, Any]:
    """A short learned-value run, on self-play seeds only (never dev or held-out).

    012's numbers play ``games`` self-play games (rounds labelled 90 on); the weights are
    fitted to the last ``keep`` rounds' boards; the fitted value agent is scored on
    ``test_games`` other self-play seeds (label round 91), then plays the next round itself.
    """
    config = _load(CONFIG)
    protected = _protected(config)
    seeds = selfplay_seeds(90, games, protected)
    test = selfplay_seeds(91, test_games, protected | {
        experiment006.native_identity(config["game"], seed) for seed in seeds})
    explore_args = {"explore": explore, "explore_start_max": start_max}
    entries = []
    with Pool(jobs) as pool:
        played = pool.map(_quick_game, [("cem", seed, config | explore_args | {
            "params": cem_params(), "round": 90}, True) for seed in seeds], chunksize=4)
        recent = [_sum_fits(played)]
        player = _scores(played)
        for index in range(rounds):
            sums = {key: [sum(values) for values in zip(*(r[key] for r in recent))]
                    for key in ("gram", "target", "totals")}
            weights = solve(sums["gram"], sums["target"], config["value_probe"]["ridge"])
            scored = pool.map(_quick_game, [("value", seed, config | {"weights": weights}, False)
                                            for seed in test], chunksize=2)
            entries.append({"round": index, "selfplay_player": player,
                            "fit": fit_quality(sums, weights), "value_agent": _scores(scored)})
            print(f"value probe round {index}: {entries[-1]['value_agent']}", file=sys.stderr,
                  flush=True)
            played = pool.map(_quick_game, [("value", seed, config | explore_args | {
                "weights": weights, "round": 92 + index}, True) for seed in seeds], chunksize=2)
            recent = (recent + [_sum_fits(played)])[-keep:]
            player = _scores(played)
    return {"explore": explore, "keep_rounds": keep, "explore_start_max": start_max,
            "selfplay_games": games, "test_games": test_games, "rounds": entries}


# ---------------------------------------------------------------- training (CEM)

def _fitness_game(job: tuple[int, int, dict[str, Any], dict[str, float]]) -> tuple[int, int, int]:
    """Training worker: ``(candidate, score, lines)`` for one candidate on one seed, played
    with the extra ply."""
    candidate, seed, config, params = job
    played = native.play_game_ex("reach_plan_extra_ply", config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=_limits(config), params=native.params(params))
    return candidate, played["score"], played["lines"]


def start_mean() -> list[float]:
    """Experiment 012's final numbers, resolved, in ``experiment009.NAMES`` order."""
    resolved = cem_params()
    return [float(resolved[name]) for name in e9.NAMES]


def train(jobs: int) -> None:
    """012's CEM (``experiment009.sample`` and ``cem_update``) with the extra ply in every
    game. Saves ``training.json`` after every iteration and can resume."""
    config = _load(CONFIG)
    seeds = _load(e12.SEEDS)["train_seeds"]
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
        if "start_params" not in state:
            games = pool.map(_fitness_game, [(0, seed, config, e9.as_params(mean))
                                             for seed in seeds], chunksize=1)
            state["start_params"] = {"mean_score": e9._mean([g[1] for g in games]),
                                     "mean_lines": e9._mean([g[2] for g in games])}
            _write(TRAINING, state)
            print(f"012's numbers with the extra ply on training seeds: {state['start_params']}",
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
        games = pool.map(_fitness_game, [(0, seed, config, e9.as_params(mean)) for seed in seeds],
                         chunksize=1)
        state["final_mean_fitness"] = {"mean_score": e9._mean([g[1] for g in games]),
                                       "mean_lines": e9._mean([g[2] for g in games])}
    state["total_wall_seconds"] = round(sum(i["wall_seconds"] for i in state["iterations"]), 1)
    _write(TRAINING, state)
    _write(FINAL_PARAMS, {"params": e9.as_params(mean), "resolved": resolve(e9.as_params(mean))})
    print(f"Wrote {FINAL_PARAMS} after {time.time() - started:.0f}s", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- evaluate / verify

RUNS = ("deep", "cem", "cem_extra_ply")  # record order, all on 012's held-out seeds


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats")} | {
        "deep_params": _load(FINAL_PARAMS)["resolved"], "params": cem_params(),
        "seeds": _heldout_seeds(), "runs": list(RUNS)}


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    return [(agent, seed, config) for agent in config["runs"] for seed in config["seeds"]]


def _committed(path: Path) -> bool:
    """Whether ``path`` is tracked by Git and unchanged since the last commit."""
    root = runner.PROJECT_ROOT
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
                          capture_output=True).returncode == 0 and \
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(path)], cwd=root).returncode == 0


def evaluate(jobs: int) -> Path:
    iterations = _load(CONFIG)["train"]["iterations"]
    if not PREDECLARED.exists() or not _committed(PREDECLARED) or not TRAINING.exists() or \
            len(_load(TRAINING)["iterations"]) < iterations or not FINAL_PARAMS.exists():
        raise ValueError("held-out games wait for a committed predeclared.md and the finished "
                         "training")
    config = record_configuration()
    tick = time.perf_counter()
    with Pool(jobs) as pool:
        episodes = pool.map(play_native, _work(config), chunksize=4)
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e11.sources(), "workers": jobs,
        "wall_seconds": round(time.perf_counter() - tick, 1), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-013"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 013 record"]
    config = record["configuration"]
    if [(e["agent"], e["seed"]) for e in record["episodes"]] != \
            [(agent, seed) for agent, seed, _ in _work(config)]:
        return ["episodes do not match the configured runs and seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(e9._replay, [(e, config) for e in record["episodes"]], chunksize=4)
    return [problem for problems in found for problem in problems]


# ---------------------------------------------------------------- summarize

def success(score_ci: dict[str, float]) -> bool:
    """The predeclared rule: the paired mean-score difference's 95% interval is wholly above 0."""
    return score_ci["ci95_low"] > 0


def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    problems = verify(path, jobs)
    if problems:
        raise ValueError(f"{path} does not verify: {problems[:3]}")
    record = _load(path)
    config = record["configuration"]
    if config["deep_params"] != _load(FINAL_PARAMS)["resolved"] or config["params"] != cem_params():
        raise ValueError("the record's numbers are not final_params.json's and 012's")
    runs = {agent: e12._rows([e for e in record["episodes"] if e["agent"] == agent])
            for agent in RUNS}
    training = _load(TRAINING)
    main_pair = e12.paired(runs["deep"], runs["cem"])
    return {
        "experiment": "013-deeper-search",
        "question": ("Does one more ply of lookahead, with the 20 numbers re-tuned for it by CEM, "
                     "beat Experiment 012 on 012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "params": {"deep": config["deep_params"], "cem": config["params"]},
        "heldout": {"games": len(runs["deep"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_deep_minus_cem": main_pair,
                    "paired_cem_extra_ply_minus_cem": e12.paired(runs["cem_extra_ply"],
                                                                 runs["cem"]),
                    "paired_deep_minus_cem_extra_ply": e12.paired(runs["deep"],
                                                                  runs["cem_extra_ply"])},
        "training": {"curve": [{key: item[key] for key in
                                ("iteration", "best", "elite_mean", "population_mean")}
                               for item in training["iterations"]],
                     "start_params": training["start_params"],
                     "final_mean": training["final_mean_fitness"],
                     "total_wall_seconds": training["total_wall_seconds"]},
        "depth_check": _load(DEPTH_CHECK),
        "success_rule": ("95% CI of the paired mean score difference (deep minus cem) on 012's "
                         "1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment013")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("select-seeds", help="write seeds.json with fresh dev seeds")
    for name, text in (("depth-check", "step 0: 012's numbers with one more ply, on dev seeds"),
                       ("value-probe", "a short learned-value run on self-play seeds"),
                       ("train", "CEM with the extra ply on 012's training seeds"),
                       ("evaluate", "play deep, cem and cem_extra_ply on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        if name == "value-probe":
            command.add_argument("--explore", type=float, required=True)
            command.add_argument("--keep", type=int, required=True)
            command.add_argument("--start-max", type=int, required=True)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-seeds":
            document = select_seeds()
            _write(SEEDS, document)
            print(f"Wrote {SEEDS}: {len(document['dev_seeds'])} dev seeds")
        elif args.command == "depth-check":
            _write(DEPTH_CHECK, depth_check(args.jobs))
            print(f"Wrote {DEPTH_CHECK}")
        elif args.command == "value-probe":
            runs = _load(VALUE_PROBE)["runs"] if VALUE_PROBE.exists() else []
            runs.append(value_probe(args.jobs, args.explore, args.keep, args.start_max))
            _write(VALUE_PROBE, {"note": ("Learned-value trials (native/value.hpp) on self-play "
                                          "seeds only; not part of the success rule."),
                                 "runs": runs})
            print(f"Wrote {VALUE_PROBE}")
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
