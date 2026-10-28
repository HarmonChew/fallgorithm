"""Complete reachability: behaviour that needs no native engine."""

from __future__ import annotations

from block_stack_ai import limits, reach
from block_stack_ai.limits import Flight, Limits
from block_stack_ai.pathaware import LEFT, RIGHT, ROTATE_CW, grid_columns
from block_stack_ai.pieces import PIECES

import test_survivalplan as survival_tests

EMPTY = (0,) * 10
RULESET = "classic_ntsc_double_killscreen"


def _both(columns, piece, flight=Flight(), level=18, hz=30):
    period, rows = limits.gravity(level, RULESET)
    arguments = dict(period=period, rows=rows, limits=Limits(hz, 0))
    return (limits.reachable(columns, piece, flight, **arguments),
            reach.reachable(columns, piece, flight, **arguments))


def test_on_an_empty_board_both_models_reach_the_same_placements_with_the_same_inputs():
    for piece in PIECES:
        for level in (18, 29, 39):
            old, new = _both(EMPTY, piece, level=level)
            assert [(r.orientation, r.x, r.y) for r in new] == \
                [(r.orientation, r.x, r.y) for r in old]
            assert [r.masks for r in new] == [r.masks for r in old]


def test_reach_is_a_superset_of_the_fixed_route_model_with_one_entry_per_lock():
    extra = 0
    for grid, piece, _, _, level in survival_tests._boards(60):
        columns = grid_columns(grid)
        for hz in (30, 15):
            old, new = _both(columns, piece, level=level, hz=hz)
            keys = [(r.orientation, r.x, r.y) for r in new]
            assert len(keys) == len(set(keys)) and keys == sorted(keys)
            assert {(r.orientation, r.x, r.y) for r in old} <= set(keys)
            extra += len(new) - len(old)
    assert extra > 0


def test_a_slide_under_an_overhang_needs_late_presses():
    rows = [[0] * 10 for _ in range(20)]
    rows[17] = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    rows[19] = [0, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    columns = grid_columns(tuple(tuple(r) for r in [[0] * 10] * 2 + rows))
    old, new = _both(columns, "I")
    old_keys = {(r.orientation, r.x, r.y) for r in old}
    slide = {r.key(): r for r in new}[(0, 3, 18)]
    assert (0, 3, 18) not in old_keys
    assert slide.masks.count(LEFT) == 2 and RIGHT not in slide.masks
    assert slide.masks[0] == 0  # it waits before the first press


def test_masks_are_built_on_demand_and_cached():
    reach._cached_search.cache_clear()
    placement = {r.key(): r for r in _both(EMPTY, "T")[1]}[(1, 3, 18)]
    assert placement._masks is None
    first = placement.masks
    assert placement.masks is first
    assert first[0] & ROTATE_CW and first[0] & LEFT


def test_a_running_tap_timer_delays_the_first_press():
    ready = {r.key(): r for r in _both(EMPTY, "O")[1]}[(0, 6, 18)]
    waiting = {r.key(): r for r in _both(EMPTY, "O", Flight(shift_wait=1))[1]}[(0, 6, 18)]
    assert ready.masks == (RIGHT,)
    assert waiting.masks == (0, RIGHT)


def test_the_search_is_remembered_for_the_same_board_piece_and_start():
    reach._cached_search.cache_clear()
    first = _both(EMPTY, "S")[1]
    second = _both(EMPTY, "S")[1]
    assert first is second
    assert reach._cached_search.cache_info().hits >= 1


def test_every_piece_on_random_boards_lands_at_a_supported_row():
    for grid, piece, _, _, level in survival_tests._boards(40):
        columns = grid_columns(grid)
        for placement in _both(columns, piece, level=level)[1]:
            assert 0 <= placement.y < 22 and 0 <= placement.orientation < 4
            assert len(placement.masks) <= 200
