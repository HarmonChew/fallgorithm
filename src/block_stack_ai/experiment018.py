"""Run Experiment 018: distil the rollouts into a fast re-ranker.

    python -m block_stack_ai.experiment018 seeds
    python -m block_stack_ai.experiment018 collect [--jobs N]
    python -m block_stack_ai.experiment018 fit DATA
    python -m block_stack_ai.experiment018 dev-check [--jobs N]

017's agent re-ranks the search's best placements by sampled rollouts, ~8 minutes a game.
``collect`` plays 017's agent on fresh distil seeds and keeps, at every rollout-ranked
decision, each candidate's features and the rollouts' mean return (native/rollout.hpp's
DistilRow); the data goes to runs/ (it is large, and each game is a pure function of its
seed). ``fit`` fits one linear score per decision kind to those means, by least squares
within each decision (only the differences between a decision's candidates matter), on
the first ``fit_games`` games, and reports on the rest how often the score picks the
rollouts' choice and what each pick loses against it, next to the search alone. ``dev-check``
plays the re-rank agent (``reach_plan_018``) on the dev seeds, paired against 015's agent.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment006, experiment012 as e12, experiment013 as e13
from . import experiment015 as e15, experiment016 as e16, experiment017 as e17, native, runner
from .engine import EngineError, create_game
from .limits import Limits

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "018-distil-rollouts"
CONFIG = EXPERIMENT_ROOT / "config.json"
SEEDS = EXPERIMENT_ROOT / "seeds.json"
RERANK = EXPERIMENT_ROOT / "rerank.json"
DEV_CHECK = EXPERIMENT_ROOT / "dev_check.json"
DISTIL_LABEL = "fallgorithm018/distil/v1/{}"
MODELS = ("preview 18-28", "commit 29-38", "commit 39+")
FEATURES = ("searched", "search_total", "extra_ply_total", "doomed_total", "own_value",
            "cleared_1", "cleared_2", "cleared_3", "cleared_4", "holes", "hole_rows",
            "hole_depth", "aggregate_height", "bumpiness", "max_height", "max_height_above_10",
            "row_transitions", "column_transitions", "well_depth", "well_reserve",
            "well_height", "edge_depth", "pits", "height_10", "height_13", "height_15",
            "height_17")
BANDS = e16.BANDS

_load, _write = e13._load, e13._write


def agent_params() -> dict[str, Any]:
    """017's agent: 015's numbers, 016's rollouts and 017's commit rollouts."""
    return e17.rollout_params() | e17._load(e17.CONFIG)["commit_rollout"]


# ---------------------------------------------------------------- seeds

def select_seeds() -> dict[str, Any]:
    """Fresh distil seeds: none used by Experiments 000-012, nor 012's or 013's seeds, nor
    a native start-state twin of any of those or of each other."""
    config = _load(CONFIG)
    used = _load(e12.SEEDS)
    excluded = sorted(set(e12.excluded_seeds()) | set(used["train_seeds"]) |
                      set(used["heldout_seeds"]) | set(_load(e13.SEEDS)["dev_seeds"]))
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
                      "used by Experiments 000-012, 012's training and held-out seeds, 013's "
                      "dev seeds, and any seed whose seed-erased native start state matches an "
                      "excluded or already selected one; no gameplay outcomes inspected"),
        "label": DISTIL_LABEL.replace("{}", "<index>"),
        "excluded_seeds": excluded, "distil_seeds": selected,
    }


# ---------------------------------------------------------------- collect

def _limits(config: dict[str, Any], reaction_ms: int | None = None) -> Limits:
    fmt = config["formats"][0]
    return Limits(fmt["tap_hz"], fmt["reaction_ms"] if reaction_ms is None else reaction_ms)


def distil_game(seed: int) -> dict[str, Any]:
    """One distil game by 017's agent and its rows."""
    config = _load(CONFIG)
    tick = time.perf_counter()
    played, rows = native.distil_game(config["game"], seed, line_cap=config["line_cap"],
                                      frame_cap=config["frame_cap"], limits=_limits(config),
                                      params=native.params(agent_params()))
    return {"seed": seed, "score": played["score"], "lines": played["lines"],
            "seconds": round(time.perf_counter() - tick, 1), "rows": rows}


def collect(jobs: int) -> Path:
    """The distil games, one line each, written as they finish (in seed order), after a
    first line describing the run; see :func:`load_data`."""
    seeds = _load(SEEDS)["distil_seeds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = runner.PROJECT_ROOT / "runs" / f"{stamp}-018-distil"
    directory.mkdir(parents=True)
    path = directory / "data.jsonl.gz"
    header = {"created_at": datetime.now(timezone.utc).isoformat(),
              "versions": runner._record_versions(), "params": agent_params(),
              "features": FEATURES, "seeds": seeds}
    with gzip.open(path, "wt", encoding="utf-8") as handle, Pool(jobs) as pool:
        handle.write(json.dumps(header, separators=(",", ":")) + "\n")
        for game in pool.imap(distil_game, seeds, chunksize=1):
            handle.write(json.dumps(game, separators=(",", ":")) + "\n")
            handle.flush()
    return path


def load_data(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """A collect run's description and its games."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header, *games = (json.loads(line) for line in handle)
    return header, games


# ---------------------------------------------------------------- fit

def decisions(rows: list[list[float]]) -> list[tuple[int, list[float], list[list[float]]]]:
    """A game's rows grouped by decision: (model, the rollouts' means, the features)."""
    out: list[tuple[int, list[float], list[list[float]]]] = []
    for row in rows:
        model, _, rank, mean, *x = row
        if rank == 0:
            out.append((int(model), [], []))
        out[-1][1].append(mean)
        out[-1][2].append(list(x))
    return out


def _first_best(values: list[float]) -> int:
    best = 0
    for index, value in enumerate(values):
        if value > values[best]:
            best = index
    return best


def dot(w: list[float], x: list[float]) -> float:
    """rollout.hpp's score: added left to right, one term at a time (not ``sum``, which
    compensates its rounding in Python 3.12)."""
    total = 0.0
    for a, b in zip(w, x):
        total += a * b
    return total


def rerank_pick(scores: list[float], searched: int) -> int:
    """rollout.hpp's re-rank choice: the highest score, the search's own choice winning
    ties, otherwise the first."""
    best = 0
    for index, value in enumerate(scores):
        if value > scores[best] or (value == scores[best] and index == searched):
            best = index
    return best


def fit(groups: list[tuple[int, list[float], list[list[float]]]], ridge: float) -> list[float]:
    """Least squares of each candidate's mean on its features, both centred within its
    decision, one weight vector per model; :data:`native.RERANK_WEIGHTS` numbers."""
    n = native.RERANK_FEATURES
    weights: list[float] = []
    for model in range(len(MODELS)):
        gram, target = [0.0] * (n * n), [0.0] * n
        for kind, means, xs in groups:
            if kind != model:
                continue
            y_bar = sum(means) / len(means)
            x_bar = [sum(x[k] for x in xs) / len(xs) for k in range(n)]
            for mean, x in zip(means, xs):
                d = [x[k] - x_bar[k] for k in range(n)]
                for i in range(n):
                    target[i] += d[i] * (mean - y_bar)
                    for j in range(n):
                        gram[i * n + j] += d[i] * d[j]
        weights += e13.solve(gram, target, ridge)
    return weights


def score(groups: list[tuple[int, list[float], list[list[float]]]],
          weights: list[float]) -> dict[str, Any]:
    """Per model: decisions, how often the search's own choice and the fitted score's pick
    are the rollouts' best, and the mean return each loses against the rollouts' best."""
    n = native.RERANK_FEATURES
    totals: Counter[str] = Counter()
    for model, means, xs in groups:
        w = weights[model * n:(model + 1) * n]
        best = _first_best(means)
        searched = next(i for i, x in enumerate(xs) if x[0] == 1.0)
        pick = rerank_pick([dot(w, x) for x in xs], searched)
        totals[f"{model}|decisions"] += 1
        totals[f"{model}|search_agrees"] += best == searched
        totals[f"{model}|rerank_agrees"] += best == pick
        totals[f"{model}|search_loss"] += means[best] - means[searched]
        totals[f"{model}|rerank_loss"] += means[best] - means[pick]
    out = {}
    for model, name in enumerate(MODELS):
        count = max(1, totals[f"{model}|decisions"])
        out[name] = {"decisions": totals[f"{model}|decisions"]} | {
            key: round(totals[f"{model}|{key}"] / count, 4)
            for key in ("search_agrees", "rerank_agrees", "search_loss", "rerank_loss")}
    return out


def fit_report(path: Path) -> dict[str, Any]:
    config = _load(CONFIG)
    data, games = load_data(path)
    if data["params"] != agent_params() or list(data["features"]) != list(FEATURES):
        raise ValueError(f"{path} is not 017's agent with these features")
    if [g["seed"] for g in games] != _load(SEEDS)["distil_seeds"]:
        raise ValueError(f"{path} is not on the distil seeds (or not complete)")
    split = config["fit_games"]
    fitted = [d for g in games[:split] for d in decisions(g["rows"])]
    checked = [d for g in games[split:] for d in decisions(g["rows"])]
    if any(not math.isfinite(v) for _, means, xs in fitted + checked
           for v in means + [k for x in xs for k in x]):
        raise ValueError(f"{path} holds a number that is not finite")
    weights = fit(fitted, config["ridge"])
    if not all(math.isfinite(w) for w in weights):
        raise ValueError("the fit gave a weight that is not finite")
    n = native.RERANK_FEATURES
    return {
        "data": {"path": str(path.relative_to(runner.PROJECT_ROOT)),
                 "created_at": data["created_at"], "versions": data["versions"],
                 "games": len(games), "fit_games": split,
                 "mean_score": e13._scores(games)["mean_score"]},
        "ridge": config["ridge"], "features": FEATURES,
        "weights": weights,
        "by_model": {name: dict(zip(FEATURES, weights[m * n:(m + 1) * n]))
                     for m, name in enumerate(MODELS)},
        "fitted_games": score(fitted, weights), "checked_games": score(checked, weights),
    }


# ---------------------------------------------------------------- dev check

def band_game(job: tuple[str, int, list[float] | None]) -> dict[str, Any]:
    """One dev game by 015's agent (``fast_deep``, weights None) or the re-rank agent,
    replayed on the Python binding, its score by band (016's ``band_game``)."""
    name, seed, weights = job
    config = _load(CONFIG)
    numbers = e16.fast_deep_params() if weights is None else agent_params()
    tick = time.perf_counter()
    played = native.play_game_ex(e16.KINDS["fast_deep"] if weights is None else
                                 "reach_plan_018", config["game"], seed,
                                 line_cap=config["line_cap"], frame_cap=config["frame_cap"],
                                 limits=_limits(config), params=native.params(numbers),
                                 weights=weights)
    seconds = time.perf_counter() - tick
    score_by: Counter[str] = Counter()
    count, band = -1, BANDS[0]
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in played["inputs"]:
            if state.phase == "active" and state.piece_count != count:
                count, band = state.piece_count, e15._band(state.level)
            before = state.score
            state, _ = game.step(mask)
            score_by[band] += state.score - before
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"{name} seed {seed}: the replay does not match the C++ game")
    return {"name": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "bands": {b: score_by[b] for b in BANDS}, "seconds": seconds}


def dev_check(jobs: int) -> dict[str, Any]:
    config = _load(CONFIG)
    seeds = _load(e13.SEEDS)["dev_seeds"][:config["dev_check_games"]]
    rerank = _load(RERANK)
    work = [("rerank", seed, rerank["weights"]) for seed in seeds] + \
        [("fast_deep", seed, None) for seed in seeds]
    with Pool(jobs) as pool:
        found = pool.map(band_game, work, chunksize=1)
    runs = {name: [g for g in found if g["name"] == name] for name in ("rerank", "fast_deep")}
    check017 = e17._load(e17.DEPTH_CHECK)
    return {
        "question": "The re-rank agent against 015's agent, on the dev seeds",
        "seeds": f"Experiment 013's first {len(seeds)} dev seeds", "games": len(seeds),
        "versions": runner._record_versions(), "numbers": agent_params(),
        "rerank": {"data": rerank["data"]["path"], "weights": rerank["weights"]},
        "runs": {name: e16._summary(games) for name, games in runs.items()},
        "paired": {"rerank - fast_deep": {"total": e12.paired(runs["rerank"], runs["fast_deep"]),
                                          "by_band": e16._band_pairs(runs["rerank"],
                                                                     runs["fast_deep"])}},
        "for_reference": {
            "017_dev": check017["runs"][_chosen_017(check017)],
            "016_dev": check017["runs"]["rollout"]},
    }


def _chosen_017(check: dict[str, Any]) -> str:
    chosen = e17._load(e17.CONFIG)["commit_rollout"]
    return next(name for name, v in check["variants"].items() if v == chosen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment018")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="select the distil seeds")
    for name, text in (("collect", "play 017's agent on the distil seeds, keep its rows"),
                       ("dev-check", "the re-rank agent against 015's on the dev seeds")):
        commands.add_parser(name, help=text).add_argument("--jobs", type=int, default=30)
    commands.add_parser("fit", help="fit rerank.json from a collect run").add_argument(
        "data", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            _write(SEEDS, select_seeds())
            print(f"Wrote {SEEDS}")
        elif args.command == "collect":
            print(f"Data: {collect(args.jobs)}")
        elif args.command == "fit":
            _write(RERANK, fit_report(args.data.resolve()))
            print(f"Wrote {RERANK}")
        else:
            _write(DEV_CHECK, dev_check(args.jobs))
            print(f"Wrote {DEV_CHECK}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
