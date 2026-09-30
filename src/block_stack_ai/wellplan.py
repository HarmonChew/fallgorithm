"""A bounded well plan: one designated well, an explicit budget and a spend rule.

Experiment 003's ``tetris`` agent scores every reachable placement with a
declared objective that rewards a four-line clear and a one-column well, but
never decides *when* to hold that well or when to give it up. Measured on the ten
evaluation seeds it kept the field flat, spent its I pieces on one- and two-line
clears and topped out in all ten games: 349.5 mean lines and 40 Tetrises in 3495
lines. The reward for a well was what a buried hole costs, so a one-column slot
was score-neutral there, and the height terms always preferred the flatter board;
the agent held no well it could name.

This module adds a plan around the same reachable set and the same one piece of
player-visible lookahead. Everything it adds is visible-information only:

* **one designated well column** (:data:`WELL_COLUMN`, the rightmost column).
  The plan measures the field -- every other column -- and the well separately,
  so a slot held for an I is not charged as a buried hole and does not have to
  compete with the height terms on their own ground; its value is the rows it
  will clear.
* an explicit **reserve**: :func:`well_reserve` is exactly how many rows a
  vertical I dropped in the well column would clear on this board right now,
  capped at four, so the plan is rewarded for the clear it is actually setting
  up rather than for an abstract column depth.
* an explicit **stack-height budget** (:data:`HEIGHT_BUDGET`): the plan builds
  only while the whole stack is below it, and the settled board's height over
  the budget is charged again, so a candidate that pushes the stack past the
  budget loses to one that does not. The height is measured over the whole
  22-row grid rather than the visible field alone, so a column whose cells rest
  in the two hidden rows above the ceiling counts as over the budget instead of
  as an empty column.
* **spend-or-abandon at a self-tracked I-drought bound** (:data:`DROUGHT_BOUND`):
  the plan counts the pieces it has been shown since an I was last visible to it,
  as the current piece or as the preview, and past that bound it stops holding
  the well and scores with the frozen flat-board heuristic instead -- the
  objective Experiment 002's ``lookahead`` agent survives on. The drought is the
  plan's own count of the pieces it was shown; nothing here reads a future piece,
  an RNG stream or an engine counter.

The two phases are the plan:

* ``BUILD`` -- the stack is under the budget and an I has been visible within the
  bound. A four-line clear earns ``tetrises``; a one-, two- or three-line clear
  is charged ``premature_clear`` per row short of four, because it breaks up the
  rows the reserve is being built from; a placement that clears nothing is
  charged nothing. The field's holes, aggregate height, bumpiness and maximum
  height are charged at the frozen heuristic's own rates -- except for holes,
  which are charged at twice that rate, because a covered cell is what stops a
  reserve band from ever completing: the controller of Experiment 002's model
  drops pieces straight down, so a cell buried under the surface cannot be
  filled again. The reserve earns ``reserve`` per row it would clear, up to four.
* ``SPEND`` -- the same frozen flat-board objective Experiment 002 uses, over all
  ten columns including the well. The plan stops reserving and clears rows
  eagerly, which is how it gives the well back when the I is late or the stack
  reaches the budget.

The value of a current placement is its own plan value plus the best plan value
the preview piece can reach on the board it leaves, and the phase of the preview
is read the same way from the visible preview: it is ``BUILD`` when the preview
is an I (the piece that completes the reserve) or while the settled stack is
still under the budget. A current placement whose preview piece has no admissible
placement has value ``-inf``. Ties keep the first placement in canonical
enumeration order (orientation ascending, then column ascending).

Scoring the current placement's *whole* value is a second change from Experiment
003, beside the plan, and the experiment's measured result is attributed to both.
Experiment 003's objective adds only the current placement's clear term
(``clear_term``) to the preview's value, so its current board is judged by the
clear it makes and by nothing else; this objective adds :func:`plan_value` for
the same placement, which is the field terms, the reserve and the overflow in
``BUILD`` and the entire frozen :func:`~block_stack_ai.heuristic.feature_score`
in ``SPEND``. The two are therefore not the same function of a current board even
where the plan's phase, budget and drought memory are held equal, and the
difference moves the chosen placement on reachable boards: the experiment's
retained evidence derives one such board in each phase rather than asserting that
the compositions agree.

The reachable-set enumeration is Experiment 002's own
:func:`block_stack_ai.pathaware._reachable`, reused rather than re-derived so the
candidate set and the lock a candidate is expected to reach cannot drift.

The constants are declared once, here, and are never revised against the ten-seed
evaluation this experiment reports. Their shape comes from the design direction
above; their values were fixed from measurements on a development seed set that
excludes the ten evaluation seeds -- odd seeds 1, 3, 5, 7, 9 and 15, 17, 19, 21,
23 -- which is stated in the experiment's notes rather than presented as a
pre-existing choice. No evaluation outcome was used to choose or revise any of
them.

The agent that drives this objective is declared here too, beside the weights it
scores by, and the runner builds it here rather than in
:mod:`block_stack_ai.agents`. That is deliberate: a run record's declared
objective names the source of the module that *builds* the agent whose
placements it replayed, and that module is the shared agent factory for the
agents declared there. The factory's bytes are what a frozen record's identity
covers, so an agent added to it would invalidate the records of every agent it
already dispatches -- including Experiment 003's, whose ten-seed measurement this
experiment is compared against. An objective that owns its agent keeps the
factory's source fixed, and the record of each agent still names the code that
actually chose its placements.
"""

from __future__ import annotations

from typing import Any

from .agents import PlacementAgent
from .heuristic import (
    GRID_ROWS,
    HEIGHT,
    HIDDEN_ROWS,
    WIDTH,
    BoardFeatures,
    Placement,
    feature_score,
)
from .pathaware import (
    _reachable,
    column_features,
    gravity_period,
    grid_columns,
    level_for_lines,
    settle_columns,
)

# The agent name a suite configures for this objective.
PLAN_AGENT = "tetris_plan"

# The declared objective. The field terms copy the frozen heuristic's rates
# (``heuristic.WEIGHTS``) rather than importing them, so this experiment's
# objective is declared in exactly one place and cannot move when that module
# changes; the doubled hole rate, the clear term, the reserve term, the budget
# and the drought bound are what this experiment adds.
PLAN_WEIGHTS = {
    "tetrises": 8.0,
    "premature_clear": -1.0,
    "holes": -2.0,
    "aggregate_height": -0.5,
    "bumpiness": -0.5,
    "max_height": -1.0,
    "reserve": 6.0,
    "overflow": -2.0,
}
# A vertical I fills four rows, so four is the most a reserve can be worth.
RESERVE_CAP = 4
# One reserve band of four rows under one full band of field: the plan may build
# a band while it holds a band of reserve, and no more.
HEIGHT_BUDGET = 8
# The pieces that lay one complete band of the nine-column field (nine columns
# times four rows, four cells per piece). Past that many shown pieces without a
# visible I, the reserve is waiting on nothing.
DROUGHT_BOUND = 9
WELL_COLUMN = WIDTH - 1
# The plan's two phases: hold the well, or spend it and clear eagerly.
BUILD = "build"
SPEND = "spend"
TIE_BREAK = (
    "first highest-valued placement in canonical enumeration order: orientation "
    "ascending, then column ascending"
)


def weights_record() -> dict[str, object]:
    """The declared weights and plan constants, as the run record publishes them."""
    return {
        **PLAN_WEIGHTS,
        "reserve_cap": RESERVE_CAP,
        "height_budget": HEIGHT_BUDGET,
        "drought_bound": DROUGHT_BOUND,
        "well_column": WELL_COLUMN,
        "tie_break": TIE_BREAK,
    }


def clear_term(lines_cleared: int) -> float:
    """The clear-size reward for one lock.

    A four-line clear earns ``tetrises``. Clearing nothing is free. Anything
    between is a premature clear and is charged ``premature_clear`` per row short
    of four, so a single wastes the most setup and a triple the least.
    """
    if lines_cleared == 4:
        return PLAN_WEIGHTS["tetrises"]
    if lines_cleared == 0:
        return 0.0
    return PLAN_WEIGHTS["premature_clear"] * (4 - lines_cleared)


def column_heights(columns: tuple[int, ...]) -> tuple[int, ...]:
    """The height of each column over the whole stack, hidden rows included.

    ``column_features`` reads the visible field alone, and that is the right
    measure for the frozen geometry: the engine clears visible rows, and the two
    hidden rows above the ceiling are a separate buffer it never clears. The
    plan's budget is not a field term, though. A column whose cells all sit in
    those hidden rows has reached the ceiling — a piece came to rest above the
    visible field because nothing below it was free — and reading it as height 0
    would report an empty column on a topped-out stack: ``holds_well`` would keep
    building, ``initial_phase`` would never take the SPEND transition and
    ``plan_value``'s overflow would charge nothing for the state that has already
    spent the stack. The height is therefore measured from the lowest occupied
    cell of the whole 22-row grid, which is exactly the value
    ``column_features`` reports for a column with a visible cell and is above
    ``HEIGHT`` for a hidden-only column, so the budget and the overflow read that
    state as over the ceiling.
    """
    heights = []
    for column in columns:
        if not column:
            heights.append(0)
            continue
        lowest = (column & -column).bit_length() - 1
        heights.append(GRID_ROWS - lowest)
    return tuple(heights)


def stack_height(columns: tuple[int, ...]) -> int:
    """The height of the whole stack: the tallest of the ten columns."""
    return max(column_heights(columns))


def field_features(columns: tuple[int, ...], well: int = WELL_COLUMN) -> BoardFeatures:
    """The existing board features over the field columns, with the well excluded.

    The designated well is the plan's reserve, not a buried hole: its column is
    left out of every field term, so holding four rows of it does not read as
    four holes and does not have to outbid the height terms. Bumpiness is summed
    over adjacent field columns only, so the step down into the well is not
    counted either. The heights are :func:`column_heights` — the whole stack,
    hidden rows included — so a field column resting on the ceiling reads as over
    the budget; the holes stay the visible field's, because a cell above the
    ceiling is occupied rather than covered.
    """
    heights = column_heights(columns)
    field_heights = [height for index, height in enumerate(heights) if index != well]
    holes = 0
    for index, column in enumerate(columns):
        if index == well:
            continue
        visible = column >> HIDDEN_ROWS
        if not visible:
            continue
        top = (visible & -visible).bit_length() - 1
        holes += (HEIGHT - top) - (visible >> top).bit_count()
    bumpiness = sum(
        abs(heights[index] - heights[index + 1])
        for index in range(WIDTH - 1)
        if index != well and index + 1 != well
    )
    return BoardFeatures(holes, sum(field_heights), bumpiness,
                         max(field_heights, default=0))


def well_reserve(columns: tuple[int, ...], well: int = WELL_COLUMN) -> int:
    """The rows a vertical I dropped in the well column would clear now, capped at four.

    The I enters the well from above and descends to its floor: it comes to rest
    on the well column's topmost filled cell, the engine's own descent rule for a
    straight drop, and the rows it fills are the four above that cell. The
    reserve is how many of those rows the lock actually clears, which is exactly
    what a Tetris is. A board whose well could not take the I -- the four rows it
    would fill reach above the ceiling -- has no reserve.
    """
    blocked = GRID_ROWS
    for row in range(GRID_ROWS):
        if columns[well] >> row & 1:
            blocked = row
            break
    landing = blocked - RESERVE_CAP
    if landing < 0:
        return 0
    _, cleared = settle_columns(columns, "I", 1, well, landing)
    return min(cleared, RESERVE_CAP)


def holds_well(drought: int, height: int) -> bool:
    """Whether the plan builds the reserve for one more piece.

    The plan holds while the stack is under the stack-height budget and an I has
    been visible to it within the drought bound. Past either, it spends: the
    reserve has waited longer than a band takes to lay, or the stack has reached
    the height the reserve was allowed to cost.
    """
    return drought < DROUGHT_BOUND and height < HEIGHT_BUDGET


def next_drought(drought: int, next_piece: str) -> int:
    """The drought the plan would report after the visible preview piece spawns.

    The preview is the only thing the plan can see beyond the current piece, so
    this is the honest update: the count restarts when the preview is the I that
    completes the reserve, and otherwise grows by one, exactly as the agent's own
    counter grows when it is shown the piece after that.
    """
    return 0 if next_piece == "I" else drought + 1


def initial_phase(drought: int, columns: tuple[int, ...]) -> str:
    """The phase a board and a drought put the plan in."""
    return BUILD if holds_well(drought, stack_height(columns)) else SPEND


def plan_value(phase: str, lines_cleared: int, columns: tuple[int, ...]) -> float:
    """The declared value of one settled board in one phase.

    ``BUILD`` scores the field terms, the clear and the reserve the board holds;
    ``SPEND`` scores the frozen flat-board objective over every column, the
    abandon the plan falls back to.
    """
    if phase == SPEND:
        return feature_score(column_features(columns), lines_cleared)
    features = field_features(columns)
    return (
        clear_term(lines_cleared)
        + PLAN_WEIGHTS["holes"] * features.holes
        + PLAN_WEIGHTS["aggregate_height"] * features.aggregate_height
        + PLAN_WEIGHTS["bumpiness"] * features.bumpiness
        + PLAN_WEIGHTS["max_height"] * features.max_height
        + PLAN_WEIGHTS["reserve"] * well_reserve(columns)
        + PLAN_WEIGHTS["overflow"] * max(0, stack_height(columns) - HEIGHT_BUDGET)
    )


def _best_next_value(phase: str, columns: tuple[int, ...], piece: str, period: int) -> float:
    """The preview piece's best declared value on this board, or ``-inf``."""
    reachable = _reachable(columns, piece, period, 0)
    if not reachable:
        return float("-inf")
    return max(plan_value(phase, placement.lines_cleared, settled)
               for placement, settled in reachable)


def plan_choice(grid: tuple[tuple[int, ...], ...], piece: str, next_piece: str, *,
                drought: int, level: int, lines: int, start_level: int,
                first_delay_remaining: int, ruleset: str, mode: str) -> Placement | None:
    """The reachable current placement with the highest declared plan value.

    Each admissible placement of the current piece is applied to the board, and
    the preview piece is then placed on the result by the same reachable-set rule
    and scored in the phase the plan would be in for it -- the preview is
    visible, so the drought can be advanced honestly by one piece and the settled
    stack's height is on the board. The highest value wins, ties keep the first in
    canonical enumeration order, and ``None`` means no current placement is
    admissible (the controller then falls back to holding Down where the piece
    spawned, as the other placement agents do). The preview's gravity uses the
    level the current placement's clear would leave, as Experiment 002's
    lookahead does.
    """
    columns = grid_columns(grid)
    phase = initial_phase(drought, columns)
    current = _reachable(columns, piece, gravity_period(level), first_delay_remaining)
    if not current:
        return None
    wrap = ruleset == "classic_ntsc_strict"
    challenge = mode == "challenge"
    best = None
    best_value = None
    for placement, settled in current:
        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        next_phase = initial_phase(next_drought(drought, next_piece), settled)
        value = plan_value(phase, placement.lines_cleared, settled) + _best_next_value(
            next_phase, settled, next_piece, gravity_period(next_level)
        )
        if best_value is None or value > best_value:
            best, best_value = placement, value
    return best


class PlanAgent(PlacementAgent):
    """The bounded well plan, executed through the shared placement controller.

    The candidate set and the one piece of preview lookahead are the ones
    Experiment 002's and 003's agents use; what this agent adds is the plan's own
    memory: it counts the pieces it has been shown since an I was last visible to
    it, as the current piece or as the preview, and hands that count to the
    objective. Every other input is the state the engine reports, so the plan
    sees only what a player sees.
    """

    def __init__(self) -> None:
        super().__init__(None)

    def reset(self) -> None:
        super().reset()
        self._drought = 0

    def _choose(self, state: Any, grid: Any) -> Placement | None:
        # The count is updated once per spawned piece, from the two pieces the
        # agent is shown: an I in either place restarts it.
        self._drought = 0 if state.current_piece == "I" or state.next_piece == "I" \
            else self._drought + 1
        return plan_choice(
            grid,
            state.current_piece,
            state.next_piece,
            drought=self._drought,
            level=state.level,
            lines=state.lines,
            start_level=state.start_level,
            first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset,
            mode=state.mode,
        )


def build_agent(name: str, seed: int) -> PlanAgent:
    """Build this objective's agent, for the runner's factory to dispatch to.

    The plan is deterministic and parameterless, so the seed a suite fixes for
    replay is unused here; it stays in the signature so this factory answers the
    same call as the shared one. The name is checked rather than trusted, so a
    caller that hands this module another agent's name is told so.
    """
    if name != PLAN_AGENT:
        raise ValueError(f"unknown agent: {name!r}")
    return PlanAgent()
