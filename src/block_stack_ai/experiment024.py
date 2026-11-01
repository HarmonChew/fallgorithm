"""Run Experiment 024: teach 023's self-taught value the late levels from real outcomes.

    python -m block_stack_ai.experiment024 loop [--jobs N] [--device cuda:0]
    python -m block_stack_ai.experiment024 diagnose K [--device cuda:0]
    python -m block_stack_ai.experiment024 dev-check K [--part 0|1] [--jobs N]

023's loop (experiment023: backups, fit, probe and its settings) with two changes. The
targets of boards with ``outcome_from_lines`` (230: level 29) lines or more: play boards
are fitted to what their game actually went on to score (lambda 1 there), and base
boards and children, whose only target is the backup, are left out. And the play rounds
are played without exploration (``explore`` 0), so those outcomes are the agent's own.
V0 is 023's sweep 15; sweep 1 trains on four rounds of V0's games (rounds 0-1 to 0-4).
``loop`` plays them, then runs sweep, probe, a new play round with the new V and the
diagnostic, sweep after sweep, until the stop rule (resumable: each step is skipped once
its file exists). ``diagnose`` checks V_K against
real outcomes by band on its own play round and its ranking at 017's rollout-ranked
decisions in 021's games of 017's agent.
"""

from __future__ import annotations

import argparse
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

from . import experiment012 as e12, experiment013 as e13, experiment020 as e20
from . import experiment021 as e21, experiment023 as e23, native, runner
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "024-real-outcomes-late"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
DATA_ROOT = runner.PROJECT_ROOT / "runs" / "024-data"
PLAY_LABEL = "fallgorithm024/play/v{}/{{}}"
RANK_DATA = runner.PROJECT_ROOT / "runs" / "021-data" / "pilot"
TETRIS_18 = e23.TETRIS_18
KEYS = e23.KEYS
EDGES = {"18": (0, 130), "19-28": (130, 230), "29-38": (230, 330), "39+": (330, 430)}
CLEAR_POINTS = (0, 40, 100, 300, 1200)

_load, _write = e13._load, e13._write


def _weights_path(sweep: int) -> Path:
    if sweep == 0:
        return runner.PROJECT_ROOT / _load(CONFIG)["start_weights"]
    return EXPERIMENT_ROOT / f"value024_sweep{sweep}.bin"


def _play_dir(name: str | int) -> Path:
    """A play round: ``0-1`` to ``0-<first_rounds>`` are V0's, round K is V_K's."""
    return DATA_ROOT / f"play{name}"


def _round_names(sweep: int) -> list[str]:
    """The rounds played before sweep ``sweep``: V0's first rounds, then 1 to sweep - 1."""
    first = [f"0-{k}" for k in range(1, _load(CONFIG)["first_rounds"] + 1)]
    return first + [str(k) for k in range(1, sweep)]


def _own_round(sweep: int) -> str:
    """The play round of V_sweep's own games (V0's: its last first round)."""
    return _round_names(1)[-1] if sweep == 0 else str(sweep)


# ---------------------------------------------------------------- play

def play_seeds(round_name: str) -> list[int]:
    """A play round's seeds (drawn on first use, stored in seeds.json): no excluded, dev
    or 023 probe start state, and none of the rounds drawn just before it that can share
    its training window (without exploration a repeated start state is a repeated game)."""
    stored = _load(SEEDS) if SEEDS.exists() else {
        "selection": "020's rule (SHA256 of the label with index; no excluded, dev, 023 "
                     "probe or repeated start state within a round or with the 3 rounds "
                     "drawn before it); no gameplay outcomes inspected",
        "play_label": PLAY_LABEL.replace("{{}}", "<index>").replace("{}", "<round>"),
        "play_seeds": {}}
    if round_name not in stored["play_seeds"]:
        e020 = _load(e20.SEEDS)
        window = list(stored["play_seeds"].values())[-(_load(e23.CONFIG)["play_rounds_kept"] - 1):]
        seen = {e20._identity(seed) for seed in e020["excluded_seeds"] + e020["dev_seeds"]
                + _load(e23.SEEDS)["probe_seeds"] + [s for r in window for s in r]}
        stored["play_seeds"][round_name] = e20._draw(
            PLAY_LABEL.format(round_name), _load(e23.CONFIG)["play"]["games"], seen)
        _write(SEEDS, stored)
    return stored["play_seeds"][round_name]


def _play_job(job: tuple[int, int, str]) -> tuple[int, dict[str, Any], bytes]:
    """023's _play_job with this experiment's exploration."""
    index, seed, weights = job
    config = _load(e23.CONFIG)
    tick = time.perf_counter()
    played, rows = native.net_game(
        (runner.PROJECT_ROOT / weights).read_bytes(), config["game"], seed,
        line_cap=config["line_cap"], frame_cap=config["frame_cap"], limits=e13._limits(config),
        explore=_load(CONFIG)["explore"], explore_seed=seed, dump=True)
    return index, {"seed": seed, "score": played["score"], "lines": played["lines"],
                   "stopping_reason": played["stopping_reason"],
                   "seconds": round(time.perf_counter() - tick, 2)}, rows


def play(round_name: str, weights: Path, jobs: int) -> Path:
    """023's play round, without exploration, into runs/024-data/play<round>
    (written to a temporary folder first, so a crash leaves no half round)."""
    directory = _play_dir(round_name)
    if directory.exists():
        raise ValueError(f"{directory} exists already")
    seeds = play_seeds(round_name)
    relative = e23._relative(weights)
    parts, games, tick = [], [], time.time()
    with Pool(jobs) as pool:
        for index, summary, rows in pool.imap(_play_job, [(i, s, relative)
                                                          for i, s in enumerate(seeds)]):
            games.append(summary)
            x = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)[1:]
            if summary["stopping_reason"] != "frame_limit" and len(x):
                parts.append(e23._boards(x) | {
                    "score": x[:, native.WIDTH + 1].copy(),
                    "game": np.full(len(x), index, np.int32),
                    "final": np.full(len(x), summary["score"], np.int64)})
    partial = directory.with_name(directory.name + ".partial")
    partial.mkdir(parents=True, exist_ok=True)
    np.savez(partial / "boards.npz",
             **{key: np.concatenate([p[key] for p in parts]) for key in parts[0]})
    _write(partial / "data.json", {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "round": round_name,
        "weights": {"path": relative, "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
        "games_per_round": len(seeds), "explore": _load(CONFIG)["explore"],
        "wall_seconds": round(time.time() - tick, 1),
        "mean_score": round(float(np.mean([g["score"] for g in games])), 1), "games": games})
    partial.replace(directory)
    return directory


def _play_rounds(sweep: int) -> list[dict[str, np.ndarray]]:
    """The play rounds sweep ``sweep`` trains on: the last ``play_rounds_kept`` (023's
    4) of the rounds played before it."""
    kept = _load(e23.CONFIG)["play_rounds_kept"]
    paths = [_play_dir(name) for name in _round_names(sweep)]
    return [e23._load_npz(p / "boards.npz") | {"name": np.array(e23._relative(p))}
            for p in paths[-kept:]]


# ---------------------------------------------------------------- sweep

def lambda_returns(backup: np.ndarray, data: dict[str, np.ndarray], lam: float,
                   from_lines: int) -> np.ndarray:
    """023's lambda-returns (in Tetrises at level 18) with lambda 1 for boards with
    ``from_lines`` lines or more: their return is the rest of their game's points."""
    points = data["score"].astype(np.float64) / TETRIS_18
    final = data["final"].astype(np.float64) / TETRIS_18
    lams = np.where(data["lines"] >= from_lines, 1.0, lam)
    out = np.zeros(len(backup))
    following = 0.0
    for t in range(len(backup) - 1, -1, -1):
        last = t == len(backup) - 1 or data["game"][t + 1] != data["game"][t]
        if last:
            step, following = final[t] - points[t], 0.0
        else:
            step = points[t + 1] - points[t]
        out[t] = (1 - lams[t]) * backup[t] + lams[t] * (step + following)
        following = out[t]
    return out


def sweep(index: int, jobs: int, device: str) -> dict[str, Any]:
    """023's sweep with this experiment's late targets."""
    config, own = _load(e23.CONFIG), _load(CONFIG)
    settings, cap, late = config["fit"], config["line_cap"], own["outcome_from_lines"]
    previous, out_path = _weights_path(index - 1), _weights_path(index)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist: run sweep {index - 1} first")
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    tick = time.time()
    every = e23._load_npz(e23.DATA_ROOT / "base_train.npz")
    early = every["lines"] < late
    train = {key: every[key][early] for key in KEYS}
    base_targets, kids = e23.backups(previous, e23._rows(train), jobs, children=True)
    kids_all = len(kids)
    kids = kids[kids[:, native.WIDTH] < late]
    kid_targets, _ = e23.backups(previous, kids, jobs, children=False)
    played = _play_rounds(index)
    play_targets = [lambda_returns(e23.backups(previous, e23._rows(p), jobs, children=False)[0],
                                   p, config["lambda"], late) for p in played]
    check = e23._load_npz(e23.DATA_ROOT / "base_check.npz")
    check_targets, _ = e23.backups(previous, e23._rows(check), jobs, children=False)
    backup_seconds = time.time() - tick
    boards = {key: np.concatenate([train[key], e23._boards(kids)[key]] + [p[key] for p in played])
              for key in KEYS}
    targets = np.concatenate([base_targets, kid_targets] + play_targets)
    torch.manual_seed(settings["torch_seed"] + index)
    model = e20.read_export(previous).to(device)
    t = e23._tensors(boards, targets, device)
    c = e23._tensors(check, check_targets, device)
    before = e23._predict(model, c, cap).cpu().numpy()
    log = e23._fit(model, t, settings, cap)
    after = e23._predict(model, c, cap).cpu().numpy()
    sha = e20.export(model, out_path)
    return {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": e23._relative(previous),
                 "sha256": hashlib.sha256(previous.read_bytes()).hexdigest()},
        "weights": {"path": e23._relative(out_path), "sha256": sha},
        "outcome_from_lines": late,
        "boards": {"train": len(train["lines"]), "train_left_out": int((~early).sum()),
                   "children": len(kids), "children_left_out": kids_all - len(kids),
                   "play": [len(p["lines"]) for p in played],
                   "play_late": [int((p["lines"] >= late).sum()) for p in played],
                   "check": len(check["lines"])},
        "play_rounds": [str(p["name"]) for p in played], "lambda": config["lambda"],
        "play_target_means": [round(float(x.mean()), 4) for x in play_targets],
        "settings": settings, "backup_seconds": round(backup_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "check": {"note": "015's check boards against the old V's backup (all bands, as 023)",
                  "by_band": e23._bands(check["lines"], {
                      "old_value": before, "backup": check_targets, "new_value": after,
                      "015_mc": check["mc"] / TETRIS_18})},
    }


# ---------------------------------------------------------------- diagnostic

def _values(model: e20.ValueNet, columns: np.ndarray, features: np.ndarray, lines: np.ndarray,
            drought: np.ndarray, last: np.ndarray, line_cap: int, device: str) -> np.ndarray:
    t = {"columns": torch.from_numpy(columns.astype(np.int32)).to(device),
         "features": torch.from_numpy(features.astype(np.int16)).to(device),
         "lines": torch.from_numpy(lines.astype(np.int16)).to(device),
         "drought": torch.from_numpy(drought.astype(np.int16)).to(device),
         "last": torch.from_numpy(last.astype(np.int8)).to(device)}
    v = e20._predict(model, t, line_cap).cpu().numpy().astype(np.float64)
    return np.where(lines >= line_cap, 0.0, v)  # net_value: 0 at the cap


def rank_scores(model: e20.ValueNet, rows: np.ndarray, line_cap: int, start_level: int,
                device: str) -> np.ndarray:
    """The net agent's commit score of each of 021's candidate rows, in Tetrises at level
    18: the clear's points plus V of the settled board (netsearch.hpp, preview unknown:
    the agent's drought, which counts the current piece, and the current piece as last)."""
    at = e21.FEATURES_AT
    cleared = np.zeros(len(rows), np.int64)
    for k in range(1, 5):
        cleared[rows[:, at + 4 + k] == 1.0] = k
    lines = rows[:, e21.LINES].astype(np.int64) + cleared
    level = np.array([native.level_for_lines(int(n), start_level) for n in lines])
    reward = np.array(CLEAR_POINTS)[cleared] * (level + 1) / TETRIS_18
    return reward + _values(model, rows[:, e21.HEAD:at], rows[:, at + 9:], lines,
                            rows[:, e21.DROUGHT], rows[:, e21.PIECE], line_cap, device)


def diagnose(index: int, device: str) -> dict[str, Any]:
    """V_index against the points its own play round went on to score, by band, and its
    commit picks at 017's rollout-ranked decisions (e21.table; the preview decisions
    below 29 are scored one ply only, so only the commit rows match the agent)."""
    config = _load(e23.CONFIG)
    cap, start = config["line_cap"], config["game"]["start_level"]
    weights = _weights_path(index)
    model = e20.read_export(weights).to(device).eval()
    directory = _play_dir(_own_round(index))
    d = e23._load_npz(directory / "boards.npz")
    v = _values(model, d["columns"], d["features"], d["lines"], d["drought"], d["last"], cap,
                device)
    actual = (d["final"].astype(np.float64) - d["score"]) / TETRIS_18
    bands = {}
    for band, (lo, hi) in EDGES.items():
        m = (d["lines"] >= lo) & (d["lines"] < hi)
        bands[band] = {"boards": int(m.sum()), "value": round(float(v[m].mean()), 3),
                       "actual": round(float(actual[m].mean()), 3),
                       "value_minus_actual": round(float((v[m] - actual[m]).mean()), 3)}
    steps = {f"{lo}-{lo + 19}": [round(float(v[m].mean()), 2), round(float(actual[m].mean()), 2)]
             for lo in range(230, cap, 20)
             if (m := (d["lines"] >= lo) & (d["lines"] < lo + 20)).any()}
    games = _load(directory / "data.json")["games"]
    _, _, rows, _ = e21.load_data(RANK_DATA)
    table = e21.table(rows, rank_scores(model, rows, cap, start, device))
    return {"sweep": index, "versions": runner._record_versions(),
            "weights": {"path": e23._relative(weights),
                        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
            "unit": "Tetrises at level 18 (22,800 points)",
            "own_games": {"play_round": e23._relative(directory), "games": len(games),
                          "mean_score": round(float(np.mean([g["score"] for g in games])), 1),
                          "line_cap_share": round(float(np.mean([g["lines"] >= cap
                                                                 for g in games])), 3),
                          "by_band": bands, "by_20_lines_value_actual": steps},
            "ranking_017_games": {"data": e23._relative(RANK_DATA),
                                  "note": "the network rows are V's commit picks; the "
                                          "rollouts end in the hand value, which leans "
                                          "this check towards the search",
                                  "table": table}}


# ---------------------------------------------------------------- loop

def _probe_path(index: int) -> Path:
    if index == 0:
        return e23.EXPERIMENT_ROOT / "probe_value_sweep15.json"
    return EXPERIMENT_ROOT / f"probe_value024_sweep{index}.json"


def _should_stop(index: int) -> bool:
    """The stop rule after sweep ``index``: the cap, or no new best probe mean in the
    last ``stop_after_flat`` sweeps (sweep 0's probe is 023's sweep 15's)."""
    own = _load(CONFIG)
    if index >= own["max_sweeps"]:
        return True
    means = [_load(_probe_path(k))["runs"]["net"]["mean_score"] for k in range(index + 1)]
    best = int(np.argmax(means))
    return index - best >= own["stop_after_flat"]


def loop(jobs: int, device: str) -> int:
    """V0's first rounds and its diagnostic, then sweep, probe, play and diagnose until
    the stop rule; each step skipped once done. Returns the last sweep."""
    for name in _round_names(1):
        if not _play_dir(name).exists():
            play(name, _weights_path(0), jobs)
    index = 0
    while True:
        path = EXPERIMENT_ROOT / f"diagnose_sweep{index}.json"
        if not path.exists():
            _write(path, diagnose(index, device))
        if index > 0:
            probe = _load(_probe_path(index))["runs"]["net"]
            print(f"sweep {index}: probe {probe['mean_score']:.0f}, "
                  f"{datetime.now().strftime('%H:%M')}", flush=True)
            if _should_stop(index):
                return index
        index += 1
        record = EXPERIMENT_ROOT / f"sweep{index}.json"
        if not record.exists():
            if _weights_path(index).exists():
                raise ValueError(f"{_weights_path(index)} has no {record.name}: delete it")
            found = sweep(index, jobs, device)
            _write(record, found)
        if not _probe_path(index).exists():
            _write(_probe_path(index), e23.probe(_weights_path(index), jobs))
        if not _play_dir(index).exists():
            play(str(index), _weights_path(index), jobs)


def dev_check(index: int, jobs: int, part: int) -> dict[str, Any]:
    """023's dev check of V_index, plus a pairing against 023 sweep 15's agent's games."""
    found = e23.dev_check(_weights_path(index), jobs, part)
    base = _load(e23.EXPERIMENT_ROOT / f"dev_check_value_sweep15_part{part}.json")["per_game"]
    return found | {"sweep15_paired": e12.paired(found["per_game"], base)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment024")
    commands = parser.add_subparsers(dest="command", required=True)
    loop_parser = commands.add_parser("loop", help="sweep, probe, play, diagnose until done")
    loop_parser.add_argument("--jobs", type=int, default=28)
    loop_parser.add_argument("--device", default="cuda:0")
    diag = commands.add_parser("diagnose", help="V_K against real outcomes and 017's picks")
    diag.add_argument("index", type=int)
    diag.add_argument("--device", default="cuda:0")
    dev = commands.add_parser("dev-check", help="V_K's agent on dev seeds")
    dev.add_argument("index", type=int)
    dev.add_argument("--part", type=int, choices=(0, 1), default=1)
    dev.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "loop":
            print(f"stopped after sweep {loop(args.jobs, args.device)}")
        elif args.command == "diagnose":
            path = EXPERIMENT_ROOT / f"diagnose_sweep{args.index}.json"
            if path.exists():
                raise ValueError(f"{path} exists already")
            _write(path, diagnose(args.index, args.device))
            print(f"Wrote {path}")
        else:
            path = EXPERIMENT_ROOT / f"dev_check_value024_sweep{args.index}_part{args.part}.json"
            if path.exists():
                raise ValueError(f"{path} exists already")
            _write(path, dev_check(args.index, args.jobs, args.part))
            print(f"Wrote {path}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
