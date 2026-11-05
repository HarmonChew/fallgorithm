"""Run Experiment 031: V39 re-taught on v29's own games (more Tetrises near the cap).

    python -m block_stack_ai.experiment031 check [--jobs N]
    python -m block_stack_ai.experiment031 round0 [--jobs N]
    python -m block_stack_ai.experiment031 loop [--jobs N] [--device D]
    python -m block_stack_ai.experiment031 choose

The agent is 030's record agent ``v29`` (v15 below 230 lines, 030's chosen V29 at 230-319,
029's V39 from 320) with its late network re-taught: V39' (native/netsearch.hpp
``set_late_net`` for every decision at ``LATE_FROM`` lines or more, V29 frozen as the mid
network). Sweep s backs up the training boards (all at ``LATE_FROM`` lines or more, from
the agent's own games) with V39' of sweep s-1 (sweep 0 = 029's V39) as the frozen
teacher, two unknown pieces deep (027's backup2, k 4; 029's arm t2), with 023's
lambda-returns along each game to its end, fits V39' of sweep s warm-started from it,
probes the agent on 300 seeds against ``v29``, checks its 39+ ranking at 017's
rollout-ranked decisions (024's check) and plays the next round (plan.md, Phase C).
``choose`` picks the V39' for the staged evaluation.
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

import numpy as np
import torch

from . import experiment013 as e13, experiment020 as e20, experiment023 as e23
from . import experiment024 as e24, experiment025 as e25, experiment028 as e28
from . import experiment029 as e29, experiment030 as e30, experiment030eval as e30eval
from . import native, register, runner

OUT = runner.PROJECT_ROOT / "experiments" / "031-v39-retuned-cap"
DATA = runner.PROJECT_ROOT / "runs" / "031-data"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
MID_FROM = e30.MID_FROM    # 230: V29 (frozen) ...
LATE_FROM = e29.LATE_FROM  # 320: ... then V39', the network taught here
DEPTH = 4                  # backup2 with k 4 (029's arm t2)
NEVER = e28.NEVER
EXTRA_PROBE_SEEDS, ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS = 200, 400, 200, 40
KEPT_ROUNDS = 3            # own rounds kept besides round 0
MIN_SWEEPS, MAX_SWEEPS, STOP_AFTER_FLAT = 5, 8, 3
LAMBDA = 0.95
EXPLORE, EXPLORE_FROM, EXPLORE_TO = 0.01, 300, 0  # own rounds only: 300 lines to the end (0)
CHILD_SHARE = 1 / 3
NEAR_CAP_LEVEL = 44        # 380 lines from level 18: the "near the cap" Tetris share
NEAR_CAP_LINES = 380
KEYS = e23.KEYS
TETRIS_18 = e20.TETRIS_18
CLEAR_POINTS = (0, 40, 100, 300, 1200)

_load, _write = e13._load, e13._write


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen() -> tuple[dict[str, Any], bytes]:
    return e29._frozen()


def _config() -> dict[str, Any]:
    return e29._config()


def v29_path() -> Path:
    """030's chosen V29 (the mid network, frozen)."""
    return e30eval.chosen()["path"]


def v39_path() -> Path:
    """029's chosen V39: v29's late network and sweep 0's teacher."""
    return e30.v39_path()


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds after the slice 029 and 030 used: 200 extra probe seeds, then
    round 0's and the rounds' (``round_seeds``); probe seeds = 023's 100 + those 200."""
    stored = e29._seeds()
    start = e30._seeds()["used_slice"][1]
    need = EXTRA_PROBE_SEEDS + ROUND0_SEEDS + ROUND_SEEDS * (MAX_SWEEPS - 1)
    train = stored["training_seeds"][start:start + need]
    if len(train) < need:
        raise ValueError(f"only {len(train)} unused training seeds, {need} needed")
    result = {"selection": f"029's training seeds (029's seeds.json) from index {start} on "
                           f"(029 used 0-1,699, 030 1,700-{start - 1}): {EXTRA_PROBE_SEEDS} "
                           f"extra probe seeds, then round 0's {ROUND0_SEEDS}, then rounds "
                           f"of {ROUND_SEEDS}",
              "used_slice": [start, start + need],
              "probe_seeds": stored["probe_seeds"] + train[:EXTRA_PROBE_SEEDS],
              "training_seeds": train[EXTRA_PROBE_SEEDS:]}
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

def _game(net: bytes, frozen: dict[str, Any], seed: int, *, late: bytes, mid: bytes,
          explore: float = 0.0, dump: bool = False) -> tuple[dict[str, Any], bytes | None]:
    return native.late_hybrid_game(
        net, frozen["game"], seed, late=late, late_from_lines=LATE_FROM, mid=mid,
        mid_from_lines=MID_FROM, commit_level=e28.COMMIT_LEVEL, adjust_k=e28.ADJUST_K,
        adjust_max_level=e28.ADJUST_MAX_LEVEL, deep2_level=e28.DEEP2_LEVEL,
        deep2_k=e28.DEEP2_K, switch_level=NEVER, line_cap=frozen["line_cap"],
        frame_cap=frozen["frame_cap"], limits=e13._limits(frozen),
        params=native.params(frozen["params"]), explore=explore,
        explore_from_lines=EXPLORE_FROM, explore_to_lines=EXPLORE_TO, explore_seed=seed,
        dump=dump)


def _late_bytes(late_path: str | None) -> bytes:
    """A late network's weights (a path relative to the project), None: 029's V39."""
    return (runner.PROJECT_ROOT / late_path).read_bytes() if late_path else \
        v39_path().read_bytes()


def _data_job(job: tuple[int, str | None, float]) -> dict[str, Any]:
    seed, late_path, explore = job
    frozen, net = _frozen()
    played, rows = _game(net, frozen, seed, late=_late_bytes(late_path),
                         mid=v29_path().read_bytes(), explore=explore, dump=True)
    return {"seed": seed, "source": 0, "score": played["score"], "lines": played["lines"],
            "rows": e29._late_rows(rows).tobytes()}


def _require_clean() -> None:
    import subprocess
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _play_data(path: Path, work: list[tuple], jobs: int) -> dict[str, Any]:
    return e29._play_data(path, work, jobs, job=_data_job)


def _require_wiring() -> None:
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION:
        raise ValueError(f"{WIRING} is missing or not matched on this build: run check")


def round0(jobs: int) -> dict[str, Any]:
    """``v29`` on round 0's seeds, no exploration; boards from ``LATE_FROM`` lines."""
    path = DATA / "round0.npz"
    if path.exists():
        raise ValueError(f"{path} exists already")
    _require_clean()
    _require_wiring()
    seeds = round_seeds(0)
    tick = time.time()
    summary = _play_data(path, [(s, None, 0.0) for s in seeds], jobs)
    result = {"experiment": "031-v39-retuned-cap", "round": 0, "seeds": len(seeds),
              "versions": runner._record_versions(), "abi_version": native.ABI_VERSION,
              "agent": "v29 (030's record agent)", "mid_from_lines": MID_FROM,
              "late_from_lines": LATE_FROM, "seconds": round(time.time() - tick, 1),
              "board_stats": board_stats(e23._load_npz(path))} | summary
    _write(OUT / "round0.json", result)
    return result


# ---------------------------------------------------------------- wiring

def _v29_games(stage: str) -> list[dict[str, Any]]:
    """030's stored games of v29 on the stage, checked to be the stage's seeds in order with
    the current V29 (V39 drift is caught by the wiring check and the replay gate)."""
    path = e30eval.games_path(stage)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    if record["chosen"]["sha256"] != _sha(v29_path()):
        raise ValueError(f"{path} was not played with the current V29")
    episodes = record["episodes"]
    if [e["seed"] for e in episodes] != e25._seeds(stage):
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    return episodes


def _wiring_job(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    kind, reference = job
    frozen, net = _frozen()
    seed = reference["seed"]
    late = {"late_v39_is_v29": v39_path().read_bytes(),
            "late_v29_differs": v29_path().read_bytes()}[kind]
    played, _ = _game(net, frozen, seed, late=late, mid=v29_path().read_bytes())
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
           played["lines"]]
    want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    if kind == "late_v29_differs":  # a different late network is used, so the game changes
        return {"kind": kind, "seed": seed, "match": got[0] != want[0]}
    same = got == want
    return {"kind": kind, "seed": seed, "match": same,
            "got": None if same else [got[0] == want[0], *got[1:]],
            "want": None if same else [True, *want[1:]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """On 030's first 3 stored screening games of v29: this runner's game with 029's V39 as
    the late network reproduces them (inputs, score, lines); V29 as the late network
    changes their inputs (the late network is used)."""
    base = _v29_games("screening")[:3]
    kinds = ("late_v39_is_v29", "late_v29_differs")
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, [(k, e) for k in kinds for e in base], chunksize=1)
    result = {"experiment": "031-v39-retuned-cap", "games": found,
              "matched": len(found) == 6 and all(g["match"] for g in found),
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- board statistics

def clears(data: dict[str, np.ndarray], start_level: int = 18) -> np.ndarray:
    """Lines cleared by the placement made from each board (0-4), the game-ending one
    included: from the next board of the same game, or for a game's last board from its
    final score (the clear's points at the level before or after the clear)."""
    lines, game = data["lines"].astype(np.int64), data["game"]
    score, final = data["score"].astype(np.int64), data["final"].astype(np.int64)
    n = len(lines)
    out = np.zeros(n, np.int64)
    if n == 0:
        return out
    same = np.r_[game[1:] == game[:-1], False]
    out[:-1] = lines[1:] - lines[:-1]
    for t in np.flatnonzero(~same):
        gained = int(final[t] - score[t])
        out[t] = 0
        for k in (4, 3, 2, 1):
            levels = {native.level_for_lines(int(lines[t]), start_level),
                      native.level_for_lines(int(lines[t]) + k, start_level)}
            if any(gained == CLEAR_POINTS[k] * (lv + 1) for lv in levels):
                out[t] = k
                break
    return out


def ready_wells(columns: np.ndarray) -> np.ndarray:
    """Per board: four stacked rows with 9 of 10 cells filled whose gaps are in one column
    that is open above them and filled (or the floor) below them, so an I there clears all
    four. ``columns`` are dumped column bitmasks (c_api.cpp fn_dump_game: visible rows only,
    bit r = visible row r, row 0 at the top, 20 rows)."""
    vis = columns.astype(np.int64) & ((1 << 20) - 1)
    n = len(vis)
    every = np.arange(n)
    cells = (vis[:, :, None] >> np.arange(20)) & 1        # board, column, row (top 0)
    nine = cells.sum(1) == 9                               # board, row
    gap = np.argmin(cells, axis=1)                         # the empty column of each row
    ready = np.zeros(n, bool)
    for r in range(17):
        ok = nine[:, r] & nine[:, r + 1] & nine[:, r + 2] & nine[:, r + 3]
        g = gap[:, r]
        ok &= (gap[:, r + 1] == g) & (gap[:, r + 2] == g) & (gap[:, r + 3] == g)
        column = vis[every, g]
        ok &= (column & ((1 << r) - 1)) == 0               # open above
        if r + 4 < 20:
            ok &= ((column >> (r + 4)) & 1) == 1           # the I stops on row r + 3
        ready |= ok
    return ready


BANDS = ((320, 330), (330, 380), (380, 410), (410, 420), (420, 428), (428, 429),
         (429, 430))


def board_stats(data: dict[str, np.ndarray]) -> dict[str, Any]:
    """By line band: boards, the share with a ready well, the Tetris share of lines cleared
    (game-ending clears included) and Tetrises per game reaching the band."""
    c = clears(data)
    ready = ready_wells(data["columns"])
    lines = data["lines"]
    out = {}
    for lo, hi in BANDS:
        m = (lines >= lo) & (lines < hi)
        cleared = int(c[m].sum())
        games = len(np.unique(data["game"][m]))
        out[f"{lo}-{hi - 1}"] = {
            "boards": int(m.sum()), "ready_well_share": round(float(ready[m].mean()), 4)
            if m.any() else None,
            "tetris_line_share": round(4 * int((c[m] == 4).sum()) / max(1, cleared), 4),
            "tetrises_per_game": round(int((c[m] == 4).sum()) / max(1, games), 3)}
    return out


# ---------------------------------------------------------------- targets and sweeps

def _round_path(index: int) -> Path:
    return DATA / ("round0.npz" if index == 0 else f"round{index}.npz")


def weights_path(sweep: int) -> Path:
    return v39_path() if sweep == 0 else OUT / f"value_sweep{sweep}.bin"


def _split(data: dict[str, np.ndarray], keep: np.ndarray) -> dict[str, np.ndarray]:
    return {key: value[keep] for key, value in data.items()}


def _training_parts(index: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    """Round 0 without the check seeds and the last ``KEPT_ROUNDS`` own rounds before sweep
    ``index``; round 0's check boards (the first ``CHECK_SEEDS`` seeds')."""
    zero = e23._load_npz(_round_path(0))
    held = np.isin(zero["seed"], np.array(round_seeds(0)[:CHECK_SEEDS]))
    parts = [_split(zero, ~held)]
    for k in range(max(1, index - KEPT_ROUNDS), index):
        parts.append(e23._load_npz(_round_path(k)))
    return parts, _split(zero, held)


def sweep(index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index``: backup2 targets with the last sweep's V39', lambda-returns along
    each own game, children; fit warm-started; check."""
    out_path = weights_path(index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    previous = weights_path(index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist")
    tick = time.time()
    parts, check = _training_parts(index)
    cache = DATA / f"targets{index}.npz"  # a crash in the fit keeps the targets
    if cache.exists():
        stored = e23._load_npz(cache)
        data = {key: stored[key] for key in KEYS}
        goal, check_targets = stored["goal"], stored["check_targets"]
        sizes, children = stored["sizes"].tolist(), int(stored["children"])
    else:
        boards, goals, child_rows = [], [], []
        rng = np.random.default_rng(31_000 + index)
        for part in parts:
            rows = e23._rows(part)
            backup, _ = e29.targets(previous, rows, DEPTH, jobs)
            boards.append({key: part[key] for key in KEYS})
            sub = {key: part[key] for key in ("score", "final", "game")}
            goals.append(e23.lambda_returns(backup, sub, LAMBDA))
            pick = rng.random(len(rows)) < CHILD_SHARE
            _, kids = e29.targets(previous, rows[pick], 1, jobs, children=True)
            child_rows.append(kids)
        kids = np.concatenate(child_rows)
        kids = kids[kids[:, native.WIDTH] >= LATE_FROM]
        kid_targets, _ = e29.targets(previous, kids, DEPTH, jobs)
        sizes, children = [int(len(g)) for g in goals], int(len(kids))
        boards.append(e23._boards(kids))
        goals.append(kid_targets)
        check_targets, _ = e29.targets(previous, e23._rows(check), DEPTH, jobs)
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
    steps = {f"{lo}-{lo + 9}": [round(float(v[m].mean()), 3) for v in (before, check_targets,
                                                                         after)]
             for lo in range(LATE_FROM, cap, 10)
             if (m := (check["lines"] >= lo) & (check["lines"] < lo + 10)).any()}
    rms = lambda a: round(float(np.sqrt(((a - check_targets) ** 2).mean())), 4)  # noqa: E731
    result = {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": e23._relative(previous), "sha256": _sha(previous)},
        "mid": {"path": e23._relative(v29_path()), "sha256": _sha(v29_path())},
        "weights": {"path": e23._relative(out_path), "sha256": sha},
        "depth": DEPTH, "lambda": LAMBDA,
        "boards": {"parts": sizes, "children": children, "check": int(len(check_targets))},
        "settings": settings, "target_seconds": round(target_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "check": {"old_value_minus_target_rms": rms(before),
                  "new_value_minus_target_rms": rms(after),
                  "target_minus_old_value": round(float((check_targets - before).mean()), 4),
                  "by_10_lines_old_target_new": steps}}
    _write(OUT / f"sweep{index}.json", result)  # the log before the weights: resumable
    partial.replace(out_path)
    return result


# ---------------------------------------------------------------- probe, ranking, play

def _probe_job(job: tuple[int, str | None]) -> dict[str, Any]:
    seed, late_path = job
    frozen, net = _frozen()
    late, mid = _late_bytes(late_path), v29_path().read_bytes()
    return register.checked_game(frozen, seed,
                                 lambda: _game(net, frozen, seed, late=late, mid=mid)[0],
                                 agent="probe")


def probe(late: Path | None, jobs: int) -> list[dict[str, Any]]:
    rel = e23._relative(late) if late else None
    with Pool(jobs) as pool:
        return pool.map(_probe_job, [(s, rel) for s in _seeds()["probe_seeds"]], chunksize=1)


def near_cap_stats(episodes: list[dict[str, Any]], from_lines: int = NEAR_CAP_LINES,
                   from_level: int = NEAR_CAP_LEVEL) -> dict[str, Any]:
    """029's late_stats from ``from_level`` (``from_lines`` from level 18) on, for the games
    whose final lines reach ``from_lines`` (the register's episodes record the entry to
    levels 29 and 39 only). ``by_level`` is keyed by the level after each clear."""
    reached = [e for e in episodes if e["result"]["lines"] >= from_lines]
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


def style(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Per game: 29-38 and 39+ (and 44+, 380 lines on) lines / Tetrises / singles / Tetris
    share, P(39), P(cap), early top-outs, 39+ points given 39."""
    s = e25._summary(episodes)
    return {"band_29_38": e30.band_stats(episodes), "late_39": e29.late_stats(episodes),
            "near_cap_44": near_cap_stats(episodes),
            "p_reach_39": s["p_reach_39"], "line_cap_share": s["line_cap_share"],
            "share_lines_below_330": s["share_lines_below_330"],
            "score_39_plus_reached": s["score_39_plus_reached"]}


def probe_base(jobs: int) -> dict[str, Any]:
    """v29 alone on the probe seeds (once), its games stored for pairing."""
    path = OUT / "probe_base.json"
    if path.exists():
        return _load(path)
    episodes = probe(None, jobs)
    result = {"agent": "v29", "versions": runner._record_versions(),
              "summary": e25._summary(episodes), "style": style(episodes),
              "episodes": episodes}
    _write(path, result)
    return result


def ranking(weights: Path, device: str) -> dict[str, Any]:
    return e29.ranking(weights, device)


def v39_ranking(device: str) -> dict[str, Any]:
    """029's V39 (sweep 0) on the 39+ ranking check, once: the eligibility bar."""
    path = OUT / "ranking_v39.json"
    if path.exists():
        return _load(path)
    result = ranking(v39_path(), device)
    _write(path, result)
    return result


def play_round(index: int, jobs: int) -> dict[str, Any]:
    """Round ``index``: the agent with V39' of sweep ``index``, 1% exploration from
    ``EXPLORE_FROM`` lines; V39' (and 029's V39) against what each board's game went on to
    score by 10 lines (calibration), and the boards' statistics."""
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
    old = e24._values(e20.read_export(v39_path()).eval(), *args)
    actual = (d["final"] - d["score"]) / TETRIS_18
    steps = {f"{lo}-{lo + 9}": [round(float(x[m].mean()), 3) for x in (v, old, actual)]
             for lo in range(LATE_FROM, cap, 10)
             if (m := (d["lines"] >= lo) & (d["lines"] < lo + 10)).any()}
    result = {"round": index, "weights": rel, "explore": EXPLORE,
              "explore_lines": [EXPLORE_FROM, EXPLORE_TO],
              "seconds": round(time.time() - tick, 1),
              "calibration_value_v39_actual_by_10_lines": steps,
              "board_stats": board_stats(d)} | summary
    _write(OUT / f"round{index}.json", result)
    return result


def _probe_result(index: int, jobs: int, device: str) -> dict[str, Any]:
    path = OUT / f"probe{index}.json"
    if path.exists():
        return _load(path)
    base = probe_base(jobs)
    weights = weights_path(index)
    episodes = probe(weights, jobs)
    result = {"sweep": index, "weights": e23._relative(weights),
              "versions": runner._record_versions(), "summary": e25._summary(episodes),
              "style": style(episodes), "base_style": base["style"],
              "paired_vs_v29": e25._paired(episodes, base["episodes"]),
              "ranking": ranking(weights, device),
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"]} for e in episodes]}
    _write(path, result)
    return result


def _means(upto: int) -> list[float]:
    return [_load(OUT / f"probe{k}.json")["paired_vs_v29"]["total"]["score"]["mean"]
            for k in range(1, upto + 1)]


def should_stop(index: int) -> bool:
    if index >= MAX_SWEEPS:
        return True
    if index < MIN_SWEEPS:
        return False
    means = _means(index)
    return index - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def _line(result: dict[str, Any]) -> str:
    t = result["paired_vs_v29"]["total"]["score"]
    s = result["style"]
    return (f"sweep {result['sweep']}: probe {t['mean']:+,.0f} ({t['ci95_low']:+,.0f}, "
            f"{t['ci95_high']:+,.0f}); 39+ {s['late_39']['tetrises']} Tetrises / "
            f"{s['late_39']['singles']} singles, share {s['late_39']['tetris_line_share']}; "
            f"44+ share {s['near_cap_44']['tetris_line_share']}; P(39) {s['p_reach_39']}; "
            f"cap {s['line_cap_share']}; odd loss "
            f"{result['ranking']['commit 39+']['network_odd_loss']}")


def loop(jobs: int, device: str) -> int:
    """Sweep, probe and play the next round until the stop rule; resumable."""
    _require_clean()
    _require_wiring()
    if not _round_path(0).exists():
        raise ValueError("round 0 is missing: run round0 first")
    v39_ranking(device)
    index = 1
    while True:
        if not weights_path(index).exists():
            sweep(index, jobs, device)
        print(_line(_probe_result(index, jobs, device)), flush=True)
        if not (OUT / f"round{index}.json").exists():  # the last one: diagnostics only
            play_round(index, jobs)
        if should_stop(index):
            return index
        index += 1


def choose(device: str = "cuda:0") -> dict[str, Any]:
    """Among the probed sweeps whose 39+ ranking loss (odd rollouts) is no worse than 029's
    V39's, the one with the highest paired probe mean (plan.md)."""
    key = "commit 39+"
    bar = v39_ranking(device)[key]["network_odd_loss"]
    rows = []
    for path in sorted(OUT.glob("probe[0-9]*.json")):
        r = _load(path)
        rows.append({"sweep": r["sweep"], "weights": r["weights"],
                     "probe_mean": r["paired_vs_v29"]["total"]["score"]["mean"],
                     "odd_loss_39": r["ranking"][key]["network_odd_loss"]})
    eligible = [r for r in rows if r["odd_loss_39"] <= bar]
    chosen = max(eligible, key=lambda r: r["probe_mean"], default=None)
    result = {"v39_odd_loss_39": bar, "sweeps": rows, "chosen": chosen}
    _write(OUT / "chosen.json", result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment031")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="029's V39 as the late network reproduces v29's games")
    commands.add_parser("round0", help="v29 data games on round 0's seeds")
    looper = commands.add_parser("loop", help="sweep, probe, play until the stop rule")
    looper.add_argument("--device", default="cuda:0")
    chooser = commands.add_parser("choose", help="pick the V39' for the staged evaluation")
    chooser.add_argument("--device", default="cuda:0")  # as the loop's ranking bar
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
            print(f"stopped after sweep {loop(args.jobs, args.device)}")
        else:
            print(json.dumps(choose(args.device)["chosen"]))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
