"""Run Experiment 028: does 027's record agent gain from handing over to 017 at level 39?

    python -m block_stack_ai.experiment028 check [--jobs N]
    python -m block_stack_ai.experiment028 screen [--jobs N]
    python -m block_stack_ai.experiment028 develop [--jobs N]
    python -m block_stack_ai.experiment028 heldout [--jobs N]
    python -m block_stack_ai.experiment028 summarize STAGE

The arm plays 027's record agent ``e29_k4`` (frozen ``v15``, native ``deep_net_game``'s
search) below a switch level and 017's frozen agent from it on (native ``deep_hybrid_game``,
see plan.md). ``summarize`` pairs it with 027's stored e29_k4 games on the same seeds (the
rule) and with 017's (reported only). ``heldout`` plays development's chosen arm on
Experiment 012's held-out seeds against 027's record games of e29_k4 (the rule) and 017's
stored record games.
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

from . import experiment013 as e13, experiment025 as e25, experiment027 as e27
from . import native, register, runner
from .experiment025 import _paired, _resume, _summary

OUT = runner.PROJECT_ROOT / "experiments" / "028-hybrid-017-at-39"
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "028"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "heldout")
BASE = "e29_k4"  # 027's chosen arm, the record
COMMIT_LEVEL, ADJUST_K, ADJUST_MAX_LEVEL = e27.COMMIT_LEVEL, e27.ADJUST_K, e27.ADJUST_MAX_LEVEL
DEEP2_LEVEL, DEEP2_K = e27.ARMS[BASE]
NEVER = 1000  # a switch level no game reaches: the base agent alone
# arm: the level from which 017 plays
ARMS = {"h39": 39}
MIN_EFFECT = 10_000
REPLAY_CHECK = "heldout_replay_check.json"
REPLAY_GAMES = 28
RULE = ("Primary metric: mean final score, paired by seed against 027's stored games of "
        "e29_k4 (arm minus e29_k4), 95% bootstrap interval of experiment012.paired. "
        "Screening: an arm is promoted if its paired mean is +10k or more. Development: an "
        "arm is kept if its paired mean is at least +10k and its interval's lower end is "
        "above 0; of the kept arms the one with the higher mean is chosen. 017's registered "
        "games are paired too (paired_vs_017) but are not part of the rule. Held-out (after "
        "predeclared.md): the chosen arm passes if its interval's lower end against 027's "
        "record games of e29_k4 on 012's held-out seeds is above 0, after 28 of 017's stored "
        "games and 28 of e29_k4's replay input for input on the build.")

_load, _write = e13._load, e13._write
WIRING = OUT / "wiring_check.json"
WIRING_GAMES = 3
EARLY_CAP = 320  # ends a game from level 18 before level 39


def _sha(name: str) -> str:
    return hashlib.sha256(register.frozen_path(name).read_bytes()).hexdigest()


def _play(net: bytes, frozen: dict[str, Any], seed: int, switch_level: int,
          line_cap: int | None = None) -> dict[str, Any]:
    """The hybrid game; ``frozen`` is 017's configuration (its game setup is v15's)."""
    return native.deep_hybrid_game(
        net, frozen["game"], seed, commit_level=COMMIT_LEVEL, adjust_k=ADJUST_K,
        adjust_max_level=ADJUST_MAX_LEVEL, deep2_level=DEEP2_LEVEL, deep2_k=DEEP2_K,
        switch_level=switch_level,
        line_cap=frozen["line_cap"] if line_cap is None else line_cap,
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
        params=native.params(frozen["params"]))


def _play_base(net: bytes, frozen: dict[str, Any], seed: int,
               line_cap: int | None = None) -> dict[str, Any]:
    """027's e29_k4 alone (native deep_net_game)."""
    return native.deep_net_game(
        net, frozen["game"], seed, commit_level=COMMIT_LEVEL, adjust_k=ADJUST_K,
        adjust_max_level=ADJUST_MAX_LEVEL, deep2_level=DEEP2_LEVEL, deep2_k=DEEP2_K,
        line_cap=frozen["line_cap"] if line_cap is None else line_cap,
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen))


def play_arm_game(job: tuple[str, dict[str, Any], bytes, int]) -> dict[str, Any]:
    """One checked game of ``arm`` (register.checked_game); ``BASE`` is e29_k4 itself."""
    arm, frozen, net, seed = job
    if arm == BASE:
        play = lambda: _play_base(net, frozen, seed)  # noqa: E731
    else:
        play = lambda: _play(net, frozen, seed, ARMS[arm])  # noqa: E731
    return register.checked_game(frozen, seed, play, agent=arm)


def _base_episodes(stage: str, seeds: list[int]) -> list[dict[str, Any]]:
    """027's stored games of e29_k4 on the stage, checked to be its seeds in order."""
    path = e27.games_path(stage, BASE)
    if not path.exists():
        raise ValueError(f"{path} is missing")
    record = e27._load_arm(stage, BASE)
    if record["search"] != e27._search(BASE) or \
            record["frozen_sha256"] != {"v15": _sha("v15")}:
        raise ValueError(f"{path} is not e29_k4's search with the current frozen v15")
    episodes = record["episodes"]
    if [e["seed"] for e in episodes] != seeds:
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    return episodes


def _seeds(stage: str) -> list[int]:
    return e25._seeds(stage)


def _frozen() -> tuple[dict[str, Any], bytes]:
    """017's frozen configuration (its game setup checked equal to v15's) and V's weights."""
    h, _, net = e25.frozen_configs()
    return h, net


# ---------------------------------------------------------------- wiring

def _wiring_job(job: tuple[str, dict[str, Any], bytes, dict[str, Any]]) -> dict[str, Any]:
    kind, frozen, net, reference = job
    seed = reference["seed"]
    if kind == "never_switch_is_e29_k4":  # 027's stored game: inputs, score, lines
        played = _play(net, frozen, seed, NEVER)
        got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
               played["lines"]]
        want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    elif kind == "switch_at_start_is_017":  # 017's registered game, input for input
        played = _play(net, frozen, seed, 0)
        got = [base64.b64encode(played["inputs"]).decode("ascii")]
        want = [reference["inputs"]]
    else:  # h39 under a line cap below level 39: e29_k4's game under the same cap
        played = _play(net, frozen, seed, ARMS["h39"], line_cap=EARLY_CAP)
        plain = _play_base(net, frozen, seed, line_cap=EARLY_CAP)
        got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
               played["lines"]]
        want = [base64.b64encode(plain["inputs"]).decode("ascii"), plain["score"],
                plain["lines"]]
    same = got == want
    inputs_same = got[0] == want[0]
    return {"kind": kind, "seed": seed, "match": same,
            "got": None if same else [inputs_same, *got[1:]],
            "want": None if same else [True, *want[1:]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """On the first screening seeds: the hybrid never switching against 027's stored
    e29_k4 games (inputs, score, lines) and h39 under a line cap of 320 against e29_k4
    under the same cap; switching at the start against 017's first registered reference
    games (its stored held-out record games, inputs)."""
    frozen, net = _frozen()
    base = _base_episodes("screening", _seeds("screening"))[:WIRING_GAMES]
    work = [("never_switch_is_e29_k4", frozen, net, e) for e in base]
    work += [("switch_at_start_is_017", frozen, net, ref)
             for ref in register._reference("017", WIRING_GAMES)]
    work += [("h39_before_39_is_e29_k4", frozen, net, e) for e in base]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, work, chunksize=1)
    result = {"experiment": "028-hybrid-017-at-39", "games": found,
              "matched": len(found) == 3 * WIRING_GAMES and all(g["match"] for g in found),
              "frozen_sha256": {"017": _sha("017"), "v15": _sha("v15")},
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


def _require_ready(stage: str, seeds: list[int]) -> None:
    """Refuse a dirty tree, an unmatched wiring check, or baselines that are not the
    stage's seeds in order (017's registered games also from the current frozen 017)."""
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION or \
            wiring.get("frozen_sha256") != {"017": _sha("017"), "v15": _sha("v15")}:
        raise ValueError(f"{WIRING} is missing, not all matched, or from another build or "
                         "frozen agents: run check first")
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
    (b) the first 28 of 027's e29_k4 record games replayed, inputs compared."""
    first = register.check_frozen("017", REPLAY_GAMES, jobs)
    frozen, net = _frozen()
    stored = _base_episodes("heldout", _seeds("heldout"))[:REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(play_arm_game, [(BASE, frozen, net, e["seed"]) for e in stored],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"experiment": "028-hybrid-017-at-39", "stage": "heldout",
            "part_a_017": first, "part_b_e29_k4": {
                "games": len(stored), "matched": len(stored) - len(bad), "mismatched_seeds": bad},
            "games": first["games"] + len(stored),
            "matched": first["matched"] + len(stored) - len(bad),
            "abi_version": native.ABI_VERSION}


def _header(arm: str, seeds: list[int], versions: dict[str, Any]) -> dict[str, Any]:
    return {"header": {"frozen_sha256": {"017": _sha("017"), "v15": _sha("v15")}, "arm": arm,
                       "setting": [COMMIT_LEVEL, ADJUST_K, ADJUST_MAX_LEVEL, DEEP2_LEVEL,
                                   DEEP2_K, ARMS[arm]],
                       "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                       "abi_version": native.ABI_VERSION, "versions": versions}}


def games_path(stage: str, arm: str) -> Path:
    return GAMES / f"{stage}-{arm}.json.gz"


def _search(arm: str) -> dict[str, int]:
    return e27._search(BASE) | {"switch_level": ARMS[arm]}


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
            a, b = replay["part_a_017"], replay["part_b_e29_k4"]
            raise ValueError(
                f"held-out replay failed: {a['matched']} of {a['games']} stored games of 017 "
                f"and {b['matched']} of {b['games']} of 027's e29_k4 replay input for input "
                f"on this build (mismatched e29_k4 seeds {b['mismatched_seeds']})")
    frozen, net = _frozen()
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
        "experiment": "028-hybrid-017-at-39", "stage": stage, "games": len(base),
        "seeds": ("Experiment 012's 1,000 held-out seeds (the established record benchmark)"
                  if stage == "heldout" else f"the register's {stage} set"),
        "arms": present, "base": BASE, "search": {arm: _search(arm) for arm in ARMS},
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "frozen_sha256": {"v15": _sha("v15"), "017": _sha("017")},
        "rule": RULE, "min_effect": MIN_EFFECT,
        "summary": {name: _summary(eps) for name, eps in episodes.items()},
        "paired_vs_e29_k4": paired,
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
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment028")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="the hybrid against e29_k4's and 017's stored games")
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
