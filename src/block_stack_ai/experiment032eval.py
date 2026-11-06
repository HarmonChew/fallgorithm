"""Run Experiment 032's staged evaluation of the chosen V18 (predeclared.md).

    python -m block_stack_ai.experiment032eval screen [--jobs N]
    python -m block_stack_ai.experiment032eval develop [--jobs N]
    python -m block_stack_ai.experiment032eval heldout [--jobs N]
    python -m block_stack_ai.experiment032eval summarize STAGE

The agent (``v18``) is 031b's record agent ``v39r`` with the V18 that ``experiment032
choose`` picked (``chosen.json``) as the network for every decision below 230 lines
(experiment032._game, no exploration). Every stage pairs it by seed with 031b's stored
``v39r`` games (the rule), 030's ``v29``, 029's ``v39`` and 017's (reported only); held-out
first replays 28 each of 017's, e29_k4's, v39's, v29's and v39r's stored record games.
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

from . import experiment013 as e13, experiment025 as e25, experiment028 as e28
from . import experiment030 as e30, experiment031 as e31, experiment031eval as e31eval
from . import experiment032 as e32, native, register, runner
from .experiment025 import _paired, _resume, _summary

OUT = e32.OUT
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "032"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "heldout")
ARM = e32.ARM      # v18
BASE = e32.BASE    # 031b's v39r
OLD = "v29"        # 030's, reported
OLDER = "v39"      # 029's, reported
MIN_EFFECT = 15_000
REPLAY_CHECK = "heldout_replay_check.json"
RULE = ("Primary metric: mean final score, paired by seed against 031b's stored games of "
        "v39r (v18 minus v39r), 95% bootstrap interval of experiment012.paired. "
        "Screening: promoted if the paired mean is +15k or more. Development: kept if the "
        "paired mean is at least +15k and the interval's lower end is above 0. 030's v29, "
        "029's v39 and 017's games are paired too but are not part of the rule. "
        "Held-out (predeclared.md): passes if the interval's lower end against 031b's "
        "record games of v39r on 012's held-out seeds is above 0, after 28 each of 017's, "
        "e29_k4's, v39's, v29's and v39r's stored games replay input for input on the build.")

_load, _write = e13._load, e13._write


def chosen() -> dict[str, Any]:
    """032's chosen V18 (chosen.json), its weights' path and sha256."""
    path = e32.CHOICE
    if not path.exists():
        raise ValueError(f"{path} is missing: run experiment032 choose first")
    pick = _load(path)["chosen"]
    if pick is None:
        raise ValueError("experiment032 choose found no sweep with a probe mean above 0")
    weights = runner.PROJECT_ROOT / pick["weights"]
    return pick | {"path": weights,
                   "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()}


def play_game(job: tuple[str | None, int]) -> dict[str, Any]:
    """One checked game of the v18 agent (``weights`` None: v15 below 230, i.e. v39r)."""
    weights, seed = job
    frozen, _ = e32._frozen()
    early = e32._early_bytes(weights)
    return register.checked_game(frozen, seed, lambda: e32._game(early, frozen, seed)[0],
                                 agent=ARM if weights else BASE)


def games_path(stage: str) -> Path:
    return GAMES / f"{stage}-{ARM}.json.gz"


def _stage_result(name: str) -> dict[str, Any]:
    path = OUT / f"{name}.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run {name} first")
    return _load(path)


def _require_ready(stage: str, seeds: list[int]) -> None:
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    e32._require_wiring()
    e32.v39r_games(stage)
    e31._v29_games(stage)
    e30._v39_games(stage)
    if stage == "heldout":
        e25._baseline(stage)
        return
    base = register.load_games(stage, "017")
    if [e["seed"] for e in base["episodes"]] != seeds or \
            base["frozen_sha256"] != e28._sha("017"):
        raise ValueError(f"017's {stage} games are not the seeds in order from the current 017")


def run(stage: str, jobs: int) -> dict[str, Any]:
    """Play the v18 agent on the stage's seeds, store the games, summarize."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    if stage == "development" and not _stage_result("screening")["promoted"]:
        raise ValueError("screening did not promote v18")
    if stage == "heldout":
        if not _stage_result("development")["kept"]:
            raise ValueError("development did not keep v18")
        if not (OUT / "predeclared.md").exists():
            raise ValueError(f"{OUT / 'predeclared.md'} is missing: predeclare first")
    if games_path(stage).exists():
        raise ValueError(f"{games_path(stage)} exists already")
    pick = chosen()
    previous = {"development": "screening", "heldout": "development"}.get(stage)
    if previous and _stage_result(previous)["chosen"] != {k: v for k, v in pick.items()
                                                          if k != "path"}:
        raise ValueError(f"chosen.json names another V18 than {previous} evaluated")
    seeds = e25._seeds(stage)
    _require_ready(stage, seeds)
    versions = runner._record_versions()
    PARTIAL.mkdir(parents=True, exist_ok=True)
    if stage == "heldout":  # every call, also a resume; kept out of the tree until the end
        replay = heldout_replay(jobs) | {"experiment": "032-v18-search-taught",
                                         "versions": versions}
        _write(PARTIAL / REPLAY_CHECK, replay)
        if replay["matched"] != replay["games"]:
            raise ValueError(f"held-out replay failed: {replay['matched']} of "
                             f"{replay['games']} stored games replay on this build")
    weights = str(pick["path"].relative_to(runner.PROJECT_ROOT))
    header = {"header": {"arm": ARM, "weights": weights, "weights_sha256": pick["sha256"],
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "abi_version": native.ABI_VERSION, "versions": versions}}
    partial = PARTIAL / f"{stage}-{ARM}.partial.jsonl"
    done = _resume(partial, header)
    todo = [(weights, seed) for seed in seeds if seed not in done]
    print(f"{stage}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(play_game, todo, chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            mean = sum(e["result"]["score"] for e in done.values()) / len(done)
            print(f"{ARM} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    GAMES.mkdir(parents=True, exist_ok=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "arm": ARM, "chosen": {k: v for k, v in pick.items()
                                                           if k != "path"},
              "weights": weights, "set": stage, "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[seed] for seed in seeds]}
    with gzip.open(games_path(stage), "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    partial.unlink()
    if stage == "heldout":
        (PARTIAL / REPLAY_CHECK).replace(OUT / REPLAY_CHECK)
    return summarize(stage, versions=versions)


def heldout_replay(jobs: int) -> dict[str, Any]:
    """031b's replay gate (017, e29_k4, v39, v29: 28 each), plus the first 28 of 031b's
    v39r record games replayed with v15 as the early network."""
    first = e31eval.heldout_replay(jobs)
    stored = e32.v39r_games("heldout")[:e28.REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(play_game, [(None, e["seed"]) for e in stored], chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"stage": "heldout", "part_abcd_031b": first,
            "part_e_v39r": {"games": len(stored), "matched": len(stored) - len(bad),
                            "mismatched_seeds": bad},
            "games": first["games"] + len(stored),
            "matched": first["matched"] + len(stored) - len(bad),
            "abi_version": native.ABI_VERSION}


def summarize(stage: str, versions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write OUT/<stage>.json: summaries, paired results, style by band and the rule's
    verdict."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    seeds = e25._seeds(stage)
    base = e32.v39r_games(stage)
    old = e31._v29_games(stage)
    older = e30._v39_games(stage)
    reference = e25._baseline("heldout") if stage == "heldout" else \
        register.load_games(stage, "017")["episodes"]
    if [e["seed"] for e in reference] != seeds:
        raise ValueError(f"017's {stage} games are not the stage's seeds in order")
    with gzip.open(games_path(stage), "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    mine = record["episodes"]
    if [e["seed"] for e in mine] != seeds:
        raise ValueError(f"v18's {stage} games are not the stage's seeds in order")
    episodes = {OLDER: older, OLD: old, BASE: base, "017": reference, ARM: mine}
    paired = _paired(mine, base)
    result: dict[str, Any] = {
        "experiment": "032-v18-search-taught", "stage": stage, "games": len(base),
        "seeds": ("Experiment 012's 1,000 held-out seeds (the established record benchmark)"
                  if stage == "heldout" else f"the register's {stage} set"),
        "arm": ARM, "chosen": record["chosen"], "base": BASE,
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "rule": RULE, "min_effect": MIN_EFFECT,
        "summary": {name: _summary(eps) for name, eps in episodes.items()},
        "style": {name: e32.style(eps) for name, eps in episodes.items()},
        "paired_vs_v39r": {ARM: paired},
        "paired_vs_v29": {ARM: _paired(mine, old)},
        "paired_vs_v39": {ARM: _paired(mine, older)},
        "paired_vs_017": {name: _paired(eps, reference) for name, eps in episodes.items()
                          if name != "017"}}
    mean = paired["total"]["score"]["mean"]
    low = paired["total"]["score"]["ci95_low"]
    if stage == "screening":
        result["promoted"] = mean >= MIN_EFFECT
    elif stage == "development":
        result["kept"] = mean >= MIN_EFFECT and low > 0
    else:
        result["passed"] = low > 0
    _write(OUT / f"{stage}.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment032eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("screen", help="v18 on the screening seeds")
    commands.add_parser("develop", help="v18 on the development seeds, if promoted")
    commands.add_parser("heldout", help="v18 on 012's held-out seeds, if kept")
    commands.add_parser("summarize", help="summarize a stage").add_argument("stage",
                                                                           choices=STAGES)
    for name, sub in commands.choices.items():
        if name != "summarize":
            sub.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    stage = {"screen": "screening", "develop": "development", "heldout": "heldout"}
    try:
        if args.command == "summarize":
            summarize(args.stage)
        else:
            run(stage[args.command], args.jobs)
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
