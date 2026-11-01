"""Experiment 024: real outcomes for the late boards."""

from __future__ import annotations

import numpy as np
import pytest

from block_stack_ai import experiment023 as e23, experiment024 as e24


def test_late_boards_take_the_rest_of_their_games_points():
    t = e24.TETRIS_18
    data = {"game": np.array([0, 0, 0, 1]), "lines": np.array([200, 240, 250, 10]),
            "score": np.array([0, 2, 3, 0]) * t, "final": np.array([5, 5, 5, 3]) * t}
    backup = np.array([1.0, 9.0, 9.0, 4.0])
    found = e24.lambda_returns(backup, data, 0.5, 230)
    # From 230 lines on the backup is ignored: the rest of the game's points.
    assert list(found[1:3]) == pytest.approx([5 - 2, 5 - 3])
    # Below 230, 023's mix of the backup and the step to the next board's return.
    assert found[0] == pytest.approx(0.5 * 1 + 0.5 * (2 + 3))
    assert found[3] == pytest.approx(0.5 * 4 + 0.5 * 3)
    # With nothing late it is 023's lambda-return.
    assert list(e24.lambda_returns(backup, data, 0.5, 10_000)) == pytest.approx(
        list(e23.lambda_returns(backup, data, 0.5)))


def test_the_loop_stops_at_the_cap_or_after_three_flat_sweeps(monkeypatch):
    means = {0: 100, 1: 120, 2: 110, 3: 119, 4: 115, 5: 130}
    monkeypatch.setattr(e24, "_probe_path", lambda k: k)
    monkeypatch.setattr(e24, "_load", lambda p: {"max_sweeps": 10, "stop_after_flat": 3}
                        if p == e24.CONFIG else {"runs": {"net": {"mean_score": means[p]}}})
    assert [e24._should_stop(k) for k in range(1, 6)] == [False, False, False, True, False]
    monkeypatch.setattr(e24, "_load", lambda p: {"max_sweeps": 5, "stop_after_flat": 3}
                        if p == e24.CONFIG else {"runs": {"net": {"mean_score": means[p]}}})
    assert e24._should_stop(5)
