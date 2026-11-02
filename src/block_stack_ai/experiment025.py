"""Run Experiment 025: hybrids of 023's value agent (V) and 017's agent (H).

    python -m block_stack_ai.experiment025 check [--jobs N]
    python -m block_stack_ai.experiment025 screen [--jobs N]
    python -m block_stack_ai.experiment025 develop [--arms ARM ...] [--jobs N]
    python -m block_stack_ai.experiment025 confirm [--arms ARM ...] [--jobs N]
    python -m block_stack_ai.experiment025 heldout [--arms ARM ...] [--jobs N]
    python -m block_stack_ai.experiment025 summarize STAGE

Each arm plays the register's screening (100), development (500) or confirmation (200)
seeds, then (after predeclared.md) Experiment 012's 1,000 held-out seeds, with
native/hybrid.hpp's agent (V below the switch level and H from it, or the reverse), both
policies exactly as frozen in experiments/register/frozen/. The games are stored like the
register's (``runs/025`` partial files make a run resumable) and ``summarize`` pairs
every arm with 017's registered games on the same seeds (on the held-out seeds, 017's stored
record games) and applies the plan's rule.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

from . import experiment012 as e12, experiment013 as e13
from . import experiment016 as e16, native, register, runner, step0a

OUT = runner.PROJECT_ROOT / "experiments" / "025-hybrids"
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "025"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "confirmation", "heldout")
# arm: (V plays first, switch level)
ARMS = {"v_h29": (True, 29), "v_h39": (True, 39), "h_v39": (False, 39)}
MIN_EFFECT = 40_000
REPLAY_CHECK = "heldout_replay_check.json"
RULE = ("Primary metric: mean final score, paired by seed against 017's registered games "
        "(hybrid minus 017), 95% bootstrap interval of experiment012.paired. Screening: an "
        "arm is promoted if its paired mean is +40k or more. Development: an arm is kept if "
        "its paired mean is at least +40k and its interval's lower end is above 0; of the "
        "kept arms the one with the higher mean is chosen. Confirmation: the chosen arm passes "
        "if its interval's lower end is above 0. Held-out (after predeclared.md): the same, on "
        "012's seeds, paired against 017's stored record games, after 28 of those games replay "
        "input for input on the build.")

_load, _write = e13._load, e13._write


def frozen_configs() -> tuple[dict[str, Any], dict[str, Any], bytes]:
    """The frozen 017 and v15 configurations and V's weights; their setups must agree."""
    h, _ = register.load_frozen("017")
    v, net = register.load_frozen("v15")
    for key in ("game", "line_cap", "frame_cap", "formats"):
        if h[key] != v[key]:
            raise ValueError(f"frozen 017 and v15 differ in {key}")
    return h, v, net


def play_arm_game(job: tuple[str, dict[str, Any], bytes, int]) -> dict[str, Any]:
    """One checked game of ``arm`` (register.checked_game), with the switch's entry state."""
    arm, frozen, net, seed = job
    v_first, level = ARMS[arm]
    params = native.params(frozen["params"])

    def play() -> dict[str, Any]:
        return native.hybrid_game(net, frozen["game"], seed, v_first=v_first,
                                  switch_level=level, line_cap=frozen["line_cap"],
                                  frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
                                  params=params)

    episode = register.checked_game(frozen, seed, play, agent=arm)
    return episode | {"switch": episode["stats"]["entry"][str(level)]}


WIRING = OUT / "wiring_check.json"
WIRING_GAMES = 3


def _wiring_job(job: tuple[str, dict[str, Any], dict[str, Any], bytes, dict[str, Any]]
                ) -> dict[str, Any]:
    kind, h, v, net, reference = job
    seed = reference["seed"]
    args = dict(line_cap=h["line_cap"], frame_cap=h["frame_cap"], limits=e13._limits(h))
    if kind == "h_alone":  # H plays at every level: 017's recorded game
        played = native.hybrid_game(net, h["game"], seed, v_first=True, switch_level=0, **args,
                                    params=native.params(h["params"]))
        got, want = base64.b64encode(played["inputs"]).decode("ascii"), reference["inputs"]
    else:  # V plays at every level: 023's reference score and lines, and net_game's inputs
        played = native.hybrid_game(net, v["game"], seed, v_first=False, switch_level=0, **args,
                                    params=native.params(h["params"]))
        pure = native.net_game(net, v["game"], seed, **args)[0]
        got = [played["score"], played["lines"], played["inputs"] == pure["inputs"]]
        want = [reference["score"], reference["lines"], True]
    return {"kind": kind, "seed": seed, "match": got == want,
            "got": None if got == want else got, "want": None if got == want else want}


def wiring_check(jobs: int) -> dict[str, Any]:
    """The hybrid agent with the frozen configurations, one policy at every level, against
    the registered references: 017's recorded inputs (byte for byte) and v15's score and
    lines (and net_game's inputs), on each reference's first games."""
    h, v, net = frozen_configs()
    work = [("h_alone", h, v, net, ref) for ref in register._reference("017", WIRING_GAMES)]
    work += [("v_alone", h, v, net, ref) for ref in register._reference("v15", WIRING_GAMES)]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, work, chunksize=1)
    result = {"experiment": "025-hybrids", "games": found,
              "matched": all(g["match"] for g in found),
              "frozen_sha256": {"017": _sha("017"), "v15": _sha("v15")},
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


def _seeds(stage: str) -> list[int]:
    """The stage's seeds: the register's, or Experiment 012's held-out seeds."""
    if stage == "heldout":
        return _load(runner.PROJECT_ROOT / "experiments" / "012-native-cem"
                     / "seeds.json")["heldout_seeds"]
    return register.set_seeds(stage)


def _baseline(stage: str, jobs: int = 4) -> list[dict[str, Any]]:
    """017's episodes on the stage's seeds: the register's games, or the stored record."""
    if stage != "heldout":
        return register.load_games(stage, "017")["episodes"]
    episodes = step0a.heldout_017(jobs)
    if [e["seed"] for e in episodes] != _seeds(stage):
        raise ValueError("017's stored held-out games are not the held-out seeds in order")
    return episodes


def _require_ready(stage: str, seeds: list[int]) -> None:
    """Refuse a dirty tree, an unmatched wiring check, or 017 baseline games that are not
    the stage's seeds in order from the current frozen 017."""
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION or \
            wiring.get("frozen_sha256") != {"017": _sha("017"), "v15": _sha("v15")}:
        raise ValueError(f"{WIRING} is missing, not all matched, or from another build or "
                         "frozen agents: run check first")
    if stage == "heldout":  # the stored record: no frozen-sha check
        _baseline(stage)
        return
    path = register.games_path(stage, "017")
    if not path.exists():
        raise ValueError(f"{path} is missing: play 017 on the {stage} set first")
    base = register.load_games(stage, "017")
    if [e["seed"] for e in base["episodes"]] != seeds or base["seeds"] != seeds:
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    if base["frozen_sha256"] != _sha("017"):
        raise ValueError(f"{path} was played with another frozen 017 than the current one")


def _sha(name: str) -> str:
    return hashlib.sha256(register.frozen_path(name).read_bytes()).hexdigest()


def _header(arm: str, seeds: list[int], versions: dict[str, Any]) -> dict[str, Any]:
    return {"header": {"frozen_sha256": {"017": _sha("017"), "v15": _sha("v15")}, "arm": arm,
                       "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                       "abi_version": native.ABI_VERSION, "versions": versions}}


def games_path(stage: str, arm: str) -> Path:
    return GAMES / f"{stage}-{arm}.json.gz"


def _promoted(arms: list[str]) -> None:
    path = OUT / "screening.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run screening first")
    promoted = _load(path)["promoted"]
    for arm in arms:
        if not promoted.get(arm):
            raise ValueError(f"{arm} was not promoted by screening")


def _resume(partial: Path, header: dict[str, Any]) -> dict[int, dict[str, Any]]:
    done: dict[int, dict[str, Any]] = {}
    if partial.exists():
        text = partial.read_text(encoding="utf-8")
        lines = text.split("\n")
        if json.loads(lines[0]) != header:
            raise ValueError(f"{partial} is from another run (arm, seeds, build or code); "
                             "move it away to start again")
        if text and not text.endswith("\n"):  # a cut-off last line: end it before appending
            with partial.open("a", encoding="utf-8") as handle:
                handle.write("\n")
        for line in lines[1:]:
            try:
                episode = json.loads(line)
            except json.JSONDecodeError:
                continue  # a blank or cut-off last line
            done[episode["seed"]] = episode
    else:
        partial.write_text(json.dumps(header) + "\n", encoding="utf-8")
    return done


def _chosen() -> str | None:
    path = OUT / "development.json"
    return _load(path).get("chosen") if path.exists() else None


def _passed() -> dict[str, bool]:
    path = OUT / "confirmation.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run confirmation first")
    return _load(path)["passed"]


def run(stage: str, arms: list[str], jobs: int) -> dict[str, Any]:
    """Play ``arms`` on the stage's seeds (all in one pool), store the games, summarize."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    unknown = [arm for arm in arms if arm not in ARMS]
    if unknown or not arms:
        raise ValueError(f"arms must be some of {tuple(ARMS)}, not {arms}")
    if stage == "development":
        _promoted(arms)
    elif stage == "confirmation":
        chosen = _chosen()
        if chosen is None or any(arm != chosen for arm in arms):
            raise ValueError(f"confirmation plays only development's chosen arm ({chosen})")
    elif stage == "heldout":
        passed = _passed()
        for arm in arms:
            if not passed.get(arm):
                raise ValueError(f"{arm} did not pass confirmation")
        if not (OUT / "predeclared.md").exists():
            raise ValueError(f"{OUT / 'predeclared.md'} is missing: predeclare first")
    for arm in arms:
        if games_path(stage, arm).exists():
            raise ValueError(f"{games_path(stage, arm)} exists already")
    seeds = _seeds(stage)
    _require_ready(stage, seeds)
    versions = runner._record_versions()
    if stage == "heldout":  # every call, also a resume; kept out of the tree until the end
        replay = register.check_frozen("017", 28, jobs)
        PARTIAL.mkdir(parents=True, exist_ok=True)
        _write(PARTIAL / REPLAY_CHECK, replay)
        if replay["matched"] != replay["games"]:
            raise ValueError(f"only {replay['matched']} of {replay['games']} stored held-out "
                             "games of 017 replay input for input on this build")
    frozen, _, net = frozen_configs()
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
                  "versions": versions, "arm": arm, "switch": dict(zip(
                      ("v_first", "switch_level"), ARMS[arm])),
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


def _rows(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"seed": e["seed"], "score": e["result"]["score"], "lines": e["result"]["lines"]}
            for e in episodes]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _entry(episodes: list[dict[str, Any]], level: str) -> dict[str, Any]:
    """Mean board of the games that reached ``level`` (None where none did)."""
    found = [e["stats"]["entry"][level] for e in episodes if e["stats"]["entry"][level]]
    return {"games": len(found)} | {key: _mean([f[key] for f in found])
                                    for key in ("max_height", "aggregate_height", "holes")}


def _summary(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    results = [e["result"] for e in episodes]
    lines, count = [r["lines"] for r in results], len(episodes)
    top = [e["stats"]["bands"]["39+"] for e in episodes]
    reached = [e for e in episodes if e["stats"]["entry"]["39"]]
    return {
        "games": count, "mean_score": _mean([r["score"] for r in results]),
        "mean_lines": _mean(lines), "median_lines": statistics.median(lines),
        "share_lines_below_230": sum(x < 230 for x in lines) / count,
        "share_lines_below_330": sum(x < 330 for x in lines) / count,
        "line_cap_share": sum(x >= 430 for x in lines) / count,
        "tetris_rate": 4 * sum(r["clear_sizes"]["tetrises"] for r in results) / sum(lines),
        "p_reach_29": sum(e["stats"]["entry"]["29"] is not None for e in episodes) / count,
        "p_reach_39": len(reached) / count,
        "score_39_plus_all": _mean(top),
        "score_39_plus_reached": _mean([e["stats"]["bands"]["39+"] for e in reached]),
        "entry_29": _entry(episodes, "29"), "entry_39": _entry(episodes, "39"),
        "seconds_per_game": _mean([r["decision_seconds"] for r in results])}


def _paired(episodes: list[dict[str, Any]], base: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [e["result"]["score"] for e in episodes]
    base_scores = [e["result"]["score"] for e in base]
    spread = np.std(scores) * np.std(base_scores)
    return {"total": e12.paired(_rows(episodes), _rows(base)),
            "by_band": e16._band_pairs([e["stats"] for e in episodes],
                                       [e["stats"] for e in base]),
            "score_correlation": float(np.corrcoef(scores, base_scores)[0, 1]) if spread else None}


def summarize(stage: str, versions: dict[str, Any] | None = None, jobs: int = 4
              ) -> dict[str, Any]:
    """Write OUT/<stage>.json: the summaries, the paired results and the rule's verdicts."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    base = _baseline(stage, jobs)
    episodes = {"017": base}
    if register.games_path(stage, "v15").exists():
        episodes["v15"] = register.load_games(stage, "v15")["episodes"]
    present = [arm for arm in ARMS if games_path(stage, arm).exists()]
    if not present:
        raise ValueError(f"no arm has played the {stage} set")
    for arm in present:
        episodes[arm] = _load_arm(stage, arm)["episodes"]
    summary = {name: _summary(eps) for name, eps in episodes.items()}
    paired = {name: _paired(eps, base) for name, eps in episodes.items()
              if name != "017"}
    result: dict[str, Any] = {
        "experiment": "025-hybrids", "stage": stage, "games": len(base),
        "seeds": f"the register's {stage} set", "arms": present,
        "switches": {arm: dict(zip(("v_first", "switch_level"), ARMS[arm])) for arm in ARMS},
        "versions": versions or runner._record_versions(), "abi_version": native.ABI_VERSION,
        "frozen_sha256": {"017": _sha("017"), "v15": _sha("v15")},
        "rule": RULE, "min_effect": MIN_EFFECT, "summary": summary, "paired_vs_017": paired}
    mean = {arm: paired[arm]["total"]["score"]["mean"] for arm in present}
    if stage == "screening":
        result["promoted"] = {arm: mean[arm] >= MIN_EFFECT for arm in present}
    elif stage in ("confirmation", "heldout"):
        result["passed"] = {arm: paired[arm]["total"]["score"]["ci95_low"] > 0
                            for arm in present}
        if stage == "heldout":
            result["seeds"] = ("Experiment 012's 1,000 held-out seeds (the established record "
                               "benchmark)")
            result["baseline"] = ("017's stored held-out record games "
                                  "(experiments/017-commit-rollouts/records/run.json.gz), "
                                  f"28 of them replayed on this build: {REPLAY_CHECK}")
    else:
        kept = {arm: mean[arm] >= MIN_EFFECT
                and paired[arm]["total"]["score"]["ci95_low"] > 0 for arm in present}
        result["kept"] = kept
        result["chosen"] = max((a for a in present if kept[a]), key=mean.get, default=None)
    _write(OUT / f"{stage}.json", result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment025")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="the hybrid with one policy alone against the references"
                        ).add_argument("--jobs", type=int, default=4)
    screen = commands.add_parser("screen", help="all three arms on the screening seeds")
    develop = commands.add_parser("develop", help="promoted arms on the development seeds")
    develop.add_argument("--arms", nargs="+", choices=tuple(ARMS))
    confirm = commands.add_parser("confirm", help="the chosen arm on the confirmation seeds")
    heldout = commands.add_parser("heldout", help="the passing arms on the held-out seeds")
    for sub in (confirm, heldout):
        sub.add_argument("--arms", nargs="+", choices=tuple(ARMS))
    for sub in (screen, develop, confirm, heldout):
        sub.add_argument("--jobs", type=int, default=28)
    commands.add_parser("summarize", help="summarize a stage").add_argument("stage",
                                                                           choices=STAGES)
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
        elif args.command == "confirm":
            chosen = _chosen()
            if args.arms is None and chosen is None:
                raise ValueError("development chose no arm")
            run("confirmation", args.arms or [chosen], args.jobs)
        elif args.command == "heldout":
            arms = args.arms or [a for a, ok in _passed().items() if ok]
            if not arms:
                raise ValueError("confirmation passed no arm")
            run("heldout", arms, args.jobs)
        else:
            arms = args.arms
            if arms is None:
                path = OUT / "screening.json"
                if not path.exists():
                    raise ValueError(f"{path} is missing: run screening first")
                arms = [a for a, ok in _load(path)["promoted"].items() if ok]
                if not arms:
                    raise ValueError("screening promoted no arm")
            run("development", arms, args.jobs)
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
