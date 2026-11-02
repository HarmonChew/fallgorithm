"""Run Experiment 027: does 026's record agent gain from looking two unknown pieces deep?

    python -m block_stack_ai.experiment027 check [--jobs N]
    python -m block_stack_ai.experiment027 screen [--jobs N]
    python -m block_stack_ai.experiment027 develop [--arms ARM ...] [--jobs N]
    python -m block_stack_ai.experiment027 heldout [--jobs N]
    python -m block_stack_ai.experiment027 summarize STAGE

Each arm is 026's chosen agent ``d3_d1b_k8`` (frozen ``v15``, native ``deep_net_game``)
with one more search change (native/netsearch.hpp ``set_deep2``, see plan.md): from a
level on, the commit decision's best k placements are rescored two unknown pieces deep.
``summarize`` pairs every arm with 026's stored d3 games on the same seeds (the rule) and
with 017's (reported only). ``heldout`` plays development's chosen arm on Experiment 012's
held-out seeds against 026's record games of d3 (the rule) and 017's stored record games.
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

from . import experiment013 as e13, experiment025 as e25, experiment026 as e26
from . import native, register, runner
from .experiment025 import _paired, _resume, _summary

OUT = runner.PROJECT_ROOT / "experiments" / "027-deeper-39"
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "027"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "heldout")
BASE = "d3_d1b_k8"  # 026's chosen arm, the record
COMMIT_LEVEL, ADJUST_K = e26.ALL_ARMS[BASE]
ADJUST_MAX_LEVEL = e26.ADJUST_MAX_LEVEL
OFF = e26.OFF
# arm: (deep2 level, deep2 k)
ARMS = {"e39_k2": (39, 2), "e39_k4": (39, 4), "e29_k4": (29, 4)}
MIN_EFFECT = 15_000
REPLAY_CHECK = "heldout_replay_check.json"
REPLAY_GAMES = 28
RULE = ("Primary metric: mean final score, paired by seed against 026's stored games of "
        "d3_d1b_k8 (arm minus d3), 95% bootstrap interval of experiment012.paired. Screening: "
        "an arm is promoted if its paired mean is +15k or more. Development: an arm is kept if "
        "its paired mean is at least +15k and its interval's lower end is above 0; of the kept "
        "arms the one with the higher mean is chosen. 017's registered games are paired too "
        "(paired_vs_017) but are not part of the rule. Held-out (after predeclared.md): the "
        "chosen arm passes if its interval's lower end against 026's record games of d3_d1b_k8 "
        "on 012's held-out seeds is above 0, after 28 of 017's stored games and 28 of d3's "
        "replay input for input on the build.")

_load, _write = e13._load, e13._write
WIRING = OUT / "wiring_check.json"
WIRING_GAMES = 3
# arm: a line cap that ends the game before the arm's deep2 level (29 / 39 from level 18)
EARLY_CAPS = {29: 220, 39: 320}


def _sha(name: str) -> str:
    return hashlib.sha256(register.frozen_path(name).read_bytes()).hexdigest()


def _play(net: bytes, frozen: dict[str, Any], seed: int, deep2: tuple[int, int],
          line_cap: int | None = None) -> dict[str, Any]:
    return native.deep_net_game(
        net, frozen["game"], seed, commit_level=COMMIT_LEVEL, adjust_k=ADJUST_K,
        adjust_max_level=ADJUST_MAX_LEVEL, deep2_level=deep2[0], deep2_k=deep2[1],
        line_cap=frozen["line_cap"] if line_cap is None else line_cap,
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen))


def play_arm_game(job: tuple[str, dict[str, Any], bytes, int]) -> dict[str, Any]:
    """One checked game of ``arm`` (register.checked_game); ``BASE`` is d3 itself."""
    arm, frozen, net, seed = job
    deep2 = (OFF, 0) if arm == BASE else ARMS[arm]
    return register.checked_game(frozen, seed, lambda: _play(net, frozen, seed, deep2),
                                 agent=arm)


def _base_episodes(stage: str, seeds: list[int]) -> list[dict[str, Any]]:
    """026's stored games of d3 on the stage, checked to be its seeds in order."""
    path = e26.games_path(stage, BASE)
    if not path.exists():
        raise ValueError(f"{path} is missing")
    record = e26._load_arm(stage, BASE)
    if record["search"] != {"commit_level": COMMIT_LEVEL, "adjust_k": ADJUST_K,
                            "adjust_max_level": ADJUST_MAX_LEVEL} or \
            record["frozen_sha256"] != {"v15": _sha("v15")}:
        raise ValueError(f"{path} is not d3's search with the current frozen v15")
    episodes = record["episodes"]
    if [e["seed"] for e in episodes] != seeds:
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    return episodes


def _seeds(stage: str) -> list[int]:
    return e25._seeds(stage)


# ---------------------------------------------------------------- wiring

def _wiring_job(job: tuple[dict[str, Any], bytes, dict[str, Any]]) -> dict[str, Any]:
    frozen, net, reference = job
    played = _play(net, frozen, reference["seed"], (OFF, 0))
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"], played["lines"]]
    want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    return {"kind": "deep2_off_is_d3", "seed": reference["seed"], "match": got == want,
            "got": None if got == want else got[1:], "want": None if got == want else want[1:]}


def _early_job(job: tuple[dict[str, Any], bytes, int, str]) -> dict[str, Any]:
    """``arm`` with the line cap cut below its deep2 level: equal to d3's game there."""
    frozen, net, seed, arm = job
    cap = EARLY_CAPS[ARMS[arm][0]]
    played = _play(net, frozen, seed, ARMS[arm], line_cap=cap)
    plain = _play(net, frozen, seed, (OFF, 0), line_cap=cap)
    same = [played[k] for k in ("inputs", "score", "lines")] == \
        [plain[k] for k in ("inputs", "score", "lines")]
    return {"kind": f"{arm}_before_its_level", "seed": seed, "match": same,
            "got": None if same else [played["score"], played["lines"]],
            "want": None if same else [plain["score"], plain["lines"]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """deep2 off against 026's first stored screening games of d3 (inputs, score, lines),
    and every arm with the line cap below its level against d3 under the same cap."""
    frozen, net = register.load_frozen("v15")
    episodes = _base_episodes("screening", _seeds("screening"))[:WIRING_GAMES]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, [(frozen, net, e) for e in episodes], chunksize=1)
        found += pool.map(_early_job, [(frozen, net, e["seed"], arm) for arm in ARMS
                                       for e in episodes], chunksize=1)
    result = {"experiment": "027-deeper-39", "games": found,
              "matched": len(found) == WIRING_GAMES * (1 + len(ARMS))
              and all(g["match"] for g in found),
              "frozen_sha256": {"v15": _sha("v15")}, "abi_version": native.ABI_VERSION,
              "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


def _require_ready(stage: str, seeds: list[int]) -> None:
    """Refuse a dirty tree, an unmatched wiring check, or baselines that are not the
    stage's seeds in order (017's registered games also from the current frozen 017)."""
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION or \
            wiring.get("frozen_sha256") != {"v15": _sha("v15")}:
        raise ValueError(f"{WIRING} is missing, not all matched, or from another build or "
                         "frozen agent: run check first")
    _base_episodes(stage, seeds)
    if stage == "heldout":
        e25._baseline(stage)
        return
    path = register.games_path(stage, "017")
    if not path.exists():
        raise ValueError(f"{path} is missing")
    base = register.load_games(stage, "017")
    if [e["seed"] for e in base["episodes"]] != seeds or base["frozen_sha256"] != _sha("017"):
        raise ValueError(f"{path} is not the {stage} seeds in order from the current 017")


def heldout_replay(jobs: int) -> dict[str, Any]:
    """(a) 28 of 017's stored held-out games replayed on this build (register.check_frozen);
    (b) the first 28 of 026's d3 record games replayed, inputs compared."""
    first = register.check_frozen("017", REPLAY_GAMES, jobs)
    frozen, net = register.load_frozen("v15")
    stored = _base_episodes("heldout", _seeds("heldout"))[:REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(play_arm_game, [(BASE, frozen, net, e["seed"]) for e in stored],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"experiment": "027-deeper-39", "stage": "heldout",
            "part_a_017": first, "part_b_d3": {
                "games": len(stored), "matched": len(stored) - len(bad), "mismatched_seeds": bad},
            "games": first["games"] + len(stored),
            "matched": first["matched"] + len(stored) - len(bad),
            "abi_version": native.ABI_VERSION}


def _header(arm: str, seeds: list[int], versions: dict[str, Any]) -> dict[str, Any]:
    return {"header": {"frozen_sha256": {"v15": _sha("v15")}, "arm": arm,
                       "setting": [COMMIT_LEVEL, ADJUST_K, ADJUST_MAX_LEVEL, *ARMS[arm]],
                       "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                       "abi_version": native.ABI_VERSION, "versions": versions}}


def games_path(stage: str, arm: str) -> Path:
    return GAMES / f"{stage}-{arm}.json.gz"


def _search(arm: str) -> dict[str, int]:
    return {"commit_level": COMMIT_LEVEL, "adjust_k": ADJUST_K,
            "adjust_max_level": ADJUST_MAX_LEVEL,
            **dict(zip(("deep2_level", "deep2_k"), ARMS[arm]))}


def _stage_result(name: str) -> dict[str, Any]:
    path = OUT / f"{name}.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run {name} first")
    return _load(path)


def _chosen() -> str | None:
    path = OUT / "development.json"
    return _load(path).get("chosen") if path.exists() else None


def run(stage: str, arms: list[str], jobs: int) -> dict[str, Any]:
    """Play ``arms`` on the stage's seeds (all in one pool), store the games, summarize."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    if not arms or any(arm not in ARMS for arm in arms):
        raise ValueError(f"arms must be some of {tuple(ARMS)}, not {arms}")
    if stage == "development":
        promoted = _stage_result("screening")["promoted"]
        if not all(promoted.get(arm) for arm in arms):
            raise ValueError(f"not every arm of {arms} was promoted by screening")
    elif stage == "heldout":
        chosen = _chosen()
        if chosen is None or arms != [chosen]:
            raise ValueError(f"the held-out stage plays only development's chosen arm "
                             f"({chosen}), not {arms}")
        if not (OUT / "predeclared.md").exists():
            raise ValueError(f"{OUT / 'predeclared.md'} is missing: predeclare first")
    for arm in arms:
        if games_path(stage, arm).exists():
            raise ValueError(f"{games_path(stage, arm)} exists already")
    seeds = _seeds(stage)
    _require_ready(stage, seeds)
    versions = runner._record_versions()
    PARTIAL.mkdir(parents=True, exist_ok=True)
    if stage == "heldout":  # every call, also a resume; kept out of the tree until the end
        replay = heldout_replay(jobs) | {"versions": versions}
        _write(PARTIAL / REPLAY_CHECK, replay)
        if replay["matched"] != replay["games"]:
            a, b = replay["part_a_017"], replay["part_b_d3"]
            raise ValueError(
                f"held-out replay failed: {a['matched']} of {a['games']} stored games of 017 "
                f"and {b['matched']} of {b['games']} of 026's d3 replay input for input "
                f"on this build (mismatched d3 seeds {b['mismatched_seeds']})")
    frozen, net = register.load_frozen("v15")
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
                  "versions": versions, "arm": arm, "search": _search(arm),
                  "frozen_sha256": headers[arm]["header"]["frozen_sha256"], "set": stage,
                  "seeds": seeds, "wall_seconds": round(time.perf_counter() - tick, 1),
                  "episodes": [done[arm][seed] for seed in seeds]}
        with gzip.open(games_path(stage, arm), "wt", encoding="utf-8") as out:
            json.dump(record, out, separators=(",", ":"))
        partials[arm].unlink()
    if stage == "heldout":
        (PARTIAL / REPLAY_CHECK).replace(OUT / REPLAY_CHECK)
    return summarize(stage, versions=versions)


# ---------------------------------------------------------------- summary

def _load_arm(stage: str, arm: str) -> dict[str, Any]:
    with gzip.open(games_path(stage, arm), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def summarize(stage: str, versions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write OUT/<stage>.json: the summaries, the paired results and the rule's verdicts."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    seeds = _seeds(stage)
    base = _base_episodes(stage, seeds)
    if stage == "heldout":
        reference = e25._baseline("heldout")
    else:
        reference = register.load_games(stage, "017")["episodes"]
    if [e["seed"] for e in reference] != seeds:
        raise ValueError(f"017's {stage} games are not the stage's seeds in order")
    present = [arm for arm in ARMS if games_path(stage, arm).exists()]
    if not present:
        raise ValueError(f"no arm has played the {stage} set")
    episodes = {BASE: base, "017": reference}
    for arm in present:
        episodes[arm] = _load_arm(stage, arm)["episodes"]
        if [e["seed"] for e in episodes[arm]] != seeds:
            raise ValueError(f"{arm}'s {stage} games are not the stage's seeds in order")
    paired = {arm: _paired(episodes[arm], base) for arm in present}
    result: dict[str, Any] = {
        "experiment": "027-deeper-39", "stage": stage, "games": len(base),
        "seeds": ("Experiment 012's 1,000 held-out seeds (the established record benchmark)"
                  if stage == "heldout" else f"the register's {stage} set"),
        "arms": present, "base": BASE, "search": {arm: _search(arm) for arm in ARMS},
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "frozen_sha256": {"v15": _sha("v15"), "017": _sha("017")},
        "rule": RULE, "min_effect": MIN_EFFECT,
        "summary": {name: _summary(eps) for name, eps in episodes.items()},
        "paired_vs_d3": paired,
        "paired_vs_017": {name: _paired(eps, reference) for name, eps in episodes.items()
                          if name != "017"}}
    mean = {arm: paired[arm]["total"]["score"]["mean"] for arm in present}
    low = {arm: paired[arm]["total"]["score"]["ci95_low"] for arm in present}
    if stage == "screening":
        result["promoted"] = {arm: mean[arm] >= MIN_EFFECT for arm in present}
    elif stage == "development":
        kept = {arm: mean[arm] >= MIN_EFFECT and low[arm] > 0 for arm in present}
        result["kept"] = kept
        result["chosen"] = max((a for a in present if kept[a]), key=mean.get, default=None)
    else:
        result["passed"] = {arm: low[arm] > 0 for arm in present}
    _write(OUT / f"{stage}.json", result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment027")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="deep2 off against d3's stored games; arms below level")
    commands.add_parser("screen", help="every arm on the screening seeds")
    develop = commands.add_parser("develop", help="promoted arms on the development seeds")
    develop.add_argument("--arms", nargs="+", choices=tuple(ARMS))
    commands.add_parser("heldout", help="development's chosen arm on 012's seeds")
    commands.add_parser("summarize", help="summarize a stage").add_argument("stage",
                                                                           choices=STAGES)
    for name, sub in commands.choices.items():
        if name != "summarize":
            sub.add_argument("--jobs", type=int, default=12 if name == "check" else 28)
    args = parser.parse_args(argv)
    try:
        if args.command == "summarize":
            summarize(args.stage)
            print(f"Wrote {OUT / f'{args.stage}.json'}")
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "screen":
            run("screening", list(ARMS), args.jobs)
        elif args.command == "develop":
            arms = args.arms or [a for a, ok in _stage_result("screening")["promoted"].items()
                                 if ok]
            if not arms:
                raise ValueError("screening promoted no arm")
            run("development", arms, args.jobs)
        else:
            chosen = _chosen()
            if chosen is None:
                raise ValueError("development chose no arm")
            run("heldout", [chosen], args.jobs)
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
