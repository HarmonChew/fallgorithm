"""An input-limited movement model: tap speed, no soft drop, gravity only.

:mod:`block_stack_ai.pathaware` assumes a controller that taps every other frame
and drops the piece with Down. A human-like player (and BetaTetris's benchmark
format) is slower: one tap every few frames, and the piece falls by gravity
alone. This module models that player for one piece.

:class:`Limits` holds the two numbers of the format. The tap interval is
``round(60.0988 / tap_hz)`` frames, at least 2 because a tap needs a release
frame (30 Hz is 2, 20 Hz is 3, 15 Hz is 4, 12 Hz is 5). The reaction time in
frames is ``round(reaction_ms * 60.0988 / 1000)`` (300 ms is 18).

The movement policy is the simple fixed one pathaware uses, for one target
``(orientation, x)``. Each frame, if the piece is not yet in the target
orientation and the rotation tap timer is ready, press the rotation that turns
the short way; if it is not yet in the target column and the shift tap timer is
ready, press the direction that moves toward it. Shifts and rotations have
separate timers, so both may be pressed on the same frame. Nothing else is ever
pressed. Gravity does the rest: a piece locks at the first failed downward move,
and at level 39 of the double-killscreen ruleset every gravity tick tries two
one-row moves.

A target is *reachable* when every press the policy makes succeeds (a blocked
press makes the target unreachable, not retried) and the piece has reached the
target orientation and column before it locks. The frame order mirrors
``Game::tick`` in ``block-stack/core/src/game.cpp``: shift, then rotate, then the
gravity counter and downward moves.

Because the policy never looks at the board, the sequence of poses a target
needs is the same on every board. :func:`_script` builds that sequence once (and
caches it), as a list of "this pose must fit at this row" checks; a board is then
tested against the checks. :func:`reachable` returns each reachable target with
the lock row and the per-frame masks that produce it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .heuristic import GRID_ROWS, SPAWN_ORIGIN_Y, WIDTH
from .pathaware import (
    _TABLES,
    _X_OFFSET,
    DAS_INITIAL,
    DAS_REPEAT,
    LEFT,
    RIGHT,
    ROTATE_CCW,
    ROTATE_CW,
    SPAWN_X,
    _landing,
    fits_at,
    gravity_period,
)
from .pieces import cells, orientation_count

FRAMES_PER_SECOND = 60.0988
# The double-killscreen ruleset's level from which gravity moves two rows.
DOUBLE_GRAVITY_LEVEL = 39
DOUBLE_KILLSCREEN = "classic_ntsc_double_killscreen"
_NEVER_SKIPPED = 1 << 20


@dataclass(frozen=True, slots=True)
class Limits:
    """A format's tap speed (presses per second) and reaction time."""

    tap_hz: float
    reaction_ms: float

    @property
    def tap_interval(self) -> int:
        """Frames from one press to the next press of the same kind."""
        return max(2, round(FRAMES_PER_SECOND / self.tap_hz))

    @property
    def reaction_frames(self) -> int:
        return round(self.reaction_ms * FRAMES_PER_SECOND / 1000)


@dataclass(frozen=True, slots=True)
class Flight:
    """Everything the model needs to continue one piece's descent.

    The defaults are the state of a piece on its first active frame. ``shift_wait``
    and ``rotate_wait`` are the frames left before each tap timer is ready again;
    ``frame`` counts the frames since the piece spawned.
    """

    orientation: int = 0
    x: int = SPAWN_X
    y: int = SPAWN_ORIGIN_Y
    gravity_counter: int = 0
    first_delay: int = 0
    previous_input: int = 0
    das_counter: int = 0
    shift_wait: int = 0
    rotate_wait: int = 0
    frame: int = 0


@dataclass(frozen=True, slots=True)
class Reach:
    """One reachable final placement and the masks (from the given flight) that make it."""

    orientation: int
    x: int
    y: int
    masks: tuple[int, ...]


def gravity(level: int, ruleset: str) -> tuple[int, int]:
    """The gravity period (frames per tick) and rows tried per tick at a level."""
    rows = 2 if ruleset == DOUBLE_KILLSCREEN and level >= DOUBLE_GRAVITY_LEVEL else 1
    return gravity_period(level), rows


def next_wait(wait: int, pressed: bool, interval: int) -> int:
    """A tap timer after one frame: restarted by a press, otherwise counting down."""
    return interval - 1 if pressed else max(0, wait - 1)


@dataclass(frozen=True, slots=True)
class _Script:
    masks: tuple[int, ...]
    # (lowest row the piece occupies, table entry, row to test, is a gravity move)
    events: tuple[tuple[int, object, int, bool], ...]
    last_pose_event: int
    start_y: int
    end_y: int
    final_entry: object


def _event(table, orientation: int, x: int, row: int, drop: bool):
    entry = table[orientation][x + _X_OFFSET] if -1 <= x <= WIDTH else None
    return (row + entry[9] if entry is not None else _NEVER_SKIPPED, entry, row, drop)


def _script(piece: str, flight: Flight, target_orientation: int, target_x: int,
            period: int, rows: int, interval: int) -> _Script:
    """The board-independent frames that take a flight to the target pose."""
    table = _TABLES[piece]
    count = orientation_count(piece)
    orientation, x, y = flight.orientation, flight.x, flight.y
    counter, delay = flight.gravity_counter, flight.first_delay
    previous, das = flight.previous_input, flight.das_counter
    shift_wait, rotate_wait = flight.shift_wait, flight.rotate_wait
    masks: list[int] = []
    events: list[tuple[int, object, int, bool]] = []
    last_pose = -1
    while (orientation, x) != (target_orientation, target_x):
        if len(masks) > 200:
            raise AssertionError("script did not reach its target pose")
        mask = 0
        if orientation != target_orientation and rotate_wait == 0:
            clockwise = (target_orientation - orientation) % count
            counterclockwise = (orientation - target_orientation) % count
            mask |= ROTATE_CW if clockwise <= counterclockwise else ROTATE_CCW
        if x != target_x and shift_wait == 0:
            mask |= LEFT if target_x < x else RIGHT
        newly = mask & ~previous
        # Game::process_horizontal. A press is a fresh edge here, so it always
        # attempts; the auto-repeat branch is the engine's and is never reached.
        if mask & (LEFT | RIGHT):
            if newly & (LEFT | RIGHT):
                das = 0
                attempt = True
            else:
                das += 1
                attempt = das >= DAS_INITIAL
                if attempt:
                    das = DAS_INITIAL - DAS_REPEAT
            if attempt:
                x += 1 if mask & RIGHT else -1
                events.append(_event(table, orientation, x, y, False))
                last_pose = len(events) - 1
        # Game::process_rotation: no wall kicks, the origin is untouched.
        if newly & ROTATE_CW:
            orientation = (orientation + 1) % count
        elif newly & ROTATE_CCW:
            orientation = (orientation - 1 + count) % count
        if newly & (ROTATE_CW | ROTATE_CCW):
            events.append(_event(table, orientation, x, y, False))
            last_pose = len(events) - 1
        # Game::process_drop without soft drop: the first-piece delay swallows
        # frames, then gravity tries ``rows`` downward moves each period.
        counter += 1
        if delay > 0:
            delay -= 1
        elif counter >= period:
            counter = 0
            for _ in range(rows):
                y += 1
                events.append(_event(table, orientation, x, y, True))
        shift_wait = next_wait(shift_wait, bool(mask & (LEFT | RIGHT)), interval)
        rotate_wait = next_wait(rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)), interval)
        previous = mask
        masks.append(mask)
    return _Script(tuple(masks), tuple(events), last_pose, flight.y, y,
                   table[orientation][x + _X_OFFSET])


# A fresh piece's scripts depend only on the piece, target and gravity, so they are
# kept; mid-flight scripts are one-off and would only fill the cache.
_cached_script = lru_cache(maxsize=None)(_script)


def _lock_row(script: _Script, columns: tuple[int, ...], top: int) -> int | None:
    """The row the piece locks at on this board, or ``None`` if it cannot get there.

    ``top`` is the highest occupied row of the board; a check whose piece lies
    entirely above it cannot collide and is skipped.
    """
    y = script.start_y
    for index, (bottom, entry, row, drop) in enumerate(script.events):
        if bottom < top or fits_at(entry, columns, row):
            if drop:
                y = row
        elif drop and index > script.last_pose_event:
            break  # a failed gravity move locks the piece, which is already in place
        else:
            return None  # blocked press, or the piece locked before arriving
    else:
        if fits_at(script.final_entry, columns, y + 1):
            y = _landing(script.final_entry, columns, y)
    if not fits_at(script.final_entry, columns, y):
        return None  # spawned on top of the stack and stuck: a top-out, not a placement
    return y


def reachable(columns: tuple[int, ...], piece: str, flight: Flight, *, period: int,
              rows: int, limits: Limits) -> tuple[Reach, ...]:
    """Every placement the limited player can reach from ``flight``, canonical order.

    ``columns`` are the ten column bitmasks of :mod:`block_stack_ai.pathaware`.
    The masks run from the flight's next frame until the piece is in its target
    pose; after that the player presses nothing and gravity lands the piece.
    """
    interval = limits.tap_interval
    top = min(((column & -column).bit_length() - 1 for column in columns if column),
              default=GRID_ROWS)
    found = []
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            make = _cached_script if flight.frame == 0 else _script
            script = make(piece, flight, orientation, x, period, rows, interval)
            y = _lock_row(script, columns, top)
            if y is not None:
                found.append(Reach(orientation, x, y, script.masks))
    return tuple(found)
