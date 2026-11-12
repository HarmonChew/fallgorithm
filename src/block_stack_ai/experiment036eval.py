"""Run Experiment 036's final evaluation: ``v36`` against 035b's stored ``v29r20d`` games.

    python -m block_stack_ai.experiment036eval gate [--jobs N]
    python -m block_stack_ai.experiment036eval develop [--jobs N]
    python -m block_stack_ai.experiment036eval heldout [--jobs N]
    python -m block_stack_ai.experiment036eval summarize STAGE

``v36`` is the agent ``experiment036 choose`` named (``decision.json``); there is a final
evaluation only if it named one. Only ``v36`` is played; it is paired by seed with 035b's
stored ``v29r20d`` games of the same set (the same search, so the difference is teaching
alone). ``gate``: 032's 30 Hz replay gate (28 each of 017's, e29_k4's, v39's, v29's and
v39r's stored held-out games) and the first 28 stored ``v29r20d`` development and held-out
games re-run by this experiment's game (predeclared.md).
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

from . import experiment025 as e25, experiment032eval as e32eval, experiment033 as e33
from . import experiment036 as e36, native, runner

OUT = e36.OUT
GAMES = e36.GAMES
PARTIAL = runner.PROJECT_ROOT / "runs" / "036eval"
GATE = OUT / "record_gate.json"
SCHEMA = e36.SCHEMA
STAGES = ("development", "heldout")
ARM, BASE = "v36", "v29r20d"
MIN_EFFECT = 15_000
RULE = ("Mean final score of v36 minus 035b's stored v29r20d games on the same seeds, paired "
        "by seed, 95% bootstrap interval of experiment012.paired (10,000 resamples, RNG seed "
        "12), both at 20 Hz / 300 ms with 035's search. Development (the register's 500): kept "
        "if the paired mean is +15,000 or more and the interval's lower end is above 0. "
        "Held-out (012's 1,000): a new 20 Hz / 300 ms record if the interval's lower end is "
        "above 0, after the gate matched on this library (140/140 stored 30 Hz record games, "
        "56/56 stored v29r20d games).")

_load, _write = e36._load, e36._write


def v36() -> dict[str, Any]:
    """The agent ``decision.json`` names, its networks' shas checked."""
    if not e36.DECISION.exists():
        raise ValueError(f"{e36.DECISION} is missing: run experiment036 choose")
    found = e36._load(e36.DECISION)
    if found["v36"] is None:
        raise ValueError("036 named no v36: there is no final evaluation")
    agent = found["agent"]
    shas = [e36._sha(e36._path(p)) for p in (agent["early"], agent["mid"], agent["late"])]
    if shas != agent["shas"] or agent["late"] != e36.LATE:
        raise ValueError("v36's networks changed after the decision")
    return agent


def games_path(stage: str) -> Path:
    return GAMES / f"{stage}-{ARM}.json.gz"


# ---------------------------------------------------------------- the gate

def _replay(stage: str, jobs: int) -> dict[str, Any]:
    """The first 28 stored v29r20d games of ``stage``, re-run by 036's game."""
    return e36.replay_20hz(stage, jobs)


def gate(jobs: int) -> dict[str, Any]:
    """Write GATE: does this build still play the stored record games input for input?"""
    e36._require_ready()
    v36()
    thirty = e32eval.heldout_replay(jobs)
    twenty = {stage: _replay(stage, jobs) for stage in STAGES}
    games = thirty["games"] + sum(p["games"] for p in twenty.values())
    matched = thirty["matched"] + sum(p["matched"] for p in twenty.values())
    result = {"experiment": "036", "part_30hz": thirty, "part_20hz_v29r20d": twenty,
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
        raise ValueError("development did not keep v36")


def _require_ready(stage: str) -> None:
    """036's guards, v36 named, the gate matched on this very library, and for held-out:
    development kept."""
    e36._require_ready()
    v36()
    _require_gate(e36.library_record())
    if stage == "heldout":
        _require_development_kept()


def play(stage: str, jobs: int) -> Path:
    """Play v36 on the stage's seeds (resuming from the partial file), store the games. An
    agent with v15 below 230 lines must play the stored v29r20d game's inputs before 230
    lines on every seed (stops otherwise)."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    target = games_path(stage)
    if target.exists():
        return target
    _require_ready(stage)
    agent, seeds = v36(), e25._seeds(stage)
    stored = e36.reference()["by_seed"][stage]
    if list(stored) != seeds:
        raise ValueError(f"the stored v29r20d {stage} games are not the stage's seeds")
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
            if agent["v15_below_230"] and e36.prefix_check([episode], stored):
                raise ValueError(f"{stage}: seed {episode['seed']} differs from v29r20d before "
                                 f"230 lines: stopped (the games stay in {partial})")
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
    base = list(e36.reference()["by_seed"][stage].values())
    if [e["seed"] for e in mine] != seeds or [e["seed"] for e in base] != seeds:
        raise ValueError(f"the {stage} games are not the stage's seeds in order")
    if record["agent"] != v36() or record["search"] != e36.search():
        raise ValueError(f"{ARM}'s {stage} games were played by another agent or search")
    if record["format"] != e33.format_of(e33._frozen()[0]):
        raise ValueError(f"{ARM}'s {stage} games were not played in the 20 Hz format")
    _require_gate(record["library"])  # the games' own library passed the gate
    if stage == "heldout":
        _require_development_kept()
    paired = e25._paired(mine, base)
    result = {"experiment": "036", "stage": stage, "games": len(seeds),
              "seeds": ("Experiment 012's 1,000 held-out seeds (the established record "
                        "benchmark)" if stage == "heldout" else "the register's development set"),
              "arm": ARM, "agent": record["agent"], "base": f"{BASE} (035b's stored games)",
              "search": record["search"], "format": record["format"], "rule": RULE,
              "style": {BASE: e36.e35.style(base), ARM: e36.e35.style(mine)},
              "paired_vs_v29r20d": paired, "library": record["library"],
              "versions": record["versions"]}
    result |= verdict(stage, paired["total"]["score"])
    _write(OUT / f"{stage}.json", result)
    return result


def _line(result: dict[str, Any]) -> str:
    score = result["paired_vs_v29r20d"]["total"]["score"]
    mine = result["style"][ARM]
    flag = {k: result[k] for k in ("kept", "passed") if k in result}
    return (f"{result['stage']}: {ARM} {mine['mean_score']:,.0f}, paired "
            f"{score['mean']:+,.0f} ({score['ci95_low']:+,.0f}, {score['ci95_high']:+,.0f}) "
            f"{flag}; {mine['seconds_per_game']:.0f} s a game")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment036eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gate", help="replay stored record games on this build")
    commands.add_parser("develop", help="v36 on the 500 development seeds")
    commands.add_parser("heldout", help="v36 on 012's 1,000 held-out seeds, if kept")
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
