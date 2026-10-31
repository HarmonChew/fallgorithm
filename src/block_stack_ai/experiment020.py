"""Run Experiment 020: a learned value network.

    python -m block_stack_ai.experiment020 seeds
    python -m block_stack_ai.experiment020 collect [--jobs N]
    python -m block_stack_ai.experiment020 fit DATA [--device cuda:0]

``seeds`` selects the new dev seeds (``fallgorithm020/dev/v1``) and round 0's training
seeds (``fallgorithm020/train/v0``). ``collect`` plays 015's agent on the training
seeds, with config.json's light exploration, and keeps every board a piece left
(native ``dump_game``) and the points the game went on to score after it. The data goes
to runs/ (it is large, and each game is a pure function of its seed and settings).
``fit`` fits the value network to a round's boards (PyTorch), writes its weights under
the experiment directory and checks it offline (step 2): validation error against two
baselines, and the probe of 013's failure (taller must be worse).
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

from . import experiment006, experiment012 as e12, experiment013 as e13
from . import experiment016 as e16, experiment018 as e18, native, runner
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "020-value-net"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
DATA_ROOT = runner.PROJECT_ROOT / "runs" / "020-data"
DEV_LABEL = "fallgorithm020/dev/v1/{}"
TRAIN_LABEL = "fallgorithm020/train/v{}/{}"  # round, index
TETRIS_18 = 1200 * 19  # the network's unit: a Tetris at level 18
# The network's inputs, in order: the 200 visible cells (row by row from the top), the 18
# board features, the speed band (18, 19-28, 29-38, 39+), the lines left before the cap
# in hundreds, the drought, and the piece that left the board (one-hot; none: all 0).
CELLS = native.WIDTH * 20
INPUTS = CELLS + native.BOARD_FEATURES + 4 + 1 + 1 + 7

_load, _write = e13._load, e13._write


# ---------------------------------------------------------------- seeds

def _identity(seed: int) -> str:
    return experiment006.native_identity(_load(CONFIG)["game"], seed)


def _draw(label: str, count: int, seen: set[str]) -> list[int]:
    """``count`` labelled seeds, none with a start state in ``seen`` (which grows)."""
    selected, index = [], 0
    while len(selected) < count:
        seed = experiment006._label_seed(label, index)
        identity = _identity(seed)
        if identity not in seen:
            selected.append(seed)
            seen.add(identity)
        index += 1
        if index > 1 << 20:
            raise ValueError(f"fewer than {count} fresh start states for {label}")
    return selected


def select_seeds() -> dict[str, Any]:
    """The dev seeds, then round 0's training seeds: none in Experiments 000-012's seeds,
    013's dev seeds or 018's distil seeds, and no two with the same
    seed-erased native start state (seeds alias in pairs, so the 16-bit space holds about
    32k distinct games)."""
    config = _load(CONFIG)
    used = _load(e12.SEEDS)
    excluded = sorted(set(e12.excluded_seeds()) | set(used["train_seeds"]) |
                      set(used["heldout_seeds"]) | set(_load(e13.SEEDS)["dev_seeds"]) |
                      set(_load(e18.SEEDS)["distil_seeds"]))
    seen = {_identity(seed) for seed in excluded}
    dev = _draw(DEV_LABEL, config["dev_seed_count"], seen)
    train = _draw(TRAIN_LABEL.format(0, "{}"), config["round0"]["games"], seen)
    return {
        "selection": ("SHA256(<label with index>), first two bytes big-endian; skip any seed "
                      "in the excluded list and any seed whose seed-erased native start "
                      "state matches an excluded or already selected one (dev first, then "
                      "training); no gameplay outcomes inspected"),
        "excluded_seeds": excluded,
        "dev_label": DEV_LABEL.replace("{}", "<index>"), "dev_seeds": dev,
        "train_label": TRAIN_LABEL.format(0, "<index>"), "train_seeds": {"0": train},
    }


# ---------------------------------------------------------------- collect

def _limits(config: dict[str, Any]) -> Any:
    return e13._limits(config)


def dump_game(job: tuple[int, int, dict[str, Any]]) -> tuple[int, dict[str, Any], bytes]:
    """One round-0 game by 015's agent with exploration, and its boards."""
    index, seed, config = job
    explore = config["round0"]
    tick = time.perf_counter()
    played, rows = native.dump_game(
        e16.KINDS["fast_deep"], config["game"], seed, line_cap=config["line_cap"],
        frame_cap=config["frame_cap"], limits=_limits(config),
        params=native.params(e16.fast_deep_params()), explore=explore["explore"],
        explore_start=explore["explore_start"], explore_seed=seed)
    summary = {"seed": seed, "score": played["score"], "lines": played["lines"],
               "pieces": played["pieces"], "stopping_reason": played["stopping_reason"],
               "seconds": round(time.perf_counter() - tick, 2)}
    return index, summary, rows


def boards(index: int, summary: dict[str, Any], rows: bytes) -> dict[str, np.ndarray]:
    """One game's dump as compact arrays; ``target`` is the points scored after the board."""
    w = native.WIDTH
    x = np.frombuffer(rows, dtype=np.int32).reshape(-1, native.DUMP_STRIDE)
    return {"columns": x[:, :w].astype(np.uint32), "lines": x[:, w].astype(np.int16),
            "target": (summary["score"] - x[:, w + 1]).astype(np.int32),
            "drought": x[:, w + 2].astype(np.int16), "last": x[:, w + 3].astype(np.int8),
            "features": x[:, w + 4:].astype(np.int16),
            "game": np.full(len(x), index, dtype=np.int32)}


def collect(jobs: int) -> Path:
    """Round 0's data: ``boards.npz`` (every game's boards, in seed order) and
    ``data.json`` (the settings, code versions and each game's result)."""
    config = _load(CONFIG)
    seeds = _load(SEEDS)["train_seeds"]["0"]
    directory = DATA_ROOT / "round0"
    directory.mkdir(parents=True, exist_ok=False)
    tick = time.time()
    parts, games = [], []
    with Pool(jobs) as pool:
        for index, summary, rows in pool.imap(dump_game, [(i, s, config)
                                                          for i, s in enumerate(seeds)],
                                              chunksize=4):
            parts.append(boards(index, summary, rows))
            games.append(summary)
            if len(games) % 1000 == 0:
                print(f"{len(games)} games, {time.time() - tick:.0f} s", file=sys.stderr,
                      flush=True)
    np.savez(directory / "boards.npz",
             **{key: np.concatenate([p[key] for p in parts]) for key in parts[0]})
    header = {"created_at": datetime.now(timezone.utc).isoformat(),
              "versions": runner._record_versions(), "agent": "015's agent (fast_deep)",
              "params": e16.fast_deep_params(), "round0": config["round0"],
              "wall_seconds": round(time.time() - tick, 1), "games": games}
    (directory / "data.json").write_text(json.dumps(header, indent=1) + "\n",
                                         encoding="utf-8")
    return directory


# ---------------------------------------------------------------- the network (step 2)

def load_boards(directory: Path) -> dict[str, np.ndarray]:
    with np.load(directory / "boards.npz") as data:
        return {key: data[key] for key in data.files}


def speed_band(lines: torch.Tensor, start_level: int = 18) -> torch.Tensor:
    """0 for the start level, 1 for 19-28, 2 for 29-38, 3 for 39+ (start level 18 only)."""
    if start_level != 18:
        raise ValueError("the speed bands are written for start level 18")
    return (lines >= 130).long() + (lines >= 230).long() + (lines >= 330).long()


def inputs(columns: torch.Tensor, features: torch.Tensor, lines: torch.Tensor,
           drought: torch.Tensor, last: torch.Tensor, line_cap: int) -> torch.Tensor:
    """The network's INPUTS numbers per board, as float32 (unnormalised)."""
    n = len(columns)
    every = torch.arange(n, device=columns.device)
    rows = torch.arange(20, device=columns.device)
    cells = (columns.long()[:, :, None] >> rows) & 1  # board, column, row
    out = torch.zeros(n, INPUTS, device=columns.device)
    out[:, :CELLS] = cells.transpose(1, 2).reshape(n, CELLS).float()
    at = CELLS + native.BOARD_FEATURES
    out[:, CELLS:at] = features.float()
    out[every, at + speed_band(lines.long())] = 1.0
    out[:, at + 4] = (line_cap - lines.float()).clamp(min=0) / 100
    out[:, at + 5] = drought.float()
    piece = last.long()
    known = piece >= 0
    out[every[known], at + 6 + piece[known]] = 1.0
    return out


class ValueNet(torch.nn.Module):
    """INPUTS -> hidden -> hidden2 -> 1 with ReLUs, inputs normalised by fixed numbers."""

    def __init__(self, hidden: int, hidden2: int, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(INPUTS, hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, hidden2),
            torch.nn.ReLU(), torch.nn.Linear(hidden2, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers((x - self.mean) / self.std).squeeze(1)


def export(model: ValueNet, path: Path) -> str:
    """The weights as native/net.hpp reads them, normalisation folded into the first
    layer: a header of int32 (magic 0x30323046, INPUTS, hidden, hidden2), then float32
    first-layer rows (one per input), its biases, the second layer's rows (one per output),
    its biases, the output weights and bias. Returns the file's sha256."""
    first, _, second, _, third = model.layers
    with torch.no_grad():
        w1 = (first.weight / model.std).double()  # hidden x INPUTS
        b1 = first.bias.double() - (w1 * model.mean.double()).sum(1)
        parts = [w1.T, b1, second.weight.double(), second.bias.double(),
                 third.weight.double().squeeze(0), third.bias.double()]
    header = np.array([0x30323046, INPUTS, first.out_features, second.out_features], np.int32)
    data = header.tobytes() + b"".join(p.float().cpu().numpy().astype("<f4").tobytes()
                                       for p in parts)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_export(path: Path) -> ValueNet:
    """A ValueNet with an exported file's weights (mean 0, std 1: folded)."""
    data = path.read_bytes()
    magic, n_in, hidden, hidden2 = np.frombuffer(data[:16], "<i4")
    if magic != 0x30323046 or n_in != INPUTS:
        raise ValueError(f"{path} is not a value network for these inputs")
    numbers = torch.from_numpy(np.frombuffer(data[16:], "<f4").copy())
    model = ValueNet(int(hidden), int(hidden2), torch.zeros(INPUTS), torch.ones(INPUTS))
    first, _, second, _, third = model.layers
    sizes = [INPUTS * hidden, hidden, hidden * hidden2, hidden2, hidden2, 1]
    if sum(sizes) != len(numbers):
        raise ValueError(f"{path} has the wrong length")
    chunks = torch.split(numbers, sizes)
    with torch.no_grad():
        first.weight.copy_(chunks[0].reshape(INPUTS, hidden).T)
        first.bias.copy_(chunks[1])
        second.weight.copy_(chunks[2].reshape(hidden2, hidden))
        second.bias.copy_(chunks[3])
        third.weight.copy_(chunks[4].reshape(1, hidden2))
        third.bias.copy_(chunks[5])
    return model


def _tensors(data: dict[str, np.ndarray], keep: np.ndarray, device: str) -> dict[str, Any]:
    return {key: torch.from_numpy(data[key][keep].astype(
        np.int32 if key == "columns" else data[key].dtype)).to(device)
        for key in ("columns", "features", "lines", "drought", "last", "target")}


def _batch_inputs(t: dict[str, Any], index: torch.Tensor, line_cap: int) -> torch.Tensor:
    return inputs(t["columns"][index], t["features"][index], t["lines"][index],
                  t["drought"][index], t["last"][index], line_cap)


def _predict(model: ValueNet, t: dict[str, Any], line_cap: int,
             batch: int = 65536) -> torch.Tensor:
    with torch.no_grad():
        return torch.cat([model(_batch_inputs(t, torch.arange(i, min(i + batch, len(t["lines"])),
                                                               device=t["lines"].device),
                                              line_cap))
                          for i in range(0, len(t["lines"]), batch)])


def linear_baselines(train: dict[str, Any], check: dict[str, Any], line_cap: int,
                     chunk: int = 1 << 20) -> dict[str, torch.Tensor]:
    """Validation predictions of "lines left x points per line" and of 013's linear value
    (per band below 29, 29-38, 39+: a constant, the lines left L, the 18 features and each
    feature times L), both fitted by least squares on the training boards, summed in
    chunks so the design matrix is never whole."""
    def design(t: dict[str, Any], at: slice) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        left = (line_cap - t["lines"][at].double()).clamp(min=0) / 100
        f = t["features"][at].double()
        x = torch.cat([torch.ones_like(left)[:, None], left[:, None], f, f * left[:, None]], 1)
        band = speed_band(t["lines"][at].long()).clamp(min=1) - 1  # 18 joins 19-28: below 29
        return left, x, band
    device = train["lines"].device
    k = 2 + 2 * native.BOARD_FEATURES
    gram = torch.zeros(3, k, k, dtype=torch.float64, device=device)
    rhs = torch.zeros(3, k, dtype=torch.float64, device=device)
    left_y = left_left = 0.0
    for start in range(0, len(train["lines"]), chunk):
        at = slice(start, start + chunk)
        left, x, band = design(train, at)
        y = train["target"][at].double() / TETRIS_18
        left_y += (y * left).sum().item()
        left_left += (left * left).sum().item()
        for b in range(3):
            rows = band == b
            gram[b] += x[rows].T @ x[rows]
            rhs[b] += x[rows].T @ y[rows]
    weights = []
    for b in range(3):
        g = gram[b] + 1e-6 * torch.diag(gram[b].diag().clamp(min=1e-9))
        weights.append(torch.linalg.solve(g, rhs[b]))
    per_line = left_y / left_left
    lines_left, linear = [], []
    for start in range(0, len(check["lines"]), chunk):
        left, x, band = design(check, slice(start, start + chunk))
        lines_left.append(per_line * left)
        linear.append(torch.stack([x @ w for w in weights], 1).gather(1, band[:, None])[:, 0])
    return {"lines_left_x_points_per_line": torch.cat(lines_left),
            "linear_013": torch.cat(linear)}


def _errors(prediction: torch.Tensor, t: dict[str, Any]) -> dict[str, Any]:
    y = t["target"].double() / TETRIS_18
    error = (prediction.double() - y) ** 2
    band = speed_band(t["lines"].long())
    names = ("18", "19-28", "29-38", "39+")
    return {"mse": round(error.mean().item(), 4),
            "r2": round(1 - error.mean().item() / y.var().item(), 4),
            "mse_by_band": {names[b]: round(error[band == b].mean().item(), 4)
                            for b in range(4) if (band == b).any()}}


def probe_boards(heights: list[int]) -> torch.Tensor:
    """Tetris-ready stacks: rows filled from the bottom to ``height``, column 9 empty."""
    out = []
    for h in heights:
        column = sum(1 << row for row in range(20 - h, 20))
        out.append([column] * (native.WIDTH - 1) + [0])
    return torch.tensor(out, dtype=torch.int64)


def probe(model: ValueNet, config: dict[str, Any], device: str) -> dict[str, Any]:
    """013's failure probe: on Tetris-ready stacks of config.json's heights, V must fall at
    each step at 19-28 and at 39+, and fall by a larger share of the first at 39+. (A real
    board's cells are 4 x pieces - 10 x lines, so with an even number of lines a 9-column
    stack is a multiple of 4 high.)"""
    rule = config["fit"]["probe"]
    heights = rule["heights"]
    columns = probe_boards(heights).to(device)
    features = torch.tensor([native.board_features(tuple(c << 2 for c in board))
                             for board in columns.tolist()], device=device)
    out: dict[str, Any] = {"heights": heights}
    for name, lines in rule["lines"].items():
        n = len(heights)
        x = inputs(columns, features, torch.full((n,), lines, device=device),
                   torch.full((n,), rule["drought"], device=device),
                   torch.full((n,), rule["last"], device=device), config["line_cap"])
        with torch.no_grad():
            v = model.to(device)(x).double().tolist()
        out[name] = {"lines": lines, "value": [round(a, 3) for a in v],
                     "falls": all(b < a for a, b in zip(v, v[1:])),
                     "share_lost": round((v[0] - v[-1]) / abs(v[0]), 4) if v[0] else None}
    slow, fast = (out[name] for name in rule["lines"])
    out["passes"] = bool(slow["falls"] and fast["falls"] and slow["share_lost"] is not None and
                         fast["share_lost"] is not None and
                         fast["share_lost"] > slow["share_lost"])
    return out


def fit_round(directory: Path, device: str) -> dict[str, Any]:
    """Fit the network on a round's boards; validation on the last ``check_share`` of the
    games (whole games held back), against the two linear baselines."""
    config = _load(CONFIG)
    settings = config["fit"]
    torch.manual_seed(settings["torch_seed"])
    data = load_boards(directory)
    header = json.loads((directory / "data.json").read_text(encoding="utf-8"))
    cut = [i for i, g in enumerate(header["games"]) if g["stopping_reason"] == "frame_limit"]
    # The empty first board of each game has no piece behind it; a game cut by the frame
    # cap has cut-short targets.
    keep = (data["last"] >= 0) & ~np.isin(data["game"], cut)
    games = int(data["game"].max()) + 1
    split = games - round(games * settings["check_share"])
    train = _tensors(data, keep & (data["game"] < split), device)
    check = _tensors(data, keep & (data["game"] >= split), device)
    cap = config["line_cap"]
    n = len(train["lines"])
    sample = _batch_inputs(train, torch.randint(n, (200_000,), device=device), cap)
    # Only the counts are normalised: the cells and one-hots stay 0 or 1, so a rarely
    # filled cell does not become a huge input.
    mean, std = sample.mean(0), sample.std(0)
    binary = torch.ones(INPUTS, dtype=torch.bool, device=device)
    at = CELLS + native.BOARD_FEATURES
    binary[CELLS:at] = False
    binary[at + 4:at + 6] = False  # lines left, drought
    mean = torch.where(binary, torch.zeros_like(mean), mean)
    std = torch.where(binary | (std < 1e-6), torch.ones_like(std), std)
    model = ValueNet(settings["hidden"], settings["hidden2"], mean, std).to(device)
    y = train["target"].float() / TETRIS_18
    with torch.no_grad():
        model.layers[-1].bias.fill_(y.mean().item())  # start at the mean, not at 0
    steps = settings["epochs"] * n // settings["batch"]
    optimiser = torch.optim.Adam(model.parameters(), lr=settings["lr"])
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, settings["lr"], total_steps=steps)
    tick, log = time.time(), []
    for step in range(steps):
        index = torch.randint(n, (settings["batch"],), device=device)
        loss = torch.nn.functional.mse_loss(model(_batch_inputs(train, index, cap)), y[index])
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        optimiser.step()
        schedule.step()
        if (step + 1) % max(1, steps // 10) == 0:
            log.append({"step": step + 1, "check": _errors(_predict(model, check, cap), check),
                        "seconds": round(time.time() - tick, 1)})
            print(log[-1], file=sys.stderr, flush=True)
    model.eval()
    weights = EXPERIMENT_ROOT / settings["weights_name"].format(directory.name)
    sha = export(model, weights)
    baselines = linear_baselines(train, check, cap)
    errors = {"network": _errors(_predict(model, check, cap), check)} | {
        name: _errors(p, check) for name, p in baselines.items()}
    gain = 1 - errors["network"]["mse"] / errors["linear_013"]["mse"]
    checked = probe(model, config, device)
    return {
        "data": {"directory": str(directory.relative_to(runner.PROJECT_ROOT)),
                 "created_at": header["created_at"], "versions": header["versions"],
                 "games": games, "train_games": split, "train_boards": n,
                 "frame_limit_games_dropped": len(cut),
                 "check_boards": len(check["lines"])},
        "versions": runner._record_versions(), "torch": torch.__version__,
        "settings": settings, "weights": {"path": str(weights.relative_to(runner.PROJECT_ROOT)),
                                          "sha256": sha},
        "unit": "points / 22,800 (a Tetris at level 18)",
        "training_log": log, "check_errors": errors,
        "mse_below_linear_013": round(gain, 4),
        "probe": checked,
        "stop_rule": (f"stop if the network's validation MSE is not at least "
                      f"{settings['min_gain']:.0%} below 013's linear model's, or the probe fails"),
        "stop": bool(gain < settings["min_gain"] or not checked["passes"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment020")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="select the dev and round-0 training seeds")
    commands.add_parser("collect", help="round 0's boards from 015's agent").add_argument(
        "--jobs", type=int, default=30)
    fit = commands.add_parser("fit", help="fit the network to a round's boards")
    fit.add_argument("data", type=Path)
    fit.add_argument("--device", default="cuda:0")
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            _write(SEEDS, select_seeds())
            print(f"Wrote {SEEDS}")
        elif args.command == "collect":
            print(f"Data: {collect(args.jobs)}")
        else:
            found = fit_round(args.data.resolve(), args.device)
            path = EXPERIMENT_ROOT / f"fit_{args.data.resolve().name}.json"
            _write(path, found)
            print(f"Wrote {path}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
