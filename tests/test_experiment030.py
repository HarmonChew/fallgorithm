"""Experiment 030: the middle network (NetSearcher::set_mid_net), the exploration end, the
hand-over lambda-returns and the runner's pure parts."""

from __future__ import annotations

import json

import numpy as np
import pytest

from block_stack_ai import experiment029 as e29, experiment030 as e30, native
from test_experiment028 import FRAME_CAP, LIMITS, NET, PARAMS, ROOT, _game, _same

OTHER = (ROOT / "experiments/023-self-taught-value/value_sweep10.bin").read_bytes()
DEEP = dict(commit_level=18, adjust_k=0, adjust_max_level=28, deep2_level=18, deep2_k=2)


def _play(mid, mid_from, *, late=None, late_from=0, seed=3, line_cap=40, explore=0.0,
          explore_from=0, explore_to=0):
    return native.late_hybrid_game(NET, _game(), seed, late=late, late_from_lines=late_from,
                                   mid=mid, mid_from_lines=mid_from, **DEEP,
                                   switch_level=1000, line_cap=line_cap, frame_cap=FRAME_CAP,
                                   limits=LIMITS, params=PARAMS, explore=explore,
                                   explore_from_lines=explore_from,
                                   explore_to_lines=explore_to)[0]


@pytest.mark.native
def test_the_mid_network_off_or_the_same_or_never_asked_is_the_late_agent():
    for seed in (3, 4):
        base = _play(None, 0, late=OTHER, late_from=20, seed=seed)
        assert _same(_play(NET, 0, late=OTHER, late_from=20, seed=seed), base)
        assert _same(_play(OTHER, 1000, late=OTHER, late_from=20, seed=seed), base)
        # from the late network's line count on the late network wins over the mid one
        assert _same(_play(NET, 20, late=OTHER, late_from=20, seed=seed), base)


@pytest.mark.native
def test_a_mid_network_changes_mid_play_only():
    seeds = (3, 4, 5)
    mid = [_play(OTHER, 20, seed=s) for s in seeds]
    assert any(not _same(g, _play(None, 0, seed=s)) for g, s in zip(mid, seeds))
    assert all(_same(_play(OTHER, 20, seed=s, line_cap=20), _play(None, 0, seed=s,
                                                                    line_cap=20))
               for s in seeds)
    # mid from 10 but late (v15) from 20: only 10-19 changes, so a game capped at 20 is
    # the mid-from-10 game without a late network
    assert all(_same(_play(OTHER, 10, late=NET, late_from=20, seed=s, line_cap=20),
                     _play(OTHER, 10, seed=s, line_cap=20)) for s in seeds)


@pytest.mark.native
def test_the_exploration_end():
    plain = _play(None, 0)
    assert _same(_play(None, 0, explore=1.0, explore_from=10, explore_to=10), plain)
    capped = dict(line_cap=20, explore=0.5, explore_from=0)
    assert _same(_play(None, 0, **capped, explore_to=20), _play(None, 0, **capped))
    assert not _same(_play(None, 0, explore=0.5, explore_to=20), plain)
    with pytest.raises(native.NativeError):
        _play(None, 0, explore_to=-1)


def _data(lines, games, score, final):
    return {"lines": np.array(lines), "game": np.array(games),
            "score": np.array(score, np.int64) * e30.TETRIS_18,
            "final": np.array(final, np.int64) * e30.TETRIS_18}


def test_handover_returns_end_at_the_late_board():
    lam = 0.5
    # game 0: two mid boards, then the hand-over board (backup = V39's A_h = 10)
    # game 1: two mid boards, the game ends before 320 (rest of points 3)
    # game 2: one mid board, crossed 320 with no board there (rest of points 7)
    d = _data([300, 310, 320, 250, 260, 319], [0, 0, 0, 1, 1, 2],
              [0, 1, 3, 0, 2, 0], [99, 99, 99, 5, 5, 7])
    backup = np.array([4.0, 6.0, 10.0, 2.0, 2.0, 1.0])
    got = e30.handover_returns(backup, d, lam)
    g1 = 0.5 * 6 + 0.5 * (2 + 10)          # steps to the hand-over board, takes A_h
    g0 = 0.5 * 4 + 0.5 * (1 + g1)
    h1 = 0.5 * 2 + 0.5 * (5 - 2)           # last board of a game below 320: real rest
    h0 = 0.5 * 2 + 0.5 * (2 + h1)
    k0 = 0.5 * 1 + 0.5 * 7
    assert np.allclose(got, [g0, g1, h0, h1, k0])  # the hand-over board is not a target
    # the game's real finish (99) never reaches game 0's targets
    d2 = dict(d, final=d["final"].copy())
    d2["final"][:3] = 10**6 * e30.TETRIS_18
    assert np.allclose(e30.handover_returns(backup, d2, lam), got)


def test_mid_rows_keep_up_to_the_first_late_board():
    lines = [200, 229, 230, 250, 319, 320, 330, 340]
    r = np.zeros((len(lines), native.DUMP_STRIDE), np.int32)
    r[:, native.WIDTH] = lines
    kept = e30._mid_rows(r.tobytes())
    assert kept[:, native.WIDTH].tolist() == [230, 250, 319, 320]
    r2 = r[:5]
    assert e30._mid_rows(r2.tobytes())[:, native.WIDTH].tolist() == [230, 250, 319]


def test_seeds_are_fresh_disjoint_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(e30, "SEEDS", tmp_path / "seeds.json")
    stored = e29._seeds()
    s = e30.make_seeds()
    used = set(stored["training_seeds"][:e30.USED_BY_029])
    blocks = [e30.round_seeds(k) for k in range(e30.MAX_SWEEPS)]
    assert len(blocks[0]) == e30.ROUND0_SEEDS
    assert all(len(b) == e30.ROUND_SEEDS for b in blocks[1:])
    flat = [x for b in blocks for x in b]
    probe = s["probe_seeds"]
    assert len(probe) == len(stored["probe_seeds"]) + e30.EXTRA_PROBE_SEEDS
    assert len(set(flat)) == len(flat) and not set(flat) & (used | set(probe))
    assert not set(probe[len(stored["probe_seeds"]):]) & used


def test_stop_rule(monkeypatch):
    means = [1, 2, 3, 4, 5, 4, 4, 4, 9, 9]
    monkeypatch.setattr(e30, "_means", lambda upto: means[:upto])
    assert [e30.should_stop(k) for k in range(1, 11)] == \
        [False] * 7 + [True, False, True]


def test_choose_skips_worse_ranking(monkeypatch, tmp_path):
    monkeypatch.setattr(e30, "OUT", tmp_path)
    key = "commit 29-38 below 320"
    monkeypatch.setattr(e30, "v15_ranking", lambda device: {key: {"network_odd_loss": 10.0}})
    for sweep, mean, loss in ((1, 5.0, 9.0), (2, 9.0, 11.0), (3, 7.0, 10.0)):
        (tmp_path / f"probe{sweep}.json").write_text(json.dumps(
            {"sweep": sweep, "weights": f"w{sweep}",
             "paired_vs_v39": {"total": {"score": {"mean": mean}}},
             "ranking": {key: {"network_odd_loss": loss}}}))
    (tmp_path / "probe_base.json").write_text("{}")
    assert e30.choose()["chosen"]["sweep"] == 3
