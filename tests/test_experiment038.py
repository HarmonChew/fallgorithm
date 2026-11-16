"""Experiment 038 step 0: the lead bonus in the native search (NetSearcher::set_lead_bonus),
the arms, the lead measure, the paired interval and the rule."""

from __future__ import annotations

import numpy as np
import pytest

from block_stack_ai import experiment038 as e38, native
from block_stack_ai.limits import Limits
from test_experiment028 import FRAME_CAP, NET, PARAMS, _game

OFF = 1000


def _play(lead, seed, line_cap=14, deep3=None):
    return native.late_hybrid_game(NET, _game(), seed, late=None, late_from_lines=0,
                                   commit_level=18, adjust_k=0, adjust_max_level=28,
                                   deep2_level=18, deep2_k=4, switch_level=OFF,
                                   line_cap=line_cap, frame_cap=FRAME_CAP,
                                   limits=Limits(20, 300), params=PARAMS, deep3=deep3,
                                   lead=lead)[0]


@pytest.mark.native
def test_lead_bonus_off_is_the_older_game_and_on_it_changes_the_game_only_in_its_window():
    plain = _play(None, 3)
    assert plain["lines"] > 8
    # beta 0, an empty window, a window no game reaches: the game without the bonus
    for off in ((0, 330, 0.0), (5, 5, 0.75), (OFF, OFF + 1, 0.75)):
        assert _play(off, 3) == plain
    assert _play((0, 330, 0.0), 3, deep3=(18, OFF, 2, 2, 2)) == \
        _play(None, 3, deep3=(18, OFF, 2, 2, 2))
    on = _play((0, 330, 2.0), 3)
    assert on == _play((0, 330, 2.0), 3)
    assert on["inputs"] != plain["inputs"]


@pytest.mark.native
def test_bad_lead_arguments_are_refused():
    for bad in ((-1, 330, 0.5), (300, 299, 0.5), (300, 330, float("nan"))):
        with pytest.raises(native.NativeError):
            _play(bad, 3)


def test_the_arms_are_the_plans():
    assert e38.ARMS == {"t300_a": (300, 0.25), "t300_b": (300, 0.75),
                        "t315_a": (315, 0.25), "t315_b": (315, 0.75)}
    assert e38.lead_of("t315_b") == (315, 330, 0.75)
    assert e38.lead_of("v36")[2] == 0.0
    with pytest.raises(KeyError):
        e38.lead_of("t320")


def test_lead_is_column_0_minus_the_mean_of_the_others():
    assert e38.lead([9] + [0] * 9) == 9.0
    assert e38.lead([4, 4, 4, 4, 4, 4, 4, 4, 4, 4]) == 0.0
    assert e38.lead([2] + [3] * 8 + [12]) == pytest.approx(2 - 36 / 9)


def test_the_rule():
    assert e38.verdict(3.0, 15_000, 10, 500)  # exactly 2 points down passes
    assert not e38.verdict(2.99, 0, 0, 500)
    assert not e38.verdict(5.0, 15_001, 0, 500)
    assert not e38.verdict(5.0, 0, 11, 500)
    assert e38.verdict(5.0, 0, -4, 500)
    rows = {"t300_a": {"qualifies": True, "mean_lead_330": 4.0},
            "t300_b": {"qualifies": False, "mean_lead_330": 9.0},
            "t315_a": {"qualifies": True, "mean_lead_330": 5.0},
            "t315_b": {"qualifies": True, "mean_lead_330": 5.0}}
    assert e38.choose(rows) == "t315_a"
    assert e38.choose({k: v | {"qualifies": False} for k, v in rows.items()}) is None


def test_paired_interval_is_seeded_and_brackets_the_mean():
    diff = np.random.default_rng(0).normal(1000, 5000, 500)
    a, b = e38.paired_interval(diff), e38.paired_interval(diff)
    assert a == b and a["ci95_low"] < a["mean"] < a["ci95_high"]
    assert a["mean"] == pytest.approx(diff.mean())
