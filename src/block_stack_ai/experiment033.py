"""Run Experiment 033: 030's V29 re-taught under 20 taps a second (V29@20).

    python -m block_stack_ai.experiment033 check [--jobs N]
    python -m block_stack_ai.experiment033 round0 [--jobs N]
    python -m block_stack_ai.experiment033 handover [--jobs N]
    python -m block_stack_ai.experiment033 loop [--jobs N] [--device D]
    python -m block_stack_ai.experiment033 choose

The agent is 031b's record agent ``v39r`` played at 20 Hz / 300 ms (``v39r20``): 023's v15
below 230 lines, 030's V29 at 230-319, 031b's V39' from 320. 030's recipe, in the 20 Hz
format: sweep s backs up the training boards (230-319 lines) with V29@20 of sweep s-1
(sweep 0 = 030's V29) as the frozen teacher, backup2 k 4 with 20 Hz reach, with
lambda-returns that hand over to the frozen V39' at the first board of 320 lines or more
(``handover_returns``), fits V29@20 of sweep s warm-started from it, probes the agent on
500 seeds against ``v39r20`` played once, and plays the next round (see plan.md).

The format is this module's own (``_frozen``: the 30 Hz frozen configuration with
``tap_hz`` 20), and every game, target and probe job reads it from here: 029's ``targets``
reads 029's 30 Hz configuration, so ``targets`` below is 033's. ``handover`` (after round
0) measures whether V39''s backup2 overvalues 20 Hz hand-over boards and decides, by
plan.md's predeclared rule, whether the hand-over value is the actual rest of the game.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import experiment013 as e13, experiment020 as e20, experiment023 as e23
from . import experiment024 as e24, experiment025 as e25, experiment028 as e28
from . import experiment029 as e29, experiment030 as e30, experiment031 as e31
from . import experiment032 as e32, native, register, runner

OUT = runner.PROJECT_ROOT / "experiments" / "033-v29-20hz"
DATA = runner.PROJECT_ROOT / "runs" / "033-data"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
HANDOVER = OUT / "handover_check.json"
CHOICE = OUT / "chosen.json"
TAP_HZ, REACTION_MS, TAP_INTERVAL = 20, 300, 3
MID_FROM = e30.MID_FROM    # 230: V29@20 from here ...
LATE_FROM = e29.LATE_FROM  # ... until 320, where 031b's V39' (frozen) takes over
DEPTH = 4                  # backup2 with k 4
NEVER = e28.NEVER
PROBE_SEEDS, ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS = 500, 400, 200, 40
FIRST_UNUSED = 8_800       # 029-032 used the training seeds before this index
KEPT_ROUNDS = 3            # own rounds kept besides round 0
MIN_SWEEPS, MAX_SWEEPS, STOP_AFTER_FLAT = 5, 10, 3
LAMBDA = 0.95
EXPLORE, EXPLORE_FROM, EXPLORE_TO = 0.005, 210, LATE_FROM  # own rounds only
CHILD_SHARE = 1 / 3
KEYS = e23.KEYS
TETRIS_18 = e20.TETRIS_18
BASE = "v39r20"
# plan.md's predeclared fallback: tallest third's gap minus shortest third's, in Tetrises
HANDOVER_GAP = 2.0
RESAMPLES = 10_000
SHIFT, ROTATE = 1 | 2, 8 | 16  # native/reach.hpp: left, right; clockwise, counterclockwise

_load, _write = e13._load, e13._write


def _sha(path: Path) -> str:
    return e30._sha(path)


# ---------------------------------------------------------------- the format

def _frozen_30() -> tuple[dict[str, Any], bytes]:
    """The frozen configuration at 30 Hz (the earlier experiments' format), for the wiring
    check and the side check only."""
    return e29._frozen()


def _frozen() -> tuple[dict[str, Any], bytes]:
    """The frozen configuration with ``tap_hz`` 20 (reaction 300 ms), same network."""
    frozen, net = e29._frozen()
    frozen = copy.deepcopy(frozen)
    if len(frozen["formats"]) != 1 or frozen["formats"][0]["reaction_ms"] != REACTION_MS:
        raise ValueError(f"the frozen format is not a single {REACTION_MS} ms format")
    frozen["formats"][0]["tap_hz"] = TAP_HZ
    if e13._limits(frozen).tap_interval != TAP_INTERVAL:
        raise ValueError(f"{TAP_HZ} Hz is not a tap interval of {TAP_INTERVAL} frames")
    return frozen, net


def _config() -> dict[str, Any]:
    frozen, _ = _frozen()
    return {"line_cap": frozen["line_cap"], "start_level": frozen["game"]["start_level"],
            "double_killscreen": frozen["game"]["ruleset"].endswith("double_killscreen"),
            "tap_interval": e13._limits(frozen).tap_interval}


def format_of(frozen: dict[str, Any]) -> dict[str, Any]:
    fmt = frozen["formats"][0]
    return {"tap_hz": fmt["tap_hz"], "reaction_ms": fmt["reaction_ms"]}


def check_tap_spacing(inputs: bytes, interval: int) -> int:
    """Raise unless no two presses of the same kind (a shift, a rotation: the agent's two
    tap timers) are closer than ``interval`` frames. ``inputs`` is one button mask per
    frame; a press is a button newly down on a frame. Returns the number of presses."""
    last = {SHIFT: None, ROTATE: None}
    previous, presses = 0, 0
    for frame, mask in enumerate(inputs):
        newly = mask & ~previous
        previous = mask
        for kind in (SHIFT, ROTATE):
            if newly & kind:
                presses += 1
                if last[kind] is not None and frame - last[kind] < interval:
                    raise ValueError(f"two presses {frame - last[kind]} frames apart at "
                                     f"frame {frame}: closer than the tap interval {interval}")
                last[kind] = frame
    return presses


def checked_game(frozen: dict[str, Any], seed: int, play: Any, agent: str) -> dict[str, Any]:
    """register.checked_game, then the tap-spacing check of the frozen format, and the
    format recorded in the episode."""
    episode = register.checked_game(frozen, seed, play, agent=agent)
    check_tap_spacing(base64.b64decode(episode["inputs"]), e13._limits(frozen).tap_interval)
    return episode | {"format": format_of(frozen)}


# ---------------------------------------------------------------- paths

def v15_path() -> Path:
    """023's v15: the network below 230 lines (frozen)."""
    return e29._v15_path()


def v29_path() -> Path:
    """030's chosen V29: v39r's mid network and sweep 0's teacher and start."""
    return e31.v29_path()


def v39r_late_path() -> Path:
    """031b's chosen V39' (the late network, frozen)."""
    return e32.v39r_late_path()


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds after the slice 029-032 used (from index 8,800): 500 probe
    seeds, then round 0's 400, then the rounds' (``round_seeds``)."""
    stored = e29._seeds()
    start = e32._seeds()["used_slice"][1]
    if start != FIRST_UNUSED:
        raise ValueError(f"032 used training seeds up to {start}, not {FIRST_UNUSED}")
    need = PROBE_SEEDS + ROUND0_SEEDS + ROUND_SEEDS * (MAX_SWEEPS - 1)
    train = stored["training_seeds"][start:start + need]
    if len(train) < need:
        raise ValueError(f"only {len(train)} unused training seeds, {need} needed")
    result = {"selection": f"029's training seeds (029's seeds.json) from index {start} on "
                           f"(029-032 used 0-{start - 1}): {PROBE_SEEDS} probe seeds, then "
                           f"round 0's {ROUND0_SEEDS}, then rounds of {ROUND_SEEDS}",
              "used_slice": [start, start + need],
              "probe_seeds": train[:PROBE_SEEDS],
              "training_seeds": train[PROBE_SEEDS:]}
    _write(SEEDS, result)
    return result


def _seeds() -> dict[str, Any]:
    return _load(SEEDS) if SEEDS.exists() else make_seeds()


def round_seeds(index: int) -> list[int]:
    train = _seeds()["training_seeds"]
    if index == 0:
        return train[:ROUND0_SEEDS]
    start = ROUND0_SEEDS + ROUND_SEEDS * (index - 1)
    return train[start:start + ROUND_SEEDS]


# ---------------------------------------------------------------- games

def _mid_bytes(mid_path: str | None) -> bytes:
    """V29@20's weights (a path relative to the project); None: 030's V29 (v39r20)."""
    return (runner.PROJECT_ROOT / mid_path if mid_path else v29_path()).read_bytes()


def _game(net: bytes, frozen: dict[str, Any], seed: int, *, mid: bytes, explore: float = 0.0,
          dump: bool = False) -> tuple[dict[str, Any], bytes | None]:
    """v39r's game in ``frozen``'s format with ``mid`` as the 230-319 lines network; the
    tap spacing of the format is checked on every game."""
    played, rows = native.late_hybrid_game(
        net, frozen["game"], seed, late=v39r_late_path().read_bytes(),
        late_from_lines=LATE_FROM, mid=mid, mid_from_lines=MID_FROM,
        commit_level=e28.COMMIT_LEVEL, adjust_k=e28.ADJUST_K,
        adjust_max_level=e28.ADJUST_MAX_LEVEL, deep2_level=e28.DEEP2_LEVEL,
        deep2_k=e28.DEEP2_K, switch_level=NEVER, line_cap=frozen["line_cap"],
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
        params=native.params(frozen["params"]), explore=explore,
        explore_from_lines=EXPLORE_FROM, explore_to_lines=EXPLORE_TO, explore_seed=seed,
        dump=dump)
    check_tap_spacing(played["inputs"], e13._limits(frozen).tap_interval)
    return played, rows


def _mid_rows(rows: bytes) -> np.ndarray:
    """A game's boards from ``MID_FROM`` lines on, up to and including its first board at
    ``LATE_FROM`` or more (the hand-over board), in order."""
    return e30._mid_rows(rows)


def _data_job(job: tuple[int, str | None, float]) -> dict[str, Any]:
    seed, mid_path, explore = job
    frozen, net = _frozen()
    played, rows = _game(net, frozen, seed, mid=_mid_bytes(mid_path), explore=explore,
                         dump=True)
    return {"seed": seed, "source": 0, "score": played["score"], "lines": played["lines"],
            "rows": _mid_rows(rows).tobytes()}


def _require_clean() -> None:
    import subprocess
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def death_steps(lines: list[int] | np.ndarray) -> dict[str, int]:
    """Games whose final lines fall in each 10-line step of 230-329."""
    lines = np.asarray(lines)
    return {f"{lo}-{lo + 9}": int(((lines >= lo) & (lines < lo + 10)).sum())
            for lo in range(MID_FROM, LATE_FROM + 10, 10)}


def _mean(values: np.ndarray) -> float | None:
    return round(float(values.mean()), 2) if len(values) else None


def _play_data(path: Path, work: list[tuple], jobs: int) -> dict[str, Any]:
    """029's _play_data with this experiment's data games, and where the games ended."""
    with Pool(jobs) as pool:
        found = pool.map(_data_job, work, chunksize=1)
    parts, meta = [], []
    for index, game in enumerate(found):
        r = np.frombuffer(game["rows"], np.int32).reshape(-1, native.DUMP_STRIDE)
        parts.append(r)
        meta.append(np.repeat([[index, game["source"], game["seed"], game["score"]]],
                              len(r), axis=0))
    rows = np.concatenate(parts) if parts else np.zeros((0, native.DUMP_STRIDE), np.int32)
    info = np.concatenate(meta) if meta else np.zeros((0, 4), np.int64)
    boards = e23._boards(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.stem + ".partial.npz")
    np.savez(partial, **boards, score=rows[:, native.WIDTH + 1].astype(np.int64),
             final=info[:, 3].astype(np.int64), game=info[:, 0].astype(np.int32),
             source=info[:, 1].astype(np.int8), seed=info[:, 2].astype(np.int32))
    partial.replace(path)
    lines = np.array([g["lines"] for g in found])
    handover = rows[rows[:, native.WIDTH] >= LATE_FROM]
    feat = handover[:, native.WIDTH + 4:]
    return {"games": len(found), "boards": int(len(rows)),
            "mean_score": round(float(np.mean([g["score"] for g in found])), 1),
            "mean_lines": round(float(lines.mean()), 1),
            "line_cap_share": round(float((lines >= 430).mean()), 3),
            "p_reach_230": round(float((lines >= MID_FROM).mean()), 3),
            "p_reach_320": round(float((lines >= LATE_FROM).mean()), 3),
            "deaths_by_10_lines_230_329": death_steps(lines),
            "handover_boards": {"games": int(len(handover)),
                                "mean_max_height": _mean(feat[:, 5]),
                                "mean_aggregate_height": _mean(feat[:, 3]),
                                "mean_holes": _mean(feat[:, 0])}}


def _require_wiring() -> None:
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION:
        raise ValueError(f"{WIRING} is missing or not matched on this build: run check")


def _handover_check() -> dict[str, Any]:
    if not HANDOVER.exists():
        raise ValueError(f"{HANDOVER} is missing: run handover (after round0) first")
    return _load(HANDOVER)


def _actual_handover() -> bool:
    """The hand-over value of round 0's decision: True is the actual rest of the game."""
    return bool(_handover_check()["use_actual_rest_of_game"])


def round0(jobs: int) -> dict[str, Any]:
    """``v39r20`` on round 0's seeds, no exploration; then backup2's cost timed on a sample."""
    path = DATA / "round0.npz"
    if path.exists():
        raise ValueError(f"{path} exists already")
    _require_clean()
    _require_wiring()
    seeds = round_seeds(0)
    tick = time.time()
    summary = _play_data(path, [(s, None, 0.0) for s in seeds], jobs)
    seconds = round(time.time() - tick, 1)
    rows = e23._rows(e23._load_npz(path))
    sample = rows[rows[:, native.WIDTH] < LATE_FROM][:: max(1, len(rows) // 2000)][:2000]
    tock = time.time()
    targets(v29_path(), sample, DEPTH, jobs)
    result = {"experiment": "033-v29-20hz", "round": 0, "seeds": len(seeds),
              "format": format_of(_frozen()[0]), "versions": runner._record_versions(),
              "abi_version": native.ABI_VERSION, "agent": "v39r20 (031b's v39r at 20 Hz)",
              "mid_from_lines": MID_FROM, "late_from_lines": LATE_FROM, "seconds": seconds,
              "backup2_seconds_per_board_x_jobs": round((time.time() - tock) * jobs /
                                                        max(1, len(sample)), 4)} | summary
    _write(OUT / "round0.json", result)
    return result


# ---------------------------------------------------------------- targets

def _target_job(job: tuple[bytes, bytes, int, bool]) -> tuple[np.ndarray, bytes | None]:
    """029's _target_job with THIS experiment's tap interval (029's reads its 30 Hz one)."""
    weights, rows, depth, children = job
    c = _config()
    args = dict(line_cap=c["line_cap"], start_level=c["start_level"],
                double_killscreen=c["double_killscreen"], tap_interval=c["tap_interval"])
    kids = None
    if depth == 1 or children:
        values, kids = native.backup_values(weights, rows, children=children, **args)
    if depth > 1:
        values = native.backup2_values(weights, rows, k=depth, **args)
    return np.array(values) / TETRIS_18, kids


def targets(weights: Path, rows: np.ndarray, depth: int, jobs: int,
            children: bool = False) -> tuple[np.ndarray, np.ndarray | None]:
    """Each row's backup (depth 1) or backup2 (depth k) under ``weights`` at 20 Hz reach,
    in Tetrises at level 18, and with ``children`` the 7 next boards of each."""
    if len(rows) == 0:
        return np.zeros(0), (np.zeros((0, native.DUMP_STRIDE), np.int32) if children else None)
    data = weights.read_bytes()
    chunks = np.array_split(rows, max(1, min(len(rows), jobs * 8)))
    with Pool(jobs) as pool:
        found = pool.map(_target_job, [(data, c.tobytes(), depth, children) for c in chunks],
                         chunksize=1)
    values = np.concatenate([v for v, _ in found])
    if not children:
        return values, None
    kids = np.concatenate([np.frombuffer(k, np.int32).reshape(-1, native.DUMP_STRIDE)
                           for _, k in found])
    return values, kids[kids[:, native.WIDTH] >= 0]


# ---------------------------------------------------------------- wiring

def _wiring_job(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    kind, reference = job
    frozen, net = _frozen_30() if kind == "hz30" else _frozen()
    seed = reference["seed"]
    played, rows = _game(net, frozen, seed, mid=v29_path().read_bytes(), dump=kind == "hz20")
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
           played["lines"]]
    if kind == "hz30":  # 031b's stored game of v39r, input for input
        want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
        return {"kind": kind, "seed": seed, "match": got == want,
                "got": None if got == want else [got[0] == want[0], *got[1:]],
                "want": None if got == want else [True, *want[1:]]}
    presses = check_tap_spacing(played["inputs"], TAP_INTERVAL)  # raises on a 30 Hz leak
    try:  # the guard must catch the stored 30 Hz game
        check_tap_spacing(base64.b64decode(reference["inputs"]), TAP_INTERVAL)
        guard_catches_30hz = False
    except ValueError:
        guard_catches_30hz = True
    return {"kind": kind, "seed": seed, "presses": presses,
            "differs_from_30hz": got[0] != reference["inputs"],
            "guard_catches_30hz": guard_catches_30hz,
            "match": got[0] != reference["inputs"] and guard_catches_30hz,
            "rows": rows}


def targets_wiring(rows: np.ndarray, jobs: int) -> dict[str, Any]:
    """Part 3: 033's targets on sample boards equal native.backup2_values (and the
    children's backup) with tap interval 3, and differ from interval 2 somewhere."""
    weights = v29_path()
    c = _config()
    args = dict(line_cap=c["line_cap"], start_level=c["start_level"],
                double_killscreen=c["double_killscreen"])
    got, _ = targets(weights, rows, DEPTH, jobs)
    direct = {i: np.array(native.backup2_values(weights.read_bytes(), rows.tobytes(), k=DEPTH,
                                                tap_interval=i, **args)) / TETRIS_18
              for i in (3, 2)}
    one, kids = targets(weights, rows, 1, jobs, children=True)
    first, direct_kids = native.backup_values(weights.read_bytes(), rows.tobytes(),
                                              children=True, tap_interval=3, **args)
    kids3 = np.frombuffer(direct_kids, np.int32).reshape(-1, native.DUMP_STRIDE)
    kids3 = kids3[kids3[:, native.WIDTH] >= 0]
    equal = bool(np.array_equal(got, direct[3]))
    differs = bool((got != direct[2]).any())
    kids_equal = bool(np.array_equal(one, np.array(first) / TETRIS_18) and
                      np.array_equal(kids, kids3))
    return {"boards": int(len(rows)), "equals_interval_3": equal, "differs_from_interval_2":
            differs, "children_equal_interval_3": kids_equal,
            "match": equal and differs and kids_equal}


def wiring_check(jobs: int) -> dict[str, Any]:
    """(1) With the 30 Hz format this runner reproduces 031b's first 3 stored screening
    games of v39r (inputs, score, lines); (2) at 20 Hz the same seeds' inputs never repeat
    a press of a kind closer than 3 frames, differ from the 30 Hz games, and the guard
    rejects the 30 Hz games; (3) 033's targets equal native.backup2_values at tap interval
    3 and differ from 2."""
    if _frozen_30()[0]["formats"][0]["tap_hz"] != 30 or _config()["tap_interval"] != 3:
        raise ValueError("the formats are not 30 Hz and 20 Hz")
    base = e32.v39r_games("screening")[:3]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, [(k, e) for k in ("hz30", "hz20") for e in base],
                         chunksize=1)
    sample = np.concatenate([np.frombuffer(g["rows"], np.int32).reshape(-1, native.DUMP_STRIDE)
                             for g in found if g["kind"] == "hz20"])
    late = sample[sample[:, native.WIDTH] >= MID_FROM]
    sample = late if len(late) >= 50 else sample
    sample = np.ascontiguousarray(sample[:: max(1, len(sample) // 50)][:50])
    part3 = targets_wiring(sample, jobs)
    games = [{k: v for k, v in g.items() if k != "rows"} for g in found]
    result = {"experiment": "033-v29-20hz", "games": games, "targets": part3,
              "format": format_of(_frozen()[0]),
              "matched": len(games) == 6 and all(g["match"] for g in games) and part3["match"],
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- hand-over value

def handover_returns(backup: np.ndarray, data: dict[str, np.ndarray], lam: float,
                     late_from: int = LATE_FROM, actual: bool = False) -> np.ndarray:
    """030's handover_returns; with ``actual`` the hand-over board's value A_h is the
    actual rest of its game (final score minus the score before it, in Tetrises) instead
    of ``backup`` (plan.md's predeclared fallback)."""
    if actual:
        rest = (data["final"].astype(np.float64) - data["score"]) / TETRIS_18
        backup = np.where(data["lines"] >= late_from, rest, backup)
    return e30.handover_returns(backup, data, lam, late_from)


def handover_decision(backup: np.ndarray, actual: np.ndarray, height: np.ndarray,
                      resamples: int = RESAMPLES, seed: int = 33) -> dict[str, Any]:
    """plan.md's predeclared rule on the hand-over boards (``backup``: V39''s backup2,
    ``actual``: the actual rest of the game, both in Tetrises; ``height``: aggregate
    height): the gap (backup minus actual) of the tallest third minus the shortest
    third's; the actual rest of the game is used if that exceeds ``HANDOVER_GAP`` Tetrises
    and its 95% bootstrap interval (each third resampled on its own) excludes 0."""
    gap = np.asarray(backup, np.float64) - actual
    shortest, middle, tallest = np.array_split(np.argsort(height, kind="stable"), 3)
    difference = gap[tallest].mean() - gap[shortest].mean()
    rng = np.random.default_rng(seed)
    boot = np.sort(gap[tallest][rng.integers(0, len(tallest), (resamples, len(tallest)))].mean(1)
                   - gap[shortest][rng.integers(0, len(shortest),
                                                (resamples, len(shortest)))].mean(1))
    low, high = float(boot[int(0.025 * resamples)]), float(boot[int(0.975 * resamples) - 1])
    return {"boards": int(len(gap)),
            "thirds_by_aggregate_height": {
                name: {"boards": int(len(third)),
                       "height_range": [int(height[third].min()), int(height[third].max())],
                       "mean_backup": round(float(backup[third].mean()), 3),
                       "mean_actual": round(float(actual[third].mean()), 3),
                       "mean_gap": round(float(gap[third].mean()), 3)}
                for name, third in (("shortest", shortest), ("middle", middle),
                                    ("tallest", tallest))},
            "tallest_minus_shortest_gap": round(float(difference), 3),
            "ci95": [round(low, 3), round(high, 3)], "resamples": resamples, "rng_seed": seed,
            "rule": f"actual rest of game if the difference exceeds {HANDOVER_GAP} Tetrises "
                    "and its 95% bootstrap interval excludes 0 (plan.md)",
            "use_actual_rest_of_game": bool(difference > HANDOVER_GAP and low > 0)}


def handover_check(jobs: int) -> dict[str, Any]:
    """Round 0's hand-over boards (the first board of 320+ lines of each game): V39''s
    backup2 at 20 Hz against the game's actual rest of the game, by thirds of aggregate
    height; writes handover_check.json with the decision."""
    if HANDOVER.exists():
        raise ValueError(f"{HANDOVER} exists already: the decision is made once")
    d = e23._load_npz(DATA / "round0.npz")
    keep = d["lines"] >= LATE_FROM
    boards = {key: d[key][keep] for key in KEYS}
    backup, _ = targets(v39r_late_path(), e23._rows(boards), DEPTH, jobs)
    actual = (d["final"][keep] - d["score"][keep]) / TETRIS_18
    result = {"experiment": "033-v29-20hz", "format": format_of(_frozen()[0]),
              "versions": runner._record_versions(), "abi_version": native.ABI_VERSION,
              "late": {"path": e23._relative(v39r_late_path()),
                       "sha256": _sha(v39r_late_path())},
              "unit": "Tetrises at level 18 (22,800 points)"} | \
        handover_decision(backup, actual, d["features"][keep][:, 3])
    _write(HANDOVER, result)
    return result


# ---------------------------------------------------------------- sweeps

def _round_path(index: int) -> Path:
    return DATA / ("round0.npz" if index == 0 else f"round{index}.npz")


def weights_path(sweep: int) -> Path:
    return v29_path() if sweep == 0 else OUT / f"value_sweep{sweep}.bin"


def _split(data: dict[str, np.ndarray], keep: np.ndarray) -> dict[str, np.ndarray]:
    return {key: value[keep] for key, value in data.items()}


def _training_parts(index: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    """Round 0 without the check seeds and the last ``KEPT_ROUNDS`` rounds before sweep
    ``index`` (whole games, hand-over boards included); round 0's check boards (the first
    ``CHECK_SEEDS`` seeds' boards below ``LATE_FROM``)."""
    zero = e23._load_npz(_round_path(0))
    held = np.isin(zero["seed"], np.array(round_seeds(0)[:CHECK_SEEDS]))
    parts = [_split(zero, ~held)]
    for k in range(max(1, index - KEPT_ROUNDS), index):
        parts.append(e23._load_npz(_round_path(k)))
    return parts, _split(zero, held & (zero["lines"] < LATE_FROM))


def sweep(index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index``: targets with the last sweep's V29@20 (hand-over to V39' by the
    hand-over check's decision), fit, check."""
    actual = _actual_handover()
    out_path = weights_path(index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    previous = weights_path(index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist")
    late = v39r_late_path()
    tick = time.time()
    parts, check = _training_parts(index)
    cache = DATA / f"targets{index}.npz"
    if cache.exists():
        stored = e23._load_npz(cache)
        data = {key: stored[key] for key in KEYS}
        goal, check_targets = stored["goal"], stored["check_targets"]
        sizes, children = stored["sizes"].tolist(), stored["children"].tolist()
    else:
        boards, goals, child_rows = [], [], []
        rng = np.random.default_rng(33_000 + index)
        for part in parts:
            rows = e23._rows(part)
            mid = part["lines"] < LATE_FROM
            backup = np.zeros(len(rows))
            backup[mid], _ = targets(previous, rows[mid], DEPTH, jobs)
            if not actual:  # else the hand-over boards' value is their actual rest of game
                backup[~mid], _ = targets(late, rows[~mid], DEPTH, jobs)
            boards.append({key: part[key][mid] for key in KEYS})
            goals.append(handover_returns(backup, part, LAMBDA, actual=actual))
            pick = rng.random(int(mid.sum())) < CHILD_SHARE
            _, kids = targets(previous, rows[mid][pick], 1, jobs, children=True)
            child_rows.append(kids)
        kids = np.concatenate(child_rows)
        kids = kids[kids[:, native.WIDTH] >= MID_FROM]
        low = kids[:, native.WIDTH] < LATE_FROM
        for subset, teacher in ((kids[low], previous), (kids[~low], late)):
            values, _ = targets(teacher, subset, DEPTH, jobs)
            boards.append(e23._boards(subset))
            goals.append(values)
        sizes = [int(len(g)) for g in goals[:len(parts)]]
        children = [int(low.sum()), int((~low).sum())]
        check_targets, _ = targets(previous, e23._rows(check), DEPTH, jobs)
        data = {key: np.concatenate([b[key] for b in boards]) for key in KEYS}
        goal = np.concatenate(goals)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partial = cache.with_name(cache.stem + ".partial.npz")
        np.savez(partial, **data, goal=goal, check_targets=check_targets,
                 sizes=np.array(sizes), children=np.array(children))
        partial.replace(cache)
    target_seconds = time.time() - tick
    settings = _load(e23.CONFIG)["fit"]
    cap = _config()["line_cap"]
    torch.manual_seed(settings["torch_seed"] + index)
    model = e20.read_export(previous).to(device)
    t = e23._tensors(data, goal, device)
    c = e23._tensors({key: check[key] for key in KEYS}, check_targets, device)
    before = e23._predict(model, c, cap).cpu().numpy()
    log = e23._fit(model, t, settings, cap)
    after = e23._predict(model, c, cap).cpu().numpy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = out_path.with_name(out_path.name + ".partial")
    sha = e20.export(model, partial)
    steps = {f"{lo}-{lo + 19}": [round(float(v[m].mean()), 3) for v in (before, check_targets,
                                                                          after)]
             for lo in range(MID_FROM, LATE_FROM, 20)
             if (m := (check["lines"] >= lo) & (check["lines"] < lo + 20)).any()}
    rms = lambda a: round(float(np.sqrt(((a - check_targets) ** 2).mean())), 4)  # noqa: E731
    result = {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "format": format_of(_frozen()[0]), "versions": runner._record_versions(),
        "torch": torch.__version__,
        "from": {"path": e23._relative(previous), "sha256": _sha(previous)},
        "late": {"path": e23._relative(late), "sha256": _sha(late)},
        "handover_value": "actual rest of game" if actual else "V39' backup2 (k 4, 20 Hz)",
        "weights": {"path": e23._relative(out_path), "sha256": sha},
        "depth": DEPTH, "lambda": LAMBDA,
        "boards": {"parts": sizes, "children_below_late_and_late": children,
                   "check": int(len(check_targets))},
        "settings": settings, "target_seconds": round(target_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "check": {"old_value_minus_target_rms": rms(before),
                  "new_value_minus_target_rms": rms(after),
                  "target_minus_old_value": round(float((check_targets - before).mean()), 4),
                  "by_20_lines_old_target_new": steps}}
    _write(OUT / f"sweep{index}.json", result)  # the log before the weights: resumable
    partial.replace(out_path)
    return result


# ---------------------------------------------------------------- probe, play

def _probe_job(job: tuple[int, str | None]) -> dict[str, Any]:
    seed, mid_path = job
    frozen, net = _frozen()
    mid = _mid_bytes(mid_path)
    return checked_game(frozen, seed, lambda: _game(net, frozen, seed, mid=mid)[0],
                        agent="probe")


def probe(mid: Path | None, jobs: int) -> list[dict[str, Any]]:
    rel = e23._relative(mid) if mid else None
    with Pool(jobs) as pool:
        return pool.map(_probe_job, [(s, rel) for s in _seeds()["probe_seeds"]], chunksize=1)


def style(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Points by band, P(230), P(320), P(39), deaths by 10-line step at 230-329, and the
    29-38, 39+ and 44+ lines / Tetrises / singles / Tetris share (031b's style)."""
    s = e25._summary(episodes)
    n = len(episodes)
    lines = [e["result"]["lines"] for e in episodes]
    bands = {band: round(sum(e["stats"]["bands"].get(band, 0) for e in episodes) / n, 1)
             for band in ("18", "19-28", "29-38", "39+")}
    return {"points_by_band": bands, "p_reach_230": s["p_reach_29"],
            "p_reach_320": sum(x >= LATE_FROM for x in lines) / n,
            "deaths_by_10_lines_230_329": death_steps(lines),
            "entry_29": s["entry_29"], "entry_39": s["entry_39"]} | e31.style(episodes)


def probe_base(jobs: int) -> dict[str, Any]:
    """v39r20 alone on the probe seeds (once), its games stored for pairing."""
    path = OUT / "probe_base.json"
    if path.exists():
        return _load(path)
    episodes = probe(None, jobs)
    result = {"agent": BASE, "format": format_of(_frozen()[0]),
              "versions": runner._record_versions(), "summary": e25._summary(episodes),
              "style": style(episodes), "episodes": episodes}
    _write(path, result)
    return result


def calibration(d: dict[str, np.ndarray], v: np.ndarray, late: np.ndarray,
                actual_handover: bool) -> dict[str, Any]:
    """V29@20's value against what each board's game went on to score and against the
    target's own definition (points to the hand-over board plus V39''s value of it, or the
    actual rest of the game with ``actual_handover``), by 10-line steps from 230; ``v`` and
    ``late`` are V29@20's and V39''s values of every board of ``d``."""
    actual = (d["final"] - d["score"]) / TETRIS_18
    defined = actual.copy()
    for t in range(len(v) - 2, -1, -1):
        if d["game"][t + 1] == d["game"][t]:
            if d["lines"][t + 1] >= LATE_FROM:
                after = actual[t + 1] if actual_handover else late[t + 1]
                defined[t] = (d["score"][t + 1] - d["score"][t]) / TETRIS_18 + after
            elif d["lines"][t] < LATE_FROM:
                defined[t] = (d["score"][t + 1] - d["score"][t]) / TETRIS_18 + defined[t + 1]
    return {f"{lo}-{lo + 9}": [round(float(x[m].mean()), 3) for x in (v, actual, defined)]
            for lo in range(MID_FROM, LATE_FROM, 10)
            if (m := (d["lines"] >= lo) & (d["lines"] < lo + 10)).any()}


def play_round(index: int, jobs: int) -> dict[str, Any]:
    """Round ``index``: the agent with V29@20 of sweep ``index``, 0.5% exploration at
    ``EXPLORE_FROM``-``EXPLORE_TO`` lines; with V29@20's calibration on its boards. The
    games that die within 10 pieces of an explored placement are not reported: neither the
    dump nor the played game records which placements were explored (a native change)."""
    path = _round_path(index)
    weights = weights_path(index)
    rel = e23._relative(weights)
    tick = time.time()
    if path.exists():  # played, but the summary below was not written: keep the games
        summary = {"resumed": "the games' summary was lost in a crash"}
    else:
        summary = _play_data(path, [(s, rel, EXPLORE) for s in round_seeds(index)], jobs)
    d = e23._load_npz(path)
    cap = _config()["line_cap"]
    args = (d["columns"], d["features"], d["lines"], d["drought"], d["last"], cap, "cpu")
    v = e24._values(e20.read_export(weights).eval(), *args)
    late = e24._values(e20.read_export(v39r_late_path()).eval(), *args)
    result = {"round": index, "weights": rel, "explore": EXPLORE,
              "explore_lines": [EXPLORE_FROM, EXPLORE_TO],
              "format": format_of(_frozen()[0]),
              "deaths_within_10_pieces_of_explored_placement": "unavailable (no native marker)",
              "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_defined_by_10_lines":
                  calibration(d, v, late, _actual_handover())} | summary
    _write(OUT / f"round{index}.json", result)
    return result


def _probe_result(index: int, jobs: int) -> dict[str, Any]:
    path = OUT / f"probe{index}.json"
    if path.exists():
        return _load(path)
    base = _load(OUT / "probe_base.json")
    weights = weights_path(index)
    episodes = probe(weights, jobs)
    result = {"sweep": index, "weights": e23._relative(weights),
              "format": format_of(_frozen()[0]), "versions": runner._record_versions(),
              "summary": e25._summary(episodes), "style": style(episodes),
              "base_style": base["style"],
              "paired_vs_v39r20": e25._paired(episodes, base["episodes"]),
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"]} for e in episodes]}
    _write(path, result)
    return result


def _means(upto: int) -> list[float]:
    return [_load(OUT / f"probe{k}.json")["paired_vs_v39r20"]["total"]["score"]["mean"]
            for k in range(1, upto + 1)]


def should_stop(index: int) -> bool:
    if index >= MAX_SWEEPS:
        return True
    if index < MIN_SWEEPS:
        return False
    means = _means(index)
    return index - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def _line(result: dict[str, Any]) -> str:
    t = result["paired_vs_v39r20"]["total"]["score"]
    s = result["style"]
    return (f"sweep {result['sweep']}: probe {t['mean']:+,.0f} ({t['ci95_low']:+,.0f}, "
            f"{t['ci95_high']:+,.0f}); bands {s['points_by_band']}; P(320) "
            f"{s['p_reach_320']}; P(39) {s['p_reach_39']}; under 330 "
            f"{s['share_lines_below_330']}")


def loop(jobs: int, device: str) -> int:
    """Sweep, probe and play the next round until the stop rule; resumable."""
    _require_clean()
    _require_wiring()
    _handover_check()
    if not _round_path(0).exists():
        raise ValueError("round 0 is missing: run round0 first")
    probe_base(jobs)
    index = 1
    while True:
        if not weights_path(index).exists():
            sweep(index, jobs, device)
        print(_line(_probe_result(index, jobs)), flush=True)
        if should_stop(index):
            return index
        # The seeds cover rounds 1 to MAX_SWEEPS - 1, which is every round a later sweep
        # trains on.
        if not (OUT / f"round{index}.json").exists():
            play_round(index, jobs)
        index += 1


def choose() -> dict[str, Any]:
    """The probed sweep with the highest paired probe mean, if above 0 (plan.md)."""
    rows = []
    for path in sorted(OUT.glob("probe[0-9]*.json")):
        r = _load(path)
        rows.append({"sweep": r["sweep"], "weights": r["weights"],
                     "probe_mean": r["paired_vs_v39r20"]["total"]["score"]["mean"]})
    best = max(rows, key=lambda r: r["probe_mean"], default=None)
    chosen = best if best and best["probe_mean"] > 0 else None
    result = {"rule": "highest paired probe mean among all probed sweeps, if above 0 "
                      "(plan.md, predeclared.md)", "format": format_of(_frozen()[0]),
              "sweeps": rows, "chosen": chosen}
    _write(CHOICE, result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment033")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="30 Hz reproduces v39r; 20 Hz format and targets")
    commands.add_parser("round0", help="v39r20 data games on round 0's seeds")
    commands.add_parser("handover", help="V39' backup2 vs the actual rest of game, round 0")
    looper = commands.add_parser("loop", help="sweep, probe, play until the stop rule")
    looper.add_argument("--device", default="cuda:0")
    commands.add_parser("choose", help="pick the V29@20 for the staged evaluation")
    for name, sub in commands.choices.items():
        if name != "choose":
            sub.add_argument("--jobs", type=int, default=6 if name == "check" else 28)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        if args.command == "round0":
            print(json.dumps(round0(args.jobs))[:400])
        elif args.command == "handover":
            print(json.dumps(handover_check(args.jobs))[:600])
        elif args.command == "loop":
            print(f"stopped after sweep {loop(args.jobs, args.device)}")
        else:
            print(json.dumps(choose()["chosen"]))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
