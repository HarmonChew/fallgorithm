"""The input-limited movement model against the native engine."""

from __future__ import annotations

import random

import pytest

from block_stack_ai.engine import create_game
from block_stack_ai.heuristic import board_grid
from block_stack_ai.limits import Flight, Limits, gravity, next_wait, reachable
from block_stack_ai.pathaware import (
    LEFT,
    RIGHT,
    ROTATE_CCW,
    ROTATE_CW,
    grid_columns,
    settle_columns,
)
from block_stack_ai.pieces import PIECES, orientation_count

pytestmark = pytest.mark.integration

RULESET = "classic_ntsc_double_killscreen"
LEVELS = (18, 19, 28, 29, 38, 39, 45)
TAP_RATES = (30, 15, 12)
# Offsets of integer fields in the engine's saved-state blob (see Game::save_state).
BOARD_AT = 56
LEVEL_AT, GRAVITY_COUNTER_AT, FIRST_DELAY_AT = 348, 356, 404


def _random_board(rng):
    """A believable stack: random column heights with a few holes, no full rows."""
    board = [[0] * 10 for _ in range(20)]
    tallest = rng.choice((9, 9, 15, 19))  # tall stacks reach the spawn rows
    for column in range(10):
        for row in range(20 - rng.randint(0, tallest), 20):
            if rng.random() > 0.08:
                board[row][column] = 1
    for row in board:
        if all(row):
            row[rng.randrange(10)] = 0
    return board


def _start(rng, board, piece, level, first_delay, counter):
    """A game in the active phase with this board, piece, level and counters."""
    game = create_game(ruleset=RULESET, mode="endless", start_level=18, seed=rng.randrange(65536))
    game.set_piece(piece, x=5, y=0, rotation=0)
    blob = bytearray(game.save_state())
    # Written into the saved state so a stack may overlap the spawn, as the engine allows.
    blob[BOARD_AT:BOARD_AT + 200] = bytes(cell for row in board for cell in row)
    for offset, value in ((LEVEL_AT, level), (GRAVITY_COUNTER_AT, counter),
                          (FIRST_DELAY_AT, first_delay)):
        blob[offset:offset + 8] = value.to_bytes(8, "little")
    state = game.load_state(bytes(blob))
    assert (state.level, state.gravity_counter, state.first_delay_remaining) \
        == (level, counter, first_delay)
    return game


def _policy_mask(piece, state, target, shift_wait, rotate_wait):
    """The fixed policy, written again from the engine's own reported pose."""
    orientation, x = target
    mask = 0
    count = orientation_count(piece)
    if state.orientation != orientation and rotate_wait == 0:
        clockwise = (orientation - state.orientation) % count
        counterclockwise = (state.orientation - orientation) % count
        mask |= ROTATE_CW if clockwise <= counterclockwise else ROTATE_CCW
    if state.x != x and shift_wait == 0:
        mask |= LEFT if x < state.x else RIGHT
    return mask


def _engine_outcome(game, piece, target, interval):
    """Play the policy on the engine: (lock row, masks until it arrived), or None.

    ``None`` means the target is not reached: a press was blocked, the game ended,
    or the piece locked in another pose.
    """
    shift_wait = rotate_wait = 0
    masks = []
    state = game.state
    arrived_at = 0 if (state.orientation, state.x) == target else None
    count = orientation_count(piece)
    for _ in range(400):
        mask = _policy_mask(piece, state, target, shift_wait, rotate_wait)
        before = state
        state, events = game.step(mask)
        masks.append(mask)
        if mask & (LEFT | RIGHT) and state.x != before.x + (1 if mask & RIGHT else -1):
            return None
        if mask & ROTATE_CW and state.orientation != (before.orientation + 1) % count:
            return None
        if mask & ROTATE_CCW and state.orientation != (before.orientation - 1) % count:
            return None
        if arrived_at is None and (state.orientation, state.x) == target:
            arrived_at = len(masks)
        shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
        rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)), interval)
        if events.game_over:
            return None
        if events.locked:
            if arrived_at is None:
                return None
            return state.y, tuple(masks[:arrived_at])
    raise AssertionError("the piece never locked")


def _check_case(rng, piece, level, hz, first_delay, counter, board):
    limits = Limits(hz, 0)
    period, rows = gravity(level, RULESET)
    game = _start(rng, board, piece, level, first_delay, counter)
    blob = game.save_state()
    state = game.state
    columns = grid_columns(board_grid(state.board, state.hidden_rows))
    flight = Flight(gravity_counter=counter, first_delay=first_delay)
    predicted = {(r.orientation, r.x): r for r in
                 reachable(columns, piece, flight, period=period, rows=rows, limits=limits)}
    checked = 0
    for orientation in range(orientation_count(piece)):
        for x in range(-1, 11):
            game.load_state(blob)
            outcome = _engine_outcome(game, piece, (orientation, x), limits.tap_interval)
            reach = predicted.get((orientation, x))
            if reach is None:
                assert outcome is None, (piece, level, hz, orientation, x)
                continue
            assert outcome is not None, (piece, level, hz, orientation, x)
            assert outcome == (reach.y, reach.masks), (piece, level, hz, orientation, x)
            # The recorded masks, then silence, put the piece in the predicted place.
            game.load_state(blob)
            for mask in reach.masks + (0,) * 400:
                state, events = game.step(mask)
                if events.locked:
                    break
            assert not events.game_over
            settled, cleared = settle_columns(columns, piece, orientation, x, reach.y)
            assert grid_columns(board_grid(state.board, state.hidden_rows)) == settled
            assert state.lines == cleared
            checked += 1
    game.close()
    return checked


def test_predicted_placements_match_the_engine_for_random_boards_levels_and_tap_rates():
    rng = random.Random(8)
    total = 0
    for level in LEVELS:
        for hz in TAP_RATES:
            for _ in range(6):
                piece = rng.choice(PIECES)
                first_delay = rng.choice((0, 0, 0, 96, 40))
                counter = rng.randrange(0, gravity(level, RULESET)[0])
                total += _check_case(rng, piece, level, hz, first_delay, counter,
                                     _random_board(rng))
    assert total > 500


def test_mid_flight_predictions_match_the_engine():
    """Stop a piece part-way, then predict from its real state and tap timers."""
    rng = random.Random(9)
    cases = 0
    for level in (18, 29, 39, 45):
        for hz in (30, 15):
            limits = Limits(hz, 0)
            interval = limits.tap_interval
            for _ in range(8):
                piece = rng.choice(PIECES)
                board = _random_board(rng)
                game = _start(rng, board, piece, level, 0, 0)
                period, rows = gravity(level, RULESET)
                # Drift toward an arbitrary first target for a few frames.
                first = (rng.randrange(orientation_count(piece)), rng.randrange(2, 8))
                shift_wait = rotate_wait = 0
                for _ in range(rng.randrange(1, 8)):
                    state = game.state
                    mask = _policy_mask(piece, state, first, shift_wait, rotate_wait)
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
                flight = Flight(
                    orientation=state.orientation, x=state.x, y=state.y,
                    gravity_counter=state.gravity_counter,
                    first_delay=state.first_delay_remaining,
                    previous_input=state.previous_input, das_counter=state.das_counter,
                    shift_wait=shift_wait, rotate_wait=rotate_wait, frame=state.frame)
                columns = grid_columns(board_grid(state.board, state.hidden_rows))
                predicted = {(r.orientation, r.x): r for r in reachable(
                    columns, piece, flight, period=period, rows=rows, limits=limits)}
                blob = game.save_state()
                for orientation in range(orientation_count(piece)):
                    for x in range(-1, 11):
                        game.load_state(blob)
                        outcome = _engine_policy_from(game, piece, (orientation, x), interval,
                                                      shift_wait, rotate_wait)
                        reach = predicted.get((orientation, x))
                        expected = None if reach is None else (reach.y, reach.masks)
                        assert outcome == expected, (piece, level, hz, orientation, x)
                        cases += reach is not None
                game.close()
    assert cases > 100


def _engine_policy_from(game, piece, target, interval, shift_wait, rotate_wait):
    """:func:`_engine_outcome` starting with the tap timers already running."""
    state = game.state
    count = orientation_count(piece)
    masks = []
    arrived_at = 0 if (state.orientation, state.x) == target else None
    for _ in range(400):
        mask = _policy_mask(piece, state, target, shift_wait, rotate_wait)
        before = state
        state, events = game.step(mask)
        masks.append(mask)
        if mask & (LEFT | RIGHT) and state.x != before.x + (1 if mask & RIGHT else -1):
            return None
        if mask & ROTATE_CW and state.orientation != (before.orientation + 1) % count:
            return None
        if mask & ROTATE_CCW and state.orientation != (before.orientation - 1) % count:
            return None
        if arrived_at is None and (state.orientation, state.x) == target:
            arrived_at = len(masks)
        shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
        rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)), interval)
        if events.game_over:
            return None
        if events.locked:
            return None if arrived_at is None else (state.y, tuple(masks[:arrived_at]))
    raise AssertionError("the piece never locked")


def test_two_row_gravity_cuts_off_far_columns_on_the_engine():
    board = [[0] * 10 for _ in range(20)]
    for row in range(10, 20):
        board[row] = [1] * 9 + [0]  # ten rows high with one open column, no full row
    rng = random.Random(1)
    reached = {}
    for level in (29, 45):
        game = _start(rng, board, "I", level, 0, 0)
        columns = grid_columns(board_grid(game.state.board, game.state.hidden_rows))
        period, rows = gravity(level, RULESET)
        reached[level] = {(r.orientation, r.x) for r in reachable(
            columns, "I", Flight(), period=period, rows=rows, limits=Limits(30, 0))}
        game.close()
    assert reached[45] < reached[29]
    far = (1, 0)
    assert far in reached[29] and far not in reached[45]
