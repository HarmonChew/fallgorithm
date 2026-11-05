"""Experiment 031 Phase A: an offline audit of the late network's well-building decisions.

    python -m block_stack_ai.experiment031audit DATA.npz [--late W] [--jobs N] [--out F]
                                                [--from-lines L] [--limit N]

On saved own-play boards (an ``experiment029._play_data`` npz: whole games from 320 lines),
every decision is re-searched in Python as the commit search does it at 29+ (preview
unknown; native/netsearch.hpp ``search`` with deep commit and deep2 k 4): the current
piece's reachable placements from the spawn (``native.reachable``), each settled
(``native.settle``) and scored by clear points + backup under the late network, the best
``DEEP2_K`` rescored by clear points + backup2. From the spawn, not the agent's in-flight
state after its reaction delay, so the re-searched pick is checked against the placement
the game made (``agrees``).

A "well placement" leaves a ready well (``experiment031.ready_wells``) or clears four. For
decisions with a well placement, the pick is compared with the best well placement:
the score gap in Tetrises at level 18, split into clear points and the future term
(backup2), by 10 lines (plan.md Phase A, item 2; Phase D gate (a)). At ready boards, also
whether an I can clear four (``i_reaches``), and the late network's calibration by 10 lines
(item 3).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from . import experiment023 as e23, experiment024 as e24, experiment029 as e29
from . import experiment031 as e31, native
from .limits import Flight
from .pieces import PIECES

DEEP2_K = 4
GATE_FROM, GATE_TO = 400, 428  # plan.md Phase D gate (a): 400-427 lines
TETRIS_18 = e31.TETRIS_18
HIDDEN = 2  # dumped columns hold the 20 visible rows; settle and reach take model rows


def _ruleset() -> str:
    frozen, _ = e29._frozen()
    return frozen["game"]["ruleset"]


def candidates(data: dict[str, np.ndarray], t: int, ruleset: str, interval: int,
               start_level: int = 18) -> list[dict[str, Any]]:
    """Decision ``t`` (board t, the piece placed from it = the next board's ``last``): every
    reachable placement from the spawn, settled, as dump rows with the clear's points."""
    cols = tuple(int(c) << HIDDEN for c in data["columns"][t])
    piece = int(data["last"][t + 1])
    lines = int(data["lines"][t])
    level = native.level_for_lines(lines, start_level)
    period, rows = native.gravity(level, ruleset)
    out = []
    for orientation, x, y, _ in native.reachable(cols, PIECES[piece], Flight(), period=period,
                                                 rows=rows, interval=interval):
        settled, cleared = native.settle(cols, PIECES[piece], orientation, x, y)
        after = lines + cleared
        visible = tuple(c >> HIDDEN for c in settled)
        out.append({"visible": visible, "lines": after, "cleared": cleared,
                    "reward": native.clear_reward(cleared, after, start_level) / TETRIS_18,
                    "features": native.board_features(settled)})
    return out


def _rows(cands: list[dict[str, Any]], drought: int, last: int) -> np.ndarray:
    w = native.WIDTH
    r = np.zeros((len(cands), native.DUMP_STRIDE), np.int32)
    for i, c in enumerate(cands):
        r[i, :w] = c["visible"]
        r[i, w] = c["lines"]
        r[i, w + 2] = drought
        r[i, w + 3] = last
        r[i, w + 4:] = np.round(c["features"]).astype(np.int32)
    return r


def audit(path: Path, late: Path, jobs: int, from_lines: int = 330,
          limit: int | None = None) -> dict[str, Any]:
    d = e23._load_npz(path)
    cfg = e29._config()
    ruleset, interval, cap = _ruleset(), cfg["tap_interval"], cfg["line_cap"]
    same = np.r_[d["game"][1:] == d["game"][:-1], False]
    picks = np.flatnonzero(same & (d["lines"] >= from_lines))
    if limit:
        picks = picks[:limit]
    decisions, rows, used = [], [], 0
    for t in picks:
        cands = candidates(d, int(t), ruleset, interval, cfg["start_level"])
        if not cands:
            continue
        r = _rows(cands, int(d["drought"][t + 1]), int(d["last"][t + 1]))
        well = e31.ready_wells(r[:, :native.WIDTH]) | \
            (np.array([c["cleared"] for c in cands]) == 4)
        nxt = tuple(int(x) for x in d["columns"][t + 1])
        actual = [i for i, c in enumerate(cands)
                  if c["visible"] == nxt and c["lines"] == int(d["lines"][t + 1])]
        decisions.append({"t": int(t), "lines": int(d["lines"][t]), "n": len(cands),
                          "well": well, "actual": actual,
                          "reward": np.array([c["reward"] for c in cands]),
                          "at": used if well.any() else -1})
        if well.any():  # only decisions with a well placement are re-searched
            rows.append(r)
            used += len(r)
    if not rows:
        raise ValueError("no decision with a well placement in these boards")
    allrows = np.concatenate(rows)
    b1, _ = e29.targets(late, allrows, 1, jobs)
    # backup2 only where the search uses it (its best DEEP2_K by points + backup) and on
    # the well placements
    need = np.zeros(len(allrows), bool)
    for dec in decisions:
        if dec["at"] < 0:
            continue
        s = slice(dec["at"], dec["at"] + dec["n"])
        top = np.argsort(-(dec["reward"] + b1[s]), kind="stable")[:DEEP2_K]
        dec["top"] = top
        need[dec["at"] + top] = True
        need[dec["at"] + np.flatnonzero(dec["well"])] = True
    b2 = np.full(len(allrows), np.nan)
    b2[need], _ = e29.targets(late, allrows[need], DEEP2_K, jobs)
    ready_board = e31.ready_wells(d["columns"])
    bands: dict[str, dict[str, list]] = {}
    gate = {k: 0 for k in ("decisions_with_a_well_placement", "picks_a_well_placement",
                           "declined", "future_decides", "cut_at_k", "reward_lower",
                           "reward_equal", "reward_higher")}
    for dec in decisions:
        lo = dec["lines"] // 10 * 10
        band = bands.setdefault(f"{lo}-{lo + 9}", {k: [] for k in (
            "agrees", "has_well", "picks_well", "gap", "gap_reward", "gap_future",
            "future_decides", "cut_at_k", "i_reaches")})
        has = dec["at"] >= 0
        band["has_well"].append(has)
        if ready_board[dec["t"]]:
            band["i_reaches"].append(_i_clears_four(d, dec["t"], ruleset, interval,
                                                    cfg["start_level"]))
        if not has:
            continue
        s = slice(dec["at"], dec["at"] + dec["n"])
        reward, f2, top = dec["reward"], b2[s], dec["top"]
        pick = int(top[np.argmax((reward + f2)[top])])
        if dec["actual"]:
            band["agrees"].append(pick in dec["actual"])
        band["picks_well"].append(bool(dec["well"][pick]))
        if not dec["well"][pick]:
            wells = np.flatnonzero(dec["well"])
            in_top = [w for w in wells if w in top]
            # the term the search compared: backup2 inside its best DEEP2_K, else backup
            if in_top:
                best = int(max(in_top, key=lambda w: reward[w] + f2[w]))
                gap_f = float(f2[pick] - f2[best])
            else:
                best = int(wells[np.argmax((reward + b1[s])[wells])])
                gap_f = float(b1[s][pick] - b1[s][best])
            gap_r = float(reward[pick] - reward[best])
            band["gap"].append(gap_r + gap_f)
            band["gap_reward"].append(gap_r)
            band["gap_future"].append(gap_f)
            band["future_decides"].append(gap_f > 0 and gap_r <= 0)
            band["cut_at_k"].append(not in_top)
            if GATE_FROM <= dec["lines"] < GATE_TO:
                gate["declined"] += 1
                gate["future_decides"] += int(gap_f > 0 and gap_r <= 0)
                gate["cut_at_k"] += int(not in_top)
                gate["reward_lower" if gap_r < 0 else "reward_equal" if gap_r == 0
                     else "reward_higher"] += 1
        if GATE_FROM <= dec["lines"] < GATE_TO:
            gate["decisions_with_a_well_placement"] += 1
            gate["picks_a_well_placement"] += int(bool(dec["well"][pick]))
    mean = lambda x: round(float(np.mean(x)), 4) if len(x) else None  # noqa: E731
    table = {k: {"decisions": len(v["has_well"]), "agrees": mean(v["agrees"]),
                 "with_a_well_placement": mean(v["has_well"]),
                 "picks_a_well_placement": mean(v["picks_well"]),
                 "declined": len(v["gap"]), "searched": len(v["picks_well"]), "mean_gap": mean(v["gap"]),
                 "mean_gap_reward": mean(v["gap_reward"]),
                 "mean_gap_future": mean(v["gap_future"]),
                 "future_decides_share": mean(v["future_decides"]),
                 "cut_at_k_share": mean(v["cut_at_k"]),
                 "ready_boards": len(v["i_reaches"]), "i_reaches_share": mean(v["i_reaches"])}
             for k, v in sorted(bands.items())}
    args = (d["columns"], d["features"], d["lines"], d["drought"], d["last"], cap, "cpu")
    from . import experiment020 as e20
    v = e24._values(e20.read_export(late).eval(), *args)
    actual = (d["final"] - d["score"]) / TETRIS_18
    calibration = {f"{lo}-{lo + 9}": [round(float(v[m].mean()), 3),
                                      round(float(actual[m].mean()), 3), int(m.sum())]
                   for lo in range(320, cap, 10)
                   if (m := (d["lines"] >= lo) & (d["lines"] < lo + 10)).any()}
    return {"data": str(path), "late": e23._relative(late), "from_lines": from_lines,
            "unit": "Tetrises at level 18", "by_10_lines": table,
            "gate_a_400_427": gate | {"future_decides_share": round(
                gate["future_decides"] / gate["declined"], 4) if gate["declined"] else None},
            "calibration_value_actual_boards": calibration,
            "board_stats": e31.board_stats(d)}


def _i_clears_four(d: dict[str, np.ndarray], t: int, ruleset: str, interval: int,
                   start_level: int) -> bool:
    cols = tuple(int(c) << HIDDEN for c in d["columns"][t])
    level = native.level_for_lines(int(d["lines"][t]), start_level)
    period, rows = native.gravity(level, ruleset)
    for orientation, x, y, _ in native.reachable(cols, "I", Flight(), period=period,
                                                 rows=rows, interval=interval):
        if native.settle(cols, "I", orientation, x, y)[1] == 4:
            return True
    return False


def played_with(data: Path) -> Path:
    """The late network a saved round was played with: for 029's own rounds (029-data/t1 or
    t2/roundN.npz) its roundN.json's ``weights``; for 031's round 0, 029's chosen V39 (v29's
    own late network). Anything else needs ``--late``."""
    from . import runner
    if data.parent.name in ("t1", "t2") and data.parent.parent.name == "029-data":
        summary = (runner.PROJECT_ROOT / "experiments" / "029-v39-search-taught" /
                   data.parent.name / f"{data.stem}.json")
        return runner.PROJECT_ROOT / json.loads(summary.read_text())["weights"]
    if data.parent.name == "031-data" and data.stem == "round0":
        return e31.v39_path()
    raise ValueError(f"pass --late: which network played {data} is not known here")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment031audit")
    parser.add_argument("data", type=Path)
    parser.add_argument("--late", type=Path, default=None,
                        help="default: the network the round was played with")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--from-lines", type=int, default=330)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    result = audit(args.data, args.late or played_with(args.data), args.jobs,
                   args.from_lines, args.limit)
    text = json.dumps(result, indent=1)
    if args.out:
        args.out.write_text(text + "\n")
    print(text[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
