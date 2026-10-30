"""Run Experiment 017: rollout re-ranking at the commit decision, from level 29.

    python -m block_stack_ai.experiment017 depth-check [--jobs N]
    python -m block_stack_ai.experiment017 evaluate [--jobs N]
    python -m block_stack_ai.experiment017 verify RECORD [--jobs N]
    python -m block_stack_ai.experiment017 summarize RECORD [--jobs N]

016's agent (``rollout``) re-ranks its search's best placements by short sampled
rollouts, but only at the decision with the preview known. From level 29 the piece
usually locks before the 300 ms reaction frame, so the commit search (preview not known)
decides alone. 017's agent (``commit_rollout``) is 016's agent with the same re-ranking
at the commit decision too: the commit search's best placements, played forward with
the unknown preview drawn first (NES odds after the current piece), then as in 016.
The numbers are 015's final ones with 016's rollout settings, not re-tuned.

``depth-check`` plays config.json's commit-rollout variants on the dev seeds, paired
against 016's agent, to choose the held-out ones. The held-out baseline is 016's record:
016's agent is unchanged (the commit rollouts are off by default), and ``evaluate``
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
from . import experiment012 as e12, experiment013 as e13, experiment016 as e16, native, runner
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "017-commit-rollouts"
CONFIG = EXPERIMENT_ROOT / "config.json"
DEPTH_CHECK = EXPERIMENT_ROOT / "depth_check.json"
RESULT = EXPERIMENT_ROOT / "result.json"
PREDECLARED = EXPERIMENT_ROOT / "predeclared.md"
BASELINE_RECORD = e16.EXPERIMENT_ROOT / "records" / "run.json.gz"
SCHEMA = "fallgorithm.experiment017.run/1"
AGENT = "reach_plan_016"  # both agents; 017's settings switch the commit rollouts on
COMMIT_NAMES = ("commit_rollout_from_level", "commit_rollout_to_level", "commit_rollout_beam",
                "commit_rollout_count", "commit_rollout_depth")

_load, _write = e13._load, e13._write


def rollout_params() -> dict[str, Any]:
    """016's agent: 015's final numbers with its commit ply and 016's rollout settings."""
    return e16.fast_deep_params() | e16._load(e16.CONFIG)["rollout"]


# ---------------------------------------------------------------- dev depth check

def depth_check(jobs: int) -> dict[str, Any]:
    """Each config.json commit-rollout variant on the dev seeds, paired by seed against
    016's agent. A diagnostic, not part of the success rule."""
    config = _load(CONFIG)
    seeds = _load(e13.SEEDS)["dev_seeds"][:config["depth_check_games"]]
    ms = config["formats"][0]["reaction_ms"]
    variants = config["depth_check"]
    base = e16._load(e16.CONFIG)["rollout"]
    same_game = ("game", "line_cap", "frame_cap", "formats")
    if any(config[key] != e16._load(e16.CONFIG)[key] for key in same_game):
        raise ValueError("016's band_game plays 016's config.json game; 017's must match it")
    # 016's band_game plays fast_deep_params() | its settings with reach_plan_016.
    work = [(name, "rollout", base | check_commit(commit), seed, ms)
            for name, commit in variants.items() for seed in seeds] + \
        [("rollout", "rollout", base, seed, ms) for seed in seeds]
    with Pool(jobs) as pool:
        found = pool.map(e16.band_game, work, chunksize=1)
    runs = {name: [g for g in found if g["name"] == name] for name in [*variants, "rollout"]}
    games = len(seeds)
    summaries = {name: e16._summary(games) for name, games in runs.items()}
    return {
        "question": "Commit-rollout settings on 016's agent, on the dev seeds",
        "seeds": f"Experiment 013's first {games} dev seeds", "games": games,
        "versions": runner._record_versions(), "numbers": rollout_params(),
        "variants": variants,
        "runs": summaries,
        "baseline_matches_016": baseline_matches_016(summaries["rollout"], games),
        "paired": {f"{name} - rollout": {"total": e12.paired(games, runs["rollout"]),
                                         "by_band": e16._band_pairs(games, runs["rollout"])}
                   for name, games in runs.items() if name != "rollout"},
    }


def baseline_matches_016(summary: dict[str, Any], games: int) -> bool:
    """Whether 016's agent on this build scores exactly as in 016's own depth check
    (its chosen variant, on the same dev seeds): every band, so levels 29+ too."""
    check = e16._load(e16.DEPTH_CHECK)
    chosen = [name for name, rollout in check["variants"].items()
              if rollout == e16._load(e16.CONFIG)["rollout"]]
    if check["games"] != games or len(chosen) != 1:
        return False
    recorded = check["runs"][chosen[0]]
    return all(summary[key] == recorded[key]
               for key in ("mean_score", "mean_lines", "line_cap_share", "score_by_band"))


# ---------------------------------------------------------------- evaluate / verify

def check_commit(commit: Any) -> dict[str, int]:
    """Commit-rollout settings: all five, and rollouts that actually run."""
    if not isinstance(commit, dict) or set(commit) != set(COMMIT_NAMES):
        raise ValueError(f"commit_rollout must set exactly {', '.join(COMMIT_NAMES)}")
    native.resolve(rollout_params() | commit)  # whole numbers, in range
    if commit["commit_rollout_beam"] < 2 or commit["commit_rollout_count"] < 1 or \
            commit["commit_rollout_depth"] < 1 or \
            commit["commit_rollout_from_level"] > commit["commit_rollout_to_level"]:
        raise ValueError("the commit_rollout settings leave the commit rollouts off")
    return commit


def record_configuration() -> dict[str, Any]:
    config = _load(CONFIG)
    check_commit(config["commit_rollout"])
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats",
                                         "commit_rollout", "identity_check_games")} | {
        "rollout_params": rollout_params(), "seeds": e13._heldout_seeds()}


def _baseline() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """016's record and its rollout episodes, in its seed order."""
    record = _load(BASELINE_RECORD)
    return record, [e for e in record["episodes"] if e["agent"] == "rollout"]


def play_native(job: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    """A held-out game by 017's agent (``commit_rollout``) or, for the identity check,
    016's (``rollout``): 016's ``play_native`` with these numbers."""
    agent, seed, config = job
    numbers = config["rollout_params"] | (config["commit_rollout"]
                                          if agent == "commit_rollout" else {})
    # 016's play_native adds its config's "rollout" to "fast_deep_params" for "rollout".
    episode = e16.play_native(("rollout", seed, config | {"fast_deep_params": numbers,
                                                          "rollout": {}}))
    episode["agent"] = agent
    return episode


def _work(config: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    seeds = config["seeds"]
    return [("commit_rollout", seed, config) for seed in seeds] + \
        [("rollout", seed, config) for seed in seeds[:config["identity_check_games"]]]


def identity_problems(found: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> list[str]:
    """016's agent replayed on this build against 016's record, input by input."""
    by_seed = {e["seed"]: e for e in baseline}
    return [f"seed {e['seed']}: 016's agent plays another game on this build"
            for e in found if e["inputs"] != by_seed[e["seed"]]["inputs"]]


def _play(job: tuple[int, dict[str, Any], int, dict[str, Any]]) -> dict[str, Any]:
    """The launcher's new game: the commit-rollout agent in format ``fmt``."""
    _, fmt, seed, config = job
    chosen = _load(CONFIG)["commit_rollout"]
    return play_native(("commit_rollout", seed,
                        config | {"rollout_params": rollout_params(),
                                  "commit_rollout": check_commit(chosen), "formats": [fmt]}))


def evaluate(jobs: int) -> Path:
    if not PREDECLARED.exists() or not e13._committed(PREDECLARED) or \
            not e13._committed(CONFIG) or not DEPTH_CHECK.exists() or \
            not e13._committed(DEPTH_CHECK):
        raise ValueError("held-out games wait for a committed predeclared.md, config.json "
                         "and depth check")
    if _load(DEPTH_CHECK).get("baseline_matches_016") is not True:
        raise ValueError("the depth check's 016 baseline did not match 016's own depth check")
    config = record_configuration()
    baseline_record, baseline = _baseline()
    if baseline_record["configuration"]["seeds"] != config["seeds"] or \
            baseline_record["configuration"]["fast_deep_params"] | \
            baseline_record["configuration"]["rollout"] != config["rollout_params"]:
        raise ValueError("016's record is not 016's agent on 012's held-out seeds")
    tick = time.perf_counter()
    work = _work(config)
    held_out = [job for job in work if job[0] == "commit_rollout"]
    identity = [job for job in work if job[0] == "rollout"]
    with Pool(jobs) as pool:
        # 016's agent first: no held-out game of 017's is played on a build that differs.
        checked = pool.map(play_native, identity, chunksize=1)
        problems = identity_problems(checked, baseline)
        if problems:
            raise ValueError(f"016's record does not match this build: {problems[:3]}")
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
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-017"
    directory.mkdir(parents=True)
    path = directory / "run.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(record, handle, separators=(",", ":"))
    return path


def verify(path: Path, jobs: int = 30) -> list[str]:
    """Replays the record's games and 016's baseline games on the engine, and checks the
    identity games against 016's record."""
    record = _load(path)
    if record.get("schema") != SCHEMA:
        return [f"{path}: not an Experiment 017 record"]
    config = record["configuration"]
    if [(e["agent"], e["seed"]) for e in record["episodes"]] != \
            [(agent, seed) for agent, seed, _ in _work(config)]:
        return ["episodes do not match the configured runs and seeds"]
    if hashlib.sha256(BASELINE_RECORD.read_bytes()).hexdigest() != \
            record["baseline_record"]["sha256"]:
        return [f"{BASELINE_RECORD} is not the baseline record this run was checked against"]
    baseline_record, baseline = _baseline()
    if [e["seed"] for e in baseline] != config["seeds"]:
        return ["016's record is not on the configured seeds"]
    problems = identity_problems([e for e in record["episodes"] if e["agent"] == "rollout"],
                                 baseline)
    jobs_list = [(e, config) for e in record["episodes"]] + \
        [(e, baseline_record["configuration"]) for e in baseline]
    with Pool(jobs) as pool:
        found = pool.starmap(e9._replay, jobs_list, chunksize=4)
    return problems + [problem for problems in found for problem in problems]


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
    if config["rollout_params"] != rollout_params() or \
            config["commit_rollout"] != _load(CONFIG)["commit_rollout"]:
        raise ValueError("the record's numbers are not 016's agent and config.json's "
                         "commit_rollout settings")
    _, baseline = _baseline()
    runs = {"commit_rollout": e12._rows([e for e in record["episodes"]
                                         if e["agent"] == "commit_rollout"]),
            "rollout": e12._rows(baseline)}
    main_pair = e12.paired(runs["commit_rollout"], runs["rollout"])
    seconds = {agent: round(sum(r["decision_seconds"] for r in rows) / len(rows), 2)
               for agent, rows in runs.items()}
    return {
        "experiment": "017-commit-rollouts",
        "question": ("Does 016's agent with rollout re-ranking at the commit decision beat "
                     "016's agent on 012's held-out seeds?"),
        "record": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "created_at": record["created_at"]},
        "baseline_record": record["baseline_record"],
        "identity_check": f"016's agent replayed input for input on the first "
                          f"{config['identity_check_games']} held-out seeds",
        "versions": record["versions"], "engine_fingerprint": record["engine_fingerprint"],
        "commit_rollout": config["commit_rollout"], "params": config["rollout_params"],
        "heldout": {"games": len(runs["commit_rollout"]),
                    **{agent: e9.metrics(rows) for agent, rows in runs.items()},
                    "paired_commit_rollout_minus_rollout": main_pair,
                    "seconds_per_game": seconds},
        "depth_check": _load(DEPTH_CHECK)["paired"],
        "success_rule": ("95% CI of the paired mean score difference (commit_rollout minus "
                         "rollout) on 012's 1,000 held-out seeds entirely above 0"),
        "success": success(main_pair["score"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment017")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("depth-check", "the commit-rollout settings on dev seeds"),
                       ("evaluate", "play commit_rollout on the held-out seeds"),
                       ("verify", "replay a record on the engine"),
                       ("summarize", "write result.json from a record")):
        command = commands.add_parser(name, help=text)
        if name in ("verify", "summarize"):
            command.add_argument("record", type=Path)
        command.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "depth-check":
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
