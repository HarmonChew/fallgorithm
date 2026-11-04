"""Run Experiment 030: a level-29-38 value (V29) taught by search.

    python -m block_stack_ai.experiment030 check [--jobs N]
    python -m block_stack_ai.experiment030 round0 [--jobs N]
    python -m block_stack_ai.experiment030 loop [--jobs N] [--device D]
    python -m block_stack_ai.experiment030 choose

The agent is 029's record agent ``v39`` (027's ``e29_k4`` with 029's chosen V39 for every
decision at ``LATE_FROM`` lines or more) whose decisions at ``MID_FROM`` lines or more that
are not late are searched with a third network, V29 (native/netsearch.hpp
``set_mid_net``: one network per decision). Sweep s backs up the training boards (230-319
lines) with V29 of sweep s-1 (sweep 0 = v15) as the frozen teacher, two unknown pieces
deep (027's backup2, k 4; 029's winning arm t2), with lambda-returns along each game that
hand over to the frozen V39 at the first board of 320 lines or more (``handover_returns``),
fits V29 of sweep s warm-started from it, probes the agent on 300 seeds against ``v39``
alone, checks its 29-38 ranking at 017's rollout-ranked decisions (024's check), and plays
the next round (see plan.md). ``choose`` picks the V29 for the staged evaluation.
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

from . import experiment013 as e13, experiment020 as e20, experiment021 as e21
from . import experiment023 as e23, experiment024 as e24, experiment025 as e25
from . import experiment028 as e28, experiment029 as e29, experiment029eval as e29eval
from . import native, register, runner

OUT = runner.PROJECT_ROOT / "experiments" / "030-v29-search-taught"
DATA = runner.PROJECT_ROOT / "runs" / "030-data"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
MID_FROM = 230           # decisions (and training boards) from here on use V29 ...
LATE_FROM = e29.LATE_FROM  # ... until 320, where 029's V39 takes over
DEPTH = 4                # backup2 with k 4 (029's arm t2)
NEVER = e28.NEVER
# 029 used training seeds 0-1,699 (round 0's 300, rounds 1-7 of 200)
USED_BY_029 = e29.ROUND0_SEEDS + e29.ROUND_SEEDS * (e29.MAX_SWEEPS - 1)
EXTRA_PROBE_SEEDS, ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS = 200, 400, 200, 40
KEPT_ROUNDS = 3          # own rounds kept besides round 0
MIN_SWEEPS, MAX_SWEEPS, STOP_AFTER_FLAT = 5, 10, 3
LAMBDA = 0.95
EXPLORE, EXPLORE_FROM, EXPLORE_TO = 0.01, 210, LATE_FROM  # own rounds only
CHILD_SHARE = 1 / 3
KEYS = e23.KEYS
TETRIS_18 = e20.TETRIS_18
RANK_DATA = e24.RANK_DATA

_load, _write = e13._load, e13._write


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen() -> tuple[dict[str, Any], bytes]:
    return e29._frozen()


def _config() -> dict[str, Any]:
    return e29._config()


def v39_path() -> Path:
    """029's chosen V39 (the late network, frozen)."""
    return e29eval.chosen()["path"]


def _v15_path() -> Path:
    return e29._v15_path()


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds after the ``USED_BY_029`` it used: 200 extra probe seeds, then
    round 0's and the rounds' (``round_seeds``)."""
    stored = e29._seeds()
    train = stored["training_seeds"][USED_BY_029:]
    need = EXTRA_PROBE_SEEDS + ROUND0_SEEDS + ROUND_SEEDS * (MAX_SWEEPS - 1)
    if len(train) < need:
        raise ValueError(f"only {len(train)} unused training seeds, {need} needed")
    result = {"selection": f"029's training seeds (seeds.json) from index {USED_BY_029} on: "
                           f"{EXTRA_PROBE_SEEDS} extra probe seeds, then round 0's "
                           f"{ROUND0_SEEDS}, then rounds of {ROUND_SEEDS}",
              "used_slice": [USED_BY_029, USED_BY_029 + need],
              "probe_seeds": stored["probe_seeds"] + train[:EXTRA_PROBE_SEEDS],
              "training_seeds": train[EXTRA_PROBE_SEEDS:need]}
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

def _game(net: bytes, frozen: dict[str, Any], seed: int, *, late: bytes, mid: bytes | None,
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


def _mid_rows(rows: bytes) -> np.ndarray:
    """A game's boards from ``MID_FROM`` lines on, up to and including its first board at
    ``LATE_FROM`` or more (the hand-over board), in order."""
    r = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)
    lines = r[:, native.WIDTH]
    r, lines = r[lines >= MID_FROM], lines[lines >= MID_FROM]
    late = np.flatnonzero(lines >= LATE_FROM)
    return r[:late[0] + 1] if len(late) else r


def _data_job(job: tuple[int, str | None, float]) -> dict[str, Any]:
    seed, mid_path, explore = job
    frozen, net = _frozen()
    late = v39_path().read_bytes()
    mid = (runner.PROJECT_ROOT / mid_path).read_bytes() if mid_path else None
    played, rows = _game(net, frozen, seed, late=late, mid=mid, explore=explore, dump=True)
    return {"seed": seed, "source": 0, "score": played["score"], "lines": played["lines"],
            "rows": _mid_rows(rows).tobytes()}


def _require_clean() -> None:
    import subprocess
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _play_data(path: Path, work: list[tuple], jobs: int) -> dict[str, Any]:
    """029's _play_data with this experiment's data games."""
    return e29._play_data(path, work, jobs, job=_data_job)


def _require_wiring() -> None:
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("abi_version") != native.ABI_VERSION:
        raise ValueError(f"{WIRING} is missing or not matched on this build: run check")


def round0(jobs: int) -> dict[str, Any]:
    """``v39`` on round 0's seeds, no exploration; then backup2's cost timed on a sample."""
    path = DATA / "round0.npz"
    if path.exists():
        raise ValueError(f"{path} exists already")
    _require_clean()
    _require_wiring()
    seeds = round_seeds(0)
    tick = time.time()
    summary = _play_data(path, [(s, None, 0.0) for s in seeds], jobs)
    seconds = round(time.time() - tick, 1)
    d = e23._load_npz(path)
    rows = e23._rows(d)
    sample = rows[rows[:, native.WIDTH] < LATE_FROM][:: max(1, len(rows) // 2000)][:2000]
    tock = time.time()
    e29.targets(_v15_path(), sample, DEPTH, jobs)
    result = {"experiment": "030-v29-search-taught", "round": 0, "seeds": len(seeds),
              "versions": runner._record_versions(), "abi_version": native.ABI_VERSION,
              "agent": "v39 (029's record agent)", "mid_from_lines": MID_FROM,
              "late_from_lines": LATE_FROM, "seconds": seconds,
              "backup2_seconds_per_board_x_jobs": round((time.time() - tock) * jobs /
                                                        max(1, len(sample)), 4)} | summary
    _write(OUT / "round0.json", result)
    return result


# ---------------------------------------------------------------- wiring

def _v39_games(stage: str) -> list[dict[str, Any]]:
    """029's stored games of v39 on the stage, checked to be the stage's seeds in order with
    the current V39."""
    path = e29eval.games_path(stage)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    if record["chosen"]["sha256"] != _sha(v39_path()):
        raise ValueError(f"{path} was not played with the current V39")
    episodes = record["episodes"]
    if [e["seed"] for e in episodes] != e25._seeds(stage):
        raise ValueError(f"{path} does not cover exactly the {stage} seeds in order")
    return episodes


def _wiring_job(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    kind, reference = job
    frozen, net = _frozen()
    seed = reference["seed"]
    late = v39_path().read_bytes()
    mid = {"mid_off_is_v39": None, "mid_v15_is_v39": net, "mid_v39_differs": late}[kind]
    played, _ = _game(net, frozen, seed, late=late, mid=mid)
    got = [base64.b64encode(played["inputs"]).decode("ascii"), played["score"],
           played["lines"]]
    want = [reference["inputs"], reference["result"]["score"], reference["result"]["lines"]]
    same = got == want
    if kind == "mid_v39_differs":  # a mid network that is used changes the game
        return {"kind": kind, "seed": seed, "match": got[0] != want[0]}
    return {"kind": kind, "seed": seed, "match": same,
            "got": None if same else [got[0] == want[0], *got[1:]],
            "want": None if same else [True, *want[1:]]}


def wiring_check(jobs: int) -> dict[str, Any]:
    """On 029's first 3 stored screening games of v39: no mid network, and v15 as the mid
    network, each reproduce them (inputs, score, lines); V39 as the mid network changes
    their inputs (the mid network is used)."""
    base = _v39_games("screening")[:3]
    kinds = ("mid_off_is_v39", "mid_v15_is_v39", "mid_v39_differs")
    work = [(kind, e) for kind in kinds for e in base]
    with Pool(jobs) as pool:
        found = pool.map(_wiring_job, work, chunksize=1)
    result = {"experiment": "030-v29-search-taught", "games": found,
              "matched": len(found) == 9 and all(g["match"] for g in found),
              "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- targets

def handover_returns(backup: np.ndarray, data: dict[str, np.ndarray], lam: float,
                     late_from: int = LATE_FROM) -> np.ndarray:
    """Each board's lambda-return along its own game, in Tetrises at level 18, for the
    boards below ``late_from`` lines (in order); ``backup`` holds every board's backup, and
    for a hand-over board (``late_from`` or more, at most one per game, its last) the
    late network's backup A_h, which ends the chain there:
    G_t = (1 - lam) B_t + lam (points until the next board + G_{t+1}), with G_h = A_h, and
    after a game's last board the rest of its points (G = 0 once it is over)."""
    points = data["score"].astype(np.float64) / TETRIS_18
    final = data["final"].astype(np.float64) / TETRIS_18
    lines, game = data["lines"], data["game"]
    out = np.zeros(len(backup))
    for t in range(len(backup) - 1, -1, -1):
        if lines[t] >= late_from:
            out[t] = backup[t]
            continue
        if t == len(backup) - 1 or game[t + 1] != game[t]:
            step, following = final[t] - points[t], 0.0
        else:
            step, following = points[t + 1] - points[t], out[t + 1]
        out[t] = (1 - lam) * backup[t] + lam * (step + following)
    return out[lines < late_from]


def _round_path(index: int) -> Path:
    return DATA / ("round0.npz" if index == 0 else f"round{index}.npz")


def weights_path(sweep: int) -> Path:
    return _v15_path() if sweep == 0 else OUT / f"value_sweep{sweep}.bin"


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
    """Sweep ``index``: targets with the last sweep's V29 (hand-over to V39), fit, check."""
    out_path = weights_path(index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    previous = weights_path(index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist")
    late = v39_path()
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
        rng = np.random.default_rng(30_000 + index)
        for part in parts:
            rows = e23._rows(part)
            mid = part["lines"] < LATE_FROM
            backup = np.zeros(len(rows))
            backup[mid], _ = e29.targets(previous, rows[mid], DEPTH, jobs)
            backup[~mid], _ = e29.targets(late, rows[~mid], DEPTH, jobs)
            boards.append({key: part[key][mid] for key in KEYS})
            goals.append(handover_returns(backup, part, LAMBDA))
            pick = rng.random(int(mid.sum())) < CHILD_SHARE
            _, kids = e29.targets(previous, rows[mid][pick], 1, jobs, children=True)
            child_rows.append(kids)
        kids = np.concatenate(child_rows)
        kids = kids[kids[:, native.WIDTH] >= MID_FROM]
        low = kids[:, native.WIDTH] < LATE_FROM
        for subset, teacher in ((kids[low], previous), (kids[~low], late)):
            values, _ = e29.targets(teacher, subset, DEPTH, jobs)
            boards.append(e23._boards(subset))
            goals.append(values)
        sizes = [int(len(g)) for g in goals[:len(parts)]]
        children = [int(low.sum()), int((~low).sum())]
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
    steps = {f"{lo}-{lo + 19}": [round(float(v[m].mean()), 3) for v in (before, check_targets,
                                                                          after)]
             for lo in range(MID_FROM, LATE_FROM, 20)
             if (m := (check["lines"] >= lo) & (check["lines"] < lo + 20)).any()}
    rms = lambda a: round(float(np.sqrt(((a - check_targets) ** 2).mean())), 4)  # noqa: E731
    result = {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": e23._relative(previous), "sha256": _sha(previous)},
        "late": {"path": e23._relative(late), "sha256": _sha(late)},
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


# ---------------------------------------------------------------- probe, ranking, play

def _probe_job(job: tuple[int, str | None]) -> dict[str, Any]:
    seed, mid_path = job
    frozen, net = _frozen()
    late = v39_path().read_bytes()
    mid = (runner.PROJECT_ROOT / mid_path).read_bytes() if mid_path else None
    return register.checked_game(frozen, seed,
                                 lambda: _game(net, frozen, seed, late=late, mid=mid)[0],
                                 agent="probe")


def band_stats(episodes: list[dict[str, Any]], low: int = 29, high: int = 38) -> dict[str, Any]:
    """Per game reaching ``low``: lines, Tetrises and singles cleared at levels ``low`` to
    ``high``, and the share of those lines cleared by Tetrises."""
    reached = [e for e in episodes if e["stats"]["entry"].get(str(low))]
    totals = {"four_line": 0, "triple": 0, "double": 0, "single": 0}
    for e in reached:
        for level, v in e["stats"]["by_level"].items():
            if low <= int(level) <= high:
                for key in totals:
                    totals[key] += v[key]
    n = max(1, len(reached))
    lines = 4 * totals["four_line"] + 3 * totals["triple"] + 2 * totals["double"] + \
        totals["single"]
    return {"games": len(reached), "lines": round(lines / n, 2),
            "tetrises": round(totals["four_line"] / n, 3),
            "singles": round(totals["single"] / n, 2),
            "tetris_line_share": round(4 * totals["four_line"] / max(1, lines), 4)}


def probe(mid: Path | None, jobs: int) -> list[dict[str, Any]]:
    rel = e23._relative(mid) if mid else None
    with Pool(jobs) as pool:
        return pool.map(_probe_job, [(s, rel) for s in _seeds()["probe_seeds"]], chunksize=1)


def _style(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    s = e25._summary(episodes)
    return {"band_29_38": band_stats(episodes), "late_39": e29.late_stats(episodes),
            "p_reach_39": s["p_reach_39"], "share_lines_below_330": s["share_lines_below_330"],
            "score_39_plus_reached": s["score_39_plus_reached"]}


def probe_base(jobs: int) -> dict[str, Any]:
    """v39 alone on the probe seeds (once), its games stored for pairing."""
    path = OUT / "probe_base.json"
    if path.exists():
        return _load(path)
    episodes = probe(None, jobs)
    result = {"agent": "v39", "versions": runner._record_versions(),
              "summary": e25._summary(episodes), "style": _style(episodes),
              "episodes": episodes}
    _write(path, result)
    return result


def ranking(weights: Path, device: str) -> dict[str, Any]:
    """024's check on the "commit 29-38" decisions: all of them, and those below
    ``LATE_FROM`` lines (V29's own band)."""
    c = _config()
    model = e20.read_export(weights).to(device).eval()
    _, _, rows, _ = e21.load_data(RANK_DATA)
    scores = e24.rank_scores(model, rows, c["line_cap"], c["start_level"], device)
    below = rows[:, e21.LINES] < LATE_FROM
    return {"weights": e23._relative(weights),
            "commit 29-38": e21.table(rows, scores)["commit 29-38"],
            "commit 29-38 below 320": e21.table(rows[below], scores[below])["commit 29-38"]}


def v15_ranking(device: str) -> dict[str, Any]:
    path = OUT / "ranking_v15.json"
    if path.exists():
        return _load(path)
    result = ranking(_v15_path(), device)
    _write(path, result)
    return result


def play_round(index: int, jobs: int) -> dict[str, Any]:
    """Round ``index``: the agent with V29 of sweep ``index``, 1% exploration at
    ``EXPLORE_FROM``-``EXPLORE_TO`` lines; with V29's value against what each board's game
    went on to score and against the target's own definition (calibration)."""
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
    late = e24._values(e20.read_export(v39_path()).eval(), *args)
    actual = (d["final"] - d["score"]) / TETRIS_18
    # the target's own definition: points to the hand-over board plus V39 of it
    defined = actual.copy()
    for t in range(len(v) - 2, -1, -1):
        if d["game"][t + 1] == d["game"][t]:
            if d["lines"][t + 1] >= LATE_FROM:
                defined[t] = (d["score"][t + 1] - d["score"][t]) / TETRIS_18 + late[t + 1]
            elif d["lines"][t] < LATE_FROM:
                defined[t] = (d["score"][t + 1] - d["score"][t]) / TETRIS_18 + defined[t + 1]
    steps = {f"{lo}-{lo + 19}": [round(float(x[m].mean()), 3) for x in (v, actual, defined)]
             for lo in range(MID_FROM, LATE_FROM, 20)
             if (m := (d["lines"] >= lo) & (d["lines"] < lo + 20)).any()}
    result = {"round": index, "weights": rel, "explore": EXPLORE,
              "explore_lines": [EXPLORE_FROM, EXPLORE_TO],
              "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_defined_by_20_lines": steps} | summary
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
              "style": _style(episodes), "base_style": base["style"],
              "paired_vs_v39": e25._paired(episodes, base["episodes"]),
              "ranking": ranking(weights, device),
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"]} for e in episodes]}
    _write(path, result)
    return result


def _means(upto: int) -> list[float]:
    return [_load(OUT / f"probe{k}.json")["paired_vs_v39"]["total"]["score"]["mean"]
            for k in range(1, upto + 1)]


def should_stop(index: int) -> bool:
    if index >= MAX_SWEEPS:
        return True
    if index < MIN_SWEEPS:
        return False
    means = _means(index)
    return index - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def loop(jobs: int, device: str) -> int:
    """Sweep, probe and play the next round until the stop rule; resumable."""
    _require_clean()
    _require_wiring()
    if not _round_path(0).exists():
        raise ValueError("round 0 is missing: run round0 first")
    v15_ranking(device)
    index = 1
    while True:
        if not weights_path(index).exists():
            sweep(index, jobs, device)
        result = _probe_result(index, jobs, device)
        t = result["paired_vs_v39"]["total"]["score"]
        print(f"sweep {index}: probe {t['mean']:+,.0f} ({t['ci95_low']:+,.0f}, "
              f"{t['ci95_high']:+,.0f}); {result['style']}", flush=True)
        if should_stop(index):
            return index
        if not (OUT / f"round{index}.json").exists():
            play_round(index, jobs)
        index += 1


def choose(device: str = "cpu") -> dict[str, Any]:
    """Among the probed sweeps whose 29-38 ranking loss below 320 lines (odd rollouts) is
    no worse than v15's, the one with the highest paired probe mean (plan.md)."""
    key = "commit 29-38 below 320"
    v15 = v15_ranking(device)[key]["network_odd_loss"]
    rows = []
    for path in sorted(OUT.glob("probe[0-9]*.json")):
        r = _load(path)
        rows.append({"sweep": r["sweep"], "weights": r["weights"],
                     "probe_mean": r["paired_vs_v39"]["total"]["score"]["mean"],
                     "odd_loss_29_38": r["ranking"][key]["network_odd_loss"]})
    eligible = [r for r in rows if r["odd_loss_29_38"] <= v15]
    chosen = max(eligible, key=lambda r: r["probe_mean"], default=None)
    result = {"v15_odd_loss_29_38": v15, "sweeps": rows, "chosen": chosen}
    _write(OUT / "chosen.json", result)
    return result


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment030")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="mid network off / v15 reproduces v39's games")
    commands.add_parser("round0", help="v39 data games on round 0's seeds")
    looper = commands.add_parser("loop", help="sweep, probe, play until the stop rule")
    looper.add_argument("--device", default="cuda:0")
    chooser = commands.add_parser("choose", help="pick the V29 for the staged evaluation")
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
            print(f"stopped after sweep {loop(args.jobs, args.device)}")
        else:
            print(json.dumps(choose(args.device)["chosen"]))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
