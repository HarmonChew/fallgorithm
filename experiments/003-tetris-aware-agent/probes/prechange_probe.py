"""Pre-change probes: each new 003 regression's contract, run on a pre-change tree.

Run this file with a pre-change tree's ``src`` on ``PYTHONPATH`` — the recorded
base commit, or the tree of the earlier publication this repair replaces:

    sandbox=/tmp/exp003-base
    mkdir -p $sandbox && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C $sandbox
    PYTHONPATH=$sandbox/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

    before=/tmp/exp003-before
    mkdir -p $before && git archive dc3c29c449c439ad8df415404d4df6d0eeb0087f | tar -x -C $before
    PYTHONPATH=$before/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

Copying this tree's ``src`` into an equally plain directory shows the same ids
satisfied after the change:

    after=/tmp/exp003-after
    mkdir -p $after && cp -r src $after/src
    PYTHONPATH=$after/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

Each id evaluates one new regression's contract against pre-change code as far
as that code can express it, prints what the tree under test reports, and exits 1
when that tree's behaviour violates the regression's assertion (the expected
result for the rows added by the clear-size, Tetris-objective and suite-wide
histogram changes) or 0 when the contract already held before the change (the
legacy-record and explicit-``--agent`` compatibility rows). A contract whose
subject does not exist at a pre-change tree at all is never counted as a
failure-before on an import: the probe reports the value it measured instead of
aborting, and those rows carry an executed substitute named in ``notes.md``.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import block_stack_ai

BASE_MODULE = block_stack_ai.__file__


def _guard() -> None:
    """Refuse to run against this worktree, and report which tree is under test.

    The path check is the real guard: pointing ``PYTHONPATH`` at this worktree
    would evaluate the contracts against the code the change already made. The
    tree's own shape is printed instead of being required, because the tree of the
    earlier publication this repair replaces also carries ``block_stack_ai.tetris``
    while it still records no objective and still compares the histogram per
    agent, and those are exactly the values these probes measure.
    """
    if "003-tetris-aware-agent" in str(BASE_MODULE):
        raise SystemExit(f"refusing to run: imported {BASE_MODULE}, not a pre-change tree")
    print(f"# tree under test: {BASE_MODULE}")
    tetris_module = Path(block_stack_ai.__file__).parent / "tetris.py"
    print(f"# block_stack_ai/tetris.py: {'present' if tetris_module.exists() else 'absent'}; "
          f"runner declares the objective section: {hasattr(runner, '_OBJECTIVE_FIELD')}")


from block_stack_ai import runner  # noqa: E402
from block_stack_ai.agents import AGENT_NAMES, GreedyPolicy, create_agent  # noqa: E402
from block_stack_ai.heuristic import (  # noqa: E402
    HEIGHT,
    WIDTH,
    board_features,
    board_grid,
    enumerate_placements,
    feature_score,
)
from block_stack_ai.pathaware import lookahead_choice  # noqa: E402

EVENT_NAMES = (
    "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
    "game_over", "challenge_completed", "lines_cleared", "score_delta",
)
HIDDEN = ((0,) * WIDTH,) * 2


def grid_of(rows):
    return board_grid(tuple(tuple(row) for row in rows), HIDDEN)


def blank_rows():
    return [[0] * WIDTH for _ in range(HEIGHT)]


def well_grid():
    """Four full rows under columns 0-8: the 003 ``well_grid``, a 4-deep well."""
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        for column in range(WIDTH - 1):
            rows[row][column] = 1
    return grid_of(rows)


@dataclass
class FakeState:
    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"
    piece_count: int = 0


class ClearGame:
    """The new metric test's stand-in, as far as the base runner implements it.

    Every base-runner field the scripted path reads exists here, and the step
    reports the same per-step clear size the registered binding reports, so the
    base tree really computes an episode for this game rather than aborting.
    """

    def __init__(self, clears, **_):
        self.state = FakeState()
        self.clears = list(clears)
        self.index = 0
        self.locks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

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


SCRIPTED = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 0,
             "height": 0, "seed": 42},
    "frame_limit": 5,
    "script": [{"mask": 0, "frames": 5}],
}

# A live suite whose agents exclude greedy, the shape that exposes the base
# CLI's hard-coded default: 003 is ``lookahead`` and ``tetris``.
SUITE_WITHOUT_GREEDY = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless",
             "start_level": 18, "height": 0},
    "frame_limit": 200000,
    "seeds": [2],
    "agents": ["lookahead"],
}


def r1_clear_sizes_field():
    """The new per-episode histogram, against base ``_play``'s own output."""
    config = runner.parse_config(SCRIPTED)
    episode = runner.run_episode(config, lambda **_: ClearGame([1, 2, 4, 0, 3]))
    print(f"# base episode keys: {sorted(episode)}")
    print(f"# base result.lines: {episode['result']['lines']}, "
          f"base event_counts.lines_cleared: {episode['result']['event_counts']['lines_cleared']}")
    assert "clear_sizes" in episode, (
        "the base runner records no per-episode clear-size histogram: "
        f"episode keys are {sorted(episode)}, so the singles/doubles/triples/tetrises "
        "the regression reads cannot be recovered from a base record"
    )
    assert episode["clear_sizes"] == {"singles": 1, "doubles": 1, "triples": 1, "tetrises": 1}


def r2_clear_sizes_summary():
    """The new per-agent summary totals, against base ``_summarize``."""
    episodes = [
        {"agent": "greedy", "seed": 1, "pieces_placed": 5,
         "result": {"score": 0, "lines": 10, "frame_count": 5, "stopping_reason": "frame_limit"}},
        {"agent": "greedy", "seed": 2, "pieces_placed": 5,
         "result": {"score": 0, "lines": 10, "frame_count": 5, "stopping_reason": "frame_limit"}},
    ]
    summary = runner._summarize(episodes)
    print(f"# base summary.greedy keys: {sorted(summary['greedy'])}")
    assert "clear_sizes" in summary["greedy"], (
        "the base summary carries no per-agent clear-size totals: keys are "
        f"{sorted(summary['greedy'])}"
    )
    assert summary["greedy"]["clear_sizes"] == {"singles": 2, "doubles": 2,
                                                "triples": 2, "tetrises": 2}


def r3_legacy_record_verifies():
    """The compatibility pin: a base record has no histogram and still verifies.

    The new verifier must keep accepting records like this one; the base tree can
    express the fixture (a record without the field) but not the new verifier, so
    this row is a ``0`` pin rather than a failure-before.
    """
    # Pin the recorded and current engine metadata to one value, exactly as the
    # new unit test does, so the probe measures the record schema and not this
    # machine's engine checkout.
    runner.engine_root = lambda: Path("/engine")
    runner.git_info = lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    with tempfile.TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text(json.dumps(SCRIPTED), encoding="utf-8")
        factory = lambda **_: ClearGame([1, 2, 4, 0, 3])
        path = runner.run_and_save(config_path, Path(directory) / "runs", factory)
        record = json.loads(path.read_text(encoding="utf-8"))
        print(f"# base record top-level keys: {sorted(record)}")
        warnings = runner.verify_run(path, factory)
    assert "clear_sizes" not in record
    assert warnings == []
    print("# the base record carries no clear_sizes and the base verifier accepts it")


def r4_premature_clear():
    """The new agent's central decision, against the frozen 002/greedy choice.

    On the well board the T can drop into the four-deep well for a single, or go
    elsewhere and leave the well for a vertical I. The base objective has no
    premature-clear charge and no well term, so both frozen agents take the
    single and leave a one-row-deep well: the base really evaluates this contract
    and its value contradicts the new assertion.
    """
    grid = well_grid()
    lookahead = lookahead_choice(grid, "T", "O", level=18, lines=0, start_level=18,
                                 first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                 mode="endless")
    greedy = GreedyPolicy().choose(enumerate_placements(grid, "T"))
    print(f"# frozen lookahead choice: (orientation, x, y, lines_cleared) = "
          f"{lookahead.orientation, lookahead.x, lookahead.y, lookahead.lines_cleared}")
    print(f"# frozen greedy choice: (orientation, x, y, lines_cleared) = "
          f"{greedy.orientation, greedy.x, greedy.y, greedy.lines_cleared}")
    assert lookahead.lines_cleared == 0 and greedy.lines_cleared == 0, (
        "the new agent must not spend a four-deep well on a one-line clear, but "
        f"the frozen agents clear {greedy.lines_cleared} row(s)"
    )


def r5_tetris_term():
    """The new clear term, against the frozen marginal value of one cleared line.

    The frozen objective values every cleared line at ``WEIGHTS['lines_cleared']``,
    so the marginal value of the one-line clear the new objective charges ``-3.0``
    is ``+1.0`` at the base: the base objective rewards exactly what the new one
    penalises. The marginal is isolated by scoring the same board with one line
    cleared and with none, so no other board feature enters the number.
    """
    from block_stack_ai.heuristic import WEIGHTS
    features = board_features(grid_of(blank_rows()))
    marginal = feature_score(features, 1) - feature_score(features, 0)
    print(f"# frozen weight for a cleared line: {WEIGHTS['lines_cleared']}")
    print(f"# frozen marginal value of a one-line clear: {marginal}")
    assert marginal <= -3.0, (
        f"the new clear term charges a one-line clear -3.0, but the frozen objective "
        f"values the same line at {marginal}: the frozen objective rewards the premature "
        "clear the new one penalises"
    )


def r6_agent_name():
    """The new agent name, against the base registry."""
    print(f"# base AGENT_NAMES: {AGENT_NAMES}")
    assert "tetris" in AGENT_NAMES, (
        f"the base registry has no tetris agent: {AGENT_NAMES}"
    )
    assert create_agent("tetris", 2) is not None


def r7_live_clear_sizes():
    """The live-play record's histogram, against base ``LiveSession``.

    Live play builds its own episode and saves it as a suite record, so it is the
    second path that records episodes. At the base it counts the engine's events
    but keeps no clear-size histogram, while the game it plays really does clear
    lines, so a base live record cannot yield a Tetris count either.
    """
    from block_stack_ai.engine import create_game
    from block_stack_ai.live import LiveSession
    from block_stack_ai.runner import SuiteConfig

    game = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18,
            "height": 0}
    limit = 600
    with tempfile.TemporaryDirectory() as directory:
        session = LiveSession(SuiteConfig(game, limit, (2,), ("greedy",)),
                              Path(directory) / "runs")
        try:
            with create_game(**game, seed=2) as desktop:
                snapshot = desktop.save_state()
                session.receive("BEGIN", snapshot)
                while not desktop.state.terminal and desktop.state.frame < limit:
                    mask = session.receive("STATE", snapshot)
                    desktop.step(mask)
                    snapshot = desktop.save_state()
                session.receive("END", snapshot)
        finally:
            session.close()
        record = json.loads(next((Path(directory) / "runs").glob("*/run.json"))
                            .read_text(encoding="utf-8"))
        episode = record["episodes"][0]
        print(f"# base live episode keys: {sorted(episode)}")
        print(f"# base live game lines: {episode['result']['lines']}, "
              f"stopping reason: {episode['result']['stopping_reason']}")
        print(f"# base live summary keys: {sorted(record['summary']['greedy'])}")
        assert episode["result"]["lines"] > 0, "the live game must clear lines for this test to bite"
        assert "clear_sizes" in episode, (
            "the base live session records no clear-size histogram: episode keys are "
            f"{sorted(episode)}"
        )
        assert episode["clear_sizes"]["singles"] + episode["clear_sizes"]["doubles"] > 0


def r8_cli_default_agent():
    """The new per-experiment ``--agent`` default, against the base CLI.

    The base ``play`` hard-codes ``greedy`` as the default agent. A suite
    experiment that does not offer greedy — like 003, whose agents are
    ``lookahead`` and ``tetris`` — therefore cannot be started without an
    explicit ``--agent``: the base CLI passes greedy and ``play_live`` rejects
    it before any engine is needed. The new CLI resolves the default from the
    selected config instead, so the same invocation starts the experiment's
    first agent.
    """
    from block_stack_ai import cli

    with tempfile.TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text(json.dumps(SUITE_WITHOUT_GREEDY), encoding="utf-8")
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            status = cli.main(["play", "--config", str(config_path), "--seed", "2"])
    message = errors.getvalue().strip()
    print(f"# base cli play --config <agents=['lookahead']> exit: {status}")
    print(f"# base cli stderr: {message}")
    assert status == 0, (
        "the base CLI hard-codes --agent greedy, so an experiment that does not "
        f"offer greedy cannot start without an explicit --agent: exit {status}, {message!r}"
    )


def r9_cli_explicit_agent_is_passed_through():
    """Compatibility pin: an explicit ``--agent`` wins over any default.

    Both trees pass an explicit ``--agent`` straight through to ``play_live``;
    the probe records what the base CLI passes, with ``play_live`` replaced by a
    recorder so no desktop binary is needed. The new CLI must keep doing this,
    which its regression asserts.
    """
    from block_stack_ai import cli

    with tempfile.TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text(json.dumps(SUITE_WITHOUT_GREEDY), encoding="utf-8")
        seen = []
        original = cli.play_live
        cli.play_live = lambda *args: seen.append(args)
        try:
            status = cli.main(["play", "--config", str(config_path), "--agent", "lookahead"])
        finally:
            cli.play_live = original
    print(f"# base cli play --agent lookahead exit: {status}, recorded agent: "
          f"{seen[0][1] if seen else None!r}")
    assert status == 0 and seen and seen[0][1] == "lookahead", (
        f"the base CLI did not pass the explicit --agent through: exit {status}, saw {seen}"
    )


def r10_cli_absent_agent_still_fails():
    """Compatibility pin: an agent absent from the experiment still fails.

    The base CLI imports the argparse ``choices`` list from the agent registry
    and ``play_live`` checks membership in the selected config, so naming an
    agent the config does not offer already fails there; the new CLI preserves
    both checks, which its regression asserts.
    """
    from block_stack_ai import cli

    with tempfile.TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text(json.dumps(SUITE_WITHOUT_GREEDY), encoding="utf-8")
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            status = cli.main(["play", "--config", str(config_path), "--agent", "random"])
    message = errors.getvalue().strip()
    print(f"# base cli play --agent random exit: {status}, stderr: {message}")
    assert status == 1 and "not in this experiment" in message, (
        f"the base CLI accepted an agent absent from the experiment: exit {status}, {message!r}"
    )


@dataclass
class ChoiceState:
    """The placement-agent fields of an engine state, on an empty board.

    The board is empty, so every placement agent's reachable set is a real one;
    the stand-in ignores the mask, so the episode is deterministic whatever the
    agent chooses.
    """

    frame: int = 0
    score: int = 0
    lines: int = 0
    terminal: bool = False
    phase: str = "active"
    piece_count: int = 0
    current_piece: str = "T"
    next_piece: str = "O"
    board: object = ((0,) * WIDTH,) * HEIGHT
    hidden_rows: object = ((0,) * WIDTH,) * 2
    orientation: int = 0
    x: int = 5
    level: int = 18
    start_level: int = 18
    first_delay_remaining: int = 0
    ruleset: str = "classic_ntsc_extended"
    mode: str = "endless"


class ChoiceGame:
    """A stand-in whose suite episodes carry a real clear-size histogram.

    One piece locks every step and each step reports the next entry of ``clears``
    as the engine's own per-step clear size, so a two-frame episode records one
    single and one double.
    """

    def __init__(self, clears=(1, 2), **_):
        self.state = ChoiceState()
        self.clears = list(clears)
        self.index = 0
        self.locks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

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
# the Tetris agent whose objective the suite record must declare.
OBJECTIVE_SUITE = {
    "game": {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18,
             "height": 0},
    "frame_limit": 2,
    "seeds": [1],
    "agents": ["lookahead", "tetris"],
}
# A suite every pre-change tree can run: the histogram is agent-independent.
HISTOGRAM_SUITE = {**OBJECTIVE_SUITE, "agents": ["greedy", "lookahead"]}


def _suite_record(configuration):
    """A suite record from the tree under test, and the factory that replays it."""
    runner.engine_root = lambda: Path("/engine")
    runner.git_info = lambda root: {"commit": "abc123", "dirty": False, "kind": "committed"}
    directory = tempfile.mkdtemp(prefix="exp003-probe-")
    config_path = Path(directory) / "config.json"
    config_path.write_text(json.dumps(configuration), encoding="utf-8")
    factory = lambda **_: ChoiceGame()
    path = runner.run_and_save(config_path, Path(directory) / "runs", factory)
    return path, factory


def _run_experiment_suite(probe: str):
    """The experiment's suite through the tree's own writer, or a reported failure."""
    try:
        return _suite_record(OBJECTIVE_SUITE)
    except ValueError as error:
        raise AssertionError(
            f"{probe}: the tree cannot run the experiment's suite at all: "
            f"run_and_save raised {error!r}"
        ) from error


def r11_suite_objective_section():
    """A suite record declares the objective that chose its placements.

    The new writer records the Tetris agent's declared objective beside the frozen
    heuristic mapping. This runs the experiment's own configuration through the
    tree's own writer and requires the record to carry the section. A tree whose
    registry has no Tetris agent cannot run the suite at all, and a tree that runs
    it without recording the objective fails at the record's own keys; both are
    the pre-change values this row pins, and neither is an import error.
    """
    path, _ = _run_experiment_suite("suite_objective_section")
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# record top-level keys: {sorted(record)}")
    assert "objective" in record, (
        "the tree writes no declared-objective section for a suite that uses the "
        f"Tetris agent: record keys are {sorted(record)}"
    )
    print(f"# recorded objective: {record['objective']}")


def r12_objective_is_verified():
    """A recorded objective is compared, not ignored.

    The new verifier rejects a suite record whose declared objective differs from
    the module's current one. This writes the experiment's suite and then changes
    the recorded objective — a changed weight and a module name that is not the
    declaring module — and requires ``verify_run`` to reject it. A verifier that
    ignores the section accepts the record and reports no difference, which is the
    pre-change value this row pins.
    """
    path, factory = _run_experiment_suite("objective_is_verified")
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# recorded objective: {record.get('objective')}")
    if "objective" in record:
        record["objective"]["weights"]["tetrises"] = 1.0
        record["objective"]["module"] = "block_stack_ai.heuristic"
    else:
        record["objective"] = {
            "module": "block_stack_ai.heuristic",
            "weights": {**record["heuristic"], "tetrises": 1.0},
        }
    path.write_text(json.dumps(record), encoding="utf-8")
    print(f"# mutated objective written: {record['objective']}")
    try:
        warnings = runner.verify_run(path, factory)
    except runner.VerificationError as error:
        print(f"# verify_run rejected the mutated objective: {error}")
        return
    raise AssertionError(
        "the tree accepted a suite record whose declared objective is not the one that "
        f"chose its placements: verify_run returned {warnings}"
    )


def r13_suite_wide_histogram():
    """Clear-size presence is one suite-wide invariant.

    The new verifier requires the histogram on every episode and every agent
    summary of a record, or on none: a record that stripped it from one agent
    while another kept it reports only part of the lines it cleared, and a record
    that reports totals its episodes do not carry leaves its own reader without
    them. This builds a record with the tree's own writer and checks three cases
    on it — one agent stripped everywhere, one agent's summary stripped while its
    episodes keep the histogram, and the histogram stripped everywhere, which must
    still verify as a legacy record. The mixed states are built from whatever the
    writer records, so the same probe runs on a tree that records no histogram at
    all.
    """
    path, factory = _suite_record(HISTOGRAM_SUITE)
    record = json.loads(path.read_text(encoding="utf-8"))
    stripped = sorted(record["summary"])[0]
    print(f"# record top-level keys: {sorted(record)}")
    print(f"# agents: {sorted(record['summary'])}; first agent: {stripped}")
    violations = []

    def verdict(label, edited, must_reject):
        path.write_text(json.dumps(edited), encoding="utf-8")
        try:
            warnings = runner.verify_run(path, factory)
        except runner.VerificationError as error:
            print(f"# {label}: rejected: {error}")
            if not must_reject:
                violations.append(f"{label}: rejected a record that must verify: {error}")
            return
        print(f"# {label}: accepted, warnings {warnings}")
        if must_reject:
            violations.append(f"{label}: accepted a record that must be rejected")

    def mixed(record):
        """One agent stripped everywhere, or given a histogram when none exists."""
        edited = json.loads(json.dumps(record))
        others = [name for name in edited["summary"] if name != stripped]
        if any("clear_sizes" in episode for episode in edited["episodes"]):
            for episode in edited["episodes"]:
                if episode["agent"] == stripped:
                    episode.pop("clear_sizes", None)
            edited["summary"][stripped].pop("clear_sizes", None)
            return edited, f"one agent ({stripped}) stripped from its episodes and summary"
        zero = {field: 0 for field in ("singles", "doubles", "triples", "tetrises")}
        for episode in edited["episodes"]:
            if episode["agent"] in others:
                episode["clear_sizes"] = dict(zero)
        for name in others:
            edited["summary"][name]["clear_sizes"] = dict(zero)
        return edited, f"one agent ({others[0]}) given a histogram while {stripped} has none"

    edited, label = mixed(record)
    verdict(label, edited, True)

    summary_only = json.loads(json.dumps(record))
    if any("clear_sizes" in episode for episode in summary_only["episodes"]):
        summary_only["summary"][stripped].pop("clear_sizes", None)
        label = (f"one agent's ({stripped}) summary stripped while its episodes keep "
                 "the histogram")
    else:
        zero = {field: 0 for field in ("singles", "doubles", "triples", "tetrises")}
        for episode in summary_only["episodes"]:
            if episode["agent"] == stripped:
                episode["clear_sizes"] = dict(zero)
        label = (f"one agent's ({stripped}) episodes given a histogram while its summary "
                 "reports none")
    verdict(label, summary_only, True)

    legacy = json.loads(json.dumps(record))
    for episode in legacy["episodes"]:
        episode.pop("clear_sizes", None)
    for summary in legacy["summary"].values():
        summary.pop("clear_sizes", None)
    verdict("the histogram stripped everywhere (a legacy record)", legacy, False)

    assert not violations, "; ".join(violations)


def r14_live_objective_section():
    """A live Tetris game's record declares the objective, like a headless suite.

    Live play builds its own episode and saves it as a suite record, so the new
    writer records the declared objective there too. This drives the desktop
    protocol with the registered native mirror exactly as the live regression does
    and requires the saved record to carry the section. A tree without the agent
    cannot play the game at all, and a tree that plays it without recording the
    objective fails at the record's keys.
    """
    from block_stack_ai.engine import create_game
    from block_stack_ai.live import LiveSession
    from block_stack_ai.runner import SuiteConfig

    game = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18,
            "height": 0}
    limit = 600
    with tempfile.TemporaryDirectory() as directory:
        try:
            session = LiveSession(SuiteConfig(game, limit, (2,), ("tetris",)),
                                  Path(directory) / "runs")
        except ValueError as error:
            raise AssertionError(
                f"the tree cannot play a live Tetris game at all: {error!r}"
            ) from error
        try:
            with create_game(**game, seed=2) as desktop:
                snapshot = desktop.save_state()
                session.receive("BEGIN", snapshot)
                while not desktop.state.terminal and desktop.state.frame < limit:
                    mask = session.receive("STATE", snapshot)
                    desktop.step(mask)
                    snapshot = desktop.save_state()
                session.receive("END", snapshot)
        finally:
            session.close()
        record = json.loads(next((Path(directory) / "runs").glob("*/run.json"))
                            .read_text(encoding="utf-8"))
        print(f"# live episode keys: {sorted(record['episodes'][0])}")
        print(f"# live record top-level keys: {sorted(record)}")
        assert "objective" in record, (
            "the tree writes no declared-objective section for a live Tetris game: "
            f"record keys are {sorted(record)}"
        )
        print(f"# recorded objective: {record['objective']}")


PROBES = {
    "clear_sizes_field": r1_clear_sizes_field,
    "clear_sizes_summary": r2_clear_sizes_summary,
    "legacy_record_verifies": r3_legacy_record_verifies,
    "premature_clear": r4_premature_clear,
    "tetris_term": r5_tetris_term,
    "agent_name": r6_agent_name,
    "live_clear_sizes": r7_live_clear_sizes,
    "cli_default_agent": r8_cli_default_agent,
    "cli_explicit_agent": r9_cli_explicit_agent_is_passed_through,
    "cli_absent_agent": r10_cli_absent_agent_still_fails,
    "suite_objective_section": r11_suite_objective_section,
    "objective_is_verified": r12_objective_is_verified,
    "suite_wide_histogram": r13_suite_wide_histogram,
    "live_objective_section": r14_live_objective_section,
}


def main() -> int:
    _guard()
    if len(sys.argv) != 2 or sys.argv[1] not in PROBES:
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}}", file=sys.stderr)
        return 2
    name = sys.argv[1]
    print(f"# probe: {name}")
    try:
        PROBES[name]()
    except AssertionError as error:
        print(f"AssertionError: {error}")
        return 1
    print("result: the tree under test satisfies this probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
