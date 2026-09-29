"""Unit tests for the Tetris-oriented objective and the new agent's decisions.

Every test here uses constructed boards and the pure Python model, so the
registered unit suite stays fast; the native side of the contract is the
four-row clear in ``test_integration.py``. The objective's values are pinned
exactly, so the declared weights cannot drift unnoticed.
"""

from __future__ import annotations

from block_stack_ai.agents import DOWN, PlacementAgent, TetrisAgent, create_agent
from block_stack_ai.heuristic import HEIGHT, HIDDEN_ROWS, WIDTH, board_grid, enumerate_placements
from block_stack_ai import pathaware
from block_stack_ai.pathaware import (
    column_features,
    grid_columns,
    lookahead_choice,
    reachable_placements,
    settle_columns,
)
from block_stack_ai.tetris import (
    TETRIS_WEIGHTS,
    WELL_DEPTH_CAP,
    clear_term,
    column_heights,
    tetris_choice,
    tetris_value,
    well_depth,
    weights_record,
)

EMPTY_HIDDEN = ((0,) * WIDTH,) * 2
EMPTY_ROWS = tuple((0,) * WIDTH for _ in range(HEIGHT))
EMPTY_GRID = board_grid(EMPTY_ROWS, EMPTY_HIDDEN)


def grid_of(rows: list[list[int]], hidden=EMPTY_HIDDEN):
    return board_grid(tuple(tuple(row) for row in rows), hidden)


def blank_rows() -> list[list[int]]:
    return [[0] * WIDTH for _ in range(HEIGHT)]


def well_grid() -> tuple[tuple[int, ...], ...]:
    """Four full rows under 9 of the 10 columns: a 4-deep well in column 9.

    The classic Tetris setup. Columns 0-8 are four rows high and column 9 is
    empty, so a vertical I dropped into column 9 completes four rows at once,
    while a J or L can fill only three of them and clear a premature triple.
    """
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        for column in range(WIDTH - 1):
            rows[row][column] = 1
    return grid_of(rows)


def flat_grid() -> tuple[tuple[int, ...], ...]:
    """The same four rows filled across all ten columns: the well is gone."""
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        for column in range(WIDTH):
            rows[row][column] = 1
    return grid_of(rows)


def columns_of(grid) -> tuple[int, ...]:
    return grid_columns(grid)


def choose(grid, piece: str, next_piece: str, *, first_delay: int = 0):
    placement = tetris_choice(grid, piece, next_piece, level=18, lines=0, start_level=18,
                              first_delay_remaining=first_delay,
                              ruleset="classic_ntsc_extended", mode="endless")
    assert placement is not None
    return placement


def test_declared_weights_are_the_published_ones():
    """The objective is declared once, and the record names exactly those values."""
    assert TETRIS_WEIGHTS == {
        "tetrises": 8.0,
        "premature_clear": -1.0,
        "holes": -1.0,
        "aggregate_height": -0.5,
        "bumpiness": -0.5,
        "max_height": -1.0,
        "well_depth": 1.0,
    }
    assert WELL_DEPTH_CAP == 4
    assert weights_record() == {
        **TETRIS_WEIGHTS, "well_depth_cap": 4,
        "tie_break": "first highest-valued placement in canonical enumeration order: "
                     "orientation ascending, then column ascending",
    }


def test_clear_term_rewards_only_the_four_line_clear():
    assert clear_term(4) == 8.0
    assert clear_term(0) == 0.0
    assert clear_term(1) == -3.0
    assert clear_term(2) == -2.0
    assert clear_term(3) == -1.0
    # A Tetris is worth more than the largest penalty any single clear can carry.
    assert clear_term(4) > 0 > clear_term(3) > clear_term(2) > clear_term(1)


def test_a_tetris_is_worth_its_declared_value_on_an_empty_board():
    assert tetris_value(4, columns_of(EMPTY_GRID)) == 8.0
    assert tetris_value(0, columns_of(EMPTY_GRID)) == 0.0


def test_well_depth_reads_one_column_slots():
    """A well is a column lower than its shallower neighbour, at the edges too."""
    assert well_depth(columns_of(EMPTY_GRID)) == 0
    assert well_depth(columns_of(flat_grid())) == 0
    # The well grid's column 9 is four rows below its only neighbour.
    assert well_depth(columns_of(well_grid())) == 4

    rows = blank_rows()
    for row in range(HEIGHT - 2, HEIGHT):
        for column in range(WIDTH):
            if column != 4:
                rows[row][column] = 1
    assert well_depth(columns_of(grid_of(rows))) == 2

    # A column beside one tall wall and one flat neighbour is not a well: the
    # shallower neighbour caps the depth at zero.
    rows = blank_rows()
    for row in range(HEIGHT - 6, HEIGHT):
        rows[row][3] = 1
    assert well_depth(columns_of(grid_of(rows))) == 0


def test_column_heights_match_the_frozen_features_on_random_boards():
    """The height rule is the one ``column_features`` reads, cell for cell."""
    for grid in (EMPTY_GRID, well_grid(), flat_grid()):
        heights = column_heights(columns_of(grid))
        features = column_features(columns_of(grid))
        assert len(heights) == WIDTH
        assert sum(heights) == features.aggregate_height
        assert max(heights) == features.max_height


def test_tetris_choice_refuses_a_premature_clear_and_keeps_the_well():
    """With a four-deep well, the agent does not spend it on a one-line clear.

    The board's only hole is the well. A T can drop into it for a single, which
    the frozen flat-board objective accepts, or go elsewhere and leave the well
    for a vertical I. The declared objective charges the single
    ``premature_clear`` and rewards the surviving well, so the chosen placement
    clears nothing and the well survives at full depth; the frozen ``lookahead``
    and ``greedy`` agents, whose objective has neither term, clear the single and
    leave a one-row-deep well.
    """
    grid = well_grid()
    singles = [
        placement for placement in reachable_placements(grid, "T", level=18,
                                                        first_delay_remaining=0)
        if placement.lines_cleared == 1
    ]
    assert singles, "the board must admit the premature single for this test to bite"

    choice = choose(grid, "T", "O")
    settled, cleared = settle_columns(columns_of(grid), "T", choice.orientation,
                                      choice.x, choice.y)
    assert choice.lines_cleared == cleared == 0
    assert well_depth(settled) == 4

    frozen = lookahead_choice(grid, "T", "O", level=18, lines=0, start_level=18,
                              first_delay_remaining=0, ruleset="classic_ntsc_extended",
                              mode="endless")
    frozen_settled, frozen_cleared = settle_columns(columns_of(grid), "T", frozen.orientation,
                                                    frozen.x, frozen.y)
    assert frozen_cleared == 1 and well_depth(frozen_settled) == 0
    greedy = max(enumerate_placements(grid, "T"), key=lambda placement: placement.score)
    assert greedy.lines_cleared == 1 and (greedy.orientation, greedy.x) == (frozen.orientation,
                                                                           frozen.x)


def test_tetris_choice_takes_the_four_line_clear_when_the_i_is_in_play():
    """The I is spent on the well, and the clear is the Tetris, not a single."""
    grid = well_grid()
    choice = choose(grid, "I", "O")
    assert choice.lines_cleared == 4
    settled, cleared = settle_columns(columns_of(grid), "I", choice.orientation,
                                      choice.x, choice.y)
    assert cleared == 4
    # Four whole rows were cleared, so the visible field is empty afterwards.
    assert settled == (0,) * WIDTH


def setup_grid() -> tuple[tuple[int, ...], ...]:
    """One four-high column at index 8 and an empty column 9: a well to protect.

    The well is the only column pair the objective can see, so the preview piece
    decides where the current piece goes without changing any clear.
    """
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        rows[row][8] = 1
    return grid_of(rows)


def test_tetris_choice_is_deterministic_and_consults_the_preview():
    """The same board and preview choose the same placement, and the preview decides.

    Two previews the agent can place differently give two different placements on
    the setup board — same board, same rules, only the visible next piece
    changes — so the lookahead is genuinely reading it. Five calls are used to
    pin determinism without an RNG.
    """
    grid = setup_grid()
    first = choose(grid, "T", "O")
    assert (first.orientation, first.x, first.y) == (
        choose(grid, "T", "O").orientation, choose(grid, "T", "O").x, choose(grid, "T", "O").y
    )
    with_i = choose(grid, "T", "I")
    assert (with_i.orientation, with_i.x) != (first.orientation, first.x)


def test_tetris_choice_falls_back_when_no_placement_is_admissible():
    rows = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            rows[row][column] = 1
    grid = grid_of(rows)
    assert tetris_choice(grid, "O", "T", level=18, lines=0, start_level=18,
                         first_delay_remaining=0, ruleset="classic_ntsc_extended",
                         mode="endless") is None


def test_create_agent_builds_the_tetris_agent_on_the_shared_controller():
    """The new agent is a placement agent, so it executes plans like the others."""
    agent = create_agent("tetris", 2)
    assert isinstance(agent, TetrisAgent)
    assert isinstance(agent, PlacementAgent)


class TetrisState:
    """The observation fields the controller and the objective read."""

    def __init__(self, grid, piece: str, next_piece: str):
        self.piece_count = 2
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


def test_tetris_agent_emits_the_shared_controller_masks_for_its_choice():
    """The agent steers the profile the shared plan model computes, not its own."""
    grid = well_grid()
    agent = create_agent("tetris", 2)
    state = TetrisState(grid, "I", "O")
    chosen = tetris_choice(grid, "I", "O", level=18, lines=0, start_level=18,
                           first_delay_remaining=0, ruleset="classic_ntsc_extended",
                           mode="endless")
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
    # The first press is a rotation of the spawn state, as the plan model says.
    assert emitted[:2] == [pathaware.ROTATE_CW, 0]

    # Nothing admissible: the shared fallback holds Down where the piece spawned.
    blocked = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            blocked[row][column] = 1
    stuck = TetrisState(grid_of(blocked), "O", "T")
    agent.reset()
    stuck.piece_count = 7
    assert agent.act(stuck) == DOWN
