from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from block_stack_ai.agents import ScriptedAgent, parse_script
from block_stack_ai import engine, runner
from block_stack_ai.runner import (
    RunConfig,
    SuiteConfig,
    VerificationError,
    parse_config,
    run_and_save,
    run_episode,
    verify_run,
)


EVENT_NAMES = (
    "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
    "game_over", "challenge_completed", "lines_cleared", "score_delta",
)


BASE = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 0, "height": 0, "seed": 42},
    "frame_limit": 10,
    "script": [{"mask": 8, "frames": 2}, {"mask": 0, "frames": 1}, {"mask": 8, "frames": 1}],
}

SUITE = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18, "height": 0},
    "frame_limit": 10,
    "seeds": [1, 2],
    "agents": ["random", "greedy"],
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


def test_scripted_and_suite_configs_are_distinguished():
    scripted = parse_config(BASE)
    assert isinstance(scripted, RunConfig)
    assert not isinstance(scripted, SuiteConfig)

    suite = parse_config(SUITE)
    assert isinstance(suite, SuiteConfig)
    assert suite.seeds == (1, 2)
    assert suite.agents == ("random", "greedy")
    assert suite.game == SUITE["game"]
    assert parse_config(suite.to_dict()) == suite


@pytest.mark.parametrize(
    "change",
    [
        {"frame_limit": 0},
        {"seeds": []},
        {"seeds": [65536]},
        {"seeds": [True]},
        {"seeds": 1},
        {"agents": []},
        {"agents": ["scripted"]},
        {"game": {**SUITE["game"], "seed": 42}},
        {"game": {**SUITE["game"], "ruleset": "classic"}},
        {"script": BASE["script"]},
    ],
)
def test_suite_config_rejects_invalid_values(change):
    with pytest.raises(ValueError):
        parse_config({**SUITE, **change})


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
    piece_count: int = 0


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
        return self.state, SimpleNamespace(**{name: 0 for name in EVENT_NAMES})


@dataclass
class SuiteState:
    """The placement-agent fields of an engine state, on a board with no room."""

    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"
    piece_count: int = 0
    current_piece: str = "T"
    board: object = ((1,) * 10,) * 20
    hidden_rows: object = ((1,) * 10,) * 2


class SuiteGame:
    """A native-engine stand-in that is blind to the agent and the seed.

    The field is full, so no placement fits and every placement agent emits the
    same Down frames. Episodes therefore replay identically whatever their
    recorded agent and seed are, which isolates the suite identity check: a
    duplicated episode changes neither the replay nor the summary.
    """

    def __init__(self, **_):
        self.state = SuiteState()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def state_hash(self):
        return self.state.frame

    def step(self, mask):
        self.state.frame += 1
        return self.state, SimpleNamespace(**{name: 0 for name in EVENT_NAMES})


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


def test_suite_verification_rejects_a_tampered_episode_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    assert [(episode["agent"], episode["seed"]) for episode in record["episodes"]] == [
        ("random", 1), ("random", 2), ("greedy", 1), ("greedy", 2)
    ]
    assert verify_run(path, lambda **_: SuiteGame()) == []

    # Neither tamper changes the configured agent and seed sets, the recorded
    # frames or the recorded summary; only the per-position identity differs.
    def rejected(episodes, message):
        path.write_text(json.dumps({**record, "episodes": episodes}), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, lambda **_: SuiteGame())

    rejected(  # swap the two random seeds: both pairs stay configured, in the wrong order
        [record["episodes"][1], record["episodes"][0], *record["episodes"][2:]],
        "Episode 0 is not the configured suite entry: recorded agent 'random' "
        "with seed 2, expected agent 'random' with seed 1",
    )
    rejected(  # duplicate (greedy, 1) and omit (greedy, 2)
        [*record["episodes"][:3], dict(record["episodes"][2])],
        "Episode 3 is not the configured suite entry: recorded agent 'greedy' "
        "with seed 1, expected agent 'greedy' with seed 2",
    )


class CountingGame(FakeGame):
    """A scripted-episode stand-in whose piece count advances independently.

    Two frame steps make one piece here, so the count differs from the frame
    count and a verifier that compares the wrong state field is caught.
    """

    def step(self, mask):
        state, events = super().step(mask)
        self.state.piece_count = self.state.frame // 2
        return state, events


def test_scripted_verification_compares_a_recorded_piece_count(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: CountingGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    # The writer records the replayed piece count beside the result it replays,
    # and that count is not the frame count.
    assert (record["pieces"], record["result"]["frame_count"]) == (2, 4)
    assert verify_run(path, lambda **_: CountingGame()) == []

    def rejected(value, message):
        path.write_text(json.dumps({**record, "pieces": value}), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, lambda **_: CountingGame())

    rejected(5, "pieces: recorded 5, replayed 2")
    rejected(4, "pieces: recorded 4, replayed 2")  # the frame count must not pass
    rejected(None, "pieces: recorded None, replayed 2")
    rejected(True, "pieces: recorded True, replayed 2")

    # A record that carries no piece count is an older record and still verifies.
    legacy = {key: value for key, value in record.items() if key != "pieces"}
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, lambda **_: CountingGame()) == []


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
