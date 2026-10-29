"""Run Experiment 015: a deeper commit search at the fast levels.

    python -m block_stack_ai.experiment015 bands [--games N] [--agents A,B] [--jobs N]
    python -m block_stack_ai.experiment015 depth-check [--jobs N]
    python -m block_stack_ai.experiment015 train [--jobs N]
    python -m block_stack_ai.experiment015 evaluate [--jobs N]
    python -m block_stack_ai.experiment015 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment015 summarize RECORD [--jobs N]

The agent decides each piece twice (native/agent.hpp): a commit search at the spawn, with
the preview not known yet (one ply: the seven unknown pieces), and an adjust search at
the reaction frame (the preview, then 013's extra ply). At levels 29+ a piece mostly
locks before the reaction frame, so the commit search decides alone. 015's agent is
014's (``reach_plan_014``) with Params' ``commit_ply_level`` and ``commit_beam``
(search.hpp): from level 29 the commit search adds the extra ply to its best
``commit_beam`` placements.

``bands`` (step 0) replays agents on 013's dev seeds and counts, per level band, the
pieces, how many reached their adjust search, the score earned and the clears.
``depth-check`` plays the commit ply (beam 2 and 4) and a killscreen budget of 4, with
and without it, on 014's numbers on the dev seeds, paired against 014's agent. ``train``
is 014's CEM over the same 22 numbers, with the commit ply in every game.
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
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment009 as e9, experiment011 as e11
from . import experiment012 as e12, experiment013 as e13, experiment014 as e14, native, runner
from .engine import EngineError, create_game

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "015-fast-commit"
CONFIG = EXPERIMENT_ROOT / "config.json"
BANDS_FILE = EXPERIMENT_ROOT / "bands.json"
DEPTH_CHECK = EXPERIMENT_ROOT / "depth_check.json"
TRAINING = EXPERIMENT_ROOT / "training.json"
FINAL_PARAMS = EXPERIMENT_ROOT / "final_params.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
SCHEMA = "fallgorithm.experiment015.run/1"
AGENT = e14.AGENT
NAMES = e14.NAMES  # the same 22 numbers; the search settings are fixed, not tuned
# Score bands as BetaTetris's statistics split them (pre-19, pre-29, pre-39).
BANDS = ("18", "19-28", "29-38", "39+")

_load, _write = e13._load, e13._write


def _band(level: int) -> str:
    return BANDS[0] if level < 19 else BANDS[1] if level < 29 else \
        BANDS[2] if level < 39 else BANDS[3]


def points_params() -> dict[str, Any]:
    """Experiment 014's final numbers (resolved): the bar, and CEM's starting point."""
    return e14._load(e14.FINAL_PARAMS)["resolved"]


def search() -> dict[str, int]:
    """config.json's commit-search settings, once step 0 has fixed the beam."""
    settings = _load(CONFIG)["search"]
    if settings["commit_beam"] is None:
        raise ValueError("config.json's search.commit_beam is not set yet (step 0 sets it)")
    return settings


def _agents() -> dict[str, dict[str, Any]]:
    """Diagnosed agents: name -> numbers for ``reach_plan_014``: 014's, 014's with each
    depth-check variant, and 015's once training has written ``final_params.json``."""
    agents = {"points": points_params()} | {
        name: points_params() | extra for name, extra in _load(CONFIG)["depth_check"].items()}
    if FINAL_PARAMS.exists():
        agents["fast_deep"] = _load(FINAL_PARAMS)["resolved"] | search()
    return agents


# ---------------------------------------------------------------- step 0: bands

def bands_game(job: tuple[str, int]) -> dict[str, Any]:
    """One dev game by the C++ agent, replayed on the Python binding. Each piece is
    credited to the band of its level at the spawn, and so are its clears and the score
    they earn; a piece "adjusts" when it is still active at the reaction frame, which is
    when native/agent.hpp runs the adjust search."""
    name, seed = job
    values = _agents()[name]
    config = _load(CONFIG)
    limits = e13._limits(config)
    played = native.play_game_ex(AGENT, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=limits,
                                 params=native.params(values))
    tally: Counter[str] = Counter()
    count, frame, band, piece = -1, 0, BANDS[0], ""
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in played["inputs"]:
            if state.phase == "active":
                if state.piece_count != count:
                    count, frame = state.piece_count, 0
                    band, piece = _band(state.level), state.current_piece
                    tally[f"pieces|{band}"] += 1
                    if piece == "I":
                        tally[f"I pieces|{band}"] += 1
                elif frame == limits.reaction_frames:
                    tally[f"adjusts|{band}"] += 1
                frame += 1
            before_lines, before_score = state.lines, state.score
            state, _ = game.step(mask)
            tally[f"score|{band}"] += state.score - before_score
            if state.lines > before_lines:
                size = state.lines - before_lines
                tally[f"clear{size}|{band}"] += 1
                tally[f"lines|{band}"] += size
                if piece == "I" and size == 4:
                    tally[f"I tetris|{band}"] += 1
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"{name} seed {seed}: the replay does not match the C++ game")
    if played["adjusts"] != sum(v for k, v in tally.items() if k.startswith("adjusts|")):
        raise ValueError(f"{name} seed {seed}: the adjust count differs from the C++ agent's")
    return {"agent": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "tally": dict(tally)}


def _band_summary(total: Counter[str], games: int) -> dict[str, Any]:
    out = {}
    for band in BANDS:
        pieces, lines = total[f"pieces|{band}"], total[f"lines|{band}"]
        tetris_lines = 4 * total[f"clear4|{band}"]
        out[band] = {
            "pieces_per_game": round(pieces / games, 1),
            "adjust_share": round(total[f"adjusts|{band}"] / max(1, pieces), 4),
            "score_per_game": round(total[f"score|{band}"] / games),
            "lines_per_game": round(lines / games, 2),
            "clears_per_game": {f"clear{size}": round(total[f"clear{size}|{band}"] / games, 2)
                                for size in (1, 2, 3, 4)},
            "tetris_share_of_lines": round(tetris_lines / max(1, lines), 4),
            "i_to_tetris": round(total[f"I tetris|{band}"] / max(1, total[f"I pieces|{band}"]),
                                 4)}
    running = 0
    for band in BANDS:  # BetaTetris's "pre-19 / pre-29 / pre-39 avg." are running totals
        running += out[band]["score_per_game"]
        out[band]["score_through_band"] = running
    return out


def bands(games: int, jobs: int, agents: list[str]) -> dict[str, Any]:
    seeds = e13._load(e13.SEEDS)["dev_seeds"][:games]
    if not seeds:
        raise ValueError("--games must be at least 1")
    with Pool(jobs) as pool:
        rows = pool.map(bands_game, [(name, seed) for name in agents for seed in seeds])
    out: dict[str, Any] = {
        "seeds": f"Experiment 013's first {len(seeds)} dev seeds (experiments/013-deeper-search/seeds.json)",
        "versions": runner._record_versions(), "agents": {}}
    for name in agents:
        mine = [row for row in rows if row["agent"] == name]
        total: Counter[str] = Counter()
        for row in mine:
            total.update(row["tally"])
        out["agents"][name] = {
            "games": len(mine), "numbers": _agents()[name],
            "mean_score": round(sum(r["score"] for r in mine) / len(mine), 1),
            "mean_lines": round(sum(r["lines"] for r in mine) / len(mine), 2),
            "bands": _band_summary(total, len(mine)), "totals": dict(sorted(total.items()))}
    return out


# ---------------------------------------------------------------- step 0: depth check

def _quick_game(job: tuple[dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """Dev and training worker: one C++ game's counters and its wall time."""
    values, seed, config = job
    tick = time.perf_counter()
    game = e14._quick_game((AGENT, values, seed, config))
    return game | {"seconds": time.perf_counter() - tick}


def depth_check(jobs: int) -> dict[str, Any]:
    """Each config.json depth-check variant on 014's numbers, on the dev seeds, paired by
    seed against 014's agent; the killscreen variants with the ply also against the same
    ply without the budget. A diagnostic, not part of the success rule."""
    config = _load(CONFIG)
    variants = {"points": {}} | config["depth_check"]
    seeds = _load(e13.SEEDS)["dev_seeds"]
    with Pool(jobs) as pool:
        runs = {name: pool.map(_quick_game, [(points_params() | extra, seed, config)
                                             for seed in seeds], chunksize=1)
                for name, extra in variants.items()}
    pairs = {f"{name} - points": e12.paired(games, runs["points"])
             for name, games in runs.items() if name != "points"}
    for beam in (2, 4):
        pairs[f"killscreen_4_beam{beam} - ply_beam{beam}"] = e12.paired(
            runs[f"killscreen_4_beam{beam}"], runs[f"ply_beam{beam}"])
    return {
        "question": "The commit ply and a killscreen budget of 4, with 014's numbers, on the dev seeds",
        "seeds": "dev_seeds (Experiment 013's)", "games": len(seeds),
        "variants": variants,
        "scores": {name: e13._scores(games) for name, games in runs.items()},
        "paired": pairs,
        "seconds_per_game": {name: round(sum(g["seconds"] for g in games) / len(games), 3)
                             for name, games in runs.items()},
    }


# ---------------------------------------------------------------- training (CEM)

def as_params(vector: list[float]) -> dict[str, float]:
    return dict(zip(NAMES, vector))


def _fitness_game(job: tuple[int, int, dict[str, Any], dict[str, float]]) -> tuple[int, int, int]:
    candidate, seed, config, values = job
    game = e14._quick_game((AGENT, values | config["search"], seed, config))
    return candidate, game["score"], game["lines"]


def start_mean() -> list[float]:
    """Experiment 014's final numbers (resolved)."""
    return [float(points_params()[name]) for name in NAMES]


def initial_spread() -> list[float]:
    """``experiment009.initial_spread()``, then config.json's spreads for 014's two."""
    spread = _load(CONFIG)["train"]["start_spread"]
    if None in spread.values():
        raise ValueError("config.json's train.start_spread is not set yet (step 0 sets it)")
    return e9.initial_spread() + [spread[name] for name in NAMES[len(e9.NAMES):]]


def train(jobs: int) -> None:
    """014's CEM (``experiment009.sample`` and ``cem_update``) over the 22 numbers with
    the commit ply in every game. Saves ``training.json`` after every iteration and resumes."""
    config = _load(CONFIG)
    config["search"] = search()
    seeds = _load(e12.SEEDS)["train_seeds"]
    settings = config["train"]
    population, elite, iterations = settings["population"], settings["elite"], settings["iterations"]
    rng = random.Random(settings["rng_seed"])
    mean, spread = start_mean(), initial_spread()
    floor = [settings["spread_floor"] * s for s in spread]
    state = _load(TRAINING) if TRAINING.exists() else {
        "settings": settings, "search": config["search"], "initial_mean": as_params(mean),
        "initial_spread": as_params(spread), "spread_floor": as_params(floor),
        "train_seeds": seeds, "iterations": []}
    if (state["settings"], state["search"], state["train_seeds"]) != \
            (settings, config["search"], seeds):
        raise ValueError(f"{TRAINING} was made with other settings or seeds; move it away first")
    started = time.time()
    with Pool(jobs) as pool:
        if "start_params" not in state:
            games = pool.map(_fitness_game, [(0, seed, config, as_params(mean))
                                             for seed in seeds], chunksize=1)
            state["start_params"] = {"mean_score": e9._mean([g[1] for g in games]),
                                     "mean_lines": e9._mean([g[2] for g in games])}
            _write(TRAINING, state)
            print(f"starting mean on training seeds: {state['start_params']}", file=sys.stderr,
                  flush=True)
        for done in state["iterations"]:  # resume: replay the draws and take the saved guess
            e9.sample(mean, spread, rng, population)
            mean, spread = list(done["mean_params"].values()), list(done["spread"].values())
        for iteration in range(len(state["iterations"]), iterations):
            tick = time.time()
            samples = e9.sample(mean, spread, rng, population)
            work = [(c, seed, config, as_params(vector))
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
                "population_mean": e9._mean(fitness), "best_params": as_params(samples[best]),
                "mean_params": as_params(mean), "spread": as_params(spread),
                "wall_seconds": round(time.time() - tick, 1)})
            _write(TRAINING, state)
            print(f"iteration {iteration}: best {fitness[best]:.0f} elite "
                  f"{state['iterations'][-1]['elite_mean']:.0f} population "
                  f"{e9._mean(fitness):.0f} ({time.time() - tick:.0f}s)", file=sys.stderr,
                  flush=True)
        games = pool.map(_fitness_game, [(0, seed, config, as_params(mean)) for seed in seeds],
                         chunksize=1)
        state["final_mean_fitness"] = {"mean_score": e9._mean([g[1] for g in games]),
                                       "mean_lines": e9._mean([g[2] for g in games])}
    state["total_wall_seconds"] = round(sum(i["wall_seconds"] for i in state["iterations"]), 1)
    _write(TRAINING, state)
    _write(FINAL_PARAMS, {"params": as_params(mean), "resolved": native.resolve(as_params(mean))})
    print(f"Wrote {FINAL_PARAMS} after {time.time() - started:.0f}s", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- evaluate / verify

RUNS = ("fast_deep", "points", "points_ply")  # record order, all on 012's held-out seeds


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats")} | {
        "search": search(), "fast_deep_params": _load(FINAL_PARAMS)["resolved"],
        "points_params": points_params(), "seeds": e13._heldout_seeds(), "runs": list(RUNS)}


def _agent_numbers(agent: str, config: dict[str, Any]) -> dict[str, Any]:
    """A record agent's numbers for ``reach_plan_014``: ``fast_deep`` is 015's trained
    agent, ``points`` 014's, ``points_ply`` 014's numbers with the commit ply."""
    if agent == "fast_deep":
        return config["fast_deep_params"] | config["search"]
    return config["points_params"] | ({"points": {}, "points_ply": config["search"]}[agent])


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    return [(agent, seed, config) for agent in config["runs"] for seed in config["seeds"]]


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game (014's ``play_native`` for 015's agents): played by the C++,
    replayed on the Python binding, the counters checked against the replay."""
    agent, seed, config = job
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    tick = time.perf_counter()
    played = native.play_game_ex(AGENT, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=e13._limits(config),
                                 params=native.params(_agent_numbers(agent, config)))
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
    """The launcher's new game: the fast_deep agent with ``config["params"]`` in format ``fmt``."""
    _, fmt, seed, config = job
    return play_native(("fast_deep", seed, config | {"fast_deep_params": config["params"],
                                                     "search": search(), "formats": [fmt]}))


def evaluate(jobs: int) -> Path:
    iterations = _load(CONFIG)["train"]["iterations"]
    if not PREDECLARED.exists() or not e13._committed(PREDECLARED) or not TRAINING.exists() or \
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
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-015"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 015 record"]
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
    if config["fast_deep_params"] != _load(FINAL_PARAMS)["resolved"] or \
            config["points_params"] != points_params() or config["search"] != search():
        raise ValueError("the record's numbers are not final_params.json's, 014's and "
                         "config.json's search settings")
    runs = {agent: e12._rows([e for e in record["episodes"] if e["agent"] == agent])
            for agent in RUNS}
    training = _load(TRAINING)
    main_pair = e12.paired(runs["fast_deep"], runs["points"])
    return {
        "experiment": "015-fast-commit",
        "question": ("Does 014's agent with the extra ply at the commit search from level 29, "
                     "re-tuned by CEM, beat 014 on 012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "search": config["search"],
        "params": {"fast_deep": config["fast_deep_params"], "points": config["points_params"]},
        "heldout": {"games": len(runs["fast_deep"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_fast_deep_minus_points": main_pair,
                    "paired_points_ply_minus_points": e12.paired(runs["points_ply"],
                                                                 runs["points"]),
                    "paired_fast_deep_minus_points_ply": e12.paired(runs["fast_deep"],
                                                                    runs["points_ply"])},
        "training": {"curve": [{key: item[key] for key in
                                ("iteration", "best", "elite_mean", "population_mean")}
                               for item in training["iterations"]],
                     "start_params": training["start_params"],
                     "final_mean": training["final_mean_fitness"],
                     "total_wall_seconds": training["total_wall_seconds"]},
        "depth_check": _load(DEPTH_CHECK),
        "success_rule": ("95% CI of the paired mean score difference (fast_deep minus points) "
                         "on 012's 1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment015")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("bands", "pieces, adjusts, score and clears by level band (dev seeds)"),
                       ("depth-check", "the commit ply and killscreen budget on dev seeds"),
                       ("train", "CEM over 22 numbers on 012's training seeds"),
                       ("evaluate", "play fast_deep, points and points_ply on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        if name == "bands":
            command.add_argument("--games", type=int, default=200)
            command.add_argument("--agents", default="points",
                                 help="comma-separated: points, a depth-check variant, or "
                                      "fast_deep (after training); other than the default, "
                                      "written to bands_<agents>.json")
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "bands":
            agents = args.agents.split(",")
            unknown = set(agents) - set(_agents())
            if unknown:
                raise ValueError(f"unknown or untrained agents: {sorted(unknown)}")
            path = BANDS_FILE if agents == ["points"] else \
                BANDS_FILE.with_name(f"bands_{'_'.join(agents)}.json")
            _write(path, bands(args.games, args.jobs, agents))
            print(f"Wrote {path}")
        elif args.command == "depth-check":
            _write(DEPTH_CHECK, depth_check(args.jobs))
            print(f"Wrote {DEPTH_CHECK}")
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
    sys.exit(main())
