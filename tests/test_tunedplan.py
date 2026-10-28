"""Experiment 009's parameterised agent: defaults equal bench_plan; params resolve safely."""

from __future__ import annotations

import pytest

from block_stack_ai import benchplan, tunedplan, wellplan
from block_stack_ai.limits import Flight, Limits
from block_stack_ai.pathaware import column_features, grid_columns

import test_survivalplan as survival_tests

LIMITS = Limits(30, 300)


def _kwargs(level, drought):
    return dict(flight=Flight(), drought=drought, level=level, lines=0, start_level=18,
                ruleset="classic_ntsc_double_killscreen", limits=LIMITS)


def test_default_params_choose_what_bench_plan_chooses():
    count = 0
    for grid, piece, preview, drought, level in survival_tests._boards(30):
        columns = grid_columns(grid)
        for next_piece in (preview, None):
            expected = benchplan.search(columns, piece, next_piece, **_kwargs(level, drought))
            found = tunedplan.search(columns, piece, next_piece, **_kwargs(level, drought))
            assert found == expected
            count += expected is not None
    assert count > 40


def test_default_values_and_phases_equal_the_hand_ones():
    value_of, phase_rule = tunedplan.make_rules()
    for grid, _, _, drought, level in survival_tests._boards(30):
        columns = grid_columns(grid)
        phase_of = phase_rule(level)
        expected_phase = (survival_phase if level >= 28 else wellplan.initial_phase)(drought, columns)
        assert phase_of(drought, columns) == expected_phase
        for phase in (wellplan.BUILD, wellplan.SPEND):
            for cleared in range(5):
                assert value_of(phase, cleared, columns) == wellplan.plan_value(phase, cleared, columns)


def survival_phase(drought, columns):
    from block_stack_ai import survivalplan
    return survivalplan.survival_phase(drought, columns)


def test_resolve_fills_defaults_rounds_and_clamps():
    assert tunedplan.resolve() == {**tunedplan.DEFAULTS, **{k: float(v) for k, v in
                                   tunedplan.DEFAULTS.items() if k not in tunedplan.INTEGER_RANGES}}
    resolved = tunedplan.resolve({"height_budget": 99.0, "survival_budget": -3.2,
                                  "survival_level": 28.6, "drought_bound": 3.9, "build_reserve": 1.5})
    assert (resolved["height_budget"], resolved["survival_budget"]) == (14, 2)
    assert (resolved["survival_level"], resolved["drought_bound"]) == (29, 4)
    assert resolved["build_reserve"] == 1.5
    assert all(isinstance(resolved[k], int) for k in tunedplan.INTEGER_RANGES)
    assert tunedplan.resolve({"survival_level": 5})["survival_level"] == 19
    assert tunedplan.resolve({"survival_level": 50})["survival_level"] == 38
    assert tunedplan.resolve({"drought_bound": 40})["drought_bound"] == 20
    with pytest.raises(ValueError):
        tunedplan.resolve({"nope": 1})


def test_extra_spend_features_add_their_weighted_counts():
    grid = next(survival_tests._boards(1))[0]
    columns = grid_columns(grid)
    base, _ = tunedplan.make_rules()
    for name, feature in (("row_transitions", tunedplan.row_transitions),
                          ("column_transitions", tunedplan.column_transitions),
                          ("edge_depth", tunedplan.edge_depth)):
        tuned, _ = tunedplan.make_rules({f"spend_{name}": -0.25})
        assert tuned(wellplan.SPEND, 0, columns) == base(wellplan.SPEND, 0, columns) - 0.25 * feature(columns)
        assert tuned(wellplan.BUILD, 0, columns) == base(wellplan.BUILD, 0, columns)


def test_phase_rule_uses_the_parameters():
    columns = grid_columns(survival_tests._grid([6] * 9 + [0]))
    _, rule = tunedplan.make_rules({"survival_budget": 8, "survival_level": 20})
    assert rule(25)(0, columns) == wellplan.BUILD  # budget 8 > height 6
    assert rule(19)(0, columns) == wellplan.BUILD  # height budget default 8
    _, rule = tunedplan.make_rules({"survival_level": 20, "height_budget": 5})
    assert rule(19)(0, columns) == wellplan.SPEND
    _, rule = tunedplan.make_rules({"drought_bound": 4})
    assert rule(18)(4, grid_columns(survival_tests._grid([1] * 10))) == wellplan.SPEND
    assert column_features(columns).max_height == 6
