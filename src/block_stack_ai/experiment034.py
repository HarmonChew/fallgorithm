"""Run Experiment 034: V29@20 re-taught with the actual 20 Hz hand-over value.

    python -m block_stack_ai.experiment034 calibrate [--jobs N]
    python -m block_stack_ai.experiment034 check [--jobs N]
    python -m block_stack_ai.experiment034 round0 [--jobs N]
    python -m block_stack_ai.experiment034 loop [--jobs N] [--device D]
    python -m block_stack_ai.experiment034 choose

The agent is 033's record ``v29r20`` (023's v15 below 230 lines, 033's sweep 6 V29@20 at
230-319, 031b's V39' from 320, at 20 Hz / 300 ms). 033's recipe and format (``experiment033``
supplies the format, the games, the target job and the guards), with four changes
(plan.md):

1. the hand-over board's value in the lambda-returns is the actual rest of its game;
2. hand-over boards are training rows, target = the actual rest of their game;
3. children at 320+ lines get ``max(0, c x V39' backup2)``, with ``c`` frozen by
   ``calibrate`` (``handover_calibration.json``) from 033's rounds 6-8, never refit;
4. lambda 0.99.

Sweep 0 is 033's sweep 6. The stop rule waits for V29@20's values to match the actual rest
of game within ``GATE`` Tetrises at every 10-line step of 270-319 (``should_stop``).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import experiment013 as e13, experiment020 as e20, experiment023 as e23
from . import experiment024 as e24, experiment025 as e25, experiment029 as e29
from . import experiment033 as e33, native, runner
from .engine import create_game

OUT = runner.PROJECT_ROOT / "experiments" / "034-v29-20hz-true-handover"
DATA = runner.PROJECT_ROOT / "runs" / "034-data"
DATA_033 = e33.DATA
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
CALIBRATION = OUT / "handover_calibration.json"
CHOICE = OUT / "chosen.json"
MID_FROM, LATE_FROM, DEPTH = e33.MID_FROM, e33.LATE_FROM, e33.DEPTH
PROBE_SEEDS, ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS = 500, 400, 200, 40
FIRST_UNUSED = 11_500      # 029-033 used the training seeds before this index
KEPT_ROUNDS = 3
MIN_SWEEPS, MAX_SWEEPS, STOP_AFTER_FLAT = 5, 10, 3
LAMBDA = 0.99
EXPLORE = e33.EXPLORE      # 0.5% at 210-319 lines, own rounds only
CHILD_SHARE = e33.CHILD_SHARE
CALIBRATION_ROUNDS = (6, 7, 8)  # 033's rounds the scale c is fitted on
GATE, GATE_FROM = 2.0, 270  # stop only once |value - actual| <= 2 at every step 270-319
KEYS = e23.KEYS
TETRIS_18 = e33.TETRIS_18
BASE = "v29r20"
ARM = "v29t20"
BASE_WEIGHTS = "experiments/033-v29-20hz/value_sweep6.bin"  # 033's chosen V29@20
ABI_033 = 28

_load, _write = e13._load, e13._write
_sha = e33._sha
format_of, checked_game = e33.format_of, e33.checked_game


def _frozen() -> tuple[dict[str, Any], bytes]:
    return e33._frozen()


def base_path() -> Path:
    """033's chosen V29@20 (v29r20's mid network, sweep 0 here), checked against 033's
    chosen.json and its stored held-out games."""
    path = runner.PROJECT_ROOT / BASE_WEIGHTS
    if _load(e33.CHOICE)["chosen"]["weights"] != BASE_WEIGHTS:
        raise ValueError(f"033's chosen.json does not name {BASE_WEIGHTS}")
    return path


def library_record() -> dict[str, Any]:
    """The native library's path, sha256 and ABI version; the ABI must be 033's."""
    path = native.library_path()
    if native.ABI_VERSION != ABI_033:
        raise ValueError(f"native ABI {native.ABI_VERSION}, 033 played with {ABI_033}")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "abi_version": native.ABI_VERSION,
            "vs_033": "033's records hold no library sha, so it cannot be compared; the "
                      "ABI equals 033's and the re-run gates check the play"}


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds from index 11,500 (029-033 used 0-11,499): 500 probe seeds,
    round 0's 400, then rounds 1-9 of 200 (11,500-14,199)."""
    stored = e29._seeds()
    start = e33._seeds()["used_slice"][1]
    if start != FIRST_UNUSED:
        raise ValueError(f"033 reserved training seeds up to {start}, not {FIRST_UNUSED}")
    need = PROBE_SEEDS + ROUND0_SEEDS + ROUND_SEEDS * (MAX_SWEEPS - 1)
    train = stored["training_seeds"][start:start + need]
    if len(train) < need:
        raise ValueError(f"only {len(train)} unused training seeds, {need} needed")
    result = {"selection": f"029's training seeds (029's seeds.json) from index {start} on "
                           f"(029-033 used 0-{start - 1}): {PROBE_SEEDS} probe seeds, then "
                           f"round 0's {ROUND0_SEEDS}, then rounds 1-{MAX_SWEEPS - 1} of "
                           f"{ROUND_SEEDS}",
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


# ---------------------------------------------------------------- guards

def _require_clean() -> None:
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _require_committed(*paths: Path) -> None:
    """Each file is tracked by git and unmodified."""
    for path in paths:
        rel = str(path.relative_to(runner.PROJECT_ROOT))
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                                 cwd=runner.PROJECT_ROOT, capture_output=True)
        same = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel],
                              cwd=runner.PROJECT_ROOT)
        if tracked.returncode or same.returncode:
            raise ValueError(f"{rel} is not committed: commit it before playing")


def _require_wiring() -> None:
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION:
        raise ValueError(f"{WIRING} is missing or not matched on this build: run check")
    if wiring.get("calibration_sha256") != calibration()["sha256"]:
        raise ValueError(f"{WIRING} was made with another calibration: run check again")


# ---------------------------------------------------------------- the calibration

def _payload_sha(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def calibration() -> dict[str, Any]:
    """The frozen hand-over calibration, its sha checked."""
    if not CALIBRATION.exists():
        raise ValueError(f"{CALIBRATION} is missing: run calibrate first")
    found = _load(CALIBRATION)
    if found.get("sha256") != _payload_sha(found):
        raise ValueError(f"{CALIBRATION} was edited after calibrate wrote it")
    return found


def scale() -> float:
    return float(calibration()["c"])


def fit_scale(backup: np.ndarray, actual: np.ndarray) -> float:
    """The scale through the origin: mean(actual) / mean(backup)."""
    return float(np.mean(actual) / np.mean(backup))


def scaled(backup: np.ndarray, c: float) -> np.ndarray:
    """``max(0, c x backup)``: V39''s backup2 brought to 20 Hz, never below death."""
    return np.maximum(0.0, c * np.asarray(backup, np.float64))


def _thirds(height: np.ndarray, **columns: np.ndarray) -> dict[str, Any]:
    out = {}
    for name, third in zip(("shortest", "middle", "tallest"),
                           np.array_split(np.argsort(height, kind="stable"), 3)):
        out[name] = {"boards": int(len(third))} | {
            f"mean_{key}": round(float(value[third].mean()), 3) for key, value in columns.items()}
    return out


def _handover_boards(data: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    keep = data["lines"] >= LATE_FROM
    return {key: value[keep] for key, value in data.items()}


def calibrate(jobs: int) -> dict[str, Any]:
    """c = mean(actual rest of game) / mean(V39' backup2 k 4 at 20 Hz) on the hand-over
    boards of 033's rounds 6-8; written once with its own sha, before any 034 game."""
    if CALIBRATION.exists():
        raise ValueError(f"{CALIBRATION} exists already: the scale is fitted once")
    _seeds()  # the seed reservation is written before any 034 game
    late = e33.v39r_late_path()
    parts, files = [], []
    for k in CALIBRATION_ROUNDS:
        path = DATA_033 / f"round{k}.npz"
        parts.append(_handover_boards(e23._load_npz(path)))
        files.append({"path": e23._relative(path), "sha256": _sha(path)})
    h = {key: np.concatenate([p[key] for p in parts]) for key in parts[0]}
    backup, _ = e33.targets(late, e23._rows({key: h[key] for key in KEYS}), DEPTH, jobs)
    actual = (h["final"] - h["score"]) / TETRIS_18
    c = fit_scale(backup, actual)
    payload = {
        "experiment": "034-v29-20hz-true-handover",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rule": "c = mean(actual rest of game) / mean(V39' backup2), through the origin; a "
                "320+ child's target is max(0, c x V39' backup2); fitted once, never refit "
                "(plan.md)",
        "data": files, "boards": int(len(backup)),
        "late": {"path": e23._relative(late), "sha256": _sha(late)},
        "target_job": {"depth": DEPTH, "format": format_of(_frozen()[0])},
        "versions": runner._record_versions(), "library": library_record(),
        "unit": "Tetrises at level 18 (22,800 points)",
        "c": c, "mean_backup": float(backup.mean()), "mean_actual": float(actual.mean()),
        "sd_actual": float(actual.std()),
        "correlation": float(np.corrcoef(backup, actual)[0, 1]),
        "backup_p5": float(np.percentile(backup, 5)),
        "backup_percentiles_5_25_50_75_95": [float(x) for x in
                                             np.percentile(backup, [5, 25, 50, 75, 95])],
        "by_aggregate_height_third": _thirds(h["features"][:, 3], backup=backup,
                                             actual=actual, scaled=scaled(backup, c))}
    payload["sha256"] = _payload_sha(payload)
    _write(CALIBRATION, payload)
    return payload


# ---------------------------------------------------------------- the prefix check

def prefix_frames(config: dict[str, Any], seed: int, inputs: bytes,
                  lines: int = MID_FROM) -> int:
    """The frames of a game before it first has ``lines`` cleared lines (its length if it
    never does): every input in them comes from a decision below ``lines``."""
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for frame, mask in enumerate(inputs):
            if state.lines >= lines:
                return frame
            state, _ = game.step(mask)
        return len(inputs)


def prefix_matches(config: dict[str, Any], seed: int, stored: bytes, mine: bytes) -> bool:
    """Do ``mine``'s inputs equal the stored game's before it first reaches 230 lines (the
    whole game if it never does)?"""
    n = prefix_frames(config, seed, stored)
    return len(mine) >= n and mine[:n] == stored[:n]


# ---------------------------------------------------------------- data

def _play_data(path: Path, seeds: list[int], weights: str, explore: float,
               jobs: int) -> dict[str, Any]:
    """033's data games with V29@20 ``weights`` (relative path) at 230-319 lines."""
    return e33._play_data(path, [(s, weights, explore) for s in seeds], jobs)


def round0(jobs: int) -> dict[str, Any]:
    """``v29r20`` on round 0's seeds, no exploration."""
    path = DATA / "round0.npz"
    if path.exists():
        raise ValueError(f"{path} exists already")
    _require_clean()
    _require_wiring()
    _require_committed(SEEDS, CALIBRATION, WIRING)
    seeds = round_seeds(0)
    tick = time.time()
    summary = _play_data(path, seeds, BASE_WEIGHTS, 0.0, jobs)
    result = {"experiment": "034-v29-20hz-true-handover", "round": 0, "seeds": len(seeds),
              "format": format_of(_frozen()[0]), "versions": runner._record_versions(),
              "library": library_record(), "agent": "v29r20 (033's record)",
              "weights": BASE_WEIGHTS, "weights_sha256": _sha(base_path()),
              "seconds": round(time.time() - tick, 1)} | summary
    _write(OUT / "round0.json", result)
    return result


# ---------------------------------------------------------------- targets

def returns(backup: np.ndarray, data: dict[str, np.ndarray], lam: float = LAMBDA) -> np.ndarray:
    """The lambda-returns of the boards below 320, the hand-over board's value being the
    actual rest of its game (033's ``handover_returns(actual=True)``)."""
    return e33.handover_returns(backup, data, lam, LATE_FROM, actual=True)


def handover_rows(data: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """The hand-over boards (320+ lines) as training rows, target the actual rest of their
    game in Tetrises."""
    keep = data["lines"] >= LATE_FROM
    rest = (data["final"][keep].astype(np.float64) - data["score"][keep]) / TETRIS_18
    return {key: data[key][keep] for key in KEYS}, rest


def late_child_targets(rows: np.ndarray, c: float, jobs: int) -> tuple[np.ndarray, np.ndarray]:
    """320+ children: ``max(0, c x V39' backup2)`` and the raw backup2."""
    raw, _ = e33.targets(e33.v39r_late_path(), rows, DEPTH, jobs)
    return scaled(raw, c), raw


def _round_path(index: int) -> Path:
    return DATA / ("round0.npz" if index == 0 else f"round{index}.npz")


def weights_path(sweep: int) -> Path:
    return base_path() if sweep == 0 else OUT / f"value_sweep{sweep}.bin"


def _split(data: dict[str, np.ndarray], keep: np.ndarray) -> dict[str, np.ndarray]:
    return {key: value[keep] for key, value in data.items()}


def _training_parts(index: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    """Round 0 without the check seeds and the last ``KEPT_ROUNDS`` rounds before sweep
    ``index``; round 0's check boards below 320 (diagnostic only)."""
    zero = e23._load_npz(_round_path(0))
    held = np.isin(zero["seed"], np.array(round_seeds(0)[:CHECK_SEEDS]))
    parts = [_split(zero, ~held)]
    for k in range(max(1, index - KEPT_ROUNDS), index):
        parts.append(e23._load_npz(_round_path(k)))
    return parts, _split(zero, held & (zero["lines"] < LATE_FROM))


def by_steps(lines: np.ndarray, *columns: np.ndarray, start: int = MID_FROM,
             stop: int = LATE_FROM + 10) -> dict[str, list[float]]:
    """Each column's mean by 10-line step (steps with boards only)."""
    return {f"{lo}-{lo + 9}": [round(float(x[m].mean()), 3) for x in columns]
            for lo in range(start, stop, 10)
            if (m := (lines >= lo) & (lines < lo + 10)).any()}


def gate_ok(steps: dict[str, list[float]], gate: float = GATE) -> bool:
    """Is value minus actual within ``gate`` at every 10-line step of 270-319 (each step
    [value, actual]; a missing step fails)?"""
    want = [f"{lo}-{lo + 9}" for lo in range(GATE_FROM, LATE_FROM, 10)]
    return all(k in steps and abs(steps[k][0] - steps[k][1]) <= gate for k in want)


def _values(weights: Path, d: dict[str, np.ndarray]) -> np.ndarray:
    cap = e33._config()["line_cap"]
    return e24._values(e20.read_export(weights).eval(), d["columns"], d["features"], d["lines"],
                       d["drought"], d["last"], cap, "cpu")


def calibration_table(weights: Path, d: dict[str, np.ndarray]) -> dict[str, list[float]]:
    """[V29@20's value, the actual rest of game] by 10-line step of 230-329 on ``d``'s
    boards (320-329: the hand-over boards)."""
    actual = (d["final"] - d["score"]) / TETRIS_18
    return by_steps(d["lines"], _values(weights, d), actual)


def cache_key(previous: Path, index: int) -> str:
    """What a sweep's targets depend on: lambda, depth, the child share, c (its file's sha),
    the previous V29@20 and the training rounds' data."""
    rounds = [0] + list(range(max(1, index - KEPT_ROUNDS), index))
    body = {"lambda": LAMBDA, "depth": DEPTH, "child_share": CHILD_SHARE,
            "calibration": calibration()["sha256"], "previous": _sha(previous),
            "rounds": {k: _sha(_round_path(k)) for k in rounds}}
    return json.dumps(body, sort_keys=True)


def build_targets(parts: list[dict[str, np.ndarray]], previous: Path, c: float, jobs: int,
                  rng: np.random.Generator) -> tuple[dict[str, np.ndarray], np.ndarray,
                                                     np.ndarray, np.ndarray, list[int]]:
    """The training rows and targets, in groups: each part's boards below 320 (lambda-returns
    with the actual hand-over), each part's hand-over boards (the actual rest of game), the
    children of a ``CHILD_SHARE`` of the boards below 320 at 230-319 lines (backup2 under
    ``previous``) and at 320+ (max(0, c x V39' backup2)). Returns the rows, the targets, the
    actual rest of game (NaN for children), the 320+ children's raw backup2 and the group
    sizes."""
    boards, goals, rests, child_rows = [], [], [], []
    for part in parts:
        rows = e23._rows(part)
        mid = part["lines"] < LATE_FROM
        backup = np.zeros(len(rows))
        backup[mid], _ = targets_mid(previous, rows[mid], jobs)
        boards.append({key: part[key][mid] for key in KEYS})
        goals.append(returns(backup, part))
        rests.append((part["final"][mid] - part["score"][mid]) / TETRIS_18)
        pick = rng.random(int(mid.sum())) < CHILD_SHARE
        _, kids = e33.targets(previous, rows[mid][pick], 1, jobs, children=True)
        child_rows.append(kids)
    for part in parts:
        hand, target = handover_rows(part)
        boards.append(hand)
        goals.append(target)
        rests.append(target)
    kids = np.concatenate(child_rows)
    kids = kids[kids[:, native.WIDTH] >= MID_FROM]
    low = kids[:, native.WIDTH] < LATE_FROM
    values, _ = targets_mid(previous, kids[low], jobs)
    late_values, raw_late = late_child_targets(kids[~low], c, jobs)
    for subset, value in ((kids[low], values), (kids[~low], late_values)):
        boards.append(e23._boards(subset))
        goals.append(value)
        rests.append(np.full(len(subset), np.nan))
    sizes = [int(len(g)) for g in goals]
    data = {key: np.concatenate([b[key] for b in boards]) for key in KEYS}
    return data, np.concatenate(goals), np.concatenate(rests), raw_late, sizes


def sweep(index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index``: lambda-returns (0.99, actual hand-over) under the last sweep's
    V29@20, the hand-over rows, the children (320+: max(0, c x V39' backup2)); fit; the gate
    calibration of the new V29@20 on the latest round."""
    cal = calibration()
    c = float(cal["c"])
    out_path = weights_path(index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    previous = weights_path(index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist")
    tick = time.time()
    parts, check = _training_parts(index)
    cache = DATA / f"targets{index}.npz"
    key = cache_key(previous, index)
    if cache.exists():
        stored = e23._load_npz(cache)
        if str(stored["key"]) != key:
            raise ValueError(f"{cache} was made with other settings or data: remove it")
        data = {k: stored[k] for k in KEYS}
        goal, check_targets = stored["goal"], stored["check_targets"]
        rest, raw_late = stored["rest"], stored["raw_late"]
        sizes = stored["sizes"].tolist()
    else:
        data, goal, rest, raw_late, sizes = build_targets(
            parts, previous, c, jobs, np.random.default_rng(34_000 + index))
        check_targets, _ = targets_mid(previous, e23._rows(check), jobs)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partial = cache.with_name(cache.stem + ".partial.npz")
        np.savez(partial, **data, goal=goal, check_targets=check_targets, rest=rest,
                 raw_late=raw_late, sizes=np.array(sizes), key=np.array(key))
        partial.replace(cache)
    target_seconds = time.time() - tick
    n = len(parts)
    groups = {"lambda_return_rows_by_part": sizes[:n], "handover_rows_by_part": sizes[n:2 * n],
              "children_below_320": sizes[2 * n], "children_320_plus": sizes[2 * n + 1]}
    played = np.isfinite(rest)  # the games' own boards (not the children)
    settings = _load(e23.CONFIG)["fit"]
    cap = e33._config()["line_cap"]
    torch.manual_seed(settings["torch_seed"] + index)
    model = e20.read_export(previous).to(device)
    t = e23._tensors(data, goal, device)
    ck = e23._tensors({key: check[key] for key in KEYS}, check_targets, device)
    before = e23._predict(model, ck, cap).cpu().numpy()
    log = e23._fit(model, t, settings, cap)
    after = e23._predict(model, ck, cap).cpu().numpy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = out_path.with_name(out_path.name + ".partial")
    sha = e20.export(model, partial)
    latest = e23._load_npz(_round_path(index - 1))
    gate_table = calibration_table(partial, latest)
    rms = lambda a: round(float(np.sqrt(((a - check_targets) ** 2).mean())), 4)  # noqa: E731
    result = {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "format": format_of(_frozen()[0]), "versions": runner._record_versions(),
        "library": library_record(), "torch": torch.__version__,
        "from": {"path": e23._relative(previous), "sha256": _sha(previous)},
        "late": {"path": e23._relative(e33.v39r_late_path()),
                 "sha256": _sha(e33.v39r_late_path())},
        "handover_value": "actual rest of game",
        "calibration": {"sha256": cal["sha256"], "c": c},
        "weights": {"path": e23._relative(out_path), "sha256": sha},
        "depth": DEPTH, "lambda": LAMBDA,
        "boards": groups | {"check": int(len(check_targets))},
        "late_children": {"mean_raw_backup2": _mean(raw_late),
                          "mean_target": _mean(scaled(raw_late, c)),
                          "share_raw_below_fit_p5":
                              round(float((raw_late < cal["backup_p5"]).mean()), 4)
                              if len(raw_late) else None},
        "mean_target_and_actual_by_10_lines":
            by_steps(data["lines"][played], goal[played], rest[played]),
        "settings": settings, "target_seconds": round(target_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "gate": {"round": index - 1, "value_actual_by_10_lines": gate_table,
                 "within": gate_ok(gate_table),
                 "rule": f"|value - actual| <= {GATE} at every 10-line step of "
                         f"{GATE_FROM}-{LATE_FROM - 1}, this sweep's V29@20 on the latest "
                         "round's boards (in sample: that round is in its training data; "
                         "plan.md)",
                 "reported_only_previous_net_out_of_sample":
                     calibration_table(previous, latest)},
        "check_diagnostic_only": {
            "note": "check targets are backup2 under the previous V29@20 (old bias)",
            "old_value_minus_target_rms": rms(before),
            "new_value_minus_target_rms": rms(after),
            "by_20_lines_old_target_new": {
                f"{lo}-{lo + 19}": [round(float(v[m].mean()), 3)
                                    for v in (before, check_targets, after)]
                for lo in range(MID_FROM, LATE_FROM, 20)
                if (m := (check["lines"] >= lo) & (check["lines"] < lo + 20)).any()}}}
    _write(OUT / f"sweep{index}.json", result)  # the log before the weights: resumable
    partial.replace(out_path)
    return result


def targets_mid(weights: Path, rows: np.ndarray, jobs: int) -> tuple[np.ndarray, None]:
    """backup2 (k 4, 20 Hz) under V29@20 ``weights``: 033's target job."""
    return e33.targets(weights, rows, DEPTH, jobs)


def _mean(values: np.ndarray) -> float | None:
    return round(float(np.mean(values)), 3) if len(values) else None


# ---------------------------------------------------------------- probe, play

def probe(weights: Path, jobs: int) -> list[dict[str, Any]]:
    rel = e23._relative(weights)
    with Pool(jobs) as pool:
        return pool.map(e33._probe_job, [(s, rel) for s in _seeds()["probe_seeds"]],
                        chunksize=1)


def probe_base(jobs: int) -> dict[str, Any]:
    """v29r20 alone on the probe seeds (once), its games stored for pairing."""
    path = OUT / "probe_base.json"
    if path.exists():
        return _load(path)
    episodes = probe(base_path(), jobs)
    result = {"agent": BASE, "weights": BASE_WEIGHTS, "format": format_of(_frozen()[0]),
              "versions": runner._record_versions(), "library": library_record(),
              "summary": e25._summary(episodes), "style": e33.style(episodes),
              "episodes": episodes}
    _write(path, result)
    return result


def drift(d: dict[str, np.ndarray], jobs: int) -> dict[str, Any]:
    """The frozen scale on this round's hand-over boards: actual rest of game against
    max(0, c x V39' backup2), mean and by aggregate-height third (reported only)."""
    h = _handover_boards(d)
    if not len(h["lines"]):
        return {"boards": 0}
    c = scale()
    raw, _ = e33.targets(e33.v39r_late_path(), e23._rows({k: h[k] for k in KEYS}), DEPTH, jobs)
    actual = (h["final"] - h["score"]) / TETRIS_18
    return {"boards": int(len(raw)), "mean_actual": _mean(actual),
            "mean_scaled": _mean(scaled(raw, c)), "mean_raw_backup2": _mean(raw),
            "by_aggregate_height_third": _thirds(h["features"][:, 3], actual=actual,
                                                 scaled=scaled(raw, c))}


def play_round(index: int, jobs: int) -> dict[str, Any]:
    """Round ``index``: the agent with V29@20 of sweep ``index``, 0.5% exploration at
    210-319 lines; V29@20's calibration on its boards and the scale's drift."""
    path = _round_path(index)
    weights = weights_path(index)
    rel = e23._relative(weights)
    tick = time.time()
    if path.exists():
        summary = {"resumed": "the games' summary was lost in a crash"}
    else:
        summary = _play_data(path, round_seeds(index), rel, EXPLORE, jobs)
    d = e23._load_npz(path)
    result = {"round": index, "weights": rel, "explore": EXPLORE,
              "explore_lines": [e33.EXPLORE_FROM, e33.EXPLORE_TO],
              "format": format_of(_frozen()[0]), "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_by_10_lines": calibration_table(weights, d),
              "scale_drift": drift(d, jobs)} | summary
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
              "summary": e25._summary(episodes), "style": e33.style(episodes),
              "base_style": base["style"],
              "paired_vs_v29r20": e25._paired(episodes, base["episodes"]),
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"]} for e in episodes]}
    _write(path, result)
    return result


def _means(upto: int) -> list[float]:
    return [_load(OUT / f"probe{k}.json")["paired_vs_v29r20"]["total"]["score"]["mean"]
            for k in range(1, upto + 1)]


def _gate(index: int) -> bool:
    return bool(_load(OUT / f"sweep{index}.json")["gate"]["within"])


def should_stop(index: int) -> bool:
    """At most 10 sweeps; from sweep 5, stop after 3 sweeps without a new best probe mean,
    but only once sweep ``index``'s gate holds (plan.md)."""
    if index >= MAX_SWEEPS:
        return True
    if index < MIN_SWEEPS:
        return False
    means = _means(index)
    return index - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT and _gate(index)


def _line(result: dict[str, Any], gate: dict[str, Any]) -> str:
    t = result["paired_vs_v29r20"]["total"]["score"]
    s, b = result["style"], result["base_style"]
    return (f"sweep {result['sweep']}: probe {t['mean']:+,.0f} ({t['ci95_low']:+,.0f}, "
            f"{t['ci95_high']:+,.0f}); P(320) {s['p_reach_320']} (base {b['p_reach_320']}); "
            f"gate {gate['within']} {gate['value_actual_by_10_lines']}")


def loop(jobs: int, device: str) -> int:
    """Sweep, probe and play the next round until the stop rule; resumable."""
    _require_clean()
    _require_wiring()
    _require_committed(SEEDS, CALIBRATION, WIRING)
    if not _round_path(0).exists():
        raise ValueError("round 0 is missing: run round0 first")
    probe_base(jobs)
    index = 1
    while True:
        if not weights_path(index).exists():
            sweep(index, jobs, device)
        result = _probe_result(index, jobs)
        print(_line(result, _load(OUT / f"sweep{index}.json")["gate"]), flush=True)
        if should_stop(index):
            return index
        if not (OUT / f"round{index}.json").exists():
            play_round(index, jobs)
        index += 1


def choose() -> dict[str, Any]:
    """The probed sweep with the highest paired probe mean against v29r20, if above 0."""
    rows = []
    for path in sorted(OUT.glob("probe[0-9]*.json")):
        r = _load(path)
        rows.append({"sweep": r["sweep"], "weights": r["weights"],
                     "probe_mean": r["paired_vs_v29r20"]["total"]["score"]["mean"]})
    rows.sort(key=lambda r: r["sweep"])
    best = max(rows, key=lambda r: r["probe_mean"], default=None)
    chosen = best if best and best["probe_mean"] > 0 else None
    result = {"rule": "highest paired probe mean against v29r20 among all probed sweeps, if "
                      "above 0 (plan.md, predeclared.md)", "format": format_of(_frozen()[0]),
              "sweeps": rows, "chosen": chosen}
    _write(CHOICE, result)
    return result


# ---------------------------------------------------------------- wiring

def _stored_base(stage: str) -> list[dict[str, Any]]:
    """033's stored v29r20 games of a stage (its seeds in order, played with sweep 6)."""
    import gzip
    path = e33.OUT / "games" / f"{stage}-{BASE}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    if record["weights"] != BASE_WEIGHTS or record["weights_sha256"] != _sha(base_path()):
        raise ValueError(f"{path} was not played with {BASE_WEIGHTS}")
    if record["format"] != format_of(_frozen()[0]):
        raise ValueError(f"{path} is not in the 20 Hz format")
    episodes = record["episodes"]
    if [e["seed"] for e in episodes] != e25._seeds(stage):
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    return episodes


def rerun(episodes: list[dict[str, Any]], weights: str, jobs: int) -> dict[str, Any]:
    """Re-play stored games by running the agent (with ``weights`` at 230-319): do all
    inputs match?"""
    with Pool(jobs) as pool:
        played = pool.map(e33._probe_job, [(e["seed"], weights) for e in episodes],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(episodes, played) if got["inputs"] != e["inputs"]]
    return {"games": len(episodes), "matched": len(episodes) - len(bad),
            "mismatched_seeds": bad}


def wiring_check(jobs: int) -> dict[str, Any]:
    """(1) sweep 0 at 20 Hz re-runs the first 3 stored v29r20 screening games input for
    input (and the prefix check passes them and catches a changed input); (2) 034's target
    job on sample boards below 320 equals native.backup2_values under V29@20 at tap interval
    3; (3) the 320+ child targets equal max(0, c x V39' backup2) computed directly."""
    cal = calibration()
    c = float(cal["c"])
    stored = _stored_base("screening")[:3]
    part1 = rerun(stored, BASE_WEIGHTS, jobs)
    frozen = _frozen()[0]
    prefix = []
    for e in stored:
        inputs = base64.b64decode(e["inputs"])
        n = prefix_frames(frozen, e["seed"], inputs)
        changed = bytearray(inputs)
        changed[n // 2] ^= 4
        prefix.append({"seed": e["seed"], "frames_before_230": n, "of": len(inputs),
                       "same_passes": prefix_matches(frozen, e["seed"], inputs, inputs),
                       "changed_caught": not prefix_matches(frozen, e["seed"], inputs,
                                                            bytes(changed))})
    d = e23._load_npz(DATA_033 / "round8.npz")
    mid = d["lines"] < LATE_FROM
    rows = e23._rows({k: d[k][mid] for k in KEYS})
    sample = np.ascontiguousarray(rows[:: max(1, len(rows) // 50)][:50])
    cfg = e33._config()
    args = dict(line_cap=cfg["line_cap"], start_level=cfg["start_level"],
                double_killscreen=cfg["double_killscreen"], tap_interval=3)
    got, _ = targets_mid(base_path(), sample, jobs)
    want = np.array(native.backup2_values(base_path().read_bytes(), sample.tobytes(), k=DEPTH,
                                          **args)) / TETRIS_18
    part2 = {"boards": int(len(sample)), "match": bool(np.array_equal(got, want))}
    near = (d["lines"] >= LATE_FROM - 5) & mid
    parents = e23._rows({k: d[k][near] for k in KEYS})
    parents = np.ascontiguousarray(parents[:: max(1, len(parents) // 40)][:40])
    _, kids = e33.targets(base_path(), parents, 1, jobs, children=True)
    late_kids = np.ascontiguousarray(kids[kids[:, native.WIDTH] >= LATE_FROM][:50])
    if len(late_kids) < 10:  # few sample children past 320: use the hand-over boards
        h = _handover_boards(d)
        late_kids = np.ascontiguousarray(e23._rows({k: h[k] for k in KEYS})[:50])
    mine, raw = late_child_targets(late_kids, c, jobs)
    direct = np.array(native.backup2_values(e33.v39r_late_path().read_bytes(),
                                            late_kids.tobytes(), k=DEPTH, **args)) / TETRIS_18
    part3 = {"boards": int(len(late_kids)), "c": c, "parents_315_319": int(len(parents)),
             "match": bool(np.array_equal(mine, np.maximum(0.0, c * direct)) and
                           np.array_equal(raw, direct))}
    result = {"experiment": "034-v29-20hz-true-handover", "rerun_screening_v29r20": part1,
              "prefix_check": prefix, "targets_below_320": part2, "late_children": part3,
              "format": format_of(frozen), "calibration_sha256": cal["sha256"],
              "matched": bool(part1["matched"] == 3 and part2["match"] and part3["match"]
                              and all(p["same_passes"] and p["changed_caught"]
                                      for p in prefix)),
              "abi_version": native.ABI_VERSION, "library": library_record(),
              "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment034")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("calibrate", help="the frozen 20 Hz scale of V39' backup2")
    commands.add_parser("check", help="the wiring check")
    commands.add_parser("round0", help="v29r20 data games on round 0's seeds")
    looper = commands.add_parser("loop", help="sweep, probe, play until the stop rule")
    looper.add_argument("--device", default="cuda:0")
    commands.add_parser("choose", help="pick the V29@20 for the staged evaluation")
    for name, sub in commands.choices.items():
        if name != "choose":
            sub.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "calibrate":
            found = calibrate(args.jobs)
            print(f"c = {found['c']:.4f} on {found['boards']} boards")
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "round0":
            print(json.dumps(round0(args.jobs))[:400])
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
