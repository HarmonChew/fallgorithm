"""Run Experiment 033's staged evaluation of the chosen V29@20 (predeclared.md).

    python -m block_stack_ai.experiment033eval screen [--jobs N]
    python -m block_stack_ai.experiment033eval develop [--jobs N]
    python -m block_stack_ai.experiment033eval heldout [--jobs N]
    python -m block_stack_ai.experiment033eval summarize STAGE
    python -m block_stack_ai.experiment033eval sidecheck [--jobs N]

Every stage plays both ``v39r20`` (031b's record agent at 20 Hz / 300 ms) and ``v29r20``
(``v39r20`` with the V29@20 that ``experiment033 choose`` picked, ``chosen.json``) on the
stage's seeds, and pairs ``v29r20`` with ``v39r20`` by seed (the rule). Held-out first
replays 28 each of 017's, e29_k4's, v39's, v29's and v39r's stored 30 Hz record games
(140/140) and the first 28 development games of each 20 Hz arm (56/56). ``sidecheck``
plays ``v29r20``'s networks at 30 Hz on the screening seeds against 031b's stored v39r games
(reported only).
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

from . import experiment013 as e13, experiment025 as e25, experiment032 as e32
from . import experiment032eval as e32eval, experiment033 as e33, native, runner
from .experiment025 import _paired, _resume, _summary

OUT = e33.OUT
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "033"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "heldout")
ARM, BASE = "v29r20", e33.BASE
MIN_EFFECT = 15_000
REPLAY_GAMES = 28
REPLAY_CHECK = "heldout_replay_check.json"
RULE = ("Primary metric: mean final score, paired by seed against v39r20 played in this "
        "experiment on the same seeds (v29r20 minus v39r20), both at 20 Hz / 300 ms, 95% "
        "bootstrap interval of experiment012.paired. Screening: promoted if the paired mean "
        "is +15k or more. Development: kept if the paired mean is at least +15k and the "
        "interval's lower end is above 0. Held-out (predeclared.md): passes (the first 20 Hz "
        "/ 300 ms record) if the interval lies above 0, after 28 each of 017's, e29_k4's, "
        "v39's, v29's and v39r's stored 30 Hz games replay input for input (140/140) and the "
        "first 28 development games of v39r20 and of v29r20 replay input for input at 20 Hz "
        "(56/56).")

_load, _write = e13._load, e13._write


def chosen() -> dict[str, Any]:
    """033's chosen V29@20 (chosen.json), its weights' path and sha256."""
    if not e33.CHOICE.exists():
        raise ValueError(f"{e33.CHOICE} is missing: run experiment033 choose first")
    pick = _load(e33.CHOICE)["chosen"]
    if pick is None:
        raise ValueError("experiment033 choose found no sweep with a probe mean above 0")
    weights = runner.PROJECT_ROOT / pick["weights"]
    return pick | {"path": weights,
                   "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()}


def play_game(job: tuple[str | None, int, bool]) -> dict[str, Any]:
    """One checked game (register.checked_game and the tap-spacing check): v39r20, or with
    ``weights`` v29r20; ``thirty`` plays the 30 Hz format (the side check only)."""
    weights, seed, thirty = job
    frozen, net = e33._frozen_30() if thirty else e33._frozen()
    mid = e33._mid_bytes(weights)
    return e33.checked_game(frozen, seed, lambda: e33._game(net, frozen, seed, mid=mid)[0],
                            agent=ARM if weights else BASE)


def games_path(stage: str, arm: str) -> Path:
    return GAMES / f"{stage}-{arm}.json.gz"


def _stage_result(name: str) -> dict[str, Any]:
    path = OUT / f"{name}.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run {name} first")
    return _load(path)


def _require_ready() -> None:
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    e33._require_wiring()
    e33._handover_check()


def _load_record(stage: str, arm: str) -> dict[str, Any]:
    with gzip.open(games_path(stage, arm), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def play_arm(stage: str, arm: str, weights: str | None, sha: str, seeds: list[int],
             pick: dict[str, Any], versions: dict[str, Any], jobs: int) -> None:
    """Play ``arm`` on the stage's seeds (resuming from the partial file) and store its
    games with the format in the header; nothing is played if the file exists. The file is
    written outside the tree (``PARTIAL``) and moved in by ``run`` once both arms are done,
    so a crash between the arms leaves the tree clean for the resume."""
    if games_path(stage, arm).exists() or (PARTIAL / games_path(stage, arm).name).exists():
        return
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": arm, "format": fmt, "weights": weights, "weights_sha256": sha,
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "abi_version": native.ABI_VERSION, "versions": versions}}
    partial = PARTIAL / f"{stage}-{arm}.partial.jsonl"
    done = _resume(partial, header)
    todo = [(weights, seed, False) for seed in seeds if seed not in done]
    print(f"{stage} {arm}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(play_game, todo, chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            mean = sum(e["result"]["score"] for e in done.values()) / len(done)
            print(f"{arm} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "arm": arm, "format": fmt,
              "chosen": {k: v for k, v in pick.items() if k != "path"},
              "weights": weights, "weights_sha256": sha, "set": stage, "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[seed] for seed in seeds]}
    with gzip.open(PARTIAL / games_path(stage, arm).name, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    partial.unlink()


def run(stage: str, jobs: int) -> dict[str, Any]:
    """Play v39r20 and v29r20 on the stage's seeds, store the games, summarize."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    if stage == "development" and not _stage_result("screening")["promoted"]:
        raise ValueError("screening did not promote v29r20")
    if stage == "heldout":
        if not _stage_result("development")["kept"]:
            raise ValueError("development did not keep v29r20")
        if not (OUT / "predeclared.md").exists():
            raise ValueError(f"{OUT / 'predeclared.md'} is missing: predeclare first")
    pick = chosen()
    shown = {k: v for k, v in pick.items() if k != "path"}
    previous = {"development": "screening", "heldout": "development"}.get(stage)
    if previous and _stage_result(previous)["chosen"] != shown:
        raise ValueError(f"chosen.json names another V29@20 than {previous} evaluated")
    seeds = e25._seeds(stage)
    _require_ready()
    versions = runner._record_versions()
    PARTIAL.mkdir(parents=True, exist_ok=True)
    if stage == "heldout":  # every call, also a resume; kept out of the tree until the end
        replay = heldout_replay(jobs) | {"experiment": "033-v29-20hz", "versions": versions}
        _write(PARTIAL / REPLAY_CHECK, replay)
        if replay["matched"] != replay["games"]:
            raise ValueError(f"held-out replay failed: {replay['matched']} of "
                             f"{replay['games']} stored games replay on this build")
    weights = str(pick["path"].relative_to(runner.PROJECT_ROOT))
    base_sha = e33._sha(e33.v29_path())
    play_arm(stage, BASE, None, base_sha, seeds, shown, versions, jobs)
    play_arm(stage, ARM, weights, pick["sha256"], seeds, shown, versions, jobs)
    GAMES.mkdir(parents=True, exist_ok=True)
    for arm in (BASE, ARM):
        if (PARTIAL / games_path(stage, arm).name).exists():
            (PARTIAL / games_path(stage, arm).name).replace(games_path(stage, arm))
    if stage == "heldout" and (PARTIAL / REPLAY_CHECK).exists():
        (PARTIAL / REPLAY_CHECK).replace(OUT / REPLAY_CHECK)
    return summarize(stage, versions=versions)


def heldout_replay(jobs: int) -> dict[str, Any]:
    """The 30 Hz gate (032's: 28 each of 017's, e29_k4's, v39's, v29's and v39r's stored
    held-out games, 140) and the 20 Hz gate: the first 28 development games of v39r20 and
    of v29r20 replayed input for input (56)."""
    thirty = e32eval.heldout_replay(jobs)
    weights = {BASE: None, ARM: str(chosen()["path"].relative_to(runner.PROJECT_ROOT))}
    twenty = {}
    for arm, path in weights.items():
        stored = _load_record("development", arm)["episodes"][:REPLAY_GAMES]
        with Pool(jobs) as pool:
            played = pool.map(play_game, [(path, e["seed"], False) for e in stored],
                              chunksize=1)
        bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
        twenty[arm] = {"games": len(stored), "matched": len(stored) - len(bad),
                       "mismatched_seeds": bad}
    return {"stage": "heldout", "part_30hz": thirty, "part_20hz": twenty,
            "format_20hz": e33.format_of(e33._frozen()[0]),
            "games": thirty["games"] + sum(p["games"] for p in twenty.values()),
            "matched": thirty["matched"] + sum(p["matched"] for p in twenty.values()),
            "abi_version": native.ABI_VERSION}


def summarize(stage: str, versions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write OUT/<stage>.json: summaries, the paired result, style and the rule's verdict."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    seeds = e25._seeds(stage)
    base, record = _load_record(stage, BASE), _load_record(stage, ARM)
    for arm, r in ((BASE, base), (ARM, record)):
        if [e["seed"] for e in r["episodes"]] != seeds:
            raise ValueError(f"{arm}'s {stage} games are not the stage's seeds in order")
        if r["format"] != e33.format_of(e33._frozen()[0]):
            raise ValueError(f"{arm}'s {stage} games were not played in the 20 Hz format")
    base_eps, mine = base["episodes"], record["episodes"]
    paired = _paired(mine, base_eps)
    result: dict[str, Any] = {
        "experiment": "033-v29-20hz", "stage": stage, "games": len(seeds),
        "seeds": ("Experiment 012's 1,000 held-out seeds (the established record benchmark)"
                  if stage == "heldout" else f"the register's {stage} set"),
        "arm": ARM, "base": BASE, "format": record["format"], "chosen": record["chosen"],
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "rule": RULE, "min_effect": MIN_EFFECT,
        "summary": {BASE: _summary(base_eps), ARM: _summary(mine)},
        "style": {BASE: e33.style(base_eps), ARM: e33.style(mine)},
        "paired_vs_v39r20": paired}
    mean = paired["total"]["score"]["mean"]
    low = paired["total"]["score"]["ci95_low"]
    if stage == "screening":
        result["promoted"] = mean >= MIN_EFFECT
    elif stage == "development":
        result["kept"] = mean >= MIN_EFFECT and low > 0
    else:
        result["passed"] = low > 0
        result["baseline_20hz_mean_v39r20"] = result["summary"][BASE]["mean_score"]
    _write(OUT / f"{stage}.json", result)
    return result


def sidecheck(jobs: int) -> dict[str, Any]:
    """Reported only: v29r20's networks at 30 Hz on the screening seeds, paired against
    031b's stored v39r games (is V29@20 better in general, or only fit for 20 Hz?)."""
    path = OUT / "sidecheck.json"
    if path.exists():
        raise ValueError(f"{path} exists already")
    pick = chosen()
    _require_ready()
    seeds = e25._seeds("screening")
    base = e32.v39r_games("screening")
    weights = str(pick["path"].relative_to(runner.PROJECT_ROOT))
    versions = runner._record_versions()
    with Pool(jobs) as pool:
        mine = pool.map(play_game, [(weights, s, True) for s in seeds], chunksize=1)
    paired = _paired(mine, base)
    fmt = e33.format_of(e33._frozen_30()[0])
    GAMES.mkdir(parents=True, exist_ok=True)
    with gzip.open(GAMES / f"screening-{ARM}-30hz.json.gz", "wt", encoding="utf-8") as out:
        json.dump({"schema": SCHEMA, "versions": versions, "arm": ARM, "format": fmt,
                   "weights": weights, "weights_sha256": pick["sha256"], "set": "screening",
                   "seeds": seeds, "episodes": mine}, out, separators=(",", ":"))
    result = {"experiment": "033-v29-20hz", "side_check": "v29r20's networks at 30 Hz vs "
              "031b's stored v39r screening games (reported only)", "format": fmt,
              "chosen": {k: v for k, v in pick.items() if k != "path"}, "versions": versions,
              "summary": {ARM: _summary(mine), "v39r": _summary(base)},
              "paired_vs_v39r_30hz": paired}
    _write(path, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment033eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("screen", help="v39r20 and v29r20 on the screening seeds")
    commands.add_parser("develop", help="both on the development seeds, if promoted")
    commands.add_parser("heldout", help="both on 012's held-out seeds, if kept")
    commands.add_parser("sidecheck", help="v29r20 at 30 Hz on the screening seeds")
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
        elif args.command == "sidecheck":
            sidecheck(args.jobs)
        else:
            run(stage[args.command], args.jobs)
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
