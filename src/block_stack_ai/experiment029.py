"""Run Experiment 029: a level-39+ value (V39) taught by search.

    python -m block_stack_ai.experiment029 check [--jobs N]
    python -m block_stack_ai.experiment029 round0 [--jobs N]
    python -m block_stack_ai.experiment029 loop ARM [--jobs N] [--device D]
    python -m block_stack_ai.experiment029 choose

The agent is 027's record agent ``e29_k4`` (frozen ``v15``) whose every decision at
``LATE_FROM`` lines or more is searched with a second network, V39
(native/netsearch.hpp ``set_late_net``: one network per decision). An arm's sweep s backs
up its training boards (all at ``LATE_FROM`` lines or more) with its V39 of sweep s-1
(sweep 0 = v15) as the frozen teacher, fits V39 of sweep s warm-started from it, probes the
agent on 023's 100 probe seeds against ``e29_k4`` alone, checks its 39+ ranking at 017's
rollout-ranked decisions (024's check), and plays the arm's next round (see plan.md). The
arms differ only in the backup: ``t1`` one unknown piece (023's), ``t2`` two (027's
backup2, k 4). ``choose`` picks the V39 for the staged evaluation (plan.md's rule).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import experiment013 as e13, experiment020 as e20, experiment021 as e21
from . import experiment023 as e23, experiment024 as e24, experiment025 as e25
from . import experiment027 as e27, experiment028 as e28, native, register, runner

OUT = runner.PROJECT_ROOT / "experiments" / "029-v39-search-taught"
DATA = runner.PROJECT_ROOT / "runs" / "029-data"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
LATE_FROM = 320          # decisions (and training boards) from here on use V39
NEVER = e28.NEVER        # a switch level no game reaches
SWITCH_017 = 39          # h39: 017 from level 39 (028)
H39_FROM_LINES = 330     # level 39 from level 18
ARMS = {"t1": 1, "t2": 4}  # arm: 1 = backup, k = backup2 with that k
ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS = 300, 200, 30
KEPT_ROUNDS = 3          # own rounds kept besides round 0
MIN_SWEEPS, MAX_SWEEPS, STOP_AFTER_FLAT = 5, 8, 3
LAMBDA = 0.95            # 023's: own-play boards' lambda-returns
EXPLORE, EXPLORE_FROM = 0.01, 300  # own rounds only: 1% a piece from 300 lines
CHILD_SHARE = 1 / 3      # the share of boards whose 7 next boards are added (children)
KEYS = e23.KEYS
TETRIS_18 = e20.TETRIS_18
RANK_DATA = e24.RANK_DATA

_load, _write = e13._load, e13._write


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen() -> tuple[dict[str, Any], bytes]:
    return e28._frozen()


def _config() -> dict[str, Any]:
    frozen, _ = _frozen()
    return {"line_cap": frozen["line_cap"], "start_level": frozen["game"]["start_level"],
            "double_killscreen": frozen["game"]["ruleset"].endswith("double_killscreen"),
            "tap_interval": e13._limits(frozen).tap_interval}


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """Training seeds: 023's play seeds in order, one per start state, none sharing a start
    state with the register's sets, 012's held-out seeds or 023's probe seeds (the probe)."""
    stored = _load(e23.SEEDS)
    probe = stored["probe_seeds"]
    seen = {e20._identity(s) for st in ("screening", "development", "heldout")
            for s in e25._seeds(st)} | {e20._identity(s) for s in probe}
    train = []
    for key in sorted(stored["play_seeds"], key=int):
        for seed in stored["play_seeds"][key]:
            identity = e20._identity(seed)
            if identity not in seen:
                train.append(seed)
                seen.add(identity)
    result = {"selection": "023's play seeds in round order, first of each start state, none "
                           "sharing a start state with the register's screening/development "
                           "sets, 012's held-out seeds or 023's probe seeds",
              "probe_seeds": probe, "training_seeds": train}
    _write(SEEDS, result)
    return result


def _seeds() -> dict[str, Any]:
    return _load(SEEDS) if SEEDS.exists() else make_seeds()


def round_seeds(index: int) -> list[int]:
    """Round 0's seeds, then each own round's next block (the same for both arms)."""
    train = _seeds()["training_seeds"]
    if index == 0:
        return train[:ROUND0_SEEDS]
    start = ROUND0_SEEDS + ROUND_SEEDS * (index - 1)
    return train[start:start + ROUND_SEEDS]


# ---------------------------------------------------------------- games

def _game(net: bytes, frozen: dict[str, Any], seed: int, *, late: bytes | None,
          switch_level: int = NEVER, explore: float = 0.0,
          dump: bool = False) -> tuple[dict[str, Any], bytes | None]:
    return native.late_hybrid_game(
        net, frozen["game"], seed, late=late, late_from_lines=LATE_FROM,
        commit_level=e28.COMMIT_LEVEL, adjust_k=e28.ADJUST_K,
        adjust_max_level=e28.ADJUST_MAX_LEVEL, deep2_level=e28.DEEP2_LEVEL,
        deep2_k=e28.DEEP2_K, switch_level=switch_level, line_cap=frozen["line_cap"],
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
        params=native.params(frozen["params"]), explore=explore,
        explore_from_lines=EXPLORE_FROM, explore_seed=seed, dump=dump)


def _late_rows(rows: bytes) -> np.ndarray:
    r = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)
    return r[r[:, native.WIDTH] >= LATE_FROM]


def _data_job(job: tuple[int, int, str | None, int, float]) -> dict[str, Any]:
    """One data game: its late boards (rows) and result."""
    seed, switch_level, late_path, source, explore = job
    frozen, net = _frozen()
    late = (runner.PROJECT_ROOT / late_path).read_bytes() if late_path else None
    played, rows = _game(net, frozen, seed, late=late, switch_level=switch_level,
                         explore=explore, dump=True)
    return {"seed": seed, "source": source, "score": played["score"],
            "lines": played["lines"], "rows": _late_rows(rows).tobytes()}


def _play_data(path: Path, jobs_list: list[tuple], jobs: int,
               job: Any = None) -> dict[str, Any]:
    """Play the data games, store their late boards as ``path`` (npz, whole games in job
    order: the rows' fields, ``score`` before the board, ``final``, ``game``, ``source``,
    ``seed``) and return a summary. ``job`` replaces ``_data_job`` (Experiment 030)."""
    with Pool(jobs) as pool:
        found = pool.map(job or _data_job, jobs_list, chunksize=1)
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
    return {"games": len(found), "boards": int(len(rows)),
            "mean_score": round(float(np.mean([g["score"] for g in found])), 1),
            "line_cap_share": round(float(np.mean([g["lines"] >= 430 for g in found])), 3),
            "by_source": {str(s): {"games": sum(g["source"] == s for g in found),
                                   "mean_score": round(float(np.mean(
                                       [g["score"] for g in found if g["source"] == s])), 1)}
                          for s in sorted({g["source"] for g in found})}}


def _require_clean() -> None:
    """Refuse uncommitted changes outside this experiment's own outputs (a resumed loop
    finds its earlier sweeps there)."""
    import subprocess
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def round0(jobs: int) -> dict[str, Any]:
    """e29_k4 (source 0) and h39 (source 1) on round 0's seeds, no exploration."""
    path = DATA / "round0.npz"
    if path.exists():
        raise ValueError(f"{path} exists already")
    _require_clean()
    seeds = round_seeds(0)
    work = [(s, NEVER, None, 0, 0.0) for s in seeds] + \
        [(s, SWITCH_017, None, 1, 0.0) for s in seeds]
    tick = time.time()
    summary = _play_data(path, work, jobs)
    result = {"experiment": "029-v39-search-taught", "round": 0, "seeds": len(seeds),
              "versions": runner._record_versions(), "abi_version": native.ABI_VERSION,
              "sources": {"0": "e29_k4 (027's record agent)",
                          "1": "h39 (e29_k4 to 38, 017 from 39; 028)"},
              "late_from_lines": LATE_FROM, "seconds": round(time.time() - tick, 1)} | summary
    _write(OUT / "round0.json", result)
    return result


# ---------------------------------------------------------------- wiring

def _wiring_job(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    kind, reference = job
    frozen, net = _frozen()
    seed = reference["seed"]
    if kind == "late_off_is_e29_k4":
        played, _ = _game(net, frozen, seed, late=None)
    else:  # v15 as the late network: the same game
        played, _ = _game(net, frozen, seed, late=net)
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
           played["lines"]]
    want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    same = got == want
    return {"kind": kind, "seed": seed, "match": same,
            "got": None if same else [got[0] == want[0], *got[1:]],
            "want": None if same else [True, *want[1:]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """On 027's first 3 stored screening games of e29_k4: no late network, and v15 as the
    late network, each reproduce them (inputs, score, lines)."""
    base = e28._base_episodes("screening", e25._seeds("screening"))[:3]
    work = [(kind, e) for kind in ("late_off_is_e29_k4", "late_v15_is_e29_k4") for e in base]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, work, chunksize=1)
    result = {"experiment": "029-v39-search-taught", "games": found,
              "matched": len(found) == 6 and all(g["match"] for g in found),
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- targets

def _target_job(job: tuple[bytes, bytes, int, bool]) -> tuple[np.ndarray, bytes | None]:
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
    """Each row's backup (depth 1) or backup2 (depth k) under ``weights``, in Tetrises at
    level 18, and with ``children`` the 7 next boards of each (those with a placement)."""
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


# ---------------------------------------------------------------- sweeps

def _arm_dir(arm: str) -> Path:
    return OUT / arm


def weights_path(arm: str, sweep: int) -> Path:
    if sweep == 0:
        return _v15_path()
    return _arm_dir(arm) / f"value_sweep{sweep}.bin"


def _v15_path() -> Path:
    return runner.PROJECT_ROOT / "experiments" / "023-self-taught-value" / "value_sweep15.bin"


def _round_path(arm: str, index: int) -> Path:
    return DATA / "round0.npz" if index == 0 else DATA / arm / f"round{index}.npz"


def _split(data: dict[str, np.ndarray], keep: np.ndarray) -> dict[str, np.ndarray]:
    return {key: value[keep] for key, value in data.items()}


def _training_parts(arm: str, sweep: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    """Round 0 without the check seeds, the arm's last ``KEPT_ROUNDS`` own rounds before
    this sweep; and round 0's check boards (the first ``CHECK_SEEDS`` seeds, both sources)."""
    zero = e23._load_npz(_round_path(arm, 0))
    # h39 plays e29_k4's game until level 39 (330 lines): keep those boards once
    zero = _split(zero, (zero["source"] == 0) | (zero["lines"] >= H39_FROM_LINES))
    check_seeds = np.array(round_seeds(0)[:CHECK_SEEDS])
    held = np.isin(zero["seed"], check_seeds)
    parts = [_split(zero, ~held)]
    for index in range(max(1, sweep - KEPT_ROUNDS), sweep):
        parts.append(e23._load_npz(_round_path(arm, index)))
    return parts, _split(zero, held)


def _part_targets(part: dict[str, np.ndarray], backup: np.ndarray) -> np.ndarray:
    """Own-play boards (round 0's e29_k4 games and own rounds) get lambda-returns along
    their games; 017's (h39, source 1) the plain backup."""
    own = part["source"] == 0
    out = backup.copy()
    if own.any():
        sub = {key: part[key][own] for key in ("score", "final", "game")}
        out[own] = e23.lambda_returns(backup[own], sub, LAMBDA)
    return out


def sweep(arm: str, index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index`` of ``arm``: targets with the last sweep's V39, fit, check."""
    out_path = weights_path(arm, index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    previous = weights_path(arm, index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist")
    depth = ARMS[arm]
    tick = time.time()
    parts, check = _training_parts(arm, index)
    cache = DATA / arm / f"targets{index}.npz"  # a crash in the fit keeps the targets
    if cache.exists():
        stored = e23._load_npz(cache)
        data = {key: stored[key] for key in KEYS}
        goal, check_targets = stored["goal"], stored["check_targets"]
        sizes, children = stored["sizes"].tolist(), int(stored["children"])
    else:
        boards, goals = [], []
        rng = np.random.default_rng(29_000 + index * 10 + depth)
        child_rows = []
        for part in parts:
            rows = e23._rows(part)
            backup, _ = targets(previous, rows, depth, jobs)
            boards.append({key: part[key] for key in KEYS})
            goals.append(_part_targets(part, backup))
            pick = rng.random(len(rows)) < CHILD_SHARE
            _, kids = targets(previous, rows[pick], 1, jobs, children=True)
            child_rows.append(kids)
        kids = np.concatenate(child_rows)
        kids = kids[kids[:, native.WIDTH] >= LATE_FROM]
        kid_targets, _ = targets(previous, kids, depth, jobs)
        sizes, children = [int(len(g)) for g in goals], int(len(kids))
        boards.append({key: value for key, value in e23._boards(kids).items()})
        goals.append(kid_targets)
        check_targets, _ = targets(previous, e23._rows(check), depth, jobs)
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
    partial.replace(out_path)
    steps = {f"{lo}-{lo + 19}": [round(float(v[m].mean()), 3) for v in (before, check_targets,
                                                                          after)]
             for lo in range(LATE_FROM, cap, 20)
             if (m := (check["lines"] >= lo) & (check["lines"] < lo + 20)).any()}
    result = {
        "arm": arm, "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": e23._relative(previous), "sha256": _sha(previous)},
        "weights": {"path": e23._relative(out_path), "sha256": sha},
        "depth": depth, "lambda": LAMBDA,
        "boards": {"parts": sizes, "children": children, "check": int(len(check_targets))},
        "settings": settings, "target_seconds": round(target_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "check": {"old_value_minus_target_rms": round(float(np.sqrt(((before - check_targets)
                                                                    ** 2).mean())), 4),
                  "new_value_minus_target_rms": round(float(np.sqrt(((after - check_targets)
                                                                    ** 2).mean())), 4),
                  "target_minus_old_value": round(float((check_targets - before).mean()), 4),
                  "by_20_lines_old_target_new": steps}}
    _write(_arm_dir(arm) / f"sweep{index}.json", result)
    return result


# ---------------------------------------------------------------- probe, ranking, play

def _probe_job(job: tuple[int, str | None]) -> dict[str, Any]:
    seed, late_path = job
    frozen, net = _frozen()
    late = (runner.PROJECT_ROOT / late_path).read_bytes() if late_path else None
    episode = register.checked_game(frozen, seed, lambda: _game(net, frozen, seed, late=late)[0],
                                    agent="probe")
    return episode


def late_stats(episodes: list[dict[str, Any]], from_level: int = 39) -> dict[str, Any]:
    """Per game reaching ``from_level``: lines, Tetrises and singles cleared from it on, and
    the share of those lines cleared by Tetrises."""
    reached = [e for e in episodes if e["stats"]["entry"].get(str(from_level))]
    totals = {"four_line": 0, "triple": 0, "double": 0, "single": 0}
    for e in reached:
        for level, v in e["stats"]["by_level"].items():
            if int(level) >= from_level:
                for key in totals:
                    totals[key] += v[key]
    n = max(1, len(reached))
    lines = 4 * totals["four_line"] + 3 * totals["triple"] + 2 * totals["double"] + \
        totals["single"]
    return {"games": len(reached), "lines": round(lines / n, 2),
            "tetrises": round(totals["four_line"] / n, 3),
            "singles": round(totals["single"] / n, 2),
            "tetris_line_share": round(4 * totals["four_line"] / max(1, lines), 4)}


def probe(late: Path | None, jobs: int) -> list[dict[str, Any]]:
    seeds = _seeds()["probe_seeds"]
    rel = e23._relative(late) if late else None
    with Pool(jobs) as pool:
        return pool.map(_probe_job, [(s, rel) for s in seeds], chunksize=1)


def probe_base(jobs: int) -> dict[str, Any]:
    """e29_k4 alone on the probe seeds (once), its games stored for pairing."""
    path = OUT / "probe_base.json"
    if path.exists():
        return _load(path)
    episodes = probe(None, jobs)
    result = {"agent": "e29_k4", "versions": runner._record_versions(),
              "summary": e25._summary(episodes), "late": late_stats(episodes),
              "episodes": episodes}
    _write(path, result)
    return result


def ranking(weights: Path, device: str) -> dict[str, Any]:
    """024's check: V's commit picks (points + V of the settled board) at 017's
    rollout-ranked decisions in 021's games, judged by the rollouts; the 39+ row."""
    c = _config()
    model = e20.read_export(weights).to(device).eval()
    _, _, rows, _ = e21.load_data(RANK_DATA)
    table = e21.table(rows, e24.rank_scores(model, rows, c["line_cap"], c["start_level"],
                                            device))
    return {"weights": e23._relative(weights), "commit 39+": table["commit 39+"]}


def play_round(arm: str, index: int, jobs: int) -> dict[str, Any]:
    """The arm's own round ``index``: the agent with V39 of sweep ``index``, 1% exploration
    from ``EXPLORE_FROM`` lines; with V39's value against what each board's game went on
    to score (calibration)."""
    path = _round_path(arm, index)
    if path.exists():
        raise ValueError(f"{path} exists already")
    weights = weights_path(arm, index)
    rel = e23._relative(weights)
    work = [(s, NEVER, rel, 0, EXPLORE) for s in round_seeds(index)]
    tick = time.time()
    summary = _play_data(path, work, jobs)
    d = e23._load_npz(path)
    model = e20.read_export(weights).eval()
    cap = _config()["line_cap"]
    v = e24._values(model, d["columns"], d["features"], d["lines"], d["drought"], d["last"],
                    cap, "cpu")
    actual = (d["final"] - d["score"]) / TETRIS_18
    steps = {f"{lo}-{lo + 19}": [round(float(v[m].mean()), 3), round(float(actual[m].mean()), 3)]
             for lo in range(LATE_FROM, cap, 20)
             if (m := (d["lines"] >= lo) & (d["lines"] < lo + 20)).any()}
    result = {"arm": arm, "round": index, "weights": rel, "explore": EXPLORE,
              "explore_from_lines": EXPLORE_FROM, "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_by_20_lines": steps} | summary
    _write(_arm_dir(arm) / f"round{index}.json", result)
    return result


def _probe_result(arm: str, index: int, jobs: int, device: str) -> dict[str, Any]:
    path = _arm_dir(arm) / f"probe{index}.json"
    if path.exists():
        return _load(path)
    base = probe_base(jobs)
    weights = weights_path(arm, index)
    episodes = probe(weights, jobs)
    paired = e25._paired(episodes, base["episodes"])
    result = {"arm": arm, "sweep": index, "weights": e23._relative(weights),
              "versions": runner._record_versions(), "summary": e25._summary(episodes),
              "late": late_stats(episodes), "base_late": base["late"],
              "paired_vs_e29_k4": paired, "ranking": ranking(weights, device),
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"]} for e in episodes]}
    _write(path, result)
    return result


def _means(arm: str, upto: int) -> list[float]:
    return [_load(_arm_dir(arm) / f"probe{k}.json")["paired_vs_e29_k4"]["total"]["score"]
            ["mean"] for k in range(1, upto + 1)]


def should_stop(arm: str, index: int) -> bool:
    """After sweep ``index``: the cap, or (from ``MIN_SWEEPS`` on) no new best probe mean
    in the last ``STOP_AFTER_FLAT`` sweeps."""
    if index >= MAX_SWEEPS:
        return True
    if index < MIN_SWEEPS:
        return False
    means = _means(arm, index)
    return index - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def loop(arm: str, jobs: int, device: str) -> int:
    """Sweep, probe and play the next round until the stop rule; resumable."""
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {tuple(ARMS)}")
    _require_clean()
    if not _round_path(arm, 0).exists():
        raise ValueError("round 0 is missing: run round0 first")
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION:
        raise ValueError(f"{WIRING} is missing or not matched on this build: run check")
    index = 1
    while True:
        if not weights_path(arm, index).exists():
            sweep(arm, index, jobs, device)
        result = _probe_result(arm, index, jobs, device)
        t = result["paired_vs_e29_k4"]["total"]["score"]
        print(f"{arm} sweep {index}: probe {t['mean']:+,.0f} ({t['ci95_low']:+,.0f}, "
              f"{t['ci95_high']:+,.0f}); 39+ {result['late']}", flush=True)
        if should_stop(arm, index):
            return index
        if not _round_path(arm, index).exists():
            play_round(arm, index, jobs)
        index += 1


def choose(device: str = "cpu") -> dict[str, Any]:
    """Among every arm's probed sweeps whose 39+ ranking loss (odd rollouts) is no worse
    than v15's, the one with the highest paired probe mean (plan.md)."""
    v15 = ranking(_v15_path(), device)["commit 39+"]["network_odd_loss"]
    rows = []
    for arm in ARMS:
        for path in sorted(_arm_dir(arm).glob("probe*.json")):
            r = _load(path)
            rows.append({"arm": arm, "sweep": r["sweep"], "weights": r["weights"],
                         "probe_mean": r["paired_vs_e29_k4"]["total"]["score"]["mean"],
                         "odd_loss_39": r["ranking"]["commit 39+"]["network_odd_loss"]})
    eligible = [r for r in rows if r["odd_loss_39"] <= v15]
    chosen = max(eligible, key=lambda r: r["probe_mean"], default=None)
    result = {"v15_odd_loss_39": v15, "sweeps": rows, "chosen": chosen}
    _write(OUT / "chosen.json", result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment029")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="late network off / v15 reproduces e29_k4's games")
    commands.add_parser("round0", help="e29_k4 and h39 data games on round 0's seeds")
    looper = commands.add_parser("loop", help="sweep, probe, play until the stop rule")
    looper.add_argument("arm", choices=tuple(ARMS))
    looper.add_argument("--device", default="cuda:0")
    chooser = commands.add_parser("choose", help="pick the V39 for the staged evaluation")
    chooser.add_argument("--device", default="cpu")
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
        elif args.command == "loop":
            print(f"{args.arm} stopped after sweep {loop(args.arm, args.jobs, args.device)}")
        else:
            print(json.dumps(choose(args.device)["chosen"]))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
