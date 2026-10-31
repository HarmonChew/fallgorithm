"""Experiment 022: playouts to the end of the game at the commit decision (native/rollout.hpp)."""

from __future__ import annotations

import pytest

from block_stack_ai import experiment013 as e13, experiment021 as e21, native
from block_stack_ai.limits import Limits
from test_experiment021 import GAME, SMALL, _net

# A short line cap keeps the playouts short (they stop at the cap).
ARGS = dict(line_cap=6, frame_cap=1500, limits=Limits(30, 300))


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def _playout(net=None, from_level=18, count=3, dump=False, numbers=SMALL):
    return native.playout_game(net, GAME, _seed(), from_level=from_level, count=count, **ARGS,
                               params=native.params(numbers), dump=dump)


def test_playouts_off_play_017s_game():
    played, _ = _playout(from_level=100)
    alone, _ = native.rank_rollout_game(None, GAME, _seed(), net_to_level=0, **ARGS,
                                        params=native.params(SMALL))
    assert {k: v for k, v in played.items() if not k.startswith("playout")} == alone
    assert played["playouts"] == played["playout_pieces"] == played["playouts_cut"] == 0


def test_playouts_are_a_pure_function_of_the_seed_and_end_at_the_cap(tmp_path):
    _, net = _net(tmp_path)
    for policy in (None, net):
        first, rows = _playout(policy, dump=True)
        again, rows_again = _playout(policy, dump=True)
        assert first == again and rows == rows_again
        assert first["playouts"] > 0 and first["playouts_cut"] == 0
        # The commit decisions (preview not known) are the playout-ranked ones; the
        # preview ones are still 016's rollouts.
        playouts = [r for r in rows if r[e21.NEXT] == -1]
        assert playouts and {int(r[e21.MODEL]) for r in playouts} == {1}
        for r in playouts:  # 3 playouts: 2 even, 1 odd; points only
            assert r[e21.MEAN] == pytest.approx((2 * r[e21.EVEN] + r[e21.ODD]) / 3)
            assert r[e21.ODD] >= 0 and r[e21.EVEN] >= 0

def test_the_network_changes_the_playouts(tmp_path):
    _, net = _net(tmp_path)
    alone, _ = _playout(None)
    ranked, _ = _playout(net)
    assert alone["playout_pieces"] != ranked["playout_pieces"] or alone != ranked


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _playout(count=0)
    with pytest.raises(native.NativeError):
        _playout(net=b"not a network")


def test_the_killscreen_network_as_the_rank_network_plays_the_rank_agents_game(tmp_path):
    # SMALL's commit band starts at 18, so the killscreen network from 18 re-ranks the
    # same commit decisions over the same candidates as the rank agent.
    _, net = _net(tmp_path)
    played, _ = native.playout_game(None, GAME, _seed(), from_level=18, count=0, **ARGS,
                                    params=native.params(SMALL), rank=net, killscreen=net)
    alone = native.rank_game(net, GAME, _seed(), **ARGS, params=native.params(SMALL))
    assert {k: v for k, v in played.items() if not k.startswith("playout")} == alone
    assert played["playouts"] == 0


def test_a_killscreen_network_changes_only_the_commit_decisions_from_its_level(tmp_path):
    _, net = _net(tmp_path)
    _, other = _net(tmp_path, seed=1)
    off, _ = native.playout_game(None, GAME, _seed(), from_level=100, count=0, **ARGS,
                                 params=native.params(SMALL), rank=net, killscreen=other)
    alone = native.rank_game(net, GAME, _seed(), **ARGS, params=native.params(SMALL))
    assert {k: v for k, v in off.items() if not k.startswith("playout")} == alone
    with pytest.raises(native.NativeError):  # playouts and a killscreen network at once
        native.playout_game(None, GAME, _seed(), from_level=18, count=2, **ARGS,
                            params=native.params(SMALL), killscreen=other)
