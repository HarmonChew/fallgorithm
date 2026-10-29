"""Run Experiment 014: real points for clears, Tetrises past the killscreen, NES odds.

    python -m block_stack_ai.experiment014 singles [--games N] [--jobs N]
    python -m block_stack_ai.experiment014 odds-check [--games N] [--jobs N]
    python -m block_stack_ai.experiment014 lever-check [--jobs N]
    python -m block_stack_ai.experiment014 train [--jobs N]
    python -m block_stack_ai.experiment014 evaluate [--jobs N]
    python -m block_stack_ai.experiment014 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment014 summarize RECORD [--jobs N]

``singles`` (step 0) replays 012's and 013's agents on 013's dev seeds and counts every
line clear by level band (18-28, 29-38, 39+) and by the phase the agent was in when it
placed the piece (BUILD, or SPEND and why), plus how many I pieces became Tetrises.

The agent (``native.play_game_ex("reach_plan_014", ...)``) is 013's deep search with the
seven unknown pieces weighed by the NES randomizer's odds (search.hpp), and two more
numbers (eval.hpp): ``clear_points``, the weight on a clear's real, level-scaled points,
and ``killscreen_budget``, the BUILD height budget from level 39. ``odds-check`` counts
the engine's own piece pairs against those odds; ``lever-check`` tries each change on
the dev seeds; ``train`` is 013's CEM with the two numbers added. All on 013's dev seeds
and 012's training and held-out seeds.
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
from . import experiment012 as e12, experiment013 as e13, native, pathaware, runner, wellplan
from .engine import EngineError, create_game
from .pieces import PIECES

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "014-real-points"
SINGLES = EXPERIMENT_ROOT / "singles.json"
CONFIG = EXPERIMENT_ROOT / "config.json"
ODDS_CHECK = EXPERIMENT_ROOT / "odds_check.json"
LEVER_CHECK = EXPERIMENT_ROOT / "lever_check.json"
TRAINING = EXPERIMENT_ROOT / "training.json"
FINAL_PARAMS = EXPERIMENT_ROOT / "final_params.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
SCHEMA = "fallgorithm.experiment014.run/1"
AGENT = "reach_plan_014"
# CEM's numbers: 009's twenty, then 014's two (start values and spreads in config.json).
NAMES = e9.NAMES + ["clear_points", "killscreen_budget"]
BANDS = ("18-28", "29-38", "39+")
REASONS = ("build", "spend:drought", "spend:height", "spend:drought+height")


def _band(level: int) -> str:
    return BANDS[0] if level < 29 else BANDS[1] if level < 39 else BANDS[2]


def _agents() -> dict[str, tuple[str, dict[str, Any]]]:
    """Diagnosed agents: name -> (native agent kind, resolved numbers); ``points`` once
    training has written ``final_params.json``."""
    agents = {"cem": ("reach_plan", e13.cem_params()),
              "deep": ("reach_plan_extra_ply", e13._load(e13.FINAL_PARAMS)["resolved"])}
    if FINAL_PARAMS.exists():
        agents["points"] = (AGENT, _load(FINAL_PARAMS)["resolved"])
    return agents


def _reason(values: dict[str, Any], phase: str, level: int, drought: int, height: int) -> str:
    if phase == wellplan.BUILD:
        return "build"
    budget = (values["killscreen_budget"]
              if level >= 39 and values.get("killscreen_budget", -1) >= 0 else
              values["survival_budget"] if level >= values["survival_level"] else
              values["height_budget"])
    long_drought, too_tall = drought >= values["drought_bound"], height >= budget
    return ("spend:drought+height" if long_drought and too_tall else
            "spend:drought" if long_drought else "spend:height")


def singles_game(job: tuple[str, int]) -> dict[str, Any]:
    """One dev game by the C++ agent, replayed on the Python binding: the per-piece phase
    is recomputed from the replayed state (``native.phase``) and every clear is credited
    to the band and phase of the piece that made it."""
    name, seed = job
    kind, values = _agents()[name]
    config = e13._load(e13.CONFIG)
    params = native.params(values)
    played = native.play_game_ex(kind, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=e13._limits(config),
                                 params=params)
    reaction = e13._limits(config).reaction_frames
    tally: Counter[str] = Counter()
    drought = before_drought = frame = 0
    count, piece = -1, ("", "", "")
    with create_game(**config["game"], seed=seed) as game:
        state = game.state

        def label(drought: int) -> tuple[str, str, str]:
            columns = pathaware.grid_columns(wellplan.visible_grid(state.board))
            phase = native.phase(params, state.level, drought, columns)
            return (_band(state.level), _reason(values, phase, state.level, drought,
                                                wellplan.stack_height(columns)),
                    state.current_piece)

        for mask in played["inputs"]:
            # The drought as native/agent.hpp counts it: at spawn only the current piece
            # resets it; the preview counts too once the adjust decision fires at the
            # reaction frame, which a piece that locks sooner never reaches.
            if state.phase == "active":
                current_is_i = state.current_piece == "I"
                preview_is_i = state.next_piece == "I"
                if state.piece_count != count:
                    count, frame, before_drought = state.piece_count, 0, drought
                    drought = 0 if current_is_i else before_drought + 1
                    piece = label(drought)
                    tally[f"pieces|{piece[0]}|{piece[1]}"] += 1
                    if current_is_i:
                        tally[f"I pieces|{piece[0]}"] += 1
                elif frame == reaction:
                    drought = 0 if current_is_i or preview_is_i else before_drought + 1
                    tally[f"pieces|{piece[0]}|{piece[1]}"] -= 1
                    piece = label(drought)
                    tally[f"pieces|{piece[0]}|{piece[1]}"] += 1
                frame += 1
            before = state.lines
            state, _ = game.step(mask)
            if state.lines > before:
                size = state.lines - before
                tally[f"clear{size}|{piece[0]}|{piece[1]}"] += 1
                if piece[2] == "I" and size == 4:
                    tally[f"I tetris|{piece[0]}"] += 1
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"{name} seed {seed}: the replay does not match the C++ game")
    return {"agent": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "tally": dict(tally)}


def _per_game(total: Counter[str], games: int) -> dict[str, Any]:
    """Per-game clears by band and phase, and the I-piece Tetris conversion by band."""
    clears = {band: {reason: {f"clear{size}": round(total[f"clear{size}|{band}|{reason}"]
                                                     / games, 2) for size in (1, 2, 3, 4)}
                     for reason in REASONS} for band in BANDS}
    pieces = {band: {reason: round(total[f"pieces|{band}|{reason}"] / games, 1)
                     for reason in REASONS} for band in BANDS}
    i_to_tetris = {band: round(total[f"I tetris|{band}"] / max(1, total[f"I pieces|{band}"]),
                               3) for band in BANDS}
    return {"clears_per_game": clears, "pieces_per_game": pieces, "i_to_tetris": i_to_tetris}


def singles(games: int, jobs: int, agents: list[str]) -> dict[str, Any]:
    seeds = e13._load(e13.SEEDS)["dev_seeds"][:games]
    work = [(name, seed) for name in agents for seed in seeds]
    with Pool(jobs) as pool:
        rows = pool.map(singles_game, work)
    if not seeds:
        raise ValueError("--games must be at least 1")
    out: dict[str, Any] = {
        "seeds": f"Experiment 013's first {len(seeds)} dev seeds (experiments/013-deeper-search/seeds.json)",
        "versions": runner._record_versions(),
        "agents": {}}
    for name in agents:
        mine = [row for row in rows if row["agent"] == name]
        total: Counter[str] = Counter()
        for row in mine:
            total.update(row["tally"])
        out["agents"][name] = {
            "games": len(mine),
            "mean_score": round(sum(r["score"] for r in mine) / len(mine), 1),
            "mean_lines": round(sum(r["lines"] for r in mine) / len(mine), 2),
            **_per_game(total, len(mine)), "totals": dict(sorted(total.items()))}
    return out


# ---------------------------------------------------------------- the agents

_load, _write = e13._load, e13._write


def deep_params() -> dict[str, Any]:
    """Experiment 013's final numbers (resolved): the bar, and CEM's starting point."""
    return e13._load(e13.FINAL_PARAMS)["resolved"]


def as_params(vector: list[float]) -> dict[str, float]:
    return dict(zip(NAMES, vector))


def _agent_args(agent: str, config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """A record agent's ``(native kind, numbers)``: ``points`` is 014's trained agent,
    ``deep`` 013's, ``deep_nes`` 013's numbers with the NES odds."""
    if agent == "points":
        return AGENT, config["points_params"]
    return {"deep": "reach_plan_extra_ply", "deep_nes": AGENT}[agent], config["deep_params"]


def _quick_game(job: tuple[str, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """Dev and training worker: one C++ game's counters."""
    kind, values, seed, config = job
    played = native.play_game_ex(kind, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=e13._limits(config),
                                 params=native.params(values))
    return {"seed": seed, "score": played["score"], "lines": played["lines"]}


# ---------------------------------------------------------------- step 0: odds and levers

def _pairs_game(seed: int) -> dict[str, int]:
    """Every (piece, next piece) pair the engine deals in one dev game by 013's agent: at
    each spawn the preview was drawn with the current piece as the previous one."""
    config = _load(CONFIG)
    played = native.play_game_ex("reach_plan_extra_ply", config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=e13._limits(config), params=native.params(deep_params()))
    pairs: Counter[str] = Counter()
    count = -1
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in played["inputs"]:
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                pairs[state.current_piece + state.next_piece] += 1
            state, _ = game.step(mask)
    return dict(pairs)


def odds_check(games: int, jobs: int) -> dict[str, Any]:
    """The engine's piece pairs on the dev seeds against search.hpp's NES odds."""
    seeds = _load(e13.SEEDS)["dev_seeds"][:games]
    total: Counter[str] = Counter()
    with Pool(jobs) as pool:
        for pairs in pool.imap_unordered(_pairs_game, seeds):
            total.update(pairs)
    rows, worst = {}, 0.0
    for previous in PIECES:
        dealt = sum(total[previous + piece] for piece in PIECES)
        observed = {piece: round(total[previous + piece] / dealt, 4) for piece in PIECES}
        expected = {piece: native.nes_odds(previous, piece) for piece in PIECES}
        worst = max(worst, *(abs(observed[p] - expected[p]) for p in PIECES))
        rows[previous] = {"pairs": dealt, "observed": observed,
                          "expected_64ths": {p: round(expected[p] * 64) for p in PIECES}}
    return {"seeds": f"013's first {len(seeds)} dev seeds", "games": len(seeds),
            "pairs": sum(total.values()), "after": rows,
            "largest_difference": round(worst, 4)}


def lever_check(jobs: int) -> dict[str, Any]:
    """Each change alone on 013's numbers, on the dev seeds, paired by seed against 013's
    agent. A diagnostic, not part of the success rule."""
    config = _load(CONFIG)
    variants = {"deep": ("reach_plan_extra_ply", {})} | {
        name: (AGENT, extra) for name, extra in config["lever_check"].items()}
    seeds = _load(e13.SEEDS)["dev_seeds"]
    tick = time.time()
    with Pool(jobs) as pool:
        runs = {name: pool.map(_quick_game, [(kind, deep_params() | extra, seed, config)
                                             for seed in seeds], chunksize=1)
                for name, (kind, extra) in variants.items()}
    return {
        "question": "Each 014 change alone, with 013's numbers, on the dev seeds",
        "seeds": "dev_seeds (Experiment 013's)", "games": len(seeds),
        "variants": {name: {"agent": kind, "numbers": extra} for name, (kind, extra)
                     in variants.items()},
        "scores": {name: e13._scores(games) for name, games in runs.items()},
        "paired_minus_deep": {name: e12.paired(games, runs["deep"])
                              for name, games in runs.items() if name != "deep"},
        "wall_seconds": round(time.time() - tick, 1),
    }


# ---------------------------------------------------------------- training (CEM)

def _fitness_game(job: tuple[int, int, dict[str, Any], dict[str, float]]) -> tuple[int, int, int]:
    candidate, seed, config, values = job
    game = _quick_game((AGENT, values, seed, config))
    return candidate, game["score"], game["lines"]


def start_mean() -> list[float]:
    """013's final numbers (resolved), then config.json's start values for the two new."""
    resolved = deep_params() | _load(CONFIG)["train"]["start_values"]
    return [float(resolved[name]) for name in NAMES]


def initial_spread() -> list[float]:
    """``experiment009.initial_spread()``, then config.json's spreads for the two new."""
    return e9.initial_spread() + [_load(CONFIG)["train"]["start_spread"][name]
                                  for name in NAMES[len(e9.NAMES):]]


def train(jobs: int) -> None:
    """013's CEM (``experiment009.sample`` and ``cem_update``) over 22 numbers with the
    014 agent in every game. Saves ``training.json`` after every iteration and resumes."""
    config = _load(CONFIG)
    seeds = _load(e12.SEEDS)["train_seeds"]
    settings = config["train"]
    population, elite, iterations = settings["population"], settings["elite"], settings["iterations"]
    rng = random.Random(settings["rng_seed"])
    mean, spread = start_mean(), initial_spread()
    floor = [settings["spread_floor"] * s for s in spread]
    state = _load(TRAINING) if TRAINING.exists() else {
        "settings": settings, "initial_mean": as_params(mean),
        "initial_spread": as_params(spread), "spread_floor": as_params(floor),
        "train_seeds": seeds, "iterations": []}
    if (state["settings"], state["train_seeds"]) != (settings, seeds):
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

RUNS = ("points", "deep", "deep_nes")  # record order, all on 012's held-out seeds


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats")} | {
        "points_params": _load(FINAL_PARAMS)["resolved"], "deep_params": deep_params(),
        "seeds": e13._heldout_seeds(), "runs": list(RUNS)}


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    return [(agent, seed, config) for agent in config["runs"] for seed in config["seeds"]]


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game (013's ``play_native`` for 014's agents): played by the C++,
    replayed on the Python binding, the counters checked against the replay."""
    agent, seed, config = job
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    kind, values = _agent_args(agent, config)
    tick = time.perf_counter()
    played = native.play_game_ex(kind, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=e13._limits(config),
                                 params=native.params(values))
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
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-014"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 014 record"]
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
    if config["points_params"] != _load(FINAL_PARAMS)["resolved"] or \
            config["deep_params"] != deep_params():
        raise ValueError("the record's numbers are not final_params.json's and 013's")
    runs = {agent: e12._rows([e for e in record["episodes"] if e["agent"] == agent])
            for agent in RUNS}
    training = _load(TRAINING)
    main_pair = e12.paired(runs["points"], runs["deep"])
    return {
        "experiment": "014-real-points",
        "question": ("Does 013's deep search with the NES piece odds, a real-points clear term "
                     "and its own build budget from level 39, re-tuned by CEM, beat 013 on "
                     "012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "params": {"points": config["points_params"], "deep": config["deep_params"]},
        "heldout": {"games": len(runs["points"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_points_minus_deep": main_pair,
                    "paired_deep_nes_minus_deep": e12.paired(runs["deep_nes"], runs["deep"]),
                    "paired_points_minus_deep_nes": e12.paired(runs["points"],
                                                               runs["deep_nes"])},
        "training": {"curve": [{key: item[key] for key in
                                ("iteration", "best", "elite_mean", "population_mean")}
                               for item in training["iterations"]],
                     "start_params": training["start_params"],
                     "final_mean": training["final_mean_fitness"],
                     "total_wall_seconds": training["total_wall_seconds"]},
        "odds_check": _load(ODDS_CHECK), "lever_check": _load(LEVER_CHECK),
        "success_rule": ("95% CI of the paired mean score difference (points minus deep) on "
                         "012's 1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment014")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("singles", "clears by level band and phase, 012's and 013's agents"),
                       ("odds-check", "the engine's piece pairs against the NES odds"),
                       ("lever-check", "each change alone with 013's numbers, on dev seeds"),
                       ("train", "CEM over 22 numbers on 012's training seeds"),
                       ("evaluate", "play points, deep and deep_nes on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        if name in ("singles", "odds-check"):
            command.add_argument("--games", type=int, default=200)
        if name == "singles":
            command.add_argument("--agents", default="cem,deep",
                                 help="comma-separated: cem, deep, points (after training); "
                                      "other than the default, written to singles_<agents>.json")
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "singles":
            agents = args.agents.split(",")
            unknown = set(agents) - set(_agents())
            if unknown:
                raise ValueError(f"unknown or untrained agents: {sorted(unknown)}")
            path = SINGLES if agents == ["cem", "deep"] else \
                SINGLES.with_name(f"singles_{'_'.join(agents)}.json")
            _write(path, singles(args.games, args.jobs, agents))
            print(f"Wrote {path}")
        elif args.command == "odds-check":
            _write(ODDS_CHECK, odds_check(args.games, args.jobs))
            print(f"Wrote {ODDS_CHECK}")
        elif args.command == "lever-check":
            _write(LEVER_CHECK, lever_check(args.jobs))
            print(f"Wrote {LEVER_CHECK}")
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
