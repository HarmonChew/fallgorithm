"""reach_plan: tuned_plan with complete reachability."""

from __future__ import annotations

import json

from block_stack_ai import experiment009 as e9
from block_stack_ai import limits, reachplan, tunedplan
from block_stack_ai.limits import Flight, Limits
from block_stack_ai.pathaware import grid_columns

import test_survivalplan as survival_tests

LIMITS = Limits(30, 300)
RULESET = "classic_ntsc_double_killscreen"
LEARNED = json.loads(e9.FINAL_PARAMS.read_text(encoding="utf-8"))["resolved"]


def _kwargs(level, drought, params):
    return dict(flight=Flight(), drought=drought, level=level, lines=0, start_level=18,
                ruleset=RULESET, limits=LIMITS, params=params)


def _fixed_route_only(columns, piece, flight, level, ruleset, limit):
    """Reach's options cut down to the placements the fixed-route model finds."""
    period, rows = limits.gravity(level, ruleset)
    allowed = {(r.orientation, r.x, r.y) for r in limits.reachable(
        columns, piece, flight, period=period, rows=rows, limits=limit)}
    return [option for option in reachplan.reach_options(columns, piece, flight, level, ruleset, limit)
            if option[0].key() in allowed]


def test_restricted_to_the_fixed_route_set_it_picks_what_tuned_plan_picks():
    count = 0
    for params in (None, LEARNED):
        for grid, piece, preview, drought, level in survival_tests._boards(30):
            columns = grid_columns(grid)
            for next_piece in (preview, None):
                expected = tunedplan.search(columns, piece, next_piece,
                                            **_kwargs(level, drought, params))
                found = reachplan.search(columns, piece, next_piece, options=_fixed_route_only,
                                         **_kwargs(level, drought, params))
                assert (found is None) == (expected is None)
                if expected is not None:
                    assert found[0].key()[:2] == (expected[0].orientation, expected[0].x)
                    assert found[1:] == expected[1:]
                    count += 1
    assert count > 80


def test_with_every_placement_allowed_it_chooses_one_of_them():
    for grid, piece, preview, drought, level in survival_tests._boards(30):
        columns = grid_columns(grid)
        new = reachplan.search(columns, piece, preview, **_kwargs(level, drought, LEARNED))
        allowed = reachplan.reach_options(columns, piece, Flight(), level, RULESET, LIMITS)
        assert (new is None) == (not allowed)
        if new is not None:
            assert new[0].key() in {option[0].key() for option in allowed}


def test_the_agent_is_tuned_plan_with_the_new_reachable_set():
    agent = reachplan.ReachAgent(LIMITS, LEARNED)
    assert isinstance(agent, tunedplan.TunedAgent)
    assert agent.params == tunedplan.resolve(LEARNED)
    assert reachplan.REACH_AGENT == "reach_plan"
