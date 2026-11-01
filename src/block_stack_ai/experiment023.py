"""Run Experiment 023: a value that teaches itself through the search.

    python -m block_stack_ai.experiment023 seeds
    python -m block_stack_ai.experiment023 base
    python -m block_stack_ai.experiment023 sweep K [--jobs N] [--device cuda:0]
    python -m block_stack_ai.experiment023 probe WEIGHTS [--jobs N]
    python -m block_stack_ai.experiment023 play R --weights WEIGHTS [--jobs N]
    python -m block_stack_ai.experiment023 dev-check WEIGHTS [--part 0|1] [--jobs N]

The value V (020's network shape) of a settled board is taught its own one-piece
lookahead: the backup of a board is the average, over the next piece by the NES odds, of
that piece's best placement's clear points plus V of the board it leaves
(native/netsearch.hpp ``NetSearcher::backup``). A sweep backs up a fixed set of boards
with the last sweep's V and fits the next V to the backups (warm-started). The set holds
``base`` boards (020's round 0 games of 015's agent, then the network agent's own games
from ``play``) and, for each, the 7 boards V itself would pick next (one per next piece),
so V is taught on the boards its own choices lead to, not only on the boards another
agent chose (020's failure). ``probe`` plays the network agent (020's NetSearcher) on 100
probe seeds against 015's and 021's agents there; ``dev-check`` does it on 020's dev seeds
against 015's and 017's stored games.
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

from . import experiment012 as e12, experiment013 as e13, experiment016 as e16
from . import experiment020 as e20, experiment021 as e21, native, runner
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "023-self-taught-value"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
PROBE_BASELINES = EXPERIMENT_ROOT / "probe_baselines.json"
DATA_ROOT = runner.PROJECT_ROOT / "runs" / "023-data"
PROBE_LABEL = "fallgorithm023/probe/v1/{}"
PLAY_LABEL = "fallgorithm023/play/v{}/{{}}"
TETRIS_18 = e20.TETRIS_18
KEYS = ("columns", "lines", "drought", "last", "features")

_load, _write = e13._load, e13._write


def _weights_path(sweep: int) -> Path:
    if sweep == 0:
        return runner.PROJECT_ROOT / _load(CONFIG)["start_weights"]
    return EXPERIMENT_ROOT / f"value_sweep{sweep}.bin"


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(runner.PROJECT_ROOT))


# ---------------------------------------------------------------- seeds

def select_seeds() -> dict[str, Any]:
    """The probe seeds: none in 020's excluded or dev seeds (so none held out or dev);
    their start states may repeat a training game's (the 16-bit space is nearly used up
    by 020's 30,000 training games), which a training-side diagnostic allows."""
    stored = _load(e20.SEEDS)
    seen = {e20._identity(seed) for seed in stored["excluded_seeds"] + stored["dev_seeds"]}
    probe = e20._draw(PROBE_LABEL, _load(CONFIG)["probe"]["games"], seen)
    return {"selection": "020's rule (SHA256 of the label with index; no excluded, dev or "
                         "repeated start state); no gameplay outcomes inspected",
            "probe_label": PROBE_LABEL.replace("{}", "<index>"), "probe_seeds": probe,
            "excluded": "020's seeds.json excluded_seeds and dev_seeds", "play_seeds": {}}


def play_seeds(round_index: int) -> list[int]:
    """A play round's seeds (drawn on first use, stored in seeds.json): no excluded, dev
    or probe start state."""
    stored = _load(SEEDS)
    if str(round_index) not in stored["play_seeds"]:
        e020 = _load(e20.SEEDS)
        seen = {e20._identity(seed)
                for seed in e020["excluded_seeds"] + e020["dev_seeds"] + stored["probe_seeds"]}
        stored["play_seeds"][str(round_index)] = e20._draw(
            PLAY_LABEL.format(round_index), _load(CONFIG)["play"]["games"], seen)
        _write(SEEDS, stored)
    return stored["play_seeds"][str(round_index)]


# ---------------------------------------------------------------- boards

def _rows(boards: dict[str, np.ndarray]) -> np.ndarray:
    """Boards as fn_dump_game's rows (the score left 0)."""
    w = native.WIDTH
    rows = np.zeros((len(boards["lines"]), native.DUMP_STRIDE), np.int32)
    rows[:, :w] = boards["columns"]
    rows[:, w] = boards["lines"]
    rows[:, w + 2] = boards["drought"]
    rows[:, w + 3] = boards["last"]
    rows[:, w + 4:] = boards["features"]
    return rows


def _boards(rows: np.ndarray) -> dict[str, np.ndarray]:
    w = native.WIDTH
    return {"columns": rows[:, :w].astype(np.uint32), "lines": rows[:, w].astype(np.int16),
            "drought": rows[:, w + 2].astype(np.int16), "last": rows[:, w + 3].astype(np.int8),
            "features": rows[:, w + 4:].astype(np.int16)}


def make_base() -> dict[str, Any]:
    """The fixed base boards from 020's round 0 (015's agent): ``boards`` sampled from
    games before ``check_from`` (training) and ``check_boards`` from the later games
    (checking), each with the points its game went on to score (``mc``). The first board
    of a game (no piece behind it) and frame-capped games are left out, as in 020."""
    settings = _load(CONFIG)["base"]
    source = runner.PROJECT_ROOT / settings["source"]
    data = e20.load_boards(source)
    games = json.loads((source / "data.json").read_text(encoding="utf-8"))["games"]
    cut = [i for i, g in enumerate(games) if g["stopping_reason"] == "frame_limit"]
    keep = (data["last"] >= 0) & ~np.isin(data["game"], cut)
    rng = np.random.default_rng(settings["numpy_seed"])
    out = {}
    for name, where, count in (("train", data["game"] < settings["check_from"],
                                settings["boards"]),
                               ("check", data["game"] >= settings["check_from"],
                                settings["check_boards"])):
        chosen = np.sort(rng.choice(np.flatnonzero(keep & where), count, replace=False))
        out[name] = {key: data[key][chosen] for key in KEYS} | {
            "mc": data["target"][chosen], "game": data["game"][chosen]}
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name, part in out.items():
        np.savez(DATA_ROOT / f"base_{name}.npz", **part)
    return {"source": settings["source"], "train_boards": len(out["train"]["lines"]),
            "check_boards": len(out["check"]["lines"])}


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


def _play_rounds() -> list[dict[str, np.ndarray]]:
    """Every play round's boards so far (whole games, in order), with ``score`` (the
    points before the board), ``game`` and ``final`` (the game's final score)."""
    kept = _load(CONFIG)["play_rounds_kept"]
    paths = sorted(DATA_ROOT.glob("play*/boards.npz"), key=lambda p: int(p.parent.name[4:]))
    return [_load_npz(path) | {"name": np.array(path.parent.name)} for path in paths[-kept:]]


def lambda_returns(backup: np.ndarray, data: dict[str, np.ndarray], lam: float) -> np.ndarray:
    """Each board's lambda-return along its own game, in Tetrises at level 18:
    G_t = (1 - lam) B_t + lam (points until the next board + G_{t+1}), where B_t is the
    board's backup and, after a game's last board, the rest of the game's points end it
    (G = 0 once it is over)."""
    points = data["score"].astype(np.float64) / TETRIS_18
    final = data["final"].astype(np.float64) / TETRIS_18
    out = np.zeros(len(backup))
    following = 0.0
    for t in range(len(backup) - 1, -1, -1):
        last = t == len(backup) - 1 or data["game"][t + 1] != data["game"][t]
        if last:
            step, following = final[t] - points[t], 0.0
        else:
            step = points[t + 1] - points[t]
        out[t] = (1 - lam) * backup[t] + lam * (step + following)
        following = out[t]
    return out


# ---------------------------------------------------------------- backups

def _backup_job(job: tuple[str, bytes, bool]) -> tuple[np.ndarray, bytes | None]:
    weights, rows, children = job
    config = _load(CONFIG)
    found, kids = native.backup_values(
        (runner.PROJECT_ROOT / weights).read_bytes(), rows, line_cap=config["line_cap"],
        start_level=config["game"]["start_level"],
        double_killscreen=config["game"]["ruleset"].endswith("double_killscreen"),
        tap_interval=e13._limits(config).tap_interval, children=children)
    return np.array(found) / TETRIS_18, kids


def backups(weights: Path, rows: np.ndarray, jobs: int,
            children: bool) -> tuple[np.ndarray, np.ndarray | None]:
    """Each row's backup under ``weights`` (in Tetrises at level 18) and with ``children``
    its 7 next boards as rows (those with no placement dropped)."""
    chunks = np.array_split(rows, max(1, jobs * 8))
    relative = _relative(weights)
    with Pool(jobs) as pool:
        found = pool.map(_backup_job, [(relative, c.tobytes(), children) for c in chunks],
                         chunksize=1)
    values = np.concatenate([v for v, _ in found])
    if not children:
        return values, None
    kids = np.concatenate([np.frombuffer(k, np.int32).reshape(-1, native.DUMP_STRIDE)
                           for _, k in found])
    return values, kids[kids[:, native.WIDTH] >= 0]


# ---------------------------------------------------------------- fit

def _tensors(boards: dict[str, np.ndarray], target: np.ndarray, device: str) -> dict[str, Any]:
    t = {key: torch.from_numpy(boards[key].astype(np.int32 if key == "columns"
                                                  else boards[key].dtype)).to(device)
         for key in KEYS}
    t["target"] = torch.from_numpy(target.astype(np.float32)).to(device)
    return t


def _predict(model: e20.ValueNet, t: dict[str, Any], line_cap: int) -> torch.Tensor:
    return e20._predict(model, t, line_cap)


def _fit(model: e20.ValueNet, t: dict[str, Any], settings: dict[str, Any],
         line_cap: int) -> list[dict[str, Any]]:
    n = len(t["lines"])
    steps = settings["epochs"] * n // settings["batch"]
    optimiser = torch.optim.Adam(model.parameters(), lr=settings["lr"])
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, settings["lr"], total_steps=steps)
    log, tick = [], time.time()
    model.train()
    for step in range(steps):
        index = torch.randint(n, (settings["batch"],), device=t["lines"].device)
        loss = torch.nn.functional.mse_loss(model(e20._batch_inputs(t, index, line_cap)),
                                            t["target"][index])
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        optimiser.step()
        schedule.step()
        if (step + 1) % max(1, steps // 5) == 0:
            log.append({"step": step + 1, "loss": round(loss.item(), 4),
                        "seconds": round(time.time() - tick, 1)})
            print(log[-1], file=sys.stderr, flush=True)
    model.eval()
    return log


def _bands(lines: np.ndarray, values: dict[str, np.ndarray]) -> dict[str, Any]:
    edges = {"18": (0, 130), "19-28": (130, 230), "29-38": (230, 330), "39+": (330, 430)}
    return {band: {name: round(float(v[(lines >= lo) & (lines < hi)].mean()), 3)
                   for name, v in values.items()}
            for band, (lo, hi) in edges.items() if ((lines >= lo) & (lines < hi)).any()}


def sweep(index: int, jobs: int, device: str) -> dict[str, Any]:
    """Sweep ``index``: back up the training boards and their children with the last
    sweep's V, fit V warm-started from it, and check it on the base check boards."""
    config = _load(CONFIG)
    settings = config["fit"]
    previous = _weights_path(index - 1)
    if not previous.exists():
        raise ValueError(f"{previous} does not exist: run sweep {index - 1} first")
    out_path = _weights_path(index)
    if out_path.exists():
        raise ValueError(f"{out_path} exists already")
    cap = config["line_cap"]
    tick = time.time()
    train = _load_npz(DATA_ROOT / "base_train.npz")
    rows = _rows(train)
    base_targets, kids = backups(previous, rows, jobs, children=True)
    kid_targets, _ = backups(previous, kids, jobs, children=False)
    played = _play_rounds()
    play_targets = [lambda_returns(backups(previous, _rows(p), jobs, children=False)[0], p,
                                   config["lambda"]) for p in played]
    check = _load_npz(DATA_ROOT / "base_check.npz")
    check_targets, _ = backups(previous, _rows(check), jobs, children=False)
    backup_seconds = time.time() - tick
    boards = {key: np.concatenate([train[key], _boards(kids)[key]] + [p[key] for p in played])
              for key in KEYS}
    targets = np.concatenate([base_targets, kid_targets] + play_targets)
    torch.manual_seed(settings["torch_seed"] + index)
    model = e20.read_export(previous).to(device)
    t = _tensors(boards, targets, device)
    c = _tensors(check, check_targets, device)
    before = _predict(model, c, cap).cpu().numpy()
    log = _fit(model, t, settings, cap)
    after = _predict(model, c, cap).cpu().numpy()
    sha = e20.export(model, out_path)
    mc = check["mc"] / TETRIS_18
    return {
        "sweep": index, "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": _relative(previous),
                 "sha256": hashlib.sha256(previous.read_bytes()).hexdigest()},
        "weights": {"path": _relative(out_path), "sha256": sha},
        "boards": {"train": len(rows), "children": len(kids),
                   "play": [len(p["lines"]) for p in played], "check": len(mc)},
        "play_rounds": [str(p["name"]) for p in played], "lambda": config["lambda"],
        "play_rounds_kept": config["play_rounds_kept"],
        "play_target_means": [round(float(t.mean()), 4) for t in play_targets],
        "settings": settings, "backup_seconds": round(backup_seconds, 1),
        "training_log": log, "unit": "Tetrises at level 18 (22,800 points)",
        "check": {
            "backup_minus_old_value": round(float((check_targets - before).mean()), 4),
            "new_value_minus_backup_rms": round(float(np.sqrt(((after - check_targets) ** 2)
                                                              .mean())), 4),
            "old_value_minus_backup_rms": round(float(np.sqrt(((before - check_targets) ** 2)
                                                              .mean())), 4),
            "by_band": _bands(check["lines"], {"old_value": before, "backup": check_targets,
                                               "new_value": after, "015_mc": mc}),
        },
        "train_backup_minus_children_backup": round(float(base_targets.mean() -
                                                          kid_targets.mean()), 4),
    }


# ---------------------------------------------------------------- games

def _game(job: tuple[str, int, str | None]) -> dict[str, Any]:
    """One game: ``net`` (the network agent with ``weights``), ``fast_deep`` (015) or
    ``rank`` (021's agent), replayed for its score by band (020's dev_game rule)."""
    name, seed, weights = job
    config = _load(CONFIG)
    common = {"line_cap": config["line_cap"], "frame_cap": config["frame_cap"],
              "limits": e13._limits(config)}
    tick = time.perf_counter()
    if name == "net":
        played, _ = native.net_game((runner.PROJECT_ROOT / weights).read_bytes(),
                                    config["game"], seed, **common)
    elif name == "rank":
        played = native.rank_game((e21.EXPERIMENT_ROOT / "rank_pilot.bin").read_bytes(),
                                  config["game"], seed,
                                  params=native.params(e21.agent_params()), **common)
    else:
        played = native.play_game_ex(e16.KINDS["fast_deep"], config["game"], seed,
                                     params=native.params(e16.fast_deep_params()), **common)
    seconds = time.perf_counter() - tick
    return {"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "seconds": seconds} | e20._replay(config, seed, played)


def _against(games: list[dict[str, Any]], base: dict[str, list[dict[str, Any]]]) -> dict:
    return {"runs": {"net": e20.summary(games)} | {n: e20.summary(g) for n, g in base.items()},
            "paired": {f"net - {n}": e12.paired(games, g) for n, g in base.items()}}


def probe(weights: Path, jobs: int) -> dict[str, Any]:
    """The network agent on the probe seeds, paired against 015's and 021's agents there
    (played once, stored in probe_baselines.json)."""
    seeds = _load(SEEDS)["probe_seeds"]
    if not PROBE_BASELINES.exists():
        with Pool(jobs) as pool:
            found = pool.map(_game, [(n, s, None) for n in ("rank", "fast_deep") for s in seeds],
                             chunksize=1)
        _write(PROBE_BASELINES, {"versions": runner._record_versions(), "games": {
            n: [g for g in found if g["name"] == n] for n in ("fast_deep", "rank")}})
    base = _load(PROBE_BASELINES)["games"]
    relative = _relative(weights)
    with Pool(jobs) as pool:
        games = pool.map(_game, [("net", s, relative) for s in seeds], chunksize=1)
    return {"weights": {"path": relative,
                        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
            "versions": runner._record_versions()} | _against(games, base) | {
        "per_game": [{k: g[k] for k in ("seed", "score", "lines")} for g in games]}


def _play_job(job: tuple[int, int, str]) -> tuple[int, dict[str, Any], bytes]:
    index, seed, weights = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played, rows = native.net_game(
        (runner.PROJECT_ROOT / weights).read_bytes(), config["game"], seed,
        line_cap=config["line_cap"], frame_cap=config["frame_cap"], limits=e13._limits(config),
        explore=config["play"]["explore"], explore_seed=seed, dump=True)
    return index, {"seed": seed, "score": played["score"], "lines": played["lines"],
                   "stopping_reason": played["stopping_reason"],
                   "seconds": round(time.perf_counter() - tick, 2)}, rows


def play(round_index: int, weights: Path, jobs: int) -> Path:
    """Play round ``round_index``: the network agent with ``weights`` (and the config's
    exploration) on fresh seeds; every board of each game (after the first; frame-capped
    games dropped) joins the training boards, with its game's points for the
    lambda-returns."""
    config = _load(CONFIG)
    directory = DATA_ROOT / f"play{round_index}"
    directory.mkdir(parents=True, exist_ok=False)
    seeds = play_seeds(round_index)
    relative = _relative(weights)
    parts, games, tick = [], [], time.time()
    with Pool(jobs) as pool:
        for index, summary, rows in pool.imap(_play_job, [(i, s, relative)
                                                          for i, s in enumerate(seeds)]):
            games.append(summary)
            x = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)[1:]
            if summary["stopping_reason"] != "frame_limit" and len(x):
                parts.append(_boards(x) | {
                    "score": x[:, native.WIDTH + 1].copy(),
                    "game": np.full(len(x), index, np.int32),
                    "final": np.full(len(x), summary["score"], np.int64)})
    np.savez(directory / "boards.npz",
             **{key: np.concatenate([p[key] for p in parts]) for key in parts[0]})
    _write(directory / "data.json", {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": runner._record_versions(), "round": round_index,
        "weights": {"path": relative, "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
        "settings": config["play"], "lambda": config["lambda"],
        "wall_seconds": round(time.time() - tick, 1),
        "mean_score": round(float(np.mean([g["score"] for g in games])), 1), "games": games})
    return directory


def dev_check(weights: Path, jobs: int, part: int) -> dict[str, Any]:
    """The network agent on one part of 020's dev seeds, paired against 015's and 017's
    stored games there and 021's rank agent's (its dev check's per-game scores, so its
    pairing has no bands)."""
    stored = _load(e20.DEV_BASELINES)[str(part)]
    relative = _relative(weights)
    with Pool(jobs) as pool:
        games = pool.map(_game, [("net", s, relative) for s in stored["seeds"]], chunksize=1)
    rank = _load(e21.EXPERIMENT_ROOT / f"dev_check_rank_pilot_part{part}.json")["per_game"]
    return {"question": "The self-taught value's agent against 015's, 017's and 021's, on "
                        "dev seeds",
            "rank_paired": e12.paired(games, rank),
            "by_band": {f"net - {n}": e16._band_pairs(games, g)
                        for n, g in stored["games"].items()},
            "seeds": f"Experiment 020's dev seeds {part * 100} to {part * 100 + 99}",
            "weights": {"path": relative,
                        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
            "versions": runner._record_versions()} | _against(games, stored["games"]) | {
        "per_game": [{k: g[k] for k in ("seed", "score", "lines")} for g in games]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment023")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="select the probe seeds")
    commands.add_parser("base", help="sample the base boards from 020's round 0")
    sweep_parser = commands.add_parser("sweep", help="back up and refit V once")
    sweep_parser.add_argument("index", type=int)
    sweep_parser.add_argument("--jobs", type=int, default=28)
    sweep_parser.add_argument("--device", default="cuda:0")
    probe_parser = commands.add_parser("probe", help="the network agent on the probe seeds")
    probe_parser.add_argument("weights", type=Path)
    probe_parser.add_argument("--jobs", type=int, default=28)
    play_parser = commands.add_parser("play", help="the network agent's own games as boards")
    play_parser.add_argument("round", type=int)
    play_parser.add_argument("--weights", type=Path, required=True)
    play_parser.add_argument("--jobs", type=int, default=28)
    dev = commands.add_parser("dev-check", help="the network agent on dev seeds")
    dev.add_argument("weights", type=Path)
    dev.add_argument("--part", type=int, choices=(0, 1), default=1)
    dev.add_argument("--jobs", type=int, default=28)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            if SEEDS.exists():
                raise ValueError(f"{SEEDS} exists already")
            _write(SEEDS, select_seeds())
            print(f"Wrote {SEEDS}")
        elif args.command == "base":
            print(make_base())
        elif args.command == "sweep":
            found = sweep(args.index, args.jobs, args.device)
            path = EXPERIMENT_ROOT / f"sweep{args.index}.json"
            _write(path, found)
            print(f"Wrote {path}")
        elif args.command == "probe":
            path = EXPERIMENT_ROOT / f"probe_{args.weights.stem}.json"
            _write(path, probe(args.weights, args.jobs))
            print(f"Wrote {path}")
        elif args.command == "play":
            print(f"Data: {play(args.round, args.weights, args.jobs)}")
        else:
            path = EXPERIMENT_ROOT / f"dev_check_{args.weights.stem}_part{args.part}.json"
            _write(path, dev_check(args.weights, args.jobs, args.part))
            print(f"Wrote {path}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
