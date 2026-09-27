from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from block_stack_ai.agents import DOWN
from block_stack_ai.engine import PROJECT_ROOT, create_game, engine_executable
from block_stack_ai.replay import export_replay
from block_stack_ai.heuristic import SPAWN_ORIGIN_Y, WIDTH, board_grid, enumerate_placements, settle
from block_stack_ai.pieces import PIECES, cells, orientation_count
from block_stack_ai.runner import (
    VerificationError,
    load_config,
    parse_config,
    run_and_save,
    run_episode,
    verify_run,
)


pytestmark = pytest.mark.integration
CONFIG = PROJECT_ROOT / "experiments" / "000-connection" / "config.json"
SUITE_CONFIG = PROJECT_ROOT / "experiments" / "001-greedy-heuristic" / "config.json"


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
    assert record["format_version"] == 1
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
    assert record["format_version"] == 2
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
