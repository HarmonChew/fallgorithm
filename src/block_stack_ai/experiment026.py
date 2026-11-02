"""Run Experiment 026: does more search help the frozen V (Direction Phase 1)?

    python -m block_stack_ai.experiment026 check [--jobs N]
    python -m block_stack_ai.experiment026 screen [--jobs N]
    python -m block_stack_ai.experiment026 screen-d3 [--jobs N]
    python -m block_stack_ai.experiment026 develop [--arms ARM ...] [--jobs N]
    python -m block_stack_ai.experiment026 summarize STAGE
    python -m block_stack_ai.experiment026 residual [--jobs N]

Each arm plays the register's screening (100) or development (500) seeds with 023's value
agent (frozen ``v15``) and one deeper-search change (native/netsearch.hpp ``set_deep``,
see plan.md); ``summarize`` pairs every arm with v15's registered games on the same seeds
(the rule) and with 017's (reported only). ``residual`` is the Bellman-residual diagnostic.
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

import numpy as np

from . import experiment013 as e13, native, register, runner
from .experiment025 import _entry, _mean, _paired, _resume, _summary  # noqa: F401

OUT = runner.PROJECT_ROOT / "experiments" / "026-deeper-v"
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "026"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development")
OFF = 1000  # a commit level no game reaches: the commit change is off
ADJUST_MAX_LEVEL = 28
# arm: (commit level, adjust k); the combination arms d3_<d1 arm>_<d2 arm without "d2_">
ARMS = {"d1a": (39, 0), "d1b": (29, 0), "d2_k4": (OFF, 4), "d2_k8": (OFF, 8)}
D1 = ("d1a", "d1b")
D2 = ("d2_k4", "d2_k8")
ALL_ARMS = ARMS | {f"d3_{a}_{b[3:]}": (ARMS[a][0], ARMS[b][1]) for a in D1 for b in D2}
MIN_EFFECT = 40_000
RULE = ("Primary metric: mean final score, paired by seed against v15's registered games "
        "(arm minus v15), 95% bootstrap interval of experiment012.paired. Screening: an arm "
        "is promoted if its paired mean is +40k or more. Development: an arm is kept if its "
        "paired mean is at least +40k and its interval's lower end is above 0; of the kept "
        "arms the one with the higher mean is chosen. 017's registered games are paired too "
        "(paired_vs_017) but are not part of the rule.")

_load, _write = e13._load, e13._write
WIRING = OUT / "wiring_check.json"
WIRING_GAMES = 3
# arm: a line cap that ends the game before the arm's commit level (29 / 39 from level 18)
EARLY_CAPS = {"d1a": 320, "d1b": 220}
RESIDUAL = OUT / "residual.json"
RESIDUAL_GAMES = 20
BANDS = (("18", 0, 18), ("19-28", 19, 28), ("29-38", 29, 38), ("39+", 39, 10_000))


def _sha(name: str) -> str:
    return hashlib.sha256(register.frozen_path(name).read_bytes()).hexdigest()


def play_arm_game(job: tuple[str, dict[str, Any], bytes, int]) -> dict[str, Any]:
    """One checked game of ``arm`` (register.checked_game)."""
    arm, frozen, net, seed = job
    commit_level, adjust_k = ALL_ARMS[arm]

    def play() -> dict[str, Any]:
        return native.deep_net_game(net, frozen["game"], seed, commit_level=commit_level,
                                    adjust_k=adjust_k, adjust_max_level=ADJUST_MAX_LEVEL,
                                    line_cap=frozen["line_cap"], frame_cap=frozen["frame_cap"],
                                    limits=e13._limits(frozen))

    return register.checked_game(frozen, seed, play, agent=arm)


# ---------------------------------------------------------------- wiring

def _wiring_job(job: tuple[dict[str, Any], bytes, dict[str, Any]]) -> dict[str, Any]:
    frozen, net, reference = job
    played = native.deep_net_game(
        net, frozen["game"], reference["seed"], commit_level=OFF, adjust_k=0,
        adjust_max_level=ADJUST_MAX_LEVEL, line_cap=frozen["line_cap"],
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen))
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"], played["lines"]]
    want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    return {"seed": reference["seed"], "match": got == want,
            "got": None if got == want else got[1:], "want": None if got == want else want[1:]}


def _early_job(job: tuple[dict[str, Any], bytes, int, str]) -> dict[str, Any]:
    """``arm`` with the line cap cut below its commit level: equal to net_game's game."""
    frozen, net, seed, arm = job
    cap = EARLY_CAPS[arm]
    args = dict(line_cap=cap, frame_cap=frozen["frame_cap"], limits=e13._limits(frozen))
    played = native.deep_net_game(net, frozen["game"], seed, commit_level=ARMS[arm][0],
                                  adjust_k=0, adjust_max_level=ADJUST_MAX_LEVEL, **args)
    plain = native.net_game(net, frozen["game"], seed, **args)[0]
    same = [played[k] for k in ("inputs", "score", "lines")] == \
        [plain[k] for k in ("inputs", "score", "lines")]
    return {"kind": f"{arm}_before_its_level", "seed": seed, "match": same,
            "got": None if same else [played["score"], played["lines"]],
            "want": None if same else [plain["score"], plain["lines"]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """The deep entry point with both changes off against v15's first registered screening
    games (inputs, score and lines), and d1a / d1b with the line cap below their level
    against net_game's games under the same caps."""
    frozen, net = register.load_frozen("v15")
    episodes = register.load_games("screening", "v15")["episodes"][:WIRING_GAMES]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, [(frozen, net, e) for e in episodes], chunksize=1)
        found += pool.map(_early_job, [(frozen, net, e["seed"], arm) for arm in EARLY_CAPS
                                       for e in episodes], chunksize=1)
    result = {"experiment": "026-deeper-v", "games": found,
              "matched": len(found) == WIRING_GAMES * (1 + len(EARLY_CAPS))
              and all(g["match"] for g in found),
              "frozen_sha256": {"v15": _sha("v15")}, "abi_version": native.ABI_VERSION,
              "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


def _require_ready(stage: str, seeds: list[int]) -> None:
    """Refuse a dirty tree, an unmatched wiring check, or baseline games (v15's, 017's) that
    are not the stage's seeds in order from the current frozen agents."""
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION or \
            wiring.get("frozen_sha256") != {"v15": _sha("v15")}:
        raise ValueError(f"{WIRING} is missing, not all matched, or from another build or "
                         "frozen agent: run check first")
    for name in ("v15", "017"):
        path = register.games_path(stage, name)
        if not path.exists():
            raise ValueError(f"{path} is missing: play {name} on the {stage} set first")
        base = register.load_games(stage, name)
        if [e["seed"] for e in base["episodes"]] != seeds or base["seeds"] != seeds:
            raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
        if base["frozen_sha256"] != _sha(name):
            raise ValueError(f"{path} was played with another frozen {name} than the current one")


def _header(arm: str, seeds: list[int], versions: dict[str, Any]) -> dict[str, Any]:
    return {"header": {"frozen_sha256": {"v15": _sha("v15")}, "arm": arm,
                       "setting": [*ALL_ARMS[arm], ADJUST_MAX_LEVEL],
                       "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                       "abi_version": native.ABI_VERSION, "versions": versions}}


def games_path(stage: str, arm: str) -> Path:
    return GAMES / f"{stage}-{arm}.json.gz"


# ---------------------------------------------------------------- the rule's inputs

def _screened(arm_names: tuple[str, ...]) -> dict[str, float]:
    """The promoted ``arm_names`` in screening.json and their paired means against v15."""
    path = OUT / "screening.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run screening first")
    screening = _load(path)
    return {arm: screening["paired_vs_v15"][arm]["total"]["score"]["mean"]
            for arm in arm_names if screening["promoted"].get(arm)}


def d3_arm() -> str:
    """The combination arm: the best promoted D1 arm with the best promoted D2 arm."""
    best = []
    for kind, names in (("D1", D1), ("D2", D2)):
        promoted = _screened(names)
        if not promoted:
            raise ValueError(f"screening promoted no {kind} arm: no combination to play")
        best.append(max(promoted, key=promoted.get))
    return f"d3_{best[0]}_{best[1][3:]}"


def _promoted(arms: list[str]) -> None:
    path = OUT / "screening.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run screening first")
    promoted = _load(path)["promoted"]
    for arm in arms:
        if not promoted.get(arm):
            raise ValueError(f"{arm} was not promoted by screening")


def run(stage: str, arms: list[str], jobs: int) -> dict[str, Any]:
    """Play ``arms`` on the stage's seeds (all in one pool), store the games, summarize."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    unknown = [arm for arm in arms if arm not in ALL_ARMS]
    if unknown or not arms:
        raise ValueError(f"arms must be some of {tuple(ALL_ARMS)}, not {arms}")
    if stage == "development":
        _promoted(arms)
    for arm in arms:
        if games_path(stage, arm).exists():
            raise ValueError(f"{games_path(stage, arm)} exists already")
    seeds = register.set_seeds(stage)
    _require_ready(stage, seeds)
    versions = runner._record_versions()
    frozen, net = register.load_frozen("v15")
    PARTIAL.mkdir(parents=True, exist_ok=True)
    headers = {arm: _header(arm, seeds, versions) for arm in arms}
    partials = {arm: PARTIAL / f"{stage}-{arm}.partial.jsonl" for arm in arms}
    done = {arm: _resume(partials[arm], headers[arm]) for arm in arms}
    todo = [(arm, frozen, net, seed) for seed in seeds for arm in arms if seed not in done[arm]]
    print(f"{stage}: {sum(map(len, done.values()))} games already done, {len(todo)} to play",
          flush=True)
    tick = time.perf_counter()
    handles = {arm: partials[arm].open("a", encoding="utf-8") for arm in arms}
    try:
        with Pool(jobs) as pool:
            for episode in pool.imap_unordered(play_arm_game, todo, chunksize=1):
                arm = episode["agent"]
                handles[arm].write(json.dumps(episode, separators=(",", ":")) + "\n")
                handles[arm].flush()
                done[arm][episode["seed"]] = episode
                print(" ".join(f"{a} {len(done[a])}/{len(seeds)} "
                               f"{sum(e['result']['score'] for e in done[a].values()) / max(1, len(done[a])):,.0f}"
                               for a in arms), flush=True)
    finally:
        for handle in handles.values():
            handle.close()
    GAMES.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
                  "versions": versions, "arm": arm,
                  "search": dict(zip(("commit_level", "adjust_k"), ALL_ARMS[arm]))
                  | {"adjust_max_level": ADJUST_MAX_LEVEL},
                  "frozen_sha256": headers[arm]["header"]["frozen_sha256"], "set": stage,
                  "seeds": seeds, "wall_seconds": round(time.perf_counter() - tick, 1),
                  "episodes": [done[arm][seed] for seed in seeds]}
        with gzip.open(games_path(stage, arm), "wt", encoding="utf-8") as out:
            json.dump(record, out, separators=(",", ":"))
        partials[arm].unlink()
    return summarize(stage, versions=versions)


# ---------------------------------------------------------------- summary

def _load_arm(stage: str, arm: str) -> dict[str, Any]:
    with gzip.open(games_path(stage, arm), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _episodes(stage: str, name: str, seeds: list[int]) -> list[dict[str, Any]]:
    episodes = register.load_games(stage, name)["episodes"]
    if [e["seed"] for e in episodes] != seeds:
        raise ValueError(f"{name}'s registered {stage} games are not the stage's seeds in order")
    return episodes


def summarize(stage: str, versions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write OUT/<stage>.json: the summaries, the paired results and the rule's verdicts."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    seeds = register.set_seeds(stage)
    base = _episodes(stage, "v15", seeds)
    episodes = {"v15": base, "017": _episodes(stage, "017", seeds)}
    present = [arm for arm in ALL_ARMS if games_path(stage, arm).exists()]
    if not present:
        raise ValueError(f"no arm has played the {stage} set")
    for arm in present:
        episodes[arm] = _load_arm(stage, arm)["episodes"]
        if [e["seed"] for e in episodes[arm]] != seeds:
            raise ValueError(f"{arm}'s {stage} games are not the stage's seeds in order")
    summary = {name: _summary(eps) for name, eps in episodes.items()}
    result: dict[str, Any] = {
        "experiment": "026-deeper-v", "stage": stage, "games": len(base),
        "seeds": f"the register's {stage} set", "arms": present,
        "search": {arm: dict(zip(("commit_level", "adjust_k"), ALL_ARMS[arm]))
                   | {"adjust_max_level": ADJUST_MAX_LEVEL} for arm in ALL_ARMS},
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "frozen_sha256": {"v15": _sha("v15"), "017": _sha("017")},
        "rule": RULE, "min_effect": MIN_EFFECT, "summary": summary,
        "paired_vs_v15": {arm: _paired(episodes[arm], base) for arm in present},
        "paired_vs_017": {name: _paired(eps, episodes["017"]) for name, eps in episodes.items()
                          if name != "017"}}
    mean = {arm: result["paired_vs_v15"][arm]["total"]["score"]["mean"] for arm in present}
    if stage == "screening":
        result["promoted"] = {arm: mean[arm] >= MIN_EFFECT for arm in present}
    else:
        kept = {arm: mean[arm] >= MIN_EFFECT
                and result["paired_vs_v15"][arm]["total"]["score"]["ci95_low"] > 0
                for arm in present}
        result["kept"] = kept
        result["chosen"] = max((a for a in present if kept[a]), key=mean.get, default=None)
    _write(OUT / f"{stage}.json", result)
    return result


# ---------------------------------------------------------------- Bellman residual

def _rows_job(job: tuple[dict[str, Any], bytes, int]) -> bytes:
    frozen, net, seed = job
    return native.net_game(net, frozen["game"], seed, line_cap=frozen["line_cap"],
                           frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
                           dump=True)[1]


def _values_job(job: tuple[dict[str, Any], bytes, bytes]) -> tuple[list[float], list[float]]:
    frozen, net, rows = job
    common = dict(line_cap=frozen["line_cap"], start_level=frozen["game"]["start_level"])
    backup, _ = native.backup_values(
        net, rows, double_killscreen=frozen["game"]["ruleset"].endswith("double_killscreen"),
        tap_interval=e13._limits(frozen).tap_interval, **common)
    return backup, native.net_values(net, rows, **common)


def band_residuals(levels: np.ndarray, value: np.ndarray, backup: np.ndarray
                   ) -> dict[str, dict[str, Any]]:
    """Count, mean and sd of ``backup - value`` and mean value (points) by level band, and
    over all boards."""
    result = {}
    for name, low, high in (*BANDS, ("all", 0, 10_000)):
        pick = (levels >= low) & (levels <= high)
        gap = (backup - value)[pick]
        result[name] = {"boards": int(pick.sum()),
                        "mean_residual": float(gap.mean()) if gap.size else None,
                        "sd_residual": float(gap.std(ddof=1)) if gap.size > 1 else None,
                        "mean_value": float(value[pick].mean()) if gap.size else None}
    return result


def residual(jobs: int) -> dict[str, Any]:
    """V's own boards from v15's first 20 screening games: ``backup(x) - V(x)`` by level
    band (both in points). Boards at or past the line cap (value and backup 0) are left out."""
    frozen, net = register.load_frozen("v15")
    seeds = register.set_seeds("screening")[:RESIDUAL_GAMES]
    with Pool(jobs) as pool:
        dumps = pool.map(_rows_job, [(frozen, net, s) for s in seeds], chunksize=1)
        rows = np.frombuffer(b"".join(dumps), np.int32).reshape(-1, native.DUMP_STRIDE)
        rows = rows[rows[:, native.WIDTH] < frozen["line_cap"]]
        chunks = np.array_split(rows, max(1, jobs * 4))
        found = pool.map(_values_job, [(frozen, net, c.tobytes()) for c in chunks if len(c)],
                         chunksize=1)
    backup = np.concatenate([np.array(b) for b, _ in found])
    value = np.concatenate([np.array(v) for _, v in found])
    start = frozen["game"]["start_level"]
    levels = np.array([native.level_for_lines(int(n), start) for n in rows[:, native.WIDTH]])
    result = {"experiment": "026-deeper-v", "agent": "v15", "seeds": seeds,
              "units": "points (backup_values and net_values, both in points)",
              "bands": band_residuals(levels, value, backup),
              "versions": runner._record_versions(), "abi_version": native.ABI_VERSION}
    _write(RESIDUAL, result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment026")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="the deep entry point, off, against v15's stored games")
    commands.add_parser("screen", help="the four base arms on the screening seeds")
    commands.add_parser("screen-d3", help="the best promoted D1 with the best promoted D2")
    develop = commands.add_parser("develop", help="promoted arms on the development seeds")
    develop.add_argument("--arms", nargs="+", choices=tuple(ALL_ARMS))
    commands.add_parser("summarize", help="summarize a stage").add_argument("stage",
                                                                           choices=STAGES)
    commands.add_parser("residual", help="the Bellman residual on v15's own boards")
    for name, sub in commands.choices.items():
        if name != "summarize":
            sub.add_argument("--jobs", type=int, default=4 if name == "check" else 28)
    args = parser.parse_args(argv)
    try:
        if args.command == "summarize":
            summarize(args.stage)
            print(f"Wrote {OUT / f'{args.stage}.json'}")
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "residual":
            residual(args.jobs)
            print(f"Wrote {RESIDUAL}")
        elif args.command == "screen":
            run("screening", list(ARMS), args.jobs)
        elif args.command == "screen-d3":
            run("screening", [d3_arm()], args.jobs)
        else:
            arms = args.arms
            if arms is None:
                path = OUT / "screening.json"
                if not path.exists():
                    raise ValueError(f"{path} is missing: run screening first")
                arms = [a for a, ok in _load(path)["promoted"].items() if ok]
                if not arms:
                    raise ValueError("screening promoted no arm")
                if any(a in arms for a in D1) and any(a in arms for a in D2) and \
                        not any(a.startswith("d3_") and games_path("screening", a).exists()
                                for a in ALL_ARMS):
                    raise ValueError("a D1 and a D2 arm were promoted but no combination was "
                                     "screened: run screen-d3 first")
            run("development", arms, args.jobs)
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
