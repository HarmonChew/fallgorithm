from __future__ import annotations

from dataclasses import dataclass
import random

from block_stack_ai.agents import DOWN, LEFT, ROTATE_CW, GreedyPolicy, PlacementAgent, RandomPolicy
from block_stack_ai.heuristic import (
    HEIGHT,
    WIDTH,
    BoardFeatures,
    Placement,
    board_features,
    board_grid,
    enumerate_placements,
    fits,
    settle,
)

EMPTY_HIDDEN = ((0,) * WIDTH,) * 2
EMPTY_ROWS = tuple((0,) * WIDTH for _ in range(HEIGHT))
EMPTY_GRID = board_grid(EMPTY_ROWS, EMPTY_HIDDEN)

# Counted by hand from the mirrored geometry: one placement per column an
# orientation fits in on the 10-wide field (the flat I spans four columns, the
# vertical I and the two long J/L/T orientations span one or two).
EXPECTED_PLACEMENTS = {"I": 17, "J": 34, "L": 34, "O": 9, "S": 17, "T": 34, "Z": 17}


def visible_grid(rows: tuple[tuple[int, ...], ...]):
    return board_grid(rows, EMPTY_HIDDEN)


def tetris_well_grid():
    """Rows 16-19 filled everywhere but column 0, so only a vertical I can clear."""
    rows = [list(row) for row in EMPTY_ROWS]
    for row in range(16, HEIGHT):
        for column in range(1, WIDTH):
            rows[row][column] = 1
    return visible_grid(tuple(tuple(row) for row in rows))


def test_features_report_holes_heights_and_bumpiness():
    assert board_features(EMPTY_GRID) == BoardFeatures(0, 0, 0, 0)

    holed = [list(row) for row in EMPTY_ROWS]
    holed[19][0] = 1
    holed[17][0] = 1
    # Column 0 holds rows 17-19 with row 18 empty: height 3, one hole below the top.
    assert board_features(visible_grid(tuple(tuple(row) for row in holed))) == BoardFeatures(1, 3, 3, 3)

    staircase = [list(row) for row in EMPTY_ROWS]
    staircase[18][0] = staircase[19][0] = 1
    staircase[19][1] = 1
    assert board_features(visible_grid(tuple(tuple(row) for row in staircase))) == BoardFeatures(0, 3, 2, 2)


def test_enumeration_covers_every_unique_rotation_and_legal_column():
    for piece, expected in EXPECTED_PLACEMENTS.items():
        placements = enumerate_placements(EMPTY_GRID, piece)
        order = [(placement.orientation, placement.x) for placement in placements]
        assert len(placements) == expected
        assert len(set(order)) == expected
        assert order == sorted(order)  # canonical: orientation, then column
        for placement in placements:
            assert placement.piece == piece
            assert placement.lines_cleared == 0
            assert fits(EMPTY_GRID, piece, placement.orientation, placement.x, placement.y)
            assert not fits(EMPTY_GRID, piece, placement.orientation, placement.x, placement.y + 1)


def test_enumeration_lands_on_top_of_the_existing_stack():
    rows = [list(row) for row in EMPTY_ROWS]
    for row in range(14, HEIGHT):
        rows[row][4] = 1
    grid = visible_grid(tuple(tuple(row) for row in rows))

    landing = [placement for placement in enumerate_placements(grid, "O") if placement.x == 4]
    assert [placement.y for placement in landing] == [12]
    assert all(placement.lines_cleared == 0 for placement in landing)


def test_settle_keeps_hidden_rows_in_place_when_a_visible_line_clears():
    """The engine compacts the visible board alone, so hidden minos never shift."""
    hidden = ((0,) * WIDTH, (1, 1) + (0,) * (WIDTH - 2))
    rows = [list(row) for row in EMPTY_ROWS]
    for column in range(2, WIDTH):
        rows[0][column] = 1  # the O completes this row from columns 0-1
    rows[1][0] = rows[1][1] = 1  # support, so the O rests at y = -1

    settled, cleared = settle(board_grid(tuple(tuple(row) for row in rows), hidden), "O", 0, 1, -1)

    expected = [list(row) for row in EMPTY_ROWS]
    expected[1][0] = expected[1][1] = 1  # the row below the clear keeps its place
    assert cleared == 1
    assert settled == board_grid(tuple(tuple(row) for row in expected), hidden)


def test_settle_shifts_visible_rows_above_a_cleared_row_downward():
    rows = [list(row) for row in EMPTY_ROWS]
    for column in range(2, WIDTH):
        rows[10][column] = 1  # the O completes this row from columns 0-1
    rows[9][5] = 1  # above the cleared row, so it moves down one
    rows[11][9] = 1  # below the cleared row, so it keeps its place

    settled, cleared = settle(visible_grid(tuple(tuple(row) for row in rows)), "O", 0, 1, 9)

    expected = [list(row) for row in EMPTY_ROWS]
    expected[10] = [1, 1, 0, 0, 0, 1, 0, 0, 0, 0]  # old visible row 9, one row lower
    expected[11][9] = 1  # old visible row 11, unmoved
    assert cleared == 1
    assert settled == visible_grid(tuple(tuple(row) for row in expected))


def test_greedy_clears_a_tetris_well_instead_of_dropping_flat():
    best = GreedyPolicy().choose(enumerate_placements(tetris_well_grid(), "I"))
    assert best is not None
    assert (best.orientation, best.x, best.y, best.lines_cleared) == (1, 0, 18, 4)

    flat = GreedyPolicy().choose(
        [placement for placement in enumerate_placements(tetris_well_grid(), "I")
         if placement.orientation == 0]
    )
    assert flat.lines_cleared == 0
    assert best.score > flat.score


def test_greedy_takes_the_first_of_equal_scores():
    placements = (
        Placement("O", 0, 1, 18, 0, -6.0),
        Placement("O", 0, 2, 18, 0, -6.0),
        Placement("O", 0, 3, 18, 0, -20.0),
    )
    assert GreedyPolicy().choose(placements) is placements[0]
    assert GreedyPolicy().choose(()) is None

    # Wall-adjacent O placements on an empty field are the least bumpy, and the
    # left wall comes first, so enumeration order breaks the tie.
    tied = enumerate_placements(EMPTY_GRID, "O")
    best = GreedyPolicy().choose(tied)
    assert best == tied[0]
    assert (best.orientation, best.x) == (0, 1)
    assert tied[-1].score == best.score


def test_random_policy_is_seeded_and_stays_inside_the_placements():
    placements = enumerate_placements(EMPTY_GRID, "T")
    first = RandomPolicy(random.Random(3))
    second = RandomPolicy(random.Random(3))
    picks = [first.choose(placements) for _ in range(8)]
    assert picks == [second.choose(placements) for _ in range(8)]
    assert all(pick in placements for pick in picks)
    assert RandomPolicy(random.Random(1)).choose(()) is None


@dataclass
class FakeState:
    piece_count: int = 1
    current_piece: str = "O"
    orientation: int = 0
    x: int = 0
    phase: str = "active"
    terminal: bool = False
    board: object = EMPTY_ROWS
    hidden_rows: object = EMPTY_HIDDEN


def test_placement_agent_presses_once_per_release_frame_and_drops_at_the_target():
    agent = PlacementAgent(GreedyPolicy())
    state = FakeState(current_piece="O", orientation=0, x=4)
    assert agent.act(state) == LEFT
    assert agent.act(state) == 0  # release frame, so the next left press is a new edge
    state.x = 3
    assert agent.act(state) == LEFT
    assert agent.act(state) == 0
    state.x = 1  # the first O placement on an empty field
    assert agent.act(state) == DOWN
    assert agent.act(state) == DOWN
    state.phase = "entry_delay"
    assert agent.act(state) == 0


def test_placement_agent_rotates_toward_the_chosen_orientation():
    agent = PlacementAgent(GreedyPolicy())
    state = FakeState(current_piece="I", orientation=0, x=5, board=tetris_well_grid())
    assert agent.act(state) == ROTATE_CW  # I rotates either way in one press
    assert agent.act(state) == 0
    state.orientation = 1
    assert agent.act(state) == LEFT
    assert agent.act(state) == 0
    state.x = 0
    assert agent.act(state) == DOWN
