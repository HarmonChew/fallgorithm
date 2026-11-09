"""Run Experiment 034's staged evaluation of the chosen V29@20 (predeclared.md).

    python -m block_stack_ai.experiment034eval screen [--jobs N]
    python -m block_stack_ai.experiment034eval develop [--jobs N]
    python -m block_stack_ai.experiment034eval heldout [--jobs N]
    python -m block_stack_ai.experiment034eval summarize STAGE

Every stage plays only the arm ``v29t20`` (``v29r20`` with the V29@20 that ``experiment034
choose`` picked) and pairs it by seed with 033's stored ``v29r20`` games of the stage. Three
guards keep that fair: before a stage the first 28 stored ``v29r20`` games are re-run by the
agent (``rerun``); on every seed the arm's inputs equal the stored game's before it first
reaches 230 lines (``prefix_matches``); the native library's sha and ABI are recorded and the
ABI must be 033's. Held-out first replays 032's 30 Hz gate (140 games) and re-runs 28 stored
``v29r20`` held-out games and 28 ``v29t20`` development games at 20 Hz.
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

from . import experiment013 as e13, experiment025 as e25, experiment032eval as e32eval
from . import experiment033 as e33, experiment034 as e34, native, runner
from .experiment025 import _paired, _resume, _summary

OUT = e34.OUT
GAMES = OUT / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "034"
SCHEMA = "fallgorithm.register.games/1"
STAGES = ("screening", "development", "heldout")
ARM, BASE = e34.ARM, e34.BASE
MIN_EFFECT = 15_000
REPLAY_GAMES = 28
RULE = ("Primary metric: mean final score, paired by seed against 033's stored v29r20 games "
        "on the same seeds (v29t20 minus v29r20), both at 20 Hz / 300 ms, 95% bootstrap "
        "interval of experiment012.paired. Guards on every stage: the first 28 stored v29r20 "
        "games re-run input for input; on every seed v29t20's inputs equal the stored game's "
        "before it first reaches 230 lines; the native ABI equals 033's (28). Screening: "
        "promoted if the paired mean is +15k or more. Development: kept if the paired mean is "
        "at least +15k and the interval's lower end is above 0. Held-out: passes (a new 20 Hz "
        "/ 300 ms record) if the interval lies above 0, after the 30 Hz gate (140/140) and "
        "28 stored v29r20 held-out and 28 v29t20 development games re-run at 20 Hz (56/56).")

_load, _write = e13._load, e13._write


def chosen() -> dict[str, Any]:
    if not e34.CHOICE.exists():
        raise ValueError(f"{e34.CHOICE} is missing: run experiment034 choose first")
    pick = _load(e34.CHOICE)["chosen"]
    if pick is None:
        raise ValueError("experiment034 choose found no sweep with a probe mean above 0")
    weights = runner.PROJECT_ROOT / pick["weights"]
    return pick | {"path": weights,
                   "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()}


def play_game(job: tuple[str, int]) -> dict[str, Any]:
    """One checked game of the arm (register.checked_game and the tap-spacing check)."""
    weights, seed = job
    frozen, net = e33._frozen()
    mid = e33._mid_bytes(weights)
    return e33.checked_game(frozen, seed, lambda: e33._game(net, frozen, seed, mid=mid)[0],
                            agent=ARM)


def games_path(stage: str) -> Path:
    return GAMES / f"{stage}-{ARM}.json.gz"


def _stage_result(name: str) -> dict[str, Any]:
    path = OUT / f"{name}.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: run {name} first")
    return _load(path)


def _load_arm(stage: str) -> dict[str, Any]:
    with gzip.open(games_path(stage), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def prefix_check(stage: str, mine: list[dict[str, Any]]) -> dict[str, Any]:
    """Every seed: the arm's inputs equal the stored v29r20 game's before 230 lines."""
    frozen = e33._frozen()[0]
    base = {e["seed"]: e for e in e34._stored_base(stage)}
    bad = [e["seed"] for e in mine
           if not e34.prefix_matches(frozen, e["seed"], base64.b64decode(base[e["seed"]]["inputs"]),
                                     base64.b64decode(e["inputs"]))]
    return {"games": len(mine), "matched": len(mine) - len(bad), "mismatched_seeds": bad}


def play_arm(stage: str, weights: str, sha: str, seeds: list[int], pick: dict[str, Any],
             versions: dict[str, Any], library: dict[str, Any], jobs: int) -> None:
    """Play the arm on the stage's seeds (resuming), stored outside the tree until done."""
    if games_path(stage).exists() or (PARTIAL / games_path(stage).name).exists():
        return
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": ARM, "format": fmt, "weights": weights, "weights_sha256": sha,
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "abi_version": native.ABI_VERSION, "versions": versions}}
    partial = PARTIAL / f"{stage}-{ARM}.partial.jsonl"
    done = _resume(partial, header)
    todo = [(weights, seed) for seed in seeds if seed not in done]
    print(f"{stage} {ARM}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(play_game, todo, chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            mean = sum(e["result"]["score"] for e in done.values()) / len(done)
            print(f"{ARM} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "arm": ARM, "format": fmt,
              "chosen": {k: v for k, v in pick.items() if k != "path"},
              "weights": weights, "weights_sha256": sha, "set": stage, "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[seed] for seed in seeds]}
    with gzip.open(PARTIAL / games_path(stage).name, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    partial.unlink()


def heldout_gate(jobs: int, base: dict[str, Any]) -> dict[str, Any]:
    """032's 30 Hz gate (140 games) and at 20 Hz: the first 28 stored v29r20 held-out
    games (``base``, the stage's own re-run) and the first 28 v29t20 development games re-run
    input for input (56)."""
    thirty = e32eval.heldout_replay(jobs)
    weights = str(chosen()["path"].relative_to(runner.PROJECT_ROOT))
    arm = e34.rerun(_load_arm("development")["episodes"][:REPLAY_GAMES], weights, jobs)
    return {"stage": "heldout", "part_30hz": thirty,
            "part_20hz": {BASE: base, ARM: arm},
            "games": thirty["games"] + base["games"] + arm["games"],
            "matched": thirty["matched"] + base["matched"] + arm["matched"],
            "abi_version": native.ABI_VERSION}


def run(stage: str, jobs: int) -> dict[str, Any]:
    """Guards, the arm on the stage's seeds, the prefix check, the summary."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    if stage == "development" and not _stage_result("screening")["promoted"]:
        raise ValueError("screening did not promote v29t20")
    if stage == "heldout" and not _stage_result("development")["kept"]:
        raise ValueError("development did not keep v29t20")
    pick = chosen()
    shown = {k: v for k, v in pick.items() if k != "path"}
    previous = {"development": "screening", "heldout": "development"}.get(stage)
    if previous and _stage_result(previous)["chosen"] != shown:
        raise ValueError(f"chosen.json names another V29@20 than {previous} evaluated")
    if runner._record_versions()["fallgorithm"]["dirty"]:
        raise ValueError("the git tree is dirty: commit before playing")
    e34._require_wiring()
    library = e34.library_record()
    seeds = e25._seeds(stage)
    versions = runner._record_versions()
    PARTIAL.mkdir(parents=True, exist_ok=True)
    gate_path = PARTIAL / f"{stage}_gate.json"
    if not gate_path.exists():
        gate = {"rerun_v29r20": e34.rerun(e34._stored_base(stage)[:REPLAY_GAMES],
                                          e34.BASE_WEIGHTS, jobs)}
        if stage == "heldout":
            gate["heldout_replay"] = heldout_gate(jobs, gate["rerun_v29r20"])
        bad = gate["rerun_v29r20"]["matched"] != gate["rerun_v29r20"]["games"] or (
            "heldout_replay" in gate and
            gate["heldout_replay"]["matched"] != gate["heldout_replay"]["games"])
        gate |= {"library": library, "versions": versions, "passed": not bad}
        _write(gate_path, gate)
        if bad:
            raise ValueError(f"{stage} gate failed: stored games do not re-run on this build")
    elif not _load(gate_path)["passed"]:
        raise ValueError(f"{stage} gate failed earlier ({gate_path})")
    weights = str(pick["path"].relative_to(runner.PROJECT_ROOT))
    play_arm(stage, weights, pick["sha256"], seeds, shown, versions, library, jobs)
    GAMES.mkdir(parents=True, exist_ok=True)
    if (PARTIAL / games_path(stage).name).exists():
        (PARTIAL / games_path(stage).name).replace(games_path(stage))
    if gate_path.exists():
        gate_path.replace(OUT / f"{stage}_gate.json")
    return summarize(stage, versions=versions)


def summarize(stage: str, versions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write OUT/<stage>.json: the prefix check, summaries, the paired result and the
    rule's verdict (a failed prefix check fails the stage)."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    seeds = e25._seeds(stage)
    record = _load_arm(stage)
    base_eps, mine = e34._stored_base(stage), record["episodes"]
    if [e["seed"] for e in mine] != seeds:
        raise ValueError(f"{ARM}'s {stage} games are not the stage's seeds in order")
    if record["format"] != e33.format_of(e33._frozen()[0]):
        raise ValueError(f"{ARM}'s {stage} games were not played in the 20 Hz format")
    prefix = prefix_check(stage, mine)
    paired = _paired(mine, base_eps)
    gate = OUT / f"{stage}_gate.json"
    result: dict[str, Any] = {
        "experiment": "034-v29-20hz-true-handover", "stage": stage, "games": len(seeds),
        "seeds": ("Experiment 012's 1,000 held-out seeds (the established record benchmark)"
                  if stage == "heldout" else f"the register's {stage} set"),
        "arm": ARM, "base": f"{BASE} (033's stored games)", "format": record["format"],
        "chosen": record["chosen"], "versions": versions or runner._record_versions(),
        "library": record.get("library"), "abi_version": native.ABI_VERSION,
        "gate": _load(gate) if gate.exists() else None, "prefix_check": prefix,
        "rule": RULE, "min_effect": MIN_EFFECT,
        "summary": {BASE: _summary(base_eps), ARM: _summary(mine)},
        "style": {BASE: e33.style(base_eps), ARM: e33.style(mine)},
        "paired_vs_v29r20": paired}
    mean = paired["total"]["score"]["mean"]
    low = paired["total"]["score"]["ci95_low"]
    fair = prefix["matched"] == prefix["games"]
    if stage == "screening":
        result["promoted"] = fair and mean >= MIN_EFFECT
    elif stage == "development":
        result["kept"] = fair and mean >= MIN_EFFECT and low > 0
    else:
        result["passed"] = fair and low > 0
    _write(OUT / f"{stage}.json", result)
    if not fair:
        raise ValueError(f"{stage}: the prefix check failed on {prefix['mismatched_seeds']}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment034eval")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("screen", help="v29t20 on the screening seeds")
    commands.add_parser("develop", help="v29t20 on the development seeds, if promoted")
    commands.add_parser("heldout", help="v29t20 on 012's held-out seeds, if kept")
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
            result = run(stage[args.command], args.jobs)
            verdict = {k: result[k] for k in ("promoted", "kept", "passed") if k in result}
            print(json.dumps(verdict))
            if not all(verdict.values()):
                return 2
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
