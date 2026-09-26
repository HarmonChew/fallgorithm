from __future__ import annotations

import json
from dataclasses import dataclass, field
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
class FakeStats:
    """The one engine statistics field the runner reads: placed pieces."""

    pieces: int = 0


@dataclass
class FakeState:
    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"
    piece_count: int = 0
    stats: FakeStats = field(default_factory=FakeStats)


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
    stats: FakeStats = field(default_factory=FakeStats)
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

    def __init__(self, lock_period=2, **_):
        self.state = SuiteState()
        self.closed = False
        self.locks = 0
        self.lock_period = lock_period

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def state_hash(self):
        return self.state.frame

    def step(self, mask):
        self.state.frame += 1
        # Two frames lock one piece; the preview counter stays one above it.
        locked = self.state.frame % self.lock_period == 0
        self.locks += int(locked)
        self.state.stats.pieces = self.locks
        self.state.piece_count = self.locks + 1
        fields = {name: 0 for name in EVENT_NAMES}
        fields["locked"] = locked
        return self.state, SimpleNamespace(**fields)


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
    rejected(  # JSON true compares equal to the configured seed 1, so type is checked
        [{**record["episodes"][0], "seed": True}, *record["episodes"][1:]],
        "Episode 0 identity must be an agent name and an integer seed: "
        "recorded agent 'random' with seed True",
    )


class AlternatingAgent:
    """A placement-agent stand-in whose masks are only 0 and 1.

    Those are exactly the integers JSON false and true compare equal to, so a
    verifier that compares recorded inputs with plain equality accepts a bool
    tamper and only the mask-type guard rejects it.
    """

    def __init__(self, *_):
        self.reset()

    def reset(self):
        self.frame = 0

    @property
    def done(self):
        return False

    def act(self, state):
        self.frame += 1
        return self.frame % 2


def test_suite_verification_checks_episode_input_types(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    monkeypatch.setattr(runner, "create_agent", lambda name, seed: AlternatingAgent())
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    assert [episode["inputs"] for episode in record["episodes"]] == [[1, 0] * 5] * 4
    # Positive control: the untampered record still verifies with no warnings.
    assert verify_run(path, lambda **_: SuiteGame()) == []

    def rejected(tamper, message):
        episodes = [{**episode, "inputs": tamper(episode["inputs"])} for episode in record["episodes"]]
        path.write_text(json.dumps({**record, "episodes": episodes}), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, lambda **_: SuiteGame())

    # JSON false/true compare equal to 0/1, so equality would replay this tampered
    # record without a difference and only the type check rejects it.
    rejected(lambda inputs: [bool(mask) for mask in inputs],
             "Recorded inputs in episode 0 must be a list of gameplay masks from 0 to 31")
    # A non-list input must be reported, not raise TypeError from len().
    rejected(lambda inputs: 5,
             "Recorded inputs in episode 0 must be a list of gameplay masks from 0 to 31")


def test_suite_record_formats_verify_under_their_own_piece_semantics(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    # New records carry the placed-piece count, one below the preview counter,
    # in every episode and in the summary, and no legacy key.
    assert [episode["pieces_placed"] for episode in record["episodes"]] == [5, 5, 5, 5]
    assert all("pieces" not in episode for episode in record["episodes"])
    assert record["summary"]["greedy"]["pieces_placed"]["mean"] == 5.0
    assert verify_run(path, lambda **_: SuiteGame()) == []

    # The older format recorded the preview counter under ``pieces``, one above
    # the placed count, in the episodes and the summary. It still verifies.
    legacy_episodes = [
        {"pieces": episode["pieces_placed"] + 1,
         **{key: value for key, value in episode.items() if key != "pieces_placed"}}
        for episode in record["episodes"]
    ]
    legacy = {**record, "episodes": legacy_episodes, "summary": runner._summarize(legacy_episodes)}
    assert legacy["summary"]["greedy"]["pieces"]["mean"] == 6.0
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, lambda **_: SuiteGame()) == []

    # A legacy record whose ``pieces`` holds the placed count instead of the
    # preview counter is rejected: the recorded value must replay as it was.
    legacy["episodes"][0]["pieces"] = 5
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(VerificationError, match="pieces: recorded 5, replayed 6"):
        verify_run(path, lambda **_: SuiteGame())


def test_suite_verification_rejects_a_boolean_piece_count(tmp_path, monkeypatch):
    """JSON ``false`` equals the integer 0, so a present count must be an int.

    With a lock period longer than the episode every episode replays to 0, and a
    saved ``false`` would pass both the per-episode equality and the summary
    comparison. The type guard rejects it.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    factory = lambda **_: SuiteGame(lock_period=100)
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert [episode["pieces_placed"] for episode in record["episodes"]] == [0, 0, 0, 0]
    assert verify_run(path, factory) == []
    episodes = [{**episode, "pieces_placed": False} for episode in record["episodes"]]
    path.write_text(json.dumps({**record, "episodes": episodes}), encoding="utf-8")
    with pytest.raises(
        VerificationError, match="Recorded pieces_placed in episode 0 must be an integer, not False"
    ):
        verify_run(path, factory)


class CountingGame(FakeGame):
    """A scripted stand-in whose lock, spawn and preview counters advance apart.

    One piece locks every ``lock_period`` frames, and ``in_flight`` leaves that
    many spawned pieces unlocked, as at a frame-limit stop. The engine's preview
    counter stays one above the spawned count. A terminal frame emits
    ``game_over`` beside its lock, the topping-out lock that places nothing, so a
    verifier that counts lock events instead of board writes is caught.
    """

    def __init__(self, *args, lock_period=1, in_flight=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_period = lock_period
        self.in_flight = in_flight
        self.locks = 0

    def step(self, mask):
        state, events = super().step(mask)
        locked = self.state.frame % self.lock_period == 0
        self.locks += int(locked)
        self.state.stats.pieces = self.locks + self.in_flight
        self.state.piece_count = self.state.stats.pieces + 1
        fields = {name: 0 for name in EVENT_NAMES}
        fields["locked"] = locked
        fields["game_over"] = bool(self.state.terminal)
        return state, SimpleNamespace(**fields)


def test_placed_piece_count_is_the_locked_count_not_the_preview_counter():
    """The reported count is the lock count; the preview counter is one above.

    ``CountingGame`` locks one piece per frame and leaves none in play, so the
    locked count equals the spawned count here while the engine's preview
    counter stays one above both. A runner that recorded the preview counter
    would report 5 here instead of 4.
    """
    config = parse_config({**BASE, "frame_limit": 4})
    game = CountingGame()
    episode = run_episode(config, lambda **_: game)
    assert episode["result"]["frame_count"] == 4
    assert episode["pieces_placed"] == 4 == game.locks
    assert game.state.piece_count == episode["pieces_placed"] + 1 == 5
    assert "pieces" not in episode


def test_frame_limit_stop_does_not_count_a_piece_that_never_locked():
    """A spawned but unlocked piece is not placed, so it is not counted.

    At a frame-limit stop the engine has spawned the active piece but no lock
    event has fired for it. The spawn counter would report 5 here; the lock
    count is 4.
    """
    config = parse_config({**BASE, "frame_limit": 4})
    game = CountingGame(in_flight=1)
    episode = run_episode(config, lambda **_: game)
    assert episode["pieces_placed"] == 4 == game.locks
    assert game.state.stats.pieces == 5
    assert game.state.piece_count == 6


def test_top_out_lock_that_writes_no_piece_is_not_counted():
    """The topping-out lock raises ``locked`` but places nothing.

    ``Game::lock`` emits ``locked`` before its ``fits`` check and writes the
    board only on success, so a game-over episode has one more lock event than
    placed pieces. Here three locks fire and the last ends the game, so two
    pieces were placed.
    """
    config = parse_config({**BASE, "frame_limit": 10})
    game = CountingGame(terminal_at=3)
    episode = run_episode(config, lambda **_: game)
    assert episode["result"]["stopping_reason"] == "game_over"
    assert episode["result"]["event_counts"]["locked"] == 3
    assert episode["result"]["event_counts"]["game_over"] == 1
    assert episode["pieces_placed"] == 2


def test_scripted_verification_compares_a_recorded_placed_piece_count(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    factory = lambda **_: CountingGame(in_flight=1)
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    # The writer records the locked count beside the result it replays; the frame
    # count is 4, the spawned count 5 and the preview counter 6.
    assert (record["pieces_placed"], record["result"]["frame_count"]) == (4, 4)
    assert "pieces" not in record
    assert verify_run(path, factory) == []

    def rejected(value, message):
        path.write_text(json.dumps({**record, "pieces_placed": value}), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, factory)

    rejected(5, "pieces_placed: recorded 5, replayed 4")  # the spawn count must not pass
    rejected(6, "pieces_placed: recorded 6, replayed 4")  # the preview counter must not pass
    rejected(None, "Recorded pieces_placed must be an integer, not None")
    rejected(True, "Recorded pieces_placed must be an integer, not True")

    # A record that carries the legacy key is an older record: it recorded the
    # preview counter under ``pieces`` and still verifies under that semantics.
    legacy = {key: value for key, value in record.items() if key != "pieces_placed"}
    legacy["pieces"] = 6
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, factory) == []
    legacy["pieces"] = 4  # the locked count must not pass the legacy comparison
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(VerificationError, match="pieces: recorded 4, replayed 6"):
        verify_run(path, factory)

    # A record that carries neither key is older still and keeps verifying.
    oldest = {key: value for key, value in legacy.items() if key != "pieces"}
    path.write_text(json.dumps(oldest), encoding="utf-8")
    assert verify_run(path, factory) == []


def test_scripted_verification_rejects_a_boolean_piece_count(tmp_path, monkeypatch):
    """JSON ``false`` equals the integer 0, so a present count must be an int.

    An episode stopped before its first lock replays to 0, and a saved ``false``
    would pass a plain equality check. The type guard rejects it.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    factory = lambda **_: CountingGame(lock_period=100, in_flight=1)
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["pieces_placed"] == 0
    assert verify_run(path, factory) == []
    path.write_text(json.dumps({**record, "pieces_placed": False}), encoding="utf-8")
    with pytest.raises(VerificationError, match="Recorded pieces_placed must be an integer, not False"):
        verify_run(path, factory)


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
