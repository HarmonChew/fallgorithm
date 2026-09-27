"""Pre-change probes: each new 003 regression's contract, run on the base tree.

Run this file with the recorded base commit's ``src`` on ``PYTHONPATH``:

    sandbox=/tmp/exp003-base
    mkdir -p $sandbox && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C $sandbox
    PYTHONPATH=$sandbox/src python experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>

Each id evaluates one new regression's contract against pre-change code as far
as that code can express it, prints what the base tree reports, and exits 1 when
the base behaviour violates the regression's assertion (the expected result for
the clear-size and Tetris-objective rows) or 0 when the contract already held
before the change (the legacy-record compatibility row). A contract whose
subject does not exist at the base at all is never counted as a failure-before;
those rows carry an executed substitute instead, named in ``notes.md``.
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import block_stack_ai

BASE_MODULE = block_stack_ai.__file__


def _guard() -> None:
    if "003-tetris-aware-agent" in str(BASE_MODULE):
        raise SystemExit(f"refusing to run: imported {BASE_MODULE}, not a pre-change tree")
    try:
        import block_stack_ai.tetris  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        raise SystemExit(f"refusing to run: {BASE_MODULE} already carries the tetris module")
    print(f"# base module: {BASE_MODULE}")


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


PROBES = {
    "clear_sizes_field": r1_clear_sizes_field,
    "clear_sizes_summary": r2_clear_sizes_summary,
    "legacy_record_verifies": r3_legacy_record_verifies,
    "premature_clear": r4_premature_clear,
    "tetris_term": r5_tetris_term,
    "agent_name": r6_agent_name,
    "live_clear_sizes": r7_live_clear_sizes,
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
    print("result: the base tree satisfies this probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
