"""Run Experiment 019: spend the rollouts where they pay.

    python -m block_stack_ai.experiment019 dev-check [--jobs N]
    python -m block_stack_ai.experiment019 recheck [--jobs N]
    python -m block_stack_ai.experiment019 evaluate [--jobs N]
    python -m block_stack_ai.experiment019 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment019 summarize RECORD [--jobs N]

017's agent (``commit_rollout``) made most of its gain at levels 39+, where longer
rollouts helped. 019's agent (``late_rollout``) is 017's agent with one or both of:
longer or more commit rollouts from level 39 (``killscreen_rollout_count`` and
``_depth``, native/rollout.hpp), and 016's rollouts at the adjust decision at 29-38 too
(``rollout_to_level`` 38), so the late adjust no longer decides by the plain search.
The numbers stay 015's, not re-tuned.

``dev-check`` plays config.json's variants on the dev seeds, paired against 017's agent,
to choose the held-out one (config.json's ``late``). The held-out baseline is 017's
record: 017's agent is unchanged (019's settings are off by default), and ``evaluate``
plays its first few seeds again to check that the record still matches this build.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment005, experiment009 as e9, experiment011 as e11
from . import experiment012 as e12, experiment013 as e13, experiment016 as e16
from . import experiment017 as e17, native, runner
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "019-late-rollouts"
CONFIG = EXPERIMENT_ROOT / "config.json"
DEV_CHECK = EXPERIMENT_ROOT / "dev_check.json"
RECHECK = EXPERIMENT_ROOT / "recheck.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
BASELINE_RECORD = e17.EXPERIMENT_ROOT / "records" / "run.json.gz"
SCHEMA = "fallgorithm.experiment019.run/1"
LATE_NAMES = ("rollout_to_level", "killscreen_rollout_count", "killscreen_rollout_depth")

_load, _write = e13._load, e13._write


def commit_rollout_params() -> dict[str, Any]:
    """017's agent: 016's agent with 017's chosen commit-rollout settings."""
    return e17.rollout_params() | e17._load(e17.CONFIG)["commit_rollout"]


def check_late(late: Any) -> dict[str, int]:
    """019's settings: some of LATE_NAMES, each changing 017's agent."""
    if not isinstance(late, dict) or not late or not set(late) <= set(LATE_NAMES):
        raise ValueError(f"late must set some of {', '.join(LATE_NAMES)}")
    if late.get("rollout_to_level", 38) != 38 or \
            late.get("killscreen_rollout_count", 1) < 1 or \
            late.get("killscreen_rollout_depth", 1) < 1:
        raise ValueError("late's settings must be rollout_to_level 38 and counts or "
                         "depths of at least 1")
    commit = e17._load(e17.CONFIG)["commit_rollout"]
    if late.get("killscreen_rollout_count") == commit["commit_rollout_count"] or \
            late.get("killscreen_rollout_depth") == commit["commit_rollout_depth"]:
        raise ValueError("late's killscreen settings must differ from 017's commit ones")
    native.resolve(commit_rollout_params() | late)  # whole numbers
    return late


# ---------------------------------------------------------------- dev check

def dev_check(jobs: int, recheck: bool = False) -> dict[str, Any]:
    """Each config.json variant on the dev seeds, paired by seed against 017's agent.
    A diagnostic, not part of the success rule. ``recheck``: config.json's
    ``recheck`` variants on the dev seeds after the first ``dev_check_games``, which
    017's settings were not chosen on (no 017 depth check to match there)."""
    config = _load(CONFIG)
    games = config["dev_check_games"]
    dev = _load(e13.SEEDS)["dev_seeds"]
    seeds = dev[games:2 * games] if recheck else dev[:games]
    ms = config["formats"][0]["reaction_ms"]
    variants = {name: config["dev_check"][name] for name in config["recheck"]} if recheck \
        else config["dev_check"]
    base = e16._load(e16.CONFIG)["rollout"] | e17._load(e17.CONFIG)["commit_rollout"]
    same_game = ("game", "line_cap", "frame_cap", "formats")
    if any(config[key] != e16._load(e16.CONFIG)[key] for key in same_game):
        raise ValueError("016's band_game plays 016's config.json game; 019's must match it")
    # 016's band_game plays fast_deep_params() | its settings with reach_plan_016.
    work = [(name, "rollout", base | check_late(late), seed, ms)
            for name, late in variants.items() for seed in seeds]
    with Pool(jobs) as pool:
        # 017's agent first: stop before the variants if it no longer plays 017's games.
        baseline = pool.map(e16.band_game, [("commit_rollout", "rollout", base, seed, ms)
                                            for seed in seeds], chunksize=1)
        if not recheck and not baseline_matches_017(e16._summary(baseline), len(seeds)):
            raise ValueError("017's agent on this build does not match 017's depth check")
        found = pool.map(e16.band_game, work, chunksize=1) + baseline
    runs = {name: [g for g in found if g["name"] == name]
            for name in [*variants, "commit_rollout"]}
    summaries = {name: e16._summary(games) for name, games in runs.items()}
    return {
        "question": "019's settings on 017's agent, on the dev seeds",
        "seeds": f"Experiment 013's dev seeds {games} to {2 * games - 1}" if recheck else
        f"Experiment 013's first {len(seeds)} dev seeds", "games": len(seeds),
        "versions": runner._record_versions(), "numbers": commit_rollout_params(),
        "variants": variants,
        "runs": summaries,
        "baseline_matches_017": None if recheck else
        baseline_matches_017(summaries["commit_rollout"], len(seeds)),
        "paired": {f"{name} - commit_rollout": {
            "total": e12.paired(games, runs["commit_rollout"]),
            "by_band": e16._band_pairs(games, runs["commit_rollout"])}
            for name, games in runs.items() if name != "commit_rollout"},
    }


def baseline_matches_017(summary: dict[str, Any], games: int) -> bool:
    """Whether 017's agent on this build scores exactly as in 017's own depth check (its
    chosen variant, on the same dev seeds), every band."""
    check = e17._load(e17.DEPTH_CHECK)
    chosen = [name for name, commit in check["variants"].items()
              if commit == e17._load(e17.CONFIG)["commit_rollout"]]
    if check["games"] != games or len(chosen) != 1:
        return False
    recorded = check["runs"][chosen[0]]
    return all(summary[key] == recorded[key]
               for key in ("mean_score", "mean_lines", "line_cap_share", "score_by_band"))


# ---------------------------------------------------------------- evaluate / verify

def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    check_late(config["late"])
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats", "late",
                                         "identity_check_games")} | {
        "commit_rollout_params": commit_rollout_params(), "seeds": e13._heldout_seeds()}


def _baseline() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """017's record and its commit_rollout episodes, in its seed order."""
    record = _load(BASELINE_RECORD)
    return record, [e for e in record["episodes"] if e["agent"] == "commit_rollout"]


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game by 019's agent (``late_rollout``) or, for the identity check,
    017's (``commit_rollout``): 016's ``play_native`` with these numbers."""
    agent, seed, config = job
    numbers = config["commit_rollout_params"] | (config["late"]
                                                 if agent == "late_rollout" else {})
    # 016's play_native adds its config's "rollout" to "fast_deep_params" for "rollout".
    episode = e16.play_native(("rollout", seed, config | {"fast_deep_params": numbers,
                                                          "rollout": {}}))
    episode["agent"] = agent
    return episode


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    seeds = config["seeds"]
    return [("late_rollout", seed, config) for seed in seeds] + \
        [("commit_rollout", seed, config) for seed in seeds[:config["identity_check_games"]]]


def identity_problems(found: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> list[str]:
    """017's agent replayed on this build against 017's record, input by input."""
    return [problem.replace("016's", "017's")
            for problem in e17.identity_problems(found, baseline)]


def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """The launcher's new game: 019's agent in format ``fmt``."""
    _, fmt, seed, config = job
    return play_native(("late_rollout", seed,
                        config | {"commit_rollout_params": commit_rollout_params(),
                                  "late": check_late(_load(CONFIG)["late"]),
                                  "formats": [fmt]}))


def evaluate(jobs: int) -> Path:
    if not PREDECLARED.exists() or not e13._committed(PREDECLARED) or \
            not e13._committed(CONFIG) or not DEV_CHECK.exists() or \
            not e13._committed(DEV_CHECK):
        raise ValueError("held-out games wait for a committed predeclared.md, config.json "
                         "and dev check")
    if _load(DEV_CHECK).get("baseline_matches_017") is not True:
        raise ValueError("the dev check's 017 baseline did not match 017's own depth check")
    config = record_configuration()
    baseline_record, baseline = _baseline()
    if baseline_record["configuration"]["seeds"] != config["seeds"] or \
            baseline_record["configuration"]["rollout_params"] | \
            baseline_record["configuration"]["commit_rollout"] != config["commit_rollout_params"]:
        raise ValueError("017's record is not 017's agent on 012's held-out seeds")
    tick = time.perf_counter()
    work = _work(config)
    held_out = [job for job in work if job[0] == "late_rollout"]
    identity = [job for job in work if job[0] == "commit_rollout"]
    with Pool(jobs) as pool:
        # 017's agent first: no held-out game of 019's is played on a build that differs.
        checked = pool.map(play_native, identity, chunksize=1)
        problems = identity_problems(checked, baseline)
        if problems:
            raise ValueError(f"017's record does not match this build: {problems[:3]}")
        episodes = pool.map(play_native, held_out, chunksize=1) + checked
    record = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "versions": runner._record_versions(),
        "engine_fingerprint": experiment005.engine_fingerprint()["combined_sha256"],
        "sources": e11.sources(), "workers": jobs,
        "baseline_record": {"path": str(BASELINE_RECORD.relative_to(runner.PROJECT_ROOT)),
                            "sha256": hashlib.sha256(BASELINE_RECORD.read_bytes()).hexdigest()},
        "wall_seconds": round(time.perf_counter() - tick, 1), "episodes": episodes,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-019"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    """Replays the record's games and 017's baseline games on the engine, and checks the
    identity games against 017's record."""
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 019 record"]
    config = record["configuration"]
    if [(e["agent"], e["seed"]) for e in record["episodes"]] != \
            [(agent, seed) for agent, seed, _ in _work(config)]:
        return ["episodes do not match the configured runs and seeds"]
    if hashlib.sha256(BASELINE_RECORD.read_bytes()).hexdigest() != \
            record["baseline_record"]["sha256"]:
        return [f"{BASELINE_RECORD} is not the baseline record this run was checked against"]
    baseline_record, baseline = _baseline()
    if [e["seed"] for e in baseline] != config["seeds"]:
        return ["017's record is not on the configured seeds"]
    problems = identity_problems(
        [e for e in record["episodes"] if e["agent"] == "commit_rollout"], baseline)
    jobs_list = [(e, config) for e in record["episodes"]] + \
        [(e, baseline_record["configuration"]) for e in baseline]
    with Pool(jobs) as pool:
        found = pool.starmap(e9._replay, jobs_list, chunksize=4)
    return problems + [problem for problems in found for problem in problems]


# ---------------------------------------------------------------- summarize

def summarize(path: Path, jobs: int = 30) -> dict[str, Any]:
    problems = verify(path, jobs)
    if problems:
        raise ValueError(f"{path} does not verify: {problems[:3]}")
    record = _load(path)
    config = record["configuration"]
    if config["commit_rollout_params"] != commit_rollout_params() or \
            config["late"] != _load(CONFIG)["late"]:
        raise ValueError("the record's numbers are not 017's agent and config.json's "
                         "late settings")
    _, baseline = _baseline()
    runs = {"late_rollout": e12._rows([e for e in record["episodes"]
                                       if e["agent"] == "late_rollout"]),
            "commit_rollout": e12._rows(baseline)}
    main_pair = e12.paired(runs["late_rollout"], runs["commit_rollout"])
    seconds = {agent: round(sum(r["decision_seconds"] for r in rows) / len(rows), 2)
               for agent, rows in runs.items()}
    return {
        "experiment": "019-late-rollouts",
        "question": ("Does 017's agent with 019's late rollout settings beat 017's agent on "
                     "012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "baseline_record": record["baseline_record"],
        "identity_check": f"017's agent replayed input for input on the first "
                          f"{config['identity_check_games']} held-out seeds",
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "late": config["late"], "params": config["commit_rollout_params"],
        "heldout": {"games": len(runs["late_rollout"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_late_rollout_minus_commit_rollout": main_pair,
                    "seconds_per_game": seconds},
        "dev_check": _load(DEV_CHECK)["paired"],
        "success_rule": ("95% CI of the paired mean score difference (late_rollout minus "
                         "commit_rollout) on 012's 1,000 held-out seeds entirely above 0"),
        "success": e17.success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment019")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("dev-check", "019's settings on dev seeds"),
                       ("recheck", "the closest settings on the next dev seeds"),
                       ("evaluate", "play late_rollout on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "dev-check":
            _write(DEV_CHECK, dev_check(args.jobs))
            print(f"Wrote {DEV_CHECK}")
        elif args.command == "recheck":
            _write(RECHECK, dev_check(args.jobs, recheck=True))
            print(f"Wrote {RECHECK}")
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
