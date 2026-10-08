from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from block_stack_ai.agents import ScriptedAgent, parse_script
from block_stack_ai import agents as agents_module, engine, live as live_module, runner, tetris as tetris_module
from block_stack_ai.runner import (
    RunConfig,
    SuiteConfig,
    VerificationError,
    parse_config,
    run_and_save,
    run_episode,
    verify_run,
)
from block_stack_ai.tetris import weights_record as tetris_weights_record
from block_stack_ai.wellplan import weights_record as wellplan_weights_record


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
    orientation: int = 0
    x: int = 5


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
    assert record["format_version"] == runner.SUITE_FORMAT_VERSION
    assert [episode["pieces_placed"] for episode in record["episodes"]] == [5, 5, 5, 5]
    assert all("pieces" not in episode for episode in record["episodes"])
    assert record["summary"]["greedy"]["pieces_placed"]["mean"] == 5.0
    assert verify_run(path, lambda **_: SuiteGame()) == []

    # Deleting the count leaves a record of the current version without a section
    # its writer always emitted. That is not the legacy shape: the version says
    # the key is written, so its absence is reported rather than silently
    # comparing nothing.
    stripped = json.loads(json.dumps(record))
    for episode in stripped["episodes"]:
        del episode["pieces_placed"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"pieces_placed in episode 0: absent, but a record of this format version "
              r"always carries the placed-piece count",
    ):
        verify_run(path, lambda **_: SuiteGame())

    # The older format recorded the preview counter under ``pieces``, one above
    # the placed count, in the episodes and the summary. The legacy version never
    # emitted ``pieces_placed``, so that shape still verifies.
    legacy_episodes = [
        {"pieces": episode["pieces_placed"] + 1,
         **{key: value for key, value in episode.items() if key != "pieces_placed"}}
        for episode in record["episodes"]
    ]
    legacy = {**record, "format_version": runner.LEGACY_SUITE_FORMAT_VERSION,
              "episodes": legacy_episodes, "summary": runner._summarize(legacy_episodes)}
    assert legacy["summary"]["greedy"]["pieces"]["mean"] == 6.0
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, lambda **_: SuiteGame()) == []

    # A legacy record whose ``pieces`` holds the placed count instead of the
    # preview counter is rejected: the recorded value must replay as it was.
    legacy["episodes"][0]["pieces"] = 5
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(VerificationError, match="pieces: recorded 5, replayed 6"):
        verify_run(path, lambda **_: SuiteGame())


def test_verification_rejects_a_mixed_piece_count_schema(tmp_path, monkeypatch):
    """The summary reports the piece key the record's own episodes carry.

    The reviewer's counterexample: ``pieces_placed`` is stripped from each
    agent's first episode and from that agent's summary, while every later
    episode keeps its count. The summary used to pick its metric from the first
    episode of each group, so it re-derived a summary with no piece metric,
    matched the stripped record, and verified a mixed schema no writer emits —
    at the legacy version, where the count is not required. The key is now read
    from every episode, so that record is reported there too; a record that
    carries the count nowhere still verifies as the older shape, and at the
    current version the same strips are reported by the version rule.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []
    assert record["summary"]["random"]["pieces_placed"]["mean"] == 5.0
    stripped = json.loads(json.dumps(record))
    first_of_agent = {}
    for episode in stripped["episodes"]:
        first_of_agent.setdefault(episode["agent"], episode)
    for episode in stripped["episodes"]:
        if first_of_agent[episode["agent"]] is episode:
            del episode["pieces_placed"]
    for summary in stripped["summary"].values():
        del summary["pieces_placed"]
    # Two of the four episodes were stripped, one per agent: read the count from
    # every episode and the record is not the shape any writer emitted.
    mixed_schema = (r"piece count must be recorded on every episode of a record or on none: "
                    r"2 of 4 episodes carry pieces_placed, 0 carry pieces")

    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"pieces_placed in episode 0: absent, but a record of this format version "
              r"always carries the placed-piece count",
    ):
        verify_run(path, factory)

    legacy = json.loads(json.dumps(stripped))
    legacy["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(VerificationError, match=mixed_schema):
        verify_run(path, factory)

    # A record that carries the count nowhere is older still and verifies, with
    # no piece metric in its summary — the legacy shape the rule must keep.
    older = json.loads(json.dumps(stripped))
    older["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    for episode in older["episodes"]:
        episode.pop("pieces_placed", None)
    path.write_text(json.dumps(older), encoding="utf-8")
    assert verify_run(path, factory) == []
    assert all("pieces_placed" not in summary for summary in older["summary"].values())

    # And at the current version a summary that lost the count its episodes all
    # carry is reported as a deleted section, not silently re-derived.
    summary_only = json.loads(json.dumps(record))
    del summary_only["summary"]["random"]["pieces_placed"]
    path.write_text(json.dumps(summary_only), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.pieces_placed: absent from 0 of 4 episodes and 1 of 2 agent "
              r"summaries, but a record of this format version carries it on every one",
    ):
        verify_run(path, factory)


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
    assert record["format_version"] == runner.FORMAT_VERSION
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

    # Deleting the count leaves a record of the current version without the
    # section its writer always emits, which is reported rather than accepted as
    # an older shape: the version, not the absence, decides that.
    stripped = {key: value for key, value in record.items() if key != "pieces_placed"}
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"pieces_placed: absent, but a record of this format version always carries "
              r"the placed-piece count",
    ):
        verify_run(path, factory)

    # A record of a legacy version that carries the legacy key is an older
    # record: it recorded the preview counter under ``pieces`` and still verifies
    # under that semantics.
    legacy = {**stripped, "format_version": runner.LEGACY_FORMAT_VERSION, "pieces": 6}
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, factory) == []
    legacy["pieces"] = 4  # the locked count must not pass the legacy comparison
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(VerificationError, match="pieces: recorded 4, replayed 6"):
        verify_run(path, factory)

    # A legacy record that carries neither key is older still and keeps verifying.
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


@pytest.mark.parametrize(
    "frame_limit,field,value",
    [(10, "score", False), (10, "lines", False), (1, "frame_count", True)],
)
def test_suite_verification_rejects_a_boolean_result_number(
    tmp_path, monkeypatch, frame_limit, field, value
):
    """JSON ``false``/``true`` equal 0 and 1, so a 0- or 1-valued result field needs a type.

    The suite stand-in scores nothing, clears nothing, and records one frame under
    a one-frame limit, so each field replays to 0 or 1 and the saved boolean would
    pass a plain value comparison.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**SUITE, "frame_limit": frame_limit}), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    recorded = record["episodes"][0]["result"][field]
    assert type(recorded) is int and recorded == (1 if value else 0)
    assert verify_run(path, lambda **_: SuiteGame()) == []

    record["episodes"][0]["result"][field] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError, match=rf"Recorded episode 0 result\.{field} must be int, not {value!r}"
    ):
        verify_run(path, lambda **_: SuiteGame())


@pytest.mark.parametrize(
    "frame_limit,lock_period,field,value",
    [(10, 2, "game_over", False), (1, 1, "locked", True)],
)
def test_suite_verification_rejects_a_boolean_event_count(
    tmp_path, monkeypatch, frame_limit, lock_period, field, value
):
    """JSON ``false``/``true`` equal 0 and 1, so a 0- or 1-valued event count needs a type.

    ``game_over`` stays 0 while the game runs, while a one-frame limit with a lock
    every frame leaves ``locked`` at 1, so either boolean would pass a plain value
    comparison against the recorded count.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    factory = lambda **_: SuiteGame(lock_period=lock_period)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**SUITE, "frame_limit": frame_limit}), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    recorded = record["episodes"][0]["result"]["event_counts"][field]
    assert type(recorded) is int and recorded == (1 if value else 0)
    assert verify_run(path, factory) == []

    record["episodes"][0]["result"]["event_counts"][field] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=rf"Recorded episode 0 result\.event_counts\.{field} must be int, not {value!r}",
    ):
        verify_run(path, factory)


@pytest.mark.parametrize(
    "seeds,keys,value,expected_type",
    [
        ([1, 2, 3], ("score", "mean"), False, float),
        ([1, 2, 3], ("score", "median"), False, int),
        ([1, 2, 3], ("score", "min"), False, int),
        ([1, 2, 3], ("score", "max"), False, int),
        ([3], ("games",), True, int),
        ([3], ("stopping_reasons", "frame_limit"), True, int),
    ],
)
def test_suite_verification_rejects_a_boolean_summary_value(
    tmp_path, monkeypatch, seeds, keys, value, expected_type
):
    """JSON ``false``/``true`` equal 0, 0.0 and 1, so every summary leaf needs its type.

    Three seeds make the group odd, so the recorded ``median`` is an ``int`` while
    ``mean`` is a ``float``: a genuine record must verify with both, and a boolean
    saved in either place must not. A single seed puts a 1 in ``games`` and in the
    ``stopping_reasons`` count, which ``true`` compares equal to.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**SUITE, "seeds": seeds}), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    recorded = record["summary"]["greedy"]
    for key in keys:
        recorded = recorded[key]
    # The genuine value is numerically equal to the boolean that will replace it,
    # which is exactly why a plain equality accepted the tamper.
    assert type(recorded) is expected_type
    assert recorded == (1 if value else 0)
    assert verify_run(path, lambda **_: SuiteGame()) == []

    tampered = json.loads(json.dumps(record))
    leaf = tampered["summary"]["greedy"]
    for key in keys[:-1]:
        leaf = leaf[key]
    leaf[keys[-1]] = value
    path.write_text(json.dumps(tampered), encoding="utf-8")
    where = ".".join(("summary", "greedy", *keys))
    with pytest.raises(
        VerificationError,
        match=rf"Recorded {where} must be {expected_type.__name__}, not {value!r}",
    ):
        verify_run(path, lambda **_: SuiteGame())


def test_suite_verification_accepts_a_summary_median_of_int_type(tmp_path, monkeypatch):
    """A median of an odd-sized group is an ``int``; the type check follows the writer.

    ``_metric`` rounds ``statistics.median``, which returns an ``int`` for an odd
    number of games and a ``float`` for an even one, so a verifier that demanded a
    fixed ``float`` median would reject a genuine three-seed record.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**SUITE, "seeds": [1, 2, 3]}), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    summary = record["summary"]["greedy"]
    assert type(summary["score"]["median"]) is int
    assert type(summary["score"]["mean"]) is float
    assert verify_run(path, lambda **_: SuiteGame()) == []


def test_suite_verification_rejects_tampered_heuristic_metadata(tmp_path, monkeypatch):
    """The recorded weights must carry the writer's types and exactly its keys.

    ``weights_record()`` holds the float weights and the tie-break string beside
    the episodes. JSON ``true`` compares equal to the float ``1.0``, so a plain
    comparison certified a record whose ``lines_cleared`` weight no longer matched
    the implementation's; an integer ``1`` for that float and a boolean for the
    tie-break string slip through the same way. The heuristic mapping now goes
    through the type-and-key comparison the episodes and the summary already use.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    path = run_and_save(config_path, tmp_path / "runs", lambda **_: SuiteGame())
    record = json.loads(path.read_text(encoding="utf-8"))
    # The genuine weight is the float 1.0, numerically equal to the boolean below.
    assert type(record["heuristic"]["lines_cleared"]) is float
    assert record["heuristic"]["lines_cleared"] == 1.0
    # Positive control: the untampered record still verifies.
    assert verify_run(path, lambda **_: SuiteGame()) == []

    def rejected(tamper, message):
        tampered = json.loads(json.dumps(record))
        tamper(tampered["heuristic"])
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, lambda **_: SuiteGame())

    def weight_to_bool(heuristic):
        heuristic["lines_cleared"] = True

    def weight_to_int(heuristic):
        heuristic["lines_cleared"] = 1

    def tie_break_to_bool(heuristic):
        heuristic["tie_break"] = True

    def add_weight(heuristic):
        heuristic["extra_weight"] = 1.0

    rejected(weight_to_bool, r"Recorded heuristic\.lines_cleared must be float, not True")
    rejected(weight_to_int, r"Recorded heuristic\.lines_cleared must be float, not 1")
    rejected(tie_break_to_bool, r"Recorded heuristic\.tie_break must be str, not True")
    rejected(add_weight, r"Recorded heuristic keys .* do not match")


def test_scripted_verification_rejects_boolean_result_fields(tmp_path, monkeypatch):
    """JSON ``false`` equals the integer 0, so result fields need their written types.

    ``FakeGame`` scores nothing, clears nothing and emits no events, so every
    recorded number is 0 and a saved ``false`` passes a plain value comparison.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    factory = lambda **_: FakeGame()
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["result"]["score"] == 0
    assert record["result"]["event_counts"]["locked"] == 0
    assert verify_run(path, factory) == []

    def rejected(mutate, message):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, factory)

    def score_to_false(tampered):
        tampered["result"]["score"] = False

    def locked_to_false(tampered):
        tampered["result"]["event_counts"]["locked"] = False

    rejected(score_to_false, "Recorded result.score must be int, not False")
    rejected(locked_to_false, "Recorded result.event_counts.locked must be int, not False")


def test_verify_run_requires_the_written_integer_format_version(tmp_path, monkeypatch):
    """``verify_run`` dispatched on plain equality, which JSON coercion reaches.

    JSON ``true`` compares equal to the integer 1 and ``2.0`` to 2, while the
    writer records whole-numbered versions. A suite record whose
    ``format_version`` was edited from 2 to ``2.0`` therefore still routed to the
    suite verifier and verified (exit 0 on the retained record before the
    change), and an edited ``true`` (or ``1.0``) routed a v1 record to the
    scripted verifier, which verified it just the same. ``false``, ``null`` and
    ``"2"`` matched no version and were already rejected as unsupported.
    Every non-integer is now reported as one, and both genuine records still
    verify as the positive control.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )

    def rejected(path, record, factory, version):
        path.write_text(json.dumps({**record, "format_version": version}), encoding="utf-8")
        with pytest.raises(
            VerificationError,
            match=rf"Recorded format_version in .* must be an integer, not {version!r}",
        ):
            verify_run(path, factory)

    suite_factory = lambda **_: SuiteGame()
    config_path = tmp_path / "suite-config.json"
    config_path.write_text(json.dumps(SUITE), encoding="utf-8")
    suite_path = run_and_save(config_path, tmp_path / "runs", suite_factory)
    suite_record = json.loads(suite_path.read_text(encoding="utf-8"))
    assert suite_record["format_version"] == runner.SUITE_FORMAT_VERSION  # the writer's own type
    assert verify_run(suite_path, suite_factory) == []
    for version in (4.0, 2.0, 1.0, True, False, None, "2"):
        rejected(suite_path, suite_record, suite_factory, version)

    scripted_factory = lambda **_: FakeGame()
    config_path = tmp_path / "scripted-config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    scripted_path = run_and_save(config_path, tmp_path / "runs", scripted_factory)
    scripted_record = json.loads(scripted_path.read_text(encoding="utf-8"))
    assert scripted_record["format_version"] == 3
    assert verify_run(scripted_path, scripted_factory) == []
    for version in (3.0, 1.0, True, 2.0, False, None, "2"):
        rejected(scripted_path, scripted_record, scripted_factory, version)


def test_engine_version_warnings_reject_a_non_boolean_dirty_flag(tmp_path, monkeypatch):
    """JSON ``0`` equals ``False``, so a malformed dirty flag used to match silently.

    ``git_info`` records ``dirty`` as a boolean, or ``null`` when there is no Git
    checkout, so those are the only recorded forms. The engine fields stay
    advisory: a wrong type is reported as a difference, never raised, so a record
    that omits the field keeps verifying with the warning. Before the change the
    tampered flag below verified with no warnings at all, which is the same
    class of type-loose recorded comparison the discriminator guard closes.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(BASE), encoding="utf-8")
    factory = lambda **_: FakeGame()
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["versions"]["engine"] == {"commit": "abc123", "dirty": False, "kind": "committed"}
    assert verify_run(path, factory) == []  # positive control: a clean tree warns about nothing

    difference = "Engine Git version or dirty status differs from the recorded run."
    working_tree = (
        "The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source."
    )

    def verify_warnings(engine):
        tampered = json.loads(json.dumps(record))
        tampered["versions"]["engine"] = engine
        path.write_text(json.dumps(tampered), encoding="utf-8")
        return verify_run(path, factory)

    # The numbers compare equal to the booleans the writer records, which is why
    # plain equality accepted them; a missing field is an older record and still
    # warns instead of raising.
    assert verify_warnings({**record["versions"]["engine"], "dirty": 0}) == [difference]
    assert verify_warnings({**record["versions"]["engine"], "dirty": 1}) == [difference]
    assert verify_warnings({"commit": "abc123", "kind": "committed"}) == [difference]
    assert verify_warnings({**record["versions"]["engine"], "commit": 0}) == [difference]

    # The null the writer records without a Git checkout is not a difference.
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": None, "dirty": None, "kind": "unversioned"}
    )
    assert verify_warnings({"commit": None, "dirty": None, "kind": "unversioned"}) == [working_tree]


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


CLEAR_SIZES = {"singles": 1, "doubles": 1, "triples": 1, "tetrises": 1}


class ClearGame:
    """A scripted stand-in that reports the engine's per-step clear size.

    Each step emits the next entry of ``clears`` as the ``lines_cleared`` event
    and adds it to ``state.lines``, and locks one piece, so the histogram, the
    line total and the placed count can be checked against one another. The same
    sequence is replayed from a fresh instance for every episode, so a suite
    summary of two agents over two seeds sums four identical histograms.
    """

    def __init__(self, clears, **_):
        self.state = SuiteState()
        self.clears = list(clears)
        self.index = 0
        self.locks = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def state_hash(self):
        return self.state.frame

    def step(self, mask):
        cleared = self.clears[self.index]
        self.index += 1
        self.state.frame += 1
        self.state.lines += cleared
        self.locks += 1
        self.state.stats.pieces = self.locks
        self.state.piece_count = self.locks + 1
        fields = {name: 0 for name in EVENT_NAMES}
        fields["locked"] = True
        fields["lines_cleared"] = cleared
        return self.state, SimpleNamespace(**fields)


SCRIPTED_CLEARS = {**BASE, "frame_limit": 5, "script": [{"mask": 0, "frames": 5}]}


def test_clear_sizes_are_tallied_from_the_engine_clear_result():
    """The per-episode histogram is the engine's own per-step clear size.

    The stand-in reports one single, one double, one triple, one four-line clear
    and one empty step. The histogram must count exactly those, and its rows must
    add up to the ``lines_cleared`` total the runner already accumulates and to
    the state's line count.
    """
    config = parse_config(SCRIPTED_CLEARS)
    episode = run_episode(config, lambda **_: ClearGame([1, 2, 4, 0, 3]))
    sizes = episode["clear_sizes"]
    assert sizes == CLEAR_SIZES
    assert episode["result"]["lines"] == 10
    assert episode["result"]["event_counts"]["lines_cleared"] == 10
    assert (1 * sizes["singles"] + 2 * sizes["doubles"]
            + 3 * sizes["triples"] + 4 * sizes["tetrises"]) == 10
    assert episode["pieces_placed"] == 5


def test_clear_size_recording_rejects_a_size_the_engine_cannot_report():
    """A clear size outside 0..4 is a broken binding, not a play outcome.

    Silently dropping it would leave the histogram and the line total
    disagreeing, which is exactly what the verifier would then reject.
    """
    config = parse_config(SCRIPTED_CLEARS)
    with pytest.raises(ValueError, match="impossible clear size: 5"):
        run_episode(config, lambda **_: ClearGame([5, 0, 0, 0, 0]))


def _clear_suite(tmp_path, monkeypatch, clears=(1, 2, 4, 0, 3)):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({**SUITE, "frame_limit": len(clears)}), encoding="utf-8")
    factory = lambda **_: ClearGame(clears)
    path = run_and_save(config_path, tmp_path / "runs", factory)
    return path, factory, json.loads(path.read_text(encoding="utf-8"))


def test_suite_summary_totals_the_clear_sizes_per_agent(tmp_path, monkeypatch):
    """Each agent's summary carries the totals its episodes recorded."""
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert len(record["episodes"]) == 4
    for episode in record["episodes"]:
        assert episode["clear_sizes"] == CLEAR_SIZES
    for name in ("greedy", "random"):
        assert record["summary"][name]["clear_sizes"] == {
            field: 2 * count for field, count in CLEAR_SIZES.items()
        }
    assert verify_run(path, factory) == []


def test_records_written_before_the_clear_size_metric_still_verify(tmp_path, monkeypatch):
    """A record that predates the histogram is declared by its version and verifies.

    Both formats are covered: the suite record loses the per-episode field and
    the summary section, the scripted record loses the top-level field, and both
    still verify at the legacy version, whose writer emitted the histogram nowhere.
    The same records at the current version are reported instead: the version is
    the marker that tells an older record from a section deleted after the fact, so
    an absent section never has to stand for both.
    """
    suite_path, suite_factory, suite_record = _clear_suite(tmp_path, monkeypatch)
    legacy = json.loads(json.dumps(suite_record))
    legacy["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    for episode in legacy["episodes"]:
        episode.pop("clear_sizes")
    for summary in legacy["summary"].values():
        summary.pop("clear_sizes")
    suite_path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(suite_path, suite_factory) == []

    current = json.loads(json.dumps(suite_record))
    for episode in current["episodes"]:
        episode.pop("clear_sizes")
    for summary in current["summary"].values():
        summary.pop("clear_sizes")
    suite_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"episode 0 clear_sizes: absent, but a record of this format version always "
              r"carries it",
    ):
        verify_run(suite_path, suite_factory)

    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "scripted-config.json"
    config_path.write_text(json.dumps(SCRIPTED_CLEARS), encoding="utf-8")
    factory = lambda **_: ClearGame([1, 2, 4, 0, 3])
    scripted_path = run_and_save(config_path, tmp_path / "runs", factory)
    scripted_record = json.loads(scripted_path.read_text(encoding="utf-8"))
    scripted_legacy = {key: value for key, value in scripted_record.items()
                       if key != "clear_sizes"}
    scripted_legacy["format_version"] = runner.LEGACY_FORMAT_VERSION
    scripted_path.write_text(json.dumps(scripted_legacy), encoding="utf-8")
    assert verify_run(scripted_path, factory) == []

    scripted_stripped = {key: value for key, value in scripted_record.items()
                         if key != "clear_sizes"}
    scripted_path.write_text(json.dumps(scripted_stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"clear_sizes: absent, but a record of this format version always carries it",
    ):
        verify_run(scripted_path, factory)


def test_a_summary_reports_exactly_the_sections_its_episodes_carry(tmp_path, monkeypatch):
    """A legacy record's summary re-derives without the histogram it never recorded.

    The per-agent totals are summed from the episodes, so a record whose episodes
    carry no histogram must re-derive a summary that carries none either.
    Experiment 002's own replay probe compares the summary it re-derives from a
    record's episodes with the **recorded** summary, so a synthesized all-zero
    section — totals for clear sizes no episode recorded — rejects a legacy record
    that experiment still publishes and that `verify` accepts, because the
    verifier excludes the section from the base it compares and lets its own
    presence rule report the absence. Both directions are pinned here: the
    comparison 002 makes, and this tree's acceptance of the same record.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert runner._summarize(record["episodes"]) == record["summary"]

    legacy = json.loads(json.dumps(record))
    legacy["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    for episode in legacy["episodes"]:
        episode.pop("clear_sizes")
    for summary in legacy["summary"].values():
        summary.pop("clear_sizes")
    for name, summary in legacy["summary"].items():
        assert "clear_sizes" not in summary, name
    # The claim Experiment 002's probe makes, and the reason a synthesized
    # section cannot stand: the episodes' own clear sizes were never recorded, so
    # the totals it would report are a measurement no run made.
    assert runner._summarize(legacy["episodes"]) == legacy["summary"]
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, factory) == []

    # The converse shape, which no writer emits: the section survives in the
    # summary while every episode lost it. It is reported as that missing
    # per-episode field, not compared against a section the replay cannot derive.
    summary_only = json.loads(json.dumps(record))
    for episode in summary_only["episodes"]:
        episode.pop("clear_sizes")
    path.write_text(json.dumps(summary_only), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"episode 0 clear_sizes: absent, but a record of this format version always "
              r"carries it",
    ):
        verify_run(path, factory)

    # Declared legacy, the same record is a partial presence: the summary kept a
    # section no episode carries, which the suite-wide rule reports rather than
    # the per-agent comparison indexing a section the replay cannot derive.
    summary_only["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(summary_only), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.clear_sizes: the clear-size histogram must be recorded on every "
              r"episode and every agent summary, or on none: 0 of 4 episodes and 2 of 2 "
              r"agent summaries carry it",
    ):
        verify_run(path, factory)


def test_verification_compares_a_present_clear_size_histogram(tmp_path, monkeypatch):
    """A present histogram is compared with the writer's type and key rules.

    The replay re-derives the counts, so a changed count, a missing key, an
    extra key and a JSON boolean in a count are each reported; the summary total
    is checked with the same rules.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []

    def rejected(tamper, message):
        tampered = json.loads(json.dumps(record))
        path.write_text(json.dumps(tamper(tampered)), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, factory)

    def changed_count(tampered):
        tampered["episodes"][0]["clear_sizes"]["tetrises"] = 0
        return tampered

    def boolean_count(tampered):
        tampered["episodes"][0]["clear_sizes"]["singles"] = True
        return tampered

    def missing_key(tampered):
        del tampered["episodes"][0]["clear_sizes"]["triples"]
        return tampered

    def extra_key(tampered):
        tampered["episodes"][0]["clear_sizes"]["quintuples"] = 0
        return tampered

    def summary_total(tampered):
        tampered["summary"]["greedy"]["clear_sizes"]["doubles"] = 1
        return tampered

    rejected(changed_count, r"episode 0 clear_sizes\.tetrises: recorded 0, replayed 1")
    rejected(boolean_count, r"episode 0 clear_sizes\.singles must be int, not True")
    rejected(missing_key, r"episode 0 clear_sizes keys .* do not match")
    rejected(extra_key, r"episode 0 clear_sizes keys .* do not match")
    rejected(summary_total, r"summary\.greedy\.clear_sizes\.doubles: recorded 1, replayed 2")


def test_verification_rejects_a_summary_that_omits_the_histogram_its_episodes_record(
    tmp_path, monkeypatch
):
    """A summary's totals are required at the current version, and all-or-nothing before it.

    The totals are summed from the episodes, so dropping only the summary
    section would verify yet leave ``report``'s reader with no per-agent totals
    for an agent whose episodes carry them. At the current version the missing
    section is reported as such; a record that says it predates the histogram is
    judged by the suite-wide rule instead, which rejects the partial presence: the
    histogram is recorded on every episode and every agent summary, or nowhere.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []
    del record["summary"]["random"]["clear_sizes"]
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.clear_sizes: absent from 0 of 4 episodes and 1 of 2 agent "
              r"summaries, but a record of this format version carries it on every one",
    ):
        verify_run(path, factory)

    record["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.clear_sizes: the clear-size histogram must be recorded on every "
              r"episode and every agent summary, or on none: 4 of 4 episodes and 1 of 2 "
              r"agent summaries carry it",
    ):
        verify_run(path, factory)


def test_verification_rejects_a_partially_histogramned_agent(tmp_path, monkeypatch):
    """The histogram is all-or-nothing across the whole suite, not per agent.

    A record with one random episode carrying the histogram and one not, while
    the other agent's episodes and summary keep theirs, would otherwise verify
    with a histogram that covers only part of the suite's lines. At the current
    version the stripped episode is reported by the required-section rule; the
    same record declared legacy is reported by the suite-wide rule.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    del record["episodes"][0]["clear_sizes"]
    del record["summary"]["random"]["clear_sizes"]
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"episode 0 clear_sizes: absent, but a record of this format version always "
              r"carries it",
    ):
        verify_run(path, factory)

    record["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.clear_sizes: the clear-size histogram must be recorded on every "
              r"episode and every agent summary, or on none: 3 of 4 episodes and 1 of 2 "
              r"agent summaries carry it",
    ):
        verify_run(path, factory)


def test_verification_rejects_a_suite_wide_partial_histogram(tmp_path, monkeypatch):
    """One agent stripped while another keeps the histogram is a rejected record.

    The totals are summed from the episodes, so a record that stripped the
    histogram from one agent's episodes and summary would verify under a
    per-agent rule yet report only the other agent's clear sizes. The same record
    with the histogram stripped everywhere is a legacy record — at the legacy
    version, which never recorded it — and still verifies.
    """
    path, factory, record = _clear_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []

    stripped = json.loads(json.dumps(record))
    for episode in stripped["episodes"]:
        if episode["agent"] == "random":
            del episode["clear_sizes"]
    del stripped["summary"]["random"]["clear_sizes"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"episode 0 clear_sizes: absent, but a record of this format version always "
              r"carries it",
    ):
        verify_run(path, factory)

    stripped["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"summary\.clear_sizes: the clear-size histogram must be recorded on every "
              r"episode and every agent summary, or on none: 2 of 4 episodes and 1 of 2 "
              r"agent summaries carry it",
    ):
        verify_run(path, factory)

    legacy = json.loads(json.dumps(stripped))
    del legacy["summary"]["greedy"]["clear_sizes"]
    for episode in legacy["episodes"]:
        episode.pop("clear_sizes", None)
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, factory) == []


@dataclass
class ChoiceState:
    """The placement-agent fields of an engine state, on an empty board.

    The board is empty, so the reachable set the lookahead and Tetris agents
    enumerate is a real one rather than the empty set a full board yields. The
    stand-in ignores the mask it is given, so the episode replays identically
    whatever the agent chooses.
    """

    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"
    piece_count: int = 0
    current_piece: str = "T"
    next_piece: str = "O"
    board: object = ((0,) * 10,) * 20
    hidden_rows: object = ((0,) * 10,) * 2
    orientation: int = 0
    x: int = 5
    level: int = 18
    start_level: int = 18
    first_delay_remaining: int = 0
    ruleset: str = "classic_ntsc_extended"
    mode: str = "endless"


class ChoiceGame:
    """A stand-in whose suite episodes carry a real clear-size histogram.

    One piece locks every step, and each step reports the next entry of ``clears``
    as the engine's per-step clear size, so a two-frame episode records one single
    and one double and each agent's summary totals its own episode's histogram.
    """

    def __init__(self, clears=(1, 2), **_):
        self.state = ChoiceState()
        self.clears = list(clears)
        self.index = 0
        self.locks = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def state_hash(self):
        return self.state.frame

    def step(self, mask):
        cleared = self.clears[self.index]
        self.index += 1
        self.state.frame += 1
        self.state.lines += cleared
        self.locks += 1
        self.state.piece_count = self.locks + 1
        fields = {name: 0 for name in EVENT_NAMES}
        fields["locked"] = True
        fields["lines_cleared"] = cleared
        return self.state, SimpleNamespace(**fields)


# The experiment's own agent pair over one seed: the frozen lookahead agent and
# the Tetris agent, whose objective the suite record must declare.
OBJECTIVE_SUITE = {**SUITE, "frame_limit": 2, "seeds": [1], "agents": ["lookahead", "tetris"]}


def _objective_suite(tmp_path, monkeypatch, agents=("lookahead", "tetris")):
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info", lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({**OBJECTIVE_SUITE, "agents": list(agents)}), encoding="utf-8"
    )
    factory = lambda **_: ChoiceGame()
    path = run_and_save(config_path, tmp_path / "runs", factory)
    return path, factory, json.loads(path.read_text(encoding="utf-8"))


def test_suite_records_the_objective_of_the_tetris_agent(tmp_path, monkeypatch):
    """A suite that uses the Tetris agent declares the objective it scores by.

    The frozen heuristic mapping is recorded for every suite, because every
    placement agent scores through it; the Tetris agent's choices come from a
    second objective, so its suite records that objective too: the module that
    declares it, the weights it publishes, and the source identity of the modules
    its decisions are computed from. A suite without the agent declares none. The
    record's version is what decides whether the section may be absent: the current
    version's writer always emits it for this suite, so deleting it is reported,
    while the same JSON at the legacy version — a record that predates the
    section — keeps verifying.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    assert record["format_version"] == runner.SUITE_FORMAT_VERSION
    assert record["objective"] == {
        "module": "block_stack_ai.tetris",
        "weights": tetris_weights_record(),
        "sources": runner._objective_sources(runner._IDENTITY_DISPATCH),
    }
    assert verify_run(path, factory) == []

    # Deleting the section without touching the version must be reported: an
    # absent optional section cannot stand for both a record that predates it and
    # a current record whose section was removed.
    stripped = json.loads(json.dumps(record))
    del stripped["objective"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"objective: absent, but a record of this format version declares the "
              r"objective of the agent whose placements it replayed",
    ):
        verify_run(path, factory)

    # The same JSON declared legacy is a record predating the section, and keeps
    # verifying, which is the compatibility side of the same rule.
    legacy = json.loads(json.dumps(stripped))
    legacy["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(path, factory) == []

    greedy_path, greedy_factory, greedy_record = _objective_suite(
        tmp_path, monkeypatch, agents=("greedy",)
    )
    assert "objective" not in greedy_record
    assert verify_run(greedy_path, greedy_factory) == []


def test_the_objective_identity_is_the_source_of_the_modules_it_runs(tmp_path, monkeypatch):
    """The identity names every module the objective's decisions are computed from.

    A digest of the declaring module alone would leave the same hole one level
    deeper — the frozen geometry, the board model and Experiment 002's
    reachable-set enumeration all decide the objective's values — so the recorded
    identity is the sha256 of each of those modules' own source, discovered from
    the objective's namespace. The agent wrapper belongs to that set too and is
    not reachable from the objective's namespace at all: it imports the objective
    rather than the other way round, and it is the code that hands the objective
    every state parameter it reads and executes the placement it returns. Each
    recorded digest is checked against the file the interpreter loaded, so the
    mapping is the source it claims to be rather than a constant the writer and
    verifier could agree on while both were wrong.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    sources = record["objective"]["sources"]
    assert set(sources) == {
        "block_stack_ai.tetris",
        "block_stack_ai.heuristic",
        "block_stack_ai.pathaware",
        "block_stack_ai.pieces",
        "block_stack_ai.agents",
        # The current walk seeds the dispatch that decides which implementation every
        # agent is built from, and the package modules its own code reaches.
        "block_stack_ai.engine",
        "block_stack_ai.runner",
    }
    assert set(runner._objective_sources(runner._IDENTITY_CHOICE)) == {
        "block_stack_ai.tetris",
        "block_stack_ai.heuristic",
        "block_stack_ai.pathaware",
        "block_stack_ai.pieces",
        "block_stack_ai.agents",
    }
    for name, digest in sources.items():
        assert digest == hashlib.sha256(
            Path(sys.modules[name].__file__).read_bytes()).hexdigest(), name
    assert sources["block_stack_ai.tetris"] == hashlib.sha256(
        Path(tetris_module.__file__).read_bytes()).hexdigest()
    assert verify_run(path, factory) == []


def test_suite_records_the_objective_of_the_configured_agent(tmp_path, monkeypatch):
    """The declared objective follows the configured agent, not one hard-wired module.

    The section names the module that declares the objective of the agent the
    suite selected, with that objective's weights and the identity of the modules
    its choices run. The identity walks *that* objective and excludes its
    sibling's: the shared agent module imports every objective, so without the
    exclusion a well-plan record would be invalidated by an edit to the Tetris
    objective, whose code no plan choice runs. A section naming the other
    objective is reported rather than accepted as a valid objective of a
    different agent, and a configuration that names two such agents is refused
    before any record exists, because a record carries one section of this shape.
    """
    path, factory, record = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris_plan"))
    assert record["format_version"] == runner.SUITE_FORMAT_VERSION
    assert record["objective"] == {
        "module": "block_stack_ai.wellplan",
        "weights": wellplan_weights_record(),
        "sources": runner._objective_sources(agent="tetris_plan"),
    }
    # The plan's identity covers the objective module, the frozen board model and
    # reachable set it calls, the wrapper that drives it, and the module that
    # selects its implementation — the runner's dispatch, whose ``build_agent`` and
    # ``DECLARED_OBJECTIVES`` decide that ``wellplan`` builds this agent at all.
    # The walk from that module also reaches the game factory it holds, which is
    # the code that creates the state every choice reads.
    assert set(record["objective"]["sources"]) == {
        "block_stack_ai.wellplan",
        "block_stack_ai.heuristic",
        "block_stack_ai.pathaware",
        "block_stack_ai.pieces",
        "block_stack_ai.agents",
        "block_stack_ai.engine",
        "block_stack_ai.runner",
    }
    assert verify_run(path, factory) == []

    # The sibling's objective is not this agent's: a record that names it is a
    # difference with the replayed module, not an acceptable declaration.
    tampered = json.loads(json.dumps(record))
    tampered["objective"]["module"] = "block_stack_ai.tetris"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"objective\.module: recorded 'block_stack_ai\.tetris', "
              r"replayed 'block_stack_ai\.wellplan'",
    ):
        verify_run(path, factory)

    # A plan suite's deleted section is reported at the version that always
    # records it, exactly as the Tetris agent's is.
    stripped = json.loads(json.dumps(record))
    del stripped["objective"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective: absent"):
        verify_run(path, factory)


def test_a_record_cannot_be_relabelled_below_the_version_that_introduced_its_agent(
    tmp_path, monkeypatch
):
    """The objective's required-ness cannot be escaped by claiming an older writer.

    The section requirements are read from the record's own ``format_version``, so
    a plan record relabelled to a version before the objective section existed
    verified with its objective deleted — and, at the versions whose writer
    recorded the objective but no identity, with the identity behind it deleted
    too: the agent name a suite may configure is not version-gated, so nothing
    else noticed. The writer that could have configured an agent is a property of
    that agent, so a record's own declared agent pins the oldest version it may
    claim; every older relabel is reported before any section is compared. The
    Tetris agent's version-2 compatibility is unchanged, because its own version-2
    writer already built it and wrote no objective.
    """
    path, factory, record = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris_plan"))
    assert verify_run(path, factory) == []
    # The floor is the version Experiment 004's writer emitted, when the plan agent
    # was introduced. A later writer that moves ``SUITE_FORMAT_VERSION`` must not
    # move this value: the version-6 plan records it emitted still have to verify.
    assert runner.DECLARED_OBJECTIVES[runner.PLAN_AGENT].introduced_in == 6
    assert 6 <= runner.SUITE_FORMAT_VERSION

    stripped_objective = json.loads(json.dumps(record))
    del stripped_objective["objective"]
    stripped_identity = json.loads(json.dumps(record))
    del stripped_identity["objective"]["sources"]

    # Every version whose writer never knew the plan agent is an impossible claim,
    # whether the objective is present or not: the relabel itself is the edit.
    for version in (runner.LEGACY_SUITE_FORMAT_VERSION, runner.PRIOR_SUITE_FORMAT_VERSION,
                    runner.OUTWARD_IDENTITY_SUITE_FORMAT_VERSION):
        for edited in (stripped_objective, stripped_identity, record):
            relabelled = json.loads(json.dumps(edited))
            relabelled["format_version"] = version
            path.write_text(json.dumps(relabelled), encoding="utf-8")
            with pytest.raises(VerificationError,
                               match=r"format_version \d+ .*predates the agent"):
                verify_run(path, factory)

    # At the version whose writer introduced it, both sections are required.
    path.write_text(json.dumps(stripped_objective), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective: absent"):
        verify_run(path, factory)
    path.write_text(json.dumps(stripped_identity), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective\.sources: absent"):
        verify_run(path, factory)

    # The Tetris agent is the other case: the version-2 writer already built it and
    # wrote no objective, so that relabel is genuine writer output and verifies.
    tetris_path, tetris_factory, tetris_record = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris"))
    assert runner.DECLARED_OBJECTIVES[runner.TETRIS_AGENT].introduced_in == \
        runner.LEGACY_SUITE_FORMAT_VERSION
    legacy = json.loads(json.dumps(tetris_record))
    del legacy["objective"]
    legacy["format_version"] = runner.LEGACY_SUITE_FORMAT_VERSION
    tetris_path.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_run(tetris_path, tetris_factory) == []


def test_the_two_declared_objectives_keep_separate_identities():
    """Each objective's identity covers its own code and not its sibling's.

    Both agents are driven by the same agent module, which imports both
    objectives, so a walk that followed every import would put the plan's module
    into the Tetris identity and the Tetris module into the plan's. That would
    make one objective's record fail under an edit to the other's code, which no
    choice of the first ever runs; the walk therefore excludes the other declared
    objectives. The version-6 Tetris identity is the five modules that version's
    writer recorded — the retained fixture and Experiment 003's capture are compared
    against that shape — while the current walk names the module that selects each
    agent's implementation, so the Tetris module itself is covered and the plan's
    module is not, in either direction.
    """
    current_tetris = runner._objective_sources(runner._IDENTITY_DISPATCH)
    assert "block_stack_ai.wellplan" not in current_tetris
    assert "block_stack_ai.tetris" not in runner._objective_sources(
        runner._IDENTITY_DISPATCH, agent="tetris_plan")
    plan_identity = runner._objective_sources(runner._IDENTITY_DISPATCH, agent="tetris_plan")
    assert "block_stack_ai.runner" in plan_identity
    assert runner._choice_driver("tetris_plan", runner._IDENTITY_DISPATCH) is \
        sys.modules["block_stack_ai.runner"]
    assert runner._choice_driver("tetris", runner._IDENTITY_DISPATCH) is \
        sys.modules["block_stack_ai.runner"]
    # The version-6 walk named the shared factory for the Tetris agent instead, which
    # is the shape those records are compared against: the writer's own version keys
    # it, and `_SUITE_FORMAT_VERSIONS` is what the verifier reads.
    version_6 = runner._objective_sources(runner._IDENTITY_CHOICE)
    assert "block_stack_ai.runner" not in version_6
    assert set(version_6) == {"block_stack_ai.tetris", "block_stack_ai.heuristic",
                              "block_stack_ai.pathaware", "block_stack_ai.pieces",
                              "block_stack_ai.agents"}
    assert runner._choice_driver("tetris", runner._IDENTITY_CHOICE) is agents_module
    assert runner._choice_driver("tetris_plan", runner._IDENTITY_CHOICE) is \
        sys.modules["block_stack_ai.runner"]
    assert "block_stack_ai.runner" in current_tetris
    assert "block_stack_ai.wellplan" not in current_tetris
    # The provenance recorder is the one package module the walk excludes, and it
    # is excluded because it cannot record its own load: it is the module that
    # installs the recorder. Its digest is therefore not part of any identity, and
    # the writer's view of it is unavailable rather than a later read of the file —
    # which is what makes the exclusion the honest shape instead of a silent gap.
    recorder = sys.modules["block_stack_ai.sourceidentity"]
    assert recorder.__name__ not in plan_identity
    assert recorder.__name__ not in current_tetris
    with pytest.raises(VerificationError, match="did not load through the package's own"):
        runner._module_source_digest(recorder, loaded=True)
    assert runner._module_source_digest(recorder, loaded=False) == hashlib.sha256(
        Path(recorder.__file__).read_bytes()).hexdigest()
    assert runner._declared_agents(("lookahead", "tetris_plan")) == ("tetris_plan",)
    assert runner._declared_agents(("greedy", "random")) == ()


def test_the_live_identity_adds_the_module_that_drives_the_session():
    """The live suite format's walk covers the controller that hands over observations.

    The live session drives the same agents a headless suite does, but every
    observation reaches the agent through ``LiveSession.receive`` and every mask it
    returns is executed there. That module imports the runner rather than the other
    way round, so neither the objective walk nor the dispatch walk can reach it, and
    a change to ``receive`` that preserved the replayed masks stayed invisible. The
    live writer emits a new format version — 8 — whose objective identity adds the
    live-driving module to the dispatch-seeded walk, and whose records always carry
    a ``controller`` section seeded from the live module alone, so the greedy,
    random and lookahead agents, which declare no objective, are covered too. The
    shapes are keyed by the record's own version, so the headless walks are exactly
    what they were and a headless record written now carries the identity it always
    carried.
    """
    assert runner._SUITE_FORMAT_VERSIONS[runner.LIVE_SUITE_FORMAT_VERSION] == (
        True, runner._IDENTITY_LIVE, True)
    assert runner._SUITE_FORMAT_VERSIONS[runner.SUITE_FORMAT_VERSION] == (
        True, runner._IDENTITY_DISPATCH, False)
    assert runner.LIVE_SUITE_FORMAT_VERSION > runner.SUITE_FORMAT_VERSION
    dispatch = runner._objective_sources(runner._IDENTITY_DISPATCH)
    live = runner._objective_sources(runner._IDENTITY_LIVE)
    assert set(live) == set(dispatch) | {live_module.__name__}
    assert live[live_module.__name__] == hashlib.sha256(
        Path(live_module.__file__).read_bytes()).hexdigest()
    # The controller's own walk starts from the live module and stops before the
    # declared objectives, because the agents that need it declare none.
    controller = runner._objective_sources(runner._IDENTITY_CONTROLLER)
    assert live_module.__name__ in controller
    assert "block_stack_ai.tetris" not in controller
    assert "block_stack_ai.wellplan" not in controller
    assert set(controller) == {
        live_module.__name__, "block_stack_ai.agents", "block_stack_ai.engine",
        "block_stack_ai.heuristic", "block_stack_ai.pathaware",
        "block_stack_ai.pieces", "block_stack_ai.runner",
    }
    assert runner._controller_identity()["module"] == live_module.__name__
    # The headless walks — and the unversioned default Experiment 003's probe and
    # capture mean — never name the live module.
    for shape in (runner._IDENTITY_DISPATCH, runner._IDENTITY_CHOICE,
                  runner._IDENTITY_OUTWARD):
        assert live_module.__name__ not in runner._objective_sources(shape)
    assert live_module.__name__ not in runner._objective_sources()
    # The live walk still seeds the dispatch for every declared agent, because the
    # session builds its agent through the same dispatch a headless run does.
    for agent in ("tetris", "tetris_plan"):
        assert runner._choice_driver(agent, runner._IDENTITY_LIVE) is runner
        assert live_module.__name__ in runner._objective_sources(
            runner._IDENTITY_LIVE, agent=agent)


def test_a_change_to_the_dispatch_that_kept_the_choices_is_caught(tmp_path, monkeypatch):
    """The module that selects the plan's implementation is part of its identity.

    The reviewer's finding: the walk seeded the objective module and the module
    that *builds* the agent, so for the plan those two seeds were the same module
    and the runner's dispatch — the code that decides ``tetris_plan`` is built by
    ``wellplan`` at all — appeared in no record's identity. A change there that
    happened to replay the same inputs was therefore invisible. The plan's identity
    now covers that module, so the same record with the dispatcher's bytes changed
    is reported, while the unchanged module leaves the record verifying with only
    the engine's working-tree warning.
    """
    path, factory, record = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris_plan"))
    runner_digest = hashlib.sha256(Path(runner.__file__).read_bytes()).hexdigest()
    assert record["objective"]["sources"]["block_stack_ai.runner"] == runner_digest
    assert verify_run(path, factory) == []

    mutated = tmp_path / "runner-changed.py"
    mutated.write_bytes(Path(runner.__file__).read_bytes() + b"\n# dispatch changed\n")
    with monkeypatch.context() as patch:
        patch.setattr(runner, "__file__", str(mutated))
        with pytest.raises(
            VerificationError,
            match=r"objective\.sources\.block_stack_ai\.runner: recorded "
                  rf"'{runner_digest}', replayed '[0-9a-f]{{64}}'",
        ):
            verify_run(path, factory)


def test_the_dispatcher_bound_is_derived_from_the_retained_artifacts(monkeypatch):
    """The version-keyed coverage is re-derived, and its unversioned form ruled out.

    The reviewer's finding asked for a wider identity shape that covers the
    dispatcher for *every* declared agent, which needs a new format version: the
    retained artifacts of Experiment 003 — its capture and the frozen fixture —
    record the Tetris identity as the five modules the version-6 writer walked, so
    widening the shape in place would stop them verifying. Both halves are derived
    here rather than asserted: the current walk covers the dispatch for the Tetris
    agent as well as the plan, the version-6 walk does not, the fixture's keys are
    the version-6 keys, and Experiment 003's retained ``record_format_versions``
    prose is generated from the writer's constants and was regenerated when the
    version moved. The retained block has to be this derivation, so a stale
    statement about who covers the dispatcher cannot pass.
    """
    probe = _load_plan_probe("exp004_plan_bound_probe")
    derived = probe.dispatcher_bound()
    assert derived["current_choice_driver"] == {"tetris": "block_stack_ai.runner",
                                                "tetris_plan": "block_stack_ai.runner"}
    assert derived["version_6_choice_driver"] == {"tetris": "block_stack_ai.agents",
                                                  "tetris_plan": "block_stack_ai.runner"}
    assert derived["plan_identity_covers"] is True
    assert derived["current_tetris_identity_covers"] is True
    assert derived["version_6_tetris_identity_covers"] is False
    assert derived["version_6_format_version"] == 6  # the retained writer's version
    assert derived["current_format_version"] == runner.SUITE_FORMAT_VERSION
    assert runner.SUITE_FORMAT_VERSION > derived["version_6_format_version"]
    assert derived["version_6_tetris_identity_keys"] == derived["fixture_identity_keys"]
    assert "block_stack_ai.runner" in derived["current_tetris_identity_keys"]
    assert derived["experiment_003_version_prose_matches"] is True
    probe.check_dispatcher_bound({"dispatcher_coverage": derived})

    stale = json.loads(json.dumps(derived))
    stale["current_tetris_identity_covers"] = False
    with pytest.raises(AssertionError, match="not the one this tree derives"):
        probe.check_dispatcher_bound({"dispatcher_coverage": stale})

    stale_statement = json.loads(json.dumps(derived))
    stale_statement["statement"] = (
        "the Tetris identity stays the five modules its version-6 writer recorded, "
        "so a change to the dispatcher is not caught")
    with pytest.raises(AssertionError, match="not the one this tree derives"):
        probe.check_dispatcher_bound({"dispatcher_coverage": stale_statement})

    # The version keying itself is checked, not only the coverage: the key sets come
    # from the shape constants, so they do not move, but the recorded table entry does
    # -- and it is that entry which lets Experiment 003's retained records verify
    # against their own shape while the current writer emits a wider one.
    with monkeypatch.context() as patch:
        patch.setattr(runner, "_SUITE_FORMAT_VERSIONS",
                      {**runner._SUITE_FORMAT_VERSIONS,
                       runner.WRAPPER_IDENTITY_SUITE_FORMAT_VERSION:
                           (True, runner._IDENTITY_DISPATCH, False)})
        unversioned = probe.dispatcher_bound()
        assert unversioned["version_6_identity_shape"] == runner._IDENTITY_DISPATCH
        assert unversioned["version_6_tetris_identity_keys"] == \
            derived["version_6_tetris_identity_keys"]
        with pytest.raises(AssertionError):
            probe.check_dispatcher_bound({"dispatcher_coverage": unversioned})

    # The retained Experiment 003 sentence is what fails if the constants move
    # without it: the derivation reports that rather than passing quietly.
    with monkeypatch.context() as patch:
        patch.setattr(runner, "SUITE_FORMAT_VERSION", runner.SUITE_FORMAT_VERSION + 1)
        bumped = probe.dispatcher_bound()
        assert bumped["experiment_003_version_prose_matches"] is False
        assert bumped["experiment_003_current_suite_token"] == "8 current suite"
        with pytest.raises(AssertionError):
            probe.check_dispatcher_bound({"dispatcher_coverage": bumped})


def test_the_engine_advisory_vocabulary_does_not_depend_on_the_checkout(monkeypatch):
    """The legacy checks' advisory set is derived, and the same on every engine state.

    ``engine_advisories`` reads the verifier's own warning code rather than copying
    its two messages. Deriving them from a synthetic engine section of ``None``
    values was wrong: an engine checkout without Git metadata records ``commit`` and
    ``dirty`` as ``None``, so the synthetic section matched it and the
    recorded-vs-current advisory dropped out of the vocabulary — and the frozen
    fixture, which records a commit and a dirty flag, then reported a warning the
    vocabulary did not contain, so the legacy checks rejected a valid replay on that
    checkout. The derivation now makes both of the verifier's advisory branches fire
    whatever this checkout's state is, and the strings it returns are the verifier's
    own.

    This is an unmarked check, so it also has to hold in the engine-independent
    selection a GitHub runner executes, where no Block Stack checkout sits beside the
    worktree. ``_engine_warnings`` reads ``git_info(engine_root())``, so the root is
    pointed at a synthetic path as well as the ``git_info`` result: patching only the
    latter left the derivation depending on a checkout being present, which failed
    there with ``Block Stack checkout not found``. The vocabulary is a property of the
    verifier's own code, not of a checkout, and the engine-dependent step -- re-running
    the frozen record -- is stubbed out of the aggregate command and run by the
    integration suite instead.
    """
    probe = _load_plan_probe("exp004_plan_advisory_probe")
    difference = "Engine Git version or dirty status differs from the recorded run."
    working_tree = (
        "The engine is a working-tree run; matching Git metadata cannot prove identical "
        "uncommitted source."
    )
    for state in ({"commit": "abc123", "dirty": False, "kind": "committed"},
                  {"commit": "abc123", "dirty": True, "kind": "working-tree"},
                  {"commit": None, "dirty": None, "kind": "unversioned"}):
        with monkeypatch.context() as patch:
            patch.setattr(runner, "engine_root",
                          lambda: Path("/synthetic/engine-checkout"))
            patch.setattr(runner, "git_info", lambda root, state=state: dict(state))
            assert probe.engine_advisories() == (difference, working_tree), state


def test_a_suite_configures_at_most_one_declared_objective(tmp_path, monkeypatch):
    """A record carries one objective section, so two such agents are refused.

    A version-6 record has one ``objective`` field, which names the module that
    declares the configured agent's objective; a suite naming two *different*
    such agents would need two sections of a shape no writer emits, so the
    configuration is rejected at parse time instead of being recorded
    ambiguously. The same agent named twice is one objective and remains valid,
    exactly as it was before this check existed.
    """
    with pytest.raises(ValueError, match=r"at most one agent with its own objective"):
        runner.parse_config({**OBJECTIVE_SUITE, "agents": ["tetris", "tetris_plan"]})
    config = runner.parse_config({**OBJECTIVE_SUITE, "agents": ["lookahead", "tetris_plan"]})
    assert config.agents == ("lookahead", "tetris_plan")

    # The same agent twice is still one objective, and stays valid as it always
    # was: its episodes repeat in the configured order. A repeated name must not
    # read as two objectives, or a record the writer produced would fail to parse
    # before it could be replayed.
    repeated = runner.parse_config({**OBJECTIVE_SUITE, "agents": ["tetris", "tetris"]})
    assert repeated.agents == ("tetris", "tetris")
    assert runner._declared_agents(("tetris", "lookahead", "tetris")) == ("tetris",)
    path, factory, record = _objective_suite(
        tmp_path, monkeypatch, agents=("tetris", "tetris"))
    assert record["objective"]["module"] == "block_stack_ai.tetris"
    assert [episode["agent"] for episode in record["episodes"]] == ["tetris", "tetris"]
    assert verify_run(path, factory) == []


def _load_plan_probe(name="exp004_plan_evidence_probe"):
    """The 004 probe file, loaded from the experiment so its checks can be driven."""
    path = (engine.PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "probes"
            / "evidence.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_plan_predeclaration_binds_the_cited_record(tmp_path, monkeypatch):
    """The plan's capture ties the cited record to the code that chose its inputs.

    The declaration is captured from the tree before the ten-seed evaluation, and
    the check re-derives every claim: the declaring module's digest, the rationale
    section's digest, the identity of the modules the plan's choices are computed
    from, and the cited record's own objective section — which must be the captured
    one and must postdate the capture. A record that predates the capture, a record
    whose identity is not the capture's, a record with no objective section at all,
    and each covered module changed after the capture are all reported rather than
    accepted.

    The record is also tied to the run the retained result cites: any later
    one-seed run, or a minimal JSON object carrying a timestamp and a copy of the
    objective, used to pass and be reported as the evaluation record, which proved
    nothing about the ten-seed measurement the capture preceded. Its path, its
    configuration — against the experiment's canonical config file rather than the
    copy the result embeds — its complete ``(agent, seed)`` episode set and, for
    each of those identities, the per-episode outcome the retained result carries
    are therefore required as well, and each is driven with a record that should be
    rejected. Without the outcome comparison a *different*, later,
    same-configuration run placed at the cited path passed with a copy of the
    captured objective even when every line, score, frame, placed-piece,
    stopping-reason and clear-size value differed from the published measurement.
    """
    probe = _load_plan_probe()
    capture = tmp_path / "predeclared_objective.json"
    monkeypatch.setattr(probe, "PREDECLARATION", capture)
    probe.predeclare()
    captured = json.loads(capture.read_text(encoding="utf-8"))
    assert captured["objective"] == wellplan_weights_record()
    assert set(captured["sources"]) == set(runner._objective_sources(agent="tetris_plan"))

    # The run the capture precedes is the record the result cites. It is produced by
    # the writer rather than hand-shaped, so its objective section, configuration and
    # episodes are the ones a real run emits; ``PROJECT_ROOT`` is pointed at the
    # temporary directory so the citation is resolved the way the retained result
    # states it, relative to the project root.
    record_path, factory, record = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris_plan"))
    rows = [probe.episode_row(episode) for episode in record["episodes"]]
    result_path = tmp_path / "result.json"
    # The citation is resolved through the result, and the accepted record is bound to
    # the rows that result retains and to the configuration the experiment's own
    # ``config.json`` states — not to the copy the result embeds.
    config_path = tmp_path / "experiment-config.json"
    config_path.write_text(json.dumps(record["configuration"]), encoding="utf-8")
    monkeypatch.setattr(probe, "EXPERIMENT_CONFIG", config_path)
    result = {
        "configuration": record["configuration"],
        "episodes_by_agent_seed": rows,
        "predeclared_objective": {
            "cited_record": str(record_path.relative_to(tmp_path)),
        },
    }
    result_path.write_text(json.dumps(result), encoding="utf-8")
    monkeypatch.setattr(probe, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(probe, "RESULT_PATH", result_path)
    probe.check_predeclaration(record_path)

    # The same configuration replayed to different outcomes is not the measured run,
    # whatever path it is placed at: the check compares every reported field of every
    # configured ``(agent, seed)`` identity with the retained row for it, so a record
    # whose games were played again — or one whose numbers were edited — is reported
    # instead of being certified as the evaluation on the strength of its
    # configuration and identity set alone.
    different = json.loads(json.dumps(record))
    different["episodes"][0]["result"]["lines"] += 1
    record_path.write_text(json.dumps(different), encoding="utf-8")
    with pytest.raises(AssertionError, match="are not the rows the retained result"):
        probe.check_predeclaration(record_path)
    record_path.write_text(json.dumps(record), encoding="utf-8")

    # The result's own rows are the other side of that comparison, so a retained
    # result whose row for a configuration identity is missing -- or whose row
    # disagrees with the run it cites -- is reported as well.
    shorter = json.loads(json.dumps(result))
    shorter["episodes_by_agent_seed"].pop()
    result_path.write_text(json.dumps(shorter), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the configured"):
        probe.check_predeclaration(record_path)
    result_path.write_text(json.dumps(result), encoding="utf-8")

    # The canonical config file is the authority on what was evaluated: a result
    # whose embedded configuration no longer matches it describes a suite the
    # documented ``run --config`` command would not reproduce.
    drifted = json.loads(json.dumps(result))
    drifted["configuration"]["seeds"] = [1, 3]
    result_path.write_text(json.dumps(drifted), encoding="utf-8")
    with pytest.raises(AssertionError, match="not this experiment's canonical"):
        probe.check_predeclaration(record_path)
    result_path.write_text(json.dumps(result), encoding="utf-8")

    # An unrelated run — the same configuration replayed later, or another record
    # altogether — is not the one the result cites, whatever its own timestamps say.
    unrelated_path, _, _ = _objective_suite(
        tmp_path, monkeypatch, agents=("lookahead", "tetris_plan"))
    assert unrelated_path != record_path
    with pytest.raises(AssertionError,
                       match="is not the run record the retained result cites"):
        probe.check_predeclaration(unrelated_path)

    # A record at the cited path whose configuration is not the evaluation
    # configuration, and one whose episodes are not its complete set, are both
    # reported: those are what make the chronology evidence about this measurement.
    one_seed = json.loads(json.dumps(record))
    one_seed["configuration"]["seeds"] = [1, 3]
    record_path.write_text(json.dumps(one_seed), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match="is not the evaluation configuration the retained result"):
        probe.check_predeclaration(record_path)

    truncated = json.loads(json.dumps(record))
    truncated["episodes"].pop()
    record_path.write_text(json.dumps(truncated), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the configured"):
        probe.check_predeclaration(record_path)

    duplicated = json.loads(json.dumps(record))
    duplicated["episodes"].append(json.loads(json.dumps(duplicated["episodes"][0])))
    record_path.write_text(json.dumps(duplicated), encoding="utf-8")
    with pytest.raises(AssertionError, match="twice"):
        probe.check_predeclaration(record_path)

    # A minimal object carrying only a timestamp and a copy of the objective — the
    # shape that used to pass — is rejected on the first structural claim: it does
    # not carry the evaluation configuration.
    minimal = {
        "created_at": "2099-01-01T00:00:00+00:00",
        "objective": record["objective"],
    }
    record_path.write_text(json.dumps(minimal), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match="is not the evaluation configuration the retained result"):
        probe.check_predeclaration(record_path)

    # A record that carries the evaluation configuration but no episodes has no run
    # for the capture's chronology to be evidence about.
    config_only = {
        "created_at": "2099-01-01T00:00:00+00:00",
        "configuration": record["configuration"],
        "objective": record["objective"],
    }
    record_path.write_text(json.dumps(config_only), encoding="utf-8")
    with pytest.raises(AssertionError, match="carries no episodes"):
        probe.check_predeclaration(record_path)

    record_path.write_text(json.dumps(record), encoding="utf-8")
    stale = json.loads(json.dumps(record))
    stale["created_at"] = "2001-01-01T00:00:00+00:00"
    record_path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(AssertionError, match="before the predeclaration"):
        probe.check_predeclaration(record_path)

    tampered = json.loads(json.dumps(record))
    tampered["objective"]["sources"] = {
        **captured["sources"], "block_stack_ai.wellplan": "0" * 64}
    record_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the capture's"):
        probe.check_predeclaration(record_path)

    without_objective = json.loads(json.dumps(record))
    del without_objective["objective"]
    record_path.write_text(json.dumps(without_objective), encoding="utf-8")
    with pytest.raises(AssertionError, match="carries no objective section"):
        probe.check_predeclaration(record_path)

    record_path.write_text(json.dumps(record), encoding="utf-8")
    for name in sorted(captured["sources"]):
        mutated = tmp_path / (name.rpartition(".")[2] + "-after-capture.py")
        mutated.write_bytes(Path(sys.modules[name].__file__).read_bytes()
                            + b"\n# changed after the capture\n")
        with monkeypatch.context() as patch:
            patch.setattr(sys.modules[name], "__file__", str(mutated))
            with pytest.raises(AssertionError, match="changed after the predeclaration"):
                probe.check_predeclaration(record_path)


def test_the_plan_result_record_rederives_its_metrics_and_capture(tmp_path):
    """The retained result's own claims are re-derived, not trusted.

    Every retained claim is checked against evidence outside the block that states
    it. The metrics block has to be the aggregate of the episode rows the same file
    carries, so a mistyped mean or a rate over the wrong denominator is reported
    instead of read as a measurement. The blocks that aggregate the same rows are
    re-derived from them: the stopping counts and their sentence, the replay block's
    own count, field list and sentence, the rate's numerator and denominator, the
    development set's disjointness and the comparison against every superseded run's
    retained rows. The acceptance block's three thresholds are
    the baseline Experiment 003's retained rows derive — re-checked here — and the
    aspirational comparison's ``reported`` column is that baseline's other agent, so
    a record cannot certify itself against numbers it declared. The predeclaration
    block's order sentence has to be the one its own two timestamps reconstruct, its
    objective and identity have to equal the capture and the tree as they stand, its
    note and identity-coverage sentences have to be the ones the capture and the
    captures it supersedes reconstruct, and
    the cited run's ``created_at`` has to be the one it names while this checkout
    still holds that temporary run. The agent-factory and dispatcher digests the
    legacy-verification block, the objective section and the capture carry have to
    be the digests of those modules' own bytes on this tree -- the factory's also
    equal to the digest the retained frozen fixture's identity records -- so a
    value written for the superseded design, or one that is not the code that
    selects the plan's agent, is reported rather than read. And the mechanism block
    has to be what the tree's model derives, so a sentence about the reserve or the
    composition that the code no longer supports is reported, while the conclusion
    and the limitations have to be the sentences the same derivation reconstructs.
    """
    probe = _load_plan_probe("exp004_plan_record_probe")
    retained = (engine.PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
                / "result.json")
    path = tmp_path / "result.json"
    path.write_text(retained.read_text(encoding="utf-8"), encoding="utf-8")
    probe.check_record(path)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["metrics"]["tetris_plan"]["tetris_line_rate"] >= 0.011445
    assert record["metrics"]["tetris_plan"]["lines_mean"] > 349.5
    assert record["metrics"]["tetris_plan"]["score_mean"] > 567266.2

    # The three thresholds and the aspirational comparison are the baseline
    # Experiment 003's retained rows derive, not numbers the record declares for
    # itself: each is asserted here against the derivation, and the tampered cases
    # below require `check-record` to reject a threshold that is not that value.
    baseline = probe.baseline_metrics(runner.TETRIS_AGENT)
    assert record["acceptance"]["tetris_line_rate"]["required_gte"] == \
        baseline["tetris_line_rate"]
    assert record["acceptance"]["mean_lines"]["required_gt"] == baseline["lines_mean"]
    assert record["acceptance"]["mean_score"]["required_gt"] == baseline["score_mean"]
    assert record["acceptance"]["aspirational"]["mean_lines"]["reported"] == \
        probe.baseline_metrics("lookahead")["lines_mean"]
    assert record["acceptance"]["aspirational"]["mean_score"]["reported"] == \
        probe.baseline_metrics("lookahead")["score_mean"]

    mistyped = json.loads(json.dumps(record))
    mistyped["metrics"]["tetris_plan"]["lines_mean"] = 999.0
    path.write_text(json.dumps(mistyped), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the aggregate of its own rows"):
        probe.check_record(path)

    wrong_denominator = json.loads(json.dumps(record))
    wrong_denominator["metrics"]["tetris_plan"]["tetris_line_rate"] = 0.4
    path.write_text(json.dumps(wrong_denominator), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the aggregate of its own rows"):
        probe.check_record(path)

    # The acceptance block is derived as well: a verdict its own numbers no longer
    # support, or a value that is not the retained metric, is reported.
    unsupported = json.loads(json.dumps(record))
    unsupported["acceptance"]["mean_lines"]["achieved"] = 100.0
    path.write_text(json.dumps(unsupported), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the retained metric"):
        probe.check_record(path)

    # The three thresholds are the values Experiment 003's retained rows derive, so
    # a record cannot certify itself against numbers it declared: zeroing all three
    # -- which used to leave `check-record` exiting 0 with every verdict still "met"
    # -- and moving any one of them are both reported before any verdict is issued.
    for label, key in (("tetris_line_rate", "required_gte"),
                       ("mean_lines", "required_gt"),
                       ("mean_score", "required_gt")):
        zeroed = json.loads(json.dumps(record))
        zeroed["acceptance"][label][key] = 0.0
        path.write_text(json.dumps(zeroed), encoding="utf-8")
        with pytest.raises(AssertionError,
                           match=rf"{label}: the retained {key} is 0.0, not the value"):
            probe.check_record(path)

    moved = json.loads(json.dumps(record))
    moved["acceptance"]["mean_lines"][
        "required_gt"] = moved["acceptance"]["mean_lines"]["required_gt"] - 1.0
    path.write_text(json.dumps(moved), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"mean_lines: the retained required_gt"):
        probe.check_record(path)

    rejudged = json.loads(json.dumps(record))
    rejudged["acceptance"]["mean_score"]["met"] = False
    path.write_text(json.dumps(rejudged), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not what"):
        probe.check_record(path)

    # The aspirational block is derived too, and both columns are bound outside this
    # record: ``achieved`` is the plan agent's own metric, and ``reported`` is the
    # value Experiment 003's retained rows derive for the agent the criteria compare
    # it with — so a block that copied the comparison agent's number into the plan's
    # column, or reported a number the baseline does not publish, is reported rather
    # than read as the plan's measurement.
    aspiration = json.loads(json.dumps(record))
    aspiration["acceptance"]["aspirational"]["mean_lines"]["achieved"] = (
        aspiration["acceptance"]["aspirational"]["mean_lines"]["reported"])
    path.write_text(json.dumps(aspiration), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match=r"aspirational\.mean_lines is not the entry"):
        probe.check_record(path)

    misreported = json.loads(json.dumps(record))
    misreported["acceptance"]["aspirational"]["mean_score"]["reported"] = 1.0
    path.write_text(json.dumps(misreported), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match=r"aspirational\.mean_score is not the entry"):
        probe.check_record(path)

    # The baseline block is derived from Experiment 003's own retained rows, so a
    # number that is not their aggregate is reported as well.
    stale_baseline = json.loads(json.dumps(record))
    stale_baseline["baseline"]["published_metrics"]["tetris"]["lines_mean"] = 1.0
    path.write_text(json.dumps(stale_baseline), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the aggregate of Experiment 003's"):
        probe.check_record(path)

    miscounted = json.loads(json.dumps(record))
    miscounted["retained_replay"]["episodes_compared"] = 19
    path.write_text(json.dumps(miscounted), encoding="utf-8")
    with pytest.raises(AssertionError, match="the retained replay block is not the one"):
        probe.check_record(path)

    reordered = json.loads(json.dumps(record))
    reordered["predeclared_objective"]["capture_order"] = (
        "the capture was written after the cited record")
    path.write_text(json.dumps(reordered), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not the line"):
        probe.check_record(path)

    stale = json.loads(json.dumps(record))
    stale["predeclared_objective"]["module_sha256"] = "0" * 64
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(AssertionError):
        probe.check_record(path)

    # The agent-factory digest is derived, not read: a value written for the
    # superseded design -- the plan agent added to the shared factory -- no longer
    # matches the digest of the tree's own agents.py, and the copy the objective
    # section carries is checked against the same digest.
    stale_factory = json.loads(json.dumps(record))
    stale_factory["legacy_verification"]["agent_factory_digest"] = "a0772867" + "0" * 56
    path.write_text(json.dumps(stale_factory), encoding="utf-8")
    with pytest.raises(AssertionError, match="agent_factory_digest"):
        probe.check_record(path)

    # The retained objective section's complete source mapping is compared with the
    # capture, entry by entry: the factory's digest and the dispatcher's are two of
    # its entries, and a tampered one is named in the report.
    stale_objective = json.loads(json.dumps(record))
    stale_objective["objective_record"]["sources"]["block_stack_ai.agents"] = "0" * 64
    path.write_text(json.dumps(stale_objective), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"block_stack_ai\.agents: recorded '0{64}'"):
        probe.check_record(path)

    stale_runner = json.loads(json.dumps(record))
    stale_runner["objective_record"]["sources"]["block_stack_ai.runner"] = "0" * 64
    path.write_text(json.dumps(stale_runner), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"block_stack_ai\.runner: recorded '0{64}'"):
        probe.check_record(path)

    # The retained objective section is compared whole, so a truncated source
    # mapping, changed weights or a different module is reported even when the
    # predeclaration block beside it still matches its capture.
    truncated_objective = json.loads(json.dumps(record))
    del truncated_objective["objective_record"]["sources"]["block_stack_ai.wellplan"]
    path.write_text(json.dumps(truncated_objective), encoding="utf-8")
    with pytest.raises(AssertionError, match="complete captured identity"):
        probe.check_record(path)

    stale_weights = json.loads(json.dumps(record))
    stale_weights["objective_record"]["weights"]["tetrises"] = 1.0
    path.write_text(json.dumps(stale_weights), encoding="utf-8")
    with pytest.raises(AssertionError, match="weights is not the weights"):
        probe.check_record(path)

    other_module = json.loads(json.dumps(record))
    other_module["objective_record"]["module"] = "block_stack_ai.tetris"
    path.write_text(json.dumps(other_module), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the module the tree's registry selects"):
        probe.check_record(path)

    # The block's own two timestamps are compared with each other, not only against
    # the sentence they generate: a capture that claims to precede a record which
    # predates it is reported even when the temporary run record is gone, which is
    # the clean-checkout case the sentence alone cannot decide.
    contradicted_order = json.loads(json.dumps(record))
    contradicted_order["predeclared_objective"]["cited_record_created_at"] = (
        contradicted_order["predeclared_objective"]["captured_at"])
    contradicted_order["predeclared_objective"]["capture_order"] = (
        probe.predeclaration_order_line(
            contradicted_order["predeclared_objective"]["captured_at"],
            contradicted_order["predeclared_objective"]["cited_record_created_at"]))
    path.write_text(json.dumps(contradicted_order), encoding="utf-8")
    with pytest.raises(AssertionError, match="timestamps contradict"):
        probe.check_record(path)

    # The mechanism block is derived from the model too, so a contradicting number
    # or a stale sentence about the objective's behaviour is reported rather than
    # read as evidence.
    stale_reserve = json.loads(json.dumps(record))
    stale_reserve["objective_mechanism"]["reserve_with_an_occupied_well"]["well_reserve"] = 0
    path.write_text(json.dumps(stale_reserve), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the one the tree's model derives"):
        probe.check_record(path)

    stale_composition = json.loads(json.dumps(record))
    contradiction = stale_composition["objective_mechanism"][
        "composition_differs_from_experiment_003"][0]["statement"]
    assert "clear_term alone" in contradiction
    stale_composition["objective_mechanism"][
        "composition_differs_from_experiment_003"][0]["statement"] = (
            "the plan composes a current placement exactly as Experiment 003's "
            "objective composes them")
    path.write_text(json.dumps(stale_composition), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the ones the tree's model derives"):
        probe.check_record(path)

    # The superseded captures are part of the ordering story too: the block has to
    # name captures that are on the tree beside the current one, older than it and
    # of a different subject, so the re-capture it claims can be checked from the
    # artifacts rather than believed.
    unlisted = json.loads(json.dumps(record))
    unlisted["predeclared_objective"]["superseded_captures"] = []
    path.write_text(json.dumps(unlisted), encoding="utf-8")
    with pytest.raises(AssertionError, match="names no superseded capture"):
        probe.check_record(path)

    missing_capture = json.loads(json.dumps(record))
    missing_capture["predeclared_objective"]["superseded_captures"].append(
        "experiments/004-bounded-well-plan/probes/not-retained.json")
    path.write_text(json.dumps(missing_capture), encoding="utf-8")
    with pytest.raises(AssertionError, match="is not on this tree"):
        probe.check_record(path)

    self_superseded = json.loads(json.dumps(record))
    self_superseded["predeclared_objective"]["superseded_captures"].append(
        self_superseded["predeclared_objective"]["capture_file"])
    path.write_text(json.dumps(self_superseded), encoding="utf-8")
    with pytest.raises(AssertionError, match="lists the current capture as superseded"):
        probe.check_record(path)

    # The reproduction block is a claim that the comparison was complete, so its
    # count, fields, source and sentence are derived from Experiment 003's rows and
    # this result's own configuration: a block that says a truncated comparison
    # reproduced -- what the baseline command used to print after iterating the
    # fresh episodes alone -- is reported here.
    miscounted_baseline = json.loads(json.dumps(record))
    miscounted_baseline["baseline"]["reproduction"]["episodes_compared"] = 19
    path.write_text(json.dumps(miscounted_baseline), encoding="utf-8")
    with pytest.raises(AssertionError, match="complete configured"):
        probe.check_record(path)

    unfielded = json.loads(json.dumps(record))
    unfielded["baseline"]["reproduction"]["fields_checked"] = ["lines", "score"]
    path.write_text(json.dumps(unfielded), encoding="utf-8")
    with pytest.raises(AssertionError, match="set of fields the probe compares"):
        probe.check_record(path)

    resourced = json.loads(json.dumps(record))
    resourced["baseline"]["reproduction"]["published_rows_source"] = "somewhere else"
    path.write_text(json.dumps(resourced), encoding="utf-8")
    with pytest.raises(AssertionError, match="does not name the retained rows"):
        probe.check_record(path)

    restated = json.loads(json.dumps(record))
    restated["baseline"]["reproduction"]["result"] = (
        "Experiment 003's rows reproduce exactly")
    path.write_text(json.dumps(restated), encoding="utf-8")
    with pytest.raises(AssertionError, match="sentence the published metrics reconstruct"):
        probe.check_record(path)

    # The retained rows themselves are required to be the complete configured set
    # on both sides, so a duplicate or a missing pair is reported before any
    # aggregate is taken over them.
    duplicated_rows = json.loads(json.dumps(record))
    duplicated_rows["episodes_by_agent_seed"].append(
        dict(duplicated_rows["episodes_by_agent_seed"][0]))
    path.write_text(json.dumps(duplicated_rows), encoding="utf-8")
    with pytest.raises(AssertionError, match="twice"):
        probe.check_record(path)

    truncated_rows = json.loads(json.dumps(record))
    truncated_rows["episodes_by_agent_seed"].pop()
    path.write_text(json.dumps(truncated_rows), encoding="utf-8")
    with pytest.raises(AssertionError, match="not the configured"):
        probe.check_record(path)


def _zero_clear_size_bucket(row: dict) -> str:
    """A clear-size bucket a row counts as zero, for the boolean-for-integer tamper.

    JSON ``false`` compares equal to ``0``, so a bucket counted as zero is the one
    whose value can be replaced by a boolean and still reproduce under plain
    equality; a non-zero count would differ from ``False`` whatever the comparison
    did.
    """
    return next(name for name, count in row["clear_sizes"].items() if count == 0)


def _tampered_plan_result(record: dict, tamper: str) -> dict:
    """The retained plan result with one named self-declared claim tampered."""
    result = json.loads(json.dumps(record))
    if tamper == "genuine":
        return result
    if tamper == "boolean_clear_size":
        row = result["episodes_by_agent_seed"][0]
        row["clear_sizes"][_zero_clear_size_bucket(row)] = False
    elif tamper == "rows_identical":
        result["refactor_no_outcomes_changed"][
            "rows_identical_to_every_superseded_run"] = False
    elif tamper == "extra_comparison_claim":
        result["refactor_no_outcomes_changed"][
            "rows_identical_to_the_superseded_run"] = True
    elif tamper == "superseded_run":
        result["refactor_no_outcomes_changed"]["superseded_runs"].append({
            "run": "runs/19700101T000000000000Z-00000000/run.json",
            "created_at": "1970-01-01T00:00:00+00:00",
            "capture": result["predeclared_objective"]["superseded_captures"][0]})
    elif tamper == "unbacked_block":
        result["run_reproduces_every_published_row"] = {"equal": True}
    elif tamper == "stopping":
        result["stopping"]["episodes_stopped_at_the_cap"]["tetris_plan"] = 1
    elif tamper == "stopping_note":
        result["stopping"]["note"] = "every game ended by topping out"
    elif tamper == "status":
        result["status"] = "failed"
    elif tamper == "numerator":
        result["acceptance"]["tetris_line_rate"]["numerator"] = "four-line clears (0)"
    elif tamper == "development":
        result["development"]["seeds"] = list(result["configuration"]["seeds"])
    elif tamper == "development_boolean":
        result["development"]["seeds"][0] = False
    elif tamper == "float_seed":
        result["episodes_by_agent_seed"][0]["seed"] = 2.0
    elif tamper == "engine_dependency":
        result["engine_dependency"]["commit"] = "0" * 40
    elif tamper == "engine_dependency_boolean":
        result["engine_dependency"]["dirty"] = 1
    elif tamper == "conclusion":
        result["conclusion"] = result["conclusion"].replace("620.0", "999.0")
        assert "999.0" in result["conclusion"]
    elif tamper == "limitations":
        result["limitations"][0] = "the agent was measured on every ruleset"
    elif tamper == "configuration":
        result["configuration"]["seeds"] = [1, 3]
    else:
        raise AssertionError(f"unknown tamper: {tamper}")
    return result


@pytest.mark.parametrize("tamper,message", [
    ("genuine", None),
    ("rows_identical",
     "the retained refactor-no-outcomes-changed block is not the comparison"),
    ("extra_comparison_claim",
     "the retained refactor-no-outcomes-changed block is not the comparison"),
    ("superseded_run",
     "the retained refactor-no-outcomes-changed block is not the comparison"),
    ("duplicated_capture", "the same subject"),
    ("unpaired_capture", "not one-to-one"),
    ("changed_weights", "did not publish the declared weights"),
    ("unretained_rationale", "is not a retained rationale generation"),
    ("capture_after_its_run", "did not precede it"),
    ("superseded_artifact", "so the re-measurement moved them"),
    ("superseded_boolean_clear_size", "so the re-measurement moved them"),
    ("boolean_clear_size", "so the re-measurement moved them"),
    ("artifact_absent", "is not on this tree"),
    ("unbacked_block", "neither re-derived nor declared narrative"),
    ("stopping", "the retained stopping block is not the one"),
    ("stopping_note", "the retained stopping block is not the one"),
    ("status", "the retained status is"),
    ("numerator", "is not the rate's own"),
    ("development", "the retained development block is not the declared development set"),
    ("development_boolean",
     "the retained development block is not the declared development set"),
    ("float_seed", "integer seed"),
    ("engine_dependency", "the retained engine-dependency block is not the one"),
    ("engine_dependency_boolean", "the retained engine-dependency block is not the one"),
    ("conclusion", "the retained conclusion is not the one"),
    ("limitations", "the retained limitations are not the ones"),
    ("configuration", "not this experiment's canonical"),
])
def test_the_plan_record_rejects_a_claim_no_derivation_backs(
    tmp_path, monkeypatch, tamper, message
):
    """Every retained claim is a claim only because a check re-derives it.

    The recurring defect in this experiment's evidence was one level above a check
    that inspects an artifact instead of binding it: a check that binds a claim's
    *inputs* while leaving its *outcomes* declared by the record under test, so the
    record could assert a fact about itself and pass. This test drives that class
    from the tampered side: every claim the retained result makes is falsified in
    turn, and `check-record` has to report it. The comparison claim is covered from
    both sides of its artifact -- a record that names a superseded run the artifact
    does not carry, an added field that no derivation produces, an artifact whose
    rows no longer equal the retained ones, and a missing artifact -- because a
    comparison is only evidence when the rows it compares are retained somewhere
    other than the record making the claim.
    """
    probe = _load_plan_probe("exp004_plan_claim_probe")
    retained = (engine.PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
                / "result.json")
    record = json.loads(retained.read_text(encoding="utf-8"))
    result = (record if tamper in ("superseded_artifact", "artifact_absent",
                                   "duplicated_capture", "unpaired_capture",
                                   "changed_weights", "capture_after_its_run",
                                   "superseded_boolean_clear_size",
                                   "unretained_rationale")
              else _tampered_plan_result(record, tamper))
    if tamper == "duplicated_capture":
        # The same capture listed twice: two loaded captures with one subject, so one
        # of them preceded no design of its own.
        captures = result["predeclared_objective"]["superseded_captures"]
        captures.append(captures[0])
    elif tamper == "unpaired_capture":
        # An extra capture whose subject is its own, so it passes the distinctness
        # rule, but which no retained superseded run names -- listed, counted and
        # unbacked. The note is recomputed from the tampered list so the record is
        # otherwise self-consistent and only the binding is missing.
        block = result["predeclared_objective"]
        unpaired = json.loads((probe.PROJECT_ROOT
                               / block["superseded_captures"][0]).read_text(encoding="utf-8"))
        unpaired["module_sha256"] = "0" * 64
        copy_path = tmp_path / "unpaired-capture.json"
        copy_path.write_text(json.dumps(unpaired), encoding="utf-8")
        block["superseded_captures"].append(str(copy_path))
        block["note"] = probe.predeclaration_note(
            json.loads(probe.PREDECLARATION.read_text(encoding="utf-8")),
            block["superseded_captures"])
    elif tamper == "changed_weights":
        # One superseded capture declares a different weight, so the note's claim that
        # no re-capture touched a declared weight or constant is false. The copy keeps
        # the original's subject and rationale, and replaces it in the list, so only
        # the declaration differs.
        block = result["predeclared_objective"]
        original = block["superseded_captures"][0]
        earlier = json.loads((probe.PROJECT_ROOT / original).read_text(encoding="utf-8"))
        earlier["objective"] = {**earlier["objective"], "reserve": 5.0}
        copy_path = tmp_path / "changed-weights-capture.json"
        copy_path.write_text(json.dumps(earlier), encoding="utf-8")
        block["superseded_captures"] = [str(copy_path) if name == original else name
                                        for name in block["superseded_captures"]]
    elif tamper == "unretained_rationale":
        # A listed capture whose rationale-section digest names no retained section:
        # the prose correction to the rationale section changed its digest, so the
        # history binds each capture to a *retained* generation rather than to the
        # current text; a digest that names no retained artifact is reported.
        block = result["predeclared_objective"]
        original = block["superseded_captures"][0]
        earlier = json.loads((probe.PROJECT_ROOT / original).read_text(encoding="utf-8"))
        earlier["notes_section_sha256"] = "0" * 64
        copy_path = tmp_path / "unretained-rationale-capture.json"
        copy_path.write_text(json.dumps(earlier), encoding="utf-8")
        block["superseded_captures"] = [str(copy_path) if name == original else name
                                        for name in block["superseded_captures"]]
        block["note"] = probe.predeclaration_note(
            json.loads(probe.PREDECLARATION.read_text(encoding="utf-8")),
            block["superseded_captures"])
    elif tamper == "capture_after_its_run":
        # A capture of a superseded run moved to a time *after* the run it is paired
        # with -- still before the current capture, keeping its subject and weights --
        # so the history claims a predeclaration that came after its evaluation.
        document = json.loads(probe.SUPERSEDED_ROWS.read_text(encoding="utf-8"))
        entry = document["runs"][0]
        original = entry["capture"]
        moved = json.loads((probe.PROJECT_ROOT / original).read_text(encoding="utf-8"))
        moved["captured_at"] = "2026-09-30T05:00:00+00:00"
        moved_path = tmp_path / "capture-after-its-run.json"
        moved_path.write_text(json.dumps(moved), encoding="utf-8")
        entry["capture"] = str(moved_path)
        artifact = tmp_path / "superseded_run_rows.json"
        artifact.write_text(json.dumps(document), encoding="utf-8")
        monkeypatch.setattr(probe, "SUPERSEDED_ROWS", artifact)
        block = result["predeclared_objective"]
        block["superseded_captures"] = [str(moved_path) if name == original else name
                                        for name in block["superseded_captures"]]
    if tamper == "superseded_artifact":
        document = json.loads(probe.SUPERSEDED_ROWS.read_text(encoding="utf-8"))
        document["runs"][0]["rows"][0]["score"] += 1
        artifact = tmp_path / "superseded_run_rows.json"
        artifact.write_text(json.dumps(document), encoding="utf-8")
        monkeypatch.setattr(probe, "SUPERSEDED_ROWS", artifact)
    elif tamper == "superseded_boolean_clear_size":
        # A clear-size count in the retained artifact replaced by a boolean: JSON
        # ``false`` equals ``0``, so the artifact still aggregates to the retained
        # row under plain equality and the comparison has to reject it by type.
        document = json.loads(probe.SUPERSEDED_ROWS.read_text(encoding="utf-8"))
        row = document["runs"][0]["rows"][0]
        row["clear_sizes"][_zero_clear_size_bucket(row)] = False
        artifact = tmp_path / "superseded_run_rows.json"
        artifact.write_text(json.dumps(document), encoding="utf-8")
        monkeypatch.setattr(probe, "SUPERSEDED_ROWS", artifact)
    elif tamper == "artifact_absent":
        monkeypatch.setattr(probe, "SUPERSEDED_ROWS", tmp_path / "not-retained.json")
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    if message is None:
        probe.check_record(path)
        return
    with pytest.raises(AssertionError, match=message):
        probe.check_record(path)


@pytest.mark.parametrize("change", [
    {"seeds": [1, 3]},
    {"agents": ["lookahead", "tetris"]},
])
def test_the_plan_record_is_bound_to_the_canonical_config(tmp_path, monkeypatch, change):
    """The experiment's config file is the authority, not the copy the result embeds.

    ``check-record`` took the evaluation configuration from the record's own
    ``configuration`` block, so editing
    ``experiments/004-bounded-well-plan/config.json`` -- the file the documented
    ``block-stack-ai run --experiment 004``/``--config`` command executes -- left the
    record certifying a suite that command would no longer reproduce: the result
    kept its old self-consistent copy and every check still passed. The embedded
    copy is now compared with the canonical file before either is used, and this
    test drives the deviation from the canonical side, for a changed seed list and a
    changed agent list, with the unmodified file still certifying the record.
    """
    probe = _load_plan_probe("exp004_plan_config_probe")
    retained = (engine.PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
                / "result.json")
    record = json.loads(retained.read_text(encoding="utf-8"))
    path = tmp_path / "result.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    canonical = tmp_path / "config.json"
    canonical.write_text(json.dumps({**record["configuration"], **change}),
                         encoding="utf-8")
    monkeypatch.setattr(probe, "EXPERIMENT_CONFIG", canonical)
    with pytest.raises(AssertionError, match="not this experiment's canonical"):
        probe.check_record(path)
    canonical.write_text(json.dumps(record["configuration"]), encoding="utf-8")
    probe.check_record(path)


def test_the_plan_replay_is_bound_to_the_canonical_config(tmp_path, monkeypatch):
    """``reproduce`` replays the experiment's config file, not the record's copy.

    The documented replay command parses the retained configuration and plays the
    suite again, and it read that configuration from the record's own copy -- so a
    canonical ``config.json`` edited to another agent or seed list left ``reproduce``
    replaying the old suite and reporting a clean reproduction, while the documented
    ``run --config`` command ran a different experiment. The replay now binds the copy
    to the canonical file before it parses or plays anything, so the drift is reported
    without a native run: the assertion fires before the suite is rebuilt.
    """
    probe = _load_plan_probe("exp004_plan_replay_probe")
    retained = (engine.PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
                / "result.json")
    record = json.loads(retained.read_text(encoding="utf-8"))
    path = tmp_path / "result.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    canonical = tmp_path / "config.json"
    canonical.write_text(json.dumps({**record["configuration"], "seeds": [1, 3]}),
                         encoding="utf-8")
    monkeypatch.setattr(probe, "EXPERIMENT_CONFIG", canonical)
    with pytest.raises(AssertionError, match="not this experiment's canonical"):
        probe.reproduce(path)


def test_the_plan_baseline_is_bound_to_experiment_003s_config(tmp_path, monkeypatch):
    """The baseline is Experiment 003's suite, per that experiment's own config file.

    The comparison this experiment is judged against is Experiment 003's measurement,
    read from its retained rows -- and those rows belong to the suite Experiment 003's
    own ``config.json`` states, not to the copy its result embeds. Binding them is
    what makes the re-derived baseline the experiment its documented run command
    reproduces; a baseline whose rows describe another suite is reported rather than
    aggregated into this record's thresholds.
    """
    probe = _load_plan_probe("exp004_plan_tetris_config_probe")
    canonical = probe.experiment_003_configuration()
    drifted = tmp_path / "003-config.json"
    drifted.write_text(json.dumps({**canonical, "seeds": [1, 3]}), encoding="utf-8")
    monkeypatch.setattr(probe, "TETRIS_CONFIG", drifted)
    with pytest.raises(AssertionError, match="not Experiment 003's canonical"):
        probe.experiment_003_evidence()
    drifted.write_text(json.dumps(canonical), encoding="utf-8")
    probe.experiment_003_evidence()


def _baseline_replay(retained: dict, rows: list[dict]) -> dict:
    """A fresh run record shaped like a replay of Experiment 003's configuration."""
    return {
        "configuration": json.loads(json.dumps(retained["configuration"])),
        "episodes": [
            {
                "agent": row["agent"],
                "seed": row["seed"],
                "pieces_placed": row["pieces_placed"],
                "clear_sizes": row["clear_sizes"],
                "result": {
                    "lines": row["lines"],
                    "score": row["score"],
                    "frame_count": row["frames"],
                    "stopping_reason": row["stopping_reason"],
                },
            }
            for row in rows
        ],
    }


def _tampered_replay(retained: dict, rows: list[dict], tamper: str) -> dict:
    """Experiment 003's rows as a fresh run record, with one named defect."""
    if tamper == "complete":
        return _baseline_replay(retained, rows)
    if tamper == "truncated":
        return _baseline_replay(retained, rows[:-1])
    if tamper == "duplicated":
        return _baseline_replay(retained, [rows[0]] + rows[:-1])
    if tamper == "configuration":
        record = _baseline_replay(retained, rows)
        record["configuration"] = {**record["configuration"], "frame_limit": 199999}
        return record
    if tamper == "contradicting":
        record = _baseline_replay(retained, rows)
        record["episodes"][0]["result"]["lines"] += 1
        return record
    if tamper == "boolean_clear_size":
        # A fresh run whose clear-size count is a boolean: the row aggregates to the
        # retained integer under plain equality, so the reproduction has to reject it
        # by type rather than certify it.
        record = _baseline_replay(retained, rows)
        row = record["episodes"][0]
        row["clear_sizes"][_zero_clear_size_bucket(row)] = False
        return record
    raise AssertionError(f"unknown tamper: {tamper}")


@pytest.mark.parametrize("tamper,message", [
    ("complete", None),
    ("truncated", "not the configured"),
    ("duplicated", "twice"),
    ("configuration", "is not Experiment 003's configuration"),
    ("contradicting", "did not reproduce"),
    ("boolean_clear_size", "did not reproduce"),
])
def test_the_plan_baseline_claim_requires_the_complete_identity_set(
    tmp_path, monkeypatch, tamper, message
):
    """A reproduction is claimed only for the whole configured set.

    ``baseline`` printed its claim after iterating the fresh episodes alone, so one
    matching episode, or twenty copies of one key, read as "Experiment 003's
    published rows reproduce exactly". The claim now requires the fresh
    configuration to be Experiment 003's and both sides to carry every configured
    ``(agent, seed)`` exactly once, so a truncated set, a duplicated key and a
    mismatched configuration are each reported instead. The recorded run is
    synthesised from Experiment 003's own retained rows, so the comparison is
    exercised without replaying the native suite; the replay that a real
    ``baseline`` call makes first is stubbed here and driven for real by
    ``test_the_plan_baseline_rejects_a_copied_rows_record_without_replay_evidence``
    and by the integration suite's genuine-record case.
    """
    probe = _load_plan_probe("exp004_plan_baseline_probe")
    monkeypatch.setattr(probe.runner, "verify_run", lambda path: [])
    retained = json.loads(probe.TETRIS_RESULT.read_text(encoding="utf-8"))
    rows = retained["episodes_by_agent_seed"]
    path = tmp_path / "003-replay.json"
    path.write_text(json.dumps(_tampered_replay(retained, rows, tamper)), encoding="utf-8")
    if message is None:
        probe.baseline(path)
        return
    with pytest.raises(AssertionError, match=message):
        probe.baseline(path)


def test_the_plan_baseline_rejects_a_copied_rows_record_without_replay_evidence(
    tmp_path, monkeypatch
):
    """A reproduction claim is not issuable from copied rows alone.

    ``baseline`` compared a supplied JSON's rows with Experiment 003's published
    rows and printed "Experiment 003's published rows reproduce exactly on this
    tree" without ever verifying the supplied record. A hand-made file carrying
    Experiment 003's canonical configuration and a copy of its published rows —
    no ``format_version``, no recorded inputs, no per-episode structure, nothing
    replayable — reached that claim. The supplied record now has to verify through
    ``runner.verify_run``, the same path ``check-legacy`` applies to the frozen
    fixture, before any claim is made about it, and this drives that exact file.
    The verification is structural before it is a replay, so the rejection needs
    no native game: the file fails on its own shape. The narrowed comparison half
    still accepts the same file and says in its own output that it did not replay
    it, which is what keeps ``check_record``'s cheap binding honest.
    """
    probe = _load_plan_probe("exp004_plan_baseline_copied_probe")
    retained = json.loads(probe.TETRIS_RESULT.read_text(encoding="utf-8"))
    rows = retained["episodes_by_agent_seed"]
    copied = {
        "configuration": json.loads(probe.TETRIS_CONFIG.read_text(encoding="utf-8")),
        "episodes": [
            {"agent": row["agent"], "seed": row["seed"],
             "pieces_placed": row["pieces_placed"], "clear_sizes": row["clear_sizes"],
             "result": {"lines": row["lines"], "score": row["score"],
                        "frame_count": row["frames"],
                        "stopping_reason": row["stopping_reason"]}}
            for row in rows
        ],
    }
    path = tmp_path / "copied-rows.json"
    path.write_text(json.dumps(copied), encoding="utf-8")
    # The row comparison half accepts it -- and says it did not replay the record.
    probe.baseline_rows(path, verified=False)
    with pytest.raises(probe.runner.VerificationError):
        probe.baseline(path)


def test_the_plan_baseline_requires_the_retained_rows_to_be_the_complete_set(
    tmp_path, monkeypatch
):
    """The retained side is required to be the complete set too.

    Experiment 003's own rows are what every published aggregate and every
    reproduction claim rests on, so a truncated copy of them cannot be reproduced
    by a complete fresh run -- the comparison has to fail rather than print a claim
    about the rows that remain.
    """
    probe = _load_plan_probe("exp004_plan_baseline_retained_probe")
    retained = json.loads(probe.TETRIS_RESULT.read_text(encoding="utf-8"))
    rows = retained["episodes_by_agent_seed"]
    shortened = json.loads(json.dumps(retained))
    shortened["episodes_by_agent_seed"] = shortened["episodes_by_agent_seed"][:-1]
    retained_path = tmp_path / "003-result.json"
    retained_path.write_text(json.dumps(shortened), encoding="utf-8")
    path = tmp_path / "003-replay.json"
    path.write_text(json.dumps(_baseline_replay(retained, rows)), encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(probe.runner, "verify_run", lambda path: [])
        patch.setattr(probe, "TETRIS_RESULT", retained_path)
        with pytest.raises(AssertionError, match="not the configured"):
            probe.baseline(path)


def test_the_plan_reproduction_comparison_rejects_a_boolean_for_a_number():
    """An outcome is compared by type as well as by value.

    JSON ``false`` compares equal to ``0`` and ``true`` to ``1``, so a comparison
    that only tests values certifies a retained row whose clear-size counts are
    booleans as an exact reproduction of one whose counts are integers -- the
    aggregate sums the boolean back to zero and every claim above it still passes.
    Every field of the compared row therefore has to carry the writer's own type,
    and a mapping its exact keys, before any value is compared; the tampered side
    is driven here from each direction, and a row whose *both* sides are booleans
    is rejected too, because the schema -- not the other side -- is the contract.
    """
    probe = _load_plan_probe("exp004_plan_typed_outcome_probe")
    row = {
        "agent": "tetris_plan", "seed": 2, "lines": 5, "score": 100, "frames": 10,
        "pieces_placed": 3, "stopping_reason": "game_over",
        "clear_sizes": {"singles": 1, "doubles": 0, "triples": 0, "tetrises": 0},
    }
    key = ("tetris_plan", 2)
    assert probe.reproduction_differences({key: row}, {key: json.loads(json.dumps(row))}) == []

    for tamper in (
        lambda tampered: tampered["clear_sizes"].__setitem__("tetrises", False),
        lambda tampered: tampered["clear_sizes"].__setitem__("doubles", 0.0),
        lambda tampered: tampered.__setitem__("lines", 5.0),
        lambda tampered: tampered["clear_sizes"].pop("triples"),
    ):
        tampered = json.loads(json.dumps(row))
        tamper(tampered)
        assert probe.reproduction_differences({key: tampered}, {key: row}), tamper
        assert probe.reproduction_differences({key: row}, {key: tampered}), tamper

    boolean_row = json.loads(json.dumps(row))
    boolean_row["clear_sizes"]["tetrises"] = False
    assert probe.reproduction_differences({key: boolean_row}, {key: boolean_row}), (
        "a row whose clear-size counts are booleans on both sides is not the schema the "
        "writer emits"
    )


def test_the_plan_reproduction_comparison_rejects_a_structurally_different_record():
    """A comparison is over the complete identity set, not over the shared keys.

    ``reproduction_differences`` walked the intersection of the two mappings, so a
    record that carried an extra identity, or dropped one, compared equal to the
    record it was said to reproduce whenever the keys they shared agreed. The
    callers check the key sets first, and the comparison now reports an identity
    present on one side only as well, so two structurally different records cannot
    be certified as a reproduction of each other.
    """
    probe = _load_plan_probe("exp004_plan_structural_probe")
    row = {
        "agent": "tetris_plan", "seed": 2, "lines": 5, "score": 100, "frames": 10,
        "pieces_placed": 3, "stopping_reason": "game_over",
        "clear_sizes": {"singles": 1, "doubles": 0, "triples": 0, "tetrises": 0},
    }
    later = json.loads(json.dumps(row))
    later["seed"] = 4
    left = {("tetris_plan", 2): row, ("tetris_plan", 4): later}
    right = {("tetris_plan", 2): json.loads(json.dumps(row))}
    assert probe.reproduction_differences(left, right), (
        "an identity present on one side only is a structural difference"
    )
    assert probe.reproduction_differences(right, left)


def test_the_plan_retained_identity_types_are_checked_before_they_are_keys():
    """A mistyped identity is rejected, not folded into the configured key.

    ``rows_by_identity`` built its key straight from the retained row, so a row
    whose ``seed`` had been edited from the integer ``2`` to the float ``2.0`` —
    which JSON compares equal to ``2``, and which is not among the fields the
    outcome comparison checks — produced the configured key, passed the identity-set
    check and certified an exact reproduction for an identity ``runner.verify_run``
    rejects. Every retained-row path builds its keys here, so the writer's own
    identity rule is applied here: the agent has to be a string and the seed an
    integer, excluding booleans.
    """
    probe = _load_plan_probe("exp004_plan_identity_type_probe")
    row = {
        "agent": "tetris_plan", "seed": 2, "lines": 5, "score": 100, "frames": 10,
        "pieces_placed": 3, "stopping_reason": "game_over",
        "clear_sizes": {"singles": 1, "doubles": 0, "triples": 0, "tetrises": 0},
    }
    assert set(probe.rows_by_identity([row], "the row")) == {("tetris_plan", 2)}
    assert set(probe.rows_by_identity([{**row, "seed": 1}], "the row")) == {("tetris_plan", 1)}
    for field, value in (("seed", 2.0), ("seed", True), ("seed", "2"), ("agent", 2)):
        suspect = json.loads(json.dumps(row))
        suspect[field] = value
        with pytest.raises(AssertionError, match="integer seed"):
            probe.rows_by_identity([suspect], "the tampered row")


def test_the_plan_replay_rejects_a_mistyped_retained_identity(tmp_path, monkeypatch):
    """The replay's retained rows carry the writer's identity types too.

    ``reproduce`` builds the retained rows into ``(agent, seed)`` keys before it
    compares anything, so a retained ``seed`` edited to the float ``2.0`` used to
    pass the identity-set check and reproduce the row it was typed to resemble. The
    suite is stubbed from the retained rows, so this path is driven without a native
    run and the tampered record must be rejected.
    """
    probe = _load_plan_probe("exp004_plan_replay_identity_probe")
    retained = json.loads(probe.RESULT_PATH.read_text(encoding="utf-8"))
    rows = retained["episodes_by_agent_seed"]
    episodes = [
        {
            "agent": row["agent"], "seed": row["seed"],
            "pieces_placed": row["pieces_placed"], "clear_sizes": row["clear_sizes"],
            "result": {"lines": row["lines"], "score": row["score"],
                       "frame_count": row["frames"],
                       "stopping_reason": row["stopping_reason"]},
        }
        for row in rows
    ]
    monkeypatch.setattr(probe.runner, "run_suite", lambda configuration: episodes)
    tampered = json.loads(json.dumps(retained))
    tampered["episodes_by_agent_seed"][0]["seed"] = 2.0
    path = tmp_path / "result.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match="integer seed"):
        probe.reproduce(path)


def test_the_plan_engine_manifest_identifies_the_dependency(tmp_path, monkeypatch):
    """The dependency the rows reproduce only on is identified, not asserted.

    The Block Stack working tree the evaluation was measured on is a read-only
    registered checkout whose uncommitted changes cannot be exported, so what this
    repository keeps is the manifest ``fingerprint-engine`` writes: the checkout,
    its commit, its dirty flag and the digest of every source file. The manifest is
    the retained evidence of that dependency, so its own consistency is checked
    wherever it is read -- the entry types, the file count and the digest over its
    own file list -- and the block the result carries is derived from it rather
    than written beside it.
    """
    probe = _load_plan_probe("exp004_plan_engine_manifest_probe")
    retained_manifest = json.loads(probe.ENGINE_MANIFEST.read_text(encoding="utf-8"))
    # The block names the manifest by its project-relative path, so it is derived
    # before the constant is pointed at a temporary copy.
    block = probe.engine_dependency_block(retained_manifest)
    assert block["file_count"] == len(retained_manifest["files"])
    assert block["combined_sha256"] == retained_manifest["combined_sha256"]
    assert block["commit"] == retained_manifest["commit"]

    path = tmp_path / "engine_fingerprint.json"
    path.write_text(json.dumps(retained_manifest), encoding="utf-8")
    monkeypatch.setattr(probe, "ENGINE_MANIFEST", path)
    assert probe.check_engine_manifest()["commit"] == retained_manifest["commit"]

    def tampered(change) -> dict:
        document = json.loads(json.dumps(retained_manifest))
        change(document)
        return document

    cases = (
        (tampered(lambda doc: doc.update(files={})), "lists no source files"),
        (tampered(lambda doc: doc.update(file_count=doc["file_count"] + 1)),
         "is not the"),
        (tampered(lambda doc: doc.update(combined_sha256="0" * 64)),
         "combined digest is not the digest of its own file list"),
        (tampered(lambda doc: doc.update(dirty=0)),
         "dirty flag is not a boolean"),
        (tampered(lambda doc: doc.update(commit="")), "names no commit"),
    )
    for document, message in cases:
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(AssertionError, match=message):
            probe.check_engine_manifest()

    # A digest that is not a sha256 is reported on the entry itself, with the digest
    # over the file list recomputed so the earlier check cannot stand in for it.
    document = tampered(lambda doc: doc["files"].__setitem__("core/src/game.cpp", "nope"))
    document["combined_sha256"] = probe.engine_source_combined(document["files"])
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(AssertionError, match="not a sha256"):
        probe.check_engine_manifest()

    # A manifest that is not on the tree at all is reported rather than skipped: the
    # disclosure has to be backed by an artifact.
    with monkeypatch.context() as patch:
        patch.setattr(probe, "ENGINE_MANIFEST", tmp_path / "absent.json")
        with pytest.raises(AssertionError, match="not on this tree"):
            probe.check_engine_manifest()


def test_the_plan_replay_rejects_a_boolean_for_a_retained_metric(tmp_path, monkeypatch):
    """The replay's aggregate comparison is type-sensitive too.

    ``reproduce`` compares each agent's replayed aggregate with the retained
    ``metrics`` mapping, and a mapping comparison with plain equality accepts a JSON
    boolean wherever the writer recorded a number: ``metrics.tetris_plan.frame_cap_stops``
    set to ``false`` equals the replayed ``0``, so the documented replay entry point
    would report that every retained metric reproduces exactly for a type-corrupted
    record. The suite is stubbed here from the retained rows, so the site is driven
    without a native run, and the tampered record must be rejected.
    """
    probe = _load_plan_probe("exp004_plan_replay_metrics_probe")
    retained = json.loads(probe.RESULT_PATH.read_text(encoding="utf-8"))
    rows = retained["episodes_by_agent_seed"]
    episodes = [
        {
            "agent": row["agent"], "seed": row["seed"],
            "pieces_placed": row["pieces_placed"], "clear_sizes": row["clear_sizes"],
            "result": {"lines": row["lines"], "score": row["score"],
                       "frame_count": row["frames"],
                       "stopping_reason": row["stopping_reason"]},
        }
        for row in rows
    ]
    monkeypatch.setattr(probe.runner, "run_suite", lambda configuration: episodes)

    path = tmp_path / "result.json"
    path.write_text(json.dumps(retained), encoding="utf-8")
    probe.reproduce(path)

    tampered = json.loads(json.dumps(retained))
    assert tampered["metrics"]["tetris_plan"]["frame_cap_stops"] == 0
    tampered["metrics"]["tetris_plan"]["frame_cap_stops"] = False
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match="replayed metrics"):
        probe.reproduce(path)


def test_the_plan_mechanism_claims_are_derived_from_the_model(monkeypatch):
    """The retained prose about the objective's behaviour is derived, not restated.

    Two retained claims of this experiment were written from the design and were
    false about the code. The reserve claim said a nonempty designated well column
    makes the reserve zero; a controller-executable sequence reaches a board whose
    well column is occupied and whose reserve is one, because the I fills the rows
    *above* the column's topmost filled cell. The composition claim said the plan
    composes a current placement "exactly as Experiment 003's objective composes
    them"; the plan adds the current placement's whole value where Experiment 003
    adds only its clear term, and the two select different placements on reachable
    boards in both phases. Both are now derived through ``pathaware`` and
    ``wellplan`` from recorded, executable placement sequences, so a retained copy
    that no longer matches the derivation — a contradicting number, a stale
    sentence or a degenerate case that shows nothing — is reported.
    """
    probe = _load_plan_probe("exp004_plan_mechanism_probe")
    derived = probe.mechanism_claims()
    reserve = derived["reserve_with_an_occupied_well"]
    assert reserve["well_column_mask"] != 0 and reserve["well_reserve"] > 0
    assert tuple(reserve["columns"]) == probe.board_from_sequence(reserve["sequence"])
    assert reserve["well_column_topmost_filled_row"] is not None
    for case in derived["composition_differs_from_experiment_003"]:
        assert case["plan_choice"] != case["prior_composition_choice"]
        assert tuple(case["columns"]) == probe.board_from_sequence(case["sequence"])
    probe.check_mechanism({"objective_mechanism": derived})

    contradicted = json.loads(json.dumps(derived))
    contradicted["reserve_with_an_occupied_well"]["well_reserve"] = 0
    with pytest.raises(AssertionError, match="not the one the tree's model derives"):
        probe.check_mechanism({"objective_mechanism": contradicted})

    stale_sentence = json.loads(json.dumps(derived))
    stale_sentence["reserve_with_an_occupied_well"]["statement"] = (
        "the reserve is zero whenever the well column is not empty")
    with pytest.raises(AssertionError, match="not the one the tree's model derives"):
        probe.check_mechanism({"objective_mechanism": stale_sentence})

    composed_alike = json.loads(json.dumps(derived))
    case = composed_alike["composition_differs_from_experiment_003"][0]
    case["prior_composition_choice"] = case["plan_choice"]
    with pytest.raises(AssertionError, match="not the ones the tree's model derives"):
        probe.check_mechanism({"objective_mechanism": composed_alike})

    missing = json.loads(json.dumps(derived))
    del missing["composition_differs_from_experiment_003"]
    assert missing != derived
    with pytest.raises(AssertionError, match="not the ones the tree's model derives"):
        probe.check_mechanism({"objective_mechanism": missing})

    # The sentinels hold the derivation itself: a sequence that leaves the well
    # column empty, or a case both compositions agree on, cannot be the evidence
    # for the sentence it is paired with, so it is reported rather than read as a
    # weaker form of the claim.
    with monkeypatch.context() as patch:
        patch.setattr(probe, "RESERVE_SEQUENCE", (("I", 1, 4),))
        with pytest.raises(AssertionError, match="empty well column"):
            probe.check_mechanism({"objective_mechanism": probe.mechanism_claims()})
    with monkeypatch.context() as patch:
        patch.setattr(probe, "COMPOSITION_CASES", (
            {"phase": "build", "sequence": (), "piece": "I", "next_piece": "I"},
        ))
        with pytest.raises(AssertionError, match="does not show a divergence"):
            probe.check_mechanism({"objective_mechanism": probe.mechanism_claims()})

    # The observation claim is the third of the class: a copy that no longer matches
    # the model, or one whose boards do not differ only above the ceiling, is
    # reported rather than read as evidence for the sentence it is paired with.
    observation = derived["visible_only_observation"]
    assert observation["columns_differ_only_above_the_ceiling"]
    assert observation["observation_erases_the_buffer"]
    assert observation["stack_height_ceiled"] == observation["stack_height_rendered"]
    assert observation["phase_ceiled"] == observation["phase_rendered"]
    assert observation["reserve_ceiled"] == observation["reserve_rendered"]
    assert observation["plan_value_ceiled"] == observation["plan_value_rendered"]
    stale_observation = json.loads(json.dumps(derived))
    stale_observation["visible_only_observation"]["stack_height_ceiled"] = (
        observation["stack_height_rendered"] + 1)
    with pytest.raises(AssertionError, match="not the one the tree's model derives"):
        probe.check_mechanism({"objective_mechanism": stale_observation})

    original_observation_claim = probe.observation_claim

    def same_board_observation():
        claim = original_observation_claim()
        claim.update(ceiled_columns=claim["rendered_columns"],
                     columns_differ_only_above_the_ceiling=False,
                     statement="the two boards are the same board")
        return claim

    with monkeypatch.context() as patch:
        patch.setattr(probe, "observation_claim", same_board_observation)
        with pytest.raises(AssertionError, match="does not state the case"):
            probe.check_mechanism({"objective_mechanism": probe.mechanism_claims()})

    # The unpatched derivation still passes after both sentinel checks.
    probe.check_mechanism({"objective_mechanism": probe.mechanism_claims()})


def test_the_plan_probe_aggregate_command_runs_without_arguments(monkeypatch, capsys):
    """``all`` and a bare invocation check the capture and the retained result.

    The aggregate command has to be runnable as documented: it re-checks the
    capture against the tree, which ``predeclare`` does by refusing to keep a
    capture whose subject moved, and it re-derives the retained result's own
    claims. The capture-to-run comparison needs a run record, so it takes one as
    an argument instead of being folded into the no-argument path with the
    capture standing in for a record. Its one native step — re-verifying the
    frozen writer's retained record — is stubbed here so this check stays
    engine-independent; ``test_integration.py`` runs the same command with that
    step real.
    """
    probe = _load_plan_probe("exp004_plan_aggregate_probe")
    legacy_checks: list[bool] = []
    monkeypatch.setattr(probe, "check_legacy", lambda: legacy_checks.append(True))
    probe.all_probes()
    assert legacy_checks == [True]
    assert "existing predeclaration kept" in capsys.readouterr().out
    assert probe.main([]) == 0
    assert probe.main(["all"]) == 0
    assert legacy_checks == [True, True, True]


def test_the_writer_records_the_loaded_code_not_a_later_edit(tmp_path, monkeypatch):
    """The writer's identity is fixed when the module loads, not read from its path.

    ``module.__file__`` is only a path: the bytes there at some later moment can
    be source the process never ran. The writer's identity is therefore taken from
    the loader that read the module's source, so an edit that lands afterwards
    cannot be recorded as the code that chose the inputs. Pointing a covered
    module at a mutated copy — the shape an edited tree has, without rewriting
    this checkout's source — separates the two views: the loaded identity ignores
    the copy, and the verifier's view of the tree follows it. That the two agree
    while the file is unchanged is what keeps every retained record verifying.
    """
    loaded = runner._objective_sources(loaded=True)
    assert loaded == runner._objective_sources()
    assert loaded["block_stack_ai.tetris"] == hashlib.sha256(
        Path(tetris_module.__file__).read_bytes()).hexdigest()

    mutated = tmp_path / "tetris.py"
    mutated.write_bytes(
        Path(tetris_module.__file__).read_bytes() + b"\n# edited after the load\n"
    )
    monkeypatch.setattr(tetris_module, "__file__", str(mutated))
    assert runner._objective_sources(loaded=True) == loaded
    assert runner._objective_sources() == {
        **loaded, "block_stack_ai.tetris": hashlib.sha256(mutated.read_bytes()).hexdigest(),
    }


# The reviewer's counterexample, the load order that separates a record's identity
# from the file on the tree, lives in the experiment as a program rather than
# inline here: the ordering only exists in a fresh process against a copy of the
# tree, so the test, ``evidence.py loaded-identity`` and ``prechange_probe.py
# loaded_identity`` all run the same file and each asserts the contract on its
# JSON. A process that already imported this tree's modules cannot replay the
# ordering, which is why the program is spawned rather than imported.
COUNTEREXAMPLE_PROGRAM = (
    engine.PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "probes"
    / "loaded_identity_program.py"
)
# The same defect through the interpreter's own bytecode cache: the program reports
# the constant the loaded code declares, the constant the file declares and the
# digest the writer recorded, and the helper below puts a tree in the state where
# the first two can differ.
STALE_CACHE_PROGRAM = (
    engine.PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "probes"
    / "stale_cache_program.py"
)



def _run_counterexample(root, *, edit=False, mode=None):
    """Run the counterexample program against its own copy of this package."""
    package = Path(sys.modules["block_stack_ai"].__file__).resolve().parent
    source_root = root / "src"
    source_root.mkdir(parents=True)
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    completed = subprocess.run(
        [sys.executable, str(COUNTEREXAMPLE_PROGRAM),
         mode or ("edit" if edit else "clean"), str(root)],
        cwd=root, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(source_root)},
    )
    assert completed.returncode == 0, completed.stderr
    measured = json.loads(completed.stdout)
    assert measured["package"] == str(source_root / package.name / "__init__.py")
    return measured


def test_an_edit_after_the_load_is_reported_rather_than_certified(tmp_path):
    """The reviewer's counterexample: a record must not name code that did not run.

    A process that imports the objective's modules, has one of their files edited,
    and only then imports the writer records the edited bytes if the identity is
    read from the path at that moment — while ``sys.modules`` still executes the
    loaded code — and a later verification reads the edited file too, so it
    certifies provenance that never held. The opposite ordering is the control:
    with the file untouched the writer's identity, the verifier's view of the tree
    and the recorded identity all agree and the record verifies, so the report
    below is the edit and nothing else.
    """
    clean = _run_counterexample(tmp_path / "clean", edit=False)
    assert clean["outcome"]["verified"] is True
    assert clean["loaded"] == clean["before"] == clean["on_disk"]
    assert clean["record"] == clean["tree"] == clean["before"]

    edited = _run_counterexample(tmp_path / "edited", edit=True)
    assert edited["before"] != edited["on_disk"]
    assert edited["loaded"] == edited["record"] == edited["before"]
    assert edited["tree"] == edited["on_disk"]
    assert edited["outcome"]["verified"] is False
    assert "objective.sources.block_stack_ai.tetris" in edited["outcome"]["error"]


def _stale_cache_tree(root):
    """A copy of this package with a compiled cache and an edited covered module.

    The copy is compiled first, so a ``__pycache__`` entry exists; then
    ``tetris.py`` is edited to the same size and its mtime restored, which is what
    keeps Python's timestamp validation accepting that entry while the source
    beside it has changed. That is the state in which a loader that digests one
    read and executes another names code that did not run.
    """
    package = Path(sys.modules["block_stack_ai"].__file__).resolve().parent
    source_root = root / "src"
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    compiled = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(source_root / package.name)],
        capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    source = source_root / package.name / "tetris.py"
    before = source.stat()
    text = source.read_text(encoding="utf-8")
    edited = text.replace("WELL_DEPTH_CAP = 4", "WELL_DEPTH_CAP = 5")
    assert edited != text and len(edited.encode()) == len(text.encode())
    source.write_text(edited, encoding="utf-8")
    os.utime(source, (before.st_atime, before.st_mtime))
    after = source.stat()
    assert (after.st_size, int(after.st_mtime)) == (before.st_size, int(before.st_mtime))
    return source_root


def test_the_identity_names_the_code_that_runs_beside_a_stale_cache(tmp_path):
    """The identity is the code that ran, not source beside a bytecode cache.

    The reviewer's counterexample: the recorder digested one read of each covered
    module's source while execution was delegated to the loader that read it, and
    that loader may execute a ``__pycache__`` entry instead — Python accepts one
    while the source it was built from still matches by integer-second mtime and
    size, so a same-length edit inside that second leaves the cache to be executed
    while a separate read returns the edited text. The record then names source the
    process did not run, and verification reads the same file and certifies it.
    Here the compiled cache is stale in exactly that way: the executed constant,
    the constant the file declares and the recorded digest must all be the same
    source.
    """
    source_root = _stale_cache_tree(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(STALE_CACHE_PROGRAM)], cwd=tmp_path,
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(source_root)},
    )
    assert completed.returncode == 0, completed.stderr
    measured = json.loads(completed.stdout)
    assert measured["source"] == 5, measured
    assert measured["executed"] == measured["source"], (
        "the identity names source the interpreter did not run: the loaded code "
        f"declares {measured['executed']} while the file declares {measured['source']}"
    )
    assert measured["recorded"] == measured["file"] and measured["agrees"] is True


def test_verification_rejects_a_wrapper_change_that_keeps_the_recorded_choices(
    tmp_path, monkeypatch
):
    """The identity covers the wrapper that drives the objective, not only the objective.

    The wrapper imports the objective, so a walk outward from the objective can
    never reach it. The reviewer's finding: changing the wrapper — a state
    parameter it hands the objective, or bypassing the objective altogether —
    then leaves the recorded identity and the replayed choices both unchanged, so
    a record whose placements no longer came from the recorded objective is
    certified. Each changed wrapper here is a copy of the module's own source
    pointed at through ``__file__``, so the replay still runs the loaded code and
    the recorded seeds keep exactly the actions they recorded; the identity is
    the only thing that can report the change.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []
    source = Path(agents_module.__file__).read_text(encoding="utf-8")
    # The wrapper hands the objective the state it reads; this copy hands it a
    # different level, from which the same reachable set is scored differently.
    handed = source.replace(
        "        return tetris_choice(\n"
        "            grid,\n"
        "            state.current_piece,\n"
        "            state.next_piece,\n"
        "            level=state.level,\n",
        "        return tetris_choice(\n"
        "            grid,\n"
        "            state.current_piece,\n"
        "            state.next_piece,\n"
        "            level=state.level + 1,\n",
    )
    # The other shape of the same finding: the wrapper still imports the objective
    # and no longer calls it, so the placements come from 002's frozen value.
    bypassed = source.replace(
        "        return tetris_choice(\n", "        return lookahead_choice(\n")
    assert handed != source and bypassed != source
    for index, (label, changed) in enumerate(
        (("a state parameter changed", handed), ("the objective bypassed", bypassed))
    ):
        copied = tmp_path / f"agents-{index}.py"
        copied.write_text(changed, encoding="utf-8")
        with monkeypatch.context() as patch:
            patch.setattr(agents_module, "__file__", str(copied))
            with pytest.raises(
                VerificationError,
                match=r"objective\.sources\.block_stack_ai\.agents: recorded "
                      rf"'{record['objective']['sources']['block_stack_ai.agents']}', "
                      r"replayed '[0-9a-f]{64}'",
            ):
                verify_run(path, factory)
    # The module's own file leaves the same record verifying: the identity rejects
    # the changed wrapper and nothing else.
    assert verify_run(path, factory) == []


def test_the_version_5_identity_stops_before_the_wrapper(tmp_path, monkeypatch):
    """A retained version-5 record is compared against the identity it recorded.

    The version-5 writer walked outward from the module that declares the
    objective, which cannot reach the wrapper that drives it, so that version's
    records are compared with that shape — a record carrying the wrapper's digest
    under that version is a section no writer emitted, and is reported. The
    version-6 and version-7 writers record the wrapper, so the walk of those
    versions is the version-5 shape plus the modules that decide which
    implementation is built: the shared factory for the agent the factory defines
    under version 6, and the runner's dispatch under version 7. Each version is
    compared against its own shape, so deleting a module that shape carries is a
    deleted key rather than an accepted narrower one.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    outward = runner._objective_sources(runner._IDENTITY_OUTWARD)
    version_6 = runner._objective_sources(runner._IDENTITY_CHOICE)
    assert set(outward) == set(version_6) - {"block_stack_ai.agents"}
    assert set(version_6) == set(record["objective"]["sources"]) - {
        "block_stack_ai.engine", "block_stack_ai.runner"}

    prior = json.loads(json.dumps(record))
    prior["format_version"] = runner.OUTWARD_IDENTITY_SUITE_FORMAT_VERSION
    prior["objective"]["sources"] = outward
    path.write_text(json.dumps(prior), encoding="utf-8")
    assert verify_run(path, factory) == []

    # The version-5 writer recorded no wrapper digest, so one is an extra key that
    # no run of that version produced.
    mixed = json.loads(json.dumps(prior))
    mixed["objective"]["sources"]["block_stack_ai.agents"] = (
        record["objective"]["sources"]["block_stack_ai.agents"])
    path.write_text(json.dumps(mixed), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"Recorded objective\.sources keys \['block_stack_ai\.agents',",
    ):
        verify_run(path, factory)

    # At the current version the wrapper belongs to the identity, so dropping it
    # is a deleted key rather than an accepted legacy shape.
    stripped = json.loads(json.dumps(record))
    del stripped["objective"]["sources"]["block_stack_ai.agents"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"do not match \['block_stack_ai\.agents',",
    ):
        verify_run(path, factory)


def test_a_current_tetris_record_covers_the_dispatcher_and_cannot_shed_it(
    tmp_path, monkeypatch
):
    """The finding: a current Tetris record's identity covers the dispatch.

    ``run_suite`` builds every agent through ``runner.build_agent``, so the
    dispatch is the code that decides which implementation a record's placements
    came from. The version-6 walk named the shared factory for an agent the factory
    defines, which left the dispatch out of a Tetris record, and a change to the
    dispatch that still replayed the recorded inputs was invisible to it. The
    current walk seeds the dispatch for every agent, so the same change is reported
    — and because the walk is keyed by the record's own version, a current record
    cannot shed the coverage by claiming the version whose shape stopped short of
    it: the recorded seven-module identity does not equal that version's five.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    runner_digest = hashlib.sha256(Path(runner.__file__).read_bytes()).hexdigest()
    assert record["objective"]["sources"]["block_stack_ai.runner"] == runner_digest
    assert verify_run(path, factory) == []

    mutated = tmp_path / "runner-changed.py"
    mutated.write_bytes(Path(runner.__file__).read_bytes() + b"\n# dispatch changed\n")
    with monkeypatch.context() as patch:
        patch.setattr(runner, "__file__", str(mutated))
        with pytest.raises(
            VerificationError,
            match=r"objective\.sources\.block_stack_ai\.runner: recorded "
                  rf"'{runner_digest}', replayed '[0-9a-f]{{64}}'",
        ):
            verify_run(path, factory)

    # Relabelling to the version whose walk stopped at the shared factory does not
    # strip the dispatcher: that version's shape is five modules, and the record
    # carries seven, so the relabel is reported as a difference.
    relabelled = json.loads(json.dumps(record))
    relabelled["format_version"] = runner.WRAPPER_IDENTITY_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(relabelled), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"objective\.sources"):
        verify_run(path, factory)

    # The two shapes are nested: the version-6 walk is the current one minus the
    # modules that name the dispatcher. A record *rewritten* into the version-6
    # shape is therefore indistinguishable from one that writer emitted, and it is
    # accepted for the same reason Experiment 003's retained records are — the
    # format version is the record's own claim about which writer produced it, and
    # the version-6 writer's records have to keep verifying. What the wider shape
    # closes is the coverage of a record written now, which is what the finding asks
    # for; deleting the keys while *keeping* the version is the edit that is caught,
    # because the recorded identity then equals neither shape.
    assert set(runner._objective_sources(runner._IDENTITY_CHOICE)) < set(
        record["objective"]["sources"])
    shedded = json.loads(json.dumps(relabelled))
    for name in ("block_stack_ai.runner", "block_stack_ai.engine"):
        del shedded["objective"]["sources"][name]
    assert shedded["objective"]["sources"] == runner._objective_sources(
        runner._IDENTITY_CHOICE)

    # The unedited record still verifies, so the identity rejects the relabel and
    # nothing else.
    path.write_text(json.dumps(record), encoding="utf-8")
    assert verify_run(path, factory) == []


def test_a_changed_live_controller_is_reported_for_a_version_8_record(
    tmp_path, monkeypatch
):
    """A live record covers the controller that drove it; the pre-fix shape did not.

    The reviewer's finding: ``LiveSession.receive`` decides when and how each
    desktop observation reaches the agent and executes the mask it returns, while
    the version-7 identity covered only the objective and the runner. A change to
    the controller that still produced the recorded masks was therefore certified,
    and the headless verifier accepted the record. A version-8 record carries the
    live walk, so the same mutated controller is reported here — and the same
    record under version 7, the shape the pre-fix writer emitted, still verifies,
    which is the legacy guarantee and the gap the new version closes. The replay
    never imports the live session, so the identity is the only thing that can
    report the change; the mutation is a copy pointed at through ``__file__``, so
    the loaded controller that produced the recorded masks is what actually ran.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch, agents=("tetris",))
    assert record["format_version"] == runner.SUITE_FORMAT_VERSION
    assert live_module.__name__ not in record["objective"]["sources"]
    live_record = json.loads(json.dumps(record))
    live_record["format_version"] = runner.LIVE_SUITE_FORMAT_VERSION
    live_record["objective"]["sources"] = runner._objective_sources(runner._IDENTITY_LIVE)
    live_record["controller"] = runner._controller_identity()
    path.write_text(json.dumps(live_record), encoding="utf-8")
    assert verify_run(path, factory) == []

    source = Path(live_module.__file__).read_text(encoding="utf-8")
    # A real change to when observations reach the agent: every other state is
    # dropped. The replay never reads this file, so the recorded masks are
    # unchanged and only the identity can report the controller that chose them.
    changed = source.replace(
        "        if kind == \"STATE\":\n",
        "        if kind == \"STATE\" and len(self.inputs) % 2 == 0:\n",
    )
    assert changed != source
    mutated = tmp_path / "live-changed.py"
    mutated.write_text(changed, encoding="utf-8")
    recorded = live_record["objective"]["sources"][live_module.__name__]
    with monkeypatch.context() as patch:
        patch.setattr(live_module, "__file__", str(mutated))
        with pytest.raises(
            VerificationError,
            match=rf"objective\.sources\.block_stack_ai\.live: recorded "
                  rf"'{recorded}', replayed '[0-9a-f]{{64}}'",
        ):
            verify_run(path, factory)
        # The version-7 writer never named the live module, so the same mutated
        # controller leaves that shape verifying. That record is the pre-fix
        # writer's output, compared against the walk its own writer recorded.
        path.write_text(json.dumps(record), encoding="utf-8")
        assert verify_run(path, factory) == []
    path.write_text(json.dumps(live_record), encoding="utf-8")
    assert verify_run(path, factory) == []


def test_a_version_8_record_without_an_objective_still_names_the_controller(
    tmp_path, monkeypatch
):
    """The controller section is what covers the agents that declare no objective.

    A live game of ``greedy``, ``random`` or ``lookahead`` declares no objective,
    so its record carries no ``objective`` section and, before this section, no
    source identity at all: a change to ``LiveSession.receive`` that preserved
    the replayed masks was certified for every one of them. Version 8 requires
    the controller section on every record, including these, and the section's
    walk stops before the declared objectives because those choices never run
    one. The same record under version 7 still verifies, because that writer
    emitted no controller section and its records have to keep verifying.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch, agents=("greedy",))
    assert "objective" not in record
    assert "controller" not in record
    live_record = json.loads(json.dumps(record))
    live_record["format_version"] = runner.LIVE_SUITE_FORMAT_VERSION
    path.write_text(json.dumps(live_record), encoding="utf-8")
    # The section is required at the version whose writer emits it, so its
    # absence is a deleted section rather than an older record.
    with pytest.raises(VerificationError, match=r"controller: absent, but a record"):
        verify_run(path, factory)

    live_record["controller"] = runner._controller_identity()
    path.write_text(json.dumps(live_record), encoding="utf-8")
    assert verify_run(path, factory) == []

    source = Path(live_module.__file__).read_text(encoding="utf-8")
    changed = source.replace(
        "        if kind == \"STATE\":\n",
        "        if kind == \"STATE\" and len(self.inputs) % 2 == 0:\n",
    )
    assert changed != source
    mutated = tmp_path / "live-changed.py"
    mutated.write_text(changed, encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(live_module, "__file__", str(mutated))
        with pytest.raises(
            VerificationError,
            match=r"controller\.sources\.block_stack_ai\.live: recorded",
        ):
            verify_run(path, factory)
    # A controller section in a version whose writer emitted none was added, and
    # is reported instead of accepted as though an older writer had produced it;
    # the same record under version 7 verifies, because no older writer emitted
    # the section and its records have to keep verifying.
    path.write_text(json.dumps(record), encoding="utf-8")
    assert verify_run(path, factory) == []
    older = json.loads(json.dumps(record))
    older["controller"] = runner._controller_identity()
    path.write_text(json.dumps(older), encoding="utf-8")
    with pytest.raises(VerificationError, match=r"controller: no writer of this format"):
        verify_run(path, factory)
    path.write_text(json.dumps(live_record), encoding="utf-8")
    assert verify_run(path, factory) == []


@pytest.mark.parametrize(
    "seeds,agents",
    [([1, 2], ["greedy"]), ([1], ["greedy", "lookahead"])],
)
def test_a_version_8_record_must_configure_the_single_live_game(
    tmp_path, monkeypatch, seeds, agents
):
    """Only the live writer's one-game configuration may claim the live format.

    ``play_live`` narrows its configuration to one seed and one agent before the
    session writes the single episode, so a version-8 record with several episodes
    is not something the live writer emits. Without the check, a multi-episode
    headless suite relabelled to version 8 and supplied with the current
    controller identity verified as though the interactive session had produced
    it; the same record at its own headless version still verifies.
    """
    monkeypatch.setattr(runner, "engine_root", lambda: Path("/engine"))
    monkeypatch.setattr(
        runner, "git_info",
        lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"},
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "game": SUITE["game"], "frame_limit": 2, "seeds": seeds, "agents": agents,
    }), encoding="utf-8")
    factory = lambda **_: ChoiceGame()
    path = run_and_save(config_path, tmp_path / "runs", factory)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert len(record["episodes"]) == len(seeds) * len(agents) > 1
    live = json.loads(json.dumps(record))
    live["format_version"] = runner.LIVE_SUITE_FORMAT_VERSION
    live["controller"] = runner._controller_identity()
    path.write_text(json.dumps(live), encoding="utf-8")
    with pytest.raises(VerificationError,
                       match=r"exactly one agent and one seed"):
        verify_run(path, factory)
    path.write_text(json.dumps(record), encoding="utf-8")
    assert verify_run(path, factory) == []


def test_a_reloaded_live_session_is_refused_not_recorded():
    """A session the live reload left stale is refused before any identity is captured.

    ``importlib.reload(live)`` creates a new ``LiveSession`` class while an
    existing instance keeps executing the previous class's ``receive``. Every
    module global that method resolves now comes from the reloaded module, so an
    identity captured on its next call would name controller bytes that never
    chose the inputs and the record would verify falsely. The guard is the class
    identity, checked before any branch runs, so a session built from the
    previous class is refused outright rather than stamped with the reloaded
    module's digest. The check drives the guard directly, without a native game,
    because the refusal must not depend on the engine.
    """
    class StaleSession:
        pass

    with pytest.raises(VerificationError, match="reloaded after this session"):
        live_module.LiveSession.receive(StaleSession(), "BEGIN", b"")


def test_objective_identity_is_required_at_the_current_version_and_optional_before(
    tmp_path, monkeypatch
):
    """The identity is newer than the objective section, so it is gated separately.

    The version-4 writer recorded the objective's module and weights but no
    identity, and the version-2 writer recorded no objective at all; the retained
    records of both keep verifying. The current version's writer always records
    the identity, so deleting it from a record of that version is a deleted
    section and is reported. An identity a record does carry is compared at every
    version, so an edited one does not verify merely because its version predates
    the writer that emits it.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)

    stripped = json.loads(json.dumps(record))
    del stripped["objective"]["sources"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"objective\.sources: absent, but a record of this format version always "
              r"carries it",
    ):
        verify_run(path, factory)

    for version in (runner.PRIOR_SUITE_FORMAT_VERSION, runner.LEGACY_SUITE_FORMAT_VERSION):
        prior = json.loads(json.dumps(stripped))
        prior["format_version"] = version
        path.write_text(json.dumps(prior), encoding="utf-8")
        assert verify_run(path, factory) == [], version

        edited = json.loads(json.dumps(record))
        edited["format_version"] = version
        edited["objective"]["sources"]["block_stack_ai.tetris"] = "0" * 64
        path.write_text(json.dumps(edited), encoding="utf-8")
        with pytest.raises(
            VerificationError,
            match=r"objective\.sources\.block_stack_ai\.tetris: recorded '0{64}', "
                  r"replayed '[0-9a-f]{64}'",
        ):
            verify_run(path, factory)


def test_verification_rejects_a_formula_change_that_leaves_the_weights_alone(
    tmp_path, monkeypatch
):
    """The weights are constants; the formula around them is what the identity pins.

    The reviewer's counterexample: the objective's clear term charges a premature
    clear at twice the declared rate. Every weight is unchanged — the changed
    module's own ``weights_record()`` equals the record's, value for value — so the
    weight comparison cannot tell the two objectives apart, and the replayed
    choices need not move either: the recorded episode is replayed through a
    stand-in that ignores the mask, so it matches under both formulas. The
    identity is what changes, and the record no longer verifies. Patching
    ``__file__`` points the verifier at a copy holding the changed formula, which
    is what a tree whose module was edited looks like, without rewriting this
    checkout's source.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []

    source = Path(tetris_module.__file__).read_text(encoding="utf-8")
    changed = source.replace(
        'return TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
        'return 2 * TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
    )
    # The one edit is the clear term's multiple: putting it back recovers the
    # original module byte for byte, so no weight constant moved.
    assert changed != source
    assert changed.replace(
        'return 2 * TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
        'return TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
    ) == source

    # The changed formula is a real second objective: its weights are the record's
    # and its clear term is not, so nothing but the identity can separate them.
    qualified = (changed
                 .replace("from .heuristic import", "from block_stack_ai.heuristic import")
                 .replace("from .pathaware import", "from block_stack_ai.pathaware import"))
    namespace: dict = {}
    exec(compile(qualified, "tetris_changed.py", "exec"), namespace)
    assert namespace["weights_record"]() == record["objective"]["weights"]
    assert namespace["clear_term"](1) == 2 * tetris_module.clear_term(1) == -6.0

    original = tetris_module.__file__
    copied = tmp_path / "tetris.py"
    copied.write_text(changed, encoding="utf-8")
    monkeypatch.setattr(tetris_module, "__file__", str(copied))
    with pytest.raises(
        VerificationError,
        match=r"objective\.sources\.block_stack_ai\.tetris: recorded "
              rf"'{record['objective']['sources']['block_stack_ai.tetris']}', "
              r"replayed '[0-9a-f]{64}'",
    ):
        verify_run(path, factory)

    # The module's own file leaves the same record verifying: the identity rejects
    # the changed formula and nothing else.
    monkeypatch.setattr(tetris_module, "__file__", original)
    assert verify_run(path, factory) == []


def test_verification_rejects_a_tampered_objective(tmp_path, monkeypatch):
    """A declared objective is compared, not merely recorded.

    A record whose objective was changed after it was written — a weight, the
    module name, a missing key, or a JSON boolean in a weight — must not verify,
    or the record would keep its authority under an objective that is not the one
    that chose its placements.
    """
    path, factory, record = _objective_suite(tmp_path, monkeypatch)
    assert verify_run(path, factory) == []

    def rejected(tamper, message):
        tampered = json.loads(json.dumps(record))
        path.write_text(json.dumps(tamper(tampered)), encoding="utf-8")
        with pytest.raises(VerificationError, match=message):
            verify_run(path, factory)

    def changed_weight(tampered):
        tampered["objective"]["weights"]["tetrises"] = 1.0
        return tampered

    def changed_module(tampered):
        tampered["objective"]["module"] = "block_stack_ai.heuristic"
        return tampered

    def missing_key(tampered):
        del tampered["objective"]["weights"]["well_depth"]
        return tampered

    def boolean_weight(tampered):
        tampered["objective"]["weights"]["well_depth"] = True
        return tampered

    rejected(changed_weight, r"objective\.weights\.tetrises: recorded 1\.0, replayed 8\.0")
    rejected(changed_module, r"objective\.module: recorded 'block_stack_ai\.heuristic', "
                             r"replayed 'block_stack_ai\.tetris'")
    rejected(missing_key, r"Recorded objective\.weights keys .* do not match")
    rejected(boolean_weight, r"Recorded objective\.weights\.well_depth must be float, not True")


def test_verification_rejects_an_objective_in_a_suite_without_one(
    tmp_path, monkeypatch
):
    """No writer declares an objective for a suite whose agents all use the frozen score."""
    path, factory, record = _objective_suite(tmp_path, monkeypatch, agents=("greedy",))
    assert "objective" not in record
    record["objective"] = {
        "module": "block_stack_ai.tetris", "weights": tetris_weights_record(),
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        VerificationError,
        match=r"objective: the configuration declares no agent whose choices",
    ):
        verify_run(path, factory)


# The earlier publication the finding measured: the refs named this commit while
# the reviewed worktree held the repair, and every repaired path existed in it.
PUBLISHED_COMMIT = "dc3c29c449c439ad8df415404d4df6d0eeb0087f"
OLDER_WORKTREE_HEAD = "6e21ab8426b534c5de96e2f648b55fc0901e0ab6"
PUBLISHED_CONTENT = "the earlier publication's file\n"
REPAIRED_CONTENT = "the repair this worktree holds uncommitted\n"
# The state lines the probe prints, pinned as literals: the counterexample must
# fail on the pre-repair probe's behaviour (it printed presence rows and no state
# line) instead of aborting on a missing attribute.
STATE_EQUAL_PREFIX = "published content equals this worktree"
STATE_EARLIER_PREFIX = "the refs name an earlier publication"


def _load_evidence_probe(name="exp003_evidence_probe"):
    """The 003 probe file, loaded from the experiment so its checks can be driven."""
    path = (engine.PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "probes"
            / "evidence.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_publication_probe():
    """The 003 publication probe, loaded from its own file in the experiment."""
    return _load_evidence_probe("exp003_publication_probe")


def _drive_publication_probe(probe, tmp_path, monkeypatch, *, worktree_content,
                             uncommitted, worktree_head=OLDER_WORKTREE_HEAD,
                             published_same=(), outside_paths=(), worktree_deleted=(),
                             worktree_added=(), tracked_missing=(),
                             untracked_directories=()):
    """Run ``check_publication`` against real content with the Git plumbing stubbed.

    The published clone and the worktree are real directories whose paths hold
    real content, so the probe's comparison runs for real; only the Git commands
    are stubbed, which is what makes the states below deterministic and offline.
    ``published_same`` names the declared paths whose published content is the
    worktree's own; every other declared path holds ``PUBLISHED_CONTENT``.
    ``outside_paths`` are tracked in both trees but outside the probe's declared
    list, with the worktree holding ``REPAIRED_CONTENT`` and the publication
    ``PUBLISHED_CONTENT``. ``worktree_deleted`` names declared paths that stay
    tracked but are deleted from the worktree, so they exist only in the
    publication. ``worktree_added`` names paths that exist only in the worktree,
    reported as untracked by ``git status``, ``tracked_missing`` names paths both
    trees list as tracked but neither actually holds, and ``untracked_directories``
    names directories that exist only in the worktree, which Git reports as one
    untracked entry each. The clone directory must not exist beforehand, because
    the probe clears it before cloning.
    """
    published_root = tmp_path / "publication"
    worktree_root = tmp_path / "worktree"
    tracked = list(probe.REPAIRED_PATHS) + list(outside_paths) + list(tracked_missing)
    for path in probe.REPAIRED_PATHS:
        if path in worktree_deleted:
            continue
        target = worktree_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(worktree_content, encoding="utf-8")
    for path in outside_paths:
        target = worktree_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(REPAIRED_CONTENT, encoding="utf-8")
    for path in worktree_added:
        target = worktree_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(REPAIRED_CONTENT, encoding="utf-8")
    for path in untracked_directories:
        (worktree_root / path).mkdir(parents=True, exist_ok=True)

    def fake_git(cwd, *arguments):
        command = " ".join(arguments)
        if command.startswith("ls-remote"):
            return 0, (f"{PUBLISHED_COMMIT}\t{probe.TASK_BRANCH_REF}\n"
                       f"{PUBLISHED_COMMIT}\t{probe.TASK_PR_REF}")
        if command.startswith("clone "):
            for path in probe.REPAIRED_PATHS:
                content = worktree_content if path in published_same else PUBLISHED_CONTENT
                target = published_root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            for path in outside_paths:
                target = published_root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(PUBLISHED_CONTENT, encoding="utf-8")
            return 0, ""
        if command == "ls-files -z":
            return 0, "\0".join(tracked) + "\0"
        if Path(cwd) == published_root:
            if command == "rev-parse HEAD":
                return 0, PUBLISHED_COMMIT
            if command == "rev-parse HEAD^{tree}":
                return 0, "a" * 40
            if command.startswith("merge-base --is-ancestor"):
                return 0, ""
        if Path(cwd) == worktree_root:
            if command == "rev-parse HEAD":
                return 0, worktree_head
            if command == "status --porcelain":
                # As the probe's own _git would: the captured output is stripped,
                # so the first entry loses its leading status column. Untracked
                # paths are reported the way Git reports them.
                entries = [f" M {path}" for path in uncommitted
                           if path not in worktree_added]
                entries += [f"?? {path}" for path in worktree_added]
                entries += [f"?? {path}" for path in untracked_directories]
                return 0, "\n".join(entries).strip()
        raise AssertionError(f"unexpected git command: {command}")

    monkeypatch.setattr(probe, "PUBLICATION_CLONE", published_root)
    monkeypatch.setattr(probe, "PROJECT_ROOT", worktree_root)
    monkeypatch.setattr(probe, "_git", fake_git)
    return fake_git


def test_publication_probe_holds_on_a_committed_tree(tmp_path, monkeypatch):
    """The probe must pass on the committed tree it is run against.

    The earlier version required this worktree's HEAD to be a recorded
    pre-publication commit with the repair still uncommitted, which a committed,
    published tree cannot satisfy — the documented ``evidence.py all`` path failed
    there. This drives the probe's own checks on a worktree whose HEAD is an older
    commit and which still has uncommitted changes, and requires it to pass; a
    branch ref and PR head that disagree must still fail, so the probe keeps its
    teeth.
    """
    probe = _load_publication_probe()
    fake_git = _drive_publication_probe(
        probe, tmp_path, monkeypatch,
        worktree_content=REPAIRED_CONTENT, uncommitted=list(probe.REPAIRED_PATHS))
    probe.check_publication()

    def disagreeing_git(cwd, *arguments):
        if arguments[0] == "ls-remote":
            return 0, (f"{PUBLISHED_COMMIT}\t{probe.TASK_BRANCH_REF}\n"
                       f"{OLDER_WORKTREE_HEAD}\t{probe.TASK_PR_REF}")
        return fake_git(cwd, *arguments)

    monkeypatch.setattr(probe, "_git", disagreeing_git)
    with pytest.raises(AssertionError):
        probe.check_publication()


def test_publication_probe_reports_content_not_presence_when_the_refs_lag(
    tmp_path, monkeypatch, capsys
):
    """A published tree that only happens to contain the paths is not the repair.

    The reviewer's counterexample: the refs name the earlier publication
    ``PUBLISHED_COMMIT``, whose repaired-path contents differ from the reviewed
    worktree across many files, while every path exists in it. The probe must
    compare content, report that the refs name an earlier publication and which
    paths differ, and never print that this worktree's content is published.
    """
    probe = _load_publication_probe()
    _drive_publication_probe(
        probe, tmp_path, monkeypatch,
        worktree_content=REPAIRED_CONTENT, uncommitted=list(probe.REPAIRED_PATHS))
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert STATE_EQUAL_PREFIX not in printed
    for path in probe.REPAIRED_PATHS:
        assert f"differs {path} " in printed, printed
    assert f"{len(probe.REPAIRED_PATHS)} of {len(probe.REPAIRED_PATHS)} compared paths differ" \
        in printed


def test_publication_probe_detects_a_changed_path_outside_the_declared_list(
    tmp_path, monkeypatch, capsys
):
    """Every path either tree tracks is compared, not only a declared list.

    The reviewer's counterexample: the publication differs from this worktree in
    one tracked path that the probe's declared list does not name, while every
    declared path is equal. A comparison driven by the declared list alone prints
    the equal-content certification there and certifies a publication that is not
    this tree; the derived set must report the earlier-publication state and name
    the differing path.
    """
    probe = _load_publication_probe()
    outside = "experiments/003-tetris-aware-agent/config.json"
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
        uncommitted=[outside], published_same=probe.REPAIRED_PATHS,
        outside_paths=[outside])
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert STATE_EQUAL_PREFIX not in printed
    assert f"differs {outside} (outside the declared repaired paths)" in printed
    assert f"1 of {len(probe.REPAIRED_PATHS) + 1} compared paths differ" in printed


def test_publication_probe_reports_a_tracked_path_deleted_in_the_worktree(
    tmp_path, monkeypatch, capsys
):
    """A tracked deletion is a reported state, not a crash.

    The reviewer's counterexample: the publication tracks a path this worktree has
    deleted, so the path has a published digest and none here. The earlier probe
    sliced the absent digest and raised ``TypeError`` instead of reporting
    anything, so a worktree that deleted one compared path could not complete the
    publication report at all. The probe must name the deletion, report the
    earlier-publication state, and finish without an exception.
    """
    probe = _load_publication_probe()
    deleted = probe.REPAIRED_PATHS[0]
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=REPAIRED_CONTENT,
        uncommitted=[deleted], worktree_deleted=[deleted],
        published_same=[path for path in probe.REPAIRED_PATHS if path != deleted])
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert STATE_EQUAL_PREFIX not in printed
    assert f"deleted {deleted}:" in printed
    assert f"deleted {deleted}: tracked in the published tree sha256" in printed
    assert f"1 of {len(probe.REPAIRED_PATHS)} compared paths differ" in printed


def test_publication_probe_reports_a_path_added_since_the_publication(
    tmp_path, monkeypatch, capsys
):
    """A path that exists only in this worktree is reported as that state.

    The counterpart of the tracked deletion: a file this worktree added and has not
    committed is untracked here and absent from the publication, so it has no
    published digest and a worktree digest. The replaced probe printed such a path
    as a bare `MISSING` row, without the state the comparison is in; this probe must
    name the added state, report the earlier-publication state (the publication does
    not carry the file) and finish.
    """
    probe = _load_publication_probe()
    added = "experiments/003-tetris-aware-agent/probes/new-probe.py"
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
        uncommitted=[added], worktree_added=[added],
        published_same=probe.REPAIRED_PATHS)
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert (f"added {added} (outside the declared repaired paths): absent from the published "
            "tree, present in this worktree sha256") in printed
    assert f"1 of {len(probe.REPAIRED_PATHS) + 1} compared paths differ" in printed


def test_publication_probe_reports_a_compared_path_that_is_a_directory(
    tmp_path, monkeypatch, capsys
):
    """A compared path that is a directory is described, not read as a file.

    An untracked directory is one `git status` entry, so it reaches the comparison
    as a path with no published digest and no digest here either — reading it would
    raise `IsADirectoryError` — while the directory itself is present. The report
    must say so, keep the earlier-publication state, and finish without an
    exception.
    """
    probe = _load_publication_probe()
    directory = "experiments/003-tetris-aware-agent/probes/new-directory/"
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
        uncommitted=[], published_same=probe.REPAIRED_PATHS,
        untracked_directories=[directory])
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert (f"not a file {directory} (outside the declared repaired paths): published absent, "
            "this worktree a directory") in printed
    assert f"1 of {len(probe.REPAIRED_PATHS) + 1} compared paths differ" in printed


def test_publication_probe_reports_a_path_present_in_neither_tree(tmp_path, monkeypatch, capsys):
    """A compared path with no digest on either side is described, not sliced.

    The state with neither a published nor a worktree digest: a path Git lists as
    tracked in both trees whose file has gone from both. No earlier comparison could
    reach it — it read presence or a list — and reading either digest there would
    raise. The report must describe it and still certify an otherwise equal tree.
    """
    probe = _load_publication_probe()
    missing = "experiments/003-tetris-aware-agent/probes/vanished.py"
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
        uncommitted=[], published_same=probe.REPAIRED_PATHS, tracked_missing=[missing])
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EQUAL_PREFIX in printed
    assert (f"absent {missing} (outside the declared repaired paths): present in neither tree"
            ) in printed


def test_publication_probe_rejects_repaired_content_a_clean_worktree_lacks(
    tmp_path, monkeypatch
):
    """A published tree differing from a clean worktree is not this task's work.

    With nothing uncommitted here, a published tree whose repaired-path content
    differs from this worktree cannot be this task's published repair; the probe
    must fail rather than report a repair it cannot see.
    """
    probe = _load_publication_probe()
    _drive_publication_probe(
        probe, tmp_path, monkeypatch,
        worktree_content=REPAIRED_CONTENT, uncommitted=[],
        worktree_head=PUBLISHED_COMMIT)
    with pytest.raises(AssertionError, match="clean worktree"):
        probe.check_publication()


def test_publication_probe_detects_a_result_only_difference(tmp_path, monkeypatch, capsys):
    """The experiment's own record is one of the compared paths.

    A publication check that compared only source and notes would certify a
    published repair while the experiment's reported result was still the previous
    round's. Every compared path is published content equal to this worktree's
    except the result artifact, which this worktree holds uncommitted: the probe
    must report the earlier-publication state and name the result instead of
    printing the equal-content certification.
    """
    probe = _load_publication_probe()
    result_path = "experiments/003-tetris-aware-agent/result.json"
    published_same = tuple(path for path in probe.REPAIRED_PATHS if path != result_path)
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=REPAIRED_CONTENT,
        uncommitted=[result_path], published_same=published_same)
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EARLIER_PREFIX in printed
    assert STATE_EQUAL_PREFIX not in printed
    assert f"differs {result_path} " in printed
    assert f"1 of {len(probe.REPAIRED_PATHS)} compared paths differ" in printed


def test_publication_probe_certifies_a_published_repair_by_content(
    tmp_path, monkeypatch, capsys
):
    """A clean checkout whose content is the published content certifies the repair.

    The post-publication state: the refs name this worktree's commit, nothing is
    uncommitted, and the repaired paths' content is identical, which is the state
    the probe is allowed to report as published.
    """
    probe = _load_publication_probe()
    _drive_publication_probe(
        probe, tmp_path, monkeypatch,
        worktree_content=PUBLISHED_CONTENT, uncommitted=[],
        worktree_head=PUBLISHED_COMMIT, published_same=probe.REPAIRED_PATHS)
    probe.check_publication()

    printed = capsys.readouterr().out
    assert STATE_EQUAL_PREFIX in printed
    assert STATE_EARLIER_PREFIX not in printed


# The state lines the record this repair replaces (ed8830a's) carried for the
# earlier round's finding, verbatim from the record it replaced: its ``state``
# still described ``cfab11e2`` and 5 differing paths while the commit fields and
# the counts beside it had been updated from a later run.
MIXED_STATE = (
    "open, branch ref and PR head at the previous publication cfab11e2; the refs do not name "
    "this worktree's content yet — 5 of the 46 compared paths differ — the probe reports that "
    "earlier-publication state rather than certifying it, and the service pushes the approved "
    "tree after the review"
)


def _retained_record_copy(tmp_path):
    """The retained result.json, as a writable copy, with its parsed content."""
    retained = (engine.PROJECT_ROOT / "experiments" / "003-tetris-aware-agent"
                / "result.json")
    path = tmp_path / "result.json"
    path.write_text(retained.read_text(encoding="utf-8"), encoding="utf-8")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _retained_publication(tmp_path):
    """The retained record's publication object, as a writable copy."""
    return _retained_record_copy(tmp_path)


def test_retained_publication_snapshot_describes_one_measured_run(tmp_path):
    """The record's publication object is one probe run's, not a mix of two.

    Two counterexamples are checked. The first is the reviewer's: ``state`` still
    named the earlier publication (``cfab11e2`` and 5 differing paths) while
    ``published_commit`` and the counts beside it had been updated from a later
    run, so no single measured state produced the object. The check reconstructs
    the state line from the record's own commit, compared-path count and
    differing-path list — through the probe's own ``state_line`` — and requires the
    record to quote exactly that line, so a line from one run cannot sit beside
    counts from another. The second is this repair round's finding: the record
    cited 11 ``repaired_paths_compared_by_content`` while 12 paths were declared,
    because the count had been transcribed from an earlier declaration and left
    behind when that list grew; the count must be the declared list's own length,
    the value the probe's emitted ``counts_line`` derives it from. The other fields
    must agree too — one commit across the four commit fields, the differing count
    equal to the list it summarises and to the uncommitted-change count, and the run
    labelled with its command and capture time — which is what
    ``evidence.py publication-record`` runs.
    """
    probe = _load_publication_probe()
    path, record = _retained_publication(tmp_path)
    probe.check_publication_record(path)

    def rejected(tamper, message):
        tampered = json.loads(json.dumps(record))
        path.write_text(json.dumps(tamper(tampered)), encoding="utf-8")
        with pytest.raises(AssertionError, match=message):
            probe.check_publication_record(path)

    def stale_state(tampered):
        tampered["publication"]["state"] = MIXED_STATE
        return tampered

    def stale_commit(tampered):
        tampered["publication"]["published_commit"] = "c" * 40
        return tampered

    def unlisted_difference(tampered):
        tampered["publication"]["observed_differing_paths"] += 1
        return tampered

    def stale_declared_count(tampered):
        tampered["publication"]["repaired_paths_compared_by_content"] = (
            len(probe.REPAIRED_PATHS) - 1)
        return tampered

    def drifted_state_count(tampered):
        # The line from an earlier run, with the sibling counts regenerated: the
        # state line still names the previous differing count and path list.
        tampered["publication"]["state"] = probe.state_line(
            tampered["publication"]["published_commit"],
            tampered["publication"]["compared_paths_count"],
            tampered["publication"]["repaired_paths_differing_from_this_worktree"][:-1])
        return tampered

    def unlabelled(tampered):
        del tampered["publication"]["captured_at"]
        return tampered

    def unlabelled_command(tampered):
        tampered["publication"]["command"] = "python -c 'import json'"
        return tampered

    rejected(stale_state, r"state is not the line these fields reconstruct")
    rejected(drifted_state_count, r"state is not the line these fields reconstruct")
    rejected(stale_commit, r"branch_head is .* but published_commit is 'c{40}'")
    rejected(unlisted_difference,
             r"observed_differing_paths is \d+ but the captured run records \d+ differing "
             r"paths")
    rejected(stale_declared_count,
             r"repaired_paths_compared_by_content is \d+ but the probe's counts line declares "
             r"\d+ repaired paths compared by content")
    rejected(unlabelled, r"captured_at is not a recorded timestamp")
    rejected(unlabelled_command, r"command does not name the publication probe")


def test_retained_publication_snapshot_cites_the_counts_the_probe_emits(
    tmp_path, monkeypatch, capsys
):
    """The record's counts are the values the probe emits for the state it describes.

    The record this repair replaces certified a comparison set it no longer
    described: ``repaired_paths_compared_by_content`` was 11 — transcribed from an
    earlier declaration — while 12 paths were declared. The probe now emits its own
    ``counts_line``, whose ``declared_paths_compared_by_content`` is derived from the
    declared list at the run. This drives the probe offline in the exact state the
    record describes — the same differing paths in the worktree and the same
    uncommitted set, every other declared path equal — and requires the record's
    declared, differing and uncommitted counts to be that line's values, so a
    hand-written count cannot drift from the declaration again. The compared-path
    total is tree-derived; it is one run's with the state line, which
    ``check_publication_record`` reconstructs from the record's own fields.
    """
    probe = _load_publication_probe()
    _, record = _retained_publication(tmp_path)
    publication = record["publication"]
    listed = publication["repaired_paths_differing_from_this_worktree"]
    # A path that differs and is not one of the declared repaired paths: the
    # record's list holds the probe's predeclaration capture as well.
    outside = [path for path in listed if path not in probe.REPAIRED_PATHS]
    _drive_publication_probe(
        probe, tmp_path, monkeypatch, worktree_content=REPAIRED_CONTENT,
        uncommitted=listed, outside_paths=outside,
        published_same=[path for path in probe.REPAIRED_PATHS if path not in listed])
    probe.check_publication()

    printed = capsys.readouterr().out
    emitted_capture = json.loads(
        next(line for line in printed.splitlines() if "publication_capture=" in line)
        .split("publication_capture=", 1)[1])
    assert emitted_capture["declared_paths"] == list(probe.REPAIRED_PATHS)
    assert [entry["path"] for entry in emitted_capture["compared_paths"] if entry["differs"]] \
        == listed
    assert sorted(emitted_capture["uncommitted_paths"]) == sorted(listed)
    emitted = dict(re.findall(
        r"\b(declared_paths_compared_by_content|compared_paths_count|"
        r"observed_differing_paths|observed_uncommitted_paths)=(\d+)", printed))
    assert emitted["declared_paths_compared_by_content"] == str(len(probe.REPAIRED_PATHS))
    assert emitted["declared_paths_compared_by_content"] == \
        str(publication["repaired_paths_compared_by_content"])
    assert emitted["observed_differing_paths"] == str(len(listed)) == \
        str(publication["observed_differing_paths"])
    assert emitted["observed_uncommitted_paths"] == str(publication["observed_uncommitted_paths"])


def _rejected_tamper(path, record, check, tamper, message):
    """Write the tampered copy of a retained record and require the check to report it."""
    path.write_text(json.dumps(tamper(json.loads(json.dumps(record)))), encoding="utf-8")
    with pytest.raises(AssertionError, match=message):
        check(path)


def test_base_commit_record_rejects_a_snapshot_that_mixes_runs(tmp_path):
    """The base-refresh snapshot is one run's captured commands, field by field.

    The reviewed counterexample: the retained object's ``worktree_head`` field
    named one commit while its captured ``rev-parse HEAD`` output named another,
    and its prose named a third, so no run produced the object. Every named field
    must be the output of the captured command whose role produced it, the state
    line must be the one those fields reconstruct, and every commit id in the
    object — in the prose as much as in the output — must be one the run observed.
    """
    probe = _load_evidence_probe("exp003_base_commit_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_base_commit_record(path)

    def rejected(tamper, message):
        _rejected_tamper(path, record, probe.check_base_commit_record, tamper, message)

    def drifted_field(tampered):
        base = tampered["base_commit"]
        base["worktree_head"] = base["commit"]
        return tampered

    def drifted_capture(tampered):
        # The capture regenerated with the field: the quoted line follows the
        # edited capture, and the field still is not what that command printed.
        base = tampered["base_commit"]
        entry = next(entry for entry in base["capture"]["commands"]
                     if entry["role"] == "this worktree's HEAD")
        entry["output"] = base["commit"]
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    def drifted_prose(tampered):
        tampered["base_commit"]["note"] += (
            " reviewed at fbe21e1345caf04970320b35689548c1efefd216.")
        return tampered

    def drifted_state(tampered):
        tampered["base_commit"]["state"] = probe.base_state_line({
            **{field: tampered["base_commit"][field] for field in probe.BASE_COMMIT_FIELDS},
            "worktree_head": "0" * 40,
        })
        return tampered

    def drifted_ancestry(tampered):
        tampered["base_commit"]["base_is_ancestor_of_remote_main"] = False
        return tampered

    drifted = (r"base_commit\.worktree_head is .* but the captured command for .this "
               r"worktree's HEAD. printed")
    rejected(drifted_field, drifted)
    rejected(drifted_capture, drifted)
    rejected(drifted_prose,
             r"names the commit fbe21e13\w*, which the captured run does not record")
    rejected(drifted_state, r"state is not the line these fields reconstruct")
    rejected(drifted_ancestry,
             r"base_commit\.base_is_ancestor_of_remote_main is False but the captured run "
             r"recorded True")


def test_base_commit_record_requires_the_captured_worktree_ancestry_command(tmp_path):
    """The snapshot's claim that this worktree descends from the base is captured.

    ``base_state_line`` says this worktree's HEAD descends from the recorded base,
    and the run captures the ``merge-base --is-ancestor`` command that establishes
    it. The retained check validated only the remote-main ancestry role, so a
    snapshot could carry the sentence with that command's exit status changed, or
    with the command dropped, and still certify. Both are now reported.
    """
    probe = _load_evidence_probe("exp003_base_commit_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_base_commit_record(path)

    def rejected(tamper, message):
        _rejected_tamper(path, record, probe.check_base_commit_record, tamper, message)

    def failed_worktree_ancestry(tampered):
        base = tampered["base_commit"]
        entry = next(command for command in base["capture"]["commands"]
                     if command["role"] == probe.BASE_WORKTREE_ANCESTRY_ROLE)
        entry["exit"] = 1
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    def dropped_worktree_ancestry(tampered):
        base = tampered["base_commit"]
        base["capture"]["commands"] = [
            command for command in base["capture"]["commands"]
            if command["role"] != probe.BASE_WORKTREE_ANCESTRY_ROLE]
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    def drifted_remote_ref(tampered):
        base = tampered["base_commit"]
        base["capture"]["remote_main_ref"] = "refs/heads/other"
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    def contradictory_ancestry_flag(tampered):
        # Both copies of the flag agree on False while the captured command
        # exited 0: the derivation the producer uses makes that impossible.
        base = tampered["base_commit"]
        base[probe.BASE_ANCESTRY_FIELD] = False
        base["capture"][probe.BASE_ANCESTRY_FIELD] = False
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    def mismatched_base_tree(tampered):
        # The observed tip is the recorded base, so the one commit would have two
        # trees: the field, its capture copy and the captured output move together.
        base = tampered["base_commit"]
        other = "0" * 40
        base["remote_main_tree"] = other
        base["capture"]["remote_main_tree"] = other
        for command in base["capture"]["commands"]:
            if command["role"] == "refreshed remote main tree from the clone":
                command["output"] = other
        base["base_capture_line"] = probe.base_capture_line(base["capture"])
        return tampered

    rejected(failed_worktree_ancestry, r"worktree-ancestry command exited 1")
    rejected(dropped_worktree_ancestry,
             r"holds 0 commands for the role .*which the state line claims")
    rejected(drifted_remote_ref,
             r"resolved the ref 'refs/heads/other', not this probe's")
    rejected(contradictory_ancestry_flag,
             r"base_commit\.base_is_ancestor_of_remote_main is False but the captured "
             r"ancestry command exited 0, which implies True")
    rejected(mismatched_base_tree,
             r"remote_main_tip is the recorded base .* but its tree .* is not the recorded "
             r"base tree")


def _drive_remote_main_probe(probe, tmp_path, monkeypatch, *, remote_tip, remote_tree,
                             base_tree, worktree_head, base_on_remote, base_on_head=True):
    """Run ``check_remote_main`` with the Git plumbing stubbed for one state.

    ``base_on_remote`` says whether the observed remote main tip contains the
    recorded base, which is the ancestry the probe has to assert and the value a
    pre-change probe instead compared with a fixed tip.
    """
    clone = tmp_path / "remote-main"
    base = probe.BASE_COMMIT

    def fake_git(cwd, *arguments):
        command = " ".join(arguments)
        where = Path(cwd)
        if command.startswith("ls-remote"):
            return 0, f"{remote_tip}\t{probe.REMOTE_MAIN_REF}"
        if command.startswith("clone "):
            return 0, ""
        if where == clone:
            if command == "rev-parse HEAD":
                return 0, remote_tip
            if command == "rev-parse HEAD^{tree}":
                return 0, remote_tree
            if command.startswith("merge-base --is-ancestor"):
                return (0 if base_on_remote else 1), ""
        elif command == f"rev-parse {base}":
            return 0, base
        elif command == f"rev-parse {base}^{{tree}}":
            return 0, base_tree
        elif command == "rev-parse HEAD":
            return 0, worktree_head
        elif command.startswith("merge-base --is-ancestor"):
            return (0 if base_on_head else 1), ""
        raise AssertionError(f"unexpected git command: {command} (in {where})")

    monkeypatch.setattr(probe, "REMOTE_MAIN_CLONE", clone)
    monkeypatch.setattr(probe, "_git", fake_git)


def test_remote_main_check_holds_when_main_has_moved_on(tmp_path, monkeypatch, capsys):
    """The base check is durable: main may have moved past the recorded base.

    The reviewer's finding: the probe required the observed remote main tip to
    equal a fixed commit, so the evidence file necessarily failed once any later
    commit reached main — this experiment's own merge included. It must instead
    assert that the observed tip contains the recorded base and report both tips
    beside each other, and still fail when the base is not on main at all.
    """
    probe = _load_evidence_probe("exp003_remote_main_probe")
    ahead = "b" * 40
    _drive_remote_main_probe(
        probe, tmp_path, monkeypatch, remote_tip=ahead, remote_tree="c" * 40,
        base_tree="d" * 40, worktree_head="e" * 40, base_on_remote=True)
    probe.check_remote_main()
    printed = capsys.readouterr().out
    assert f"remote main has since moved to {ahead}, which contains it" in printed
    assert f"this worktree's HEAD is {'e' * 40}, which descends from it" in printed
    capture = json.loads(
        next(line for line in printed.splitlines() if "base_capture=" in line)
        .split("base_capture=", 1)[1])
    assert capture["remote_main_tip"] == ahead
    assert capture["commit"] == probe.BASE_COMMIT
    assert capture["base_is_ancestor_of_remote_main"] is True

    # The tip still equals the base: then its tree must be the base's tree.
    _drive_remote_main_probe(
        probe, tmp_path, monkeypatch, remote_tip=probe.BASE_COMMIT,
        remote_tree="c" * 40, base_tree="d" * 40, worktree_head="e" * 40,
        base_on_remote=True)
    with pytest.raises(AssertionError, match=r"tree"):
        probe.check_remote_main()

    # One commit with the base's tree is the state the branch was cut from.
    _drive_remote_main_probe(
        probe, tmp_path, monkeypatch, remote_tip=probe.BASE_COMMIT,
        remote_tree="d" * 40, base_tree="d" * 40, worktree_head="e" * 40,
        base_on_remote=True)
    probe.check_remote_main()
    assert "the observed remote main tip is that base" in capsys.readouterr().out

    # A remote main that does not contain the recorded base is still reported.
    _drive_remote_main_probe(
        probe, tmp_path, monkeypatch, remote_tip=ahead, remote_tree="c" * 40,
        base_tree="d" * 40, worktree_head="e" * 40, base_on_remote=False)
    with pytest.raises(AssertionError, match=r"does not contain the recorded base"):
        probe.check_remote_main()

    # And a worktree HEAD that does not descend from the base is reported.
    _drive_remote_main_probe(
        probe, tmp_path, monkeypatch, remote_tip=ahead, remote_tree="c" * 40,
        base_tree="d" * 40, worktree_head="e" * 40, base_on_remote=True,
        base_on_head=False)
    with pytest.raises(AssertionError, match=r"does not descend from the base"):
        probe.check_remote_main()


def test_publication_record_counts_come_from_the_captured_run(tmp_path):
    """The publication record's counts are lengths of its captured run's lists.

    The reviewer's finding: every count was checked against another value the
    same helpers derived, so mutating ``compared_paths_count`` and regenerating
    the state and counts lines with the shipped helpers still verified. The record
    now stores the run's captured state — one outcome per compared path and the
    uncommitted paths — and each count is that capture's own list length, so a
    regenerated count without a matching captured list is reported.
    """
    probe = _load_publication_probe()
    path, record = _retained_record_copy(tmp_path)
    probe.check_publication_record(path)

    def rejected(tamper, message):
        _rejected_tamper(path, record, probe.check_publication_record, tamper, message)

    def regenerated_count(tampered):
        publication = tampered["publication"]
        publication["compared_paths_count"] -= 1
        listed = publication["repaired_paths_differing_from_this_worktree"]
        publication["state"] = probe.state_line(
            publication["published_commit"], publication["compared_paths_count"], listed)
        publication["counts_line"] = probe.counts_line(
            publication["compared_paths_count"], publication["observed_differing_paths"],
            publication["observed_uncommitted_paths"])
        return tampered

    def regenerated_differing_list(tampered):
        publication = tampered["publication"]
        publication["repaired_paths_differing_from_this_worktree"] = []
        publication["observed_differing_paths"] = 0
        publication["observed_uncommitted_paths"] = 0
        publication["state"] = probe.state_line(publication["published_commit"],
                                               publication["compared_paths_count"], [])
        publication["counts_line"] = probe.counts_line(
            publication["compared_paths_count"], 0, 0)
        return tampered

    def drifted_capture(tampered):
        capture = tampered["publication"]["capture"]
        capture["uncommitted_paths"] = capture["uncommitted_paths"][1:]
        tampered["publication"]["publication_capture_line"] = \
            probe.publication_capture_line(capture)
        return tampered

    rejected(regenerated_count,
             r"compared_paths_count is \d+ but the captured run compared \d+ paths")
    rejected(regenerated_differing_list,
             r"repaired_paths_differing_from_this_worktree is \[\] but the captured run "
             r"records these paths differing")
    rejected(drifted_capture,
             r"observed_uncommitted_paths is \d+ but the captured run records \d+ "
             r"uncommitted paths")


def test_publication_record_derives_each_capture_entry_from_its_recorded_states(tmp_path):
    """A captured entry's two decisions follow from its own recorded states.

    The reviewer's counterexample: the retained entry for a differing file has its
    outcome changed to ``same`` while its recorded sides are still two files and
    its ``differs`` flag is still true. Every field is individually a legal value —
    ``same`` is a known outcome, ``file`` a known state — but their combination is
    one no run produced, so validating the fields one at a time certifies a
    snapshot that was never measured. The check recomputes the outcome and the
    differing flag from the entry's own states and digests, so the regenerated
    capture line is reported; the genuine capture still passes.
    """
    probe = _load_publication_probe()
    path, record = _retained_record_copy(tmp_path)
    probe.check_publication_record(path)
    capture = record["publication"]["capture"]
    differing = next(entry for entry in capture["compared_paths"] if entry["differs"])
    assert differing["published"] == "file" and differing["worktree"] == "file"

    def rejected(**changes):
        tampered = json.loads(json.dumps(record))
        target = next(entry for entry in tampered["publication"]["capture"]["compared_paths"]
                      if entry["path"] == differing["path"])
        target.update(changes)
        tampered["publication"]["publication_capture_line"] = \
            probe.publication_capture_line(tampered["publication"]["capture"])
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(AssertionError) as error:
            probe.check_publication_record(path)
        return str(error.value)

    message = rejected(outcome="same")
    assert f"the captured entry for {differing['path']!r} records the outcome 'same'" in message
    assert "imply 'differs'" in message
    message = rejected(differs=False)
    assert "records differs=False, but its recorded states and digests imply True" in message
    # A digest that a state does not have is not a combination any run read either.
    message = rejected(outcome="added", differs=True)
    assert "imply 'differs'" in message and "imply 'added'" not in message

    # The refs the run resolved are captured evidence too: a capture naming
    # another branch is not a run of this probe, however consistent it is.
    tampered = json.loads(json.dumps(record))
    tampered["publication"]["capture"]["branch_ref"] = "refs/heads/other"
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(tampered["publication"]["capture"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"resolved the branch 'refs/heads/other'"):
        probe.check_publication_record(path)

    # A differing path that the captured uncommitted list does not name is the
    # state ``check_publication`` rejects; equal counts alone cannot see it.
    tampered = json.loads(json.dumps(record))
    capture = tampered["publication"]["capture"]
    differing = next(entry for entry in capture["compared_paths"] if entry["differs"])
    unchanged = next(entry["path"] for entry in capture["compared_paths"]
                     if not entry["differs"] and entry["outcome"] == "same")
    capture["uncommitted_paths"] = [
        unchanged if path == differing["path"] else path
        for path in capture["uncommitted_paths"]]
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(capture)
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match=r"records these paths differing but not uncommitted"):
        probe.check_publication_record(path)

    # The list's coverage is a claim too: a declared repaired path replaced by a
    # duplicate of an unchanged entry keeps every count while comparing a path
    # twice and omitting the declared one.
    tampered = json.loads(json.dumps(record))
    capture = tampered["publication"]["capture"]
    entries = capture["compared_paths"]
    declared = next(
        (item for item in entries
         if item["path"] in probe.REPAIRED_PATHS and not item["differs"]),
        next(item for item in entries if item["path"] in probe.REPAIRED_PATHS))
    donor = next(item for item in entries
                 if item["path"] != declared["path"]
                 and item["differs"] == declared["differs"])
    declared.update(donor)
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(capture)
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"compares these paths more than once"):
        probe.check_publication_record(path)

    # The worktree HEAD is this checkout's own: the probe records it beside the
    # published commit and permits it to differ, so a snapshot from that state has
    # to certify once its capture line is regenerated.
    tampered = json.loads(json.dumps(record))
    other_head = "1" * 40
    tampered["publication"]["capture"]["worktree_head"] = other_head
    tampered["publication"]["observed_worktree_head"] = other_head
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(tampered["publication"]["capture"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    probe.check_publication_record(path)

    # An uncommitted path whose content already equals the publication (a
    # mode-only change, or an edit reproducing the published bytes) is a capture
    # the probe can emit: only coverage of the differing paths is required.
    tampered = json.loads(json.dumps(record))
    capture = tampered["publication"]["capture"]
    extra = next(entry["path"] for entry in capture["compared_paths"]
                 if entry["outcome"] == "same" and entry["path"] not in capture["uncommitted_paths"])
    capture["uncommitted_paths"] = sorted(capture["uncommitted_paths"] + [extra])
    tampered["publication"]["observed_uncommitted_paths"] = len(capture["uncommitted_paths"])
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(capture)
    tampered["publication"]["counts_line"] = probe.counts_line(
        tampered["publication"]["compared_paths_count"],
        tampered["publication"]["observed_differing_paths"],
        tampered["publication"]["observed_uncommitted_paths"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    probe.check_publication_record(path)


def test_predeclaration_covers_every_module_of_the_objective_identity(tmp_path, monkeypatch):
    """The captured objective covers the helpers its decisions run through.

    The reviewer's counterexample: the capture recorded only the declaring
    module's digest while the recorded objective identity covers ``tetris.py``
    plus the modules its code calls, so a change to a helper after the capture
    still passed ``check-predeclaration`` even though it moves every value the
    objective computes. This captures the objective with the probe's own
    ``predeclare`` and then changes each covered module in turn — through a
    mutated copy of its file, so nothing in this worktree is touched — and
    requires the check to reject each one, with the declaring module's digest
    still equal when a helper is the one that changed.
    """
    probe = _load_evidence_probe("exp003_predeclaration_probe")
    capture = tmp_path / "predeclared_objective.json"
    monkeypatch.setattr(probe, "PREDECLARATION", capture)
    probe.predeclare()
    captured = json.loads(capture.read_text(encoding="utf-8"))
    record_path = tmp_path / "run.json"
    record_path.write_text(
        json.dumps({"created_at": "2099-01-01T00:00:00+00:00",
                    "objective": {"sources": captured["sources"],
                                  "weights": captured["objective"]}}), encoding="utf-8")
    probe.check_predeclaration(record_path)

    # A cited record that carries no identity cannot tie the capture to what the
    # measurement itself wrote: the run's own identity must be compared, so its
    # absence is reported rather than skipped.
    record_path.write_text(
        json.dumps({"created_at": "2099-01-01T00:00:00+00:00"}), encoding="utf-8")
    with pytest.raises(AssertionError, match="carries no objective identity"):
        probe.check_predeclaration(record_path)
    record_path.write_text(
        json.dumps({"created_at": "2099-01-01T00:00:00+00:00",
                    "objective": {"sources": captured["sources"],
                                  "weights": captured["objective"]}}), encoding="utf-8")

    # The capture covers the identity's whole set, not one module.
    assert set(captured["sources"]) == set(runner._objective_sources())
    assert len(captured["sources"]) > 1
    for name in sorted(captured["sources"]):
        module = sys.modules[name]
        mutated = tmp_path / f"{name}.py"
        mutated.write_bytes(Path(module.__file__).read_bytes() + b"\n# a helper changed\n")
        with monkeypatch.context() as patch:
            patch.setattr(module, "__file__", str(mutated))
            with pytest.raises(AssertionError, match="changed after the predeclaration"):
                probe.check_predeclaration(record_path)
            # A helper's change moves every value the objective computes while the
            # module that declares it is untouched: the digest-only capture this
            # replaces reported nothing here.
            if name != "block_stack_ai.tetris":
                assert probe._module_digest() == captured["module_sha256"]

    # The declared mapping is compared too: an edited capture whose weights are
    # not the ones the objective's code publishes cannot certify a run scored by
    # the published ones, and predeclare refuses to keep such a capture.
    capture.write_text(json.dumps(
        {**captured, "objective": {**captured["objective"], "tetrises": 80.0}}),
        encoding="utf-8")
    with pytest.raises(AssertionError,
                       match=r"not the ones the objective's code publishes"):
        probe.check_predeclaration(record_path)
    with pytest.raises(AssertionError,
                       match=r"declared weights are not the ones the objective's code publishes"):
        probe.predeclare()
    capture.write_text(json.dumps(captured), encoding="utf-8")

    # A capture of the pre-change shape — the declaring module's digest alone —
    # is refused by the capture path and cannot support the check either.
    capture.write_text(json.dumps({key: value for key, value in captured.items()
                                   if key != "sources"}), encoding="utf-8")
    with pytest.raises(AssertionError, match="covers only the declaring module"):
        probe.predeclare()
    with pytest.raises(AssertionError, match="records only the declaring module"):
        probe.check_predeclaration(record_path)


def test_the_writer_records_a_reloaded_modules_identity(tmp_path):
    """A reloaded module's identity is the one the writer records, not its import-time copy.

    The reviewer's finding: the writer copied an identity bound when ``runner``
    was imported, so a long-lived process that reloads a covered module — the
    ordinary way such a process changes the code it runs — updated the loader's
    record while every record written afterwards kept naming the bytes from before
    the reload. The reloaded module's code is what computes the later choices, so
    the record named an implementation that produced nothing. The counterexample
    program's ``reload`` mode runs the ordering in a fresh process: the modules are
    imported, the writer is imported, the file is edited, the module is reloaded,
    and only then is a run built and verified. What the writer records must be the
    loader's current digest — and, because the reloaded code is what chose the
    recorded inputs and the tree holds it, verification must pass rather than
    report.
    """
    measured = _run_counterexample(tmp_path / "reload", mode="reload")
    assert measured["subject"] == "block_stack_ai.agents", measured
    assert measured["before"] != measured["on_disk"], measured
    assert measured["loader"] == measured["on_disk"], measured
    assert measured["record"] == measured["loader"], (
        "the writer recorded the identity bound when it was imported rather than the "
        f"reloaded module's own: loader {measured['loader']}, recorded "
        f"{measured['record']}"
    )
    assert measured["loaded"] == measured["loader"], measured
    assert measured["outcome"]["verified"] is True, measured["outcome"]


def test_publication_record_derives_the_tree_from_the_repository(tmp_path):
    """The commit/tree pairing comes from the repository, not from its own copy.

    The reviewer's finding: ``check_publication_record`` validated the recorded
    ``published_tree`` only against the same value inside the capture, so setting
    both to ``000…`` and regenerating the capture line with the shipped helper
    certified a pairing no publication probe could have observed — the captured
    commit's immutable tree is not that value. The retained record passes, and the
    zeroed pairing, and a commit this repository cannot resolve, are reported.
    """
    probe = _load_evidence_probe("exp003_publication_tree_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_publication_record(path)
    published = record["publication"]["published_commit"]
    resolved, _ = probe._resolved_commit_tree(published)
    assert resolved == record["publication"]["published_tree"], (
        "the retained record's published_tree is not what this repository resolves "
        f"{published}^{{tree}} to: {resolved}")

    zeros = "0" * 40
    tampered = json.loads(json.dumps(record))
    tampered["publication"]["published_tree"] = zeros
    tampered["publication"]["capture"]["published_tree"] = zeros
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(tampered["publication"]["capture"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"resolves .* to '[0-9a-f]{40}'"):
        probe.check_publication_record(path)

    # A commit this repository does not hold cannot back the pairing at all, so it
    # is reported instead of being compared with its own copy.
    tampered = json.loads(json.dumps(record))
    unknown = "d" * 40
    tampered["publication"]["published_commit"] = unknown
    tampered["publication"]["branch_head"] = unknown
    tampered["publication"]["pull_request_head"] = unknown
    tampered["publication"]["capture"]["published_commit"] = unknown
    tampered["publication"]["capture"]["branch_head"] = unknown
    tampered["publication"]["capture"]["pull_request_head"] = unknown
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(tampered["publication"]["capture"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"does not resolve to a tree in this repository"):
        probe.check_publication_record(path)


def test_publication_record_rejects_a_tree_in_all_commit_fields(tmp_path):
    """Consistent copies of a tree hash cannot claim a published commit."""
    probe = _load_evidence_probe("exp003_publication_commit_type_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_publication_record(path)
    publication = record["publication"]
    tree = publication["published_tree"]
    for field in ("published_commit", "branch_head", "pull_request_head"):
        publication[field] = tree
        publication["capture"][field] = tree
    publication["publication_capture_line"] = probe.publication_capture_line(
        publication["capture"])
    publication["state"] = probe.state_line(
        tree, publication["compared_paths_count"],
        publication["repaired_paths_differing_from_this_worktree"])
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(AssertionError, match="not a commit object"):
        probe.check_publication_record(path)


def test_commit_tree_resolution_requires_an_exact_commit_object(tmp_path, monkeypatch):
    """The shared publication/base resolver also rejects tags that peel to commits."""
    probe = _load_evidence_probe("exp003_exact_commit_probe")

    def git(*args, input=None):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], input=input, text=True,
            capture_output=True, check=True).stdout.strip()

    git("init", "--quiet")
    tree = git("mktree", input="")
    commit = git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit-tree", tree, input="test commit\n")
    tag = git("mktag", input=(f"object {commit}\ntype commit\ntag test\n"
                             "tagger Test <test@example.com> 0 +0000\n\ntest tag\n"))
    blob = git("hash-object", "-w", "--stdin", input="test blob\n")
    monkeypatch.setattr(probe, "PROJECT_ROOT", tmp_path)
    assert probe._resolved_commit_tree(commit)[0] == tree
    for object_id in (tree, tag, blob):
        resolved, reason = probe._resolved_commit_tree(object_id)
        assert resolved is None, (object_id, resolved)
        assert "not a commit object" in reason


def test_publication_record_derives_the_compared_paths_prose(tmp_path):
    """The comparison-set prose is derived from the captured per-path evidence.

    The reviewer's finding: the record's prose claimed 46 paths in the published
    tree while the capture beside it held 48 entries whose published state is a
    file, because the sentence was a hand-maintained literal. The retained record
    passes, a prose count the capture does not support is reported, and so is a
    capture whose entries were changed under the sentence.
    """
    probe = _load_evidence_probe("exp003_publication_prose_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_publication_record(path)
    capture = record["publication"]["capture"]
    published_files = probe.publication_file_count(capture)
    assert record["publication"]["compared_paths"] == probe.compared_paths_prose(
        len(capture["compared_paths"]), published_files)

    wrong = record["publication"]["compared_paths"].replace(
        f"{published_files} of the {len(capture['compared_paths'])} compared paths",
        f"{published_files - 2} of the {len(capture['compared_paths'])} compared paths")
    assert wrong != record["publication"]["compared_paths"], record["publication"]["compared_paths"]
    tampered = json.loads(json.dumps(record))
    tampered["publication"]["compared_paths"] = wrong
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"compared_paths is .*not the sentence"):
        probe.check_publication_record(path)

    # The other direction: the capture loses a published file and its own
    # per-entry decisions are recomputed to match, so the only thing left
    # disagreeing is the sentence the record retains.
    tampered = json.loads(json.dumps(record))
    entries = tampered["publication"]["capture"]["compared_paths"]
    stripped = next(entry for entry in entries
                    if entry["published"] == "file" and entry["worktree"] == "file"
                    and entry["differs"])
    stripped["published"] = "absent"
    stripped["published_sha256"] = None
    stripped["outcome"], stripped["differs"] = probe.path_decision(
        stripped["published"], stripped["published_sha256"],
        stripped["worktree"], stripped["worktree_sha256"])
    tampered["publication"]["publication_capture_line"] = \
        probe.publication_capture_line(tampered["publication"]["capture"])
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"compared_paths is .*not the sentence"):
        probe.check_publication_record(path)


def test_predeclaration_record_derives_the_cited_timestamp(tmp_path):
    """The order sentence is the one the block's own timestamps reconstruct.

    The reviewer's finding: the block carries the cited record's ``created_at`` in
    ``cited_record_created_at`` while the sentence beside it still quoted an
    earlier evaluation's timestamp of the same round, so the block described two
    measurements. The retained record passes; a sentence rewritten to quote a
    different instant is reported, and so is that field changed without its own
    sentence.
    """
    probe = _load_evidence_probe("exp003_predeclaration_record_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_predeclaration_record(path)
    block = record["predeclared_objective"]
    assert block["capture_order"] == probe.predeclaration_order_line(
        block["captured_at"], block["cited_record_created_at"],
        probe.predeclaration_superseded(block))

    stale = json.loads(json.dumps(record))
    stale["predeclared_objective"]["capture_order"] = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00)",
        "2001-01-01T00:00:00.000000+00:00",
        stale["predeclared_objective"]["capture_order"])
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(AssertionError, match=r"capture_order is not the line"):
        probe.check_predeclaration_record(path)

    # The value the sentence is derived from is itself part of the block, so it is
    # read from the cited record when this checkout retains it: changing it beside
    # an unchanged sentence is reported too. ``runs/`` is ignored output, so the
    # comparison is made where that evidence is present.
    if (probe.PROJECT_ROOT / block["cited_record"]).is_file():
        moved = json.loads(json.dumps(record))
        moved["predeclared_objective"]["cited_record_created_at"] = (
            "2001-01-01T00:00:00.000000+00:00")
        path.write_text(json.dumps(moved), encoding="utf-8")
        with pytest.raises(AssertionError,
                           match=r"cited_record_created_at is .* but the cited record"):
            probe.check_predeclaration_record(path)


def test_record_derives_the_format_version_prose(tmp_path):
    """The retained version prose is the line the writer's own table generates.

    The reviewer's finding: the summary still named version 5 as the current suite
    format while ``runner.SUITE_FORMAT_VERSION`` is 6 and the version map beside it
    already described 5 as the earlier outward-only identity. The retained
    sentence is the generated one, and a sentence naming an outdated table is
    reported.
    """
    probe = _load_evidence_probe("exp003_version_prose_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_predeclaration_record(path)
    sentence = record["record_format_versions"]["this_round"]
    assert sentence.endswith(probe.format_versions_line()), sentence
    assert f"{runner.SUITE_FORMAT_VERSION} current suite" in sentence
    assert f"{runner.OUTWARD_IDENTITY_SUITE_FORMAT_VERSION} outward-identity suite" in sentence

    stale = json.loads(json.dumps(record))
    stale["record_format_versions"]["this_round"] = sentence.replace(
        f"{runner.SUITE_FORMAT_VERSION} current suite",
        f"{runner.OUTWARD_IDENTITY_SUITE_FORMAT_VERSION} current suite")
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(AssertionError,
                       match=r"this_round does not end with the version prose"):
        probe.check_predeclaration_record(path)


def test_base_commit_record_derives_the_trees_from_the_repository(tmp_path):
    """The base snapshot's commit/tree pairings come from the repository too.

    The same class as the publication snapshot's pairing, one block over: the
    base snapshot's ``git_tree_id`` and ``remote_main_tree`` were validated against
    copies of themselves — the captured ``rev-parse`` output is inside the same
    object — so rewriting the field, its capture copy, the captured command output
    and the state line together certified a pairing no run observed. The retained
    snapshot passes, and both co-forged pairings are reported.
    """
    probe = _load_evidence_probe("exp003_base_trees_probe")
    path, record = _retained_record_copy(tmp_path)
    probe.check_base_commit_record(path)
    base = record["base_commit"]
    resolved, _ = probe._resolved_commit_tree(base["commit"])
    assert resolved == base["git_tree_id"], (resolved, base["git_tree_id"])

    def rewrite(tampered, trees, tip=None):
        target = tampered["base_commit"]
        for field, value in trees.items():
            target[field] = value
            target["capture"][field] = value
        if tip is not None:
            target["remote_main_tip"] = tip
            target["capture"]["remote_main_tip"] = tip
            for entry in target["capture"]["commands"]:
                if entry["role"] == "refreshed remote main commit from the clone":
                    entry["output"] = tip
        for entry in target["capture"]["commands"]:
            for role, field in probe.BASE_COMMIT_ROLES:
                if entry["role"] == role and field in trees:
                    entry["output"] = trees[field]
        target["base_capture_line"] = probe.base_capture_line(target["capture"])
        target["state"] = probe.base_state_line(
            {name: target[name] for name in probe.BASE_COMMIT_FIELDS})

    zeros = "0" * 40
    for label, trees, tip in (
        ("both trees zeroed in every copy",
         {"git_tree_id": zeros, "remote_main_tree": zeros}, None),
        ("the tip's tree zeroed with the observed tip moved to this checkout's HEAD",
         {"remote_main_tree": zeros}, subprocess.run(
             ["git", "rev-parse", "HEAD"], cwd=engine.PROJECT_ROOT, text=True,
             capture_output=True, check=True).stdout.strip()),
    ):
        tampered = json.loads(json.dumps(record))
        rewrite(tampered, trees, tip=tip)
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(AssertionError,
                           match=r"this repository resolves .* to '[0-9a-f]{40}'"):
            probe.check_base_commit_record(path)


def test_the_writer_refuses_a_mixed_loaded_closure(tmp_path):
    """A partial reload is refused, not stamped with the reloaded module's identity.

    The review follow-up to the reload repair, in both directions a partial reload
    can take. Reloading only the objective module updates the loader's digest for
    it while the wrapper keeps the callable it imported by value; reloading only
    the wrapper updates its digest while the writer keeps the factory it imported
    by value (``runner.create_agent``, with the script parser and the agent classes
    beside it). In either direction the code that would compute a choice and the
    module an identity would name are two implementations, and the counterexample
    program's ``mixed`` and ``mixed-caller`` modes run those orderings in a fresh
    process. Each must be refused, with the stale reference named and no record
    written — a run stamped with the reloaded module's digest would describe code
    that produced none of its inputs.
    """
    for mode, reference in (("mixed", "block_stack_ai.agents.tetris_choice"),
                            ("mixed-caller", "block_stack_ai.runner.create_agent")):
        measured = _run_counterexample(tmp_path / mode, mode=mode)
        assert measured["mode"] == mode, measured
        assert measured["before"] != measured["on_disk"], measured
        assert measured["loader"] == measured["on_disk"], measured
        assert measured["refused"] is True, (
            f"the {mode} run was stamped with a record instead of being refused: "
            f"{measured['record']}"
        )
        assert reference in measured["refusal"], measured["refusal"]
        assert measured["record"] is None, measured
