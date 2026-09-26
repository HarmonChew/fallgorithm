"""Board model and fixed evaluation for one-piece greedy placement.

The model works on the engine's grid: rows ``0`` and ``1`` are the two hidden
rows above the visible field and rows ``2..21`` are visible rows ``0..19``.
Row indices follow the engine's own ``fits``/``lock`` rules, including the
allowance for minos that come to rest above the visible field.

Features and weights follow the conventional flattened-board evaluation: the
immediate line clear plus penalties for holes, aggregate height, bumpiness and
maximum height. The weights are fixed here, chosen once from that documented
family, and are never tuned against the evaluation seeds.

Placements are straight drops: a piece enters its column at the engine's spawn
origin row and descends only downward, so a column blocked at that origin has no
placement. Lateral movement during the descent and entering in one column and
sliding over to another are out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pieces import cells, orientation_count

WIDTH = 10
HEIGHT = 20
HIDDEN_ROWS = 2
GRID_ROWS = HIDDEN_ROWS + HEIGHT

WEIGHTS = {
    "lines_cleared": 1.0,
    "holes": -1.0,
    "aggregate_height": -0.5,
    "bumpiness": -0.5,
    "max_height": -1.0,
}
TIE_BREAK = "first highest-scoring placement in enumeration order: orientation ascending, then x ascending"

# The native piece origin row a straight drop must enter at: the model's ``y``
# is the engine's own piece-origin row (engine row = model row - HIDDEN_ROWS),
# and ``Game::spawn`` (core/src/game.cpp) sets ``state_.y = 0`` while an in-place
# rotation leaves the origin untouched (``Game::process_rotation`` keeps x and
# y). Measured on the registered read-only library: a spawn trace reports
# ``(x=5, y=0, orientation=0)``, and ``set_piece`` for every piece at every
# orientation reports origin row 0, unchanged by clockwise rotations. The
# integration test ``test_enumeration_matches_engine_straight_drops_from_the_spawn_origin``
# keeps this measured value honest for the whole placement set.
SPAWN_ORIGIN_Y = 0

Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class BoardFeatures:
    holes: int
    aggregate_height: int
    bumpiness: int
    max_height: int


@dataclass(frozen=True, slots=True)
class Placement:
    """One enumerated placement and the score of its resulting board."""

    piece: str
    orientation: int
    x: int
    y: int
    lines_cleared: int
    score: float


def weights_record() -> dict[str, object]:
    """The fixed weights and tie-break rule as they are written into a run record."""
    return {**WEIGHTS, "tie_break": TIE_BREAK}


def board_grid(board: object, hidden_rows: object) -> Grid:
    """Convert binding board rows (20) and hidden rows (2) into the model grid."""
    rows = [[1 if cell else 0 for cell in row] for row in hidden_rows]
    rows.extend([1 if cell else 0 for cell in row] for row in board)
    return tuple(tuple(row) for row in rows)


def board_features(grid: Grid) -> BoardFeatures:
    """Holes, aggregate height, bumpiness and maximum height of a settled grid.

    Heights and holes cover the visible field only: the engine clears full
    visible rows, and minos resting in the hidden rows are not part of the
    cleared field.
    """
    heights = []
    holes = 0
    for column in range(WIDTH):
        top = None
        filled = 0
        for row in range(HIDDEN_ROWS, GRID_ROWS):
            if grid[row][column]:
                if top is None:
                    top = row
                filled += 1
        if top is None:
            heights.append(0)
            continue
        heights.append(GRID_ROWS - top)
        holes += GRID_ROWS - top - filled
    bumpiness = sum(abs(left - right) for left, right in zip(heights, heights[1:]))
    return BoardFeatures(holes, sum(heights), bumpiness, max(heights))


def feature_score(features: BoardFeatures, lines_cleared: int) -> float:
    return (
        WEIGHTS["lines_cleared"] * lines_cleared
        + WEIGHTS["holes"] * features.holes
        + WEIGHTS["aggregate_height"] * features.aggregate_height
        + WEIGHTS["bumpiness"] * features.bumpiness
        + WEIGHTS["max_height"] * features.max_height
    )


def fits(grid: Grid, piece: str, orientation: int, x: int, y: int) -> bool:
    """Whether the piece fits at this origin, mirroring the engine's boundary rules."""
    for offset_x, offset_y in cells(piece, orientation):
        column = x + offset_x
        row = y + offset_y + HIDDEN_ROWS
        if column < 0 or column >= WIDTH or row < 0 or row >= GRID_ROWS:
            return False
        if grid[row][column]:
            return False
    return True


def settle(grid: Grid, piece: str, orientation: int, x: int, y: int) -> tuple[Grid, int]:
    """Lock the piece, clear full visible rows, and return the settled grid and clear count.

    This mirrors ``Game::lock``/``Game::clear_rows``: only the 20 visible rows
    are scanned for full rows and only they are compacted, so a hidden row is
    never cleared and no hidden cell is ever moved. Within the visible field the
    surviving rows collect at the bottom in order and the cleared rows reopen
    empty at its top, so a row below the lowest cleared row keeps its place. The
    hidden rows are a separate buffer: a lock writes a hidden cell only for a
    mino resting above the ceiling, and a visible clear leaves the buffer
    byte-identical. Verified cell for cell against the registered native library
    for a hidden-only lock, a ceiling-straddling lock that clears visible row 0,
    a mid-field clear with the buffer already occupied, and a double clear. The
    hidden-row tests in ``tests/test_heuristic.py`` and
    ``tests/test_integration.py`` fail if the hidden rows are shifted instead.
    """
    rows = [list(row) for row in grid]
    for offset_x, offset_y in cells(piece, orientation):
        rows[y + offset_y + HIDDEN_ROWS][x + offset_x] = 1
    visible = rows[HIDDEN_ROWS:]
    remaining = [row for row in visible if not all(row)]
    cleared = len(visible) - len(remaining)
    if cleared:
        # The hidden rows stay put: only the visible field above the cleared
        # rows moves down, into the empty rows reopened at its top.
        rows[HIDDEN_ROWS:] = [[0] * WIDTH for _ in range(cleared)] + remaining
    return tuple(tuple(row) for row in rows), cleared


def _drop_y(grid: Grid, piece: str, orientation: int, x: int) -> int | None:
    """Origin row of a straight drop into this column, or None when it cannot fit.

    The piece enters the column at the engine's spawn origin row
    (:data:`SPAWN_ORIGIN_Y`) and only ever descends from there. A straight drop
    cannot pass through an occupied cell, and it cannot start anywhere else: a
    column whose spawn origin is obstructed has no legal placement, even if the
    piece would fit further down. From the origin the piece descends through
    consecutive free origins and stops at the first obstruction or the floor.
    Lateral movement during the descent and entering in one column and sliding
    across are out of scope: the frame controller aligns the piece at the spawn
    row first and then holds Down.
    """
    if not fits(grid, piece, orientation, x, SPAWN_ORIGIN_Y):
        return None
    y = SPAWN_ORIGIN_Y
    while fits(grid, piece, orientation, x, y + 1):
        y += 1
    return y


def enumerate_placements(grid: Grid, piece: str) -> tuple[Placement, ...]:
    """Every unique rotation and legal column, scored by its settled board.

    Enumeration order is canonical: orientation ascending, then column
    ascending. A placement is a straight drop that enters its column at the
    engine's spawn origin row and then descends only downward, which is what the
    frame controller below can actually execute. Lateral movement during the
    descent and entering in one column and sliding over to another are out of
    scope, so a column blocked at its spawn origin contributes no placement.
    """
    placements = []
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            y = _drop_y(grid, piece, orientation, x)
            if y is None:
                continue
            settled, cleared = settle(grid, piece, orientation, x, y)
            placements.append(
                Placement(piece, orientation, x, y, cleared,
                          feature_score(board_features(settled), cleared))
            )
    return tuple(placements)
