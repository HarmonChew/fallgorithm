"""The input-limited movement model's arithmetic and pure-Python behaviour."""

from __future__ import annotations

from block_stack_ai import limits
from block_stack_ai.limits import Flight, Limits
from block_stack_ai.pathaware import LEFT, RIGHT, ROTATE_CCW, ROTATE_CW

EMPTY = (0,) * 10


def test_tap_interval_is_the_rounded_frame_count_with_a_two_frame_minimum():
    assert [Limits(hz, 0).tap_interval for hz in (30, 20, 15, 12)] == [2, 3, 4, 5]
    assert Limits(60, 0).tap_interval == 2
    assert Limits(1000, 0).tap_interval == 2


def test_reaction_frames_are_the_rounded_frame_count():
    assert Limits(30, 300).reaction_frames == 18
    assert Limits(30, 0).reaction_frames == 0
    assert Limits(30, 150).reaction_frames == 9


def test_gravity_moves_two_rows_only_on_the_double_killscreen_ruleset_from_level_39():
    assert limits.gravity(38, "classic_ntsc_double_killscreen") == (1, 1)
    assert limits.gravity(39, "classic_ntsc_double_killscreen") == (1, 2)
    assert limits.gravity(45, "classic_ntsc_extended") == (1, 1)
    assert limits.gravity(18, "classic_ntsc_double_killscreen") == (3, 1)


def test_a_tap_timer_restarts_on_a_press_and_counts_down_otherwise():
    assert limits.next_wait(0, True, 2) == 1
    assert limits.next_wait(1, False, 2) == 0
    assert limits.next_wait(0, False, 2) == 0
    assert limits.next_wait(3, False, 5) == 2


def test_shifts_and_rotations_press_together_and_taps_alternate_with_a_release():
    limit = Limits(30, 0)
    found = {(r.orientation, r.x): r for r in limits.reachable(
        EMPTY, "T", Flight(), period=3, rows=1, limits=limit)}
    masks = found[(1, 8)].masks  # one rotation and three shifts
    assert masks[0] == ROTATE_CW | RIGHT
    assert masks[1] == 0
    assert masks[2] == RIGHT and masks[4] == RIGHT
    assert found[(3, 2)].masks[0] == ROTATE_CCW | LEFT  # the short way round
    slow = {(r.orientation, r.x): r for r in limits.reachable(
        EMPTY, "T", Flight(), period=3, rows=1, limits=Limits(15, 0))}
    assert slow[(0, 8)].masks == (RIGHT, 0, 0, 0, RIGHT, 0, 0, 0, RIGHT)


def test_a_piece_in_its_target_pose_needs_no_input_and_lands_on_the_floor():
    found = limits.reachable(EMPTY, "O", Flight(), period=3, rows=1, limits=Limits(30, 0))
    centre = [r for r in found if r.x == 5][0]
    assert centre.masks == ()
    assert centre.y == 18  # y is the engine's origin row; the O fills rows 18 and 19


def test_a_mid_flight_flight_keeps_its_tap_timer():
    ready = limits.reachable(EMPTY, "O", Flight(), period=3, rows=1, limits=Limits(30, 0))
    waiting = limits.reachable(EMPTY, "O", Flight(shift_wait=1), period=3, rows=1,
                               limits=Limits(30, 0))
    left = lambda found: [r for r in found if r.x == 4][0].masks  # noqa: E731
    assert left(ready) == (LEFT,)
    assert left(waiting) == (0, LEFT)


def test_far_columns_are_cut_off_by_two_row_gravity_on_a_tall_stack():
    flat = (((1 << 10) - 1) << 12,) * 10  # a flat stack 10 rows high (model rows 12-21)
    near = {(r.orientation, r.x) for r in limits.reachable(
        flat, "I", Flight(), period=1, rows=1, limits=Limits(30, 0))}
    double = {(r.orientation, r.x) for r in limits.reachable(
        flat, "I", Flight(), period=1, rows=2, limits=Limits(30, 0))}
    assert (1, 0) in near and (1, 0) not in double
    assert double < near
