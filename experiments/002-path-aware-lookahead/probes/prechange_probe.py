"""Pre-change probes: each new 002 regression's contract, run on the base tree.

Run this file with the recorded base commit's ``src`` on ``PYTHONPATH`` and with
the working directory anywhere; ``evidence.py prechange`` builds that sandbox
with ``git archive HEAD`` and runs every id. Directly:

    sandbox=/tmp/exp002-base
    mkdir -p $sandbox && git archive HEAD | tar -x -C $sandbox
    PYTHONPATH=$sandbox/src python experiments/002-path-aware-lookahead/probes/prechange_probe.py <id>

Each id evaluates one new regression's contract against pre-change code as far
as that code can express it, prints what the base tree reports, and exits 1 when
the base behaviour violates the regression's assertion (the expected result for
the reachability rows) or 0 when the contract already held before the change
(the frozen-side and pre-existing-fallback rows).
"""

from __future__ import annotations

import random
import sys

import block_stack_ai

BASE_MODULE = block_stack_ai.__file__


def _guard() -> None:
    if "experiment-002-path-aware-lookahead" in str(BASE_MODULE):
        raise SystemExit(f"refusing to run: imported {BASE_MODULE}, not a pre-change tree")
    try:
        import block_stack_ai.pathaware  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        raise SystemExit(f"refusing to run: {BASE_MODULE} already carries pathaware")
    print(f"# base module: {BASE_MODULE}")


from block_stack_ai.agents import (  # noqa: E402
    AGENT_NAMES,
    DOWN,
    GreedyPolicy,
    PlacementAgent,
    create_agent,
)
from block_stack_ai.engine import create_game  # noqa: E402
from block_stack_ai.heuristic import (  # noqa: E402
    HEIGHT,
    HIDDEN_ROWS,
    SPAWN_ORIGIN_Y,
    WIDTH,
    Placement,
    board_features,
    board_grid,
    enumerate_placements,
    feature_score,
    fits,
    settle,
)
from block_stack_ai.pieces import PIECES, cells, orientation_count  # noqa: E402

HIDDEN = ((0,) * WIDTH,) * 2


def grid_of(rows, hidden=HIDDEN):
    return board_grid(tuple(tuple(row) for row in rows), hidden)


def blank_rows():
    return [[0] * WIDTH for _ in range(HEIGHT)]


def ceiling_grid():
    """Visible rows 0-1 filled at columns 7-9: the 002 ``right_wall_grid``."""
    rows = blank_rows()
    for row in (0, 1):
        for column in range(7, WIDTH):
            rows[row][column] = 1
    return grid_of(rows)


def fence_grid():
    """Visible rows 2-19 filled at column 3: the 002 ``fence_grid``."""
    rows = blank_rows()
    for row in range(2, HEIGHT):
        rows[row][3] = 1
    return grid_of(rows)


def blocked_spawn_grid():
    """Visible rows 0-2 filled everywhere: the 002 ``blocked_spawn_grid``."""
    rows = blank_rows()
    for row in range(3):
        for column in range(WIDTH):
            rows[row][column] = 1
    return grid_of(rows)


def random_grids(count: int):
    """The 002 test's grid stream, reproduced exactly (same seed, same draws)."""
    rng = random.Random(20260927)
    grids = [grid_of(blank_rows()), ceiling_grid(), fence_grid()]
    for _ in range(count):
        hidden = tuple(tuple(1 if rng.random() < 0.15 else 0 for _ in range(WIDTH))
                       for _ in range(HIDDEN_ROWS))
        rows = [[1 if rng.random() < 0.25 else 0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
        grids.append(grid_of(rows, hidden))
    return grids


def straight_set(grid, piece):
    return {(p.orientation, p.x, p.y) for p in enumerate_placements(grid, piece)}


def every_aim(piece):
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            yield orientation, x


# --- R1/R2: the new bitmask model's contract is against frozen heuristic code.


def r1_column_masks():
    """The frozen side the new bitmask test compares against, executed at base."""
    grids = random_grids(12)
    settled = 0
    features = []
    for grid in grids:
        features.append(board_features(grid))
        for piece in PIECES:
            for orientation, x in every_aim(piece):
                for y in range(0, 20):
                    if not fits(grid, piece, orientation, x, y):
                        continue
                    # The new test compares the frozen board_features(settled)
                    # and the settled grid with the bitmask mirror. Only this
                    # frozen side exists at the base.
                    settled_board, cleared = settle(grid, piece, orientation, x, y)
                    board_features(settled_board)
                    assert cleared >= 0
                    settled += 1
    digest = sum(h.holes + h.aggregate_height + h.bumpiness + h.max_height for h in features)
    print(f"grids: {len(grids)}")
    print(f"frozen settle/fits/board_features states executed: {settled}")
    print(f"feature digest over the grids: {digest}")
    print("frozen side exists and executes; the bitmask mirror it is compared to is new")
    print(f"pathaware importable at base: {'block_stack_ai.pathaware' in sys.modules}")


def occupied_hidden_grid():
    """The 002 test's single-clear case: visible row 0 clears above the buffer."""
    hidden = ((0,) * WIDTH, (1, 1) + (0,) * (WIDTH - 2))
    rows = blank_rows()
    for column in range(2, WIDTH):
        rows[0][column] = 1
    rows[1][0] = rows[1][1] = 1
    return grid_of(rows, hidden)


def double_clear_grid():
    """The 002 test's double-clear case: two full rows under an occupied buffer."""
    hidden = ((0,) * WIDTH, tuple(1 if column in (4, 5) else 0 for column in range(WIDTH)))
    rows = blank_rows()
    for column in range(WIDTH):
        if column not in (4, 5):
            rows[18][column] = 1
            rows[19][column] = 1
    return grid_of(rows, hidden)


def r1b_settle_hidden():
    """The frozen settle the hidden-buffer regression compares against.

    ``tests/test_pathaware.py::test_settle_columns_keeps_the_hidden_buffer_across_a_clear``
    asserts that the new bitmask ``settle_columns`` equals the frozen
    ``heuristic.settle`` on two boards with an occupied hidden buffer, and that
    the buffer survives the clear (``Game::clear_rows`` rewrites the visible
    board alone). Only the frozen side exists at the base, so this probe
    executes that side on the test's own boards and reports the pinned values.
    """
    single = occupied_hidden_grid()
    settled, cleared = settle(single, "O", 0, 1, -1)
    print(f"# single clear: frozen settle('O', x=1, y=-1) -> cleared={cleared}")
    print(f"# single clear: frozen hidden buffer after the clear = {settled[:HIDDEN_ROWS]}")
    assert cleared == 1
    assert settled[:HIDDEN_ROWS] == single[:HIDDEN_ROWS]
    double = double_clear_grid()
    settled2, cleared2 = settle(double, "O", 0, 5, 18)
    visible = settled2[HIDDEN_ROWS:]
    print(f"# double clear: frozen settle('O', x=5, y=18) -> cleared={cleared2}")
    print(f"# double clear: frozen hidden buffer after the clear = {settled2[:HIDDEN_ROWS]}")
    print(f"# double clear: frozen visible field after the clear = "
          f"{sum(sum(row) for row in visible)} filled cells (the two cleared rows were all of it)")
    assert cleared2 == 2
    assert settled2[:HIDDEN_ROWS] == double[:HIDDEN_ROWS]
    assert sum(sum(row) for row in visible) == 0
    print("frozen settle exists and executes; the bitmask settle_columns mirror it is new")
    print(f"pathaware importable at base: {'block_stack_ai.pathaware' in sys.modules}")


def r12b_engine_level():
    """The engine's own level transition, the behaviour the new mirror copies.

    ``test_level_for_lines_mirrors_the_engine_transitions`` pins a function that
    does not exist at the base, so the base cannot evaluate the assertion. The
    behaviour it mirrors is the registered engine's own: this clears lines at the
    start level's transition threshold and prints the level the engine reports,
    giving the mirror's pinned table a measured pre-change reference.
    """
    threshold = 10  # FIRST_TRANSITION_LINES[0], from core/src/rules.cpp
    configuration = {"ruleset": "classic_ntsc_extended", "mode": "endless",
                     "start_level": 0, "height": 0}
    board = [[0] * WIDTH for _ in range(HEIGHT)]
    for row in (HEIGHT - 2, HEIGHT - 1):
        for column in range(WIDTH - 2):
            board[row][column] = 1
    samples = []
    with create_game(**configuration, seed=2) as game:
        state = game.state
        for _ in range(4096):
            if state.lines >= threshold + 1 or state.terminal:
                break
            if state.phase != "active":
                state, _ = game.step(0)
                continue
            stage = state.lines
            game.set_board(board)
            game.set_piece("O", x=WIDTH - 1, y=HEIGHT - 2)
            for _ in range(64):
                state, events = game.step(DOWN)
                if state.lines != stage or state.terminal:
                    break
            samples.append((state.lines, state.level))
    print(f"# engine, start level 0: (lines, level) samples = {samples}")
    first_raised = next((lines for lines, level in samples if level != 0), None)
    print(f"# engine: level 0 through {threshold - 1} lines, level 1 first reported at "
          f"{first_raised} lines (the pinned threshold)")
    assert first_raised == threshold, (first_raised, samples)
    assert all(level == 0 for lines, level in samples if lines < threshold), samples
    assert state.level == 1, (state.lines, state.level)
    print("the engine itself raises the level at exactly the pinned threshold; the "
          "mirror function that copies it has no pre-change counterpart")


def dense_grid():
    """The 002 test's dense stranded board (board 442 of the seeded stream)."""
    rows = [
        "0101000111", "1001100110", "1101111111", "1001111110", "1111011011",
        "1111110101", "0111110001", "1111010111", "0111111111", "1011111101",
        "0101111011", "1111111011", "0001110111", "1100011100", "1011101101",
        "1111111111", "1111101111", "0111110111", "1111101111", "1111110111",
    ]
    return grid_of([[int(cell) for cell in row] for row in rows])


def r9b_base_choice():
    """The frozen choice rule's determinism, the base analogue of the new one.

    ``test_lookahead_choice_is_deterministic`` asserts the new agent's choice is
    a pure function of the board and the preview. The base has no lookahead, but
    its choice rule is deterministic in the same sense: the frozen
    ``GreedyPolicy`` over the frozen enumeration returns the same placement every
    time. Only that frozen side exists at the base.
    """
    grid = dense_grid()
    placements = enumerate_placements(grid, "J")
    policy = GreedyPolicy()
    choices = [(p.orientation, p.x) for p in (policy.choose(placements) for _ in range(5))]
    print(f"# frozen enumeration of J on the dense board: {len(placements)} placements")
    print(f"# base GreedyPolicy.choose, five calls: {choices}")
    assert len(set(choices)) == 1, choices
    print("the frozen choice rule is already a pure function of its inputs")


def r10b_base_value_rule():
    """The frozen value rule that the new -inf contract replaces.

    ``test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece``
    asserts that a current placement which leaves the preview piece no admissible
    placement has value ``-inf``. The base has no lookahead: its only value rule
    scores the current placement's own settled board (``GreedyPolicy`` over
    ``enumerate_placements``), with no next-piece term at all, so the base cannot
    express that contract. This executes the frozen rule on the three placements
    the board admits; the frozen ``settle`` reproduces each lock at the same
    origin the new plan model predicts, so the boards are the same ones.
    """
    grid = dense_grid()
    behaviours = [(p.orientation, p.x, p.y) for p in enumerate_placements(grid, "J")]
    print(f"# frozen straight-drop candidates for J on the dense board: {sorted(behaviours)}")
    for orientation, x in ((0, 5), (3, 5), (3, 6)):
        settled, cleared = settle(grid, "J", orientation, x, 0)
        score = feature_score(board_features(settled), cleared)
        print(f"# base rule for J({orientation}, {x}) at origin row 0: cleared {cleared}, "
              f"its own board scores {score:.2f}")
    assert (0, 5, 0) in behaviours and (3, 5, 0) in behaviours and (3, 6, 0) in behaviours
    chosen = GreedyPolicy().choose(enumerate_placements(grid, "J"))
    print(f"# the frozen rule's own choice on this board: J({chosen.orientation}, {chosen.x}) "
          f"at origin row {chosen.y}, score {chosen.score:.2f}")
    print("the base rule has no next-piece term: it scores neither (0, 5) nor (3, 5)")
    print("worse for stranding the preview piece, so the regression's -inf has no")
    print("pre-change counterpart")


def r2_fits_predicate():
    """The frozen fit rule the new precomputed table is compared against."""
    grids = random_grids(8)
    compared = 0
    agree = 0
    for grid in grids:
        for piece in PIECES:
            for orientation in range(orientation_count(piece)):
                for x in range(-1, WIDTH + 1):
                    for y in range(0, 22):
                        entry = fits(grid, piece, orientation, x, y)
                        compared += 1
                        agree += int(entry == fits(grid, piece, orientation, x, y))
    print(f"grids: {len(grids)}")
    print(f"frozen fits() states the new table is compared against: {compared}")
    print(f"frozen fits() is a pure function on them: {agree} / {compared}")
    print("frozen side exists and executes; the precomputed _TABLES/fits_at mirror is new")


# --- R3: equivalence between the new reachable set and the frozen enumeration.


def r3_reachable_equals_straight():
    grid = grid_of(blank_rows())
    total = 0
    for piece in PIECES:
        placements = enumerate_placements(grid, piece)
        total += len(placements)
        print(f"{piece}: {len(placements)} straight-drop placements, "
              f"columns {sorted({p.x for p in placements})}")
    print(f"frozen enumerate_placements total on the empty board: {total}")
    print("only the frozen side of the equivalence exists at the base")


# --- R4: extra columns a straight drop cannot enter (pre-change violation).


def r4_extra_columns():
    grid = ceiling_grid()
    straight = straight_set(grid, "O")
    print("# base candidate set for O (the only candidate set the base can build):")
    print(f"straight set = {sorted(straight)}")
    required = {(0, 7, 18), (0, 8, 18), (0, 9, 18)}
    missing = sorted(required - straight)
    print(f"placements the regression requires and the base set lacks: {missing}")
    assert not missing, (
        "pre-change candidate set has no (0,7)/(0,8)/(0,9): the regression's "
        f"'reachable - straight == {sorted(required)}' cannot hold"
    )


# --- R5: plans the straight model offers and the controller cannot execute.


def r5_drop_unexecutable_model():
    grid = fence_grid()
    straight = straight_set(grid, "I")
    print(f"# base straight set for I on the fence board: {sorted(straight)}")
    offender = (1, 3, 0)
    assert offender not in straight, (
        "pre-change straight-drop model still offers the plan (1,3,0), which the "
        "controller executes by locking in column 4 instead: the regression's "
        "'(1, 3) not in reachable' cannot hold"
    )


# --- R6/R7: controller rules the base already implements inline.


def _state(piece, orientation, x, piece_count, phase="active", terminal=False, board=None,
           hidden=HIDDEN):
    class State:
        pass

    state = State()
    state.current_piece = piece
    state.orientation = orientation
    state.x = x
    state.piece_count = piece_count
    state.phase = phase
    state.terminal = terminal
    state.board = board if board is not None else tuple((0,) * WIDTH for _ in range(HEIGHT))
    state.hidden_rows = hidden
    return state


def r6_plan_mask():
    """The base controller's own per-frame decision, driven through act()."""
    cases = 0
    presses = 0
    for piece in PIECES:
        count = orientation_count(piece)
        for orientation in range(count):
            for x in range(-1, WIDTH + 1):
                for to in list(range(count)) + [None]:
                    for tx in list(range(-1, WIDTH + 1)) + [None]:
                        for release in (False, True):
                            agent = PlacementAgent(GreedyPolicy())
                            agent._piece_count = 7
                            agent._release = release
                            agent._placement = (
                                Placement(piece, to, tx, 0, 0, 0.0)
                                if to is not None and tx is not None else None
                            )
                            mask = agent.act(_state(piece, orientation, x, 7))
                            cases += 1
                            presses += int(agent._release)
    print(f"base controller (PlacementAgent.act) states driven: {cases}")
    print(f"states that set a release frame: {presses}")
    print("base emits a mask and a release flag for every one of them")


def r7_fallback():
    """The base fallback: no straight placement means Down where it spawned."""
    grid = blocked_spawn_grid()
    for piece in PIECES:
        assert enumerate_placements(grid, piece) == ()
    policy = GreedyPolicy()
    print(f"greedy policy on an empty candidate tuple: {policy.choose(())}")
    agent = PlacementAgent(policy)
    state = _state("O", 0, 5, 7, board=grid[HIDDEN_ROWS:], hidden=grid[:HIDDEN_ROWS])
    masks = [agent.act(state) for _ in range(3)]
    print(f"base PlacementAgent masks where no placement fits: {masks}")
    assert masks == [DOWN, DOWN, DOWN], masks
    print("the Down fallback is pre-existing base behaviour; the reachable set is new")


# --- R8: the preview decides the choice (pre-change violation).


def r8_preview_choice():
    grid = grid_of(blank_rows())
    best = max(enumerate_placements(grid, "O"), key=lambda placement: placement.score)
    print(f"# base greedy choice on the empty board with an O: {(best.orientation, best.x)}")
    print("the base reads no preview field at all: its observation has none")
    required = (0, 9)
    assert (best.orientation, best.x) == required, (
        f"base greedy choice {(best.orientation, best.x)} != {required}, the placement "
        "the regression requires for the S preview: the choice cannot depend on the preview"
    )


# --- R13: the new agent name (pre-change violation).


def r13_agent_name():
    print(f"AGENT_NAMES = {AGENT_NAMES}")
    try:
        agent = create_agent("lookahead", 2)
    except ValueError as error:
        print(f"create_agent('lookahead', 2) -> ValueError: {error}")
        raise AssertionError(
            "the base has no lookahead agent, so the suite-record regression cannot hold"
        ) from error
    raise AssertionError(f"unexpectedly created {agent!r}")


# --- R12/R5 native probes: the base model against the engine itself.


def _later_piece_template(board, configuration, piece, obstruct=None):
    """A native spawn state for a later piece, the way the runner reaches it.

    With ``obstruct``, the piece is placed on ``board`` first and the obstructing
    board is installed afterwards: ``set_piece`` refuses an overlapping piece and
    ``Game::spawn`` has no collision test, so this is how an overlapped spawn is
    reached.
    """
    game = create_game(**configuration)
    for _ in range(1000):
        state, events = game.step(DOWN)
        if events.locked:
            break
    else:
        raise AssertionError("the first piece never locked")
    for _ in range(200):
        state, events = game.step(0)
        if events.spawned:
            break
    else:
        raise AssertionError("no spawn after the first lock")
    assert (state.x, state.y, state.orientation) == (5, 0, 0)
    assert state.previous_input == 0
    assert state.first_delay_remaining == 0
    game.set_board(board)
    game.set_piece(piece, x=5, y=SPAWN_ORIGIN_Y, rotation=0)
    if obstruct is not None:
        game.set_board(obstruct)
    return game


def _drive_base_agent(game, piece, aim):
    """Drive the engine with the base controller's own masks aiming at ``aim``."""
    agent = PlacementAgent(GreedyPolicy())
    agent._piece_count = game.state.piece_count
    agent._placement = Placement(piece, aim[0], aim[1], 0, 0, 0.0)
    for _ in range(4096):
        state = game.state
        if state.phase != "active" or state.terminal:
            return None
        mask = agent.act(state)
        state, events = game.step(mask)
        if events.locked:
            return (state.orientation, state.x, state.y, events.game_over)
    raise AssertionError("the plan never locked")


CONFIG = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18,
          "height": 0, "seed": 3}


def r12_native_ceiling():
    """A placement the base straight model rejects but the engine really makes."""
    board = [[0] * WIDTH for _ in range(HEIGHT)]
    for row in (0, 1):
        for column in range(7, WIDTH):
            board[row][column] = 1
    model = straight_set(grid_of(board), "O")
    print(f"# base straight model's candidate set: {sorted(model)}")
    locked = None
    with _later_piece_template(board, CONFIG, "O") as game:
        locked = _drive_base_agent(game, "O", (0, 7))
    print(f"# base controller aiming at (0, 7) locks the engine at: {locked}")
    assert locked[:2] in {(o, x) for o, x, _ in model}, (
        f"the engine locked the aimed (0, 7) at {locked} but the pre-change straight "
        "model's candidate set excludes it: the whole-set gate has no pre-change analogue"
    )


def r5_native_fence():
    """A plan the base straight model offers and the engine locks elsewhere."""
    board = [[0] * WIDTH for _ in range(HEIGHT)]
    for row in range(2, HEIGHT):
        board[row][3] = 1
    model = straight_set(grid_of(board), "I")
    aim = (1, 3)
    print(f"# base straight model offers {aim} at row 0: {(1, 3, 0) in model}")
    locked = None
    with _later_piece_template(board, CONFIG, "I") as game:
        locked = _drive_base_agent(game, "I", aim)
    print(f"# base controller aiming at {aim} locks the engine at: {locked}")
    assert locked[:2] == aim, (
        f"the engine locked {locked} instead of the aimed {aim}: the pre-change model "
        "offers a placement the controller cannot execute"
    )


def r15_native_overhang():
    """A spawn the engine rescues out of an overlap, which the base set omits."""
    overhang = blank_rows()
    for column in range(2, 6):
        overhang[0][column] = 1
    for row in range(HEIGHT):
        overhang[row][2] = 1
    grid = grid_of(overhang)
    omitted = {piece: (0, 5, 0) not in straight_set(grid, piece) for piece in PIECES}
    print(f"# the frozen straight-drop set omits the plan (0, 5) for every piece: "
          f"{all(omitted.values())} ({omitted})")
    assert all(omitted.values()), omitted
    model = straight_set(grid, "O")
    with _later_piece_template(blank_rows(), CONFIG, "O", obstruct=overhang) as game:
        locked = _drive_base_agent(game, "O", (0, 5))
    print(f"# base controller aiming at (0, 5) on the overlapped spawn locks the engine at: "
          f"{locked}")
    assert locked is not None and locked[:2] in {(o, x) for o, x, _ in model}, (
        f"the engine locked {locked} but the pre-change candidate set is "
        f"{sorted(model)}: it omits a placement the controller executes by descending "
        "out of the overlap"
    )


PROBES = {
    "column_masks": r1_column_masks,
    "settle_hidden": r1b_settle_hidden,
    "fits_predicate": r2_fits_predicate,
    "reachable_equals_straight": r3_reachable_equals_straight,
    "extra_columns": r4_extra_columns,
    "drop_unexecutable_model": r5_drop_unexecutable_model,
    "plan_mask": r6_plan_mask,
    "base_choice": r9b_base_choice,
    "base_value_rule": r10b_base_value_rule,
    "engine_level": r12b_engine_level,
    "fallback": r7_fallback,
    "preview_choice": r8_preview_choice,
    "agent_name": r13_agent_name,
    "native_ceiling": r12_native_ceiling,
    "native_fence": r5_native_fence,
    "native_overhang": r15_native_overhang,
}


def main() -> int:
    _guard()
    if len(sys.argv) != 2 or sys.argv[1] not in PROBES:
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}}", file=sys.stderr)
        return 2
    name = sys.argv[1]
    print(f"# probe: {name}")
    try:
        PROBES[name]()
    except AssertionError as error:
        print(f"AssertionError: {error}")
        return 1
    print("result: the base tree satisfies this probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
