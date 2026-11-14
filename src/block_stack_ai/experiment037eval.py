"""Run Experiment 037's final evaluation: ``v37`` against 036's stored ``v36`` games.

    python -m block_stack_ai.experiment037eval gate [--jobs N]
    python -m block_stack_ai.experiment037eval develop [--jobs N]
    python -m block_stack_ai.experiment037eval heldout [--jobs N]
    python -m block_stack_ai.experiment037eval summarize STAGE

036's final evaluation (``experiment036eval``) with ``v37`` (``experiment037 choose``) as
the arm and 036's stored ``v36`` games as the base. ``gate``: 032's 30 Hz replay gate and
the first 28 stored ``v36`` development and held-out games re-run (predeclared.md).
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

from . import experiment025 as e25, experiment032eval as e32eval, experiment033 as e33
from . import experiment034 as e34
from . import experiment036 as e36, experiment037 as e37, native, runner

OUT = e37.OUT
GAMES = e37.GAMES
PARTIAL = runner.PROJECT_ROOT / "runs" / "037eval"
GATE = OUT / "record_gate.json"
SCHEMA = e36.SCHEMA
STAGES = ("development", "heldout")
ARM, BASE = "v37", "v36"
MIN_EFFECT = 15_000
RULE = ("Mean final score of v37 minus 036's stored v36 games on the same seeds, paired "
        "by seed, 95% bootstrap interval of experiment012.paired (10,000 resamples, RNG seed "
        "12), both at 20 Hz / 300 ms with 035's search. Development (the register's 500): kept "
        "if the paired mean is +15,000 or more and the interval's lower end is above 0. "
        "Held-out (012's 1,000): a new 20 Hz / 300 ms record if the interval's lower end is "
        "above 0, after the gate matched on this library (140/140 stored 30 Hz record games, "
        "56/56 stored v36 games).")

_load, _write = e36._load, e36._write


def v37() -> dict[str, Any]:
    """The agent ``decision.json`` names, its networks' shas checked."""
    if not e37.DECISION.exists():
        raise ValueError(f"{e37.DECISION} is missing: run experiment037 choose")
    found = e36._load(e37.DECISION)
    if found["v37"] is None:
        raise ValueError("037 named no v37: there is no final evaluation")
    agent = found["agent"]
    shas = [e36._sha(e36._path(p)) for p in (agent["early"], agent["mid"], agent["late"])]
    if shas != agent["shas"] or agent["late"] != e36.LATE:
        raise ValueError("v36's networks changed after the decision")
    return agent


def games_path(stage: str) -> Path:
    return GAMES / f"{stage}-{ARM}.json.gz"


# ---------------------------------------------------------------- the gate

def _replay(stage: str, jobs: int) -> dict[str, Any]:
    """The first 28 stored v36 games of ``stage``, re-run by 036's game."""
    return e37.replay_v36(stage, jobs)


def gate(jobs: int) -> dict[str, Any]:
    """Write GATE: does this build still play the stored record games input for input?"""
    e37._require_ready()
    v37()
    thirty = e32eval.heldout_replay(jobs)
    twenty = {stage: _replay(stage, jobs) for stage in STAGES}
    games = thirty["games"] + sum(p["games"] for p in twenty.values())
    matched = thirty["matched"] + sum(p["matched"] for p in twenty.values())
    result = {"experiment": "037", "part_30hz": thirty, "part_20hz_v36": twenty,
              "games": games, "matched_games": matched, "matched": matched == games,
              "library": e36.library_record(), "versions": runner._record_versions()}
    _write(GATE, result)
    return result


# ---------------------------------------------------------------- the stages

def _stage_result(stage: str) -> dict[str, Any]:
    path = OUT / f"{stage}.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run {stage} first")
    return _load(path)


def _require_gate(library: dict[str, Any]) -> None:
    found = _load(GATE) if GATE.exists() else {}
    if not found.get("matched") or found.get("library") != library:
        raise ValueError(f"{GATE} is missing or not matched on this library: run gate")


def _require_development_kept() -> None:
    if not _stage_result("development")["kept"]:
        raise ValueError("development did not keep v37")


def _require_ready(stage: str) -> None:
    """037's guards, v37 named, the gate matched on this very library, and for held-out:
    development kept."""
    e37._require_ready()
    v37()
    _require_gate(e36.library_record())
    if stage == "heldout":
        _require_development_kept()


def play(stage: str, jobs: int) -> Path:
    """Play v37 on the stage's seeds (resuming from the partial file), store the games. An
    agent with v36's V18 below 230 lines must play the stored v36 game's inputs before 230
    lines on every seed (stops otherwise)."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    target = games_path(stage)
    if target.exists():
        return target
    _require_ready(stage)
    agent, seeds = v37(), e25._seeds(stage)
    stored = e37.ref()["by_seed"][stage]
    if list(stored) != seeds:
        raise ValueError(f"the stored v36 {stage} games are not the stage's seeds")
    e34._require_committed(*(e37._path(agent[k]) for k in ("early", "mid", "late")))
    guard = agent["early"] == e37.V36_EARLY
    frozen = e33._frozen()[0]
    versions, library = runner._record_versions(), e36.library_record()
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": ARM, "stage": stage, "agent": agent, "search": e36.search(),
                         "format": fmt, "library": library, "versions": versions,
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest()}}
    PARTIAL.mkdir(parents=True, exist_ok=True)
    partial = PARTIAL / f"{stage}-{ARM}.partial.jsonl"
    done = e36.resume(partial, header)
    todo = [(seed, agent["early"], agent["mid"], ARM) for seed in seeds if seed not in done]
    print(f"{stage} {ARM}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(e36._probe_job, todo, chunksize=1):
            s = episode["seed"]
            if guard and not e34.prefix_matches(frozen, s, base64.b64decode(stored[s]["inputs"]),
                                                base64.b64decode(episode["inputs"])):
                raise ValueError(f"{stage}: seed {s} differs from v36 before 230 lines: "
                                 f"stopped (the games stay in {partial})")
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            if len(done) % 20 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{stage} {ARM} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "arm": ARM, "set": stage,
              "agent": agent, "search": e36.search(), "format": fmt, "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[seed] for seed in seeds]}
    GAMES.mkdir(parents=True, exist_ok=True)
    staged = PARTIAL / target.name
    with gzip.open(staged, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    staged.replace(target)
    partial.unlink()
    return target


def verdict(stage: str, score: dict[str, float]) -> dict[str, bool]:
    """The predeclared rule for a stage, from the paired score's mean and interval."""
    if stage == "development":
        return {"kept": bool(score["mean"] >= MIN_EFFECT and score["ci95_low"] > 0)}
    return {"passed": bool(score["ci95_low"] > 0)}


def summarize(stage: str) -> dict[str, Any]:
    """Write OUT/<stage>.json: both arms' figures, the paired result and the verdict."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    with gzip.open(games_path(stage), "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    seeds = e25._seeds(stage)
    mine = record["episodes"]
    base = list(e37.ref()["by_seed"][stage].values())
    if [e["seed"] for e in mine] != seeds or [e["seed"] for e in base] != seeds:
        raise ValueError(f"the {stage} games are not the stage's seeds in order")
    if record["agent"] != v37() or record["search"] != e36.search():
        raise ValueError(f"{ARM}'s {stage} games were played by another agent or search")
    if record["format"] != e33.format_of(e33._frozen()[0]):
        raise ValueError(f"{ARM}'s {stage} games were not played in the 20 Hz format")
    _require_gate(record["library"])  # the games' own library passed the gate
    if stage == "heldout":
        _require_development_kept()
    paired = e25._paired(mine, base)
    result = {"experiment": "037", "stage": stage, "games": len(seeds),
              "seeds": ("Experiment 012's 1,000 held-out seeds (the established record "
                        "benchmark)" if stage == "heldout" else "the register's development set"),
              "arm": ARM, "agent": record["agent"], "base": f"{BASE} (036's stored games)",
              "search": record["search"], "format": record["format"], "rule": RULE,
              "style": {BASE: e36.e35.style(base), ARM: e36.e35.style(mine)},
              "paired_vs_v36": paired, "library": record["library"],
              "versions": record["versions"]}
    result |= verdict(stage, paired["total"]["score"])
    _write(OUT / f"{stage}.json", result)
    return result


def _line(result: dict[str, Any]) -> str:
    score = result["paired_vs_v36"]["total"]["score"]
    mine = result["style"][ARM]
    flag = {k: result[k] for k in ("kept", "passed") if k in result}
    return (f"{result['stage']}: {ARM} {mine['mean_score']:,.0f}, paired "
            f"{score['mean']:+,.0f} ({score['ci95_low']:+,.0f}, {score['ci95_high']:+,.0f}) "
            f"{flag}; {mine['seconds_per_game']:.0f} s a game")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment037eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gate", help="replay stored record games on this build")
    commands.add_parser("develop", help="v37 on the 500 development seeds")
    commands.add_parser("heldout", help="v37 on 012's 1,000 held-out seeds, if kept")
    commands.add_parser("summarize", help="summarize a stage").add_argument("stage",
                                                                           choices=STAGES)
    for name, sub in commands.choices.items():
        if name != "summarize":
            sub.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "gate":
            found = gate(args.jobs)
            print(f"gate: {found['matched_games']}/{found['games']} matched")
            return 0 if found["matched"] else 1
        stage = {"develop": "development", "heldout": "heldout"}.get(args.command, None)
        if stage:
            play(stage, args.jobs)
        print(_line(summarize(stage or args.stage)))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
