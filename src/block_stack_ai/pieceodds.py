"""Direction Phase 0: is the Markov "NES odds" model of the next piece right?

    python -m block_stack_ai.pieceodds exact [--out PATH]
    python -m block_stack_ai.pieceodds empirical RECORD [RECORD...] [--agent NAME]
                                                [--jobs N] [--out PATH]

The search averages the next piece by ``native.nes_odds(previous, piece)``, which sees only
the previous piece. The engine (block-stack core/src/rng.cpp) picks from a 16-bit LFSR that
advances every frame, with the first roll ``((state >> 8) + piece_count) & 7`` and one
retry. ``rng_advance`` and ``rng_piece`` below mirror it. A spawn selects the next preview
in ``tick``: the LFSR advances for the frame, then ``piece_count`` increments and
``rng_piece(state, piece_count, current)`` runs (``current`` is the piece just spawned).

``exact`` computes, for each previous piece and each ``piece_count % 8``, the next-piece
distribution with the selection-time state uniform over the LFSR cycle, and compares it
with the Markov odds. ``empirical`` replays recorded games on the Python binding, checks
that ``rng_piece`` predicts every preview, and tallies (band, count % 8, previous, pick).
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import math
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

from . import experiment013 as e13, experiment015 as e15, native, runner
from .engine import create_game
from .pieces import PIECES

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "direction-phase0-piece-odds"
EXACT = EXPERIMENT_ROOT / "exact.json"
EMPIRICAL = EXPERIMENT_ROOT / "empirical.json"
BANDS = e15.BANDS
SELECTION_ORDER = ("T", "J", "Z", "O", "S", "L", "I")
SPAWN_ID = {"T": 2, "J": 7, "Z": 8, "O": 10, "S": 11, "L": 14, "I": 18, None: 0}

_write = e13._write


# ---------------------------------------------------------------- the engine's RNG

def rng_advance(state: int) -> int:
    feedback = ((state >> 1) ^ (state >> 9)) & 1
    return (state >> 1) | (feedback << 15)


def rng_piece(state: int, piece_count: int, previous: str | None) -> tuple[str, int]:
    """(the pick, the state after) as rng.cpp's ``rng_piece``; ``piece_count`` counts the
    piece being selected."""
    index = ((state >> 8) + piece_count) & 7
    if index < 7 and SELECTION_ORDER[index] != previous:
        return SELECTION_ORDER[index], state
    state = rng_advance(state)
    return SELECTION_ORDER[(((state >> 8) & 7) + SPAWN_ID[previous]) % 7], state


def markov() -> np.ndarray:
    """``native.nes_odds`` as a [previous][piece] table in PIECES order."""
    return np.array([[native.nes_odds(a, b) for b in PIECES] for a in PIECES])


# ---------------------------------------------------------------- exact

def cycle_states() -> tuple[list[int], list[int]]:
    """The LFSR cycle through state 2, in order, and the 16-bit seeds not on it."""
    cycle, state = [], 2
    while True:
        cycle.append(state)
        state = rng_advance(state)
        if state == 2:
            break
    on = set(cycle)
    return cycle, [s for s in range(1 << 16) if s not in on]


def seed_report() -> dict[str, Any]:
    cycle, off = cycle_states()
    reach_zero = [s for s in off if _settles(s) == 0]
    return {"cycle_length": len(cycle), "seeds_on_cycle": len(cycle),
            "seeds_off_cycle": off if len(off) <= 8 else len(off),
            "off_cycle_seeds_that_reach_state_0": reach_zero,
            "off_cycle_seeds_that_join_the_cycle": len(off) - len(reach_zero),
            "longest_tail": max((_tail(s) for s in off if s not in reach_zero), default=0),
            "note": "state 0 is a fixed point; seed 1 steps to 0 and stays"}


def _settles(state: int) -> int | None:
    on = set(cycle_states()[0]) if not hasattr(_settles, "on") else _settles.on
    _settles.on = on
    for _ in range(1 << 16):
        if state in on or state == 0:
            return None if state in on else 0
        state = rng_advance(state)
    return None


def _tail(state: int) -> int:
    on, steps = _settles.on, 0
    while state not in on:
        state, steps = rng_advance(state), steps + 1
    return steps


def exact_table() -> np.ndarray:
    """[count % 8][previous][piece]: the pick's distribution with the selection-time state
    (after the frame's advance) uniform over the cycle."""
    states = np.array(cycle_states()[0], dtype=np.int64)
    table = np.zeros((8, 7, 7))
    order = np.array([PIECES.index(p) for p in SELECTION_ORDER])
    for c in range(8):
        for p, previous in enumerate(PIECES):
            first = ((states >> 8) + c) & 7
            retry = first == 7
            retry |= order[np.minimum(first, 6)] == p
            after = (states >> 1) | ((((states >> 1) ^ (states >> 9)) & 1) << 15)
            second = order[(((after >> 8) & 7) + SPAWN_ID[previous]) % 7]
            pick = np.where(retry, second, order[np.minimum(first, 6)])
            table[c, p] = np.bincount(pick, minlength=7) / len(states)
    return table


def exact() -> dict[str, Any]:
    table, odds = exact_table(), markov()
    average = table.mean(axis=0)
    per_count = np.abs(table - odds).max(axis=(1, 2))
    return {
        "question": "The next-piece distribution given the previous piece and piece_count % 8, "
                    "selection-time RNG state uniform over the cycle, against nes_odds",
        "versions": runner._record_versions(), "pieces": list(PIECES),
        "seeds": seed_report(),
        "convention": "count is piece_count including the piece being selected; the state is "
                      "after the frame's advance; previous is the piece just spawned",
        "markov": odds.tolist(), "table": table.tolist(), "average": average.tolist(),
        "max_abs_diff_average": float(np.abs(average - odds).max()),
        "max_abs_diff_per_count": per_count.tolist(),
        "max_abs_diff_per_count_times_64": (per_count * 64).tolist(),
        "mean_over_counts_of_max_abs_diff": float(per_count.mean()),
        "row_sums_range": [float(table.sum(axis=2).min()), float(table.sum(axis=2).max())],
    }


# ---------------------------------------------------------------- the replay

def replay(config: dict[str, Any], seed: int, inputs: bytes, frames: int | None = None
           ) -> list[tuple[int, str, str, int, int]]:
    """Steps a recorded game and returns each spawn selection as (count, previous, pick,
    level, frames since the last selection). Raises if ``rng_piece`` mispredicts one."""
    events, last = [], 0
    with create_game(**config, seed=seed) as game:
        state = game.state
        for frame, mask in enumerate(inputs[:frames]):
            rng, count = state.rng_state, state.piece_count
            state, _ = game.step(mask)
            if state.piece_count == count:
                continue
            if state.piece_count != count + 1:
                raise ValueError(f"seed {seed} frame {frame}: piece_count jumped")
            pick, after = rng_piece(rng_advance(rng), state.piece_count, state.current_piece)
            if (pick, after) != (state.next_piece, state.rng_state):
                raise ValueError(f"seed {seed} frame {frame}: rng_piece predicts {pick} "
                                 f"and state {after}, the engine {state.next_piece} "
                                 f"and {state.rng_state}")
            events.append((state.piece_count, state.current_piece, pick, state.level,
                           frame - last))
            last = frame
    return events


def _game(job: tuple[dict[str, Any], int, str]) -> dict[str, Any]:
    config, seed, inputs = job
    events = replay(config, seed, base64.b64decode(inputs))
    tally: Counter[str] = Counter()
    gaps: dict[str, list[int]] = {}
    for count, previous, pick, level, gap in events[1:]:
        band = e15._band(level)
        tally[f"{band}|{count % 8}|{previous}|{pick}"] += 1
        gaps.setdefault(band, []).append(gap)
    return {"tally": dict(tally), "gaps": {b: [sum(g), len(g), min(g), max(g)]
                                           for b, g in gaps.items()}}


# ---------------------------------------------------------------- statistics

def chi2_sf_even(x: float, df: int) -> float:
    """P(chi-square with even ``df`` >= x), in closed form."""
    half, term, total = x / 2, 1.0, 1.0
    for k in range(1, df // 2):
        term *= half / k
        total += term
    p = math.exp(-half) * total
    if math.isnan(p):  # exp underflows while the sum overflows: a huge statistic
        return 0.0
    return min(1.0, p)


def _freq(counts: np.ndarray) -> np.ndarray:
    return counts / np.maximum(counts.sum(axis=-1, keepdims=True), 1)


def _chi2(counts: np.ndarray, expected: np.ndarray) -> tuple[float, int]:
    """Statistic and degrees of freedom over the last axis, summed over the others;
    rows with no games are skipped."""
    n = counts.sum(axis=-1, keepdims=True)
    live = n[..., 0] > 0
    stat = (((counts - n * expected) ** 2) / np.maximum(n * expected, 1e-300))[live].sum()
    return float(stat), int(live.sum()) * 6


def _tv(a: np.ndarray, b: np.ndarray, weight: np.ndarray) -> float:
    """Total variation per row, weighted by ``weight`` (rows of ``a``'s leading axes)."""
    return float((0.5 * np.abs(a - b).sum(axis=-1) * weight).sum() / max(weight.sum(), 1))


def _chi_rows(counts: np.ndarray, expected: np.ndarray) -> list[dict[str, Any]]:
    out = []
    for p, name in enumerate(PIECES):
        stat, df = _chi2(counts[p], expected[p])
        out.append({"previous": name, "n": int(counts[p].sum()), "chi2": stat, "df": df,
                    "p": chi2_sf_even(stat, df) if df else None})
    return out


def analyse(tally: dict[str, int]) -> dict[str, Any]:
    odds, table = markov(), exact_table()
    index = {name: i for i, name in enumerate(PIECES)}
    counts = np.zeros((len(BANDS), 8, 7, 7))
    for key, n in tally.items():
        band, count, previous, pick = key.split("|")
        counts[BANDS.index(band), int(count), index[previous], index[pick]] += n
    by_pc = counts.sum(axis=0)            # [count][previous][piece]
    by_p = by_pc.sum(axis=0)              # [previous][piece]
    total = by_p.sum()

    def summary(c: np.ndarray) -> dict[str, Any]:
        """c: [count][previous][piece] for one band or all."""
        pooled, weight = c.sum(axis=0), c.sum(axis=(0, 2))
        freq = _freq(pooled)
        stat, df = _chi2(c, table)
        return {
            "n": int(c.sum()), "frequency": freq.tolist(),
            "tv_vs_markov": _tv(freq, odds, weight),
            "max_abs_diff_vs_markov": float(np.abs(freq - odds)[weight > 0].max(initial=0)),
            "chi2_vs_markov_by_previous": _chi_rows(pooled, odds),
            "tv_vs_exact_per_count": _tv(_freq(c), table, c.sum(axis=2)),
            "chi2_vs_exact_per_count": {
                "by_previous": [
                    {"previous": name, "n": int(c[:, p].sum()),
                     "chi2": _chi2(c[:, p], table[:, p])[0], "df": _chi2(c[:, p], table[:, p])[1],
                     "p": chi2_sf_even(*_chi2(c[:, p], table[:, p]))
                     if _chi2(c[:, p], table[:, p])[1] else None}
                    for p, name in enumerate(PIECES)],
                "chi2": stat, "df": df, "p": chi2_sf_even(stat, df) if df else None}}

    freq = _freq(by_pc)
    live = by_pc.sum(axis=2) > 0
    observed = (freq - odds)[live].ravel()
    predicted = (table - odds)[live].ravel()
    weights = np.repeat(by_pc.sum(axis=2)[live], 7)
    mean_o = (weights * observed).sum() / weights.sum()
    mean_p = (weights * predicted).sum() / weights.sum()
    cov = (weights * (observed - mean_o) * (predicted - mean_p)).sum() / weights.sum()
    var_p = (weights * (predicted - mean_p) ** 2).sum() / weights.sum()
    var_o = (weights * (observed - mean_o) ** 2).sum() / weights.sum()
    # information the count gives, in bits, weighted by the empirical (previous, count)
    w = by_pc.sum(axis=2) / total
    with np.errstate(divide="ignore", invalid="ignore"):
        kl = np.where(table > 0, table * np.log2(table / odds), 0.0).sum(axis=2)
        ratio = np.where(by_pc > 0, by_pc * np.log2(table / odds), 0.0).sum()
    return {
        "games_pieces": int(total),
        "overall": summary(by_pc),
        "by_band": {band: summary(counts[i]) for i, band in enumerate(BANDS)
                    if counts[i].sum()},
        "per_count": {
            "empirical_minus_markov_vs_exact_minus_markov": {
                "correlation": float(cov / math.sqrt(var_p * var_o)) if var_p * var_o else None,
                "slope": float(cov / var_p) if var_p else None,
                "cells": int(live.sum())},
            "max_abs_diff_empirical_vs_exact_by_count": [
                float(np.abs(freq[c] - table[c])[live[c]].max(initial=0)) for c in range(8)],
            "max_abs_diff_empirical_vs_markov_by_count": [
                float(np.abs(freq[c] - odds)[live[c]].max(initial=0)) for c in range(8)],
            "mean_abs_diff_empirical_vs_exact": float(
                (weights * np.abs(freq - table)[live].ravel()).sum() / weights.sum()),
            "mean_abs_diff_empirical_vs_markov": float(
                (weights * np.abs(freq - odds)[live].ravel()).sum() / weights.sum())},
        "information": {
            "mean_kl_bits_exact_per_count_vs_markov": float((w * kl).sum()),
            "log_likelihood_gain_bits_per_piece": float(ratio / total),
            "note": "gain = mean over observed picks of log2(exact per-count prob / Markov prob)"},
        "counts": {f"{b}|{c}|{p}": counts[b, c, p].astype(int).tolist()
                   for b in range(len(BANDS)) for c in range(8) for p in range(7)
                   if counts[b, c, p].sum()},
    }


def load_episodes(paths: list[str], agent: str | None) -> list[tuple[dict[str, Any], int, str]]:
    jobs = []
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            record = json.load(handle)
        game = record.get("configuration", {}).get("game") or record["frozen"]["game"]
        jobs += [(game, e["seed"], e["inputs"]) for e in record["episodes"]
                 if agent is None or e.get("agent") == agent]
    return jobs


def empirical(paths: list[str], agent: str | None, jobs: int) -> dict[str, Any]:
    work = load_episodes(paths, agent)
    with Pool(jobs) as pool:
        games = pool.map(_game, work, chunksize=4)
    tally: Counter[str] = Counter()
    gaps: dict[str, list[int]] = {}
    for game in games:
        tally.update(game["tally"])
        for band, (total, n, low, high) in game["gaps"].items():
            old = gaps.setdefault(band, [0, 0, 1 << 30, 0])
            gaps[band] = [old[0] + total, old[1] + n, min(old[2], low), max(old[3], high)]
    return {
        "question": "Do recorded games' next pieces follow nes_odds, or the exact per-count "
                    "table?", "versions": runner._record_versions(), "records": paths,
        "agent": agent, "games": len(work),
        "selection": "every spawn selection but each game's first (no gap before it); every "
                     "one was predicted exactly by rng_piece from the state before its frame",
        "frames_since_previous_selection": {
            b: {"mean": t / n, "min": lo, "max": hi, "n": n} for b, (t, n, lo, hi) in gaps.items()},
        "pieces": list(PIECES)} | analyse(dict(tally))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("exact").add_argument("--out", type=Path, default=EXACT)
    run = sub.add_parser("empirical")
    run.add_argument("records", nargs="+")
    run.add_argument("--agent")
    run.add_argument("--jobs", type=int, default=28)
    run.add_argument("--out", type=Path, default=EMPIRICAL)
    args = parser.parse_args(argv)
    tick = time.perf_counter()
    result = exact() if args.command == "exact" else \
        empirical(args.records, args.agent, args.jobs)
    result["seconds"] = time.perf_counter() - tick
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write(args.out, result)
    print(f"wrote {args.out} in {result['seconds']:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
