"""Run Experiment 021: a network that ranks the search's top moves.

    python -m block_stack_ai.experiment021 seeds
    python -m block_stack_ai.experiment021 collect [--jobs N]
    python -m block_stack_ai.experiment021 fit [DATA] [--device cuda:0]
    python -m block_stack_ai.experiment021 dev-check WEIGHTS [--part 0|1] [--jobs N]

017's agent re-ranks the search's best placements by sampled rollouts, ~8 minutes a game.
``collect`` plays 017's agent on fresh distil seeds and keeps, at every rollout-ranked
decision, each candidate's settled board, the decision's pieces, lines and drought, 018's
re-rank features and the rollouts' means (all, even and odd rollouts; native
``rank_distil_game``). Each game is written as it finishes, so a stopped run resumes.
``fit`` fits a network (020's shape, on the board's cells and the numbers of
:func:`inputs`) to each candidate's mean minus its decision's average, on all but the
last ``check_share`` of the games, and reports on those, per decision kind, how often the
network, the search alone and the even rollouts pick the rollouts' best and what each pick
loses against it (018's table; also judged on the odd rollouts alone, which none of the
three saw). ``dev-check`` plays the rank agent (``rank_game``) on Experiment 020's dev
seeds, paired against 015's and 017's agents (020's dev_baselines.json).
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
from . import experiment016 as e16, experiment018 as e18, experiment020 as e20, native, runner

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "021-rank-net"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
DATA_ROOT = runner.PROJECT_ROOT / "runs" / "021-data"
DISTIL_LABEL = "fallgorithm021/distil/v1/{}"
MODELS = e18.MODELS
MAGIC = 0x31323046
HEAD = native.RANK_DISTIL_HEAD
# Rows of native.rank_distil_game: these head columns, the ten columns, the features.
MODEL, LEVEL, RANK, MEAN, EVEN, ODD, PIECE, NEXT, LINES, DROUGHT = range(HEAD)
FEATURES_AT = HEAD + native.WIDTH
# The network's inputs (native rollout.hpp's rank_inputs, after the cells): the re-rank
# features, the model, the current piece and the preview (one-hot each), the lines left
# after the candidate's clear / 100, the level / 10 and the drought.
CELLS = e20.CELLS
DENSE = native.RERANK_FEATURES + 3 + 7 + 7 + 3
INPUTS = CELLS + DENSE
# Inputs that are 0 or 1, left unnormalised: the cells, the flags among the features
# (searched, extra ply, doomed, cleared 1-4) and the one-hots.
_FLAGS = [e18.FEATURES.index(name) for name in
          ("searched", "extra_ply_total", "doomed_total", "cleared_1", "cleared_2",
           "cleared_3", "cleared_4")]
BINARY = sorted(set(range(CELLS)) | {CELLS + k for k in _FLAGS} |
                set(range(CELLS + native.RERANK_FEATURES, CELLS + native.RERANK_FEATURES + 17)))

_load, _write = e13._load, e13._write


def agent_params() -> dict[str, Any]:
    """017's agent (018's teacher)."""
    return e18.agent_params()


# ---------------------------------------------------------------- seeds

def select_seeds() -> dict[str, Any]:
    """Fresh distil seeds: none of Experiments 000-012's, 012's training or held-out, 013's
    dev, 018's distil or 020's dev seeds, nor a native start-state twin of any of those or
    of each other. 020's training seeds are not excluded: they trained a different model,
    and with only 30,720 distinct start states they hold nearly all of them."""
    config = _load(CONFIG)
    used = _load(e12.SEEDS)
    excluded = sorted(set(e12.excluded_seeds()) | set(used["train_seeds"]) |
                      set(used["heldout_seeds"]) | set(_load(e13.SEEDS)["dev_seeds"]) |
                      set(_load(e18.SEEDS)["distil_seeds"]) | set(_load(e20.SEEDS)["dev_seeds"]))
    seen = {experiment006.native_identity(config["game"], seed) for seed in excluded}
    selected, index = [], 0
    while len(selected) < config["distil_games"]:
        seed = experiment006._label_seed(DISTIL_LABEL, index)
        identity = experiment006.native_identity(config["game"], seed)
        if identity not in seen:
            selected.append(seed)
            seen.add(identity)
        index += 1
    return {
        "selection": ("SHA256(<label with index>), first two bytes big-endian; skip any seed "
                      "in the excluded list and any seed whose seed-erased native start state "
                      "matches an excluded or already selected one; no gameplay outcomes "
                      "inspected"),
        "label": DISTIL_LABEL.replace("{}", "<index>"),
        "excluded_seeds": excluded, "distil_seeds": selected,
    }


# ---------------------------------------------------------------- collect

def distil_game(job: tuple[int, int]) -> tuple[int, dict[str, Any], np.ndarray]:
    index, seed = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played, rows = native.rank_distil_game(
        config["game"], seed, line_cap=config["line_cap"], frame_cap=config["frame_cap"],
        limits=e13._limits(config), params=native.params(agent_params()))
    summary = {"index": index, "seed": seed, "score": played["score"],
               "lines": played["lines"], "pieces": played["pieces"],
               "stopping_reason": played["stopping_reason"],
               "seconds": round(time.perf_counter() - tick, 1)}
    return index, summary, np.array(rows, dtype=np.float64).reshape(-1, native.RANK_DISTIL_STRIDE)


def collect(jobs: int, name: str = "pilot") -> Path:
    """The distil games into ``runs/021-data/<name>``: ``games/<index>.npy`` (each game's
    rows), ``games.jsonl`` (each game's result, as they finish) and ``data.json`` (the
    settings and code versions, at the start and at the end). Games already there are
    kept, so a stopped run resumes."""
    seeds = _load(SEEDS)["distil_seeds"]
    directory = DATA_ROOT / name
    (directory / "games").mkdir(parents=True, exist_ok=True)
    header_path = directory / "data.json"
    header = json.loads(header_path.read_text(encoding="utf-8")) if header_path.exists() else {
        "created_at": datetime.now(timezone.utc).isoformat(), "params": agent_params(),
        "features": e18.FEATURES, "seeds": seeds, "versions_at_start": []}
    if header["params"] != agent_params() or header["seeds"] != seeds:
        raise ValueError(f"{directory} holds another run")
    header["versions_at_start"].append(runner._record_versions())
    _write(header_path, header)
    # A game counts as done once its log line is written (after its rows are in place).
    log_path = directory / "games.jsonl"
    done = {json.loads(line)["index"] for line in
            (log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else [])}
    todo = [(i, s) for i, s in enumerate(seeds) if i not in done]
    tick = time.time()
    with Pool(jobs) as pool, log_path.open("a", encoding="utf-8") as log:
        for index, summary, rows in pool.imap_unordered(distil_game, todo, chunksize=1):
            part = directory / "games" / f"{index}.part.npy"
            np.save(part, rows)
            part.replace(directory / "games" / f"{index}.npy")
            log.write(json.dumps(summary) + "\n")
            log.flush()
            done.add(index)
            print(f"{len(done)}/{len(seeds)} games, {time.time() - tick:.0f} s",
                  file=sys.stderr, flush=True)
    header["versions_at_end"] = runner._record_versions()
    _write(header_path, header)
    return directory


def load_data(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray,
                                         np.ndarray]:
    """A complete run: its header, its games (in seed order), all rows and each row's game."""
    header = json.loads((directory / "data.json").read_text(encoding="utf-8"))
    found = {}
    for line in (directory / "games.jsonl").read_text(encoding="utf-8").splitlines():
        game = json.loads(line)
        found[game["index"]] = game
    if sorted(found) != list(range(len(header["seeds"]))):
        raise ValueError(f"{directory} is not complete: {len(found)}/{len(header['seeds'])} games")
    games = [found[i] for i in range(len(header["seeds"]))]
    parts = [np.load(directory / "games" / f"{i}.npy") for i in range(len(games))]
    rows = np.concatenate(parts)
    game = np.concatenate([np.full(len(p), i, dtype=np.int32) for i, p in enumerate(parts)])
    return header, games, rows, game


# ---------------------------------------------------------------- the network

def decision_index(rows: np.ndarray) -> np.ndarray:
    """Each row's decision number (a decision starts at rank 0)."""
    return np.cumsum(rows[:, RANK] == 0) - 1


def inputs(rows: torch.Tensor, line_cap: int) -> torch.Tensor:
    """The network's INPUTS numbers per row, float32 (unnormalised): rank_inputs."""
    n = len(rows)
    every = torch.arange(n, device=rows.device)
    columns = rows[:, HEAD:FEATURES_AT].long()
    cells = (columns[:, :, None] >> torch.arange(20, device=rows.device)) & 1
    out = torch.zeros(n, INPUTS, device=rows.device)
    out[:, :CELLS] = cells.transpose(1, 2).reshape(n, CELLS).float()
    x = rows[:, FEATURES_AT:]
    out[:, CELLS:CELLS + native.RERANK_FEATURES] = x.float()
    at = CELLS + native.RERANK_FEATURES
    out[every, at + rows[:, MODEL].long()] = 1.0
    out[every, at + 3 + rows[:, PIECE].long()] = 1.0
    nxt = rows[:, NEXT].long()
    known = nxt >= 0
    out[every[known], at + 10 + nxt[known]] = 1.0
    cleared = sum(k * x[:, 4 + k] for k in range(1, 5))
    out[:, at + 17] = (line_cap - (rows[:, LINES] + cleared)).clamp(min=0).float() / 100
    out[:, at + 18] = rows[:, LEVEL].float() / 10
    out[:, at + 19] = rows[:, DROUGHT].float()
    return out


def export(model: e20.ValueNet, path: Path) -> str:
    return e20.export(model, path, MAGIC)


def read_export(path: Path) -> e20.ValueNet:
    return e20.read_export(path, MAGIC, INPUTS)


def _first_best(values: list[float]) -> int:
    return e18._first_best(values)


def pick(scores: list[float], searched: int) -> int:
    """rollout.hpp's rank-net choice: the highest score, the search's own choice winning
    ties, otherwise the first (018's rerank_pick)."""
    return e18.rerank_pick(scores, searched)


def table(rows: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    """018's table per decision kind: how often the search, the network (``scores``) and
    the even rollouts pick the rollouts' best (by the full mean), what each pick loses
    against it, and what each loses judged by the odd rollouts alone."""
    starts = np.flatnonzero(rows[:, RANK] == 0).tolist() + [len(rows)]
    totals: dict[tuple[int, str], float] = {}
    count = [0, 0, 0]

    def add(model: int, key: str, value: float) -> None:
        totals[model, key] = totals.get((model, key), 0.0) + value

    for begin, end in zip(starts, starts[1:]):
        if end - begin < 2:
            continue
        model = int(rows[begin, MODEL])
        mean = rows[begin:end, MEAN].tolist()
        odd = rows[begin:end, ODD].tolist()
        searched = int(np.flatnonzero(rows[begin:end, FEATURES_AT] == 1.0)[0])
        picks = {"search": searched, "network": pick(scores[begin:end].tolist(), searched),
                 "even_rollouts": _first_best(rows[begin:end, EVEN].tolist())}
        best, best_odd = _first_best(mean), max(odd)
        count[model] += 1
        for name, chosen in picks.items():
            add(model, f"{name}_agrees", chosen == best)
            add(model, f"{name}_loss", mean[best] - mean[chosen])
            add(model, f"{name}_odd_loss", best_odd - odd[chosen])
    out = {}
    for model, name in enumerate(MODELS):
        n = max(1, count[model])
        out[name] = {"decisions": count[model]} | {
            key: round(totals.get((model, key), 0.0) / n, 4)
            for key in [f"{p}_{k}" for p in ("search", "network", "even_rollouts")
                        for k in ("agrees", "loss", "odd_loss")]}
    return out


def _groups(rows: np.ndarray, device: str) -> tuple[torch.Tensor, torch.Tensor]:
    """The decisions of 2 or more candidates as a padded index (decisions x beam, -1 for
    none) and each decision's model."""
    starts = np.flatnonzero(rows[:, RANK] == 0)
    sizes = np.diff(np.append(starts, len(rows)))
    keep = sizes >= 2
    width = int(sizes.max())
    index = np.full((len(starts), width), -1, dtype=np.int64)
    for k in range(width):
        has = sizes > k
        index[has, k] = starts[has] + k
    return (torch.from_numpy(index[keep]).to(device),
            torch.from_numpy(rows[starts[keep], MODEL].astype(np.int64)).to(device))


def _predict(model: e20.ValueNet, rows: torch.Tensor, line_cap: int,
             batch: int = 65536) -> torch.Tensor:
    with torch.no_grad():
        return torch.cat([model(inputs(rows[i:i + batch], line_cap))
                          for i in range(0, len(rows), batch)])


def fit_run(directory: Path, device: str) -> dict[str, Any]:
    """Fit the network on the first games of a run and report on the rest (step 2)."""
    config = _load(CONFIG)
    settings = config["fit"]
    torch.manual_seed(settings["torch_seed"])
    header, games, rows, game = load_data(directory)
    if header["params"] != agent_params() or list(header["features"]) != list(e18.FEATURES):
        raise ValueError(f"{directory} is not 017's agent with these features")
    if not np.isfinite(rows).all():
        raise ValueError(f"{directory} holds a number that is not finite")
    split = len(games) - round(len(games) * config["check_share"])
    cap = config["line_cap"]
    train_rows, check_rows = rows[game < split], rows[game >= split]
    train = torch.from_numpy(train_rows).to(device)
    check = torch.from_numpy(check_rows).to(device)
    index, kinds = _groups(train_rows, device)
    valid = index >= 0
    safe = index.clamp(min=0)
    target = train[:, MEAN][safe] * valid
    centred = (target - target.sum(1, keepdim=True) / valid.sum(1, keepdim=True)) * valid
    # Each kind's targets in units of its own spread, so the 18-28 decisions (small
    # differences) count as much as the 29+ ones.
    scale = torch.stack([centred[kinds == m][valid[kinds == m]].std() for m in range(3)])
    scale = torch.nan_to_num(scale, nan=1.0)  # a kind with no decisions
    sample = inputs(train[torch.randint(len(train), (200_000,), device=device)], cap)
    mean, std = sample.mean(0), sample.std(0)
    binary = torch.zeros(INPUTS, dtype=torch.bool, device=device)
    binary[BINARY] = True
    mean = torch.where(binary, torch.zeros_like(mean), mean)
    std = torch.where(binary | (std < 1e-6), torch.ones_like(std), std)
    model = e20.ValueNet(settings["hidden"], settings["hidden2"], mean, std, INPUTS).to(device)
    n = len(index)
    steps = settings["epochs"] * n // settings["batch"]
    optimiser = torch.optim.Adam(model.parameters(), lr=settings["lr"])
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, settings["lr"], total_steps=steps)
    tick, log = time.time(), []
    for step in range(steps):
        chosen = torch.randint(n, (settings["batch"],), device=device)
        at, ok = safe[chosen], valid[chosen]
        out = model(inputs(train[at.flatten()], cap)).reshape(at.shape) * ok
        out = (out - out.sum(1, keepdim=True) / ok.sum(1, keepdim=True)) * ok
        error = ((out - centred[chosen]) / scale[kinds[chosen]][:, None]) ** 2 * ok
        loss = error.sum() / ok.sum()
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        optimiser.step()
        schedule.step()
        if (step + 1) % max(1, steps // 10) == 0:
            model.eval()
            report = table(check_rows, _predict(model, check, cap).cpu().numpy())
            model.train()
            log.append({"step": step + 1, "loss": round(loss.item(), 4),
                        "network_loss": {k: v["network_loss"] for k, v in report.items()},
                        "seconds": round(time.time() - tick, 1)})
            print(log[-1], file=sys.stderr, flush=True)
    model.eval()
    weights = EXPERIMENT_ROOT / settings["weights_name"].format(directory.name)
    sha = export(model, weights)
    scores = _predict(model, check, cap).double().cpu().numpy()
    # The C++ network on the first check rows must give the same outputs.
    sample_rows = [tuple(r) for r in check_rows[:2000].tolist()]
    native_scores = native.rank_values(weights.read_bytes(), sample_rows, line_cap=cap,
                                       start_level=config["game"]["start_level"])
    checked = table(check_rows, scores)
    fitted = table(train_rows, _predict(model, train, cap).double().cpu().numpy())
    stop = not all(checked[name]["network_loss"] < checked[name]["search_loss"]
                   for name in MODELS)
    return {
        "data": {"directory": str(directory.relative_to(runner.PROJECT_ROOT)),
                 "created_at": header["created_at"],
                 "versions_at_start": header["versions_at_start"],
                 "versions_at_end": header.get("versions_at_end"),
                 "games": len(games), "fit_games": split, "rows": len(rows),
                 "mean_score": round(sum(g["score"] for g in games) / len(games), 1),
                 "fit_decisions": n},
        "versions": runner._record_versions(), "torch": torch.__version__,
        "settings": settings, "check_share": config["check_share"],
        "target_scale": [round(v, 4) for v in scale.tolist()],
        "weights": {"path": str(weights.relative_to(runner.PROJECT_ROOT)), "sha256": sha},
        "native_max_difference": max(abs(a - b) for a, b in zip(native_scores, scores)),
        "training_log": log, "checked_games": checked, "fitted_games": fitted,
        "stop_rule": "stop if the network's loss is not below the search's in all three "
                     "decision kinds (checked games, full means)",
        "stop": stop,
    }


# ---------------------------------------------------------------- dev check (step 3)

def dev_game(job: tuple[int, str]) -> dict[str, Any]:
    """One dev game by the rank agent with the weights file ``weights`` (relative to the
    project), replayed for its score by band (020's dev_game)."""
    seed, weights = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played = native.rank_game((runner.PROJECT_ROOT / weights).read_bytes(), config["game"],
                              seed, line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                              limits=e13._limits(config), params=native.params(agent_params()))
    seconds = time.perf_counter() - tick
    return {"name": "rank", "seed": seed, "score": played["score"], "lines": played["lines"],
            "seconds": seconds} | e20._replay(config, seed, played)


def dev_check(weights: Path, jobs: int, part: int = 0) -> dict[str, Any]:
    """The rank agent on one part of 020's dev seeds, paired against 015's and 017's
    agents (020's stored games)."""
    stored = _load(e20.DEV_BASELINES)
    if str(part) not in stored:
        raise ValueError(f"020's dev_baselines.json has no part {part}; play it there first")
    base = stored[str(part)]
    relative = str(weights.resolve().relative_to(runner.PROJECT_ROOT))
    with Pool(jobs) as pool:
        games = pool.map(dev_game, [(seed, relative) for seed in base["seeds"]], chunksize=1)
    return {
        "question": "The rank agent against 015's and 017's agents, on 020's dev seeds",
        "seeds": f"Experiment 020's dev seeds {part * len(games)} to "
                 f"{(part + 1) * len(games) - 1}", "games": len(games),
        "versions": runner._record_versions(),
        "weights": {"path": relative, "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
        "runs": {"rank": e20.summary(games)} | {name: e20.summary(base["games"][name])
                                                for name in e20.BASELINES},
        "paired": {f"rank - {name}": {"total": e12.paired(games, base["games"][name]),
                                      "by_band": e16._band_pairs(games, base["games"][name])}
                   for name in e20.BASELINES},
        "per_game": [{key: g[key] for key in ("seed", "score", "lines")} for g in games],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment021")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="select the distil seeds")
    collect_parser = commands.add_parser("collect", help="017's games and their decisions")
    collect_parser.add_argument("--jobs", type=int, default=30)
    fit = commands.add_parser("fit", help="fit the rank network and check it offline")
    fit.add_argument("data", type=Path, nargs="?", default=DATA_ROOT / "pilot")
    fit.add_argument("--device", default="cuda:0")
    check = commands.add_parser("dev-check", help="the rank agent on dev seeds")
    check.add_argument("weights", type=Path)
    check.add_argument("--part", type=int, choices=(0, 1), default=0)
    check.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            _write(SEEDS, select_seeds())
            print(f"Wrote {SEEDS}")
        elif args.command == "collect":
            print(f"Data: {collect(args.jobs)}")
        elif args.command == "fit":
            directory = args.data.resolve()
            path = EXPERIMENT_ROOT / f"fit_{directory.name}.json"
            _write(path, fit_run(directory, args.device))
            print(f"Wrote {path}")
        else:
            path = EXPERIMENT_ROOT / f"dev_check_{args.weights.stem}_part{args.part}.json"
            _write(path, dev_check(args.weights, args.jobs, args.part))
            print(f"Wrote {path}")
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
