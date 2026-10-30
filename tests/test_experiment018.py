"""Experiment 018: the rollouts' data dump and the fitted re-ranker (native/rollout.hpp)."""

from __future__ import annotations

import math

import pytest

from block_stack_ai import experiment013 as e13, experiment015 as e15, experiment016 as e16
from block_stack_ai import experiment018 as e18, native
from block_stack_ai.limits import Limits

GAME = {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless", "start_level": 18,
        "height": 0}
# 017's tests' small settings: rollouts from the start level and the commit rollouts and
# commit ply from there too, so a short game has both kinds of decision.
SMALL = e16.fast_deep_params() | {
    "commit_ply_level": 18, "rollout_from_level": 18, "rollout_to_level": 28,
    "rollout_beam": 3, "rollout_count": 4, "rollout_depth": 4, "rollout_death": 1000,
    "commit_rollout_from_level": 18, "commit_rollout_to_level": 99, "commit_rollout_beam": 3,
    "commit_rollout_count": 4, "commit_rollout_depth": 4}
N = native.RERANK_FEATURES


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def _play(kind, numbers=SMALL, weights=None, reaction_ms=300):
    return native.play_game_ex(kind, GAME, _seed(), line_cap=430, frame_cap=1500,
                               limits=Limits(30, reaction_ms), params=native.params(numbers),
                               weights=weights)["inputs"]


def _distil():
    return native.distil_game(GAME, _seed(), line_cap=430, frame_cap=1500,
                              limits=Limits(30, 300), params=native.params(SMALL))


def test_the_dump_does_not_change_the_game():
    played, rows = _distil()
    assert played["inputs"] == _play("reach_plan_016")
    assert rows


def test_the_rows_are_whole_decisions():
    _, rows = _distil()
    groups = e18.decisions([list(row) for row in rows])
    assert {model for model, _, _ in groups} == {0, 1}  # preview, commit below 39
    for model, means, xs in groups:
        assert 2 <= len(means) <= 3
        assert sum(x[0] for x in xs) == 1.0  # one search choice per decision
        for x in xs:
            assert sum(x[5:9]) in (0.0, 1.0)  # at most one cleared-rows flag
    ranks = [int(row[2]) for row in rows]
    assert all(b == a + 1 or b == 0 for a, b in zip(ranks, ranks[1:]))


def test_zero_weights_play_the_search_alone():
    zero = [0.0] * native.RERANK_WEIGHTS
    assert _play("reach_plan_018", weights=zero) == _play(e15.AGENT)


def test_weights_change_the_game_and_repeat_exactly():
    weights = [0.0] * native.RERANK_WEIGHTS
    for model in range(3):
        weights[model * N + e18.FEATURES.index("holes")] = -1.0  # fewer holes first
        weights[model * N + e18.FEATURES.index("aggregate_height")] = -0.1  # then lower
    once = _play("reach_plan_018", weights=weights)
    assert once != _play(e15.AGENT)
    assert once == _play("reach_plan_018", weights=weights)


def test_the_re_ranker_takes_its_weights():
    with pytest.raises(ValueError):
        _play("reach_plan_018", weights=[0.0] * (native.RERANK_WEIGHTS - 1))
    with pytest.raises(ValueError):
        _play("reach_plan_018")


def test_the_fit_recovers_a_linear_ranking():
    # Means that are an exact linear function of the features, plus a per-decision offset
    # (which the within-decision centring removes).
    import random
    rng = random.Random(18)
    true = [rng.uniform(-1, 1) for _ in range(N)]
    groups = []
    for index in range(400):
        xs = [[1.0 if k == 0 else 0.0] + [rng.uniform(0, 5) for _ in range(N - 1)]
              for k in range(4)]
        offset = rng.uniform(-100, 100)
        groups.append((index % 3, [offset + sum(a * b for a, b in zip(true, x)) for x in xs], xs))
    weights = e18.fit(groups, 1e-9)
    report = e18.score(groups, weights)
    for name in e18.MODELS:
        assert report[name]["rerank_agrees"] == 1.0
        assert report[name]["rerank_loss"] == pytest.approx(0.0, abs=1e-9)


def test_rerank_pick_lets_the_search_choice_win_ties():
    assert e18.rerank_pick([1.0, 2.0, 2.0], searched=2) == 2
    assert e18.rerank_pick([1.0, 2.0, 2.0], searched=0) == 1
    assert e18.rerank_pick([0.0, 0.0, 0.0], searched=1) == 1


def test_every_row_is_finite_in_a_game_that_tops_out():
    # The search's total is -inf where some piece has no placement; the features stand in.
    played, rows = native.distil_game(GAME, 2076, line_cap=430, frame_cap=150_000,
                                      limits=Limits(30, 300), params=native.params(SMALL))
    assert played["stopping_reason"] == "game_over"
    assert all(math.isfinite(v) for row in rows for v in row)
    assert any(row[4 + e18.FEATURES.index("doomed_total")] == 1.0 for row in rows)


def test_commit_totals_say_which_include_the_extra_ply():
    _, rows = _distil()
    deep = e18.FEATURES.index("extra_ply_total")
    for model, _, xs in e18.decisions([list(row) for row in rows]):
        flags = [x[deep] for x in xs]
        assert flags == ([0.0] * len(xs) if model == 0 else [1.0, 1.0] + [0.0] * (len(xs) - 2))


def test_the_features_are_named_in_the_native_order():
    assert len(e18.FEATURES) == N
