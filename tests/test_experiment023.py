"""Experiment 023: the backup of a settled board (native/netsearch.hpp NetSearcher::backup)."""

from __future__ import annotations

import numpy as np
import pytest

from block_stack_ai import experiment023 as e23, native
from test_experiment020 import _random_net

ARGS = dict(line_cap=430, start_level=18, double_killscreen=True, tap_interval=2)


def _row(lines=0, drought=0, last=-1):
    row = np.zeros(native.DUMP_STRIDE, np.int32)  # an empty board
    row[native.WIDTH], row[native.WIDTH + 2], row[native.WIDTH + 3] = lines, drought, last
    return row


def _children(kids):
    return np.frombuffer(kids, np.int32).reshape(-1, native.DUMP_STRIDE)


def test_an_empty_boards_backup_is_the_mean_value_of_its_children(tmp_path):
    # No piece clears a line on an empty board, so the backup is the plain average (1/7
    # each for the first board) of the network's value of each piece's best board.
    _, net = _random_net(tmp_path)
    found, kids = native.backup_values(net, _row().tobytes(), **ARGS, children=True)
    rows = _children(kids)
    assert rows.shape == (7, native.DUMP_STRIDE)
    assert list(rows[:, native.WIDTH]) == [0] * 7 and list(rows[:, native.WIDTH + 3]) == list(range(7))
    assert all(rows[:, :native.WIDTH].any(axis=1))  # each piece left cells behind
    values = native.net_values(net, rows.tobytes(), line_cap=430, start_level=18)
    assert found[0] == pytest.approx(sum(values) / 7, rel=1e-9)
    # Asking for the children does not change the backup.
    assert native.backup_values(net, _row().tobytes(), **ARGS)[0] == found


def test_the_backup_is_0_at_the_line_cap_and_follows_the_nes_odds(tmp_path):
    _, net = _random_net(tmp_path)
    found, kids = native.backup_values(net, _row(lines=430).tobytes(), **ARGS, children=True)
    assert found == [0.0] and list(_children(kids)[:, native.WIDTH]) == [-1] * 7
    first = native.backup_values(net, _row().tobytes(), **ARGS)[0]
    after_i = native.backup_values(net, _row(last=0).tobytes(), **ARGS)[0]
    assert after_i != first  # the odds after a known piece are not 1/7 each


def test_bad_arguments_are_refused(tmp_path):
    _, net = _random_net(tmp_path)
    with pytest.raises(native.NativeError):
        native.backup_values(b"not a network", _row().tobytes(), **ARGS)
    with pytest.raises(native.NativeError):
        native.backup_values(net, _row(last=7).tobytes(), **ARGS)
    assert native.backup_values(net, b"", **ARGS) == ([], None)


def test_lambda_returns_run_backwards_within_each_game():
    t = e23.TETRIS_18  # scores in points; returns in Tetrises at level 18
    data = {"game": np.array([0, 0, 1]), "score": np.array([0, 2, 0]) * t,
            "final": np.array([5, 5, 3]) * t}
    backup = np.array([1.0, 2.0, 4.0])
    found = e23.lambda_returns(backup, data, 0.5)
    last_0 = 0.5 * 2 + 0.5 * (5 - 2)        # game 0's last board: the rest of its points
    first_0 = 0.5 * 1 + 0.5 * (2 + last_0)  # its step to the next board, then that return
    assert list(found) == pytest.approx([first_0, last_0, 0.5 * 4 + 0.5 * 3])
    assert list(e23.lambda_returns(backup, data, 0.0)) == list(backup)


# ---------------------------------------------------------------- milestone 2: V in 017's rollouts

def _leaf(net, from_level):
    from test_experiment021 import GAME, SMALL
    from block_stack_ai.limits import Limits
    from block_stack_ai import experiment013 as e13
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    args = dict(line_cap=430, frame_cap=1500, limits=Limits(30, 300), params=native.params(SMALL))
    leaf = native.leaf_rollout_game(net, GAME, seed, from_level=from_level, **args)
    alone, _ = native.rank_rollout_game(None, GAME, seed, net_to_level=0, **args)
    return leaf, alone


def test_the_leaf_value_off_plays_017s_game_and_on_changes_it(tmp_path):
    _, net = _random_net(tmp_path)
    off, alone = _leaf(net, 100)
    assert off == alone
    on, _ = _leaf(net, 18)
    assert on != alone and on == _leaf(net, 18)[0]  # a pure function of the seed


def test_the_leaf_rollouts_refuse_a_bad_network():
    with pytest.raises(native.NativeError):
        _leaf(b"not a network", 18)
