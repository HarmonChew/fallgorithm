"""The C++ library (``native/``) against the Python reference it translates.

Every comparison is exact: boards bit for bit, values with ``==``. Build the library
first with ``.venv/bin/python scripts/build_native.py``.
"""

from __future__ import annotations

import json
import math
import random

import pytest

from block_stack_ai import native, reach, tunedplan, wellplan
from block_stack_ai.heuristic import GRID_ROWS, HIDDEN_ROWS, WIDTH
from block_stack_ai.limits import DOUBLE_KILLSCREEN, Flight, gravity
from block_stack_ai.pathaware import level_for_lines, settle_columns
from block_stack_ai.pieces import PIECES, cells, orientation_count

pytestmark = pytest.mark.native

FINAL_PARAMS = native.PROJECT_ROOT / "experiments" / "009-cem-score" / "final_params.json"


def _random_columns(rng: random.Random) -> tuple[int, ...]:
    """A random board: any heights, some holes, sometimes cells in the hidden rows.

    The agent's own board never has hidden cells, but the boards its search settles
    can (a lock at the ceiling), and those are evaluated too.
    """
    density = rng.choice((0.5, 0.8, 0.95, 1.0))
    tall = rng.random() < 0.3
    columns = []
    for _ in range(WIDTH):
        top = rng.randint(0, 20 if tall else 10)
        column = 0
        for row in range(GRID_ROWS - top, GRID_ROWS):
            if row == GRID_ROWS - top or rng.random() < density:
                column |= 1 << row
        if rng.random() < 0.05:
            column |= rng.randint(1, 3)  # hidden rows 0 and 1
        columns.append(column)
    return tuple(columns)


def _random_placement(rng: random.Random) -> tuple[str, int, int, int]:
    """A piece pose with every cell inside the 22 model rows (overlap allowed)."""
    piece = rng.choice(PIECES)
    orientation = rng.randrange(orientation_count(piece))
    offsets = cells(piece, orientation)
    xs = [dx for dx, _ in offsets]
    ys = [dy for _, dy in offsets]
    x = rng.randint(-min(xs), WIDTH - 1 - max(xs))
    y = rng.randint(-HIDDEN_ROWS - min(ys), GRID_ROWS - HIDDEN_ROWS - 1 - max(ys))
    return piece, orientation, x, y


def _param_sets() -> list[dict[str, float]]:
    rng = random.Random(11)
    sets = [dict(tunedplan.DEFAULTS), json.loads(FINAL_PARAMS.read_text())["resolved"]]
    for _ in range(20):
        values: dict[str, float] = {}
        for name in native.WEIGHT_NAMES:
            draw = rng.random()
            values[name] = 0.0 if draw < 0.1 else -0.0 if draw < 0.15 else rng.gauss(0, 4)
        for name, (low, high) in tunedplan.INTEGER_RANGES.items():
            values[name] = rng.randint(low, high)
        sets.append(values)
    return sets


def test_the_params_struct_matches_the_python_parameters():
    assert set(native.WEIGHT_NAMES + native.INTEGER_NAMES) == set(tunedplan.DEFAULTS)
    assert set(native.INTEGER_NAMES) == set(tunedplan.INTEGER_RANGES)
    native.load()  # checks the ABI version and the struct size


def test_settle_matches_the_python_on_random_boards():
    rng = random.Random(1)
    cleared_seen = set()
    for _ in range(20000):
        columns = _random_columns(rng)
        piece, orientation, x, y = _random_placement(rng)
        expected = settle_columns(columns, piece, orientation, x, y)
        assert native.settle(columns, piece, orientation, x, y) == expected
        cleared_seen.add(expected[1])
    assert cleared_seen >= {0, 1, 2, 3, 4}


def test_settle_clears_one_to_four_rows_under_a_vertical_i():
    for gap in range(WIDTH):
        for rows in range(1, 5):
            filled = (1 << GRID_ROWS) - (1 << (GRID_ROWS - rows))
            columns = tuple(0 if column == gap else filled for column in range(WIDTH))
            y = GRID_ROWS - HIDDEN_ROWS - 2  # the vertical I's lowest cell on the floor
            expected = settle_columns(columns, "I", 1, gap, y)
            assert expected[1] == rows
            assert native.settle(columns, "I", 1, gap, y) == expected


def test_settle_never_clears_a_full_hidden_row():
    rng = random.Random(3)
    checked = 0
    for hidden in (1, 2, 3):
        for _ in range(2000):
            columns = tuple(column | hidden for column in _random_columns(rng))
            piece, orientation, x, y = _random_placement(rng)
            expected = settle_columns(columns, piece, orientation, x, y)
            assert native.settle(columns, piece, orientation, x, y) == expected
            checked += expected[1] > 0
    assert checked > 100


def test_settle_refuses_a_pose_outside_the_board():
    with pytest.raises(ValueError):
        native.settle((0,) * WIDTH, "I", 0, 0, 5)  # cells at columns -2 and -1


def test_values_and_phases_match_the_python_exactly():
    rng = random.Random(2)
    boards = [_random_columns(rng) for _ in range(400)] + [(0,) * WIDTH]
    for values in _param_sets():
        value_of, phase_rule = tunedplan.make_rules(values)
        native_params = native.params(values)
        for columns in boards:
            for phase in (wellplan.BUILD, wellplan.SPEND):
                for cleared in range(5):
                    expected = value_of(phase, cleared, columns)
                    found = native.value(native_params, phase, cleared, columns)
                    assert found == expected and math.copysign(1, found) == math.copysign(1, expected), \
                        (values, phase, cleared, columns, found, expected)
            level, drought = rng.randint(18, 45), rng.randint(0, 20)
            assert native.phase(native_params, level, drought, columns) == \
                phase_rule(level)(drought, columns)


def test_phase_boundaries_match_the_python():
    final = json.loads(FINAL_PARAMS.read_text())["resolved"]
    _, phase_rule = tunedplan.make_rules(final)
    native_params = native.params(final)
    for stack in range(0, 21):
        columns = tuple((1 << GRID_ROWS) - (1 << (GRID_ROWS - stack)) for _ in range(WIDTH))
        for level in (18, 28, 29, 30, 39):
            for drought in range(0, 12):
                assert native.phase(native_params, level, drought, columns) == \
                    phase_rule(level)(drought, columns)


def test_levels_and_gravity_match_the_python():
    for start_level in range(20):
        for lines in range(0, 431):
            assert native.level_for_lines(lines, start_level) == level_for_lines(lines, start_level)
    for level in range(0, 60):
        for ruleset in (DOUBLE_KILLSCREEN, "classic_ntsc_extended"):
            assert native.gravity(level, ruleset) == gravity(level, ruleset)


# ---------------------------------------------------------------- reach (step 2)

REACH_LEVELS = (18, 19, 28, 29, 38, 39, 45)
INTERVALS = (2, 3, 4, 5)  # 30, 20, 15 and 12 Hz


def _cave_columns(rng: random.Random) -> tuple[int, ...]:
    """A random stack with gaps under roofs, so slides, tucks and spins are possible."""
    columns = list(_random_columns(rng))
    for index, column in enumerate(columns):
        visible = column >> HIDDEN_ROWS
        if visible and rng.random() < 0.5:
            top = (visible & -visible).bit_length() - 1 + HIDDEN_ROWS
            for row in range(top + 1, min(GRID_ROWS, top + 1 + rng.randint(1, 3))):
                columns[index] &= ~(1 << row)
    return tuple(columns)


def _random_flight(rng: random.Random, piece: str, period: int, interval: int) -> Flight:
    if rng.random() < 0.5:  # a fresh piece, sometimes the game's first
        delay = rng.choice((0, 0, rng.randint(1, 120)))
        return Flight(gravity_counter=rng.randrange(period), first_delay=delay)
    return Flight(orientation=rng.randrange(orientation_count(piece)), x=rng.randint(0, WIDTH - 1),
                  y=rng.randint(0, 14), gravity_counter=rng.randrange(period),
                  first_delay=rng.choice((0, 0, rng.randint(1, 30))),
                  shift_wait=rng.randrange(interval), rotate_wait=rng.randrange(interval))


def _python_reach(columns, piece, flight, period, rows, interval):
    found = reach._search(columns, piece, flight.orientation, flight.x, flight.y,
                          flight.gravity_counter, flight.first_delay, flight.shift_wait,
                          flight.rotate_wait, period, rows, interval)
    return [(r.orientation, r.x, r.y, r.masks) for r in found]


def test_reach_matches_the_python_in_order_with_every_mask():
    rng = random.Random(4)
    cases = placements = late = 0
    for _ in range(3000):
        columns = (_cave_columns if rng.random() < 0.6 else _random_columns)(rng)
        piece = rng.choice(PIECES)
        level, interval = rng.choice(REACH_LEVELS), rng.choice(INTERVALS)
        period, rows = gravity(level, DOUBLE_KILLSCREEN)
        flight = _random_flight(rng, piece, period, interval)
        expected = _python_reach(columns, piece, flight, period, rows, interval)
        assert native.reachable(columns, piece, flight, period=period, rows=rows,
                                interval=interval) == expected, (columns, piece, flight, level, interval)
        cases += 1
        placements += len(expected)
        late += sum(1 for *_, masks in expected if 0 in masks)  # a wait before a press
    assert placements > 20 * cases // 2 and late > 1000


def test_reach_matches_the_python_from_every_spawn_on_an_empty_and_a_full_board():
    full = tuple((1 << GRID_ROWS) - (1 << 3) for _ in range(WIDTH))  # only rows 0-2 open
    for columns in ((0,) * WIDTH, full):
        for piece in PIECES:
            for level in REACH_LEVELS:
                for interval in INTERVALS:
                    period, rows = gravity(level, DOUBLE_KILLSCREEN)
                    expected = _python_reach(columns, piece, Flight(), period, rows, interval)
                    assert native.reachable(columns, piece, Flight(), period=period, rows=rows,
                                            interval=interval) == expected


def test_reach_matches_the_python_where_the_600_frame_cap_cuts_the_search():
    rng = random.Random(5)
    cut = 0
    for _ in range(150):
        columns = _random_columns(rng)
        piece = rng.choice(PIECES)
        interval = rng.choice(INTERVALS)
        period = 48  # level 0's gravity, so a long first-piece delay reaches the cap
        flight = Flight(gravity_counter=rng.randrange(period), first_delay=rng.randint(520, 620))
        expected = _python_reach(columns, piece, flight, period, 1, interval)
        assert native.reachable(columns, piece, flight, period=period, rows=1,
                                interval=interval) == expected
        cut += not expected
    assert 20 < cut < 130  # some searches end at the cap with no lock, some lock before it


def test_reach_locks_on_the_last_frame_before_the_cap_and_not_after_it():
    # Only rows 0-3 are open, so a fresh piece locks on its first gravity tick, which
    # comes on frame ``first_delay`` (the counter keeps counting through the delay).
    nearly_full = tuple((1 << GRID_ROWS) - (1 << 4) for _ in range(WIDTH))
    for first_delay in (598, 599, 600, 601):
        for piece in PIECES:
            flight = Flight(first_delay=first_delay)
            expected = _python_reach(nearly_full, piece, flight, 48, 1, 2)
            assert bool(expected) == (first_delay < 600)
            assert native.reachable(nearly_full, piece, flight, period=48, rows=1,
                                    interval=2) == expected
