"""Run Experiment 014: make a single cost what it really costs.

    python -m block_stack_ai.experiment014 singles [--games N] [--jobs N]

``singles`` (step 0) replays 012's and 013's agents on 013's dev seeds and counts every
line clear by level band (18-28, 29-38, 39+) and by the phase the agent was in when it
placed the piece (BUILD, or SPEND and why), plus how many I pieces became Tetrises. It
is the diagnostic Experiment 013's notes describe, committed before 014 changes anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment013 as e13, native, pathaware, runner, wellplan
from .engine import create_game
from .limits import Limits

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "014-real-points"
SINGLES = EXPERIMENT_ROOT / "singles.json"
BANDS = ("18-28", "29-38", "39+")
REASONS = ("build", "spend:drought", "spend:height", "spend:drought+height")


def _band(level: int) -> str:
    return BANDS[0] if level < 29 else BANDS[1] if level < 39 else BANDS[2]


def _agents() -> dict[str, tuple[str, dict[str, Any]]]:
    """Diagnosed agents: name -> (native agent kind, resolved numbers)."""
    return {"cem": ("reach_plan", e13.cem_params()),
            "deep": ("reach_plan_extra_ply", e13._load(e13.FINAL_PARAMS)["resolved"])}


def _reason(values: dict[str, Any], phase: str, level: int, drought: int, height: int) -> str:
    if phase == wellplan.BUILD:
        return "build"
    budget = values["survival_budget"] if level >= values["survival_level"] else \
        values["height_budget"]
    long_drought, too_tall = drought >= values["drought_bound"], height >= budget
    return ("spend:drought+height" if long_drought and too_tall else
            "spend:drought" if long_drought else "spend:height")


def singles_game(job: tuple[str, int]) -> dict[str, Any]:
    """One dev game by the C++ agent, replayed on the Python binding: the per-piece phase
    is recomputed from the replayed state (``native.phase``) and every clear is credited
    to the band and phase of the piece that made it."""
    name, seed = job
    kind, values = _agents()[name]
    config = e13._load(e13.CONFIG)
    params = native.params(values)
    played = native.play_game_ex(kind, config["game"], seed, line_cap=config["line_cap"],
                                 frame_cap=config["frame_cap"], limits=e13._limits(config),
                                 params=params)
    reaction = e13._limits(config).reaction_frames
    tally: Counter[str] = Counter()
    drought = before_drought = frame = 0
    count, piece = -1, ("", "", "")
    with create_game(**config["game"], seed=seed) as game:
        state = game.state

        def label(drought: int) -> tuple[str, str, str]:
            columns = pathaware.grid_columns(wellplan.visible_grid(state.board))
            phase = native.phase(params, state.level, drought, columns)
            return (_band(state.level), _reason(values, phase, state.level, drought,
                                                wellplan.stack_height(columns)),
                    state.current_piece)

        for mask in played["inputs"]:
            # The drought as native/agent.hpp counts it: at spawn only the current piece
            # resets it; the preview counts too once the adjust decision fires at the
            # reaction frame, which a piece that locks sooner never reaches.
            if state.phase == "active":
                current_is_i = state.current_piece == "I"
                preview_is_i = state.next_piece == "I"
                if state.piece_count != count:
                    count, frame, before_drought = state.piece_count, 0, drought
                    drought = 0 if current_is_i else before_drought + 1
                    piece = label(drought)
                    tally[f"pieces|{piece[0]}|{piece[1]}"] += 1
                    if current_is_i:
                        tally[f"I pieces|{piece[0]}"] += 1
                elif frame == reaction:
                    drought = 0 if current_is_i or preview_is_i else before_drought + 1
                    tally[f"pieces|{piece[0]}|{piece[1]}"] -= 1
                    piece = label(drought)
                    tally[f"pieces|{piece[0]}|{piece[1]}"] += 1
                frame += 1
            before = state.lines
            state, _ = game.step(mask)
            if state.lines > before:
                size = state.lines - before
                tally[f"clear{size}|{piece[0]}|{piece[1]}"] += 1
                if piece[2] == "I" and size == 4:
                    tally[f"I tetris|{piece[0]}"] += 1
    if (state.score, state.lines) != (played["score"], played["lines"]):
        raise ValueError(f"{name} seed {seed}: the replay does not match the C++ game")
    return {"agent": name, "seed": seed, "score": played["score"], "lines": played["lines"],
            "tally": dict(tally)}


def _per_game(total: Counter[str], games: int) -> dict[str, Any]:
    """Per-game clears by band and phase, and the I-piece Tetris conversion by band."""
    clears = {band: {reason: {f"clear{size}": round(total[f"clear{size}|{band}|{reason}"]
                                                     / games, 2) for size in (1, 2, 3, 4)}
                     for reason in REASONS} for band in BANDS}
    pieces = {band: {reason: round(total[f"pieces|{band}|{reason}"] / games, 1)
                     for reason in REASONS} for band in BANDS}
    i_to_tetris = {band: round(total[f"I tetris|{band}"] / max(1, total[f"I pieces|{band}"]),
                               3) for band in BANDS}
    return {"clears_per_game": clears, "pieces_per_game": pieces, "i_to_tetris": i_to_tetris}


def singles(games: int, jobs: int) -> dict[str, Any]:
    seeds = e13._load(e13.SEEDS)["dev_seeds"][:games]
    work = [(name, seed) for name in _agents() for seed in seeds]
    with Pool(jobs) as pool:
        rows = pool.map(singles_game, work)
    if not seeds:
        raise ValueError("--games must be at least 1")
    out: dict[str, Any] = {
        "seeds": f"Experiment 013's first {len(seeds)} dev seeds (experiments/013-deeper-search/seeds.json)",
        "versions": runner._record_versions(),
        "agents": {}}
    for name in _agents():
        mine = [row for row in rows if row["agent"] == name]
        total: Counter[str] = Counter()
        for row in mine:
            total.update(row["tally"])
        out["agents"][name] = {
            "games": len(mine),
            "mean_score": round(sum(r["score"] for r in mine) / len(mine), 1),
            "mean_lines": round(sum(r["lines"] for r in mine) / len(mine), 2),
            **_per_game(total, len(mine)), "totals": dict(sorted(total.items()))}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment014")
    sub = parser.add_subparsers(dest="command", required=True)
    diag = sub.add_parser("singles")
    diag.add_argument("--games", type=int, default=200)
    diag.add_argument("--jobs", type=int, default=30)
    args = parser.parse_args(argv)
    if args.command == "singles":
        SINGLES.parent.mkdir(parents=True, exist_ok=True)
        SINGLES.write_text(json.dumps(singles(args.games, args.jobs), indent=1) + "\n")
        print(SINGLES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
