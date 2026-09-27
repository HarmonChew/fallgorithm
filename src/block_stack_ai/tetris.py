"""Tetris-oriented evaluation and one-piece-lookahead placement choice.

Experiment 002's ``lookahead`` agent already plays only placements its own frame
controller can execute, and looks one piece ahead through the player-visible
preview. Its objective is the frozen flat-board score of
:data:`block_stack_ai.heuristic.WEIGHTS`, which rewards every cleared line alike
and has no term for the shape a Tetris (a four-line clear) needs. This module
adds a second, separately named objective for the same reachable set: it keeps
the frozen geometry, the reachable-set simulation and the one-piece lookahead,
and changes only how a candidate is scored.

The objective is declared here, once, before any evaluation run, and is never
revisited against evaluation outcomes:

* a four-line clear is the goal and earns ``tetrises``; a one-, two- or
  three-line clear is charged ``premature_clear`` per row short of four, because
  it breaks up the stack a Tetris was being built from; a placement that clears
  nothing is charged nothing, so the board terms still decide between two
  non-clearing moves;
* a buried hole and a tall column are penalised at the frozen heuristic's own
  rates, so the new agent cannot buy a well by burying the rest of the field;
* a one-column well earns ``well_depth`` per row of depth up to
  ``WELL_DEPTH_CAP`` rows: four rows is what a vertical I needs, and deeper holds
  only unfinished height the other terms already penalise.

The value of a current placement is its own clear term plus the best value the
preview piece can reach on the board the current placement leaves, and the
current placement with the highest value wins. Unlike Experiment 002's value,
the current placement's clear reward is part of the sum: without it the agent
could not tell a four-line clear from any other emptier board. A current
placement whose preview piece has no admissible placement has value ``-inf``,
so it loses to every placement that leaves the preview piece one, exactly as
Experiment 002's value does. Ties keep the first placement in canonical
enumeration order (orientation ascending, then column ascending).

The reachable-set enumeration is Experiment 002's own
:func:`block_stack_ai.pathaware._reachable`. It is reused rather than
re-derived so the candidate set and the lock a candidate is expected to reach
cannot drift between the two agents, and so the agent does not pay for
recomputing the column masks on every candidate; the leading underscore is the
module's internal marking, and Experiment 002's own tests already call it.
"""

from __future__ import annotations

from .heuristic import HEIGHT, HIDDEN_ROWS, WIDTH, Placement
from .pathaware import (
    _reachable,
    column_features,
    gravity_period,
    grid_columns,
    level_for_lines,
)

# The declared objective. The board terms copy the frozen heuristic's rates
# (``heuristic.WEIGHTS``) rather than importing them, so this experiment's
# objective is declared in exactly one place and cannot move when that module
# changes; the clear term and the well term are what this experiment adds.
TETRIS_WEIGHTS = {
    "tetrises": 8.0,
    "premature_clear": -1.0,
    "holes": -1.0,
    "aggregate_height": -0.5,
    "bumpiness": -0.5,
    "max_height": -1.0,
    "well_depth": 1.0,
}
WELL_DEPTH_CAP = 4
TIE_BREAK = (
    "first highest-valued placement in canonical enumeration order: orientation "
    "ascending, then column ascending"
)


def weights_record() -> dict[str, object]:
    """The declared weights, the well cap and the tie-break rule, as published."""
    return {**TETRIS_WEIGHTS, "well_depth_cap": WELL_DEPTH_CAP, "tie_break": TIE_BREAK}


def clear_term(lines_cleared: int) -> float:
    """The clear-size reward for one lock.

    A four-line clear earns ``tetrises``. Clearing nothing is free. Anything
    between is a premature clear and is charged ``premature_clear`` per row short
    of four, so a single wastes the most setup and a triple the least.
    """
    if lines_cleared == 4:
        return TETRIS_WEIGHTS["tetrises"]
    if lines_cleared == 0:
        return 0.0
    return TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)


def column_heights(columns: tuple[int, ...]) -> tuple[int, ...]:
    """The visible-field height of each column, as ``column_features`` reads it."""
    heights = []
    for column in columns:
        visible = column >> HIDDEN_ROWS
        if not visible:
            heights.append(0)
            continue
        top = (visible & -visible).bit_length() - 1
        heights.append(HEIGHT - top)
    return tuple(heights)


def well_depth(columns: tuple[int, ...]) -> int:
    """The deepest one-column well of a settled board, in rows.

    A well is a column lower than its immediate neighbours: the classic
    one-piece-wide slot a vertical I fills. An edge column has one neighbour and
    an interior column two, and the depth is the height difference to the
    shallower neighbour, so a slot beside a single tall wall does not read as
    deep. A flat board has no well and returns zero.
    """
    heights = column_heights(columns)
    best = 0
    for index, height in enumerate(heights):
        neighbours = []
        if index > 0:
            neighbours.append(heights[index - 1])
        if index + 1 < WIDTH:
            neighbours.append(heights[index + 1])
        depth = min(neighbours) - height
        if depth > best:
            best = depth
    return best


def tetris_value(lines_cleared: int, columns: tuple[int, ...]) -> float:
    """The declared objective for one settled board and the clear that produced it."""
    features = column_features(columns)
    return (
        clear_term(lines_cleared)
        + TETRIS_WEIGHTS["holes"] * features.holes
        + TETRIS_WEIGHTS["aggregate_height"] * features.aggregate_height
        + TETRIS_WEIGHTS["bumpiness"] * features.bumpiness
        + TETRIS_WEIGHTS["max_height"] * features.max_height
        + TETRIS_WEIGHTS["well_depth"] * min(well_depth(columns), WELL_DEPTH_CAP)
    )


def _best_next_value(columns: tuple[int, ...], piece: str, period: int) -> float:
    """The preview piece's best declared value on this board, or ``-inf``."""
    reachable = _reachable(columns, piece, period, 0)
    if not reachable:
        return float("-inf")
    return max(tetris_value(placement.lines_cleared, settled)
               for placement, settled in reachable)


def tetris_choice(grid: tuple[tuple[int, ...], ...], piece: str, next_piece: str, *,
                  level: int, lines: int, start_level: int, first_delay_remaining: int,
                  ruleset: str, mode: str) -> Placement | None:
    """The reachable current placement with the highest declared value.

    Each admissible placement of the current piece is applied to the board and
    scored by :func:`tetris_value` on its clear, and the preview piece is then
    placed on the result by the same reachable-set rule; the value of the
    current placement is its own clear term plus the best value the preview
    piece reaches. The highest value wins, ties keep the first in canonical
    enumeration order, and ``None`` means no current placement is admissible
    (the controller then falls back to holding Down where the piece spawned,
    exactly as Experiment 002's agent and the straight-drop agent do). The
    preview's gravity uses the level the current placement's clear would leave,
    as Experiment 002's lookahead does.
    """
    current = _reachable(grid_columns(grid), piece, gravity_period(level),
                         first_delay_remaining)
    if not current:
        return None
    wrap = ruleset == "classic_ntsc_strict"
    challenge = mode == "challenge"
    best = None
    best_value = None
    for placement, settled in current:
        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        value = clear_term(placement.lines_cleared) + _best_next_value(
            settled, next_piece, gravity_period(next_level)
        )
        if best_value is None or value > best_value:
            best, best_value = placement, value
    return best
