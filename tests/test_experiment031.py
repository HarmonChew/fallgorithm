"""Experiment 031: the runner's pure parts (clears with the game-ending one, ready wells,
seeds, stop rule, choice)."""

from __future__ import annotations

import json

import numpy as np

from block_stack_ai import experiment029 as e29, experiment030 as e30, experiment031 as e31
from block_stack_ai import native


def _column_masks(rows_filled: dict[int, list[int]]) -> np.ndarray:
    """A dumped board from {visible row (0 top .. 19 bottom): filled columns}: column
    bitmasks with bit r = visible row r (c_api.cpp fn_dump_game)."""
    cols = np.zeros(10, np.int64)
    for row, filled in rows_filled.items():
        for c in filled:
            cols[c] |= 1 << row
    return cols


def test_ready_wells():
    full_but = lambda g: [c for c in range(10) if c != g]  # noqa: E731
    four = {r: full_but(9) for r in (16, 17, 18, 19)}
    ready = _column_masks(four)
    three = _column_masks({r: full_but(9) for r in (17, 18, 19)})
    crooked = _column_masks({16: full_but(8), 17: full_but(9), 18: full_but(9),
                             19: full_but(9)})
    covered_top = _column_masks(four | {0: [9]})          # blocked in the top visible row
    # four ready rows over a fifth row that is open at the well too: the I falls 5 deep
    deep = _column_masks({r: full_but(9) for r in (15, 16, 17, 18)} | {19: [0, 1]})
    high = _column_masks({r: full_but(0) for r in (5, 6, 7, 8)} | {9: list(range(10))})
    got = e31.ready_wells(np.stack([ready, three, crooked, covered_top, deep, high]))
    assert got.tolist() == [True, False, False, False, False, True]


def test_near_cap_stats_on_stored_games():
    import gzip
    from block_stack_ai import experiment030eval as e30eval
    with gzip.open(e30eval.games_path("screening"), "rt", encoding="utf-8") as handle:
        episodes = json.load(handle)["episodes"]
    got = e31.near_cap_stats(episodes)
    assert got["games"] == sum(e["result"]["lines"] >= 380 for e in episodes) > 0
    assert got["tetrises"] > 0
    late = e29.late_stats(episodes)
    assert got["lines"] < late["lines"]  # 44+ is part of 39+


def _data(lines, games, score, final):
    return {"lines": np.array(lines), "game": np.array(games),
            "score": np.array(score, np.int64), "final": np.array(final, np.int64)}


def test_clears_count_the_game_ending_clear():
    lvl = lambda n: native.level_for_lines(n, 18) + 1  # noqa: E731
    # game 0: 420 -> 421 (single) -> 425 (tetris) -> ends at 429 by a tetris (cap)
    # game 1: one board at 400 and it tops out (no points after it)
    # game 2: a board at 428, then a double ends it (to 430)
    s0 = [0, 40 * lvl(421), 40 * lvl(421) + 1200 * lvl(425)]
    final0 = s0[2] + 1200 * lvl(429)
    d = _data([420, 421, 425, 429, 400, 428], [0, 0, 0, 0, 1, 2],
              [s0[0], s0[1], s0[2], s0[2], 5, 7], [final0] * 4 + [5, 7 + 100 * lvl(428)])
    d["score"][3] = s0[2]
    assert e31.clears(d).tolist() == [1, 4, 4, 4, 0, 2]


def test_board_stats_bands():
    d = _data([320, 330, 331, 335], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0])
    d["columns"] = np.zeros((4, 10), np.int64)
    out = e31.board_stats(d)
    assert out["330-379"]["boards"] == 3 and out["320-329"]["boards"] == 1
    assert out["420-427"]["ready_well_share"] is None


def test_seeds_are_fresh_disjoint_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(e31, "SEEDS", tmp_path / "seeds.json")
    stored = e29._seeds()
    s = e31.make_seeds()
    start = e30._seeds()["used_slice"][1]
    assert s["used_slice"][0] == start == 4100
    used = set(stored["training_seeds"][:start]) | set(e30._seeds()["probe_seeds"])
    blocks = [e31.round_seeds(k) for k in range(e31.MAX_SWEEPS)]
    assert len(blocks[0]) == e31.ROUND0_SEEDS
    assert all(len(b) == e31.ROUND_SEEDS for b in blocks[1:])
    flat = [x for b in blocks for x in b]
    probe = s["probe_seeds"]
    assert len(probe) == len(stored["probe_seeds"]) + e31.EXTRA_PROBE_SEEDS
    assert len(set(flat)) == len(flat) and not set(flat) & (used | set(probe))
    assert not set(probe[len(stored["probe_seeds"]):]) & used


def test_stop_rule(monkeypatch):
    means = [1, 2, 3, 4, 5, 4, 4, 4]
    monkeypatch.setattr(e31, "_means", lambda upto: means[:upto])
    assert [e31.should_stop(k) for k in range(1, 9)] == [False] * 7 + [True]
    means2 = [1, 9, 3, 4, 5, 4, 4, 4]
    monkeypatch.setattr(e31, "_means", lambda upto: means2[:upto])
    assert [e31.should_stop(k) for k in range(1, 6)] == [False] * 4 + [True]


def test_choose_skips_worse_ranking(monkeypatch, tmp_path):
    monkeypatch.setattr(e31, "OUT", tmp_path)
    key = "commit 39+"
    monkeypatch.setattr(e31, "v39_ranking", lambda device: {key: {"network_odd_loss": 10.0}})
    for sweep, mean, loss in ((1, 5.0, 9.0), (2, 9.0, 11.0), (3, 7.0, 10.0)):
        (tmp_path / f"probe{sweep}.json").write_text(json.dumps(
            {"sweep": sweep, "weights": f"w{sweep}",
             "paired_vs_v29": {"total": {"score": {"mean": mean}}},
             "ranking": {key: {"network_odd_loss": loss}}}))
    (tmp_path / "probe_base.json").write_text("{}")
    assert e31.choose()["chosen"]["sweep"] == 3
