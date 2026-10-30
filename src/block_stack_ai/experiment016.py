"""Run Experiment 016: rollout re-ranking at levels 18-28.

    python -m block_stack_ai.experiment016 reaction [--games N] [--jobs N]
    python -m block_stack_ai.experiment016 depth-check [--jobs N]
    python -m block_stack_ai.experiment016 evaluate [--jobs N]
    python -m block_stack_ai.experiment016 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment016 summarize RECORD [--jobs N]

015's agent (``fast_deep``) picks each piece by a two-to-three-ply search over a hand
weighted board value. 016's agent (``rollout``, ``reach_plan_016``) is the same agent
with native/rollout.hpp on top: at the decision with the preview known, from level 18
to 28, it plays the search's best few placements forward with sampled pieces, each
rollout placed by the same search, and keeps the placement whose rollouts are worth
the most. The numbers are 015's final ones, not re-tuned.

``reaction`` (step 0) plays 015's agent on the dev seeds at several reaction times and
credits the score to level bands: what the 300 ms preview delay costs, band by band.
``depth-check`` plays config.json's rollout settings on the dev seeds, paired against
015's agent, to choose the held-out ones.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment009 as e9, experiment011 as e11
from . import experiment012 as e12, experiment013 as e13, experiment015 as e15, native, runner
from .engine import EngineError, create_game
from .limits import Limits

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "016-rollouts"
CONFIG = EXPERIMENT_ROOT / "config.json"
REACTION = EXPERIMENT_ROOT / "reaction.json"
DEPTH_CHECK = EXPERIMENT_ROOT / "depth_check.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
SCHEMA = "fallgorithm.experiment016.run/1"
KINDS = {"fast_deep": e15.AGENT, "rollout": "reach_plan_016"}
BANDS = e15.BANDS

_load, _write = e13._load, e13._write


def fast_deep_params() -> dict[str, Any]:
    """015's final numbers with its commit ply: the baseline, and the rollouts' search."""
    return _load(e15.FINAL_PARAMS)["resolved"] | e15.search()


def _numbers(agent: str, rollout: dict[str, int]) -> dict[str, Any]:
    return fast_deep_params() | (rollout if agent == "rollout" else {})


# ---------------------------------------------------------------- dev games by band

def band_game(job: tuple[str, str, dict[str, int], int, int]) -> dict[str, Any]:
    """One dev game by the C++ agent, replayed on the Python binding, its score credited
    to the band of the level at each piece's spawn (015's ``bands_game`` rule). ``name``
    labels the run the game belongs to."""
    name, agent, rollout, seed, reaction_ms = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played = native.play_game_ex(KINDS[agent], config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=Limits(config["formats"][0]["tap_hz"], reaction_ms),
                                 params=native.params(_numbers(agent, rollout)))
    seconds = time.perf_counter() - tick
    score: Counter[str] = Counter()
    count, band = -1, BANDS[0]
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in played["inputs"]:
            if state.phase == "active" and state.piece_count != count:
                count, band = state.piece_count, e15._band(state.level)
            before = state.score
            state, _ = game.step(mask)
            score[band] += state.score - before
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"{agent} seed {seed}: the replay does not match the C++ game")
    return {"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "bands": {band: score[band] for band in BANDS}, "seconds": seconds}


def _summary(games: list[dict[str, Any]]) -> dict[str, Any]:
    return e13._scores(games) | {
        "line_cap_share": round(sum(g["lines"] >= _load(CONFIG)["line_cap"] for g in games) /
                                len(games), 4),
        "score_by_band": {band: round(sum(g["bands"][band] for g in games) / len(games))
                          for band in BANDS},
        "seconds_per_game": round(sum(g["seconds"] for g in games) / len(games), 2)}


def _band_pairs(games: list[dict[str, Any]], base: list[dict[str, Any]]) -> dict[str, Any]:
    return {band: e9.bootstrap_mean_ci([g["bands"][band] - b["bands"][band]
                                        for g, b in zip(games, base)], seed=e12.BOOTSTRAP_SEED)
            for band in BANDS}


def reaction(games: int, jobs: int) -> dict[str, Any]:
    """015's agent at each config.json reaction time on the first ``games`` dev seeds."""
    config = _load(CONFIG)
    seeds = _load(e13.SEEDS)["dev_seeds"][:games]
    if not seeds:
        raise ValueError("--games must be at least 1")
    times = config["reaction_check_ms"]
    with Pool(jobs) as pool:
        runs = {ms: pool.map(band_game, [(str(ms), "fast_deep", {}, seed, ms)
                                         for seed in seeds]) for ms in times}
    base = runs[config["formats"][0]["reaction_ms"]]
    return {
        "question": "What does the preview delay cost 015's agent, band by band (dev seeds)?",
        "seeds": f"Experiment 013's first {len(seeds)} dev seeds", "games": len(seeds),
        "versions": runner._record_versions(), "numbers": fast_deep_params(),
        "runs": {str(ms): _summary(games) for ms, games in runs.items()},
        "paired_vs_benchmark": {str(ms): {"total": e12.paired(games, base),
                                          "by_band": _band_pairs(games, base)}
                                for ms, games in runs.items() if games is not base},
    }


def depth_check(jobs: int) -> dict[str, Any]:
    """Each config.json rollout variant on the dev seeds, paired by seed against 015's
    agent. A diagnostic, not part of the success rule."""
    config = _load(CONFIG)
    seeds = _load(e13.SEEDS)["dev_seeds"][:config["depth_check_games"]]
    ms = config["formats"][0]["reaction_ms"]
    variants = config["depth_check"]
    work = [(name, "rollout", rollout, seed, ms) for name, rollout in variants.items()
            for seed in seeds] + [("fast_deep", "fast_deep", {}, seed, ms) for seed in seeds]
    with Pool(jobs) as pool:
        found = pool.map(band_game, work, chunksize=1)
    runs = {name: [g for g in found if g["name"] == name] for name in [*variants, "fast_deep"]}
    base = runs["fast_deep"]
    games = len(seeds)
    return {
        "question": "Rollout settings on 015's numbers, on the dev seeds",
        "seeds": f"Experiment 013's first {games} dev seeds", "games": games,
        "versions": runner._record_versions(), "variants": variants,
        "runs": {name: _summary(games) for name, games in runs.items()},
        "paired": {f"{name} - fast_deep": {"total": e12.paired(games, base),
                                           "by_band": _band_pairs(games, base)}
                   for name, games in runs.items() if name != "fast_deep"},
    }


# ---------------------------------------------------------------- evaluate / verify

RUNS = ("rollout", "fast_deep")  # record order, both on 012's held-out seeds


ROLLOUT_NAMES = ("rollout_from_level", "rollout_to_level", "rollout_beam", "rollout_count",
                 "rollout_depth", "rollout_death")


def check_rollout(rollout: Any) -> dict[str, int]:
    """config.json's chosen settings: all six, and rollouts that actually run."""
    if not isinstance(rollout, dict) or set(rollout) != set(ROLLOUT_NAMES):
        raise ValueError(f"config.json's rollout must set exactly {', '.join(ROLLOUT_NAMES)}")
    native.resolve(fast_deep_params() | rollout)  # whole numbers, in range
    if rollout["rollout_beam"] < 2 or rollout["rollout_count"] < 1 or \
            rollout["rollout_depth"] < 1 or \
            rollout["rollout_from_level"] > rollout["rollout_to_level"]:
        raise ValueError("config.json's rollout settings leave the rollouts off")
    return rollout


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    check_rollout(config["rollout"])
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats",
                                         "rollout")} | {
        "fast_deep_params": fast_deep_params(), "seeds": e13._heldout_seeds(),
        "runs": list(RUNS)}


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    return [(agent, seed, config) for agent in config["runs"] for seed in config["seeds"]]


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game (015's ``play_native`` for 016's agents): played by the C++,
    replayed on the Python binding, the counters checked against the replay."""
    agent, seed, config = job
    with create_game(**config["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    numbers = config["fast_deep_params"] | (config["rollout"] if agent == "rollout" else {})
    tick = time.perf_counter()
    played = native.play_game_ex(KINDS[agent], config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=e13._limits(config), params=native.params(numbers))
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
    if not PREDECLARED.exists() or not e13._committed(PREDECLARED) or \
            not e13._committed(CONFIG) or not DEPTH_CHECK.exists():
        raise ValueError("held-out games wait for a committed predeclared.md and config.json "
                         "and the depth check")
    config = record_configuration()
    tick = time.perf_counter()
    with Pool(jobs) as pool:
        # The rollout games are the slow ones; one at a time keeps the workers busy.
        episodes = pool.map(play_native, _work(config), chunksize=1)
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e11.sources(), "workers": jobs,
        "wall_seconds": round(time.perf_counter() - tick, 1), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-016"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 016 record"]
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
    if config["fast_deep_params"] != fast_deep_params() or \
            config["rollout"] != _load(CONFIG)["rollout"]:
        raise ValueError("the record's numbers are not 015's final ones and config.json's "
                         "rollout settings")
    runs = {agent: e12._rows([e for e in record["episodes"] if e["agent"] == agent])
            for agent in RUNS}
    main_pair = e12.paired(runs["rollout"], runs["fast_deep"])
    seconds = {agent: round(sum(r["decision_seconds"] for r in rows) / len(rows), 2)
               for agent, rows in runs.items()}
    return {
        "experiment": "016-rollouts",
        "question": ("Does 015's agent with rollout re-ranking at levels 18-28 beat 015's "
                     "agent on 012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "rollout": config["rollout"], "params": config["fast_deep_params"],
        "heldout": {"games": len(runs["rollout"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_rollout_minus_fast_deep": main_pair,
                    "seconds_per_game": seconds},
        "depth_check": _load(DEPTH_CHECK)["paired"],
        "success_rule": ("95% CI of the paired mean score difference (rollout minus fast_deep) "
                         "on 012's 1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment016")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("reaction", "015's agent at several reaction times (dev seeds)"),
                       ("depth-check", "the rollout settings on dev seeds"),
                       ("evaluate", "play rollout and fast_deep on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        if name == "reaction":
            command.add_argument("--games", type=int, default=200)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "reaction":
            _write(REACTION, reaction(args.games, args.jobs))
            print(f"Wrote {REACTION}")
        elif args.command == "depth-check":
            _write(DEPTH_CHECK, depth_check(args.jobs))
            print(f"Wrote {DEPTH_CHECK}")
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
