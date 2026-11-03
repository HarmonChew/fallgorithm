"""Experiment 029: the late network (NetSearcher::set_late_net), backup2 over rows and the
runner's pure parts."""

from __future__ import annotations

import json

import numpy as np
import pytest

from block_stack_ai import experiment029 as e29, native
from test_experiment028 import FRAME_CAP, LIMITS, NET, PARAMS, ROOT, _game, _same

pytestmark = pytest.mark.native

OTHER = (ROOT / "experiments/023-self-taught-value/value_sweep10.bin").read_bytes()
DEEP = dict(commit_level=18, adjust_k=0, adjust_max_level=28, deep2_level=18, deep2_k=2)


def _late(late, late_from, *, seed=3, line_cap=40, explore=0.0, explore_from=0, dump=False):
    return native.late_hybrid_game(NET, _game(), seed, late=late, late_from_lines=late_from,
                                   **DEEP, switch_level=1000, line_cap=line_cap,
                                   frame_cap=FRAME_CAP, limits=LIMITS, params=PARAMS,
                                   explore=explore, explore_from_lines=explore_from, dump=dump)


def _deep(seed=3, line_cap=40):
    return native.deep_net_game(NET, _game(), seed, **DEEP, line_cap=line_cap,
                                frame_cap=FRAME_CAP, limits=LIMITS)


def test_the_late_network_off_or_the_same_network_is_the_deep_agent():
    for seed in (3, 4):
        base = _deep(seed)
        assert _same(_late(None, 0, seed=seed)[0], base)
        assert _same(_late(NET, 0, seed=seed)[0], base)
        assert _same(_late(OTHER, 1000, seed=seed)[0], base)  # never late


def test_a_late_network_changes_late_play_only():
    seeds = (3, 4, 5)
    late = [_late(OTHER, 20, seed=s)[0] for s in seeds]
    assert any(not _same(g, _deep(s)) for g, s in zip(late, seeds))
    assert late == [_late(OTHER, 20, seed=s)[0] for s in seeds]
    # the network is chosen by the position's lines: a game ending at 20 lines never asks it
    assert all(_same(_late(OTHER, 20, seed=s, line_cap=20)[0], _deep(s, line_cap=20))
               for s in seeds)


def test_exploration_and_the_dump():
    plain, rows = _late(None, 0, dump=True)
    assert _same(plain, _deep())
    r = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)
    assert len(r) == plain["pieces"] and (np.diff(r[:, native.WIDTH]) >= 0).all()
    explored, _ = _late(None, 0, explore=0.5, explore_from=20)
    assert not _same(explored, plain)
    # exploration only from 20 lines: the same inputs as plain until then
    first = int(np.flatnonzero(r[:, native.WIDTH] >= 20)[0])  # the first piece at 20 lines
    assert explored["inputs"][:100] == plain["inputs"][:100] and first > 0
    assert _same(_late(None, 0, explore=1.0, explore_from=10**6)[0], plain)


def test_backup2_values():
    _, rows = _late(None, 0, dump=True)
    r = np.frombuffer(rows, np.int32).reshape(-1, native.DUMP_STRIDE)[5:12].tobytes()
    args = dict(line_cap=430, start_level=18, double_killscreen=True,
                tap_interval=LIMITS.tap_interval)
    one, _ = native.backup_values(NET, r, **args)
    two = native.backup2_values(NET, r, k=4, **args)
    assert two == native.backup2_values(NET, r, k=4, **args)
    assert all(abs(a - b) < 0.05 * abs(a) for a, b in zip(one, two))
    assert native.backup2_values(NET, r, k=1, **args) != two
    with pytest.raises(native.NativeError):
        native.backup2_values(NET, r, k=0, **args)


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _late(None, -1)
    with pytest.raises(native.NativeError):
        _late(None, 0, explore=2.0)


# ---------------------------------------------------------------- the runner

def test_round_seeds_are_disjoint_blocks():
    blocks = [e29.round_seeds(i) for i in range(4)]
    assert [len(b) for b in blocks] == [300, 200, 200, 200]
    assert len(set().union(*map(set, blocks))) == 900
    stored = e29._seeds()
    assert not set(stored["training_seeds"]) & set(stored["probe_seeds"])


def test_lambda_on_own_boards_plain_backup_on_017s():
    part = {"source": np.array([0, 0, 1, 1], np.int8), "score": np.array([0, 22800, 0, 0]),
            "final": np.array([45600, 45600, 99999, 99999]), "game": np.array([0, 0, 1, 1])}
    backup = np.array([5.0, 4.0, 7.0, 6.0])
    out = e29._part_targets(part, backup)
    assert out[2:].tolist() == [7.0, 6.0]
    # the last own board: (1 - l) B + l * (points to the end); the first leans on it
    lam = e29.LAMBDA
    last = (1 - lam) * 4.0 + lam * 1.0
    assert out[1] == pytest.approx(last)
    assert out[0] == pytest.approx((1 - lam) * 5.0 + lam * (1.0 + last))


def test_stop_rule(monkeypatch):
    means = {}
    monkeypatch.setattr(e29, "_means", lambda arm, upto: means[arm][:upto])
    means["a"] = [5, 6, 7, 1, 1, 1, 1, 1]
    assert not any(e29.should_stop("a", k) for k in (1, 2, 3, 4, 5))
    assert e29.should_stop("a", 6)  # best at 3, three flat sweeps after it
    means["b"] = [1, 2, 3, 4, 5, 6, 7, 8]
    assert not e29.should_stop("b", 7) and e29.should_stop("b", 8)  # the cap


def test_choose_skips_worse_ranking(monkeypatch, tmp_path):
    monkeypatch.setattr(e29, "OUT", tmp_path)
    monkeypatch.setattr(e29, "ranking",
                        lambda weights, device: {"commit 39+": {"network_odd_loss": 24.0}})
    for arm, sweep, mean, loss in (("t1", 1, 30_000, 25.0), ("t1", 2, 20_000, 23.0),
                                   ("t2", 1, 10_000, 24.0)):
        (tmp_path / arm).mkdir(exist_ok=True)
        (tmp_path / arm / f"probe{sweep}.json").write_text(json.dumps(
            {"sweep": sweep, "weights": f"{arm}/{sweep}",
             "paired_vs_e29_k4": {"total": {"score": {"mean": mean}}},
             "ranking": {"commit 39+": {"network_odd_loss": loss}}}))
    chosen = e29.choose()["chosen"]
    assert (chosen["arm"], chosen["sweep"]) == ("t1", 2)
