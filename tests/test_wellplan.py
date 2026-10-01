"""Unit tests for the bounded well plan and the plan agent's decisions.

Every test here uses constructed boards and the pure Python model, so the
registered unit suite stays fast; the native side of the contract is the
four-row clear in ``test_integration.py``. The objective's values are pinned
exactly, so the declared weights cannot drift unnoticed.

The constructed boards are boards a game can actually be in: no row is ever
already complete, because ``Game::clear_rows`` would have cleared one. That
matters for the reserve, which is measured by settling a vertical I and counting
the rows the lock clears.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from block_stack_ai import agents as agents_module
from block_stack_ai import pathaware, runner
from block_stack_ai import wellplan as wellplan_module
from block_stack_ai.agents import DOWN, PlacementAgent
from block_stack_ai.heuristic import (
    GRID_ROWS,
    HEIGHT,
    HIDDEN_ROWS,
    WIDTH,
    board_grid,
    feature_score,
)
from block_stack_ai.pathaware import column_features, grid_columns
from block_stack_ai.wellplan import (
    BUILD,
    DROUGHT_BOUND,
    HEIGHT_BUDGET,
    PLAN_AGENT,
    PLAN_WEIGHTS,
    RESERVE_CAP,
    SPEND,
    WELL_COLUMN,
    PlanAgent,
    build_agent,
    clear_term,
    column_heights,
    field_features,
    holds_well,
    initial_phase,
    next_drought,
    plan_choice,
    plan_value,
    stack_height,
    well_reserve,
    weights_record,
)

EMPTY_HIDDEN = ((0,) * WIDTH,) * 2
EMPTY_ROWS = tuple((0,) * WIDTH for _ in range(HEIGHT))
EMPTY_GRID = board_grid(EMPTY_ROWS, EMPTY_HIDDEN)

# The retained rationale, read here because two of these tests bind its prose to
# the boundary and the penalty the code actually implements.
NOTES = (Path(wellplan_module.__file__).resolve().parents[2] / "experiments"
         / "004-bounded-well-plan" / "notes.md")
OBJECTIVE_SECTION_START = "<!-- predeclared-objective:start -->"
OBJECTIVE_SECTION_END = "<!-- predeclared-objective:end -->"


def declared_objective_section() -> str:
    """The retained rationale section, between the markers the probe hashes."""
    text = NOTES.read_text(encoding="utf-8")
    start = text.index(OBJECTIVE_SECTION_START)
    end = text.index(OBJECTIVE_SECTION_END) + len(OBJECTIVE_SECTION_END)
    return text[start:end]


def grid_of(rows: list[list[int]], hidden=EMPTY_HIDDEN):
    return board_grid(tuple(tuple(row) for row in rows), hidden)


def blank_rows() -> list[list[int]]:
    return [[0] * WIDTH for _ in range(HEIGHT)]


def stacked(heights: list[int]) -> tuple[tuple[int, ...], ...]:
    """A grid whose columns are filled from the floor to the given heights."""
    rows = blank_rows()
    for column, height in enumerate(heights):
        for row in range(height):
            rows[HEIGHT - 1 - row][column] = 1
    return grid_of(rows)


def open_well(height: int) -> tuple[tuple[int, ...], ...]:
    """Nine columns filled to ``height`` and an empty designated well column."""
    return stacked([height] * (WIDTH - 1) + [0])


def columns_of(grid) -> tuple[int, ...]:
    return grid_columns(grid)


def choose(grid, piece: str, next_piece: str, *, drought: int = 0, first_delay: int = 0):
    return plan_choice(grid, piece, next_piece, drought=drought, level=18, lines=0,
                       start_level=18, first_delay_remaining=first_delay,
                       ruleset="classic_ntsc_extended", mode="endless")


def test_declared_weights_are_the_published_ones():
    """The objective is declared once, and the record names exactly those values."""
    assert PLAN_WEIGHTS == {
        "tetrises": 8.0,
        "premature_clear": -1.0,
        "holes": -2.0,
        "aggregate_height": -0.5,
        "bumpiness": -0.5,
        "max_height": -1.0,
        "reserve": 6.0,
        "overflow": -2.0,
    }
    record = weights_record()
    assert record == {
        **PLAN_WEIGHTS,
        "reserve_cap": RESERVE_CAP,
        "height_budget": HEIGHT_BUDGET,
        "drought_bound": DROUGHT_BOUND,
        "well_column": WELL_COLUMN,
        "tie_break": (
            "first highest-valued placement in canonical enumeration order: orientation "
            "ascending, then column ascending"
        ),
    }
    assert RESERVE_CAP == 4 and WELL_COLUMN == WIDTH - 1 == 9


def test_clear_term_rewards_only_the_four_line_clear():
    assert clear_term(4) == 8.0
    assert clear_term(0) == 0.0
    assert clear_term(1) == -3.0
    assert clear_term(2) == -2.0
    assert clear_term(3) == -1.0
    assert clear_term(4) > 0 > clear_term(3) > clear_term(2) > clear_term(1)


def test_column_heights_and_stack_height_read_the_frozen_features():
    """Where a column holds a visible cell, the plan's height is the frozen one.

    ``column_features`` measures the visible field alone; the plan measures the
    whole stack, so the two agree exactly on every column with a visible cell and
    differ only where a column's cells all rest above the ceiling — the case the
    next test pins.
    """
    for heights in ([0] * 10, list(range(0, 10)), [20] * 10, [4] * 9 + [0], [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]):
        columns = columns_of(stacked(heights))
        features = column_features(columns)
        assert max(column_heights(columns)) == features.max_height
        assert stack_height(columns) == max(heights)
        field = field_features(columns)
        assert field.max_height == max(heights[:WELL_COLUMN])
        assert field.aggregate_height == sum(heights[:WELL_COLUMN])


def test_a_column_resting_in_the_hidden_rows_is_over_the_budget():
    """Cells above the ceiling are stack height, not an empty column.

    The engine's two hidden rows are part of the stack: a piece comes to rest
    there when nothing below it is free, which the native integration test reaches
    by locking an O above the ceiling. Reading such a column as height 0 would
    leave the plan building on a topped-out stack — ``holds_well`` true, the SPEND
    transition unreachable and the overflow term zero — so the height is measured
    from the lowest occupied cell of the whole 22-row grid. The frozen field
    measure still reports nothing there, which is the reading this replaces.
    """
    hidden_only = (1, 2) + (0,) * (WIDTH - 2)
    heights = column_heights(hidden_only)
    assert heights[:2] == (GRID_ROWS, GRID_ROWS - 1)
    assert heights[2:] == (0,) * (WIDTH - 2)
    assert stack_height(hidden_only) == GRID_ROWS
    assert column_features(hidden_only).max_height == 0
    assert not holds_well(0, stack_height(hidden_only))
    assert initial_phase(0, hidden_only) == SPEND
    assert plan_value(BUILD, 0, hidden_only) < 0.0 == plan_value(
        BUILD, 0, columns_of(EMPTY_GRID))


def test_field_features_leave_the_designated_well_out_of_every_field_term():
    """The held well is a reserve, not four buried holes.

    A four-high field with an empty well column has no field holes at all, and
    the step down into the well is not bumpiness either, so holding the reserve
    does not have to outbid the frozen geometry. A buried cell *inside* the well
    column is not a field hole either: the plan keeps its own measure of what the
    well is worth, and the well is not part of the field it is trying to keep
    flat.
    """
    columns = columns_of(open_well(4))
    field = field_features(columns)
    assert (field.holes, field.aggregate_height, field.bumpiness, field.max_height) == (0, 36, 0, 4)

    # A cell buried under the top of the well column: the I would land above it,
    # and the field terms still report no holes of their own.
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        for column in range(WIDTH - 1):
            rows[row][column] = 1
    rows[HEIGHT - 1][WELL_COLUMN] = 1
    field = field_features(columns_of(grid_of(rows)))
    assert field.holes == 0


def test_well_reserve_is_the_rows_a_vertical_i_would_clear():
    """The reserve is the clear itself, measured by dropping the I in the well.

    A vertical I descends the well column to its floor and fills the four rows
    above the well column's topmost cell, so the reserve is how many of those
    rows the lock completes: one per complete row of the field below that band,
    four at most. An empty board has none, and a well whose band would reach
    above the ceiling takes no I at all.
    """
    assert well_reserve(columns_of(EMPTY_GRID)) == 0
    for depth in range(1, RESERVE_CAP + 1):
        assert well_reserve(columns_of(open_well(depth))) == depth
    assert well_reserve(columns_of(open_well(RESERVE_CAP + 3))) == RESERVE_CAP

    # A well column already filled while the field is missing a column beside it:
    # the I lands on top of the fill, and the band it fills is not complete.
    assert well_reserve(columns_of(stacked([6] * 8 + [0, 2]))) == 0


def test_a_filled_well_column_leaves_no_reserve():
    """These two boards have no reserve, and the field beside the well is why.

    An I dropped into a well filled to depth 1 or 2 rests on that fill, so the band
    it fills is rows 1-4 or 2-5; eight columns stand six rows high and the ninth is
    empty, so no row of that band is complete and the reserve is zero. That is a
    statement about these boards and not about occupied well columns in general:
    ``well_reserve`` measures the rows above the column's topmost filled cell, so a
    well filled low down still holds a reserve when the field below the band is
    complete, and ``objective_mechanism.reserve_with_an_occupied_well`` derives such
    a board from a controller-executable sequence (reserve 1 with the well column
    occupied).
    """
    columns = columns_of(stacked([6] * 8 + [0, 1]))
    assert well_reserve(columns) == 0
    assert well_reserve(columns_of(stacked([6] * 8 + [0, 2]))) == 0


def test_holds_well_is_bounded_by_the_stack_budget_and_the_drought():
    """Both bounds end the build, and the budget reads the whole stack."""
    assert holds_well(0, 0)
    assert holds_well(DROUGHT_BOUND - 1, HEIGHT_BUDGET - 1)
    assert not holds_well(DROUGHT_BOUND, 0)
    assert not holds_well(0, HEIGHT_BUDGET)
    assert initial_phase(0, columns_of(EMPTY_GRID)) == BUILD
    assert initial_phase(DROUGHT_BOUND, columns_of(EMPTY_GRID)) == SPEND
    # A tall well column is still stack height: the budget is not only the field.
    tall_well = stacked([1] * (WIDTH - 1) + [HEIGHT_BUDGET])
    assert initial_phase(0, columns_of(tall_well)) == SPEND


def test_next_drought_restarts_when_the_preview_is_an_i():
    assert next_drought(4, "I") == 0
    assert next_drought(4, "T") == 5


@pytest.mark.parametrize("drought,next_piece,height,phase", [
    # Both of holds_well's conditions decide the preview's phase: a preview that is
    # an I resets the drought, so it keeps building only while the settled stack is
    # under the budget -- the case a disjunction of the two conditions gets wrong --
    # and a preview that is not an I builds only while both still hold.
    (0, "I", 0, BUILD),
    (0, "I", HEIGHT_BUDGET - 1, BUILD),
    (0, "I", HEIGHT_BUDGET, SPEND),
    (0, "I", HEIGHT_BUDGET + 4, SPEND),
    (0, "T", 0, BUILD),
    (DROUGHT_BOUND - 2, "T", 0, BUILD),
    (DROUGHT_BOUND - 1, "T", 0, SPEND),
    (0, "T", HEIGHT_BUDGET, SPEND),
])
def test_the_preview_phase_is_both_of_holds_well_conditions(
    drought, next_piece, height, phase
):
    """The preview's phase is ``initial_phase`` on the board and the advanced drought.

    The criterion the declared objective is judged against requires the objective's
    own declaration to describe the function that produced the results. The module
    docstring said the preview is scored in ``BUILD`` when it is an I *or* while the
    stack is under the budget, which is a disjunction of ``holds_well``'s two
    conditions and is false about an I preview at or above the budget: the settled
    stack's height closes the build whatever the preview is, so that board is
    scored in ``SPEND``. This derives each case from the code and requires the
    docstring to state both conditions rather than either.
    """
    settled = columns_of(stacked([0] * (WIDTH - 1) + [height]))
    assert stack_height(settled) == height
    advanced = next_drought(drought, next_piece)
    assert holds_well(advanced, height) is (phase == BUILD)
    assert initial_phase(advanced, settled) == phase

    documented = " ".join(wellplan_module.__doc__.split())
    assert "or while the settled stack" not in documented, (
        "the module docstring still declares the preview's phase as a disjunction of "
        "holds_well's conditions, which is false at or above the height budget"
    )
    assert "the settled stack is still under the budget" in documented, (
        "the module docstring does not state the budget condition the preview's phase "
        "is built from"
    )


def test_build_value_is_the_declared_terms_and_the_budget():
    """The build value of a constructed board is pinned term by term.

    Nine columns filled to four with the well open: no field holes, no
    bumpiness, an aggregate height of 36, a maximum of 4, a four-row reserve and
    no overflow, so ``-0.5*36 - 1.0*4 + 6.0*4`` is 2. A short field column costs
    the reserve a row and the bumpiness step, and a stack over the budget is
    charged per row beyond it.
    """
    assert plan_value(BUILD, 0, columns_of(EMPTY_GRID)) == 0.0
    assert plan_value(BUILD, 0, columns_of(open_well(4))) == 2.0
    assert plan_value(BUILD, 0, columns_of(stacked([4] * 8 + [3, 0]))) == -4.0
    assert plan_value(BUILD, 0, columns_of(open_well(HEIGHT_BUDGET))) == -20.0
    assert plan_value(BUILD, 0, columns_of(open_well(HEIGHT_BUDGET + 2))) == -35.0
    assert plan_value(BUILD, 0, columns_of(open_well(1))) == 0.5


def test_spend_value_is_the_frozen_flat_board_score():
    """The abandon scores the board Experiment 002's lookahead scores."""
    for heights, lines in ((([0] * 9 + [0]), 0), ([4] * 8 + [3, 0], 2), ([0] * 10, 4)):
        columns = columns_of(stacked(heights))
        assert plan_value(SPEND, lines, columns) == feature_score(
            column_features(columns), lines)


def test_plan_choice_takes_the_four_line_clear_when_the_i_is_in_play():
    """The I is spent on the well, and the clear is the Tetris, not a single."""
    grid = open_well(RESERVE_CAP)
    choice = choose(grid, "I", "O")
    assert choice is not None
    assert (choice.orientation, choice.x, choice.lines_cleared) == (1, WELL_COLUMN, 4)


def test_plan_choice_keeps_the_reserve_rather_than_spending_it_on_a_single():
    """The build phase will not break the reserve for a premature clear.

    Nine columns two rows high with the well open: a T dropped into the well
    completes two rows and clears a double, which the plan charges, or it can be
    laid on the field and leave the reserve — and the reserve it leaves is worth
    more than the clear. The same board with the drought spent is the abandon:
    the frozen flat score takes the clear, which is how the plan gives the well
    back when the I is late.
    """
    grid = open_well(2)
    building = choose(grid, "T", "O", drought=0)
    assert (building.orientation, building.x, building.lines_cleared) == (2, 1, 0)
    abandoned = choose(grid, "T", "O", drought=DROUGHT_BOUND)
    assert abandoned.lines_cleared == 1
    assert abandoned.x == WELL_COLUMN


def test_plan_choice_spends_the_well_at_the_stack_budget_too():
    """The height bound is the other abandon trigger, not only the drought.

    The same board plays differently either side of the budget. At two rows the
    plan is building, and an S is laid on the field to leave the reserve open; at
    the budget the plan has abandoned the well, and the frozen flat score takes
    the clear the S can make by dropping into it.
    """
    low = choose(open_well(2), "S", "O")
    assert (low.orientation, low.x, low.lines_cleared) == (0, 1, 0)
    capped = choose(open_well(HEIGHT_BUDGET), "S", "O")
    assert capped.lines_cleared == 1


def test_plan_choice_is_deterministic_and_consults_the_preview():
    """The same board and preview choose the same placement, and the preview decides.

    Two previews the plan can place differently give two different placements on
    the same board: an I in the preview is the piece that completes the reserve,
    so the plan reads it and drops the current S to the well side instead of
    laying it where the I would have gone.
    """
    grid = stacked([2] * 8 + [0, 0])
    first = choose(grid, "S", "O")
    repeat = choose(grid, "S", "O")
    assert (repeat.orientation, repeat.x) == (first.orientation, first.x)
    with_i = choose(grid, "S", "I")
    assert (with_i.orientation, with_i.x) != (first.orientation, first.x)


def test_plan_choice_falls_back_when_no_placement_is_admissible():
    rows = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            rows[row][column] = 1
    assert choose(grid_of(rows), "O", "T") is None


def test_create_agent_builds_the_plan_agent_on_the_shared_controller():
    """The new agent is a placement agent, so it executes plans like the others.

    It is built by the module that owns its objective, and the runner's registry
    is what a suite is validated against. The shared factory's own module is left
    untouched and still knows only its own agents: its source is what every
    record it wrote covers, so an agent added there would invalidate the records
    of the agents it already dispatches.
    """
    agent = build_agent("tetris_plan", 2)
    assert isinstance(agent, PlanAgent)
    assert isinstance(agent, PlacementAgent)
    assert isinstance(runner.build_agent(PLAN_AGENT, 2), PlanAgent)
    assert PLAN_AGENT in runner.AGENT_NAMES
    assert PLAN_AGENT not in agents_module.AGENT_NAMES
    with pytest.raises(ValueError, match="unknown agent"):
        build_agent("tetris", 2)
    with pytest.raises(ValueError, match="unknown agent"):
        runner.build_agent("nonesuch", 2)


class PlanState:
    """The observation fields the controller and the objective read."""

    def __init__(self, grid, piece: str, next_piece: str, piece_count: int = 2):
        self.piece_count = piece_count
        self.current_piece = piece
        self.next_piece = next_piece
        self.orientation = 0
        self.x = 5
        self.phase = "active"
        self.terminal = False
        self.board = grid[HIDDEN_ROWS:]
        self.hidden_rows = grid[:HIDDEN_ROWS]
        self.level = 18
        self.lines = 0
        self.start_level = 18
        self.first_delay_remaining = 0
        self.ruleset = "classic_ntsc_extended"
        self.mode = "endless"


def test_plan_agent_emits_the_shared_controller_masks_for_its_choice():
    """The agent steers the profile the shared plan model computes, not its own."""
    grid = open_well(RESERVE_CAP)
    agent = build_agent("tetris_plan", 2)
    state = PlanState(grid, "I", "O")
    chosen = plan_choice(grid, "I", "O", drought=agent._drought, level=18, lines=0,
                         start_level=18, first_delay_remaining=0,
                         ruleset="classic_ntsc_extended", mode="endless")
    expected = []
    release = False
    orientation, x = state.orientation, state.x
    for _ in range(64):
        mask, release = pathaware.plan_mask(orientation, x, (chosen.orientation, chosen.x),
                                            release, 2)
        expected.append(mask)
        if mask == DOWN:
            break
    emitted = [agent.act(state) for _ in expected]
    assert emitted == expected
    assert emitted[:2] == [pathaware.ROTATE_CW, 0]

    # Nothing admissible: the shared fallback holds Down where the piece spawned.
    blocked = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            blocked[row][column] = 1
    stuck = PlanState(grid_of(blocked), "O", "T", piece_count=7)
    agent.reset()
    assert agent.act(stuck) == DOWN


def test_plan_agent_counts_the_pieces_it_is_shown_and_restarts_on_an_i(monkeypatch):
    """The drought the plan reads is the agent's own count of visible pieces.

    The count is the plan's only memory, so it is driven here piece by piece: it
    grows for every piece whose current and preview are not an I, restarts when
    either is, and is handed to the objective unchanged.
    """
    seen: list[int] = []
    real = wellplan_module.plan_choice

    def recording(grid, piece, next_piece, *, drought, **rest):
        seen.append(drought)
        return real(grid, piece, next_piece, drought=drought, **rest)

    monkeypatch.setattr(wellplan_module, "plan_choice", recording)
    agent = build_agent("tetris_plan", 0)
    grid = open_well(1)
    for index, (piece, preview) in enumerate(
        [("T", "O"), ("S", "Z"), ("L", "I"), ("J", "T"), ("I", "O")]
    ):
        agent.act(PlanState(grid, piece, preview, piece_count=index + 1))
    # T/O and S/Z count up, the L with an I preview restarts, the J/T counts one,
    # and the I itself restarts.
    assert seen == [1, 2, 0, 1, 0]


def test_the_plan_spends_at_the_drought_bound_the_prose_states(monkeypatch):
    """The phase turns over on the bound-th no-I observation, and the prose says so.

    ``holds_well`` is ``drought < DROUGHT_BOUND`` and the agent advances its own
    count once per spawned piece, so the count reaches the bound on the bound-th
    consecutive observation without a visible I and the phase *there* is already
    ``SPEND``. The boundary is therefore read from the code here rather than
    paraphrased beside it: the agent is driven through consecutive no-I
    observations, the count it hands the objective and the phase that count puts
    the board in are recorded, and the transition is required at exactly the
    observation whose count equals the bound. The retained rationale and the
    module docstring have to describe that same boundary -- the sentence that said
    the plan spends only *past* the bound was one observation later than the code
    -- so a docstring or a rationale row that drifts from the predicate is
    reported here instead of read as a description of it.
    """
    seen: list[int] = []
    real = wellplan_module.plan_choice

    def recording(grid, piece, next_piece, *, drought, **rest):
        seen.append(drought)
        return real(grid, piece, next_piece, drought=drought, **rest)

    monkeypatch.setattr(wellplan_module, "plan_choice", recording)
    agent = build_agent(PLAN_AGENT, 0)
    grid = open_well(1)
    for index in range(DROUGHT_BOUND + 2):
        agent.act(PlanState(grid, "T", "O", piece_count=index + 1))

    assert seen == list(range(1, DROUGHT_BOUND + 3))
    phases = [initial_phase(drought, columns_of(grid)) for drought in seen]
    assert phases[:DROUGHT_BOUND - 1] == [BUILD] * (DROUGHT_BOUND - 1)
    assert phases[DROUGHT_BOUND - 1] == SPEND
    assert phases[DROUGHT_BOUND - 1:] == [SPEND] * len(phases[DROUGHT_BOUND - 1:])
    # The observation the transition lands on is the bound itself, not one later.
    assert seen[phases.index(SPEND)] == DROUGHT_BOUND

    documented = " ".join(wellplan_module.__doc__.split())
    assert "bound-th" in documented, (
        "the module docstring does not state the boundary the predicate implements"
    )
    assert "past that bound" not in documented, (
        "the module docstring says the plan spends only past the bound, which is one "
        "observation later than holds_well"
    )
    section = " ".join(declared_objective_section().split())
    assert "on the bound-th spawned piece without a visible I" in section, (
        "the predeclared rationale row does not state the boundary the predicate "
        "implements"
    )
    assert "past the bound" not in section, (
        "the predeclared rationale row says the plan spends only past the bound, which "
        "is one observation later than holds_well"
    )


def test_the_drought_counter_counts_spawned_pieces_and_the_prose_says_so(monkeypatch):
    """The drought is a per-spawn count, and every restatement uses that unit.

    ``PlanAgent._choose`` advances the counter once per spawn observation, from the
    piece it places and the visible preview, so after ``k`` consecutive
    observations without a visible I the counter is ``k`` while ``k + 1`` piece
    instances have been shown -- the preview of one observation is the current
    piece of the next. The bound is therefore *not* the number of pieces the plan
    has been shown: it is reached on the bound-th observation, by which time one
    more piece instance has been exposed than the counter reports. The arithmetic
    is read from the code rather than from the prose beside it: the agent is driven
    through consecutive no-I observations, the count it hands the objective is
    recorded, the observation the phase first turns ``SPEND`` on is required to be
    the bound-th, and each retained restatement is required to count in the
    counter's own unit -- spawned pieces -- rather than the pieces the plan has
    been shown, which is the off-by-one description this derives against.
    """
    seen: list[int] = []
    real = wellplan_module.plan_choice

    def recording(grid, piece, next_piece, *, drought, **rest):
        seen.append(drought)
        return real(grid, piece, next_piece, drought=drought, **rest)

    monkeypatch.setattr(wellplan_module, "plan_choice", recording)
    agent = build_agent(PLAN_AGENT, 0)
    grid = open_well(1)
    # One observation per piece placed; the i-th shows the i-th piece as current
    # and the (i + 1)-th as the preview, so it exposes i + 1 piece instances.
    pieces = ["T", "S", "L", "J", "O", "Z"] * 3
    observations = DROUGHT_BOUND + 2
    for index in range(observations):
        agent.act(PlanState(grid, pieces[index], pieces[index + 1], piece_count=index + 1))

    # One increment per spawn observation: the counter is a per-spawn count.
    assert seen == list(range(1, observations + 1))
    phases = [initial_phase(drought, columns_of(grid)) for drought in seen]
    first_spend = phases.index(SPEND)
    assert seen[first_spend] == DROUGHT_BOUND
    # The bound-th observation has shown one more piece instance than the counter
    # reports -- the count is spawn observations, not distinct pieces shown.
    exposures = first_spend + 2
    assert exposures == DROUGHT_BOUND + 1
    assert exposures == seen[first_spend] + 1

    source = Path(wellplan_module.__file__).read_text(encoding="utf-8").splitlines()
    constant = next(i for i, line in enumerate(source)
                    if line.startswith("DROUGHT_BOUND = "))
    comment_start = constant
    while comment_start and source[comment_start - 1].startswith("#"):
        comment_start -= 1
    comment = " ".join(line.lstrip("#").strip() for line in source[comment_start:constant])
    row = next(line for line in declared_objective_section().splitlines()
               if line.startswith("| `drought_bound` |"))
    sites = {
        "module docstring": " ".join(wellplan_module.__doc__.split()),
        "DROUGHT_BOUND comment": " ".join(comment.split()),
        "holds_well docstring": " ".join(holds_well.__doc__.split()),
        "PlanAgent docstring": " ".join(PlanAgent.__doc__.split()),
        "predeclared rationale": " ".join(declared_objective_section().split()),
        "drought_bound row": " ".join(row.split()),
    }
    for where, text in sites.items():
        assert "spawned piece" in text, (
            f"{where} does not count the drought in the per-spawn unit _choose "
            "implements; the counter advances once per spawned piece"
        )
        for stale in ("shown piece", "pieces it has been shown", "pieces it was shown"):
            assert stale not in text, (
                f"{where} counts the pieces the plan has been shown, which is one more "
                f"than the per-spawn counter ({seen[first_spend]} spawn observations, "
                f"{exposures} piece instances at the bound)"
            )
    # The sites that state the boundary state it in the same per-spawn unit.
    for where in ("module docstring", "DROUGHT_BOUND comment", "holds_well docstring",
                  "predeclared rationale", "drought_bound row"):
        assert "bound-th" in sites[where], (
            f"{where} does not state the bound-th spawned piece the predicate turns on"
        )


def test_the_plan_reads_the_engine_piece_counter_through_the_inherited_act(monkeypatch):
    """The rationale's account of what the plan reads is derived from the controller.

    The predeclared rationale used to say the plan reads "no engine counter".
    ``PlanAgent`` overrides only ``_choose``, and the ``act`` it inherits from
    ``PlacementAgent`` decides that a new piece spawned by comparing
    ``state.piece_count`` with the count it last saw -- so the plan does read the
    engine's piece counter, which is the engine's visible per-piece observation
    rather than hidden information. The claim is derived here instead of restated:
    the plan is shown to run the inherited controller, the controller is shown to
    call the choice hook only when the counter changes, and the retained rationale
    is required to say so and not to deny it.
    """
    assert "act" not in PlanAgent.__dict__, (
        "the plan defines its own act, so the rationale's account of the inherited "
        "controller is stale"
    )
    assert PlanAgent.act is PlacementAgent.act

    calls: list[int] = []
    agent = build_agent(PLAN_AGENT, 0)
    original = agent._choose

    def recording(state, grid):
        calls.append(state.piece_count)
        return original(state, grid)

    monkeypatch.setattr(agent, "_choose", recording)
    grid = open_well(1)
    for count in (1, 1, 1, 2, 3, 3):
        agent.act(PlanState(grid, "T", "O", piece_count=count))
    # The controller chooses once per spawned piece, keyed on the engine's counter.
    assert calls == [1, 2, 3]

    section = " ".join(declared_objective_section().split())
    assert "no engine counter" not in section, (
        "the predeclared rationale denies a read the inherited controller makes"
    )
    assert "piece counter" in section, (
        "the predeclared rationale does not state that the plan reads the engine's "
        "piece counter"
    )


def test_overflow_is_a_penalty_inside_the_value_not_a_dominance_rule():
    """An over-budget placement can still outscore one that stays under the budget.

    ``plan_value`` adds ``overflow`` per row past the budget *inside* the summed
    value, so the charge is one term among the clear and field terms and can be
    outweighed. The case is derived from the code rather than asserted: on the
    seven-row field with an open well, a J has reachable placements that settle
    over the budget and one that clears a row and stays under it, and the
    over-budget placement's own ``plan_value`` is the higher of the two -- so the
    sentence that said it "loses to one that does not" would be false about the
    objective that produced the results. ``plan_choice`` selects the over-budget
    placement on the same board, which is the composition the results came from.
    """
    grid = open_well(7)
    columns = columns_of(grid)
    assert stack_height(columns) == 7 < HEIGHT_BUDGET
    reachable = pathaware._reachable(columns, "J", pathaware.gravity_period(18), 0)

    def value(pair):
        placement, settled = pair
        return plan_value(BUILD, placement.lines_cleared, settled)

    over = [pair for pair in reachable if stack_height(pair[1]) > HEIGHT_BUDGET]
    under = [pair for pair in reachable if stack_height(pair[1]) <= HEIGHT_BUDGET]
    assert over and under, "the derived counterexample needs both kinds of candidate"
    best_over = max(over, key=value)
    best_under = max(under, key=value)
    assert stack_height(best_over[1]) > HEIGHT_BUDGET
    assert stack_height(best_under[1]) <= HEIGHT_BUDGET
    assert value(best_over) > value(best_under)

    chosen = choose(grid, "J", "O")
    assert (chosen.orientation, chosen.x) == (best_over[0].orientation, best_over[0].x)
    settled_chosen = next(settled for placement, settled in reachable
                          if (placement.orientation, placement.x)
                          == (chosen.orientation, chosen.x))
    assert stack_height(settled_chosen) > HEIGHT_BUDGET

    documented = " ".join(wellplan_module.__doc__.split())
    assert "loses to one that does not" not in documented, (
        "the module docstring claims the overflow term dominates the placement "
        "comparison, which the derived counterexample contradicts"
    )
    assert "loses value" in documented, (
        "the module docstring does not describe the overflow term as a penalty inside "
        "the summed value"
    )
