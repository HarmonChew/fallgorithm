"""Board model and fixed evaluation for one-piece greedy placement.

The model works on the engine's grid: rows ``0`` and ``1`` are the two hidden
rows above the visible field and rows ``2..21`` are visible rows ``0..19``.
Row indices follow the engine's own ``fits``/``lock`` rules, including the
allowance for minos that come to rest above the visible field.

Features and weights follow the conventional flattened-board evaluation: the
immediate line clear plus penalties for holes, aggregate height, bumpiness and
maximum height. The weights are fixed here, chosen once from that documented
family, and are never tuned against the evaluation seeds.
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

    Only the visible field compacts, and it compacts downward: the surviving
    visible rows keep their order and collect at the bottom, so every row above
    a cleared row shifts down by the number of cleared rows below it, and the
    cleared rows reopen empty at the top of the visible field. The two hidden
    rows do not move: a piece locked above the ceiling keeps its hidden minos
    after a lower row clears. This mirrors the native lock exactly, which
    compacts ``state_.board`` alone and never touches ``state_.hidden_rows``
    (``Game::clear_rows``) and reports the hidden rows as a separate 2x10
    buffer. ``test_settle_keeps_hidden_rows_in_place_when_a_visible_line_clears``
    and ``test_placement_model_matches_a_native_lock_straddling_the_ceiling``
    pin that behaviour.
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
    """Origin row of a straight drop into this column, or None when it cannot fit."""
    y = -HIDDEN_ROWS
    while y <= HEIGHT and not fits(grid, piece, orientation, x, y):
        y += 1
    if y > HEIGHT:
        return None
    while fits(grid, piece, orientation, x, y + 1):
        y += 1
    return y


def enumerate_placements(grid: Grid, piece: str) -> tuple[Placement, ...]:
    """Every unique rotation and legal column, scored by its settled board.

    Enumeration order is canonical: orientation ascending, then column
    ascending. A placement is a straight drop from above the stack, which is
    what the frame controller below can actually execute.
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
