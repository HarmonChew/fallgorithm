"""Path-aware placement enumeration and one-piece lookahead.

The straight-drop model in :mod:`block_stack_ai.heuristic` enumerates a piece's
unique rotations and legal columns and assumes the piece enters its column at
the engine's spawn origin row and only descends from there. That is what the
frame controller of :class:`block_stack_ai.agents.PlacementAgent` tries to
execute, but the engine is free to refuse the attempt: shifting happens at
whatever row the piece has reached, gravity keeps lowering the piece while the
controller presses, and a blocked press is simply dropped. A piece can therefore
lock in a column the straight-drop model never predicted.

This module derives the placement set the controller can really execute. A
candidate is an ``(orientation, x)`` the controller aims at; the plan is
simulated frame by frame from the engine's native spawn state using the same mask
function the controller uses (:func:`plan_mask`), mirroring ``Game::tick``'s
active-phase order in ``core/src/game.cpp`` -- horizontal, then rotation, then
gravity/soft drop, each per-frame counter advanced as the engine advances it --
and the engine's ``fits`` and ``lock`` rules. A candidate is admissible only when
the simulated lock is exactly the placement that was aimed at and the engine
would really write the piece there.

Boards are held as ten column bitmasks (bit ``r`` of a column is row ``r`` of the
22-row model grid, rows 0-1 being the engine's two hidden rows). The bitmask
``settle`` and feature code mirrors :func:`heuristic.settle` and
:func:`heuristic.board_features`, and the unit tests pin the two to each other.

The lookahead is one piece deep. For every admissible current placement the next
piece is placed on the board that placement leaves, using the same reachable set
and scored with the existing fixed features and weights, and the current
placement whose best next placement scores highest is chosen. A current placement
that leaves the next piece no admissible placement at all has value ``-inf``: it
is worse than any placement that leaves the next piece one, so it is chosen only
when every current placement shares that fate. Ties keep the first placement in
canonical enumeration order (orientation ascending, then column ascending), the
same order :func:`heuristic.enumerate_placements` uses. When no current placement
is admissible the controller keeps pressing Down where the piece spawned, exactly
as :class:`PlacementAgent`'s fallback does.
"""

from __future__ import annotations

from dataclasses import dataclass

from .heuristic import (
    GRID_ROWS,
    HEIGHT,
    HIDDEN_ROWS,
    SPAWN_ORIGIN_Y,
    WIDTH,
    BoardFeatures,
    Placement,
    feature_score,
)
from .pieces import cells, orientation_count

# Gameplay bits of the engine's controller mask (AI API input table).
LEFT = 1
RIGHT = 2
DOWN = 4
ROTATE_CW = 8
ROTATE_CCW = 16

# The engine spawns every piece at x = 5 (Game::spawn, core/src/game.cpp).
SPAWN_X = 5

# NTSC gravity lookup table and level-transition thresholds, mirrored from
# core/src/rules.cpp. Gravity is indexed by level and capped at 29.
GRAVITY_PERIOD = (
    48, 43, 38, 33, 28, 23, 18, 13, 8, 6,
    5, 5, 5, 4, 4, 4, 3, 3, 3, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 1,
)
FIRST_TRANSITION_LINES = (
    10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
    100, 100, 100, 100, 100, 100, 110, 120, 130, 140,
)

# The controller's horizontal DAS: a single-frame press on one frame and a
# release on the next, so the auto-repeat threshold is never reached. The model
# mirrors the engine's counter anyway so the step stays a faithful transcription
# of Game::process_horizontal.
DAS_INITIAL = 16
DAS_REPEAT = 6

# A plan always terminates: gravity lowers the piece until it locks, so the
# longest run is a first-piece delay plus a full descent. The bound only guards
# the mirror against a transcription bug.
MAX_PLAN_FRAMES = 4096

# Column-index window of the precomputed piece tables: an aim of x can only move
# by one column at a time, so cells outside this window can never be reached and
# are recorded as "does not fit".
_X_OFFSET = 1
_X_VALUES = range(-1, 11)

# Visible rows are model rows 2..21; the engine clears only those, and the two
# hidden rows above them are a separate buffer ``Game::clear_rows`` never touches.
_VISIBLE_MASK = ((1 << GRID_ROWS) - 1) ^ ((1 << HIDDEN_ROWS) - 1)
_HIDDEN_MASK = (1 << HIDDEN_ROWS) - 1

Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class PlanOutcome:
    """Where the engine locks a planned piece, from its native spawn state."""

    orientation: int
    x: int
    y: int
    reached: bool
    top_out: bool


def gravity_period(level: int) -> int:
    """The engine's gravity period for a level, capped at level 29."""
    return GRAVITY_PERIOD[level if level < 29 else 29]


def level_for_lines(lines: int, start_level: int, *, wrap: bool = False,
                    challenge: bool = False) -> int:
    """The level the engine reports after clearing ``lines`` total lines.

    Mirrors ``Game::update_level``: a challenge game never raises its level, a
    strict game wraps the target into a byte, and both keep the start level until
    the start level's transition threshold is passed. Only gravity depends on the
    level, and gravity is capped at level 29, so the mirror is exact for the
    period even where the raw level differs.
    """
    if challenge:
        return start_level
    threshold = FIRST_TRANSITION_LINES[start_level]
    if lines < threshold:
        return start_level
    target = start_level + 1 + (lines - threshold) // 10
    return target & 0xFF if wrap else target


def plan_mask(orientation: int, x: int, plan: tuple[int, int] | None, release: bool,
              count: int) -> tuple[int, bool]:
    """The controller's next mask for a plan, and the next release flag.

    This is the frame controller's whole decision: rotate toward the aimed
    orientation by the shorter way, one press per horizontal step, then hold Down.
    A press is always followed by a release frame so the next press is a fresh
    edge. ``plan`` is ``None`` when no placement was chosen, which holds Down
    where the piece spawned. The simulation calls this same function, so the
    model cannot drift from the controller.
    """
    if release:
        return 0, False
    if plan is None:
        return DOWN, False
    target_orientation, target_x = plan
    if orientation != target_orientation:
        clockwise = (target_orientation - orientation) % count
        counterclockwise = (orientation - target_orientation) % count
        return (ROTATE_CW if clockwise <= counterclockwise else ROTATE_CCW), True
    if x != target_x:
        return (LEFT if target_x < x else RIGHT), True
    return DOWN, False


def grid_columns(grid: Grid) -> tuple[int, ...]:
    """The model grid as ten column bitmasks (bit ``row`` set when filled)."""
    return tuple(
        sum(1 << row for row in range(GRID_ROWS) if grid[row][column])
        for column in range(WIDTH)
    )


def column_features(columns: tuple[int, ...]) -> BoardFeatures:
    """The existing board features, computed from the column bitmasks.

    Identical to :func:`heuristic.board_features` on the equivalent grid: heights
    and holes cover the visible field only, the top of a column is its topmost
    filled visible cell, and a hole is an empty visible cell below that top.
    """
    heights = []
    holes = 0
    for column in columns:
        visible = column >> HIDDEN_ROWS
        if not visible:
            heights.append(0)
            continue
        top = (visible & -visible).bit_length() - 1
        height = HEIGHT - top
        holes += height - (visible >> top).bit_count()
        heights.append(height)
    bumpiness = sum(abs(left - right) for left, right in zip(heights, heights[1:]))
    return BoardFeatures(holes, sum(heights), bumpiness, max(heights))


def settle_columns(columns: tuple[int, ...], piece: str, orientation: int, x: int,
                   y: int) -> tuple[tuple[int, ...], int]:
    """Lock a piece into the column masks, clearing full visible rows.

    Identical to :func:`heuristic.settle` on the equivalent grid: only the 20
    visible rows are scanned and compacted, the hidden rows are a separate buffer
    that a visible clear leaves byte-identical, and the surviving rows collect at
    the bottom in their original order.
    """
    settled = list(columns)
    for offset_x, offset_y in cells(piece, orientation):
        settled[x + offset_x] |= 1 << (y + offset_y + HIDDEN_ROWS)
    common = settled[0]
    for column in settled[1:]:
        common &= column
    full = common & _VISIBLE_MASK
    if not full:
        return tuple(settled), 0
    cleared = full.bit_count()
    rows = []
    while full:
        lowest = full & -full
        rows.append(lowest.bit_length() - 1)
        full ^= lowest
    for row in rows:
        # Only the visible field compacts. The hidden buffer is a separate
        # buffer the engine never touches in ``Game::clear_rows``, so its bits
        # are carried over untouched while the visible cells below the cleared
        # row move up by one.
        low_mask = ((1 << row) - 1) & _VISIBLE_MASK
        high_mask = ~((1 << (row + 1)) - 1)
        for index in range(WIDTH):
            column = settled[index]
            settled[index] = ((column & _HIDDEN_MASK) | (column & high_mask)
                              | ((column & low_mask) << 1))
    return tuple(settled), cleared


def _cell_table(piece: str) -> tuple[tuple[tuple[int, ...] | None, ...], ...]:
    """Per orientation, per aim x: the piece's absolute cells in the model grid.

    Each entry is ``(column0, row0, column1, row1, column2, row2, column3,
    row3, min_row_offset, max_row_offset)`` flattened for a four-cell check, or
    ``None`` when the piece would hang off either side of the board.
    """
    table = []
    for orientation in range(orientation_count(piece)):
        row = []
        for x in _X_VALUES:
            offsets = cells(piece, orientation)
            columns = [x + offset_x for offset_x, _ in offsets]
            if any(column < 0 or column >= WIDTH for column in columns):
                row.append(None)
                continue
            flat: tuple[int, ...] = ()
            for column, (_, offset_y) in zip(columns, offsets):
                flat += (column, offset_y + HIDDEN_ROWS)
            row_offsets = flat[1::2]
            row.append(flat + (min(row_offsets), max(row_offsets)))
        table.append(tuple(row))
    return tuple(table)


_TABLES = {piece: _cell_table(piece) for piece in ("I", "J", "L", "O", "S", "T", "Z")}


def fits_at(entry: tuple[int, ...] | None, columns: tuple[int, ...], y: int) -> bool:
    """Whether the piece at this aim occupies free cells at origin row ``y``."""
    if entry is None or y + entry[8] < 0 or y + entry[9] >= GRID_ROWS:
        return False
    return not (
        (columns[entry[0]] >> (y + entry[1])) & 1
        or (columns[entry[2]] >> (y + entry[3])) & 1
        or (columns[entry[4]] >> (y + entry[5])) & 1
        or (columns[entry[6]] >> (y + entry[7])) & 1
    )


def _landing(entry: tuple[int, ...], columns: tuple[int, ...], y: int) -> int:
    """The lowest origin the piece can descend to from ``y`` with Down held.

    The first filled cell strictly below each piece cell blocks it; the piece
    stops on the row above the highest of those blocks. Every origin between
    ``y`` and the result is free once the first downward attempt succeeds, so
    this is the terminus of the engine's frame-by-frame descent.
    """
    landing = GRID_ROWS
    for index in range(0, 8, 2):
        column = entry[index]
        offset_y = entry[index + 1]
        base = y + offset_y + 1
        rest = columns[column] >> base
        blocked = base + (rest & -rest).bit_length() - 1 if rest else GRID_ROWS
        candidate = blocked - offset_y - 1
        if candidate < landing:
            landing = candidate
    return landing


def _simulate(piece: str, columns: tuple[int, ...], target_orientation: int,
              target_x: int, period: int, first_delay_remaining: int) -> PlanOutcome:
    """One plan's exact mask sequence, from the spawn state to the engine's lock.

    ``columns`` is the board the piece spawns into and is only read: the caller
    settles the lock afterwards, once it knows the placement is admissible.
    """
    table = _TABLES[piece]
    count = orientation_count(piece)
    plan = (target_orientation, target_x)
    orientation = 0
    x = SPAWN_X
    y = SPAWN_ORIGIN_Y
    release = False
    previous_input = 0
    gravity_counter = 0
    soft_drop_counter = 0
    das_counter = 0
    for _ in range(MAX_PLAN_FRAMES):
        mask, release = plan_mask(orientation, x, plan, release, count)
        if mask == DOWN:
            # Down is held from here on, so only downward attempts remain. The
            # first attempt decides: if it fails, Game::lock commits at this
            # origin -- and Game::spawn has no collision test, so the origin may
            # not fit (an overlapped spawn), which the lock rejects by writing
            # nothing. If it succeeds the piece descends to its terminus.
            entry = table[target_orientation][target_x + _X_OFFSET]
            if not fits_at(entry, columns, y + 1):
                return PlanOutcome(target_orientation, target_x, y, True,
                                   not fits_at(entry, columns, y))
            return PlanOutcome(target_orientation, target_x, _landing(entry, columns, y), True, False)
        newly = mask & ~previous_input
        # Game::process_horizontal: a held Down suppresses shifting, and a fresh
        # press always attempts a move. The controller never holds a direction
        # long enough for the auto-repeat threshold, so that branch is the
        # engine's, not the controller's, and exists to keep the mirror faithful.
        if (mask & (LEFT | RIGHT)) != 0:
            if (newly & (LEFT | RIGHT)) != 0:
                das_counter = 0
                attempt = True
            else:
                das_counter += 1
                attempt = das_counter >= DAS_INITIAL
                if attempt:
                    das_counter = DAS_INITIAL - DAS_REPEAT
            if attempt:
                if (mask & RIGHT) != 0:
                    entry = table[orientation][x + 1 + _X_OFFSET]
                    if fits_at(entry, columns, y):
                        x += 1
                    else:
                        das_counter = DAS_INITIAL
                else:
                    entry = table[orientation][x - 1 + _X_OFFSET]
                    if fits_at(entry, columns, y):
                        x -= 1
                    else:
                        das_counter = DAS_INITIAL
        # Game::process_rotation: no wall kicks, and the origin is untouched.
        if (newly & ROTATE_CW) != 0:
            candidate = (orientation + 1) % count
            if fits_at(table[candidate][x + _X_OFFSET], columns, y):
                orientation = candidate
        elif (newly & ROTATE_CCW) != 0:
            candidate = (orientation - 1 + count) % count
            if fits_at(table[candidate][x + _X_OFFSET], columns, y):
                orientation = candidate
        # Game::process_drop: the first-piece delay consumes frames before any
        # gravity attempt, then soft drop and gravity both attempt downward.
        gravity_counter += 1
        if first_delay_remaining > 0:
            if (newly & DOWN) != 0:
                first_delay_remaining = 0
            else:
                first_delay_remaining -= 1
                previous_input = mask
                continue
        soft_attempt = False
        if soft_drop_counter == 0:
            if (mask & (LEFT | RIGHT)) == 0 and (newly & (LEFT | RIGHT | DOWN)) == DOWN:
                soft_drop_counter = 1
        elif (mask & (LEFT | RIGHT | DOWN)) != DOWN:
            soft_drop_counter = 0
        else:
            soft_drop_counter += 1
            if soft_drop_counter >= 3:
                soft_drop_counter = 1
                soft_attempt = True
        if soft_attempt or gravity_counter >= period:
            gravity_counter = 0
            if fits_at(table[orientation][x + _X_OFFSET], columns, y + 1):
                y += 1
            else:
                # Game::lock: a failed downward attempt commits the lock, and the
                # lock itself rejects an origin whose cells collide.
                locked = fits_at(table[orientation][x + _X_OFFSET], columns, y)
                return PlanOutcome(orientation, x, y,
                                   orientation == target_orientation and x == target_x,
                                   not locked)
        previous_input = mask
    raise AssertionError("plan simulation did not reach a lock")


def simulate_plan(grid: Grid, piece: str, plan: tuple[int, int], *, level: int,
                  first_delay_remaining: int) -> PlanOutcome:
    """Where the engine locks the piece when the controller executes ``plan``."""
    return _simulate(piece, grid_columns(grid), plan[0], plan[1],
                     gravity_period(level), first_delay_remaining)


def _reachable(columns: tuple[int, ...], piece: str, period: int,
               first_delay_remaining: int) -> tuple[tuple[Placement, tuple[int, ...]], ...]:
    """Every admissible placement and the board it leaves, in canonical order."""
    placements = []
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            outcome = _simulate(piece, columns, orientation, x, period, first_delay_remaining)
            if not outcome.reached or outcome.top_out:
                continue
            settled, cleared = settle_columns(columns, piece, orientation, x, outcome.y)
            placements.append((
                Placement(piece, orientation, x, outcome.y, cleared,
                          feature_score(column_features(settled), cleared)),
                settled,
            ))
    return tuple(placements)


def reachable_placements(grid: Grid, piece: str, *, level: int,
                         first_delay_remaining: int) -> tuple[Placement, ...]:
    """Every placement the frame controller can execute, in canonical order."""
    return tuple(
        placement for placement, _ in
        _reachable(grid_columns(grid), piece, gravity_period(level), first_delay_remaining)
    )


def _best_next_value(columns: tuple[int, ...], piece: str, level: int) -> float:
    """The score of the next piece's best admissible placement on this board.

    ``-inf`` when the next piece has no admissible placement at all. A current
    placement is worth its best admissible next placement, so a preview piece the
    controller cannot place anywhere is worse than every placement that leaves it
    a real one. The rejected Down fallback is not a placement: scoring its board
    instead would let a move that strands the preview piece outrank a move that
    leaves it a placement, which is the outcome the reachable set exists to
    prevent.
    """
    reachable = _reachable(columns, piece, gravity_period(level), 0)
    if not reachable:
        return float("-inf")
    return max(placement.score for placement, _ in reachable)


def lookahead_choice(grid: Grid, piece: str, next_piece: str, *, level: int, lines: int,
                     start_level: int, first_delay_remaining: int, ruleset: str,
                     mode: str) -> Placement | None:
    """The reachable current placement with the best reachable next placement.

    Each admissible placement of the current piece is applied to the model grid
    and the next piece -- the one the binding's player-visible preview reports --
    is placed on the result by the same reachable-set rule, scored with the
    existing fixed features and weights. The current placement whose best next
    placement scores highest wins; a current placement whose next piece has no
    admissible placement has value ``-inf``, so it loses to every placement that
    leaves the next piece one and is kept only if all of them do. Ties keep the
    first in canonical enumeration order. ``None`` means no current placement is
    admissible.
    """
    current = _reachable(grid_columns(grid), piece, gravity_period(level), first_delay_remaining)
    if not current:
        return None
    wrap = ruleset == "classic_ntsc_strict"
    challenge = mode == "challenge"
    best = None
    best_value = None
    for placement, settled in current:
        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        value = _best_next_value(settled, next_piece, next_level)
        if best_value is None or value > best_value:
            best, best_value = placement, value
    return best
