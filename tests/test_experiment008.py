"""Experiment 008's harness: statistics without the engine, and a short real game."""

from __future__ import annotations

import base64

import pytest

from block_stack_ai import experiment008 as e8

CONFIG = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500, "agent": "bench_plan",
    "formats": [{"tap_hz": 30, "reaction_ms": 300}], "seeds": [7],
}


def test_percentiles_interpolate_linearly():
    assert e8._percentile([10, 20, 30, 40, 50], 50) == 30
    assert e8._percentile([10, 20, 30, 40, 50], 10) == 14
    assert e8._percentile([5], 90) == 5


def test_format_metrics_count_each_stopping_reason_and_level():
    def row(lines, reason, l29, l39):
        return {"lines": lines, "score": lines * 1000, "stopping_reason": reason,
                "level_29_score": l29, "level_39_score": l39, "pieces": 100, "switches": 10}
    rows = [row(100, "game_over", None, None), row(300, "game_over", 5, None),
            row(430, "line_cap", 5, 9), row(430, "line_cap", 5, 9)]
    metrics = e8._format_metrics(rows)
    assert metrics["top_out_pct"] == 50.0
    assert metrics["reached_level_29_pct"] == 75.0
    assert metrics["reached_level_39_pct"] == 50.0
    assert metrics["reached_line_cap_pct"] == 50.0
    assert metrics["lines"]["mean"] == 315.0
    assert metrics["adjust_switch_pct"] == 10.0


def test_prior_seeds_cover_the_earlier_experiments():
    seeds = e8.prior_seeds()
    assert seeds == sorted(set(seeds)) and 33713 in seeds  # an Experiment 006 seed


@pytest.mark.integration
def test_a_short_game_replays_and_a_tampered_record_does_not():
    episode = e8._play((0, CONFIG["formats"][0], 7, CONFIG))
    assert episode["result"]["stopping_reason"] == "frame_limit"
    assert episode["result"]["frames"] == len(base64.b64decode(episode["inputs"])) == 1500
    assert e8._replay(episode, CONFIG) == []
    episode["result"]["lines"] += 1
    assert any("lines" in problem for problem in e8._replay(episode, CONFIG))


@pytest.mark.integration
def test_the_line_cap_stops_the_game_at_the_lock_that_reaches_it():
    config = dict(CONFIG, line_cap=1, frame_cap=20000)
    episode = e8._play((0, config["formats"][0], 7, config))
    assert episode["result"]["stopping_reason"] == "line_cap"
    assert episode["result"]["lines"] >= 1
    assert e8._replay(episode, config) == []
    # Replaying with a higher cap would continue past the recorded stop.
    assert e8._replay(episode, dict(config, line_cap=2)) != []
