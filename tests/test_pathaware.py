"""Unit tests for the path-aware reachability model and the lookahead agent.

Every test here uses constructed boards and the pure Python model, so the
registered unit suite stays fast; the native side of the contract is the
whole-set gate in ``test_integration.py``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


from block_stack_ai.agents import DOWN, LEFT, RIGHT, ROTATE_CCW, ROTATE_CW, LookaheadAgent
from block_stack_ai.heuristic import (
    HEIGHT,
    HIDDEN_ROWS,
    WIDTH,
    board_features,
    board_grid,
    enumerate_placements,
    feature_score,
    fits,
    settle,
)
from block_stack_ai import pathaware
from block_stack_ai.pathaware import (
    PlanOutcome,
    column_features,
    fits_at,
    grid_columns,
    level_for_lines,
    lookahead_choice,
    plan_mask,
    reachable_placements,
    settle_columns,
    simulate_plan,
)
from block_stack_ai.pieces import PIECES, cells, orientation_count

EMPTY_HIDDEN = ((0,) * WIDTH,) * 2
EMPTY_ROWS = tuple((0,) * WIDTH for _ in range(HEIGHT))
EMPTY_GRID = board_grid(EMPTY_ROWS, EMPTY_HIDDEN)


def grid_of(rows: list[list[int]], hidden=EMPTY_HIDDEN):
    return board_grid(tuple(tuple(row) for row in rows), hidden)


def blank_rows() -> list[list[int]]:
    return [[0] * WIDTH for _ in range(HEIGHT)]


def right_wall_grid():
    """Visible rows 0 and 1 filled at columns 7-9: a ceiling the piece slides under."""
    rows = blank_rows()
    for row in (0, 1):
        for column in range(7, WIDTH):
            rows[row][column] = 1
    return grid_of(rows)


def fence_grid():
    """Visible rows 2-19 filled at column 3: a wall no plan can cross."""
    rows = blank_rows()
    for row in range(2, HEIGHT):
        rows[row][3] = 1
    return grid_of(rows)


def blocked_spawn_grid():
    """Visible rows 0-2 filled everywhere: no piece fits at the spawn origin."""
    rows = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            rows[row][column] = 1
    return grid_of(rows)


def random_grids(count: int):
    rng = random.Random(20260927)
    grids = [EMPTY_GRID, right_wall_grid(), fence_grid()]
    for _ in range(count):
        hidden = tuple(tuple(1 if rng.random() < 0.15 else 0 for _ in range(WIDTH)) for _ in range(HIDDEN_ROWS))
        rows = [[1 if rng.random() < 0.25 else 0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
        grids.append(grid_of(rows, hidden))
    return grids


def every_aim(piece: str):
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            yield orientation, x


def test_column_masks_match_the_grid_settle_and_features():
    """The bitmask model must be the grid model, cell for cell and feature for feature."""
    for grid in random_grids(12):
        columns = grid_columns(grid)
        assert column_features(columns) == board_features(grid)
        for piece in PIECES:
            for orientation, x in every_aim(piece):
                for y in range(0, 20):
                    if not fits(grid, piece, orientation, x, y):
                        continue
                    settled, cleared = settle(grid, piece, orientation, x, y)
                    masked, masked_cleared = settle_columns(columns, piece, orientation, x, y)
                    assert masked == grid_columns(settled)
                    assert masked_cleared == cleared
                    assert column_features(masked) == board_features(settled)


def occupied_hidden_grid():
    """The engine's hidden-row clear case: visible row 0 clears above the buffer."""
    hidden = ((0,) * WIDTH, (1, 1) + (0,) * (WIDTH - 2))
    rows = blank_rows()
    for column in range(2, WIDTH):
        rows[0][column] = 1  # the O completes visible row 0 from columns 0-1
    rows[1][0] = rows[1][1] = 1  # support, so the O rests at origin row -1
    return grid_of(rows, hidden)


def double_clear_grid():
    """Two full visible rows under an occupied hidden buffer."""
    hidden = ((0,) * WIDTH, tuple(1 if column in (4, 5) else 0 for column in range(WIDTH)))
    rows = blank_rows()
    for column in range(WIDTH):
        if column not in (4, 5):  # the O at x = 5 covers columns 4 and 5
            rows[18][column] = 1
            rows[19][column] = 1
    return grid_of(rows, hidden)


def hidden_rows_of(columns: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple((columns[column] >> row) & 1 for column in range(WIDTH))
                 for row in range(HIDDEN_ROWS))


def test_settle_columns_keeps_the_hidden_buffer_across_a_clear():
    """The bitmask mirror compacts the visible field alone, exactly like the engine.

    ``Game::clear_rows`` rewrites ``state_.board`` and never touches
    ``state_.hidden_rows``, which ``tests/test_heuristic.py`` and
    ``tests/test_integration.py`` verify on the native engine for a single clear
    and a double clear below an occupied buffer. The mirror must do the same:
    with the buffer carried along by the compaction, a clear moves hidden minos
    into the visible field and empties the buffer.
    """
    single = occupied_hidden_grid()
    single_columns = grid_columns(single)
    settled, cleared = settle(single, "O", 0, 1, -1)
    masked, masked_cleared = settle_columns(single_columns, "O", 0, 1, -1)
    assert cleared == masked_cleared == 1
    assert masked == grid_columns(settled)
    assert hidden_rows_of(masked) == single[:HIDDEN_ROWS]

    double = double_clear_grid()
    double_columns = grid_columns(double)
    settled, cleared = settle(double, "O", 0, 5, 18)
    masked, masked_cleared = settle_columns(double_columns, "O", 0, 5, 18)
    assert cleared == masked_cleared == 2
    assert masked == grid_columns(settled)
    assert hidden_rows_of(masked) == double[:HIDDEN_ROWS]
    # The two cleared rows were the whole visible field, so only the buffer is left.
    assert all(masked[column] == (double_columns[column] & 0b11) for column in range(WIDTH))


def test_fits_predicate_matches_the_cell_by_cell_fit_rule():
    """The precomputed piece table must agree with the frozen fit rule."""
    for grid in random_grids(8):
        columns = grid_columns(grid)
        for piece in PIECES:
            for orientation in range(orientation_count(piece)):
                for x in range(-1, WIDTH + 1):
                    entry = pathaware._TABLES[piece][orientation][x + 1]
                    for y in range(0, 22):
                        assert fits_at(entry, columns, y) == fits(grid, piece, orientation, x, y), (
                            piece, orientation, x, y,
                        )


def test_reachable_placements_equal_straight_drops_on_an_unobstructed_board():
    """With nothing in the way the controller executes exactly the straight drops.

    The first-piece delay (96 frames with no gravity attempt) is the cleanest
    case: the piece never descends while it rotates and shifts, so the plan is
    the straight drop the frozen model describes, placement for placement and
    score for score.
    """
    for piece in PIECES:
        assert reachable_placements(EMPTY_GRID, piece, level=18,
                                    first_delay_remaining=96) == enumerate_placements(EMPTY_GRID, piece)


def test_reachable_placements_add_columns_the_straight_drop_rejects():
    """Gravity while shifting reaches columns a drop from the origin cannot enter.

    Visible rows 0 and 1 are filled at columns 7-9, so a drop entering those
    columns at the spawn origin collides immediately and the frozen enumeration
    rejects them. The controller keeps pressing while gravity lowers the piece,
    and once the piece is below those rows the shift succeeds.
    """
    grid = right_wall_grid()
    straight = {(placement.orientation, placement.x, placement.y)
                for placement in enumerate_placements(grid, "O")}
    assert straight == {(0, 1, 18), (0, 2, 18), (0, 3, 18), (0, 4, 18), (0, 5, 18), (0, 6, 18)}

    reachable = {(placement.orientation, placement.x, placement.y)
                 for placement in reachable_placements(grid, "O", level=18, first_delay_remaining=0)}
    assert reachable - straight == {(0, 7, 18), (0, 8, 18), (0, 9, 18)}
    assert straight < reachable


def test_reachable_placements_drop_plans_the_controller_cannot_execute():
    """The lateral path can be blocked even where a straight drop would fit.

    Column 3 is filled from visible row 2 down. The vertical I aiming at column
    3 fits at the origin and the frozen enumeration offers it, but gravity drops
    the piece to row 1 before the shift is attempted, and from there the four
    cells can never clear the wall: the plan locks in column 4 instead.
    """
    grid = fence_grid()
    assert (1, 3, 0) in {(p.orientation, p.x, p.y)
                         for p in enumerate_placements(grid, "I")}
    assert simulate_plan(grid, "I", (1, 3), level=18,
                         first_delay_remaining=0) == PlanOutcome(1, 4, 18, False, False)

    reachable = {(placement.orientation, placement.x)
                 for placement in reachable_placements(grid, "I", level=18, first_delay_remaining=0)}
    assert (1, 3) not in reachable
    assert all(x >= 4 for orientation, x in reachable if orientation == 1)


def overhang_grid():
    """Visible row 0 filled at columns 2-5 over a full wall in column 2.

    A piece spawned at the origin overlaps this ceiling: every piece's
    orientation-0 footprint at x = 5 covers column 4 or 5 in row 0.
    """
    rows = blank_rows()
    for column in range(2, 6):
        rows[0][column] = 1
    for row in range(HEIGHT):
        rows[row][2] = 1
    return grid_of(rows)


def test_reachable_placements_rescue_an_overlapped_spawn():
    """An overlapped spawn is rescued by descending out of the overlap.

    ``Game::spawn`` does not test collision -- an overlapped entry can be
    rescued by an input before a downward collision reaches the lock commit
    path -- so the plan must keep attempting Down from an origin that does not
    fit. ``Game::lock`` rejects the origin only if the piece never moved off it.
    The frozen straight-drop model instead declares the origin blocked and
    offers nothing, which is the omission the reachable set removes.
    """
    grid = overhang_grid()
    for piece in PIECES:
        outcome = simulate_plan(grid, piece, (0, 5), level=18, first_delay_remaining=0)
        assert outcome.reached and not outcome.top_out, (piece, outcome)
        assert (outcome.orientation, outcome.x) == (0, 5)
        reachable = {(placement.orientation, placement.x)
                     for placement in reachable_placements(grid, piece, level=18,
                                                           first_delay_remaining=0)}
        assert (0, 5) in reachable, piece
        assert not any(placement.orientation == 0 and placement.x == 5
                       for placement in enumerate_placements(grid, piece)), piece


def test_plan_mask_rotates_by_the_shorter_way_and_releases_every_press():
    """The controller's whole decision rule, which the simulation shares."""
    # The O has one orientation, so it only ever presses horizontally then Down.
    assert plan_mask(0, 4, (0, 1), False, 1) == (LEFT, True)
    assert plan_mask(0, 4, (0, 1), True, 1) == (0, False)
    assert plan_mask(0, 1, (0, 1), False, 1) == (DOWN, False)
    # Two orientations apart in a four-way piece ties, and the tie takes CW.
    assert plan_mask(0, 5, (2, 5), False, 4) == (ROTATE_CW, True)
    # Three apart is one press the other way.
    assert plan_mask(0, 5, (3, 5), False, 4) == (ROTATE_CCW, True)
    # Two-way pieces rotate either way in one press; CW wins the tie.
    assert plan_mask(0, 5, (1, 5), False, 2) == (ROTATE_CW, True)
    # No chosen placement holds Down where the piece spawned.
    assert plan_mask(0, 5, None, False, 4) == (DOWN, False)


def test_fallback_holds_down_when_no_placement_is_admissible():
    """The documented fallback: nothing admissible means Down where it spawned."""
    grid = blocked_spawn_grid()
    for piece in PIECES:
        assert reachable_placements(grid, piece, level=18, first_delay_remaining=0) == ()
        assert lookahead_choice(grid, piece, "T", level=18, lines=0, start_level=18,
                                first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                mode="endless") is None

    agent = LookaheadAgent()
    state = lookahead_state(grid, "O", "T")
    assert agent.act(state) == DOWN
    assert agent.act(state) == DOWN


def test_lookahead_choice_depends_on_the_preview_piece():
    """The next piece genuinely decides which current placement is chosen.

    On an empty board with the first-piece delay the O can take columns 1 to 9,
    and every one of them leaves the O's own score unchanged apart from its
    reachable set. The next piece decides: with an I preview both wall-adjacent
    placements tie at -7.0, and with an S preview column 9 is uniquely best at
    -8.5. Both were checked against the documented value definition, which the
    test recomputes from the published reachable set and features.
    """
    def values(next_piece: str) -> dict[tuple[int, int], float]:
        out = {}
        for placement in reachable_placements(EMPTY_GRID, "O", level=18, first_delay_remaining=96):
            settled, cleared = settle(EMPTY_GRID, "O", placement.orientation, placement.x,
                                      placement.y)
            nexts = reachable_placements(settled, next_piece, level=level_for_lines(
                cleared, 18), first_delay_remaining=0)
            out[(placement.orientation, placement.x)] = max(p.score for p in nexts)
        return out

    tied = values("I")
    assert tied[(0, 1)] == tied[(0, 9)] == -7.0
    assert max(tied.values()) == -7.0
    assert choose(EMPTY_GRID, "O", "I") == (0, 1)
    assert choose(EMPTY_GRID, "O", "I") == first_maximum(tied)

    unique = values("S")
    assert unique[(0, 1)] == -9.5
    assert unique[(0, 9)] == -8.5 == max(unique.values())
    assert choose(EMPTY_GRID, "O", "S") == (0, 9)
    assert choose(EMPTY_GRID, "O", "S") == first_maximum(unique)

    # The straight-drop greedy choice is column 1 for both previews, so the S
    # episode is a real disagreement between the two agents, not a tie-break.
    greedy = max(enumerate_placements(EMPTY_GRID, "O"), key=lambda placement: placement.score)
    assert (greedy.orientation, greedy.x) == (0, 1)


def dense_stranded_grid():
    """A nearly full board found by a seeded search (``random.Random(1)``, 75% fill).

    Board 442 of that stream. On it the J has exactly three reachable placements:
    ``(3, 6)``, which leaves the Z a real placement, and ``(0, 5)`` and
    ``(3, 5)``, which leave it none. The rejected fallback-scoring rule would
    score the stranded ``(0, 5)`` at ``-155.0``, above the ``-158.0`` the real
    placement is worth, so that rule aims at a placement after which the preview
    piece cannot be placed at all. The assertions below check every one of those
    values, so the board cannot drift into a different case.
    """
    rows = [
        "0101000111", "1001100110", "1101111111", "1001111110", "1111011011",
        "1111110101", "0111110001", "1111010111", "0111111111", "1011111101",
        "0101111011", "1111111011", "0001110111", "1100011100", "1011101101",
        "1111111111", "1111101111", "0111110111", "1111101111", "1111110111",
    ]
    return grid_of([[int(cell) for cell in row] for row in rows])


def test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece():
    """A current placement is worth its best ADMISSIBLE next placement.

    Scoring the next piece's rejected Down fallback instead of ``-inf`` gives the
    stranded ``(0, 5)`` the higher value on this board (its unchanged board scores
    above the real placements the Z is left elsewhere), so the agent would aim at
    a placement after which the preview piece cannot be placed at all.
    """
    grid = dense_stranded_grid()
    columns = grid_columns(grid)
    current = {
        (placement.orientation, placement.x): settled
        for placement, settled in pathaware._reachable(
            columns, "J", pathaware.gravity_period(18), 0)
    }
    assert set(current) == {(0, 5), (3, 5), (3, 6)}
    assert pathaware._reachable(current[(3, 6)], "Z", pathaware.gravity_period(18), 0)
    assert pathaware._reachable(current[(0, 5)], "Z", pathaware.gravity_period(18), 0) == ()
    assert pathaware._reachable(current[(3, 5)], "Z", pathaware.gravity_period(18), 0) == ()
    assert pathaware._best_next_value(current[(3, 5)], "Z", 18) == float("-inf")
    assert pathaware._best_next_value(current[(3, 6)], "Z", 18) == -158.0
    # The rejected rule: the stranded board's own score beats the real placement.
    assert feature_score(column_features(current[(0, 5)]), 0) == -155.0

    choice = lookahead_choice(grid, "J", "Z", level=18, lines=0, start_level=18,
                              first_delay_remaining=0, ruleset="classic_ntsc_extended",
                              mode="endless")
    assert (choice.orientation, choice.x) == (3, 6)


def test_lookahead_choice_is_deterministic():
    """The same board and preview always choose the same placement."""
    grid = right_wall_grid()
    first = choose_with_delay(grid, "T", "I", 0)
    assert first in {(p.orientation, p.x)
                     for p in reachable_placements(grid, "T", level=18, first_delay_remaining=0)}
    assert choose_with_delay(grid, "T", "I", 0) == first
    assert choose_with_delay(grid, "T", "I", 0) == first


def test_level_for_lines_mirrors_the_engine_transitions():
    assert level_for_lines(0, 18) == 18
    assert level_for_lines(129, 18) == 18
    assert level_for_lines(130, 18) == 19
    assert level_for_lines(140, 18) == 20
    assert level_for_lines(9, 0) == 0
    assert level_for_lines(10, 0) == 1
    assert level_for_lines(40, 0) == 4
    assert level_for_lines(300, 18, wrap=True) == (18 + 1 + 17) & 0xFF
    # A challenge game's level never moves, whatever the cleared lines.
    assert level_for_lines(300, 5, challenge=True) == 5


def choose(grid, piece: str, next_piece: str) -> tuple[int, int]:
    return choose_with_delay(grid, piece, next_piece, 96)


def choose_with_delay(grid, piece: str, next_piece: str, first_delay: int) -> tuple[int, int]:
    placement = lookahead_choice(grid, piece, next_piece, level=18, lines=0, start_level=18,
                                 first_delay_remaining=first_delay,
                                 ruleset="classic_ntsc_extended", mode="endless")
    assert placement is not None
    return placement.orientation, placement.x


def first_maximum(values: dict[tuple[int, int], float]) -> tuple[int, int]:
    best = max(values.values())
    return next(key for key in sorted(values) if values[key] == best)


@dataclass
class LookaheadState:
    """The observation fields the lookup and the controller read."""

    piece_count: int = 2
    current_piece: str = "O"
    next_piece: str = "T"
    orientation: int = 0
    x: int = 5
    phase: str = "active"
    terminal: bool = False
    board: object = EMPTY_ROWS
    hidden_rows: object = EMPTY_HIDDEN
    level: int = 18
    lines: int = 0
    start_level: int = 18
    first_delay_remaining: int = 0
    ruleset: str = "classic_ntsc_extended"
    mode: str = "endless"


def lookahead_state(grid, piece: str, next_piece: str) -> LookaheadState:
    rows = grid[HIDDEN_ROWS:]
    hidden = grid[:HIDDEN_ROWS]
    return LookaheadState(current_piece=piece, next_piece=next_piece, board=rows, hidden_rows=hidden)
