"""Experiment 026: the deeper search (NetSearcher::set_deep) and its staged runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from block_stack_ai import experiment013 as e13, native

pytestmark = pytest.mark.native

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "experiments/023-self-taught-value/config.json").read_text())
NET = (ROOT / "experiments/023-self-taught-value/value_sweep15.bin").read_bytes()
LIMITS = e13._limits(CONFIG)
FRAME_CAP = 20000
OFF = 1000


def _deep(commit_level=OFF, adjust_k=0, adjust_max_level=28, *, net=NET, seed=3, start_level=18,
          line_cap=40):
    game = CONFIG["game"] | {"start_level": start_level}
    return native.deep_net_game(net, game, seed, commit_level=commit_level, adjust_k=adjust_k,
                                adjust_max_level=adjust_max_level, line_cap=line_cap,
                                frame_cap=FRAME_CAP, limits=LIMITS)


def _v(*, seed=3, start_level=18, line_cap=40):
    game = CONFIG["game"] | {"start_level": start_level}
    return native.net_game(NET, game, seed, line_cap=line_cap, frame_cap=FRAME_CAP,
                           limits=LIMITS)[0]


def _same(a, b):
    return a["inputs"] == b["inputs"] and a["score"] == b["score"] and a["lines"] == b["lines"]


def test_deep_off_is_the_plain_value_agent():
    for seed in (3, 4):
        assert _same(_deep(seed=seed), _v(seed=seed))
        # the adjust level limit does nothing while k is 0
        assert _same(_deep(OFF, 0, 5, seed=seed), _v(seed=seed))


def test_deep_arms_play_valid_games_that_differ():
    kw = dict(line_cap=60)
    plain = [_v(seed=s, **kw) for s in (3, 4, 5)]
    for args in ((18, 0, 28), (OFF, 4, 28), (OFF, 8, 28)):
        games = [_deep(*args, seed=s, **kw) for s in (3, 4, 5)]
        for game, base in zip(games, plain):
            assert game["lines"] > 20 and game["score"] > 0
        assert any(not _same(g, b) for g, b in zip(games, plain)), args
        assert games == [_deep(*args, seed=s, **kw) for s in (3, 4, 5)]  # deterministic


def test_a_commit_level_beyond_the_game_is_off():
    # a 40-line game from level 18 never reaches level 29
    assert _same(_deep(29, 0), _v())


def test_adjust_level_limit_matters():
    # adjust_max_level below the start level switches the adjust change off
    assert _same(_deep(OFF, 8, 10), _v())


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _deep(net=b"not a network")
    with pytest.raises(native.NativeError):
        _deep(-1)
    with pytest.raises(native.NativeError):
        _deep(OFF, -1)
    with pytest.raises(native.NativeError):
        _deep(OFF, 4, -1)

