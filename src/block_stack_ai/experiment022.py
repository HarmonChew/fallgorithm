"""Run Experiment 022: score the killscreen's moves by real points to the game's end.

    python -m block_stack_ai.experiment022 dev-check [--part 1|0] [--variant V] [--jobs N]

017's agent picks its level 29+ moves by 10-piece rollouts scored by the hand-built
placement value. 022 keeps that agent below ``playout_from_level`` (39) and from there
scores the commit search's best placements by playouts to the end of the game instead
(native ``playout_game``): fresh pieces placed as the fast agent places them at a commit
decision, until a top-out or the line cap, each worth the real points it earns.
``dev-check`` plays config ``variants`` on one part of Experiment 020's dev seeds, paired
against 015's and 017's stored games there (020's dev_baselines.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from multiprocessing import Pool
from typing import Any

from . import experiment012 as e12, experiment013 as e13, experiment016 as e16
from . import experiment020 as e20, experiment021 as e21, native, runner

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "022-playouts"
CONFIG = EXPERIMENT_ROOT / "config.json"

_load, _write = e13._load, e13._write


def play(config: dict[str, Any], seed: int, variant: dict[str, Any]) -> dict[str, Any]:
    """One game by 017's agent with ``variant``'s playouts from config
    ``playout_from_level``."""
    if variant["policy"] not in ("rank", "search"):
        raise ValueError(f"unknown playout policy {variant['policy']!r}")
    net = ((runner.PROJECT_ROOT / config["rank_net"]).read_bytes()
           if variant["policy"] == "rank" else None)
    played, _ = native.playout_game(
        net, config["game"], seed, from_level=config["playout_from_level"],
        count=variant["count"], line_cap=config["line_cap"], frame_cap=config["frame_cap"],
        limits=e13._limits(config), params=native.params(e21.agent_params()))
    return played


def dev_game(job: tuple[str, int]) -> dict[str, Any]:
    """One dev game by variant ``name``, replayed for its score by band."""
    name, seed = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played = play(config, seed, config["variants"][name])
    seconds = time.perf_counter() - tick
    return ({"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
             "seconds": seconds} |
            {key: played[key] for key in ("playouts", "playout_pieces", "playouts_cut")} |
            e20._replay(config, seed, played))


def dev_check(jobs: int, part: int = 1, variants: list[str] | None = None) -> dict[str, Any]:
    """Config ``variants`` on one part of 020's dev seeds, paired against 015's and 017's
    agents there."""
    stored = _load(e20.DEV_BASELINES)
    if str(part) not in stored:
        raise ValueError(f"020's dev_baselines.json has no part {part}")
    base = stored[str(part)]
    config = _load(CONFIG)
    chosen = variants or list(config["variants"])
    unknown = [name for name in chosen if name not in config["variants"]]
    if unknown:
        raise ValueError(f"unknown variants {unknown}")
    todo = [(name, seed) for name in chosen for seed in base["seeds"]]
    with Pool(jobs) as pool:
        played = pool.map(dev_game, todo, chunksize=1)
    runs = {name: [g for g in played if g["name"] == name] for name in chosen}
    net = runner.PROJECT_ROOT / config["rank_net"]
    return {
        "question": "017's agent with its level 39+ commit decisions scored by playouts to the "
                    "game's end, against 017's agent, on 020's dev seeds",
        "seeds": f"Experiment 020's dev seeds {part * len(base['seeds'])} to "
                 f"{(part + 1) * len(base['seeds']) - 1}", "games": len(base["seeds"]),
        "versions": runner._record_versions(),
        "rank_net": {"path": config["rank_net"],
                     "sha256": hashlib.sha256(net.read_bytes()).hexdigest()},
        "playout_from_level": config["playout_from_level"],
        "variants": {name: config["variants"][name] for name in chosen},
        "runs": {name: e20.summary(games) for name, games in runs.items()} |
                {name: e20.summary(base["games"][name]) for name in e20.BASELINES},
        "paired": {f"{name} - {other}": {"total": e12.paired(games, base["games"][other]),
                                         "by_band": e16._band_pairs(games, base["games"][other])}
                   for name, games in runs.items() for other in e20.BASELINES},
        "playouts": {name: {key: sum(g[key] for g in games)
                            for key in ("playouts", "playout_pieces", "playouts_cut")}
                     for name, games in runs.items()},
        "per_game": {name: [{key: g[key] for key in ("seed", "score", "lines", "seconds")}
                            for g in games] for name, games in runs.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment022")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("dev-check", help="the playout agents on dev seeds")
    check.add_argument("--part", type=int, choices=(0, 1), default=1)
    check.add_argument("--variant", action="append", dest="variants")
    check.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "dev-check":
            names = "_".join(args.variants) if args.variants else "all"
            path = EXPERIMENT_ROOT / f"dev_check_{names}_part{args.part}.json"
            if path.exists():
                raise ValueError(f"{path} exists")
            _write(path, dev_check(args.jobs, args.part, args.variants))
            print(f"Wrote {path}")
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
