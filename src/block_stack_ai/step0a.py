"""Step 0a of ROADMAP-after-024: accounting checks and the stored games' report.

    python -m block_stack_ai.step0a accounting [--games N] [--jobs J]
    python -m block_stack_ai.step0a report [--out PATH] [--games-root DIR] [--jobs J]

``accounting`` writes experiments/register/accounting.json: the clear points of replayed
017 and V games against ``native.clear_reward``, V at the line cap and at a top-out, V's
backup against the NES odds, and (as text) how 017's rollouts end. ``report`` writes
experiments/register/reports.json: per stored run, points by band, level band and clear
type, Tetris rate, the line distribution, the chance to reach 29 and 39, and the boards
at those levels.
"""

from __future__ import annotations

import argparse
import base64
import glob
import gzip
import json
import statistics
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

from . import experiment013 as e13, experiment015 as e15, native, register, runner
from .engine import create_game

REGISTER = runner.PROJECT_ROOT / "experiments" / "register"
ACCOUNTING = REGISTER / "accounting.json"
REPORTS = REGISTER / "reports.json"
GAMES_025 = runner.PROJECT_ROOT / "experiments" / "025-hybrids" / "games"
HELDOUT_CACHE = runner.PROJECT_ROOT / "runs" / "step0a" / "017-heldout-stats.json.gz"
CLEAR_POINTS = {"single": 40, "double": 100, "triple": 300, "four_line": 1200}
BANDS = register.BANDS
START_LEVEL, LINE_CAP, TAP_INTERVAL = 18, 430, 2
ARGS = dict(line_cap=LINE_CAP, start_level=START_LEVEL, double_killscreen=True,
            tap_interval=TAP_INTERVAL)
# README of BetaTetris NN v0.1.0 (ROADMAP-after-024 section 1); other seeds and RNG.
BETATETRIS = {"label": "BetaTetris NN v0.1.0 (descriptive, different seeds and RNG)",
              "bands": dict(zip(BANDS, (637_000, 592_000, 734_000, 380_000))),
              "mean_lines": 392, "mean_score": 2_342_000}
FACTS_017 = [
    "native/rollout.hpp rollout(): a hand rollout that finds no placement for a piece "
    "(choice_.found false) returns at once with total -= rollout_death * (depth - step), "
    "so each missing placement of the remaining depth costs rollout_death.",
    "The hand rollout() has no line-cap stop: its loop runs step < depth only, so it keeps "
    "placing and summing the hand value past 430 lines (leaf_rollout, 023's, stops at "
    "leaf_line_cap_).",
    "The hand evaluation (value_of, eval.hpp) has no line-cap term; the lines only set the "
    "level (clear points and phase).",
]


# ---------------------------------------------------------------- accounting

def clear_points_check(config: dict[str, Any], seed: int, inputs: bytes) -> dict[str, Any]:
    """Replay a game on the binding; on each frame where the lines rise, the score delta
    against ``native.clear_reward`` (agents never soft drop); frames that change the score
    with no clear; and the pieces spawned at 420 lines or more."""
    checked, bad, no_clear, late, count = 0, [], 0, 0, -1
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for frame, mask in enumerate(inputs):
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                late += state.lines >= 420
            lines, score = state.lines, state.score
            state, _ = game.step(mask)
            gained = state.score - score
            if state.lines > lines:
                checked += 1
                want = native.clear_reward(state.lines - lines, state.lines, START_LEVEL)
                if gained != want:
                    bad.append({"frame": frame, "cleared": state.lines - lines,
                                "lines_after": state.lines, "got": gained, "want": want})
            elif gained:
                no_clear += 1
    return {"seed": seed, "lines": state.lines, "score": state.score, "clears": checked,
            "mismatches": bad, "score_without_clear": no_clear, "pieces_at_420_plus": late}


def _v_clear_job(job: tuple[dict[str, Any], bytes, int]) -> dict[str, Any]:
    frozen, weights, seed = job
    played = register.native_game(frozen, weights, seed)
    return clear_points_check(frozen, seed, played["inputs"])


def _record_job(job: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    frozen, episode = job
    return clear_points_check(frozen, episode["seed"], base64.b64decode(episode["inputs"]))


def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [dict(m, seed=r["seed"]) for r in rows for m in r["mismatches"]]
    return {"pass": not bad, "games": len(rows), "clears_checked": sum(r["clears"] for r in rows),
            "mismatches": len(bad), "first_mismatches": bad[:5],
            "frames_with_score_and_no_clear": sum(r["score_without_clear"] for r in rows),
            "pieces_at_420_plus_per_game": [r["pieces_at_420_plus"] for r in rows]}


def check_clear_points(games: int, jobs: int) -> dict[str, Any]:
    f17, _ = register.load_frozen("017")
    episodes = register._reference("017", games)
    fv, weights = register.load_frozen("v15")
    seeds = register.set_seeds("screening")[:20]
    with Pool(jobs) as pool:
        r17 = pool.map(_record_job, [(f17, e) for e in episodes], chunksize=1)
        rv = pool.map(_v_clear_job, [(fv, weights, s) for s in seeds], chunksize=1)
    return {"unit": "points: clear_points[cleared] * (level after the clear + 1)",
            "017": _summarise(r17), "v15": _summarise(rv),
            "pass": not any(r["mismatches"] for r in r17 + rv)}


def row(columns=(0,) * native.WIDTH, lines=0, drought=0, last=-1) -> np.ndarray:
    out = np.zeros(native.DUMP_STRIDE, np.int32)
    out[:native.WIDTH] = columns
    out[native.WIDTH], out[native.WIDTH + 2], out[native.WIDTH + 3] = lines, drought, last
    return out


def _children(kids: bytes) -> np.ndarray:
    return np.frombuffer(kids, np.int32).reshape(-1, native.DUMP_STRIDE)


def check_cap(net: bytes) -> dict[str, Any]:
    rows = b"".join(row(lines=n).tobytes() for n in (430, 431))
    values = native.net_values(net, rows, line_cap=LINE_CAP, start_level=START_LEVEL)
    backups, _ = native.backup_values(net, rows, **ARGS)
    crossing = check_cap_crossing(net)
    return {"pass": values == [0.0, 0.0] and backups == [0.0, 0.0]
            and len(crossing) == 2 and all(c["pass"] for c in crossing),
            "net_values_430_431": values, "backup_values_430_431": backups,
            "crossing_the_cap": crossing,
            "crossing_note": "boards at 428 and 429 lines (one open column, uniform odds): "
                             "each child that crosses 430 must be valued at its clear points "
                             "plus 0, and the backup equal the mean of clear points plus value"}


def _topout_board(net: bytes) -> tuple[np.ndarray, np.ndarray] | None:
    """A board where only some next pieces have a placement, found by trying stacks of
    near-full columns in both bit orders."""
    rng = np.random.default_rng(0)
    for _ in range(400):
        heights = rng.integers(14, 20, native.WIDTH)
        heights[rng.integers(native.WIDTH)] = rng.integers(0, 14)
        for top_first in (False, True):
            cols = [((1 << int(h)) - 1) << (20 - int(h)) if top_first else (1 << int(h)) - 1
                    for h in heights]
            board = row(cols)
            _, kids = native.backup_values(net, board.tobytes(), children=True, **ARGS)
            lines = _children(kids)[:, native.WIDTH]
            if 0 < (lines == -1).sum() < 7:
                return board, _children(kids)
    return None


def _parts(net: bytes, parent: np.ndarray, kids: np.ndarray) -> list[tuple[int, float, float]]:
    """(child index, clear points, net value of the child) of each piece with a child."""
    keep = [i for i in range(len(kids)) if kids[i, native.WIDTH] != -1]
    if not keep:
        return []
    values = native.net_values(net, kids[keep].tobytes(), line_cap=LINE_CAP,
                               start_level=START_LEVEL)
    return [(i, native.clear_reward(int(kids[i, native.WIDTH] - parent[native.WIDTH]),
                                    int(kids[i, native.WIDTH]), START_LEVEL), v)
            for i, v in zip(keep, values)]


def check_cap_crossing(net: bytes) -> dict[str, Any]:
    """Boards at 428 and 429 lines with a clear that crosses the cap: the backup must give
    that child its clear points and value 0."""
    cases = []
    for lines in (428, 429):
        for column in range(native.WIDTH):
            for top_first in (False, True):
                depth = 430 - lines  # open rows, so a clear of that many lines reaches the cap
                full = ((1 << depth) - 1) << (20 - depth) if top_first else (1 << depth) - 1
                cols = [0 if c == column else full for c in range(native.WIDTH)]
                board = row(cols, lines=lines)
                backup, kids = native.backup_values(net, board.tobytes(), children=True, **ARGS)
                kids = _children(kids)
                parts = _parts(net, board, kids)
                crossing = [(i, c, v) for i, c, v in parts if kids[i, native.WIDTH] >= LINE_CAP]
                if crossing:
                    expected = sum(c + v for _, c, v in parts) / 7
                    cases.append({
                        "lines": lines, "board": board[:native.WIDTH].tolist(),
                        "crossing": [{"piece": native.PIECES[i], "lines_after": int(kids[i, native.WIDTH]),
                                      "clear_points": c, "child_value": v} for i, c, v in crossing],
                        "backup": backup[0], "expected": expected,
                        "pass": all(v == 0.0 and c > 0 for _, c, v in crossing)
                        and abs(backup[0] - expected) < 1e-6 * max(1.0, abs(expected))})
                    break
            else:
                continue
            break
    return cases


def check_topout(net: bytes) -> dict[str, Any]:
    found = _topout_board(net)
    if found is None:
        return {"pass": False, "problem": "no partial top-out board found"}
    board, kids = found
    backup = native.backup_values(net, board.tobytes(), **ARGS)[0][0]
    parts = _parts(net, board, kids)
    expected = sum(_odds(int(board[native.WIDTH + 3]), i) * (c + v) for i, c, v in parts)
    missing = [i for i in range(7) if kids[i, native.WIDTH] == -1]
    return {"pass": abs(backup - expected) < 1e-6 * max(1.0, abs(expected)), "board": board[:native.WIDTH].tolist(),
            "pieces_without_a_placement": [native.PIECES[i] for i in missing],
            "backup": backup, "expected_sum_over_pieces_with_a_child": expected,
            "surviving_piece_values": {native.PIECES[i]: v for i, _, v in parts},
            "note": "the surviving pieces' values on this board are negative, so a top-out "
                    "(0) beats surviving here: V extrapolates on near-dead boards. On real V "
                    "boards all values were positive (min 7,651 over 928 boards of seed "
                    "13770); check d's min_child_value is the minimum over its own 200 sampled boards of that seed (also positive)."}


def _odds(last: int, piece: int) -> float:
    return 1 / 7 if last == -1 else native.nes_odds(native.PIECES[last], native.PIECES[piece])


def check_odds(net: bytes, frozen: dict[str, Any], boards: int = 200) -> dict[str, Any]:
    seed = register.set_seeds("screening")[0]
    _, dump = native.net_game(net, frozen["game"], seed, line_cap=LINE_CAP,
                              frame_cap=frozen["frame_cap"], limits=e13._limits(frozen), dump=True)
    rows = np.frombuffer(dump, np.int32).reshape(-1, native.DUMP_STRIDE)
    rows = rows[np.linspace(0, len(rows) - 1, min(boards, len(rows))).astype(int)]
    worst, compared, lowest = 0.0, 0, float("inf")
    for parent in rows:
        for last in range(-1, 7):
            probe = parent.copy()
            probe[native.WIDTH + 3] = last
            backup, kids = native.backup_values(net, probe.tobytes(), children=True, **ARGS)
            kids = _children(kids)
            parts = _parts(net, probe, kids)
            expected = sum(_odds(last, i) * (c + v) for i, c, v in parts)
            lowest = min([lowest] + [v for _, _, v in parts])
            worst = max(worst, abs(backup[0] - expected))
            compared += 1
    return {"pass": worst < 1e-6, "seed": seed, "boards": len(rows), "comparisons": compared,
            "max_abs_error_points": worst,
            "min_child_value": lowest,
            "note": "self-consistency of the backup against the C++ nes_odds table; whether "
                    "that table is NES-exact is Direction Phase 0's check"}


def check_pieces_late(clear: dict[str, Any]) -> dict[str, Any]:
    late = clear["017"]["pieces_at_420_plus_per_game"]
    return {"games": len(late), "mean_pieces_at_420_plus": round(float(np.mean(late)), 1),
            "min": min(late), "max": max(late)}


def accounting(games: int, jobs: int) -> dict[str, Any]:
    frozen, weights = register.load_frozen("v15")
    params = register.load_frozen("017")[0]["params"]
    clear = check_clear_points(games, jobs)
    out = {"a_clear_points": clear, "b_cap": check_cap(weights),
           "c_topout": check_topout(weights), "d_odds": check_odds(weights, frozen),
           "e_017_terminal": {"facts": FACTS_017, "rollout_death": params["rollout_death"],
                              "region_size": check_pieces_late(clear),
                              "note": "pieces spawned at 420+ lines in the replayed 017 games"}}
    out["pass"] = all(out[k]["pass"] for k in ("a_clear_points", "b_cap", "c_topout", "d_odds"))
    REGISTER.mkdir(parents=True, exist_ok=True)
    e13._write(ACCOUNTING, out)
    return out


# ---------------------------------------------------------------- report

def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(values, q))


def line_distribution(lines: list[int]) -> dict[str, Any]:
    n = len(lines)
    return {"mean": round(statistics.fmean(lines), 1), "median": statistics.median(lines),
            "p10": percentile(lines, 10), "p25": percentile(lines, 25),
            "share_below_230": sum(x < 230 for x in lines) / n,
            "share_below_330": sum(x < 330 for x in lines) / n,
            "share_at_cap": sum(x >= LINE_CAP for x in lines) / n}


def level_bands(stats: dict[str, Any]) -> dict[str, dict[str, float]]:
    """One game's clears and points by level band and clear type (the points as the clear
    scored, recorded by ``register.game_stats``; accounting checks them against
    clear_points * (level after the clear + 1))."""
    out = {b: dict.fromkeys(CLEAR_POINTS, 0) | {f"{c}_points": 0 for c in CLEAR_POINTS}
           | {"points": 0} for b in BANDS}
    for level, entry in stats["by_level"].items():
        band = out[e15._band(int(level))]
        band["points"] += entry["points"]
        for clear in CLEAR_POINTS:
            band[clear] += entry[clear]
            band[f"{clear}_points"] += entry[f"{clear}_points"]
    return out


def summarise_run(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(episodes)
    results = [e["result"] for e in episodes]
    stats = [e["stats"] for e in episodes]
    per_game = [level_bands(s) for s in stats]
    scores = [r["score"] for r in results]
    lines = [r["lines"] for r in results]
    bands = {b: {k: round(statistics.fmean(g[b][k] for g in per_game), 1)
                 for k in per_game[0][b]} for b in BANDS}
    tetris_points = sum(g[b]["four_line_points"] for g in per_game for b in BANDS)
    out: dict[str, Any] = {
        "games": n, "mean_score": round(statistics.fmean(scores)),
        "score_by_band": {b: round(statistics.fmean(s["bands"][b] for s in stats)) for b in BANDS},
        "by_level_band_and_clear": bands,
        "tetris_points_share": round(tetris_points / max(1, sum(scores)), 4),
        "tetris_rate": round(4 * sum(g[b]["four_line"] for g in per_game for b in BANDS)
                             / max(1, sum(lines)), 4),
        "lines": line_distribution(lines)}
    for level in register.ENTRY_LEVELS:
        reached = [s for s in stats if s["entry"][str(level)]]
        out[f"p_reach_{level}"] = len(reached) / n
        out[f"entry_{level}"] = ({k: round(statistics.fmean(s["entry"][str(level)][k]
                                                              for s in reached), 1)
                                  for k in reached[0]["entry"][str(level)]} if reached else None)
    reached39 = [s for s in stats if s["entry"]["39"]]
    out["points_39_plus_given_reach_39"] = (
        round(statistics.fmean(s["bands"]["39+"] for s in reached39)) if reached39 else None)
    return out


def _stats_job(job: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    frozen, episode = job
    return register.game_stats(frozen, episode["seed"], base64.b64decode(episode["inputs"]))


def heldout_017(jobs: int) -> list[dict[str, Any]]:
    """017's held-out record episodes, with ``stats`` (cached: the replays are slow)."""
    frozen, _ = register.load_frozen("017")
    episodes = register._reference("017", 10**9)
    if HELDOUT_CACHE.exists():
        with gzip.open(HELDOUT_CACHE, "rt", encoding="utf-8") as handle:
            cache = json.load(handle)
    else:
        cache = {}
    todo = [e for e in episodes if str(e["seed"]) not in cache or any(
        "single_points" not in row for row in cache[str(e["seed"])]["by_level"].values())]
    if todo:
        with Pool(jobs) as pool:
            for e, s in zip(todo, pool.map(_stats_job, [(frozen, e) for e in todo], chunksize=1)):
                cache[str(e["seed"])] = s
        HELDOUT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(HELDOUT_CACHE, "wt", encoding="utf-8") as handle:
            json.dump(cache, handle)
    return [e | {"stats": cache[str(e["seed"])]} for e in episodes]


def with_clear_points(frozen: dict[str, Any], episodes: list[dict[str, Any]], jobs: int
                      ) -> list[dict[str, Any]]:
    """``episodes`` with stats that hold the points of each clear type: games stored by
    the earlier ``register.game_stats`` are replayed again."""
    old = [e for e in episodes
           if any("single_points" not in row for row in e["stats"]["by_level"].values())]
    if not old:
        return episodes
    with Pool(jobs) as pool:
        fresh = pool.map(_stats_job, [(frozen, e) for e in old], chunksize=1)
    again = {e["seed"]: s for e, s in zip(old, fresh)}
    return [e | {"stats": again[e["seed"]]} if e["seed"] in again else e for e in episodes]


def stored_runs(games_root: Path, jobs: int = 4) -> dict[str, list[dict[str, Any]]]:
    """The stored runs: the register's 017 and v15 games under ``games_root`` and 025's
    games, from ``games_root`` too unless it is the default (then the project's own)."""
    paths = [games_root / f"{s}-{a}.json.gz" for s in ("screening", "development")
             for a in ("017", "v15")]
    root = GAMES_025 if games_root == register.GAMES else games_root
    paths += [Path(p) for p in sorted(glob.glob(str(root / "*.json.gz")))]
    runs = {}
    for path in dict.fromkeys(paths):
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                record = json.load(handle)
            frozen = register.load_frozen("v15" if path.name.endswith("-v15.json.gz")
                                          else "017")[0]
            runs[path.name.removesuffix(".json.gz")] = with_clear_points(
                frozen, record["episodes"], jobs)
    return runs


def table(reports: dict[str, Any]) -> str:
    head = ["run", "games", "mean score", *BANDS, "mean lines", "tetris rate", "P29", "P39",
            "39+ pts given reach 39"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for name, r in reports["runs"].items():
        cells = [name, r["games"], f"{r['mean_score']:,}",
                 *(f"{r['score_by_band'][b]:,}" for b in BANDS), r["lines"]["mean"],
                 f"{r['tetris_rate']:.1%}", f"{r['p_reach_29']:.0%}", f"{r['p_reach_39']:.0%}",
                 f"{r['points_39_plus_given_reach_39']:,}"
                 if r["points_39_plus_given_reach_39"] is not None else "-"]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    b = BETATETRIS
    lines.append("| " + " | ".join(["BetaTetris NN (descriptive)", "-", f"{b['mean_score']:,}",
                                    *(f"{b['bands'][x]:,}" for x in BANDS), str(b["mean_lines"]),
                                    "-", "-", "-", "-"]) + " |")
    return "\n".join(lines)


def report(out: Path, games_root: Path, jobs: int) -> dict[str, Any]:
    runs = stored_runs(games_root, jobs)
    runs["017-heldout"] = heldout_017(jobs)
    reports = {"betatetris": BETATETRIS, "games_root": str(games_root),
               "runs": {name: summarise_run(eps) for name, eps in runs.items()}}
    e13._write(out, reports)
    print(table(reports))
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.step0a")
    commands = parser.add_subparsers(dest="command", required=True)
    a = commands.add_parser("accounting")
    a.add_argument("--games", type=int, default=50)
    a.add_argument("--jobs", type=int, default=4)
    r = commands.add_parser("report")
    r.add_argument("--out", type=Path, default=REPORTS)
    r.add_argument("--games-root", type=Path, default=register.GAMES)
    r.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args(argv)
    if args.command == "accounting":
        result = accounting(args.games, args.jobs)
        print(json.dumps({k: (v.get("pass") if isinstance(v, dict) else v)
                          for k, v in result.items()}, indent=1))
    else:
        report(args.out, args.games_root, args.jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
