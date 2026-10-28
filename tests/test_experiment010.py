"""Experiment 010's harness: statistics, seeds, and a short real game."""

from __future__ import annotations

import base64

import pytest

from block_stack_ai import experiment009 as e9
from block_stack_ai import experiment010 as e10

CONFIG = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500, "agent": "reach_plan",
    "formats": [{"tap_hz": 30, "reaction_ms": 300}], "seeds": [7],
}


def test_the_seeds_are_a_prefix_of_008s_held_out_seeds():
    seeds = e10.heldout_seeds()
    assert seeds == e9.heldout_seeds()[:len(seeds)]
    assert e10.heldout_seeds({"seed_count": 5}) == e9.heldout_seeds()[:5]
    assert len(e10.record_configuration()["seeds"]) == len(seeds)


def test_the_parameters_are_009s_unchanged():
    assert e10.FINAL_PARAMS == e9.FINAL_PARAMS
    assert e10.record_configuration()["params"] == e9._load(e9.FINAL_PARAMS)["resolved"]


def test_the_success_rule_is_the_predeclared_one():
    assert e10.success({"ci95_low": 1.0})
    assert not e10.success({"ci95_low": 0.0})
    assert not e10.success({"ci95_low": -5.0})
    assert "entirely above 0" in (e10.EXPERIMENT_ROOT / "predeclared.md").read_text(encoding="utf-8")


def test_rates_average_placements_per_piece_by_level_band():
    games = [{"level_29": [2, 20, 24], "level_39_plus": [0, 0, 0]},
             {"level_29": [2, 10, 12], "level_39_plus": [4, 40, 44]}]
    rates = e10._rates(games)
    assert rates["level_29"] == {"pieces": 4, "limits_mean": 7.5, "reach_mean": 9.0}
    assert rates["level_39_plus"]["limits_mean"] == 10.0
    assert e10._rates([{"level_29": [0, 0, 0], "level_39_plus": [0, 0, 0]}])["level_29"][
        "limits_mean"] is None


@pytest.mark.integration
def test_a_short_reach_plan_game_replays_and_counts_its_spawns():
    config = dict(CONFIG, params=e9._load(e9.FINAL_PARAMS)["resolved"])
    episode = e10._play((0, CONFIG["formats"][0], 7, config))
    assert len(base64.b64decode(episode["inputs"])) == 1500
    assert e9._replay(episode, config) == []
    assert episode["result"]["decision_seconds"] > 0
    spawns = e10.spawns(episode, config)
    assert len(spawns) == episode["result"]["pieces"]
    counts = e10.placement_counts(episode, config)
    assert set(counts) == {"level_29", "level_39_plus"}
    game = e10.autopsy_game(episode, config)
    assert len(game["window"]) == min(e10.AUTOPSY_WINDOW, len(spawns))
    assert all(row["reach_placements"] >= row["limits_placements"] for row in game["window"])
