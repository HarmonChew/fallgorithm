"""Experiment 037: longer-horizon targets for the 20 Hz networks
(experiments/037-longer-horizon-targets/plan.md).

Step 0 (this module so far): the offline lambda check. No games are played. For each
network (V29 at 230-319, V18 below 230) one sweep's training set is built from 036's stored
rounds with 036's recipe (backup2 k 4 under ``v36``'s network, a third of the played
boards' children, the hand-over value of 036), the backups once; only the played rows'
lambda-returns change with lambda. A network is fitted from ``v36``'s for each lambda (036's
fit settings, one torch seed) and valued on a later round's boards against their actual
rest of game.

    python -m block_stack_ai.experiment037 step0 [--jobs N] [--device D]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch

from . import experiment020 as e20, experiment023 as e23, experiment030 as e30
from . import experiment033 as e33, experiment034 as e34, experiment036 as e36
from . import native, runner

OUT = runner.PROJECT_ROOT / "experiments" / "037-longer-horizon-targets"
DATA = runner.PROJECT_ROOT / "runs" / "037-data"
STEP0 = OUT / "step0.json"
TETRIS_18 = e36.TETRIS_18
KEYS = e36.KEYS
LAMBDAS = (0.95, 0.98, 0.99, 1.0)
BASE_LAMBDA = 0.95
BIAS_SHARE, RMS_SLACK = 1 / 3, 1.05
TORCH_SEED_OFFSET = 37_000

V36_EARLY = "experiments/036-20hz-full-reteach/stage2/value_sweep2.bin"  # v36's V18@20
V36_MID = "experiments/036-20hz-full-reteach/stage3/value_sweep1.bin"    # v36's V29@20

# the step 0 setting of each network: 036's stage whose rounds it uses, the rounds trained
# on (round 0 without its check seeds first), the round tested on, the band, the test's
# line limit and the risky / safe boards (features: 0 holes, 3 aggregate height, 5 max
# height; ``drought`` the I drought at the board)
NETWORKS: dict[str, dict[str, Any]] = {
    "V29": {"stage": 3, "previous": V36_MID, "train": (0, 1, 2, 3), "test": 4,
            "band": (e36.MID_FROM, e36.LATE_FROM), "test_below": e36.LATE_FROM,
            "risky": "I drought 16+ or max height 12+",
            "safe": "I drought under 10, max height under 10, no holes"},
    "V18": {"stage": 2, "previous": V36_EARLY, "train": (0, 1, 2), "test": 3,
            "band": (0, e36.MID_FROM), "test_below": 130,
            "risky": "10+ holes", "safe": "no holes"},
}


def _risky_safe(name: str, d: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    holes, top, drought = d["features"][:, 0], d["features"][:, 5], d["drought"]
    if name == "V29":
        return (drought >= 16) | (top >= 12), (drought < 10) & (top < 10) & (holes == 0)
    return holes >= 10, holes == 0


def _handover(name: str, jobs: int) -> Callable[[np.ndarray], np.ndarray]:
    """036's hand-over value: V29 max(0, c x V39' backup2); V18 the backup2 of ``v36``'s
    V29@20."""
    if name == "V29":
        c = e34.scale()
        return lambda rows: e34.scaled(e36.targets(e36._path(e36.LATE), rows, e36.DEPTH,
                                                   jobs)[0], c)
    mid = e36._path(V36_MID)
    return lambda rows: e36.targets(mid, rows, e36.DEPTH, jobs)[0]


def training_parts(name: str) -> list[dict[str, np.ndarray]]:
    net = NETWORKS[name]
    stage = net["stage"]
    zero = e23._load_npz(e36._round_path(stage, 0))
    held = np.isin(zero["seed"], np.array(e36.round_seeds(stage, 0)[:e36.CHECK_SEEDS]))
    return [e33._split(zero, ~held)] + [e23._load_npz(e36._round_path(stage, k))
                                         for k in net["train"][1:]]


def base_rows(name: str, jobs: int) -> dict[str, Any]:
    """The lambda-free part of the training set: per part the played boards' backups
    (hand-over boards valued by the hand-over), and the children rows with their targets
    (036's ``build_targets`` with the returns left out)."""
    net = NETWORKS[name]
    previous = e36._path(net["previous"])
    split = net["band"][1]
    handover = _handover(name, jobs)
    rng = np.random.default_rng(TORCH_SEED_OFFSET + net["stage"])
    parts, backups, played, kid_boards, goals = training_parts(name), [], [], [], []
    for part in parts:
        rows = e23._rows(part)
        below = part["lines"] < split
        backup = np.zeros(len(rows))
        backup[below], _ = e36.targets(previous, rows[below], e36.DEPTH, jobs)
        if (~below).any():
            backup[~below] = handover(rows[~below])
        backups.append(backup)
        played.append({key: part[key][below] for key in KEYS})
        pick = rng.random(int(below.sum())) < e36.CHILD_SHARE
        _, kids = e36.targets(previous, rows[below][pick], 1, jobs, children=True)
        low = kids[:, native.WIDTH] < split
        for subset, is_low in ((kids[low], True), (kids[~low], False)):
            if not len(subset):
                continue
            values = (e36.targets(previous, subset, e36.DEPTH, jobs)[0] if is_low
                      else handover(subset))
            kid_boards.append(e23._boards(subset))
            goals.append(values)
    return {"parts": parts, "backups": backups, "child_boards": kid_boards,
            "played_boards": played, "child_goals": goals, "split": split}


def returns(base: dict[str, Any], lam: float) -> np.ndarray:
    return np.concatenate([e30.handover_returns(b, part, lam, late_from=base["split"])
                           for b, part in zip(base["backups"], base["parts"])])


def fit(name: str, base: dict[str, Any], lam: float, device: str) -> tuple[e20.ValueNet, list]:
    boards = base["played_boards"] + base["child_boards"]
    data = {key: np.concatenate([b[key] for b in boards]) for key in KEYS}
    goal = np.concatenate([returns(base, lam)] + base["child_goals"])
    settings = e36._load(e23.CONFIG)["fit"]
    torch.manual_seed(settings["torch_seed"] + TORCH_SEED_OFFSET)
    model = e20.read_export(e36._path(NETWORKS[name]["previous"])).to(device)
    log = e23._fit(model, e23._tensors(data, goal, device), settings,
                   e33._config()["line_cap"])
    return model, log


def evaluate(name: str, model: e20.ValueNet, test: dict[str, np.ndarray],
             device: str) -> dict[str, Any]:
    """The fitted network on the test round's band boards against their actual rest of
    game: the risk bias (risky minus safe mean error), rms, and errors by 10-line step."""
    net = NETWORKS[name]
    lo, hi = net["band"][0], net["test_below"]
    keep = (test["lines"] >= lo) & (test["lines"] < hi)
    d = e33._split(test, keep)
    value = e23._predict(model, e23._tensors({k: d[k] for k in KEYS}, np.zeros(len(d["lines"])),
                                             device), e33._config()["line_cap"]).cpu().numpy()
    error = value - (d["final"] - d["score"]) / TETRIS_18
    risky, safe = _risky_safe(name, d)
    return {"boards": int(len(error)), "risky_boards": int(risky.sum()),
            "safe_boards": int(safe.sum()),
            "mean_error_risky": round(float(error[risky].mean()), 3),
            "mean_error_safe": round(float(error[safe].mean()), 3),
            "risk_bias": round(float(error[risky].mean() - error[safe].mean()), 3),
            "rms": round(float(np.sqrt((error ** 2).mean())), 3),
            "mean_error": round(float(error.mean()), 3),
            "mean_error_by_10_lines": {
                f"{s}-{s + 9}": round(float(error[(d["lines"] >= s) & (d["lines"] < s + 10)].mean()), 3)
                for s in range(lo, hi, 10) if ((d["lines"] >= s) & (d["lines"] < s + 10)).any()}}


def pick_lambda(rows: dict[str, dict[str, Any]]) -> float | None:
    """The smallest lambda above 0.95 whose risk bias is at most a third of 0.95's in size
    and whose rms is at most 5% above 0.95's; None if there is none."""
    base = rows[str(BASE_LAMBDA)]
    for lam in LAMBDAS[1:]:
        r = rows[str(lam)]
        if abs(r["risk_bias"]) <= BIAS_SHARE * abs(base["risk_bias"]) and \
                r["rms"] <= RMS_SLACK * base["rms"]:
            return lam
    return None


def step0(jobs: int, device: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "experiment": OUT.name, "step": 0, "created_at": datetime.now(timezone.utc).isoformat(),
        "rule": " ".join(pick_lambda.__doc__.split()), "lambdas": list(LAMBDAS),
        "library": e36.library_record(), "versions": runner._record_versions(),
        "unit": "Tetrises at level 18 (22,800 points)", "networks": {}}
    for name, net in NETWORKS.items():
        tick = time.time()
        base = base_rows(name, jobs)
        test = e23._load_npz(e36._round_path(net["stage"], net["test"]))
        rows: dict[str, Any] = {}
        before = evaluate(name, e20.read_export(e36._path(net["previous"])).to(device), test,
                          device)
        for lam in LAMBDAS:
            model, log = fit(name, base, lam, device)
            rows[str(lam)] = evaluate(name, model, test, device) | {"final_loss": log[-1]["loss"]}
            print(name, lam, rows[str(lam)]["risk_bias"], rows[str(lam)]["rms"],
                  file=sys.stderr, flush=True)
        chosen = pick_lambda(rows)
        result["networks"][name] = {
            "setting": {k: (list(v) if isinstance(v, tuple) else v) for k, v in net.items()},
            "played_rows": int(sum(len(b["lines"]) for b in base["played_boards"])),
            "child_rows": int(sum(len(g) for g in base["child_goals"])),
            "previous_on_test": before, "by_lambda": rows, "lambda": chosen,
            "seconds": round(time.time() - tick, 1)}
        print(name, "lambda", chosen, file=sys.stderr, flush=True)
    result["go"] = any(n["lambda"] is not None for n in result["networks"].values())
    OUT.mkdir(parents=True, exist_ok=True)
    STEP0.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment037")
    commands = parser.add_subparsers(dest="command", required=True)
    s0 = commands.add_parser("step0", help="the offline lambda check (no games)")
    s0.add_argument("--jobs", type=int, default=28)
    s0.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args(argv)
    found = step0(args.jobs, args.device)
    for name, n in found["networks"].items():
        print(name, "lambda", n["lambda"], {k: (v["risk_bias"], v["rms"])
                                             for k, v in n["by_lambda"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
