"""Run, verify, summarise and autopsy Experiment 010 (complete reachability).

    python -m block_stack_ai.experiment010 evaluate [--jobs N]
    python -m block_stack_ai.experiment010 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment010 summarize RECORD [--jobs N]
    python -m block_stack_ai.experiment010 autopsy [--jobs N]

The question: does finding *every* placement the tap and reaction limits allow
(:mod:`block_stack_ai.reach`) raise ``tuned_plan``'s score and survival, with
Experiment 009's learned numbers unchanged? ``evaluate`` plays
:class:`block_stack_ai.reachplan.ReachAgent` on Experiment 008's held-out seeds (a
prefix of them when ``config.json`` says ``seed_count``) at 30 Hz / 300 ms.
``summarize`` compares it, seed by seed, with Experiment 009's retained record.
``autopsy`` replays some of 009's games near their deaths and asks what the full
search would have found. Helpers that do not change (statistics, replaying) are
imported from :mod:`block_stack_ai.experiment009`; ``_play`` is a copy of its
``_play`` with the new agent and a decision timer.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment006, experiment008 as e8, experiment009 as e9, runner
from . import limits as limits_model
from . import reach, reachplan, tunedplan, wellplan
from .engine import EngineError, create_game
from .limits import Flight, Limits
from .pathaware import column_features, grid_columns, settle_columns

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "010-complete-reach"
CONFIG = EXPERIMENT_ROOT / "config.json"
RESULT = EXPERIMENT_ROOT / "result.json"
AUTOPSY = EXPERIMENT_ROOT / "autopsy.json"
FINAL_PARAMS = e9.FINAL_PARAMS  # Experiment 009's learned numbers, unchanged
BASELINE_RECORD = e9.EXPERIMENT_ROOT / "records" / "run.json.gz"
SCHEMA = "fallgorithm.experiment010.run/1"
AUTOPSY_GAMES, AUTOPSY_WINDOW = 30, 10
RATE_LEVELS = {"level_29": lambda level: level == 29, "level_39_plus": lambda level: level >= 39}
TIMING_GAMES, TIMING_STRIDE = 12, 20


def _load(path: Path) -> Any:
    return experiment006._load(path)


# ---------------------------------------------------------------- playing

def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """One game like 009's, with ``reach_plan``; the result also holds the time spent deciding."""
    index, fmt, seed, config = job
    agent = reachplan.ReachAgent(Limits(fmt["tap_hz"], fmt["reaction_ms"]), config["params"])
    inputs = bytearray()
    marks: dict[int, int | None] = {level: None for level in e8.LEVEL_MARKS}
    sizes = dict.fromkeys(e9.CLEAR_NAMES.values(), 0)
    spent = 0.0
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
        state = game.state
        while (reason := e8._stop_reason(state, len(inputs), config)) is None:
            tick = time.perf_counter()
            mask = agent.act(state)
            spent += time.perf_counter() - tick
            before = state.lines
            state, _ = game.step(mask)
            inputs.append(mask)
            e9._tally(state, before, sizes, marks)
        result = e8._result(state, reason, marks, game)
    result.update(pieces=agent.pieces, adjusts=agent.adjusts, switches=agent.switches,
                  clear_sizes=sizes, decision_seconds=round(spent, 2))
    return {"format": index, "seed": seed, "initial_state_hash": initial_hash,
            "inputs": base64.b64encode(bytes(inputs)).decode("ascii"), "result": result}


def heldout_seeds(config: dict[str, Any] | None = None) -> list[int]:
    """008's held-out seeds, or the fixed prefix of them named by ``seed_count``."""
    config = config or _load(CONFIG)
    seeds = _load(e8.CONFIG)["seeds"]
    return seeds[:config.get("seed_count", len(seeds))]


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "agent", "formats")} | {
        "params": _load(FINAL_PARAMS)["resolved"], "seeds": heldout_seeds(config)}


def evaluate(jobs: int) -> Path:
    config = record_configuration()
    work = [(0, config["formats"][0], seed, config) for seed in config["seeds"]]
    with Pool(jobs) as pool:
        episodes = []
        for episode in pool.imap(_play, work, chunksize=1):
            episodes.append(episode)
            result = episode["result"]
            print(f"{len(episodes)}/{len(work)} seed {episode['seed']}: {result['lines']} lines, "
                  f"score {result['score']}, {result['stopping_reason']}, "
                  f"{result['decision_seconds']}s deciding", file=sys.stderr, flush=True)
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e8._sources(), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-010"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 010 record"]
    config = record["configuration"]
    if [e["seed"] for e in record["episodes"]] != config["seeds"]:
        return ["episodes do not match the configured seeds"]
    with Pool(jobs) as pool:
        found = pool.starmap(e9._replay, [(e, config) for e in record["episodes"]], chunksize=1)
    return [problem for problems in found for problem in problems]


# ---------------------------------------------------------------- replaying positions

def spawns(episode: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """The board and pieces at every piece spawn of a recorded game, in order."""
    inputs = base64.b64decode(episode["inputs"])
    found, seen = [], None
    with create_game(**config["game"], seed=episode["seed"]) as game:
        state = game.state
        for action in (*inputs, None):
            if state.phase == "active" and not state.terminal and state.piece_count != seen:
                seen = state.piece_count
                found.append({"columns": grid_columns(wellplan.visible_grid(state.board)),
                              "piece": state.current_piece, "next_piece": state.next_piece,
                              "level": state.level, "lines": state.lines})
            if action is not None:
                state, _ = game.step(action)
    return found


def _options(columns: tuple[int, ...], piece: str, level: int, ruleset: str,
             limits: Limits, model: Any) -> list[Any]:
    period, rows = limits_model.gravity(level, ruleset)
    return list(model.reachable(columns, piece, Flight(), period=period, rows=rows,
                                limits=limits))


def placement_counts(episode: dict[str, Any], config: dict[str, Any]) -> dict[str, list[int]]:
    """Per level band: ``[pieces, placements by limits.py, placements by reach.py]``."""
    limits = Limits(config["formats"][0]["tap_hz"], config["formats"][0]["reaction_ms"])
    totals = {name: [0, 0, 0] for name in RATE_LEVELS}
    for spawn in spawns(episode, config):
        for name, in_band in RATE_LEVELS.items():
            if in_band(spawn["level"]):
                args = (spawn["columns"], spawn["piece"], spawn["level"],
                        config["game"]["ruleset"], limits)
                totals[name][0] += 1
                totals[name][1] += len(_options(*args, limits_model))
                totals[name][2] += len(_options(*args, reach))
    return totals


def _rates(per_game: list[dict[str, list[int]]]) -> dict[str, Any]:
    out = {}
    for name in RATE_LEVELS:
        pieces = sum(game[name][0] for game in per_game)
        old = sum(game[name][1] for game in per_game)
        new = sum(game[name][2] for game in per_game)
        out[name] = {"pieces": pieces,
                     "limits_mean": round(old / pieces, 2) if pieces else None,
                     "reach_mean": round(new / pieces, 2) if pieces else None}
    return out


def decision_time(episodes: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """Time both searches, alone on the machine, on the same sampled positions.

    A decision is one piece's commit search (preview unknown) plus its adjust search
    (preview known), both from a fresh piece. The reach cache is emptied before each.
    """
    params = config["params"]
    limits = Limits(config["formats"][0]["tap_hz"], config["formats"][0]["reaction_ms"])
    ruleset = config["game"]["ruleset"]
    bands = {"level_18_28": lambda v: v < 29, "level_29_38": lambda v: 29 <= v < 39,
             "level_39_plus": lambda v: v >= 39}
    seconds = {band: {"limits": [], "reach": []} for band in bands}
    for episode in episodes[:TIMING_GAMES]:
        for spawn in spawns(episode, config)[::TIMING_STRIDE]:
            for band, in_band in bands.items():
                if not in_band(spawn["level"]):
                    continue
                for name, search in (("limits", tunedplan.search), ("reach", reachplan.search)):
                    reach._cached_search.cache_clear()
                    tick = time.perf_counter()
                    for preview in (None, spawn["next_piece"]):
                        search(spawn["columns"], spawn["piece"], preview, flight=Flight(),
                               drought=0, level=spawn["level"], lines=spawn["lines"],
                               start_level=config["game"]["start_level"], ruleset=ruleset,
                               limits=limits, params=params)
                    seconds[band][name].append(time.perf_counter() - tick)
    return {band: {"positions": len(values["limits"]),
                   "tuned_plan_ms": round(1000 * sum(values["limits"]) / len(values["limits"]), 1),
                   "reach_plan_ms": round(1000 * sum(values["reach"]) / len(values["reach"]), 1)}
            for band, values in seconds.items() if values["limits"]}


# ---------------------------------------------------------------- summarize

def success(ci: dict[str, float]) -> bool:
    """The predeclared rule: the paired mean-score difference's 95% interval is wholly above 0."""
    return ci["ci95_low"] > 0


def _rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"seed": e["seed"], **e["result"]} for e in record["episodes"]]


def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    record = _load(path)
    config = record["configuration"]
    rows = _rows(record)
    base = _load(BASELINE_RECORD)
    by_seed = {row["seed"]: row for row in _rows(base)}
    missing = set(config["seeds"]) - set(by_seed)
    if missing:
        raise ValueError(f"009 has no games for seeds {sorted(missing)}")
    base_rows = [by_seed[seed] for seed in config["seeds"]]
    paired = {name: [row[name] - by_seed[row["seed"]][name] for row in rows]
              for name in ("score", "lines")}
    ci = e9.bootstrap_mean_ci(paired["score"])
    wanted = set(config["seeds"])
    base_episodes = [e for e in base["episodes"] if e["seed"] in wanted]
    with Pool(jobs) as pool:
        new_counts = pool.starmap(placement_counts, [(e, config) for e in record["episodes"]],
                                  chunksize=1)
        old_counts = pool.starmap(placement_counts, [(e, base["configuration"])
                                                     for e in base_episodes], chunksize=1)
    pieces = sum(row["pieces"] for row in rows)
    return {
        "experiment": "010-complete-reach",
        "question": ("Does a complete reachability search raise tuned_plan's score and survival "
                     "on the same held-out seeds, with Experiment 009's params unchanged?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "params": config["params"], "seeds": len(config["seeds"]),
        "reach_plan": e9.metrics(rows), "tuned_plan_009": e9.metrics(base_rows),
        "paired_score_difference": ci,
        "paired_lines_difference": e9.bootstrap_mean_ci(paired["lines"]),
        "paired_score_wins": {"reach_higher": sum(d > 0 for d in paired["score"]),
                              "tuned_higher": sum(d < 0 for d in paired["score"]),
                              "equal": sum(d == 0 for d in paired["score"])},
        "success_rule": "95% CI of the paired mean score difference entirely above 0",
        "success": success(ci),
        "reachable_placements_per_piece": {
            "on_reach_plan_boards": _rates(new_counts),
            "on_tuned_plan_boards": _rates(old_counts)},
        "decision_seconds_per_piece_under_load": round(
            sum(row["decision_seconds"] for row in rows) / pieces, 4),
        "decision_ms_alone": decision_time(record["episodes"], config),
        "episodes": rows,
    }


# ---------------------------------------------------------------- autopsy

def _best_height(options: list[Any], columns: tuple[int, ...], piece: str) -> int | None:
    """The lowest stack any of the options leaves, or ``None`` when there is none."""
    heights = [wellplan.stack_height(settle_columns(columns, piece, r.orientation, r.x, r.y)[0])
               for r in options]
    return min(heights) if heights else None


def autopsy_game(episode: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """The last pieces of a recorded game: what each model could reach at each spawn."""
    limits = Limits(config["formats"][0]["tap_hz"], config["formats"][0]["reaction_ms"])
    ruleset = config["game"]["ruleset"]
    last = spawns(episode, config)[-AUTOPSY_WINDOW:]
    rows = []
    for spawn in last:
        columns, piece = spawn["columns"], spawn["piece"]
        old = _options(columns, piece, spawn["level"], ruleset, limits, limits_model)
        new = _options(columns, piece, spawn["level"], ruleset, limits, reach)
        old_keys = {(r.orientation, r.x, r.y) for r in old}
        extra = [r for r in new if (r.orientation, r.x, r.y) not in old_keys]
        old_best, new_best = _best_height(old, columns, piece), _best_height(new, columns, piece)
        rows.append({
            "piece": piece, "level": spawn["level"],
            "stack_height": wellplan.stack_height(columns),
            "holes": column_features(columns).holes,
            "limits_placements": len(old), "reach_placements": len(new),
            "extra_placements": len(extra),
            "lowest_stack_limits": old_best, "lowest_stack_reach": new_best,
            "rescue": bool(new) and not old,
            "lower_stack_with_reach": new_best is not None and (old_best is None
                                                               or new_best < old_best)})
    return {"seed": episode["seed"], "lines": episode["result"]["lines"],
            "death": rows[-1], "window": rows}


def autopsy(jobs: int) -> dict[str, Any]:
    base = _load(BASELINE_RECORD)
    config = base["configuration"]
    episodes = base["episodes"][::len(base["episodes"]) // AUTOPSY_GAMES][:AUTOPSY_GAMES]
    with Pool(jobs) as pool:
        games = pool.starmap(autopsy_game, [(e, config) for e in episodes], chunksize=1)
    deaths = [g["death"] for g in games]
    window = [row for g in games for row in g["window"]]

    def count(rows: list[dict[str, Any]], field: str) -> int:
        return sum(bool(row[field]) for row in rows)

    return {
        "source": "every 10th game of Experiment 009's record, last "
                  f"{AUTOPSY_WINDOW} spawns of each",
        "games": len(games),
        "death_piece": {
            "mean_level": round(sum(d["level"] for d in deaths) / len(deaths), 1),
            "mean_stack_height": round(sum(d["stack_height"] for d in deaths) / len(deaths), 1),
            "mean_holes": round(sum(d["holes"] for d in deaths) / len(deaths), 1),
            "mean_limits_placements": round(sum(d["limits_placements"] for d in deaths) / len(deaths), 2),
            "mean_reach_placements": round(sum(d["reach_placements"] for d in deaths) / len(deaths), 2),
            "with_extra_placements": count(deaths, "extra_placements"),
            "limits_had_none_reach_had_some": count(deaths, "rescue"),
            "reach_leaves_a_lower_stack": count(deaths, "lower_stack_with_reach")},
        "last_window": {
            "pieces": len(window),
            "mean_limits_placements": round(sum(r["limits_placements"] for r in window) / len(window), 2),
            "mean_reach_placements": round(sum(r["reach_placements"] for r in window) / len(window), 2),
            "with_extra_placements": count(window, "extra_placements"),
            "reach_leaves_a_lower_stack": count(window, "lower_stack_with_reach")},
        "games_detail": games,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment010")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("evaluate", "play reach_plan on the held-out seeds"),
                       ("verify", "replay a record on the native engine"),
                       ("summarize", "write result.json from a record"),
                       ("autopsy", "write autopsy.json from Experiment 009's record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            print(f"Record: {evaluate(args.jobs)}")
        elif args.command == "verify":
            problems = verify(args.record.resolve(), args.jobs)
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print(f"Verified: {args.record}")
        elif args.command == "summarize":
            e9._write(RESULT, summarize(args.record.resolve(), args.jobs))
            print(f"Wrote {RESULT}")
        else:
            e9._write(AUTOPSY, autopsy(args.jobs))
            print(f"Wrote {AUTOPSY}")
    except (EngineError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
