from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from block_stack_ai.engine import create_game, engine_executable
from block_stack_ai.live import LiveSession
from block_stack_ai.runner import SuiteConfig, VerificationError, verify_run


pytestmark = pytest.mark.integration
GAME = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18, "height": 0}


def test_live_session_rejects_desktop_drift_and_excludes_aborted_games(tmp_path):
    config = SuiteConfig(GAME, 1200, (2,), ("greedy",))
    session = LiveSession(config, tmp_path / "runs")
    try:
        with create_game(**GAME, seed=2) as desktop:
            initial = desktop.save_state()
            session.receive("BEGIN", initial)
            mask = session.receive("STATE", initial)
            desktop.step(mask ^ 1)
            with pytest.raises(VerificationError, match="differs"):
                session.receive("STATE", desktop.save_state())
            assert session.records == []
            desktop.load_state(initial)
            desktop.step(mask)
            session.receive("ABORT", desktop.save_state())
            assert not session.active
            assert not (tmp_path / "runs").exists()
            # Restart must reset the policy as well as the native state.
            session.receive("BEGIN", initial)
            assert session.receive("STATE", initial) == mask
    finally:
        session.close()


@pytest.fixture
def desktop_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "preferences"))


@pytest.mark.desktop
@pytest.mark.parametrize("agent,reason", [("greedy", "frame_limit"), ("random", "game_over")])
def test_live_desktop_pause_step_restart_and_record(tmp_path, desktop_environment, agent, reason):
    config = SuiteConfig(GAME, 1200, (2,), ("random", "greedy"))
    path = tmp_path / "experiments/001-test/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(config.to_dict()), encoding="utf-8")
    runs = tmp_path / "runs"
    # The native smoke path pauses, advances a frame, restarts, then runs this
    # fresh game to completion through the very same per-frame pipe protocol.
    code = """
import sys
from pathlib import Path
from block_stack_ai import cli
from block_stack_ai.live import play_live
cli.PROJECT_ROOT = Path(sys.argv[1])
def play(*args):
    return play_live(*args, runs_dir=Path(sys.argv[3]), desktop_arguments=('--controller-smoke',))
cli.play_live = play
raise SystemExit(cli.main(['play', '--experiment', '001', '--agent', sys.argv[2], '--seed', '2']))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), agent, str(runs)],
        capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Stopped at frame 1" in completed.stdout
    records = list(runs.glob("*/run.json"))
    assert len(records) == 1  # the aborted game before restart was not scored
    record = json.loads(records[0].read_text())
    assert record["configuration"]["agents"] == [agent]
    assert record["configuration"]["seeds"] == [2]
    assert record["episodes"][0]["result"]["stopping_reason"] == reason
    verify_run(records[0])  # regenerate decisions through the original headless path


@pytest.mark.desktop
@pytest.mark.parametrize("response", ["32\n", "-1\n", "1x\n"])
def test_native_controller_rejects_invalid_masks(desktop_environment, response):
    completed = subprocess.run(
        [str(engine_executable("block_stack")), "--controller-stdio", "--frames", "2"],
        input=response, capture_output=True, text=True, timeout=5,
    )
    assert completed.returncode == 1
    assert "invalid unsigned value" in completed.stderr


@pytest.mark.desktop
def test_native_controller_exits_when_input_pipe_closes(desktop_environment):
    completed = subprocess.run(
        [str(engine_executable("block_stack")), "--controller-stdio", "--frames", "2"],
        input="", capture_output=True, text=True, timeout=5,
    )
    assert completed.returncode == 0
    messages = completed.stdout.splitlines()
    assert messages[-1].startswith("ABORT ")
    with create_game() as game:
        state = game.load_state(bytes.fromhex(messages[-1].split(" ", 1)[1]))
        assert state.frame == 0
