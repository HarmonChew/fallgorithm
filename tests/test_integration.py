from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys

import pytest

from block_stack_ai.agents import DOWN, create_agent
from block_stack_ai.engine import PROJECT_ROOT, create_game, engine_executable
from block_stack_ai.replay import export_replay
from block_stack_ai import wellplan
from block_stack_ai.heuristic import (
    GRID_ROWS,
    HEIGHT,
    SPAWN_ORIGIN_Y,
    WIDTH,
    board_grid,
    enumerate_placements,
    settle,
)
from block_stack_ai.pathaware import (
    grid_columns,
    plan_mask,
    reachable_placements,
    settle_columns,
    simulate_plan,
)
from block_stack_ai.pieces import PIECES, cells, orientation_count
from block_stack_ai import runner
from block_stack_ai.runner import (
    LEGACY_SUITE_FORMAT_VERSION,
    PRIOR_SUITE_FORMAT_VERSION,
    SUITE_FORMAT_VERSION,
    FORMAT_VERSION,
    VerificationError,
    load_config,
    parse_config,
    run_and_save,
    run_episode,
    verify_run,
)
from block_stack_ai.tetris import weights_record as tetris_weights_record
from block_stack_ai.wellplan import weights_record as wellplan_weights_record


pytestmark = pytest.mark.integration
CONFIG = PROJECT_ROOT / "experiments" / "000-connection" / "config.json"
SUITE_CONFIG = PROJECT_ROOT / "experiments" / "001-greedy-heuristic" / "config.json"
LOOKAHEAD_CONFIG = PROJECT_ROOT / "experiments" / "002-path-aware-lookahead" / "config.json"
TETRIS_CONFIG = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "config.json"
PLAN_CONFIG = PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "config.json"


def _plan_probe(name="exp004_plan_probe"):
    """The 004 probe file, loaded from the experiment so its checks can be driven."""
    path = (PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "probes"
            / "evidence.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_read_and_advance_exact_frames():
    with create_game(seed=42, start_level=18) as game:
        before = game.state
        assert before.frame == 0
        assert len(before.board) == 20
        for _ in range(5):
            game.step(0)
        assert game.state.frame == before.frame + 5


def test_same_seed_and_inputs_have_same_native_hash():
    configuration = load_config(CONFIG).game
    inputs = [1, 1, 0, 8, 8, 0, 8, 0, 4, 4, 4]
    hashes = []
    for _ in range(2):
        with create_game(**configuration) as game:
            events = [game.step(mask)[1] for mask in inputs]
            assert events[3].rotated
            assert not events[4].rotated  # a held rotation does not fire again
            assert events[6].rotated      # a release creates a fresh press edge
            hashes.append(game.state_hash())
    assert hashes[0] == hashes[1]


def test_save_and_verify_real_run(tmp_path: Path):
    path = run_and_save(CONFIG, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == FORMAT_VERSION
    assert record["inputs"]
    assert record["result"]["frame_count"] == len(record["inputs"])
    verify_run(path)
    record["result"]["final_state_hash"] = "0000000000000000"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(VerificationError, match="final_state_hash"):
        verify_run(path)


def test_every_enumerated_placement_locks_where_the_model_says():
    """The mirrored geometry, straight drop and lock rules must match the engine."""
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 5}
    with create_game(**configuration) as game:
        state = game.state
        grid = board_grid(state.board, state.hidden_rows)
        piece = state.current_piece
        placements = enumerate_placements(grid, piece)
    assert placements

    for placement in placements:
        with create_game(**configuration) as game:
            assert game.state.current_piece == piece
            game.set_piece(placement.piece, x=placement.x, y=placement.y, rotation=placement.orientation)
            events = None
            for _ in range(10):
                state, events = game.step(DOWN)
                if events.locked:
                    break
            assert events is not None and events.locked
            settled, cleared = settle(grid, placement.piece, placement.orientation, placement.x, placement.y)
            assert cleared == 0
            assert board_grid(state.board, state.hidden_rows) == settled


def test_enumeration_matches_engine_straight_drops_from_the_spawn_origin():
    """Whole-set gate: every enumerated placement is an engine-reachable drop.

    Two constructed boards isolate the two directions the contract cares about:

    * a visible overhang over a stack (visible row 0 filled at columns 4 and 5
      with free cells below, a tall left stack and a shorter right one), so a
      column blocked at the spawn origin must contribute no placement and no
      placement may rest above the origin;
    * minos occupying the hidden buffer while the visible field is empty, so a
      column whose *hidden* cells are filled while its visible spawn rows are
      free must still be enumerated (the old top-of-grid entry rejected it).

    For every piece, orientation and legal column the native engine is driven
    from the spawn origin: ``set_piece`` (which enforces the engine's own
    ``fits``) and Down held until lock. A rejected ``set_piece`` must correspond
    to no enumerated placement, and a locked origin must equal the enumerated
    ``y``. This compares the entire placement set of both boards, not a sample.
    """
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}

    overhang = [[0] * WIDTH for _ in range(20)]
    for row in range(12, 20):
        for column in range(4):
            overhang[row][column] = 1
    for row in range(16, 20):
        for column in range(6, WIDTH):
            overhang[row][column] = 1
    overhang[0][4] = overhang[0][5] = 1

    empty_visible = [[0] * WIDTH for _ in range(20)]
    ceiling_blocker = [list(row) for row in empty_visible]
    ceiling_blocker[0][8] = ceiling_blocker[0][9] = 1

    templates = []
    with create_game(**configuration) as builder:
        builder.set_board(overhang)
        templates.append(("overhang", board_grid(builder.state.board, builder.state.hidden_rows),
                          builder.clone()))
        # Lock an O above the ceiling, then wipe the visible field: the hidden
        # buffer keeps its minos while the visible spawn rows are free.
        builder.set_board(ceiling_blocker)
        builder.set_piece("O", x=9, y=-2)
        for _ in range(60):
            _, events = builder.step(DOWN)
            if events.locked:
                break
        else:
            raise AssertionError("the ceiling O never locked")
        builder.set_board(empty_visible)
        hidden_grid = board_grid(builder.state.board, builder.state.hidden_rows)
        assert hidden_grid[0][8:10] == (1, 1)
        assert hidden_grid[1][8:10] == (1, 1)
        templates.append(("hidden-buffer", hidden_grid, builder.clone()))

    def engine_lock(template, piece, orientation, x):
        """Origin row the engine locks at from the spawn origin, or None if refused."""
        with template.clone() as trial:
            try:
                trial.set_piece(piece, x=x, y=SPAWN_ORIGIN_Y, rotation=orientation)
            except RuntimeError:
                return None
            for _ in range(400):
                state, events = trial.step(DOWN)
                if events.locked:
                    assert (state.orientation, state.x) == (orientation, x)
                    return state.y
            raise AssertionError(f"{piece} orientation {orientation} at x={x} never locked")

    compared = 0
    for label, grid, template in templates:
        with template:
            for piece in PIECES:
                model = {
                    (placement.orientation, placement.x): placement
                    for placement in enumerate_placements(grid, piece)
                }
                for orientation in range(orientation_count(piece)):
                    offsets = cells(piece, orientation)
                    first = min(offset_x for offset_x, _ in offsets)
                    last = max(offset_x for offset_x, _ in offsets)
                    for x in range(-first, WIDTH - last):
                        locked_y = engine_lock(template, piece, orientation, x)
                        placement = model.get((orientation, x))
                        compared += 1
                        if locked_y is None:
                            assert placement is None, (label, piece, orientation, x, placement)
                        else:
                            assert placement is not None, (label, piece, orientation, x, locked_y)
                            assert placement.y == locked_y, (label, piece, orientation, x)

    def columns(piece):
        return sum(
            WIDTH - (max(offset_x for offset_x, _ in cells(piece, orientation))
                     - min(offset_x for offset_x, _ in cells(piece, orientation)))
            for orientation in range(orientation_count(piece))
        )

    assert compared == sum(columns(piece) for piece in PIECES) * len(templates)


def test_placement_model_matches_a_native_lock_straddling_the_ceiling():
    """A lock that rests in the hidden rows and clears the visible row below it."""
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}

    rows = [[0] * 10 for _ in range(20)]
    for column in range(2, 10):
        rows[0][column] = 1  # the O completes this row from columns 0-1
    rows[1][0] = rows[1][1] = 1  # support, so the O rests at y = -1

    with create_game(**configuration) as game:
        game.set_board(rows)
        grid = board_grid(game.state.board, game.state.hidden_rows)
        game.set_piece("O", x=1, y=-1)
        for _ in range(200):
            state, events = game.step(0)
            if events.locked:
                break
        else:
            raise AssertionError("the ceiling piece never locked")
        settled, cleared = settle(grid, "O", 0, 1, -1)
        native = board_grid(state.board, state.hidden_rows)

    assert events.lines_cleared == cleared == 1
    # The lower minos completed and cleared visible row 0; the minos above the
    # ceiling stay in hidden row -1 exactly where the engine left them.
    assert native[1][:2] == (1, 1)
    assert native[2] == (0,) * 10
    assert native == settled


def test_hidden_rows_survive_a_later_clear_below_the_ceiling():
    """Minos left above the ceiling stay put when a later, lower row clears.

    The dispute was whether an occupied hidden row shifts down with a cleared
    row. The registered engine compacts ``state_.board`` alone and never touches
    ``state_.hidden_rows``, so the buffer is byte-identical across later locks
    that clear one row and two rows, while a model that shifted hidden rows
    would not match the engine.
    """
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}

    def lock(game, piece, x, y):
        game.set_piece(piece, x=x, y=y)
        for _ in range(200):
            state, events = game.step(0)
            if events.locked:
                return state, events
        raise AssertionError("the piece never locked")

    def board(full_rows, support_row):
        rows = [[0] * 10 for _ in range(20)]
        for row in full_rows:
            for column in range(2, 10):
                rows[row][column] = 1  # the O completes these rows at columns 0-1
        rows[support_row][0] = rows[support_row][1] = 1  # pins the O resting on top
        return rows

    with create_game(**configuration) as game:
        # First lock leaves minos above the ceiling and clears visible row 0.
        game.set_board(board((0,), 1))
        _, first = lock(game, "O", 1, -1)
        assert first.lines_cleared == 1
        hidden = game.state.hidden_rows
        assert all(hidden[1][:2])  # the O left minos above the ceiling

        # A later mid-field clear, far below the occupied hidden row.
        game.set_board(board((10,), 12))
        grid = board_grid(game.state.board, game.state.hidden_rows)
        state, events = lock(game, "O", 1, 10)
        settled, cleared = settle(grid, "O", 0, 1, 10)
        assert events.lines_cleared == cleared == 1
        assert state.hidden_rows == hidden  # the buffer never moves or clears
        assert board_grid(state.board, state.hidden_rows) == settled

        # A later double clear, also far below the occupied hidden row.
        game.set_board(board((8, 9), 10))
        grid = board_grid(game.state.board, game.state.hidden_rows)
        state, events = lock(game, "O", 1, 8)
        settled, cleared = settle(grid, "O", 0, 1, 8)
        assert events.lines_cleared == cleared == 2
        assert state.hidden_rows == hidden
        assert board_grid(state.board, state.hidden_rows) == settled


def test_suite_save_and_verify_real_run(tmp_path: Path):
    raw = json.loads(SUITE_CONFIG.read_text(encoding="utf-8"))
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**raw, "frame_limit": 400, "seeds": [1, 2]}), encoding="utf-8")

    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert sorted(record["summary"]) == ["greedy", "random"]
    assert len(record["episodes"]) == 4
    for summary in record["summary"].values():
        assert summary["games"] == 2
        assert set(summary["stopping_reasons"]) <= {"game_over", "frame_limit"}
        for metric in ("score", "lines", "frames", "pieces_placed"):
            assert set(summary[metric]) == {"mean", "median", "min", "max"}
    verify_run(path)

    record["episodes"][0]["inputs"].insert(0, 0)
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(VerificationError, match="episode 0"):
        verify_run(path)


def test_recorded_placed_pieces_agree_with_the_native_engine():
    """The recorded count is the board placements, not the engine's preview counter.

    A whole top-out episode is driven with no inputs on the fixed suite ruleset.
    ``state.piece_count`` is the RNG/preview selection counter and stays one
    above ``state.stats.pieces``; at game over ``stats.pieces`` equals the number
    of lock events. The topping-out lock raises ``locked`` but writes no piece,
    so the recorded count is one below both. A stop before the first lock shows
    the other end: the engine has already spawned the active piece
    (``stats.pieces == 1``) but nothing has locked, so the placed count is zero.
    """
    configuration = {**load_config(SUITE_CONFIG).game, "seed": 2}
    config = parse_config(
        {"game": configuration, "frame_limit": 2000, "script": [{"mask": 0, "frames": 2000}]}
    )
    episode = run_episode(config)
    assert episode["result"]["stopping_reason"] == "game_over"
    assert "pieces" not in episode

    locked = 0
    with create_game(**configuration) as game:
        state = game.state
        assert state.piece_count == state.stats.pieces + 1
        while not state.terminal:
            state, events = game.step(0)
            locked += int(events.locked)
        assert state.piece_count == state.stats.pieces + 1

    assert state.stats.pieces == locked
    assert episode["result"]["event_counts"]["locked"] == locked
    assert episode["result"]["event_counts"]["game_over"] == 1
    assert episode["pieces_placed"] == locked - 1 == state.stats.pieces - 1

    early_config = parse_config(
        {"game": configuration, "frame_limit": 1, "script": [{"mask": 0, "frames": 100}]}
    )
    early = run_episode(early_config)
    assert early["result"]["stopping_reason"] == "frame_limit"
    assert early["pieces_placed"] == 0
    with create_game(**configuration) as game:
        state, _ = game.step(0)
    assert state.stats.pieces == 1  # the active piece is spawned, not locked
    assert state.piece_count == 2


@pytest.mark.parametrize("variant", ["experiment", "strict_challenge", "frame_limit"])
def test_desktop_replay_preserves_verified_run(tmp_path: Path, variant: str):
    config = load_config(CONFIG).to_dict()
    if variant == "strict_challenge":
        config["game"].update(ruleset="classic_ntsc_strict", mode="challenge", height=5, seed=65535)
    elif variant == "frame_limit":
        config["frame_limit"] = 3
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    replay_path, _ = export_replay(path)
    verification = subprocess.run(
        [str(engine_executable("block_stack_replay")), str(replay_path)],
        check=True, capture_output=True, text=True,
    )
    assert f"{len(record['inputs'])} frames" in verification.stdout
    assert f"hash {int(record['result']['final_state_hash'], 16):x}" in verification.stdout

    # A broken record must fail verification before replacing a valid export.
    original = replay_path.read_bytes()
    record["result"]["final_state_hash"] = "0000000000000000"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(VerificationError, match="final_state_hash"):
        export_replay(path)
    assert replay_path.read_bytes() == original



def _aims(piece: str):
    """Every orientation and legal column of a piece, in canonical order."""
    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, WIDTH - last):
            yield orientation, x


def _spawn_template(configuration, board, first_piece: bool, seed_hidden: bool = False):
    """A native spawn state on a chosen board, with the engine's own timing.

    A later piece is reached the way the runner reaches it: the current piece is
    driven to its lock with Down held, then release frames carry the engine
    through the entry delay into the next spawn, so the state has no first-piece
    delay and a zero previous input. The game's first piece is used straight out
    of ``reset``, where the 96-frame delay is the model's to expect. Both
    ``previous_input`` and the delay are asserted rather than assumed. The board
    is replaced last, and ``set_piece`` puts a chosen piece back at the spawn
    origin.

    ``seed_hidden`` locks an O above the ceiling first, leaving minos in the
    hidden buffer, and then spawns on top of them, so the visible board can be
    replaced while the buffer stays occupied.
    """
    with create_game(**configuration) as game:
        state = game.state
        if seed_hidden:
            blocker = [[0] * WIDTH for _ in range(20)]
            blocker[0][8] = blocker[0][9] = 1  # the O comes to rest above the ceiling
            game.set_board(blocker)
            game.set_piece("O", x=9, y=-2)
            for _ in range(200):
                state, events = game.step(DOWN)
                if events.locked:
                    break
            else:
                raise AssertionError("the ceiling O never locked")
            assert events.lines_cleared == 0
            assert all(game.state.hidden_rows[1][8:10])
            for _ in range(200):
                state, events = game.step(0)
                if events.spawned:
                    break
            else:
                raise AssertionError("no spawn after the ceiling lock")
        elif not first_piece:
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
        assert state.first_delay_remaining == (96 if first_piece else 0)
        game.set_board(board)
        return game.clone(), state.first_delay_remaining


def _native_plan_lock(template, piece: str, plan, obstruct=None):
    """Drive the engine with the controller's masks and report where it locked.

    The masks come from ``plan_mask`` on the engine's own observation, not from
    the model's simulation, so this compares the two independently. With
    ``obstruct``, the piece is placed on the template's own board first and the
    obstructing board is installed afterwards: ``set_piece`` refuses an
    overlapping piece and ``Game::spawn`` has no collision test, so this is how
    the engine reaches an overlapped spawn.
    """
    with template.clone() as trial:
        trial.set_piece(piece, x=5, y=SPAWN_ORIGIN_Y, rotation=0)
        if obstruct is not None:
            trial.set_board(obstruct)
        release = False
        count = orientation_count(piece)
        state = trial.state
        for _ in range(4096):
            if state.phase != "active" or state.terminal:
                break
            mask, release = plan_mask(state.orientation, state.x, plan, release, count)
            state, events = trial.step(mask)
            if events.locked:
                return (state.orientation, state.x, state.y, events.game_over,
                        board_grid(state.board, state.hidden_rows))
        raise AssertionError(f"{piece} aiming at {plan} never locked")


def test_reachable_placements_match_engine_locks_from_the_spawn_state():
    """Whole-set gate: every plan locks exactly where the path model says.

    The boards put both directions of the contract on the engine itself:

    * a ceiling two visible rows tall over columns 7-9, which a piece can only
      get under by descending while it presses -- the straight-drop model rejects
      those columns and the reachable set must not;
    * a wall in column 3 from visible row 2 down, which no plan can cross even
      though a straight drop into the columns beyond it fits -- the straight-drop
      model offers those columns and the reachable set must not;
    * minos in the hidden buffer beside a tall stack, so a piece descending there
    meets the buffer;
    * visible row 0 filled over a wall, so every piece's spawn footprint is
      occupied: the engine has no collision test at spawn, so the plan has to
      descend out of the overlap rather than declare a top-out;
    * two seeded irregular boards (30% and 55% fill), also installed after the
      piece so the origin overlaps wherever they cover it — the case a
      randomized comparison exposed and the structured fixtures missed.

    Each board is driven as a later piece (gravity from the first active frame)
    and the ceiling also as the game's first piece (96 frames without a gravity
    attempt). For every piece, orientation and legal column the native engine is
    driven from the spawn state with exactly the masks the controller emits, and
    its locked ``(orientation, x, y)`` must equal the model's ``PlanOutcome``. A
    lock the engine turns into a top-out must correspond to no reachable
    placement; every other lock is a placement exactly when the plan reached its
    aim, and then the settled board must match cell for cell. This compares the
    whole placement set of every board, not a sample.
    """
    configuration = {**load_config(LOOKAHEAD_CONFIG).game, "seed": 3}

    ceiling = [[0] * WIDTH for _ in range(20)]
    for row in (0, 1):
        for column in range(7, WIDTH):
            ceiling[row][column] = 1

    wall = [[0] * WIDTH for _ in range(20)]
    for row in range(2, 20):
        wall[row][3] = 1

    stack = [[0] * WIDTH for _ in range(20)]
    for row in range(12, 20):
        for column in range(8, WIDTH):
            stack[row][column] = 1

    empty = [[0] * WIDTH for _ in range(20)]

    # Visible row 0 filled at columns 2-5 over a wall in column 2: every piece's
    # spawn footprint at x = 5 covers row 0, so the spawn origin is occupied.
    overhang = [[0] * WIDTH for _ in range(20)]
    for column in range(2, 6):
        overhang[0][column] = 1
    for row in range(20):
        overhang[row][2] = 1

    cases = [
        ("ceiling", ceiling, None, False, False),
        ("ceiling", ceiling, None, True, False),
        ("wall", wall, None, False, False),
        ("hidden-stack", stack, None, False, True),
        # An overlapped spawn: the engine has no collision test at spawn, so the
        # plan must descend out of the overlap instead of topping out.
        ("overhang-spawn", empty, overhang, False, False),
    ]

    # Irregular boards, placed after the piece so the spawn overlaps wherever the
    # board covers the origin: the structured fixtures above never did that, and
    # a randomized comparison is what exposed the rescue case. Seeded, so the
    # boards are the same on every run.
    generator = random.Random(20260927)
    for label, fill in (("random-sparse", 0.30), ("random-dense", 0.55)):
        cases.append((label, empty,
                      [[1 if generator.random() < fill else 0 for _ in range(WIDTH)]
                       for _ in range(20)], False, False))

    compared = 0
    for label, board, obstruct, first_piece, seed_hidden in cases:
        template, first_delay = _spawn_template(configuration, board, first_piece, seed_hidden)
        with template:
            state = template.state
            model_board = board if obstruct is None else obstruct
            grid = board_grid(tuple(tuple(int(cell) for cell in row) for row in model_board),
                              state.hidden_rows)
            columns = grid_columns(grid)
            if seed_hidden:
                assert grid[1][8:10] == (1, 1)
            for piece in PIECES:
                model = {
                    (placement.orientation, placement.x): placement
                    for placement in reachable_placements(
                        grid, piece, level=state.level, first_delay_remaining=first_delay)
                }
                for orientation, x in _aims(piece):
                    plan = (orientation, x)
                    native = _native_plan_lock(template, piece, plan, obstruct)
                    outcome = simulate_plan(grid, piece, plan, level=state.level,
                                            first_delay_remaining=first_delay)
                    compared += 1
                    placement = model.get(plan)
                    assert (outcome.orientation, outcome.x, outcome.y) == native[:3], (
                        label, first_piece, piece, plan, outcome, native[:3])
                    assert (outcome.reached and not outcome.top_out) == (placement is not None), (
                        label, first_piece, piece, plan, outcome)
                    if native[3]:  # Game::lock rejected the origin, so nothing was written
                        assert placement is None, (label, first_piece, piece, plan)
                        continue
                    assert (native[:2] == plan) == (placement is not None), (
                        label, first_piece, piece, plan, native[:3])
                    if placement is not None:
                        assert placement.y == native[2]
                        settled, cleared = settle_columns(columns, piece, orientation, x,
                                                          placement.y)
                        assert cleared == placement.lines_cleared
                        assert settled == grid_columns(native[4]), (label, first_piece, piece, plan)

    assert compared == sum(1 for piece in PIECES for _ in _aims(piece)) * len(cases)


def test_suite_record_with_the_lookahead_agent_runs_and_verifies(tmp_path: Path):
    """The new agent plays a suite episode and its record replays."""
    raw = json.loads(LOOKAHEAD_CONFIG.read_text(encoding="utf-8"))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({**raw, "frame_limit": 400, "seeds": [2], "agents": ["lookahead"]}),
        encoding="utf-8",
    )
    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert sorted(record["summary"]) == ["lookahead"]
    assert len(record["episodes"]) == 1
    assert record["episodes"][0]["result"]["stopping_reason"] in {"game_over", "frame_limit"}
    verify_run(path)


def test_tetris_agent_clears_four_rows_on_a_ready_native_well():
    """The declared objective spends the I on a four-row clear, on the engine.

    The board holds four full rows under columns 0-8 and an empty column 9, the
    classic Tetris setup. The agent drives the real engine from the spawn state,
    and the engine's own per-step clear result must be the four lines
    ``tetris_choice`` claims: the only four-row clear on this board is the
    vertical I in column 9, so a four-line clear on the engine is that placement.
    """
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}
    rows = [[0] * WIDTH for _ in range(20)]
    for row in range(16, 20):
        for column in range(WIDTH - 1):
            rows[row][column] = 1

    with create_game(**configuration) as game:
        game.set_board(rows)
        game.set_piece("I", x=5, y=0)
        agent = create_agent("tetris", configuration["seed"])
        events = None
        for _ in range(2000):
            state, events = game.step(agent.act(game.state))
            if events.locked:
                break
        else:
            raise AssertionError("the placed I never locked")
        assert events.lines_cleared == 4
        assert not events.game_over
        # The four rows cleared, so the visible field is empty and the engine's
        # line counter advanced by exactly four.
        assert game.state.lines == 4
        settled = board_grid(game.state.board, game.state.hidden_rows)
        assert all(cell == 0 for row in settled[2:] for cell in row)


def test_plan_agent_clears_four_rows_on_a_ready_native_well():
    """The plan's reserve is a real four-row clear on the engine.

    Four full rows under columns 0-8 and an empty column 9: the reserve the plan
    measures on this board is four, so its own choice for an I is the vertical
    drop into the designated well, and the engine's per-step clear result must be
    the four lines that reserve claims.
    """
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}
    rows = [[0] * WIDTH for _ in range(20)]
    for row in range(16, 20):
        for column in range(WIDTH - 1):
            rows[row][column] = 1

    with create_game(**configuration) as game:
        game.set_board(rows)
        game.set_piece("I", x=5, y=0)
        agent = runner.build_agent("tetris_plan", configuration["seed"])
        events = None
        for _ in range(2000):
            state, events = game.step(agent.act(game.state))
            if events.locked:
                break
        else:
            raise AssertionError("the placed I never locked")
        assert events.lines_cleared == 4
        assert not events.game_over
        assert game.state.lines == 4
        settled = board_grid(game.state.board, game.state.hidden_rows)
        assert all(cell == 0 for row in settled[2:] for cell in row)


def test_the_plan_reads_a_native_hidden_stack_as_over_its_budget():
    """A column above the ceiling is stack height to the plan, on the engine's rows.

    The engine's hidden buffer is real stack: the suite's own ``seed_hidden``
    template locks an O above the ceiling, so columns 8 and 9 hold cells in the
    hidden rows while the visible board is empty. Reading heights from the visible
    field alone made that state look like an empty board, which left
    ``holds_well`` true and the SPEND transition unreachable on a topped-out
    stack; the plan's height is measured from the lowest occupied cell of the
    whole grid, so the phase it reads here is the one the engine's state is in.
    """
    suite = load_config(SUITE_CONFIG)
    configuration = {**suite.game, "seed": 1}
    template, _ = _spawn_template(configuration, [[0] * WIDTH for _ in range(20)], False,
                                  seed_hidden=True)
    with template:
        grid = board_grid(template.state.board, template.state.hidden_rows)
        assert all(cell == 0 for row in grid[2:] for cell in row)
        assert grid[0][8:10] == (1, 1) and grid[1][8:10] == (1, 1)
        columns = grid_columns(grid)
        assert wellplan.stack_height(columns) == GRID_ROWS
        assert wellplan.stack_height(columns) > HEIGHT
        assert not wellplan.holds_well(0, wellplan.stack_height(columns))
        assert wellplan.initial_phase(0, columns) == wellplan.SPEND


def test_suite_record_with_the_plan_agent_runs_and_verifies(tmp_path: Path):
    """The plan agent plays, records its histogram, and declares its own objective."""
    raw = json.loads(PLAN_CONFIG.read_text(encoding="utf-8"))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({**raw, "frame_limit": 400, "seeds": [2], "agents": ["tetris_plan"]}),
        encoding="utf-8",
    )
    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert sorted(record["summary"]) == ["tetris_plan"]
    episode = record["episodes"][0]
    assert (episode["clear_sizes"]["singles"]
            + 2 * episode["clear_sizes"]["doubles"]
            + 3 * episode["clear_sizes"]["triples"]
            + 4 * episode["clear_sizes"]["tetrises"]) == episode["result"]["lines"]
    assert record["objective"] == {
        "module": "block_stack_ai.wellplan", "weights": wellplan_weights_record(),
        "sources": runner._objective_sources(agent="tetris_plan"),
    }
    verify_run(path)


def test_a_record_written_by_the_frozen_writer_still_verifies():
    """The identity of a record written before this experiment still matches here.

    The fixture is a version-6 suite record written by the frozen Experiment 003
    tree's own writer (``git archive`` of the branch base's ``src``, whose
    ``tetris.py`` hashes to the digest Experiment 003's retained capture records),
    and its ``objective`` section names the Tetris objective and the source
    identity of the five modules that computed its placements. Adding an agent
    must not invalidate such a record: the shared agent factory keeps dispatching
    exactly the agents its frozen source defined, so the digest that record covers
    is still the digest on this tree, and its recorded inputs replay because the
    frozen agent's behaviour is unchanged — the fixture's ten seeds' worth of
    Experiment 003 rows are re-derived in the experiment's own ``baseline`` check.
    """
    legacy = (PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "probes"
              / "legacy_v6_tetris_record.json")
    record = json.loads(legacy.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert record["objective"]["module"] == "block_stack_ai.tetris"
    assert record["objective"]["sources"] == runner._objective_sources()
    assert runner._objective_sources()["block_stack_ai.agents"] == hashlib.sha256(
        Path(sys.modules["block_stack_ai.agents"].__file__).read_bytes()).hexdigest()
    assert sum(episode["result"]["lines"] for episode in record["episodes"]) > 0
    # The verifier's only warnings are the engine-Git advisories, and they describe
    # this checkout's engine state rather than the record: which of them appears
    # changes when the engine's own working-tree edits are committed, while the
    # record, its replay and its identity are unchanged. Comparing against the
    # verifier's own advisory vocabulary (``probe.engine_advisories``) rather than
    # one wording keeps the check about the record instead of about the engine's
    # dirty flag.
    advisories = _plan_probe("exp004_plan_legacy_probe").engine_advisories()
    assert advisories
    warnings = verify_run(legacy)
    assert all(warning in advisories for warning in warnings), warnings


def test_the_frozen_record_checks_tolerate_a_committed_engine(monkeypatch):
    """The legacy checks read the verifier's advisories, not one engine state.

    The fixture records the engine as a working tree at a specific commit, so a
    checkout whose engine edits are committed — or whose engine has no Git metadata
    at all — reports different engine advisories than this one does. That is a
    property of the engine checkout and not of the record: the identity still
    matches this tree and the recorded inputs still replay. Requiring the
    working-tree wording specifically made the frozen-record checks fail on those
    states, so they now compare against the verifier's own advisory vocabulary and
    this test pins the states the old wording rejected.
    """
    probe = _plan_probe("exp004_plan_committed_engine_probe")
    committed = {"commit": "0" * 40, "dirty": False, "kind": "committed"}
    with monkeypatch.context() as patch:
        patch.setattr(runner, "git_info", lambda root: dict(committed))
        probe.check_legacy()
        warnings = verify_run(probe.LEGACY_RECORD)
    assert warnings and all(
        warning in probe.engine_advisories() for warning in warnings), warnings
    # The state this guards: the committed engine reports the recorded-vs-current
    # advisory, which the old wording requirement rejected.
    assert not all("working-tree" in warning for warning in warnings)


def test_the_frozen_record_checks_tolerate_an_unversioned_engine(monkeypatch):
    """The advisory vocabulary is derived independently of this checkout's Git state.

    An engine checkout with no Git metadata records ``commit`` and ``dirty`` as
    ``None``, so a vocabulary derived from a synthetic section of ``None`` values
    matched that state and dropped the recorded-vs-current advisory — and the frozen
    fixture, which records a commit and a dirty flag, then reported a warning the
    vocabulary did not contain. The derivation now makes both of the verifier's
    advisory branches fire whatever the checkout is, and this pins the state that
    broke it.
    """
    probe = _plan_probe("exp004_plan_unversioned_engine_probe")
    unversioned = {"commit": None, "dirty": None, "kind": "unversioned"}
    with monkeypatch.context() as patch:
        patch.setattr(runner, "git_info", lambda root: dict(unversioned))
        advisories = probe.engine_advisories()
        assert len(advisories) == 2, advisories
        probe.check_legacy()
        warnings = verify_run(probe.LEGACY_RECORD)
    assert warnings and all(warning in advisories for warning in warnings), warnings


def test_the_plan_probe_aggregate_command_checks_the_native_fixture():
    """The documented aggregate probe command runs end to end, native steps included.

    ``probes/evidence.py all`` is what the experiment's notes tell a reader to run.
    Its native step re-verifies the frozen writer's retained record, so the
    command is exercised here with that step real rather than stubbed; the
    engine-independent wiring of the same command is checked by the unit suite.
    """
    probe = _plan_probe("exp004_plan_probe_integration")
    probe.all_probes()
    assert probe.main([]) == 0
    assert probe.main(["check-legacy"]) == 0


def test_suite_record_with_the_tetris_agent_runs_and_verifies(tmp_path: Path):
    """The new agent plays a suite episode, records its clear sizes, and replays."""
    raw = json.loads(TETRIS_CONFIG.read_text(encoding="utf-8"))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({**raw, "frame_limit": 400, "seeds": [2], "agents": ["tetris"]}),
        encoding="utf-8",
    )
    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert sorted(record["summary"]) == ["tetris"]
    assert len(record["episodes"]) == 1
    episode = record["episodes"][0]
    assert sorted(episode["clear_sizes"]) == ["doubles", "singles", "tetrises", "triples"]
    assert (episode["clear_sizes"]["singles"]
            + 2 * episode["clear_sizes"]["doubles"]
            + 3 * episode["clear_sizes"]["triples"]
            + 4 * episode["clear_sizes"]["tetrises"]) == episode["result"]["lines"]
    assert episode["result"]["stopping_reason"] in {"game_over", "frame_limit"}
    # The replay re-derives the histogram from the engine's own clear result.
    verify_run(path)


def test_suite_record_with_the_tetris_agent_declares_its_objective(tmp_path: Path):
    """A real tetris suite records the objective that chose its placements.

    The record names the module that declares the objective, the weights it
    publishes and the source identity of the modules its decisions are computed
    from, and the replay compares them. The section is required at the version
    this writer emits, because the writer always records it for a suite that uses
    the agent: deleting it makes the record verify under whatever objective is
    current, so it is reported, and deleting only the identity is reported too,
    because the current writer always records that. The same JSON under the
    legacy version, which never emitted the section, still verifies, and so does
    the same JSON under the prior version, whose writer emitted the objective
    without the identity.
    """
    raw = json.loads(TETRIS_CONFIG.read_text(encoding="utf-8"))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({**raw, "frame_limit": 400, "seeds": [2], "agents": ["tetris"]}),
        encoding="utf-8",
    )
    path = run_and_save(config_path, tmp_path / "runs")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["format_version"] == SUITE_FORMAT_VERSION
    assert record["objective"] == {
        "module": "block_stack_ai.tetris", "weights": tetris_weights_record(),
        "sources": runner._objective_sources(),
    }
    verify_run(path)

    stripped = json.loads(json.dumps(record))
    del stripped["objective"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective: absent, but a record of this "
                                                r"format version declares the objective"):
        verify_run(path)

    legacy = json.loads(json.dumps(stripped))
    legacy["format_version"] = LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(legacy), encoding="utf-8")
    verify_run(path)

    # The identity is the newer half of the section, gated separately: a version-5
    # record without it had it deleted, while the version-4 writer never recorded
    # it and its records keep verifying.
    without_identity = json.loads(json.dumps(record))
    del without_identity["objective"]["sources"]
    path.write_text(json.dumps(without_identity), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective\.sources: absent, but a record of "
                                                r"this format version always carries it"):
        verify_run(path)

    without_identity["format_version"] = PRIOR_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(without_identity), encoding="utf-8")
    verify_run(path)
