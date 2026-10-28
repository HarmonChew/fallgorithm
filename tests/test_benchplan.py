"""Experiment 008's benchmark agent, without the native engine."""

from __future__ import annotations

from types import SimpleNamespace

from block_stack_ai import benchplan, survivalplan, wellplan
from block_stack_ai.limits import Flight, Limits, Reach
from block_stack_ai.pathaware import _reachable, gravity_period, grid_columns

import test_survivalplan as survival_tests

LIMITS = Limits(30, 300)


def _pathaware_options(columns, piece, flight, level, ruleset, limits):
    """Stand-in reachable set: pathaware's, so the search can be compared to the original."""
    return [(Reach(p.orientation, p.x, p.y, ()), p.lines_cleared, settled)
            for p, settled in _reachable(columns, piece, gravity_period(level), 0)]


def test_the_copied_search_matches_survival_plan_on_the_same_reachable_set(monkeypatch):
    monkeypatch.setattr(benchplan, "_options", _pathaware_options)
    arguments = dict(survival_tests.ARGUMENTS)
    for grid, piece, preview, drought, level in survival_tests._boards(40):
        expected = survivalplan.search_choice(
            grid, piece, preview, drought=drought, level=level,
            phase_of=survivalplan.survival_phase if level >= survivalplan.SURVIVAL_LEVEL
            else wellplan.initial_phase, **arguments)
        found = benchplan.search(
            grid_columns(grid), piece, preview, flight=Flight(), drought=drought, level=level,
            lines=0, start_level=18, ruleset="classic_ntsc_extended", limits=LIMITS)
        assert (found[0].orientation, found[0].x) == (expected.orientation, expected.x)


def test_the_commit_search_finds_a_placement_without_a_preview(monkeypatch):
    monkeypatch.setattr(benchplan, "_options", _pathaware_options)
    for grid, piece, _, drought, level in survival_tests._boards(10):
        found = benchplan.search(
            grid_columns(grid), piece, None, flight=Flight(), drought=drought, level=level,
            lines=0, start_level=18, ruleset="classic_ntsc_extended", limits=LIMITS)
        assert found is not None


def _state(**changes):
    values = dict(
        phase="active", terminal=False, piece_count=3, current_piece="O", next_piece="T",
        board=[[0] * 10 for _ in range(20)], orientation=0, x=5, y=0, gravity_counter=0,
        first_delay_remaining=0, previous_input=0, das_counter=0, level=18, lines=0,
        start_level=18, ruleset="classic_ntsc_double_killscreen")
    values.update(changes)
    return SimpleNamespace(**values)


def test_the_agent_commits_then_adjusts_at_the_reaction_frame():
    agent = benchplan.BenchAgent(Limits(30, 300))
    calls = []
    real = benchplan.search

    def spy(*args, **kwargs):
        calls.append((args[2] is None, kwargs["flight"].frame))
        return real(*args, **kwargs)

    benchplan.search, original = spy, benchplan.search
    try:
        for frame in range(25):
            agent.act(_state(y=frame))
    finally:
        benchplan.search = original
    assert calls == [(True, 0), (False, 18)]
    assert agent.pieces == 1 and agent.adjusts == 1


def test_with_no_reaction_time_the_agent_searches_once_with_the_preview():
    agent = benchplan.BenchAgent(Limits(30, 0))
    calls = []
    real = benchplan.search
    benchplan.search, original = lambda *a, **k: (calls.append(a[2]), real(*a, **k))[1], real
    try:
        for _ in range(10):
            agent.act(_state())
    finally:
        benchplan.search = original
    assert calls == ["T"]
    assert agent.adjusts == 0


def test_the_agent_presses_nothing_outside_the_active_phase():
    agent = benchplan.BenchAgent(Limits(30, 300))
    assert agent.act(_state(phase="entry_delay")) == 0


def test_a_drought_follows_the_pieces_seen_so_far():
    agent = benchplan.BenchAgent(Limits(30, 300))
    agent.act(_state(current_piece="O", next_piece="I", piece_count=1))
    assert agent._drought_before == 0 and agent._drought == 1  # the preview is not seen yet
    for _ in range(20):
        agent.act(_state(current_piece="O", next_piece="I", piece_count=1))
    assert agent._drought == 0  # after the adjust the I is known
    agent.act(_state(current_piece="I", next_piece="O", piece_count=2))
    assert agent._drought == 0
