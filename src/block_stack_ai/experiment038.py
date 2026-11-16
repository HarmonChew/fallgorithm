"""Run Experiment 038's step 0: can column 0 be built ahead before level 39, at what cost?

    python -m block_stack_ai.experiment038 base
    python -m block_stack_ai.experiment038 check [--jobs N]
    python -m block_stack_ai.experiment038 step0 [--jobs N]
    python -m block_stack_ai.experiment038 summarize
    python -m block_stack_ai.experiment038 status

The agent is 036's record ``v36`` (its three networks, 035's search) at 20 Hz / 300 ms. Step
0 changes only the search (plan.md, predeclared.md): for a decision whose position has ``L``
lines or more and fewer than 330, every leaf value gets ``beta`` x column 0's lead (min(height
of column 0, 16) minus the mean height of columns 1-9) in Tetrises at level 18
(NetSearcher::set_lead_bonus). Four arms play probe A and are paired by seed with ``v36``'s
stored probe A games (036's ``stage3-sweep1-A``, copied into this experiment by ``base``).

* ``base``: copy and check ``v36``'s stored probe A games.
* ``check``: the wiring check: the first 28 stored games re-run through the bonus path with
  beta 0 must match input for input.
* ``step0``: the four arms in order, each resumable; every game checked on the engine, and
  its inputs must equal ``v36``'s before it first has ``L`` lines (stops the arm otherwise).
* ``summarize``: replay every game for the board at 330 lines, apply the rule, write
  ``step0.json``.
"""

from __future__ import annotations

import argparse
import base64
import functools
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

from . import experiment025 as e25, experiment033 as e33, experiment034 as e34
from . import experiment035 as e35, experiment036 as e36, native, runner, wellplan
from .engine import create_game
from .pathaware import grid_columns

OUT = runner.PROJECT_ROOT / "experiments" / "038-level39-20hz"
RUNS = runner.PROJECT_ROOT / "runs" / "038"
GAMES = OUT / "games"
BASE_SOURCE = runner.PROJECT_ROOT / "runs" / "036" / "games" / "stage3-sweep1-A.json.gz"
BASE_GAMES = GAMES / "v36-A.json.gz"
WIRING = OUT / "wiring_check.json"
STEP0 = OUT / "step0.json"
SCHEMA = e36.SCHEMA
REPLAY_GAMES = 28

TO_LINES = 330
ENTRY = 330  # the board the lead is read on: the first piece at 330 lines or more
ARMS: dict[str, tuple[int, float]] = {"t300_a": (300, 0.25), "t300_b": (300, 0.75),
                                      "t315_a": (315, 0.25), "t315_b": (315, 0.75)}
LEAD_RISE, MAX_COST, MAX_P330_DROP = 3.0, 15_000, 0.02  # the drop is tested in games
RESAMPLES, RNG_SEED = 10_000, 12

_load, _write = e36._load, e36._write


# ---------------------------------------------------------------- the agent

@functools.lru_cache(maxsize=1)
def v36() -> dict[str, Any]:
    """036's ``v36`` (decision.json), its networks' shas checked."""
    agent = e36._load(e36.DECISION)["agent"]
    shas = [e36._sha(e36._path(p)) for p in (agent["early"], agent["mid"], agent["late"])]
    if shas != agent["shas"] or agent["late"] != e36.LATE:
        raise ValueError("v36's networks changed after 036's decision")
    return agent


def lead_of(arm: str) -> tuple[int, int, float]:
    """NetSearcher::set_lead_bonus's (from_lines, to_lines, beta) of an arm; ``v36`` is
    the bonus path with beta 0."""
    if arm == "v36":
        return (ARMS["t300_a"][0], TO_LINES, 0.0)
    from_lines, beta = ARMS[arm]
    return (from_lines, TO_LINES, beta)


def _game(seed: int, lead: tuple[int, int, float]) -> dict[str, Any]:
    """``v36``'s game (e36._game's arguments, v36's networks) with the lead bonus."""
    agent, (frozen, _), s = v36(), e33._frozen(), e36.search()
    played, _ = native.late_hybrid_game(
        e36._bytes(agent["early"]), frozen["game"], seed, late=e36._bytes(agent["late"]),
        late_from_lines=e36.LATE_FROM, mid=e36._bytes(agent["mid"]),
        mid_from_lines=e36.MID_FROM, commit_level=s["commit_level"], adjust_k=s["adjust_k"],
        adjust_max_level=s["adjust_max_level"], deep2_level=s["deep2_level"],
        deep2_k=s["deep2_k"], switch_level=e36.NEVER, line_cap=frozen["line_cap"],
        frame_cap=frozen["frame_cap"], limits=e36.e13._limits(frozen),
        params=native.params(frozen["params"]), deep3=tuple(s["deep3"]), lead=lead)
    e33.check_tap_spacing(played["inputs"], e36.TAP_INTERVAL)
    return played


def _job(job: tuple[int, str]) -> dict[str, Any]:
    """One checked game (register.checked_game and the 20 Hz tap-spacing check)."""
    seed, arm = job
    lead = lead_of(arm)
    return e33.checked_game(e33._frozen()[0], seed, lambda: _game(seed, lead), agent=arm)


def library_record() -> dict[str, Any]:
    found = e35.library_record()
    lib = native.load()
    if not hasattr(lib, "fn_lead_game"):
        raise ValueError("the native library has no fn_lead_game: rebuild it")
    return found


# ---------------------------------------------------------------- v36's stored games

def probe_seeds() -> list[int]:
    return e36.probe_seeds("A")


def _read(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def copy_base() -> dict[str, Any]:
    """Copy 036's stored ``v36`` probe A games into the experiment, after checking them."""
    record = _read(BASE_SOURCE)
    agent = v36()
    if record["agent"] != {"early": agent["early"], "mid": agent["mid"]} or \
            record["search"] != e36.search():
        raise ValueError(f"{BASE_SOURCE} was not played by v36")
    if record["format"] != e33.format_of(e33._frozen()[0]):
        raise ValueError(f"{BASE_SOURCE} is not in the 20 Hz format")
    if [e["seed"] for e in record["episodes"]] != probe_seeds():
        raise ValueError(f"{BASE_SOURCE} does not cover probe A in order")
    GAMES.mkdir(parents=True, exist_ok=True)
    if not BASE_GAMES.exists():
        shutil.copyfile(BASE_SOURCE, BASE_GAMES)
    if hashlib.sha256(BASE_GAMES.read_bytes()).hexdigest() != \
            hashlib.sha256(BASE_SOURCE.read_bytes()).hexdigest():
        raise ValueError(f"{BASE_GAMES} differs from {BASE_SOURCE}")
    return {"games": len(record["episodes"]), "library": record["library"]}


@functools.lru_cache(maxsize=1)
def base_by_seed() -> dict[int, dict[str, Any]]:
    record = _read(BASE_GAMES)
    if [e["seed"] for e in record["episodes"]] != probe_seeds():
        raise ValueError(f"{BASE_GAMES} does not cover probe A in order")
    return {e["seed"]: e for e in record["episodes"]}


def prefix_ok(seed: int, inputs: bytes, from_lines: int) -> bool:
    """Do ``inputs`` equal ``v36``'s stored game before it first has ``from_lines`` lines
    (the whole game if it never does)?"""
    stored = base64.b64decode(base_by_seed()[seed]["inputs"])
    n = e34.prefix_frames(e33._frozen()[0], seed, stored, from_lines)
    return len(inputs) >= n and inputs[:n] == stored[:n]


# ---------------------------------------------------------------- guards

def _require_clean() -> None:
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _require_ready(wiring: bool = True) -> None:
    """A clean tree outside the experiment; the plan, the protocol and the base games
    committed; for the arms, the wiring check matched on this very library."""
    _require_clean()
    v36()
    e34._require_committed(OUT / "plan.md", OUT / "predeclared.md", BASE_GAMES)
    if wiring:
        found = _load(WIRING) if WIRING.exists() else {}
        if not found.get("matched") or found.get("library") != library_record():
            raise ValueError(f"{WIRING} is missing or not matched on this library: run check")


def wiring_check(jobs: int) -> dict[str, Any]:
    """The first 28 stored ``v36`` probe A games re-run through the bonus path, beta 0."""
    _require_ready(wiring=False)
    stored = list(base_by_seed().values())[:REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(_job, [(e["seed"], "v36") for e in stored], chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    result = {"experiment": OUT.name, "games": len(stored), "matched_games": len(stored) - len(bad),
              "mismatched_seeds": bad, "matched": not bad, "lead": list(lead_of("v36")),
              "library": library_record(), "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- the arms

def games_path(arm: str) -> Path:
    return RUNS / "games" / f"{arm}-A.json.gz"


def play_arm(arm: str, jobs: int) -> Path:
    """An arm on probe A (resuming from its partial file), stored in ``runs/038/games``."""
    target = games_path(arm)
    if target.exists():
        return target
    _require_ready()
    seeds, lead = probe_seeds(), lead_of(arm)
    versions, library = runner._record_versions(), library_record()
    fmt = e33.format_of(e33._frozen()[0])
    header = {"header": {"arm": arm, "lead": list(lead), "agent": v36(), "search": e36.search(),
                         "format": fmt, "library": library, "versions": versions,
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest()}}
    (RUNS / "partial").mkdir(parents=True, exist_ok=True)
    partial = RUNS / "partial" / f"{arm}-A.partial.jsonl"
    done = e36.resume(partial, header)
    todo = [(seed, arm) for seed in seeds if seed not in done]
    print(f"{arm}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(_job, todo, chunksize=1):
            if not prefix_ok(episode["seed"], base64.b64decode(episode["inputs"]), lead[0]):
                raise ValueError(f"{arm}: seed {episode['seed']} differs from v36 before "
                                 f"{lead[0]} lines: stopped (the games stay in {partial})")
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            if len(done) % 50 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{arm} {len(done)}/{len(seeds)} {mean:,.0f} "
                      f"({time.perf_counter() - tick:,.0f} s)", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "arm": arm, "lead": list(lead),
              "agent": v36(), "search": e36.search(), "format": fmt, "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[s] for s in seeds]}
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".partial")
    with gzip.open(staged, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    staged.replace(target)
    partial.unlink()
    return target


def load_arm(arm: str) -> dict[str, Any]:
    record = _read(games_path(arm))
    if [e["seed"] for e in record["episodes"]] != probe_seeds() or \
            record["lead"] != list(lead_of(arm)) or record["search"] != e36.search():
        raise ValueError(f"{games_path(arm)} is not {arm} on probe A")
    return record


# ---------------------------------------------------------------- the board at 330

def lead(heights: list[int]) -> float:
    """Column 0's height minus the mean height of columns 1-9 (the free look's lead)."""
    return heights[0] - sum(heights[1:]) / 9


def entry(job: tuple[int, str]) -> dict[str, Any]:
    """Replay a game: the column heights and score at its first piece with 330 lines or
    more, and its clears by size from there on (the free look's ``entry_columns``)."""
    seed, encoded = job
    frozen = e33._frozen()[0]
    count, heights, score_at, lines_at, before, clears = -1, None, None, None, 0, Counter()
    with create_game(**frozen["game"], seed=seed) as game:
        state = game.state
        for mask in base64.b64decode(encoded):
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                if state.lines > before and before >= ENTRY:
                    clears[state.lines - before] += 1
                before = state.lines
                if heights is None and state.lines >= ENTRY:
                    heights = e35._heights(grid_columns(wellplan.visible_grid(state.board)))
                    score_at, lines_at = state.score, state.lines
            state, _ = game.step(mask)
        if state.lines > before and before >= ENTRY:
            clears[state.lines - before] += 1
        final = state.score
    return {"seed": seed, "reached": heights is not None, "heights": heights,
            "lines_at": lines_at, "lines_after": state.lines - lines_at if heights else 0,
            "before": int(score_at if score_at is not None else final),
            "after": int(final - score_at) if score_at is not None else 0,
            "clears": {str(k): v for k, v in sorted(clears.items())}}


def entries(episodes: list[dict[str, Any]], jobs: int) -> list[dict[str, Any]]:
    with Pool(jobs) as pool:
        return pool.map(entry, [(e["seed"], e["inputs"]) for e in episodes], chunksize=4)


def paired_interval(diff: np.ndarray) -> dict[str, float]:
    """Mean of per-seed differences, 95% percentile bootstrap interval (RNG seed 12)."""
    rng = np.random.default_rng(RNG_SEED)
    boot = np.sort(diff[rng.integers(0, len(diff), (RESAMPLES, len(diff)))].mean(1))
    return {"mean": float(diff.mean()), "ci95_low": float(boot[int(0.025 * RESAMPLES)]),
            "ci95_high": float(boot[int(0.975 * RESAMPLES) - 1])}


def figures(found: list[dict[str, Any]], episodes: list[dict[str, Any]]) -> dict[str, Any]:
    reached = [f for f in found if f["reached"]]
    clears = Counter()
    for f in reached:
        clears.update({int(k): v for k, v in f["clears"].items()})
    lines_after = [f["lines_after"] for f in reached]
    by_lead: dict[int, list[int]] = {}
    for f, after in zip(reached, lines_after):
        by_lead.setdefault(max(-3, min(6, round(lead(f["heights"])))), []).append(after)
    n = len(found)
    return {"p_330": len(reached) / n,
            "mean_lead_330": float(np.mean([lead(f["heights"]) for f in reached])),
            "mean_heights_330": [round(float(np.mean([f["heights"][c] for f in reached])), 2)
                                 for c in range(10)],
            "points_before_330": float(np.mean([f["before"] for f in found])),
            "points_from_330_per_game": float(np.mean([f["after"] for f in found])),
            "points_from_330_per_game_reaching": float(np.mean([f["after"] for f in reached])),
            "lines_from_330_per_game_reaching": float(np.mean(lines_after)),
            "clears_from_330": {str(k): v for k, v in sorted(clears.items())},
            "lines_after_330_by_lead": {str(k): {"games": len(v), "lines": round(float(np.mean(v)), 2)}
                                        for k, v in sorted(by_lead.items())}}


def verdict(rise: float, cost: float, dropped_games: int, games: int) -> bool:
    """predeclared.md: lead at 330 up by 3 rows or more, at most 15k a game lost before 330
    (paired mean), P(330) down by at most 2 points (counted in games: no rounding error)."""
    return bool(rise >= LEAD_RISE and cost <= MAX_COST and
                dropped_games * 100 <= round(MAX_P330_DROP * 100) * games)


def choose(rows: dict[str, dict[str, Any]]) -> str | None:
    """The qualifying arm with the largest lead (the first in ARMS order on a tie)."""
    good = [arm for arm in ARMS if arm in rows and rows[arm]["qualifies"]]
    return max(good, key=lambda a: rows[a]["mean_lead_330"]) if good else None


def summarize(jobs: int) -> dict[str, Any]:
    base_eps = [base_by_seed()[s] for s in probe_seeds()]
    base_found = entries(base_eps, jobs)
    base = figures(base_found, base_eps)
    base["style"] = e35.style(base_eps)
    rows: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        if not games_path(arm).exists():
            continue
        record = load_arm(arm)
        if record["library"] != _load(WIRING)["library"]:
            raise ValueError(f"{arm} was played on another library than the wiring check's")
        eps = record["episodes"]
        found = entries(eps, jobs)
        row = figures(found, eps)
        before = np.array([f["before"] for f in found], np.float64)
        base_before = np.array([f["before"] for f in base_found], np.float64)
        cost = paired_interval(base_before - before)  # points lost before 330, paired
        after = paired_interval(np.array([f["after"] for f in found], np.float64) -
                                np.array([f["after"] for f in base_found], np.float64))
        both = [(lead(f["heights"]), lead(b["heights"])) for f, b in zip(found, base_found)
                if f["reached"] and b["reached"]]
        rise = row["mean_lead_330"] - base["mean_lead_330"]
        drop = base["p_330"] - row["p_330"]
        dropped = sum(f["reached"] for f in base_found) - sum(f["reached"] for f in found)
        total = e25._paired(eps, base_eps)
        score = total["total"]["score"]
        row |= {"lead": record["lead"], "lead_rise": rise,
                "lead_rise_paired_both_reach": {"games": len(both), "mean": float(
                    np.mean([a - b for a, b in both])) if both else None},
                "cost_before_330": cost, "points_from_330_paired": after,
                "p_330_drop": drop, "p_330_drop_games": dropped, "paired_total": total,
                "record_candidate": bool(score["mean"] > 0 and score["ci95_low"] > 0),
                "style": e35.style(eps), "library": record["library"],
                "qualifies": verdict(rise, cost["mean"], dropped, len(found))}
        rows[arm] = row
    chosen = choose(rows)
    result = {"experiment": OUT.name, "step": 0, "seeds": "probe A (035's 14,200-14,699 "
              "indices of 029's list; screening only)", "base": "v36's stored probe A games",
              "rule": ("An arm qualifies if the mean lead at 330 lines (column 0 minus the "
                       "mean of columns 1-9, games reaching 330) rises by 3 rows or more over "
                       "v36's, the paired mean of points lost before 330 lines is at most "
                       "15,000, and P(330) falls by at most 2 points. Stage 1 takes the "
                       "qualifying arm with the largest lead; none qualifies: 038 stops."),
              "v36": base, "arms": rows, "complete": len(rows) == len(ARMS),
              "chosen": chosen if len(rows) == len(ARMS) else None,
              "versions": runner._record_versions()}
    _write(STEP0, result)
    return result


def status() -> dict[str, Any]:
    out: dict[str, Any] = {"base_copied": BASE_GAMES.exists(), "wiring": None, "arms": {}}
    if WIRING.exists():
        out["wiring"] = _load(WIRING)["matched"]
    for arm in ARMS:
        partial = RUNS / "partial" / f"{arm}-A.partial.jsonl"
        if games_path(arm).exists():
            out["arms"][arm] = "done"
        elif partial.exists():
            out["arms"][arm] = f"{sum(1 for _ in partial.open()) - 1}/500"
    out["step0"] = _load(STEP0)["chosen"] if STEP0.exists() else None
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment038")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("base", help="copy v36's stored probe A games")
    for name in ("check", "step0", "summarize"):
        commands.add_parser(name).add_argument("--jobs", type=int, default=28)
    commands.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "base":
            print(copy_base())
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"wiring: {found['matched_games']}/{found['games']} matched")
            return 0 if found["matched"] else 1
        elif args.command == "step0":
            for arm in ARMS:
                play_arm(arm, args.jobs)
            found = summarize(args.jobs)
            print(json.dumps({a: {k: r[k] for k in ("lead_rise", "p_330_drop", "qualifies")}
                              | {"cost": r["cost_before_330"]["mean"]}
                              for a, r in found["arms"].items()}, indent=1))
            print("chosen:", found["chosen"])
        elif args.command == "summarize":
            found = summarize(args.jobs)
            print("chosen:", found["chosen"])
        else:
            print(json.dumps(status(), indent=1))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
