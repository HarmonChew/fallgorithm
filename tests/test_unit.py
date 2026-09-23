from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from block_stack_ai.agents import ScriptedAgent, parse_script
from block_stack_ai import engine
from block_stack_ai.runner import parse_config, run_episode


BASE = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 0, "height": 0, "seed": 42},
    "frame_limit": 10,
    "script": [{"mask": 8, "frames": 2}, {"mask": 0, "frames": 1}, {"mask": 8, "frames": 1}],
}


@pytest.mark.parametrize(
    "change",
    [
        {"frame_limit": 0},
        {"frame_limit": True},
        {"script": []},
        {"script": [{"mask": 32, "frames": 1}]},
        {"script": [{"mask": True, "frames": 1}]},
        {"script": [{"mask": 1, "frames": 0}]},
        {"game": {**BASE["game"], "seed": 65536}},
        {"game": {**BASE["game"], "start_level": 20}},
    ],
)
def test_config_rejects_invalid_values(change):
    with pytest.raises(ValueError):
        parse_config({**BASE, **change})


def test_script_is_deterministic_and_releases_rotation():
    agent = ScriptedAgent(parse_script(BASE["script"]))
    first = [agent.act(None) for _ in range(4)]
    assert first == [8, 8, 0, 8]
    assert agent.done
    with pytest.raises(StopIteration):
        agent.act(None)
    agent.reset()
    assert [agent.act(object()) for _ in range(4)] == first


@dataclass
class FakeState:
    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"


class FakeGame:
    def __init__(self, terminal_at=None, terminal_phase="game_over"):
        self.state = FakeState()
        self.terminal_at = terminal_at
        self.terminal_phase = terminal_phase
        self.closed = False
        self.actions = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def state_hash(self):
        return self.state.frame + (100 if self.state.terminal else 0)

    def step(self, mask):
        self.actions.append(mask)
        self.state.frame += 1
        if self.state.frame == self.terminal_at:
            self.state.terminal = True
            self.state.phase = self.terminal_phase
        names = (
            "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
            "game_over", "challenge_completed", "lines_cleared", "score_delta",
        )
        return self.state, SimpleNamespace(**{name: 0 for name in names})


@pytest.mark.parametrize(
    "limit,terminal_at,phase,expected_reason,expected_frames",
    [
        (10, None, "game_over", "script_complete", 4),
        (2, None, "game_over", "frame_limit", 2),
        (10, 2, "game_over", "game_over", 2),
        (10, 1, "challenge_complete", "challenge_complete", 1),
    ],
)
def test_stopping_reasons_and_resource_close(limit, terminal_at, phase, expected_reason, expected_frames):
    config = parse_config({**BASE, "frame_limit": limit})
    game = FakeGame(terminal_at, phase)
    episode = run_episode(config, lambda **_: game)
    assert episode["result"]["stopping_reason"] == expected_reason
    assert episode["result"]["frame_count"] == expected_frames
    assert len(episode["inputs"]) == expected_frames
    assert game.actions == episode["inputs"]
    assert game.closed


def test_game_is_closed_when_a_step_raises():
    game = FakeGame()

    def fail(_mask):
        raise RuntimeError("native step failed")

    game.step = fail
    with pytest.raises(RuntimeError, match="native step failed"):
        run_episode(parse_config(BASE), lambda **_: game)
    assert game.closed


def test_missing_engine_checkout_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setenv("BLOCK_STACK_ROOT", str(tmp_path / "missing"))
    with pytest.raises(engine.EngineError, match="BLOCK_STACK_ROOT"):
        engine.engine_root()


def test_missing_native_library_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setenv("BLOCKS_NATIVE_LIB", str(tmp_path / "missing.so"))
    with pytest.raises(engine.EngineError, match="BLOCKS_NATIVE_LIB"):
        engine.native_library_path()
    monkeypatch.delenv("BLOCKS_NATIVE_LIB")
    monkeypatch.setattr(engine, "BUILD_DIR", Path(tmp_path / "empty"))
    with pytest.raises(engine.EngineError, match="setup_engine.py"):
        engine.native_library_path()
