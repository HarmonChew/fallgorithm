"""Run Experiment 036: the whole 20 Hz agent re-taught in one run (plan.md, predeclared.md).

    python -m block_stack_ai.experiment036 seeds
    python -m block_stack_ai.experiment036 check [--jobs N]
    python -m block_stack_ai.experiment036 earlier-checks [--jobs N]
    python -m block_stack_ai.experiment036 stage {1,2,3} [--jobs N] [--device D]
    python -m block_stack_ai.experiment036 choose
    python -m block_stack_ai.experiment036 status

The agent is 035b's record ``v29r20d`` (023's v15 below 230 lines, 033's sweep 6 V29@20 at
230-319, 031b's V39' from 320, 035's ``search_for_036``) at 20 Hz / 300 ms. Three stages,
each 030/033's recipe (backup2 k 4 targets under the previous sweep's network, lambda 0.95
returns, a third of the boards' children, warm start, 023's fit, own rounds of 200 games
with 0.5% exploration, a probe after every sweep), with every target of a sweep on one
value scale, also across the hand-over line:

1. V29@20 (230-319): the value at 320+ (hand-over boards and children) is
   max(0, c x V39' backup2), c from 034's frozen calibration;
2. V18@20 (below 230): the value at 230+ is stage 1's chosen V29@20's backup2;
3. V29@20 again, on stage 2's agent's games.

Before a sweep is fitted its targets pass two checks (``target_checks``); a sweep that
fails one is not fitted and its stage ends. Sweeps are probed on probe A (035's first 500
probe seeds), each stage's choice once on probe B; the probe measure is against all 2,500
stored ``v29r20d`` games (``measure``). ``choose`` names ``v36``; the final evaluation is
``experiment036eval``.
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
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch

from . import experiment013 as e13, experiment020 as e20, experiment023 as e23
from . import experiment025 as e25, experiment028 as e28, experiment029 as e29
from . import experiment030 as e30, experiment032 as e32
from . import experiment033 as e33, experiment034 as e34, experiment035 as e35
from . import experiment035eval as e35eval, native, runner

OUT = runner.PROJECT_ROOT / "experiments" / "036-20hz-full-reteach"
DATA = runner.PROJECT_ROOT / "runs" / "036-data"
RUNS = runner.PROJECT_ROOT / "runs" / "036"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
EARLIER = OUT / "checks_on_earlier_runs.json"
DECISION = OUT / "decision.json"
REGATE = OUT / "library_gate_20hz.json"
REPLAY_GAMES = 28
WIRING_EXPLORE = 0.05  # the wiring check's exploration (sure to change a game with deep3)
GAMES = OUT / "games"
SCHEMA = "fallgorithm.register.games/1"

MID_FROM, LATE_FROM = e33.MID_FROM, e33.LATE_FROM  # 230, 320
TAP_INTERVAL, TAP_INTERVAL_30 = e33.TAP_INTERVAL, 2
DEPTH, LAMBDA, CHILD_SHARE = 4, 0.95, 1 / 3
ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS, KEPT_ROUNDS = 400, 200, 40, 3
EXPLORE = 0.005
STOP_AFTER_FLAT = 3
FIRST_INDEX, END_INDEX = 15_200, 21_000  # 029's training list, indices 15,200-20,999
PROBE_HALF = 500
# stage: (min sweeps, max sweeps, first index of round 0, the band the stage teaches,
# exploration band of the own rounds)
STAGES: dict[int, dict[str, Any]] = {
    1: {"min": 5, "max": 8, "start": 15_200, "band": (MID_FROM, LATE_FROM),
        "explore": (e33.EXPLORE_FROM, e33.EXPLORE_TO)},
    2: {"min": 6, "max": 10, "start": 17_000, "band": (0, MID_FROM),
        "explore": (0, MID_FROM)},
    3: {"min": 5, "max": 8, "start": 19_200, "band": (MID_FROM, LATE_FROM),
        "explore": (e33.EXPLORE_FROM, e33.EXPLORE_TO)},
}
CHECK_LIMIT, REPORT_FROM = 2.0, 1.0  # Tetrises at level 18
STAGE2_STOP = -30_000
RESAMPLES, RNG_SEED = 10_000, 12
KEYS = e23.KEYS
TETRIS_18 = e33.TETRIS_18
NEVER = e28.NEVER
BASE = "v29r20d"

# the input networks (all committed before round 0)
V15 = "experiments/023-self-taught-value/value_sweep15.bin"         # below 230
V18_032 = "experiments/032-v18-search-taught/value_sweep9.bin"      # 032's V18 (30 Hz)
V29_BASE = e34.BASE_WEIGHTS                                         # 033's sweep 6 V29@20
V29_WARM = "experiments/034-v29-20hz-true-handover/value_sweep10.bin"  # stage 1's warm start
LATE = "experiments/031-v39-retuned-cap/value_sweep5.bin"           # 031b's V39'

_load = e13._load
_relative = e23._relative


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    e13._write(path, value)


def _path(rel: str) -> Path:
    return runner.PROJECT_ROOT / rel


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_inputs() -> None:
    """The named input networks are the ones the earlier experiments' code points at."""
    for rel, path in ((V15, e29._v15_path()), (LATE, e33.v39r_late_path()),
                      (V29_BASE, e34.base_path())):
        if _path(rel).resolve() != path.resolve():
            raise ValueError(f"{rel} is not {path}")


# ---------------------------------------------------------------- seeds

def make_seeds() -> dict[str, Any]:
    """029's training seeds 15,200-20,999 (035 used up to 15,199) by stage: round 0's 400,
    then rounds of 200 for every own round a later sweep can train on; the probe halves
    are 035's 1,000 probe seeds."""
    probe = e35._seeds()  # checks 035's reservation
    start = _load(e35.SEEDS)["used_slice"][1]
    if start != FIRST_INDEX:
        raise ValueError(f"035 used training seeds up to {start}, not {FIRST_INDEX}")
    train = e29._seeds()["training_seeds"]
    if len(train) < END_INDEX:
        raise ValueError(f"only {len(train)} training seeds, {END_INDEX} needed")
    stages, at = {}, FIRST_INDEX
    for stage, spec in STAGES.items():
        if spec["start"] != at:
            raise ValueError(f"stage {stage} starts at {spec['start']}, not {at}")
        rounds = spec["max"] - 1  # the last sweep's round would never be trained on
        end = at + ROUND0_SEEDS + ROUND_SEEDS * rounds
        stages[str(stage)] = {"slice": [at, end], "round0": train[at:at + ROUND0_SEEDS],
                              "rounds": train[at + ROUND0_SEEDS:end]}
        at = end
    if at != END_INDEX:
        raise ValueError(f"the stages end at {at}, not {END_INDEX}")
    result = {"selection": f"029's training seeds (029's seeds.json) from index {FIRST_INDEX} "
                           f"to {END_INDEX - 1} (029-035 used 0-{FIRST_INDEX - 1}): per stage "
                           f"round 0's {ROUND0_SEEDS}, then own rounds of {ROUND_SEEDS}; probe "
                           f"A and B are 035's 1,000 probe seeds (indices 14,200-14,699 and "
                           f"14,700-15,199)",
              "used_slice": [FIRST_INDEX, END_INDEX], "stages": stages,
              "probe": {"A": probe[:PROBE_HALF], "B": probe[PROBE_HALF:]}}
    _write(SEEDS, result)
    return result


@functools.lru_cache(maxsize=1)
def _seeds() -> dict[str, Any]:
    stored = _load(SEEDS) if SEEDS.exists() else make_seeds()
    if stored["used_slice"] != [FIRST_INDEX, END_INDEX]:
        raise ValueError(f"{SEEDS} is not the reserved slice {FIRST_INDEX}-{END_INDEX - 1}")
    return stored


def round_seeds(stage: int, index: int) -> list[int]:
    part = _seeds()["stages"][str(stage)]
    if index == 0:
        return part["round0"]
    if not 1 <= index < STAGES[stage]["max"]:
        raise ValueError(f"stage {stage} has no round {index}")
    start = ROUND_SEEDS * (index - 1)
    return part["rounds"][start:start + ROUND_SEEDS]


def probe_seeds(half: str) -> list[int]:
    return _seeds()["probe"][half]


# ---------------------------------------------------------------- the game

@functools.lru_cache(maxsize=1)
def search() -> dict[str, Any]:
    """035's ``search_for_036`` (checked by 035b's code against the setting 035 played)."""
    return e35eval.search()


@functools.lru_cache(maxsize=8)
def _bytes(rel: str) -> bytes:
    return _path(rel).read_bytes()


def _game(seed: int, early: str, mid: str, *, explore: float = 0.0,
          explore_lines: tuple[int, int] = (0, 0),
          dump: bool = False) -> tuple[dict[str, Any], bytes | None]:
    """``v29r20d``'s game with ``early`` below 230 lines and ``mid`` at 230-319 (paths
    relative to the project), V39' from 320, 035's search, the 20 Hz format; ``explore``
    is the chance of a random placement per piece at ``explore_lines``. The tap spacing of
    the format is checked on every game."""
    frozen, _ = e33._frozen()
    s = search()
    played, rows = native.late_hybrid_game(
        _bytes(early), frozen["game"], seed, late=_bytes(LATE), late_from_lines=LATE_FROM,
        mid=_bytes(mid), mid_from_lines=MID_FROM, commit_level=s["commit_level"],
        adjust_k=s["adjust_k"], adjust_max_level=s["adjust_max_level"],
        deep2_level=s["deep2_level"], deep2_k=s["deep2_k"], switch_level=NEVER,
        line_cap=frozen["line_cap"], frame_cap=frozen["frame_cap"],
        limits=e13._limits(frozen), params=native.params(frozen["params"]), explore=explore,
        explore_from_lines=explore_lines[0], explore_to_lines=explore_lines[1],
        explore_seed=seed, dump=dump, deep3=tuple(s["deep3"]))
    e33.check_tap_spacing(played["inputs"], TAP_INTERVAL)
    return played, rows


def band_rows(rows: bytes, stage: int) -> np.ndarray:
    """A game's dumped boards in the stage's band, up to and including its first board past
    the band (the hand-over board), in order."""
    return e32.early_rows(rows) if stage == 2 else e30._mid_rows(rows)


def _data_job(job: tuple[int, int, int, str, str, float]) -> dict[str, Any]:
    """One data game (029's ``_play_data`` job): ``(seed, source, stage, early, mid,
    explore)``."""
    seed, source, stage, early, mid, explore = job
    dumped: list[bytes] = []

    def play() -> dict[str, Any]:
        played, rows = _game(seed, early, mid, explore=explore,
                             explore_lines=STAGES[stage]["explore"], dump=True)
        dumped.append(rows)
        return played

    # every game replayed on the engine with its counters checked (predeclared.md's guards)
    episode = e33.checked_game(e33._frozen()[0], seed, play, agent=f"data-stage{stage}")
    return {"seed": seed, "source": source, "score": episode["result"]["score"],
            "lines": episode["result"]["lines"], "rows": band_rows(dumped[0], stage).tobytes()}


def _probe_job(job: tuple[int, str, str, str]) -> dict[str, Any]:
    """One checked game (register.checked_game and the 20 Hz tap-spacing check)."""
    seed, early, mid, label = job
    return e33.checked_game(e33._frozen()[0], seed,
                            lambda: _game(seed, early, mid)[0], agent=label)


# ---------------------------------------------------------------- guards

def library_record() -> dict[str, Any]:
    found = e35.library_record()
    if found["abi_version"] != 29:
        raise ValueError(f"native ABI {found['abi_version']}, 036 is predeclared on 29")
    return found


def _require_clean() -> None:
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _require_ready() -> None:
    """predeclared.md's guards before any data or probe game: a clean tree outside the
    experiment; the plan, the protocol, the seeds, the calibration and every input network
    committed; the wiring check matched on this very library."""
    _require_clean()
    _check_inputs()
    e34._require_committed(OUT / "plan.md", OUT / "predeclared.md", SEEDS, e34.CALIBRATION,
                           *(_path(rel) for rel in (V15, V18_032, V29_BASE, V29_WARM, LATE)))
    library = library_record()
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("library") != library:
        raise ValueError(f"{WIRING} is missing or not matched on this library: run check")
    first = _round_library(1, 0)
    if first is not None and first != library:
        found = _load(REGATE) if REGATE.exists() else {}
        if not found.get("matched") or found.get("library") != library:
            raise ValueError("the native library changed during the run: run check and "
                             "regate (the 20 Hz part of the gate) on it first")


def replay_20hz(stage: str, jobs: int) -> dict[str, Any]:
    """The first 28 stored v29r20d games of a set re-run by this module's game."""
    stored = list(reference()["by_seed"][stage].values())[:REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(_probe_job, [(e["seed"], V15, V29_BASE, BASE) for e in stored],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"games": len(stored), "matched": len(stored) - len(bad), "mismatched_seeds": bad}


def regate(jobs: int) -> dict[str, Any]:
    """predeclared.md: after a library change, the 20 Hz part of the gate (the first 28
    stored v29r20d development and held-out games) on the new library."""
    parts = {stage: replay_20hz(stage, jobs) for stage in ("development", "heldout")}
    result = {"experiment": OUT.name, "part_20hz_v29r20d": parts,
              "matched": all(p["matched"] == p["games"] for p in parts.values()),
              "library": library_record(), "versions": runner._record_versions()}
    _write(REGATE, result)
    return result


# ---------------------------------------------------------------- the base's stored games

@functools.lru_cache(maxsize=1)
def reference() -> dict[str, Any]:
    """035b's stored ``v29r20d`` games: on the probe seeds (035's ``combined``), on the
    development and held-out seeds. Their scores and points at levels 29 and up (the 2,500),
    and the probe games by seed (for the prefix guard and the paired figures)."""
    sets = {"probe": e35.games_path(e35.COMBINED), "development": e35eval.games_path(
        "development"), "heldout": e35eval.games_path("heldout")}
    want = {"probe": e35._seeds(), "development": e25._seeds("development"),
            "heldout": e25._seeds("heldout")}
    weights = _sha(_path(V29_BASE))
    episodes: dict[str, list[dict[str, Any]]] = {}
    for name, path in sets.items():
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            record = json.load(handle)
        if record["search"] != search() or record["weights_sha256"] != weights:
            raise ValueError(f"{path} was not played by v29r20d")
        if record["format"] != e33.format_of(e33._frozen()[0]):
            raise ValueError(f"{path} is not in the 20 Hz format")
        if [e["seed"] for e in record["episodes"]] != want[name]:
            raise ValueError(f"{path} does not cover its seeds in order")
        episodes[name] = record["episodes"]
    every = [e for name in sets for e in episodes[name]]
    return {"scores": np.array([e["result"]["score"] for e in every], np.float64),
            "late": np.array([late_points(e) for e in every], np.float64),
            "by_seed": {name: {e["seed"]: e for e in found} for name, found in episodes.items()}}


def late_points(episode: dict[str, Any]) -> int:
    """Points scored at levels 29 and up."""
    bands = episode["stats"]["bands"]
    return bands.get("29-38", 0) + bands.get("39+", 0)


def prefix_check(mine: list[dict[str, Any]], stored: dict[int, dict[str, Any]]) -> list[int]:
    """The seeds whose inputs differ from the stored ``v29r20d`` game before it first has
    230 lines (the whole game if it never does)."""
    frozen = e33._frozen()[0]
    return [e["seed"] for e in mine
            if not e34.prefix_matches(frozen, e["seed"],
                                      base64.b64decode(stored[e["seed"]]["inputs"]),
                                      base64.b64decode(e["inputs"]))]


# ---------------------------------------------------------------- the probe measure

def bootstrap_difference(mine: np.ndarray, base: np.ndarray, resamples: int = RESAMPLES,
                         seed: int = RNG_SEED) -> dict[str, float]:
    """Mean of ``mine`` minus mean of ``base`` with a 95% percentile interval, each sample
    resampled on its own."""
    mine, base = np.asarray(mine, np.float64), np.asarray(base, np.float64)
    rng = np.random.default_rng(seed)
    boot = np.empty(resamples)
    for start in range(0, resamples, 1000):  # bounded memory
        n = min(1000, resamples - start)
        boot[start:start + n] = (mine[rng.integers(0, len(mine), (n, len(mine)))].mean(1) -
                                 base[rng.integers(0, len(base), (n, len(base)))].mean(1))
    boot.sort()
    return {"mean": float(mine.mean() - base.mean()),
            "ci95_low": float(boot[int(0.025 * resamples)]),
            "ci95_high": float(boot[int(0.975 * resamples) - 1]),
            "resamples": resamples, "rng_seed": seed}


def measure(episodes: list[dict[str, Any]], v15_below: bool) -> dict[str, Any]:
    """predeclared.md's probe measure: against all 2,500 stored ``v29r20d`` games, the mean
    final score; for an agent with v15 below 230 (it plays ``v29r20d``'s own game there),
    the mean points at levels 29 and up."""
    ref = reference()
    if v15_below:
        mine, base, kind = [late_points(e) for e in episodes], ref["late"], "points_29_up"
    else:
        mine, base, kind = [e["result"]["score"] for e in episodes], ref["scores"], "score"
    return {"kind": kind, "base_games": int(len(base)), "base_mean": float(base.mean()),
            "mine_mean": float(np.mean(mine))} | bootstrap_difference(np.array(mine), base)


# ---------------------------------------------------------------- the networks of a stage

def stage_dir(stage: int) -> Path:
    return OUT / f"stage{stage}"


def warm_start_2() -> str:
    """Stage 2's warm start: the better of v15 and 032's V18 on probe A in the stage 2
    agent (``warm_start.json``)."""
    path = stage_dir(2) / "warm_start.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: stage 2 has not probed its candidates")
    return _load(path)["chosen"]


def weights_rel(stage: int, sweep: int) -> str:
    """The V29@20 (stages 1, 3) or V18@20 (stage 2) of a sweep; sweep 0 is the warm start."""
    if sweep == 0:
        if stage == 1:
            return V29_WARM
        return warm_start_2() if stage == 2 else choice(1)["weights"]
    return _relative(stage_dir(stage) / f"value_sweep{sweep}.bin")


def agent(stage: int, sweep: int) -> tuple[str, str]:
    """(below 230, 230-319) of the stage's agent with the sweep's network."""
    if stage == 1:
        return V15, weights_rel(1, sweep)
    if stage == 2:
        return weights_rel(2, sweep), choice(1)["weights"]
    return choice(2)["weights"], weights_rel(3, sweep)


def handover_value(stage: int, jobs: int,
                   tap_interval: int = TAP_INTERVAL) -> Callable[[np.ndarray], np.ndarray]:
    """The one function that values every board past the stage's band, for the hand-over
    boards' returns and the children alike: stages 1 and 3 max(0, c x V39' backup2), stage
    2 the backup2 of stage 1's chosen V29@20."""
    if stage == 2:
        mid = _path(choice(1)["weights"])
        return lambda rows: targets(mid, rows, DEPTH, jobs, tap_interval=tap_interval)[0]
    c = e34.scale()
    return lambda rows: e34.scaled(
        targets(_path(LATE), rows, DEPTH, jobs, tap_interval=tap_interval)[0], c)


# ---------------------------------------------------------------- targets

def _target_job(job: tuple[bytes, bytes, int, bool, int]) -> tuple[np.ndarray, bytes | None]:
    """029's / 033's target job with the tap interval as an argument."""
    weights, rows, depth, children, tap_interval = job
    c = e33._config()
    args = dict(line_cap=c["line_cap"], start_level=c["start_level"],
                double_killscreen=c["double_killscreen"], tap_interval=tap_interval)
    kids = None
    if depth == 1 or children:
        values, kids = native.backup_values(weights, rows, children=children, **args)
    if depth > 1:
        values = native.backup2_values(weights, rows, k=depth, **args)
    return np.array(values) / TETRIS_18, kids


def targets(weights: Path, rows: np.ndarray, depth: int, jobs: int, children: bool = False,
            tap_interval: int = TAP_INTERVAL) -> tuple[np.ndarray, np.ndarray | None]:
    """Each row's backup (depth 1) or backup2 (depth k) under ``weights``, in Tetrises at
    level 18, and with ``children`` the next boards of each (those with a placement)."""
    if len(rows) == 0:
        return np.zeros(0), (np.zeros((0, native.DUMP_STRIDE), np.int32) if children else None)
    data = weights.read_bytes()
    chunks = np.array_split(rows, max(1, min(len(rows), jobs * 8)))
    with Pool(jobs) as pool:
        found = pool.map(_target_job, [(data, np.ascontiguousarray(c).tobytes(), depth,
                                        children, tap_interval) for c in chunks], chunksize=1)
    values = np.concatenate([v for v, _ in found])
    if not children:
        return values, None
    kids = np.concatenate([np.frombuffer(k, np.int32).reshape(-1, native.DUMP_STRIDE)
                           for _, k in found])
    return values, kids[kids[:, native.WIDTH] >= 0]


def build_targets(parts: list[dict[str, np.ndarray]], previous: Path, split: int,
                  handover: Callable[[np.ndarray], np.ndarray], jobs: int,
                  rng: np.random.Generator,
                  tap_interval: int = TAP_INTERVAL) -> dict[str, np.ndarray]:
    """A sweep's training rows and targets. Each part's boards below ``split`` (the played
    boards) get lambda-returns of backup2 under ``previous`` that end at the game's first
    board at ``split`` or more with ``handover`` of it; the children of a ``CHILD_SHARE`` of
    the played boards get backup2 under ``previous`` below ``split`` and ``handover`` at
    ``split`` or more. No row has a game outcome as its target. ``kind``: 0 played, 1 child
    below ``split``, 2 child at ``split`` or more; ``rest``: the played boards' actual rest
    of game (NaN for children); ``handover_*``: the hand-over boards' lines, value and
    actual rest of game."""
    boards, goals, kinds, rests, child_rows = [], [], [], [], []
    hand_lines, hand_value, hand_rest = [], [], []
    for part in parts:
        rows = e23._rows(part)
        below = part["lines"] < split
        backup = np.zeros(len(rows))
        backup[below], _ = targets(previous, rows[below], DEPTH, jobs,
                                   tap_interval=tap_interval)
        backup[~below] = handover(rows[~below]) if (~below).any() else np.zeros(0)
        rest = (part["final"].astype(np.float64) - part["score"]) / TETRIS_18
        boards.append({key: part[key][below] for key in KEYS})
        goals.append(e30.handover_returns(backup, part, LAMBDA, late_from=split))
        kinds.append(np.zeros(int(below.sum()), np.int8))
        rests.append(rest[below])
        hand_lines.append(part["lines"][~below])
        hand_value.append(backup[~below])
        hand_rest.append(rest[~below])
        pick = rng.random(int(below.sum())) < CHILD_SHARE
        _, kids = targets(previous, rows[below][pick], 1, jobs, children=True,
                          tap_interval=tap_interval)
        child_rows.append(kids)
    kids = np.concatenate(child_rows)
    low = kids[:, native.WIDTH] < split
    for subset, kind in ((kids[low], 1), (kids[~low], 2)):
        if kind == 1:
            values, _ = targets(previous, subset, DEPTH, jobs, tap_interval=tap_interval)
        else:
            values = handover(subset) if len(subset) else np.zeros(0)
        boards.append(e23._boards(subset))
        goals.append(values)
        kinds.append(np.full(len(subset), kind, np.int8))
        rests.append(np.full(len(subset), np.nan))
    return {key: np.concatenate([b[key] for b in boards]) for key in KEYS} | {
        "goal": np.concatenate(goals), "kind": np.concatenate(kinds),
        "rest": np.concatenate(rests), "handover_lines": np.concatenate(hand_lines),
        "handover_value": np.concatenate(hand_value),
        "handover_rest": np.concatenate(hand_rest)}


# ---------------------------------------------------------------- the checks

def _step_mean(lines: np.ndarray, values: np.ndarray, lo: int) -> float | None:
    m = (lines >= lo) & (lines < lo + 10)
    return float(values[m].mean()) if m.any() else None


def target_checks(stage: int, played_lines: np.ndarray, played: np.ndarray,
                  child_lines: np.ndarray, children: np.ndarray,
                  handover: np.ndarray) -> dict[str, Any]:
    """predeclared.md's two checks on a sweep's targets (Tetrises at level 18), by 10-line
    step of the taught band; children are binned by their own line count, a step with no
    rows of either kind fails.

    * gap: the children's mean target minus the played boards' is at most +2.0 at every
      step;
    * cliff: the children's drop from the band's last step to the first step past it,
      minus the played boards' drop (their mean target at the last step minus the mean
      hand-over value), within 2.0 (stages 1 and 3) or at most +2.0 (stage 2).
    """
    lo, hi = STAGES[stage]["band"]
    table, gaps = {}, []
    for step in range(lo, hi, 10):
        p, c = _step_mean(played_lines, played, step), _step_mean(child_lines, children, step)
        gap = None if p is None or c is None else c - p
        gaps.append(gap)
        table[f"{step}-{step + 9}"] = [None if x is None else round(x, 3) for x in (p, c, gap)]
    last, past = hi - 10, hi
    p_last = _step_mean(played_lines, played, last)
    c_last, c_past = (_step_mean(child_lines, children, s) for s in (last, past))
    h = float(np.mean(handover)) if len(handover) else None
    child_drop = None if c_last is None or c_past is None else c_last - c_past
    played_drop = None if p_last is None or h is None else p_last - h
    excess = None if child_drop is None or played_drop is None else child_drop - played_drop
    gap_ok = all(g is not None and g <= CHECK_LIMIT for g in gaps)
    cliff_ok = excess is not None and (excess <= CHECK_LIMIT if stage == 2 else
                                       abs(excess) <= CHECK_LIMIT)
    found = [g for g in gaps if g is not None]
    return {"unit": "Tetrises at level 18 (22,800 points)",
            "gap_by_10_lines_played_children_gap": table,
            "worst_gap": round(max(found), 3) if found else None,
            "most_negative_gap": round(min(found), 3) if found else None,
            "steps_from_plus_1": [k for k, v in table.items()
                                  if v[2] is not None and v[2] > REPORT_FROM],
            "gap_ok": bool(gap_ok),
            "cliff": {"from_step": f"{last}-{last + 9}", "to_step": f"{past}-{past + 9}",
                      "children_drop": None if child_drop is None else round(child_drop, 3),
                      "played_drop": None if played_drop is None else round(played_drop, 3),
                      "mean_handover_value": None if h is None else round(h, 3),
                      "handover_boards": int(len(handover)),
                      "excess": None if excess is None else round(excess, 3),
                      "two_sided": stage != 2},
            "cliff_ok": bool(cliff_ok), "passed": bool(gap_ok and cliff_ok),
            "limit": CHECK_LIMIT}


def checks_of(stage: int, built: dict[str, np.ndarray]) -> dict[str, Any]:
    kind, lines, goal = built["kind"], built["lines"].astype(np.int64), built["goal"]
    return target_checks(stage, lines[kind == 0], goal[kind == 0], lines[kind > 0],
                         goal[kind > 0], built["handover_value"])


# ---------------------------------------------------------------- rounds

def _round_path(stage: int, index: int) -> Path:
    return DATA / f"stage{stage}" / f"round{index}.npz"


def round_work(stage: int, index: int) -> list[tuple[int, int, int, str, str, float]]:
    """The data games of a round: round 0 without exploration (stage 1: the first 200
    seeds with v15 below 230, the last 200 with 032's V18; stage 2: the stage 1 agent with
    stage 2's warm start; stage 3: the stage 2 agent), an own round with the sweep's
    network and 0.5% exploration."""
    seeds = round_seeds(stage, index)
    if index == 0 and stage == 1:
        half = ROUND0_SEEDS // 2
        return [(s, 0, 1, V15, V29_WARM, 0.0) for s in seeds[:half]] + \
            [(s, 1, 1, V18_032, V29_WARM, 0.0) for s in seeds[half:]]
    early, mid = agent(stage, index)
    return [(s, 0, stage, early, mid, 0.0 if index == 0 else EXPLORE) for s in seeds]


def _library_path(stage: int, index: int) -> Path:
    return DATA / f"stage{stage}" / f"round{index}.library.json"


def _round_library(stage: int, index: int) -> dict[str, Any] | None:
    """The library a round's games were played on (None before it is played)."""
    path = _library_path(stage, index)
    return _load(path) if path.exists() else None


def play_data(path: Path, work: list[tuple], stage: int, jobs: int) -> dict[str, Any]:
    """029's ``_play_data`` with this module's data job (the boards of the stage's band and
    its hand-over board, whole games in work order), and where the games ended."""
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
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.stem + ".partial.npz")
    np.savez(partial, **e23._boards(rows), score=rows[:, native.WIDTH + 1].astype(np.int64),
             final=info[:, 3].astype(np.int64), game=info[:, 0].astype(np.int32),
             source=info[:, 1].astype(np.int8), seed=info[:, 2].astype(np.int32))
    partial.replace(path)
    lines = np.array([g["lines"] for g in found])
    lo, hi = STAGES[stage]["band"]
    deaths = {f"{s}-{s + 9}": int(((lines >= s) & (lines < s + 10)).sum())
              for s in range(lo, hi + 10, 10)}
    by_source = {str(s): {"games": int(sum(g["source"] == s for g in found)),
                          "mean_score": round(float(np.mean([g["score"] for g in found
                                                             if g["source"] == s])), 1)}
                 for s in sorted({g["source"] for g in found})}
    return {"games": len(found), "boards": int(len(rows)),
            "mean_score": round(float(np.mean([g["score"] for g in found])), 1),
            "mean_lines": round(float(lines.mean()), 1),
            "p_reach_230": round(float((lines >= MID_FROM).mean()), 3),
            "p_reach_320": round(float((lines >= LATE_FROM).mean()), 3),
            "line_cap_share": round(float((lines >= 430).mean()), 3),
            "deaths_by_10_lines_in_band": deaths, "by_source": by_source}


def _handover_summary(path: Path, stage: int) -> dict[str, Any]:
    d = e23._load_npz(path)
    split = STAGES[stage]["band"][1]
    feat = d["features"][d["lines"] >= split]
    return {"handover_boards": {"games": int(len(feat)), "at_lines": split,
                                "mean_max_height": e33._mean(feat[:, 5]),
                                "mean_aggregate_height": e33._mean(feat[:, 3]),
                                "mean_holes": e33._mean(feat[:, 0])}}


def _values(weights: Path, d: dict[str, np.ndarray]) -> np.ndarray:
    return e34._values(weights, d)


def calibration(stage: int, weights: Path, d: dict[str, np.ndarray]) -> dict[str, Any]:
    """The taught network's value against the actual rest of game by 10-line step of its
    band (and the first step past it)."""
    lo, hi = STAGES[stage]["band"]
    actual = (d["final"] - d["score"]) / TETRIS_18
    return e34.by_steps(d["lines"], _values(weights, d), actual, start=lo, stop=hi + 10)


def play_round(stage: int, index: int, jobs: int) -> dict[str, Any]:
    """Round ``index`` of the stage, its summary, the taught network's value against the
    actual rest of game and (stages 1 and 3) the frozen scale's drift on its hand-over
    boards."""
    record = stage_dir(stage) / f"round{index}.json"
    if record.exists():
        return _load(record)
    path = _round_path(stage, index)
    work = round_work(stage, index)
    tick = time.time()
    if path.exists():  # played, but the summary below was not written: keep the games
        summary = {"resumed": "the games' summary was lost in a crash"}
    else:
        _require_ready()
        library = library_record()
        summary = play_data(path, work, stage, jobs)
        _write(_library_path(stage, index), library)
    d = e23._load_npz(path)
    taught = _path(work[0][4] if stage != 2 else work[0][3])
    result = {"experiment": OUT.name, "stage": stage, "round": index, "seeds": len(work),
              "agents": sorted({(w[1], w[3], w[4]) for w in work}),
              "explore": work[0][5], "explore_lines": list(STAGES[stage]["explore"]),
              "format": e33.format_of(e33._frozen()[0]), "search": search(),
              "library": _round_library(stage, index), "versions": runner._record_versions(),
              "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_by_10_lines": calibration(stage, taught, d)} | \
        summary | _handover_summary(path, stage)
    if stage != 2:
        result["scale_drift"] = e34.drift(d, jobs)
    _write(record, result)
    return result


# ---------------------------------------------------------------- sweeps

def training_parts(stage: int, index: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    """Round 0 without its first ``CHECK_SEEDS`` seeds and the last ``KEPT_ROUNDS`` own
    rounds before sweep ``index`` (whole games, hand-over boards included); round 0's check
    boards (those seeds' boards in the band, reported only)."""
    zero = e23._load_npz(_round_path(stage, 0))
    held = np.isin(zero["seed"], np.array(round_seeds(stage, 0)[:CHECK_SEEDS]))
    parts = [e33._split(zero, ~held)]
    for k in range(max(1, index - KEPT_ROUNDS), index):
        parts.append(e23._load_npz(_round_path(stage, k)))
    split = STAGES[stage]["band"][1]
    return parts, e33._split(zero, held & (zero["lines"] < split))


def cache_key(stage: int, index: int, previous: Path) -> str:
    rounds = [0] + list(range(max(1, index - KEPT_ROUNDS), index))
    body = {"stage": stage, "lambda": LAMBDA, "depth": DEPTH, "child_share": CHILD_SHARE,
            "previous": _sha(previous), "tap_interval": TAP_INTERVAL,
            "rounds": {k: _sha(_round_path(stage, k)) for k in rounds}}
    if stage == 2:
        body["handover"] = {"mid_backup2": _sha(_path(choice(1)["weights"]))}
    else:
        body["handover"] = {"late": _sha(_path(LATE)), "calibration": e34.calibration()["sha256"]}
    return json.dumps(body, sort_keys=True)


def _sweep_record(stage: int, index: int) -> Path:
    return stage_dir(stage) / f"sweep{index}.json"


def sweep(stage: int, index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index`` of the stage: targets under the previous sweep's network, the two
    checks, and only if both pass the fit (warm-started from the previous network)."""
    out_path = _path(weights_rel(stage, index))
    record = _sweep_record(stage, index)
    if out_path.exists() or (record.exists() and not _load(record)["fitted"]):
        return _load(record)
    previous = _path(weights_rel(stage, index - 1))
    split = STAGES[stage]["band"][1]
    tick = time.time()
    parts, check = training_parts(stage, index)
    cache = DATA / f"stage{stage}" / f"targets{index}.npz"
    key = cache_key(stage, index, previous)
    if cache.exists():
        built = e23._load_npz(cache)
        if str(built.pop("key")) != key:
            raise ValueError(f"{cache} was made with other settings or data: remove it")
        check_targets = built.pop("check_targets")
    else:
        built = build_targets(parts, previous, split, handover_value(stage, jobs), jobs,
                              np.random.default_rng(36_000 + 100 * stage + index))
        check_targets, _ = targets(previous, e23._rows(check), DEPTH, jobs)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partial = cache.with_name(cache.stem + ".partial.npz")
        np.savez(partial, **built, check_targets=check_targets, key=np.array(key))
        partial.replace(cache)
    target_seconds = time.time() - tick
    checks = checks_of(stage, built)
    kind = built["kind"]
    played = kind == 0
    result: dict[str, Any] = {
        "experiment": OUT.name, "stage": stage, "sweep": index,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": e33.format_of(e33._frozen()[0]), "library": library_record(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": _relative(previous), "sha256": _sha(previous)},
        "handover": json.loads(key)["handover"], "depth": DEPTH, "lambda": LAMBDA,
        "boards": {"played": int(played.sum()), "children_in_band": int((kind == 1).sum()),
                   "children_past_band": int((kind == 2).sum()),
                   "handover_boards": int(len(built["handover_value"])),
                   "check": int(len(check_targets))},
        "mean_target_and_actual_by_10_lines": e34.by_steps(
            built["lines"][played], built["goal"][played], built["rest"][played],
            start=STAGES[stage]["band"][0], stop=split),
        "handover_value_and_actual": {
            "mean_value": e34._mean(built["handover_value"]),
            "mean_actual": e34._mean(built["handover_rest"])},
        "target_seconds": round(target_seconds, 1),
        "unit": "Tetrises at level 18 (22,800 points)", "checks": checks,
        "fitted": checks["passed"]}
    if not checks["passed"]:
        _write(record, result | {"weights": None})
        return _load(record)
    settings = _load(e23.CONFIG)["fit"]
    cap = e33._config()["line_cap"]
    torch.manual_seed(settings["torch_seed"] + 100 * stage + index)
    model = e20.read_export(previous).to(device)
    t = e23._tensors({k: built[k] for k in KEYS}, built["goal"], device)
    ck = e23._tensors({k: check[k] for k in KEYS}, check_targets, device)
    before = e23._predict(model, ck, cap).cpu().numpy()
    log = e23._fit(model, t, settings, cap)
    after = e23._predict(model, ck, cap).cpu().numpy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = out_path.with_name(out_path.name + ".partial")
    sha = e20.export(model, partial)
    rms = lambda a: round(float(np.sqrt(((a - check_targets) ** 2).mean())), 4)  # noqa: E731
    result |= {"weights": {"path": _relative(out_path), "sha256": sha}, "settings": settings,
               "torch_seed": settings["torch_seed"] + 100 * stage + index,
               "training_log": log,
               "check_boards_diagnostic": {"old_value_minus_target_rms": rms(before),
                                           "new_value_minus_target_rms": rms(after)}}
    _write(record, result)  # the record before the weights: resumable
    partial.replace(out_path)
    return result


# ---------------------------------------------------------------- probes

def resume(partial: Path, header: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """025's ``_resume``; a partial file from another run (a commit since it started, or
    another build) is moved aside to ``.stale`` and the step is replayed (predeclared.md)."""
    try:
        return e25._resume(partial, header)
    except ValueError:
        stale = partial.with_name(partial.name + ".stale")
        partial.replace(stale)
        print(f"{partial.name} is from another run: moved to {stale.name}, replaying",
              flush=True)
        return e25._resume(partial, header)


def _probe_name(stage: int, label: str, half: str) -> str:
    return f"stage{stage}-{label}-{half}"


def play_probe(stage: int, label: str, early: str, mid: str, half: str,
               jobs: int) -> list[dict[str, Any]]:
    """The agent (``early`` below 230, ``mid`` at 230-319) on a probe half, resuming from
    its partial file; an agent with v15 below 230 must play the stored ``v29r20d`` game's
    inputs before 230 lines on every seed (stops the step otherwise). The games are kept in
    ``runs/036/games``."""
    name = _probe_name(stage, label, half)
    target = RUNS / "games" / f"{name}.json.gz"
    seeds = probe_seeds(half)
    if target.exists():
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            record = json.load(handle)
        if [e["seed"] for e in record["episodes"]] != seeds or \
                record["agent"] != {"early": early, "mid": mid}:
            raise ValueError(f"{target} is not this agent on probe {half}")
        return record["episodes"]
    _require_ready()
    versions, library = runner._record_versions(), library_record()
    agent_record = {"early": early, "mid": mid}
    header = {"header": {"name": name, "agent": agent_record, "search": search(),
                         "shas": [_sha(_path(early)), _sha(_path(mid))],
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "library": library, "versions": versions}}
    (RUNS / "partial").mkdir(parents=True, exist_ok=True)
    partial = RUNS / "partial" / f"{name}.partial.jsonl"
    done = resume(partial, header)
    guard = early == V15
    stored = reference()["by_seed"]["probe"]
    todo = [(s, early, mid, name) for s in seeds if s not in done]
    print(f"{name}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(_probe_job, todo, chunksize=1):
            if guard and prefix_check([episode], stored):
                raise ValueError(f"{name}: seed {episode['seed']} differs from v29r20d before "
                                 f"230 lines: stopped (the games stay in {partial})")
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            if len(done) % 50 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{name} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "name": name, "agent": agent_record,
              "shas": header["header"]["shas"], "search": search(),
              "format": e33.format_of(e33._frozen()[0]), "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[s] for s in seeds]}
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".partial")
    with gzip.open(staged, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    staged.replace(target)
    partial.unlink()
    return record["episodes"]


def _probe_record(stage: int, label: str, half: str) -> Path:
    return stage_dir(stage) / f"probe{half}_{label}.json"


def probe(stage: int, label: str, early: str, mid: str, half: str, jobs: int) -> dict[str, Any]:
    """A probe's record: the measure (with its interval), the seed-paired difference
    against the stored ``v29r20d`` games (reported only), the reported figures and the
    games' per-seed outcomes."""
    path = _probe_record(stage, label, half)
    if path.exists():
        return _load(path)
    episodes = play_probe(stage, label, early, mid, half, jobs)
    stored = reference()["by_seed"]["probe"]
    base = [stored[e["seed"]] for e in episodes]
    result = {"experiment": OUT.name, "stage": stage, "label": label, "half": half,
              "agent": {"early": early, "mid": mid,
                        "shas": [_sha(_path(early)), _sha(_path(mid))]},
              "measure": measure(episodes, early == V15),
              "paired_vs_v29r20d_same_seeds_reported_only": e25._paired(episodes, base),
              "style": e35.style(episodes), "base_style_same_seeds": e35.style(base),
              "prefix_guard": "every seed matched" if early == V15 else "not applicable",
              "library": _gz_record(stage, label, half)["library"],
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"], "bands": e["stats"]["bands"]}
                        for e in episodes]}
    _write(path, result)
    return result


def _gz_record(stage: int, label: str, half: str) -> dict[str, Any]:
    target = RUNS / "games" / f"{_probe_name(stage, label, half)}.json.gz"
    with gzip.open(target, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def probe_measure(stage: int, label: str, half: str = "A") -> float:
    return float(_load(_probe_record(stage, label, half))["measure"]["mean"])


# ---------------------------------------------------------------- the stop rule, the choice

def should_stop(stage: int, means: list[float]) -> bool:
    """``means``: the probe A measures of sweeps 1 to n. At the stage's maximum, stop; from
    its minimum on, stop after ``STOP_AFTER_FLAT`` sweeps without a new best."""
    n = len(means)
    if n >= STAGES[stage]["max"]:
        return True
    if n < STAGES[stage]["min"]:
        return False
    return n - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def pick(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The row with the highest measure (the first of equals), None if there is none."""
    return max(rows, key=lambda r: r["measure"], default=None)


def choice(stage: int) -> dict[str, Any]:
    """The stage's chosen sweep (``choice.json``)."""
    path = stage_dir(stage) / "choice.json"
    if not path.exists():
        raise ValueError(f"{path} is missing: stage {stage} has not chosen")
    found = _load(path)
    if found["chosen"] is None:
        raise ValueError(f"stage {stage} has no choice")
    return found["chosen"]


def stage_choice(stage: int) -> dict[str, Any]:
    """The probed sweep (1 or later, all passed the checks) with the highest probe A
    measure."""
    rows = []
    for k in range(1, STAGES[stage]["max"] + 1):
        if _probe_record(stage, f"sweep{k}", "A").exists():
            rows.append({"sweep": k, "weights": weights_rel(stage, k),
                         "measure": probe_measure(stage, f"sweep{k}")})
    return {"rule": "the sweep (1 or later) with the highest probe A measure among those "
                    "that passed the checks (predeclared.md)",
            "sweeps": rows, "chosen": pick(rows)}


def stage_rule(stage: int, b: dict[str, Any] | None, chosen: dict[str, Any] | None,
               a_measure: float | None) -> dict[str, Any]:
    """predeclared.md's rules between the stages: stage 1 goes on only if its choice's
    probe A measure is above 0; stage 2 is stopped if its choice's probe B measure is below
    -30,000 with the interval's upper end under 0; a stage with no sweep that passed the
    checks has no choice (and stops the run at stages 1 and 2)."""
    if chosen is None:
        return {"go": False, "why": "no sweep passed the checks"}
    if stage == 1 and not a_measure > 0:
        return {"go": False, "why": f"the choice's probe A measure {a_measure:+,.0f} is not "
                                    "above 0 (the owner's go / no-go)"}
    if stage == 2 and b is not None and b["mean"] < STAGE2_STOP and b["ci95_high"] < 0:
        return {"go": False, "why": f"probe B measure {b['mean']:+,.0f} below "
                                    f"{STAGE2_STOP:+,} with the interval under 0"}
    return {"go": True}


def choose_v36(candidates: dict[int, float | None]) -> dict[str, Any]:
    """``candidates``: the stage choices' probe B measures (None: stopped or no choice).
    ``v36`` is the one with the highest; there is a final evaluation only if it is above
    0."""
    rows = [{"stage": s, "measure": m} for s, m in sorted(candidates.items()) if m is not None]
    best = pick(rows)
    if best is None or not best["measure"] > 0:
        return {"v36": None, "final_evaluation": False, "candidates": rows}
    return {"v36": best["stage"], "final_evaluation": True, "candidates": rows,
            "probe_b_measure_selected": best["measure"]}


# ---------------------------------------------------------------- the stages

def _write_choice(stage: int, body: dict[str, Any]) -> dict[str, Any]:
    _write(stage_dir(stage) / "choice.json", body)
    return body


def _stage_done(stage: int) -> dict[str, Any] | None:
    path = stage_dir(stage) / "choice.json"
    return _load(path) if path.exists() else None


def _require_go(stage: int) -> None:
    found = _stage_done(stage)
    if found is None or not found["rule"]["go"]:
        raise ValueError(f"stage {stage} did not go on: no stage {stage + 1}")


def _keep_games(stage: int, label: str, half: str) -> None:
    """Copy a stage choice's probe B games into the experiment (``games/``)."""
    source = RUNS / "games" / f"{_probe_name(stage, label, half)}.json.gz"
    GAMES.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, GAMES / source.name)


def stage2_warm_start(jobs: int) -> dict[str, Any]:
    """Stage 2's candidates on probe A in the stage 2 agent: v15 (its games are stage 1's
    choice's probe A games) and 032's V18 (played); the higher mean score on probe A (the
    same seeds, so also the seed-paired mean) is the warm start, v15 on a tie."""
    path = stage_dir(2) / "warm_start.json"
    if path.exists():
        return _load(path)
    one = choice(1)
    v15 = _load(_probe_record(1, f"sweep{one['sweep']}", "A"))
    v18 = probe(2, "sweep0_v18_032", V18_032, one["weights"], "A", jobs)
    score = lambda r: float(np.mean([g["score"] for g in r["games"]]))  # noqa: E731
    v15_score, v18_score = score(v15), score(v18)
    result = {"rule": "the higher mean score on probe A of the two in the stage 2 agent, v15 "
                      "on a tie (predeclared.md)",
              "candidates": {V15: {"mean_score": v15_score, "probe": _relative(
                  _probe_record(1, f"sweep{one['sweep']}", "A")),
                  "measure_total_score": v15_score - float(reference()["scores"].mean())},
                  V18_032: {"mean_score": v18_score,
                            "probe": _relative(_probe_record(2, "sweep0_v18_032", "A")),
                            "measure_total_score": v18["measure"]["mean"]}},
              "v18_minus_v15_paired_mean": v18_score - v15_score,
              "chosen": V18_032 if v18_score > v15_score else V15}
    _write(path, result)
    return result


def commit_step(message: str, push: bool = False) -> None:
    """Commit the experiment's directory (and push), if a step changed it."""
    rel = str(OUT.relative_to(runner.PROJECT_ROOT))
    changed = subprocess.run(["git", "status", "--porcelain", "--", rel],
                             cwd=runner.PROJECT_ROOT, capture_output=True, text=True,
                             check=True).stdout
    if not changed.strip():
        return
    subprocess.run(["git", "add", "-A", "--", rel], cwd=runner.PROJECT_ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=runner.PROJECT_ROOT, check=True)
    if push and subprocess.run(["git", "push", "-q", "origin", "HEAD"],
                               cwd=runner.PROJECT_ROOT).returncode:
        print("push failed (continuing)", flush=True)


def run_stage(stage: int, jobs: int, device: str,
              after: Callable[[str], None] = lambda message: None) -> dict[str, Any]:
    """One stage, resumable: round 0, sweep 0's probe, the sweeps (each: targets, checks,
    fit, probe A, the stop rule, the next own round), the choice, its probe B and the
    stage's rule. ``after`` is called with a description after every step."""
    done = _stage_done(stage)
    if done is not None:
        return done
    if stage > 1:
        _require_go(stage - 1)
    _require_ready()
    name = f"Experiment 036 stage {stage}"
    if stage == 2:
        found = stage2_warm_start(jobs)
        after(f"{name}: warm start {found['chosen']} (probe A of both candidates)")
    play_round(stage, 0, jobs)
    after(f"{name}: round 0")
    if stage == 1:
        probe(1, "sweep0", *agent(1, 0), "A", jobs)
        after(f"{name}: sweep 0 (the warm start) on probe A")
    means: list[float] = []
    index = 1
    while True:
        result = sweep(stage, index, jobs, device)
        if not result["fitted"]:
            print(f"stage {stage} sweep {index}: checks failed, the stage ends", flush=True)
            after(f"{name} sweep {index}: its targets failed the checks, not fitted")
            break
        after(f"{name} sweep {index}: targets, checks and fit")
        found = probe(stage, f"sweep{index}", *agent(stage, index), "A", jobs)
        means.append(found["measure"]["mean"])
        m = found["measure"]
        print(f"stage {stage} sweep {index}: probe A {m['mean']:+,.0f} ({m['ci95_low']:+,.0f}, "
              f"{m['ci95_high']:+,.0f}) [{m['kind']}]", flush=True)
        after(f"{name} sweep {index} on probe A: {m['mean']:+,.0f} ({m['kind']})")
        if should_stop(stage, means):
            break
        play_round(stage, index, jobs)
        after(f"{name}: round {index}")
        index += 1
    body = stage_choice(stage)
    chosen = body["chosen"]
    a = chosen["measure"] if chosen else None
    rule = stage_rule(stage, None, chosen, a)
    b = None
    if rule["go"]:  # stage 1's no-go plays no probe B
        label = f"sweep{chosen['sweep']}"
        b = probe(stage, label, *agent_of_choice(stage, chosen), "B", jobs)["measure"]
        _keep_games(stage, label, "B")
        rule = stage_rule(stage, b, chosen, a)
    found = _write_choice(stage, body | {"probe_b": b, "rule": rule})
    after(f"{name}: choice {chosen and chosen['sweep']}, probe B "
          f"{'none' if b is None else format(b['mean'], '+,.0f')}, go {rule['go']}")
    return found


def agent_of_choice(stage: int, chosen: dict[str, Any]) -> tuple[str, str]:
    return agent(stage, chosen["sweep"])


def decide() -> dict[str, Any]:
    """``v36`` (decision.json): the stage choice (of the stages not stopped) with the highest
    probe B measure, if above 0. Needs every stage to have run or the run to have stopped."""
    candidates: dict[int, float | None] = {}
    for stage in STAGES:
        found = _stage_done(stage)
        if found is None:
            raise ValueError(f"stage {stage} has not run")
        go = found["rule"]["go"]
        candidates[stage] = found["probe_b"]["mean"] if go and found["probe_b"] else None
        if not go and stage < 3:  # a no-go at stage 1 or a stopped stage 2 ends the run
            break
    result = choose_v36(candidates)
    if result["v36"] is not None:
        stage = result["v36"]
        chosen = choice(stage)
        early, mid = agent_of_choice(stage, chosen)
        result["agent"] = {"stage": stage, "sweep": chosen["sweep"], "early": early,
                           "mid": mid, "late": LATE,
                           "shas": [_sha(_path(p)) for p in (early, mid, LATE)],
                           "v15_below_230": early == V15}
    result["rule"] = ("v36 is the stage choice with the highest probe B measure; no final "
                      "evaluation unless it is above 0; its probe B figure is selected (the "
                      "best of up to three) (predeclared.md). Stage 1's measure is in points at "
                      "levels 29 and up, the others' in total score: stage 1's agent plays "
                      "v29r20d's own game below 230 lines (prefix guard), so its total score "
                      "differs from v29r20d's only there, and the 29+ form leaves out the probe "
                      "half's luck below 230. The one-scale rule covers the training rows' "
                      "values; inside backup2 a board's leaves are valued by the network the "
                      "target is computed under (033's recipe).")
    _write(DECISION, result)
    return result


# ---------------------------------------------------------------- the wiring check

def _wiring_game(job: tuple[int, str, str, float, bool]) -> dict[str, Any]:
    seed, early, mid, explore, dump = job
    played, rows = _game(seed, early, mid, explore=explore,
                         explore_lines=STAGES[1]["explore"], dump=dump)
    out = {"seed": seed, "inputs": base64.b64encode(played["inputs"]).decode("ascii"),
           "score": played["score"], "lines": played["lines"]}
    if dump:
        r = band_rows(rows, 1)
        out |= {"band_rows": int(len(r)), "rows_sha": hashlib.sha256(rows).hexdigest()}
    return out


def _first_games(part: dict[str, np.ndarray], games: int) -> dict[str, np.ndarray]:
    keep = np.isin(part["game"], np.unique(part["game"])[:games])
    return {k: v[keep] for k, v in part.items()}


def _equal_on_games(stored: Path, part: dict[str, np.ndarray], split: int, previous: Path,
                    handover: Callable[[np.ndarray], np.ndarray], tap_interval: int,
                    jobs: int, games: int = 3) -> dict[str, Any]:
    """This module's played-board targets of the first ``games`` games of a stored sweep's
    first training part against that sweep's stored targets (its first rows)."""
    sub = _first_games(part, games)
    built = build_targets([sub], previous, split, handover, jobs, np.random.default_rng(0),
                          tap_interval=tap_interval)
    mine = built["goal"][built["kind"] == 0]
    want = e23._load_npz(stored)["goal"][:len(mine)]
    return {"stored": _relative(stored), "games": games, "boards": int(len(mine)),
            "max_abs_difference": float(np.abs(mine - want).max()) if len(mine) else None,
            "match": bool(len(mine) > 0 and np.array_equal(mine, want))}


def wiring_check(jobs: int) -> dict[str, Any]:
    """plan.md's wiring check, on this library:

    1. this module's game with ``v29r20d``'s networks re-runs the first 3 stored
       ``v29r20d`` probe games input for input, also as data-dump games with exploration off;
       with exploration on a dump game is deterministic; 032's V18 below 230 changes a game;
    2. the stage 1 target job: on 033's sweep 7 data (first 3 games of its first part) with
       033's networks and 033's hand-over value it gives 033's stored targets; at 20 Hz it
       equals 033's target job; its 320+ value equals max(0, c x 033's V39' backup2);
    3. the stage 2 target job on 032's sweep 10 data (first 3 games of its first part) with
       032's networks and the 30 Hz format gives 032's stored targets.
    """
    _check_inputs()
    probe_games = e35._seeds()[:3]
    stored = reference()["by_seed"]["probe"]
    first = [stored[s] for s in probe_games]
    work = [(s, V15, V29_BASE, 0.0, d) for d in (False, True) for s in probe_games]
    work += [(probe_games[0], V15, V29_BASE, WIRING_EXPLORE, True)] * 2
    work += [(probe_games[0], V18_032, V29_BASE, 0.0, False)]
    with Pool(min(jobs, len(work))) as pool:
        played = pool.map(_wiring_game, work, chunksize=1)
    want = [e["inputs"] for e in first]
    plain = [g["inputs"] == w for g, w in zip(played[:3], want)]
    dumped = [g["inputs"] == w for g, w in zip(played[3:6], want)]
    explored = played[6:8]
    part1 = {"seeds": probe_games, "game_matches": plain, "dump_game_matches": dumped,
             "score_lines_match": [[g["score"], g["lines"]] == [e["result"]["score"],
                                                               e["result"]["lines"]]
                                   for g, e in zip(played[:3], first)],
             "explore_dump_deterministic": explored[0] == explored[1],
             "explore_changes_the_game": explored[0]["inputs"] != want[0],
             "explore_band_rows": explored[0]["band_rows"], "explore_rate": WIRING_EXPLORE,
             "v18_below_230_changes_the_game": played[8]["inputs"] != want[0]}
    part1["match"] = bool(all(plain) and all(dumped) and all(part1["score_lines_match"]) and
                          part1["explore_dump_deterministic"] and explored[0]["band_rows"] > 0
                          and part1["explore_changes_the_game"]
                          and part1["v18_below_230_changes_the_game"])
    # 2. stage 1's target job against 033's
    late = _path(LATE)
    parts33, _ = e33._training_parts(7)
    raw = lambda rows: targets(late, rows, DEPTH, jobs)[0]  # noqa: E731  033's hand-over
    returns33 = _equal_on_games(e33.DATA / "targets7.npz", parts33[0], LATE_FROM,
                                e33.weights_path(6), raw, TAP_INTERVAL, jobs)
    zero = e23._load_npz(e33.DATA / "round8.npz")
    below = e23._rows({k: zero[k][zero["lines"] < LATE_FROM] for k in KEYS})
    sample = np.ascontiguousarray(below[:: max(1, len(below) // 50)][:50])
    mine, _ = targets(e33.weights_path(6), sample, DEPTH, jobs)
    theirs, _ = e33.targets(e33.weights_path(6), sample, DEPTH, jobs)
    kids_mine = targets(e33.weights_path(6), sample, 1, jobs, children=True)
    kids_theirs = e33.targets(e33.weights_path(6), sample, 1, jobs, children=True)
    handover_rows = e23._rows({k: zero[k][zero["lines"] >= LATE_FROM] for k in KEYS})[:50]
    scaled = handover_value(1, jobs)(np.ascontiguousarray(handover_rows))
    direct, _ = e33.targets(late, np.ascontiguousarray(handover_rows), DEPTH, jobs)
    part2 = {"returns_vs_033_sweep7": returns33,
             "backup2_equals_033_target_job": bool(np.array_equal(mine, theirs)),
             "children_equal_033_target_job": bool(
                 np.array_equal(kids_mine[0], kids_theirs[0]) and
                 np.array_equal(kids_mine[1], kids_theirs[1])),
             "late_boards": int(len(handover_rows)), "c": e34.scale(),
             "late_value_equals_scaled_033_v39_backup2": bool(
                 np.array_equal(scaled, e34.scaled(direct, e34.scale())))}
    part2["match"] = bool(returns33["match"] and part2["backup2_equals_033_target_job"] and
                          part2["children_equal_033_target_job"] and part2["late_boards"] > 0
                          and part2["late_value_equals_scaled_033_v39_backup2"])
    # 3. stage 2's target job against 032's (30 Hz, 032's networks)
    if e29._config() | {"tap_interval": TAP_INTERVAL} != e33._config():
        raise ValueError("the 30 Hz and 20 Hz configurations differ in more than the tap")
    anchor = e32.v29_path()
    parts32, _ = e32._training_parts(10)
    def v29(rows: np.ndarray) -> np.ndarray:  # 032's hand-over value: 030's V29 at 30 Hz
        return targets(anchor, rows, DEPTH, jobs, tap_interval=TAP_INTERVAL_30)[0]

    returns32 = _equal_on_games(e32.DATA / "targets10.npz", parts32[0], MID_FROM,
                                e32.weights_path(9), v29, TAP_INTERVAL_30, jobs)
    early = e23._rows({k: parts32[0][k][parts32[0]["lines"] < MID_FROM] for k in KEYS})
    sample32 = np.ascontiguousarray(early[:: max(1, len(early) // 50)][:50])
    mine32, _ = targets(e32.weights_path(9), sample32, DEPTH, jobs, tap_interval=TAP_INTERVAL_30)
    theirs32, _ = e29.targets(e32.weights_path(9), sample32, DEPTH, jobs)
    part3 = {"returns_vs_032_sweep10": returns32,
             "backup2_equals_032_target_job": bool(np.array_equal(mine32, theirs32))}
    part3["match"] = bool(returns32["match"] and part3["backup2_equals_032_target_job"])
    result = {"experiment": OUT.name, "format": e33.format_of(e33._frozen()[0]),
              "search": search(), "games": part1, "stage1_targets": part2,
              "stage2_targets": part3,
              "matched": bool(part1["match"] and part2["match"] and part3["match"]),
              "calibration_sha256": e34.calibration()["sha256"], "library": library_record(),
              "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- the checks on earlier runs

def _handover_values(path: Path, split: int, weights: Path, tap_interval: int, jobs: int,
                     cache: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """backup2 of a stored round's hand-over boards (``split`` lines or more), keyed by
    (game, lines), once per round file."""
    key = str(path)
    if key not in cache:
        d = e23._load_npz(path)
        keep = d["lines"] >= split
        cache[key] = {"seed": d["seed"][keep], "values": targets(
            weights, e23._rows({k: d[k][keep] for k in KEYS}), DEPTH, jobs,
            tap_interval=tap_interval)[0]}
    return cache[key]


def earlier_checks(jobs: int) -> dict[str, Any]:
    """The two checks re-computed on 033's, 034's and 032's stored sweep targets (plan.md's
    table). The hand-over value of 033 (V39' backup2, 20 Hz) and 032 (030's V29 backup2, 30
    Hz) is not stored with their targets, so it is computed on their training parts'
    hand-over boards; 034's is the actual rest of game it trained on. No game is played."""
    out: dict[str, Any] = {}
    cache: dict[str, Any] = {}
    for k in range(1, 11):
        d = e23._load_npz(e34.DATA / f"targets{k}.npz")
        sizes = d["sizes"].tolist()
        n = (len(sizes) - 2) // 2
        a, b = sum(sizes[:n]), sum(sizes[:2 * n])
        lines = d["lines"].astype(np.int64)
        out[f"034_sweep{k}"] = target_checks(1, lines[:a], d["goal"][:a], lines[b:],
                                             d["goal"][b:], d["goal"][a:b])
    for name, module, sweeps, stage, split, weights, tap in (
            ("033", e33, range(1, 10), 1, LATE_FROM, e33.v39r_late_path(), TAP_INTERVAL),
            ("032", e32, range(1, 11), 2, MID_FROM, e32.v29_path(), TAP_INTERVAL_30)):
        for k in sweeps:
            d = e23._load_npz(module.DATA / f"targets{k}.npz")
            a = int(sum(d["sizes"].tolist()))
            lines = d["lines"].astype(np.int64)
            rounds = [0] + list(range(max(1, k - module.KEPT_ROUNDS), k))
            held = set(module.round_seeds(0)[:module.CHECK_SEEDS])
            values = []
            for r in rounds:
                found = _handover_values(module.DATA / f"round{r}.npz", split, weights, tap,
                                         jobs, cache)
                keep = ~np.isin(found["seed"], list(held)) if r == 0 else \
                    np.ones(len(found["seed"]), bool)
                values.append(found["values"][keep])
            out[f"{name}_sweep{k}"] = target_checks(stage, lines[:a], d["goal"][:a],
                                                    lines[a:], d["goal"][a:],
                                                    np.concatenate(values))
    result = {"experiment": OUT.name,
              "note": "034: hand-over value = the actual rest of game (its training rows); "
                      "033: V39' backup2 at 20 Hz; 032: 030's V29 backup2 at 30 Hz, both "
                      "computed here on the training parts' hand-over boards. 032 is checked "
                      "in stage 2's form.",
              "passed": {key: v["passed"] for key, v in out.items()},
              "sweeps": out, "library": library_record(),
              "versions": runner._record_versions()}
    _write(EARLIER, result)
    return result


# ---------------------------------------------------------------- status, command line

def status() -> dict[str, Any]:
    found: dict[str, Any] = {}
    for stage in STAGES:
        rows = {}
        for k in range(0, STAGES[stage]["max"] + 1):
            rec = _sweep_record(stage, k)
            pa = _probe_record(stage, f"sweep{k}", "A")
            if rec.exists() or pa.exists():
                rows[k] = {"fitted": _load(rec)["fitted"] if rec.exists() else None,
                           "probe_a": _load(pa)["measure"]["mean"] if pa.exists() else None}
        found[str(stage)] = {"sweeps": rows, "done": _stage_done(stage)}
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment036")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="write the seed reservation (no games)")
    commands.add_parser("check", help="the wiring check")
    commands.add_parser("earlier-checks", help="the checks on 032-034's stored targets")
    stager = commands.add_parser("stage", help="run one stage (resumable)")
    stager.add_argument("stage", type=int, choices=sorted(STAGES))
    stager.add_argument("--device", default="cuda:0")
    stager.add_argument("--commit", action="store_true",
                        help="commit the experiment's directory after every step")
    stager.add_argument("--push", action="store_true", help="and push each commit")
    commands.add_parser("choose", help="name v36 (decision.json)")
    commands.add_parser("regate", help="the 20 Hz gate on a new library (after a change)")
    commands.add_parser("status", help="the sweeps and probes so far")
    for name in ("check", "earlier-checks", "stage", "regate"):
        commands.choices[name].add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            found = make_seeds() if not SEEDS.exists() else _load(SEEDS)
            print(f"{SEEDS}: indices {found['used_slice']}")
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "earlier-checks":
            print(json.dumps(earlier_checks(args.jobs)["passed"], indent=1))
        elif args.command == "stage":
            after = (lambda message: commit_step(message, args.push)) if args.commit else \
                (lambda message: None)
            found = run_stage(args.stage, args.jobs, args.device, after)
            print(json.dumps({k: found[k] for k in ("chosen", "probe_b", "rule")}, indent=1))
        elif args.command == "regate":
            found = regate(args.jobs)
            print(f"Wrote {REGATE}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "choose":
            print(json.dumps(decide(), indent=1))
        else:
            print(json.dumps(status(), indent=1))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
