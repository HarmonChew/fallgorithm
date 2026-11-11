"""Run Experiment 035b: a 20 Hz record attempt for 035's combined search (predeclared-record.md).

    python -m block_stack_ai.experiment035eval gate [--jobs N]
    python -m block_stack_ai.experiment035eval develop [--jobs N]
    python -m block_stack_ai.experiment035eval heldout [--jobs N]
    python -m block_stack_ai.experiment035eval summarize STAGE

The arm ``v29r20d`` is 033's record agent ``v29r20`` (its networks unchanged) with the search
035 chose for 036 (``results.json`` ``search_for_036``: the deeper commit and the second
unknown piece from level 18, a third unknown piece at the commit from level 29). Only the arm
is played; it is paired by seed with 033's stored ``v29r20`` games of the same set, which the
gate first shows this build still plays input for input. ``gate``: 032's 30 Hz replay gate
(28 each of 017's, e29_k4's, v39's, v29's and v39r's stored held-out games) and the first 28
stored ``v29r20`` development and held-out games re-run with ``v29r20``'s own search.
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

from . import experiment013 as e13, experiment025 as e25, experiment032eval as e32eval
from . import experiment033 as e33, experiment034 as e34, experiment035 as e35
from . import native, runner

OUT = e35.OUT
GAMES = e35.GAMES
PARTIAL = runner.PROJECT_ROOT / "runs" / "035b"
PREDECLARED = OUT / "predeclared-record.md"
GATE = OUT / "record_gate.json"
SCHEMA = e35.SCHEMA
STAGES = ("development", "heldout")
ARM, BASE = "v29r20d", "v29r20"
MIN_EFFECT = 15_000
REPLAY_GAMES = 28
RULE = ("Mean final score of v29r20d (v29r20's networks with 035's combined search) minus "
        "033's stored v29r20 games on the same seeds, paired by seed, 95% bootstrap interval "
        "of experiment012.paired (10,000 resamples, RNG seed 12), both at 20 Hz / 300 ms. "
        "Development (the register's 500): kept if the paired mean is +15,000 or more and the "
        "interval's lower end is above 0. Held-out (012's 1,000): a new 20 Hz / 300 ms record "
        "if the interval's lower end is above 0, after the gate matched on this library "
        "(140/140 stored 30 Hz record games, 56/56 stored v29r20 games).")

_load, _write = e13._load, e13._write


def search() -> dict[str, Any]:
    """035's chosen search for 036, checked against the combined setting it played."""
    chosen = e35.decision()["search_for_036"]
    if chosen["arm"] != e35.COMBINED or chosen["search"] != e35.search_of(e35.COMBINED):
        raise ValueError("results.json's search_for_036 is not the combined setting 035 played")
    return chosen["search"]


def games_path(stage: str) -> Path:
    return GAMES / f"{stage}-{ARM}.json.gz"


def _sha_of(value: Any) -> str:
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


# ---------------------------------------------------------------- the gate

def _replay(stage: str, jobs: int) -> dict[str, Any]:
    """The first 28 stored v29r20 games of ``stage``, re-run with v29r20's own search."""
    stored = e34._stored_base(stage)[:REPLAY_GAMES]
    base = e35.base_search()
    with Pool(jobs) as pool:
        played = pool.map(e35.play_game, [(BASE, e["seed"], base) for e in stored],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"games": len(stored), "matched": len(stored) - len(bad), "mismatched_seeds": bad}


def gate(jobs: int) -> dict[str, Any]:
    """Write GATE: does this build still play the stored record games input for input?"""
    e35._require_ready()
    e34._require_committed(PREDECLARED)
    thirty = e32eval.heldout_replay(jobs)
    twenty = {stage: _replay(stage, jobs) for stage in STAGES}
    games = thirty["games"] + sum(p["games"] for p in twenty.values())
    matched = thirty["matched"] + sum(p["matched"] for p in twenty.values())
    result = {"experiment": "035b", "part_30hz": thirty, "part_20hz_v29r20": twenty,
              "games": games, "matched_games": matched, "matched": matched == games,
              "library": e35.library_record(), "versions": runner._record_versions()}
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
        raise ValueError("development did not keep v29r20d")


def _require_ready(stage: str) -> None:
    """035's checks (a clean tree outside the experiment, its plan, protocol, seeds and
    wiring check), this protocol committed, the gate matched on this very library, and for
    held-out: development kept."""
    e35._require_ready()
    e34._require_committed(PREDECLARED)
    _require_gate(e35.library_record())
    if stage == "heldout":
        _require_development_kept()


def play(stage: str, jobs: int) -> Path:
    """Play v29r20d on the stage's seeds (resuming from the partial file), store the games."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    target = games_path(stage)
    if target.exists():
        return target
    _require_ready(stage)
    setting, seeds = search(), e25._seeds(stage)
    e34._stored_base(stage)  # the stored base covers the stage's seeds in order
    versions, library = runner._record_versions(), e35.library_record()
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": ARM, "stage": stage, "search": setting, "format": fmt,
                         "weights_sha256": e35._sha(e34.base_path()),
                         "seeds_sha256": _sha_of(seeds), "library": library,
                         "versions": versions}}
    PARTIAL.mkdir(parents=True, exist_ok=True)
    partial = PARTIAL / f"{stage}-{ARM}.partial.jsonl"
    done = e25._resume(partial, header)
    todo = [(ARM, seed, setting) for seed in seeds if seed not in done]
    print(f"{stage} {ARM}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(e35.play_game, todo, chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            if len(done) % 20 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{stage} {ARM} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "arm": ARM, "set": stage,
              "search": setting, "format": fmt, "weights": e35.BASE_WEIGHTS,
              "weights_sha256": e35._sha(e34.base_path()), "seeds": seeds,
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
    mine, base = record["episodes"], e34._stored_base(stage)
    if [e["seed"] for e in mine] != seeds:
        raise ValueError(f"{ARM}'s {stage} games are not the stage's seeds in order")
    if record["search"] != search():
        raise ValueError(f"{ARM}'s {stage} games were played with another search")
    if record["format"] != e33.format_of(e33._frozen()[0]):
        raise ValueError(f"{ARM}'s {stage} games were not played in the 20 Hz format")
    if record["weights_sha256"] != e35._sha(e34.base_path()):
        raise ValueError(f"{ARM}'s {stage} games were not played with {e35.BASE_WEIGHTS}")
    _require_gate(record["library"])  # the games' own library passed the gate
    if stage == "heldout":
        _require_development_kept()
    paired = e25._paired(mine, base)
    result = {"experiment": "035b", "stage": stage, "games": len(seeds),
              "seeds": ("Experiment 012's 1,000 held-out seeds (the established record "
                        "benchmark)" if stage == "heldout" else "the register's development set"),
              "arm": ARM, "base": f"{BASE} (033's stored games)", "search": record["search"],
              "base_search": e35.base_search(), "format": record["format"], "rule": RULE,
              "style": {BASE: e35.style(base), ARM: e35.style(mine)},
              "paired_vs_v29r20": paired, "library": record["library"],
              "versions": record["versions"]}
    result |= verdict(stage, paired["total"]["score"])
    _write(OUT / f"{stage}.json", result)
    return result


def _line(result: dict[str, Any]) -> str:
    score = result["paired_vs_v29r20"]["total"]["score"]
    mine = result["style"][ARM]
    flag = {k: result[k] for k in ("kept", "passed") if k in result}
    return (f"{result['stage']}: {ARM} {mine['mean_score']:,.0f}, paired "
            f"{score['mean']:+,.0f} ({score['ci95_low']:+,.0f}, {score['ci95_high']:+,.0f}) "
            f"{flag}; {mine['seconds_per_game']:.0f} s a game")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment035eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gate", help="replay stored record games on this build")
    commands.add_parser("develop", help="v29r20d on the 500 development seeds")
    commands.add_parser("heldout", help="v29r20d on 012's 1,000 held-out seeds, if kept")
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
