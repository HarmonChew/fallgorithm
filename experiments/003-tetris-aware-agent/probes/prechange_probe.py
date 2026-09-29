"""Pre-change probes: each new 003 regression's contract, run on a pre-change tree.

Run this file with a pre-change tree's ``src`` on ``PYTHONPATH`` — the recorded
base commit, or the tree of an earlier publication this repair replaces:

    sandbox=/tmp/exp003-base
    mkdir -p $sandbox && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C $sandbox
    PYTHONPATH=$sandbox/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

    before=/tmp/exp003-before
    mkdir -p $before && git archive dc3c29c449c439ad8df415404d4df6d0eeb0087f | tar -x -C $before
    PYTHONPATH=$before/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

    reviewed=/tmp/exp003-reviewed
    mkdir -p $reviewed && git archive fbe21e1 | tar -x -C $reviewed
    PYTHONPATH=$reviewed/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

The third tree is the version the earlier repair replaced — the tree those
findings were measured against — and it carries both of that round's defects: its
``format_version`` does not say which sections its writer always emitted, and its
publication probe reads a per-path digest a state need not have.

The tree the current repair replaces is the last publication, whose identity
stops at the modules the objective's own imports reach:

    replaced=/tmp/exp003-replaced
    mkdir -p $replaced && git archive 63e432fff79d075fa9149ea7936751abfc42c546 | tar -x -C $replaced
    PYTHONPATH=$replaced/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

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

``publication_content`` is the one id whose subject is a probe file rather than
the tree's ``src``: it loads ``experiments/003-tetris-aware-agent/probes/evidence.py``
from the tree under test and drives that file's ``check_publication`` with the
reviewer's counterexample, so the run above shows whether that tree's probe
compares the repaired paths' content or only their presence. Pass a probe file as
the second argument when the tree under test carries only ``src``:

    PYTHONPATH=$after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content $PWD/experiments/003-tetris-aware-agent/probes/evidence.py

The later rounds added these ids of that shape — ``predeclaration_identity``,
``remote_main_durability``, ``publication_count_capture``, ``base_commit_record``,
``publication_record_derivation``, ``base_worktree_ancestry``,
``predeclaration_record_identity``, ``predeclaration_weights`` and
``objective_wrapper_identity`` — plus ``piece_summary_schema`` and
``summary_histogram_derivation``, whose subject is the runner, and
``live_objective_snapshot``, whose subject is the tree's ``live`` module. Each names the artifact it needs; a tree that carries no such
artifact predates the experiment and reports ``no subject on this tree`` instead
of aborting with an ``ImportError``, and is never counted as a failure-before. A
row whose contract is genuinely new capability is a **pin** (exit 0) and says so,
with its substitute evidence named.

This round's five rows are of the same shape and each names a claim that was only
ever compared with a copy of itself: ``publication_tree_derivation`` (the
commit/tree pairing must come from the repository's own objects),
``publication_paths_prose`` (the comparison-set sentence must come from the
captured per-path states), ``predeclaration_created_at`` (the retained order
sentence must come from the block's own two timestamps), ``format_version_prose``
(the version sentence must come from the writer's version table) and
``loaded_identity_reload`` (a module the process reloaded must be recorded as the
code that computes the choices, not as the identity bound at import). The first
four drive the tree's own ``evidence.py``; ``loaded_identity_reload`` runs
``loaded_identity_program.py`` in its ``reload`` mode against a copy of the tree's
package, like ``loaded_identity`` and ``stale_cache``.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import block_stack_ai

BASE_MODULE = block_stack_ai.__file__
# The publication-content probe loads a probe file to drive it: the tree under
# test's own copy by default, or the path in ``sys.argv[2]`` for the ``after``
# tree, which carries only ``src``.
DEFAULT_PUBLICATION_PROBE = (Path(BASE_MODULE).parents[2] / "experiments"
                             / "003-tetris-aware-agent" / "probes" / "evidence.py")
PUBLICATION_PROBE_OVERRIDE: Path | None = None


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
    histogram = {"singles": 1, "doubles": 1, "triples": 1, "tetrises": 1}
    episodes = [
        {"agent": "greedy", "seed": 1, "pieces_placed": 5, "clear_sizes": dict(histogram),
         "result": {"score": 0, "lines": 10, "frame_count": 5, "stopping_reason": "frame_limit"}},
        {"agent": "greedy", "seed": 2, "pieces_placed": 5, "clear_sizes": dict(histogram),
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
    # Stripping the histogram everywhere from a record of the current version
    # deletes a section its writer always emits, and must be reported; the same
    # JSON at the legacy version — the one whose writer recorded no histogram —
    # must verify. A pre-change tree has no such version, so it leaves its own
    # version in place and the stripped record is only its compatibility case.
    current = json.loads(json.dumps(legacy))
    verdict("the histogram stripped everywhere at the current version", current, True)
    legacy["format_version"] = getattr(
        runner, "LEGACY_SUITE_FORMAT_VERSION", legacy["format_version"]
    )
    verdict("the histogram stripped everywhere at the legacy version", legacy, False)

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


def r15_publication_content():
    """A publication probe must establish the repair from content, not presence.

    The reviewer's counterexample, reproduced offline: the published refs name an
    earlier publication whose repaired-path contents differ from the reviewed
    worktree while every one of those paths exists in it, and the worktree holds
    the repair uncommitted. A probe that certifies the repair from presence passes
    there and reports nothing about content, which is the defect; the tree under
    test must instead report the earlier-publication state, name the differing
    paths, and refuse a published tree that differs from a clean worktree. A second
    contract covers the same defect one level down: a probe that compares only a
    hand-listed set of paths certifies a publication as this worktree's when the
    only difference is a tracked path outside that list, so this probe also drives
    that state and requires the differing path to be reported.

    The target probe file is the tree under test's own
    ``experiments/003-tetris-aware-agent/probes/evidence.py`` by default, or the
    path given as a second argument — a copy of this tree's probe, for the
    ``after`` run whose tree carries only ``src``.
    """
    target = PUBLICATION_PROBE_OVERRIDE or DEFAULT_PUBLICATION_PROBE
    print(f"# target probe file: {target}")
    spec = importlib.util.spec_from_file_location("exp003_publication_target", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = tuple(getattr(module, "REPAIRED_PATHS", ()))
    assert paths, f"{target} declares no REPAIRED_PATHS to compare"
    earlier = "the refs name an earlier publication"
    equal = "published content equals this worktree"
    published_content = "the earlier publication's file\n"
    repaired_content = "the repair this worktree holds uncommitted\n"
    outside = "experiments/003-tetris-aware-agent/config.json"
    violations = []

    def drive(*, worktree_contents, published_contents, uncommitted, head):
        """Run the target probe on real content with its Git commands stubbed."""
        tracked = sorted(set(worktree_contents) | set(published_contents))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            published_root = root / "publication"
            worktree_root = root / "worktree"
            for path, content in worktree_contents.items():
                destination = worktree_root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")

            def fake_git(cwd, *arguments):
                command = " ".join(arguments)
                if command.startswith("ls-remote"):
                    return 0, (f"{head}\t{module.TASK_BRANCH_REF}\n"
                               f"{head}\t{module.TASK_PR_REF}")
                if command.startswith("clone "):
                    for path, content in published_contents.items():
                        destination = published_root / path
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_text(content, encoding="utf-8")
                    return 0, ""
                if command == "ls-files -z":
                    return 0, "\0".join(tracked) + "\0"
                if Path(cwd) == published_root:
                    if command == "rev-parse HEAD":
                        return 0, head
                    if command == "rev-parse HEAD^{tree}":
                        return 0, "0" * 40
                    if command.startswith("merge-base --is-ancestor"):
                        return 0, ""
                if Path(cwd) == worktree_root:
                    if command == "rev-parse HEAD":
                        return 0, head
                    if command == "status --porcelain":
                        return 0, ("\n".join(f" M {path}" for path in uncommitted)
                                   .strip())
                raise AssertionError(f"unexpected git command: {command}")

            module.PUBLICATION_CLONE = published_root
            module.PROJECT_ROOT = worktree_root
            module._git = fake_git
            captured = io.StringIO()
            try:
                with contextlib.redirect_stdout(captured):
                    module.check_publication()
            except AssertionError as error:
                return str(error), captured.getvalue()
            except TypeError as error:
                # A pre-change probe's defect raised while reporting a state it
                # cannot describe — reading a digest that side does not have. It is
                # returned as that case's value so the rest of the row still runs
                # and the row reports the defect instead of aborting on it.
                return f"TypeError: {error}", captured.getvalue()
        return None, captured.getvalue()

    declared = tuple(paths)
    earlier_commit = "1" * 40
    error, output = drive(worktree_contents={p: repaired_content for p in declared},
                          published_contents={p: published_content for p in declared},
                          uncommitted=paths, head=earlier_commit)
    print(f"# {earlier_commit[:7]} published, worktree dirty holding the repair: "
          f"exit {'1' if error else '0'}"
          f"{f' ({error})' if error else ''}")
    if error is not None:
        violations.append(f"the dirty-worktree case failed: {error}")
    if earlier not in output:
        violations.append("the dirty-worktree case reported no content comparison: "
                          f"it certified from presence (stdout {len(output)} bytes, "
                          f"no {earlier!r} line)")
    if equal in output:
        violations.append("the dirty-worktree case called the repair published")
    for path in paths:
        if f"differs {path}" not in output:
            violations.append(f"the dirty-worktree case did not name the differing path {path}")
    print(f"#   reported {output.count('| differs')} differing paths of {len(paths)}")

    error, output = drive(worktree_contents={p: repaired_content for p in declared},
                          published_contents={p: published_content for p in declared},
                          uncommitted=(), head=earlier_commit)
    print(f"# {earlier_commit[:7]} published, worktree clean: exit "
          f"{'1' if error else '0'}{f' ({error})' if error else ''}")
    if error is None:
        violations.append("the clean-worktree case passed, so a published tree that is not "
                          "this worktree's content was certified as carrying the repair")

    error, output = drive(worktree_contents={p: published_content for p in declared},
                          published_contents={p: published_content for p in declared},
                          uncommitted=(), head=earlier_commit)
    print(f"# {earlier_commit[:7]} published, worktree clean and equal: exit "
          f"{'1' if error else '0'}{f' ({error})' if error else ''}")
    if error is not None:
        violations.append(f"the equal-content clean-worktree case failed: {error}")
    elif equal not in output:
        violations.append("the equal-content clean-worktree case reported no equal-content line")

    worktree_contents = {p: published_content for p in declared}
    worktree_contents[outside] = repaired_content
    published_contents = {p: published_content for p in declared}
    published_contents[outside] = published_content
    error, output = drive(worktree_contents=worktree_contents,
                          published_contents=published_contents,
                          uncommitted=(outside,), head=earlier_commit)
    print(f"# {earlier_commit[:7]} published, only {outside} differs, worktree dirty: exit "
          f"{'1' if error else '0'}{f' ({error})' if error else ''}")
    if error is not None:
        violations.append(f"the path-outside-the-declared-list case failed: {error}")
    if equal in output:
        violations.append(f"the path-outside-the-declared-list case certified a publication "
                          f"as this worktree when only {outside} differed, which the declared "
                          f"list does not name")
    if f"differs {outside}" not in output:
        violations.append(f"the path-outside-the-declared-list case did not name {outside}")

    # A tracked deletion: the publication holds every compared path, this worktree
    # has deleted one of them, so that path has a published digest and none here.
    # A report that reads the missing digest raises instead of describing the
    # tree; the deletion must be named and the report completed.
    deleted = declared[0]
    error, output = drive(worktree_contents={p: published_content for p in declared
                                             if p != deleted},
                          published_contents={p: published_content for p in declared},
                          uncommitted=(deleted,), head=earlier_commit)
    print(f"# {earlier_commit[:7]} published, {deleted} deleted in the worktree: exit "
          f"{'1' if error else '0'}{f' ({error})' if error else ''}")
    if error is not None:
        violations.append(f"the tracked-deletion case failed: {error}")
    if f"deleted {deleted}" not in output:
        violations.append(f"the tracked-deletion case did not report the tracked deletion of "
                          f"{deleted}")

    assert not violations, "; ".join(violations)


def r16_objective_required_when_versioned():
    """A current record must carry the objective its own writer always emits.

    The reviewer's counterexample, reproduced: the experiment's suite is written
    by the tree's own writer and the declared-objective section is then deleted
    without touching ``format_version``. A verifier that reads "legacy" from the
    absent section accepts the stripped record and reports nothing, so a record of
    the current version can lose the section that ties it to the objective which
    chose its placements. The tree must report the absence instead, and the same
    JSON declared at the legacy version — a record predating the section — must
    still verify. A tree that cannot run the suite at all reports that, rather than
    aborting on an import.
    """
    path, factory = _run_experiment_suite("objective_required_when_versioned")
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# record format_version: {record.get('format_version')}")
    print(f"# record top-level keys: {sorted(record)}")
    if "objective" not in record:
        raise AssertionError(
            "the tree writes no declared-objective section for a suite that uses the Tetris "
            f"agent, so there is nothing for the version to require: record keys are "
            f"{sorted(record)}"
        )
    stripped = json.loads(json.dumps(record))
    del stripped["objective"]
    path.write_text(json.dumps(stripped), encoding="utf-8")
    try:
        warnings = runner.verify_run(path, factory)
    except runner.VerificationError as error:
        print(f"# the same record with the section deleted is reported: {error}")
    else:
        raise AssertionError(
            "the tree accepted a record of its own version with the declared objective "
            f"deleted, so the record verifies under whatever objective is current: "
            f"verify_run returned {warnings}"
        )

    legacy = json.loads(json.dumps(stripped))
    legacy["format_version"] = getattr(
        runner, "LEGACY_SUITE_FORMAT_VERSION", legacy["format_version"]
    )
    path.write_text(json.dumps(legacy), encoding="utf-8")
    try:
        warnings = runner.verify_run(path, factory)
    except runner.VerificationError as error:
        raise AssertionError(
            f"the tree rejected a legacy record that predates the section, which must keep "
            f"verifying: {error}"
        ) from error
    print(f"# the same JSON at the legacy version still verifies: warnings {warnings}")


def r17_objective_identity():
    """A record's objective is identified by its source, not only by its weights.

    The reviewer's counterexample: the objective's clear term is changed — a
    premature clear is charged at twice the declared rate — while every weight
    constant stays exactly as it was. The recorded weights therefore still compare
    equal, and a record written under the old formula verifies under the new one
    whenever the replayed choices happen to be preserved. This writes the
    experiment's suite with the tree's own writer, changes the declaring module's
    source, and requires the tree to reject the record. A tree whose objective
    section is the module name and the weights accepts it and reports nothing,
    which is the pre-change value this row pins; a tree whose writer records the
    objective's source identity reports the changed digest instead. The record's
    episodes are replayed through a stand-in that ignores the mask, so the changed
    formula cannot move the recorded inputs: the identity is the only thing that
    can tell the two objectives apart.
    """
    import importlib

    path, factory = _run_experiment_suite("objective_identity")
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# record format_version: {record.get('format_version')}")
    objective = record.get("objective")
    if objective is None:
        raise AssertionError(
            "the tree writes no declared-objective section for a suite that uses the Tetris "
            f"agent, so no identity could be recorded: record keys are {sorted(record)}"
        )
    print(f"# recorded objective keys: {sorted(objective)}")
    print(f"# recorded weights: {objective.get('weights')}")
    print(f"# recorded identity: {objective.get('sources')}")

    try:
        from block_stack_ai import tetris
    except ImportError as error:
        raise AssertionError(
            "the tree declares no Tetris objective module, so there is no objective whose "
            f"formula this probe could change: {error}"
        ) from error
    module = Path(tetris.__file__)
    original = module.read_text(encoding="utf-8")
    changed = original.replace(
        'return TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
        'return 2 * TETRIS_WEIGHTS["premature_clear"] * (4 - lines_cleared)',
    )
    if changed == original:
        raise AssertionError(
            f"the tree's objective does not contain the clear term this probe changes: {module}"
        )
    try:
        module.write_text(changed, encoding="utf-8")
        importlib.reload(tetris)
        print(f"# changed clear term: clear_term(1) is now {tetris.clear_term(1)} "
              f"(declared -3.0), weights unchanged: "
              f"{tetris.weights_record() == objective.get('weights')}")
        try:
            warnings = runner.verify_run(path, factory)
        except runner.VerificationError as error:
            print(f"# the record is reported under the changed objective: {error}")
            if "objective" not in str(error):
                raise AssertionError(
                    "the tree rejected the record, but not for the objective's identity: "
                    f"{error}"
                ) from error
        else:
            raise AssertionError(
                "the tree accepted a record whose objective's formula changed while its "
                f"weights did not, so the record verifies under an objective that did not "
                f"produce it: verify_run returned {warnings}"
            )
    finally:
        module.write_text(original, encoding="utf-8")
        importlib.reload(tetris)
    print(f"# the unchanged objective verifies again: warnings {runner.verify_run(path, factory)}")


class SubjectAbsent(Exception):
    """The tree under test carries no artifact a row's subject names.

    Raised instead of letting a missing file abort as an ``ImportError``: the row
    reports what it could not find, and it is never counted as a failure-before.
    """


def _target_probe():
    """The probe file under test: this tree's, or the path given as a second argument.

    A tree older than the experiment carries no such file at all (Experiment 003
    did not exist at the recorded base commit), which is reported rather than
    raised as an import error.
    """
    target = PUBLICATION_PROBE_OVERRIDE or DEFAULT_PUBLICATION_PROBE
    if not target.exists():
        raise SubjectAbsent(
            f"{target} does not exist: the tree under test predates Experiment 003, so this "
            "row has no subject there"
        )
    print(f"# target probe file: {target}")
    spec = importlib.util.spec_from_file_location("exp003_target_probe", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return Path(target), module


def _target_record(target: Path) -> tuple[Path, dict]:
    """The retained record that belongs to the tree the target probe file came from."""
    path = (target.resolve().parents[3] / "experiments" / "003-tetris-aware-agent"
            / "result.json")
    return path, json.loads(path.read_text(encoding="utf-8"))


# One episode per agent and seed, so a group's first episode can be stripped
# without emptying the group: the mixed shape this round's finding names.
PIECES_SUITE = {**HISTOGRAM_SUITE, "seeds": [1, 2]}


def r18_piece_summary_schema():
    """The summary's piece count is read from the record's schema, not one episode.

    The reviewer's counterexample, reproduced against the tree's own writer: the
    first episode of every agent loses its piece count, the summaries lose the
    metric, the later episodes keep their counts, and the record is declared at
    the legacy version, whose writer may omit the count. A verifier that selects
    the summary's metric from the first episode of each group re-derives a summary
    with no piece metric, matches the stripped record and reports nothing — a
    mixed schema no writer emits. This tree reads the key from every episode and
    reports it. A tree whose writer records no piece count at all is reported
    instead of being counted as a failure.
    """
    path, factory = _suite_record(PIECES_SUITE)
    record = json.loads(path.read_text(encoding="utf-8"))
    fields = [field for field in ("pieces_placed", "pieces")
              if all(field in episode for episode in record["episodes"])]
    if not fields:
        raise AssertionError(
            "the tree's writer records no piece count on every episode, so this record "
            "cannot be stripped into the mixed shape the finding names"
        )
    field = fields[0]
    stripped = json.loads(json.dumps(record))
    first_of_agent = {}
    for episode in stripped["episodes"]:
        first_of_agent.setdefault(episode["agent"], episode)
    for episode in stripped["episodes"]:
        if first_of_agent[episode["agent"]] is episode:
            del episode[field]
    for summary in stripped["summary"].values():
        summary.pop(field, None)
    stripped["format_version"] = getattr(
        runner, "LEGACY_SUITE_FORMAT_VERSION", stripped["format_version"])
    path.write_text(json.dumps(stripped), encoding="utf-8")
    print(f"# the writer's piece key: {field}; the record is declared at "
          f"format_version {stripped['format_version']}")
    print(f"# episodes carrying {field}: "
          f"{sum(1 for episode in stripped['episodes'] if field in episode)} of "
          f"{len(stripped['episodes'])}")
    try:
        warnings = runner.verify_run(path, factory)
    except runner.VerificationError as error:
        print(f"# the mixed record is reported: {error}")
        return
    except KeyError as error:
        raise AssertionError(
            f"the tree cannot summarise the record at all: verify_run raised KeyError({error}) "
            "because the summary's piece key is selected from the group's first episode, which "
            "no longer carries it, while the later episodes carry a different one"
        ) from error
    raise AssertionError(
        f"the tree accepted a record whose first episode of each agent carries no {field} "
        f"while the later episodes keep it, and whose summaries report no piece metric at "
        f"all: verify_run returned {warnings}"
    )


def r19_predeclaration_identity():
    """The captured objective covers every module its decisions are computed from.

    The reviewer's counterexample: the capture records only the declaring module's
    digest while the recorded objective identity covers that module plus the
    helpers its code calls, so a post-capture change to a helper still passes
    ``check-predeclaration`` although it moves every value the objective computes.
    This captures the objective with the target probe's own ``predeclare``, then
    changes a **helper** module — through a mutated copy of its file, so nothing
    under test is touched — and requires the check to report it. A tree whose
    check hashes only the declaring module accepts the changed tree.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_predeclaration"):
        raise SubjectAbsent(
            f"{target} has no check_predeclaration: this row's subject is the declared "
            "objective's capture, and that tree does not capture one"
        )
    with tempfile.TemporaryDirectory(prefix="exp003-predeclaration-") as directory:
        scratch = Path(directory)
        capture = scratch / "predeclared_objective.probe.json"
        module.PREDECLARATION = capture
        module.predeclare()
        # The cited record has to postdate the capture; a helper's change is what
        # this row measures, not the ordering, so a fresh record stands in for it.
        # A check that requires the record's own identity (this round's) needs the
        # capture's identity here; a pre-change check ignores it.
        cited = scratch / "probe-record.json"
        captured = json.loads(capture.read_text(encoding="utf-8"))
        record = {"created_at": "2099-01-01T00:00:00+00:00"}
        if "sources" in captured:
            record["objective"] = {"sources": captured["sources"],
                                   "weights": captured["objective"]}
        cited.write_text(json.dumps(record), encoding="utf-8")
        module.check_predeclaration(cited)
        print("# the unchanged tree passes the check")
        captured_module_digest = captured["module_sha256"]
        identity = getattr(runner, "_objective_sources", None)
        names = sorted(identity()) if identity is not None else ["block_stack_ai.heuristic"]
        helper = next((name for name in names
                       if name != "block_stack_ai.tetris"
                       and getattr(sys.modules.get(name), "__file__", None)), None)
        if helper is None:
            raise AssertionError(
                "no module other than the declaring one is available to change, so this row "
                "cannot measure a missed helper change"
            )
        print(f"# the objective identity covers: {names}" if identity is not None else
              "# the tree publishes no objective identity, so the helper below is the "
              "geometry and board model every placement term runs through")
        mutated = scratch / f"{helper.rsplit('.', 1)[-1]}.py"
        mutated.write_bytes(Path(sys.modules[helper].__file__).read_bytes() + b"\n# changed\n")
        sys.modules[helper].__file__ = str(mutated)
        print(f"# changed helper: {helper} ({mutated})")
        print(f"# the declaring module is untouched: "
              f"{module._module_digest() == captured_module_digest}")
        try:
            module.check_predeclaration(cited)
        except AssertionError as error:
            print(f"# the helper's change is reported: {error}")
            return
        raise AssertionError(
            f"the tree accepted a change to {helper} after the capture: the capture covers "
            "only the declaring module, so a helper's change moves every value the objective "
            "computes while check-predeclaration reports nothing"
        )


def r20_remote_main_durability():
    """The base check survives main moving past the recorded base.

    The reviewer's finding: the probe compared the observed remote main tip with a
    fixed commit, so the evidence file necessarily failed once any later commit
    reached main — this experiment's own merge included. This drives the target
    probe's ``check_remote_main`` with the Git plumbing stubbed to an observed main
    that is ahead of the base but contains it, which the fixed-tip comparison
    rejects and the ancestry check accepts. A remote main that does not contain
    the base must still be reported.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_remote_main"):
        raise SubjectAbsent(
            f"{target} has no check_remote_main: this row's subject is the base-refresh "
            "probe, and that tree carries none"
        )
    scratch = Path(tempfile.mkdtemp(prefix="exp003-remote-main-"))
    clone = scratch / "remote-main"
    base = module.BASE_COMMIT
    ahead, tree, head = "b" * 40, "c" * 40, "e" * 40
    print(f"# recorded base: {base}; observed remote main tip: {ahead} (ahead of it)")

    def drive(base_on_remote):
        def fake_git(cwd, *arguments):
            command = " ".join(arguments)
            where = Path(cwd)
            if command.startswith("ls-remote"):
                return 0, f"{ahead}\t{module.REMOTE_MAIN_REF}"
            if command.startswith("clone "):
                return 0, ""
            if where == clone:
                if command == "rev-parse HEAD":
                    return 0, ahead
                if command == "rev-parse HEAD^{tree}":
                    return 0, tree
                if command.startswith("merge-base --is-ancestor"):
                    return (0 if base_on_remote else 1), ""
            elif command == f"rev-parse {base}":
                return 0, base
            elif command == f"rev-parse {base}^{{tree}}":
                return 0, tree
            elif command == "rev-parse HEAD":
                return 0, head
            elif command.startswith("merge-base --is-ancestor"):
                return 0, ""
            raise AssertionError(f"unexpected git command: {command} (in {where})")

        module.REMOTE_MAIN_CLONE = clone
        module._git = fake_git

    drive(True)
    try:
        module.check_remote_main()
    except AssertionError as error:
        raise AssertionError(
            f"the tree rejected an observed remote main that contains the recorded base: "
            f"{error}"
        ) from error
    print("# the remote main ahead of the base is accepted and both tips are reported")

    drive(False)
    try:
        module.check_remote_main()
    except AssertionError as error:
        print(f"# a remote main that does not contain the base is reported: {error}")
        return
    raise AssertionError(
        "the tree accepted an observed remote main that does not contain the recorded base"
    )


def r21_publication_count_capture():
    """The publication record's counts are lengths of a captured run's own lists.

    The reviewer's finding: every count was checked against another value the same
    helpers derived, so mutating ``compared_paths_count`` and regenerating the
    state and counts lines with the shipped helpers still verified. This takes the
    tree's own retained record — which its own check accepts — changes that count
    and regenerates the derived lines with the tree's own ``state_line`` and
    ``counts_line``, and requires the record to be reported. A tree whose check has
    no captured run to compare the count against accepts it.
    """
    target, module = _target_probe()
    record_path, record = _target_record(target)
    if not hasattr(module, "check_publication_record"):
        raise SubjectAbsent(
            f"{target} has no check_publication_record: this row's subject is the captured "
            "run that check reads, and that tree records no publication snapshot"
        )
    module.check_publication_record(record_path)
    print("# the retained record passes the check")
    publication = record["publication"]
    publication["compared_paths_count"] = publication["compared_paths_count"] - 1
    listed = publication["repaired_paths_differing_from_this_worktree"]
    publication["state"] = module.state_line(
        publication["published_commit"], publication["compared_paths_count"], listed)
    publication["counts_line"] = module.counts_line(
        publication["compared_paths_count"], publication["observed_differing_paths"],
        publication["observed_uncommitted_paths"])
    tampered = Path(tempfile.mkdtemp(prefix="exp003-publication-")) / "result.json"
    tampered.write_text(json.dumps(record), encoding="utf-8")
    print(f"# compared_paths_count changed to {publication['compared_paths_count']} and the "
          f"state and counts lines regenerated with the tree's own helpers")
    try:
        module.check_publication_record(tampered)
    except AssertionError as error:
        print(f"# the regenerated counts are reported: {error}")
        return
    raise AssertionError(
        "the tree accepted a publication record whose count was regenerated without a "
        "matching captured run, so the count is checked against another derived value"
    )


def r22_base_commit_record():
    """The retained base-refresh snapshot is one run's captured commands and values.

    This check is **new capability**, so a pre-change tree has no counterpart
    method to fail: the row is a pin, not a failure-before. What the pre-change
    tree can show is the artifact the check is about — its retained
    ``base_commit`` object's own disagreement between the captured command output
    and the field beside it — which this row prints. When the tree does have the
    check, this row drives it instead: the retained record must pass, and a copy
    whose field disagrees with the captured output must be reported.
    """
    target, module = _target_probe()
    record_path, record = _target_record(target)
    base = record["base_commit"]
    if not hasattr(module, "check_base_commit_record"):
        commands = base.get("remote_main_refresh", {}).get("commands", [])
        captured = [entry.get("stdout", entry.get("output", "")) for entry in commands]
        head_outputs = [entry.get("stdout", entry.get("output", ""))
                        for entry in commands if "rev-parse HEAD" in entry.get("command", "")]
        print("# the tree has no base-commit check: the contract is new capability, so this "
              "row is a pin rather than a failure-before")
        print(f"# its retained base_commit.worktree_head is {base.get('worktree_head')!r}")
        print(f"# its captured `rev-parse HEAD` outputs are {head_outputs}")
        if base.get("worktree_head") not in head_outputs:
            print("# the retained object names one commit in its field and another in its "
                  "captured output: no single run produced it, which is the artifact this "
                  "row's check is about")
        else:
            print("# the retained object's field is the commit its captured output names, so "
                  "this tree has no mixed snapshot to show")
        print("# the substitute evidence for this row is executed in this worktree: "
              "evidence.py base-commit-record rejects the pre-change record and a copy whose "
              "field disagrees with its captured output (see notes.md)")
        return
    module.check_base_commit_record(record_path)
    print("# the retained snapshot passes the check")
    tampered = json.loads(json.dumps(record))
    tampered["base_commit"]["worktree_head"] = tampered["base_commit"]["commit"]
    path = Path(tempfile.mkdtemp(prefix="exp003-base-")) / "result.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    try:
        module.check_base_commit_record(path)
    except AssertionError as error:
        print(f"# a field that disagrees with its captured output is reported: {error}")
        return
    raise AssertionError(
        "the tree accepted a base_commit object whose worktree_head field disagrees with the "
        "captured command output it came from"
    )


def r23_publication_record_derivation():
    """A captured entry's decisions, and its coverage, follow from the captured states.

    Two findings of the same shape. The first: the retained check validated an
    entry's ``outcome``, ``published``, ``worktree`` and ``differs`` one at a time,
    so a differing file whose outcome was rewritten to ``same`` (with its two sides
    still files and its ``differs`` flag still true) passed — each field legal, the
    combination one no run produced. The second: the captured ``uncommitted_paths``
    list was compared only by length, so swapping a differing path out of it for an
    unchanged one preserved every count while certifying a snapshot
    ``check_publication`` rejects (a differing path the worktree does not hold
    uncommitted). This takes the tree's own retained record — which its own check
    accepts — and requires each mutation, with the capture line regenerated by the
    tree's own helper, to be reported. A tree whose check reads neither the
    derivation nor the coverage accepts them.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_publication_record"):
        raise SubjectAbsent(
            f"{target} has no check_publication_record: this row's subject is the retained "
            "publication snapshot, and that tree records none"
        )
    record_path, record = _target_record(target)
    module.check_publication_record(record_path)
    print("# the retained record passes the check")
    capture = record["publication"]["capture"]
    entry = next((item for item in capture["compared_paths"] if item["differs"]), None)
    if entry is None or entry["published"] != "file" or entry["worktree"] != "file":
        raise AssertionError(
            "the retained capture holds no differing file pair to rewrite, so this row "
            "cannot measure the isolation of the per-path fields"
        )
    unchanged = next(item["path"] for item in capture["compared_paths"]
                     if not item["differs"] and item["outcome"] == "same")
    print(f"# the differing file pair: {entry['path']!r} "
          f"({entry['published']} vs {entry['worktree']}, differs {entry['differs']})")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-publication-entry-"))

    def reported(name, mutate):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        path = scratch / "result.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        try:
            module.check_publication_record(path)
        except AssertionError as error:
            print(f"# {name} is reported: {error}")
            return True
        return False

    def rewritten_outcome(tampered):
        target_entry = next(item for item in tampered["publication"]["capture"]["compared_paths"]
                            if item["path"] == entry["path"])
        target_entry["outcome"] = "same"
        capture_line(tampered)

    def moved_uncommitted(tampered):
        tampered_capture = tampered["publication"]["capture"]
        tampered_capture["uncommitted_paths"] = [
            unchanged if path == entry["path"] else path
            for path in tampered_capture["uncommitted_paths"]]
        capture_line(tampered)

    def duplicated_path(tampered):
        # A declared repaired path's entry is replaced by a copy of an unchanged
        # one, so the capture compares a path twice and omits the declared path
        # while every count, including the differing and uncommitted ones, is
        # unchanged.
        tampered_capture = tampered["publication"]["capture"]
        entries = tampered_capture["compared_paths"]
        # The reviewer's case: a declared path whose entry is *unchanged*, so the
        # differing list, the uncommitted list and every count stay as they were.
        declared = next(
            (item for item in entries
             if item["path"] in module.REPAIRED_PATHS and not item["differs"]),
            next(item for item in entries
                 if item["path"] in module.REPAIRED_PATHS and item["differs"]))
        donor = next(item for item in entries
                     if item["path"] != declared["path"]
                     and item["differs"] == declared["differs"])
        declared.update(donor)
        capture_line(tampered)

    def capture_line(tampered):
        tampered["publication"]["publication_capture_line"] = \
            module.publication_capture_line(tampered["publication"]["capture"])

    print("# its outcome rewritten to 'same' with both sides still files and differs true")
    accepted = []
    if not reported("the outcome rewrite", rewritten_outcome):
        accepted.append("an entry whose outcome says 'same' while its recorded sides are two "
                        "differing files")
    if not reported("the uncommitted swap", moved_uncommitted):
        accepted.append("a capture whose differing path is not in its uncommitted list")
    print("# a declared repaired path replaced by a duplicate of an unchanged one")
    if not reported("the duplicated path", duplicated_path):
        accepted.append("a capture that compares a path twice and omits a declared repaired path")
    if accepted:
        raise AssertionError(
            "the tree accepted: " + "; ".join(accepted) + " — so a snapshot no run produced "
            "certifies"
        )


def r24_base_commit_worktree_ancestry():
    """The base snapshot's capture backs its ancestry claims, both of them.

    Two findings of the same shape. The first: ``check_base_commit_record``
    validated the remote-main ancestry role but not the captured
    ``merge-base --is-ancestor BASE HEAD`` command that ``base_state_line`` claims,
    so a snapshot could carry the sentence with that command's exit status changed
    to 1 and still certify. The second: the object's
    ``base_is_ancestor_of_remote_main`` flag was compared with its capture copy
    rather than derived from the captured command's exit status, so a snapshot
    whose two copies both say ``false`` while the command exited 0 certifies —
    a state ``check_remote_main`` (which derives the flag as ``status == 0``)
    cannot produce. This takes the tree's own retained record — which its own
    check accepts — applies each mutation with the capture line regenerated by the
    tree's own helper, and requires the record to be reported.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_base_commit_record"):
        raise SubjectAbsent(
            f"{target} has no check_base_commit_record: this row's subject is the retained "
            "base-refresh snapshot, and that tree carries none"
        )
    record_path, record = _target_record(target)
    module.check_base_commit_record(record_path)
    print("# the retained snapshot passes the check")
    base = record["base_commit"]
    role = getattr(module, "BASE_WORKTREE_ANCESTRY_ROLE",
                   "the worktree HEAD descends from the recorded base")
    ancestry_field = getattr(module, "BASE_ANCESTRY_FIELD",
                             "base_is_ancestor_of_remote_main")
    entries = [entry for entry in base["capture"]["commands"] if entry["role"] == role]
    if len(entries) != 1:
        raise AssertionError(
            f"the retained capture holds {len(entries)} commands for the role {role!r}, so "
            "this row cannot measure the check's treatment of it"
        )
    scratch = Path(tempfile.mkdtemp(prefix="exp003-base-ancestry-"))

    def reported(name, mutate):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        tampered["base_commit"]["base_capture_line"] = \
            module.base_capture_line(tampered["base_commit"]["capture"])
        path = scratch / "result.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        try:
            module.check_base_commit_record(path)
        except AssertionError as error:
            print(f"# {name} is reported: {error}")
            return True
        return False

    def failed_worktree_ancestry(tampered):
        tampered_base = tampered["base_commit"]
        target_entry = next(entry for entry in tampered_base["capture"]["commands"]
                            if entry["role"] == role)
        target_entry["exit"] = 1

    def contradictory_ancestry_flag(tampered):
        tampered_base = tampered["base_commit"]
        tampered_base[ancestry_field] = False
        tampered_base["capture"][ancestry_field] = False

    def mismatched_base_tree(tampered):
        # The observed tip is the recorded base, so one commit's tree is claimed
        # twice: the field, its capture copy and the captured `rev-parse` output
        # all move together to a different tree, which the producer rejects.
        tampered_base = tampered["base_commit"]
        other = "0" * 40
        tampered_base["remote_main_tree"] = other
        tampered_base["capture"]["remote_main_tree"] = other
        for entry in tampered_base["capture"]["commands"]:
            if entry["role"] == "refreshed remote main tree from the clone":
                entry["output"] = other

    print(f"# the {role!r} command's exit changed to 1")
    accepted = []
    if not reported("the failed worktree-ancestry command", failed_worktree_ancestry):
        accepted.append("a worktree-ancestry command that failed")
    print(f"# both copies of {ancestry_field!r} changed to False while the command exited 0")
    if not reported("the contradictory ancestry flag", contradictory_ancestry_flag):
        accepted.append("an ancestry flag that contradicts the captured command's exit status")
    print("# the recorded base named as the observed tip with a different tree")
    if not reported("the mismatched base tree", mismatched_base_tree):
        accepted.append("a snapshot that gives the recorded base a different tree")
    if accepted:
        raise AssertionError(
            "the tree accepted: " + "; ".join(accepted) + " — so the state line's claim is "
            "not established by the capture the record retains"
        )


def r25_live_objective_snapshot():
    """The live record's objective is the loaded implementation's, across restarts.

    The reviewer's finding: ``_objective_section(self.config)`` read the covered
    source files when the game ended while the versions were captured at BEGIN, so
    a module edited mid-session was recorded as the code that chose the inputs; and
    reading the files again at a restart's BEGIN attributed the restarted game to
    source bytes the interpreter never loaded. This drives two Tetris games in one
    session, changes a covered module's file after the first BEGIN, plays each to
    the end, and requires **both** saved records to carry the identity the session
    started with. A tree that reads the files at END (or again at BEGIN) records
    the post-edit identity and is reported.
    """
    if "tetris" not in AGENT_NAMES:
        raise SubjectAbsent(
            "the tree's agent registry has no tetris agent, so it cannot play the live game "
            "this row drives"
        )
    from block_stack_ai.engine import create_game
    from block_stack_ai.live import LiveSession
    from block_stack_ai.runner import SuiteConfig, _objective_section

    game = {"ruleset": "classic_ntsc_extended", "mode": "endless", "start_level": 18,
            "height": 0}
    limit = 60
    with tempfile.TemporaryDirectory() as directory:
        config = SuiteConfig(game, limit, (2,), ("tetris",))
        tetris_module = sys.modules["block_stack_ai.tetris"]
        original_file = tetris_module.__file__
        original_bytes = Path(original_file).read_bytes()
        session = LiveSession(config, Path(directory) / "runs")
        try:
            for game_number in range(1, 3):
                with create_game(**game, seed=2) as desktop:
                    snapshot = desktop.save_state()
                    session.receive("BEGIN", snapshot)
                    if game_number == 1:
                        # The identity of the implementation that was loaded: the
                        # session's own snapshot where it has one, or the tree's own
                        # reader taken before the edit.
                        begin = getattr(session, "objective", None)
                        if begin is None:
                            begin = _objective_section(config)
                        print("# the session's objective identity: "
                              f"{begin['objective']['sources']['block_stack_ai.tetris']}")
                        mutated = Path(directory) / "tetris.py"
                        mutated.write_bytes(original_bytes + b"\n# changed\n")
                        tetris_module.__file__ = str(mutated)
                    while not desktop.state.terminal and desktop.state.frame < limit:
                        mask = session.receive("STATE", snapshot)
                        desktop.step(mask)
                        snapshot = desktop.save_state()
                    session.receive("END", snapshot)
        finally:
            tetris_module.__file__ = original_file
            session.close()
        records = sorted((Path(directory) / "runs").glob("*/run.json"))
        assert len(records) == 2, len(records)
        for number, path in enumerate(records, start=1):
            record = json.loads(path.read_text(encoding="utf-8"))
            digest = record["objective"]["sources"]["block_stack_ai.tetris"]
            print(f"# game {number}'s record objective identity: {digest}")
            assert record["objective"] == begin["objective"], (
                f"game {number}'s record carries the identity read after the edit, not the "
                "identity of the loaded implementation the session started with"
            )


def r26_predeclaration_record_identity():
    """The check compares the capture with the identity the run itself wrote.

    The reviewer's finding: the capture's helper digests were transcribed from the
    evaluation record's own ``objective.sources`` after the run while the capture
    kept an earlier ``captured_at``, and the check skipped the comparison whenever
    the cited record carried no identity. This cites a record that carries none and
    requires the check to report it, so a post-run transcription cannot leave the
    run's identity unexamined. A tree whose check treats the identity as optional
    accepts the record.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_predeclaration"):
        raise SubjectAbsent(
            f"{target} has no check_predeclaration: this row's subject is the declared "
            "objective's capture, and that tree does not capture one"
        )
    captured = json.loads(module.PREDECLARATION.read_text(encoding="utf-8"))
    if "sources" not in captured:
        raise SubjectAbsent(
            "the tree's capture records only the declaring module's digest, so it cannot "
            "be compared with a run's identity at all"
        )
    with tempfile.TemporaryDirectory(prefix="exp003-predeclaration-record-") as directory:
        record_path = Path(directory) / "run.json"
        record_path.write_text(
            json.dumps({"created_at": "2099-01-01T00:00:00+00:00"}), encoding="utf-8")
        print("# a cited record that carries no objective identity")
        try:
            module.check_predeclaration(record_path)
        except AssertionError as error:
            print(f"# the record without an identity is reported: {error}")
            return
        raise AssertionError(
            "the tree accepted a cited record that carries no objective identity: the "
            "capture is never compared with the identity the measurement itself wrote, so a "
            "post-run transcription under an earlier timestamp cannot be told from a "
            "genuine pre-run capture"
        )


def r27_predeclaration_weights():
    """The check compares the capture's declared weights with the code and the run.

    The reviewer's finding: ``check_predeclaration`` read only the capture's source
    digests and timestamps, never its ``objective`` mapping, so a capture whose
    declared weights were edited — ``tetrises`` raised from ``8.0`` to ``80.0`` —
    still certified a run scored by the published weights. This points the target
    check at an edited copy of the tree's own capture and an otherwise valid cited
    record, and requires the record to be reported. A tree whose check never reads
    the mapping accepts it.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_predeclaration"):
        raise SubjectAbsent(
            f"{target} has no check_predeclaration: this row's subject is the declared "
            "objective's capture, and that tree does not capture one"
        )
    captured = json.loads(module.PREDECLARATION.read_text(encoding="utf-8"))
    if "sources" not in captured or not isinstance(captured.get("objective"), dict):
        raise SubjectAbsent(
            "the tree's capture records no objective mapping beside its identity, so this row "
            "cannot measure the weight comparison"
        )
    scratch = Path(tempfile.mkdtemp(prefix="exp003-predeclaration-weights-"))
    declared = json.loads(json.dumps(captured))
    original = declared["objective"].get("tetrises")
    declared["objective"]["tetrises"] = 80.0
    capture_path = scratch / "predeclared_objective.json"
    capture_path.write_text(json.dumps(declared), encoding="utf-8")
    module.PREDECLARATION = capture_path
    record_path = scratch / "run.json"
    record_path.write_text(json.dumps({
        "created_at": "2099-01-01T00:00:00+00:00",
        "objective": {"sources": captured["sources"], "weights": captured["objective"]},
    }), encoding="utf-8")
    print(f"# the capture's declared tetrises weight changed from {original} to 80.0; the "
          f"cited record carries the published mapping")
    try:
        module.check_predeclaration(record_path)
    except AssertionError as error:
        print(f"# the edited declared weights are reported: {error}")
        return
    raise AssertionError(
        "the tree accepted a capture whose declared weights are not the ones the objective's "
        "code publishes, so the declaration and the measurement can disagree while every "
        "digest matches"
    )


def r28_objective_wrapper_identity():
    """The recorded identity covers the agent wrapper that drives the objective.

    The reviewer's finding: the identity was walked outward from the module that
    declares the objective, and the wrapper that hands the objective every state
    parameter it reads and executes the placement it returns imports that module,
    so the dependency runs the other way and no such walk can reach it. A wrapper
    change — a state parameter altered, or the objective bypassed — then left the
    recorded identity and the replayed choices both unchanged, so a record whose
    placements no longer came from the recorded objective was certified. This runs
    the experiment's suite with the tree's own writer, changes
    ``block_stack_ai.agents`` through a mutated copy of its file — the loaded code
    the replay runs is untouched, so the recorded seeds keep exactly the actions
    they recorded — and requires the record to be reported. A tree whose identity
    stops at the objective's own imports accepts it and reports nothing.
    """
    path, factory = _run_experiment_suite("objective_wrapper_identity")
    record = json.loads(path.read_text(encoding="utf-8"))
    objective = record.get("objective")
    if objective is None:
        raise AssertionError(
            "the tree writes no declared-objective section for a suite that uses the Tetris "
            f"agent, so no identity could be recorded: record keys are {sorted(record)}"
        )
    identity = objective.get("sources")
    if identity is None:
        raise AssertionError(
            "the tree records no objective source identity, so the wrapper's coverage cannot "
            f"be measured: the objective section's keys are {sorted(objective)}"
        )
    print(f"# record format_version: {record.get('format_version')}")
    print(f"# recorded identity: {identity}")
    wrapper = "block_stack_ai.agents"
    print(f"# the identity covers the agent wrapper {wrapper}: {wrapper in identity}")
    wrapper_module = sys.modules[wrapper]
    original_file = wrapper_module.__file__
    original = Path(original_file).read_text(encoding="utf-8")
    call = ("        return tetris_choice(\n"
            "            grid,\n"
            "            state.current_piece,\n"
            "            state.next_piece,\n")
    cases = (
        ("a state parameter changed",
         (call + "            level=state.level,\n",
          call + "            level=state.level + 1,\n")),
        # The wrapper still imports the objective and no longer calls it, so the
        # placements come from the frozen lookahead value instead.
        ("the objective bypassed",
         (call, "        return lookahead_choice(\n"
                "            grid,\n"
                "            state.current_piece,\n"
                "            state.next_piece,\n")),
    )
    print(f"# the record verifies before the wrapper changes: {runner.verify_run(path, factory)}")
    certified = []
    try:
        for label, (before, after) in cases:
            changed = original.replace(before, after)
            if changed == original:
                raise AssertionError(
                    f"the tree's wrapper does not contain the tetris choice this probe "
                    f"changes for '{label}': {wrapper_module.__file__}"
                )
            mutated = Path(tempfile.mkdtemp(prefix="exp003-wrapper-")) / "agents.py"
            mutated.write_text(changed, encoding="utf-8")
            # Only the file the identity hashes is pointed at the copy; the module
            # the replay runs stays the loaded one, so the recorded seeds keep the
            # actions they recorded and the identity is the only thing that moved.
            wrapper_module.__file__ = str(mutated)
            print(f"# changed wrapper ({label}): {mutated}; the loaded code is untouched, so "
                  f"the replayed inputs are the recorded ones")
            try:
                warnings = runner.verify_run(path, factory)
            except runner.VerificationError as error:
                print(f"# the wrapper change ({label}) is reported: {error}")
                if wrapper not in str(error):
                    raise AssertionError(
                        "the tree rejected the record, but not for the wrapper's identity: "
                        f"{error}"
                    ) from error
            else:
                print(f"# the wrapper change ({label}) is certified: verify_run returned "
                      f"{warnings}")
                certified.append(label)
    finally:
        wrapper_module.__file__ = original_file
    if certified:
        raise AssertionError(
            f"the tree certified a record whose wrapper changed ({', '.join(certified)}) while "
            "its recorded seeds kept exactly their recorded actions, so the record verifies "
            f"under code that did not produce it: its recorded identity covers "
            f"{sorted(identity)}, which does not include the agent wrapper {wrapper} that "
            "supplies every state parameter the objective reads and executes the placement it "
            "returns"
        )
    print(f"# the unchanged wrapper verifies again: {runner.verify_run(path, factory)}")


def r29_summary_histogram_derivation():
    """A summary re-derives only the sections the record's episodes carry.

    Experiment 002's own replay probe compares the summary it re-derives from a
    legacy record's episodes with the recorded summary, so a re-derived summary
    that adds a histogram the episodes never recorded — all-zero totals for clear
    sizes no run measured — rejects a record that experiment still publishes,
    while ``verify_run`` accepts it because the verifier excludes that section
    from the compared base and reports the absence with its own presence rule.
    This writes a suite record, strips the histogram from every episode and every
    summary (the shape the base commit's writer emitted) and requires the
    re-derived summary to equal the recorded one. A tree whose ``_summarize``
    always adds the section reports the mismatch.
    """
    path, _ = _suite_record(HISTOGRAM_SUITE)
    record = json.loads(path.read_text(encoding="utf-8"))
    carried = all("clear_sizes" in episode for episode in record["episodes"])
    legacy = json.loads(json.dumps(record))
    for episode in legacy["episodes"]:
        episode.pop("clear_sizes", None)
    for summary in legacy["summary"].values():
        summary.pop("clear_sizes", None)
    print(f"# the tree's own episodes carry clear_sizes: {carried}")
    print(f"# the legacy shape: {len(legacy['episodes'])} episodes and "
          f"{len(legacy['summary'])} summaries, none carrying clear_sizes")
    replayed = runner._summarize(legacy["episodes"])
    print(f"# re-derived summary: {replayed}")
    print(f"# recorded summary  : {legacy['summary']}")
    if replayed != legacy["summary"]:
        added = sorted((name, sorted(set(entry) - set(legacy["summary"][name])))
                       for name, entry in replayed.items()
                       if set(entry) != set(legacy["summary"][name]))
        raise AssertionError(
            "the tree's summary adds a section the record's episodes never carried, so "
            "Experiment 002's own replay probe — which compares the summary it "
            f"re-derives with the recorded one — rejects a record 002 still publishes: "
            f"{added}"
        )
    print("# the re-derived summary equals the recorded one")
    if not carried:
        print("# a tree that records no histogram at all writes this shape anyway, so the "
              "contract already held there")


# The counterexample program the 003 tree carries beside this file. It is a
# program rather than a function because the defect is in an ordering: the
# objective's modules are imported, one of their files is edited, and only then is
# the writer imported. That ordering exists only in a fresh process, and the
# process must load the tree under test's own package, so the row spawns it with
# ``PYTHONPATH`` pointing at a copy of that package.
COUNTEREXAMPLE_PROGRAM = Path(__file__).resolve().parent / "loaded_identity_program.py"


def _run_counterexample(mode: str, root: Path) -> dict:
    """Run the counterexample program against a fresh copy of this tree's package.

    ``mode`` is ``clean`` (the control: nothing is edited) or ``edit`` (the
    counterexample). Each mode gets its own copy of the package and its own
    working directory, so the edit cannot reach the control's run and neither can
    reach the tree under test.
    """
    package = Path(block_stack_ai.__file__).resolve().parent
    source_root = root / f"{mode}-src"
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    run_root = root / mode
    run_root.mkdir(parents=True)
    completed = subprocess.run(
        [sys.executable, str(COUNTEREXAMPLE_PROGRAM), mode, str(run_root)],
        cwd=run_root, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(source_root)},
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"the counterexample program could not run against this tree "
            f"(exit {completed.returncode}): {completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


def _reads_loaded_identity() -> bool:
    """Whether this tree carries a writer's view of the loaded identity.

    Two shapes of it have existed: the import-time snapshot
    (``_LOADED_OBJECTIVE_SOURCES``) the earlier rounds bound, and the reader this
    round's repair calls when a run is built (``_loaded_objective_sources``,
    which reads the loader's record at that moment). The rows that measure the
    loaded-vs-tree values ask for either, so removing the snapshot cannot silence
    them: a row that reported "no subject" here would exit 0 without running its
    counterexample.
    """
    return (hasattr(runner, "_LOADED_OBJECTIVE_SOURCES")
            or hasattr(runner, "_loaded_objective_sources"))


def r30_loaded_identity():
    """A record's identity is the code the loader read, not the file read later.

    The reviewer's finding: ``_objective_sources`` took each covered module's
    digest by reading ``module.__file__``, and the writer bound its snapshot when
    ``runner`` was imported. A path is not code — a process that imports the
    objective's modules, has one of their files edited, and only then imports the
    writer recorded the edited bytes while ``sys.modules`` still executed the
    loaded ones, and verification read the same edited file, so the record was
    certified under an implementation that did not choose its inputs. This runs
    the counterexample program against a copy of the tree under test's package:
    the file is edited between the modules' import and the writer's, and the
    contract is that the writer records the loaded bytes, the verifier's view
    follows the file, and the mismatch is *reported* rather than certified. The
    ``clean`` run is the control: with the file untouched all five values agree
    and the record verifies, so the report in the ``edit`` run is the edit.
    """
    if "tetris" not in AGENT_NAMES or not _reads_loaded_identity():
        raise SubjectAbsent(
            "this tree has no Tetris agent, so it records no objective identity whose "
            "loaded-vs-tree value could be measured"
        )
    with tempfile.TemporaryDirectory(prefix="exp003-loaded-identity-") as directory:
        root = Path(directory)
        clean = _run_counterexample("clean", root)
        print(f"# clean run, no edit: loaded {clean['loaded'][:16]}, tree {clean['tree'][:16]}, "
              f"record {clean['record'][:16]}, verified {clean['outcome']['verified']}")
        assert clean["outcome"]["verified"] is True, (
            "a record written from an unchanged tree must verify: this tree reports "
            f"{clean['outcome'].get('error')}"
        )
        assert clean["loaded"] == clean["before"] == clean["on_disk"] == clean["record"], (
            "with the file untouched the loaded identity, the file and the recorded identity "
            f"must be one digest: loaded {clean['loaded']}, file {clean['on_disk']}, "
            f"recorded {clean['record']}"
        )
        assert clean["tree"] == clean["on_disk"], (
            "the verifier's view of the tree must be the file on the tree: tree "
            f"{clean['tree']}, file {clean['on_disk']}"
        )
        edited = _run_counterexample("edit", root)
        print(f"# edit run: file before {edited['before'][:16]}, file after {edited['on_disk'][:16]}, "
              f"loaded {edited['loaded'][:16]}, tree {edited['tree'][:16]}, "
              f"record {edited['record'][:16]}, verified {edited['outcome']['verified']}")
        assert edited["before"] != edited["on_disk"], (
            "the counterexample's edit did not change the covered file, so the run measured "
            "nothing"
        )
        assert edited["loaded"] == edited["record"] == edited["before"], (
            "the writer recorded the file as it stands after the edit rather than the code the "
            "interpreter loaded: loaded identity "
            f"{edited['loaded']} vs file before the edit {edited['before']} and after "
            f"{edited['on_disk']}, recorded {edited['record']}"
        )
        assert edited["tree"] == edited["on_disk"], (
            "the verifier's view of the tree must follow the edited file: tree "
            f"{edited['tree']}, file {edited['on_disk']}"
        )
        if edited["outcome"]["verified"]:
            raise AssertionError(
                "the tree certified a record whose recorded identity is the code that was "
                "loaded while the file it names on the tree holds different bytes: the "
                "record's implementation did not choose its inputs, and the provenance must "
                "be reported instead"
            )
        if "block_stack_ai.tetris" not in str(edited["outcome"].get("error")):
            raise AssertionError(
                "the tree rejected the record, but not for the covered module the edit moved: "
                f"{edited['outcome'].get('error')}"
            )
        print("# the recorded identity is the loaded code; the edit is reported, not certified")


# The stale-cache program the 003 tree carries beside this file, and the same-length
# edit the row makes: one character changes, so the file's size is unchanged and a
# compiled cache built from the old text stays valid to Python's timestamp check.
STALE_CACHE_PROGRAM = Path(__file__).resolve().parent / "stale_cache_program.py"
STALE_CACHE_FROM = "WELL_DEPTH_CAP = 4"
STALE_CACHE_TO = "WELL_DEPTH_CAP = 5"


def _stale_cache_tree(root: Path) -> Path:
    """A compiled copy of this tree's package whose covered module was edited in place.

    ``compileall`` writes the cache the interpreter's own loader would use; the
    edit keeps the file's size and restores its mtime, so Python's timestamp
    validation still accepts that cache while the source beside it has changed.
    """
    package = Path(block_stack_ai.__file__).resolve().parent
    source_root = root / "src"
    shutil.copytree(package, source_root / package.name,
                    ignore=shutil.ignore_patterns("__pycache__"))
    compiled = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(source_root / package.name)],
        capture_output=True, text=True)
    if compiled.returncode != 0:
        raise AssertionError(f"compileall failed on this tree: {compiled.stderr.strip()}")
    source = source_root / package.name / "tetris.py"
    before = source.stat()
    text = source.read_text(encoding="utf-8")
    edited = text.replace(STALE_CACHE_FROM, STALE_CACHE_TO)
    if edited == text or len(edited) != len(text):
        raise AssertionError(
            f"the tree's tetris.py does not carry '{STALE_CACHE_FROM}', or the edit is not "
            f"the same length: {source}")
    source.write_text(edited, encoding="utf-8")
    os.utime(source, (before.st_atime, before.st_mtime))
    after = source.stat()
    if (after.st_size, int(after.st_mtime)) != (before.st_size, int(before.st_mtime)):
        raise AssertionError("the edit changed the file's size or mtime, so the cache is dead")
    return source_root


def r31_stale_cache():
    """The recorded identity is the code that ran, not source beside a bytecode cache.

    The reviewer's finding: the recorder digested one read of each covered module's
    source while delegating execution to the loader that read it, and that loader
    may execute a ``__pycache__`` entry instead. Python accepts such an entry while
    the source it was built from still matches by integer-second mtime and size, so
    a same-length edit inside that second leaves a cache that is executed while a
    separate read of the file returns the edited text: the record names source the
    process did not run, and verification — which reads the same file — certifies
    it. This compiles a copy of the tree under test, edits ``tetris.py`` to the same
    size with its mtime restored, and requires the constant the loaded code
    declares, the constant the file declares and the recorded digest to be one and
    the same source.
    """
    if "tetris" not in AGENT_NAMES or not _reads_loaded_identity():
        raise SubjectAbsent(
            "this tree has no Tetris agent, so it records no objective identity whose "
            "loaded-vs-tree value could be measured")
    with tempfile.TemporaryDirectory(prefix="exp003-stale-cache-") as directory:
        root = Path(directory)
        source_root = _stale_cache_tree(root)
        completed = subprocess.run(
            [sys.executable, str(STALE_CACHE_PROGRAM)], cwd=root, capture_output=True,
            text=True, env={**os.environ, "PYTHONPATH": str(source_root)})
        if completed.returncode != 0:
            raise AssertionError(
                f"the stale-cache program could not run against this tree "
                f"(exit {completed.returncode}): {completed.stderr.strip()}")
        measured = json.loads(completed.stdout)
        print(f"# stale cache: the loaded code declares {measured['executed']}, the file "
              f"declares {measured['source']}, the writer recorded "
              f"{measured['recorded'][:16]}, the file is {measured['file'][:16]}")
        assert measured["source"] == 5, measured
        if measured["executed"] != measured["source"]:
            raise AssertionError(
                "the identity names source the interpreter did not run: the loaded code "
                f"declares {measured['executed']} while the file declares "
                f"{measured['source']}, and the recorded digest is the file's own "
                f"({measured['recorded'][:16]}), so a verifier reading that file certifies "
                "a record that does not name what ran")
        if not measured["agrees"] or measured["recorded"] != measured["file"]:
            raise AssertionError(
                "the recorded identity is not the source that ran: recorded "
                f"{measured['recorded']}, file {measured['file']}")
        print("# the code that ran, the file on the tree and the recorded identity are one source")


# The instant-shaped tokens a retained sentence may quote: the same shape the
# probe's own derivation restricts a record block to.
TIMESTAMP_SHAPE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)")


def _accepts(module, path: Path, check: str) -> tuple[bool, str]:
    """Whether the tree's ``check`` accepts a record, and the message if it does not."""
    try:
        getattr(module, check)(path)
    except AssertionError as error:
        return False, str(error)
    return True, ""


def r32_publication_tree_derivation():
    """The published commit/tree pairing is derived from the repository's objects.

    The reviewer's finding: ``check_publication_record`` validated the recorded
    ``published_tree`` only against the copy of it inside the capture, so setting
    both to ``000…`` and regenerating the capture line with the shipped helper
    certified — as one run — a commit/tree pairing no publication probe could have
    observed, because the captured commit's immutable tree is not that value. The
    tree's own retained record is taken here, its Git reader is stubbed so the
    repository answers the tree of the commit the record names, and the zeroed
    pairing is required to be reported. A tree whose check compares the field with
    its own copy accepts it.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_publication_record"):
        raise SubjectAbsent(
            f"{target} has no check_publication_record: this row's subject is the retained "
            "publication snapshot, and that tree records none"
        )
    record_path, record = _target_record(target)
    publication = record["publication"]
    published = publication["published_commit"]
    # The tree the repository itself gives that commit, read here rather than taken
    # from the record; the Git reader is then stubbed to answer with it, so the
    # check can be driven offline while the answer is still the repository's own.
    status, output = module._git(module.PROJECT_ROOT, "rev-parse", f"{published}^{{tree}}")
    tree = (output.splitlines()[-1] if status == 0 and output.splitlines()
            else publication["capture"]["published_tree"])

    def fake_git(cwd, *arguments):
        command = " ".join(arguments)
        if command == f"rev-parse {published}^{{tree}}":
            return 0, tree
        if command == "rev-parse HEAD":
            return 0, published
        raise AssertionError(f"unexpected git command: {command} (in {cwd})")

    module._git = fake_git
    module.check_publication_record(record_path)
    print(f"# the retained record passes the check; the repository resolves {published}^{{tree}} "
          f"to {tree}")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-publication-tree-"))
    tampered = json.loads(json.dumps(record))
    zeros = "0" * 40
    tampered["publication"]["published_tree"] = zeros
    tampered["publication"]["capture"]["published_tree"] = zeros
    tampered["publication"]["publication_capture_line"] = \
        module.publication_capture_line(tampered["publication"]["capture"])
    path = scratch / "result.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    print(f"# both copies of published_tree changed to {zeros} and the capture line "
          f"regenerated with the tree's own helper")
    accepted, message = _accepts(module, path, "check_publication_record")
    if accepted:
        raise AssertionError(
            "the tree accepted a publication record whose published_tree and its capture "
            "copy are both 000…, a commit/tree pairing no publication probe could have "
            "observed — the captured commit's immutable tree is the real one — because the "
            "field is checked only against its own copy"
        )
    print(f"# the zeroed pairing is reported: {message}")


def _stale_timestamp(block: dict) -> str | None:
    """A timestamp the block quotes that is neither of the two it carries."""
    quoted = {block.get("captured_at"), block.get("cited_record_created_at")}
    for _, text in _block_strings(block):
        for token in TIMESTAMP_SHAPE.findall(text):
            if token not in quoted:
                return token
    return None


def _block_strings(value, where="predeclared_objective"):
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _block_strings(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _block_strings(item, f"{where}[{index}]")


def r33_predeclaration_created_at():
    """The retained order sentence is derived from the cited record's timestamp.

    The reviewer's finding: the predeclaration block carries the cited record's
    ``created_at`` in ``cited_record_created_at`` while the sentence beside it
    still quoted an earlier evaluation's timestamp of the same round, so the block
    described two measurements. This takes the tree's own retained record, requires
    its check to report a sentence rewritten to quote a different instant, and — on
    a tree whose checks read none of this — prints the disagreement the tree's own
    record carries: it is the counterexample, executed on that tree.
    """
    target, module = _target_probe()
    record_path, record = _target_record(target)
    block = record["predeclared_objective"]
    stale = _stale_timestamp(block)
    print(f"# the retained block's cited_record_created_at is "
          f"{block.get('cited_record_created_at')!r}")
    if not hasattr(module, "check_predeclaration_record"):
        accepted, _ = _accepts(module, record_path, "check_publication_record")
        print(f"# the tree has no check_predeclaration_record; its publication check "
              f"accepts the record: {accepted}")
        print(f"# the sentence beside it quotes {stale!r}")
        raise AssertionError(
            "the tree accepts a predeclared_objective block whose capture_order quotes "
            f"{stale!r} while the cited record's own created_at beside it is "
            f"{block.get('cited_record_created_at')!r}: nothing in that tree reads the "
            "sentence, so the block may describe two measurements"
        )
    module.check_predeclaration_record(record_path)
    print("# the retained block passes the check")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-predeclaration-created-at-"))
    path = scratch / "result.json"
    rejected: list[str] = []
    for label, mutate in (
        ("the sentence rewritten to quote a different instant",
         lambda tampered: tampered["predeclared_objective"].__setitem__(
             "capture_order", TIMESTAMP_SHAPE.sub(
                 "2001-01-01T00:00:00.000000+00:00",
                 tampered["predeclared_objective"]["capture_order"]))),
        ("the cited timestamp changed beside its own sentence",
         lambda tampered: tampered["predeclared_objective"].__setitem__(
             "cited_record_created_at", "2001-01-01T00:00:00.000000+00:00")),
    ):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        path.write_text(json.dumps(tampered), encoding="utf-8")
        accepted, message = _accepts(module, path, "check_predeclaration_record")
        if accepted:
            raise AssertionError(
                f"the tree accepted the retained block with {label}, so the sentence and "
                "the value beside it are not required to be one measurement"
            )
        print(f"# {label} is reported: {message}")
        rejected.append(label)
    assert rejected


def r34_publication_paths_prose():
    """The comparison-set prose is derived from the captured run's per-path states.

    The reviewer's finding: the record's prose claimed a number of paths in the
    published tree that the captured run's own per-path evidence contradicts — 46
    against the 48 entries whose published state is a file — because the sentence
    was a hand-maintained literal beside the capture. This takes the tree's own
    retained record, requires its check to report a prose count the capture does
    not support, and requires the capture stripped of a published file to be
    reported too. A tree whose check never reads the sentence accepts both.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_publication_record"):
        raise SubjectAbsent(
            f"{target} has no check_publication_record: this row's subject is the retained "
            "publication snapshot, and that tree records none"
        )
    record_path, record = _target_record(target)
    capture = record["publication"]["capture"]
    published_files = sum(1 for entry in capture["compared_paths"]
                          if entry["published"] == "file")
    print(f"# the retained capture: {len(capture['compared_paths'])} compared paths, "
          f"{published_files} of them files in the published tree")
    print(f"# the retained prose: {record['publication']['compared_paths']!r}")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-publication-prose-"))
    path = scratch / "result.json"

    def prose_without_the_capture(tampered):
        # The sentence an earlier round left behind, kept beside the capture: it
        # claims a count the captured per-path entries do not support.
        tampered["publication"]["compared_paths"] = (
            record["publication"]["compared_paths"].replace(
                f"{published_files} of the {len(capture['compared_paths'])} compared paths",
                f"{published_files - 2} of the {len(capture['compared_paths'])} compared paths"))

    def capture_without_a_file(tampered):
        # The other direction: the capture loses a published file and its own
        # per-entry decisions are recomputed to match, so the only thing left
        # disagreeing is the sentence the record retains.
        entries = tampered["publication"]["capture"]["compared_paths"]
        for entry in entries:
            if entry["published"] == "file" and entry["worktree"] == "file" \
                    and entry["differs"]:
                entry["published"] = "absent"
                entry["published_sha256"] = None
                entry["outcome"], entry["differs"] = module.path_decision(
                    entry["published"], entry["published_sha256"],
                    entry["worktree"], entry["worktree_sha256"])
                break
        tampered["publication"]["publication_capture_line"] = \
            module.publication_capture_line(tampered["publication"]["capture"])

    accepted_before = _accepts(module, record_path, "check_publication_record")[0]
    print(f"# the tree's own check accepts its retained record: {accepted_before}")
    if not hasattr(module, "compared_paths_prose"):
        raise AssertionError(
            "the tree's publication check reads no derivation of the comparison-set prose, "
            f"so a sentence claiming {published_files - 2} paths where the captured run "
            f"records {published_files} is certified"
        )
    module.check_publication_record(record_path)
    for label, mutate in (("the prose count the capture does not support",
                           prose_without_the_capture),
                          ("the capture stripped of a published file", capture_without_a_file)):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        path.write_text(json.dumps(tampered), encoding="utf-8")
        accepted, message = _accepts(module, path, "check_publication_record")
        if accepted:
            raise AssertionError(
                f"the tree accepted {label}, so the retained sentence and the captured "
                "per-path evidence are not required to be one run's"
            )
        print(f"# {label} is reported: {message}")


def r35_format_version_prose():
    """The version prose is derived from the writer's own version table.

    The reviewer's finding: the retained summary still named version 5 as the
    current suite format while ``runner.SUITE_FORMAT_VERSION`` is 6 and the version
    map beside it already described 5 as the earlier outward-only identity,
    because the sentence was a second, hand-maintained copy of the constants. This
    takes the tree's own retained record, requires its check to report a sentence
    that names an outdated table, and — on a tree whose checks read none of this —
    prints the sentence against the constants that tree's own writer declares.
    """
    target, module = _target_probe()
    record_path, record = _target_record(target)
    prose = record.get("record_format_versions", {})
    sentence = prose.get("this_round", "")
    print(f"# the retained version prose: {sentence!r}")
    print(f"# the tree's writer declares: FORMAT_VERSION "
          f"{getattr(runner, 'FORMAT_VERSION', None)}, PRIOR_SUITE_FORMAT_VERSION "
          f"{getattr(runner, 'PRIOR_SUITE_FORMAT_VERSION', None)}, "
          f"OUTWARD_IDENTITY_SUITE_FORMAT_VERSION "
          f"{getattr(runner, 'OUTWARD_IDENTITY_SUITE_FORMAT_VERSION', None)}, "
          f"SUITE_FORMAT_VERSION {getattr(runner, 'SUITE_FORMAT_VERSION', None)}")
    if not hasattr(module, "check_predeclaration_record"):
        accepted, _ = _accepts(module, record_path, "check_publication_record")
        print(f"# the tree has no check that reads this sentence; its publication check "
              f"accepts the record: {accepted}")
        current = getattr(runner, "SUITE_FORMAT_VERSION", None)
        if current is not None and f"{current} current suite" not in sentence:
            raise AssertionError(
                f"the tree's retained version prose does not state that version {current} is "
                f"the current suite format while its own writer emits it: {sentence!r}"
            )
        raise AssertionError(
            "the tree reads no derivation of this sentence, so it may describe a version "
            "table its writer does not have"
        )
    module.check_predeclaration_record(record_path)
    print("# the retained record passes the check")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-version-prose-"))
    path = scratch / "result.json"
    current = getattr(runner, "SUITE_FORMAT_VERSION", None)
    stale = sentence.replace(
        f"{current} current suite", "5 current suite")
    if stale == sentence:
        raise AssertionError(
            "the retained sentence does not state the current suite format through the "
            f"constant, so this row cannot rewrite it: {sentence!r}"
        )
    tampered = json.loads(json.dumps(record))
    tampered["record_format_versions"]["this_round"] = stale
    path.write_text(json.dumps(tampered), encoding="utf-8")
    print(f"# the sentence rewritten to name version 5 as the current suite: {stale!r}")
    accepted, message = _accepts(module, path, "check_predeclaration_record")
    if accepted:
        raise AssertionError(
            "the tree accepted a retained summary that names version 5 as the current suite "
            f"format while its writer emits version {current}"
        )
    print(f"# the outdated sentence is reported: {message}")


def r36_loaded_identity_reload():
    """A coherent reload is recorded as the code that computes the choices.

    The control for the two refusals below, and the positive half of the review's
    finding: a long-lived process reloads the wrapper whose code computes the
    choices, and must record the reloaded digests rather than an identity bound
    when the writer was imported. The program's ``reload`` mode reloads the
    wrapper *and* the writer — the writer holds the agent factory by value, so
    reloading the wrapper alone is a mixed closure and is the case
    ``loaded_closure_consistency`` measures — and the contract here is that the
    recorded identity is the loader's current digest for each reloaded module and
    that verification passes, because the reloaded code is what chose the recorded
    inputs. This row passes on the tree this round replaces as well: a writer that
    re-reads its identity at import records the reloaded digests there too, so the
    row is a control rather than a failure-before, and the failure-before for the
    reload family is ``loaded_closure_consistency``.
    """
    if "tetris" not in AGENT_NAMES or not (
        hasattr(runner, "_LOADED_OBJECTIVE_SOURCES")
        or hasattr(runner, "_loaded_objective_sources")
    ):
        raise SubjectAbsent(
            "this tree has no Tetris agent, so it records no objective identity whose "
            "reload behaviour could be measured"
        )
    with tempfile.TemporaryDirectory(prefix="exp003-loaded-reload-") as directory:
        measured = _run_counterexample("reload", Path(directory))
        print(f"# reload run: the module is {measured['subject']}, the file before the edit "
              f"{measured['before'][:16]}, after {measured['on_disk'][:16]}, the loader's "
              f"record {measured['loader'][:16]}, what the writer records "
              f"{measured['record'][:16]}, verified {measured['outcome']['verified']}")
        assert measured["before"] != measured["on_disk"], (
            "the counterexample's edit did not change the covered file, so the run measured "
            "nothing"
        )
        assert measured["loader"] == measured["on_disk"], (
            "the reload did not update the loader's record of the module it re-read: loader "
            f"{measured['loader']}, file {measured['on_disk']}"
        )
        if measured["record"] != measured["loader"]:
            raise AssertionError(
                "the writer recorded the identity bound when it was imported rather than the "
                f"reloaded module's own: the loader's record is {measured['loader']} (the "
                f"code that computes the choices after the reload) while the run records "
                f"{measured['record']} — the bytes from before the reload, which drove no "
                "choice of this run"
            )
        assert measured["outcome"]["verified"] is True, (
            "the reloaded module's own code chose the recorded inputs and the tree holds it, "
            f"so the record must verify: {measured['outcome'].get('error')}"
        )
        print("# the recorded identity is the reloaded module's; the reload is recorded, "
              "not a stale import-time snapshot")


def r37_base_commit_trees():
    """The base snapshot's commits' trees come from the repository's own objects.

    The same class as ``publication_tree_derivation``, one block over: the base
    snapshot's ``git_tree_id`` and ``remote_main_tree`` were validated against
    copies of themselves — the captured ``rev-parse`` output is inside the same
    object — so rewriting the field, its capture copy and the command output
    together certified a commit/tree pairing no run observed. This takes the tree's
    own retained record, rewrites each pairing in every copy with the state line
    regenerated by the tree's own helper, and requires it to be reported. A tree
    whose check compares the field with its own copies accepts both.
    """
    target, module = _target_probe()
    if not hasattr(module, "check_base_commit_record"):
        raise SubjectAbsent(
            f"{target} has no check_base_commit_record: this row's subject is the retained "
            "base-refresh snapshot, and that tree records none"
        )
    record_path, record = _target_record(target)
    module.check_base_commit_record(record_path)
    print("# the retained snapshot passes the check")
    scratch = Path(tempfile.mkdtemp(prefix="exp003-base-trees-"))
    path = scratch / "result.json"
    zeros = "0" * 40
    # The observed tip is this checkout's own HEAD, read from the worktree the row
    # runs in: a commit this repository holds, so the tip's tree can be resolved
    # from outside the snapshot.
    repo_root = Path(__file__).resolve().parents[3]
    head = module._git(repo_root, "rev-parse", "HEAD")[1].strip()

    def rewrite(tampered, trees, tip=None):
        """Set the named tree fields in every copy, and regenerate the derived lines."""
        base = tampered["base_commit"]
        for field, value in trees.items():
            base[field] = value
            base["capture"][field] = value
        if tip is not None:
            base["remote_main_tip"] = tip
            base["capture"]["remote_main_tip"] = tip
            for entry in base["capture"]["commands"]:
                if entry["role"] == "refreshed remote main commit from the clone":
                    entry["output"] = tip
        for entry in base["capture"]["commands"]:
            for role, field in module.BASE_COMMIT_ROLES:
                if entry["role"] == role and field in trees:
                    entry["output"] = trees[field]
        base["base_capture_line"] = module.base_capture_line(base["capture"])
        base["state"] = module.base_state_line(
            {name: base[name] for name in module.BASE_COMMIT_FIELDS})

    for label, mutate in (
        ("git_tree_id and remote_main_tree, their capture copies and the captured "
         "rev-parse outputs all set to 000…",
         lambda tampered: rewrite(tampered, {"git_tree_id": zeros,
                                             "remote_main_tree": zeros})),
        ("remote_main_tree likewise, with the observed tip moved to a commit this "
         "checkout holds",
         lambda tampered: rewrite(tampered, {"remote_main_tree": zeros}, tip=head)),
    ):
        tampered = json.loads(json.dumps(record))
        mutate(tampered)
        path.write_text(json.dumps(tampered), encoding="utf-8")
        accepted, message = _accepts(module, path, "check_base_commit_record")
        if accepted:
            raise AssertionError(
                f"the tree accepted the retained base snapshot with {label}, a commit/tree "
                "pairing no run observed, because the field is checked only against copies "
                "of itself"
            )
        print(f"# {label} is reported: {message}")



def r38_loaded_closure_consistency():
    """A partial reload is refused, not stamped with the reloaded identity.

    The reviewer's counterexample, one step past ``loaded_identity_reload``, in
    both directions a partial reload can take. Reloading only the objective module
    updates the loader's digest for it, while the wrapper that drives the objective
    keeps the callable it imported by value; reloading only the wrapper updates
    *its* digest, while the writer that selects the agent keeps the factory it
    imported by value (``runner.create_agent``, and beside it the script parser and
    the agent classes). In either direction the code that would compute a choice
    and the module an identity would name are two implementations, and no single
    digest describes both. The counterexample program's ``mixed`` and
    ``mixed-caller`` modes run those orderings in a fresh process and report what
    the writer did; this row requires a refusal that names a stale reference, and
    reports the record the tree wrote instead where there is no refusal. A tree
    that stamps the reloaded module's digest on a run whose choices come from the
    old object fails.
    """
    if "tetris" not in AGENT_NAMES or not _reads_loaded_identity():
        raise SubjectAbsent(
            "this tree has no Tetris agent, so it records no objective identity whose "
            "closure consistency could be measured"
        )
    accepted: list[str] = []
    with tempfile.TemporaryDirectory(prefix="exp003-loaded-closure-") as directory:
        for mode, reference in (("mixed", "block_stack_ai.agents.tetris_choice"),
                                ("mixed-caller", "block_stack_ai.runner.create_agent")):
            measured = _run_counterexample(mode, Path(directory) / mode)
            print(f"# {mode}: the module is {measured['subject']}, the file before the edit "
                  f"{measured['before'][:16]}, after {measured['on_disk'][:16]}, the loader's "
                  f"record {measured['loader'][:16]}, what the writer did "
                  f"(refused={measured['refused']}, recorded "
                  f"{(measured['record'] or 'nothing')[:16]})")
            assert measured["before"] != measured["on_disk"], (
                "the counterexample's edit did not change the covered file, so the run "
                "measured nothing"
            )
            assert measured["loader"] == measured["on_disk"], (
                "the reload did not update the loader's record of the module it re-read: "
                f"loader {measured['loader']}, file {measured['on_disk']}"
            )
            if not measured["refused"]:
                accepted.append(
                    f"{mode}: the writer stamped a record for a mixed loaded closure instead "
                    f"of refusing it (the loader's record for {measured['subject']} is "
                    f"{measured['loader']}, while the code that would compute a choice is the "
                    f"object the caller imported by value, and the run was recorded as "
                    f"{measured['record']})")
                continue
            assert reference in (measured["refusal"] or ""), (
                f"the writer refused the {mode} run but did not name {reference}: "
                f"{measured['refusal']}"
            )
            assert measured["record"] is None, measured
            print(f"# {mode} is refused, and the refusal names {reference}: "
                  f"{(measured['refusal'] or '')[:110]}…")
    if accepted:
        raise AssertionError("; ".join(accepted))


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
    "publication_content": r15_publication_content,
    "objective_required_when_versioned": r16_objective_required_when_versioned,
    "objective_identity": r17_objective_identity,
    "piece_summary_schema": r18_piece_summary_schema,
    "predeclaration_identity": r19_predeclaration_identity,
    "remote_main_durability": r20_remote_main_durability,
    "publication_count_capture": r21_publication_count_capture,
    "base_commit_record": r22_base_commit_record,
    "publication_record_derivation": r23_publication_record_derivation,
    "base_worktree_ancestry": r24_base_commit_worktree_ancestry,
    "live_objective_snapshot": r25_live_objective_snapshot,
    "predeclaration_record_identity": r26_predeclaration_record_identity,
    "predeclaration_weights": r27_predeclaration_weights,
    "objective_wrapper_identity": r28_objective_wrapper_identity,
    "summary_histogram_derivation": r29_summary_histogram_derivation,
    "loaded_identity": r30_loaded_identity,
    "stale_cache": r31_stale_cache,
    "publication_tree_derivation": r32_publication_tree_derivation,
    "predeclaration_created_at": r33_predeclaration_created_at,
    "publication_paths_prose": r34_publication_paths_prose,
    "format_version_prose": r35_format_version_prose,
    "loaded_identity_reload": r36_loaded_identity_reload,
    "base_commit_trees": r37_base_commit_trees,
    "loaded_closure_consistency": r38_loaded_closure_consistency,
}
# The ids whose subject is a probe file rather than the tree's ``src``: they
# accept the path of the probe file to drive, for a tree that carries only
# ``src`` (the ``after`` run) or for a pre-change tree whose own probe file should
# be driven (``publication_content``, ``remote_main_durability``).
PROBE_FILE_IDS = (
    "publication_content", "predeclaration_identity", "remote_main_durability",
    "publication_count_capture", "base_commit_record", "publication_record_derivation",
    "base_worktree_ancestry", "predeclaration_record_identity", "predeclaration_weights",
    "publication_tree_derivation", "predeclaration_created_at", "publication_paths_prose",
    "format_version_prose", "base_commit_trees",
)


def main() -> int:
    _guard()
    if (len(sys.argv) not in (2, 3) or sys.argv[1] not in PROBES
            or (len(sys.argv) == 3 and sys.argv[1] not in PROBE_FILE_IDS)):
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}} [probe-file]  "
              f"(the probe file is only for {', '.join(PROBE_FILE_IDS)})", file=sys.stderr)
        return 2
    global PUBLICATION_PROBE_OVERRIDE
    if len(sys.argv) == 3:
        PUBLICATION_PROBE_OVERRIDE = Path(sys.argv[2])
    name = sys.argv[1]
    print(f"# probe: {name}")
    try:
        PROBES[name]()
    except SubjectAbsent as error:
        print(f"# no subject on this tree: {error}")
        return 0
    except AssertionError as error:
        print(f"AssertionError: {error}")
        return 1
    print("result: the tree under test satisfies this probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
