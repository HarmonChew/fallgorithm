from __future__ import annotations

import json
from pathlib import Path

import pytest

from block_stack_ai.agents import DOWN
from block_stack_ai.engine import PROJECT_ROOT, create_game
from block_stack_ai.heuristic import board_grid, enumerate_placements, settle
from block_stack_ai.runner import (
    VerificationError,
    load_config,
    run_and_save,
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
        for metric in ("score", "lines", "frames", "pieces"):
            assert set(summary[metric]) == {"mean", "median", "min", "max"}
    verify_run(path)

    record["episodes"][0]["inputs"].insert(0, 0)
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(VerificationError, match="episode 0"):
        verify_run(path)
