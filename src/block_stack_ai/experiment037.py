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


def step0_parts(name: str) -> list[dict[str, np.ndarray]]:
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
    parts, backups, played, kid_boards, goals = step0_parts(name), [], [], [], []
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




# ================================================================ stages A and B
#
# Stage A re-teaches V29@20 (230-319) from v36's, stage B V18@20 (below 230) from v36's,
# each with its step 0 lambda (a stage whose network got no lambda is not run). Everything
# else is 036's recipe (036's stage 3 for A, stage 2 for B), with 036's game, search,
# checks and probe seeds, and three new guards (predeclared.md). The base is v36's stored
# games.

RUNS = runner.PROJECT_ROOT / "runs" / "037"
SEEDS = OUT / "seeds.json"
WIRING = OUT / "wiring_check.json"
DECISION = OUT / "decision.json"
BASE_GAMES = OUT / "base_games"
GAMES = OUT / "games"
SCHEMA = e36.SCHEMA
BASE = "v36"
LATE = e36.LATE
DEPTH, CHILD_SHARE = e36.DEPTH, e36.CHILD_SHARE
ROUND0_SEEDS, ROUND_SEEDS, CHECK_SEEDS, KEPT_ROUNDS = 400, 200, 40, 3
EXPLORE = e36.EXPLORE
STOP_AFTER_FLAT = 2
DEATH_MARGIN = 10   # stage A: deaths at 230-319 on a probe half at most v36's + 10
WRECK_MARGIN = 3    # stage B: games with 40+ singles at level 18 at most v36's + 3
WRECK_SINGLES = 40
SEED_LABEL = "fallgorithm-training/037/v1/{}"
REPLAY_GAMES = 28

# stage: the network it teaches, 036's stage whose band / exploration / checks it uses,
# sweeps, the step 0 network
STAGES: dict[str, dict[str, Any]] = {
    "A": {"net": "V29", "e36": 3, "min": 3, "max": 6, "band": (e36.MID_FROM, e36.LATE_FROM)},
    "B": {"net": "V18", "e36": 2, "min": 2, "max": 4, "band": (0, e36.MID_FROM)},
}
V36_PROBE_A = "runs/036/games/stage3-sweep1-A.json.gz"  # copied to base_games/ by `seeds`
V36_SETS = {"probeA": BASE_GAMES / "probeA-v36.json.gz",
            "probeB": e36.GAMES / "stage3-sweep1-B.json.gz",
            "development": e36.GAMES / "development-v36.json.gz",
            "heldout": e36.GAMES / "heldout-v36.json.gz"}

_load, _write, _path, _sha, _relative = e36._load, e36._write, e36._path, e36._sha, e36._relative


def stage_lambda(stage: str) -> float | None:
    """The stage's lambda from step 0 (None: the stage is not run)."""
    if not STEP0.exists():
        raise ValueError(f"{STEP0} is missing: run step0 first")
    return _load(STEP0)["networks"][STAGES[stage]["net"]]["lambda"]


# ---------------------------------------------------------------- seeds

def _identities_taken() -> set[str]:
    from . import experiment025 as e25, experiment029 as e29
    taken = {e20._identity(s) for s in e29._seeds()["training_seeds"]}
    taken |= {e20._identity(s) for st in ("screening", "development", "heldout")
              for s in e25._seeds(st)}
    taken |= {e20._identity(s) for s in _load(e23.SEEDS)["probe_seeds"]}
    return taken


def make_seeds() -> dict[str, Any]:
    """New training seeds (029's list is used up): labelled seeds, one per start state, none
    sharing a start state with 029's training list, the register's sets, 012's held-out
    seeds or 023's probe seeds; per stage round 0's 400, then 200 per own round a later
    sweep can train on. The probe halves are 036's. v36's probe A games are copied into the
    experiment (the base)."""
    from . import experiment006 as e06
    if SEEDS.exists():
        return _load(SEEDS)
    taken, picked, index = _identities_taken(), [], 0
    need = sum(ROUND0_SEEDS + ROUND_SEEDS * (spec["max"] - 1) for spec in STAGES.values())
    while len(picked) < need:
        seed = e06._label_seed(SEED_LABEL, index)
        identity = e20._identity(seed)
        if identity not in taken:
            picked.append(seed)
            taken.add(identity)
        index += 1
    stages, at = {}, 0
    for stage, spec in STAGES.items():
        end = at + ROUND0_SEEDS + ROUND_SEEDS * (spec["max"] - 1)
        stages[stage] = {"round0": picked[at:at + ROUND0_SEEDS],
                         "rounds": picked[at + ROUND0_SEEDS:end]}
        at = end
    result = {"selection": f"labelled seeds ({SEED_LABEL}, first two bytes of SHA256), one "
                           "per start state, none sharing a start state with 029's training "
                           "list, the register's screening / development sets, 012's held-out "
                           "seeds or 023's probe seeds; labels drawn 0-" + str(index - 1),
              "stages": stages,
              "probe": {"A": e36.probe_seeds("A"), "B": e36.probe_seeds("B")}}
    _write(SEEDS, result)
    BASE_GAMES.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copyfile(_path(V36_PROBE_A), V36_SETS["probeA"])
    return result


def _seeds() -> dict[str, Any]:
    if not SEEDS.exists():
        raise ValueError(f"{SEEDS} is missing: run seeds")
    return _load(SEEDS)


def round_seeds(stage: str, index: int) -> list[int]:
    part = _seeds()["stages"][stage]
    if index == 0:
        return part["round0"]
    if not 1 <= index < STAGES[stage]["max"]:
        raise ValueError(f"stage {stage} has no round {index}")
    start = ROUND_SEEDS * (index - 1)
    return part["rounds"][start:start + ROUND_SEEDS]


def probe_seeds(half: str) -> list[int]:
    return _seeds()["probe"][half]


# ---------------------------------------------------------------- the base: v36's games

def _gz(path: Path) -> dict[str, Any]:
    import gzip
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def reference() -> dict[str, Any]:
    """v36's stored games (probe A, probe B, development, held-out: 2,500), checked to be
    v36's networks, search and format on their seeds in order."""
    from . import experiment025 as e25
    want = {"probeA": e36.probe_seeds("A"), "probeB": e36.probe_seeds("B"),
            "development": e25._seeds("development"), "heldout": e25._seeds("heldout")}
    episodes = {}
    for name, path in V36_SETS.items():
        record = _gz(path)
        if (record["agent"]["early"], record["agent"]["mid"]) != (V36_EARLY, V36_MID):
            raise ValueError(f"{path} was not played by v36")
        if record["search"] != e36.search() or \
                record["format"] != e33.format_of(e33._frozen()[0]):
            raise ValueError(f"{path} is not v36's search and format")
        if [e["seed"] for e in record["episodes"]] != want[name]:
            raise ValueError(f"{path} does not cover its seeds in order")
        episodes[name] = record["episodes"]
    every = [e for found in episodes.values() for e in found]
    return {"scores": np.array([e["result"]["score"] for e in every], np.float64),
            "late": np.array([e36.late_points(e) for e in every], np.float64),
            "by_seed": {n: {e["seed"]: e for e in found} for n, found in episodes.items()}}


_REFERENCE: dict[str, Any] = {}


def ref() -> dict[str, Any]:
    if not _REFERENCE:
        _REFERENCE.update(reference())
    return _REFERENCE


def measure(episodes: list[dict[str, Any]], same_below_230: bool) -> dict[str, Any]:
    """036's probe measure against v36's 2,500 stored games: the mean final score, or for an
    agent that plays v36's own game below 230 (stage A) the mean points at levels 29 and
    up."""
    r = ref()
    if same_below_230:
        mine, base, kind = [e36.late_points(e) for e in episodes], r["late"], "points_29_up"
    else:
        mine, base, kind = [e["result"]["score"] for e in episodes], r["scores"], "score"
    return {"kind": kind, "base_games": int(len(base)), "base_mean": float(base.mean()),
            "mine_mean": float(np.mean(mine))} | e36.bootstrap_difference(np.array(mine), base)


def deaths_mid(episodes: list[dict[str, Any]]) -> int:
    return sum(e36.MID_FROM <= e["result"]["lines"] < e36.LATE_FROM for e in episodes)


def wrecked(episodes: list[dict[str, Any]]) -> int:
    return sum(e["stats"]["by_level"].get("18", {}).get("single", 0) >= WRECK_SINGLES
               for e in episodes)


def guards(stage: str, episodes: list[dict[str, Any]], half: str) -> dict[str, Any]:
    """The new per-probe guard (predeclared.md): stage A deaths at 230-319 at most v36's on
    the same half + DEATH_MARGIN; stage B games with 40+ singles at level 18 at most v36's
    + WRECK_MARGIN. Both are reported for both stages; only the stage's own decides."""
    base = list(ref()["by_seed"][f"probe{half}"].values())
    d, db, w, wb = deaths_mid(episodes), deaths_mid(base), wrecked(episodes), wrecked(base)
    ok = d <= db + DEATH_MARGIN if stage == "A" else w <= wb + WRECK_MARGIN
    return {"deaths_230_319": d, "v36_deaths_230_319": db, "wrecked_games": w,
            "v36_wrecked_games": wb, "death_margin": DEATH_MARGIN,
            "wreck_margin": WRECK_MARGIN, "decides": "deaths" if stage == "A" else "wrecked",
            "passed": bool(ok)}


# ---------------------------------------------------------------- the networks of a stage

def stage_dir(stage: str) -> Path:
    return OUT / f"stage{stage}"


def _stage_done(stage: str) -> dict[str, Any] | None:
    path = stage_dir(stage) / "choice.json"
    return _load(path) if path.exists() else None


def mid_for_b() -> str:
    """Stage B's V29@20: stage A's choice if stage A went on, else v36's."""
    found = _stage_done("A")
    if found is not None and found["rule"]["go"]:
        return found["chosen"]["weights"]
    return V36_MID


def weights_rel(stage: str, sweep: int) -> str:
    if sweep == 0:
        return V36_MID if stage == "A" else V36_EARLY
    return _relative(stage_dir(stage) / f"value_sweep{sweep}.bin")


def agent(stage: str, sweep: int) -> tuple[str, str]:
    """(below 230, 230-319) of the stage's agent with the sweep's network."""
    if stage == "A":
        return V36_EARLY, weights_rel("A", sweep)
    return weights_rel("B", sweep), mid_for_b()


def handover_value(stage: str, jobs: int) -> Callable[[np.ndarray], np.ndarray]:
    """Stage A: max(0, c x V39' backup2); stage B: backup2 of stage B's V29@20."""
    if stage == "A":
        return _handover("V29", jobs)
    mid = _path(mid_for_b())
    return lambda rows: e36.targets(mid, rows, DEPTH, jobs)[0]


# ---------------------------------------------------------------- guards before games

def _require_clean() -> None:
    import subprocess
    found = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", f":!{OUT.relative_to(runner.PROJECT_ROOT)}"],
        cwd=runner.PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    if found.strip():
        raise ValueError(f"the git tree is dirty outside {OUT.name}: commit before playing")


def _require_ready() -> None:
    """Before any game: a clean tree outside the experiment; the plan, the protocol, step
    0, the seeds, the base games and every input network committed; the wiring check
    matched on this very library, which must not have changed since."""
    _require_clean()
    e34._require_committed(OUT / "plan.md", OUT / "predeclared.md", STEP0, SEEDS,
                           V36_SETS["probeA"], e34.CALIBRATION,
                           *(_path(rel) for rel in (V36_EARLY, V36_MID, LATE)),
                           *(V36_SETS[k] for k in ("probeB", "development", "heldout")))
    library = e36.library_record()
    wiring = _load(WIRING) if WIRING.exists() else {}
    if not wiring.get("matched") or wiring.get("library") != library:
        raise ValueError(f"{WIRING} is missing or not matched on this library: run check")


def _replay_job(job: tuple[int, str, str, str]) -> dict[str, Any]:
    return e36._probe_job(job)


def replay_v36(name: str, jobs: int) -> dict[str, Any]:
    """The first 28 stored v36 games of a set re-run by 036's game."""
    from multiprocessing import Pool
    stored = list(ref()["by_seed"][name].values())[:REPLAY_GAMES]
    with Pool(jobs) as pool:
        played = pool.map(_replay_job, [(e["seed"], V36_EARLY, V36_MID, BASE) for e in stored],
                          chunksize=1)
    bad = [e["seed"] for e, got in zip(stored, played) if got["inputs"] != e["inputs"]]
    return {"games": len(stored), "matched": len(stored) - len(bad), "mismatched_seeds": bad}


def wiring_check(jobs: int) -> dict[str, Any]:
    """The first 28 stored v36 development and held-out games re-run on this library."""
    parts = {name: replay_v36(name, jobs) for name in ("development", "heldout")}
    result = {"experiment": OUT.name, "part_20hz_v36": parts,
              "matched": all(p["matched"] == p["games"] for p in parts.values()),
              "library": e36.library_record(), "versions": runner._record_versions()}
    _write(WIRING, result)
    return result


# ---------------------------------------------------------------- rounds

def _round_path(stage: str, index: int) -> Path:
    return DATA / f"stage{stage}" / f"round{index}.npz"


def round_work(stage: str, index: int) -> list[tuple[int, int, int, str, str, float]]:
    """Round 0: the stage's agent with its warm start, no exploration; an own round: the
    sweep's network, 0.5% exploration (036's data job and exploration band)."""
    early, mid = agent(stage, index)
    return [(s, 0, STAGES[stage]["e36"], early, mid, 0.0 if index == 0 else EXPLORE)
            for s in round_seeds(stage, index)]


def play_round(stage: str, index: int, jobs: int) -> dict[str, Any]:
    record = stage_dir(stage) / f"round{index}.json"
    if record.exists():
        return _load(record)
    path = _round_path(stage, index)
    work = round_work(stage, index)
    s36 = STAGES[stage]["e36"]
    tick = time.time()
    library_path = path.with_name(f"round{index}.library.json")
    if path.exists():
        summary = {"resumed": "the games' summary was lost in a crash"}
    else:
        _require_ready()
        e34._require_committed(*{_path(w[3]) for w in work}, *{_path(w[4]) for w in work})
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(json.dumps(e36.library_record()), encoding="utf-8")
        summary = e36.play_data(path, work, s36, jobs)
    d = e23._load_npz(path)
    taught = _path(work[0][4] if stage == "A" else work[0][3])
    result = {"experiment": OUT.name, "stage": stage, "round": index, "seeds": len(work),
              "agents": sorted({(w[3], w[4]) for w in work}), "explore": work[0][5],
              "format": e33.format_of(e33._frozen()[0]), "search": e36.search(),
              "library": json.loads(library_path.read_text(encoding="utf-8")),
              "versions": runner._record_versions(),
              "seconds": round(time.time() - tick, 1),
              "calibration_value_actual_by_10_lines": e36.calibration(s36, taught, d)} | \
        summary | e36._handover_summary(path, s36)
    if stage == "A":
        result["scale_drift"] = e34.drift(d, jobs)
    _write(record, result)
    return result


# ---------------------------------------------------------------- targets and sweeps

def build_targets(parts: list[dict[str, np.ndarray]], previous: Path, split: int,
                  handover: Callable[[np.ndarray], np.ndarray], lam: float, jobs: int,
                  rng: np.random.Generator) -> dict[str, np.ndarray]:
    """036's ``build_targets`` with the played rows' lambda as an argument."""
    boards, goals, kinds, rests, child_rows = [], [], [], [], []
    hand_lines, hand_value, hand_rest = [], [], []
    for part in parts:
        rows = e23._rows(part)
        below = part["lines"] < split
        backup = np.zeros(len(rows))
        backup[below], _ = e36.targets(previous, rows[below], DEPTH, jobs)
        backup[~below] = handover(rows[~below]) if (~below).any() else np.zeros(0)
        rest = (part["final"].astype(np.float64) - part["score"]) / TETRIS_18
        boards.append({key: part[key][below] for key in KEYS})
        goals.append(e30.handover_returns(backup, part, lam, late_from=split))
        kinds.append(np.zeros(int(below.sum()), np.int8))
        rests.append(rest[below])
        hand_lines.append(part["lines"][~below])
        hand_value.append(backup[~below])
        hand_rest.append(rest[~below])
        pick = rng.random(int(below.sum())) < CHILD_SHARE
        _, kids = e36.targets(previous, rows[below][pick], 1, jobs, children=True)
        child_rows.append(kids)
    kids = np.concatenate(child_rows)
    low = kids[:, native.WIDTH] < split
    for subset, kind in ((kids[low], 1), (kids[~low], 2)):
        if kind == 1:
            values, _ = e36.targets(previous, subset, DEPTH, jobs)
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


def training_parts(stage: str, index: int) -> tuple[list[dict[str, np.ndarray]], dict]:
    zero = e23._load_npz(_round_path(stage, 0))
    held = np.isin(zero["seed"], np.array(round_seeds(stage, 0)[:CHECK_SEEDS]))
    parts = [e33._split(zero, ~held)]
    for k in range(max(1, index - KEPT_ROUNDS), index):
        parts.append(e23._load_npz(_round_path(stage, k)))
    split = STAGES[stage]["band"][1]
    return parts, e33._split(zero, held & (zero["lines"] < split))


def garbage_boards() -> dict[str, np.ndarray]:
    """Stage B's fixed garbage check boards: 036 stage 2's round 3 (step 0's V18 test set)
    below 130 lines."""
    d = e23._load_npz(e36._round_path(2, 3))
    return e33._split(d, d["lines"] < 130)


def garbage_gap(weights: Path, d: dict[str, np.ndarray]) -> float:
    """Mean over 10-line steps below 130 of V(10+ holes) - V(no holes), Tetrises."""
    values = e34._values(weights, d)
    holes, gaps = d["features"][:, 0], []
    for s in range(0, 130, 10):
        step = (d["lines"] >= s) & (d["lines"] < s + 10)
        bad, clean = step & (holes >= 10), step & (holes == 0)
        if bad.any() and clean.any():
            gaps.append(values[bad].mean() - values[clean].mean())
    return round(float(np.mean(gaps)), 3)


def sweep(stage: str, index: int, jobs: int, device: str) -> dict[str, Any]:
    """036's sweep with the stage's lambda; stage B adds the garbage check after the fit
    (the fitted network's garbage gap no less negative than v36's V18's)."""
    out_path = _path(weights_rel(stage, index))
    record = stage_dir(stage) / f"sweep{index}.json"
    if out_path.exists() or (record.exists() and not _load(record)["fitted"]):
        return _load(record)
    lam = stage_lambda(stage)
    previous = _path(weights_rel(stage, index - 1))
    s36, split = STAGES[stage]["e36"], STAGES[stage]["band"][1]
    tick = time.time()
    parts, check = training_parts(stage, index)
    built = build_targets(parts, previous, split, handover_value(stage, jobs), lam, jobs,
                          np.random.default_rng(TORCH_SEED_OFFSET + 100 * ord(stage) + index))
    check_targets, _ = e36.targets(previous, e23._rows(check), DEPTH, jobs)
    checks = e36.checks_of(s36, built)
    kind = built["kind"]
    played = kind == 0
    result: dict[str, Any] = {
        "experiment": OUT.name, "stage": stage, "sweep": index,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": e33.format_of(e33._frozen()[0]), "library": e36.library_record(),
        "versions": runner._record_versions(), "torch": torch.__version__,
        "from": {"path": _relative(previous), "sha256": _sha(previous)},
        "depth": DEPTH, "lambda": lam,
        "handover": ({"late": _sha(_path(LATE)), "calibration": e34.calibration()["sha256"]}
                     if stage == "A" else
                     {"mid": mid_for_b(), "mid_sha256": _sha(_path(mid_for_b()))}),
        "training_rounds": [0] + list(range(max(1, index - KEPT_ROUNDS), index)),
        "boards": {"played": int(played.sum()), "children_in_band": int((kind == 1).sum()),
                   "children_past_band": int((kind == 2).sum()),
                   "handover_boards": int(len(built["handover_value"])),
                   "check": int(len(check_targets))},
        "mean_target_and_actual_by_10_lines": e34.by_steps(
            built["lines"][played], built["goal"][played], built["rest"][played],
            start=STAGES[stage]["band"][0], stop=split),
        "handover_value_and_actual": {"mean_value": e34._mean(built["handover_value"]),
                                      "mean_actual": e34._mean(built["handover_rest"])},
        "target_seconds": round(time.time() - tick, 1),
        "unit": "Tetrises at level 18 (22,800 points)", "checks": checks,
        "fitted": checks["passed"]}
    if not checks["passed"]:
        _write(record, result | {"weights": None, "eligible": False})
        return _load(record)
    settings = _load(e23.CONFIG)["fit"]
    cap = e33._config()["line_cap"]
    seed = settings["torch_seed"] + TORCH_SEED_OFFSET + 100 * ord(stage) + index
    torch.manual_seed(seed)
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
               "torch_seed": seed, "training_log": log,
               "check_boards_diagnostic": {"old_value_minus_target_rms": rms(before),
                                           "new_value_minus_target_rms": rms(after)},
               "eligible": True}
    if stage == "B":
        boards = garbage_boards()
        mine, v36_gap = garbage_gap(partial, boards), garbage_gap(_path(V36_EARLY), boards)
        result["garbage_check"] = {"gap": mine, "v36_gap": v36_gap,
                                   "passed": bool(mine <= v36_gap)}
        result["eligible"] = result["garbage_check"]["passed"]
    _write(record, result)
    partial.replace(out_path)
    return result


# ---------------------------------------------------------------- probes

def _probe_name(stage: str, label: str, half: str) -> str:
    return f"stage{stage}-{label}-{half}"


def play_probe(stage: str, label: str, early: str, mid: str, half: str,
               jobs: int) -> list[dict[str, Any]]:
    """036's ``play_probe`` with v36 as the base: an agent with v36's V18 below 230 must
    play v36's stored inputs there on every seed (stops otherwise)."""
    import gzip, hashlib
    from multiprocessing import Pool
    name = _probe_name(stage, label, half)
    target = RUNS / "games" / f"{name}.json.gz"
    seeds = probe_seeds(half)
    if target.exists():
        record = _gz(target)
        if [e["seed"] for e in record["episodes"]] != seeds or \
                record["agent"] != {"early": early, "mid": mid}:
            raise ValueError(f"{target} is not this agent on probe {half}")
        return record["episodes"]
    _require_ready()
    e34._require_committed(_path(early), _path(mid))
    versions, library = runner._record_versions(), e36.library_record()
    agent_record = {"early": early, "mid": mid}
    header = {"header": {"name": name, "agent": agent_record, "search": e36.search(),
                         "shas": [_sha(_path(early)), _sha(_path(mid))],
                         "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                         "library": library, "versions": versions}}
    (RUNS / "partial").mkdir(parents=True, exist_ok=True)
    partial = RUNS / "partial" / f"{name}.partial.jsonl"
    done = e36.resume(partial, header)
    guard = early == V36_EARLY
    stored = ref()["by_seed"][f"probe{half}"]
    frozen = e33._frozen()[0]
    todo = [(s, early, mid, name) for s in seeds if s not in done]
    print(f"{name}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    import base64
    with partial.open("a", encoding="utf-8") as handle, Pool(jobs) as pool:
        for episode in pool.imap_unordered(e36._probe_job, todo, chunksize=1):
            s = episode["seed"]
            if guard and not e34.prefix_matches(frozen, s, base64.b64decode(stored[s]["inputs"]),
                                                base64.b64decode(episode["inputs"])):
                raise ValueError(f"{name}: seed {s} differs from v36 before 230 lines: "
                                 f"stopped (the games stay in {partial})")
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[s] = episode
            if len(done) % 50 == 0 or len(done) == len(seeds):
                mean = sum(e["result"]["score"] for e in done.values()) / len(done)
                print(f"{name} {len(done)}/{len(seeds)} {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "library": library, "name": name, "agent": agent_record,
              "shas": header["header"]["shas"], "search": e36.search(),
              "format": e33.format_of(frozen), "seeds": seeds,
              "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[s] for s in seeds]}
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".partial")
    with gzip.open(staged, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    staged.replace(target)
    partial.unlink()
    return record["episodes"]


def probe(stage: str, label: str, early: str, mid: str, half: str, jobs: int) -> dict[str, Any]:
    from . import experiment025 as e25
    path = stage_dir(stage) / f"probe{half}_{label}.json"
    if path.exists():
        return _load(path)
    episodes = play_probe(stage, label, early, mid, half, jobs)
    base = [ref()["by_seed"][f"probe{half}"][e["seed"]] for e in episodes]
    same = early == V36_EARLY
    result = {"experiment": OUT.name, "stage": stage, "label": label, "half": half,
              "agent": {"early": early, "mid": mid,
                        "shas": [_sha(_path(early)), _sha(_path(mid))]},
              "measure": measure(episodes, same), "guard": guards(stage, episodes, half),
              "paired_vs_v36_same_seeds_reported_only": e25._paired(episodes, base),
              "style": e36.e35.style(episodes), "base_style_same_seeds": e36.e35.style(base),
              "prefix_guard": "every seed matched" if same else "not applicable",
              "games": [{"seed": e["seed"], "score": e["result"]["score"],
                         "lines": e["result"]["lines"], "bands": e["stats"]["bands"]}
                        for e in episodes]}
    _write(path, result)
    return result


# ---------------------------------------------------------------- the stages

def should_stop(stage: str, means: list[float]) -> bool:
    n = len(means)
    if n >= STAGES[stage]["max"]:
        return True
    if n < STAGES[stage]["min"]:
        return False
    return n - (int(np.argmax(means)) + 1) >= STOP_AFTER_FLAT


def stage_choice(stage: str) -> dict[str, Any]:
    """The eligible probed sweep (checks passed, garbage check passed for B, the probe
    guard passed) with the highest probe A measure."""
    rows = []
    for k in range(1, STAGES[stage]["max"] + 1):
        path = stage_dir(stage) / f"probeA_sweep{k}.json"
        if not path.exists():
            continue
        found, swept = _load(path), _load(stage_dir(stage) / f"sweep{k}.json")
        rows.append({"sweep": k, "weights": weights_rel(stage, k),
                     "measure": found["measure"]["mean"],
                     "eligible": bool(swept["eligible"] and found["guard"]["passed"])})
    eligible = [r for r in rows if r["eligible"]]
    return {"rule": "the eligible sweep (1 or later) with the highest probe A measure "
                    "(predeclared.md)", "sweeps": rows,
            "chosen": max(eligible, key=lambda r: r["measure"], default=None)}


def commit_step(message: str, push: bool = False) -> None:
    """Commit the experiment's directory (and push), if a step changed it."""
    import subprocess
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


def run_stage(stage: str, jobs: int, device: str,
              after: Callable[[str], None] = lambda message: None) -> dict[str, Any]:
    """One stage, resumable: round 0, the sweeps (targets, checks, fit, [garbage check],
    probe A with its guard, the stop rule, the next own round), the choice, and its probe
    B if its probe A measure is above 0. Stage B ends at a sweep that fails the checks, the
    garbage check or its guard; stage A ends only at a sweep that fails the checks."""
    done = _stage_done(stage)
    if done is not None:
        return done
    if stage == "B" and stage_lambda("A") is not None and _stage_done("A") is None:
        raise ValueError("stage A has not finished")
    name = f"Experiment 037 stage {stage}"
    if stage_lambda(stage) is None:
        body = {"rule": {"go": False, "why": "step 0 gave this network no lambda"},
                "sweeps": [], "chosen": None, "probe_b": None}
        _write(stage_dir(stage) / "choice.json", body)
        after(f"{name}: not run (step 0)")
        return body
    _require_ready()
    e34._require_committed(_path(agent(stage, 0)[1]))
    play_round(stage, 0, jobs)
    after(f"{name}: round 0")
    means: list[float] = []
    index = 1
    while True:
        result = sweep(stage, index, jobs, device)
        if not result["fitted"]:
            after(f"{name} sweep {index}: its targets failed the checks, not fitted")
            break
        after(f"{name} sweep {index}: targets, checks and fit")
        if stage == "B" and not result["eligible"]:
            after(f"{name} sweep {index}: failed the garbage check, the stage ends")
            break
        found = probe(stage, f"sweep{index}", *agent(stage, index), "A", jobs)
        means.append(found["measure"]["mean"])
        m = found["measure"]
        print(f"stage {stage} sweep {index}: probe A {m['mean']:+,.0f} ({m['ci95_low']:+,.0f}, "
              f"{m['ci95_high']:+,.0f}) [{m['kind']}] guard {found['guard']}", flush=True)
        after(f"{name} sweep {index} on probe A: {m['mean']:+,.0f} ({m['kind']}), guard "
              f"{found['guard']['passed']}")
        if stage == "B" and not (result["eligible"] and found["guard"]["passed"]):
            break
        if should_stop(stage, means):
            break
        play_round(stage, index, jobs)
        after(f"{name}: round {index}")
        index += 1
    body = stage_choice(stage)
    chosen = body["chosen"]
    b, rule = None, {"go": False, "why": "no eligible sweep"}
    if chosen is not None:
        if chosen["measure"] > 0:
            label = f"sweep{chosen['sweep']}"
            found = probe(stage, label, *agent(stage, chosen["sweep"]), "B", jobs)
            b = found["measure"] | {"guard": found["guard"]}
            GAMES.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copyfile(RUNS / "games" / f"{_probe_name(stage, label, 'B')}.json.gz",
                            GAMES / f"{_probe_name(stage, label, 'B')}.json.gz")
            rule = {"go": True}
        else:
            rule = {"go": False, "why": f"the choice's probe A measure {chosen['measure']:+,.0f} "
                                        "is not above 0"}
    body = body | {"probe_b": b, "rule": rule}
    _write(stage_dir(stage) / "choice.json", body)
    after(f"{name}: choice {chosen and chosen['sweep']}, probe B "
          f"{'none' if b is None else format(b['mean'], '+,.0f')}, go {rule['go']}")
    return body


def decide() -> dict[str, Any]:
    """``v37`` (decision.json): the stage choice that went on with the highest probe B
    measure, if above 0."""
    rows = []
    for stage in STAGES:
        found = _stage_done(stage)
        if found is None:
            raise ValueError(f"stage {stage} has not run")
        if found["rule"]["go"] and found["probe_b"] is not None and \
                found["probe_b"]["guard"]["passed"]:
            rows.append({"stage": stage, "measure": found["probe_b"]["mean"]})
    best = max(rows, key=lambda r: r["measure"], default=None)
    result: dict[str, Any] = {"candidates": rows, "v37": None, "final_evaluation": False}
    if best is not None and best["measure"] > 0:
        stage = best["stage"]
        chosen = _stage_done(stage)["chosen"]
        early, mid = agent(stage, chosen["sweep"])
        result |= {"v37": stage, "final_evaluation": True,
                   "probe_b_measure_selected": best["measure"],
                   "agent": {"stage": stage, "sweep": chosen["sweep"], "early": early,
                             "mid": mid, "late": LATE,
                             "shas": [_sha(_path(p)) for p in (early, mid, LATE)]}}
    result["rule"] = ("v37 is the stage choice (of the stages that went on, whose probe B "
                      "passed the stage's guard) with the highest probe B measure; no final evaluation unless it is above 0; its probe B "
                      "figure is selected (predeclared.md). Stage A's measure is in points at "
                      "levels 29 and up (it plays v36's own game below 230), stage B's in "
                      "total score.")
    _write(DECISION, result)
    return result


def status() -> dict[str, Any]:
    out: dict[str, Any] = {"step0": None}
    if STEP0.exists():
        out["step0"] = {n: v["lambda"] for n, v in _load(STEP0)["networks"].items()}
    for stage in STAGES:
        rows = []
        for k in range(1, STAGES[stage]["max"] + 1):
            path = stage_dir(stage) / f"probeA_sweep{k}.json"
            if path.exists():
                f = _load(path)
                rows.append({"sweep": k, "measure": round(f["measure"]["mean"]),
                             "guard": f["guard"]["passed"]})
        out[stage] = {"probes": rows, "choice": _stage_done(stage)}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment037")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("step0", "the offline lambda check (no games)"),
                       ("seeds", "draw the training seeds, copy v36's probe A games"),
                       ("check", "the wiring check (28 + 28 stored v36 games)"),
                       ("stage", "run one stage (resumable)"),
                       ("choose", "name v37 (decision.json)"), ("status", "progress")):
        sub = commands.add_parser(name, help=text)
        if name in ("step0", "check", "stage"):
            sub.add_argument("--jobs", type=int, default=28)
        if name in ("step0", "stage"):
            sub.add_argument("--device",
                             default="cuda" if torch.cuda.is_available() else "cpu")
        if name == "stage":
            sub.add_argument("stage", choices=tuple(STAGES))
            sub.add_argument("--commit", action="store_true")
            sub.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    import subprocess
    if getattr(args, "commit", False):
        for key in ("user.name", "user.email"):
            if subprocess.run(["git", "config", key], cwd=runner.PROJECT_ROOT,
                              capture_output=True).returncode:
                print(f"git {key} is not set: set it before --commit", file=sys.stderr)
                return 2
    try:
        if args.command == "step0":
            found = step0(args.jobs, args.device)
            for name, n in found["networks"].items():
                print(name, "lambda", n["lambda"], {k: (v["risk_bias"], v["rms"])
                                                     for k, v in n["by_lambda"].items()})
        elif args.command == "seeds":
            found = make_seeds()
            print({k: (len(v["round0"]), len(v["rounds"])) for k, v in found["stages"].items()})
        elif args.command == "check":
            found = wiring_check(args.jobs)
            print(f"Wrote {WIRING}: matched {found['matched']}")
            return 0 if found["matched"] else 1
        elif args.command == "stage":
            after = (lambda m: commit_step(m, args.push)) if args.commit else (lambda m: None)
            found = run_stage(args.stage, args.jobs, args.device, after)
            print(json.dumps(found, indent=1))
        elif args.command == "choose":
            print(json.dumps(decide(), indent=1))
        else:
            print(json.dumps(status(), indent=1))
    except (native.NativeError, OSError, KeyError, ValueError, json.JSONDecodeError,
            subprocess.CalledProcessError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
