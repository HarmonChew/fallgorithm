"""Experiment 032: the early (base) network slot, the early rows, the hand-over at 230,
the seeds, the stop rule, the choice, the calibration and the evaluation's rule."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from block_stack_ai import experiment025 as e25, experiment029 as e29, experiment030 as e30
from block_stack_ai import experiment031 as e31, experiment032 as e32
from block_stack_ai import experiment032eval as ev, native, register
from test_experiment028 import FRAME_CAP, LIMITS, NET, PARAMS, ROOT, _game, _same

OTHER = (ROOT / "experiments/023-self-taught-value/value_sweep10.bin").read_bytes()
DEEP = dict(commit_level=18, adjust_k=0, adjust_max_level=28, deep2_level=18, deep2_k=2)


def _play(base, mid, mid_from, *, seed=3, line_cap=40):
    return native.late_hybrid_game(base, _game(), seed, late=None, late_from_lines=0,
                                   mid=mid, mid_from_lines=mid_from, **DEEP,
                                   switch_level=1000, line_cap=line_cap, frame_cap=FRAME_CAP,
                                   limits=LIMITS, params=PARAMS)[0]


@pytest.mark.native
def test_the_early_network_is_used_only_below_mid_from():
    seeds = (3, 4, 5)
    # the mid network from 0 lines: the base network is never asked
    assert all(_same(_play(OTHER, NET, 0, seed=s), _play(NET, NET, 0, seed=s)) for s in seeds)
    # from 20 on the mid network: a different base network changes the game below 20
    assert any(not _same(_play(OTHER, NET, 20, seed=s), _play(NET, NET, 20, seed=s))
               for s in seeds)


def _rows(lines):
    r = np.zeros((len(lines), native.DUMP_STRIDE), np.int32)
    r[:, native.WIDTH] = lines
    return r.tobytes()


def test_early_rows_keep_up_to_the_first_board_at_230():
    kept = e32.early_rows(_rows([0, 4, 100, 229, 230, 250, 330]))
    assert kept[:, native.WIDTH].tolist() == [0, 4, 100, 229, 230]
    assert e32.early_rows(_rows([0, 50, 120]))[:, native.WIDTH].tolist() == [0, 50, 120]
    assert e32.early_rows(_rows([0, 228, 232, 236]))[:, native.WIDTH].tolist() == [0, 228, 232]


def test_handover_returns_end_at_the_board_at_230():
    lam = 0.5
    d = {"lines": np.array([200, 228, 232, 100, 110]), "game": np.array([0, 0, 0, 1, 1]),
         "score": np.array([0, 1, 3, 0, 2], np.int64) * e32.TETRIS_18,
         "final": np.array([99, 99, 99, 5, 5], np.int64) * e32.TETRIS_18}
    backup = np.array([4.0, 6.0, 10.0, 2.0, 2.0])
    got = e30.handover_returns(backup, d, lam, late_from=e32.MID_FROM)
    g1 = 0.5 * 6 + 0.5 * (2 + 10)
    g0 = 0.5 * 4 + 0.5 * (1 + g1)
    h1 = 0.5 * 2 + 0.5 * (5 - 2)
    h0 = 0.5 * 2 + 0.5 * (2 + h1)
    assert np.allclose(got, [g0, g1, h0, h1])


def test_seeds_are_fresh_disjoint_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(e32, "SEEDS", tmp_path / "seeds.json")
    stored = e29._seeds()
    s = e32.make_seeds()
    start = e31._seeds()["used_slice"][1]
    assert s["used_slice"][0] == start == 6100
    used = set(stored["training_seeds"][:start])
    blocks = [e32.round_seeds(k) for k in range(e32.MAX_SWEEPS)]
    assert len(blocks[0]) == e32.ROUND0_SEEDS
    assert all(len(b) == e32.ROUND_SEEDS for b in blocks[1:])
    flat = [x for b in blocks for x in b]
    probe = s["probe_seeds"]
    assert len(probe) == len(set(probe)) == e32.PROBE_SEEDS
    assert s["used_slice"] == [6100, 6100 + 500 + 400 + 200 * 9]
    assert len(set(flat)) == len(flat) and not set(flat) & (used | set(probe))
    assert not set(probe) & (used | set(stored["probe_seeds"]))


def test_stop_rule(monkeypatch):
    means = [1, 2, 3, 4, 5, 4, 4, 4, 9, 9]
    monkeypatch.setattr(e32, "_means", lambda upto: means[:upto])
    assert [e32.should_stop(k) for k in range(1, 11)] == \
        [False] * 7 + [True, False, True]


def _probe(tmp_path, sweep, mean):
    (tmp_path / f"probe{sweep}.json").write_text(json.dumps(
        {"sweep": sweep, "weights": f"w{sweep}",
         "paired_vs_v39r": {"total": {"score": {"mean": mean}}},
         "ranking": {e32.RANK_KEY: {"network_odd_loss": 1.0}}}))


def test_choose_takes_the_highest_probe_above_0(monkeypatch, tmp_path):
    monkeypatch.setattr(e32, "OUT", tmp_path)
    monkeypatch.setattr(e32, "CHOICE", tmp_path / "chosen.json")
    for sweep, mean in ((1, 5.0), (2, 9.0), (3, 7.0)):
        _probe(tmp_path, sweep, mean)
    (tmp_path / "probe_base.json").write_text("{}")
    assert e32.choose()["chosen"]["sweep"] == 2
    for sweep, mean in ((1, -5.0), (2, -1.0), (3, 0.0)):
        _probe(tmp_path, sweep, mean)
    assert e32.choose()["chosen"] is None


def test_calibration_defines_targets_to_the_handover():
    d = {"lines": np.array([0, 20, 232, 0, 25]), "game": np.array([0, 0, 0, 1, 1]),
         "score": np.array([0, 1, 4, 0, 2], np.int64) * e32.TETRIS_18,
         "final": np.array([50, 50, 50, 3, 3], np.int64) * e32.TETRIS_18}
    v = np.array([1.0, 2.0, 0.0, 3.0, 4.0])
    anchor = np.array([0.0, 0.0, 30.0, 0.0, 0.0])
    got = e32.calibration(d, v, anchor)
    # game 0: board at 20 -> 3 points to the hand-over + V29's 30 = 33; board at 0 -> 34
    # game 1: no hand-over: points along the game, then the actual rest (3 and 1)
    assert got["0-19"] == [2.0, 0.5 * (50 + 3), 0.5 * (34 + 3)]
    assert got["20-39"] == [3.0, 0.5 * (49 + 1), 0.5 * (33 + 1)]
    assert set(got) == {"0-19", "20-39"}  # the hand-over board (232) is not a step
    # the last step stops at 229, without the hand-over board
    d2 = {"lines": np.array([225, 231]), "game": np.array([0, 0]),
          "score": np.array([0, 2], np.int64) * e32.TETRIS_18,
          "final": np.array([9, 9], np.int64) * e32.TETRIS_18}
    got2 = e32.calibration(d2, np.array([1.0, 7.0]), np.array([0.0, 5.0]))
    assert got2 == {"220-229": [1.0, 9.0, 7.0]}


def _episode(seed, score, lines=300):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    by_level = {"18": {"single": 1, "double": 0, "triple": 0, "four_line": 3, "points": 9},
                "25": {"single": 2, "double": 0, "triple": 0, "four_line": 1, "points": 5},
                "39": {"single": 2, "double": 0, "triple": 0, "four_line": 1, "points": 50}}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, (1, 2, 3, 4))),
                      "entry": {"29": entry, "39": entry}, "by_level": by_level}}


def test_level_stats_count_games_reaching_the_band():
    eps = [_episode(0, 1, lines=120), _episode(1, 1, lines=300)]
    s18 = e32.level_stats(eps, 18, 18, 0)
    assert s18["games"] == 2 and s18["tetrises"] == 3.0 and s18["tetris_line_share"] == pytest.approx(12 / 13, abs=1e-4)
    s19 = e32.level_stats(eps, 19, 28, 130)
    assert s19["games"] == 1 and s19["tetrises"] == 1.0 and s19["singles"] == 2.0


def _store(path, episodes, **extra):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes, **extra}, out)


def _fake(monkeypatch, tmp_path, stage, gains):
    monkeypatch.setattr(ev, "OUT", tmp_path / "out")
    monkeypatch.setattr(ev, "GAMES", tmp_path / "games32")
    monkeypatch.setattr(e32, "v39r_games", lambda stage: [_episode(s, 4000) for s in range(3)])
    monkeypatch.setattr(e31, "_v29_games", lambda stage: [_episode(s, 3000) for s in range(3)])
    monkeypatch.setattr(e30, "_v39_games", lambda stage: [_episode(s, 2000) for s in range(3)])
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e25, "_seeds", lambda stage: [0, 1, 2])
    (tmp_path / "out").mkdir(exist_ok=True)
    _store(register.games_path(stage, "017"), [_episode(s, 1000) for s in range(3)])
    _store(ev.games_path(stage), [_episode(s, 4000 + g) for s, g in enumerate(gains)],
           chosen={"sweep": 3})


def test_screening_promotes_at_15k(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [20_000, 15_000, 10_000])
    result = ev.summarize("screening")
    assert result["promoted"] is True
    assert result["paired_vs_v39r"]["v18"]["total"]["score"]["mean"] == pytest.approx(15_000)
    assert result["paired_vs_v29"]["v18"]["total"]["score"]["mean"] == pytest.approx(16_000)
    assert result["paired_vs_017"]["v39r"]["total"]["score"]["mean"] == pytest.approx(3000)
    assert result["style"]["v18"]["level_18"]["tetrises"] == 3.0
    _fake(monkeypatch, tmp_path, "screening", [14_999] * 3)
    assert ev.summarize("screening")["promoted"] is False


def test_development_and_heldout_need_the_interval_above_0(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "development", [20_000, 20_000, 20_000])
    assert ev.summarize("development")["kept"] is True
    _fake(monkeypatch, tmp_path, "development", [60_000, -10_000, 10_000])
    assert ev.summarize("development")["kept"] is False
    monkeypatch.setattr(e25, "_baseline", lambda stage: [_episode(s, 1000) for s in range(3)])
    _fake(monkeypatch, tmp_path, "heldout", [1, 2, 3])
    assert ev.summarize("heldout")["passed"] is True
