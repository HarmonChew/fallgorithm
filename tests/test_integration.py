from __future__ import annotations

import json
from pathlib import Path

import pytest

from block_stack_ai.engine import PROJECT_ROOT, create_game
from block_stack_ai.runner import VerificationError, load_config, run_and_save, verify_run


pytestmark = pytest.mark.integration
CONFIG = PROJECT_ROOT / "experiments" / "000-connection" / "config.json"


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
