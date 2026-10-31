"""Run Experiment 020: a learned value network.

    python -m block_stack_ai.experiment020 seeds [--round R]
    python -m block_stack_ai.experiment020 collect [--round R] [--jobs N]
    python -m block_stack_ai.experiment020 fit DATA [DATA ...] [--device cuda:0]
    python -m block_stack_ai.experiment020 dev-check WEIGHTS [--prefilter K] [--part 0|1] [--jobs N]

``seeds`` selects the new dev seeds (``fallgorithm020/dev/v1``) and round 0's training
seeds (``fallgorithm020/train/v0``). ``collect`` plays 015's agent on the training
seeds, with config.json's light exploration, and keeps every board a piece left
(native ``dump_game``) and the points the game went on to score after it. The data goes
to runs/ (it is large, and each game is a pure function of its seed and settings).
``fit`` fits the value network to a round's boards (PyTorch), writes its weights under
the experiment directory and checks it offline (step 2): validation error against two
baselines, and the probe of 013's failure (taller must be worse). ``dev-check`` plays the
network agent (native/netsearch.hpp) on dev seeds 0-99 (part 0) or 100-199 (part 1), paired
against 015's and 017's agents (their games stored once in dev_baselines.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import experiment006, experiment012 as e12, experiment013 as e13
from . import experiment015 as e15, experiment016 as e16, experiment018 as e18
from . import experiment019 as e19, native, runner
from .engine import EngineError, create_game

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


def draw_round_seeds(round_index: int) -> dict[str, Any]:
    """seeds.json with a later round's training seeds added: fresh labels, but start
    states may repeat earlier rounds' training ones (never a dev, held-out or excluded one,
    nor one of an earlier round's check games, held back by ``fit``); see config.json's
    seeds_note."""
    stored = _load(SEEDS)
    if round_index < 1 or str(round_index) in stored["train_seeds"]:
        raise ValueError(f"round {round_index}'s seeds are already chosen (or are round 0's)")
    share = _load(CONFIG)["fit"]["check_share"]
    checked = [seed for seeds in stored["train_seeds"].values()
               for seed in seeds[len(seeds) - round(len(seeds) * share):]]
    seen = {_identity(seed) for seed in stored["excluded_seeds"] + stored["dev_seeds"] + checked}
    stored["train_seeds"][str(round_index)] = _draw(
        TRAIN_LABEL.format(round_index, "{}"), _load(CONFIG)[f"round{round_index}"]["games"], seen)
    return stored


def round_seeds(round_index: int) -> list[int]:
    found = _load(SEEDS)["train_seeds"].get(str(round_index))
    if found is None:
        raise ValueError(f"no seeds for round {round_index}: run `seeds --round {round_index}`")
    return found


def dump_game(job: tuple[int, int, int, dict[str, Any]]) -> tuple[int, dict[str, Any], bytes]:
    """One training game and its boards: round 0 by 015's agent, a later round by the
    network agent with that round's weights and prefilter; both with exploration."""
    round_index, index, seed, config = job
    settings = config[f"round{round_index}"]
    explore = {"explore": settings["explore"], "explore_start": settings["explore_start"],
               "explore_seed": round_index << 16 | seed}
    common = {"line_cap": config["line_cap"], "frame_cap": config["frame_cap"],
              "limits": _limits(config), "params": native.params(e16.fast_deep_params())}
    tick = time.perf_counter()
    if round_index == 0:
        played, rows = native.dump_game(e16.KINDS["fast_deep"], config["game"], seed,
                                        **common, **explore)
    else:
        played, rows = native.net_game(
            (runner.PROJECT_ROOT / settings["weights"]).read_bytes(), config["game"], seed,
            prefilter=settings["prefilter"], dump=True, **common, **explore)
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


def collect(round_index: int, jobs: int) -> Path:
    """A round's data: ``boards.npz`` (every game's boards, in seed order) and
    ``data.json`` (the settings, code versions and each game's result)."""
    config = _load(CONFIG)
    seeds = round_seeds(round_index)
    directory = DATA_ROOT / f"round{round_index}"
    directory.mkdir(parents=True, exist_ok=False)
    tick = time.time()
    parts, games = [], []
    with Pool(jobs) as pool:
        for index, summary, rows in pool.imap(dump_game, [(round_index, i, s, config)
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
              "versions": runner._record_versions(), "round": round_index,
              "params": e16.fast_deep_params(), "settings": config[f"round{round_index}"],
              "weights_sha256": None if round_index == 0 else hashlib.sha256(
                  (runner.PROJECT_ROOT / config[f"round{round_index}"]["weights"]).read_bytes()
              ).hexdigest(),
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
    """INPUTS (or ``inputs``) -> hidden -> hidden2 -> 1 with ReLUs, inputs normalised by
    fixed numbers."""

    def __init__(self, hidden: int, hidden2: int, mean: torch.Tensor, std: torch.Tensor,
                 inputs: int = INPUTS):
        super().__init__()
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(inputs, hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, hidden2),
            torch.nn.ReLU(), torch.nn.Linear(hidden2, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers((x - self.mean) / self.std).squeeze(1)


def export(model: ValueNet, path: Path, magic: int = 0x30323046) -> str:
    """The weights as native/net.hpp reads them, normalisation folded into the first
    layer: a header of int32 (``magic``, the inputs, hidden, hidden2), then float32
    first-layer rows (one per input), its biases, the second layer's rows (one per output),
    its biases, the output weights and bias. Returns the file's sha256."""
    first, _, second, _, third = model.layers
    with torch.no_grad():
        w1 = (first.weight / model.std).double()  # hidden x INPUTS
        b1 = first.bias.double() - (w1 * model.mean.double()).sum(1)
        parts = [w1.T, b1, second.weight.double(), second.bias.double(),
                 third.weight.double().squeeze(0), third.bias.double()]
    header = np.array([magic, first.in_features, first.out_features, second.out_features],
                      np.int32)
    data = header.tobytes() + b"".join(p.float().cpu().numpy().astype("<f4").tobytes()
                                       for p in parts)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_export(path: Path, magic: int = 0x30323046, inputs: int = INPUTS) -> ValueNet:
    """A ValueNet with an exported file's weights (mean 0, std 1: folded)."""
    data = path.read_bytes()
    found, n_in, hidden, hidden2 = np.frombuffer(data[:16], "<i4")
    if found != magic or n_in != inputs:
        raise ValueError(f"{path} is not a network for these inputs")
    numbers = torch.from_numpy(np.frombuffer(data[16:], "<f4").copy())
    model = ValueNet(int(hidden), int(hidden2), torch.zeros(inputs), torch.ones(inputs), inputs)
    first, _, second, _, third = model.layers
    sizes = [inputs * hidden, hidden, hidden * hidden2, hidden2, hidden2, 1]
    if sum(sizes) != len(numbers):
        raise ValueError(f"{path} has the wrong length")
    chunks = torch.split(numbers, sizes)
    with torch.no_grad():
        first.weight.copy_(chunks[0].reshape(inputs, hidden).T)
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


def fit_round(directories: list[Path], device: str) -> dict[str, Any]:
    """Fit the network on one or more rounds' boards; validation on the last
    ``check_share`` of each round's games (whole games held back), against the two linear
    baselines."""
    config = _load(CONFIG)
    settings = config["fit"]
    torch.manual_seed(settings["torch_seed"])
    parts, headers, offset, cut, split_games = [], [], 0, 0, 0
    for directory in directories:
        data = load_boards(directory)
        header = json.loads((directory / "data.json").read_text(encoding="utf-8"))
        frame_cut = [i for i, g in enumerate(header["games"])
                     if g["stopping_reason"] == "frame_limit"]
        games = len(header["games"])
        split = games - round(games * settings["check_share"])
        # The empty first board of each game has no piece behind it; a game cut by the
        # frame cap has cut-short targets.
        data["keep"] = (data["last"] >= 0) & ~np.isin(data["game"], frame_cut)
        data["checked"] = data["game"] >= split
        data["game"] = data["game"] + offset
        parts.append(data)
        headers.append(header)
        offset, cut, split_games = offset + games, cut + len(frame_cut), split_games + split
    data = {key: np.concatenate([p[key] for p in parts]) for key in parts[0]}
    games = offset
    train = _tensors(data, data["keep"] & ~data["checked"], device)
    check = _tensors(data, data["keep"] & data["checked"], device)
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
    weights = EXPERIMENT_ROOT / settings["weights_name"].format(directories[-1].name)
    sha = export(model, weights)
    baselines = linear_baselines(train, check, cap)
    errors = {"network": _errors(_predict(model, check, cap), check)} | {
        name: _errors(p, check) for name, p in baselines.items()}
    gain = 1 - errors["network"]["mse"] / errors["linear_013"]["mse"]
    checked = probe(model, config, device)
    return {
        "data": {"directories": [str(d.relative_to(runner.PROJECT_ROOT)) for d in directories],
                 "created_at": [h["created_at"] for h in headers],
                 "versions": [h["versions"] for h in headers],
                 "games": games, "train_games": split_games, "train_boards": n,
                 "frame_limit_games_dropped": cut,
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


# ---------------------------------------------------------------- dev check (step 3)

DEV_BASELINES = EXPERIMENT_ROOT / "dev_baselines.json"
BASELINES = ("fast_deep", "commit_rollout")  # 015's agent and 017's
BANDS = e16.BANDS


def baseline_numbers(name: str) -> dict[str, Any]:
    return e16.fast_deep_params() if name == "fast_deep" else e19.commit_rollout_params()


def dev_seeds(part: int) -> list[int]:
    """Dev seeds 0-99 (part 0, for comparisons) or 100-199 (part 1, to confirm a keeper)."""
    games = _load(CONFIG)["dev_games"]
    return _load(SEEDS)["dev_seeds"][part * games:(part + 1) * games]


def _replay(config: dict[str, Any], seed: int, played: dict[str, Any]) -> dict[str, Any]:
    """A C++ game replayed on the Python binding: its score by the band of the level at
    each piece's spawn (016's rule) and the lines it cleared by Tetrises."""
    score: Counter[str] = Counter()
    count, band = -1, BANDS[0]
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in played["inputs"]:
            if state.phase == "active" and state.piece_count != count:
                count, band = state.piece_count, e15._band(state.level)
            before = state.score
            state, _ = game.step(mask)
            score[band] += state.score - before
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"seed {seed}: the replay does not match the C++ game")
    return {"bands": {b: score[b] for b in BANDS},
            "tetris_lines": 4 * state.stats.clear_counts["four_line"]}


def dev_game(job: tuple[str, int, str | None, int]) -> dict[str, Any]:
    """One dev game by a baseline (``weights`` None) or the network agent with the weights
    file ``weights`` (relative to the project) and ``prefilter``."""
    name, seed, weights, prefilter = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    if weights is None:
        played = native.play_game_ex(
            e16.KINDS["fast_deep"] if name == "fast_deep" else "reach_plan_016",
            config["game"], seed, line_cap=config["line_cap"], frame_cap=config["frame_cap"],
            limits=_limits(config), params=native.params(baseline_numbers(name)))
    else:
        played, _ = native.net_game((runner.PROJECT_ROOT / weights).read_bytes(),
                                    config["game"], seed, line_cap=config["line_cap"],
                                    frame_cap=config["frame_cap"], limits=_limits(config),
                                    params=native.params(e16.fast_deep_params()),
                                    prefilter=prefilter)
    seconds = time.perf_counter() - tick
    return {"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "seconds": seconds} | _replay(config, seed, played)


def summary(games: list[dict[str, Any]]) -> dict[str, Any]:
    return e16._summary(games) | {"tetris_rate": round(
        sum(g["tetris_lines"] for g in games) / max(1, sum(g["lines"] for g in games)), 4)}


def dev_baselines(jobs: int, part: int) -> dict[str, Any]:
    """015's and 017's agents on one part of the dev seeds (stored once, in
    dev_baselines.json, since neither changes)."""
    stored = _load(DEV_BASELINES) if DEV_BASELINES.exists() else {}
    if str(part) not in stored:
        seeds = dev_seeds(part)
        with Pool(jobs) as pool:
            found = pool.map(dev_game, [(name, seed, None, 0) for name in reversed(BASELINES)
                                        for seed in seeds], chunksize=1)
        stored[str(part)] = {"seeds": seeds, "versions": runner._record_versions(),
                             "games": {name: [g for g in found if g["name"] == name]
                                       for name in BASELINES}}
        _write(DEV_BASELINES, stored)
    return stored[str(part)]


def dev_check(weights: Path, prefilter: int, jobs: int, part: int = 0) -> dict[str, Any]:
    """The network agent with ``weights`` and ``prefilter`` (0: none) on one part of the dev
    seeds, paired against 015's and 017's agents. A diagnostic, not part of the success
    rule."""
    relative = str(weights.resolve().relative_to(runner.PROJECT_ROOT))
    base = dev_baselines(jobs, part)
    with Pool(jobs) as pool:
        games = pool.map(dev_game, [("net", seed, relative, prefilter) for seed in base["seeds"]],
                         chunksize=1)
    return {
        "question": "The network agent against 015's and 017's agents, on the dev seeds",
        "seeds": f"Experiment 020's dev seeds {part * len(games)} to "
                 f"{(part + 1) * len(games) - 1}", "games": len(games),
        "versions": runner._record_versions(),
        "prefilter": prefilter, "weights": {"path": relative,
                    "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
        "runs": {"net": summary(games)} | {name: summary(base["games"][name])
                                           for name in BASELINES},
        "paired": {f"net - {name}": {"total": e12.paired(games, base["games"][name]),
                                     "by_band": e16._band_pairs(games, base["games"][name])}
                   for name in BASELINES},
        "per_game": [{key: g[key] for key in ("seed", "score", "lines")} for g in games],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment020")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="select the dev and round-0 training seeds (or a "
                        "later round's)").add_argument("--round", type=int, default=0)
    collect_parser = commands.add_parser("collect", help="a round's training boards")
    collect_parser.add_argument("--round", type=int, default=0)
    collect_parser.add_argument("--jobs", type=int, default=30)
    fit = commands.add_parser("fit", help="fit the network to a round's boards")
    fit.add_argument("data", type=Path, nargs="+")
    fit.add_argument("--device", default="cuda:0")
    check = commands.add_parser("dev-check", help="the network agent on dev seeds")
    check.add_argument("weights", type=Path)
    check.add_argument("--prefilter", type=int, default=0)
    check.add_argument("--part", type=int, choices=(0, 1), default=0)
    check.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            _write(SEEDS, select_seeds() if args.round == 0 else draw_round_seeds(args.round))
            print(f"Wrote {SEEDS}")
        elif args.command == "collect":
            print(f"Data: {collect(args.round, args.jobs)}")
        elif args.command == "dev-check":
            path = EXPERIMENT_ROOT / (f"dev_check_{args.weights.stem}_k{args.prefilter}"
                                      f"_part{args.part}.json")
            _write(path, dev_check(args.weights, args.prefilter, args.jobs, args.part))
            print(f"Wrote {path}")
        else:
            directories = [d.resolve() for d in args.data]
            found = fit_round(directories, args.device)
            path = EXPERIMENT_ROOT / f"fit_{directories[-1].name}.json"
            _write(path, found)
            print(f"Wrote {path}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
