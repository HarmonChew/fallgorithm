from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from block_stack_ai.engine import create_game, engine_executable, engine_root, native_library_path
from block_stack_ai.live import LiveSession
from block_stack_ai import runner
from block_stack_ai.runner import SuiteConfig, VerificationError, verify_run
from block_stack_ai.tetris import weights_record as tetris_weights_record


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


def test_live_session_records_the_clear_size_histogram_and_verifies(tmp_path, monkeypatch):
    """A completed live game records the same histogram a suite episode does.

    Live play builds its own episode, so it is the second path that writes
    episodes. The desktop protocol is driven here with a plain native mirror: the
    greedy agent clears lines within the frame limit, and the recorded histogram
    must be non-empty, add up to the line total the record already carries, equal
    the summary total derived from it, and replay under ``verify_run``. Without
    the histogram in the episode the summary would carry totals the episode did
    not record, and the replay would reject the record.
    """
    limit = 600
    config = SuiteConfig(GAME, limit, (2,), ("greedy",))
    session = LiveSession(config, tmp_path / "runs")
    try:
        with create_game(**GAME, seed=2) as desktop:
            snapshot = desktop.save_state()
            session.receive("BEGIN", snapshot)
            while not desktop.state.terminal and desktop.state.frame < limit:
                mask = session.receive("STATE", snapshot)
                desktop.step(mask)
                snapshot = desktop.save_state()
            session.receive("END", snapshot)
    finally:
        session.close()
    records = list((tmp_path / "runs").glob("*/run.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    episode = record["episodes"][0]
    sizes = episode["clear_sizes"]
    assert sizes["singles"] + sizes["doubles"] + sizes["triples"] + sizes["tetrises"] > 0
    assert (sizes["singles"] + 2 * sizes["doubles"] + 3 * sizes["triples"]
            + 4 * sizes["tetrises"]) == episode["result"]["lines"]
    assert record["summary"]["greedy"]["clear_sizes"] == sizes
    # This agent declares no objective, so the controller section is the only
    # source identity the record carries; it is what reports a changed live
    # module for a greedy, random or lookahead live game.
    assert record["format_version"] == runner.LIVE_SUITE_FORMAT_VERSION
    assert "objective" not in record
    assert record["controller"] == runner._controller_identity()
    assert "block_stack_ai.live" in record["controller"]["sources"]
    verify_run(records[0])
    live = sys.modules["block_stack_ai.live"]
    mutated = tmp_path / "live-changed.py"
    mutated.write_text(Path(live.__file__).read_text(encoding="utf-8")
                       + "\n# the controller changed after the game\n",
                       encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(live, "__file__", str(mutated))
        with pytest.raises(VerificationError,
                           match=r"controller\.sources\.block_stack_ai\.live"):
            verify_run(records[0])
    verify_run(records[0])


def test_live_tetris_session_records_the_objective_and_verifies(tmp_path, monkeypatch):
    """A live Tetris game declares the same objective a headless suite does, plus live.

    Live play is the second path that writes a suite record, so the declared
    objective has to be recorded there too: without it a live Tetris record would
    verify under whatever objective is current whenever the change happens to
    preserve the replayed choices, and without the objective's source identity it
    would verify under a changed formula whenever the weights were unchanged. The
    live session also emits its own format version, whose identity adds the module
    that drove the game: every observation reached the agent through
    ``LiveSession.receive`` here, and a change to that controller that preserved
    the replayed masks has to be reported. The desktop protocol is driven with a
    plain native mirror, and the record must name the declaring module, its
    weights, the live-seeded source identity and version 8, and replay under
    ``verify_run`` — which reports a changed controller and nothing else.
    """
    limit = 600
    config = SuiteConfig(GAME, limit, (2,), ("tetris",))
    session = LiveSession(config, tmp_path / "runs")
    try:
        with create_game(**GAME, seed=2) as desktop:
            snapshot = desktop.save_state()
            session.receive("BEGIN", snapshot)
            while not desktop.state.terminal and desktop.state.frame < limit:
                mask = session.receive("STATE", snapshot)
                desktop.step(mask)
                snapshot = desktop.save_state()
            session.receive("END", snapshot)
    finally:
        session.close()
    records = list((tmp_path / "runs").glob("*/run.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["format_version"] == runner.LIVE_SUITE_FORMAT_VERSION
    assert record["objective"] == {
        "module": "block_stack_ai.tetris", "weights": tetris_weights_record(),
        "sources": runner._objective_sources(runner._IDENTITY_LIVE),
    }
    assert "block_stack_ai.live" in record["objective"]["sources"]
    assert record["controller"] == runner._controller_identity()
    assert "block_stack_ai.live" in record["controller"]["sources"]
    assert sorted(record["summary"]) == ["tetris"]
    verify_run(records[0])

    # A change to the live controller's own source is reported for the record it
    # wrote, while the record itself is untouched. The edit really changes when
    # observations reach the agent — every other state is dropped — and the replay
    # never reads this file, so the recorded masks still replay and the identity
    # is the only thing that can report what the controller did.
    live = sys.modules["block_stack_ai.live"]
    mutated = tmp_path / "live-changed.py"
    changed = Path(live.__file__).read_text(encoding="utf-8").replace(
        '        if kind == "STATE":\n',
        '        if kind == "STATE" and len(self.inputs) % 2 == 0:\n',
    )
    assert changed != Path(live.__file__).read_text(encoding="utf-8")
    mutated.write_text(changed, encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setattr(live, "__file__", str(mutated))
        with pytest.raises(VerificationError,
                           match=r"objective\.sources\.block_stack_ai\.live"):
            verify_run(records[0])
    verify_run(records[0])


def test_live_tetris_session_snapshots_the_objective_at_begin(tmp_path, monkeypatch):
    """A mid-game edit to a covered module is not recorded as the code that chose inputs.

    The reviewer's findings: ``_objective_section(self.config)`` read the covered
    source files when the game ended, while the game's versions were captured at
    BEGIN, so a module edited mid-session was recorded as the code that chose the
    inputs; and reading the files again at a restart's BEGIN attributed the
    restarted game to source bytes the interpreter never loaded. Each BEGIN now
    reads the loader's identity, which stays unchanged without a reload, and
    retains it through END. This drives two Tetris games in one session, changes a
    covered module's file after the first BEGIN, and requires both saved records
    to carry the identity of the loaded implementation.
    """
    limit = 60
    config = SuiteConfig(GAME, limit, (2,), ("tetris",))
    module = sys.modules["block_stack_ai.tetris"]
    original_path = Path(module.__file__)
    original_bytes = original_path.read_bytes()
    original_digest = runner._objective_sources(
        runner._IDENTITY_DISPATCH)["block_stack_ai.tetris"]
    session = LiveSession(config, tmp_path / "runs")
    try:
        # The second game is a live restart (`R`) after the edit.
        for _ in range(2):
            with create_game(**GAME, seed=2) as desktop:
                snapshot = desktop.save_state()
                session.receive("BEGIN", snapshot)
                mutated = tmp_path / "tetris.py"
                mutated.write_bytes(original_bytes + b"\n# changed mid-game\n")
                monkeypatch.setattr(module, "__file__", str(mutated))
                while not desktop.state.terminal and desktop.state.frame < limit:
                    mask = session.receive("STATE", snapshot)
                    desktop.step(mask)
                    snapshot = desktop.save_state()
                session.receive("END", snapshot)
    finally:
        monkeypatch.setattr(module, "__file__", str(original_path))
        session.close()
    records = sorted((tmp_path / "runs").glob("*/run.json"))
    assert len(records) == 2
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["objective"] == session.objective["objective"]
        assert record["objective"]["sources"]["block_stack_ai.tetris"] == original_digest


@pytest.mark.parametrize("reload_mode", ["complete", "objective_only", "agents_only"])
def test_live_session_refreshes_loaded_identity_at_each_begin(tmp_path, reload_mode):
    """A reused session records reloaded objective code, or is refused outright.

    A session built before a reload keeps running the class it was constructed
    from. Reloading the objective modules without the live module leaves the
    running controller's references stale in its module namespaces, so the next
    BEGIN is refused as an inconsistent closure; reloading the live module
    replaces the class while the retained instance still executes the previous
    ``receive``, so the session is refused before any identity is captured and a
    newly constructed session records the reloaded identity and runs the
    reloaded objective. Only a complete reload followed by a fresh session is a
    describable implementation.
    """
    package = Path(sys.modules["block_stack_ai"].__file__).parent
    source_root = tmp_path / "src"
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    # Use a separate interpreter and package copy so reloads cannot affect other
    # tests or modify the checkout. Both games use the real native mirror.
    code = r'''
import importlib
import json
from pathlib import Path
import sys
from block_stack_ai import agents, live, runner, tetris

root = Path(sys.argv[1])
mode = sys.argv[2]
game = {"ruleset": "classic_ntsc_extended", "mode": "endless",
        "start_level": 18, "height": 0}
config = runner.SuiteConfig(game, 1, (2,), ("tetris",))
session = live.LiveSession(config, root / "runs")
try:
    initial = session.game.save_state()
    session.receive("BEGIN", initial)
    original = session.objective["objective"]
    session.receive("STATE", initial)
    session.receive("END", session.game.save_state())
    runner.verify_run(session.records[0])

    source = Path(tetris.__file__)
    text = source.read_text(encoding="utf-8")
    changed = text.replace('"tetrises": 8.0,', '"tetrises": 9.0,')
    assert changed != text
    source.write_text(changed, encoding="utf-8")
    # The live module changes too, so the retained session's class and the
    # reloaded module's identity are different implementations.
    live_source = Path(live.__file__)
    live_source.write_text(
        live_source.read_text(encoding="utf-8")
        + "\n# reloaded while a session was retained\n",
        encoding="utf-8",
    )
    modules = {"complete": (tetris, agents, runner, live),
               "objective_only": (tetris,), "agents_only": (agents,)}[mode]
    for module in modules:
        importlib.reload(module)

    if mode != "complete":
        try:
            session.receive("BEGIN", initial)
        except runner.VerificationError as error:
            assert "inconsistent" in str(error), str(error)
        else:
            raise AssertionError("BEGIN accepted a partially reloaded implementation")
        assert not session.active
        assert len(session.records) == 1
    else:
        expected = runner._objective_section(
            config, loaded=True, shape=runner._IDENTITY_LIVE)["objective"]
        assert expected["sources"] != original["sources"]
        first_record = json.loads(session.records[0].read_text(encoding="utf-8"))
        # The retained session runs the previous class's ``receive``. Its next
        # BEGIN has to be refused rather than stamped with the reloaded module's
        # digest, because the code that would choose the game's inputs is not the
        # code the record would name.
        try:
            session.receive("BEGIN", initial)
        except runner.VerificationError as error:
            assert "reloaded after this session" in str(error), str(error)
        else:
            raise AssertionError("BEGIN accepted a session the live reload left stale")
        assert not session.active
        assert len(session.records) == 1
        # A new session runs the reloaded class and records the reloaded identity.
        session.close()
        session = live.LiveSession(config, root / "runs")
        session.receive("BEGIN", initial)
        assert type(session.agent) is agents.TetrisAgent
        calls = []
        def track(frame, event, arg):
            if event == "call" and frame.f_code is tetris.tetris_choice.__code__:
                calls.append(frame.f_globals["TETRIS_WEIGHTS"]["tetrises"])
        sys.setprofile(track)
        try:
            session.receive("STATE", initial)
        finally:
            sys.setprofile(None)
        session.receive("END", session.game.save_state())
        record = json.loads(session.records[-1].read_text(encoding="utf-8"))
        assert calls == [9.0], calls
        assert record["objective"] == expected, record["objective"]
        assert first_record["objective"] == original
        runner.verify_run(session.records[-1])
finally:
    session.close()
'''
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), reload_mode], cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONPATH": str(source_root),
             "BLOCK_STACK_ROOT": str(engine_root()),
             "BLOCKS_NATIVE_LIB": str(native_library_path())},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_live_session_refuses_a_stale_controller_closure(tmp_path):
    """An objective-less session refuses a controller reload it cannot describe.

    The reviewer's finding: ``greedy``, ``random`` and ``lookahead`` declare no
    objective, so their version-8 record's identity is the controller section
    alone. Reloading ``agents`` without its importers leaves
    ``runner.create_agent`` pointing at the previous function while the
    controller walk would hash the reloaded ``agents`` module, so the record
    would name bytes that did not build the agent. The loaded view of the
    controller identity runs the same inconsistent-closure check the objective
    identity runs, and this drives that check through a separate interpreter.
    """
    package = Path(sys.modules["block_stack_ai"].__file__).parent
    source_root = tmp_path / "src"
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    code = r'''
import importlib
from pathlib import Path
import sys
from block_stack_ai import agents, live, runner

root = Path(sys.argv[1])
game = {"ruleset": "classic_ntsc_extended", "mode": "endless",
        "start_level": 18, "height": 0}
config = runner.SuiteConfig(game, 1, (2,), ("lookahead",))
session = live.LiveSession(config, root / "runs")
try:
    initial = session.game.save_state()
    importlib.reload(agents)
    try:
        session.receive("BEGIN", initial)
    except runner.VerificationError as error:
        assert "inconsistent" in str(error), str(error)
        assert "runner.create_agent" in str(error), str(error)
        print("refused")
    else:
        raise AssertionError("the controller section accepted a stale closure")
finally:
    session.close()
'''
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)], cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONPATH": str(source_root),
             "BLOCK_STACK_ROOT": str(engine_root()),
             "BLOCKS_NATIVE_LIB": str(native_library_path())},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "refused" in completed.stdout
