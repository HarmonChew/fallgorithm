"""The complete-reachability model against the native engine."""

from __future__ import annotations

import random

import pytest

from block_stack_ai.engine import create_game
from block_stack_ai.heuristic import board_grid
from block_stack_ai.limits import Flight, Limits, gravity, next_wait
from block_stack_ai.limits import reachable as limits_reachable
from block_stack_ai.pathaware import (
    LEFT,
    RIGHT,
    ROTATE_CCW,
    ROTATE_CW,
    grid_columns,
    settle_columns,
)
from block_stack_ai.pieces import PIECES, orientation_count
from block_stack_ai.reach import reachable

from test_limits_integration import LEVELS, RULESET, TAP_RATES, _random_board, _start

pytestmark = pytest.mark.integration


def _lock_by_masks(game, masks):
    """Feed the masks, then silence; return the state at the lock (or None for a top-out)."""
    for mask in tuple(masks) + (0,) * 600:
        state, events = game.step(mask)
        if events.game_over:
            return None
        if events.locked:
            return state
    raise AssertionError("the piece never locked")


def _check_case(rng, piece, level, hz, first_delay, counter, board):
    limits = Limits(hz, 0)
    period, rows = gravity(level, RULESET)
    game = _start(rng, board, piece, level, first_delay, counter)
    blob = game.save_state()
    columns = grid_columns(board_grid(game.state.board, game.state.hidden_rows))
    flight = Flight(gravity_counter=counter, first_delay=first_delay)
    found = reachable(columns, piece, flight, period=period, rows=rows, limits=limits)
    keys = {(r.orientation, r.x, r.y) for r in found}
    assert len(keys) == len(found)
    # Everything the fixed-route model reaches is reached here, on the same row.
    old = limits_reachable(columns, piece, flight, period=period, rows=rows, limits=limits)
    assert {(r.orientation, r.x, r.y) for r in old} <= keys
    for placement in found:
        game.load_state(blob)
        state = _lock_by_masks(game, placement.masks)
        assert state is not None, (piece, level, hz, placement)
        settled, cleared = settle_columns(columns, piece, placement.orientation, placement.x,
                                          placement.y)
        assert grid_columns(board_grid(state.board, state.hidden_rows)) == settled
        assert state.lines == cleared
    # Completeness: random legal tap sequences never lock anywhere outside the set.
    interval = limits.tap_interval
    count = orientation_count(piece)
    for _ in range(12):
        game.load_state(blob)
        shift_wait = rotate_wait = 0
        for _ in range(600):
            mask = 0
            if shift_wait == 0 and rng.random() < 0.3:
                mask |= rng.choice((LEFT, RIGHT))
            if rotate_wait == 0 and count > 1 and rng.random() < 0.3:
                mask |= rng.choice((ROTATE_CW, ROTATE_CCW))
            before = game.state
            state, events = game.step(mask)
            shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
            rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)), interval)
            if events.game_over:
                break
            if events.locked:
                # The piece locked in the pose it had before this frame's gravity: its
                # board gained exactly that piece, so find the pose from the board.
                row = [r for r in found
                       if grid_columns(board_grid(state.board, state.hidden_rows))
                       == settle_columns(columns, piece, r.orientation, r.x, r.y)[0]]
                assert row, (piece, level, hz, mask)
                break
    game.close()
    return len(found), len(found) - len(old)


def test_every_placement_is_exact_and_a_superset_of_the_fixed_route_model():
    rng = random.Random(10)
    total = extra = 0
    for level in LEVELS:
        for hz in TAP_RATES:
            for _ in range(5):
                piece = rng.choice(PIECES)
                first_delay = rng.choice((0, 0, 0, 96, 40))
                counter = rng.randrange(0, gravity(level, RULESET)[0])
                found, more = _check_case(rng, piece, level, hz, first_delay, counter,
                                          _random_board(rng))
                total += found
                extra += more
    assert total > 500
    assert extra > 0  # waiting and moving late does reach more placements


def test_a_slide_under_an_overhang_that_needs_waiting_is_found_and_works_on_the_engine():
    # A roof over columns 0-2 at row 17 with row 18 open beneath it. The flat I can only
    # get under the roof by dropping past it first and sliding left at the last moment.
    board = [[0] * 10 for _ in range(20)]
    board[17] = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    board[19] = [0, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    rng = random.Random(3)
    game = _start(rng, board, "I", 18, 0, 0)
    blob = game.save_state()
    columns = grid_columns(board_grid(game.state.board, game.state.hidden_rows))
    period, rows = gravity(18, RULESET)
    limits = Limits(30, 0)
    old = {(r.orientation, r.x, r.y) for r in limits_reachable(
        columns, "I", Flight(), period=period, rows=rows, limits=limits)}
    new = {r.key(): r for r in reachable(columns, "I", Flight(), period=period, rows=rows,
                                          limits=limits)}
    under = (0, 3, 18)  # flat I in columns 1-4 on row 18, two cells under the roof
    assert under not in old
    assert under in new
    game.load_state(blob)
    state = _lock_by_masks(game, new[under].masks)
    settled, _ = settle_columns(columns, "I", 0, 3, 18)
    assert grid_columns(board_grid(state.board, state.hidden_rows)) == settled
    assert new[under].masks.count(LEFT) == 2 and RIGHT not in new[under].masks
    game.close()


def test_mid_flight_search_matches_the_engine_state_and_timers():
    rng = random.Random(11)
    cases = 0
    for level in (18, 29, 39, 45):
        for hz in (30, 15):
            limits = Limits(hz, 0)
            interval = limits.tap_interval
            period, rows = gravity(level, RULESET)
            for _ in range(8):
                piece = rng.choice(PIECES)
                board = _random_board(rng)
                game = _start(rng, board, piece, level, 0, 0)
                shift_wait = rotate_wait = 0
                for _ in range(rng.randrange(1, 10)):
                    mask = 0
                    if shift_wait == 0:
                        mask |= rng.choice((0, LEFT, RIGHT))
                    if rotate_wait == 0:
                        mask |= rng.choice((0, ROTATE_CW))
                    state, events = game.step(mask)
                    shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
                    rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)),
                                            interval)
                    if events.locked or state.phase != "active":
                        break
                state = game.state
                if state.phase != "active":
                    game.close()
                    continue
                flight = Flight(state.orientation, state.x, state.y, state.gravity_counter,
                                state.first_delay_remaining, state.previous_input,
                                state.das_counter, shift_wait, rotate_wait, state.frame)
                columns = grid_columns(board_grid(state.board, state.hidden_rows))
                blob = game.save_state()
                found = reachable(columns, piece, flight, period=period, rows=rows, limits=limits)
                old = {r.key() if hasattr(r, "key") else (r.orientation, r.x, r.y)
                       for r in limits_reachable(columns, piece, flight, period=period,
                                                 rows=rows, limits=limits)}
                assert old <= {r.key() for r in found}
                for placement in found:
                    game.load_state(blob)
                    locked = _lock_by_masks(game, placement.masks)
                    settled, _ = settle_columns(columns, piece, placement.orientation,
                                                placement.x, placement.y)
                    assert grid_columns(board_grid(locked.board, locked.hidden_rows)) == settled
                    cases += 1
                game.close()
    assert cases > 100


def _cave_board(rng):
    """A random stack with roofs over open cells, so slides and tucks are possible."""
    board = _random_board(rng)
    for _ in range(rng.randint(1, 4)):
        row = rng.randint(4, 18)
        first = rng.randint(0, 8)
        last = rng.randint(first, min(9, first + 4))
        for column in range(first, last + 1):
            board[row][column] = 1
        for below in range(row + 1, min(20, row + 3)):
            for column in range(first, last + 1):
                if rng.random() < 0.7:
                    board[below][column] = 0
    for row in board:
        if all(row):
            row[rng.randrange(10)] = 0
    return board


def _every_tap_legal_lock(game, blob, interval):
    """Breadth-first over every tap-legal input on the engine; the set of (board, lines) locked.

    Each frame may press nothing or any allowed shift and rotation; a button is tappable
    only when its timer is ready (a press restarts it). No soft drop and no holding.
    """
    locks, seen, frontier = set(), set(), [(blob, 0, 0)]
    while frontier:
        following = []
        for saved, shift_wait, rotate_wait in frontier:
            shifts = (0, LEFT, RIGHT) if shift_wait == 0 else (0,)
            rotations = (0, ROTATE_CW, ROTATE_CCW) if rotate_wait == 0 else (0,)
            for shift in shifts:
                for rotate in rotations:
                    mask = shift | rotate
                    game.load_state(saved)
                    state, events = game.step(mask)
                    if events.game_over:
                        continue
                    if events.locked:
                        locks.add((grid_columns(board_grid(state.board, state.hidden_rows)),
                                   state.lines))
                        continue
                    waits = (interval - 1 if shift else max(0, shift_wait - 1),
                             interval - 1 if rotate else max(0, rotate_wait - 1))
                    key = (state.x, state.y, state.orientation, state.gravity_counter,
                           state.first_delay_remaining, *waits)
                    if key not in seen:
                        seen.add(key)
                        following.append((game.save_state(), *waits))
        frontier = following
    return locks


def test_reach_equals_an_exhaustive_search_of_tap_legal_inputs_on_cave_boards():
    rng = random.Random(21)
    checked = 0
    for piece, level, hz in (("I", 18, 30), ("J", 29, 30), ("T", 39, 30), ("L", 18, 15)):
        board = _cave_board(rng)
        period, rows = gravity(level, RULESET)
        counter = rng.randrange(period)
        game = _start(rng, board, piece, level, 0, counter)
        blob = game.save_state()
        columns = grid_columns(board_grid(game.state.board, game.state.hidden_rows))
        limits = Limits(hz, 0)
        found = reachable(columns, piece, Flight(gravity_counter=counter), period=period,
                          rows=rows, limits=limits)
        mine = {settle_columns(columns, piece, r.orientation, r.x, r.y) for r in found}
        assert _every_tap_legal_lock(game, blob, limits.tap_interval) == mine, (piece, level, hz)
        checked += len(mine)
        game.close()
    assert checked > 20
