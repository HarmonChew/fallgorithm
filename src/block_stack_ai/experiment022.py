"""Run Experiment 022: score the killscreen's moves by real points to the game's end.

    python -m block_stack_ai.experiment022 dev-check [--part 1|0] [--variant V] [--jobs N]
    python -m block_stack_ai.experiment022 seeds ROUND
    python -m block_stack_ai.experiment022 collect ROUND [--jobs N]
    python -m block_stack_ai.experiment022 fit ROUND [--device cuda:0]
    python -m block_stack_ai.experiment022 dev-check-net ROUND [--part 1|0] [--jobs N]

017's agent picks its level 29+ moves by 10-piece rollouts scored by the hand-built
placement value. 022 keeps that agent below ``playout_from_level`` (39) and from there
scores the commit search's best placements by playouts to the end of the game instead
(native ``playout_game``): fresh pieces placed as the fast agent places them at a commit
decision, until a top-out or the line cap, each worth the real points it earns.
``dev-check`` plays config ``variants`` on one part of Experiment 020's dev seeds, paired
against 015's and 017's stored games there (020's dev_baselines.json).

Step 3 (``step3.md``), train on those scores: ``seeds`` selects a round's fresh seeds,
``collect`` plays the round's games (021's rank agent below level 39, playouts from it,
placed by the round's playout network) and keeps every playout-scored decision's
candidates (021's rows, means in points_unit), ``fit`` fits a killscreen network (021's
shape) to the candidates' means minus their decision's average and reports 021's table
on the held-back games, and ``dev-check-net`` plays 017's and the rank agent with that
network at the killscreen in place of their rollouts, paired against them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from multiprocessing import Pool
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import experiment006, experiment012 as e12, experiment013 as e13, experiment016 as e16
from . import experiment020 as e20, experiment021 as e21, native, runner

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "022-playouts"
CONFIG = EXPERIMENT_ROOT / "config.json"
DATA_ROOT = runner.PROJECT_ROOT / "runs" / "022-data"
LABEL = "fallgorithm022/collect/v{}/{{}}"

_load, _write = e13._load, e13._write


def play(config: dict[str, Any], seed: int, variant: dict[str, Any]) -> dict[str, Any]:
    """One game by 017's agent with ``variant``'s playouts from config
    ``playout_from_level``."""
    if variant["policy"] not in ("rank", "search"):
        raise ValueError(f"unknown playout policy {variant['policy']!r}")
    net = ((runner.PROJECT_ROOT / config["rank_net"]).read_bytes()
           if variant["policy"] == "rank" else None)
    played, _ = native.playout_game(
        net, config["game"], seed, from_level=config["playout_from_level"],
        count=variant["count"], line_cap=config["line_cap"], frame_cap=config["frame_cap"],
        limits=e13._limits(config), params=native.params(e21.agent_params()))
    return played


def dev_game(job: tuple[str, int]) -> dict[str, Any]:
    """One dev game by variant ``name``, replayed for its score by band."""
    name, seed = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played = play(config, seed, config["variants"][name])
    seconds = time.perf_counter() - tick
    return ({"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
             "seconds": seconds} |
            {key: played[key] for key in ("playouts", "playout_pieces", "playouts_cut")} |
            e20._replay(config, seed, played))


def dev_check(jobs: int, part: int = 1, variants: list[str] | None = None) -> dict[str, Any]:
    """Config ``variants`` on one part of 020's dev seeds, paired against 015's and 017's
    agents there."""
    stored = _load(e20.DEV_BASELINES)
    if str(part) not in stored:
        raise ValueError(f"020's dev_baselines.json has no part {part}")
    base = stored[str(part)]
    config = _load(CONFIG)
    chosen = variants or list(config["variants"])
    unknown = [name for name in chosen if name not in config["variants"]]
    if unknown:
        raise ValueError(f"unknown variants {unknown}")
    todo = [(name, seed) for name in chosen for seed in base["seeds"]]
    with Pool(jobs) as pool:
        played = pool.map(dev_game, todo, chunksize=1)
    runs = {name: [g for g in played if g["name"] == name] for name in chosen}
    net = runner.PROJECT_ROOT / config["rank_net"]
    return {
        "question": "017's agent with its level 39+ commit decisions scored by playouts to the "
                    "game's end, against 017's agent, on 020's dev seeds",
        "seeds": f"Experiment 020's dev seeds {part * len(base['seeds'])} to "
                 f"{(part + 1) * len(base['seeds']) - 1}", "games": len(base["seeds"]),
        "versions": runner._record_versions(),
        "rank_net": {"path": config["rank_net"],
                     "sha256": hashlib.sha256(net.read_bytes()).hexdigest()},
        "playout_from_level": config["playout_from_level"],
        "variants": {name: config["variants"][name] for name in chosen},
        "runs": {name: e20.summary(games) for name, games in runs.items()} |
                {name: e20.summary(base["games"][name]) for name in e20.BASELINES},
        "paired": {f"{name} - {other}": {"total": e12.paired(games, base["games"][other]),
                                         "by_band": e16._band_pairs(games, base["games"][other])}
                   for name, games in runs.items() for other in e20.BASELINES},
        "playouts": {name: {key: sum(g[key] for g in games)
                            for key in ("playouts", "playout_pieces", "playouts_cut")}
                     for name, games in runs.items()},
        "per_game": {name: [{key: g[key] for key in ("seed", "score", "lines", "seconds")}
                            for g in games] for name, games in runs.items()},
    }


# ---------------------------------------------------------------- step 3

def seeds_path(round_: int) -> Path:
    return EXPERIMENT_ROOT / f"seeds_round{round_}.json"


def weights_path(round_: int) -> Path:
    return EXPERIMENT_ROOT / _load(CONFIG)["step3"]["fit"]["weights_name"].format(
        f"round{round_}")


def select_seeds(round_: int) -> dict[str, Any]:
    """Fresh seeds for round ``round_``: none of 021's excluded or distil seeds (so none of
    the dev or held-out seeds), nor an earlier round's, nor a native start-state twin of
    any of those or of each other."""
    config = _load(CONFIG)
    excluded = set(_load(e21.SEEDS)["excluded_seeds"]) | set(_load(e21.SEEDS)["distil_seeds"])
    for r in range(1, round_):
        excluded |= set(_load(seeds_path(r))["seeds"])
    excluded = sorted(excluded)
    seen = {experiment006.native_identity(config["game"], seed) for seed in excluded}
    label = LABEL.format(round_)
    selected, index = [], 0
    while len(selected) < config["step3"]["games"]:
        seed = experiment006._label_seed(label, index)
        identity = experiment006.native_identity(config["game"], seed)
        if identity not in seen:
            selected.append(seed)
            seen.add(identity)
        index += 1
    return {"selection": _load(e21.SEEDS)["selection"] + "; also not 021's distil seeds nor "
                         "an earlier round's",
            "label": label.replace("{}", "<index>"), "excluded_seeds": excluded,
            "seeds": selected}


def playout_net(round_: int) -> Path:
    """Round ``round_``'s playout network: 021's rank network, then the round before's."""
    if round_ == 1:
        return runner.PROJECT_ROOT / _load(CONFIG)["rank_net"]
    return weights_path(round_ - 1)


def collect_game(job: tuple[int, int, int]) -> tuple[int, dict[str, Any], np.ndarray]:
    index, seed, round_ = job
    config = _load(CONFIG)
    tick = time.perf_counter()
    played, rows = native.playout_game(
        playout_net(round_).read_bytes(), config["game"], seed,
        from_level=config["playout_from_level"], count=config["step3"]["count"],
        line_cap=config["line_cap"], frame_cap=config["frame_cap"],
        limits=e13._limits(config), params=native.params(e21.agent_params()), dump=True,
        rank=(runner.PROJECT_ROOT / config["rank_net"]).read_bytes())
    rows = [r for r in rows if r[e21.NEXT] == -1 and r[e21.LEVEL] >= config["playout_from_level"]]
    summary = {"index": index, "seed": seed, "score": played["score"],
               "lines": played["lines"], "pieces": played["pieces"],
               "stopping_reason": played["stopping_reason"],
               "playouts_cut": played["playouts_cut"],
               "seconds": round(time.perf_counter() - tick, 1)}
    return index, summary, np.array(rows, dtype=np.float64).reshape(-1, native.RANK_DISTIL_STRIDE)


def collect(round_: int, jobs: int) -> Path:
    """Round ``round_``'s games into ``runs/022-data/round<N>`` (021's layout: games/<i>.npy,
    games.jsonl, data.json); games already there are kept, so a stopped run resumes."""
    config = _load(CONFIG)
    seeds = _load(seeds_path(round_))["seeds"]
    net = playout_net(round_)
    settings = {"params": e21.agent_params(), "features": list(e21.e18.FEATURES),
                "seeds": seeds, "count": config["step3"]["count"],
                "playout_from_level": config["playout_from_level"],
                "rank_net": {"path": config["rank_net"], "sha256": hashlib.sha256(
                    (runner.PROJECT_ROOT / config["rank_net"]).read_bytes()).hexdigest()},
                "playout_net": {"path": str(net.relative_to(runner.PROJECT_ROOT)),
                                "sha256": hashlib.sha256(net.read_bytes()).hexdigest()}}
    directory = DATA_ROOT / f"round{round_}"
    (directory / "games").mkdir(parents=True, exist_ok=True)
    header_path = directory / "data.json"
    header = (json.loads(header_path.read_text(encoding="utf-8")) if header_path.exists()
              else {"created_at": datetime.now(timezone.utc).isoformat()} | settings |
              {"versions_at_start": []})
    if any(header[key] != value for key, value in settings.items()):
        raise ValueError(f"{directory} holds another run")
    header["versions_at_start"].append(runner._record_versions())
    _write(header_path, header)
    log_path = directory / "games.jsonl"
    done = {json.loads(line)["index"] for line in
            (log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else [])}
    todo = [(i, s, round_) for i, s in enumerate(seeds) if i not in done]
    tick = time.time()
    with Pool(jobs) as pool, log_path.open("a", encoding="utf-8") as log:
        for index, summary, rows in pool.imap_unordered(collect_game, todo, chunksize=1):
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


def fit(round_: int, device: str) -> dict[str, Any]:
    """The killscreen network on rounds 1..``round_``'s data (021's fit, one decision kind):
    each candidate's mean minus its decision's average, fitted on every round's first
    games and checked on each round's last ``check_share``."""
    config = _load(CONFIG)
    settings = config["step3"]["fit"]
    torch.manual_seed(settings["torch_seed"])
    runs, parts, fitting = [], [], []
    for r in range(1, round_ + 1):
        directory = DATA_ROOT / f"round{r}"
        header, games, rows, game = e21.load_data(directory)
        if header["params"] != e21.agent_params() or not np.isfinite(rows).all():
            raise ValueError(f"{directory} is not this agent's, or holds a number not finite")
        split = len(games) - round(len(games) * config["step3"]["check_share"])
        runs.append({"directory": str(directory.relative_to(runner.PROJECT_ROOT)),
                     "playout_net": header["playout_net"], "games": len(games),
                     "fit_games": split, "rows": len(rows),
                     "versions_at_end": header.get("versions_at_end"),
                     "mean_score": round(sum(g["score"] for g in games) / len(games), 1)})
        parts.append(rows)
        fitting.append(game < split)
    rows, fitting = np.concatenate(parts), np.concatenate(fitting)
    cap = config["line_cap"]
    train_rows, check_rows = rows[fitting], rows[~fitting]
    train = torch.from_numpy(train_rows).to(device)
    check = torch.from_numpy(check_rows).to(device)
    index, _ = e21._groups(train_rows, device)
    valid = index >= 0
    safe = index.clamp(min=0)
    target = train[:, e21.MEAN][safe] * valid
    centred = (target - target.sum(1, keepdim=True) / valid.sum(1, keepdim=True)) * valid
    scale = centred[valid].std()
    sample = e21.inputs(train[torch.randint(len(train), (200_000,), device=device)], cap)
    mean, std = sample.mean(0), sample.std(0)
    binary = torch.zeros(e21.INPUTS, dtype=torch.bool, device=device)
    binary[e21.BINARY] = True
    mean = torch.where(binary, torch.zeros_like(mean), mean)
    std = torch.where(binary | (std < 1e-6), torch.ones_like(std), std)
    model = e21.e20.ValueNet(settings["hidden"], settings["hidden2"], mean, std,
                             e21.INPUTS).to(device)
    n = len(index)
    steps = settings["epochs"] * n // settings["batch"]
    optimiser = torch.optim.Adam(model.parameters(), lr=settings["lr"])
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, settings["lr"], total_steps=steps)
    tick, log = time.time(), []
    for step in range(steps):
        chosen = torch.randint(n, (settings["batch"],), device=device)
        at, ok = safe[chosen], valid[chosen]
        out = model(e21.inputs(train[at.flatten()], cap)).reshape(at.shape) * ok
        out = (out - out.sum(1, keepdim=True) / ok.sum(1, keepdim=True)) * ok
        loss = (((out - centred[chosen]) / scale) ** 2 * ok).sum() / ok.sum()
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        optimiser.step()
        schedule.step()
        if (step + 1) % max(1, steps // 10) == 0:
            model.eval()
            report = e21.table(check_rows, e21._predict(model, check, cap).cpu().numpy())
            model.train()
            log.append({"step": step + 1, "loss": round(loss.item(), 4),
                        "network_loss": report["commit 39+"]["network_loss"],
                        "seconds": round(time.time() - tick, 1)})
            print(log[-1], file=sys.stderr, flush=True)
    model.eval()
    weights = weights_path(round_)
    sha = e21.export(model, weights)
    scores = e21._predict(model, check, cap).double().cpu().numpy()
    sample_rows = [tuple(r) for r in check_rows[:2000].tolist()]
    native_scores = native.rank_values(weights.read_bytes(), sample_rows, line_cap=cap,
                                       start_level=config["game"]["start_level"])
    checked = e21.table(check_rows, scores)["commit 39+"]
    return {
        "data": {"runs": runs, "fit_decisions": n},
        "versions": runner._record_versions(), "torch": torch.__version__,
        "settings": settings, "target_scale": round(scale.item(), 4),
        "weights": {"path": str(weights.relative_to(runner.PROJECT_ROOT)), "sha256": sha},
        "native_max_difference": max(abs(a - b) for a, b in zip(native_scores, scores)),
        "training_log": log, "checked_games": checked,
        "fitted_games": e21.table(train_rows, e21._predict(model, train, cap).double()
                                  .cpu().numpy())["commit 39+"],
        "units": "points_unit (a Tetris at level 18); losses against the playouts' best",
        "stop_rule": "stop if the network's loss is not below the search's (checked games)",
        "stop": not checked["network_loss"] < checked["search_loss"],
    }


def net_game(job: tuple[str, int, int]) -> dict[str, Any]:
    """One dev game: agent ``name`` (config step3.agents, or a baseline ``rank``) with round
    ``round_``'s killscreen network."""
    name, seed, round_ = job
    config = _load(CONFIG)
    rank = (runner.PROJECT_ROOT / config["rank_net"]).read_bytes()
    args = dict(line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                limits=e13._limits(config), params=native.params(e21.agent_params()))
    tick = time.perf_counter()
    if name == "rank":
        played = native.rank_game(rank, config["game"], seed, **args)
    else:
        played, _ = native.playout_game(
            None, config["game"], seed, from_level=config["playout_from_level"], count=0,
            rank=rank if name == "rank_ks" else None,
            killscreen=weights_path(round_).read_bytes(), **args)
    seconds = time.perf_counter() - tick
    return {"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "seconds": seconds} | e20._replay(config, seed, played)


def dev_check_net(round_: int, jobs: int, part: int = 1) -> dict[str, Any]:
    """017_ks against 017's agent and rank_ks against the rank agent, on one part of 020's
    dev seeds."""
    stored = _load(e20.DEV_BASELINES)
    if str(part) not in stored:
        raise ValueError(f"020's dev_baselines.json has no part {part}")
    base = stored[str(part)]
    names = list(_load(CONFIG)["step3"]["agents"]) + ["rank"]
    with Pool(jobs) as pool:
        played = pool.map(net_game, [(name, seed, round_) for name in names
                                     for seed in base["seeds"]], chunksize=1)
    runs = {name: [g for g in played if g["name"] == name] for name in names}
    runs["017"] = base["games"]["commit_rollout"]
    pairs = {"017_ks - 017": ("017_ks", "017"), "rank_ks - rank": ("rank_ks", "rank")}
    weights = weights_path(round_)
    return {
        "question": "the killscreen network in place of the level 39+ rollouts, against the "
                    "same agents without it, on 020's dev seeds",
        "seeds": f"Experiment 020's dev seeds {part * len(base['seeds'])} to "
                 f"{(part + 1) * len(base['seeds']) - 1}", "games": len(base["seeds"]),
        "versions": runner._record_versions(),
        "weights": {"path": str(weights.relative_to(runner.PROJECT_ROOT)),
                    "sha256": hashlib.sha256(weights.read_bytes()).hexdigest()},
        "runs": {name: e20.summary(games) for name, games in runs.items()},
        "paired": {key: {"total": e12.paired(runs[a], runs[b]),
                         "by_band": e16._band_pairs(runs[a], runs[b])}
                   for key, (a, b) in pairs.items()},
        "per_game": {name: [{key: g[key] for key in ("seed", "score", "lines")} for g in games]
                     for name, games in runs.items() if name != "017"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment022")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("dev-check", help="the playout agents on dev seeds")
    check.add_argument("--part", type=int, choices=(0, 1), default=1)
    check.add_argument("--variant", action="append", dest="variants")
    check.add_argument("--jobs", type=int, default=30)
    for command in ("seeds", "collect", "fit", "dev-check-net"):
        sub = commands.add_parser(command)
        sub.add_argument("round_", type=int, metavar="ROUND")
        if command in ("collect", "dev-check-net"):
            sub.add_argument("--jobs", type=int, default=30)
        if command == "fit":
            sub.add_argument("--device", default="cuda:0")
        if command == "dev-check-net":
            sub.add_argument("--part", type=int, choices=(0, 1), default=1)
    args = parser.parse_args(argv)
    try:
        if getattr(args, "round_", 1) < 1:
            raise ValueError("rounds start at 1")
        if args.command == "seeds":
            path = seeds_path(args.round_)
            if path.exists():
                raise ValueError(f"{path} exists")
            _write(path, select_seeds(args.round_))
            print(f"Wrote {path}")
        elif args.command == "collect":
            print(f"Data: {collect(args.round_, args.jobs)}")
        elif args.command == "fit":
            path = EXPERIMENT_ROOT / f"fit_round{args.round_}.json"
            if path.exists() or weights_path(args.round_).exists():
                raise ValueError(f"{path.name} or its weights exist")
            _write(path, fit(args.round_, args.device))
            print(f"Wrote {path}")
        elif args.command == "dev-check-net":
            path = EXPERIMENT_ROOT / f"dev_check_net_round{args.round_}_part{args.part}.json"
            if path.exists():
                raise ValueError(f"{path} exists")
            _write(path, dev_check_net(args.round_, args.jobs, args.part))
            print(f"Wrote {path}")
        if args.command == "dev-check":
            names = "_".join(args.variants) if args.variants else "all"
            path = EXPERIMENT_ROOT / f"dev_check_{names}_part{args.part}.json"
            if path.exists():
                raise ValueError(f"{path} exists")
            _write(path, dev_check(args.jobs, args.part, args.variants))
            print(f"Wrote {path}")
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
